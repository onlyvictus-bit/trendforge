"""Atomic, read-only, one-assembly research snapshot acceptance tests."""
from __future__ import annotations

import json
import sqlite3
import threading
import socket
from collections import Counter
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.market_data_store import MarketDataStore
from trendforge_api.selection import snapshot_service as service, s8_service
from trendforge_api.selection.cash_a1_staging import persist_cash_staging
from trendforge_api.selection.cash_a2_identity import persist_cash_identity
from trendforge_api.selection.cash_a3_discovery import persist_cash_discovery
from trendforge_api.selection.cash_a4_history import persist_cash_history
from test_s3_cheap_discovery import _discovery
from test_s4_structure_pack import (
    DECISION_AT, _fixtures, _store_breakout_history,
    build_r4_identity_pin, persist_r4_identity_pin,
    build_r14_ca_join, persist_r14_ca_join,
    build_r5_structure_batch, persist_r5_structure_batch,
    persist_inventory_source_bundle, persist_attention_order, SelectionState,
)


@pytest.fixture
def spine(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "snapshot.db")
    instrument, identity, history, bundle, attention, staging, context = _fixtures()
    _store_breakout_history(instrument)
    discovery = _discovery([("R5TEST", SelectionState.WATCH)])
    discovery = discovery.model_copy(update={"identity_batch_id": identity.batch_id})
    row = attention.rows[0].model_copy(update={"lineage": {
        **attention.rows[0].lineage,
        "cashPipelineRunId": attention.cash_pipeline_run_id,
        "discoveryBatchId": discovery.batch_id,
        "tradingDate": attention.trading_date,
    }})
    attention = attention.model_copy(update={"rows": (row,)})
    persist_cash_staging(staging)
    persist_cash_identity(identity)
    persist_cash_history(history)
    persist_cash_discovery(discovery)
    persist_inventory_source_bundle(bundle)
    persist_attention_order(attention)
    pin = persist_r4_identity_pin(build_r4_identity_pin(
        bundle=bundle, attention=attention, identity=identity,
    ))
    ca = persist_r14_ca_join(build_r14_ca_join(
        bundle=bundle, attention=attention, identity=identity, pin=pin,
        observations=[], vintages=[], decision_at=DECISION_AT,
    ))
    r5 = persist_r5_structure_batch(build_r5_structure_batch(
        bundle=bundle, attention=attention, identity=identity, history=history,
        staging=staging, context=context, ca_join=ca, decision_at=DECISION_AT,
    ))
    MarketDataStore(db_path=storage.DB_PATH, root=tmp_path / "objects").initialize_schema()
    return bundle, attention, r5


def _dump():
    with sqlite3.connect(storage.DB_PATH) as conn:
        return "\n".join(conn.iterdump())


def test_one_assembly_read_only_real_spine(spine, monkeypatch):
    counts = Counter()
    for name in ("build_s3_cheap_discovery", "build_native_core_run", "build_s2_market_weather",
                 "build_s4_structure_pack", "build_s5_enrichment", "build_s6_resolution", "build_s7_state"):
        original = getattr(s8_service, name)

        def observed(*args, _name=name, _fn=original, **kwargs):
            counts[_name] += 1
            return _fn(*args, **kwargs)

        monkeypatch.setattr(s8_service, name, observed)
    before = _dump()
    value = service.build_research_snapshot(lane_factory=lambda: {"effectiveLane": "FREE_OFFICIAL"})
    assert value.assembly_count == 1
    assert value.panels["s7State"] is not None, value.panel_status
    assert value.panels["s8Latest"]["persisted"] is False
    assert value.panels["s7State"]["confirmedCount"] == 0
    assert value.panels["s8Latest"]["lineage"]["r2RunHash"] == spine[1].run_hash
    assert value.decision_at == DECISION_AT
    assert set(counts.values()) == {1}
    assert len(counts) == 7
    assert before == _dump()


def test_snapshot_http_contract(spine):
    response = TestClient(app).get("/api/v1/selection/snapshot")
    assert response.status_code == 200, response.text
    data = response.json()
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Research-Snapshot-ID"] == data["snapshotId"]
    assert data["coherence"] == "SQLITE_READ_TRANSACTION"
    assert set(data["panels"]) == set(service.PANEL_KEYS)
    assert TestClient(app).post("/api/v1/selection/snapshot").status_code == 405


def test_missing_database_fails_without_creation(tmp_path, monkeypatch):
    path = tmp_path / "missing.db"
    monkeypatch.setattr(storage, "DB_PATH", path)
    response = TestClient(app).get("/api/v1/selection/snapshot")
    assert response.status_code == 503
    assert not path.exists()


def test_mixed_core_is_rejected(spine, monkeypatch):
    attention = spine[1].model_copy(update={"r1_bundle_hash": "other-generation"})
    monkeypatch.setattr(service, "latest_attention_order", lambda: attention)
    with pytest.raises(ValueError, match="WAIT_RESEARCH_SNAPSHOT_LINEAGE"):
        service.build_research_snapshot(lane_factory=lambda: {})


def test_missing_r5_keeps_core_but_never_reuses_later_panels(spine, monkeypatch):
    monkeypatch.setattr(service, "latest_r5_structure_batch", lambda: None)
    value = service.build_research_snapshot(lane_factory=lambda: {})
    assert value.assembly_count == 0
    assert value.panels["attention"] is not None
    assert value.panels["s7State"] is None
    assert value.panels["s8Latest"] is None
    assert value.panel_status["structure"].code == "WAIT_SNAPSHOT_R5_LINEAGE"
    assert value.panels["labBundle"]["nativeDefinitions"]
    assert value.panels["labBundle"]["nativeCore"] is None


def test_optional_enrichment_failure_is_attempted_once(spine, monkeypatch):
    calls = []

    def failure(**_):
        calls.append(1)
        raise ValueError("WAIT_TEST_ENRICHMENT")

    monkeypatch.setattr(s8_service, "build_s5_enrichment", failure)
    # Fallbacks in the consumer stages would otherwise rebuild failing S5.
    from trendforge_api.selection import s6_family_resolution, s7_state_gates
    monkeypatch.setattr(s6_family_resolution, "build_s5_enrichment", failure)
    monkeypatch.setattr(s7_state_gates, "build_s5_enrichment", failure)
    value = service.build_research_snapshot(lane_factory=lambda: {})
    assert calls == [1]
    assert value.panels["s5Enrich"] is None
    assert value.panels["s7State"] is not None, value.panel_status


def test_corrupt_envelope_is_not_accepted(spine):
    value = service.build_research_snapshot(lane_factory=lambda: {})
    tampered = value.model_dump(mode="json", by_alias=True)
    tampered["panels"]["attention"]["rows"][0]["symbol"] = "CHANGED"
    with pytest.raises(ValueError, match="SNAPSHOT_HASH_MISMATCH"):
        service.ResearchSnapshotV1.model_validate(tampered)


def test_serialized_envelope_round_trip_is_stable(spine):
    value = service.build_research_snapshot(lane_factory=lambda: {}, captured_at=datetime(2026, 9, 7, tzinfo=UTC))
    payload = json.loads(value.model_dump_json(by_alias=True))
    assert service.ResearchSnapshotV1.model_validate(payload).snapshot_hash == value.snapshot_hash


def test_concurrent_publish_cannot_mix_old_and_new_generations(spine, monkeypatch):
    """Publish a new R1/R2 between the reader's first and second calls."""
    old_bundle, old_attention, _ = spine
    bundle = old_bundle.model_dump(mode="json", by_alias=True)
    bundle.update(bundleId="r1-next", bundleHash="b" * 64)
    attention = old_attention.model_dump(mode="json", by_alias=True)
    attention.update(runId="r2-next", runHash="c" * 64, r1BundleId=bundle["bundleId"], r1BundleHash=bundle["bundleHash"])
    failures = []

    def publish():
        try:
            with sqlite3.connect(storage.DB_PATH, timeout=5) as conn:
                for payload, run_id, profile_id in (
                    (bundle, "r1-next", old_bundle.profile_id),
                    (attention, "r2-next", old_attention.profile_id),
                ):
                    conn.execute(
                        "INSERT INTO selection_scan_runs (run_id,profile_id,as_of,persisted_at,payload_json) VALUES (?,?,?,?,?)",
                        (run_id, profile_id, DECISION_AT.isoformat(), "2099-01-01T00:00:00Z", json.dumps(payload)),
                    )
        except Exception as exc:
            failures.append(exc)

    original = service.latest_inventory_source_bundle

    def read_then_publish():
        old = original()
        writer = threading.Thread(target=publish)
        writer.start()
        writer.join(timeout=5)
        assert not writer.is_alive(), "reader blocked concurrent WAL writer"
        assert not failures
        return old

    monkeypatch.setattr(service, "latest_inventory_source_bundle", read_then_publish)
    first = service.build_research_snapshot(lane_factory=lambda: {})
    assert first.panels["evidence"]["bundleId"] == old_bundle.bundle_id
    assert first.panels["attention"]["runId"] == old_attention.run_id
    assert first.panels["s7State"] is not None
    monkeypatch.setattr(service, "latest_inventory_source_bundle", original)
    second = service.build_research_snapshot(lane_factory=lambda: {})
    assert second.panels["evidence"]["bundleId"] == "r1-next"
    assert second.panels["attention"]["runId"] == "r2-next"
    assert second.panels["s7State"] is None  # old downstream objects cannot join the new core
    assert first.snapshot_id != second.snapshot_id


def test_lineage_mismatch_rejected_even_with_recomputed_checksum(spine):
    value = service.build_research_snapshot(lane_factory=lambda: {})
    tampered = value.model_dump(mode="json", by_alias=True)
    tampered["panels"]["s7State"]["s6RunHash"] = "different-run"
    body = {k: v for k, v in tampered.items() if k not in {"snapshotId", "snapshotHash"}}
    tampered["snapshotHash"] = service._digest(body)
    tampered["snapshotId"] = "rs-" + tampered["snapshotHash"]
    with pytest.raises(ValueError, match="SNAPSHOT_PANEL_LINEAGE_MISMATCH"):
        service.ResearchSnapshotV1.model_validate(tampered)


def test_current_projection_uses_one_evaluation_clock_not_old_price_time(spine):
    captured = datetime(2026, 9, 7, 10, tzinfo=UTC)
    value = service.build_research_snapshot(lane_factory=lambda: {}, captured_at=captured)
    assert value.decision_at == DECISION_AT
    assert value.evaluated_at == captured
    for name in ("s4Pack", "s5Enrich", "s6Resolve", "s7State", "s8Latest"):
        assert datetime.fromisoformat(value.panels[name]["builtAt"]) == captured


def test_refresh_never_attempts_outbound_network_or_source_acquisition(spine, monkeypatch):
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(1)
        raise AssertionError("snapshot may not fetch sources or call a broker")

    monkeypatch.setattr(socket.socket, "connect", deny)
    value = service.build_research_snapshot(lane_factory=lambda: {})
    assert value.panels["s7State"] is not None
    assert attempts == []


def test_saved_activation_is_rechecked_without_writing(spine):
    from trendforge_api.selection.r2b_live import build_r2b_named_activation, persist_r2b_named_activation
    stored = persist_r2b_named_activation(build_r2b_named_activation())
    before = _dump()
    value = service.build_research_snapshot(lane_factory=lambda: {})
    assert value.panels["namedActivation"]["runHash"] == stored.run_hash
    assert before == _dump()


def test_validation_metrics_use_the_captured_dataset_id(spine, monkeypatch):
    calls = []
    monkeypatch.setattr(service, "status_payload", lambda: {"latestDatasetRunId": "dataset-pinned"})

    def metrics(*, dataset_run_id):
        calls.append(dataset_run_id)
        return {"metrics": [], "count": 0}

    monkeypatch.setattr(service, "metrics_payload", metrics)
    value = service.build_research_snapshot(lane_factory=lambda: {})
    assert calls == ["dataset-pinned"]
    assert value.panel_status["r16Metrics"].scope == "VALIDATION"