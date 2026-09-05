"""Live R3 FUS-009 diagnostic resolution over exact R1/R2 lineage."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ..source_contracts import SourceResult
from ..source_inventory_compiler import CompiledSourceContract
from .attention_order import InventoryDiscoveryV1
from .cash_a2_identity import CashIdentityBatch
from .contracts import (
    DataMode,
    EvidenceDirection,
    EvidenceFamily,
    GateOutcome,
    SelectionGateResult,
    SelectionState,
    StateCeiling,
    stable_id,
)
from .inventory_source_bundle import InventorySourceBundleV1
from .r3_claim_adapter import claims_from_cash_pipeline
from .resolver import ClaimDisposition, ResolutionProfile, resolve_evidence
from .store import latest_selection_payload, persist_selection_payload

SCHEMA_VERSION = "trendforge.resolution.v1"
PROFILE_ID = "PRF-R3-LIVE-DIAGNOSTIC"
PROFILE_VERSION = "1.0.0"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


def live_profile() -> ResolutionProfile:
    return ResolutionProfile(
        profile_id=PROFILE_ID,
        profile_version=PROFILE_VERSION,
        family_weights={
            EvidenceFamily.TRADABILITY_AND_SAFETY: 0.20,
            EvidenceFamily.MARKET_AND_SECTOR_CONTEXT: 0.15,
            EvidenceFamily.STRUCTURE: 0.30,
            EvidenceFamily.PARTICIPATION: 0.25,
            EvidenceFamily.EVENT_AND_SPONSOR: 0.10,
        },
        required_families=(EvidenceFamily.STRUCTURE, EvidenceFamily.PARTICIPATION),
        required_source_ids=("nse_bhavcopy_eod",),
        min_completeness=1.0,
        state_ceiling=StateCeiling.WAIT,
        allowed_data_modes=(DataMode.EOD_RESEARCH,),
        corroboration_epsilon=0.0,
    )


class R3SuppressionV1(BaseModel):
    model_config = MODEL_CONFIG
    claim_id: str | None = None
    disposition: str
    reason: str


class R3ResolutionRowV1(BaseModel):
    model_config = MODEL_CONFIG
    candidate_id: str
    symbol: str
    r2_public_state: SelectionState
    resolution_state: SelectionState
    blocks_progression: bool
    evidence_direction: EvidenceDirection
    display_order: int
    selected_support_claim_ids: tuple[str, ...] = ()
    selected_opposition_claim_ids: tuple[str, ...] = ()
    suppressed: tuple[R3SuppressionV1, ...] = ()
    family_support: dict[str, float]
    family_opposition: dict[str, float]
    missing_families: tuple[str, ...]
    conflict: bool
    evidence_strength: float = Field(ge=0, le=1)
    evidence_strength_label: str = "Evidence strength - not win probability"
    entry: None = None
    target: None = None
    stop: None = None
    quantity: None = None

    @model_validator(mode="after")
    def fail_closed(self) -> "R3ResolutionRowV1":
        if self.resolution_state is SelectionState.CONFIRMED:
            raise ValueError("live R3 cannot emit CONFIRMED")
        return self


class R3ResolutionV1(BaseModel):
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
    collector_run_id: str
    cash_pipeline_run_id: str
    permission_fingerprint: str
    trading_date: str
    decision_at: datetime
    state_ceiling: StateCeiling = StateCeiling.WAIT
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    evidence_strength_label: str = "Evidence strength - not win probability"
    persisted: bool = False
    market_context: dict[str, Any] | None = None
    rows: tuple[R3ResolutionRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def live_ceiling(self) -> "R3ResolutionV1":
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("R3 cannot activate sources or unlock CONFIRMED")
        if any(row.resolution_state is SelectionState.CONFIRMED for row in self.rows):
            raise ValueError("R3 live rows cannot be CONFIRMED")
        mc = self.market_context
        if mc is not None and mc.get("canSupportConfirmed") is not False:
            raise ValueError("market_context is display-only; canSupportConfirmed must be false")
        return self


def _r2_gate(state: SelectionState) -> SelectionGateResult:
    if state is SelectionState.REJECT:
        return SelectionGateResult(code="R2_PUBLIC_REJECT", outcome=GateOutcome.REJECT, blocks_confirmed=True, reason="R2 already rejected this row.")
    return SelectionGateResult(code="WAIT_SOURCE_ACTIVATION", outcome=GateOutcome.WAIT, blocks_confirmed=True, reason="Source activation remains false; R3 is diagnostic only.")


def build_r3_resolution(
    *,
    bundle: InventorySourceBundleV1,
    attention: InventoryDiscoveryV1,
    source_result: SourceResult,
    identity: CashIdentityBatch,
    compiled_source_contracts: Sequence[CompiledSourceContract],
    expected_permission_fingerprint: str,
) -> R3ResolutionV1:
    if bundle.permission_fingerprint != expected_permission_fingerprint:
        raise ValueError("WAIT_PERMISSION_MATRIX_MISMATCH")
    if attention.permission_fingerprint != expected_permission_fingerprint:
        raise ValueError("WAIT_PERMISSION_MATRIX_MISMATCH")
    adapter = claims_from_cash_pipeline(bundle=bundle, attention=attention, source_result=source_result, identity=identity, compiled_source_contracts=compiled_source_contracts)
    profile = live_profile()
    rows: list[R3ResolutionRowV1] = []
    for r2 in attention.rows:
        resolution = resolve_evidence(
            profile=profile,
            decision_at=attention.built_at,
            evidence_direction=r2.evidence_direction,
            claims=adapter.claims_by_symbol[r2.symbol],
            facts=adapter.facts_by_symbol[r2.symbol],
            source_results=adapter.source_results,
            completeness=r2.completeness,
            existing_gates=(_r2_gate(r2.public_state),),
            data_mode=DataMode.EOD_RESEARCH,
        )
        selected_support = tuple(item.claim_id for item in resolution.claims if item.disposition is ClaimDisposition.SELECTED_SUPPORT)
        selected_opposition = tuple(item.claim_id for item in resolution.claims if item.disposition is ClaimDisposition.SELECTED_OPPOSITION)
        suppressed = [R3SuppressionV1(claim_id=item.claim_id, disposition=item.disposition.value, reason=item.reason) for item in resolution.claims if item.disposition not in {ClaimDisposition.SELECTED_SUPPORT, ClaimDisposition.SELECTED_OPPOSITION}]
        suppressed.extend(R3SuppressionV1(disposition=reason, reason=reason) for reason in adapter.suppressions_by_symbol[r2.symbol])
        rows.append(R3ResolutionRowV1(
            candidate_id=r2.candidate_id,
            symbol=r2.symbol,
            r2_public_state=r2.public_state,
            resolution_state=resolution.state,
            blocks_progression=True,
            evidence_direction=r2.evidence_direction,
            display_order=r2.display_order,
            selected_support_claim_ids=selected_support,
            selected_opposition_claim_ids=selected_opposition,
            suppressed=tuple(suppressed),
            family_support={item.family.value: item.support_strength for item in resolution.families},
            family_opposition={item.family.value: item.opposition_strength for item in resolution.families},
            missing_families=tuple(item.value for item in resolution.family_missing),
            conflict=bool(selected_support and selected_opposition),
            evidence_strength=resolution.evidence_strength,
        ))
    identity_payload = {
        "r1BundleHash": bundle.bundle_hash,
        "r2RunHash": attention.run_hash,
        "profileVersion": PROFILE_VERSION,
        "decisionAt": attention.built_at.isoformat(),
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
    }
    run_hash = hashlib.sha256(json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return R3ResolutionV1(
        run_id=stable_id("r3-resolution", bundle.bundle_id, attention.run_id, PROFILE_VERSION, run_hash),
        run_hash=run_hash,
        r1_bundle_id=bundle.bundle_id,
        r1_bundle_hash=bundle.bundle_hash,
        r2_run_id=attention.run_id,
        r2_run_hash=attention.run_hash,
        collector_run_id=bundle.collector_run_id,
        cash_pipeline_run_id=bundle.cash_pipeline_run_id,
        permission_fingerprint=bundle.permission_fingerprint,
        trading_date=bundle.trading_date.isoformat(),
        decision_at=attention.built_at,
        rows=tuple(rows),
        warnings=("R3 resolves evidence families; it does not estimate win probability or authorize a trade.",),
    )


def persist_r3_resolution(value: R3ResolutionV1) -> R3ResolutionV1:
    stored = value.model_copy(update={"persisted": True})
    persist_selection_payload(
        run_id=stored.run_id,
        profile_id=PROFILE_ID,
        as_of=stored.decision_at,
        payload=stored.model_dump(mode="json", by_alias=True),
        candidates=tuple((row.candidate_id, row.symbol, row.resolution_state.value, row.model_dump(mode="json", by_alias=True)) for row in stored.rows),
    )
    return stored


def latest_r3_resolution() -> R3ResolutionV1 | None:
    payload = latest_selection_payload(PROFILE_ID)
    return R3ResolutionV1.model_validate(payload) if payload is not None else None
