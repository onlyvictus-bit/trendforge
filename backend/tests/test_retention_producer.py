from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from trendforge_api.historical_retention import RetentionReferenceType
from trendforge_api.retention_producer import (
    DurableRetentionRegistrar,
    RetentionEvidenceIntent,
    RetentionOutboxStatus,
)


NOW = datetime(2026, 9, 9, 1, 30, tzinfo=UTC)
DAY = date(2026, 9, 8)
HASH = "A" * 64


class FakeAuthority:
    def __init__(self, *, fail: Exception | None = None) -> None:
        self.fail = fail
        self.calls = []

    def register(self, reference):
        self.calls.append(reference)
        if self.fail is not None:
            raise self.fail
        return reference


def _intent(**changes) -> RetentionEvidenceIntent:
    values = {
        "artifact_type": "S8_DECISION_VERSION",
        "artifact_id": "s8-run-001",
        "artifact_version": "1.0.0",
        "reference_type": RetentionReferenceType.DECISION_VERSION,
        "run_id": "collector-run-001",
        "trading_date": DAY,
        "content_hash": HASH,
        "created_at": NOW,
    }
    values.update(changes)
    return RetentionEvidenceIntent(**values)


def test_intent_identity_is_deterministic_and_hash_normalized() -> None:
    first = _intent()
    second = _intent(content_hash=HASH.lower())

    assert first.content_hash == HASH.lower()
    assert first.event_id == second.event_id
    assert first.reference_id == second.reference_id
    assert len(first.payload_hash) == 64


def test_intent_requires_exact_lineage_locator() -> None:
    with pytest.raises(ValueError, match="requires run_id, trading_date, or content_hash"):
        _intent(run_id=None, trading_date=None, content_hash=None)


def test_enqueue_is_idempotent(tmp_path: Path) -> None:
    registrar = DurableRetentionRegistrar(db_path=tmp_path / "retention.db")
    first = registrar.enqueue(_intent())
    second = registrar.enqueue(_intent())

    assert first.event_id == second.event_id
    assert second.status is RetentionOutboxStatus.PENDING
    with sqlite3.connect(tmp_path / "retention.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[0] == 1


def test_enqueue_can_share_producer_transaction_and_rollback(tmp_path: Path) -> None:
    db_path = tmp_path / "retention.db"
    registrar = DurableRetentionRegistrar(db_path=db_path)
    registrar.initialize_schema()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE producer_artifacts (artifact_id TEXT PRIMARY KEY)")
        conn.commit()
        conn.execute("BEGIN")
        conn.execute("INSERT INTO producer_artifacts VALUES (?)", ("s8-run-001",))
        registrar.enqueue(_intent(), connection=conn)
        conn.rollback()
    finally:
        conn.close()

    with sqlite3.connect(db_path) as check:
        assert check.execute("SELECT COUNT(*) FROM producer_artifacts").fetchone()[0] == 0
        assert check.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[0] == 0


def test_dispatch_applies_once_and_replay_is_idempotent(tmp_path: Path) -> None:
    authority = FakeAuthority()
    registrar = DurableRetentionRegistrar(db_path=tmp_path / "retention.db", authority=authority)
    pending = registrar.enqueue(_intent())

    applied = registrar.dispatch(pending.event_id)
    replay = registrar.dispatch(pending.event_id)

    assert applied.status is RetentionOutboxStatus.APPLIED
    assert replay.status is RetentionOutboxStatus.APPLIED
    assert len(authority.calls) == 1
    assert registrar.assert_publishable(pending.event_id).status is RetentionOutboxStatus.APPLIED


def test_authority_failure_is_blocking_and_publish_fails_closed(tmp_path: Path) -> None:
    authority = FakeAuthority(fail=RuntimeError("protected evidence missing"))
    registrar = DurableRetentionRegistrar(db_path=tmp_path / "retention.db", authority=authority)
    pending = registrar.enqueue(_intent())

    receipt = registrar.dispatch(pending.event_id)

    assert receipt.status is RetentionOutboxStatus.FAILED_BLOCKING
    assert "protected evidence missing" in (receipt.last_error or "")
    with pytest.raises(RuntimeError, match="publication must fail closed"):
        registrar.assert_publishable(pending.event_id)
    with pytest.raises(RuntimeError, match="retention event is blocking"):
        registrar.dispatch(pending.event_id)


def test_payload_tampering_is_detected_before_authority(tmp_path: Path) -> None:
    authority = FakeAuthority()
    db_path = tmp_path / "retention.db"
    registrar = DurableRetentionRegistrar(db_path=db_path, authority=authority)
    pending = registrar.enqueue(_intent())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE historical_retention_outbox SET payload_json = ? WHERE event_id = ?",
            ('{"tampered":true}', pending.event_id),
        )
        conn.commit()

    with pytest.raises(RuntimeError, match="payload hash mismatch"):
        registrar.dispatch(pending.event_id)
    assert authority.calls == []


def test_column_tampering_is_detected_even_when_payload_hash_is_unchanged(tmp_path: Path) -> None:
    authority = FakeAuthority()
    db_path = tmp_path / "retention.db"
    registrar = DurableRetentionRegistrar(db_path=db_path, authority=authority)
    pending = registrar.enqueue(_intent())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE historical_retention_outbox SET artifact_id = ? WHERE event_id = ?",
            ("repointed-artifact", pending.event_id),
        )
        conn.commit()

    with pytest.raises(RuntimeError, match="payload columns disagree"):
        registrar.dispatch(pending.event_id)
    assert authority.calls == []


def test_reconcile_pending_is_bounded_and_deterministic(tmp_path: Path) -> None:
    authority = FakeAuthority()
    registrar = DurableRetentionRegistrar(db_path=tmp_path / "retention.db", authority=authority)
    first = registrar.enqueue(
        _intent(artifact_id="a", created_at=datetime(2026, 9, 9, 1, 0, tzinfo=UTC))
    )
    second = registrar.enqueue(
        _intent(artifact_id="b", created_at=datetime(2026, 9, 9, 1, 1, tzinfo=UTC))
    )

    receipts = registrar.reconcile_pending(limit=1)

    assert [item.event_id for item in receipts] == [first.event_id]
    assert registrar.assert_publishable(first.event_id).status is RetentionOutboxStatus.APPLIED
    with pytest.raises(RuntimeError, match="publication must fail closed"):
        registrar.assert_publishable(second.event_id)
