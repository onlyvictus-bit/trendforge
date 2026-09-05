from __future__ import annotations

from collections import defaultdict
from typing import Any
from xml.etree import ElementTree

from .common import parse_date_value, parse_float, parse_int, source_result


MAX_XBRL_BYTES = 5 * 1024 * 1024


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _values(root: ElementTree.Element) -> dict[str, list[str]]:
    output: dict[str, list[str]] = defaultdict(list)
    for element in root.iter():
        value = (element.text or "").strip()
        if value:
            output[_local_name(element.tag)].append(value)
    return output


def _first(values: dict[str, list[str]], *keys: str) -> str | None:
    for key in keys:
        matches = values.get(key)
        if matches:
            return matches[0]
    return None


def _all(values: dict[str, list[str]], *keys: str) -> list[str]:
    output: list[str] = []
    for key in keys:
        output.extend(values.get(key, []))
    return list(dict.fromkeys(output))


def _phase(values: dict[str, list[str]], url: str | None) -> str:
    explicit = (_first(values, "PhaseOfBuyback") or "").upper()
    normalized_url = (url or "").lower()
    if "POST" in explicit or "postupload" in normalized_url:
        return "POST"
    return "PRE"


def _document_type(values: dict[str, list[str]], url: str | None) -> str:
    normalized_url = (url or "").lower()
    if _first(values, "BuybackPricePerShare") or "btrupload" in normalized_url:
        return "BUYBACK_TENDER"
    if _first(values, "OfferPricePerShareFullyPaidUp") or "takeover" in normalized_url:
        return "TAKEOVER_OPEN_OFFER"
    return "UNKNOWN"


def _data_date(values: dict[str, list[str]], offer_type: str) -> str | None:
    if offer_type == "BUYBACK_TENDER":
        value = _first(
            values,
            "DateOfSubmissionForBuybackTenderRoute",
            "DateOfPublicAnnouncement",
            "instant",
        )
    else:
        value = _first(
            values,
            "DateOfSubmissionForTakeoverPreTenderingPhase",
            "DateOfSubmissionForTakeoverPostTenderingPhase",
            "instant",
        )
    return parse_date_value(value)


def parse_bse_offer_xbrl(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse official BSE buyback/takeover XBRL into one normalized event."""
    if not content or len(content) > MAX_XBRL_BYTES:
        return source_result(
            parser_state="WAIT_PARSE_ERROR",
            data_date=None,
            record_count=0,
            summary="BSE XBRL is empty or exceeds the safe parser size limit.",
            output={"scope": "CORPORATE_OFFER_TERMS"},
            error="invalid XBRL size",
        )
    head = content[:4096].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
        return source_result(
            parser_state="WAIT_PARSE_ERROR",
            data_date=None,
            record_count=0,
            summary="BSE XBRL contains a prohibited DTD or entity declaration.",
            output={"scope": "CORPORATE_OFFER_TERMS"},
            error="DTD/entity declarations are not allowed",
        )
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        return source_result(
            parser_state="WAIT_PARSE_ERROR",
            data_date=None,
            record_count=0,
            summary="BSE XBRL is malformed and was rejected.",
            output={"scope": "CORPORATE_OFFER_TERMS"},
            error=str(exc),
        )

    values = _values(root)
    offer_type = _document_type(values, url)
    phase = _phase(values, url)
    data_date = _data_date(values, offer_type)
    observed_date = parse_date_value(last_modified)
    if observed_date and (data_date is None or data_date > observed_date):
        data_date = observed_date

    if offer_type == "BUYBACK_TENDER":
        company = _first(values, "NameOfTheCompany")
        isin = _first(values, "ISIN")
        scrip_code = _first(values, "ScripCode")
        nse_symbol = _first(values, "NSESymbol")
        symbol = nse_symbol if nse_symbol and nse_symbol != "NOTLISTED" else scrip_code
        offer_price = parse_float(_first(values, "BuybackPricePerShare"))
        quantity = parse_int(_first(values, "NumberOfSharesOfBuybackOffer"))
        consideration = parse_float(
            _first(values, "AmountOfAggregateConsiderationNotExceeding")
        )
        announcement_date = parse_date_value(_first(values, "DateOfPublicAnnouncement"))
        record_date = parse_date_value(_first(values, "DateOfRecordOfBuyback"))
        start_date = parse_date_value(_first(values, "DateOfBuybackOpening"))
        end_date = parse_date_value(_first(values, "DateOfBuybackClosing"))
        acquirers: list[str] = []
    else:
        company = _first(values, "NameOfTargetCompany")
        isin = _first(values, "ISINOfTargetCompany")
        scrip_code = _first(values, "ScripCode")
        symbol = scrip_code
        offer_price = parse_float(_first(values, "OfferPricePerShareFullyPaidUp"))
        quantity = parse_int(_first(values, "NumberOfSharesFullyPaidUpToBeAquired"))
        consideration = parse_float(_first(values, "OfferSize"))
        announcement_date = data_date
        record_date = None
        start_date = parse_date_value(_first(values, "DateOfStartOfTendering"))
        end_date = parse_date_value(_first(values, "DateOfEndOfTendering"))
        acquirers = _all(values, "NameOfAcquirer", "NameOfPersonsActingInConcert")

    required = (company, isin, data_date)
    terms_are_positive = (
        offer_price is not None
        and offer_price > 0
        and quantity is not None
        and quantity > 0
    )
    if (
        offer_type == "UNKNOWN"
        or any(value in {None, ""} for value in required)
        or not terms_are_positive
    ):
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary=(
                "BSE XBRL lacks mandatory identity/date fields or positive "
                "price-and-quantity offer terms."
            ),
            output={
                "scope": "CORPORATE_OFFER_TERMS",
                "offerType": offer_type,
                "phase": phase,
            },
        )

    row = {
        "symbol": str(symbol or "").upper(),
        "scripCode": str(scrip_code or ""),
        "isin": isin,
        "company": company,
        "offerType": offer_type,
        "phase": phase,
        "actionType": offer_type,
        "actionClass": "OTHER",
        "announcementDate": announcement_date,
        "recordDate": record_date,
        "startDate": start_date,
        "endDate": end_date,
        "offerPrice": offer_price,
        "quantity": quantity,
        "consideration": consideration,
        "acquirers": acquirers,
        "scope": "CORPORATE_OFFER_TERMS",
    }
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=1,
        summary=f"Structured {offer_type} {phase} terms parsed from BSE XBRL.",
        output={"scope": "CORPORATE_OFFER_TERMS", "rows": [row]},
    )
