"""S6 claim-feed widening: merge R5-minted structure claims into the FUS-009 feed.

Additive research plumbing. Nothing here writes public state, unlocks
CONFIRMED, or changes ceilings: structure claims keep whatever ceiling and
can_support_confirmed flags R5 minted on them (False), and the optional
market-context block is display-only context with canSupportConfirmed=false.
"""

from __future__ import annotations

from typing import Any

from .contracts import EvidenceClaim, NormalizedFact
from .r3_claim_adapter import ClaimAdapterResult
from .r3_live import R3ResolutionV1


def structure_claims_from_r5(
    r5_batch: Any,
) -> dict[str, tuple[EvidenceClaim, ...]]:
    """Collect the real EvidenceClaim objects R5 minted per symbol."""
    out: dict[str, tuple[EvidenceClaim, ...]] = {}
    for row in getattr(r5_batch, "rows", ()) or ():
        if row.claims:
            out[row.symbol] = out.get(row.symbol, ()) + tuple(row.claims)
    return out


def structure_facts_from_r5(
    r5_batch: Any,
) -> dict[str, tuple[NormalizedFact, ...]]:
    """Collect the lineage facts backing those structure claims."""
    out: dict[str, tuple[NormalizedFact, ...]] = {}
    for row in getattr(r5_batch, "rows", ()) or ():
        if row.facts:
            out[row.symbol] = out.get(row.symbol, ()) + tuple(row.facts)
    return out


def merged_feed(
    cash: ClaimAdapterResult,
    r5_batch: Any | None = None,
) -> tuple[
    dict[str, tuple[EvidenceClaim, ...]],
    dict[str, tuple[NormalizedFact, ...]],
]:
    """Union the cash participation feed with optional R5 structure claims.

    Dedupe by claim_id (first wins) — resolve_evidence requires unique
    claim ids, and identical content minted twice must suppress, not crash.
    No re-ranking: downstream FUS-009 correlation groups own representative
    selection.
    """
    claims_by_symbol: dict[str, tuple[EvidenceClaim, ...]] = {}
    facts_by_symbol: dict[str, tuple[NormalizedFact, ...]] = {}
    struct_claims = structure_claims_from_r5(r5_batch) if r5_batch is not None else {}
    struct_facts = structure_facts_from_r5(r5_batch) if r5_batch is not None else {}
    symbols = set(cash.claims_by_symbol) | set(struct_claims)
    for symbol in symbols:
        seen: set[str] = set()
        merged_claims: list[EvidenceClaim] = []
        for claim in (*cash.claims_by_symbol.get(symbol, ()), *struct_claims.get(symbol, ())):
            if claim.claim_id in seen:
                continue
            seen.add(claim.claim_id)
            merged_claims.append(claim)
        claims_by_symbol[symbol] = tuple(merged_claims)
        merged_facts: dict[str, NormalizedFact] = {}
        for fact in (*cash.facts_by_symbol.get(symbol, ()), *struct_facts.get(symbol, ())):
            merged_facts[fact.fact_id] = fact
        facts_by_symbol[symbol] = tuple(merged_facts.values())
    return claims_by_symbol, facts_by_symbol


def market_context_block(weather: Any | None) -> dict[str, Any] | None:
    """Project S2 weather as display-only context; never a vote."""
    if weather is None:
        return None
    return {
        "regimeLabel": weather.regime_label,
        "tradingDate": weather.trading_date,
        "why": tuple(weather.why),
        "canSupportConfirmed": False,
    }


def attach_market_context(
    resolution: R3ResolutionV1 | None, weather: Any | None
) -> R3ResolutionV1 | None:
    block = market_context_block(weather)
    if resolution is None or block is None:
        return resolution
    return resolution.model_copy(update={"market_context": block})
