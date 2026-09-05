from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .common import source_result


def _schema(reason: str, scope: str) -> dict[str, Any]:
    return source_result(
        parser_state="WAIT_SCHEMA_MISMATCH",
        data_date=None,
        record_count=0,
        summary=f"World Gold Council schema validation failed: {reason}",
        output={"scope": scope, "qualityIssues": [reason], "rows": []},
        error=reason,
    )


def _iso_date(value: Any) -> str | None:
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return number


def _json_object(content: bytes) -> dict[str, Any] | None:
    try:
        payload = json.loads(content.decode("utf-8-sig", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def parse_wgc_gold_open_interest(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    scope = "GOLD_FUTURES_OI_DELAYED_CONTEXT"
    payload = _json_object(content)
    if payload is None:
        return _schema("response is not a JSON object", scope)
    chart = payload.get("chartData")
    if not isinstance(chart, dict):
        return _schema("chartData object is missing", scope)
    as_of_date = _iso_date(chart.get("asOfDate"))
    frequency = str(chart.get("periodicity") or "").strip().upper()
    series = chart.get("series")
    if as_of_date is None:
        return _schema("asOfDate is missing or invalid", scope)
    if frequency != "WEEKLY":
        return _schema(
            f"expected WEEKLY periodicity, got {frequency or 'missing'}", scope
        )
    if not isinstance(series, list) or not series:
        return _schema("series list is missing or empty", scope)

    rows: list[dict[str, Any]] = []
    identities: set[tuple[str, str]] = set()
    for series_index, item in enumerate(series):
        if not isinstance(item, dict):
            return _schema(f"series {series_index} is not an object", scope)
        venue = str(item.get("name") or "").strip()
        points = item.get("data")
        if not venue or not isinstance(points, list):
            return _schema(f"series {series_index} lacks name or data", scope)
        for point_index, point in enumerate(points):
            if not isinstance(point, list) or len(point) != 2:
                return _schema(
                    f"{venue} point {point_index} is not a date/value pair", scope
                )
            observation_date = _iso_date(point[0])
            value = _number(point[1])
            if observation_date is None or value is None:
                return _schema(
                    f"{venue} point {point_index} has invalid date or value", scope
                )
            identity = (venue.casefold(), observation_date)
            if identity in identities:
                return _schema(
                    f"duplicate observation for {venue} on {observation_date}", scope
                )
            identities.add(identity)
            rows.append(
                {
                    "venue": venue,
                    "observationDate": observation_date,
                    "openInterestUsdBn": value,
                    "frequency": frequency,
                    "units": "USD_BILLION",
                }
            )
    if not rows:
        return _schema("series contained no observations", scope)
    latest_observation = max(row["observationDate"] for row in rows)
    if latest_observation > as_of_date:
        return _schema("an observation is newer than chartData.asOfDate", scope)
    rows.sort(key=lambda row: (row["venue"].casefold(), row["observationDate"]))
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=as_of_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} WGC weekly gold futures OI observations.",
        output={
            "scope": scope,
            "frequency": frequency,
            "units": "USD_BILLION",
            "venueCount": len({row["venue"] for row in rows}),
            "rows": rows,
        },
    )


def _dataset_from_url(url: str | None) -> str | None:
    normalized = (url or "").lower()
    if "holdings-chart" in normalized:
        return "HOLDINGS"
    if "flows-chart" in normalized:
        return "FLOWS"
    return None


def _epoch_date(value: Any) -> str | None:
    number = _number(value)
    if number is None or number < 0:
        return None
    try:
        return datetime.fromtimestamp(number / 1000, tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _etf_row(
    *,
    dataset: str,
    observation_date: str,
    region: str,
    value: float,
    gold_price: float | None,
    derived: bool,
) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "period": "WEEKLY",
        "observationDate": observation_date,
        "region": region.upper().replace(" ", "_"),
        "value": value,
        "units": "TONNES",
        "goldPriceUsdOz": gold_price,
        "isDerived": derived,
    }


def _holdings_rows(weekly: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    tonnes = weekly.get("tonnes")
    columns = tonnes.get("columns") if isinstance(tonnes, dict) else None
    points = tonnes.get("set") if isinstance(tonnes, dict) else None
    expected = ["Date", "North America", "Europe", "Asia", "Other", "Gold, US$/oz"]
    if not isinstance(columns, list) or not isinstance(points, list):
        return [], "Weekly tonnes columns/set are missing"
    if columns != expected:
        return [], "Weekly tonnes columns do not match the expected WGC schema"
    rows: list[dict[str, Any]] = []
    seen_dates: set[str] = set()
    for point_index, point in enumerate(points):
        if not isinstance(point, list) or len(point) != len(expected):
            return [], f"weekly point {point_index} has an invalid width"
        observation_date = _epoch_date(point[0])
        if observation_date is None or observation_date in seen_dates:
            return [], f"weekly point {point_index} has invalid/duplicate timestamp"
        seen_dates.add(observation_date)
        gold_price = _number(point[-1])
        values = [
            (_number(value), region)
            for region, value in zip(expected[1:5], point[1:5], strict=True)
        ]
        numeric = [(value, region) for value, region in values if value is not None]
        rows.extend(
            _etf_row(
                dataset="HOLDINGS",
                observation_date=observation_date,
                region=region,
                value=value,
                gold_price=gold_price,
                derived=False,
            )
            for value, region in numeric
        )
        if numeric:
            rows.append(
                _etf_row(
                    dataset="HOLDINGS",
                    observation_date=observation_date,
                    region="WORLD_TOTAL",
                    value=round(sum(value for value, _ in numeric), 8),
                    gold_price=gold_price,
                    derived=True,
                )
            )
    return rows, None


def _flow_rows(weekly: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    series = weekly.get("series")
    tonnes_series = series.get("tonnes") if isinstance(series, dict) else None
    if not isinstance(tonnes_series, list) or not tonnes_series:
        return [], "Weekly flow tonnes series is missing or empty"
    by_date: dict[str, dict[str, float]] = {}
    gold_price_by_date: dict[str, float] = {}
    for series_index, item in enumerate(tonnes_series):
        if not isinstance(item, dict):
            return [], f"flow series {series_index} is not an object"
        region = str(item.get("name") or "").strip()
        points = item.get("data")
        if not region or not isinstance(points, list):
            return [], f"flow series {series_index} lacks name or data"
        is_gold_price = region.casefold().startswith("gold price")
        for point_index, point in enumerate(points):
            if not isinstance(point, list) or len(point) != 2:
                return [], f"{region} flow point {point_index} is not a date/value pair"
            observation_date = _epoch_date(point[0])
            value = _number(point[1])
            if observation_date is None or value is None:
                return [], f"{region} flow point {point_index} has invalid data"
            if is_gold_price:
                if observation_date in gold_price_by_date:
                    return [], f"duplicate gold price for {observation_date}"
                gold_price_by_date[observation_date] = value
                continue
            date_values = by_date.setdefault(observation_date, {})
            if region in date_values:
                return [], f"duplicate {region} flow for {observation_date}"
            date_values[region] = value
    rows: list[dict[str, Any]] = []
    for observation_date, values in sorted(by_date.items()):
        gold_price = gold_price_by_date.get(observation_date)
        rows.extend(
            _etf_row(
                dataset="FLOWS",
                observation_date=observation_date,
                region=region,
                value=value,
                gold_price=gold_price,
                derived=False,
            )
            for region, value in sorted(values.items())
        )
        rows.append(
            _etf_row(
                dataset="FLOWS",
                observation_date=observation_date,
                region="WORLD_TOTAL",
                value=round(sum(values.values()), 8),
                gold_price=gold_price,
                derived=True,
            )
        )
    return rows, None


def parse_wgc_gold_etf_series(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    scope = "GOLD_ETF_DELAYED_DEMAND_CONTEXT"
    dataset = _dataset_from_url(url)
    if dataset is None:
        return _schema("ETF endpoint does not identify holdings or flows", scope)
    payload = _json_object(content)
    if payload is None:
        return _schema("response is not a JSON object", scope)
    chart = payload.get("chartData")
    as_of_date = _iso_date(chart.get("asOfDate")) if isinstance(chart, dict) else None
    data = chart.get("data") if isinstance(chart, dict) else None
    weekly = data.get("Weekly") if isinstance(data, dict) else None
    if as_of_date is None:
        return _schema("chartData.asOfDate is missing or invalid", scope)
    if not isinstance(weekly, dict):
        return _schema("Weekly ETF data object is missing", scope)
    rows, error = (
        _holdings_rows(weekly) if dataset == "HOLDINGS" else _flow_rows(weekly)
    )
    if error:
        return _schema(error, scope)
    if not rows:
        return _schema("Weekly tonnes series contained no numeric observations", scope)
    latest_observation = max(row["observationDate"] for row in rows)
    if latest_observation > as_of_date:
        return _schema("an ETF observation is newer than chartData.asOfDate", scope)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=as_of_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} WGC weekly ETF {dataset.lower()} observations.",
        output={
            "scope": scope,
            "dataset": dataset,
            "period": "WEEKLY",
            "units": "TONNES",
            "rows": rows,
        },
    )
