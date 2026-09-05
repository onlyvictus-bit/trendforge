"""File A R16/R18 PIT gate tests: auto-approve, session counts, blockers."""

from __future__ import annotations

from trendforge_api.selection.pit_gate import build_pit_gate


def _payload(rows: list[dict], run_id: str = "s8-run") -> dict:
    return {"runId": run_id, "rows": rows}


def _row(status: str) -> dict:
    return {"symbol": "X", "status": status}


def test_auto_approve_when_minima_pass() -> None:
    rows = [_row("WIN") for _ in range(15)] + [_row("LOSS") for _ in range(5)]
    gate = build_pit_gate(homework_payloads=[_payload(rows)])
    assert gate.auto_approve_guidance is True
    assert gate.guidance_status == "PIT_APPROVED_FOR_GUIDANCE"
    assert gate.performance_ui_allowed is True
    assert gate.horizon_complete_count == 20


def test_not_approved_when_insufficient_sessions() -> None:
    rows = [_row("WIN") for _ in range(3)] + [_row("CENSORED") for _ in range(2)]
    gate = build_pit_gate(homework_payloads=[_payload(rows)])
    assert gate.auto_approve_guidance is False
    assert gate.guidance_status == "PIT_NOT_APPROVED"


def test_win_rate_correct() -> None:
    rows = [_row("WIN") for _ in range(12)] + [_row("LOSS") for _ in range(8)]
    gate = build_pit_gate(homework_payloads=[_payload(rows)])
    assert gate.guidance_win_rate == 60.0


def test_win_rate_null_when_no_resolved() -> None:
    rows = [_row("CENSORED") for _ in range(10)]
    gate = build_pit_gate(homework_payloads=[_payload(rows)])
    assert gate.guidance_win_rate is None


def test_validation_status_never_fully_approved() -> None:
    rows = [_row("WIN") for _ in range(25)]
    gate = build_pit_gate(homework_payloads=[_payload(rows)])
    assert gate.validation_status != "PIT_APPROVED"


def test_blockers_listed_when_sessions_missing() -> None:
    rows = [_row("NO_FORWARD_SESSION") for _ in range(5)]
    gate = build_pit_gate(homework_payloads=[_payload(rows)])
    assert any("SESSION" in b for b in gate.blockers)


def test_empty_homework_gives_zero_gate() -> None:
    gate = build_pit_gate(homework_payloads=[])
    assert gate.labeled_row_count == 0
    assert gate.guidance_win_rate is None
    assert gate.auto_approve_guidance is False


def test_series_always_has_official_nse() -> None:
    gate = build_pit_gate(homework_payloads=[_payload([_row("WIN")])])
    assert any(s.get("kind") == "OFFICIAL_NSE" for s in gate.series)


def test_pit_gate_route_serves_from_store(tmp_path, monkeypatch) -> None:
    """Regression: the route must resolve its store helper (live 500 guard)."""
    from fastapi.testclient import TestClient

    from trendforge_api import storage
    from trendforge_api.main import app

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "pit-gate-route.db")
    storage._INITIALIZED_DB_PATHS.clear()
    client = TestClient(app)
    response = client.get("/api/v1/selection/pit-gate")
    assert response.status_code == 200
    assert response.json()["guidanceStatus"] == "PIT_NOT_APPROVED"
    assert client.post("/api/v1/selection/pit-gate").status_code == 405
