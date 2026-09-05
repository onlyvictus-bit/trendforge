"""Acceptance tests for GET /api/v1/tools/oi_tracker.

Contract: prompt section 8. Fewer than two comparable observations stays
WAIT_PATH; a missing chain surface degrades PCR to UNKNOWN (never 0 or
infinity) and the row state to WAIT_CHAIN; roll-aware windows are on.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from trendforge_api.main import app
from trendforge_api.options_intelligence.bff import build_oi_tracker_batch
from trendforge_api.selection.fo_a6_enrichment import (
    FoContractSlice,
    FoEnrichmentBatch,
    FoEnrichmentRow,
)

client = TestClient(app)


def _slice(oi: int, symbol: str = "RELIANCE") -> FoContractSlice:
    return FoContractSlice(
        symbol=symbol,
        instrument_class="FUTURE",
        expiry="2026-09-29",
        close=3000.0,
        previous_close=2990.0,
        open_interest=oi,
        oi_change=10_000,
        oi_quadrant="NEUTRAL_OR_UNKNOWN",
        volume=500_000,
    )


def _run(data_date: str, oi: int, symbol: str = "RELIANCE") -> FoEnrichmentBatch:
    return FoEnrichmentBatch(
        batch_id=f"run-{data_date}",
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        artifact_hash="c" * 64,
        row_count=1,
        rows=(
            FoEnrichmentRow(
                symbol=symbol,
                shortlisted=True,
                fo_state="FUTURES_OK",
                near_future=_slice(oi, symbol),
                option_oi_used=False,
                note="test",
            ),
        ),
    )


def test_single_observation_stays_wait_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff.list_fo_enrichment_history",
        lambda limit: [_run("2026-08-21", 2_000_000)],
    )
    payload = build_oi_tracker_batch()
    assert payload.rows[0].observations == 1
    assert payload.rows[0].oi_path_label == "UNKNOWN"
    assert payload.rows[0].public_state == "WAIT_PATH"


def test_rising_path_and_unknown_pcr_without_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history = [
        _run("2026-08-20", 1_900_000),
        _run("2026-08-21", 2_000_000),
        _run("2026-08-22", 2_100_000),
    ]
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff.list_fo_enrichment_history",
        lambda limit: history,
    )
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff.chain_snapshots",
        lambda **kwargs: [],
    )
    payload = build_oi_tracker_batch()
    row = payload.rows[0]
    assert row.observations == 3
    assert row.oi_path_label == "RISING"
    assert row.pcr_open is None and row.pcr_current is None
    assert row.public_state == "WAIT_CHAIN"
    assert row.can_confirm is False


def test_falling_path_with_chain_pcr(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from trendforge_api import storage
    from trendforge_api.options_intelligence.iv_recorder import record_chain_snapshot

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "market.db")
    storage._INITIALIZED_DB_PATHS.clear()
    history = [
        _run("2026-08-21", 2_200_000),
        _run("2026-08-22", 2_100_000),
    ]
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff.list_fo_enrichment_history",
        lambda limit: history,
    )
    rows = [
        {"expiry": "2026-09-29", "strike": 3000.0, "right": "CE", "openInterest": 100.0, "volume": 10.0},
        {"expiry": "2026-09-29", "strike": 3000.0, "right": "PE", "openInterest": 50.0, "volume": 5.0},
    ]
    record_chain_snapshot(
        underlying="RELIANCE",
        expiry="2026-09-29",
        quality_state="CHAIN_OK",
        spot=2995.0,
        payload={"rows": rows, "expectedStrikeCount": 1},
    )
    payload = build_oi_tracker_batch()
    row = payload.rows[0]
    assert row.oi_path_label == "FALLING"
    assert row.pcr_open is not None and row.pcr_current is not None


def test_zero_call_denominator_is_unknown(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from trendforge_api import storage
    from trendforge_api.options_intelligence.surface import pcr_oi

    assert pcr_oi(put_oi=100.0, call_oi=0.0) is None
    assert pcr_oi(put_oi=0.0, call_oi=None) is None


def test_route_rejects_post() -> None:
    assert client.post("/api/v1/tools/oi_tracker").status_code == 405
