from __future__ import annotations

from fastapi.testclient import TestClient

from trendforge_api.main import app
from trendforge_api.selection.profile_source_contracts import (
    MatchPolicy,
    build_strategy_source_registry,
)
from trendforge_api.source_inventory_compiler import compile_default_inventory


PROFILE_IDS = {f"PRF-{index:03d}" for index in range(1, 8)}


def test_all_seven_profiles_have_named_mandatory_confirmation_and_veto_sources() -> None:
    registry = build_strategy_source_registry()
    assert registry.profile_count == 7
    assert {profile.profile_id for profile in registry.profiles} == PROFILE_IDS
    for profile in registry.profiles:
        assert profile.mandatory
        assert profile.confirmations
        assert profile.vetoes
        for group in (*profile.mandatory, *profile.confirmations, *profile.vetoes):
            assert group.source_keys
            assert len(group.source_keys) == len(set(group.source_keys))
            assert group.evidence_family
            assert group.match_policy in {MatchPolicy.ALL_OF, MatchPolicy.ANY_OF}


def test_registration_projection_matches_compiler_without_claiming_data_ready() -> None:
    registered = {
        item.source_contract_id for item in compile_default_inventory().source_contracts
    }
    registry = build_strategy_source_registry()
    assert registry.source_activation_ready is False
    assert registry.can_unlock_confirmed is False
    assert registry.executable is False
    for profile in registry.profiles:
        assert profile.source_activation_ready is False
        assert profile.can_unlock_confirmed is False
        assert profile.executable is False
        assert profile.state_ceiling_without_live_acceptance == "WAIT"
        for group in (*profile.mandatory, *profile.confirmations, *profile.vetoes):
            assert set(group.registered_keys) == set(group.source_keys) & registered
            assert set(group.missing_keys) == set(group.source_keys) - registered


def test_intraday_profiles_wait_for_unavailable_live_bar_contract() -> None:
    registry = build_strategy_source_registry()
    for profile_id in ("PRF-001", "PRF-002"):
        profile = next(item for item in registry.profiles if item.profile_id == profile_id)
        live_groups = [item for item in profile.mandatory if item.live_data_required]
        assert live_groups
        bars = next(item for item in live_groups if "BARS" in item.group_id)
        assert bars.source_keys == ("openalgo_intraday_candles",)
        assert bars.contract_covered is False
        assert profile.registration_complete is False


def test_delayed_sources_never_become_mandatory_live_proof() -> None:
    registry = build_strategy_source_registry()
    delayed = [
        group
        for profile in registry.profiles
        for group in profile.confirmations
        if group.delayed_context_only
    ]
    assert delayed
    assert all(not group.live_data_required for group in delayed)
    assert any("cftc_cot" in group.source_keys for group in delayed)
    assert any("amfi_monthly_portfolio" in group.source_keys for group in delayed)


def test_profile_source_contract_api_is_read_only_and_zero_authority() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/selection/profile-source-contracts")
    assert response.status_code == 200
    payload = response.json()
    assert payload["profileCount"] == 7
    assert payload["sourceActivationReady"] is False
    assert payload["canUnlockConfirmed"] is False
    assert payload["executable"] is False
    assert client.post("/api/v1/selection/profile-source-contracts").status_code == 405
