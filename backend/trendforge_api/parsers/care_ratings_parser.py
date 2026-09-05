"""Pure parser for CARE Ratings' official page-owned rationale JSON."""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from urllib.parse import quote

from .common import parse_date_value, source_result


PDF_BASE = "https://www.careratings.com/upload/CompanyFiles/PR/"


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _action(title: str) -> str:
    value = title.casefold()
    if "upgrade" in value:
        return "RATING_UPGRADED"
    if "downgrade" in value:
        return "RATING_DOWNGRADED"
    if "reaffirm" in value:
        return "RATING_REAFFIRMED"
    if "withdraw" in value:
        return "RATING_WITHDRAWN"
    if "assign" in value:
        return "RATING_ASSIGNED"
    return "OTHER_DISCLOSED_RATING_ACTION"


def parse_care_ratings(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="CARE response is not valid JSON.",
            output={"rows": [], "scope": "STOCK_LEVEL_INFORMATIONAL"},
            error=str(exc),
        )
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="CARE response is missing the required data list.",
            output={"rows": [], "scope": "STOCK_LEVEL_INFORMATIONAL"},
            error="missing data list",
        )
    source_rows = payload["data"]
    if not source_rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="CARE returned zero rating-rationale records; retain last-good.",
            output={"rows": [], "sourceRowCount": 0, "scope": "STOCK_LEVEL_INFORMATIONAL"},
            error="empty data list",
        )

    reference_text = parse_date_value(last_modified)
    reference = date.fromisoformat(reference_text) if reference_text else None
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    invalid = 0
    duplicates = 0
    for position, raw in enumerate(source_rows, start=1):
        if not isinstance(raw, dict):
            invalid += 1
            continue
        company_id = _text(raw.get("CompanyID"))
        company_name = _text(raw.get("CompanyName"))
        title = _text(raw.get("FileTitle"))
        filename = _text(raw.get("FileURL"))
        published = parse_date_value(raw.get("PublishedDate"))
        if not company_id or not company_name or not filename or not published:
            invalid += 1
            continue
        if reference and date.fromisoformat(published) > reference:
            invalid += 1
            continue
        identity = (company_id, published, filename)
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        heading = title or company_name
        rows.append(
            {
                "symbol": None,
                "mappingState": "UNMAPPED_NO_FUZZY_TICKER_MATCH",
                "careCompanyId": company_id,
                "companyName": company_name,
                "heading": heading,
                "ratingAction": _action(heading),
                "publicationDate": published,
                "fileType": _text(raw.get("FileType")) or None,
                "rationaleFilename": filename,
                "rationaleUrl": PDF_BASE + quote(filename),
                "sourceRow": position,
                "sourceUrl": url,
                "sourceTrust": "OFFICIAL",
                "scope": "STOCK_LEVEL_INFORMATIONAL",
                "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            }
        )
    if not rows:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="CARE rows failed identity/date/schema validation.",
            output={
                "rows": [],
                "sourceRowCount": len(source_rows),
                "invalidRowCount": invalid,
                "scope": "STOCK_LEVEL_INFORMATIONAL",
            },
            error="no valid rows",
        )
    data_date = max(row["publicationDate"] for row in rows)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} official CARE rating rationales.",
        output={
            "rows": rows,
            "records": rows,
            "sourceRowCount": len(source_rows),
            "normalizedRowCount": len(rows),
            "invalidRowCount": invalid,
            "duplicateRowCount": duplicates,
            "unmappedCompanyCount": len(rows),
            "parserVersion": "1.0.0",
            "sourceTrust": "OFFICIAL",
            "scope": "STOCK_LEVEL_INFORMATIONAL",
            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            "symbolMappingPolicy": "NO_FUZZY_TICKER_MATCH",
        },
    )
