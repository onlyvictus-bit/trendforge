from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from trendforge_api.main import app
from trendforge_api.openalgo_identity import (
    InstrumentIdentityQuery,
    InstrumentKind,
    OpenAlgoInstrumentContract,
    OpenAlgoInstrumentMapper,
)
from trendforge_api.openalgo_shadow import (
    ActivationStage,
    OpenAlgoActivationEvidenceV1,
    OpenAlgoBaseCandidateV1,
    OpenAlgoOptionSnapshotV1,
    OpenAlgoRestObservationV1,
    OpenAlgoShadowRuntime,
    OptionApplicability,
    assess_openalgo_activation,
    build_openalgo_shadow_batch,
    build_option_purpose_votes,
)
from trendforge_api.openalgo_stream import OpenAlgoStreamManager, StreamState
from trendforge_api.options_intelligence.chain_quality import StrikeQuote
from trendforge_api.selection.research_quantity import compute_research_quantity


NOW = datetime(2026, 8, 31, 10, 0, tzinfo=UTC)
RAW_HASH = "a" * 64
REPLAY_HASH = "b" * 64
BASE_HASH = "c" * 64


def _activation(**changes):
    values = {
        "enabled": True,
        "contract_pinned": True,
        "fixture_verified": True,
        "live_observation_approved": False,
        "rest_observed": False,
        "rest_replay_verified": False,
        "stream_observed": False,
        "reconnect_verified": False,
        "stream_replay_verified": False,
        "provider_sequence_available": False,
    }
    values.update(changes)
    return assess_openalgo_activation(OpenAlgoActivationEvidenceV1(**values))


def _identity():
    contract = OpenAlgoInstrumentContract(
        exchange="NSE",
        segment="CASH",
        symbol="RELIANCE",
        broker_symbol="RELIANCE-EQ",
        token="2885",
        name="RELIANCE INDUSTRIES",
        instrument_kind=InstrumentKind.EQUITY,
        lot_size=1,
        tick_size=0.05,
        unit="SHARE",
        source_version="master-fixture-v1",
    )
    mapper = OpenAlgoInstrumentMapper((contract,))
    return mapper.resolve(
        InstrumentIdentityQuery(
            exchange="NSE", symbol="RELIANCE", as_of=NOW.date()
        )
    )


def _base(**changes):
    values = {
        "symbol": "RELIANCE",
        "base_public_state": "WATCH",
        "evidence_direction": "BULLISH",
        "draft_confirmed_eligible": True,
        "invalidation_condition": "95",
        "atr": 2.0,
        "is_reject_or_ban": False,
        "completeness_ratio": 1.0,
        "regime_label": "RISK_ON",
        "index_suspect": False,
        "base_row_hash": BASE_HASH,
        "fno_eligible": True,
    }
    values.update(changes)
    return OpenAlgoBaseCandidateV1(**values)


def _rest(**changes):
    values = {
        "quality_state": "VALID_POPULATED",
        "last_price": 100.0,
        "data_at": NOW,
        "received_at": NOW,
        "max_age_seconds": 120,
        "raw_content_hash": RAW_HASH,
        "replay_content_hash": REPLAY_HASH,
        "route": "/api/v1/quotes",
    }
    values.update(changes)
    return OpenAlgoRestObservationV1(**values)


def _rows():
    return (
        StrikeQuote(
            expiry="24-SEP-26",
            strike=95,
            right="CE",
            bid=7.0,
            ask=7.2,
            ltp=7.1,
            open_interest=1_000,
            volume=500,
            implied_volatility=22,
        ),
        StrikeQuote(
            expiry="24-SEP-26",
            strike=95,
            right="PE",
            bid=1.9,
            ask=2.0,
            ltp=1.95,
            open_interest=1_800,
            volume=700,
            implied_volatility=23,
        ),
        StrikeQuote(
            expiry="24-SEP-26",
            strike=105,
            right="CE",
            bid=2.1,
            ask=2.2,
            ltp=2.15,
            open_interest=2_000,
            volume=900,
            implied_volatility=24,
        ),
        StrikeQuote(
            expiry="24-SEP-26",
            strike=105,
            right="PE",
            bid=6.8,
            ask=7.0,
            ltp=6.9,
            open_interest=1_200,
            volume=600,
            implied_volatility=25,
        ),
    )


def _option_snapshot(**changes):
    values = {
        "applicable": True,
        "underlying": "RELIANCE",
        "exchange": "NFO",
        "expiry": date(2026, 9, 24),
        "captured_at": NOW,
        "max_age_seconds": 300,
        "spot": 100,
        "years_to_expiry": 24 / 365,
        "lot_size": 250,
        "expected_strike_count": 2,
        "rows": _rows(),
        "iv_percentile": 82,
        "snapshot_id": "chain-snapshot-1",
        "dataset_root_id": "openalgo-optionchain-NFO-RELIANCE-24SEP26",
        "raw_content_hash": RAW_HASH,
    }
    values.update(changes)
    return OpenAlgoOptionSnapshotV1(**values)


def test_r17_i_disabled_is_inert():
    activation = assess_openalgo_activation(OpenAlgoActivationEvidenceV1())
    assert activation.stage is ActivationStage.DISABLED
    assert activation.network_allowed is False
    assert activation.storage_allowed is False
    assert activation.projection_allowed is False


def test_r17_i_configuration_is_not_shadow_live():
    activation = _activation(live_observation_approved=True)
    assert activation.stage is ActivationStage.FIXTURE_VERIFIED
    assert activation.shadow_live is False
    assert "WAIT_REST_OBSERVATION" in activation.blocker_codes


def test_r17_i_rest_requires_replay():
    activation = _activation(rest_observed=True, rest_replay_verified=False)
    assert activation.stage is ActivationStage.FIXTURE_VERIFIED
    assert "WAIT_REST_REPLAY" in activation.blocker_codes


def test_r17_i_stream_observation_without_provider_sequence_cannot_go_live():
    activation = _activation(
        live_observation_approved=True,
        rest_observed=True,
        rest_replay_verified=True,
        stream_observed=True,
        reconnect_verified=True,
        stream_replay_verified=True,
    )
    assert activation.stage is ActivationStage.STREAM_SHADOW_OBSERVED
    assert activation.shadow_live is False
    assert "WAIT_STREAM_SEQUENCE_UNAVAILABLE" in activation.blocker_codes


def test_r17_i_full_proof_can_reach_shadow_live():
    activation = _activation(
        live_observation_approved=True,
        rest_observed=True,
        rest_replay_verified=True,
        stream_observed=True,
        reconnect_verified=True,
        stream_replay_verified=True,
        provider_sequence_available=True,
    )
    assert activation.stage is ActivationStage.SHADOW_LIVE
    assert activation.shadow_live is True
    assert activation.executable is False


def test_r17_i_disable_stops_stream_and_preserves_base_hash():
    manager = OpenAlgoStreamManager(enabled=True)
    manager.begin_connect(at=NOW)
    runtime = OpenAlgoShadowRuntime(
        base_payload={"runId": "r1-r16", "rows": [{"symbol": "RELIANCE"}]},
        stream_manager=manager,
    )
    before = runtime.base_output_hash
    rollback = runtime.disable()
    assert rollback.before_base_hash == rollback.after_base_hash == before
    assert rollback.stream_state == StreamState.STOPPED
    assert rollback.network_activity_after_disable == 0
    assert rollback.storage_activity_after_disable == 0


def test_r17_i_disabled_runtime_rejects_network_and_storage_activity():
    runtime = OpenAlgoShadowRuntime(base_payload={"rows": []})
    runtime.disable()
    with pytest.raises(RuntimeError, match="disabled"):
        runtime.note_network_activity()
    with pytest.raises(RuntimeError, match="disabled"):
        runtime.note_storage_activity()


def test_r17_h_non_fno_votes_are_not_applicable():
    votes, concentration = build_option_purpose_votes(
        _option_snapshot(applicable=False, rows=())
    )
    assert len(votes) == 7
    assert {vote.applicability for vote in votes} == {
        OptionApplicability.NOT_APPLICABLE
    }
    assert concentration.independent_confirmation_count == 0


def test_r17_h_partial_or_crossed_chain_waits_all_votes():
    crossed = list(_rows())
    crossed[0] = crossed[0].model_copy(update={"bid": 8.0, "ask": 7.0})
    votes, _ = build_option_purpose_votes(
        _option_snapshot(rows=tuple(crossed))
    )
    assert {vote.applicability for vote in votes} == {
        OptionApplicability.WAIT_PARTIAL_CHAIN
    }


def test_r17_h_votes_are_unique_but_share_one_lineage():
    votes, concentration = build_option_purpose_votes(_option_snapshot())
    assert len(votes) == 7
    assert len({vote.vote_id for vote in votes}) == 7
    assert {vote.dataset_root_id for vote in votes} == {
        "openalgo-optionchain-NFO-RELIANCE-24SEP26"
    }
    assert {vote.snapshot_id for vote in votes} == {"chain-snapshot-1"}
    assert concentration.vote_count == 7
    assert concentration.dataset_root_count == 1
    assert concentration.independent_confirmation_count == 0


def test_r17_h_pcr_zero_denominator_is_unavailable():
    rows = tuple(row.model_copy(update={"open_interest": 0}) if row.right == "CE" else row for row in _rows())
    votes, _ = build_option_purpose_votes(_option_snapshot(rows=rows))
    pcr = next(vote for vote in votes if vote.vote_id == "OPTION_PCR_CROWDING")
    assert pcr.applicability is OptionApplicability.UNAVAILABLE
    assert pcr.raw_value is None


def test_r17_h_gamma_is_never_dealer_positioning():
    votes, _ = build_option_purpose_votes(_option_snapshot())
    gamma = next(vote for vote in votes if vote.vote_id == "OPTION_GAMMA_FRAGILITY")
    serialized = gamma.model_dump_json().casefold()
    assert "unsigned" in serialized
    assert "dealer positioning" not in serialized
    assert gamma.can_confirm is False


def test_r17_h_projection_never_changes_base_state_or_confirms():
    activation = _activation(
        rest_observed=True,
        rest_replay_verified=True,
    )
    batch = build_openalgo_shadow_batch(
        base_run_hash=BASE_HASH,
        candidates=(_base(),),
        activation=activation,
        identities={"RELIANCE": _identity()},
        rest_observations={"RELIANCE": _rest()},
        option_snapshots={"RELIANCE": _option_snapshot()},
        as_of=NOW,
    )
    row = batch.rows[0]
    assert row.base_public_state == "WATCH"
    assert row.public_state == "WATCH"
    assert row.openalgo_profile_state in {"WATCH", "WAIT"}
    assert batch.confirmed_count == 0
    assert batch.base_output_unchanged is True
    assert batch.executable is False


def test_r17_h_stale_rest_blocks_profile_and_quantity():
    activation = _activation(rest_observed=True, rest_replay_verified=True)
    stale = _rest(
        data_at=NOW - timedelta(minutes=10),
        received_at=NOW - timedelta(minutes=10),
        max_age_seconds=120,
    )
    batch = build_openalgo_shadow_batch(
        base_run_hash=BASE_HASH,
        candidates=(_base(),),
        activation=activation,
        identities={"RELIANCE": _identity()},
        rest_observations={"RELIANCE": stale},
        option_snapshots={},
        as_of=NOW,
    )
    row = batch.rows[0]
    assert row.openalgo_profile_state == "WAIT"
    assert row.research_quantity == 0
    assert "WAIT_REST_STALE" in row.missing_or_conflicting


def test_r17_h_quantity_uses_costs_and_does_not_double_count_lot():
    no_cost = compute_research_quantity(
        public_state="WAIT",
        evidence_direction="BULLISH",
        draft_confirmed_eligible=True,
        is_reject_or_ban=False,
        official_close=100,
        invalidation_condition="95",
        atr=2,
        lot_size=25,
        s8_completeness_ratio=1,
        regime_label="RISK_ON",
        index_suspect=False,
        research_capital_inr=100_000,
        slippage_per_share=0,
    )
    with_cost = compute_research_quantity(
        public_state="WAIT",
        evidence_direction="BULLISH",
        draft_confirmed_eligible=True,
        is_reject_or_ban=False,
        official_close=100,
        invalidation_condition="95",
        atr=2,
        lot_size=25,
        s8_completeness_ratio=1,
        regime_label="RISK_ON",
        index_suspect=False,
        research_capital_inr=100_000,
        slippage_per_share=1,
    )
    assert no_cost["researchQuantity"] % 25 == 0
    assert no_cost["notionalInr"] == no_cost["researchQuantity"] * 100
    assert with_cost["researchQuantity"] <= no_cost["researchQuantity"]


def test_r17_h_api_is_read_only_and_disabled_by_default(monkeypatch):
    monkeypatch.delenv("OPENALGO_ENABLED", raising=False)
    client = TestClient(app)
    response = client.get("/api/v1/integrations/openalgo/shadow")
    assert response.status_code == 200
    payload = response.json()
    assert payload["activation"]["stage"] == "DISABLED"
    assert payload["rows"] == []
    assert payload["executable"] is False
    assert client.post("/api/v1/integrations/openalgo/shadow").status_code == 405


def test_r17_i_enabled_configuration_cannot_activate_data_lane(monkeypatch):
    monkeypatch.setenv("OPENALGO_ENABLED", "1")
    monkeypatch.setenv("TRENDFORGE_DATA_LANE", "OPENALGO_RO")
    client = TestClient(app)
    shadow = client.get("/api/v1/integrations/openalgo/shadow").json()
    lane = client.get("/api/v1/settings/data-lane").json()
    assert shadow["activation"]["stage"] == "FIXTURE_VERIFIED"
    assert lane["effectiveLane"] == "FREE_OFFICIAL"
    assert lane["openAlgoState"] == "FIXTURE_VERIFIED"
    assert lane["blocker"] == "WAIT_OPENALGO_ABSENT"
    assert lane["canConfirm"] is False
    assert lane["executable"] is False
