"""R-HIST-03F M2 — tamper/corruption acceptance.

Every mutation uses controlled direct SQL on scratch DBs only (fault
injection, never a production repair path). Each must fail closed: dispatch
or finalization raises before authority/governed use, and the 03E coverage
oracle reports non-PASS through its independent deep verifier.

F_TAMPER_01/02/05..09/11/12 + publication-member and R18-field classes.
R16-parent and market-byte classes run against the real pipeline graph.
Scratch DBs only. Fixed timestamps only.
"""
from __future__ import annotations

import sqlite3

import pytest

from trendforge_api import storage
from trendforge_api.historical_retention import RetentionReferenceType
from trendforge_api.retention_producer import DurableRetentionRegistrar, RetentionOutboxStatus
from trendforge_api.retention_publication import (
    RetentionEvidenceRoot,
    RetentionPublicationRequest,
    RetentionPublicationStatus,
    RetentionPublicationStore,
)
from trendforge_api.selection import r18_store
from trendforge_api.selection.r18_history_finalization import (
    verify_governed_rhist03d_artifact,
)
from trendforge_api.selection.r18_history_store import (
    persist_audit_record,
    persist_frozen_dataset,
)

from tests.rhist03f_harness import (
    NOW,
    authority_row,
    coverage_report,
    dataset_manifest,
    init_db,
    outbox_row,
    persist_profile,
)


class FakeAuthority:
    def register(self, reference):
        return reference


def _tamper(db_path, sql: str, params: tuple = ()) -> None:
    with storage.connect() as conn:
        conn.execute(sql, params)
        conn.commit()


def _drop_guards(db_path, table: str) -> None:
    """Remove the R-HIST-03D immutability triggers (deeper-compromise injection).

    Layer 1 (triggers) must block naive writes; layer 2 (stored-hash and
    proof verifiers) must detect writes that bypass layer 1. Scratch DBs only.
    """
    with storage.connect() as conn:
        conn.execute(f"DROP TRIGGER IF EXISTS rhist03d_guard_{table}_update")
        conn.execute(f"DROP TRIGGER IF EXISTS rhist03d_guard_{table}_delete")
        conn.commit()


def _statuses(report: dict) -> set[str]:
    return {str(row["status"]) for row in report["findings"]}


def _profile_ids(index: int) -> tuple[str, str]:
    return f"PRF-03F-{index:03d}", "1.0.0"


# ---------------------------------------------------------------------------
# Outbox tampers (F_TAMPER_01/02/09/10) — blocked before authority
# ---------------------------------------------------------------------------


def test_F_TAMPER_01_outbox_payload_tamper_blocks_before_authority(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(91, finalize=False)
    _tamper(
        db_path,
        "UPDATE historical_retention_outbox SET payload_json=? WHERE event_id=?",
        ('{"tampered":true}', item["event_id"]),
    )

    with pytest.raises(RuntimeError, match="payload hash mismatch"):
        DurableRetentionRegistrar(db_path=db_path).dispatch(item["event_id"])
    assert authority_row(db_path, item["reference_id"]) is None
    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["status"] != RetentionOutboxStatus.APPLIED.value
    assert coverage_report(db_path)["verdict"] != "PASS"


def test_F_TAMPER_02_outbox_indexed_column_tamper_blocks_before_authority(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(92, finalize=False)
    _tamper(
        db_path,
        "UPDATE historical_retention_outbox SET artifact_hash=? WHERE event_id=?",
        ("f" * 64, item["event_id"]),
    )

    with pytest.raises(RuntimeError, match="payload columns disagree"):
        DurableRetentionRegistrar(db_path=db_path).dispatch(item["event_id"])
    assert authority_row(db_path, item["reference_id"]) is None
    assert coverage_report(db_path)["verdict"] != "PASS"


@pytest.mark.parametrize("bad_version", ["2.0.0", "9.9.9-zero"])
def test_F_TAMPER_09_wrong_artifact_version_blocks_dispatch(tmp_path, monkeypatch, bad_version) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(93, finalize=False)
    _tamper(
        db_path,
        "UPDATE historical_retention_outbox SET artifact_version=? WHERE event_id=?",
        (bad_version, item["event_id"]),
    )

    with pytest.raises(RuntimeError, match="payload columns disagree"):
        DurableRetentionRegistrar(db_path=db_path).dispatch(item["event_id"])
    assert authority_row(db_path, item["reference_id"]) is None
    assert coverage_report(db_path)["verdict"] != "PASS"


@pytest.mark.parametrize("bad_type", ["MODEL_VERSION", "NOPE"])
def test_F_TAMPER_10_wrong_reference_type_blocks_dispatch(tmp_path, monkeypatch, bad_type) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(94, finalize=False)
    _tamper(
        db_path,
        "UPDATE historical_retention_outbox SET reference_type=? WHERE event_id=?",
        (bad_type, item["event_id"]),
    )

    with pytest.raises(Exception, match="columns disagree|not a valid|NOPE"):
        DurableRetentionRegistrar(db_path=db_path).dispatch(item["event_id"])
    assert authority_row(db_path, item["reference_id"]) is None
    assert coverage_report(db_path)["verdict"] != "PASS"


# ---------------------------------------------------------------------------
# Link / authority / artifact tampers (F_TAMPER_05/08/11) — never healthy
# ---------------------------------------------------------------------------


def test_F_TAMPER_08_link_repoint_is_detected(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(95, finalize=False)
    sql = (
        "UPDATE r18_retention_links SET artifact_hash=? "
        "WHERE artifact_type='STRATEGY_PROFILE' AND artifact_id=? AND artifact_version=?"
    )
    params = ("e" * 64, item["profile_id"], item["version"])

    # Layer 1: the immutability trigger blocks the naive write.
    with pytest.raises(sqlite3.IntegrityError, match="immutable artifact"):
        _tamper(db_path, sql, params)

    # Layer 2: past the trigger, the finalize-time link check still refuses.
    _drop_guards(db_path, "r18_retention_links")
    _tamper(db_path, sql, params)
    with pytest.raises(RuntimeError, match="LINK_MISSING_OR_MISMATCH|LINK_HASH_MISMATCH"):
        r18_store.finalize_rhist03d_artifact(
            "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=True
        )
    assert coverage_report(db_path)["verdict"] != "PASS"


def test_F_TAMPER_08b_authority_redirect_is_detected(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(96, finalize=False)
    DurableRetentionRegistrar(db_path=db_path).dispatch(item["event_id"])
    _tamper(
        db_path,
        "UPDATE historical_retention_references SET artifact_hash=? WHERE reference_id=?",
        ("e" * 64, item["reference_id"]),
    )

    with pytest.raises(RuntimeError, match="AUTHORITY_PROOF_MISMATCH"):
        r18_store.finalize_rhist03d_artifact(
            "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=True
        )
    assert coverage_report(db_path)["verdict"] != "PASS"


def test_F_TAMPER_11_artifact_hash_column_corrupt_is_detected(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(97)
    sql = (
        "UPDATE strategy_profile_versions SET content_hash=? "
        "WHERE profile_id=? AND profile_version=?"
    )
    params = ("d" * 64, item["profile_id"], item["version"])

    with pytest.raises(sqlite3.IntegrityError, match="immutable artifact"):
        _tamper(db_path, sql, params)

    _drop_guards(db_path, "strategy_profile_versions")
    _tamper(db_path, sql, params)
    with pytest.raises(Exception, match="CORRUPT|MISMATCH"):
        verify_governed_rhist03d_artifact(
            "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=True
        )
    assert coverage_report(db_path)["verdict"] != "PASS"


def test_F_TAMPER_11b_artifact_payload_corrupt_is_detected(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(98)

    def _corrupt() -> None:
        with storage.connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT payload_json FROM strategy_profile_versions "
                "WHERE profile_id=? AND profile_version=?",
                (item["profile_id"], item["version"]),
            ).fetchone()
            payload = row["payload_json"].replace(
                "BREAKOUT_CONTINUATION", "BREAKOUT_TAMPERED"
            )
            assert payload != row["payload_json"]
            conn.execute(
                "UPDATE strategy_profile_versions SET payload_json=? "
                "WHERE profile_id=? AND profile_version=?",
                (payload, item["profile_id"], item["version"]),
            )
            conn.commit()

    with pytest.raises(sqlite3.IntegrityError, match="immutable artifact"):
        _corrupt()

    _drop_guards(db_path, "strategy_profile_versions")
    _corrupt()
    with pytest.raises(Exception, match="CORRUPT|MISMATCH"):
        verify_governed_rhist03d_artifact(
            "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=True
        )
    assert coverage_report(db_path)["verdict"] != "PASS"


# ---------------------------------------------------------------------------
# Publication member tampers (F_TAMPER_06/07) — staged lies never publish
# ---------------------------------------------------------------------------


def _staged_publication(db_path, tag: str):
    store = RetentionPublicationStore(
        db_path=db_path,
        registrar=DurableRetentionRegistrar(db_path=db_path, authority=FakeAuthority()),
    )
    request = RetentionPublicationRequest(
        artifact_type="S8_DECISION_VERSION",
        artifact_id=f"s8-03f-{tag}",
        artifact_version="s8.v1",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        evidence_roots=(
            RetentionEvidenceRoot(role="ROOT", run_id="run-1"),
            RetentionEvidenceRoot(role="PEER", run_id="run-2"),
        ),
        lineage={"s8PayloadHash": "c" * 64},
        created_at=NOW,
    )
    return store, store.stage_owned(request)


def test_F_TAMPER_06_removed_member_blocks_publication(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    store, staged = _staged_publication(db_path, "member-rm")
    _tamper(
        db_path,
        "DELETE FROM historical_retention_publication_members "
        "WHERE publication_id=? AND evidence_role='PEER'",
        (staged.publication_id,),
    )

    finalized = store.finalize(staged.publication_id)
    assert finalized.status is RetentionPublicationStatus.FAILED_BLOCKING
    with pytest.raises(RuntimeError, match="before exact retention protection"):
        store.mark_published(staged.publication_id)
    assert coverage_report(db_path)["verdict"] != "PASS"


def test_F_TAMPER_07_replaced_member_event_never_matches_lineage(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    store, staged = _staged_publication(db_path, "member-swap")
    _, donor = _staged_publication(db_path, "member-donor")
    store.finalize(donor.publication_id)
    with storage.connect() as conn:
        conn.row_factory = sqlite3.Row
        donor_event = conn.execute(
            "SELECT event_id FROM historical_retention_publication_members "
            "WHERE publication_id=? LIMIT 1",
            (donor.publication_id,),
        ).fetchone()["event_id"]
        conn.execute(
            "UPDATE historical_retention_publication_members SET event_id=? "
            "WHERE publication_id=? AND evidence_role='PEER'",
            (f"{donor_event}-swapped", staged.publication_id),
        )
        conn.commit()

    # The swapped event is unknown: dispatch fails, publication blocks.
    finalized = store.finalize(staged.publication_id)
    assert finalized.status is RetentionPublicationStatus.FAILED_BLOCKING
    with pytest.raises(RuntimeError, match="before exact retention protection"):
        store.mark_published(staged.publication_id)
    assert coverage_report(db_path)["verdict"] != "PASS"


# ---------------------------------------------------------------------------
# R18 field tampers (F_TAMPER_12/40/42/43) — binding integrity at stored layer
# ---------------------------------------------------------------------------


def test_F_TAMPER_12_dataset_own_hash_corrupt_is_detected(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    manifest_model = dataset_manifest("TAMPER12")
    assert persist_frozen_dataset(manifest_model)["stored"] is True
    sql = "UPDATE ml_frozen_datasets SET dataset_hash=? WHERE dataset_id=? AND dataset_version=?"
    params = ("d" * 64, manifest_model.dataset_id, manifest_model.dataset_version)

    with pytest.raises(sqlite3.IntegrityError, match="immutable artifact"):
        _tamper(db_path, sql, params)

    _drop_guards(db_path, "ml_frozen_datasets")
    _tamper(db_path, sql, params)
    with pytest.raises(Exception, match="CORRUPT|MISMATCH"):
        r18_store.finalize_rhist03d_artifact(
            "ML_DATASET",
            manifest_model.dataset_id,
            manifest_model.dataset_version,
            verify_parents=False,
        )
    assert coverage_report(db_path)["verdict"] != "PASS"


@pytest.mark.parametrize(
    "mutation",
    [
        ("delete-member", "DELETE FROM ml_frozen_dataset_members WHERE dataset_record_id=?", ()),
        (
            "corrupt-member-hash",
            "UPDATE ml_frozen_dataset_members SET member_hash=? WHERE dataset_record_id=?",
            ("a" * 64,),
        ),
        (
            "cutoff-rewrite",
            "UPDATE ml_frozen_datasets SET label_cutoff=? WHERE dataset_id=? AND dataset_version=?",
            None,
        ),
    ],
)
def test_F_TAMPER_38_dataset_member_and_cutoff_tamper_detected(
    tmp_path, monkeypatch, mutation
) -> None:
    from datetime import timedelta as _td

    db_path = init_db(tmp_path, monkeypatch)
    manifest_model = dataset_manifest("TAMPER38")
    assert persist_frozen_dataset(manifest_model)["stored"] is True
    record_id = f"{manifest_model.dataset_id}:{manifest_model.dataset_version}"
    name, sql, extra = mutation
    if name == "cutoff-rewrite":
        params = (
            (manifest_model.label_cutoff + _td(days=30)).isoformat(),
            manifest_model.dataset_id,
            manifest_model.dataset_version,
        )
    elif name == "delete-member":
        params = (record_id,)
    else:
        params = (extra[0], record_id)

    # Layer 1: triggers block the naive write; staged state stays intact.
    with pytest.raises(sqlite3.IntegrityError, match="immutable artifact"):
        _tamper(db_path, sql, params)

    _drop_guards(db_path, "ml_frozen_datasets")
    _drop_guards(db_path, "ml_frozen_dataset_members")
    if name == "cutoff-rewrite":
        # Auxiliary columns are not trust roots: past the trigger, a
        # column-only lie is ineffective — governed readers consume the
        # verified sealed payload, which still carries the true cutoff.
        _tamper(db_path, sql, params)
        verified = r18_store.finalize_rhist03d_artifact(
            "ML_DATASET",
            manifest_model.dataset_id,
            manifest_model.dataset_version,
            verify_parents=False,
        )
        from datetime import datetime as _dt

        assert _dt.fromisoformat(
            str(verified["labelCutoff"]).replace("Z", "+00:00")
        ) == manifest_model.label_cutoff
        assert coverage_report(db_path)["verdict"] != "PASS"
        return

    # Layer 2: past the triggers, stored-hash verification still refuses.
    _tamper(db_path, sql, params)
    with pytest.raises(Exception, match="CORRUPT|MISMATCH|COUNT"):
        r18_store.finalize_rhist03d_artifact(
            "ML_DATASET",
            manifest_model.dataset_id,
            manifest_model.dataset_version,
            verify_parents=False,
        )
    assert coverage_report(db_path)["verdict"] != "PASS"


def test_F_TAMPER_42_profile_rewrite_same_version_rejected(tmp_path, monkeypatch) -> None:
    from trendforge_api.selection import r18_governance as governance

    from tests.rhist03f_harness import NOW, build_profile

    init_db(tmp_path, monkeypatch)
    profile = build_profile(99)
    assert r18_store.persist_strategy_profile(profile) is True
    # A valid rival (self-consistent hash) with different semantics under the
    # same version must be rejected at the write path, not merged.
    rival = governance.build_strategy_profile_version(
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        strategy_id="CONTINUATION",
        strategy_version="1.0.0",
        market="NSE",
        instrument_class="EQUITY",
        horizon="INTRADAY",
        timeframes=("5m",),
        setups=("TAMPERED_SETUP",),
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
        created_at=profile.created_at,
        valid_from=NOW,
    )
    assert rival.content_hash != profile.content_hash
    with pytest.raises(ValueError, match="PROFILE_VERSION_IMMUTABLE"):
        r18_store.persist_strategy_profile(rival)


def test_F_TAMPER_43_audit_predecessor_tamper_detected(tmp_path, monkeypatch) -> None:
    from tests.test_rhist03f_r18_recovery import _build_chain

    db_path = init_db(tmp_path, monkeypatch)
    chain = _build_chain()
    assert persist_frozen_dataset(chain["dataset"])["stored"] is True
    assert persist_audit_record(chain["audit"]) is True
    sql = "UPDATE governance_audit_records SET predecessor_audit_hash=? WHERE audit_id=?"
    params = ("f" * 64, "AUD-03F-M1-1")

    # Layer 1: the trigger blocks the naive predecessor rewrite.
    with pytest.raises(sqlite3.IntegrityError, match="immutable artifact"):
        _tamper(db_path, sql, params)

    # Layer 2a: past the trigger, a column-only lie is ineffective — the
    # verified sealed payload still carries the true predecessor.
    _drop_guards(db_path, "governance_audit_records")
    _tamper(db_path, sql, params)
    verified = r18_store.finalize_rhist03d_artifact(
        "AUDIT", "AUD-03F-M1-1", "1", verify_parents=False
    )
    assert verified["predecessorAuditHash"] is None

    # Layer 2b: rewriting the sealed payload itself is detected.
    with storage.connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT payload_json FROM governance_audit_records WHERE audit_id=?",
            ("AUD-03F-M1-1",),
        ).fetchone()
        payload = row["payload_json"].replace("03f-m1-fixture", "tampered-reviewer")
        assert payload != row["payload_json"]
        conn.execute(
            "UPDATE governance_audit_records SET payload_json=? WHERE audit_id=?",
            (payload, "AUD-03F-M1-1"),
        )
        conn.commit()
    with pytest.raises(Exception, match="CORRUPT|MISMATCH"):
        verify_governed_rhist03d_artifact("AUDIT", "AUD-03F-M1-1", "1", verify_parents=False)
    assert coverage_report(db_path)["verdict"] != "PASS"
