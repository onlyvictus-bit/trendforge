from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
import re
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from .parsers.source_freshness import parse_iso_date


OFFICIAL_UNLOCK_ROLES = {"OFFICIAL_GATE_SOURCE", "OFFICIAL_OR_LICENSED"}
PASSING_STRUCTURED_STATUS = "STRUCTURED_OK"


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class SourceRole(StrEnum):
    OFFICIAL_GATE = "OFFICIAL_GATE"
    OFFICIAL_DELAYED_CONTEXT = "OFFICIAL_DELAYED_CONTEXT"
    LICENSED_OR_BROKER_READ_ONLY = "LICENSED_OR_BROKER_READ_ONLY"
    UNOFFICIAL_RESEARCH_FALLBACK = "UNOFFICIAL_RESEARCH_FALLBACK"
    SECONDARY_DISCOVERY = "SECONDARY_DISCOVERY"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    SHADOW_UPSTREAM = "SHADOW_UPSTREAM"
    EXPERIMENTAL = "EXPERIMENTAL"


class SourceResultState(StrEnum):
    STRUCTURED_OK = "STRUCTURED_OK"
    VALID_EMPTY = "VALID_EMPTY"
    BLOCKED = "BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    HTTP_ERROR = "HTTP_ERROR"
    WRONG_CONTENT = "WRONG_CONTENT"
    PARTIAL = "PARTIAL"
    PARSE_FAILED = "PARSE_FAILED"
    SCHEMA_CHANGED = "SCHEMA_CHANGED"
    STALE = "STALE"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"


class SourceContract(BaseModel):
    """Versioned decision-use contract for one dataset root."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        frozen=True,
    )

    source_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    role: SourceRole
    schema_version: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    allows_valid_empty: bool = False
    empty_semantics: str | None = None
    max_age_seconds: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_empty_contract(self) -> "SourceContract":
        if self.allows_valid_empty and not self.empty_semantics:
            raise ValueError("allows_valid_empty requires explicit empty_semantics")
        return self


class SourceResult(BaseModel):
    """Typed result that never conflates valid empty data with a failure."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        frozen=True,
    )

    source_id: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)
    role: SourceRole
    state: SourceResultState
    record_count: int = Field(default=0, ge=0)
    data_date: date | None = None
    published_at: datetime | None = None
    received_at: datetime
    available_at: datetime
    retrieved_at: datetime
    schema_version: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    artifact_hash: str | None = None
    raw_path: str | None = None
    empty_semantics: str | None = None
    freshness: Literal["FRESH", "STALE", "UNKNOWN"] = "UNKNOWN"
    can_support_confirmed: bool = False
    state_ceiling: Literal["WATCH", "WAIT", "CONFIRMED"] = "WAIT"
    error_type: str | None = None
    error_message: str | None = None
    warnings: tuple[str, ...] = ()

    @computed_field(return_type=bool)
    @property
    def ok(self) -> bool:
        return self.state in {
            SourceResultState.STRUCTURED_OK,
            SourceResultState.VALID_EMPTY,
        }

    @field_validator(
        "published_at",
        "received_at",
        "available_at",
        "retrieved_at",
    )
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("point-in-time timestamps must be timezone-aware")
        return value

    @field_validator("artifact_hash")
    @classmethod
    def validate_artifact_hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.lower()
        if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
            raise ValueError("artifact_hash must be a SHA-256 hexadecimal digest")
        return normalized

    @model_validator(mode="after")
    def validate_result_semantics(self) -> "SourceResult":
        if self.available_at > self.retrieved_at:
            raise ValueError("available_at cannot be after retrieved_at")
        if self.received_at > self.retrieved_at:
            raise ValueError("received_at cannot be after retrieved_at")
        if self.published_at is not None and self.published_at > self.available_at:
            raise ValueError("published_at cannot be after available_at")

        if self.state is SourceResultState.STRUCTURED_OK:
            if self.record_count <= 0:
                raise ValueError("STRUCTURED_OK requires at least one record")
            if self.data_date is None or self.artifact_hash is None:
                raise ValueError("STRUCTURED_OK requires data_date and artifact_hash")
        elif self.state is SourceResultState.VALID_EMPTY:
            if self.record_count != 0:
                raise ValueError("VALID_EMPTY requires record_count=0")
            if self.data_date is None or self.artifact_hash is None:
                raise ValueError("VALID_EMPTY requires source date and schema proof")
            if not self.empty_semantics:
                raise ValueError("VALID_EMPTY requires explicit empty_semantics")
        elif self.can_support_confirmed:
            raise ValueError(
                "failed, stale, partial, or unattempted results cannot confirm"
            )

        if (
            self.state is SourceResultState.VALID_EMPTY
            and self.can_support_confirmed
        ):
            raise ValueError("VALID_EMPTY cannot support CONFIRMED")
        if self.state is SourceResultState.VALID_EMPTY and self.state_ceiling != "WAIT":
            raise ValueError("VALID_EMPTY requires state_ceiling=WAIT")

        allowed_role = self.role in {
            SourceRole.OFFICIAL_GATE,
            SourceRole.LICENSED_OR_BROKER_READ_ONLY,
        }
        if self.can_support_confirmed and self.state is not SourceResultState.STRUCTURED_OK:
            raise ValueError("only STRUCTURED_OK results can support CONFIRMED")
        if self.can_support_confirmed and self.freshness != "FRESH":
            raise ValueError("confirming results require explicit FRESH proof")
        if self.can_support_confirmed and not allowed_role:
            raise ValueError("source role cannot support CONFIRMED")
        if self.can_support_confirmed and self.state_ceiling != "CONFIRMED":
            raise ValueError("confirming results require state_ceiling=CONFIRMED")
        if self.state_ceiling == "CONFIRMED" and not self.can_support_confirmed:
            raise ValueError("CONFIRMED ceiling requires confirmation eligibility")
        if self.state is SourceResultState.STALE and self.freshness != "STALE":
            raise ValueError("STALE result requires freshness=STALE")
        if not self.ok and not (self.error_type or self.error_message):
            raise ValueError("non-success result requires a typed error")
        return self

    def is_available_at(self, decision_at: datetime) -> bool:
        if decision_at.tzinfo is None or decision_at.utcoffset() is None:
            raise ValueError("decision_at must be timezone-aware")
        return self.available_at <= decision_at


def source_result_from_endpoint(
    *,
    contract: SourceContract,
    endpoint_result: Any,
    data_date: date | None,
    published_at: datetime | None,
    available_at: datetime,
    schema_validated: bool,
    parser_validated: bool,
    revision_id: str,
    freshness: Literal["FRESH", "STALE", "UNKNOWN"] = "UNKNOWN",
) -> SourceResult:
    """Adapt endpoint output after parser, schema, and freshness proof."""

    endpoint_state = str(getattr(endpoint_result, "state", "BROKEN"))
    if "." in endpoint_state:
        endpoint_state = endpoint_state.rsplit(".", 1)[-1]
    record_count = int(getattr(endpoint_result, "record_count", 0) or 0)
    error_type = getattr(endpoint_result, "error_type", None)
    reason = getattr(endpoint_result, "reason", None)
    artifact_hash = getattr(endpoint_result, "content_hash", None)
    proof_complete = data_date is not None and artifact_hash is not None

    state = SourceResultState.PARTIAL
    mapped_error = error_type or "RAW_ONLY_NOT_SCANNER_READY"
    if endpoint_state == "RAW_ARCHIVED" and schema_validated and parser_validated:
        if record_count > 0 and proof_complete:
            state = SourceResultState.STRUCTURED_OK
            mapped_error = None
        elif record_count == 0 and contract.allows_valid_empty and proof_complete:
            state = SourceResultState.VALID_EMPTY
            mapped_error = None
        elif not proof_complete:
            mapped_error = "MISSING_SOURCE_DATE_OR_ARTIFACT"
        else:
            state = SourceResultState.PARSE_FAILED
            mapped_error = "UNPROVEN_EMPTY"
    elif endpoint_state == "NO_DATA_NOW":
        if (
            contract.allows_valid_empty
            and schema_validated
            and parser_validated
            and proof_complete
        ):
            state = SourceResultState.VALID_EMPTY
            mapped_error = None
        else:
            mapped_error = "UNPROVEN_EMPTY"
    elif endpoint_state == "STALE_FALLBACK":
        state = SourceResultState.STALE
        mapped_error = error_type or "STALE_FALLBACK"
    elif endpoint_state == "WRONG_CONTENT":
        state = SourceResultState.WRONG_CONTENT
        mapped_error = error_type or "WRONG_CONTENT"
    elif endpoint_state == "BROKEN":
        status_code = getattr(endpoint_result, "status_code", None)
        if error_type in {"BLOCK_PAGE", "HTTP_401", "HTTP_403"} or status_code in {
            401,
            403,
        }:
            state = SourceResultState.BLOCKED
        elif error_type == "HTTP_429" or status_code == 429:
            state = SourceResultState.RATE_LIMITED
        elif error_type == "TIMEOUT":
            state = SourceResultState.TIMEOUT
        else:
            state = SourceResultState.HTTP_ERROR
        mapped_error = error_type or "ENDPOINT_FAILURE"

    if freshness not in {"FRESH", "STALE", "UNKNOWN"}:
        raise ValueError(f"unsupported freshness proof: {freshness}")

    valid_empty_observation = state is SourceResultState.VALID_EMPTY
    if state in {
        SourceResultState.STRUCTURED_OK,
        SourceResultState.VALID_EMPTY,
    } and freshness == "STALE":
        state = SourceResultState.STALE
        mapped_error = "STALE_SOURCE"

    role_can_confirm = contract.role in {
        SourceRole.OFFICIAL_GATE,
        SourceRole.LICENSED_OR_BROKER_READ_ONLY,
    }
    can_confirm = (
        state is SourceResultState.STRUCTURED_OK
        and freshness == "FRESH"
        and role_can_confirm
    )
    fetched_at = getattr(endpoint_result, "fetched_at")
    return SourceResult(
        source_id=contract.source_id,
        contract_version=contract.version,
        role=contract.role,
        state=state,
        record_count=(0 if state is SourceResultState.VALID_EMPTY else record_count),
        data_date=data_date,
        published_at=published_at,
        received_at=fetched_at,
        available_at=available_at,
        retrieved_at=fetched_at,
        schema_version=contract.schema_version,
        parser_version=contract.parser_version,
        revision_id=revision_id,
        artifact_hash=artifact_hash,
        raw_path=getattr(endpoint_result, "raw_path", None),
        empty_semantics=(
            contract.empty_semantics if valid_empty_observation else None
        ),
        freshness=(
            "STALE"
            if state is SourceResultState.STALE
            else freshness
            if state
            in {
                SourceResultState.STRUCTURED_OK,
                SourceResultState.VALID_EMPTY,
            }
            else "UNKNOWN"
        ),
        can_support_confirmed=can_confirm,
        state_ceiling="CONFIRMED" if can_confirm else "WAIT",
        error_type=mapped_error,
        error_message=reason if mapped_error else None,
    )


@dataclass(frozen=True)
class ParserUnlockResult:
    can_pass: bool
    state: str
    reason: str


VALID_EMPTY_SOURCES = {
    "nse_asm",
    "nse_gsm",
    "nse_fno_ban",
    "nse_mwpl_ban",
    "nse_slb",
    "nse_large_deals",
    "bse_buyback_tender",
    "bse_takeover_open_offer",
    "nse_daily_buyback",
}


def normalize_parser_status(
    *,
    source_key: str,
    parser_state: str,
    data_date: str | None,
    record_count: int,
    is_fresh: bool,
) -> str:
    if parser_state == "PARSED_STRUCTURED":
        if record_count <= 0 and source_key not in VALID_EMPTY_SOURCES:
            return "PARSED_EMPTY"
        if not data_date:
            return "WAIT_SOURCE_DATE"
        if not is_fresh:
            return "STRUCTURED_STALE"
        return PASSING_STRUCTURED_STATUS
    if parser_state == "PARSED_METADATA_ONLY":
        return "PARSED_METADATA_ONLY"
    if parser_state == "WAIT_EMPTY_PARSE":
        return "PARSED_EMPTY"
    if parser_state == "WAIT_STALE_DATA":
        return "STRUCTURED_STALE"
    if parser_state == "WAIT_PARSE_ERROR":
        return "SCHEMA_MISMATCH"
    if parser_state in {
        "WAIT_SOURCE_SNAPSHOT",
        "WAIT_FETCH_REQUIRED",
        "BROKEN",
        "NO_PARSER",
    }:
        return parser_state
    if parser_state == "PARSED":
        return "PARSED_METADATA_ONLY"
    return "SCHEMA_MISMATCH"


def freshness_status_for(
    is_fresh: bool, data_date: str | None, parser_status: str
) -> str:
    if parser_status in {"BROKEN", "SCHEMA_MISMATCH"}:
        return "BROKEN"
    if not data_date:
        return "UNKNOWN"
    return "FRESH" if is_fresh else "STALE"


def parser_can_unlock_gate(
    *,
    parser_status: str,
    data_date: date | None,
    record_count: int,
    max_age_days: int,
    can_be_valid_empty: bool,
    today: date,
) -> ParserUnlockResult:
    if parser_status != PASSING_STRUCTURED_STATUS:
        return ParserUnlockResult(
            can_pass=False,
            state=parser_status,
            reason=f"Parser status is {parser_status}, not STRUCTURED_OK.",
        )
    if data_date is None:
        return ParserUnlockResult(
            can_pass=False,
            state="WAIT_SOURCE_DATE",
            reason="Structured parser did not provide a source data date.",
        )
    if record_count <= 0 and not can_be_valid_empty:
        return ParserUnlockResult(
            can_pass=False,
            state="PARSED_EMPTY",
            reason="Structured parser returned no usable records.",
        )
    stale_before = today - timedelta(days=max_age_days)
    if data_date < stale_before:
        return ParserUnlockResult(
            can_pass=False,
            state="STRUCTURED_STALE",
            reason=f"Source data date {data_date.isoformat()} is older than allowed freshness window.",
        )
    return ParserUnlockResult(
        can_pass=True,
        state="PASS",
        reason="Structured parser output is present, dated, non-stale, and valid for this source.",
    )


BLOCKING_SOURCE_STATES = {
    "WAIT_SOURCE_SNAPSHOT",
    "WAIT_FETCH_REQUIRED",
    "BROKEN",
    "NO_PARSER",
    "PARSED_METADATA_ONLY",
    "SCHEMA_MISMATCH",
    "PARSED_EMPTY",
    "STRUCTURED_STALE",
    "WAIT_SOURCE_DATE",
    "WAIT_PARSE_LATEST_SNAPSHOT",
}


def source_state_blocks_ready(source_state: str) -> bool:
    return source_state in BLOCKING_SOURCE_STATES


def can_source_unlock_ready(
    source_role: str,
    parser_status: str,
    freshness: str,
    *,
    source_activation_ready: bool = False,
    compiler_gate_permission: bool = False,
) -> bool:
    if not source_activation_ready or not compiler_gate_permission:
        return False
    if source_role not in OFFICIAL_UNLOCK_ROLES:
        return False
    if parser_status != PASSING_STRUCTURED_STATUS:
        return False
    if freshness in {"STALE", "BROKEN", "UNKNOWN"}:
        return False
    return True


def parsed_data_date(value: str | None) -> date | None:
    return parse_iso_date(value)
