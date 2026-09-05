"""L13 EXPLAIN: how / what / where / when plus File A's eight radar questions.

Empty strings are forbidden; every slot that cannot speak emits an UNKNOWN code.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

from .calculate import CalculatedFact
from .fuse import FusionResultV1

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

_NOT_IN_SCOPE = "NOT_IN_SCOPE_RESEARCH_RADAR"


class ExplainV1(BaseModel):
    model_config = MODEL_CONFIG

    how: str
    what: str
    where: str
    when: str
    invalidation: str
    q1_instrument_profile_timeframe: str
    q2_state_classification: str
    q3_why_entered_now: str
    q4_supporting_families: str
    q5_strongest_contradiction: str
    q6_missing_proof_and_state_change_condition: str
    q7_run_completeness_freshness: str
    q8_what_changed_vs_prior_run: str

    @model_validator(mode="after")
    def nothing_silent(self) -> "ExplainV1":
        for name, value in self.__dict__.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"explain field {name} must be non-empty")
        return self


def _facts_line(facts: list[CalculatedFact], *, codes_only: bool = False) -> str:
    parts: list[str] = []
    for fact in facts:
        if fact.ok and not codes_only:
            value = f"={fact.value}" if fact.value is not None else ""
            parts.append(f"{fact.code}{value}")
        elif not fact.ok:
            parts.append(fact.code)
    return "; ".join(parts) if parts else "UNKNOWN_NO_FACTS_COMPUTED"


def build_explain(
    *,
    symbol: str,
    horizon: str,
    market: str,
    public_state: str,
    fusion: FusionResultV1,
    facts: list[CalculatedFact],
    completeness: float,
    freshness: str,
    restriction_state: str,
    what_changed: str = "NO_BASELINE",
) -> ExplainV1:
    ok_facts = [fact for fact in facts if fact.ok]
    unknown_facts = [fact for fact in facts if not fact.ok]

    structure = next((f for f in ok_facts if f.family == "STRUCTURE"), None)
    participation = next((f for f in ok_facts if f.family == "PARTICIPATION"), None)
    delivery = next((f for f in ok_facts if f.family == "DELIVERY"), None)
    fo = next((f for f in ok_facts if f.family == "DERIVATIVES_FUTURES"), None)
    mcx = next((f for f in ok_facts if f.family == "MCX_LOCAL"), None)

    how_parts: list[str] = []
    if horizon == "COMMODITY":
        how_parts.append(
            f"local MCX {mcx.code}={mcx.value}"
            if mcx
            else "local MCX UNKNOWN_NO_LOCAL_BAR"
        )
    else:
        how_parts.append(
            f"structure {structure.code}={structure.value}"
            if structure
            else "structure UNKNOWN_NO_CLOSED_STRUCTURE_FACT"
        )
        how_parts.append(
            f"participation {participation.code}"
            if participation
            else "participation one-cash-story-read-from-R2 (no second volume vote)"
        )
        if horizon == "INTRADAY":
            how_parts.append("delivery FORBIDDEN_ON_INTRADAY")
        else:
            how_parts.append(
                f"delivery {delivery.code}"
                if delivery
                else "delivery UNKNOWN_DELIVERY_SOURCE_MISSING"
            )
        if fo:
            how_parts.append(f"F&O {fo.code}")
        else:
            how_parts.append("F&O package MISSING_CASH_ONLY_NOT_PUNISHED")

    event_facts = [
        fact
        for fact in ok_facts
        if fact.family in {"EVENT_AND_SPONSOR", "SPONSOR_DELAYED"}
    ]
    unknown_codes = [fact.code for fact in unknown_facts]

    when_known = (
        f"EOD file known after 15:35 IST; horizon {horizon}; "
        f"freshness {freshness}"
    )
    next_confirm = (
        "; ".join(fact.code for fact in unknown_facts[:2])
        if unknown_facts
        else "next independent family confirmation pending source activation"
    )
    invalidation = (
        "close back inside prior structure on adjusted series"
        if structure
        else "UNKNOWN_INVALIDATION_NEEDS_CLOSED_STRUCTURE"
    )

    contradiction = next(
        (
            family.why
            for family in fusion.families
            if family.status in {"CONFLICT", "OPPOSE"}
        ),
        "UNKNOWN_NO_OPPOSITION_RECORDED",
    )

    return ExplainV1(
        how="; ".join(how_parts),
        what=(
            _facts_line(event_facts)
            if event_facts
            else "UNKNOWN_NO_EVENT_OR_SPONSOR_FACT"
        ),
        where=f"{market} {horizon}; not a trade entry, no live T1/T2 as orders",
        when=when_known,
        invalidation=invalidation,
        q1_instrument_profile_timeframe=f"{symbol} research radar {horizon} ({market})",
        q2_state_classification=public_state,
        q3_why_entered_now=(
            _facts_line(ok_facts, codes_only=True)
            if ok_facts
            else "UNKNOWN_ONLY_UNPROVEN_SLOTS"
        ),
        q4_supporting_families=(
            ", ".join(
                family.family
                for family in fusion.families
                if family.status == "SUPPORT"
            )
            or "UNKNOWN_NO_SUPPORTING_FAMILY_YET"
        ),
        q5_strongest_contradiction=contradiction,
        q6_missing_proof_and_state_change_condition=(
            f"missing/unknown: {'; '.join(unknown_codes) if unknown_codes else 'NONE'}; "
            f"state changes only after named sources activate; restriction={restriction_state}"
        ),
        q7_run_completeness_freshness=(
            f"completeness={completeness:.2f} freshness={freshness}"
        ),
        q8_what_changed_vs_prior_run=what_changed,
    )


__all__ = ["ExplainV1", "build_explain"]
