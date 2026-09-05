"""S4 probability stage: WITH and WITHOUT families side by side.

Reuses the exact `s4s5_compare` helpers and rounding so the overlay numbers
match `GET /api/v1/selection/s4s5-compare` within 1e-6. No third formula.
"""

from __future__ import annotations

from ...selection.r5_live import R5StructureRowV1
from ...selection.attention_order import AttentionRowV1
from ...selection.contracts import SelectionState
from ...selection.s4s5_compare import (
    BIAS,
    SIDE_WEIGHT,
    S4S5FormulaResultV1,
    WITHOUT_FORMULA,
    WITH_FORMULA,
    _book_z,
    _kelly,
    _p_min,
    _side_z,
    _sigmoid,
)


def side_z(*, state: SelectionState, priority: float | None) -> float:
    return _side_z(state=state, priority=priority)


def book_z(row: R5StructureRowV1 | None) -> float:
    return _book_z(row)


def both_families(
    *,
    attention_row: AttentionRowV1,
    r5_row: R5StructureRowV1 | None,
) -> tuple[S4S5FormulaResultV1, S4S5FormulaResultV1, float, float, float]:
    """Return (with_result, without_result, side, book, p_min)."""
    side = _side_z(
        state=attention_row.public_state, priority=attention_row.attention_priority
    )
    book = _book_z(r5_row)
    logit_with = BIAS + SIDE_WEIGHT * side + 1.2 * book
    logit_without = BIAS + SIDE_WEIGHT * side
    p_min = _p_min()
    # Round first, then gate — identical to build_s4s5_compare so PASS/FAIL
    # chips can never disagree at the rounding boundary.
    p_with = round(_sigmoid(logit_with), 4)
    p_without = round(_sigmoid(logit_without), 4)
    level = r5_row.metrics.reference_level if r5_row is not None and r5_row.metrics else None
    t1_label = "T1=entry+0.382×R (R=prior_range; width not on this proxy row)"
    t2_label = "T2=entry+0.618×R (R=prior_range; width not on this proxy row)"
    from ...selection.s4s5_compare import _package

    with_result = S4S5FormulaResultV1(
        formula=WITH_FORMULA,
        p_hat=p_with,
        p_min=round(p_min, 4),
        would_pass_p_min=p_with >= round(p_min, 4),
        kelly_illustration=round(_kelly(p_with), 6),
        entry_label="POC∩WALL∩PRZ (compressed; wall votes)",
        entry_level=level,
        t1_label=t1_label,
        t2_label=t2_label,
        package=None,
        logit=round(logit_with, 4),
        notes=(
            "B4+B5 mixed into p̂ (original v3 S4).",
            "Same OI/structure book also used as entry.",
        ),
    )
    without_result = S4S5FormulaResultV1(
        formula=WITHOUT_FORMULA,
        p_hat=p_without,
        p_min=round(p_min, 4),
        would_pass_p_min=p_without >= round(p_min, 4),
        kelly_illustration=round(_kelly(p_without), 6),
        entry_label="structure box only (wall=liquidity)",
        entry_level=level,
        t1_label=t1_label,
        t2_label=t2_label,
        package=_package(r5_row),
        logit=round(logit_without, 4),
        notes=(
            "p̂ from B1–B3 proxy only.",
            "B4 is package; B5 is location.",
        ),
    )
    return with_result, without_result, round(side, 4), round(book, 4), p_min
