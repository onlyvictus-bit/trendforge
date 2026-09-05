from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trendforge_api import storage
from trendforge_api.selection.cash_a1_staging import (
    persist_cash_staging,
    stage_cash_bytes,
    stage_cash_last_good,
)
from trendforge_api.selection.contracts import NormalizedFact
from trendforge_api.source_contracts import SourceResultState

CASH_CSV = b"""TradDt,TckrSymb,SctySrs,ISIN,OpnPric,HghPric,LwPric,ClsPric,PrvsClsgPric,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd
14-Aug-2026,RELIANCE,EQ,INE002A01018,100,110,99,105,100,1000,105000,10
14-Aug-2026,TCS,EQ,INE467B01029,200,210,198,201,200,500,100500,8
"""


def test_a1_stages_cash_bytes_without_normalized_fact(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "cash-a1.db")
    batch = persist_cash_staging(
        stage_cash_bytes(
            CASH_CSV,
            fetched_at=datetime(2026, 8, 14, 16, 0, tzinfo=UTC),
        )
    )
    assert batch.persisted is True
    assert batch.milestone == "A1"
    assert batch.acceptance_ceiling == "STAGING_ONLY"
    assert batch.source_result.state is SourceResultState.STRUCTURED_OK
    assert batch.source_result.can_support_confirmed is False
    assert batch.source_result.state_ceiling == "WAIT"
    assert batch.source_result.artifact_hash
    assert batch.source_result.data_date.isoformat() == "2026-08-14"
    assert batch.row_count == 2
    assert {row["symbol"] for row in batch.rows} == {"RELIANCE", "TCS"}
    dumped = batch.model_dump(by_alias=True)
    assert "instrumentId" not in dumped
    assert "normalizedFact" not in dumped
    with pytest.raises(Exception):
        NormalizedFact.model_validate(dumped)


def test_a1_empty_content_stays_parse_failed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "cash-a1-empty.db")
    batch = persist_cash_staging(
        stage_cash_bytes(
            b"TradDt,TckrSymb,SctySrs\n",
            fetched_at=datetime(2026, 8, 14, 16, 0, tzinfo=UTC),
        )
    )
    assert batch.source_result.state is SourceResultState.PARSE_FAILED
    assert batch.row_count == 0
    assert batch.source_result.can_support_confirmed is False


def test_a1_missing_last_good_is_not_attempted(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "cash-a1-missing.db")
    from trendforge_api.market_data_store import MarketDataStore

    store = MarketDataStore(root=tmp_path / "objects", db_path=tmp_path / "market.db")
    store.initialize_schema()
    batch = persist_cash_staging(stage_cash_last_good(store))
    assert batch.source_result.state is SourceResultState.NOT_ATTEMPTED
    assert batch.source_result.error_type == "MISSING_LAST_GOOD"
    assert batch.row_count == 0
