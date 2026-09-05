"""M-Factor claim merge: R5 closed-bar STRUCTURE + R3 cash PARTICIPATION.

Pure composition only. This module never imports FastAPI, never fetches URLs,
never re-scores families (resolver.py FUS-009 owns that) and never lifts a
ceiling. Authority: M_FACTOR_USEFUL_FUS009_WIRING_GLM_PROMPT.md (2026-08-23),
File A FUS-009 and FTR-006/007/017/040.

Structure claims are rebuilt by re-running the same deterministic
``analyze_closed_bar_structure`` that produced the persisted, hash-matched R5
row. If the fresh analysis drifts from the persisted row, claims are withheld
with a named code instead of mixed into the snapshot. Rebuilt claims keep
``can_support_confirmed=False``; R5's WAIT ceiling is untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..source_contracts import SourceResult
from .cash_a4_history import CashRawSessionBar
from .contracts import (
    EvidenceClaim,
    InstrumentIdentity,
    NormalizedFact,
)
from .r14_live import R14CaJoinRowV1
from .r5_live import R5StructureRowV1, _closed_bars, _profile
from .structure import analyze_closed_bar_structure

INDEX_CONFLICT_THRESHOLD_PERCENT = 1.0
INDEX_SESSION_CHANGE_SANITY_PERCENT = 7.0


@dataclass(frozen=True)
class StructureRebuild:
    """Deterministic rebuild outcome for one symbol's R5 structure evidence."""

    claims: tuple[EvidenceClaim, ...] = ()
    facts: tuple[NormalizedFact, ...] = ()
    codes: tuple[str, ...] = ()
    minted_features: tuple[str, ...] = ()
    reference_level: float | None = None
    detected_setups: tuple[str, ...] = ()


@dataclass(frozen=True)
class MergedSymbolClaims:
    """One symbol's merged FUS-009 input set (claims + facts + named blockers)."""

    claims: tuple[EvidenceClaim, ...] = ()
    facts: tuple[NormalizedFact, ...] = ()
    suppressions: tuple[str, ...] = ()
    structure_codes: tuple[str, ...] = ()
    structure_features: tuple[str, ...] = ()
    reference_level: float | None = None
    detected_setups: tuple[str, ...] = ()


def rebuild_r5_claims(
    *,
    r5_row: R5StructureRowV1,
    instrument: InstrumentIdentity,
    raw_bars: list[CashRawSessionBar],
    ca_row: R14CaJoinRowV1,
    source_result: SourceResult,
    decision_at: datetime,
) -> StructureRebuild:
    """Rebuild FTR-006/007/017 claims exactly as R5 minted them.

    Only rows whose persisted R5 record actually detected setups are rebuilt;
    everything else stays a named NOT_EVALUATED/WAIT slot, never a silent skip.
    """
    if not r5_row.detected_setups or r5_row.metrics is None:
        return StructureRebuild(
            codes=("STRUCTURE_NOT_EVALUATED",),
            detected_setups=r5_row.detected_setups,
        )
    profile = _profile(r5_row.evidence_direction)
    if profile is None or not raw_bars:
        return StructureRebuild(
            codes=("WAIT_R5_REBUILD_INPUTS_MISSING",),
            detected_setups=r5_row.detected_setups,
        )
    bars, bar_waits = _closed_bars(
        instrument=instrument,
        raw_bars=raw_bars,
        decision_at=decision_at,
        ca_row=ca_row,
    )
    if bar_waits or not bars:
        return StructureRebuild(
            codes=tuple(bar_waits) or ("WAIT_HISTORY_NOT_READY",),
            detected_setups=r5_row.detected_setups,
        )
    analysis = analyze_closed_bar_structure(
        instrument=instrument,
        bars=bars,
        source_result=source_result,
        profile=profile,
        decision_at=decision_at,
    )
    fresh = analysis.metrics
    persisted = r5_row.metrics
    drifted = (
        fresh.accepted != persisted.accepted
        or bool(fresh.narrow_range) != bool(persisted.narrow_range)
        or (fresh.relative_volume is None) != (persisted.relative_volume is None)
        or (
            fresh.relative_volume is not None
            and persisted.relative_volume is not None
            and abs(fresh.relative_volume - persisted.relative_volume) > 1e-9
        )
    )
    if drifted:
        return StructureRebuild(
            codes=("WAIT_R5_REBUILD_DRIFT",),
            reference_level=persisted.reference_level,
            detected_setups=r5_row.detected_setups,
        )
    if not analysis.claims:
        return StructureRebuild(
            codes=("STRUCTURE_CLAIMS_EMPTY",),
            reference_level=persisted.reference_level,
            detected_setups=r5_row.detected_setups,
        )
    return StructureRebuild(
        claims=analysis.claims,
        facts=(analysis.fact,),
        minted_features=tuple(
            dict.fromkeys(claim.feature_id for claim in analysis.claims)
        ),
        reference_level=fresh.reference_level,
        detected_setups=r5_row.detected_setups,
    )


def merge_symbol_claims(
    *,
    cash_claims: tuple[EvidenceClaim, ...],
    cash_facts: tuple[NormalizedFact, ...],
    adapter_suppressions: tuple[str, ...] = (),
    structure: StructureRebuild | None = None,
) -> MergedSymbolClaims:
    """Concatenate the cash-activity claim with rebuilt structure claims.

    FTR-040 and FTR-017 share CG_ACTIVITY_SESSION; FUS-009 takes the max per
    group side, so participation is never double counted here.
    """
    structure = structure or StructureRebuild()
    return MergedSymbolClaims(
        claims=tuple(cash_claims) + structure.claims,
        facts=tuple(cash_facts) + structure.facts,
        suppressions=tuple(adapter_suppressions),
        structure_codes=structure.codes,
        structure_features=structure.minted_features,
        reference_level=structure.reference_level,
        detected_setups=structure.detected_setups,
    )


def index_session_conflict(
    *,
    row_class: str,
    index_change_percent: float | None,
    threshold_percent: float = INDEX_CONFLICT_THRESHOLD_PERCENT,
) -> bool:
    """INDEX_CONFLICT_V0: a materially opposite NIFTY session vs the row class.

    This is a session-change heuristic, not the versioned breadth+index
    structure rule of plan 1D (not built yet). Fail-closed default: no signal
    when the index context is missing. A change outside the sanity bound (no
    real NIFTY session has exceeded +/-7%) is treated as unproven rather than
    trusted, because a conflict must be proven, never assumed. The flag seats
    a row to WAIT; it never creates an opposite trade.
    """
    if index_change_percent is None:
        return False
    if abs(index_change_percent) > INDEX_SESSION_CHANGE_SANITY_PERCENT:
        return False
    if row_class in {"Bull", "Strong Bull"} and index_change_percent <= -threshold_percent:
        return True
    if row_class in {"Bear", "Strong Bear"} and index_change_percent >= threshold_percent:
        return True
    return False


def what_label(
    *, deal_summary: str | None, deal_tag: str | None
) -> str:
    """Named-deal WHAT label from R6 enrichment. No EVENT claim is minted.

    FTR-026 (EVENT_AND_SPONSOR) has no live fact/source wiring yet, so named
    deals are labels only; market-wide FII/DII nets are never stock evidence.
    """
    if deal_summary and deal_tag:
        return f"NAMED_DEAL {deal_summary}"
    if deal_summary:
        return f"DEAL_UNNAMED_OR_UNALIGNED {deal_summary}"
    return "UNKNOWN_NO_LARGE_DEAL_ROW"


def structure_how_text(
    merged: MergedSymbolClaims,
    *,
    structure_claim_ids: tuple[str, ...] = (),
    structure_state: str | None = None,
) -> str:
    """HOW text cites real claim IDs, or names exactly why STRUCTURE did not vote."""
    if merged.structure_features and structure_claim_ids:
        return (
            f"R5 STRUCTURE voted: {' + '.join(merged.structure_features)} "
            f"claims {', '.join(structure_claim_ids)}; setups "
            f"{', '.join(merged.detected_setups) or 'none'}"
            + (
                f"; reference level {merged.reference_level} (research label, never an order level)"
                if merged.reference_level is not None
                else ""
            )
            + (f"; R5 state {structure_state}" if structure_state else "")
        )
    if merged.structure_codes:
        return f"STRUCTURE_WITHHELD ({'; '.join(merged.structure_codes)})"
    return "STRUCTURE_NOT_EVALUATED: required family STRUCTURE has no eligible FUS-009 claims"
