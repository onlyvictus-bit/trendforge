from __future__ import annotations

import csv
import io
from datetime import date


def _wait_schema(reason: str) -> dict:
    return {
        "parser_state": "WAIT_SCHEMA_MISMATCH",
        "data_date": None,
        "record_count": 0,
        "summary": f"FRED series schema validation failed: {reason}",
        "output": {"qualityIssues": [reason]},
        "error": reason,
    }


def parse_fred_series(
    content: bytes,
    *,
    expected_series_id: str,
    units: str,
    url: str | None = None,
    last_modified: str | None = None,
) -> dict:
    del url, last_modified
    text = content.decode("utf-8-sig", errors="strict")
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return _wait_schema("empty CSV")
    normalized_header = [value.strip() for value in header]
    if len(normalized_header) != 2:
        return _wait_schema("expected exactly observation_date and one series column")
    if normalized_header[0].lower() not in {"observation_date", "date"}:
        return _wait_schema("first column is not observation_date")
    if normalized_header[1].upper() != expected_series_id:
        return _wait_schema(
            f"expected series {expected_series_id}, got {normalized_header[1]}"
        )

    values_by_date: dict[str, float] = {}
    missing_count = 0
    for line_number, row in enumerate(reader, start=2):
        if not row or not any(value.strip() for value in row):
            continue
        if len(row) != 2:
            return _wait_schema(f"line {line_number} has {len(row)} columns")
        try:
            observation_date = date.fromisoformat(row[0].strip()).isoformat()
        except ValueError:
            return _wait_schema(f"line {line_number} has invalid observation date")
        raw_value = row[1].strip()
        if raw_value in {"", ".", "NA", "N/A"}:
            missing_count += 1
            continue
        try:
            value = float(raw_value)
        except ValueError:
            return _wait_schema(f"line {line_number} has invalid numeric value")
        if observation_date in values_by_date:
            return _wait_schema(f"duplicate observation date {observation_date}")
        values_by_date[observation_date] = value

    rows = [
        {
            "seriesId": expected_series_id,
            "observationDate": observation_date,
            "value": values_by_date[observation_date],
            "units": units,
        }
        for observation_date in sorted(values_by_date)
    ]
    if not rows:
        return {
            "parser_state": "WAIT_EMPTY_PARSE",
            "data_date": None,
            "record_count": 0,
            "summary": f"FRED {expected_series_id} contained no numeric observations.",
            "output": {"missingObservationCount": missing_count, "rows": []},
        }
    return {
        "parser_state": "PARSED_STRUCTURED",
        "data_date": rows[-1]["observationDate"],
        "record_count": len(rows),
        "summary": f"Parsed {len(rows)} FRED {expected_series_id} observations.",
        "output": {
            "seriesId": expected_series_id,
            "units": units,
            "missingObservationCount": missing_count,
            "rows": rows,
        },
    }


def parse_fred_real_yield(content: bytes, **kwargs) -> dict:
    return parse_fred_series(
        content, expected_series_id="DFII10", units="percent", **kwargs
    )


def parse_fred_broad_dollar(content: bytes, **kwargs) -> dict:
    return parse_fred_series(
        content, expected_series_id="DTWEXBGS", units="index", **kwargs
    )
