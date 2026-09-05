from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from trendforge_api.institutional_ai import (
    IsolationForestAdapter,
    ModelState,
    blend_probabilities,
    model_capabilities,
)
from trendforge_api.institutional_backtest import (
    WalkForwardPoint,
    walk_forward_validate,
)
from trendforge_api.institutional_config import load_institutional_config
from trendforge_api.institutional_engine import (
    FactorSnapshot,
    HardFilterSnapshot,
    InstitutionalAnalysisRequest,
    analyze_institutional,
)
from trendforge_api.institutional_features import build_institutional_features
from trendforge_api.institutional_sources import (
    ENDPOINTS,
    AsyncEndpointClient,
    FetchState,
)
from trendforge_api.main import app


REQUIRED_ENDPOINTS = {
    "nse_all_indices",
    "nse_market_turnover",
    "nse_preopen_nifty",
    "nse_preopen_fo",
    "nse_preopen_sme",
    "nse_quote_equity",
    "nse_quote_equity_trade_info",
    "nse_index_nifty50",
    "nse_index_banknifty",
    "nse_index_midcap100",
    "nse_index_smallcap100",
    "nse_quote_derivative",
    "nse_live_equity_derivatives_index_opt",
    "nse_live_equity_derivatives_index_fut",
    "nse_live_equity_derivatives_banknifty_opt",
    "nse_live_equity_derivatives_banknifty_fut",
    "nse_option_chain_nifty",
    "nse_option_chain_banknifty",
    "nse_option_chain_equity",
    "nse_oi_spurts",
    "nse_most_active_underlying",
    "nse_variations_gainers",
    "nse_variations_loosers",
    "nse_fii_dii",
    "nse_asm",
    "nse_gsm",
    "nse_pledge",
    "nse_pit",
    "nse_pit_symbol",
    "nse_block_deal",
    "nse_bulk_deal_symbol",
    "nse_corporate_actions",
    "nse_announcements",
    "nse_financial_results",
    "nse_slb",
    "bse_scrip_header",
    "bse_sensex",
    "amfi_nav",
    "mfapi_schemes",
    "mfapi_history",
    "nsdl_fpi",
    "nsdl_fpi_daily_reportdetail",
    "cftc_legacy_futures_only",
    "cftc_disagg_futures_only",
    "cftc_tff_futures_only",
}


def _valid_request(**updates: object) -> InstitutionalAnalysisRequest:
    values: dict[str, object] = {
        "symbol": "RELIANCE",
        "as_of": datetime(2026, 7, 13, 15, 30, tzinfo=UTC),
        "factors": FactorSnapshot(
            smart_money=2.2,
            trend=2.0,
            volatility=1.6,
            momentum=1.8,
            fundamental=1.5,
            risk=1.4,
        ),
        "hard_filters": HardFilterSnapshot(),
        "source_ready": True,
        "models_ready": True,
        "anomaly_state": "CLEAR",
        "model_probabilities": {
            "hmm": 0.78,
            "random_forest": 0.80,
            "xgboost": 0.79,
            "lstm": 0.77,
        },
        "entry": 150.0,
        "stop": 145.0,
        "target": 160.0,
    }
    values.update(updates)
    return InstitutionalAnalysisRequest.model_validate(values)


def test_default_configuration_is_valid_and_weights_sum_to_one() -> None:
    config = load_institutional_config()

    assert config.risk.account_size == 100_000
    assert sum(config.weights.model_dump().values()) == pytest.approx(1.0)
    assert config.screening.bull_threshold > config.screening.neutral_zone
    assert config.config_hash


def test_all_submitted_endpoints_are_preserved_as_contracts() -> None:
    assert REQUIRED_ENDPOINTS <= set(ENDPOINTS)
    assert ENDPOINTS["nse_quote_equity"].requires_nse_session is True
    assert ENDPOINTS["bse_sensex"].requires_nse_session is False
    assert (
        "index=nse50_opt"
        in ENDPOINTS["nse_live_equity_derivatives_index_opt"].url_template
    )
    assert (
        "index=nifty_bank_fut"
        in ENDPOINTS["nse_live_equity_derivatives_banknifty_fut"].url_template
    )
    assert ENDPOINTS["nse_option_chain_equity"].required_parameters == (
        "symbol",
        "expiry",
    )
    assert "option-chain-v3" in ENDPOINTS["nse_option_chain_equity"].url_template


def test_nse_option_chain_accepts_supported_exchange_expiry_formats() -> None:
    AsyncEndpointClient._validate_parameters(
        ENDPOINTS["nse_option_chain_equity"],
        {"symbol": "RELIANCE", "expiry": "25-Aug-2026"},
    )
    AsyncEndpointClient._validate_parameters(
        ENDPOINTS["nse_option_chain_equity"],
        {"symbol": "RELIANCE", "expiry": "2026-08-25"},
    )
    with pytest.raises(ValueError, match="expiry must use"):
        AsyncEndpointClient._validate_parameters(
            ENDPOINTS["nse_option_chain_equity"],
            {"symbol": "RELIANCE", "expiry": "25/08/2026"},
        )


def test_async_fetcher_seeds_nse_session_and_archives_structured_response(
    tmp_path: Path,
) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.path == "/":
            return httpx.Response(
                200,
                text="<html>NSE</html>",
                headers={"set-cookie": "nseappid=test; Path=/"},
            )
        if request.url.path == "/api/allIndices":
            return httpx.Response(
                200,
                json={"data": [{"index": "NIFTY 50", "last": 25100.0}]},
            )
        return httpx.Response(404)

    async def run() -> None:
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            result = await client.fetch("nse_all_indices")
        finally:
            await client.aclose()

        assert result.state == FetchState.RAW_ARCHIVED
        assert result.can_score is False
        assert result.record_count == 1
        assert result.content_hash
        assert result.raw_path and Path(result.raw_path).is_file()

    asyncio.run(run())
    assert requested[:3] == [
        "https://www.nseindia.com/",
        "https://www.nseindia.com/market-data/live-equity-market",
        "https://www.nseindia.com/option-chain",
    ]
    assert requested[3] == "https://www.nseindia.com/api/allIndices"


def test_failed_refresh_returns_visible_stale_fallback_that_cannot_score(
    tmp_path: Path,
) -> None:
    api_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal api_calls
        if request.url.path in {
            "/",
            "/market-data/live-equity-market",
            "/option-chain",
        }:
            return httpx.Response(200, text="<html>NSE</html>")
        api_calls += 1
        if api_calls == 1:
            return httpx.Response(200, json={"data": [{"index": "NIFTY 50"}]})
        return httpx.Response(503, text="temporarily unavailable")

    async def run() -> None:
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            first = await client.fetch("nse_all_indices")
            second = await client.fetch("nse_all_indices", force=True)
        finally:
            await client.aclose()

        assert first.state == FetchState.RAW_ARCHIVED
        assert second.state == FetchState.STALE_FALLBACK
        assert second.can_score is False
        assert "503" in (second.reason or "")

    asyncio.run(run())


def test_wrong_content_is_archived_before_json_parse_failure(tmp_path: Path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    async def run() -> None:
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            result = await client.fetch("bse_sensex")
        finally:
            await client.aclose()

        assert result.state == FetchState.WRONG_CONTENT
        assert result.can_score is False
        assert result.content_hash
        assert (
            result.raw_path
            and Path(result.raw_path).read_text() == "<html>not json</html>"
        )

    asyncio.run(run())


def test_feature_engine_produces_finite_multi_factor_metrics() -> None:
    candles: list[dict[str, float | str]] = []
    start = datetime(2025, 1, 1, tzinfo=UTC)
    for index in range(260):
        close = 100.0 + (index * 0.15) + ((index % 11) - 5) * 0.08
        candles.append(
            {
                "timestamp": (start + timedelta(days=index)).isoformat(),
                "open": close - 0.4,
                "high": close + 1.0,
                "low": close - 1.1,
                "close": close,
                "volume": 1_000_000.0 + (index * 2_000),
                "barState": "COMPLETE",
            }
        )

    result = build_institutional_features(candles, var_confidence=0.95)

    assert result.state == "OK"
    assert result.feature_registry_version == "1.1.0"
    assert result.indicator_engine_id == "trendforge.numpy-pandas"
    assert result.indicator_engine_version == "1.0.0"
    for key in {
        "ema_20",
        "ema_50",
        "ema_200",
        "rsi_14",
        "atr_14",
        "adx_14",
        "macd",
        "bollinger_width",
        "obv",
        "cmf_20",
        "var_historical",
        "cvar_historical",
        "max_drawdown",
    }:
        assert key in result.values
        assert result.values[key] is not None
    assert result.missing == []


def test_complete_fixture_can_classify_bullish_but_remains_watch_only() -> None:
    result = analyze_institutional(_valid_request())

    assert result.classification == "BULLISH"
    assert result.state == "WATCH"
    assert result.executable is False
    assert result.suggested_quantity == 0
    assert result.bull_probability >= 0.70


def test_missing_factor_fails_closed_and_cannot_size() -> None:
    request = _valid_request(
        factors=FactorSnapshot(
            smart_money=2.2,
            trend=2.0,
            volatility=None,
            momentum=1.8,
            fundamental=1.5,
            risk=1.4,
        )
    )

    result = analyze_institutional(request)

    assert result.classification == "WATCHLIST"
    assert result.state == "WAIT_DATA_WEAK"
    assert result.suggested_quantity == 0
    assert "volatility" in result.missing_factors


def test_hard_surveillance_filter_forces_no_trade() -> None:
    request = _valid_request(
        hard_filters=HardFilterSnapshot(gsm=True, pledge_percent=55.0)
    )

    result = analyze_institutional(request)

    assert result.classification == "NO_TRADE"
    assert result.state == "REJECT_HARD_FILTER"
    assert result.suggested_quantity == 0
    assert any("GSM" in reason for reason in result.reasons)


def test_untrained_ai_models_are_explicit_and_block_ready() -> None:
    request = _valid_request(models_ready=False, model_probabilities={})

    result = analyze_institutional(request)

    assert result.classification == "WATCHLIST"
    assert result.state == "WAIT_MODEL_UNTRAINED"
    assert result.suggested_quantity == 0


def test_anomaly_model_is_a_veto_gate() -> None:
    result = analyze_institutional(_valid_request(anomaly_state="ANOMALY"))

    assert result.classification == "WATCHLIST"
    assert result.state == "WAIT_MODEL_ANOMALY"
    assert result.suggested_quantity == 0


def test_ai_capability_registry_and_weighted_blend_do_not_hide_missing_models() -> None:
    capabilities = model_capabilities()
    assert {"hmm", "isolation_forest", "random_forest", "xgboost", "lstm"} <= set(
        capabilities
    )
    assert capabilities["lstm"].state in {
        ModelState.DEPENDENCY_MISSING,
        ModelState.UNTRAINED,
    }

    blended = blend_probabilities(
        probabilities={"hmm": 0.8, "random_forest": 0.7},
        weights={"hmm": 0.4, "random_forest": 0.2, "xgboost": 0.4},
        required_models={"hmm", "random_forest", "xgboost"},
    )
    assert blended.ready is False
    assert blended.probability is None
    assert blended.missing_models == ["xgboost"]


def test_isolation_forest_is_an_anomaly_gate_not_a_direction_probability() -> None:
    model = IsolationForestAdapter(contamination=0.05, random_state=7)
    training = [[index / 100, index / 200] for index in range(100)]
    model.fit(training)

    normal = model.assess([0.5, 0.25])
    outlier = model.assess([20.0, -20.0])

    assert normal.model_state == ModelState.READY
    assert normal.anomaly_score > outlier.anomaly_score
    assert outlier.is_anomaly is True


def test_walk_forward_validation_never_trains_on_current_or_future_outcome() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    points = [
        WalkForwardPoint(
            as_of=start + timedelta(days=index),
            factor_score=2.0 if index % 2 == 0 else -2.0,
            forward_return=0.02 if index % 2 == 0 else -0.015,
        )
        for index in range(40)
    ]

    report = walk_forward_validate(points, min_train_size=20)

    assert report.evaluation_count == 20
    assert report.lookahead_detected is False
    assert all(row.training_end < row.as_of for row in report.predictions)
    assert report.win_rate == pytest.approx(1.0)


def test_institutional_api_exposes_config_and_every_endpoint_contract() -> None:
    client = TestClient(app)

    config_response = client.get("/api/institutional/config")
    source_response = client.get("/api/institutional/sources")

    assert config_response.status_code == 200
    assert config_response.json()["configHash"]
    assert source_response.status_code == 200
    returned = {row["key"] for row in source_response.json()["endpoints"]}
    assert REQUIRED_ENDPOINTS <= returned


def test_institutional_analysis_api_cannot_self_certify_source_or_model_readiness() -> (
    None
):
    client = TestClient(app)
    payload = _valid_request().model_dump(mode="json")

    response = client.post(
        "/api/institutional/analyze?persist=false",
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["classification"] == "WATCHLIST"
    assert body["state"] == "WAIT_SOURCE_STRUCTURED_PENDING"
    assert body["executable"] is False
    assert body["suggestedQuantity"] == 0


def test_institutional_walk_forward_api_returns_auditable_predictions() -> None:
    client = TestClient(app)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    payload = {
        "points": [
            {
                "asOf": (start + timedelta(days=index)).isoformat(),
                "factorScore": 2 if index % 2 == 0 else -2,
                "forwardReturn": 0.01 if index % 2 == 0 else -0.01,
            }
            for index in range(30)
        ],
        "minTrainSize": 20,
    }

    response = client.post("/api/institutional/backtest", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["evaluationCount"] == 10
    assert body["lookaheadDetected"] is False
