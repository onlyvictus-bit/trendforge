"""Parsers for NSE MTO delivery and short-selling archive files."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from .common import decode_bytes, extract_data_date, source_result

_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9&.\-]{0,24}$")


def parse_nse_mto_delivery(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse MTO_DDMMYYYY.DAT security-wise delivery position (record type 20)."""
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if not parts or parts[0] != "20":
            continue
        try:
            if len(parts) >= 7:
                symbol, series, qty, dlv, pct = (
                    parts[2],
                    parts[3],
                    parts[4],
                    parts[5],
                    parts[6],
                )
            elif len(parts) == 6:
                symbol, series, qty, dlv, pct = parts[2], None, parts[3], parts[4], parts[5]
            else:
                continue
            sym = str(symbol or "").strip().upper()
            if not _SYMBOL_RE.fullmatch(sym):
                continue
            rows.append(
                {
                    "symbol": sym,
                    "series": (series or "").strip().upper() or None,
                    "qty_traded": int(float(str(qty).replace(",", "") or 0)),
                    "deliverable_qty": int(float(str(dlv).replace(",", "") or 0)),
                    "delivery_pct": float(str(pct).replace(",", "") or 0),
                }
            )
        except (TypeError, ValueError):
            continue

    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="MTO file had no type-20 delivery rows",
            output={"dateSource": date_source, "rows": []},
        )

    # Prefer EQ series when present, keep all rows for inventory sample
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"MTO delivery rows={len(rows)}",
        output={"dateSource": date_source, "rows": rows, "records": rows},
    )


def parse_nse_short_selling(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse shortselling_DDMMYYYY.csv daily short disclosure."""
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    reader = csv.reader(io.StringIO(text))
    rows_raw = [row for row in reader if any(cell.strip() for cell in row)]
    if len(rows_raw) < 2:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="Short-selling file empty",
            output={"dateSource": date_source, "rows": []},
        )

    records: list[dict[str, Any]] = []
    for row in rows_raw[1:]:
        if len(row) < 4:
            continue
        try:
            sym = str(row[1]).strip().upper()
            if not _SYMBOL_RE.fullmatch(sym):
                continue
            records.append(
                {
                    "security": str(row[0]).strip(),
                    "symbol": sym,
                    "trade_date": str(row[2]).strip(),
                    "short_qty": int(str(row[3]).replace(",", "").strip() or 0),
                }
            )
        except (TypeError, ValueError):
            continue

    if not records:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="Short-selling file had no usable rows",
            output={"dateSource": date_source, "rows": []},
        )

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(records),
        summary=f"Short-selling rows={len(records)}",
        output={"dateSource": date_source, "rows": records, "records": records},
    )


def parse_bse_fo_bhavcopy(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse BSE derivatives BhavCopy_BSE_FO_*.CSV unified format."""
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary="BSE FO bhavcopy missing header",
            output={"dateSource": date_source, "rows": []},
        )
    rows: list[dict[str, Any]] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        # keep raw keys; normalize a few aliases for screener
        rec = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
        symbol = (
            rec.get("TckrSymb")
            or rec.get("symbol")
            or rec.get("Symbol")
            or rec.get("SCRIP_CD")
        )
        if symbol:
            rec["symbol"] = str(symbol).strip().upper()
        rows.append(rec)

    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="BSE FO bhavcopy empty",
            output={"dateSource": date_source, "rows": []},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"BSE FO bhav rows={len(rows)}",
        output={"dateSource": date_source, "rows": rows, "records": rows},
    )


def parse_nse_preopen_cash(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse NSE market-data-pre-open JSON into flat stock rows."""
    import json

    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary="Pre-open payload is not JSON",
            output={"dateSource": date_source, "rows": []},
        )

    rows: list[dict[str, Any]] = []
    for item in payload.get("data") or []:
        if not isinstance(item, dict):
            continue
        meta = item.get("metadata") or {}
        pom = (item.get("detail") or {}).get("preOpenMarket") or {}
        symbol = str(meta.get("symbol") or "").strip().upper()
        if not _SYMBOL_RE.fullmatch(symbol):
            continue
        rows.append(
            {
                "symbol": symbol,
                "iep": pom.get("IEP"),
                "change": pom.get("Change"),
                "pct_change": pom.get("perChange"),
                "pChange": pom.get("perChange"),
                "prev_close": pom.get("prevClose"),
                "final_qty": pom.get("finalQuantity"),
                "total_traded_volume": pom.get("totalTradedVolume"),
                "total_buy_qty": pom.get("totalBuyQuantity"),
                "total_sell_qty": pom.get("totalSellQuantity"),
                "turnover": meta.get("totalTurnover"),
                "ltp": pom.get("IEP"),
            }
        )

    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="Pre-open cash had no stock rows",
            output={"dateSource": date_source, "rows": []},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Pre-open cash rows={len(rows)}",
        output={
            "dateSource": date_source,
            "timestamp": payload.get("timestamp"),
            "status": payload.get("niftyPreopenStatus"),
            "rows": rows,
            "records": rows,
        },
    )
