"""Official MTO delivery evidence for the Hybrid V2 AS block (Phase 2).

Usable only when the official `nse_mto_delivery` last-good is structured and
its data_date matches the research session at available_at <= decision_at.
Volume is never a delivery proxy. Numeric scrips and UNKNOWN_ID rows skip AS.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from statistics import median
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from ... import storage

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

SOURCE_KEY = "nse_mto_delivery"
MIN_SESSIONS = 20
MAD_SCALE = 1.4826

AsStatusLiteral = Literal["USABLE", "UNKNOWN", "STALE", "WAIT_CA"]


class AsDeliveryEvidenceV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    status: AsStatusLiteral = "UNKNOWN"
    delivery_z: float | None = None
    accumulation_days: int | None = None
    sample_size: int = 0
    median_delivery_pct: float | None = None
    latest_data_date: str | None = None
    why: tuple[str, ...] = ()


def _parse_ts(value) -> datetime | None:
    if value in {None, ""}:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def load_delivery_series(
    *,
    symbol: str,
    session_date: date,
    decision_at: datetime,
    limit: int = 120,
) -> list[tuple[date, float]]:
    """Dated EQ delivery% series from official MTO last-goods only.

    PIT rules: a parse result enters the series only when its data_date is on
    or before the research session AND its parsed_at <= decision_at. The newest
    parse per data_date wins; older parses of the same day are superseded.
    """
    wanted = symbol.upper()
    by_date: dict[date, tuple[datetime, float]] = {}
    for result in storage.list_source_parse_results(SOURCE_KEY, limit=limit):
        if result.parser_state != "PARSED_STRUCTURED":
            continue
        if not result.data_date:
            continue
        try:
            data_date = date.fromisoformat(result.data_date)
        except ValueError:
            continue
        if data_date > session_date:
            continue
        parsed_at = _parse_ts(result.parsed_at)
        if parsed_at is None or parsed_at > decision_at:
            continue
        pct = _symbol_delivery_pct(result.output, wanted)
        if pct is None:
            continue
        current = by_date.get(data_date)
        if current is None or parsed_at > current[0]:
            by_date[data_date] = (parsed_at, pct)
    return sorted((day, pct) for day, (_ts, pct) in by_date.items())


def _symbol_delivery_pct(output: dict, wanted: str) -> float | None:
    rows = output.get("rows") or output.get("records") or []
    fallback: float | None = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("symbol") or "").upper() != wanted:
            continue
        try:
            pct = float(row.get("delivery_pct"))
        except (TypeError, ValueError):
            continue
        if str(row.get("series") or "").upper() == "EQ":
            return pct
        if fallback is None:
            fallback = pct
    return fallback


def robust_z(window: list[float]) -> tuple[float | None, float, float]:
    """(x - median_20) / (1.4826 * MAD_20). MAD=0 means UNKNOWN."""
    med = median(window)
    mad = median(abs(value - med) for value in window)
    if mad == 0:
        return None, med, mad
    value = window[-1]
    return (value - med) / (MAD_SCALE * mad), med, mad


def accumulation_day_count(
    *,
    window_dates: list[date],
    window_pcts: list[float],
    median_pct: float,
    raw_bars_fn: Callable[..., list],
    symbol: str,
    session_date: date,
) -> tuple[int | None, str | None]:
    """Count quiet accumulation days: delivery% > median_20 and |return| <= median range.

    Quiet is defined on A4 raw bars. Missing bars mean UNKNOWN, never volume proxy.
    """
    bars = raw_bars_fn(symbol, through=session_date)
    if not bars:
        return None, "WAIT_A4_BARS_MISSING"
    close_by_date = {bar.trade_date: float(bar.close) for bar in bars if bar.close}
    returns: dict[date, float] = {}
    previous: float | None = None
    for bar in sorted(bars, key=lambda item: item.trade_date):
        close = float(bar.close) if bar.close else None
        if close is not None and previous is not None and previous > 0:
            returns[bar.trade_date] = close / previous - 1.0
        previous = close if close is not None else previous
    ranges = [abs(value) for value in returns.values()]
    if not ranges:
        return None, "WAIT_A4_RETURNS_MISSING"
    median_range = median(ranges)
    count = 0
    matched = False
    for day, pct in zip(window_dates, window_pcts):
        session_return = returns.get(day)
        if session_return is None:
            continue
        matched = True
        if pct > median_pct and abs(session_return) <= median_range:
            count += 1
    if not matched:
        return None, "WAIT_A4_SESSION_DATES_MISSING"
    return count, None


def build_as_delivery_evidence(
    *,
    symbol: str,
    instrument_id: str | None,
    ca_state: str,
    session_date: date,
    decision_at: datetime,
    raw_bars_fn: Callable[..., list] | None = None,
) -> AsDeliveryEvidenceV1:
    # Identity gate first: numeric scrips and UNKNOWN_ID rows skip AS even if
    # MTO rows exist under that symbol string.
    if not symbol or symbol.isdigit() or instrument_id is None:
        return AsDeliveryEvidenceV1(
            symbol=symbol,
            status="UNKNOWN",
            why=("UNKNOWN_ID_ROWS_SKIP_AS",),
        )
    if ca_state == "WAIT_CA":
        return AsDeliveryEvidenceV1(
            symbol=symbol,
            status="WAIT_CA",
            why=("WAIT_CA_HIDE_DELIVERY_Z",),
        )
    bars_fn = raw_bars_fn
    if bars_fn is None:
        from ...selection.cash_a4_history import list_raw_bars as bars_fn  # noqa: PLC0415
    series = load_delivery_series(
        symbol=symbol, session_date=session_date, decision_at=decision_at
    )
    if not series:
        return AsDeliveryEvidenceV1(symbol=symbol, status="UNKNOWN", why=("MTO_SERIES_MISSING",))
    latest_date = series[-1][0]
    stale = latest_date < session_date
    if len(series) < MIN_SESSIONS:
        status: AsStatusLiteral = "STALE" if stale else "UNKNOWN"
        why = ["MTO_SERIES_SHORT"] + (["MTO_LATEST_NOT_SESSION"] if stale else [])
        return AsDeliveryEvidenceV1(
            symbol=symbol,
            status=status,
            sample_size=len(series),
            latest_data_date=latest_date.isoformat(),
            why=tuple(why),
        )
    window = series[-MIN_SESSIONS:]
    dates = [day for day, _ in window]
    pcts = [pct for _, pct in window]
    z, med, _mad = robust_z(pcts)
    base_why = ["MTO_LATEST_NOT_SESSION"] if stale else []
    if z is None:
        return AsDeliveryEvidenceV1(
            symbol=symbol,
            status="UNKNOWN",
            sample_size=len(window),
            median_delivery_pct=med,
            latest_data_date=latest_date.isoformat(),
            why=tuple(base_why + ["MTO_MAD_ZERO"]),
        )
    days, day_why = accumulation_day_count(
        window_dates=dates,
        window_pcts=pcts,
        median_pct=med,
        raw_bars_fn=bars_fn,
        symbol=symbol,
        session_date=session_date,
    )
    why = list(base_why)
    if day_why:
        why.append(day_why)
    if stale:
        # STALE never ships a z: only USABLE evidence may display delivery_z.
        return AsDeliveryEvidenceV1(
            symbol=symbol,
            status="STALE",
            delivery_z=None,
            accumulation_days=days,
            sample_size=len(window),
            median_delivery_pct=med,
            latest_data_date=latest_date.isoformat(),
            why=tuple(why),
        )
    return AsDeliveryEvidenceV1(
        symbol=symbol,
        status="USABLE",
        delivery_z=round(z, 4),
        accumulation_days=days,
        sample_size=len(window),
        median_delivery_pct=med,
        latest_data_date=latest_date.isoformat(),
        why=tuple(why),
    )
