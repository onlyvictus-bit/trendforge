from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any

import pandas as pd

from .common import csv_rows_from_text, decode_bytes, source_result


def _schema(reason: str) -> dict[str, Any]:
    return source_result(
        parser_state="WAIT_SCHEMA_MISMATCH",
        data_date=None,
        record_count=0,
        summary=reason,
        output={"endpointConnected": True, "noDataNow": True},
        error=reason,
    )


def _date_from_url(url: str | None) -> str | None:
    if not url:
        return None
    for candidate in reversed(re.findall(r"(?<!\d)(\d{8})(?!\d)", url)):
        for fmt in ("%d%m%Y", "%Y%m%d"):
            try:
                return datetime.strptime(candidate, fmt).date().isoformat()
            except ValueError:
                continue
    return None


def _valid_empty(summary: str, scope: str, data_date: str | None) -> dict[str, Any]:
    if data_date is None:
        return _schema(f"{scope} valid-empty artifact lacks a source date.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=0,
        summary=summary,
        output={
            "endpointConnected": True,
            "noDataNow": True,
            "validEmpty": True,
            "scope": scope,
            "rows": [],
        },
    )


def parse_nse_price_bands(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    text = decode_bytes(content)
    if "<html" in text[:500].casefold() or "<!doctype" in text[:500].casefold():
        return _schema("NSE price-band response is HTML, not the complete CSV.")
    raw_rows = csv_rows_from_text(text)
    if not raw_rows:
        return _schema("NSE price-band CSV has no rows.")
    required = {"symbol", "series", "security_name", "band", "remarks"}
    if not required.issubset(raw_rows[0]):
        return _schema("NSE price-band CSV lacks the required complete-list columns.")
    data_date = _date_from_url(url)
    if data_date is None:
        return _schema("NSE price-band CSV URL lacks a valid publication date.")

    rows: list[dict[str, Any]] = []
    allowed = {2.0, 5.0, 10.0, 20.0, 40.0}
    for raw in raw_rows:
        symbol = str(raw.get("symbol") or "").strip().upper()
        series = str(raw.get("series") or "").strip().upper()
        band_text = str(raw.get("band") or "").strip()
        if not symbol or not series or not band_text:
            return _schema("NSE price-band CSV contains an incomplete row.")
        if band_text.casefold() == "no band":
            band_percent = None
        else:
            try:
                band_percent = float(band_text.replace("%", "").strip())
            except ValueError:
                return _schema(f"NSE price-band row has an unknown band: {band_text!r}.")
            if band_percent not in allowed:
                return _schema(f"NSE price-band row has an unsupported band: {band_percent}.")
        rows.append(
            {
                "symbol": symbol,
                "series": series,
                "company": str(raw.get("security_name") or "").strip(),
                "bandPercent": band_percent,
                "hasPriceBand": band_percent is not None,
                "remarks": str(raw.get("remarks") or "").strip(),
            }
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSE complete price-band classifications.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "STOCK_TRADABILITY_PRICE_BAND_CLASSIFICATION",
            "boundaryAuthority": "CLASSIFICATION_ONLY",
            "rows": rows,
        },
    )


def parse_nse_auction_securities(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    if b"<html" in content[:500].lower() or b"<!doctype" in content[:500].lower():
        return _schema("NSE periodic-auction response is HTML, not a workbook.")
    try:
        sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, header=None, dtype=str)
    except Exception as exc:
        return _schema(f"NSE periodic-auction workbook is unreadable: {type(exc).__name__}.")
    data_date = _date_from_url(url)
    if data_date is None:
        return _schema("NSE periodic-auction workbook URL lacks a valid publication date.")

    parsed_rows: list[dict[str, Any]] = []
    schema_seen = False
    nil_seen = False
    for frame in sheets.values():
        if frame.empty:
            continue
        for header_index in range(min(20, len(frame))):
            header = [
                str(value).strip().casefold() if not pd.isna(value) else ""
                for value in frame.iloc[header_index]
            ]
            if "symbol" not in header or "series" not in header:
                continue
            schema_seen = True
            symbol_index, series_index = header.index("symbol"), header.index("series")
            for _, item in frame.iloc[header_index + 1 :].iterrows():
                symbol = "" if pd.isna(item.iloc[symbol_index]) else str(item.iloc[symbol_index]).strip().upper()
                series = "" if pd.isna(item.iloc[series_index]) else str(item.iloc[series_index]).strip().upper()
                if not symbol:
                    continue
                if symbol == "NIL":
                    nil_seen = True
                    continue
                if not series:
                    return _schema("NSE periodic-auction workbook contains a symbol without series.")
                parsed_rows.append(
                    {
                        "symbol": symbol,
                        "series": series,
                        "restriction": "PERIODIC_CALL_AUCTION_ILLIQUID_SECURITY",
                        "effectiveDate": data_date,
                    }
                )
            break
    if not schema_seen:
        return _schema("NSE periodic-auction workbook lacks Symbol and Series columns.")
    if not parsed_rows:
        if nil_seen:
            return _valid_empty(
                "NSE periodic-call-auction workbook explicitly reports NIL securities.",
                "STOCK_TRADABILITY_PERIODIC_CALL_AUCTION",
                data_date,
            )
        return _schema("NSE periodic-auction workbook has no security rows and no NIL marker.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(parsed_rows),
        summary=f"Parsed {len(parsed_rows)} NSE periodic-call-auction securities.",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "STOCK_TRADABILITY_PERIODIC_CALL_AUCTION",
            "rows": parsed_rows,
        },
    )
