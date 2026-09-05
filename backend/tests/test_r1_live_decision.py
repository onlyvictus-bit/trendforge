from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api.main import app
from trendforge_api.selection.contracts import (
    DataMode,
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    SelectionCandidate,
    SelectionState,
    StateCeiling,
)
from trendforge_api.selection.live_run import build_live_selection_run
from trendforge_api.selection.series_layers import (
    SeriesKind,
    open_adjusted_series,
    raw_series,
)
from trendforge_api.selection.transitions import (
    TransitionDecision,
    apply_selection_transition,
    is_legal_edge,
)
from trendforge_api.source_contracts import SourceRole


AS_OF = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)


def test_sta006_denies_watch_to_confirmed() -> None:
    assert is_legal_edge(SelectionState.WATCH, SelectionState.CONFIRMED) is False
    resulting, accepted, reason = apply_selection_transition(
        SelectionState.WATCH,
        SelectionState.CONFIRMED,
        source_activation_ready=True,
        closed_structure_accepted=True,
    )
    assert accepted is False
    assert resulting is SelectionState.WAIT
    assert reason is TransitionDecision.DENIED_ILLEGAL_EDGE


def test_sta006_activation_false_blocks_live_confirmed() -> None:
    resulting, accepted, reason = apply_selection_transition(
        SelectionState.WAIT,
        SelectionState.CONFIRMED,
        source_activation_ready=False,
        closed_structure_accepted=True,
    )
    assert accepted is False
    assert resulting is SelectionState.WAIT
    assert reason is TransitionDecision.DENIED_ACTIVATION


def test_cross020_adjustment_does_not_mutate_raw() -> None:
    raw = raw_series(instrument_key="NSE:RELIANCE", artifact_hash="a" * 64)
    adjusted = open_adjusted_series(raw, adjustment_event_id="CA-SPLIT-1")
    assert raw.kind is SeriesKind.RAW
    assert adjusted.kind is SeriesKind.ADJUSTED
    assert adjusted.series_id != raw.series_id
    assert adjusted.source_artifact_hash == raw.source_artifact_hash
    with pytest.raises(ValueError, match="RAW"):
        open_adjusted_series(adjusted, adjustment_event_id="CA-SPLIT-2")


def test_r1_dto_rejects_quantity_fields() -> None:
    with pytest.raises(ValidationError, match="FUS-008"):
        SelectionCandidate.model_validate(
            {
                "candidateId": "c1",
                "runId": "r1",
                "instrument": {
                    "instrumentId": "i1",
                    "exchange": "NSE",
                    "segment": "EQ",
                    "symbol": "TEST",
                },
                "market": "NSE",
                "profileId": "p",
                "profileVersion": "1",
                "timeframe": "1d",
                "state": "WAIT",
                "stateCeiling": "WAIT",
                "evidenceDirection": "UNKNOWN",
                "discoveryReason": "x",
                "topReason": "x",
                "nextConfirmation": "x",
                "invalidationCondition": "x",
                "context": "x",
                "freshness": "UNKNOWN",
                "completeness": 0,
                "whatChanged": "NO_BASELINE",
                "evidenceStrength": 0,
                "dataMode": "EOD_RESEARCH",
                "quantity": 0,
            }
        )


def test_confirming_claim_requires_pit_envelope() -> None:
    with pytest.raises(ValidationError, match="PIT envelope"):
        EvidenceClaim.create(
            feature_id="FTR-006",
            feature_version="1.0.0",
            family=EvidenceFamily.STRUCTURE,
            correlation_group="CG_PRICE_STRUCTURE",
            direction=EvidenceDirection.BULLISH,
            strength_before_caps=0.5,
            source_fact_ids=("fact-1",),
            authority=SourceRole.OFFICIAL_GATE,
            available_at=AS_OF,
            state_ceiling=StateCeiling.CONFIRMED,
            can_support_confirmed=True,
            explanation="Missing envelope must fail.",
        )


def test_live_selection_run_never_confirms() -> None:
    batch = build_live_selection_run(symbols=("RELIANCE", "TATASTEEL"), as_of=AS_OF)
    assert batch.milestone == "R1-LIVE"
    assert batch.source_activation_ready is False
    assert batch.live_confirmed_count == 0
    assert batch.h1a0_passed == batch.h1a0_total
    assert all(item.state is SelectionState.WAIT for item in batch.candidates)
    assert all(item.executable is False for item in batch.candidates)
    dumped = batch.model_dump()
    assert "quantity" not in dumped
    assert all("quantity" not in item.model_dump() for item in batch.candidates)


def test_live_selection_api_is_research_only() -> None:
    response = TestClient(app).get("/api/v1/selection/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schemaVersion"] == "trendforge.legacy-selection-live.v1"
    assert payload["legacyProjection"] is True
    assert payload["acceptanceCeiling"] == "NO_LIVE_CONFIRMED"
    assert payload["liveConfirmedCount"] == 0
    assert payload["sourceActivationReady"] is False
    assert "quantity" not in payload


def test_live_selection_can_persist_and_compare(tmp_path, monkeypatch) -> None:
    from datetime import timedelta

    from trendforge_api import storage
    from trendforge_api.selection.store import (
        apply_comparable_diff,
        latest_live_selection_batch,
        persist_live_selection_batch,
    )

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "selection.db")
    storage._INITIALIZED_DB_PATHS.clear()
    first = persist_live_selection_batch(
        build_live_selection_run(symbols=("RELIANCE",), as_of=AS_OF)
    )
    assert first.persisted is True
    assert first.storage == "STORED"
    loaded = latest_live_selection_batch()
    assert loaded is not None
    assert loaded.run.run_id == first.run.run_id
    assert loaded.candidates[0].state is SelectionState.WAIT
    second = persist_live_selection_batch(
        apply_comparable_diff(
            build_live_selection_run(
                symbols=("RELIANCE",), as_of=AS_OF + timedelta(minutes=1)
            ),
            loaded,
        )
    )
    assert second.run.run_id != first.run.run_id
    assert second.candidates[0].comparable_baseline == "COMPARED"
    assert second.candidates[0].comparable_run_id == first.run.run_id
    assert "VERSION" in second.candidates[0].change_kinds
    assert second.live_confirmed_count == 0
