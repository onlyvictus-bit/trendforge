from __future__ import annotations

import json
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


def _deal_type(row: dict[str, str], url: str | None = None) -> str:
    raw = find_value(row, ("deal_type", "type", "session")) or ""
    upper = raw.upper()
    if "BLOCK" in upper:
        return "BLOCK"
    if "BULK" in upper:
        return "BULK"
    lower_url = (url or "").lower()
    if "block" in lower_url:
        return "BLOCK"
    if "bulk" in lower_url:
        return "BULK"
    return "LARGE"


def parse_nse_large_deals(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    rows, source_name = rows_from_content(content)
    deals: list[dict[str, Any]] = []

    for row in rows:
        symbol = find_value(row, ("symbol", "scrip_symbol", "ticker"))
        if not symbol:
            continue
        buyer = find_value(row, ("buyer", "buy_client", "buy")) or ""
        seller = find_value(row, ("seller", "sell_client", "sell")) or ""
        client = find_value(row, ("client_name", "client")) or ""
        side = (find_value(row, ("buy_sell", "buy/sell", "side")) or "").strip().upper()
        if client and side in {"B", "BUY"}:
            buyer, seller = client, ""
        elif client and side in {"S", "SELL"}:
            buyer, seller = "", client
        quantity = parse_int(find_value(row, ("quantity", "qty", "traded_qty")))
        price = parse_float(find_value(row, ("price", "trade_price", "avg_price")))
        value = parse_float(find_value(row, ("value", "turnover", "trade_value")))
        close_price = parse_float(
            find_value(row, ("close", "close_price", "previous_close")), price
        )
        row_date = (
            parse_date_value(find_value(row, ("date", "trade_date"))) or data_date
        )
        if quantity <= 0 and value > 0 and price > 0:
            quantity = int(value / price)
        if value <= 0 and quantity > 0 and price > 0:
            value = quantity * price
        if price <= 0 or (not buyer and not seller):
            continue
        premium_pct = (
            ((price - close_price) / close_price * 100) if close_price > 0 else 0.0
        )
        if premium_pct >= 2:
            mode = "PREMIUM"
        elif premium_pct <= -2:
            mode = "DISCOUNT"
        else:
            mode = "AT_MARKET"
        deals.append(
            {
                "symbol": symbol.strip().upper(),
                "dealType": _deal_type(row, url),
                "date": row_date,
                "buyer": buyer.strip(),
                "seller": seller.strip(),
                "quantity": quantity,
                "price": price,
                "value": value,
                "closePrice": close_price,
                "premiumPct": round(premium_pct, 3),
                "dealMode": mode,
                "scope": "STOCK_LEVEL_DEAL_ANCHOR",
            }
        )

    if not deals:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="No usable NSE large/bulk/block deals found in latest raw snapshot.",
            output={"scope": "STOCK_LEVEL_DEAL_ANCHOR", "dateSource": date_source},
        )

    anchors: dict[str, dict[str, Any]] = {}
    for deal in deals:
        current = anchors.get(deal["symbol"])
        if current is None or deal["value"] > current["value"]:
            anchor_type = "NEUTRAL"
            if deal["dealMode"] == "PREMIUM" and deal["buyer"]:
                anchor_type = "BUYER_PREMIUM"
            elif deal["dealMode"] == "DISCOUNT" and deal["seller"]:
                anchor_type = "SELLER_DISCOUNT"
            anchors[deal["symbol"]] = {
                "symbol": deal["symbol"],
                "anchorType": anchor_type,
                "anchorPrice": deal["price"],
                "buyer": deal["buyer"],
                "seller": deal["seller"],
                "value": deal["value"],
                "dealMode": deal["dealMode"],
            }

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(deals),
        summary=f"NSE large deals parsed from {source_name}; deal anchors available.",
        output={
            "scope": "STOCK_LEVEL_DEAL_ANCHOR",
            "dateSource": date_source,
            "deals": deals,
            "anchors": list(anchors.values()),
            "rows": deals,
        },
    )


def parse_nse_large_deals_snapshot(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    """Parse NSE live large-deals snapshot JSON (bulk/block/short sections).

    This is the populated companion when /api/block-deal returns empty data[]
    outside the block session window.
    """
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="NSE large-deals snapshot is not valid JSON.",
            output={"scope": "STOCK_LEVEL_DEAL_ANCHOR", "rows": []},
            error="invalid json",
        )
    if not isinstance(payload, dict):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="NSE large-deals snapshot is not a JSON object.",
            output={"scope": "STOCK_LEVEL_DEAL_ANCHOR", "rows": []},
            error="not object",
        )

    as_on = parse_date_value(payload.get("as_on_date") or payload.get("timestamp"))
    deals: list[dict[str, Any]] = []
    section_counts: dict[str, int] = {}
    for section_key, deal_type in (
        ("BLOCK_DEALS_DATA", "BLOCK"),
        ("BULK_DEALS_DATA", "BULK"),
        ("SHORT_DEALS_DATA", "SHORT"),
    ):
        section = payload.get(section_key)
        if not isinstance(section, list):
            section_counts[deal_type] = 0
            continue
        count = 0
        for item in section:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            side = str(item.get("buySell") or "").strip().upper()
            client = str(item.get("clientName") or "").strip()
            quantity = parse_int(item.get("qty") or item.get("quantity"))
            price = parse_float(item.get("watp") or item.get("price"))
            if quantity <= 0 and price <= 0 and not client:
                continue
            buyer = client if side in {"B", "BUY", "P"} else ""
            seller = client if side in {"S", "SELL"} else ""
            if not buyer and not seller and client:
                # unknown side — keep client as buyer for visibility
                buyer = client
            value = quantity * price if quantity > 0 and price > 0 else 0.0
            event_date = parse_date_value(item.get("date")) or as_on
            deals.append(
                {
                    "symbol": symbol,
                    "company": str(item.get("name") or "").strip(),
                    "dealType": deal_type,
                    "date": event_date,
                    "side": side or None,
                    "clientName": client or None,
                    "buyer": buyer,
                    "seller": seller,
                    "quantity": quantity,
                    "price": price,
                    "value": value,
                    "remarks": item.get("remarks"),
                    "scope": "STOCK_LEVEL_DEAL_ANCHOR",
                    "sourceSection": section_key,
                }
            )
            count += 1
        section_counts[deal_type] = count

    if not deals:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=as_on,
            record_count=0,
            summary="NSE large-deals snapshot connected but has no bulk/block rows now.",
            output={
                "endpointConnected": True,
                "noDataNow": True,
                "scope": "STOCK_LEVEL_DEAL_ANCHOR",
                "sectionCounts": section_counts,
                "rows": [],
            },
        )

    dates = [d["date"] for d in deals if d.get("date")]
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(dates) if dates else as_on,
        record_count=len(deals),
        summary=(
            f"Parsed {len(deals)} NSE large-deal rows "
            f"(block={section_counts.get('BLOCK', 0)}, "
            f"bulk={section_counts.get('BULK', 0)}, "
            f"short={section_counts.get('SHORT', 0)})."
        ),
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": "STOCK_LEVEL_DEAL_ANCHOR",
            "sectionCounts": section_counts,
            "rows": deals,
            "blockRows": [d for d in deals if d["dealType"] == "BLOCK"],
            "bulkRows": [d for d in deals if d["dealType"] == "BULK"],
        },
    )
