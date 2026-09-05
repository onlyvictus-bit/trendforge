from __future__ import annotations

import re
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

_SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9&.\-]{1,19}$")
_BAN_HEADER_PATTERN = re.compile(
    r"Securities\s+in\s+Ban\s+For\s+Trade\s+Date\s+[^:\r\n]+:",
    re.IGNORECASE,
)


def classify_mwpl(mwpl_percent: float, is_banned: bool = False) -> str:
    if is_banned or mwpl_percent >= 95:
        return "BANNED"
    if mwpl_percent >= 90:
        return "ORANGE"
    if mwpl_percent >= 80:
        return "YELLOW"
    return "SAFE"


def _contract_mismatch(
    *,
    data_date: str | None,
    date_source: str | None,
    expected_contract: str,
    summary: str,
) -> dict[str, Any]:
    return source_result(
        parser_state="WAIT_SCHEMA_MISMATCH",
        data_date=data_date,
        record_count=0,
        summary=summary,
        output={
            "scope": "STOCK_DERIVATIVES_SAFETY",
            "dateSource": date_source,
            "expectedContract": expected_contract,
        },
    )


def _extract_banned_symbols(text: str, header: re.Match[str]) -> list[str]:
    banned: list[str] = []
    for line in text[header.end() :].splitlines():
        columns = [part.strip().upper() for part in line.split(",")]
        candidate = columns[1] if len(columns) >= 2 and columns[0].isdigit() else ""
        if _SYMBOL_PATTERN.fullmatch(candidate):
            banned.append(candidate)
    return sorted(set(banned))


BAN_SCHEMA_ID = "nse_fo_secban_csv_v1"
MWPL_SCHEMA_ID = "nse_ncl_combineoi_v1"


def parse_nse_fno_ban(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse only the official fo_secban artifact.

    The ban artifact is a hard-veto membership list. It never provides or
    implies symbol-level MWPL utilization percentages.
    """

    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    ban_header = _BAN_HEADER_PATTERN.search(text)
    if ban_header is None:
        return _contract_mismatch(
            data_date=data_date,
            date_source=date_source,
            expected_contract="nse_fno_ban",
            summary="Artifact is not the official NSE F&O ban-list schema.",
        )

    banned = _extract_banned_symbols(text, ban_header)
    rows = [
        {
            "symbol": symbol,
            "mwplPercent": None,
            "totalOi": None,
            "mwpl": None,
            "banStatus": "BANNED",
            "isBanned": True,
            "oiReliable": False,
            "scope": "STOCK_DERIVATIVES_SAFETY",
            "evidenceCoverage": "FNO_BAN_ONLY",
        }
        for symbol in banned
    ]
    valid_empty = not rows
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=(
            "Official NSE F&O ban symbols parsed."
            if rows
            else "Official NSE F&O ban file is valid and contains no banned symbols."
        ),
        output={
            "scope": "STOCK_DERIVATIVES_SAFETY",
            "canonicalSourceKey": "nse_fno_ban",
            "evidenceCoverage": "FNO_BAN_ONLY",
            "dateSource": date_source,
            "symbols": banned,
            "rows": rows,
            "validEmpty": valid_empty,
            "warning": (
                "Ban evidence is a hard veto only; it cannot provide or confirm "
                "MWPL utilization percentages."
            ),
        },
    )


def parse_nse_mwpl_percentages(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse a separately verified symbol-level MWPL percentage artifact."""

    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    rows, source_name = rows_from_content(content)
    parsed_rows: list[dict[str, Any]] = []

    for row in rows:
        symbol = find_value(
            row,
            (
                "nse_symbol",
                "symbol",
                "scrip",
                "underlying",
                "security",
            ),
        )
        percent_raw = find_value(
            row, ("percentage", "mwpl_percent", "mwpl_pct", "percent")
        )
        futeq_raw = find_value(
            row,
            (
                "future_equivalent_open_interest",
                "futeq_oi",
                "ncl_futeq_oi",
            ),
        )
        total_oi_raw = find_value(
            row,
            (
                "open_interest",
                "total_oi",
                "ncl_open_interest",
                "market_wide_open_interest",
            ),
        )
        mwpl_raw = find_value(row, ("mwpl", "market_wide_position_limit"))
        limit_raw = (
            find_value(
                row,
                (
                    "limit_for_next_day",
                    "limit_next_day",
                    "next_day_limit",
                ),
            )
            or ""
        )
        clean_symbol = symbol.strip().upper() if symbol else ""
        if not _SYMBOL_PATTERN.fullmatch(clean_symbol):
            continue
        mwpl_percent = parse_float(percent_raw)
        futeq_oi = parse_int(futeq_raw)
        market_oi = parse_int(total_oi_raw)
        utilization_oi = futeq_oi if futeq_oi > 0 else market_oi
        mwpl_value = parse_int(mwpl_raw)
        if mwpl_percent <= 0 and utilization_oi > 0 and mwpl_value > 0:
            mwpl_percent = round((utilization_oi / mwpl_value) * 100, 3)
        if mwpl_percent <= 0:
            continue
        no_fresh = "no fresh" in limit_raw.lower()
        status = classify_mwpl(mwpl_percent, is_banned=no_fresh)
        parsed_rows.append(
            {
                "symbol": clean_symbol,
                "mwplPercent": mwpl_percent,
                "totalOi": utilization_oi,
                "mwpl": mwpl_value,
                "banStatus": status,
                "isBanned": status == "BANNED" or no_fresh,
                "oiReliable": status in {"SAFE", "YELLOW"} and not no_fresh,
                "limitForNextDay": limit_raw.strip() or None,
                "scope": "STOCK_DERIVATIVES_SAFETY",
                "evidenceCoverage": "FULL_MWPL_PERCENTAGES",
                "utilizationBasis": "FUTEQ_OI" if futeq_oi > 0 else "MARKET_WIDE_OI",
            }
        )

    if not parsed_rows:
        return _contract_mismatch(
            data_date=data_date,
            date_source=date_source,
            expected_contract="nse_mwpl_percentages",
            summary=(
                "Artifact does not contain schema-valid symbol-level MWPL "
                "percentages from a separately verified contract."
            ),
        )

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(parsed_rows),
        summary=f"NSE MWPL percentage rows parsed from {source_name}.",
        output={
            "scope": "STOCK_DERIVATIVES_SAFETY",
            "canonicalSourceKey": "nse_mwpl_percentages",
            "evidenceCoverage": "FULL_MWPL_PERCENTAGES",
            "dateSource": date_source,
            "thresholds": {"yellow": 80, "orange": 90, "ban": 95},
            "rows": parsed_rows,
        },
    )


def parse_nse_mwpl(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Backward-compatible parser dispatcher for stored legacy snapshots.

    New runtime wiring must use nse_fno_ban or nse_mwpl_percentages directly.
    This alias is never registered as an independent voting source.
    """

    text = decode_bytes(content)
    if _BAN_HEADER_PATTERN.search(text):
        result = parse_nse_fno_ban(content, url=url, last_modified=last_modified)
        canonical_key = "nse_fno_ban"
    else:
        result = parse_nse_mwpl_percentages(
            content, url=url, last_modified=last_modified
        )
        canonical_key = "nse_mwpl_percentages"
    result.setdefault("output", {})
    result["output"].update(
        {
            "compatibilityAlias": "nse_mwpl_ban",
            "canonicalSourceKey": canonical_key,
            "nonVotingAlias": True,
        }
    )
    return result
