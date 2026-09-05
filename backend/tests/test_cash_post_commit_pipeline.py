from __future__ import annotations

import json

import pytest
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from trendforge_api import main as main_module, storage
from trendforge_api.main import app
from trendforge_api.source_inventory_compiler import compile_default_inventory
from trendforge_api.selection.attention_order import latest_attention_order
from trendforge_api.selection.cash_a1_staging import latest_cash_staging
from trendforge_api.selection.cash_a2_identity import latest_cash_identity
from trendforge_api.selection.contracts import EvidenceDirection, SelectionState
from trendforge_api.selection.inventory_source_bundle import latest_inventory_source_bundle
from trendforge_api.selection.r3_live import build_r3_resolution, latest_r3_resolution
from trendforge_api.selection import cash_post_commit
from trendforge_api.market_data_service import NormalizedSourceResult
from trendforge_api.market_data_store import ManifestStatus, MarketDataStore
from trendforge_api.selection.cash_post_commit import (
    CashPipelineExecution,
    CashPipelineStage,
    CashPostCommitOrchestrator,
    CashPipelineRunContext,
    run_existing_cash_pipeline,
)


from trendforge_api.selection.use_matrix_c0 import (
    SourceUseMatrix,
    SourceUseRow,
    persist_source_use_matrix,
)

TRADE_DATE = date(2026, 8, 14)
NOW = datetime(2026, 8, 14, 16, 5, tzinfo=UTC)


def _result(
    source_key: str,
    status: ManifestStatus,
    *,
    rows: int = 1,
    digest: str = "a" * 64,
) -> NormalizedSourceResult:
    return NormalizedSourceResult(
        source_key=source_key,
        normalized_source_key=source_key,
        status=status,
        parser_state="PARSED_STRUCTURED",
        http_status=200,
        fetched_at=NOW,
        data_date=TRADE_DATE,
        normalized_row_count=rows,
        normalized_content_hash=digest,
        stored_attempt_id=1,
    )


def _commit_cash(store: MarketDataStore, *, digest_seed: str = "cash") -> None:
    payload = {
        "sourceKey": "nse_bhavcopy_eod",
        "parserState": "PARSED_STRUCTURED",
        "dataDate": TRADE_DATE.isoformat(),
        "records": [
            {
                "tradeDate": TRADE_DATE.isoformat(),
                "symbol": "RELIANCE",
                "series": "EQ",
                "isin": "INE002A01018",
                "open": 1400,
                "high": 1440,
                "low": 1390,
                "close": 1430,
                "previousClose": 1400,
                "volume": 1000000,
                "tradedValue": 1430000000,
            }
        ],
    }
    store.commit_success(
        run_id=f"collector-{digest_seed}",
        source_key="nse_bhavcopy_eod",
        trading_date=TRADE_DATE,
        slot="eod",
        attempted_at=NOW,
        fetched_at=NOW,
        data_date=TRADE_DATE,
        source_url="https://example.test/cash.csv",
        http_status=200,
        media_type="application/vnd.trendforge.normalized+json",
        content=json.dumps(payload, sort_keys=True).encode(),
        extension="json",
        normalized_row_count=1,
        retry_count=0,
    )


class RecordingRunner:
    def __init__(self, *, fail: bool = False, legacy_first: bool = False) -> None:
        self.fail = fail
        self.legacy_first = legacy_first
        self.calls = []

    def __call__(self, context):
        self.calls.append(context)
        if self.fail:
            raise RuntimeError("fixture A3 failure")
        legacy_output = self.legacy_first and len(self.calls) == 1
        return CashPipelineExecution(
            stages=(
                CashPipelineStage(stage_id="A1", state="COMPLETED", detail="fixture"),
                CashPipelineStage(stage_id="C1", state="COMPLETED", detail="fixture"),
                *(
                    ()
                    if legacy_output
                    else (
                        CashPipelineStage(
                            stage_id="R16",
                            state="BLOCKED",
                            detail="WAIT_R16_SCHEMA_NOT_APPLIED",
                        ),
                    )
                ),
            ),
            rank_batch_id="rank-fixture",
            r1_bundle_id=None if legacy_output else "r1-fixture",
            r2_order_id=None if legacy_output else "r2-fixture",
            r3_resolution_id=None if legacy_output else "r3-fixture",
            r4_pin_id=None if legacy_output else "r4-fixture",
            r14_join_id=None if legacy_output else "r14-fixture",
            r5_structure_id=None if legacy_output else "r5-fixture",
            s8_run_id=None if legacy_output else "s8-fixture",
            permission_fingerprint="permission-fixture",
        )


def _orchestrator(tmp_path: Path, runner: RecordingRunner):
    store = MarketDataStore(root=tmp_path / "market-data", db_path=tmp_path / "market.db")
    return (
        CashPostCommitOrchestrator(
            store=store,
            state_path=tmp_path / "cash-pipeline-state.json",
            runner=runner,
        ),
        store,
    )


def test_unrelated_source_refresh_does_not_run_cash_pipeline(tmp_path: Path) -> None:
    runner = RecordingRunner()
    orchestrator, _store = _orchestrator(tmp_path, runner)

    snapshot = orchestrator.process(
        collector_run_id="run-unrelated",
        trading_date=TRADE_DATE,
        results={"cftc_cot": _result("cftc_cot", ManifestStatus.SUCCESS_NEW)},
    )

    assert runner.calls == []
    assert snapshot.latest_dispatch.decision == "SKIPPED_UNRELATED"
    assert snapshot.latest_run is None


def test_http_200_without_current_saved_cash_blocks_pipeline(tmp_path: Path) -> None:
    runner = RecordingRunner()
    orchestrator, _store = _orchestrator(tmp_path, runner)

    snapshot = orchestrator.process(
        collector_run_id="run-http-only",
        trading_date=TRADE_DATE,
        results={
            "nse_bhavcopy_eod": _result(
                "nse_bhavcopy_eod", ManifestStatus.FAILED, rows=0
            )
        },
    )

    assert runner.calls == []
    assert snapshot.latest_run is not None
    assert snapshot.latest_run.state == "BLOCKED_INPUT"
    assert "saved current cash" in snapshot.latest_run.error.lower()


def test_same_relevant_artifact_fingerprint_runs_once(tmp_path: Path) -> None:
    runner = RecordingRunner()
    orchestrator, store = _orchestrator(tmp_path, runner)
    _commit_cash(store)
    results = {
        "nse_bhavcopy_eod": _result(
            "nse_bhavcopy_eod", ManifestStatus.SUCCESS_NEW
        )
    }

    first = orchestrator.process(
        collector_run_id="run-first", trading_date=TRADE_DATE, results=results
    )
    second = orchestrator.process(
        collector_run_id="run-second", trading_date=TRADE_DATE, results=results
    )

    assert len(runner.calls) == 1
    assert first.latest_run is not None
    assert first.latest_run.state == "COMPLETED"
    assert second.latest_dispatch.decision == "SKIPPED_DUPLICATE"
    assert second.latest_run.fingerprint == first.latest_run.fingerprint


def test_pipeline_version_change_rebuilds_complete_r1_r2_once(tmp_path: Path, monkeypatch) -> None:
    runner = RecordingRunner()
    orchestrator, store = _orchestrator(tmp_path, runner)
    _commit_cash(store)
    results = {"nse_bhavcopy_eod": _result("nse_bhavcopy_eod", ManifestStatus.SUCCESS_NEW)}

    first = orchestrator.process(
        collector_run_id="run-before-version", trading_date=TRADE_DATE, results=results
    )
    monkeypatch.setattr(cash_post_commit, "PIPELINE_VERSION", "fixture-upgraded-version")
    upgraded = orchestrator.process(
        collector_run_id="run-after-version", trading_date=TRADE_DATE, results=results
    )

    assert first.latest_run is not None
    assert upgraded.latest_dispatch.decision == "DISPATCHED"
    assert upgraded.latest_run is not None
    assert upgraded.latest_run.fingerprint != first.latest_run.fingerprint
    assert len(runner.calls) == 2


def test_identical_fingerprint_upgrades_legacy_run_missing_r1_r2_once(
    tmp_path: Path,
) -> None:
    runner = RecordingRunner(legacy_first=True)
    orchestrator, store = _orchestrator(tmp_path, runner)
    _commit_cash(store)
    results = {
        "nse_bhavcopy_eod": _result(
            "nse_bhavcopy_eod", ManifestStatus.SUCCESS_NEW
        )
    }

    legacy = orchestrator.process(
        collector_run_id="run-legacy", trading_date=TRADE_DATE, results=results
    )
    upgraded = orchestrator.process(
        collector_run_id="run-upgrade", trading_date=TRADE_DATE, results=results
    )
    duplicate = orchestrator.process(
        collector_run_id="run-after-upgrade", trading_date=TRADE_DATE, results=results
    )

    assert legacy.latest_run.r1_bundle_id is None
    assert legacy.latest_run.r2_order_id is None
    assert upgraded.latest_dispatch.decision == "DISPATCHED"
    assert upgraded.latest_run.r1_bundle_id == "r1-fixture"
    assert upgraded.latest_run.r2_order_id == "r2-fixture"
    assert duplicate.latest_dispatch.decision == "SKIPPED_DUPLICATE"
    assert len(runner.calls) == 2


def test_downstream_failure_is_recorded_without_raising_or_erasing_last_good(
    tmp_path: Path,
) -> None:
    runner = RecordingRunner(fail=True)
    orchestrator, store = _orchestrator(tmp_path, runner)
    _commit_cash(store)

    snapshot = orchestrator.process(
        collector_run_id="run-failed-stage",
        trading_date=TRADE_DATE,
        results={
            "nse_bhavcopy_eod": _result(
                "nse_bhavcopy_eod", ManifestStatus.SUCCESS_NEW
            )
        },
    )

    assert snapshot.latest_run is not None
    assert snapshot.latest_run.state == "FAILED_STAGE"
    assert "fixture A3 failure" in snapshot.latest_run.error
    assert store.latest_for("nse_bhavcopy_eod") is not None


def test_valid_empty_ban_is_a_gate_observation_not_a_positive_family(
    tmp_path: Path,
) -> None:
    runner = RecordingRunner()
    orchestrator, store = _orchestrator(tmp_path, runner)
    _commit_cash(store)

    snapshot = orchestrator.process(
        collector_run_id="run-empty-ban",
        trading_date=TRADE_DATE,
        results={
            "nse_fno_ban": _result(
                "nse_fno_ban", ManifestStatus.VALID_EMPTY, rows=0, digest="b" * 64
            )
        },
    )

    assert snapshot.latest_run is not None
    assert snapshot.latest_run.state == "COMPLETED"
    assert runner.calls[0].ban_valid_empty is True
    assert "nse_fno_ban" in snapshot.latest_run.trigger_source_keys
    assert snapshot.latest_run.can_unlock_confirmed is False


def test_real_executor_reuses_existing_a1_c1_stages_on_normalized_last_good(
    tmp_path: Path, monkeypatch
) -> None:
    store = MarketDataStore(root=tmp_path / "market-data", db_path=tmp_path / "market.db")
    _commit_cash(store)
    monkeypatch.setattr(storage, "DB_PATH", store.db_path)
    storage._INITIALIZED_DB_PATHS.clear()
    matrix = persist_source_use_matrix(
        SourceUseMatrix(
            matrix_id="matrix-fixture",
            rows=(
                SourceUseRow(
                    source_key="nse_bhavcopy_eod",
                    desk="SWING",
                    job="RANK",
                    family="PRICE/ACTIVITY",
                    can_rank=True,
                    can_veto=False,
                    can_unlock_confirmed=False,
                    can_vote=False,
                    ceiling="WATCH",
                    note="fixture permission",
                ),
            ),
            row_count=1,
        )
    )
    monkeypatch.setattr(
        "trendforge_api.selection.cash_post_commit._permission_fingerprint",
        lambda: "permission-fixture",
    )
    ban = _result(
        "nse_fno_ban", ManifestStatus.VALID_EMPTY, rows=0, digest="b" * 64
    )

    execution = run_existing_cash_pipeline(
        CashPipelineRunContext(
            store=store,
            collector_run_id="collector-real",
            trading_date=TRADE_DATE,
            results={"nse_fno_ban": ban},
            trigger_source_keys=("nse_fno_ban",),
            fingerprint="f" * 64,
            prior_permission_fingerprint="permission-fixture",
            ban_valid_empty=True,
        )
    )

    assert [stage.stage_id for stage in execution.stages] == [
        "A1", "A2", "A3", "A4", "A5", "A6", "C0", "B", "C1",
        "R1", "R2", "R3", "R4", "R14", "R5", "S8", "R16",
    ]
    assert execution.permission_fingerprint == "permission-fixture"
    assert execution.rank_batch_id
    assert execution.r1_bundle_id
    assert execution.r2_order_id
    assert execution.r3_resolution_id
    assert execution.r4_pin_id
    assert execution.r14_join_id
    assert execution.r5_structure_id
    assert execution.s8_run_id
    assert execution.r16_dataset_run_id is None
    assert execution.stages[-1].state == "BLOCKED"
    assert "WAIT_R16_SCHEMA_NOT_APPLIED" in execution.stages[-1].detail
    assert matrix.source_activation_ready is False
    assert all(stage.state != "FAILED" for stage in execution.stages)

def test_r3_uses_exact_lineage_keeps_r2_immutable_and_wait_only(
    tmp_path: Path, monkeypatch
) -> None:
    store = MarketDataStore(root=tmp_path / "market-data", db_path=tmp_path / "market.db")
    _commit_cash(store)
    monkeypatch.setattr(storage, "DB_PATH", store.db_path)
    storage._INITIALIZED_DB_PATHS.clear()
    execution = run_existing_cash_pipeline(
        CashPipelineRunContext(
            store=store,
            collector_run_id="collector-r3-lineage",
            trading_date=TRADE_DATE,
            results={},
            trigger_source_keys=("nse_bhavcopy_eod",),
            fingerprint="3" * 64,
            observed_at=NOW,
        )
    )
    assert execution.r3_resolution_id
    bundle = latest_inventory_source_bundle()
    attention = latest_attention_order()
    staging = latest_cash_staging()
    identity = latest_cash_identity()
    persisted = latest_r3_resolution()
    assert bundle and attention and staging and identity and persisted
    assert persisted.run_id == execution.r3_resolution_id
    assert persisted.r1_bundle_hash == bundle.bundle_hash
    assert persisted.r2_run_hash == attention.run_hash
    assert persisted.permission_fingerprint == bundle.permission_fingerprint
    assert persisted.source_activation_ready is False
    assert persisted.can_unlock_confirmed is False
    assert all(row.resolution_state is not SelectionState.CONFIRMED for row in persisted.rows)
    assert all(
        row.entry is None and row.target is None and row.stop is None and row.quantity is None
        for row in persisted.rows
    )

    before = attention.model_dump_json(by_alias=True)
    source_row = attention.rows[0].model_copy(
        update={
            "public_state": SelectionState.WATCH,
            "evidence_direction": EvidenceDirection.BULLISH,
            "attention_rank": 1,
            "attention_priority": 0.8,
            "completeness": 1.0,
        }
    )
    ranked = attention.model_copy(
        update={
            "rows": (source_row,),
            "universe_count": 1,
            "watch_count": 1,
            "wait_count": 0,
            "reject_count": 0,
        }
    )
    rebuilt = build_r3_resolution(
        bundle=bundle,
        attention=ranked,
        source_result=staging.source_result,
        identity=identity,
        compiled_source_contracts=compile_default_inventory().source_contracts,
        expected_permission_fingerprint=bundle.permission_fingerprint,
    )
    assert attention.model_dump_json(by_alias=True) == before
    assert len(rebuilt.rows[0].selected_support_claim_ids) == 1, rebuilt.rows[0].suppressed
    assert rebuilt.rows[0].resolution_state is SelectionState.WAIT
    assert "STRUCTURE" in rebuilt.rows[0].missing_families
    assert rebuilt.rows[0].conflict is False
    with pytest.raises(ValueError, match="WAIT_PERMISSION_MATRIX_MISMATCH"):
        build_r3_resolution(
            bundle=bundle,
            attention=ranked,
            source_result=staging.source_result,
            identity=identity,
            compiled_source_contracts=compile_default_inventory().source_contracts,
            expected_permission_fingerprint="outdated-permission",
        )


def test_r3_get_is_read_only_and_rejects_mixed_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    store = MarketDataStore(root=tmp_path / "market-data", db_path=tmp_path / "market.db")
    _commit_cash(store)
    monkeypatch.setattr(storage, "DB_PATH", store.db_path)
    storage._INITIALIZED_DB_PATHS.clear()
    run_existing_cash_pipeline(
        CashPipelineRunContext(
            store=store,
            collector_run_id="collector-r3-api",
            trading_date=TRADE_DATE,
            results={},
            trigger_source_keys=("nse_bhavcopy_eod",),
            fingerprint="4" * 64,
        )
    )
    bundle = latest_inventory_source_bundle()
    attention = latest_attention_order()
    resolution = latest_r3_resolution()
    assert bundle and attention and resolution
    monkeypatch.setattr(main_module, "latest_inventory_source_bundle", lambda: bundle)
    monkeypatch.setattr(main_module, "latest_attention_order", lambda: attention)
    monkeypatch.setattr(main_module, "latest_r3_resolution", lambda: resolution)
    with TestClient(app) as client:
        response = client.get("/api/v1/selection/resolution")
        assert response.status_code == 200
        payload = response.json()
        assert payload["runId"] == resolution.run_id
        assert payload["stateCeiling"] == "WAIT"
        assert all(row["resolutionState"] != "CONFIRMED" for row in payload["rows"])

        mismatch = resolution.model_copy(update={"r1_bundle_hash": "mismatch"})
        monkeypatch.setattr(main_module, "latest_r3_resolution", lambda: mismatch)
        blocked = client.get("/api/v1/selection/resolution")
        assert blocked.status_code == 503
        assert blocked.json()["detail"]["code"] == "R3_RESOLUTION_NOT_READY"


def test_duplicate_input_recovers_missing_r3_without_rebuilding_r1_r2(
    tmp_path: Path, monkeypatch
) -> None:
    store = MarketDataStore(root=tmp_path / "market-data", db_path=tmp_path / "market.db")
    _commit_cash(store)
    monkeypatch.setattr(storage, "DB_PATH", store.db_path)
    storage._INITIALIZED_DB_PATHS.clear()
    orchestrator = CashPostCommitOrchestrator(
        store=store,
        state_path=tmp_path / "cash-pipeline-state.json",
    )
    results = {
        "nse_bhavcopy_eod": _result(
            "nse_bhavcopy_eod", ManifestStatus.SUCCESS_NEW
        )
    }
    first = orchestrator.process(
        collector_run_id="r3-first",
        trading_date=TRADE_DATE,
        results=results,
    )
    assert first.latest_run and first.latest_run.r3_resolution_id
    original_r1 = first.latest_run.r1_bundle_id
    original_r2 = first.latest_run.r2_order_id
    r2_before = latest_attention_order().model_dump_json(by_alias=True)
    missing_r3 = first.latest_run.model_copy(
        update={
            "r3_resolution_id": None,
            "stages": tuple(
                stage for stage in first.latest_run.stages if stage.stage_id != "R3"
            ),
        }
    )
    orchestrator._write(first.model_copy(update={"latest_run": missing_r3}))
    orchestrator.runner = lambda _context: (_ for _ in ()).throw(
        AssertionError("R1/R2 runner must not be called during R3 recovery")
    )

    recovered = orchestrator.process(
        collector_run_id="r3-recovery",
        trading_date=TRADE_DATE,
        results=results,
    )
    assert recovered.latest_dispatch.decision == "DISPATCHED"
    assert recovered.latest_run.r1_bundle_id == original_r1
    assert recovered.latest_run.r2_order_id == original_r2
    assert recovered.latest_run.r3_resolution_id, recovered.latest_run.stages[-1]
    assert latest_attention_order().model_dump_json(by_alias=True) == r2_before
    assert recovered.latest_run.stages[-1].stage_id == "R3"
    assert recovered.latest_run.stages[-1].state == "COMPLETED"
