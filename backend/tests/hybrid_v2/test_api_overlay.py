"""Overlay API: typed 200/503/404, POST 405, C8/C11 field contracts."""

from __future__ import annotations

from fastapi.testclient import TestClient

from trendforge_api.hybrid_v2.pipeline import build_hybrid_v2_overlay
from trendforge_api.hybrid_v2.tests_support.fixtures import persist_overlay_lineage
from trendforge_api.main import app


def test_get_overlay_200_with_contract_fields(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    client = TestClient(app)
    response = client.get("/api/v1/hybrid-v2/overlay?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["schemaVersion"] == "trendforge.hybrid-v2-overlay.v1"
    assert any("HYBRID_V2_OVERLAY_NOT_FILE_A" in warning for warning in body["warnings"])
    row = body["rows"][0]
    assert row["r14CaState"] in {"NONE", "ADJUSTED", "WAIT_CA", "MISSING"}
    assert 0 <= row["kellyIllustration"] <= 0.02
    assert row["whyWait"]
    assert row["s6VehicleStatus"] == "UNKNOWN_NEEDS_R12"
    assert row["asStatus"] in {"USABLE", "UNKNOWN", "STALE", "WAIT_CA"}


def test_overlay_symbol_endpoint_and_404(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    client = TestClient(app)
    hit = client.get("/api/v1/hybrid-v2/overlay/HVBTEST")
    assert hit.status_code == 200
    assert hit.json()["symbol"] == "HVBTEST"
    miss = client.get("/api/v1/hybrid-v2/overlay/NOPE")
    assert miss.status_code == 404
    assert miss.json()["detail"]["code"] == "HYBRID_V2_SYMBOL_NOT_FOUND"


def test_post_is_405(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    client = TestClient(app)
    assert client.post("/api/v1/hybrid-v2/overlay").status_code == 405
    assert client.post("/api/v1/hybrid-v2/overlay/HVBTEST").status_code == 405


def test_empty_db_gives_typed_503(tmp_path, monkeypatch) -> None:
    # Isolate storage so "empty" is deterministic — the real dev DB now
    # carries live R1/R2 payloads from collector runs. (Same pattern as
    # tests_support/fixtures.persist_overlay_lineage.)
    import trendforge_api.storage as storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "empty-hybrid.db")
    storage._INITIALIZED_DB_PATHS.clear()
    client = TestClient(app)
    response = client.get("/api/v1/hybrid-v2/overlay")
    assert response.status_code == 503
    code = response.json()["detail"]["code"]
    assert code.startswith("WAIT_HYBRID")


def test_c8_kelly_caps_and_zero_edge(tmp_path, monkeypatch) -> None:
    from trendforge_api.hybrid_v2.stages.s7_size import kelly_illustration

    persist_overlay_lineage(tmp_path, monkeypatch)
    batch = build_hybrid_v2_overlay(limit=5)
    assert all(0 <= row.kelly_illustration <= 0.02 for row in batch.rows)
    assert kelly_illustration(0.1) == 0.0
    assert kelly_illustration(0.99) <= 0.02


def test_c11_t1_label_without_width_has_no_fabricated_price(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    batch = build_hybrid_v2_overlay(limit=5)
    for row in batch.rows:
        if row.s5_label_state != "LABEL_ONLY":
            continue
        # Labels may reference the formula; they must not print a computed price.
        assert "width not on this proxy row" in row.s5_t1_label
        assert "width not on this proxy row" in row.s5_t2_label
        for token in row.s5_t1_label.replace("+0.382×R", "").split():
            token.strip("=+×R ")
            if token.replace(".", "").isdigit():
                raise AssertionError(f"fabricated price in T1 label: {row.s5_t1_label}")
