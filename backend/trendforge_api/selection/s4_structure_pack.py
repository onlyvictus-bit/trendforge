"""File A S4 (SEL-005): minimal closed-bar structure pack over live R5 WAIT rows.

This stage EXTENDS the persisted R5 batch into a display pack. It never
re-scans bars, never re-runs a structure engine, and never upgrades state:

- Every claim-backed tag keeps the ceiling R5 minted on it (WATCH or lower).
- Breakout acceptance and trend acceptance share ONE CG_PRICE_STRUCTURE
  representative claim id per row (same bars cannot vote twice).
- NR/compression is CG_COMPRESSION and can never confirm on its own.
- The optional pattern lane is CG_PATTERN_STRUCTURE display-only with
  can_support_confirmed=False hard-coded by model validation.
- RVOL-EOD is a participation companion (CG_ACTIVITY_SESSION), not a second
  structure vote.
- WAIT_CA / REJECT rows carry UNKNOWN codes instead of structure claims.

Ceiling: LIVE_S4_WAIT_REJECT_ONLY. confirmedCount is pinned to 0. There is
no entry/target/stop field anywhere in this DTO: nextTrigger and
invalidationCondition are labels, not trade geometry.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .contracts import (
    EvidenceDirection,
    SelectionState,
    StateCeiling,
    stable_id,
)
from .r5_live import R5StructureBatchV1, R5StructureRowV1, latest_r5_structure_batch

SCHEMA_VERSION = "trendforge.s4-structure-pack.v1"
PROFILE_ID = "PRF-S4-STRUCTURE-PACK"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_S4_WAIT_REJECT_ONLY"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

GROUP_PRICE_STRUCTURE = "CG_PRICE_STRUCTURE"
GROUP_COMPRESSION = "CG_COMPRESSION"
GROUP_ACTIVITY_SESSION = "CG_ACTIVITY_SESSION"
GROUP_PATTERN_STRUCTURE = "CG_PATTERN_STRUCTURE"

TRIGGER_UNKNOWN_WAIT_CA = (
    "UNKNOWN_GAP_WAIT_CA resolve corporate action before any trigger"
)
INVALIDATION_UNKNOWN_WAIT_CA = "UNKNOWN_GAP_WAIT_CA"


class S4SetupTagV1(BaseModel):
    model_config = MODEL_CONFIG

    tag: str
    feature_id: str
    correlation_group: str
    direction: EvidenceDirection | None = None
    claim_id: str | None = None
    companion_only: bool = False
    same_root_as: str | None = None
    can_support_confirmed: Literal[False] = False


class S4PatternLaneEntryV1(BaseModel):
    model_config = MODEL_CONFIG

    pattern: str
    note: str = "PATTERN_DISPLAY_ONLY_NEVER_VOTES"
    can_support_confirmed: Literal[False] = False


class S4StructureRowV1(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    symbol: str
    instrument_id: str
    r2_public_state: SelectionState
    research_state: SelectionState
    state_ceiling: StateCeiling = StateCeiling.WAIT
    evidence_direction: EvidenceDirection
    display_order: int = Field(gt=0)
    ca_state: str
    index_context_state: str
    history_count: int = Field(ge=0)
    source_mode: str
    r14_run_id: str | None = None
    r14_run_hash: str | None = None
    setup_tags: tuple[S4SetupTagV1, ...] = ()
    pattern_lane: tuple[S4PatternLaneEntryV1, ...] = ()
    price_structure_representative_claim_id: str | None = None
    compression_representative_claim_id: str | None = None
    activity_representative_claim_id: str | None = None
    next_trigger: str = Field(min_length=1)
    invalidation_condition: str = Field(min_length=1)
    gate_codes: tuple[str, ...] = ()
    why_wait: tuple[str, ...] = ()
    why_unknown: tuple[str, ...] = ()

    @model_validator(mode="after")
    def enforce_s4_ceiling(self) -> "S4StructureRowV1":
        if self.research_state is SelectionState.CONFIRMED:
            raise ValueError("S4 pack cannot emit CONFIRMED")
        if self.r2_public_state is not SelectionState.REJECT and (
            not self.next_trigger.strip() or not self.invalidation_condition.strip()
        ):
            raise ValueError("every WATCH/WAIT structure row needs trigger labels")
        claim_backed = {
            tag.correlation_group: tag.claim_id
            for tag in self.setup_tags
            if tag.claim_id is not None
        }
        if GROUP_PRICE_STRUCTURE in claim_backed and (
            claim_backed[GROUP_PRICE_STRUCTURE]
            != self.price_structure_representative_claim_id
        ):
            raise ValueError("one CG_PRICE_STRUCTURE representative per row")
        if any(
            tag.claim_id is not None
            for tag in self.setup_tags
            if tag.correlation_group == GROUP_PRICE_STRUCTURE
        ) and self.ca_state == "WAIT_CA":
            raise ValueError("WAIT_CA rows cannot carry structure claims")
        return self


class S4StructurePackBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    run_id: str
    run_hash: str
    r1_bundle_id: str
    r1_bundle_hash: str
    r2_run_id: str
    r2_run_hash: str
    r14_run_id: str | None = None
    r14_run_hash: str | None = None
    trading_date: str
    built_at: datetime
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    confirmed_count: int = 0
    universe_count: int = Field(ge=0)
    rows: tuple[S4StructureRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_pack(self) -> "S4StructurePackBatchV1":
        if self.universe_count != len(self.rows):
            raise ValueError("S4 universe count does not match rows")
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("S4 cannot activate sources or unlock CONFIRMED")
        if self.confirmed_count != 0:
            raise ValueError("S4 confirmedCount is pinned to zero")
        if any(row.research_state is SelectionState.CONFIRMED for row in self.rows):
            raise ValueError("S4 rows cannot be CONFIRMED")
        return self


def _claim_by_feature(row: R5StructureRowV1) -> dict[str, object]:
    return {claim.feature_id: claim for claim in row.claims}


def _price_structure_tag(
    row: R5StructureRowV1,
) -> tuple[S4SetupTagV1 | None, S4SetupTagV1 | None]:
    """Breakout tag plus the same-root trend acceptance label.

    Both map to the single FTR-006 claim R5 minted, so the row keeps exactly
    one CG_PRICE_STRUCTURE representative.
    """
    breakout_claim = next(
        (
            claim
            for claim in row.claims
            if claim.correlation_group == GROUP_PRICE_STRUCTURE
        ),
        None,
    )
    if breakout_claim is None:
        return None, None
    if breakout_claim.direction is EvidenceDirection.BEARISH:
        breakout_tag = "BREAKDOWN_ACCEPTED"
        trend_word = "below"
    else:
        breakout_tag = "BREAKOUT_ACCEPTED"
        trend_word = "above"
    primary = S4SetupTagV1(
        tag=breakout_tag,
        feature_id=breakout_claim.feature_id,
        correlation_group=GROUP_PRICE_STRUCTURE,
        direction=breakout_claim.direction,
        claim_id=breakout_claim.claim_id,
    )
    trend = S4SetupTagV1(
        tag=f"TREND_ACCEPTANCE_{trend_word.upper()}_LEVEL",
        feature_id="FTR-005",
        correlation_group=GROUP_PRICE_STRUCTURE,
        direction=breakout_claim.direction,
        claim_id=breakout_claim.claim_id,
        same_root_as=breakout_claim.feature_id,
    )
    return primary, trend


def _compression_tag(row: R5StructureRowV1) -> S4SetupTagV1 | None:
    nr_setup = next((s for s in row.detected_setups if s.startswith("NR")), None)
    if nr_setup is None:
        return None
    nr_claim = next(
        (
            claim
            for claim in row.claims
            if claim.correlation_group == GROUP_COMPRESSION
        ),
        None,
    )
    window = nr_setup[2:] if len(nr_setup) > 2 else "7"
    return S4SetupTagV1(
        tag=f"{nr_setup}_COMPRESSION",
        feature_id=nr_claim.feature_id if nr_claim else "FTR-007",
        correlation_group=GROUP_COMPRESSION,
        direction=row.evidence_direction,
        claim_id=nr_claim.claim_id if nr_claim else None,
    )


def _activity_tag(row: R5StructureRowV1) -> S4SetupTagV1 | None:
    if "RVOL" not in row.detected_setups:
        return None
    rvol_claim = next(
        (
            claim
            for claim in row.claims
            if claim.correlation_group == GROUP_ACTIVITY_SESSION
        ),
        None,
    )
    return S4SetupTagV1(
        tag="RVOL_EOD_PARTICIPATION",
        feature_id=rvol_claim.feature_id if rvol_claim else "FTR-017",
        correlation_group=GROUP_ACTIVITY_SESSION,
        direction=row.evidence_direction,
        claim_id=rvol_claim.claim_id if rvol_claim else None,
        companion_only=True,
    )


def _trigger_labels(
    row: R5StructureRowV1,
) -> tuple[str, str]:
    """Deterministic WAIT labels. Never executable geometry."""
    codes = set(row.gate_codes) | set(row.why_wait)
    if row.ca_state == "WAIT_CA" or any(code.startswith("WAIT_CA") for code in codes):
        return TRIGGER_UNKNOWN_WAIT_CA, INVALIDATION_UNKNOWN_WAIT_CA
    if row.structure_state is SelectionState.REJECT or (
        row.r2_public_state is SelectionState.REJECT
    ):
        return (
            "UNKNOWN_R2_PUBLIC_REJECT no live trigger while rejected",
            "a new valid structure is required before any trigger",
        )
    metrics = row.metrics
    if metrics is not None and metrics.accepted:
        side = (
            "hold below prior-range low"
            if row.evidence_direction is EvidenceDirection.BEARISH
            else "hold above prior-range high"
        )
        level = f"{metrics.reference_level:.4f}" if metrics.reference_level else "?"
        return (
            f"WAIT close {side} ({level}) on next completed bar",
            "close back inside prior range on adjusted series",
        )
    if metrics is not None and metrics.narrow_range:
        return (
            "WAIT close outside the NR window range on next completed bar",
            "failed expansion back inside the NR window on adjusted series",
        )
    if metrics is not None and metrics.reference_level is not None:
        side = (
            "below prior-range low"
            if row.evidence_direction is EvidenceDirection.BEARISH
            else "above prior-range high"
        )
        return (
            f"WAIT close {side} on next completed bar",
            "close back inside prior range on adjusted series",
        )
    if "WAIT_HISTORY_NOT_READY" in codes or row.history_count == 0:
        return (
            "UNKNOWN_HISTORY_NOT_READY need more completed adjusted bars",
            "UNKNOWN_NO_ADJUSTED_BASELINE",
        )
    return "UNKNOWN_NO_STRUCTURE_CLAIM pending closed-bar analysis", (
        "UNKNOWN_NO_ADJUSTED_BASELINE"
    )


def _pack_row(
    row: R5StructureRowV1,
    *,
    pattern_lane: tuple[S4PatternLaneEntryV1, ...],
) -> S4StructureRowV1:
    breakout, trend = _price_structure_tag(row)
    compression = _compression_tag(row)
    activity = _activity_tag(row)
    tags = tuple(tag for tag in (breakout, trend, compression, activity) if tag)
    why_unknown: list[str] = []
    if not pattern_lane:
        why_unknown.append("PATTERN_LANE_NOT_EVALUATED_R5_ONLY")
    next_trigger, invalidation = _trigger_labels(row)
    research_state = (
        SelectionState.REJECT
        if row.structure_state is SelectionState.REJECT
        else SelectionState.WAIT
    )
    return S4StructureRowV1(
        candidate_id=row.candidate_id,
        symbol=row.symbol,
        instrument_id=row.instrument_id,
        r2_public_state=row.r2_public_state,
        research_state=research_state,
        evidence_direction=row.evidence_direction,
        display_order=row.display_order,
        ca_state=row.ca_state,
        index_context_state=row.index_context_state,
        history_count=row.history_count,
        source_mode=row.source_mode,
        r14_run_id=None,
        r14_run_hash=None,
        setup_tags=tags,
        pattern_lane=pattern_lane,
        price_structure_representative_claim_id=(
            breakout.claim_id if breakout else None
        ),
        compression_representative_claim_id=(
            compression.claim_id if compression else None
        ),
        activity_representative_claim_id=(activity.claim_id if activity else None),
        next_trigger=next_trigger,
        invalidation_condition=invalidation,
        gate_codes=tuple(dict.fromkeys(row.gate_codes)),
        why_wait=tuple(dict.fromkeys(row.why_wait)),
        why_unknown=tuple(dict.fromkeys(why_unknown)),
    )


def build_s4_structure_pack(
    *,
    r5: R5StructureBatchV1 | None = None,
    pattern_tags_by_symbol: dict[str, tuple[str, ...]] | None = None,
    built_at: datetime | None = None,
) -> S4StructurePackBatchV1:
    """Project the persisted hash-matched R5 batch into the S4 display pack."""
    batch = r5 if r5 is not None else latest_r5_structure_batch()
    if batch is None:
        raise ValueError("WAIT_S4_R5_NOT_READY")
    patterns = pattern_tags_by_symbol or {}
    rows = []
    for row in batch.rows:
        lane = tuple(
            S4PatternLaneEntryV1(pattern=name)
            for name in patterns.get(row.symbol, ())
        )
        packed = _pack_row(row, pattern_lane=lane)
        rows.append(
            packed.model_copy(
                update={
                    "r14_run_id": batch.r14_run_id,
                    "r14_run_hash": batch.r14_run_hash,
                }
            )
        )
    identity_payload = {
        "r5RunHash": batch.run_hash,
        "profileVersion": PROFILE_VERSION,
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return S4StructurePackBatchV1(
        run_id=stable_id("s4-structure-pack", batch.run_id, run_hash),
        run_hash=run_hash,
        r1_bundle_id=batch.r1_bundle_id,
        r1_bundle_hash=batch.r1_bundle_hash,
        r2_run_id=batch.r2_run_id,
        r2_run_hash=batch.r2_run_hash,
        r14_run_id=batch.r14_run_id,
        r14_run_hash=batch.r14_run_hash,
        trading_date=batch.trading_date,
        built_at=built_at or batch.decision_at,
        universe_count=len(rows),
        rows=tuple(rows),
        warnings=(
            "S4 structure pack is deterministic research evidence, not win "
            "probability. Trigger labels are not trade geometry.",
        ),
    )


def shortlist_symbols(pack: S4StructurePackBatchV1) -> tuple[str, ...]:
    """Names with at least one structure claim for downstream bounded stages."""
    claimed = [
        row.symbol
        for row in pack.rows
        if row.price_structure_representative_claim_id
        or row.compression_representative_claim_id
    ]
    return tuple(sorted(set(claimed)))


__all__ = [
    "ACCEPTANCE_CEILING",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "S4PatternLaneEntryV1",
    "S4SetupTagV1",
    "S4StructurePackBatchV1",
    "S4StructureRowV1",
    "build_s4_structure_pack",
    "latest_s4_structure_pack_inputs",
    "shortlist_symbols",
]


def latest_s4_structure_pack_inputs() -> R5StructureBatchV1 | None:
    return latest_r5_structure_batch()
