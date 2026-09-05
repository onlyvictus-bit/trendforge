from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from trendforge_api import main
from trendforge_api.main import app
from trendforge_api.selection.attention_order import AttentionRowV1, InventoryDiscoveryV1
from trendforge_api.selection.cash_a3_discovery import (
    CashDiscoveryBatch,
    CashDiscoveryMetrics,
    CashDiscoveryRow,
    DiscoveryProfile,
)
from trendforge_api.selection.cash_a4_history import CashRawSessionBar
from trendforge_api.selection.contracts import EvidenceDirection, SelectionState
from trendforge_api.selection.s3_cheap_discovery import (
    ACCEPTANCE_CEILING,
    SCHEMA_VERSION,
    build_s3_cheap_discovery,
    build_s3_watch_queue,
)

NOW = datetime(2026, 8, 14, 3, 40, tzinfo=UTC)  # 09:10 IST
TRADING_DATE = "2026-08-14"


def _attention_row(symbol: str, state: SelectionState, batch_id: str, priority: float | None):
    return AttentionRowV1(
        candidate_id=f"cand-{symbol}",
        symbol=symbol,
        public_state=state,
        evidence_direction=EvidenceDirection.BULLISH,
        display_order=1,
        attention_rank=1 if state is SelectionState.WATCH else None,
        attention_priority=priority if state is SelectionState.WATCH else None,
        attention_band="HIGH" if priority is not None else "UNRANKED",
        supporting_families=("CASH_SESSION_ROOT",) if priority is not None else (),
        opposing_claims=(),
        missing_evidence=("SOURCE_ACTIVATION", "CLOSED_BAR_STRUCTURE"),
        conflicts=(),
        completeness=1.0,
        freshness="CURRENT",
        source_quality="OFFICIAL_STRUCTURED",
        restriction_state="REJECT" if state is SelectionState.REJECT else "ELIGIBLE_RESEARCH",
        why_visible="R2 research attention.",
        why_not_confirmed=("SOURCE_ACTIVATION", "CLOSED_BAR_STRUCTURE"),
        lineage={
            "cashPipelineRunId": "cash-1",
            "discoveryBatchId": batch_id,
            "tradingDate": TRADING_DATE,
        },
        dataset_root_ids=("root-cash",),
    )


def _attention(states: list[tuple[str, SelectionState]], batch_id: str = "a3-1"):
    rows = tuple(
        _attention_row(symbol, state, batch_id, round(0.9 - index * 0.001, 6))
        for index, (symbol, state) in enumerate(states)
    )
    return InventoryDiscoveryV1(
        run_id="r2-1",
        run_hash="2" * 64,
        r1_bundle_id="r1-1",
        r1_bundle_hash="1" * 64,
        collector_run_id="collector-1",
        cash_pipeline_run_id="cash-1",
        cash_pipeline_fingerprint="c" * 64,
        permission_fingerprint="p" * 64,
        snapshot_bundle_id="snapshot-1",
        trading_date=TRADING_DATE,
        built_at=NOW,
        universe_count=len(rows),
        watch_count=sum(row.public_state is SelectionState.WATCH for row in rows),
        wait_count=sum(row.public_state is SelectionState.WAIT for row in rows),
        reject_count=sum(row.public_state is SelectionState.REJECT for row in rows),
        rows=rows,
    )


def _discovery(states: list[tuple[str, SelectionState]], batch_id: str = "a3-1"):
    rows = tuple(
        CashDiscoveryRow(
            symbol=symbol,
            instrument_id=f"NSE:EQ:{symbol}",
            fact_id=f"fact-{symbol}",
            public_state=state,
            discovery_profiles=(DiscoveryProfile.MOMENTUM,) if state is SelectionState.WATCH else (),
            discovery_reason="A3 profile result.",
            metrics=CashDiscoveryMetrics(session_return=0.02),
            eligible=state is not SelectionState.REJECT,
            banned=state is SelectionState.REJECT,
        )
        for symbol, state in states
    )
    return CashDiscoveryBatch(
        batch_id=batch_id,
        identity_batch_id="a2-1",
        eligible_count=sum(row.eligible for row in rows),
        watch_count=sum(row.public_state is SelectionState.WATCH for row in rows),
        rows=rows,
    )


def _loader(payloads=None, calls=None):
    payloads = payloads or {}

    def load(key):
        if calls is not None:
            calls.append(key)
        rows = payloads.get(key)
        if rows is None:
            return None
        return {
            "parserState": "PARSED_STRUCTURED",
            "dataDate": TRADING_DATE,
            "output": {"records": rows},
        }

    return load


def _bar(symbol: str, day: date, close: float, volume: float, width: float = 2.0):
    return CashRawSessionBar(
        bar_id=f"bar-{symbol}-{day}",
        instrument_id=f"NSE:EQ:{symbol}",
        symbol=symbol,
        trade_date=day,
        artifact_hash="a" * 64,
        series_id=f"raw-{symbol}",
        open=close - 0.5,
        high=close + width / 2,
        low=close - width / 2,
        close=close,
        previous_close=close - 1,
        volume=volume,
        traded_value=volume * close,
    )


def _history(symbol: str, *, through: date):
    start = through - timedelta(days=20)
    if symbol in {"NIFTY 50", "NIFTY50"}:
        return [_bar("NIFTY 50", start + timedelta(days=i), 100 + i, 1000) for i in range(21)]
    return [
        _bar(symbol, start + timedelta(days=i), 200 + i * 2, 1000 if i < 20 else 2000, 1.0 if i == 20 else 2.0)
        for i in range(21)
    ]


def test_t1_scans_full_universe_not_top_40() -> None:
    states = [(f"STOCK{i:03d}", SelectionState.WATCH) for i in range(75)]
    batch = build_s3_cheap_discovery(
        discovery=_discovery(states),
        attention=_attention(states),
        loader=_loader(),
        history_loader=_history,
        built_at=NOW,
    )
    assert batch.schema_version == SCHEMA_VERSION
    assert batch.eligible_count == 75
    assert batch.scanned_count == 75
    assert len(batch.rows) == 75
    assert batch.completeness == 1.0


def test_t2_partial_scan_counts_unattempted_separately_from_excluded() -> None:
    states = [
        ("WATCHED", SelectionState.WATCH),
        ("MISSING", SelectionState.WATCH),
        ("BLOCKED", SelectionState.REJECT),
    ]
    batch = build_s3_cheap_discovery(
        discovery=_discovery([states[0], states[2]]),
        attention=_attention(states),
        loader=_loader(),
        history_loader=lambda *_args, **_kwargs: [],
        built_at=NOW,
    )
    assert batch.eligible_count == 2
    assert batch.scanned_count == 1
    assert batch.unattempted_count == 1
    assert batch.excluded_count == 1
    assert batch.wait_partial_scan is True
    watched = next(row for row in batch.rows if row.symbol == "WATCHED")
    assert watched.research_state is SelectionState.WAIT
    assert "WAIT_PARTIAL_SCAN" in watched.why_unknown


def test_t3_delivery_is_never_queried_or_exposed() -> None:
    calls: list[str] = []
    states = [("ALPHA", SelectionState.WATCH)]
    batch = build_s3_cheap_discovery(
        discovery=_discovery(states),
        attention=_attention(states),
        loader=_loader(calls=calls),
        history_loader=_history,
        built_at=NOW,
    )
    assert batch.delivery_queried is False
    assert "nse_mto_delivery" not in calls
    assert all("delivery" not in type(row).model_fields for row in batch.rows)


def test_t4_activity_tag_does_not_change_r2_attention_priority() -> None:
    states = [("ALPHA", SelectionState.WATCH)]
    r2 = _attention(states)
    before_hash = r2.run_hash
    before_priority = r2.rows[0].attention_priority
    batch = build_s3_cheap_discovery(
        discovery=_discovery(states),
        attention=r2,
        loader=_loader({"nse_most_active_volume": [{"symbol": "ALPHA"}]}),
        history_loader=_history,
        built_at=NOW,
    )
    assert "ACTIVITY_LIST" in batch.rows[0].tags
    assert batch.rows[0].attention_priority == before_priority
    assert r2.run_hash == before_hash


def test_t5_missing_preopen_is_unknown_not_drop() -> None:
    states = [("ALPHA", SelectionState.WATCH)]
    batch = build_s3_cheap_discovery(
        discovery=_discovery(states),
        attention=_attention(states),
        loader=_loader(),
        history_loader=_history,
        built_at=NOW,
    )
    assert len(batch.rows) == 1
    assert "UNKNOWN_PREOPEN_NO_SYMBOL_ROW" in batch.rows[0].why_unknown


def test_t6_cash_only_missing_oi_is_not_punished() -> None:
    states = [("CASHONLY", SelectionState.WATCH)]
    batch = build_s3_cheap_discovery(
        discovery=_discovery(states),
        attention=_attention(states),
        loader=_loader(),
        history_loader=_history,
        built_at=NOW,
    )
    row = batch.rows[0]
    assert row.research_state is SelectionState.WATCH
    assert "OI_SPURT" not in row.tags
    assert not any("OI" in reason for reason in row.why_unknown)


def test_t7_wait_and_reject_never_enter_watch_queue() -> None:
    states = [
        ("WATCHED", SelectionState.WATCH),
        ("WAITING", SelectionState.WAIT),
        ("REJECTED", SelectionState.REJECT),
    ]
    batch = build_s3_cheap_discovery(
        discovery=_discovery(states),
        attention=_attention(states),
        loader=_loader(),
        history_loader=_history,
        built_at=NOW,
    )
    queue = build_s3_watch_queue(batch, limit=50)
    assert [row.symbol for row in queue.rows] == ["WATCHED"]
    assert next(row for row in batch.rows if row.symbol == "WAITING").research_state is SelectionState.WAIT
    assert next(row for row in batch.rows if row.symbol == "REJECTED").research_state is SelectionState.REJECT


def test_t8_native_scanner_absence_is_information_only() -> None:
    states = [("ALPHA", SelectionState.WATCH)]
    row = build_s3_cheap_discovery(
        discovery=_discovery(states),
        attention=_attention(states),
        loader=_loader(),
        history_loader=_history,
        built_at=NOW,
    ).rows[0]
    assert "NATIVE_SCANNER_NOT_REGISTERED" in row.why_unknown
    assert row.research_state is SelectionState.WATCH


def test_t9_no_confirmation_and_rvol_nr7_rs_are_deterministic() -> None:
    states = [("ALPHA", SelectionState.WATCH)]
    r2 = _attention(states)
    batch = build_s3_cheap_discovery(
        discovery=_discovery(states),
        attention=r2,
        loader=_loader(),
        history_loader=_history,
        built_at=NOW,
    )
    row = batch.rows[0]
    assert batch.acceptance_ceiling == ACCEPTANCE_CEILING
    assert batch.source_activation_ready is False
    assert batch.can_unlock_confirmed is False
    assert batch.confirmed_count == 0
    assert row.rvol_eod == 2.0
    assert {"RVOL_EOD", "NR7", "RS_1D", "RS_5D"}.issubset(row.tags)
    assert row.can_unlock_confirmed is False
    assert r2.run_hash == "2" * 64


def test_t10_lineage_and_http_methods_fail_closed(monkeypatch) -> None:
    states = [("ALPHA", SelectionState.WATCH)]
    with pytest.raises(ValueError, match="WAIT_S3_LINEAGE_MISMATCH"):
        build_s3_cheap_discovery(
            discovery=_discovery(states, batch_id="a3-current"),
            attention=_attention(states, batch_id="a3-old"),
            loader=_loader(),
            history_loader=_history,
            built_at=NOW,
        )

    ready = build_s3_cheap_discovery(
        discovery=_discovery(states),
        attention=_attention(states),
        loader=_loader(),
        history_loader=_history,
        built_at=NOW,
    )
    monkeypatch.setattr(main, "build_s3_cheap_discovery", lambda **_kwargs: ready)
    client = TestClient(app)
    assert client.get("/api/v1/selection/cheap-discovery").status_code == 200
    watch = client.get("/api/v1/selection/cheap-discovery/watch?limit=1")
    assert watch.status_code == 200
    assert watch.json()["rows"][0]["symbol"] == "ALPHA"
    assert client.post("/api/v1/selection/cheap-discovery").status_code == 405
    assert client.post("/api/v1/selection/cheap-discovery/watch").status_code == 405

    def mismatch(**_kwargs):
        raise ValueError("WAIT_S3_LINEAGE_MISMATCH")

    monkeypatch.setattr(main, "build_s3_cheap_discovery", mismatch)
    response = client.get("/api/v1/selection/cheap-discovery")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "WAIT_S3_LINEAGE_MISMATCH"
