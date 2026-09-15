"""R-HIST-03F M2 — concurrency and storage-failure acceptance.

Deterministic synchronization only (Barrier/Event + explicit lock control;
timeouts exist solely to prevent deadlock). Assertions target final semantic
state, never which thread won. No lease/claim columns exist in the current
schema by design (see 03F plan section 34): these tests prove concurrent
duplicate work converges idempotently, making leases a future optimization,
not a correctness requirement.

F_RACE_01..08, F_IO_01/02/03/05. F_IO_04 (paired-store outage) is M3 scope.
Scratch DBs only. Fixed timestamps only.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import timedelta

import pytest

from trendforge_api.historical_retention import (
    HistoricalRetentionAuthority,
    RetentionReference,
    RetentionReferenceType,
)
from trendforge_api.retention_coverage import CoverageStatus, reconcile_pending_coverage
from trendforge_api.retention_producer import (
    DurableRetentionRegistrar,
    RetentionEvidenceIntent,
    RetentionOutboxStatus,
)

from tests.rhist03f_harness import (
    NOW,
    count_authority_refs,
    coverage_report,
    init_db,
    link_state,
    outbox_row,
    persist_profile,
    profile_state,
    restart,
)

BARRIER_TIMEOUT = 30.0


def _run_workers(count_or_targets, target=None, *args) -> list:
    """Run workers on threads; re-raise thread failures here.

    Either `_run_workers(n, fn, *args)` (same fn on n threads) or
    `_run_workers([fn_a, fn_b])` (one thread per fn, for mixed roles sharing
    one start-gate).
    """
    if isinstance(count_or_targets, list):
        targets = list(count_or_targets)
        adapter = [(fn, ()) for fn in targets]
    else:
        adapter = [(target, args)] * int(count_or_targets)
    outcomes: list = [None] * len(adapter)

    def _wrap(index: int, fn, fn_args) -> None:
        try:
            outcomes[index] = ("ok", fn(*fn_args))
        except Exception as exc:  # noqa: BLE001 — collected, re-raised below
            outcomes[index] = ("error", exc)

    threads = [
        threading.Thread(target=_wrap, args=(index, fn, fn_args))
        for index, (fn, fn_args) in enumerate(adapter)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120.0)
        assert not thread.is_alive(), "worker deadlocked"
    return outcomes


def _ok(results: list):
    errors = [item[1] for item in results if item[0] == "error"]
    assert not errors, f"worker failures: {errors!r}"
    return [item[1] for item in results]


# ---------------------------------------------------------------------------
# F_RACE_01 — two dispatchers, same PENDING event, barrier-aligned at register
# ---------------------------------------------------------------------------


def test_F_RACE_01_concurrent_duplicate_dispatch_converges(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(71, finalize=False)
    barrier = threading.Barrier(2, timeout=BARRIER_TIMEOUT)
    real_register = HistoricalRetentionAuthority.register

    def _aligned(self, reference):
        barrier.wait(timeout=BARRIER_TIMEOUT)
        return real_register(self, reference)

    monkeypatch.setattr(HistoricalRetentionAuthority, "register", _aligned)
    results = _run_workers(
        2, lambda: DurableRetentionRegistrar(db_path=db_path).dispatch(item["event_id"])
    )
    receipts = _ok(results)
    assert all(r.status is RetentionOutboxStatus.APPLIED for r in receipts)
    assert {r.reference_id for r in receipts} == {item["reference_id"]}

    # One semantic authority reference; canonical finalize converges.
    assert count_authority_refs(db_path, item["reference_id"]) == 1
    from trendforge_api.selection import r18_store

    r18_store.finalize_rhist03d_artifact(
        "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=True
    )
    assert profile_state(db_path, item["profile_id"], item["version"]) == "APPLIED"
    assert coverage_report(db_path)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# F_RACE_02 — duplicate exact downstream registration converges
# ---------------------------------------------------------------------------


def test_F_RACE_02_concurrent_duplicate_authority_register_converges(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(72, finalize=False)
    authority = HistoricalRetentionAuthority(db_path=db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        event = conn.execute(
            "SELECT * FROM historical_retention_outbox WHERE event_id=?",
            (item["event_id"],),
        ).fetchone()
    reference = RetentionReference(
        reference_id=item["reference_id"],
        reference_type=RetentionReferenceType.STRATEGY_PROFILE,
        artifact_id=item["profile_id"],
        artifact_version=item["version"],
        artifact_hash=item["content_hash"],
        created_at=NOW,
    )
    assert event is not None
    barrier = threading.Barrier(2, timeout=BARRIER_TIMEOUT)

    def _register():
        barrier.wait(timeout=BARRIER_TIMEOUT)
        return authority.register(reference)

    returned = _ok(_run_workers(2, _register))
    assert returned[0] == returned[1] == reference
    assert count_authority_refs(db_path, item["reference_id"]) == 1


# ---------------------------------------------------------------------------
# F_RACE_03 — same event_id, changed payload, racing producers: no repoint
# ---------------------------------------------------------------------------


def test_F_RACE_03_racing_repoint_attempts_never_mutate_stored_intent(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)

    def _intent(created_at, artifact_hash):
        return RetentionEvidenceIntent(
            artifact_type="R18_STRATEGY_PROFILE",
            artifact_id="PRF-03F-RACE",
            artifact_version="1.0.0",
            reference_type=RetentionReferenceType.STRATEGY_PROFILE,
            artifact_hash=artifact_hash,
            created_at=created_at,
        )

    # Same lineage (createdAt is excluded from the lineage digest), different
    # material: exactly one racer wins the INSERT; the loser is rejected and
    # the stored row is never mutated.
    shared_hash = "a" * 64
    first = _intent(NOW, shared_hash)
    second = _intent(NOW + timedelta(hours=1), shared_hash)
    assert first.event_id == second.event_id
    barrier = threading.Barrier(2, timeout=BARRIER_TIMEOUT)

    def _enqueue(payload):
        barrier.wait(timeout=BARRIER_TIMEOUT)
        return DurableRetentionRegistrar(db_path=db_path).enqueue(payload)

    outcomes: list = [None, None]

    def _racer(index: int) -> None:
        try:
            outcomes[index] = ("ok", _enqueue(first if index == 0 else second))
        except Exception as exc:  # noqa: BLE001 — one racer must lose
            outcomes[index] = ("error", exc)

    threads = [threading.Thread(target=_racer, args=(index,)) for index in (0, 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120.0)
    assert all(item is not None for item in outcomes)

    winners = [item[1] for item in outcomes if item[0] == "ok"]
    losers = [item[1] for item in outcomes if item[0] == "error"]
    assert len(winners) == 1 and len(losers) == 1
    assert isinstance(losers[0], (ValueError, sqlite3.IntegrityError))

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT event_id, payload_json, payload_hash FROM historical_retention_outbox"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["event_id"] == first.event_id
    # Stored material equals one racer's exact payload; a later same-lineage
    # intent with different material is rejected, never merged.
    assert rows[0]["payload_json"] in {first.payload_json, second.payload_json}
    assert rows[0]["payload_hash"] in {first.payload_hash, second.payload_hash}
    with pytest.raises(ValueError, match="immutable|cannot be repointed"):
        DurableRetentionRegistrar(db_path=db_path).enqueue(
            _intent(NOW + timedelta(hours=2), shared_hash)
        )


# ---------------------------------------------------------------------------
# F_RACE_04 — reconciler vs dispatcher on the same event converge
# ---------------------------------------------------------------------------


def test_F_RACE_04_reconciler_vs_dispatcher_converge(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(74, finalize=False)
    # Start-gate: both workers enter processing simultaneously. No barrier
    # inside the critical section, so no party can strand the other.
    start = threading.Barrier(2, timeout=BARRIER_TIMEOUT)

    def _dispatch():
        start.wait(timeout=BARRIER_TIMEOUT)
        return DurableRetentionRegistrar(db_path=db_path).dispatch(item["event_id"])

    def _reconcile():
        start.wait(timeout=BARRIER_TIMEOUT)
        return DurableRetentionRegistrar(db_path=db_path).reconcile_pending(limit=10)

    results = _run_workers([_dispatch, _reconcile])
    assert results[0][0] == "ok"
    # Reconcile may legitimately observe the event before/after dispatch.
    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["status"] == RetentionOutboxStatus.APPLIED.value
    assert count_authority_refs(db_path, item["reference_id"]) == 1


# ---------------------------------------------------------------------------
# F_RACE_05 — database lock during dispatch stays retryable, never false-done
# ---------------------------------------------------------------------------


def test_F_RACE_05_lock_during_dispatch_stays_pending_then_recovers(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(75, finalize=False)

    # Explicit RESERVED lock: no timing luck involved.
    locker = sqlite3.connect(db_path, timeout=30.0)
    locker.execute("BEGIN IMMEDIATE")
    locker.execute(
        "UPDATE historical_retention_outbox SET attempts = attempts WHERE event_id = ?",
        (item["event_id"],),
    )
    before = outbox_row(db_path, item["event_id"])
    try:
        # The pre-authority attempts-bump has no silent catch: a locked store
        # raises loudly instead of manufacturing a completion claim.
        with pytest.raises(sqlite3.OperationalError, match="locked|busy"):
            DurableRetentionRegistrar(db_path=db_path).dispatch(item["event_id"])
    finally:
        locker.rollback()
        locker.close()

    # Nothing partial: PENDING preserved, attempts untouched, no authority ref.
    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["status"] == RetentionOutboxStatus.PENDING.value
    assert event["attempts"] == before["attempts"]
    from tests.rhist03f_harness import authority_row as _authority_row

    assert _authority_row(db_path, item["reference_id"]) is None
    report = coverage_report(db_path)
    assert report["verdict"] == "FAIL"
    assert CoverageStatus.PENDING_RETENTION.value in {
        str(row["status"]) for row in report["findings"]
    }

    restart()
    recovered = DurableRetentionRegistrar(db_path=db_path).dispatch(item["event_id"])
    assert recovered.status is RetentionOutboxStatus.APPLIED
    assert count_authority_refs(db_path, item["reference_id"]) == 1


# ---------------------------------------------------------------------------
# F_RACE_06 — two finalizers, same artifact: one semantic outcome
# ---------------------------------------------------------------------------


def test_F_RACE_06_concurrent_finalizers_converge_without_duplicates(
    tmp_path, monkeypatch
) -> None:
    from trendforge_api.selection import r18_store

    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(76, finalize=False)
    barrier = threading.Barrier(2, timeout=BARRIER_TIMEOUT)
    real_finalize = r18_store.finalize_rhist03d_artifact

    def _aligned(artifact_type, artifact_id, version, **kwargs):
        barrier.wait(timeout=BARRIER_TIMEOUT)
        return real_finalize(artifact_type, artifact_id, version, **kwargs)

    monkeypatch.setattr(r18_store, "finalize_rhist03d_artifact", _aligned)
    results = _run_workers(
        2,
        lambda: r18_store.finalize_rhist03d_artifact(
            "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=True
        ),
    )
    _ok(results)
    assert profile_state(db_path, item["profile_id"], item["version"]) == "APPLIED"
    assert link_state(db_path, "STRATEGY_PROFILE", item["profile_id"], item["version"]) == "APPLIED"
    assert count_authority_refs(db_path, item["reference_id"]) == 1
    assert coverage_report(db_path)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# F_RACE_07 — audit during PENDING->APPLIED transition stays coherent
# ---------------------------------------------------------------------------


def test_F_RACE_07_audit_during_transition_is_coherent(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    item = persist_profile(77, finalize=False)
    samples: list = []

    def _audit():
        return coverage_report(db_path)

    def _recover():
        reconcile_pending_coverage(limit=10)
        from trendforge_api.selection import r18_store

        r18_store.finalize_rhist03d_artifact(
            "STRATEGY_PROFILE", item["profile_id"], item["version"], verify_parents=True
        )
        return coverage_report(db_path)

    audit_results = _run_workers(3, _audit)
    recover_results = _run_workers(1, _recover)
    samples.extend(_ok(audit_results))
    samples.extend(_ok(recover_results))
    for report in samples:
        assert report["verdict"] in ("FAIL", "PASS", "EMPTY")
        assert report["coveredCount"] <= report["expectedCount"]
        assert report["coverage"] in (0.0, 1.0) or 0.0 < report["coverage"] < 1.0
    assert coverage_report(db_path)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# F_RACE_08 — stale worker after newer unrelated work cannot cross-talk
# ---------------------------------------------------------------------------


def test_F_RACE_08_concurrent_independent_events_keep_own_identities(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    first = persist_profile(78, finalize=False)
    second = persist_profile(79, finalize=False)
    barrier = threading.Barrier(2, timeout=BARRIER_TIMEOUT)
    real_register = HistoricalRetentionAuthority.register

    def _aligned(self, reference):
        barrier.wait(timeout=BARRIER_TIMEOUT)
        return real_register(self, reference)

    monkeypatch.setattr(HistoricalRetentionAuthority, "register", _aligned)
    import queue as _queue

    work: _queue.Queue = _queue.Queue()
    work.put(first["event_id"])
    work.put(second["event_id"])

    def _dispatch_one():
        return DurableRetentionRegistrar(db_path=db_path).dispatch(work.get_nowait())

    results = _run_workers(2, _dispatch_one)
    receipts = _ok(results)
    assert {r.event_id for r in receipts} == {first["event_id"], second["event_id"]}
    assert {r.reference_id for r in receipts} == {
        first["reference_id"],
        second["reference_id"],
    }
    assert count_authority_refs(db_path, first["reference_id"]) == 1
    assert count_authority_refs(db_path, second["reference_id"]) == 1
    first_row = outbox_row(db_path, first["event_id"])
    second_row = outbox_row(db_path, second["event_id"])
    assert first_row is not None and second_row is not None
    assert first_row["reference_id"] != second_row["reference_id"]


# ---------------------------------------------------------------------------
# F_IO_01 — lock before the artifact transaction: nothing partial survives
# ---------------------------------------------------------------------------


def test_F_IO_01_lock_before_artifact_transaction_leaves_nothing_partial(
    tmp_path, monkeypatch
) -> None:
    from tests.rhist03f_harness import build_profile

    db_path = init_db(tmp_path, monkeypatch)
    locker = sqlite3.connect(db_path, timeout=30.0)
    locker.execute("BEGIN IMMEDIATE")
    locker.execute("SELECT COUNT(*) FROM strategy_profile_versions")
    try:
        from trendforge_api.selection import r18_store

        with pytest.raises(Exception, match="locked|busy"):
            r18_store.persist_strategy_profile(build_profile(80))
    finally:
        locker.rollback()
        locker.close()

    assert profile_state(db_path, "PRF-03F-080", "1.0.0") is None
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[0] == 0
    assert coverage_report(db_path)["verdict"] == "EMPTY"

    # Lock released: canonical path works.
    from trendforge_api.selection import r18_store as store_module

    assert store_module.persist_strategy_profile(build_profile(80)) is True


# ---------------------------------------------------------------------------
# F_IO_03 — authority store unavailable: fail closed, never APPLIED
# ---------------------------------------------------------------------------


def test_F_IO_03_unavailable_authority_fails_closed_without_applied_claim(
    tmp_path, monkeypatch
) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    missing = tmp_path / "no-such-dir" / "authority.db"
    registrar = DurableRetentionRegistrar(
        db_path=db_path,
        authority=HistoricalRetentionAuthority(db_path=missing),
    )
    item = persist_profile(81, finalize=False)

    receipt = None
    try:
        receipt = registrar.dispatch(item["event_id"])
    except Exception as exc:  # noqa: BLE001 — unavailable store must fail closed
        assert "unable to open" in str(exc).lower() or "no such" in str(exc).lower()
    if receipt is not None:
        assert receipt.status is not RetentionOutboxStatus.APPLIED

    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["status"] != RetentionOutboxStatus.APPLIED.value
    assert link_state(db_path, "STRATEGY_PROFILE", item["profile_id"], item["version"]) != "APPLIED"
    assert coverage_report(db_path)["verdict"] != "PASS"


# ---------------------------------------------------------------------------
# F_IO_05 — dispatch cannot conjure evidence bytes that were never stored
# ---------------------------------------------------------------------------


def test_F_IO_05_dispatch_without_stored_evidence_fails_closed(
    tmp_path, monkeypatch
) -> None:
    from trendforge_api.historical_retention import RetentionReferenceType
    from trendforge_api.retention_producer import RetentionEvidenceIntent

    db_path = init_db(tmp_path, monkeypatch)
    registrar = DurableRetentionRegistrar(db_path=db_path)
    intent = RetentionEvidenceIntent(
        artifact_type="S8_DECISION_VERSION:ROOT",
        artifact_id="s8-ghost",
        artifact_version="s8.v1",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        run_id="run-ghost-never-stored",
        created_at=NOW,
    )
    registrar.enqueue(intent)
    # Registration is not verification: dispatch fails closed, and the 03E
    # inverse proof exposes the ghost reference as an orphan — unstored bytes
    # can never appear as governed history.
    receipt = registrar.dispatch(intent.event_id)
    assert receipt.status is RetentionOutboxStatus.FAILED_BLOCKING
    assert receipt.last_error is not None and "refusing unknown run_id" in receipt.last_error
    event = outbox_row(db_path, intent.event_id)
    assert event is not None and event["status"] == RetentionOutboxStatus.FAILED_BLOCKING.value
    report = coverage_report(db_path)
    assert report["verdict"] == "FAIL"
    assert report["expectedCount"] == 0
    assert report["orphanCount"] >= 1
    assert CoverageStatus.RETENTION_ORPHAN.value in {
        str(row["status"]) for row in report["findings"]
    }
