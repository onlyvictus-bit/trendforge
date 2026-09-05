from __future__ import annotations

from datetime import date

import pytest

from trendforge_api.openalgo_client import (
    OpenAlgoConfig,
    OpenAlgoDataClient,
    OpenAlgoUnavailable,
)


def test_history_uses_documented_read_only_post_contract() -> None:
    calls = []

    def transport(url, body, timeout):
        calls.append((url, body, timeout))
        return {
            "status": "success",
            "data": [
                {
                    "timestamp": 1750909500,
                    "open": 100,
                    "high": 102,
                    "low": 99,
                    "close": 101,
                    "volume": 1000,
                    "oi": 5000,
                }
            ],
        }

    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"), transport
    )
    rows = client.history(
        symbol="RELIANCE",
        exchange="NSE",
        interval="1m",
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 10),
    )

    assert rows[0]["oi"] == 5000
    assert calls[0][0] == "http://127.0.0.1:5000/api/v1/history"
    assert calls[0][1]["apikey"] == "secret"


def test_history_accepts_openalgo_daily_token_and_rejects_yfinance_token() -> None:
    calls = []

    def transport(url, body, timeout):
        calls.append((url, body, timeout))
        return {
            "status": "success",
            "data": [
                {
                    "timestamp": "2026-07-01 15:30:00+05:30",
                    "open": 100,
                    "high": 102,
                    "low": 99,
                    "close": 101,
                    "volume": 1000,
                }
            ],
        }

    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"), transport
    )
    client.history(
        symbol="RELIANCE",
        exchange="NSE",
        interval="D",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 10),
    )

    assert calls[0][1]["interval"] == "D"
    with pytest.raises(ValueError, match="OpenAlgo interval token"):
        client.history(
            symbol="RELIANCE",
            exchange="NSE",
            interval="1d",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
        )


def test_option_chain_uses_documented_contract_and_bounds_strikes() -> None:
    calls = []

    def transport(url, body, timeout):
        calls.append((url, body, timeout))
        return {"status": "success", "chain": [], "atm_strike": 25000}

    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://localhost:5000", "secret"), transport
    )
    result = client.option_chain(
        underlying="NIFTY",
        exchange="NSE_INDEX",
        expiry_date="30JUL26",
        strike_count=10,
    )

    assert result["atm_strike"] == 25000
    assert calls[0][0].endswith("/api/v1/optionchain")
    assert calls[0][1]["strike_count"] == 10


def test_option_greeks_uses_verified_black76_route() -> None:
    calls = []

    def transport(url, body, timeout):
        calls.append((url, body, timeout))
        return {
            "status": "success",
            "symbol": "NIFTY30JUL2625000CE",
            "implied_volatility": 14.2,
            "greeks": {"delta": 0.52, "gamma": 0.001},
        }

    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://localhost:5000", "secret"), transport
    )
    result = client.option_greeks(
        symbol="NIFTY30JUL2625000CE",
        exchange="NFO",
        interest_rate=6.5,
        underlying_symbol="NIFTY",
        underlying_exchange="NSE_INDEX",
        expiry_time="15:30",
    )

    assert result["greeks"]["delta"] == 0.52
    assert calls[0][0].endswith("/api/v1/optiongreeks")
    assert calls[0][1]["underlying_exchange"] == "NSE_INDEX"
    assert calls[0][1]["interest_rate"] == 6.5


def test_multi_option_greeks_uses_verified_batch_route() -> None:
    calls = []

    def transport(url, body, timeout):
        calls.append((url, body, timeout))
        return {
            "status": "success",
            "data": [{"status": "success", "symbol": "NIFTY30JUL2625000CE"}],
            "summary": {"total": 1, "success": 1, "failed": 0},
        }

    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"), transport
    )
    result = client.multi_option_greeks(
        symbols=[
            {
                "symbol": "NIFTY30JUL2625000CE",
                "exchange": "NFO",
                "underlying_symbol": "NIFTY",
                "underlying_exchange": "NSE_INDEX",
            }
        ],
        expiry_time="15:30",
    )

    assert result["summary"]["success"] == 1
    assert calls[0][0].endswith("/api/v1/multioptiongreeks")
    assert calls[0][1]["symbols"][0]["symbol"] == "NIFTY30JUL2625000CE"

    with pytest.raises(ValueError, match="between 1 and 50"):
        client.multi_option_greeks(symbols=[])


def test_derivatives_route_status_does_not_claim_oi_or_gex_are_verified() -> None:
    status = OpenAlgoDataClient.derivatives_route_status()

    assert status["/api/v1/multioptiongreeks"] == "VERIFIED_READ_ONLY"
    assert status["/api/v1/oi-analytics"] == "PROPOSED_NOT_EXPOSED"
    assert status["/api/v1/gex"] == "PROPOSED_NOT_EXPOSED"


def test_remote_openalgo_is_blocked_by_default() -> None:
    with pytest.raises(OpenAlgoUnavailable, match="Remote OpenAlgo URLs are blocked"):
        OpenAlgoDataClient(OpenAlgoConfig("https://broker.example", "secret"))


def test_order_routes_are_not_exposed() -> None:
    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"), lambda *_: {}
    )
    assert not hasattr(client, "place_order")
