"""STA-006 public-state transition guard.

Structure substates inform the inspector. They do not write WATCH/WAIT/
CONFIRMED/REJECT. Activation-false cannot accept live CONFIRMED.
"""

from __future__ import annotations

from enum import StrEnum

from .contracts import SelectionState


class TransitionDecision(StrEnum):
    ACCEPTED = "ACCEPTED"
    DENIED_ILLEGAL_EDGE = "DENIED_ILLEGAL_EDGE"
    DENIED_ACTIVATION = "DENIED_ACTIVATION"
    DENIED_STRUCTURE = "DENIED_STRUCTURE"
    DENIED_TERMINAL_REJECT = "DENIED_TERMINAL_REJECT"


ALLOWED_SELECTION_EDGES: dict[SelectionState, frozenset[SelectionState]] = {
    SelectionState.WATCH: frozenset(
        {SelectionState.WATCH, SelectionState.WAIT, SelectionState.REJECT}
    ),
    SelectionState.WAIT: frozenset(
        {
            SelectionState.WATCH,
            SelectionState.WAIT,
            SelectionState.CONFIRMED,
            SelectionState.REJECT,
        }
    ),
    SelectionState.CONFIRMED: frozenset(
        {SelectionState.CONFIRMED, SelectionState.WAIT, SelectionState.REJECT}
    ),
    SelectionState.REJECT: frozenset(),
}


def is_legal_edge(prior: SelectionState, requested: SelectionState) -> bool:
    return requested in ALLOWED_SELECTION_EDGES[prior]


def apply_selection_transition(
    prior: SelectionState,
    requested: SelectionState,
    *,
    source_activation_ready: bool,
    closed_structure_accepted: bool,
) -> tuple[SelectionState, bool, TransitionDecision]:
    """Return (resulting_state, accepted, reason)."""
    if prior is SelectionState.REJECT and requested is not SelectionState.REJECT:
        return prior, False, TransitionDecision.DENIED_TERMINAL_REJECT
    if not is_legal_edge(prior, requested):
        if (
            prior is SelectionState.WATCH
            and requested is SelectionState.CONFIRMED
        ):
            return SelectionState.WAIT, False, TransitionDecision.DENIED_ILLEGAL_EDGE
        return prior, False, TransitionDecision.DENIED_ILLEGAL_EDGE
    if requested is SelectionState.CONFIRMED and not source_activation_ready:
        return SelectionState.WAIT, False, TransitionDecision.DENIED_ACTIVATION
    if requested is SelectionState.CONFIRMED and not closed_structure_accepted:
        return SelectionState.WAIT, False, TransitionDecision.DENIED_STRUCTURE
    return requested, True, TransitionDecision.ACCEPTED
