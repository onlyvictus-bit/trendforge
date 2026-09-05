from __future__ import annotations

import csv

from .common import decode_bytes, parse_date_value, parse_float, source_result


EXPECTED_HEADER = [
    "Scheme Code",
    "ISIN Div Payout/ ISIN Growth",
    "ISIN Div Reinvestment",
    "Scheme Name",
    "Net Asset Value",
    "Date",
]


def parse_amfi_nav(content: bytes, **_kwargs) -> dict:
    lines = decode_bytes(content).splitlines()
    if not lines:
        return _schema_error("empty NAV file")
    header = next(csv.reader([lines[0]], delimiter=";"), [])
    if [item.strip() for item in header] != EXPECTED_HEADER:
        return _schema_error("unexpected AMFI NAV header")

    category = ""
    fund_house = ""
    rows: list[dict] = []
    for line_number, line in enumerate(lines[1:], start=2):
        stripped = line.strip()
        if not stripped:
            continue
        if ";" not in stripped:
            if "Schemes(" in stripped:
                category = stripped
                fund_house = ""
            else:
                fund_house = stripped
            continue
        values = next(csv.reader([stripped], delimiter=";"), [])
        if len(values) != 6:
            return _schema_error(f"line {line_number} has {len(values)} fields")
        scheme_code, isin_growth, isin_reinvestment, name, nav_raw, date_raw = (
            value.strip() for value in values
        )
        nav_date = parse_date_value(date_raw)
        nav = parse_float(nav_raw, default=-1)
        if not scheme_code.isdigit() or not name or nav < 0 or nav_date is None:
            return _schema_error(f"line {line_number} contains invalid NAV data")
        rows.append(
            {
                "schemeCode": scheme_code,
                "isinGrowth": "" if isin_growth == "-" else isin_growth,
                "isinReinvestment": (
                    "" if isin_reinvestment == "-" else isin_reinvestment
                ),
                "schemeName": name,
                "fundHouse": fund_house,
                "category": category,
                "nav": nav,
                "navDate": nav_date,
                "scope": "FUND_PRICING_REFERENCE_ONLY",
            }
        )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="AMFI NAV file contained no scheme observations.",
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(row["navDate"] for row in rows),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} official AMFI NAV observations.",
        output={
            "scope": "FUND_PRICING_REFERENCE_ONLY",
            "canProvePortfolioFlow": False,
            "warning": "NAV movement does not prove mutual-fund stock buying or selling.",
            "rows": rows,
        },
    )


def _schema_error(reason: str) -> dict:
    return source_result(
        parser_state="WAIT_SCHEMA_MISMATCH",
        data_date=None,
        record_count=0,
        summary=f"AMFI NAV schema validation failed: {reason}.",
        output={"qualityIssues": [reason]},
        error=reason,
    )
