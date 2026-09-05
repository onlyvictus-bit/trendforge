from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

import trendforge_api.main as main_module
from trendforge_api.institutional_sources import (
    MARKET_ACTIVITY_ENDPOINTS,
    AsyncEndpointClient,
    EndpointFetchResult,
    FetchState,
    market_activity_requests,
)
from trendforge_api.main import app
from trendforge_api.market_activity import (
    build_market_activity_snapshot,
    latest_market_activity_snapshot,
    save_market_activity_snapshot,
)


NOW = datetime(2026, 7, 14, 10, 30, tzinfo=UTC)


def _result(
    endpoint_key: str,
    payload: dict,
    *,
    state: FetchState = FetchState.RAW_ARCHIVED,
) -> EndpointFetchResult:
    return EndpointFetchResult(
        endpoint_key=endpoint_key,
        state=state,
        fetched_at=NOW,
        url=f"https://www.nseindia.com/api/{endpoint_key}",
        content_hash=f"hash-{endpoint_key}",
        record_count=1,
        payload=payload,
        can_score=False,
    )


def _complete_results(*, state: FetchState = FetchState.RAW_ARCHIVED):
    return [
        _result(
            "nse_volume_gainers",
            {
                "timestamp": "14-Jul-2026 16:00:00",
                "data": [
                    {
                        "symbol": "RELIANCE",
                        "volume": 5_000_000,
                        "week1volChange": 550,
                        "week2volChange": 240,
                        "ltp": 104,
                        "pChange": 3.2,
                        "turnover": 500,
                    }
                ],
            },
            state=state,
        ),
        _result(
            "nse_most_active_volume",
            {
                "timestamp": "14-Jul-2026 16:00:00",
                "data": [
                    {
                        "symbol": "RELIANCE",
                        "lastPrice": 104,
                        "pChange": 3.2,
                        "totalTradedVolume": 5_000_000,
                        "totalTradedValue": 520_000_000,
                    }
                ],
            },
            state=state,
        ),
        _result(
            "nse_most_active_value",
            {
                "timestamp": "14-Jul-2026 16:00:00",
                "data": [
                    {
                        "symbol": "RELIANCE",
                        "lastPrice": 104,
                        "pChange": 3.2,
                        "totalTradedVolume": 5_000_000,
                        "totalTradedValue": 520_000_000,
                    }
                ],
            },
            state=state,
        ),
        _result(
            "nse_large_deals_snapshot",
            {
                "as_on_date": "14-Jul-2026",
                "BULK_DEALS_DATA": [
                    {
                        "symbol": "RELIANCE",
                        "buySell": "BUY",
                        "clientName": "INSTITUTION A",
                        "qty": 100_000,
                        "watp": 100,
                    }
                ],
                "BLOCK_DEALS_DATA": [],
                "SHORT_DEALS_DATA": [],
            },
            state=state,
        ),
    ]


def test_market_activity_contract_group_is_complete() -> None:
    assert {key for key, _ in market_activity_requests()} == set(
        MARKET_ACTIVITY_ENDPOINTS
    )


def test_ranker_builds_watch_not_ready_from_confluent_activity() -> None:
    snapshot = build_market_activity_snapshot(_complete_results())

    candidate = snapshot.candidates[0]
    assert candidate.symbol == "RELIANCE"
    assert candidate.state == "WAIT_CONFIRMATION"
    assert candidate.direction == "BULLISH"
    assert candidate.activity_score >= 70
    assert candidate.deal_anchor_price == 100
    assert candidate.named_buyers == ["INSTITUTION A"]
    assert candidate.can_unlock_ready is False
    assert "NOT_WIN_PROBABILITY" in candidate.score_meaning
    assert len(candidate.required_confirmations) == 5


def test_stale_sources_cannot_create_activity_watch() -> None:
    snapshot = build_market_activity_snapshot(
        _complete_results(state=FetchState.STALE_FALLBACK)
    )

    assert snapshot.source_completeness == 0
    assert snapshot.candidates[0].state == "WAIT_STALE"
    assert snapshot.can_unlock_ready is False


def test_market_activity_snapshot_is_persisted_for_future_outcome_analysis(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "research.sqlite3"
    snapshot = build_market_activity_snapshot(_complete_results())

    save_market_activity_snapshot(snapshot, db_path)
    loaded = latest_market_activity_snapshot(limit=1, db_path=db_path)

    assert loaded.run_id == snapshot.run_id
    assert loaded.candidates[0].symbol == "RELIANCE"
    assert loaded.candidates[0].activity_score == snapshot.candidates[0].activity_score


def test_nse_seed_403_is_best_effort_when_public_api_succeeds(tmp_path: Path) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.path in {
            "/",
            "/market-data/live-equity-market",
            "/option-chain",
        }:
            return httpx.Response(403, text="seed blocked")
        if request.url.path == "/api/live-analysis-volume-gainers":
            return httpx.Response(200, json={"data": [{"symbol": "RELIANCE"}]})
        return httpx.Response(404)

    async def run() -> EndpointFetchResult:
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.fetch("nse_volume_gainers")
        finally:
            await client.aclose()

    result = asyncio.run(run())
    assert result.state == FetchState.RAW_ARCHIVED
    assert requested[:3] == [
        "https://www.nseindia.com/",
        "https://www.nseindia.com/market-data/live-equity-market",
        "https://www.nseindia.com/option-chain",
    ]
    assert "live-analysis-volume-gainers" in requested[3]


def test_large_deal_record_count_includes_all_three_arrays() -> None:
    payload = {
        "BULK_DEALS_DATA": [{"symbol": "A"}] * 2,
        "BLOCK_DEALS_DATA": [{"symbol": "B"}],
        "SHORT_DEALS_DATA": [{"symbol": "C"}] * 3,
    }
    assert AsyncEndpointClient._record_count(payload, "json") == 6


def test_market_activity_api_fetches_persists_and_returns_research_watch(
    monkeypatch,
) -> None:
    class FakeClient:
        async def fetch_many(self, requests, *, concurrency=4):
            assert {key for key, _ in requests} == set(MARKET_ACTIVITY_ENDPOINTS)
            assert concurrency == 2
            return _complete_results()

        async def aclose(self):
            return None

    saved = []
    monkeypatch.setattr(main_module, "AsyncEndpointClient", FakeClient)
    monkeypatch.setattr(
        main_module, "save_market_activity_snapshot", lambda snapshot: saved.append(snapshot)
    )

    response = TestClient(app).post("/api/market-activity/fetch?limit=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "RESEARCH_ONLY"
    assert payload["candidates"][0]["state"] == "WAIT_CONFIRMATION"
    assert payload["canUnlockReady"] is False
    assert len(saved) == 1
