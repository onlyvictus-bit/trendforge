from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from .common import (
    decode_bytes,
    extract_data_date,
    find_value,
    parse_date_value,
    rows_from_content,
    source_result,
)


def _document_url(value: Any) -> str | None:
    path = str(value or "").strip()
    return urljoin("https://www.bseindia.com/", path) if path else None


def _offer_type(url: str | None) -> str:
    normalized = (url or "").lower()
    if "buybacktenderoffer" in normalized:
        return "BUYBACK_TENDER"
    if "takeover" in normalized:
        return "TAKEOVER_OPEN_OFFER"
    return "UNKNOWN"


def _bse_date(value: Any) -> str | None:
    text = str(value or "").strip()
    match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", text)
    if match:
        try:
            return datetime.strptime(match.group(1), "%m/%d/%Y").date().isoformat()
        except ValueError:
            return None
    return parse_date_value(text)


def parse_bse_offer_index(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse BSE's offer index without treating linked XBRL metadata as terms."""
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    observed_date = parse_date_value(last_modified)
    if observed_date and (data_date is None or data_date > observed_date):
        data_date = observed_date
        date_source = "retrieval_or_last_modified_date"

    rows, source_name = rows_from_content(content)
    offer_type = _offer_type(url)
    offers: list[dict[str, Any]] = []
    publication_dates: list[str] = []
    for row in rows:
        company = find_value(row, ("fld_name_of_company", "company_name")) or ""
        company_id = find_value(row, ("fld_company_id", "company_code")) or ""
        scrip_code = find_value(row, ("scripcode", "scrip_code")) or ""
        pre_document = find_value(row, ("predoc", "pre_doc"))
        post_document = find_value(row, ("postdoc", "post_doc"))
        if not company or not (pre_document or post_document):
            continue
        pre_published_at = _bse_date(
            find_value(row, ("preti", "preenddate", "pre_date"))
        )
        post_published_at = _bse_date(
            find_value(row, ("postti", "postenddate", "post_date"))
        )
        publication_dates.extend(
            value for value in (pre_published_at, post_published_at) if value
        )
        offers.append(
            {
                "company": company.strip(),
                "bseCompanyId": company_id.strip(),
                "scripCode": scrip_code.strip(),
                "offerType": offer_type,
                "preDocumentUrl": _document_url(pre_document),
                "postDocumentUrl": _document_url(post_document),
                "prePublishedAt": pre_published_at,
                "postPublishedAt": post_published_at,
                "preRevisionStatus": (
                    find_value(row, ("prestatus", "pre_status")) or "UNKNOWN"
                ).upper(),
                "postRevisionStatus": (
                    find_value(row, ("poststatus", "post_status")) or "UNKNOWN"
                ).upper(),
                "scope": "CORPORATE_OFFER_DISCOVERY_ONLY",
            }
        )

    if publication_dates:
        latest_publication = max(publication_dates)
        if observed_date and latest_publication > observed_date:
            data_date = observed_date
            date_source = "latest_publication_capped_by_retrieval"
        else:
            data_date = latest_publication
            date_source = "latest_offer_publication"

    if not offers:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="No BSE offer-index rows with linked documents were found.",
            output={
                "scope": "CORPORATE_OFFER_DISCOVERY_ONLY",
                "dateSource": date_source,
                "requiresXbrlDetails": True,
            },
        )

    return source_result(
        parser_state="PARSED_METADATA_ONLY",
        data_date=data_date,
        record_count=len(offers),
        summary=(
            f"BSE offer index parsed from {source_name}; linked XBRL terms remain required."
        ),
        output={
            "scope": "CORPORATE_OFFER_DISCOVERY_ONLY",
            "dateSource": date_source,
            "requiresXbrlDetails": True,
            "rows": offers,
        },
    )
