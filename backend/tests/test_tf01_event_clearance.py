"""TF-01 adversarial tests for scoped semantic event clearance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from trendforge_api.macro_event_context import (
    EventClearanceEvidence,
    EventClearanceOutcome,
    EventClearanceResult,
    evaluate_event_clearance,
)

DECISION_AT = datetime(2026, 8, 14, 11, 30, tzinfo=UTC)


def _evidence(
    *,
    evidence_id: str = "evt-evidence-1",
    instrument_id: str = "ins-INFY",
    symbol: str = "INFY",
    outcome: EventClearanceOutcome = EventClearanceOutcome.CLEAR,
    semantic_coverage_complete: bool = True,
    assessed_at: datetime = DECISION_AT - timedelta(minutes=5),
    valid_until: datetime = DECISION_AT + timedelta(hours=2),
    source_key: str = "nse_structured_announcements",
    parser_version: str | None = "event-parser-1.0.0",
    content_hash: str | None = "a" * 64,
    event_id: str | None = None,
) -> EventClearanceEvidence:
    return EventClearanceEvidence(
        evidence_id=evidence_id,
        source_key=source_key,
        instrument_id=instrument_id,
        symbol=symbol,
        profile_id="PRF-003-SWING-EOD",
        profile_version="1.0.0",
        event_window_start=DECISION_AT - timedelta(hours=6),
        event_window_end=DECISION_AT + timedelta(hours=6),
        assessed_at=assessed_at,
        valid_until=valid_until,
        semantic_coverage_complete=semantic_coverage_complete,
        source_outcome=outcome,
        parser_version=parser_version,
        content_hash=content_hash,
        event_id=event_id,
    )


def _evaluate(*evidence: EventClearanceEvidence):
    return evaluate_event_clearance(
        instrument_id="ins-INFY",
        symbol="INFY",
        profile_id="PRF-003-SWING-EOD",
        profile_version="1.0.0",
        decision_at=DECISION_AT,
        evidence=evidence,
    )


def test_expired_clearance_is_unknown() -> None:
    result = _evaluate(_evidence(valid_until=DECISION_AT - timedelta(seconds=1)))
    assert result.outcome is EventClearanceOutcome.UNKNOWN
    assert "WAIT_EVENT_CLEARANCE_EXPIRED" in result.reason_codes


def test_incomplete_or_metadata_only_coverage_is_unknown() -> None:
    incomplete = _evaluate(_evidence(semantic_coverage_complete=False))
    metadata_only = _evaluate(_evidence(parser_version=None, content_hash=None))
    assert incomplete.outcome is EventClearanceOutcome.UNKNOWN
    assert metadata_only.outcome is EventClearanceOutcome.UNKNOWN


def test_blocking_event_is_blocked() -> None:
    result = _evaluate(
        _evidence(
            outcome=EventClearanceOutcome.BLOCKED,
            event_id="INFY_RESULTS_2026Q2",
        )
    )
    assert result.outcome is EventClearanceOutcome.BLOCKED
    assert result.blocking_event_ids == ("INFY_RESULTS_2026Q2",)


def test_complete_scoped_clear_evidence_is_clear() -> None:
    result = _evaluate(_evidence())
    assert result.outcome is EventClearanceOutcome.CLEAR
    assert result.semantic_coverage_complete is True
    assert result.can_satisfy_mandatory_gate is True


def test_other_symbol_evidence_cannot_clear_this_instrument() -> None:
    result = _evaluate(
        _evidence(
            instrument_id="ins-TCS",
            symbol="TCS",
        )
    )
    assert result.outcome is EventClearanceOutcome.UNKNOWN
    assert result.can_satisfy_mandatory_gate is False
    assert "WAIT_EVENT_CLEARANCE_NO_SCOPED_EVIDENCE" in result.reason_codes


def test_other_profile_evidence_cannot_clear_this_strategy() -> None:
    evidence = _evidence().model_copy(
        update={
            "profile_id": "PRF-ALT-REVERSAL",
            "profile_version": "2.0.0",
        }
    )
    result = _evaluate(evidence)
    assert result.outcome is EventClearanceOutcome.UNKNOWN
    assert result.can_satisfy_mandatory_gate is False
    assert "WAIT_EVENT_CLEARANCE_NO_SCOPED_EVIDENCE" in result.reason_codes


def test_contradictory_sources_never_silently_clear() -> None:
    result = _evaluate(
        _evidence(evidence_id="clear", source_key="nse_structured_announcements"),
        _evidence(
            evidence_id="blocked",
            source_key="bse_xbrl_announcements",
            outcome=EventClearanceOutcome.BLOCKED,
            event_id="INFY_RESULTS_CONFLICT",
        ),
    )
    assert result.outcome is EventClearanceOutcome.UNKNOWN
    assert result.can_satisfy_mandatory_gate is False
    assert "WAIT_EVENT_CLEARANCE_CONTRADICTORY" in result.reason_codes


def test_clear_result_cannot_self_certify_without_temporal_lineage() -> None:
    with pytest.raises(ValidationError, match="lineage-backed CLEAR"):
        EventClearanceResult(
            instrument_id="ins-INFY",
            symbol="INFY",
            profile_id="PRF-003-SWING-EOD",
            profile_version="1.0.0",
            decision_at=DECISION_AT,
            outcome=EventClearanceOutcome.CLEAR,
            evidence_ids=("claimed-clear",),
            semantic_coverage_complete=True,
            can_satisfy_mandatory_gate=True,
        )
