from __future__ import annotations

from fastapi.testclient import TestClient

from trendforge_api.main import app
from trendforge_api.selection import (
    EvidenceDirection,
    EvidenceFamily,
    GateOutcome,
    ResolutionProfile,
    SelectionGateResult,
    SelectionState,
    build_q5_r2_fixture_batch,
    resolve_evidence,
)
from trendforge_api.selection.r2_fixtures import R2_PROFILE
from trendforge_api.selection.resolver import ClaimDisposition


def _candidate_resolution(symbol: str):
    batch = build_q5_r2_fixture_batch()
    pairs = zip(batch.candidates, batch.resolutions, strict=True)
    return batch, next(
        (candidate, resolution)
        for candidate, resolution in pairs
        if candidate.instrument.symbol == symbol
    )


def test_q5_r2_fixtures_cover_watch_wait_reject_without_confirmed() -> None:
    batch = build_q5_r2_fixture_batch()
    states = {candidate.state for candidate in batch.candidates}
    assert states == {
        SelectionState.WATCH,
        SelectionState.WAIT,
        SelectionState.REJECT,
    }
    assert all(
        candidate.state is not SelectionState.CONFIRMED
        for candidate in batch.candidates
    )
    assert all(resolution.corroboration_bonus == 0 for resolution in batch.resolutions)


def test_same_group_support_selects_only_strongest_claim() -> None:
    batch, (_candidate, resolution) = _candidate_resolution("TF_WATCH")
    primary = next(
        claim for claim in batch.claims if claim.strength_before_caps == 0.45
    )
    duplicate = next(
        claim for claim in batch.claims if claim.strength_before_caps == 0.30
    )
    assert primary.claim_id in resolution.selected_claim_ids
    assert duplicate.claim_id in resolution.suppressed_claim_ids
    disposition = {claim.claim_id: claim.disposition for claim in resolution.claims}
    assert disposition[primary.claim_id] is ClaimDisposition.SELECTED_SUPPORT
    assert disposition[duplicate.claim_id] is ClaimDisposition.SUPPRESSED_CORRELATED


def test_shadow_claim_is_zero_vote_even_when_stronger() -> None:
    batch, (_candidate, resolution) = _candidate_resolution("TF_WATCH")
    shadow = next(
        claim for claim in batch.claims if claim.authority.value == "SHADOW_UPSTREAM"
    )
    result = next(
        item for item in resolution.claims if item.claim_id == shadow.claim_id
    )

    assert shadow.strength_before_caps == 0.99
    assert result.disposition is ClaimDisposition.SUPPRESSED_AUTHORITY
    assert shadow.claim_id not in resolution.selected_claim_ids


def test_future_claim_is_suppressed_at_decision_time() -> None:
    batch, (_candidate, resolution) = _candidate_resolution("TF_WAIT_EARLY_CONFIRM")
    future = next(
        claim for claim in batch.claims if claim.available_at > batch.run.as_of
    )
    result = next(
        item for item in resolution.claims if item.claim_id == future.claim_id
    )
    assert result.disposition is ClaimDisposition.SUPPRESSED_FUTURE


def test_opposition_is_visible_and_subtracted_without_corroboration() -> None:
    _batch, (candidate, resolution) = _candidate_resolution("TF_WAIT_EARLY_CONFIRM")
    assert EvidenceFamily.STRUCTURE in candidate.family_supports
    assert resolution.support_strength == 0.415
    assert resolution.opposition_strength == 0.12
    assert resolution.evidence_strength == 0.295
    assert resolution.corroboration_bonus == 0


def test_resolver_output_is_deterministic_for_reordered_claims() -> None:
    batch, (candidate, _) = _candidate_resolution("TF_WAIT_EARLY_CONFIRM")
    fact = next(
        fact
        for fact in batch.facts
        if fact.instrument_id == candidate.instrument.instrument_id
    )
    claims = tuple(
        claim for claim in batch.claims if fact.fact_id in claim.source_fact_ids
    )
    common = {
        "profile": R2_PROFILE,
        "decision_at": batch.run.as_of,
        "evidence_direction": EvidenceDirection.BULLISH,
        "facts": (fact,),
        "source_results": batch.source_results,
        "completeness": 1.0,
    }
    forward = resolve_evidence(claims=claims, **common)
    reverse = resolve_evidence(claims=tuple(reversed(claims)), **common)
    assert forward.model_dump(mode="json") == reverse.model_dump(mode="json")


def test_blocked_required_source_maps_to_wait_not_reject() -> None:
    batch, (candidate, _) = _candidate_resolution("TF_WATCH")
    fact = next(
        fact
        for fact in batch.facts
        if fact.instrument_id == candidate.instrument.instrument_id
    )
    claims = tuple(
        claim for claim in batch.claims if fact.fact_id in claim.source_fact_ids
    )
    profile = ResolutionProfile(
        profile_id="PRF-BLOCKED-SOURCE",
        profile_version="1",
        family_weights={EvidenceFamily.PARTICIPATION: 1.0},
        required_source_ids=("SRC-NSE-OPTIONS",),
    )
    resolution = resolve_evidence(
        profile=profile,
        decision_at=batch.run.as_of,
        evidence_direction=EvidenceDirection.BULLISH,
        claims=claims,
        facts=(fact,),
        source_results=batch.source_results,
        completeness=1.0,
        discovery_only=False,
    )
    assert resolution.state is SelectionState.WAIT
    assert all(
        gate.outcome is not GateOutcome.REJECT for gate in resolution.gate_results
    )
    assert any("BLOCKED" in gate.code for gate in resolution.gate_results)


def test_valid_empty_required_source_is_not_a_failure() -> None:
    batch, (candidate, _) = _candidate_resolution("TF_WATCH")
    fact = next(
        fact
        for fact in batch.facts
        if fact.instrument_id == candidate.instrument.instrument_id
    )
    claims = tuple(
        claim for claim in batch.claims if fact.fact_id in claim.source_fact_ids
    )
    profile = ResolutionProfile(
        profile_id="PRF-VALID-EMPTY",
        profile_version="1",
        family_weights={EvidenceFamily.PARTICIPATION: 1.0},
        required_source_ids=("SRC-NSE-GSM",),
    )
    resolution = resolve_evidence(
        profile=profile,
        decision_at=batch.run.as_of,
        evidence_direction=EvidenceDirection.BULLISH,
        claims=claims,
        facts=(fact,),
        source_results=batch.source_results,
        completeness=1.0,
        discovery_only=True,
    )
    assert resolution.state is SelectionState.WATCH
    assert not any("SRC-NSE-GSM" in gate.code for gate in resolution.gate_results)


def test_partial_scan_and_hard_veto_have_different_states() -> None:
    batch, (candidate, _) = _candidate_resolution("TF_WATCH")
    fact = next(
        fact
        for fact in batch.facts
        if fact.instrument_id == candidate.instrument.instrument_id
    )
    claims = tuple(
        claim for claim in batch.claims if fact.fact_id in claim.source_fact_ids
    )
    partial = resolve_evidence(
        profile=R2_PROFILE,
        decision_at=batch.run.as_of,
        evidence_direction=EvidenceDirection.BULLISH,
        claims=claims,
        facts=(fact,),
        source_results=batch.source_results,
        completeness=0.5,
        discovery_only=True,
    )
    rejected = resolve_evidence(
        profile=R2_PROFILE,
        decision_at=batch.run.as_of,
        evidence_direction=EvidenceDirection.BULLISH,
        claims=claims,
        facts=(fact,),
        source_results=batch.source_results,
        completeness=1.0,
        existing_gates=(
            SelectionGateResult(
                code="REJECT_TEST_VETO",
                outcome=GateOutcome.REJECT,
                blocks_confirmed=True,
                reason="Controlled deterministic veto.",
            ),
        ),
        discovery_only=True,
    )
    assert partial.state is SelectionState.WAIT
    assert "WAIT_PARTIAL_SCAN" in partial.gate_codes
    assert rejected.state is SelectionState.REJECT
    assert "REJECT_TEST_VETO" in rejected.gate_codes


def test_q5_r2_api_exposes_resolution_and_no_trade_fields() -> None:
    response = TestClient(app).get("/api/v1/selection/fixtures/q5-r2")
    assert response.status_code == 200
    payload = response.json()
    assert payload["milestone"] == "Q5-R2"
    assert set(payload["publicStates"]) == {
        "WATCH",
        "WAIT",
        "CONFIRMED",
        "REJECT",
    }
    assert {candidate["state"] for candidate in payload["candidates"]} == {
        "WATCH",
        "WAIT",
        "REJECT",
    }
    assert all(item["corroborationBonus"] == 0 for item in payload["resolutions"])
    for forbidden in (
        "tradeDirection",
        "entry",
        "stop",
        "target",
        "quantity",
        "orderIntent",
        "winProbability",
    ):
        assert forbidden not in response.text
