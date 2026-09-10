"""Explicit, append-only SQLite persistence for R18 governance artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .. import storage
from .r18_history_finalization import (
    assert_rhist03d_upgrade_safe,
    finalize_rhist03d_artifact,
    rhist03d_preflight_inventory,
    verify_governed_rhist03d_artifact,
)
from .r18_history_store import (
    apply_schema as apply_rhist03d_schema,
    get_governed_frozen_dataset,
    persist_audit_record,
    persist_frozen_dataset,
    persist_governed_model,
    persist_strategy_profile,
    schema_status as rhist03d_schema_status,
    verify_stored_rhist03d_artifact,
)

MIGRATION_VERSION = "0014_r18_model_governance"
TABLES = ("ml_model_registry", "ml_evaluation_reports", "ml_promotion_reviews", "ml_drift_events")


def schema_status() -> dict[str, Any]:
    storage.init_db(); conn = storage.connect()
    try:
        names = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        migration = conn.execute("SELECT 1 FROM schema_migrations WHERE version=?", (MIGRATION_VERSION,)).fetchone()
    finally: conn.close()
    present = tuple(name for name in TABLES if name in names)
    return {"migrationVersion": MIGRATION_VERSION, "applied": bool(migration) and len(present) == len(TABLES), "tables": present, "missingTables": tuple(name for name in TABLES if name not in names)}


def apply_schema() -> dict[str, Any]:
    storage.init_db(); conn = storage.connect()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS ml_model_registry (record_id TEXT PRIMARY KEY, model_id TEXT NOT NULL, model_hash TEXT NOT NULL, state TEXT NOT NULL, payload_json TEXT NOT NULL, content_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_ml_model_registry_model_created ON ml_model_registry(model_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS ml_evaluation_reports (record_id TEXT PRIMARY KEY, model_id TEXT NOT NULL, model_hash TEXT NOT NULL, dataset_hash TEXT NOT NULL, payload_json TEXT NOT NULL, content_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_ml_evaluations_model_created ON ml_evaluation_reports(model_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS ml_promotion_reviews (record_id TEXT PRIMARY KEY, model_id TEXT NOT NULL, model_hash TEXT NOT NULL, decision TEXT NOT NULL, record_hash TEXT NOT NULL UNIQUE, payload_json TEXT NOT NULL, content_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_ml_reviews_model_created ON ml_promotion_reviews(model_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS ml_drift_events (record_id TEXT PRIMARY KEY, model_id TEXT NOT NULL, model_hash TEXT NOT NULL, resulting_state TEXT NOT NULL, payload_json TEXT NOT NULL, content_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_ml_drift_model_created ON ml_drift_events(model_id, created_at DESC);
        """)
        conn.execute("INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)", (MIGRATION_VERSION, "R18 append-only model governance", datetime.now(UTC).isoformat())); conn.commit()
    finally: conn.close()
    return schema_status()


def _persist(table: str, record_id: str, payload: dict[str, Any], columns: tuple[str, ...], values: tuple[Any, ...]) -> bool:
    if table not in TABLES or not schema_status()["applied"]: raise RuntimeError("WAIT_R18_SCHEMA_NOT_APPLIED")
    encoded = storage.encode_json(payload); import hashlib; content_hash = hashlib.sha256(encoded.encode()).hexdigest(); conn = storage.connect()
    try:
        existing = conn.execute(f"SELECT payload_json FROM {table} WHERE record_id=?", (record_id,)).fetchone()
        if existing:
            if existing["payload_json"] != encoded: raise ValueError("R18_ARTIFACT_IMMUTABLE")
            return False
        names = ("record_id",) + columns + ("payload_json", "content_hash", "created_at"); marks = ",".join("?" for _ in names)
        conn.execute(f"INSERT INTO {table} ({','.join(names)}) VALUES ({marks})", (record_id,) + values + (encoded, content_hash, datetime.now(UTC).isoformat())); conn.commit(); return True
    finally: conn.close()


def persist_manifest(payload: dict[str, Any]) -> bool:
    return _persist("ml_model_registry", payload["modelId"] + ":" + payload["modelHash"], payload, ("model_id", "model_hash", "state"), (payload["modelId"], payload["modelHash"], payload["state"]))


def persist_evaluation(payload: dict[str, Any]) -> bool:
    return _persist("ml_evaluation_reports", payload["evaluationId"], payload, ("model_id", "model_hash", "dataset_hash"), (payload["modelId"], payload["modelHash"], payload["datasetHash"]))


def persist_review(payload: dict[str, Any]) -> bool:
    return _persist("ml_promotion_reviews", payload["reviewId"], payload, ("model_id", "model_hash", "decision", "record_hash"), (payload["modelId"], payload["modelHash"], payload["decision"], payload["recordHash"]))


def persist_drift(payload: dict[str, Any]) -> bool:
    return _persist("ml_drift_events", payload["driftId"], payload, ("model_id", "model_hash", "resulting_state"), (payload["modelId"], payload["modelHash"], payload["resultingState"]))


def get_payload(table: str, record_id: str) -> dict[str, Any] | None:
    if table not in TABLES or not schema_status()["applied"]: return None
    import json; conn = storage.connect()
    try: row = conn.execute(f"SELECT payload_json FROM {table} WHERE record_id = ?", (record_id,)).fetchone()
    finally: conn.close()
    return json.loads(row["payload_json"]) if row else None


def list_payloads(table: str, limit: int = 100) -> list[dict[str, Any]]:
    if table not in TABLES or not schema_status()["applied"]: return []
    import json; conn = storage.connect()
    try: rows = conn.execute(f"SELECT payload_json FROM {table} ORDER BY created_at DESC, record_id DESC LIMIT ?", (max(1, min(limit, 1000)),)).fetchall()
    finally: conn.close()
    return [json.loads(row["payload_json"]) for row in rows]
