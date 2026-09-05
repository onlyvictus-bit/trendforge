from __future__ import annotations

import html
import json
import re
from datetime import datetime
from typing import Any

from .common import (
    decode_bytes,
    extract_data_date,
    find_value,
    parse_float,
    parse_int,
    normalize_name,
    rows_from_content,
    source_result,
)


def _embedded_bhavcopy_rows(text: str) -> tuple[list[dict[str, str]], str, bool]:
    match = re.search(
        r'<div\s+[^>]*id=["\']bhavcopy-data["\'][^>]*>(.*?)</div>',
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return [], "html", False
    try:
        payload = json.loads(html.unescape(match.group(1)).strip())
    except json.JSONDecodeError:
        return [], "mcx_embedded_json", True
    if not isinstance(payload, list):
        return [], "mcx_embedded_json", True
    rows = [
        {
            normalize_name(key): "" if value is None else str(value).strip()
            for key, value in item.items()
        }
        for item in payload
        if isinstance(item, dict)
    ]
    return rows, "mcx_embedded_json", False


def _mcx_data_date(rows: list[dict[str, str]]) -> str | None:
    for row in rows:
        value = find_value(row, ("date", "trade_date"))
        if not value:
            continue
        try:
            return datetime.strptime(value, "%m/%d/%Y").date().isoformat()
        except ValueError:
            continue
    return None


def parse_mcx_bhavcopy(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    rows, source_name, embedded_schema_error = _embedded_bhavcopy_rows(text)
    if embedded_schema_error:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="MCX embedded bhavcopy JSON is malformed.",
            output={"scope": "MCX_FUTURES_EOD_CONFIRMATION"},
        )
    if not rows:
        rows, source_name = rows_from_content(content)
    data_date = _mcx_data_date(rows)
    date_source = "embedded_trade_date" if data_date else "missing"
    if not data_date:
        data_date, date_source = extract_data_date(text, url, last_modified)
    candles: list[dict[str, Any]] = []
    excluded_option_rows = 0

    for row in rows:
        instrument = (
            (find_value(row, ("instrument_name", "instrument")) or "").strip().upper()
        )
        if instrument and instrument != "FUTCOM":
            excluded_option_rows += 1
            continue
        symbol = find_value(row, ("symbol", "commodity", "contract", "instrument"))
        expiry = find_value(row, ("expiry", "expiry_date", "exp_date")) or ""
        close_price = parse_float(
            find_value(row, ("close", "close_price", "settle", "settlement", "last"))
        )
        volume = parse_int(find_value(row, ("volume", "traded_qty", "qty")))
        open_interest = parse_int(find_value(row, ("open_interest", "oi")))
        oi_change = parse_int(
            find_value(row, ("change_in_oi", "oi_change", "chg_in_oi"))
        )
        if not symbol or (close_price <= 0 and volume <= 0 and open_interest <= 0):
            continue
        candles.append(
            {
                "symbol": symbol.strip().upper(),
                "expiry": expiry.strip(),
                "instrument": instrument or "FUTCOM",
                "open": parse_float(find_value(row, ("open",))),
                "high": parse_float(find_value(row, ("high",))),
                "low": parse_float(find_value(row, ("low",))),
                "close": close_price,
                "previousClose": parse_float(
                    find_value(row, ("previous_close", "prev_close"))
                ),
                "volume": volume,
                "value": parse_float(find_value(row, ("value", "turnover"))),
                "openInterest": open_interest,
                "oiChange": oi_change,
                "scope": "MCX_FUTURES_EOD_CONFIRMATION",
            }
        )

    if not candles:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="No usable MCX bhavcopy rows found in latest raw snapshot.",
            output={
                "scope": "MCX_FUTURES_EOD_CONFIRMATION",
                "dateSource": date_source,
                "excludedOptionRows": excluded_option_rows,
            },
        )

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(candles),
        summary=f"MCX bhavcopy parsed from {source_name}; EOD confirmation only.",
        output={
            "scope": "MCX_FUTURES_EOD_CONFIRMATION",
            "dateSource": date_source,
            "excludedOptionRows": excluded_option_rows,
            "warning": "MCX bhavcopy is EOD; live intraday MCX still needs a broker/licensed feed.",
            "rows": candles,
        },
    )
