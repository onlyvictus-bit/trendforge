from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .historical_retention import HistoricalRetentionAuthority
from .read_snapshot import borrow_connection


STORE_MIGRATION_VERSION = "0020_market_data_69_store"
MANIFEST_SCHEMA_VERSION = "trendforge.marketDataManifest.v1"
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
_EXTENSION_PATTERN = re.compile(r"[A-Za-z0-9]{1,12}")
_SLOT_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,32}")


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ManifestStatus(StrEnum):
    SUCCESS_NEW = "SUCCESS_NEW"
    SUCCESS_UNCHANGED = "SUCCESS_UNCHANGED"
    VALID_EMPTY = "VALID_EMPTY"
    STALE_LAST_GOOD = "STALE_LAST_GOOD"
    WAITING_FOR_PUBLICATION = "WAITING_FOR_PUBLICATION"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CACHED_CURRENT = "CACHED_CURRENT"
    NOT_DUE_NO_DATA = "NOT_DUE_NO_DATA"
    MISSED = "MISSED"


class ObjectReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    content_hash: str
    path: Path
    size_bytes: int = Field(ge=0)
    media_type: str
    created: bool

    @field_validator("content_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        normalized = value.casefold()
        if not _HASH_PATTERN.fullmatch(normalized):
            raise ValueError("content_hash must be a SHA-256 hex digest")
        return normalized


class StoredAttempt(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempt_id: int = Field(gt=0)
    run_id: str
    source_key: str
    trading_date: date
    slot: str
    attempted_at: datetime
    status: ManifestStatus
    source_url: str | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    media_type: str | None = None
    content_hash: str | None = None
    object_path: str | None = None
    data_date: date | None = None
    fetched_at: datetime | None = None
    normalized_row_count: int = Field(default=0, ge=0)
    error: str | None = None
    retry_count: int = Field(default=0, ge=0)


class ManifestEntry(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    source_key: str = Field(min_length=1)
    status: ManifestStatus
    attempted_at: datetime | None = None
    source_url: str | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    media_type: str | None = None
    content_hash: str | None = None
    object_path: str | None = None
    data_date: date | None = None
    fetched_at: datetime | None = None
    normalized_row_count: int = Field(default=0, ge=0)
    last_good_hash: str | None = None
    last_good_path: str | None = None
    age_seconds: int | None = Field(default=None, ge=0)
    is_stale: bool = False
    error: str | None = None
    retry_count: int = Field(default=0, ge=0)

    @field_validator("content_hash", "last_good_hash")
    @classmethod
    def validate_optional_hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.casefold()
        if not _HASH_PATTERN.fullmatch(normalized):
            raise ValueError("hash fields must contain SHA-256 hex digests")
        return normalized

    @model_validator(mode="after")
    def validate_success_reference(self) -> ManifestEntry:
        if self.status in {
            ManifestStatus.SUCCESS_NEW,
            ManifestStatus.SUCCESS_UNCHANGED,
            ManifestStatus.CACHED_CURRENT,
        } and (not self.content_hash or not self.object_path):
            raise ValueError("successful manifest entries require an object reference")
        return self


class SnapshotManifest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    schema_version: str = MANIFEST_SCHEMA_VERSION
    run_id: str = Field(min_length=1, max_length=128)
    registry_sha256: str
    trading_date: date
    slot: str
    generated_at: datetime
    entries: tuple[ManifestEntry, ...]

    @field_validator("registry_sha256")
    @classmethod
    def validate_registry_hash(cls, value: str) -> str:
        normalized = value.casefold()
        if not _HASH_PATTERN.fullmatch(normalized):
            raise ValueError("registry_sha256 must be a SHA-256 hex digest")
        return normalized

    @field_validator("slot")
    @classmethod
    def validate_slot(cls, value: str) -> str:
        if not _SLOT_PATTERN.fullmatch(value):
            raise ValueError("slot contains unsupported path characters")
        return value

    @model_validator(mode="after")
    def validate_unique_sources(self) -> SnapshotManifest:
        keys = [entry.source_key for entry in self.entries]
        if len(keys) != len(set(keys)):
            raise ValueError("manifest entries must have a unique source_key")
        return self


class SavedManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    manifest_hash: str
    manifest_path: str
    entry_count: int = Field(ge=0)


class CleanupReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    dry_run: bool
    retained_trading_dates: tuple[date, ...]
    eligible_day_paths: tuple[str, ...]
    deleted_day_paths: tuple[str, ...]
    eligible_object_paths: tuple[str, ...]
    deleted_object_paths: tuple[str, ...]


class MarketDataStore:
    """Content-addressed market-data storage over a caller-selected SQLite DB.

    The class never selects the production database implicitly. MD69-M2 tests
    pass temporary paths; the production path is connected only in MD69-M7.
    """

    def __init__(self, *, root: Path, db_path: Path) -> None:
        self.root = root.expanduser().resolve(strict=False)
        self.db_path = db_path.expanduser().resolve(strict=False)
        self.objects_root = self.root / "objects"

    def _connect(self) -> sqlite3.Connection:
        borrowed = borrow_connection(self.db_path)
        if borrowed is not None:
            return borrowed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    def initialize_schema(self) -> None:
        if borrow_connection(self.db_path) is not None:
            return  # Existing schema only; snapshot reads never run migrations.
        self.root.mkdir(parents=True, exist_ok=True)
        self.objects_root.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS market_data_objects (
                    content_hash TEXT PRIMARY KEY,
                    object_path TEXT NOT NULL UNIQUE,
                    size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
                    media_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS market_data_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    trading_date TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    attempted_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_url TEXT,
                    http_status INTEGER,
                    media_type TEXT,
                    content_hash TEXT,
                    object_path TEXT,
                    data_date TEXT,
                    fetched_at TEXT,
                    normalized_row_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(content_hash) REFERENCES market_data_objects(content_hash)
                );

                CREATE INDEX IF NOT EXISTS idx_market_data_attempt_source_time
                ON market_data_attempts(source_key, attempted_at DESC);

                CREATE TABLE IF NOT EXISTS market_data_latest (
                    source_key TEXT PRIMARY KEY,
                    attempt_id INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    object_path TEXT NOT NULL,
                    data_date TEXT,
                    fetched_at TEXT NOT NULL,
                    normalized_row_count INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(attempt_id) REFERENCES market_data_attempts(id),
                    FOREIGN KEY(content_hash) REFERENCES market_data_objects(content_hash)
                );

                CREATE TABLE IF NOT EXISTS market_data_manifests (
                    run_id TEXT PRIMARY KEY,
                    trading_date TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    registry_sha256 TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    manifest_path TEXT NOT NULL,
                    manifest_hash TEXT NOT NULL,
                    entry_count INTEGER NOT NULL CHECK(entry_count >= 0)
                );

                CREATE INDEX IF NOT EXISTS idx_market_data_manifest_date_slot
                ON market_data_manifests(trading_date, slot);

                CREATE TABLE IF NOT EXISTS market_data_manifest_objects (
                    run_id TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    PRIMARY KEY(run_id, source_key, content_hash),
                    FOREIGN KEY(run_id) REFERENCES market_data_manifests(run_id)
                        ON DELETE CASCADE,
                    FOREIGN KEY(content_hash) REFERENCES market_data_objects(content_hash)
                );
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations(version, description, applied_at)
                VALUES (?, ?, ?)
                """,
                (
                    STORE_MIGRATION_VERSION,
                    "MD69 content-addressed objects, attempts, last-good and manifests",
                    datetime.now(UTC).isoformat(),
                ),
            )

    @staticmethod
    def _atomic_write(target: Path, payload: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.part"
        try:
            with temporary.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    def install_object(
        self, content: bytes, *, extension: str, media_type: str
    ) -> ObjectReference:
        self.initialize_schema()
        normalized_extension = extension.removeprefix(".")
        if not _EXTENSION_PATTERN.fullmatch(normalized_extension):
            raise ValueError("extension must contain only 1-12 letters or digits")
        content_hash = hashlib.sha256(content).hexdigest()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM market_data_objects WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()
        if existing is not None:
            path = Path(existing["object_path"])
            if not path.is_file() or path.stat().st_size != int(existing["size_bytes"]):
                raise RuntimeError("content object metadata exists but file is missing or truncated")
            return ObjectReference(
                content_hash=content_hash,
                path=path,
                size_bytes=int(existing["size_bytes"]),
                media_type=existing["media_type"],
                created=False,
            )

        target = self.objects_root / content_hash[:2] / (
            f"{content_hash}.{normalized_extension.casefold()}"
        )
        self._atomic_write(target, content)
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO market_data_objects(
                    content_hash, object_path, size_bytes, media_type, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (content_hash, str(target), len(content), media_type, created_at),
            )
            row = connection.execute(
                "SELECT * FROM market_data_objects WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()
        if row is None:
            raise sqlite3.IntegrityError("content object metadata was not persisted")
        canonical_path = Path(row["object_path"])
        if canonical_path != target and target.exists():
            target.unlink()
        return ObjectReference(
            content_hash=content_hash,
            path=canonical_path,
            size_bytes=int(row["size_bytes"]),
            media_type=row["media_type"],
            created=canonical_path == target,
        )

    def commit_success(
        self,
        *,
        run_id: str,
        source_key: str,
        trading_date: date,
        slot: str,
        attempted_at: datetime,
        fetched_at: datetime,
        data_date: date | None,
        source_url: str,
        http_status: int,
        media_type: str,
        content: bytes,
        extension: str,
        normalized_row_count: int,
        retry_count: int,
    ) -> StoredAttempt:
        if normalized_row_count < 0:
            raise ValueError("normalized_row_count cannot be negative")
        object_ref = self.install_object(
            content, extension=extension, media_type=media_type
        )
        with self._connect() as connection:
            previous = connection.execute(
                "SELECT content_hash FROM market_data_latest WHERE source_key = ?",
                (source_key,),
            ).fetchone()
            status = (
                ManifestStatus.SUCCESS_UNCHANGED
                if previous is not None
                and previous["content_hash"] == object_ref.content_hash
                else ManifestStatus.SUCCESS_NEW
            )
            cursor = connection.execute(
                """
                INSERT INTO market_data_attempts(
                    run_id, source_key, trading_date, slot, attempted_at, status,
                    source_url, http_status, media_type, content_hash, object_path,
                    data_date, fetched_at, normalized_row_count, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    source_key,
                    trading_date.isoformat(),
                    slot,
                    attempted_at.isoformat(),
                    status.value,
                    source_url,
                    http_status,
                    media_type,
                    object_ref.content_hash,
                    str(object_ref.path),
                    data_date.isoformat() if data_date else None,
                    fetched_at.isoformat(),
                    normalized_row_count,
                    retry_count,
                ),
            )
            attempt_id = cursor.lastrowid
            if attempt_id is None:
                raise sqlite3.IntegrityError("market-data attempt has no row id")
            connection.execute(
                """
                INSERT INTO market_data_latest(
                    source_key, attempt_id, content_hash, object_path, data_date,
                    fetched_at, normalized_row_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    attempt_id=excluded.attempt_id,
                    content_hash=excluded.content_hash,
                    object_path=excluded.object_path,
                    data_date=excluded.data_date,
                    fetched_at=excluded.fetched_at,
                    normalized_row_count=excluded.normalized_row_count,
                    updated_at=excluded.updated_at
                """,
                (
                    source_key,
                    attempt_id,
                    object_ref.content_hash,
                    str(object_ref.path),
                    data_date.isoformat() if data_date else None,
                    fetched_at.isoformat(),
                    normalized_row_count,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return StoredAttempt(
            attempt_id=int(attempt_id),
            run_id=run_id,
            source_key=source_key,
            trading_date=trading_date,
            slot=slot,
            attempted_at=attempted_at,
            status=status,
            source_url=source_url,
            http_status=http_status,
            media_type=media_type,
            content_hash=object_ref.content_hash,
            object_path=str(object_ref.path),
            data_date=data_date,
            fetched_at=fetched_at,
            normalized_row_count=normalized_row_count,
            retry_count=retry_count,
        )

    def record_attempt(
        self,
        *,
        run_id: str,
        source_key: str,
        trading_date: date,
        slot: str,
        attempted_at: datetime,
        status: ManifestStatus,
        source_url: str | None = None,
        http_status: int | None = None,
        error: str | None = None,
        retry_count: int = 0,
    ) -> StoredAttempt:
        self.initialize_schema()
        if status in {
            ManifestStatus.SUCCESS_NEW,
            ManifestStatus.SUCCESS_UNCHANGED,
            ManifestStatus.CACHED_CURRENT,
        }:
            raise ValueError("successful attempts must use commit_success")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO market_data_attempts(
                    run_id, source_key, trading_date, slot, attempted_at, status,
                    source_url, http_status, error, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    source_key,
                    trading_date.isoformat(),
                    slot,
                    attempted_at.isoformat(),
                    status.value,
                    source_url,
                    http_status,
                    error,
                    retry_count,
                ),
            )
            attempt_id = cursor.lastrowid
        if attempt_id is None:
            raise sqlite3.IntegrityError("market-data attempt has no row id")
        return StoredAttempt(
            attempt_id=int(attempt_id),
            run_id=run_id,
            source_key=source_key,
            trading_date=trading_date,
            slot=slot,
            attempted_at=attempted_at,
            status=status,
            source_url=source_url,
            http_status=http_status,
            error=error,
            retry_count=retry_count,
        )

    @staticmethod
    def _attempt_from_row(row: sqlite3.Row) -> StoredAttempt:
        return StoredAttempt(
            attempt_id=int(row["id"]),
            run_id=row["run_id"],
            source_key=row["source_key"],
            trading_date=date.fromisoformat(row["trading_date"]),
            slot=row["slot"],
            attempted_at=datetime.fromisoformat(row["attempted_at"]),
            status=ManifestStatus(row["status"]),
            source_url=row["source_url"],
            http_status=row["http_status"],
            media_type=row["media_type"],
            content_hash=row["content_hash"],
            object_path=row["object_path"],
            data_date=date.fromisoformat(row["data_date"]) if row["data_date"] else None,
            fetched_at=(
                datetime.fromisoformat(row["fetched_at"])
                if row["fetched_at"]
                else None
            ),
            normalized_row_count=int(row["normalized_row_count"]),
            error=row["error"],
            retry_count=int(row["retry_count"]),
        )

    def latest_for(self, source_key: str) -> StoredAttempt | None:
        self.initialize_schema()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT attempts.*
                FROM market_data_latest AS latest
                JOIN market_data_attempts AS attempts ON attempts.id = latest.attempt_id
                WHERE latest.source_key = ?
                """,
                (source_key,),
            ).fetchone()
        return self._attempt_from_row(row) if row is not None else None

    def latest_attempts_all(self) -> dict[str, StoredAttempt]:
        """Load the most recent attempt for every source, including failures and empties."""
        self.initialize_schema()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT attempts.*
                FROM market_data_attempts AS attempts
                JOIN (
                    SELECT source_key, MAX(id) AS latest_id
                    FROM market_data_attempts
                    GROUP BY source_key
                ) AS newest ON newest.latest_id = attempts.id
                ORDER BY attempts.source_key
                """
            ).fetchall()
        return {row["source_key"]: self._attempt_from_row(row) for row in rows}

    def latest_all(self) -> dict[str, StoredAttempt]:
        """Load every last-good pointer in one SQLite read."""
        self.initialize_schema()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT attempts.*
                FROM market_data_latest AS latest
                JOIN market_data_attempts AS attempts ON attempts.id = latest.attempt_id
                ORDER BY attempts.source_key
                """
            ).fetchall()
        return {row["source_key"]: self._attempt_from_row(row) for row in rows}

    def object_path_for_hash(self, content_hash: str) -> Path:
        normalized = content_hash.casefold()
        if not _HASH_PATTERN.fullmatch(normalized):
            raise ValueError("content_hash must be a SHA-256 hex digest")
        self.initialize_schema()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT object_path FROM market_data_objects WHERE content_hash = ?",
                (normalized,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown content object: {normalized}")
        return Path(row["object_path"])

    def write_manifest(self, manifest: SnapshotManifest) -> SavedManifest:
        self.initialize_schema()
        payload_dict: dict[str, Any] = manifest.model_dump(
            mode="json", by_alias=True
        )
        payload = json.dumps(
            payload_dict,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        manifest_hash = hashlib.sha256(payload).hexdigest()
        target = (
            self.root
            / manifest.trading_date.isoformat()
            / "snapshots"
            / manifest.slot
            / "manifest.json"
        )
        previous_payload = target.read_bytes() if target.exists() else None
        self._atomic_write(target, payload)
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO market_data_manifests(
                        run_id, trading_date, slot, generated_at, registry_sha256,
                        schema_version, manifest_path, manifest_hash, entry_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        trading_date=excluded.trading_date,
                        slot=excluded.slot,
                        generated_at=excluded.generated_at,
                        registry_sha256=excluded.registry_sha256,
                        schema_version=excluded.schema_version,
                        manifest_path=excluded.manifest_path,
                        manifest_hash=excluded.manifest_hash,
                        entry_count=excluded.entry_count
                    """,
                    (
                        manifest.run_id,
                        manifest.trading_date.isoformat(),
                        manifest.slot,
                        manifest.generated_at.isoformat(),
                        manifest.registry_sha256,
                        manifest.schema_version,
                        str(target),
                        manifest_hash,
                        len(manifest.entries),
                    ),
                )
                connection.execute(
                    "DELETE FROM market_data_manifest_objects WHERE run_id = ?",
                    (manifest.run_id,),
                )
                for entry in manifest.entries:
                    if not entry.content_hash:
                        continue
                    known = connection.execute(
                        "SELECT 1 FROM market_data_objects WHERE content_hash = ?",
                        (entry.content_hash,),
                    ).fetchone()
                    if known is None:
                        raise ValueError(
                            f"manifest references unknown object {entry.content_hash}"
                        )
                    connection.execute(
                        """
                        INSERT INTO market_data_manifest_objects(
                            run_id, source_key, content_hash
                        ) VALUES (?, ?, ?)
                        """,
                        (manifest.run_id, entry.source_key, entry.content_hash),
                    )
        except Exception:
            if previous_payload is None:
                if target.exists():
                    target.unlink()
            else:
                self._atomic_write(target, previous_payload)
            raise
        return SavedManifest(
            run_id=manifest.run_id,
            manifest_hash=manifest_hash,
            manifest_path=str(target),
            entry_count=len(manifest.entries),
        )

    @staticmethod
    def _is_reparse_point(path: Path) -> bool:
        if path.is_symlink():
            return True
        attributes = getattr(path.stat(), "st_file_attributes", 0)
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))

    def assert_safe_delete_target(self, target: Path, *, as_of_date: date) -> Path:
        root = self.root.resolve(strict=False)
        candidate = target.expanduser().resolve(strict=False)
        if candidate == root:
            raise ValueError("refusing to delete the market-data root itself")
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("delete target must remain beneath market-data root") from exc
        if len(relative.parts) != 1:
            raise ValueError("retention may delete only a direct trading-day directory")
        try:
            target_date = date.fromisoformat(relative.name)
        except ValueError as exc:
            raise ValueError("retention target must be an ISO trading-day directory") from exc
        if target_date == as_of_date:
            raise ValueError("refusing to delete the current trading day")
        cursor = target
        while cursor != self.root:
            if cursor.exists() and self._is_reparse_point(cursor):
                raise ValueError("refusing symlink or reparse-point traversal")
            cursor = cursor.parent
        return candidate

    def _assert_tree_has_no_reparse_points(self, target: Path) -> None:
        if not target.exists():
            return
        for directory, child_directories, filenames in os.walk(
            target, topdown=True, followlinks=False
        ):
            parent = Path(directory)
            for name in (*child_directories, *filenames):
                child = parent / name
                if self._is_reparse_point(child):
                    raise ValueError(
                        "refusing nested symlink or reparse-point traversal"
                    )

    def _future_referenced_hashes(self, expired_dates: set[str]) -> set[str]:
        with self._connect() as connection:
            latest = {
                row[0]
                for row in connection.execute(
                    "SELECT content_hash FROM market_data_latest"
                )
            }
            manifest = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT refs.content_hash
                    FROM market_data_manifest_objects AS refs
                    JOIN market_data_manifests AS manifests
                      ON manifests.run_id = refs.run_id
                    WHERE manifests.trading_date NOT IN (
                        SELECT value FROM json_each(?)
                    )
                    """,
                    (json.dumps(sorted(expired_dates)),),
                )
            }
        return latest | manifest

    def cleanup_retention(
        self,
        *,
        as_of_date: date,
        completed_trading_days: list[date],
        detailed_trading_days: int = 5,
        dry_run: bool = True,
    ) -> CleanupReport:
        self.initialize_schema()
        if detailed_trading_days < 0:
            raise ValueError("detailed_trading_days cannot be negative")

        retention_authority = HistoricalRetentionAuthority(db_path=self.db_path)
        protection = retention_authority.protection_set(as_of_date=as_of_date)
        protected_dates = set(protection.trading_dates)
        protected_hashes = set(protection.content_hashes)

        completed = sorted({day for day in completed_trading_days if day < as_of_date})
        age_retained = (
            set(completed[-detailed_trading_days:]) if detailed_trading_days else set()
        )
        retained_set = age_retained | (set(completed) & protected_dates)
        retained = tuple(sorted(retained_set))
        expired_dates = set(completed) - retained_set
        expired = {day.isoformat() for day in expired_dates}
        targets = tuple(self.root / value for value in sorted(expired))

        for target in targets:
            safe_target = self.assert_safe_delete_target(
                target, as_of_date=as_of_date
            )
            self._assert_tree_has_no_reparse_points(safe_target)

        future_references = self._future_referenced_hashes(expired) | protected_hashes
        with self._connect() as connection:
            object_rows = connection.execute(
                "SELECT content_hash, object_path FROM market_data_objects"
            ).fetchall()
        eligible_objects = tuple(
            Path(row["object_path"])
            for row in object_rows
            if row["content_hash"] not in future_references
        )
        eligible_day_paths = tuple(str(path) for path in targets if path.exists())
        eligible_object_paths = tuple(
            str(path) for path in eligible_objects if path.exists()
        )

        if dry_run:
            return CleanupReport(
                dry_run=True,
                retained_trading_dates=retained,
                eligible_day_paths=eligible_day_paths,
                deleted_day_paths=(),
                eligible_object_paths=eligible_object_paths,
                deleted_object_paths=(),
            )

        current_protection = retention_authority.protection_set(as_of_date=as_of_date)
        if current_protection != protection:
            raise RuntimeError(
                "retention protection changed during cleanup; refusing destructive cleanup"
            )

        for trading_day in expired_dates:
            retention_authority.assert_deletion_allowed(
                trading_date=trading_day,
                as_of_date=as_of_date,
            )
        with self._connect() as connection:
            run_rows = connection.execute(
                """
                SELECT run_id
                FROM market_data_manifests
                WHERE trading_date IN (SELECT value FROM json_each(?))
                """,
                (json.dumps(sorted(expired)),),
            ).fetchall()
        for row in run_rows:
            retention_authority.assert_deletion_allowed(
                run_id=row["run_id"],
                as_of_date=as_of_date,
            )
        for row in object_rows:
            path = Path(row["object_path"])
            if path in eligible_objects:
                retention_authority.assert_deletion_allowed(
                    content_hash=row["content_hash"],
                    as_of_date=as_of_date,
                )

        deleted_days: list[str] = []
        for target in targets:
            safe_target = self.assert_safe_delete_target(
                target, as_of_date=as_of_date
            )
            if safe_target.exists():
                shutil.rmtree(safe_target)
                deleted_days.append(str(safe_target))
        with self._connect() as connection:
            for trading_date_value in expired:
                connection.execute(
                    "DELETE FROM market_data_manifests WHERE trading_date = ?",
                    (trading_date_value,),
                )

        deleted_objects: list[str] = []
        for path in eligible_objects:
            resolved = path.resolve(strict=False)
            try:
                resolved.relative_to(self.objects_root.resolve(strict=False))
            except ValueError as exc:
                raise ValueError("object cleanup target escaped objects root") from exc
            if resolved.exists() and self._is_reparse_point(resolved):
                raise ValueError("refusing symlink or reparse-point object deletion")
            if resolved.exists():
                resolved.unlink()
                deleted_objects.append(str(resolved))
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM market_data_objects WHERE object_path = ?",
                    (str(path),),
                )
        return CleanupReport(
            dry_run=False,
            retained_trading_dates=retained,
            eligible_day_paths=eligible_day_paths,
            deleted_day_paths=tuple(deleted_days),
            eligible_object_paths=eligible_object_paths,
            deleted_object_paths=tuple(deleted_objects),
        )
