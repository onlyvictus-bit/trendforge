from __future__ import annotations

import json

from .common import parse_date_value, parse_float, source_result


def _unwrap_payload(payload: object) -> list:
    """Accept raw list or common NSE wrappers {data: [...]}, {fiidii: [...]}."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "Data", "fiidii", "FII_DII", "rows", "records"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return inner
        # single-day object with FII/DII nested
        rows: list = []
        for key, val in payload.items():
            if isinstance(val, list):
                rows.extend(val)
            elif isinstance(val, dict) and any(
                k in val for k in ("buyValue", "buyValueCrore", "Buy ₹ Cr", "buy")
            ):
                rows.append(val)
        if rows:
            return rows
    return []


def _category(raw: object) -> str | None:
    category_raw = str(raw or "").strip().upper()
    if category_raw in {"FII", "FPI", "FII/FPI", "FII_FPI", "FOREIGN"}:
        return "FII_FPI"
    if category_raw in {"DII", "DOMESTIC"}:
        return "DII"
    return None


def parse_nse_fii_dii(content: bytes, **_kwargs) -> dict:
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _schema_error(f"invalid JSON: {exc}")

    items = _unwrap_payload(payload)
    if not items:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="NSE FII/DII response contained no flow records.",
        )

    rows: list[dict] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return _schema_error(f"record {index} is not an object")
        category = _category(
            item.get("category")
            or item.get("Category")
            or item.get("client_type")
            or item.get("investorType")
        )
        if category is None:
            return _schema_error(
                f"record {index} has unknown category {item.get('category')}"
            )
        data_date = parse_date_value(
            item.get("date") or item.get("Date") or item.get("asOnDate")
        )
        buy = parse_float(
            item.get("buyValue")
            or item.get("buyValueCrore")
            or item.get("Buy ₹ Cr")
            or item.get("buy")
            or item.get("buyValueInCrores"),
            default=-1,
        )
        sell = parse_float(
            item.get("sellValue")
            or item.get("sellValueCrore")
            or item.get("Sell ₹ Cr")
            or item.get("sell")
            or item.get("sellValueInCrores"),
            default=-1,
        )
        net = parse_float(
            item.get("netValue")
            or item.get("netValueCrore")
            or item.get("Net ₹ Cr")
            or item.get("net")
            or item.get("netValueInCrores"),
            default=float("nan"),
        )
        if data_date is None or buy < 0 or sell < 0:
            return _schema_error(f"record {index} has invalid date or values")
        if net != net:  # NaN → derive
            net = buy - sell
        if abs((buy - sell) - net) > 0.5:
            # tolerate small rounding; still fail large inconsistency
            if abs((buy - sell) - net) > 5.0:
                return _schema_error(f"record {index} net does not equal buy minus sell")
        rows.append(
            {
                "dataDate": data_date,
                "category": category,
                "buyValueCrore": buy,
                "sellValueCrore": sell,
                "netValueCrore": net,
                "scope": "MARKET_REGIME_ONLY",
            }
        )
    # Keep one row per category (latest if duplicates)
    by_cat: dict[str, dict] = {}
    for row in rows:
        by_cat[row["category"]] = row
    rows = list(by_cat.values())
    if not rows:
        return _schema_error("no valid institutional category rows")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(row["dataDate"] for row in rows),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} NSE institutional cash-flow records.",
        output={
            "scope": "MARKET_REGIME_ONLY",
            "warning": "Aggregate FII/DII cash flow is not stock-level attribution.",
            "rows": rows,
            "records": rows,
        },
    )


def _schema_error(reason: str) -> dict:
    return source_result(
        parser_state="WAIT_SCHEMA_MISMATCH",
        data_date=None,
        record_count=0,
        summary=f"NSE FII/DII schema validation failed: {reason}.",
        output={"qualityIssues": [reason]},
        error=reason,
    )


def _to_crore(value: float) -> float:
    """BSE CategoryTurnover publishes absolute rupees; store crore for NSE parity."""
    if value != value:  # NaN
        return value
    # Values >= 1e6 are almost certainly rupees (not already crore).
    if abs(value) >= 1_000_000:
        return round(value / 10_000_000.0, 4)
    return value


def parse_bse_fii_dii(content: bytes, **_kwargs) -> dict:
    """Parse BSE CategoryTurnover JSON (FII/DII cash-side category turnover).

    Live contract (verified 2026-08-10):
      GET https://api.bseindia.com/BseIndiaAPI/api/CategoryTurnover/w
      -> {Table:[{REPORTING_DATE, CLIENT_TYPE_BSENSE, PURCHASE_BSENSE, SALE_BSENSE,
                  NET_BSENSE, CLIENT_TYPE_DII, PURCHASE_DII, SALE_DII, NET_DII, ...}]}

    Aggregate market-regime only — never stock-level FII/MF attribution.
    """
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary=f"BSE FII/DII schema validation failed: invalid JSON: {exc}.",
            output={"qualityIssues": [f"invalid JSON: {exc}"]},
            error=f"invalid JSON: {exc}",
        )

    table: list | None = None
    if isinstance(payload, dict):
        inner = payload.get("Table") or payload.get("table") or payload.get("data")
        if isinstance(inner, list):
            table = inner
    elif isinstance(payload, list):
        table = payload

    if not table:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="BSE CategoryTurnover response contained no FII/DII rows.",
        )

    row0 = table[0]
    if not isinstance(row0, dict):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="BSE FII/DII schema validation failed: first Table row is not an object.",
            output={"qualityIssues": ["first Table row is not an object"]},
            error="first Table row is not an object",
        )

    data_date = parse_date_value(row0.get("REPORTING_DATE") or row0.get("date") or row0.get("Date"))
    rows: list[dict] = []

    fii_buy_raw = parse_float(
        row0.get("PURCHASE_BSENSE") or row0.get("BUY_TOTAL_BSENSE"),
        default=float("nan"),
    )
    fii_sell_raw = parse_float(
        row0.get("SALE_BSENSE") or row0.get("SELL_TOTAL_BSENSE"),
        default=float("nan"),
    )
    fii_net_raw = parse_float(
        row0.get("NET_BSENSE") or row0.get("NET_TOTAL_BSENSE"),
        default=float("nan"),
    )
    if fii_buy_raw == fii_buy_raw and fii_sell_raw == fii_sell_raw:  # not NaN
        if fii_net_raw != fii_net_raw:
            fii_net_raw = fii_buy_raw - fii_sell_raw
        rows.append(
            {
                "dataDate": data_date,
                "category": "FII_FPI",
                "buyValueCrore": _to_crore(fii_buy_raw),
                "sellValueCrore": _to_crore(fii_sell_raw),
                "netValueCrore": _to_crore(fii_net_raw),
                "scope": "MARKET_REGIME_ONLY",
                "exchange": "BSE",
                "sourceField": str(row0.get("CLIENT_TYPE_BSENSE") or "FII_BSENSE"),
            }
        )

    dii_buy_raw = parse_float(
        row0.get("PURCHASE_DII") or row0.get("BUY_TOTAL_DII"),
        default=float("nan"),
    )
    dii_sell_raw = parse_float(
        row0.get("SALE_DII") or row0.get("SELL_TOTAL_DII"),
        default=float("nan"),
    )
    dii_net_raw = parse_float(
        row0.get("NET_DII") or row0.get("NET_TOTAL_DII"),
        default=float("nan"),
    )
    if dii_buy_raw == dii_buy_raw and dii_sell_raw == dii_sell_raw:
        if dii_net_raw != dii_net_raw:
            dii_net_raw = dii_buy_raw - dii_sell_raw
        rows.append(
            {
                "dataDate": data_date,
                "category": "DII",
                "buyValueCrore": _to_crore(dii_buy_raw),
                "sellValueCrore": _to_crore(dii_sell_raw),
                "netValueCrore": _to_crore(dii_net_raw),
                "scope": "MARKET_REGIME_ONLY",
                "exchange": "BSE",
                "sourceField": str(row0.get("CLIENT_TYPE_DII") or "DII_BSENSE"),
            }
        )

    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="BSE CategoryTurnover Table had no usable FII/DII buy/sell fields.",
        )
    if data_date is None:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="BSE FII/DII schema validation failed: missing REPORTING_DATE.",
            output={"qualityIssues": ["missing REPORTING_DATE"]},
            error="missing REPORTING_DATE",
        )

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} BSE institutional category-turnover records.",
        output={
            "scope": "MARKET_REGIME_ONLY",
            "exchange": "BSE",
            "unit": "CRORE",
            "warning": (
                "BSE category turnover is aggregate market-regime context only. "
                "Not stock-level FII/MF attribution. Values converted from rupees to crore."
            ),
            "rows": rows,
            "records": rows,
        },
    )
