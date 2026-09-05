"""File A R11 MCX master + swing RS/delivery gate tests.

Law under test:
- MCX stays WAIT without an official local master + local bars;
  missing lot/tick/expiry stays WAIT (never invented);
- FBIL FX / CFTC / WGC are delayed context and can never unlock or confirm
  MCX; PRF-005/006/007 boards stay empty this ticket;
- cash S7 CONFIRMED law is untouched (regression);
- swing delivery gate reuses S5 EOD-only semantics; INTRADAY stays forbidden;
- POST runner forbidden; no place_order in the new module.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.selection.r11_mcx_live import (
    ACCEPTANCE_CEILING,
    SCHEMA_VERSION,
    build_mcx_master,
    mcx_profile_blocker,
    swing_delivery_gate,
    swing_rs_gate,
)


def _hash(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()


def _store_parse(
    monkeypatch,
    source_key: str,
    *,
    data_date: str = "2026-08-14",
    parser_state: str = "PARSED_STRUCTURED",
    output: dict | None = None,
) -> None:
    monkeypatch.setattr(storage, "save_structured_source_rows", lambda result: None)
    snapshot = storage.save_source_snapshot(
        __import__(
            "trendforge_api.models", fromlist=["SourceSnapshotRecord"]
        ).SourceSnapshotRecord(
            sourceKey=source_key,
            name=source_key,
            url=f"https://www.mcxindia.com/{source_key}.json",
            checkState="UNCHANGED",
            statusCode=200,
            contentHash=_hash(f"{source_key}-lg"),
            contentLength=128,
            checkedAt="2026-08-14T17:30:00+00:00",
            changed=False,
        )
    )
    storage.save_source_parse_result(
        __import__(
            "trendforge_api.models", fromlist=["SourceParseResult"]
        ).SourceParseResult(
            source_key=source_key,
            snapshot_id=snapshot.id,
            parser_state=parser_state,
            data_date=data_date,
            record_count=len((output or {}).get("rows", [])) or 1,
            summary="r11 fixture",
            output=output or {"rows": [], "validEmpty": True},
            error=None,
            parsed_at="2026-08-14T17:30:00+00:00",
        )
    )


MASTER_ROWS = {
    "rows": [
        {
            "symbol": "GOLDM",
            "instrumentId": "MCX-GOLDM-20261005",
            "lotSize": 100,
            "tickSize": 1.0,
            "expiry": "2026-10-05",
            "tenderStart": None,
            "tenderEnd": None,
        },
        {
            "symbol": "SILVERM",
            "instrumentId": "MCX-SILVERM-20261230",
            # lot/tick deliberately missing -> WAIT, never invented
            "expiry": "2026-12-30",
        },
    ]
}


# ---------------------------------------------------------------------------
# §4.1 No master artifact -> READY count 0, ceiling WAIT
# ---------------------------------------------------------------------------


def test_empty_spine_is_honest_wait(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r11-empty.db")
    storage._INITIALIZED_DB_PATHS.clear()
    batch = build_mcx_master()
    assert batch.schema_version == SCHEMA_VERSION
    assert batch.acceptance_ceiling == ACCEPTANCE_CEILING == (
        "LIVE_MCX_WAIT_WITHOUT_NAMED_ACTIVATION"
    )
    assert batch.ready_count == 0
    assert batch.confirmed_count == 0
    assert batch.can_unlock_confirmed is False
    assert batch.executable is False
    overall = batch.readiness_counts.get("MASTER_AND_LOCAL_CONTEXT_READY", 0)
    assert overall == 0
    assert any("WAIT_MCX_MASTER" in w for w in batch.warnings)
    assert "mcx_market_watch" in batch.tried_source_keys


# ---------------------------------------------------------------------------
# §4.2 Master present: lot/tick/expiry missing stays WAIT, never invented
# ---------------------------------------------------------------------------


def _ready_fixture(tmp_path, monkeypatch):
    _store_parse(monkeypatch, "mcx_market_watch", output=MASTER_ROWS)
    _store_parse(
        monkeypatch,
        "mcx_bhavcopy",
        output={"rows": [{"symbol": "GOLDM", "close": 62000}], "validEmpty": False},
    )
    return build_mcx_master()


def test_rows_never_invent_missing_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r11-master.db")
    storage._INITIALIZED_DB_PATHS.clear()
    batch = _ready_fixture(tmp_path, monkeypatch)
    by_symbol = {row.symbol: row for row in batch.rows}
    gold = by_symbol["GOLDM"]
    silver = by_symbol["SILVERM"]
    assert gold.lot_size == 100 and gold.tick_size == 1.0
    assert gold.expiry == "2026-10-05"
    assert silver.lot_size is None
    assert silver.tick_size is None
    assert "WAIT_LOT" in silver.why
    assert "WAIT_TICK" in silver.why
    assert silver.readiness != "MASTER_AND_LOCAL_CONTEXT_READY"
    # GOLDM has full master fields; readiness depends on local bars freshness.
    assert gold.readiness in {
        "MASTER_AND_LOCAL_CONTEXT_READY",
        "WAIT_MCX_STALE",
        "WAIT_MCX_LOCAL_BARS",
    }
    assert all(row.can_support_confirmed is False for row in batch.rows)


# ---------------------------------------------------------------------------
# §4.3 Tender window hit -> WAIT_TENDER veto
# ---------------------------------------------------------------------------


def test_tender_window_hit_vetoes_ready(tmp_path, monkeypatch) -> None:
    rows = {
        "rows": [
            {
                "symbol": "COPPERM",
                "instrumentId": "MCX-COPPERM-20260930",
                "lotSize": 2500,
                "tickSize": 0.15,
                "expiry": "2026-09-30",
                "tenderStart": "2026-08-13",
                "tenderEnd": "2026-08-16",
            }
        ]
    }
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r11-tender.db")
    storage._INITIALIZED_DB_PATHS.clear()
    _store_parse(monkeypatch, "mcx_market_watch", output=rows)
    _store_parse(monkeypatch, "mcx_bhavcopy")
    batch = build_mcx_master(trading_date="2026-08-14")
    row = next(r for r in batch.rows if r.symbol == "COPPERM")
    assert "WAIT_TENDER" in row.why
    assert row.readiness != "MASTER_AND_LOCAL_CONTEXT_READY"


# ---------------------------------------------------------------------------
# §4.4/§4.5 FBIL / CFTC are context-only and can never unlock MCX
# ---------------------------------------------------------------------------


def test_delayed_context_cannot_unlock_or_confirm(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r11-fbil.db")
    storage._INITIALIZED_DB_PATHS.clear()
    _store_parse(monkeypatch, "fbil_usdinr_reference")
    _store_parse(monkeypatch, "cftc_cot", data_date="2026-08-11")
    batch = build_mcx_master()
    assert batch.ready_count == 0
    assert batch.confirmed_count == 0
    assert any("FBIL" in w or "delayed FX" in w for w in batch.warnings)
    assert any("CFTC" in w for w in batch.warnings)


# ---------------------------------------------------------------------------
# Swing gates reuse S5 semantics; INTRADAY stays forbidden (§4.8)
# ---------------------------------------------------------------------------


def test_swing_delivery_gate_maps_statuses() -> None:
    blocked, code = swing_delivery_gate("FORBIDDEN_ON_INTRADAY")
    assert blocked is True and code == "FORBIDDEN_ON_INTRADAY"
    blocked, code = swing_delivery_gate("CURRENT_PCT_NO_Z_HISTORY")
    assert blocked is True and code == "WAIT_DELIVERY"
    blocked, code = swing_delivery_gate("DELIVERY_Z_PIT20")
    assert blocked is False


def test_swing_rs_gate_is_gate_only_not_score() -> None:
    assert swing_rs_gate(None, None) is False
    assert swing_rs_gate(1.2, None) is True
    assert swing_rs_gate(None, 0.9) is True


def test_s5_intraday_delivery_still_forbidden() -> None:
    """Regression pin on the existing S5 EOD-only guard."""
    from trendforge_api.selection.s5_shortlist_enrichment import S5DeliveryFieldV1

    field = S5DeliveryFieldV1(
        status="FORBIDDEN_ON_INTRADAY",
        why="Delivery evidence is forbidden on the intraday horizon.",
    )
    assert field.horizon_guard == "EOD_ONLY"


def test_mcx_profile_blocker_requires_ready_context(tmp_path, monkeypatch) -> None:
    assert mcx_profile_blocker(None) == "WAIT_MCX_MASTER"
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r11-blocker.db")
    storage._INITIALIZED_DB_PATHS.clear()
    batch = build_mcx_master()
    assert mcx_profile_blocker(batch) == "WAIT_MCX_MASTER"


# ---------------------------------------------------------------------------
# §4.7 HTTP surface
# ---------------------------------------------------------------------------


def test_post_routes_are_405(tmp_path, monkeypatch) -> None:
    client = TestClient(app)
    assert client.post("/api/v1/selection/mcx-master").status_code == 405
    assert client.post("/api/v1/selection/mcx-master/GOLDM").status_code == 405


def test_symbol_route_404_named(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r11-sym.db")
    storage._INITIALIZED_DB_PATHS.clear()
    client = TestClient(app)
    response = client.get("/api/v1/selection/mcx-master/NOSUCH")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "R11_SYMBOL_NOT_FOUND"


def test_no_place_order_in_module() -> None:
    from pathlib import Path

    source = Path(
        r"D:\TrendForge\backend\trendforge_api\selection\r11_mcx_live.py"
    ).read_text(encoding="utf-8")
    assert "place_order" not in source
