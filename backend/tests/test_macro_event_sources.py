from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

import trendforge_api.main as main_module
from trendforge_api.institutional_sources import (
    ENDPOINTS,
    FetchState,
    MACRO_EVENT_ENDPOINTS,
    EndpointFetchResult,
    macro_event_requests,
)
from trendforge_api.macro_event_context import (
    build_macro_event_context_snapshot,
    latest_macro_event_context_snapshot,
    save_macro_event_context_snapshot,
)
from trendforge_api.main import app


EXPECTED_MACRO_EVENT_ENDPOINTS = {
    "usda_wasde",
    "dgcis_trade_data",
    "imd_rainfall_timeseries",
    "des_crop_estimates",
    "shfe_weekly_stock",
    "china_nbs_indicator",
    "mcx_future_prices",
    "mcx_trading_holidays",
    "mcx_circulars",
    "fbil_usdinr_reference",
    "bse_xbrl_announcements",
    "nse_xbrl_taxonomy",
    "nse_pit_annual",
    "nse_shareholding_pattern",
    "mca_company_master_data",
    "cdsl_fpi_fortnightly",
    "rbi_fpi_caution",
    "msei_fii_dii",
    "cftc_legacy_futures_only",
    "cftc_disagg_futures_only",
    "cftc_tff_futures_only",
    "cftc_release_schedule",
    "eia_petroleum_schedule",
}


def _result(
    endpoint_key: str,
    *,
    state: FetchState = FetchState.RAW_ARCHIVED,
    record_count: int = 1,
) -> EndpointFetchResult:
    return EndpointFetchResult(
        endpointKey=endpoint_key,
        state=state,
        fetchedAt=datetime(2026, 7, 15, 12, tzinfo=UTC),
        url=ENDPOINTS[endpoint_key].url_template,
        contentHash=f"hash-{endpoint_key}",
        rawPath=f"D:/raw/{endpoint_key}.json",
        mediaType="application/json",
        recordCount=record_count,
        payload={"data": [{"row": 1}]} if record_count else {"data": []},
        canScore=False,
        reason="fixture",
    )


def test_macro_event_contracts_cover_all_declared_sources() -> None:
    assert set(MACRO_EVENT_ENDPOINTS) == EXPECTED_MACRO_EVENT_ENDPOINTS
    assert EXPECTED_MACRO_EVENT_ENDPOINTS <= set(ENDPOINTS)
    assert ENDPOINTS["usda_wasde"].required_parameters == ("year_month",)
    assert ENDPOINTS["shfe_weekly_stock"].required_parameters == ("date_str",)
    assert ENDPOINTS["mcx_future_prices"].http_method == "POST"
    assert ENDPOINTS["mcx_future_prices"].body_parameters == ("Date",)
    assert ENDPOINTS["mcx_trading_holidays"].http_method == "POST"
    assert ENDPOINTS["mcx_circulars"].body_parameters == ("PageNo", "Records")
    assert ENDPOINTS["bse_xbrl_announcements"].required_parameters == (
        "category",
        "scripcode",
    )
    assert ENDPOINTS["nse_pit_annual"].requires_nse_session is True
    assert ENDPOINTS["nse_shareholding_pattern"].requires_nse_session is True
    assert ENDPOINTS["cftc_disagg_futures_only"].response_kind == "json"
    assert "publicreporting.cftc.gov" in ENDPOINTS["cftc_tff_futures_only"].url_template
    assert ENDPOINTS["cftc_release_schedule"].response_kind == "html"
    assert ENDPOINTS["eia_petroleum_schedule"].response_kind == "html"


def test_macro_event_request_builder_is_bounded_and_parameterized() -> None:
    requests = macro_event_requests(
        symbol="RELIANCE",
        scripcode="500325",
        year_month="0726",
        shfe_date="20260710",
        mcx_date="15/07/2026",
        year=2026,
        nbs_indicator_code="A0B01",
        bse_category="Company Update",
    )
    request_map = dict(requests)

    assert set(request_map) == EXPECTED_MACRO_EVENT_ENDPOINTS
    assert request_map["usda_wasde"] == {"year_month": "0726"}
    assert request_map["shfe_weekly_stock"] == {"date_str": "20260710"}
    assert request_map["mcx_future_prices"] == {"Date": "15/07/2026"}
    assert request_map["mcx_circulars"] == {"PageNo": "1", "Records": "50"}
    assert request_map["bse_xbrl_announcements"] == {
        "category": "Company Update",
        "scripcode": "500325",
    }
    assert request_map["nse_pit_annual"] == {
        "from_date": "01-01-2026",
        "to_date": "31-12-2026",
    }
    assert request_map["nse_shareholding_pattern"] == {"symbol": "RELIANCE"}
    assert request_map["cftc_legacy_futures_only"] == {}
    assert request_map["cftc_disagg_futures_only"] == {}
    assert request_map["cftc_tff_futures_only"] == {}


def test_invalid_macro_parameters_are_rejected() -> None:
    try:
        macro_event_requests(
            symbol="../BAD",
            scripcode="500325",
            year_month="0726",
            shfe_date="20260710",
            mcx_date="15/07/2026",
            year=2026,
        )
    except ValueError as exc:
        assert "symbol" in str(exc)
    else:
        raise AssertionError("Expected invalid symbol to be rejected")


def test_macro_event_snapshot_is_research_only_and_reports_missing_sources() -> None:
    results = [
        _result("usda_wasde"),
        _result("shfe_weekly_stock"),
        _result("eia_petroleum_schedule", state=FetchState.BROKEN, record_count=0),
    ]

    snapshot = build_macro_event_context_snapshot(results)

    assert snapshot.state == "WAIT_PARTIAL_SOURCE"
    assert snapshot.source_completeness == round(2 / len(MACRO_EVENT_ENDPOINTS), 4)
    assert snapshot.can_unlock_ready is False
    assert "eia_petroleum_schedule" in snapshot.missing_source_keys
    assert "mcx_circulars" in snapshot.missing_source_keys
    assert snapshot.sources[0].scanner_use == "AGRI_REGIME"
    assert snapshot.sources[0].can_unlock_ready is False


def test_macro_event_snapshot_persists_and_restores(tmp_path: Path) -> None:
    snapshot = build_macro_event_context_snapshot([_result(key) for key in MACRO_EVENT_ENDPOINTS])
    database = tmp_path / "macro.sqlite3"

    save_macro_event_context_snapshot(snapshot, db_path=database)
    restored = latest_macro_event_context_snapshot(db_path=database)

    assert restored.run_id == snapshot.run_id
    assert restored.state == "RESEARCH_ONLY"
    assert len(restored.sources) == len(MACRO_EVENT_ENDPOINTS)
    assert restored.can_unlock_ready is False


def test_macro_event_batch_api_fetches_all_sources_and_saves(monkeypatch) -> None:
    captured: list[tuple[str, dict[str, str]]] = []
    saved = []

    class FakeClient:
        async def fetch_many(self, requests, *, concurrency=4):
            del concurrency
            captured.extend(requests)
            return [_result(key) for key, _ in requests]

        async def aclose(self):
            return None

    monkeypatch.setattr(main_module, "AsyncEndpointClient", FakeClient)
    monkeypatch.setattr(
        main_module,
        "save_macro_event_context_snapshot",
        lambda snapshot: saved.append(snapshot),
    )

    response = TestClient(app).post(
        "/api/institutional/macro-event-sources/fetch",
        json={
            "symbol": "RELIANCE",
            "scripcode": "500325",
            "yearMonth": "0726",
            "shfeDate": "20260710",
            "mcxDate": "15/07/2026",
            "year": 2026,
        },
    )

    assert response.status_code == 200
    assert {key for key, _ in captured} == EXPECTED_MACRO_EVENT_ENDPOINTS
    assert response.json()["state"] == "RESEARCH_ONLY"
    assert response.json()["sourceCompleteness"] == 1
    assert len(saved) == 1
    assert len(saved[0].sources) == len(MACRO_EVENT_ENDPOINTS)
