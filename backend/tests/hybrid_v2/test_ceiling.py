"""C1/C15/C2: the overlay ceiling is absolute."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api import storage
from trendforge_api.hybrid_v2.contracts import (
    MANDATORY_WARNING,
    S6_VEHICLE_STATUS,
    HybridOverlayBatchV1,
)
from trendforge_api.hybrid_v2.pipeline import build_hybrid_v2_overlay
from trendforge_api.hybrid_v2.tests_support.fixtures import (
    DECISION_AT,
    TRADING_DATE,
    persist_overlay_lineage,
)
from trendforge_api.main import app


def _batch(tmp_path, monkeypatch, **kwargs):
    persist_overlay_lineage(tmp_path, monkeypatch, **kwargs)
    return build_hybrid_v2_overlay(limit=5)


def test_c1_batch_cannot_confirm_or_trade(tmp_path, monkeypatch) -> None:
    batch = _batch(tmp_path, monkeypatch)
    assert batch.can_unlock_confirmed is False
    assert batch.executable is False
    assert batch.source_activation_ready is False
    assert batch.calibration == "RESEARCH_PROXY_NOT_CALIBRATED"
    assert all(row.research_state.value != "CONFIRMED" for row in batch.rows)
    assert MANDATORY_WARNING in batch.warnings


def test_c1_tampering_with_ceiling_raises(tmp_path, monkeypatch) -> None:
    batch = _batch(tmp_path, monkeypatch)
    payload = batch.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError):
        HybridOverlayBatchV1.model_validate({**payload, "canUnlockConfirmed": True})
    with pytest.raises(ValidationError):
        HybridOverlayBatchV1.model_validate({**payload, "sourceActivationReady": True})
    rows = [dict(item) for item in payload["rows"]]
    rows[0]["researchState"] = "CONFIRMED"
    with pytest.raises(ValidationError):
        HybridOverlayBatchV1.model_validate({**payload, "rows": rows})
    with pytest.raises(ValidationError):
        HybridOverlayBatchV1.model_validate(
            {**payload, "warnings": ("something else",)}
        )


def test_c1_row_s6_status_is_locked(tmp_path, monkeypatch) -> None:
    row = _batch(tmp_path, monkeypatch).rows[0]
    assert row.s6_vehicle_status == S6_VEHICLE_STATUS
    payload = row.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError):
        HybridOverlayBatchV1(
            trading_date=TRADING_DATE.isoformat(),
            decision_at=DECISION_AT,
            row_count=1,
            warnings=(MANDATORY_WARNING,),
            rows=[{**payload, "s6VehicleStatus": "LONG_CALL_SPREAD"}],
        )


def test_c15_source_activation_stays_false_in_api(tmp_path, monkeypatch) -> None:
    _batch(tmp_path, monkeypatch)
    client = TestClient(app)
    response = client.get("/api/v1/hybrid-v2/overlay?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["sourceActivationReady"] is False
    assert body["canUnlockConfirmed"] is False
    assert body["executable"] is False


def test_c2_post_overlay_is_405(tmp_path, monkeypatch) -> None:
    _batch(tmp_path, monkeypatch)
    client = TestClient(app)
    assert client.post("/api/v1/hybrid-v2/overlay").status_code == 405
