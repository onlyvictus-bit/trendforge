from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from hashlib import sha256
import json
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
from pydantic.alias_generators import to_camel

from ..feature_registry import FEATURE_REGISTRY_VERSION, feature_contract_by_id
from ..indicator_engine import (
    INDICATOR_ENGINE_ID,
    INDICATOR_ENGINE_VERSION,
    IndicatorBinding,
    assess_indicator_manifest,
)
from ..source_contracts import SourceResult, SourceRole


MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    frozen=True,
)
LEGACY_DISCOVERY_SCORE_FIELDS = frozenset(
    {
        "detail_score",
        "detailScore",
        "combined_score",
        "combinedScore",
        "Combined_Score",
        "win_probability",
        "winProbability",
        "quantity",
        "qty",
        "final_qty",
        "finalQty",
        "order_qty",
        "orderQty",
        "position_size",
        "positionSize",
    }
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_STRENGTH_LABEL: Literal["Evidence strength - not win probability"] = (
    "Evidence strength - not win probability"
)


class SelectionState(StrEnum):
    WATCH = "WATCH"
    WAIT = "WAIT"
    CONFIRMED = "CONFIRMED"
    REJECT = "REJECT"


class StateCeiling(StrEnum):
    WATCH = "WATCH"
    WAIT = "WAIT"
    CONFIRMED = "CONFIRMED"


class DataMode(StrEnum):
    EOD_RESEARCH = "EOD_RESEARCH"
    PUBLIC_INTRADAY_RESEARCH = "PUBLIC_INTRADAY_RESEARCH"
    BROKER_READ_ONLY = "BROKER_READ_ONLY"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"


class EvidenceDirection(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class EvidenceFamily(StrEnum):
    TRADABILITY_AND_SAFETY = "TRADABILITY_AND_SAFETY"
    MARKET_AND_SECTOR_CONTEXT = "MARKET_AND_SECTOR_CONTEXT"
    STRUCTURE = "STRUCTURE"
    PARTICIPATION = "PARTICIPATION"
    DERIVATIVES_OI = "DERIVATIVES_OI"
    OPTIONS_CONTEXT = "OPTIONS_CONTEXT"
    EVENT_AND_SPONSOR = "EVENT_AND_SPONSOR"
    MACRO_AND_COMMODITY_CONTEXT = "MACRO_AND_COMMODITY_CONTEXT"
    SPONSOR_DELAYED_CONTEXT = "SPONSOR_DELAYED_CONTEXT"
    EXPERIMENTAL = "EXPERIMENTAL"


class GateOutcome(StrEnum):
    PASS = "PASS"
    WAIT = "WAIT"
    REJECT = "REJECT"
    UNKNOWN = "UNKNOWN"


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime, StrEnum)):
        return value.isoformat() if not isinstance(value, StrEnum) else value.value
    raise TypeError(f"Unsupported stable identity value: {type(value).__name__}")


def stable_id(prefix: str, *parts: Any) -> str:
    payload = json.dumps(
        parts,
        default=_json_default,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"{prefix}_{sha256(payload).hexdigest()[:24]}"


def _aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _sha256(value: str, field_name: str) -> str:
    normalized = value.lower()
    if SHA256_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"{field_name} must be a SHA-256 hexadecimal digest")
    return normalized


class InstrumentIdentity(BaseModel):
    model_config = MODEL_CONFIG

    instrument_id: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    segment: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    isin: str | None = None
    series: str | None = None
    contract: str | None = None
    expiry: date | None = None
    lot_size: int | None = Field(default=None, gt=0)
    tick_size: float | None = Field(default=None, gt=0)

    @field_validator("exchange", "segment", "symbol", "isin", "series", "contract")
    @classmethod
    def normalize_identity_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    @classmethod
    def create(
        cls,
        *,
        exchange: str,
        segment: str,
        symbol: str,
        isin: str | None = None,
        series: str | None = None,
        contract: str | None = None,
        expiry: date | None = None,
        lot_size: int | None = None,
        tick_size: float | None = None,
    ) -> "InstrumentIdentity":
        normalized = {
            "exchange": exchange.strip().upper(),
            "segment": segment.strip().upper(),
            "symbol": symbol.strip().upper(),
            "isin": (isin or "").strip().upper(),
            "series": (series or "").strip().upper(),
            "contract": (contract or "").strip().upper(),
            "expiry": expiry.isoformat() if expiry else "",
        }
        return cls(
            instrument_id=stable_id("ins", normalized),
            exchange=normalized["exchange"],
            segment=normalized["segment"],
            symbol=normalized["symbol"],
            isin=normalized["isin"] or None,
            series=normalized["series"] or None,
            contract=normalized["contract"] or None,
            expiry=expiry,
            lot_size=lot_size,
            tick_size=tick_size,
        )


class PointInTimeLineage(BaseModel):
    model_config = MODEL_CONFIG

    event_time: datetime
    published_at: datetime
    received_at: datetime
    available_at: datetime
    retrieved_at: datetime
    revision_id: str = Field(min_length=1)
    artifact_hash: str

    @field_validator(
        "event_time",
        "published_at",
        "received_at",
        "available_at",
        "retrieved_at",
    )
    @classmethod
    def require_timezone(cls, value: datetime, info: Any) -> datetime:
        return _aware(value, info.field_name)

    @field_validator("artifact_hash")
    @classmethod
    def validate_artifact_hash(cls, value: str) -> str:
        return _sha256(value, "artifact_hash")

    @model_validator(mode="after")
    def validate_availability_order(self) -> "PointInTimeLineage":
        if self.published_at > self.available_at:
            raise ValueError("published_at cannot be after available_at")
        if self.available_at > self.received_at:
            raise ValueError("available_at cannot be after received_at")
        if self.received_at > self.retrieved_at:
            raise ValueError("received_at cannot be after retrieved_at")
        return self

    def is_eligible_at(self, decision_at: datetime) -> bool:
        return self.available_at <= _aware(decision_at, "decision_at")


class EventIdentity(BaseModel):
    model_config = MODEL_CONFIG

    event_id: str = Field(min_length=1)
    dataset_root: str = Field(min_length=1)
    business_keys: dict[str, str]
    linked_source_fact_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_business_identity(self) -> "EventIdentity":
        if not self.business_keys:
            raise ValueError("event identity requires business_keys")
        return self

    @classmethod
    def create(
        cls,
        *,
        dataset_root: str,
        business_keys: dict[str, str],
        linked_source_fact_ids: tuple[str, ...] = (),
    ) -> "EventIdentity":
        normalized_keys = {
            key.strip(): str(value).strip()
            for key, value in business_keys.items()
            if key.strip() and str(value).strip()
        }
        return cls(
            event_id=stable_id("evt", dataset_root.strip(), normalized_keys),
            dataset_root=dataset_root.strip(),
            business_keys=normalized_keys,
            linked_source_fact_ids=tuple(sorted(set(linked_source_fact_ids))),
        )


class BarIdentity(BaseModel):
    model_config = MODEL_CONFIG

    bar_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    open_time: datetime
    close_time: datetime
    is_closed: bool
    adjustment_version: str = Field(min_length=1)
    raw_hash: str
    source_mode: DataMode

    @field_validator("open_time", "close_time")
    @classmethod
    def require_timezone(cls, value: datetime, info: Any) -> datetime:
        return _aware(value, info.field_name)

    @field_validator("raw_hash")
    @classmethod
    def validate_raw_hash(cls, value: str) -> str:
        return _sha256(value, "raw_hash")

    @model_validator(mode="after")
    def validate_bar_window(self) -> "BarIdentity":
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be after open_time")
        return self

    @classmethod
    def create(
        cls,
        *,
        instrument_id: str,
        timeframe: str,
        session_id: str,
        open_time: datetime,
        close_time: datetime,
        is_closed: bool,
        adjustment_version: str,
        raw_hash: str,
        source_mode: DataMode,
    ) -> "BarIdentity":
        return cls(
            bar_id=stable_id(
                "bar",
                instrument_id,
                timeframe,
                close_time,
                adjustment_version,
                raw_hash.lower(),
            ),
            instrument_id=instrument_id,
            timeframe=timeframe,
            session_id=session_id,
            open_time=open_time,
            close_time=close_time,
            is_closed=is_closed,
            adjustment_version=adjustment_version,
            raw_hash=raw_hash,
            source_mode=source_mode,
        )


class NormalizedFact(BaseModel):
    model_config = MODEL_CONFIG

    fact_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    dataset_root: str = Field(min_length=1)
    business_keys: dict[str, str]
    data_date: date
    lineage: PointInTimeLineage
    quality_state: Literal[
        "STRUCTURED_OK",
        "VALID_EMPTY",
        "INPUT_INCOMPLETE",
        "STALE",
        "REJECTED",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)

    def is_eligible_at(self, decision_at: datetime) -> bool:
        return self.lineage.is_eligible_at(decision_at)

    @classmethod
    def create(
        cls,
        *,
        instrument_id: str,
        source_id: str,
        dataset_root: str,
        business_keys: dict[str, str],
        data_date: date,
        lineage: PointInTimeLineage,
        quality_state: Literal[
            "STRUCTURED_OK",
            "VALID_EMPTY",
            "INPUT_INCOMPLETE",
            "STALE",
            "REJECTED",
        ],
        payload: dict[str, Any] | None = None,
    ) -> "NormalizedFact":
        normalized_keys = dict(sorted(business_keys.items()))
        return cls(
            fact_id=stable_id(
                "fact",
                dataset_root,
                normalized_keys,
                lineage.revision_id,
                lineage.artifact_hash,
            ),
            instrument_id=instrument_id,
            source_id=source_id,
            dataset_root=dataset_root,
            business_keys=normalized_keys,
            data_date=data_date,
            lineage=lineage,
            quality_state=quality_state,
            payload=payload or {},
        )


class SelectionGateResult(BaseModel):
    model_config = MODEL_CONFIG

    code: str = Field(min_length=1)
    outcome: GateOutcome
    blocks_confirmed: bool
    reason: str = Field(min_length=1)
    required: bool = True

    @model_validator(mode="after")
    def validate_blocking_semantics(self) -> "SelectionGateResult":
        must_block = self.required and self.outcome in {
            GateOutcome.WAIT,
            GateOutcome.REJECT,
            GateOutcome.UNKNOWN,
        }
        if must_block and not self.blocks_confirmed:
            raise ValueError("required WAIT/REJECT/UNKNOWN gate must block CONFIRMED")
        if self.outcome is GateOutcome.PASS and self.blocks_confirmed:
            raise ValueError("PASS gate cannot block CONFIRMED")
        return self


class EvidenceClaim(BaseModel):
    model_config = MODEL_CONFIG

    claim_id: str = Field(min_length=1)
    feature_id: str = Field(min_length=1)
    feature_version: str = Field(min_length=1)
    family: EvidenceFamily
    correlation_group: str = Field(min_length=1)
    direction: EvidenceDirection
    strength_before_caps: float = Field(ge=0, le=1)
    source_fact_ids: tuple[str, ...] = Field(min_length=1)
    authority: SourceRole
    available_at: datetime
    event_time: datetime | None = None
    published_at: datetime | None = None
    received_at: datetime | None = None
    revision_id: str | None = None
    artifact_hash: str | None = None
    valid_until: datetime | None = None
    state_ceiling: StateCeiling
    can_support_confirmed: bool = False
    explanation: str = Field(min_length=1)

    @field_validator("available_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _aware(value, "available_at")

    @model_validator(mode="after")
    def validate_confirmation_authority(self) -> "EvidenceClaim":
        contract = feature_contract_by_id(self.feature_id)
        if contract is None:
            raise ValueError(f"feature {self.feature_id} is not registered")
        if self.feature_version != contract.feature_version:
            raise ValueError(
                f"feature {self.feature_id} version does not match registry "
                f"{contract.feature_version}"
            )
        if self.family.value != contract.evidence_family:
            raise ValueError(f"feature {self.feature_id} evidence family mismatch")
        if self.correlation_group != contract.correlation_group:
            raise ValueError(f"feature {self.feature_id} correlation group mismatch")
        if (
            self.state_ceiling is StateCeiling.CONFIRMED
            and contract.state_ceiling != StateCeiling.CONFIRMED.value
        ):
            raise ValueError(f"feature {self.feature_id} cannot support CONFIRMED")
        if (
            self.can_support_confirmed
            and self.state_ceiling is not StateCeiling.CONFIRMED
        ):
            raise ValueError("confirming claim requires CONFIRMED state ceiling")
        if (
            self.authority
            in {
                SourceRole.SHADOW_UPSTREAM,
                SourceRole.EXPERIMENTAL,
                SourceRole.REFERENCE_ONLY,
                SourceRole.SECONDARY_DISCOVERY,
            }
            and self.can_support_confirmed
        ):
            raise ValueError("claim authority cannot support CONFIRMED")
        normalized_facts = tuple(sorted(set(self.source_fact_ids)))
        if normalized_facts != self.source_fact_ids:
            raise ValueError("source fact IDs must be sorted and unique")
        expected_claim_id = stable_id(
            "clm",
            self.feature_id,
            self.feature_version,
            self.family,
            self.correlation_group,
            self.direction,
            self.authority,
            self.available_at,
            normalized_facts,
        )
        if self.claim_id != expected_claim_id:
            raise ValueError("claim_id does not match the stable claim identity")
        if self.can_support_confirmed or self.state_ceiling is StateCeiling.CONFIRMED:
            missing = [
                name
                for name, value in (
                    ("event_time", self.event_time),
                    ("published_at", self.published_at),
                    ("received_at", self.received_at),
                    ("revision_id", self.revision_id),
                    ("artifact_hash", self.artifact_hash),
                )
                if value in {None, ""}
            ]
            if missing:
                raise ValueError(
                    "confirming claim requires PIT envelope fields: "
                    + ", ".join(missing)
                )
            if self.published_at and self.published_at > self.available_at:
                raise ValueError("published_at cannot be after available_at")
            if self.received_at and self.available_at > self.received_at:
                raise ValueError("available_at cannot be after received_at")
        return self

    def is_eligible_at(self, decision_at: datetime) -> bool:
        return self.available_at <= _aware(decision_at, "decision_at")

    @classmethod
    def create(
        cls,
        *,
        feature_id: str,
        feature_version: str,
        family: EvidenceFamily,
        correlation_group: str,
        direction: EvidenceDirection,
        strength_before_caps: float,
        source_fact_ids: tuple[str, ...],
        authority: SourceRole,
        available_at: datetime,
        state_ceiling: StateCeiling,
        can_support_confirmed: bool,
        explanation: str,
        event_time: datetime | None = None,
        published_at: datetime | None = None,
        received_at: datetime | None = None,
        revision_id: str | None = None,
        artifact_hash: str | None = None,
        valid_until: datetime | None = None,
    ) -> "EvidenceClaim":
        normalized_facts = tuple(sorted(set(source_fact_ids)))
        return cls(
            claim_id=stable_id(
                "clm",
                feature_id,
                feature_version,
                family,
                correlation_group,
                direction,
                authority,
                available_at,
                normalized_facts,
            ),
            feature_id=feature_id,
            feature_version=feature_version,
            family=family,
            correlation_group=correlation_group,
            direction=direction,
            strength_before_caps=strength_before_caps,
            source_fact_ids=normalized_facts,
            authority=authority,
            available_at=available_at,
            event_time=event_time,
            published_at=published_at,
            received_at=received_at,
            revision_id=revision_id,
            artifact_hash=artifact_hash,
            valid_until=valid_until,
            state_ceiling=state_ceiling,
            can_support_confirmed=can_support_confirmed,
            explanation=explanation,
        )


class SelectionCandidate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
        extra="forbid",
    )

    candidate_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    instrument: InstrumentIdentity
    market: Literal["NSE", "MCX"]
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    state: SelectionState
    state_ceiling: StateCeiling
    evidence_direction: EvidenceDirection
    discovery_reason: str = Field(min_length=1)
    family_supports: tuple[EvidenceFamily, ...] = ()
    family_opposes: tuple[EvidenceFamily, ...] = ()
    family_missing: tuple[EvidenceFamily, ...] = ()
    top_reason: str = Field(min_length=1)
    contradiction: str | None = None
    missing_proof: tuple[str, ...] = ()
    next_confirmation: str = Field(min_length=1)
    invalidation_condition: str = Field(min_length=1)
    context: str = Field(min_length=1)
    freshness: Literal["FRESH", "STALE", "MIXED", "UNKNOWN"]
    completeness: float = Field(ge=0, le=1)
    what_changed: str = Field(min_length=1)
    evidence_strength: float = Field(ge=0, le=1)
    evidence_strength_label: Literal["Evidence strength - not win probability"] = (
        EVIDENCE_STRENGTH_LABEL
    )
    gate_results: tuple[SelectionGateResult, ...] = ()
    source_ages_seconds: dict[str, int | None] = Field(default_factory=dict)
    data_mode: DataMode
    demo_only: bool = True
    executable: Literal[False] = False
    comparable_baseline: Literal["COMPARED", "NO_BASELINE"] = "NO_BASELINE"
    comparable_run_id: str | None = None
    change_kinds: tuple[str, ...] = ()

    @computed_field(return_type=tuple[str, ...])
    @property
    def gate_codes(self) -> tuple[str, ...]:
        return tuple(gate.code for gate in self.gate_results)

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_discovery_scores(cls, data: Any) -> Any:
        # CROSS-014 / FUS-008 / T-073: discovery ranks cannot enter a decision DTO.
        if isinstance(data, dict):
            forbidden = [
                key
                for key in data
                if key in LEGACY_DISCOVERY_SCORE_FIELDS
            ]
            if forbidden:
                raise ValueError(
                    "FUS-008: legacy discovery score cannot enter a decision "
                    f"contract: {', '.join(sorted(str(item) for item in forbidden))}"
                )
        return data

    @model_validator(mode="after")
    def validate_state_contract(self) -> "SelectionCandidate":
        family_sets = [
            set(self.family_supports),
            set(self.family_opposes),
            set(self.family_missing),
        ]
        if family_sets[0] & family_sets[1] or family_sets[0] & family_sets[2]:
            raise ValueError(
                "evidence families cannot be both support and oppose/missing"
            )
        if family_sets[1] & family_sets[2]:
            raise ValueError("evidence families cannot be both oppose and missing")
        if self.state is SelectionState.CONFIRMED:
            if self.state_ceiling is not StateCeiling.CONFIRMED:
                raise ValueError("CONFIRMED exceeds state ceiling")
            if self.data_mode is DataMode.SYNTHETIC_TEST or self.demo_only:
                raise ValueError("synthetic/demo candidate cannot be CONFIRMED")
        if self.state is SelectionState.REJECT and not any(
            gate.outcome is GateOutcome.REJECT for gate in self.gate_results
        ):
            raise ValueError("REJECT requires a deterministic rejecting gate")
        if self.state is SelectionState.WAIT and not any(
            gate.blocks_confirmed for gate in self.gate_results
        ):
            raise ValueError("WAIT requires a named blocking gate")
        for age in self.source_ages_seconds.values():
            if age is not None and age < 0:
                raise ValueError("source ages cannot be negative")
        return self


class SelectionScanRun(BaseModel):
    model_config = MODEL_CONFIG

    run_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    as_of: datetime
    universe_version: str = Field(min_length=1)
    data_mode: DataMode
    feature_registry_version: str = Field(
        default=FEATURE_REGISTRY_VERSION,
        min_length=1,
    )
    indicator_engine_id: str = Field(default=INDICATOR_ENGINE_ID, min_length=1)
    indicator_engine_version: str = Field(
        default=INDICATOR_ENGINE_VERSION,
        min_length=1,
    )
    eligible_count: int = Field(ge=0)
    scanned_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    unattempted_count: int = Field(ge=0)
    indicator_bindings: tuple[IndicatorBinding, ...] = ()

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _aware(value, "as_of")

    @computed_field(return_type=float)
    @property
    def completeness(self) -> float:
        if self.eligible_count == 0:
            return 0.0
        return round(self.scanned_count / self.eligible_count, 6)

    @model_validator(mode="after")
    def validate_scan_counts(self) -> "SelectionScanRun":
        accounted = (
            self.scanned_count
            + self.excluded_count
            + self.failed_count
            + self.unattempted_count
        )
        if accounted != self.eligible_count:
            raise ValueError(
                "scan counts must reconcile exactly to eligible_count "
                f"(accounted={accounted}, eligible={self.eligible_count})"
            )
        if self.feature_registry_version != FEATURE_REGISTRY_VERSION:
            raise ValueError("scan run feature registry does not match the R0 pin")
        if (
            self.indicator_engine_id != INDICATOR_ENGINE_ID
            or self.indicator_engine_version != INDICATOR_ENGINE_VERSION
        ):
            raise ValueError("scan run indicator engine does not match the R0 pin")
        if self.indicator_bindings:
            manifest = assess_indicator_manifest(self.indicator_bindings)
            if not manifest.ok:
                raise ValueError(
                    "scan run indicator manifest is invalid: "
                    + "; ".join(manifest.errors)
                )
        expected_run_id = self._stable_run_id()
        if self.run_id != expected_run_id:
            raise ValueError("run_id does not match the stable scan-run identity")
        return self

    def _stable_run_id(self) -> str:
        bindings = tuple(
            (
                binding.feature_id,
                binding.feature_version,
                binding.engine_id,
                binding.engine_version,
                binding.minimum_warmup_bars,
                binding.observation_count,
            )
            for binding in self.indicator_bindings
        )
        return stable_id(
            "run",
            self.profile_id,
            self.profile_version,
            self.as_of,
            self.universe_version,
            self.data_mode,
            self.feature_registry_version,
            self.indicator_engine_id,
            self.indicator_engine_version,
            self.eligible_count,
            self.scanned_count,
            self.excluded_count,
            self.failed_count,
            self.unattempted_count,
            bindings,
        )

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        profile_version: str,
        as_of: datetime,
        universe_version: str,
        data_mode: DataMode,
        eligible_count: int,
        feature_registry_version: str = FEATURE_REGISTRY_VERSION,
        indicator_engine_id: str = INDICATOR_ENGINE_ID,
        indicator_engine_version: str = INDICATOR_ENGINE_VERSION,
        scanned_count: int,
        excluded_count: int = 0,
        failed_count: int = 0,
        unattempted_count: int = 0,
        indicator_bindings: tuple[IndicatorBinding, ...] = (),
    ) -> "SelectionScanRun":
        binding_identity = tuple(
            (
                binding.feature_id,
                binding.feature_version,
                binding.engine_id,
                binding.engine_version,
                binding.minimum_warmup_bars,
                binding.observation_count,
            )
            for binding in indicator_bindings
        )
        return cls(
            run_id=stable_id(
                "run",
                profile_id,
                profile_version,
                as_of,
                universe_version,
                data_mode,
                feature_registry_version,
                indicator_engine_id,
                indicator_engine_version,
                eligible_count,
                scanned_count,
                excluded_count,
                failed_count,
                unattempted_count,
                binding_identity,
            ),
            profile_id=profile_id,
            profile_version=profile_version,
            as_of=as_of,
            universe_version=universe_version,
            data_mode=data_mode,
            feature_registry_version=feature_registry_version,
            indicator_engine_id=indicator_engine_id,
            indicator_engine_version=indicator_engine_version,
            eligible_count=eligible_count,
            scanned_count=scanned_count,
            excluded_count=excluded_count,
            failed_count=failed_count,
            unattempted_count=unattempted_count,
            indicator_bindings=indicator_bindings,
        )


class SelectionFixtureBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: Literal["Q5-R1"] = "Q5-R1"
    acceptance_ceiling: Literal["NO_EARLY_CONFIRMED"] = "NO_EARLY_CONFIRMED"
    public_states: tuple[SelectionState, ...] = tuple(SelectionState)
    run: SelectionScanRun
    candidates: tuple[SelectionCandidate, ...]
    source_results: tuple[SourceResult, ...]
    facts: tuple[NormalizedFact, ...]
    claims: tuple[EvidenceClaim, ...]

    @model_validator(mode="after")
    def enforce_q5_r1_ceiling(self) -> "SelectionFixtureBatch":
        if any(
            candidate.state is SelectionState.CONFIRMED for candidate in self.candidates
        ):
            raise ValueError("Q5-R1 fixtures cannot emit CONFIRMED")
        if any(candidate.run_id != self.run.run_id for candidate in self.candidates):
            raise ValueError("fixture candidates must belong to the fixture run")
        return self
