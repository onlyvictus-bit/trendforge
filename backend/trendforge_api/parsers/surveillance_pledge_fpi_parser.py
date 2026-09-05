from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any

from .common import parse_date_value, parse_float, parse_int, source_result, today_iso


def _optional_float(value: Any) -> float | None:
    if value is None or not str(value).strip():
        return None
    return parse_float(value)


def _optional_int(value: Any) -> int | None:
    if value is None or not str(value).strip():
        return None
    return parse_int(value)


def _financial_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    cleaned = re.sub(r"[^0-9.+-]", "", text.strip("()"))
    if not cleaned:
        return None
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return -number if negative else number


def _json(content: bytes, label: str) -> tuple[Any | None, dict[str, Any] | None]:
    try:
        return json.loads(content), None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        reason = f"{label} response is not valid JSON: {exc}"
        return None, source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary=reason,
            output={"endpointConnected": True, "noDataNow": True},
            error=reason,
        )


def parse_nse_asm(content: bytes, **_kwargs) -> dict[str, Any]:
    payload, error = _json(content, "NSE ASM")
    if error:
        return error
    if not isinstance(payload, dict):
        return _schema("NSE ASM response is not an object.")
    rows: list[dict[str, Any]] = []
    for key, measure in (
        ("longterm", "LONG_TERM_ASM"),
        ("shortterm", "SHORT_TERM_ASM"),
    ):
        section = payload.get(key)
        data = section.get("data") if isinstance(section, dict) else None
        if not isinstance(data, list):
            return _schema(f"NSE ASM response lacks {key}.data.")
        for item in data:
            if not isinstance(item, dict) or not item.get("symbol"):
                return _schema(f"NSE ASM {key} contains an invalid row.")
            rows.append(
                {
                    "symbol": str(item["symbol"]).upper(),
                    "company": str(item.get("companyName") or ""),
                    "isin": str(item.get("isin") or "").upper(),
                    "measure": measure,
                    "stage": str(item.get("asmSurvIndicator") or ""),
                    "code": str(item.get("survCode") or ""),
                    "description": str(item.get("survDesc") or ""),
                    "effectiveDate": parse_date_value(item.get("asmTime")),
                }
            )
    if not rows:
        return _valid_empty("NSE ASM endpoint currently lists no securities.", "ASM")
    data_dates = [row["effectiveDate"] for row in rows if row["effectiveDate"]]
    if not data_dates:
        return _schema("NSE ASM rows lack an effective source date.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(data_dates),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSE ASM surveillance rows.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "STOCK_SAFETY_HARD_BLOCK",
            "rows": rows,
        },
    )


def parse_nse_gsm(content: bytes, **_kwargs) -> dict[str, Any]:
    payload, error = _json(content, "NSE GSM")
    if error:
        return error
    data = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        return _schema("NSE GSM response is not a list.")
    if not data:
        return _valid_empty("NSE GSM endpoint currently lists no securities.", "GSM")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict) or not item.get("symbol"):
            return _schema("NSE GSM contains an invalid row.")
        rows.append(
            {
                "symbol": str(item["symbol"]).upper(),
                "company": str(item.get("companyName") or item.get("company") or ""),
                "isin": str(item.get("isin") or "").upper(),
                "measure": "GSM",
                "stage": str(item.get("stage") or item.get("gsmStage") or ""),
                "code": str(item.get("survCode") or item.get("code") or ""),
                "description": str(
                    item.get("survDesc") or item.get("description") or ""
                ),
                "effectiveDate": parse_date_value(
                    item.get("date") or item.get("gsmTime")
                ),
            }
        )
    data_dates = [row["effectiveDate"] for row in rows if row["effectiveDate"]]
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(data_dates) if data_dates else today_iso(),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSE GSM surveillance rows.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "STOCK_SAFETY_HARD_BLOCK",
            "rows": rows,
        },
    )


def parse_nse_esm(content: bytes, **_kwargs) -> dict[str, Any]:
    payload, error = _json(content, "NSE ESM")
    if error:
        return error
    data = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        return _schema("NSE ESM response is not a list.")
    if not data:
        return _valid_empty("NSE ESM endpoint currently lists no securities.", "ESM")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict) or not item.get("symbol"):
            return _schema("NSE ESM contains an invalid row.")
        effective_date = parse_date_value(item.get("esmTime") or item.get("date"))
        if not effective_date:
            return _schema("NSE ESM row lacks an effective source date.")
        rows.append(
            {
                "symbol": str(item["symbol"]).upper(),
                "company": str(item.get("companyName") or item.get("company") or ""),
                "isin": str(item.get("isin") or "").upper(),
                "measure": "ESM",
                "stage": str(item.get("esmSurvIndicator") or item.get("stage") or ""),
                "code": str(item.get("survCode") or item.get("code") or ""),
                "description": str(item.get("survDesc") or item.get("description") or ""),
                "effectiveDate": effective_date,
            }
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(row["effectiveDate"] for row in rows),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSE ESM surveillance rows.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "STOCK_SAFETY_HARD_BLOCK",
            "rows": rows,
        },
    )


def parse_nse_pledge_data(content: bytes, **_kwargs) -> dict[str, Any]:
    payload, error = _json(content, "NSE pledge")
    if error:
        return error
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return _schema("NSE pledge response lacks a data list.")
    if not data:
        return _valid_empty("NSE pledge endpoint currently has no rows.", "PLEDGE")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict) or not item.get("comName"):
            return _schema("NSE pledge response contains an invalid company row.")
        reporting_date = parse_date_value(item.get("shp"))
        if reporting_date is None:
            return _schema("NSE pledge row lacks a shareholding-period date.")
        rows.append(
            {
                "company": str(item["comName"]).strip(),
                "reportingDate": reporting_date,
                "broadcastDate": parse_date_value(item.get("broadcastDt")),
                "pledgedShares": _optional_int(item.get("numSharesPledged")),
                "pledgedPercent": _optional_float(item.get("percSharesPledged")),
                "promoterHoldingPercent": _optional_float(
                    item.get("percPromoterHolding")
                ),
                "promoterHoldingShares": _optional_int(item.get("totPromoterHolding")),
                "issuedShares": _optional_int(item.get("totIssuedShares")),
            }
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(row["reportingDate"] for row in rows),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSE promoter-pledge rows.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "DELAYED_PROMOTER_RISK",
            "symbolMappingRequired": True,
            "rows": rows,
        },
    )


def parse_nse_oi_spurts(content: bytes, **_kwargs) -> dict[str, Any]:
    payload, error = _json(content, "NSE OI-spurts")
    if error:
        return error
    if not isinstance(payload, dict):
        return _schema("NSE OI-spurts response is not an object.")
    data = payload.get("data")
    if not isinstance(data, list):
        return _schema("NSE OI-spurts response lacks a data list.")
    if not data:
        return _valid_empty(
            "NSE OI-spurts endpoint currently has no rows.", "OI_SPURTS"
        )
    current_date = parse_date_value(payload.get("currTradingDate"))
    if current_date is None:
        return _schema("NSE OI-spurts response lacks current trading date.")
    rows = [
        {
            "symbol": str(item.get("symbol") or "").upper(),
            "latestOi": _optional_int(item.get("latestOI")),
            "previousOi": _optional_int(item.get("prevOI")),
            "oiChange": _optional_int(item.get("changeInOI")),
            "oiChangePercent": _optional_float(item.get("avgInOI")),
            "volume": _optional_int(item.get("volume")),
            "underlyingValue": _optional_float(item.get("underlyingValue")),
            "currentTradingDate": current_date,
            "previousTradingDate": parse_date_value(payload.get("prevTradingDate")),
        }
        for item in data
        if isinstance(item, dict) and item.get("symbol")
    ]
    if not rows:
        return _schema("NSE OI-spurts has no valid symbol rows.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=current_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSE OI-spurt rows.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "DERIVATIVES_ACTIVITY_CONTEXT_ONLY",
            "canCalculateMwplPercent": False,
            "warning": "OI change lacks the MWPL denominator and cannot estimate ban utilization.",
            "rows": rows,
        },
    )


class _TableRows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, _attrs) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def parse_nse_regulation_disclosure(content: bytes, **_kwargs) -> dict[str, Any]:
    """Parse NSE Regulation 29/31 corporate shareholding-disclosure JSON.

    Live payload may be a bare list [] or {\"data\": [...]}. Empty list is a valid
    connected empty official endpoint (no disclosures in the current window).
    """
    payload, error = _json(content, "NSE regulation disclosure")
    if error:
        return error
    scope = "OWNERSHIP_DISCLOSURE_EVENTS"
    if isinstance(payload, list):
        data = payload
    elif isinstance(payload, dict):
        data = payload.get("data")
        if data is None:
            # some variants nest under records
            records = payload.get("records")
            data = records if isinstance(records, list) else []
    else:
        return _schema("NSE regulation disclosure response is not JSON list/object.")
    if not isinstance(data, list):
        return _schema("NSE regulation disclosure lacks a data list.")
    if not data:
        return _valid_empty(
            "NSE regulation disclosure endpoint is connected but has no events now.",
            "REGULATION_DISCLOSURE",
        )
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            return _schema("NSE regulation disclosure contains a non-object row.")
        symbol = str(item.get("symbol") or "").strip().upper()
        if not symbol:
            # keep scrip-only rows if present
            symbol = str(item.get("symbolName") or item.get("company") or "").strip()
        if not symbol:
            continue
        event_date = parse_date_value(
            item.get("creditDateFrom")
            or item.get("creditDate")
            or item.get("sr_dateof_creation")
            or item.get("broadcastDateTime")
            or item.get("ddmDroadcastDate")
            or item.get("date")
        )
        rows.append(
            {
                "symbol": symbol,
                "company": str(
                    item.get("company")
                    or item.get("companyName")
                    or item.get("comName")
                    or ""
                ).strip(),
                "eventDate": event_date,
                "promoterName": str(
                    item.get("promoterName")
                    or item.get("personName")
                    or item.get("acquirerName")
                    or ""
                ).strip()
                or None,
                "transactionType": str(
                    item.get("transactionType")
                    or item.get("typeOfEvent")
                    or item.get("tranType")
                    or ""
                ).strip()
                or None,
                "shares": _optional_int(
                    item.get("nosharesAcquired") or item.get("numofShares")
                ),
                "percentBefore": _optional_float(
                    item.get("persharesPrior") or item.get("pershareAlrdyheldPrmtr")
                ),
                "percentChange": _optional_float(
                    item.get("persharesAcquired") or item.get("perofShares")
                ),
                "percentAfter": _optional_float(
                    item.get("persharesAfterAcq") or item.get("persharesPostevent")
                ),
                "broadcastDate": parse_date_value(
                    item.get("ddmDroadcastDate") or item.get("broadcastDateTime")
                ),
                "raw": {
                    k: item.get(k)
                    for k in (
                        "isin",
                        "nameOfLenderDebenture",
                        "entityFavorShares",
                        "reasonForEncumbrance",
                    )
                    if item.get(k) not in (None, "")
                },
            }
        )
    if not rows:
        return _valid_empty(
            "NSE regulation disclosure returned rows without usable symbol/event fields.",
            "REGULATION_DISCLOSURE",
        )
    dates = [row["eventDate"] for row in rows if row.get("eventDate")]
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(dates) if dates else today_iso(),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSE regulation shareholding-disclosure events.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": scope,
            "rows": rows,
        },
    )


def parse_bse_pledge_data(content: bytes, **_kwargs) -> dict[str, Any]:
    """Parse BSE consolidated promoter pledge shareholding snapshot.

    Payload shape: {"Table": [ {ScripCode, CompanyName, PROMOTEREncum_*, ...}, ... ], "Table1": [...]}
    """
    payload, error = _json(content, "BSE pledge")
    if error:
        return error
    if not isinstance(payload, dict):
        return _schema("BSE pledge response is not a JSON object.")
    table = payload.get("Table")
    if not isinstance(table, list):
        return _schema("BSE pledge response lacks Table list.")
    if not table:
        return _valid_empty("BSE pledge endpoint currently has no company rows.", "PLEDGE")
    rows: list[dict[str, Any]] = []
    for item in table:
        if not isinstance(item, dict):
            continue
        scrip = item.get("ScripCode")
        company = str(item.get("CompanyName") or "").strip()
        if scrip is None or not company:
            continue
        published = parse_date_value(item.get("SHP_PulishedTime") or item.get("MAxDate"))
        rows.append(
            {
                "scripCode": str(scrip).strip(),
                "company": company,
                "publishedDate": published,
                "totalIssuedShares": _optional_int(item.get("TOTAL_NO_OF_ISSUED_SHARES")),
                "promoterHoldingShares": _optional_int(
                    item.get("NoofShares_TOTAL_PROMOTER_HOLDING")
                ),
                "promoterHoldingPercent": _optional_float(
                    item.get("Percentage_TOTAL_PROMOTER_HOLDING")
                ),
                "publicHoldingShares": _optional_int(item.get("Public_NoofShares_HOLDING")),
                "promoterEncumberedShares": _optional_int(
                    item.get("PROMOTEREncum_NoOfshares")
                ),
                "promoterEncumberedPercentOfPromoter": _optional_float(
                    item.get("PROMOTEREncum_Percof_PromoterShares")
                ),
                "promoterEncumberedPercentOfTotal": _optional_float(
                    item.get("PROMOTEREncum_Percof_TotalShares")
                ),
                "pledgedShares": _optional_int(item.get("Noofsharespledged")),
                "pledgeFlag": str(item.get("FLAg_Pledge") or "").strip() or None,
                "groupCode": str(item.get("GROUP_CODE") or "").strip() or None,
                "listedStatus": str(item.get("LISTED_STATUS") or "").strip() or None,
                "industry": str(item.get("Industry_name") or "").strip() or None,
                "encumberedMarketCap": _optional_float(item.get("EncumMktCAP")),
            }
        )
    if not rows:
        return _schema("BSE pledge Table contained no usable company rows.")
    dates = [row["publishedDate"] for row in rows if row["publishedDate"]]
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(dates) if dates else today_iso(),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} BSE promoter-pledge company rows.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "DELAYED_PROMOTER_PLEDGE_RISK",
            "symbolMappingRequired": True,
            "rows": rows,
        },
    )


def _nsdl_auc_rows(
    table: list[list[str]], table_index: int, fallback_date: str | None
) -> list[dict[str, Any]]:
    """Parse NSDL FPI Assets Under Custody category tables (ReportDetail AUC layout)."""
    rows: list[dict[str, Any]] = []
    # Find header row with Equity/Debt columns
    header_idx = None
    for idx, cells in enumerate(table):
        joined = " ".join(cells).casefold()
        if "equity" in joined and "debt" in joined and "total" in joined:
            header_idx = idx
            break
    if header_idx is None:
        return rows
    # Normalize common multi-row headers: Category / Sub Category / Equity / Debt / ...
    for row_index, cells in enumerate(table[header_idx + 1 :], start=header_idx + 1):
        if len(cells) < 3:
            continue
        category = cells[0].strip()
        if not category or category.casefold() in {
            "category of the fpi",
            "sr. no.",
            "total",
            "grand total",
        }:
            # still allow Total rows with numbers
            if category.casefold() not in {"total", "grand total"}:
                continue
        # Layout A: Category | SubCategory | Equity | Debt | DebtVRR | Hybrid | Total
        if len(cells) >= 7:
            subcategory = cells[1].strip()
            values = cells[2:7]
            labels = ("equityAucCrore", "debtAucCrore", "debtVrrAucCrore", "hybridAucCrore", "totalAucCrore")
        elif len(cells) >= 4:
            subcategory = ""
            values = cells[1:4] if len(cells) == 4 else cells[2:5]
            labels = ("equityAucCrore", "debtAucCrore", "totalAucCrore")
            if len(values) < 3:
                continue
        else:
            continue
        numeric = [_financial_float(v) for v in values[: len(labels)]]
        if any(v is None for v in numeric):
            continue
        # Skip pure header-like text rows
        if category.casefold() in {"category i", "category ii", "category iii"} and all(
            v is None or v == 0 for v in numeric
        ):
            continue
        row: dict[str, Any] = {
            "tableIndex": table_index,
            "rowIndex": row_index,
            "tableType": "FPI_AUC_BY_CATEGORY",
            "reportingDate": fallback_date,
            "category": category,
            "subCategory": subcategory if len(cells) >= 7 else None,
            "routeOrProduct": subcategory or category,
        }
        for label, value in zip(labels, numeric):
            row[label] = value
        rows.append(row)
    return rows


def _nsdl_limit_rows(
    table: list[list[str]], table_index: int, fallback_date: str | None
) -> list[dict[str, Any]]:
    """Parse NSDL FPI investment-limit utilization tables."""
    rows: list[dict[str, Any]] = []
    if not table:
        return rows
    header = " ".join(table[0]).casefold()
    if "instrument type" not in header or "investment" not in header:
        return rows
    for row_index, cells in enumerate(table[1:], start=1):
        if len(cells) < 4:
            continue
        instrument = cells[0].strip()
        if not instrument or instrument.casefold() in {"instrument type", "notes"}:
            continue
        # Prefer: Instrument | Eligible | Upper Limit | Investment | ... | Total Investment | % utilised
        numbers = [_financial_float(c) for c in cells[1:]]
        usable = [n for n in numbers if n is not None]
        if not usable:
            continue
        rows.append(
            {
                "tableIndex": table_index,
                "rowIndex": row_index,
                "tableType": "FPI_INVESTMENT_LIMITS",
                "reportingDate": fallback_date,
                "category": "FPI_LIMITS",
                "routeOrProduct": instrument,
                "instrumentType": instrument,
                "upperLimitCrore": numbers[1] if len(numbers) > 1 else None,
                "investmentCrore": numbers[2] if len(numbers) > 2 else usable[0],
                "totalInvestmentCrore": numbers[5] if len(numbers) > 5 else usable[-1],
                "limitUtilisedPercent": numbers[6] if len(numbers) > 6 else None,
                "cells": cells,
            }
        )
    return rows


def parse_nsdl_fpi_daily(content: bytes, **_kwargs) -> dict[str, Any]:
    text = content.decode("utf-8", errors="replace")
    if "request rejected" in text.casefold() and "<table" not in text.casefold():
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="NSDL FPI endpoint rejected the request (WAF/access control).",
            output={"endpointConnected": False, "noDataNow": True, "rows": []},
            error="NSDL request rejected",
        )
    parser = _TableRows()
    parser.feed(text)
    title_date = parse_date_value(text)
    rows: list[dict[str, Any]] = []
    for table_index, table in enumerate(parser.tables):
        joined = " ".join(cell for row in table for cell in row)
        joined_cf = joined.casefold()
        if "Derivative Products" in joined or (
            "Open Interest" in joined
            and any(product in joined for product in ("Index Futures", "Stock Futures"))
        ):
            rows.extend(_nsdl_derivative_rows(table, table_index, title_date))
        elif "FPI Investments" in joined or (
            "Gross Purchases" in joined and "Net Investment" in joined
        ):
            rows.extend(_nsdl_cash_rows(table, table_index, title_date))
        elif "auc" in joined_cf and (
            "category of the fpi" in joined_cf or "sub category of the fpi" in joined_cf
        ):
            rows.extend(_nsdl_auc_rows(table, table_index, title_date))
        elif "instrument type" in joined_cf and "upper limit" in joined_cf:
            rows.extend(_nsdl_limit_rows(table, table_index, title_date))
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=title_date,
            record_count=0,
            summary="NSDL FPI endpoint is connected but has no parseable daily-trend rows.",
            output={"endpointConnected": True, "noDataNow": True, "rows": []},
        )
    dates = [row["reportingDate"] for row in rows if row.get("reportingDate")]
    table_types = sorted({str(row.get("tableType") or "") for row in rows})
    scope = (
        "AGGREGATE_FPI_DAILY_TRENDS_ONLY"
        if any(t in {"CASH_AND_DEBT", "DERIVATIVES"} for t in table_types)
        else "AGGREGATE_FPI_AUC_AND_LIMITS_CONTEXT"
    )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(dates) if dates else title_date or today_iso(),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSDL aggregate FPI rows ({', '.join(table_types)}).",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": scope,
            "canProveStockHoldings": False,
            "tableTypes": table_types,
            "rows": rows,
        },
    )


def parse_cdsl_fpi_fortnightly_sector(content: bytes, **_kwargs) -> dict[str, Any]:
    """Parse CDSL Fortnightly Sector-wise FII/FPI investment HTML pages.

    Public pages under:
      https://www.cdslindia.com/publications/FII/FortnightlySecWisePages/
    provide sector AUC and net investment for screener regime context.
    """
    text = content.decode("utf-8", errors="replace")
    parser = _TableRows()
    parser.feed(text)
    title_date = parse_date_value(text)
    # Prefer "as on <date>" from header cells
    for table in parser.tables:
        for row in table[:4]:
            for cell in row:
                parsed = parse_date_value(cell)
                if parsed:
                    title_date = parsed
    rows: list[dict[str, Any]] = []
    for table_index, table in enumerate(parser.tables):
        if not table:
            continue
        # Find header with Sectors
        header_idx = None
        for idx, cells in enumerate(table):
            joined = " ".join(cells).casefold()
            if "sectors" in joined and "equity" in joined:
                header_idx = idx
                break
        if header_idx is None:
            continue
        for row_index, cells in enumerate(table[header_idx + 1 :], start=header_idx + 1):
            if len(cells) < 4:
                continue
            # Layout: Sr | Sector | Equity AUC | Debt... | totals | net investment cols...
            first = cells[0].strip()
            sector = cells[1].strip() if len(cells) > 1 else ""
            if not sector or sector.casefold() in {"sectors", "total", "grand total"}:
                # allow Total rows with numbers
                if sector.casefold() not in {"total", "grand total"}:
                    continue
            if not first.isdigit() and sector.casefold() not in {"total", "grand total"}:
                # sometimes sector is first column
                if first and not first.isdigit():
                    sector = first
                else:
                    continue
            equity_auc = _financial_float(cells[2] if len(cells) > 2 else None)
            # last equity-like total columns vary; keep primary metrics
            numbers = [_financial_float(c) for c in cells[2:]]
            usable = [n for n in numbers if n is not None]
            if equity_auc is None and not usable:
                continue
            rows.append(
                {
                    "tableIndex": table_index,
                    "rowIndex": row_index,
                    "tableType": "FPI_FORTNIGHTLY_SECTOR",
                    "reportingDate": title_date,
                    "sector": sector,
                    "routeOrProduct": sector,
                    "equityAucCrore": equity_auc,
                    "primaryValueCrore": equity_auc if equity_auc is not None else usable[0],
                    "values": usable,
                    "cells": cells,
                    "source": "cdsl_fpi_fortnightly_sector",
                }
            )
    if not rows:
        # NSDL FPI selection / listing pages (peer source when CDSL WAF blocks)
        anchors = re.findall(
            r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            text,
            flags=re.I | re.S,
        )
        for href, label in anchors:
            label_clean = re.sub(r"<[^>]+>", "", label).strip()
            low = f"{href} {label_clean}".casefold()
            if not any(tok in low for tok in ("fpi", "fii", "fortnight", "sector", "auc")):
                continue
            if len(label_clean) < 3 and "http" not in href:
                continue
            rows.append(
                {
                    "tableType": "FPI_DIRECTORY_LINK",
                    "reportingDate": title_date,
                    "sector": label_clean[:120] or href,
                    "routeOrProduct": label_clean[:120] or href,
                    "name": label_clean[:120],
                    "url": href,
                    "symbol": re.sub(r"[^A-Z0-9]+", "_", (label_clean or "FPI").upper())[:24]
                    or "FPI",
                    "source": "nsdl_or_cdsl_fpi_directory",
                }
            )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=title_date,
            record_count=0,
            summary="CDSL fortnightly sector page connected but no sector rows parsed.",
            output={
                "endpointConnected": True,
                "noDataNow": True,
                "scope": "AGGREGATE_FPI_FORTNIGHTLY_SECTOR_CONTEXT",
                "rows": [],
            },
        )
    dates = [r.get("reportingDate") for r in rows if r.get("reportingDate")]
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(dates) if dates else title_date or today_iso(),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} CDSL fortnightly sector-wise FPI rows.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "AGGREGATE_FPI_FORTNIGHTLY_SECTOR_CONTEXT",
            "canProveStockHoldings": False,
            "rows": rows,
        },
    )


def _nsdl_fortnightly_date_from_url(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(
        r"FII(?:Invest|Inest)Sector_([A-Za-z]+)(\d{1,2})(\d{4})\.html?",
        url,
        re.IGNORECASE,
    )
    if not match:
        return None
    month, day, year = match.groups()
    return parse_date_value(f"{day}-{month[:3]}-{year}")


def parse_nsdl_fpi_fortnightly(
    content: bytes, *, url: str | None = None, **_kwargs
) -> dict[str, Any]:
    """Parse NSDL fortnightly FPI sector/selection HTML into aggregate sector rows.

    Selection pages without data tables are returned as empty parse (not usable populated).
    """
    text = content.decode("utf-8", errors="replace")
    if "request rejected" in text.casefold() and len(text) < 1000:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="NSDL fortnightly endpoint rejected the request (WAF/access control).",
            output={"endpointConnected": False, "noDataNow": True, "rows": []},
            error="NSDL request rejected",
        )
    parser = _TableRows()
    parser.feed(text)
    title_date = _nsdl_fortnightly_date_from_url(url) or parse_date_value(text)
    rows: list[dict[str, Any]] = []
    for table_index, table in enumerate(parser.tables):
        joined = " ".join(cell for row in table for cell in row)
        joined_cf = joined.casefold()
        # Sector allocation style tables
        if any(
            marker in joined_cf
            for marker in (
                "sector",
                "industry",
                "net investment",
                "gross purchases",
                "market value",
                "equity",
            )
        ):
            # Prefer multi-column numeric data rows
            for row_index, cells in enumerate(table):
                if len(cells) < 3:
                    continue
                serial_number = cells[0].strip().isdigit()
                label_index = 1 if serial_number and len(cells) > 2 else 0
                label = cells[label_index].strip()
                if not label or label.casefold() in {
                    "sector",
                    "industry",
                    "particulars",
                    "sr. no.",
                    "s.no.",
                }:
                    continue
                numbers = [_financial_float(c) for c in cells[label_index + 1 :]]
                if sum(1 for n in numbers if n is not None) < 1:
                    continue
                # skip pure navigation option dumps
                if len(label) > 200:
                    continue
                rows.append(
                    {
                        "tableIndex": table_index,
                        "rowIndex": row_index,
                        "tableType": "FPI_FORTNIGHTLY_SECTOR",
                        "reportingDate": title_date,
                        "sector": label,
                        "routeOrProduct": label,
                        "values": [n for n in numbers if n is not None],
                        "primaryValueCrore": next((n for n in numbers if n is not None), None),
                        "cells": cells,
                    }
                )
        # Also accept AUC category layout if present on the page
        if "category of the fpi" in joined_cf or (
            "auc" in joined_cf and "equity" in joined_cf and "debt" in joined_cf
        ):
            rows.extend(_nsdl_auc_rows(table, table_index, title_date))
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=title_date,
            record_count=0,
            summary="NSDL fortnightly page connected but exposed no sector/market data rows.",
            output={
                "endpointConnected": True,
                "noDataNow": True,
                "scope": "AGGREGATE_FPI_FORTNIGHTLY_SECTOR_CONTEXT",
                "rows": [],
            },
        )
    dates = [row.get("reportingDate") for row in rows if row.get("reportingDate")]
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(dates) if dates else title_date or today_iso(),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSDL fortnightly FPI sector/context rows.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "AGGREGATE_FPI_FORTNIGHTLY_SECTOR_CONTEXT",
            "canProveStockHoldings": False,
            "rows": rows,
        },
    )


def _nsdl_cash_rows(
    table: list[list[str]], table_index: int, fallback_date: str | None
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reporting_date = fallback_date
    current_category: str | None = None
    for row_index, cells in enumerate(table):
        if not cells or "Reporting Date" in cells or "Gross Purchases" in cells:
            continue
        parsed_date = parse_date_value(cells[0])
        if parsed_date and len(cells) >= 8:
            reporting_date = parsed_date
            current_category = cells[1]
            route = cells[2]
            values = cells[3:7]
            conversion = _financial_float(cells[7])
        elif len(cells) >= 6:
            current_category = cells[0]
            route = cells[1]
            values = cells[2:6]
            conversion = None
        elif len(cells) >= 5 and cells[0].strip().lower() == "total":
            current_category = "TOTAL"
            route = "TOTAL"
            values = cells[1:5]
            conversion = None
        elif len(cells) >= 5 and current_category:
            route = cells[0]
            values = cells[1:5]
            conversion = None
        else:
            continue
        if reporting_date is None or len(values) != 4:
            continue
        numeric = [_financial_float(value) for value in values]
        if any(value is None for value in numeric):
            continue
        rows.append(
            {
                "tableIndex": table_index,
                "rowIndex": row_index,
                "tableType": "CASH_AND_DEBT",
                "reportingDate": reporting_date,
                "category": current_category,
                "routeOrProduct": route,
                "grossPurchasesCrore": numeric[0],
                "grossSalesCrore": numeric[1],
                "netInvestmentCrore": numeric[2],
                "netInvestmentUsdMillion": numeric[3],
                "conversionUsdInr": conversion,
                "cells": cells,
            }
        )
    return rows


def _nsdl_derivative_rows(
    table: list[list[str]], table_index: int, fallback_date: str | None
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reporting_date = fallback_date
    for row_index, cells in enumerate(table):
        parsed_date = parse_date_value(cells[0]) if cells else None
        if parsed_date and len(cells) >= 8:
            reporting_date = parsed_date
            product = cells[1]
            values = cells[2:8]
        elif len(cells) == 7:
            product = cells[0]
            values = cells[1:7]
        else:
            continue
        if reporting_date is None or len(values) != 6:
            continue
        numeric = [_financial_float(value) for value in values]
        if any(value is None for value in numeric):
            continue
        rows.append(
            {
                "tableIndex": table_index,
                "rowIndex": row_index,
                "tableType": "DERIVATIVES",
                "reportingDate": reporting_date,
                "category": "FPI_DERIVATIVE_POSITIONING",
                "routeOrProduct": product,
                "buyContracts": numeric[0],
                "buyValueCrore": numeric[1],
                "sellContracts": numeric[2],
                "sellValueCrore": numeric[3],
                "openInterestContracts": numeric[4],
                "openInterestValueCrore": numeric[5],
                "cells": cells,
            }
        )
    return rows


def _valid_empty(summary: str, source: str) -> dict[str, Any]:
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=today_iso(),
        record_count=0,
        summary=summary,
        output={
            "endpointConnected": True,
            "noDataNow": True,
            "validEmpty": True,
            "scope": "STOCK_SAFETY_HARD_BLOCK"
            if source in {"ASM", "GSM"}
            else "CONTEXT_ONLY",
            "rows": [],
        },
    )


def _schema(reason: str) -> dict[str, Any]:
    return source_result(
        parser_state="WAIT_SCHEMA_MISMATCH",
        data_date=None,
        record_count=0,
        summary=reason,
        output={"endpointConnected": True, "noDataNow": True, "rows": []},
        error=reason,
    )
