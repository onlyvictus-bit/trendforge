"""R16 cash-EOD point-in-time and read-only authority tests."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trendforge_api import storage


def _bar(day: date, *, open_: float, high: float, low: float, close: float) -> dict:
    return {
        "trade_date": day.isoformat(),
        "available_at": datetime(
            day.year, day.month, day.day, 13, 0, tzinfo=UTC
        ).isoformat(),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1000.0,
        "artifact_hash": f"hash-{day.isoformat()}",
    }


def _s8_payload() -> dict:
    return {
        "runId": "s8-2026-08-01",
        "tradingDate": "2026-08-01",
        "asOf": "2026-08-01T14:00:00+00:00",
        "lineage": {
            "r1RunHash": "r1-hash",
            "r2RunHash": "r2-hash",
            "r14RunHash": "r14-hash",
            "r5RunHash": "r5-hash",
            "s2RunId": "s2-id",
            "s3RunId": "s3-id",
            "s4PackId": "s4-id",
            "s5RunId": "s5-id",
            "s6RunId": "s6-id",
            "s7RunId": "s7-id",
            "nativeGuidanceRunHash": "native-hash",
            "missingStages": [],
        },
        "s3Completeness": {"ratio": 1.0, "threshold": 0.95},
        "rows": [
            {
                "candidateId": "candidate-AAA",
                "symbol": "AAA",
                "publicState": "WATCH",
                "evidenceDirection": "BULLISH",
            }
        ],
    }


def _ready_hypothesis():
    from trendforge_api.selection.r16_pit import R16FrozenHypothesisV1

    return R16FrozenHypothesisV1(
        hypothesis_id="hyp-1",
        dataset_revision_hash="revision",
        source_s8_run_id="s8-1",
        source_s8_hash="s8-hash",
        source_s8_lineage_hash="lineage",
        candidate_id="candidate-AAA",
        symbol="AAA",
        trading_date="2026-08-01",
        decision_cutoff_at=datetime(2026, 8, 1, 14, 0, tzinfo=UTC),
        direction="BULLISH",
        horizon_sessions=5,
        public_state="WATCH",
        geometry_status="READY",
        trigger_price=100,
        entry_low=100,
        entry_high=101,
        invalidation=95,
        target_1=105,
        target_2=110,
        source_bar_hashes=("bar-hash",),
    )


def test_schema_requires_explicit_application(tmp_path, monkeypatch) -> None:
    from trendforge_api.selection.r16_store import apply_r16_schema, r16_schema_status

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r16.db")
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    assert r16_schema_status()["applied"] is False

    result = apply_r16_schema()
    assert result["applied"] is True
    assert set(result["tables"]) == {
        "pit_dataset_runs",
        "pit_hypotheses",
        "pit_observations",
        "pit_fold_results",
        "pit_metrics",
        "pit_approval_ledger",
    }


def test_frozen_hypotheses_are_horizon_bound_and_ignore_future_bars() -> None:
    from trendforge_api.selection.r16_pit import build_frozen_hypotheses

    start = date(2026, 7, 1)
    visible = [
        _bar(
            start + timedelta(days=i),
            open_=100 + i,
            high=101 + i,
            low=99 + i,
            close=100 + i,
        )
        for i in range(22)
    ]
    first = build_frozen_hypotheses(
        s8_payload=_s8_payload(), bars_by_symbol={"AAA": visible}
    )
    changed = build_frozen_hypotheses(
        s8_payload=_s8_payload(),
        bars_by_symbol={
            "AAA": visible
            + [_bar(date(2026, 8, 3), open_=500, high=900, low=1, close=700)]
        },
    )
    assert first == changed
    assert {row.horizon_sessions for row in first} == {5, 10, 20}
    assert len({row.hypothesis_id for row in first}) == 3


def test_incomplete_s8_lineage_is_not_eligible() -> None:
    from trendforge_api.selection.r16_pit import build_frozen_hypotheses

    payload = _s8_payload()
    payload["lineage"]["s3RunId"] = None
    with pytest.raises(ValueError, match="WAIT_R16_S8_LINEAGE_INCOMPLETE"):
        build_frozen_hypotheses(s8_payload=payload, bars_by_symbol={"AAA": []})


def test_r16_labeler_is_stop_first_on_same_bar() -> None:
    from trendforge_api.selection.r16_pit import label_hypothesis

    bars = [_bar(date(2026, 8, 3), open_=100, high=106, low=94, close=102)]
    observation = label_hypothesis(_ready_hypothesis(), bars=bars)
    assert observation.status == "STOP"
    assert observation.collision_policy == "STOP_FIRST_CONSERVATIVE"
    assert observation.intrabar_ambiguous is True
    assert observation.confirmation_authorized is False


def test_gap_beyond_entry_is_no_entry_not_an_optimistic_fill() -> None:
    from trendforge_api.selection.r16_pit import label_hypothesis

    bars = [_bar(date(2026, 8, 3), open_=103, high=106, low=102, close=104)]
    observation = label_hypothesis(_ready_hypothesis(), bars=bars)
    assert observation.status == "NO_ENTRY"
    assert observation.entry_price is None
    assert observation.censor_reason == "GAP_BEYOND_ENTRY_ZONE_NO_CHASE"


def test_observation_identity_is_idempotent_for_same_path_and_append_only_for_new_path() -> None:
    from trendforge_api.selection.r16_pit import label_hypothesis

    first_bar = _bar(date(2026, 8, 3), open_=99, high=99.5, low=98, close=99)
    first = label_hypothesis(_ready_hypothesis(), bars=[first_bar])
    repeated = label_hypothesis(_ready_hypothesis(), bars=[first_bar])
    second = label_hypothesis(
        _ready_hypothesis(),
        bars=[first_bar, _bar(date(2026, 8, 4), open_=100, high=102, low=99, close=101)],
    )
    assert first.observation_id == repeated.observation_id
    assert first.path_hash == repeated.path_hash
    assert second.observation_id != first.observation_id


def test_missing_geometry_never_becomes_zero() -> None:
    from trendforge_api.selection.r16_pit import build_frozen_hypotheses

    result = build_frozen_hypotheses(
        s8_payload=_s8_payload(), bars_by_symbol={"AAA": []}
    )
    assert len(result) == 3
    assert all(row.geometry_status == "NO_GEOMETRY" for row in result)
    assert all(row.entry_low is None for row in result)
    assert all(row.invalidation is None for row in result)
    assert all(row.exclusion_reason for row in result)


def test_approval_policy_fails_closed_without_costs() -> None:
    from trendforge_api.selection.r16_metrics import evaluate_approval

    approval = evaluate_approval(
        metrics={
            "eligibleDateCount": 150,
            "eligibleObservationCount": 600,
            "resolvedCount": 300,
            "distinctDateCount": 150,
            "foldCount": 3,
            "censorRate": 0.10,
            "missingS8Rate": 0.01,
            "bootstrapWidth": 0.10,
            "costModelVersion": None,
        },
        dataset_run_id="dataset-1",
    )
    assert approval.validation_status == "PIT_NOT_APPROVED"
    assert approval.confirmation_authorized is False
    assert approval.execution_authorized is False
    assert "WAIT_COST_MODEL" in approval.blockers


def test_r16_routes_are_read_only_and_schema_waits(tmp_path, monkeypatch) -> None:
    from trendforge_api.main import app

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r16-routes.db")
    storage._INITIALIZED_DB_PATHS.clear()
    client = TestClient(app)
    paths = (
        "/api/v1/selection/pit/status",
        "/api/v1/selection/pit/runs",
        "/api/v1/selection/pit/observations",
        "/api/v1/selection/pit/metrics",
        "/api/v1/selection/pit/approval",
    )
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert client.post(path).status_code == 405
    status = client.get(paths[0]).json()
    assert status["validationStatus"] == "PIT_NOT_APPROVED"
    assert "WAIT_R16_SCHEMA_NOT_APPLIED" in status["blockers"]

def _persist_r16_test_bar(
    day: date, *, high: float, low: float, close: float, symbol: str = "AAA"
) -> None:
    from trendforge_api.selection.cash_a4_history import CashRawSessionBar, _store_raw_bar
    from trendforge_api.selection.contracts import stable_id
    from trendforge_api.market_data_store import MarketDataStore

    market = MarketDataStore(root=Path(storage.DB_PATH).parent / "market", db_path=storage.DB_PATH)
    market.initialize_schema()
    artifact = market.install_object(
        json.dumps({"symbol": symbol, "date": day.isoformat(), "high": high, "low": low, "close": close}).encode(),
        extension="json", media_type="application/json",
    ).content_hash
    _store_raw_bar(
        CashRawSessionBar(
            bar_id=stable_id("r16-test-bar", symbol, day.isoformat(), artifact),
            instrument_id=f"NSE:{symbol}:EQ",
            symbol=symbol,
            trade_date=day,
            artifact_hash=artifact,
            series_id=stable_id("r16-series", symbol, artifact),
            open=close,
            high=high,
            low=low,
            close=close,
            previous_close=close,
            volume=1000,
            traded_value=100000,
        )
    )

def _prepare_r16_service_db(tmp_path, monkeypatch) -> None:
    from trendforge_api.historical_retention import HistoricalRetentionAuthority, RetentionReferenceType
    from trendforge_api.retention_producer import DurableRetentionRegistrar
    from trendforge_api.retention_publication import RetentionEvidenceRoot, RetentionPublicationRequest, RetentionPublicationStore
    from trendforge_api.selection.r16_store import apply_r16_schema
    from trendforge_api.selection.s8_persist_run import PROFILE_ID as S8_PROFILE_ID
    from trendforge_api.selection.store import persist_selection_payload

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r16-service.db")
    monkeypatch.delenv("TRENDFORGE_MARKET_DATA_DB_PATH", raising=False)
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    apply_r16_schema()

    payload = _s8_payload()
    payload["schemaVersion"] = "trendforge.s8-scan.v1"
    payload["runId"] = "s8-2026-08-03"
    payload["tradingDate"] = "2026-08-03"
    payload["asOf"] = "2026-08-03T14:00:00+00:00"
    start = date(2026, 7, 1)
    for index in range(22):
        if index < 8:
            high, low, close = 101.0, 99.0, 100.0
        else:
            high, low, close = 110.0, 108.0, 109.0
        if index == 19:
            low = 107.9
        _persist_r16_test_bar(
            start + timedelta(days=index), high=high, low=low, close=close
        )

    with storage.connect() as conn:
        hashes = [row[0] for row in conn.execute("SELECT artifact_hash FROM cash_raw_session_bars ORDER BY trade_date")]
    authority = HistoricalRetentionAuthority(db_path=storage.DB_PATH)
    publications = RetentionPublicationStore(
        db_path=storage.DB_PATH,
        registrar=DurableRetentionRegistrar(db_path=storage.DB_PATH, authority=authority),
    )
    request = RetentionPublicationRequest(
        artifact_type="S8_DECISION_VERSION", artifact_id=payload["runId"],
        artifact_version=payload["schemaVersion"],
        reference_type=RetentionReferenceType.DECISION_VERSION,
        evidence_roots=tuple(RetentionEvidenceRoot(role=f"R1_RAW_{index}", content_hash=value) for index, value in enumerate(hashes)),
        lineage={"s8": payload["lineage"], "tradingDate": payload["tradingDate"],
                 "s8PayloadHash": hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()},
        created_at=datetime.fromisoformat(payload["asOf"]),
    )
    publications.stage_owned(request)
    publications.finalize(request.publication_id)
    persist_selection_payload(
        run_id=payload["runId"], profile_id=S8_PROFILE_ID,
        as_of=datetime.fromisoformat(payload["asOf"]), payload=payload,
    )
    publications.mark_published(request.publication_id)


def test_bulk_bar_loader_excludes_unrequested_symbols_and_old_history(
    tmp_path, monkeypatch
) -> None:
    from trendforge_api.selection.cash_a4_history import list_raw_bars_by_symbol

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r16-bounded-bars.db")
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    _persist_r16_test_bar(
        date(2026, 6, 1), high=101, low=99, close=100, symbol="AAA"
    )
    _persist_r16_test_bar(
        date(2026, 8, 1), high=111, low=109, close=110, symbol="AAA"
    )
    _persist_r16_test_bar(
        date(2026, 8, 1), high=211, low=209, close=210, symbol="BBB"
    )

    rows = list_raw_bars_by_symbol(
        {"AAA"}, from_date=date(2026, 7, 1), through=date(2026, 8, 31)
    )
    assert set(rows) == {"AAA"}
    assert [row.trade_date for row in rows["AAA"]] == [date(2026, 8, 1)]


def test_r16_query_plans_use_dataset_and_exact_cell_indexes(
    tmp_path, monkeypatch
) -> None:
    from trendforge_api.selection.r16_store import (
        apply_r16_schema,
        query_plan,
    )

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r16-query-plan.db")
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    apply_r16_schema()

    observation_plan = query_plan(
        "pit_observations",
        "SELECT payload_json FROM pit_observations "
        "WHERE dataset_run_id = ? ORDER BY rowid DESC LIMIT ?",
        ("dataset-1", 51),
    )
    metric_plan = query_plan(
        "pit_metrics",
        "SELECT payload_json FROM pit_metrics "
        "WHERE exact_cell = ? ORDER BY created_at DESC LIMIT 1",
        ("NSE_CASH_EOD|PRF-003|SWING|BULLISH|5",),
    )

    assert any("idx_pit_observations_dataset_status" in row for row in observation_plan)
    assert any("idx_pit_metrics_cell_latest" in row for row in metric_plan)

def test_same_date_conflicting_s8_payloads_fail_closed(
    tmp_path, monkeypatch
) -> None:
    from trendforge_api.selection.r16_service import run_incremental
    from trendforge_api.selection.s8_persist_run import PROFILE_ID as S8_PROFILE_ID
    from trendforge_api.selection.store import persist_selection_payload

    _prepare_r16_service_db(tmp_path, monkeypatch)
    conflicting = _s8_payload()
    conflicting["runId"] = "s8-2026-08-03-conflict"
    conflicting["tradingDate"] = "2026-08-03"
    conflicting["asOf"] = "2026-08-03T14:01:00+00:00"
    conflicting["rows"][0]["publicState"] = "WAIT"
    persist_selection_payload(
        run_id=conflicting["runId"],
        profile_id=S8_PROFILE_ID,
        as_of=datetime.fromisoformat(conflicting["asOf"]),
        payload=conflicting,
    )

    result = run_incremental(owner_id="test-conflict-owner")
    assert result["validationStatus"] == "PIT_NOT_APPROVED"
    assert result["replay"]["state"] == "WAIT"
    assert result["replay"]["datasetRunCount"] == 0
    assert result["replay"]["sourceDateConflictCount"] == 1
    assert all(
        row["reason"].startswith("WAIT_R16_S8_DATE_CONFLICT")
        for row in result["replay"]["rejectedS8"]
    )

def test_r16_service_replay_is_incremental_append_only_and_idempotent(
    tmp_path, monkeypatch
) -> None:
    from trendforge_api.selection.r16_service import run_incremental
    from trendforge_api.selection.r16_store import (
        list_hypotheses,
        list_observations,
    )

    _prepare_r16_service_db(tmp_path, monkeypatch)
    _persist_r16_test_bar(date(2026, 8, 4), high=109.5, low=108.5, close=109.0)

    first = run_incremental(owner_id="test-owner-1")
    assert first["replay"]["datasetRunCount"] == 1
    assert first["replay"]["hypothesisCount"] == 3
    assert first["replay"]["observationsAppended"] == 3
    assert len(list_hypotheses(limit=100)) == 3
    assert len(list_observations(limit=100)) == 3
    assert first["confirmationAuthorized"] is False
    assert first["executionAuthorized"] is False

    _persist_r16_test_bar(date(2026, 8, 5), high=110.5, low=109.0, close=110.2)
    second = run_incremental(owner_id="test-owner-2")
    assert second["replay"]["observationsAppended"] == 3
    assert len(list_observations(limit=100)) == 6

    repeated = run_incremental(owner_id="test-owner-3")
    assert repeated["replay"]["observationsAppended"] == 0
    assert len(list_observations(limit=100)) == 6
    assert all(
        row["validationStatus"] == "PIT_NOT_APPROVED"
        for row in repeated["approvals"]
    )


def test_r16_worker_lease_is_singleton_and_recovers_after_release(
    tmp_path, monkeypatch
) -> None:
    from trendforge_api.selection.r16_store import (
        acquire_worker_lease,
        apply_r16_schema,
        release_worker_lease,
    )

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r16-lease.db")
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    apply_r16_schema()

    assert acquire_worker_lease("owner-a") is True
    assert acquire_worker_lease("owner-b") is False
    release_worker_lease("owner-a")
    assert acquire_worker_lease("owner-b") is True
    release_worker_lease("owner-b")


def test_r16_read_only_routes_do_not_mutate_applied_schema(
    tmp_path, monkeypatch
) -> None:
    from trendforge_api.main import app
    from trendforge_api.selection.r16_store import TABLES, apply_r16_schema

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r16-readonly.db")
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    apply_r16_schema()

    def counts() -> dict[str, int]:
        conn = storage.connect()
        try:
            return {
                table: int(conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"])
                for table in TABLES
            }
        finally:
            conn.close()

    before = counts()
    client = TestClient(app)
    for path in (
        "/api/v1/selection/pit/status",
        "/api/v1/selection/pit/runs",
        "/api/v1/selection/pit/observations",
        "/api/v1/selection/pit/metrics",
        "/api/v1/selection/pit/approval",
    ):
        assert client.get(path).status_code == 200
    assert counts() == before


def test_lineage_incomplete_same_date_does_not_quarantine_valid_s8(
    tmp_path, monkeypatch
 ) -> None:
    from trendforge_api.selection.r16_service import run_incremental
    from trendforge_api.selection.s8_persist_run import PROFILE_ID as S8_PROFILE_ID
    from trendforge_api.selection.store import persist_selection_payload

    _prepare_r16_service_db(tmp_path, monkeypatch)
    incomplete = _s8_payload()
    incomplete["runId"] = "s8-2026-08-03-incomplete"
    incomplete["tradingDate"] = "2026-08-03"
    incomplete["asOf"] = "2026-08-03T14:01:00+00:00"
    incomplete["lineage"]["missingStages"] = ["S2_STALE"]
    persist_selection_payload(
        run_id=incomplete["runId"],
        profile_id=S8_PROFILE_ID,
        as_of=datetime.fromisoformat(incomplete["asOf"]),
        payload=incomplete,
    )

    result = run_incremental(owner_id="test-incomplete-owner")
    assert result["replay"]["datasetRunCount"] == 1
    assert result["replay"]["sourceDateConflictCount"] == 0
    rejected = {
        row["runId"]: row["reason"] for row in result["replay"]["rejectedS8"]
    }
    assert rejected[incomplete["runId"]] == "WAIT_R16_S8_LINEAGE_INCOMPLETE:S2_STALE"
