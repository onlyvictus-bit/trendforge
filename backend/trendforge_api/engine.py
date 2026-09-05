from __future__ import annotations

import logging
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from .mock_data import RADAR_CANDIDATES, SOURCE_HEALTH
from .models import (
    CandidateType,
    CommandBar,
    RadarCandidate,
    SourceHealth,
    SourceParseResult,
    SourceSnapshotRecord,
    SourceState,
    StatusGroup,
)
from .exchange_calendar import evaluate_nse_calendar
from .parsers.source_freshness import is_data_date_fresh
from .safety_engine import evaluate_safety_status
from .source_inventory_compiler import DEFAULT_WORKBOOK, compile_default_inventory
from .source_monitor import SOURCE_CATALOG
from .storage import (
    latest_market_context_snapshot,
    list_scanner_candidates,
    list_scanner_runs,
    list_source_parse_results,
    list_source_snapshots,
)


LOGGER = logging.getLogger("trendforge.engine")
IST = ZoneInfo("Asia/Kolkata")


def demo_mode_enabled() -> bool:
    return os.getenv("TRENDFORGE_DEMO_MODE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _latest_real_candidates() -> list[RadarCandidate]:
    runs = list_scanner_runs(limit=1)
    if not runs or not runs[0].get("candidate_count"):
        return []
    rows = list_scanner_candidates(run_id=int(runs[0]["id"]), limit=1000)
    by_symbol: dict[str, RadarCandidate] = {}
    for row in rows:
        try:
            candidate = RadarCandidate.model_validate(row["payload"])
        except Exception as exc:
            LOGGER.warning(
                "invalid_scanner_candidate_skipped candidate_id=%s error=%s",
                row.get("id"),
                exc,
            )
            continue
        current = by_symbol.get(candidate.symbol)
        if current is None or candidate.quality > current.quality:
            by_symbol[candidate.symbol] = candidate
    return list(by_symbol.values())


def list_candidates(
    mode: CandidateType | None = None,
    status: StatusGroup | None = None,
    timeframe: str | None = None,
    search: str | None = None,
) -> list[RadarCandidate]:
    rows = _latest_real_candidates()
    if not rows and demo_mode_enabled():
        rows = RADAR_CANDIDATES

    if mode is not None:
        rows = [row for row in rows if row.type == mode]

    if status is not None:
        rows = [row for row in rows if row.status_group == status]

    if timeframe:
        rows = [row for row in rows if timeframe in row.timeframe]

    if search:
        needle = search.casefold().strip()
        rows = [
            row
            for row in rows
            if needle
            in " ".join([row.symbol, row.state, row.setup, row.reason]).casefold()
        ]

    return rows


def get_candidate(symbol: str) -> RadarCandidate | None:
    normalized = symbol.casefold().replace("%20", " ")
    rows = _latest_real_candidates()
    if not rows and demo_mode_enabled():
        rows = RADAR_CANDIDATES
    for row in rows:
        if row.symbol.casefold() == normalized:
            return row
    return None


def _workbook_signature() -> tuple[int, int]:
    path = Path(DEFAULT_WORKBOOK)
    try:
        stat = path.stat()
        return (int(stat.st_mtime_ns), int(stat.st_size))
    except OSError:
        return (0, 0)


@lru_cache(maxsize=4)
def _compiler_maturity_context(
    workbook_signature: tuple[int, int],
) -> tuple[dict[str, tuple[str, bool]], bool]:
    """Map source_key -> (maturityState, gatePermission) + global activation flag.

    GREEN operational health is not maturity and never means activation-ready.
    """
    del workbook_signature  # cache key only
    report = compile_default_inventory()
    by_key: dict[str, tuple[str, bool]] = {}
    for contract in report.source_contracts:
        by_key[contract.source_contract_id] = (
            contract.maturity_state.value,
            bool(contract.gate_permission),
        )
    return by_key, bool(report.source_activation_ready)


def list_source_health() -> list[SourceHealth]:
    if demo_mode_enabled():
        return SOURCE_HEALTH
    snapshots_by_source: dict[str, list[SourceSnapshotRecord]] = {}
    for source_snapshot in list_source_snapshots(limit=10_000):
        snapshots_by_source.setdefault(source_snapshot.source_key, []).append(
            source_snapshot
        )
    parses_by_source: dict[str, list[SourceParseResult]] = {}
    for source_parse in list_source_parse_results(limit=10_000):
        parses_by_source.setdefault(source_parse.source_key, []).append(source_parse)

    try:
        maturity_by_key, activation_ready = _compiler_maturity_context(
            _workbook_signature()
        )
    except Exception:
        logging.getLogger(__name__).exception(
            "source-health maturity join failed; continuing without ladder fields"
        )
        maturity_by_key, activation_ready = {}, False

    rows: list[SourceHealth] = []
    for descriptor in SOURCE_CATALOG:
        snapshots = snapshots_by_source.get(descriptor.key, [])
        snapshot = snapshots[0] if snapshots else None
        parses = parses_by_source.get(descriptor.key, [])
        parsed = parses[0] if parses else None
        structured = next(
            (item for item in parses if item.parser_state == "PARSED_STRUCTURED"),
            None,
        )
        successful = next(
            (
                item
                for item in snapshots
                if item.check_state not in {"BROKEN", "SKIPPED"} and item.content_hash
            ),
            None,
        )
        consecutive_failures = 0
        for item in snapshots:
            if item.check_state == "SKIPPED":
                continue
            if item.check_state != "BROKEN":
                break
            consecutive_failures += 1
        if snapshot and snapshot.check_state == "BROKEN":
            state = SourceState.RED
        elif structured:
            state = (
                SourceState.GREEN
                if is_data_date_fresh(descriptor.key, structured.data_date)
                else SourceState.AMBER
            )
        elif snapshot or parsed:
            state = SourceState.AMBER
        else:
            state = SourceState.NA
        maturity_state, gate_permission = maturity_by_key.get(
            descriptor.key, (None, False)
        )
        rows.append(
            SourceHealth(
                name=descriptor.name,
                owner=descriptor.authority.value,
                state=state,
                trustLabel=descriptor.authority.value,
                updateFrequency=descriptor.expected_frequency,
                latestDataDate=(
                    structured.data_date
                    if structured and structured.data_date
                    else parsed.data_date
                    if parsed and parsed.data_date
                    else snapshot.last_modified
                    if snapshot and snapshot.last_modified
                    else "UNAVAILABLE"
                ),
                decisionUse=descriptor.decision_use,
                url=snapshot.url if snapshot else descriptor.url,
                lastAttemptedAt=snapshot.checked_at if snapshot else None,
                lastSuccessfulAt=successful.checked_at if successful else None,
                consecutiveFailures=consecutive_failures,
                staleThresholdHours=descriptor.stale_after_hours,
                limitation=descriptor.limitation,
                sourceKey=descriptor.key,
                maturityState=maturity_state,
                gatePermission=gate_permission,
                sourceActivationReady=activation_ready,
            )
        )
    return rows


def current_command_bar() -> CommandBar:
    context = latest_market_context_snapshot()
    safety = evaluate_safety_status()
    calendar = evaluate_nse_calendar()
    now = datetime.now(IST)
    liquidity_active = bool(
        calendar["isTradingDay"]
        and (now.hour, now.minute) >= (9, 15)
        and (now.hour, now.minute) <= (15, 30)
    )
    market_state = str(context.get("state")) if context else "WAIT_CONTEXT"
    vix = (
        f"{context.get('indiaVix')} {context.get('vixState')}"
        if context
        else "WAIT_DATA"
    )
    no_trade = (
        safety.state
        if safety.state in {"LOCKED_NO_TRADE", "STOP_TRADING_NOW"}
        else "NO_TRADE"
        if market_state == "NO_TRADE"
        else "OFF"
    )
    return CommandBar(
        system="RESEARCH_ONLY",
        regime=market_state,
        indiaVix=vix,
        safety=safety.state,
        liquidityWindow="ACTIVE" if liquidity_active else "CLOSED",
        expiryMode="UNKNOWN",
        noTradeOverride=no_trade,
    )
