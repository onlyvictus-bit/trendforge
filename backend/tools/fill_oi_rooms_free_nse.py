"""Fetch official free NSE FO/MWPL/ban artifacts and rebuild OI rooms.

Not a File A activation. Observation codes stay CONTEXT_ONLY.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from trendforge_api.options_intelligence.bff import (  # noqa: E402
    build_oi_analysis_batch,
    build_oi_tracker_batch,
    build_strike_explorer_batch,
)
from trendforge_api.options_intelligence.eod_chain import (  # noqa: E402
    persist_eod_option_chains_from_fo,
)
from trendforge_api.parsers.nse_fo_bhavcopy_parser import parse_nse_fo_bhavcopy  # noqa: E402
from trendforge_api.selection.fo_a6_enrichment import (  # noqa: E402
    build_fo_enrichment_batch,
    persist_fo_enrichment,
)
from trendforge_api.source_monitor import check_source  # noqa: E402
from trendforge_api.source_parser import parse_source, read_snapshot_bytes  # noqa: E402
from trendforge_api.storage import get_latest_source_snapshot  # noqa: E402


SOURCES = ("nse_fo_bhavcopy", "nse_fno_ban", "nse_mwpl_percentages")


def _fetch_and_parse(source_key: str) -> None:
    snapshot = check_source(source_key, fetch=True, timeout_seconds=45)
    print(
        f"FETCH {source_key} state={snapshot.check_state} "
        f"status={snapshot.status_code} url={snapshot.url} "
        f"bytes={snapshot.content_length}"
    )
    parsed = parse_source(source_key, save=True)
    print(
        f"PARSE {source_key} {parsed.parser_state} date={parsed.data_date} "
        f"rows={parsed.record_count} {parsed.summary[:160]}"
    )


def main() -> int:
    for key in SOURCES:
        try:
            _fetch_and_parse(key)
        except Exception as exc:
            print(f"FAIL {key}: {type(exc).__name__}: {exc}")

    fo_snap = get_latest_source_snapshot("nse_fo_bhavcopy")
    fo_bytes = read_snapshot_bytes(fo_snap.raw_path if fo_snap else None)
    if not fo_bytes:
        print("NO FO BYTES")
        return 1
    parsed_fo = parse_nse_fo_bhavcopy(fo_bytes)
    print(
        "FO_ROWS",
        parsed_fo.get("parser_state"),
        parsed_fo.get("data_date"),
        parsed_fo.get("record_count"),
    )
    a6 = persist_fo_enrichment(build_fo_enrichment_batch(fo_content=fo_bytes))
    ok = [row for row in a6.rows if row.fo_state == "FUTURES_OK" and row.near_future]
    print(
        "A6",
        a6.data_date,
        a6.parser_state,
        "rows",
        a6.row_count,
        "FUTURES_OK",
        len(ok),
    )
    if ok:
        sample = ok[0]
        nf = sample.near_future
        print(
            "A6_SAMPLE",
            sample.symbol,
            nf.expiry,
            "oi",
            nf.open_interest,
            "d_oi",
            nf.oi_change,
            "close",
            nf.close,
        )
    chain = persist_eod_option_chains_from_fo(
        (parsed_fo.get("output") or {}).get("rows") or [],
        symbols={row.symbol for row in ok},
        limit_underlyings=188,
    )
    print("EOD_CHAINS", chain)

    analysis = build_oi_analysis_batch(limit=40)
    codes = {}
    mwpl_states = {}
    for row in analysis.rows:
        codes[row.observation_code] = codes.get(row.observation_code, 0) + 1
        mwpl_states[row.mwpl.official_state] = (
            mwpl_states.get(row.mwpl.official_state, 0) + 1
        )
    print(
        "OI_ANALYSIS",
        analysis.data_date,
        "n",
        analysis.row_count,
        "codes",
        codes,
        "mwpl",
        mwpl_states,
    )
    tracker = build_oi_tracker_batch(limit=10)
    print("OI_TRACKER", tracker.row_count, tracker.rows[0].public_state if tracker.rows else None)
    if ok:
        sample = ok[0]
        try:
            strike = build_strike_explorer_batch(
                underlying=sample.symbol, expiry=sample.near_future.expiry
            )
            print(
                "STRIKE",
                sample.symbol,
                sample.near_future.expiry,
                strike.quality_state,
                "ladder",
                len(strike.ladder),
                "call",
                strike.call_wall.strike,
            )
        except Exception as exc:
            print(f"STRIKE_WAIT {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
