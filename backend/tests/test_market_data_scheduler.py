from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from trendforge_api import cli
from trendforge_api.market_data_registry import (
    EXPECTED_SOURCE_COUNT,
    CadenceClass,
    load_market_data_registry,
)
from trendforge_api.market_data_scheduler import (
    CASH_SOURCE_KEY,
    EOD_RETRY_SECONDS,
    INDEX_CLOSE_SOURCE_KEY,
    IST,
    SNAPSHOT_SLOTS,
    ManualRefreshCoordinator,
    MarketDataScheduler,
    SchedulerState,
    build_default_scheduler,
)
from trendforge_api.market_data_service import NormalizedSourceResult, ParameterContext
from trendforge_api.market_data_store import ManifestStatus, MarketDataStore


TRADING_DAY = date(2026, 8, 5)


def _at(hour: int, minute: int) -> datetime:
    return datetime(2026, 8, 5, hour, minute, tzinfo=IST).astimezone(UTC)


def _calendar(is_open: bool = True):
    def evaluate(_at: datetime) -> dict:
        return {
            "state": "OPEN_NORMAL" if is_open else "CLOSED_HOLIDAY",
            "isTradingDay": is_open,
            "canRunScheduledScan": is_open,
            "tradingDate": TRADING_DAY.isoformat(),
            "reason": "fixture",
        }

    return evaluate


class CountingService:
    def __init__(
        self,
        store: MarketDataStore,
        *,
        failures: set[str] | None = None,
        stale_eod: set[str] | None = None,
    ) -> None:
        self.store = store
        self.failures = failures or set()
        self.stale_eod = stale_eod or set()
        self.calls: list[tuple[str, ...]] = []

    async def run_sources(
        self,
        contracts,
        *,
        context: ParameterContext,
        run_id: str | None = None,
        slot: str = "manual",
    ) -> dict[str, NormalizedSourceResult]:
        keys = tuple(contract.source_key for contract in contracts)
        self.calls.append(keys)
        output: dict[str, NormalizedSourceResult] = {}
        assert run_id is not None
        for key in keys:
            if key in self.failures:
                attempt = self.store.record_attempt(
                    run_id=run_id,
                    source_key=key,
                    trading_date=context.trading_date,
                    slot=slot,
                    attempted_at=context.now,
                    status=ManifestStatus.FAILED,
                    error="fixture failure",
                )
                output[key] = NormalizedSourceResult(
                    source_key=key,
                    normalized_source_key=key,
                    status=ManifestStatus.FAILED,
                    parser_state="FETCH_FAILED",
                    error="fixture failure",
                    stored_attempt_id=attempt.attempt_id,
                )
                continue
            data_date = (
                context.trading_date - timedelta(days=1)
                if key in self.stale_eod
                else context.trading_date
            )
            payload = {"sourceKey": key, "records": [{"symbol": key.upper()}]}
            attempted = self.store.commit_success(
                run_id=run_id,
                source_key=key,
                trading_date=context.trading_date,
                slot=slot,
                attempted_at=context.now,
                fetched_at=context.now,
                data_date=data_date,
                source_url=f"https://example.test/{key}",
                http_status=200,
                media_type="application/vnd.trendforge.normalized+json",
                content=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
                extension="json",
                normalized_row_count=1,
                retry_count=0,
            )
            output[key] = NormalizedSourceResult(
                source_key=key,
                normalized_source_key=key,
                status=attempted.status,
                parser_state="PARSED_STRUCTURED",
                source_url=f"https://example.test/{key}",
                http_status=200,
                fetched_at=context.now,
                data_date=data_date,
                normalized_row_count=1,
                records=({"symbol": key.upper()},),
                payload=payload,
                normalized_content_hash=attempted.content_hash,
                stored_attempt_id=attempted.attempt_id,
            )
        return output


class RecordingDerivedService:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict] = []

    def materialize(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("fixture derived failure")
        return {"industry_peer_group_v1": {"records": [{"symbol": "ABC"}]}}


def _scheduler(
    tmp_path: Path,
    *,
    enabled: bool = True,
    calendar_open: bool = True,
    failures: set[str] | None = None,
    stale_eod: set[str] | None = None,
):
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    service = CountingService(store, failures=failures, stale_eod=stale_eod)
    scheduler = MarketDataScheduler(
        registry=load_market_data_registry(),
        store=store,
        service=service,
        enabled=enabled,
        allow_provisional_for_testing=True,
        calendar_evaluator=_calendar(calendar_open),
        slot_grace_seconds=180,
    )
    return scheduler, service, store


def test_status_session_clock_is_ist_not_utc(tmp_path: Path) -> None:
    scheduler, _service, _store = _scheduler(tmp_path)
    status = scheduler.status()
    assert status["timezone"] == "Asia/Kolkata"
    assert "+05:30" in status["clockIst"]
    assert "sessionPhase" in status
    assert "researchSessionDate" in status


def test_slots_are_exact_ist_and_ist_has_no_dst_shift() -> None:
    assert SNAPSHOT_SLOTS == ("0900", "0917", "1030", "1230", "1330", "1500")
    winter = datetime(2026, 1, 5, 9, 17, tzinfo=IST).utcoffset()
    summer = datetime(2026, 8, 5, 9, 17, tzinfo=IST).utcoffset()
    assert winter == summer == timedelta(hours=5, minutes=30)
    assert EOD_RETRY_SECONDS == 900


def test_default_scheduler_requires_two_explicit_activation_flags(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("MARKET_DATA_69_ENABLED", "1")
    monkeypatch.delenv("MARKET_DATA_69_PROVISIONAL_OVERRIDE", raising=False)
    blocked = build_default_scheduler(
        db_path=tmp_path / "blocked.db", data_root=tmp_path / "blocked-data"
    )
    assert blocked.enabled is True
    assert blocked.status()["provisionalOverrideActive"] is False

    monkeypatch.setenv("MARKET_DATA_69_PROVISIONAL_OVERRIDE", "1")
    enabled = build_default_scheduler(
        db_path=tmp_path / "enabled.db", data_root=tmp_path / "enabled-data"
    )
    status = enabled.status()
    assert enabled.enabled is True
    assert status["scheduleAuthority"] == "PROVISIONAL"
    assert status["activationReady"] is False
    assert status["provisionalOverrideActive"] is True


def test_due_only_snapshot_calls_subset_and_manifests_all_sources(tmp_path: Path) -> None:
    scheduler, service, _store = _scheduler(tmp_path)

    result = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 17)))

    assert result.state is SchedulerState.COMPLETED
    assert 0 < result.due_count < EXPECTED_SOURCE_COUNT
    assert len(service.calls) == 2
    assert sum(len(call) for call in service.calls) == result.due_count
    assert set(service.calls[0]).isdisjoint(service.calls[1])
    payload = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert len(payload["entries"]) == EXPECTED_SOURCE_COUNT


def test_snapshot_materializes_calculated_outputs_without_counting_them_as_sources(
    tmp_path: Path,
) -> None:
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    service = CountingService(store)
    derived = RecordingDerivedService()
    scheduler = MarketDataScheduler(
        registry=load_market_data_registry(),
        store=store,
        service=service,
        derived_service=derived,
        enabled=True,
        allow_provisional_for_testing=True,
        calendar_evaluator=_calendar(True),
        eod_date_resolver=lambda _at: TRADING_DAY,
    )

    result = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 17)))

    assert result.state is SchedulerState.COMPLETED
    assert len(derived.calls) == 1
    assert derived.calls[0]["run_id"] == result.run_id
    assert scheduler.status()["lastCalculatedOutputCount"] == 1
    payload = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert len(payload["entries"]) == EXPECTED_SOURCE_COUNT


def test_calculation_failure_is_isolated_from_source_collection(tmp_path: Path) -> None:
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    service = CountingService(store)
    derived = RecordingDerivedService(fail=True)
    scheduler = MarketDataScheduler(
        registry=load_market_data_registry(),
        store=store,
        service=service,
        derived_service=derived,
        enabled=True,
        allow_provisional_for_testing=True,
        calendar_evaluator=_calendar(True),
        eod_date_resolver=lambda _at: TRADING_DAY,
    )

    result = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 17)))

    assert result.state is SchedulerState.COMPLETED
    assert scheduler.status()["lastDerivedError"] == "RuntimeError: fixture derived failure"


def test_kill_switch_writes_blocked_manifest_and_makes_zero_service_calls(tmp_path: Path) -> None:
    scheduler, service, _store = _scheduler(tmp_path, enabled=False)

    result = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 17)))

    assert result.state is SchedulerState.DISABLED
    assert service.calls == []
    payload = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert len(payload["entries"]) == EXPECTED_SOURCE_COUNT


def test_provisional_registry_cannot_activate_without_explicit_fixture_gate(tmp_path: Path) -> None:
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    service = CountingService(store)
    scheduler = MarketDataScheduler(
        registry=load_market_data_registry(),
        store=store,
        service=service,
        enabled=True,
        allow_provisional_for_testing=False,
        calendar_evaluator=_calendar(True),
        eod_date_resolver=lambda _at: TRADING_DAY,
    )

    result = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 17)))

    assert result.state is SchedulerState.ACTIVATION_BLOCKED
    assert service.calls == []


def test_holiday_suppresses_market_sources_but_keeps_google_trends_context(
    tmp_path: Path,
) -> None:
    scheduler, service, _store = _scheduler(tmp_path, calendar_open=False)

    result = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 17)))

    assert result.state is SchedulerState.MARKET_CLOSED
    assert service.calls == [("google_trends_india_rss",)]


def test_holiday_0900_runs_only_publishers_whose_rules_allow_closed_days(
    tmp_path: Path,
) -> None:
    scheduler, service, _store = _scheduler(tmp_path, calendar_open=False)

    result = asyncio.run(scheduler.run_snapshot(slot="0900", at=_at(9, 0)))

    assert result.state is SchedulerState.MARKET_CLOSED
    assert service.calls
    allowed = {
        contract.source_key
        for contract in scheduler.registry.contracts
        if scheduler._closed_session_allowed(contract)
    }
    assert set(service.calls[0])
    assert set(service.calls[0]).issubset(allowed)


def test_late_slot_is_missed_and_never_relabelled_on_time(tmp_path: Path) -> None:
    scheduler, service, _store = _scheduler(tmp_path)

    result = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 25)))

    assert result.state is SchedulerState.MISSED
    assert service.calls == []


def test_late_missed_audit_does_not_overwrite_completed_slot_manifest(
    tmp_path: Path,
) -> None:
    scheduler, _service, _store = _scheduler(tmp_path)
    completed = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 17)))
    completed_bytes = Path(completed.manifest_path).read_bytes()

    missed = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 25)))

    assert missed.manifest_path != completed.manifest_path
    assert Path(completed.manifest_path).read_bytes() == completed_bytes


def test_sqlite_lease_rejects_duplicate_and_recovers_after_expiry(tmp_path: Path) -> None:
    scheduler, _service, _store = _scheduler(tmp_path)
    now = _at(9, 17)

    assert scheduler.acquire_lease("owner-a", now=now, ttl_seconds=60) is True
    assert scheduler.acquire_lease("owner-b", now=now, ttl_seconds=60) is False
    assert scheduler.acquire_lease(
        "owner-b", now=now + timedelta(seconds=61), ttl_seconds=60
    ) is True


def test_restart_tick_records_each_missed_slot_once(tmp_path: Path) -> None:
    scheduler, service, _store = _scheduler(tmp_path)

    first = asyncio.run(scheduler.tick(at=_at(10, 35)))
    second = asyncio.run(scheduler.tick(at=_at(10, 36)))

    assert [item.state for item in first] == [
        SchedulerState.MISSED,
        SchedulerState.MISSED,
        SchedulerState.MISSED,
    ]
    assert second == ()
    assert service.calls == []


def test_manual_source_run_respects_singleton_lease(tmp_path: Path) -> None:
    scheduler, service, _store = _scheduler(tmp_path)
    assert scheduler.acquire_lease("active-owner", now=_at(10, 0), ttl_seconds=120)

    result = asyncio.run(
        scheduler.run_source("nse_all_indices", at=_at(10, 0))
    )

    assert result["state"] == SchedulerState.LEASE_HELD.value
    assert service.calls == []


def test_manual_all_refresh_uses_dynamic_registry_and_runs_when_closed(
    tmp_path: Path,
) -> None:
    scheduler, service, _store = _scheduler(tmp_path, calendar_open=False)

    result = asyncio.run(scheduler.run_all(at=_at(16, 5)))

    expected_keys = {contract.source_key for contract in scheduler.registry.contracts}
    assert result.state is SchedulerState.COMPLETED
    assert result.due_count == len(expected_keys)
    assert result.completed_count == len(expected_keys)
    assert len(service.calls) == 2
    assert set().union(*map(set, service.calls)) == expected_keys
    assert set(service.calls[0]).isdisjoint(service.calls[1])
    assert result.slot == "manual-20260805-160500"
    payload = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert payload["slot"] == result.slot
    assert {entry["sourceKey"] for entry in payload["entries"]} == expected_keys


def test_manual_all_failure_keeps_last_success_with_true_timestamp(
    tmp_path: Path,
) -> None:
    scheduler, service, store = _scheduler(tmp_path)
    source_key = scheduler.registry.contracts[0].source_key
    first = asyncio.run(scheduler.run_all(at=_at(10, 0)))
    last_good = store.latest_for(source_key)
    assert last_good is not None

    service.failures.add(source_key)
    second = asyncio.run(scheduler.run_all(at=_at(10, 5)))

    preserved = store.latest_for(source_key)
    assert preserved is not None
    assert preserved.content_hash == last_good.content_hash
    manifest = json.loads(Path(second.manifest_path).read_text(encoding="utf-8"))
    entry = next(row for row in manifest["entries"] if row["sourceKey"] == source_key)
    assert entry["status"] == "STALE_LAST_GOOD"
    assert entry["contentHash"] == last_good.content_hash
    assert entry["objectPath"] == last_good.object_path
    assert entry["dataDate"] == last_good.data_date.isoformat()
    assert datetime.fromisoformat(entry["fetchedAt"].replace("Z", "+00:00")) == (
        last_good.fetched_at
    )
    assert first.manifest_path != second.manifest_path


def test_manual_refresh_coordinator_reports_dynamic_schedule_and_counts(
    tmp_path: Path,
) -> None:
    scheduler, _service, _store = _scheduler(tmp_path)
    coordinator = ManualRefreshCoordinator(scheduler, clock=lambda: _at(11, 11))

    async def exercise() -> dict:
        started = await coordinator.start()
        assert started["state"] == "RUNNING"
        assert started["accepted"] is True
        return await coordinator.wait()

    finished = asyncio.run(exercise())
    assert finished["state"] == "COMPLETED", finished
    assert finished["sourceCount"] == len(scheduler.registry.contracts)
    assert finished["scheduledTimesIst"] == [
        "09:00", "09:17", "10:30", "12:30", "13:30", "15:00"
    ]
    assert finished["attemptedCount"] == len(scheduler.registry.contracts)
    assert finished["successfulCount"] == len(scheduler.registry.contracts)


def test_eod_stops_each_source_only_after_current_date_success(tmp_path: Path) -> None:
    registry = load_market_data_registry()
    eod_keys = {
        item.source_key
        for item in registry.contracts
        if item.cadence_class in {CadenceClass.DAILY_EOD, CadenceClass.DAILY_EOD_COMMODITY}
    }
    stale_key = sorted(eod_keys)[0]
    scheduler, service, _store = _scheduler(tmp_path, stale_eod={stale_key})

    first = asyncio.run(scheduler.run_eod(at=_at(15, 35)))
    suppressed = asyncio.run(scheduler.run_eod(at=_at(15, 36)))
    second = asyncio.run(scheduler.run_eod(at=_at(15, 50)))

    assert first.due_count == len(eod_keys)
    assert stale_key in service.calls[0]
    assert suppressed.state is SchedulerState.WAITING_FOR_EOD
    assert suppressed.due_count == 0
    assert service.calls[1] == (stale_key,)
    assert second.due_count == 1


def test_health_projection_tracks_failure_streak_and_success(tmp_path: Path) -> None:
    registry = load_market_data_registry()
    failing_key = next(
        item.source_key
        for item in registry.contracts
        if item.cadence_class is CadenceClass.INTRADAY
    )
    scheduler, _service, _store = _scheduler(tmp_path, failures={failing_key})

    asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 17)))
    health = {row["sourceKey"]: row for row in scheduler.health_projection()}

    assert len(health) == EXPECTED_SOURCE_COUNT
    assert health[failing_key]["consecutiveFailures"] == 1
    assert health[failing_key]["lastStatus"] == "FAILED"


def test_cli_contract_parses_and_routes_all_market_data_commands(monkeypatch) -> None:
    routed: list[str] = []

    def fake_runner(args):
        routed.append(args.command)
        return {"status": "FIXTURE", "command": args.command}, 0

    monkeypatch.setattr(cli, "run_market_data_cli_command", fake_runner)
    commands = (
        ["start-scheduler", "--db-path", "x.db", "--data-root", "x"],
        ["run-snapshot", "--time", "0917", "--db-path", "x.db", "--data-root", "x"],
        ["run-source", "--source-key", "nse_all_indices", "--db-path", "x.db", "--data-root", "x"],
        ["run-all", "--db-path", "x.db", "--data-root", "x"],
        ["run-eod", "--db-path", "x.db", "--data-root", "x"],
        ["show-status", "--db-path", "x.db", "--data-root", "x"],
        ["cleanup", "--dry-run", "--db-path", "x.db", "--data-root", "x"],
        ["cleanup", "--apply", "--db-path", "x.db", "--data-root", "x"],
    )
    for argv in commands:
        args = cli.build_parser().parse_args(argv)
        payload, status = cli.run_market_data_cli_command(args)
        assert status == 0
        assert payload["command"] == argv[0]

    assert routed == [item[0] for item in commands]


def test_reconcile_open_session_uses_last_closed_day_and_fetches_index(
    tmp_path: Path,
) -> None:
    scheduler, service, _store = _scheduler(tmp_path)
    research = date(2026, 8, 4)
    scheduler.eod_date_resolver = lambda _at: research

    result = asyncio.run(scheduler.reconcile_research_session(at=_at(10, 0)))

    assert result.state is SchedulerState.COMPLETED
    assert result.trading_date == research
    fetched = set().union(*map(set, service.calls))
    assert CASH_SOURCE_KEY in fetched
    assert INDEX_CLOSE_SOURCE_KEY in fetched
    assert len(fetched) == 2
    assert scheduler.store.latest_for(INDEX_CLOSE_SOURCE_KEY) is not None
    assert scheduler.store.latest_for(INDEX_CLOSE_SOURCE_KEY).data_date == research


def test_holiday_eod_reconciles_last_session_instead_of_idling(
    tmp_path: Path,
) -> None:
    scheduler, service, _store = _scheduler(tmp_path, calendar_open=False)
    research = date(2026, 8, 4)
    scheduler.eod_date_resolver = lambda _at: research

    result = asyncio.run(scheduler.run_eod(at=_at(16, 5)))

    assert result.state is SchedulerState.MARKET_CLOSED
    assert result.trading_date == research
    fetched = set().union(*map(set, service.calls))
    assert fetched == {CASH_SOURCE_KEY, INDEX_CLOSE_SOURCE_KEY}


def test_reconcile_skips_refetch_when_closed_session_already_current(
    tmp_path: Path,
) -> None:
    scheduler, service, _store = _scheduler(tmp_path)
    research = date(2026, 8, 4)
    scheduler.eod_date_resolver = lambda _at: research
    first = asyncio.run(scheduler.reconcile_research_session(at=_at(10, 0)))
    assert first.due_count == 2
    calls_after_first = len(service.calls)
    second = asyncio.run(scheduler.reconcile_research_session(at=_at(10, 1)))
    assert second.due_count == 0
    assert len(service.calls) == calls_after_first


class RecordingPostCommit:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict] = []

    def process(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("fixture post-commit failure")
        return {
            "contract": "trendforge.cashPostCommit.v1",
            "latestRun": {"state": "COMPLETED"},
        }


def test_scheduler_dispatches_one_post_commit_event_after_saved_run(tmp_path: Path) -> None:
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    service = CountingService(store)
    post_commit = RecordingPostCommit()
    scheduler = MarketDataScheduler(
        registry=load_market_data_registry(),
        store=store,
        service=service,
        post_commit_processor=post_commit,
        enabled=True,
        allow_provisional_for_testing=True,
        calendar_evaluator=_calendar(True),
        eod_date_resolver=lambda _at: TRADING_DAY,
    )

    result = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 17)))

    assert result.state is SchedulerState.COMPLETED
    assert len(post_commit.calls) == 1
    assert post_commit.calls[0]["collector_run_id"] == result.run_id
    assert post_commit.calls[0]["trading_date"] == TRADING_DAY
    assert scheduler.status()["postCommit"]["latestRun"]["state"] == "COMPLETED"


def test_weekend_post_commit_uses_expected_latest_eod_date(tmp_path: Path) -> None:
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    post_commit = RecordingPostCommit()
    expected_eod = date(2026, 8, 14)
    scheduler = MarketDataScheduler(
        registry=load_market_data_registry(),
        store=store,
        service=CountingService(store),
        post_commit_processor=post_commit,
        enabled=True,
        allow_provisional_for_testing=True,
        calendar_evaluator=_calendar(False),
        eod_date_resolver=lambda _at: expected_eod,
    )

    asyncio.run(
        scheduler._dispatch_post_commit(
            collector_run_id="weekend-refresh",
            at=datetime(2026, 8, 16, 12, 0, tzinfo=IST).astimezone(UTC),
            results={},
        )
    )

    assert len(post_commit.calls) == 1
    assert post_commit.calls[0]["trading_date"] == expected_eod


def test_post_commit_blocks_when_official_eod_date_is_unknown(tmp_path: Path) -> None:
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    post_commit = RecordingPostCommit()
    scheduler = MarketDataScheduler(
        registry=load_market_data_registry(),
        store=store,
        service=CountingService(store),
        post_commit_processor=post_commit,
        enabled=True,
        allow_provisional_for_testing=True,
        calendar_evaluator=_calendar(False),
        eod_date_resolver=lambda _at: None,
    )

    asyncio.run(
        scheduler._dispatch_post_commit(
            collector_run_id="calendar-unknown",
            at=datetime(2026, 8, 16, 12, 0, tzinfo=IST).astimezone(UTC),
            results={},
        )
    )

    assert post_commit.calls == []
    status = scheduler.status()["postCommit"]
    assert status["state"] == "BLOCKED_INPUT"
    assert "calendar" in status["error"].lower()


def test_post_commit_failure_does_not_rollback_collector_run(tmp_path: Path) -> None:
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    service = CountingService(store)
    post_commit = RecordingPostCommit(fail=True)
    scheduler = MarketDataScheduler(
        registry=load_market_data_registry(),
        store=store,
        service=service,
        post_commit_processor=post_commit,
        enabled=True,
        allow_provisional_for_testing=True,
        calendar_evaluator=_calendar(True),
        eod_date_resolver=lambda _at: TRADING_DAY,
    )

    result = asyncio.run(scheduler.run_snapshot(slot="0917", at=_at(9, 17)))

    assert result.state is SchedulerState.COMPLETED
    assert result.manifest_path is not None
    assert Path(result.manifest_path).is_file()
    assert scheduler.status()["postCommit"]["state"] == "FAILED_STAGE"
    assert "fixture post-commit failure" in scheduler.status()["postCommit"]["error"]