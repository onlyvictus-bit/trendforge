"""R-HIST-03D completion safety: DB guards, upgrade inventory and PIT proof.

This module tightens the already-owned R18/R16 contracts. It never repairs
history on read and never grants promotion or execution authority.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any, Callable

from .. import storage
from ..historical_retention import RetentionReferenceType
from ..retention_producer import DurableRetentionRegistrar, RetentionEvidenceIntent
from ..r16_retention import verified_record as verified_r16_record
from .r16_pit import _payload_hash as r16_payload_hash

TYPED_REFERENCE_TYPES = ("ML_DATASET", "MODEL_VERSION", "STRATEGY_PROFILE", "AUDIT")
IMMUTABLE_ARTIFACT_TABLES = (
    "ml_frozen_datasets",
    "ml_governed_model_versions",
    "strategy_profile_versions",
    "governance_audit_records",
)
FULLY_IMMUTABLE_TABLES = ("ml_frozen_dataset_members", "r18_retention_supersessions")


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
        for operation in ("UPDATE", "DELETE"):
            conn.execute(
                f"CREATE TRIGGER IF NOT EXISTS rhist03d_superseded_outbox_{operation.lower()} "
                f"BEFORE {operation} ON historical_retention_outbox "
                "WHEN EXISTS (SELECT 1 FROM r18_retention_supersessions "
                "WHERE old_event_id=OLD.event_id) "
                "BEGIN SELECT RAISE(ABORT, 'R-HIST-03D immutable superseded event'); END"
            )
        conn.execute(
            "CREATE TRIGGER IF NOT EXISTS rhist03d_superseded_reference_insert "
            "BEFORE INSERT ON historical_retention_references "
            "WHEN EXISTS (SELECT 1 FROM r18_retention_supersessions "
            "WHERE old_reference_id=NEW.reference_id) "
            "BEGIN SELECT RAISE(ABORT, 'R-HIST-03D superseded reference'); END"
        )
        conn.commit()


def rhist03d_upgrade_inventory() -> dict[str, Any]:
    """Classify old typed namespace usage without modifying it."""
    typed = ",".join("?" for _ in TYPED_REFERENCE_TYPES)
    with storage.connect() as conn:
        old_events = conn.execute(
            f"SELECT status,COUNT(*) AS n FROM historical_retention_outbox "
            f"WHERE reference_type IN ({typed}) AND artifact_hash IS NULL "
            "AND artifact_type='R18_' || reference_type "
            "AND content_hash IS NOT NULL GROUP BY status",
            TYPED_REFERENCE_TYPES,
        ).fetchall()
        old_refs = conn.execute(
            f"SELECT COUNT(*) FROM historical_retention_references AS r "
            f"WHERE reference_type IN ({typed}) AND artifact_hash IS NULL "
            "AND content_hash IS NOT NULL AND ("
            "reference_type IN ('MODEL_VERSION','STRATEGY_PROFILE') OR EXISTS ("
            "SELECT 1 FROM historical_retention_outbox AS e WHERE e.reference_id=r.reference_id "
            "AND e.artifact_type='R18_' || e.reference_type))",
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


def _old_typed_intent(row: sqlite3.Row) -> RetentionEvidenceIntent:
    if (
        row["reference_type"] not in TYPED_REFERENCE_TYPES
        or row["artifact_type"] != "R18_" + row["reference_type"]
        or row["artifact_hash"] is not None or row["content_hash"] is None
        or row["run_id"] is not None or row["trading_date"] is not None
    ):
        raise RuntimeError("WAIT_RHIST03D_NOT_PREFIX_SEMANTIC_EVENT")
    intent = RetentionEvidenceIntent(
        artifact_type=row["artifact_type"], artifact_id=row["artifact_id"],
        artifact_version=row["artifact_version"],
        reference_type=RetentionReferenceType(row["reference_type"]),
        content_hash=row["content_hash"], created_at=datetime.fromisoformat(row["created_at"]),
    )
    if (row["event_id"], row["reference_id"], row["payload_json"], row["payload_hash"]) != (
        intent.event_id, intent.reference_id, intent.payload_json, intent.payload_hash,
    ):
        raise RuntimeError("WAIT_RHIST03D_PREFIX_EVENT_IDENTITY_MISMATCH")
    return intent


def _corrected_intent(old: RetentionEvidenceIntent) -> RetentionEvidenceIntent:
    return RetentionEvidenceIntent(
        artifact_type=old.artifact_type, artifact_id=old.artifact_id,
        artifact_version=old.artifact_version, reference_type=old.reference_type,
        artifact_hash=old.content_hash, created_at=old.created_at,
    )


def resolve_retention_link(
    conn: sqlite3.Connection, artifact_type: str, artifact_id: str, artifact_version: str,
) -> dict[str, Any] | None:
    """Resolve immutable supersession evidence; never update the original link."""
    row = conn.execute(
        "SELECT * FROM r18_retention_links WHERE artifact_type=? AND artifact_id=? AND artifact_version=?",
        (artifact_type, artifact_id, artifact_version),
    ).fetchone()
    if row is None:
        return None
    link = dict(row)
    recovery = conn.execute(
        "SELECT * FROM r18_retention_supersessions WHERE old_event_id=?", (link["event_id"],)
    ).fetchone()
    if recovery is None:
        return link
    registrar = DurableRetentionRegistrar(db_path=storage.DB_PATH)
    old_row = registrar._load_verified_row(conn, link["event_id"])
    old = _old_typed_intent(old_row)
    corrected = _corrected_intent(old)
    expected = {
        "old_event_id": old.event_id, "old_reference_id": old.reference_id,
        "old_payload_hash": old.payload_hash,
        "new_event_id": corrected.event_id, "new_reference_id": corrected.reference_id,
        "new_payload_hash": corrected.payload_hash,
        "artifact_type": artifact_type, "artifact_id": artifact_id,
        "artifact_version": artifact_version, "artifact_hash": link["artifact_hash"],
    }
    if (
        any(recovery[key] != value for key, value in expected.items())
        or old.reference_type.value != artifact_type or old.artifact_id != artifact_id
        or old.artifact_version != artifact_version or old.content_hash != link["artifact_hash"]
        or link["reference_id"] != old.reference_id
        or old_row["status"] not in ("PENDING", "FAILED_BLOCKING")
        or not recovery["reviewed_by"].strip() or not recovery["reason"].strip()
        or conn.execute("SELECT 1 FROM historical_retention_references WHERE reference_id=?", (old.reference_id,)).fetchone()
    ):
        raise RuntimeError("WAIT_RHIST03D_SUPERSESSION_PROOF_MISMATCH")
    new_row = registrar._load_verified_row(conn, corrected.event_id)
    if (
        new_row["payload_json"] != corrected.payload_json
        or new_row["payload_hash"] != corrected.payload_hash
        or new_row["reference_id"] != corrected.reference_id
    ):
        raise RuntimeError("WAIT_RHIST03D_SUPERSESSION_EVENT_MISMATCH")
    return {**link, "event_id": corrected.event_id, "reference_id": corrected.reference_id}


def supersede_rhist03d_event(
    event_id: str, *, reviewed_by: str, reason: str,
) -> dict[str, Any]:
    """Explicit recovery of a non-APPLIED pre-fix event; E1 and its link survive."""
    from .r18_history_store import _artifact_mapping, verify_stored_rhist03d_artifact

    if not reviewed_by.strip() or not reason.strip():
        raise ValueError("RHIST03D_SUPERSESSION_REVIEW_REQUIRED")
    conn = storage.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        assert_rhist03d_upgrade_safe()
        registrar = DurableRetentionRegistrar(db_path=storage.DB_PATH)
        old_row = registrar._load_verified_row(conn, event_id)
        old = _old_typed_intent(old_row)
        if old_row["status"] not in ("PENDING", "FAILED_BLOCKING"):
            raise RuntimeError("WAIT_RHIST03D_PREFIX_APPLIED_REQUIRES_REVIEW")
        kind = old.reference_type.value
        verify_stored_rhist03d_artifact(kind, old.artifact_id, old.artifact_version)
        existing = conn.execute(
            "SELECT * FROM r18_retention_supersessions WHERE old_event_id=?", (event_id,)
        ).fetchone()
        if existing is not None:
            resolve_retention_link(conn, kind, old.artifact_id, old.artifact_version)
            return dict(existing)
        link = resolve_retention_link(conn, kind, old.artifact_id, old.artifact_version)
        table, id_col, version_col, hash_col, _, _ = _artifact_mapping(kind)
        where = f"{id_col}=?" + (f" AND {version_col}=?" if version_col else "")
        params = (old.artifact_id, old.artifact_version) if version_col else (old.artifact_id,)
        artifact = conn.execute(f"SELECT * FROM {table} WHERE {where}", params).fetchone()
        if (
            link is None or link["event_id"] != event_id
            or link["reference_id"] != old.reference_id or link["artifact_hash"] != old.content_hash
            or link["publication_state"] != "PENDING_RETENTION"
            or artifact is None or artifact[hash_col] != old.content_hash
            or artifact["publication_state"] != "PENDING_RETENTION"
            or conn.execute("SELECT 1 FROM historical_retention_references WHERE reference_id=?", (old.reference_id,)).fetchone()
        ):
            raise RuntimeError("WAIT_RHIST03D_PREFIX_ARTIFACT_OR_LINK_REQUIRES_REVIEW")
        corrected = _corrected_intent(old)
        registrar.enqueue(corrected, connection=conn)
        evidence = {
            "old_event_id": old.event_id, "old_reference_id": old.reference_id,
            "old_payload_hash": old.payload_hash,
            "new_event_id": corrected.event_id, "new_reference_id": corrected.reference_id,
            "new_payload_hash": corrected.payload_hash,
            "artifact_type": kind, "artifact_id": old.artifact_id,
            "artifact_version": old.artifact_version, "artifact_hash": old.content_hash,
            "reviewed_by": reviewed_by.strip(), "reason": reason.strip(),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        conn.execute(
            "INSERT INTO r18_retention_supersessions(" + ",".join(evidence) + ") VALUES(" +
            ",".join("?" for _ in evidence) + ")", tuple(evidence.values()),
        )
        conn.commit()
        return evidence
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
    "resolve_retention_link",
    "supersede_rhist03d_event",
)
