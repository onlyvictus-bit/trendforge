"""Pure parser for CRISIL's official latest rating-rationales JSON listing."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

from .common import parse_date_value, source_result


RATIONALE_BASE_URL = (
    "https://www.crisilratings.com/mnt/winshare/Ratings/RatingList/RatingDocs/"
)


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _date(value: Any) -> str | None:
    parsed = parse_date_value(value)
    if parsed:
        return parsed
    text = _text(value)
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _reference_date(last_modified: str | None) -> date | None:
    parsed = _date(last_modified)
    return date.fromisoformat(parsed) if parsed else None


def _action(heading: str) -> str:
    value = heading.casefold()
    reaffirmed = "reaffirm" in value
    outlook = "outlook" in value and any(
        token in value for token in ("revised", "changed", "stable", "positive", "negative")
    )
    if reaffirmed and outlook:
        return "RATING_REAFFIRMED_OUTLOOK_REVISED"
    if "issuer not cooperating" in value and "migrat" in value:
        return "ISSUER_NOT_COOPERATING_RATING_MIGRATED"
    if "upgrade" in value:
        return "RATING_UPGRADED"
    if "downgrade" in value:
        return "RATING_DOWNGRADED"
    if reaffirmed:
        return "RATING_REAFFIRMED"
    if "withdraw" in value:
        return "RATING_WITHDRAWN"
    if "assign" in value:
        return "RATING_ASSIGNED"
    if outlook:
        return "OUTLOOK_REVISED"
    return "OTHER_DISCLOSED_RATING_ACTION"


def parse_crisil_ratings(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Normalize CRISIL records without inventing exchange ticker mappings."""
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="CRISIL rating-rationales response is not valid JSON.",
            output={"rows": [], "scope": "STOCK_LEVEL_INFORMATIONAL"},
            error=str(exc),
        )
    if not isinstance(payload, dict) or not isinstance(payload.get("docs"), list):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="CRISIL response is missing the required docs list.",
            output={"rows": [], "scope": "STOCK_LEVEL_INFORMATIONAL"},
            error="missing docs list",
        )

    docs = payload["docs"]
    if not docs:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="CRISIL returned zero rating-rationale rows; last-good must be retained.",
            output={
                "rows": [],
                "sourceRowCount": 0,
                "normalizedRowCount": 0,
                "scope": "STOCK_LEVEL_INFORMATIONAL",
                "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            },
            error="empty docs list",
        )

    reference = _reference_date(last_modified)
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    invalid = 0
    duplicates = 0
    for position, raw in enumerate(docs, start=1):
        if not isinstance(raw, dict):
            invalid += 1
            continue
        company_code = _text(raw.get("companyCode"))
        company_name = _text(raw.get("companyName"))
        heading = _text(raw.get("heading"))
        filename = _text(raw.get("ratingFileName"))
        rating_date = _date(raw.get("ratingDate"))
        transaction_date = _date(raw.get("transDate"))
        publication_date = max(
            item for item in (rating_date, transaction_date) if item is not None
        ) if rating_date or transaction_date else None
        if not company_code or not company_name or not heading or not publication_date:
            invalid += 1
            continue
        if reference and date.fromisoformat(publication_date) > reference:
            invalid += 1
            continue
        identity = (
            company_code,
            publication_date,
            filename,
            _text(raw.get("prId")),
        )
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        rows.append(
            {
                "symbol": None,
                "mappingState": "UNMAPPED_NO_FUZZY_TICKER_MATCH",
                "crisilCompanyCode": company_code,
                "companyName": company_name,
                "industryName": _text(raw.get("industryName")) or None,
                "heading": heading,
                "ratingAction": _action(heading),
                "ratingDate": rating_date,
                "transactionDate": transaction_date,
                "publicationDate": publication_date,
                "rationaleFilename": filename or None,
                "rationaleUrl": RATIONALE_BASE_URL + quote(filename) if filename else None,
                "prId": raw.get("prId"),
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
            summary="CRISIL rows failed required identity/date/schema validation.",
            output={
                "rows": [],
                "sourceRowCount": len(docs),
                "normalizedRowCount": 0,
                "invalidRowCount": invalid,
                "scope": "STOCK_LEVEL_INFORMATIONAL",
                "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            },
            error="no valid rating-rationale rows",
        )

    data_date = max(row["publicationDate"] for row in rows)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} official CRISIL rating rationales.",
        output={
            "rows": rows,
            "records": rows,
            "sourceRowCount": len(docs),
            "normalizedRowCount": len(rows),
            "invalidRowCount": invalid,
            "duplicateRowCount": duplicates,
            "unmappedCompanyCount": len(rows),
            "reportedTotalCount": payload.get("numFound"),
            "parserVersion": "1.0.0",
            "sourceTrust": "OFFICIAL",
            "scope": "STOCK_LEVEL_INFORMATIONAL",
            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            "symbolMappingPolicy": "NO_FUZZY_TICKER_MATCH",
        },
    )
