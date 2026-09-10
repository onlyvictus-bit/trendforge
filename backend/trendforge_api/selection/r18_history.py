"""R-HIST-03D immutable learning and governance history contracts.

This module is an implementation helper for the canonical R18 governance owner.
It adds no trading, promotion, strategy, or execution authority.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator
from pydantic.alias_generators import to_camel


R_HIST_03D_EXECUTION_AUTHORIZED = False
R_HIST_03D_AUTOMATIC_PROMOTION_ALLOWED = False
DATASET_SCHEMA_VERSION = "trendforge.rhist03d-frozen-dataset.v1"
MODEL_SCHEMA_VERSION = "trendforge.rhist03d-model-version.v1"
PROFILE_SCHEMA_VERSION = "trendforge.rhist03d-strategy-profile.v1"
AUDIT_SCHEMA_VERSION = "trendforge.rhist03d-audit.v1"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


def canonical_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", by_alias=True)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _aware(value: datetime, code: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(code)
    return value.astimezone(UTC)


def _hash64(value: str | None, code: str) -> None:
    if value is None or len(value) != 64 or any(
        ch not in "0123456789abcdef" for ch in value.casefold()
    ):
        raise ValueError(code)


def _normalized_material(
    model_type: type[BaseModel],
    values: dict[str, Any],
    *,
    computed_field: str,
) -> dict[str, Any]:
    """Return validated canonical material without constructing an invalid model.

    The previous implementation used ``model_construct``. That bypassed Pydantic
    validation and left nested dictionaries unconverted, so builders could hash a
    different logical object from the one later checked by normal model validation.
    Here every supplied/default field is validated through its declared field type
    before JSON-mode serialization. The object's own computed identity is excluded.
    Required fields that are deliberately computed by the caller (for example
    ``member_id``) may be absent at this stage and are therefore skipped; final
    public-model construction still enforces all required fields and validators.
    """
    source = dict(values)
    source.pop(computed_field, None)
    source.pop(to_camel(computed_field), None)
    material: dict[str, Any] = {}
    for field_name, field in model_type.model_fields.items():
        if field_name == computed_field:
            continue
        alias = field.alias or to_camel(field_name)
        if field_name in source:
            raw = source[field_name]
        elif alias in source:
            raw = source[alias]
        elif field.is_required():
            continue
        else:
            raw = field.get_default(call_default_factory=True)
        adapter = TypeAdapter(field.annotation)
        validated = adapter.validate_python(raw)
        material[alias] = adapter.dump_python(validated, mode="json")
    return material


class FrozenEvidenceRootV1(BaseModel):
    model_config = MODEL_CONFIG

    role: str = Field(min_length=1)
    run_id: str | None = None
    trading_date: str | None = None
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_root(self) -> "FrozenEvidenceRootV1":
        if self.content_hash is not None:
            _hash64(self.content_hash, "EVIDENCE_HASH_INVALID")
        if not any((self.run_id, self.trading_date, self.content_hash)):
            raise ValueError("EVIDENCE_ROOT_IDENTITY_REQUIRED")
        return self


class FrozenDatasetMemberV1(BaseModel):
    model_config = MODEL_CONFIG

    member_id: str
    member_hash: str
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
    decision_version_hash: str
    decision_at: datetime
    decision_data_cutoff: datetime
    max_feature_available_at: datetime
    public_state: str
    outcome_id: str | None = None
    outcome_hash: str | None = None
    outcome_state: str | None = None
    outcome_available_at: datetime | None = None
    revision_id: str | None = None
    revision_hash: str | None = None
    revision_available_at: datetime | None = None
    label_available_at: datetime | None = None
    feature_manifest_id: str
    feature_manifest_hash: str
    formula_set_version: str
    formula_set_hash: str
    input_hashes: tuple[str, ...]
    evidence_roots: tuple[FrozenEvidenceRootV1, ...]
    split: str
    fold: str
    inclusion_reason: str
    exclusion_reason: str | None = None

    @model_validator(mode="after")
    def validate_member(self) -> "FrozenDatasetMemberV1":
        for value, code in (
            (self.decision_version_hash, "DECISION_HASH_INVALID"),
            (self.feature_manifest_hash, "FEATURE_MANIFEST_HASH_INVALID"),
            (self.formula_set_hash, "FORMULA_SET_HASH_INVALID"),
        ):
            _hash64(value, code)
        if self.outcome_hash is not None:
            _hash64(self.outcome_hash, "OUTCOME_HASH_INVALID")
        if self.revision_hash is not None:
            _hash64(self.revision_hash, "REVISION_HASH_INVALID")
        for value in self.input_hashes:
            _hash64(value, "INPUT_HASH_INVALID")
        decision_at = _aware(self.decision_at, "DECISION_TIME_REQUIRES_TIMEZONE")
        decision_cutoff = _aware(
            self.decision_data_cutoff, "DECISION_CUTOFF_REQUIRES_TIMEZONE"
        )
        max_feature = _aware(
            self.max_feature_available_at, "FEATURE_TIME_REQUIRES_TIMEZONE"
        )
        if decision_cutoff < decision_at:
            raise ValueError("DECISION_CUTOFF_BEFORE_DECISION")
        if max_feature > decision_cutoff:
            raise ValueError("FUTURE_FEATURE_EXCEEDS_DECISION_CUTOFF")
        if self.outcome_available_at is not None:
            outcome_at = _aware(
                self.outcome_available_at, "OUTCOME_TIME_REQUIRES_TIMEZONE"
            )
            if outcome_at < decision_at:
                raise ValueError("FUTURE_LABEL_CHRONOLOGY_INVALID")
        if self.label_available_at is not None:
            label_at = _aware(
                self.label_available_at, "LABEL_TIME_REQUIRES_TIMEZONE"
            )
            if label_at < decision_at:
                raise ValueError("FUTURE_LABEL_CHRONOLOGY_INVALID")
        if self.revision_available_at is not None:
            _aware(self.revision_available_at, "REVISION_TIME_REQUIRES_TIMEZONE")
        if bool(self.outcome_id) != bool(self.outcome_hash):
            raise ValueError("OUTCOME_ID_HASH_PAIR_REQUIRED")
        if bool(self.revision_id) != bool(self.revision_hash):
            raise ValueError("REVISION_ID_HASH_PAIR_REQUIRED")
        if not self.evidence_roots:
            raise ValueError("EVIDENCE_ROOTS_REQUIRED")
        material = self.model_dump(
            mode="json",
            by_alias=True,
            exclude={"member_id", "member_hash"},
        )
        expected_hash = canonical_hash(material)
        if self.member_hash != expected_hash:
            raise ValueError("DATASET_MEMBER_HASH_MISMATCH")
        expected_id = "rhist03d-member:" + expected_hash
        if self.member_id != expected_id:
            raise ValueError("DATASET_MEMBER_ID_MISMATCH")
        return self


def build_frozen_dataset_member(**values: Any) -> FrozenDatasetMemberV1:
    for key in ("decision_at", "decision_data_cutoff", "max_feature_available_at"):
        values[key] = _aware(values[key], key.upper() + "_REQUIRES_TIMEZONE")
    if values["decision_data_cutoff"] < values["decision_at"]:
        raise ValueError("DECISION_CUTOFF_BEFORE_DECISION")
    if values["max_feature_available_at"] > values["decision_data_cutoff"]:
        raise ValueError("FUTURE_FEATURE_EXCEEDS_DECISION_CUTOFF")
    for key in ("outcome_available_at", "label_available_at"):
        if values.get(key) is not None:
            values[key] = _aware(values[key], "FUTURE_LABEL_TIMEZONE_REQUIRED")
    if (
        values.get("outcome_available_at") is not None
        and values.get("label_available_at") is not None
        and values["outcome_available_at"] != values["label_available_at"]
    ):
        raise ValueError("FUTURE_LABEL_AVAILABILITY_MISMATCH")
    material = _normalized_material(
        FrozenDatasetMemberV1,
        values,
        computed_field="member_hash",
    )
    material.pop("memberId", None)
    member_hash = canonical_hash(material)
    return FrozenDatasetMemberV1(
        **values,
        member_hash=member_hash,
        member_id="rhist03d-member:" + member_hash,
    )


class FrozenDatasetManifestV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = DATASET_SCHEMA_VERSION
    dataset_id: str
    dataset_version: str
    dataset_hash: str
    purpose: str
    created_at: datetime
    decision_cutoff: datetime
    label_cutoff: datetime
    build_cutoff: datetime
    population_policy_id: str
    population_policy_version: str
    label_policy_id: str
    label_policy_version: str
    feature_manifest_id: str
    feature_manifest_hash: str
    formula_set_version: str
    formula_set_hash: str
    cost_model_version: str | None = None
    members: tuple[FrozenDatasetMemberV1, ...]
    member_count: int
    member_manifest_hash: str
    base_population: bool
    source_population_count: int
    transformation_policy_id: str | None = None
    transformation_policy_version: str | None = None
    state_distribution: dict[str, int]
    outcome_distribution: dict[str, int]
    exclusion_reason_distribution: dict[str, int]
    evidence_root_digest: str
    parent_dataset_id: str | None = None
    parent_dataset_hash: str | None = None
    code_digest: str | None = None

    @model_validator(mode="after")
    def validate_manifest(self) -> "FrozenDatasetManifestV1":
        for value, code in (
            (self.dataset_hash, "DATASET_HASH_INVALID"),
            (self.member_manifest_hash, "MEMBER_MANIFEST_HASH_INVALID"),
            (self.feature_manifest_hash, "FEATURE_MANIFEST_HASH_INVALID"),
            (self.formula_set_hash, "FORMULA_SET_HASH_INVALID"),
            (self.evidence_root_digest, "EVIDENCE_ROOT_DIGEST_INVALID"),
        ):
            _hash64(value, code)
        if self.parent_dataset_hash is not None:
            _hash64(self.parent_dataset_hash, "PARENT_DATASET_HASH_INVALID")
        if self.code_digest is not None:
            _hash64(self.code_digest, "CODE_DIGEST_INVALID")
        if not (self.decision_cutoff < self.label_cutoff < self.build_cutoff):
            raise ValueError("DATASET_CUTOFF_ORDER_INVALID")
        if self.member_count != len(self.members):
            raise ValueError("DATASET_MEMBER_COUNT_MISMATCH")
        if len({row.member_id for row in self.members}) != len(self.members):
            raise ValueError("DUPLICATE_DATASET_MEMBER")
        if self.base_population and self.source_population_count != self.member_count:
            raise ValueError("BASE_POPULATION_INCOMPLETE")
        if not self.base_population:
            if not self.transformation_policy_id or not self.transformation_policy_version:
                raise ValueError("EXCLUSION_POLICY_REQUIRED")
            if self.source_population_count != self.member_count + sum(
                self.exclusion_reason_distribution.values()
            ):
                raise ValueError("TRANSFORMED_POPULATION_COUNT_MISMATCH")
        expected_members = canonical_hash(
            [
                row.member_hash
                for row in sorted(self.members, key=lambda item: item.member_id)
            ]
        )
        if self.member_manifest_hash != expected_members:
            raise ValueError("MEMBER_MANIFEST_HASH_MISMATCH")
        material = self.model_dump(
            mode="json", by_alias=True, exclude={"dataset_hash"}
        )
        if self.dataset_hash != canonical_hash(material):
            raise ValueError("DATASET_HASH_MISMATCH")
        return self


def _member_with_dataset_cutoff(
    member: FrozenDatasetMemberV1, build_cutoff: datetime, label_cutoff: datetime
) -> FrozenDatasetMemberV1:
    for value in (
        member.outcome_available_at,
        member.label_available_at,
        member.revision_available_at,
    ):
        if value is not None and value > build_cutoff:
            raise ValueError("FUTURE_LABEL_EXCEEDS_BUILD_CUTOFF")
    if member.label_available_at is not None and member.label_available_at > label_cutoff:
        raise ValueError("FUTURE_LABEL_EXCEEDS_LABEL_CUTOFF")
    return member


def build_frozen_dataset_manifest(**values: Any) -> FrozenDatasetManifestV1:
    decision_cutoff = _aware(
        values["decision_cutoff"], "DATASET_DECISION_CUTOFF_REQUIRES_TIMEZONE"
    )
    label_cutoff = _aware(
        values["label_cutoff"], "DATASET_LABEL_CUTOFF_REQUIRES_TIMEZONE"
    )
    build_cutoff = _aware(
        values["build_cutoff"], "DATASET_BUILD_CUTOFF_REQUIRES_TIMEZONE"
    )
    if not decision_cutoff < label_cutoff < build_cutoff:
        raise ValueError("DATASET_CUTOFF_ORDER_INVALID")
    members = tuple(
        _member_with_dataset_cutoff(member, build_cutoff, label_cutoff)
        for member in values["members"]
    )
    if len({row.member_id for row in members}) != len(members):
        raise ValueError("DUPLICATE_DATASET_MEMBER")
    state_distribution = dict(sorted(Counter(row.public_state for row in members).items()))
    outcome_distribution = dict(
        sorted(Counter(row.outcome_state for row in members if row.outcome_state).items())
    )
    exclusions = dict(sorted(values.get("exclusion_reason_distribution", {}).items()))
    member_manifest_hash = canonical_hash(
        [row.member_hash for row in sorted(members, key=lambda item: item.member_id)]
    )
    evidence_material = sorted(
        canonical_json(root) for member in members for root in member.evidence_roots
    )
    evidence_root_digest = canonical_hash(evidence_material)
    prepared = {
        **values,
        "created_at": _aware(
            values["created_at"], "DATASET_CREATED_AT_REQUIRES_TIMEZONE"
        ),
        "decision_cutoff": decision_cutoff,
        "label_cutoff": label_cutoff,
        "build_cutoff": build_cutoff,
        "members": tuple(sorted(members, key=lambda item: item.member_id)),
        "member_count": len(members),
        "member_manifest_hash": member_manifest_hash,
        "state_distribution": state_distribution,
        "outcome_distribution": outcome_distribution,
        "exclusion_reason_distribution": exclusions,
        "evidence_root_digest": evidence_root_digest,
    }
    if prepared.get("base_population", True) and prepared.get(
        "source_population_count"
    ) != len(members):
        raise ValueError("BASE_POPULATION_INCOMPLETE")
    if not prepared.get("base_population", True):
        if not prepared.get("transformation_policy_id") or not prepared.get(
            "transformation_policy_version"
        ):
            raise ValueError("EXCLUSION_POLICY_REQUIRED")
    material = _normalized_material(
        FrozenDatasetManifestV1,
        prepared,
        computed_field="dataset_hash",
    )
    dataset_hash = canonical_hash(material)
    return FrozenDatasetManifestV1(**prepared, dataset_hash=dataset_hash)


def verify_frozen_dataset_manifest(
    manifest: FrozenDatasetManifestV1 | dict[str, Any],
    *,
    available_evidence_hashes: set[str],
) -> FrozenDatasetManifestV1:
    model = (
        manifest
        if isinstance(manifest, FrozenDatasetManifestV1)
        else FrozenDatasetManifestV1.model_validate(manifest)
    )
    available = {value.casefold() for value in available_evidence_hashes}
    for member in model.members:
        if member.feature_manifest_hash != model.feature_manifest_hash:
            raise ValueError("FEATURE_MANIFEST_MISMATCH")
        required = {
            root.content_hash.casefold()
            for root in member.evidence_roots
            if root.content_hash
        }
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
    training_dataset_hash: str
    evaluation_dataset_id: str
    evaluation_dataset_version: str
    evaluation_dataset_hash: str
    holdout_dataset_id: str | None = None
    holdout_dataset_version: str | None = None
    holdout_dataset_hash: str | None = None
    feature_set_hash: str
    formula_set_hash: str
    model_artifact_hash: str
    code_build_hash: str
    config_hash: str
    hyperparameters: dict[str, Any]
    random_seeds: tuple[int, ...]
    cost_model_version: str
    evaluation_id: str
    evaluation_hash: str
    created_at: datetime
    model_hash: str
    governance_state: Literal["CHALLENGER"] = "CHALLENGER"
    automatic_promotion_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_model_hash(self) -> "GovernedModelVersionV1":
        for value, code in (
            (self.training_dataset_hash, "MODEL_TRAINING_DATASET_HASH_INVALID"),
            (self.evaluation_dataset_hash, "MODEL_EVALUATION_DATASET_HASH_INVALID"),
            (self.feature_set_hash, "MODEL_FEATURE_SET_HASH_INVALID"),
            (self.formula_set_hash, "MODEL_FORMULA_SET_HASH_INVALID"),
            (self.model_artifact_hash, "MODEL_ARTIFACT_HASH_INVALID"),
            (self.code_build_hash, "MODEL_CODE_HASH_INVALID"),
            (self.config_hash, "MODEL_CONFIG_HASH_INVALID"),
            (self.evaluation_hash, "MODEL_EVALUATION_HASH_INVALID"),
            (self.model_hash, "MODEL_HASH_INVALID"),
        ):
            _hash64(value, code)
        if self.holdout_dataset_hash is not None:
            _hash64(self.holdout_dataset_hash, "MODEL_HOLDOUT_HASH_INVALID")
        material = self.model_dump(
            mode="json", by_alias=True, exclude={"model_hash"}
        )
        if self.model_hash != canonical_hash(material):
            raise ValueError("MODEL_HASH_MISMATCH")
        return self


def build_governed_model_version(**values: Any) -> GovernedModelVersionV1:
    training = values.pop("training_dataset")
    evaluation = values.pop("evaluation_dataset")
    holdout = values.pop("holdout_dataset", None)
    provided_training_hash = values.pop("training_dataset_hash", None)
    if (
        provided_training_hash is not None
        and provided_training_hash != training.dataset_hash
    ):
        raise ValueError("MODEL_DATASET_BINDING_MISMATCH")
    if values.get("model_artifact_hash") is None or len(
        str(values["model_artifact_hash"])
    ) != 64:
        raise ValueError("MODEL_ARTIFACT_HASH_INVALID")
    prepared = {
        **values,
        "training_dataset_id": training.dataset_id,
        "training_dataset_version": training.dataset_version,
        "training_dataset_hash": training.dataset_hash,
        "evaluation_dataset_id": evaluation.dataset_id,
        "evaluation_dataset_version": evaluation.dataset_version,
        "evaluation_dataset_hash": evaluation.dataset_hash,
        "holdout_dataset_id": holdout.dataset_id if holdout else None,
        "holdout_dataset_version": holdout.dataset_version if holdout else None,
        "holdout_dataset_hash": holdout.dataset_hash if holdout else None,
        "created_at": _aware(
            values["created_at"], "MODEL_CREATED_AT_REQUIRES_TIMEZONE"
        ),
    }
    material = _normalized_material(
        GovernedModelVersionV1,
        prepared,
        computed_field="model_hash",
    )
    model_hash = canonical_hash(material)
    return GovernedModelVersionV1(**prepared, model_hash=model_hash)


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
    model_hash: str | None = None
    research_ceiling: str
    activation_allowed: Literal[False] = False
    created_at: datetime
    valid_from: datetime
    content_hash: str

    @model_validator(mode="after")
    def validate_content_hash(self) -> "StrategyProfileVersionV1":
        _hash64(self.content_hash, "PROFILE_CONTENT_HASH_INVALID")
        if any((self.model_id, self.model_version, self.model_hash)) and not all(
            (self.model_id, self.model_version, self.model_hash)
        ):
            raise ValueError("PROFILE_MODEL_BINDING_INCOMPLETE")
        if self.model_hash is not None:
            _hash64(self.model_hash, "PROFILE_MODEL_HASH_INVALID")
        material = self.model_dump(
            mode="json", by_alias=True, exclude={"content_hash"}
        )
        if self.content_hash != canonical_hash(material):
            raise ValueError("PROFILE_CONTENT_HASH_MISMATCH")
        return self


def build_strategy_profile_version(**values: Any) -> StrategyProfileVersionV1:
    if values.get("activation_allowed", False):
        raise ValueError("R_HIST_03D_CANNOT_ACTIVATE_PROFILE")
    if any(values.get(name) for name in ("model_id", "model_version", "model_hash")) and not all(
        values.get(name) for name in ("model_id", "model_version", "model_hash")
    ):
        raise ValueError("PROFILE_MODEL_BINDING_INCOMPLETE")
    if values.get("model_hash") is not None:
        _hash64(values["model_hash"], "PROFILE_MODEL_HASH_INVALID")
    prepared = {
        **values,
        "created_at": _aware(
            values["created_at"], "PROFILE_CREATED_AT_REQUIRES_TIMEZONE"
        ),
        "valid_from": _aware(
            values["valid_from"], "PROFILE_VALID_FROM_REQUIRES_TIMEZONE"
        ),
    }
    prepared.pop("content_hash", None)
    material = _normalized_material(
        StrategyProfileVersionV1,
        prepared,
        computed_field="content_hash",
    )
    content_hash = canonical_hash(material)
    return StrategyProfileVersionV1(**prepared, content_hash=content_hash)


class GovernanceAuditRecordV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = AUDIT_SCHEMA_VERSION
    audit_id: str
    reviewed_artifact_type: str
    artifact_id: str
    artifact_version: str
    artifact_hash: str
    dataset_id: str | None = None
    dataset_hash: str | None = None
    model_id: str | None = None
    model_hash: str | None = None
    profile_id: str | None = None
    profile_hash: str | None = None
    evaluation_id: str | None = None
    evaluation_hash: str | None = None
    predecessor_audit_hash: str | None = None
    decision: Literal["APPROVE", "REJECT", "ROLLBACK", "REVIEW"]
    reviewer: str
    reason: str
    reviewed_at: datetime
    evidence_hash: str
    governance_policy_version: str
    pit_prerequisite_proven: bool
    resulting_state: str
    record_hash: str
    automatic_promotion_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_record_hash(self) -> "GovernanceAuditRecordV1":
        _hash64(self.record_hash, "AUDIT_RECORD_HASH_INVALID")
        material = self.model_dump(
            mode="json", by_alias=True, exclude={"record_hash"}
        )
        if self.record_hash != canonical_hash(material):
            raise ValueError("AUDIT_RECORD_HASH_MISMATCH")
        return self


def build_governance_audit_record(**values: Any) -> GovernanceAuditRecordV1:
    if values.get("decision") == "APPROVE" and not values.get("pit_prerequisite_proven"):
        raise ValueError("PIT_PREREQUISITE_UNPROVEN")
    if not str(values.get("reviewer", "")).strip() or not str(
        values.get("reason", "")
    ).strip():
        raise ValueError("AUDIT_REVIEWER_AND_REASON_REQUIRED")
    for key in (
        "artifact_hash",
        "dataset_hash",
        "model_hash",
        "profile_hash",
        "evaluation_hash",
        "predecessor_audit_hash",
        "evidence_hash",
    ):
        if values.get(key) is not None:
            _hash64(values[key], "AUDIT_HASH_INVALID")
    prepared = {
        **values,
        "reviewed_at": _aware(
            values["reviewed_at"], "AUDIT_REVIEWED_AT_REQUIRES_TIMEZONE"
        ),
    }
    prepared.pop("record_hash", None)
    material = _normalized_material(
        GovernanceAuditRecordV1,
        prepared,
        computed_field="record_hash",
    )
    record_hash = canonical_hash(material)
    return GovernanceAuditRecordV1(**prepared, record_hash=record_hash)
