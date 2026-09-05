"""A4 PIT cash history, baselines and adjusted-series vintages.

RAW session bars are immutable. Corporate actions open a new ADJUSTED series.
Replay at decision_at cannot see a CA whose available_at is in the future.
Unresolved CA (no factor) is WAIT integrity, not bullish event.

This is NOT File A R4. R4 may read membership fixtures against these IDs;
it does not own bars or CA vintages. R14 is the later official CA join.
"""

from __future__ import annotations

import hashlib
import time
from datetime import UTC, date, datetime, timedelta
from statistics import median
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .. import storage
from .cash_a2_identity import CashIdentityBatch, latest_cash_identity
from .contracts import stable_id
from .series_layers import MarketSeriesRef, open_adjusted_series, raw_series

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)
BASELINE_WINDOW = 20
OFFICIAL_HISTORY_BARS = 21
HISTORY_PROBE_SYMBOL = "RELIANCE"


class CorporateActionVintage(BaseModel):
    model_config = MODEL_CONFIG

    event_id: str
    symbol: str
    action_class: str
    effective_date: date
    available_at: datetime
    revision_id: str
    adjustment_factor: float | None = None

    def visible_at(self, decision_at: datetime) -> bool:
        if decision_at.tzinfo is None or decision_at.utcoffset() is None:
            raise ValueError("decision_at must be timezone-aware")
        return self.available_at <= decision_at


class CashRawSessionBar(BaseModel):
    model_config = MODEL_CONFIG

    bar_id: str
    instrument_id: str
    symbol: str
    trade_date: date
    artifact_hash: str
    series_id: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    previous_close: float
    volume: float = 0
    traded_value: float = 0


class ParticipationBaseline(BaseModel):
    model_config = MODEL_CONFIG

    session_count: int = Field(ge=0)
    window: int = BASELINE_WINDOW
    median_volume: float | None = None
    median_turnover: float | None = None
    median_range_pct: float | None = None
    complete: bool = False
    reason: str


class CashHistoryRow(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    instrument_id: str
    raw_series_id: str
    adjusted_series_id: str | None = None
    visible_ca_event_ids: tuple[str, ...] = ()
    hidden_future_ca_count: int = 0
    ca_state: Literal["NONE", "ADJUSTED", "WAIT_CA"]
    baseline: ParticipationBaseline
    public_note: str


class CashHistoryBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: str = "A4"
    acceptance_ceiling: str = "HISTORY_VINTAGES_ONLY"
    batch_id: str
    identity_batch_id: str | None
    decision_at: datetime
    can_rank: bool = False
    can_unlock_confirmed: bool = False
    raw_bar_count: int = Field(ge=0)
    row_count: int = Field(ge=0)
    rows: tuple[CashHistoryRow, ...] = ()
    persisted: bool = False


def _aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def persist_ca_vintages(vintages: list[CorporateActionVintage]) -> None:
    storage.init_db()
    conn = storage.connect()
    try:
        for item in vintages:
            conn.execute(
                """
                INSERT OR REPLACE INTO cash_ca_vintages (
                    event_id, symbol, action_class, effective_date, available_at,
                    revision_id, adjustment_factor, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.event_id,
                    item.symbol.upper(),
                    item.action_class,
                    item.effective_date.isoformat(),
                    item.available_at.isoformat(),
                    item.revision_id,
                    item.adjustment_factor,
                    storage.encode_json(item.model_dump(mode="json", by_alias=True)),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def list_ca_vintages() -> list[CorporateActionVintage]:
    storage.init_db()
    conn = storage.connect()
    try:
        rows = conn.execute(
            "SELECT payload_json FROM cash_ca_vintages ORDER BY available_at"
        ).fetchall()
    finally:
        conn.close()
    return [CorporateActionVintage.model_validate(storage.decode_json(row["payload_json"])) for row in rows]


def _store_raw_bar(bar: CashRawSessionBar) -> None:
    storage.init_db()
    conn = storage.connect()
    try:
        existing = conn.execute(
            """
            SELECT artifact_hash FROM cash_raw_session_bars
            WHERE instrument_id = ? AND trade_date = ?
            """,
            (bar.instrument_id, bar.trade_date.isoformat()),
        ).fetchone()
        if existing is not None and existing["artifact_hash"] != bar.artifact_hash:
            raise ValueError(
                "RAW cash session bar is immutable; a changed hash must not overwrite "
                f"{bar.symbol} {bar.trade_date}"
            )
        conn.execute(
            """
            INSERT OR IGNORE INTO cash_raw_session_bars (
                bar_id, instrument_id, symbol, trade_date, artifact_hash,
                series_id, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bar.bar_id,
                bar.instrument_id,
                bar.symbol,
                bar.trade_date.isoformat(),
                bar.artifact_hash,
                bar.series_id,
                storage.encode_json(bar.model_dump(mode="json", by_alias=True)),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_raw_bars(symbol: str, *, through: date) -> list[CashRawSessionBar]:
    storage.init_db()
    conn = storage.connect()
    try:
        rows = conn.execute(
            """
            SELECT payload_json FROM cash_raw_session_bars
            WHERE symbol = ? AND trade_date <= ?
            ORDER BY trade_date
            """,
            (symbol.upper(), through.isoformat()),
        ).fetchall()
    finally:
        conn.close()
    return [CashRawSessionBar.model_validate(storage.decode_json(row["payload_json"])) for row in rows]

def list_raw_bars_by_symbol(
    symbols: set[str], *, through: date, from_date: date | None = None
) -> dict[str, list[CashRawSessionBar]]:
    """Load requested symbols in bounded bulk queries, never all stored bars."""
    wanted = sorted({symbol.upper() for symbol in symbols if symbol})
    if not wanted:
        return {}
    output: dict[str, list[CashRawSessionBar]] = {symbol: [] for symbol in wanted}
    storage.init_db()
    conn = storage.connect()
    try:
        rows = []
        for offset in range(0, len(wanted), 500):
            chunk = wanted[offset : offset + 500]
            placeholders = ",".join("?" for _ in chunk)
            where = [f"symbol IN ({placeholders})", "trade_date <= ?"]
            params = [*chunk, through.isoformat()]
            if from_date is not None:
                where.append("trade_date >= ?")
                params.append(from_date.isoformat())
            rows.extend(
                conn.execute(
                    "SELECT payload_json FROM cash_raw_session_bars "
                    f"WHERE {' AND '.join(where)} ORDER BY symbol, trade_date",
                    params,
                ).fetchall()
            )
    finally:
        conn.close()
    for row in rows:
        bar = CashRawSessionBar.model_validate(storage.decode_json(row["payload_json"]))
        output[bar.symbol.upper()].append(bar)
    return output

def _official_cash_urls(day: date) -> list[str]:
    from ..source_resolver import direct_download_candidates

    wanted = (day.strftime("%Y%m%d"), day.strftime("%d%m%y"))
    urls = [
        url
        for url in direct_download_candidates("nse_bhavcopy_eod", today=day)
        if any(token in url for token in wanted)
    ]
    urls.sort(key=lambda url: "BhavCopy_NSE_CM_" not in url)
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def ensure_official_raw_history(
    through: date,
    *,
    days: int = OFFICIAL_HISTORY_BARS,
    timeout_seconds: int = 20,
) -> dict[str, int | str | bool]:
    """Fill missing official cash session bars behind last-good. Never overwrites."""
    existing = list_raw_bars(HISTORY_PROBE_SYMBOL, through=through)
    if len(existing) >= days:
        return {"skipped": True, "reason": "history already meets structure window"}
    identity = latest_cash_identity()
    if identity is None:
        return {"skipped": True, "reason": "no A2 identity to map symbols"}
    from ..parsers.nse_cash_bhavcopy_parser import parse_nse_cash_bhavcopy
    from ..source_resolver import fetch_url
    from urllib.error import HTTPError, URLError

    instrument_by_symbol = {
        row.instrument.symbol: row.instrument.instrument_id for row in identity.rows
    }
    targets: list[date] = []
    cursor = through - timedelta(days=1)
    while len(targets) < days - 1:
        if cursor.weekday() < 5:
            targets.append(cursor)
        cursor -= timedelta(days=1)
    stats: dict[str, int | str | bool] = {
        "skipped": False,
        "days_saved": 0,
        "days_missing": 0,
        "days_failed": 0,
    }
    for day in reversed(targets):
        content = None
        for url in _official_cash_urls(day):
            try:
                status, _headers, payload = fetch_url(url, timeout_seconds)
            except HTTPError as exc:
                if exc.code == 404:
                    continue
                stats["days_failed"] = int(stats["days_failed"]) + 1
                content = None
                break
            except (URLError, TimeoutError, OSError):
                continue
            if status >= 400 or not payload:
                continue
            content = payload
            break
        if content is None:
            stats["days_missing"] = int(stats["days_missing"]) + 1
            continue
        parsed = parse_nse_cash_bhavcopy(content)
        if parsed.get("parser_state") != "PARSED_STRUCTURED":
            stats["days_failed"] = int(stats["days_failed"]) + 1
            continue
        if str(parsed.get("data_date")) != day.isoformat():
            stats["days_failed"] = int(stats["days_failed"]) + 1
            continue
        artifact = hashlib.sha256(content).hexdigest()
        for row in parsed.get("output", {}).get("rows") or []:
            symbol = str(row.get("symbol") or "").upper()
            instrument_id = instrument_by_symbol.get(symbol)
            if instrument_id is None or not row.get("open") or not row.get("high") or not row.get("low"):
                continue
            bar = CashRawSessionBar(
                bar_id=stable_id("cbar", instrument_id, day.isoformat(), artifact),
                instrument_id=instrument_id,
                symbol=symbol,
                trade_date=day,
                artifact_hash=artifact,
                series_id=raw_series(
                    instrument_key=f"NSE:{symbol}:EQ", artifact_hash=artifact
                ).series_id,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                previous_close=float(row["previousClose"]),
                volume=float(row.get("volume") or 0),
                traded_value=float(row.get("tradedValue") or 0),
            )
            try:
                _store_raw_bar(bar)
            except ValueError:
                continue
        stats["days_saved"] = int(stats["days_saved"]) + 1
        time.sleep(0.2)
    return stats


def _bar_from_fact(row) -> CashRawSessionBar | None:
    payload = row.fact.payload
    close = payload.get("close")
    previous = payload.get("previousClose")
    if close is None or previous is None:
        return None
    artifact = row.fact.lineage.artifact_hash
    instrument_key = f"NSE:{row.instrument.symbol}:{row.instrument.series}"
    series = raw_series(instrument_key=instrument_key, artifact_hash=artifact)
    trade_date = row.fact.data_date
    return CashRawSessionBar(
        bar_id=stable_id("cbar", row.instrument.instrument_id, trade_date.isoformat(), artifact),
        instrument_id=row.instrument.instrument_id,
        symbol=row.instrument.symbol,
        trade_date=trade_date,
        artifact_hash=artifact,
        series_id=series.series_id,
        open=payload.get("open"),
        high=payload.get("high"),
        low=payload.get("low"),
        close=float(close),
        previous_close=float(previous),
        volume=float(payload.get("volume") or 0),
        traded_value=float(payload.get("tradedValue") or 0),
    )


def _baseline(bars: list[CashRawSessionBar]) -> ParticipationBaseline:
    window = bars[-BASELINE_WINDOW:]
    if len(window) < 2:
        return ParticipationBaseline(
            session_count=len(window),
            complete=False,
            reason="Need at least two visible raw sessions for a participation baseline.",
        )
    volumes = [item.volume for item in window]
    turnovers = [item.traded_value for item in window]
    ranges: list[float] = []
    for item in window:
        if item.high is not None and item.low is not None and item.previous_close > 0:
            ranges.append((item.high - item.low) / item.previous_close)
    return ParticipationBaseline(
        session_count=len(window),
        complete=True,
        median_volume=float(median(volumes)),
        median_turnover=float(median(turnovers)),
        median_range_pct=float(median(ranges)) if ranges else None,
        reason=f"Median participation over {len(window)} visible raw sessions.",
    )


def _visible_ca(
    vintages: list[CorporateActionVintage],
    *,
    symbol: str,
    decision_at: datetime,
) -> tuple[list[CorporateActionVintage], int]:
    hidden = 0
    visible: list[CorporateActionVintage] = []
    for item in vintages:
        if item.symbol.upper() != symbol.upper():
            continue
        if not item.visible_at(decision_at):
            hidden += 1
            continue
        visible.append(item)
    return visible, hidden


def _apply_series(
    raw: MarketSeriesRef, visible: list[CorporateActionVintage]
) -> tuple[MarketSeriesRef | None, Literal["NONE", "ADJUSTED", "WAIT_CA"]]:
    resolved = [item for item in visible if item.adjustment_factor is not None]
    unresolved = [item for item in visible if item.adjustment_factor is None]
    if unresolved:
        return None, "WAIT_CA"
    if not resolved:
        return None, "NONE"
    ordered = sorted(resolved, key=lambda value: (value.effective_date, value.event_id))
    event_id = "+".join(item.event_id for item in ordered)
    return open_adjusted_series(raw, adjustment_event_id=event_id), "ADJUSTED"


def build_cash_history_batch(
    identity: CashIdentityBatch | None = None,
    *,
    decision_at: datetime | None = None,
    vintages: list[CorporateActionVintage] | None = None,
) -> CashHistoryBatch:
    at = _aware(decision_at or datetime.now(UTC), "decision_at")
    batch = identity if identity is not None else latest_cash_identity()
    stored_vintages = list_ca_vintages()
    if vintages:
        persist_ca_vintages(vintages)
        stored_vintages = list_ca_vintages()
    if batch is None:
        return CashHistoryBatch(
            batch_id=str(uuid4()),
            identity_batch_id=None,
            decision_at=at,
            raw_bar_count=0,
            row_count=0,
            rows=(),
        )
    rows: list[CashHistoryRow] = []
    raw_count = 0
    for item in batch.rows:
        bar = _bar_from_fact(item)
        if bar is None:
            continue
        _store_raw_bar(bar)
        raw_count += 1
        history = list_raw_bars(bar.symbol, through=bar.trade_date)
        raw_ref = raw_series(
            instrument_key=f"NSE:{bar.symbol}:{item.instrument.series}",
            artifact_hash=bar.artifact_hash,
        )
        visible, hidden = _visible_ca(stored_vintages, symbol=bar.symbol, decision_at=at)
        adjusted, ca_state = _apply_series(raw_ref, visible)
        note = {
            "NONE": "No visible corporate-action vintage. RAW series unchanged.",
            "ADJUSTED": "Visible CA opened a new ADJUSTED series. RAW was not mutated.",
            "WAIT_CA": "Visible CA has no factor. Integrity WAIT; not bullish.",
        }[ca_state]
        if hidden:
            note += f" {hidden} future CA vintage(s) hidden from this decision_at."
        rows.append(
            CashHistoryRow(
                symbol=bar.symbol,
                instrument_id=bar.instrument_id,
                raw_series_id=raw_ref.series_id,
                adjusted_series_id=adjusted.series_id if adjusted else None,
                visible_ca_event_ids=tuple(event.event_id for event in visible),
                hidden_future_ca_count=hidden,
                ca_state=ca_state,
                baseline=_baseline(history),
                public_note=note,
            )
        )
    return CashHistoryBatch(
        batch_id=str(uuid4()),
        identity_batch_id=batch.batch_id,
        decision_at=at,
        can_rank=False,
        can_unlock_confirmed=False,
        raw_bar_count=raw_count,
        row_count=len(rows),
        rows=tuple(rows),
    )


def persist_cash_history(batch: CashHistoryBatch) -> CashHistoryBatch:
    if batch.can_rank or batch.can_unlock_confirmed:
        raise ValueError("A4 cannot set can_rank or can_unlock_confirmed")
    storage.init_db()
    conn = storage.connect()
    now = datetime.now(UTC).isoformat()
    try:
        conn.execute(
            """
            INSERT INTO cash_history_runs (
                batch_id, identity_batch_id, decision_at, raw_bar_count,
                row_count, payload_json, persisted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch.batch_id,
                batch.identity_batch_id,
                batch.decision_at.isoformat(),
                batch.raw_bar_count,
                batch.row_count,
                storage.encode_json(batch.model_dump(mode="json", by_alias=True)),
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return batch.model_copy(update={"persisted": True})


def latest_cash_history() -> CashHistoryBatch | None:
    storage.init_db()
    conn = storage.connect()
    try:
        head = conn.execute(
            """
            SELECT payload_json FROM cash_history_runs
            ORDER BY persisted_at DESC, batch_id DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if head is None:
        return None
    payload = storage.decode_json(head["payload_json"])
    payload["persisted"] = True
    return CashHistoryBatch.model_validate(payload)
