from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .models import DataTrust


class CausalLayer(str, Enum):
    CAUSE = "CAUSE"
    SPONSOR = "SPONSOR"
    STRUCTURE = "STRUCTURE"
    FLOW = "FLOW"


class GateOutcome(str, Enum):
    PASS = "PASS"
    SOFT_FAIL = "SOFT_FAIL"
    HARD_FAIL = "HARD_FAIL"
    WAIT = "WAIT"
    STALE = "STALE"


class CauseType(str, Enum):
    INFORMATION_ASYMMETRY = "INFORMATION_ASYMMETRY"
    FORCED_MANDATORY_FLOW = "FORCED_MANDATORY_FLOW"
    FUNDAMENTAL_RERATING = "FUNDAMENTAL_RERATING"
    REFLEXIVITY_FEEDBACK = "REFLEXIVITY_FEEDBACK"


class SponsorActor(str, Enum):
    FII = "FII"
    DII = "DII"
    PROMOTER_INSIDER = "PROMOTER_INSIDER"
    NAMED_INVESTOR = "NAMED_INVESTOR"
    MARKET_MAKER_OPTION_WRITER = "MARKET_MAKER_OPTION_WRITER"
    RETAIL_OPERATOR = "RETAIL_OPERATOR"


FinalState = Literal[
    "PRIORITY_RADAR",
    "READY",
    "WAIT",
    "WAIT_FOMO",
    "WAIT_DATA_WEAK",
    "WAIT_MTF_CONFLICT",
    "WAIT_EMOTIONAL_RISK",
    "REJECT",
    "SHORT_WATCH",
    "NO_TRADE",
    "LOCKED_NO_TRADE",
    "STOP_TRADING_NOW",
]
Stage1Label = Literal["ELIGIBLE", "INELIGIBLE", "WAIT", "STALE", "HARD_FAIL"]
Stage2Label = Literal["BLOCKED", "NOT_RUN", "WAIT_TRIGGER", "WEAK", "CONFIRMED"]


LAYER_MAXIMUMS = {
    CausalLayer.CAUSE: 6.0,
    CausalLayer.SPONSOR: 10.0,
    CausalLayer.STRUCTURE: 6.0,
    CausalLayer.FLOW: 6.0,
}

LAYER_MINIMUMS = {
    CausalLayer.CAUSE: 2.0,
    CausalLayer.SPONSOR: 4.0,
    CausalLayer.STRUCTURE: 2.0,
    CausalLayer.FLOW: 2.0,
}

DEFAULT_DECAY_LAMBDAS = {
    "DELIVERY_PERCENT": 0.15,
    "PROMOTER_BUY": 0.04,
    "BULK_DEAL": 0.07,
    "MF_HOLDING": 0.02,
}

UNOFFICIAL_TRUST = {
    DataTrust.OPEN_SOURCE_UNOFFICIAL,
    DataTrust.UNOFFICIAL_WRAPPER,
    DataTrust.UNOFFICIAL_TEMP,
    DataTrust.SYNTHETIC_TEST,
}


class CausalEvidenceInput(BaseModel):
    evidence_id: str = Field(alias="evidenceId", min_length=1, max_length=120)
    layer: CausalLayer
    signal_type: str = Field(alias="signalType", min_length=1, max_length=80)
    contribution: float = Field(ge=-10, le=10)
    source: str = Field(min_length=1, max_length=200)
    source_key: str | None = Field(default=None, alias="sourceKey", max_length=100)
    source_row_id: int | None = Field(default=None, alias="sourceRowId", ge=1)
    source_date: datetime = Field(alias="sourceDate")
    observed_at: datetime = Field(alias="observedAt")
    trust_level: DataTrust = Field(alias="trustLevel")
    explanation: str = Field(min_length=1, max_length=1000)
    raw_input_keys: list[str] = Field(default_factory=list, alias="rawInputKeys")
    decay_lambda: float | None = Field(default=None, ge=0, le=5, alias="decayLambda")
    initial_weight: float | None = Field(
        default=None, gt=0, le=1, alias="initialWeight"
    )
    stale_after_days: float | None = Field(default=None, gt=0, alias="staleAfterDays")
    cause_type: CauseType | None = Field(default=None, alias="causeType")
    sponsor_actor: SponsorActor | None = Field(default=None, alias="sponsorActor")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def require_domain_classification(self) -> "CausalEvidenceInput":
        if self.source_date.utcoffset() is None or self.observed_at.utcoffset() is None:
            raise ValueError("sourceDate and observedAt must be timezone-aware")
        if (
            self.contribution > 0
            and self.layer == CausalLayer.CAUSE
            and self.cause_type is None
        ):
            raise ValueError("positive CAUSE evidence requires causeType")
        if (
            self.contribution > 0
            and self.layer == CausalLayer.SPONSOR
            and self.sponsor_actor is None
        ):
            raise ValueError("positive SPONSOR evidence requires sponsorActor")
        return self


class DecisionGateInput(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    outcome: GateOutcome
    reason: str = Field(min_length=1, max_length=1000)
    override_state: FinalState | None = Field(default=None, alias="overrideState")

    model_config = {"populate_by_name": True}


class ExecutionStageInput(BaseModel):
    score: float = Field(ge=0, le=16)
    trigger_active: bool = Field(alias="triggerActive")
    gates: list[DecisionGateInput] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class CausalCandidateInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9&._ -]+$")
    direction: Literal["LONG", "SHORT", "WATCH"] = "WATCH"
    as_of: datetime = Field(alias="asOf")
    evidence: list[CausalEvidenceInput]
    gates: list[DecisionGateInput] = Field(default_factory=list)
    execution: ExecutionStageInput | None = None
    evaluation_mode: Literal["PRODUCTION", "DEMO"] = Field(
        default="PRODUCTION", alias="evaluationMode"
    )

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_point_in_time_contract(self) -> "CausalCandidateInput":
        if self.as_of.utcoffset() is None:
            raise ValueError("asOf must be timezone-aware")
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidenceId values must be unique within a candidate")
        return self


class CausalBatchRequest(BaseModel):
    candidates: list[CausalCandidateInput] = Field(min_length=1, max_length=5000)
    minimum_total: float = Field(default=18, ge=0, le=28, alias="minimumTotal")
    minimum_layers: int = Field(default=3, ge=1, le=4, alias="minimumLayers")
    minimum_percentile: float = Field(
        default=90, ge=0, le=100, alias="minimumPercentile"
    )

    model_config = {"populate_by_name": True}


class EvaluatedEvidence(BaseModel):
    evidence_id: str = Field(alias="evidenceId")
    layer: CausalLayer
    signal_type: str = Field(alias="signalType")
    source: str
    source_key: str | None = Field(default=None, alias="sourceKey")
    source_row_id: int | None = Field(default=None, alias="sourceRowId")
    source_date: datetime = Field(alias="sourceDate")
    observed_at: datetime = Field(alias="observedAt")
    age_days: float = Field(alias="ageDays")
    freshness: Literal["FRESH", "STALE", "FUTURE"]
    trust_level: DataTrust = Field(alias="trustLevel")
    raw_contribution: float = Field(alias="rawContribution")
    decay_weight: float = Field(alias="decayWeight")
    adjusted_contribution: float = Field(alias="adjustedContribution")
    raw_input_keys: list[str] = Field(alias="rawInputKeys")
    cause_type: CauseType | None = Field(default=None, alias="causeType")
    sponsor_actor: SponsorActor | None = Field(default=None, alias="sponsorActor")
    explanation: str

    model_config = {"populate_by_name": True}


class IndependencePenalty(BaseModel):
    left_layer: CausalLayer = Field(alias="leftLayer")
    right_layer: CausalLayer = Field(alias="rightLayer")
    raw_input_key: str = Field(alias="rawInputKey")
    amount: float
    reason: str

    model_config = {"populate_by_name": True}


class LayerScore(BaseModel):
    layer: CausalLayer
    raw_score: float = Field(alias="rawScore")
    penalty: float
    final_score: float = Field(alias="finalScore")
    maximum: float
    minimum: float
    passed: bool

    model_config = {"populate_by_name": True}


class CausalEvaluationResult(BaseModel):
    symbol: str
    direction: str
    stage1_label: Stage1Label = Field(alias="stage1Label")
    stage1_score: float = Field(alias="stage1Score")
    stage1_maximum: float = Field(default=28, alias="stage1Maximum")
    stage2_label: Stage2Label = Field(alias="stage2Label")
    stage2_score: float | None = Field(default=None, alias="stage2Score")
    percentile_rank: float = Field(alias="percentileRank")
    layer_scores: list[LayerScore] = Field(alias="layerScores")
    passing_layer_count: int = Field(alias="passingLayerCount")
    evidence: list[EvaluatedEvidence]
    independence_penalties: list[IndependencePenalty] = Field(
        alias="independencePenalties"
    )
    gates: list[DecisionGateInput]
    final_state: FinalState = Field(alias="finalState")
    reasons: list[str]
    active_cause_types: list[CauseType] = Field(alias="activeCauseTypes")
    sponsor_actors: list[SponsorActor] = Field(alias="sponsorActors")
    executable: Literal[False] = False

    model_config = {"populate_by_name": True}


class _CandidateDraft(BaseModel):
    candidate: CausalCandidateInput
    stage1_score: float
    layer_scores: list[LayerScore]
    evidence: list[EvaluatedEvidence]
    penalties: list[IndependencePenalty]
    point_in_time_failure: bool
    unofficial_qualifying_evidence: bool


def _age_days(source_date: datetime, as_of: datetime) -> float:
    return (as_of - source_date).total_seconds() / 86400


def _evaluate_evidence(item: CausalEvidenceInput, as_of: datetime) -> EvaluatedEvidence:
    age_days = _age_days(item.source_date, as_of)
    freshness: Literal["FRESH", "STALE", "FUTURE"]
    if age_days < 0 or item.observed_at > as_of:
        freshness = "FUTURE"
        weight = 0.0
    else:
        freshness = (
            "STALE"
            if item.stale_after_days is not None and age_days > item.stale_after_days
            else "FRESH"
        )
        decay_lambda = item.decay_lambda
        if decay_lambda is None:
            decay_lambda = DEFAULT_DECAY_LAMBDAS.get(item.signal_type.upper(), 0.0)
        initial_weight = item.initial_weight
        if initial_weight is None:
            initial_weight = 0.4 if item.signal_type.upper() == "MF_HOLDING" else 1.0
        weight = initial_weight * math.exp(-decay_lambda * max(age_days, 0))
        if freshness == "STALE":
            weight = min(weight, 0.4)
    adjusted = item.contribution * weight
    return EvaluatedEvidence(
        evidenceId=item.evidence_id,
        layer=item.layer,
        signalType=item.signal_type,
        source=item.source,
        sourceKey=item.source_key,
        sourceRowId=item.source_row_id,
        sourceDate=item.source_date,
        observedAt=item.observed_at,
        ageDays=round(age_days, 6),
        freshness=freshness,
        trustLevel=item.trust_level,
        rawContribution=item.contribution,
        decayWeight=round(weight, 6),
        adjustedContribution=round(adjusted, 6),
        rawInputKeys=item.raw_input_keys,
        causeType=item.cause_type,
        sponsorActor=item.sponsor_actor,
        explanation=item.explanation,
    )


def _independence_penalties(
    candidate: CausalCandidateInput,
    evaluated: dict[str, EvaluatedEvidence],
) -> tuple[list[IndependencePenalty], dict[CausalLayer, float]]:
    strongest: dict[tuple[CausalLayer, str], float] = {}
    for item in candidate.evidence:
        adjusted = evaluated[item.evidence_id].adjusted_contribution
        if adjusted <= 0:
            continue
        for raw_key in {
            key.strip().casefold() for key in item.raw_input_keys if key.strip()
        }:
            strongest[(item.layer, raw_key)] = max(
                strongest.get((item.layer, raw_key), 0.0), adjusted
            )

    penalties: list[IndependencePenalty] = []
    by_layer: dict[CausalLayer, float] = defaultdict(float)
    layers = list(CausalLayer)
    for left_index, left in enumerate(layers):
        for right in layers[left_index + 1 :]:
            shared = {key for layer, key in strongest if layer == left} & {
                key for layer, key in strongest if layer == right
            }
            for raw_key in sorted(shared):
                amount = 0.3 * min(
                    strongest[(left, raw_key)], strongest[(right, raw_key)]
                )
                by_layer[left] += amount / 2
                by_layer[right] += amount / 2
                penalties.append(
                    IndependencePenalty(
                        leftLayer=left,
                        rightLayer=right,
                        rawInputKey=raw_key,
                        amount=round(amount, 6),
                        reason="Shared raw input is not independent confirmation.",
                    )
                )
    return penalties, by_layer


def _draft(candidate: CausalCandidateInput) -> _CandidateDraft:
    evaluated_list = [
        _evaluate_evidence(item, candidate.as_of) for item in candidate.evidence
    ]
    evaluated = {item.evidence_id: item for item in evaluated_list}
    raw_scores: dict[CausalLayer, float] = defaultdict(float)
    for source_item in candidate.evidence:
        raw_scores[source_item.layer] += evaluated[
            source_item.evidence_id
        ].adjusted_contribution

    penalties, layer_penalties = _independence_penalties(candidate, evaluated)
    layer_scores: list[LayerScore] = []
    for layer in CausalLayer:
        raw_score = min(max(raw_scores[layer], 0.0), LAYER_MAXIMUMS[layer])
        penalty = min(layer_penalties[layer], raw_score)
        final_score = max(raw_score - penalty, 0.0)
        layer_scores.append(
            LayerScore(
                layer=layer,
                rawScore=round(raw_score, 6),
                penalty=round(penalty, 6),
                finalScore=round(final_score, 6),
                maximum=LAYER_MAXIMUMS[layer],
                minimum=LAYER_MINIMUMS[layer],
                passed=final_score >= LAYER_MINIMUMS[layer],
            )
        )

    return _CandidateDraft(
        candidate=candidate,
        stage1_score=round(sum(item.final_score for item in layer_scores), 6),
        layer_scores=layer_scores,
        evidence=evaluated_list,
        penalties=penalties,
        point_in_time_failure=any(
            item.freshness == "FUTURE" for item in evaluated_list
        ),
        unofficial_qualifying_evidence=any(
            item.adjusted_contribution > 0 and item.trust_level in UNOFFICIAL_TRUST
            for item in evaluated_list
        ),
    )


def _percentiles(drafts: list[_CandidateDraft]) -> dict[str, float]:
    scores = [item.stage1_score for item in drafts]
    return {
        item.candidate.symbol: round(
            100 * sum(score <= item.stage1_score for score in scores) / len(scores), 2
        )
        for item in drafts
    }


def _gate_override(gates: list[DecisionGateInput]) -> FinalState | None:
    priority: list[FinalState] = [
        "STOP_TRADING_NOW",
        "LOCKED_NO_TRADE",
        "NO_TRADE",
        "WAIT_EMOTIONAL_RISK",
        "WAIT_FOMO",
        "WAIT_MTF_CONFLICT",
    ]
    states = {gate.override_state for gate in gates if gate.override_state is not None}
    return next((state for state in priority if state in states), None)


def _finalize(
    draft: _CandidateDraft,
    percentile: float,
    request: CausalBatchRequest,
) -> CausalEvaluationResult:
    candidate = draft.candidate
    all_gates = candidate.gates + (
        candidate.execution.gates if candidate.execution else []
    )
    override = _gate_override(all_gates)
    hard_fail = draft.point_in_time_failure or any(
        gate.outcome == GateOutcome.HARD_FAIL for gate in all_gates
    )
    stale = any(gate.outcome == GateOutcome.STALE for gate in all_gates)
    wait_gate = any(gate.outcome == GateOutcome.WAIT for gate in all_gates)
    passing_layers = sum(item.passed for item in draft.layer_scores)
    numeric_eligible = (
        draft.stage1_score >= request.minimum_total
        and passing_layers >= request.minimum_layers
        and all(item.passed for item in draft.layer_scores)
        and percentile >= request.minimum_percentile
    )
    reasons: list[str] = []
    if draft.point_in_time_failure:
        reasons.append(
            "Point-in-time violation: evidence is dated after the evaluation cutoff."
        )
    reasons.extend(
        gate.reason for gate in all_gates if gate.outcome != GateOutcome.PASS
    )

    if hard_fail:
        stage1_label: Stage1Label = "HARD_FAIL"
    elif stale:
        stage1_label = "STALE"
    elif wait_gate:
        stage1_label = "WAIT"
    elif numeric_eligible:
        stage1_label = "ELIGIBLE"
    else:
        stage1_label = "INELIGIBLE"

    execution = candidate.execution
    if stage1_label != "ELIGIBLE":
        stage2_label: Stage2Label = "BLOCKED"
        stage2_score = execution.score if execution else None
    elif execution is None:
        stage2_label = "NOT_RUN"
        stage2_score = None
    elif not execution.trigger_active:
        stage2_label = "WAIT_TRIGGER"
        stage2_score = execution.score
    elif execution.score < 12:
        stage2_label = "WEAK"
        stage2_score = execution.score
    else:
        stage2_label = "CONFIRMED"
        stage2_score = execution.score

    if override is not None:
        final_state: FinalState = override
    elif hard_fail:
        final_state = "REJECT"
    elif (
        stale
        or draft.unofficial_qualifying_evidence
        and candidate.evaluation_mode == "PRODUCTION"
    ):
        final_state = "WAIT_DATA_WEAK"
    elif wait_gate:
        final_state = "WAIT"
    elif stage1_label != "ELIGIBLE":
        final_state = "REJECT"
    elif stage2_label in {"NOT_RUN", "WAIT_TRIGGER", "WEAK"}:
        final_state = "WAIT"
    else:
        final_state = "READY"

    if not reasons:
        reasons.append(
            f"Stage 1 {stage1_label}: {draft.stage1_score:.2f}/28, "
            f"{passing_layers}/4 layers, percentile {percentile:.2f}."
        )
    if stage2_label == "BLOCKED":
        reasons.append("Stage 2 is blocked because Stage 1 is not eligible.")
    elif stage2_label == "WAIT_TRIGGER":
        reasons.append(
            "Stage 1 is eligible, but the live execution trigger is not active."
        )
    elif stage2_label == "WEAK":
        reasons.append(
            "Stage 2 execution score is below the 12/16 confirmation threshold."
        )
    if (
        draft.unofficial_qualifying_evidence
        and candidate.evaluation_mode == "PRODUCTION"
    ):
        reasons.append(
            "Unofficial evidence may support research but cannot unlock production READY."
        )

    cause_types = sorted(
        {
            item.cause_type
            for item in candidate.evidence
            if item.contribution > 0 and item.cause_type is not None
        },
        key=lambda item: item.value,
    )
    sponsor_actors = sorted(
        {
            item.sponsor_actor
            for item in candidate.evidence
            if item.contribution > 0 and item.sponsor_actor is not None
        },
        key=lambda item: item.value,
    )
    return CausalEvaluationResult(
        symbol=candidate.symbol,
        direction=candidate.direction,
        stage1Label=stage1_label,
        stage1Score=draft.stage1_score,
        stage2Label=stage2_label,
        stage2Score=stage2_score,
        percentileRank=percentile,
        layerScores=draft.layer_scores,
        passingLayerCount=passing_layers,
        evidence=draft.evidence,
        independencePenalties=draft.penalties,
        gates=all_gates,
        finalState=final_state,
        reasons=reasons,
        activeCauseTypes=cause_types,
        sponsorActors=sponsor_actors,
        executable=False,
    )


def evaluate_causal_batch(request: CausalBatchRequest) -> list[CausalEvaluationResult]:
    symbols = [candidate.symbol.casefold() for candidate in request.candidates]
    if len(symbols) != len(set(symbols)):
        raise ValueError(
            "candidate symbols must be unique within a percentile-ranking batch"
        )
    drafts = [_draft(candidate) for candidate in request.candidates]
    percentiles = _percentiles(drafts)
    return [
        _finalize(item, percentiles[item.candidate.symbol], request) for item in drafts
    ]
