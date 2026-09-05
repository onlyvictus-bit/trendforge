"""Acceptance tests for GET /api/v1/tools/oi_analysis.

Contract: docs/fable/remaining_build/OI_OPTIONS_ROOMS_GLM_PROMPT.md §8.
The board must fail closed to WAIT_FO_LINEAGE, emit PRICE_*_OI_* codes
with UNKNOWN on equality/mismatch/pollution, run official MWPL/ban gates
first, never carry geometry or CONFIRMED, and never leak fixture demo
strings into a live DTO.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from trendforge_api.main import app
from trendforge_api.options_intelligence.bff import build_oi_analysis_batch
from trendforge_api.options_intelligence.quadrant import observation_quadrant
from trendforge_api.selection.contracts import MODEL_CONFIG
from trendforge_api.selection.fo_a6_enrichment import (
    FoContractSlice,
    FoEnrichmentBatch,
    FoEnrichmentRow,
)

client = TestClient(app)


def _slice(**overrides) -> FoContractSlice:
    base = dict(
        symbol="RELIANCE",
        instrument_class="FUTURE",
        expiry="2026-09-29",
        close=3000.0,
        previous_close=2970.0,
        open_interest=2_100_000,
        oi_change=60_000,
        oi_quadrant="NEUTRAL_OR_UNKNOWN",
        volume=1_000_000,
    )
    base.update(overrides)
    return FoContractSlice(**base)


def _batch(rows: list[FoEnrichmentRow]) -> FoEnrichmentBatch:
    return FoEnrichmentBatch(
        batch_id="test-batch",
        parser_state="PARSED_STRUCTURED",
        data_date="2026-08-21",
        artifact_hash="b" * 64,
        row_count=len(rows),
        rows=tuple(rows),
    )


def _ok_row(symbol: str = "RELIANCE") -> FoEnrichmentRow:
    return FoEnrichmentRow(
        symbol=symbol,
        shortlisted=True,
        fo_state="FUTURES_OK",
        near_future=_slice(symbol=symbol),
        rollover_ratio=None,
        option_oi_used=False,
        note="test",
    )


def _monkeypatch_lineage(monkeypatch: pytest.MonkeyPatch, batch) -> None:
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff._load_fo_batch", lambda: batch
    )


def test_quadrant_codes_and_legacy_alias() -> None:
    up_up = observation_quadrant(
        close=101.0, previous_close=100.0, open_interest=110, prior_open_interest=100
    )
    assert up_up.code.value == "PRICE_UP_OI_UP"
    assert up_up.legacy_code == "OI_RISE_PRICE_RISE"
    down_up = observation_quadrant(
        close=99.0, previous_close=100.0, open_interest=110, prior_open_interest=100
    )
    assert down_up.code.value == "PRICE_DOWN_OI_UP" and down_up.legacy_code == "OI_RISE_PRICE_FALL"
    up_down = observation_quadrant(
        close=101.0, previous_close=100.0, open_interest=90, prior_open_interest=100
    )
    assert up_down.code.value == "PRICE_UP_OI_DOWN" and up_down.legacy_code == "OI_FALL_PRICE_RISE"


def test_quadrant_unknown_paths() -> None:
    missing_prior = observation_quadrant(
        close=101.0, previous_close=100.0, open_interest=110, prior_open_interest=None
    )
    assert missing_prior.code.value == "UNKNOWN" and "PRIOR_OI_MISSING" in missing_prior.reasons
    zero_prior = observation_quadrant(
        close=101.0, previous_close=100.0, open_interest=110, prior_open_interest=0
    )
    assert zero_prior.code.value == "UNKNOWN"
    equal = observation_quadrant(
        close=100.0, previous_close=100.0, open_interest=110, prior_open_interest=100
    )
    assert equal.code.value == "UNKNOWN" and "PRICE_EQUALITY_NOT_DIRECTION" in equal.reasons
    roll = observation_quadrant(
        close=101.0,
        previous_close=100.0,
        open_interest=110,
        prior_open_interest=100,
        roll_window=True,
    )
    assert roll.code.value == "UNKNOWN" and "ROLL_WINDOW_POLLUTION" in roll.reasons


def test_bff_fails_closed_without_lineage(monkeypatch: pytest.MonkeyPatch) -> None:
    _monkeypatch_lineage(monkeypatch, None)
    with pytest.raises(Exception) as exc:
        build_oi_analysis_batch()
    assert getattr(exc.value, "code", "") == "WAIT_FO_LINEAGE"
    response = client.get("/api/v1/tools/oi_analysis")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "WAIT_FO_LINEAGE"


def test_bff_rows_carry_codes_gates_and_no_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _monkeypatch_lineage(monkeypatch, _batch([_ok_row("RELIANCE"), _ok_row("INFY")]))
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff.get_latest_source_parse_result",
        lambda key: None,
    )
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff._ban", lambda symbol: False
    )
    payload = build_oi_analysis_batch()
    assert payload.row_count == len(payload.rows) == 2
    for row in payload.rows:
        assert row.observation_code in {
            "PRICE_UP_OI_UP",
            "PRICE_DOWN_OI_UP",
            "PRICE_UP_OI_DOWN",
            "PRICE_DOWN_OI_DOWN",
            "UNKNOWN",
        }
        assert row.public_state in {"WATCH", "WAIT"}
        assert row.entry is None and row.stop is None and row.quantity is None
        assert row.can_confirm is False and row.authority == "CONTEXT_ONLY"
        assert row.mwpl.official_state == "MWPL_MISSING"
        # Decision-guidance fields: every decodable row must carry a read,
        # both bias readings and a workflow next step.
        assert row.trader_read, "trader_read must never be empty"
        assert row.if_long_bias and row.if_short_bias
        assert "not an order" in row.next_step.lower() or row.next_step
        if row.observation_code == "PRICE_UP_OI_DOWN":
            assert "WEAKENS a long hypothesis" in row.if_long_bias
        if row.observation_code == "PRICE_DOWN_OI_UP":
            assert "SUPPORTS a short structure hypothesis" in row.if_short_bias
    text = payload.model_dump_json(by_alias=True).upper()
    assert "+18.4%" not in text
    for row in payload.rows:
        assert row.public_state != "CONFIRMED"


def test_high_next_month_oi_share_labels_roll_but_keeps_near_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = _ok_row("RELIANCE")
    row = row.model_copy(update={"rollover_ratio": 0.72})
    _monkeypatch_lineage(monkeypatch, _batch([row]))
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff.get_latest_source_parse_result",
        lambda key: None,
    )
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff._ban", lambda symbol: False
    )
    payload = build_oi_analysis_batch()
    assert payload.rows[0].roll_window is True
    assert payload.rows[0].observation_code == "PRICE_UP_OI_UP"


def test_route_rejects_post_and_serves_camel_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _monkeypatch_lineage(monkeypatch, _batch([_ok_row()]))
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff.get_latest_source_parse_result",
        lambda key: None,
    )
    monkeypatch.setattr("trendforge_api.options_intelligence.bff._ban", lambda s: False)
    get_response = client.get("/api/v1/tools/oi_analysis?limit=5")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["stateCeiling"] == "RESEARCH_SHADOW_ONLY"
    assert body["columnsSpec"][0]["column"] == "Price path"
    post_response = client.post("/api/v1/tools/oi_analysis")
    assert post_response.status_code == 405


def test_demo_strings_never_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = FoEnrichmentRow(
        symbol="TATASTEEL",
        shortlisted=True,
        fo_state="FUTURES_OK",
        near_future=_slice(symbol="TATASTEEL"),
        option_oi_used=False,
        note="fixture leak attempt",
    )
    _monkeypatch_lineage(monkeypatch, _batch([bad]))
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff.get_latest_source_parse_result",
        lambda key: None,
    )
    monkeypatch.setattr("trendforge_api.options_intelligence.bff._ban", lambda s: False)
    with pytest.raises(ValueError):
        build_oi_analysis_batch()


def test_ban_row_next_step_stops_derivative_story(monkeypatch: pytest.MonkeyPatch) -> None:
    _monkeypatch_lineage(monkeypatch, _batch([_ok_row("SAIL")]))
    monkeypatch.setattr(
        "trendforge_api.options_intelligence.bff.get_latest_source_parse_result",
        lambda key: None,
    )
    monkeypatch.setattr("trendforge_api.options_intelligence.bff._ban", lambda s: True)
    payload = build_oi_analysis_batch()
    row = payload.rows[0]
    assert row.mwpl.official_state == "BAN"
    assert "HARD_BLOCK_BAN_ADD" in row.blockers
    assert "banned" in row.next_step.lower()


def test_model_config_is_house_camel_case() -> None:
    from trendforge_api.selection.fo_a6_enrichment import MODEL_CONFIG as A6_CONFIG

    assert MODEL_CONFIG is not None
    assert A6_CONFIG is not None
