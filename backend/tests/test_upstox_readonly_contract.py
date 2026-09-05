from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from trendforge_api.institutional_sources import (
    ENDPOINTS,
    AsyncEndpointClient,
    FetchState,
)
from trendforge_api.parsers.upstox_readonly_parser import (
    parse_upstox_corporate_actions,
    parse_upstox_fundamental_history,
    parse_upstox_historical_candles,
    parse_upstox_market_quote,
    parse_upstox_max_pain,
    parse_upstox_open_interest,
    parse_upstox_company_profile,
    parse_upstox_key_ratios,
    parse_upstox_option_chain,
    parse_upstox_option_greeks,
    parse_upstox_pcr_history,
)
from trendforge_api.source_parser import parse_source_content


UPSTOX_KEYS = {key for key in ENDPOINTS if key.startswith("upstox_")}


def test_upstox_contracts_are_read_only_and_environment_credentialed() -> None:
    forbidden = ("/order", "/place", "/modify", "/cancel", "/portfolio")

    assert UPSTOX_KEYS <= ENDPOINTS.keys()
    assert len(UPSTOX_KEYS) == 15
    for key in UPSTOX_KEYS:
        spec = ENDPOINTS[key]
        assert spec.http_method == "GET"
        assert spec.url_template.startswith("https://api.upstox.com/")
        assert spec.credential_env == "UPSTOX_ANALYTICS_TOKEN"
        assert not any(token in spec.url_template.lower() for token in forbidden)


def test_missing_upstox_token_fails_closed_without_network(
    tmp_path: Path, monkeypatch
) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise AssertionError("missing credential must stop before network")

    async def run():
        monkeypatch.delenv("UPSTOX_ANALYTICS_TOKEN", raising=False)
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.fetch(
                "upstox_key_ratios", {"isin": "INE002A01018"}
            )
        finally:
            await client.aclose()

    result = asyncio.run(run())

    assert calls == 0
    assert result.state == FetchState.BROKEN
    assert result.can_score is False
    assert "UPSTOX_ANALYTICS_TOKEN" in (result.reason or "")


def test_upstox_token_is_sent_as_bearer_but_never_returned(
    tmp_path: Path, monkeypatch
) -> None:
    token = "test-read-only-token-never-persist"
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"status": "success", "data": {"isin": "INE002A01018"}},
            headers={"Content-Type": "application/json"},
        )

    async def run():
        monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", token)
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.fetch(
                "upstox_company_profile", {"isin": "INE002A01018"}
            )
        finally:
            await client.aclose()

    result = asyncio.run(run())

    assert len(requests) == 1
    assert requests[0].headers["Authorization"] == f"Bearer {token}"
    assert result.state == FetchState.RAW_ARCHIVED
    assert result.can_score is False
    exposed = " ".join(
        str(value)
        for value in (
            result.url,
            result.reason,
            result.raw_path,
            result.payload,
        )
    )
    assert token not in exposed


def test_upstox_fundamental_normalizers_keep_values_informational() -> None:
    profile = parse_upstox_company_profile(
        json.dumps(
            {
                "status": "success",
                "data": {
                    "company_profile": "Example business",
                    "sector": "Refineries",
                    "sector_market_cap_inr": {"value": 1942866.05, "unit": "crore"},
                    "sector_market_cap_usd": {"value": 215.87, "unit": "billion"},
                },
            }
        ).encode(),
        url="https://api.upstox.com/v2/fundamentals/INE002A01018/profile",
    )
    ratios = parse_upstox_key_ratios(
        json.dumps(
            {
                "status": "success",
                "data": [
                    {"name": "P/E", "company_value": "20.15", "sector_value": "12.46"},
                    {"name": "ROCE", "company_value": "10.39%", "sector_value": "16.9%"},
                ],
            }
        ).encode(),
        url="https://api.upstox.com/v2/fundamentals/INE002A01018/key-ratios",
    )

    assert profile["parser_state"] == "PARSED_STRUCTURED"
    assert profile["output"]["rows"][0]["sectorMarketCapCr"] == 1942866.05
    assert profile["output"]["rows"][0]["scoreEligible"] is False
    assert ratios["record_count"] == 2
    assert ratios["output"]["rows"][1]["companyValue"] == 10.39
    assert ratios["output"]["rows"][1]["isPercent"] is True
    assert all(row["scoreEligible"] is False for row in ratios["output"]["rows"])


def test_upstox_endpoint_only_parser_reaches_shared_normalizer() -> None:
    result = parse_source_content(
        "upstox_company_profile",
        json.dumps(
            {
                "status": "success",
                "data": {
                    "company_profile": "Example business",
                    "sector": "Refineries",
                },
            }
        ).encode(),
        url="https://api.upstox.com/v2/fundamentals/INE002A01018/profile",
        last_modified="2026-08-11T09:20:00+05:30",
    )

    assert result.parser_state == "PARSED_STRUCTURED"
    assert result.record_count == 1
    assert result.output["category"] == "credentialed_read_only"
    assert result.output["rows"][0]["scoreEligible"] is False


def test_upstox_option_and_pcr_normalizers_preserve_provider_greeks() -> None:
    option = parse_upstox_option_chain(
        json.dumps(
            {
                "status": "success",
                "data": [
                    {
                        "expiry": "2026-08-13",
                        "pcr": 0.91,
                        "strike_price": 25000,
                        "underlying_key": "NSE_INDEX|Nifty 50",
                        "underlying_spot_price": 24950.2,
                        "call_options": {
                            "instrument_key": "NSE_FO|1001",
                            "market_data": {"ltp": 111.5, "volume": 500, "oi": 750, "prev_oi": 700},
                            "option_greeks": {"iv": 0.18, "delta": 0.52, "gamma": 0.001, "theta": -8.2, "vega": 12.4},
                        },
                        "put_options": {
                            "instrument_key": "NSE_FO|1002",
                            "market_data": {"ltp": 145.0, "volume": 450, "oi": 820, "prev_oi": 810},
                            "option_greeks": {"iv": 0.19, "delta": -0.48, "gamma": 0.001, "theta": -8.0, "vega": 12.1},
                        },
                    }
                ],
            }
        ).encode(),
        last_modified="2026-08-11T09:20:00+05:30",
    )
    pcr = parse_upstox_pcr_history(
        json.dumps(
            {
                "status": "success",
                "data": {
                    "instrument_key": "NSE_INDEX|Nifty 50",
                    "expiry_date": "13-08-2026",
                    "pcr": 0.91,
                    "insights": [{"timestamp": "2026-08-11T09:15:00+05:30", "pcr": 0.88}],
                },
            }
        ).encode(),
        url="https://api.upstox.com/v2/market/pcr?instrument_key=NSE_INDEX%7CNifty%2050&expiry=2026-08-13&date=2026-08-11&bucket_interval=60",
    )

    row = option["output"]["rows"][0]
    assert option["parser_state"] == "PARSED_STRUCTURED"
    assert option["data_date"] == "2026-08-11"
    assert option["data_date"] != "2026-08-13"
    assert row["CE_iv"] == 0.18
    assert row["PE_delta"] == -0.48
    assert row["scoreEligible"] is False
    assert option["output"]["atmIvObservation"]["atmIvPct"] == 18.5
    assert pcr["data_date"] == "2026-08-11"
    assert pcr["output"]["rows"][0]["observationType"] == "INTRADAY_BUCKET"
    assert pcr["output"]["rows"][0]["scoreEligible"] is False


def test_upstox_pcr_payload_cannot_override_safety_fields() -> None:
    parsed = parse_upstox_pcr_history(
        json.dumps(
            {
                "status": "success",
                "data": {
                    "instrument_key": "NSE_INDEX|Nifty 50",
                    "expiry_date": "13-08-2026",
                    "pcr": 0.91,
                    "insights": [
                        {
                            "timestamp": "2026-08-11T09:15:00+05:30",
                            "pcr": 0.88,
                            "call_volume": 1200,
                            "put_volume": 1056,
                            "scoreEligible": True,
                            "sourceTrust": "OVERRIDDEN",
                        }
                    ],
                },
            }
        ).encode(),
        url="https://api.upstox.com/v2/market/pcr?instrument_key=NSE_INDEX%7CNifty%2050&expiry=2026-08-13&date=2026-08-11&bucket_interval=60",
    )

    row = parsed["output"]["rows"][0]
    assert row["pcr"] == 0.88
    assert row["callVolume"] == 1200
    assert row["putVolume"] == 1056
    assert row["scoreEligible"] is False
    assert row["sourceTrust"] == "FREE_CREDENTIALED_READ_ONLY"


def test_upstox_quote_candle_and_standalone_greeks_normalizers() -> None:
    quote = parse_upstox_market_quote(
        json.dumps(
            {
                "status": "success",
                "data": {
                    "NSE_EQ:NHPC": {
                        "instrument_token": "NSE_EQ|INE848E01016",
                        "last_price": 52.1,
                        "volume": 1000,
                        "oi": 0,
                        "ohlc": {"open": 53.4, "high": 53.8, "low": 51.75, "close": 52.05},
                        "depth": {"buy": [{"price": 52.05, "quantity": 6917}], "sell": []},
                    }
                },
            }
        ).encode()
    )
    candles = parse_upstox_historical_candles(
        json.dumps(
            {
                "status": "success",
                "data": {"candles": [["2026-08-11T00:00:00+05:30", 51, 53, 50, 52, 10000, 123]]},
            }
        ).encode(),
        url="https://api.upstox.com/v3/historical-candle/NSE_EQ%7CINE848E01016/days/1/2026-08-11/2026-08-01",
    )
    greeks = parse_upstox_option_greeks(
        json.dumps(
            {
                "status": "success",
                "data": {
                    "NSE_FO:NIFTY": {
                        "instrument_token": "NSE_FO|43885",
                        "last_price": 412.2,
                        "volume": 3609600,
                        "iv": 0.3359,
                        "vega": 3.3899,
                        "gamma": 0.0005,
                        "theta": -51.848,
                        "delta": -0.8081,
                        "oi": 2476650,
                    }
                },
            }
        ).encode()
    )

    assert quote["output"]["rows"][0]["buyDepth"][0]["quantity"] == 6917
    assert candles["data_date"] == "2026-08-11"
    assert candles["output"]["rows"][0]["openInterest"] == 123
    assert greeks["output"]["rows"][0]["providerSuppliedGreeks"] is True
    assert greeks["output"]["rows"][0]["delta"] == -0.8081


def test_upstox_historical_candles_quarantine_invalid_ohlc() -> None:
    parsed = parse_upstox_historical_candles(
        json.dumps(
            {
                "status": "success",
                "data": {
                    "candles": [
                        ["not-a-date", None, 53, 50, 52, 10000, 123],
                        ["2026-08-11T00:00:00+05:30", 51, 49, 50, 52, 10000, 123],
                    ]
                },
            }
        ).encode(),
        url="https://api.upstox.com/v3/historical-candle/NSE_EQ%7CINE848E01016/days/1/2026-08-11/2026-08-01",
    )

    assert parsed["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert parsed["record_count"] == 0


def test_upstox_statement_oi_and_max_pain_normalizers() -> None:
    statement = parse_upstox_fundamental_history(
        json.dumps(
            {
                "status": "success",
                "data": {
                    "type": "consolidated",
                    "time_period": "yearly",
                    "units_in": "crore",
                    "cash_flow": [
                        {"category": "operating", "history": [{"period": "Mar 2025", "value": 178703, "change": "+12.54%"}]}
                    ],
                },
            }
        ).encode(),
        url="https://api.upstox.com/v2/fundamentals/INE002A01018/cash-flow?type=consolidated&fs=true",
    )
    oi = parse_upstox_open_interest(
        json.dumps(
            {
                "status": "success",
                "data": {
                    "total_puts": 12500000,
                    "total_calls": 9800000,
                    "spot_closing_price": 24450.75,
                    "expiry": "2026-08-13",
                    "call_put_oi_data_list": [{"call_oi": 450000, "put_oi": 680000, "strike_price": 24000}],
                },
            }
        ).encode(),
        url="https://api.upstox.com/v2/market/oi?instrument_key=NSE_INDEX%7CNifty%2050&expiry=2026-08-13&date=2026-08-11",
    )
    pain = parse_upstox_max_pain(
        json.dumps(
            {
                "status": "success",
                "data": {
                    "instrument_key": "NSE_INDEX|Nifty 50",
                    "expiry_date": "13-08-2026",
                    "max_pain": 24050,
                    "spot_closing_price": 24044.35,
                    "insights": [{"max_pain": 24250, "spot_price": 23955, "time": "09:15"}],
                },
            }
        ).encode(),
        url="https://api.upstox.com/v2/market/max-pain?instrument_key=NSE_INDEX%7CNifty%2050&expiry=2026-08-13&date=2026-08-11&bucket_interval=60",
    )

    assert statement["output"]["rows"][0]["valueCr"] == 178703
    assert statement["output"]["rows"][0]["changePct"] == 12.54
    assert oi["data_date"] == "2026-08-11"
    assert oi["output"]["rows"][0]["putOi"] == 680000
    assert pain["output"]["rows"][0]["maxPain"] == 24250
    assert pain["output"]["rows"][0]["scoreEligible"] is False


def test_upstox_corporate_actions_match_official_schema() -> None:
    parsed = parse_upstox_corporate_actions(
        json.dumps(
            {
                "status": "success",
                "data": [
                    {
                        "name": "Dividend",
                        "expiry_date": "14 Aug 2025",
                        "amount": 5.5,
                        "ratio": None,
                        "event_details": [
                            {"name": "Announcement date", "value": "25 Apr 2025"},
                            {"name": "Record date", "value": "14 Aug 2025"},
                        ],
                    }
                ],
            }
        ).encode(),
        url="https://api.upstox.com/v2/fundamentals/INE002A01018/corporate-actions",
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2025-08-14"
    row = parsed["output"]["rows"][0]
    assert row["action"] == "Dividend"
    assert row["effectiveDate"] == "2025-08-14"
    assert row["detailDates"]["Announcement date"] == "2025-04-25"
    assert row["scoreEligible"] is False
