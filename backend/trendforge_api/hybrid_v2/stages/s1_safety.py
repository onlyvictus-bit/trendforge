"""S1 safety stage. Copy of R2 restriction / REJECT as veto; never invents ASM."""

from __future__ import annotations

from ...selection.attention_order import AttentionRowV1
from ...selection.contracts import SelectionState


def assess_safety(attention_row: AttentionRowV1) -> tuple[str, tuple[str, ...]]:
    codes: list[str] = []
    if attention_row.public_state is SelectionState.REJECT:
        codes.append("R2_PUBLIC_REJECT")
    if attention_row.restriction_state and attention_row.restriction_state != "READY":
        codes.append(f"R2_RESTRICTION_{attention_row.restriction_state}")
    status = "REJECT" if attention_row.public_state is SelectionState.REJECT else (
        "WAIT" if codes else "OK"
    )
    return status, tuple(codes)
