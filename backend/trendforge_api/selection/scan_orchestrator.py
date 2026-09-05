"""File A daily scan orchestrator: chains S0-S8 builders into one command.

Usage:
    python -m trendforge_api.selection.scan_orchestrator

Runs every stage in order using the current hash-matched spine, persists the
S8 blob, and prints a summary. This is the single entry point for daily
research scans. No broker, no orders, no CONFIRMED unlock.
"""

from __future__ import annotations

import sys
import time

from ..scanners.native_core import build_native_core_run
from .r5_live import latest_r5_structure_batch
from .s2_market_weather import build_s2_market_weather
from .s4_structure_pack import build_s4_structure_pack
from .s5_shortlist_enrichment import build_s5_enrichment
from .s6_family_resolution import build_s6_resolution
from .s7_state_gates import build_s7_state
from .s8_persist_run import (
    S8ScanBlobV1,
    build_s8_scan,
    persist_s8_scan,
)


def run_daily_scan() -> dict:
    """Chain all stage builders and persist ONE reconstructable blob."""
    t0 = time.monotonic()
    stages: list[dict] = []

    def _stage(name: str, fn):
        start = time.monotonic()
        try:
            result = fn()
            elapsed = round(time.monotonic() - start, 2)
            stages.append({"stage": name, "ok": True, "elapsed_s": elapsed})
            return result
        except Exception as exc:
            elapsed = round(time.monotonic() - start, 2)
            stages.append({
                "stage": name, "ok": False,
                "error": str(exc)[:200], "elapsed_s": elapsed,
            })
            raise

    weather = _stage("S2 weather", lambda: build_s2_market_weather())
    r5 = _stage("R5 structure", lambda: latest_r5_structure_batch())
    if r5 is None:
        raise ValueError("WAIT_ORCHESTRATOR_R5_NOT_READY")
    pack = _stage("S4 pack", lambda: build_s4_structure_pack(r5=r5))
    s5_batch = None
    try:
        s5_batch = _stage("S5 enrich", lambda: build_s5_enrichment(s4=pack))
    except ValueError:
        stages.append({"stage": "S5 enrich", "ok": False, "note": "fallback used"})
    s6_board = _stage("S6 resolve", lambda: build_s6_resolution(
        s4=pack, r5=r5, s5=s5_batch, weather=weather
    ))
    s7_board = _stage("S7 gates", lambda: build_s7_state(
        r5=r5, s4=pack, s5=s5_batch, s6=s6_board, weather=weather
    ))
    native_core = _stage(
        "R13 guidance", lambda: build_native_core_run(r5=r5)
    )

    prior_blob = None
    try:
        from .store import latest_selection_payload
        from .s8_persist_run import PROFILE_ID as _S8_PROFILE
        prior_blob = latest_selection_payload(_S8_PROFILE)
    except Exception:
        pass

    blob = _stage("S8 build+persist", lambda: _build_and_persist(
        r5=r5, pack=pack, s5=s5_batch, s6=s6_board,
        s7=s7_board, weather=weather, native_core=native_core,
        prior_payload=prior_blob,
    ))

    total = round(time.monotonic() - t0, 2)
    return {
        "runId": blob.run_id,
        "confirmedCount": blob.confirmed_count,
        "rowCount": len(blob.rows),
        "states": sorted({r.public_state.value for r in blob.rows}),
        "totalSeconds": total,
        "stages": stages,
    }


def _build_and_persist(
    r5=None,
    pack=None,
    s5=None,
    s6=None,
    s7=None,
    weather=None,
    native_core=None,
    prior_payload=None,
    **_,
) -> S8ScanBlobV1:

    blob = build_s8_scan(
        s7=s7, s6=s6, pack=pack, r5=r5,
        s5=s5,
        weather=weather,
        native_core=native_core,
        prior_payload=prior_payload,
    )
    return persist_s8_scan(blob)


def main() -> None:
    print("=== TrendForge daily scan ===")
    try:
        summary = run_daily_scan()
    except Exception as exc:
        print(f"SCAN FAILED: {exc}")
        sys.exit(1)

    print(f"runId: {summary['runId']}")
    print(f"rows: {summary['rowCount']}")
    print(f"states: {summary['states']}")
    print(f"confirmedCount: {summary['confirmedCount']}")
    print(f"time: {summary['totalSeconds']}s")
    for s in summary["stages"]:
        status = "✓" if s.get("ok") else "✗"
        elapsed = f" ({s.get('elapsed_s', '?')}s)" if s.get("elapsed_s") else ""
        print(f"  {status} {s['stage']}{elapsed}")


if __name__ == "__main__":
    main()
