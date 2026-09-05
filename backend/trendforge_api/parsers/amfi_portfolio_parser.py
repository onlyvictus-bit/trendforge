from __future__ import annotations

import json
import re
from calendar import monthrange
from datetime import date
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


def _extract_month(text: str, data_date: str | None) -> str | None:
    match = re.search(r"(20\d{2})[-/](0?[1-9]|1[0-2])", text)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}"
    match = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})",
        text,
        re.I,
    )
    if match:
        month = (
            "jan feb mar apr may jun jul aug sep oct nov dec".split().index(
                match.group(1)[:3].lower()
            )
            + 1
        )
        return f"{match.group(2)}-{month:02d}"
    if data_date:
        return data_date[:7]
    return None


def parse_amfi_portfolio(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    try:
        bundle = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        bundle = None
    if (
        isinstance(bundle, dict)
        and bundle.get("datasetKind") == "AMFI_SCHEME_WISE_QUARTERLY_EXPOSURE"
    ):
        return _parse_scheme_wise_bundle(bundle)

    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    month = _extract_month(text[:5000], data_date)
    rows, source_name = rows_from_content(content)
    holdings: list[dict[str, Any]] = []

    for row in rows:
        stock = find_value(row, ("symbol", "stock", "company", "issuer", "security"))
        isin = find_value(row, ("isin",))
        scheme = find_value(row, ("scheme", "scheme_name"))
        amc = find_value(row, ("amc", "fund_house", "mutual_fund"))
        quantity = parse_int(
            find_value(row, ("quantity", "qty", "shares", "no_of_shares"))
        )
        market_value = parse_float(
            find_value(row, ("market_value", "value", "mkt_value", "fair_value"))
        )
        percent_aum = parse_float(
            find_value(
                row, ("percent_aum", "%_aum", "aum", "percentage_to_nav", "holding_pct")
            )
        )
        if not stock or (quantity <= 0 and market_value <= 0):
            continue
        holdings.append(
            {
                "amc": (amc or "").strip(),
                "scheme": (scheme or "").strip(),
                "isin": (isin or "").strip().upper(),
                "stock": stock.strip().upper(),
                "quantity": quantity,
                "marketValue": market_value,
                "percentAum": percent_aum,
                "month": month,
                "scope": "SWING_CONFIRMATION_ONLY",
            }
        )

    if not holdings:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="No usable AMFI holdings found in latest raw snapshot.",
            output={
                "scope": "SWING_CONFIRMATION_ONLY",
                "dateSource": date_source,
                "month": month,
            },
        )

    by_stock: dict[str, dict[str, Any]] = {}
    for item in holdings:
        stock = item["stock"]
        entry = by_stock.setdefault(
            stock,
            {
                "stock": stock,
                "schemeCount": 0,
                "amcNames": set(),
                "totalValue": 0.0,
                "scope": "SWING_CONFIRMATION_ONLY",
            },
        )
        entry["schemeCount"] += 1
        if item["amc"]:
            entry["amcNames"].add(item["amc"])
        entry["totalValue"] += item["marketValue"]

    sponsors = []
    for item in by_stock.values():
        amc_count = len(item["amcNames"])
        if amc_count >= 5:
            signal = "STRONG"
        elif amc_count >= 2:
            signal = "MODERATE"
        elif amc_count == 1:
            signal = "WEAK"
        else:
            signal = "NEUTRAL"
        sponsors.append(
            {
                "stock": item["stock"],
                "amcCount": amc_count,
                "schemeCount": item["schemeCount"],
                "totalValue": round(item["totalValue"], 2),
                "signal": signal,
                "scope": "SWING_CONFIRMATION_ONLY",
            }
        )

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(holdings),
        summary=f"AMFI portfolio holdings parsed from {source_name}; swing confirmation only.",
        output={
            "scope": "SWING_CONFIRMATION_ONLY",
            "dateSource": date_source,
            "month": month,
            "warning": "AMFI monthly holdings cannot create intraday READY.",
            "holdings": holdings,
            "sponsors": sponsors,
        },
    )


def _parse_scheme_wise_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    coverage = bundle.get("coverage") or {}
    quarter_date = str(bundle.get("quarterDate") or "")[:10] or None
    data_date = _quarter_end(quarter_date)
    quarter_name = str(bundle.get("quarterName") or "").strip()
    if coverage.get("state") != "COMPLETE" or int(coverage.get("failedFunds") or 0):
        return source_result(
            parser_state="WAIT_PARSE_ERROR",
            data_date=data_date,
            record_count=0,
            summary="AMFI scheme-wise API coverage is partial; evidence is blocked.",
            output={
                "datasetKind": "AMFI_SCHEME_WISE_QUARTERLY_EXPOSURE",
                "scope": "SWING_CONFIRMATION_ONLY",
                "coverage": coverage,
                "quantityAvailable": False,
            },
            error="One or more AMFI fund API responses failed validation or retrieval.",
        )

    exposures: list[dict[str, Any]] = []
    for response in bundle.get("responses", []):
        if response.get("state") != "OK":
            continue
        for row in response.get("rows", []):
            company = str(row.get("Company_Name") or "").strip()
            scheme = str(row.get("Scheme_Name") or "").strip()
            if not company or not scheme:
                continue
            exposures.append(
                {
                    "sourceRowIndex": len(exposures),
                    "mfId": str(row.get("MF_ID") or response.get("mfId") or ""),
                    "amc": str(response.get("mfName") or "").strip(),
                    "schemeId": str(row.get("Scheme_ID") or "").strip(),
                    "scheme": scheme,
                    "isin": str(row.get("ISIN") or "").strip().upper(),
                    "companyName": company.upper(),
                    "securityType": str(row.get("Security_Type") or "").strip(),
                    "marketValue": parse_float(row.get("MarketValue")),
                    "marketValuePercentage": parse_float(
                        row.get("MarketValuePercentage")
                    ),
                    "quarterDate": str(row.get("QuarterDate") or quarter_date)[:10],
                    "quarterName": str(row.get("QuarterName") or quarter_name),
                    "scope": "SWING_CONFIRMATION_ONLY",
                }
            )
    if not exposures:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="AMFI scheme-wise API bundle contained no usable exposures.",
            output={
                "datasetKind": "AMFI_SCHEME_WISE_QUARTERLY_EXPOSURE",
                "scope": "SWING_CONFIRMATION_ONLY",
                "coverage": coverage,
                "quantityAvailable": False,
            },
        )

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(exposures),
        summary="AMFI quarterly scheme exposures parsed; delayed swing context only.",
        output={
            "datasetKind": "AMFI_SCHEME_WISE_QUARTERLY_EXPOSURE",
            "scope": "SWING_CONFIRMATION_ONLY",
            "quarterDate": quarter_date,
            "quarterName": quarter_name,
            "coverage": coverage,
            "quantityAvailable": False,
            "warning": (
                "This API has market value and portfolio percentage but no quantity. "
                "It cannot create monthly quantity deltas or intraday READY."
            ),
            "exposures": exposures,
        },
    )


def _quarter_end(quarter_start: str | None) -> str | None:
    if not quarter_start:
        return None
    try:
        start = date.fromisoformat(quarter_start)
    except ValueError:
        return None
    end_month = start.month + 2
    end_year = start.year + (end_month - 1) // 12
    end_month = (end_month - 1) % 12 + 1
    return date(end_year, end_month, monthrange(end_year, end_month)[1]).isoformat()
