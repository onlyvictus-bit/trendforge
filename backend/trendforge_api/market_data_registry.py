from __future__ import annotations

import csv
import hashlib
import importlib
import re
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = ROOT_DIR / "config" / "source_refresh_registry_69.csv"
DEFAULT_HASH_PATH = ROOT_DIR / "config" / "source_refresh_registry_69.csv.sha256"
DEFAULT_PROFILES_PATH = ROOT_DIR / "config" / "source_refresh_profiles.yaml"

EXPECTED_SOURCE_COUNT = 126
PINNED_REGISTRY_SHA256 = (
    "526C2D23E8FD2EC97888B07569ADBE681E37C0C3AF5375A087229D908E91734E"
)
PINNED_PRIMARY_KEY_SET_SHA256 = (
    "B047CF81DF66FDE392476CC81F39109F42DA6FFC864B7EF802307E68BCBEEC34"
)
PROVISIONAL_EVIDENCE_STATUS = "PROVISIONAL_UNVERIFIED_NEEDS_OFFICIAL_WEB_CHECK"
SOURCE_KEY_PATTERN = re.compile(r"^[a-z0-9_]+$")
SIMPLE_INTERVAL_PATTERN = re.compile(
    r"^(?P<count>[1-9][0-9]*)\s+(?P<unit>seconds?|minutes?|hours?|days?)$",
    re.IGNORECASE,
)

REQUIRED_CSV_COLUMNS = frozenset(
    {
        "source_key",
        "canonical_url",
        "all_contract_urls",
        "proposed_cadence_class",
        "proposed_source_publication_cadence",
        "proposed_etl_refresh_interval",
        "proposed_active_window_ist",
        "proposed_holiday_or_closed_rule",
        "proposed_empty_data_rule",
        "proposed_fetch_group",
        "evidence_status",
        "official_evidence_url",
    }
)


class CadenceClass(StrEnum):
    INTRADAY = "INTRADAY"
    INTRADAY_EVENT = "INTRADAY_EVENT"
    SESSION_WINDOW = "SESSION_WINDOW"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    EVENT_DRIVEN_SLOW = "EVENT_DRIVEN_SLOW"
    DAILY_EOD = "DAILY_EOD"
    DAILY_EOD_COMMODITY = "DAILY_EOD_COMMODITY"
    DAILY_OR_CHANGE_DETECT = "DAILY_OR_CHANGE_DETECT"
    WEEKLY_RELEASE = "WEEKLY_RELEASE"
    FORTNIGHTLY_RELEASE = "FORTNIGHTLY_RELEASE"
    QUARTERLY_RELEASE = "QUARTERLY_RELEASE"


class ScheduleAuthority(StrEnum):
    PROVISIONAL = "PROVISIONAL"
    OFFICIAL_VERIFIED = "OFFICIAL_VERIFIED"


class AcquisitionOwner(StrEnum):
    ASYNC_ENDPOINT_CLIENT = "ASYNC_ENDPOINT_CLIENT"
    RESOLVER_MONITOR = "RESOLVER_MONITOR"


class FetchGroupMode(StrEnum):
    INDEPENDENT = "INDEPENDENT"
    RESPONSE_REUSE = "RESPONSE_REUSE"
    SESSION_SHARING = "SESSION_SHARING"


class StaleThresholdAuthority(StrEnum):
    UNSET = "UNSET"
    INTERNAL_ENGINEERING_POLICY = "INTERNAL_ENGINEERING_POLICY"


class CallStyle(StrEnum):
    SINGLE_RESULT = "SINGLE_RESULT"
    BATCH_RESULTS = "BATCH_RESULTS"


class CsvSourceContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_key: str
    canonical_url: str
    all_contract_urls: tuple[str, ...]
    cadence_class: CadenceClass
    source_publication_cadence: str
    etl_refresh_interval: str
    exact_interval_seconds: int | None
    active_window_ist: str
    holiday_or_closed_rule: str
    empty_data_rule: str
    fetch_group: str
    evidence_status: str
    official_evidence_url: str | None

    @field_validator("source_key")
    @classmethod
    def valid_source_key(cls, value: str) -> str:
        if not SOURCE_KEY_PATTERN.fullmatch(value):
            raise ValueError(f"invalid source_key {value!r}")
        return value

    @field_validator(
        "source_publication_cadence",
        "etl_refresh_interval",
        "active_window_ist",
        "holiday_or_closed_rule",
        "empty_data_rule",
        "fetch_group",
        "evidence_status",
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("required registry text cannot be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_urls_and_authority(self) -> "CsvSourceContract":
        parsed = urlparse(self.canonical_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(f"invalid canonical_url for {self.source_key}")
        if self.canonical_url not in self.all_contract_urls:
            raise ValueError(
                f"canonical_url must be included in all_contract_urls for {self.source_key}"
            )
        if self.evidence_status != PROVISIONAL_EVIDENCE_STATUS:
            raise ValueError(
                f"{self.source_key} schedule evidence must remain {PROVISIONAL_EVIDENCE_STATUS}"
            )
        return self


class ParameterProviderProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    provides: tuple[str, ...] = ()
    fanout: bool = False


class AdapterDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    callable_path: str = Field(alias="callable")
    call_style: CallStyle

    @field_validator("callable_path")
    @classmethod
    def valid_callable_path(cls, value: str) -> str:
        if value.count(":") != 1:
            raise ValueError("adapter callable must use module:function")
        return value


class ValidatorDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    empty_semantics: str = Field(min_length=3)


class SourceProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_key: str
    acquisition_owner: AcquisitionOwner
    endpoint_key: str | None = None
    fanout_endpoint_keys: tuple[str, ...] = ()
    normalized_source_key: str
    required_parameters: tuple[str, ...] = ()
    parameter_provider: str
    fanout_strategy: str = Field(min_length=3)
    parser_or_adapter_id: str = Field(min_length=3)
    validator_id: str = Field(min_length=3)
    fetch_group_mode: FetchGroupMode
    stale_threshold_seconds: int | None = Field(default=None, gt=0)
    stale_threshold_authority: StaleThresholdAuthority

    @field_validator("source_key", "normalized_source_key")
    @classmethod
    def valid_source_keys(cls, value: str) -> str:
        if not SOURCE_KEY_PATTERN.fullmatch(value):
            raise ValueError(f"invalid source key {value!r}")
        return value

    @model_validator(mode="after")
    def validate_stale_threshold_authority(self) -> "SourceProfile":
        if self.stale_threshold_seconds is None:
            if self.stale_threshold_authority is not StaleThresholdAuthority.UNSET:
                raise ValueError("unset stale threshold must use UNSET authority")
        elif (
            self.stale_threshold_authority
            is not StaleThresholdAuthority.INTERNAL_ENGINEERING_POLICY
        ):
            raise ValueError(
                "stale threshold is internal engineering policy, not official evidence"
            )
        return self


class RefreshProfiles(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    registry_sha256: str
    primary_key_set_sha256: str
    timezone: str
    schedule_authority: ScheduleAuthority
    activation_ready: bool
    parameter_providers: dict[str, ParameterProviderProfile]
    adapters: dict[str, AdapterDefinition]
    validators: dict[str, ValidatorDefinition]
    sources: tuple[SourceProfile, ...]

    @model_validator(mode="after")
    def provisional_profiles_are_disabled(self) -> "RefreshProfiles":
        if self.schedule_authority is ScheduleAuthority.PROVISIONAL and self.activation_ready:
            raise ValueError("provisional schedules cannot be activation-ready")
        if self.timezone != "Asia/Kolkata":
            raise ValueError("market-data registry timezone must be Asia/Kolkata")
        return self


class MarketDataSourceContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_key: str
    canonical_url: str
    all_contract_urls: tuple[str, ...]
    cadence_class: CadenceClass
    source_publication_cadence: str
    etl_refresh_interval: str
    exact_interval_seconds: int | None
    active_window_ist: str
    holiday_or_closed_rule: str
    empty_data_rule: str
    fetch_group: str
    evidence_status: str
    official_evidence_url: str | None
    schedule_authority: ScheduleAuthority
    activation_ready: bool
    acquisition_owner: AcquisitionOwner
    endpoint_key: str | None
    fanout_endpoint_keys: tuple[str, ...]
    normalized_source_key: str
    required_parameters: tuple[str, ...]
    parameter_provider: str
    provided_parameters: tuple[str, ...]
    fanout_strategy: str
    parser_or_adapter_id: str
    validator_id: str
    fetch_group_mode: FetchGroupMode
    stale_threshold_seconds: int | None
    stale_threshold_authority: StaleThresholdAuthority
    component_verified: bool


class MarketDataRegistry(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    timezone: str
    registry_sha256: str
    primary_key_set_sha256: str
    schedule_authority: ScheduleAuthority
    activation_ready: bool
    contracts: tuple[MarketDataSourceContract, ...]
    component_summary: dict[str, int]

    @property
    def by_key(self) -> dict[str, MarketDataSourceContract]:
        return {item.source_key: item for item in self.contracts}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _primary_key_hash(keys: set[str]) -> str:
    return _sha256("\n".join(sorted(keys)).encode("utf-8"))


def _exact_interval_seconds(text: str) -> int | None:
    match = SIMPLE_INTERVAL_PATTERN.fullmatch(text.strip())
    if match is None:
        return None
    count = int(match.group("count"))
    unit = match.group("unit").casefold()
    multiplier = 1
    if unit.startswith("minute"):
        multiplier = 60
    elif unit.startswith("hour"):
        multiplier = 3_600
    elif unit.startswith("day"):
        multiplier = 86_400
    return count * multiplier


def _split_urls(value: str) -> tuple[str, ...]:
    # A canonical identity may itself be a pipe-joined multi-key contract.
    # The inventory CSV separates distinct contract URLs with a spaced pipe.
    return tuple(item.strip() for item in value.split(" | ") if item.strip())


def _read_csv_contracts(path: Path) -> tuple[CsvSourceContract, ...]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or ())
        missing_columns = sorted(REQUIRED_CSV_COLUMNS - columns)
        if missing_columns:
            raise ValueError(f"registry missing required columns: {missing_columns}")
        raw_rows = list(reader)

    raw_keys = [str(row.get("source_key") or "").strip() for row in raw_rows]
    duplicates = sorted({key for key in raw_keys if raw_keys.count(key) > 1})
    if duplicates:
        raise ValueError(f"duplicate source_key values: {duplicates}")
    if len(raw_rows) != EXPECTED_SOURCE_COUNT:
        raise ValueError(
            f"registry must contain exactly {EXPECTED_SOURCE_COUNT} rows; found {len(raw_rows)}"
        )

    contracts: list[CsvSourceContract] = []
    for row in raw_rows:
        interval = str(row["proposed_etl_refresh_interval"] or "").strip()
        official_url = str(row["official_evidence_url"] or "").strip() or None
        contracts.append(
            CsvSourceContract(
                source_key=str(row["source_key"] or "").strip(),
                canonical_url=str(row["canonical_url"] or "").strip(),
                all_contract_urls=_split_urls(str(row["all_contract_urls"] or "")),
                cadence_class=str(row["proposed_cadence_class"] or "").strip(),
                source_publication_cadence=str(
                    row["proposed_source_publication_cadence"] or ""
                ).strip(),
                etl_refresh_interval=interval,
                exact_interval_seconds=_exact_interval_seconds(interval),
                active_window_ist=str(row["proposed_active_window_ist"] or "").strip(),
                holiday_or_closed_rule=str(
                    row["proposed_holiday_or_closed_rule"] or ""
                ).strip(),
                empty_data_rule=str(row["proposed_empty_data_rule"] or "").strip(),
                fetch_group=str(row["proposed_fetch_group"] or "").strip(),
                evidence_status=str(row["evidence_status"] or "").strip(),
                official_evidence_url=official_url,
            )
        )
    return tuple(contracts)


def _read_profiles(path: Path) -> RefreshProfiles:
    loaded = yaml.safe_load(path.read_bytes())
    if not isinstance(loaded, dict):
        raise ValueError(f"profiles file {path} must contain a YAML object")
    return RefreshProfiles.model_validate(loaded)


def _resolve_callable(path: str) -> Any:
    module_name, function_name = path.split(":", 1)
    module = importlib.import_module(module_name)
    value = getattr(module, function_name, None)
    if not callable(value):
        raise ValueError(f"referenced adapter callable does not exist: {path}")
    return value


def _verify_profile_components(
    profile: SourceProfile,
    profiles: RefreshProfiles,
) -> tuple[str, ...]:
    from .disclosure_intelligence import NORMALIZERS
    from .institutional_sources import (
        ENDPOINTS,
        INTRADAY_STOCK_DETAIL_ENDPOINTS,
        MARKET_ACTIVITY_ENDPOINTS,
    )
    from .live_panels import P0_SOURCE_KEYS
    from .source_monitor import SOURCE_CATALOG
    from .source_parser import STRUCTURED_PARSERS

    endpoint_key = profile.endpoint_key
    if profile.acquisition_owner is AcquisitionOwner.ASYNC_ENDPOINT_CLIENT:
        if endpoint_key is None or endpoint_key not in ENDPOINTS:
            raise ValueError(
                f"{profile.source_key} references unknown endpoint {endpoint_key}"
            )
        endpoint = ENDPOINTS[endpoint_key]
        normalized = endpoint.normalized_source_key or profile.source_key
        if normalized != profile.normalized_source_key:
            raise ValueError(
                f"{profile.source_key} normalized_source_key must be {normalized}"
            )
        endpoint_parameters = tuple(endpoint.required_parameters)
        if set(endpoint_parameters) != set(profile.required_parameters):
            raise ValueError(
                f"{profile.source_key} required parameters do not match {endpoint_key}"
            )
    else:
        catalog_keys = {item.key for item in SOURCE_CATALOG}
        if endpoint_key is not None:
            raise ValueError(
                f"{profile.source_key} resolver/monitor profile cannot define endpoint_key"
            )
        if profile.source_key not in catalog_keys:
            raise ValueError(
                f"{profile.source_key} has no source-monitor descriptor"
            )

    for fanout_key in profile.fanout_endpoint_keys:
        if fanout_key not in ENDPOINTS:
            raise ValueError(
                f"{profile.source_key} references unknown fanout endpoint {fanout_key}"
            )
        fanout_normalized = ENDPOINTS[fanout_key].normalized_source_key or profile.source_key
        if fanout_normalized != profile.normalized_source_key:
            raise ValueError(
                f"{profile.source_key} fanout endpoint {fanout_key} normalizes to {fanout_normalized}"
            )

    if profile.parameter_provider not in profiles.parameter_providers:
        raise ValueError(
            f"{profile.source_key} references unknown parameter provider {profile.parameter_provider}"
        )
    provider = profiles.parameter_providers[profile.parameter_provider]
    if not set(profile.required_parameters) <= set(provider.provides):
        raise ValueError(
            f"{profile.source_key} required parameters are not supplied by {profile.parameter_provider}"
        )
    if profile.required_parameters and profile.parameter_provider == "none":
        raise ValueError(f"{profile.source_key} required parameters need a provider")
    if profile.fanout_strategy == "ENDPOINT_BUNDLE" and len(profile.fanout_endpoint_keys) < 2:
        raise ValueError(
            f"{profile.source_key} ENDPOINT_BUNDLE requires multiple endpoint keys"
        )

    adapter_id = profile.parser_or_adapter_id
    if adapter_id.startswith("structured:"):
        parser_key = adapter_id.removeprefix("structured:")
        if parser_key not in STRUCTURED_PARSERS or not callable(STRUCTURED_PARSERS[parser_key]):
            raise ValueError(
                f"{profile.source_key} references missing structured parser {parser_key}"
            )
    else:
        definition = profiles.adapters.get(adapter_id)
        if definition is None:
            raise ValueError(
                f"{profile.source_key} references unknown adapter {adapter_id}"
            )
        _resolve_callable(definition.callable_path)
        if adapter_id == "disclosure_snapshot" and endpoint_key not in NORMALIZERS:
            raise ValueError(
                f"{profile.source_key} endpoint is not registered for disclosure normalization"
            )
        if adapter_id == "live_panel_source" and endpoint_key not in P0_SOURCE_KEYS:
            raise ValueError(
                f"{profile.source_key} endpoint is not registered for live normalization"
            )
        if adapter_id == "market_activity_snapshot" and endpoint_key not in MARKET_ACTIVITY_ENDPOINTS:
            raise ValueError(
                f"{profile.source_key} endpoint is not registered for market-activity normalization"
            )
        if adapter_id == "intraday_detail_snapshot" and not (
            endpoint_key in INTRADAY_STOCK_DETAIL_ENDPOINTS
            or profile.source_key == "nse_sector_constituents"
        ):
            raise ValueError(
                f"{profile.source_key} endpoint is not registered for intraday normalization"
            )

    if profile.validator_id not in profiles.validators:
        raise ValueError(
            f"{profile.source_key} references unknown validator {profile.validator_id}"
        )
    return provider.provides


def _compile_contracts(
    csv_contracts: tuple[CsvSourceContract, ...],
    profiles: RefreshProfiles,
) -> tuple[MarketDataSourceContract, ...]:
    csv_by_key = {item.source_key: item for item in csv_contracts}
    profile_keys = [item.source_key for item in profiles.sources]
    duplicate_profiles = sorted(
        {key for key in profile_keys if profile_keys.count(key) > 1}
    )
    if duplicate_profiles:
        raise ValueError(f"duplicate profile source_key values: {duplicate_profiles}")
    if set(profile_keys) != set(csv_by_key):
        missing = sorted(set(csv_by_key) - set(profile_keys))
        extra = sorted(set(profile_keys) - set(csv_by_key))
        raise ValueError(f"profile key set does not match registry; missing={missing}, extra={extra}")

    modes_by_group: dict[str, set[FetchGroupMode]] = {}
    compiled: list[MarketDataSourceContract] = []
    for profile in profiles.sources:
        source = csv_by_key[profile.source_key]
        provided_parameters = _verify_profile_components(profile, profiles)
        modes_by_group.setdefault(source.fetch_group, set()).add(profile.fetch_group_mode)
        compiled.append(
            MarketDataSourceContract(
                **source.model_dump(),
                schedule_authority=profiles.schedule_authority,
                activation_ready=profiles.activation_ready,
                **profile.model_dump(exclude={"source_key"}),
                provided_parameters=provided_parameters,
                component_verified=True,
            )
        )

    inconsistent_groups = {
        group: sorted(mode.value for mode in modes)
        for group, modes in modes_by_group.items()
        if len(modes) != 1
    }
    if inconsistent_groups:
        raise ValueError(f"fetch_group modes are inconsistent: {inconsistent_groups}")
    return tuple(compiled)


@lru_cache(maxsize=16)
def load_market_data_registry(
    registry_path: str | Path | None = None,
    profiles_path: str | Path | None = None,
    hash_path: str | Path | None = None,
    expected_sha256: str | None = None,
) -> MarketDataRegistry:
    csv_path = Path(registry_path or DEFAULT_REGISTRY_PATH).expanduser().resolve()
    yaml_path = Path(profiles_path or DEFAULT_PROFILES_PATH).expanduser().resolve()
    expected = (expected_sha256 or PINNED_REGISTRY_SHA256).upper()
    actual = _sha256(csv_path.read_bytes())
    if actual != expected:
        raise ValueError(f"registry SHA-256 mismatch: expected {expected}, found {actual}")

    if expected_sha256 is None:
        digest_path = Path(hash_path or DEFAULT_HASH_PATH).expanduser().resolve()
        digest_tokens = digest_path.read_text(encoding="ascii").split()
        if not digest_tokens or digest_tokens[0].upper() != PINNED_REGISTRY_SHA256:
            raise ValueError("registry .sha256 file does not contain the pinned digest")

    csv_contracts = _read_csv_contracts(csv_path)
    source_keys = {item.source_key for item in csv_contracts}
    key_hash = _primary_key_hash(source_keys)
    if key_hash != PINNED_PRIMARY_KEY_SET_SHA256:
        raise ValueError(
            f"registry primary key set mismatch: expected {PINNED_PRIMARY_KEY_SET_SHA256}, found {key_hash}"
        )

    profiles = _read_profiles(yaml_path)
    if profiles.registry_sha256.upper() != actual:
        raise ValueError("profiles registry_sha256 does not match registry bytes")
    if profiles.primary_key_set_sha256.upper() != key_hash:
        raise ValueError("profiles primary_key_set_sha256 does not match registry keys")
    if profiles.schedule_authority is not ScheduleAuthority.PROVISIONAL:
        raise ValueError("MD69-M1 schedules must remain PROVISIONAL")
    if profiles.activation_ready:
        raise ValueError("provisional schedules cannot be activation-ready")

    contracts = _compile_contracts(csv_contracts, profiles)
    count = len(contracts)
    return MarketDataRegistry(
        version=profiles.version,
        timezone=profiles.timezone,
        registry_sha256=actual,
        primary_key_set_sha256=key_hash,
        schedule_authority=profiles.schedule_authority,
        activation_ready=profiles.activation_ready,
        contracts=contracts,
        component_summary={
            "acquisition_covered": count,
            "normalization_covered": count,
            "parameter_covered": count,
            "component_verified": sum(item.component_verified for item in contracts),
        },
    )
