"""File A S2 market weather tests: honest percent, context never votes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.parsers.nse_index_close_parser import parse_nse_index_close
from trendforge_api.selection.s2_market_weather import (
    S2MarketWeatherV1,
    build_s2_market_weather,
)

DECISION_AT = datetime(2026, 8, 14, 17, 0, tzinfo=UTC)


def _csv_row(name: str, close: str, change: str, extra: str = "") -> str:
    return f"{name},{close},,{change}{extra}"


def _loader_factory(index_rows=None, breadth_rows=None, mcx_rows=None):
    def _load(key):
        if key == "nse_index_close_eod" and index_rows is not None:
            return {
                "parserState": "PARSED_STRUCTURED",
                "dataDate": "2026-08-14",
                "output": {"rows": index_rows},
            }
        if key in {"nse_pr_market_snapshot", "nse_market_status"} and breadth_rows:
            return {
                "parserState": "PARSED_STRUCTURED",
                "dataDate": "2026-08-14",
                "output": {"rows": breadth_rows},
            }
        if key == "mcx_bhavcopy_daily" and mcx_rows is not None:
            return {
                "parserState": "PARSED_STRUCTURED",
                "dataDate": "2026-08-14",
                "output": {"rows": mcx_rows},
            }
        return None

    return _load


# ---------------------------------------------------------------------------
# T1 points are never percent: the 20.15 bug, fixed at parse time
# ---------------------------------------------------------------------------


def test_t1_points_never_percent_in_parser() -> None:
    csv = "\n".join(
        [
            "Index Name,Closing Index Value,Index Date,Change",
            "NIFTY 50,24050.00,2026-08-14,20.15",
            "INDIA VIX,13.9,2026-08-14,0.4",
        ]
    )
    result = parse_nse_index_close(csv.encode())
    assert result["parser_state"] == "PARSED_STRUCTURED"
    nifty = next(r for r in result["output"]["rows"] if r["indexName"] == "NIFTY 50")
    # 20.15 was points; close 24050 vs previous (24050-20.15) is ~0.084%.
    assert nifty["changePercent"] == pytest.approx(0.0838, abs=1e-3)
    assert nifty["changePercentStatus"] == "RECOMPUTED_FROM_POINTS"


# ---------------------------------------------------------------------------
# T2 official JSON percent key wins over variation points
# ---------------------------------------------------------------------------


def test_t2_official_percent_key_wins() -> None:
    csv = "\n".join(
        [
            "Index Name,Closing Index Value,Previous Close,Variation,Percent Change,Index Date",
            "NIFTY 50,24383.60,24317.15,66.45,0.27,2026-08-14",
            "INDIA VIX,13.9,13.5,0.4,2.96,2026-08-14",
        ]
    )
    result = parse_nse_index_close(csv.encode())
    nifty = next(r for r in result["output"]["rows"] if r["indexName"] == "NIFTY 50")
    assert result["parser_state"] == "PARSED_STRUCTURED"
    assert nifty["changePercent"] == pytest.approx(0.27)
    assert nifty["changePercentStatus"] == "OFFICIAL_PERCENT_KEY"


# ---------------------------------------------------------------------------
# T3 rejected parse fails closed to null + code, never a pretty zero
# ---------------------------------------------------------------------------


def test_t3_rejected_parse_is_null_not_zero() -> None:
    csv = "\n".join(
        [
            "Index Name,Closing Index Value,Index Date",
            "NIFTY 50,24000.00,2026-08-14",
            "INDIA VIX,13.5,2026-08-14",
        ]
    )
    result = parse_nse_index_close(csv.encode())
    nifty = next(r for r in result["output"]["rows"] if r["indexName"] == "NIFTY 50")
    assert nifty["changePercent"] is None
    assert nifty["changePercentStatus"] == "INDEX_PCT_PARSE_REJECTED"


def test_t3b_live_leak_variation_points_rejected_without_corroboration() -> None:
    """Real last-good once carried percentChange=66.95 (actually variation
    points) with no points/previous columns to compare against."""
    csv = "\n".join(
        [
            "Index Name,Closing Index Value,Index Date,Percent Change",
            "NIFTY 50,24317.15,2026-07-30,66.95",
            "INDIA VIX,13.4,2026-07-30,0.5",
        ]
    )
    result = parse_nse_index_close(csv.encode())
    nifty = next(r for r in result["output"]["rows"] if r["indexName"] == "NIFTY 50")
    assert nifty["changePercent"] is None
    assert nifty["changePercentStatus"] == "INDEX_PCT_PARSE_REJECTED"


# ---------------------------------------------------------------------------
# T4/T7/T8 weather DTO: bands, grey global, ceilings, no stock vote
# ---------------------------------------------------------------------------


def test_t4_t7_t8_weather_contract(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s2.db")
    index_rows = [
        {
            "indexName": "NIFTY 50",
            "close": 24050.0,
            "previousClose": 24029.85,
            "pointsChange": 20.15,
            "changePercent": 0.0838,
            "changePercentStatus": "RECOMPUTED_FROM_POINTS",
        },
        {
            "indexName": "INDIA VIX",
            "close": 13.9,
            "changePercent": 2.96,
            "changePercentStatus": "OFFICIAL_PERCENT_KEY",
        },
        {
            "indexName": "NIFTY IT",
            "close": 38000.0,
            "changePercent": -0.4,
            "changePercentStatus": "OFFICIAL_PERCENT_KEY",
        },
        {
            "indexName": "NIFTY METAL",
            "close": 9000.0,
            "changePercent": 1.2,
            "changePercentStatus": "OFFICIAL_PERCENT_KEY",
        },
    ]
    weather = build_s2_market_weather(loader=_loader_factory(index_rows=index_rows))
    assert weather.nifty50.changePercent == pytest.approx(0.0838, abs=1e-3)
    assert weather.indiaVix.band == "NORMAL"
    # Sector ranks come from official rows, leader first.
    assert weather.sectors[0].name == "NIFTY METAL"
    assert weather.sectors[0].rank == 1
    assert all(g.canDirectContract is False for g in weather.commodityGlobal)
    assert weather.canUnlockConfirmed is False
    assert weather.sourceActivationReady is False
    assert weather.canRank is False
    assert weather.regimeLabel in {"RISK_ON", "RISK_OFF", "MIXED", "RANGE", "UNKNOWN"}
    # Breadth missing stays UNKNOWN, never invented 0/0.
    assert weather.breadth.status.startswith("UNKNOWN")
    assert weather.breadth.advances is None


def test_vix_high_cannot_become_stock_direction(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s2-vix.db")
    index_rows = [
        {
            "indexName": "NIFTY 50",
            "close": 24000.0,
            "previousClose": 23800.0,
            "pointsChange": 200.0,
            "changePercent": 0.84,
            "changePercentStatus": "OFFICIAL_PERCENT_KEY",
        },
        {
            "indexName": "INDIA VIX",
            "close": 25.0,
            "changePercent": 10.0,
            "changePercentStatus": "OFFICIAL_PERCENT_KEY",
        },
    ]
    weather = build_s2_market_weather(loader=_loader_factory(index_rows=index_rows))
    # Nifty up but VIX HIGH blocks RISK_ON: weather is mixed, not a buy call.
    assert weather.indiaVix.band == "HIGH"
    assert weather.regimeLabel != "RISK_ON"


# ---------------------------------------------------------------------------
# T5 missing breadth is UNKNOWN, not 0/0; present breadth computes ratio
# ---------------------------------------------------------------------------


def test_t5_missing_breadth_unknown_present_breadth_rated(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s2-breadth.db")
    index_rows = [
        {
            "indexName": "NIFTY 50",
            "close": 100.0,
            "previousClose": 99.0,
            "pointsChange": 1.0,
            "changePercent": 1.01,
            "changePercentStatus": "RECOMPUTED_FROM_PREVIOUS_CLOSE",
        },
        {
            "indexName": "INDIA VIX",
            "close": 13.0,
            "changePercent": 0.5,
            "changePercentStatus": "OFFICIAL_PERCENT_KEY",
        },
    ]
    missing = build_s2_market_weather(loader=_loader_factory(index_rows=index_rows))
    assert missing.breadth.advances is None
    assert missing.breadth.declines is None
    assert missing.breadth.ratio is None

    present = build_s2_market_weather(
        loader=_loader_factory(
            index_rows=index_rows,
            breadth_rows=[{"advances": 1500, "declines": 500, "unchanged": 300}],
        )
    )
    assert present.breadth.advances == 1500
    assert present.breadth.ratio == pytest.approx(3.0)
    assert present.breadth.status == "BREADTH_RISK_ON"


# ---------------------------------------------------------------------------
# T7 local MCX percent only from local bars; global stays grey
# ---------------------------------------------------------------------------


def test_t7_commodity_local_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s2-mcx.db")
    index_rows = [
        {
            "indexName": "NIFTY 50",
            "close": 100.0,
            "previousClose": 99.0,
            "pointsChange": 1.0,
            "changePercent": 1.01,
            "changePercentStatus": "OK",
        },
        {
            "indexName": "INDIA VIX",
            "close": 13.0,
            "changePercent": 0.5,
            "changePercentStatus": "OK",
        },
    ]
    weather_no_local = build_s2_market_weather(loader=_loader_factory(index_rows=index_rows))
    assert weather_no_local.commodityLocal == ()
    assert "UNKNOWN_NO_LOCAL_MCX_BAR" in weather_no_local.whyUnknown

    weather_local = build_s2_market_weather(
        loader=_loader_factory(
            index_rows=index_rows,
            mcx_rows=[
                {"symbol": "GOLDM", "close": 72000.0, "previousClose": 71000.0},
            ],
        )
    )
    gold = next(c for c in weather_local.commodityLocal if c.symbol == "GOLD")
    assert gold.changePercent == pytest.approx(1.41, abs=0.02)
    assert gold.status == "CURRENT_LOCAL_BAR"
    assert all(g.canDirectContract is False for g in weather_local.commodityGlobal)


def test_breadth_from_official_cash_session_when_snapshot_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s2-cash-ad.db")
    from trendforge_api.selection import s2_market_weather as mod
    from trendforge_api.selection.s2_market_weather import BreadthV1

    monkeypatch.setattr(
        mod,
        "_breadth_from_official_cash_session",
        lambda: BreadthV1(
            advances=1400,
            declines=900,
            unchanged=40,
            ratio=1.5556,
            status="BREADTH_RISK_ON",
        ),
    )
    index_rows = [
        {
            "indexName": "NIFTY 50",
            "close": 24050.0,
            "previousClose": 24029.85,
            "pointsChange": 20.15,
            "changePercent": 0.0838,
        },
        {"indexName": "INDIA VIX", "close": 13.9, "changePercent": 0.4},
    ]
    weather = build_s2_market_weather(loader=_loader_factory(index_rows=index_rows))
    assert weather.breadth.advances == 1400
    assert weather.breadth.declines == 900
    assert "BREADTH_FROM_OFFICIAL_CASH_BHAVCOPY" in weather.why
    assert weather.canUnlockConfirmed is False


# ---------------------------------------------------------------------------
# T8 payload ceiling flips rejected; T9 routes
# ---------------------------------------------------------------------------


def test_t8_ceiling_validators(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s2-t8.db")
    weather = build_s2_market_weather(loader=_loader_factory(index_rows=[]))
    payload = weather.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError):
        S2MarketWeatherV1.model_validate({**payload, "canUnlockConfirmed": True})
    with pytest.raises(ValidationError):
        S2MarketWeatherV1.model_validate({**payload, "canRank": True})


def test_t9_routes(monkeypatch) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/api/v1/selection/market-weather").status_code == 405
    assert client.post("/api/v1/selection/market-weather/sectors").status_code == 405

    from trendforge_api import main as main_module

    real = main_module.build_s2_market_weather

    def _boom(**_kwargs):
        raise ValueError("S2_LAST_GOOD_MISSING")

    monkeypatch.setattr(main_module, "build_s2_market_weather", _boom)
    response = client.get("/api/v1/selection/market-weather")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "S2_LAST_GOOD_MISSING"
    monkeypatch.setattr(main_module, "build_s2_market_weather", real)


def test_stale_sector_points_recomputed_and_mcx_bhavcopy_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s2-fill.db")
    index_rows = [
        {
            # Stored old-parser row: points copied into changePercent.
            "indexName": "NIFTY METAL",
            "close": 12701.8,
            "pointsChange": 15.0,
            "changePercent": 15.0,
        },
        {
            "indexName": "INDIA VIX",
            "close": 13.4,
            "changePercent": 0.5,
        },
        {
            "indexName": "NIFTY 50",
            "close": 24317.15,
            "pointsChange": 66.45,
            "changePercent": 66.95,
        },
    ]
    weather = build_s2_market_weather(
        loader=_loader_factory(
            index_rows=index_rows,
            mcx_rows=[
                {
                    "symbol": "ALUMINI",
                    "expiry": "31JUL2026",
                    "close": 337.15,
                    "previousClose": 334.0,
                    "oiChange": 0,
                }
            ],
        ),
    )
    metal = next(s for s in weather.sectors if s.name == "NIFTY METAL")
    assert metal.changePercent == pytest.approx(0.1182, abs=1e-3)
    nifty = weather.nifty50
    assert nifty.changePercent == pytest.approx(0.2735, abs=1e-2)
    aluminium = [c for c in weather.commodityLocal if c.symbol == "ALUMINIUM"]
    assert len(aluminium) == 1
    assert aluminium[0].changePercent == pytest.approx(0.943, abs=1e-2)
