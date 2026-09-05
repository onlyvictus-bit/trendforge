"""Finite offline PK compatibility harness and native-promotion governance."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
from math import isfinite
from pathlib import Path
from time import perf_counter
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from ..selection.contracts import stable_id, to_camel


SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
WORKER_MODULE = "trendforge_api.scanners.pk_fixture_worker"
ALLOWED_FIXTURE_SUFFIXES = {".json"}
PK_MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    frozen=True,
    extra="forbid",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _canonical_bytes(value: BaseModel | dict) -> bytes:
    payload = (
        value.model_dump(mode="json", by_alias=True)
        if isinstance(value, BaseModel)
        else value
    )
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _require_hash(value: str, field_name: str) -> str:
    normalized = value.lower()
    if SHA256_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"{field_name} must be a SHA-256 hash")
    return normalized


class PKUpstreamPinStatus(StrEnum):
    VERIFIED = "VERIFIED"
    FIXTURE_ONLY_UNVERIFIED = "FIXTURE_ONLY_UNVERIFIED"


class PKDiscrepancyClass(StrEnum):
    MATCH = "MATCH"
    INTENDED_DIFFERENCE = "INTENDED_DIFFERENCE"
    NATIVE_DEFECT = "NATIVE_DEFECT"
    UPSTREAM_DEFECT = "UPSTREAM_DEFECT"
    UNRESOLVED = "UNRESOLVED"


class PKReviewDecision(StrEnum):
    PENDING = "PENDING"
    APPROVE_MATCH = "APPROVE_MATCH"
    APPROVE_INTENDED_DIFFERENCE = "APPROVE_INTENDED_DIFFERENCE"
    REJECT_NATIVE = "REJECT_NATIVE"
    REJECT_UPSTREAM = "REJECT_UPSTREAM"
    UNRESOLVED = "UNRESOLVED"


class PKPromotionStatus(StrEnum):
    REGISTERED_NOT_ACTIVE = "REGISTERED_NOT_ACTIVE"
    NATIVE_PROMOTION_CANDIDATE = "NATIVE_PROMOTION_CANDIDATE"
    NATIVE_PROMOTED = "NATIVE_PROMOTED"
    REJECTED = "REJECTED"


class PKHarnessStatus(StrEnum):
    COMPLETED = "COMPLETED"
    INPUT_REJECTED = "INPUT_REJECTED"
    PROCESS_FAILED = "PROCESS_FAILED"
    TIMED_OUT = "TIMED_OUT"
    OUTPUT_REJECTED = "OUTPUT_REJECTED"


class PKFaultMode(StrEnum):
    NONE = "NONE"
    CRASH = "CRASH"
    TIMEOUT = "TIMEOUT"
    INVALID_JSON = "INVALID_JSON"
    OVERSIZED_OUTPUT = "OVERSIZED_OUTPUT"


class PKScannerDisposition(StrEnum):
    NATIVE_MAPPED = "NATIVE_MAPPED"
    QUARANTINED = "QUARANTINED"


class PKTagStatus(StrEnum):
    TAGGED_REFERENCE = "TAGGED_REFERENCE"
    QUARANTINED = "QUARANTINED"


class PKUpstreamPin(BaseModel):
    model_config = PK_MODEL_CONFIG

    repository: str = Field(min_length=1)
    commit: str
    license_hash: str
    isolated_environment_lock_hash: str
    pin_status: PKUpstreamPinStatus

    @field_validator("commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        normalized = value.lower()
        if COMMIT_PATTERN.fullmatch(normalized) is None:
            raise ValueError("commit must be a 40-character hexadecimal hash")
        return normalized

    @field_validator("license_hash", "isolated_environment_lock_hash")
    @classmethod
    def validate_hashes(cls, value: str, info) -> str:
        return _require_hash(value, info.field_name)

    @model_validator(mode="after")
    def validate_pin_status(self) -> "PKUpstreamPin":
        if self.pin_status is PKUpstreamPinStatus.VERIFIED:
            if not self.repository.startswith("https://"):
                raise ValueError("verified upstream repository must use HTTPS")
            if self.commit == "0" * 40:
                raise ValueError("verified upstream commit cannot be a placeholder")
        elif not self.repository.startswith("fixture://"):
            raise ValueError("unverified pin is allowed only for local fixtures")
        return self


class PKFixtureManifest(BaseModel):
    model_config = PK_MODEL_CONFIG

    manifest_id: str = Field(min_length=1)
    manifest_version: str = Field(min_length=1)
    fixture_id: str = Field(min_length=1)
    fixture_schema_version: str = Field(min_length=1)
    fixture_hash: str
    approved_artifacts: tuple[str, ...]

    @field_validator("fixture_hash")
    @classmethod
    def validate_fixture_hash(cls, value: str) -> str:
        return _require_hash(value, "fixture_hash")

    @model_validator(mode="after")
    def reject_executable_or_cached_artifacts(self) -> "PKFixtureManifest":
        if not self.approved_artifacts:
            raise ValueError("fixture manifest needs at least one approved artifact")
        for artifact in self.approved_artifacts:
            artifact_path = Path(artifact)
            if (
                artifact_path.name != artifact
                or artifact_path.is_absolute()
                or re.match(r"^[A-Za-z]:", artifact)
                or "\\" in artifact
                or artifact_path.suffix.lower() not in ALLOWED_FIXTURE_SUFFIXES
            ):
                raise ValueError("only sanitized JSON fixture artifacts are allowed")
        return self


class PKNativeScannerSpec(BaseModel):
    model_config = PK_MODEL_CONFIG

    scanner_id: str = Field(min_length=1)
    scanner_version: str = Field(min_length=1)
    algorithm_id: str = Field(min_length=1)
    algorithm_version: str = Field(min_length=1)
    parameter_hash: str
    implementation_hash: str

    @field_validator("parameter_hash", "implementation_hash")
    @classmethod
    def validate_hashes(cls, value: str, info) -> str:
        return _require_hash(value, info.field_name)


class PKScannerInventoryEntry(BaseModel):
    """One scanner ID observed in the pinned upstream menu."""

    model_config = PK_MODEL_CONFIG

    scanner_id: str = Field(pattern=r"^X:(?:[0-9]|[1-4][0-9])$")
    label: str = Field(min_length=1)
    disposition: PKScannerDisposition
    native_feature_ids: tuple[str, ...] = ()
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_mapping(self) -> "PKScannerInventoryEntry":
        if self.disposition is PKScannerDisposition.NATIVE_MAPPED:
            if not self.native_feature_ids:
                raise ValueError("native-mapped scanner needs native feature IDs")
        elif self.native_feature_ids:
            raise ValueError("quarantined scanner cannot claim native feature IDs")
        return self


class PKR4InventoryManifest(BaseModel):
    """Pinned upstream facts; never an upstream runtime dependency."""

    model_config = PK_MODEL_CONFIG

    manifest_version: Literal["pk-r4-inventory-1"] = "pk-r4-inventory-1"
    upstream_pin: PKUpstreamPin
    license_name: Literal["MIT"] = "MIT"
    menu_source_hash: str
    scanner_source_hash: str
    dependency_lock_hash: str
    declared_dependencies: tuple[str, ...]
    entries: tuple[PKScannerInventoryEntry, ...]
    upstream_runtime_required: Literal[False] = False
    upstream_can_vote: Literal[False] = False
    production_authorized: Literal[False] = False

    @field_validator("menu_source_hash", "scanner_source_hash", "dependency_lock_hash")
    @classmethod
    def validate_inventory_hashes(cls, value: str, info) -> str:
        return _require_hash(value, info.field_name)

    @model_validator(mode="after")
    def require_complete_unique_inventory(self) -> "PKR4InventoryManifest":
        ids = tuple(entry.scanner_id for entry in self.entries)
        expected = tuple(f"X:{index}" for index in range(50))
        if ids != expected:
            raise ValueError("pinned scanner inventory must contain X:0 through X:49")
        if len(self.declared_dependencies) != 47:
            raise ValueError("pinned dependency inventory must contain 47 declarations")
        if len(set(self.declared_dependencies)) != len(self.declared_dependencies):
            raise ValueError("pinned dependency inventory must be unique")
        return self


class PKShadowTag(BaseModel):
    """Non-voting result of mapping one pinned scanner ID to native research."""

    model_config = PK_MODEL_CONFIG

    scanner_id: str = Field(min_length=1)
    status: PKTagStatus
    instrument_id: str | None = None
    symbol: str | None = None
    native_feature_ids: tuple[str, ...] = ()
    reason: str = Field(min_length=1)
    authority: Literal["EXPERIMENTAL_REFERENCE"] = "EXPERIMENTAL_REFERENCE"
    voting_weight: Literal[0.0] = 0.0
    can_affect_rank: Literal[False] = False
    can_affect_state: Literal[False] = False
    can_support_confirmed: Literal[False] = False

    @model_validator(mode="after")
    def validate_tag(self) -> "PKShadowTag":
        if self.status is PKTagStatus.TAGGED_REFERENCE:
            if not (self.instrument_id and self.symbol and self.native_feature_ids):
                raise ValueError("mapped tag needs canonical identity and feature IDs")
        elif self.instrument_id or self.native_feature_ids:
            raise ValueError("quarantined tag cannot expose mapped identity or features")
        return self


class PKUniverseMembershipFixture(BaseModel):
    """Early PIT/delisting fixture; membership is evaluated as-of, not today."""

    model_config = PK_MODEL_CONFIG

    instrument_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    member_from: datetime
    member_until: datetime | None = None
    delisted_at: datetime | None = None
    available_at: datetime

    @field_validator("member_from", "member_until", "delisted_at", "available_at")
    @classmethod
    def require_membership_timezone(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("membership timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_membership_window(self) -> "PKUniverseMembershipFixture":
        if self.member_until is not None and self.member_until <= self.member_from:
            raise ValueError("member_until must be after member_from")
        return self

    def eligible_at(self, decision_at: datetime) -> bool:
        if decision_at.tzinfo is None or decision_at.utcoffset() is None:
            raise ValueError("decision_at must be timezone-aware")
        if self.available_at > decision_at or self.member_from > decision_at:
            return False
        if self.member_until is not None and decision_at >= self.member_until:
            return False
        if self.delisted_at is not None and decision_at >= self.delisted_at:
            return False
        return True


class PKSanitizedRow(BaseModel):
    model_config = PK_MODEL_CONFIG

    symbol: str = Field(min_length=1)
    close: float = Field(gt=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol cannot be empty")
        return normalized

    @field_validator("close")
    @classmethod
    def validate_close(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("close must be finite")
        return value


class PKSanitizedFixture(BaseModel):
    model_config = PK_MODEL_CONFIG

    fixture_id: str = Field(min_length=1)
    schema_version: Literal["pk-sanitized-fixture-1"] = "pk-sanitized-fixture-1"
    scanner_key: Literal["PK_FIXTURE_CLOSE_ABOVE"] = "PK_FIXTURE_CLOSE_ABOVE"
    as_of: datetime
    threshold: float = Field(gt=0)
    rows: tuple[PKSanitizedRow, ...] = Field(min_length=1, max_length=1000)

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("threshold must be finite")
        return value

    @model_validator(mode="after")
    def require_unique_symbols(self) -> "PKSanitizedFixture":
        symbols = [row.symbol for row in self.rows]
        if len(set(symbols)) != len(symbols):
            raise ValueError("sanitized fixture symbols must be unique")
        return self

    @computed_field(return_type=str)
    @property
    def normalized_hash(self) -> str:
        payload = self.model_dump(
            mode="json", by_alias=True, exclude={"normalized_hash"}
        )
        return _hash_bytes(_canonical_bytes(payload))


class PKShadowOutput(BaseModel):
    model_config = PK_MODEL_CONFIG

    schema_version: Literal["pk-shadow-output-1"] = "pk-shadow-output-1"
    matched_symbols: tuple[str, ...]

    @field_validator("matched_symbols")
    @classmethod
    def require_sorted_unique_symbols(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted(symbol.strip().upper() for symbol in value))
        if any(not symbol for symbol in normalized):
            raise ValueError("matched symbol cannot be empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("matched symbols must be unique")
        return normalized


class ShadowObservation(BaseModel):
    model_config = PK_MODEL_CONFIG

    observation_id: str = Field(min_length=1)
    fixture_id: str = Field(min_length=1)
    observed_at: datetime
    output_hash: str
    matched_symbols: tuple[str, ...]
    authority: Literal["EXPERIMENTAL_REFERENCE"] = "EXPERIMENTAL_REFERENCE"
    voting_weight: Literal[0.0] = 0.0
    can_affect_rank: Literal[False] = False
    can_affect_state: Literal[False] = False
    can_support_confirmed: Literal[False] = False

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value

    @field_validator("output_hash")
    @classmethod
    def validate_output_hash(cls, value: str) -> str:
        return _require_hash(value, "output_hash")


class PKHarnessLimits(BaseModel):
    model_config = PK_MODEL_CONFIG

    timeout_seconds: float = Field(default=10.0, ge=0.05, le=30.0)
    max_input_bytes: int = Field(default=250_000, ge=100, le=1_000_000)
    max_output_bytes: int = Field(default=100_000, ge=100, le=1_000_000)


class PKDifferentialArtifact(BaseModel):
    model_config = PK_MODEL_CONFIG

    artifact_id: str = Field(min_length=1)
    artifact_version: Literal["offline-native-differential-artifact-1"] = (
        "offline-native-differential-artifact-1"
    )
    fixture_id: str = Field(min_length=1)
    upstream_pin: PKUpstreamPin
    manifest_id: str = Field(min_length=1)
    native_scanner: PKNativeScannerSpec
    input_raw_hash: str
    input_normalized_hash: str
    upstream_output_hash: str
    native_output_hash: str
    field_tolerances: dict[str, float]
    discrepancy_class: PKDiscrepancyClass
    discrepancy_fields: tuple[str, ...]
    reviewer_decision: PKReviewDecision = PKReviewDecision.PENDING
    reviewer_id: str | None = None
    review_note: str | None = None
    reviewed_at: datetime | None = None
    promotion_status: PKPromotionStatus = PKPromotionStatus.REGISTERED_NOT_ACTIVE
    started_at: datetime
    completed_at: datetime
    elapsed_ms: float = Field(ge=0)
    input_bytes: int = Field(ge=0)
    output_bytes: int = Field(ge=0)
    worker_invocations: Literal[1] = 1
    finite_process_terminated: Literal[True] = True
    fixture_only: bool
    upstream_observed: bool
    shadow_observation: ShadowObservation
    upstream_runtime_required: Literal[False] = False
    upstream_can_vote: Literal[False] = False

    @field_validator(
        "input_raw_hash",
        "input_normalized_hash",
        "upstream_output_hash",
        "native_output_hash",
    )
    @classmethod
    def validate_hashes(cls, value: str, info) -> str:
        return _require_hash(value, info.field_name)

    @field_validator("started_at", "completed_at", "reviewed_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("artifact timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_artifact_semantics(self) -> "PKDifferentialArtifact":
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if (
            self.discrepancy_class is PKDiscrepancyClass.MATCH
            and self.discrepancy_fields
        ):
            raise ValueError("MATCH cannot contain discrepancy fields")
        if (
            self.discrepancy_class is not PKDiscrepancyClass.MATCH
            and not self.discrepancy_fields
        ):
            raise ValueError("non-MATCH artifact needs discrepancy fields")
        if self.fixture_only == self.upstream_observed:
            raise ValueError(
                "artifact must be either fixture-only or observed upstream, never both or neither"
            )
        reviewed = self.reviewer_decision is not PKReviewDecision.PENDING
        if reviewed != bool(self.reviewer_id and self.review_note and self.reviewed_at):
            raise ValueError("review decision and review metadata must appear together")
        if (
            self.promotion_status is PKPromotionStatus.NATIVE_PROMOTION_CANDIDATE
            and self.reviewer_decision
            not in {
                PKReviewDecision.APPROVE_MATCH,
                PKReviewDecision.APPROVE_INTENDED_DIFFERENCE,
            }
        ):
            raise ValueError("promotion candidate requires an approved review")
        return self


class PKHarnessResult(BaseModel):
    model_config = PK_MODEL_CONFIG

    status: PKHarnessStatus
    artifact: PKDifferentialArtifact | None = None
    error_type: str | None = None
    error_message: str | None = None
    attempts: int = Field(ge=0, le=1)
    started_at: datetime
    completed_at: datetime
    worker_invocations: int = Field(ge=0, le=1)
    finite_process_terminated: bool
    production_affected: Literal[False] = False
    production_authorized: Literal[False] = False

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("harness timestamps must be timezone-aware")
        return value

    @computed_field(return_type=bool)
    @property
    def ok(self) -> bool:
        return self.status is PKHarnessStatus.COMPLETED

    @model_validator(mode="after")
    def validate_result_semantics(self) -> "PKHarnessResult":
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if self.attempts != self.worker_invocations:
            raise ValueError("attempts and worker invocations must match")
        if not self.finite_process_terminated:
            raise ValueError("finite worker must be terminated before returning")
        if self.status is PKHarnessStatus.COMPLETED:
            if (
                self.artifact is None
                or self.error_type
                or self.error_message
                or self.worker_invocations != 1
            ):
                raise ValueError("completed harness result needs only an artifact")
        elif self.artifact is not None or not (self.error_type and self.error_message):
            raise ValueError(
                "failed harness result needs a typed error and no artifact"
            )
        return self


class PKPromotionEvidence(BaseModel):
    model_config = PK_MODEL_CONFIG

    reviewer_id: str = Field(min_length=1)
    reviewed_at: datetime
    native_implementation_hash: str
    acceptance_test_ids: tuple[str, ...] = Field(min_length=1)
    feature_contract_id: str = Field(min_length=1)
    feature_contract_version: str = Field(min_length=1)
    evidence_family: str = Field(min_length=1)
    correlation_group: str = Field(min_length=1)
    no_upstream_runtime_dependency: Literal[True] = True

    @field_validator("reviewed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at must be timezone-aware")
        return value

    @field_validator("native_implementation_hash")
    @classmethod
    def validate_implementation_hash(cls, value: str) -> str:
        return _require_hash(value, "native_implementation_hash")

    @field_validator("acceptance_test_ids")
    @classmethod
    def validate_acceptance_tests(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(test_id.strip() for test_id in value)
        if any(not test_id for test_id in normalized) or len(set(normalized)) != len(
            normalized
        ):
            raise ValueError("acceptance test IDs must be non-empty and unique")
        return normalized


class PKPromotionRecord(BaseModel):
    model_config = PK_MODEL_CONFIG

    promotion_id: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)
    status: PKPromotionStatus
    reasons: tuple[str, ...]
    native_only: Literal[True] = True
    upstream_runtime_dependency: Literal[False] = False
    upstream_can_vote: Literal[False] = False
    reviewed_at: datetime
    feature_contract_id: str = Field(min_length=1)
    feature_contract_version: str = Field(min_length=1)
    evidence_family: str = Field(min_length=1)
    correlation_group: str = Field(min_length=1)

    @field_validator("reviewed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_promotion_semantics(self) -> "PKPromotionRecord":
        if self.status is PKPromotionStatus.NATIVE_PROMOTED and self.reasons:
            raise ValueError("promoted native feature cannot retain blocker reasons")
        if self.status is not PKPromotionStatus.NATIVE_PROMOTED and not self.reasons:
            raise ValueError("inactive or rejected promotion needs explicit reasons")
        return self


class Q5R5FixtureBatch(BaseModel):
    model_config = PK_MODEL_CONFIG

    milestone: Literal["Q5-R5"] = "Q5-R5"
    acceptance_ceiling: Literal["NO_RUNTIME_SIDECAR_OR_PRODUCTION_VOTE"] = (
        "NO_RUNTIME_SIDECAR_OR_PRODUCTION_VOTE"
    )
    fixture_only: Literal[True] = True
    production_authorized: Literal[False] = False
    executable: Literal[False] = False
    successful_match: PKHarnessResult
    unresolved_difference: PKHarnessResult
    fixture_promotion: PKPromotionRecord

    @model_validator(mode="after")
    def enforce_r5_boundary(self) -> "Q5R5FixtureBatch":
        artifacts = (
            self.successful_match.artifact,
            self.unresolved_difference.artifact,
        )
        if any(artifact is None for artifact in artifacts):
            raise ValueError("R5 fixture needs two completed differential artifacts")
        if any(
            artifact.shadow_observation.can_affect_rank
            or artifact.shadow_observation.can_affect_state
            or artifact.shadow_observation.can_support_confirmed
            for artifact in artifacts
            if artifact is not None
        ):
            raise ValueError("PK shadow observation cannot vote")
        if self.fixture_promotion.status is not PKPromotionStatus.REGISTERED_NOT_ACTIVE:
            raise ValueError("fixture-only upstream cannot be promoted")
        return self


def _failure(
    *,
    status: PKHarnessStatus,
    error_type: str,
    error_message: str,
    started_at: datetime,
    attempts: int,
    worker_invocations: int,
    finite_process_terminated: bool,
) -> PKHarnessResult:
    return PKHarnessResult(
        status=status,
        error_type=error_type,
        error_message=error_message,
        attempts=attempts,
        started_at=started_at,
        completed_at=_utc_now(),
        worker_invocations=worker_invocations,
        finite_process_terminated=finite_process_terminated,
    )


def _native_output(fixture: PKSanitizedFixture) -> PKShadowOutput:
    return PKShadowOutput(
        matched_symbols=tuple(
            sorted(row.symbol for row in fixture.rows if row.close > fixture.threshold)
        )
    )


def run_pk_offline_comparison(
    *,
    pin: PKUpstreamPin,
    manifest: PKFixtureManifest,
    native_scanner: PKNativeScannerSpec,
    fixture: PKSanitizedFixture,
    limits: PKHarnessLimits | None = None,
    native_output_override: PKShadowOutput | None = None,
    fault_mode: PKFaultMode = PKFaultMode.NONE,
) -> PKHarnessResult:
    """Run exactly one fixed local fixture worker; never a production dependency."""

    started_at = _utc_now()
    configured_limits = limits or PKHarnessLimits()
    if pin.pin_status is not PKUpstreamPinStatus.FIXTURE_ONLY_UNVERIFIED:
        return _failure(
            status=PKHarnessStatus.INPUT_REJECTED,
            error_type="UPSTREAM_ADAPTER_NOT_IMPLEMENTED",
            error_message="The current worker validates fixtures only, not upstream PKScreener.",
            started_at=started_at,
            attempts=0,
            worker_invocations=0,
            finite_process_terminated=True,
        )
    if manifest.fixture_id != fixture.fixture_id:
        return _failure(
            status=PKHarnessStatus.INPUT_REJECTED,
            error_type="FIXTURE_ID_MISMATCH",
            error_message="Manifest and sanitized fixture IDs differ.",
            started_at=started_at,
            attempts=0,
            worker_invocations=0,
            finite_process_terminated=True,
        )
    if manifest.fixture_schema_version != fixture.schema_version:
        return _failure(
            status=PKHarnessStatus.INPUT_REJECTED,
            error_type="FIXTURE_SCHEMA_MISMATCH",
            error_message="Manifest and sanitized fixture schemas differ.",
            started_at=started_at,
            attempts=0,
            worker_invocations=0,
            finite_process_terminated=True,
        )
    if manifest.fixture_hash != fixture.normalized_hash:
        return _failure(
            status=PKHarnessStatus.INPUT_REJECTED,
            error_type="FIXTURE_HASH_MISMATCH",
            error_message="Sanitized fixture hash does not match the manifest.",
            started_at=started_at,
            attempts=0,
            worker_invocations=0,
            finite_process_terminated=True,
        )

    envelope = {
        "fixture": fixture.model_dump(
            mode="json", by_alias=True, exclude_computed_fields=True
        ),
        "faultMode": fault_mode.value,
    }
    raw_input = _canonical_bytes(envelope)
    if len(raw_input) > configured_limits.max_input_bytes:
        return _failure(
            status=PKHarnessStatus.INPUT_REJECTED,
            error_type="INPUT_LIMIT_EXCEEDED",
            error_message="Sanitized fixture exceeds the configured input limit.",
            started_at=started_at,
            attempts=0,
            worker_invocations=0,
            finite_process_terminated=True,
        )

    command = (sys.executable, "-m", WORKER_MODULE)
    allowed_env = {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {
            "APPDATA",
            "LOCALAPPDATA",
            "PATH",
            "PATHEXT",
            "PROGRAMDATA",
            "PYTHONHOME",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "USERPROFILE",
            "VIRTUAL_ENV",
            "WINDIR",
        }
    }
    allowed_env["PYTHONIOENCODING"] = "utf-8"
    timer = perf_counter()
    try:
        process = subprocess.run(
            command,
            input=raw_input,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).resolve().parents[2],
            env=allowed_env,
            timeout=configured_limits.timeout_seconds,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return _failure(
            status=PKHarnessStatus.TIMED_OUT,
            error_type="WORKER_TIMEOUT",
            error_message="Finite fixture worker exceeded its time budget.",
            started_at=started_at,
            attempts=1,
            worker_invocations=1,
            finite_process_terminated=True,
        )
    elapsed_ms = (perf_counter() - timer) * 1000
    if process.returncode != 0:
        return _failure(
            status=PKHarnessStatus.PROCESS_FAILED,
            error_type="WORKER_EXIT_NONZERO",
            error_message=f"Finite fixture worker exited with code {process.returncode}.",
            started_at=started_at,
            attempts=1,
            worker_invocations=1,
            finite_process_terminated=True,
        )
    if len(process.stdout) > configured_limits.max_output_bytes:
        return _failure(
            status=PKHarnessStatus.OUTPUT_REJECTED,
            error_type="OUTPUT_LIMIT_EXCEEDED",
            error_message="Finite fixture worker exceeded its output limit.",
            started_at=started_at,
            attempts=1,
            worker_invocations=1,
            finite_process_terminated=True,
        )
    try:
        upstream_output = PKShadowOutput.model_validate_json(process.stdout)
    except ValueError:
        return _failure(
            status=PKHarnessStatus.OUTPUT_REJECTED,
            error_type="OUTPUT_SCHEMA_INVALID",
            error_message="Finite fixture worker returned invalid JSON or schema.",
            started_at=started_at,
            attempts=1,
            worker_invocations=1,
            finite_process_terminated=True,
        )

    native_output = native_output_override or _native_output(fixture)
    upstream_bytes = _canonical_bytes(upstream_output)
    native_bytes = _canonical_bytes(native_output)
    upstream_hash = _hash_bytes(upstream_bytes)
    native_hash = _hash_bytes(native_bytes)
    if upstream_output.matched_symbols == native_output.matched_symbols:
        discrepancy_class = PKDiscrepancyClass.MATCH
        discrepancy_fields: tuple[str, ...] = ()
    else:
        discrepancy_class = PKDiscrepancyClass.UNRESOLVED
        discrepancy_fields = ("matchedSymbols",)

    completed_at = _utc_now()
    artifact_key = {
        "fixture_id": fixture.fixture_id,
        "upstream_commit": pin.commit,
        "native_scanner_id": native_scanner.scanner_id,
        "native_scanner_version": native_scanner.scanner_version,
        "parameter_hash": native_scanner.parameter_hash,
        "input_normalized_hash": fixture.normalized_hash,
        "upstream_output_hash": upstream_hash,
        "native_output_hash": native_hash,
    }
    artifact_id = stable_id("pkdiff", artifact_key)
    observation = ShadowObservation(
        observation_id=stable_id(
            "pkshadow", {"artifact_id": artifact_id, "output_hash": upstream_hash}
        ),
        fixture_id=fixture.fixture_id,
        observed_at=completed_at,
        output_hash=upstream_hash,
        matched_symbols=upstream_output.matched_symbols,
    )
    artifact = PKDifferentialArtifact(
        artifact_id=artifact_id,
        fixture_id=fixture.fixture_id,
        upstream_pin=pin,
        manifest_id=manifest.manifest_id,
        native_scanner=native_scanner,
        input_raw_hash=_hash_bytes(raw_input),
        input_normalized_hash=fixture.normalized_hash,
        upstream_output_hash=upstream_hash,
        native_output_hash=native_hash,
        field_tolerances={"matchedSymbols": 0.0},
        discrepancy_class=discrepancy_class,
        discrepancy_fields=discrepancy_fields,
        started_at=started_at,
        completed_at=completed_at,
        elapsed_ms=elapsed_ms,
        input_bytes=len(raw_input),
        output_bytes=len(process.stdout),
        fixture_only=True,
        upstream_observed=False,
        shadow_observation=observation,
    )
    return PKHarnessResult(
        status=PKHarnessStatus.COMPLETED,
        artifact=artifact,
        attempts=1,
        started_at=started_at,
        completed_at=completed_at,
        worker_invocations=1,
        finite_process_terminated=True,
    )


def apply_pk_review(
    *,
    artifact: PKDifferentialArtifact,
    decision: PKReviewDecision,
    reviewer_id: str,
    review_note: str,
    reviewed_at: datetime,
) -> PKDifferentialArtifact:
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise ValueError("reviewed_at must be timezone-aware")
    if not reviewer_id.strip() or not review_note.strip():
        raise ValueError("PK differential review needs reviewer and note")
    if decision is PKReviewDecision.APPROVE_MATCH:
        if artifact.discrepancy_class is not PKDiscrepancyClass.MATCH:
            raise ValueError("only an exact MATCH can receive APPROVE_MATCH")
        status = PKPromotionStatus.NATIVE_PROMOTION_CANDIDATE
    elif decision is PKReviewDecision.APPROVE_INTENDED_DIFFERENCE:
        if artifact.discrepancy_class is PKDiscrepancyClass.MATCH:
            raise ValueError("MATCH cannot be reviewed as an intended difference")
        status = PKPromotionStatus.NATIVE_PROMOTION_CANDIDATE
    elif decision in {PKReviewDecision.REJECT_NATIVE, PKReviewDecision.REJECT_UPSTREAM}:
        status = PKPromotionStatus.REJECTED
    else:
        status = PKPromotionStatus.REGISTERED_NOT_ACTIVE
    payload = artifact.model_dump(mode="python")
    payload.update(
        {
            "reviewer_decision": decision,
            "reviewer_id": reviewer_id.strip(),
            "review_note": review_note.strip(),
            "reviewed_at": reviewed_at,
            "promotion_status": status,
        }
    )
    return PKDifferentialArtifact.model_validate(payload)


def evaluate_native_promotion(
    *,
    artifact: PKDifferentialArtifact,
    evidence: PKPromotionEvidence,
) -> PKPromotionRecord:
    reasons: list[str] = []
    if artifact.upstream_pin.pin_status is not PKUpstreamPinStatus.VERIFIED:
        reasons.append("UPSTREAM_PIN_NOT_VERIFIED")
    if not artifact.upstream_observed or artifact.fixture_only:
        reasons.append("UPSTREAM_NOT_OBSERVED")
    if artifact.promotion_status is not PKPromotionStatus.NATIVE_PROMOTION_CANDIDATE:
        reasons.append("DIFFERENTIAL_NOT_REVIEWED_FOR_PROMOTION")
    if artifact.reviewer_decision not in {
        PKReviewDecision.APPROVE_MATCH,
        PKReviewDecision.APPROVE_INTENDED_DIFFERENCE,
    }:
        reasons.append("REVIEW_NOT_APPROVED")
    if (
        evidence.native_implementation_hash
        != artifact.native_scanner.implementation_hash
    ):
        reasons.append("NATIVE_IMPLEMENTATION_HASH_MISMATCH")

    status = (
        PKPromotionStatus.NATIVE_PROMOTED
        if not reasons
        else PKPromotionStatus.REGISTERED_NOT_ACTIVE
    )
    return PKPromotionRecord(
        promotion_id=stable_id(
            "pkpromotion",
            {
                "artifact_id": artifact.artifact_id,
                "implementation_hash": evidence.native_implementation_hash,
                "reviewed_at": evidence.reviewed_at.isoformat(),
            },
        ),
        artifact_id=artifact.artifact_id,
        status=status,
        reasons=tuple(reasons),
        reviewed_at=evidence.reviewed_at,
        feature_contract_id=evidence.feature_contract_id,
        feature_contract_version=evidence.feature_contract_version,
        evidence_family=evidence.evidence_family,
        correlation_group=evidence.correlation_group,
    )




PK_R4_UPSTREAM_COMMIT = "ab4212355e2442e7c8f5430d53fa3f56ea5af3b8"
PK_R4_LICENSE_HASH = "abcd106106429213f29a4690297649c0e15853a5fee2550747308660445d2e90"
PK_R4_DEPENDENCY_HASH = "6f1f1a85c908660a017764cf109a9948ca293a6790238b445cf47f3a9221caf2"
PK_R4_DECLARED_DEPENDENCIES = (
    "advanced_ta==0.1.8",
    "TA-Lib>=0.6.0",
    "alive-progress==1.6.2",
    "click>=8.1.7",
    "Halo>=0.0.31",
    "rich>=13.9.2",
    "tabulate>=0.9.0",
    "bs4>=0.0.2",
    "lxml==4.9.4",
    "gitpython>=3.1.43",
    "gspread>=5.12.4",
    "gspread_pandas>=3.3.0",
    "joblib>=1.4.2",
    "numpy==1.26.4",
    "scipy==1.12.0",
    "scikit-learn==1.4.2",
    "pandas>=2.2.3,<2.3",
    "keras==3.6.0",
    "openpyxl>=3.1.5",
    "Pyarrow>=17.0.0",
    "xlsxwriter>=3.2.0",
    "pefile>=2023.2.7,<2024.8.26",
    "Pillow>=9.5.0",
    "PKDevTools>=0.13.20260522.361",
    "PKNSETools>=0.1.20260505.153",
    "PKBrokers>=0.1.20260505.69",
    "pyppeteer>=2.0.0",
    "pytz>=2024.2",
    "python-telegram-bot>=13.4,<20.0",
    "requests>=2.32.4",
    "requests_cache>=1.2.1",
    "requests_ratelimiter>=0.7.0",
    "pyrate_limiter>=2.10.0",
    "urllib3>=1.26.20",
    "vectorbt==0.28.1",
    "numba==0.61.2",
    "llvmlite==0.44.0",
    "coverage==7.13.0",
    "imageio==2.37.2",
    "setuptools>=78.1.1",
    "autobahn>=19.11.2",
    "cryptography>=46.0.5",
    "filelock>=3.20.3",
    "protobuf>=5.29.6",
    "pyasn1>=0.6.2",
    "tornado>=6.5.3",
    "zipp>=3.19.1",
)
PK_R4_MENU_HASH = "5060a0f002e82939206e2c2757e36e9e061a3c09417ac33f1258e77f96dcc401"
PK_R4_SCANNER_HASH = "7f69027ef9621b6bf959aa098cbf3afaE3b98b16c156e990e245da0fd86a7fd2".lower()
PK_R4_SCANNER_LABELS = (
    "Full Screening",
    "Probable Breakouts",
    "Today's Breakouts",
    "Consolidating stocks",
    "Lowest Volume in last N-days",
    "RSI screening",
    "Reversal Signals",
    "Stocks making Chart Patterns",
    "CCI outside configured range",
    "Volume gainers",
    "Closing at least 2% up since last 3 days",
    "Short term bullish Ichimoku",
    "N-Minute Price and Volume breakout",
    "Bullish RSI and MACD",
    "NR4 Daily Today",
    "52 week low breakout",
    "10 days low breakout",
    "52 week high breakout",
    "Bullish Aroon crossover",
    "MACD Histogram cross below zero",
    "Bullish for next day",
    "MF/FIIs Popular Stocks",
    "View Stock Performance",
    "Breaking out now",
    "Higher Highs Lows and Close",
    "Lower Highs and Lows",
    "Stock split bonus dividends",
    "ATR Cross",
    "Bullish Higher Opens",
    "Intraday Bid Ask Build-up",
    "ATR Trailing Stops",
    "High Momentum",
    "Intraday Breakout Breakdown setup",
    "Potential Profitable setups",
    "Bullish Anchored VWAP",
    "Perfect Short Sells Futures",
    "Probable Short Sells Futures",
    "Short Sell Candidates Volume SMA",
    "Intraday Short Sell PSAR Volume SMA",
    "IPO Lifetime First Day Bullish Break",
    "Price Action",
    "Pivot Points",
    "Super Gainers",
    "Super Losers",
    "Strong Buy Signals",
    "Strong Sell Signals",
    "All Buy Signals",
    "All Sell Signals",
    "Bullish 10-day high breakout",
    "52-week high approaching breakout",
)
PK_R4_NATIVE_MAP = {
    "X:1": ("FTR-005",),
    "X:2": ("FTR-006",),
    "X:14": ("FTR-007",),
    "X:23": ("FTR-006",),
    "X:48": ("FTR-006",),
    "X:49": ("FTR-005",),
}


def build_pk_r4_inventory() -> PKR4InventoryManifest:
    entries = []
    for index, label in enumerate(PK_R4_SCANNER_LABELS):
        scanner_id = f"X:{index}"
        feature_ids = PK_R4_NATIVE_MAP.get(scanner_id, ())
        mapped = bool(feature_ids)
        entries.append(
            PKScannerInventoryEntry(
                scanner_id=scanner_id,
                label=label,
                disposition=(
                    PKScannerDisposition.NATIVE_MAPPED
                    if mapped
                    else PKScannerDisposition.QUARANTINED
                ),
                native_feature_ids=feature_ids,
                reason=(
                    "Native concept mapping exists, but the upstream result remains "
                    "zero-vote until differential parity is reviewed."
                    if mapped
                    else "No reviewed native semantic mapping; quarantine this ID."
                ),
            )
        )
    return PKR4InventoryManifest(
        upstream_pin=PKUpstreamPin(
            repository="https://github.com/pkjmesra/PKScreener",
            commit=PK_R4_UPSTREAM_COMMIT,
            license_hash=PK_R4_LICENSE_HASH,
            isolated_environment_lock_hash=PK_R4_DEPENDENCY_HASH,
            pin_status=PKUpstreamPinStatus.VERIFIED,
        ),
        menu_source_hash=PK_R4_MENU_HASH,
        scanner_source_hash=PK_R4_SCANNER_HASH,
        dependency_lock_hash=PK_R4_DEPENDENCY_HASH,
        declared_dependencies=PK_R4_DECLARED_DEPENDENCIES,
        entries=tuple(entries),
    )


def build_pk_shadow_tag(
    *,
    scanner_id: str,
    instrument_id: str,
    symbol: str,
    identity_rows: tuple[object, ...],
    companion_scrip_code: str | None = None,
) -> PKShadowTag:
    """Map through A2 identity only; a BSE scrip code is never NSE identity."""

    inventory = build_pk_r4_inventory()
    entry = next(
        (item for item in inventory.entries if item.scanner_id == scanner_id),
        None,
    )
    if entry is None:
        return PKShadowTag(
            scanner_id=scanner_id,
            status=PKTagStatus.QUARANTINED,
            reason="UNKNOWN_UPSTREAM_SCANNER_ID",
        )
    if entry.disposition is PKScannerDisposition.QUARANTINED:
        return PKShadowTag(
            scanner_id=scanner_id,
            status=PKTagStatus.QUARANTINED,
            reason="SCANNER_ID_HAS_NO_REVIEWED_NATIVE_MAPPING",
        )

    normalized_symbol = symbol.strip().upper()
    canonical = next(
        (
            row.instrument
            for row in identity_rows
            if getattr(row, "instrument", None) is not None
            and row.instrument.instrument_id == instrument_id
            and row.instrument.symbol == normalized_symbol
        ),
        None,
    )
    if canonical is None:
        suffix = (
            "_COMPANION_SCRIP_CODE_NOT_IDENTITY"
            if companion_scrip_code
            else ""
        )
        return PKShadowTag(
            scanner_id=scanner_id,
            status=PKTagStatus.QUARANTINED,
            reason=f"A2_CANONICAL_IDENTITY_REQUIRED{suffix}",
        )
    return PKShadowTag(
        scanner_id=scanner_id,
        status=PKTagStatus.TAGGED_REFERENCE,
        instrument_id=canonical.instrument_id,
        symbol=canonical.symbol,
        native_feature_ids=entry.native_feature_ids,
        reason="A2 identity matched; tag remains experimental and zero-vote.",
    )
def _fixture_inputs() -> tuple[
    PKUpstreamPin,
    PKFixtureManifest,
    PKNativeScannerSpec,
    PKSanitizedFixture,
]:
    fixture = PKSanitizedFixture(
        fixture_id="PK-Q5-R5-FIXTURE-001",
        as_of=datetime(2026, 7, 18, 15, 30, tzinfo=timezone.utc),
        threshold=100.0,
        rows=(
            PKSanitizedRow(symbol="AAA", close=105.0),
            PKSanitizedRow(symbol="BBB", close=95.0),
            PKSanitizedRow(symbol="CCC", close=110.0),
        ),
    )
    pin = PKUpstreamPin(
        repository="fixture://pkscreener-contract-only",
        commit="0" * 40,
        license_hash=_hash_bytes(b"fixture-license-not-upstream-license"),
        isolated_environment_lock_hash=_hash_bytes(b"fixture-worker-lock-v1"),
        pin_status=PKUpstreamPinStatus.FIXTURE_ONLY_UNVERIFIED,
    )
    manifest = PKFixtureManifest(
        manifest_id="PK-MANIFEST-Q5-R5-001",
        manifest_version="1.0.0",
        fixture_id=fixture.fixture_id,
        fixture_schema_version=fixture.schema_version,
        fixture_hash=fixture.normalized_hash,
        approved_artifacts=("pk_q5_r5_fixture.json",),
    )
    native = PKNativeScannerSpec(
        scanner_id="TF-PK-FIXTURE-CLOSE-ABOVE",
        scanner_version="0.1.0",
        algorithm_id="PK_FIXTURE_CLOSE_ABOVE",
        algorithm_version="1.0.0",
        parameter_hash=_hash_bytes(b'{"threshold":100.0}'),
        implementation_hash=_hash_bytes(b"native-fixture-close-above-v1"),
    )
    return pin, manifest, native, fixture


def build_q5_r5_fixture_batch() -> Q5R5FixtureBatch:
    pin, manifest, native, fixture = _fixture_inputs()
    successful = run_pk_offline_comparison(
        pin=pin,
        manifest=manifest,
        native_scanner=native,
        fixture=fixture,
    )
    unresolved = run_pk_offline_comparison(
        pin=pin,
        manifest=manifest,
        native_scanner=native,
        fixture=fixture,
        native_output_override=PKShadowOutput(matched_symbols=("AAA",)),
    )
    for label, result in (
        ("successful match", successful),
        ("unresolved difference", unresolved),
    ):
        if result.artifact is None:
            raise RuntimeError(
                f"Q5-R5 {label} fixture failed: {result.status.value} / "
                f"{result.error_type}: {result.error_message}"
            )
    assert successful.artifact is not None
    reviewed = apply_pk_review(
        artifact=successful.artifact,
        decision=PKReviewDecision.APPROVE_MATCH,
        reviewer_id="Q5-R5-FIXTURE-REVIEWER",
        review_note="Fixture proves workflow only; it is not observed upstream parity.",
        reviewed_at=_utc_now(),
    )
    promotion = evaluate_native_promotion(
        artifact=reviewed,
        evidence=PKPromotionEvidence(
            reviewer_id="Q5-R5-FIXTURE-REVIEWER",
            reviewed_at=_utc_now(),
            native_implementation_hash=native.implementation_hash,
            acceptance_test_ids=("T-191", "T-218", "T-219", "T-220"),
            feature_contract_id="FTR-PK-FIXTURE-ONLY",
            feature_contract_version="0.0.0",
            evidence_family="EXPERIMENTAL_REFERENCE",
            correlation_group="CG_PK_FIXTURE_ONLY",
        ),
    )
    return Q5R5FixtureBatch(
        successful_match=successful,
        unresolved_difference=unresolved,
        fixture_promotion=promotion,
    )


def main() -> int:
    batch = build_q5_r5_fixture_batch()
    sys.stdout.write(batch.model_dump_json(by_alias=True, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
