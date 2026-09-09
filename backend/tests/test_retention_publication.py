from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from trendforge_api.historical_retention import RetentionReferenceType
from trendforge_api.retention_producer import DurableRetentionRegistrar
from trendforge_api.retention_publication import (
    RetentionEvidenceRoot,
    RetentionPublicationRequest,
    RetentionPublicationStatus,
    RetentionPublicationStore,
)

NOW = datetime(2026, 9, 9, 2, 0, tzinfo=UTC)
DAY = date(2026, 9, 8)


class FakeAuthority:
    def __init__(self, *, fail: Exception | None = None) -> None:
        self.fail = fail
        self.references = []

    def register(self, reference):
        self.references.append(reference)
        if self.fail is not None:
            raise self.fail
        return reference


def _request(**changes) -> RetentionPublicationRequest:
    values = {
        "artifact_type": "S8_DECISION_VERSION",
        "artifact_id": "s8-001",
        "artifact_version": "trendforge.s8-scan.v1",
        "reference_type": RetentionReferenceType.DECISION_VERSION,
        "evidence_roots": (
            RetentionEvidenceRoot(
                role="COLLECTOR_RUN",
                run_id="collector-001",
                trading_date=DAY,
            ),
        ),
        "lineage": {"r5RunHash": "r5", "s7RunId": "s7"},
        "created_at": NOW,
    }
    values.update(changes)
    return RetentionPublicationRequest(**values)


def _store(tmp_path: Path, *, authority: FakeAuthority | None = None):
    db_path = tmp_path / "research.db"
    registrar = DurableRetentionRegistrar(
        db_path=db_path,
        authority=authority or FakeAuthority(),
    )
    return RetentionPublicationStore(db_path=db_path, registrar=registrar), db_path


def test_stage_rolls_back_with_caller_transaction(tmp_path: Path) -> None:
    store, db_path = _store(tmp_path)
    store.initialize_schema()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("CREATE TABLE producer_artifact(id TEXT PRIMARY KEY)")
        conn.commit()
        conn.execute("BEGIN")
        conn.execute("INSERT INTO producer_artifact VALUES ('s8-001')")
        store.stage(_request(), connection=conn)
        conn.rollback()
    finally:
        conn.close()
    with sqlite3.connect(db_path) as check:
        assert check.execute("SELECT COUNT(*) FROM producer_artifact").fetchone()[0] == 0
        assert check.execute(
            "SELECT COUNT(*) FROM historical_retention_publications"
        ).fetchone()[0] == 0
        assert check.execute(
            "SELECT COUNT(*) FROM historical_retention_outbox"
        ).fetchone()[0] == 0


def test_two_phase_publication_requires_protection_then_artifact(tmp_path: Path) -> None:
    authority = FakeAuthority()
    store, _ = _store(tmp_path, authority=authority)
    staged = store.stage_owned(_request())
    with pytest.raises(RuntimeError, match="artifact publication is incomplete"):
        store.assert_published(staged.publication_id)
    protected = store.finalize(staged.publication_id)
    assert protected.status is RetentionPublicationStatus.PROTECTED_PENDING_ARTIFACT
    assert len(authority.references) == 1
    published = store.mark_published(staged.publication_id)
    assert published.status is RetentionPublicationStatus.PUBLISHED
    assert store.coverage()["coverage"] == 1.0


def test_same_artifact_cannot_repoint_lineage(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    store.stage_owned(_request())
    with pytest.raises(ValueError, match="cannot be repointed"):
        store.stage_owned(_request(lineage={"r5RunHash": "changed"}))


def test_authority_failure_never_publishes(tmp_path: Path) -> None:
    store, _ = _store(tmp_path, authority=FakeAuthority(fail=RuntimeError("missing evidence")))
    staged = store.stage_owned(_request())
    blocked = store.finalize(staged.publication_id)
    assert blocked.status is RetentionPublicationStatus.FAILED_BLOCKING
    with pytest.raises(RuntimeError, match="artifact cannot publish before"):
        store.mark_published(staged.publication_id)


def test_evidence_root_requires_exact_locator_and_unique_role() -> None:
    with pytest.raises(ValueError, match="requires exact lineage"):
        RetentionEvidenceRoot(role="COLLECTOR_RUN")
    root = RetentionEvidenceRoot(role="COLLECTOR_RUN", run_id="run")
    with pytest.raises(ValueError, match="roles must be unique"):
        _request(evidence_roots=(root, root))
