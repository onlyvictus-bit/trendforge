from __future__ import annotations

import json
import math
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .institutional_sources import EndpointFetchResult, FetchState


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT_DIR / "data" / "trendforge_research.db"
ACTIVITY_ENDPOINTS = (
    "nse_volume_gainers",
    "nse_most_active_volume",
    "nse_most_active_value",
    "nse_large_deals_snapshot",
)
FRESH_STATES = {FetchState.RAW_ARCHIVED, FetchState.NO_DATA_NOW}


class MarketActivityModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MarketActivitySource(MarketActivityModel):
    endpoint_key: str
    state: str
    fetched_at: datetime
    record_count: int = Field(ge=0)
    content_hash: str | None = None
    from_cache: bool = False
    source_timestamp: str | None = None
    reason: str | None = None


class MarketActivityCandidate(MarketActivityModel):
    symbol: str
    state: Literal[
        "WATCH_LONG",
        "WATCH_SHORT",
        "WAIT_CONFIRMATION",
        "WAIT_PARTIAL_SOURCE",
        "WAIT_STALE",
    ]
    direction: Literal["BULLISH", "BEARISH", "MIXED"]
    activity_score: float = Field(ge=0, le=100)
    score_meaning: str = "EVIDENCE_STRENGTH_NOT_WIN_PROBABILITY"
    last_price: float | None = None
    price_change_pct: float | None = None
    volume: float | None = None
    turnover: float | None = None
    week1_volume_change_pct: float | None = None
    week2_volume_change_pct: float | None = None
    most_active_volume_rank: int | None = None
    most_active_value_rank: int | None = None
    deal_anchor_price: float | None = None
    deal_notional: float = 0
    short_deal_notional: float = 0
    named_buyers: list[str] = Field(default_factory=list)
    named_sellers: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    required_confirmations: list[str] = Field(default_factory=list)
    source_keys: list[str] = Field(default_factory=list)
    can_unlock_ready: bool = False


class MarketActivitySnapshot(MarketActivityModel):
    run_id: str
    fetched_at: datetime
    state: Literal["RESEARCH_ONLY", "WAIT_SOURCE", "WAIT_NO_SNAPSHOT"]
    source_completeness: float = Field(ge=0, le=1)
    sources: list[MarketActivitySource] = Field(default_factory=list)
    candidates: list[MarketActivityCandidate] = Field(default_factory=list)
    can_unlock_ready: bool = False
    reason: str


def _number(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, "", "-"):
            continue
        try:
            parsed = float(str(value).replace(",", ""))
        except ValueError:
            continue
        if math.isfinite(parsed):
            return parsed
    return None


def _text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _payload_rows(result: EndpointFetchResult | None, key: str = "data") -> list[dict[str, Any]]:
    payload = result.payload if result is not None else None
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key)
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _source_timestamp(result: EndpointFetchResult) -> str | None:
    if not isinstance(result.payload, dict):
        return None
    value = result.payload.get("timestamp") or result.payload.get("as_on_date")
    return str(value).strip() if value is not None and str(value).strip() else None


def _ranked(rows: list[dict[str, Any]]) -> dict[str, tuple[int, dict[str, Any]]]:
    ranked: dict[str, tuple[int, dict[str, Any]]] = {}
    for rank, row in enumerate(rows, start=1):
        symbol = _text(row, "symbol").upper()
        if symbol and symbol not in ranked:
            ranked[symbol] = (rank, row)
    return ranked


def _deal_evidence(result: EndpointFetchResult | None) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for deal_type, key in (
        ("BULK", "BULK_DEALS_DATA"),
        ("BLOCK", "BLOCK_DEALS_DATA"),
        ("SHORT", "SHORT_DEALS_DATA"),
    ):
        for row in _payload_rows(result, key):
            symbol = _text(row, "symbol").upper()
            quantity = _number(row, "qty", "quantity") or 0
            price = _number(row, "watp", "price") or 0
            if not symbol or quantity <= 0 or price <= 0:
                continue
            item = evidence.setdefault(
                symbol,
                {
                    "notional": 0.0,
                    "short_notional": 0.0,
                    "weighted_price": 0.0,
                    "quantity": 0.0,
                    "buyers": [],
                    "sellers": [],
                    "types": set(),
                },
            )
            notional = quantity * price
            item["notional"] += notional
            item["weighted_price"] += notional
            item["quantity"] += quantity
            item["types"].add(deal_type)
            if deal_type == "SHORT":
                item["short_notional"] += notional
            client = _text(row, "clientName", "client_name")
            side = _text(row, "buySell", "side").upper()
            target = item["buyers"] if side in {"BUY", "B"} else item["sellers"]
            if client and client not in target:
                target.append(client)
    for item in evidence.values():
        item["anchor"] = (
            item["weighted_price"] / item["quantity"] if item["quantity"] else None
        )
        item["types"] = sorted(item["types"])
    return evidence


def _spurt_score(row: dict[str, Any] | None) -> tuple[float, float | None, float | None]:
    if row is None:
        return 0, None, None
    week1 = _number(row, "week1volChange")
    week2 = _number(row, "week2volChange")
    maximum = max((value for value in (week1, week2) if value is not None), default=0)
    score = 30 if maximum >= 500 else 26 if maximum >= 200 else 22 if maximum >= 100 else 16 if maximum >= 50 else 8 if maximum > 0 else 0
    if week1 is not None and week2 is not None and min(week1, week2) >= 100:
        score += 5
    return min(score, 35), week1, week2


def _price_score(change: float | None) -> float:
    magnitude = abs(change or 0)
    return 10 if magnitude >= 5 else 7 if magnitude >= 3 else 4 if magnitude >= 1 else 0


def legacy_activity_state(
    source_completeness: float,
    stale: bool,
) -> Literal["WAIT_CONFIRMATION", "WAIT_PARTIAL_SOURCE", "WAIT_STALE"]:
    """CROSS-014 / FUS-008: activity_score and direction cannot set state."""
    if stale:
        return "WAIT_STALE"
    if source_completeness < 0.75:
        return "WAIT_PARTIAL_SOURCE"
    return "WAIT_CONFIRMATION"


def _candidate(
    symbol: str,
    volume_row: dict[str, Any] | None,
    active_volume: tuple[int, dict[str, Any]] | None,
    active_value: tuple[int, dict[str, Any]] | None,
    deal: dict[str, Any] | None,
    source_keys: list[str],
    source_completeness: float,
    stale: bool,
) -> MarketActivityCandidate:
    price_row = active_value[1] if active_value else active_volume[1] if active_volume else volume_row or {}
    change = _number(price_row, "pChange")
    last_price = _number(price_row, "lastPrice", "ltp")
    volume = _number(price_row, "totalTradedVolume", "quantityTraded", "volume")
    turnover = _number(price_row, "totalTradedValue", "turnover")
    spurt, week1, week2 = _spurt_score(volume_row)
    active_score = (12 if active_volume else 0) + (16 if active_value else 0)
    deal_score = 12 if deal else 0
    anchor = deal.get("anchor") if deal else None
    acceptance = "UNKNOWN"
    if last_price and anchor:
        acceptance = "ABOVE" if last_price >= anchor * 1.01 else "BELOW" if last_price <= anchor * 0.99 else "AT"
        deal_score += 5 if acceptance in {"ABOVE", "BELOW"} else 2
    score = min(100.0, spurt + active_score + _price_score(change) + deal_score)

    direction_points = 2 if (change or 0) > 0 else -2 if (change or 0) < 0 else 0
    if acceptance == "ABOVE":
        direction_points += 1
    elif acceptance == "BELOW":
        direction_points -= 1
    if deal and deal.get("short_notional", 0) > 0 and (change or 0) < 0:
        direction_points -= 1
    direction = "BULLISH" if direction_points >= 2 else "BEARISH" if direction_points <= -2 else "MIXED"

    # CROSS-014 / FUS-008: activity_score may sort the queue only.
    state = legacy_activity_state(source_completeness, stale)

    reasons: list[str] = []
    if spurt:
        reasons.append(f"Volume spurt strength {spurt:.0f}/35 versus recent averages.")
    if active_volume or active_value:
        labels = []
        if active_volume:
            labels.append(f"volume rank {active_volume[0]}")
        if active_value:
            labels.append(f"value rank {active_value[0]}")
        reasons.append("Most-active confirmation: " + ", ".join(labels) + ".")
    if change is not None:
        reasons.append(f"Current NSE price change is {change:+.2f}%.")
    if deal:
        reasons.append(
            f"Named {','.join(deal['types'])} activity is present; price acceptance versus WATP is {acceptance}."
        )
    if not reasons:
        reasons.append("No complete activity evidence is available for this symbol.")

    return MarketActivityCandidate(
        symbol=symbol,
        state=state,
        direction=direction,
        activity_score=round(score, 2),
        last_price=last_price,
        price_change_pct=change,
        volume=volume,
        turnover=turnover,
        week1_volume_change_pct=week1,
        week2_volume_change_pct=week2,
        most_active_volume_rank=active_volume[0] if active_volume else None,
        most_active_value_rank=active_value[0] if active_value else None,
        deal_anchor_price=round(anchor, 4) if anchor else None,
        deal_notional=round(deal.get("notional", 0), 2) if deal else 0,
        short_deal_notional=round(deal.get("short_notional", 0), 2) if deal else 0,
        named_buyers=(deal.get("buyers", [])[:3] if deal else []),
        named_sellers=(deal.get("sellers", [])[:3] if deal else []),
        reasons=reasons,
        required_confirmations=[
            "Fresh price above/below VWAP with ORB or structure confirmation",
            "Market and sector breadth aligned with direction",
            "Tradable spread, depth and position-size capacity",
            "OI/MWPL/basis confirmation when the symbol is in F&O",
            "Risk and emotional-safety gates pass",
        ],
        source_keys=source_keys,
        can_unlock_ready=False,
    )


def build_market_activity_snapshot(
    results: list[EndpointFetchResult], *, limit: int = 50
) -> MarketActivitySnapshot:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    by_key = {result.endpoint_key: result for result in results}
    sources = [
        MarketActivitySource(
            endpoint_key=result.endpoint_key,
            state=result.state.value,
            fetched_at=result.fetched_at,
            record_count=result.record_count,
            content_hash=result.content_hash,
            from_cache=result.from_cache,
            source_timestamp=_source_timestamp(result),
            reason=result.reason,
        )
        for result in results
        if result.endpoint_key in ACTIVITY_ENDPOINTS
    ]
    fresh_keys = {
        result.endpoint_key
        for result in results
        if result.endpoint_key in ACTIVITY_ENDPOINTS and result.state in FRESH_STATES
    }
    completeness = len(fresh_keys) / len(ACTIVITY_ENDPOINTS)
    stale = bool(sources) and not fresh_keys

    volume_rows = _ranked(_payload_rows(by_key.get("nse_volume_gainers")))
    active_volume = _ranked(_payload_rows(by_key.get("nse_most_active_volume")))
    active_value = _ranked(_payload_rows(by_key.get("nse_most_active_value")))
    deals = _deal_evidence(by_key.get("nse_large_deals_snapshot"))
    symbols = set(volume_rows) | set(active_volume) | set(active_value) | set(deals)
    candidates = [
        _candidate(
            symbol,
            volume_rows.get(symbol, (0, None))[1],
            active_volume.get(symbol),
            active_value.get(symbol),
            deals.get(symbol),
            sorted(
                key
                for key, mapping in (
                    ("nse_volume_gainers", volume_rows),
                    ("nse_most_active_volume", active_volume),
                    ("nse_most_active_value", active_value),
                    ("nse_large_deals_snapshot", deals),
                )
                if symbol in mapping
            ),
            completeness,
            stale,
        )
        for symbol in symbols
    ]
    candidates.sort(
        key=lambda item: (item.activity_score, abs(item.price_change_pct or 0)),
        reverse=True,
    )
    state = "RESEARCH_ONLY" if candidates else "WAIT_SOURCE"
    return MarketActivitySnapshot(
        run_id=str(uuid4()),
        fetched_at=max((result.fetched_at for result in results), default=datetime.now(UTC)),
        state=state,
        source_completeness=round(completeness, 4),
        sources=sources,
        candidates=candidates[:limit],
        can_unlock_ready=False,
        reason=(
            "Activity ranking is research evidence only; READY requires VWAP, structure, market/sector, derivatives when applicable, risk and safety confirmation."
            if candidates
            else "No usable NSE market-activity rows are available."
        ),
    )


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS market_activity_runs (
            run_id TEXT PRIMARY KEY,
            fetched_at TEXT NOT NULL,
            state TEXT NOT NULL,
            source_completeness REAL NOT NULL,
            candidate_count INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS market_activity_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL REFERENCES market_activity_runs(run_id),
            symbol TEXT NOT NULL,
            candidate_state TEXT NOT NULL,
            direction TEXT NOT NULL,
            activity_score REAL NOT NULL,
            payload_json TEXT NOT NULL,
            UNIQUE(run_id, symbol)
        );
        CREATE INDEX IF NOT EXISTS idx_market_activity_latest
        ON market_activity_runs(fetched_at DESC);
        CREATE INDEX IF NOT EXISTS idx_market_activity_symbol
        ON market_activity_candidates(symbol, run_id);
        """
    )


def save_market_activity_snapshot(
    snapshot: MarketActivitySnapshot, db_path: Path = DEFAULT_DB
) -> None:
    payload = snapshot.model_dump(mode="json", by_alias=True)
    with _connect(db_path) as connection:
        _initialize(connection)
        connection.execute(
            """
            INSERT INTO market_activity_runs(
                run_id, fetched_at, state, source_completeness,
                candidate_count, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.run_id,
                snapshot.fetched_at.isoformat(),
                snapshot.state,
                snapshot.source_completeness,
                len(snapshot.candidates),
                json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
            ),
        )
        connection.executemany(
            """
            INSERT INTO market_activity_candidates(
                run_id, symbol, candidate_state, direction,
                activity_score, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot.run_id,
                    item.symbol,
                    item.state,
                    item.direction,
                    item.activity_score,
                    json.dumps(
                        item.model_dump(mode="json", by_alias=True),
                        ensure_ascii=True,
                        separators=(",", ":"),
                    ),
                )
                for item in snapshot.candidates
            ],
        )


def latest_market_activity_snapshot(
    *, limit: int = 20, db_path: Path = DEFAULT_DB
) -> MarketActivitySnapshot:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    with _connect(db_path) as connection:
        _initialize(connection)
        row = connection.execute(
            "SELECT payload_json FROM market_activity_runs ORDER BY fetched_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return MarketActivitySnapshot(
            run_id="NO_SNAPSHOT",
            fetched_at=datetime.now(UTC),
            state="WAIT_NO_SNAPSHOT",
            source_completeness=0,
            reason="Run the NSE market-activity refresh to create the first snapshot.",
        )
    snapshot = MarketActivitySnapshot.model_validate_json(row["payload_json"])
    return snapshot.model_copy(update={"candidates": snapshot.candidates[:limit]})
