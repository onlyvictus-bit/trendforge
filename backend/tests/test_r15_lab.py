"""File A R15 Scanner Lab bundle tests (PK7 / UI-007).

Law under test: one 200 with named inner codes; confirmedCount pinned 0;
POST forbidden; PK shadow parity state is descriptive only.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app


def test_bundle_200_with_named_codes_on_empty_spine(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r15-empty.db")
    storage._INITIALIZED_DB_PATHS.clear()
    client = TestClient(app)
    response = client.get("/api/v1/scanners/lab-bundle")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schemaVersion"] == "trendforge.scanner-lab.v1"
    assert payload["confirmedCount"] == 0
    assert payload["executable"] is False
    assert payload["emitsClaims"] is False
    assert len(payload["nativeDefinitions"]) >= 5
    assert len(payload["pipeDefinitions"]) >= 2
    assert payload["nativeCore"] is None
    assert payload["nativeCoreCode"]
    for entry in payload["pipeRuns"]:
        assert entry["run"] is None or entry["code"] is None
        if entry["run"] is None:
            # Typed spine code (convention: WAIT_* / R5_EVIDENCE_NOT_READY).
            assert str(entry["code"])
    assert payload["pkShadow"]["state"] == "PK_SHADOW"
    assert payload["pkShadow"]["parity"] in {"PARITY_OK", "PARITY_UNKNOWN"}


def test_bundle_post_is_405() -> None:
    client = TestClient(app)
    assert client.post("/api/v1/scanners/lab-bundle").status_code == 405


def test_bundle_pipe_runs_compute_on_live_spine(tmp_path, monkeypatch) -> None:
    from trendforge_api.hybrid_v2.tests_support.fixtures import (
        persist_overlay_lineage,
    )

    persist_overlay_lineage(tmp_path, monkeypatch, with_structure=True)
    client = TestClient(app)
    response = client.get("/api/v1/scanners/lab-bundle")
    assert response.status_code == 200
    payload = response.json()
    assert payload["nativeCore"] is not None
    assert payload["nativeCore"]["confirmedCount"] == 0
    assert payload["nativeCoreCode"] is None
    runs = payload["pipeRuns"]
    assert len(runs) >= 2
    # Either a computed run (with stage list) or a named WAIT code — never both.
    for entry in runs:
        if entry["run"] is not None:
            assert entry["code"] is None
            assert entry["run"]["confirmedCount"] == 0
        else:
            assert entry["code"]
