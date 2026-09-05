"""Expiry calendar law for the four OI/options rooms.

Verified 2026 schedule (user-verified 2026-08-23): NIFTY weekly options
expire on TUESDAY (shifted to the previous trading day when Tuesday is a
holiday); every NSE monthly contract - NIFTY/BANKNIFTY/FINNIFTY/
MIDCPNIFTY and all single-stock F&O - expires on the LAST Tuesday of the
month. The last Tuesday is therefore the mega-expiry: weekly + monthly +
all stock contracts settle together. Stock F&O is physically settled;
holding an ITM stock position into that expiry forces delivery, so the
research surface raises a hard block from T-2 sessions.
"""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)

WEEKLY_EXPIRY_WEEKDAY = 1  # Tuesday


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    cursor = next_month_first - timedelta(days=1)
    while cursor.weekday() != weekday:
        cursor -= timedelta(days=1)
    return cursor


def last_tuesday(year: int, month: int) -> date:
    return _last_weekday_of_month(year, month, WEEKLY_EXPIRY_WEEKDAY)


def is_mega_expiry(expiry: date) -> bool:
    """True when the expiry is also the monthly last-Tuesday settlement."""
    return expiry == last_tuesday(expiry.year, expiry.month)


def next_weekly_expiry(
    on_date: date,
    *,
    holidays: frozenset[date] = frozenset(),
) -> date:
    """Next NIFTY-style weekly expiry on/after on_date (holiday-shifted)."""
    days_ahead = (WEEKLY_EXPIRY_WEEKDAY - on_date.weekday()) % 7
    candidate = on_date + timedelta(days=days_ahead)
    while candidate in holidays:
        candidate -= timedelta(days=1)
    return candidate


def previous_trading_day(day: date, *, holidays: frozenset[date] = frozenset()) -> date:
    cursor = day - timedelta(days=1)
    while cursor.weekday() >= 5 or cursor in holidays:
        cursor -= timedelta(days=1)
    return cursor


def physical_delivery_block_start(
    expiry: date,
    *,
    holidays: frozenset[date] = frozenset(),
    sessions_ahead: int = 2,
) -> date:
    """First session at which the ITM stock F&O hard block must be active."""
    cursor = expiry
    for _ in range(sessions_ahead):
        cursor = previous_trading_day(cursor, holidays=holidays)
    return cursor


class ExpiryContext(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    expiry: str
    dte_calendar_days: int
    is_tuesday: bool
    is_mega_expiry: bool
    mega_expiry_stress_tag: str
    physical_block_active_from: str | None = None


def expiry_context(
    expiry: date,
    *,
    today: date,
    holidays: frozenset[date] = frozenset(),
) -> ExpiryContext:
    mega = is_mega_expiry(expiry)
    block_from = (
        physical_delivery_block_start(expiry, holidays=holidays).isoformat()
        if mega
        else None
    )
    return ExpiryContext(
        expiry=expiry.isoformat(),
        dte_calendar_days=(expiry - today).days,
        is_tuesday=expiry.weekday() == WEEKLY_EXPIRY_WEEKDAY,
        is_mega_expiry=mega,
        mega_expiry_stress_tag=(
            "MEGA_EXPIRY_LAST_TUESDAY_WEEKLY_MONTHLY_ALL_STOCKS"
            if mega
            else "NOT_MEGA_EXPIRY"
        ),
        physical_block_active_from=block_from,
    )
