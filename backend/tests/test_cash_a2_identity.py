from __future__ import annotations

from datetime import UTC, datetime

from trendforge_api import storage
from trendforge_api.market_data_store import ManifestStatus, MarketDataStore
from trendforge_api.selection.cash_a1_staging import persist_cash_staging, stage_cash_bytes
from trendforge_api.selection.cash_a2_identity import (
    build_cash_identity_batch,
    persist_cash_identity,
)
from trendforge_api.selection.contracts import SelectionState
from trendforge_api.source_contracts import SourceResultState

CASH_CSV = b"""TradDt,TckrSymb,SctySrs,ISIN,OpnPric,HghPric,LwPric,ClsPric,PrvsClsgPric,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd
14-Aug-2026,RELIANCE,EQ,INE002A01018,100,110,99,105,100,1000,105000,10
14-Aug-2026,TCS,EQ,INE467B01029,200,210,198,201,200,500,100500,8
"""
BAN_READY = b"Securities in Ban For Trade Date 14-AUG-2026:\n1,RELIANCE\n"
BAN_EMPTY = b"Securities in Ban For Trade Date 14-AUG-2026:\n"
FETCHED = datetime(2026, 8, 14, 16, 0, tzinfo=UTC)


def _stage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "cash-a2.db")
    return persist_cash_staging(stage_cash_bytes(CASH_CSV, fetched_at=FETCHED))


def test_a2_creates_normalized_facts_without_rank(tmp_path, monkeypatch) -> None:
    staging = _stage(tmp_path, monkeypatch)
    batch = persist_cash_identity(
        build_cash_identity_batch(
            staging,
            ban_content=BAN_EMPTY,
            ban_status=ManifestStatus.SUCCESS_NEW.value,
            ban_fetched_at=FETCHED,
        )
    )
    assert batch.milestone == "A2"
    assert batch.can_rank is False
    assert batch.can_unlock_confirmed is False
    assert batch.fact_count == 2
    assert {row.instrument.symbol for row in batch.rows} == {"RELIANCE", "TCS"}
    assert all(row.instrument.instrument_id.startswith("ins_") for row in batch.rows)
    assert all(row.fact.instrument_id == row.instrument.instrument_id for row in batch.rows)
    assert all(row.public_state is SelectionState.WAIT for row in batch.rows)
    assert all("evidenceDirection" not in row.fact.payload for row in batch.rows)
    assert batch.restriction.state == "READY"
    assert batch.restriction.can_veto is True


def test_a2_missing_ban_is_wait_not_reject(tmp_path, monkeypatch) -> None:
    staging = _stage(tmp_path, monkeypatch)
    store = MarketDataStore(root=tmp_path / "objects", db_path=tmp_path / "market.db")
    store.initialize_schema()
    batch = build_cash_identity_batch(staging, store=store)
    assert batch.restriction.state == "WAIT_RESTRICTION"
    assert batch.restriction.can_veto is False
    assert all(row.public_state is SelectionState.WAIT for row in batch.rows)
    assert all(
        any(gate.code == "S1_BAN" and gate.outcome.value == "WAIT" for gate in row.gates)
        for row in batch.rows
    )


def test_a2_proven_ban_rejects_only_listed_symbol(tmp_path, monkeypatch) -> None:
    staging = _stage(tmp_path, monkeypatch)
    batch = build_cash_identity_batch(
        staging,
        ban_content=BAN_READY,
        ban_status=ManifestStatus.SUCCESS_NEW.value,
        ban_fetched_at=FETCHED,
    )
    by_symbol = {row.instrument.symbol: row for row in batch.rows}
    assert by_symbol["RELIANCE"].public_state is SelectionState.REJECT
    assert by_symbol["RELIANCE"].banned is True
    assert by_symbol["TCS"].public_state is SelectionState.WAIT
    assert by_symbol["TCS"].banned is False


def test_a2_stale_ban_cannot_reject(tmp_path, monkeypatch) -> None:
    staging = _stage(tmp_path, monkeypatch)
    batch = build_cash_identity_batch(
        staging,
        ban_content=BAN_READY,
        ban_status=ManifestStatus.STALE_LAST_GOOD.value,
        ban_fetched_at=FETCHED,
    )
    assert batch.restriction.proven is False
    assert batch.restriction.can_veto is False
    assert all(row.public_state is SelectionState.WAIT for row in batch.rows)


def test_a2_stale_cash_facts_are_not_ranked(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "cash-a2-stale.db")
    staging = persist_cash_staging(
        stage_cash_bytes(
            CASH_CSV,
            fetched_at=FETCHED,
            last_good_status=ManifestStatus.STALE_LAST_GOOD.value,
        )
    )
    assert staging.source_result.state is SourceResultState.STALE
    batch = build_cash_identity_batch(
        staging,
        ban_content=BAN_EMPTY,
        ban_status=ManifestStatus.SUCCESS_NEW.value,
        ban_fetched_at=FETCHED,
    )
    assert batch.can_rank is False
    assert all(row.fact.quality_state == "STALE" for row in batch.rows)
    assert all(
        any(gate.code == "S0_SOURCE_HEALTH" and gate.outcome.value == "WAIT" for gate in row.gates)
        for row in batch.rows
    )
