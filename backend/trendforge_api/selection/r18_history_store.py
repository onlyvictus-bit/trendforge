"""Additive R-HIST-03D persistence owned by the canonical R18 store."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from .. import storage
from ..historical_retention import RetentionReferenceType
from ..retention_producer import DurableRetentionRegistrar, RetentionEvidenceIntent
from .r18_history import (
    FrozenDatasetManifestV1,
    GovernanceAuditRecordV1,
    GovernedModelVersionV1,
    StrategyProfileVersionV1,
)

MIGRATION_VERSION = "0015_rhist03d_learning_history"
TABLES = (
    "ml_frozen_datasets",
    "ml_frozen_dataset_members",
    "ml_governed_model_versions",
    "strategy_profile_versions",
    "governance_audit_records",
    "r18_retention_links",
)


def schema_status() -> dict[str, Any]:
    storage.init_db()
    with storage.connect() as conn:
        names = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        migration = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version=?",
            (MIGRATION_VERSION,),
        ).fetchone()
    present = tuple(name for name in TABLES if name in names)
    return {
        "migrationVersion": MIGRATION_VERSION,
        "applied": bool(migration) and len(present) == len(TABLES),
        "tables": present,
        "missingTables": tuple(name for name in TABLES if name not in names),
    }


def apply_schema() -> dict[str, Any]:
    """Apply 03D explicitly; ordinary storage initialization never calls this."""
    storage.init_db()
    conn = storage.connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ml_frozen_datasets (
                record_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                dataset_version TEXT NOT NULL,
                dataset_hash TEXT NOT NULL,
                member_manifest_hash TEXT,
                decision_cutoff TEXT,
                label_cutoff TEXT,
                build_cutoff TEXT,
                member_count INTEGER,
                publication_state TEXT NOT NULL DEFAULT 'LEGACY_UNGOVERNED',
                payload_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(dataset_id,dataset_version),
                UNIQUE(dataset_hash)
            );
            CREATE TABLE IF NOT EXISTS ml_frozen_dataset_members (
                member_id TEXT PRIMARY KEY,
                dataset_record_id TEXT NOT NULL,
                member_hash TEXT NOT NULL,
                instrument_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL,
                profile_id TEXT NOT NULL,
                profile_version TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                horizon TEXT NOT NULL,
                direction TEXT NOT NULL,
                decision_version_id TEXT NOT NULL,
                decision_version_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                FOREIGN KEY(dataset_record_id) REFERENCES ml_frozen_datasets(record_id),
                UNIQUE(dataset_record_id,member_hash)
            );
            CREATE TABLE IF NOT EXISTS ml_governed_model_versions (
                record_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                model_hash TEXT NOT NULL UNIQUE,
                training_dataset_id TEXT NOT NULL,
                training_dataset_hash TEXT NOT NULL,
                evaluation_dataset_id TEXT NOT NULL,
                evaluation_dataset_hash TEXT NOT NULL,
                model_artifact_hash TEXT NOT NULL,
                publication_state TEXT NOT NULL DEFAULT 'LEGACY_UNGOVERNED',
                payload_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(model_id,model_version)
            );
            CREATE TABLE IF NOT EXISTS strategy_profile_versions (
                record_id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                profile_version TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                model_id TEXT,
                model_version TEXT,
                model_hash TEXT,
                publication_state TEXT NOT NULL DEFAULT 'LEGACY_UNGOVERNED',
                payload_json TEXT NOT NULL,
                stored_content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(profile_id,profile_version)
            );
            CREATE TABLE IF NOT EXISTS governance_audit_records (
                record_id TEXT PRIMARY KEY,
                audit_id TEXT NOT NULL UNIQUE,
                artifact_type TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                artifact_version TEXT NOT NULL,
                artifact_hash TEXT NOT NULL,
                predecessor_audit_hash TEXT,
                record_hash TEXT NOT NULL UNIQUE,
                decision TEXT NOT NULL,
                publication_state TEXT NOT NULL DEFAULT 'LEGACY_UNGOVERNED',
                payload_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS r18_retention_links (
                artifact_type TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                artifact_version TEXT NOT NULL,
                artifact_hash TEXT NOT NULL,
                event_id TEXT NOT NULL,
                reference_id TEXT NOT NULL,
                publication_state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(artifact_type,artifact_id,artifact_version)
            );
            """
        )
        DurableRetentionRegistrar(db_path=storage.DB_PATH).initialize_schema(conn)
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version,description,applied_at) "
            "VALUES(?,?,?)",
            (
                MIGRATION_VERSION,
                "R-HIST-03D frozen dataset/model/profile/audit history",
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return schema_status()


def _require_schema() -> None:
    if not schema_status()["applied"]:
        raise RuntimeError("WAIT_RHIST03D_SCHEMA_NOT_APPLIED")


def _encode(model: Any) -> tuple[str, str]:
    payload = model.model_dump(mode="json", by_alias=True)
    encoded = storage.encode_json(payload)
    return encoded, hashlib.sha256(encoded.encode()).hexdigest()


def _stage_retention(
    conn,
    *,
    artifact_type: str,
    artifact_id: str,
    artifact_version: str,
    artifact_hash: str,
    created_at: datetime,
) -> tuple[str, str]:
    """Stage one deterministic canonical intent in the caller-owned transaction."""
    intent = RetentionEvidenceIntent(
        artifact_type=f"R18_{artifact_type}",
        artifact_id=artifact_id,
        artifact_version=artifact_version,
        reference_type=RetentionReferenceType(artifact_type),
        content_hash=artifact_hash,
        created_at=created_at,
    )
    receipt = DurableRetentionRegistrar(db_path=storage.DB_PATH).enqueue(
        intent, connection=conn
    )
    now = created_at.astimezone(UTC).isoformat()
    existing = conn.execute(
        "SELECT artifact_hash,event_id,reference_id FROM r18_retention_links "
        "WHERE artifact_type=? AND artifact_id=? AND artifact_version=?",
        (artifact_type, artifact_id, artifact_version),
    ).fetchone()
    if existing is not None:
        if (
            existing["artifact_hash"] != artifact_hash
            or existing["event_id"] != receipt.event_id
            or existing["reference_id"] != receipt.reference_id
        ):
            raise ValueError("R18_RETENTION_LINK_IMMUTABLE")
    else:
        conn.execute(
            "INSERT INTO r18_retention_links(artifact_type,artifact_id,artifact_version,"
            "artifact_hash,event_id,reference_id,publication_state,created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (
                artifact_type,
                artifact_id,
                artifact_version,
                artifact_hash,
                receipt.event_id,
                receipt.reference_id,
                "PENDING_RETENTION",
                now,
            ),
        )
    return receipt.event_id, receipt.reference_id


def persist_frozen_dataset(
    model: FrozenDatasetManifestV1, *, fault_point: str | None = None
) -> dict[str, Any]:
    _require_schema()
    encoded, content_hash = _encode(model)
    record_id = f"{model.dataset_id}:{model.dataset_version}"
    conn = storage.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT payload_json FROM ml_frozen_datasets WHERE record_id=?", (record_id,)
        ).fetchone()
        if existing:
            if existing["payload_json"] != encoded:
                raise ValueError("DATASET_VERSION_IMMUTABLE")
            conn.rollback()
            return {"stored": False, "publicationStatus": "PENDING_RETENTION"}
        conn.execute(
            "INSERT INTO ml_frozen_datasets(record_id,dataset_id,dataset_version,"
            "dataset_hash,member_manifest_hash,decision_cutoff,label_cutoff,build_cutoff,"
            "member_count,publication_state,payload_json,content_hash,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                record_id,
                model.dataset_id,
                model.dataset_version,
                model.dataset_hash,
                model.member_manifest_hash,
                model.decision_cutoff.isoformat(),
                model.label_cutoff.isoformat(),
                model.build_cutoff.isoformat(),
                model.member_count,
                "PENDING_RETENTION",
                encoded,
                content_hash,
                model.created_at.isoformat(),
            ),
        )
        if fault_point == "AFTER_ARTIFACT_INSERT":
            raise RuntimeError("INJECTED_AFTER_ARTIFACT_INSERT")
        for member in model.members:
            member_json = storage.encode_json(
                member.model_dump(mode="json", by_alias=True)
            )
            member_content = hashlib.sha256(member_json.encode()).hexdigest()
            conn.execute(
                "INSERT INTO ml_frozen_dataset_members(member_id,dataset_record_id,"
                "member_hash,instrument_id,opportunity_id,profile_id,profile_version,"
                "timeframe,horizon,direction,decision_version_id,decision_version_hash,"
                "payload_json,content_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    member.member_id,
                    record_id,
                    member.member_hash,
                    member.instrument_id,
                    member.opportunity_id,
                    member.profile_id,
                    member.profile_version,
                    member.timeframe,
                    member.horizon,
                    member.direction,
                    member.decision_version_id,
                    member.decision_version_hash,
                    member_json,
                    member_content,
                ),
            )
        _stage_retention(
            conn,
            artifact_type="ML_DATASET",
            artifact_id=model.dataset_id,
            artifact_version=model.dataset_version,
            artifact_hash=model.dataset_hash,
            created_at=model.created_at,
        )
        conn.commit()
        return {"stored": True, "publicationStatus": "PENDING_RETENTION"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def persist_strategy_profile(model: StrategyProfileVersionV1) -> bool:
    _require_schema()
    encoded, stored_hash = _encode(model)
    record_id = f"{model.profile_id}:{model.profile_version}"
    conn = storage.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT content_hash,payload_json FROM strategy_profile_versions "
            "WHERE record_id=?",
            (record_id,),
        ).fetchone()
        if existing:
            if (
                existing["content_hash"] != model.content_hash
                or existing["payload_json"] != encoded
            ):
                raise ValueError("PROFILE_VERSION_IMMUTABLE")
            conn.rollback()
            return False
        conn.execute(
            "INSERT INTO strategy_profile_versions(record_id,profile_id,profile_version,"
            "content_hash,model_id,model_version,model_hash,publication_state,payload_json,"
            "stored_content_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                record_id,
                model.profile_id,
                model.profile_version,
                model.content_hash,
                model.model_id,
                model.model_version,
                model.model_hash,
                "PENDING_RETENTION",
                encoded,
                stored_hash,
                model.created_at.isoformat(),
            ),
        )
        _stage_retention(
            conn,
            artifact_type="STRATEGY_PROFILE",
            artifact_id=model.profile_id,
            artifact_version=model.profile_version,
            artifact_hash=model.content_hash,
            created_at=model.created_at,
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def persist_governed_model(model: GovernedModelVersionV1) -> bool:
    _require_schema()
    encoded, stored_hash = _encode(model)
    record_id = f"{model.model_id}:{model.model_version}"
    conn = storage.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        for dataset_id, dataset_hash in (
            (model.training_dataset_id, model.training_dataset_hash),
            (model.evaluation_dataset_id, model.evaluation_dataset_hash),
        ):
            row = conn.execute(
                "SELECT dataset_hash FROM ml_frozen_datasets "
                "WHERE dataset_id=? AND dataset_hash=?",
                (dataset_id, dataset_hash),
            ).fetchone()
            if not row:
                raise ValueError("MODEL_DATASET_BINDING_UNPROVEN")
        existing = conn.execute(
            "SELECT payload_json FROM ml_governed_model_versions WHERE record_id=?",
            (record_id,),
        ).fetchone()
        if existing:
            if existing["payload_json"] != encoded:
                raise ValueError("MODEL_VERSION_IMMUTABLE")
            conn.rollback()
            return False
        conn.execute(
            "INSERT INTO ml_governed_model_versions(record_id,model_id,model_version,"
            "model_hash,training_dataset_id,training_dataset_hash,evaluation_dataset_id,"
            "evaluation_dataset_hash,model_artifact_hash,publication_state,payload_json,"
            "content_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                record_id,
                model.model_id,
                model.model_version,
                model.model_hash,
                model.training_dataset_id,
                model.training_dataset_hash,
                model.evaluation_dataset_id,
                model.evaluation_dataset_hash,
                model.model_artifact_hash,
                "PENDING_RETENTION",
                encoded,
                stored_hash,
                model.created_at.isoformat(),
            ),
        )
        _stage_retention(
            conn,
            artifact_type="MODEL_VERSION",
            artifact_id=model.model_id,
            artifact_version=model.model_version,
            artifact_hash=model.model_hash,
            created_at=model.created_at,
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def persist_audit_record(model: GovernanceAuditRecordV1) -> bool:
    _require_schema()
    encoded, stored_hash = _encode(model)
    conn = storage.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        latest = conn.execute(
            "SELECT record_hash FROM governance_audit_records WHERE artifact_type=? "
            "AND artifact_id=? AND artifact_version=? "
            "ORDER BY created_at DESC,audit_id DESC LIMIT 1",
            (
                model.reviewed_artifact_type,
                model.artifact_id,
                model.artifact_version,
            ),
        ).fetchone()
        expected = latest["record_hash"] if latest else None
        if model.predecessor_audit_hash != expected:
            raise ValueError("AUDIT_PREDECESSOR_MISMATCH")
        existing = conn.execute(
            "SELECT payload_json FROM governance_audit_records WHERE audit_id=?",
            (model.audit_id,),
        ).fetchone()
        if existing:
            if existing["payload_json"] != encoded:
                raise ValueError("AUDIT_RECORD_IMMUTABLE")
            conn.rollback()
            return False
        conn.execute(
            "INSERT INTO governance_audit_records(record_id,audit_id,artifact_type,"
            "artifact_id,artifact_version,artifact_hash,predecessor_audit_hash,record_hash,"
            "decision,publication_state,payload_json,content_hash,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                model.audit_id,
                model.audit_id,
                model.reviewed_artifact_type,
                model.artifact_id,
                model.artifact_version,
                model.artifact_hash,
                model.predecessor_audit_hash,
                model.record_hash,
                model.decision,
                "PENDING_RETENTION",
                encoded,
                stored_hash,
                model.reviewed_at.isoformat(),
            ),
        )
        _stage_retention(
            conn,
            artifact_type="AUDIT",
            artifact_id=model.audit_id,
            artifact_version="1",
            artifact_hash=model.record_hash,
            created_at=model.reviewed_at,
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_governed_frozen_dataset(
    dataset_id: str, dataset_version: str
) -> dict[str, Any] | None:
    if not schema_status()["applied"]:
        return None
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT payload_json,publication_state FROM ml_frozen_datasets "
            "WHERE dataset_id=? AND dataset_version=?",
            (dataset_id, dataset_version),
        ).fetchone()
    if not row or row["publication_state"] != "APPLIED":
        return None
    return json.loads(row["payload_json"])


def verify_stored_rhist03d_artifact(
    artifact_type: str, artifact_id: str, artifact_version: str
) -> dict[str, Any]:
    _require_schema()
    mapping = {
        "ML_DATASET": (
            "ml_frozen_datasets",
            "dataset_id",
            "dataset_version",
            "dataset_hash",
            "content_hash",
        ),
        "MODEL_VERSION": (
            "ml_governed_model_versions",
            "model_id",
            "model_version",
            "model_hash",
            "content_hash",
        ),
        "STRATEGY_PROFILE": (
            "strategy_profile_versions",
            "profile_id",
            "profile_version",
            "content_hash",
            "stored_content_hash",
        ),
    }
    if artifact_type not in mapping:
        raise ValueError("UNSUPPORTED_RHIST03D_ARTIFACT")
    table, id_col, version_col, hash_col, stored_hash_col = mapping[artifact_type]
    with storage.connect() as conn:
        row = conn.execute(
            f"SELECT payload_json,{stored_hash_col},{hash_col} FROM {table} "
            f"WHERE {id_col}=? AND {version_col}=?",
            (artifact_id, artifact_version),
        ).fetchone()
    if not row:
        raise ValueError("ARTIFACT_MISSING")
    actual_content = hashlib.sha256(row["payload_json"].encode()).hexdigest()
    if actual_content != row[stored_hash_col]:
        raise ValueError("CORRUPT_CONTENT_HASH")
    try:
        payload = json.loads(row["payload_json"])
    except json.JSONDecodeError as exc:
        raise ValueError("CORRUPT_PAYLOAD_JSON") from exc
    declared = (
        payload.get("datasetHash")
        or payload.get("modelHash")
        or payload.get("contentHash")
    )
    if declared != row[hash_col]:
        raise ValueError("CORRUPT_INDEXED_HASH")
    return payload
