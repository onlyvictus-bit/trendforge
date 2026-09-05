from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api.causal_engine import CausalBatchRequest, evaluate_causal_batch
from trendforge_api.main import app


AS_OF = datetime(2026, 7, 10, 10, 30, tzinfo=timezone.utc)


def evidence(
    evidence_id: str,
    layer: str,
    contribution: float,
    *,
    signal_type: str = "GENERIC",
    age_days: float = 0,
    trust: str = "OFFICIAL",
    raw_keys: list[str] | None = None,
) -> dict:
    row = {
        "evidenceId": evidence_id,
        "layer": layer,
        "signalType": signal_type,
        "contribution": contribution,
        "source": "controlled-fixture",
        "sourceDate": (AS_OF - timedelta(days=age_days)).isoformat(),
        "observedAt": (AS_OF - timedelta(days=age_days)).isoformat(),
        "trustLevel": trust,
        "explanation": f"Controlled {layer} evidence.",
        "rawInputKeys": raw_keys or [],
    }
    if layer == "CAUSE" and contribution > 0:
        row["causeType"] = "FUNDAMENTAL_RERATING"
    if layer == "SPONSOR" and contribution > 0:
        row["sponsorActor"] = "PROMOTER_INSIDER"
    return row


def eligible_candidate(symbol: str = "ALPHA") -> dict:
    return {
        "symbol": symbol,
        "direction": "LONG",
        "asOf": AS_OF.isoformat(),
        "evaluationMode": "DEMO",
        "evidence": [
            evidence("cause", "CAUSE", 5),
            evidence("sponsor", "SPONSOR", 8),
            evidence("structure", "STRUCTURE", 5),
            evidence("flow", "FLOW", 5),
        ],
        "gates": [{"code": "TRAP", "outcome": "PASS", "reason": "No trap."}],
        "execution": {"score": 14, "triggerActive": True, "gates": []},
    }


def test_positive_cause_and_sponsor_evidence_requires_classification() -> None:
    row = eligible_candidate()
    del row["evidence"][0]["causeType"]
    with pytest.raises(ValidationError, match="causeType"):
        CausalBatchRequest(candidates=[row])


def test_decay_and_mutual_fund_initial_weight_are_applied() -> None:
    row = eligible_candidate()
    row["evidence"][1] = evidence("sponsor", "SPONSOR", 10, signal_type="MF_HOLDING")
    row["evidence"][1]["sponsorActor"] = "DII"
    result = evaluate_causal_batch(CausalBatchRequest(candidates=[row]))[0]
    sponsor = next(item for item in result.evidence if item.evidence_id == "sponsor")
    assert sponsor.decay_weight == pytest.approx(0.4)
    assert sponsor.adjusted_contribution == pytest.approx(4.0)


def test_shared_raw_input_receives_master_plan_independence_penalty() -> None:
    row = eligible_candidate()
    row["evidence"][2]["rawInputKeys"] = ["volume"]
    row["evidence"][3]["rawInputKeys"] = ["volume"]
    result = evaluate_causal_batch(CausalBatchRequest(candidates=[row]))[0]
    assert len(result.independence_penalties) == 1
    assert result.independence_penalties[0].amount == pytest.approx(1.5)
    structure = next(
        item for item in result.layer_scores if item.layer.value == "STRUCTURE"
    )
    flow = next(item for item in result.layer_scores if item.layer.value == "FLOW")
    assert structure.penalty == pytest.approx(0.75)
    assert flow.penalty == pytest.approx(0.75)


def test_future_evidence_is_point_in_time_hard_failure() -> None:
    row = eligible_candidate()
    row["evidence"][0]["sourceDate"] = (AS_OF + timedelta(days=1)).isoformat()
    result = evaluate_causal_batch(CausalBatchRequest(candidates=[row]))[0]
    assert result.stage1_label == "HARD_FAIL"
    assert result.stage2_label == "BLOCKED"
    assert result.final_state == "REJECT"


def test_high_execution_score_cannot_rescue_weak_causal_thesis() -> None:
    row = eligible_candidate()
    row["evidence"][0]["contribution"] = 0
    row["evidence"][1]["contribution"] = 0
    row["execution"]["score"] = 16
    result = evaluate_causal_batch(CausalBatchRequest(candidates=[row]))[0]
    assert result.stage1_label == "INELIGIBLE"
    assert result.stage2_label == "BLOCKED"
    assert result.final_state == "REJECT"


def test_eligible_stage1_and_confirmed_stage2_can_emit_read_only_ready() -> None:
    result = evaluate_causal_batch(
        CausalBatchRequest(candidates=[eligible_candidate()])
    )[0]
    assert result.stage1_label == "ELIGIBLE"
    assert result.stage2_label == "CONFIRMED"
    assert result.final_state == "READY"
    assert result.executable is False
    assert result.passing_layer_count == 4
    assert result.percentile_rank == 100


def test_production_unofficial_evidence_downgrades_ready() -> None:
    row = eligible_candidate()
    row["evaluationMode"] = "PRODUCTION"
    row["evidence"][3]["trustLevel"] = "UNOFFICIAL_TEMP"
    result = evaluate_causal_batch(CausalBatchRequest(candidates=[row]))[0]
    assert result.stage1_label == "ELIGIBLE"
    assert result.final_state == "WAIT_DATA_WEAK"


def test_hard_safety_override_wins_over_scores() -> None:
    row = eligible_candidate()
    row["gates"].append(
        {
            "code": "DAILY_LOSS_LOCK",
            "outcome": "HARD_FAIL",
            "reason": "Daily loss limit reached.",
            "overrideState": "LOCKED_NO_TRADE",
        }
    )
    result = evaluate_causal_batch(CausalBatchRequest(candidates=[row]))[0]
    assert result.final_state == "LOCKED_NO_TRADE"
    assert result.stage2_label == "BLOCKED"


def test_percentile_gate_only_allows_top_decile_candidate() -> None:
    strong = eligible_candidate("STRONG")
    weak = deepcopy(strong)
    weak["symbol"] = "WEAK"
    weak["evidence"][0]["contribution"] = 3
    request = CausalBatchRequest(candidates=[strong, weak])
    results = {item.symbol: item for item in evaluate_causal_batch(request)}
    assert results["STRONG"].percentile_rank == 100
    assert results["STRONG"].stage1_label == "ELIGIBLE"
    assert results["WEAK"].percentile_rank == 50
    assert results["WEAK"].stage1_label == "INELIGIBLE"


def test_typed_causal_api_returns_alias_contract() -> None:
    response = TestClient(app).post(
        "/api/causal/evaluate", json={"candidates": [eligible_candidate()]}
    )
    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["stage1Label"] == "ELIGIBLE"
    assert payload["stage2Label"] == "CONFIRMED"
    assert payload["finalState"] == "READY"
    assert payload["executable"] is False


def test_causal_api_rejects_duplicate_symbols_in_ranking_batch() -> None:
    response = TestClient(app).post(
        "/api/causal/evaluate",
        json={"candidates": [eligible_candidate(), eligible_candidate()]},
    )
    assert response.status_code == 422
    assert "unique" in response.json()["detail"]


def test_stale_evidence_is_capped_to_context_weight() -> None:
    row = eligible_candidate()
    row["evidence"][1]["sourceDate"] = (AS_OF - timedelta(days=20)).isoformat()
    row["evidence"][1]["observedAt"] = (AS_OF - timedelta(days=20)).isoformat()
    row["evidence"][1]["staleAfterDays"] = 5
    result = evaluate_causal_batch(CausalBatchRequest(candidates=[row]))[0]
    sponsor = next(item for item in result.evidence if item.evidence_id == "sponsor")
    assert sponsor.freshness == "STALE"
    assert sponsor.decay_weight <= 0.4


def test_every_layer_minimum_is_mandatory_even_when_total_and_three_layers_pass() -> (
    None
):
    row = eligible_candidate()
    row["evidence"][3]["contribution"] = 1.5
    result = evaluate_causal_batch(CausalBatchRequest(candidates=[row]))[0]
    assert result.stage1_score >= 18
    assert result.passing_layer_count == 3
    assert result.stage1_label == "INELIGIBLE"
    assert result.stage2_label == "BLOCKED"


def test_duplicate_evidence_ids_are_rejected() -> None:
    row = eligible_candidate()
    row["evidence"][1]["evidenceId"] = "cause"
    with pytest.raises(ValidationError, match="evidenceId"):
        CausalBatchRequest(candidates=[row])


def test_timezone_naive_cutoff_is_rejected() -> None:
    row = eligible_candidate()
    row["asOf"] = "2026-07-10T10:30:00"
    with pytest.raises(ValidationError, match="timezone-aware"):
        CausalBatchRequest(candidates=[row])
