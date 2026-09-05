from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .institutional_sources import EndpointFetchResult, FetchState


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT_DIR / "data" / "trendforge_research.db"
IST = ZoneInfo("Asia/Kolkata")

ParserState = Literal[
    "STRUCTURED_OK",
    "VALID_EMPTY",
    "STALE_FALLBACK",
    "SCHEMA_MISMATCH",
    "FETCH_FAILED",
]


class DisclosureModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DisclosureSourceStatus(DisclosureModel):
    endpoint_key: str
    fetch_state: str
    parser_state: ParserState
    fetched_at: datetime
    content_hash: str | None = None
    source_record_count: int = Field(ge=0)
    normalized_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    reason: str
    can_unlock_ready: bool = False


class InstitutionalDisclosureEvent(DisclosureModel):
    event_id: str
    source_key: str
    source_content_hash: str | None = None
    source_record_id: str | None = None
    symbol: str | None = None
    scrip_code: str | None = None
    isin: str | None = None
    company: str | None = None
    event_type: str
    category: str | None = None
    side: Literal["BUY", "SELL", "CREATE", "RELEASE", "INVOKE", "OTHER"] | None = None
    actor: str | None = None
    counterparty: str | None = None
    event_date: str | None = None
    published_at: str | None = None
    quantity: float | None = None
    price: float | None = None
    notional: float | None = None
    percent_before: float | None = None
    percent_change: float | None = None
    percent_after: float | None = None
    promoter_holding_pct: float | None = None
    pledge_shares: float | None = None
    pledge_pct_promoter: float | None = None
    pledge_pct_total: float | None = None
    headline: str | None = None
    attachment_url: str | None = None
    revision_status: str | None = None
    source_fields: dict[str, Any] = Field(default_factory=dict)
    can_unlock_ready: bool = False


class DisclosureNormalizationSnapshot(DisclosureModel):
    run_id: str
    normalized_at: datetime
    state: Literal["RESEARCH_ONLY", "WAIT_SOURCE"]
    sources: list[DisclosureSourceStatus] = Field(default_factory=list)
    events: list[InstitutionalDisclosureEvent] = Field(default_factory=list)
    can_unlock_ready: bool = False
    reason: str


class DisclosureDrilldown(DisclosureModel):
    run_id: str
    normalized_at: datetime
    state: Literal["RESEARCH_ONLY", "WAIT_SOURCE", "WAIT_NO_SNAPSHOT"]
    source_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    sources: list[DisclosureSourceStatus] = Field(default_factory=list)
    events: list[InstitutionalDisclosureEvent] = Field(default_factory=list)
    can_unlock_ready: bool = False
    reason: str


def _text(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() not in {"", "-"}:
            return str(value).strip()
    return None


def _number(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, "", "-"):
            continue
        try:
            parsed = float(str(value).replace(",", "").strip())
        except ValueError:
            continue
        if math.isfinite(parsed):
            return parsed
    return None


def _date(value: Any) -> str | None:
    if value is None or not str(value).strip() or str(value).strip() == "-":
        return None
    text = str(value).strip()
    formats = (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y %H:%M",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d/%m/%Y",
        "%d %b %Y",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if any(token in fmt for token in ("%H", "%M", "%S")):
            return parsed.replace(tzinfo=IST).isoformat()
        return parsed.date().isoformat()
    return text


def _slug(value: str | None, fallback: str) -> str:
    clean = re.sub(r"[^A-Z0-9]+", "_", (value or "").upper()).strip("_")
    return clean or fallback


def _rows(payload: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys or ("data", "Data", "Table", "aaData"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _event_id(source_key: str, row: dict[str, Any]) -> str:
    canonical = json.dumps(row, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(f"{source_key}\n{canonical}".encode()).hexdigest()


def _side(value: str | None) -> Literal["BUY", "SELL", "CREATE", "RELEASE", "INVOKE", "OTHER"]:
    text = (value or "").upper()
    if any(token in text for token in ("BUY", "PURCHASE", "ACQUISITION")) or text in {"B", "P"}:
        return "BUY"
    if any(token in text for token in ("SELL", "SALE", "DISPOSAL")) or text == "S":
        return "SELL"
    if any(token in text for token in ("CREATE", "CREATION")):
        return "CREATE"
    if "RELEASE" in text or "REVOK" in text:
        return "RELEASE"
    if "INVOK" in text:
        return "INVOKE"
    return "OTHER"


def _event(
    source_key: str,
    result: EndpointFetchResult,
    row: dict[str, Any],
    **values: Any,
) -> InstitutionalDisclosureEvent:
    return InstitutionalDisclosureEvent(
        event_id=_event_id(source_key, row),
        source_key=source_key,
        source_content_hash=result.content_hash,
        source_fields=row,
        **values,
    )


def _announcement_events(
    source_key: str, result: EndpointFetchResult, rows: list[dict[str, Any]]
) -> list[InstitutionalDisclosureEvent]:
    events: list[InstitutionalDisclosureEvent] = []
    for row in rows:
        if source_key == "nse_announcements":
            symbol = _text(row, "symbol")
            published = _date(_text(row, "an_dt", "sort_date", "exchdisstime"))
            headline = _text(row, "attchmntText", "desc")
            record_id = _text(row, "seq_id")
            company = _text(row, "sm_name")
            isin = _text(row, "sm_isin")
            category = _text(row, "desc")
            attachment = _text(row, "attchmntFile")
            revision = _text(row, "old_new")
            scrip_code = None
        else:
            scrip_code = _text(row, "SCRIP_CD")
            published = _date(_text(row, "News_submission_dt", "DT_TM", "NEWS_DT"))
            headline = _text(row, "NEWSSUB", "HEADLINE", "MORE")
            record_id = _text(row, "NEWSID")
            company = _text(row, "SLONGNAME")
            isin = None
            symbol = None
            category = _text(row, "SUBCATNAME", "CATEGORYNAME")
            attachment_name = _text(row, "ATTACHMENTNAME")
            attachment = (
                f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment_name}"
                if attachment_name
                else None
            )
            revision = _text(row, "FILESTATUS", "OLD")
        if not (record_id or headline) or not published:
            continue
        events.append(
            _event(
                source_key,
                result,
                row,
                source_record_id=record_id,
                symbol=symbol.upper() if symbol else None,
                scrip_code=scrip_code,
                isin=isin,
                company=company,
                event_type=_slug(category, "ANNOUNCEMENT"),
                category=category,
                event_date=published,
                published_at=published,
                headline=headline,
                attachment_url=attachment,
                revision_status=revision,
            )
        )
    return events


def _nse_regulation_events(
    source_key: str, result: EndpointFetchResult, rows: list[dict[str, Any]]
) -> list[InstitutionalDisclosureEvent]:
    events: list[InstitutionalDisclosureEvent] = []
    for row in rows:
        symbol = _text(row, "symbol")
        actor = _text(row, "promoterName", "personName", "acquirerName")
        if source_key == "nse_regulation_29":
            action = _text(row, "transactionType")
            event_date = _date(_text(row, "creditDateFrom", "creditDate", "ddmDroadcastDate"))
            published = _date(_text(row, "ddmDroadcastDate"))
            quantity = _number(row, "nosharesAcquired")
            before = _number(row, "persharesPrior")
            change = _number(row, "persharesAcquired")
            after = _number(row, "persharesAfterAcq")
            event_type = "SAST_ACQUISITION" if _side(action) == "BUY" else "SAST_DISPOSAL" if _side(action) == "SELL" else "SAST_CHANGE"
            counterparty = None
            headline = action
        elif source_key == "nse_regulation_31":
            action = _text(row, "typeOfEvent")
            side = _side(action)
            event_type = {
                "CREATE": "PLEDGE_CREATE",
                "RELEASE": "PLEDGE_RELEASE",
                "INVOKE": "PLEDGE_INVOKE",
            }.get(side, "ENCUMBRANCE_EVENT")
            event_date = _date(_text(row, "sr_dateof_creation", "broadcastDateTime"))
            published = _date(_text(row, "broadcastDateTime"))
            quantity = _number(row, "numofShares")
            before = _number(row, "pershareAlrdyheldPrmtr")
            change = _number(row, "perofShares")
            after = _number(row, "persharesPostevent")
            counterparty = _text(row, "nameOfLenderDebenture", "entityFavorShares")
            headline = _text(row, "reasonForEncumbrance", "typeOfEvent")
        else:
            action = _text(row, "tranType", "transactionType", "acqMode")
            side = _side(action)
            event_type = "INSIDER_BUY" if side == "BUY" else "INSIDER_SELL" if side == "SELL" else "INSIDER_TRANSACTION"
            event_date = _date(_text(row, "date", "transactionDate", "tradeDate"))
            published = _date(_text(row, "broadcastDate", "disclosureDate", "date"))
            quantity = _number(row, "quantity", "secAcq", "noOfSecurities")
            before = _number(row, "preTranHolding", "preHolding")
            change = None
            after = _number(row, "postTranHolding", "postHolding")
            counterparty = None
            headline = action
        if not symbol or not event_date:
            continue
        events.append(
            _event(
                source_key,
                result,
                row,
                source_record_id=_text(row, "mstrSeqNum", "seqNum", "smst_seq_id"),
                symbol=symbol.upper(),
                company=_text(row, "companyName"),
                event_type=event_type,
                side=_side(action),
                actor=actor,
                counterparty=counterparty,
                event_date=event_date,
                published_at=published,
                quantity=quantity,
                percent_before=before,
                percent_change=change,
                percent_after=after,
                headline=headline,
            )
        )
    return events


def _bse_insider_events(
    source_key: str, result: EndpointFetchResult, rows: list[dict[str, Any]]
) -> list[InstitutionalDisclosureEvent]:
    events: list[InstitutionalDisclosureEvent] = []
    for row in rows:
        action = _text(row, "TRAN_TYPE", "TRANSACTION_TYPE", "Acq_Sale")
        side = _side(action)
        event_date = _date(_text(row, "DATE", "DEAL_DATE", "TRANSACTION_DATE"))
        scrip_code = _text(row, "SCRIP_CD", "SCRIP_CODE", "BSECODE")
        if not scrip_code or not event_date:
            continue
        quantity = _number(row, "SEC_VAL", "QUANTITY", "NO_OF_SECURITIES")
        price = _number(row, "PRICE", "TRADE_PRICE")
        events.append(
            _event(
                source_key,
                result,
                row,
                source_record_id=_text(row, "NEWSID", "ID"),
                scrip_code=scrip_code,
                company=_text(row, "SCRIP_NAME", "COMPANY_NAME"),
                event_type="INSIDER_BUY" if side == "BUY" else "INSIDER_SELL" if side == "SELL" else "INSIDER_TRANSACTION",
                category=_text(row, "CATEGORY"),
                side=side,
                actor=_text(row, "ACQUIREE", "CLIENT_NAME", "PERSON_NAME"),
                event_date=event_date,
                published_at=_date(_text(row, "DISCLOSURE_DATE", "DATE")),
                quantity=quantity,
                price=price,
                notional=_number(row, "VALUE") or (
                    quantity * price if quantity is not None and price is not None else None
                ),
                percent_before=_number(row, "HOLDING_PRE", "PRE_HOLDING"),
                percent_after=_number(row, "HOLDING_POST", "POST_HOLDING"),
                headline=f"BSE insider transaction {side}",
            )
        )
    return events


def _buyback_events(
    source_key: str, result: EndpointFetchResult, rows: list[dict[str, Any]]
) -> list[InstitutionalDisclosureEvent]:
    events: list[InstitutionalDisclosureEvent] = []
    for row in rows:
        symbol = _text(row, "symbol", "Symbol", "SYMBOL")
        company = _text(row, "companyName", "CompanyName", "COMPANY_NAME")
        event_date = _date(
            _text(row, "date", "buyBackDate", "broadcastDate", "openDate", "recordDate")
        )
        if not (symbol or company) or not event_date:
            continue
        quantity = _number(row, "quantity", "noOfShares", "numberOfShares")
        price = _number(row, "price", "buybackPrice", "offerPrice")
        events.append(
            _event(
                source_key,
                result,
                row,
                source_record_id=_text(row, "id", "seqNum", "recordId"),
                symbol=symbol.upper() if symbol else None,
                company=company,
                event_type="BUYBACK_EXECUTION",
                category=_text(row, "buybackType", "type"),
                side="BUY",
                event_date=event_date,
                published_at=_date(_text(row, "broadcastDate", "date")),
                quantity=quantity,
                price=price,
                notional=_number(row, "value", "buybackValue") or (
                    quantity * price if quantity is not None and price is not None else None
                ),
                headline=_text(row, "description", "remarks") or "NSE daily buyback execution",
            )
        )
    return events


def _nse_pledge_events(
    source_key: str, result: EndpointFetchResult, rows: list[dict[str, Any]]
) -> list[InstitutionalDisclosureEvent]:
    events: list[InstitutionalDisclosureEvent] = []
    for row in rows:
        company = _text(row, "comName")
        event_date = _date(_text(row, "shp", "compBroadcastDate", "broadcastDt"))
        if not company or not event_date:
            continue
        events.append(
            _event(
                source_key,
                result,
                row,
                company=company,
                event_type="PLEDGE_SNAPSHOT",
                event_date=event_date,
                published_at=_date(_text(row, "broadcastDt")),
                promoter_holding_pct=_number(row, "percPromoterHolding"),
                pledge_shares=_number(row, "numSharesPledged", "noOfPledgeShare"),
                pledge_pct_promoter=_number(row, "percPromoterShares"),
                pledge_pct_total=_number(row, "percSharesPledged", "percTotShares"),
                headline="NSE promoter pledge snapshot",
            )
        )
    return events


def _shareholding_events(
    source_key: str, result: EndpointFetchResult, rows: list[dict[str, Any]]
) -> list[InstitutionalDisclosureEvent]:
    events: list[InstitutionalDisclosureEvent] = []
    for row in rows:
        symbol = _text(row, "symbol")
        event_date = _date(_text(row, "date"))
        if not symbol or not event_date:
            continue
        events.append(
            _event(
                source_key,
                result,
                row,
                source_record_id=_text(row, "recordId"),
                symbol=symbol.upper(),
                isin=_text(row, "isin"),
                company=_text(row, "name"),
                event_type="SHAREHOLDING_SNAPSHOT",
                event_date=event_date,
                published_at=_date(_text(row, "submissionDate", "broadcastDate")),
                promoter_holding_pct=_number(row, "pr_and_prgrp"),
                headline="Quarterly shareholding pattern",
                attachment_url=_text(row, "xbrl"),
                revision_status=_text(row, "revisedStatus", "revisedData"),
            )
        )
    return events


def _bse_pledge_events(
    source_key: str, result: EndpointFetchResult, rows: list[dict[str, Any]]
) -> list[InstitutionalDisclosureEvent]:
    events: list[InstitutionalDisclosureEvent] = []
    for row in rows:
        scrip_code = _text(row, "ScripCode")
        event_date = _date(_text(row, "MAxDate", "SHP_PulishedTime"))
        if not scrip_code or not event_date:
            continue
        events.append(
            _event(
                source_key,
                result,
                row,
                scrip_code=scrip_code,
                company=_text(row, "CompanyName"),
                event_type="PLEDGE_SNAPSHOT",
                event_date=event_date,
                published_at=_date(_text(row, "SHP_PulishedTime")),
                promoter_holding_pct=_number(row, "Percentage_TOTAL_PROMOTER_HOLDING"),
                pledge_shares=_number(row, "PROMOTEREncum_NoOfshares"),
                pledge_pct_promoter=_number(row, "PROMOTEREncum_Percof_PromoterShares"),
                pledge_pct_total=_number(row, "PROMOTEREncum_Percof_TotalShares"),
                headline="BSE promoter pledge snapshot",
            )
        )
    return events


def _bse_sast_events(
    source_key: str, result: EndpointFetchResult, rows: list[dict[str, Any]]
) -> list[InstitutionalDisclosureEvent]:
    events: list[InstitutionalDisclosureEvent] = []
    for row in rows:
        scrip_code = _text(row, "scrip_code")
        action = _text(row, "Acq_Sale")
        event_date = _date(_text(row, "Acquisition_date", "NEWDT"))
        if not scrip_code or not event_date:
            continue
        side = _side(action)
        events.append(
            _event(
                source_key,
                result,
                row,
                scrip_code=scrip_code,
                company=_text(row, "Company_Name"),
                event_type="SAST_ACQUISITION" if side == "BUY" else "SAST_DISPOSAL" if side == "SELL" else "SAST_CHANGE",
                category=_text(row, "flag"),
                side=side,
                actor=_text(row, "shareholdername"),
                event_date=event_date,
                published_at=_date(_text(row, "NEWDT")),
                quantity=_number(row, "Acq_sale_qty"),
                percent_change=_number(row, "Acq_sale_Pct"),
                percent_after=_number(row, "Acquisition_Pct_After", "Fld_TotDilPerAfterAcq"),
                headline=f"BSE SAST {action or 'change'}",
            )
        )
    return events


def _bse_deal_events(
    source_key: str, result: EndpointFetchResult, rows: list[dict[str, Any]]
) -> list[InstitutionalDisclosureEvent]:
    events: list[InstitutionalDisclosureEvent] = []
    event_type = "BLOCK_DEAL" if source_key == "bse_block_deals" else "BULK_DEAL"
    for row in rows:
        scrip_code = _text(row, "SCRIP_CODE")
        event_date = _date(_text(row, "DEAL_DATE"))
        side = _side(_text(row, "TRANSACTION_TYPE"))
        quantity = _number(row, "QUANTITY")
        price = _number(row, "PRICE")
        if not scrip_code or not event_date or side == "OTHER":
            continue
        events.append(
            _event(
                source_key,
                result,
                row,
                scrip_code=scrip_code,
                company=_text(row, "scripname"),
                event_type=event_type,
                side=side,
                actor=_text(row, "CLIENT_NAME"),
                event_date=event_date,
                published_at=event_date,
                quantity=quantity,
                price=price,
                notional=quantity * price if quantity is not None and price is not None else None,
                headline=f"{event_type.replace('_', ' ').title()} {side}",
            )
        )
    return events


NORMALIZERS: dict[
    str,
    tuple[tuple[str, ...], Callable[[str, EndpointFetchResult, list[dict[str, Any]]], list[InstitutionalDisclosureEvent]]],
] = {
    "nse_announcements": (("symbol", "an_dt"), _announcement_events),
    "bse_corporate_announcements": (("NEWSID", "DT_TM"), _announcement_events),
    "nse_regulation_29": (("symbol", "creditDateFrom"), _nse_regulation_events),
    "nse_regulation_31": (("symbol", "typeOfEvent"), _nse_regulation_events),
    "nse_pit": (("symbol",), _nse_regulation_events),
    "nse_tender_buyback": ((), _buyback_events),
    "nse_pledge": (("comName", "shp"), _nse_pledge_events),
    "nse_shareholding_pattern": (("symbol", "date"), _shareholding_events),
    "bse_insider_trading": ((), _bse_insider_events),
    "bse_pledge_data": (("ScripCode", "CompanyName"), _bse_pledge_events),
    "bse_sast": (("scrip_code", "Acquisition_date"), _bse_sast_events),
    "bse_bulk_deals": (("SCRIP_CODE", "DEAL_DATE"), _bse_deal_events),
    "bse_block_deals": (("SCRIP_CODE", "DEAL_DATE"), _bse_deal_events),
}


def _coerce_result(value: EndpointFetchResult | dict[str, Any]) -> EndpointFetchResult:
    return value if isinstance(value, EndpointFetchResult) else EndpointFetchResult.model_validate(value)


def _normalize_source(
    result: EndpointFetchResult,
) -> tuple[DisclosureSourceStatus, list[InstitutionalDisclosureEvent]]:
    if result.state == FetchState.NO_DATA_NOW:
        return DisclosureSourceStatus(
            endpoint_key=result.endpoint_key,
            fetch_state=result.state.value,
            parser_state="VALID_EMPTY",
            fetched_at=result.fetched_at,
            content_hash=result.content_hash,
            source_record_count=result.record_count,
            normalized_count=0,
            rejected_count=0,
            reason="The verified endpoint returned a valid empty response for this fetch.",
        ), []
    if result.state not in {FetchState.RAW_ARCHIVED, FetchState.STALE_FALLBACK}:
        return DisclosureSourceStatus(
            endpoint_key=result.endpoint_key,
            fetch_state=result.state.value,
            parser_state="FETCH_FAILED",
            fetched_at=result.fetched_at,
            content_hash=result.content_hash,
            source_record_count=result.record_count,
            normalized_count=0,
            rejected_count=0,
            reason=result.reason or "The source fetch did not produce an archived payload.",
        ), []
    contract = NORMALIZERS.get(result.endpoint_key)
    if contract is None:
        return DisclosureSourceStatus(
            endpoint_key=result.endpoint_key,
            fetch_state=result.state.value,
            parser_state="SCHEMA_MISMATCH",
            fetched_at=result.fetched_at,
            content_hash=result.content_hash,
            source_record_count=result.record_count,
            normalized_count=0,
            rejected_count=result.record_count,
            reason="No source-specific disclosure normalizer is registered.",
        ), []
    required, normalizer = contract
    rows = _rows(result.payload)
    if not rows:
        return DisclosureSourceStatus(
            endpoint_key=result.endpoint_key,
            fetch_state=result.state.value,
            parser_state="SCHEMA_MISMATCH",
            fetched_at=result.fetched_at,
            content_hash=result.content_hash,
            source_record_count=result.record_count,
            normalized_count=0,
            rejected_count=result.record_count,
            reason="Archived payload did not contain the expected row collection.",
        ), []
    schema_rows = [row for row in rows if all(key in row for key in required)]
    events = normalizer(result.endpoint_key, result, schema_rows)
    rejected = len(rows) - len(events)
    parser_state: ParserState = (
        "STALE_FALLBACK" if result.state == FetchState.STALE_FALLBACK else "STRUCTURED_OK"
    ) if events else "SCHEMA_MISMATCH"
    return DisclosureSourceStatus(
        endpoint_key=result.endpoint_key,
        fetch_state=result.state.value,
        parser_state=parser_state,
        fetched_at=result.fetched_at,
        content_hash=result.content_hash,
        source_record_count=result.record_count,
        normalized_count=len(events),
        rejected_count=rejected,
        reason=(
            "Rows were normalized from a stale cached artifact and cannot confirm current conditions."
            if parser_state == "STALE_FALLBACK"
            else "Source-specific fields were normalized with raw-row lineage; evidence remains research-only."
            if parser_state == "STRUCTURED_OK"
            else "Rows did not satisfy the source-specific schema or minimum identity/date fields."
        ),
    ), events


def build_disclosure_snapshot(
    results: list[EndpointFetchResult | dict[str, Any]],
) -> DisclosureNormalizationSnapshot:
    statuses: list[DisclosureSourceStatus] = []
    events: list[InstitutionalDisclosureEvent] = []
    seen: set[str] = set()
    for value in results:
        result = _coerce_result(value)
        if result.endpoint_key not in NORMALIZERS:
            continue
        status, normalized = _normalize_source(result)
        statuses.append(status)
        for event in normalized:
            if event.event_id not in seen:
                events.append(event)
                seen.add(event.event_id)
    has_structured = any(item.parser_state == "STRUCTURED_OK" for item in statuses)
    return DisclosureNormalizationSnapshot(
        run_id=str(uuid4()),
        normalized_at=datetime.now(UTC),
        state="RESEARCH_ONLY" if has_structured else "WAIT_SOURCE",
        sources=statuses,
        events=events,
        reason=(
            "Structured disclosure evidence is stored for research and cross-confirmation; it cannot independently unlock READY."
            if has_structured
            else "No fresh structured disclosure rows were available in this normalization run."
        ),
    )


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS institutional_disclosure_runs (
            run_id TEXT PRIMARY KEY,
            normalized_at TEXT NOT NULL,
            state TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            event_count INTEGER NOT NULL,
            reason TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS institutional_disclosure_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL REFERENCES institutional_disclosure_runs(run_id),
            endpoint_key TEXT NOT NULL,
            fetch_state TEXT NOT NULL,
            parser_state TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            content_hash TEXT,
            source_record_count INTEGER NOT NULL,
            normalized_count INTEGER NOT NULL,
            rejected_count INTEGER NOT NULL,
            reason TEXT NOT NULL,
            UNIQUE(run_id, endpoint_key)
        );
        CREATE TABLE IF NOT EXISTS institutional_disclosure_events (
            event_id TEXT PRIMARY KEY,
            source_key TEXT NOT NULL,
            source_content_hash TEXT,
            symbol TEXT,
            scrip_code TEXT,
            event_type TEXT NOT NULL,
            event_date TEXT,
            published_at TEXT,
            payload_json TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS institutional_disclosure_run_events (
            run_id TEXT NOT NULL REFERENCES institutional_disclosure_runs(run_id),
            event_id TEXT NOT NULL REFERENCES institutional_disclosure_events(event_id),
            PRIMARY KEY(run_id, event_id)
        );
        CREATE INDEX IF NOT EXISTS idx_disclosure_event_symbol
        ON institutional_disclosure_events(symbol, event_date DESC);
        CREATE INDEX IF NOT EXISTS idx_disclosure_event_scrip
        ON institutional_disclosure_events(scrip_code, event_date DESC);
        CREATE INDEX IF NOT EXISTS idx_disclosure_run_latest
        ON institutional_disclosure_runs(normalized_at DESC);
        """
    )


def save_disclosure_snapshot(
    snapshot: DisclosureNormalizationSnapshot, db_path: Path = DEFAULT_DB
) -> None:
    with _connect(db_path) as connection:
        _initialize(connection)
        connection.execute(
            """
            INSERT INTO institutional_disclosure_runs(
                run_id, normalized_at, state, source_count, event_count, reason
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.run_id,
                snapshot.normalized_at.isoformat(),
                snapshot.state,
                len(snapshot.sources),
                len(snapshot.events),
                snapshot.reason,
            ),
        )
        connection.executemany(
            """
            INSERT INTO institutional_disclosure_sources(
                run_id, endpoint_key, fetch_state, parser_state, fetched_at,
                content_hash, source_record_count, normalized_count,
                rejected_count, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot.run_id,
                    source.endpoint_key,
                    source.fetch_state,
                    source.parser_state,
                    source.fetched_at.isoformat(),
                    source.content_hash,
                    source.source_record_count,
                    source.normalized_count,
                    source.rejected_count,
                    source.reason,
                )
                for source in snapshot.sources
            ],
        )
        now = datetime.now(UTC).isoformat()
        for event in snapshot.events:
            payload = json.dumps(
                event.model_dump(mode="json", by_alias=True),
                ensure_ascii=True,
                separators=(",", ":"),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO institutional_disclosure_events(
                    event_id, source_key, source_content_hash, symbol, scrip_code,
                    event_type, event_date, published_at, payload_json, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.source_key,
                    event.source_content_hash,
                    event.symbol,
                    event.scrip_code,
                    event.event_type,
                    event.event_date,
                    event.published_at,
                    payload,
                    now,
                ),
            )
            connection.execute(
                "INSERT OR IGNORE INTO institutional_disclosure_run_events(run_id, event_id) VALUES (?, ?)",
                (snapshot.run_id, event.event_id),
            )


def normalize_and_save_disclosures(
    results: list[EndpointFetchResult | dict[str, Any]], db_path: Path = DEFAULT_DB
) -> DisclosureNormalizationSnapshot:
    snapshot = build_disclosure_snapshot(results)
    save_disclosure_snapshot(snapshot, db_path)
    return snapshot


def latest_disclosure_drilldown(
    *, symbol: str | None = None, limit: int = 100, db_path: Path = DEFAULT_DB
) -> DisclosureDrilldown:
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    clean_symbol = symbol.strip().upper() if symbol else None
    with _connect(db_path) as connection:
        _initialize(connection)
        run = connection.execute(
            "SELECT * FROM institutional_disclosure_runs ORDER BY normalized_at DESC LIMIT 1"
        ).fetchone()
        if run is None:
            return DisclosureDrilldown(
                run_id="NO_SNAPSHOT",
                normalized_at=datetime.now(UTC),
                state="WAIT_NO_SNAPSHOT",
                source_count=0,
                event_count=0,
                returned_count=0,
                reason="Run a corporate or extended-market source refresh to create the first normalized snapshot.",
            )
        source_rows = connection.execute(
            "SELECT * FROM institutional_disclosure_sources WHERE run_id = ? ORDER BY endpoint_key",
            (run["run_id"],),
        ).fetchall()
        sql = """
            SELECT event.payload_json
            FROM institutional_disclosure_run_events link
            JOIN institutional_disclosure_events event ON event.event_id = link.event_id
            WHERE link.run_id = ?
        """
        parameters: list[Any] = [run["run_id"]]
        if clean_symbol:
            sql += " AND UPPER(event.symbol) = ?"
            parameters.append(clean_symbol)
        sql += " ORDER BY COALESCE(event.published_at, event.event_date) DESC, event.event_id LIMIT ?"
        parameters.append(limit)
        event_rows = connection.execute(sql, parameters).fetchall()
    sources = [
        DisclosureSourceStatus(
            endpoint_key=row["endpoint_key"],
            fetch_state=row["fetch_state"],
            parser_state=row["parser_state"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            content_hash=row["content_hash"],
            source_record_count=row["source_record_count"],
            normalized_count=row["normalized_count"],
            rejected_count=row["rejected_count"],
            reason=row["reason"],
        )
        for row in source_rows
    ]
    events = [
        InstitutionalDisclosureEvent.model_validate_json(row["payload_json"])
        for row in event_rows
    ]
    return DisclosureDrilldown(
        run_id=run["run_id"],
        normalized_at=datetime.fromisoformat(run["normalized_at"]),
        state=run["state"],
        source_count=run["source_count"],
        event_count=run["event_count"],
        returned_count=len(events),
        sources=sources,
        events=events,
        reason=run["reason"],
    )
