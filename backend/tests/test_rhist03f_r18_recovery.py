"""R-HIST-03F M1 — R18 crash/restart/replay recovery across all four types.

F_CRASH_05 (APPLIED-proof vs visibility split), F_CRASH_08 (per-type finalize
crashes), F_CRASH_09 (restart at every durable boundary), F_REPLAY_04
(idempotent re-finalization). Dual oracles throughout.

Parentless fixtures (fabricated valid manifests, verify_parents=False) prove
crash mechanics fast; honest coverage for parentless APPLIED artifacts is
non-PASS by design. Parented PASS is proven by the 03E source-to-end suite.
Scratch DBs only. Fixed timestamps only.
"""
from __future__ import annotations

import hashlib
import sqlite3

import pytest

from trendforge_api import storage
from trendforge_api.retention_coverage import CoverageStatus
from trendforge_api.retention_producer import DurableRetentionRegistrar, RetentionOutboxStatus
from trendforge_api.selection import r18_governance as governance
from trendforge_api.selection import r18_store
from trendforge_api.selection.r18_history_finalization import (
    verify_governed_rhist03d_artifact,
)
from trendforge_api.selection.r18_history_store import (
    persist_audit_record,
    persist_frozen_dataset,
    persist_governed_model,
)

from tests.rhist03f_harness import (
    NOW,
    authority_row,
    count_authority_refs,
    coverage_report,
    dataset_manifest,
    init_db,
    link_state,
    outbox_row,
    persist_profile,
    profile_state,
    restart,
)

FIX = b"03f-m1-fixture"


def _h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _link_ids(db_path, artifact_type: str, artifact_id: str, version: str):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        link = conn.execute(
            "SELECT artifact_hash, event_id, reference_id, publication_state "
            "FROM r18_retention_links WHERE artifact_type=? AND artifact_id=? AND artifact_version=?",
            (artifact_type, artifact_id, version),
        ).fetchone()
    assert link is not None
    return (
        str(link["event_id"]),
        str(link["reference_id"]),
        str(link["artifact_hash"]),
        str(link["publication_state"]),
    )


def _finalize(artifact_type: str, artifact_id: str, version: str, fault=None):
    return r18_store.finalize_rhist03d_artifact(
        artifact_type, artifact_id, version, fault_point=fault, verify_parents=False
    )


def _build_chain():
    """Pure builders for a parentless 4-type chain. No DB writes."""
    train = dataset_manifest("M1TRAIN")
    model = governance.build_governed_model_version(
        model_id="MDL-03F-M1",
        model_version="1.0.0",
        purpose="RESEARCH_EVALUATION",
        market="NSE",
        horizon="SWING",
        training_dataset=train.model_dump(mode="python", by_alias=False),
        evaluation_dataset=train.model_dump(mode="python", by_alias=False),
        feature_set_hash=train.feature_manifest_hash,
        formula_set_hash=train.formula_set_hash,
        model_artifact_hash=_h("03f-m1-model-artifact"),
        code_build_hash=_h("03f-m1-code"),
        config_hash=_h("03f-m1-config"),
        hyperparameters={"fixture": "03f-m1-no-training"},
        random_seeds=(7,),
        cost_model_version="cost-v1",
        evaluation_id="EVAL-03F-M1",
        evaluation_hash=train.dataset_hash,
        created_at=NOW,
    )
    profile = governance.build_strategy_profile_version(
        profile_id="PRF-03F-M1",
        profile_version="1.0.0",
        strategy_id="CONTINUATION",
        strategy_version="1.0.0",
        market="NSE",
        instrument_class="EQUITY",
        horizon="SWING",
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
        model_id="MDL-03F-M1",
        model_version="1.0.0",
        model_hash=model.model_hash,
        research_ceiling="WAIT",
        activation_allowed=False,
        created_at=NOW,
        valid_from=NOW,
    )
    audit = governance.build_governance_audit_record(
        audit_id="AUD-03F-M1-1",
        reviewed_artifact_type="MODEL_VERSION",
        artifact_id="MDL-03F-M1",
        artifact_version="1.0.0",
        artifact_hash=model.model_hash,
        dataset_id=train.dataset_id,
        dataset_hash=train.dataset_hash,
        model_id="MDL-03F-M1",
        model_hash=model.model_hash,
        profile_id="PRF-03F-M1",
        profile_hash=profile.content_hash,
        evaluation_id="EVAL-03F-M1",
        evaluation_hash=train.dataset_hash,
        predecessor_audit_hash=None,
        decision="REVIEW",
        reviewer="03f-m1-fixture",
        reason="controlled parentless crash-recovery fixture",
        reviewed_at=NOW,
        evidence_hash=train.evidence_root_digest,
        governance_policy_version="fixture-v1",
        pit_prerequisite_proven=True,
        resulting_state="REVIEWED",
    )
    return {"dataset": train, "model": model, "profile": profile, "audit": audit}


def _persist_upto(chain: dict, target: str) -> None:
    """Persist prerequisites so `target` is staged PENDING; finalize nothing.

    Model persist requires its training/evaluation datasets APPLIED, so the
    dataset is finalized (verify_parents=False) whenever the target is not the
    dataset itself. Nothing else is finalized here.
    """
    assert persist_frozen_dataset(chain["dataset"])["stored"] is True
    if target == "ML_DATASET":
        return
    _finalize("ML_DATASET", "DS-03F-M1TRAIN", "1.0.0")
    assert persist_governed_model(chain["model"]) is True
    if target == "MODEL_VERSION":
        return
    assert r18_store.persist_strategy_profile(chain["profile"]) is True
    if target == "STRATEGY_PROFILE":
        return
    assert persist_audit_record(chain["audit"]) is True


# ---------------------------------------------------------------------------
# F_CRASH_05 — APPLIED proof without finalized visibility stays hidden
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seam", ["AFTER_LINK_APPLIED", "BEFORE_LOCAL_COMMIT"])
def test_F_CRASH_05_visibility_crash_rolls_back_atomically(tmp_path, monkeypatch, seam) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(61, finalize=False)

    with pytest.raises(RuntimeError, match=f"INJECTED_{seam}"):
        _finalize("STRATEGY_PROFILE", item["profile_id"], item["version"], fault=seam)

    # Oracle A: canonical path cannot strand a half-visible pair.
    assert profile_state(db_path, item["profile_id"], item["version"]) == "PENDING_RETENTION"
    assert link_state(db_path, "STRATEGY_PROFILE", item["profile_id"], item["version"]) == (
        "PENDING_RETENTION"
    )
    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["status"] == RetentionOutboxStatus.APPLIED.value

    # Oracle B: APPLIED outbox alone is never healthy visibility.
    report = coverage_report(db_path)
    assert report["verdict"] != "PASS"

    restart()
    _finalize("STRATEGY_PROFILE", item["profile_id"], item["version"])
    assert profile_state(db_path, item["profile_id"], item["version"]) == "APPLIED"
    assert link_state(db_path, "STRATEGY_PROFILE", item["profile_id"], item["version"]) == "APPLIED"
    assert count_authority_refs(db_path, item["reference_id"]) == 1
    assert coverage_report(db_path)["verdict"] == "PASS"


def test_F_CRASH_05c_split_publication_state_is_detected_never_exposed(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(62, finalize=False)

    # Controlled fault injection: force the split the canonical path cannot create.
    with storage.connect() as conn:
        conn.execute(
            "UPDATE r18_retention_links SET publication_state='APPLIED' "
            "WHERE artifact_type='STRATEGY_PROFILE' AND artifact_id=? AND artifact_version=?",
            (item["profile_id"], item["version"]),
        )
        conn.commit()

    with pytest.raises(RuntimeError, match="SPLIT_PUBLICATION_STATE"):
        _finalize("STRATEGY_PROFILE", item["profile_id"], item["version"])
    with pytest.raises(RuntimeError, match="NOT_APPLIED|LINK_NOT_APPLIED"):
        verify_governed_rhist03d_artifact(
            "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=False
        )
    assert coverage_report(db_path)["verdict"] != "PASS"


def test_F_CRASH_05d_outbox_applied_before_visibility_recovers_cleanly(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(63, finalize=False)

    with pytest.raises(RuntimeError, match="INJECTED_AFTER_OUTBOX_APPLIED"):
        _finalize("STRATEGY_PROFILE", item["profile_id"], item["version"], fault="AFTER_OUTBOX_APPLIED")

    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["status"] == RetentionOutboxStatus.APPLIED.value
    assert profile_state(db_path, item["profile_id"], item["version"]) == "PENDING_RETENTION"

    report = coverage_report(db_path)
    assert report["verdict"] == "FAIL"
    assert CoverageStatus.PENDING_RETENTION.value in {
        str(row["status"]) for row in report["findings"]
    }

    restart()
    _finalize("STRATEGY_PROFILE", item["profile_id"], item["version"])
    assert coverage_report(db_path)["verdict"] == "PASS"
    assert count_authority_refs(db_path, item["reference_id"]) == 1


# ---------------------------------------------------------------------------
# F_CRASH_08 — per-type finalize crashes converge without repoint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("artifact_type", "artifact_id", "version", "seam"),
    [
        ("ML_DATASET", "DS-03F-M1TRAIN", "1.0.0", "BEFORE_DISPATCH"),
        ("MODEL_VERSION", "MDL-03F-M1", "1.0.0", "AFTER_PARENT_PROOF"),
        ("STRATEGY_PROFILE", "PRF-03F-M1", "1.0.0", "AFTER_LINK_APPLIED"),
        ("AUDIT", "AUD-03F-M1-1", "1", "BEFORE_LOCAL_COMMIT"),
    ],
)
def test_F_CRASH_08_per_type_finalize_crash_recovers_without_repoint(
    tmp_path, monkeypatch, artifact_type, artifact_id, version, seam
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    chain = _build_chain()
    _persist_upto(chain, artifact_type)
    event_id, reference_id, artifact_hash, _ = _link_ids(db_path, artifact_type, artifact_id, version)

    with pytest.raises(RuntimeError, match=f"INJECTED_{seam}"):
        _finalize(artifact_type, artifact_id, version, fault=seam)

    # Intermediate: staged, never half-visible, never healthy.
    event = outbox_row(db_path, event_id)
    assert event is not None
    assert coverage_report(db_path)["verdict"] != "PASS"

    restart()
    _finalize(artifact_type, artifact_id, version)

    # Same identities, one semantic reference, idempotent re-finalize.
    event_id2, reference_id2, artifact_hash2, state2 = _link_ids(
        db_path, artifact_type, artifact_id, version
    )
    assert (event_id2, reference_id2, artifact_hash2) == (event_id, reference_id, artifact_hash)
    assert state2 == "APPLIED"
    assert count_authority_refs(db_path, reference_id) == 1
    _finalize(artifact_type, artifact_id, version)
    assert count_authority_refs(db_path, reference_id) == 1
    ref = authority_row(db_path, reference_id)
    assert ref is not None and ref["artifact_hash"] == artifact_hash

    # Honest accounting: a parentless APPLIED proof is never PASS. A chain with
    # no verifiable parents is LINEAGE_MISSING; a chain whose referenced parent
    # exists but is itself unverifiable is LINEAGE_BROKEN.
    producer, honest = {
        "ML_DATASET": ("R18_ML_DATASET", CoverageStatus.LINEAGE_MISSING),
        "MODEL_VERSION": ("R18_MODEL_VERSION", CoverageStatus.LINEAGE_MISSING),
        "STRATEGY_PROFILE": ("R18_STRATEGY_PROFILE", CoverageStatus.LINEAGE_BROKEN),
        "AUDIT": ("R18_AUDIT", CoverageStatus.LINEAGE_BROKEN),
    }[artifact_type]
    report = coverage_report(db_path)
    assert report["verdict"] != "PASS"
    by_producer = {str(f["producerId"]): str(f["status"]) for f in report["findings"]}
    assert by_producer.get(producer) == honest.value


def test_F_CRASH_08_parentless_applied_graph_reports_honest_non_pass(
    tmp_path, monkeypatch
) -> None:
    """Parentless APPLIED artifacts must not manufacture a healthy PASS."""
    db_path = init_db(tmp_path, monkeypatch)
    chain = _build_chain()
    _persist_upto(chain, "MODEL_VERSION")
    _finalize("MODEL_VERSION", "MDL-03F-M1", "1.0.0")

    report = coverage_report(db_path)
    assert report["verdict"] != "PASS", report["verdict"]
    assert report["expectedCount"] == 2


# ---------------------------------------------------------------------------
# F_CRASH_09 — restart after every durable boundary preserves identities
# ---------------------------------------------------------------------------


def test_F_CRASH_09_restart_at_every_boundary_preserves_identities(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(69, finalize=False)
    registrar = DurableRetentionRegistrar(db_path=db_path)

    restart()  # boundary 1: after persist, before dispatch
    assert outbox_row(db_path, item["event_id"])["status"] == RetentionOutboxStatus.PENDING.value

    registrar.dispatch(item["event_id"])
    restart()  # boundary 2: after outbox APPLIED, before finalize
    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["status"] == RetentionOutboxStatus.APPLIED.value
    assert profile_state(db_path, item["profile_id"], item["version"]) == "PENDING_RETENTION"

    r18_store.finalize_rhist03d_artifact(
        "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=True
    )
    restart()  # boundary 3: after finalize
    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["reference_id"] == item["reference_id"]
    assert count_authority_refs(db_path, item["reference_id"]) == 1
    assert coverage_report(db_path)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# F_REPLAY_04 — repeat finalization converges on the same governed artifact
# ---------------------------------------------------------------------------


def test_F_REPLAY_04_repeat_dataset_finalize_is_idempotent(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    manifest_model = dataset_manifest("REPLAY")
    assert persist_frozen_dataset(manifest_model)["stored"] is True

    first = _finalize("ML_DATASET", manifest_model.dataset_id, manifest_model.dataset_version)
    event_id, reference_id, _, _ = _link_ids(
        db_path, "ML_DATASET", manifest_model.dataset_id, manifest_model.dataset_version
    )
    second = _finalize("ML_DATASET", manifest_model.dataset_id, manifest_model.dataset_version)
    assert first == second
    assert count_authority_refs(db_path, reference_id) == 1
    assert outbox_row(db_path, event_id)["status"] == RetentionOutboxStatus.APPLIED.value
