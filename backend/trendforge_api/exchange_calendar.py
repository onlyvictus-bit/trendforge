from __future__ import annotations

from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo

from .storage import exchange_calendar_coverage, list_exchange_calendar_days


IST = ZoneInfo("Asia/Kolkata")
EOD_PUBLICATION_CUTOFF = time(18, 0)
NSE_PRE_OPEN = time(9, 0)
NSE_SESSION_START = time(9, 15)
NSE_SESSION_END = time(15, 30)
NSE_EOD_POLL_START = time(15, 35)


class NseSessionPhase(StrEnum):
    PRE_OPEN = "PRE_OPEN"
    OPEN = "OPEN"
    EOD_WINDOW = "EOD_WINDOW"
    CLOSED_NON_TRADING = "CLOSED_NON_TRADING"


def evaluate_nse_calendar(
    at: datetime | date | None = None, *, segment: str = "CM"
) -> dict[str, Any]:
    if at is None:
        local_date = datetime.now(IST).date()
    elif isinstance(at, datetime):
        localized = at.replace(tzinfo=IST) if at.tzinfo is None else at.astimezone(IST)
        local_date = localized.date()
    else:
        local_date = at

    segment = segment.strip().upper()
    coverage = exchange_calendar_coverage(
        exchange="NSE", segment=segment, year=local_date.year
    )
    if coverage is None:
        return {
            "exchange": "NSE",
            "segment": segment,
            "tradingDate": local_date.isoformat(),
            "state": "WAIT_CALENDAR_DATA",
            "isTradingDay": False,
            "canRunScheduledScan": False,
            "reason": f"No structured official NSE {segment} calendar coverage for {local_date.year}.",
            "coverage": None,
        }

    rows = list_exchange_calendar_days(
        exchange="NSE", segment=segment, trading_date=local_date.isoformat()
    )
    special = next((row for row in rows if row["state"] == "OPEN_SPECIAL"), None)
    closed = next((row for row in rows if row["state"] == "CLOSED"), None)
    if special:
        state, is_open = "OPEN_SPECIAL", True
        reason = special["description"]
    elif closed:
        state, is_open = "CLOSED_HOLIDAY", False
        reason = closed["description"]
    elif local_date.weekday() >= 5:
        state, is_open = "CLOSED_WEEKEND", False
        reason = "Weekend is closed unless an official special-session record opens it."
    else:
        state, is_open = "OPEN_NORMAL", True
        reason = "Covered weekday with no official closure record."
    return {
        "exchange": "NSE",
        "segment": segment,
        "tradingDate": local_date.isoformat(),
        "state": state,
        "isTradingDay": is_open,
        "canRunScheduledScan": is_open,
        "reason": reason,
        "coverage": coverage,
    }


def expected_latest_nse_eod_date(
    at: datetime | None = None, *, segment: str = "CM"
) -> date | None:
    local = (at or datetime.now(IST)).astimezone(IST)
    today_state = evaluate_nse_calendar(local, segment=segment)
    if today_state["state"] == "WAIT_CALENDAR_DATA":
        return None
    cursor = local.date()
    if today_state["isTradingDay"] and local.time() >= EOD_PUBLICATION_CUTOFF:
        return cursor
    cursor -= timedelta(days=1)
    for _ in range(15):
        state = evaluate_nse_calendar(cursor, segment=segment)
        if state["state"] == "WAIT_CALENDAR_DATA":
            return None
        if state["isTradingDay"]:
            return cursor
        cursor -= timedelta(days=1)
    return None


def nse_session_phase(
    at: datetime | None = None,
    *,
    calendar: dict[str, Any] | None = None,
    segment: str = "CM",
) -> NseSessionPhase:
    local = (at or datetime.now(IST)).astimezone(IST)
    status = calendar if calendar is not None else evaluate_nse_calendar(local, segment=segment)
    if not status.get("isTradingDay"):
        return NseSessionPhase.CLOSED_NON_TRADING
    clock = local.time()
    if clock >= NSE_EOD_POLL_START:
        return NseSessionPhase.EOD_WINDOW
    if clock >= NSE_SESSION_START:
        return NseSessionPhase.OPEN
    if clock >= NSE_PRE_OPEN:
        return NseSessionPhase.PRE_OPEN
    return NseSessionPhase.PRE_OPEN


def expected_research_session_date(
    at: datetime | None = None, *, segment: str = "CM"
) -> date | None:
    """Closed official cash session R5 may research right now.

    OPEN / PRE_OPEN: previous trading day (today's bar is not closed).
    EOD_WINDOW on a trading day: today (poll official files; last-good stays
    until the dated artifact actually parses as today).
    Holiday / weekend: last trading day, never relabelled as calendar today.
    """
    local = (at or datetime.now(IST)).astimezone(IST)
    today_state = evaluate_nse_calendar(local, segment=segment)
    if today_state["state"] == "WAIT_CALENDAR_DATA":
        return None
    phase = nse_session_phase(local, calendar=today_state, segment=segment)
    cursor = local.date()
    if phase is NseSessionPhase.EOD_WINDOW and today_state["isTradingDay"]:
        return cursor
    cursor -= timedelta(days=1)
    for _ in range(15):
        state = evaluate_nse_calendar(cursor, segment=segment)
        if state["state"] == "WAIT_CALENDAR_DATA":
            return None
        if state["isTradingDay"]:
            return cursor
        cursor -= timedelta(days=1)
    return None
