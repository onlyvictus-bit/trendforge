"""Q5-R4 fixture batch: bounded enrichment, MCX gates, options domain.

This is NOT live File A R4 (PK0 pin + ID inventory). Live R4 is `r4_live.py`.
Do not treat this fixture as identity, CA history, or a PK runtime.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, model_validator

from ..source_contracts import SourceResult, SourceResultState, SourceRole
from .contracts import InstrumentIdentity, MODEL_CONFIG, SelectionState
from .enrichment import (
    EnrichmentBudget,
    EnrichmentCandidate,
    EnrichmentJob,
    EnrichmentPlan,
    build_enrichment_plan,
)
from .mcx_contracts import (
    MCXContractAssessment,
    MCXContractMasterEntry,
    MCXLocalObservation,
    MCXRuleStatus,
    evaluate_mcx_contract,
)
from .options_domain import OptionDomainAssessment, evaluate_option_chain


IST = timezone(timedelta(hours=5, minutes=30))
R4_AS_OF = datetime(2026, 7, 19, 9, 0, tzinfo=IST)
R4_SNAPSHOT_AT = datetime(2026, 7, 18, 15, 30, tzinfo=IST)
R4_EXPIRY = date(2026, 7, 30)


class Q5R4FixtureBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: Literal["Q5-R4"] = "Q5-R4"
    acceptance_ceiling: Literal["UNKNOWN_EXPLICIT_NO_MCX_CONFIRMED"] = (
        "UNKNOWN_EXPLICIT_NO_MCX_CONFIRMED"
    )
    fixture_only: Literal[True] = True
    production_authorized: Literal[False] = False
    executable: Literal[False] = False
    enrichment_plan: EnrichmentPlan
    option_assessments: tuple[OptionDomainAssessment, ...]
    mcx_assessments: tuple[MCXContractAssessment, ...]

    @model_validator(mode="after")
    def enforce_r4_boundary(self) -> "Q5R4FixtureBatch":
        if any(item.can_support_confirmed for item in self.option_assessments):
            raise ValueError("static option context cannot confirm")
        if any(item.state is SelectionState.CONFIRMED for item in self.mcx_assessments):
            raise ValueError("Q5-R4 MCX fixture cannot confirm")
        if any(
            item.metrics and item.metrics.gex_proxy_status != "POSTPONED_GEX_PROXY"
            for item in self.option_assessments
        ):
            raise ValueError("GEX proxy must remain postponed")
        return self


def _digest(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


def _source_result(source_id: str, label: str) -> SourceResult:
    return SourceResult(
        source_id=source_id,
        contract_version="1.0.0",
        role=SourceRole.OFFICIAL_GATE,
        state=SourceResultState.STRUCTURED_OK,
        record_count=10,
        data_date=R4_SNAPSHOT_AT.date(),
        published_at=R4_SNAPSHOT_AT,
        received_at=R4_SNAPSHOT_AT + timedelta(seconds=1),
        available_at=R4_SNAPSHOT_AT,
        retrieved_at=R4_SNAPSHOT_AT + timedelta(seconds=2),
        schema_version="q5-r4-fixture-schema-1",
        parser_version="q5-r4-fixture-parser-1",
        revision_id="q5-r4-fixture-1",
        artifact_hash=_digest(label),
        freshness="FRESH",
        can_support_confirmed=True,
        state_ceiling="CONFIRMED",
    )


def _nse_instrument(symbol: str) -> InstrumentIdentity:
    return InstrumentIdentity.create(
        exchange="NSE",
        segment="EQUITY",
        symbol=symbol,
        series="EQ",
        tick_size=0.05,
    )


def _option_rows(expiry: date) -> tuple[dict, ...]:
    rows: list[dict] = []
    values = {
        100.0: {"CE": 100.0, "PE": 50.0},
        110.0: {"CE": 200.0, "PE": 300.0},
        120.0: {"CE": 500.0, "PE": 200.0},
    }
    for strike, sides in values.items():
        for option_type, oi in sides.items():
            rows.append(
                {
                    "expiry": expiry,
                    "strike": strike,
                    "option_type": option_type,
                    "bid": 9.5,
                    "ask": 10.0,
                    "ltp": 9.8,
                    "open_interest": oi,
                    "volume": 1000.0,
                    "implied_volatility": 0.20,
                }
            )
    return tuple(rows)


def _build_enrichment_fixture() -> EnrichmentPlan:
    candidates = (
        EnrichmentCandidate(
            candidate_id="R4-WAIT-OPTIONS",
            instrument=_nse_instrument("TF_R4_WAIT"),
            state=SelectionState.WAIT,
            discovery_priority=0.80,
            requested_jobs=(
                EnrichmentJob.OPTION_CHAIN,
                EnrichmentJob.DERIVATIVES_OI,
                EnrichmentJob.CORPORATE_EVENTS,
            ),
        ),
        EnrichmentCandidate(
            candidate_id="R4-WATCH-EVENT",
            instrument=_nse_instrument("TF_R4_WATCH"),
            state=SelectionState.WATCH,
            discovery_priority=0.95,
            requested_jobs=(
                EnrichmentJob.CORPORATE_EVENTS,
                EnrichmentJob.DELIVERY,
            ),
        ),
        EnrichmentCandidate(
            candidate_id="R4-REJECTED",
            instrument=_nse_instrument("TF_R4_REJECT"),
            state=SelectionState.REJECT,
            discovery_priority=1.0,
            requested_jobs=(EnrichmentJob.OPTION_CHAIN,),
        ),
        EnrichmentCandidate(
            candidate_id="R4-CONFIRMED-NO-REQUERY",
            instrument=_nse_instrument("TF_R4_CONFIRMED"),
            state=SelectionState.CONFIRMED,
            discovery_priority=1.0,
            requested_jobs=(EnrichmentJob.OPTION_CHAIN,),
        ),
    )
    budget = EnrichmentBudget(
        budget_id="BUD-Q5-R4-FIXTURE",
        budget_version="1.0.0",
        max_candidates=2,
        max_jobs_per_candidate=2,
        allowed_jobs=(
            EnrichmentJob.OPTION_CHAIN,
            EnrichmentJob.DERIVATIVES_OI,
            EnrichmentJob.CORPORATE_EVENTS,
            EnrichmentJob.DELIVERY,
        ),
    )
    return build_enrichment_plan(candidates=candidates, budget=budget)


def _build_option_fixtures() -> tuple[OptionDomainAssessment, ...]:
    source = _source_result("SRC-NSE-OPTIONS", "q5-r4-option-chain")
    underlying = _nse_instrument("TF_R4_OPTION")
    complete = _option_rows(R4_EXPIRY)
    incomplete = tuple(
        row
        for row in complete
        if not (row["strike"] == 120.0 and row["option_type"] == "PE")
    )
    crossed = list(complete)
    crossed[0] = {**crossed[0], "bid": 11.0, "ask": 10.0}
    mixed = list(complete)
    mixed[0] = {**mixed[0], "expiry": date(2026, 8, 27)}
    expired = date(2026, 7, 18)
    cases = (
        (R4_EXPIRY, complete),
        (R4_EXPIRY, incomplete),
        (R4_EXPIRY, tuple(crossed)),
        (R4_EXPIRY, tuple(mixed)),
        (expired, _option_rows(expired)),
    )
    return tuple(
        evaluate_option_chain(
            underlying=underlying,
            source_result=source,
            snapshot_at=R4_SNAPSHOT_AT,
            decision_at=R4_AS_OF,
            expiry=expiry,
            spot=110.0,
            multiplier=50.0,
            expected_strike_count=3,
            raw_rows=rows,
            required=True,
        )
        for expiry, rows in cases
    )


def _mcx_instrument(*, expired: bool = False) -> InstrumentIdentity:
    expiry = date(2026, 7, 18) if expired else date(2026, 8, 5)
    return InstrumentIdentity.create(
        exchange="MCX",
        segment="FUTCOM",
        symbol="GOLDM",
        contract=f"GOLDM{expiry.strftime('%d%b%Y').upper()}FUT",
        expiry=expiry,
        lot_size=100,
        tick_size=0.1,
    )


def _master(
    instrument: InstrumentIdentity,
    *,
    expired: bool = False,
) -> MCXContractMasterEntry:
    return MCXContractMasterEntry(
        instrument=instrument,
        master_revision="MCX-MASTER-2026-07-18-V1",
        calendar_version="MCX-CALENDAR-2026-V1",
        tender_rule_status=MCXRuleStatus.DATED,
        delivery_rule_status=MCXRuleStatus.DATED,
        tender_start=date(2026, 7, 15) if expired else date(2026, 8, 1),
        delivery_start=date(2026, 7, 17) if expired else date(2026, 8, 3),
        available_at=R4_SNAPSHOT_AT,
    )


def _observation(instrument: InstrumentIdentity) -> MCXLocalObservation:
    return MCXLocalObservation(
        instrument_id=instrument.instrument_id,
        observed_at=R4_SNAPSHOT_AT,
        close=73_500.0,
        volume=2_000.0,
        open_interest=8_000.0,
        source_fact_id=f"fact-{instrument.instrument_id}",
    )


def _build_mcx_fixtures() -> tuple[MCXContractAssessment, ...]:
    master_result = _source_result("SRC-MCX-MASTER", "q5-r4-mcx-master")
    local_result = _source_result("SRC-MCX-EOD", "q5-r4-mcx-eod")
    calendar_result = _source_result("SRC-MCX-CALENDAR", "q5-r4-mcx-calendar")
    instrument = _mcx_instrument()
    master = _master(instrument)
    observation = _observation(instrument)
    expired_instrument = _mcx_instrument(expired=True)

    common = {
        "master_result": master_result,
        "local_result": local_result,
        "calendar_result": calendar_result,
        "decision_at": R4_AS_OF,
    }
    return (
        evaluate_mcx_contract(
            requested_instrument=instrument,
            master_entry=master,
            local_observation=observation,
            **common,
        ),
        evaluate_mcx_contract(
            requested_instrument=instrument,
            master_entry=None,
            local_observation=observation,
            master_result=None,
            local_result=local_result,
            calendar_result=calendar_result,
            decision_at=R4_AS_OF,
        ),
        evaluate_mcx_contract(
            requested_instrument=instrument,
            master_entry=master,
            local_observation=None,
            **common,
        ),
        evaluate_mcx_contract(
            requested_instrument=expired_instrument,
            master_entry=_master(expired_instrument, expired=True),
            local_observation=_observation(expired_instrument),
            **common,
        ),
        evaluate_mcx_contract(
            requested_instrument=instrument,
            master_entry=master,
            local_observation=observation,
            synthetic_continuous=True,
            **common,
        ),
    )


def build_q5_r4_fixture_batch() -> Q5R4FixtureBatch:
    return Q5R4FixtureBatch(
        enrichment_plan=_build_enrichment_fixture(),
        option_assessments=_build_option_fixtures(),
        mcx_assessments=_build_mcx_fixtures(),
    )
