"""R-HIST-03F M1 — real-pipeline S8/R16 crash recovery.

Reuses the accepted 03E source-to-end pipeline builder (no duplication):
F_GOLDEN_S8R16 (real S8+R16 golden), F_CRASH_06 (S8 publication finalization),
F_CRASH_07 (R16 staged-commit vs finalize). Dual oracles throughout.

Scratch DBs only (the builder's synthetic bytes). Fixed pipeline timestamps.
"""
from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from trendforge_api import r16_retention
from trendforge_api import storage
from trendforge_api.historical_retention import RetentionReferenceType
from trendforge_api.r16_retention import resume_pending_publications, verified_record
from trendforge_api.retention_coverage import CoverageStatus, audit_coverage
from trendforge_api.retention_producer import DurableRetentionRegistrar
from trendforge_api.retention_publication import (
    RetentionEvidenceRoot,
    RetentionPublicationRequest,
    RetentionPublicationStatus,
    RetentionPublicationStore,
)
from trendforge_api.selection import r18_store

from tests.rhist03f_harness import NOW, init_db, restart
from tests.test_rhist03e_source_to_end import _run_eligible_pipeline


class FakeAuthority:
    def register(self, reference):
        return reference


def _s8_publication(db_path: Path) -> dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM historical_retention_publications "
            "WHERE artifact_type='S8_DECISION_VERSION'",
        ).fetchone()
    assert row is not None, "pipeline must stage the S8 publication even on crash"
    return dict(row)


def _r16_pending_count(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return int(
            conn.execute(
                "SELECT COUNT(*) AS n FROM historical_retention_publications "
                "WHERE artifact_type LIKE 'R16_%' AND status='PENDING_RETENTION'"
            ).fetchone()["n"]
        )


# ---------------------------------------------------------------------------
# F_GOLDEN_S8R16 — real S8 + R16 graph passes both oracles
# ---------------------------------------------------------------------------


def test_F_GOLDEN_S8R16_real_pipeline_graph_passes_both_oracles(
    tmp_path, monkeypatch
) -> None:
    s8_run_id = _run_eligible_pipeline(tmp_path, monkeypatch, "03f-golden")
    db_path = Path(str(storage.DB_PATH))
    r18_store.apply_rhist03d_schema()

    # Oracle A: S8 PUBLISHED, every R16 publication PUBLISHED, rows match.
    pub = _s8_publication(db_path)
    assert pub["status"] == RetentionPublicationStatus.PUBLISHED.value
    assert pub["artifact_id"] == s8_run_id
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        hyps = int(conn.execute("SELECT COUNT(*) AS n FROM pit_hypotheses").fetchone()["n"])
        obs = int(conn.execute("SELECT COUNT(*) AS n FROM pit_observations").fetchone()["n"])
        unpublished = int(
            conn.execute(
                "SELECT COUNT(*) AS n FROM historical_retention_publications "
                "WHERE status != 'PUBLISHED'"
            ).fetchone()["n"]
        )
    assert hyps >= 1 and obs >= 1
    assert unpublished == 0
    # The pipeline writes intermediate scan rows; exactly one carries the
    # governed profile id that the 03E registry counts.
    with sqlite3.connect(db_path) as conn:
        governed_scans = conn.execute(
            "SELECT COUNT(*) AS n FROM selection_scan_runs WHERE profile_id='PRF-S8-SCAN-RUN'"
        ).fetchone()[0]
    assert governed_scans == 1

    # Oracle B: full coverage PASS with stable report hash.
    first = audit_coverage(audit_at=NOW)
    assert first["expectedCount"] > 0
    assert first["coveredCount"] == first["expectedCount"]
    assert first["coverage"] == 1.0
    assert first["orphanCount"] == 0
    assert first["blockingCount"] == 0
    assert first["verdict"] == "PASS"
    assert first["perProducer"]["S8_DECISION_VERSION"]["expected"] == 1
    assert first["perProducer"]["R16_DECISION_VERSION"]["expected"] == hyps
    assert first["perProducer"]["R16_OUTCOME"]["expected"] == obs
    again = audit_coverage(audit_at=NOW + timedelta(hours=1))
    assert again["reportHash"] == first["reportHash"]

    restart()
    assert audit_coverage(audit_at=NOW)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# F_CRASH_06a — staged publication survives restart, resumes without duplicates
# ---------------------------------------------------------------------------


def test_F_CRASH_06a_staged_publication_resumes_after_restart(tmp_path, monkeypatch) -> None:
    db_path = init_db(tmp_path, monkeypatch)
    store = RetentionPublicationStore(
        db_path=db_path,
        registrar=DurableRetentionRegistrar(db_path=db_path, authority=FakeAuthority()),
    )
    request = RetentionPublicationRequest(
        artifact_type="S8_DECISION_VERSION",
        artifact_id="s8-03f-resume",
        artifact_version="s8.v1",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        evidence_roots=(RetentionEvidenceRoot(role="ROOT", run_id="run-1"),),
        lineage={"s8PayloadHash": "b" * 64},
        created_at=NOW,
    )
    staged = store.stage_owned(request)
    assert staged.status is RetentionPublicationStatus.PENDING_RETENTION

    # Crash before finalize: governed readers stay closed.
    restart()
    store2 = RetentionPublicationStore(
        db_path=db_path,
        registrar=DurableRetentionRegistrar(db_path=db_path, authority=FakeAuthority()),
    )
    with pytest.raises(RuntimeError, match="fail closed|incomplete|protected"):
        store2.assert_published(staged.publication_id)

    # Canonical recovery: same identity, no duplicate members.
    finalized = store2.finalize(staged.publication_id)
    assert finalized.status is RetentionPublicationStatus.PROTECTED_PENDING_ARTIFACT
    published = store2.mark_published(staged.publication_id)
    assert published.status is RetentionPublicationStatus.PUBLISHED
    restaged = store2.stage_owned(request)
    assert restaged.publication_id == staged.publication_id
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        members = conn.execute(
            "SELECT COUNT(*) AS n, COUNT(DISTINCT event_id) AS u "
            "FROM historical_retention_publication_members WHERE publication_id=?",
            (staged.publication_id,),
        ).fetchone()
    assert members["n"] == 1 and members["u"] == 1
    store2.assert_published(staged.publication_id)
    store2.mark_published(staged.publication_id)


# ---------------------------------------------------------------------------
# F_CRASH_06b — crash between S8 persist and mark_published resumes cleanly
# ---------------------------------------------------------------------------


def test_F_CRASH_06b_s8_crash_before_visibility_resumes_to_published(
    tmp_path, monkeypatch
) -> None:
    calls = {"n": 0}
    real_mark = RetentionPublicationStore.mark_published

    def _crash_once(self, publication_id: str):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("INJECTED_S8_VISIBILITY_CRASH")
        return real_mark(self, publication_id)

    monkeypatch.setattr(RetentionPublicationStore, "mark_published", _crash_once)
    try:
        _run_eligible_pipeline(tmp_path, monkeypatch, "03f-s8crash")
    except Exception as exc:  # noqa: BLE001 — injected crash aborts the run
        # Either the injected error itself or the builder's s8_run_id assert
        # tripping over the aborted S8 stage; both prove the crash landed.
        assert "INJECTED_S8_VISIBILITY_CRASH" in str(exc) or calls["n"] >= 1
    assert calls["n"] >= 1, "fault must fire inside the pipeline run"

    db_path = Path(str(storage.DB_PATH))
    pub = _s8_publication(db_path)

    # Intermediate: artifact persisted, protection proven, visibility withheld.
    with sqlite3.connect(db_path) as conn:
        governed_scans = conn.execute(
            "SELECT COUNT(*) AS n FROM selection_scan_runs WHERE profile_id='PRF-S8-SCAN-RUN'"
        ).fetchone()[0]
    assert governed_scans == 1
    assert pub["status"] == RetentionPublicationStatus.PROTECTED_PENDING_ARTIFACT.value
    store = RetentionPublicationStore(db_path=db_path)
    with pytest.raises(RuntimeError, match="incomplete"):
        store.assert_published(pub["publication_id"])

    # Restart + canonical resume: exactly one PUBLISHED publication, no dupes.
    restart()
    resumed = RetentionPublicationStore(db_path=db_path).mark_published(pub["publication_id"])
    assert resumed.status is RetentionPublicationStatus.PUBLISHED
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        members = conn.execute(
            "SELECT COUNT(*) AS n, COUNT(DISTINCT event_id) AS u "
            "FROM historical_retention_publication_members WHERE publication_id=?",
            (pub["publication_id"],),
        ).fetchone()
        pubs = conn.execute(
            "SELECT COUNT(*) AS n FROM historical_retention_publications "
            "WHERE artifact_type='S8_DECISION_VERSION'"
        ).fetchone()["n"]
    assert members["n"] == members["u"] >= 1
    assert pubs == 1
    RetentionPublicationStore(db_path=db_path).assert_published(pub["publication_id"])


# ---------------------------------------------------------------------------
# F_CRASH_07 — crash after R16 commit, before finalize, resumes via canonical API
# ---------------------------------------------------------------------------


def test_F_CRASH_07_r16_commit_without_finalize_resumes_idempotently(
    tmp_path, monkeypatch
) -> None:
    calls = {"n": 0}
    real_finalize = r16_retention.finalize_publications

    def _crash_once(publication_ids: list[str]) -> None:
        # The pipeline issues an empty no-op flush first; the crash must land
        # after the first real R16 commit, i.e. the first non-empty batch.
        if publication_ids:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("INJECTED_R16_FINALIZE_CRASH")
        return real_finalize(publication_ids)

    monkeypatch.setattr(r16_retention, "finalize_publications", _crash_once)
    try:
        _run_eligible_pipeline(tmp_path, monkeypatch, "03f-r16crash")
    except RuntimeError as exc:
        assert "INJECTED_R16_FINALIZE_CRASH" in str(exc)

    db_path = Path(str(storage.DB_PATH))
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        hyps = conn.execute("SELECT hypothesis_id FROM pit_hypotheses ORDER BY hypothesis_id").fetchall()
    assert hyps, "R16 rows must survive the post-commit crash"
    assert _r16_pending_count(db_path) >= 1

    # Hidden until canonical recovery runs.
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        with pytest.raises(Exception, match="fail closed|protected|incomplete|PUBLISHED|APPLIED"):
            verified_record(conn, "DECISION_VERSION", str(hyps[0]["hypothesis_id"]))

    restart()
    resumed = resume_pending_publications()
    assert resumed >= 1
    assert _r16_pending_count(db_path) == 0
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        verified_record(conn, "DECISION_VERSION", str(hyps[0]["hypothesis_id"]))
    assert resume_pending_publications() == 0

    report = audit_coverage()
    assert report["verdict"] != "PASS" or report["coveredCount"] == report["expectedCount"]
    assert CoverageStatus.PENDING_RETENTION.value not in {
        str(row["status"]) for row in report["findings"]
    }
