"""Unit tests for M-Factor claim merge (R5 STRUCTURE + cash PARTICIPATION).

Authority: M_FACTOR_USEFUL_FUS009_WIRING_GLM_PROMPT.md (2026-08-23).
Golden rule: identical merged claims produce identical FUS-009 outputs, and
adding an accepted FTR-006 structure claim raises only the matching
hypothesis. Persisted R5 metrics in these fixtures come from a first
analyze_closed_bar_structure pass, exactly like live R5 persistence.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from trendforge_api.selection.cash_a4_history import CashRawSessionBar
from trendforge_api.selection.contracts import (
    DataMode,
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    InstrumentIdentity,
    SelectionState,
    StateCeiling,
)
from trendforge_api.selection.m_factor_claims import (
    MergedSymbolClaims,
    index_session_conflict,
    merge_symbol_claims,
    rebuild_r5_claims,
    structure_how_text,
    what_label,
)
from trendforge_api.selection.r14_live import R14CaJoinRowV1
from trendforge_api.selection.r5_live import R5StructureRowV1, _closed_bars, _profile
from trendforge_api.selection.r3_live import _r2_gate, live_profile
from trendforge_api.selection.resolver import resolve_evidence
from trendforge_api.selection.structure import (
    StructureMetrics,
    analyze_closed_bar_structure,
)
from trendforge_api.source_contracts import (
    SourceResult,
    SourceResultState,
    SourceRole,
)

IST = ZoneInfo("Asia/Kolkata")
DECISION_AT = datetime(2026, 8, 21, 11, 0, tzinfo=UTC)  # 16:30 IST, after close


def _source_result() -> SourceResult:
    return SourceResult(
        source_id="nse_bhavcopy_eod",
        contract_version="1.0.0",
        role=SourceRole.OFFICIAL_GATE,
        state=SourceResultState.STRUCTURED_OK,
        record_count=1,
        data_date=date(2026, 8, 21),
        published_at=DECISION_AT - timedelta(hours=2),
        received_at=DECISION_AT - timedelta(hours=1),
        available_at=DECISION_AT - timedelta(hours=1),
        retrieved_at=DECISION_AT - timedelta(hours=1),
        schema_version="1.0.0",
        parser_version="1.0.0",
        revision_id="rev-1",
        artifact_hash="a" * 64,
        freshness="FRESH",
    )


def _instrument() -> InstrumentIdentity:
    return InstrumentIdentity.create(
        exchange="NSE", segment="EQ", symbol="FIXTURE", series="EQ"
    )


def _raw_bars(direction: str = "bull", *, sessions: int = 24) -> list[CashRawSessionBar]:
    instrument_id = _instrument().instrument_id
    bars: list[CashRawSessionBar] = []
    start = date(2026, 7, 20)
    for index in range(sessions):
        close = 100.0 + index * 0.05
        volume = 1_000_000.0 + index * 1_000.0
        if direction == "bull" and index == sessions - 1:
            close = 130.0
            volume = 3_000_000.0
        elif direction == "bear" and index == sessions - 1:
            close = 70.0
            volume = 3_000_000.0
        bars.append(
            CashRawSessionBar(
                bar_id=f"bar-{index}",
                instrument_id=instrument_id,
                symbol="FIXTURE",
                trade_date=start + timedelta(days=index),
                artifact_hash=f"{index:064d}",
                series_id="raw-series",
                open=close - 0.5,
                high=close + 0.5,
                low=close - 1.0,
                close=close,
                previous_close=close - 0.05,
                volume=volume,
            )
        )
    return bars


def _ca_row() -> R14CaJoinRowV1:
    return R14CaJoinRowV1(
        candidate_id="cand-fixture",
        symbol="FIXTURE",
        display_order=1,
        r2_public_state=SelectionState.WATCH,
        join_status="NONE",
        ca_state="NONE",
        raw_series_id="raw-series",
        identity_continuity="SAME_INSTRUMENT",
        why_wait=("R14_LIVE_WAIT_CEILING",),
    )


def _r5_row_from_analysis(
    analysis_direction: EvidenceDirection,
    bars: list[CashRawSessionBar],
) -> tuple[R5StructureRowV1, StructureMetrics]:
    """Persisted-style R5 row whose metrics come from a real analysis pass."""
    ca = _ca_row()
    closed, waits = _closed_bars(
        instrument=_instrument(), raw_bars=bars, decision_at=DECISION_AT, ca_row=ca
    )
    assert not waits
    profile = _profile(analysis_direction)
    assert profile is not None
    analysis = analyze_closed_bar_structure(
        instrument=_instrument(),
        bars=closed,
        source_result=_source_result(),
        profile=profile,
        decision_at=DECISION_AT,
    )
    setups: list[str] = []
    if analysis.metrics.accepted:
        setups.append("CLOSED_BAR_BREAKOUT")
    if analysis.metrics.narrow_range:
        setups.append(f"NR{profile.nr_window}")
    if (
        analysis.metrics.relative_volume is not None
        and analysis.metrics.relative_volume >= profile.min_rvol
    ):
        setups.append("RVOL")
    row = R5StructureRowV1(
        candidate_id="cand-fixture",
        symbol="FIXTURE",
        instrument_id="ins_fixture",
        r2_public_state=SelectionState.WATCH,
        structure_state=SelectionState.WAIT,
        evidence_direction=analysis_direction,
        display_order=1,
        source_mode="OFFICIAL_LAST_GOOD",
        history_count=len(closed),
        ca_state="NONE",
        index_context_state="CURRENT",
        detected_setups=tuple(setups),
        gate_codes=("R5_LIVE_WAIT_CEILING",),
        why_wait=("R5_LIVE_WAIT_CEILING",),
        metrics=analysis.metrics,
    )
    return row, analysis.metrics


def _rebuild(row: R5StructureRowV1, bars: list[CashRawSessionBar]):
    return rebuild_r5_claims(
        r5_row=row,
        instrument=_instrument(),
        raw_bars=bars,
        ca_row=_ca_row(),
        source_result=_source_result(),
        decision_at=DECISION_AT,
    )


def _resolve(merged: MergedSymbolClaims, direction: EvidenceDirection):
    return resolve_evidence(
        profile=live_profile(),
        decision_at=DECISION_AT,
        evidence_direction=direction,
        claims=merged.claims,
        facts=merged.facts,
        source_results=(_source_result(),),
        completeness=1.0,
        existing_gates=(_r2_gate(SelectionState.WATCH),),
        data_mode=DataMode.EOD_RESEARCH,
    )


def test_rebuild_mints_structure_and_participation_for_accepted_breakout() -> None:
    row, _metrics = _r5_row_from_analysis(EvidenceDirection.BULLISH, _raw_bars("bull"))
    assert "CLOSED_BAR_BREAKOUT" in row.detected_setups
    rebuild = _rebuild(row, _raw_bars("bull"))
    features = {claim.feature_id for claim in rebuild.claims}
    assert {"FTR-006", "FTR-017"} <= features
    assert rebuild.codes == ()
    assert all(claim.can_support_confirmed is False for claim in rebuild.claims)
    assert rebuild.reference_level is not None


def test_rebuild_withholds_on_drift() -> None:
    row, _metrics = _r5_row_from_analysis(EvidenceDirection.BULLISH, _raw_bars("bull"))
    rebuild = _rebuild(row, _raw_bars("bear"))  # bars no longer reproduce R5
    assert rebuild.claims == ()
    assert rebuild.codes == ("WAIT_R5_REBUILD_DRIFT",)


def test_rebuild_skips_rows_without_setups() -> None:
    row, _ = _r5_row_from_analysis(EvidenceDirection.BULLISH, _raw_bars("bull"))
    empty = row.model_copy(update={"detected_setups": (), "metrics": None})
    rebuild = _rebuild(empty, _raw_bars("bull"))
    assert rebuild.claims == () and rebuild.codes == ("STRUCTURE_NOT_EVALUATED",)


def test_ftr006_lifts_only_the_matching_hypothesis() -> None:
    row, _ = _r5_row_from_analysis(EvidenceDirection.BULLISH, _raw_bars("bull"))
    structure = _rebuild(row, _raw_bars("bull"))
    merged = merge_symbol_claims(cash_claims=(), cash_facts=(), structure=structure)
    cash_only = merge_symbol_claims(cash_claims=(), cash_facts=())

    cash_long = _resolve(cash_only, EvidenceDirection.BULLISH)
    merged_long = _resolve(merged, EvidenceDirection.BULLISH)
    merged_short = _resolve(merged, EvidenceDirection.BEARISH)

    assert cash_long.evidence_strength == 0.0
    # STRUCTURE (0.30) + participation from FTR-017 both vote long.
    assert merged_long.evidence_strength > 0.30
    # Bullish structure never feeds the short hypothesis.
    assert merged_short.evidence_strength == 0.0
    # Golden determinism: identical claims -> identical strengths.
    assert _resolve(merged, EvidenceDirection.BULLISH).evidence_strength == merged_long.evidence_strength


def test_ftr017_and_cash_claim_take_group_max_not_sum() -> None:
    row, _ = _r5_row_from_analysis(EvidenceDirection.BULLISH, _raw_bars("bull"))
    structure = _rebuild(row, _raw_bars("bull"))
    rvol_claim = next(c for c in structure.claims if c.feature_id == "FTR-017")
    cash_claim = EvidenceClaim.create(
        feature_id="FTR-040",
        feature_version="1.0.0",
        family=EvidenceFamily.PARTICIPATION,
        correlation_group="CG_ACTIVITY_SESSION",
        direction=EvidenceDirection.BULLISH,
        strength_before_caps=0.5,
        source_fact_ids=structure.claims[0].source_fact_ids,
        authority=structure.claims[0].authority,
        available_at=structure.claims[0].available_at,
        state_ceiling=StateCeiling.WATCH,
        can_support_confirmed=False,
        explanation="cash session participation fixture",
    )
    merged = merge_symbol_claims(
        cash_claims=(cash_claim,), cash_facts=(), structure=structure
    )
    run = _resolve(merged, EvidenceDirection.BULLISH)
    participation = next(
        family for family in run.families if family.family is EvidenceFamily.PARTICIPATION
    )
    assert participation.support_strength == max(rvol_claim.strength_before_caps, 0.5)


def test_bearish_structure_creates_short_side_evidence() -> None:
    row, _ = _r5_row_from_analysis(EvidenceDirection.BEARISH, _raw_bars("bear"))
    structure = _rebuild(row, _raw_bars("bear"))
    assert structure.claims
    assert all(claim.direction is EvidenceDirection.BEARISH for claim in structure.claims)
    merged = merge_symbol_claims(cash_claims=(), cash_facts=(), structure=structure)
    assert _resolve(merged, EvidenceDirection.BEARISH).evidence_strength > 0.30
    assert _resolve(merged, EvidenceDirection.BULLISH).evidence_strength == 0.0


def test_index_session_conflict_heuristic() -> None:
    assert index_session_conflict(row_class="Bull", index_change_percent=-1.4) is True
    assert index_session_conflict(row_class="Strong Bull", index_change_percent=-2.0) is True
    assert index_session_conflict(row_class="Bear", index_change_percent=1.5) is True
    assert index_session_conflict(row_class="Bull", index_change_percent=-0.4) is False
    assert index_session_conflict(row_class="Neutral", index_change_percent=-3.0) is False
    assert index_session_conflict(row_class="Bull", index_change_percent=None) is False
    # A suspect parser artifact (no real NIFTY session moves 20%) is unproven,
    # never a conflict.
    assert index_session_conflict(row_class="Bear", index_change_percent=20.15) is False


def test_what_label_slots() -> None:
    assert what_label(
        deal_summary="2026-08-20 BULK BUY qty=1000000 client=ACME", deal_tag="NAMED_DEAL"
    ).startswith("NAMED_DEAL")
    assert what_label(
        deal_summary="2026-08-20 BULK UNNAMED_DEAL", deal_tag=None
    ).startswith("DEAL_UNNAMED_OR_UNALIGNED")
    assert what_label(deal_summary=None, deal_tag=None) == "UNKNOWN_NO_LARGE_DEAL_ROW"


def test_how_text_names_claim_ids_or_withhold_code() -> None:
    row, _ = _r5_row_from_analysis(EvidenceDirection.BULLISH, _raw_bars("bull"))
    structure = _rebuild(row, _raw_bars("bull"))
    merged = merge_symbol_claims(cash_claims=(), cash_facts=(), structure=structure)
    how = structure_how_text(
        merged,
        structure_claim_ids=tuple(claim.claim_id for claim in structure.claims),
        structure_state="WAIT",
    )
    assert "FTR-006" in how and "STRUCTURE voted" in how and "reference level" in how

    withheld = MergedSymbolClaims(structure_codes=("WAIT_R5_REBUILD_DRIFT",))
    assert structure_how_text(withheld).startswith("STRUCTURE_WITHHELD (WAIT_R5_REBUILD_DRIFT)")
    plain = merge_symbol_claims(cash_claims=(), cash_facts=())
    assert structure_how_text(plain).startswith("STRUCTURE_NOT_EVALUATED")
