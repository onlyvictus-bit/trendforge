from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .parsers.bse_offer_xbrl_parser import parse_bse_offer_xbrl
from .source_monitor import hash_bytes, save_raw_snapshot
from .source_resolver import fetch_url
from .storage import (
    bse_offer_document_version_exists,
    get_latest_source_parse_result,
    save_bse_offer_document,
    save_raw_source_artifact,
)


SUPPORTED_INDEX_SOURCES = {"bse_buyback_tender", "bse_takeover_open_offer"}
FetchFunction = Callable[[str, int], tuple[int, dict[str, str], bytes]]


def _candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in rows:
        for phase, url_key, date_key, revision_key in (
            ("PRE", "preDocumentUrl", "prePublishedAt", "preRevisionStatus"),
            ("POST", "postDocumentUrl", "postPublishedAt", "postRevisionStatus"),
        ):
            document_url = row.get(url_key)
            if not document_url:
                continue
            candidates.append(
                {
                    **row,
                    "phase": phase,
                    "documentUrl": document_url,
                    "publishedDate": row.get(date_key),
                    "revisionStatus": row.get(revision_key) or "UNKNOWN",
                }
            )
    candidates.sort(
        key=lambda item: (item.get("publishedDate") or "", item["documentUrl"]),
        reverse=True,
    )
    return list({item["documentUrl"]: item for item in candidates}.values())


def refresh_bse_offer_documents(
    source_key: str,
    *,
    max_documents: int = 10,
    timeout_seconds: int = 15,
    force: bool = False,
    fetcher: FetchFunction = fetch_url,
) -> dict[str, Any]:
    """Fetch a bounded batch of linked BSE XBRL files from a saved index."""
    if source_key not in SUPPORTED_INDEX_SOURCES:
        raise ValueError(f"unsupported BSE offer source: {source_key}")
    if not 1 <= max_documents <= 100:
        raise ValueError("max_documents must be between 1 and 100")
    index = get_latest_source_parse_result(source_key)
    if index is None or index.parser_state != "PARSED_METADATA_ONLY":
        return {
            "sourceKey": source_key,
            "state": "WAIT_INDEX_METADATA",
            "attempted": 0,
            "saved": 0,
            "skipped": 0,
            "failed": 0,
            "reason": "A fresh parsed BSE offer index is required before XBRL fetch.",
            "executable": False,
        }

    attempted = saved = skipped = failed = 0
    results: list[dict[str, Any]] = []
    for item in _candidates(index.output.get("rows", [])):
        if attempted >= max_documents:
            break
        url = item["documentUrl"]
        revision = str(item.get("revisionStatus") or "UNKNOWN").upper()
        if not force and bse_offer_document_version_exists(
            document_url=url,
            published_date=item.get("publishedDate"),
            revision_status=revision,
        ):
            skipped += 1
            continue
        attempted += 1
        fetched_at = datetime.now(timezone.utc).isoformat()
        try:
            status_code, headers, content = fetcher(url, timeout_seconds)
            if status_code >= 400 or not content:
                raise OSError(f"HTTP {status_code} or empty XBRL response")
            content_hash = hash_bytes(content)
            raw_key = f"{source_key}_xbrl"
            raw_path = str(save_raw_snapshot(raw_key, content_hash, content))
            parsed = parse_bse_offer_xbrl(
                content,
                url=url,
                last_modified=headers.get("last-modified") or fetched_at,
            )
            artifact = {
                "parent_source_key": source_key,
                "company_id": item.get("bseCompanyId"),
                "symbol": item.get("symbol"),
                "scrip_code": item.get("scripCode"),
                "offer_type": item.get("offerType") or "UNKNOWN",
                "phase": item["phase"],
                "document_url": url,
                "published_date": item.get("publishedDate"),
                "revision_status": revision,
                "fetched_at": fetched_at,
                "status_code": status_code,
                "content_hash": content_hash,
                "raw_path": raw_path,
                "parser_state": parsed["parser_state"],
                "data_date": parsed.get("data_date"),
                "payload": parsed.get("output", {}),
                "error": parsed.get("error"),
            }
            document_id = save_bse_offer_document(artifact)
            save_raw_source_artifact(
                source_key=raw_key,
                fetched_at=fetched_at,
                content_hash=content_hash,
                content_length=len(content),
                raw_path=raw_path,
                last_modified=headers.get("last-modified"),
                etag=headers.get("etag"),
                parser_state=parsed["parser_state"],
                data_date=parsed.get("data_date"),
            )
            if parsed["parser_state"] == "PARSED_STRUCTURED":
                saved += 1
            else:
                failed += 1
            results.append(
                {
                    "documentId": document_id,
                    "url": url,
                    "phase": item["phase"],
                    "parserState": parsed["parser_state"],
                    "dataDate": parsed.get("data_date"),
                    "contentHash": content_hash,
                }
            )
        except (OSError, TimeoutError, ValueError) as exc:
            failed += 1
            results.append(
                {
                    "url": url,
                    "phase": item["phase"],
                    "parserState": "WAIT_PARSE_ERROR",
                    "error": str(exc),
                }
            )

    state = (
        "STRUCTURED_OK"
        if failed == 0 and (saved > 0 or skipped > 0)
        else "WAIT_XBRL_DETAILS"
    )
    return {
        "sourceKey": source_key,
        "state": state,
        "attempted": attempted,
        "saved": saved,
        "skipped": skipped,
        "failed": failed,
        "results": results,
        "executable": False,
    }
