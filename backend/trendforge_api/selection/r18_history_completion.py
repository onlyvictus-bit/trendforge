"""R-HIST-03D completion safety: DB guards, upgrade inventory and PIT proof.

This module tightens the already-owned R18/R16 contracts. It never repairs
history on read and never grants promotion or execution authority.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Callable

from .. import storage
from ..r16_retention import verified_record as verified_r16_record
from .r16_pit import _payload_hash as r16_payload_hash

TYPED_REFERENCE_TYPES = ("ML_DATASET", "MODEL_VERSION", "STRATEGY_PROFILE", "AUDIT")
IMMUTABLE_ARTIFACT_TABLES = (
    "ml_frozen_datasets",
    "ml_governed_model_versions",
    "strategy_profile_versions",
    "governance_audit_records",
)
FULLY_IMMUTABLE_TABLES = ("ml_frozen_dataset_members",)


def _columns(conn: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})"))


def _install_transition_guard(conn: sqlite3.Connection, table: str) -> None:
    columns = _columns(conn, table)
    if "publication_state" not in columns:
        raise RuntimeError(f"WAIT_RHIST03D_PUBLICATION_STATE_MISSING:{table}")
    immutable = tuple(column for column in columns if column != "publication_state")
    same = " AND ".join(f"NEW.{column} IS OLD.{column}" for column in immutable)
    trigger = f"rhist03d_guard_{table}_update"
    conn.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    conn.execute(
        f"CREATE TRIGGER {trigger} BEFORE UPDATE ON {table} "
        "WHEN NOT (OLD.publication_state='PENDING_RETENTION' "
        "AND NEW.publication_state='APPLIED' AND " + same + ") "
        "BEGIN SELECT RAISE(ABORT, 'R-HIST-03D immutable artifact'); END"
    )
    delete_trigger = f"rhist03d_guard_{table}_delete"
    conn.execute(f"DROP TRIGGER IF EXISTS {delete_trigger}")
    conn.execute(
        f"CREATE TRIGGER {delete_trigger} BEFORE DELETE ON {table} "
        "BEGIN SELECT RAISE(ABORT, 'R-HIST-03D immutable artifact'); END"
    )


def _install_full_guard(conn: sqlite3.Connection, table: str) -> None:
    for operation in ("UPDATE", "DELETE"):
        trigger = f"rhist03d_guard_{table}_{operation.lower()}"
        conn.execute(f"DROP TRIGGER IF EXISTS {trigger}")
        conn.execute(
            f"CREATE TRIGGER {trigger} BEFORE {operation} ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'R-HIST-03D immutable artifact'); END"
        )


def install_rhist03d_db_guards() -> None:
    """Install idempotent guards after the explicit 03D schema exists."""
    with storage.connect() as conn:
        names = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for table in IMMUTABLE_ARTIFACT_TABLES:
            if table not in names:
                raise RuntimeError(f"WAIT_RHIST03D_TABLE_MISSING:{table}")
            _install_transition_guard(conn, table)
        for table in FULLY_IMMUTABLE_TABLES:
            if table not in names:
                raise RuntimeError(f"WAIT_RHIST03D_TABLE_MISSING:{table}")
            _install_full_guard(conn, table)
        if "r18_retention_links" not in names:
            raise RuntimeError("WAIT_RHIST03D_TABLE_MISSING:r18_retention_links")
        _install_transition_guard(conn, "r18_retention_links")
        conn.commit()


def rhist03d_upgrade_inventory() -> dict[str, Any]:
    """Classify old typed namespace usage without modifying it."""
    typed = ",".join("?" for _ in TYPED_REFERENCE_TYPES)
    with storage.connect() as conn:
        old_events = conn.execute(
            f"SELECT status,COUNT(*) AS n FROM historical_retention_outbox "
            f"WHERE reference_type IN ({typed}) AND artifact_hash IS NULL "
            "AND content_hash IS NOT NULL GROUP BY status",
            TYPED_REFERENCE_TYPES,
        ).fetchall()
        old_refs = conn.execute(
            f"SELECT COUNT(*) FROM historical_retention_references "
            f"WHERE reference_type IN ({typed}) AND artifact_hash IS NULL "
            "AND content_hash IS NOT NULL",
            TYPED_REFERENCE_TYPES,
        ).fetchone()[0]
    by_status = {str(row["status"]): int(row["n"]) for row in old_events}
    applied_events = by_status.get("APPLIED", 0)
    return {
        "preFixTypedEventsByStatus": dict(sorted(by_status.items())),
        "preFixAppliedTypedEvents": applied_events,
        "preFixAppliedTypedReferences": int(old_refs),
        "supersedableTypedEvents": by_status.get("PENDING", 0)
        + by_status.get("FAILED_BLOCKING", 0),
        "stopRequired": bool(applied_events or old_refs),
    }


def assert_rhist03d_upgrade_safe() -> dict[str, Any]:
    inventory = rhist03d_upgrade_inventory()
    if inventory["stopRequired"]:
        raise RuntimeError("WAIT_RHIST03D_PREFIX_APPLIED_TYPED_IDENTITY_REQUIRES_MIGRATION")
    return inventory


def _parse_aware(value: Any, code: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError(code)
    return parsed


def _root_hashes(publication: Any) -> set[str]:
    return {
        str(root.content_hash).lower()
        for root in publication.evidence_roots
        if getattr(root, "content_hash", None)
    }


def verify_dataset_r16_parents(
    payload: dict[str, Any],
    *,
    verifier: Callable[..., tuple[Any, dict[str, Any], Any]] = verified_r16_record,
) -> None:
    """Prove each frozen member agrees with its canonical R16 chronology/identity."""
    for member in payload.get("members", ()):
        _, decision, decision_publication = verifier(
            storage.connect(), "DECISION_VERSION", member["decisionVersionId"]
        )
        if r16_payload_hash(decision) != member["decisionVersionHash"]:
            raise RuntimeError("WAIT_RHIST03D_DECISION_HASH_MISMATCH")
        decision_at = _parse_aware(decision.get("decisionCutoffAt"), "WAIT_RHIST03D_DECISION_CUTOFF_INVALID")
        declared_decision = _parse_aware(member.get("decisionAt"), "WAIT_RHIST03D_MEMBER_DECISION_TIME_INVALID")
        declared_cutoff = _parse_aware(member.get("decisionDataCutoff"), "WAIT_RHIST03D_MEMBER_CUTOFF_INVALID")
        if decision_at != declared_decision or decision_at != declared_cutoff:
            raise RuntimeError("WAIT_RHIST03D_DECISION_CUTOFF_MISMATCH")
        authoritative_available = _parse_aware(
            decision.get("maxInputAvailableAt"),
            "WAIT_RHIST03D_PARENT_AVAILABILITY_REQUIRED",
        )
        declared_available = _parse_aware(
            member.get("maxFeatureAvailableAt"),
            "WAIT_RHIST03D_MEMBER_AVAILABILITY_REQUIRED",
        )
        if authoritative_available > decision_at:
            raise RuntimeError("WAIT_RHIST03D_PARENT_AVAILABILITY_EXCEEDS_CUTOFF")
        if declared_available != authoritative_available:
            raise RuntimeError("WAIT_RHIST03D_FEATURE_AVAILABILITY_MISMATCH")
        for source_key, member_key, code in (
            ("profileId", "profileId", "PROFILE_ID"),
            ("profileVersion", "profileVersion", "PROFILE_VERSION"),
            ("timeframe", "timeframe", "TIMEFRAME"),
            ("publicState", "publicState", "PUBLIC_STATE"),
            ("setupPolicyId", "setupId", "SETUP_POLICY"),
        ):
            if str(decision.get(source_key)) != str(member.get(member_key)):
                raise RuntimeError(f"WAIT_RHIST03D_{code}_MISMATCH")
        source_bars = {str(value).lower() for value in decision.get("sourceBarHashes", ())}
        member_inputs = {str(value).lower() for value in member.get("inputHashes", ())}
        if not source_bars or not source_bars.issubset(member_inputs):
            raise RuntimeError("WAIT_RHIST03D_INPUT_HASH_MISMATCH")
        member_roots = {
            str(root.get("contentHash")).lower()
            for root in member.get("evidenceRoots", ())
            if root.get("contentHash")
        }
        if not _root_hashes(decision_publication).issubset(member_roots):
            raise RuntimeError("WAIT_RHIST03D_DECISION_EVIDENCE_ROOT_MISSING")

        if member.get("outcomeId"):
            _, outcome, outcome_publication = verifier(
                storage.connect(), "OUTCOME", member["outcomeId"]
            )
            if r16_payload_hash(outcome) != member.get("outcomeHash"):
                raise RuntimeError("WAIT_RHIST03D_OUTCOME_HASH_MISMATCH")
            available = _parse_aware(
                outcome.get("labelComputedAt"),
                "WAIT_RHIST03D_OUTCOME_AVAILABILITY_REQUIRED",
            )
            if available != _parse_aware(
                member.get("outcomeAvailableAt"),
                "WAIT_RHIST03D_MEMBER_OUTCOME_AVAILABILITY_REQUIRED",
            ):
                raise RuntimeError("WAIT_RHIST03D_OUTCOME_AVAILABILITY_MISMATCH")
            if member.get("labelAvailableAt") and available != _parse_aware(
                member["labelAvailableAt"], "WAIT_RHIST03D_LABEL_AVAILABILITY_INVALID"
            ):
                raise RuntimeError("WAIT_RHIST03D_LABEL_AVAILABILITY_MISMATCH")
            if not _root_hashes(outcome_publication).issubset(member_roots):
                raise RuntimeError("WAIT_RHIST03D_OUTCOME_EVIDENCE_ROOT_MISSING")

        if member.get("revisionId"):
            _, revision, revision_publication = verifier(
                storage.connect(), "REVISION", member["revisionId"]
            )
            if r16_payload_hash(revision) != member.get("revisionHash"):
                raise RuntimeError("WAIT_RHIST03D_REVISION_HASH_MISMATCH")
            recorded = _parse_aware(
                revision.get("recordedAt"), "WAIT_RHIST03D_REVISION_AVAILABILITY_REQUIRED"
            )
            if recorded != _parse_aware(
                member.get("revisionAvailableAt"),
                "WAIT_RHIST03D_MEMBER_REVISION_AVAILABILITY_REQUIRED",
            ):
                raise RuntimeError("WAIT_RHIST03D_REVISION_AVAILABILITY_MISMATCH")
            if not _root_hashes(revision_publication).issubset(member_roots):
                raise RuntimeError("WAIT_RHIST03D_REVISION_EVIDENCE_ROOT_MISSING")


def rhist03d_integrity_status() -> dict[str, Any]:
    """Read-only operator visibility for publication/integrity state."""
    with storage.connect() as conn:
        counts: dict[str, dict[str, int]] = {}
        for table in IMMUTABLE_ARTIFACT_TABLES:
            rows = conn.execute(
                f"SELECT publication_state,COUNT(*) AS n FROM {table} GROUP BY publication_state"
            ).fetchall()
            counts[table] = {str(row["publication_state"]): int(row["n"]) for row in rows}
        pending_outbox = conn.execute(
            "SELECT COUNT(*) FROM historical_retention_outbox WHERE artifact_hash IS NOT NULL AND status='PENDING'"
        ).fetchone()[0]
        blocking_outbox = conn.execute(
            "SELECT COUNT(*) FROM historical_retention_outbox WHERE artifact_hash IS NOT NULL AND status='FAILED_BLOCKING'"
        ).fetchone()[0]
    return {
        "artifactsByState": counts,
        "typedPendingOutbox": int(pending_outbox),
        "typedBlockingOutbox": int(blocking_outbox),
        "upgradeInventory": rhist03d_upgrade_inventory(),
    }


__all__ = (
    "assert_rhist03d_upgrade_safe",
    "install_rhist03d_db_guards",
    "rhist03d_integrity_status",
    "rhist03d_upgrade_inventory",
    "r16_payload_hash",
    "verify_dataset_r16_parents",
)
