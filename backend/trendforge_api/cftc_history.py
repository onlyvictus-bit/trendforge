from __future__ import annotations

import io
import zipfile
from datetime import date
from pathlib import PurePosixPath
from typing import Callable

from . import storage
from .source_monitor import build_source_snapshot, get_source_descriptor
from .source_parser import parse_source
from .source_resolver import fetch_url


MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
FetchFunction = Callable[[str, int], tuple[int, dict[str, str], bytes]]


def official_cftc_history_urls(years: int, *, today: date | None = None) -> list[str]:
    current_year = (today or date.today()).year
    first_year = current_year - years + 1
    return [
        f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"
        for year in range(first_year, current_year + 1)
    ]


def _validate_archive(content: bytes) -> str | None:
    if not content or len(content) > MAX_ARCHIVE_BYTES:
        return "Archive is empty or exceeds the compressed size limit."
    stream = io.BytesIO(content)
    if not zipfile.is_zipfile(stream):
        return "Response is not a valid ZIP archive."
    with zipfile.ZipFile(stream) as archive:
        members = archive.infolist()
        if not members or len(members) > 20:
            return "Archive has an invalid member count."
        if sum(member.file_size for member in members) > MAX_UNCOMPRESSED_BYTES:
            return "Archive exceeds the uncompressed size limit."
        for member in members:
            path = PurePosixPath(member.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                return "Archive contains an unsafe path."
            if not member.is_dir() and path.suffix.lower() not in {".txt", ".csv"}:
                return "Archive contains an unexpected file type."
    return None


def import_cftc_history(
    *,
    years: int,
    fetch: bool,
    fetcher: FetchFunction = fetch_url,
) -> dict:
    urls = official_cftc_history_urls(years)
    if not fetch:
        return {"state": "WAIT_FETCH_REQUIRED", "urls": urls, "results": []}
    descriptor = get_source_descriptor("cftc_cot")
    if descriptor is None:
        return {
            "state": "BROKEN",
            "urls": urls,
            "results": [],
            "error": "CFTC source descriptor is missing.",
        }

    results = []
    for url in urls:
        try:
            status, headers, content = fetcher(url, 30)
            error = _validate_archive(content) if status < 400 else f"HTTP {status}"
            snapshot = build_source_snapshot(
                descriptor,
                status_code=status,
                content=content if error is None else None,
                headers=headers,
                error=error,
                resolved_url=url,
            )
            storage.save_source_snapshot(snapshot)
            parsed = parse_source("cftc_cot") if error is None else None
            results.append(
                {
                    "url": url,
                    "state": parsed.parser_state if parsed else "BROKEN",
                    "dataDate": parsed.data_date if parsed else None,
                    "recordCount": parsed.record_count if parsed else 0,
                    "error": error,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "url": url,
                    "state": "BROKEN",
                    "dataDate": None,
                    "recordCount": 0,
                    "error": str(exc),
                }
            )
    completed = sum(row["state"] == "PARSED_STRUCTURED" for row in results)
    state = (
        "COMPLETE" if completed == len(urls) else "PARTIAL" if completed else "BROKEN"
    )
    return {"state": state, "urls": urls, "results": results}
