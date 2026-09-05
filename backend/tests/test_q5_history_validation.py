from __future__ import annotations

from datetime import timedelta
from math import nan

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api.main import app
from trendforge_api.selection import (
    CandidateInspector,
    StructureSubstate,
    DriftStatus,
    PITOutcome,
    PITValidationResult,
    Q5R6FixtureBatch,
    SelectionHistory,
    SelectionState,
    SelectionStateEvent,
    ValidationCostProfile,
    ValidationStatus,
    assess_validation_drift,
    build_q5_r6_fixture_batch,
    build_state_event,
    evaluate_pit_validation,
)
from trendforge_api.selection.r6_fixtures import (
    R6_DECISION_AT,
    R6_EVALUATED_AT,
    _cost_profile,
    _drift_artifact,
    _confirmation_context,
    _no_entry_outcome,
    _outcomes,
    _validation_artifacts,
    _validation_profile,
)


def _batch():
    return build_q5_r6_fixture_batch()


def _approved() -> PITValidationResult:
    result = _batch().validation_results[0]
    assert result.status is ValidationStatus.PIT_APPROVED
    return result


def _validate(**overrides) -> PITValidationResult:
    cost = _cost_profile()
    outcomes = overrides.pop("outcomes", _outcomes(cost))
    evaluated_at = overrides.pop("evaluated_at", R6_EVALUATED_AT)
    walk_forward_passed = overrides.pop("walk_forward_passed", True)
    holdout_passed = overrides.pop("holdout_passed", True)
    if outcomes:
        walk_forward_artifact, holdout_artifact = _validation_artifacts(
            outcomes,
            evaluated_at,
            walk_forward_passed=walk_forward_passed,
            holdout_passed=holdout_passed,
        )
    else:
        walk_forward_artifact = None
        holdout_artifact = None
    values = {
        "run_id": "PIT-R6-TEST",
        "profile": _validation_profile(),
        "outcomes": outcomes,
        "cost_profile": cost,
        "evaluated_at": evaluated_at,
        "walk_forward_artifact": walk_forward_artifact,
        "holdout_artifact": holdout_artifact,
        "fixture_only": True,
    }
    values.update(overrides)
    return evaluate_pit_validation(**values)


def test_q5_r6_fixture_hides_performance_probability_and_execution() -> None:
    batch = _batch()
    assert batch.acceptance_ceiling == "NO_PERFORMANCE_OR_PROBABILITY_UI"
    assert batch.fixture_only is True
    assert batch.production_authorized is False
    assert batch.executable is False
    assert batch.inspector.performance_ui_visible is False
    assert batch.inspector.probability_ui_visible is False
    assert all(row.executable is False for row in batch.radar)


def test_state_history_reconstructs_every_transition_in_order() -> None:
    history = _batch().histories[0]
    assert history.reconstructable is True
    assert history.current_state is SelectionState.REJECT
    assert [event.sequence for event in history.events] == [1, 2, 3, 4, 5]
    assert history.what_changed[-1].endswith("STRUCTURE_INVALIDATED")


@pytest.mark.parametrize(
    "blocker",
    ("WAIT_BAR_CLOSE", "WAIT_STREAM_GAP", "WAIT_SOURCE_CONFLICT"),
)
def test_confirmation_with_recoverable_blocker_is_denied(blocker: str) -> None:
    event = build_state_event(
        sequence=1,
        candidate_id="C1",
        comparable_run_id="R1",
        prior_state=SelectionState.WAIT,
        requested_state=SelectionState.CONFIRMED,
        occurred_at=R6_DECISION_AT,
        reason_code="REQUEST_CONFIRM",
        reason="Requested.",
        blockers=(blocker,),
    )
    assert event.accepted is False
    assert event.resulting_state is SelectionState.WAIT
    assert event.reason_code == blocker


def test_blocked_watch_confirmation_resolves_to_wait() -> None:
    event = build_state_event(
        sequence=1,
        candidate_id="C1",
        comparable_run_id="R1",
        prior_state=SelectionState.WATCH,
        requested_state=SelectionState.CONFIRMED,
        occurred_at=R6_DECISION_AT,
        reason_code="REQUEST_CONFIRM",
        reason="Requested.",
        blockers=("WAIT_BAR_CLOSE",),
    )
    assert event.accepted is False
    assert event.resulting_state is SelectionState.WAIT
    assert event.reason_code == "WAIT_DIRECT_CONFIRMATION_FORBIDDEN"


def test_confirmation_without_complete_proof_is_denied() -> None:
    event = build_state_event(
        sequence=1,
        candidate_id="C1",
        comparable_run_id="R1",
        prior_state=SelectionState.WAIT,
        requested_state=SelectionState.CONFIRMED,
        occurred_at=R6_DECISION_AT,
        reason_code="REQUEST_CONFIRM",
        reason="Requested without proof.",
    )
    assert event.accepted is False
    assert event.resulting_state is SelectionState.WAIT
    assert event.reason_code == "WAIT_CONFIRMATION_CONTEXT_MISSING"


def test_confirmation_with_complete_proof_is_accepted() -> None:
    context = _confirmation_context(R6_DECISION_AT)
    event = build_state_event(
        sequence=1,
        candidate_id="C1",
        comparable_run_id="R1",
        prior_state=SelectionState.WAIT,
        requested_state=SelectionState.CONFIRMED,
        occurred_at=R6_DECISION_AT,
        reason_code="CLOSED_BAR_CONFIRMED",
        reason="All required evidence passed.",
        confirmation_context=context,
        structure_substate=StructureSubstate.ACCEPTED,
    )
    assert event.accepted is True
    assert event.resulting_state is SelectionState.CONFIRMED
    assert event.confirmation_context == context
    assert event.confirmation_proof is not None


def test_event_identity_changes_with_material_diff() -> None:
    base = {
        "sequence": 1,
        "candidate_id": "C1",
        "comparable_run_id": "R1",
        "prior_state": SelectionState.WATCH,
        "requested_state": SelectionState.WAIT,
        "occurred_at": R6_DECISION_AT,
        "reason_code": "WAIT_SOURCE",
        "reason": "Source missing.",
    }
    left = build_state_event(**base, added_gate_codes=("WAIT_SOURCE",))
    right = build_state_event(**base, added_gate_codes=("WAIT_SCHEMA",))
    assert left.event_id != right.event_id


def test_reject_without_hard_veto_is_denied() -> None:
    event = build_state_event(
        sequence=1,
        candidate_id="C1",
        comparable_run_id="R1",
        prior_state=SelectionState.WATCH,
        requested_state=SelectionState.REJECT,
        occurred_at=R6_DECISION_AT,
        reason_code="REJECT_REQUEST",
        reason="Requested.",
    )
    assert event.accepted is False
    assert event.resulting_state is SelectionState.WATCH
    assert event.reason_code == "REJECT_REQUIRES_HARD_VETO"


def test_hard_veto_cannot_be_encoded_as_watch_or_wait() -> None:
    event = build_state_event(
        sequence=1,
        candidate_id="C1",
        comparable_run_id="R1",
        prior_state=SelectionState.WATCH,
        requested_state=SelectionState.WAIT,
        occurred_at=R6_DECISION_AT,
        reason_code="HARD_VETO",
        reason="Wrong target state.",
        hard_veto=True,
    )
    assert event.accepted is False
    assert event.reason_code == "HARD_VETO_REQUIRES_REJECT"


def test_state_event_rejects_inconsistent_acceptance_and_duplicate_diffs() -> None:
    event = _batch().histories[0].events[0]
    payload = event.model_dump(mode="python")
    payload["accepted"] = True
    with pytest.raises(ValidationError):
        SelectionStateEvent.model_validate(payload)

    payload = event.model_dump(mode="python")
    payload["added_claim_ids"] = ("CLM-1", "CLM-1")
    with pytest.raises(ValidationError):
        SelectionStateEvent.model_validate(payload)


@pytest.mark.parametrize("defect", ("sequence", "prior", "time", "candidate"))
def test_history_rejects_non_reconstructable_event_chain(defect: str) -> None:
    history = _batch().histories[0]
    payload = history.model_dump(mode="python")
    events = [event.model_dump(mode="python") for event in history.events]
    if defect == "sequence":
        events[1]["sequence"] = 9
    elif defect == "prior":
        events[1]["prior_state"] = SelectionState.REJECT
    elif defect == "time":
        events[1]["occurred_at"] = events[0]["occurred_at"] - timedelta(seconds=1)
    else:
        events[1]["candidate_id"] = "OTHER"
    payload["events"] = events
    with pytest.raises(ValidationError):
        SelectionHistory.model_validate(payload)


def test_cost_profile_is_versioned_and_total_is_deterministic() -> None:
    cost = _cost_profile()
    assert cost.profile_id and cost.profile_version
    assert cost.total_cost_bps == 20.0
    assert cost.sensitivity_multipliers == (0.75, 1.0, 1.5)


def test_cost_profile_rejects_unsorted_or_duplicate_sensitivity() -> None:
    payload = _cost_profile().model_dump(mode="python")
    for values in ((1.0, 0.75), (1.0, 1.0)):
        payload["sensitivity_multipliers"] = values
        with pytest.raises(ValidationError):
            ValidationCostProfile.model_validate(payload)


def test_outcome_rejects_predecision_availability_and_survivorship_leakage() -> None:
    outcome = _outcomes(_cost_profile())[0]
    payload = outcome.model_dump(mode="python")
    payload["outcome_available_at"] = outcome.decision_at - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        PITOutcome.model_validate(payload)

    payload = outcome.model_dump(mode="python")
    payload["membership_available_at"] = outcome.decision_at + timedelta(seconds=1)
    with pytest.raises(ValidationError):
        PITOutcome.model_validate(payload)


def test_censored_outcome_requires_reason_and_completed_outcome_forbids_it() -> None:
    censored = _outcomes(_cost_profile())[-1]
    payload = censored.model_dump(mode="python")
    payload["censored_reason"] = None
    with pytest.raises(ValidationError):
        PITOutcome.model_validate(payload)

    completed = _outcomes(_cost_profile())[0]
    payload = completed.model_dump(mode="python")
    payload["censored_reason"] = "not allowed"
    with pytest.raises(ValidationError):
        PITOutcome.model_validate(payload)


def test_outcome_availability_respects_completion_and_censor_horizons() -> None:
    cost = _cost_profile()
    completed = _outcomes(cost)[0]
    payload = completed.model_dump(mode="python")
    payload["outcome_available_at"] = completed.horizon_end + timedelta(seconds=1)
    with pytest.raises(ValidationError):
        PITOutcome.model_validate(payload)

    censored = _outcomes(cost)[-1]
    payload = censored.model_dump(mode="python")
    payload["outcome_available_at"] = censored.horizon_end - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        PITOutcome.model_validate(payload)


def test_missing_cost_profile_blocks_pit_approval() -> None:
    result = _validate(cost_profile=None)
    assert result.status is ValidationStatus.PIT_REJECTED
    assert "PIT_COST_PROFILE_MISSING" in result.blocker_codes
    assert result.performance_ui_allowed is False


def test_fixture_pit_approval_still_cannot_show_performance_or_probability() -> None:
    result = _approved()
    assert result.effective_sample == 3
    assert len(result.outcome_ids) == 4
    assert result.performance_ui_allowed is False
    assert result.probability_ui_allowed is False


def test_censored_rows_are_retained_but_do_not_satisfy_effective_sample() -> None:
    profile = _validation_profile().model_copy(update={"min_effective_sample": 4})
    result = _validate(profile=profile)
    assert result.effective_sample == 3
    assert len(result.outcome_ids) == 4
    assert "PIT_SAMPLE_INSUFFICIENT" in result.blocker_codes


def test_cost_profile_mismatch_blocks_approval() -> None:
    payload = _outcomes(_cost_profile())[0].model_dump(mode="python")
    payload["cost_profile_version"] = "0.9.0"
    with pytest.raises(ValidationError):
        PITOutcome.model_validate(payload)


def test_future_outcome_or_cost_profile_blocks_pit_approval() -> None:
    cost = _cost_profile()
    result = _validate(
        evaluated_at=_outcomes(cost)[0].outcome_available_at - timedelta(seconds=1)
    )
    assert "PIT_OUTCOME_NOT_AVAILABLE" in result.blocker_codes

    future_cost = cost.model_copy(
        update={"available_at": R6_EVALUATED_AT + timedelta(seconds=1)}
    )
    result = _validate(cost_profile=future_cost)
    assert "PIT_COST_PROFILE_FUTURE" in result.blocker_codes


@pytest.mark.parametrize(
    ("overrides", "blocker"),
    (
        ({"outcomes": ()}, "PIT_SAMPLE_INSUFFICIENT"),
        ({"walk_forward_passed": False}, "PIT_WALK_FORWARD_FAILED"),
        ({"holdout_passed": False}, "PIT_HOLDOUT_FAILED"),
        ({"walk_forward_artifact": None}, "PIT_WALK_FORWARD_FAILED"),
        ({"holdout_artifact": None}, "PIT_HOLDOUT_FAILED"),
    ),
)
def test_each_validation_gate_blocks_approval(overrides: dict, blocker: str) -> None:
    result = _validate(**overrides)
    assert result.status is ValidationStatus.PIT_REJECTED
    assert blocker in result.blocker_codes


def test_metrics_and_cost_sensitivity_are_computed_from_outcomes() -> None:
    result = _approved()
    assert result.calibration_error is not None
    assert result.max_drawdown is not None
    assert result.false_confirmed_rate == pytest.approx(2 / 3, abs=1e-8)
    assert [point.multiplier for point in result.cost_sensitivity] == [0.75, 1.0, 1.5]


def test_forged_net_return_and_cost_arithmetic_block_approval() -> None:
    payload = _outcomes(_cost_profile())[0].model_dump(mode="python")
    payload["net_return"] = 99.0
    payload["explicit_cost_bps"] = 0.0
    with pytest.raises(ValidationError):
        PITOutcome.model_validate(payload)


def test_deterministic_calibration_drawdown_expectancy_and_false_rate_gates() -> None:
    base = _validation_profile()
    calibration = base.model_copy(update={"max_calibration_error": 0.001})
    assert "PIT_CALIBRATION_FAILED" in _validate(profile=calibration).blocker_codes

    drawdown = base.model_copy(update={"max_drawdown": 0.001})
    assert "PIT_DRAWDOWN_FAILED" in _validate(profile=drawdown).blocker_codes

    false_rate = base.model_copy(update={"max_false_confirmed_rate": 0.50})
    assert "PIT_FALSE_CONFIRMED_FAILED" in _validate(profile=false_rate).blocker_codes

    expectancy = base.model_copy(update={"min_net_expectancy": 0.10})
    assert "PIT_EXPECTANCY_FAILED" in _validate(profile=expectancy).blocker_codes


def test_unchecked_delisting_and_duplicate_outcome_block_approval() -> None:
    cost = _cost_profile()
    rows = list(_outcomes(cost))
    payload = rows[0].model_dump(mode="python")
    payload["delisting_checked"] = False
    rows[0] = PITOutcome.model_validate(payload)
    assert "PIT_DELISTING_UNCHECKED" in _validate(outcomes=tuple(rows)).blocker_codes

    rows = list(_outcomes(cost))
    rows[-1] = rows[0]
    assert "PIT_DUPLICATE_OUTCOME" in _validate(outcomes=tuple(rows)).blocker_codes


def test_drift_can_warn_or_demote_but_never_auto_promote() -> None:
    approved = _approved()
    healthy = assess_validation_drift(
        validation=approved,
        metric_artifact=_drift_artifact(
            approved,
            assessed_at=R6_EVALUATED_AT,
            feature_psi=0.05,
            calibration_error_delta=0.01,
            residual_shift=0.02,
        ),
        assessed_at=R6_EVALUATED_AT,
    )
    warned = assess_validation_drift(
        validation=approved,
        metric_artifact=_drift_artifact(
            approved,
            assessed_at=R6_EVALUATED_AT,
            feature_psi=0.16,
            calibration_error_delta=0.01,
            residual_shift=0.10,
        ),
        assessed_at=R6_EVALUATED_AT,
    )
    demoted = assess_validation_drift(
        validation=approved,
        metric_artifact=_drift_artifact(
            approved,
            assessed_at=R6_EVALUATED_AT,
            feature_psi=0.30,
            calibration_error_delta=0.20,
            residual_shift=0.20,
        ),
        assessed_at=R6_EVALUATED_AT,
    )
    assert [healthy.status, warned.status, demoted.status] == [
        DriftStatus.HEALTHY,
        DriftStatus.WARN,
        DriftStatus.DEMOTED,
    ]
    assert all(item.metric_artifact_id for item in (healthy, warned, demoted))
    assert all(item.can_auto_promote is False for item in (healthy, warned, demoted))
    assert demoted.demotes_to_research_only is True


def test_drift_without_approved_baseline_is_not_evaluated() -> None:
    rejected = _batch().validation_results[1]
    drift = assess_validation_drift(
        validation=rejected,
        metric_artifact=_drift_artifact(
            rejected,
            assessed_at=R6_EVALUATED_AT,
            feature_psi=0.01,
            calibration_error_delta=0.01,
            residual_shift=0.01,
        ),
        assessed_at=R6_EVALUATED_AT,
    )
    assert drift.status is DriftStatus.NOT_EVALUATED


def test_missing_drift_metric_demotes_approved_profile() -> None:
    drift = assess_validation_drift(
        validation=_approved(),
        metric_artifact=None,
        assessed_at=R6_EVALUATED_AT,
    )
    assert drift.status is DriftStatus.DEMOTED
    assert "DRIFT_ARTIFACT_MISSING_OR_MISMATCHED" in drift.reason_codes


def test_nonfinite_validation_values_and_negative_drift_are_rejected_or_demoted() -> (
    None
):
    profile = _validation_profile().model_dump(mode="python")
    profile["min_net_expectancy"] = nan
    with pytest.raises(ValidationError):
        type(_validation_profile()).model_validate(profile)

    with pytest.raises(ValidationError):
        _drift_artifact(
            _approved(),
            assessed_at=R6_EVALUATED_AT,
            feature_psi=-0.01,
            calibration_error_delta=0.0,
            residual_shift=0.01,
        )


def test_inspector_requires_hidden_validation_without_visible_performance() -> None:
    inspector = _batch().inspector
    section = next(
        item for item in inspector.sections if item.section_id == "VALIDATION"
    )
    assert section.status == "HIDDEN"
    payload = inspector.model_dump(mode="python")
    payload["performance_ui_visible"] = True
    payload["validation_status"] = ValidationStatus.PIT_REJECTED
    with pytest.raises(ValidationError):
        CandidateInspector.model_validate(payload)


def test_r6_payload_contains_no_trade_or_probability_contract() -> None:
    payload = _batch().model_dump_json(by_alias=True)
    for forbidden in (
        "winProbability",
        "tradeDirection",
        "orderIntent",
        "quantity",
        "entryPrice",
        "stopPrice",
        "targetPrice",
    ):
        assert forbidden not in payload


def test_r6_api_is_read_only_fixture_with_hidden_validation() -> None:
    response = TestClient(app).get("/api/v1/selection/fixtures/q5-r6")
    assert response.status_code == 200
    payload = response.json()
    assert payload["milestone"] == "Q5-R6"
    assert payload["productionAuthorized"] is False
    assert payload["inspector"]["performanceUiVisible"] is False
    assert payload["inspector"]["probabilityUiVisible"] is False


def test_path_outcome_requires_versions_cutoff_and_excursions() -> None:
    outcome = _outcomes(_cost_profile())[0]
    assert outcome.entry_policy_version == "EOD-CLOSE-ENTRY-V1"
    assert outcome.delisting_check_version == "NSE-DELISTING-PIT-V1"
    assert outcome.decision_at <= outcome.cutoff_at <= outcome.horizon_end
    assert outcome.mfe is not None and outcome.mfe >= 0
    assert outcome.mae is not None and outcome.mae <= 0

    for field in ("entry_policy_version", "delisting_check_version"):
        payload = outcome.model_dump(mode="python")
        payload[field] = ""
        with pytest.raises(ValidationError):
            PITOutcome.model_validate(payload)


def test_non_entry_outcome_cannot_manufacture_performance() -> None:
    no_entry = _no_entry_outcome(_cost_profile())
    assert no_entry.label.value == "NO_ENTRY"
    assert no_entry.gross_return == 0.0
    assert no_entry.net_return == 0.0
    assert no_entry.explicit_cost_bps == 0.0
    result = _validate(outcomes=(no_entry,))
    assert result.effective_sample == 0
    assert "PIT_SAMPLE_INSUFFICIENT" in result.blocker_codes

    payload = no_entry.model_dump(mode="python")
    payload["gross_return"] = 0.01
    with pytest.raises(ValidationError):
        PITOutcome.model_validate(payload)


def test_censored_path_requires_horizon_cutoff() -> None:
    outcome = _outcomes(_cost_profile())[-1]
    payload = outcome.model_dump(mode="python")
    payload["cutoff_at"] = outcome.horizon_end - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        PITOutcome.model_validate(payload)


def test_drift_cannot_precede_validation_baseline() -> None:
    with pytest.raises(ValueError):
        assess_validation_drift(
            validation=_approved(),
            metric_artifact=None,
            assessed_at=R6_EVALUATED_AT - timedelta(seconds=1),
        )


def test_inspector_claim_roles_and_sections_are_unique() -> None:
    inspector = _batch().inspector
    payload = inspector.model_dump(mode="python")
    payload["suppressed_claim_ids"] = payload["selected_claim_ids"]
    with pytest.raises(ValidationError):
        CandidateInspector.model_validate(payload)

    payload = inspector.model_dump(mode="python")
    payload["sections"] = (*payload["sections"], payload["sections"][0])
    with pytest.raises(ValidationError):
        CandidateInspector.model_validate(payload)


def test_fixture_batch_rejects_cross_view_state_mismatch() -> None:
    batch = _batch()
    payload = batch.model_dump(mode="python")
    payload["radar"][0]["state"] = SelectionState.WATCH
    with pytest.raises(ValidationError):
        Q5R6FixtureBatch.model_validate(payload)
