from __future__ import annotations

import csv
import hashlib
import io
import ipaddress
import json
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from . import storage
from .source_registry_contracts import (
    RegistryUrlContract,
    classify_registry_urls,
    load_saved_link_inventory,
)
from .source_monitor import SOURCE_CATALOG
from .source_resolver import LinkExtractor, direct_download_candidates, request_headers
from .vyom_resolver import BrowserDiscovery, discover_links_with_vyom


DEFAULT_ARCHIVE_ROOT = storage.DATA_DIR / "raw_source_inventory"
DEFAULT_REPORT_ROOT = storage.DATA_DIR / "reports"
MAX_FETCH_IDS = 25
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
ARTIFACT_SUFFIXES = (".csv", ".json", ".txt", ".zip", ".xls", ".xlsx", ".xml")
ANTI_BOT_MARKERS = (
    b"cf-chl-captcha",
    b"cf-browser-verification",
    b"just a moment...",
    b"access denied",
    b"verify you are human",
)
IRRELEVANT_GLOBAL_ARTIFACT_MARKERS = (
    "list-of-fake-trading-apps",
    "service-providers.xls",
    "list-of-companies-databas",
)


@dataclass(frozen=True)
class AuditFetchResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes
    truncated: bool


class StructuredHTMLProfiler(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.table_count = 0
        self.table_row_count = 0
        self.table_headers: list[str] = []
        self.embedded_json_count = 0
        self._cell_tag: str | None = None
        self._cell_text: list[str] = []
        self._json_script = False
        self._script_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered == "table":
            self.table_count += 1
        elif lowered == "tr":
            self.table_row_count += 1
        elif lowered in {"th", "td"}:
            self._cell_tag, self._cell_text = lowered, []
        elif lowered == "script":
            values = {key.lower(): value for key, value in attrs if value}
            self._json_script = "json" in values.get("type", "").lower()
            self._script_text = []

    def handle_data(self, data: str) -> None:
        if self._cell_tag:
            self._cell_text.append(data)
        if self._json_script:
            self._script_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"th", "td"} and self._cell_tag == lowered:
            value = " ".join(" ".join(self._cell_text).split())
            if lowered == "th" and value and len(self.table_headers) < 100:
                self.table_headers.append(value)
            self._cell_tag, self._cell_text = None, []
        elif lowered == "script" and self._json_script:
            try:
                json.loads("".join(self._script_text))
                self.embedded_json_count += 1
            except json.JSONDecodeError:
                pass
            self._json_script, self._script_text = False, []


def canonicalize_inventory_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    path = parts.path.rstrip("/") or ""
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            urlencode(sorted(query_items)),
            "",
        )
    )


def inventory_manifest_hash(urls: list[str]) -> str:
    payload = "\n".join(f"{index}\0{url}" for index, url in enumerate(urls, 1))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def provisional_family_id(canonical_url: str) -> str:
    digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]
    return f"URLFAM-{digest}"


def fetch_inventory_url(
    url: str, timeout_seconds: int, max_bytes: int
) -> AuditFetchResponse:
    request = Request(url, headers=request_headers(url))
    try:
        response = urlopen(request, timeout=timeout_seconds)
    except HTTPError as exc:
        response = exc
    with response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        declared = headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            return AuditFetchResponse(int(response.status), headers, b"", True)
        content = response.read(max_bytes + 1)
        truncated = len(content) > max_bytes
        return AuditFetchResponse(
            int(getattr(response, "status", getattr(response, "code", 200))),
            headers,
            content[:max_bytes],
            truncated,
        )


def _is_html(content_type: str, content: bytes) -> bool:
    head = content[:1000].lstrip().lower()
    return "text/html" in content_type or head.startswith((b"<!doctype html", b"<html"))


def _looks_tabular(content: bytes) -> bool:
    text = content[:10000].decode("utf-8-sig", errors="replace")
    lines = [line for line in text.splitlines() if line.strip()][:3]
    if len(lines) < 2:
        return False
    return any(
        lines[0].count(delimiter) >= 1
        and lines[1].count(delimiter) == lines[0].count(delimiter)
        for delimiter in (",", "\t", "|")
    )


def _is_json(content: bytes) -> bool:
    try:
        json.loads(content.decode("utf-8-sig"))
        return True
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False


def _is_artifact_url(url: str) -> bool:
    path = urlsplit(url).path.lower()
    return path.endswith(ARTIFACT_SUFFIXES)


def _static_artifact_links(base_url: str, content: bytes) -> list[str]:
    extractor = LinkExtractor(base_url)
    try:
        extractor.feed(content.decode("utf-8", errors="replace"))
    except Exception:
        return []
    return list(
        dict.fromkeys(
            item["url"]
            for item in extractor.links
            if _is_artifact_url(item["url"])
            and not any(
                marker in item["url"].lower()
                for marker in IRRELEVANT_GLOBAL_ARTIFACT_MARKERS
            )
        )
    )


def _organization_domain(hostname: str) -> str:
    labels = hostname.lower().strip(".").split(".")
    if len(labels) < 2:
        return hostname.lower()
    compound_suffixes = {"co.in", "org.in", "gov.in", "com.cn", "gov.cn"}
    suffix = ".".join(labels[-2:])
    width = 3 if suffix in compound_suffixes and len(labels) >= 3 else 2
    return ".".join(labels[-width:])


def _safe_discovered_artifact_url(landing_url: str, candidate_url: str) -> bool:
    landing = urlsplit(landing_url)
    candidate = urlsplit(candidate_url)
    if candidate.scheme != "https" or not candidate.hostname:
        return False
    try:
        ipaddress.ip_address(candidate.hostname)
        return False
    except ValueError:
        pass
    if not landing.hostname or not _is_artifact_url(candidate_url):
        return False
    return _organization_domain(landing.hostname) == _organization_domain(
        candidate.hostname
    )


def _html_profile(content: bytes) -> dict[str, object]:
    profiler = StructuredHTMLProfiler()
    try:
        profiler.feed(content.decode("utf-8", errors="replace"))
    except Exception:
        return {"format": "HTML", "profileState": "PARSE_ERROR"}
    return {
        "format": "HTML",
        "tableCount": profiler.table_count,
        "tableRowCount": profiler.table_row_count,
        "tableHeaders": profiler.table_headers,
        "embeddedJsonCount": profiler.embedded_json_count,
    }


def _json_profile(content: bytes) -> dict[str, object]:
    payload = json.loads(content.decode("utf-8-sig"))
    records: list[object]
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = next(
            (
                value
                for key in ("data", "results", "records", "rows", "table")
                if isinstance((value := payload.get(key)), list)
            ),
            [payload],
        )
    else:
        records = [payload]
    field_names = sorted(
        {str(key) for item in records[:100] if isinstance(item, dict) for key in item}
    )
    return {
        "format": "JSON",
        "recordCount": len(records),
        "fieldNames": field_names,
        "topLevelType": type(payload).__name__,
    }


def _tabular_profile(content: bytes) -> dict[str, object]:
    text = content.decode("utf-8-sig", errors="replace")
    sample = text[:10000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    headers = [value.strip() for value in rows[0]] if rows else []
    return {
        "format": "TABULAR",
        "delimiter": delimiter,
        "recordCount": max(0, len(rows) - 1),
        "fieldNames": headers,
    }


def _zip_profile(content: bytes) -> tuple[dict[str, object], list[str]]:
    issues: list[str] = []
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()[:500]
    if any(".." in Path(name).parts or Path(name).is_absolute() for name in names):
        issues.append("ZIP_PATH_TRAVERSAL_MEMBER")
    return {
        "format": "ZIP",
        "memberCount": len(names),
        "members": names[:50],
    }, issues


def _profile_payload(
    state: str, response: AuditFetchResponse
) -> tuple[dict[str, object], list[str]]:
    content = response.content
    try:
        if state in {"HTML_METADATA_ONLY", "HTML_STRUCTURED_CANDIDATE"}:
            return _html_profile(content), []
        if state == "JSON_ARTIFACT_CANDIDATE":
            return _json_profile(content), []
        if state == "TABULAR_ARTIFACT_CANDIDATE":
            return _tabular_profile(content), []
        if state == "BINARY_ARTIFACT_CANDIDATE" and content.startswith(b"PK\x03\x04"):
            return _zip_profile(content)
    except (
        csv.Error,
        json.JSONDecodeError,
        UnicodeDecodeError,
        zipfile.BadZipFile,
    ) as exc:
        return {"format": "UNKNOWN", "profileState": "PARSE_ERROR"}, [
            f"PROFILE_ERROR:{type(exc).__name__}"
        ]
    return {"format": "UNKNOWN", "profileState": "NOT_APPLICABLE"}, []


def _normalization_state(fetch_state: str, mapped_source_keys: list[str]) -> str:
    structured = {
        "TABULAR_ARTIFACT_CANDIDATE",
        "JSON_ARTIFACT_CANDIDATE",
        "BINARY_ARTIFACT_CANDIDATE",
        "HTML_STRUCTURED_CANDIDATE",
    }
    if fetch_state in structured:
        return (
            "MAPPED_PARSER_REVIEW" if mapped_source_keys else "SOURCE_SCHEMA_REQUIRED"
        )
    if fetch_state == "DOCUMENT_ONLY":
        return "DOCUMENT_METADATA_ONLY"
    return "NOT_NORMALIZABLE"


def _payload_state(
    url: str, response: AuditFetchResponse
) -> tuple[str, str, list[str], bool]:
    content_type = response.headers.get("content-type", "").lower()
    content = response.content
    if response.truncated:
        return "MAX_BYTES_EXCEEDED", "NOT_USED", [], False
    if response.status_code >= 400:
        return "HTTP_ERROR", "NOT_USED", [], False
    if not content:
        return "EMPTY_RESPONSE", "NOT_USED", [], False
    if _is_html(content_type, content):
        if any(marker in content[:10000].lower() for marker in ANTI_BOT_MARKERS):
            return "ANTI_BOT_RESPONSE", "NOT_USED", [], False
        links = _static_artifact_links(url, content)
        if links:
            return "HTML_WITH_ARTIFACT_LINKS", "STATIC_DISCOVERED", links, False
        profile = _html_profile(content)
        if profile.get("tableCount") or profile.get("embeddedJsonCount"):
            return "HTML_STRUCTURED_CANDIDATE", "STATIC_STRUCTURED", [], True
        return "HTML_METADATA_ONLY", "STATIC_NO_LINKS", [], False
    if content.startswith(b"%PDF"):
        return "DOCUMENT_ONLY", "NOT_USED", [], True
    if content.startswith((b"PK\x03\x04", b"\xd0\xcf\x11\xe0")):
        return "BINARY_ARTIFACT_CANDIDATE", "NOT_USED", [], True
    if "json" in content_type or _is_json(content):
        return "JSON_ARTIFACT_CANDIDATE", "NOT_USED", [], True
    if "csv" in content_type or _looks_tabular(content):
        return "TABULAR_ARTIFACT_CANDIDATE", "NOT_USED", [], True
    return "UNVERIFIED_PAYLOAD", "NOT_USED", [], False


def _disposition(
    source_role: str,
    fetch_state: str,
    duplicate_of: int | None,
    mapped_source_keys: list[str],
) -> str:
    if duplicate_of is not None:
        return "DUPLICATE_REJECT"
    role_dispositions = {
        "REFERENCE_ONLY": "REFERENCE_ONLY",
        "OPEN_SOURCE_REFERENCE": "IMPLEMENTATION_REFERENCE_ONLY",
        "SECONDARY_DISCOVERY": "DISCOVERY_ONLY",
        "LOCAL_APPLICATION": "LOCAL_ONLY",
        "LICENSED_CANDIDATE": "LICENSE_REQUIRED",
        "UNCLASSIFIED": "QUARANTINE",
    }
    if source_role in role_dispositions:
        return role_dispositions[source_role]
    if mapped_source_keys and fetch_state in {
        "TABULAR_ARTIFACT_CANDIDATE",
        "JSON_ARTIFACT_CANDIDATE",
        "BINARY_ARTIFACT_CANDIDATE",
    }:
        return "MAP_EXISTING_SOURCE"
    state_dispositions = {
        "NOT_FETCHED": "AUDIT_PENDING",
        "TABULAR_ARTIFACT_CANDIDATE": "BUILD_OR_MAP_PARSER",
        "JSON_ARTIFACT_CANDIDATE": "BUILD_OR_MAP_PARSER",
        "BINARY_ARTIFACT_CANDIDATE": "BUILD_OR_MAP_PARSER",
        "HTML_STRUCTURED_CANDIDATE": "SOURCE_SCHEMA_REQUIRED",
        "HTML_WITH_ARTIFACT_LINKS": "RESOLVER_REQUIRED",
        "DOCUMENT_ONLY": "DOCUMENT_OR_RULE_INPUT",
        "ANTI_BOT_RESPONSE": "BLOCKED_ANTI_BOT",
    }
    return state_dispositions.get(fetch_state, "BLOCKED_UNVERIFIED")


def _archive_content(
    *,
    root: Path,
    manifest_hash: str,
    inventory_id: int,
    content: bytes,
    url: str,
    content_type: str | None,
) -> tuple[str, str]:
    content_hash = hashlib.sha256(content).hexdigest()
    suffix = Path(urlsplit(url).path).suffix.lower()
    allowed = {
        ".csv",
        ".json",
        ".txt",
        ".zip",
        ".xls",
        ".xlsx",
        ".xml",
        ".pdf",
        ".html",
    }
    if suffix not in allowed:
        lowered_type = (content_type or "").lower()
        suffix = (
            ".json"
            if "json" in lowered_type
            else ".html"
            if "html" in lowered_type
            else ".bin"
        )
    destination = (
        root / manifest_hash / f"row_{inventory_id:03d}" / f"{content_hash}{suffix}"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        destination.write_bytes(content)
    return content_hash, str(destination.resolve())


def _browser_candidates(url: str, timeout_seconds: int) -> BrowserDiscovery:
    return discover_links_with_vyom(url, timeout_seconds)


def _attempt_fetch(
    *,
    url: str,
    timeout_seconds: int,
    max_bytes: int,
) -> dict[str, object]:
    try:
        response = fetch_inventory_url(url, timeout_seconds, max_bytes)
    except Exception as exc:
        return {
            "fetch_state": "FETCH_ERROR",
            "scraper_state": "NOT_USED",
            "discovered_urls": [],
            "resolved_url": url,
            "error": f"{type(exc).__name__}: {str(exc)[:500]}",
        }
    state, scraper_state, links, archive = _payload_state(url, response)
    return {
        "fetch_state": state,
        "scraper_state": scraper_state,
        "discovered_urls": links,
        "resolved_url": url,
        "response": response,
        "archive": archive,
        "error": None,
    }


def _fetch_row(
    *,
    landing_url: str,
    direct_candidates: list[str],
    timeout_seconds: int,
    max_bytes: int,
    use_browser: bool,
) -> dict[str, object]:
    attempts: list[dict[str, object]] = []
    final: dict[str, object] | None = None
    for candidate in list(dict.fromkeys([*direct_candidates, landing_url])):
        fetched = _attempt_fetch(
            url=candidate,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
        )
        attempts.append(
            {
                "url": candidate,
                "state": fetched["fetch_state"],
                "error": fetched["error"],
            }
        )
        final = fetched
        if fetched["fetch_state"] in {
            "TABULAR_ARTIFACT_CANDIDATE",
            "JSON_ARTIFACT_CANDIDATE",
            "BINARY_ARTIFACT_CANDIDATE",
        }:
            break
    if final is None:
        raise RuntimeError("No inventory URL was available for fetch.")
    if final["fetch_state"] == "HTML_WITH_ARTIFACT_LINKS":
        discovered_value = final["discovered_urls"]
        discovered = discovered_value if isinstance(discovered_value, list) else []
        safe_candidates = [
            url
            for url in discovered
            if _safe_discovered_artifact_url(landing_url, str(url))
        ][:8]
        for candidate in safe_candidates:
            fetched = _attempt_fetch(
                url=str(candidate),
                timeout_seconds=timeout_seconds,
                max_bytes=max_bytes,
            )
            attempts.append(
                {
                    "url": candidate,
                    "state": fetched["fetch_state"],
                    "error": fetched["error"],
                }
            )
            if fetched["fetch_state"] in {
                "TABULAR_ARTIFACT_CANDIDATE",
                "JSON_ARTIFACT_CANDIDATE",
                "BINARY_ARTIFACT_CANDIDATE",
            }:
                fetched["discovered_urls"] = discovered
                fetched["scraper_state"] = "STATIC_FOLLOWED"
                final = fetched
                break
    if final["fetch_state"] == "HTML_METADATA_ONLY" and use_browser:
        browser = _browser_candidates(landing_url, timeout_seconds)
        browser_links = [
            item["url"] for item in browser.links if _is_artifact_url(item["url"])
        ]
        final["scraper_state"] = f"BROWSER_{browser.state}"
        if browser_links:
            final["fetch_state"] = "HTML_WITH_ARTIFACT_LINKS"
            final["discovered_urls"] = browser_links
    final["attempts"] = attempts
    return final


def _mapped_source_keys() -> dict[str, list[str]]:
    mapped: dict[str, list[str]] = {}
    for descriptor in SOURCE_CATALOG:
        canonical = canonicalize_inventory_url(descriptor.url)
        mapped.setdefault(canonical, []).append(descriptor.key)
    return mapped


def _derived_official_candidates(landing_url: str) -> list[str]:
    parts = urlsplit(landing_url)
    path_parts = [part for part in parts.path.split("/") if part]
    if (
        parts.hostname == "fred.stlouisfed.org"
        and len(path_parts) == 2
        and path_parts[0].lower() == "series"
        and path_parts[1].replace("-", "").replace("_", "").isalnum()
    ):
        series_id = path_parts[1].upper()
        return [f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"]
    return []


def _candidate_urls(source_keys: list[str], landing_url: str) -> list[str]:
    candidates: list[str] = _derived_official_candidates(landing_url)
    for source_key in source_keys:
        candidates.extend(direct_download_candidates(source_key)[:8])
    return list(dict.fromkeys(candidates))[:20]


def _base_row(
    *,
    run_id: str,
    inventory_id: int,
    contract: RegistryUrlContract,
    canonical_url: str,
    duplicate_of: int | None,
    mapped_source_keys: list[str],
    audited_at: str,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "inventory_id": inventory_id,
        "url": contract.url,
        "canonical_url": canonical_url,
        "hostname": contract.hostname,
        "source_role": contract.source_role,
        "allowed_jobs_json": json.dumps(contract.allowed_jobs, separators=(",", ":")),
        "provisional_family_id": provisional_family_id(canonical_url),
        "duplicate_of_inventory_id": duplicate_of,
        "fetch_state": "NOT_FETCHED",
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "content_hash": None,
        "raw_path": None,
        "scraper_state": "NOT_USED",
        "discovered_urls_json": "[]",
        "resolved_url": None,
        "mapped_source_keys_json": json.dumps(mapped_source_keys),
        "attempts_json": "[]",
        "normalization_state": "NOT_EVALUATED",
        "payload_profile_json": "{}",
        "quality_issues_json": "[]",
        "error": None,
        "can_unlock_ready": False,
        "audited_at": audited_at,
    }


def _apply_fetch_result(
    row: dict[str, object],
    fetched: dict[str, object],
    archive_root: Path,
    manifest_hash: str,
) -> None:
    row["fetch_state"] = fetched["fetch_state"]
    row["scraper_state"] = fetched["scraper_state"]
    row["discovered_urls_json"] = json.dumps(fetched["discovered_urls"])
    row["resolved_url"] = fetched.get("resolved_url")
    row["attempts_json"] = json.dumps(fetched.get("attempts", []))
    row["error"] = fetched["error"]
    response = fetched.get("response")
    if not isinstance(response, AuditFetchResponse):
        return
    row["status_code"] = response.status_code
    row["content_type"] = response.headers.get("content-type")
    row["content_length"] = len(response.content)
    profile, quality_issues = _profile_payload(str(row["fetch_state"]), response)
    mapped_source_keys = json.loads(str(row["mapped_source_keys_json"]))
    row["normalization_state"] = _normalization_state(
        str(row["fetch_state"]), mapped_source_keys
    )
    row["payload_profile_json"] = json.dumps(profile)
    row["quality_issues_json"] = json.dumps(quality_issues)
    if response.content:
        row["content_hash"] = hashlib.sha256(response.content).hexdigest()
    if fetched.get("archive") and response.content:
        content_hash, raw_path = _archive_content(
            root=archive_root,
            manifest_hash=manifest_hash,
            inventory_id=int(str(row["inventory_id"])),
            content=response.content,
            url=str(row.get("resolved_url") or row["url"]),
            content_type=response.headers.get("content-type"),
        )
        row["content_hash"], row["raw_path"] = content_hash, raw_path


def _write_report(
    run_id: str, rows: list[dict[str, object]], report_root: Path
) -> Path:
    report_root.mkdir(parents=True, exist_ok=True)
    path = report_root / f"source_inventory_audit_{run_id}.csv"
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path.resolve()


def audit_saved_inventory(
    *,
    urls: Iterable[str] | None = None,
    fetch_ids: set[int] | None = None,
    use_browser: bool = False,
    timeout_seconds: int = 15,
    max_bytes: int = 5_000_000,
    throttle_seconds: float = 0.25,
    archive_root: Path | None = None,
    report_root: Path | None = None,
) -> dict[str, object]:
    inventory = list(urls) if urls is not None else load_saved_link_inventory()
    selected = set(fetch_ids or set())
    if len(selected) > MAX_FETCH_IDS:
        raise ValueError(
            f"At most {MAX_FETCH_IDS} URLs may be fetched in one audit run."
        )
    invalid_ids = selected - set(range(1, len(inventory) + 1))
    if invalid_ids:
        raise ValueError(f"Unknown inventory IDs: {sorted(invalid_ids)}")
    contracts = classify_registry_urls(inventory)
    manifest_hash = inventory_manifest_hash(inventory)
    run_id = uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat()
    storage.start_source_inventory_audit_run(
        run_id=run_id,
        manifest_hash=manifest_hash,
        total_rows=len(inventory),
        selected_fetch_rows=len(selected),
        fetch_enabled=bool(selected),
        browser_enabled=use_browser,
        started_at=started_at,
    )
    seen: dict[str, int] = {}
    source_keys_by_url = _mapped_source_keys()
    rows: list[dict[str, object]] = []
    for inventory_id, contract in enumerate(contracts, 1):
        canonical_url = canonicalize_inventory_url(contract.url)
        duplicate_of = seen.get(canonical_url)
        seen.setdefault(canonical_url, inventory_id)
        mapped_source_keys = source_keys_by_url.get(canonical_url, [])
        row = _base_row(
            run_id=run_id,
            inventory_id=inventory_id,
            contract=contract,
            canonical_url=canonical_url,
            duplicate_of=duplicate_of,
            mapped_source_keys=mapped_source_keys,
            audited_at=datetime.now(timezone.utc).isoformat(),
        )
        if inventory_id in selected and duplicate_of is None:
            fetched = _fetch_row(
                landing_url=contract.url,
                direct_candidates=_candidate_urls(mapped_source_keys, contract.url),
                timeout_seconds=timeout_seconds,
                max_bytes=max_bytes,
                use_browser=use_browser,
            )
            _apply_fetch_result(
                row, fetched, archive_root or DEFAULT_ARCHIVE_ROOT, manifest_hash
            )
            if throttle_seconds > 0:
                time.sleep(throttle_seconds)
        row["disposition"] = _disposition(
            contract.source_role,
            str(row["fetch_state"]),
            duplicate_of,
            mapped_source_keys,
        )
        rows.append(row)
    recorded = storage.save_source_inventory_audit_rows(rows)
    report_path = _write_report(run_id, rows, report_root or DEFAULT_REPORT_ROOT)
    completed_at = datetime.now(timezone.utc).isoformat()
    storage.complete_source_inventory_audit_run(
        run_id=run_id,
        status="COMPLETE",
        completed_at=completed_at,
        report_path=str(report_path),
    )
    state_counts: dict[str, int] = {}
    for row in rows:
        state = str(row["fetch_state"])
        state_counts[state] = state_counts.get(state, 0) + 1
    return {
        "runId": run_id,
        "manifestHash": manifest_hash,
        "totalRows": len(inventory),
        "recordedRows": recorded,
        "selectedFetchRows": len(selected),
        "statusCounts": state_counts,
        "reportPath": str(report_path),
        "rule": "Inventory audit results never unlock READY; parser and gate verification remain mandatory.",
    }
