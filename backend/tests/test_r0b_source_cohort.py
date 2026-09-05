from __future__ import annotations

from fastapi.testclient import TestClient

from trendforge_api.main import app
from trendforge_api.source_cohort_r0b import R0B_COHORT, evaluate_r0b_cohort
from trendforge_api.source_inventory_compiler import compile_default_inventory


def test_r0b_cohort_stays_non_voting_and_non_activating() -> None:
    report = evaluate_r0b_cohort()
    compiler = compile_default_inventory()
    assert report.source_activation_ready is False
    assert report.gate_authorized_source_key_count == 0
    assert report.h1a0_passed == compiler.h1a0_acceptance_passed
    assert report.h1a0_total == 6
    assert {item.source_key for item in report.members} == {
        item.source_key for item in R0B_COHORT
    }
    assert all(item.can_vote is False for item in report.members)
    assert all(item.can_unlock_confirmed is False for item in report.members)
    assert report.source_activation_ready is False
    assert report.reviewed_count == len(R0B_COHORT)
    mwpl = next(item for item in report.members if item.source_key == "nse_mwpl_percentages")
    assert mwpl.confirm_eligible is False
    assert mwpl.can_vote is False
    assert any(
        dim.id == "valid_empty_or_unavailable_distinct" and dim.state.value == "PASS"
        for dim in mwpl.dimensions
    )
    confirm_path = [item for item in report.members if item.source_key != "nse_mwpl_percentages"]
    assert all(item.proven is True for item in confirm_path)
    assert all(item.confirm_eligible is True for item in confirm_path)
    ban = next(item for item in report.members if item.source_key == "nse_fno_ban")
    assert any(
        dim.id == "parser_registered" and dim.state.value == "PASS"
        for dim in ban.dimensions
    )
    assert any(
        dim.id == "extended_fields_complete" and dim.state.value == "PASS"
        for dim in ban.dimensions
    )
    assert any(
        dim.id == "source_specific_retry_breaker" and dim.state.value == "PASS"
        for dim in ban.dimensions
    )
    assert "rate_budget" not in ban.waived_extended_fields
    assert all(item.reviewed is True for item in report.members)


def test_r0b_api_does_not_authorize() -> None:
    payload = TestClient(app).get("/api/source-inventory/r0b-cohort").json()
    assert payload["slice"] == "R0-B"
    assert payload["sourceActivationReady"] is False
    assert payload["gateAuthorizedSourceKeyCount"] == 0
    assert payload["reviewedCount"] == 6
    mwpl = next(item for item in payload["members"] if item["sourceKey"] == "nse_mwpl_percentages")
    assert mwpl["confirmEligible"] is False
    assert mwpl["canVote"] is False
    assert payload["sourceActivationReady"] is False
    assert payload["sourceActivationReady"] is False
