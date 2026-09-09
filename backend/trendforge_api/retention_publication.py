from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Protocol

from .historical_retention import RetentionReferenceType
from .retention_producer import DurableRetentionRegistrar, RetentionEvidenceIntent, RetentionOutboxStatus


class RetentionPublicationStatus(StrEnum):
    PENDING_RETENTION = "PENDING_RETENTION"
    PROTECTED_PENDING_ARTIFACT = "PROTECTED_PENDING_ARTIFACT"
    PUBLISHED = "PUBLISHED"
    FAILED_BLOCKING = "FAILED_BLOCKING"


@dataclass(frozen=True, slots=True)
class RetentionEvidenceRoot:
    role: str
    run_id: str | None = None
    trading_date: date | None = None
    content_hash: str | None = None

    def __post_init__(self) -> None:
        role = self.role.strip().upper()
        if not role:
            raise ValueError("retention evidence role is required")
        object.__setattr__(self, "role", role)
        run_id = self.run_id.strip() if self.run_id is not None else None
        if self.run_id is not None and not run_id:
            raise ValueError("run_id cannot be blank")
        object.__setattr__(self, "run_id", run_id)
        if self.content_hash is not None:
            digest = self.content_hash.casefold()
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("content_hash must be a SHA-256 hex digest")
            object.__setattr__(self, "content_hash", digest)
        if not any((self.run_id, self.trading_date, self.content_hash)):
            raise ValueError("retention evidence root requires exact lineage")

    def canonical(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "runId": self.run_id,
            "tradingDate": self.trading_date.isoformat() if self.trading_date else None,
            "contentHash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class RetentionPublicationRequest:
    artifact_type: str
    artifact_id: str
    artifact_version: str
    reference_type: RetentionReferenceType
    evidence_roots: tuple[RetentionEvidenceRoot, ...]
    lineage: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        for name in ("artifact_type", "artifact_id", "artifact_version"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise ValueError(f"{name} is required")
            object.__setattr__(self, name, value)
        if not self.evidence_roots:
            raise ValueError("mandatory publication requires at least one evidence root")
        roles = [root.role for root in self.evidence_roots]
        if len(roles) != len(set(roles)):
            raise ValueError("retention evidence roles must be unique within an artifact")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @property
    def publication_id(self) -> str:
        material = json.dumps(
            {
                "artifactType": self.artifact_type,
                "artifactId": self.artifact_id,
                "artifactVersion": self.artifact_version,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return "rhist-pub:" + hashlib.sha256(material).hexdigest()

    @property
    def lineage_json(self) -> str:
        return json.dumps(
            {
                "artifactType": self.artifact_type,
                "artifactId": self.artifact_id,
                "artifactVersion": self.artifact_version,
                "referenceType": self.reference_type.value,
                "evidenceRoots": [root.canonical() for root in self.evidence_roots],
                "lineage": self.lineage,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    @property
    def lineage_hash(self) -> str:
        return hashlib.sha256(self.lineage_json.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RetentionPublicationReceipt:
    publication_id: str
    artifact_type: str
    artifact_id: str
    status: RetentionPublicationStatus
    required_count: int
    applied_count: int
    last_error: str | None = None


class _Registrar(Protocol):
    def initialize_schema(self, connection: sqlite3.Connection | None = None) -> None: ...
    def enqueue(self, intent: RetentionEvidenceIntent, *, connection: sqlite3.Connection | None = None): ...
    def dispatch(self, event_id: str): ...


class RetentionPublicationStore:
    """Research-side publication gate for cross-store historical retention."""

    def __init__(self, *, db_path: Path, registrar: _Registrar | None = None) -> None:
        self.db_path = db_path.expanduser().resolve(strict=False)
        self.registrar = registrar or DurableRetentionRegistrar(db_path=self.db_path)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def initialize_schema(self, *, connection: sqlite3.Connection | None = None) -> None:
        owns = connection is None
        conn = connection or self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS historical_retention_publications (
                    publication_id TEXT PRIMARY KEY,
                    artifact_type TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    artifact_version TEXT NOT NULL,
                    reference_type TEXT NOT NULL,
                    lineage_json TEXT NOT NULL,
                    lineage_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    required_count INTEGER NOT NULL,
                    applied_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_error TEXT,
                    UNIQUE(artifact_type, artifact_id, artifact_version)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_retention_publications_status "
                "ON historical_retention_publications(status, created_at, publication_id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS historical_retention_publication_members (
                    publication_id TEXT NOT NULL,
                    evidence_role TEXT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    reference_id TEXT NOT NULL UNIQUE,
                    root_json TEXT NOT NULL,
                    PRIMARY KEY(publication_id, evidence_role),
                    FOREIGN KEY(publication_id)
                        REFERENCES historical_retention_publications(publication_id)
                )
                """
            )
            self.registrar.initialize_schema(connection=conn)
            if owns:
                conn.commit()
        finally:
            if owns:
                conn.close()

    def stage(
        self,
        request: RetentionPublicationRequest,
        *,
        connection: sqlite3.Connection,
    ) -> RetentionPublicationReceipt:
        self.initialize_schema(connection=connection)
        now = request.created_at.isoformat()
        existing = connection.execute(
            "SELECT * FROM historical_retention_publications WHERE publication_id = ?",
            (request.publication_id,),
        ).fetchone()
        if existing is not None:
            if (
                existing["lineage_hash"] != request.lineage_hash
                or existing["lineage_json"] != request.lineage_json
                or existing["reference_type"] != request.reference_type.value
            ):
                raise ValueError("retention publication identity is immutable and cannot be repointed")
            return self._receipt(existing)

        connection.execute(
            """
            INSERT INTO historical_retention_publications(
                publication_id, artifact_type, artifact_id, artifact_version,
                reference_type, lineage_json, lineage_hash, status,
                required_count, applied_count, created_at, updated_at, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, NULL)
            """,
            (
                request.publication_id,
                request.artifact_type,
                request.artifact_id,
                request.artifact_version,
                request.reference_type.value,
                request.lineage_json,
                request.lineage_hash,
                RetentionPublicationStatus.PENDING_RETENTION.value,
                len(request.evidence_roots),
                now,
                now,
            ),
        )
        for root in request.evidence_roots:
            intent = RetentionEvidenceIntent(
                artifact_type=f"{request.artifact_type}:{root.role}",
                artifact_id=request.artifact_id,
                artifact_version=request.artifact_version,
                reference_type=request.reference_type,
                run_id=root.run_id,
                trading_date=root.trading_date,
                content_hash=root.content_hash,
                created_at=request.created_at,
            )
            pending = self.registrar.enqueue(intent, connection=connection)
            connection.execute(
                """
                INSERT INTO historical_retention_publication_members(
                    publication_id, evidence_role, event_id, reference_id, root_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    request.publication_id,
                    root.role,
                    pending.event_id,
                    pending.reference_id,
                    json.dumps(root.canonical(), sort_keys=True, separators=(",", ":")),
                ),
            )
        row = connection.execute(
            "SELECT * FROM historical_retention_publications WHERE publication_id = ?",
            (request.publication_id,),
        ).fetchone()
        assert row is not None
        return self._receipt(row)

    def stage_owned(self, request: RetentionPublicationRequest) -> RetentionPublicationReceipt:
        self.initialize_schema()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            receipt = self.stage(request, connection=conn)
            conn.commit()
            return receipt

    def finalize(self, publication_id: str) -> RetentionPublicationReceipt:
        self.initialize_schema()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM historical_retention_publications WHERE publication_id = ?",
                (publication_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown retention publication: {publication_id}")
            if row["status"] in {
                RetentionPublicationStatus.PROTECTED_PENDING_ARTIFACT.value,
                RetentionPublicationStatus.PUBLISHED.value,
            }:
                return self._receipt(row)
            members = conn.execute(
                "SELECT event_id FROM historical_retention_publication_members WHERE publication_id = ? ORDER BY evidence_role",
                (publication_id,),
            ).fetchall()
        applied = 0
        failures: list[str] = []
        for member in members:
            try:
                result = self.registrar.dispatch(member["event_id"])
            except Exception as exc:
                failures.append(f"{type(exc).__name__}: {exc}")
                continue
            if result.status is RetentionOutboxStatus.APPLIED:
                applied += 1
            elif result.status is RetentionOutboxStatus.FAILED_BLOCKING:
                failures.append(result.last_error or "retention dispatch failed blocking")
            else:
                failures.append(f"retention event remained {result.status.value}")
        status = (
            RetentionPublicationStatus.PROTECTED_PENDING_ARTIFACT
            if applied == len(members) and not failures
            else RetentionPublicationStatus.FAILED_BLOCKING
        )
        error = "; ".join(failures)[:4000] if failures else None
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE historical_retention_publications
                SET status = ?, applied_count = ?, updated_at = ?, last_error = ?
                WHERE publication_id = ?
                """,
                (status.value, applied, datetime.now(UTC).isoformat(), error, publication_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM historical_retention_publications WHERE publication_id = ?",
                (publication_id,),
            ).fetchone()
        assert row is not None
        return self._receipt(row)

    def mark_published(self, publication_id: str) -> RetentionPublicationReceipt:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM historical_retention_publications WHERE publication_id = ?",
                (publication_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown retention publication: {publication_id}")
            if row["status"] == RetentionPublicationStatus.PUBLISHED.value:
                return self._receipt(row)
            if row["status"] != RetentionPublicationStatus.PROTECTED_PENDING_ARTIFACT.value:
                raise RuntimeError("artifact cannot publish before exact retention protection")
            conn.execute(
                "UPDATE historical_retention_publications SET status = ?, updated_at = ?, last_error = NULL WHERE publication_id = ?",
                (RetentionPublicationStatus.PUBLISHED.value, datetime.now(UTC).isoformat(), publication_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM historical_retention_publications WHERE publication_id = ?",
                (publication_id,),
            ).fetchone()
        assert row is not None
        return self._receipt(row)

    def assert_protected(self, publication_id: str) -> RetentionPublicationReceipt:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM historical_retention_publications WHERE publication_id = ?",
                (publication_id,),
            ).fetchone()
        if row is None or row["status"] not in {
            RetentionPublicationStatus.PROTECTED_PENDING_ARTIFACT.value,
            RetentionPublicationStatus.PUBLISHED.value,
        }:
            raise RuntimeError("immutable publication is not retention-protected; fail closed")
        return self._receipt(row)

    def assert_published(self, publication_id: str) -> RetentionPublicationReceipt:
        receipt = self.assert_protected(publication_id)
        if receipt.status is not RetentionPublicationStatus.PUBLISHED:
            raise RuntimeError("retention is protected but artifact publication is incomplete")
        return receipt

    def reconcile_pending(self, *, limit: int = 100) -> tuple[RetentionPublicationReceipt, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.initialize_schema()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT publication_id FROM historical_retention_publications
                WHERE status = ? ORDER BY created_at, publication_id LIMIT ?
                """,
                (RetentionPublicationStatus.PENDING_RETENTION.value, int(limit)),
            ).fetchall()
        return tuple(self.finalize(row["publication_id"]) for row in rows)

    def coverage(self, *, artifact_types: Iterable[str] | None = None) -> dict[str, Any]:
        self.initialize_schema()
        requested = tuple(sorted(set(artifact_types or ())))
        where = ""
        params: tuple[Any, ...] = ()
        if requested:
            placeholders = ",".join("?" for _ in requested)
            where = f" WHERE artifact_type IN ({placeholders})"
            params = requested
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM historical_retention_publications"
                + where
                + " GROUP BY status",
                params,
            ).fetchall()
        counts = {row["status"]: int(row["count"]) for row in rows}
        total = sum(counts.values())
        protected = counts.get(RetentionPublicationStatus.PUBLISHED.value, 0)
        return {
            "totalMandatoryArtifacts": total,
            "protectedMandatoryArtifacts": protected,
            "coverage": (protected / total) if total else 1.0,
            "countsByStatus": counts,
        }

    @staticmethod
    def _receipt(row: sqlite3.Row) -> RetentionPublicationReceipt:
        return RetentionPublicationReceipt(
            publication_id=row["publication_id"],
            artifact_type=row["artifact_type"],
            artifact_id=row["artifact_id"],
            status=RetentionPublicationStatus(row["status"]),
            required_count=int(row["required_count"]),
            applied_count=int(row["applied_count"]),
            last_error=row["last_error"],
        )
