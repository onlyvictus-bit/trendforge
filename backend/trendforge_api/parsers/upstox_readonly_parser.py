"""Pure normalizers for Upstox free read-only Analytics API responses.

These parsers never fetch, authenticate, place orders, or infer missing values.
The token is handled by ``AsyncEndpointClient`` and is never present here.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .common import decode_bytes, parse_date_value, source_result


SOURCE_SCOPE = "FREE_CREDENTIALED_READ_ONLY_INFORMATIONAL"


def _payload(content: bytes) -> tuple[Any, str | None]:
    try:
        payload = json.loads(decode_bytes(content))
    except json.JSONDecodeError:
        return None, "Upstox response is not JSON."
    if not isinstance(payload, dict):
        return None, "Upstox response root is not an object."
    if str(payload.get("status") or "").lower() != "success":
        errors = payload.get("errors")
        return None, f"Upstox response status is not success: {errors!r}"
    return payload.get("data"), None


def _wait(summary: str) -> dict[str, Any]:
    return source_result(
        parser_state="WAIT_SCHEMA_MISMATCH",
        data_date=None,
        record_count=0,
        summary=summary,
        output={"rows": [], "records": [], "scope": SOURCE_SCOPE},
    )


def _isin_from_url(url: str | None) -> str | None:
    match = re.search(r"/fundamentals/(IN[A-Z0-9]{10})/", url or "", re.I)
    return match.group(1).upper() if match else None


def _number(value: Any) -> float | None:
    if value is None or str(value).strip().lower() in {"", "-", "none", "null"}:
        return None
    try:
        return float(str(value).strip().replace(",", "").replace("%", ""))
    except ValueError:
        return None


def parse_upstox_company_profile(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, dict):
        return _wait(error or "Upstox company profile data is not an object.")
    inr = data.get("sector_market_cap_inr") or {}
    usd = data.get("sector_market_cap_usd") or {}
    row = {
        "isin": _isin_from_url(url),
        "companyProfile": data.get("company_profile"),
        "sector": data.get("sector"),
        "sectorMarketCapCr": _number(inr.get("value")) if isinstance(inr, dict) else None,
        "sectorMarketCapUsd": _number(usd.get("value")) if isinstance(usd, dict) else None,
        "sectorMarketCapUsdUnit": usd.get("unit") if isinstance(usd, dict) else None,
        "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
        "scoreEligible": False,
    }
    if not row["isin"] or not row["sector"]:
        return _wait("Upstox company profile is missing ISIN or sector.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=None,
        record_count=1,
        summary="Parsed one read-only Upstox company profile.",
        output={"rows": [row], "records": [row], "scope": SOURCE_SCOPE},
    )


def parse_upstox_key_ratios(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, list):
        return _wait(error or "Upstox key-ratio data is not a list.")
    isin = _isin_from_url(url)
    rows = []
    for item in data:
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            continue
        rows.append(
            {
                "isin": isin,
                "ratio": str(item["name"]).strip(),
                "companyValue": _number(item.get("company_value")),
                "sectorValue": _number(item.get("sector_value")),
                "isPercent": "%" in str(item.get("company_value") or "")
                or "%" in str(item.get("sector_value") or ""),
                "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
                "scoreEligible": False,
            }
        )
    if not isin or not rows:
        return _wait("Upstox key-ratio response has no ISIN-linked ratio rows.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=None,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox key ratios.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )


def _leg_fields(leg: Any, prefix: str) -> dict[str, Any]:
    if not isinstance(leg, dict):
        return {}
    market = leg.get("market_data") or {}
    greeks = leg.get("option_greeks") or {}
    if not isinstance(market, dict):
        market = {}
    if not isinstance(greeks, dict):
        greeks = {}
    return {
        f"{prefix}_instrumentKey": leg.get("instrument_key"),
        f"{prefix}_ltp": _number(market.get("ltp")),
        f"{prefix}_volume": _number(market.get("volume")),
        f"{prefix}_oi": _number(market.get("oi")),
        f"{prefix}_prevOi": _number(market.get("prev_oi")),
        f"{prefix}_bidPrice": _number(market.get("bid_price")),
        f"{prefix}_bidQty": _number(market.get("bid_qty")),
        f"{prefix}_askPrice": _number(market.get("ask_price")),
        f"{prefix}_askQty": _number(market.get("ask_qty")),
        f"{prefix}_iv": _number(greeks.get("iv")),
        f"{prefix}_delta": _number(greeks.get("delta")),
        f"{prefix}_gamma": _number(greeks.get("gamma")),
        f"{prefix}_theta": _number(greeks.get("theta")),
        f"{prefix}_vega": _number(greeks.get("vega")),
        f"{prefix}_pop": _number(greeks.get("pop")),
    }


def parse_upstox_option_chain(
    content: bytes, *, last_modified: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, list):
        return _wait(error or "Upstox option-chain data is not a list.")
    rows = []
    for item in data:
        if not isinstance(item, dict) or item.get("strike_price") is None:
            continue
        expiry = parse_date_value(item.get("expiry"))
        underlying_key = str(item.get("underlying_key") or "").strip()
        row = {
            "underlyingKey": underlying_key or None,
            "underlying": unquote(underlying_key.split("|", 1)[-1]) if underlying_key else None,
            "expiry": expiry or item.get("expiry"),
            "strikePrice": _number(item.get("strike_price")),
            "underlyingSpotPrice": _number(item.get("underlying_spot_price")),
            "pcr": _number(item.get("pcr")),
            "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
            "scoreEligible": False,
        }
        row.update(_leg_fields(item.get("call_options"), "CE"))
        row.update(_leg_fields(item.get("put_options"), "PE"))
        rows.append(row)
    if not rows:
        return _wait("Upstox option chain has no strike rows.")
    data_date = parse_date_value(last_modified)
    from ..iv_rank import select_atm_iv_observation

    atm_observation = (
        select_atm_iv_observation(rows, data_date=data_date)
        if data_date
        else {
            "state": "WAIT_MISSING_DATA_DATE",
            "dataDate": None,
            "atmIvPct": None,
            "scoreEligible": False,
        }
    )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox option-chain strikes.",
        output={
            "rows": rows,
            "records": rows,
            "scope": SOURCE_SCOPE,
            "atmIvObservation": atm_observation,
        },
    )


def parse_upstox_pcr_history(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, dict):
        return _wait(error or "Upstox PCR data is not an object.")
    query = parse_qs(urlparse(url or "").query)
    data_date = parse_date_value((query.get("date") or [None])[0])
    base = {
        "instrumentKey": data.get("instrument_key") or (query.get("instrument_key") or [None])[0],
        "expiry": parse_date_value(data.get("expiry_date") or (query.get("expiry") or [None])[0]),
        "pcr": _number(data.get("pcr")),
        "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
        "scoreEligible": False,
    }
    insights = data.get("insights")
    rows = []
    if isinstance(insights, list):
        for item in insights:
            if not isinstance(item, dict):
                continue
            row = dict(base)
            row.update(
                {
                    "timestamp": item.get("timestamp") or item.get("time"),
                    "pcr": _number(item.get("pcr")),
                    "callVolume": _number(item.get("call_volume")),
                    "putVolume": _number(item.get("put_volume")),
                }
            )
            row["sourceTrust"] = "FREE_CREDENTIALED_READ_ONLY"
            row["scoreEligible"] = False
            row["observationType"] = "INTRADAY_BUCKET"
            rows.append(row)
    if not rows and base["instrumentKey"] and base["pcr"] is not None:
        rows = [{**base, "observationType": "DAILY_SUMMARY"}]
    if not rows:
        return _wait("Upstox PCR response has no summary or insight rows.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox PCR observations.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )


def parse_upstox_market_quote(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, dict):
        return _wait(error or "Upstox full-quote data is not an object.")
    rows = []
    for label, item in data.items():
        if not isinstance(item, dict):
            continue
        ohlc = item.get("ohlc") or {}
        depth = item.get("depth") or {}
        if not isinstance(ohlc, dict):
            ohlc = {}
        if not isinstance(depth, dict):
            depth = {}
        rows.append(
            {
                "instrumentLabel": label,
                "instrumentKey": item.get("instrument_token") or item.get("instrument_key"),
                "lastPrice": _number(item.get("last_price")),
                "open": _number(ohlc.get("open")),
                "high": _number(ohlc.get("high")),
                "low": _number(ohlc.get("low")),
                "previousClose": _number(ohlc.get("close")),
                "volume": _number(item.get("volume")),
                "openInterest": _number(item.get("oi")),
                "totalBuyQuantity": _number(item.get("total_buy_quantity")),
                "totalSellQuantity": _number(item.get("total_sell_quantity")),
                "buyDepth": depth.get("buy") if isinstance(depth.get("buy"), list) else [],
                "sellDepth": depth.get("sell") if isinstance(depth.get("sell"), list) else [],
                "lastTradeTime": item.get("last_trade_time"),
                "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
                "scoreEligible": False,
            }
        )
    if not rows:
        return _wait("Upstox full-quote response has no instrument rows.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=None,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox full quotes.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )


def parse_upstox_historical_candles(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    data, error = _payload(content)
    candles = data.get("candles") if isinstance(data, dict) else None
    if error or not isinstance(candles, list):
        return _wait(error or "Upstox historical response has no candle list.")
    match = re.search(r"/historical-candle/([^/]+)/", url or "")
    instrument_key = unquote(match.group(1)) if match else None
    rows = []
    dates = []
    for candle in candles:
        if not isinstance(candle, list) or len(candle) < 6:
            continue
        data_date = parse_date_value(candle[0])
        open_price = _number(candle[1])
        high_price = _number(candle[2])
        low_price = _number(candle[3])
        close_price = _number(candle[4])
        volume = _number(candle[5])
        if (
            not data_date
            or None in (open_price, high_price, low_price, close_price, volume)
            or high_price < max(open_price, low_price, close_price)
            or low_price > min(open_price, high_price, close_price)
        ):
            continue
        dates.append(data_date)
        rows.append(
            {
                "instrumentKey": instrument_key,
                "timestamp": candle[0],
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "openInterest": _number(candle[6]) if len(candle) > 6 else None,
                "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
                "scoreEligible": False,
            }
        )
    if not rows:
        return _wait("Upstox historical response has no schema-valid candles.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(dates) if dates else None,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox OHLCV candles.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )


def parse_upstox_option_greeks(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, dict):
        return _wait(error or "Upstox option-Greeks data is not an object.")
    rows = []
    for label, item in data.items():
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "instrumentLabel": label,
                "instrumentKey": item.get("instrument_token"),
                "lastPrice": _number(item.get("last_price")),
                "lastTradedQuantity": _number(item.get("ltq")),
                "volume": _number(item.get("volume")),
                "previousClose": _number(item.get("cp")),
                "iv": _number(item.get("iv")),
                "delta": _number(item.get("delta")),
                "gamma": _number(item.get("gamma")),
                "theta": _number(item.get("theta")),
                "vega": _number(item.get("vega")),
                "openInterest": _number(item.get("oi")),
                "providerSuppliedGreeks": True,
                "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
                "scoreEligible": False,
            }
        )
    if not rows:
        return _wait("Upstox option-Greeks response has no instrument rows.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=None,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} provider-supplied Upstox option-Greeks rows.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )


def parse_upstox_fundamental_history(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, dict):
        return _wait(error or "Upstox financial-statement data is not an object.")
    isin = _isin_from_url(url)
    rows = []
    for field, detail_level in (
        ("balance_sheet", "SUMMARY"),
        ("cash_flow", "SUMMARY"),
        ("income_statement", "SUMMARY"),
        ("full_statement", "FULL_STATEMENT"),
    ):
        groups = data.get(field)
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            metric = group.get("category") or group.get("particular") or group.get("name")
            history = group.get("history")
            if not metric or not isinstance(history, list):
                continue
            for observation in history:
                if not isinstance(observation, dict) or observation.get("period") is None:
                    continue
                rows.append(
                    {
                        "isin": isin,
                        "statement": field,
                        "detailLevel": detail_level,
                        "metric": metric,
                        "period": observation.get("period"),
                        "valueCr": _number(observation.get("value")),
                        "changePct": _number(observation.get("change")),
                        "statementType": data.get("type"),
                        "timePeriod": data.get("time_period"),
                        "unit": data.get("units_in"),
                        "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
                        "scoreEligible": False,
                    }
                )
    if not isin or not rows:
        return _wait("Upstox statement response has no ISIN-linked history rows.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=None,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox financial-statement observations.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )


def parse_upstox_share_holdings(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, list):
        return _wait(error or "Upstox shareholding data is not a list.")
    isin = _isin_from_url(url)
    rows = []
    for group in data:
        if not isinstance(group, dict) or not isinstance(group.get("history"), list):
            continue
        for observation in group["history"]:
            if not isinstance(observation, dict) or observation.get("period") is None:
                continue
            rows.append(
                {
                    "isin": isin,
                    "holderCategory": group.get("category"),
                    "period": observation.get("period"),
                    "holdingPct": _number(observation.get("value")),
                    "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
                    "scoreEligible": False,
                }
            )
    if not isin or not rows:
        return _wait("Upstox shareholding response has no ISIN-linked history rows.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=None,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox shareholding observations.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )


def parse_upstox_corporate_actions(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, list):
        return _wait(error or "Upstox corporate-action data is not a list.")
    isin = _isin_from_url(url)
    rows = []
    dates = []
    for item in data:
        if not isinstance(item, dict):
            continue
        expiry_date = parse_date_value(item.get("expiry_date"))
        if expiry_date:
            dates.append(expiry_date)
        details = item.get("event_details")
        detail_map = {
            str(detail.get("name")): detail.get("value")
            for detail in details
            if isinstance(detail, dict) and detail.get("name")
        } if isinstance(details, list) else {}
        rows.append(
            {
                "isin": isin,
                "action": item.get("name") or item.get("event_type") or item.get("type") or item.get("event"),
                "effectiveDate": expiry_date,
                "amount": _number(item.get("amount")),
                "ratio": item.get("ratio"),
                "details": detail_map,
                "detailDates": {
                    key: parsed
                    for key, value in detail_map.items()
                    if (parsed := parse_date_value(value)) is not None
                },
                "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
                "scoreEligible": False,
            }
        )
    if not isin or not rows:
        return _wait("Upstox corporate-action response has no ISIN-linked events.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(dates) if dates else None,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox corporate actions.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )


def parse_upstox_competitors(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, list):
        return _wait(error or "Upstox competitor data is not a list.")
    rows = []
    for item in data:
        if not isinstance(item, dict) or not item.get("instrument_key"):
            continue
        inr = item.get("sector_market_cap_inr") or {}
        usd = item.get("sector_market_cap_usd") or {}
        rows.append(
            {
                "instrumentKey": item.get("instrument_key"),
                "isin": str(item.get("instrument_key")).split("|", 1)[-1],
                "companyProfile": item.get("company_profile"),
                "sector": item.get("sector"),
                "sectorMarketCapCr": _number(inr.get("value")) if isinstance(inr, dict) else None,
                "sectorMarketCapUsd": _number(usd.get("value")) if isinstance(usd, dict) else None,
                "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
                "scoreEligible": False,
            }
        )
    if not rows:
        return _wait("Upstox competitor response has no instrument rows.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=None,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox competitor profiles.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )


def parse_upstox_open_interest(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, dict):
        return _wait(error or "Upstox OI data is not an object.")
    query = parse_qs(urlparse(url or "").query)
    instrument_key = (query.get("instrument_key") or [None])[0]
    expiry = parse_date_value(data.get("expiry"))
    rows = []
    strikes = data.get("call_put_oi_data_list")
    if isinstance(strikes, list):
        for item in strikes:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "instrumentKey": instrument_key,
                    "expiry": expiry,
                    "strikePrice": _number(item.get("strike_price")),
                    "callOi": _number(item.get("call_oi")),
                    "putOi": _number(item.get("put_oi")),
                    "totalCallOi": _number(data.get("total_calls")),
                    "totalPutOi": _number(data.get("total_puts")),
                    "spotClosingPrice": _number(data.get("spot_closing_price")),
                    "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
                    "scoreEligible": False,
                }
            )
    if not rows:
        return _wait("Upstox OI response has no per-strike rows.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=parse_date_value((query.get("date") or [None])[0]),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox per-strike OI rows.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )


def parse_upstox_max_pain(
    content: bytes, *, url: str | None = None, **_kwargs: Any
) -> dict[str, Any]:
    data, error = _payload(content)
    if error or not isinstance(data, dict):
        return _wait(error or "Upstox max-pain data is not an object.")
    query = parse_qs(urlparse(url or "").query)
    base = {
        "instrumentKey": data.get("instrument_key") or (query.get("instrument_key") or [None])[0],
        "expiry": parse_date_value(data.get("expiry_date")),
        "dailyMaxPain": _number(data.get("max_pain")),
        "spotClosingPrice": _number(data.get("spot_closing_price")),
        "sourceTrust": "FREE_CREDENTIALED_READ_ONLY",
        "scoreEligible": False,
    }
    rows = []
    insights = data.get("insights")
    if isinstance(insights, list):
        for item in insights:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    **base,
                    "time": item.get("time"),
                    "maxPain": _number(item.get("max_pain")),
                    "spotPrice": _number(item.get("spot_price")),
                    "observationType": "INTRADAY_BUCKET",
                }
            )
    if not rows and base["instrumentKey"] and base["dailyMaxPain"] is not None:
        rows = [{**base, "observationType": "DAILY_SUMMARY"}]
    if not rows:
        return _wait("Upstox max-pain response has no summary or insight rows.")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=parse_date_value((query.get("date") or [None])[0]),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} read-only Upstox max-pain observations.",
        output={"rows": rows, "records": rows, "scope": SOURCE_SCOPE},
    )
