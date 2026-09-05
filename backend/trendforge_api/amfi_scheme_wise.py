from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urlencode


AMFI_SCHEME_API = "https://www.amfiindia.com/api/schemewisedisclosure-investment"
REQUIRED_ROW_FIELDS = {
    "MF_ID",
    "Scheme_ID",
    "Scheme_Name",
    "ISIN",
    "Company_Name",
    "Security_Type",
    "MarketValue",
    "MarketValuePercentage",
    "QuarterDate",
    "QuarterName",
}


@dataclass(frozen=True)
class AmfiDirectory:
    funds: tuple[dict[str, Any], ...]
    quarters: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class AmfiFetchAttempt:
    url: str
    result_state: str
    status_code: int | None
    content_type: str | None
    content_length: int | None
    error: str | None = None


Fetch = Callable[[str, int], tuple[int, dict[str, str], bytes]]


def _unescape_next_data(content: bytes) -> str:
    text = content.decode("utf-8", errors="replace")
    return text.replace('\\"', '"').replace("\\u0026", "&")


def parse_amfi_scheme_directory(content: bytes) -> AmfiDirectory:
    """Extract the official AMFI fund directory and quarter list from Next data."""
    text = _unescape_next_data(content)
    funds = {
        int(mf_id): {"mfId": int(mf_id), "mfName": name.strip()}
        for mf_id, name in re.findall(r'"mf_id":"(\d+)"\s*,\s*"mf_name":"(.*?)"', text)
        if name.strip()
    }
    quarters = {
        quarter_date[:10]: {
            "quarterDate": quarter_date[:10],
            "quarterName": quarter_name.strip(),
        }
        for quarter_date, quarter_name in re.findall(
            r'"QuarterDate":"([^"]+)"\s*,\s*"QuarterName":"([^"]+)"', text
        )
        if quarter_name.strip()
    }
    if not funds or not quarters:
        raise ValueError("AMFI scheme directory is missing funds or quarters.")
    return AmfiDirectory(
        funds=tuple(funds[key] for key in sorted(funds)),
        quarters=tuple(quarters[key] for key in sorted(quarters, reverse=True)),
    )


def _api_date(quarter_date: str) -> str:
    return datetime.strptime(quarter_date, "%Y-%m-%d").strftime("%d-%b-%Y")


def _api_url(mf_id: int, quarter_date: str) -> str:
    return f"{AMFI_SCHEME_API}?{urlencode({'MF_ID': mf_id, 'strMonth': _api_date(quarter_date)})}"


def _fetch_fund(
    fund: dict[str, Any],
    quarter: dict[str, str],
    fetcher: Fetch,
    timeout_seconds: int,
) -> tuple[dict[str, Any], AmfiFetchAttempt]:
    url = _api_url(int(fund["mfId"]), quarter["quarterDate"])
    error: str | None
    try:
        status, headers, content = fetcher(url, timeout_seconds)
    except HTTPError as exc:
        status = exc.code
        headers = {key.lower(): value for key, value in exc.headers.items()}
        content = exc.read()
    except Exception as exc:
        return (
            {**fund, "url": url, "state": "FETCH_ERROR", "rows": []},
            AmfiFetchAttempt(url, "FETCH_ERROR", None, None, None, str(exc)),
        )

    content_type = headers.get("content-type") or headers.get("Content-Type")
    no_data_body = content.strip().lower()
    is_json_no_data = no_data_body.startswith(b"{") and (
        b'"message"' in no_data_body
        and (b'"nil"' in no_data_body or b"no data found" in no_data_body)
    )
    if status in {200, 404} and is_json_no_data:
        return (
            {**fund, "url": url, "state": "NO_DATA", "rows": []},
            AmfiFetchAttempt(url, "NO_DATA", status, content_type, len(content)),
        )
    if status >= 400:
        return (
            {**fund, "url": url, "state": "HTTP_ERROR", "rows": []},
            AmfiFetchAttempt(
                url, "HTTP_ERROR", status, content_type, len(content), f"HTTP {status}"
            ),
        )
    try:
        rows = json.loads(content)
    except json.JSONDecodeError as exc:
        rows = None
        error = f"Invalid JSON: {exc}"
    else:
        error = None
    if not isinstance(rows, list):
        return (
            {**fund, "url": url, "state": "SCHEMA_MISMATCH", "rows": []},
            AmfiFetchAttempt(
                url, "SCHEMA_MISMATCH", status, content_type, len(content), error
            ),
        )
    if rows and any(
        not isinstance(row, dict) or not REQUIRED_ROW_FIELDS.issubset(row)
        for row in rows
    ):
        return (
            {**fund, "url": url, "state": "SCHEMA_MISMATCH", "rows": []},
            AmfiFetchAttempt(
                url,
                "SCHEMA_MISMATCH",
                status,
                content_type,
                len(content),
                "One or more AMFI records are missing required fields.",
            ),
        )
    state = "OK" if rows else "NO_DATA"
    return (
        {
            **fund,
            "url": url,
            "state": state,
            "contentSha256": hashlib.sha256(content).hexdigest(),
            "rows": rows,
        },
        AmfiFetchAttempt(url, state, status, content_type, len(content)),
    )


def _select_latest_populated_quarter(
    directory: AmfiDirectory, fetcher: Fetch, timeout_seconds: int
) -> tuple[
    dict[str, str],
    dict[int, tuple[dict[str, Any], AmfiFetchAttempt]],
    list[AmfiFetchAttempt],
]:
    funds_by_id = {int(item["mfId"]): item for item in directory.funds}
    preferred = [funds_by_id[key] for key in (28, 22, 9) if key in funds_by_id]
    probes = preferred or list(directory.funds[:3])
    all_attempts: list[AmfiFetchAttempt] = []
    for quarter in directory.quarters:
        cache: dict[int, tuple[dict[str, Any], AmfiFetchAttempt]] = {}
        for fund in probes:
            result = _fetch_fund(fund, quarter, fetcher, timeout_seconds)
            all_attempts.append(result[1])
            cache[int(fund["mfId"])] = result
            if result[0]["state"] == "OK" and result[0]["rows"]:
                return quarter, cache, all_attempts
        if any(item[0]["state"] not in {"NO_DATA"} for item in cache.values()):
            raise RuntimeError(
                f"AMFI quarter probe failed for {quarter['quarterName']}; refusing fallback."
            )
    raise RuntimeError(
        "AMFI directory contains no populated quarter in the published list."
    )


def build_amfi_scheme_bundle(
    directory_content: bytes,
    *,
    fetcher: Fetch,
    timeout_seconds: int,
    max_workers: int = 4,
) -> tuple[bytes, tuple[AmfiFetchAttempt, ...]]:
    """Build one auditable bundle from the official AMFI per-fund API."""
    directory = parse_amfi_scheme_directory(directory_content)
    quarter, cache, attempts = _select_latest_populated_quarter(
        directory, fetcher, timeout_seconds
    )
    responses: dict[int, dict[str, Any]] = {
        key: value[0] for key, value in cache.items()
    }
    remaining = [fund for fund in directory.funds if int(fund["mfId"]) not in responses]
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, 4))) as executor:
        futures = {
            executor.submit(_fetch_fund, fund, quarter, fetcher, timeout_seconds): int(
                fund["mfId"]
            )
            for fund in remaining
        }
        for future in as_completed(futures):
            response, attempt = future.result()
            responses[futures[future]] = response
            attempts.append(attempt)

    ordered = [responses[int(fund["mfId"])] for fund in directory.funds]
    successful = sum(item["state"] == "OK" for item in ordered)
    no_data = sum(item["state"] == "NO_DATA" for item in ordered)
    failed = len(ordered) - successful - no_data
    total_rows = sum(len(item.get("rows", [])) for item in ordered)
    coverage_state = "COMPLETE" if failed == 0 else "PARTIAL"
    payload = {
        "datasetKind": "AMFI_SCHEME_WISE_QUARTERLY_EXPOSURE",
        "sourcePageUrl": "https://www.amfiindia.com/otherdata/scheme-wise-disclosure",
        "sourcePageSha256": hashlib.sha256(directory_content).hexdigest(),
        "quarterDate": quarter["quarterDate"],
        "quarterName": quarter["quarterName"],
        "coverage": {
            "state": coverage_state,
            "requestedFunds": len(ordered),
            "successfulFunds": successful,
            "noDataFunds": no_data,
            "failedFunds": failed,
            "totalRows": total_rows,
        },
        "responses": ordered,
    }
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode(),
        tuple(attempts),
    )
