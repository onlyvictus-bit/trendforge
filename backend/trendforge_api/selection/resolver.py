from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from ..source_contracts import SourceResult, SourceResultState, SourceRole
from .contracts import (
    DataMode,
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    GateOutcome,
    MODEL_CONFIG,
    NormalizedFact,
    SelectionGateResult,
    SelectionState,
    StateCeiling,
)


class ClaimDisposition(StrEnum):
    SELECTED_SUPPORT = "SELECTED_SUPPORT"
    SELECTED_OPPOSITION = "SELECTED_OPPOSITION"
    SUPPRESSED_CORRELATED = "SUPPRESSED_CORRELATED"
    SUPPRESSED_FUTURE = "SUPPRESSED_FUTURE"
    SUPPRESSED_FACT_MISSING = "SUPPRESSED_FACT_MISSING"
    SUPPRESSED_FACT_QUALITY = "SUPPRESSED_FACT_QUALITY"
    SUPPRESSED_SOURCE_MISSING = "SUPPRESSED_SOURCE_MISSING"
    SUPPRESSED_SOURCE_STATE = "SUPPRESSED_SOURCE_STATE"
    SUPPRESSED_AUTHORITY = "SUPPRESSED_AUTHORITY"
    SUPPRESSED_NON_DIRECTIONAL = "SUPPRESSED_NON_DIRECTIONAL"


NON_VOTING_ROLES = {
    SourceRole.REFERENCE_ONLY,
    SourceRole.SHADOW_UPSTREAM,
    SourceRole.EXPERIMENTAL,
}


class ResolutionProfile(BaseModel):
    model_config = MODEL_CONFIG

    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    family_weights: dict[EvidenceFamily, float]
    required_families: tuple[EvidenceFamily, ...] = ()
    required_source_ids: tuple[str, ...] = ()
    min_completeness: float = Field(default=1.0, ge=0, le=1)
    state_ceiling: StateCeiling = StateCeiling.WAIT
    allowed_data_modes: tuple[DataMode, ...] = ()
    corroboration_epsilon: Literal[0.0] = 0.0

    @model_validator(mode="after")
    def validate_profile(self) -> "ResolutionProfile":
        if not self.family_weights:
            raise ValueError("family_weights cannot be empty")
        if any(weight < 0 or weight > 1 for weight in self.family_weights.values()):
            raise ValueError("family weights must be between zero and one")
        if sum(self.family_weights.values()) > 1.000001:
            raise ValueError("family weights cannot sum above one")
        if any(
            family not in self.family_weights or self.family_weights[family] <= 0
            for family in self.required_families
        ):
            raise ValueError("required families need a positive profile weight")
        if EvidenceFamily.EXPERIMENTAL in self.family_weights:
            raise ValueError("EXPERIMENTAL cannot receive production rank weight")
        if self.state_ceiling is StateCeiling.CONFIRMED and not self.allowed_data_modes:
            raise ValueError("CONFIRMED profile requires allowed_data_modes")
        if self.state_ceiling is StateCeiling.CONFIRMED and not self.required_families:
            raise ValueError("CONFIRMED profile requires independent families")
        if (
            self.state_ceiling is StateCeiling.CONFIRMED
            and not self.required_source_ids
        ):
            raise ValueError("CONFIRMED profile requires authoritative sources")
        return self


class ResolvedClaim(BaseModel):
    model_config = MODEL_CONFIG

    claim_id: str
    family: EvidenceFamily
    correlation_group: str
    disposition: ClaimDisposition
    strength: float = Field(ge=0, le=1)
    reason: str


class CorrelationGroupResolution(BaseModel):
    model_config = MODEL_CONFIG

    family: EvidenceFamily
    correlation_group: str
    selected_support_claim_id: str | None = None
    selected_support_strength: float = Field(default=0, ge=0, le=1)
    selected_opposition_claim_id: str | None = None
    selected_opposition_strength: float = Field(default=0, ge=0, le=1)
    suppressed_claim_ids: tuple[str, ...] = ()


class FamilyResolution(BaseModel):
    model_config = MODEL_CONFIG

    family: EvidenceFamily
    weight: float = Field(ge=0, le=1)
    support_strength: float = Field(ge=0, le=1)
    opposition_strength: float = Field(ge=0, le=1)
    net_strength: float = Field(ge=0, le=1)
    selected_support_claim_ids: tuple[str, ...] = ()
    selected_opposition_claim_ids: tuple[str, ...] = ()
    suppressed_claim_ids: tuple[str, ...] = ()


class EvidenceResolution(BaseModel):
    model_config = MODEL_CONFIG

    profile_id: str
    profile_version: str
    decision_at: datetime
    evidence_direction: EvidenceDirection
    state: SelectionState
    state_ceiling: StateCeiling = StateCeiling.WAIT
    support_strength: float = Field(ge=0, le=1)
    opposition_strength: float = Field(ge=0, le=1)
    evidence_strength: float = Field(ge=0, le=1)
    corroboration_bonus: Literal[0.0] = 0.0
    family_supports: tuple[EvidenceFamily, ...] = ()
    family_opposes: tuple[EvidenceFamily, ...] = ()
    family_missing: tuple[EvidenceFamily, ...] = ()
    selected_claim_ids: tuple[str, ...] = ()
    suppressed_claim_ids: tuple[str, ...] = ()
    gate_results: tuple[SelectionGateResult, ...] = ()
    groups: tuple[CorrelationGroupResolution, ...] = ()
    families: tuple[FamilyResolution, ...] = ()
    claims: tuple[ResolvedClaim, ...] = ()
    reason: str

    @field_validator("decision_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decision_at must be timezone-aware")
        return value

    @computed_field(return_type=tuple[str, ...])
    @property
    def gate_codes(self) -> tuple[str, ...]:
        return tuple(gate.code for gate in self.gate_results)

    @model_validator(mode="after")
    def enforce_resolution_contract(self) -> "EvidenceResolution":
        if (
            self.state is SelectionState.CONFIRMED
            and self.state_ceiling is not StateCeiling.CONFIRMED
        ):
            raise ValueError("CONFIRMED exceeds the resolution state ceiling")
        if self.corroboration_bonus != 0:
            raise ValueError("Q5-R2 corroboration bonus must remain zero")
        return self


def _relation(
    claim_direction: EvidenceDirection,
    target_direction: EvidenceDirection,
) -> Literal["SUPPORT", "OPPOSITION"] | None:
    if target_direction is EvidenceDirection.BULLISH:
        if claim_direction is EvidenceDirection.BULLISH:
            return "SUPPORT"
        if claim_direction is EvidenceDirection.BEARISH:
            return "OPPOSITION"
    elif target_direction is EvidenceDirection.BEARISH:
        if claim_direction is EvidenceDirection.BEARISH:
            return "SUPPORT"
        if claim_direction is EvidenceDirection.BULLISH:
            return "OPPOSITION"
    return None


def _suppressed(
    claim: EvidenceClaim,
    disposition: ClaimDisposition,
    reason: str,
) -> ResolvedClaim:
    return ResolvedClaim(
        claim_id=claim.claim_id,
        family=claim.family,
        correlation_group=claim.correlation_group,
        disposition=disposition,
        strength=claim.strength_before_caps,
        reason=reason,
    )


def _claim_eligibility(
    claim: EvidenceClaim,
    *,
    decision_at: datetime,
    facts: dict[str, NormalizedFact],
    source_results: dict[str, SourceResult],
) -> tuple[ClaimDisposition, str] | None:
    if claim.available_at > decision_at:
        return (
            ClaimDisposition.SUPPRESSED_FUTURE,
            "Claim was not available at the decision time.",
        )
    if claim.authority in NON_VOTING_ROLES:
        return (
            ClaimDisposition.SUPPRESSED_AUTHORITY,
            f"{claim.authority.value} cannot enter production rank.",
        )

    for fact_id in claim.source_fact_ids:
        fact = facts.get(fact_id)
        if fact is None:
            return (
                ClaimDisposition.SUPPRESSED_FACT_MISSING,
                f"Source fact {fact_id} is missing.",
            )
        if not fact.is_eligible_at(decision_at):
            return (
                ClaimDisposition.SUPPRESSED_FUTURE,
                f"Source fact {fact_id} was unavailable at decision time.",
            )
        if fact.quality_state != "STRUCTURED_OK":
            return (
                ClaimDisposition.SUPPRESSED_FACT_QUALITY,
                f"Source fact {fact_id} is {fact.quality_state}.",
            )
        source_result = source_results.get(fact.source_id)
        if source_result is None:
            return (
                ClaimDisposition.SUPPRESSED_SOURCE_MISSING,
                f"Source result {fact.source_id} is missing.",
            )
        if source_result.role is not claim.authority:
            return (
                ClaimDisposition.SUPPRESSED_AUTHORITY,
                "Claim authority does not match its source result.",
            )
        if not source_result.is_available_at(decision_at):
            return (
                ClaimDisposition.SUPPRESSED_FUTURE,
                f"Source result {fact.source_id} was unavailable at decision time.",
            )
        if (
            source_result.state is not SourceResultState.STRUCTURED_OK
            or source_result.freshness != "FRESH"
        ):
            return (
                ClaimDisposition.SUPPRESSED_SOURCE_STATE,
                f"Source result {fact.source_id} is {source_result.state.value}.",
            )
    return None


def _gate(
    code: str,
    outcome: GateOutcome,
    reason: str,
) -> SelectionGateResult:
    return SelectionGateResult(
        code=code,
        outcome=outcome,
        blocks_confirmed=outcome
        in {
            GateOutcome.WAIT,
            GateOutcome.REJECT,
            GateOutcome.UNKNOWN,
        },
        reason=reason,
        required=True,
    )


def _append_gate(
    gates: list[SelectionGateResult],
    gate: SelectionGateResult,
) -> None:
    if gate.code not in {item.code for item in gates}:
        gates.append(gate)


def _source_failure_gate(
    source_id: str,
    result: SourceResult | None,
    *,
    decision_at: datetime,
) -> SelectionGateResult | None:
    if result is None:
        return _gate(
            f"WAIT_SOURCE_MISSING_{source_id}",
            GateOutcome.WAIT,
            f"Required source {source_id} has no result.",
        )
    if not result.is_available_at(decision_at):
        return _gate(
            f"WAIT_SOURCE_TIME_{source_id}",
            GateOutcome.WAIT,
            f"Required source {source_id} has invalid availability.",
        )
    if (
        result.state
        in {
            SourceResultState.STRUCTURED_OK,
            SourceResultState.VALID_EMPTY,
        }
        and result.freshness == "FRESH"
    ):
        return None
    return _gate(
        f"WAIT_SOURCE_{result.state.value}_{source_id}",
        GateOutcome.WAIT,
        (
            f"Required source {source_id} is {result.state.value}; "
            "recoverable evidence failure maps to WAIT."
        ),
    )


def resolve_evidence(
    *,
    profile: ResolutionProfile,
    decision_at: datetime,
    evidence_direction: EvidenceDirection,
    claims: tuple[EvidenceClaim, ...],
    facts: tuple[NormalizedFact, ...],
    source_results: tuple[SourceResult, ...],
    completeness: float,
    existing_gates: tuple[SelectionGateResult, ...] = (),
    discovery_only: bool = False,
    data_mode: DataMode = DataMode.SYNTHETIC_TEST,
) -> EvidenceResolution:
    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise ValueError("decision_at must be timezone-aware")
    if completeness < 0 or completeness > 1:
        raise ValueError("completeness must be between zero and one")

    fact_map = {fact.fact_id: fact for fact in facts}
    if len(fact_map) != len(facts):
        raise ValueError("fact_id values must be unique")
    source_map = {result.source_id: result for result in source_results}
    if len(source_map) != len(source_results):
        raise ValueError("source_id values must be unique")
    claim_map = {claim.claim_id: claim for claim in claims}
    if len(claim_map) != len(claims):
        raise ValueError("claim_id values must be unique")

    resolved: dict[str, ResolvedClaim] = {}
    buckets: dict[
        tuple[EvidenceFamily, str],
        dict[str, list[EvidenceClaim]],
    ] = defaultdict(lambda: {"SUPPORT": [], "OPPOSITION": []})

    for claim in sorted(claims, key=lambda item: item.claim_id):
        failure = _claim_eligibility(
            claim,
            decision_at=decision_at,
            facts=fact_map,
            source_results=source_map,
        )
        if failure is not None:
            resolved[claim.claim_id] = _suppressed(claim, *failure)
            continue
        relation = _relation(claim.direction, evidence_direction)
        if relation is None:
            resolved[claim.claim_id] = _suppressed(
                claim,
                ClaimDisposition.SUPPRESSED_NON_DIRECTIONAL,
                "Claim direction is not support or opposition for this candidate.",
            )
            continue
        buckets[(claim.family, claim.correlation_group)][relation].append(claim)

    group_results: list[CorrelationGroupResolution] = []
    for (family, group), sides in sorted(
        buckets.items(),
        key=lambda item: (item[0][0].value, item[0][1]),
    ):
        selected: dict[str, EvidenceClaim | None] = {
            "SUPPORT": None,
            "OPPOSITION": None,
        }
        suppressed_ids: list[str] = []
        for relation in ("SUPPORT", "OPPOSITION"):
            ranked = sorted(
                sides[relation],
                key=lambda item: (-item.strength_before_caps, item.claim_id),
            )
            if ranked:
                winner = ranked[0]
                selected[relation] = winner
                disposition = (
                    ClaimDisposition.SELECTED_SUPPORT
                    if relation == "SUPPORT"
                    else ClaimDisposition.SELECTED_OPPOSITION
                )
                resolved[winner.claim_id] = ResolvedClaim(
                    claim_id=winner.claim_id,
                    family=winner.family,
                    correlation_group=winner.correlation_group,
                    disposition=disposition,
                    strength=winner.strength_before_caps,
                    reason="Strongest eligible claim for this correlation-group side.",
                )
                for claim in ranked[1:]:
                    suppressed_ids.append(claim.claim_id)
                    resolved[claim.claim_id] = _suppressed(
                        claim,
                        ClaimDisposition.SUPPRESSED_CORRELATED,
                        (
                            "A stronger claim in the same correlation group "
                            "already represents this side."
                        ),
                    )
        support = selected["SUPPORT"]
        opposition = selected["OPPOSITION"]
        group_results.append(
            CorrelationGroupResolution(
                family=family,
                correlation_group=group,
                selected_support_claim_id=support.claim_id if support else None,
                selected_support_strength=(
                    support.strength_before_caps if support else 0
                ),
                selected_opposition_claim_id=(
                    opposition.claim_id if opposition else None
                ),
                selected_opposition_strength=(
                    opposition.strength_before_caps if opposition else 0
                ),
                suppressed_claim_ids=tuple(sorted(suppressed_ids)),
            )
        )

    family_results: list[FamilyResolution] = []
    supports: list[EvidenceFamily] = []
    opposes: list[EvidenceFamily] = []
    missing: list[EvidenceFamily] = []
    for family in EvidenceFamily:
        family_groups = [item for item in group_results if item.family is family]
        support_strength = max(
            (item.selected_support_strength for item in family_groups),
            default=0,
        )
        opposition_strength = max(
            (item.selected_opposition_strength for item in family_groups),
            default=0,
        )
        if support_strength > opposition_strength:
            supports.append(family)
        elif opposition_strength > 0:
            opposes.append(family)
        if (
            family in profile.required_families
            and support_strength == 0
            and opposition_strength == 0
        ):
            missing.append(family)
        family_results.append(
            FamilyResolution(
                family=family,
                weight=profile.family_weights.get(family, 0),
                support_strength=support_strength,
                opposition_strength=opposition_strength,
                net_strength=max(support_strength - opposition_strength, 0),
                selected_support_claim_ids=tuple(
                    sorted(
                        item.selected_support_claim_id
                        for item in family_groups
                        if item.selected_support_claim_id
                    )
                ),
                selected_opposition_claim_ids=tuple(
                    sorted(
                        item.selected_opposition_claim_id
                        for item in family_groups
                        if item.selected_opposition_claim_id
                    )
                ),
                suppressed_claim_ids=tuple(
                    sorted(
                        claim_id
                        for item in family_groups
                        for claim_id in item.suppressed_claim_ids
                    )
                ),
            )
        )

    support_strength = min(
        sum(item.weight * item.support_strength for item in family_results),
        1.0,
    )
    opposition_strength = min(
        sum(item.weight * item.opposition_strength for item in family_results),
        1.0,
    )
    evidence_strength = max(support_strength - opposition_strength, 0)

    gates = list(existing_gates)
    hard_veto_present = any(
        gate.outcome is GateOutcome.REJECT for gate in existing_gates
    )
    if not hard_veto_present:
        for source_id in profile.required_source_ids:
            source_gate = _source_failure_gate(
                source_id,
                source_map.get(source_id),
                decision_at=decision_at,
            )
            if source_gate is not None:
                _append_gate(gates, source_gate)
        if completeness < profile.min_completeness:
            _append_gate(
                gates,
                _gate(
                    "WAIT_PARTIAL_SCAN",
                    GateOutcome.WAIT,
                    (
                        f"Scan completeness {completeness:.4f} is below profile "
                        f"minimum {profile.min_completeness:.4f}."
                    ),
                ),
            )
    if not discovery_only and not hard_veto_present:
        by_family = {item.family: item for item in family_results}
        for family in profile.required_families:
            result = by_family[family]
            if result.support_strength == 0 and result.opposition_strength == 0:
                _append_gate(
                    gates,
                    _gate(
                        f"WAIT_REQUIRED_FAMILY_{family.value}",
                        GateOutcome.WAIT,
                        f"Required family {family.value} has no eligible support.",
                    ),
                )
            elif result.opposition_strength >= result.support_strength:
                _append_gate(
                    gates,
                    _gate(
                        f"WAIT_FAMILY_CONFLICT_{family.value}",
                        GateOutcome.WAIT,
                        f"Required family {family.value} is opposed or unresolved.",
                    ),
                )

        if profile.state_ceiling is StateCeiling.CONFIRMED:
            if data_mode not in profile.allowed_data_modes:
                _append_gate(
                    gates,
                    _gate(
                        "WAIT_DATA_MODE",
                        GateOutcome.WAIT,
                        (
                            f"Data mode {data_mode.value} is not eligible for "
                            "this confirmation profile."
                        ),
                    ),
                )

            selected_support_ids = {
                claim_id
                for family in profile.required_families
                for claim_id in by_family[family].selected_support_claim_ids
            }
            untrusted_claims = sorted(
                claim_id
                for claim_id in selected_support_ids
                if not claim_map[claim_id].can_support_confirmed
            )
            if untrusted_claims:
                _append_gate(
                    gates,
                    _gate(
                        "WAIT_CLAIM_AUTHORITY",
                        GateOutcome.WAIT,
                        (
                            "Required-family claims are not authorized for "
                            f"CONFIRMED: {', '.join(untrusted_claims)}."
                        ),
                    ),
                )

            untrusted_sources = sorted(
                source_id
                for source_id in profile.required_source_ids
                if source_id in source_map
                and not source_map[source_id].can_support_confirmed
            )
            if untrusted_sources:
                _append_gate(
                    gates,
                    _gate(
                        "WAIT_SOURCE_AUTHORITY",
                        GateOutcome.WAIT,
                        (
                            "Required sources are not authorized for CONFIRMED: "
                            f"{', '.join(untrusted_sources)}."
                        ),
                    ),
                )

    has_reject = any(gate.outcome is GateOutcome.REJECT for gate in gates)
    has_wait = any(gate.blocks_confirmed for gate in gates)
    if has_reject:
        state = SelectionState.REJECT
    elif has_wait:
        state = SelectionState.WAIT
    elif discovery_only:
        state = SelectionState.WATCH
    elif profile.state_ceiling is StateCeiling.CONFIRMED:
        state = SelectionState.CONFIRMED
    else:
        _append_gate(
            gates,
            _gate(
                "WAIT_Q5_R2_NO_CONFIRMED",
                GateOutcome.WAIT,
                "Q5-R2 resolver is capped at WAIT until Q5-R3 closed-bar acceptance.",
            ),
        )
        state = SelectionState.WAIT

    selected_ids = tuple(
        sorted(
            claim_id
            for claim_id, item in resolved.items()
            if item.disposition
            in {
                ClaimDisposition.SELECTED_SUPPORT,
                ClaimDisposition.SELECTED_OPPOSITION,
            }
        )
    )
    suppressed_ids = tuple(
        sorted(claim_id for claim_id in resolved if claim_id not in selected_ids)
    )
    if state is SelectionState.REJECT:
        reason = next(
            gate.reason for gate in gates if gate.outcome is GateOutcome.REJECT
        )
    elif state is SelectionState.WAIT:
        reason = next(gate.reason for gate in gates if gate.blocks_confirmed)
    else:
        reason = "Eligible discovery evidence remains in the WATCH queue."

    return EvidenceResolution(
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        decision_at=decision_at,
        evidence_direction=evidence_direction,
        state=state,
        state_ceiling=profile.state_ceiling,
        support_strength=round(support_strength, 6),
        opposition_strength=round(opposition_strength, 6),
        evidence_strength=round(evidence_strength, 6),
        family_supports=tuple(supports),
        family_opposes=tuple(opposes),
        family_missing=tuple(missing),
        selected_claim_ids=selected_ids,
        suppressed_claim_ids=suppressed_ids,
        gate_results=tuple(gates),
        groups=tuple(group_results),
        families=tuple(family_results),
        claims=tuple(resolved[key] for key in sorted(resolved)),
        reason=reason,
    )
