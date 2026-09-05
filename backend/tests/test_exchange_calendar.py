from __future__ import annotations

import json
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.exchange_calendar import (
    NseSessionPhase,
    evaluate_nse_calendar,
    expected_latest_nse_eod_date,
    expected_research_session_date,
    nse_session_phase,
)
from trendforge_api.models import SourceParseResult
from trendforge_api.parsers.nse_trading_calendar_parser import (
    parse_nse_trading_calendar,
)
from trendforge_api.scanner_scheduler import ScannerScheduler
from trendforge_api.main import app


def fixture_payload(*, special_open: bool = False) -> bytes:
    rows = [
        {
            "tradingDate": "26-Jan-2026",
            "weekDay": "Monday",
            "description": "Republic Day",
            "morning_session": None,
            "evening_session": None,
            "Sr_no": 1,
        }
    ]
    if special_open:
        rows.append(
            {
                "tradingDate": "11-Jul-2026",
                "weekDay": "Saturday",
                "description": "Official special trading session",
                "isSpecialSession": True,
            }
        )
    return json.dumps({"CM": rows, "FO": rows}).encode()


def persist_calendar(content: bytes) -> None:
    parsed = parse_nse_trading_calendar(
        content, last_modified="Sat, 11 Jul 2026 06:00:00 GMT"
    )
    result = SourceParseResult(
        sourceKey="nse_trading_calendar",
        snapshotId=1,
        parserState=parsed["parser_state"],
        dataDate=parsed["data_date"],
        recordCount=parsed["record_count"],
        summary=parsed["summary"],
        output=parsed["output"],
        error=parsed["error"],
        parsedAt=datetime.now(timezone.utc).isoformat(),
    )
    result.id = 1
    storage.save_structured_source_rows(result)


def test_parser_normalizes_segment_holidays_and_coverage() -> None:
    result = parse_nse_trading_calendar(
        fixture_payload(), last_modified="Sat, 11 Jul 2026 06:00:00 GMT"
    )
    assert result["parser_state"] == "PARSED_STRUCTURED"
    assert result["data_date"] == "2026-07-11"
    assert result["record_count"] == 2
    assert result["output"]["rows"][0]["state"] == "CLOSED"
    assert {row["segment"] for row in result["output"]["coverage"]} == {"CM", "FO"}


def test_parser_fails_closed_on_invalid_or_missing_cash_market_data() -> None:
    invalid = parse_nse_trading_calendar(b"not-json")
    assert invalid["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    no_cash = parse_nse_trading_calendar(
        json.dumps({"FO": []}).encode(),
        last_modified="Sat, 11 Jul 2026 06:00:00 GMT",
    )
    assert no_cash["parser_state"] == "WAIT_EMPTY_PARSE"


def test_calendar_requires_coverage_and_handles_weekday_holiday_weekend(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "calendar.db")
    missing = evaluate_nse_calendar(date(2026, 7, 10))
    assert missing["state"] == "WAIT_CALENDAR_DATA"
    assert missing["canRunScheduledScan"] is False

    persist_calendar(fixture_payload())
    weekday = evaluate_nse_calendar(date(2026, 7, 10))
    holiday = evaluate_nse_calendar(date(2026, 1, 26))
    weekend = evaluate_nse_calendar(date(2026, 7, 11))
    assert weekday["state"] == "OPEN_NORMAL"
    assert holiday["state"] == "CLOSED_HOLIDAY"
    assert weekend["state"] == "CLOSED_WEEKEND"


def test_weekend_opens_only_with_explicit_special_session(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "special.db")
    persist_calendar(fixture_payload(special_open=True))
    result = evaluate_nse_calendar(date(2026, 7, 11))
    assert result["state"] == "OPEN_SPECIAL"
    assert result["canRunScheduledScan"] is True


def test_aware_datetime_is_evaluated_in_india_timezone(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "timezone.db")
    persist_calendar(fixture_payload())
    result = evaluate_nse_calendar(datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc))
    assert result["tradingDate"] == "2026-07-11"
    assert result["state"] == "CLOSED_WEEKEND"


def test_background_scheduler_skips_when_calendar_is_not_open(monkeypatch) -> None:
    blocked = {
        "state": "WAIT_CALENDAR_DATA",
        "canRunScheduledScan": False,
        "isTradingDay": False,
        "reason": "fixture",
    }
    monkeypatch.setattr(
        "trendforge_api.scanner_scheduler.evaluate_nse_calendar", lambda: blocked
    )
    result = ScannerScheduler().run_once(trigger="scheduler")
    assert result["status"] == "WAIT_CALENDAR_DATA"
    assert result["candidateCount"] == 0


def test_calendar_api_exposes_status_and_rows(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "calendar-api.db")
    persist_calendar(fixture_payload())
    client = TestClient(app)
    status = client.get(
        "/api/calendar/status", params={"at": "2026-01-26T10:00:00+05:30"}
    )
    days = client.get("/api/calendar/days", params={"segment": "CM", "year": 2026})
    assert status.status_code == 200
    assert status.json()["state"] == "CLOSED_HOLIDAY"
    assert days.status_code == 200
    assert len(days.json()) == 1


def test_expected_eod_date_respects_weekend_and_publication_cutoff(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "expected-eod.db")
    persist_calendar(fixture_payload())
    monday_before_publish = datetime.fromisoformat("2026-07-13T10:00:00+05:30")
    monday_after_publish = datetime.fromisoformat("2026-07-13T18:30:00+05:30")
    saturday = datetime.fromisoformat("2026-07-11T12:00:00+05:30")
    assert expected_latest_nse_eod_date(monday_before_publish) == date(2026, 7, 10)
    assert expected_latest_nse_eod_date(monday_after_publish) == date(2026, 7, 13)
    assert expected_latest_nse_eod_date(saturday) == date(2026, 7, 10)


def test_session_phase_and_research_date_follow_open_close_holiday(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "session-phase.db")
    persist_calendar(fixture_payload())
    open_morning = datetime.fromisoformat("2026-07-10T10:00:00+05:30")
    eod_afternoon = datetime.fromisoformat("2026-07-10T16:00:00+05:30")
    pre_open = datetime.fromisoformat("2026-07-10T08:30:00+05:30")
    saturday = datetime.fromisoformat("2026-07-11T12:00:00+05:30")
    holiday = datetime.fromisoformat("2026-01-26T16:00:00+05:30")
    assert nse_session_phase(open_morning) is NseSessionPhase.OPEN
    assert nse_session_phase(eod_afternoon) is NseSessionPhase.EOD_WINDOW
    assert nse_session_phase(pre_open) is NseSessionPhase.PRE_OPEN
    assert nse_session_phase(saturday) is NseSessionPhase.CLOSED_NON_TRADING
    assert nse_session_phase(holiday) is NseSessionPhase.CLOSED_NON_TRADING
    assert expected_research_session_date(open_morning) == date(2026, 7, 9)
    assert expected_research_session_date(eod_afternoon) == date(2026, 7, 10)
    assert expected_research_session_date(saturday) == date(2026, 7, 10)
    assert expected_research_session_date(holiday) == date(2026, 1, 23)
