from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .common import (
    decode_bytes,
    extract_data_date,
    find_value,
    parse_float,
    parse_int,
    rows_from_content,
    source_result,
)


def parse_nse_slb(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    if data_date is None and url:
        match = re.search(r"slb_openpos_(\d{8})\.csv", url, re.I)
        if match:
            data_date = datetime.strptime(match.group(1), "%d%m%Y").date().isoformat()
            date_source = "artifact_filename"
    rows, source_name = rows_from_content(content)
    records_by_symbol: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = find_value(row, ("symbol", "security", "scrip"))
        open_positions = parse_int(
            find_value(
                row,
                (
                    "open_positions",
                    "open_position",
                    "open_interest",
                    "oi",
                    "outstanding_quantity_at_the_end_of_the_day",
                ),
            )
        )
        # Open-position reports contain an outstanding quantity but no traded
        # volume. Only map a column that explicitly represents volume.
        volume = parse_int(find_value(row, ("volume", "traded_quantity")))
        borrow_rate = parse_float(
            find_value(
                row,
                (
                    "annualised_yield",
                    "annualized_yield",
                    "borrow_rate",
                    "yield",
                    "rate",
                ),
            )
        )
        turnover = parse_float(
            find_value(row, ("turnover", "transaction_value", "value"))
        )
        if not symbol or (open_positions <= 0 and volume <= 0 and turnover <= 0):
            continue
        normalized_symbol = symbol.strip().upper()
        record = records_by_symbol.setdefault(
            normalized_symbol,
            {
                "symbol": normalized_symbol,
                "openPositions": 0,
                "volume": 0,
                "borrowRate": 0.0,
                "turnover": 0.0,
                "series": set(),
            },
        )
        record["openPositions"] += open_positions
        record["volume"] += volume
        record["borrowRate"] = max(record["borrowRate"], borrow_rate)
        record["turnover"] += turnover
        series = find_value(row, ("series", "settlement_series"))
        if series:
            record["series"].add(series.strip().upper())
    records = [
        {
            "symbol": item["symbol"],
            "openPositions": item["openPositions"],
            "volume": item["volume"],
            "borrowRate": item["borrowRate"],
            "turnover": item["turnover"],
            "seriesCount": len(item["series"]),
            "pressure": "HIGH_BORROW_PRESSURE"
            if item["borrowRate"] >= 10
            else "NORMAL_OR_UNKNOWN",
            "scope": "BORROW_PRESSURE_PROXY_ONLY",
        }
        for item in records_by_symbol.values()
    ]
    if not records:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="No usable NSE SLB rows found.",
            output={"scope": "BORROW_PRESSURE_PROXY_ONLY", "dateSource": date_source},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(records),
        summary=f"NSE SLB rows parsed from {source_name}; borrow-pressure proxy only.",
        output={
            "scope": "BORROW_PRESSURE_PROXY_ONLY",
            "dateSource": date_source,
            "rows": records,
            "warning": "SLB is a borrow-pressure proxy, not exact total short interest.",
        },
    )
