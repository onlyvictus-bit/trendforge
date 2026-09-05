from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import fmean, pstdev
from typing import Any


FEATURE_VERSION = "1.0.0"
SOURCE_ROLE = "OFFICIAL_DELAYED_CONTEXT"
WINDOWS = (13, 26, 52, 156)


def _pick(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None


def _number(row: dict[str, Any], *keys: str) -> float:
    value = _pick(row, *keys)
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _normalize(row: dict[str, Any]) -> dict[str, Any] | None:
    report_date = _date_value(_pick(row, "report_date", "reportDate"))
    market = str(_pick(row, "market") or "").strip()
    if report_date is None or not market:
        return None
    return {
        "market": market,
        "contractMarketCode": str(
            _pick(row, "contract_market_code", "contractMarketCode") or ""
        ).strip()
        or None,
        "reportDate": report_date,
        "openInterest": _number(row, "open_interest", "openInterest"),
        "managedMoneyNet": _number(row, "managed_money_net", "managedMoneyNet"),
        "commercialNet": _number(row, "commercial_net", "commercialNet"),
        "swapDealerNet": _number(row, "swap_dealer_net", "swapDealerNet"),
        "otherReportableNet": _number(
            row, "other_reportable_net", "otherReportableNet"
        ),
        "nonReportableNet": _number(row, "non_reportable_net", "nonReportableNet"),
    }


def _window(values: list[float], size: int) -> list[float] | None:
    return values[-size:] if len(values) >= size else None


def _mean(values: list[float], size: int) -> float | None:
    sample = _window(values, size)
    return round(fmean(sample), 4) if sample else None


def _zscore(values: list[float], size: int) -> float | None:
    sample = _window(values, size)
    if not sample:
        return None
    deviation = pstdev(sample)
    return round((sample[-1] - fmean(sample)) / deviation, 4) if deviation else 0.0


def _percentile(values: list[float], size: int) -> float | None:
    sample = _window(values, size)
    if not sample:
        return None
    return round(sum(value <= sample[-1] for value in sample) / len(sample), 4)


def _position_state(current: float, change: float | None) -> str:
    if change is None:
        return "INSUFFICIENT_HISTORY"
    if current >= 0 and change > 0:
        return "BUILDING_LONGS"
    if current >= 0 and change < 0:
        return "REDUCING_LONGS"
    if current < 0 and change < 0:
        return "BUILDING_SHORTS"
    if current < 0 and change > 0:
        return "COVERING_SHORTS"
    return "UNCHANGED"


def _crowding(percentile_52: float | None, percentile_260: float | None) -> str:
    value = percentile_260 if percentile_260 is not None else percentile_52
    if value is None:
        return "INSUFFICIENT_HISTORY"
    if value >= 0.9:
        return "CROWDED_LONG"
    if value <= 0.1:
        return "CROWDED_SHORT"
    return "NOT_CROWDED"


def _price_divergence(
    current_date: str,
    previous_date: str | None,
    managed_change: float | None,
    price_by_date: dict[str, float] | None,
) -> str:
    if not price_by_date or not previous_date or managed_change is None:
        return "UNAVAILABLE_PRICE_SERIES"
    current_price = price_by_date.get(current_date)
    previous_price = price_by_date.get(previous_date)
    if current_price is None or previous_price is None:
        return "UNAVAILABLE_PRICE_SERIES"
    price_change = current_price - previous_price
    if managed_change > 0 and price_change < 0:
        return "FUNDS_BUYING_WEAKNESS"
    if managed_change < 0 and price_change > 0:
        return "FUNDS_SELLING_STRENGTH"
    if managed_change * price_change > 0:
        return "POSITION_PRICE_ALIGNED"
    return "NO_DIRECTIONAL_DIVERGENCE"


def _feature_row(
    history: list[dict[str, Any]], price_by_date: dict[str, float] | None
) -> dict[str, Any]:
    current = history[-1]
    previous = history[-2] if len(history) > 1 else None
    managed = [row["managedMoneyNet"] for row in history]
    open_interest = [row["openInterest"] for row in history]
    managed_change = (
        current["managedMoneyNet"] - previous["managedMoneyNet"] if previous else None
    )
    report_date = current["reportDate"].isoformat()
    percentile_52 = _percentile(managed, 52)
    percentile_260 = _percentile(managed, 260)
    return {
        "featureVersion": FEATURE_VERSION,
        "market": current["market"],
        "contractMarketCode": current["contractMarketCode"],
        "reportDate": report_date,
        "expectedReleaseDate": (current["reportDate"] + timedelta(days=3)).isoformat(),
        "observationCount": len(history),
        "openInterest": current["openInterest"],
        "openInterestChange1w": current["openInterest"] - previous["openInterest"]
        if previous
        else None,
        "managedMoneyNet": current["managedMoneyNet"],
        "managedMoneyNetChange1w": managed_change,
        "commercialNet": current["commercialNet"],
        "commercialNetChange1w": current["commercialNet"] - previous["commercialNet"]
        if previous
        else None,
        "swapDealerNet": current["swapDealerNet"],
        "swapDealerNetChange1w": current["swapDealerNet"] - previous["swapDealerNet"]
        if previous
        else None,
        "otherReportableNet": current["otherReportableNet"],
        "nonReportableNet": current["nonReportableNet"],
        "managedMoneyMean13w": _mean(managed, 13),
        "managedMoneyMean26w": _mean(managed, 26),
        "managedMoneyMean52w": _mean(managed, 52),
        "managedMoneyMean156w": _mean(managed, 156),
        "managedMoneyZscore52w": _zscore(managed, 52),
        "managedMoneyZscore156w": _zscore(managed, 156),
        "openInterestZscore52w": _zscore(open_interest, 52),
        "openInterestZscore156w": _zscore(open_interest, 156),
        "managedMoneyPercentile52w": percentile_52,
        "managedMoneyPercentile260w": percentile_260,
        "positionState": _position_state(current["managedMoneyNet"], managed_change),
        "crowdingState": _crowding(percentile_52, percentile_260),
        "positionPriceDivergence": _price_divergence(
            report_date,
            previous["reportDate"].isoformat() if previous else None,
            managed_change,
            price_by_date,
        ),
        "commercialInterpretation": "HEDGING_CATEGORY_CONTEXT_ONLY",
        "scope": "COMMODITY_REGIME_ONLY",
        "sourceRole": SOURCE_ROLE,
        "canUnlockReady": False,
    }


def build_cftc_feature_history(
    positions: list[dict[str, Any]],
    *,
    as_of: date | datetime | str | None = None,
    price_by_date: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    cutoff = _date_value(as_of) if as_of is not None else None
    grouped: dict[str, dict[date, dict[str, Any]]] = {}
    for raw in positions:
        row = _normalize(raw)
        if row is None or (cutoff and row["reportDate"] > cutoff):
            continue
        key = row["contractMarketCode"] or row["market"]
        grouped.setdefault(key, {})[row["reportDate"]] = row

    features: list[dict[str, Any]] = []
    for rows_by_date in grouped.values():
        ordered = [rows_by_date[key] for key in sorted(rows_by_date)]
        for index in range(len(ordered)):
            features.append(_feature_row(ordered[: index + 1], price_by_date))
    return sorted(features, key=lambda row: (row["reportDate"], row["market"]))
