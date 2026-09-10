"""Durable producer-side wiring for historical evidence retention.

R-HIST-03A foundation: producers enqueue an immutable retention intent in the
same SQLite transaction as the artifact they publish. A dispatcher then
materializes the intent through HistoricalRetentionAuthority. Replays are
idempotent; payload mutation is treated as corruption and fails closed.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from trendforge_api.historical_retention import (
    HistoricalRetentionAuthority,
    RetentionReference,
    RetentionReferenceType,
)


class RetentionOutboxStatus(StrEnum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    FAILED_BLOCKING = "FAILED_BLOCKING"


def _normalize_sha256(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
        raise ValueError(f"{field_name} must be a 64-character SHA256 hex digest")
    return normalized


@dataclass(frozen=True, slots=True)
class RetentionEvidenceIntent:
    artifact_type: str
    artifact_id: str
    artifact_version: str
    reference_type: RetentionReferenceType
    run_id: str | None = None
    trading_date: date | None = None
    content_hash: str | None = None
    artifact_hash: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        for name in ("artifact_type", "artifact_id", "artifact_version"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise ValueError(f"{name} must be non-empty")
            object.__setattr__(self, name, value)
        if self.run_id is not None:
            run_id = self.run_id.strip()
            if not run_id:
                raise ValueError("run_id cannot be blank")
            object.__setattr__(self, "run_id", run_id)
        object.__setattr__(
            self,
            "content_hash",
            _normalize_sha256(self.content_hash, field_name="content_hash"),
        )
        object.__setattr__(
            self,
            "artifact_hash",
            _normalize_sha256(self.artifact_hash, field_name="artifact_hash"),
        )
        market_mode = bool(self.run_id or self.trading_date or self.content_hash)
        artifact_mode = self.artifact_hash is not None
        if not market_mode and not artifact_mode:
            raise ValueError(
                "retention intent requires run_id, trading_date, or content_hash, "
                "or artifact_hash"
            )
        if market_mode and artifact_mode:
            raise ValueError(
                "retention intent requires exactly one evidence identity mode: "
                "market locator or artifact_hash"
            )
        created_at = self.created_at
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", created_at.astimezone(UTC))

    def canonical_payload(self) -> dict[str, str | None]:
        payload: dict[str, str | None] = {
            "artifactId": self.artifact_id,
            "artifactType": self.artifact_type,
            "artifactVersion": self.artifact_version,
            "contentHash": self.content_hash,
            "createdAt": self.created_at.isoformat(),
            "referenceType": self.reference_type.value,
            "runId": self.run_id,
            "tradingDate": self.trading_date.isoformat() if self.trading_date else None,
        }
        if self.artifact_hash is not None:
            payload["artifactHash"] = self.artifact_hash
        return payload

    @property
    def payload_json(self) -> str:
        return json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":"))

    @property
    def payload_hash(self) -> str:
        return hashlib.sha256(self.payload_json.encode("utf-8")).hexdigest()

    @property
    def lineage_digest(self) -> str:
        identity = self.canonical_payload().copy()
        identity.pop("createdAt")
        canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def event_id(self) -> str:
        return f"rhist03:{self.lineage_digest}"

    @property
    def reference_id(self) -> str:
        return f"{self.reference_type.value.lower()}:{self.lineage_digest}"


@dataclass(frozen=True, slots=True)
class RetentionPublicationReceipt:
    event_id: str
    reference_id: str
    status: RetentionOutboxStatus
    attempts: int
    applied_at: datetime | None = None
    last_error: str | None = None


class _RetentionAuthority(Protocol):
    def register(self, reference: RetentionReference) -> RetentionReference: ...


class DurableRetentionRegistrar:
    """Immutable producer outbox plus deterministic retention dispatcher."""

    def __init__(
        self,
        *,
        db_path: Path | str,
        authority: _RetentionAuthority | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.authority = authority or HistoricalRetentionAuthority(db_path=self.db_path)

    @staticmethod
    def _ensure_column(
        conn: sqlite3.Connection,
        table: str,
        column: str,
        declaration: str,
    ) -> None:
        columns = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")

    def initialize_schema(self, connection: sqlite3.Connection | None = None) -> None:
        owns = connection is None
        conn = connection or sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS historical_retention_outbox (
                    event_id TEXT PRIMARY KEY,
                    reference_id TEXT NOT NULL UNIQUE,
                    artifact_type TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    artifact_version TEXT NOT NULL,
                    reference_type TEXT NOT NULL,
                    run_id TEXT,
                    trading_date TEXT,
                    content_hash TEXT,
                    artifact_hash TEXT,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    applied_at TEXT,
                    last_error TEXT
                )
                """
            )
            self._ensure_column(conn, "historical_retention_outbox", "artifact_hash", "TEXT")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_retention_outbox_status_created "
                "ON historical_retention_outbox(status, created_at)"
            )
            if owns:
                conn.commit()
        finally:
            if owns:
                conn.close()

    def enqueue(
        self,
        intent: RetentionEvidenceIntent,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> RetentionPublicationReceipt:
        """Enqueue idempotently; caller-owned connection preserves producer atomicity."""
        owns = connection is None
        conn = connection or sqlite3.connect(self.db_path)
        try:
            self.initialize_schema(conn)
            existing = conn.execute(
                "SELECT payload_hash, payload_json FROM historical_retention_outbox WHERE event_id = ?",
                (intent.event_id,),
            ).fetchone()
            if existing is not None:
                if existing[0] != intent.payload_hash or existing[1] != intent.payload_json:
                    raise ValueError("retention outbox event_id is immutable and cannot be repointed")
                return self._receipt(conn, intent.event_id)
            conn.execute(
                """
                INSERT INTO historical_retention_outbox (
                    event_id, reference_id, artifact_type, artifact_id, artifact_version,
                    reference_type, run_id, trading_date, content_hash, artifact_hash,
                    payload_json, payload_hash, status, attempts, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    intent.event_id,
                    intent.reference_id,
                    intent.artifact_type,
                    intent.artifact_id,
                    intent.artifact_version,
                    intent.reference_type.value,
                    intent.run_id,
                    intent.trading_date.isoformat() if intent.trading_date else None,
                    intent.content_hash,
                    intent.artifact_hash,
                    intent.payload_json,
                    intent.payload_hash,
                    RetentionOutboxStatus.PENDING.value,
                    intent.created_at.isoformat(),
                ),
            )
            if owns:
                conn.commit()
            return self._receipt(conn, intent.event_id)
        except Exception:
            if owns:
                conn.rollback()
            raise
        finally:
            if owns:
                conn.close()

    @staticmethod
    def _typed_transient(row: sqlite3.Row, exc: Exception) -> bool:
        if row["artifact_hash"] is None or not isinstance(exc, sqlite3.OperationalError):
            return False
        message = str(exc).lower()
        return "locked" in message or "busy" in message

    def dispatch(self, event_id: str) -> RetentionPublicationReceipt:
        """Apply one intent; typed SQLite contention stays safely retryable."""
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as conn:
            row = self._load_verified_row(conn, event_id)
            if row["status"] == RetentionOutboxStatus.APPLIED.value:
                return self._receipt(conn, event_id)
            if row["status"] == RetentionOutboxStatus.FAILED_BLOCKING.value:
                raise RuntimeError(f"retention event is blocking: {event_id}: {row['last_error']}")
            attempts = int(row["attempts"]) + 1
            conn.execute(
                "UPDATE historical_retention_outbox SET attempts = ? WHERE event_id = ?",
                (attempts, event_id),
            )
            conn.commit()

        try:
            reference = RetentionReference(
                reference_id=row["reference_id"],
                reference_type=RetentionReferenceType(row["reference_type"]),
                content_hash=row["content_hash"],
                run_id=row["run_id"],
                trading_date=date.fromisoformat(row["trading_date"])
                if row["trading_date"]
                else None,
                artifact_id=row["artifact_id"] if row["artifact_hash"] else None,
                artifact_version=row["artifact_version"] if row["artifact_hash"] else None,
                artifact_hash=row["artifact_hash"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self.authority.register(reference)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            status = (
                RetentionOutboxStatus.PENDING
                if self._typed_transient(row, exc)
                else RetentionOutboxStatus.FAILED_BLOCKING
            )
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE historical_retention_outbox SET status = ?, last_error = ? WHERE event_id = ?",
                    (status.value, error, event_id),
                )
                conn.commit()
                return self._receipt(conn, event_id)

        with sqlite3.connect(self.db_path) as conn:
            verified = self._load_verified_row(conn, event_id)
            now = datetime.now(UTC).isoformat()
            conn.execute(
                "UPDATE historical_retention_outbox "
                "SET status = ?, applied_at = ?, last_error = NULL WHERE event_id = ?",
                (RetentionOutboxStatus.APPLIED.value, now, event_id),
            )
            conn.commit()
            return self._receipt(conn, verified["event_id"])

    def reconcile_pending(self, *, limit: int = 100) -> tuple[RetentionPublicationReceipt, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT event_id FROM historical_retention_outbox "
                "WHERE status = ? ORDER BY created_at, event_id LIMIT ?",
                (RetentionOutboxStatus.PENDING.value, limit),
            ).fetchall()
        return tuple(self.dispatch(str(row[0])) for row in rows)

    def assert_publishable(self, event_id: str) -> RetentionPublicationReceipt:
        self.initialize_schema()
        with sqlite3.connect(self.db_path) as conn:
            receipt = self._receipt(conn, event_id)
        if receipt.status is not RetentionOutboxStatus.APPLIED:
            raise RuntimeError(
                f"historical retention not applied; publication must fail closed: {event_id} "
                f"status={receipt.status.value}"
            )
        return receipt

    def _load_verified_row(self, conn: sqlite3.Connection, event_id: str) -> sqlite3.Row:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM historical_retention_outbox WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown retention outbox event: {event_id}")
        payload_json = str(row["payload_json"])
        actual_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        if actual_hash != row["payload_hash"]:
            raise RuntimeError(f"retention outbox payload hash mismatch: {event_id}")
        payload = json.loads(payload_json)
        expected: dict[str, str | None] = {
            "artifactId": row["artifact_id"],
            "artifactType": row["artifact_type"],
            "artifactVersion": row["artifact_version"],
            "contentHash": row["content_hash"],
            "createdAt": row["created_at"],
            "referenceType": row["reference_type"],
            "runId": row["run_id"],
            "tradingDate": row["trading_date"],
        }
        if row["artifact_hash"] is not None:
            expected["artifactHash"] = row["artifact_hash"]
        if payload != expected:
            raise RuntimeError(f"retention outbox payload columns disagree: {event_id}")
        return row

    def _receipt(self, conn: sqlite3.Connection, event_id: str) -> RetentionPublicationReceipt:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT event_id, reference_id, status, attempts, applied_at, last_error "
            "FROM historical_retention_outbox WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown retention outbox event: {event_id}")
        return RetentionPublicationReceipt(
            event_id=str(row["event_id"]),
            reference_id=str(row["reference_id"]),
            status=RetentionOutboxStatus(str(row["status"])),
            attempts=int(row["attempts"]),
            applied_at=datetime.fromisoformat(row["applied_at"]) if row["applied_at"] else None,
            last_error=str(row["last_error"]) if row["last_error"] else None,
        )


__all__ = [
    "DurableRetentionRegistrar",
    "RetentionEvidenceIntent",
    "RetentionOutboxStatus",
    "RetentionPublicationReceipt",
]
