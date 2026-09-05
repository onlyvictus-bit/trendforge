"""Research A/B of hybrid S4/S5 formulas. Not live CONFIRMED. Not size.

WITH (original v3 compression): B1–B5 mixed into one p̂; wall also used as entry.
WITHOUT (adopted split): p̂ from B1–B3 proxy only; B4 package; B5 location only.

Numbers are RESEARCH_PROXY_NOT_CALIBRATED. They exist so future days can be
compared; they cannot authorize qty or CONFIRMED.
"""

from __future__ import annotations

from math import exp
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .attention_order import latest_attention_order
from .contracts import SelectionState
from .inventory_source_bundle import latest_inventory_source_bundle
from .r5_live import R5StructureRowV1, latest_r5_structure_batch

SCHEMA_VERSION = "trendforge.s4s5-compare.v1"
FORMULA_VERSION = "proxy-1.0.0"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)
ILLUSTRATION_B = 1.2
ILLUSTRATION_Q = 0.5
ILLUSTRATION_C = 0.08
ILLUSTRATION_SE = 0.05
BIAS = -0.4
SIDE_WEIGHT = 1.2
BOOK_WEIGHT = 1.2
WITH_FORMULA = "p̂ = σ(-0.4 + 1.2·z_side + 1.2·z_book)  [original S4: B4/B5 mixed into probability]"
WITHOUT_FORMULA = "p̂ = σ(-0.4 + 1.2·z_side)  [split: B4=package, B5=location only]"
P_MIN_FORMULA = "p_min = (1+c)/(1+b) = 1.08/2.2"

ViewMode = Literal["with", "without", "both"]


def _sigmoid(value: float) -> float:
    if value >= 20:
        return 1.0
    if value <= -20:
        return 0.0
    return 1.0 / (1.0 + exp(-value))


def _p_min() -> float:
    return (1.0 + ILLUSTRATION_C) / (1.0 + ILLUSTRATION_B)


def _kelly(p_hat: float) -> float:
    p_used = max(0.0, p_hat - ILLUSTRATION_SE)
    edge = p_used * ILLUSTRATION_B - ILLUSTRATION_Q
    raw = 0.25 * max(0.0, edge / ILLUSTRATION_B)
    return min(0.02, raw)


def _side_z(*, state: SelectionState, priority: float | None) -> float:
    if priority is not None:
        return float(priority)
    if state is SelectionState.WATCH:
        return 0.55
    if state is SelectionState.WAIT:
        return 0.25
    return 0.0


def _book_z(row: R5StructureRowV1 | None) -> float:
    if row is None:
        return 0.0
    setups = set(row.detected_setups)
    score = 0.12 * len(setups)
    metrics = row.metrics
    if metrics is not None and metrics.accepted:
        score += 0.22
    if (
        metrics is not None
        and metrics.relative_volume is not None
        and metrics.relative_volume >= 1.5
    ):
        score += 0.18
    if "NR7" in setups or (metrics is not None and metrics.narrow_range):
        score += 0.08
    return min(1.0, score)


def _package(row: R5StructureRowV1 | None) -> str:
    if row is None:
        return "UNKNOWN"
    if row.r2_public_state is SelectionState.REJECT:
        return "CONFLICT"
    if row.detected_setups:
        return "SUPPORT"
    if row.history_count < 8:
        return "UNKNOWN"
    return "WEAKEN"


class S4S5FormulaResultV1(BaseModel):
    model_config = MODEL_CONFIG

    formula: str
    p_hat: float = Field(ge=0, le=1)
    p_min: float = Field(ge=0, le=1)
    would_pass_p_min: bool
    kelly_illustration: float = Field(ge=0, le=0.02)
    entry_label: str
    entry_level: float | None = None
    t1_label: str
    t2_label: str
    package: str | None = None
    logit: float
    notes: tuple[str, ...] = ()


class S4S5CompareRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    r2_public_state: SelectionState
    direction: str
    display_order: int
    side_z: float
    book_z: float
    with_s4s5: S4S5FormulaResultV1
    without_s4s5: S4S5FormulaResultV1
    p_hat_inflation: float
    research_state: SelectionState = SelectionState.WAIT


class S4S5CompareBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    formula_version: str = FORMULA_VERSION
    calibration: str = "RESEARCH_PROXY_NOT_CALIBRATED"
    can_unlock_confirmed: bool = False
    executable: bool = False
    with_formula: str = WITH_FORMULA
    without_formula: str = WITHOUT_FORMULA
    p_min_formula: str = P_MIN_FORMULA
    p_min: float
    illustration_b: float = ILLUSTRATION_B
    illustration_c: float = ILLUSTRATION_C
    row_count: int = Field(ge=0)
    with_pass_count: int = Field(ge=0)
    without_pass_count: int = Field(ge=0)
    rows: tuple[S4S5CompareRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def research_ceiling(self) -> "S4S5CompareBatchV1":
        if self.can_unlock_confirmed or self.executable:
            raise ValueError("S4/S5 compare cannot trade or confirm")
        if any(row.research_state is SelectionState.CONFIRMED for row in self.rows):
            raise ValueError("S4/S5 compare rows cannot be CONFIRMED")
        return self


def _entry_level(row: R5StructureRowV1 | None) -> float | None:
    if row is None or row.metrics is None:
        return None
    return row.metrics.reference_level


def build_s4s5_compare(*, limit: int = 40) -> S4S5CompareBatchV1:
    if limit < 1:
        raise ValueError("limit must be positive")
    attention = latest_attention_order()
    structure = latest_r5_structure_batch()
    bundle = latest_inventory_source_bundle()
    if attention is None:
        raise ValueError("WAIT_S4S5_R2_NOT_READY")
    if (
        bundle is not None
        and (
            attention.r1_bundle_id != bundle.bundle_id
            or attention.r1_bundle_hash != bundle.bundle_hash
        )
    ):
        raise ValueError("WAIT_S4S5_LINEAGE_MISMATCH")
    by_symbol: dict[str, R5StructureRowV1] = {}
    if structure is not None:
        if (
            structure.r2_run_id != attention.run_id
            or structure.r2_run_hash != attention.run_hash
        ):
            raise ValueError("WAIT_S4S5_LINEAGE_MISMATCH")
        by_symbol = {row.symbol: row for row in structure.rows}
    p_min = _p_min()
    ranked = sorted(attention.rows, key=lambda item: item.display_order)[:limit]
    rows: list[S4S5CompareRowV1] = []
    for item in ranked:
        r5 = by_symbol.get(item.symbol)
        side = _side_z(state=item.public_state, priority=item.attention_priority)
        book = _book_z(r5)
        logit_with = BIAS + SIDE_WEIGHT * side + BOOK_WEIGHT * book
        logit_without = BIAS + SIDE_WEIGHT * side
        p_with = round(_sigmoid(logit_with), 4)
        p_without = round(_sigmoid(logit_without), 4)
        level = _entry_level(r5)
        t1_label = (
            "T1=entry+0.382×R (R=prior_range; width not on this proxy row)"
        )
        t2_label = (
            "T2=entry+0.618×R (R=prior_range; width not on this proxy row)"
        )
        with_result = S4S5FormulaResultV1(
            formula=WITH_FORMULA,
            p_hat=p_with,
            p_min=round(p_min, 4),
            would_pass_p_min=p_with >= p_min,
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
            would_pass_p_min=p_without >= p_min,
            kelly_illustration=round(_kelly(p_without), 6),
            entry_label="structure box only (wall=liquidity)",
            entry_level=level,
            t1_label=t1_label,
            t2_label=t2_label,
            package=_package(r5),
            logit=round(logit_without, 4),
            notes=(
                "p̂ from B1–B3 proxy only.",
                "B4 is package; B5 is location.",
            ),
        )
        rows.append(
            S4S5CompareRowV1(
                symbol=item.symbol,
                r2_public_state=item.public_state,
                direction=item.evidence_direction.value,
                display_order=item.display_order,
                side_z=round(side, 4),
                book_z=round(book, 4),
                with_s4s5=with_result,
                without_s4s5=without_result,
                p_hat_inflation=round(p_with - p_without, 4),
            )
        )
    return S4S5CompareBatchV1(
        p_min=round(p_min, 4),
        row_count=len(rows),
        with_pass_count=sum(row.with_s4s5.would_pass_p_min for row in rows),
        without_pass_count=sum(row.without_s4s5.would_pass_p_min for row in rows),
        rows=tuple(rows),
        warnings=(
            "RESEARCH_PROXY_NOT_CALIBRATED. Not live p̂. Not size. Not CONFIRMED.",
            "WITH mixes book into probability (original v3). WITHOUT uses the split.",
            "Compare both for paper days, then pick one formula family.",
        ),
    )
