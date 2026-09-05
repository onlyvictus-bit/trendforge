"""Batch last-good loaders for radar Stage B. Never vote; never invent."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from ..r6_live import _float, _rows, _text, _usable

MIN_DELIVERY_SESSIONS = 20
MAD_SCALE = 1.4826


def default_parse_loader():
    from ...storage import get_latest_source_parse_result

    return get_latest_source_parse_result


def load_shp_rows(loader) -> list[dict[str, Any]]:
    usable = _usable(loader("nse_shareholding_pattern")) if callable(loader) else None
    if usable is None:
        return []
    rows: list[dict[str, Any]] = []
    for row in _rows(usable[0]):
        symbol = (_text(row, "symbol") or "").upper()
        if not symbol:
            continue
        promoter = _float(
            row,
            "pr_and_prgrp",
            "promoter_holding_pct",
            "percPromoterHolding",
            "Percentage_TOTAL_PROMOTER_HOLDING",
            "promoter",
        )
        public = _float(row, "public_val", "public_holding_pct", "public", "percPublicHolding")
        rows.append(
            {
                "symbol": symbol,
                "promoter_holding_pct": promoter,
                "public_holding_pct": public,
                "date": _text(row, "date", "submissionDate", "broadcastDate"),
            }
        )
    return rows


def load_preopen_map(loader) -> dict[str, dict[str, float]]:
    """IEP gap from official pre-open last-good. Intraday only; never LIVE_VERIFIED."""
    for key in ("nse_preopen", "nse_pre_open", "nse_preopen_fo"):
        usable = _usable(loader(key)) if callable(loader) else None
        if usable is None:
            continue
        out: dict[str, dict[str, float]] = {}
        for row in _rows(usable[0]):
            symbol = (_text(row, "symbol") or "").upper()
            iep = _float(row, "iep", "indicativePrice", "price")
            prev = _float(row, "prevClose", "previousClose", "pClose")
            gap = _float(row, "gap_pct", "gapPct")
            if symbol and gap is None and iep is not None and prev not in (None, 0):
                gap = (iep - prev) / prev * 100.0
            if symbol and gap is not None:
                out[symbol] = {"gap_pct": float(gap), "iep": float(iep or 0.0)}
        if out:
            return out
    return {}


def load_activity_symbols(loader) -> set[str]:
    """Most-active / volume-gainer names. Same cash session as R2 — not a second vote."""
    symbols: set[str] = set()
    for key in (
        "nse_most_active_volume",
        "nse_most_active_value",
        "nse_volume_gainers",
        "nse_most_active_underlying",
    ):
        usable = _usable(loader(key)) if callable(loader) else None
        if usable is None:
            continue
        for row in _rows(usable[0]):
            symbol = (_text(row, "symbol", "underlying") or "").upper()
            if symbol:
                symbols.add(symbol)
    return symbols


def load_event_map(loader) -> dict[str, str]:
    """Latest official filing/announcement/buyback headline per symbol. No side."""
    found: dict[str, str] = {}
    for key in (
        "nse_announcements",
        "nse_board_meetings",
        "nse_daily_buyback",
        "nse_corporate_filings_actions",
        "nse_financial_results",
    ):
        usable = _usable(loader(key)) if callable(loader) else None
        if usable is None:
            continue
        for row in _rows(usable[0]):
            symbol = (_text(row, "symbol") or "").upper()
            if not symbol or symbol in found:
                continue
            headline = _text(
                row,
                "headline",
                "subject",
                "desc",
                "description",
                "purpose",
                "eventType",
                "companyName",
            )
            found[symbol] = f"{key}:{headline or 'OFFICIAL_EVENT'}"
    return found


def load_nifty_closes(trading_date: date, limit: int = 80) -> list[Any]:
    from ...storage import list_nse_index_eod

    rows = list_nse_index_eod(index_name="NIFTY 50", as_of=trading_date.isoformat(), limit=limit)
    if not rows:
        rows = list_nse_index_eod(index_name="NIFTY50", as_of=trading_date.isoformat(), limit=limit)

    class _Close:
        def __init__(self, close: float) -> None:
            self.close = close

    closes: list[_Close] = []
    for row in rows:
        value = row.get("close") or row.get("index_close") or row.get("closingValue")
        try:
            closes.append(_Close(float(value)))
        except (TypeError, ValueError):
            continue
    return closes


def load_delivery_history(
    wanted: set[str],
    session_date: date,
    decision_at: datetime,
    *,
    parse_limit: int = 40,
) -> dict[str, list[float]]:
    """PIT EQ delivery% series per symbol. Volume is never a proxy."""
    from ...storage import list_source_parse_results

    by_symbol_date: dict[str, dict[date, tuple[datetime, float]]] = {}
    wanted_u = {item.upper() for item in wanted}
    for result in list_source_parse_results("nse_mto_delivery", limit=parse_limit):
        if str(getattr(result, "parser_state", "")).upper() not in {
            "PARSED",
            "PARSED_STRUCTURED",
            "PARSED_ADAPTER",
        }:
            continue
        raw_date = getattr(result, "data_date", None)
        if not raw_date:
            continue
        try:
            data_date = date.fromisoformat(str(raw_date)[:10])
        except ValueError:
            continue
        if data_date > session_date:
            continue
        parsed_at = _parse_ts(getattr(result, "parsed_at", None))
        if parsed_at is None or parsed_at > decision_at:
            continue
        output = getattr(result, "output", None)
        if not isinstance(output, dict):
            continue
        for row in _rows(output):
            symbol = (_text(row, "symbol") or "").upper()
            if not symbol or symbol not in wanted_u:
                continue
            pct = _float(row, "delivery_pct", "deliveryPct", "deliveryPercentage")
            if pct is None or not 0 <= pct <= 100:
                continue
            series = (_text(row, "series") or "").upper()
            current = by_symbol_date.setdefault(symbol, {})
            existing = current.get(data_date)
            if series != "EQ" and existing is not None:
                continue
            if existing is None or parsed_at > existing[0] or series == "EQ":
                current[data_date] = (parsed_at, float(pct))
    return {
        symbol: [pct for _day, pct in sorted(dates.items())]
        for symbol, dates in by_symbol_date.items()
    }


def robust_delivery_z(window: list[float]) -> tuple[float | None, float]:
    from statistics import median

    if len(window) < MIN_DELIVERY_SESSIONS:
        return None, 0.0
    sample = window[-MIN_DELIVERY_SESSIONS:]
    med = median(sample)
    mad = median(abs(value - med) for value in sample)
    if mad == 0:
        return None, med
    return (sample[-1] - med) / (MAD_SCALE * mad), med


def r5_setup_map(r1_bundle_id: str, r1_bundle_hash: str, r2_run_id: str, r2_run_hash: str) -> dict[str, tuple[str, ...]]:
    from ..r5_live import latest_r5_structure_batch

    batch = latest_r5_structure_batch()
    if batch is None:
        return {}
    if (
        batch.r1_bundle_id != r1_bundle_id
        or batch.r1_bundle_hash != r1_bundle_hash
        or batch.r2_run_id != r2_run_id
        or batch.r2_run_hash != r2_run_hash
    ):
        return {}
    return {
        row.symbol.upper(): tuple(row.detected_setups)
        for row in batch.rows
        if row.detected_setups
    }


def _parse_ts(value) -> datetime | None:
    if value in {None, ""}:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
