from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from trendforge_api import main, storage
from trendforge_api.main import app
from trendforge_api.selection.attention_order import (
    FORMULA_ID,
    SCHEMA_VERSION,
    build_attention_order,
    latest_attention_order,
    persist_attention_order,
)
from trendforge_api.selection.contracts import EvidenceDirection, SelectionState
from trendforge_api.selection.inventory_source_bundle import (
    InventorySourceBundleV1,
    SourceEvidenceRecordV1,
    SourceUsabilityState,
    StockEvidenceRecordV1,
)
from trendforge_api.selection.shadow_screener import run_shadow_screener

NOW = datetime(2026, 8, 14, 16, 5, tzinfo=UTC)


def _source() -> SourceEvidenceRecordV1:
    return SourceEvidenceRecordV1(
        source_key="nse_bhavcopy_eod",
        canonical_source_key="nse_bhavcopy_eod",
        canonical_url="https://example.test/cash",
        normalized_source_key="nse_bhavcopy_eod",
        acquisition_owner="ASYNC_ENDPOINT_CLIENT",
        parser_or_adapter_id="cash",
        validator_id="cash",
        cadence_class="DAILY_EOD",
        attempt_state="SUCCESS_NEW",
        parser_state="PARSED_STRUCTURED",
        usability_state=SourceUsabilityState.USABLE_CURRENT,
        reason="current",
        http_status=200,
        fetched_at=NOW,
        data_date=date(2026, 8, 14),
        row_count=4,
        normalized_content_hash="a" * 64,
        dataset_root_id="root-cash",
        correlation_group="ROOT:nse_bhavcopy_eod",
        evidence_eligible=True,
    )


def _stock(symbol: str, state: SelectionState, *, ret=0.8, volume=0.8, turnover=0.7) -> StockEvidenceRecordV1:
    return StockEvidenceRecordV1(
        candidate_id=f"cand-{symbol}",
        symbol=symbol,
        instrument_id=f"NSE:EQ:{symbol}",
        fact_id=f"fact-{symbol}",
        public_state=state,
        evidence_direction=EvidenceDirection.BULLISH,
        research_class="BULLISH",
        why_visible="Cash discovery attention.",
        why_not_confirmed=("SOURCE_ACTIVATION", "CLOSED_BAR_STRUCTURE"),
        attempted_sources=("nse_bhavcopy_eod",),
        completed_sources=("nse_bhavcopy_eod",),
        valid_empty_sources=(),
        failed_sources=(),
        not_attempted_sources=(),
        family_coverage={"CASH_SESSION_ROOT": "CURRENT", "STRUCTURE": "MISSING_UNTIL_R5"},
        dataset_root_ids=("root-cash",),
        supporting_claims=("PRICE", "ACTIVITY"),
        opposing_claims=(),
        cheap_features={
            "sessionDirection": "UP",
            "sessionReturn": 0.02,
            "returnPercentile": ret,
            "volumePercentile": volume,
            "turnoverPercentile": turnover,
        },
        source_clock={
            "nse_bhavcopy_eod": {
                "attemptState": "SUCCESS_NEW",
                "usabilityState": "USABLE_CURRENT",
                "dataDate": "2026-08-14",
                "fetchedAt": NOW.isoformat(),
            }
        },
        lineage={
            "collectorRunId": "collector-1",
            "cashPipelineRunId": "cash-collector-1",
            "tradingDate": "2026-08-14",
            "rankBatchId": "rank-1",
        },
        restriction_state="REJECT" if state is SelectionState.REJECT else "ELIGIBLE_RESEARCH",
        tradability="REJECTED" if state is SelectionState.REJECT else "RESEARCH_ONLY",
        completeness=1.0,
    )


def _bundle(stocks=None) -> InventorySourceBundleV1:
    rows = tuple(stocks or (
        _stock("BETA", SelectionState.WATCH),
        _stock("ALPHA", SelectionState.WATCH),
        _stock("WAITCO", SelectionState.WAIT),
        _stock("REJECTCO", SelectionState.REJECT),
    ))
    return InventorySourceBundleV1(
        bundle_id="r1-bundle-1",
        bundle_hash="b" * 64,
        collector_run_id="collector-1",
        cash_pipeline_run_id="cash-collector-1",
        cash_pipeline_fingerprint="f" * 64,
        permission_fingerprint="p" * 64,
        snapshot_bundle_id="snapshot-1",
        trading_date=date(2026, 8, 14),
        built_at=NOW,
        registry_sha256="r" * 64,
        source_contract_count=1,
        stock_record_count=len(rows),
        stage_states={"C0": "COMPLETED", "C1": "COMPLETED"},
        source_records=(_source(),),
        stock_records=rows,
    )


def test_r2_is_deterministic_ordinal_and_uses_symbol_tie_break() -> None:
    first = build_attention_order(_bundle(), expected_permission_fingerprint="p" * 64, built_at=NOW)
    second = build_attention_order(_bundle(), expected_permission_fingerprint="p" * 64, built_at=NOW)
    assert first.schema_version == SCHEMA_VERSION
    assert first.formula_id == FORMULA_ID
    assert first.run_hash == second.run_hash
    assert [row.symbol for row in first.rows] == ["ALPHA", "BETA", "WAITCO", "REJECTCO"]
    assert [row.attention_rank for row in first.rows] == [1, 2, None, None]
    assert all(row.entry is row.target is row.stop is row.risk_reward is None for row in first.rows)


def test_r2_caps_same_root_features_to_one_supporting_family() -> None:
    order = build_attention_order(_bundle(), built_at=NOW)
    alpha = order.rows[0]
    assert alpha.supporting_families == ("CASH_SESSION_ROOT",)
    assert alpha.attention_priority == 0.8
    assert "PRICE" not in alpha.supporting_families
    assert "ACTIVITY" not in alpha.supporting_families


def test_r2_missing_activity_does_not_hidden_renormalize() -> None:
    stock = _stock("MISSING", SelectionState.WATCH, volume=None, turnover=None)
    order = build_attention_order(_bundle((stock,)), built_at=NOW)
    row = order.rows[0]
    assert row.public_state is SelectionState.WAIT
    assert row.attention_priority is None
    assert row.attention_rank is None
    assert "CURRENT_COMPLETE_CASH_FEATURES" in row.missing_evidence


def test_r2_stale_source_data_cannot_keep_watch_rank() -> None:
    stock = _stock("STALE", SelectionState.WATCH)
    stale_clock = {
        "nse_bhavcopy_eod": {
            "attemptState": "SUCCESS_NEW",
            "usabilityState": "STALE_DATA",
            "freshnessState": "STALE",
            "dataDate": "2026-08-13",
            "fetchedAt": NOW.isoformat(),
        }
    }
    stock = stock.model_copy(update={"source_clock": stale_clock})
    row = build_attention_order(_bundle((stock,)), built_at=NOW).rows[0]
    assert row.public_state is SelectionState.WAIT
    assert row.attention_rank is None
    assert row.attention_priority is None
    assert row.freshness == "STALE"
    assert row.source_quality == "SOURCE_DATA_OLD"


def test_r2_rejects_permission_or_snapshot_mismatch() -> None:
    with pytest.raises(ValueError, match="WAIT_PERMISSION_MATRIX_MISMATCH"):
        build_attention_order(_bundle(), expected_permission_fingerprint="x" * 64)
    broken = _bundle().model_copy(update={"stage_states": {"C1": "SKIPPED"}})
    with pytest.raises(ValueError, match="WAIT_MIXED_SNAPSHOT_INPUTS"):
        build_attention_order(broken)


def test_r2_persists_without_changing_state_authority(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "selection.db")
    storage._INITIALIZED_DB_PATHS.clear()
    stored = persist_attention_order(build_attention_order(_bundle(), built_at=NOW))
    loaded = latest_attention_order()
    assert stored.persisted is True
    assert loaded is not None
    assert loaded.run_id == stored.run_id
    assert loaded.source_activation_ready is False
    assert loaded.watch_count == 2
    assert all(row.public_state is not SelectionState.CONFIRMED for row in loaded.rows)


def test_r2_shadow_is_hash_pinned_deterministic_and_non_authoritative() -> None:
    bundle = _bundle()
    results = [run_shadow_screener(bundle) for _ in range(3)]
    assert all(result.status == "COMPLETED" for result in results), (
        "shadow runs: "
        + str([(result.status, result.error) for result in results])
    )
    assert len({result.output_hash for result in results}) == 1
    assert all(not result.can_vote and not result.can_change_baseline for result in results)
    baseline = build_attention_order(bundle, built_at=NOW)
    with_shadow = build_attention_order(
        bundle,
        shadow_comparison=results[0].model_dump(mode="json", by_alias=True),
        built_at=NOW,
    )
    assert [(row.symbol, row.public_state, row.attention_priority) for row in baseline.rows] == [
        (row.symbol, row.public_state, row.attention_priority) for row in with_shadow.rows
    ]

def test_r2_attention_apis_return_persisted_collection_and_symbol(monkeypatch) -> None:
    order = build_attention_order(_bundle(), built_at=NOW)
    monkeypatch.setattr(main, "latest_attention_order", lambda: order)
    client = TestClient(app)
    collection = client.get("/api/v1/selection/attention")
    assert collection.status_code == 200
    assert collection.json()["schemaVersion"] == SCHEMA_VERSION
    assert collection.json()["acceptanceCeiling"] == "WATCH_WAIT_REJECT"
    symbol = client.get("/api/v1/selection/attention/alpha")
    assert symbol.status_code == 200
    assert symbol.json()["symbol"] == "ALPHA"
    assert symbol.json()["attentionRank"] == 1


def test_r2_attention_apis_fail_closed(monkeypatch) -> None:
    monkeypatch.setattr(main, "latest_attention_order", lambda: None)
    client = TestClient(app)
    assert client.get("/api/v1/selection/attention").status_code == 503
    assert client.get("/api/v1/selection/attention/ALPHA").status_code == 503