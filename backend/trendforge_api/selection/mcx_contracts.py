from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, Field, field_validator, model_validator

from ..source_contracts import SourceResult, SourceResultState
from .contracts import (
    GateOutcome,
    InstrumentIdentity,
    MODEL_CONFIG,
    SelectionGateResult,
    SelectionState,
    StateCeiling,
)


class MCXReadiness(StrEnum):
    MASTER_AND_LOCAL_CONTEXT_READY = "MASTER_AND_LOCAL_CONTEXT_READY"
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"


class MCXRuleStatus(StrEnum):
    DATED = "DATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MCXContractMasterEntry(BaseModel):
    model_config = MODEL_CONFIG

    instrument: InstrumentIdentity
    master_revision: str = Field(min_length=1)
    calendar_version: str = Field(min_length=1)
    tender_rule_status: MCXRuleStatus
    delivery_rule_status: MCXRuleStatus
    tender_start: date | None = None
    delivery_start: date | None = None
    available_at: datetime

    @field_validator("available_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("available_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_tradeable_contract_identity(self) -> "MCXContractMasterEntry":
        instrument = self.instrument
        if instrument.exchange != "MCX":
            raise ValueError("MCX master entry requires MCX exchange")
        if not instrument.contract or instrument.expiry is None:
            raise ValueError("MCX master entry requires contract and expiry")
        if instrument.lot_size is None or instrument.tick_size is None:
            raise ValueError("MCX master entry requires lot size and tick size")
        if self.tender_rule_status is MCXRuleStatus.DATED and self.tender_start is None:
            raise ValueError("dated tender rule requires tender_start")
        if (
            self.tender_rule_status is MCXRuleStatus.NOT_APPLICABLE
            and self.tender_start is not None
        ):
            raise ValueError("non-applicable tender rule cannot have tender_start")
        if (
            self.delivery_rule_status is MCXRuleStatus.DATED
            and self.delivery_start is None
        ):
            raise ValueError("dated delivery rule requires delivery_start")
        if (
            self.delivery_rule_status is MCXRuleStatus.NOT_APPLICABLE
            and self.delivery_start is not None
        ):
            raise ValueError("non-applicable delivery rule cannot have delivery_start")
        if self.tender_start and self.tender_start > instrument.expiry:
            raise ValueError("tender_start cannot be after expiry")
        if self.delivery_start and self.delivery_start > instrument.expiry:
            raise ValueError("delivery_start cannot be after expiry")
        return self


class MCXLocalObservation(BaseModel):
    model_config = MODEL_CONFIG

    instrument_id: str = Field(min_length=1)
    observed_at: datetime
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    open_interest: float = Field(ge=0)
    source_fact_id: str = Field(min_length=1)

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value

    @field_validator("close", "volume", "open_interest")
    @classmethod
    def require_finite(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("MCX observation values must be finite")
        return value


class MCXContractAssessment(BaseModel):
    model_config = MODEL_CONFIG

    requested_instrument: InstrumentIdentity
    state: SelectionState
    state_ceiling: StateCeiling = StateCeiling.WAIT
    readiness: MCXReadiness
    gate_results: tuple[SelectionGateResult, ...]
    unknown_fields: tuple[str, ...]
    master_revision: str | None = None
    calendar_version: str | None = None
    local_source_fact_id: str | None = None
    can_support_confirmed: bool = False
    synthetic_continuous_tradeable: bool = False

    @model_validator(mode="after")
    def enforce_q5_r4_ceiling(self) -> "MCXContractAssessment":
        if self.state is SelectionState.CONFIRMED or self.can_support_confirmed:
            raise ValueError("Q5-R4 MCX assessment cannot confirm")
        if self.synthetic_continuous_tradeable:
            raise ValueError("synthetic continuous MCX series is never tradeable")
        if (
            self.state is SelectionState.WATCH
            and self.readiness is not MCXReadiness.MASTER_AND_LOCAL_CONTEXT_READY
        ):
            raise ValueError("MCX WATCH requires complete local context")
        return self


def _gate(
    code: str,
    outcome: GateOutcome,
    reason: str,
) -> SelectionGateResult:
    return SelectionGateResult(
        code=code,
        outcome=outcome,
        blocks_confirmed=outcome in {GateOutcome.WAIT, GateOutcome.REJECT},
        reason=reason,
        required=True,
    )


def _source_gate(
    source_id: str,
    result: SourceResult | None,
    decision_at: datetime,
) -> SelectionGateResult | None:
    if result is None:
        return _gate(
            f"WAIT_MCX_SOURCE_MISSING_{source_id}",
            GateOutcome.WAIT,
            f"Required MCX source {source_id} is missing.",
        )
    if result.source_id != source_id:
        return _gate(
            f"WAIT_MCX_SOURCE_IDENTITY_{source_id}",
            GateOutcome.WAIT,
            f"Expected MCX source {source_id}, received {result.source_id}.",
        )
    if not result.is_available_at(decision_at):
        return _gate(
            f"WAIT_MCX_SOURCE_TIME_{source_id}",
            GateOutcome.WAIT,
            f"Required MCX source {source_id} was unavailable at decision time.",
        )
    if (
        result.state is not SourceResultState.STRUCTURED_OK
        or result.freshness != "FRESH"
    ):
        return _gate(
            f"WAIT_MCX_SOURCE_{result.state.value}_{source_id}",
            GateOutcome.WAIT,
            f"Required MCX source {source_id} is not structured and fresh.",
        )
    return None


def evaluate_mcx_contract(
    *,
    requested_instrument: InstrumentIdentity,
    master_entry: MCXContractMasterEntry | None,
    local_observation: MCXLocalObservation | None,
    master_result: SourceResult | None,
    local_result: SourceResult | None,
    calendar_result: SourceResult | None,
    decision_at: datetime,
    synthetic_continuous: bool = False,
) -> MCXContractAssessment:
    """Gate MCX context on local contract identity; never substitute proxies."""

    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise ValueError("decision_at must be timezone-aware")
    if requested_instrument.exchange != "MCX":
        raise ValueError("requested instrument must be MCX")

    gates: list[SelectionGateResult] = []
    unknown: list[str] = []
    if synthetic_continuous:
        gates.append(
            _gate(
                "REJECT_MCX_SYNTHETIC_CONTINUOUS",
                GateOutcome.REJECT,
                "Synthetic continuous MCX series cannot represent a tradeable contract.",
            )
        )

    for source_id, result in (
        ("SRC-MCX-MASTER", master_result),
        ("SRC-MCX-EOD", local_result),
        ("SRC-MCX-CALENDAR", calendar_result),
    ):
        source_gate = _source_gate(source_id, result, decision_at)
        if source_gate:
            gates.append(source_gate)
            unknown.append(source_id)

    if master_entry is None:
        gates.append(
            _gate(
                "WAIT_MCX_MASTER_ENTRY",
                GateOutcome.WAIT,
                "The requested contract is absent from the verified local master.",
            )
        )
        unknown.extend(("expiry", "lot_size", "tick_size", "tender_rules"))
    else:
        if master_entry.available_at > decision_at:
            gates.append(
                _gate(
                    "WAIT_MCX_MASTER_PIT",
                    GateOutcome.WAIT,
                    "MCX master revision was unavailable at decision time.",
                )
            )
            unknown.append("master_revision")
        if master_entry.instrument.instrument_id != requested_instrument.instrument_id:
            gates.append(
                _gate(
                    "WAIT_MCX_CONTRACT_IDENTITY",
                    GateOutcome.WAIT,
                    "Requested contract does not match the master identity.",
                )
            )
            unknown.append("contract_identity")
        expiry = master_entry.instrument.expiry
        if expiry is not None and expiry <= decision_at.date():
            gates.append(
                _gate(
                    "REJECT_MCX_EXPIRED_CONTRACT",
                    GateOutcome.REJECT,
                    "The requested MCX contract is expired.",
                )
            )
        tender_or_delivery = (
            master_entry.tender_start
            and master_entry.tender_start <= decision_at.date()
        ) or (
            master_entry.delivery_start
            and master_entry.delivery_start <= decision_at.date()
        )
        if tender_or_delivery:
            gates.append(
                _gate(
                    "WAIT_MCX_TENDER_DELIVERY_WINDOW",
                    GateOutcome.WAIT,
                    "Contract is in a tender or delivery-sensitive window.",
                )
            )

    if local_observation is None:
        gates.append(
            _gate(
                "WAIT_MCX_LOCAL_PRICE_OI",
                GateOutcome.WAIT,
                "Local MCX contract price and open interest are missing.",
            )
        )
        unknown.extend(("local_price", "local_open_interest"))
    else:
        if local_observation.observed_at > decision_at:
            gates.append(
                _gate(
                    "WAIT_MCX_LOCAL_PIT",
                    GateOutcome.WAIT,
                    "Local MCX observation was unavailable at decision time.",
                )
            )
        if local_observation.instrument_id != requested_instrument.instrument_id:
            gates.append(
                _gate(
                    "WAIT_MCX_LOCAL_IDENTITY",
                    GateOutcome.WAIT,
                    "Local price/OI artifact belongs to another contract.",
                )
            )
            unknown.append("local_contract_identity")
        if (
            local_result is not None
            and local_result.data_date is not None
            and local_observation.observed_at.date() != local_result.data_date
        ):
            gates.append(
                _gate(
                    "WAIT_MCX_LOCAL_SOURCE_DATE_MISMATCH",
                    GateOutcome.WAIT,
                    "Local price/OI observation does not match the source data date.",
                )
            )
            unknown.append("local_source_date_alignment")

    has_reject = any(gate.outcome is GateOutcome.REJECT for gate in gates)
    has_wait = any(gate.outcome is GateOutcome.WAIT for gate in gates)
    if has_reject:
        state = SelectionState.REJECT
        readiness = MCXReadiness.INVALID
    elif has_wait:
        state = SelectionState.WAIT
        readiness = MCXReadiness.UNKNOWN
    else:
        state = SelectionState.WATCH
        readiness = MCXReadiness.MASTER_AND_LOCAL_CONTEXT_READY
        gates.extend(
            (
                _gate(
                    "PASS_MCX_MASTER",
                    GateOutcome.PASS,
                    "Contract identity, expiry, lot and tick are verified.",
                ),
                _gate(
                    "PASS_MCX_LOCAL_PRICE_OI",
                    GateOutcome.PASS,
                    "Local contract price and OI artifact is aligned.",
                ),
                _gate(
                    "PASS_MCX_CALENDAR",
                    GateOutcome.PASS,
                    "Local expiry/tender/delivery calendar is available.",
                ),
            )
        )

    return MCXContractAssessment(
        requested_instrument=requested_instrument,
        state=state,
        readiness=readiness,
        gate_results=tuple(gates),
        unknown_fields=tuple(sorted(set(unknown))),
        master_revision=master_entry.master_revision if master_entry else None,
        calendar_version=master_entry.calendar_version if master_entry else None,
        local_source_fact_id=(
            local_observation.source_fact_id if local_observation else None
        ),
    )
