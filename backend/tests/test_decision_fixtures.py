from __future__ import annotations

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.decision_fixtures import (
    build_named_state_fixture_batch,
    load_demo_decision_run,
)
from trendforge_api.main import app


def test_named_state_fixture_batch_covers_required_outputs() -> None:
    batch = build_named_state_fixture_batch()
    states = {item.final_state for item in batch.results}
    assert {
        "READY",
        "WAIT",
        "REJECT",
        "NO_TRADE",
        "WAIT_DATA_WEAK",
        "LOCKED_NO_TRADE",
    } <= states
    assert all(item.executable is False for item in batch.results)
    assert (
        next(item for item in batch.results if item.symbol == "TF_REJECT").stage2_label
        == "BLOCKED"
    )
    assert (
        next(item for item in batch.results if item.symbol == "TF_WAIT").stage2_label
        == "WAIT_TRIGGER"
    )


def test_demo_decision_run_persists_candidates_and_causal_audit(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "decision-fixtures.db")
    summary = load_demo_decision_run()
    assert summary["candidateCount"] == 8
    assert summary["stateCounts"]["READY"] == 1
    rows = storage.list_scanner_candidates(run_id=summary["runId"], limit=20)
    assert len(rows) == 8
    ready = next(row["payload"] for row in rows if row["symbol"] == "TF_READY")
    assert ready["causalEvaluation"]["stage1Label"] == "ELIGIBLE"
    assert ready["causalEvaluation"]["stage2Label"] == "CONFIRMED"
    assert ready["causalEvaluation"]["executable"] is False
    gates = storage.list_gate_decisions(run_id=str(summary["runId"]), limit=100)
    assert any(
        row["gate_key"] == "STAGE1_CAUSAL" and row["symbol"] == "TF_READY"
        for row in gates
    )


def test_demo_decision_api_loads_explicit_fixture_run(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "decision-api.db")
    response = TestClient(app).post("/api/demo/decision-scenarios/load")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "DETERMINISTIC_DEMO"
    assert payload["candidateCount"] == 8
    candidates = TestClient(app).get(
        "/api/scanner/candidates", params={"runId": payload["runId"]}
    )
    assert candidates.status_code == 200
    assert len(candidates.json()) == 8
    radar = TestClient(app).get("/api/radar")
    assert radar.status_code == 200
    radar_rows = radar.json()
    assert len(radar_rows) == 8
    assert {row["state"] for row in radar_rows} >= {
        "READY",
        "WAIT",
        "REJECT",
        "NO_TRADE",
        "LOCKED_NO_TRADE",
    }
    assert len(TestClient(app).get("/api/shortlist").json()) == 1
    assert all(
        row["statusGroup"] == "wait"
        for row in TestClient(app).get("/api/wait-candidates").json()
    )
    assert all(
        row["statusGroup"] == "reject"
        for row in TestClient(app).get("/api/rejected-candidates").json()
    )
    latest = TestClient(app).get("/api/scanner/latest")
    assert latest.status_code == 200
    assert latest.json()["run"]["id"] == payload["runId"]
    assert len(latest.json()["candidates"]) == 8
