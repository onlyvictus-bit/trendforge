from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any

from . import storage
from .disclosure_intelligence import normalize_and_save_disclosures
from .institutional_sources import (
    AsyncEndpointClient,
    DEFAULT_INTRADAY_SECTOR_INDICES,
    intraday_stock_detail_requests,
    scanner_parser_requests,
)
from .intraday_stock_details import (
    build_intraday_stock_detail_snapshot,
    save_intraday_stock_detail_snapshot,
)
from .demo_data import load_demo_data
from .decision_fixtures import load_demo_decision_run
from .lifecycle_fixtures import load_lifecycle_fixture_events
from .source_registry_contracts import build_registry_coverage
from .performance import benchmark_cached_nifty50


MARKET_DATA_COMMANDS = {
    "start-scheduler",
    "run-snapshot",
    "run-source",
    "run-all",
    "run-eod",
    "show-status",
    "cleanup",
}

R16_COMMANDS = {
    "r16-status",
    "r16-schema",
    "r16-build",
    "r16-catch-up",
    "r16-replay",
    "r16-rebuild",
}


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def init_database() -> dict[str, Any]:
    storage.init_db()
    connection = storage.connect()
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        connection.close()
    return {
        "database": str(storage.DB_PATH),
        "integrity": integrity,
        "foreignKeys": bool(foreign_keys),
        "journalMode": journal_mode,
    }


def migrate_database() -> dict[str, Any]:
    storage.init_db()
    migrations = storage.list_schema_migrations()
    return {
        "status": "PASS",
        "database": str(storage.DB_PATH),
        "migrationCount": len(migrations),
        "migrations": migrations,
    }


def validate_source_coverage() -> tuple[dict[str, Any], int]:
    coverage = build_registry_coverage()
    payload = coverage.model_dump(mode="json", by_alias=True)
    valid = (
        coverage.unclassified_url_count == 0
        and coverage.active_source_count == coverage.contracted_source_count
    )
    payload["status"] = "PASS" if valid else "FAIL"
    return payload, 0 if valid else 1


async def fetch_scanner_parser_sources(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    requests = scanner_parser_requests(
        symbol=args.symbol,
        scripcode=args.scripcode,
        from_date=args.from_date,
        to_date=args.to_date,
    )
    client = AsyncEndpointClient()
    try:
        results = await client.fetch_many(requests, concurrency=args.concurrency)
    finally:
        await client.aclose()
    snapshot = normalize_and_save_disclosures(results)
    payload = {
        "status": "PASS" if any(source.parser_state == "STRUCTURED_OK" for source in snapshot.sources) else "WAIT_SOURCE",
        "sourceCount": len(results),
        "rawArchivedCount": sum(1 for result in results if result.state.value == "RAW_ARCHIVED"),
        "validEmptyCount": sum(1 for result in results if result.state.value == "NO_DATA_NOW"),
        "staleFallbackCount": sum(1 for result in results if result.state.value == "STALE_FALLBACK"),
        "brokenCount": sum(1 for result in results if result.state.value in {"BROKEN", "WRONG_CONTENT"}),
        "normalizedSourceCount": len(snapshot.sources),
        "normalizedEventCount": len(snapshot.events),
        "runId": snapshot.run_id,
        "state": snapshot.state,
        "reason": snapshot.reason,
        "sources": [source.model_dump(mode="json", by_alias=True) for source in snapshot.sources],
        "fetches": [result.model_dump(mode="json", by_alias=True) for result in results],
    }
    if args.json_report:
        report_path = Path(args.json_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        payload["jsonReport"] = str(report_path)
    return payload, 0 if payload["brokenCount"] == 0 else 1


async def fetch_intraday_stock_details(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    sector_indices = tuple(args.sector_index or DEFAULT_INTRADAY_SECTOR_INDICES)
    requests = intraday_stock_detail_requests(
        from_date=args.from_date,
        to_date=args.to_date,
        sector_indices=sector_indices,
        symbols=tuple(args.symbol or ()),
    )
    client = AsyncEndpointClient()
    try:
        results = await client.fetch_many(requests, concurrency=args.concurrency)
    finally:
        await client.aclose()
    snapshot = build_intraday_stock_detail_snapshot(results, limit=args.limit)
    save_intraday_stock_detail_snapshot(snapshot)
    payload = snapshot.model_dump(mode="json", by_alias=True)
    payload["sourceCount"] = len(results)
    payload["rawArchivedCount"] = sum(1 for result in results if result.state.value == "RAW_ARCHIVED")
    payload["validEmptyCount"] = sum(1 for result in results if result.state.value == "NO_DATA_NOW")
    payload["staleFallbackCount"] = sum(1 for result in results if result.state.value == "STALE_FALLBACK")
    payload["brokenCount"] = sum(1 for result in results if result.state.value in {"BROKEN", "WRONG_CONTENT"})
    payload["fetches"] = [result.model_dump(mode="json", by_alias=True) for result in results]
    if args.json_report:
        report_path = Path(args.json_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        payload["jsonReport"] = str(report_path)
    return payload, 0 if payload["rawArchivedCount"] > 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TrendForge local research utilities")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "init-db", help="Initialize and verify the local SQLite database"
    )
    commands.add_parser(
        "migrate", help="Apply and list versioned local schema migrations"
    )
    demo = commands.add_parser(
        "demo-data", help="Load deterministic research-only candles"
    )
    demo.add_argument("--symbol", default="TFDEMO")
    demo.add_argument("--no-parquet", action="store_true")
    commands.add_parser(
        "demo-decisions", help="Persist deterministic named-state scanner scenarios"
    )
    commands.add_parser(
        "demo-harmonic-lifecycle",
        help="Persist deterministic harmonic lifecycle transitions",
    )
    commands.add_parser(
        "source-coverage",
        help="Validate canonical source URL and active-contract coverage",
    )
    commands.add_parser(
        "benchmark-nifty50",
        help="Benchmark a cached deterministic scan over the current official Nifty 50 universe",
    )
    fetch_scanner = commands.add_parser(
        "fetch-scanner-sources",
        help="Fetch the 13-source NSE/BSE scanner parser set and save normalized disclosure evidence",
    )
    fetch_scanner.add_argument("--symbol", default="RELIANCE")
    fetch_scanner.add_argument("--scripcode", default="500325")
    fetch_scanner.add_argument("--from-date", required=True)
    fetch_scanner.add_argument("--to-date", required=True)
    fetch_scanner.add_argument("--concurrency", type=int, default=3)
    fetch_scanner.add_argument("--json-report")
    fetch_intraday = commands.add_parser(
        "fetch-intraday-stock-details",
        help="Fetch research-only OI, active derivatives, sector, BSE order-win and NSDL FPI stock-detail evidence",
    )
    fetch_intraday.add_argument("--from-date", required=True)
    fetch_intraday.add_argument("--to-date", required=True)
    fetch_intraday.add_argument("--sector-index", action="append")
    fetch_intraday.add_argument("--symbol", action="append")
    fetch_intraday.add_argument("--limit", type=int, default=25)
    fetch_intraday.add_argument("--concurrency", type=int, default=3)
    fetch_intraday.add_argument("--json-report")

    def add_market_paths(command: argparse.ArgumentParser) -> None:
        command.add_argument("--db-path", required=True)
        command.add_argument("--data-root", required=True)

    start_market = commands.add_parser(
        "start-scheduler",
        help="Run the single MD69 collector in the foreground; activation remains fail-closed",
    )
    add_market_paths(start_market)
    start_market.add_argument("--poll-seconds", type=int, default=15)

    run_snapshot = commands.add_parser(
        "run-snapshot", help="Run one named MD69 checkpoint when due"
    )
    add_market_paths(run_snapshot)
    run_snapshot.add_argument("--time", required=True, choices=("0900", "0917", "1030", "1230", "1330", "1500"))

    run_source = commands.add_parser(
        "run-source", help="Run one configured MD69 source through the guarded service"
    )
    add_market_paths(run_source)
    run_source.add_argument("--source-key", required=True)

    run_all = commands.add_parser(
        "run-all",
        help="Manually run every source in the current MD69 registry",
    )
    add_market_paths(run_all)

    run_eod = commands.add_parser(
        "run-eod", help="Run one guarded post-15:35 EOD polling cycle"
    )
    add_market_paths(run_eod)

    show_status = commands.add_parser(
        "show-status", help="Show MD69 lease, health, schedule and latest-run state"
    )
    add_market_paths(show_status)

    cleanup = commands.add_parser(
        "cleanup", help="Plan retention cleanup; deletion requires --apply"
    )
    add_market_paths(cleanup)
    cleanup_mode = cleanup.add_mutually_exclusive_group()
    cleanup_mode.add_argument("--dry-run", action="store_true")
    cleanup_mode.add_argument("--apply", action="store_true")
    def add_r16_db(command: argparse.ArgumentParser) -> None:
        command.add_argument("--db-path", required=True)

    r16_status = commands.add_parser(
        "r16-status", help="Read the R16 dataset/replay validation state"
    )
    add_r16_db(r16_status)
    r16_schema = commands.add_parser(
        "r16-schema", help="Inspect or explicitly apply the approval-gated R16 schema"
    )
    add_r16_db(r16_schema)
    r16_schema.add_argument("--apply", action="store_true")
    for command_name, help_text in (
        ("r16-build", "Run one incremental R16 replay catch-up"),
        ("r16-catch-up", "Catch up every real persisted S8 date"),
        ("r16-replay", "Append labels only where the observed path changed"),
    ):
        command = commands.add_parser(command_name, help=help_text)
        add_r16_db(command)
    r16_rebuild = commands.add_parser(
        "r16-rebuild", help="Open a new R16 dataset revision with an audit reason"
    )
    add_r16_db(r16_rebuild)
    r16_rebuild.add_argument("--reason", required=True)

    return parser


def run_r16_cli_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    from .selection.r16_service import run_incremental, status_payload
    from .selection.r16_store import apply_r16_schema, r16_schema_status

    storage.DB_PATH = Path(args.db_path)
    storage._INITIALIZED_DB_PATHS.clear()
    if args.command == "r16-status":
        return status_payload(), 0
    if args.command == "r16-schema":
        return (apply_r16_schema() if args.apply else r16_schema_status()), 0
    mode = {
        "r16-build": "incremental",
        "r16-catch-up": "catch_up",
        "r16-replay": "replay",
        "r16-rebuild": "rebuild",
    }[args.command]
    payload = run_incremental(
        mode=mode,
        rebuild_reason=getattr(args, "reason", None),
    )
    return payload, 0


def run_market_data_cli_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    from datetime import UTC, date, datetime, timedelta

    from .exchange_calendar import evaluate_nse_calendar
    from .market_data_scheduler import build_default_scheduler

    scheduler = build_default_scheduler(
        db_path=Path(args.db_path), data_root=Path(args.data_root)
    )
    now = datetime.now(UTC)
    if args.command == "start-scheduler":
        payload = asyncio.run(
            scheduler.start_foreground(poll_seconds=args.poll_seconds)
        )
        return payload, 0 if payload.get("state") == "DISABLED" else 1
    if args.command == "run-snapshot":
        result = asyncio.run(scheduler.run_snapshot(slot=args.time, at=now))
        payload = result.model_dump(mode="json")
        return payload, 0 if result.state.value in {"COMPLETED", "DISABLED", "ACTIVATION_BLOCKED", "MARKET_CLOSED"} else 1
    if args.command == "run-source":
        payload = asyncio.run(scheduler.run_source(args.source_key, at=now))
        return payload, 0 if payload.get("state") in {"DISABLED", "ACTIVATION_BLOCKED"} else 1
    if args.command == "run-all":
        result = asyncio.run(scheduler.run_all(at=now))
        payload = result.model_dump(mode="json")
        return payload, 0 if result.state.value in {
            "COMPLETED", "DISABLED", "ACTIVATION_BLOCKED", "LEASE_HELD"
        } else 1
    if args.command == "run-eod":
        result = asyncio.run(scheduler.run_eod(at=now))
        payload = result.model_dump(mode="json")
        return payload, 0 if result.state.value in {"COMPLETED", "DISABLED", "ACTIVATION_BLOCKED", "MARKET_CLOSED", "WAITING_FOR_EOD"} else 1
    if args.command == "show-status":
        return scheduler.status(), 0
    completed: list[date] = []
    cursor = now.date() - timedelta(days=1)
    for _ in range(20):
        state = evaluate_nse_calendar(cursor)
        if state.get("isTradingDay"):
            completed.append(cursor)
        cursor -= timedelta(days=1)
        if len(completed) >= 10:
            break
    report = scheduler.store.cleanup_retention(
        as_of_date=now.date(),
        completed_trading_days=completed,
        dry_run=not bool(args.apply),
    )
    return report.model_dump(mode="json"), 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init-db":
            _print(init_database())
            return 0
        if args.command == "migrate":
            _print(migrate_database())
            return 0
        if args.command == "demo-data":
            _print(
                load_demo_data(symbol=args.symbol, write_parquet=not args.no_parquet)
            )
            return 0
        if args.command == "demo-decisions":
            _print(load_demo_decision_run())
            return 0
        if args.command == "demo-harmonic-lifecycle":
            _print(load_lifecycle_fixture_events())
            return 0
        if args.command == "benchmark-nifty50":
            members = storage.list_index_constituents("NIFTY50", limit=100)
            report = benchmark_cached_nifty50([str(row["symbol"]) for row in members])
            _print(report)
            return 0 if report["status"] == "PASS" else 1
        if args.command == "fetch-scanner-sources":
            payload, status = asyncio.run(fetch_scanner_parser_sources(args))
            _print(payload)
            return status
        if args.command == "fetch-intraday-stock-details":
            payload, status = asyncio.run(fetch_intraday_stock_details(args))
            _print(payload)
            return status
        if args.command in MARKET_DATA_COMMANDS:
            payload, status = run_market_data_cli_command(args)
            _print(payload)
            return status
        if args.command in R16_COMMANDS:
            payload, status = run_r16_cli_command(args)
            _print(payload)
            return status
        payload, status = validate_source_coverage()
        _print(payload)
        return status
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        _print({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
