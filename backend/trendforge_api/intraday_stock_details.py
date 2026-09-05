from __future__ import annotations

import csv
import io
import json
import math
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .institutional_sources import EndpointFetchResult, FetchState


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT_DIR / "data" / "trendforge_research.db"
FRESH_STATES = {FetchState.RAW_ARCHIVED, FetchState.NO_DATA_NOW}


def legacy_discovery_state(
    completeness: float,
    detail_score: float | None = None,
) -> Literal["WAIT_CONFIRMATION", "WAIT_SOURCE"]:
    """CROSS-014 / FUS-008: completeness only.

    ``detail_score`` is accepted only so callers cannot accidentally
    pass it as a positional state input. It is ignored.
    """
    _ = detail_score
    if completeness < 0.5:
        return "WAIT_SOURCE"
    return "WAIT_CONFIRMATION"

OI_BUCKETS = {
    "Rise-in-OI-Rise": "LONG_BUILDUP",
    "Rise-in-OI-Slide": "SHORT_BUILDUP",
    "Slide-in-OI-Rise": "SHORT_COVERING",
    "Slide-in-OI-Slide": "LONG_UNWINDING",
}
OI_POINTS = {
    "LONG_BUILDUP": 2.0,
    "SHORT_COVERING": 1.0,
    "SHORT_BUILDUP": -2.0,
    "LONG_UNWINDING": -1.0,
}


class IntradayStockDetailModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class IntradayStockDetailSource(IntradayStockDetailModel):
    endpoint_key: str
    state: str
    fetched_at: datetime
    record_count: int = Field(ge=0)
    from_cache: bool = False
    reason: str | None = None


class IntradayStockDetailCandidate(IntradayStockDetailModel):
    symbol: str
    state: Literal["WATCH_LONG", "WATCH_SHORT", "WAIT_CONFIRMATION", "WAIT_SOURCE"]
    direction_hint: Literal["BULLISH_EVIDENCE", "BEARISH_EVIDENCE", "MIXED"]
    detail_score: float = Field(ge=0, le=100)
    score_meaning: str = "EVIDENCE_STRENGTH_NOT_WIN_PROBABILITY"
    oi_bias_score: float = 0
    oi_signals: list[str] = Field(default_factory=list)
    active_option_volume: float = 0
    active_option_oi: float = 0
    active_future_volume: float = 0
    active_future_oi: float = 0
    top_active_contract: str | None = None
    preopen_gap_pct: float | None = None
    preopen_iep: float | None = None
    preopen_matched_qty: float | None = None
    block_deal_notional: float = 0
    bulk_deal_notional: float = 0
    derivatives_total_value: float = 0
    underlying_value: float | None = None
    last_price: float | None = None
    vwap: float | None = None
    quote_change_pct: float | None = None
    delivery_pct: float | None = None
    pcr: float | None = None
    max_pain: float | None = None
    support: float | None = None
    resistance: float | None = None
    atm_iv_ce: float | None = None
    atm_iv_pe: float | None = None
    derivative_contract_count: int = 0
    derivative_quote_oi: float = 0
    futures_basis: float | None = None
    futures_basis_pct: float | None = None
    futures_oi_change_pct: float | None = None
    most_active_derivative_value: float = 0
    insider_buy_value: float = 0
    insider_sell_value: float = 0
    insider_net_value: float = 0
    insider_disclosure_count: int = 0
    promoter_holding_pct: float | None = None
    public_holding_pct: float | None = None
    shareholding_date: str | None = None
    recent_financial_result: bool = False
    sector_index: str | None = None
    sector_side: Literal["GAINER", "LOSER", "UNKNOWN"] = "UNKNOWN"
    sector_change_pct: float | None = None
    stock_change_pct: float | None = None
    reasons: list[str] = Field(default_factory=list)
    source_keys: list[str] = Field(default_factory=list)
    can_unlock_ready: bool = False


class BSEOrderWinAnnouncement(IntradayStockDetailModel):
    scrip_code: str | None = None
    company: str | None = None
    headline: str | None = None
    news_date: str | None = None
    attachment_name: str | None = None
    attachment_url: str | None = None


class NSEBlockDeal(IntradayStockDetailModel):
    symbol: str | None = None
    client_name: str | None = None
    side: str | None = None
    quantity: float | None = None
    price: float | None = None
    notional: float | None = None


class IntradayStockDetailSnapshot(IntradayStockDetailModel):
    run_id: str
    fetched_at: datetime
    state: Literal["RESEARCH_ONLY", "WAIT_SOURCE"]
    source_completeness: float = Field(ge=0, le=1)
    sources: list[IntradayStockDetailSource] = Field(default_factory=list)
    candidates: list[IntradayStockDetailCandidate] = Field(default_factory=list)
    bse_order_wins: list[BSEOrderWinAnnouncement] = Field(default_factory=list)
    nse_block_deals: list[NSEBlockDeal] = Field(default_factory=list)
    nse_bulk_deals: list[NSEBlockDeal] = Field(default_factory=list)
    nsdl_fpi_table_count: int = 0
    market_context: dict[str, Any] = Field(default_factory=dict)
    can_unlock_ready: bool = False
    reason: str


def _number(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, "", "-"):
            continue
        try:
            parsed = float(str(value).replace(",", "").replace("%", ""))
        except ValueError:
            continue
        if math.isfinite(parsed):
            return parsed
    return None


def _text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _rows(payload: Any, *preferred_keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in (*preferred_keys, "data", "Data", "records", "rows", "Table"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
        if isinstance(value, dict):
            nested = _rows(value)
            if nested:
                return nested
    return []


def _result_map(results: list[EndpointFetchResult]) -> dict[str, EndpointFetchResult]:
    return {result.endpoint_key: result for result in results}


def _fresh(result: EndpointFetchResult | None) -> bool:
    return result is not None and result.state in FRESH_STATES


def _source(result: EndpointFetchResult) -> IntradayStockDetailSource:
    return IntradayStockDetailSource(
        endpoint_key=result.endpoint_key,
        state=result.state.value,
        fetched_at=result.fetched_at,
        record_count=result.record_count,
        from_cache=result.from_cache,
        reason=result.reason,
    )


def _is_stock_contract(row: dict[str, Any]) -> bool:
    instrument = _text(row, "instrument", "instrumentType", "contractType").lower()
    symbol = _text(row, "symbol", "underlying").upper()
    if symbol in {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}:
        return False
    return not instrument or "index" not in instrument


def _bucket_rows(payload: Any, bucket_key: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        value = payload.get(bucket_key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
        rows: list[dict[str, Any]] = []
        for nested in payload.values():
            rows.extend(_bucket_rows(nested, bucket_key))
        return rows
    if isinstance(payload, list):
        rows = []
        for nested in payload:
            rows.extend(_bucket_rows(nested, bucket_key))
        return rows
    return []


def _oi_contract_evidence(result: EndpointFetchResult | None) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    if not _fresh(result):
        return evidence
    for bucket_key, signal in OI_BUCKETS.items():
        for row in _bucket_rows(result.payload, bucket_key):
            if not _is_stock_contract(row):
                continue
            symbol = _text(row, "symbol", "underlying").upper()
            if not symbol:
                continue
            item = evidence.setdefault(
                symbol,
                {
                    "score": 0.0,
                    "signals": set(),
                    "contracts": 0,
                    "source_keys": set(),
                },
            )
            item["score"] += OI_POINTS[signal]
            item["signals"].add(signal)
            item["contracts"] += 1
            item["source_keys"].add("nse_oi_spurts_contracts")
    return evidence


def _active_derivatives(
    option_result: EndpointFetchResult | None,
    future_result: EndpointFetchResult | None,
) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for kind, result in (("option", option_result), ("future", future_result)):
        if not _fresh(result):
            continue
        for row in _rows(result.payload):
            if not _is_stock_contract(row):
                continue
            symbol = _text(row, "underlying", "symbol").upper()
            if not symbol:
                continue
            item = evidence.setdefault(
                symbol,
                {
                    "option_volume": 0.0,
                    "option_oi": 0.0,
                    "future_volume": 0.0,
                    "future_oi": 0.0,
                    "top_contract": None,
                    "top_volume": -1.0,
                    "source_keys": set(),
                },
            )
            volume = _number(row, "volume", "totTrdQty", "totalTradedVolume") or 0
            oi = _number(row, "openInterest", "latestOI", "oi") or 0
            if kind == "option":
                item["option_volume"] += volume
                item["option_oi"] += oi
                item["source_keys"].add("nse_live_equity_derivatives_stock_opt")
            else:
                item["future_volume"] += volume
                item["future_oi"] += oi
                item["source_keys"].add("nse_live_equity_derivatives_stock_fut")
            if volume > item["top_volume"]:
                item["top_volume"] = volume
                item["top_contract"] = _text(row, "contract", "identifier", "meta")
    return evidence


def _oi_underlying_evidence(result: EndpointFetchResult | None) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    if not _fresh(result):
        return evidence
    for row in _rows(result.payload):
        symbol = _text(row, "symbol", "underlying").upper()
        if not symbol:
            continue
        evidence[symbol] = {
            "total": _number(row, "total", "totalValue") or 0,
            "underlying_value": _number(row, "underlyingValue", "underlying_value"),
            "change_in_oi": _number(row, "changeInOI", "change_in_oi"),
            "source_keys": {"nse_oi_spurts"},
        }
    return evidence


def _sector_rankings(result: EndpointFetchResult | None) -> dict[str, str]:
    if not _fresh(result):
        return {}
    sectors: list[tuple[str, float]] = []
    for row in _rows(result.payload):
        key = _text(row, "key", "indexType", "category").upper()
        name = _text(row, "index", "indexName", "indexSymbol", "name").upper()
        change = _number(row, "percentChange", "pChange")
        if change is None or not name:
            continue
        if key == "SECTORAL INDICES" or name.startswith("NIFTY "):
            sectors.append((name, change))
    sectors.sort(key=lambda item: item[1], reverse=True)
    selected: dict[str, str] = {}
    for name, _ in sectors[:3]:
        selected[name] = "GAINER"
    for name, _ in sectors[-3:]:
        selected.setdefault(name, "LOSER")
    return selected


def _sector_name_from_url(url: str) -> str | None:
    query = parse_qs(urlparse(url).query)
    values = query.get("index")
    return values[0].upper() if values else None


def _sector_constituents(
    results: list[EndpointFetchResult], sector_sides: dict[str, str]
) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for result in results:
        if result.endpoint_key != "nse_sector_constituents" or not _fresh(result):
            continue
        sector_index = _sector_name_from_url(result.url) or "UNKNOWN"
        sector_side = sector_sides.get(sector_index, "UNKNOWN")
        sector_change = None
        for idx, row in enumerate(_rows(result.payload)):
            symbol = _text(row, "symbol").upper()
            if idx == 0 and not symbol:
                sector_change = _number(row, "pChange", "percentChange")
                continue
            if not symbol:
                continue
            evidence[symbol] = {
                "sector_index": sector_index,
                "sector_side": sector_side,
                "sector_change": sector_change,
                "stock_change": _number(row, "pChange", "percentChange"),
                "source_keys": {"nse_sector_constituents"},
            }
    return evidence


def _preopen_evidence(result: EndpointFetchResult | None) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    if not _fresh(result):
        return evidence
    for row in _rows(result.payload):
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else row
        detail = row.get("detail") if isinstance(row.get("detail"), dict) else {}
        symbol = _text(meta, "symbol", "Symbol").upper()
        if not symbol:
            continue
        iep = _number(meta, "iep", "indicativePrice", "lastPrice", "finalPrice")
        prev_close = _number(meta, "previousClose", "prevClose", "previous_close")
        gap_pct = _number(meta, "pChange", "changePct", "perChange")
        if gap_pct is None and iep is not None and prev_close:
            gap_pct = round(((iep - prev_close) / prev_close) * 100, 2)
        evidence[symbol] = {
            "gap_pct": gap_pct,
            "iep": iep,
            "matched_qty": _number(meta, "finalQuantity", "totalTradedVolume", "quantity") or _number(detail, "preOpenMarket", "totalBuyQuantity"),
            "source_keys": {"nse_preopen_fo"},
        }
    return evidence


def _nse_block_deal_rows(result: EndpointFetchResult | None) -> list[NSEBlockDeal]:
    if not _fresh(result):
        return []
    rows = _rows(result.payload)
    deals: list[NSEBlockDeal] = []
    for row in rows:
        symbol = _text(row, "symbol", "Symbol", "securityName").upper()
        quantity = _number(row, "quantity", "qty", "Quantity")
        price = _number(row, "tradePrice", "price", "watp", "TradePrice")
        notional = quantity * price if quantity and price else _number(row, "value", "notional")
        deals.append(
            NSEBlockDeal(
                symbol=symbol or None,
                client_name=_text(row, "clientName", "name", "ClientName") or None,
                side=_text(row, "buySell", "side", "BuySell") or None,
                quantity=quantity,
                price=price,
                notional=notional,
            )
        )
    return deals


def _nse_bulk_deal_csv_rows(result: EndpointFetchResult | None) -> list[NSEBlockDeal]:
    if not _fresh(result) or not isinstance(result.payload, str):
        return []
    deals: list[NSEBlockDeal] = []
    reader = csv.DictReader(io.StringIO(result.payload))
    for row in reader:
        symbol = _text(row, "Symbol").upper()
        quantity = _number(row, "Quantity Traded")
        price = _number(row, "Trade Price / Wght. Avg. Price")
        notional = quantity * price if quantity and price else None
        deals.append(
            NSEBlockDeal(
                symbol=symbol or None,
                client_name=_text(row, "Client Name") or None,
                side=_text(row, "Buy/Sell") or None,
                quantity=quantity,
                price=price,
                notional=notional,
            )
        )
    return deals


def _block_deal_evidence(block_deals: list[NSEBlockDeal]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for deal in block_deals:
        if not deal.symbol:
            continue
        item = evidence.setdefault(
            deal.symbol,
            {"notional": 0.0, "source_keys": {"nse_block_deal"}},
        )
        item["notional"] += deal.notional or 0
    return evidence


def _bulk_deal_evidence(bulk_deals: list[NSEBlockDeal]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for deal in bulk_deals:
        if not deal.symbol:
            continue
        item = evidence.setdefault(
            deal.symbol,
            {"notional": 0.0, "source_keys": {"nse_bulk_deals_today_csv"}},
        )
        item["notional"] += deal.notional or 0
    return evidence


def _most_active_underlying_evidence(result: EndpointFetchResult | None) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    if not _fresh(result):
        return evidence
    for row in _rows(result.payload):
        symbol = _text(row, "symbol", "underlying").upper()
        if not symbol or symbol in {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}:
            continue
        evidence[symbol] = {
            "total": _number(row, "totTurnover", "total", "totalValue", "turnover", "value") or 0,
            "volume": _number(row, "totVolume", "volume", "contracts") or 0,
            "source_keys": {"nse_most_active_underlying"},
        }
    return evidence


def _variation_count(payload: Any, section_key: str) -> int:
    if not isinstance(payload, dict):
        return 0
    section = payload.get(section_key)
    if isinstance(section, dict):
        data = section.get("data")
        if isinstance(data, list):
            return len(data)
    if isinstance(section, list):
        return len(section)
    return 0


def _index_derivative_context(results: dict[str, EndpointFetchResult]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    endpoint_labels = {
        "nse_live_equity_derivatives_index_opt": "niftyIndexOption",
        "nse_live_equity_derivatives_index_fut": "niftyIndexFuture",
        "nse_live_equity_derivatives_banknifty_opt": "bankNiftyIndexOption",
        "nse_live_equity_derivatives_banknifty_fut": "bankNiftyIndexFuture",
    }
    for endpoint_key, label in endpoint_labels.items():
        result = results.get(endpoint_key)
        if not _fresh(result):
            continue
        rows = _rows(result.payload)
        total_volume = 0.0
        total_oi = 0.0
        for row in rows:
            total_volume += _number(
                row,
                "volume",
                "numberOfContractsTraded",
                "totalTradedVolume",
                "totTrdQty",
            ) or 0.0
            total_oi += _number(row, "openInterest", "latestOI", "oi") or 0.0
        context[f"{label}RecordCount"] = len(rows)
        context[f"{label}Volume"] = total_volume
        context[f"{label}OpenInterest"] = total_oi
    return context


def _market_context(results: dict[str, EndpointFetchResult]) -> dict[str, Any]:
    gainers = results.get("nse_variations_gainers")
    losers = results.get("nse_variations_loosers")
    context: dict[str, Any] = {}
    if _fresh(gainers):
        context["cashGainers"] = _variation_count(gainers.payload, "allSec")
        context["foGainers"] = _variation_count(gainers.payload, "FOSec")
    if _fresh(losers):
        context["cashLosers"] = _variation_count(losers.payload, "allSec")
        context["foLosers"] = _variation_count(losers.payload, "FOSec")
    turnover = results.get("nse_market_turnover")
    if _fresh(turnover):
        context["marketTurnoverRecordCount"] = turnover.record_count
    most_active = results.get("nse_most_active_underlying")
    if _fresh(most_active):
        context["mostActiveUnderlyingRecordCount"] = most_active.record_count
    financial = results.get("nse_financial_results")
    if _fresh(financial):
        context["financialResultRecordCount"] = financial.record_count
    nsdl_daily = results.get("nsdl_fpi_daily_reportdetail")
    if _fresh(nsdl_daily):
        context["nsdlFpiDailyTableCount"] = _nsdl_table_count(nsdl_daily)
    nsdl_fortnightly = results.get("nsdl_fpi_fortnightly")
    if _fresh(nsdl_fortnightly):
        context["nsdlFpiFortnightlyTableCount"] = _nsdl_table_count(nsdl_fortnightly)
    context.update(_index_derivative_context(results))
    return context


def _financial_result_evidence(result: EndpointFetchResult | None) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    if not _fresh(result):
        return evidence
    for row in _rows(result.payload):
        symbol = _text(row, "symbol", "sym", "companySymbol").upper()
        if not symbol:
            continue
        evidence[symbol] = {
            "recent_result": True,
            "result_date": _text(row, "toDate", "periodEnded", "broadcastDate", "xbrlFilingDate"),
            "source_keys": {"nse_financial_results"},
        }
    return evidence


def _symbol_from_url(url: str) -> str | None:
    query = parse_qs(urlparse(url).query)
    values = query.get("symbol")
    return values[0].upper() if values else None


def _quote_evidence(results: list[EndpointFetchResult]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for result in results:
        if result.endpoint_key != "nse_quote_equity" or not _fresh(result):
            continue
        if not isinstance(result.payload, dict):
            continue
        symbol = _symbol_from_url(result.url)
        price_info = result.payload.get("priceInfo") or {}
        security_info = result.payload.get("securityInfo") or {}
        if symbol:
            evidence[symbol] = {
                "last_price": _number(price_info, "lastPrice"),
                "change_pct": _number(price_info, "pChange"),
                "vwap": _number(price_info, "vwap"),
                "upper_band": _number(price_info, "upperCP"),
                "lower_band": _number(price_info, "lowerCP"),
                "fno": str(security_info.get("derivatives", "")).upper() == "YES",
                "source_keys": {"nse_quote_equity"},
            }
    return evidence


def _trade_info_evidence(results: list[EndpointFetchResult]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for result in results:
        if result.endpoint_key != "nse_quote_equity_trade_info" or not _fresh(result):
            continue
        if not isinstance(result.payload, dict):
            continue
        symbol = _symbol_from_url(result.url)
        depth = result.payload.get("marketDeptOrderBook") or {}
        trade_info = depth.get("tradeInfo") or {}
        delivery = result.payload.get("securityWiseDP") or {}
        delivery_qty = _number(delivery, "deliveryQuantity")
        traded_qty = _number(delivery, "quantityTraded")
        delivery_pct = _number(delivery, "deliveryToTradedQuantity")
        if delivery_pct is None and delivery_qty and traded_qty:
            delivery_pct = round(100 * delivery_qty / traded_qty, 2)
        if symbol:
            evidence[symbol] = {
                "delivery_pct": delivery_pct,
                "delivery_qty": delivery_qty,
                "traded_qty": traded_qty,
                "total_buy_qty": _number(depth, "totalBuyQuantity"),
                "total_sell_qty": _number(depth, "totalSellQuantity"),
                "turnover_lakh": _number(trade_info, "totalTradedValue"),
                "source_keys": {"nse_quote_equity_trade_info"},
            }
    return evidence


def _option_chain_evidence(results: list[EndpointFetchResult]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for result in results:
        if result.endpoint_key != "nse_option_chain_equity" or not _fresh(result):
            continue
        symbol = _symbol_from_url(result.url)
        if not symbol or not isinstance(result.payload, dict):
            continue
        records = result.payload.get("records") or result.payload.get("data") or {}
        if not isinstance(records, dict):
            continue
        rows = records.get("data")
        if not isinstance(rows, list):
            rows = _rows(result.payload)
        expiries = records.get("expiryDates") or []
        expiry = expiries[0] if expiries else None
        spot = _number(records, "underlyingValue")
        chain: list[dict[str, float | None]] = []
        ce_oi_total = 0.0
        pe_oi_total = 0.0
        for row in rows:
            if not isinstance(row, dict):
                continue
            if expiry and _text(row, "expiryDate") != expiry:
                continue
            ce = row.get("CE") if isinstance(row.get("CE"), dict) else {}
            pe = row.get("PE") if isinstance(row.get("PE"), dict) else {}
            strike = _number(row, "strikePrice")
            if strike is None:
                continue
            ce_oi = _number(ce, "openInterest") or 0
            pe_oi = _number(pe, "openInterest") or 0
            ce_oi_total += ce_oi
            pe_oi_total += pe_oi
            chain.append(
                {
                    "strike": strike,
                    "ce_oi": ce_oi,
                    "pe_oi": pe_oi,
                    "ce_iv": _number(ce, "impliedVolatility"),
                    "pe_iv": _number(pe, "impliedVolatility"),
                }
            )
        if not chain:
            continue

        def pain(strike: float) -> float:
            return sum(
                max(0, strike - (row["strike"] or 0)) * (row["ce_oi"] or 0)
                + max(0, (row["strike"] or 0) - strike) * (row["pe_oi"] or 0)
                for row in chain
            )

        support = max(chain, key=lambda row: row["pe_oi"] or 0)["strike"]
        resistance = max(chain, key=lambda row: row["ce_oi"] or 0)["strike"]
        max_pain = min((row["strike"] for row in chain if row["strike"] is not None), key=pain)
        atm = min(chain, key=lambda row: abs((row["strike"] or 0) - spot)) if spot else None
        evidence[symbol] = {
            "spot": spot,
            "pcr": round(pe_oi_total / ce_oi_total, 3) if ce_oi_total else None,
            "max_pain": max_pain,
            "support": support,
            "resistance": resistance,
            "total_ce_oi": ce_oi_total,
            "total_pe_oi": pe_oi_total,
            "atm_iv_ce": atm.get("ce_iv") if atm else None,
            "atm_iv_pe": atm.get("pe_iv") if atm else None,
            "source_keys": {"nse_option_chain_equity"},
        }
    return evidence


def _derivative_quote_evidence(results: list[EndpointFetchResult]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for result in results:
        if result.endpoint_key != "nse_quote_derivative" or not _fresh(result):
            continue
        symbol = _symbol_from_url(result.url)
        if not symbol or not isinstance(result.payload, dict):
            continue
        contracts = result.payload.get("stocks") or []
        underlying = _number(result.payload, "underlyingValue")
        total_oi = 0.0
        contract_count = 0
        nearest_future_price = None
        nearest_oi_change = None
        for stock in contracts:
            if not isinstance(stock, dict):
                continue
            metadata = stock.get("metadata") if isinstance(stock.get("metadata"), dict) else {}
            depth = stock.get("marketDeptOrderBook") or {}
            trade_info = depth.get("tradeInfo") or {}
            total_oi += _number(trade_info, "openInterest") or 0
            contract_count += 1
            instrument_type = _text(metadata, "instrumentType").lower()
            if nearest_future_price is None and "fut" in instrument_type:
                nearest_future_price = _number(metadata, "lastPrice")
                nearest_oi_change = _number(trade_info, "pchangeinOpenInterest", "pChangeinOpenInterest")
                if underlying is None:
                    underlying = _number(metadata, "underlyingValue")
        basis = nearest_future_price - underlying if nearest_future_price is not None and underlying else None
        evidence[symbol] = {
            "contract_count": contract_count,
            "total_oi": total_oi,
            "futures_basis": basis,
            "futures_basis_pct": round((basis / underlying) * 100, 3) if basis is not None and underlying else None,
            "futures_oi_change_pct": nearest_oi_change,
            "source_keys": {"nse_quote_derivative"},
        }
    return evidence


def _pit_evidence(results: list[EndpointFetchResult]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for result in results:
        if result.endpoint_key not in {"nse_pit_symbol", "nse_pit_annual"} or not _fresh(result):
            continue
        fallback_symbol = _symbol_from_url(result.url)
        for row in _rows(result.payload):
            symbol = _text(row, "symbol", "sym").upper() or fallback_symbol
            if not symbol:
                continue
            mode = _text(row, "tdpTransactionType", "acqMode", "transactionType", "mode").lower()
            value = _number(row, "secVal", "valueOfSecurities", "value") or 0
            item = evidence.setdefault(
                symbol,
                {
                    "buy_value": 0.0,
                    "sell_value": 0.0,
                    "count": 0,
                    "source_keys": set(),
                },
            )
            item["count"] += 1
            item["source_keys"].add(result.endpoint_key)
            if any(token in mode for token in ("buy", "acquisition", "purchase", "acq")):
                item["buy_value"] += value
            elif any(token in mode for token in ("sell", "sale", "disposal", "dispose")):
                item["sell_value"] += value
    for item in evidence.values():
        item["net_value"] = item["buy_value"] - item["sell_value"]
    return evidence


def _shareholding_evidence(results: list[EndpointFetchResult]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for result in results:
        if result.endpoint_key != "nse_shareholding_pattern" or not _fresh(result):
            continue
        fallback_symbol = _symbol_from_url(result.url)
        rows = _rows(result.payload)
        if not rows:
            continue
        latest = rows[0]
        symbol = _text(latest, "symbol", "sym").upper() or fallback_symbol
        if not symbol:
            continue
        evidence[symbol] = {
            "promoter_holding_pct": _number(
                latest, "pr_and_prgrp", "promoter", "promoterHolding"
            ),
            "public_holding_pct": _number(
                latest, "public_val", "public", "publicHolding"
            ),
            "shareholding_date": _text(latest, "date", "submissionDate", "broadcastDate")
            or None,
            "company": _text(latest, "name", "companyName"),
            "xbrl": _text(latest, "xbrl") or None,
            "source_keys": {"nse_shareholding_pattern"},
        }
    return evidence


def _bse_order_wins(result: EndpointFetchResult | None) -> list[BSEOrderWinAnnouncement]:
    if not _fresh(result):
        return []
    announcements: list[BSEOrderWinAnnouncement] = []
    for row in _rows(result.payload):
        attachment = _text(row, "ATTACHMENTNAME", "attachmentName")
        announcements.append(
            BSEOrderWinAnnouncement(
                scrip_code=_text(row, "SCRIP_CD", "scripCode") or None,
                company=_text(row, "SLONGNAME", "companyName", "COMPANYNAME") or None,
                headline=_text(row, "NEWSSUB", "HEADLINE", "NewsSub") or None,
                news_date=_text(row, "NEWS_DT", "DissemDT", "News_submission_dt") or None,
                attachment_name=attachment or None,
                attachment_url=(
                    f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment}"
                    if attachment
                    else None
                ),
            )
        )
    return announcements


def _nsdl_table_count(result: EndpointFetchResult | None) -> int:
    if not _fresh(result) or not isinstance(result.payload, str):
        return 0
    return result.payload.lower().count("<table")


def build_intraday_stock_detail_snapshot(
    results: list[EndpointFetchResult], *, limit: int = 25
) -> IntradayStockDetailSnapshot:
    mapped = _result_map(results)
    sources = [_source(result) for result in results]
    fresh_count = sum(1 for result in results if _fresh(result))
    completeness = fresh_count / len(results) if results else 0

    oi_contracts = _oi_contract_evidence(mapped.get("nse_oi_spurts_contracts"))
    derivatives = _active_derivatives(
        mapped.get("nse_live_equity_derivatives_stock_opt"),
        mapped.get("nse_live_equity_derivatives_stock_fut"),
    )
    underlyings = _oi_underlying_evidence(mapped.get("nse_oi_spurts"))
    sector_sides = _sector_rankings(mapped.get("nse_all_indices"))
    sector_rows = _sector_constituents(results, sector_sides)
    preopen = _preopen_evidence(mapped.get("nse_preopen_fo"))
    nse_block_deals = _nse_block_deal_rows(mapped.get("nse_block_deal"))
    nse_bulk_deals = _nse_bulk_deal_csv_rows(mapped.get("nse_bulk_deals_today_csv"))
    block_deals = _block_deal_evidence(nse_block_deals)
    bulk_deals = _bulk_deal_evidence(nse_bulk_deals)
    most_active = _most_active_underlying_evidence(mapped.get("nse_most_active_underlying"))
    quote = _quote_evidence(results)
    trade = _trade_info_evidence(results)
    option_chain = _option_chain_evidence(results)
    derivative_quote = _derivative_quote_evidence(results)
    pit = _pit_evidence(results)
    shareholding = _shareholding_evidence(results)
    financial_results = _financial_result_evidence(mapped.get("nse_financial_results"))
    market_context = _market_context(mapped)

    symbols = sorted(
        set(oi_contracts)
        | set(derivatives)
        | set(underlyings)
        | set(sector_rows)
        | set(preopen)
        | set(block_deals)
        | set(bulk_deals)
        | set(most_active)
        | set(quote)
        | set(trade)
        | set(option_chain)
        | set(derivative_quote)
        | set(pit)
        | set(shareholding)
        | set(financial_results)
    )
    candidates: list[IntradayStockDetailCandidate] = []
    for symbol in symbols:
        oi = oi_contracts.get(symbol, {})
        drv = derivatives.get(symbol, {})
        und = underlyings.get(symbol, {})
        sec = sector_rows.get(symbol, {})
        pre = preopen.get(symbol, {})
        block = block_deals.get(symbol, {})
        bulk = bulk_deals.get(symbol, {})
        active = most_active.get(symbol, {})
        qte = quote.get(symbol, {})
        trd = trade.get(symbol, {})
        opt = option_chain.get(symbol, {})
        fut = derivative_quote.get(symbol, {})
        insider = pit.get(symbol, {})
        ownership = shareholding.get(symbol, {})
        fin = financial_results.get(symbol, {})
        oi_bias = float(oi.get("score", 0))
        activity = (
            min((drv.get("option_volume", 0) or 0) / 10_000, 12)
            + min((drv.get("future_volume", 0) or 0) / 10_000, 10)
            + min((und.get("total", 0) or 0) / 10_000, 12)
            + min((active.get("total", 0) or 0) / 10_000, 8)
        )
        sector_score = 8 if sec.get("sector_side") == "GAINER" else -8 if sec.get("sector_side") == "LOSER" else 0
        preopen_score = 6 if abs(pre.get("gap_pct") or 0) >= 2 else 3 if abs(pre.get("gap_pct") or 0) >= 1 else 0
        block_score = 7 if (block.get("notional") or 0) > 0 else 0
        bulk_score = 5 if (bulk.get("notional") or 0) > 0 else 0
        quote_score = 0.0
        if qte.get("last_price") is not None and qte.get("vwap") is not None:
            quote_score += 5 if qte["last_price"] > qte["vwap"] else -3
        if trd.get("delivery_pct") is not None:
            quote_score += 6 if trd["delivery_pct"] >= 60 else 3 if trd["delivery_pct"] >= 40 else 0
        if opt.get("pcr") is not None:
            quote_score += 4 if opt["pcr"] > 1.2 else -4 if opt["pcr"] < 0.7 else 0
        if fut.get("futures_basis_pct") is not None:
            quote_score += 2 if fut["futures_basis_pct"] > 0.2 else -2 if fut["futures_basis_pct"] < -0.2 else 0
        if fut.get("futures_oi_change_pct") is not None and qte.get("change_pct") is not None:
            if qte["change_pct"] > 0 and fut["futures_oi_change_pct"] > 3:
                quote_score += 5
            elif qte["change_pct"] < 0 and fut["futures_oi_change_pct"] > 3:
                quote_score -= 5
        insider_score = 6 if (insider.get("net_value") or 0) > 0 else -4 if (insider.get("net_value") or 0) < 0 else 0
        result_score = 2 if fin.get("recent_result") else 0
        breadth_multiplier = 1.0
        if (
            market_context.get("cashLosers", 0)
            and market_context.get("cashGainers", 0)
            and market_context["cashLosers"] > 2 * market_context["cashGainers"]
        ):
            breadth_multiplier = 0.5
        raw_score = (
            40
            + (oi_bias * 8)
            + activity
            + sector_score
            + preopen_score
            + block_score
            + bulk_score
            + quote_score
            + insider_score
            + result_score
        ) * breadth_multiplier
        score = max(0.0, min(100.0, raw_score))
        gap = pre.get("gap_pct")
        gap_points = 1 if (gap or 0) > 0 else -1 if (gap or 0) < 0 else 0
        direction_points = oi_bias + (1 if sector_score > 0 else -1 if sector_score < 0 else 0) + gap_points
        direction = (
            "BULLISH_EVIDENCE"
            if direction_points > 1
            else "BEARISH_EVIDENCE"
            if direction_points < -1
            else "MIXED"
        )
        # CROSS-014 / FUS-008: detail_score may sort the discovery queue only.
        # Completeness owns the wait ceiling. Direction stays a hint, not state.
        state = legacy_discovery_state(completeness)

        reasons: list[str] = []
        if oi.get("signals"):
            reasons.append("OI_CONTRACT_BUCKETS:" + ",".join(sorted(oi["signals"])))
        if drv:
            reasons.append("ACTIVE_DERIVATIVES_PRESENT")
        if und:
            reasons.append("HIGH_DERIVATIVE_VALUE_CONTEXT")
        if sec:
            reasons.append(f"SECTOR_{sec.get('sector_side', 'UNKNOWN')}")
        if pre:
            reasons.append("PREOPEN_FO_GAP_AVAILABLE")
        if block:
            reasons.append("NSE_BLOCK_DEAL_PRESENT")
        if bulk:
            reasons.append("NSE_BULK_DEAL_PRESENT")
        if active:
            reasons.append("MOST_ACTIVE_DERIVATIVE_UNDERLYING")
        if qte:
            reasons.append("QUOTE_EQUITY_AVAILABLE")
        if trd:
            reasons.append("TRADE_INFO_DELIVERY_AVAILABLE")
        if opt:
            reasons.append("OPTION_CHAIN_METRICS_AVAILABLE")
        if fut:
            reasons.append("DERIVATIVE_QUOTE_AVAILABLE")
        if insider:
            reasons.append("PIT_INSIDER_ACTIVITY_AVAILABLE")
        if ownership:
            reasons.append("NSE_SHAREHOLDING_PATTERN_AVAILABLE")
        if fin:
            reasons.append("RECENT_FINANCIAL_RESULT_AVAILABLE")
        if breadth_multiplier < 1:
            reasons.append("WEAK_CASH_BREADTH_SCORE_HALVED")

        source_keys = sorted(
            set(oi.get("source_keys", set()))
            | set(drv.get("source_keys", set()))
            | set(und.get("source_keys", set()))
            | set(sec.get("source_keys", set()))
            | set(pre.get("source_keys", set()))
            | set(block.get("source_keys", set()))
            | set(bulk.get("source_keys", set()))
            | set(active.get("source_keys", set()))
            | set(qte.get("source_keys", set()))
            | set(trd.get("source_keys", set()))
            | set(opt.get("source_keys", set()))
            | set(fut.get("source_keys", set()))
            | set(insider.get("source_keys", set()))
            | set(ownership.get("source_keys", set()))
            | set(fin.get("source_keys", set()))
        )
        candidates.append(
            IntradayStockDetailCandidate(
                symbol=symbol,
                state=state,
                direction_hint=direction,
                detail_score=round(score, 2),
                oi_bias_score=round(oi_bias, 2),
                oi_signals=sorted(oi.get("signals", [])),
                active_option_volume=float(drv.get("option_volume", 0) or 0),
                active_option_oi=float(drv.get("option_oi", 0) or 0),
                active_future_volume=float(drv.get("future_volume", 0) or 0),
                active_future_oi=float(drv.get("future_oi", 0) or 0),
                top_active_contract=drv.get("top_contract"),
                preopen_gap_pct=pre.get("gap_pct"),
                preopen_iep=pre.get("iep"),
                preopen_matched_qty=pre.get("matched_qty"),
                block_deal_notional=float(block.get("notional", 0) or 0),
                bulk_deal_notional=float(bulk.get("notional", 0) or 0),
                derivatives_total_value=float(und.get("total", 0) or 0),
                underlying_value=und.get("underlying_value"),
                last_price=qte.get("last_price"),
                vwap=qte.get("vwap"),
                quote_change_pct=qte.get("change_pct"),
                delivery_pct=trd.get("delivery_pct"),
                pcr=opt.get("pcr"),
                max_pain=opt.get("max_pain"),
                support=opt.get("support"),
                resistance=opt.get("resistance"),
                atm_iv_ce=opt.get("atm_iv_ce"),
                atm_iv_pe=opt.get("atm_iv_pe"),
                derivative_contract_count=int(fut.get("contract_count", 0) or 0),
                derivative_quote_oi=float(fut.get("total_oi", 0) or 0),
                futures_basis=fut.get("futures_basis"),
                futures_basis_pct=fut.get("futures_basis_pct"),
                futures_oi_change_pct=fut.get("futures_oi_change_pct"),
                most_active_derivative_value=float(active.get("total", 0) or 0),
                insider_buy_value=float(insider.get("buy_value", 0) or 0),
                insider_sell_value=float(insider.get("sell_value", 0) or 0),
                insider_net_value=float(insider.get("net_value", 0) or 0),
                insider_disclosure_count=int(insider.get("count", 0) or 0),
                promoter_holding_pct=ownership.get("promoter_holding_pct"),
                public_holding_pct=ownership.get("public_holding_pct"),
                shareholding_date=ownership.get("shareholding_date"),
                recent_financial_result=bool(fin.get("recent_result")),
                sector_index=sec.get("sector_index"),
                sector_side=sec.get("sector_side", "UNKNOWN"),
                sector_change_pct=sec.get("sector_change"),
                stock_change_pct=sec.get("stock_change"),
                reasons=reasons,
                source_keys=source_keys,
            )
        )

    candidates.sort(key=lambda item: item.detail_score, reverse=True)
    state = "RESEARCH_ONLY" if fresh_count else "WAIT_SOURCE"
    return IntradayStockDetailSnapshot(
        run_id=str(uuid4()),
        fetched_at=datetime.now(UTC),
        state=state,
        source_completeness=round(completeness, 4),
        sources=sources,
        candidates=candidates[:limit],
        bse_order_wins=_bse_order_wins(mapped.get("bse_order_win_announcements")),
        nse_block_deals=nse_block_deals,
        nse_bulk_deals=nse_bulk_deals,
        nsdl_fpi_table_count=_nsdl_table_count(
            mapped.get("nsdl_fpi_daily_reportdetail")
        )
        + _nsdl_table_count(mapped.get("nsdl_fpi_fortnightly")),
        market_context=market_context,
        reason=(
            "Research-only stock-detail evidence; cannot unlock READY without price, freshness, and gate confirmation."
            if fresh_count
            else "No fresh intraday stock-detail source snapshots."
        ),
    )


def save_intraday_stock_detail_snapshot(
    snapshot: IntradayStockDetailSnapshot, db_path: Path = DEFAULT_DB
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS intraday_stock_detail_runs (
                run_id TEXT PRIMARY KEY,
                fetched_at TEXT NOT NULL,
                state TEXT NOT NULL,
                source_completeness REAL NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS intraday_stock_detail_candidates (
                run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                state TEXT NOT NULL,
                direction_hint TEXT NOT NULL,
                detail_score REAL NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY(run_id, symbol)
            )
            """
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO intraday_stock_detail_runs(
                run_id, fetched_at, state, source_completeness, payload_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                snapshot.run_id,
                snapshot.fetched_at.isoformat(),
                snapshot.state,
                snapshot.source_completeness,
                json.dumps(snapshot.model_dump(mode="json", by_alias=True), sort_keys=True),
            ),
        )
        for candidate in snapshot.candidates:
            connection.execute(
                """
                INSERT OR REPLACE INTO intraday_stock_detail_candidates(
                    run_id, symbol, state, direction_hint, detail_score, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.run_id,
                    candidate.symbol,
                    candidate.state,
                    candidate.direction_hint,
                    candidate.detail_score,
                    json.dumps(candidate.model_dump(mode="json", by_alias=True), sort_keys=True),
                ),
            )
