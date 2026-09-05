from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256

from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api.main import app
from trendforge_api.selection import (
    EnrichmentBudget,
    EnrichmentCandidate,
    EnrichmentJob,
    InstrumentIdentity,
    MCXContractMasterEntry,
    MCXLocalObservation,
    MCXReadiness,
    MCXRuleStatus,
    SelectionState,
    build_enrichment_plan,
    build_q5_r1_fixture_batch,
    build_q5_r4_fixture_batch,
    evaluate_mcx_contract,
    evaluate_option_chain,
)
from trendforge_api.source_contracts import (
    SourceResult,
    SourceResultState,
    SourceRole,
)


IST = timezone(timedelta(hours=5, minutes=30))
SNAPSHOT_AT = datetime(2026, 7, 18, 15, 30, tzinfo=IST)
DECISION_AT = datetime(2026, 7, 19, 9, 0, tzinfo=IST)
EXPIRY = date(2026, 7, 30)


def _source(
    source_id: str,
    *,
    data_date: date | None = None,
) -> SourceResult:
    return SourceResult(
        source_id=source_id,
        contract_version="1.0.0",
        role=SourceRole.OFFICIAL_GATE,
        state=SourceResultState.STRUCTURED_OK,
        record_count=10,
        data_date=data_date or SNAPSHOT_AT.date(),
        published_at=SNAPSHOT_AT,
        received_at=SNAPSHOT_AT + timedelta(seconds=1),
        available_at=SNAPSHOT_AT,
        retrieved_at=SNAPSHOT_AT + timedelta(seconds=2),
        schema_version="q5-r4-test-schema-1",
        parser_version="q5-r4-test-parser-1",
        revision_id="q5-r4-test-revision-1",
        artifact_hash=sha256(source_id.encode()).hexdigest(),
        freshness="FRESH",
        can_support_confirmed=True,
        state_ceiling="CONFIRMED",
    )


def _nse(symbol: str) -> InstrumentIdentity:
    return InstrumentIdentity.create(
        exchange="NSE",
        segment="EQUITY",
        symbol=symbol,
        series="EQ",
        tick_size=0.05,
    )


def _mcx(*, expiry: date = date(2026, 8, 5)) -> InstrumentIdentity:
    return InstrumentIdentity.create(
        exchange="MCX",
        segment="FUTCOM",
        symbol="GOLDM",
        contract=f"GOLDM{expiry.strftime('%d%b%Y').upper()}FUT",
        expiry=expiry,
        lot_size=100,
        tick_size=0.1,
    )


def _master(instrument: InstrumentIdentity) -> MCXContractMasterEntry:
    return MCXContractMasterEntry(
        instrument=instrument,
        master_revision="MCX-MASTER-2026-07-18-V1",
        calendar_version="MCX-CALENDAR-2026-V1",
        tender_rule_status=MCXRuleStatus.DATED,
        delivery_rule_status=MCXRuleStatus.DATED,
        tender_start=date(2026, 8, 1),
        delivery_start=date(2026, 8, 3),
        available_at=SNAPSHOT_AT,
    )


def _observation(instrument: InstrumentIdentity) -> MCXLocalObservation:
    return MCXLocalObservation(
        instrument_id=instrument.instrument_id,
        observed_at=SNAPSHOT_AT,
        close=73_500.0,
        volume=2_000.0,
        open_interest=8_000.0,
        source_fact_id=f"fact-{instrument.instrument_id}",
    )


def _option_rows(expiry: date = EXPIRY) -> tuple[dict, ...]:
    rows: list[dict] = []
    values = {
        100.0: {"CE": 100.0, "PE": 50.0},
        110.0: {"CE": 200.0, "PE": 300.0},
        120.0: {"CE": 500.0, "PE": 200.0},
    }
    for strike, sides in values.items():
        for option_type, open_interest in sides.items():
            rows.append(
                {
                    "expiry": expiry,
                    "strike": strike,
                    "option_type": option_type,
                    "bid": 9.5,
                    "ask": 10.0,
                    "ltp": 9.8,
                    "open_interest": open_interest,
                    "volume": 1_000.0,
                    "implied_volatility": 0.20,
                }
            )
    return tuple(rows)


def _option_assessment(
    rows: tuple[dict, ...],
    *,
    source_id: str = "SRC-NSE-OPTIONS",
    expiry: date = EXPIRY,
    required: bool = True,
):
    return evaluate_option_chain(
        underlying=_nse("TF_OPTION"),
        source_result=_source(source_id),
        snapshot_at=SNAPSHOT_AT,
        decision_at=DECISION_AT,
        expiry=expiry,
        spot=110.0,
        multiplier=50.0,
        expected_strike_count=3,
        raw_rows=rows,
        required=required,
    )


def _mcx_assessment(
    *,
    instrument: InstrumentIdentity | None = None,
    master: MCXContractMasterEntry | None = None,
    observation: MCXLocalObservation | None = None,
    master_result: SourceResult | None = None,
    local_result: SourceResult | None = None,
    calendar_result: SourceResult | None = None,
    synthetic_continuous: bool = False,
):
    selected = instrument or _mcx()
    return evaluate_mcx_contract(
        requested_instrument=selected,
        master_entry=master if master is not None else _master(selected),
        local_observation=(
            observation if observation is not None else _observation(selected)
        ),
        master_result=(
            master_result if master_result is not None else _source("SRC-MCX-MASTER")
        ),
        local_result=(
            local_result if local_result is not None else _source("SRC-MCX-EOD")
        ),
        calendar_result=(
            calendar_result
            if calendar_result is not None
            else _source("SRC-MCX-CALENDAR")
        ),
        decision_at=DECISION_AT,
        synthetic_continuous=synthetic_continuous,
    )


def test_q5_r4_fixture_enforces_unknown_and_non_execution_boundaries() -> None:
    batch = build_q5_r4_fixture_batch()
    assert batch.fixture_only is True
    assert batch.production_authorized is False
    assert batch.executable is False
    assert batch.enrichment_plan.selected_count == 2
    assert [item.state for item in batch.option_assessments] == [
        SelectionState.WATCH,
        SelectionState.WAIT,
        SelectionState.WAIT,
        SelectionState.WAIT,
        SelectionState.WAIT,
    ]
    assert [item.state for item in batch.mcx_assessments] == [
        SelectionState.WATCH,
        SelectionState.WAIT,
        SelectionState.WAIT,
        SelectionState.REJECT,
        SelectionState.REJECT,
    ]


def test_enrichment_budget_caps_candidates_and_jobs() -> None:
    batch = build_q5_r4_fixture_batch()
    plan = batch.enrichment_plan
    assert len(plan.assignments) == plan.budget.max_candidates == 2
    assert all(
        0 < len(item.jobs) <= plan.budget.max_jobs_per_candidate
        for item in plan.assignments
    )


def test_enrichment_plan_is_deterministic_under_input_reordering() -> None:
    candidates = tuple(
        EnrichmentCandidate(
            candidate_id=f"C-{index}",
            instrument=_nse(f"TF_{index}"),
            state=SelectionState.WAIT if index < 2 else SelectionState.WATCH,
            discovery_priority=priority,
            requested_jobs=(EnrichmentJob.OPTION_CHAIN,),
        )
        for index, priority in enumerate((0.6, 0.9, 1.0))
    )
    budget = EnrichmentBudget(
        budget_id="BUD-TEST",
        budget_version="1",
        max_candidates=2,
        max_jobs_per_candidate=1,
        allowed_jobs=(EnrichmentJob.OPTION_CHAIN,),
    )
    forward = build_enrichment_plan(candidates=candidates, budget=budget)
    reverse = build_enrichment_plan(
        candidates=tuple(reversed(candidates)), budget=budget
    )
    assert forward.assignments == reverse.assignments


def test_enrichment_excludes_terminal_states_and_candidates_without_allowed_jobs() -> (
    None
):
    candidates = (
        EnrichmentCandidate(
            candidate_id="NO-ALLOWED-JOB",
            instrument=_nse("TF_NONE"),
            state=SelectionState.WAIT,
            discovery_priority=1.0,
            requested_jobs=(EnrichmentJob.MCX_CONTRACT,),
        ),
        EnrichmentCandidate(
            candidate_id="ELIGIBLE",
            instrument=_nse("TF_ELIGIBLE"),
            state=SelectionState.WATCH,
            discovery_priority=0.5,
            requested_jobs=(EnrichmentJob.OPTION_CHAIN,),
        ),
        EnrichmentCandidate(
            candidate_id="CONFIRMED",
            instrument=_nse("TF_CONFIRMED"),
            state=SelectionState.CONFIRMED,
            discovery_priority=1.0,
            requested_jobs=(EnrichmentJob.OPTION_CHAIN,),
        ),
        EnrichmentCandidate(
            candidate_id="REJECT",
            instrument=_nse("TF_REJECT"),
            state=SelectionState.REJECT,
            discovery_priority=1.0,
            requested_jobs=(EnrichmentJob.OPTION_CHAIN,),
        ),
    )
    budget = EnrichmentBudget(
        budget_id="BUD-FILTER",
        budget_version="1",
        max_candidates=4,
        max_jobs_per_candidate=1,
        allowed_jobs=(EnrichmentJob.OPTION_CHAIN,),
    )
    plan = build_enrichment_plan(candidates=candidates, budget=budget)
    assert [item.candidate_id for item in plan.assignments] == ["ELIGIBLE"]
    assert set(plan.excluded_candidate_ids) == {
        "NO-ALLOWED-JOB",
        "CONFIRMED",
        "REJECT",
    }


def test_enrichment_queue_priority_is_not_serialized_as_evidence() -> None:
    assignment = build_q5_r4_fixture_batch().enrichment_plan.assignments[0]
    payload = assignment.model_dump(mode="json", by_alias=True)
    assert set(payload) == {"candidateId", "instrumentId", "queueRank", "jobs"}
    assert "strength" not in str(payload).lower()
    assert "probability" not in str(payload).lower()


def test_valid_option_snapshot_derives_only_context_metrics() -> None:
    result = _option_assessment(_option_rows())
    assert result.state is SelectionState.WATCH
    assert result.can_support_confirmed is False
    assert result.metrics is not None
    assert result.metrics.pcr_oi == 0.6875
    assert result.metrics.call_wall == 120.0
    assert result.metrics.put_wall == 110.0
    assert result.metrics.max_pain == 110.0
    assert result.metrics.completeness == 1.0


def test_incomplete_option_chain_waits_without_partial_metrics() -> None:
    rows = tuple(
        row
        for row in _option_rows()
        if not (row["strike"] == 120.0 and row["option_type"] == "PE")
    )
    result = _option_assessment(rows)
    assert result.state is SelectionState.WAIT
    assert result.metrics is None
    assert "INCOMPLETE_STRIKE_SET" in result.null_reasons
    assert "WAIT_OPTION_CHAIN_INCOMPLETE" in {gate.code for gate in result.gate_results}


def test_crossed_option_quote_waits() -> None:
    rows = list(_option_rows())
    rows[0] = {**rows[0], "bid": 11.0, "ask": 10.0}
    result = _option_assessment(tuple(rows))
    assert result.state is SelectionState.WAIT
    assert result.metrics is None
    assert "WAIT_OPTION_QUOTE_DOMAIN" in {gate.code for gate in result.gate_results}


def test_mixed_option_expiry_waits() -> None:
    rows = list(_option_rows())
    rows[0] = {**rows[0], "expiry": date(2026, 8, 27)}
    result = _option_assessment(tuple(rows))
    assert result.state is SelectionState.WAIT
    assert "WAIT_OPTION_MIXED_EXPIRY" in {gate.code for gate in result.gate_results}


def test_expired_option_snapshot_waits() -> None:
    expired = date(2026, 7, 18)
    result = _option_assessment(_option_rows(expired), expiry=expired)
    assert result.state is SelectionState.WAIT
    assert "WAIT_OPTION_EXPIRED" in {gate.code for gate in result.gate_results}


def test_zero_call_oi_keeps_pcr_unknown() -> None:
    rows = tuple(
        {**row, "open_interest": 0.0} if row["option_type"] == "CE" else row
        for row in _option_rows()
    )
    result = _option_assessment(rows)
    assert result.state is SelectionState.WAIT
    assert result.metrics is None
    assert "CE_OI_DENOMINATOR_ZERO" in result.null_reasons


def test_duplicate_option_contract_waits_instead_of_double_counting() -> None:
    rows = _option_rows()
    result = _option_assessment(rows + (rows[0],))
    assert result.state is SelectionState.WAIT
    assert result.metrics is None
    assert "WAIT_OPTION_DUPLICATE_CONTRACT" in {
        gate.code for gate in result.gate_results
    }


def test_wrong_option_source_contract_waits() -> None:
    result = _option_assessment(_option_rows(), source_id="SRC-NSE-EOD")
    assert result.state is SelectionState.WAIT
    assert "OPTION_SOURCE_ID_MISMATCH" in result.null_reasons
    assert "WAIT_OPTION_SOURCE_IDENTITY" in {gate.code for gate in result.gate_results}


def test_optional_invalid_option_context_is_explicit_but_nonblocking() -> None:
    result = _option_assessment((), required=False)
    assert result.state is SelectionState.WAIT
    assert result.metrics is None
    assert result.gate_results
    assert all(gate.required is False for gate in result.gate_results)
    assert all(gate.blocks_confirmed is False for gate in result.gate_results)


def test_gex_proxy_remains_postponed() -> None:
    result = _option_assessment(_option_rows())
    assert result.metrics is not None
    assert result.metrics.gex_proxy_status == "POSTPONED_GEX_PROXY"


def test_complete_mcx_local_context_is_watch_only() -> None:
    result = _mcx_assessment()
    assert result.state is SelectionState.WATCH
    assert result.readiness is MCXReadiness.MASTER_AND_LOCAL_CONTEXT_READY
    assert result.can_support_confirmed is False
    assert result.state_ceiling.value == "WAIT"


def test_missing_mcx_master_is_wait_with_unknown_contract_fields() -> None:
    instrument = _mcx()
    result = evaluate_mcx_contract(
        requested_instrument=instrument,
        master_entry=None,
        local_observation=_observation(instrument),
        master_result=None,
        local_result=_source("SRC-MCX-EOD"),
        calendar_result=_source("SRC-MCX-CALENDAR"),
        decision_at=DECISION_AT,
    )
    assert result.state is SelectionState.WAIT
    assert {"expiry", "lot_size", "tick_size", "tender_rules"}.issubset(
        result.unknown_fields
    )


def test_missing_mcx_local_price_and_oi_is_wait() -> None:
    instrument = _mcx()
    result = evaluate_mcx_contract(
        requested_instrument=instrument,
        master_entry=_master(instrument),
        local_observation=None,
        master_result=_source("SRC-MCX-MASTER"),
        local_result=None,
        calendar_result=_source("SRC-MCX-CALENDAR"),
        decision_at=DECISION_AT,
    )
    assert result.state is SelectionState.WAIT
    assert {"local_price", "local_open_interest"}.issubset(result.unknown_fields)


def test_wrong_mcx_source_identity_waits() -> None:
    result = _mcx_assessment(master_result=_source("SRC-WRONG-MASTER"))
    assert result.state is SelectionState.WAIT
    assert "SRC-MCX-MASTER" in result.unknown_fields
    assert "WAIT_MCX_SOURCE_IDENTITY_SRC-MCX-MASTER" in {
        gate.code for gate in result.gate_results
    }


def test_mcx_local_observation_must_match_source_date() -> None:
    result = _mcx_assessment(
        local_result=_source("SRC-MCX-EOD", data_date=date(2026, 7, 17))
    )
    assert result.state is SelectionState.WAIT
    assert "local_source_date_alignment" in result.unknown_fields
    assert "WAIT_MCX_LOCAL_SOURCE_DATE_MISMATCH" in {
        gate.code for gate in result.gate_results
    }


def test_expired_mcx_contract_is_rejected() -> None:
    instrument = _mcx(expiry=date(2026, 7, 18))
    result = _mcx_assessment(
        instrument=instrument,
        master=MCXContractMasterEntry(
            instrument=instrument,
            master_revision="MCX-MASTER-EXPIRED",
            calendar_version="MCX-CALENDAR-2026-V1",
            tender_rule_status=MCXRuleStatus.DATED,
            delivery_rule_status=MCXRuleStatus.DATED,
            tender_start=date(2026, 7, 15),
            delivery_start=date(2026, 7, 17),
            available_at=SNAPSHOT_AT,
        ),
        observation=_observation(instrument),
    )
    assert result.state is SelectionState.REJECT
    assert result.readiness is MCXReadiness.INVALID


def test_synthetic_continuous_mcx_series_is_rejected() -> None:
    result = _mcx_assessment(synthetic_continuous=True)
    assert result.state is SelectionState.REJECT
    assert "REJECT_MCX_SYNTHETIC_CONTINUOUS" in {
        gate.code for gate in result.gate_results
    }


def test_mcx_master_rejects_missing_lot_and_tick() -> None:
    instrument = InstrumentIdentity.create(
        exchange="MCX",
        segment="FUTCOM",
        symbol="GOLDM",
        contract="GOLDM05AUG2026FUT",
        expiry=date(2026, 8, 5),
    )
    try:
        MCXContractMasterEntry(
            instrument=instrument,
            master_revision="MCX-MASTER-MISSING-FIELDS",
            calendar_version="MCX-CALENDAR-2026-V1",
            tender_rule_status=MCXRuleStatus.NOT_APPLICABLE,
            delivery_rule_status=MCXRuleStatus.NOT_APPLICABLE,
            available_at=SNAPSHOT_AT,
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("MCX master without lot/tick must be rejected")


def test_mcx_master_requires_explicit_tender_and_delivery_semantics() -> None:
    instrument = _mcx()
    try:
        MCXContractMasterEntry(
            instrument=instrument,
            master_revision="MCX-MASTER-MISSING-RULES",
            calendar_version="MCX-CALENDAR-2026-V1",
            available_at=SNAPSHOT_AT,
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("missing tender/delivery semantics must be rejected")


def test_mcx_not_applicable_rules_cannot_carry_dates() -> None:
    instrument = _mcx()
    try:
        MCXContractMasterEntry(
            instrument=instrument,
            master_revision="MCX-MASTER-CONTRADICTORY-RULES",
            calendar_version="MCX-CALENDAR-2026-V1",
            tender_rule_status=MCXRuleStatus.NOT_APPLICABLE,
            delivery_rule_status=MCXRuleStatus.NOT_APPLICABLE,
            tender_start=date(2026, 8, 1),
            available_at=SNAPSHOT_AT,
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("contradictory tender semantics must be rejected")


def test_q5_r4_api_is_non_executable_and_exposes_no_probability_or_order_fields() -> (
    None
):
    response = TestClient(app).get("/api/v1/selection/fixtures/q5-r4")
    assert response.status_code == 200
    payload = response.json()
    assert payload["milestone"] == "Q5-R4"
    assert payload["fixtureOnly"] is True
    assert payload["productionAuthorized"] is False
    assert payload["executable"] is False
    for forbidden in (
        "tradeDirection",
        "entry",
        "stop",
        "target",
        "quantity",
        "orderIntent",
        "winProbability",
        "winRate",
    ):
        assert forbidden not in response.text


def test_public_selection_exports_preserve_q5_r1_and_q5_r4_builders() -> None:
    assert build_q5_r1_fixture_batch().milestone == "Q5-R1"
    assert build_q5_r4_fixture_batch().milestone == "Q5-R4"
