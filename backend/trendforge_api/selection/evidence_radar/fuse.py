"""FUS-009 inside the radar: one representative per correlation group,
family scores with contradiction penalty. WAIT-only; never a Combined_Score."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .calculate import CalculatedFact, FactDirection

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

# Versioned display weights. Context families are weight 0: they explain,
# they never vote. Delivery is its own small family, never a second volume.
FUSION_WEIGHTS_V1: dict[str, float] = {
    "STRUCTURE": 0.25,
    "PARTICIPATION": 0.20,
    "DELIVERY": 0.10,
    "EVENT_AND_SPONSOR": 0.15,
    "SPONSOR_DELAYED": 0.10,
    "DERIVATIVES_FUTURES": 0.10,
    "DERIVATIVES_OPTIONS": 0.05,
    "MARKET_AND_SECTOR_CONTEXT": 0.0,
    "GLOBAL_CONTEXT": 0.0,
    "TRADABILITY_AND_SAFETY": 0.0,
    "IDENTITY": 0.0,
    "PK_SHADOW": 0.0,
    "UNKNOWN_FAMILY": 0.0,
    "SECONDARY_DISCOVERY": 0.0,
    "MCX_LOCAL": 0.25,
}

HORIZON_WEIGHT_OVERRIDES_V1: dict[str, dict[str, float]] = {
    # Intraday may not use delayed sponsor or delivery evidence at all;
    # assembly also never builds those facts for the intraday horizon.
    "INTRADAY": {"SPONSOR_DELAYED": 0.0, "DELIVERY": 0.0},
    # Position legality is enforced at assembly: session activity is never fed
    # in as accumulation-today; relative-strength carries its own weight.
}


class FamilyFusionV1(BaseModel):
    model_config = MODEL_CONFIG

    family: str
    status: str  # SUPPORT | OPPOSE | MISSING | CONFLICT | CONTEXT_ONLY
    direction: str
    representative_claim_id: str | None = None
    why: str


class FusionResultV1(BaseModel):
    model_config = MODEL_CONFIG

    horizon: str
    fused_direction: str  # BULLISH | BEARISH | NEUTRAL | CONFLICT
    conflict: bool
    display_rank_key: float
    families: tuple[FamilyFusionV1, ...]


def _representative_per_group(facts: list[CalculatedFact]) -> list[CalculatedFact]:
    chosen: list[CalculatedFact] = []
    seen_groups: set[str] = set()
    for fact in facts:
        if not fact.ok:
            continue
        group = fact.correlation_group or fact.family
        if group in seen_groups:
            continue
        seen_groups.add(group)
        chosen.append(fact)
    return chosen


def fuse_instrument(facts: list[CalculatedFact], horizon: str) -> FusionResultV1:
    overrides = HORIZON_WEIGHT_OVERRIDES_V1.get(horizon, {})
    families: list[FamilyFusionV1] = []
    contributions: dict[str, float] = {}
    detail: dict[str, float] = {}
    conflict = False

    by_family: dict[str, list[CalculatedFact]] = {}
    for fact in facts:
        by_family.setdefault(fact.family, []).append(fact)

    for family, family_facts in sorted(by_family.items()):
        weight = overrides.get(family, FUSION_WEIGHTS_V1.get(family, 0.0))
        representatives = _representative_per_group(family_facts)
        if not representatives:
            unknown = next((f for f in family_facts if not f.ok), None)
            families.append(
                FamilyFusionV1(
                    family=family,
                    status="MISSING",
                    direction="UNKNOWN",
                    representative_claim_id=unknown.code if unknown else None,
                    why=unknown.why if unknown else "No last-good evidence for this family.",
                )
            )
            continue
        directions = {rep.direction for rep in representatives}
        primary = representatives[0]
        if len(directions) > 1:
            conflict = True
            families.append(
                FamilyFusionV1(
                    family=family,
                    status="CONFLICT",
                    direction="CONFLICT",
                    representative_claim_id=primary.code,
                    why="Independent groups inside this family point in opposite directions.",
                )
            )
            continue
        if weight == 0.0:
            families.append(
                FamilyFusionV1(
                    family=family,
                    status="CONTEXT_ONLY",
                    direction=primary.direction.value,
                    representative_claim_id=primary.code,
                    why=primary.why,
                )
            )
            continue
        if primary.direction is FactDirection.BULLISH:
            contributions[family] = weight
            detail[family] = weight
            status = "SUPPORT"
            fused_direction = "BULLISH"
        elif primary.direction is FactDirection.BEARISH:
            contributions[family] = -weight
            detail[family] = -weight
            status = "OPPOSE"
            fused_direction = "BEARISH"
        else:
            contributions[family] = 0.0
            detail[family] = 0.0
            status = "NEUTRAL"
            fused_direction = "NEUTRAL"
        families.append(
            FamilyFusionV1(
                family=family,
                status=status,
                direction=fused_direction,
                representative_claim_id=primary.code,
                why=primary.why,
            )
        )

    total = round(sum(contributions.values()), 6)
    # Cross-family opposition is handled by the weighted sum itself (File A
    # contradiction penalty); hard CONFLICT stays reserved for disagreement
    # between independent groups inside one family.
    if conflict:
        fused_direction = "CONFLICT"
    elif total > 0.05:
        fused_direction = "BULLISH"
    elif total < -0.05:
        fused_direction = "BEARISH"
    else:
        fused_direction = "NEUTRAL"

    return FusionResultV1(
        horizon=horizon,
        fused_direction=fused_direction,
        conflict=conflict,
        display_rank_key=total,
        families=tuple(families),
    )


__all__ = [
    "FUSION_WEIGHTS_V1",
    "FamilyFusionV1",
    "FusionResultV1",
    "fuse_instrument",
]
