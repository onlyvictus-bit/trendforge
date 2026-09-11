"""R-HIST-03D governed-publication proof and crash-safe finalization.

This module is deliberately downstream of immutable artifact persistence. It does
not build models, select trades, promote strategies, repair history, or create
broker/execution authority. It converts a locally valid PENDING_RETENTION R18
history artifact to APPLIED only after the exact durable outbox event, Historical
Retention Authority reference, and required historical parents are all proven.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .. import storage
from ..historical_retention import RetentionReferenceType
from ..retention_producer import (
    DurableRetentionRegistrar,
    RetentionEvidenceIntent,
    RetentionOutboxStatus,
)
from ..r16_retention import _payload_hash as r16_payload_hash
from ..r16_retention import verified_record as verified_r16_record
from .r18_history_completion import (
    assert_rhist03d_upgrade_safe as assert_completion_upgrade_safe,
    resolve_retention_link,
)
from .r18_history_store import (
    AUDIT_RETENTION_VERSION,
    verify_stored_rhist03d_artifact,
)


@dataclass(frozen=True, slots=True)
class RHist03DArtifactLocator:
    artifact_type: str
    artifact_id: str
    artifact_version: str


_ARTIFACT_TABLES: dict[str, tuple[str, str, str | None, str]] = {
    "ML_DATASET": ("ml_frozen_datasets", "dataset_id", "dataset_version", "dataset_hash"),
    "MODEL_VERSION": (
        "ml_governed_model_versions",
        "model_id",
        "model_version",
        "model_hash",
    ),
    "STRATEGY_PROFILE": (
        "strategy_profile_versions",
        "profile_id",
        "profile_version",
        "content_hash",
    ),
    "AUDIT": ("governance_audit_records", "audit_id", None, "record_hash"),
}


def _mapping(locator: RHist03DArtifactLocator) -> tuple[str, str, str | None, str]:
    if locator.artifact_type not in _ARTIFACT_TABLES:
        raise ValueError("UNSUPPORTED_RHIST03D_ARTIFACT")
    if locator.artifact_type == "AUDIT" and locator.artifact_version != AUDIT_RETENTION_VERSION:
        raise ValueError("AUDIT_RETENTION_VERSION_INVALID")
    return _ARTIFACT_TABLES[locator.artifact_type]


def _artifact_row(conn, locator: RHist03DArtifactLocator):
    table, id_col, version_col, hash_col = _mapping(locator)
    if version_col is None:
        return conn.execute(
            f"SELECT *,{hash_col} AS semantic_hash FROM {table} WHERE {id_col}=?",
            (locator.artifact_id,),
        ).fetchone()
    return conn.execute(
        f"SELECT *,{hash_col} AS semantic_hash FROM {table} "
        f"WHERE {id_col}=? AND {version_col}=?",
        (locator.artifact_id, locator.artifact_version),
    ).fetchone()


def rhist03d_preflight_inventory() -> dict[str, Any]:
    """Read-only upgrade inventory. Never repairs, rewrites, or supersedes rows."""
    storage.init_db()
    result: dict[str, Any] = {
        "artifacts": {},
        "links": {},
        "outbox": {},
        "references": {},
        "preFixAppliedTypedEvents": 0,
        "stopRequired": False,
    }
    with storage.connect() as conn:
        names = {
            str(row["name"])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for artifact_type, (table, _, _, _) in _ARTIFACT_TABLES.items():
            if table not in names:
                result["artifacts"][artifact_type] = {}
                continue
            rows = conn.execute(
                f"SELECT publication_state,COUNT(*) AS n FROM {table} "
                "GROUP BY publication_state ORDER BY publication_state"
            ).fetchall()
            result["artifacts"][artifact_type] = {
                str(row["publication_state"]): int(row["n"]) for row in rows
            }

        if "r18_retention_links" in names:
            rows = conn.execute(
                "SELECT publication_state,COUNT(*) AS n FROM r18_retention_links "
                "GROUP BY publication_state ORDER BY publication_state"
            ).fetchall()
            result["links"] = {
                str(row["publication_state"]): int(row["n"]) for row in rows
            }

        if "historical_retention_outbox" in names:
            columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(historical_retention_outbox)")
            }
            rows = conn.execute(
                "SELECT status,COUNT(*) AS n FROM historical_retention_outbox "
                "WHERE artifact_type LIKE 'R18_%' GROUP BY status ORDER BY status"
            ).fetchall()
            result["outbox"] = {str(row["status"]): int(row["n"]) for row in rows}
            if "artifact_hash" in columns:
                old_applied = conn.execute(
                    "SELECT COUNT(*) AS n FROM historical_retention_outbox "
                    "WHERE artifact_type IN "
                    "('R18_ML_DATASET','R18_MODEL_VERSION','R18_STRATEGY_PROFILE','R18_AUDIT') "
                    "AND status='APPLIED' AND artifact_hash IS NULL AND content_hash IS NOT NULL"
                ).fetchone()
                result["preFixAppliedTypedEvents"] = int(old_applied["n"])
            else:
                old_applied = conn.execute(
                    "SELECT COUNT(*) AS n FROM historical_retention_outbox "
                    "WHERE artifact_type IN "
                    "('R18_ML_DATASET','R18_MODEL_VERSION','R18_STRATEGY_PROFILE','R18_AUDIT') "
                    "AND status='APPLIED' AND content_hash IS NOT NULL"
                ).fetchone()
                result["preFixAppliedTypedEvents"] = int(old_applied["n"])

        if "historical_retention_references" in names:
            rows = conn.execute(
                "SELECT reference_type,COUNT(*) AS n FROM historical_retention_references "
                "WHERE reference_type IN ('ML_DATASET','MODEL_VERSION','STRATEGY_PROFILE','AUDIT') "
                "GROUP BY reference_type ORDER BY reference_type"
            ).fetchall()
            result["references"] = {
                str(row["reference_type"]): int(row["n"]) for row in rows
            }

    result["stopRequired"] = bool(result["preFixAppliedTypedEvents"])
    return result


def assert_rhist03d_upgrade_safe() -> dict[str, Any]:
    return assert_completion_upgrade_safe()


def _verify_dataset_r16_parents(payload: dict[str, Any]) -> None:
    """Prove exact R16 record hashes and their retained S8/market ancestors."""
    with storage.connect() as conn:
        for member in payload.get("members", ()):
            _, decision, decision_publication = verified_r16_record(
                conn,
                "DECISION_VERSION",
                str(member["decisionVersionId"]),
            )
            if r16_payload_hash(decision) != member["decisionVersionHash"]:
                raise RuntimeError("WAIT_RHIST03D_DECISION_PARENT_HASH_MISMATCH")

            required_market_hashes = {
                str(root["contentHash"])
                for root in member.get("evidenceRoots", ())
                if root.get("contentHash")
            }
            proven_market_hashes = {
                str(root.content_hash)
                for root in decision_publication.evidence_roots
                if root.content_hash
            }

            outcome_id = member.get("outcomeId")
            if outcome_id:
                _, outcome, outcome_publication = verified_r16_record(
                    conn,
                    "OUTCOME",
                    str(outcome_id),
                )
                if r16_payload_hash(outcome) != member.get("outcomeHash"):
                    raise RuntimeError("WAIT_RHIST03D_OUTCOME_PARENT_HASH_MISMATCH")
                proven_market_hashes.update(
                    str(root.content_hash)
                    for root in outcome_publication.evidence_roots
                    if root.content_hash
                )

            revision_id = member.get("revisionId")
            if revision_id:
                _, revision, revision_publication = verified_r16_record(
                    conn,
                    "REVISION",
                    str(revision_id),
                )
                if r16_payload_hash(revision) != member.get("revisionHash"):
                    raise RuntimeError("WAIT_RHIST03D_REVISION_PARENT_HASH_MISMATCH")
                proven_market_hashes.update(
                    str(root.content_hash)
                    for root in revision_publication.evidence_roots
                    if root.content_hash
                )

            if not required_market_hashes.issubset(proven_market_hashes):
                raise RuntimeError("WAIT_RHIST03D_MEMBER_EVIDENCE_NOT_IN_R16_LINEAGE")


def _verify_model_parents(payload: dict[str, Any]) -> None:
    required: list[tuple[str, str, str]] = [
        (
            str(payload["trainingDatasetId"]),
            str(payload["trainingDatasetVersion"]),
            str(payload["trainingDatasetHash"]),
        ),
        (
            str(payload["evaluationDatasetId"]),
            str(payload["evaluationDatasetVersion"]),
            str(payload["evaluationDatasetHash"]),
        ),
    ]
    if payload.get("holdoutDatasetId"):
        required.append(
            (
                str(payload["holdoutDatasetId"]),
                str(payload["holdoutDatasetVersion"]),
                str(payload["holdoutDatasetHash"]),
            )
        )
    for dataset_id, dataset_version, dataset_hash in required:
        parent = verify_governed_rhist03d_artifact(
            "ML_DATASET", dataset_id, dataset_version, verify_parents=True
        )
        if parent.get("datasetHash") != dataset_hash:
            raise RuntimeError("WAIT_RHIST03D_MODEL_DATASET_HASH_MISMATCH")


def _verify_profile_parents(payload: dict[str, Any]) -> None:
    if payload.get("modelId") is None:
        return
    parent = verify_governed_rhist03d_artifact(
        "MODEL_VERSION",
        str(payload["modelId"]),
        str(payload["modelVersion"]),
        verify_parents=True,
    )
    if parent.get("modelHash") != payload.get("modelHash"):
        raise RuntimeError("WAIT_RHIST03D_PROFILE_MODEL_HASH_MISMATCH")


def _verify_audit_parent(payload: dict[str, Any]) -> None:
    reviewed_type = str(payload["reviewedArtifactType"])
    if reviewed_type not in _ARTIFACT_TABLES:
        raise RuntimeError("WAIT_RHIST03D_AUDIT_ARTIFACT_TYPE_UNSUPPORTED")
    parent = verify_governed_rhist03d_artifact(
        reviewed_type,
        str(payload["artifactId"]),
        str(payload["artifactVersion"]),
        verify_parents=True,
    )
    semantic_keys = {
        "ML_DATASET": "datasetHash",
        "MODEL_VERSION": "modelHash",
        "STRATEGY_PROFILE": "contentHash",
        "AUDIT": "recordHash",
    }
    if parent.get(semantic_keys[reviewed_type]) != payload.get("artifactHash"):
        raise RuntimeError("WAIT_RHIST03D_AUDIT_REVIEWED_HASH_MISMATCH")


def _verify_parents(artifact_type: str, payload: dict[str, Any]) -> None:
    if artifact_type == "ML_DATASET":
        _verify_dataset_r16_parents(payload)
    elif artifact_type == "MODEL_VERSION":
        _verify_model_parents(payload)
    elif artifact_type == "STRATEGY_PROFILE":
        _verify_profile_parents(payload)
    elif artifact_type == "AUDIT":
        _verify_audit_parent(payload)


def _verify_retention_proof(locator: RHist03DArtifactLocator, semantic_hash: str) -> None:
    with storage.connect() as conn:
        link = resolve_retention_link(
            conn, locator.artifact_type, locator.artifact_id, locator.artifact_version
        )
        if link is None or link["artifact_hash"] != semantic_hash:
            raise RuntimeError("WAIT_RHIST03D_RETENTION_LINK_MISSING_OR_MISMATCH")
        event = conn.execute(
            "SELECT * FROM historical_retention_outbox WHERE event_id=?",
            (link["event_id"],),
        ).fetchone()
        if event is None or event["status"] != RetentionOutboxStatus.APPLIED.value:
            raise RuntimeError("WAIT_RHIST03D_RETENTION_OUTBOX_NOT_APPLIED")
        intent = RetentionEvidenceIntent(
            artifact_type=f"R18_{locator.artifact_type}",
            artifact_id=locator.artifact_id,
            artifact_version=locator.artifact_version,
            reference_type=RetentionReferenceType(locator.artifact_type),
            artifact_hash=semantic_hash,
            created_at=datetime.fromisoformat(str(event["created_at"])),
        )
        if (
            event["event_id"] != intent.event_id
            or link["reference_id"] != intent.reference_id
            or event["reference_id"] != intent.reference_id
            or event["payload_json"] != intent.payload_json
            or event["payload_hash"] != intent.payload_hash
            or event["artifact_hash"] != semantic_hash
            or event["content_hash"] is not None
        ):
            raise RuntimeError("WAIT_RHIST03D_RETENTION_OUTBOX_PROOF_MISMATCH")
        reference = conn.execute(
            "SELECT * FROM historical_retention_references WHERE reference_id=?",
            (link["reference_id"],),
        ).fetchone()
        if (
            reference is None
            or reference["reference_type"] != locator.artifact_type
            or reference["artifact_id"] != locator.artifact_id
            or reference["artifact_version"] != locator.artifact_version
            or reference["artifact_hash"] != semantic_hash
            or reference["content_hash"] is not None
            or not reference["permanent"]
            or reference["retain_until"] is not None
        ):
            raise RuntimeError("WAIT_RHIST03D_AUTHORITY_PROOF_MISMATCH")


def verify_governed_rhist03d_artifact(
    artifact_type: str,
    artifact_id: str,
    artifact_version: str,
    *,
    verify_parents: bool = True,
) -> dict[str, Any]:
    locator = RHist03DArtifactLocator(artifact_type, artifact_id, artifact_version)
    payload = verify_stored_rhist03d_artifact(
        artifact_type, artifact_id, artifact_version
    )
    with storage.connect() as conn:
        row = _artifact_row(conn, locator)
        link = resolve_retention_link(conn, artifact_type, artifact_id, artifact_version)
    if row is None or row["publication_state"] != "APPLIED":
        raise RuntimeError("WAIT_RHIST03D_ARTIFACT_NOT_APPLIED")
    if link is None or link["publication_state"] != "APPLIED":
        raise RuntimeError("WAIT_RHIST03D_LINK_NOT_APPLIED")
    semantic_hash = str(row["semantic_hash"])
    _verify_retention_proof(locator, semantic_hash)
    if verify_parents:
        _verify_parents(artifact_type, payload)
    return payload


def finalize_rhist03d_artifact(
    artifact_type: str,
    artifact_id: str,
    artifact_version: str,
    *,
    fault_point: str | None = None,
    verify_parents: bool = True,
) -> dict[str, Any]:
    """Finalize one artifact. Replay is idempotent; reads never call this function."""
    assert_rhist03d_upgrade_safe()
    locator = RHist03DArtifactLocator(artifact_type, artifact_id, artifact_version)
    payload = verify_stored_rhist03d_artifact(
        artifact_type, artifact_id, artifact_version
    )
    with storage.connect() as conn:
        row = _artifact_row(conn, locator)
        link = resolve_retention_link(conn, artifact_type, artifact_id, artifact_version)
    if row is None or link is None:
        raise RuntimeError("WAIT_RHIST03D_ARTIFACT_OR_LINK_MISSING")
    semantic_hash = str(row["semantic_hash"])
    if link["artifact_hash"] != semantic_hash:
        raise RuntimeError("WAIT_RHIST03D_RETENTION_LINK_HASH_MISMATCH")

    if row["publication_state"] == "APPLIED" or link["publication_state"] == "APPLIED":
        if row["publication_state"] != "APPLIED" or link["publication_state"] != "APPLIED":
            raise RuntimeError("WAIT_RHIST03D_SPLIT_PUBLICATION_STATE")
        return verify_governed_rhist03d_artifact(
            artifact_type,
            artifact_id,
            artifact_version,
            verify_parents=verify_parents,
        )

    if fault_point == "BEFORE_DISPATCH":
        raise RuntimeError("INJECTED_BEFORE_DISPATCH")
    registrar = DurableRetentionRegistrar(db_path=storage.DB_PATH)
    receipt = registrar.dispatch(
        str(link["event_id"]), fault_point=fault_point
    )
    if receipt.status is not RetentionOutboxStatus.APPLIED:
        raise RuntimeError("WAIT_RHIST03D_RETENTION_DISPATCH_BLOCKED")
    if fault_point == "AFTER_OUTBOX_APPLIED":
        raise RuntimeError("INJECTED_AFTER_OUTBOX_APPLIED")

    _verify_retention_proof(locator, semantic_hash)
    if verify_parents:
        _verify_parents(artifact_type, payload)
    if fault_point == "AFTER_PARENT_PROOF":
        raise RuntimeError("INJECTED_AFTER_PARENT_PROOF")

    table, id_col, version_col, _ = _mapping(locator)
    conn = storage.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        current_row = _artifact_row(conn, locator)
        current_link = resolve_retention_link(conn, artifact_type, artifact_id, artifact_version)
        if current_row is None or current_link is None:
            raise RuntimeError("WAIT_RHIST03D_ARTIFACT_OR_LINK_MISSING")
        if current_row["publication_state"] != current_link["publication_state"]:
            raise RuntimeError("WAIT_RHIST03D_SPLIT_PUBLICATION_STATE")
        if current_row["semantic_hash"] != semantic_hash or current_link["artifact_hash"] != semantic_hash:
            raise RuntimeError("WAIT_RHIST03D_FINALIZE_CAS_MISMATCH")
        # Another finalizer may have committed while this caller proved parents.
        # Re-read under the writer lock and accept only the exact complete pair.
        if current_row["publication_state"] != "APPLIED":
            updated_link = conn.execute(
                "UPDATE r18_retention_links SET publication_state='APPLIED' "
                "WHERE artifact_type=? AND artifact_id=? AND artifact_version=? "
                "AND artifact_hash=? AND publication_state='PENDING_RETENTION'",
                (artifact_type, artifact_id, artifact_version, semantic_hash),
            ).rowcount
            if fault_point == "AFTER_LINK_APPLIED":
                raise RuntimeError("INJECTED_AFTER_LINK_APPLIED")
            if version_col is None:
                updated_artifact = conn.execute(
                    f"UPDATE {table} SET publication_state='APPLIED' "
                    f"WHERE {id_col}=? AND publication_state='PENDING_RETENTION'",
                    (artifact_id,),
                ).rowcount
            else:
                updated_artifact = conn.execute(
                    f"UPDATE {table} SET publication_state='APPLIED' "
                    f"WHERE {id_col}=? AND {version_col}=? "
                    "AND publication_state='PENDING_RETENTION'",
                    (artifact_id, artifact_version),
                ).rowcount
            if updated_artifact != 1 or updated_link != 1:
                raise RuntimeError("WAIT_RHIST03D_FINALIZE_CAS_MISMATCH")
        if fault_point == "BEFORE_LOCAL_COMMIT":
            raise RuntimeError("INJECTED_BEFORE_LOCAL_COMMIT")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return verify_governed_rhist03d_artifact(
        artifact_type,
        artifact_id,
        artifact_version,
        verify_parents=verify_parents,
    )


__all__ = [
    "assert_rhist03d_upgrade_safe",
    "finalize_rhist03d_artifact",
    "rhist03d_preflight_inventory",
    "verify_governed_rhist03d_artifact",
]
