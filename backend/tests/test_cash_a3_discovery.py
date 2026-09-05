from __future__ import annotations

from datetime import UTC, datetime

from trendforge_api import storage
from trendforge_api.market_data_store import ManifestStatus
from trendforge_api.selection.cash_a1_staging import persist_cash_staging, stage_cash_bytes
from trendforge_api.selection.cash_a2_identity import (
    build_cash_identity_batch,
    persist_cash_identity,
)
from trendforge_api.selection.cash_a3_discovery import (
    DiscoveryProfile,
    build_cash_discovery_batch,
    persist_cash_discovery,
)
from trendforge_api.selection.contracts import SelectionState

# Five EQ names so cross-section percentiles can separate profiles.
CASH_CSV = b"""TradDt,TckrSymb,SctySrs,ISIN,OpnPric,HghPric,LwPric,ClsPric,PrvsClsgPric,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd
14-Aug-2026,MOMENTUM,EQ,INE000A01001,100,120,100,120,100,5000,600000,50
14-Aug-2026,RECOVERY,EQ,INE000A01002,100,101,80,101,105,800,80800,20
14-Aug-2026,WIDE,EQ,INE000A01003,100,160,40,90,100,900,81000,15
14-Aug-2026,TIGHT,EQ,INE000A01004,100,100.4,99.8,100.1,100,1200,120000,12
14-Aug-2026,LIQUID,EQ,INE000A01005,100,102,99,101,100,20000,2020000,200
"""
BAN_MOMENTUM = b"Securities in Ban For Trade Date 14-AUG-2026:\n1,MOMENTUM\n"
BAN_EMPTY = b"Securities in Ban For Trade Date 14-AUG-2026:\n"
FETCHED = datetime(2026, 8, 14, 16, 0, tzinfo=UTC)


def _discover(tmp_path, monkeypatch, csv=CASH_CSV, ban=BAN_EMPTY, stale=False):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "cash-a3.db")
    staging = persist_cash_staging(
        stage_cash_bytes(
            csv,
            fetched_at=FETCHED,
            last_good_status=(
                ManifestStatus.STALE_LAST_GOOD.value
                if stale
                else ManifestStatus.SUCCESS_NEW.value
            ),
        )
    )
    identity = persist_cash_identity(
        build_cash_identity_batch(
            staging,
            ban_content=ban,
            ban_status=ManifestStatus.SUCCESS_NEW.value,
            ban_fetched_at=FETCHED,
        )
    )
    return persist_cash_discovery(build_cash_discovery_batch(identity))


def test_a3_assigns_watch_reasons_without_rank(tmp_path, monkeypatch) -> None:
    batch = _discover(tmp_path, monkeypatch)
    assert batch.milestone == "A3"
    assert batch.profile_id == "DISC_EOD_V1"
    assert batch.can_rank is False
    assert batch.can_unlock_confirmed is False
    by_symbol = {row.symbol: row for row in batch.rows}
    assert DiscoveryProfile.MOMENTUM in by_symbol["MOMENTUM"].discovery_profiles
    assert by_symbol["MOMENTUM"].public_state is SelectionState.WATCH
    assert DiscoveryProfile.RECOVERY in by_symbol["RECOVERY"].discovery_profiles
    assert DiscoveryProfile.RANGE in by_symbol["WIDE"].discovery_profiles
    assert DiscoveryProfile.NARROW_SESSION in by_symbol["TIGHT"].discovery_profiles
    assert DiscoveryProfile.LIQUIDITY in by_symbol["LIQUID"].discovery_profiles
    assert all("FTR-018" not in row.discovery_reason for row in batch.rows)
    assert batch.watch_count >= 4


def test_a3_banned_symbol_cannot_watch(tmp_path, monkeypatch) -> None:
    batch = _discover(tmp_path, monkeypatch, ban=BAN_MOMENTUM)
    row = next(item for item in batch.rows if item.symbol == "MOMENTUM")
    assert row.banned is True
    assert row.public_state is SelectionState.REJECT
    assert row.discovery_profiles == ()


def test_a3_stale_cash_cannot_watch(tmp_path, monkeypatch) -> None:
    batch = _discover(tmp_path, monkeypatch, stale=True)
    assert batch.can_rank is False
    assert all(row.public_state is not SelectionState.WATCH for row in batch.rows)
    assert batch.watch_count == 0
    assert batch.eligible_count == 0
