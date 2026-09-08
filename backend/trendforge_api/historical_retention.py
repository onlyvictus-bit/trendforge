from __future__ import annotations

import re
import sqlite3
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


RETENTION_MIGRATION_VERSION = "0022_historical_evidence_retention"
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


class RetentionTier(StrEnum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


class RetentionReferenceType(StrEnum):
    DECISION_VERSION = "DECISION_VERSION"
    OUTCOME = "OUTCOME"
    REVISION = "REVISION"
    ML_DATASET = "ML_DATASET"
    MODEL_VERSION = "MODEL_VERSION"
    STRATEGY_PROFILE = "STRATEGY_PROFILE"
    AUDIT = "AUDIT"
    TEMPORARY = "TEMPORARY"


PERMANENT_REFERENCE_TYPES = frozenset(
    {
        RetentionReferenceType.DECISION_VERSION,
        RetentionReferenceType.OUTCOME,
        RetentionReferenceType.REVISION,
        RetentionReferenceType.ML_DATASET,
        RetentionReferenceType.MODEL_VERSION,
        RetentionReferenceType.STRATEGY_PROFILE,
        RetentionReferenceType.AUDIT,
    }
)


class RetentionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    temporary_days: int = Field(default=7, ge=1)
    hot_days: int = Field(default=90, ge=1)
    warm_days: int = Field(default=365, ge=1)

    @model_validator(mode="after")
    def validate_tier_order(self) -> RetentionPolicy:
        if self.temporary_days > self.hot_days:
            raise ValueError("temporary_days cannot exceed hot_days")
        if self.hot_days >= self.warm_days:
            raise ValueError("hot_days must be less than warm_days")
        return self

    def tier_for(self, trading_date: date, *, as_of_date: date) -> RetentionTier:
        age_days = (as_of_date - trading_date).days
        if age_days < 0:
            raise ValueError("trading_date cannot be in the future")
        if age_days <= self.hot_days:
            return RetentionTier.HOT
        if age_days <= self.warm_days:
            return RetentionTier.WARM
        return RetentionTier.COLD


class RetentionReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    reference_id: str = Field(min_length=1, max_length=256)
    reference_type: RetentionReferenceType
    content_hash: str | None = None
    run_id: str | None = Field(default=None, max_length=128)
    trading_date: date | None = None
    permanent: bool = True
    retain_until: date | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_reference(self) -> RetentionReference:
        if not any((self.content_hash, self.run_id, self.trading_date)):
            raise ValueError("retention reference must identify evidence")
        if self.content_hash is not None:
            normalized = self.content_hash.casefold()
            if not _HASH_PATTERN.fullmatch(normalized):
                raise ValueError("content_hash must be a SHA-256 hex digest")
            object.__setattr__(self, "content_hash", normalized)
        if self.permanent and self.retain_until is not None:
            raise ValueError("permanent retention reference cannot have retain_until")
        if not self.permanent and self.retain_until is None:
            raise ValueError("non-permanent retention reference requires retain_until")
        if self.reference_type in PERMANENT_REFERENCE_TYPES and not self.permanent:
            raise ValueError(
                f"{self.reference_type.value} evidence cannot use temporary retention"
            )
        return self

    def is_active(self, *, as_of_date: date) -> bool:
        if self.permanent:
            return True
        assert self.retain_until is not None
        return self.retain_until >= as_of_date


class RetentionProtectionSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    trading_dates: tuple[date, ...] = ()
    run_ids: tuple[str, ...] = ()
    content_hashes: tuple[str, ...] = ()
    reference_ids: tuple[str, ...] = ()


class HistoricalRetentionAuthority:
    """Fail-closed authority for historical evidence retention.

    This service owns retention references and computes immutable protection sets.
    It deliberately does not delete files. Deletion remains a separate operation
    that must consume this authority before it is allowed to remove history.
    """

    def __init__(self, *, db_path: Path, policy: RetentionPolicy | None = None) -> None:
        self.db_path = db_path.expanduser().resolve(strict=False)
        self.policy = policy or RetentionPolicy()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS historical_retention_references (
                    reference_id TEXT PRIMARY KEY,
                    reference_type TEXT NOT NULL,
                    content_hash TEXT,
                    run_id TEXT,
                    trading_date TEXT,
                    permanent INTEGER NOT NULL CHECK(permanent IN (0, 1)),
                    retain_until TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_retention_content_hash
                ON historical_retention_references(content_hash);

                CREATE INDEX IF NOT EXISTS idx_retention_run_id
                ON historical_retention_references(run_id);

                CREATE INDEX IF NOT EXISTS idx_retention_trading_date
                ON historical_retention_references(trading_date);
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations(version, description, applied_at)
                VALUES (?, ?, ?)
                """,
                (
                    RETENTION_MIGRATION_VERSION,
                    "Reference-aware historical evidence retention authority",
                    datetime.now(UTC).isoformat(),
                ),
            )

    def _known_table(self, connection: sqlite3.Connection, table: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None

    def _validate_evidence_exists(
        self, connection: sqlite3.Connection, reference: RetentionReference
    ) -> None:
        if reference.content_hash is not None:
            if not self._known_table(connection, "market_data_objects"):
                raise ValueError("market_data_objects is unavailable; refusing unknown content_hash")
            row = connection.execute(
                "SELECT 1 FROM market_data_objects WHERE content_hash = ?",
                (reference.content_hash,),
            ).fetchone()
            if row is None:
                raise ValueError("unknown content_hash; refusing retention reference")
        if reference.run_id is not None:
            if not self._known_table(connection, "market_data_manifests"):
                raise ValueError("market_data_manifests is unavailable; refusing unknown run_id")
            row = connection.execute(
                "SELECT trading_date FROM market_data_manifests WHERE run_id = ?",
                (reference.run_id,),
            ).fetchone()
            if row is None:
                raise ValueError("unknown run_id; refusing retention reference")
            if (
                reference.trading_date is not None
                and row["trading_date"] != reference.trading_date.isoformat()
            ):
                raise ValueError("run_id trading_date does not match retention reference")

    def register(self, reference: RetentionReference) -> RetentionReference:
        self.initialize_schema()
        with self._connect() as connection:
            self._validate_evidence_exists(connection, reference)
            connection.execute(
                """
                INSERT INTO historical_retention_references(
                    reference_id, reference_type, content_hash, run_id, trading_date,
                    permanent, retain_until, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(reference_id) DO UPDATE SET
                    reference_type=excluded.reference_type,
                    content_hash=excluded.content_hash,
                    run_id=excluded.run_id,
                    trading_date=excluded.trading_date,
                    permanent=excluded.permanent,
                    retain_until=excluded.retain_until,
                    created_at=excluded.created_at
                """,
                (
                    reference.reference_id,
                    reference.reference_type.value,
                    reference.content_hash,
                    reference.run_id,
                    reference.trading_date.isoformat() if reference.trading_date else None,
                    int(reference.permanent),
                    reference.retain_until.isoformat() if reference.retain_until else None,
                    reference.created_at.isoformat(),
                ),
            )
        return reference

    @staticmethod
    def _from_row(row: sqlite3.Row) -> RetentionReference:
        return RetentionReference(
            reference_id=row["reference_id"],
            reference_type=RetentionReferenceType(row["reference_type"]),
            content_hash=row["content_hash"],
            run_id=row["run_id"],
            trading_date=date.fromisoformat(row["trading_date"]) if row["trading_date"] else None,
            permanent=bool(row["permanent"]),
            retain_until=date.fromisoformat(row["retain_until"]) if row["retain_until"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def active_references(self, *, as_of_date: date) -> tuple[RetentionReference, ...]:
        self.initialize_schema()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM historical_retention_references ORDER BY reference_id"
            ).fetchall()
        references = tuple(self._from_row(row) for row in rows)
        return tuple(ref for ref in references if ref.is_active(as_of_date=as_of_date))

    def protection_set(self, *, as_of_date: date) -> RetentionProtectionSet:
        references = self.active_references(as_of_date=as_of_date)
        dates = {ref.trading_date for ref in references if ref.trading_date is not None}
        run_ids = {ref.run_id for ref in references if ref.run_id is not None}
        hashes = {ref.content_hash for ref in references if ref.content_hash is not None}

        with self._connect() as connection:
            if run_ids:
                if not self._known_table(connection, "market_data_manifests"):
                    raise RuntimeError("cannot resolve protected run_ids without manifest table")
                for run_id in sorted(run_ids):
                    row = connection.execute(
                        "SELECT trading_date FROM market_data_manifests WHERE run_id = ?",
                        (run_id,),
                    ).fetchone()
                    if row is None:
                        raise RuntimeError(f"protected run_id disappeared: {run_id}")
                    dates.add(date.fromisoformat(row["trading_date"]))

                    if self._known_table(connection, "market_data_manifest_objects"):
                        object_rows = connection.execute(
                            "SELECT content_hash FROM market_data_manifest_objects WHERE run_id = ?",
                            (run_id,),
                        ).fetchall()
                        hashes.update(row["content_hash"] for row in object_rows)
            if hashes and self._known_table(connection, "market_data_manifest_objects"):
                for content_hash in tuple(hashes):
                    object_rows = connection.execute(
                        """
                        SELECT manifests.trading_date, refs.run_id
                        FROM market_data_manifest_objects AS refs
                        JOIN market_data_manifests AS manifests
                          ON manifests.run_id = refs.run_id
                        WHERE refs.content_hash = ?
                        """,
                        (content_hash,),
                    ).fetchall()
                    for row in object_rows:
                        dates.add(date.fromisoformat(row["trading_date"]))
                        run_ids.add(row["run_id"])

        return RetentionProtectionSet(
            trading_dates=tuple(sorted(dates)),
            run_ids=tuple(sorted(run_ids)),
            content_hashes=tuple(sorted(hashes)),
            reference_ids=tuple(sorted(ref.reference_id for ref in references)),
        )

    def assert_deletion_allowed(
        self,
        *,
        trading_date: date | None = None,
        run_id: str | None = None,
        content_hash: str | None = None,
        as_of_date: date,
    ) -> None:
        protection = self.protection_set(as_of_date=as_of_date)
        if trading_date is not None and trading_date in protection.trading_dates:
            raise PermissionError("trading date is protected historical evidence")
        if run_id is not None and run_id in protection.run_ids:
            raise PermissionError("manifest run is protected historical evidence")
        if content_hash is not None and content_hash.casefold() in protection.content_hashes:
            raise PermissionError("content hash is protected historical evidence")
