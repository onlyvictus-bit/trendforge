"""R1 immutable source and stock evidence bundle built from the accepted A1-C1 run."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ..market_data_registry import (
    CadenceClass,
    MarketDataRegistry,
    MarketDataSourceContract,
    load_market_data_registry,
)
from ..market_data_service import NormalizedSourceResult
from ..market_data_store import ManifestStatus, MarketDataStore, StoredAttempt
from ..source_inventory_compiler import compile_default_inventory
from .cash_a3_discovery import CashDiscoveryBatch, CashDiscoveryRow
from .cash_c1_rank import CashRankBatch, CashRankRow
from .contracts import EvidenceDirection, SelectionState, StateCeiling, stable_id
from .store import latest_selection_payload, persist_selection_payload

SCHEMA_VERSION = "trendforge.inventory-source-bundle.v1"
PROFILE_ID = "PRF-R1-EVIDENCE"
FRESHNESS_POLICY_VERSION = "registry-cadence-v1"
MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    frozen=True,
)


class SourceUsabilityState(StrEnum):
    USABLE_CURRENT = "USABLE_CURRENT"
    VALID_EMPTY_CURRENT = "VALID_EMPTY_CURRENT"
    STALE_LAST_GOOD = "STALE_LAST_GOOD"
    FETCH_FAILED = "FETCH_FAILED"
    PARSE_FAILED = "PARSE_FAILED"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    MISSING_REQUIRED_PARAMETER = "MISSING_REQUIRED_PARAMETER"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CATALOG_ONLY = "CATALOG_ONLY"
    STALE_DATA = "STALE_DATA"


class SourceFreshnessState(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    FUTURE = "FUTURE"
    UNKNOWN = "UNKNOWN"


_CADENCE_MAX_AGE_SECONDS = {
    CadenceClass.INTRADAY: 8 * 60 * 60,
    CadenceClass.INTRADAY_EVENT: 8 * 60 * 60,
    CadenceClass.SESSION_WINDOW: 24 * 60 * 60,
    CadenceClass.DAILY_EOD: 72 * 60 * 60,
    CadenceClass.DAILY_EOD_COMMODITY: 72 * 60 * 60,
    CadenceClass.DAILY_OR_CHANGE_DETECT: 72 * 60 * 60,
    CadenceClass.WEEKLY_RELEASE: 10 * 24 * 60 * 60,
    CadenceClass.FORTNIGHTLY_RELEASE: 21 * 24 * 60 * 60,
    CadenceClass.QUARTERLY_RELEASE: 110 * 24 * 60 * 60,
    CadenceClass.EVENT_DRIVEN: 30 * 24 * 60 * 60,
    CadenceClass.EVENT_DRIVEN_SLOW: 90 * 24 * 60 * 60,
}

_SESSION_DATE_CADENCES = {
    CadenceClass.INTRADAY,
    CadenceClass.INTRADAY_EVENT,
    CadenceClass.SESSION_WINDOW,
    CadenceClass.DAILY_EOD,
    CadenceClass.DAILY_EOD_COMMODITY,
}
_CLOSED_DAY_PUBLICATION_MARKERS = (
    "continue on weekends",
    "weekends may still publish",
    "continue reduced checks on weekends",
    "continue on holidays",
)
_SESSION_PUBLICATION_MARKERS = (
    "trading day",
    "trading days",
    "exchange trading",
    "business day",
    "after close",
    "market day",
)


def _requires_expected_session(contract: MarketDataSourceContract) -> bool:
    text = " ".join(
        (
            contract.source_publication_cadence,
            contract.active_window_ist,
            contract.holiday_or_closed_rule,
        )
    ).casefold()
    if any(marker in text for marker in _CLOSED_DAY_PUBLICATION_MARKERS):
        return False
    return contract.cadence_class in _SESSION_DATE_CADENCES and any(
        marker in text for marker in _SESSION_PUBLICATION_MARKERS
    )


def _evaluate_freshness(
    contract: MarketDataSourceContract,
    *,
    data_date: date | None,
    fetched_at: datetime | None,
    trading_date: date,
    now: datetime,
    valid_empty: bool = False,
) -> tuple[SourceFreshnessState, str, int | None]:
    """Evaluate one result under its registry cadence, not a universal age rule."""
    if fetched_at is None or fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
        return SourceFreshnessState.UNKNOWN, "A timezone-aware fetch timestamp is required.", None
    observed = fetched_at.astimezone(UTC)
    age_seconds = int((now.astimezone(UTC) - observed).total_seconds())
    if age_seconds < 0:
        return SourceFreshnessState.FUTURE, "Fetch timestamp is in the future.", None
    if data_date is not None and data_date > now.date():
        return SourceFreshnessState.FUTURE, "Data date is later than the observation date.", age_seconds

    max_age = _CADENCE_MAX_AGE_SECONDS[contract.cadence_class]
    if age_seconds > max_age:
        return (
            SourceFreshnessState.STALE,
            f"Fetch proof exceeds the {contract.cadence_class.value} freshness window.",
            age_seconds,
        )

    if data_date is None:
        if valid_empty:
            return (
                SourceFreshnessState.CURRENT,
                f"Schema-valid empty response is current under {contract.cadence_class.value} fetch time.",
                age_seconds,
            )
        return SourceFreshnessState.UNKNOWN, "Populated data requires an observed data date.", age_seconds

    if _requires_expected_session(contract) and data_date != trading_date:
        return (
            SourceFreshnessState.STALE,
            f"Expected session {trading_date.isoformat()}, observed {data_date.isoformat()}.",
            age_seconds,
        )

    if contract.cadence_class is CadenceClass.WEEKLY_RELEASE and (trading_date - data_date).days > 10:
        return SourceFreshnessState.STALE, "Weekly release is older than its cadence window.", age_seconds
    if contract.cadence_class is CadenceClass.FORTNIGHTLY_RELEASE and (trading_date - data_date).days > 21:
        return SourceFreshnessState.STALE, "Fortnightly release is older than its cadence window.", age_seconds
    if contract.cadence_class is CadenceClass.QUARTERLY_RELEASE and (trading_date - data_date).days > 110:
        return SourceFreshnessState.STALE, "Quarterly release is older than its cadence window.", age_seconds

    return (
        SourceFreshnessState.CURRENT,
        f"Current under the registry {contract.cadence_class.value} publication contract.",
        age_seconds,
    )


class SourceEvidenceRecordV1(BaseModel):
    model_config = MODEL_CONFIG

    source_key: str
    canonical_source_key: str
    alias_of: str | None = None
    canonical_url: str
    normalized_source_key: str
    acquisition_owner: str
    parser_or_adapter_id: str
    validator_id: str
    cadence_class: str
    source_publication_cadence: str = ""
    etl_refresh_interval: str = ""
    active_window_ist: str = ""
    holiday_or_closed_rule: str = ""
    empty_data_rule: str = ""
    freshness_state: SourceFreshnessState = SourceFreshnessState.UNKNOWN
    freshness_reason: str = "Freshness was not evaluated."
    freshness_age_seconds: int | None = Field(default=None, ge=0)
    expected_trading_date: date | None = None
    attempt_state: str
    parser_state: str
    usability_state: SourceUsabilityState
    reason: str
    http_status: int | None = None
    fetched_at: datetime | None = None
    data_date: date | None = None
    row_count: int = Field(default=0, ge=0)
    raw_content_hash: str | None = None
    normalized_content_hash: str | None = None
    last_good_hash: str | None = None
    dataset_root_id: str | None = None
    correlation_group: str
    evidence_eligible: bool = False
    vote_eligible: bool = False
    can_unlock_ready: bool = False
    error: str | None = None


class StockEvidenceRecordV1(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    symbol: str
    instrument_id: str
    fact_id: str
    public_state: SelectionState
    state_ceiling: StateCeiling = StateCeiling.WAIT
    evidence_direction: EvidenceDirection
    research_class: str
    why_visible: str
    why_not_confirmed: tuple[str, ...]
    attempted_sources: tuple[str, ...]
    completed_sources: tuple[str, ...]
    valid_empty_sources: tuple[str, ...]
    failed_sources: tuple[str, ...]
    not_attempted_sources: tuple[str, ...]
    family_coverage: dict[str, str]
    dataset_root_ids: tuple[str, ...]
    supporting_claims: tuple[str, ...]
    opposing_claims: tuple[str, ...]
    cheap_features: dict[str, float | str | None]
    source_clock: dict[str, dict[str, str | None]]
    lineage: dict[str, str | None]
    restriction_state: str
    tradability: str = "RESEARCH_ONLY"
    completeness: float = Field(ge=0.0, le=1.0)
    entry: None = None
    target: None = None
    stop: None = None
    risk_reward: None = None

    @model_validator(mode="after")
    def r1_is_research_only(self) -> "StockEvidenceRecordV1":
        if self.public_state is SelectionState.CONFIRMED:
            raise ValueError("R1 cannot contain CONFIRMED")
        if any(value is not None for value in (self.entry, self.target, self.stop, self.risk_reward)):
            raise ValueError("R1 cannot contain trade geometry")
        return self


class InventorySourceBundleV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    freshness_policy_version: str = FRESHNESS_POLICY_VERSION
    bundle_id: str
    bundle_hash: str
    collector_run_id: str
    cash_pipeline_run_id: str
    cash_pipeline_fingerprint: str
    permission_fingerprint: str
    snapshot_bundle_id: str
    trading_date: date
    built_at: datetime
    registry_sha256: str
    source_contract_count: int = Field(ge=0)
    stock_record_count: int = Field(ge=0)
    source_activation_ready: bool = False
    gate_authorized_source_key_count: int = 0
    acceptance_ceiling: str = "WATCH_WAIT_REJECT"
    persisted: bool = False
    stage_states: dict[str, str]
    source_records: tuple[SourceEvidenceRecordV1, ...]
    stock_records: tuple[StockEvidenceRecordV1, ...]

    @model_validator(mode="after")
    def validate_fail_closed_bundle(self) -> "InventorySourceBundleV1":
        if self.source_contract_count != len(self.source_records):
            raise ValueError("source contract count does not match source records")
        if self.stock_record_count != len(self.stock_records):
            raise ValueError("stock record count does not match stock records")
        if self.source_activation_ready:
            raise ValueError("R1 source activation is not approved")
        if any(row.vote_eligible or row.can_unlock_ready for row in self.source_records):
            raise ValueError("R1 source rows cannot vote or unlock readiness")
        return self


def _error_state(error: str | None, parser_state: str) -> SourceUsabilityState:
    text = f"{error or ''} {parser_state}".casefold()
    if "parameter" in text or "missing index" in text or "missing key" in text:
        return SourceUsabilityState.MISSING_REQUIRED_PARAMETER
    if "schema" in text or "missing bse table" in text:
        return SourceUsabilityState.SCHEMA_MISMATCH
    if "parse" in text or "json" in text or "html" in text:
        return SourceUsabilityState.PARSE_FAILED
    if any(token in text for token in ("blocked", "access denied", "captcha", "403")):
        return SourceUsabilityState.BLOCKED
    return SourceUsabilityState.FETCH_FAILED


def _classify(
    result: NormalizedSourceResult | None,
    attempt: StoredAttempt | None,
    last_good: StoredAttempt | None,
    freshness_state: SourceFreshnessState,
    freshness_reason: str,
) -> tuple[SourceUsabilityState, str]:
    status = result.status if result is not None else attempt.status if attempt else None
    rows = result.normalized_row_count if result is not None else attempt.normalized_row_count if attempt else 0
    parser = result.parser_state if result is not None else "UNKNOWN"
    error = result.error if result is not None else attempt.error if attempt else None
    if status in {
        ManifestStatus.SUCCESS_NEW,
        ManifestStatus.SUCCESS_UNCHANGED,
        ManifestStatus.CACHED_CURRENT,
    }:
        if rows > 0 and parser not in {"WAIT_SCHEMA_MISMATCH", "PARSE_FAILED"}:
            if freshness_state is SourceFreshnessState.CURRENT:
                return SourceUsabilityState.USABLE_CURRENT, "Current structured non-empty records are available."
            return SourceUsabilityState.STALE_DATA, freshness_reason
        return _error_state(error or "successful transport produced no usable rows", parser), "Transport completed but usable parsed records were not proven."
    if status is ManifestStatus.VALID_EMPTY:
        if freshness_state is SourceFreshnessState.CURRENT:
            return SourceUsabilityState.VALID_EMPTY_CURRENT, "Current response is schema-valid and explicitly empty."
        return SourceUsabilityState.STALE_DATA, freshness_reason
    if status is ManifestStatus.STALE_LAST_GOOD or (status is ManifestStatus.FAILED and last_good is not None):
        return SourceUsabilityState.STALE_LAST_GOOD, "Current attempt failed; retained last-good data is stale research context only."
    if status in {ManifestStatus.WAITING_FOR_PUBLICATION, ManifestStatus.NOT_DUE_NO_DATA}:
        return SourceUsabilityState.NOT_APPLICABLE, "Source is not due or is awaiting its publication window."
    if status in {ManifestStatus.PARTIAL, ManifestStatus.FAILED, ManifestStatus.MISSED}:
        return _error_state(error, parser), "Current source attempt did not produce usable parsed data."
    if last_good is not None:
        return SourceUsabilityState.STALE_LAST_GOOD, "No current attempt is available; retained last-good data is not current."
    return SourceUsabilityState.CATALOG_ONLY, "Registered source has no observed usable attempt in this snapshot."


def _source_records(
    *,
    registry: MarketDataRegistry,
    store: MarketDataStore,
    results: Mapping[str, NormalizedSourceResult],
    trading_date: date,
    now: datetime,
) -> tuple[SourceEvidenceRecordV1, ...]:
    latest_attempts = store.latest_attempts_all()
    latest_good = store.latest_all()
    records: list[SourceEvidenceRecordV1] = []
    for contract in sorted(registry.contracts, key=lambda item: item.source_key):
        result = results.get(contract.source_key)
        attempt = latest_attempts.get(contract.source_key)
        last_good = latest_good.get(contract.source_key)
        status = result.status if result is not None else attempt.status if attempt else None
        fetched_at = result.fetched_at if result is not None else attempt.fetched_at if attempt else None
        data_date = result.data_date if result is not None else attempt.data_date if attempt else None
        freshness_state, freshness_reason, freshness_age_seconds = _evaluate_freshness(
            contract,
            data_date=data_date,
            fetched_at=fetched_at,
            trading_date=trading_date,
            now=now,
            valid_empty=status is ManifestStatus.VALID_EMPTY,
        )
        state, reason = _classify(
            result,
            attempt,
            last_good,
            freshness_state,
            freshness_reason,
        )
        alias_of = (
            contract.normalized_source_key
            if contract.normalized_source_key != contract.source_key
            else None
        )
        rows = result.normalized_row_count if result is not None else attempt.normalized_row_count if attempt else 0
        attempt_state = result.status.value if result is not None else attempt.status.value if attempt else "NOT_ATTEMPTED"
        parser_state = result.parser_state if result is not None else "UNKNOWN"
        normalized_hash = result.normalized_content_hash if result is not None else attempt.content_hash if attempt else None
        raw_hash = result.raw_content_hashes[0] if result is not None and result.raw_content_hashes else None
        root_hash = normalized_hash or (last_good.content_hash if last_good else None)
        root = stable_id("root", contract.normalized_source_key, root_hash) if root_hash else None
        eligible = state is SourceUsabilityState.USABLE_CURRENT and alias_of is None and rows > 0
        records.append(
            SourceEvidenceRecordV1(
                source_key=contract.source_key,
                canonical_source_key=contract.normalized_source_key,
                alias_of=alias_of,
                canonical_url=contract.canonical_url,
                normalized_source_key=contract.normalized_source_key,
                acquisition_owner=contract.acquisition_owner.value,
                parser_or_adapter_id=contract.parser_or_adapter_id,
                validator_id=contract.validator_id,
                cadence_class=contract.cadence_class.value,
                source_publication_cadence=contract.source_publication_cadence,
                etl_refresh_interval=contract.etl_refresh_interval,
                active_window_ist=contract.active_window_ist,
                holiday_or_closed_rule=contract.holiday_or_closed_rule,
                empty_data_rule=contract.empty_data_rule,
                freshness_state=freshness_state,
                freshness_reason=freshness_reason,
                freshness_age_seconds=freshness_age_seconds,
                expected_trading_date=trading_date,
                attempt_state=attempt_state,
                parser_state=parser_state,
                usability_state=state,
                reason=reason,
                http_status=result.http_status if result is not None else attempt.http_status if attempt else None,
                fetched_at=fetched_at,
                data_date=data_date,
                row_count=rows,
                raw_content_hash=raw_hash,
                normalized_content_hash=normalized_hash,
                last_good_hash=last_good.content_hash if last_good else None,
                dataset_root_id=root,
                correlation_group=f"ROOT:{contract.normalized_source_key}",
                evidence_eligible=eligible,
                vote_eligible=False,
                can_unlock_ready=False,
                error=result.error if result is not None else attempt.error if attempt else None,
            )
        )
    return tuple(records)


def _direction(row: CashDiscoveryRow) -> EvidenceDirection:
    direction = row.metrics.session_direction.value
    if direction == "UP":
        return EvidenceDirection.BULLISH
    if direction == "DOWN":
        return EvidenceDirection.BEARISH
    return EvidenceDirection.UNKNOWN


def _stock_records(
    *,
    collector_run_id: str,
    cash_pipeline_run_id: str,
    trading_date: date,
    discovery: CashDiscoveryBatch,
    rank: CashRankBatch,
    source_records: tuple[SourceEvidenceRecordV1, ...],
    stage_states: Mapping[str, str],
) -> tuple[StockEvidenceRecordV1, ...]:
    sources = {row.source_key: row for row in source_records}
    rank_by_symbol: dict[str, CashRankRow] = {row.symbol: row for row in rank.rows}
    applicable = tuple(
        key for key in (
            "nse_bhavcopy_eod",
            "nse_corporate_filings_actions",
            "nse_index_close_eod",
            "nse_fo_bhavcopy",
            "nse_fno_ban",
            "nse_mwpl_percentages",
        ) if key in sources
    )
    records: list[StockEvidenceRecordV1] = []
    for item in sorted(discovery.rows, key=lambda row: row.symbol):
        ranked = rank_by_symbol.get(item.symbol)
        state = ranked.public_state if ranked is not None else item.public_state
        attempted = tuple(key for key in applicable if sources[key].attempt_state != "NOT_ATTEMPTED")
        completed = tuple(key for key in applicable if sources[key].usability_state is SourceUsabilityState.USABLE_CURRENT)
        empty = tuple(key for key in applicable if sources[key].usability_state is SourceUsabilityState.VALID_EMPTY_CURRENT)
        failed = tuple(
            key for key in applicable
            if sources[key].usability_state in {
                SourceUsabilityState.FETCH_FAILED,
                SourceUsabilityState.PARSE_FAILED,
                SourceUsabilityState.SCHEMA_MISMATCH,
                SourceUsabilityState.MISSING_REQUIRED_PARAMETER,
                SourceUsabilityState.BLOCKED,
                SourceUsabilityState.STALE_LAST_GOOD,
                SourceUsabilityState.STALE_DATA,
            }
        )
        not_attempted = tuple(key for key in applicable if key not in attempted)
        roots = tuple(sorted({sources[key].dataset_root_id for key in completed if sources[key].dataset_root_id}))
        missing = ["SOURCE_ACTIVATION", "CLOSED_BAR_STRUCTURE"]
        if stage_states.get("A5") != "COMPLETED":
            missing.append("INDEX_CONTEXT")
        if stage_states.get("A6") != "COMPLETED":
            missing.append("DERIVATIVES_CONTEXT")
        missing.extend(f"SOURCE:{key}" for key in failed)
        source_clock = {
            key: {
                "attemptState": sources[key].attempt_state,
                "usabilityState": sources[key].usability_state.value,
                "dataDate": sources[key].data_date.isoformat() if sources[key].data_date else None,
                "fetchedAt": sources[key].fetched_at.isoformat() if sources[key].fetched_at else None,
                "cadenceClass": sources[key].cadence_class,
                "freshnessState": sources[key].freshness_state.value,
                "freshnessReason": sources[key].freshness_reason,
            }
            for key in applicable
        }
        metrics = item.metrics
        cheap_features: dict[str, float | str | None] = {
            "sessionDirection": metrics.session_direction.value,
            "sessionReturn": metrics.session_return,
            "returnPercentile": metrics.return_percentile,
            "volumePercentile": metrics.volume_percentile,
            "turnoverPercentile": metrics.turnover_percentile,
            "rangePercentile": metrics.range_percentile,
            "closeLocationPercentile": metrics.close_location_percentile,
        }
        completeness = len(completed) / len(applicable) if applicable else 0.0
        records.append(
            StockEvidenceRecordV1(
                candidate_id=stable_id("r1-stock", cash_pipeline_run_id, item.instrument_id),
                symbol=item.symbol,
                instrument_id=item.instrument_id,
                fact_id=item.fact_id,
                public_state=state,
                evidence_direction=_direction(item),
                research_class="BULLISH" if _direction(item) is EvidenceDirection.BULLISH else "BEARISH" if _direction(item) is EvidenceDirection.BEARISH else "NEUTRAL",
                why_visible=ranked.reason if ranked is not None else item.discovery_reason,
                why_not_confirmed=tuple(dict.fromkeys(missing)),
                attempted_sources=attempted,
                completed_sources=completed,
                valid_empty_sources=empty,
                failed_sources=failed,
                not_attempted_sources=not_attempted,
                family_coverage={
                    "CASH_SESSION_ROOT": "CURRENT" if "nse_bhavcopy_eod" in completed else "MISSING",
                    "INDEX_CONTEXT": stage_states.get("A5", "MISSING"),
                    "DERIVATIVES_CONTEXT": stage_states.get("A6", "MISSING"),
                    "RESTRICTION": "VETO" if item.banned else "CHECKED" if "nse_fno_ban" in attempted else "UNKNOWN",
                    "STRUCTURE": "MISSING_UNTIL_R5",
                },
                dataset_root_ids=roots,
                supporting_claims=ranked.support if ranked is not None else (),
                opposing_claims=ranked.opposition if ranked is not None else (),
                cheap_features=cheap_features,
                source_clock=source_clock,
                lineage={
                    "collectorRunId": collector_run_id,
                    "cashPipelineRunId": cash_pipeline_run_id,
                    "tradingDate": trading_date.isoformat(),
                    "discoveryBatchId": discovery.batch_id,
                    "rankBatchId": rank.batch_id,
                    "factId": item.fact_id,
                },
                restriction_state="REJECT" if item.banned else "ELIGIBLE_RESEARCH",
                tradability="REJECTED" if state is SelectionState.REJECT else "RESEARCH_ONLY",
                completeness=round(completeness, 6),
            )
        )
    return tuple(records)


def build_inventory_source_bundle(
    *,
    store: MarketDataStore,
    collector_run_id: str,
    cash_pipeline_run_id: str,
    cash_pipeline_fingerprint: str,
    permission_fingerprint: str,
    snapshot_bundle_id: str,
    trading_date: date,
    results: Mapping[str, NormalizedSourceResult],
    discovery: CashDiscoveryBatch,
    rank: CashRankBatch,
    stage_states: Mapping[str, str],
    registry: MarketDataRegistry | None = None,
    built_at: datetime | None = None,
) -> InventorySourceBundleV1:
    registry = registry or load_market_data_registry()
    report = compile_default_inventory()
    now = built_at or datetime.now(UTC)
    source_records = _source_records(
        registry=registry,
        store=store,
        results=results,
        trading_date=trading_date,
        now=now,
    )
    stock_records = _stock_records(
        collector_run_id=collector_run_id,
        cash_pipeline_run_id=cash_pipeline_run_id,
        trading_date=trading_date,
        discovery=discovery,
        rank=rank,
        source_records=source_records,
        stage_states=stage_states,
    )
    identity = {
        "collectorRunId": collector_run_id,
        "cashPipelineRunId": cash_pipeline_run_id,
        "cashPipelineFingerprint": cash_pipeline_fingerprint,
        "permissionFingerprint": permission_fingerprint,
        "snapshotBundleId": snapshot_bundle_id,
        "freshnessPolicyVersion": FRESHNESS_POLICY_VERSION,
        "tradingDate": trading_date.isoformat(),
        "registrySha256": registry.registry_sha256,
        "sourceRecords": [row.model_dump(mode="json", by_alias=True) for row in source_records],
        "stockRecords": [row.model_dump(mode="json", by_alias=True) for row in stock_records],
    }
    bundle_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    bundle_id = stable_id("r1-bundle", collector_run_id, cash_pipeline_fingerprint, bundle_hash)
    return InventorySourceBundleV1(
        bundle_id=bundle_id,
        bundle_hash=bundle_hash,
        collector_run_id=collector_run_id,
        cash_pipeline_run_id=cash_pipeline_run_id,
        cash_pipeline_fingerprint=cash_pipeline_fingerprint,
        permission_fingerprint=permission_fingerprint,
        snapshot_bundle_id=snapshot_bundle_id,
        trading_date=trading_date,
        built_at=now,
        registry_sha256=registry.registry_sha256,
        source_contract_count=len(source_records),
        stock_record_count=len(stock_records),
        source_activation_ready=False,
        gate_authorized_source_key_count=report.gate_authorized_source_key_count,
        stage_states=dict(stage_states),
        source_records=source_records,
        stock_records=stock_records,
    )


def persist_inventory_source_bundle(bundle: InventorySourceBundleV1) -> InventorySourceBundleV1:
    stored = bundle.model_copy(update={"persisted": True})
    payload = stored.model_dump(mode="json", by_alias=True)
    candidates = tuple(
        (
            row.candidate_id,
            row.symbol,
            row.public_state.value,
            row.model_dump(mode="json", by_alias=True),
        )
        for row in stored.stock_records
    )
    persist_selection_payload(
        run_id=stored.bundle_id,
        profile_id=PROFILE_ID,
        as_of=stored.built_at,
        payload=payload,
        candidates=candidates,
    )
    return stored


def latest_inventory_source_bundle() -> InventorySourceBundleV1 | None:
    payload = latest_selection_payload(PROFILE_ID)
    return InventorySourceBundleV1.model_validate(payload) if payload is not None else None