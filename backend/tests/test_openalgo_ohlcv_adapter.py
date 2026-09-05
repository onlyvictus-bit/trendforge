from __future__ import annotations

from datetime import date

from trendforge_api import source_adapters
from trendforge_api.models import DataTrust
from trendforge_api.openalgo_client import OpenAlgoConfig


def test_openalgo_history_normalizes_to_trendforge_candles(monkeypatch) -> None:
    calls = []

    class FakeClient:
        def __init__(self, config):
            assert config.api_key == "secret"

        def history(self, **kwargs):
            calls.append(kwargs)
            return [
                {
                    "timestamp": "2026-07-12 09:15:00+05:30",
                    "open": 1500,
                    "high": 1510,
                    "low": 1495,
                    "close": 1508,
                    "volume": 25000,
                    "oi": 100000,
                }
            ]

    monkeypatch.setattr(
        source_adapters.OpenAlgoConfig,
        "from_env",
        classmethod(lambda cls: OpenAlgoConfig("http://127.0.0.1:5000", "secret")),
    )
    monkeypatch.setattr(source_adapters, "OpenAlgoDataClient", FakeClient)
    display, requested, candles = source_adapters.fetch_openalgo_ohlcv(
        "NSE:RELIANCE", "1m", "5d"
    )

    assert display == "RELIANCE"
    assert requested == "NSE:RELIANCE"
    assert len(candles) == 1
    assert candles[0].source == "openalgo"
    assert candles[0].timestamp == "2026-07-12T03:45:00+00:00"
    assert candles[0].trust_level == DataTrust.OFFICIAL_OR_LICENSED
    assert calls[0]["exchange"] == "NSE"
    assert calls[0]["symbol"] == "RELIANCE"
    assert isinstance(calls[0]["start_date"], date)


def test_openalgo_daily_timeframe_uses_openalgo_daily_contract(monkeypatch) -> None:
    calls = []

    class FakeClient:
        def __init__(self, config):
            pass

        def history(self, **kwargs):
            calls.append(kwargs)
            return [
                {
                    "timestamp": "2026-07-12 15:30:00+05:30",
                    "open": 1500,
                    "high": 1510,
                    "low": 1495,
                    "close": 1508,
                    "volume": 25000,
                }
            ]

    monkeypatch.setattr(
        source_adapters.OpenAlgoConfig,
        "from_env",
        classmethod(lambda cls: OpenAlgoConfig("http://127.0.0.1:5000", "secret")),
    )
    monkeypatch.setattr(source_adapters, "OpenAlgoDataClient", FakeClient)

    _, _, candles = source_adapters.fetch_openalgo_ohlcv("NSE:RELIANCE", "1d", "1y")

    assert calls[0]["interval"] == "D"
    assert candles[0].timeframe == "1d"


def test_openalgo_adapter_is_registered_as_licensed_source() -> None:
    assert (
        source_adapters.SOURCE_AUTHORITY["openalgo"] == DataTrust.OFFICIAL_OR_LICENSED
    )
