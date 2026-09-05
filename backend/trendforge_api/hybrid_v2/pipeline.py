"""Overlay pipeline: build_hybrid_v2_overlay() from the read-only spine."""

from __future__ import annotations

from datetime import date

from ..selection.contracts import SelectionState
from .as_lab.delivery import build_as_delivery_evidence
from .blocks.b1_regime import B1_WHY
from .blocks.b2_sector import B2_WHY
from .blocks.b3_cash import b3_z
from .blocks.b4_positioning import B4_WHY, b4_package
from .blocks.b5_location import b5_location_labels
from .contracts import (
    CEILING,
    MANDATORY_WARNING,
    S6_VEHICLE_STATUS,
    HybridOverlayBatchV1,
    HybridOverlayRowV1,
)
from .spine_adapter import load_hybrid_spine
from .stages.s0_integrity import assess_integrity
from .stages.s1_safety import assess_safety
from .stages.s4_probability import both_families
from .stages.s7_size import kelly_illustration


def _session_date(trading_date: str) -> date:
    try:
        return date.fromisoformat(trading_date)
    except ValueError:
        return date.today()


def build_hybrid_v2_overlay(*, limit: int = 40) -> HybridOverlayBatchV1:
    if limit < 1:
        raise ValueError("limit must be positive")
    spine = load_hybrid_spine()
    session = _session_date(spine.attention.trading_date)

    structure_rows = {
        row.symbol: row for row in (spine.structure.rows if spine.structure else ())
    }
    ca_by_symbol = {
        row.symbol.upper(): row for row in (spine.ca_join.rows if spine.ca_join else ())
    }
    instrument_by_candidate = {
        row.candidate_id: row.instrument_id
        for row in (spine.r4_pin.rows if spine.r4_pin else ())
    }

    ranked = sorted(spine.attention.rows, key=lambda item: item.display_order)[:limit]
    rows: list[HybridOverlayRowV1] = []
    for item in ranked:
        r5_row = structure_rows.get(item.symbol)
        ca_row = ca_by_symbol.get(item.symbol.upper())
        instrument_id = (
            instrument_by_candidate.get(item.candidate_id) or r5_row.instrument_id
            if r5_row is not None
            else instrument_by_candidate.get(item.candidate_id)
        )
        numeric_or_unknown_id = (
            item.symbol.isdigit()
            or ca_row is not None and ca_row.join_status == "UNKNOWN_ID"
        )
        effective_instrument_id = None if numeric_or_unknown_id else instrument_id
        ca_state = ca_row.ca_state if ca_row is not None else "MISSING"

        as_evidence = build_as_delivery_evidence(
            symbol=item.symbol,
            instrument_id=effective_instrument_id,
            ca_state=ca_state,
            session_date=session,
            decision_at=spine.decision_at,
        )

        integrity_status, integrity_codes = assess_integrity(
            structure_present=r5_row is not None, as_evidence=as_evidence
        )
        safety_status, safety_codes = assess_safety(item)
        del integrity_status, safety_status

        with_result, without_result = both_families(
            attention_row=item, r5_row=r5_row
        )[:2]

        b3 = b3_z(as_evidence)
        package = b4_package(r5_row)
        labels = b5_location_labels(r5_row)

        why_wait: list[str] = [
            "HYBRID_V2_OVERLAY_RESEARCH_CEILING",
            *integrity_codes,
            *safety_codes,
            *B1_WHY,
            *B2_WHY,
            *B4_WHY,
            "S6_UNKNOWN_NEEDS_R12",
        ]
        if as_evidence.why:
            why_wait.extend(as_evidence.why)

        research_state = (
            SelectionState.REJECT
            if item.public_state is SelectionState.REJECT
            else SelectionState.WAIT
        )
        rows.append(
            HybridOverlayRowV1(
                symbol=item.symbol,
                instrument_id=effective_instrument_id,
                r2_public_state=item.public_state,
                r5_structure_state=(
                    r5_row.structure_state if r5_row is not None else SelectionState.WAIT
                ),
                r14_ca_state=ca_state,
                research_state=research_state,
                display_order=item.display_order,
                b1_z=None,
                b2_z=None,
                b3_z=b3,
                b4_z=None,
                b5_z=None,
                with_s4s5=with_result,
                without_s4s5=without_result,
                s6_vehicle_status=S6_VEHICLE_STATUS,
                kelly_illustration=kelly_illustration(without_result.p_hat),
                as_delivery_z=as_evidence.delivery_z,
                as_status=as_evidence.status,
                b4_package=package,
                s5_label_state=labels["state"],
                s5_entry_label=labels["entry"],
                s5_t1_label=labels["t1"],
                s5_t2_label=labels["t2"],
                why_wait=tuple(dict.fromkeys(why_wait)),
                r1_bundle_hash=spine.bundle.bundle_hash,
                r2_run_hash=spine.attention.run_hash,
                r14_run_hash=spine.ca_join.run_hash if spine.ca_join else None,
                r5_run_hash=spine.structure.run_hash if spine.structure else None,
            )
        )

    return HybridOverlayBatchV1(
        trading_date=spine.attention.trading_date,
        decision_at=spine.decision_at,
        row_count=len(rows),
        rows=tuple(rows),
        warnings=(
            MANDATORY_WARNING,
            f"Calibration {CEILING}. AS delivery is the only real block; B1/B2/B4/B5 stay UNKNOWN.",
            "Kelly illustration only, capped at 2%. S5 levels are LABEL_ONLY.",
        ),
    )
