"""Explicit, append-only SQLite persistence for R18 governance artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from .. import storage
from . import r18_history_completion as _completion
from .r18_history_finalization import (
    finalize_rhist03d_artifact as _base_finalize_rhist03d_artifact,
    verify_governed_rhist03d_artifact as _base_verify_governed_rhist03d_artifact,
)
from .r18_history_store import (
    apply_schema as _apply_rhist03d_schema,
    persist_audit_record,
    persist_frozen_dataset,
    persist_governed_model,
    persist_strategy_profile,
    schema_status as _rhist03d_schema_status,
    verify_stored_rhist03d_artifact,
)


def apply_rhist03d_schema() -> dict[str, Any]:
    result = _apply_rhist03d_schema()
    _completion.install_rhist03d_db_guards()
    return {**result, "dbImmutabilityGuards": True}


def rhist03d_schema_status() -> dict[str, Any]:
    result = _rhist03d_schema_status()
    with storage.connect() as conn:
        triggers = {
            str(row["name"])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'rhist03d_guard_%'"
            )
        }
    return {**result, "dbImmutabilityGuards": bool(triggers)}


def rhist03d_preflight_inventory() -> dict[str, Any]:
    return _completion.rhist03d_upgrade_inventory()


def assert_rhist03d_upgrade_safe() -> dict[str, Any]:
    return _completion.assert_rhist03d_upgrade_safe()


def verify_governed_rhist03d_artifact(
    artifact_type: str,
    artifact_id: str,
    artifact_version: str,
    *,
    verify_parents: bool = True,
) -> dict[str, Any]:
    payload = _base_verify_governed_rhist03d_artifact(
        artifact_type,
        artifact_id,
        artifact_version,
        verify_parents=verify_parents,
    )
    if verify_parents and artifact_type == "ML_DATASET":
        _completion.verify_dataset_r16_parents(payload)
    return payload


def finalize_rhist03d_artifact(
    artifact_type: str,
    artifact_id: str,
    artifact_version: str,
    *,
    fault_point: str | None = None,
    verify_parents: bool = True,
) -> dict[str, Any]:
    """Finalize only after the strengthened 03D preflight/PIT proof succeeds."""
    assert_rhist03d_upgrade_safe()
    if verify_parents and artifact_type == "ML_DATASET":
        payload = verify_stored_rhist03d_artifact(
            artifact_type, artifact_id, artifact_version
        )
        _completion.verify_dataset_r16_parents(payload)
    return _base_finalize_rhist03d_artifact(
        artifact_type,
        artifact_id,
        artifact_version,
        fault_point=fault_point,
        verify_parents=verify_parents,
    )


def rhist03d_integrity_status() -> dict[str, Any]:
    return _completion.rhist03d_integrity_status()


__all__ = (
    "apply_rhist03d_schema",
    "assert_rhist03d_upgrade_safe",
    "finalize_rhist03d_artifact",
    "persist_audit_record",
    "persist_frozen_dataset",
    "persist_governed_model",
    "persist_strategy_profile",
    "rhist03d_integrity_status",
    "rhist03d_preflight_inventory",
    "rhist03d_schema_status",
    "verify_governed_rhist03d_artifact",
    "verify_stored_rhist03d_artifact",
)

MIGRATION_VERSION = "0014_r18_model_governance"
TABLES = (
    "ml_model_registry",
    "ml_evaluation_reports",
    "ml_promotion_reviews",
    "ml_drift_events",
)


def get_governed_frozen_dataset(
    dataset_id: str, dataset_version: str
) -> dict[str, Any] | None:
    """Pure fail-closed governed read; never repairs or backfills history."""
    try:
        return verify_governed_rhist03d_artifact(
            "ML_DATASET", dataset_id, dataset_version, verify_parents=True
        )
    except (RuntimeError, ValueError, KeyError):
        return None


def schema_status() -> dict[str, Any]:
    storage.init_db()
    conn = storage.connect()
    try:
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
    finally:
        conn.close()
    present = tuple(name for name in TABLES if name in names)
    return {
        "migrationVersion": MIGRATION_VERSION,
        "applied": bool(migration) and len(present) == len(TABLES),
        "tables": present,
        "missingTables": tuple(name for name in TABLES if name not in names),
    }


def apply_schema() -> dict[str, Any]:
    storage.init_db()
    conn = storage.connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ml_model_registry (
                record_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                model_hash TEXT NOT NULL,
                state TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ml_model_registry_model_created
            ON ml_model_registry(model_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS ml_evaluation_reports (
                record_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                model_hash TEXT NOT NULL,
                dataset_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ml_evaluations_model_created
            ON ml_evaluation_reports(model_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS ml_promotion_reviews (
                record_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                model_hash TEXT NOT NULL,
                decision TEXT NOT NULL,
                record_hash TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ml_reviews_model_created
            ON ml_promotion_reviews(model_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS ml_drift_events (
                record_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                model_hash TEXT NOT NULL,
                resulting_state TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ml_drift_model_created
            ON ml_drift_events(model_id, created_at DESC);
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations"
            "(version, description, applied_at) VALUES (?, ?, ?)",
            (
                MIGRATION_VERSION,
                "R18 append-only model governance",
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return schema_status()


def _persist(
    table: str,
    record_id: str,
    payload: dict[str, Any],
    columns: tuple[str, ...],
    values: tuple[Any, ...],
) -> bool:
    if table not in TABLES or not schema_status()["applied"]:
        raise RuntimeError("WAIT_R18_SCHEMA_NOT_APPLIED")
    encoded = storage.encode_json(payload)
    content_hash = hashlib.sha256(encoded.encode()).hexdigest()
    conn = storage.connect()
    try:
        existing = conn.execute(
            f"SELECT payload_json FROM {table} WHERE record_id=?",
            (record_id,),
        ).fetchone()
        if existing:
            if existing["payload_json"] != encoded:
                raise ValueError("R18_ARTIFACT_IMMUTABLE")
            return False
        names = ("record_id",) + columns + (
            "payload_json",
            "content_hash",
            "created_at",
        )
        marks = ",".join("?" for _ in names)
        conn.execute(
            f"INSERT INTO {table} ({','.join(names)}) VALUES ({marks})",
            (record_id,)
            + values
            + (encoded, content_hash, datetime.now(UTC).isoformat()),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def persist_manifest(payload: dict[str, Any]) -> bool:
    return _persist(
        "ml_model_registry",
        payload["modelId"] + ":" + payload["modelHash"],
        payload,
        ("model_id", "model_hash", "state"),
        (payload["modelId"], payload["modelHash"], payload["state"]),
    )


def persist_evaluation(payload: dict[str, Any]) -> bool:
    return _persist(
        "ml_evaluation_reports",
        payload["evaluationId"],
        payload,
        ("model_id", "model_hash", "dataset_hash"),
        (payload["modelId"], payload["modelHash"], payload["datasetHash"]),
    )


def persist_review(payload: dict[str, Any]) -> bool:
    return _persist(
        "ml_promotion_reviews",
        payload["reviewId"],
        payload,
        ("model_id", "model_hash", "decision", "record_hash"),
        (
            payload["modelId"],
            payload["modelHash"],
            payload["decision"],
            payload["recordHash"],
        ),
    )


def persist_drift(payload: dict[str, Any]) -> bool:
    return _persist(
        "ml_drift_events",
        payload["driftId"],
        payload,
        ("model_id", "model_hash", "resulting_state"),
        (payload["modelId"], payload["modelHash"], payload["resultingState"]),
    )


def get_payload(table: str, record_id: str) -> dict[str, Any] | None:
    if table not in TABLES or not schema_status()["applied"]:
        return None
    conn = storage.connect()
    try:
        row = conn.execute(
            f"SELECT payload_json FROM {table} WHERE record_id = ?",
            (record_id,),
        ).fetchone()
    finally:
        conn.close()
    return json.loads(row["payload_json"]) if row else None


def list_payloads(table: str, limit: int = 100) -> list[dict[str, Any]]:
    if table not in TABLES or not schema_status()["applied"]:
        return []
    conn = storage.connect()
    try:
        rows = conn.execute(
            f"SELECT payload_json FROM {table} "
            "ORDER BY created_at DESC, record_id DESC LIMIT ?",
            (max(1, min(limit, 1000)),),
        ).fetchall()
    finally:
        conn.close()
    return [json.loads(row["payload_json"]) for row in rows]
