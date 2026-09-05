"""R18 model governance: offline evaluation, human review, drift, and rollback."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .r16_service import (
    runs_payload as r16_runs_payload,
    status_payload as r16_status_payload,
)

CONTRACT = "trendforge.r18-model-governance.v1"
POLICY_VERSION = "r18-governance-1"


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.title() for part in tail)


def _hash(*parts: object) -> str:
    body = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode()).hexdigest()


class ModelState(StrEnum):
    MODEL_NOT_APPROVED = "MODEL_NOT_APPROVED"
    CHALLENGER = "CHALLENGER"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CHAMPION = "CHAMPION"
    REJECTED = "REJECTED"
    SHADOW = "SHADOW"
    STALE_MODEL = "STALE_MODEL"
    DISABLED = "DISABLED"
    ROLLED_BACK = "ROLLED_BACK"


class ModelManifestV1(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    model_id: str
    model_version: str
    purpose: str
    market: Literal["NSE_EQUITY", "NSE_DERIVATIVE", "MCX"]
    horizon: Literal["INTRADAY", "SWING", "EOD"]
    dataset_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_set_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    formula_set_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    state: ModelState = ModelState.CHALLENGER

    @model_validator(mode="after")
    def immutable_identity(self) -> "ModelManifestV1":
        expected = _hash(
            self.model_id, self.model_version, self.purpose, self.market,
            self.horizon, self.dataset_hash, self.feature_set_hash,
            self.formula_set_hash,
        )
        if self.model_hash != expected:
            raise ValueError("MODEL_HASH_MISMATCH")
        if self.created_at.tzinfo is None:
            raise ValueError("MODEL_CREATED_AT_REQUIRES_TIMEZONE")
        return self


class FoldPredictionV1(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)
    fold_index: int = Field(ge=0)
    train_end: date
    test_start: date
    test_end: date
    embargo_sessions: int = Field(ge=1)
    probabilities: tuple[float, ...]
    outcomes: tuple[int, ...]
    net_r: tuple[float, ...]

    @model_validator(mode="after")
    def validate_fold(self) -> "FoldPredictionV1":
        if not self.train_end < self.test_start <= self.test_end:
            raise ValueError("WALK_FORWARD_ORDER_INVALID")
        if not self.probabilities or not (
            len(self.probabilities) == len(self.outcomes) == len(self.net_r)
        ):
            raise ValueError("FOLD_VECTOR_LENGTH_MISMATCH")
        if any(not math.isfinite(p) or p < 0 or p > 1 for p in self.probabilities):
            raise ValueError("PROBABILITY_INVALID")
        if any(y not in (0, 1) for y in self.outcomes):
            raise ValueError("OUTCOME_INVALID")
        if any(not math.isfinite(v) for v in self.net_r):
            raise ValueError("NET_R_INVALID")
        return self


class ChallengerEvaluationInputV1(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)
    manifest: ModelManifestV1
    r16_contract: Literal["trendforge.r16-pit.v1"]
    r16_validation_status: Literal["PIT_APPROVED", "PIT_NOT_APPROVED"]
    dataset_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cost_model_version: str
    folds: tuple[FoldPredictionV1, ...]
    holdout: FoldPredictionV1

    @model_validator(mode="after")
    def validate_lineage(self) -> "ChallengerEvaluationInputV1":
        if self.dataset_hash != self.manifest.dataset_hash:
            raise ValueError("R16_DATASET_HASH_MISMATCH")
        ordered = sorted(self.folds, key=lambda row: row.test_start)
        if len(ordered) < 2:
            raise ValueError("WALK_FORWARD_FOLDS_INSUFFICIENT")
        if any(left.test_end >= right.test_start for left, right in zip(ordered, ordered[1:])):
            raise ValueError("WALK_FORWARD_TEST_OVERLAP")
        if self.holdout.test_start <= ordered[-1].test_end:
            raise ValueError("HOLDOUT_NOT_UNTOUCHED")
        if not self.cost_model_version.strip():
            raise ValueError("COST_MODEL_REQUIRED")
        return self


class ChallengerEvaluationV1(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)
    contract: str = CONTRACT
    evaluation_id: str
    model_id: str
    model_hash: str
    dataset_hash: str
    evaluated_at: datetime
    fold_count: int
    observation_count: int
    brier_score: float
    expected_calibration_error: float
    average_net_r_after_costs: float
    holdout_brier_score: float
    holdout_average_net_r_after_costs: float
    review_eligible: bool
    blockers: tuple[str, ...]
    automatic_promotion: Literal[False] = False


def _metrics(probabilities: tuple[float, ...], outcomes: tuple[int, ...], net_r: tuple[float, ...]) -> tuple[float, float, float]:
    brier = sum((p - y) ** 2 for p, y in zip(probabilities, outcomes)) / len(outcomes)
    bins: dict[int, list[tuple[float, int]]] = {}
    for p, y in zip(probabilities, outcomes):
        bins.setdefault(min(9, int(p * 10)), []).append((p, y))
    ece = sum(
        len(rows) / len(outcomes)
        * abs(sum(p for p, _ in rows) / len(rows) - sum(y for _, y in rows) / len(rows))
        for rows in bins.values()
    )
    return brier, ece, sum(net_r) / len(net_r)


def evaluate_challenger(payload: ChallengerEvaluationInputV1, *, now: datetime | None = None) -> ChallengerEvaluationV1:
    folds = sorted(payload.folds, key=lambda row: row.fold_index)
    p = tuple(value for fold in folds for value in fold.probabilities)
    y = tuple(value for fold in folds for value in fold.outcomes)
    r = tuple(value for fold in folds for value in fold.net_r)
    brier, ece, average_r = _metrics(p, y, r)
    holdout_brier, _, holdout_r = _metrics(
        payload.holdout.probabilities, payload.holdout.outcomes, payload.holdout.net_r
    )
    blockers: list[str] = []
    if payload.r16_validation_status != "PIT_APPROVED":
        blockers.append("PIT_NOT_APPROVED")
    if len(y) < 30:
        blockers.append("EFFECTIVE_SAMPLE_INSUFFICIENT")
    if average_r <= 0 or holdout_r <= 0:
        blockers.append("NET_EXPECTANCY_NOT_POSITIVE")
    if ece > 0.05:
        blockers.append("CALIBRATION_ERROR_EXCEEDS_POLICY")
    evaluated_at = now or datetime.now(UTC)
    evaluation_id = _hash(
        payload.manifest.model_hash, payload.dataset_hash, payload.cost_model_version,
        tuple(fold.model_dump(mode="json") for fold in folds),
        payload.holdout.model_dump(mode="json"), POLICY_VERSION,
    )
    return ChallengerEvaluationV1(
        evaluation_id=evaluation_id, model_id=payload.manifest.model_id,
        model_hash=payload.manifest.model_hash, dataset_hash=payload.dataset_hash,
        evaluated_at=evaluated_at, fold_count=len(folds), observation_count=len(y),
        brier_score=brier, expected_calibration_error=ece,
        average_net_r_after_costs=average_r,
        holdout_brier_score=holdout_brier,
        holdout_average_net_r_after_costs=holdout_r,
        review_eligible=not blockers, blockers=tuple(blockers),
    )


class PromotionReviewV1(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)
    review_id: str
    model_id: str
    model_hash: str
    evaluation_id: str
    evidence_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    signature_scheme: Literal["SHA256_CHAIN_V1"] = "SHA256_CHAIN_V1"
    decision: Literal["APPROVE", "REJECT"]
    reviewer: str
    reason: str
    r16_validation_status: Literal["PIT_APPROVED", "PIT_NOT_APPROVED"]
    effective_state: ModelState
    previous_record_hash: str | None = None
    record_hash: str
    reviewed_at: datetime


def build_promotion_review(*, manifest: ModelManifestV1, evaluation: ChallengerEvaluationV1, decision: Literal["APPROVE", "REJECT"], reviewer: str, reason: str, r16_validation_status: str, previous_record_hash: str | None = None, now: datetime | None = None) -> PromotionReviewV1:
    if not reviewer.strip() or not reason.strip():
        raise ValueError("HUMAN_REVIEWER_AND_REASON_REQUIRED")
    if decision == "APPROVE" and r16_validation_status != "PIT_APPROVED":
        raise ValueError("PIT_NOT_APPROVED")
    if decision == "APPROVE" and not evaluation.review_eligible:
        raise ValueError("CHALLENGER_NOT_REVIEW_ELIGIBLE")
    effective = ModelState.CHAMPION if decision == "APPROVE" else ModelState.REJECTED
    reviewed_at = now or datetime.now(UTC)
    review_id = _hash(manifest.model_hash, evaluation.evaluation_id, decision, reviewer, reviewed_at.isoformat())
    evidence_hash = _hash(manifest.model_hash, evaluation.evaluation_id, evaluation.dataset_hash)
    record_hash = _hash(review_id, evidence_hash, decision, reviewer, reason, previous_record_hash, "SHA256_CHAIN_V1")
    return PromotionReviewV1(
        review_id=review_id, model_id=manifest.model_id, model_hash=manifest.model_hash,
        evaluation_id=evaluation.evaluation_id, evidence_hash=evidence_hash,
        decision=decision, reviewer=reviewer,
        reason=reason, r16_validation_status=r16_validation_status,
        effective_state=effective, previous_record_hash=previous_record_hash,
        record_hash=record_hash, reviewed_at=reviewed_at,
    )


class DriftAssessmentV1(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)
    drift_id: str
    model_id: str
    model_hash: str
    assessed_at: datetime
    feature_psi: float = Field(ge=0)
    prediction_psi: float = Field(ge=0)
    calibration_delta: float = Field(ge=0)
    breached: tuple[str, ...]
    resulting_state: ModelState
    rollback_model_hash: str | None = None
    rollback_state: Literal["CHAMPION"] | None = None
    automatic_promotion: Literal[False] = False


def assess_drift(*, manifest: ModelManifestV1, feature_psi: float, prediction_psi: float, calibration_delta: float, previous_champion_hash: str | None = None, now: datetime | None = None) -> DriftAssessmentV1:
    values = (feature_psi, prediction_psi, calibration_delta)
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("DRIFT_VALUE_INVALID")
    breached: list[str] = []
    if feature_psi >= 0.20:
        breached.append("FEATURE_DRIFT")
    if prediction_psi >= 0.20:
        breached.append("PREDICTION_DRIFT")
    if calibration_delta >= 0.05:
        breached.append("CALIBRATION_DRIFT")
    state = ModelState.STALE_MODEL if breached else manifest.state
    rollback = previous_champion_hash if breached and manifest.state == ModelState.CHAMPION else None
    assessed_at = now or datetime.now(UTC)
    return DriftAssessmentV1(
        drift_id=_hash(manifest.model_hash, assessed_at.isoformat(), values, POLICY_VERSION),
        model_id=manifest.model_id, model_hash=manifest.model_hash,
        assessed_at=assessed_at, feature_psi=feature_psi,
        prediction_psi=prediction_psi, calibration_delta=calibration_delta,
        breached=tuple(breached), resulting_state=state,
        rollback_model_hash=rollback,
        rollback_state="CHAMPION" if rollback else None,
    )


def governance_status() -> dict[str, object]:
    r16 = r16_status_payload()
    approved = r16.get("validationStatus") == "PIT_APPROVED"
    latest_runs = r16_runs_payload(limit=1).get("runs") or []
    dataset_age_days: int | None = None
    if latest_runs:
        trading_date = latest_runs[0].get("tradingDate")
        if trading_date:
            dataset_age_days = max(
                0, (datetime.now(UTC).date() - date.fromisoformat(trading_date)).days
            )
    return {
        "contract": CONTRACT,
        "modelState": "MODEL_NOT_APPROVED",
        "r16ValidationStatus": r16.get("validationStatus", "PIT_NOT_APPROVED"),
        "datasetStatus": r16.get("datasetStatus", "BUILDING"),
        "datasetAgeDays": dataset_age_days,
        "blockers": tuple(r16.get("blockers") or ()) + (() if approved else ("PIT_NOT_APPROVED",)),
        "probabilityVisible": False,
        "winRateVisible": False,
        "performanceVisible": False,
        "automaticPromotionAllowed": False,
        "executionAuthorized": False,
        "copy": "Research simulation only - no broker order.",
    }



