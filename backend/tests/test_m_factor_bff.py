"""Acceptance tests for the M-Factor read-only BFF (GET /api/v1/tools/m_factor).

Contract: docs/fable/remaining_build/M_FACTOR_LIVE_UI_OPENCODE_PROMPT.md §6 and
docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md §1D. The BFF projects two
FUS-009 hypotheses per symbol; it must not invent a second score, geometry,
a win rate or a CONFIRMED state.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.market_data_service import NormalizedSourceResult
from trendforge_api.market_data_store import ManifestStatus, MarketDataStore
from trendforge_api.selection.cash_post_commit import (
    CashPipelineRunContext,
    run_existing_cash_pipeline,
)
from trendforge_api.selection.m_factor_bff import (
    assign_board,
    build_m_factor_batch,
    directional_class,
)

TRADE_DATE = date(2026, 8, 14)
NOW = datetime(2026, 8, 14, 16, 5, tzinfo=UTC)

BHAV_RECORDS = [
    {
        "tradeDate": TRADE_DATE.isoformat(),
        "symbol": "RELIANCE",
        "series": "EQ",
        "isin": "INE002A01018",
        "open": 1400,
        "high": 1440,
        "low": 1390,
        "close": 1430,
        "previousClose": 1400,
        "volume": 1000000,
        "tradedValue": 1430000000,
    },
    {
        "tradeDate": TRADE_DATE.isoformat(),
        "symbol": "INFY",
        "series": "EQ",
        "isin": "INE009A01021",
        "open": 1560,
        "high": 1565,
        "low": 1520,
        "close": 1530,
        "previousClose": 1558,
        "volume": 900000,
        "tradedValue": 1380000000,
    },
    {
        "tradeDate": TRADE_DATE.isoformat(),
        "symbol": "TCS",
        "series": "EQ",
        "isin": "INE467B01029",
        "open": 4100,
        "high": 4140,
        "low": 4080,
        "close": 4110,
        "previousClose": 4102,
        "volume": 400000,
        "tradedValue": 1640000000,
    },
]


def _result(
    source_key: str,
    status: ManifestStatus,
    *,
    rows: int = 1,
    digest: str = "a" * 64,
) -> NormalizedSourceResult:
    return NormalizedSourceResult(
        source_key=source_key,
        normalized_source_key=source_key,
        status=status,
        parser_state="PARSED_STRUCTURED",
        http_status=200,
        fetched_at=NOW,
        data_date=TRADE_DATE,
        normalized_row_count=rows,
        normalized_content_hash=digest,
        stored_attempt_id=1,
    )


def _commit_cash(store: MarketDataStore) -> None:
    payload = {
        "sourceKey": "nse_bhavcopy_eod",
        "parserState": "PARSED_STRUCTURED",
        "dataDate": TRADE_DATE.isoformat(),
        "records": BHAV_RECORDS,
    }
    store.commit_success(
        run_id="collector-m-factor",
        source_key="nse_bhavcopy_eod",
        trading_date=TRADE_DATE,
        slot="eod",
        attempted_at=NOW,
        fetched_at=NOW,
        data_date=TRADE_DATE,
        source_url="https://example.test/cash.csv",
        http_status=200,
        media_type="application/vnd.trendforge.normalized+json",
        content=json.dumps(payload, sort_keys=True).encode(),
        extension="json",
        normalized_row_count=len(BHAV_RECORDS),
        retry_count=0,
    )


@pytest.fixture()
def live_lineage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Persist a real R1->R5 cash lineage and point storage at it."""
    store = MarketDataStore(root=tmp_path / "market-data", db_path=tmp_path / "market.db")
    _commit_cash(store)
    monkeypatch.setattr(storage, "DB_PATH", store.db_path)
    storage._INITIALIZED_DB_PATHS.clear()
    run_existing_cash_pipeline(
        CashPipelineRunContext(
            store=store,
            collector_run_id="collector-m-factor-bff",
            trading_date=TRADE_DATE,
            results={},
            trigger_source_keys=("nse_bhavcopy_eod",),
            fingerprint="6" * 64,
        )
    )


def _all_rows(payload: dict) -> list[dict]:
    return payload["buyRows"] + payload["sellRows"] + payload["waitRows"]


def test_two_hypotheses_equal_own_resolve_runs_and_subsume_r3(live_lineage) -> None:
    """FMR-010.1 under the 2026-08-23 contract: long/short equal the BFF's own
    two resolve_evidence runs over merged claims (cash + any hash-matched R5
    structure). The persisted thin R3 row stays a lower bound plus a debug
    comparison field, never the definition."""
    with TestClient(app) as client:
        bff = client.get("/api/v1/tools/m_factor", params={"horizon": "swing", "debug": 1})
        r3 = client.get("/api/v1/selection/resolution")
        assert bff.status_code == 200, bff.text
        assert r3.status_code == 200, r3.text
        payload = bff.json()
        resolution = r3.json()

    rows_by_symbol = {row["symbol"]: row for row in _all_rows(payload)}
    assert rows_by_symbol, "BFF returned no rows"
    for r3_row in resolution["rows"]:
        row = rows_by_symbol.get(r3_row["symbol"])
        assert row is not None, f"missing symbol {r3_row['symbol']}"
        expected = round(r3_row["evidenceStrength"] * 100, 2)
        assert row["r3EvidenceStrength"] == expected
        # This fixture lineage has one bar day, so R5 mints no structure
        # claims and the merged set equals the thin R3 claim set exactly.
        if r3_row["evidenceDirection"] == "BULLISH":
            assert row["longStrength"] == expected
            assert row["shortStrength"] == 0.0
        elif r3_row["evidenceDirection"] == "BEARISH":
            assert row["shortStrength"] == expected
            assert row["longStrength"] == 0.0
        # No bonus stacking; mBalance/rank derive from the two hypotheses.
        assert row["rankStrength"] == max(row["longStrength"], row["shortStrength"])
        assert row["mBalance"] == round(row["longStrength"] - row["shortStrength"], 2)


def test_readiness_requires_a_structure_vote(live_lineage) -> None:
    """This fixture lineage has no R5 setups, so SETUP_READY must not appear."""
    with TestClient(app) as client:
        payload = client.get("/api/v1/tools/m_factor", params={"horizon": "swing"}).json()
    for row in _all_rows(payload):
        assert row["readinessTag"] != "SETUP_READY"
        assert row["how"].startswith(("STRUCTURE_NOT_EVALUATED", "STRUCTURE_WITHHELD"))
        assert row["what"] in {
            "UNKNOWN_NO_LARGE_DEAL_ROW",
        } or row["what"].startswith(("NAMED_DEAL", "DEAL_UNNAMED_OR_UNALIGNED"))


def test_duplicate_activity_cannot_raise_rank(live_lineage) -> None:
    batch = build_m_factor_batch(horizon="swing", side="both", limit=40)
    for row in batch.buy_rows + batch.sell_rows + batch.wait_rows:
        assert 0.0 <= row.long_strength <= 100.0
        assert 0.0 <= row.short_strength <= 100.0
        assert len(set(row.selected_support_claim_ids)) == len(row.selected_support_claim_ids)
        assert len(set(row.selected_opposition_claim_ids)) == len(row.selected_opposition_claim_ids)


def test_directional_class_bands_are_version_v0() -> None:
    assert directional_class(80) == "Strong Bull"
    assert directional_class(60) == "Strong Bull"
    assert directional_class(59.99) == "Bull"
    assert directional_class(20) == "Bull"
    assert directional_class(19.99) == "Neutral"
    assert directional_class(0) == "Neutral"
    assert directional_class(-19.99) == "Neutral"
    assert directional_class(-20) == "Bear"
    assert directional_class(-59.99) == "Bear"
    assert directional_class(-60) == "Strong Bear"
    assert directional_class(-90) == "Strong Bear"


def test_board_assignment_rules() -> None:
    # Strong Bull + hard gate stays WAIT: class can never override the gate.
    assert assign_board(80, 5, "Strong Bull", public_state="WAIT")[0] == "buy"
    assert assign_board(80, 5, "Strong Bull", public_state="REJECT")[0] == "wait"
    assert assign_board(80, 5, "Strong Bull", public_state="WAIT", index_conflict=True)[0] == "wait"
    # Neutral / unresolved never takes a side.
    assert assign_board(15, 10, "Neutral", public_state="WAIT")[0] == "wait"
    assert assign_board(10, 10, "Neutral", public_state="WAIT")[0] == "wait"
    # SELL is symmetric and never dual-seated with BUY.
    assert assign_board(5, 75, "Strong Bear", public_state="WAIT")[0] == "sell"
    assert assign_board(5, 75, "Bear", public_state="WAIT")[0] == "sell"
    # Class must agree with the winning side.
    assert assign_board(70, 5, "Bear", public_state="WAIT")[0] == "wait"


def test_class_readiness_state_stay_separate(live_lineage) -> None:
    with TestClient(app) as client:
        payload = client.get(
            "/api/v1/tools/m_factor", params={"horizon": "swing", "debug": 1}
        ).json()
    classes = {"Strong Bull", "Bull", "Neutral", "Bear", "Strong Bear"}
    readiness = {"DEVELOPING", "SETUP_READY", "EXPIRED", "INVALIDATED"}
    states = {"WATCH", "WAIT", "REJECT"}
    for row in _all_rows(payload):
        assert row["directionalClass"] in classes
        assert row["readinessTag"] in readiness
        assert row["publicState"] in states
        assert row["publicState"] != "CONFIRMED"
        assert row["whyWait"], "every live row must name its blockers"
        assert row["nextProof"]
    assert payload["stateCeiling"] == "WAIT"
    assert payload["sourceActivationReady"] is False
    assert payload["canUnlockConfirmed"] is False
    assert payload["classVersion"] == "M_FACTOR_CLASS_V0"
    assert payload["calibration"] == "UNCALIBRATED_M_FACTOR_CLASS_V0"
    if payload["buyRows"] or payload["sellRows"]:
        assert all(row["publicState"] != "CONFIRMED" for row in _all_rows(payload))


def test_rows_carry_no_trade_geometry(live_lineage) -> None:
    batch = build_m_factor_batch(horizon="swing", side="both", limit=40)
    for row in batch.buy_rows + batch.sell_rows + batch.wait_rows:
        assert row.entry is None and row.stop is None
        assert row.t1 is None and row.t2 is None and row.quantity is None


def test_intra_horizon_is_empty_with_wait_code(live_lineage) -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/tools/m_factor", params={"horizon": "intra"})
        assert response.status_code == 200
        payload = response.json()
    assert payload["horizon"] == "intra"
    assert payload["horizonWaitCode"] == "WAIT_HORIZON_INTRADAY_NOT_ACTIVATED"
    assert payload["buyRows"] == []
    assert payload["sellRows"] == []
    assert payload["waitRows"] == []
    assert "WAIT_HORIZON_INTRADAY_NOT_ACTIVATED" in payload["warnings"]


def test_position_and_commodity_horizons_fail_closed(live_lineage) -> None:
    with TestClient(app) as client:
        position = client.get("/api/v1/tools/m_factor", params={"horizon": "position"}).json()
        commodity = client.get("/api/v1/tools/m_factor", params={"horizon": "commodity"}).json()
    assert position["horizonWaitCode"] == "WAIT_HORIZON_POSITION_NOT_WIRED"
    assert commodity["horizonWaitCode"] == "WAIT_HORIZON_COMMODITY_MCX_LOCAL_NOT_WIRED"
    for payload in (position, commodity):
        assert payload["buyRows"] == [] and payload["sellRows"] == [] and payload["waitRows"] == []


def test_track_record_is_locked(live_lineage) -> None:
    with TestClient(app) as client:
        payload = client.get("/api/v1/tools/m_factor").json()
    track = payload["track"]
    assert track["state"] == "PIT_NOT_VALIDATED"
    assert track["sampleCount"] == 0
    assert track["winRate"] is None
    assert track["benchmarkDelta"] is None


def test_post_is_rejected(live_lineage) -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/tools/m_factor")
    assert response.status_code == 405


def test_unknown_horizon_or_side_is_rejected(live_lineage) -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/tools/m_factor", params={"horizon": "scalp"}).status_code == 422
        assert client.get("/api/v1/tools/m_factor", params={"side": "both&"}).status_code == 422


def test_side_filter_does_not_change_calculation(live_lineage) -> None:
    with TestClient(app) as client:
        both = client.get("/api/v1/tools/m_factor", params={"side": "both"}).json()
        sell = client.get("/api/v1/tools/m_factor", params={"side": "sell"}).json()
    assert sell["sideFilter"] == "sell"
    assert sell["buyRows"] == []
    assert sell["sellRows"] == both["sellRows"]


def test_limit_is_applied_per_board(live_lineage) -> None:
    batch = build_m_factor_batch(horizon="swing", side="both", limit=1)
    assert len(batch.buy_rows) <= 1
    assert len(batch.sell_rows) <= 1
    assert len(batch.wait_rows) <= 1


def test_mixed_hashes_return_503_with_code(live_lineage, monkeypatch: pytest.MonkeyPatch) -> None:
    from trendforge_api.selection import m_factor_bff
    from trendforge_api.selection.r3_live import latest_r3_resolution

    resolution = latest_r3_resolution()
    assert resolution is not None

    monkeypatch.setattr(m_factor_bff, "latest_r3_resolution", lambda: None)
    with TestClient(app) as client:
        missing = client.get("/api/v1/tools/m_factor")
    assert missing.status_code == 503
    assert missing.json()["detail"]["code"] == "R3_RESOLUTION_NOT_READY"

    mismatch = resolution.model_copy(update={"r1_bundle_hash": "mismatch"})
    monkeypatch.setattr(m_factor_bff, "latest_r3_resolution", lambda: mismatch)
    with TestClient(app) as client:
        blocked = client.get("/api/v1/tools/m_factor")
    assert blocked.status_code == 503
    assert blocked.json()["detail"]["code"] == "WAIT_MIXED_SNAPSHOT"


def test_live_dto_has_no_fixture_values(live_lineage) -> None:
    with TestClient(app) as client:
        payload = client.get("/api/v1/tools/m_factor", params={"debug": 1}).json()
    serialized = json.dumps(payload)
    assert "FIXTURE" not in serialized
    assert "168.9" not in serialized
    assert "175.2" not in serialized
    assert "165.1" not in serialized
    assert payload["runId"] != "FIXTURE-20260729-1042"
    assert payload["warnings"], "warnings must include evidence-not-probability"
    assert any("not win probability" in warning for warning in payload["warnings"])


def test_debug_includes_fus009_family_detail(live_lineage) -> None:
    with TestClient(app) as client:
        payload = client.get("/api/v1/tools/m_factor", params={"debug": 1}).json()
    for row in _all_rows(payload):
        families = {item["family"]: item for item in row["families"]}
        assert families["STRUCTURE"]["weight"] == 0.30
        assert families["PARTICIPATION"]["weight"] == 0.25
        assert families["TRADABILITY_AND_SAFETY"]["weight"] == 0.20
        assert families["MARKET_AND_SECTOR_CONTEXT"]["weight"] == 0.15
        assert families["EVENT_AND_SPONSOR"]["weight"] == 0.10
