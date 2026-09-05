"""File A S6 (SEL-007): FUS-009 family resolution over S4+S5 claims.

Research strength only. This stage:
- ingests REAL lineage-backed claims: R5-minted structure/participation
  claims (via s6_claim_feed) plus any explicitly injected claim feed;
- resolves them through the canonical ``resolver.resolve_evidence`` with the
  ACTIVE VERSIONED PROFILE OBJECT (never a hardcoded required-family list);
- projects every EvidenceFamily into a support/oppose map, flags conflict,
  and labels evidence strength exactly "Evidence strength - not win
  probability".

This stage is NOT:
- CONFIRMED (that is S7 behind the R2-B unlock amendment);
- Combined_Score / additive tutorial points;
- a second volume vote (correlation groups own representation);
- S2-as-stock-vote: market weather is attached as display-only context with
  canSupportConfirmed=false and can never satisfy a required family.

Ceiling LIVE_S6_RESOLVE_WAIT_ONLY. Rows are WAIT/WATCH/REJECT only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ..source_contracts import SourceResult
from .attention_order import InventoryDiscoveryV1, latest_attention_order
from .contracts import (
    DataMode,
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    NormalizedFact,
    SelectionState,
    StateCeiling,
    stable_id,
)
from .inventory_source_bundle import InventorySourceBundleV1, latest_inventory_source_bundle
from .r14_live import latest_r14_ca_join
from .r3_claim_adapter import claims_from_cash_pipeline
from .r3_live import live_profile
from .r5_live import R5StructureBatchV1, latest_r5_structure_batch
from .resolver import ClaimDisposition, ResolutionProfile, resolve_evidence
from .s4_structure_pack import (
    S4StructurePackBatchV1,
    build_s4_structure_pack,
    shortlist_symbols,
)
from .s5_shortlist_enrichment import S5EnrichmentBatchV1, build_s5_enrichment
from .s6_claim_feed import merged_feed, structure_claims_from_r5
from .store import latest_selection_payload

SCHEMA_VERSION = "trendforge.s6-resolution.v1"
PROFILE_ID = "PRF-S6-FAMILY-RESOLUTION"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_S6_RESOLVE_WAIT_ONLY"
STRENGTH_LABEL = "Evidence strength - not win probability"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class S6FamilyStrengthV1(BaseModel):
    model_config = MODEL_CONFIG

    support: float = Field(ge=0, le=1)
    oppose: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)


class S6ResolutionRowV1(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    symbol: str
    r2_public_state: SelectionState
    resolution_state: SelectionState
    state_ceiling: StateCeiling = StateCeiling.WAIT
    evidence_direction: EvidenceDirection
    display_order: int = Field(gt=0)
    families: dict[str, S6FamilyStrengthV1]
    conflict: bool
    evidence_strength: float = Field(ge=0, le=1)
    evidence_strength_label: str = STRENGTH_LABEL
    missing_families: tuple[str, ...] = ()
    representative_claim_ids: tuple[str, ...] = ()
    suppressed_claim_ids: tuple[str, ...] = ()
    why: tuple[str, ...] = ()
    why_unknown: tuple[str, ...] = ()
    can_unlock_confirmed: bool = False

    @model_validator(mode="after")
    def enforce_s6_ceiling(self) -> "S6ResolutionRowV1":
        if self.resolution_state is SelectionState.CONFIRMED:
            raise ValueError("S6 cannot emit CONFIRMED")
        if self.can_unlock_confirmed:
            raise ValueError("S6 cannot unlock CONFIRMED")
        if "not win probability" not in self.evidence_strength_label:
            raise ValueError("evidence strength must be labelled not-win-probability")
        return self


class S6MarketContextBlockV1(BaseModel):
    model_config = MODEL_CONFIG

    regime_label: str | None = None
    trading_date: str | None = None
    why: tuple[str, ...] = ()
    can_support_confirmed: Literal[False] = False


class S6ResolutionBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    active_profile_id: str
    active_profile_version: str
    run_id: str
    run_hash: str
    r1_bundle_hash: str
    r2_run_hash: str
    r14_run_hash: str | None = None
    trading_date: str
    built_at: datetime
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    confirmed_count: int = 0
    universe_count: int = Field(ge=0)
    market_context: S6MarketContextBlockV1 | None = None
    rows: tuple[S6ResolutionRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_batch(self) -> "S6ResolutionBatchV1":
        if self.universe_count != len(self.rows):
            raise ValueError("S6 universe count does not match rows")
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("S6 cannot activate sources or unlock CONFIRMED")
        if any(row.resolution_state is SelectionState.CONFIRMED for row in self.rows):
            raise ValueError("S6 rows cannot be CONFIRMED")
        if self.confirmed_count != 0:
            raise ValueError("S6 confirmedCount is pinned to zero")
        return self


def _market_context(weather: Any) -> S6MarketContextBlockV1 | None:
    if weather is None:
        return None
    regime = getattr(weather, "regime_label", None)
    trading_date = getattr(weather, "trading_date", None)
    why = tuple(getattr(weather, "why", ()) or ())
    if regime is None and trading_date is None and not why:
        return None
    return S6MarketContextBlockV1(
        regime_label=str(regime) if regime is not None else None,
        trading_date=str(trading_date) if trading_date is not None else None,
        why=tuple(str(item) for item in why),
    )


def _r2_gate(state: SelectionState):
    from .contracts import GateOutcome, SelectionGateResult

    if state is SelectionState.REJECT:
        return SelectionGateResult(
            code="R2_PUBLIC_REJECT",
            outcome=GateOutcome.REJECT,
            blocks_confirmed=True,
            reason="R2 already rejected this row.",
        )
    return SelectionGateResult(
        code="WAIT_SOURCE_ACTIVATION",
        outcome=GateOutcome.WAIT,
        blocks_confirmed=True,
        reason="Source activation remains false; S6 resolution is diagnostic.",
    )


def _family_map(resolution, profile: ResolutionProfile) -> dict[str, S6FamilyStrengthV1]:
    by_family = {item.family.value: item for item in resolution.families}
    out: dict[str, S6FamilyStrengthV1] = {}
    for family in EvidenceFamily:
        item = by_family.get(family.value)
        out[family.value] = S6FamilyStrengthV1(
            support=item.support_strength if item else 0,
            oppose=item.opposition_strength if item else 0,
            weight=profile.family_weights.get(family, 0),
        )
    return out


def _s5_notes(s5: S5EnrichmentBatchV1 | None) -> dict[str, tuple[str, ...]]:
    """Typed S5 fields become honest context notes, never extra votes."""
    notes: dict[str, tuple[str, ...]] = {}
    if s5 is None:
        return notes
    for row in s5.rows:
        items = ["S5_ENRICHMENT_CONTEXT_NOT_A_VOTE"]
        if row.options_package.status == "UNKNOWN_NEEDS_R12":
            items.append("OPTIONS_NEEDS_R12_NO_FRESH_CHAIN")
        if row.delivery.status.startswith(("UNKNOWN", "FORBIDDEN")):
            items.append(f"DELIVERY_{row.delivery.status}")
        notes[row.symbol.upper()] = tuple(items)
    return notes


def merge_native_claims(
    rows: Any,
    *,
    native_claims: Any = (),
    covered_groups: dict[str, set[str]] | None = None,
) -> tuple[S6ResolutionRowV1, ...]:
    """R8 ingest: native scanner claims fill EMPTY correlation groups only.

    First-wins per (symbol, group): a group listed in ``covered_groups``
    (already represented by an R5/R14-minted claim) can never be overridden,
    and within one call the first native claim per group wins. Duplicate
    claim ids are always skipped.
    """
    coverage = covered_groups or {}
    out: list[S6ResolutionRowV1] = []
    for row in rows:
        reps = list(row.representative_claim_ids)
        symbol_key = row.symbol.upper()
        seen_groups = set(coverage.get(symbol_key, set()))
        why_extra: list[str] = []
        for claim in native_claims or ():
            if str(claim.get("symbol", "")).upper() != symbol_key:
                continue
            group = str(claim.get("group", ""))
            claim_id = str(claim.get("claim_id", ""))
            if not group or not claim_id:
                continue
            if claim_id in reps or group in seen_groups:
                continue
            reps.append(claim_id)
            seen_groups.add(group)
            why_extra.append(f"NATIVE_CLAIM_INGESTED:{claim_id}")
        changed = len(reps) != len(row.representative_claim_ids)
        if changed:
            out.append(
                row.model_copy(
                    update={
                        "representative_claim_ids": tuple(reps),
                        "why": tuple(dict.fromkeys((*row.why, *why_extra))),
                    }
                )
            )
        else:
            out.append(row)
    return tuple(out)


def build_s6_resolution(
    *,
    s4: S4StructurePackBatchV1 | None = None,
    r5: R5StructureBatchV1 | None = None,
    s5: S5EnrichmentBatchV1 | None = None,
    attention: InventoryDiscoveryV1 | None = None,
    bundle: InventorySourceBundleV1 | None = None,
    source_result: SourceResult | None = None,
    weather: Any = None,
    profile: ResolutionProfile | None = None,
    claims_extra_by_symbol: dict[str, tuple[EvidenceClaim, ...]] | None = None,
    facts_extra: tuple[NormalizedFact, ...] = (),
    ca_join: Any | None = None,
    cash_feed: Any | None = None,
    identity: Any | None = None,
    compiled_source_contracts: Any | None = None,
    bound_to_shortlist: bool = True,
    native_claims: Any = (),
    built_at: datetime | None = None,
) -> S6ResolutionBatchV1:
    """Resolve S4+S5-era claims per family using the canonical resolver.

    Claim feed is ``merged_feed``: the cash FTR-040 participation adapter
    unioned with R5-published structure claims. Rows are bounded to the S4/S5
    structure-claimed shortlist unless ``bound_to_shortlist`` is disabled for
    wide diagnostics.

    ``native_claims`` (R8): optional mappings
    ``{"symbol","group","claim_id"}`` ingested AFTER resolution with strict
    first-wins per correlation group - a group already represented by an R5
    claim can never be overridden (see ``merge_native_claims``).
    """
    batch5 = r5 if r5 is not None else latest_r5_structure_batch()
    if batch5 is None:
        raise ValueError("WAIT_S6_R5_NOT_READY")
    pack = s4 if s4 is not None else build_s4_structure_pack(r5=batch5)
    active_profile = profile or live_profile()
    r1 = bundle if bundle is not None else latest_inventory_source_bundle()
    r2 = attention if attention is not None else latest_attention_order()
    joined14 = ca_join if ca_join is not None else latest_r14_ca_join()
    if (
        pack.r14_run_hash is None
        or joined14 is None
        or pack.r14_run_hash != joined14.run_hash
    ):
        raise ValueError("WAIT_S6_LINEAGE_MISMATCH")

    warnings_list: list[str] = []
    cash_source = source_result
    if cash_source is None:
        from .cash_a1_staging import latest_cash_staging

        staging = latest_cash_staging()
        cash_source = staging.source_result if staging is not None else None

    adapter = cash_feed
    if adapter is None and r1 is not None and r2 is not None and cash_source is not None:
        try:
            from .cash_a2_identity import latest_cash_identity
            from ..source_inventory_compiler import compile_default_inventory

            feed_identity = (
                identity
                if identity is not None
                else latest_cash_identity()
            )
            feed_contracts = (
                compiled_source_contracts
                if compiled_source_contracts is not None
                else compile_default_inventory().source_contracts
            )
            if feed_identity is not None:
                adapter = claims_from_cash_pipeline(
                    bundle=r1,
                    attention=r2,
                    source_result=cash_source,
                    identity=feed_identity,
                    compiled_source_contracts=feed_contracts,
                )
            else:
                warnings_list.append("CASH_FEED_IDENTITY_MISSING")
        except ValueError as exc:
            adapter = None
            warnings_list.append(f"CASH_FEED_LINEAGE_SKIPPED_{exc}")
    elif adapter is None:
        warnings_list.append("CASH_FEED_UNAVAILABLE")

    struct_claims = structure_claims_from_r5(batch5)
    struct_facts: dict[str, tuple[NormalizedFact, ...]] = {
        row.symbol: row.facts for row in batch5.rows if row.facts
    }
    if adapter is not None:
        claims_by_symbol, facts_by_symbol = merged_feed(adapter, batch5)
    else:
        claims_by_symbol, facts_by_symbol = dict(struct_claims), dict(struct_facts)
    extras = claims_extra_by_symbol or {}
    extra_fact_list = facts_extra

    suppressions_by_symbol: dict[str, tuple[str, ...]] = (
        dict(adapter.suppressions_by_symbol) if adapter is not None else {}
    )

    s5_notes = _s5_notes(s5 if s5 is not None else _try_build_s5(pack))
    now = built_at or batch5.decision_at
    shortlist = (
        set(shortlist_symbols(pack)) if bound_to_shortlist else None
    )
    adapter_source_ids = {
        result.source_id for result in (adapter.source_results if adapter else ())
    }
    source_results = tuple(
        dict.fromkeys(
            (adapter.source_results if adapter else ())
            + ((cash_source,) if cash_source is not None and cash_source.source_id not in adapter_source_ids else ())
        )
    )
    rows: list[S6ResolutionRowV1] = []
    for row5 in batch5.rows:
        symbol_key = row5.symbol.upper()
        if shortlist is not None and row5.symbol not in shortlist:
            continue
        claims = tuple(claims_by_symbol.get(row5.symbol, ())) + tuple(
            extras.get(symbol_key, ())
        )
        facts = tuple(facts_by_symbol.get(row5.symbol, ())) + tuple(extra_fact_list)
        resolution = resolve_evidence(
            profile=active_profile,
            decision_at=now,
            evidence_direction=row5.evidence_direction,
            claims=claims,
            facts=facts,
            source_results=source_results,
            completeness=1.0,
            existing_gates=(_r2_gate(row5.r2_public_state),),
            data_mode=DataMode.EOD_RESEARCH,
        )
        selected_ids = tuple(
            item.claim_id
            for item in resolution.claims
            if item.disposition
            in {ClaimDisposition.SELECTED_SUPPORT, ClaimDisposition.SELECTED_OPPOSITION}
        )
        suppressed_ids = tuple(
            item.claim_id
            for item in resolution.claims
            if item.disposition
            not in {ClaimDisposition.SELECTED_SUPPORT, ClaimDisposition.SELECTED_OPPOSITION}
        )
        conflict = bool(resolution.family_opposes) and bool(resolution.family_supports)
        why = tuple(dict.fromkeys(gate.code for gate in resolution.gate_results))
        why_unknown = tuple(
            dict.fromkeys(
                s5_notes.get(symbol_key, ())
                + suppressions_by_symbol.get(row5.symbol, ())
                + suppressions_by_symbol.get(symbol_key, ())
            )
        )
        rows.append(
            S6ResolutionRowV1(
                candidate_id=row5.candidate_id,
                symbol=row5.symbol,
                r2_public_state=row5.r2_public_state,
                resolution_state=(
                    SelectionState.REJECT
                    if row5.structure_state is SelectionState.REJECT
                    else resolution.state
                ),
                evidence_direction=row5.evidence_direction,
                display_order=row5.display_order,
                families=_family_map(resolution, active_profile),
                conflict=conflict,
                evidence_strength=resolution.evidence_strength,
                evidence_strength_label=STRENGTH_LABEL,
                missing_families=tuple(
                    family.value for family in resolution.family_missing
                ),
                representative_claim_ids=selected_ids,
                suppressed_claim_ids=suppressed_ids,
                why=why,
                why_unknown=why_unknown,
            )
        )

    if native_claims:
        rows = list(
            merge_native_claims(tuple(rows), native_claims=native_claims)
        )

    if native_claims:
        rows = list(
            merge_native_claims(tuple(rows), native_claims=native_claims)
        )

    identity_payload = {
        "s4RunHash": pack.run_hash,
        "activeProfileId": active_profile.profile_id,
        "activeProfileVersion": active_profile.profile_version,
        "cashFeedMerged": adapter is not None,
        "boundToShortlist": bool(shortlist is not None),
        "decisionAt": now.isoformat(),
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    feed_warnings = (
        () if adapter is not None
        else (tuple(warnings_list) or ("CASH_FEED_UNAVAILABLE",))
    )
    return S6ResolutionBatchV1(
        run_id=stable_id("s6-resolution", pack.run_id, run_hash),
        run_hash=run_hash,
        r1_bundle_hash=pack.r1_bundle_hash,
        r2_run_hash=pack.r2_run_hash,
        r14_run_hash=pack.r14_run_hash,
        trading_date=pack.trading_date,
        built_at=now,
        active_profile_id=active_profile.profile_id,
        active_profile_version=active_profile.profile_version,
        universe_count=len(rows),
        market_context=_market_context(weather),
        rows=tuple(rows),
        warnings=(
            "S6 fuses lineage-backed claims only; S5 enrichment fields stay "
            "display context until their sources carry vote authority.",
            "Required families come from the active versioned profile object.",
            "Claim feed is merged_feed: cash FTR-040 participation unioned "
            "with R5 structure claims; rows are bounded to the S4/S5 claimed "
            "shortlist." if shortlist is not None else
            "Wide diagnostic mode: rows are not bounded to the shortlist.",
            *feed_warnings,
        ),
    )


def _try_build_s5(pack: S4StructurePackBatchV1) -> S5EnrichmentBatchV1 | None:
    try:
        return build_s5_enrichment(s4=pack)
    except ValueError:
        return None


def latest_s6_resolution() -> S6ResolutionBatchV1 | None:
    payload = latest_selection_payload(PROFILE_ID)
    return S6ResolutionBatchV1.model_validate(payload) if payload else None


__all__ = [
    "ACCEPTANCE_CEILING",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "STRENGTH_LABEL",
    "S6FamilyStrengthV1",
    "S6MarketContextBlockV1",
    "S6ResolutionBatchV1",
    "S6ResolutionRowV1",
    "build_s6_resolution",
    "latest_s6_resolution",
    "merge_native_claims",
]
