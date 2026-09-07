"""File A S7 (SEL-008): one public-state owner over the S6 resolution.

PRF-003 NSE swing continuation is the LIVE profile:
- required family: STRUCTURE support > 0 (closed bars, hash-matched R14);
- alternative gate: PARTICIPATION support > 0 OR EVENT support > 0 OR
  RS-above-median companion (when an RS source is available; unavailable RS
  simply cannot satisfy the alternative — fail closed, never invented);
- event blackout from macro_event_context last-good; unknown → WAIT;
- S2 weather regime UNKNOWN → WAIT_WEATHER_UNKNOWN flag (never a vote);
- AMENDMENT 2026-08-25: when the R2-B named-activation ledger has OBSERVED
  all five confirm-path last-goods current, rows that satisfy the full
  PRF-003 checklist may seat publicState=CONFIRMED for PRF-003 EOD. With
  sourceActivationReady=false CONFIRMED stays unreachable (regression).

Guidance fields (TRADE_GUIDANCE_LAW_2026-08-25):
- researchQuantity at the confirmation point (never executable);
- guidanceOrderTicket preview on CONFIRMED rows only;
- batch.intradayGuidanceConfirmed mirrors the data-lane intraday mode
  (ON_FREE / OPENALGO) — guidance only, never a public intraday state.

Ceiling: LIVE_S7_WATCH_WAIT_REJECT_ONLY when locked;
LIVE_S7_CONFIRMED_EOD_PRF003_NAMED_ONLY when activated.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .contracts import EvidenceDirection, SelectionState, stable_id
from .r5_live import R5StructureBatchV1, latest_r5_structure_batch
from .s4_structure_pack import (
    S4StructurePackBatchV1,
    build_s4_structure_pack,
)
from .s5_shortlist_enrichment import (
    S5EnrichmentBatchV1,
    build_s5_enrichment,
)
from .s6_family_resolution import (
    S6ResolutionBatchV1,
    S6ResolutionRowV1,
    build_s6_resolution,
)
from .tradability import (
    TradabilityBatchV1,
    TradabilityOutcome,
    TradabilityResultV1,
    build_tradability_batch,
)

SCHEMA_VERSION = "trendforge.s7-state.v1"
PROFILE_ID = "PRF-S7-STATE-GATES"
ACTIVE_PROFILE_ID = "PRF-003-SWING-EOD"
ACTIVE_PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_S7_WATCH_WAIT_REJECT_ONLY"
ACTIVATED_CEILING = "LIVE_S7_CONFIRMED_EOD_PRF003_NAMED_ONLY"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class S7IdeaCardV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    public_state: SelectionState
    evidence_direction: EvidenceDirection
    evidence_strength: float = Field(ge=0, le=1, default=0.0)
    evidence_strength_label: str = "Evidence strength - not win probability"
    family_support: dict[str, float]
    family_opposition: dict[str, float]
    missing_families: tuple[str, ...] = ()
    why: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    next_trigger: str | None = None
    invalidation_condition: str | None = None
    weather_regime: str | None = None
    fo_package_status: str | None = None
    options_package_status: str | None = None
    draft_confirmed_eligible: bool = False
    tradability_outcome: TradabilityOutcome = TradabilityOutcome.WAIT
    tradability_reason: str = "WAIT_TRADABILITY_NOT_EVALUATED"
    tradability_hash: str | None = None
    tradability: TradabilityResultV1 | None = None
    research_quantity: int | None = None
    research_qty_reason: str | None = None
    guidance_order_ticket: dict[str, Any] | None = None
    entry: None = None
    stop: None = None
    t1: None = None
    t2: None = None
    quantity: None = None

    @model_validator(mode="after")
    def enforce_card_law(self) -> "S7IdeaCardV1":
        if self.public_state is SelectionState.CONFIRMED:
            if not self.draft_confirmed_eligible:
                raise ValueError(
                    "S7 CONFIRMED requires the full PRF-003 draft checklist"
                )
            if self.tradability_outcome is not TradabilityOutcome.PASS:
                raise ValueError("S7 CONFIRMED requires tradability PASS")
        elif self.draft_confirmed_eligible and (
            self.public_state is not SelectionState.WAIT
        ):
            raise ValueError(
                "draftConfirmedEligible may only exist on WAIT rows"
            )
        return self


class S7StateBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    active_profile_id: str = ACTIVE_PROFILE_ID
    active_profile_version: str = ACTIVE_PROFILE_VERSION
    run_id: str
    run_hash: str
    s6_run_hash: str
    r2_run_hash: str
    r14_run_hash: str | None = None
    tradability_run_hash: str | None = None
    trading_date: str | None = None
    built_at: datetime | None = None
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    confirmed_count: int = 0
    draft_confirmed_eligible_count: int = Field(ge=0, default=0)
    intraday_guidance_confirmed: bool = False
    market_context_regime: str | None = None
    rows: tuple[S7IdeaCardV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def enforce_s7_law(self) -> "S7StateBatchV1":
        if self.can_unlock_confirmed:
            raise ValueError("S7 cannot unlock CONFIRMED via canUnlockConfirmed")
        confirmed_rows = [
            row for row in self.rows if row.public_state is SelectionState.CONFIRMED
        ]
        if self.source_activation_ready:
            if self.confirmed_count != len(confirmed_rows):
                raise ValueError(
                    "confirmedCount must equal the number of CONFIRMED rows"
                )
        else:
            # Regression lock: without the observed named activation,
            # CONFIRMED is unreachable and the count stays zero.
            if confirmed_rows or self.confirmed_count != 0:
                raise ValueError(
                    "CONFIRMED forbidden while sourceActivationReady is false"
                )
        for row in self.rows:
            if row.draft_confirmed_eligible and (
                row.public_state
                not in {SelectionState.WAIT, SelectionState.CONFIRMED}
            ):
                raise ValueError(
                    "draftConfirmedEligible may only exist on WAIT/CONFIRMED "
                    "rows (activation lock)"
                )
        return self


def _reasons(row6: S6ResolutionRowV1) -> tuple[list[str], bool]:
    """Return (why_codes, hard_reject)."""
    why: list[str] = list(row6.why)
    reject = row6.r2_public_state is SelectionState.REJECT
    if reject:
        why.insert(0, "R2_PUBLIC_REJECT")
    if row6.resolution_state is SelectionState.REJECT:
        reject = True
        why.insert(0, "S6_STRUCTURE_REJECT")
    return why, reject


def classify_row(
    *,
    row6: S6ResolutionRowV1,
    next_trigger: str | None,
    invalidation: str | None,
    has_structure_tags: bool,
    ca_break: bool,
    blackout_known_clear: bool,
    rs_ok: bool | None,
    weather_unknown: bool,
    tradability_outcome: TradabilityOutcome = TradabilityOutcome.PASS,
    tradability_reasons: tuple[str, ...] = (),
    activation_ready: bool = False,
) -> tuple[SelectionState, list[str], bool]:
    """Pure PRF-003 gate. Returns (state, reasons, draft_confirmed_eligible).

    rs_ok: True when an available RS companion beats the PIT median;
    None when no RS source is wired (it then cannot satisfy anything).
    activation_ready: the OBSERVED named-activation ledger state; only a
    True value may seat CONFIRMED, and every fail-closed override still
    outranks it.
    """
    why: list[str] = []
    reasons, hard_reject = _reasons(row6)
    why.extend(reasons)
    if ca_break:
        why.append("WAIT_CA_IDENTITY_BREAK")

    families = row6.families
    structure_support = families.get("STRUCTURE").support if "STRUCTURE" in families else 0
    participation = families.get("PARTICIPATION").support if "PARTICIPATION" in families else 0
    event = families.get("EVENT_AND_SPONSOR").support if "EVENT_AND_SPONSOR" in families else 0

    alt_ok = participation > 0 or event > 0 or bool(rs_ok)
    if rs_ok is None:
        why.append("PRF003_RS_UNAVAILABLE")

    conflict = bool(row6.conflict)

    # Fail-closed overrides — these seat WAIT no matter what.
    if weather_unknown:
        why.append("WAIT_WEATHER_UNKNOWN")
    if not blackout_known_clear:
        why.append("WAIT_EVENT_BLACKOUT_UNKNOWN")
    if ca_break:
        why.append("WAIT_CA_IDENTITY_BREAK")
    if conflict:
        why.append("WAIT_CONFLICT_ABOVE_THRESHOLD")

    fail_closed = (
        weather_unknown
        or (not blackout_known_clear)
        or ca_break
        or conflict
    )

    if tradability_outcome is TradabilityOutcome.REJECT:
        hard_reject = True
        why.extend(tradability_reasons or ("REJECT_TRADABILITY",))
    elif tradability_outcome is TradabilityOutcome.WAIT:
        fail_closed = True
        why.extend(tradability_reasons or ("WAIT_TRADABILITY",))

    if hard_reject:
        state = SelectionState.REJECT
        draft = False
    elif fail_closed:
        state = SelectionState.WAIT
        draft = False
    elif structure_support <= 0:
        # Nothing structural formed yet.
        state = SelectionState.WATCH if has_structure_tags else SelectionState.WAIT
        why.append(
            "WATCH_FORMING_STRUCTURE_TAGS"
            if state is SelectionState.WATCH
            else "WAIT_MISSING_STRUCTURE"
        )
        draft = False
    elif not alt_ok:
        # Structure exists but the independent companion family is missing.
        state = SelectionState.WATCH if has_structure_tags else SelectionState.WAIT
        why.append(
            "WATCH_FORMING_STRUCTURE_TAGS"
            if state is SelectionState.WATCH
            else "WAIT_MISSING_PARTICIPATION_OR_EVENT"
        )
        draft = False
    elif not activation_ready:
        # Every PRF-003 research condition holds; the ONLY remaining blocker
        # is the activation lock, so the row is draft-CONFIRMED-eligible.
        state = SelectionState.WAIT
        why.append("WAIT_SOURCE_ACTIVATION")
        draft = True
    else:
        # Amendment path: named ledger observed all five last-goods current,
        # PRF-003 checklist fully satisfied → public research CONFIRMED.
        state = SelectionState.CONFIRMED
        why.append("CONFIRMED_PRF003_EOD_NAMED_SOURCES")
        draft = True

    return state, why, draft


def _observed_activation_ready() -> bool:
    """Read the R2-B named-activation ledger. Never invent the flag."""
    try:
        from .r2b_live import latest_r2b_named_activation

        stored = latest_r2b_named_activation()
    except Exception:
        return False
    return bool(stored is not None and stored.source_activation_ready)


def _intraday_guidance(lane: Any) -> bool:
    mode = getattr(lane, "intraday_mode", None)
    return mode in {"ON_FREE", "OPENALGO"}


def _paper_plan_for(
    *,
    symbol: str,
    public_state: SelectionState,
    evidence_direction: str,
    draft_confirmed_eligible: bool,
    invalidation_condition: str | None,
    trading_date: Any,
    regime_label: str | None,
) -> tuple[dict[str, Any], float | None]:
    """Compute the paper research plan (qty 0 unless geometry is provable)."""
    from .guidance_oms import compute_paper_plan

    return compute_paper_plan(
        symbol=symbol,
        public_state=public_state.value,
        evidence_direction=evidence_direction,
        draft_confirmed_eligible=draft_confirmed_eligible,
        invalidation_condition=invalidation_condition,
        trading_date=trading_date,
        regime_label=regime_label,
    )


def build_s7_state(
    *,
    r5: R5StructureBatchV1 | None = None,
    s4: S4StructurePackBatchV1 | None = None,
    s5: S5EnrichmentBatchV1 | None = None,
    s6: S6ResolutionBatchV1 | None = None,
    weather: Any = None,
    event_snapshot: Any | None = None,
    activation_ready: bool | None = None,
    lane: Any = None,
    tradability: TradabilityBatchV1 | None = None,
    allow_enrichment_fallback: bool = True,
) -> S7StateBatchV1:
    """Assemble hash-matched R5→S4→S5→S6 and project the public states.

    activation_ready defaults to an OBSERVED read of the persisted R2-B
    named-activation ledger; callers may pass it explicitly (tests, replay).
    """
    batch5 = r5 if r5 is not None else latest_r5_structure_batch()
    if batch5 is None:
        raise ValueError("WAIT_S7_R5_NOT_READY")
    pack = s4 if s4 is not None else build_s4_structure_pack(r5=batch5)
    s5_batch = s5 if s5 is not None else None
    try:
        if s5_batch is None and allow_enrichment_fallback:
            s5_batch = build_s5_enrichment(s4=pack)
    except ValueError:
        s5_batch = None

    resolution = s6 if s6 is not None else build_s6_resolution(
        s4=pack, r5=batch5, s5=s5_batch, weather=weather
    )

    tradability_batch = tradability or build_tradability_batch(
        symbols=(row.symbol for row in resolution.rows),
        profile_id="PRF-003",
        decision_at=(resolution.built_at or datetime.now().astimezone()),
    )
    tradability_by_symbol = {
        row.symbol.upper(): row for row in tradability_batch.rows
    }

    if activation_ready is None:
        activation_ready = _observed_activation_ready()

    intraday_ok = _intraday_guidance(lane)

    blackout_known_clear = (
        getattr(event_snapshot, "state", None) == "RESEARCH_ONLY"
        if event_snapshot is not None
        else False
    )

    pack_by_symbol = {row.symbol: row for row in pack.rows}
    s5_by_symbol = {
        row.symbol.upper(): row for row in (s5_batch.rows if s5_batch else ())
    }

    rows: list[S7IdeaCardV1] = []
    draft_count = 0
    for row6 in resolution.rows:
        prow = pack_by_symbol.get(row6.symbol)
        erow = s5_by_symbol.get(row6.symbol.upper())
        next_trigger = getattr(prow, "next_trigger", None) if prow else None
        invalidation = getattr(prow, "invalidation_condition", None) if prow else None
        has_tags = bool(getattr(prow, "detected_setups", ()) ) if prow else False
        ca_state = (getattr(prow, "ca_state", "") or "") if prow else ""
        ca_break = ("BREAK" in ca_state.upper()) or ("IDENTITY" in ca_state.upper() and "CONFLICT" in ca_state.upper())

        weather_unknown = bool(
            resolution.market_context is None
            or (resolution.market_context.regime_label in (None, "", "UNKNOWN"))
        )
        restriction = tradability_by_symbol.get(row6.symbol.upper())
        if restriction is None:
            restriction_outcome = TradabilityOutcome.WAIT
            restriction_reasons = ("WAIT_TRADABILITY_SYMBOL_MISSING",)
        else:
            restriction_outcome = restriction.outcome
            restriction_reasons = restriction.reason_codes

        state, why, draft = classify_row(
            row6=row6,
            next_trigger=next_trigger,
            invalidation=invalidation,
            has_structure_tags=has_tags,
            ca_break=ca_break,
            blackout_known_clear=blackout_known_clear,
            rs_ok=None,
            weather_unknown=weather_unknown,
            tradability_outcome=restriction_outcome,
            tradability_reasons=restriction_reasons,
            activation_ready=bool(activation_ready),
        )
        if draft:
            draft_count += 1

        fo_status = getattr(erow, "fo_package", None) and erow.fo_package.status or None
        opt_status = getattr(erow, "options_package", None) and erow.options_package.status or None

        plan, _close = _paper_plan_for(
            symbol=row6.symbol,
            public_state=state,
            evidence_direction=str(row6.evidence_direction),
            draft_confirmed_eligible=draft,
            invalidation_condition=invalidation,
            trading_date=resolution.trading_date,
            regime_label=(
                resolution.market_context.regime_label
                if resolution.market_context else None
            ),
        )
        ticket = None
        if state is SelectionState.CONFIRMED:
            from .guidance_oms import build_paper_ticket

            ticket = build_paper_ticket(
                symbol=row6.symbol,
                public_state=state.value,
                plan=plan,
            ).model_dump(mode="json", by_alias=True)

        rows.append(
            S7IdeaCardV1(
                symbol=row6.symbol,
                public_state=state,
                evidence_direction=row6.evidence_direction,
                evidence_strength=row6.evidence_strength,
                family_support={
                    k: v.support for k, v in row6.families.items()
                },
                family_opposition={
                    k: v.oppose for k, v in row6.families.items()
                },
                missing_families=row6.missing_families,
                why=tuple(why) + tuple(row6.why_unknown),
                missing_evidence=tuple(row6.why_unknown),
                next_trigger=next_trigger,
                invalidation_condition=invalidation,
                weather_regime=(
                    resolution.market_context.regime_label
                    if resolution.market_context else None
                ),
                fo_package_status=str(fo_status) if fo_status else None,
                options_package_status=str(opt_status) if opt_status else None,
                draft_confirmed_eligible=draft,
                tradability_outcome=restriction_outcome,
                tradability_reason=(
                    restriction.primary_reason
                    if restriction is not None
                    else "WAIT_TRADABILITY_SYMBOL_MISSING"
                ),
                tradability_hash=(
                    restriction.tradability_hash if restriction is not None else None
                ),
                tradability=restriction,
                research_quantity=int(plan.get("researchQuantity") or 0),
                research_qty_reason=str(plan.get("reason") or "") or None,
                guidance_order_ticket=ticket,
            )
        )

    identity_payload = {
        "s6RunHash": resolution.run_hash,
        "tradabilityRunHash": tradability_batch.run_hash,
        "activeProfileId": ACTIVE_PROFILE_ID,
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    regime = (
        resolution.market_context.regime_label
        if resolution.market_context else None
    )
    confirmed_count = sum(
        1 for row in rows if row.public_state is SelectionState.CONFIRMED
    )
    warnings = ["Research state - not an order."]
    if activation_ready:
        warnings.append(
            "PRF-003 EOD public CONFIRMED active via named sources; "
            "NO BROKER ORDERS. Guidance OMS preview only."
        )
    else:
        warnings.append("CONFIRMED unreachable while sourceActivationReady is false.")
    return S7StateBatchV1(
        run_id=stable_id("s7-state", resolution.run_id, run_hash),
        run_hash=run_hash,
        s6_run_hash=resolution.run_hash,
        r2_run_hash=resolution.r2_run_hash,
        r14_run_hash=resolution.r14_run_hash,
        tradability_run_hash=tradability_batch.run_hash,
        trading_date=resolution.trading_date,
        built_at=resolution.built_at,
        acceptance_ceiling=(
            ACTIVATED_CEILING if activation_ready else ACCEPTANCE_CEILING
        ),
        source_activation_ready=bool(activation_ready),
        confirmed_count=confirmed_count,
        draft_confirmed_eligible_count=draft_count,
        intraday_guidance_confirmed=intraday_ok,
        market_context_regime=regime,
        rows=tuple(rows),
        warnings=tuple(warnings),
    )


def latest_s7_state() -> S7StateBatchV1 | None:
    from .store import latest_selection_payload

    payload = latest_selection_payload(PROFILE_ID)
    return S7StateBatchV1.model_validate(payload) if payload else None


__all__ = [
    "ACCEPTANCE_CEILING",
    "ACTIVATED_CEILING",
    "ACTIVE_PROFILE_ID",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "S7IdeaCardV1",
    "S7StateBatchV1",
    "build_s7_state",
    "classify_row",
    "latest_s7_state",
]
