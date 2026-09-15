"""R-HIST-03F M0 — golden baseline, crash recovery, replay/idempotency.

Every scenario uses two independent oracles:
  Oracle A — direct persisted-state inspection (SQL rows, hashes, states).
  Oracle B — accepted 03E `audit_coverage()` verdict.

Scratch DBs only. Fixed timestamps only. No live network.
Scenario IDs: F_GOLDEN_00, F_CRASH_01..04, F_REPLAY_01/02/06.
"""
from __future__ import annotations

import sqlite3
from datetime import timedelta

import pytest

from trendforge_api import storage
from trendforge_api.historical_retention import RetentionReferenceType
from trendforge_api.retention_coverage import CoverageStatus, reconcile_pending_coverage
from trendforge_api.retention_producer import (
    DurableRetentionRegistrar,
    RetentionEvidenceIntent,
    RetentionOutboxStatus,
)
from trendforge_api.selection import r18_governance as governance
from trendforge_api.selection import r18_store
from trendforge_api.selection.r18_history_finalization import (
    verify_governed_rhist03d_artifact,
)
from trendforge_api.selection.r18_history_store import persist_frozen_dataset

from tests.rhist03f_harness import (
    NOW,
    assert_manifest_healthy,
    assert_manifests_equal,
    authority_row,
    build_profile,
    capture_manifest,
    count_authority_refs,
    coverage_report,
    init_db,
    link_state,
    outbox_count,
    outbox_row,
    persist_profile,
    profile_state,
    restart,
)

H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64
H6 = "6" * 64

DECISION_AT = NOW - timedelta(days=8)
LABEL_AT = DECISION_AT + timedelta(days=3)


def _statuses(report: dict) -> set[str]:
    return {str(row["status"]) for row in report["findings"]}


def _dataset_manifest(tag: str):
    member = governance.build_frozen_dataset_member(
        instrument_id="NSE:INFY:EQ",
        opportunity_id="INFY:EOD:continuation:SHORT",
        profile_id="PRF-R16-NSE-CASH-EOD-SWING",
        profile_version="1.0.0",
        strategy_id="R16_SWING",
        strategy_version="1.0.0",
        setup_id="SWING_BREAKOUT_BREAKDOWN_V1",
        setup_episode_id="episode-1",
        timeframe="EOD",
        horizon="SWING",
        direction="BEARISH",
        decision_version_id="D100v1",
        decision_version_hash=H1,
        decision_at=DECISION_AT,
        decision_data_cutoff=DECISION_AT,
        max_feature_available_at=DECISION_AT - timedelta(seconds=1),
        public_state="WATCH",
        outcome_id="O1",
        outcome_hash=H2,
        outcome_state="TARGET",
        outcome_available_at=LABEL_AT,
        revision_id=None,
        revision_hash=None,
        revision_available_at=None,
        label_available_at=LABEL_AT,
        feature_manifest_id="r16-source-features-v1",
        feature_manifest_hash=H3,
        formula_set_version="r16-policy-bundle-v1",
        formula_set_hash=H4,
        input_hashes=(H5,),
        evidence_roots=(
            {"role": "DECISION_MARKET_EVIDENCE", "contentHash": H5},
            {"role": "OUTCOME_MARKET_EVIDENCE", "contentHash": H6},
        ),
        split="TRAIN",
        fold="F1",
        inclusion_reason="BASE_POPULATION",
        exclusion_reason=None,
    )
    decision_cutoff = DECISION_AT
    label_cutoff = LABEL_AT + timedelta(days=1)
    build_cutoff = LABEL_AT + timedelta(days=2)
    return governance.build_frozen_dataset_manifest(
        dataset_id=f"DS-03F-{tag}",
        dataset_version="1.0.0",
        purpose="TRAIN",
        created_at=build_cutoff,
        decision_cutoff=decision_cutoff,
        label_cutoff=label_cutoff,
        build_cutoff=build_cutoff,
        population_policy_id="R16_COMPLETE_BASE_POPULATION",
        population_policy_version="1.0.0",
        label_policy_id="R16_LABEL_POLICY",
        label_policy_version="1.0.0",
        feature_manifest_id="r16-source-features-v1",
        feature_manifest_hash=H3,
        formula_set_version="r16-policy-bundle-v1",
        formula_set_hash=H4,
        cost_model_version="cost-v1",
        members=(member.model_dump(mode="python", by_alias=False),),
        base_population=True,
        source_population_count=1,
        code_digest=None,
    )


# ---------------------------------------------------------------------------
# F_GOLDEN_00 — healthy baseline passes both oracles and survives restart
# ---------------------------------------------------------------------------


def test_F_GOLDEN_00_healthy_graph_passes_both_oracles_and_survives_restart(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    identities = [persist_profile(index) for index in range(3)]

    # Oracle B: accepted 03E coverage.
    report = coverage_report(db_path)
    assert report["expectedCount"] == 3
    assert report["coveredCount"] == 3
    assert report["coverage"] == 1.0
    assert report["orphanCount"] == 0
    assert report["blockingCount"] == 0
    assert report["verdict"] == "PASS"
    assert coverage_report(db_path, audit_at=NOW + timedelta(hours=1))["reportHash"] == report["reportHash"]

    # Oracle A: direct persisted-state proof agrees.
    manifest = capture_manifest(db_path, identities)
    assert_manifest_healthy(manifest)

    # Realistic restart: drop process-local state, re-read from disk.
    restart()
    manifest_after = capture_manifest(db_path, identities)
    assert_manifests_equal(manifest, manifest_after)
    assert coverage_report(db_path)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# F_CRASH_01 — crash before the artifact transaction begins
# ---------------------------------------------------------------------------


def test_F_CRASH_01_crash_before_artifact_transaction_leaves_no_phantom(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    registrar = DurableRetentionRegistrar(db_path=db_path)

    # Nothing was ever written: unknown dispatch fails, coverage is EMPTY.
    with pytest.raises(KeyError, match="unknown retention outbox event"):
        registrar.dispatch("rhist03:does-not-exist")
    assert outbox_count(db_path) == 0

    report = coverage_report(db_path)
    assert report["expectedCount"] == 0
    assert report["verdict"] == "EMPTY"
    assert report["verdict"] != "PASS"


# ---------------------------------------------------------------------------
# F_CRASH_02 — crash inside the artifact transaction before COMMIT
# ---------------------------------------------------------------------------


def test_F_CRASH_02a_dataset_crash_after_artifact_insert_rolls_back_intent(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    manifest_model = _dataset_manifest("ROLLBACK")

    with pytest.raises(RuntimeError, match="INJECTED_AFTER_ARTIFACT_INSERT"):
        persist_frozen_dataset(manifest_model, fault_point="AFTER_ARTIFACT_INSERT")

    # Oracle A: artifact, members, link, and outbox intent all rolled back.
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        assert (
            conn.execute(
                "SELECT COUNT(*) AS n FROM ml_frozen_datasets WHERE dataset_id=?",
                (manifest_model.dataset_id,),
            ).fetchone()["n"]
            == 0
        )
        assert (
            conn.execute("SELECT COUNT(*) AS n FROM ml_frozen_dataset_members").fetchone()["n"]
            == 0
        )
        assert (
            conn.execute("SELECT COUNT(*) AS n FROM r18_retention_links").fetchone()["n"] == 0
        )
    assert outbox_count(db_path) == 0

    # Oracle B: no phantom governed artifact.
    report = coverage_report(db_path)
    assert report["expectedCount"] == 0
    assert report["verdict"] == "EMPTY"


def test_F_CRASH_02b_profile_crash_before_commit_rolls_back_artifact_and_intent(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)

    def _crash(self, intent, *, connection=None):
        raise RuntimeError("INJECTED_ENQUEUE_CRASH")

    monkeypatch.setattr(DurableRetentionRegistrar, "enqueue", _crash)
    with pytest.raises(RuntimeError, match="INJECTED_ENQUEUE_CRASH"):
        r18_store.persist_strategy_profile(build_profile(21))

    # Oracle A: same-transaction atomicity — artifact survives IFF intent survives.
    assert profile_state(db_path, "PRF-03F-021", "1.0.0") is None
    assert outbox_count(db_path) == 0
    assert link_state(db_path, "STRATEGY_PROFILE", "PRF-03F-021", "1.0.0") is None

    # Oracle B agrees.
    assert coverage_report(db_path)["verdict"] == "EMPTY"


# ---------------------------------------------------------------------------
# F_CRASH_03 — crash after artifact+PENDING COMMIT, before dispatch
# ---------------------------------------------------------------------------


def test_F_CRASH_03_pending_survives_restart_and_reconciles_without_duplicates(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    identities = [persist_profile(31, finalize=False)]
    item = identities[0]

    # Intermediate state: durable PENDING, hidden from governed reads.
    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["status"] == RetentionOutboxStatus.PENDING.value
    assert profile_state(db_path, item["profile_id"], item["version"]) == "PENDING_RETENTION"
    assert link_state(db_path, "STRATEGY_PROFILE", item["profile_id"], item["version"]) == (
        "PENDING_RETENTION"
    )
    with pytest.raises(RuntimeError, match="WAIT_RHIST03D_ARTIFACT_NOT_APPLIED"):
        verify_governed_rhist03d_artifact("STRATEGY_PROFILE", item["profile_id"], item["version"])

    report = coverage_report(db_path)
    assert report["verdict"] == "FAIL"
    assert CoverageStatus.PENDING_RETENTION.value in _statuses(report)
    assert CoverageStatus.PENDING_RETENTION.value != "PASS"

    # Restart, then canonical recovery resumes the exact deterministic work.
    restart()
    result = reconcile_pending_coverage(limit=10)
    assert result["processed"] == 1
    assert result["after"]["verdict"] == "PASS"

    # Same identities, one semantic reference, no duplicates.
    manifest = capture_manifest(db_path, identities)
    assert_manifest_healthy(manifest)
    assert manifest["profiles"][0]["event_id"] == item["event_id"]
    assert manifest["profiles"][0]["reference_id"] == item["reference_id"]
    assert count_authority_refs(db_path, item["reference_id"]) == 1


# ---------------------------------------------------------------------------
# F_CRASH_04 — authority registered, crash before local APPLIED mark
# ---------------------------------------------------------------------------


def test_F_CRASH_04_authority_success_then_crash_converges_idempotently(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    identities = [persist_profile(41, finalize=False)]
    item = identities[0]
    registrar = DurableRetentionRegistrar(db_path=db_path)

    with pytest.raises(RuntimeError, match="INJECTED_AFTER_AUTHORITY_REGISTERED"):
        registrar.dispatch(item["event_id"], fault_point="AFTER_AUTHORITY_REGISTERED")

    # Split-brain intermediate: authority reference exists, outbox still PENDING.
    ref = authority_row(db_path, item["reference_id"])
    assert ref is not None
    assert ref["artifact_hash"] == item["content_hash"]
    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["status"] == RetentionOutboxStatus.PENDING.value
    assert coverage_report(db_path)["verdict"] == "FAIL"

    # Restart: redispatch converges through authority idempotency.
    restart()
    registrar2 = DurableRetentionRegistrar(db_path=db_path)
    receipt = registrar2.dispatch(item["event_id"])
    assert receipt.status is RetentionOutboxStatus.APPLIED
    assert receipt.reference_id == item["reference_id"]
    assert count_authority_refs(db_path, item["reference_id"]) == 1

    r18_store.finalize_rhist03d_artifact(
        "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=True
    )
    manifest = capture_manifest(db_path, identities)
    assert_manifest_healthy(manifest)
    assert manifest["coverage"]["reportHash"] == coverage_report(db_path)["reportHash"]


# ---------------------------------------------------------------------------
# F_REPLAY_01 / F_REPLAY_02 — idempotent replay of intent and APPLIED events
# ---------------------------------------------------------------------------


def test_F_REPLAY_01_duplicate_producer_intent_and_redispatch_converge(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    identities = [persist_profile(51)]
    item = identities[0]
    registrar = DurableRetentionRegistrar(db_path=db_path)

    # Duplicate producer replay: same artifact+version+evidence is idempotent.
    assert r18_store.persist_strategy_profile(build_profile(51)) is False
    r18_store.finalize_rhist03d_artifact(
        "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=True
    )

    first = registrar.dispatch(item["event_id"])
    second = registrar.dispatch(item["event_id"])
    assert first.status is RetentionOutboxStatus.APPLIED
    assert second.status is RetentionOutboxStatus.APPLIED
    assert (first.event_id, first.reference_id) == (second.event_id, second.reference_id)
    assert count_authority_refs(db_path, item["reference_id"]) == 1
    assert coverage_report(db_path)["verdict"] == "PASS"


def test_F_REPLAY_02_applied_redispatch_creates_no_new_reference(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    identities = [persist_profile(52)]
    item = identities[0]
    registrar = DurableRetentionRegistrar(db_path=db_path)

    before = outbox_row(db_path, item["event_id"])
    assert before is not None and before["status"] == RetentionOutboxStatus.APPLIED.value
    receipt = registrar.dispatch(item["event_id"])
    after = outbox_row(db_path, item["event_id"])
    assert receipt.status is RetentionOutboxStatus.APPLIED
    assert after is not None and after["status"] == RetentionOutboxStatus.APPLIED.value
    assert after["attempts"] == before["attempts"]
    assert count_authority_refs(db_path, item["reference_id"]) == 1


# ---------------------------------------------------------------------------
# F_REPLAY_06 — same identity with changed material is rejected, never repointed
# ---------------------------------------------------------------------------


def test_F_REPLAY_06_same_event_id_with_changed_payload_is_rejected(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    registrar = DurableRetentionRegistrar(db_path=db_path)

    def _intent(created_at, artifact_hash):
        return RetentionEvidenceIntent(
            artifact_type="R18_STRATEGY_PROFILE",
            artifact_id="PRF-03F-REPLAY",
            artifact_version="1.0.0",
            reference_type=RetentionReferenceType.STRATEGY_PROFILE,
            artifact_hash=artifact_hash,
            created_at=created_at,
        )

    first = registrar.enqueue(_intent(NOW, H1))
    # Same lineage (event_id excludes createdAt) but different material.
    with pytest.raises(ValueError, match="immutable|cannot be repointed"):
        registrar.enqueue(_intent(NOW + timedelta(hours=1), H1))

    kept = outbox_row(db_path, first.event_id)
    assert kept is not None and kept["status"] == RetentionOutboxStatus.PENDING.value


def test_F_REPLAY_06b_tampered_outbox_payload_blocks_dispatch_before_authority(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    registrar = DurableRetentionRegistrar(db_path=db_path)
    intent = RetentionEvidenceIntent(
        artifact_type="R18_STRATEGY_PROFILE",
        artifact_id="PRF-03F-TAMPER",
        artifact_version="1.0.0",
        reference_type=RetentionReferenceType.STRATEGY_PROFILE,
        artifact_hash=H2,
        created_at=NOW,
    )
    receipt = registrar.enqueue(intent)

    # Controlled direct-SQL fault injection (scratch DB only, never a repair path).
    with storage.connect() as conn:
        conn.execute(
            "UPDATE historical_retention_outbox SET payload_json=? WHERE event_id=?",
            ('{"tampered":true}', receipt.event_id),
        )
        conn.commit()

    with pytest.raises(RuntimeError, match="payload hash mismatch"):
        registrar.dispatch(receipt.event_id)
    assert authority_row(db_path, receipt.reference_id) is None
    assert coverage_report(db_path)["verdict"] != "PASS"
