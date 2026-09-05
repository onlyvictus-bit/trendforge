from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from trendforge_api.market_data_parameters import SavedMarketParameterProvider
from trendforge_api.market_data_store import MarketDataStore


NOW = datetime(2026, 8, 6, 6, 30, tzinfo=UTC)
DAY = date(2026, 8, 6)


def _store(tmp_path: Path) -> MarketDataStore:
    store = MarketDataStore(
        root=tmp_path / "market_data",
        db_path=tmp_path / "research.db",
    )
    store.initialize_schema()
    return store


def _save(store: MarketDataStore, source_key: str, records: list[dict]) -> None:
    payload = json.dumps({"records": records}, sort_keys=True).encode("utf-8")
    store.commit_success(
        run_id=f"run-{source_key}",
        source_key=source_key,
        trading_date=DAY,
        slot="manual",
        attempted_at=NOW,
        fetched_at=NOW,
        data_date=DAY,
        source_url="https://example.test/source",
        http_status=200,
        media_type="application/vnd.trendforge.normalized+json",
        content=payload,
        extension="json",
        normalized_row_count=len(records),
        retry_count=0,
    )


def test_saved_provider_builds_current_sectors_and_bounded_option_contracts(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    _save(
        store,
        "nse_all_indices",
        [
            {"index": "NIFTY IT", "key": "SECTORAL INDICES"},
            {"index": "NIFTY AUTO", "key": "SECTORAL INDICES"},
            {"index": "NIFTY 50", "key": "BROAD MARKET INDICES"},
        ],
    )
    _save(
        store,
        "nse_fo_bhavcopy",
        [
            {"symbol": "RELIANCE", "optionType": "CE", "expiry": "2026-08-25"},
            {"symbol": "RELIANCE", "optionType": "PE", "expiry": "2026-09-29"},
            {"symbol": "TCS", "optionType": "PE", "expiry": "2026-08-25"},
            {"symbol": "OLD", "optionType": "CE", "expiry": "2026-07-28"},
            {"symbol": "NIFTY", "optionType": "CE", "expiry": "2026-08-25"},
        ],
    )
    _save(
        store,
        "nse_most_active_underlying",
        [
            {"symbol": "TCS", "optVolume": 100},
            {"symbol": "RELIANCE", "optVolume": 200},
            {"symbol": "NOT_FO", "optVolume": 1000},
        ],
    )

    context = SavedMarketParameterProvider(store, option_symbol_limit=1)(
        DAY, "OPEN", NOW
    )

    assert context.sector_indices == ("NIFTY AUTO", "NIFTY IT")
    assert context.symbols == ("RELIANCE",)
    assert context.option_expiries == {"RELIANCE": "25-Aug-2026"}


def test_saved_provider_fails_closed_when_inputs_are_missing(tmp_path: Path) -> None:
    context = SavedMarketParameterProvider(_store(tmp_path))(DAY, "OPEN", NOW)

    assert context.symbols == ()
    assert context.sector_indices == ()
    assert context.option_expiries == {}
