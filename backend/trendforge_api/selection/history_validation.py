"""Q5-R6 state history, PIT validation, drift, and inspector contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import isfinite
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from .pit_path import PITPathEvidence, derive_pit_path

from .contracts import (
    MODEL_CONFIG,
    BarIdentity,
    EvidenceClaim,
    EvidenceFamily,
    GateOutcome,
    NormalizedFact,
    SelectionGateResult,
    SelectionState,
    stable_id,
)
from .transitions import ALLOWED_SELECTION_EDGES


class OutcomePathLabel(StrEnum):
    TARGET_FIRST = "TARGET_FIRST"
    STOP_FIRST = "STOP_FIRST"
    SAME_BAR_STOP_FIRST = "SAME_BAR_STOP_FIRST"
    HORIZON_CENSORED = "HORIZON_CENSORED"
    INVALIDATED_BEFORE_ENTRY = "INVALIDATED_BEFORE_ENTRY"
    NO_ENTRY = "NO_ENTRY"
    DELISTED_OR_UNPRICED = "DELISTED_OR_UNPRICED"
    DATA_INCOMPLETE = "DATA_INCOMPLETE"


class ValidationStatus(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"
    PIT_REJECTED = "PIT_REJECTED"
    PIT_APPROVED = "PIT_APPROVED"


class DriftStatus(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"
    HEALTHY = "HEALTHY"
    WARN = "WARN"
    DEMOTED = "DEMOTED"


def _aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


class StructureSubstate(StrEnum):
    THINKING = "THINKING"
    TESTING = "TESTING"
    ACCEPTED = "ACCEPTED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


class ConfirmationContext(BaseModel):
    """Immutable evidence inputs from which confirmation is derived."""

    model_config = MODEL_CONFIG

    context_id: str = Field(min_length=1)
    decision_at: datetime
    closed_bar: BarIdentity
    required_families: tuple[EvidenceFamily, ...] = Field(min_length=2)
    claims: tuple[EvidenceClaim, ...] = Field(min_length=2)
    facts: tuple[NormalizedFact, ...] = Field(min_length=1)
    gate_results: tuple[SelectionGateResult, ...] = Field(min_length=1)

    @field_validator("decision_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _aware(value, "decision_at")

    @model_validator(mode="after")
    def validate_context(self) -> "ConfirmationContext":
        if (
            not self.closed_bar.is_closed
            or self.closed_bar.close_time > self.decision_at
        ):
            raise ValueError(
                "confirmation requires a closed bar available by decision time"
            )
        if len(self.required_families) != len(set(self.required_families)):
            raise ValueError("required confirmation families must be unique")
        claim_ids = tuple(claim.claim_id for claim in self.claims)
        fact_ids = tuple(fact.fact_id for fact in self.facts)
        gate_codes = tuple(gate.code for gate in self.gate_results)
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("confirmation claims must be unique")
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("confirmation facts must be unique")
        if len(gate_codes) != len(set(gate_codes)):
            raise ValueError("confirmation gates must be unique")
        facts_by_id = {fact.fact_id: fact for fact in self.facts}
        eligible_claims = tuple(
            claim
            for claim in self.claims
            if claim.can_support_confirmed and claim.is_eligible_at(self.decision_at)
        )
        if {claim.family for claim in eligible_claims} < set(self.required_families):
            raise ValueError("required independent evidence families are not satisfied")
        groups = {
            claim.correlation_group
            for claim in eligible_claims
            if claim.family in self.required_families
        }
        if len(groups) < len(self.required_families):
            raise ValueError(
                "required evidence families need independent correlation groups"
            )
        referenced_fact_ids = {
            fact_id for claim in eligible_claims for fact_id in claim.source_fact_ids
        }
        if not referenced_fact_ids or not referenced_fact_ids <= set(facts_by_id):
            raise ValueError("confirmation claims reference unresolved source facts")
        if any(
            facts_by_id[fact_id].quality_state != "STRUCTURED_OK"
            or not facts_by_id[fact_id].is_eligible_at(self.decision_at)
            for fact_id in referenced_fact_ids
        ):
            raise ValueError("confirmation source facts are stale, invalid, or future")
        if any(
            gate.required
            and (gate.outcome is not GateOutcome.PASS or gate.blocks_confirmed)
            for gate in self.gate_results
        ):
            raise ValueError("required confirmation gates must pass")
        expected_id = stable_id(
            "confirmctx",
            self.decision_at,
            self.closed_bar.bar_id,
            tuple(sorted(self.required_families)),
            tuple(sorted(claim_ids)),
            tuple(sorted(referenced_fact_ids)),
            tuple(sorted(gate_codes)),
        )
        if self.context_id != expected_id:
            raise ValueError("confirmation context identity does not match its inputs")
        return self

    @classmethod
    def create(
        cls,
        *,
        decision_at: datetime,
        closed_bar: BarIdentity,
        required_families: tuple[EvidenceFamily, ...],
        claims: tuple[EvidenceClaim, ...],
        facts: tuple[NormalizedFact, ...],
        gate_results: tuple[SelectionGateResult, ...],
    ) -> "ConfirmationContext":
        referenced_fact_ids = tuple(
            sorted({fact_id for claim in claims for fact_id in claim.source_fact_ids})
        )
        context_id = stable_id(
            "confirmctx",
            decision_at,
            closed_bar.bar_id,
            tuple(sorted(required_families)),
            tuple(sorted(claim.claim_id for claim in claims)),
            referenced_fact_ids,
            tuple(sorted(gate.code for gate in gate_results)),
        )
        return cls(
            context_id=context_id,
            decision_at=decision_at,
            closed_bar=closed_bar,
            required_families=tuple(sorted(set(required_families))),
            claims=tuple(sorted(claims, key=lambda claim: claim.claim_id)),
            facts=tuple(sorted(facts, key=lambda fact: fact.fact_id)),
            gate_results=tuple(sorted(gate_results, key=lambda gate: gate.code)),
        )


class ConfirmationProof(BaseModel):
    """Derived proof retained with the event; no caller-supplied pass booleans."""

    model_config = MODEL_CONFIG

    proof_id: str = Field(min_length=1)
    proof_version: Literal["confirmation-proof-2"] = "confirmation-proof-2"
    context_id: str = Field(min_length=1)
    closed_bar_id: str = Field(min_length=1)
    required_families: tuple[EvidenceFamily, ...] = Field(min_length=2)
    evidence_claim_ids: tuple[str, ...] = Field(min_length=2)
    source_fact_ids: tuple[str, ...] = Field(min_length=1)
    gate_codes: tuple[str, ...] = Field(min_length=1)
    all_passed: Literal[True] = True

    @model_validator(mode="after")
    def validate_proof(self) -> "ConfirmationProof":
        for values in (
            self.required_families,
            self.evidence_claim_ids,
            self.source_fact_ids,
            self.gate_codes,
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(
                    "confirmation proof identifiers must be unique and sorted"
                )
        expected = stable_id(
            "confirmproof",
            self.context_id,
            self.closed_bar_id,
            self.required_families,
            self.evidence_claim_ids,
            self.source_fact_ids,
            self.gate_codes,
        )
        if self.proof_id != expected:
            raise ValueError(
                "confirmation proof identity does not match derived inputs"
            )
        return self

    @classmethod
    def from_context(cls, context: ConfirmationContext) -> "ConfirmationProof":
        claim_ids = tuple(sorted(claim.claim_id for claim in context.claims))
        fact_ids = tuple(
            sorted(
                {
                    fact_id
                    for claim in context.claims
                    for fact_id in claim.source_fact_ids
                }
            )
        )
        gate_codes = tuple(sorted(gate.code for gate in context.gate_results))
        families = tuple(sorted(context.required_families))
        return cls(
            proof_id=stable_id(
                "confirmproof",
                context.context_id,
                context.closed_bar.bar_id,
                families,
                claim_ids,
                fact_ids,
                gate_codes,
            ),
            context_id=context.context_id,
            closed_bar_id=context.closed_bar.bar_id,
            required_families=families,
            evidence_claim_ids=claim_ids,
            source_fact_ids=fact_ids,
            gate_codes=gate_codes,
        )


class SelectionStateEvent(BaseModel):
    model_config = MODEL_CONFIG

    event_id: str = Field(min_length=1)
    event_version: Literal["selection-state-event-2"] = "selection-state-event-2"
    sequence: int = Field(ge=1)
    candidate_id: str = Field(min_length=1)
    candidate_instance_id: str = Field(min_length=1)
    reopened_from_candidate_id: str | None = None
    comparable_run_id: str = Field(min_length=1)
    prior_state: SelectionState
    requested_state: SelectionState
    resulting_state: SelectionState
    structure_substate: StructureSubstate
    accepted: bool
    occurred_at: datetime
    reason_code: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    added_claim_ids: tuple[str, ...] = ()
    removed_claim_ids: tuple[str, ...] = ()
    added_gate_codes: tuple[str, ...] = ()
    removed_gate_codes: tuple[str, ...] = ()
    source_health_changes: tuple[str, ...] = ()
    confirmation_context: ConfirmationContext | None = None
    confirmation_proof: ConfirmationProof | None = None

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _aware(value, "occurred_at")

    @model_validator(mode="after")
    def validate_event(self) -> "SelectionStateEvent":
        if self.candidate_id != self.candidate_instance_id:
            raise ValueError(
                "candidate ID must identify the immutable candidate instance"
            )
        if self.reopened_from_candidate_id == self.candidate_instance_id:
            raise ValueError("reopened candidate cannot link to itself")
        if self.accepted and self.resulting_state is not self.requested_state:
            raise ValueError("accepted transition must reach requested state")
        denied_result_is_valid = self.resulting_state is self.prior_state or (
            self.prior_state is SelectionState.WATCH
            and self.requested_state is SelectionState.CONFIRMED
            and self.resulting_state is SelectionState.WAIT
        )
        if not self.accepted and not denied_result_is_valid:
            raise ValueError(
                "denied transition must preserve prior state or resolve WATCH confirmation to WAIT"
            )
        for values in (
            self.added_claim_ids,
            self.removed_claim_ids,
            self.added_gate_codes,
            self.removed_gate_codes,
            self.source_health_changes,
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(
                    "state-event diff identifiers must be unique and sorted"
                )
        if set(self.added_claim_ids) & set(self.removed_claim_ids):
            raise ValueError("a claim cannot be both added and removed")
        if set(self.added_gate_codes) & set(self.removed_gate_codes):
            raise ValueError("a gate cannot be both added and removed")
        if self.resulting_state is SelectionState.CONFIRMED:
            if self.structure_substate is not StructureSubstate.ACCEPTED:
                raise ValueError("CONFIRMED requires ACCEPTED closed-bar structure")
            if self.confirmation_context is None or self.confirmation_proof is None:
                raise ValueError(
                    "CONFIRMED needs derived confirmation context and proof"
                )
            expected = ConfirmationProof.from_context(self.confirmation_context)
            if self.confirmation_proof != expected:
                raise ValueError(
                    "confirmation proof does not match its evidence context"
                )
            if self.confirmation_context.decision_at != self.occurred_at:
                raise ValueError(
                    "confirmation context must use the transition decision time"
                )
        elif (
            self.confirmation_context is not None or self.confirmation_proof is not None
        ):
            raise ValueError("non-CONFIRMED event cannot retain confirmation proof")
        if (
            self.structure_substate
            in {
                StructureSubstate.INVALIDATED,
                StructureSubstate.EXPIRED,
            }
            and self.resulting_state is not SelectionState.REJECT
        ):
            raise ValueError("invalidated or expired structure must resolve to REJECT")
        return self


def build_state_event(
    *,
    sequence: int,
    candidate_id: str,
    comparable_run_id: str,
    prior_state: SelectionState,
    requested_state: SelectionState,
    occurred_at: datetime,
    reason_code: str,
    reason: str,
    blockers: tuple[str, ...] = (),
    hard_veto: bool = False,
    added_claim_ids: tuple[str, ...] = (),
    removed_claim_ids: tuple[str, ...] = (),
    added_gate_codes: tuple[str, ...] = (),
    removed_gate_codes: tuple[str, ...] = (),
    source_health_changes: tuple[str, ...] = (),
    confirmation_context: ConfirmationContext | None = None,
    candidate_instance_id: str | None = None,
    reopened_from_candidate_id: str | None = None,
    structure_substate: StructureSubstate = StructureSubstate.THINKING,
) -> SelectionStateEvent:
    """Create one deterministic transition without self-attested confirmation."""

    instance_id = candidate_instance_id or candidate_id
    normalized_blockers = tuple(sorted(set(blockers)))
    normalized_added_claims = tuple(sorted(set(added_claim_ids)))
    normalized_removed_claims = tuple(sorted(set(removed_claim_ids)))
    normalized_added_gates = tuple(sorted(set(added_gate_codes)))
    normalized_removed_gates = tuple(sorted(set(removed_gate_codes)))
    normalized_source_changes = tuple(sorted(set(source_health_changes)))
    accepted = True
    resulting_state = requested_state
    final_code = reason_code
    final_reason = reason
    confirmation_proof: ConfirmationProof | None = None

    if prior_state is SelectionState.REJECT:
        accepted = False
        resulting_state = prior_state
        final_code = "REJECT_INSTANCE_TERMINAL"
        final_reason = "Rejected candidate instances are immutable; create a linked WATCH instance."
    elif (
        structure_substate in {StructureSubstate.INVALIDATED, StructureSubstate.EXPIRED}
        and requested_state is not SelectionState.REJECT
    ):
        accepted = False
        resulting_state = prior_state
        final_code = "STRUCTURE_TERMINAL_REQUIRES_REJECT"
        final_reason = "Invalidated or expired structure must be recorded as REJECT."
    elif (
        prior_state is SelectionState.WATCH
        and requested_state is SelectionState.CONFIRMED
    ):
        accepted = False
        resulting_state = SelectionState.WAIT
        final_code = "WAIT_DIRECT_CONFIRMATION_FORBIDDEN"
        final_reason = "WATCH must pass through WAIT before CONFIRMED."
    elif requested_state is SelectionState.CONFIRMED and normalized_blockers:
        accepted = False
        resulting_state = prior_state
        final_code = normalized_blockers[0]
        final_reason = "Confirmation denied: " + ", ".join(normalized_blockers)
    elif requested_state is SelectionState.CONFIRMED and confirmation_context is None:
        accepted = False
        resulting_state = prior_state
        final_code = "WAIT_CONFIRMATION_CONTEXT_MISSING"
        final_reason = (
            "Confirmation denied: resolved bars, claims, facts, and gates are required."
        )
    elif requested_state is SelectionState.CONFIRMED:
        confirmation_proof = ConfirmationProof.from_context(confirmation_context)
        if structure_substate is not StructureSubstate.ACCEPTED:
            accepted = False
            resulting_state = prior_state
            final_code = "WAIT_STRUCTURE_NOT_ACCEPTED"
            final_reason = "Confirmation denied: closed-bar structure is not ACCEPTED."
            confirmation_context = None
            confirmation_proof = None
    elif requested_state is SelectionState.REJECT and not (
        hard_veto
        or structure_substate
        in {
            StructureSubstate.INVALIDATED,
            StructureSubstate.EXPIRED,
        }
    ):
        accepted = False
        resulting_state = prior_state
        final_code = "REJECT_REQUIRES_HARD_VETO"
        final_reason = "REJECT requires a deterministic hard veto or invalidation."
    elif hard_veto and requested_state is not SelectionState.REJECT:
        accepted = False
        resulting_state = prior_state
        final_code = "HARD_VETO_REQUIRES_REJECT"
        final_reason = "A hard veto cannot be represented as a non-REJECT transition."

    if resulting_state is not SelectionState.CONFIRMED:
        confirmation_context = None
        confirmation_proof = None

    identity = {
        "sequence": sequence,
        "candidate_instance_id": instance_id,
        "reopened_from_candidate_id": reopened_from_candidate_id,
        "run_id": comparable_run_id,
        "prior": prior_state,
        "requested": requested_state,
        "result": resulting_state,
        "structure_substate": structure_substate,
        "occurred_at": occurred_at,
        "reason_code": final_code,
        "reason": final_reason,
        "added_claim_ids": normalized_added_claims,
        "removed_claim_ids": normalized_removed_claims,
        "added_gate_codes": normalized_added_gates,
        "removed_gate_codes": normalized_removed_gates,
        "source_health_changes": normalized_source_changes,
        "confirmation_context_id": (
            confirmation_context.context_id if confirmation_context else None
        ),
        "confirmation_proof_id": (
            confirmation_proof.proof_id if confirmation_proof else None
        ),
    }
    return SelectionStateEvent(
        event_id=stable_id("stevt", identity),
        sequence=sequence,
        candidate_id=instance_id,
        candidate_instance_id=instance_id,
        reopened_from_candidate_id=reopened_from_candidate_id,
        comparable_run_id=comparable_run_id,
        prior_state=prior_state,
        requested_state=requested_state,
        resulting_state=resulting_state,
        structure_substate=structure_substate,
        accepted=accepted,
        occurred_at=occurred_at,
        reason_code=final_code,
        reason=final_reason,
        added_claim_ids=normalized_added_claims,
        removed_claim_ids=normalized_removed_claims,
        added_gate_codes=normalized_added_gates,
        removed_gate_codes=normalized_removed_gates,
        source_health_changes=normalized_source_changes,
        confirmation_context=confirmation_context,
        confirmation_proof=confirmation_proof,
    )


class SelectionHistory(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str = Field(min_length=1)
    candidate_instance_id: str = Field(min_length=1)
    reopened_from_candidate_id: str | None = None
    initial_state: SelectionState
    current_state: SelectionState
    events: tuple[SelectionStateEvent, ...]
    reconstructable: Literal[True] = True

    @model_validator(mode="after")
    def validate_chain(self) -> "SelectionHistory":
        if self.candidate_id != self.candidate_instance_id:
            raise ValueError(
                "history candidate ID must identify one immutable instance"
            )
        if self.reopened_from_candidate_id == self.candidate_instance_id:
            raise ValueError("reopened history cannot link to itself")
        if not self.events:
            raise ValueError("state history needs at least one event")
        allowed_edges = ALLOWED_SELECTION_EDGES
        expected = self.initial_state
        previous_time: datetime | None = None
        seen_ids: set[str] = set()
        for expected_sequence, event in enumerate(self.events, start=1):
            if (
                event.candidate_id != self.candidate_instance_id
                or event.candidate_instance_id != self.candidate_instance_id
            ):
                raise ValueError("state history mixes candidate instances")
            if event.reopened_from_candidate_id != self.reopened_from_candidate_id:
                raise ValueError("state history has inconsistent reopen lineage")
            if event.sequence != expected_sequence:
                raise ValueError("state history sequence is not contiguous")
            if event.event_id in seen_ids:
                raise ValueError("state history contains duplicate event IDs")
            if event.prior_state is not expected:
                raise ValueError("state history prior state does not reconstruct")
            if event.accepted and event.resulting_state not in allowed_edges[expected]:
                raise ValueError("state history contains a forbidden transition")
            if expected is SelectionState.REJECT:
                raise ValueError(
                    "rejected candidate instance is terminal; create a linked new instance"
                )
            if previous_time and event.occurred_at < previous_time:
                raise ValueError("state history timestamps are out of order")
            seen_ids.add(event.event_id)
            previous_time = event.occurred_at
            expected = event.resulting_state
        if self.current_state is not expected:
            raise ValueError("current state does not match reconstructed history")
        return self

    @computed_field(return_type=tuple[str, ...])
    @property
    def what_changed(self) -> tuple[str, ...]:
        return tuple(
            f"{event.prior_state}->{event.resulting_state}: {event.reason_code}"
            for event in self.events
        )


class ValidationCostProfile(BaseModel):
    model_config = MODEL_CONFIG

    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    venue: Literal["NSE", "MCX"]
    horizon: str = Field(min_length=1)
    brokerage_bps: float = Field(ge=0)
    fees_taxes_bps: float = Field(ge=0)
    spread_bps: float = Field(ge=0)
    slippage_bps: float = Field(ge=0)
    impact_bps: float = Field(ge=0)
    sensitivity_multipliers: tuple[float, ...] = Field(min_length=2)
    available_at: datetime

    @field_validator("available_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _aware(value, "available_at")

    @field_validator(
        "brokerage_bps", "fees_taxes_bps", "spread_bps", "slippage_bps", "impact_bps"
    )
    @classmethod
    def require_finite_costs(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("cost inputs must be finite")
        return value

    @field_validator("sensitivity_multipliers")
    @classmethod
    def validate_sensitivity(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if any(not isfinite(item) or item <= 0 for item in value):
            raise ValueError("cost sensitivity multipliers must be finite and positive")
        if tuple(sorted(set(value))) != value:
            raise ValueError("cost sensitivity multipliers must be unique and sorted")
        return value

    @computed_field(return_type=float)
    @property
    def total_cost_bps(self) -> float:
        return round(
            self.brokerage_bps
            + self.fees_taxes_bps
            + self.spread_bps
            + self.slippage_bps
            + self.impact_bps,
            6,
        )


class CostSensitivityPoint(BaseModel):
    model_config = MODEL_CONFIG

    multiplier: float = Field(gt=0)
    net_expectancy: float

    @field_validator("multiplier", "net_expectancy")
    @classmethod
    def require_finite_values(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("cost sensitivity values must be finite")
        return value


class PITOutcome(BaseModel):
    """Outcome whose label and metrics are verified against immutable path evidence."""

    model_config = MODEL_CONFIG

    outcome_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    decision_at: datetime
    entry_policy_version: str = Field(min_length=1)
    horizon_end: datetime
    cutoff_at: datetime
    outcome_available_at: datetime
    label: OutcomePathLabel
    universe_version: str = Field(min_length=1)
    membership_available_at: datetime
    raw_bar_version: str = Field(min_length=1)
    adjusted_bar_version: str = Field(min_length=1)
    cost_profile_id: str = Field(min_length=1)
    cost_profile_version: str = Field(min_length=1)
    gross_return: float
    net_return: float
    explicit_cost_bps: float = Field(ge=0)
    predicted_probability: float | None = Field(default=None, ge=0, le=1)
    prediction_artifact_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    prediction_available_at: datetime | None = None
    mfe: float | None = Field(default=None, ge=0)
    mae: float | None = Field(default=None, le=0)
    path_evidence: PITPathEvidence
    delisting_checked: bool
    delisting_check_version: str = Field(min_length=1)
    censored_reason: str | None = None

    @field_validator(
        "decision_at",
        "horizon_end",
        "cutoff_at",
        "outcome_available_at",
        "membership_available_at",
        "prediction_available_at",
    )
    @classmethod
    def require_timezone(
        cls,
        value: datetime | None,
        info,
    ) -> datetime | None:
        return _aware(value, info.field_name) if value is not None else None

    @field_validator("gross_return", "net_return", "explicit_cost_bps", "mfe", "mae")
    @classmethod
    def require_finite_values(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("outcome values must be finite")
        return value

    @model_validator(mode="after")
    def validate_pit(self) -> "PITOutcome":
        if self.horizon_end <= self.decision_at:
            raise ValueError("outcome horizon must follow decision time")
        if not self.decision_at <= self.cutoff_at <= self.horizon_end:
            raise ValueError("outcome cutoff must be within observation horizon")
        if self.membership_available_at > self.decision_at:
            raise ValueError("future universe membership is survivorship leakage")

        prediction_parts = (
            self.predicted_probability,
            self.prediction_artifact_hash,
            self.prediction_available_at,
        )
        if any(value is None for value in prediction_parts) and any(
            value is not None for value in prediction_parts
        ):
            raise ValueError(
                "prediction requires probability, artifact hash, and availability"
            )
        if (
            self.prediction_available_at is not None
            and self.prediction_available_at > self.decision_at
        ):
            raise ValueError("prediction available after decision is temporal leakage")

        derived = derive_pit_path(
            self.path_evidence,
            decision_at=self.decision_at,
            horizon_end=self.horizon_end,
            cutoff_at=self.cutoff_at,
        )
        if self.label.value != derived.label:
            raise ValueError("outcome label does not match immutable bar path")
        if abs(self.gross_return - derived.gross_return) > 1e-8:
            raise ValueError("gross return does not match immutable bar path")
        if self.mfe != derived.mfe or self.mae != derived.mae:
            raise ValueError("MFE/MAE do not match immutable bar path")
        if self.outcome_available_at != derived.outcome_available_at:
            raise ValueError("outcome availability does not match terminal evidence")
        if self.outcome_available_at < self.cutoff_at:
            raise ValueError("outcome cannot be available before terminal cutoff")

        expected_cost = self.explicit_cost_bps / 10_000 if derived.entered else 0.0
        expected_net = round(self.gross_return - expected_cost, 8)
        if abs(self.net_return - expected_net) > 1e-8:
            raise ValueError("net return does not match derived path and explicit cost")
        if not derived.entered and self.explicit_cost_bps != 0:
            raise ValueError("non-entry outcome cannot carry transaction costs")

        non_performance_labels = {
            OutcomePathLabel.HORIZON_CENSORED,
            OutcomePathLabel.INVALIDATED_BEFORE_ENTRY,
            OutcomePathLabel.NO_ENTRY,
            OutcomePathLabel.DELISTED_OR_UNPRICED,
            OutcomePathLabel.DATA_INCOMPLETE,
        }
        if self.label in non_performance_labels and not self.censored_reason:
            raise ValueError("non-performance outcome needs an explicit reason")
        if self.label not in non_performance_labels and self.censored_reason:
            raise ValueError(
                "resolved performance outcome cannot carry a censor reason"
            )
        if (
            self.label
            in {
                OutcomePathLabel.TARGET_FIRST,
                OutcomePathLabel.STOP_FIRST,
                OutcomePathLabel.SAME_BAR_STOP_FIRST,
            }
            and self.predicted_probability is None
        ):
            raise ValueError("resolved performance outcome needs a PIT prediction")

        expected_id = stable_id(
            "pitout",
            self.candidate_id,
            self.decision_at,
            self.entry_policy_version,
            self.path_evidence.evidence_id,
            self.cost_profile_id,
            self.cost_profile_version,
        )
        if self.outcome_id != expected_id:
            raise ValueError("outcome identity does not match path and versions")
        return self

    @classmethod
    def create_from_path(
        cls,
        *,
        candidate_id: str,
        decision_at: datetime,
        entry_policy_version: str,
        horizon_end: datetime,
        cutoff_at: datetime,
        universe_version: str,
        membership_available_at: datetime,
        raw_bar_version: str,
        adjusted_bar_version: str,
        cost_profile_id: str,
        cost_profile_version: str,
        explicit_cost_bps: float,
        predicted_probability: float | None,
        prediction_artifact_hash: str | None,
        prediction_available_at: datetime | None,
        path_evidence: PITPathEvidence,
        delisting_checked: bool,
        delisting_check_version: str,
        censored_reason: str | None = None,
    ) -> "PITOutcome":
        derived = derive_pit_path(
            path_evidence,
            decision_at=decision_at,
            horizon_end=horizon_end,
            cutoff_at=cutoff_at,
        )
        applied_cost_bps = explicit_cost_bps if derived.entered else 0.0
        outcome_id = stable_id(
            "pitout",
            candidate_id,
            decision_at,
            entry_policy_version,
            path_evidence.evidence_id,
            cost_profile_id,
            cost_profile_version,
        )
        return cls(
            outcome_id=outcome_id,
            candidate_id=candidate_id,
            decision_at=decision_at,
            entry_policy_version=entry_policy_version,
            horizon_end=horizon_end,
            cutoff_at=cutoff_at,
            outcome_available_at=derived.outcome_available_at,
            label=OutcomePathLabel(derived.label),
            universe_version=universe_version,
            membership_available_at=membership_available_at,
            raw_bar_version=raw_bar_version,
            adjusted_bar_version=adjusted_bar_version,
            cost_profile_id=cost_profile_id,
            cost_profile_version=cost_profile_version,
            gross_return=derived.gross_return,
            net_return=round(
                derived.gross_return - applied_cost_bps / 10_000,
                8,
            ),
            explicit_cost_bps=applied_cost_bps,
            predicted_probability=predicted_probability,
            prediction_artifact_hash=prediction_artifact_hash,
            prediction_available_at=prediction_available_at,
            mfe=derived.mfe,
            mae=derived.mae,
            path_evidence=path_evidence,
            delisting_checked=delisting_checked,
            delisting_check_version=delisting_check_version,
            censored_reason=censored_reason,
        )


class PITValidationProfile(BaseModel):
    model_config = MODEL_CONFIG

    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    min_effective_sample: int = Field(ge=1)
    max_calibration_error: float = Field(ge=0, le=1)
    min_net_expectancy: float
    max_drawdown: float = Field(ge=0, le=1)
    max_false_confirmed_rate: float = Field(ge=0, le=1)
    max_feature_psi: float = Field(gt=0)
    max_residual_shift: float = Field(gt=0)

    @field_validator(
        "max_calibration_error",
        "min_net_expectancy",
        "max_drawdown",
        "max_false_confirmed_rate",
        "max_feature_psi",
        "max_residual_shift",
    )
    @classmethod
    def require_finite_thresholds(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("validation thresholds must be finite")
        return value


class ValidationArtifactProof(BaseModel):
    """Versioned result of one reproducible validation split."""

    model_config = MODEL_CONFIG

    artifact_id: str = Field(min_length=1)
    artifact_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_kind: Literal["WALK_FORWARD", "HOLDOUT"]
    calculation_version: Literal["pit-validation-artifact-1"] = (
        "pit-validation-artifact-1"
    )
    split_policy_version: str = Field(min_length=1)
    outcome_ids: tuple[str, ...] = Field(min_length=1)
    generated_at: datetime
    available_at: datetime
    passed: bool

    @field_validator("generated_at", "available_at")
    @classmethod
    def require_timezone(cls, value: datetime, info) -> datetime:
        return _aware(value, info.field_name)

    @model_validator(mode="after")
    def validate_artifact(self) -> "ValidationArtifactProof":
        if self.available_at < self.generated_at:
            raise ValueError(
                "validation artifact cannot be available before generation"
            )
        if tuple(sorted(set(self.outcome_ids))) != self.outcome_ids:
            raise ValueError(
                "validation artifact outcome IDs must be unique and sorted"
            )
        expected = stable_id(
            "pitvalart",
            self.artifact_hash,
            self.artifact_kind,
            self.calculation_version,
            self.split_policy_version,
            self.outcome_ids,
            self.generated_at,
            self.available_at,
            self.passed,
        )
        if self.artifact_id != expected:
            raise ValueError("validation artifact identity does not match its inputs")
        return self

    @classmethod
    def create(
        cls,
        *,
        artifact_hash: str,
        artifact_kind: Literal["WALK_FORWARD", "HOLDOUT"],
        split_policy_version: str,
        outcome_ids: tuple[str, ...],
        generated_at: datetime,
        available_at: datetime,
        passed: bool,
    ) -> "ValidationArtifactProof":
        normalized_hash = artifact_hash.lower()
        normalized_ids = tuple(sorted(set(outcome_ids)))
        return cls(
            artifact_id=stable_id(
                "pitvalart",
                normalized_hash,
                artifact_kind,
                "pit-validation-artifact-1",
                split_policy_version,
                normalized_ids,
                generated_at,
                available_at,
                passed,
            ),
            artifact_hash=normalized_hash,
            artifact_kind=artifact_kind,
            split_policy_version=split_policy_version,
            outcome_ids=normalized_ids,
            generated_at=generated_at,
            available_at=available_at,
            passed=passed,
        )


class PITValidationResult(BaseModel):
    model_config = MODEL_CONFIG

    run_id: str = Field(min_length=1)
    profile: PITValidationProfile
    status: ValidationStatus
    outcome_ids: tuple[str, ...]
    effective_sample: int = Field(ge=0)
    calibration_error: float | None = None
    net_expectancy: float | None = None
    max_drawdown: float | None = None
    false_confirmed_rate: float | None = None
    cost_profile_id: str | None = None
    cost_profile_version: str | None = None
    cost_sensitivity: tuple[CostSensitivityPoint, ...] = ()
    walk_forward_artifact_id: str | None = None
    holdout_artifact_id: str | None = None
    blocker_codes: tuple[str, ...] = ()
    evaluated_at: datetime
    fixture_only: bool = True
    production_authorized: Literal[False] = False

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _aware(value, "evaluated_at")

    @field_validator(
        "calibration_error",
        "net_expectancy",
        "max_drawdown",
        "false_confirmed_rate",
    )
    @classmethod
    def require_finite_metrics(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("validation metrics must be finite")
        return value

    @computed_field(return_type=bool)
    @property
    def performance_ui_allowed(self) -> bool:
        return False

    @computed_field(return_type=bool)
    @property
    def probability_ui_allowed(self) -> bool:
        return False

    @model_validator(mode="after")
    def validate_result(self) -> "PITValidationResult":
        metrics = (
            self.calibration_error,
            self.net_expectancy,
            self.max_drawdown,
            self.false_confirmed_rate,
        )
        if self.status is ValidationStatus.PIT_APPROVED:
            if self.blocker_codes or any(value is None for value in metrics):
                raise ValueError("PIT_APPROVED needs complete metrics and no blockers")
            if not self.cost_profile_id or not self.cost_profile_version:
                raise ValueError("PIT_APPROVED needs a versioned cost profile")
            if not self.cost_sensitivity:
                raise ValueError("PIT_APPROVED needs cost sensitivity results")
            if not self.walk_forward_artifact_id or not self.holdout_artifact_id:
                raise ValueError(
                    "PIT_APPROVED needs walk-forward and holdout artifacts"
                )
        elif not self.blocker_codes:
            raise ValueError("non-approved validation needs blocker codes")
        return self


def evaluate_pit_validation(
    *,
    run_id: str,
    profile: PITValidationProfile,
    outcomes: tuple[PITOutcome, ...],
    cost_profile: ValidationCostProfile | None,
    evaluated_at: datetime,
    walk_forward_artifact: ValidationArtifactProof | None,
    holdout_artifact: ValidationArtifactProof | None,
    fixture_only: bool = True,
) -> PITValidationResult:
    blockers: list[str] = []
    completed_labels = {
        OutcomePathLabel.TARGET_FIRST,
        OutcomePathLabel.STOP_FIRST,
        OutcomePathLabel.SAME_BAR_STOP_FIRST,
    }
    completed = tuple(
        outcome for outcome in outcomes if outcome.label in completed_labels
    )
    if cost_profile is None:
        blockers.append("PIT_COST_PROFILE_MISSING")
    if len(completed) < profile.min_effective_sample:
        blockers.append("PIT_SAMPLE_INSUFFICIENT")
    expected_outcome_ids = tuple(sorted(outcome.outcome_id for outcome in outcomes))
    if (
        walk_forward_artifact is None
        or walk_forward_artifact.artifact_kind != "WALK_FORWARD"
        or not walk_forward_artifact.passed
        or walk_forward_artifact.available_at > evaluated_at
        or walk_forward_artifact.outcome_ids != expected_outcome_ids
    ):
        blockers.append("PIT_WALK_FORWARD_FAILED")
    if (
        holdout_artifact is None
        or holdout_artifact.artifact_kind != "HOLDOUT"
        or not holdout_artifact.passed
        or holdout_artifact.available_at > evaluated_at
        or holdout_artifact.outcome_ids != expected_outcome_ids
    ):
        blockers.append("PIT_HOLDOUT_FAILED")
    if any(not outcome.delisting_checked for outcome in outcomes):
        blockers.append("PIT_DELISTING_UNCHECKED")
    if len({outcome.outcome_id for outcome in outcomes}) != len(outcomes):
        blockers.append("PIT_DUPLICATE_OUTCOME")
    business_keys = {
        (outcome.candidate_id, outcome.decision_at, outcome.horizon_end)
        for outcome in outcomes
    }
    if len(business_keys) != len(outcomes):
        blockers.append("PIT_SEMANTIC_DUPLICATE_OUTCOME")
    if any(outcome.outcome_available_at > evaluated_at for outcome in outcomes):
        blockers.append("PIT_OUTCOME_NOT_AVAILABLE")
    if cost_profile and cost_profile.available_at > evaluated_at:
        blockers.append("PIT_COST_PROFILE_FUTURE")
    if cost_profile and any(
        outcome.cost_profile_id != cost_profile.profile_id
        or outcome.cost_profile_version != cost_profile.profile_version
        for outcome in outcomes
    ):
        blockers.append("PIT_COST_PROFILE_MISMATCH")

    expected_cost_bps = cost_profile.total_cost_bps if cost_profile else None
    if expected_cost_bps is not None and any(
        (
            abs(outcome.explicit_cost_bps - expected_cost_bps) > 1e-6
            or abs(
                outcome.net_return - (outcome.gross_return - expected_cost_bps / 10_000)
            )
            > 1e-8
        )
        for outcome in outcomes
        if outcome.path_evidence.entry_at is not None
    ):
        blockers.append("PIT_COST_ARITHMETIC_MISMATCH")

    deterministic_returns = (
        tuple(
            outcome.gross_return - expected_cost_bps / 10_000 for outcome in completed
        )
        if expected_cost_bps is not None
        else ()
    )
    net_expectancy = (
        round(sum(deterministic_returns) / len(deterministic_returns), 8)
        if deterministic_returns
        else None
    )
    probabilities = tuple(outcome.predicted_probability for outcome in completed)
    if not probabilities or any(value is None for value in probabilities):
        calibration_value = None
    else:
        observed = tuple(
            1.0 if outcome.label is OutcomePathLabel.TARGET_FIRST else 0.0
            for outcome in completed
        )
        calibration_value = round(
            sum(
                (float(probability) - actual) ** 2
                for probability, actual in zip(probabilities, observed, strict=True)
            )
            / len(observed),
            8,
        )

    equity = 1.0
    peak = 1.0
    drawdown_value = 0.0 if deterministic_returns else None
    ordered_completed = sorted(completed, key=lambda outcome: outcome.decision_at)
    for outcome in ordered_completed:
        net_return = outcome.gross_return - (expected_cost_bps or 0.0) / 10_000
        equity *= 1.0 + net_return
        peak = max(peak, equity)
        drawdown_value = max(drawdown_value or 0.0, (peak - equity) / peak)
    if drawdown_value is not None:
        drawdown_value = round(drawdown_value, 8)

    failure_labels = {
        OutcomePathLabel.STOP_FIRST,
        OutcomePathLabel.SAME_BAR_STOP_FIRST,
        OutcomePathLabel.DELISTED_OR_UNPRICED,
    }
    false_confirmed_value = (
        round(
            sum(outcome.label in failure_labels for outcome in completed)
            / len(completed),
            8,
        )
        if completed
        else None
    )
    cost_sensitivity = (
        tuple(
            CostSensitivityPoint(
                multiplier=multiplier,
                net_expectancy=round(
                    sum(
                        outcome.gross_return - expected_cost_bps * multiplier / 10_000
                        for outcome in completed
                    )
                    / len(completed),
                    8,
                ),
            )
            for multiplier in cost_profile.sensitivity_multipliers
        )
        if cost_profile and completed
        else ()
    )
    if calibration_value is None or calibration_value > profile.max_calibration_error:
        blockers.append("PIT_CALIBRATION_FAILED")
    if net_expectancy is None or net_expectancy < profile.min_net_expectancy:
        blockers.append("PIT_EXPECTANCY_FAILED")
    if drawdown_value is None or drawdown_value > profile.max_drawdown:
        blockers.append("PIT_DRAWDOWN_FAILED")
    if (
        false_confirmed_value is None
        or false_confirmed_value > profile.max_false_confirmed_rate
    ):
        blockers.append("PIT_FALSE_CONFIRMED_FAILED")

    unique_blockers = tuple(sorted(set(blockers)))
    status = (
        ValidationStatus.PIT_APPROVED
        if not unique_blockers
        else ValidationStatus.PIT_REJECTED
    )
    return PITValidationResult(
        run_id=run_id,
        profile=profile,
        status=status,
        outcome_ids=tuple(sorted(outcome.outcome_id for outcome in outcomes)),
        effective_sample=len(completed),
        calibration_error=calibration_value,
        net_expectancy=net_expectancy,
        max_drawdown=drawdown_value,
        false_confirmed_rate=false_confirmed_value,
        cost_profile_id=cost_profile.profile_id if cost_profile else None,
        cost_profile_version=cost_profile.profile_version if cost_profile else None,
        cost_sensitivity=cost_sensitivity,
        walk_forward_artifact_id=(
            walk_forward_artifact.artifact_id if walk_forward_artifact else None
        ),
        holdout_artifact_id=(
            holdout_artifact.artifact_id if holdout_artifact else None
        ),
        blocker_codes=unique_blockers,
        evaluated_at=evaluated_at,
        fixture_only=fixture_only,
    )


class DriftMetricArtifact(BaseModel):
    """Lineage-bound drift metrics for one approved validation baseline."""

    model_config = MODEL_CONFIG

    artifact_id: str = Field(min_length=1)
    artifact_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculation_version: Literal["pit-drift-1"] = "pit-drift-1"
    validation_run_id: str = Field(min_length=1)
    baseline_window_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_window_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    available_at: datetime
    feature_psi: float = Field(ge=0)
    calibration_error_delta: float
    residual_shift: float = Field(ge=0)

    @field_validator("available_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _aware(value, "available_at")

    @field_validator("feature_psi", "calibration_error_delta", "residual_shift")
    @classmethod
    def require_finite_metrics(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("drift artifact metrics must be finite")
        return value

    @model_validator(mode="after")
    def validate_artifact(self) -> "DriftMetricArtifact":
        expected = stable_id(
            "driftart",
            self.artifact_hash,
            self.calculation_version,
            self.validation_run_id,
            self.baseline_window_hash,
            self.current_window_hash,
            self.available_at,
            self.feature_psi,
            self.calibration_error_delta,
            self.residual_shift,
        )
        if self.artifact_id != expected:
            raise ValueError("drift artifact identity does not match its inputs")
        return self

    @classmethod
    def create(
        cls,
        *,
        artifact_hash: str,
        validation_run_id: str,
        baseline_window_hash: str,
        current_window_hash: str,
        available_at: datetime,
        feature_psi: float,
        calibration_error_delta: float,
        residual_shift: float,
    ) -> "DriftMetricArtifact":
        values = (
            artifact_hash.lower(),
            validation_run_id,
            baseline_window_hash.lower(),
            current_window_hash.lower(),
            available_at,
            feature_psi,
            calibration_error_delta,
            residual_shift,
        )
        return cls(
            artifact_id=stable_id("driftart", values[0], "pit-drift-1", *values[1:]),
            artifact_hash=values[0],
            validation_run_id=validation_run_id,
            baseline_window_hash=values[2],
            current_window_hash=values[3],
            available_at=available_at,
            feature_psi=feature_psi,
            calibration_error_delta=calibration_error_delta,
            residual_shift=residual_shift,
        )


class DriftAssessment(BaseModel):
    model_config = MODEL_CONFIG

    assessment_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    validation_run_id: str = Field(min_length=1)
    metric_artifact_id: str | None = None
    metric_calculation_version: str | None = None
    baseline_window_hash: str | None = None
    current_window_hash: str | None = None
    baseline_evaluated_at: datetime
    status: DriftStatus
    feature_psi: float | None = None
    calibration_error_delta: float | None = None
    residual_shift: float | None = None
    reason_codes: tuple[str, ...]
    assessed_at: datetime
    can_auto_promote: Literal[False] = False

    @field_validator("assessed_at", "baseline_evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime, info) -> datetime:
        return _aware(value, info.field_name)

    @field_validator("feature_psi", "residual_shift")
    @classmethod
    def require_nonnegative_drift_metrics(cls, value: float | None) -> float | None:
        if value is not None and (not isfinite(value) or value < 0):
            raise ValueError("drift magnitude metrics must be finite and non-negative")
        return value

    @model_validator(mode="after")
    def validate_temporal_order(self) -> "DriftAssessment":
        if self.assessed_at < self.baseline_evaluated_at:
            raise ValueError("drift cannot be assessed before its validation baseline")
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise ValueError("drift reason codes must be unique")
        return self

    @computed_field(return_type=bool)
    @property
    def demotes_to_research_only(self) -> bool:
        return self.status is DriftStatus.DEMOTED


def assess_validation_drift(
    *,
    validation: PITValidationResult,
    metric_artifact: DriftMetricArtifact | None,
    assessed_at: datetime,
) -> DriftAssessment:
    if assessed_at < validation.evaluated_at:
        raise ValueError("drift cannot be assessed before validation")

    reasons: list[str] = []
    artifact_valid = (
        metric_artifact is not None
        and metric_artifact.validation_run_id == validation.run_id
        and metric_artifact.available_at <= assessed_at
    )
    if validation.status is not ValidationStatus.PIT_APPROVED:
        status = DriftStatus.NOT_EVALUATED
        reasons.append("DRIFT_REQUIRES_PIT_APPROVED_BASELINE")
    elif not artifact_valid:
        status = DriftStatus.DEMOTED
        reasons.append("DRIFT_ARTIFACT_MISSING_OR_MISMATCHED")
    else:
        assert metric_artifact is not None
        if (
            metric_artifact.feature_psi > validation.profile.max_feature_psi
            or metric_artifact.residual_shift > validation.profile.max_residual_shift
            or metric_artifact.calibration_error_delta
            > validation.profile.max_calibration_error
        ):
            status = DriftStatus.DEMOTED
            reasons.append("DRIFT_THRESHOLD_EXCEEDED")
        elif (
            metric_artifact.feature_psi > validation.profile.max_feature_psi * 0.75
            or metric_artifact.residual_shift
            > validation.profile.max_residual_shift * 0.75
        ):
            status = DriftStatus.WARN
            reasons.append("DRIFT_NEAR_THRESHOLD")
        else:
            status = DriftStatus.HEALTHY
            reasons.append("DRIFT_WITHIN_PROFILE_LIMITS")

    feature_psi = metric_artifact.feature_psi if artifact_valid else None
    calibration_delta = (
        metric_artifact.calibration_error_delta if artifact_valid else None
    )
    residual_shift = metric_artifact.residual_shift if artifact_valid else None
    return DriftAssessment(
        assessment_id=stable_id(
            "drift",
            validation.run_id,
            validation.profile.profile_version,
            assessed_at,
            metric_artifact.artifact_id if artifact_valid and metric_artifact else None,
        ),
        profile_id=validation.profile.profile_id,
        profile_version=validation.profile.profile_version,
        validation_run_id=validation.run_id,
        metric_artifact_id=(
            metric_artifact.artifact_id if artifact_valid and metric_artifact else None
        ),
        metric_calculation_version=(
            metric_artifact.calculation_version
            if artifact_valid and metric_artifact
            else None
        ),
        baseline_window_hash=(
            metric_artifact.baseline_window_hash
            if artifact_valid and metric_artifact
            else None
        ),
        current_window_hash=(
            metric_artifact.current_window_hash
            if artifact_valid and metric_artifact
            else None
        ),
        baseline_evaluated_at=validation.evaluated_at,
        status=status,
        feature_psi=feature_psi,
        calibration_error_delta=calibration_delta,
        residual_shift=residual_shift,
        reason_codes=tuple(reasons),
        assessed_at=assessed_at,
    )


class InspectorSection(BaseModel):
    model_config = MODEL_CONFIG

    section_id: Literal[
        "DECISION_PROOF",
        "STRUCTURE_PARTICIPATION",
        "DERIVATIVES",
        "CORPORATE_SPONSOR",
        "SCANNER_LAB",
        "SOURCES_LINEAGE",
        "HISTORY",
        "FAILURES",
        "VALIDATION",
    ]
    title: str = Field(min_length=1)
    status: Literal["AVAILABLE", "UNKNOWN", "HIDDEN"]
    summary: str = Field(min_length=1)
    items: tuple[str, ...] = ()


class CandidateInspector(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str = Field(min_length=1)
    state: SelectionState
    evidence_strength_label: Literal["Evidence strength - not win probability"]
    selected_claim_ids: tuple[str, ...]
    suppressed_claim_ids: tuple[str, ...]
    opposing_claim_ids: tuple[str, ...]
    source_health: tuple[str, ...]
    sections: tuple[InspectorSection, ...]
    validation_status: ValidationStatus
    performance_ui_visible: Literal[False] = False
    probability_ui_visible: Literal[False] = False
    executable: Literal[False] = False

    @model_validator(mode="after")
    def validate_visibility(self) -> "CandidateInspector":
        section_ids = tuple(item.section_id for item in self.sections)
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("inspector section IDs must be unique")

        originals = (
            self.selected_claim_ids,
            self.suppressed_claim_ids,
            self.opposing_claim_ids,
        )
        claim_sets = tuple(set(values) for values in originals)
        if any(
            len(values) != len(original)
            for values, original in zip(claim_sets, originals, strict=True)
        ):
            raise ValueError("inspector claim IDs must be unique")
        if any(
            left & right
            for index, left in enumerate(claim_sets)
            for right in claim_sets[index + 1 :]
        ):
            raise ValueError(
                "selected, suppressed, and opposing claims must be disjoint"
            )
        if len(self.source_health) != len(set(self.source_health)):
            raise ValueError("inspector source-health rows must be unique")

        validation_section = next(
            (item for item in self.sections if item.section_id == "VALIDATION"), None
        )
        if validation_section is None:
            raise ValueError("inspector needs a validation section")
        if (
            self.performance_ui_visible
            and self.validation_status is not ValidationStatus.PIT_APPROVED
        ):
            raise ValueError("performance UI requires PIT_APPROVED")
        if not self.performance_ui_visible and validation_section.status != "HIDDEN":
            raise ValueError("unapproved validation section must remain hidden")
        return self
