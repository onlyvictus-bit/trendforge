"""Deterministic Q5-R6 state-history, inspector, and PIT fixtures."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from ..source_contracts import SourceRole
from .contracts import (
    MODEL_CONFIG,
    BarIdentity,
    DataMode,
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    GateOutcome,
    NormalizedFact,
    PointInTimeLineage,
    SelectionGateResult,
    SelectionState,
    StateCeiling,
)
from .pit_path import PITBarObservation, PITDirection, PITPathEvidence
from .history_validation import (
    CandidateInspector,
    ConfirmationContext,
    StructureSubstate,
    DriftAssessment,
    DriftMetricArtifact,
    InspectorSection,
    PITOutcome,
    PITValidationProfile,
    PITValidationResult,
    SelectionHistory,
    ValidationArtifactProof,
    ValidationCostProfile,
    assess_validation_drift,
    build_state_event,
    evaluate_pit_validation,
)


IST = timezone(timedelta(hours=5, minutes=30))
R6_DECISION_AT = datetime(2026, 7, 14, 15, 30, tzinfo=IST)
R6_EVALUATED_AT = datetime(2026, 7, 19, 9, 0, tzinfo=IST)


class Q5R6RadarRow(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    profile: str = Field(min_length=1)
    state: SelectionState
    evidence_strength: float = Field(ge=0, le=1)
    evidence_strength_label: Literal["Evidence strength - not win probability"] = (
        "Evidence strength - not win probability"
    )
    why_appeared: str = Field(min_length=1)
    what_changed: str = Field(min_length=1)
    top_support: str = Field(min_length=1)
    strongest_contradiction: str = Field(min_length=1)
    missing_proof: str = Field(min_length=1)
    freshness: str = Field(min_length=1)
    confirmation_condition: str = Field(min_length=1)
    invalidation_condition: str = Field(min_length=1)
    completeness: float = Field(ge=0, le=1)
    no_action_reason: str = Field(min_length=1)
    executable: Literal[False] = False


class Q5R6FixtureBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: Literal["Q5-R6"] = "Q5-R6"
    acceptance_ceiling: Literal["NO_PERFORMANCE_OR_PROBABILITY_UI"] = (
        "NO_PERFORMANCE_OR_PROBABILITY_UI"
    )
    fixture_only: Literal[True] = True
    production_authorized: Literal[False] = False
    executable: Literal[False] = False
    radar: tuple[Q5R6RadarRow, ...]
    histories: tuple[SelectionHistory, ...]
    cost_profile: ValidationCostProfile
    # Immutable price paths are retained for offline validation, not serialized
    # through the trader-facing fixture endpoint.
    outcomes: tuple[PITOutcome, ...] = Field(exclude=True)
    validation_results: tuple[PITValidationResult, ...]
    drift_assessments: tuple[DriftAssessment, ...]
    inspector: CandidateInspector

    @model_validator(mode="after")
    def enforce_r6_boundary(self) -> "Q5R6FixtureBatch":
        if any(result.performance_ui_allowed for result in self.validation_results):
            raise ValueError("fixture validation cannot expose performance UI")
        if any(result.probability_ui_allowed for result in self.validation_results):
            raise ValueError("Q5-R6 cannot expose probability UI")
        if (
            self.inspector.performance_ui_visible
            or self.inspector.probability_ui_visible
        ):
            raise ValueError("fixture inspector must hide performance and probability")
        if any(row.executable for row in self.radar):
            raise ValueError("Q5-R6 radar is non-executable")

        history_by_candidate = {
            history.candidate_id: history for history in self.histories
        }
        if len(history_by_candidate) != len(self.histories):
            raise ValueError("Q5-R6 histories must have unique candidates")
        radar_by_candidate = {row.candidate_id: row for row in self.radar}
        if len(radar_by_candidate) != len(self.radar):
            raise ValueError("Q5-R6 radar rows must have unique candidates")
        history = history_by_candidate.get(self.inspector.candidate_id)
        radar = radar_by_candidate.get(self.inspector.candidate_id)
        if history is None or radar is None:
            raise ValueError("inspector candidate must exist in radar and history")
        if (
            history.current_state is not self.inspector.state
            or radar.state is not self.inspector.state
        ):
            raise ValueError("radar, history, and inspector state must agree")
        if self.inspector.validation_status not in {
            result.status for result in self.validation_results
        }:
            raise ValueError("inspector validation status needs a matching result")
        return self


def _digest(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


def _confirmation_context(decision_at: datetime) -> ConfirmationContext:
    lineage = PointInTimeLineage(
        event_time=decision_at - timedelta(hours=1),
        published_at=decision_at - timedelta(minutes=45),
        available_at=decision_at - timedelta(minutes=30),
        received_at=decision_at - timedelta(minutes=29),
        retrieved_at=decision_at - timedelta(minutes=28),
        revision_id="R6-CONFIRM-REV-1",
        artifact_hash=_digest("r6-confirmation-source"),
    )
    common = {
        "instrument_id": "INS-R6-RELIANCE",
        "source_id": "SRC-NSE-EOD",
        "data_date": decision_at.date(),
        "lineage": lineage,
        "quality_state": "STRUCTURED_OK",
    }
    structure_fact = NormalizedFact.create(
        **common,
        dataset_root="NSE_EOD_PRICE",
        business_keys={"symbol": "RELIANCE", "kind": "closed_price"},
        payload={"closed": True, "fixture": True},
    )
    participation_fact = NormalizedFact.create(
        **common,
        dataset_root="NSE_EOD_VOLUME",
        business_keys={"symbol": "RELIANCE", "kind": "closed_volume"},
        payload={"closed": True, "fixture": True},
    )
    structure_claim = EvidenceClaim.create(
        feature_id="FTR-006",
        feature_version="1.0.0",
        family=EvidenceFamily.STRUCTURE,
        correlation_group="CG_PRICE_STRUCTURE",
        direction=EvidenceDirection.BULLISH,
        strength_before_caps=0.72,
        source_fact_ids=(structure_fact.fact_id,),
        authority=SourceRole.OFFICIAL_GATE,
        available_at=lineage.available_at,
        event_time=lineage.event_time,
        published_at=lineage.published_at,
        received_at=lineage.received_at,
        revision_id=lineage.revision_id,
        artifact_hash=lineage.artifact_hash,
        state_ceiling=StateCeiling.CONFIRMED,
        can_support_confirmed=True,
        explanation="Closed EOD structure passed from official price evidence.",
    )
    participation_claim = EvidenceClaim.create(
        feature_id="FTR-017",
        feature_version="1.0.0",
        family=EvidenceFamily.PARTICIPATION,
        correlation_group="CG_ACTIVITY_SESSION",
        direction=EvidenceDirection.BULLISH,
        strength_before_caps=0.68,
        source_fact_ids=(participation_fact.fact_id,),
        authority=SourceRole.OFFICIAL_GATE,
        available_at=lineage.available_at,
        event_time=lineage.event_time,
        published_at=lineage.published_at,
        received_at=lineage.received_at,
        revision_id=lineage.revision_id,
        artifact_hash=lineage.artifact_hash,
        state_ceiling=StateCeiling.CONFIRMED,
        can_support_confirmed=True,
        explanation="Closed EOD participation passed from official volume evidence.",
    )
    closed_bar = BarIdentity.create(
        instrument_id="INS-R6-RELIANCE",
        timeframe="1d",
        session_id=decision_at.date().isoformat(),
        open_time=decision_at.replace(hour=9, minute=15),
        close_time=decision_at,
        is_closed=True,
        adjustment_version="NSE-EOD-ADJ-CA-V3",
        raw_hash=_digest("r6-confirmation-closed-bar"),
        source_mode=DataMode.EOD_RESEARCH,
    )
    gates = (
        SelectionGateResult(
            code="TRADABILITY_AND_SAFETY_PASS",
            outcome=GateOutcome.PASS,
            blocks_confirmed=False,
            reason="Required fixture gate passed.",
        ),
    )
    return ConfirmationContext.create(
        decision_at=decision_at,
        closed_bar=closed_bar,
        required_families=(
            EvidenceFamily.STRUCTURE,
            EvidenceFamily.PARTICIPATION,
        ),
        claims=(structure_claim, participation_claim),
        facts=(structure_fact, participation_fact),
        gate_results=gates,
    )


def _history() -> SelectionHistory:
    candidate_id = "TF-R6-HISTORY-001"
    confirm_time = R6_DECISION_AT + timedelta(days=2)
    context = _confirmation_context(confirm_time)
    claim_ids = tuple(claim.claim_id for claim in context.claims)
    events = (
        build_state_event(
            sequence=1,
            candidate_id=candidate_id,
            comparable_run_id="R6-RUN-001",
            prior_state=SelectionState.WATCH,
            requested_state=SelectionState.CONFIRMED,
            occurred_at=R6_DECISION_AT,
            reason_code="CONFIRM_REQUESTED",
            reason="Closed-bar confirmation was requested.",
            blockers=("WAIT_BAR_CLOSE",),
            added_gate_codes=("WAIT_BAR_CLOSE",),
            structure_substate=StructureSubstate.TESTING,
        ),
        build_state_event(
            sequence=2,
            candidate_id=candidate_id,
            comparable_run_id="R6-RUN-002",
            prior_state=SelectionState.WAIT,
            requested_state=SelectionState.WAIT,
            occurred_at=R6_DECISION_AT + timedelta(days=1),
            reason_code="WAIT_SOURCE_CONFLICT",
            reason="Official correction conflicts with the discovery claim.",
            removed_gate_codes=("WAIT_BAR_CLOSE",),
            added_gate_codes=("WAIT_SOURCE_CONFLICT",),
            source_health_changes=("SRC-NSE-EOD:FRESH->CONFLICT",),
            structure_substate=StructureSubstate.TESTING,
        ),
        build_state_event(
            sequence=3,
            candidate_id=candidate_id,
            comparable_run_id="R6-RUN-003",
            prior_state=SelectionState.WAIT,
            requested_state=SelectionState.CONFIRMED,
            occurred_at=confirm_time,
            reason_code="CLOSED_BAR_CONFIRMED",
            reason="Closed EOD structure and independent participation passed.",
            added_claim_ids=claim_ids,
            removed_gate_codes=("WAIT_SOURCE_CONFLICT",),
            source_health_changes=("SRC-NSE-EOD:CONFLICT->FRESH",),
            confirmation_context=context,
            structure_substate=StructureSubstate.ACCEPTED,
        ),
        build_state_event(
            sequence=4,
            candidate_id=candidate_id,
            comparable_run_id="R6-RUN-004",
            prior_state=SelectionState.CONFIRMED,
            requested_state=SelectionState.WAIT,
            occurred_at=R6_DECISION_AT + timedelta(days=3),
            reason_code="WAIT_SOURCE_CORRECTION",
            reason="A post-decision source revision removed required confirmation.",
            removed_claim_ids=(claim_ids[-1],),
            added_gate_codes=("WAIT_SOURCE_CORRECTION",),
            structure_substate=StructureSubstate.TESTING,
        ),
        build_state_event(
            sequence=5,
            candidate_id=candidate_id,
            comparable_run_id="R6-RUN-005",
            prior_state=SelectionState.WAIT,
            requested_state=SelectionState.REJECT,
            occurred_at=R6_DECISION_AT + timedelta(days=4),
            reason_code="STRUCTURE_INVALIDATED",
            reason="The closed-bar structure invalidation level was breached.",
            hard_veto=True,
            added_gate_codes=("STRUCTURE_INVALIDATED",),
            structure_substate=StructureSubstate.INVALIDATED,
        ),
    )
    return SelectionHistory(
        candidate_id=candidate_id,
        candidate_instance_id=candidate_id,
        initial_state=SelectionState.WATCH,
        current_state=SelectionState.REJECT,
        events=events,
    )


def _cost_profile() -> ValidationCostProfile:
    return ValidationCostProfile(
        profile_id="COST-NSE-EOD-RESEARCH",
        profile_version="1.0.0",
        venue="NSE",
        horizon="5_SESSION",
        brokerage_bps=2.0,
        fees_taxes_bps=4.0,
        spread_bps=5.0,
        slippage_bps=8.0,
        impact_bps=1.0,
        sensitivity_multipliers=(0.75, 1.0, 1.5),
        available_at=R6_DECISION_AT - timedelta(days=30),
    )


def _outcomes(cost: ValidationCostProfile) -> tuple[PITOutcome, ...]:
    scenarios = (
        {
            "name": "target",
            "target": 103.5,
            "stop": 98.0,
            "high": 104.0,
            "low": 99.0,
            "close": 103.0,
            "days": 3,
            "probability": 0.72,
            "reason": None,
        },
        {
            "name": "stop",
            "target": 103.0,
            "stop": 98.2,
            "high": 101.0,
            "low": 98.0,
            "close": 98.5,
            "days": 3,
            "probability": 0.30,
            "reason": None,
        },
        {
            "name": "same-bar",
            "target": 103.0,
            "stop": 98.8,
            "high": 103.2,
            "low": 98.5,
            "close": 100.0,
            "days": 3,
            "probability": 0.30,
            "reason": None,
        },
        {
            "name": "censored",
            "target": 104.0,
            "stop": 97.0,
            "high": 102.0,
            "low": 99.0,
            "close": 100.6,
            "days": 7,
            "probability": None,
            "reason": "Horizon ended without target or stop.",
        },
    )
    rows: list[PITOutcome] = []
    for index, scenario in enumerate(scenarios, start=1):
        decision_at = R6_DECISION_AT - timedelta(days=index * 7)
        horizon_end = decision_at + timedelta(days=7)
        cutoff_at = decision_at + timedelta(days=int(scenario["days"]))
        entry_at = decision_at + timedelta(days=1)
        bar = PITBarObservation.create(
            close_time=cutoff_at,
            available_at=cutoff_at + timedelta(minutes=1),
            open=100.0,
            high=float(scenario["high"]),
            low=float(scenario["low"]),
            close=float(scenario["close"]),
            raw_hash=_digest(f"r6-pit-bar-{scenario['name']}"),
        )
        path = PITPathEvidence.create(
            direction=PITDirection.LONG,
            entry_at=entry_at,
            entry_price=100.0,
            target_price=float(scenario["target"]),
            stop_price=float(scenario["stop"]),
            bars=(bar,),
            source_artifact_hash=_digest(f"r6-pit-path-{scenario['name']}"),
        )
        probability = scenario["probability"]
        candidate_id = f"TF-R6-PIT-{index:03d}"
        rows.append(
            PITOutcome.create_from_path(
                candidate_id=candidate_id,
                decision_at=decision_at,
                entry_policy_version="EOD-CLOSE-ENTRY-V1",
                horizon_end=horizon_end,
                cutoff_at=cutoff_at,
                universe_version=f"NIFTY500-PIT-{decision_at.date().isoformat()}",
                membership_available_at=decision_at - timedelta(days=1),
                raw_bar_version="NSE-EOD-RAW-V1",
                adjusted_bar_version="NSE-EOD-ADJ-CA-V3",
                cost_profile_id=cost.profile_id,
                cost_profile_version=cost.profile_version,
                explicit_cost_bps=cost.total_cost_bps,
                predicted_probability=(
                    float(probability) if probability is not None else None
                ),
                prediction_artifact_hash=(
                    _digest(f"r6-prediction-{index}")
                    if probability is not None
                    else None
                ),
                prediction_available_at=(
                    decision_at - timedelta(minutes=1)
                    if probability is not None
                    else None
                ),
                path_evidence=path,
                delisting_checked=True,
                delisting_check_version="NSE-DELISTING-PIT-V1",
                censored_reason=(
                    str(scenario["reason"]) if scenario["reason"] else None
                ),
            )
        )
    return tuple(rows)


def _no_entry_outcome(cost: ValidationCostProfile) -> PITOutcome:
    decision_at = R6_DECISION_AT - timedelta(days=35)
    horizon_end = decision_at + timedelta(days=7)
    bar = PITBarObservation.create(
        close_time=horizon_end,
        available_at=horizon_end + timedelta(minutes=1),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.2,
        raw_hash=_digest("r6-pit-bar-no-entry"),
    )
    path = PITPathEvidence.create(
        direction=PITDirection.LONG,
        bars=(bar,),
        source_artifact_hash=_digest("r6-pit-path-no-entry"),
    )
    return PITOutcome.create_from_path(
        candidate_id="TF-R6-PIT-NO-ENTRY",
        decision_at=decision_at,
        entry_policy_version="EOD-CLOSE-ENTRY-V1",
        horizon_end=horizon_end,
        cutoff_at=horizon_end,
        universe_version=f"NIFTY500-PIT-{decision_at.date().isoformat()}",
        membership_available_at=decision_at - timedelta(days=1),
        raw_bar_version="NSE-EOD-RAW-V1",
        adjusted_bar_version="NSE-EOD-ADJ-CA-V3",
        cost_profile_id=cost.profile_id,
        cost_profile_version=cost.profile_version,
        explicit_cost_bps=cost.total_cost_bps,
        predicted_probability=None,
        prediction_artifact_hash=None,
        prediction_available_at=None,
        path_evidence=path,
        delisting_checked=True,
        delisting_check_version="NSE-DELISTING-PIT-V1",
        censored_reason="Entry policy never became eligible.",
    )


def _validation_artifacts(
    outcomes: tuple[PITOutcome, ...],
    evaluated_at: datetime,
    *,
    walk_forward_passed: bool = True,
    holdout_passed: bool = True,
) -> tuple[ValidationArtifactProof, ValidationArtifactProof]:
    outcome_ids = tuple(outcome.outcome_id for outcome in outcomes)
    generated_at = evaluated_at - timedelta(minutes=2)
    available_at = evaluated_at - timedelta(minutes=1)
    return (
        ValidationArtifactProof.create(
            artifact_hash=_digest(
                f"r6-walk-forward-{walk_forward_passed}-{outcome_ids}"
            ),
            artifact_kind="WALK_FORWARD",
            split_policy_version="R6-WALK-FORWARD-SPLIT-V1",
            outcome_ids=outcome_ids,
            generated_at=generated_at,
            available_at=available_at,
            passed=walk_forward_passed,
        ),
        ValidationArtifactProof.create(
            artifact_hash=_digest(f"r6-holdout-{holdout_passed}-{outcome_ids}"),
            artifact_kind="HOLDOUT",
            split_policy_version="R6-HOLDOUT-SPLIT-V1",
            outcome_ids=outcome_ids,
            generated_at=generated_at,
            available_at=available_at,
            passed=holdout_passed,
        ),
    )


def _validation_profile() -> PITValidationProfile:
    return PITValidationProfile(
        profile_id="PIT-Q5-R6-EOD-FIXTURE",
        profile_version="1.0.0",
        min_effective_sample=3,
        max_calibration_error=0.12,
        min_net_expectancy=-0.001,
        max_drawdown=0.15,
        max_false_confirmed_rate=0.70,
        max_feature_psi=0.20,
        max_residual_shift=0.15,
    )


def _drift_artifact(
    validation: PITValidationResult,
    *,
    assessed_at: datetime,
    feature_psi: float,
    calibration_error_delta: float,
    residual_shift: float,
) -> DriftMetricArtifact:
    return DriftMetricArtifact.create(
        artifact_hash=_digest(
            f"r6-drift-{validation.run_id}-{feature_psi}-{calibration_error_delta}-{residual_shift}"
        ),
        validation_run_id=validation.run_id,
        baseline_window_hash=_digest(f"r6-drift-baseline-{validation.run_id}"),
        current_window_hash=_digest(f"r6-drift-current-{assessed_at.isoformat()}"),
        available_at=assessed_at,
        feature_psi=feature_psi,
        calibration_error_delta=calibration_error_delta,
        residual_shift=residual_shift,
    )


def _inspector(
    *,
    history: SelectionHistory,
    validation: PITValidationResult,
) -> CandidateInspector:
    sections = (
        InspectorSection(
            section_id="DECISION_PROOF",
            title="Decision Proof",
            status="AVAILABLE",
            summary="One structure and one independent participation claim were selected.",
            items=("CLM-STRUCTURE-1", "CLM-PARTICIPATION-1"),
        ),
        InspectorSection(
            section_id="STRUCTURE_PARTICIPATION",
            title="Structure and Participation",
            status="AVAILABLE",
            summary="Closed EOD inputs only; open bars cannot confirm.",
        ),
        InspectorSection(
            section_id="DERIVATIVES",
            title="Derivatives",
            status="UNKNOWN",
            summary="Optional derivative context was not required for this profile.",
        ),
        InspectorSection(
            section_id="CORPORATE_SPONSOR",
            title="Corporate and Sponsor",
            status="UNKNOWN",
            summary="No sponsor claim was used for confirmation.",
        ),
        InspectorSection(
            section_id="SCANNER_LAB",
            title="Scanner Lab",
            status="AVAILABLE",
            summary="Native scanner lineage only; PK fixture output has zero authority.",
        ),
        InspectorSection(
            section_id="SOURCES_LINEAGE",
            title="Sources and Lineage",
            status="AVAILABLE",
            summary="Official EOD source, raw hash and adjustment version retained.",
        ),
        InspectorSection(
            section_id="HISTORY",
            title="History",
            status="AVAILABLE",
            summary="Append-only events reconstruct the current REJECT state.",
            items=history.what_changed,
        ),
        InspectorSection(
            section_id="FAILURES",
            title="Failures",
            status="AVAILABLE",
            summary="Source correction and structural invalidation remain visible.",
            items=("WAIT_SOURCE_CORRECTION", "STRUCTURE_INVALIDATED"),
        ),
        InspectorSection(
            section_id="VALIDATION",
            title="Validation",
            status="HIDDEN",
            summary="Fixture validation cannot unlock trader-facing performance.",
            items=(validation.status.value,),
        ),
    )
    return CandidateInspector(
        candidate_id=history.candidate_id,
        state=history.current_state,
        evidence_strength_label="Evidence strength - not win probability",
        selected_claim_ids=("CLM-STRUCTURE-1",),
        suppressed_claim_ids=("CLM-STRUCTURE-CORRELATED",),
        opposing_claim_ids=("CLM-SOURCE-CORRECTION",),
        source_health=("SRC-NSE-EOD:FRESH", "SRC-PK-FIXTURE:SHADOW_ZERO_AUTHORITY"),
        sections=sections,
        validation_status=validation.status,
        performance_ui_visible=False,
    )


def build_q5_r6_fixture_batch() -> Q5R6FixtureBatch:
    history = _history()
    cost_profile = _cost_profile()
    outcomes = _outcomes(cost_profile)
    profile = _validation_profile()
    walk_forward_artifact, holdout_artifact = _validation_artifacts(
        outcomes, R6_EVALUATED_AT
    )
    approved_fixture = evaluate_pit_validation(
        run_id="PIT-R6-APPROVED-FIXTURE",
        profile=profile,
        outcomes=outcomes,
        cost_profile=cost_profile,
        evaluated_at=R6_EVALUATED_AT,
        walk_forward_artifact=walk_forward_artifact,
        holdout_artifact=holdout_artifact,
        fixture_only=True,
    )
    rejected_missing_cost = evaluate_pit_validation(
        run_id="PIT-R6-REJECTED-MISSING-COST",
        profile=profile,
        outcomes=outcomes,
        cost_profile=None,
        evaluated_at=R6_EVALUATED_AT,
        walk_forward_artifact=walk_forward_artifact,
        holdout_artifact=holdout_artifact,
        fixture_only=True,
    )
    healthy_at = R6_EVALUATED_AT
    healthy = assess_validation_drift(
        validation=approved_fixture,
        metric_artifact=_drift_artifact(
            approved_fixture,
            assessed_at=healthy_at,
            feature_psi=0.08,
            calibration_error_delta=0.01,
            residual_shift=0.04,
        ),
        assessed_at=healthy_at,
    )
    demoted_at = R6_EVALUATED_AT + timedelta(minutes=1)
    demoted = assess_validation_drift(
        validation=approved_fixture,
        metric_artifact=_drift_artifact(
            approved_fixture,
            assessed_at=demoted_at,
            feature_psi=0.30,
            calibration_error_delta=0.15,
            residual_shift=0.20,
        ),
        assessed_at=demoted_at,
    )
    radar = (
        Q5R6RadarRow(
            candidate_id=history.candidate_id,
            symbol="TF_R6_HISTORY",
            profile="EOD_SWING_RESEARCH",
            state=history.current_state,
            evidence_strength=0.0,
            why_appeared="Prior closed-bar structure entered the research queue.",
            what_changed="A later correction removed participation, then structure invalidated.",
            top_support="No current support survives the hard invalidation.",
            strongest_contradiction="Official correction conflicts with prior confirmation.",
            missing_proof="Not recoverable while structural invalidation remains active.",
            freshness="MIXED - correction lineage retained",
            confirmation_condition="A new candidate instance requires new closed-bar evidence.",
            invalidation_condition="Already met: structure invalidated.",
            completeness=1.0,
            no_action_reason="REJECT is a research state; no action is produced.",
        ),
    )
    inspector = _inspector(history=history, validation=approved_fixture)
    return Q5R6FixtureBatch(
        radar=radar,
        histories=(history,),
        cost_profile=cost_profile,
        outcomes=outcomes,
        validation_results=(approved_fixture, rejected_missing_cost),
        drift_assessments=(healthy, demoted),
        inspector=inspector,
    )
