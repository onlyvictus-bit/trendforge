from __future__ import annotations

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.lifecycle_fixtures import build_lifecycle_fixture_inputs
from trendforge_api.main import app


def test_general_alert_persists_reason_risk_and_acknowledgement(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "alerts.db")
    client = TestClient(app)
    response = client.post(
        "/api/alerts",
        json={
            "alertType": "SOURCE_STALE",
            "severity": "WARN",
            "symbol": "RELIANCE",
            "state": "WAIT_DATA_WEAK",
            "reason": "NSE source is older than its freshness contract.",
            "risk": {"affectedGate": "G00_DATA_HEALTHY"},
        },
    )
    assert response.status_code == 200
    alert = response.json()
    assert alert["acknowledged"] is False
    assert alert["risk"]["affectedGate"] == "G00_DATA_HEALTHY"
    acknowledged = client.put(f"/api/alerts/{alert['id']}/acknowledge")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged"] is True


def test_manual_journal_records_and_updates_outcome(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "journal.db")
    client = TestClient(app)
    created = client.post(
        "/api/journal",
        json={
            "symbol": "INFY",
            "mode": "INTRADAY",
            "direction": "LONG",
            "decisionState": "READY",
            "setup": "ORB",
            "quantity": 10,
            "entryPrice": 1500,
            "stopPrice": 1480,
            "openedAt": "2026-07-10T10:00:00+05:30",
            "notes": "Manual research entry only.",
        },
    )
    assert created.status_code == 200
    journal = created.json()
    assert journal["outcomeState"] == "OPEN"
    updated = client.put(
        f"/api/journal/{journal['id']}/outcome",
        json={
            "outcomeState": "WIN",
            "exitPrice": 1540,
            "closedAt": "2026-07-10T14:00:00+05:30",
            "pnl": 400,
            "rMultiple": 2,
            "notes": "Target reached.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["outcomeState"] == "WIN"
    assert updated.json()["rMultiple"] == 2
    assert len(client.get("/api/journal").json()) == 1


def test_journal_rejects_invalid_risk_geometry_and_broker_fields(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "journal-invalid.db")
    payload = {
        "symbol": "INFY",
        "mode": "INTRADAY",
        "direction": "LONG",
        "decisionState": "READY",
        "setup": "ORB",
        "quantity": 10,
        "entryPrice": 1500,
        "stopPrice": 1520,
        "openedAt": "2026-07-10T10:00:00+05:30",
        "brokerOrderId": "FORBIDDEN",
    }
    response = TestClient(app).post("/api/journal", json=payload)
    assert response.status_code == 422


def test_lifecycle_terminal_event_creates_reasoned_general_alert(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "lifecycle-alert.db")
    payload = build_lifecycle_fixture_inputs()["LOSS"]
    client = TestClient(app)
    response = client.post(
        "/api/harmonic/lifecycle/evaluate",
        params={"persist": True},
        json=payload.model_dump(mode="json", by_alias=True),
    )
    assert response.status_code == 200
    alerts = client.get("/api/alerts", params={"symbol": "TFLIFE"}).json()
    assert len(alerts) == 1
    assert alerts[0]["alertType"] == "HARMONIC_LOSS"
    assert alerts[0]["reason"]
    assert alerts[0]["risk"]["invalidationPrice"] == 95
