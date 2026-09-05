from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from trendforge_api.main import app

from trendforge_api.source_cohort_r0b import R0B_COHORT
from trendforge_api.source_cohort_r0c import build_r0c_cohort, evaluate_r0c_cohort
from trendforge_api.source_inventory_compiler import compile_default_inventory


def test_r0c_is_complete_non_overlapping_compiler_remainder() -> None:
    compiler = compile_default_inventory()
    report = evaluate_r0c_cohort()
    all_ids = {item.source_contract_id for item in compiler.source_contracts}
    r0b_ids = {item.source_key for item in R0B_COHORT} & all_ids
    r0c_ids = {item.source_contract_id for item in report.members}

    assert r0b_ids.isdisjoint(r0c_ids)
    assert r0b_ids | r0c_ids == all_ids
    assert report.compiled_contract_count == len(all_ids)
    assert report.r0b_compiled_count == len(r0b_ids)
    assert report.r0c_contract_count == len(r0c_ids)
    assert report.partition_complete is True


def test_r0c_members_are_quarantined_and_have_zero_authority() -> None:
    report = evaluate_r0c_cohort()
    assert report.source_activation_ready is False
    assert report.gate_authorized_source_key_count == 0
    assert report.reviewed_count == 0
    assert report.quarantined_count == report.r0c_contract_count
    assert report.members
    assert all(item.quarantined for item in report.members)
    assert all(not item.reviewed for item in report.members)
    assert all(not item.activation_eligible for item in report.members)
    assert all(not item.can_vote for item in report.members)
    assert all(not item.can_unlock_confirmed for item in report.members)
    assert all(not item.gate_permission for item in report.members)
    assert all(not item.executable for item in report.members)
    assert all("R0_C_UNREVIEWED_CONTRACT" in item.quarantine_reasons for item in report.members)


def test_r0c_fails_closed_if_remainder_contract_gains_gate_permission() -> None:
    compiler = compile_default_inventory()
    r0b_ids = {item.source_key for item in R0B_COHORT}
    index = next(
        i for i, item in enumerate(compiler.source_contracts)
        if item.source_contract_id not in r0b_ids
    )
    contracts = list(compiler.source_contracts)
    contracts[index] = contracts[index].model_copy(update={"gate_permission": True})
    unsafe = compiler.model_copy(update={"source_contracts": contracts})

    with pytest.raises(ValueError, match="unexpectedly has gate permission"):
        build_r0c_cohort(unsafe)

def test_r0c_api_exposes_complete_quarantined_remainder() -> None:
    response = TestClient(app).get("/api/source-inventory/r0c-cohort")
    assert response.status_code == 200
    payload = response.json()

    assert payload["slice"] == "R0-C"
    assert payload["partitionComplete"] is True
    assert payload["sourceActivationReady"] is False
    assert payload["gateAuthorizedSourceKeyCount"] == 0
    assert payload["reviewedCount"] == 0
    assert payload["quarantinedCount"] == payload["r0cContractCount"]
    assert payload["members"]
    assert all(item["quarantined"] is True for item in payload["members"])
    assert all(item["activationEligible"] is False for item in payload["members"])
    assert all(item["canVote"] is False for item in payload["members"])
    assert all(item["canUnlockConfirmed"] is False for item in payload["members"])
    assert all(item["gatePermission"] is False for item in payload["members"])
    assert all(item["executable"] is False for item in payload["members"])
