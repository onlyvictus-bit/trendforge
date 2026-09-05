from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.demo_data import generate_demo_daily_candles
from trendforge_api.main import app
from trendforge_api.market_context import (
    MarketContextInput,
    SectorContextInput,
    evaluate_market_context,
    evaluate_sector_context,
)
from trendforge_api.parsers.nse_instrument_parser import parse_nse_instruments
from trendforge_api.source_parser import parse_source_content
from trendforge_api.source_resolver import direct_download_candidates
from trendforge_api.scanner_scheduler import ScannerScheduler


AS_OF = datetime(2026, 7, 11, 16, 0, tzinfo=timezone.utc)


def rising_series(start: float, count: int, step: float) -> list[float]:
    return [start + index * step for index in range(count)]


def test_official_nse_equity_and_nifty500_files_parse_identity_and_sector() -> None:
    equity = (
        "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\n"
        "INFY,Infosys Limited,EQ,08-Feb-1995,5,1,INE009A01021,5\n"
    ).encode()
    parsed_equity = parse_nse_instruments(
        equity, last_modified="Thu, 09 Jul 2026 21:35:03 GMT"
    )
    row = parsed_equity["output"]["rows"][0]
    assert row["symbol"] == "INFY"
    assert row["isin"] == "INE009A01021"
    assert row["scope"] == "ALL_NSE_EQUITY"
    assert parsed_equity["data_date"] == "2026-07-09"

    constituents = (
        "Company Name,Industry,Symbol,Series,ISIN Code\n"
        "Infosys Limited,Information Technology,INFY,EQ,INE009A01021\n"
    ).encode()
    parsed_sector = parse_nse_instruments(
        constituents,
        url="https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
        last_modified="2026-07-11",
    )
    sector_row = parsed_sector["output"]["rows"][0]
    assert sector_row["industry"] == "Information Technology"
    assert sector_row["indexMembership"] == "NIFTY500"

    assert direct_download_candidates("nse_equity_universe") == [
        "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    ]
    assert direct_download_candidates("nse_nifty500_constituents") == [
        "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
    ]
    parsed_nifty50 = parse_nse_instruments(
        constituents,
        url="https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
        last_modified="2026-07-11",
    )
    assert parsed_nifty50["output"]["rows"][0]["indexMembership"] == "NIFTY50"
    assert direct_download_candidates("nse_nifty50_constituents") == [
        "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
    ]


def test_instrument_rows_persist_point_in_time_and_join_sector(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "instrument-universe.db")
    equity = (
        "SYMBOL,NAME OF COMPANY,SERIES,DATE OF LISTING,PAID UP VALUE,MARKET LOT,ISIN NUMBER,FACE VALUE\n"
        "INFY,Infosys Limited,EQ,08-Feb-1995,5,1,INE009A01021,5\n"
    ).encode()
    sector = (
        "Company Name,Industry,Symbol,Series,ISIN Code\n"
        "Infosys Limited,Information Technology,INFY,EQ,INE009A01021\n"
    ).encode()
    first = parse_source_content(
        "nse_equity_universe", equity, last_modified="2026-07-11"
    )
    second = parse_source_content(
        "nse_nifty500_constituents", sector, last_modified="2026-07-11"
    )
    storage.save_source_parse_result(first)
    storage.save_source_parse_result(second)
    instruments = storage.list_nse_instruments(symbol="INFY", as_of="2026-07-11")
    assert instruments[0]["company"] == "Infosys Limited"
    assert instruments[0]["industry"] == "Information Technology"
    assert instruments[0]["index_membership"] == "NIFTY500"
    status = storage.nse_instrument_universe_status()
    assert status["instrumentCount"] == 1
    assert status["nifty500MembershipCount"] == 1
    assert "0010_nse_instrument_universe" in {
        row["version"] for row in storage.list_schema_migrations()
    }


def test_market_regime_blocks_narrow_rally_vix_shock_and_future_data() -> None:
    bullish = evaluate_market_context(
        MarketContextInput(
            asOf=AS_OF,
            sourceDate=AS_OF - timedelta(hours=1),
            niftyCloses=rising_series(20_000, 220, 10),
            niftyReturnPercent=0.7,
            indiaVix=13,
            indiaVixChangePercent=-2,
            advances=1_200,
            declines=600,
            unchanged=100,
            trustLevel="OFFICIAL_FREE_EOD",
        )
    )
    assert bullish.state == "TRADEABLE_BULLISH"
    assert bullish.gate_outcome == "PASS"
    assert bullish.breadth_state == "HEALTHY"

    shocked = evaluate_market_context(
        MarketContextInput(
            asOf=AS_OF,
            sourceDate=AS_OF - timedelta(hours=1),
            niftyCloses=rising_series(20_000, 220, 10),
            niftyReturnPercent=0.8,
            indiaVix=24,
            indiaVixChangePercent=35,
            advances=300,
            declines=1_000,
            unchanged=50,
            trustLevel="OFFICIAL_FREE_EOD",
        )
    )
    assert shocked.state == "NO_TRADE"
    assert shocked.gate_outcome == "HARD_FAIL"
    assert shocked.narrow_index_divergence is True

    future = MarketContextInput(
        asOf=AS_OF,
        sourceDate=AS_OF + timedelta(minutes=1),
        niftyCloses=rising_series(20_000, 220, 10),
        niftyReturnPercent=0,
        indiaVix=13,
        indiaVixChangePercent=0,
        advances=1,
        declines=1,
        unchanged=0,
        trustLevel="OFFICIAL_FREE_EOD",
    )
    assert evaluate_market_context(future).gate_outcome == "HARD_FAIL"


def test_rrg_sector_direction_gate_is_point_in_time_and_catalyst_aware() -> None:
    benchmark = rising_series(100, 80, 0.2)
    leading_sector = rising_series(100, 80, 0.45)
    leading = evaluate_sector_context(
        SectorContextInput(
            sector="Information Technology",
            direction="LONG",
            asOf=AS_OF,
            sourceDate=AS_OF - timedelta(hours=1),
            sectorCloses=leading_sector,
            benchmarkCloses=benchmark,
            trustLevel="OFFICIAL_FREE_EOD",
        )
    )
    assert leading.rrg_state == "LEADING"
    assert leading.gate_outcome == "PASS"

    lagging = evaluate_sector_context(
        SectorContextInput(
            sector="Metals",
            direction="LONG",
            asOf=AS_OF,
            sourceDate=AS_OF - timedelta(hours=1),
            sectorCloses=list(reversed(leading_sector)),
            benchmarkCloses=benchmark,
            trustLevel="OFFICIAL_FREE_EOD",
        )
    )
    assert lagging.rrg_state == "LAGGING"
    assert lagging.gate_outcome == "HARD_FAIL"

    override = evaluate_sector_context(
        SectorContextInput(
            sector="Metals",
            direction="LONG",
            asOf=AS_OF,
            sourceDate=AS_OF - timedelta(hours=1),
            sectorCloses=list(reversed(leading_sector)),
            benchmarkCloses=benchmark,
            trustLevel="OFFICIAL_FREE_EOD",
            verifiedCatalystOverride=True,
        )
    )
    assert override.gate_outcome == "SOFT_FAIL"


def test_context_api_persists_read_only_snapshots(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "context-api.db")
    client = TestClient(app)
    response = client.post(
        "/api/context/market/evaluate",
        json={
            "asOf": AS_OF.isoformat(),
            "sourceDate": (AS_OF - timedelta(hours=1)).isoformat(),
            "niftyCloses": rising_series(20_000, 220, 10),
            "niftyReturnPercent": 0.7,
            "indiaVix": 13,
            "indiaVixChangePercent": -2,
            "advances": 1200,
            "declines": 600,
            "unchanged": 100,
            "trustLevel": "SYNTHETIC_TEST",
        },
    )
    assert response.status_code == 200
    assert response.json()["executable"] is False
    latest = client.get("/api/context/market/latest")
    assert latest.status_code == 200
    assert latest.json()["state"] == "TRADEABLE_BULLISH"
    assert "0011_market_sector_context" in {
        row["version"] for row in storage.list_schema_migrations()
    }


def test_scanner_waits_without_context_and_no_trade_overrides_on_market_shock(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "context-scanner.db")
    storage.save_ohlcv_candles(
        generate_demo_daily_candles(symbol="CTXSCAN", sessions=45)
    )
    missing = ScannerScheduler().run_once(
        universe="WATCHLIST_ONLY", fetch=False, trigger="missing-context"
    )
    candidate = storage.list_scanner_candidates(run_id=missing["runId"], limit=10)[0][
        "payload"
    ]
    assert candidate["state"] == "WAIT_DATA_WEAK"
    assert candidate["marketContext"]["gateOutcome"] == "WAIT"

    now = datetime.now(timezone.utc)
    shock = evaluate_market_context(
        MarketContextInput(
            asOf=now,
            sourceDate=now - timedelta(minutes=5),
            niftyCloses=rising_series(20_000, 220, 10),
            niftyReturnPercent=0.8,
            indiaVix=24,
            indiaVixChangePercent=35,
            advances=300,
            declines=1_000,
            unchanged=50,
            trustLevel="SYNTHETIC_TEST",
        )
    )
    storage.save_market_context_snapshot(shock.model_dump(mode="json", by_alias=True))
    blocked = ScannerScheduler().run_once(
        universe="WATCHLIST_ONLY", fetch=False, trigger="market-shock"
    )
    blocked_candidate = storage.list_scanner_candidates(
        run_id=blocked["runId"], limit=10
    )[0]["payload"]
    assert blocked_candidate["state"] == "NO_TRADE"
    assert blocked_candidate["marketContext"]["state"] == "NO_TRADE"
