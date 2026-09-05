"""Fail-closed parsers for free official global context replacements."""

from __future__ import annotations

import calendar
import io
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

from .common import source_result


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:  # NaN
        return None
    return parsed


def parse_eia_steo_opec_supply(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    """Parse OPEC/OPEC+ supply from the official monthly STEO workbook."""
    try:
        import pandas as pd

        frame = pd.read_excel(io.BytesIO(content), sheet_name="3ctab", header=None)
    except Exception as exc:  # noqa: BLE001
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary=f"EIA STEO workbook unreadable: {exc}",
            output={"rows": [], "metric": "SUPPLY_PRODUCTION_NOT_QUOTA"},
            error=str(exc),
        )
    heading = " ".join(str(value) for value in frame.iloc[:2].to_numpy().ravel())
    if "World Petroleum" not in heading or len(frame) < 6 or frame.shape[1] < 4:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="EIA STEO 3ctab schema marker is missing.",
            output={"rows": [], "metric": "SUPPLY_PRODUCTION_NOT_QUOTA"},
        )
    forecast_date: str | None = None
    for value in frame.iloc[:6, :2].to_numpy().ravel():
        text = str(value).strip()
        for fmt in ("%A, %B %d, %Y", "%B %d, %Y"):
            try:
                forecast_date = datetime.strptime(text, fmt).date().isoformat()
                break
            except ValueError:
                continue
        if forecast_date:
            break
    if forecast_date is None:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="EIA STEO forecast date is missing.",
            output={"rows": [], "metric": "SUPPLY_PRODUCTION_NOT_QUOTA"},
        )
    periods: dict[int, str] = {}
    current_year: int | None = None
    for column in range(2, frame.shape[1]):
        year_value = _number(frame.iat[2, column])
        if year_value is not None and 2000 <= int(year_value) <= 2100:
            current_year = int(year_value)
        month_text = str(frame.iat[3, column]).strip()[:3].title()
        if current_year and month_text in calendar.month_abbr:
            month = list(calendar.month_abbr).index(month_text)
            periods[column] = f"{current_year:04d}-{month:02d}"
    wanted = {
        "papr_opec",
        "papr_opecplus",
        "papr_opecplus_opec",
        "papr_opecplus_other",
    }
    rows: list[dict[str, Any]] = []
    source_cells = 0
    for row_index in range(4, len(frame)):
        code = str(frame.iat[row_index, 0]).strip().casefold()
        if code not in wanted:
            continue
        label = str(frame.iat[row_index, 1]).strip()
        for column, period in periods.items():
            value = _number(frame.iat[row_index, column])
            if value is None or value <= 0:
                continue
            source_cells += 1
            rows.append(
                {
                    "dataDate": forecast_date,
                    "period": period,
                    "seriesCode": code,
                    "seriesLabel": label,
                    "millionBarrelsPerDay": value,
                    "metric": "SUPPLY_PRODUCTION",
                    "isQuota": False,
                    "scope": "GLOBAL_OIL_SUPPLY_CONTEXT_ONLY",
                }
            )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=forecast_date,
            record_count=0,
            summary="EIA STEO workbook contained no positive OPEC supply rows.",
            output={"rows": [], "metric": "SUPPLY_PRODUCTION_NOT_QUOTA"},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=forecast_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} dated EIA OPEC/OPEC+ supply observations.",
        output={
            "rows": rows,
            "records": rows,
            "sourceRowCount": source_cells,
            "metric": "SUPPLY_PRODUCTION_NOT_QUOTA",
            "canProveQuota": False,
        },
    )


def _month(value: str) -> str | None:
    try:
        parsed = datetime.strptime(value.strip(), "%B %Y")
    except ValueError:
        return None
    return parsed.strftime("%Y-%m")


def parse_opec_production_adjustment(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    """Parse an aggregate adjustment event; country quota tables are not inferred."""
    parser = _Text()
    parser.feed(content.decode("utf-8", errors="replace"))
    text = " ".join(parser.parts)
    adjustment = re.search(
        r"production adjustment of\s+([0-9,]+)\s+thousand barrels per day",
        text,
        re.I,
    )
    effective = re.search(r"implemented in\s+([A-Za-z]+\s+20\d{2})", text, re.I)
    meeting = re.search(r"met virtually on\s+(\d{1,2}\s+[A-Za-z]+\s+20\d{2})", text, re.I)
    countries_match = re.search(r"namely\s+(.+?)\s+met virtually", text, re.I)
    if adjustment is None or effective is None or meeting is None:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="OPEC release lacked a dated aggregate production-adjustment contract.",
            output={"rows": [], "metric": "PRODUCTION_ADJUSTMENT_NOT_QUOTA"},
        )
    try:
        data_date = datetime.strptime(meeting.group(1), "%d %B %Y").date().isoformat()
    except ValueError:
        data_date = None
    effective_month = _month(effective.group(1))
    if data_date is None or effective_month is None:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="OPEC adjustment dates were not parseable.",
            output={"rows": [], "metric": "PRODUCTION_ADJUSTMENT_NOT_QUOTA"},
        )
    countries_text = countries_match.group(1) if countries_match else ""
    countries = [
        item.strip(" ,.")
        for item in re.split(r",|\band\b", countries_text, flags=re.I)
        if item.strip(" ,.")
    ]
    row = {
        "dataDate": data_date,
        "effectiveMonth": effective_month,
        "adjustmentThousandBarrelsPerDay": int(adjustment.group(1).replace(",", "")),
        "participatingCountries": countries,
        "metric": "PRODUCTION_ADJUSTMENT",
        "isQuota": False,
        "countryRequiredProductionAvailable": False,
        "releaseUrl": url,
        "scope": "GLOBAL_OIL_POLICY_CONTEXT_ONLY",
    }
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=1,
        summary="Parsed one official OPEC aggregate production-adjustment event.",
        output={
            "rows": [row],
            "records": [row],
            "metric": "PRODUCTION_ADJUSTMENT_NOT_QUOTA",
            "canProveCountryQuota": False,
        },
    )
