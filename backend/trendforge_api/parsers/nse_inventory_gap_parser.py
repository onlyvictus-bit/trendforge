from __future__ import annotations

"""Pure parsers for the seven inventory gap feeds.

Fetching and raw archival remain owned by source_monitor/source_resolver.  Every
parser returns the normal TrendForge source_result envelope and fails closed on
empty or malformed payloads.
"""

import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .common import parse_date_value, parse_float, parse_int, source_result


T2T_SERIES = {"BE", "BT", "IT", "ST", "BZ", "SZ"}
DERIVATIVE_EXCHANGES = {"NFO", "BFO", "MCX"}
DERIVATIVE_TYPES = {"FUT", "CE", "PE"}


def _decode(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("latin-1", errors="replace")


def _csv_rows(content: bytes) -> list[dict[str, str]]:
    return [
        {
            str(key or "").strip(): (value.strip() if isinstance(value, str) else value)
            for key, value in row.items()
            if key is not None
        }
        for row in csv.DictReader(io.StringIO(_decode(content)))
    ]


def _zip_csv(content: bytes, prefixes: tuple[str, ...]) -> tuple[list[dict[str, str]], str]:
    if not zipfile.is_zipfile(io.BytesIO(content)):
        return [], ""
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
        for prefix in prefixes:
            for name in names:
                leaf = name.rsplit("/", 1)[-1].lower()
                if leaf.startswith(prefix.lower()) and leaf.endswith((".csv", ".txt")):
                    return _csv_rows(archive.read(name)), name
    return [], ""


def _json_payload(content: bytes) -> Any:
    return json.loads(_decode(content))


def _data_date_from_url(url: str | None, last_modified: str | None) -> str | None:
    parsed = parse_date_value(url or "")
    match = re.search(r"PR(\d{2})(\d{2})(\d{2})\.zip", url or "", re.I)
    if match:
        try:
            parsed = datetime.strptime("".join(match.groups()), "%d%m%y").date().isoformat()
        except ValueError:
            pass
    return parsed or parse_date_value(last_modified or "")


def _fail(summary: str, scope: str, *, schema: bool = False) -> dict[str, Any]:
    return source_result(
        parser_state="WAIT_SCHEMA_MISMATCH" if schema else "WAIT_EMPTY_PARSE",
        data_date=None,
        record_count=0,
        summary=summary,
        output={"scope": scope, "rows": []},
        error=summary if schema else None,
    )


def _bhav_rows(content: bytes) -> tuple[list[dict[str, str]], str]:
    rows, source_name = _zip_csv(content, ("pd",))
    if rows:
        return rows, source_name
    rows = _csv_rows(content)
    return rows, "csv"


def parse_nse_trade_to_trade(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    rows, source_name = _bhav_rows(content)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        series = str(row.get("SERIES") or row.get("SctySrs") or "").strip().upper()
        symbol = str(row.get("SYMBOL") or row.get("TckrSymb") or "").strip().upper()
        if not symbol or series not in T2T_SERIES:
            continue
        normalized.append(
            {
                "symbol": symbol,
                "series": series,
                "name": str(row.get("SECURITY") or row.get("FinInstrmNm") or "").strip() or None,
                "close": parse_float(row.get("CLOSE_PRICE") or row.get("ClsPric")) or None,
                "t2t": True,
                "intradayEligible": False,
                "tradeMode": "DELIVERY_ONLY",
            }
        )
    if not normalized:
        return _fail("No trade-for-trade series rows were found in the NSE bhavcopy.", "NSE_T2T")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=_data_date_from_url(url, last_modified),
        record_count=len(normalized),
        summary=f"Derived {len(normalized)} NSE trade-for-trade symbols from {source_name}.",
        output={
            "scope": "NSE_T2T",
            "sourceRowCount": len(rows),
            "normalizedRowCount": len(normalized),
            "series": sorted(T2T_SERIES),
            "rows": normalized,
        },
    )


def parse_kite_derivatives_contract_master(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    raw = _csv_rows(content)
    if len(raw) < 90000:
        return _fail(
            f"Kite instrument dump is incomplete ({len(raw)} rows; expected at least 90000).",
            "DERIVATIVE_CONTRACT_MASTER",
            schema=True,
        )
    filtered: list[dict[str, Any]] = []
    for row in raw:
        exchange = str(row.get("exchange") or "").strip().upper()
        instrument_type = str(row.get("instrument_type") or "").strip().upper()
        symbol = str(row.get("name") or "").strip().upper()
        lot_size = parse_int(row.get("lot_size"))
        expiry = parse_date_value(row.get("expiry"))
        if (
            exchange not in DERIVATIVE_EXCHANGES
            or instrument_type not in DERIVATIVE_TYPES
            or not symbol
            or not expiry
            or lot_size <= 0
        ):
            continue
        filtered.append(
            {
                "symbol": symbol,
                "exchange": exchange,
                "instrumentType": instrument_type,
                "expiry": expiry,
                "lotSize": lot_size,
            }
        )
    if not filtered:
        return _fail("No valid NFO/BFO/MCX FUT/CE/PE contracts found.", "DERIVATIVE_CONTRACT_MASTER")

    grouped: dict[tuple[str, str], set[tuple[str, str, int]]] = defaultdict(set)
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for row in filtered:
        key = (row["exchange"], row["symbol"])
        grouped[key].add((row["expiry"], row["instrumentType"], row["lotSize"]))
        counts[key] += 1
    normalized: list[dict[str, Any]] = []
    for (exchange, symbol), schedules in sorted(grouped.items()):
        schedule_rows = [
            {"expiry": expiry, "instrumentType": kind, "lotSize": lot}
            for expiry, kind, lot in sorted(schedules)
        ]
        future = [row for row in schedule_rows if row["instrumentType"] == "FUT"]
        nearest = (future or schedule_rows)[0]
        normalized.append(
            {
                "symbol": symbol,
                "exchange": exchange,
                "nearestExpiry": nearest["expiry"],
                "nearestLotSize": nearest["lotSize"],
                "contractTypes": sorted({row["instrumentType"] for row in schedule_rows}),
                "expiryCount": len({row["expiry"] for row in schedule_rows}),
                "contractCount": counts[(exchange, symbol)],
                "lotSchedules": schedule_rows,
                "sourceTrust": "OPEN_SOURCE_UNOFFICIAL",
            }
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=_data_date_from_url(url, last_modified) or date.today().isoformat(),
        record_count=len(normalized),
        summary=(
            f"Filtered {len(filtered)} derivative contracts from {len(raw)} Kite rows "
            f"and aggregated them into {len(normalized)} underlying schedules."
        ),
        output={
            "scope": "DERIVATIVE_CONTRACT_MASTER",
            "sourceRowCount": len(raw),
            "filteredContractCount": len(filtered),
            "normalizedRowCount": len(normalized),
            "rows": normalized,
        },
    )


def parse_nse_board_meetings(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    payload = _json_payload(content)
    rows = payload if isinstance(payload, list) else payload.get("data", []) if isinstance(payload, dict) else []
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("bm_symbol") or "").strip().upper()
        meeting_date = parse_date_value(row.get("bm_date") or row.get("proposedMeetingDate"))
        if not symbol or not meeting_date:
            continue
        purpose = str(row.get("bm_purpose") or "").strip()
        normalized.append(
            {
                "symbol": symbol,
                "name": row.get("sm_name"),
                "isin": row.get("sm_isin"),
                "meetingDate": meeting_date,
                "purpose": purpose,
                "description": row.get("bm_desc"),
                "resultsEvent": "financial result" in purpose.lower(),
                "attachment": row.get("attachment"),
                "publishedAt": row.get("bm_timestamp") or row.get("sysTime"),
            }
        )
    if not normalized:
        return _fail("NSE board-meeting endpoint returned no schema-valid symbol events.", "NSE_BOARD_MEETINGS")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=_data_date_from_url(url, last_modified) or date.today().isoformat(),
        record_count=len(normalized),
        summary=f"Parsed {len(normalized)} NSE board-meeting events.",
        output={"scope": "NSE_BOARD_MEETINGS", "sourceRowCount": len(rows), "normalizedRowCount": len(normalized), "rows": normalized},
    )


def _most_active_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("data"), list):
        return [dict(row, basis="legacy") for row in payload["data"] if isinstance(row, dict)]
    by_id: dict[str, dict[str, Any]] = {}
    for basis in ("volume", "value"):
        section = payload.get(basis) or {}
        for raw in section.get("data") or []:
            if not isinstance(raw, dict):
                continue
            ident = str(raw.get("identifier") or "").strip()
            if not ident:
                continue
            if ident in by_id:
                by_id[ident]["basis"] = "volume+value"
            else:
                by_id[ident] = dict(raw, basis=basis)
    return list(by_id.values())


def parse_nse_most_active_derivatives(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    raw = _most_active_rows(_json_payload(content))
    normalized = []
    for row in raw:
        symbol = str(row.get("underlying") or "").strip().upper()
        identifier = str(row.get("identifier") or "").strip()
        if not symbol or not identifier:
            continue
        normalized.append(
            {
                "symbol": symbol,
                "identifier": identifier,
                "basis": row.get("basis"),
                "instrumentType": row.get("instrumentType"),
                "instrument": row.get("instrument"),
                "expiryDate": parse_date_value(row.get("expiryDate")),
                "optionType": row.get("optionType"),
                "strikePrice": parse_float(row.get("strikePrice")) or None,
                "lastPrice": parse_float(row.get("lastPrice")) or None,
                "pChange": parse_float(row.get("pChange")),
                "contractsTraded": parse_int(row.get("numberOfContractsTraded")),
                "turnover": parse_float(row.get("totalTurnover")),
                "openInterest": parse_int(row.get("openInterest")),
                "underlyingValue": parse_float(row.get("underlyingValue")) or None,
            }
        )
    if not normalized:
        return _fail("NSE most-active derivative response has no valid contracts.", "NSE_MOST_ACTIVE_DERIVATIVES")
    section = "options" if "index=options" in (url or "").lower() else "futures"
    for row in normalized:
        row["section"] = section
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=_data_date_from_url(url, last_modified) or date.today().isoformat(),
        record_count=len(normalized),
        summary=f"Parsed {len(normalized)} most-active NSE {section} contracts.",
        output={"scope": f"NSE_MOST_ACTIVE_{section.upper()}", "sourceRowCount": len(raw), "normalizedRowCount": len(normalized), "rows": normalized},
    )


def parse_nse_ipo_issue_calendar(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    payload = _json_payload(content)
    rows = payload if isinstance(payload, list) else payload.get("data", []) if isinstance(payload, dict) else []
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        normalized.append(
            {
                "symbol": symbol,
                "companyName": row.get("companyName"),
                "series": row.get("series"),
                "status": str(row.get("status") or "UNKNOWN").strip(),
                "feedSection": str(
                    row.get("feedSection")
                    or ("current" if "current" in (url or "").lower() else "issue_calendar")
                ),
                "issueStartDate": parse_date_value(row.get("issueStartDate")),
                "issueEndDate": parse_date_value(row.get("issueEndDate")),
                "issuePrice": row.get("issuePrice"),
                "issueSize": row.get("issueSize"),
                "sharesBid": parse_int(row.get("noOfsharesBid")),
                "sharesOffered": parse_int(row.get("noOfSharesOffered")),
                "subscriptionTimes": parse_float(row.get("noOfTime")) or None,
            }
        )
    if not normalized:
        return _fail("NSE IPO endpoint returned no symbol-bearing issue rows.", "NSE_IPO_ISSUE_CALENDAR")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=_data_date_from_url(url, last_modified) or date.today().isoformat(),
        record_count=len(normalized),
        summary=f"Parsed {len(normalized)} NSE IPO issue-calendar rows without relabelling status.",
        output={"scope": "NSE_IPO_ISSUE_CALENDAR", "sourceRowCount": len(rows), "normalizedRowCount": len(normalized), "rows": normalized},
    )


def parse_nse_pr_market_snapshot(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    pd_rows, pd_name = _zip_csv(content, ("pd",))
    if not pd_rows:
        return _fail("PR ZIP has no pd equity file.", "NSE_PR_MARKET_SNAPSHOT", schema=True)
    eq_rows = [row for row in pd_rows if str(row.get("SERIES") or "").strip().upper() == "EQ"]
    rows: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for row in eq_rows:
        symbol = str(row.get("SYMBOL") or "").strip().upper()
        previous = parse_float(row.get("PREV_CL_PR"))
        close = parse_float(row.get("CLOSE_PRICE"))
        if not symbol or previous <= 0 or close <= 0:
            continue
        changes.append(
            {
                "symbol": symbol,
                "name": row.get("SECURITY"),
                "close": close,
                "previousClose": previous,
                "pctChange": round((close - previous) / previous * 100, 2),
            }
        )
        high = parse_float(row.get("HIGH_PRICE"))
        low = parse_float(row.get("LOW_PRICE"))
        high52 = parse_float(row.get("HI_52_WK"))
        low52 = parse_float(row.get("LO_52_WK"))
        event = "HIT_52W_HIGH" if high52 > 0 and high >= high52 else "HIT_52W_LOW" if low52 > 0 and low <= low52 else None
        if event:
            rows.append(
                {
                    "section": "wk52",
                    "symbol": symbol,
                    "name": row.get("SECURITY"),
                    "event": event,
                    "close": close,
                    "high52": high52 or None,
                    "low52": low52 or None,
                }
            )
    changes.sort(key=lambda row: row["pctChange"], reverse=True)
    for item in changes[:25]:
        rows.append(dict(item, section="top_gainers"))
    for item in changes[-25:]:
        rows.append(dict(item, section="top_losers"))

    actions, _ = _zip_csv(content, ("bc", "ca"))
    for action in actions:
        symbol = str(action.get("SYMBOL") or "").strip().upper()
        series = str(action.get("SERIES") or "").strip().upper()
        if not symbol or series not in {"", "EQ", "BE", "BZ", "BT", "ST", "SZ"}:
            continue
        rows.append(
            {
                "section": "corp_actions",
                "symbol": symbol,
                "series": series or None,
                "name": action.get("SECURITY"),
                "exDate": parse_date_value(action.get("EX_DT")),
                "recordDate": parse_date_value(action.get("RECORD_DT")),
                "purpose": action.get("PURPOSE"),
            }
        )

    mcap_rows, _ = _zip_csv(content, ("mcap",))
    for item in mcap_rows:
        symbol = str(item.get("Symbol") or item.get("SYMBOL") or "").strip().upper()
        series = str(item.get("Series") or item.get("SERIES") or "").strip().upper()
        market_cap_rs = parse_float(item.get("Market Cap(Rs.)") or item.get("MARKET_CAP"))
        if not symbol or series not in {"", "EQ"} or market_cap_rs <= 0:
            continue
        rows.append(
            {
                "section": "mcap",
                "symbol": symbol,
                "name": item.get("Security Name") or item.get("SECURITY"),
                "close": parse_float(item.get("Close Price/Paid up value(Rs.)")) or None,
                "marketCapRs": market_cap_rs,
                "marketCapCr": round(market_cap_rs / 10_000_000, 4),
                "category": item.get("Category"),
            }
        )
    if not rows or any(not row.get("symbol") for row in rows):
        return _fail("PR ZIP produced no complete symbol-bearing market rows.", "NSE_PR_MARKET_SNAPSHOT")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=_data_date_from_url(url, last_modified),
        record_count=len(rows),
        summary=f"Derived {len(rows)} symbol-safe PR market rows from {pd_name}.",
        output={
            "scope": "NSE_PR_MARKET_SNAPSHOT",
            "sourceRowCount": len(pd_rows) + len(actions) + len(mcap_rows),
            "normalizedRowCount": len(rows),
            "rows": rows,
        },
    )
