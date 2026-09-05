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


def parse_nse_instruments(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    observed_date, _ = extract_data_date("", None, last_modified)
    if observed_date:
        data_date = observed_date
        date_source = "retrieval_or_last_modified_date"
    rows, source_name = rows_from_content(content)
    lower_url = (url or "").lower()
    index_membership = (
        "NIFTY50"
        if "ind_nifty50list" in lower_url
        else "NIFTY200"
        if "ind_nifty200list" in lower_url
        else "NIFTY500"
        if "ind_nifty500list" in lower_url
        else None
    )
    is_constituent_file = index_membership is not None or any(
        "industry" in row for row in rows[:3]
    )
    if is_constituent_file and index_membership is None:
        index_membership = "NIFTY500"
    output_rows: list[dict[str, Any]] = []
    for row in rows:
        symbol = (find_value(row, ("symbol",)) or "").strip().upper()
        company = (
            find_value(row, ("name_of_company", "company_name", "company")) or ""
        ).strip()
        series = (find_value(row, ("series",)) or "").strip().upper()
        isin = (
            (find_value(row, ("isin_number", "isin_code", "isin")) or "")
            .strip()
            .upper()
        )
        if not symbol or not company or not series or not isin:
            continue
        industry = (find_value(row, ("industry",)) or "").strip() or None
        output_rows.append(
            {
                "symbol": symbol,
                "company": company,
                "series": series,
                "listingDate": parse_date_value(
                    find_value(row, ("date_of_listing", "listing_date"))
                ),
                "paidUpValue": parse_float(find_value(row, ("paid_up_value",))) or None,
                "marketLot": parse_int(find_value(row, ("market_lot",))) or None,
                "isin": isin,
                "faceValue": parse_float(find_value(row, ("face_value",))) or None,
                "industry": industry,
                "indexMembership": index_membership if is_constituent_file else None,
                "active": True,
                "scope": f"{index_membership}_SECTOR_MEMBERSHIP"
                if is_constituent_file
                else "ALL_NSE_EQUITY",
            }
        )
    if not output_rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="No schema-valid NSE instrument rows found.",
            output={"scope": "NSE_INSTRUMENT_UNIVERSE", "dateSource": date_source},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(output_rows),
        summary=f"NSE instrument identity rows parsed from {source_name}.",
        output={
            "scope": f"{index_membership}_SECTOR_MEMBERSHIP"
            if is_constituent_file
            else "ALL_NSE_EQUITY",
            "dateSource": date_source,
            "rows": output_rows,
        },
    )
