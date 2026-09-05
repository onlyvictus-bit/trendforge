from __future__ import annotations

import json
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from typing import Any

from .common import source_result


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        normalized = tag.lower()
        if normalized == "tr":
            self._row = []
        elif normalized in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"td", "th"} and self._cell is not None:
            if self._row is not None:
                self._row.append(" ".join(self._cell).strip())
            self._cell = None
        elif normalized == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
            self._cell = None


def _schema(reason: str) -> dict[str, Any]:
    return source_result(
        parser_state="WAIT_SCHEMA_MISMATCH",
        data_date=None,
        record_count=0,
        summary=f"SGE daily report schema validation failed: {reason}",
        output={
            "scope": "CHINA_PHYSICAL_GOLD_DELAYED_CONTEXT",
            "qualityIssues": [reason],
            "rows": [],
        },
        error=reason,
    )


def _optional_number(value: str) -> float | None:
    normalized = value.strip().replace(",", "").replace("%", "")
    if normalized in {"", "-", "N/A", "NA"}:
        return None
    try:
        number = float(normalized)
    except ValueError:
        return None
    return number if number == number else None


def _optional_integer(value: str) -> int | None:
    number = _optional_number(value)
    if number is None:
        return None
    return int(round(number))


def _valid_date(value: str) -> str | None:
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        return None


def parse_sge_daily_report(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    scope = "CHINA_PHYSICAL_GOLD_DELAYED_CONTEXT"
    try:
        text = content.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        return _schema("response is not valid UTF-8 HTML")
    parser = _TableParser()
    try:
        parser.feed(text)
    except Exception as exc:
        return _schema(f"HTML parser failed with {type(exc).__name__}")

    flattened_headers = " ".join(
        cell for row in parser.rows for cell in row if _valid_date(cell) is None
    ).casefold()
    required_markers = ("contract", "open interest", "delivery volume")
    if not all(marker in flattened_headers for marker in required_markers):
        return _schema("required Date/Contract/OI/Delivery columns were not found")

    rows: list[dict[str, Any]] = []
    identities: set[tuple[str, str]] = set()
    for source_row in parser.rows:
        if not source_row:
            continue
        trade_date = _valid_date(source_row[0])
        if trade_date is None:
            continue
        if len(source_row) != 14:
            return _schema(
                f"dated row for {trade_date} has {len(source_row)} columns, expected 14"
            )
        contract = source_row[1].strip()
        if not contract:
            return _schema(f"dated row for {trade_date} has no contract")
        identity = (trade_date, contract.casefold())
        if identity in identities:
            return _schema(f"duplicate {contract} row for {trade_date}")
        identities.add(identity)
        rows.append(
            {
                "tradeDate": trade_date,
                "contract": contract,
                "open": _optional_number(source_row[2]),
                "high": _optional_number(source_row[3]),
                "low": _optional_number(source_row[4]),
                "close": _optional_number(source_row[5]),
                "change": _optional_number(source_row[6]),
                "changePercent": _optional_number(source_row[7]),
                "weightedAveragePrice": _optional_number(source_row[8]),
                "volumeKg": _optional_number(source_row[9]),
                "amountCny": _optional_number(source_row[10]),
                "openInterestLots": _optional_integer(source_row[11]),
                "direction": source_row[12].strip() or None,
                "deliveryVolumeLots": _optional_integer(source_row[13]),
            }
        )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="SGE daily report is connected but contains no dated contract rows.",
            output={"scope": scope, "noDataNow": True, "rows": []},
        )
    rows.sort(key=lambda row: (row["tradeDate"], row["contract"]))
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(row["tradeDate"] for row in rows),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} SGE daily gold-market contract rows.",
        output={
            "scope": scope,
            "currency": "CNY",
            "priceUnits": "CNY_PER_GRAM",
            "rows": rows,
        },
    )


def _sge_pair_rows(
    series_key: str, raw: Any, *, series_label: str
) -> list[dict[str, Any]]:
    """Convert SGE [[epoch_ms, value], ...] pairs into dict market rows."""
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        try:
            observed = datetime.fromtimestamp(float(item[0]) / 1000, tz=UTC).date()
            value = float(item[1])
        except (TypeError, ValueError, OSError, OverflowError):
            continue
        if value != value:  # NaN
            continue
        rows.append(
            {
                # Canonical TrendForge fields
                "tradeDate": observed.isoformat(),
                "series": series_key,
                "seriesLabel": series_label,
                "value": value,
                "currency": "CNY",
                "priceUnits": "CNY_PER_GRAM",
                "instrument": "SGE_BENCHMARK_GOLD",
                # Required normalized aliases for screener consumers
                "date": observed.isoformat(),
                "benchmark_value": value,
                "source": "sge_benchmark_gold",
            }
        )
    rows.sort(key=lambda row: row["tradeDate"])
    return rows


def parse_sge_benchmark_gold(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    """Parse Shanghai Gold Exchange AM/PM benchmark history (zp/wp series).

    Official DayilyJzj payload shape:
      {"zp": [[ms, price], ...], "wp": [[ms, price], ...]}
    These are real macro gold price observations, not HTML landing metadata.
    """
    scope = "CHINA_PHYSICAL_GOLD_DELAYED_CONTEXT"
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _schema("SGE benchmark response is not valid JSON")
    if not isinstance(payload, dict):
        return _schema("SGE benchmark response is not a JSON object")

    zp = _sge_pair_rows("zp", payload.get("zp"), series_label="AM_BENCHMARK")
    wp = _sge_pair_rows("wp", payload.get("wp"), series_label="PM_BENCHMARK")
    rows = zp + wp
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="SGE benchmark endpoint connected but has no zp/wp observations.",
            output={
                "endpointConnected": True,
                "noDataNow": True,
                "scope": scope,
                "rows": [],
            },
        )
    data_date = max(row["tradeDate"] for row in rows)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} SGE benchmark gold observations (zp={len(zp)}, wp={len(wp)}).",
        output={
            "endpointConnected": True,
            "noDataNow": False,
            "scope": scope,
            "currency": "CNY",
            "priceUnits": "CNY_PER_GRAM",
            "latestZp": zp[-1]["value"] if zp else None,
            "latestWp": wp[-1]["value"] if wp else None,
            "rows": rows,
        },
    )
