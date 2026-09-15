"""R-HIST-03F shared fault-acceptance harness (M0).

Test-only helpers: deterministic scratch-DB setup, minimal golden-graph builder,
direct persisted-state oracle (Oracle A), 03E coverage oracle wrapper (Oracle B),
golden manifest capture/comparison, and realistic restart simulation.

No production code. No live network. Scratch DBs only. Fixed timestamps only.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from trendforge_api import storage
from trendforge_api.retention_coverage import audit_coverage
from trendforge_api.selection import r18_governance as governance
from trendforge_api.selection import r18_store
from trendforge_api.selection.r16_store import apply_r16_schema

NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)

# Fields that may legitimately change across recovery attempts; everything else
# in the manifest is semantic and must remain stable.
NON_SEMANTIC_MANIFEST_KEYS = frozenset({"appliedAt", "auditAt", "attempts"})


def init_db(tmp_path: Path, monkeypatch, name: str = "rhist03f.db") -> Path:
    """Create an isolated scratch research DB with R16 + R18 retention schema."""
    db_path = tmp_path / name
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    monkeypatch.delenv("TRENDFORGE_MARKET_DATA_DB_PATH", raising=False)
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    apply_r16_schema()
    r18_store.apply_rhist03d_schema()
    return db_path


def restart() -> None:
    """Simulate process restart: drop process-local DB state.

    All connections are short-lived (no pool), so clearing the initialized-path
    registry forces every owner to re-read persisted state from disk on next use.
    Callers must reinstantiate registrar/store objects after this.
    """
    storage._INITIALIZED_DB_PATHS.clear()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def build_profile(index: int, *, created_at: datetime | None = None):
    at = created_at or (NOW + timedelta(seconds=index))
    return governance.build_strategy_profile_version(
        profile_id=f"PRF-03F-{index:03d}",
        profile_version="1.0.0",
        strategy_id="CONTINUATION",
        strategy_version="1.0.0",
        market="NSE",
        instrument_class="EQUITY",
        horizon="INTRADAY",
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
        model_id=None,
        model_version=None,
        model_hash=None,
        research_ceiling="WAIT",
        activation_allowed=False,
        created_at=at,
        valid_from=NOW,
    )


def persist_profile(index: int, *, finalize: bool = True) -> dict[str, str]:
    """Persist (+ optionally finalize) one golden profile; return its identities."""
    profile = build_profile(index)
    assert r18_store.persist_strategy_profile(profile) is True
    if finalize:
        r18_store.finalize_rhist03d_artifact(
            "STRATEGY_PROFILE",
            profile.profile_id,
            profile.profile_version,
            verify_parents=True,
        )
    with _connect(storage.DB_PATH) as conn:
        link = conn.execute(
            "SELECT artifact_hash, event_id, reference_id, publication_state "
            "FROM r18_retention_links WHERE artifact_type='STRATEGY_PROFILE' "
            "AND artifact_id=? AND artifact_version=?",
            (profile.profile_id, profile.profile_version),
        ).fetchone()
    assert link is not None
    return {
        "profile_id": profile.profile_id,
        "version": profile.profile_version,
        "content_hash": profile.content_hash,
        "event_id": str(link["event_id"]),
        "reference_id": str(link["reference_id"]),
    }


def outbox_row(db_path: Path, event_id: str) -> dict[str, Any] | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT event_id, reference_id, artifact_type, artifact_id, "
            "artifact_version, status, attempts, applied_at, last_error, "
            "payload_hash FROM historical_retention_outbox WHERE event_id=?",
            (event_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def authority_row(db_path: Path, reference_id: str) -> dict[str, Any] | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM historical_retention_references WHERE reference_id=?",
            (reference_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def count_authority_refs(db_path: Path, reference_id: str) -> int:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM historical_retention_references WHERE reference_id=?",
            (reference_id,),
        ).fetchone()
        return int(row["n"])


def artifact_state(
    db_path: Path, table: str, id_col: str, artifact_id: str, version_col: str | None, version: str
) -> str | None:
    with _connect(db_path) as conn:
        if version_col is None:
            row = conn.execute(
                f"SELECT publication_state FROM {table} WHERE {id_col}=?", (artifact_id,)
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT publication_state FROM {table} WHERE {id_col}=? AND {version_col}=?",
                (artifact_id, version),
            ).fetchone()
        return str(row["publication_state"]) if row is not None else None


def profile_state(db_path: Path, profile_id: str, version: str) -> str | None:
    return artifact_state(
        db_path, "strategy_profile_versions", "profile_id", profile_id, "profile_version", version
    )


def link_state(db_path: Path, artifact_type: str, artifact_id: str, version: str) -> str | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT publication_state FROM r18_retention_links WHERE artifact_type=? "
            "AND artifact_id=? AND artifact_version=?",
            (artifact_type, artifact_id, version),
        ).fetchone()
        return str(row["publication_state"]) if row is not None else None


def outbox_count(db_path: Path) -> int:
    with _connect(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) AS n FROM historical_retention_outbox").fetchone()["n"])


def coverage_report(db_path: Path, *, audit_at: datetime = NOW) -> dict[str, Any]:
    """Oracle B: accepted 03E coverage oracle (read-only)."""
    return audit_coverage(db_path=db_path, audit_at=audit_at)


def capture_manifest(db_path: Path, identities: list[dict[str, str]]) -> dict[str, Any]:
    """Capture the semantic golden manifest (deterministic order)."""
    ordered = sorted(identities, key=lambda item: (item["profile_id"], item["version"]))
    profiles: list[dict[str, Any]] = []
    for item in ordered:
        event = outbox_row(db_path, item["event_id"])
        ref = authority_row(db_path, item["reference_id"])
        profiles.append(
            {
                "profile_id": item["profile_id"],
                "version": item["version"],
                "content_hash": item["content_hash"],
                "event_id": item["event_id"],
                "reference_id": item["reference_id"],
                "outbox_status": event["status"] if event else None,
                "artifact_state": profile_state(db_path, item["profile_id"], item["version"]),
                "link_state": link_state(db_path, "STRATEGY_PROFILE", item["profile_id"], item["version"]),
                "authority_type": ref["reference_type"] if ref else None,
                "authority_hash": ref["artifact_hash"] if ref else None,
            }
        )
    report = coverage_report(db_path)
    return {
        "profiles": profiles,
        "coverage": {
            "expectedCount": report["expectedCount"],
            "coveredCount": report["coveredCount"],
            "coverage": report["coverage"],
            "orphanCount": report["orphanCount"],
            "blockingCount": report["blockingCount"],
            "verdict": report["verdict"],
            "reportHash": report["reportHash"],
        },
    }


def assert_manifest_healthy(manifest: dict[str, Any]) -> None:
    """Golden baseline acceptance: non-empty, fully covered, zero orphans/blockers."""
    coverage = manifest["coverage"]
    assert manifest["profiles"], "golden graph must be non-empty"
    assert coverage["expectedCount"] > 0
    assert coverage["coveredCount"] == coverage["expectedCount"]
    assert coverage["coverage"] == 1.0
    assert coverage["orphanCount"] == 0
    assert coverage["blockingCount"] == 0
    assert coverage["verdict"] == "PASS"
    for profile in manifest["profiles"]:
        assert profile["outbox_status"] == "APPLIED", profile
        assert profile["artifact_state"] == "APPLIED", profile
        assert profile["link_state"] == "APPLIED", profile
        assert profile["authority_type"] == "STRATEGY_PROFILE", profile
        assert profile["authority_hash"] == profile["content_hash"], profile


def assert_manifests_equal(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Semantic manifest equality across restart/recovery (reportHash must match)."""
    assert before["profiles"] == after["profiles"]
    assert before["coverage"] == after["coverage"]


__all__ = [
    "NOW",
    "artifact_state",
    "assert_manifest_healthy",
    "assert_manifests_equal",
    "authority_row",
    "build_profile",
    "capture_manifest",
    "count_authority_refs",
    "coverage_report",
    "init_db",
    "link_state",
    "outbox_count",
    "outbox_row",
    "persist_profile",
    "profile_state",
    "restart",
]
