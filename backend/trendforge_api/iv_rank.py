"""Fail-closed ATM implied-volatility history and rank helpers.

This module derives a display statistic from provider or exchange IV. It is not
a source, vote, score term, or synthetic replacement for missing observations.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(str(value).strip().replace(",", "").replace("%", ""))
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _iv_percent(row: Mapping[str, Any], side: str) -> float | None:
    provider_value = _number(row.get(f"{side}_iv"))
    if provider_value is not None:
        return provider_value * 100 if provider_value <= 3 else provider_value
    exchange_value = _number(row.get(f"{side}_impliedVolatility"))
    return exchange_value


def select_atm_iv_observation(
    rows: Iterable[Mapping[str, Any]],
    *,
    data_date: str,
    source_key: str | None = None,
) -> dict[str, Any]:
    """Select the closest strike and average its populated CE/PE IV values."""
    candidates = []
    for row in rows:
        strike = _number(row.get("strikePrice") or row.get("strike_price"))
        spot = _number(
            row.get("underlyingSpotPrice")
            or row.get("underlyingValue")
            or row.get("underlying_spot_price")
        )
        if strike is None or spot is None:
            continue
        ivs = [value for side in ("CE", "PE") if (value := _iv_percent(row, side)) is not None]
        if not ivs:
            continue
        candidates.append(
            (
                abs(strike - spot),
                strike,
                spot,
                sum(ivs) / len(ivs),
                len(ivs),
                row,
            )
        )
    if not candidates:
        return {
            "state": "WAIT_MISSING_ATM_IV",
            "dataDate": data_date,
            "atmIvPct": None,
            "scoreEligible": False,
        }
    _, strike, spot, iv, leg_count, selected = min(
        candidates, key=lambda item: (item[0], item[1])
    )
    return {
        "state": "OBSERVED",
        "sourceKey": source_key,
        "underlyingKey": selected.get("underlyingKey"),
        "expiry": selected.get("expiry"),
        "dataDate": data_date,
        "strikePrice": strike,
        "underlyingSpotPrice": spot,
        "atmIvPct": round(iv, 6),
        "legCount": leg_count,
        "scoreEligible": False,
    }


def calculate_iv_rank(
    observations: Iterable[Mapping[str, Any]],
    *,
    valid_trading_dates: Iterable[str] | None = None,
    underlying_key: str | None = None,
    min_sessions: int = 252,
) -> dict[str, Any]:
    """Return IV rank/percentile only over an official distinct-session window."""
    if min_sessions < 2:
        raise ValueError("min_sessions must be at least 2")
    if valid_trading_dates is None:
        return {
            "state": "WAIT_CALENDAR_REQUIRED",
            "sessionsAvailable": 0,
            "sessionsRequired": min_sessions,
            "ivRankPct": None,
            "ivPercentilePct": None,
            "scoreEligible": False,
        }

    official_sessions = {str(item).strip() for item in valid_trading_dates}
    by_date: dict[str, float] = {}
    rejected = 0
    for observation in observations:
        data_date = str(observation.get("dataDate") or "").strip()
        iv = _number(observation.get("atmIvPct"))
        observation_underlying = str(
            observation.get("underlyingKey") or ""
        ).strip()
        try:
            parsed_date = date.fromisoformat(data_date)
        except ValueError:
            rejected += 1
            continue
        if (
            data_date not in official_sessions
            or parsed_date.weekday() >= 5
            or iv is None
            or (
                underlying_key is not None
                and observation_underlying != underlying_key
            )
        ):
            rejected += 1
            continue
        by_date[data_date] = iv

    dates = sorted(by_date)
    available = len(dates)
    if available < min_sessions:
        return {
            "state": "WAIT_INSUFFICIENT_HISTORY",
            "sessionsAvailable": available,
            "sessionsRequired": min_sessions,
            "rejectedObservationCount": rejected,
            "ivRankPct": None,
            "ivPercentilePct": None,
            "scoreEligible": False,
        }

    window_dates = dates[-min_sessions:]
    values = [by_date[data_date] for data_date in window_dates]
    current = values[-1]
    low = min(values)
    high = max(values)
    rank = None if high == low else (current - low) / (high - low) * 100
    percentile = sum(value <= current for value in values) / len(values) * 100
    return {
        "state": "READY_INFORMATIONAL",
        "dataDate": window_dates[-1],
        "sessionsAvailable": available,
        "sessionsUsed": min_sessions,
        "rejectedObservationCount": rejected,
        "currentAtmIvPct": current,
        "windowLowIvPct": low,
        "windowHighIvPct": high,
        "ivRankPct": round(rank, 6) if rank is not None else None,
        "ivPercentilePct": round(percentile, 6),
        "derived": True,
        "scoreEligible": False,
    }
