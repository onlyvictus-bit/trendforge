"""Pure parsers for third-party FII holding-change screens.

These are lagged ownership-change lists (often 3M / QoQ), not official daily
FII stock tape. They never invent tickers from company names.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any

from .common import parse_float, source_result, today_iso


SCOPE = "THIRD_PARTY_HOLDING_CHANGE_INFORMATIONAL"
ZERO = "ZERO_SCORE_INFORMATIONAL"
_TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9&_.-]{0,31}$")


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    parsed = parse_float(value, default=float("nan"))
    if parsed != parsed:  # NaN
        return None
    return parsed


def _ticker(value: Any) -> str | None:
    text = _text(value).upper().replace("NSE:", "").replace(".NS", "")
    if not text or not _TICKER_RE.fullmatch(text):
        return None
    return text


def _load_json(content: bytes) -> Any:
    return json.loads(content.decode("utf-8-sig"))


class _HtmlTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered == "table":
            self._table = []
        elif lowered == "tr" and self._table is not None:
            self._row = []
        elif lowered in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(_text("".join(self._cell)))
            self._cell = None
        elif lowered == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif lowered == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def _tables(html: str) -> list[list[list[str]]]:
    parser = _HtmlTableParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return []
    return parser.tables


def _header_index(header: list[str], *needles: str) -> int | None:
    lowered = [cell.casefold() for cell in header]
    for needle in needles:
        for index, cell in enumerate(lowered):
            if needle in cell:
                return index
    return None


def parse_screener_in_fii_holding_change(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    try:
        payload = _load_json(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Screener.in FII bundle is not valid JSON.",
            output={"rows": [], "scope": SCOPE},
            error=str(exc),
        )
    pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(pages, list):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Screener.in FII bundle is missing pages.",
            output={"rows": [], "scope": SCOPE},
            error="missing pages",
        )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("html"), str):
            continue
        for table in _tables(page["html"]):
            if len(table) < 2:
                continue
            header = table[0]
            name_i = _header_index(header, "name")
            hold_i = _header_index(header, "fii hold")
            chg_i = _header_index(header, "chg in fii", "fii hold %")
            if name_i is None:
                continue
            for raw in table[1:]:
                name = _text(raw[name_i] if name_i < len(raw) else "")
                if (
                    not name
                    or name.casefold() == "name"
                    or name.casefold().startswith("median")
                ):
                    continue
                key = re.sub(r"[^a-z0-9]+", "", name.casefold())
                if not key or key in seen:
                    continue
                seen.add(key)
                hold = _num(raw[hold_i]) if hold_i is not None and hold_i < len(raw) else None
                chg = _num(raw[chg_i]) if chg_i is not None and chg_i < len(raw) else None
                rows.append(
                    {
                        "name": name,
                        "symbol": None,
                        "fiiHoldPct": hold,
                        "fiiChgPct": chg,
                        "source": "screener.in",
                        "scoreAuthority": ZERO,
                    }
                )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="Screener.in returned no FII-hold rows; retain last-good.",
            output={"rows": [], "scope": SCOPE},
            error="empty screener rows",
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=today_iso(),
        record_count=len(rows),
        summary="Third-party Screener.in FII hold-% change; names only; not daily FII tape.",
        output={"rows": rows, "scope": SCOPE, "hasTicker": False},
        error=None,
    )


def parse_tickertape_fii_holding_change_3m(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    try:
        payload = _load_json(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Tickertape FII bundle is not valid JSON.",
            output={"rows": [], "scope": SCOPE},
            error=str(exc),
        )
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Tickertape FII bundle is missing results.",
            output={"rows": [], "scope": SCOPE},
            error="missing results",
        )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        stock = item.get("stock") if isinstance(item.get("stock"), dict) else item
        info = stock.get("info") if isinstance(stock.get("info"), dict) else {}
        ratios = stock.get("advancedRatios") if isinstance(stock.get("advancedRatios"), dict) else {}
        symbol = _ticker(info.get("ticker") or item.get("ticker") or stock.get("ticker"))
        if symbol is None or symbol in seen:
            continue
        seen.add(symbol)
        rows.append(
            {
                "name": _text(info.get("name") or item.get("name")),
                "symbol": symbol,
                "fiiHoldPct": _num(ratios.get("forInstHldng") or item.get("forInstHldng")),
                "fiiChgPct": _num(ratios.get("forInstHldng3M") or item.get("forInstHldng3M")),
                "source": "tickertape",
                "scoreAuthority": ZERO,
            }
        )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="Tickertape returned no ticker rows; retain last-good.",
            output={"rows": [], "scope": SCOPE},
            error="empty tickertape rows",
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=today_iso(),
        record_count=len(rows),
        summary="Third-party Tickertape 3M FII holding change with ticker; not daily FII tape.",
        output={"rows": rows, "scope": SCOPE, "hasTicker": True},
        error=None,
    )


def parse_dhan_fii_holding_change(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    try:
        payload = _load_json(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Dhan FII bundle is not valid JSON.",
            output={"rows": [], "scope": SCOPE},
            error=str(exc),
        )
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Dhan FII bundle is missing data.",
            output={"rows": [], "scope": SCOPE},
            error="missing data",
        )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        symbol = _ticker(item.get("Sym") or item.get("symbol"))
        if symbol is None or symbol in seen:
            continue
        seen.add(symbol)
        rows.append(
            {
                "name": _text(item.get("DispSym") or item.get("name")),
                "symbol": symbol,
                "isin": _text(item.get("Isin") or item.get("isin")) or None,
                "fiiHoldPct": None,
                "fiiChgPct": _num(item.get("FIIHLDChagPer") or item.get("fiiChgPct")),
                "source": "dhan",
                "scoreAuthority": ZERO,
            }
        )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="Dhan returned no ticker rows; retain last-good.",
            output={"rows": [], "scope": SCOPE},
            error="empty dhan rows",
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=today_iso(),
        record_count=len(rows),
        summary="Third-party Dhan FII holding-change % with ticker; not daily FII tape.",
        output={"rows": rows, "scope": SCOPE, "hasTicker": True},
        error=None,
    )


def parse_equitymaster_fii_buys_reference(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    html = content.decode("utf-8-sig", errors="replace")
    if "Just a moment" in html or "cf-challenge" in html.casefold():
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Equitymaster returned a Cloudflare challenge; retain last-good.",
            output={"rows": [], "scope": SCOPE},
            error="cloudflare challenge",
        )
    tables = _tables(html)
    if not tables:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Equitymaster HTML has no usable table.",
            output={"rows": [], "scope": SCOPE},
            error="no table",
        )
    table = max(tables, key=lambda item: len(item) * max(len(item[0]) if item else 0, 1))
    if len(table) < 4:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="Equitymaster table has too few rows; retain last-good.",
            output={"rows": [], "scope": SCOPE},
            error="sparse table",
        )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in table[1:]:
        name = _text(raw[0] if raw else "")
        key = re.sub(r"[^a-z0-9]+", "", name.casefold())
        if not name or not key or key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "name": name,
                "symbol": None,
                # Observed table columns are company, CMP, market cap,
                # current FII %, previous FII %, and change.  Preserve both
                # levels and the reported delta so the stock-name panel can
                # show useful evidence without inventing a ticker.
                "price": _num(raw[1]) if len(raw) > 1 else None,
                "marketCapCr": _num(raw[2]) if len(raw) > 2 else None,
                "fiiHoldPct": _num(raw[3]) if len(raw) > 3 else None,
                "previousFiiHoldPct": _num(raw[4]) if len(raw) > 4 else None,
                "fiiChgPct": _num(raw[5]) if len(raw) > 5 else None,
                "cells": raw[1:6],
                "source": "equitymaster",
                "scoreAuthority": ZERO,
            }
        )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="Equitymaster returned no name rows; retain last-good.",
            output={"rows": [], "scope": SCOPE},
            error="empty equitymaster rows",
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=today_iso(),
        record_count=len(rows),
        summary="Third-party Equitymaster institutional-buy names; no ticker; not daily FII tape.",
        output={"rows": rows, "scope": SCOPE, "hasTicker": False},
        error=None,
    )
