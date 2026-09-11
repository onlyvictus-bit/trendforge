"""Strict R-HIST-03D semantic identity contracts.

All builders validate normalized material before hashing. Semantic identity never
stringifies unsupported Python objects, and it normalizes SHA-256 text,
timezones, and explicitly set-like collections before canonical serialization.
This module grants no trading, promotion, strategy, or execution authority.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

R_HIST_03D_EXECUTION_AUTHORIZED = False
R_HIST_03D_AUTOMATIC_PROMOTION_ALLOWED = False
DATASET_SCHEMA_VERSION = "trendforge.rhist03d-frozen-dataset.v1"
MODEL_SCHEMA_VERSION = "trendforge.rhist03d-model-version.v1"
PROFILE_SCHEMA_VERSION = "trendforge.rhist03d-strategy-profile.v1"
AUDIT_SCHEMA_VERSION = "trendforge.rhist03d-audit.v1"
MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    frozen=True,
    extra="forbid",
)


def _normalize_sha256(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("semantic hash must be a SHA-256 hex digest")
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise ValueError("semantic hash must be a SHA-256 hex digest")
    return normalized


Sha256Hex = Annotated[str, BeforeValidator(_normalize_sha256)]


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("semantic datetime must be timezone-aware")
    return value.astimezone(UTC)


UtcDateTime = Annotated[datetime, AfterValidator(_utc_datetime)]


def _semantic_value(value: Any) -> Any:
    """Normalize the explicitly allowed semantic JSON value domain."""
    if isinstance(value, BaseModel):
        return _semantic_value(value.model_dump(mode="python", by_alias=True))
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NON_FINITE_SEMANTIC_FLOAT")
        return value
    if isinstance(value, datetime):
        return _utc_datetime(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_semantic_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("SEMANTIC_JSON_KEYS_MUST_BE_STRINGS")
        return {key: _semantic_value(item) for key, item in value.items()}
    raise ValueError(f"UNSUPPORTED_SEMANTIC_VALUE:{type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        _semantic_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _aware(value: datetime, code: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(code)
    return value.astimezone(UTC)


def _identity_check_skipped(info: ValidationInfo, identity: str) -> bool:
    return bool(info.context and info.context.get("rhist03d_skip_identity") == identity)


def _identity_material(model: BaseModel, *excluded_fields: str) -> dict[str, Any]:
    return model.model_dump(
        mode="python",
        by_alias=True,
        exclude=set(excluded_fields),
    )


def _normalized_set_tuple(value: Any, *, code: str) -> tuple[Any, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(code)
    rows = tuple(value)
    material = [canonical_json(item) for item in rows]
    if len(set(material)) != len(material):
        raise ValueError(code)
    return tuple(item for _, item in sorted(zip(material, rows), key=lambda row: row[0]))


def _require_string_keys(value: Any) -> Any:
    if isinstance(value, dict) and any(not isinstance(key, str) for key in value):
        raise ValueError("SEMANTIC_JSON_KEYS_MUST_BE_STRINGS")
    return value


class FrozenEvidenceRootV1(BaseModel):
    model_config = MODEL_CONFIG
    role: str = Field(min_length=1)
    run_id: str | None = None
    trading_date: str | None = None
    content_hash: Sha256Hex | None = None

    @model_validator(mode="after")
    def validate_root(self) -> "FrozenEvidenceRootV1":
        if not any((self.run_id, self.trading_date, self.content_hash)):
            raise ValueError("EVIDENCE_ROOT_IDENTITY_REQUIRED")
        return self


class FrozenDatasetMemberV1(BaseModel):
    model_config = MODEL_CONFIG
    member_id: str
    member_hash: Sha256Hex
    instrument_id: str
    opportunity_id: str
    profile_id: str
    profile_version: str
    strategy_id: str
    strategy_version: str
    setup_id: str
    setup_episode_id: str
    timeframe: str
    horizon: str
    direction: str
    decision_version_id: str
    decision_version_hash: Sha256Hex
    decision_at: UtcDateTime
    decision_data_cutoff: UtcDateTime
    max_feature_available_at: UtcDateTime
    public_state: str
    outcome_id: str | None = None
    outcome_hash: Sha256Hex | None = None
    outcome_state: str | None = None
    outcome_available_at: UtcDateTime | None = None
    revision_id: str | None = None
    revision_hash: Sha256Hex | None = None
    revision_available_at: UtcDateTime | None = None
    label_available_at: UtcDateTime | None = None
    feature_manifest_id: str
    feature_manifest_hash: Sha256Hex
    formula_set_version: str
    formula_set_hash: Sha256Hex
    input_hashes: tuple[Sha256Hex, ...]
    evidence_roots: tuple[FrozenEvidenceRootV1, ...]
    split: str
    fold: str
    inclusion_reason: str
    exclusion_reason: str | None = None

    @field_validator("input_hashes", mode="before")
    @classmethod
    def normalize_input_hash_order(cls, value: Any) -> tuple[Any, ...]:
        return _normalized_set_tuple(value, code="DUPLICATE_INPUT_HASH")

    @field_validator("evidence_roots", mode="before")
    @classmethod
    def normalize_evidence_root_order(cls, value: Any) -> tuple[Any, ...]:
        if not isinstance(value, (list, tuple)):
            raise ValueError("EVIDENCE_ROOTS_REQUIRED")
        roots = tuple(FrozenEvidenceRootV1.model_validate(item) for item in value)
        return _normalized_set_tuple(roots, code="DUPLICATE_EVIDENCE_ROOT")

    @model_validator(mode="after")
    def validate_member(self, info: ValidationInfo) -> "FrozenDatasetMemberV1":
        if self.decision_data_cutoff < self.decision_at:
            raise ValueError("DECISION_CUTOFF_BEFORE_DECISION")
        if self.max_feature_available_at > self.decision_data_cutoff:
            raise ValueError("FUTURE_FEATURE_EXCEEDS_DECISION_CUTOFF")
        if self.outcome_available_at is not None and self.outcome_available_at < self.decision_at:
            raise ValueError("FUTURE_LABEL_CHRONOLOGY_INVALID")
        if self.label_available_at is not None and self.label_available_at < self.decision_at:
            raise ValueError("FUTURE_LABEL_CHRONOLOGY_INVALID")
        if self.revision_available_at is not None and self.revision_available_at < self.decision_at:
            raise ValueError("REVISION_TIME_BEFORE_DECISION")
        if (
            self.outcome_available_at is not None
            and self.label_available_at is not None
            and self.outcome_available_at != self.label_available_at
        ):
            raise ValueError("FUTURE_LABEL_AVAILABILITY_MISMATCH")
        if bool(self.outcome_id) != bool(self.outcome_hash):
            raise ValueError("OUTCOME_ID_HASH_PAIR_REQUIRED")
        if bool(self.revision_id) != bool(self.revision_hash):
            raise ValueError("REVISION_ID_HASH_PAIR_REQUIRED")
        if not self.evidence_roots:
            raise ValueError("EVIDENCE_ROOTS_REQUIRED")
        if _identity_check_skipped(info, "member"):
            return self
        expected_hash = canonical_hash(_identity_material(self, "member_id", "member_hash"))
        if self.member_hash != expected_hash:
            raise ValueError("DATASET_MEMBER_HASH_MISMATCH")
        if self.member_id != "rhist03d-member:" + expected_hash:
            raise ValueError("DATASET_MEMBER_ID_MISMATCH")
        return self


def build_frozen_dataset_member(**values: Any) -> FrozenDatasetMemberV1:
    source = dict(values)
    for key in ("member_id", "memberId", "member_hash", "memberHash"):
        source.pop(key, None)
    placeholder = "0" * 64
    draft = FrozenDatasetMemberV1.model_validate(
        {**source, "member_id": "rhist03d-member:" + placeholder, "member_hash": placeholder},
        context={"rhist03d_skip_identity": "member"},
    )
    member_hash = canonical_hash(_identity_material(draft, "member_id", "member_hash"))
    return FrozenDatasetMemberV1.model_validate(
        {
            **draft.model_dump(mode="python", by_alias=False),
            "member_hash": member_hash,
            "member_id": "rhist03d-member:" + member_hash,
        }
    )


class FrozenDatasetManifestV1(BaseModel):
    model_config = MODEL_CONFIG
    schema_version: str = DATASET_SCHEMA_VERSION
    dataset_id: str
    dataset_version: str
    dataset_hash: Sha256Hex
    purpose: str
    created_at: UtcDateTime
    decision_cutoff: UtcDateTime
    label_cutoff: UtcDateTime
    build_cutoff: UtcDateTime
    population_policy_id: str
    population_policy_version: str
    label_policy_id: str
    label_policy_version: str
    feature_manifest_id: str
    feature_manifest_hash: Sha256Hex
    formula_set_version: str
    formula_set_hash: Sha256Hex
    cost_model_version: str | None = None
    members: tuple[FrozenDatasetMemberV1, ...]
    member_count: int = Field(ge=0)
    member_manifest_hash: Sha256Hex
    base_population: bool
    source_population_count: int = Field(ge=0)
    transformation_policy_id: str | None = None
    transformation_policy_version: str | None = None
    state_distribution: dict[str, int]
    outcome_distribution: dict[str, int]
    exclusion_reason_distribution: dict[str, int]
    evidence_root_digest: Sha256Hex
    parent_dataset_id: str | None = None
    parent_dataset_hash: Sha256Hex | None = None
    code_digest: Sha256Hex | None = None

    @field_validator("members", mode="before")
    @classmethod
    def normalize_member_order(cls, value: Any) -> tuple[FrozenDatasetMemberV1, ...]:
        if not isinstance(value, (list, tuple)):
            raise ValueError("DATASET_MEMBERS_REQUIRED")
        members = tuple(FrozenDatasetMemberV1.model_validate(item) for item in value)
        return tuple(sorted(members, key=lambda item: item.member_id))

    @model_validator(mode="after")
    def validate_manifest(self, info: ValidationInfo) -> "FrozenDatasetManifestV1":
        if not (self.decision_cutoff < self.label_cutoff < self.build_cutoff):
            raise ValueError("DATASET_CUTOFF_ORDER_INVALID")
        if self.member_count != len(self.members):
            raise ValueError("DATASET_MEMBER_COUNT_MISMATCH")
        if len({row.member_id for row in self.members}) != len(self.members):
            raise ValueError("DUPLICATE_DATASET_MEMBER")
        if bool(self.parent_dataset_id) != bool(self.parent_dataset_hash):
            raise ValueError("PARENT_DATASET_ID_HASH_PAIR_REQUIRED")
        if self.base_population:
            if self.source_population_count != self.member_count:
                raise ValueError("BASE_POPULATION_INCOMPLETE")
            if self.exclusion_reason_distribution:
                raise ValueError("BASE_POPULATION_CANNOT_DECLARE_EXCLUSIONS")
        else:
            if not self.transformation_policy_id or not self.transformation_policy_version:
                raise ValueError("EXCLUSION_POLICY_REQUIRED")
            if self.source_population_count != self.member_count + sum(self.exclusion_reason_distribution.values()):
                raise ValueError("TRANSFORMED_POPULATION_COUNT_MISMATCH")
        if self.member_manifest_hash != canonical_hash([row.member_hash for row in self.members]):
            raise ValueError("MEMBER_MANIFEST_HASH_MISMATCH")
        expected_states = dict(sorted(Counter(row.public_state for row in self.members).items()))
        expected_outcomes = dict(sorted(Counter(row.outcome_state for row in self.members if row.outcome_state).items()))
        if self.state_distribution != expected_states:
            raise ValueError("STATE_DISTRIBUTION_MISMATCH")
        if self.outcome_distribution != expected_outcomes:
            raise ValueError("OUTCOME_DISTRIBUTION_MISMATCH")
        evidence_material = sorted(canonical_json(root) for member in self.members for root in member.evidence_roots)
        if self.evidence_root_digest != canonical_hash(evidence_material):
            raise ValueError("EVIDENCE_ROOT_DIGEST_MISMATCH")
        for member in self.members:
            if member.feature_manifest_id != self.feature_manifest_id or member.feature_manifest_hash != self.feature_manifest_hash:
                raise ValueError("FEATURE_MANIFEST_MISMATCH")
            if member.formula_set_version != self.formula_set_version or member.formula_set_hash != self.formula_set_hash:
                raise ValueError("FORMULA_SET_MISMATCH")
        if _identity_check_skipped(info, "dataset"):
            return self
        if self.dataset_hash != canonical_hash(_identity_material(self, "dataset_hash")):
            raise ValueError("DATASET_HASH_MISMATCH")
        return self


def _member_with_dataset_cutoff(
    member: FrozenDatasetMemberV1,
    build_cutoff: datetime,
    label_cutoff: datetime,
) -> FrozenDatasetMemberV1:
    for value in (member.outcome_available_at, member.label_available_at, member.revision_available_at):
        if value is not None and value > build_cutoff:
            raise ValueError("FUTURE_LABEL_EXCEEDS_BUILD_CUTOFF")
    if member.label_available_at is not None and member.label_available_at > label_cutoff:
        raise ValueError("FUTURE_LABEL_EXCEEDS_LABEL_CUTOFF")
    return member


def build_frozen_dataset_manifest(**values: Any) -> FrozenDatasetManifestV1:
    source = dict(values)
    source.pop("dataset_hash", None)
    source.pop("datasetHash", None)
    decision_cutoff = _aware(source["decision_cutoff"], "DATASET_DECISION_CUTOFF_REQUIRES_TIMEZONE")
    label_cutoff = _aware(source["label_cutoff"], "DATASET_LABEL_CUTOFF_REQUIRES_TIMEZONE")
    build_cutoff = _aware(source["build_cutoff"], "DATASET_BUILD_CUTOFF_REQUIRES_TIMEZONE")
    if not decision_cutoff < label_cutoff < build_cutoff:
        raise ValueError("DATASET_CUTOFF_ORDER_INVALID")
    members = tuple(
        sorted(
            (
                _member_with_dataset_cutoff(FrozenDatasetMemberV1.model_validate(member), build_cutoff, label_cutoff)
                for member in source["members"]
            ),
            key=lambda item: item.member_id,
        )
    )
    if len({row.member_id for row in members}) != len(members):
        raise ValueError("DUPLICATE_DATASET_MEMBER")
    exclusions = dict(sorted(source.get("exclusion_reason_distribution", {}).items()))
    prepared = {
        **source,
        "created_at": _aware(source["created_at"], "DATASET_CREATED_AT_REQUIRES_TIMEZONE"),
        "decision_cutoff": decision_cutoff,
        "label_cutoff": label_cutoff,
        "build_cutoff": build_cutoff,
        "members": members,
        "member_count": len(members),
        "member_manifest_hash": canonical_hash([row.member_hash for row in members]),
        "state_distribution": dict(sorted(Counter(row.public_state for row in members).items())),
        "outcome_distribution": dict(sorted(Counter(row.outcome_state for row in members if row.outcome_state).items())),
        "exclusion_reason_distribution": exclusions,
        "evidence_root_digest": canonical_hash(sorted(canonical_json(root) for member in members for root in member.evidence_roots)),
    }
    placeholder = "0" * 64
    draft = FrozenDatasetManifestV1.model_validate(
        {**prepared, "dataset_hash": placeholder},
        context={"rhist03d_skip_identity": "dataset"},
    )
    dataset_hash = canonical_hash(_identity_material(draft, "dataset_hash"))
    return FrozenDatasetManifestV1.model_validate(
        {**draft.model_dump(mode="python", by_alias=False), "dataset_hash": dataset_hash}
    )


def verify_frozen_dataset_manifest(
    manifest: FrozenDatasetManifestV1 | dict[str, Any],
    *,
    available_evidence_hashes: set[str],
) -> FrozenDatasetManifestV1:
    model = manifest if isinstance(manifest, FrozenDatasetManifestV1) else FrozenDatasetManifestV1.model_validate(manifest)
    available = {_normalize_sha256(value) for value in available_evidence_hashes}
    for member in model.members:
        required = {root.content_hash for root in member.evidence_roots if root.content_hash is not None}
        if not required.issubset(available):
            raise ValueError("EVIDENCE_ROOT_MISSING")
    return model


class GovernedModelVersionV1(BaseModel):
    model_config = MODEL_CONFIG
    schema_version: str = MODEL_SCHEMA_VERSION
    model_id: str
    model_version: str
    purpose: str
    market: str
    horizon: str
    training_dataset_id: str
    training_dataset_version: str
    training_dataset_hash: Sha256Hex
    evaluation_dataset_id: str
    evaluation_dataset_version: str
    evaluation_dataset_hash: Sha256Hex
    holdout_dataset_id: str | None = None
    holdout_dataset_version: str | None = None
    holdout_dataset_hash: Sha256Hex | None = None
    feature_set_hash: Sha256Hex
    formula_set_hash: Sha256Hex
    model_artifact_hash: Sha256Hex
    code_build_hash: Sha256Hex
    config_hash: Sha256Hex
    hyperparameters: dict[str, Any]
    random_seeds: tuple[int, ...]
    cost_model_version: str
    evaluation_id: str
    evaluation_hash: Sha256Hex
    created_at: UtcDateTime
    model_hash: Sha256Hex
    governance_state: Literal["CHALLENGER"] = "CHALLENGER"
    automatic_promotion_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False

    @field_validator("hyperparameters", mode="before")
    @classmethod
    def validate_hyperparameter_keys(cls, value: Any) -> Any:
        return _require_string_keys(value)

    @model_validator(mode="after")
    def validate_model_hash(self, info: ValidationInfo) -> "GovernedModelVersionV1":
        holdout_fields = (self.holdout_dataset_id, self.holdout_dataset_version, self.holdout_dataset_hash)
        if any(field is not None for field in holdout_fields) and not all(field is not None for field in holdout_fields):
            raise ValueError("MODEL_HOLDOUT_BINDING_INCOMPLETE")
        canonical_json(self.hyperparameters)
        if _identity_check_skipped(info, "model"):
            return self
        if self.model_hash != canonical_hash(_identity_material(self, "model_hash")):
            raise ValueError("MODEL_HASH_MISMATCH")
        return self


def build_governed_model_version(**values: Any) -> GovernedModelVersionV1:
    source = dict(values)
    training = FrozenDatasetManifestV1.model_validate(source.pop("training_dataset"))
    evaluation = FrozenDatasetManifestV1.model_validate(source.pop("evaluation_dataset"))
    holdout_value = source.pop("holdout_dataset", None)
    holdout = FrozenDatasetManifestV1.model_validate(holdout_value) if holdout_value is not None else None
    for supplied, actual, code in (
        (source.pop("training_dataset_hash", None), training.dataset_hash, "MODEL_DATASET_BINDING_MISMATCH"),
        (source.pop("evaluation_dataset_hash", None), evaluation.dataset_hash, "MODEL_EVALUATION_BINDING_MISMATCH"),
        (source.pop("holdout_dataset_hash", None), holdout.dataset_hash if holdout else None, "MODEL_HOLDOUT_BINDING_MISMATCH"),
    ):
        if supplied is not None and supplied != actual:
            raise ValueError(code)
    source.pop("model_hash", None)
    source.pop("modelHash", None)
    prepared = {
        **source,
        "training_dataset_id": training.dataset_id,
        "training_dataset_version": training.dataset_version,
        "training_dataset_hash": training.dataset_hash,
        "evaluation_dataset_id": evaluation.dataset_id,
        "evaluation_dataset_version": evaluation.dataset_version,
        "evaluation_dataset_hash": evaluation.dataset_hash,
        "holdout_dataset_id": holdout.dataset_id if holdout else None,
        "holdout_dataset_version": holdout.dataset_version if holdout else None,
        "holdout_dataset_hash": holdout.dataset_hash if holdout else None,
    }
    placeholder = "0" * 64
    draft = GovernedModelVersionV1.model_validate(
        {**prepared, "model_hash": placeholder},
        context={"rhist03d_skip_identity": "model"},
    )
    model_hash = canonical_hash(_identity_material(draft, "model_hash"))
    return GovernedModelVersionV1.model_validate(
        {**draft.model_dump(mode="python", by_alias=False), "model_hash": model_hash}
    )


class StrategyProfileVersionV1(BaseModel):
    model_config = MODEL_CONFIG
    schema_version: str = PROFILE_SCHEMA_VERSION
    profile_id: str
    profile_version: str
    strategy_id: str
    strategy_version: str
    market: str
    instrument_class: str
    horizon: str
    timeframes: tuple[str, ...]
    setups: tuple[str, ...]
    directions: tuple[str, ...]
    required_to_calculate: tuple[str, ...]
    required_to_qualify: tuple[str, ...]
    optional_context: tuple[str, ...]
    prohibited_for_condition: tuple[str, ...]
    relative_strength_contract: str
    gate_policy: str
    ranking_group: str
    risk_cost_assumptions: tuple[str, ...]
    model_id: str | None = None
    model_version: str | None = None
    model_hash: Sha256Hex | None = None
    research_ceiling: str
    activation_allowed: Literal[False] = False
    created_at: UtcDateTime
    valid_from: UtcDateTime
    content_hash: Sha256Hex

    @field_validator(
        "timeframes", "setups", "directions", "required_to_calculate",
        "required_to_qualify", "optional_context", "prohibited_for_condition",
        "risk_cost_assumptions", mode="before",
    )
    @classmethod
    def normalize_profile_set_fields(cls, value: Any) -> tuple[Any, ...]:
        return _normalized_set_tuple(value, code="PROFILE_SET_FIELD_DUPLICATE")

    @model_validator(mode="after")
    def validate_content_hash(self, info: ValidationInfo) -> "StrategyProfileVersionV1":
        model_binding = (self.model_id, self.model_version, self.model_hash)
        if any(value is not None for value in model_binding) and not all(value is not None for value in model_binding):
            raise ValueError("PROFILE_MODEL_BINDING_INCOMPLETE")
        if _identity_check_skipped(info, "profile"):
            return self
        if self.content_hash != canonical_hash(_identity_material(self, "content_hash")):
            raise ValueError("PROFILE_CONTENT_HASH_MISMATCH")
        return self


def build_strategy_profile_version(**values: Any) -> StrategyProfileVersionV1:
    source = dict(values)
    if source.get("activation_allowed", False):
        raise ValueError("R_HIST_03D_CANNOT_ACTIVATE_PROFILE")
    source.pop("content_hash", None)
    source.pop("contentHash", None)
    placeholder = "0" * 64
    draft = StrategyProfileVersionV1.model_validate(
        {**source, "content_hash": placeholder},
        context={"rhist03d_skip_identity": "profile"},
    )
    content_hash = canonical_hash(_identity_material(draft, "content_hash"))
    return StrategyProfileVersionV1.model_validate(
        {**draft.model_dump(mode="python", by_alias=False), "content_hash": content_hash}
    )


class GovernanceAuditRecordV1(BaseModel):
    model_config = MODEL_CONFIG
    schema_version: str = AUDIT_SCHEMA_VERSION
    audit_id: str
    reviewed_artifact_type: str
    artifact_id: str
    artifact_version: str
    artifact_hash: Sha256Hex
    dataset_id: str | None = None
    dataset_hash: Sha256Hex | None = None
    model_id: str | None = None
    model_hash: Sha256Hex | None = None
    profile_id: str | None = None
    profile_hash: Sha256Hex | None = None
    evaluation_id: str | None = None
    evaluation_hash: Sha256Hex | None = None
    predecessor_audit_hash: Sha256Hex | None = None
    decision: Literal["APPROVE", "REJECT", "ROLLBACK", "REVIEW"]
    reviewer: str
    reason: str
    reviewed_at: UtcDateTime
    evidence_hash: Sha256Hex
    governance_policy_version: str
    pit_prerequisite_proven: bool
    resulting_state: str
    record_hash: Sha256Hex
    automatic_promotion_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_record_hash(self, info: ValidationInfo) -> "GovernanceAuditRecordV1":
        for name, artifact_id, artifact_hash in (
            ("DATASET", self.dataset_id, self.dataset_hash),
            ("MODEL", self.model_id, self.model_hash),
            ("PROFILE", self.profile_id, self.profile_hash),
            ("EVALUATION", self.evaluation_id, self.evaluation_hash),
        ):
            if bool(artifact_id) != bool(artifact_hash):
                raise ValueError(f"AUDIT_{name}_ID_HASH_PAIR_REQUIRED")
        if not self.reviewer.strip() or not self.reason.strip():
            raise ValueError("AUDIT_REVIEWER_AND_REASON_REQUIRED")
        if self.decision == "APPROVE" and not self.pit_prerequisite_proven:
            raise ValueError("PIT_PREREQUISITE_UNPROVEN")
        if _identity_check_skipped(info, "audit"):
            return self
        if self.record_hash != canonical_hash(_identity_material(self, "record_hash")):
            raise ValueError("AUDIT_RECORD_HASH_MISMATCH")
        return self


def build_governance_audit_record(**values: Any) -> GovernanceAuditRecordV1:
    source = dict(values)
    if source.get("decision") == "APPROVE" and not source.get("pit_prerequisite_proven"):
        raise ValueError("PIT_PREREQUISITE_UNPROVEN")
    if not str(source.get("reviewer", "")).strip() or not str(source.get("reason", "")).strip():
        raise ValueError("AUDIT_REVIEWER_AND_REASON_REQUIRED")
    source.pop("record_hash", None)
    source.pop("recordHash", None)
    placeholder = "0" * 64
    draft = GovernanceAuditRecordV1.model_validate(
        {**source, "record_hash": placeholder},
        context={"rhist03d_skip_identity": "audit"},
    )
    record_hash = canonical_hash(_identity_material(draft, "record_hash"))
    return GovernanceAuditRecordV1.model_validate(
        {**draft.model_dump(mode="python", by_alias=False), "record_hash": record_hash}
    )


__all__ = (
    "AUDIT_SCHEMA_VERSION", "DATASET_SCHEMA_VERSION", "MODEL_SCHEMA_VERSION",
    "PROFILE_SCHEMA_VERSION", "R_HIST_03D_AUTOMATIC_PROMOTION_ALLOWED",
    "R_HIST_03D_EXECUTION_AUTHORIZED", "FrozenDatasetManifestV1",
    "FrozenDatasetMemberV1", "FrozenEvidenceRootV1", "GovernanceAuditRecordV1",
    "GovernedModelVersionV1", "StrategyProfileVersionV1",
    "build_frozen_dataset_manifest", "build_frozen_dataset_member",
    "build_governance_audit_record", "build_governed_model_version",
    "build_strategy_profile_version", "canonical_hash", "canonical_json",
    "verify_frozen_dataset_manifest",
)
