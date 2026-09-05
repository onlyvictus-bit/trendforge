from __future__ import annotations

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.harmonic_lifecycle import evaluate_harmonic_lifecycle
from trendforge_api.lifecycle_fixtures import (
    build_lifecycle_fixture_inputs,
    load_lifecycle_fixture_events,
)
from trendforge_api.main import app


def test_deterministic_lifecycle_fixtures_cover_every_required_state() -> None:
    results = {
        name: evaluate_harmonic_lifecycle(payload)
        for name, payload in build_lifecycle_fixture_inputs().items()
    }
    assert {result.state for result in results.values()} == {
        "FORMING",
        "COMPLETE",
        "TRIGGERED",
        "INVALIDATED",
        "WIN_T1",
        "WIN_T2",
        "WIN_T3",
        "LOSS",
        "EXPIRED",
    }
    assert [event.state for event in results["WIN_T3"].transitions][-1] == "WIN_T3"


def test_same_bar_target_and_stop_is_conservative_loss() -> None:
    payload = build_lifecycle_fixture_inputs()["WIN_T1"].model_copy(deep=True)
    payload.bars[-1].low = 94
    result = evaluate_harmonic_lifecycle(payload)
    assert result.state == "LOSS"
    assert "same bar" in result.reason.lower()


def test_lifecycle_events_persist_once_and_remain_ordered(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "lifecycle.db")
    first = load_lifecycle_fixture_events()
    second = load_lifecycle_fixture_events()
    assert first["savedEvents"] > 0
    assert second["savedEvents"] == 0
    rows = storage.list_harmonic_lifecycle_events(pattern_key="TF_LIFE_WIN_T3")
    assert rows
    assert [row["sequence"] for row in rows] == sorted(row["sequence"] for row in rows)
    assert rows[-1]["state"] == "WIN_T3"


def test_lifecycle_api_evaluates_and_persists(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "lifecycle-api.db")
    payload = build_lifecycle_fixture_inputs()["LOSS"]
    response = TestClient(app).post(
        "/api/harmonic/lifecycle/evaluate",
        params={"persist": True},
        json=payload.model_dump(mode="json", by_alias=True),
    )
    assert response.status_code == 200
    result = response.json()
    assert result["state"] == "LOSS"
    events = TestClient(app).get(
        "/api/harmonic/lifecycle/events", params={"patternKey": payload.pattern_key}
    )
    assert events.status_code == 200
    assert events.json()[-1]["state"] == "LOSS"
