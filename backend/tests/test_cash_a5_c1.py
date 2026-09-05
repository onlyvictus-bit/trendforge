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
    build_cash_discovery_batch,
    persist_cash_discovery,
)
from trendforge_api.selection.cash_a4_history import (
    CorporateActionVintage,
    build_cash_history_batch,
    persist_cash_history,
)
from trendforge_api.selection.cash_c1_rank import build_cash_rank_batch, persist_cash_rank
from trendforge_api.selection.contracts import SelectionState
from trendforge_api.selection.fo_a6_enrichment import (
    build_fo_enrichment_batch,
    persist_fo_enrichment,
)
from trendforge_api.selection.index_a5_context import build_cash_context_batch
from trendforge_api.selection.mwpl_b import assess_mwpl
from trendforge_api.selection.use_matrix_c0 import (
    build_source_use_matrix,
    persist_source_use_matrix,
)

CASH_CSV = b"""TradDt,TckrSymb,SctySrs,ISIN,OpnPric,HghPric,LwPric,ClsPric,PrvsClsgPric,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd
14-Aug-2026,MOMENTUM,EQ,INE000A01001,100,120,100,120,100,5000,600000,50
14-Aug-2026,RECOVERY,EQ,INE000A01002,100,101,80,101,105,800,80800,20
14-Aug-2026,WIDE,EQ,INE000A01003,100,160,40,90,100,900,81000,15
14-Aug-2026,TIGHT,EQ,INE000A01004,100,100.4,99.8,100.1,100,1200,120000,12
14-Aug-2026,LIQUID,EQ,INE000A01005,100,102,99,101,100,20000,2020000,200
"""
INDEX_CSV = b"""Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change,Volume
NIFTY 50,14-Aug-2026,24000,24100,23900,24050,50,0.21,1000
INDIA VIX,14-Aug-2026,12,13,11,12.5,0.5,4.1,0
NIFTY BANK,14-Aug-2026,50000,50100,49900,50050,50,0.1,100
"""
FO_CSV = b"""TckrSymb,FinInstrmTp,XpryDt,ClsPric,PrvsClsgPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,StrkPric,OptnTp
MOMENTUM,FUTSTK,28-Aug-2026,120,110,10000,500,80,0,
MOMENTUM,FUTSTK,25-Sep-2026,121,111,4000,100,20,0,
MOMENTUM,OPTSTK,28-Aug-2026,5,4,99999,8000,40,100,CE
"""
BAN_EMPTY = b"Securities in Ban For Trade Date 14-AUG-2026:\n"
FETCHED = datetime(2026, 8, 14, 16, 0, tzinfo=UTC)


def _pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "cash-rest.db")
    staging = persist_cash_staging(stage_cash_bytes(CASH_CSV, fetched_at=FETCHED))
    identity = persist_cash_identity(
        build_cash_identity_batch(
            staging,
            ban_content=BAN_EMPTY,
            ban_status=ManifestStatus.SUCCESS_NEW.value,
            ban_fetched_at=FETCHED,
        )
    )
    discovery = persist_cash_discovery(build_cash_discovery_batch(identity))
    history = persist_cash_history(build_cash_history_batch(identity, decision_at=FETCHED))
    return identity, discovery, history


def test_a5_index_is_context_and_ca_wait_demotes_watch(tmp_path, monkeypatch) -> None:
    identity, discovery, _history = _pipeline(tmp_path, monkeypatch)
    history = persist_cash_history(
        build_cash_history_batch(
            identity,
            decision_at=FETCHED,
            vintages=[
                CorporateActionVintage(
                    event_id="CA-WAIT",
                    symbol="MOMENTUM",
                    action_class="SPLIT",
                    effective_date=datetime(2026, 8, 14).date(),
                    available_at=datetime(2026, 8, 14, 6, 0, tzinfo=UTC),
                    revision_id="r1",
                    adjustment_factor=None,
                )
            ],
        )
    )
    batch = build_cash_context_batch(
        index_content=INDEX_CSV,
        discovery=discovery,
        history=history,
    )
    assert batch.milestone == "A5"
    assert batch.index.can_rank is False
    assert batch.index.nifty50_close == 24050
    assert batch.index.india_vix == 12.5
    assert batch.index.role == "CONTEXT"
    mom = next(row for row in batch.rows if row.symbol == "MOMENTUM")
    assert mom.ca_integrity == "WAIT_CA"
    assert mom.public_state is SelectionState.WAIT


def test_a5_accepts_normalized_json_index_payload(tmp_path, monkeypatch) -> None:
    _identity, discovery, history = _pipeline(tmp_path, monkeypatch)
    payload = (
        b'{"parserState":"PARSED_STRUCTURED","dataDate":"2026-08-14","records":['
        b'{"indexName":"NIFTY 50","close":24050,"changePercent":0.21},'
        b'{"indexName":"INDIA VIX","close":12.5}'
        b"]}"
    )
    batch = build_cash_context_batch(
        index_content=payload, discovery=discovery, history=history
    )
    assert batch.index.parser_state == "PARSED_STRUCTURED"
    assert batch.index.nifty50_close == 24050
    assert batch.index.india_vix == 12.5
    assert batch.index.can_unlock_confirmed is False


def test_a6_uses_futures_only_and_does_not_penalize_cash(tmp_path, monkeypatch) -> None:
    _identity, discovery, _history = _pipeline(tmp_path, monkeypatch)
    batch = build_fo_enrichment_batch(fo_content=FO_CSV, discovery=discovery)
    by_symbol = {row.symbol: row for row in batch.rows}
    assert batch.can_rank is False
    assert by_symbol["MOMENTUM"].fo_state == "FUTURES_OK"
    assert by_symbol["MOMENTUM"].option_oi_used is False
    assert by_symbol["MOMENTUM"].near_future is not None
    assert by_symbol["MOMENTUM"].near_future.open_interest == 10000
    assert by_symbol["LIQUID"].option_oi_used is False
    assert by_symbol["TIGHT"].option_oi_used is False


def test_c0_matrix_keeps_can_vote_false(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "c0.db")
    matrix = persist_source_use_matrix(build_source_use_matrix())
    cash = next(row for row in matrix.rows if row.source_key == "nse_bhavcopy_eod")
    ban = next(row for row in matrix.rows if row.source_key == "nse_fno_ban")
    mwpl = next(row for row in matrix.rows if row.source_key == "nse_mwpl_percentages")
    assert cash.can_rank is True
    assert cash.can_vote is False
    assert cash.can_unlock_confirmed is False
    assert cash.ceiling == "WATCH"
    assert ban.can_veto is True
    assert ban.can_rank is False
    assert mwpl.can_veto is False
    assert matrix.source_activation_ready is False


def test_b_mwpl_missing_does_not_block(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "mwpl.db")
    missing = assess_mwpl(None)
    junk = assess_mwpl(b"not-a-percentage-file")
    assert missing.state == "MWPL_MISSING"
    assert junk.state == "MWPL_MISSING"
    assert missing.can_veto is False
    assert junk.can_rank is False


def test_c1_ranks_watch_only_when_can_rank(tmp_path, monkeypatch) -> None:
    _identity, discovery, _history = _pipeline(tmp_path, monkeypatch)
    persist_source_use_matrix(build_source_use_matrix())
    persist_fo_enrichment(build_fo_enrichment_batch(fo_content=FO_CSV, discovery=discovery))
    ranked = persist_cash_rank(build_cash_rank_batch(discovery=discovery))
    assert ranked.can_unlock_confirmed is False
    assert ranked.mwpl_state == "MWPL_MISSING"
    watched = [row for row in ranked.rows if row.rank is not None]
    assert watched
    assert all(row.public_state is SelectionState.WATCH for row in watched)
    assert watched == sorted(watched, key=lambda row: row.rank or 0)
    assert all(row.attention_score is not None for row in watched)
