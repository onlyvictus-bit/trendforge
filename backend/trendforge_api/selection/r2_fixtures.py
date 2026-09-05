from __future__ import annotations

from datetime import timedelta
from typing import Literal

from pydantic import BaseModel, model_validator

from ..source_contracts import SourceResult, SourceRole
from .contracts import (
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    MODEL_CONFIG,
    NormalizedFact,
    SelectionCandidate,
    SelectionFixtureBatch,
    SelectionScanRun,
    SelectionState,
    StateCeiling,
    stable_id,
)
from .fixtures import build_q5_r1_fixture_batch
from .resolver import EvidenceResolution, ResolutionProfile, resolve_evidence


R2_PROFILE = ResolutionProfile(
    profile_id="PRF-Q5-R2-FIXTURE",
    profile_version="1.0.0",
    family_weights={
        EvidenceFamily.TRADABILITY_AND_SAFETY: 0.20,
        EvidenceFamily.MARKET_AND_SECTOR_CONTEXT: 0.15,
        EvidenceFamily.STRUCTURE: 0.30,
        EvidenceFamily.PARTICIPATION: 0.25,
        EvidenceFamily.EVENT_AND_SPONSOR: 0.10,
    },
    required_families=(
        EvidenceFamily.STRUCTURE,
        EvidenceFamily.PARTICIPATION,
    ),
    required_source_ids=("SRC-NSE-EOD", "SRC-NSE-GSM"),
    min_completeness=1.0,
)


class Q5R2FixtureBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: Literal["Q5-R2"] = "Q5-R2"
    acceptance_ceiling: Literal["WATCH_WAIT_REJECT_ONLY"] = "WATCH_WAIT_REJECT_ONLY"
    public_states: tuple[SelectionState, ...] = tuple(SelectionState)
    profile: ResolutionProfile
    run: SelectionScanRun
    candidates: tuple[SelectionCandidate, ...]
    resolutions: tuple[EvidenceResolution, ...]
    source_results: tuple[SourceResult, ...]
    facts: tuple[NormalizedFact, ...]
    claims: tuple[EvidenceClaim, ...]

    @model_validator(mode="after")
    def enforce_q5_r2_contract(self) -> "Q5R2FixtureBatch":
        if any(item.state is SelectionState.CONFIRMED for item in self.candidates):
            raise ValueError("Q5-R2 fixtures cannot emit CONFIRMED")
        if any(item.corroboration_bonus != 0 for item in self.resolutions):
            raise ValueError("Q5-R2 corroboration bonus must remain zero")
        by_symbol = {
            candidate.instrument.symbol: candidate.state
            for candidate in self.candidates
        }
        if set(by_symbol.values()) != {
            SelectionState.WATCH,
            SelectionState.WAIT,
            SelectionState.REJECT,
        }:
            raise ValueError("Q5-R2 fixtures must cover WATCH, WAIT and REJECT")
        return self


def _claim(
    fact: NormalizedFact,
    *,
    feature_id: str,
    family: EvidenceFamily,
    group: str,
    direction: EvidenceDirection,
    strength: float,
    authority: SourceRole = SourceRole.OFFICIAL_GATE,
    available_offset_minutes: int = 0,
) -> EvidenceClaim:
    return EvidenceClaim.create(
        feature_id=feature_id,
        feature_version="1.0.0",
        family=family,
        correlation_group=group,
        direction=direction,
        strength_before_caps=strength,
        source_fact_ids=(fact.fact_id,),
        authority=authority,
        available_at=(
            fact.lineage.available_at + timedelta(minutes=available_offset_minutes)
        ),
        state_ceiling=StateCeiling.WAIT,
        can_support_confirmed=False,
        explanation=f"Deterministic Q5-R2 claim {feature_id}.",
    )


def _build_claims(base: SelectionFixtureBatch) -> tuple[EvidenceClaim, ...]:
    watch, wait_close, early_confirm, _reject = base.facts
    return (
        _claim(
            watch,
            feature_id="FTR-018",
            family=EvidenceFamily.PARTICIPATION,
            group="CG_ACTIVITY_SESSION",
            direction=EvidenceDirection.BULLISH,
            strength=0.45,
        ),
        _claim(
            watch,
            feature_id="FTR-017",
            family=EvidenceFamily.PARTICIPATION,
            group="CG_ACTIVITY_SESSION",
            direction=EvidenceDirection.BULLISH,
            strength=0.30,
        ),
        _claim(
            watch,
            feature_id="FTR-018",
            family=EvidenceFamily.PARTICIPATION,
            group="CG_ACTIVITY_SESSION",
            direction=EvidenceDirection.BULLISH,
            strength=0.99,
            authority=SourceRole.SHADOW_UPSTREAM,
        ),
        _claim(
            wait_close,
            feature_id="FTR-005",
            family=EvidenceFamily.STRUCTURE,
            group="CG_PRICE_STRUCTURE",
            direction=EvidenceDirection.BULLISH,
            strength=0.55,
        ),
        _claim(
            early_confirm,
            feature_id="FTR-006",
            family=EvidenceFamily.STRUCTURE,
            group="CG_PRICE_STRUCTURE",
            direction=EvidenceDirection.BULLISH,
            strength=0.80,
        ),
        _claim(
            early_confirm,
            feature_id="FTR-017",
            family=EvidenceFamily.PARTICIPATION,
            group="CG_ACTIVITY_SESSION",
            direction=EvidenceDirection.BULLISH,
            strength=0.70,
        ),
        _claim(
            early_confirm,
            feature_id="FTR-005",
            family=EvidenceFamily.STRUCTURE,
            group="CG_PRICE_STRUCTURE",
            direction=EvidenceDirection.BEARISH,
            strength=0.40,
        ),
        _claim(
            early_confirm,
            feature_id="FTR-017",
            family=EvidenceFamily.PARTICIPATION,
            group="CG_ACTIVITY_SESSION",
            direction=EvidenceDirection.BULLISH,
            strength=0.95,
            available_offset_minutes=1800,
        ),
    )


def _candidate_claims(
    fact: NormalizedFact,
    claims: tuple[EvidenceClaim, ...],
) -> tuple[EvidenceClaim, ...]:
    return tuple(claim for claim in claims if fact.fact_id in claim.source_fact_ids)


def _resolved_candidate(
    *,
    base: SelectionCandidate,
    run: SelectionScanRun,
    resolution: EvidenceResolution,
) -> SelectionCandidate:
    contradiction = (
        "Opposing families: "
        + ", ".join(family.value for family in resolution.family_opposes)
        if resolution.family_opposes
        else base.contradiction
    )
    missing_proof = tuple(family.value for family in resolution.family_missing)
    if not missing_proof:
        missing_proof = base.missing_proof
    payload = base.model_dump(mode="python", exclude={"gate_codes"})
    payload.update(
        {
            "candidate_id": stable_id(
                "cand",
                run.run_id,
                base.instrument.instrument_id,
            ),
            "run_id": run.run_id,
            "profile_id": R2_PROFILE.profile_id,
            "profile_version": R2_PROFILE.profile_version,
            "state": resolution.state,
            "state_ceiling": StateCeiling.WAIT,
            "family_supports": resolution.family_supports,
            "family_opposes": resolution.family_opposes,
            "family_missing": resolution.family_missing,
            "top_reason": resolution.reason,
            "contradiction": contradiction,
            "missing_proof": missing_proof,
            "next_confirmation": (
                "Satisfy the named WAIT gates in a later comparable run."
                if resolution.state is SelectionState.WAIT
                else base.next_confirmation
            ),
            "evidence_strength": resolution.evidence_strength,
            "gate_results": resolution.gate_results,
            "what_changed": "Q5-R2 family and correlation-group resolution applied.",
        }
    )
    return SelectionCandidate.model_validate(payload)


def build_q5_r2_fixture_batch() -> Q5R2FixtureBatch:
    base = build_q5_r1_fixture_batch()
    run = SelectionScanRun.create(
        profile_id=R2_PROFILE.profile_id,
        profile_version=R2_PROFILE.profile_version,
        as_of=base.run.as_of,
        universe_version="fixture-universe-r2-1",
        data_mode=base.run.data_mode,
        eligible_count=len(base.candidates),
        scanned_count=len(base.candidates),
    )
    claims = _build_claims(base)
    resolutions: list[EvidenceResolution] = []
    candidates: list[SelectionCandidate] = []

    for candidate, fact in zip(base.candidates, base.facts, strict=True):
        existing_gates = (
            ()
            if candidate.instrument.symbol == "TF_WAIT_EARLY_CONFIRM"
            else candidate.gate_results
        )
        resolution = resolve_evidence(
            profile=R2_PROFILE,
            decision_at=run.as_of,
            evidence_direction=candidate.evidence_direction,
            claims=_candidate_claims(fact, claims),
            facts=(fact,),
            source_results=base.source_results,
            completeness=run.completeness,
            existing_gates=existing_gates,
            discovery_only=candidate.state is SelectionState.WATCH,
        )
        resolutions.append(resolution)
        candidates.append(
            _resolved_candidate(base=candidate, run=run, resolution=resolution)
        )

    return Q5R2FixtureBatch(
        profile=R2_PROFILE,
        run=run,
        candidates=tuple(candidates),
        resolutions=tuple(resolutions),
        source_results=base.source_results,
        facts=base.facts,
        claims=claims,
    )
