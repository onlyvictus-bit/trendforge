from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

import trendforge_api.main as main_module
from trendforge_api.institutional_sources import (
    CORPORATE_DISCLOSURE_ENDPOINTS,
    SCANNER_PARSER_ENDPOINTS,
    ENDPOINTS,
    AsyncEndpointClient,
    EndpointFetchResult,
    ContractStatus,
    FetchState,
    corporate_disclosure_requests,
    scanner_parser_requests,
)
from trendforge_api.main import app


EXPECTED_CORPORATE_ENDPOINTS = {
    "nse_announcements",
    "nse_shareholding_pattern",
    "nse_pledge",
    "nse_regulation_31",
    "nse_pit",
    "nse_regulation_29",
    "nse_tender_buyback",
    "bse_corporate_announcements",
    "bse_insider_trading",
    "bse_pledge_data",
}


EXPECTED_SCANNER_PARSER_ENDPOINTS = {
    *EXPECTED_CORPORATE_ENDPOINTS,
    "bse_sast",
    "bse_bulk_deals",
    "bse_block_deals",
}


def test_ten_corporate_disclosure_contracts_are_registered() -> None:
    assert set(CORPORATE_DISCLOSURE_ENDPOINTS) == EXPECTED_CORPORATE_ENDPOINTS
    assert EXPECTED_CORPORATE_ENDPOINTS <= set(ENDPOINTS)
    assert ENDPOINTS["nse_announcements"].url_template == (
        "https://www.nseindia.com/api/corporate-announcements?index=equities"
    )
    assert ENDPOINTS["nse_pit"].url_template == (
        "https://www.nseindia.com/api/corporates-pit"
    )
    assert ENDPOINTS["nse_pledge"].url_template == (
        "https://www.nseindia.com/api/corporate-pledgeData"
    )
    assert ENDPOINTS["nse_shareholding_pattern"].contract_status == ContractStatus.VERIFIED
    assert ENDPOINTS["bse_pledge_data"].timeout_seconds == 120


def test_corporate_disclosure_request_builder_covers_all_ten_sources() -> None:
    requests = corporate_disclosure_requests(
        symbol="reliance",
        scripcode="500325",
        from_date="2026-07-01",
        to_date="2026-07-14",
    )

    assert {key for key, _ in requests} == EXPECTED_CORPORATE_ENDPOINTS
    request_map = dict(requests)
    assert request_map["nse_shareholding_pattern"] == {"symbol": "RELIANCE"}
    assert request_map["bse_insider_trading"] == {
        "scripcode": "500325",
        "from_date": "01/07/2026",
        "to_date": "14/07/2026",
    }
    assert request_map["bse_corporate_announcements"]["from_date"] == "20260701"
    assert request_map["bse_pledge_data"] == {}


def test_batch_fetch_seeds_nse_and_keeps_all_raw_data_research_only(
    tmp_path: Path,
) -> None:
    requested: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request)
        if request.url.host == "www.nseindia.com" and request.url.path == "/":
            return httpx.Response(
                200,
                text="<html>NSE</html>",
                headers={"set-cookie": "nseappid=test; Path=/"},
            )
        if request.url.host == "www.nseindia.com":
            return httpx.Response(200, json={"data": [{"symbol": "RELIANCE"}]})
        return httpx.Response(200, json={"Table": []})

    async def run() -> list:
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.fetch_many(
                corporate_disclosure_requests(
                    symbol="RELIANCE",
                    scripcode="500325",
                    from_date="2026-07-01",
                    to_date="2026-07-14",
                ),
                concurrency=2,
            )
        finally:
            await client.aclose()

    results = asyncio.run(run())

    assert len(results) == 10
    assert {result.endpoint_key for result in results} == EXPECTED_CORPORATE_ENDPOINTS
    assert all(result.can_score is False for result in results)
    assert all(result.state in {FetchState.RAW_ARCHIVED, FetchState.NO_DATA_NOW} for result in results)
    assert all(result.raw_path and Path(result.raw_path).is_file() for result in results)

    assert requested[0].url == httpx.URL("https://www.nseindia.com/")
    bse_requests = [
        item for item in requested if (item.url.host or "").endswith("bseindia.com")
    ]
    assert bse_requests
    assert all(item.headers.get("referer", "").startswith("https://www.bseindia.com/") for item in bse_requests)


def test_verified_contract_result_still_cannot_score_before_normalization(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            return httpx.Response(200, text="<html>NSE</html>")
        return httpx.Response(200, json={"data": [{"symbol": "RELIANCE"}]})

    async def run():
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.fetch(
                "nse_shareholding_pattern", {"symbol": "RELIANCE"}
            )
        finally:
            await client.aclose()

    result = asyncio.run(run())

    assert result.state == FetchState.RAW_ARCHIVED
    assert result.can_score is False
    assert "schema" in (result.reason or "").lower()


def test_batch_api_exposes_one_result_per_corporate_source(monkeypatch) -> None:
    captured: list[tuple[str, dict[str, str]]] = []

    class FakeClient:
        async def fetch_many(self, requests, *, concurrency=4):
            del concurrency
            captured.extend(requests)
            return [
                EndpointFetchResult(
                    endpoint_key=key,
                    state=FetchState.NO_DATA_NOW,
                    fetched_at=datetime.fromisoformat("2026-07-14T09:00:00+00:00"),
                    url=ENDPOINTS[key].url_template,
                    record_count=0,
                    can_score=False,
                    reason="No records now.",
                )
                for key, _ in requests
            ]

        async def aclose(self):
            return None

    monkeypatch.setattr(main_module, "AsyncEndpointClient", FakeClient)
    monkeypatch.setattr(main_module, "normalize_and_save_disclosures", lambda results: None)
    response = TestClient(app).post(
        "/api/institutional/corporate-sources/fetch",
        json={
            "symbol": "RELIANCE",
            "scripcode": "500325",
            "fromDate": "2026-07-01",
            "toDate": "2026-07-14",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 10
    assert {key for key, _ in captured} == EXPECTED_CORPORATE_ENDPOINTS


def test_scanner_parser_request_builder_covers_chatgpt_thirteen_source_set() -> None:
    requests = scanner_parser_requests(
        symbol="reliance",
        scripcode="500325",
        from_date="2026-07-01",
        to_date="2026-07-14",
    )

    assert set(SCANNER_PARSER_ENDPOINTS) == EXPECTED_SCANNER_PARSER_ENDPOINTS
    assert {key for key, _ in requests} == EXPECTED_SCANNER_PARSER_ENDPOINTS
    request_map = dict(requests)
    assert request_map["nse_shareholding_pattern"] == {"symbol": "RELIANCE"}
    assert request_map["bse_bulk_deals"] == {
        "from_date": "01/07/2026",
        "to_date": "14/07/2026",
    }
    assert request_map["bse_block_deals"] == {
        "from_date": "01/07/2026",
        "to_date": "14/07/2026",
    }
    assert request_map["bse_sast"] == {}


def test_scanner_parser_cli_command_fetches_and_normalizes(monkeypatch) -> None:
    import trendforge_api.cli as cli_module

    captured: list[tuple[str, dict[str, str]]] = []
    normalized_batches: list[list] = []

    class FakeClient:
        async def fetch_many(self, requests, *, concurrency=4):
            assert concurrency == 2
            captured.extend(requests)
            return [
                EndpointFetchResult(
                    endpoint_key=key,
                    state=FetchState.NO_DATA_NOW,
                    fetched_at=datetime.fromisoformat("2026-07-14T09:00:00+00:00"),
                    url=ENDPOINTS[key].url_template,
                    record_count=0,
                    can_score=False,
                    reason="No records now.",
                )
                for key, _ in requests
            ]

        async def aclose(self):
            return None

    class FakeSnapshot:
        run_id = "RUN1"
        state = "WAIT_SOURCE"
        reason = "test"
        sources = []
        events = []

    monkeypatch.setattr(cli_module, "AsyncEndpointClient", FakeClient)
    monkeypatch.setattr(
        cli_module,
        "normalize_and_save_disclosures",
        lambda results: normalized_batches.append(results) or FakeSnapshot(),
    )
    parser = cli_module.build_parser()
    args = parser.parse_args(
        [
            "fetch-scanner-sources",
            "--symbol",
            "RELIANCE",
            "--scripcode",
            "500325",
            "--from-date",
            "2026-07-01",
            "--to-date",
            "2026-07-14",
            "--concurrency",
            "2",
        ]
    )

    payload, status = asyncio.run(cli_module.fetch_scanner_parser_sources(args))

    assert status == 0
    assert payload["sourceCount"] == 13
    assert payload["validEmptyCount"] == 13
    assert {key for key, _ in captured} == EXPECTED_SCANNER_PARSER_ENDPOINTS
    assert len(normalized_batches) == 1
