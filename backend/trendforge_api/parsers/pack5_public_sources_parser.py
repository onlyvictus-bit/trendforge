"""Pure parsers for the usable public Pack-5 operational/context routes."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from .common import source_result


SYMBOL_RE = re.compile(r"^[A-Z0-9&_.-]{1,32}$")


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _number(value: Any) -> float | None:
    cleaned = _text(value).replace(",", "")
    if not cleaned or cleaned in {"-", "--", "NA", "N/A"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _date(value: Any, *formats: str) -> datetime | None:
    text = _text(value)
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def parse_nse_market_status(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Normalize NSE session states; this is operational context, never a vote."""
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="NSE market status is not valid JSON.",
            output={"rows": [], "scope": "OPERATIONAL_CONTEXT"},
            error=str(exc),
        )
    states = payload.get("marketState") if isinstance(payload, dict) else None
    if not isinstance(states, list):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="NSE market status is missing marketState.",
            output={"rows": [], "scope": "OPERATIONAL_CONTEXT"},
            error="missing marketState list",
        )
    fetched_at = _timestamp(last_modified)
    rows: list[dict[str, Any]] = []
    invalid = duplicate = 0
    seen: set[str] = set()
    dates: list[str] = []
    for raw in states:
        if not isinstance(raw, dict):
            invalid += 1
            continue
        market = _text(raw.get("market"))
        status = _text(raw.get("marketStatus")).upper()
        traded_at = _date(raw.get("tradeDate"), "%d-%b-%Y %H:%M", "%d-%b-%Y")
        if not market or not status or traded_at is None:
            invalid += 1
            continue
        if fetched_at is not None and traded_at.date() > fetched_at.date():
            invalid += 1
            continue
        identity = market.casefold()
        if identity in seen:
            duplicate += 1
            continue
        seen.add(identity)
        dates.append(traded_at.date().isoformat())
        rows.append(
            {
                "symbol": None,
                "market": market,
                "marketStatus": status,
                "tradeDate": traded_at.date().isoformat(),
                "tradeTimestamp": traded_at.isoformat().replace("+00:00", "Z"),
                "index": _text(raw.get("index")) or None,
                "last": _number(raw.get("last")),
                "variation": _number(raw.get("variation")),
                "percentChange": _number(raw.get("percentChange")),
                "statusMessage": _text(raw.get("marketStatusMessage")) or None,
                "sourceUrl": url,
                "sourceTrust": "OFFICIAL",
                "scope": "OPERATIONAL_CONTEXT",
                "scoreAuthority": "ZERO_SCORE_OPERATIONAL",
            }
        )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="NSE market status produced no valid session rows; retain last-good.",
            output={"rows": [], "invalidRowCount": invalid, "scope": "OPERATIONAL_CONTEXT"},
            error="no valid marketState rows",
        )
    rows.sort(key=lambda row: row["market"])
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(dates),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} official NSE market session states.",
        output={
            "rows": rows,
            "records": rows,
            "sourceRowCount": len(states),
            "normalizedRowCount": len(rows),
            "invalidRowCount": invalid,
            "duplicateRowCount": duplicate,
            "parserVersion": "1.0.0",
            "sourceTrust": "OFFICIAL",
            "scope": "OPERATIONAL_CONTEXT",
            "scoreAuthority": "ZERO_SCORE_OPERATIONAL",
        },
    )


def _rupeevest_symbol_map(search_payload: Any) -> dict[str, dict[str, str | None]]:
    rows = search_payload.get("stock_data_search") if isinstance(search_payload, dict) else None
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, str | None]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        fincode = _text(row.get("fincode"))
        parts = [_text(part) for part in _text(row.get("stock_search")).split("|")]
        symbol = parts[-1].upper() if len(parts) >= 3 else _text(row.get("symbol")).upper()
        if not fincode or not SYMBOL_RE.fullmatch(symbol):
            continue
        result[fincode] = {
            "symbol": symbol,
            "companyName": _text(row.get("compname")) or _text(row.get("s_name")) or None,
            "bseScripCode": parts[-2] if len(parts) >= 3 and parts[-2].isdigit() else None,
        }
    return result


def parse_rupeevest_mf_flows(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Normalize RupeeVest's public monthly stock-level MF buy/sell aggregates."""
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="RupeeVest MF flow bundle is not valid JSON.",
            output={"rows": [], "scope": "SUPPORTING_INFORMATIONAL"},
            error=str(exc),
        )
    if not isinstance(payload, dict):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="RupeeVest MF flow bundle is not an object.",
            output={"rows": [], "scope": "SUPPORTING_INFORMATIONAL"},
            error="bundle must be an object",
        )
    symbols = _rupeevest_symbol_map(payload.get("search"))
    if not symbols:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="RupeeVest bundle has no usable stock identity map.",
            output={"rows": [], "scope": "SUPPORTING_INFORMATIONAL"},
            error="missing stock identity map",
        )
    fetched_at = _timestamp(last_modified)
    rows: list[dict[str, Any]] = []
    source_rows = invalid = unmapped = duplicate = 0
    seen: set[tuple[str, str, str]] = set()
    dates: list[str] = []
    sections = (
        ("BUY", payload.get("buys"), "stock_compare_data"),
        ("SELL", payload.get("sells"), "stock_compare_data_1"),
    )
    for direction, section, row_key in sections:
        section_rows = section.get(row_key) if isinstance(section, dict) else None
        if not isinstance(section_rows, list):
            return source_result(
                parser_state="WAIT_SCHEMA_MISMATCH",
                data_date=None,
                record_count=0,
                summary=f"RupeeVest bundle is missing {row_key}.",
                output={"rows": [], "scope": "SUPPORTING_INFORMATIONAL"},
                error=f"missing {row_key}",
            )
        for raw in section_rows:
            source_rows += 1
            if not isinstance(raw, dict):
                invalid += 1
                continue
            fincode = _text(raw.get("fincode"))
            identity = symbols.get(fincode)
            if identity is None:
                unmapped += 1
                continue
            observed = _date(raw.get("day"), "%Y-%m-%d")
            shares = _number(raw.get("no_of_share_change"))
            value = _number(raw.get("price_of_share_change"))
            if observed is None or shares is None or value is None:
                invalid += 1
                continue
            if fetched_at is not None and observed.date() > fetched_at.date():
                invalid += 1
                continue
            key = (direction, fincode, observed.date().isoformat())
            if key in seen:
                duplicate += 1
                continue
            seen.add(key)
            dates.append(observed.date().isoformat())
            signed_shares = abs(shares) if direction == "BUY" else -abs(shares)
            signed_value = abs(value) if direction == "BUY" else -abs(value)
            rows.append(
                {
                    "symbol": identity["symbol"],
                    "fincode": fincode,
                    "bseScripCode": identity["bseScripCode"],
                    "companyName": _text(raw.get("compname")) or identity["companyName"],
                    "sector": _text(raw.get("rv_sect_name")) or None,
                    "marketCapClass": _text(raw.get("classification")) or None,
                    "direction": direction,
                    "netShareChange": int(signed_shares),
                    "approximateValueCr": round(signed_value / 10_000_000, 4),
                    "dataDate": observed.date().isoformat(),
                    "sourceUrl": url,
                    "sourceTrust": "OPEN_SOURCE_UNOFFICIAL",
                    "scope": "SUPPORTING_INFORMATIONAL",
                    "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
                }
            )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="RupeeVest MF flow bundle produced no equity-joinable rows; retain last-good.",
            output={"rows": [], "sourceRowCount": source_rows, "scope": "SUPPORTING_INFORMATIONAL"},
            error="no normalized rows",
        )
    rows.sort(key=lambda row: (row["dataDate"], row["symbol"], row["direction"]), reverse=True)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(dates),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} public RupeeVest monthly MF stock-flow rows.",
        output={
            "rows": rows,
            "records": rows,
            "identityRowCount": len(symbols),
            "sourceRowCount": source_rows,
            "normalizedRowCount": len(rows),
            "invalidRowCount": invalid,
            "unmappedRowCount": unmapped,
            "duplicateRowCount": duplicate,
            "parserVersion": "1.0.0",
            "sourceTrust": "OPEN_SOURCE_UNOFFICIAL",
            "scope": "SUPPORTING_INFORMATIONAL",
            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            "mappingPolicy": "EXPLICIT_PUBLIC_SYMBOL_MAP_ONLY",
        },
    )
