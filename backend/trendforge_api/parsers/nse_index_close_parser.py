from __future__ import annotations

from typing import Any

from .common import (
    compact_key,
    find_value,
    parse_date_value,
    parse_float,
    parse_int,
    rows_from_content,
    source_result,
)


INDEX_CLOSE_SCHEMA_ID = "nse_all_indices_close_v1"

# Keys that are unambiguously percentages. The bare word "change" (and
# "variation") is POINTS on NSE index files and must never land in a
# percent field - the 20.15-points-as-percent bug.
_PERCENT_KEYS = (
    "percentChange",
    "percent_change",
    "pChange",
    "pctChange",
    "per_change",
    "perchange",
    "percentageChange",
    "percentage_change",
)
_POINTS_KEYS = (
    "points_change",
    "pointsChange",
    "variation",
    "change",
)


def _opt_float(row: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    """Strict optional read: missing/empty stays None, never a 0.0 default."""
    value = find_value(row, keys)
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "-"}:
        return None
    try:
        return float(text.replace(",", "").replace("%", ""))
    except ValueError:
        return None


def _exact_float(row: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    """Exact compact-key read only. Substring fallback is forbidden here:
    bare 'change' must not steal a 'percent_change' column."""
    items = {compact_key(k): v for k, v in row.items() if k}
    for key in keys:
        value = items.get(compact_key(key))
        if value is None:
            continue
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "-"}:
            continue
        try:
            return float(text.replace(",", "").replace("%", ""))
        except ValueError:
            continue
    return None


def _honest_change_percent(
    row: dict[str, Any], close: float
) -> tuple[float | None, str, float | None]:
    """Return (changePercent, status, pointsChange) with fail-closed honesty."""
    claimed = _opt_float(row, _PERCENT_KEYS)
    points = _exact_float(row, _POINTS_KEYS)
    previous = _opt_float(row, ("previous_close", "previousClose", "prev_close"))
    if previous is not None and previous <= 0:
        previous = None

    # Corroborated recompute first: it beats any unverified claim.
    recompute_source = None
    recomputed: float | None = None
    if previous is not None and previous > 0:
        candidate = (close - previous) / previous * 100.0
        if abs(candidate) <= 30.0:
            recomputed = round(candidate, 6)
            recompute_source = "RECOMPUTED_FROM_PREVIOUS_CLOSE"
    if recomputed is None and points is not None:
        prior = close - points
        if prior > 0:
            candidate = (close - prior) / prior * 100.0
            if abs(candidate) <= 30.0:
                recomputed = round(candidate, 6)
                recompute_source = "RECOMPUTED_FROM_POINTS"

    if claimed is not None:
        # Small claims are plausible official percents.
        if abs(claimed) <= 5.0:
            # But a large points move beside a tiny percent is contradictory;
            # trust the recompute when they disagree badly.
            if (
                recomputed is not None
                and abs(claimed - recomputed) > 2.0
                and points is not None
                and abs(points) > 5.0 * max(abs(claimed), 0.1)
            ):
                return recomputed, recompute_source, points
            return round(claimed, 6), "OFFICIAL_PERCENT_KEY", points
        # Large claims need corroboration before they are trusted at all.
        if recomputed is not None and abs(claimed - recomputed) < 0.5:
            return round(claimed, 6), "OFFICIAL_PERCENT_KEY", points
        if points is not None and abs(abs(claimed) - abs(points)) < 1.0:
            pass  # points mislabelled as percent -> use the recompute below
        elif abs(claimed) <= 20.0:
            return (
                round(claimed, 6),
                "OFFICIAL_PERCENT_KEY_UNCORROBORATED",
                points,
            )

    if recomputed is not None:
        return recomputed, recompute_source, points

    return None, "INDEX_PCT_PARSE_REJECTED", points


def parse_nse_index_close(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    rows, source_name = rows_from_content(content)
    normalized: list[dict[str, Any]] = []
    dates: set[str] = set()
    for row in rows:
        index_name = (find_value(row, ("index_name",)) or "").strip().upper()
        index_date = parse_date_value(find_value(row, ("index_date",)))
        close = parse_float(find_value(row, ("closing_index_value", "close")))
        if not index_name or not index_date or close <= 0:
            continue
        dates.add(index_date)
        change_percent, percent_status, points = _honest_change_percent(row, close)
        previous = _opt_float(
            row, ("previous_close", "previousClose", "prev_close")
        )
        if previous is None and points is not None:
            previous = close - points
        normalized.append(
            {
                "indexName": index_name,
                "indexDate": index_date,
                "open": parse_float(find_value(row, ("open_index_value", "open"))),
                "high": parse_float(find_value(row, ("high_index_value", "high"))),
                "low": parse_float(find_value(row, ("low_index_value", "low"))),
                "close": close,
                "previousClose": previous,
                "pointsChange": points,
                "changePercent": change_percent,
                "changePercentStatus": percent_status,
                "volume": parse_int(find_value(row, ("volume",))),
                "turnoverCrore": parse_float(
                    find_value(row, ("turnover_rs_cr", "turnover"))
                ),
                "scope": "NSE_INDEX_EOD",
            }
        )
    if not normalized or len(dates) != 1:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE"
            if not normalized
            else "WAIT_SCHEMA_MISMATCH",
            data_date=next(iter(dates), None),
            record_count=0,
            summary="NSE all-indices close file lacks one coherent dated set of index rows.",
            output={"scope": "NSE_INDEX_EOD", "sourceName": source_name},
        )
    names = {row["indexName"] for row in normalized}
    if "NIFTY 50" not in names or "INDIA VIX" not in names:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=next(iter(dates)),
            record_count=0,
            summary="NSE index file is missing mandatory NIFTY 50 or INDIA VIX rows.",
            output={"scope": "NSE_INDEX_EOD", "availableIndices": sorted(names)},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=next(iter(dates)),
        record_count=len(normalized),
        summary=f"Official NSE all-indices close rows parsed from {source_name}.",
        output={"scope": "NSE_INDEX_EOD", "rows": normalized},
    )

