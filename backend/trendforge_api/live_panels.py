from __future__ import annotations

import asyncio
import inspect
import json
import os
import sqlite3
from copy import deepcopy
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from .exchange_calendar import evaluate_nse_calendar
from .institutional_sources import (
    DEFAULT_CACHE_DB,
    ENDPOINTS,
    AsyncEndpointClient,
    EndpointFetchResult,
    FetchState,
)
from .parsers.nse_large_deals_parser import parse_nse_large_deals_snapshot
from .parsers.surveillance_pledge_fpi_parser import parse_nse_oi_spurts


IST = ZoneInfo("Asia/Kolkata")
CONTRACT = "trendforge.livePanels.v1"
DEFAULT_MAX_AGE_SEC = 300
MAX_ROWS_PER_SOURCE = 500
MAX_TOTAL_ROWS = 10_000
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024

P0_SOURCE_KEYS: tuple[str, ...] = (
    "nse_variations_gainers",
    "nse_variations_loosers",
    "nse_volume_gainers",
    "nse_most_active_volume",
    "nse_most_active_value",
    "nse_all_indices",
    "nse_oi_spurts",
    "nse_most_active_underlying",
    "nse_large_deals_snapshot",
    "nse_preopen_fo",
)

# These already-normalized MD69 sources are useful after close, but they never
# satisfy the intraday P0 freshness gate or turn a panel LIVE.
CLOSED_RESEARCH_SOURCE_KEYS: tuple[str, ...] = (
    "nse_bhavcopy_eod",
    "nse_large_deals",
    "nse_trade_to_trade",
    "nse_board_meetings",
    "nse_most_active_futures",
    "nse_most_active_options",
    "nse_ipo_issue_calendar",
    "nse_pr_market_snapshot",
    # Phase-1 from 30-pack (EOD / research overlay — never invent LIVE alone)
    "nse_fno_ban",
    "nse_participant_oi",
    "nse_mto_delivery",
    "nse_short_selling",
    "bse_fo_bhavcopy",
    "amfi_nav",
    "nse_preopen_cash",
    # Phase-2 from 30-pack
    "bse_insider_trading",
    "nse_option_chain_nifty",
    "nse_option_chain_banknifty",
    "lbma_gold_silver_fix",
    "eia_natgas_storage",
    "usda_wasde_cornell",
    "nse_fii_derivatives_stats",
    # Phase-3 multi-step / remaining pack
    "rbi_fbil_usdinr",
    "nse_index_option_chain_v3",
    "cdsl_fpi_fortnightly",
    "dgcis_trade_data",
    # Finish set — full 30-pack remainder
    "yahoo_cme_proxy",
    "yahoo_lme_proxy",
    "mcx_market_watch",
    "mcx_option_chain",
    "mcx_top_participants",
    "mcx_warehouse_stocks",
    "mcx_delivery_reports",
    "ncdex_bhavcopy",
    "amfi_portfolio_disclosure",
    "nse_bulk_deals_today_csv",
    "nse_bulk_deal_symbol",
    "nse_quote_equity_trade_info",
    "screener_in_fii_holding_change",
    "tickertape_fii_holding_change_3m",
    "dhan_fii_holding_change",
    "equitymaster_fii_buys_reference",
)
PANEL_OVERLAY_SOURCE_KEYS: tuple[str, ...] = tuple(
    dict.fromkeys((*P0_SOURCE_KEYS, *CLOSED_RESEARCH_SOURCE_KEYS))
)

INTRADAY_SOURCE_KEYS = frozenset(P0_SOURCE_KEYS) - {
    "nse_large_deals_snapshot",
    "nse_preopen_fo",
}
PANEL_CRITICAL_SOURCES: dict[str, tuple[str, ...]] = {
    "sector": ("nse_all_indices",),
    "consensus": (
        "nse_variations_gainers",
        "nse_variations_loosers",
        "nse_volume_gainers",
    ),
    "screener": (
        "nse_variations_gainers",
        "nse_variations_loosers",
        "nse_volume_gainers",
        "nse_most_active_volume",
        "nse_most_active_value",
    ),
}
PANEL_RESEARCH_SOURCES: dict[str, tuple[str, ...]] = {
    "sector": ("nse_all_indices",),
    "consensus": (
        "nse_variations_gainers",
        "nse_variations_loosers",
        "nse_volume_gainers",
        "nse_large_deals",
        "nse_large_deals_snapshot",
    ),
    "screener": (
        "nse_variations_gainers",
        "nse_variations_loosers",
        "nse_volume_gainers",
        "nse_most_active_volume",
        "nse_most_active_value",
        *CLOSED_RESEARCH_SOURCE_KEYS,
    ),
}


def _enabled_from_env() -> bool:
    value = os.getenv("TRENDFORGE_LIVE_PANELS_ENABLED", "false")
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.astimezone(IST).date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=IST).astimezone(UTC)
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("T", " ").removesuffix("Z")
    for fmt in (
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(normalized, fmt).replace(tzinfo=IST).astimezone(UTC)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=IST).astimezone(UTC)


def evaluate_live_market_session(
    at: datetime | None = None,
    *,
    calendar_evaluator: Callable[[datetime], dict[str, Any]] = evaluate_nse_calendar,
) -> dict[str, Any]:
    instant = at or datetime.now(UTC)
    instant = instant.replace(tzinfo=UTC) if instant.tzinfo is None else instant.astimezone(UTC)
    local = instant.astimezone(IST)
    calendar = calendar_evaluator(instant)
    calendar_state = str(calendar.get("state") or "WAIT_CALENDAR_DATA")
    trading_date = str(calendar.get("tradingDate") or local.date().isoformat())

    if calendar_state == "WAIT_CALENDAR_DATA":
        session = "WAIT_CALENDAR"
    elif not calendar.get("isTradingDay"):
        session = "MARKET_CLOSED"
    elif calendar_state == "OPEN_SPECIAL":
        # Special-session times must come from an official structured record.
        session = "WAIT_SPECIAL_SESSION_TIMES"
    elif local.time() < time(9, 0):
        session = "PRE_MARKET"
    elif local.time() < time(9, 15):
        session = "PRE_OPEN"
    elif local.time() < time(15, 30):
        session = "OPEN"
    else:
        session = "MARKET_CLOSED"

    return {
        "exchange": "NSE",
        "timezone": "Asia/Kolkata",
        "tradingDate": trading_date,
        "session": session,
        "calendarState": calendar_state,
        "reason": calendar.get("reason"),
    }


def _source_rows(key: str, payload: Any) -> tuple[list[dict[str, Any]], Any, str]:
    if not isinstance(payload, dict):
        return [], None, "WAIT_SCHEMA_MISMATCH"

    if key in {"nse_variations_gainers", "nse_variations_loosers"}:
        section = payload.get("allSec")
        if not isinstance(section, dict):
            return [], None, "WAIT_SCHEMA_MISMATCH"
        section_rows = section.get("data")
        normalized_rows = (
            [row for row in section_rows if isinstance(row, dict)]
            if isinstance(section_rows, list)
            else []
        )
        return normalized_rows, section.get("timestamp"), "PARSED_LIVE_ADAPTER"

    if key == "nse_oi_spurts":
        parsed = parse_nse_oi_spurts(_json_bytes(payload))
        oi_rows = payload.get("data")
        normalized_rows = (
            [row for row in oi_rows if isinstance(row, dict)]
            if isinstance(oi_rows, list)
            else []
        )
        return (
            normalized_rows,
            payload.get("timestamp"),
            str(parsed.get("parser_state") or "WAIT_SCHEMA_MISMATCH"),
        )

    if key == "nse_large_deals_snapshot":
        parsed = parse_nse_large_deals_snapshot(_json_bytes(payload))
        output = parsed.get("output") if isinstance(parsed, dict) else None
        source_rows = output.get("rows") if isinstance(output, dict) else []
        deal_rows: list[dict[str, Any]] = []
        for source in source_rows if isinstance(source_rows, list) else []:
            if not isinstance(source, dict):
                continue
            quantity = source.get("quantity")
            price = source.get("price")
            side = str(source.get("side") or "").upper()
            deal_rows.append(
                {
                    **source,
                    "side": side,
                    "buySell": side,
                    "qty": quantity,
                    "watp": price,
                }
            )
        return (
            deal_rows,
            payload.get("as_on_date"),
            str(parsed.get("parser_state") or "WAIT_SCHEMA_MISMATCH"),
        )

    generic_rows = payload.get("data")
    normalized_rows = (
        [row for row in generic_rows if isinstance(row, dict)]
        if isinstance(generic_rows, list)
        else []
    )
    return normalized_rows, payload.get("timestamp"), "PARSED_LIVE_ADAPTER"


def normalize_live_result(
    result: EndpointFetchResult,
    *,
    now: datetime | None = None,
    market_trading_date: str,
    max_age_sec: int = DEFAULT_MAX_AGE_SEC,
) -> dict[str, Any]:
    instant = now or datetime.now(UTC)
    instant = instant.replace(tzinfo=UTC) if instant.tzinfo is None else instant.astimezone(UTC)
    key = result.endpoint_key
    rows, observed_value, parser_state = _source_rows(key, result.payload)
    source_row_count = len(rows)
    truncated = source_row_count > MAX_ROWS_PER_SOURCE
    rows = rows[:MAX_ROWS_PER_SOURCE]

    observed_at = _parse_timestamp(observed_value)
    observed_date = _parse_date(observed_value)
    if key == "nse_large_deals_snapshot":
        data_date = observed_date
        # Date is authoritative; fetchedAt is the observation time for age display.
        observed_at = result.fetched_at.astimezone(UTC)
    else:
        data_date = observed_at.astimezone(IST).date() if observed_at else observed_date
    if data_date is None:
        data_date = result.fetched_at.astimezone(IST).date()
    if observed_at is None:
        observed_at = result.fetched_at.astimezone(UTC)

    age_sec = max(0, int((instant - observed_at).total_seconds()))
    future_sec = int((observed_at - instant).total_seconds())
    fetch_usable = result.state in {FetchState.RAW_ARCHIVED, FetchState.NO_DATA_NOW}
    wrong_day = data_date.isoformat() != market_trading_date
    market_date = _parse_date(market_trading_date)
    research_eligible = bool(rows) and future_sec <= 120 and (
        market_date is None or data_date <= market_date
    )

    reason: str | None = result.reason
    if future_sec > 120:
        state, reason = "QUARANTINED", "dataAsOf is more than two minutes in the future"
    elif wrong_day:
        state, reason = "QUARANTINED", "tradingDate does not match the current NSE session"
    elif not fetch_usable:
        state, reason = "STALE", result.reason or f"fetch state {result.state.value} is not live-eligible"
    elif parser_state != "PARSED_STRUCTURED" and parser_state != "PARSED_LIVE_ADAPTER":
        state, reason = "QUARANTINED", f"parser state {parser_state} is not usable"
    elif not rows:
        state, reason = "EMPTY", "normalized live adapter produced no records"
    elif key in INTRADAY_SOURCE_KEYS and age_sec > max_age_sec:
        state, reason = "STALE", f"source age {age_sec}s exceeds {max_age_sec}s"
    elif key == "nse_preopen_fo":
        state = "SESSION_CONTEXT"
    elif key == "nse_large_deals_snapshot":
        state = "TRADING_DAY_CONTEXT"
    else:
        state = "FRESH"

    eligible = state in {
        "FRESH",
        "SESSION_CONTEXT",
        "TRADING_DAY_CONTEXT",
    } and bool(rows)
    return {
        "sourceKey": key,
        "sourceUrl": result.url,
        "fetchState": result.state.value,
        "state": state,
        "eligible": eligible,
        "researchEligible": research_eligible,
        "freshnessClass": (
            "TRADING_DAY" if key == "nse_large_deals_snapshot" else "SESSION" if key == "nse_preopen_fo" else "INTRADAY_300"
        ),
        "tradingDate": data_date.isoformat(),
        "dataAsOf": observed_at.isoformat(),
        "fetchedAt": result.fetched_at.astimezone(UTC).isoformat(),
        "ageSec": age_sec,
        "parserState": parser_state,
        "sourceRowCount": source_row_count,
        "normalizedRowCount": len(rows),
        "recordsSample": rows,
        "truncated": truncated,
        "contentHash": result.content_hash,
        "reason": reason,
    }


def _panel_state(
    panel: str,
    sources: dict[str, dict[str, Any]],
    session: str,
) -> dict[str, Any]:
    required = PANEL_CRITICAL_SOURCES[panel]
    fresh = [key for key in required if sources.get(key, {}).get("eligible")]
    missing = [key for key in required if key not in fresh]
    research = [
        key
        for key in PANEL_RESEARCH_SOURCES[panel]
        if sources.get(key, {}).get("researchEligible")
    ]

    if session == "PRE_OPEN":
        state = "PRE_OPEN"
    elif session == "MARKET_CLOSED":
        state = "MARKET_CLOSED"
    elif session != "OPEN":
        state = "WAIT"
    elif len(fresh) == len(required):
        state = "LIVE"
    elif fresh:
        state = "PARTIAL"
    else:
        state = "STALE"
    return {
        "state": state,
        "requiredSources": list(required),
        "freshSources": fresh,
        "researchSources": research,
        "researchSourceCandidates": list(PANEL_RESEARCH_SOURCES[panel]),
        "missingOrStaleSources": missing,
        "maxAgeSec": DEFAULT_MAX_AGE_SEC,
    }


def build_live_snapshot(
    sources: dict[str, dict[str, Any]],
    *,
    now: datetime | None = None,
    market: dict[str, Any],
    max_age_sec: int = DEFAULT_MAX_AGE_SEC,
    refresh_state: str = "READY",
) -> dict[str, Any]:
    instant = now or datetime.now(UTC)
    instant = instant.replace(tzinfo=UTC) if instant.tzinfo is None else instant.astimezone(UTC)
    session = str(market.get("session") or "WAIT_CALENDAR")
    panels = {name: _panel_state(name, sources, session) for name in PANEL_CRITICAL_SOURCES}
    for panel in panels.values():
        panel["maxAgeSec"] = max_age_sec

    remaining = MAX_TOTAL_ROWS
    overlay: list[dict[str, Any]] = []
    overlay_keys = tuple(
        dict.fromkeys((*PANEL_OVERLAY_SOURCE_KEYS, *sorted(sources)))
    )
    for key in overlay_keys:
        source = sources.get(key)
        source_allowed = bool(source) and bool(
            source.get("eligible") or source.get("researchEligible")
        )
        if not source_allowed or remaining <= 0:
            continue
        research_only = session not in {"OPEN", "PRE_OPEN"} or not source.get("eligible")
        source_limit = (
            remaining
            if key in PANEL_OVERLAY_SOURCE_KEYS
            else min(MAX_ROWS_PER_SOURCE, remaining)
        )
        records = list(source.get("recordsSample") or [])[:source_limit]
        remaining -= len(records)
        overlay.append(
            {
                "active_source_keys": key,
                "source_key": key,
                "records_sample": records,
                "records_scope": (
                    "saved_research_records"
                    if research_only
                    else "live_normalized_records"
                ),
                "data_date": source.get("tradingDate"),
                "fetched_at": source.get("fetchedAt"),
                "source_row_count": source.get("sourceRowCount", 0),
                "normalized_row_count": len(records),
                "live_source_status": (
                    "RESEARCH_ONLY" if research_only else source.get("state")
                ),
            }
        )

    source_diagnostics = {
        key: {field: value for field, value in source.items() if field != "recordsSample"}
        for key, source in sources.items()
    }
    snapshot: dict[str, Any] = {
        "contract": CONTRACT,
        "snapshotId": str(uuid4()),
        "generatedAt": instant.isoformat(),
        "market": market,
        "refresh": {"state": refresh_state, "maxAgeSec": max_age_sec},
        "panelVersions": {"sector": "1", "consensus": "4", "screener": "1.3"},
        "panels": panels,
        "sources": source_diagnostics,
        "inventoryOverlay": overlay,
        "sourceActivationReady": False,
    }
    response_truncated = False
    while len(_json_bytes(snapshot)) > MAX_SNAPSHOT_BYTES:
        response_truncated = True
        changed = False
        for row in overlay:
            records = row["records_sample"]
            if len(records) > 1:
                row["records_sample"] = records[: max(1, len(records) // 2)]
                row["normalized_row_count"] = len(row["records_sample"])
                changed = True
        if not changed:
            for row in reversed(overlay):
                if row["records_sample"]:
                    row["records_sample"] = []
                    row["normalized_row_count"] = 0
                    changed = True
                    break
        if not changed:
            break
    if response_truncated:
        snapshot["refresh"]["responseTruncated"] = True
        for panel in snapshot["panels"].values():
            if panel["state"] == "LIVE":
                panel["state"] = "PARTIAL"
    snapshot["responseBytes"] = len(_json_bytes(snapshot))
    return snapshot


def _disabled_snapshot(now: datetime, market: dict[str, Any], max_age_sec: int) -> dict[str, Any]:
    snapshot = build_live_snapshot({}, now=now, market=market, max_age_sec=max_age_sec, refresh_state="WAIT_DISABLED")
    for panel in snapshot["panels"].values():
        panel["state"] = "WAIT"
    return snapshot


class LivePanelsService:
    def __init__(
        self,
        *,
        db_path: Path = DEFAULT_CACHE_DB,
        client_factory: Callable[[], Any] | None = None,
        enabled: bool | None = None,
        calendar_evaluator: Callable[[datetime], dict[str, Any]] = evaluate_nse_calendar,
        canonical_source_provider: Callable[..., Any] | None = None,
    ) -> None:
        self._db_path = Path(db_path)
        self._client_factory = client_factory or (lambda: AsyncEndpointClient(cache_db=self._db_path))
        self._enabled = _enabled_from_env() if enabled is None else enabled
        self._calendar_evaluator = calendar_evaluator
        self._canonical_source_provider = canonical_source_provider
        self._lock = asyncio.Lock()
        self._latest: dict[str, Any] | None = None
        self._last_completed_generation = 0
        self._consecutive_widespread_failures = 0
        self._breaker_trip_count = 0
        self._breaker_until: datetime | None = None
        self._source_failure_counts: dict[str, int] = {}
        self._source_quarantine_until: dict[str, datetime] = {}
        self._scheduler_task: asyncio.Task[None] | None = None
        self._scheduler_stop = asyncio.Event()

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize_projection(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS live_panel_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    generated_at TEXT NOT NULL,
                    trading_date TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cutoff = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
            connection.execute("DELETE FROM live_panel_snapshots WHERE generated_at < ?", (cutoff,))

    def _save(self, snapshot: dict[str, Any]) -> None:
        self._initialize_projection()
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO live_panel_snapshots(snapshot_id, generated_at, trading_date, payload_json) VALUES (?, ?, ?, ?)",
                (
                    snapshot["snapshotId"],
                    snapshot["generatedAt"],
                    snapshot["market"]["tradingDate"],
                    json.dumps(snapshot, ensure_ascii=True, separators=(",", ":"), default=str),
                ),
            )

    @staticmethod
    def _failed_fetch(result: EndpointFetchResult) -> bool:
        return result.state in {
            FetchState.STALE_FALLBACK,
            FetchState.WRONG_CONTENT,
            FetchState.BROKEN,
        }

    def _circuit_snapshot(
        self,
        *,
        instant: datetime,
        market: dict[str, Any],
        max_age_sec: int,
    ) -> dict[str, Any]:
        if self._latest is None:
            snapshot = build_live_snapshot(
                {},
                now=instant,
                market=market,
                max_age_sec=max_age_sec,
                refresh_state="CIRCUIT_OPEN",
            )
        else:
            snapshot = deepcopy(self._latest)
            snapshot["snapshotId"] = str(uuid4())
            snapshot["generatedAt"] = instant.isoformat()
            snapshot["market"] = market
            snapshot["refresh"] = {
                "state": "CIRCUIT_OPEN",
                "maxAgeSec": max_age_sec,
                "retryAfter": self._breaker_until.isoformat() if self._breaker_until else None,
            }
            for row in snapshot.get("inventoryOverlay") or []:
                row["records_scope"] = "saved_research_records"
                row["live_source_status"] = "RESEARCH_ONLY"
        for panel in snapshot["panels"].values():
            panel["state"] = "STALE"
        return snapshot

    def _latest_for_market(
        self,
        *,
        instant: datetime,
        market: dict[str, Any],
        max_age_sec: int,
    ) -> dict[str, Any] | None:
        if self._latest is None:
            return None
        snapshot = deepcopy(self._latest)
        snapshot["snapshotId"] = str(uuid4())
        snapshot["generatedAt"] = instant.isoformat()
        snapshot["market"] = market
        diagnostics = snapshot.get("sources") or {}
        for source in diagnostics.values():
            observed = _parse_timestamp(source.get("dataAsOf"))
            if observed is not None:
                source["ageSec"] = max(0, int((instant - observed).total_seconds()))
            wrong_day = source.get("tradingDate") != market.get("tradingDate")
            too_old = (
                source.get("freshnessClass") == "INTRADAY_300"
                and source.get("ageSec", max_age_sec + 1) > max_age_sec
            )
            if wrong_day or too_old:
                source["eligible"] = False
                source["state"] = "QUARANTINED" if wrong_day else "STALE"
        snapshot["panels"] = {
            name: _panel_state(name, diagnostics, str(market.get("session")))
            for name in PANEL_CRITICAL_SOURCES
        }
        eligible_keys = {
            key
            for key, source in diagnostics.items()
            if source.get("eligible") or source.get("researchEligible")
        }
        snapshot["inventoryOverlay"] = [
            row
            for row in snapshot.get("inventoryOverlay") or []
            if row.get("source_key") in eligible_keys
        ]
        for row in snapshot["inventoryOverlay"]:
            source = diagnostics.get(str(row.get("source_key") or ""), {})
            if market["session"] not in {"OPEN", "PRE_OPEN"} or not source.get("eligible"):
                row["records_scope"] = "saved_research_records"
                row["live_source_status"] = "RESEARCH_ONLY"
        snapshot["refresh"] = {
            "state": "CACHE",
            "maxAgeSec": max_age_sec,
        }
        if market["session"] not in {"OPEN", "PRE_OPEN"}:
            snapshot["refresh"] = {
                "state": "CACHE_RESEARCH" if snapshot["inventoryOverlay"] else "WAIT_SESSION",
                "maxAgeSec": max_age_sec,
            }
            for panel in snapshot["panels"].values():
                panel["state"] = (
                    "MARKET_CLOSED"
                    if market["session"] == "MARKET_CLOSED"
                    else "WAIT"
                )
        return snapshot

    def _update_safety_state(
        self,
        results: list[EndpointFetchResult],
        normalized: dict[str, dict[str, Any]],
        *,
        instant: datetime,
    ) -> bool:
        widespread_failures = sum(self._failed_fetch(row) for row in results)
        if widespread_failures >= max(5, len(results) // 2):
            self._consecutive_widespread_failures += 1
        else:
            self._consecutive_widespread_failures = 0

        for key, source in normalized.items():
            if source["state"] in {
                "FRESH",
                "SESSION_CONTEXT",
                "TRADING_DAY_CONTEXT",
                "EMPTY",
            }:
                self._source_failure_counts[key] = 0
                self._source_quarantine_until.pop(key, None)
                continue
            count = self._source_failure_counts.get(key, 0) + 1
            self._source_failure_counts[key] = count
            if count >= 3:
                self._source_quarantine_until[key] = instant + timedelta(minutes=10)

        if self._consecutive_widespread_failures < 3:
            return False
        self._breaker_trip_count += 1
        pause_minutes = 15 if self._breaker_trip_count == 1 else 30
        self._breaker_until = instant + timedelta(minutes=pause_minutes)
        self._consecutive_widespread_failures = 0
        return True

    def start(self, *, interval_sec: int = 120) -> None:
        if (
            not self._enabled
            or self._scheduler_task is not None
            or self._canonical_source_provider is not None
        ):
            return
        self._scheduler_stop.clear()

        async def run() -> None:
            while not self._scheduler_stop.is_set():
                instant = datetime.now(UTC)
                market = evaluate_live_market_session(
                    instant, calendar_evaluator=self._calendar_evaluator
                )
                if market["session"] in {"OPEN", "PRE_OPEN"}:
                    try:
                        await self.get_snapshot(refresh=True, now=instant)
                    except Exception:
                        # The API remains fail-closed and can continue serving cache.
                        pass
                try:
                    await asyncio.wait_for(
                        self._scheduler_stop.wait(), timeout=max(30, interval_sec)
                    )
                except TimeoutError:
                    continue

        self._scheduler_task = asyncio.create_task(run(), name="trendforge-live-panels")

    async def stop(self) -> None:
        self._scheduler_stop.set()
        if self._scheduler_task is not None:
            await self._scheduler_task
            self._scheduler_task = None

    async def get_snapshot(
        self,
        *,
        refresh: bool = True,
        force: bool = False,
        now: datetime | None = None,
        max_age_sec: int = DEFAULT_MAX_AGE_SEC,
    ) -> dict[str, Any]:
        instant = now or datetime.now(UTC)
        instant = instant.replace(tzinfo=UTC) if instant.tzinfo is None else instant.astimezone(UTC)
        # The live-fetch kill switch must never construct the legacy network
        # client, but it must not hide a hash-verified MD69 manifest that was
        # already downloaded and committed by the collector.
        if not self._enabled and self._canonical_source_provider is None:
            market = {
                "exchange": "NSE",
                "timezone": "Asia/Kolkata",
                "tradingDate": instant.astimezone(IST).date().isoformat(),
                "session": "WAIT_DISABLED",
                "calendarState": "NOT_EVALUATED",
                "reason": "TRENDFORGE_LIVE_PANELS_ENABLED is false",
            }
            return _disabled_snapshot(instant, market, max_age_sec)
        market = evaluate_live_market_session(instant, calendar_evaluator=self._calendar_evaluator)
        if self._breaker_until is not None and instant < self._breaker_until:
            return self._circuit_snapshot(
                instant=instant, market=market, max_age_sec=max_age_sec
            )
        if not refresh and self._latest is not None:
            cached = self._latest_for_market(
                instant=instant, market=market, max_age_sec=max_age_sec
            )
            assert cached is not None
            return cached

        generation_seen = self._last_completed_generation
        async with self._lock:
            if self._latest is not None and self._last_completed_generation != generation_seen:
                return self._latest
            if self._latest is not None and not force and market["session"] == "OPEN":
                generated = datetime.fromisoformat(self._latest["generatedAt"])
                if (instant - generated).total_seconds() <= max_age_sec:
                    return self._latest
            if not refresh:
                return self._latest or build_live_snapshot({}, now=instant, market=market, max_age_sec=max_age_sec, refresh_state="WAIT_NO_CACHE")
            if (
                market["session"] not in {"OPEN", "PRE_OPEN"}
                and not force
                and self._canonical_source_provider is None
            ):
                if self._latest is not None:
                    cached = self._latest_for_market(
                        instant=instant, market=market, max_age_sec=max_age_sec
                    )
                    assert cached is not None
                    return cached
                return build_live_snapshot({}, now=instant, market=market, max_age_sec=max_age_sec, refresh_state="WAIT_SESSION")

            if self._canonical_source_provider is not None:
                try:
                    provided = self._canonical_source_provider(
                        now=instant,
                        market_trading_date=market["tradingDate"],
                        max_age_sec=max_age_sec,
                        source_keys=(
                            PANEL_OVERLAY_SOURCE_KEYS
                            if market["session"] == "MARKET_CLOSED"
                            else P0_SOURCE_KEYS
                        ),
                        research_source_keys=CLOSED_RESEARCH_SOURCE_KEYS,
                        include_all_sources=True,
                        supporting_sample_limit=10,
                    )
                    normalized = (
                        await provided if inspect.isawaitable(provided) else provided
                    )
                    canonical_state = "CANONICAL_MANIFEST"
                except Exception:
                    normalized = {}
                    canonical_state = "CANONICAL_MANIFEST_FAILED"
                snapshot = build_live_snapshot(
                    normalized,
                    now=instant,
                    market=market,
                    max_age_sec=max_age_sec,
                    refresh_state=canonical_state,
                )
                self._save(snapshot)
                self._latest = snapshot
                self._last_completed_generation += 1
                return snapshot

            client = self._client_factory()
            try:
                allowed_keys = (
                    ("nse_preopen_fo",)
                    if market["session"] == "PRE_OPEN" and not force
                    else P0_SOURCE_KEYS
                )
                requests: list[tuple[str, dict[str, str]]] = [
                    (key, {})
                    for key in allowed_keys
                    if key in ENDPOINTS
                    and instant >= self._source_quarantine_until.get(key, instant)
                ]
                try:
                    results = await client.fetch_many(requests, concurrency=3)
                except Exception as exc:
                    results = [
                        EndpointFetchResult(
                            endpoint_key=key,
                            state=FetchState.BROKEN,
                            fetched_at=instant,
                            url=ENDPOINTS[key].url_template,
                            record_count=0,
                            can_score=False,
                            reason=f"live refresh failed closed: {type(exc).__name__}",
                            error_type="REQUEST_FAILED",
                        )
                        for key, _parameters in requests
                    ]
            finally:
                try:
                    await client.aclose()
                except Exception:
                    pass

            normalized = {
                result.endpoint_key: normalize_live_result(
                    result,
                    now=instant,
                    market_trading_date=market["tradingDate"],
                    max_age_sec=max_age_sec,
                )
                for result in results
            }
            circuit_tripped = self._update_safety_state(
                results, normalized, instant=instant
            )
            for key in P0_SOURCE_KEYS:
                until = self._source_quarantine_until.get(key)
                if key not in normalized and until is not None and instant < until:
                    normalized[key] = {
                        "sourceKey": key,
                        "state": "QUARANTINED",
                        "eligible": False,
                        "tradingDate": market["tradingDate"],
                        "recordsSample": [],
                        "normalizedRowCount": 0,
                        "reason": f"source cooldown until {until.isoformat()}",
                    }
            snapshot = build_live_snapshot(
                normalized,
                now=instant,
                market=market,
                max_age_sec=max_age_sec,
                refresh_state="CIRCUIT_OPEN" if circuit_tripped else "REFRESHED",
            )
            if circuit_tripped:
                snapshot["inventoryOverlay"] = []
                snapshot["refresh"]["retryAfter"] = (
                    self._breaker_until.isoformat()
                    if self._breaker_until is not None
                    else None
                )
                for panel in snapshot["panels"].values():
                    panel["state"] = "STALE"
            self._save(snapshot)
            self._latest = snapshot
            self._last_completed_generation += 1
            return snapshot
