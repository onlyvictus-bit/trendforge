"""File A S7 (SEL-008) state-gate tests: one public-state owner, WAIT ceiling."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trendforge_api.selection.contracts import EvidenceDirection, SelectionState, stable_id
from trendforge_api.selection.s7_state_gates import (
    S7IdeaCardV1,
    S7StateBatchV1,
    build_s7_state,
    classify_row,
)
from trendforge_api.selection.tradability import (
    TradabilityOutcome,
    pass_fixture_batch,
)
from trendforge_api.selection.s4_structure_pack import build_s4_structure_pack
from trendforge_api.selection.s6_family_resolution import (
    S6FamilyStrengthV1,
    S6MarketContextBlockV1,
    S6ResolutionBatchV1,
    S6ResolutionRowV1,
)


def _family(name: str, support: float, oppose: float = 0.0):
    return name, S6FamilyStrengthV1(support=support, oppose=oppose, weight=0.1)


def _row6(
    *,
    symbol: str = "TEST",
    structure: float = 0.8,
    participation: float = 0.0,
    event: float = 0.0,
    conflict: bool = False,
    r2_state: SelectionState = SelectionState.WATCH,
    resolution_state: SelectionState | None = None,
    why: tuple[str, ...] = (),
) -> S6ResolutionRowV1:
    fams = dict(
        [
            _family("STRUCTURE", structure),
            _family("PARTICIPATION", participation),
            _family("EVENT_AND_SPONSOR", event),
        ]
    )
    return S6ResolutionRowV1(
        candidate_id=f"c-{symbol}",
        symbol=symbol,
        r2_public_state=r2_state,
        resolution_state=(
            resolution_state
            if resolution_state is not None
            else SelectionState.WAIT
        ),
        evidence_direction=EvidenceDirection.BULLISH,
        display_order=1,
        families=fams,
        conflict=conflict,
        evidence_strength=0.4,
        why=why,
    )


def _classify(row6, **kw):
    kw.setdefault("next_trigger", None)
    kw.setdefault("invalidation", None)
    kw.setdefault("has_structure_tags", True)
    kw.setdefault("ca_break", False)
    kw.setdefault("blackout_known_clear", True)
    kw.setdefault("rs_ok", None)
    kw.setdefault("weather_unknown", False)
    return classify_row(row6=row6, **kw)


def test_activation_false_forces_wait_not_confirmed() -> None:
    row = _row6(structure=0.9, participation=0.9)
    state, why, draft = _classify(row)
    assert state is SelectionState.WAIT
    assert "WAIT_SOURCE_ACTIVATION" in why
    assert draft is True  # structural checklist passes; only the lock remains


def test_missing_structure_waits_and_cannot_watch() -> None:
    row = _row6(structure=0.0, participation=0.9)
    state, why, draft = _classify(row, has_structure_tags=False)
    assert state is SelectionState.WAIT
    assert "WAIT_MISSING_STRUCTURE" in why
    assert draft is False


def test_participation_or_event_alternative() -> None:
    part_only = _row6(participation=0.5)
    event_only = _row6(event=0.4)
    neither = _row6()
    assert _classify(part_only)[0] is SelectionState.WAIT  # locked, but alt OK
    assert _classify(event_only)[0] is SelectionState.WAIT
    state_none, why_none, draft_none = _classify(neither)
    # Forming tags promote to WATCH; the missing-family code stays visible.
    assert state_none is SelectionState.WATCH
    assert "WATCH_FORMING_STRUCTURE_TAGS" in why_none
    assert draft_none is False

    no_tags_state, no_tags_why, _ = _classify(neither, has_structure_tags=False)
    assert no_tags_state is SelectionState.WAIT
    assert "WAIT_MISSING_PARTICIPATION_OR_EVENT" in no_tags_why


def test_rs_companion_satisfies_alternative_when_available() -> None:
    row = _row6()
    state, _, draft = _classify(row, rs_ok=True)
    assert state is SelectionState.WAIT  # still activation-locked
    assert draft is True
    state_none, _, draft_none = _classify(row, rs_ok=None)
    assert draft_none is False


def test_weather_unknown_is_fail_closed_flag_not_vote() -> None:
    row = _row6(structure=0.9, participation=0.9)
    state, why, _ = _classify(row, weather_unknown=True)
    assert state is SelectionState.WAIT
    assert "WAIT_WEATHER_UNKNOWN" in why


def test_blackout_unknown_fails_closed() -> None:
    row = _row6(structure=0.9, participation=0.9)
    state, why, _ = _classify(row, blackout_known_clear=False)
    assert state is SelectionState.WAIT
    assert "WAIT_EVENT_BLACKOUT_UNKNOWN" in why


def test_conflict_seats_wait_never_buy_side() -> None:
    row = _row6(conflict=True)
    state, why, _ = _classify(row)
    assert state is SelectionState.WAIT
    assert any("CONFLICT" in c for c in why)


def test_reject_paths() -> None:
    banned = _row6(r2_state=SelectionState.REJECT)
    struct_rej = _row6(resolution_state=SelectionState.REJECT)
    for row in (banned, struct_rej):
        state, _, draft = _classify(row)
        assert state is SelectionState.REJECT
        assert draft is False


def test_draft_eligible_never_becomes_confirmed_state() -> None:
    row = _row6(structure=0.9, participation=0.9)
    card = S7IdeaCardV1(
        symbol="X",
        public_state=SelectionState.WAIT,
        evidence_direction=row.evidence_direction,
        family_support={"STRUCTURE": 0.9},
        family_opposition={},
        draft_confirmed_eligible=True,
    )
    assert card.public_state is SelectionState.WAIT
    assert card.entry is None and card.quantity is None
    with pytest.raises(ValueError):
        S7IdeaCardV1(
            symbol="X",
            public_state=SelectionState.CONFIRMED,
            evidence_direction=EvidenceDirection.BULLISH,
            family_support={},
            family_opposition={},
        )


def _minimal_batch(rows: tuple[S7IdeaCardV1, ...], **overrides) -> S7StateBatchV1:
    base = dict(
        run_id="r",
        run_hash="h",
        s6_run_hash="s6h",
        r2_run_hash="r2h",
        rows=rows,
    )
    base.update(overrides)
    return S7StateBatchV1(**base)


def test_batch_law_validators() -> None:
    card = S7IdeaCardV1(
        symbol="X",
        public_state=SelectionState.WAIT,
        evidence_direction=EvidenceDirection.BULLISH,
        family_support={},
        family_opposition={},
    )
    ok = _minimal_batch((card,))
    assert ok.confirmed_count == 0 and ok.source_activation_ready is False
    # Amendment: the observed activation flag alone unlocks nothing.
    flagged = _minimal_batch((card,), source_activation_ready=True)
    assert flagged.confirmed_count == 0
    with pytest.raises(ValueError):
        _minimal_batch((card,), can_unlock_confirmed=True)


def test_options_strip_never_upgrades_state() -> None:
    row = _row6(participation=0.5)
    a = _classify(row)[0]
    b = _classify(row)[0]  # options are not inputs to classify at all
    assert a is b


def test_weather_context_block_display_only() -> None:
    block = S6MarketContextBlockV1(regime_label="RISK_ON")
    assert block.can_support_confirmed is False


# ---------------------------------------------------------------------------
# R2-B activation amendment (2026-08-25): CONFIRMED allowed only when the
# named activation ledger observed all five last-goods current.
# ---------------------------------------------------------------------------


def test_activation_true_seats_confirmed_for_prf003() -> None:
    row = _row6(structure=0.9, participation=0.9)
    state, why, draft = _classify(row, activation_ready=True)
    assert state is SelectionState.CONFIRMED
    assert "CONFIRMED_PRF003_EOD_NAMED_SOURCES" in why
    assert draft is True


def test_fail_closed_overrides_beat_activation_ready() -> None:
    ready_row = _row6(structure=0.9, participation=0.9)
    banned = _row6(structure=0.9, participation=0.9, r2_state=SelectionState.REJECT)
    ca_break_row = _row6(structure=0.9, participation=0.9)
    blackout_row = _row6(structure=0.9, participation=0.9)
    assert _classify(ready_row, activation_ready=True, ca_break=False)[
        0
    ] is SelectionState.CONFIRMED
    assert _classify(banned, activation_ready=True)[0] is SelectionState.REJECT
    state_ca, why_ca, _ = _classify(
        ca_break_row, activation_ready=True, ca_break=True
    )
    assert state_ca is SelectionState.WAIT
    assert "WAIT_CA_IDENTITY_BREAK" in why_ca
    state_bo, why_bo, _ = _classify(
        blackout_row, activation_ready=True, blackout_known_clear=False
    )
    assert state_bo is SelectionState.WAIT
    assert "WAIT_EVENT_BLACKOUT_UNKNOWN" in why_bo


def test_missing_r14_wait_ca_blocks_even_when_ready() -> None:
    # A WAIT_CA row carries ca_break=True from the pack; it must never confirm.
    row = _row6(structure=0.9, participation=0.9)
    state, why, draft = _classify(row, activation_ready=True, ca_break=True)
    assert state is SelectionState.WAIT
    assert draft is False


def test_card_confirmed_requires_draft_eligible() -> None:
    with pytest.raises(ValueError):
        S7IdeaCardV1(
            symbol="X",
            public_state=SelectionState.CONFIRMED,
            evidence_direction=EvidenceDirection.BULLISH,
            family_support={"STRUCTURE": 0.9},
            family_opposition={},
            draft_confirmed_eligible=False,
        )
    card = S7IdeaCardV1(
        symbol="X",
        public_state=SelectionState.CONFIRMED,
        evidence_direction=EvidenceDirection.BULLISH,
        family_support={"STRUCTURE": 0.9},
        family_opposition={},
        draft_confirmed_eligible=True,
        tradabilityOutcome=TradabilityOutcome.PASS,
        research_quantity=10,
    )
    assert card.public_state is SelectionState.CONFIRMED
    assert card.entry is None and card.quantity is None  # geometry stays absent


def test_batch_confirmed_law_both_directions() -> None:
    wait_card = S7IdeaCardV1(
        symbol="W",
        public_state=SelectionState.WAIT,
        evidence_direction=EvidenceDirection.BULLISH,
        family_support={},
        family_opposition={},
        draft_confirmed_eligible=True,
    )
    confirmed_card = S7IdeaCardV1(
        symbol="C",
        public_state=SelectionState.CONFIRMED,
        evidence_direction=EvidenceDirection.BULLISH,
        family_support={"STRUCTURE": 0.9},
        family_opposition={},
        draft_confirmed_eligible=True,
        tradabilityOutcome=TradabilityOutcome.PASS,
    )
    # Locked: any CONFIRMED row or nonzero count stays forbidden (regression).
    with pytest.raises(ValueError):
        _minimal_batch((confirmed_card,))
    with pytest.raises(ValueError):
        _minimal_batch((wait_card,), confirmed_count=1)
    # Unlocked: CONFIRMED rows require sourceActivationReady and exact count.
    ok = _minimal_batch(
        (wait_card, confirmed_card),
        source_activation_ready=True,
        confirmed_count=1,
    )
    assert ok.confirmed_count == 1
    with pytest.raises(ValueError):
        _minimal_batch((confirmed_card,), source_activation_ready=True)


def test_build_s7_state_observes_named_ledger_by_default(
    tmp_path, monkeypatch
) -> None:
    """No persisted ledger -> default observation keeps the lock on."""
    from types import SimpleNamespace

    from trendforge_api.hybrid_v2.tests_support.fixtures import (
        persist_overlay_lineage as _lineage,
    )

    parts = _lineage(tmp_path, monkeypatch, with_structure=True)
    r5 = parts["structure"]
    pack = build_s4_structure_pack(r5=r5)
    six = _s6_batch_for(pack.rows[0].symbol)
    batch = build_s7_state(
        r5=r5,
        s4=pack,
        s6=six,
        event_snapshot=SimpleNamespace(state="RESEARCH_ONLY"),
        tradability=pass_fixture_batch(
            (pack.rows[0].symbol,),
            decision_at=datetime(2026, 8, 14, 17, 0, tzinfo=UTC),
        ),
    )
    assert batch.source_activation_ready is False
    assert batch.confirmed_count == 0
    assert all(row.public_state is not SelectionState.CONFIRMED for row in batch.rows)
    target = next(row for row in batch.rows if row.symbol == pack.rows[0].symbol)
    assert target.draft_confirmed_eligible is True
    assert "WAIT_SOURCE_ACTIVATION" in target.why


def test_build_s7_state_emits_confirmed_when_activated(
    tmp_path, monkeypatch
) -> None:
    from types import SimpleNamespace

    from trendforge_api.hybrid_v2.tests_support.fixtures import (
        persist_overlay_lineage as _lineage,
    )

    parts = _lineage(tmp_path, monkeypatch, with_structure=True)
    r5 = parts["structure"]
    pack = build_s4_structure_pack(r5=r5)
    symbol = pack.rows[0].symbol
    six = _s6_batch_for(symbol)
    batch = build_s7_state(
        r5=r5,
        s4=pack,
        s6=six,
        event_snapshot=SimpleNamespace(state="RESEARCH_ONLY"),
        activation_ready=True,
        tradability=pass_fixture_batch(
            (symbol,),
            decision_at=datetime(2026, 8, 14, 17, 0, tzinfo=UTC),
        ),
    )
    assert batch.confirmed_count >= 1
    target = next(row for row in batch.rows if row.symbol == symbol)
    assert target.public_state is SelectionState.CONFIRMED
    assert target.draft_confirmed_eligible is True
    assert "CONFIRMED_PRF003_EOD_NAMED_SOURCES" in target.why
    # Guidance fields exist; execution never appears.
    assert target.research_quantity is not None
    assert hasattr(target, "guidance_order_ticket")
    assert target.entry is None and target.quantity is None


def test_tradability_wait_and_reject_override_activation() -> None:
    row = _row6(structure=0.9, participation=0.9)
    wait_state, wait_why, wait_draft = _classify(
        row,
        activation_ready=True,
        tradability_outcome=TradabilityOutcome.WAIT,
        tradability_reasons=("WAIT_ASM_ACTIVE",),
    )
    reject_state, reject_why, reject_draft = _classify(
        row,
        activation_ready=True,
        tradability_outcome=TradabilityOutcome.REJECT,
        tradability_reasons=("REJECT_T2T_INTRADAY",),
    )
    assert wait_state is SelectionState.WAIT
    assert wait_draft is False
    assert "WAIT_ASM_ACTIVE" in wait_why
    assert reject_state is SelectionState.REJECT
    assert reject_draft is False
    assert "REJECT_T2T_INTRADAY" in reject_why


def _s6_batch_for(symbol: str):
    """Minimal hash-consistent S6 batch over one fixture row."""
    import hashlib

    fams = {
        "STRUCTURE": S6FamilyStrengthV1(support=0.9, oppose=0.0, weight=0.1),
        "PARTICIPATION": S6FamilyStrengthV1(support=0.8, oppose=0.0, weight=0.1),
        "EVENT_AND_SPONSOR": S6FamilyStrengthV1(support=0.0, oppose=0.0, weight=0.1),
    }
    row = S6ResolutionRowV1(
        candidate_id=f"c-{symbol}",
        symbol=symbol,
        r2_public_state=SelectionState.WATCH,
        resolution_state=SelectionState.WAIT,
        evidence_direction=EvidenceDirection.BULLISH,
        display_order=1,
        families=fams,
        conflict=False,
        evidence_strength=0.4,
    )
    run_hash = hashlib.sha256(symbol.encode()).hexdigest()
    return S6ResolutionBatchV1(
        active_profile_id="PRF-003-SWING-EOD",
        active_profile_version="1.0.0",
        run_id=stable_id("s6", "fixture", run_hash),
        run_hash=run_hash,
        r1_bundle_hash="a" * 64,
        r2_run_hash="b" * 64,
        trading_date="2026-08-14",
        built_at=datetime(2026, 8, 14, 17, 0, tzinfo=UTC),
        universe_count=1,
        market_context=S6MarketContextBlockV1(regime_label="RISK_ON"),
        rows=(row,),
    )
