from __future__ import annotations

from pydantic import ValidationError
from fastapi.testclient import TestClient

from trendforge_api.main import app
from trendforge_api.selection import (
    ClosedBar,
    DataMode,
    EvidenceDirection,
    EvidenceFamily,
    GateOutcome,
    InstrumentIdentity,
    ResolutionProfile,
    SelectionState,
    analyze_closed_bar_structure,
    build_fixture_bars,
    build_q5_r3_fixture_batch,
    resolve_evidence,
)
from trendforge_api.selection.r3_fixtures import (
    R3_AS_OF,
    R3_RESOLUTION_PROFILE,
    R3_STRUCTURE_PROFILE,
)


def _decision(symbol: str):
    batch = build_q5_r3_fixture_batch()
    return batch, next(
        decision for decision in batch.decisions if decision.instrument.symbol == symbol
    )


def _instrument(symbol: str) -> InstrumentIdentity:
    return InstrumentIdentity.create(
        exchange="NSE",
        segment="EQUITY",
        symbol=symbol,
        series="EQ",
        tick_size=0.05,
    )


def _resolve_custom(
    *,
    symbol: str,
    scenario: str = "BREAKOUT",
    data_mode: DataMode = DataMode.EOD_RESEARCH,
    adjustment_version: str = "ADJ-TEST-V1",
    bars_limit: int | None = None,
):
    batch = build_q5_r3_fixture_batch()
    source_result = batch.source_results[0]
    instrument = _instrument(symbol)
    bars = build_fixture_bars(
        instrument,
        scenario=scenario,
        data_mode=data_mode,
        adjustment_version=adjustment_version,
    )
    if bars_limit is not None:
        bars = bars[:bars_limit]
    analysis = analyze_closed_bar_structure(
        instrument=instrument,
        bars=bars,
        source_result=source_result,
        profile=R3_STRUCTURE_PROFILE,
        decision_at=R3_AS_OF,
    )
    resolution = resolve_evidence(
        profile=R3_RESOLUTION_PROFILE,
        decision_at=R3_AS_OF,
        evidence_direction=EvidenceDirection.BULLISH,
        claims=analysis.claims,
        facts=(analysis.fact,),
        source_results=(source_result,),
        completeness=1.0,
        existing_gates=analysis.gate_results,
        data_mode=data_mode,
    )
    return bars, analysis, resolution


def test_q5_r3_fixture_covers_four_states_with_one_eod_confirmation() -> None:
    batch = build_q5_r3_fixture_batch()
    assert {decision.state for decision in batch.decisions} == set(SelectionState)
    confirmed = [
        decision
        for decision in batch.decisions
        if decision.state is SelectionState.CONFIRMED
    ]
    assert len(confirmed) == 1
    assert confirmed[0].data_mode is DataMode.EOD_RESEARCH
    assert confirmed[0].fixture_only is True
    assert confirmed[0].production_authorized is False
    assert confirmed[0].research_priority_only is True
    assert confirmed[0].executable is False


def test_closed_breakout_uses_prior_bars_and_separate_rvol_family() -> None:
    batch, decision = _decision("TF_R3_CONFIRMED")
    index = batch.decisions.index(decision)
    analysis = batch.analyses[index]
    resolution = batch.resolutions[index]

    assert analysis.metrics.accepted is True
    assert analysis.metrics.relative_volume == 2.0
    assert set(analysis.metrics.reference_bar_ids).isdisjoint(
        analysis.metrics.acceptance_bar_ids
    )
    assert EvidenceFamily.STRUCTURE in resolution.family_supports
    assert EvidenceFamily.PARTICIPATION in resolution.family_supports
    assert all(claim.can_support_confirmed for claim in analysis.claims)


def test_unclosed_acceptance_bar_waits_and_emits_no_confirming_claim() -> None:
    batch, decision = _decision("TF_R3_WAIT_OPEN")
    index = batch.decisions.index(decision)
    analysis = batch.analyses[index]

    assert decision.state is SelectionState.WAIT
    assert "WAIT_BAR_NOT_CLOSED" in {gate.code for gate in decision.gate_results}
    assert not any(claim.can_support_confirmed for claim in analysis.claims)


def test_breakout_without_rvol_waits_for_independent_participation() -> None:
    batch, decision = _decision("TF_R3_WAIT_RVOL")
    index = batch.decisions.index(decision)
    analysis = batch.analyses[index]

    assert analysis.metrics.accepted is True
    assert analysis.metrics.relative_volume == 1.1
    assert decision.state is SelectionState.WAIT
    assert "WAIT_REQUIRED_FAMILY_PARTICIPATION" in {
        gate.code for gate in decision.gate_results
    }


def test_nr7_compression_is_watch_only() -> None:
    batch, decision = _decision("TF_R3_WATCH_NR7")
    index = batch.decisions.index(decision)
    analysis = batch.analyses[index]
    compression = next(
        claim for claim in analysis.claims if claim.feature_id == "FTR-007"
    )

    assert decision.state is SelectionState.WATCH
    assert analysis.metrics.narrow_range is True
    assert compression.can_support_confirmed is False


def test_deterministic_invalidation_rejects() -> None:
    _batch, decision = _decision("TF_R3_REJECT")
    assert decision.state is SelectionState.REJECT
    assert any(
        gate.code == "REJECT_STRUCTURE_INVALIDATED"
        and gate.outcome is GateOutcome.REJECT
        for gate in decision.gate_results
    )


def test_intraday_mode_cannot_confirm_in_q5_r3() -> None:
    _bars, _analysis, resolution = _resolve_custom(
        symbol="TF_R3_INTRADAY",
        data_mode=DataMode.PUBLIC_INTRADAY_RESEARCH,
    )
    assert resolution.state is SelectionState.WAIT
    assert "WAIT_DATA_MODE" in resolution.gate_codes


def test_unresolved_adjustment_waits() -> None:
    _bars, analysis, resolution = _resolve_custom(
        symbol="TF_R3_UNADJUSTED",
        adjustment_version="UNRESOLVED",
    )
    assert analysis.fact.quality_state == "INPUT_INCOMPLETE"
    assert resolution.state is SelectionState.WAIT
    assert "WAIT_ADJUSTMENT_UNRESOLVED" in resolution.gate_codes


def test_insufficient_history_is_not_treated_as_empty_or_zero() -> None:
    _bars, analysis, resolution = _resolve_custom(
        symbol="TF_R3_SHORT_HISTORY",
        bars_limit=5,
    )
    assert analysis.metrics.reference_level is None
    assert analysis.metrics.relative_volume is None
    assert resolution.state is SelectionState.WAIT
    assert "WAIT_INSUFFICIENT_HISTORY" in resolution.gate_codes


def test_zero_volume_baseline_is_unknown_and_waits() -> None:
    batch = build_q5_r3_fixture_batch()
    source_result = batch.source_results[0]
    instrument = _instrument("TF_R3_ZERO_BASELINE")
    original = build_fixture_bars(instrument, scenario="BREAKOUT")
    bars = tuple(
        bar.model_copy(update={"volume": 0.0 if index < len(original) - 1 else 2000.0})
        for index, bar in enumerate(original)
    )
    analysis = analyze_closed_bar_structure(
        instrument=instrument,
        bars=bars,
        source_result=source_result,
        profile=R3_STRUCTURE_PROFILE,
        decision_at=R3_AS_OF,
    )
    resolution = resolve_evidence(
        profile=R3_RESOLUTION_PROFILE,
        decision_at=R3_AS_OF,
        evidence_direction=EvidenceDirection.BULLISH,
        claims=analysis.claims,
        facts=(analysis.fact,),
        source_results=(source_result,),
        completeness=1.0,
        existing_gates=analysis.gate_results,
        data_mode=DataMode.EOD_RESEARCH,
    )
    assert analysis.metrics.relative_volume is None
    assert resolution.state is SelectionState.WAIT
    assert "WAIT_RVOL_BASELINE_UNKNOWN" in resolution.gate_codes


def test_malformed_ohlc_is_rejected_before_feature_calculation() -> None:
    instrument = _instrument("TF_R3_BAD_OHLC")
    bar = build_fixture_bars(instrument, scenario="BREAKOUT")[0]
    try:
        ClosedBar(
            identity=bar.identity,
            open=100,
            high=99,
            low=98,
            close=101,
            volume=1000,
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("invalid OHLC must not enter the feature engine")


def test_confirmed_profile_requires_independent_families_and_sources() -> None:
    try:
        ResolutionProfile(
            profile_id="PRF-INVALID-CONFIRM",
            profile_version="1",
            family_weights={EvidenceFamily.STRUCTURE: 1.0},
            state_ceiling="CONFIRMED",
            allowed_data_modes=(DataMode.EOD_RESEARCH,),
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("CONFIRMED profile must name families and sources")


def test_duplicate_session_identity_waits() -> None:
    batch = build_q5_r3_fixture_batch()
    source_result = batch.source_results[0]
    instrument = _instrument("TF_R3_DUPLICATE_SESSION")
    original = build_fixture_bars(instrument, scenario="BREAKOUT")
    duplicate_identity = original[1].identity.model_copy(
        update={"session_id": original[0].identity.session_id}
    )
    bars = (
        original[0],
        original[1].model_copy(update={"identity": duplicate_identity}),
        *original[2:],
    )
    analysis = analyze_closed_bar_structure(
        instrument=instrument,
        bars=bars,
        source_result=source_result,
        profile=R3_STRUCTURE_PROFILE,
        decision_at=R3_AS_OF,
    )
    assert "WAIT_BAR_IDENTITY" in {gate.code for gate in analysis.gate_results}


def test_q5_r3_api_is_non_executable_and_has_no_trade_or_probability_fields() -> None:
    response = TestClient(app).get("/api/v1/selection/fixtures/q5-r3")
    assert response.status_code == 200
    payload = response.json()
    assert payload["milestone"] == "Q5-R3"
    assert payload["fixtureOnly"] is True
    assert payload["productionAuthorized"] is False
    assert payload["executable"] is False
    assert {decision["state"] for decision in payload["decisions"]} == {
        "WATCH",
        "WAIT",
        "CONFIRMED",
        "REJECT",
    }
    for forbidden in (
        "tradeDirection",
        "entry",
        "stop",
        "target",
        "quantity",
        "orderIntent",
        "winProbability",
    ):
        assert forbidden not in response.text
