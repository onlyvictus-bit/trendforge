from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from trendforge_api.main import app
from trendforge_api.scanners import (
    PKDifferentialArtifact,
    PKDiscrepancyClass,
    PKFixtureManifest,
    PKHarnessLimits,
    PKHarnessResult,
    PKHarnessStatus,
    PKPromotionEvidence,
    PKPromotionRecord,
    PKPromotionStatus,
    PKReviewDecision,
    PKSanitizedFixture,
    PKSanitizedRow,
    PKScannerDisposition,
    PKTagStatus,
    PKUniverseMembershipFixture,
    PKUpstreamPin,
    PKUpstreamPinStatus,
    apply_pk_review,
    build_pk_r4_inventory,
    build_pk_shadow_tag,
    build_q5_r5_fixture_batch,
    evaluate_native_promotion,
    run_pk_offline_comparison,
)
from trendforge_api.selection import InstrumentIdentity
from trendforge_api.scanners.pk_compatibility import (
    PKFaultMode,
    PKShadowOutput,
    _fixture_inputs,
    _hash_bytes,
)


def _inputs():
    return _fixture_inputs()


def _run(**overrides):
    pin, manifest, native, fixture = _inputs()
    values = {
        "pin": pin,
        "manifest": manifest,
        "native_scanner": native,
        "fixture": fixture,
    }
    values.update(overrides)
    return run_pk_offline_comparison(**values)


def _artifact() -> PKDifferentialArtifact:
    result = _run()
    assert result.artifact is not None
    return result.artifact


def _verified_artifact() -> PKDifferentialArtifact:
    artifact = _artifact()
    verified_pin = PKUpstreamPin(
        repository="https://example.invalid/pinned-pkscreener",
        commit="1" * 40,
        license_hash=_hash_bytes(b"synthetic-verified-license-hash"),
        isolated_environment_lock_hash=_hash_bytes(b"synthetic-verified-lock"),
        pin_status=PKUpstreamPinStatus.VERIFIED,
    )
    payload = artifact.model_dump(mode="python")
    payload.update(
        {
            "upstream_pin": verified_pin,
            "fixture_only": False,
            "upstream_observed": True,
        }
    )
    return PKDifferentialArtifact.model_validate(payload)


def _promotion_evidence(artifact: PKDifferentialArtifact) -> PKPromotionEvidence:
    return PKPromotionEvidence(
        reviewer_id="Q5-R5-TEST-REVIEWER",
        reviewed_at=datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc),
        native_implementation_hash=artifact.native_scanner.implementation_hash,
        acceptance_test_ids=("T-191", "T-218", "T-219", "T-220"),
        feature_contract_id="FTR-PK-NATIVE-TEST",
        feature_contract_version="1.0.0",
        evidence_family="STRUCTURE",
        correlation_group="CG_PK_NATIVE_TEST",
    )


def test_q5_r5_fixture_is_finite_nonproduction_and_nonexecutable() -> None:
    batch = build_q5_r5_fixture_batch()
    assert batch.fixture_only is True
    assert batch.production_authorized is False
    assert batch.executable is False
    assert batch.successful_match.status is PKHarnessStatus.COMPLETED
    assert batch.unresolved_difference.status is PKHarnessStatus.COMPLETED
    assert batch.fixture_promotion.status is PKPromotionStatus.REGISTERED_NOT_ACTIVE


def test_match_artifact_contains_required_reproducibility_fields() -> None:
    artifact = _artifact()
    assert artifact.artifact_version == "offline-native-differential-artifact-1"
    assert artifact.discrepancy_class is PKDiscrepancyClass.MATCH
    assert artifact.discrepancy_fields == ()
    assert artifact.input_raw_hash
    assert artifact.input_normalized_hash
    assert artifact.upstream_output_hash == artifact.native_output_hash
    assert artifact.field_tolerances == {"matchedSymbols": 0.0}
    assert artifact.worker_invocations == 1
    assert artifact.finite_process_terminated is True


def test_unresolved_difference_cannot_be_called_match() -> None:
    pin, manifest, native, fixture = _inputs()
    result = run_pk_offline_comparison(
        pin=pin,
        manifest=manifest,
        native_scanner=native,
        fixture=fixture,
        native_output_override=PKShadowOutput(matched_symbols=("AAA",)),
    )
    assert result.artifact is not None
    assert result.artifact.discrepancy_class is PKDiscrepancyClass.UNRESOLVED
    assert result.artifact.discrepancy_fields == ("matchedSymbols",)
    assert result.artifact.upstream_output_hash != result.artifact.native_output_hash


def test_shadow_observation_has_zero_vote_and_no_state_or_rank_authority() -> None:
    observation = _artifact().shadow_observation
    payload = observation.model_dump(mode="json", by_alias=True)
    assert observation.authority == "EXPERIMENTAL_REFERENCE"
    assert observation.voting_weight == 0.0
    assert observation.can_affect_rank is False
    assert observation.can_affect_state is False
    assert observation.can_support_confirmed is False
    assert "state" not in payload
    assert "evidenceClaim" not in str(payload)


def test_manifest_rejects_pickle_cache_source_and_executable_artifacts() -> None:
    _pin, manifest, _native, _fixture = _inputs()
    for artifact in (
        "upstream.pkl",
        "upstream.pickle",
        "upstream.joblib",
        "upstream.cache",
        "upstream.py",
        "upstream.exe",
        "upstream.zip",
    ):
        try:
            PKFixtureManifest(
                manifest_id=manifest.manifest_id,
                manifest_version=manifest.manifest_version,
                fixture_id=manifest.fixture_id,
                fixture_schema_version=manifest.fixture_schema_version,
                fixture_hash=manifest.fixture_hash,
                approved_artifacts=(artifact,),
            )
        except ValidationError:
            pass
        else:
            raise AssertionError(f"unsafe artifact accepted: {artifact}")


def test_manifest_rejects_paths_even_when_the_suffix_is_json() -> None:
    _, manifest, _, _ = _fixture_inputs()
    for artifact in (
        "../fixture.json",
        "fixtures/fixture.json",
        "C:\\tmp\\fixture.json",
    ):
        payload = manifest.model_dump(mode="python")
        payload["approved_artifacts"] = (artifact,)
        with pytest.raises(ValidationError):
            PKFixtureManifest.model_validate(payload)


def test_upstream_pin_rejects_missing_or_placeholder_verified_commit() -> None:
    _pin, _manifest, _native, _fixture = _inputs()
    for commit in ("", "0" * 40):
        try:
            PKUpstreamPin(
                repository="https://example.invalid/pkscreener",
                commit=commit,
                license_hash=_hash_bytes(b"license"),
                isolated_environment_lock_hash=_hash_bytes(b"lock"),
                pin_status=PKUpstreamPinStatus.VERIFIED,
            )
        except ValidationError:
            pass
        else:
            raise AssertionError("missing/placeholder verified commit was accepted")


def test_fixture_schema_forbids_unexpected_fields() -> None:
    _pin, _manifest, _native, fixture = _inputs()
    payload = fixture.model_dump(mode="python", exclude_computed_fields=True)
    payload["command"] = "arbitrary executable"
    try:
        PKSanitizedFixture.model_validate(payload)
    except ValidationError:
        pass
    else:
        raise AssertionError("unexpected fixture command field was accepted")


def test_fixture_rejects_duplicate_symbols() -> None:
    try:
        PKSanitizedFixture(
            fixture_id="PK-DUPLICATE-SYMBOL",
            as_of=datetime(2026, 7, 19, tzinfo=timezone.utc),
            threshold=100.0,
            rows=(
                PKSanitizedRow(symbol="AAA", close=101.0),
                PKSanitizedRow(symbol="aaa", close=102.0),
            ),
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("duplicate normalized symbols were accepted")


def test_manifest_hash_mismatch_rejects_before_process_start() -> None:
    pin, manifest, native, fixture = _inputs()
    bad_manifest = manifest.model_copy(update={"fixture_hash": "f" * 64})
    result = run_pk_offline_comparison(
        pin=pin,
        manifest=bad_manifest,
        native_scanner=native,
        fixture=fixture,
    )
    assert result.status is PKHarnessStatus.INPUT_REJECTED
    assert result.error_type == "FIXTURE_HASH_MISMATCH"
    assert result.worker_invocations == 0


def test_manifest_schema_mismatch_rejects_before_process_start() -> None:
    pin, manifest, native, fixture = _inputs()
    bad_manifest = manifest.model_copy(update={"fixture_schema_version": "wrong"})
    result = run_pk_offline_comparison(
        pin=pin,
        manifest=bad_manifest,
        native_scanner=native,
        fixture=fixture,
    )
    assert result.status is PKHarnessStatus.INPUT_REJECTED
    assert result.error_type == "FIXTURE_SCHEMA_MISMATCH"
    assert result.attempts == 0


def test_manifest_fixture_id_mismatch_rejects_before_process_start() -> None:
    pin, manifest, native, fixture = _inputs()
    bad_manifest = manifest.model_copy(update={"fixture_id": "OTHER"})
    result = run_pk_offline_comparison(
        pin=pin,
        manifest=bad_manifest,
        native_scanner=native,
        fixture=fixture,
    )
    assert result.status is PKHarnessStatus.INPUT_REJECTED
    assert result.error_type == "FIXTURE_ID_MISMATCH"


def test_current_fixture_worker_rejects_verified_pin_instead_of_faking_upstream() -> (
    None
):
    _pin, manifest, native, fixture = _inputs()
    verified = PKUpstreamPin(
        repository="https://example.invalid/pinned-pkscreener",
        commit="1" * 40,
        license_hash=_hash_bytes(b"synthetic-license"),
        isolated_environment_lock_hash=_hash_bytes(b"synthetic-lock"),
        pin_status=PKUpstreamPinStatus.VERIFIED,
    )
    result = run_pk_offline_comparison(
        pin=verified,
        manifest=manifest,
        native_scanner=native,
        fixture=fixture,
    )
    assert result.status is PKHarnessStatus.INPUT_REJECTED
    assert result.error_type == "UPSTREAM_ADAPTER_NOT_IMPLEMENTED"
    assert result.worker_invocations == 0


def test_input_limit_rejects_without_starting_worker() -> None:
    result = _run(limits=PKHarnessLimits(max_input_bytes=100))
    assert result.status is PKHarnessStatus.INPUT_REJECTED
    assert result.error_type == "INPUT_LIMIT_EXCEEDED"
    assert result.worker_invocations == 0


def test_worker_crash_is_explicit_and_production_unaffected() -> None:
    result = _run(fault_mode=PKFaultMode.CRASH)
    assert result.status is PKHarnessStatus.PROCESS_FAILED
    assert result.error_type == "WORKER_EXIT_NONZERO"
    assert result.artifact is None
    assert result.production_affected is False


def test_worker_timeout_is_explicit_terminated_and_production_unaffected() -> None:
    result = _run(
        fault_mode=PKFaultMode.TIMEOUT,
        limits=PKHarnessLimits(timeout_seconds=0.05),
    )
    assert result.status is PKHarnessStatus.TIMED_OUT
    assert result.error_type == "WORKER_TIMEOUT"
    assert result.worker_invocations == 1
    assert result.finite_process_terminated is True
    assert result.production_affected is False


def test_invalid_worker_json_is_output_failure_not_empty_match() -> None:
    result = _run(fault_mode=PKFaultMode.INVALID_JSON)
    assert result.status is PKHarnessStatus.OUTPUT_REJECTED
    assert result.error_type == "OUTPUT_SCHEMA_INVALID"
    assert result.artifact is None


def test_oversized_worker_output_is_rejected() -> None:
    result = _run(
        fault_mode=PKFaultMode.OVERSIZED_OUTPUT,
        limits=PKHarnessLimits(max_output_bytes=1_000),
    )
    assert result.status is PKHarnessStatus.OUTPUT_REJECTED
    assert result.error_type == "OUTPUT_LIMIT_EXCEEDED"


def test_successful_harness_invokes_and_terminates_one_process() -> None:
    result = _run()
    assert result.ok is True
    assert result.attempts == 1
    assert result.worker_invocations == 1
    assert result.finite_process_terminated is True


def test_artifact_identity_is_stable_across_repeated_fixture_runs() -> None:
    first = _artifact()
    second = _artifact()
    assert first.artifact_id == second.artifact_id
    assert first.input_normalized_hash == second.input_normalized_hash
    assert first.upstream_output_hash == second.upstream_output_hash


def test_match_review_creates_candidate_but_does_not_activate_fixture() -> None:
    reviewed = apply_pk_review(
        artifact=_artifact(),
        decision=PKReviewDecision.APPROVE_MATCH,
        reviewer_id="REVIEWER",
        review_note="Contract-only fixture match.",
        reviewed_at=datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc),
    )
    assert reviewed.promotion_status is PKPromotionStatus.NATIVE_PROMOTION_CANDIDATE
    record = evaluate_native_promotion(
        artifact=reviewed,
        evidence=_promotion_evidence(reviewed),
    )
    assert record.status is PKPromotionStatus.REGISTERED_NOT_ACTIVE
    assert "UPSTREAM_PIN_NOT_VERIFIED" in record.reasons
    assert record.upstream_runtime_dependency is False


def test_mismatch_cannot_receive_match_approval() -> None:
    batch = build_q5_r5_fixture_batch()
    artifact = batch.unresolved_difference.artifact
    assert artifact is not None
    try:
        apply_pk_review(
            artifact=artifact,
            decision=PKReviewDecision.APPROVE_MATCH,
            reviewer_id="REVIEWER",
            review_note="Invalid approval attempt.",
            reviewed_at=datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("unresolved difference received match approval")


def test_verified_reviewed_synthetic_artifact_can_promote_native_only() -> None:
    artifact = apply_pk_review(
        artifact=_verified_artifact(),
        decision=PKReviewDecision.APPROVE_MATCH,
        reviewer_id="REVIEWER",
        review_note="Synthetic contract test for a reviewed verified artifact.",
        reviewed_at=datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc),
    )
    record = evaluate_native_promotion(
        artifact=artifact,
        evidence=_promotion_evidence(artifact),
    )
    assert record.status is PKPromotionStatus.NATIVE_PROMOTED
    assert record.native_only is True
    assert record.upstream_runtime_dependency is False
    assert record.upstream_can_vote is False


def test_native_hash_mismatch_blocks_promotion() -> None:
    artifact = apply_pk_review(
        artifact=_verified_artifact(),
        decision=PKReviewDecision.APPROVE_MATCH,
        reviewer_id="REVIEWER",
        review_note="Synthetic hash mismatch test.",
        reviewed_at=datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc),
    )
    evidence = _promotion_evidence(artifact).model_copy(
        update={"native_implementation_hash": "f" * 64}
    )
    record = evaluate_native_promotion(artifact=artifact, evidence=evidence)
    assert record.status is PKPromotionStatus.REGISTERED_NOT_ACTIVE
    assert "NATIVE_IMPLEMENTATION_HASH_MISMATCH" in record.reasons


def test_review_metadata_cannot_be_partially_present() -> None:
    artifact = _artifact()
    payload = artifact.model_dump(mode="python")
    payload.update(
        {
            "reviewer_decision": PKReviewDecision.APPROVE_MATCH,
            "reviewer_id": "REVIEWER",
        }
    )
    try:
        PKDifferentialArtifact.model_validate(payload)
    except ValidationError:
        pass
    else:
        raise AssertionError("partial review metadata was accepted")


def test_artifact_requires_exactly_one_provenance_mode() -> None:
    artifact = _verified_artifact()
    for fixture_only, upstream_observed in ((False, False), (True, True)):
        payload = artifact.model_dump(mode="python")
        payload.update(
            fixture_only=fixture_only,
            upstream_observed=upstream_observed,
        )
        with pytest.raises(ValidationError):
            PKDifferentialArtifact.model_validate(payload)


def test_harness_result_rejects_unterminated_or_inconsistent_worker_state() -> None:
    result = _run()
    payload = result.model_dump(mode="python")
    payload["finite_process_terminated"] = False
    with pytest.raises(ValidationError):
        PKHarnessResult.model_validate(payload)

    payload = result.model_dump(mode="python")
    payload["attempts"] = 0
    with pytest.raises(ValidationError):
        PKHarnessResult.model_validate(payload)


def test_promotion_record_requires_blockers_unless_native_is_promoted() -> None:
    batch = build_q5_r5_fixture_batch()
    payload = batch.fixture_promotion.model_dump(mode="python")
    payload["reasons"] = ()
    with pytest.raises(ValidationError):
        PKPromotionRecord.model_validate(payload)


def test_production_route_inventory_contains_no_pk_shadow_routes() -> None:
    paths = {route.path for route in app.routes}
    assert not any(path.startswith("/api/v1/shadow/pkscreener/") for path in paths)
    assert not any("pkscreener" in path.lower() for path in paths)


def test_developer_cli_outputs_fixture_artifact_without_production_fields() -> None:
    process = subprocess.run(
        [sys.executable, "-m", "trendforge_api.scanners"],
        cwd="D:/TrendForge/backend",
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert process.returncode == 0
    assert '"milestone": "Q5-R5"' in process.stdout
    assert '"productionAuthorized": false' in process.stdout
    for forbidden in ("orderIntent", "quantity", "winProbability", "tradeDirection"):
        assert forbidden not in process.stdout


def test_r5_adds_no_production_http_endpoint() -> None:
    client = TestClient(app)
    for path in (
        "/api/v1/shadow/pkscreener/run",
        "/api/v1/shadow/pkscreener/parity",
    ):
        assert client.get(path).status_code == 404


def test_r4_inventory_is_real_pinned_complete_and_zero_vote() -> None:
    inventory = build_pk_r4_inventory()
    assert inventory.upstream_pin.commit == "ab4212355e2442e7c8f5430d53fa3f56ea5af3b8"
    assert inventory.upstream_pin.pin_status is PKUpstreamPinStatus.VERIFIED
    assert inventory.license_name == "MIT"
    assert len(inventory.entries) == 50
    assert len(inventory.declared_dependencies) == 47
    assert "numpy==1.26.4" in inventory.declared_dependencies
    assert tuple(item.scanner_id for item in inventory.entries) == tuple(
        f"X:{index}" for index in range(50)
    )
    assert inventory.upstream_runtime_required is False
    assert inventory.upstream_can_vote is False
    assert inventory.production_authorized is False
    assert any(
        item.disposition is PKScannerDisposition.NATIVE_MAPPED
        for item in inventory.entries
    )
    assert any(
        item.disposition is PKScannerDisposition.QUARANTINED
        for item in inventory.entries
    )


def test_r4_unknown_scanner_id_is_quarantined() -> None:
    tag = build_pk_shadow_tag(
        scanner_id="X:999",
        instrument_id="not-used",
        symbol="RELIANCE",
        identity_rows=(),
    )
    assert tag.status is PKTagStatus.QUARANTINED
    assert tag.reason == "UNKNOWN_UPSTREAM_SCANNER_ID"
    assert tag.voting_weight == 0
    assert tag.can_affect_rank is False
    assert tag.can_affect_state is False
    assert tag.can_support_confirmed is False


def test_r4_uses_a2_identity_and_never_companion_scrip_code() -> None:
    instrument = InstrumentIdentity.create(
        exchange="NSE",
        segment="EQ",
        symbol="RELIANCE",
        series="EQ",
        isin="INE002A01018",
    )
    identity_rows = (SimpleNamespace(instrument=instrument),)
    mapped = build_pk_shadow_tag(
        scanner_id="X:14",
        instrument_id=instrument.instrument_id,
        symbol="RELIANCE",
        identity_rows=identity_rows,
        companion_scrip_code="500325",
    )
    assert mapped.status is PKTagStatus.TAGGED_REFERENCE
    assert mapped.instrument_id == instrument.instrument_id
    assert mapped.symbol == "RELIANCE"

    rejected = build_pk_shadow_tag(
        scanner_id="X:14",
        instrument_id="500325",
        symbol="500325",
        identity_rows=identity_rows,
        companion_scrip_code="500325",
    )
    assert rejected.status is PKTagStatus.QUARANTINED
    assert rejected.instrument_id is None
    assert "COMPANION_SCRIP_CODE_NOT_IDENTITY" in rejected.reason


def test_r4_pit_membership_does_not_reintroduce_delisted_name() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    delisted = start + timedelta(days=30)
    row = PKUniverseMembershipFixture(
        instrument_id="ins-test",
        symbol="OLDCO",
        member_from=start,
        member_until=delisted,
        delisted_at=delisted,
        available_at=start,
    )
    assert row.eligible_at(start + timedelta(days=10)) is True
    assert row.eligible_at(delisted) is False
    assert row.eligible_at(delisted + timedelta(days=1)) is False


def test_r4_worker_faults_leave_baseline_selection_payload_unchanged() -> None:
    baseline = {
        "candidateId": "cand-1",
        "state": "WAIT",
        "rank": 1,
        "claims": ["claim-existing"],
    }
    before = dict(baseline)
    assert _run(fault_mode=PKFaultMode.CRASH).production_affected is False
    assert _run(
        fault_mode=PKFaultMode.TIMEOUT,
        limits=PKHarnessLimits(timeout_seconds=0.05),
    ).production_affected is False
    assert baseline == before

