from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event

import pytest

from trendforge_api import storage
from trendforge_api.historical_retention import (
    HistoricalRetentionAuthority, RetentionReference, RetentionReferenceType,
)
from trendforge_api.retention_producer import DurableRetentionRegistrar, RetentionEvidenceIntent
from trendforge_api.selection import r18_history_finalization as finalization
from trendforge_api.selection import r18_history_store as history_store
from trendforge_api.selection import r18_store

from test_rhist03d_finalization import NOW, _profile, _set_db


def _old_profile(tmp_path, monkeypatch, status="PENDING"):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    original_intent = history_store.RetentionEvidenceIntent

    def old_namespace(**values):
        values["content_hash"] = values.pop("artifact_hash")
        return original_intent(**values)

    # Reproduce the historical producer without bypassing any database guard.
    with monkeypatch.context() as patch:
        patch.setattr(history_store, "RetentionEvidenceIntent", old_namespace)
        history_store.persist_strategy_profile(profile)
    with storage.connect() as conn:
        conn.execute("UPDATE historical_retention_outbox SET status=?", (status,))
        conn.commit()
        old = dict(conn.execute("SELECT * FROM historical_retention_outbox").fetchone())
    return profile, old


def _recover(event_id):
    recover = getattr(r18_store, "supersede_rhist03d_event", None)
    assert callable(recover), "controlled 03D supersession is missing"
    return recover(event_id, reviewed_by="test-reviewer", reason="pre-fix semantic namespace")


@pytest.mark.parametrize("status", ["PENDING", "FAILED_BLOCKING"])
def test_supersession_preserves_e1_and_governs_only_deterministic_e2(tmp_path, monkeypatch, status):
    profile, old = _old_profile(tmp_path, monkeypatch, status)
    result = _recover(old["event_id"])
    assert result == _recover(old["event_id"])
    expected = RetentionEvidenceIntent(
        artifact_type="R18_STRATEGY_PROFILE", artifact_id=profile.profile_id,
        artifact_version=profile.profile_version,
        reference_type=RetentionReferenceType.STRATEGY_PROFILE,
        artifact_hash=profile.content_hash, created_at=NOW,
    )
    assert result["new_event_id"] == expected.event_id
    assert result["new_event_id"] != old["event_id"]
    published = r18_store.finalize_rhist03d_artifact(
        "STRATEGY_PROFILE", profile.profile_id, profile.profile_version
    )
    assert published["contentHash"] == profile.content_hash
    with storage.connect() as conn:
        assert dict(conn.execute(
            "SELECT * FROM historical_retention_outbox WHERE event_id=?", (old["event_id"],)
        ).fetchone()) == old
        assert conn.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[0] == 2
        refs = conn.execute("SELECT reference_id,artifact_hash FROM historical_retention_references").fetchall()
        assert [tuple(row) for row in refs] == [(expected.reference_id, profile.content_hash)]
        assert conn.execute("SELECT event_id FROM r18_retention_links").fetchone()[0] == old["event_id"]
        for sql in (
            "UPDATE r18_retention_supersessions SET reason='changed'",
            "DELETE FROM r18_retention_supersessions",
            "UPDATE historical_retention_outbox SET content_hash=NULL WHERE event_id=?",
            "DELETE FROM historical_retention_outbox WHERE event_id=?",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                conn.execute(sql, (old["event_id"],) if "?" in sql else ())
    with pytest.raises(RuntimeError, match="SUPERSEDED|PREFIX"):
        DurableRetentionRegistrar(db_path=storage.DB_PATH).dispatch(old["event_id"])


def test_applied_old_event_hard_stops_without_any_change(tmp_path, monkeypatch):
    _, old = _old_profile(tmp_path, monkeypatch, "APPLIED")
    with pytest.raises(RuntimeError, match="APPLIED.*(REVIEW|MIGRATION)"):
        _recover(old["event_id"])
    with storage.connect() as conn:
        assert dict(conn.execute("SELECT * FROM historical_retention_outbox").fetchone()) == old
        assert conn.execute("SELECT COUNT(*) FROM r18_retention_supersessions").fetchone()[0] == 0


def test_legacy_market_dataset_is_not_a_pre_fix_semantic_event(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    event = RetentionEvidenceIntent(
        artifact_type="LEGACY_DATASET", artifact_id="market-data", artifact_version="1",
        reference_type=RetentionReferenceType.ML_DATASET, content_hash="a" * 64, created_at=NOW,
    )
    registrar = DurableRetentionRegistrar(db_path=storage.DB_PATH)
    registrar.enqueue(event)
    with storage.connect() as conn:
        conn.execute("UPDATE historical_retention_outbox SET status='APPLIED'")
        conn.commit()
    assert r18_store.rhist03d_preflight_inventory()["stopRequired"] is False


@pytest.mark.parametrize("point", [
    "BEFORE_DISPATCH", "AFTER_AUTHORITY_REGISTERED", "AFTER_OUTBOX_APPLIED",
    "AFTER_PARENT_PROOF", "AFTER_LINK_APPLIED", "BEFORE_LOCAL_COMMIT",
])
def test_crash_window_is_hidden_and_replay_is_idempotent(tmp_path, monkeypatch, point):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    r18_store.persist_strategy_profile(profile)
    args = ("STRATEGY_PROFILE", profile.profile_id, profile.profile_version)
    with pytest.raises(RuntimeError, match="INJECTED_" + point):
        r18_store.finalize_rhist03d_artifact(*args, fault_point=point)
    with storage.connect() as conn:
        assert conn.execute("SELECT publication_state FROM strategy_profile_versions").fetchone()[0] == "PENDING_RETENTION"
        assert conn.execute("SELECT publication_state FROM r18_retention_links").fetchone()[0] == "PENDING_RETENTION"
    with pytest.raises(RuntimeError, match="NOT_APPLIED"):
        r18_store.verify_governed_rhist03d_artifact(*args)
    result = r18_store.finalize_rhist03d_artifact(*args)
    assert r18_store.finalize_rhist03d_artifact(*args) == result
    with storage.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM historical_retention_references").fetchone()[0] == 1


def test_two_simultaneous_finalizers_publish_once_and_both_replay(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    r18_store.persist_strategy_profile(profile)
    barrier = Barrier(2)
    original = finalization._verify_parents

    def synchronized_parents(artifact_type, payload):
        original(artifact_type, payload)
        # Force both callers to observe pending before either can commit.
        if barrier.n_waiting or not passed.is_set():
            barrier.wait(timeout=10)
            passed.set()

    passed = Event()
    monkeypatch.setattr(finalization, "_verify_parents", synchronized_parents)
    args = ("STRATEGY_PROFILE", profile.profile_id, profile.profile_version)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(r18_store.finalize_rhist03d_artifact, *args) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    assert results[0] == results[1]
    with storage.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM historical_retention_references").fetchone()[0] == 1
        assert conn.execute("SELECT status FROM historical_retention_outbox").fetchone()[0] == "APPLIED"


def test_late_dispatch_failure_cannot_downgrade_applied_event(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    r18_store.persist_strategy_profile(profile)
    with storage.connect() as conn:
        event_id = conn.execute("SELECT event_id FROM historical_retention_outbox").fetchone()[0]
    started, release = Event(), Event()

    class LateFailure:
        def register(self, _reference):
            started.set()
            assert release.wait(timeout=10)
            raise sqlite3.OperationalError("database is busy")

    with ThreadPoolExecutor(max_workers=1) as executor:
        losing = executor.submit(
            DurableRetentionRegistrar(db_path=storage.DB_PATH, authority=LateFailure()).dispatch, event_id
        )
        assert started.wait(timeout=10)
        try:
            winner = DurableRetentionRegistrar(db_path=storage.DB_PATH).dispatch(event_id)
        finally:
            release.set()
        loser = losing.result(timeout=10)
    assert winner.status == loser.status == "APPLIED"


def test_split_local_state_is_refused_without_repair(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    r18_store.persist_strategy_profile(profile)
    with storage.connect() as conn:
        conn.execute("UPDATE r18_retention_links SET publication_state='APPLIED'")
        conn.commit()
    with pytest.raises(RuntimeError, match="SPLIT_PUBLICATION_STATE"):
        r18_store.finalize_rhist03d_artifact("STRATEGY_PROFILE", profile.profile_id, profile.profile_version)


def test_recovery_crash_rolls_back_e2_and_audit_record(tmp_path, monkeypatch):
    _, old = _old_profile(tmp_path, monkeypatch)
    enqueue = DurableRetentionRegistrar.enqueue

    def crash(self, intent, **kwargs):
        enqueue(self, intent, **kwargs)
        raise RuntimeError("INJECTED_AFTER_E2_INSERT")

    with monkeypatch.context() as patch:
        patch.setattr(DurableRetentionRegistrar, "enqueue", crash)
        with pytest.raises(RuntimeError, match="INJECTED_AFTER_E2_INSERT"):
            _recover(old["event_id"])
    with storage.connect() as conn:
        assert dict(conn.execute("SELECT * FROM historical_retention_outbox").fetchone()) == old
        assert conn.execute("SELECT COUNT(*) FROM r18_retention_supersessions").fetchone()[0] == 0
    _recover(old["event_id"])


def test_two_recoveries_append_only_one_correction(tmp_path, monkeypatch):
    _, old = _old_profile(tmp_path, monkeypatch)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_recover, old["event_id"]) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert results[0] == results[1]
    with storage.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM r18_retention_supersessions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[0] == 2


def test_recovery_refuses_already_registered_e1_even_before_ack(tmp_path, monkeypatch):
    _, old = _old_profile(tmp_path, monkeypatch)
    with storage.connect() as conn:
        conn.execute(
            "INSERT INTO historical_retention_references(reference_id,reference_type,content_hash,"
            "permanent,created_at) VALUES(?,?,?,?,?)",
            (old["reference_id"], old["reference_type"], old["content_hash"], 1, old["created_at"]),
        )
        conn.commit()
    with pytest.raises(RuntimeError, match="APPLIED.*MIGRATION"):
        _recover(old["event_id"])
    with storage.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[0] == 1


def test_superseded_event_cannot_register_after_recovery(tmp_path, monkeypatch):
    _, old = _old_profile(tmp_path, monkeypatch)
    _recover(old["event_id"])
    with storage.connect() as conn:
        with pytest.raises(sqlite3.IntegrityError, match="superseded reference"):
            conn.execute(
                "INSERT INTO historical_retention_references(reference_id,reference_type,content_hash,"
                "permanent,created_at) VALUES(?,?,?,?,?)",
                (old["reference_id"], old["reference_type"], old["content_hash"], 1, old["created_at"]),
            )


def test_real_sqlite_writer_contention_keeps_publication_replayable(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    r18_store.persist_strategy_profile(profile)
    args = ("STRATEGY_PROFILE", profile.profile_id, profile.profile_version)
    # Finish registration first; hold a second writer only at the local commit.
    with storage.connect() as conn:
        event_id = conn.execute("SELECT event_id FROM historical_retention_outbox").fetchone()[0]
    DurableRetentionRegistrar(db_path=storage.DB_PATH).dispatch(event_id)
    lock = storage.connect()
    connect = storage.connect
    original = finalization._verify_parents

    def locked_after_proof(kind, payload):
        original(kind, payload)
        lock.execute("BEGIN IMMEDIATE")

    def short_timeout():
        conn = connect()
        conn.execute("PRAGMA busy_timeout=1")
        return conn

    try:
        with monkeypatch.context() as patch:
            patch.setattr(finalization, "_verify_parents", locked_after_proof)
            patch.setattr(storage, "connect", short_timeout)
            with pytest.raises(sqlite3.OperationalError, match="locked|busy"):
                r18_store.finalize_rhist03d_artifact(*args)
    finally:
        lock.rollback()
        lock.close()
    with storage.connect() as conn:
        assert conn.execute("SELECT publication_state FROM r18_retention_links").fetchone()[0] == "PENDING_RETENTION"
    assert r18_store.finalize_rhist03d_artifact(*args)["contentHash"] == profile.content_hash


@pytest.mark.parametrize("conflicting", [False, True])
def test_concurrent_authority_registration_preserves_exact_identity(tmp_path, monkeypatch, conflicting):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    r18_store.persist_strategy_profile(profile)
    with storage.connect() as conn:
        reference_id = conn.execute("SELECT reference_id FROM historical_retention_outbox").fetchone()[0]
    reference = RetentionReference(
        reference_id=reference_id, reference_type=RetentionReferenceType.STRATEGY_PROFILE,
        artifact_id=profile.profile_id, artifact_version=profile.profile_version,
        artifact_hash=profile.content_hash, created_at=NOW,
    )
    barrier = Barrier(2)

    class RacingConnection(sqlite3.Connection):
        synchronized = False

        def execute(self, sql, parameters=()):
            cursor = super().execute(sql, parameters)
            if sql.startswith("SELECT * FROM historical_retention_references WHERE reference_id") and not self.synchronized:
                self.synchronized = True
                barrier.wait(timeout=10)
            return cursor

    def racing_connection():
        conn = sqlite3.connect(storage.DB_PATH, factory=RacingConnection, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    authority = HistoricalRetentionAuthority(db_path=storage.DB_PATH)
    monkeypatch.setattr(authority, "_connect", racing_connection)
    second = reference.model_copy(update={"created_at": NOW + timedelta(seconds=1)}) if conflicting else reference
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(authority.register, item) for item in (reference, second)]
        results, errors = [], []
        for future in futures:
            try:
                results.append(future.result(timeout=20))
            except ValueError as exc:
                errors.append(str(exc))
    if conflicting:
        assert len(results) == len(errors) == 1
        assert "immutable" in errors[0]
    else:
        assert results == [reference, reference]
        assert errors == []
    with storage.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM historical_retention_references").fetchone()[0] == 1
