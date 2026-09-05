from __future__ import annotations

import re
from typing import Any

from .common import (
    decode_bytes,
    extract_data_date,
    find_value,
    parse_date_value,
    parse_float,
    parse_int,
    rows_from_content,
    source_result,
)
from ..corporate_actions import classify_action


def _ratio(value: Any) -> tuple[float | None, float | None]:
    if value in {None, ""}:
        return None, None
    match = re.search(r"(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)", str(value))
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))


def _revision(value: Any) -> str:
    normalized = str(value or "UNKNOWN").upper()
    if "CANCEL" in normalized or "WITHDRAW" in normalized:
        return "CANCELLED"
    if "REVIS" in normalized or "MODIF" in normalized:
        return "REVISED"
    if "ORIGINAL" in normalized or "NEW" in normalized:
        return "ORIGINAL"
    return "UNKNOWN"


def _cash_from_action(value: str) -> float | None:
    matches = re.findall(r"\b(?:RS|RE)\.?\s*-?\s*(\d+(?:\.\d+)?)", value, re.IGNORECASE)
    amounts = [float(item) for item in matches]
    return round(sum(amounts), 6) if amounts else None


def _optional_bool(value: Any) -> bool | None:
    normalized = str(value or "").strip().upper()
    if normalized in {"TRUE", "YES", "Y", "1"}:
        return True
    if normalized in {"FALSE", "NO", "N", "0"}:
        return False
    return None


CORPORATE_ACTIONS_SCHEMA_ID = "nse_corporate_filings_actions_v1"


def parse_corporate_events(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    observed_date = parse_date_value(last_modified)
    if observed_date and (data_date is None or data_date > observed_date):
        data_date = observed_date
        date_source = "retrieval_or_last_modified_date"
    rows, source_name = rows_from_content(content)
    events: list[dict[str, Any]] = []
    for row in rows:
        symbol = (
            find_value(row, ("symbol", "scrip_code", "scrip", "security_code")) or ""
        )
        company = (
            find_value(row, ("company_name", "security_name", "company", "comp")) or ""
        )
        action = (
            find_value(
                row,
                (
                    "action_type",
                    "purpose",
                    "subject",
                    "sub_type",
                    "offer_type",
                    "type",
                ),
            )
            or ""
        )
        if not (symbol or company) or not action:
            continue
        action_class = classify_action(action)
        numerator, denominator = _ratio(
            find_value(
                row,
                (
                    "action_ratio",
                    "ratio",
                    "split_ratio",
                    "bonus_ratio",
                    "ratio_details",
                ),
            )
            or action
        )
        explicit_cash = parse_float(
            find_value(
                row,
                ("dividend_amount", "cash_amount", "amount_per_share"),
            )
        )
        events.append(
            {
                "symbol": symbol.strip().upper(),
                "company": company.strip(),
                "actionType": action.strip().upper(),
                "actionClass": action_class,
                "announcementDate": parse_date_value(
                    find_value(
                        row,
                        (
                            "announcement_date",
                            "broadcast_date",
                            "ca_broadcast_date",
                            "date",
                        ),
                    )
                ),
                "exDate": parse_date_value(find_value(row, ("ex_date", "exdate"))),
                "recordDate": parse_date_value(
                    find_value(row, ("record_date", "recorddate", "rec_date"))
                ),
                "startDate": parse_date_value(
                    find_value(row, ("start_date", "open_date"))
                ),
                "endDate": parse_date_value(
                    find_value(row, ("end_date", "close_date"))
                ),
                "offerPrice": parse_float(
                    find_value(
                        row, ("offer_price", "buyback_price", "floor_price", "price")
                    )
                ),
                "quantity": parse_int(
                    find_value(row, ("quantity", "shares", "buyback_qty"))
                ),
                "ratioNumerator": numerator,
                "ratioDenominator": denominator,
                "cashAmount": (
                    explicit_cash or _cash_from_action(action)
                    if action_class == "DIVIDEND"
                    else None
                ),
                "priceAdjustmentFactor": parse_float(
                    find_value(
                        row,
                        (
                            "price_adjustment_factor",
                            "adjustment_factor",
                            "exchange_adjustment_factor",
                        ),
                    )
                ),
                "predecessorSymbol": (
                    find_value(
                        row,
                        ("predecessor_symbol", "old_symbol", "transferor_symbol"),
                    )
                    or ""
                )
                .strip()
                .upper()
                or None,
                "successorSymbol": (
                    find_value(
                        row,
                        ("successor_symbol", "new_symbol", "transferee_symbol"),
                    )
                    or ""
                )
                .strip()
                .upper()
                or None,
                "continuityConfirmed": _optional_bool(
                    find_value(
                        row,
                        (
                            "continuity_confirmed",
                            "same_instrument_continuity",
                            "symbol_continuity_confirmed",
                        ),
                    )
                ),
                "revisionStatus": _revision(
                    find_value(row, ("status", "revision_status", "filing_status"))
                ),
                "scope": "CORPORATE_EVENT_CONTEXT",
            }
        )
    if not events:
        if url and "corporates-daily-buyback" in url:
            return source_result(
                parser_state="PARSED_STRUCTURED",
                data_date=data_date,
                record_count=0,
                summary="Official NSE daily-buyback response is valid and empty.",
                output={
                    "scope": "CORPORATE_EVENT_CONTEXT",
                    "dateSource": date_source,
                    "validEmpty": True,
                    "rows": [],
                },
            )
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="No structured corporate-event rows found.",
            output={"scope": "CORPORATE_EVENT_CONTEXT", "dateSource": date_source},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(events),
        summary=f"Corporate events parsed from {source_name}.",
        output={
            "scope": "CORPORATE_EVENT_CONTEXT",
            "dateSource": date_source,
            "rows": events,
        },
    )
