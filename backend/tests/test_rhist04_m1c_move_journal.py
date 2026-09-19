"""R-HIST-04 M1C — durable movement journal + fencing + restart reconciler.

Metadata/control-plane milestone ONLY. No evidence is copied, moved,
deleted, compressed, restored or repointed here. Every test uses scratch
DBs and scratch files. The journal remembers movement intent; physical
operations belong to M2A and later.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from trendforge_api.market_data_store import MarketDataStore
from trendforge_api.retention_moves import (
    MoveAuthorityLostError,
    MoveJournalStore,
    apply_move_schema,
)
from trendforge_api.retention_tiering import RetentionTieringStore


def _store(tmp_path: Path, name: str = "market.db") -> MarketDataStore:
    return MarketDataStore(
        root=tmp_path / "market-data",
        db_path=tmp_path / name,
    )


def _adopted_source(tmp_path: Path, payload: bytes, db_name: str = "market.db"):
    """Install bytes and adopt a VERIFIED HOT source replica; return ids."""
    store = _store(tmp_path, db_name)
    ref = store.install_object(
        payload, extension="json", media_type="application/json"
    )
    tiering = RetentionTieringStore(
        objects_root=tmp_path / "market-data" / "objects",
        db_path=tmp_path / db_name,
    )
    replica_id = tiering.adopt_legacy_as_replica(
        ref.content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    journal = MoveJournalStore(db_path=tmp_path / db_name)
    return store, journal, ref.content_hash, replica_id


def _intent_kwargs(tmp_path: Path, content_hash: str, replica_id: str, **overrides):
    mirror = tmp_path / "warm-mirror"
    kwargs = {
        "content_hash": content_hash,
        "source_replica_id": replica_id,
        "destination_tier": "WARM",
        "destination_backend_id": "local-warm",
        "destination_object_key": f"warm/{content_hash[:2]}/{content_hash}.json",
        "destination_locator": str(mirror / content_hash[:2] / f"{content_hash}.json"),
        "representation": "RAW",
        "representation_version": "v1",
        "operation_kind": "COPY",
    }
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_journal_schema_is_additive_and_versioned(tmp_path: Path) -> None:
    db_path = tmp_path / "moves.db"
    with sqlite3.connect(db_path) as conn:
        apply_move_schema(conn)
        conn.commit()
        version = conn.execute(
            "SELECT description FROM schema_migrations WHERE version = ?",
            ("0025_rhist04_move_journal",),
        ).fetchone()[0]
    assert "move" in version.casefold() or "journal" in version.casefold()
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "market_data_tier_moves" in tables
    assert "rhist04_replicas" in tables  # tiering dependency present
    # Legacy tables untouched: no other writes happened.
    with sqlite3.connect(db_path) as conn:
        apply_move_schema(conn)
        conn.commit()


def test_full_journal_durability_is_effective(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.install_object(b'{"h1": "durable"}', extension="json",
                         media_type="application/json")
    journal = MoveJournalStore(db_path=tmp_path / "market.db")
    observed = journal.durability()
    assert observed["journal_mode"] == "wal"
    assert observed["synchronous"] == "FULL"
    assert observed["foreign_keys"] is True


def test_invalid_state_row_is_rejected(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "bad-state"}'
    )
    record = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    with sqlite3.connect(tmp_path / "market.db") as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE market_data_tier_moves SET state = ? WHERE move_id = ?",
                ("ARCHIVED", record.move_id),
            )


def test_immutable_movement_identity_cannot_be_repointed(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "immutable"}'
    )
    record = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    with sqlite3.connect(tmp_path / "market.db") as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE market_data_tier_moves SET destination_tier = ? "
                "WHERE move_id = ?",
                ("COLD", record.move_id),
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE market_data_tier_moves SET content_hash = ? "
                "WHERE move_id = ?",
                ("0" * 64, record.move_id),
            )
    again = journal.get_move(record.move_id)
    assert again is not None
    assert again.destination_tier == "WARM"
    assert again.content_hash == content_hash


# ---------------------------------------------------------------------------
# Determinism / idempotency
# ---------------------------------------------------------------------------


def test_same_intent_returns_same_move_id_without_reset(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "idem"}'
    )
    first = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    assert first.state == "PENDING_COPY"
    claim = journal.claim_move(
        first.move_id,
        expected_state="PENDING_COPY",
        expected_version=first.state_version,
    )
    journal.transition_move(
        first.move_id,
        expected_state="PENDING_COPY",
        expected_version=claim.state_version,
        worker_epoch=claim.worker_epoch,
        new_state="COPY_IN_PROGRESS",
    )
    second = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    assert second.move_id == first.move_id
    assert second.state == "COPY_IN_PROGRESS"
    assert second.state_version == first.state_version + 2


def test_different_destination_gives_different_move_id(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "distinct"}'
    )
    warm = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    cold = journal.create_move_intent(
        **_intent_kwargs(
            tmp_path,
            content_hash,
            replica_id,
            destination_tier="COLD",
            destination_backend_id="local-cold",
            destination_object_key=f"cold/{content_hash}.json",
            destination_locator=str(tmp_path / "cold-mirror" / f"{content_hash}.json"),
        )
    )
    assert cold.move_id != warm.move_id


def test_create_rejects_removed_and_quarantined_sources(tmp_path: Path) -> None:
    store = _store(tmp_path)
    ref = store.install_object(
        b'{"h1": "bad-source"}', extension="json", media_type="application/json"
    )
    tiering = RetentionTieringStore(
        objects_root=tmp_path / "market-data" / "objects",
        db_path=tmp_path / "market.db",
    )
    victim = tiering.adopt_legacy_as_replica(
        ref.content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    journal = MoveJournalStore(db_path=tmp_path / "market.db")
    assert tiering.set_replica_state(
        victim, expected_state="VERIFIED", new_state="REMOVED"
    ) is True
    with pytest.raises(ValueError, match="REMOVED|source"):
        journal.create_move_intent(
            **_intent_kwargs(tmp_path, ref.content_hash, victim)
        )

    ref2 = store.install_object(
        b'{"h1": "quarantined-source"}', extension="json",
        media_type="application/json",
    )
    suspect = tiering.adopt_legacy_as_replica(
        ref2.content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    assert tiering.set_replica_state(
        suspect,
        expected_state="VERIFIED",
        new_state="QUARANTINED",
        quarantine_reason="test",
    ) is True
    with pytest.raises(ValueError, match="QUARANTINED|source"):
        journal.create_move_intent(
            **_intent_kwargs(tmp_path, ref2.content_hash, suspect)
        )


def test_create_rejects_same_semantic_source_and_destination(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    ref = store.install_object(
        b'{"h1": "alias"}', extension="json", media_type="application/json"
    )
    tiering = RetentionTieringStore(
        objects_root=tmp_path / "market-data" / "objects",
        db_path=tmp_path / "market.db",
    )
    replica_id = tiering.adopt_legacy_as_replica(
        ref.content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.row_factory = sqlite3.Row
        locator = conn.execute(
            "SELECT locator FROM rhist04_replicas WHERE replica_id = ?",
            (replica_id,),
        ).fetchone()["locator"]
    journal = MoveJournalStore(db_path=tmp_path / "market.db")
    with pytest.raises(ValueError, match="alias|same|destination"):
        journal.create_move_intent(
            **_intent_kwargs(
                tmp_path,
                ref.content_hash,
                replica_id,
                destination_tier="HOT",
                destination_backend_id="local-hot",
                destination_object_key="objects/ab/x.json",
                destination_locator=locator,
            )
        )


def test_create_rejects_unknown_source_replica(tmp_path: Path) -> None:
    _store(tmp_path).install_object(
        b'{"h1": "orphan-intent"}', extension="json",
        media_type="application/json",
    )
    journal = MoveJournalStore(db_path=tmp_path / "market.db")
    with pytest.raises(ValueError, match="source replica"):
        journal.create_move_intent(
            **_intent_kwargs(tmp_path, "1" * 64, "rep_doesnotexist000000000000000000")
        )


# ---------------------------------------------------------------------------
# Fencing
# ---------------------------------------------------------------------------


def test_first_claim_increments_epoch_and_version(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "claim1"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    assert created.worker_epoch == 0
    claim = journal.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=created.state_version,
    )
    assert claim.worker_epoch == created.worker_epoch + 1
    assert claim.state_version == created.state_version + 1
    assert claim.state == "PENDING_COPY"


def test_two_claims_from_same_snapshot_exactly_one_wins(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "race"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    journal2 = MoveJournalStore(db_path=tmp_path / "market.db")
    winner = journal.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=created.state_version,
    )
    with pytest.raises(MoveAuthorityLostError):
        journal2.claim_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=created.state_version,
        )
    stored = journal.get_move(created.move_id)
    assert stored is not None
    assert stored.worker_epoch == winner.worker_epoch


def test_stale_worker_transition_is_rejected(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "stale"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    journal_b = MoveJournalStore(db_path=tmp_path / "market.db")
    stale = journal.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=created.state_version,
    )
    fresh = journal_b.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=stale.state_version,
    )
    with pytest.raises(MoveAuthorityLostError):
        journal.transition_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=stale.state_version,
            worker_epoch=stale.worker_epoch,
            new_state="COPY_IN_PROGRESS",
        )
    # The authoritative worker proceeds; state is not corrupted.
    journal_b.transition_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=fresh.state_version,
        worker_epoch=fresh.worker_epoch,
        new_state="COPY_IN_PROGRESS",
    )
    stored = journal.get_move(created.move_id)
    assert stored is not None
    assert stored.state == "COPY_IN_PROGRESS"
    assert stored.worker_epoch == fresh.worker_epoch


def test_wrong_epoch_version_state_rejected(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "wrong"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    claim = journal.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=created.state_version,
    )
    with pytest.raises(MoveAuthorityLostError):
        journal.transition_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch + 99,
            new_state="COPY_IN_PROGRESS",
        )
    with pytest.raises(MoveAuthorityLostError):
        journal.transition_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=claim.state_version + 99,
            worker_epoch=claim.worker_epoch,
            new_state="COPY_IN_PROGRESS",
        )
    with pytest.raises(MoveAuthorityLostError):
        journal.transition_move(
            created.move_id,
            expected_state="COPIED_UNVERIFIED",
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch,
            new_state="DESTINATION_VERIFIED",
        )
    stored = journal.get_move(created.move_id)
    assert stored is not None
    assert stored.state == "PENDING_COPY"


def test_wall_clock_does_not_confer_authority(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "clock"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    claim = journal.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=created.state_version,
    )
    # Adversarial clock skew in both directions changes nothing.
    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.execute(
            "UPDATE market_data_tier_moves SET updated_at = ? WHERE move_id = ?",
            ("1999-01-01T00:00:00+00:00", created.move_id),
        )
        conn.commit()
    journal.transition_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=claim.state_version,
        worker_epoch=claim.worker_epoch,
        new_state="COPY_IN_PROGRESS",
    )
    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.execute(
            "UPDATE market_data_tier_moves SET updated_at = ? WHERE move_id = ?",
            ("2999-01-01T00:00:00+00:00", created.move_id),
        )
        conn.commit()
    stored = journal.get_move(created.move_id)
    assert stored is not None
    assert stored.state == "COPY_IN_PROGRESS"
    # A wrong epoch still loses no matter what the clock says.
    with pytest.raises(MoveAuthorityLostError):
        journal.transition_move(
            created.move_id,
            expected_state="COPY_IN_PROGRESS",
            expected_version=stored.state_version,
            worker_epoch=stored.worker_epoch + 1,
            new_state="COPIED_UNVERIFIED",
        )


# ---------------------------------------------------------------------------
# Transition state machine
# ---------------------------------------------------------------------------


def test_valid_lifecycle_edges_pass(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "lifecycle"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    plan = [
        "COPY_IN_PROGRESS",
        "COPIED_UNVERIFIED",
        "DESTINATION_VERIFIED",
        "SOURCE_REMOVAL_PENDING",
    ]
    state, version = "PENDING_COPY", created.state_version
    for target in plan:
        claim = journal.claim_move(
            created.move_id, expected_state=state, expected_version=version
        )
        journal.transition_move(
            created.move_id,
            expected_state=state,
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch,
            new_state=target,
        )
        state, version = target, claim.state_version + 1
    stored = journal.get_move(created.move_id)
    assert stored is not None
    assert stored.state == "SOURCE_REMOVAL_PENDING"
    assert stored.state_version == version


def test_invalid_edges_and_terminal_states_fail(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "edges"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    claim = journal.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=created.state_version,
    )
    # Skipping stages is illegal.
    with pytest.raises(ValueError, match="illegal|transition"):
        journal.transition_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch,
            new_state="DESTINATION_VERIFIED",
        )
    # Unknown target state is illegal.
    with pytest.raises(ValueError, match="illegal|transition|state"):
        journal.transition_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch,
            new_state="ARCHIVED",
        )
    # Failed states require a bounded typed error code.
    with pytest.raises(ValueError, match="error_code|error code"):
        journal.transition_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch,
            new_state="FAILED_RETRYABLE",
        )
    journal.transition_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=claim.state_version,
        worker_epoch=claim.worker_epoch,
        new_state="FAILED_BLOCKING",
        error_code="INTEGRITY_FAILED",
    )
    blocked = journal.get_move(created.move_id)
    assert blocked is not None
    # Terminal states cannot reopen.
    claim2 = journal.claim_move(
        created.move_id,
        expected_state="FAILED_BLOCKING",
        expected_version=blocked.state_version,
    )
    with pytest.raises(ValueError, match="terminal|illegal|transition"):
        journal.transition_move(
            created.move_id,
            expected_state="FAILED_BLOCKING",
            expected_version=claim2.state_version,
            worker_epoch=claim2.worker_epoch,
            new_state="COPY_IN_PROGRESS",
        )


def test_completed_cannot_reopen(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "complete"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    state, version = "PENDING_COPY", created.state_version
    for target in ("COPY_IN_PROGRESS", "COPIED_UNVERIFIED",
                   "DESTINATION_VERIFIED", "SOURCE_REMOVAL_PENDING",
                   "COMPLETED"):
        claim = journal.claim_move(
            created.move_id, expected_state=state, expected_version=version
        )
        journal.transition_move(
            created.move_id,
            expected_state=state,
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch,
            new_state=target,
        )
        state, version = target, claim.state_version + 1
    done = journal.get_move(created.move_id)
    assert done is not None and done.state == "COMPLETED"
    claim = journal.claim_move(
        created.move_id, expected_state="COMPLETED",
        expected_version=done.state_version,
    )
    with pytest.raises(ValueError, match="terminal|illegal|transition"):
        journal.transition_move(
            created.move_id,
            expected_state="COMPLETED",
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch,
            new_state="COPY_IN_PROGRESS",
        )


# ---------------------------------------------------------------------------
# Restart reconciliation + crash behavior
# ---------------------------------------------------------------------------


def _drive(journal, move_id, targets):
    state = "PENDING_COPY"
    version = journal.get_move(move_id).state_version
    for target in targets:
        claim = journal.claim_move(
            move_id, expected_state=state, expected_version=version
        )
        journal.transition_move(
            move_id,
            expected_state=state,
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch,
            new_state=target,
        )
        state, version = target, claim.state_version + 1
    return journal.get_move(move_id)


def test_reconciler_classifies_incomplete_moves(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "reconcile"}'
    )
    pending = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    strobe = journal.create_move_intent(
        **_intent_kwargs(
            tmp_path, content_hash, replica_id,
            destination_object_key="warm/other.json",
            destination_locator=str(tmp_path / "warm-mirror" / "other.json"),
        )
    )
    _drive(journal, strobe.move_id, ["COPY_IN_PROGRESS"])
    assert journal.reconcile(limit=10).processed["RECOVERED_RETRYABLE"] == 1
    # New store instance = restarted process.
    journal2 = MoveJournalStore(db_path=tmp_path / "market.db")
    report = journal2.reconcile(limit=10)
    by_id = {entry.move_id: entry for entry in report.entries}
    assert by_id[pending.move_id].classification == "NO_ACTION"
    assert by_id[strobe.move_id].classification == "NO_ACTION"
    recovered = journal2.get_move(strobe.move_id)
    assert recovered is not None
    assert recovered.state == "FAILED_RETRYABLE"


def test_reconciler_never_promotes_unverified_states(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "nopromote"}'
    )
    manifestations = []
    for tag, targets in (
        ("a", ["COPY_IN_PROGRESS", "COPIED_UNVERIFIED"]),
        ("b", ["COPY_IN_PROGRESS", "COPIED_UNVERIFIED", "DESTINATION_VERIFIED"]),
    ):
        move = journal.create_move_intent(
            **_intent_kwargs(
                tmp_path, content_hash, replica_id,
                destination_object_key=f"warm/{tag}.json",
                destination_locator=str(tmp_path / "warm-mirror" / f"{tag}.json"),
            )
        )
        manifestations.append((move.move_id, targets))
        _drive(journal, move.move_id, targets)
    journal2 = MoveJournalStore(db_path=tmp_path / "market.db")
    report = journal2.reconcile(limit=10)
    by_id = {entry.move_id: entry for entry in report.entries}
    assert by_id[manifestations[0][0]].classification == "REQUIRES_DESTINATION_REPROOF"
    assert by_id[manifestations[1][0]].classification == "REQUIRES_DESTINATION_REPROOF"
    for move_id, _ in manifestations:
        stored = journal2.get_move(move_id)
        assert stored is not None
        assert stored.state in ("COPIED_UNVERIFIED", "DESTINATION_VERIFIED")


def test_reconciler_leaves_safe_and_terminal_states(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "terminal"}'
    )
    present = journal.create_move_intent(
        **_intent_kwargs(
            tmp_path, content_hash, replica_id,
            destination_object_key="warm/present.json",
            destination_locator=str(tmp_path / "warm-mirror" / "present.json"),
        )
    )
    _drive(
        journal, present.move_id,
        ["COPY_IN_PROGRESS", "COPIED_UNVERIFIED", "DESTINATION_VERIFIED",
         "DEST_VERIFIED_SOURCE_PRESENT"],
    )
    blocked = journal.create_move_intent(
        **_intent_kwargs(
            tmp_path, content_hash, replica_id,
            destination_object_key="warm/blocked.json",
            destination_locator=str(tmp_path / "warm-mirror" / "blocked.json"),
        )
    )
    _drive(journal, blocked.move_id, [])
    claim = journal.claim_move(
        blocked.move_id, expected_state="PENDING_COPY",
        expected_version=journal.get_move(blocked.move_id).state_version,
    )
    journal.transition_move(
        blocked.move_id,
        expected_state="PENDING_COPY",
        expected_version=claim.state_version,
        worker_epoch=claim.worker_epoch,
        new_state="FAILED_BLOCKING",
        error_code="INTEGRITY_FAILED",
    )
    journal2 = MoveJournalStore(db_path=tmp_path / "market.db")
    report = journal2.reconcile(limit=10)
    by_id = {entry.move_id: entry for entry in report.entries}
    assert by_id[present.move_id].classification == "SAFE_REDUNDANCY"
    assert present.move_id and journal2.get_move(present.move_id).state == (
        "DEST_VERIFIED_SOURCE_PRESENT"
    )
    assert blocked.move_id not in by_id  # terminal rows are not selected


def test_crash_after_claim_cannot_write_with_stale_epoch(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "crash-claim"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    stale = journal.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=created.state_version,
    )
    # Crash: drop the instance, reopen in a "new process".
    del journal
    journal2 = MoveJournalStore(db_path=tmp_path / "market.db")
    recovered = journal2.get_move(created.move_id)
    assert recovered is not None
    assert recovered.move_id == created.move_id
    assert recovered.state == "PENDING_COPY"
    assert recovered.worker_epoch == stale.worker_epoch
    fresh = journal2.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=recovered.state_version,
    )
    assert fresh.worker_epoch == stale.worker_epoch + 1
    with pytest.raises(MoveAuthorityLostError):
        journal2.transition_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=stale.state_version,
            worker_epoch=stale.worker_epoch,
            new_state="COPY_IN_PROGRESS",
        )


def test_crash_after_transition_recovers_retryable(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "crash-mid"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    _drive(journal, created.move_id, ["COPY_IN_PROGRESS"])
    # Crash: reopen, reconcile.
    del journal
    journal2 = MoveJournalStore(db_path=tmp_path / "market.db")
    report = journal2.reconcile(limit=10)
    assert report.processed["RECOVERED_RETRYABLE"] == 1
    stored = journal2.get_move(created.move_id)
    assert stored is not None
    assert stored.state == "FAILED_RETRYABLE"
    assert stored.move_id == created.move_id


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_concurrent_duplicate_intent_creates_one_row(tmp_path: Path) -> None:
    _, _, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "concurrent"}'
    )
    kwargs = _intent_kwargs(tmp_path, content_hash, replica_id)
    move_ids: list[str] = []
    errors: list[BaseException] = []

    def _worker():
        try:
            journal = MoveJournalStore(db_path=tmp_path / "market.db")
            move_ids.append(
                journal.create_move_intent(**kwargs).move_id
            )
        except BaseException as exc:  # noqa: BLE001 - collected for assertion
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    assert len(move_ids) == 8
    assert len(set(move_ids)) == 1
    with sqlite3.connect(tmp_path / "market.db") as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM market_data_tier_moves WHERE move_id = ?",
            (move_ids[0],),
        ).fetchone()[0]
    assert count == 1


def test_concurrent_claims_exactly_one_wins(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "claim-race"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    outcomes: list[str] = []

    def _worker():
        try:
            worker_journal = MoveJournalStore(db_path=tmp_path / "market.db")
            claim = worker_journal.claim_move(
                created.move_id,
                expected_state="PENDING_COPY",
                expected_version=created.state_version,
            )
            outcomes.append(f"won:{claim.worker_epoch}")
        except MoveAuthorityLostError:
            outcomes.append("lost")

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["lost"] * 7 + ["won:1"]
    stored = journal.get_move(created.move_id)
    assert stored is not None
    assert stored.worker_epoch == 1
    assert stored.state_version == created.state_version + 1


# ---------------------------------------------------------------------------
# Static authority surface
# ---------------------------------------------------------------------------


def _code_only(text: str) -> str:
    out: list[str] = []
    in_docstring = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('"""'):
            if stripped.count('"""') == 2 and len(stripped) > 3:
                continue
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        out.append(line.split("#", 1)[0])
    return "\n".join(out)


def test_no_physical_movement_or_delete_api_in_journal() -> None:
    root = Path(__file__).resolve().parents[1] / "trendforge_api"
    forbidden = (
        "shutil.move",
        "shutil.rmtree",
        "os.rename",
        "os.replace",
        ".unlink(",
        ".rmdir(",
        "def move_replica",
        "def delete_replica",
        "def copy_replica",
        "def restore_replica",
        "def remove_source",
        "def retire_source",
    )
    for name in ("retention_moves.py", "retention_tiering.py"):
        code = _code_only((root / name).read_text(encoding="utf-8"))
        for token in forbidden:
            assert token not in code, f"{name} must not contain {token!r}"


def test_move_error_codes_are_bounded_and_typed(tmp_path: Path) -> None:
    _, journal, content_hash, replica_id = _adopted_source(
        tmp_path, b'{"h1": "codes"}'
    )
    created = journal.create_move_intent(
        **_intent_kwargs(tmp_path, content_hash, replica_id)
    )
    claim = journal.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=created.state_version,
    )
    with pytest.raises(ValueError, match="error_code|error code"):
        journal.transition_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch,
            new_state="FAILED_RETRYABLE",
            error_code="something went wrong in prose with spaces and !!!!",
        )
    journal.transition_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=claim.state_version,
        worker_epoch=claim.worker_epoch,
        new_state="FAILED_RETRYABLE",
        error_code="COPY_INTERRUPTED",
    )
    stored = journal.get_move(created.move_id)
    assert stored is not None
    assert stored.last_error_code == "COPY_INTERRUPTED"
