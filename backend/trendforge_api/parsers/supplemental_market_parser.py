from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

from .common import (
    parse_date_value,
    parse_float,
    parse_int,
    rows_from_content,
    source_result,
)


def _empty(summary: str, scope: str) -> dict[str, Any]:
    return source_result(
        parser_state="WAIT_EMPTY_PARSE",
        data_date=None,
        record_count=0,
        summary=summary,
        output={
            "endpointConnected": True,
            "noDataNow": True,
            "scope": scope,
            "rows": [],
        },
    )


def _schema(summary: str, scope: str) -> dict[str, Any]:
    return source_result(
        parser_state="WAIT_SCHEMA_MISMATCH",
        data_date=None,
        record_count=0,
        summary=summary,
        output={
            "endpointConnected": True,
            "noDataNow": True,
            "scope": scope,
            "rows": [],
        },
        error=summary,
    )


def _option_chain_max_pain(rows: list[dict[str, Any]]) -> float | None:
    """Strike that minimizes total intrinsic payout for CE+PE open interest."""
    strikes = sorted(
        {
            float(row["strike"])
            for row in rows
            if row.get("strike") is not None and float(row["strike"]) > 0
        }
    )
    if not strikes:
        return None
    best_strike: float | None = None
    best_pain = float("inf")
    for candidate in strikes:
        pain = 0.0
        for row in rows:
            strike = float(row["strike"])
            oi = float(row.get("openInterest") or 0)
            if oi <= 0:
                continue
            if row.get("optionType") == "CE" and candidate > strike:
                pain += (candidate - strike) * oi
            elif row.get("optionType") == "PE" and candidate < strike:
                pain += (strike - candidate) * oi
        if pain < best_pain:
            best_pain = pain
            best_strike = candidate
    return best_strike


def _option_chain_walls(
    rows: list[dict[str, Any]], option_type: str, *, top_n: int = 3
) -> list[dict[str, Any]]:
    filtered = [
        row
        for row in rows
        if row.get("optionType") == option_type and (row.get("openInterest") or 0) > 0
    ]
    filtered.sort(key=lambda row: float(row.get("openInterest") or 0), reverse=True)
    return [
        {
            "strike": row.get("strike"),
            "expiry": row.get("expiry"),
            "openInterest": row.get("openInterest"),
            "oiChange": row.get("oiChange"),
        }
        for row in filtered[:top_n]
    ]


def _option_chain_request_identity(url: str | None) -> tuple[str, str]:
    query = parse_qs(urlparse(str(url or "")).query)
    return (
        str((query.get("symbol") or [""])[0]).strip().upper(),
        str((query.get("expiry") or [""])[0]).strip(),
    )


def parse_nse_option_chain(
    content: bytes, *, url: str | None = None, **_kwargs
) -> dict[str, Any]:
    scope = "DERIVATIVES_CONFIRMATION_ONLY"
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _schema("NSE option-chain response is not valid JSON.", scope)
    if not isinstance(payload, dict):
        return _schema("NSE option-chain response is not an object.", scope)

    # Bare {} after a successful HTTP 200 is a soft/session empty — not a normal
    # populated market snapshot and not a typed empty records payload.
    if not payload:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary=(
                "NSE option-chain returned empty object {}; treat as soft-empty/"
                "session-limited response, not populated CE/PE chain."
            ),
            output={
                "endpointConnected": True,
                "noDataNow": True,
                "softEmptyObject": True,
                "scope": scope,
                "rows": [],
                "metrics": {},
            },
        )

    records = payload.get("records")
    if not isinstance(records, dict) or not records.get("data"):
        return _empty(
            "NSE option-chain endpoint is connected but has no data now.", scope
        )
    timestamp = str(records.get("timestamp") or "")
    data_date = parse_date_value(timestamp)
    underlying = parse_float(records.get("underlyingValue"))
    requested_symbol, requested_expiry = _option_chain_request_identity(url)
    record_expiries = [
        str(value).strip()
        for value in (records.get("expiryDates") or [])
        if str(value).strip()
    ]
    fallback_expiry = requested_expiry or (
        record_expiries[0] if len(record_expiries) == 1 else ""
    )
    rows: list[dict[str, Any]] = []
    source_row_count = 0
    invalid_row_count = 0
    for strike_row in records["data"]:
        if not isinstance(strike_row, dict):
            return _schema("NSE option-chain contains a non-object strike row.", scope)
        for option_type in ("CE", "PE"):
            option = strike_row.get(option_type)
            if not isinstance(option, dict):
                continue
            source_row_count += 1
            symbol = str(
                option.get("underlying")
                or strike_row.get("underlying")
                or records.get("underlying")
                or requested_symbol
                or ""
            ).strip().upper()
            expiry = str(
                strike_row.get("expiryDate")
                or option.get("expiryDate")
                or fallback_expiry
                or ""
            ).strip()
            strike = parse_float(strike_row.get("strikePrice"))
            if not symbol or not expiry or strike is None:
                invalid_row_count += 1
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "expiry": expiry,
                    "strike": strike,
                    "optionType": option_type,
                    "openInterest": parse_int(option.get("openInterest")),
                    "oiChange": parse_int(option.get("changeinOpenInterest")),
                    "volume": parse_int(option.get("totalTradedVolume")),
                    "iv": parse_float(option.get("impliedVolatility")),
                    "lastPrice": parse_float(option.get("lastPrice")),
                    "underlyingValue": underlying,
                    "timestamp": timestamp,
                }
            )
    if not rows:
        return _schema(
            "NSE option-chain returned contracts without canonical symbol/expiry/strike identity.",
            scope,
        )

    call_oi = sum(
        float(row.get("openInterest") or 0)
        for row in rows
        if row.get("optionType") == "CE"
    )
    put_oi = sum(
        float(row.get("openInterest") or 0)
        for row in rows
        if row.get("optionType") == "PE"
    )
    pcr = round(put_oi / call_oi, 6) if call_oi > 0 else None
    max_pain = _option_chain_max_pain(rows)
    metrics = {
        "underlyingValue": underlying,
        "callOiTotal": call_oi,
        "putOiTotal": put_oi,
        "pcrOi": pcr,
        "maxPainStrike": max_pain,
        "callOiWalls": _option_chain_walls(rows, "CE"),
        "putOiWalls": _option_chain_walls(rows, "PE"),
        "expiryDates": sorted({str(row.get("expiry") or "") for row in rows if row.get("expiry")}),
    }
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=(
            f"Parsed {len(rows)} NSE option-chain contract rows "
            f"(PCR={pcr}, maxPain={max_pain})."
        ),
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": scope,
            "parserVersion": "1.1.0",
            "sourceTrust": "OFFICIAL_PRIMARY",
            "sourceRowCount": source_row_count,
            "normalizedRowCount": len(rows),
            "invalidRowCount": invalid_row_count,
            "rows": rows,
            "metrics": metrics,
        },
    )


def _pit_direction(value: Any) -> str:
    text = str(value or "").strip().casefold()
    if any(token in text for token in ("sell", "sale", "disposal", "dispose")):
        return "SELL"
    if any(token in text for token in ("buy", "purchase", "acquisition", "acquire")):
        return "BUY"
    return "UNKNOWN"


def _pit_as_of_date(last_modified: str | None) -> date | None:
    text = str(last_modified or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_nse_pit_current(
    content: bytes, *, last_modified: str | None = None, **_kwargs
) -> dict[str, Any]:
    scope = "SMART_MONEY_DISCLOSURE"
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _schema("NSE PIT response is not valid JSON.", scope)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return _schema("NSE PIT response lacks a data list.", scope)
    if not payload["data"]:
        return _empty(
            "NSE PIT endpoint is connected but has no disclosures now.", scope
        )
    rows: list[dict[str, Any]] = []
    invalid = duplicate = 0
    seen: set[str] = set()
    as_of_date = _pit_as_of_date(last_modified)
    for item in payload["data"]:
        if not isinstance(item, dict):
            invalid += 1
            continue
        event_date = parse_date_value(item.get("date") or item.get("acqfromDt"))
        symbol = str(item.get("symbol") or "").strip().upper()
        if not symbol or event_date is None:
            invalid += 1
            continue
        if as_of_date is not None and event_date > as_of_date.isoformat():
            invalid += 1
            continue
        direction = _pit_direction(item.get("tdpTransactionType"))
        quantity = parse_int(item.get("secAcq"))
        identity = str(item.get("did") or item.get("pid") or "").strip() or "|".join(
            (
                symbol,
                str(item.get("acqName") or "").strip().casefold(),
                event_date,
                direction,
                str(quantity),
            )
        )
        if identity in seen:
            duplicate += 1
            continue
        seen.add(identity)
        transaction_date = parse_date_value(item.get("acqfromDt"))
        transaction_mode = str(item.get("acqMode") or "").strip()
        rows.append(
            {
                "disclosureId": str(item.get("did") or item.get("pid") or "").strip() or None,
                "symbol": symbol,
                "company": str(item.get("company") or ""),
                "entity": str(item.get("acqName") or ""),
                "transactionType": transaction_mode,
                "transactionMode": transaction_mode,
                "transactionDirection": direction,
                "securityType": str(item.get("secType") or ""),
                "quantity": quantity,
                "value": parse_float(item.get("secVal")),
                "postShares": parse_int(item.get("afterAcqSharesNo")),
                "postHoldingPercent": parse_float(item.get("afterAcqSharesPer")),
                "eventDate": event_date,
                "filingDate": event_date,
                "transactionDate": transaction_date,
                "xbrlLink": str(item.get("xbrl") or item.get("xbrlLink") or ""),
                "sourceTrust": "OFFICIAL",
                "scope": scope,
                "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            }
        )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="NSE PIT produced no valid dated disclosures; retain last-good.",
            output={
                "endpointConnected": True,
                "noDataNow": True,
                "scope": scope,
                "rows": [],
                "sourceRowCount": len(payload["data"]),
                "invalidRowCount": invalid,
                "duplicateRowCount": duplicate,
                "parserVersion": "1.1.0",
            },
        )
    rows.sort(key=lambda row: (row["eventDate"], row["symbol"], row["disclosureId"] or ""), reverse=True)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(row["eventDate"] for row in rows),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} current NSE PIT disclosures.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": scope,
            "rows": rows,
            "records": rows,
            "sourceRowCount": len(payload["data"]),
            "normalizedRowCount": len(rows),
            "invalidRowCount": invalid,
            "duplicateRowCount": duplicate,
            "parserVersion": "1.1.0",
            "sourceTrust": "OFFICIAL",
            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
        },
    )


def _bse_date(url: str | None) -> str | None:
    match = re.search(r"EQ(\d{2})(\d{2})(\d{2})", url or "", re.IGNORECASE)
    if not match:
        return None
    return datetime.strptime("".join(match.groups()), "%d%m%y").date().isoformat()


def parse_bse_bhavcopy(
    content: bytes, *, url: str | None = None, **_kwargs
) -> dict[str, Any]:
    scope = "EOD_PRICE_VOLUME_BACKUP"
    if content.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        return _schema("BSE bhavcopy endpoint returned HTML content.", scope)
    raw_rows, _ = rows_from_content(content)
    rows: list[dict[str, Any]] = []
    row_dates: list[str] = []
    for item in raw_rows:
        code = str(
            item.get("fin_instrm_id")
            or item.get("fininstrmid")
            or item.get("sc_code")
            or item.get("code")
            or ""
        ).strip()
        name = str(
            item.get("tckr_symb")
            or item.get("tckrsymb")
            or item.get("sc_name")
            or item.get("name")
            or ""
        ).strip()
        if not code or not name:
            continue
        trade_date = parse_date_value(
            item.get("trad_dt") or item.get("traddt") or item.get("date")
        )
        if trade_date:
            row_dates.append(trade_date)
        rows.append(
            {
                "scripCode": code,
                "name": name,
                "tradeDate": trade_date,
                "open": parse_float(
                    item.get("opn_pric") or item.get("opnpric") or item.get("open")
                ),
                "high": parse_float(
                    item.get("hgh_pric") or item.get("hghpric") or item.get("high")
                ),
                "low": parse_float(
                    item.get("lw_pric") or item.get("lwpric") or item.get("low")
                ),
                "close": parse_float(
                    item.get("cls_pric") or item.get("clspric") or item.get("close")
                ),
                "volume": parse_int(
                    item.get("ttl_tradg_vol")
                    or item.get("ttltradgvol")
                    or item.get("no_of_shrs")
                    or item.get("trdqty")
                ),
                "turnover": parse_float(
                    item.get("ttl_trf_val")
                    or item.get("ttltrfval")
                    or item.get("net_turnov")
                    or item.get("trdval")
                ),
            }
        )
    if not rows:
        return _empty("BSE bhavcopy ZIP contained no equity rows.", scope)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(row_dates) if row_dates else _bse_date(url),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} BSE bhavcopy rows.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": scope,
            "rows": rows,
        },
    )


def parse_nse_block_deal_live(content: bytes, **_kwargs) -> dict[str, Any]:
    scope = "MARKET_ACTIVITY_CONTEXT_ONLY"
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _schema("NSE live block-deal response is not valid JSON.", scope)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return _schema("NSE live block-deal response lacks a data list.", scope)
    if not payload["data"]:
        return _empty("NSE live block-deal endpoint has no rows now.", scope)
    timestamp = str(payload.get("timestamp") or "")
    rows = [
        {
            "symbol": str(item.get("symbol") or "").upper(),
            "session": str(item.get("session") or ""),
            "lastPrice": parse_float(item.get("lastPrice")),
            "quantity": parse_int(item.get("totalTradedQuantity")),
            "value": parse_float(item.get("totalTradedValue")),
            "orderType": str(item.get("orderType") or ""),
            "timestamp": timestamp,
        }
        for item in payload["data"]
        if isinstance(item, dict) and item.get("symbol")
    ]
    if not rows:
        return _empty("NSE live block-deal endpoint has no usable rows now.", scope)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=parse_date_value(timestamp),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSE live block-deal market rows.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": scope,
            "canProveNamedSponsor": False,
            "rows": rows,
        },
    )
