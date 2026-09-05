from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient


NOW = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
H = "a" * 64


def _manifest(state="CHALLENGER"):
    from trendforge_api.selection.r18_governance import ModelManifestV1, _hash

    values = dict(
        model_id="swing-trigger-quality",
        model_version="1.0.0",
        purpose="trigger quality",
        market="NSE_EQUITY",
        horizon="SWING",
        dataset_hash=H,
        feature_set_hash="b" * 64,
        formula_set_hash="c" * 64,
        created_at=NOW,
        state=state,
    )
    values["model_hash"] = _hash(
        values["model_id"], values["model_version"], values["purpose"],
        values["market"], values["horizon"], values["dataset_hash"],
        values["feature_set_hash"], values["formula_set_hash"],
    )
    return ModelManifestV1(**values)


def _fold(index: int, start: date, count: int = 20):
    from trendforge_api.selection.r18_governance import FoldPredictionV1

    probabilities = tuple(0.98 if i % 2 else 0.02 for i in range(count))
    outcomes = tuple(1 if i % 2 else 0 for i in range(count))
    return FoldPredictionV1(
        fold_index=index,
        train_end=start - timedelta(days=2),
        test_start=start,
        test_end=start + timedelta(days=1),
        embargo_sessions=1,
        probabilities=probabilities,
        outcomes=outcomes,
        net_r=tuple(0.2 for _ in range(count)),
    )


def _input(validation="PIT_NOT_APPROVED"):
    from trendforge_api.selection.r18_governance import ChallengerEvaluationInputV1

    return ChallengerEvaluationInputV1(
        manifest=_manifest(),
        r16_contract="trendforge.r16-pit.v1",
        r16_validation_status=validation,
        dataset_hash=H,
        cost_model_version="costs-1",
        folds=(_fold(0, date(2026, 1, 10)), _fold(1, date(2026, 2, 10))),
        holdout=_fold(2, date(2026, 3, 10)),
    )


def test_manifest_hashes_are_required_and_immutable():
    manifest = _manifest()
    assert manifest.state == "CHALLENGER"
    with pytest.raises(ValueError, match="MODEL_HASH_MISMATCH"):
        type(manifest).model_validate({**manifest.model_dump(), "model_hash": "f" * 64})


def test_evaluation_uses_walk_forward_embargo_costs_and_untouched_holdout():
    from trendforge_api.selection.r18_governance import evaluate_challenger

    result = evaluate_challenger(_input("PIT_APPROVED"), now=NOW)
    assert result.fold_count == 2
    assert result.observation_count == 40
    assert result.average_net_r_after_costs > 0
    assert result.holdout_average_net_r_after_costs > 0
    assert result.review_eligible is True
    assert result.automatic_promotion is False


def test_evaluation_is_not_review_eligible_while_r16_is_not_approved():
    from trendforge_api.selection.r18_governance import evaluate_challenger

    result = evaluate_challenger(_input(), now=NOW)
    assert result.review_eligible is False
    assert "PIT_NOT_APPROVED" in result.blockers


def test_overlapping_folds_and_touched_holdout_fail_closed():
    from trendforge_api.selection.r18_governance import ChallengerEvaluationInputV1

    payload = _input().model_dump()
    payload["folds"][1]["test_start"] = payload["folds"][0]["test_end"]
    payload["folds"][1]["train_end"] = payload["folds"][0]["test_start"] - timedelta(days=1)
    payload["folds"][1]["test_end"] = payload["folds"][0]["test_end"] + timedelta(days=1)
    with pytest.raises(ValueError, match="WALK_FORWARD_TEST_OVERLAP"):
        ChallengerEvaluationInputV1.model_validate(payload)


def test_human_approval_is_blocked_until_pit_approved():
    from trendforge_api.selection.r18_governance import build_promotion_review, evaluate_challenger

    evaluation = evaluate_challenger(_input(), now=NOW)
    with pytest.raises(ValueError, match="PIT_NOT_APPROVED"):
        build_promotion_review(
            manifest=_manifest(), evaluation=evaluation, decision="APPROVE",
            reviewer="risk-reviewer", reason="fixture", r16_validation_status="PIT_NOT_APPROVED", now=NOW,
        )


def test_rejection_is_signed_and_allowed_without_pit_approval():
    from trendforge_api.selection.r18_governance import build_promotion_review, evaluate_challenger

    review = build_promotion_review(
        manifest=_manifest(), evaluation=evaluate_challenger(_input(), now=NOW),
        decision="REJECT", reviewer="risk-reviewer", reason="insufficient PIT history",
        r16_validation_status="PIT_NOT_APPROVED", previous_record_hash="d" * 64, now=NOW,
    )
    assert review.effective_state == "REJECTED"
    assert len(review.record_hash) == 64
    assert len(review.evidence_hash) == 64
    assert review.signature_scheme == "SHA256_CHAIN_V1"
    assert review.previous_record_hash == "d" * 64


def test_drift_demotes_champion_and_restores_previous_signed_champion():
    from trendforge_api.selection.r18_governance import assess_drift

    result = assess_drift(
        manifest=_manifest("CHAMPION"), feature_psi=0.3,
        prediction_psi=0.1, calibration_delta=0.06,
        previous_champion_hash="e" * 64, now=NOW,
    )
    assert result.resulting_state == "STALE_MODEL"
    assert result.breached == ("FEATURE_DRIFT", "CALIBRATION_DRIFT")
    assert result.rollback_model_hash == "e" * 64
    assert result.rollback_state == "CHAMPION"
    assert result.automatic_promotion is False


def test_r18_store_is_append_only_and_uses_explicit_schema(tmp_path, monkeypatch):
    from trendforge_api import storage
    from trendforge_api.selection.r18_store import apply_schema, persist_manifest, schema_status

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r18.db")
    assert schema_status()["applied"] is False
    assert apply_schema()["applied"] is True
    payload = _manifest().model_dump(mode="json", by_alias=True)
    assert persist_manifest(payload) is True
    assert persist_manifest(payload) is False
    changed = {**payload, "purpose": "tampered"}
    with pytest.raises(ValueError, match="R18_ARTIFACT_IMMUTABLE"):
        persist_manifest(changed)


def test_governance_status_hides_probability_and_execution(monkeypatch):
    import trendforge_api.selection.r18_governance as module

    monkeypatch.setattr(module, "r16_status_payload", lambda: {
        "validationStatus": "PIT_NOT_APPROVED", "datasetStatus": "BUILDING",
        "blockers": ["INSUFFICIENT_PIT_DATES"],
    })
    monkeypatch.setattr(module, "r16_runs_payload", lambda limit=1: {"runs": []})
    status = module.governance_status()
    assert status["modelState"] == "MODEL_NOT_APPROVED"
    assert status["probabilityVisible"] is False
    assert status["winRateVisible"] is False
    assert status["performanceVisible"] is False
    assert status["executionAuthorized"] is False


def test_governance_status_calculates_dataset_age(monkeypatch):
    import trendforge_api.selection.r18_governance as module

    monkeypatch.setattr(module, "r16_status_payload", lambda: {
        "validationStatus": "PIT_NOT_APPROVED", "datasetStatus": "BUILDING",
        "blockers": [],
    })
    today = datetime.now(UTC).date()
    monkeypatch.setattr(module, "r16_runs_payload", lambda limit=1: {
        "runs": [{"tradingDate": (today - timedelta(days=3)).isoformat()}]
    })
    assert module.governance_status()["datasetAgeDays"] == 3


def test_governance_get_is_read_only_and_review_post_fails_closed(tmp_path, monkeypatch):
    from trendforge_api import main, storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r18-api.db")
    client = TestClient(main.app)
    response = client.get("/api/research/ml/governance")
    assert response.status_code == 200
    payload = response.json()
    assert payload["modelState"] == "MODEL_NOT_APPROVED"
    assert payload["probabilityVisible"] is False
    assert payload["schema"]["applied"] is False
    assert "WAIT_R18_SCHEMA_NOT_APPLIED" in payload["blockers"]
    blocked = client.post("/api/research/ml/reviews", json={})
    assert blocked.status_code == 503
    assert blocked.json()["detail"]["code"] == "WAIT_R18_SCHEMA_NOT_APPLIED"




def test_offline_service_requires_real_r16_dataset_hash(tmp_path, monkeypatch):
    from trendforge_api import storage
    import trendforge_api.selection.r18_service as service
    from trendforge_api.selection.r18_store import apply_schema

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r18-service.db")
    apply_schema()
    monkeypatch.setattr(service, "r16_schema_status", lambda: {"applied": True})
    monkeypatch.setattr(service, "list_dataset_runs", lambda limit=500000: [])
    with pytest.raises(ValueError, match="R16_PIT_DATASET_HASH_NOT_FOUND"):
        service.run_offline_challenger_evaluation(_input())


def test_offline_service_persists_only_proven_r16_dataset(tmp_path, monkeypatch):
    from trendforge_api import storage
    import trendforge_api.selection.r18_service as service
    from trendforge_api.selection.r18_store import apply_schema, list_payloads

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r18-service-ok.db")
    apply_schema()
    monkeypatch.setattr(service, "r16_schema_status", lambda: {"applied": True})
    monkeypatch.setattr(service, "list_dataset_runs", lambda limit=500000: [
        {"datasetRevisionHash": H, "datasetStatus": "BUILDING"}
    ])
    result = service.run_offline_challenger_evaluation(_input())
    assert result.review_eligible is False
    assert len(list_payloads("ml_model_registry")) == 1
    assert len(list_payloads("ml_evaluation_reports")) == 1


def test_review_route_loads_persisted_evidence_and_blocks_approval(tmp_path, monkeypatch):
    from trendforge_api import main, storage
    from trendforge_api.selection.r18_governance import evaluate_challenger
    from trendforge_api.selection.r18_store import (
        apply_schema, persist_evaluation, persist_manifest
    )

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r18-review.db")
    apply_schema()
    manifest = _manifest()
    evaluation = evaluate_challenger(_input(), now=NOW)
    persist_manifest(manifest.model_dump(mode="json", by_alias=True))
    persist_evaluation(evaluation.model_dump(mode="json", by_alias=True))
    monkeypatch.setattr(main, "r16_status_payload", lambda: {
        "validationStatus": "PIT_NOT_APPROVED"
    })
    client = TestClient(main.app)
    body = {
        "modelId": manifest.model_id,
        "modelHash": manifest.model_hash,
        "evaluationId": evaluation.evaluation_id,
        "decision": "REJECT",
        "reviewer": "risk-reviewer",
        "reason": "insufficient PIT history",
    }
    rejected = client.post("/api/research/ml/reviews", json=body)
    assert rejected.status_code == 200
    assert rejected.json()["effectiveState"] == "REJECTED"
    approved = client.post(
        "/api/research/ml/reviews", json={**body, "decision": "APPROVE"}
    )
    assert approved.status_code == 409
    assert "PIT_NOT_APPROVED" in approved.json()["detail"]["code"]
    fabricated = client.post(
        "/api/research/ml/reviews",
        json={"manifest": manifest.model_dump(mode="json", by_alias=True)},
    )
    assert fabricated.status_code == 404

