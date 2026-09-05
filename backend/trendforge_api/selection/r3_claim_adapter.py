"""Exact-lineage adapter from the live cash pipeline into FUS-009 claims."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..feature_registry import feature_contract_by_id
from ..source_contracts import SourceResult
from ..source_inventory_compiler import CompiledSourceContract
from .attention_order import InventoryDiscoveryV1
from .cash_a2_identity import CashIdentityBatch
from .contracts import (
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    NormalizedFact,
    StateCeiling,
)
from .inventory_source_bundle import (
    InventorySourceBundleV1,
    SourceFreshnessState,
    SourceUsabilityState,
)

FEATURE_ID = "FTR-040"
SOURCE_ID = "nse_bhavcopy_eod"


@dataclass(frozen=True)
class ClaimAdapterResult:
    claims_by_symbol: dict[str, tuple[EvidenceClaim, ...]]
    facts_by_symbol: dict[str, tuple[NormalizedFact, ...]]
    source_results: tuple[SourceResult, ...]
    suppressions_by_symbol: dict[str, tuple[str, ...]]


def _contract(contracts: Sequence[CompiledSourceContract]) -> CompiledSourceContract | None:
    return next((item for item in contracts if item.source_contract_id == SOURCE_ID), None)


def _qualified_source_result(
    bundle: InventorySourceBundleV1, source_result: SourceResult
) -> SourceResult:
    record = next(
        (item for item in bundle.source_records if item.source_key == SOURCE_ID),
        None,
    )
    hashes = {
        value
        for value in (
            record.raw_content_hash if record else None,
            record.normalized_content_hash if record else None,
            record.last_good_hash if record else None,
        )
        if value
    }
    qualified = bool(
        record
        and record.usability_state is SourceUsabilityState.USABLE_CURRENT
        and record.freshness_state is SourceFreshnessState.CURRENT
        and record.data_date == source_result.data_date
        and source_result.artifact_hash in hashes
    )
    if qualified:
        return source_result.model_copy(update={"freshness": "FRESH"})
    return source_result


def claims_from_cash_pipeline(
    *,
    bundle: InventorySourceBundleV1,
    attention: InventoryDiscoveryV1,
    source_result: SourceResult,
    identity: CashIdentityBatch,
    compiled_source_contracts: Sequence[CompiledSourceContract],
) -> ClaimAdapterResult:
    if attention.r1_bundle_id != bundle.bundle_id or attention.r1_bundle_hash != bundle.bundle_hash:
        raise ValueError("WAIT_MIXED_SNAPSHOT_INPUTS: R1/R2 mismatch")
    if attention.built_at.tzinfo is None or attention.built_at.utcoffset() is None:
        raise ValueError("WAIT_LINEAGE_INCOMPLETE: R2 builtAt is naive")

    contract = _contract(compiled_source_contracts)
    feature = feature_contract_by_id(FEATURE_ID)
    binding_ok = bool(
        contract
        and feature
        and FEATURE_ID in contract.feature_ids
        and contract.directional_permission
        and contract.authority_cap == "RESEARCH_DIRECTIONAL_WAIT_ONLY"
        and contract.independence_family == EvidenceFamily.PARTICIPATION.value
        and "SWING" in contract.allowed_timeframes
        and "NSE_EQ" in contract.allowed_instruments
    )
    facts = {row.instrument.symbol: row.fact for row in identity.rows}
    r1_by_symbol = {row.symbol: row for row in bundle.stock_records}
    claims_by_symbol: dict[str, tuple[EvidenceClaim, ...]] = {}
    facts_by_symbol: dict[str, tuple[NormalizedFact, ...]] = {}
    suppressions: dict[str, tuple[str, ...]] = {}

    for row in attention.rows:
        reasons: list[str] = []
        fact = facts.get(row.symbol)
        r1 = r1_by_symbol.get(row.symbol)
        if not binding_ok:
            reasons.append("SUPPRESSED_COMPILER_PERMISSION")
        if fact is None or r1 is None or (fact is not None and r1.fact_id != fact.fact_id):
            reasons.append("SUPPRESSED_FACT_MISSING")
        if row.attention_priority is None:
            reasons.append("SUPPRESSED_ATTENTION_UNRANKED")
        if row.evidence_direction not in {EvidenceDirection.BULLISH, EvidenceDirection.BEARISH}:
            reasons.append("SUPPRESSED_NON_DIRECTIONAL")
        if source_result.source_id != SOURCE_ID:
            reasons.append("SUPPRESSED_SOURCE_MISMATCH")

        claim: EvidenceClaim | None = None
        if not reasons and fact is not None and feature is not None:
            claim = EvidenceClaim.create(
                feature_id=feature.feature_id,
                feature_version=feature.feature_version,
                family=EvidenceFamily.PARTICIPATION,
                correlation_group=feature.correlation_group,
                direction=row.evidence_direction,
                strength_before_caps=float(row.attention_priority),
                source_fact_ids=(fact.fact_id,),
                authority=source_result.role,
                available_at=fact.lineage.available_at,
                event_time=fact.lineage.event_time,
                published_at=fact.lineage.published_at,
                received_at=fact.lineage.received_at,
                revision_id=fact.lineage.revision_id,
                artifact_hash=fact.lineage.artifact_hash,
                state_ceiling=StateCeiling.WATCH,
                can_support_confirmed=False,
                explanation="Closed NSE cash-session participation; attention strength is not probability.",
            )
        claims_by_symbol[row.symbol] = (claim,) if claim is not None else ()
        facts_by_symbol[row.symbol] = (fact,) if fact is not None else ()
        suppressions[row.symbol] = tuple(reasons)

    return ClaimAdapterResult(
        claims_by_symbol=claims_by_symbol,
        facts_by_symbol=facts_by_symbol,
        source_results=(_qualified_source_result(bundle, source_result),),
        suppressions_by_symbol=suppressions,
    )
