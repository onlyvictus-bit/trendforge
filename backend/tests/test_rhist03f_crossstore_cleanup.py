"""R-HIST-03F M3 — cross-store, cleanup, invention-negative, golden restart.

Reuses the accepted 03E paired-pipeline builder (separate research + market
scratch files). Dual oracles throughout; the declared cross-store audit is
Oracle B for multi-store scenarios.

F_IO_04, cross-store matrix, cleanup safety (§18), historical-invention
negative (§21), golden restart (§19). Scratch DBs only. Synthetic bytes only.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from trendforge_api.historical_retention import RetentionReference, RetentionReferenceType
from trendforge_api.market_data_store import (
    MANIFEST_SCHEMA_VERSION,
    ManifestEntry,
    ManifestStatus,
    MarketDataStore,
    SnapshotManifest,
)
from trendforge_api.r16_retention import resolve_s8_parent
from trendforge_api.retention_coverage import CoverageStatus, audit_coverage

from tests.rhist03f_harness import (
    NOW,
    assert_manifest_healthy,
    capture_manifest,
    count_authority_refs,
    coverage_report,
    init_db,
    outbox_row,
    persist_profile,
    restart,
)
from tests.test_rhist03e_m3a_acceptance import _run_paired_pipeline
from tests.test_rhist03e_source_to_end import _trading_days
from tests.test_rhist03e_source_to_end import TRADE_DATE


def _declared(research_db: Path, market_db: Path) -> dict[str, object]:
    from typing import Any

    report: dict[str, Any] = audit_coverage(
        db_path=research_db,
        market_db_paths=[market_db],
        audit_at=NOW,
    )

    assert isinstance(report, dict), (
        "03E audit_coverage contract violation: "
        f"expected dict, got {type(report).__name__}"
    )

    assert "verdict" in report
    assert "expectedCount" in report
    assert "coveredCount" in report

    return report


def _s8_pub(research_db: Path) -> dict:
    with sqlite3.connect(research_db) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM historical_retention_publications WHERE artifact_type='S8_DECISION_VERSION'"
        ).fetchone()
    assert row is not None
    return dict(row)


def _s8_roots(pub: dict) -> list[str]:
    return [
        str(root["contentHash"])
        for root in json.loads(pub["lineage_json"])["evidenceRoots"]
        if root.get("contentHash")
    ]


def _paired_manifest(research_db: Path, market_db: Path) -> dict:
    with sqlite3.connect(research_db) as conn:
        conn.row_factory = sqlite3.Row
        s8 = conn.execute(
            "SELECT artifact_id, status FROM historical_retention_publications "
            "WHERE artifact_type='S8_DECISION_VERSION'"
        ).fetchall()
        hyps = conn.execute("SELECT COUNT(*) AS n FROM pit_hypotheses").fetchone()["n"]
        obs = conn.execute("SELECT COUNT(*) AS n FROM pit_observations").fetchone()["n"]
        outbox = conn.execute(
            "SELECT status, COUNT(*) AS n FROM historical_retention_outbox GROUP BY status"
        ).fetchall()
    with sqlite3.connect(market_db) as conn:
        conn.row_factory = sqlite3.Row
        refs = conn.execute(
            "SELECT reference_type, COUNT(*) AS n FROM historical_retention_references GROUP BY 1"
        ).fetchall()
        objects = conn.execute("SELECT COUNT(*) AS n FROM market_data_objects").fetchone()[0]
    report = _declared(research_db, market_db)
    return {
        "s8": [(r["artifact_id"], r["status"]) for r in s8],
        "hypotheses": hyps,
        "observations": obs,
        "outbox": sorted((r["status"], r["n"]) for r in outbox),
        "authority": sorted((r["reference_type"], r["n"]) for r in refs),
        "objects": objects,
        "coverage": {k: report[k] for k in ("expectedCount", "coveredCount", "coverage",
                                            "orphanCount", "blockingCount", "verdict", "reportHash")},
    }


# ---------------------------------------------------------------------------
# X1/GOLDEN-RESTART — paired healthy graph survives realistic restart
# ---------------------------------------------------------------------------


def test_X1a_paired_graph_passes_and_survives_restart_without_repair(
    tmp_path, monkeypatch
) -> None:
    """X1-A — healthy restart: the durable graph survives with NO repair.

    No reconciliation is run: a healthy graph must re-read identically from
    disk (same semantic identities, hashes, reference IDs, publication
    identities, coverage PASS including a stable reportHash).
    """
    research_db, market_db, s8_run_id = _run_paired_pipeline(tmp_path, monkeypatch, "03f-x1")
    assert research_db.resolve() != market_db.resolve()

    first = _declared(research_db, market_db)
    assert first["verdict"] == "PASS"
    assert first["expectedCount"] > 0
    assert first["coveredCount"] == first["expectedCount"]
    assert first["orphanCount"] == 0
    assert first["blockingCount"] == 0
    manifest = _paired_manifest(research_db, market_db)

    # Realistic restart only: drop process-local state and re-read from disk.
    restart()
    assert _paired_manifest(research_db, market_db) == manifest
    assert _declared(research_db, market_db)["verdict"] == "PASS"
    assert _s8_pub(research_db)["artifact_id"] == s8_run_id


def test_X1b_pending_graph_recovers_after_restart_via_canonical_reconciliation(
    tmp_path, monkeypatch
) -> None:
    """X1-B — pending recovery: legitimate PENDING work converges after restart.

    Uses the accepted M0 PENDING construction (persisted but not finalized
    R18 profile): hidden from governed reads and non-PASS before restart,
    then exactly the canonical ``reconcile_pending_coverage`` resumes it to
    APPLIED/PUBLISHED → PASS with identical identities and no duplicates.
    """
    from trendforge_api.retention_coverage import reconcile_pending_coverage
    from trendforge_api.retention_producer import RetentionOutboxStatus

    db_path = init_db(tmp_path, monkeypatch, "x1b.db")
    identities = [persist_profile(71, finalize=False)]
    item = identities[0]

    # Oracle A (direct): durable PENDING, hidden from governed reads.
    event = outbox_row(db_path, item["event_id"])
    assert event is not None and event["status"] == RetentionOutboxStatus.PENDING.value
    before = coverage_report(db_path)
    assert before["verdict"] != "PASS"
    assert CoverageStatus.PENDING_RETENTION.value in {
        str(f["status"]) for f in before["findings"]
    }

    restart()
    result = reconcile_pending_coverage(limit=10)
    assert result["processed"] == 1
    assert result["after"]["verdict"] == "PASS"

    # Oracle B + identities: same event/reference/hash, one semantic ref.
    manifest = capture_manifest(db_path, identities)
    assert_manifest_healthy(manifest)
    assert manifest["profiles"][0]["event_id"] == item["event_id"]
    assert manifest["profiles"][0]["reference_id"] == item["reference_id"]
    assert manifest["profiles"][0]["content_hash"] == item["content_hash"]
    assert count_authority_refs(db_path, item["reference_id"]) == 1


# ---------------------------------------------------------------------------
# F_IO_04 — unavailable external store fails closed, never ignored-to-PASS
# ---------------------------------------------------------------------------


def test_F_IO_04_unavailable_market_store_fails_closed(tmp_path, monkeypatch) -> None:
    research_db, market_db, _ = _run_paired_pipeline(tmp_path, monkeypatch, "03f-io4")
    assert _declared(research_db, market_db)["verdict"] == "PASS"

    # Oracle A (direct): the declared store path is missing on disk.
    # NOTE: the live scratch DB cannot be renamed on Windows (file lock), so
    # the unavailable store is simulated with a declared-but-missing path.
    # This exercises the identical contract path (MARKET_STORE_UNAVAILABLE →
    # REGISTRY_ERROR → non-PASS) as a rename/delete on POSIX.
    missing = market_db.with_name("missing-03f-io4.db")
    assert not missing.exists()
    report = _declared(research_db, missing)
    assert report["verdict"] != "PASS"
    assert report["verdict"] in ("FAIL", "UNKNOWN", "EMPTY")
    assert any(
        "MARKET_STORE_UNAVAILABLE" in str(f.get("detail", ""))
        for f in report["findings"]
    ), "unavailable store must surface the typed fail-closed finding"
    assert not missing.exists(), "failed audit must not recreate the store"
    assert _declared(research_db, market_db)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# X3 — external orphan fails the declared audit, heals on legitimate removal
# ---------------------------------------------------------------------------


def test_X3_external_orphan_fails_declared_audit_then_heals(tmp_path, monkeypatch) -> None:
    from trendforge_api.historical_retention import HistoricalRetentionAuthority

    research_db, market_db, _ = _run_paired_pipeline(tmp_path, monkeypatch, "03f-x3")
    assert _declared(research_db, market_db)["verdict"] == "PASS"

    # Oracle A (direct): genuine evidence (an existing object hash, shaped
    # exactly like real rows which carry run_id None) under a reference_id no
    # research outbox event owns. Registration passes every fail-closed
    # existence check, so the row is a true unexplained authority reference.
    with sqlite3.connect(market_db) as conn:
        victim = conn.execute(
            "SELECT content_hash FROM market_data_objects LIMIT 1"
        ).fetchone()[0]
    authority = HistoricalRetentionAuthority(db_path=market_db)
    authority.register(
        RetentionReference(
            reference_id="intruder-03f-x3",
            reference_type=RetentionReferenceType.DECISION_VERSION,
            content_hash=str(victim),
            run_id=None,
            created_at=NOW,
        )
    )
    report = _declared(research_db, market_db)
    assert report["verdict"] == "FAIL"
    assert report["orphanCount"] >= 1
    assert CoverageStatus.RETENTION_ORPHAN.value in {
        str(f["status"]) for f in report["findings"]
    }

    with sqlite3.connect(market_db) as conn:
        conn.execute(
            "DELETE FROM historical_retention_references WHERE reference_id=?",
            ("intruder-03f-x3",),
        )
        conn.commit()
    assert _declared(research_db, market_db)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# C1 — cleanup preserves governed evidence, still deletes the unreferenced
# ---------------------------------------------------------------------------


def test_C1_cleanup_preserves_governed_evidence_but_deletes_unreferenced(
    tmp_path, monkeypatch
) -> None:
    research_db, market_db, _ = _run_paired_pipeline(tmp_path, monkeypatch, "03f-c1")
    pub = _s8_pub(research_db)
    roots = _s8_roots(pub)
    assert roots, "golden S8 must carry object-backed roots"

    # Oracle A, before: governed evidence pinned by hash, path, bytes and
    # authority identity (the relationship cleanup must preserve).
    market_root = tmp_path / "market-data"
    protected: dict[str, dict[str, object]] = {}
    with sqlite3.connect(market_db) as conn:
        conn.row_factory = sqlite3.Row
        for root_hash in roots:
            obj = conn.execute(
                "SELECT object_path, size_bytes FROM market_data_objects "
                "WHERE content_hash=?",
                (root_hash,),
            ).fetchone()
            assert obj is not None, f"governed object missing before cleanup: {root_hash[:12]}"
            obj_path = Path(str(obj["object_path"]))
            if not obj_path.is_absolute():
                obj_path = market_root / obj_path
            refs = {
                str(r["reference_id"])
                for r in conn.execute(
                    "SELECT reference_id FROM historical_retention_references "
                    "WHERE content_hash=?",
                    (root_hash,),
                ).fetchall()
            }
            assert refs, f"governed evidence must carry authority: {root_hash[:12]}"
            with open(obj_path, "rb") as handle:
                blob = handle.read()
            assert hashlib.sha256(blob).hexdigest() == root_hash
            assert len(blob) == int(obj["size_bytes"])
            protected[root_hash] = {
                "path": obj_path,
                "sha256": hashlib.sha256(blob).hexdigest(),
                "size": len(blob),
                "references": refs,
            }

    store = MarketDataStore(root=tmp_path / "market-data", db_path=market_db)
    stray_ref = store.install_object(b'{"stray":"unreferenced"}', extension="json",
                                     media_type="application/json")
    stray_manifest = SnapshotManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        run_id="stray-unreferenced-run",
        registry_sha256="7" * 64,
        trading_date=date(2026, 6, 2),
        slot="1500",
        generated_at=NOW,
        entries=(
            ManifestEntry(
                source_key="source_stray",
                status=ManifestStatus.SUCCESS_NEW,
                content_hash=stray_ref.content_hash,
                object_path=str(stray_ref.path),
                normalized_row_count=1,
                retry_count=0,
            ),
        ),
    )
    store.write_manifest(stray_manifest)

    days = list(_trading_days(TRADE_DATE, 22)) + [date(2026, 6, 2)]
    applied = store.cleanup_retention(
        as_of_date=date(2026, 9, 15),
        completed_trading_days=days,
        detailed_trading_days=0,
        dry_run=False,
    )

    # Governed roots survive byte-identical with authority intact; the
    # genuinely unreferenced stray is deleted from both index and disk.
    with sqlite3.connect(market_db) as conn:
        conn.row_factory = sqlite3.Row
        for root_hash in roots:
            assert conn.execute(
                "SELECT 1 FROM market_data_objects WHERE content_hash=?",
                (root_hash,),
            ).fetchone()[0] == 1, f"governed evidence deleted: {root_hash[:12]}"
            after_refs = {
                str(r["reference_id"])
                for r in conn.execute(
                    "SELECT reference_id FROM historical_retention_references "
                    "WHERE content_hash=?",
                    (root_hash,),
                ).fetchall()
            }
            assert after_refs == protected[root_hash]["references"], (
                f"authority relationship must still resolve: {root_hash[:12]}"
            )
        assert conn.execute(
            "SELECT 1 FROM market_data_objects WHERE content_hash=?",
            (stray_ref.content_hash,),
        ).fetchone() is None
    for root_hash, pin in protected.items():
        survivor = pin["path"]
        assert isinstance(survivor, Path) and survivor.is_file()
        with open(survivor, "rb") as handle:
            survivor_bytes = handle.read()
        assert hashlib.sha256(survivor_bytes).hexdigest() == pin["sha256"], (
            f"governed bytes must be untouched: {root_hash[:12]}"
        )
        assert len(survivor_bytes) == pin["size"]
    assert str(stray_ref.path) in set(applied.deleted_object_paths)
    assert not Path(str(stray_ref.path)).exists(), "eligible object must be gone from disk"
    for root_hash in roots:
        assert all(root_hash not in str(path) for path in applied.deleted_object_paths)

    assert _declared(research_db, market_db)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# H1 — historical invention: latest bytes never substitute missing originals
# ---------------------------------------------------------------------------


def test_H1_latest_evidence_never_substitutes_missing_original(tmp_path, monkeypatch) -> None:
    from trendforge_api.retention_coverage import reconcile_pending_coverage

    research_db, market_db, s8_run_id = _run_paired_pipeline(tmp_path, monkeypatch, "03f-h1")
    pub = _s8_pub(research_db)
    original = _s8_roots(pub)[0]

    with sqlite3.connect(market_db) as conn:
        conn.execute("DELETE FROM market_data_objects WHERE content_hash=?", (original,))
        conn.commit()
    store = MarketDataStore(root=tmp_path / "market-data", db_path=market_db)
    newer = store.install_object(b'{"newer":"not-history"}', extension="json",
                                 media_type="application/json")
    assert newer.content_hash != original

    # Oracle A, setup: the tempting H2 replacement genuinely exists on disk
    # and in the object index — the negative test is real.
    with sqlite3.connect(market_db) as conn:
        assert conn.execute(
            "SELECT 1 FROM market_data_objects WHERE content_hash=?",
            (newer.content_hash,),
        ).fetchone() == (1,)
    assert Path(str(newer.path)).is_file()

    # Recovery may resume deterministic pending work (none here) but must not
    # invent lineage: no new reference, no rebinding, still blocked.
    resumed = reconcile_pending_coverage(limit=50)
    assert resumed["processed"] == 0
    with sqlite3.connect(market_db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) AS n FROM historical_retention_references WHERE content_hash=?",
            (newer.content_hash,),
        ).fetchone()[0] == 0
    # No historical row rewritten: the full S8 publication row is identical,
    # D still references H1, and no member/publication names H2.
    assert _s8_pub(research_db) == pub
    assert original in _s8_roots(_s8_pub(research_db))
    with sqlite3.connect(research_db) as conn:
        member_hits = conn.execute(
            "SELECT COUNT(*) FROM historical_retention_publication_members "
            "WHERE root_json LIKE ?",
            (f"%{newer.content_hash}%",),
        ).fetchone()[0]
        lineage_hits = conn.execute(
            "SELECT COUNT(*) FROM historical_retention_publications "
            "WHERE lineage_json LIKE ?",
            (f"%{newer.content_hash}%",),
        ).fetchone()[0]
    assert member_hits == 0
    assert lineage_hits == 0

    report = _declared(research_db, market_db)
    assert report["verdict"] != "PASS"
    s8_statuses = {
        str(f["status"]) for f in report["findings"] if f["artifactId"] == s8_run_id
    }
    assert s8_statuses, "S8 decision must still be enumerated after H1 loss"
    assert "COVERED" not in s8_statuses, "missing original must never report COVERED"

    # Governed reconstruction with the TRUE recorded identities still refuses:
    # the missing original cannot be swapped for the newer bytes.
    from trendforge_api.selection.r16_pit import _payload_hash as _r16_hash

    with sqlite3.connect(research_db) as conn:
        conn.row_factory = sqlite3.Row
        scan = conn.execute(
            "SELECT payload_json FROM selection_scan_runs WHERE run_id=?", (s8_run_id,)
        ).fetchone()
        prow = conn.execute(
            "SELECT publication_id, lineage_hash FROM historical_retention_publications "
            "WHERE artifact_type='S8_DECISION_VERSION' AND artifact_id=?",
            (s8_run_id,),
        ).fetchone()
    payload = json.loads(scan["payload_json"])
    with sqlite3.connect(research_db) as conn:
        conn.row_factory = sqlite3.Row
        with pytest.raises(Exception, match="MISSING|BROKEN|BOUND|INVALID|PROOF"):
            resolve_s8_parent(
                conn,
                run_id=s8_run_id,
                expected_hash=_r16_hash(payload),
                expected_version=str(payload.get("schemaVersion") or ""),
                expected_publication_id=str(prow["publication_id"]),
                expected_lineage_hash=str(prow["lineage_hash"]),
            )
