"""TF-01 adversarial tests for typed mandatory-gate propagation."""

from __future__ import annotations

from trendforge_api.selection.contracts import (
    EvidenceDirection,
    GateOutcome,
    SelectionGateResult,
    SelectionState,
)
from trendforge_api.selection.s6_family_resolution import (
    S6FamilyStrengthV1,
    S6ResolutionRowV1,
)
from trendforge_api.selection.s7_state_gates import classify_row


def _row(*, inherited_gates: tuple[SelectionGateResult, ...] = ()) -> S6ResolutionRowV1:
    families = {
        "STRUCTURE": S6FamilyStrengthV1(support=0.9, oppose=0.0, weight=0.5),
        "PARTICIPATION": S6FamilyStrengthV1(support=0.9, oppose=0.0, weight=0.5),
        "EVENT_AND_SPONSOR": S6FamilyStrengthV1(support=0.0, oppose=0.0, weight=0.0),
    }
    return S6ResolutionRowV1(
        candidate_id="c-TF01",
        symbol="TF01",
        r2_public_state=SelectionState.WATCH,
        resolution_state=SelectionState.WAIT,
        evidence_direction=EvidenceDirection.BULLISH,
        display_order=1,
        families=families,
        conflict=False,
        evidence_strength=0.9,
        inherited_gates=inherited_gates,
    )


def _gate(code: str, outcome: GateOutcome, *, required: bool = True, scope: str = "PIPELINE_MANDATORY") -> SelectionGateResult:
    return SelectionGateResult(
        code=code,
        outcome=outcome,
        required=required,
        blocks_confirmed=(required and outcome is not GateOutcome.PASS),
        reason=f"TF-01 fixture {code}",
        scope=scope,
    )


def _classify(row: S6ResolutionRowV1):
    return classify_row(
        row6=row,
        next_trigger=None,
        invalidation=None,
        has_structure_tags=True,
        ca_break=False,
        blackout_known_clear=True,
        rs_ok=None,
        weather_unknown=False,
        activation_ready=True,
    )


def test_required_wait_survives_s6_to_s7_structurally() -> None:
    row = _row(inherited_gates=(_gate("WAIT_REQUIRED_UPSTREAM", GateOutcome.WAIT),))
    state, why, draft = _classify(row)
    assert state is SelectionState.WAIT
    assert draft is False
    assert "WAIT_REQUIRED_UPSTREAM" in why


def test_required_unknown_survives_s6_to_s7_structurally() -> None:
    row = _row(inherited_gates=(_gate("UNKNOWN_REQUIRED_UPSTREAM", GateOutcome.UNKNOWN),))
    state, why, draft = _classify(row)
    assert state is SelectionState.WAIT
    assert draft is False
    assert "UNKNOWN_REQUIRED_UPSTREAM" in why


def test_required_reject_survives_s6_to_s7_structurally() -> None:
    row = _row(inherited_gates=(_gate("REJECT_REQUIRED_UPSTREAM", GateOutcome.REJECT),))
    state, why, draft = _classify(row)
    assert state is SelectionState.REJECT
    assert draft is False
    assert "REJECT_REQUIRED_UPSTREAM" in why


def test_optional_gate_does_not_freeze_s7() -> None:
    row = _row(
        inherited_gates=(
            _gate("OPTIONAL_CONTEXT_UNKNOWN", GateOutcome.UNKNOWN, required=False),
        )
    )
    state, _, draft = _classify(row)
    assert state is SelectionState.CONFIRMED
    assert draft is True


def test_stage_local_gate_does_not_become_permanent_s7_blocker() -> None:
    row = _row(
        inherited_gates=(
            _gate(
                "WAIT_SOURCE_ACTIVATION",
                GateOutcome.WAIT,
                scope="STAGE_LOCAL",
            ),
        )
    )
    state, _, draft = _classify(row)
    assert state is SelectionState.CONFIRMED
    assert draft is True
