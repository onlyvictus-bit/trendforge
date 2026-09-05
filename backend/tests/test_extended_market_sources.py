from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

import trendforge_api.main as main_module
from trendforge_api.institutional_sources import (
    ENDPOINTS,
    AsyncEndpointClient,
    FetchState,
    extended_market_requests,
)
from trendforge_api.main import app


EXPECTED_EXTENDED_ENDPOINTS = {
    "bse_sast",
    "bse_bulk_deals",
    "bse_block_deals",
    "mcx_option_chain",
    "mcx_market_watch",
    "mcx_delivery_reports",
    "sge_benchmark_gold",
    "baker_hughes_na_rig_count",
}


def test_extended_market_contracts_use_verified_live_routes() -> None:
    assert EXPECTED_EXTENDED_ENDPOINTS <= set(ENDPOINTS)
    assert ENDPOINTS["bse_sast"].url_template.endswith(
        "/Corporatesast/w?scripCode=&Regulation=&fromDT=&ToDate=&Isdefault="
    )
    assert "/BulkDealData_ng/w?DealType=1" in ENDPOINTS["bse_bulk_deals"].url_template
    assert "/BulkDealData_ng/w?DealType=2" in ENDPOINTS["bse_block_deals"].url_template
    assert ENDPOINTS["mcx_option_chain"].url_template.startswith(
        "https://www.mcxindia.com/backpage.aspx/GetOptionChain?"
    )
    assert ENDPOINTS["mcx_option_chain"].http_method == "POST"
    assert ENDPOINTS["mcx_option_chain"].body_kind == "json"
    assert ENDPOINTS["mcx_market_watch"].url_template.endswith(
        "/backpage.aspx/GetMarketWatch"
    )
    assert ENDPOINTS["mcx_market_watch"].http_method == "POST"
    assert ENDPOINTS["mcx_delivery_reports"].response_kind == "html"
    assert ENDPOINTS["sge_benchmark_gold"].http_method == "POST"
    assert ENDPOINTS["sge_benchmark_gold"].body_kind == "form"
    assert ENDPOINTS["baker_hughes_na_rig_count"].response_kind == "binary"


def test_extended_market_request_builder_is_bounded_and_validated() -> None:
    requests = extended_market_requests(
        scripcode="500325",
        from_date="2026-07-01",
        to_date="2026-07-14",
        mcx_symbol="GOLD",
        mcx_expiry="29JUL2026",
    )

    assert {key for key, _ in requests} == EXPECTED_EXTENDED_ENDPOINTS
    request_map = dict(requests)
    assert request_map["bse_bulk_deals"]["from_date"] == "01/07/2026"
    assert request_map["bse_block_deals"]["to_date"] == "14/07/2026"
    assert request_map["mcx_option_chain"] == {
        "symbol": "GOLD",
        "expiry": "29JUL2026",
        "Commodity": "GOLD",
        "Expiry": "29JUL2026",
    }
    assert request_map["mcx_delivery_reports"] == {}
    assert request_map["sge_benchmark_gold"] == {
        "start": "2026-07",
        "end": "2026-07",
    }


def test_post_form_binary_and_nested_json_are_archived_fail_closed(tmp_path: Path) -> None:
    requests_seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        if request.url.host == "en.sge.com.cn":
            return httpx.Response(200, json={"zp": [[1, 100.0], [2, 101.0]], "wp": [[1, 99.0]]})
        if request.url.host == "bakerhughesrigcount.gcs-web.com":
            return httpx.Response(
                200,
                content=b"PK\x03\x04workbook",
                headers={
                    "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                },
            )
        return httpx.Response(
            200,
            json={"success": True, "data": {"Summary": {}, "Data": [{"Symbol": "GOLD"}] }},
        )

    async def run():
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            sge = await client.fetch(
                "sge_benchmark_gold", {"start": "2026-07", "end": "2026-07"}
            )
            baker = await client.fetch("baker_hughes_na_rig_count")
            mcx = await client.fetch("mcx_market_watch")
            return sge, baker, mcx
        finally:
            await client.aclose()

    sge, baker, mcx = asyncio.run(run())

    assert sge.state == FetchState.RAW_ARCHIVED
    assert sge.record_count == 2
    assert requests_seen[0].method == "POST"
    assert requests_seen[0].content == b"start=2026-07&end=2026-07"

    assert baker.state == FetchState.RAW_ARCHIVED
    assert baker.record_count == 1
    assert baker.raw_path and Path(baker.raw_path).suffix == ".xlsx"
    assert baker.payload == {"byteLength": 12}

    assert mcx.state == FetchState.RAW_ARCHIVED
    assert mcx.record_count == 1
    assert all(result.can_score is False for result in (sge, baker, mcx))


def test_invalid_extended_date_range_is_rejected() -> None:
    try:
        extended_market_requests(
            scripcode="500325",
            from_date="2026-07-14",
            to_date="2026-07-01",
            mcx_symbol="GOLD",
            mcx_expiry="29JUL2026",
        )
    except ValueError as exc:
        assert "from_date" in str(exc)
    else:
        raise AssertionError("Expected invalid date range to be rejected")


def test_extended_market_batch_api_fetches_every_contract(monkeypatch) -> None:
    captured: list[tuple[str, dict[str, str]]] = []
    commodity_batches: list[list] = []

    class FakeClient:
        async def fetch_many(self, requests, *, concurrency=4):
            del concurrency
            captured.extend(requests)
            return [
                {
                    "endpointKey": key,
                    "state": "NO_DATA_NOW",
                    "fetchedAt": "2026-07-14T09:00:00Z",
                    "url": ENDPOINTS[key].url_template,
                    "recordCount": 0,
                    "canScore": False,
                    "reason": "No records now.",
                }
                for key, _ in requests
            ]

        async def aclose(self):
            return None

    monkeypatch.setattr(main_module, "AsyncEndpointClient", FakeClient)
    monkeypatch.setattr(main_module, "normalize_and_save_disclosures", lambda results: None)
    monkeypatch.setattr(
        main_module,
        "normalize_and_save_commodity_context",
        lambda results: commodity_batches.append(results),
    )
    response = TestClient(app).post(
        "/api/institutional/extended-market-sources/fetch",
        json={
            "scripcode": "500325",
            "fromDate": "2026-07-01",
            "toDate": "2026-07-14",
            "mcxSymbol": "GOLD",
            "mcxExpiry": "29JUL2026",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == len(EXPECTED_EXTENDED_ENDPOINTS)
    assert {key for key, _ in captured} == EXPECTED_EXTENDED_ENDPOINTS
    assert len(commodity_batches) == 1
    assert len(commodity_batches[0]) == len(EXPECTED_EXTENDED_ENDPOINTS)
