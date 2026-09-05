from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trendforge_api.institutional_sources import EndpointFetchResult, FetchState
from trendforge_api.live_panels import (
    P0_SOURCE_KEYS,
    LivePanelsService,
    build_live_snapshot,
    evaluate_live_market_session,
    normalize_live_result,
)


NOW = datetime(2026, 8, 4, 9, 30, tzinfo=UTC)  # 15:00 IST
TRADING_DATE = "2026-08-04"


def _result(key: str, payload: object, *, fetched_at: datetime = NOW) -> EndpointFetchResult:
    return EndpointFetchResult(
        endpointKey=key,
        state=FetchState.RAW_ARCHIVED,
        fetchedAt=fetched_at,
        url=f"https://example.test/{key}",
        contentHash=f"hash-{key}",
        rawPath=f"/tmp/{key}.json",
        mediaType="application/json",
        recordCount=1,
        payload=payload,
        canScore=False,
    )


def _payloads() -> dict[str, dict]:
    variation = {
        "allSec": {
            "timestamp": "04-Aug-2026 14:59:00",
            "data": [{"symbol": "RELIANCE", "ltp": 1400, "perChange": 1.2}],
        }
    }
    generic = {
        "timestamp": "04-Aug-2026 14:59:00",
        "data": [{"symbol": "RELIANCE", "lastPrice": 1400, "pChange": 1.2}],
    }
    return {
        "nse_variations_gainers": variation,
        "nse_variations_loosers": variation,
        "nse_volume_gainers": {
            "timestamp": "04-Aug-2026 14:59:00",
            "data": [{"symbol": "RELIANCE", "ltp": 1400, "pChange": 1.2, "week1volChange": 2.5}],
        },
        "nse_most_active_volume": generic,
        "nse_most_active_value": generic,
        "nse_all_indices": {
            "timestamp": "04-Aug-2026 14:59",
            "data": [{"index": "NIFTY 50", "last": 25000, "percentChange": 0.8}],
        },
        "nse_oi_spurts": {
            "timestamp": "04-Aug-2026 14:59:00",
            "currTradingDate": "04-Aug-2026",
            "prevTradingDate": "03-Aug-2026",
            "data": [{"symbol": "RELIANCE", "latestOI": 120, "prevOI": 100, "changeInOI": 20, "avgInOI": 20}],
        },
        "nse_most_active_underlying": generic,
        "nse_large_deals_snapshot": {
            "as_on_date": "04-Aug-2026",
            "BULK_DEALS_DATA": [{"symbol": "RELIANCE", "buySell": "BUY", "clientName": "FUND", "qty": "10", "watp": "1400", "date": "04-Aug-2026"}],
            "BLOCK_DEALS_DATA": [],
            "SHORT_DEALS_DATA": [],
        },
        "nse_preopen_fo": {
            "timestamp": "04-Aug-2026 09:07:00",
            "data": [{"metadata": {"symbol": "RELIANCE", "lastPrice": 1390, "previousClose": 1380, "iep": 1390}, "detail": {"preOpenMarket": {"IEP": 1390}}}],
        },
    }


def test_all_ten_p0_sources_have_populated_inventory_shaped_adapters() -> None:
    payloads = _payloads()
    assert set(payloads) == set(P0_SOURCE_KEYS)
    for key in P0_SOURCE_KEYS:
        row = normalize_live_result(
            _result(key, payloads[key]),
            now=NOW,
            market_trading_date=TRADING_DATE,
            max_age_sec=300,
        )
        assert row["sourceKey"] == key
        assert row["tradingDate"] == TRADING_DATE
        assert row["normalizedRowCount"] >= 1
        assert row["recordsSample"]
        expected_state = {
            "nse_large_deals_snapshot": "TRADING_DAY_CONTEXT",
            "nse_preopen_fo": "SESSION_CONTEXT",
        }.get(key, "FRESH")
        assert row["state"] == expected_state
        if key not in {"nse_large_deals_snapshot", "nse_preopen_fo"}:
            assert row["ageSec"] == 60


def test_structured_validation_preserves_browser_aliases() -> None:
    payloads = _payloads()
    oi = normalize_live_result(
        _result("nse_oi_spurts", payloads["nse_oi_spurts"]),
        now=NOW,
        market_trading_date=TRADING_DATE,
        max_age_sec=300,
    )
    assert oi["parserState"] == "PARSED_STRUCTURED"
    assert oi["recordsSample"][0]["avgInOI"] == 20

    deals = normalize_live_result(
        _result("nse_large_deals_snapshot", payloads["nse_large_deals_snapshot"]),
        now=NOW,
        market_trading_date=TRADING_DATE,
        max_age_sec=300,
    )
    deal = deals["recordsSample"][0]
    assert deals["parserState"] == "PARSED_STRUCTURED"
    assert deal["side"] == "BUY"
    assert deal["buySell"] == "BUY"
    assert deal["qty"] == 10


def test_wrong_trading_date_and_301_seconds_block_freshness() -> None:
    payload = _payloads()["nse_most_active_value"]
    wrong_day = normalize_live_result(
        _result("nse_most_active_value", payload),
        now=NOW,
        market_trading_date="2026-08-05",
        max_age_sec=300,
    )
    assert wrong_day["state"] == "QUARANTINED"
    assert wrong_day["eligible"] is False

    payload["timestamp"] = "04-Aug-2026 14:54:59"
    old = normalize_live_result(
        _result("nse_most_active_value", payload),
        now=NOW,
        market_trading_date=TRADING_DATE,
        max_age_sec=300,
    )
    assert old["ageSec"] == 301
    assert old["state"] == "STALE"


def test_panel_live_partial_and_stale_rules_are_source_family_based() -> None:
    sources = {
        key: normalize_live_result(
            _result(key, payload),
            now=NOW,
            market_trading_date=TRADING_DATE,
            max_age_sec=300,
        )
        for key, payload in _payloads().items()
    }
    snapshot = build_live_snapshot(
        sources,
        now=NOW,
        market={"tradingDate": TRADING_DATE, "session": "OPEN", "timezone": "Asia/Kolkata"},
        max_age_sec=300,
    )
    assert snapshot["panels"]["sector"]["state"] == "LIVE"
    assert snapshot["panels"]["consensus"]["state"] == "LIVE"
    assert snapshot["panels"]["screener"]["state"] == "LIVE"

    partial = dict(sources)
    partial["nse_most_active_value"] = {**partial["nse_most_active_value"], "state": "STALE", "eligible": False}
    snapshot = build_live_snapshot(
        partial,
        now=NOW,
        market={"tradingDate": TRADING_DATE, "session": "OPEN", "timezone": "Asia/Kolkata"},
        max_age_sec=300,
    )
    assert snapshot["panels"]["screener"]["state"] == "PARTIAL"
    assert snapshot["panels"]["consensus"]["state"] == "LIVE"

    stale = {key: {**value, "state": "STALE", "eligible": False} for key, value in sources.items()}
    snapshot = build_live_snapshot(
        stale,
        now=NOW,
        market={"tradingDate": TRADING_DATE, "session": "OPEN", "timezone": "Asia/Kolkata"},
        max_age_sec=300,
    )
    assert {row["state"] for row in snapshot["panels"].values()} == {"STALE"}
    assert snapshot["inventoryOverlay"]
    assert all(
        row["live_source_status"] == "RESEARCH_ONLY"
        and row["records_scope"] == "saved_research_records"
        for row in snapshot["inventoryOverlay"]
    )


def test_session_clock_distinguishes_preopen_open_close_and_calendar_wait() -> None:
    def open_day(_at: datetime) -> dict:
        return {"state": "OPEN_NORMAL", "isTradingDay": True, "reason": "covered"}

    assert evaluate_live_market_session(datetime(2026, 8, 4, 3, 40, tzinfo=UTC), calendar_evaluator=open_day)["session"] == "PRE_OPEN"
    assert evaluate_live_market_session(datetime(2026, 8, 4, 4, 0, tzinfo=UTC), calendar_evaluator=open_day)["session"] == "OPEN"
    assert evaluate_live_market_session(datetime(2026, 8, 4, 10, 1, tzinfo=UTC), calendar_evaluator=open_day)["session"] == "MARKET_CLOSED"

    def missing_calendar(_at: datetime) -> dict:
        return {"state": "WAIT_CALENDAR_DATA", "isTradingDay": False, "reason": "missing"}

    assert evaluate_live_market_session(NOW, calendar_evaluator=missing_calendar)["session"] == "WAIT_CALENDAR"


def test_kill_switch_never_constructs_or_calls_fetch_client(tmp_path: Path) -> None:
    calls = 0

    class ForbiddenClient:
        def __init__(self) -> None:
            nonlocal calls
            calls += 1

    service = LivePanelsService(
        db_path=tmp_path / "live.db",
        client_factory=ForbiddenClient,
        enabled=False,
    )
    result = asyncio.run(service.get_snapshot(refresh=True, now=NOW))
    assert calls == 0
    assert result["refresh"]["state"] == "WAIT_DISABLED"
    assert {panel["state"] for panel in result["panels"].values()} == {"WAIT"}


def test_single_flight_deduplicates_concurrent_refreshes(tmp_path: Path) -> None:
    payloads = _payloads()
    fetch_many_calls = 0

    class FakeClient:
        async def fetch_many(self, requests, *, concurrency):
            nonlocal fetch_many_calls
            fetch_many_calls += 1
            await asyncio.sleep(0.02)
            return [_result(key, payloads[key]) for key, _ in requests]

        async def aclose(self) -> None:
            return None

    service = LivePanelsService(
        db_path=tmp_path / "live.db",
        client_factory=FakeClient,
        enabled=True,
        calendar_evaluator=lambda _at: {"state": "OPEN_NORMAL", "isTradingDay": True, "reason": "covered"},
    )

    async def run() -> list[dict]:
        return await asyncio.gather(*(service.get_snapshot(refresh=True, force=True, now=NOW) for _ in range(10)))

    results = asyncio.run(run())
    assert fetch_many_calls == 1
    assert len({row["snapshotId"] for row in results}) == 1


def test_three_widespread_failed_cycles_open_global_circuit(tmp_path: Path) -> None:
    fetch_many_calls = 0

    class FailingClient:
        async def fetch_many(self, requests, *, concurrency):
            nonlocal fetch_many_calls
            fetch_many_calls += 1
            return [
                EndpointFetchResult(
                    endpointKey=key,
                    state=FetchState.BROKEN,
                    fetchedAt=NOW,
                    url=f"https://example.test/{key}",
                    recordCount=0,
                    canScore=False,
                    reason="NSE access denied",
                    statusCode=403,
                    errorType="ACCESS_DENIED",
                )
                for key, _ in requests
            ]

        async def aclose(self) -> None:
            return None

    service = LivePanelsService(
        db_path=tmp_path / "live.db",
        client_factory=FailingClient,
        enabled=True,
        calendar_evaluator=lambda _at: {"state": "OPEN_NORMAL", "isTradingDay": True, "reason": "covered"},
    )

    async def run() -> list[dict]:
        results = []
        for offset in range(4):
            results.append(
                await service.get_snapshot(
                    refresh=True,
                    force=True,
                    now=NOW + timedelta(seconds=offset),
                )
            )
        return results

    results = asyncio.run(run())
    assert fetch_many_calls == 3
    assert results[2]["refresh"]["state"] == "CIRCUIT_OPEN"
    assert results[3]["refresh"]["state"] == "CIRCUIT_OPEN"
    assert results[3]["inventoryOverlay"] == []
    assert {panel["state"] for panel in results[3]["panels"].values()} == {"STALE"}


def test_read_only_cache_path_recomputes_age_and_never_refetches(tmp_path: Path) -> None:
    payloads = _payloads()
    fetch_many_calls = 0

    class FakeClient:
        async def fetch_many(self, requests, *, concurrency):
            nonlocal fetch_many_calls
            fetch_many_calls += 1
            return [_result(key, payloads[key]) for key, _ in requests]

        async def aclose(self) -> None:
            return None

    service = LivePanelsService(
        db_path=tmp_path / "live.db",
        client_factory=FakeClient,
        enabled=True,
        calendar_evaluator=lambda _at: {"state": "OPEN_NORMAL", "isTradingDay": True, "reason": "covered"},
    )

    async def run() -> tuple[dict, dict]:
        fresh = await service.get_snapshot(refresh=True, now=NOW)
        cached = await service.get_snapshot(
            refresh=False,
            now=NOW + timedelta(seconds=301),
        )
        return fresh, cached

    fresh, cached = asyncio.run(run())
    assert fetch_many_calls == 1
    assert fresh["panels"]["screener"]["state"] == "LIVE"
    assert cached["refresh"]["state"] == "CACHE"
    assert cached["panels"]["sector"]["state"] == "STALE"
    assert cached["panels"]["consensus"]["state"] == "STALE"
    assert cached["panels"]["screener"]["state"] == "STALE"
    assert cached["inventoryOverlay"]
    assert any(
        row["live_source_status"] == "RESEARCH_ONLY"
        for row in cached["inventoryOverlay"]
    )


def test_market_close_serves_saved_same_day_overlay_as_research_only(tmp_path: Path) -> None:
    payloads = _payloads()

    class FakeClient:
        async def fetch_many(self, requests, *, concurrency):
            return [_result(key, payloads[key]) for key, _ in requests]

        async def aclose(self) -> None:
            return None

    service = LivePanelsService(
        db_path=tmp_path / "live.db",
        client_factory=FakeClient,
        enabled=True,
        calendar_evaluator=lambda _at: {"state": "OPEN_NORMAL", "isTradingDay": True, "reason": "covered"},
    )

    async def run() -> dict:
        await service.get_snapshot(refresh=True, now=NOW)
        return await service.get_snapshot(
            refresh=True,
            now=datetime(2026, 8, 4, 10, 1, tzinfo=UTC),
        )

    closed = asyncio.run(run())
    assert closed["market"]["session"] == "MARKET_CLOSED"
    assert closed["inventoryOverlay"]
    assert all(
        row["live_source_status"] == "RESEARCH_ONLY"
        and row["records_scope"] == "saved_research_records"
        for row in closed["inventoryOverlay"]
    )
    assert {panel["state"] for panel in closed["panels"].values()} == {"MARKET_CLOSED"}
