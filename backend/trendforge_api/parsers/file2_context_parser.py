"""Pure parsers for the verified file-2 delayed/context source family."""

from __future__ import annotations

import calendar
import io
import json
import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any

from .common import decode_bytes, source_result
from .finish_30_parsers import parse_yahoo_chart


class _Tables(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        tag = tag.casefold()
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    cleaned = re.sub(r"[^0-9.()\-+]", "", str(value)).strip()
    if not cleaned or cleaned in {"+", "-", "."}:
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        parsed = float(cleaned)
    except ValueError:
        return None
    return -parsed if negative else parsed


def _integer(value: Any) -> int | None:
    parsed = _number(value)
    return int(parsed) if parsed is not None else None


def _text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return " ".join(str(value).split())


def _month_end(title: str) -> str | None:
    match = re.search(r"month\s+of\s+([A-Za-z]+)\s+(20\d{2})", title, re.I)
    if not match:
        return None
    try:
        parsed = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%B %Y")
    except ValueError:
        return None
    last_day = calendar.monthrange(parsed.year, parsed.month)[1]
    return parsed.replace(day=last_day).date().isoformat()


def parse_amfi_monthly_aum(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    """Parse the official AMFI monthly consolidated AUM workbook."""
    try:
        import pandas as pd

        sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, header=None)
    except Exception as exc:  # noqa: BLE001
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary=f"AMFI monthly AUM workbook unreadable: {exc}",
            output={"rows": [], "scope": "AGGREGATE_DELAYED_MUTUAL_FUND_CONTEXT"},
            error=str(exc),
        )

    rows: list[dict[str, Any]] = []
    report_date: str | None = None
    source_rows = 0
    for sheet_name, frame in sheets.items():
        if frame.empty:
            continue
        for value in frame.iloc[:10].to_numpy().ravel().tolist():
            candidate = _month_end(_text(value))
            if candidate:
                report_date = max(report_date or candidate, candidate)
        header_index = None
        for index in range(min(20, len(frame))):
            header = [_text(value).casefold() for value in frame.iloc[index].tolist()]
            if any("scheme name" in value for value in header) and any(
                "net assets under management" in value for value in header
            ):
                header_index = index
                break
        if header_index is None:
            continue
        header = [_text(value).casefold() for value in frame.iloc[header_index].tolist()]

        def column(predicate: Any) -> int | None:
            return next((i for i, value in enumerate(header) if predicate(value)), None)

        name_i = column(lambda value: "scheme name" in value)
        schemes_i = column(lambda value: "no. of schemes" in value)
        folios_i = column(lambda value: "no. of folios" in value)
        mobilized_i = column(lambda value: "funds mobilized" in value)
        redemption_i = column(
            lambda value: "repurchase" in value or "redemption" in value
        )
        inflow_i = column(lambda value: "net inflow" in value or "outflow" in value)
        closing_i = column(
            lambda value: value.startswith("net assets under management as on")
            and "segregated" not in value
        )
        average_i = column(lambda value: value.startswith("average net assets"))
        if name_i is None or schemes_i is None or closing_i is None:
            continue
        for row_index in range(header_index + 1, len(frame)):
            raw = frame.iloc[row_index].tolist()
            source_rows += 1
            name = _text(raw[name_i] if name_i < len(raw) else None)
            scheme_count = _integer(raw[schemes_i] if schemes_i < len(raw) else None)
            closing_aum = _number(raw[closing_i] if closing_i < len(raw) else None)
            if not name or scheme_count is None or closing_aum is None:
                continue

            def at(index: int | None) -> Any:
                return raw[index] if index is not None and index < len(raw) else None

            rows.append(
                {
                    "reportDate": report_date,
                    "schemeCategory": name,
                    "numberOfSchemes": scheme_count,
                    "numberOfFolios": _integer(at(folios_i)),
                    "fundsMobilizedCr": _number(at(mobilized_i)),
                    "redemptionCr": _number(at(redemption_i)),
                    "netInflowCr": _number(at(inflow_i)),
                    "closingAumCr": closing_aum,
                    "averageAumCr": _number(at(average_i)),
                    "sheet": str(sheet_name),
                    "sourceRow": row_index + 1,
                    "scope": "AGGREGATE_DELAYED_MUTUAL_FUND_CONTEXT",
                }
            )
    if not rows or report_date is None:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=report_date,
            record_count=0,
            summary="AMFI monthly AUM workbook had no schema-valid category rows.",
            output={"rows": [], "scope": "AGGREGATE_DELAYED_MUTUAL_FUND_CONTEXT"},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=report_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} AMFI monthly AUM category rows.",
        output={
            "rows": rows,
            "records": rows,
            "sourceRowCount": source_rows,
            "scope": "AGGREGATE_DELAYED_MUTUAL_FUND_CONTEXT",
            "canProveLiveFundBuying": False,
        },
    )


def _html_tables(content: bytes | str) -> list[list[list[str]]]:
    parser = _Tables()
    parser.feed(content if isinstance(content, str) else decode_bytes(content))
    return parser.tables


def parse_tradingeconomics_bdi(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    """Parse the current Baltic Dry Index row from the approved third-party page."""
    text = decode_bytes(content)
    iso_dates = re.findall(r"20\d{2}-[01]\d-[0-3]\d", text)
    data_date = max(iso_dates) if iso_dates else None
    bdi_row = next(
        (
            row
            for table in _html_tables(text)
            for row in table
            if row and row[0].strip().casefold() == "baltic dry"
        ),
        None,
    )
    if not bdi_row or len(bdi_row) < 6:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="TradingEconomics page had no populated Baltic Dry row.",
            output={"rows": [], "scope": "MARKET_REGIME_ONLY"},
        )
    numeric_cells = [(index, _number(value)) for index, value in enumerate(bdi_row[1:], 1)]
    numeric_cells = [(index, value) for index, value in numeric_cells if value is not None]
    if not numeric_cells:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary="TradingEconomics Baltic Dry row contained no numeric value.",
            output={"rows": []},
        )
    price = numeric_cells[0][1]
    first_percentage_index = next(
        (index for index, value in enumerate(bdi_row) if "%" in value),
        len(bdi_row),
    )
    pre_percentage_numbers = [
        _number(value) for value in bdi_row[2:first_percentage_index]
    ]
    pre_percentage_numbers = [
        value for value in pre_percentage_numbers if value is not None
    ]
    daily_change = pre_percentage_numbers[-1] if pre_percentage_numbers else None
    previous_value = price - daily_change if daily_change is not None else None
    percentages = [_number(value) for value in bdi_row if "%" in value]
    percentages = [value for value in percentages if value is not None]
    record = {
        "series": "BALTIC_DRY_INDEX",
        "value": price,
        "previousValue": previous_value,
        "dailyChange": daily_change,
        "dailyChangePct": percentages[0] if percentages else None,
        "monthChangePct": percentages[1] if len(percentages) > 1 else None,
        "yearChangePct": percentages[2] if len(percentages) > 2 else None,
        "observationLabel": bdi_row[-1],
        "dataDate": data_date,
        "unit": "points",
        "sourceTrust": "THIRD_PARTY_APPROVED",
        "scope": "MARKET_REGIME_ONLY",
    }
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=1,
        summary="Parsed current TradingEconomics Baltic Dry Index observation.",
        output={
            "rows": [record],
            "records": [record],
            "scope": "MARKET_REGIME_ONLY",
            "canProveStockDirection": False,
        },
    )


def parse_yahoo_bdry_proxy(content: bytes, **kwargs: Any) -> dict[str, Any]:
    """Parse BDRY bars and label them as a proxy, never as the official BDI."""
    parsed = parse_yahoo_chart(content, **kwargs)
    if parsed.get("parser_state") != "PARSED_STRUCTURED":
        return parsed
    rows = (parsed.get("output") or {}).get("rows") or []
    rows = [row for row in rows if str(row.get("symbol") or "").upper() == "BDRY"]
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=parsed.get("data_date"),
            record_count=0,
            summary="Yahoo response had no populated BDRY bars.",
            output={"rows": []},
        )
    for row in rows:
        row.update(
            {
                "proxyMetric": "DRY_BULK_SHIPPING_ETF_SENTIMENT",
                "officialBalticDryIndex": False,
                "sourceTrust": "THIRD_PARTY_PROXY",
                "scope": "MARKET_REGIME_ONLY",
            }
        )
    timestamps = [int(row["timestamp"]) for row in rows if row.get("timestamp")]
    data_date = (
        datetime.fromtimestamp(max(timestamps), tz=timezone.utc).date().isoformat()
        if timestamps
        else parsed.get("data_date")
    )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} Yahoo BDRY proxy bars (not official BDI).",
        output={
            "rows": rows,
            "records": rows,
            "scope": "MARKET_REGIME_ONLY",
            "officialBalticDryIndex": False,
        },
    )


def _traffic_lower_bound(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"([0-9,.]+)\s*([KMB])?", value.upper())
    if not match:
        return None
    base = float(match.group(1).replace(",", ""))
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(
        match.group(2) or "", 1
    )
    return int(base * multiplier)


def parse_google_trends_india_rss(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    """Parse official Google Trends India RSS current items."""
    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(content)
    except Exception as exc:  # noqa: BLE001
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary=f"Google Trends RSS XML invalid: {exc}",
            output={"rows": []},
            error=str(exc),
        )
    if root.tag.rsplit("}", 1)[-1].casefold() != "rss" or root.find("./channel") is None:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Google Trends response was valid XML but not an RSS channel.",
            output={"rows": []},
        )
    rows: list[dict[str, Any]] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        pub_raw = (item.findtext("pubDate") or "").strip()
        published_at = None
        if pub_raw:
            try:
                published_at = parsedate_to_datetime(pub_raw).astimezone(timezone.utc).isoformat()
            except (TypeError, ValueError):
                published_at = None
        traffic = next(
            (
                (child.text or "").strip()
                for child in list(item)
                if child.tag.endswith("approx_traffic")
            ),
            None,
        )
        rows.append(
            {
                "title": title,
                "link": (item.findtext("link") or "").strip(),
                "publishedAt": published_at,
                "approxTraffic": traffic,
                "approxTrafficLowerBound": _traffic_lower_bound(traffic),
                "geo": "IN",
                "source": "google_trends_rss",
                "scope": "AGGREGATE_CURRENT_TRENDS_CONTEXT",
            }
        )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="Google Trends India RSS contained no titled items.",
            output={"rows": []},
        )
    dates = [row["publishedAt"][:10] for row in rows if row.get("publishedAt")]
    data_date = max(dates) if dates else None
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} official Google Trends India RSS items.",
        output={
            "rows": rows,
            "records": rows,
            "scope": "AGGREGATE_CURRENT_TRENDS_CONTEXT",
            "isKeywordInterestHistory": False,
        },
    )


def _parse_westmetall_page(html: str, metal: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for table in _html_tables(html):
        if not table or len(table[0]) < 4:
            continue
        header = " ".join(table[0]).casefold()
        if "stock" not in header or "3-month" not in header:
            continue
        for row in table[1:]:
            if len(row) < 4:
                continue
            try:
                data_date = datetime.strptime(row[0], "%d. %B %Y").date().isoformat()
            except ValueError:
                continue
            cash = _number(row[1])
            three_month = _number(row[2])
            stock = _number(row[3])
            if cash is None or stock is None:
                continue
            records.append(
                {
                    "dataDate": data_date,
                    "metal": metal.upper(),
                    "cashSettlement": cash,
                    "threeMonthPrice": three_month,
                    "warehouseStockTonnes": stock,
                    "sourceTrust": "THIRD_PARTY_MIRROR",
                    "officialLmeArtifact": False,
                    "scope": "COMMODITY_CONTEXT_ONLY",
                }
            )
    return records


def parse_westmetall_lme(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    """Parse one or the six-session-aggregated Westmetall LME tables."""
    pages: list[tuple[str, str]] = []
    try:
        payload = json.loads(decode_bytes(content))
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("pages"), list):
        for page in payload["pages"]:
            if isinstance(page, dict) and page.get("html") and page.get("metal"):
                pages.append((str(page["metal"]), str(page["html"])))
    else:
        pages.append(("COPPER", decode_bytes(content)))
    rows = [
        row
        for metal, html in pages
        for row in _parse_westmetall_page(html, metal)
    ]
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="Westmetall response had no populated LME stock rows.",
            output={"rows": []},
        )
    data_date = max(row["dataDate"] for row in rows)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} Westmetall LME price/warehouse rows.",
        output={
            "rows": rows,
            "records": rows,
            "scope": "COMMODITY_CONTEXT_ONLY",
            "sourceTrust": "THIRD_PARTY_MIRROR",
            "officialLmeArtifact": False,
        },
    )
