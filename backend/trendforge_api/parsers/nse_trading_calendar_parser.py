from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .common import extract_data_date, source_result


def _parse_date(value: object) -> str | None:
    text = str(value or "").strip()
    for pattern in ("%d-%b-%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _explicit_special_open(item: dict[str, Any]) -> bool:
    state = (
        str(
            item.get("sessionState")
            or item.get("session_state")
            or item.get("marketState")
            or ""
        )
        .strip()
        .upper()
    )
    explicit = item.get("isSpecialSession", item.get("is_special_session"))
    return explicit is True or state in {"OPEN_SPECIAL", "SPECIAL_OPEN"}


def parse_nse_trading_calendar(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="NSE trading calendar is not valid JSON.",
            output={"scope": "NSE_TRADING_CALENDAR"},
            error=str(exc),
        )
    if not isinstance(payload, dict):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="NSE trading calendar root must be an object keyed by segment.",
            output={"scope": "NSE_TRADING_CALENDAR"},
        )

    rows: list[dict[str, Any]] = []
    coverage: set[tuple[str, int]] = set()
    malformed = 0
    for raw_segment, values in payload.items():
        if not isinstance(values, list):
            continue
        segment = str(raw_segment).strip().upper()
        for item in values:
            if not isinstance(item, dict):
                malformed += 1
                continue
            trading_date = _parse_date(item.get("tradingDate"))
            description = str(item.get("description") or "").strip()
            if not trading_date or not description:
                malformed += 1
                continue
            special_open = _explicit_special_open(item)
            rows.append(
                {
                    "exchange": "NSE",
                    "segment": segment,
                    "tradingDate": trading_date,
                    "weekDay": str(item.get("weekDay") or "").strip() or None,
                    "state": "OPEN_SPECIAL" if special_open else "CLOSED",
                    "description": description,
                    "morningSession": item.get("morning_session"),
                    "eveningSession": item.get("evening_session"),
                    "explicitSpecialSession": special_open,
                }
            )
            coverage.add((segment, int(trading_date[:4])))

    if not rows or not any(segment == "CM" for segment, _ in coverage):
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="No schema-valid NSE cash-market calendar rows were found.",
            output={"scope": "NSE_TRADING_CALENDAR", "malformedRows": malformed},
        )

    data_date, date_source = extract_data_date("", url, last_modified)
    if not data_date:
        return source_result(
            parser_state="WAIT_SOURCE_DATE",
            data_date=None,
            record_count=0,
            summary="NSE calendar response lacks an authoritative retrieval date.",
            output={"scope": "NSE_TRADING_CALENDAR", "rows": rows},
        )
    coverage_rows = [
        {
            "exchange": "NSE",
            "segment": segment,
            "year": year,
            "validFrom": f"{year:04d}-01-01",
            "validTo": f"{year:04d}-12-31",
        }
        for segment, year in sorted(coverage)
    ]
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary="Official NSE segment holiday calendar parsed with annual coverage.",
        output={
            "scope": "NSE_TRADING_CALENDAR",
            "dateSource": date_source,
            "rows": rows,
            "coverage": coverage_rows,
            "malformedRows": malformed,
            "warning": "Weekend special sessions require an explicit OPEN_SPECIAL record; names are never inferred.",
        },
    )
