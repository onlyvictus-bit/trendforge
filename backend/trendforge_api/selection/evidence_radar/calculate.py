"""Stage B calculate recipes. Every recipe returns a typed fact with a
mandatory null-reason: if we did not compute a number, the code says why."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from ..cash_a4_history import list_raw_bars

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

RS_WINDOWS_DAYS = (5, 21, 63)


class FactDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class CalculatedFact(BaseModel):
    model_config = MODEL_CONFIG

    family: str
    code: str
    ok: bool
    direction: FactDirection = FactDirection.UNKNOWN
    value: float | None = None
    why: str
    correlation_group: str = ""


def _direction_from_sign(value: float) -> FactDirection:
    if value > 0:
        return FactDirection.BULLISH
    if value < 0:
        return FactDirection.BEARISH
    return FactDirection.NEUTRAL


def gap_fact(symbol: str, trading_date: date, ca_state: str) -> CalculatedFact:
    """Adjusted-safe gap from RAW A4 bars; R14 CA state is the authority."""
    family, group = "STRUCTURE", "CG_PRICE_STRUCTURE"
    if ca_state == "WAIT_CA":
        return CalculatedFact(
            family=family,
            code="UNKNOWN_GAP_WAIT_CA",
            ok=False,
            value=None,
            why="Corporate action unresolved; RAW gap would be unadjusted.",
            correlation_group=group,
        )
    bars = [
        bar
        for bar in list_raw_bars(symbol, through=trading_date)
        if bar.open is not None and bar.close is not None
    ]
    if len(bars) < 2 or bars[-1].trade_date == bars[-2].trade_date or not bars[-2].close:
        return CalculatedFact(
            family=family,
            code="UNKNOWN_GAP_BARS_MISSING",
            ok=False,
            value=None,
            why="Fewer than two closed sessions with open/close available.",
            correlation_group=group,
        )
    previous_close = float(bars[-2].close)
    gap_pct = round((float(bars[-1].open) - previous_close) / previous_close * 100.0, 4)
    return CalculatedFact(
        family=family,
        code="GAP_PCT_ADJUSTED_SAFE",
        ok=True,
        direction=_direction_from_sign(gap_pct),
        value=gap_pct,
        why="Gap of last open vs prior close on CA-safe series.",
        correlation_group=group,
    )


def delivery_fact(
    symbol: str,
    horizon: str,
    delivery_map: dict[str, float],
    history: list[float] | None = None,
) -> CalculatedFact:
    """Delivery is EOD-only. Intraday boards may never carry it.

    A 20-session robust z is a quality number, not a buy/sell vote (NEUTRAL).
    Volume is never used as a delivery proxy.
    """
    family, group = "DELIVERY", "CG_DELIVERY_EOD"
    if horizon == "INTRADAY":
        return CalculatedFact(
            family=family,
            code="FORBIDDEN_ON_INTRADAY",
            ok=False,
            value=None,
            why="Delivery evidence is forbidden on the intraday horizon.",
            correlation_group=group,
        )
    from .loads import MIN_DELIVERY_SESSIONS, robust_delivery_z

    series = history or []
    if len(series) >= MIN_DELIVERY_SESSIONS:
        z_score, median_pct = robust_delivery_z(series)
        if z_score is None:
            return CalculatedFact(
                family=family,
                code="CURRENT_PCT_Z_UNKNOWN_MAD0",
                ok=True,
                value=series[-1],
                why=(
                    f"{len(series)} MTO sessions; median={median_pct:.2f} but MAD=0 "
                    "so z is UNKNOWN. Direction stays NEUTRAL (not a buy/sell vote)."
                ),
                correlation_group=group,
            )
        return CalculatedFact(
            family=family,
            code="DELIVERY_Z_PIT20",
            ok=True,
            direction=FactDirection.NEUTRAL,
            value=round(z_score, 4),
            why=(
                f"Robust z vs {MIN_DELIVERY_SESSIONS}-session MTO median; "
                "quality number only, not a directional vote."
            ),
            correlation_group=group,
        )
    pct = delivery_map.get(symbol.upper())
    if pct is None:
        return CalculatedFact(
            family=family,
            code="UNKNOWN_DELIVERY_SOURCE_MISSING",
            ok=False,
            value=None,
            why="No MTO last-good row for this symbol.",
            correlation_group=group,
        )
    return CalculatedFact(
        family=family,
        code="CURRENT_PCT_ONLY_Z_UNKNOWN_NEEDS_20_SESSIONS",
        ok=True,
        value=pct,
        why=(
            "Current-session delivery percentage as a fact. The PIT z-score "
            "needs at least 20 completed MTO sessions and stays UNKNOWN."
        ),
        correlation_group=group,
    )


def rs_fact(
    symbol: str,
    trading_date: date,
    *,
    benchmark_bars: list[Any] | None = None,
    windows: tuple[int, ...] = RS_WINDOWS_DAYS,
) -> CalculatedFact:
    """RS = stock return - benchmark return over versioned windows."""
    family, group = "PARTICIPATION", "CG_RELATIVE_STRENGTH"
    bars = list_raw_bars(symbol, through=trading_date)
    closes = [float(bar.close) for bar in bars if bar.close is not None]
    shortest = min(windows)
    if len(closes) <= shortest or benchmark_bars is None:
        return CalculatedFact(
            family=family,
            code="UNKNOWN_RS_BENCHMARK_OR_HISTORY_INSUFFICIENT",
            ok=False,
            value=None,
            why=(
                "RS needs aligned benchmark history plus more closes than the "
                "shortest configured window."
            ),
            correlation_group=group,
        )
    bench_closes = [float(bar.close) for bar in benchmark_bars if bar.close is not None]
    results: dict[str, float] = {}
    for window in windows:
        if len(closes) <= window or len(bench_closes) <= window:
            continue
        stock_ret = (closes[-1] - closes[-window - 1]) / closes[-window - 1]
        bench_ret = (
            (bench_closes[-1] - bench_closes[-window - 1]) / bench_closes[-window - 1]
        )
        results[str(window)] = round(stock_ret - bench_ret, 6)
    if not results:
        return CalculatedFact(
            family=family,
            code="UNKNOWN_RS_WINDOWS_NOT_COMPUTABLE",
            ok=False,
            value=None,
            why="No configured window had enough aligned history.",
            correlation_group=group,
        )
    primary = results.get(str(windows[1]) if len(windows) > 1 else str(windows[0]), 0.0)
    return CalculatedFact(
        family=family,
        code="RS_MULTI_WINDOW_V1",
        ok=True,
        direction=_direction_from_sign(primary),
        value=primary,
        why=f"Stock minus benchmark return per window: {results}.",
        correlation_group=group,
    )


def named_deal_fact(symbol: str, large_deals: list[Any]) -> CalculatedFact:
    family, group = "EVENT_AND_SPONSOR", "CG_EVENT_ROOT"
    symbol_deals = [deal for deal in large_deals if deal.symbol.upper() == symbol.upper()]
    if not symbol_deals:
        return CalculatedFact(
            family=family,
            code="UNKNOWN_NO_LARGE_DEAL_ROW",
            ok=False,
            value=None,
            why="No bulk/block last-good row names this symbol.",
            correlation_group=group,
        )
    latest = max(symbol_deals, key=lambda deal: deal.date)
    client = (latest.client or "").strip()
    if not client:
        return CalculatedFact(
            family=family,
            code="UNNAMED_DEAL_NOT_FII",
            ok=False,
            direction=_direction_from_sign(1.0 if latest.side == "BUY" else -1.0)
            if latest.side
            else FactDirection.UNKNOWN,
            value=float(latest.quantity or 0),
            why=f"{latest.date} {latest.deal_type} deal has no client name; never labelled FII.",
            correlation_group=group,
        )
    upper = client.upper()
    like_fii = "FII" in upper or "FPI" in upper
    side = latest.side
    direction = (
        FactDirection.BULLISH
        if side == "BUY"
        else FactDirection.BEARISH
        if side == "SELL"
        else FactDirection.UNKNOWN
    )
    return CalculatedFact(
        family=family,
        code="NAMED_FII_LIKE_DEAL" if like_fii else "NAMED_DEAL",
        ok=True,
        direction=direction,
        value=float(latest.value or latest.quantity or 0),
        why=f"{latest.date} {latest.deal_type} {'BUY' if side == 'BUY' else 'SELL' if side == 'SELL' else 'SIDE?'} client={client}",
        correlation_group=group,
    )


def amfi_fact(symbol: str, amfi_map: dict[str, dict[str, Any]]) -> CalculatedFact:
    family, group = "SPONSOR_DELAYED", "CG_DELAYED_SPONSOR"
    entry = amfi_map.get(symbol.upper())
    if not entry:
        return CalculatedFact(
            family=family,
            code="UNKNOWN_MF_NO_AMFI_ROW",
            ok=False,
            value=None,
            why="No AMFI scheme-delta last-good row for this stock.",
            correlation_group=group,
        )
    net_qty = entry["net_quantity_change"]
    delta = (
        "NET_ADDED"
        if net_qty > 0
        else "NET_REDUCED"
        if net_qty < 0
        else "FLAT"
    )
    return CalculatedFact(
        family=family,
        code=f"DELAYED_MF_{delta}_{entry['month']}",
        ok=True,
        direction=_direction_from_sign(net_qty),
        value=float(net_qty),
        why=f"AMFI month={entry['month']} schemes +{entry['schemes_added']}/-{entry['schemes_reduced']}; delayed, never 'bought today'.",
        correlation_group=group,
    )


def shp_context_fact(symbol: str, shp_rows: list[dict[str, Any]] | None) -> CalculatedFact:
    """Delayed ownership context. FII% delta has no normalized parser."""
    family, group = "SPONSOR_DELAYED", "CG_DELAYED_SPONSOR"
    row = next(
        (
            item
            for item in (shp_rows or [])
            if str(item.get("symbol") or "").upper() == symbol.upper()
        ),
        None,
    )
    promoter = row.get("promoter_holding_pct") if isinstance(row, dict) else None
    public = row.get("public_holding_pct") if isinstance(row, dict) else None
    if promoter is None and public is None:
        return CalculatedFact(
            family=family,
            code="SHP_FII_DELTA_NOT_NORMALIZED",
            ok=False,
            value=None,
            why=(
                "Shareholding last-good lifts promoter/public context only; "
                "no normalized FII% vs prior-quarter parser exists."
            ),
            correlation_group=group,
        )
    return CalculatedFact(
        family=family,
        code="SHP_PROMOTER_PUBLIC_CONTEXT_DELAYED_QUARTER",
        ok=True,
        value=None,
        why=f"Promoter={promoter}% public={public}% (quarterly, delayed). shpFiiDelta stays null.",
        correlation_group=group,
    )


def market_fii_chip_fact(market_fii: Any) -> CalculatedFact:
    return CalculatedFact(
        family="MARKET_AND_SECTOR_CONTEXT",
        code="MARKET_FII_NET_CHIP",
        ok=market_fii.status == "CURRENT",
        value=market_fii.net_crore,
        why="Board-level whole-market net; never copied onto a symbol.",
        correlation_group="CG_MARKET_CONTEXT",
    )


def fo_package_fact(
    symbol: str,
    fo_symbols: set[str],
    quadrants: dict[str, str],
    oi_changes: dict[str, int] | None = None,
) -> CalculatedFact:
    family, group = "DERIVATIVES_FUTURES", "CG_FUTURES_OI"
    if symbol.upper() not in fo_symbols:
        return CalculatedFact(
            family=family,
            code="NOT_IN_A6_SHORTLIST_CASH_ONLY_NOT_PUNISHED",
            ok=False,
            value=None,
            why="Cash-only name; missing F&O never penalizes it.",
            correlation_group=group,
        )
    key = symbol.upper()
    quadrant = quadrants.get(key, "NEUTRAL_OR_UNKNOWN")
    oi_change = (oi_changes or {}).get(key)
    direction = (
        FactDirection.BULLISH
        if quadrant in {"LONG_BUILDUP", "SHORT_COVERING"}
        else FactDirection.BEARISH
        if quadrant in {"SHORT_BUILDUP", "LONG_UNWINDING"}
        else FactDirection.NEUTRAL
    )
    oi_note = f" OI change={oi_change}." if oi_change is not None else ""
    return CalculatedFact(
        family=family,
        code=f"FO_OI_PACKAGE_{quadrant}",
        ok=True,
        direction=direction,
        value=float(oi_change) if oi_change is not None else None,
        why=f"One futures-OI package per A6; OI level/change/quadrant share one family.{oi_note}",
        correlation_group=group,
    )


def preopen_gap_fact(symbol: str, preopen_map: dict[str, dict[str, float]]) -> CalculatedFact:
    family, group = "STRUCTURE", "CG_PRICE_STRUCTURE"
    row = preopen_map.get(symbol.upper())
    if not row:
        return CalculatedFact(
            family=family,
            code="UNKNOWN_NO_PREOPEN_SNAPSHOT",
            ok=False,
            value=None,
            why="No official pre-open IEP snapshot for this symbol.",
            correlation_group=group,
        )
    gap = float(row["gap_pct"])
    return CalculatedFact(
        family=family,
        code="PREOPEN_GAP_FTR001",
        ok=True,
        direction=_direction_from_sign(gap),
        value=round(gap, 4),
        why="IEP vs previous close from official pre-open; not a live ORB confirm.",
        correlation_group=group,
    )


def activity_join_fact(symbol: str, activity_symbols: set[str]) -> CalculatedFact:
    family, group = "PARTICIPATION", "CG_ACTIVITY_SESSION"
    if symbol.upper() not in activity_symbols:
        return CalculatedFact(
            family=family,
            code="ACTIVITY_SESSION_NOT_ON_MOST_ACTIVE",
            ok=False,
            value=None,
            why="Not on official most-active/volume-gainer last-good (same session as R2).",
            correlation_group=group,
        )
    return CalculatedFact(
        family=family,
        code="ACTIVITY_SESSION_JOIN_NOT_SECOND_VOTE",
        ok=True,
        why="Same cash-session activity root as R2; join only, never a second volume vote.",
        correlation_group=group,
    )


def official_event_fact(symbol: str, event_map: dict[str, str]) -> CalculatedFact:
    family, group = "EVENT_AND_SPONSOR", "CG_EVENT_ROOT"
    headline = event_map.get(symbol.upper())
    if not headline:
        return CalculatedFact(
            family=family,
            code="UNKNOWN_NO_OFFICIAL_EVENT_ROW",
            ok=False,
            value=None,
            why="No announcement/result/buyback last-good row names this symbol.",
            correlation_group=group,
        )
    return CalculatedFact(
        family=family,
        code="OFFICIAL_EVENT_AVAILABLE_AT",
        ok=True,
        why=f"Official event last-good: {headline}. Side unknown; not a second deal vote.",
        correlation_group=group,
    )


def r5_setup_fact(symbol: str, setups: dict[str, tuple[str, ...]], direction: FactDirection) -> CalculatedFact:
    family, group = "STRUCTURE", "CG_PRICE_STRUCTURE"
    tags = setups.get(symbol.upper()) or ()
    if not tags:
        return CalculatedFact(
            family=family,
            code="UNKNOWN_NO_R5_SETUP_TAG",
            ok=False,
            value=None,
            why="No hash-matched R5 closed-bar setup tag.",
            correlation_group=group,
        )
    return CalculatedFact(
        family=family,
        code="R5_SETUP_TAGS",
        ok=True,
        direction=direction,
        why=f"R5 closed-bar tags (WAIT): {','.join(tags)}.",
        correlation_group=group,
    )


def mcx_dte_days(expiry: str | None, as_of: date) -> int | None:
    if not expiry:
        return None
    text = str(expiry).strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return (datetime.strptime(text[:11].replace(" ", "-"), fmt).date() - as_of).days
        except ValueError:
            continue
    try:
        return (date.fromisoformat(text[:10]) - as_of).days
    except ValueError:
        return None


def options_fact() -> CalculatedFact:
    return CalculatedFact(
        family="DERIVATIVES_OPTIONS",
        code="OPTIONS_PACKAGE_UNKNOWN_NEEDS_R12",
        ok=False,
        value=None,
        why="Fresh expiry-scoped option chain contract is not wired; static PCR is not direction.",
        correlation_group="CG_OPTION_CHAIN",
    )


__all__ = [
    "CalculatedFact",
    "FactDirection",
    "RS_WINDOWS_DAYS",
    "activity_join_fact",
    "amfi_fact",
    "delivery_fact",
    "fo_package_fact",
    "gap_fact",
    "market_fii_chip_fact",
    "mcx_dte_days",
    "named_deal_fact",
    "official_event_fact",
    "options_fact",
    "preopen_gap_fact",
    "r5_setup_fact",
    "rs_fact",
    "shp_context_fact",
]
