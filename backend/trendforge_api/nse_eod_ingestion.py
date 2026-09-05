from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Any
from urllib.error import HTTPError, URLError

from pydantic import BaseModel, Field

from .models import SourceParseResult
from .source_monitor import build_source_snapshot, get_source_descriptor
from .source_parser import parse_source_content
from .source_resolver import direct_download_candidates, fetch_url
from .storage import save_source_parse_result, save_source_snapshot


class NSEEODBackfillResult(BaseModel):
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    attempted_dates: int = Field(alias="attemptedDates")
    fetched_artifacts: int = Field(alias="fetchedArtifacts")
    structured_artifacts: int = Field(alias="structuredArtifacts")
    missing_artifacts: int = Field(alias="missingArtifacts")
    failed_artifacts: int = Field(alias="failedArtifacts")
    source_results: list[dict[str, Any]] = Field(alias="sourceResults")

    model_config = {"populate_by_name": True}


def _artifact_url(source_key: str, trade_date: date) -> str:
    candidates = direct_download_candidates(source_key, today=trade_date)
    if not candidates:
        raise ValueError(f"No direct archive contract for {source_key}.")
    return candidates[0]


def _fetch_artifact(
    source_key: str, trade_date: date, timeout_seconds: int
) -> dict[str, Any]:
    url = _artifact_url(source_key, trade_date)
    try:
        status, headers, content = fetch_url(url, timeout_seconds)
        if status >= 400 or not content:
            return {
                "state": "MISSING",
                "sourceKey": source_key,
                "date": trade_date,
                "url": url,
            }
        return {
            "state": "FETCHED",
            "sourceKey": source_key,
            "date": trade_date,
            "url": url,
            "status": status,
            "headers": headers,
            "content": content,
        }
    except HTTPError as exc:
        return {
            "state": "MISSING" if exc.code == 404 else "FAILED",
            "sourceKey": source_key,
            "date": trade_date,
            "url": url,
            "error": f"HTTP {exc.code}: {exc.reason}",
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "state": "FAILED",
            "sourceKey": source_key,
            "date": trade_date,
            "url": url,
            "error": str(exc),
        }


def _persist_fetched_artifact(item: dict[str, Any]) -> dict[str, Any]:
    source_key = str(item["sourceKey"])
    descriptor = get_source_descriptor(source_key)
    if descriptor is None:
        raise ValueError(f"Unknown source descriptor: {source_key}")
    snapshot = save_source_snapshot(
        build_source_snapshot(
            descriptor,
            status_code=int(item["status"]),
            content=item["content"],
            headers=item["headers"],
            resolved_url=str(item["url"]),
        )
    )
    parsed = parse_source_content(
        source_key,
        item["content"],
        url=str(item["url"]),
        last_modified=item["headers"].get("last-modified") or snapshot.checked_at,
        response_headers=item["headers"],
    )
    saved = save_source_parse_result(
        SourceParseResult.model_validate(
            {
                **parsed.model_dump(mode="json", by_alias=True),
                "snapshotId": snapshot.id,
            }
        )
    )
    return {
        "sourceKey": source_key,
        "date": item["date"].isoformat(),
        "snapshotId": snapshot.id,
        "parseId": saved.id,
        "parserState": saved.parser_state,
        "recordCount": saved.record_count,
        "contentHash": snapshot.content_hash,
    }


def ingest_nse_eod_date(
    trade_date: date, *, include_cash: bool = True, timeout_seconds: int = 20
) -> list[dict[str, Any]]:
    keys = ["nse_index_close_eod"]
    if include_cash:
        keys.append("nse_bhavcopy_eod")
    results: list[dict[str, Any]] = []
    for key in keys:
        fetched = _fetch_artifact(key, trade_date, timeout_seconds)
        if fetched["state"] == "FETCHED":
            results.append(_persist_fetched_artifact(fetched))
        else:
            results.append(
                {
                    "sourceKey": key,
                    "date": trade_date.isoformat(),
                    "parserState": fetched["state"],
                    "recordCount": 0,
                    "error": fetched.get("error"),
                }
            )
    return results


def backfill_nse_eod(
    start_date: date,
    end_date: date,
    *,
    include_cash_history: bool = False,
    timeout_seconds: int = 20,
    max_workers: int = 6,
) -> NSEEODBackfillResult:
    if end_date < start_date:
        raise ValueError("end_date must not precede start_date")
    calendar_days = (end_date - start_date).days + 1
    if calendar_days > 370:
        raise ValueError("backfill range cannot exceed 370 calendar days")
    weekdays = [
        start_date + timedelta(days=offset)
        for offset in range(calendar_days)
        if (start_date + timedelta(days=offset)).weekday() < 5
    ]
    jobs = [("nse_index_close_eod", item) for item in weekdays]
    if include_cash_history:
        jobs.extend(("nse_bhavcopy_eod", item) for item in weekdays)
    elif weekdays:
        jobs.append(("nse_bhavcopy_eod", weekdays[-1]))

    fetched_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, 8))) as executor:
        futures = {
            executor.submit(_fetch_artifact, key, item, timeout_seconds): (key, item)
            for key, item in jobs
        }
        for future in as_completed(futures):
            fetched_results.append(future.result())

    persisted: list[dict[str, Any]] = []
    fetched_count = structured_count = missing_count = failed_count = 0
    for item in sorted(
        fetched_results, key=lambda row: (row["date"], row["sourceKey"])
    ):
        if item["state"] == "FETCHED":
            fetched_count += 1
            saved = _persist_fetched_artifact(item)
            structured_count += saved["parserState"] == "PARSED_STRUCTURED"
            persisted.append(saved)
        elif item["state"] == "MISSING":
            missing_count += 1
        else:
            failed_count += 1
            persisted.append(
                {
                    "sourceKey": item["sourceKey"],
                    "date": item["date"].isoformat(),
                    "parserState": item["state"],
                    "recordCount": 0,
                    "error": item.get("error"),
                }
            )
    return NSEEODBackfillResult(
        startDate=start_date,
        endDate=end_date,
        attemptedDates=len(weekdays),
        fetchedArtifacts=fetched_count,
        structuredArtifacts=structured_count,
        missingArtifacts=missing_count,
        failedArtifacts=failed_count,
        sourceResults=persisted,
    )
