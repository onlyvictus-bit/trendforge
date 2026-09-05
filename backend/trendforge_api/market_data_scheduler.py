from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from .derived_market_outputs import CALCULATED_OUTPUT_KEYS, DerivedMarketOutputService
from .exchange_calendar import (
    NseSessionPhase,
    evaluate_nse_calendar,
    expected_research_session_date,
    nse_session_phase,
)
from .market_data_registry import (
    CadenceClass,
    FetchGroupMode,
    MarketDataRegistry,
    MarketDataSourceContract,
    ScheduleAuthority,
    load_market_data_registry,
)
from .market_data_service import (
    MarketDataService,
    NormalizedSourceResult,
    ParameterContext,
)
from .market_data_parameters import SavedMarketParameterProvider
from .market_data_store import (
    MANIFEST_SCHEMA_VERSION,
    ManifestEntry,
    ManifestStatus,
    MarketDataStore,
    SnapshotManifest,
)
from .selection.cash_post_commit import CashPostCommitOrchestrator


IST = ZoneInfo("Asia/Kolkata")
SNAPSHOT_SLOTS = ("0900", "0917", "1030", "1230", "1330", "1500")
EOD_START = time(15, 35)
EOD_RETRY_SECONDS = 900
SCHEDULER_MIGRATION_VERSION = "0021_market_data_69_scheduler"
LEASE_KEY = "md69-collector"
CASH_SOURCE_KEY = "nse_bhavcopy_eod"
INDEX_CLOSE_SOURCE_KEY = "nse_index_close_eod"
INDEX_CLOSE_URL = (
    "https://nsearchives.nseindia.com/content/indices/ind_close_all_01011970.csv"
)


class SchedulerState(StrEnum):
    COMPLETED = "COMPLETED"
    DISABLED = "DISABLED"
    ACTIVATION_BLOCKED = "ACTIVATION_BLOCKED"
    MARKET_CLOSED = "MARKET_CLOSED"
    MISSED = "MISSED"
    LEASE_HELD = "LEASE_HELD"
    WAITING_FOR_EOD = "WAITING_FOR_EOD"
    FAILED = "FAILED"


def scheduled_times_ist() -> list[str]:
    """Return display times from the scheduler's authoritative slot registry."""
    return [f"{slot[:2]}:{slot[2:]}" for slot in SNAPSHOT_SLOTS]


class SchedulerRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    state: SchedulerState
    trading_date: date
    slot: str
    due_count: int = Field(default=0, ge=0)
    completed_count: int = Field(default=0, ge=0)
    manifest_path: str | None = None
    reason: str


class DueDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_key: str
    due: bool
    reason: str
    schedule_authority: str


ContextProvider = Callable[[date, str, datetime], ParameterContext]
CalendarEvaluator = Callable[[datetime], dict[str, Any]]
EodDateResolver = Callable[[datetime], date | None]


class MarketDataScheduler:
    def __init__(
        self,
        *,
        registry: MarketDataRegistry,
        store: MarketDataStore,
        service: MarketDataService,
        derived_service: DerivedMarketOutputService | None = None,
        post_commit_processor: Any | None = None,
        enabled: bool = False,
        allow_provisional_for_testing: bool = False,
        calendar_evaluator: CalendarEvaluator = evaluate_nse_calendar,
        eod_date_resolver: EodDateResolver = expected_research_session_date,
        context_provider: ContextProvider | None = None,
        slot_grace_seconds: int = 180,
    ) -> None:
        if slot_grace_seconds < 0:
            raise ValueError("slot_grace_seconds cannot be negative")
        self.registry = registry
        self.store = store
        self.service = service
        self.derived_service = derived_service or DerivedMarketOutputService(store=store)
        self.post_commit_processor = post_commit_processor
        self._last_post_commit: dict[str, Any] | None = None
        self._last_derived_error: str | None = None
        self._last_calculated_output_count = 0
        self.enabled = enabled
        self.allow_provisional_for_testing = allow_provisional_for_testing
        self.calendar_evaluator = calendar_evaluator
        self.eod_date_resolver = eod_date_resolver
        self.context_provider = context_provider
        self.slot_grace_seconds = slot_grace_seconds
        self._initialize_state_schema()

    async def _dispatch_post_commit(
        self,
        *,
        collector_run_id: str,
        at: datetime,
        results: dict[str, NormalizedSourceResult],
    ) -> None:
        if self.post_commit_processor is None:
            return
        pipeline_date = self.eod_date_resolver(at)
        if pipeline_date is None:
            latest_cash = self.store.latest_for(CASH_SOURCE_KEY)
            pipeline_date = latest_cash.data_date if latest_cash is not None else None
        if pipeline_date is None:
            self._last_post_commit = {
                "state": "BLOCKED_INPUT",
                "collectorRunId": collector_run_id,
                "error": "Official NSE calendar cannot prove the expected EOD date",
                "sourceActivationReady": False,
                "canUnlockConfirmed": False,
            }
            return
        try:
            snapshot = await asyncio.to_thread(
                self.post_commit_processor.process,
                collector_run_id=collector_run_id,
                trading_date=pipeline_date,
                results=results,
            )
            self._last_post_commit = (
                snapshot.model_dump(mode="json", by_alias=True)
                if hasattr(snapshot, "model_dump")
                else dict(snapshot)
            )
        except Exception as exc:
            self._last_post_commit = {
                "state": "FAILED_STAGE",
                "collectorRunId": collector_run_id,
                "error": f"{type(exc).__name__}: {exc}",
                "sourceActivationReady": False,
                "canUnlockConfirmed": False,
            }

    def _connect(self) -> sqlite3.Connection:
        self.store.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.store.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize_state_schema(self) -> None:
        self.store.initialize_schema()
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS market_data_scheduler_leases (
                    lease_key TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    heartbeat_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS market_data_source_schedule (
                    source_key TEXT PRIMARY KEY,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    last_status TEXT,
                    last_attempt_at TEXT,
                    last_success_at TEXT,
                    last_data_date TEXT,
                    last_error TEXT,
                    eod_complete_date TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS market_data_scheduler_runs (
                    run_id TEXT PRIMARY KEY,
                    trading_date TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    state TEXT NOT NULL,
                    due_count INTEGER NOT NULL,
                    completed_count INTEGER NOT NULL,
                    manifest_path TEXT,
                    reason TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL
                );
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations(version, description, applied_at)
                VALUES (?, ?, ?)
                """,
                (
                    SCHEDULER_MIGRATION_VERSION,
                    "MD69 due state, source health, scheduler runs and singleton lease",
                    datetime.now(UTC).isoformat(),
                ),
            )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    def acquire_lease(
        self, owner_id: str, *, now: datetime, ttl_seconds: int = 120
    ) -> bool:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        instant = self._utc(now)
        expires = instant + timedelta(seconds=ttl_seconds)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM market_data_scheduler_leases WHERE lease_key = ?",
                (LEASE_KEY,),
            ).fetchone()
            if row is not None:
                current_expiry = datetime.fromisoformat(row["expires_at"])
                if row["owner_id"] != owner_id and current_expiry > instant:
                    return False
            connection.execute(
                """
                INSERT INTO market_data_scheduler_leases(
                    lease_key, owner_id, acquired_at, heartbeat_at, expires_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(lease_key) DO UPDATE SET
                    owner_id=excluded.owner_id,
                    acquired_at=excluded.acquired_at,
                    heartbeat_at=excluded.heartbeat_at,
                    expires_at=excluded.expires_at
                """,
                (
                    LEASE_KEY,
                    owner_id,
                    instant.isoformat(),
                    instant.isoformat(),
                    expires.isoformat(),
                ),
            )
        return True

    def release_lease(self, owner_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM market_data_scheduler_leases WHERE lease_key = ? AND owner_id = ?",
                (LEASE_KEY, owner_id),
            )

    @staticmethod
    def _closed_session_allowed(contract: MarketDataSourceContract) -> bool:
        text = contract.holiday_or_closed_rule.casefold()
        return any(
            marker in text
            for marker in (
                "continue on weekends/holidays",
                "change-detection even on holidays",
                "reduced cadence",
                "publisher calendar",
                "calendar-based",
                "cftc release calendar",
                "eia holiday release calendar",
                "nsdl reporting calendar",
            )
        )

    @staticmethod
    def _slot_cadences(slot: str) -> set[CadenceClass]:
        if slot in {"0917", "1030", "1230", "1330", "1500"}:
            values = {CadenceClass.INTRADAY, CadenceClass.INTRADAY_EVENT}
        else:
            values = set()
        if slot in {"0900", "0917"}:
            values.add(CadenceClass.SESSION_WINDOW)
        if slot in {"0900", "1500"}:
            values.update(
                {
                    CadenceClass.EVENT_DRIVEN,
                    CadenceClass.EVENT_DRIVEN_SLOW,
                    CadenceClass.DAILY_OR_CHANGE_DETECT,
                }
            )
        if slot == "0900":
            values.update(
                {
                    CadenceClass.WEEKLY_RELEASE,
                    CadenceClass.FORTNIGHTLY_RELEASE,
                    CadenceClass.QUARTERLY_RELEASE,
                }
            )
        return values

    def _source_state(self, source_key: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM market_data_source_schedule WHERE source_key = ?",
                (source_key,),
            ).fetchone()

    def _source_states(self) -> dict[str, sqlite3.Row]:
        with self._connect() as connection:
            return {
                row["source_key"]: row
                for row in connection.execute(
                    "SELECT * FROM market_data_source_schedule"
                ).fetchall()
            }

    def due_decisions(
        self,
        *,
        slot: str,
        at: datetime,
        calendar: dict[str, Any],
    ) -> tuple[DueDecision, ...]:
        if slot not in SNAPSHOT_SLOTS:
            raise ValueError(f"unsupported snapshot slot: {slot}")
        eligible_cadences = self._slot_cadences(slot)
        decisions: list[DueDecision] = []
        instant = self._utc(at)
        source_states = self._source_states()
        for contract in self.registry.contracts:
            if contract.cadence_class not in eligible_cadences:
                decisions.append(
                    DueDecision(
                        source_key=contract.source_key,
                        due=False,
                        reason="cadence is not due at this checkpoint",
                        schedule_authority=contract.schedule_authority.value,
                    )
                )
                continue
            if not calendar.get("isTradingDay") and not self._closed_session_allowed(contract):
                decisions.append(
                    DueDecision(
                        source_key=contract.source_key,
                        due=False,
                        reason="closed-session rule suppresses this source",
                        schedule_authority=contract.schedule_authority.value,
                    )
                )
                continue
            state = source_states.get(contract.source_key)
            if (
                state is not None
                and state["last_attempt_at"]
                and contract.exact_interval_seconds is not None
            ):
                last_attempt = datetime.fromisoformat(state["last_attempt_at"])
                elapsed = (instant - last_attempt).total_seconds()
                if elapsed < contract.exact_interval_seconds:
                    decisions.append(
                        DueDecision(
                            source_key=contract.source_key,
                            due=False,
                            reason="exact interval has not elapsed",
                            schedule_authority=contract.schedule_authority.value,
                        )
                    )
                    continue
            decisions.append(
                DueDecision(
                    source_key=contract.source_key,
                    due=True,
                    reason="due under provisional fixture policy",
                    schedule_authority=contract.schedule_authority.value,
                )
            )
        return tuple(decisions)

    def _context(self, trading_date: date, session: str, at: datetime) -> ParameterContext:
        if self.context_provider is not None:
            return self.context_provider(trading_date, session, at)
        return ParameterContext(
            trading_date=trading_date,
            market_session=session,
            now=self._utc(at),
        )

    def _index_close_contract(self) -> MarketDataSourceContract:
        cash = self.registry.by_key[CASH_SOURCE_KEY]
        return cash.model_copy(
            update={
                "source_key": INDEX_CLOSE_SOURCE_KEY,
                "canonical_url": INDEX_CLOSE_URL,
                "all_contract_urls": (INDEX_CLOSE_URL,),
                "normalized_source_key": INDEX_CLOSE_SOURCE_KEY,
                "parser_or_adapter_id": f"structured:{INDEX_CLOSE_SOURCE_KEY}",
                "fetch_group": "INDEX_CLOSE_CONTEXT_COMPANION",
                "fetch_group_mode": FetchGroupMode.INDEPENDENT,
                "cadence_class": CadenceClass.DAILY_EOD,
                "endpoint_key": None,
                "fanout_endpoint_keys": (),
            }
        )

    @staticmethod
    def _usable_latest(latest: Any) -> bool:
        return (
            latest is not None
            and latest.status
            in {ManifestStatus.SUCCESS_NEW, ManifestStatus.SUCCESS_UNCHANGED}
            and latest.data_date is not None
            and latest.normalized_row_count > 0
        )

    def _result_from_latest(self, source_key: str) -> NormalizedSourceResult | None:
        latest = self.store.latest_for(source_key)
        if not self._usable_latest(latest):
            return None
        return NormalizedSourceResult(
            source_key=source_key,
            normalized_source_key=source_key,
            status=ManifestStatus.SUCCESS_UNCHANGED,
            parser_state="PARSED_STRUCTURED",
            source_url=latest.source_url,
            http_status=latest.http_status,
            fetched_at=latest.fetched_at,
            data_date=latest.data_date,
            normalized_row_count=latest.normalized_row_count,
            normalized_content_hash=latest.content_hash,
            stored_attempt_id=latest.attempt_id,
        )

    def _attempt_cooling_down(self, source_key: str, *, at: datetime) -> bool:
        state = self._source_state(source_key)
        if state is None or not state["last_attempt_at"]:
            return False
        last_attempt = datetime.fromisoformat(state["last_attempt_at"])
        return (self._utc(at) - last_attempt).total_seconds() < EOD_RETRY_SECONDS

    async def reconcile_research_session(self, *, at: datetime) -> SchedulerRunResult:
        """Fetch official cash+index for the closed session R5 can use now.

        OPEN/PRE_OPEN: last trading day. EOD_WINDOW: today. Holiday: last
        trading day, never relabelled as calendar today. Index close is a
        companion artifact, not a 123rd voter.
        """
        instant = self._utc(at)
        local = instant.astimezone(IST)
        calendar = self.calendar_evaluator(instant)
        phase = nse_session_phase(instant, calendar=calendar)
        research_date = self.eod_date_resolver(instant)
        slot = f"reconcile-{phase.value}"
        if research_date is None:
            latest_cash = self.store.latest_for(CASH_SOURCE_KEY)
            research_date = latest_cash.data_date if latest_cash is not None else local.date()
        session = (
            "MARKET_CLOSED"
            if phase is NseSessionPhase.CLOSED_NON_TRADING
            else "OPEN"
            if phase is NseSessionPhase.OPEN
            else phase.value
        )
        if not self.enabled:
            return self._blocked_result(
                state=SchedulerState.DISABLED,
                trading_date=research_date,
                slot=slot,
                at=instant,
                reason="MARKET_DATA_69_ENABLED is disabled",
            )
        if (
            self.registry.schedule_authority is ScheduleAuthority.PROVISIONAL
            and not self.allow_provisional_for_testing
        ):
            return self._blocked_result(
                state=SchedulerState.ACTIVATION_BLOCKED,
                trading_date=research_date,
                slot=slot,
                at=instant,
                reason="provisional schedules cannot activate production collection",
            )
        cash_latest = self.store.latest_for(CASH_SOURCE_KEY)
        cash_current = (
            self._usable_latest(cash_latest) and cash_latest.data_date == research_date
        )
        cash_date = cash_latest.data_date if cash_current else research_date
        index_latest = self.store.latest_for(INDEX_CLOSE_SOURCE_KEY)
        index_current = (
            self._usable_latest(index_latest) and index_latest.data_date == cash_date
        )
        need_cash = not cash_current and not self._attempt_cooling_down(
            CASH_SOURCE_KEY, at=instant
        )
        need_index = not index_current and not self._attempt_cooling_down(
            INDEX_CLOSE_SOURCE_KEY, at=instant
        )
        if not need_cash and not need_index:
            if hasattr(self.service, "transport"):
                from .selection.cash_a4_history import ensure_official_raw_history

                history_stats = await asyncio.to_thread(
                    ensure_official_raw_history, through=research_date
                )
                if history_stats.get("days_saved"):
                    from .selection.r14_live import (
                        build_r14_ca_join,
                        persist_r14_ca_join,
                    )
                    from .selection.r5_live import (
                        build_r5_structure_batch,
                        persist_r5_structure_batch,
                    )

                    def _refresh_structure_after_backfill() -> None:
                        try:
                            join = persist_r14_ca_join(build_r14_ca_join())
                            persist_r5_structure_batch(
                                build_r5_structure_batch(ca_join=join)
                            )
                        except ValueError:
                            # WAIT_*: lineage not ready; the post-commit pipeline
                            # owns the full rebuild and GETs stay 503, not stale.
                            return

                    await asyncio.to_thread(_refresh_structure_after_backfill)
            synthetic: dict[str, NormalizedSourceResult] = {}
            cash_result = self._result_from_latest(CASH_SOURCE_KEY)
            index_result = self._result_from_latest(INDEX_CLOSE_SOURCE_KEY)
            if cash_result is not None:
                synthetic[CASH_SOURCE_KEY] = cash_result
            if index_result is not None:
                synthetic[INDEX_CLOSE_SOURCE_KEY] = index_result
            if synthetic:
                await self._dispatch_post_commit(
                    collector_run_id=f"reconcile-{research_date.isoformat()}",
                    at=instant,
                    results=synthetic,
                )
            return SchedulerRunResult(
                run_id=f"{research_date.isoformat()}-{slot}-current",
                state=(
                    SchedulerState.MARKET_CLOSED
                    if phase is NseSessionPhase.CLOSED_NON_TRADING
                    else SchedulerState.COMPLETED
                ),
                trading_date=research_date,
                slot=slot,
                reason=f"{phase.value}: last-good closed session is already current",
            )
        owner = uuid.uuid4().hex
        if not self.acquire_lease(owner, now=instant):
            return SchedulerRunResult(
                run_id=f"lease-held-{uuid.uuid4().hex[:12]}",
                state=SchedulerState.LEASE_HELD,
                trading_date=research_date,
                slot=slot,
                reason="another collector owns the SQLite lease",
            )
        try:
            contracts: list[MarketDataSourceContract] = []
            if need_cash:
                contracts.append(self.registry.by_key[CASH_SOURCE_KEY])
            if need_index:
                contracts.append(self._index_close_contract())
            run_id = f"{research_date.isoformat()}-{slot}-{uuid.uuid4().hex[:12]}"
            results = await self._run_contracts(
                tuple(contracts),
                trading_date=research_date,
                session=session,
                at=instant,
                run_id=run_id,
                slot=slot,
            )
            adjusted: dict[str, NormalizedSourceResult] = {}
            for key, result in results.items():
                if (
                    result.status
                    in {ManifestStatus.SUCCESS_NEW, ManifestStatus.SUCCESS_UNCHANGED}
                    and result.data_date != research_date
                ):
                    result = result.model_copy(
                        update={
                            "status": ManifestStatus.WAITING_FOR_PUBLICATION,
                            "error": "artifact does not yet carry the research session date",
                        }
                    )
                adjusted[key] = result
            self._record_health(
                adjusted, at=instant, eod=True, trading_date=research_date
            )
            success_states = {
                ManifestStatus.SUCCESS_NEW,
                ManifestStatus.SUCCESS_UNCHANGED,
            }
            cash_result = adjusted.get(CASH_SOURCE_KEY)
            if cash_result is None or cash_result.status not in success_states:
                cash_result = self._result_from_latest(CASH_SOURCE_KEY)
            index_result = adjusted.get(INDEX_CLOSE_SOURCE_KEY)
            if index_result is None or index_result.status not in success_states:
                index_result = self._result_from_latest(INDEX_CLOSE_SOURCE_KEY)
            dispatch: dict[str, NormalizedSourceResult] = {}
            if cash_result is not None:
                dispatch[CASH_SOURCE_KEY] = cash_result
            if index_result is not None:
                dispatch[INDEX_CLOSE_SOURCE_KEY] = index_result
            path = self._write_manifest(
                run_id=run_id,
                trading_date=research_date,
                slot=slot,
                at=instant,
                results=adjusted,
            )
            if hasattr(self.service, "transport"):
                from .selection.cash_a4_history import ensure_official_raw_history

                await asyncio.to_thread(
                    ensure_official_raw_history, through=research_date
                )
            if dispatch:
                await self._dispatch_post_commit(
                    collector_run_id=run_id,
                    at=instant,
                    results=dispatch,
                )
            completed = sum(
                item.data_date == research_date
                and item.status
                in {ManifestStatus.SUCCESS_NEW, ManifestStatus.SUCCESS_UNCHANGED}
                for item in adjusted.values()
            )
            result = SchedulerRunResult(
                run_id=run_id,
                state=(
                    SchedulerState.MARKET_CLOSED
                    if phase is NseSessionPhase.CLOSED_NON_TRADING
                    else SchedulerState.COMPLETED
                ),
                trading_date=research_date,
                slot=slot,
                due_count=len(contracts),
                completed_count=completed,
                manifest_path=path,
                reason=(
                    f"{phase.value}: official cash/index reconcile for "
                    f"{research_date.isoformat()} (not a 123-job vote)"
                ),
            )
            self._save_run(result, started_at=instant)
            return result
        finally:
            self.release_lease(owner)

    async def _run_contracts(
        self,
        contracts: tuple[MarketDataSourceContract, ...],
        *,
        trading_date: date,
        session: str,
        at: datetime,
        run_id: str,
        slot: str,
    ) -> dict[str, NormalizedSourceResult]:
        """Run base feeds first, then rebuild saved-data fan-out inputs.

        Each phase still uses MarketDataService's bounded concurrency and
        per-source failure isolation. This only establishes dependency order.
        """
        if not contracts:
            return {}
        independent_providers = {"none", "calendar_date_window", "trading_date_window"}
        base = tuple(
            item for item in contracts if item.parameter_provider in independent_providers
        )
        dependent = tuple(
            item for item in contracts if item.parameter_provider not in independent_providers
        )
        results: dict[str, NormalizedSourceResult] = {}
        if base:
            results.update(
                await self.service.run_sources(
                    base,
                    context=self._context(trading_date, session, at),
                    run_id=run_id,
                    slot=slot,
                )
            )
        if dependent:
            results.update(
                await self.service.run_sources(
                    dependent,
                    context=self._context(trading_date, session, at),
                    run_id=run_id,
                    slot=slot,
                )
            )
        try:
            calculated = self.derived_service.materialize(
                run_id=run_id,
                at=at,
                trading_date=trading_date,
                slot=slot,
            )
            self._last_calculated_output_count = len(calculated)
            self._last_derived_error = None
        except Exception as exc:
            # Calculations are informational and must never stop source
            # acquisition, last-good preservation, or manifest production.
            self._last_calculated_output_count = 0
            self._last_derived_error = f"{type(exc).__name__}: {exc}"
        return results

    def _manifest_entry(
        self,
        contract: MarketDataSourceContract,
        result: NormalizedSourceResult | None,
        *,
        latest: Any = None,
        fallback_status: ManifestStatus = ManifestStatus.NOT_DUE_NO_DATA,
        fallback_error: str | None = None,
        now: datetime,
    ) -> ManifestEntry:
        if result is None:
            if latest is None:
                return ManifestEntry(
                    source_key=contract.source_key,
                    status=fallback_status,
                    error=fallback_error,
                    retry_count=0,
                )
            age = max(0, int((self._utc(now) - (latest.fetched_at or latest.attempted_at)).total_seconds()))
            return ManifestEntry(
                source_key=contract.source_key,
                status=ManifestStatus.CACHED_CURRENT,
                attempted_at=latest.attempted_at,
                source_url=latest.source_url,
                http_status=latest.http_status,
                media_type=latest.media_type,
                content_hash=latest.content_hash,
                object_path=latest.object_path,
                data_date=latest.data_date,
                fetched_at=latest.fetched_at,
                normalized_row_count=latest.normalized_row_count,
                last_good_hash=latest.content_hash,
                last_good_path=latest.object_path,
                age_seconds=age,
                is_stale=False,
                retry_count=latest.retry_count,
            )
        if result.status in {
            ManifestStatus.SUCCESS_NEW,
            ManifestStatus.SUCCESS_UNCHANGED,
        } and latest is not None:
            return ManifestEntry(
                source_key=contract.source_key,
                status=result.status,
                attempted_at=now,
                source_url=result.source_url,
                http_status=result.http_status,
                media_type="application/vnd.trendforge.normalized+json",
                content_hash=latest.content_hash,
                object_path=latest.object_path,
                data_date=result.data_date,
                fetched_at=result.fetched_at,
                normalized_row_count=result.normalized_row_count,
                last_good_hash=latest.content_hash,
                last_good_path=latest.object_path,
                retry_count=result.retry_count,
            )
        status = (
            ManifestStatus.STALE_LAST_GOOD
            if latest is not None and result.status is ManifestStatus.FAILED
            else result.status
        )
        use_last_good = latest is not None and status is ManifestStatus.STALE_LAST_GOOD
        return ManifestEntry(
            source_key=contract.source_key,
            status=status,
            attempted_at=now,
            source_url=latest.source_url if use_last_good else result.source_url,
            http_status=latest.http_status if use_last_good else result.http_status,
            media_type=latest.media_type if use_last_good else None,
            content_hash=latest.content_hash if use_last_good else None,
            object_path=latest.object_path if use_last_good else None,
            data_date=latest.data_date if use_last_good else result.data_date,
            fetched_at=latest.fetched_at if use_last_good else result.fetched_at,
            normalized_row_count=(
                latest.normalized_row_count
                if use_last_good
                else result.normalized_row_count
            ),
            last_good_hash=latest.content_hash if latest else None,
            last_good_path=latest.object_path if latest else None,
            is_stale=latest is not None,
            error=result.error,
            retry_count=result.retry_count,
        )

    def _write_manifest(
        self,
        *,
        run_id: str,
        trading_date: date,
        slot: str,
        at: datetime,
        results: dict[str, NormalizedSourceResult] | None = None,
        fallback_status: ManifestStatus = ManifestStatus.NOT_DUE_NO_DATA,
        fallback_error: str | None = None,
    ) -> str:
        result_map = results or {}
        latest_map = self.store.latest_all()
        entries = tuple(
            self._manifest_entry(
                contract,
                result_map.get(contract.source_key),
                latest=latest_map.get(contract.source_key),
                fallback_status=fallback_status,
                fallback_error=fallback_error,
                now=at,
            )
            for contract in self.registry.contracts
        )
        saved = self.store.write_manifest(
            SnapshotManifest(
                schema_version=MANIFEST_SCHEMA_VERSION,
                run_id=run_id,
                registry_sha256=self.registry.registry_sha256,
                trading_date=trading_date,
                slot=slot,
                generated_at=self._utc(at),
                entries=entries,
            )
        )
        return saved.manifest_path

    def _record_health(
        self,
        results: dict[str, NormalizedSourceResult],
        *,
        at: datetime,
        eod: bool = False,
        trading_date: date,
    ) -> None:
        instant = self._utc(at).isoformat()
        success_states = {
            ManifestStatus.SUCCESS_NEW,
            ManifestStatus.SUCCESS_UNCHANGED,
        }
        with self._connect() as connection:
            for source_key, result in results.items():
                previous = connection.execute(
                    "SELECT * FROM market_data_source_schedule WHERE source_key = ?",
                    (source_key,),
                ).fetchone()
                failures = int(previous["consecutive_failures"]) if previous else 0
                if result.status in success_states:
                    failures = 0
                elif result.status in {ManifestStatus.FAILED, ManifestStatus.PARTIAL}:
                    failures += 1
                eod_complete = (
                    trading_date.isoformat()
                    if eod
                    and result.status in success_states
                    and result.data_date == trading_date
                    else previous["eod_complete_date"]
                    if previous
                    else None
                )
                connection.execute(
                    """
                    INSERT INTO market_data_source_schedule(
                        source_key, attempt_count, consecutive_failures,
                        last_status, last_attempt_at, last_success_at,
                        last_data_date, last_error, eod_complete_date, updated_at
                    ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_key) DO UPDATE SET
                        attempt_count=market_data_source_schedule.attempt_count + 1,
                        consecutive_failures=excluded.consecutive_failures,
                        last_status=excluded.last_status,
                        last_attempt_at=excluded.last_attempt_at,
                        last_success_at=COALESCE(excluded.last_success_at, market_data_source_schedule.last_success_at),
                        last_data_date=COALESCE(excluded.last_data_date, market_data_source_schedule.last_data_date),
                        last_error=excluded.last_error,
                        eod_complete_date=COALESCE(excluded.eod_complete_date, market_data_source_schedule.eod_complete_date),
                        updated_at=excluded.updated_at
                    """,
                    (
                        source_key,
                        failures,
                        result.status.value,
                        instant,
                        instant if result.status in success_states else None,
                        result.data_date.isoformat() if result.data_date else None,
                        result.error,
                        eod_complete,
                        instant,
                    ),
                )

    def _save_run(self, result: SchedulerRunResult, *, started_at: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO market_data_scheduler_runs(
                    run_id, trading_date, slot, state, due_count,
                    completed_count, manifest_path, reason, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.run_id,
                    result.trading_date.isoformat(),
                    result.slot,
                    result.state.value,
                    result.due_count,
                    result.completed_count,
                    result.manifest_path,
                    result.reason,
                    self._utc(started_at).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def _blocked_result(
        self,
        *,
        state: SchedulerState,
        trading_date: date,
        slot: str,
        at: datetime,
        reason: str,
        manifest_status: ManifestStatus = ManifestStatus.NOT_DUE_NO_DATA,
    ) -> SchedulerRunResult:
        audit_slot = f"{slot}-{state.value.casefold()}-{self._utc(at).astimezone(IST).strftime('%H%M%S')}"
        run_id = f"{trading_date.isoformat()}-{slot}-{state.value}"
        path = self._write_manifest(
            run_id=run_id,
            trading_date=trading_date,
            slot=audit_slot,
            at=at,
            fallback_status=manifest_status,
            fallback_error=reason,
        )
        result = SchedulerRunResult(
            run_id=run_id,
            state=state,
            trading_date=trading_date,
            slot=slot,
            manifest_path=path,
            reason=reason,
        )
        self._save_run(result, started_at=at)
        return result

    async def run_snapshot(self, *, slot: str, at: datetime) -> SchedulerRunResult:
        if slot not in SNAPSHOT_SLOTS:
            raise ValueError(f"unsupported snapshot slot: {slot}")
        instant = self._utc(at)
        local = instant.astimezone(IST)
        calendar = self.calendar_evaluator(instant)
        trading_date = date.fromisoformat(
            str(calendar.get("tradingDate") or local.date().isoformat())
        )
        expected = datetime.combine(
            local.date(), time(int(slot[:2]), int(slot[2:])), tzinfo=IST
        )
        if (local - expected).total_seconds() > self.slot_grace_seconds:
            return self._blocked_result(
                state=SchedulerState.MISSED,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                reason="slot grace window elapsed; late run recorded as MISSED",
                manifest_status=ManifestStatus.MISSED,
            )
        if not self.enabled:
            return self._blocked_result(
                state=SchedulerState.DISABLED,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                reason="MARKET_DATA_69_ENABLED is disabled",
            )
        if (
            self.registry.schedule_authority is ScheduleAuthority.PROVISIONAL
            and not self.allow_provisional_for_testing
        ):
            return self._blocked_result(
                state=SchedulerState.ACTIVATION_BLOCKED,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                reason="provisional schedules cannot activate production collection",
            )
        owner = uuid.uuid4().hex
        if not self.acquire_lease(owner, now=instant):
            return SchedulerRunResult(
                run_id=f"lease-held-{uuid.uuid4().hex[:12]}",
                state=SchedulerState.LEASE_HELD,
                trading_date=trading_date,
                slot=slot,
                reason="another collector owns the SQLite lease",
            )
        started = instant
        try:
            decisions = self.due_decisions(slot=slot, at=instant, calendar=calendar)
            due_keys = {item.source_key for item in decisions if item.due}
            contracts = tuple(
                contract
                for contract in self.registry.contracts
                if contract.source_key in due_keys
            )
            run_id = f"{trading_date.isoformat()}-{slot}"
            session = "OPEN" if calendar.get("isTradingDay") else "MARKET_CLOSED"
            results = (
                await self._run_contracts(
                    contracts,
                    trading_date=trading_date,
                    session=session,
                    at=instant,
                    run_id=run_id,
                    slot=slot,
                )
                if contracts
                else {}
            )
            self._record_health(
                results, at=instant, trading_date=trading_date
            )
            path = self._write_manifest(
                run_id=run_id,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                results=results,
            )
            result = SchedulerRunResult(
                run_id=run_id,
                state=(
                    SchedulerState.COMPLETED
                    if calendar.get("isTradingDay")
                    else SchedulerState.MARKET_CLOSED
                ),
                trading_date=trading_date,
                slot=slot,
                due_count=len(contracts),
                completed_count=len(results),
                manifest_path=path,
                reason=(
                    "due-only snapshot completed under provisional fixture policy"
                    if calendar.get("isTradingDay")
                    else "market closed; only closed-session-eligible publishers were checked"
                ),
            )
            self._save_run(result, started_at=started)
            await self._dispatch_post_commit(
                collector_run_id=run_id,
                at=instant,
                results=results,
            )
            return result
        finally:
            self.release_lease(owner)

    async def run_eod(self, *, at: datetime) -> SchedulerRunResult:
        instant = self._utc(at)
        local = instant.astimezone(IST)
        calendar = self.calendar_evaluator(instant)
        trading_date = date.fromisoformat(
            str(calendar.get("tradingDate") or local.date().isoformat())
        )
        slot = f"eod-{local.strftime('%H%M')}"
        if local.time() < EOD_START:
            return self._blocked_result(
                state=SchedulerState.WAITING_FOR_EOD,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                reason="EOD polling starts at 15:35 IST",
            )
        if not self.enabled:
            return self._blocked_result(
                state=SchedulerState.DISABLED,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                reason="MARKET_DATA_69_ENABLED is disabled",
            )
        if (
            self.registry.schedule_authority is ScheduleAuthority.PROVISIONAL
            and not self.allow_provisional_for_testing
        ):
            return self._blocked_result(
                state=SchedulerState.ACTIVATION_BLOCKED,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                reason="provisional schedules cannot activate production collection",
            )
        if not calendar.get("isTradingDay"):
            return await self.reconcile_research_session(at=at)
        owner = uuid.uuid4().hex
        if not self.acquire_lease(owner, now=instant):
            return SchedulerRunResult(
                run_id=f"lease-held-{uuid.uuid4().hex[:12]}",
                state=SchedulerState.LEASE_HELD,
                trading_date=trading_date,
                slot=slot,
                reason="another collector owns the SQLite lease",
            )
        try:
            contracts: list[MarketDataSourceContract] = []
            source_states = self._source_states()
            for contract in self.registry.contracts:
                if contract.cadence_class not in {
                    CadenceClass.DAILY_EOD,
                    CadenceClass.DAILY_EOD_COMMODITY,
                }:
                    continue
                state = source_states.get(contract.source_key)
                if state is not None and state["eod_complete_date"] == trading_date.isoformat():
                    continue
                if state is not None and state["last_attempt_at"]:
                    last_attempt = datetime.fromisoformat(state["last_attempt_at"])
                    if (instant - last_attempt).total_seconds() < EOD_RETRY_SECONDS:
                        continue
                contracts.append(contract)
            if not contracts:
                return SchedulerRunResult(
                    run_id=f"{trading_date.isoformat()}-{slot}-not-due",
                    state=SchedulerState.WAITING_FOR_EOD,
                    trading_date=trading_date,
                    slot=slot,
                    reason="no incomplete EOD source has reached its 15-minute retry interval",
                )
            run_id = f"{trading_date.isoformat()}-{slot}-{uuid.uuid4().hex[:12]}"
            results = (
                await self._run_contracts(
                    tuple(contracts),
                    trading_date=trading_date,
                    session="MARKET_CLOSED",
                    at=instant,
                    run_id=run_id,
                    slot=slot,
                )
                if contracts
                else {}
            )
            adjusted: dict[str, NormalizedSourceResult] = {}
            for key, result in results.items():
                if (
                    result.status
                    in {ManifestStatus.SUCCESS_NEW, ManifestStatus.SUCCESS_UNCHANGED}
                    and result.data_date != trading_date
                ):
                    result = result.model_copy(
                        update={
                            "status": ManifestStatus.WAITING_FOR_PUBLICATION,
                            "error": "EOD artifact does not yet carry the current trading date",
                        }
                    )
                adjusted[key] = result
            self._record_health(
                adjusted,
                at=instant,
                eod=True,
                trading_date=trading_date,
            )
            path = self._write_manifest(
                run_id=run_id,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                results=adjusted,
            )
            result = SchedulerRunResult(
                run_id=run_id,
                state=SchedulerState.COMPLETED,
                trading_date=trading_date,
                slot=slot,
                due_count=len(contracts),
                completed_count=sum(
                    item.data_date == trading_date
                    and item.status
                    in {ManifestStatus.SUCCESS_NEW, ManifestStatus.SUCCESS_UNCHANGED}
                    for item in adjusted.values()
                ),
                manifest_path=path,
                reason="per-source EOD polling cycle completed",
            )
            self._save_run(result, started_at=instant)
            await self._dispatch_post_commit(
                collector_run_id=run_id,
                at=instant,
                results=adjusted,
            )
            return result
        finally:
            self.release_lease(owner)

    def health_projection(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = {
                row["source_key"]: row
                for row in connection.execute(
                    "SELECT * FROM market_data_source_schedule"
                ).fetchall()
            }
        output: list[dict[str, Any]] = []
        for contract in self.registry.contracts:
            row = rows.get(contract.source_key)
            output.append(
                {
                    "sourceKey": contract.source_key,
                    "scheduleAuthority": contract.schedule_authority.value,
                    "activationReady": contract.activation_ready,
                    "attemptCount": int(row["attempt_count"]) if row else 0,
                    "consecutiveFailures": int(row["consecutive_failures"]) if row else 0,
                    "lastStatus": row["last_status"] if row else "NEVER",
                    "lastAttemptAt": row["last_attempt_at"] if row else None,
                    "lastSuccessAt": row["last_success_at"] if row else None,
                    "lastDataDate": row["last_data_date"] if row else None,
                    "lastError": row["last_error"] if row else None,
                    "eodCompleteDate": row["eod_complete_date"] if row else None,
                }
            )
        return output

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            lease = connection.execute(
                "SELECT * FROM market_data_scheduler_leases WHERE lease_key = ?",
                (LEASE_KEY,),
            ).fetchone()
            latest_run = connection.execute(
                "SELECT * FROM market_data_scheduler_runs ORDER BY completed_at DESC LIMIT 1"
            ).fetchone()
        post_commit = self._last_post_commit
        if post_commit is None and self.post_commit_processor is not None:
            persisted = self.post_commit_processor.snapshot()
            if persisted is not None:
                post_commit = persisted.model_dump(mode="json", by_alias=True)
        now_ist = datetime.now(IST)
        calendar = self.calendar_evaluator(now_ist)
        research = self.eod_date_resolver(now_ist)
        return {
            "enabled": self.enabled,
            "scheduleAuthority": self.registry.schedule_authority.value,
            "activationReady": self.registry.activation_ready,
            "provisionalOverrideActive": self.allow_provisional_for_testing,
            "sourceCount": len(self.registry.contracts),
            "slots": list(SNAPSHOT_SLOTS),
            "lease": dict(lease) if lease else None,
            "latestRun": dict(latest_run) if latest_run else None,
            "health": self.health_projection(),
            "calculatedOutputKeys": sorted(CALCULATED_OUTPUT_KEYS),
            "lastCalculatedOutputCount": self._last_calculated_output_count,
            "lastDerivedError": self._last_derived_error,
            "postCommit": post_commit,
            "timezone": "Asia/Kolkata",
            "clockIst": now_ist.isoformat(),
            "sessionPhase": nse_session_phase(
                now_ist, calendar=calendar
            ).value,
            "researchSessionDate": (
                None if research is None else research.isoformat()
            ),
        }

    async def run_source(
        self, source_key: str, *, at: datetime
    ) -> dict[str, Any]:
        contract = self.registry.by_key.get(source_key)
        if contract is None:
            raise KeyError(f"unknown market-data source: {source_key}")
        if not self.enabled:
            return {"state": SchedulerState.DISABLED.value, "sourceKey": source_key}
        if (
            self.registry.schedule_authority is ScheduleAuthority.PROVISIONAL
            and not self.allow_provisional_for_testing
        ):
            return {
                "state": SchedulerState.ACTIVATION_BLOCKED.value,
                "sourceKey": source_key,
            }
        instant = self._utc(at)
        calendar = self.calendar_evaluator(instant)
        trading_date = date.fromisoformat(str(calendar["tradingDate"]))
        owner = uuid.uuid4().hex
        if not self.acquire_lease(owner, now=instant):
            return {
                "state": SchedulerState.LEASE_HELD.value,
                "sourceKey": source_key,
            }
        try:
            run_id = f"manual-{source_key}-{uuid.uuid4().hex[:12]}"
            context = self._context(trading_date, "MANUAL", instant)
            results = await self.service.run_sources(
                (contract,), context=context, run_id=run_id, slot="manual"
            )
            self._record_health(results, at=instant, trading_date=trading_date)
            return results[source_key].model_dump(mode="json")
        finally:
            self.release_lease(owner)

    async def run_all(self, *, at: datetime) -> SchedulerRunResult:
        """Manually attempt every contract in the current registry.

        This bypasses cadence and holiday suppression only. The existing
        activation gates, singleton lease, bounded service, validation,
        normalization, last-good preservation and manifest writer still apply.
        """
        instant = self._utc(at)
        local = instant.astimezone(IST)
        calendar = self.calendar_evaluator(instant)
        trading_date = date.fromisoformat(
            str(calendar.get("tradingDate") or local.date().isoformat())
        )
        slot = f"manual-{local.strftime('%Y%m%d-%H%M%S')}"
        if not self.enabled:
            return self._blocked_result(
                state=SchedulerState.DISABLED,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                reason="MARKET_DATA_69_ENABLED is disabled",
            )
        if (
            self.registry.schedule_authority is ScheduleAuthority.PROVISIONAL
            and not self.allow_provisional_for_testing
        ):
            return self._blocked_result(
                state=SchedulerState.ACTIVATION_BLOCKED,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                reason="provisional schedules require the approved activation override",
            )
        owner = uuid.uuid4().hex
        if not self.acquire_lease(owner, now=instant, ttl_seconds=900):
            return SchedulerRunResult(
                run_id=f"manual-lease-held-{uuid.uuid4().hex[:12]}",
                state=SchedulerState.LEASE_HELD,
                trading_date=trading_date,
                slot=slot,
                reason="another collector owns the SQLite lease",
            )
        started = instant
        try:
            contracts = tuple(self.registry.contracts)
            run_id = f"{trading_date.isoformat()}-{slot}-{uuid.uuid4().hex[:12]}"
            results = await self._run_contracts(
                contracts,
                trading_date=trading_date,
                session="MANUAL",
                at=instant,
                run_id=run_id,
                slot=slot,
            )
            self._record_health(results, at=instant, trading_date=trading_date)
            path = self._write_manifest(
                run_id=run_id,
                trading_date=trading_date,
                slot=slot,
                at=instant,
                results=results,
            )
            result = SchedulerRunResult(
                run_id=run_id,
                state=SchedulerState.COMPLETED,
                trading_date=trading_date,
                slot=slot,
                due_count=len(contracts),
                completed_count=len(results),
                manifest_path=path,
                reason="manual registry-wide refresh completed",
            )
            self._save_run(result, started_at=started)
            await self._dispatch_post_commit(
                collector_run_id=run_id,
                at=instant,
                results=results,
            )
            return result
        finally:
            self.release_lease(owner)

    def _finalized_slots(self, trading_date: date) -> set[str]:
        with self._connect() as connection:
            return {
                row["slot"]
                for row in connection.execute(
                    """
                    SELECT slot FROM market_data_scheduler_runs
                    WHERE trading_date = ?
                      AND state IN ('COMPLETED', 'MISSED', 'MARKET_CLOSED')
                    """,
                    (trading_date.isoformat(),),
                ).fetchall()
            }

    async def tick(self, *, at: datetime) -> tuple[SchedulerRunResult, ...]:
        """Run or explicitly miss every checkpoint reached since restart."""
        instant = self._utc(at)
        local = instant.astimezone(IST)
        finalized = self._finalized_slots(local.date())
        output: list[SchedulerRunResult] = []
        for slot in SNAPSHOT_SLOTS:
            expected = datetime.combine(
                local.date(), time(int(slot[:2]), int(slot[2:])), tzinfo=IST
            )
            if local < expected or slot in finalized:
                continue
            result = await self.run_snapshot(slot=slot, at=instant)
            output.append(result)
        return tuple(output)

    async def start_foreground(self, *, poll_seconds: int = 15) -> dict[str, Any]:
        if poll_seconds < 1:
            raise ValueError("poll_seconds must be positive")
        if not self.enabled:
            return {"state": SchedulerState.DISABLED.value, **self.status()}
        if (
            self.registry.schedule_authority is ScheduleAuthority.PROVISIONAL
            and not self.allow_provisional_for_testing
        ):
            return {"state": SchedulerState.ACTIVATION_BLOCKED.value, **self.status()}
        while True:
            now_ist = datetime.now(IST)
            calendar = self.calendar_evaluator(now_ist)
            phase = nse_session_phase(now_ist, calendar=calendar)
            await self.reconcile_research_session(at=now_ist)
            await self.tick(at=now_ist)
            if phase is NseSessionPhase.EOD_WINDOW:
                await self.run_eod(at=now_ist)
            await asyncio.sleep(poll_seconds)


def build_default_scheduler(*, db_path: Path, data_root: Path) -> MarketDataScheduler:
    store = MarketDataStore(root=data_root, db_path=db_path)
    service = MarketDataService(store=store)
    enabled = os.getenv("MARKET_DATA_69_ENABLED", "0").strip() == "1"
    provisional_override = (
        os.getenv("MARKET_DATA_69_PROVISIONAL_OVERRIDE", "0").strip() == "1"
    )
    return MarketDataScheduler(
        registry=load_market_data_registry(),
        store=store,
        service=service,
        post_commit_processor=CashPostCommitOrchestrator(store=store),
        context_provider=SavedMarketParameterProvider(store),
        enabled=enabled,
        # Explicit operator-authorized M7 override. Manifests and status keep
        # PROVISIONAL authority; this does not promote registry evidence.
        allow_provisional_for_testing=provisional_override,
    )


class ManualRefreshCoordinator:
    """Single-flight background wrapper for a registry-wide manual refresh."""

    def __init__(
        self,
        scheduler: MarketDataScheduler,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.scheduler = scheduler
        self.clock = clock or (lambda: datetime.now(UTC))
        self._task: asyncio.Task[None] | None = None
        self._start_lock = asyncio.Lock()
        self._state: dict[str, Any] = {
            "state": "IDLE",
            "accepted": False,
            "startedAt": None,
            "completedAt": None,
            "attemptedCount": 0,
            "successfulCount": 0,
            "lastGoodCount": 0,
            "validEmptyCount": 0,
            "failedCount": 0,
            "manifestPath": None,
            "error": None,
        }

    def status(self) -> dict[str, Any]:
        return {
            **self._state,
            "sourceCount": len(self.scheduler.registry.contracts),
            "scheduledTimesIst": scheduled_times_ist(),
        }

    async def start(self) -> dict[str, Any]:
        async with self._start_lock:
            if self._task is not None and not self._task.done():
                return {**self.status(), "accepted": False}
            instant = self.scheduler._utc(self.clock())
            self._state = {
                "state": "RUNNING",
                "accepted": True,
                "startedAt": instant.isoformat(),
                "completedAt": None,
                "attemptedCount": 0,
                "successfulCount": 0,
                "lastGoodCount": 0,
                "validEmptyCount": 0,
                "failedCount": 0,
                "manifestPath": None,
                "error": None,
            }
            self._task = asyncio.create_task(self._execute(instant))
            return self.status()

    async def _execute(self, instant: datetime) -> None:
        try:
            result = await self.scheduler.run_all(at=instant)
            counts = {
                "successfulCount": 0,
                "lastGoodCount": 0,
                "validEmptyCount": 0,
                "failedCount": 0,
            }
            if result.manifest_path:
                manifest = json.loads(
                    Path(result.manifest_path).read_text(encoding="utf-8")
                )
                for entry in manifest.get("entries", []):
                    status = str(entry.get("status") or "")
                    if status in {"SUCCESS_NEW", "SUCCESS_UNCHANGED"}:
                        counts["successfulCount"] += 1
                    elif status in {"STALE_LAST_GOOD", "CACHED_CURRENT"}:
                        counts["lastGoodCount"] += 1
                    elif status == "VALID_EMPTY":
                        counts["validEmptyCount"] += 1
                    elif status in {"FAILED", "PARTIAL", "WAITING_FOR_PUBLICATION"}:
                        counts["failedCount"] += 1
            self._state = {
                **self._state,
                **counts,
                "state": result.state.value,
                "accepted": result.state is not SchedulerState.LEASE_HELD,
                "completedAt": datetime.now(UTC).isoformat(),
                "attemptedCount": result.due_count,
                "manifestPath": result.manifest_path,
                "runId": result.run_id,
                "reason": result.reason,
            }
        except Exception as exc:
            self._state = {
                **self._state,
                "state": SchedulerState.FAILED.value,
                "completedAt": datetime.now(UTC).isoformat(),
                "error": f"{type(exc).__name__}: {exc}",
            }

    async def wait(self) -> dict[str, Any]:
        task = self._task
        if task is not None:
            await task
        return self.status()
