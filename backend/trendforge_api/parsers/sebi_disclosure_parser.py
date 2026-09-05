from __future__ import annotations

from typing import Any

from .common import (
    decode_bytes,
    extract_data_date,
    find_value,
    parse_date_value,
    parse_float,
    parse_int,
    rows_from_content,
    source_result,
)


def parse_sebi_disclosures(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    rows, source_name = rows_from_content(content)
    disclosures: list[dict[str, Any]] = []
    for row in rows:
        symbol = find_value(row, ("symbol", "company_symbol")) or ""
        isin = find_value(row, ("isin",)) or ""
        entity = (
            find_value(
                row, ("person_name", "entity_name", "acquirer", "promoter", "name")
            )
            or ""
        )
        transaction_type = (
            find_value(
                row, ("transaction_type", "acquisition_disposal", "nature", "type")
            )
            or ""
        )
        if not (symbol or isin) or not entity or not transaction_type:
            continue
        disclosures.append(
            {
                "symbol": symbol.strip().upper(),
                "isin": isin.strip().upper(),
                "entity": entity.strip(),
                "relationship": (
                    find_value(row, ("relationship", "category", "designation")) or ""
                )
                .strip()
                .upper(),
                "transactionType": transaction_type.strip().upper(),
                "eventDate": parse_date_value(
                    find_value(row, ("transaction_date", "event_date", "date"))
                ),
                "disclosureDate": parse_date_value(
                    find_value(row, ("disclosure_date", "reported_date"))
                ),
                "quantity": parse_int(
                    find_value(row, ("quantity", "shares", "securities"))
                ),
                "price": parse_float(
                    find_value(row, ("price", "transaction_price", "value_per_share"))
                ),
                "preHolding": parse_float(
                    find_value(
                        row, ("pre_holding", "holding_before", "pre_shareholding")
                    )
                ),
                "postHolding": parse_float(
                    find_value(
                        row, ("post_holding", "holding_after", "post_shareholding")
                    )
                ),
                "evidenceType": "DIRECT_PUBLIC_DISCLOSURE",
                "scope": "STOCK_LEVEL_DISCLOSURE",
            }
        )
    if not disclosures:
        state = (
            "PARSED_METADATA_ONLY"
            if "<html" in text[:500].lower() or content.startswith(b"%PDF")
            else "WAIT_EMPTY_PARSE"
        )
        return source_result(
            parser_state=state,
            data_date=data_date,
            record_count=0,
            summary="SEBI page/document captured, but no validated structured disclosure rows were extracted.",
            output={"scope": "STOCK_LEVEL_DISCLOSURE", "dateSource": date_source},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(disclosures),
        summary=f"SEBI structured disclosures parsed from {source_name}.",
        output={
            "scope": "STOCK_LEVEL_DISCLOSURE",
            "dateSource": date_source,
            "rows": disclosures,
        },
    )
