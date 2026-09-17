from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from trendforge_api import storage
from trendforge_api.historical_retention import RetentionReferenceType
from trendforge_api.retention_coverage import (
    CoverageStatus,
    audit_coverage,
    producer_registry,
    reconcile_pending_coverage,
    validate_registry,
)
from trendforge_api.retention_producer import DurableRetentionRegistrar
from trendforge_api.retention_publication import (
    RetentionEvidenceRoot,
    RetentionPublicationRequest,
    RetentionPublicationStore,
)
from trendforge_api.selection import r18_governance as governance
from trendforge_api.selection import r18_store
from trendforge_api.selection.r16_store import apply_r16_schema
from trendforge_api.selection.s8_persist_run import PROFILE_ID, SCHEMA_VERSION
from trendforge_api.selection.store import persist_selection_payload

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


class FakeAuthority:
    def register(self, reference):
        return reference


def _set_db(tmp_path: Path, monkeypatch) -> Path:
    db_path = tmp_path / "rhist03e.db"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    monkeypatch.delenv("TRENDFORGE_MARKET_DATA_DB_PATH", raising=False)
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    apply_r16_schema()
    r18_store.apply_rhist03d_schema()
    return db_path


def _profile(index: int):
    return governance.build_strategy_profile_version(
        profile_id=f"PRF-03E-{index}",
        profile_version="1.0.0",
        strategy_id="CONTINUATION",
        strategy_version="1.0.0",
        market="NSE",
        instrument_class="EQUITY",
        horizon="INTRADAY",
        timeframes=("5m",),
        setups=("BREAKOUT_CONTINUATION",),
        directions=("LONG", "SHORT"),
        required_to_calculate=("closed_bars",),
        required_to_qualify=("liquidity",),
        optional_context=(),
        prohibited_for_condition=("future_data",),
        relative_strength_contract="same-time-sector-v1",
        gate_policy="tradability-v1",
        ranking_group="intraday-continuation",
        risk_cost_assumptions=("cost-v1",),
        model_id=None,
        model_version=None,
        model_hash=None,
        research_ceiling="WAIT",
        activation_allowed=False,
        created_at=NOW + timedelta(seconds=index),
        valid_from=NOW,
    )


def _persist_profiles(count: int, *, finalize: int) -> None:
    for index in range(count):
        profile = _profile(index)
        assert r18_store.persist_strategy_profile(profile) is True
        if index < finalize:
            r18_store.finalize_rhist03d_artifact(
                "STRATEGY_PROFILE",
                profile.profile_id,
                profile.profile_version,
                verify_parents=True,
            )


def _statuses(report: dict) -> set[str]:
    return {str(row["status"]) for row in report["findings"]}


def test_registry_keeps_s8_and_r16_decision_producers_distinct() -> None:
    specs = [
        spec
        for spec in producer_registry()
        if spec.reference_type is RetentionReferenceType.DECISION_VERSION
    ]
    assert {spec.producer_id for spec in specs} == {
        "S8_DECISION_VERSION",
        "R16_DECISION_VERSION",
    }
    assert {spec.table for spec in specs} == {
        "selection_scan_runs",
        "pit_hypotheses",
    }


def test_dataset_members_are_not_an_independent_denominator_family() -> None:
    tables = {spec.table for spec in producer_registry()}
    assert "ml_frozen_datasets" in tables
    assert "ml_frozen_dataset_members" not in tables


def test_registry_validation_rejects_duplicate_owner() -> None:
    first = producer_registry()[0]
    errors = validate_registry((first, first))
    assert "DUPLICATE_PRODUCER_ID" in errors
    assert "DUPLICATE_AUTHORITATIVE_STORE_SCOPE" in errors


def test_empty_population_is_empty_not_pass(tmp_path, monkeypatch) -> None:
    _set_db(tmp_path, monkeypatch)
    report = audit_coverage(audit_at=NOW)
    assert report["expectedCount"] == 0
    assert report["coveredCount"] == 0
    assert report["coverage"] == 0.0
    assert report["verdict"] == "EMPTY"


def test_report_hash_is_deterministic_excluding_timestamp(tmp_path, monkeypatch) -> None:
    _set_db(tmp_path, monkeypatch)
    first = audit_coverage(audit_at=NOW)
    second = audit_coverage(audit_at=NOW + timedelta(hours=1))
    assert first["auditAt"] != second["auditAt"]
    assert first["reportHash"] == second["reportHash"]
    assert first["findings"] == second["findings"]


def test_pending_is_not_covered(tmp_path, monkeypatch) -> None:
    _set_db(tmp_path, monkeypatch)
    _persist_profiles(1, finalize=0)
    report = audit_coverage(audit_at=NOW)
    assert report["expectedCount"] == 1
    assert report["coveredCount"] == 0
    assert report["verdict"] == "FAIL"
    assert CoverageStatus.PENDING_RETENTION.value in _statuses(report)


def test_9_of_10_fails_from_real_artifact_denominator(tmp_path, monkeypatch) -> None:
    _set_db(tmp_path, monkeypatch)
    _persist_profiles(10, finalize=9)
    report = audit_coverage(audit_at=NOW)
    assert report["expectedCount"] == 10
    assert report["coveredCount"] == 9
    assert report["coverage"] == pytest.approx(0.9)
    assert report["verdict"] == "FAIL"
    assert report["countsByStatus"][CoverageStatus.PENDING_RETENTION.value] == 1


def test_10_of_10_passes_on_canonical_applied_proof(tmp_path, monkeypatch) -> None:
    _set_db(tmp_path, monkeypatch)
    _persist_profiles(10, finalize=10)
    report = audit_coverage(audit_at=NOW)
    assert report["expectedCount"] == 10
    assert report["coveredCount"] == 10
    assert report["coverage"] == 1.0
    assert report["orphanCount"] == 0
    assert report["blockingCount"] == 0
    assert report["verdict"] == "PASS"


def test_s8_artifact_without_publication_is_missing_retention(tmp_path, monkeypatch) -> None:
    _set_db(tmp_path, monkeypatch)
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "runId": "s8-missing-retention",
        "asOf": NOW.isoformat(),
        "tradingDate": "2026-09-13",
        "lineage": {},
        "rows": [],
    }
    persist_selection_payload(
        run_id=payload["runId"],
        profile_id=PROFILE_ID,
        as_of=NOW,
        payload=payload,
    )
    report = audit_coverage(audit_at=NOW)
    assert report["expectedCount"] == 1
    assert report["coveredCount"] == 0
    assert report["verdict"] == "FAIL"
    assert CoverageStatus.MISSING_RETENTION.value in _statuses(report)


def test_publication_without_real_artifact_is_retention_orphan(
    tmp_path, monkeypatch
) -> None:
    db_path = _set_db(tmp_path, monkeypatch)
    store = RetentionPublicationStore(
        db_path=db_path,
        registrar=DurableRetentionRegistrar(
            db_path=db_path,
            authority=FakeAuthority(),
        ),
    )
    request = RetentionPublicationRequest(
        artifact_type="S8_DECISION_VERSION",
        artifact_id="s8-orphan",
        artifact_version=SCHEMA_VERSION,
        reference_type=RetentionReferenceType.DECISION_VERSION,
        evidence_roots=(RetentionEvidenceRoot(role="ROOT", run_id="run-1"),),
        lineage={"s8PayloadHash": "a" * 64},
        created_at=NOW,
    )
    receipt = store.stage_owned(request)
    store.finalize(receipt.publication_id)
    store.mark_published(receipt.publication_id)
    report = audit_coverage(audit_at=NOW)
    assert report["expectedCount"] == 0
    assert report["coverage"] == 0.0
    assert report["verdict"] == "FAIL"
    assert report["orphanCount"] >= 1
    assert CoverageStatus.RETENTION_ORPHAN.value in _statuses(report)


def test_bounded_reconciliation_uses_existing_r18_owner(tmp_path, monkeypatch) -> None:
    _set_db(tmp_path, monkeypatch)
    _persist_profiles(2, finalize=0)
    first = reconcile_pending_coverage(limit=1)
    assert first["processed"] == 1
    assert first["after"]["expectedCount"] == 2
    assert first["after"]["coveredCount"] == 1
    assert first["after"]["verdict"] == "FAIL"
    second = reconcile_pending_coverage(limit=1)
    assert second["processed"] == 1
    assert second["after"]["coveredCount"] == 2
    assert second["after"]["verdict"] == "PASS"


def test_reconciliation_limit_must_be_positive(tmp_path, monkeypatch) -> None:
    _set_db(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="positive"):
        reconcile_pending_coverage(limit=0)


def test_missing_authoritative_table_fails_closed(tmp_path, monkeypatch) -> None:
    db_path = _set_db(tmp_path, monkeypatch)
    with storage.connect() as conn:
        conn.execute("DROP TABLE pit_revisions")
        conn.commit()
    report = audit_coverage(db_path=db_path, audit_at=NOW)
    assert report["verdict"] == "FAIL"
    assert CoverageStatus.REGISTRY_ERROR.value in _statuses(report)
