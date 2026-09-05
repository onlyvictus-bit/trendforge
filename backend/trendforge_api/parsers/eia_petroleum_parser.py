from __future__ import annotations

import csv
import io
import re
from datetime import datetime


REQUIRED_METRICS = {
    "Commercial (Excluding SPR)": "COMMERCIAL_EXCLUDING_SPR",
    "Total Motor Gasoline": "TOTAL_MOTOR_GASOLINE",
    "Distillate Fuel Oil": "DISTILLATE_FUEL_OIL",
}


def _wait_schema(reason: str) -> dict:
    return {
        "parser_state": "WAIT_SCHEMA_MISMATCH",
        "data_date": None,
        "record_count": 0,
        "summary": f"EIA weekly petroleum schema validation failed: {reason}",
        "output": {"qualityIssues": [reason]},
        "error": reason,
    }


def _parse_date(value: str) -> str:
    return datetime.strptime(value.strip(), "%m/%d/%y").date().isoformat()


def _parse_float(value: str) -> float:
    return float(value.strip().replace(",", ""))


def _metric_key(name: str) -> str:
    known = REQUIRED_METRICS.get(name)
    if known:
        return known
    return re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")


def parse_eia_petroleum_stocks(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
) -> dict:
    del url, last_modified
    text = content.decode("utf-8-sig", errors="replace").replace("\x1a", "")
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return _wait_schema("empty CSV")
    if len(header) != 8 or header[0].strip().upper() != "STUB_1":
        return _wait_schema("expected the eight-column weekly stocks table")
    try:
        current_date = _parse_date(header[1])
        previous_date = _parse_date(header[2])
        year_ago_date = _parse_date(header[5])
    except ValueError:
        return _wait_schema("invalid weekly stock date header")

    rows: list[dict[str, object]] = []
    names: set[str] = set()
    for line_number, row in enumerate(reader, start=2):
        if not row or not any(value.strip() for value in row):
            continue
        if row[0].strip().upper() == "STUB_1":
            break
        if len(row) != 8:
            return _wait_schema(f"line {line_number} has {len(row)} columns")
        name = " ".join(row[0].split())
        if not name or name in names:
            return _wait_schema(f"invalid or duplicate metric at line {line_number}")
        try:
            values = [_parse_float(value) for value in row[1:]]
        except ValueError:
            return _wait_schema(f"line {line_number} has invalid numeric data")
        names.add(name)
        rows.append(
            {
                "metricKey": _metric_key(name),
                "metricName": name,
                "observationDate": current_date,
                "previousWeekDate": previous_date,
                "yearAgoDate": year_ago_date,
                "currentValue": values[0],
                "previousWeekValue": values[1],
                "weeklyChange": values[2],
                "weeklyPercentChange": values[3],
                "yearAgoValue": values[4],
                "yearChange": values[5],
                "yearPercentChange": values[6],
                "units": "million_barrels",
            }
        )

    missing = sorted(set(REQUIRED_METRICS) - names)
    if missing:
        return _wait_schema("missing required metrics: " + ", ".join(missing))
    commercial = next(
        item for item in rows if item["metricKey"] == "COMMERCIAL_EXCLUDING_SPR"
    )
    weekly_change_value = commercial.get("weeklyChange")
    if not isinstance(weekly_change_value, (int, float)):
        return _wait_schema("commercial inventory change is not numeric")
    weekly_change = float(weekly_change_value)
    bias = (
        "BEARISH_BUILD"
        if weekly_change > 0
        else "BULLISH_DRAW"
        if weekly_change < 0
        else "NEUTRAL"
    )
    return {
        "parser_state": "PARSED_STRUCTURED",
        "data_date": current_date,
        "record_count": len(rows),
        "summary": f"Parsed {len(rows)} EIA weekly petroleum stock metrics.",
        "output": {
            "rows": rows,
            "crudeInventoryBias": bias,
            "scope": "MCX_CRUDE_DELAYED_CONTEXT_ONLY",
        },
    }
