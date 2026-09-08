"""S6 family resolution tests (File A SEL-007, WAIT ceiling)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import test_s4_structure_pack as s4f
from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.selection.contracts import (
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    NormalizedFact,
    PointInTimeLineage,
    SelectionState,
    StateCeiling,
)
from trendforge_api.selection.r5_live import build_r5_structure_batch, persist_r5_structure_batch
from trendforge_api.selection.s6_family_resolution import (
    ACCEPTANCE_CEILING,
    STRENGTH_LABEL,
    build_s6_resolution,
)
from trendforge_api.selection.attention_order import persist_attention_order
from trendforge_api.selection.inventory_source_bundle import (
    persist_inventory_source_bundle,
)
from trendforge_api.selection.r4_live import build_r4_identity_pin, persist_r4_identity_pin
from trendforge_api.selection.r14_live import build_r14_ca_join, persist_r14_ca_join
from trendforge_api.source_contracts import SourceResult, SourceResultState, SourceRole


DECISION_AT = s4f.DECISION_AT
TRADING_DATE = s4f.TRADING_DATE


def _synthetic_fact(instrument_id: str, tag: str) -> NormalizedFact:
    lineage = PointInTimeLineage(
        event_time=DECISION_AT - timedelta(hours=2),
        published_at=DECISION_AT - timedelta(hours=1),
        received_at=DECISION_AT,
        available_at=DECISION_AT - timedelta(minutes=30),
        retrieved_at=DECISION_AT,
        revision_id="r1",
        artifact_hash=s4f._hash(f"fact-{tag}"),
    )
    return NormalizedFact.create(
        instrument_id=instrument_id,
        source_id="nse_bhavcopy_eod",
        dataset_root="S6_SYNTHETIC_TEST",
        business_keys={"symbol": "R5TEST", "tag": tag},
        data_date=TRADING_DATE,
        lineage=lineage,
        quality_state="STRUCTURED_OK",
        payload={"tag": tag},
    )


def _claim(
    fact: NormalizedFact,
    source: SourceResult,
    *,
    family: EvidenceFamily,
    group: str,
    feature_id: str,
    direction: EvidenceDirection,
    strength: float,
) -> EvidenceClaim:
    return EvidenceClaim.create(
        feature_id=feature_id,
        feature_version="1.0.0",
        family=family,
        correlation_group=group,
        direction=direction,
        strength_before_caps=strength,
        source_fact_ids=(fact.fact_id,),
        authority=source.role,
        available_at=fact.lineage.available_at,
        event_time=fact.lineage.event_time,
        published_at=fact.lineage.published_at,
        received_at=fact.lineage.received_at,
        revision_id="r1",
        artifact_hash=fact.lineage.artifact_hash,
        state_ceiling=StateCeiling.WAIT,
        can_support_confirmed=False,
        explanation="synthetic S6 test claim",
    )


def _source() -> SourceResult:
    return SourceResult(
        source_id="nse_bhavcopy_eod",
        contract_version="a1-staging-1",
        role=SourceRole.OFFICIAL_GATE,
        state=SourceResultState.STRUCTURED_OK,
        record_count=1,
        data_date=TRADING_DATE,
        published_at=DECISION_AT - timedelta(hours=1),
        received_at=DECISION_AT,
        available_at=DECISION_AT - timedelta(minutes=30),
        retrieved_at=DECISION_AT,
        schema_version="fixture",
        parser_version="fixture",
        revision_id="r1",
        artifact_hash=s4f._hash("latest-cash"),
        freshness="FRESH",
        can_support_confirmed=False,
        state_ceiling="WAIT",
    )


def _s6(tmp_path, monkeypatch, **overrides):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s6.db")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    join = s4f._ca_join(bundle, attention, identity)
    r5 = s4f._build_r5(instrument, identity, history, bundle, attention, staging, context)
    params = dict(
        r5=r5,
        bundle=bundle,
        attention=attention,
        source_result=_source(),
        ca_join=join,
        built_at=DECISION_AT,
    )
    params.update(overrides)
    return build_s6_resolution(**params)


def test_s6_two_activity_claims_yield_one_participation_representative(
    tmp_path, monkeypatch
) -> None:
    instrument_id = "ins-test"
    source = _source()
    fact_a = _synthetic_fact(instrument_id, "activity-a")
    fact_b = _synthetic_fact(instrument_id, "activity-b")
    claims = (
        _claim(
            fact_a, source,
            family=EvidenceFamily.PARTICIPATION,
            group="CG_ACTIVITY_SESSION",
            feature_id="FTR-017",
            direction=EvidenceDirection.BULLISH,
            strength=0.9,
        ),
        _claim(
            fact_b, source,
            family=EvidenceFamily.PARTICIPATION,
            group="CG_ACTIVITY_SESSION",
            feature_id="FTR-017",
            direction=EvidenceDirection.BULLISH,
            strength=0.4,
        ),
    )
    batch = _s6(
        tmp_path,
        monkeypatch,
        claims_extra_by_symbol={"R5TEST": claims},
        facts_extra=(fact_a, fact_b),
    )
    row = batch.rows[0]
    assert row.families["PARTICIPATION"].support == pytest.approx(0.9)
    activity_selected = [
        cid for cid in row.representative_claim_ids if cid in {claims[0].claim_id, claims[1].claim_id}
    ]
    assert activity_selected == [claims[0].claim_id]
    assert claims[1].claim_id in row.suppressed_claim_ids


def test_s6_exchange_mirrored_event_is_one_family_input(tmp_path, monkeypatch) -> None:
    source = _source()
    fact_nse = _synthetic_fact("ins-test", "event-nse")
    fact_bse = _synthetic_fact("ins-test", "event-bse-mirror")
    claims = (
        _claim(
            fact_nse, source,
            family=EvidenceFamily.EVENT_AND_SPONSOR,
            group="CG_EVENT_ROOT",
            feature_id="FTR-026",
            direction=EvidenceDirection.BULLISH,
            strength=0.8,
        ),
        _claim(
            fact_bse, source,
            family=EvidenceFamily.EVENT_AND_SPONSOR,
            group="CG_EVENT_ROOT",
            feature_id="FTR-026",
            direction=EvidenceDirection.BULLISH,
            strength=0.8,
        ),
    )
    batch = _s6(
        tmp_path,
        monkeypatch,
        claims_extra_by_symbol={"R5TEST": claims},
        facts_extra=(fact_nse, fact_bse),
    )
    row = batch.rows[0]
    # Both exchange mirrors land in one CG_EVENT_ROOT group: one representative.
    event_selected = set(row.representative_claim_ids) & {
        claims[0].claim_id,
        claims[1].claim_id,
    }
    assert len(event_selected) == 1
    assert row.families["EVENT_AND_SPONSOR"].support == pytest.approx(0.8)
    mirrored = (set(row.suppressed_claim_ids) | event_selected) >= {
        claims[0].claim_id,
        claims[1].claim_id,
    }
    assert mirrored


def test_s6_pcr_and_wall_are_one_options_context(tmp_path, monkeypatch) -> None:
    source = _source()
    fact_pcr = _synthetic_fact("ins-test", "pcr")
    fact_wall = _synthetic_fact("ins-test", "wall")
    claims = (
        _claim(
            fact_pcr, source,
            family=EvidenceFamily.OPTIONS_CONTEXT,
            group="CG_OPTION_CHAIN",
            feature_id="FTR-023",
            direction=EvidenceDirection.BEARISH,
            strength=0.7,
        ),
        _claim(
            fact_wall, source,
            family=EvidenceFamily.OPTIONS_CONTEXT,
            group="CG_OPTION_CHAIN",
            feature_id="FTR-024",
            direction=EvidenceDirection.BEARISH,
            strength=0.3,
        ),
    )
    batch = _s6(
        tmp_path,
        monkeypatch,
        claims_extra_by_symbol={"R5TEST": claims},
        facts_extra=(fact_pcr, fact_wall),
    )
    row = batch.rows[0]
    assert row.families["OPTIONS_CONTEXT"].oppose == pytest.approx(0.7)
    selected_options = set(row.representative_claim_ids) & {
        claims[0].claim_id,
        claims[1].claim_id,
    }
    assert selected_options == {claims[0].claim_id}
    assert claims[1].claim_id in row.suppressed_claim_ids


def test_s6_opposite_event_groups_flag_conflict_not_confirmed(
    tmp_path, monkeypatch
) -> None:
    source = _source()
    fact_up = _synthetic_fact("ins-test", "event-up")
    fact_down = _synthetic_fact("ins-test", "event-down")
    claims = (
        _claim(
            fact_up, source,
            family=EvidenceFamily.EVENT_AND_SPONSOR,
            group="CG_EVENT_ROOT",
            feature_id="FTR-026",
            direction=EvidenceDirection.BULLISH,
            strength=0.6,
        ),
        _claim(
            fact_down, source,
            family=EvidenceFamily.SPONSOR_DELAYED_CONTEXT,
            group="CG_DELAYED_SPONSOR",
            feature_id="FTR-027",
            direction=EvidenceDirection.BEARISH,
            strength=0.5,
        ),
    )
    batch = _s6(
        tmp_path,
        monkeypatch,
        claims_extra_by_symbol={"R5TEST": claims},
        facts_extra=(fact_up, fact_down),
    )
    row = batch.rows[0]
    assert row.conflict is True
    assert row.resolution_state is not SelectionState.CONFIRMED
    assert batch.confirmed_count == 0


def test_s6_missing_required_structure_gives_zero_strength_wait(
    tmp_path, monkeypatch
) -> None:
    from datetime import time as dtime
    from zoneinfo import ZoneInfo

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s6-miss.db")
    IST = ZoneInfo("Asia/Kolkata")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    mid_session = datetime.combine(TRADING_DATE, dtime(10, 0), tzinfo=IST)
    r5 = s4f._build_r5(
        instrument, identity, history, bundle, attention, staging, context,
        decision_at=mid_session,
    )
    batch = build_s6_resolution(
        r5=r5,
        bundle=bundle,
        attention=attention,
        source_result=_source(),
        ca_join=s4f._ca_join(bundle, attention, identity),
        bound_to_shortlist=False,
        built_at=DECISION_AT,
    )
    row = batch.rows[0]
    assert "STRUCTURE" in row.missing_families
    assert row.evidence_strength == 0
    assert row.resolution_state is SelectionState.WAIT


def test_s6_preserves_only_pipeline_mandatory_gates(
    tmp_path, monkeypatch
) -> None:
    """Required evidence failures survive S6, but S6-local ceilings do not."""
    from datetime import time as dtime
    from zoneinfo import ZoneInfo

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s6-inherited-gates.db")
    ist = ZoneInfo("Asia/Kolkata")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    mid_session = datetime.combine(TRADING_DATE, dtime(10, 0), tzinfo=ist)
    r5 = s4f._build_r5(
        instrument,
        identity,
        history,
        bundle,
        attention,
        staging,
        context,
        decision_at=mid_session,
    )
    batch = build_s6_resolution(
        r5=r5,
        bundle=bundle,
        attention=attention,
        source_result=_source(),
        ca_join=s4f._ca_join(bundle, attention, identity),
        bound_to_shortlist=False,
        built_at=DECISION_AT,
    )
    row = batch.rows[0]
    inherited_codes = {gate.code for gate in row.inherited_gates}

    assert "WAIT_REQUIRED_FAMILY_STRUCTURE" in inherited_codes
    assert "WAIT_SOURCE_ACTIVATION" not in inherited_codes
    assert "WAIT_Q5_R2_NO_CONFIRMED" not in inherited_codes
    assert "WAIT_SOURCE_ACTIVATION" in row.why


def test_s6_strength_label_is_not_win_probability(tmp_path, monkeypatch) -> None:
    batch = _s6(tmp_path, monkeypatch)
    assert batch.rows[0].evidence_strength_label == STRENGTH_LABEL
    assert "not win probability" in batch.model_dump_json(by_alias=True)


def test_s6_context_claim_alone_cannot_buy(tmp_path, monkeypatch) -> None:
    source = _source()
    fact_ctx = _synthetic_fact("ins-test", "market-up")
    claim = _claim(
        fact_ctx, source,
        family=EvidenceFamily.MARKET_AND_SECTOR_CONTEXT,
        group="CG_MARKET_REGIME",
        feature_id="FTR-002",
        direction=EvidenceDirection.BULLISH,
        strength=1.0,
    )
    batch = _s6(
        tmp_path,
        monkeypatch,
        claims_extra_by_symbol={"R5TEST": (claim,)},
        facts_extra=(fact_ctx,),
    )
    row = batch.rows[0]
    # Context family can rank, but it can never satisfy a required family or
    # produce a BUY seat on its own.
    assert row.families["MARKET_AND_SECTOR_CONTEXT"].support == pytest.approx(1.0)
    assert row.resolution_state is SelectionState.WAIT
    assert row.can_unlock_confirmed is False
    assert batch.market_context is None or (
        batch.market_context.can_support_confirmed is False
    )


def test_s6_ceilings_and_lineage_hashes(tmp_path, monkeypatch) -> None:
    batch = _s6(tmp_path, monkeypatch)
    assert batch.acceptance_ceiling == ACCEPTANCE_CEILING
    assert batch.can_unlock_confirmed is False
    assert batch.source_activation_ready is False
    assert batch.r2_run_hash == s4f._hash("r2")
    blob = batch.model_dump_json(by_alias=True)
    for forbidden in ('"entry"', '"quantity"', '"winProbability"', '"resolutionState":"CONFIRMED"'):
        assert forbidden not in blob.replace(" ", "")


def test_s6_post_405_and_missing_lineage_503(tmp_path, monkeypatch) -> None:
    client = TestClient(app)
    assert client.post("/api/v1/selection/s6-resolution").status_code == 405
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s6-empty.db")
    response = TestClient(app).get("/api/v1/selection/s6-resolution")
    assert response.status_code == 503


def test_s6_required_families_come_from_profile_object(
    tmp_path, monkeypatch
) -> None:
    from datetime import time as dtime
    from zoneinfo import ZoneInfo

    from trendforge_api.selection.resolver import ResolutionProfile

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s6-swap.db")
    IST = ZoneInfo("Asia/Kolkata")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    mid_session = datetime.combine(TRADING_DATE, dtime(10, 0), tzinfo=IST)
    r5 = s4f._build_r5(
        instrument, identity, history, bundle, attention, staging, context,
        decision_at=mid_session,
    )
    join = s4f._ca_join(bundle, attention, identity)

    def make_profile(required):
        weights = {EvidenceFamily.STRUCTURE: 0.6}
        if EvidenceFamily.PARTICIPATION in required:
            weights[EvidenceFamily.PARTICIPATION] = 0.4
        return ResolutionProfile(
            profile_id=f"PRF-SWAP-{'-'.join(sorted(f.value for f in required))}",
            profile_version="9.9.9",
            family_weights=weights,
            required_families=tuple(required),
            state_ceiling=StateCeiling.WAIT,
            allowed_data_modes=(),
            corroboration_epsilon=0.0,
        )

    only_structure = make_profile((EvidenceFamily.STRUCTURE,))
    structure_and_participation = make_profile(
        (EvidenceFamily.STRUCTURE, EvidenceFamily.PARTICIPATION)
    )
    common = dict(
        r5=r5,
        bundle=bundle,
        attention=attention,
        source_result=_source(),
        ca_join=join,
        bound_to_shortlist=False,
        built_at=DECISION_AT,
    )
    batch_a = build_s6_resolution(profile=only_structure, **common)
    batch_b = build_s6_resolution(profile=structure_and_participation, **common)
    row_a = batch_a.rows[0]
    row_b = batch_b.rows[0]
    # Same claims, different active profile object -> different requirements.
    assert "PARTICIPATION" not in row_a.missing_families
    assert {"STRUCTURE", "PARTICIPATION"} <= set(row_b.missing_families)
    assert batch_a.active_profile_id != batch_b.active_profile_id


def test_s6_bounded_to_shortlist_excludes_claimless_rows(
    tmp_path, monkeypatch
) -> None:
    from datetime import time as dtime
    from zoneinfo import ZoneInfo

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s6-bound.db")
    IST = ZoneInfo("Asia/Kolkata")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    mid_session = datetime.combine(TRADING_DATE, dtime(10, 0), tzinfo=IST)
    r5 = s4f._build_r5(
        instrument, identity, history, bundle, attention, staging, context,
        decision_at=mid_session,
    )
    join = s4f._ca_join(bundle, attention, identity)
    common = dict(
        r5=r5,
        bundle=bundle,
        attention=attention,
        source_result=_source(),
        ca_join=join,
        built_at=DECISION_AT,
    )
    bounded = build_s6_resolution(**common)
    wide = build_s6_resolution(bound_to_shortlist=False, **common)
    # The only fixture row has no structure claim mid-session: the funnel
    # bounds it out of the board, while wide diagnostics still show it.
    assert bounded.universe_count == 0
    assert bounded.rows == ()
    assert wide.universe_count == 1
    assert any("shortlist" in warning for warning in bounded.warnings)


def test_s6_merged_cash_feed_competes_in_one_participation_group(
    tmp_path, monkeypatch
) -> None:
    from trendforge_api.selection.r3_claim_adapter import ClaimAdapterResult

    source = _source()
    cash_fact = _synthetic_fact("ins-test", "cash-ftr040")
    cash_claim = _claim(
        cash_fact, source,
        family=EvidenceFamily.PARTICIPATION,
        group="CG_ACTIVITY_SESSION",
        feature_id="FTR-040",
        direction=EvidenceDirection.BULLISH,
        strength=0.95,
    )
    feed = ClaimAdapterResult(
        claims_by_symbol={"R5TEST": (cash_claim,)},
        facts_by_symbol={"R5TEST": (cash_fact,)},
        source_results=(source,),
        suppressions_by_symbol={},
    )
    batch = _s6(tmp_path, monkeypatch, cash_feed=feed)
    row = batch.rows[0]
    # Cash FTR-040 and R5's RVOL claim share CG_ACTIVITY_SESSION: the merged
    # feed keeps exactly one participation representative and it is the
    # strongest claim.
    assert row.families["PARTICIPATION"].support == pytest.approx(0.95)
    assert cash_claim.claim_id in row.representative_claim_ids
    assert any("merged_feed" in warning for warning in batch.warnings)


def test_s6_assembles_cash_feed_from_pipeline_inputs(
    tmp_path, monkeypatch
) -> None:
    """Route-path assembly: real claims_from_cash_pipeline over the fixtures."""
    from trendforge_api.source_inventory_compiler import compile_default_inventory

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s6-cashpipe.db")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    r5 = s4f._build_r5(instrument, identity, history, bundle, attention, staging, context)
    join = s4f._ca_join(bundle, attention, identity)
    batch = build_s6_resolution(
        r5=r5,
        bundle=bundle,
        attention=attention,
        identity=identity,
        compiled_source_contracts=compile_default_inventory().source_contracts,
        source_result=_source(),
        ca_join=join,
        built_at=DECISION_AT,
    )
    assert not any(
        warning.startswith("CASH_FEED_") for warning in batch.warnings
    ), batch.warnings
    row = batch.rows[0]
    # The adapter minted a real FTR-040 claim at attention priority 0.9; it
    # beats R5's RVOL claim (2.5x baseline -> 0.833) inside CG_ACTIVITY_SESSION.
    assert row.families["PARTICIPATION"].support == pytest.approx(0.9)


def test_s6_api_route_returns_resolution(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s6-api.db")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    persist_inventory_source_bundle(bundle)
    persist_attention_order(attention)
    pin = persist_r4_identity_pin(
        build_r4_identity_pin(bundle=bundle, attention=attention, identity=identity)
    )
    join = persist_r14_ca_join(
        build_r14_ca_join(
            bundle=bundle,
            attention=attention,
            identity=identity,
            pin=pin,
            observations=[],
            vintages=[],
            decision_at=DECISION_AT,
        )
    )
    persist_r5_structure_batch(
        build_r5_structure_batch(
            bundle=bundle,
            attention=attention,
            identity=identity,
            history=history,
            staging=staging,
            context=context,
            ca_join=join,
            decision_at=DECISION_AT,
        )
    )
    client = TestClient(app)
    response = client.get("/api/v1/selection/s6-resolution")
    assert response.status_code == 200
    body = response.json()
    assert body["acceptanceCeiling"] == "LIVE_S6_RESOLVE_WAIT_ONLY"
    assert body["confirmedCount"] == 0
    assert body["rows"][0]["resolutionState"] in {"WAIT", "WATCH"}
