"""R-HIST-04 M1B: exact-H1 replica catalog and canonical evidence resolver.

Historical evidence is identified by immutable semantic identity
(``content_hash`` H1), never by physical storage location. This module owns
the single canonical read path from H1 to verified bytes:

```text
reader -> content_hash H1 -> RetentionTieringStore -> VERIFIED exact replica
```

Legacy locators (``object_path``/``objectPath``/``lastGoodPath``) remain
provenance only. A legacy file may satisfy a read only as a compatibility
candidate when H1 has no replica records yet, and only after no-follow
regular-file, root-containment, size and SHA-256 proof.

Reads never write: no schema creation, no backfill, no repair, no H2 or
latest-data substitution. Every resolution failure raises ``OSError`` so
existing reader failure handling keeps failing closed.

M1B scope only: NO movement, NO deletion, NO restore, NO compression APIs.
There is intentionally no ``shutil``/``os.replace``/``unlink`` in this file.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

TIERING_MIGRATION_VERSION = "0024_rhist04_replica_catalog"

TIERS: tuple[str, ...] = ("HOT", "WARM", "COLD")
_TIER_RANK = {tier: index for index, tier in enumerate(TIERS)}

STATES: tuple[str, ...] = (
    "DISCOVERED",
    "VERIFIED",
    "RETIRING",
    "QUARANTINED",
    "REMOVED",
)

DEFAULT_MAX_OBJECT_BYTES = 64 * 1024 * 1024

_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
_NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)


def _normalize_hash(content_hash: str) -> str:
    normalized = str(content_hash).casefold()
    if not _HASH_PATTERN.fullmatch(normalized):
        raise ValueError("content_hash must be a SHA-256 hex digest")
    return normalized


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def apply_tiering_schema(connection: sqlite3.Connection) -> None:
    """Create the additive R-HIST-04 replica catalog (idempotent, no deletes)."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rhist04_replicas (
            replica_id TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            tier TEXT NOT NULL,
            backend_id TEXT NOT NULL,
            locator TEXT NOT NULL,
            failure_domain TEXT NOT NULL,
            backend_version_token TEXT NOT NULL,
            representation TEXT NOT NULL,
            representation_version TEXT NOT NULL,
            storage_hash TEXT NOT NULL,
            logical_size_bytes INTEGER NOT NULL CHECK(logical_size_bytes >= 0),
            stored_size_bytes INTEGER NOT NULL CHECK(stored_size_bytes >= 0),
            state TEXT NOT NULL,
            state_version INTEGER NOT NULL DEFAULT 1,
            verified_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            quarantine_reason TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_rhist04_replicas_hash
        ON rhist04_replicas(content_hash);

        CREATE TABLE IF NOT EXISTS rhist04_store_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at)"
        " VALUES (?, ?, ?)",
        (
            TIERING_MIGRATION_VERSION,
            "R-HIST-04 exact-H1 replica catalog and store metadata",
            _utc_now(),
        ),
    )


def record_objects_root(connection: sqlite3.Connection, objects_root: Path) -> None:
    """Remember the legacy object root for this database (first writer wins)."""
    connection.execute(
        "INSERT OR IGNORE INTO rhist04_store_meta(key, value) VALUES (?, ?)",
        ("objects_root", str(objects_root)),
    )


@dataclass(frozen=True, slots=True)
class ReplicaRecord:
    replica_id: str
    content_hash: str
    tier: str
    backend_id: str
    locator: str
    failure_domain: str
    representation: str
    stored_size_bytes: int
    state: str
    state_version: int
    verified_at: str


@dataclass(frozen=True, slots=True)
class ExactVerification:
    content_hash: str
    available: bool
    tier: str | None
    replica_id: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class ShadowComparison:
    content_hash: str
    legacy_hash: str | None
    replica_hash: str | None
    replica_id: str | None
    equal: bool


class RetentionTieringStore:
    """Canonical exact-H1 evidence resolver over one market-data database."""

    def __init__(self, *, objects_root: Path, db_path: Path) -> None:
        self.objects_root = objects_root.expanduser()
        self.db_path = db_path.expanduser()

    @classmethod
    def tiering_for_connection(
        cls, connection: sqlite3.Connection
    ) -> RetentionTieringStore:
        """Build a resolver from an open market-database connection."""
        try:
            entries = connection.execute("PRAGMA database_list").fetchall()
        except sqlite3.Error as exc:
            raise OSError(
                f"OBJECT_ROOT_UNKNOWN: cannot locate database file ({exc})"
            ) from exc
        main = next((row for row in entries if row[1] == "main"), None)
        db_file = str(main[2]) if main is not None else ""
        if not db_file:
            raise OSError(
                "OBJECT_ROOT_UNKNOWN: in-memory database has no object root"
            )
        return cls.tiering_for_db(Path(db_file))

    @classmethod
    def tiering_for_db(
        cls, db_path: Path, *, objects_root: Path | None = None
    ) -> RetentionTieringStore:
        """Resolve the legacy object root from explicit config or store metadata."""
        if objects_root is not None:
            return cls(objects_root=objects_root, db_path=db_path)
        resolved = Path(db_path).expanduser()
        if not resolved.is_file():
            raise OSError(
                f"OBJECT_ROOT_UNKNOWN: no database file at {resolved} "
                "and no explicit objects root"
            )
        with sqlite3.connect(resolved) as connection:
            connection.row_factory = sqlite3.Row
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "rhist04_store_meta" not in tables:
                raise OSError(
                    "OBJECT_ROOT_UNKNOWN: rhist04_store_meta absent; "
                    "legacy root cannot be proven"
                )
            row = connection.execute(
                "SELECT value FROM rhist04_store_meta WHERE key = 'objects_root'"
            ).fetchone()
        if row is None:
            raise OSError(
                "OBJECT_ROOT_UNKNOWN: objects_root not recorded for this database"
            )
        return cls(objects_root=Path(str(row["value"])), db_path=resolved)

    # -- low-level helpers -------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _tables(self, connection: sqlite3.Connection) -> set[str]:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    def _replica_rows(
        self, connection: sqlite3.Connection, content_hash: str
    ) -> list[sqlite3.Row]:
        if "rhist04_replicas" not in self._tables(connection):
            return []
        return connection.execute(
            "SELECT * FROM rhist04_replicas WHERE content_hash = ?",
            (content_hash,),
        ).fetchall()

    def _legacy_row(
        self, connection: sqlite3.Connection, content_hash: str
    ) -> sqlite3.Row | None:
        if "market_data_objects" not in self._tables(connection):
            return None
        return connection.execute(
            "SELECT object_path, size_bytes FROM market_data_objects "
            "WHERE content_hash = ?",
            (content_hash,),
        ).fetchone()

    @staticmethod
    def _contained(path: Path, root: Path) -> Path | None:
        """Resolve without following a final symlink; require root containment."""
        if path.is_symlink():
            return None
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(root.resolve(strict=False))
        except ValueError:
            return None
        if resolved.is_symlink():
            return None
        return resolved

    def _open_no_follow(self, path: Path) -> int:
        """Open a regular file without following symlinks; return the fd."""
        binary = getattr(os, "O_BINARY", 0)
        if _NO_FOLLOW:
            return os.open(path, os.O_RDONLY | _NO_FOLLOW | binary)
        if path.is_symlink():
            raise OSError(f"LEGACY_LOCATOR_REJECTED: symlink not allowed: {path}")
        return os.open(path, os.O_RDONLY | binary)

    def _prove_bytes(
        self,
        path: Path,
        *,
        content_hash: str,
        expected_size: int | None,
        max_bytes: int,
        locator_kind: str,
    ) -> bytes:
        """Read exactly the bytes at path and prove they are H1."""
        fd = self._open_no_follow(path)
        try:
            size = os.fstat(fd).st_size
            if expected_size is not None and size != expected_size:
                raise OSError(
                    f"REPLICA_INTEGRITY_FAILED: {locator_kind} size {size} "
                    f"!= recorded {expected_size} for {content_hash[:12]}"
                )
            if size > max_bytes:
                raise OSError(
                    f"OBJECT_TOO_LARGE: {locator_kind} size {size} "
                    f"exceeds bound {max_bytes}"
                )
            chunks: list[bytes] = []
            remaining = max_bytes + 1
            while remaining > 0:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
        finally:
            os.close(fd)
        payload = b"".join(chunks)
        if len(payload) > max_bytes:
            raise OSError(
                f"OBJECT_TOO_LARGE: {locator_kind} grew past bound {max_bytes} "
                "during read"
            )
        if len(payload) != size:
            raise OSError(
                f"REPLICA_INTEGRITY_FAILED: {locator_kind} changed during read "
                f"for {content_hash[:12]}"
            )
        # The returned buffer itself is hashed: a same-length in-place mutation
        # between any earlier check and this read cannot escape as trusted bytes.
        if hashlib.sha256(payload).hexdigest() != content_hash:
            raise OSError(
                f"REPLICA_INTEGRITY_FAILED: {locator_kind} bytes do not hash "
                f"to {content_hash[:12]}"
            )
        return payload

    def _prove_legacy(
        self, raw_locator: str, *, content_hash: str, max_bytes: int
    ) -> bytes:
        unresolved = Path(raw_locator).expanduser()
        contained = self._contained(unresolved, self.objects_root)
        if contained is None:
            raise OSError(
                f"LEGACY_LOCATOR_REJECTED: {raw_locator} escapes the legacy "
                "object root or is a symlink"
            )
        expected_size: int | None = None
        if self.db_path.is_file():
            with self._connect() as connection:
                row = self._legacy_row(connection, content_hash)
                if row is not None:
                    expected_size = int(row["size_bytes"])
        return self._prove_bytes(
            contained,
            content_hash=content_hash,
            expected_size=expected_size,
            max_bytes=max_bytes,
            locator_kind="legacy locator",
        )

    def _prove_replica(
        self, record: ReplicaRecord, *, max_bytes: int
    ) -> bytes:
        locator = Path(record.locator).expanduser()
        if not locator.is_absolute():
            raise OSError(
                f"REPLICA_INTEGRITY_FAILED: replica {record.replica_id} "
                "locator is not absolute"
            )
        if locator.is_symlink():
            raise OSError(
                f"REPLICA_INTEGRITY_FAILED: replica {record.replica_id} "
                "locator is a symlink"
            )
        # The physical file must match the recorded stored size; the logical
        # H1 identity is proven by hashing the returned buffer itself.
        return self._prove_bytes(
            locator,
            content_hash=record.content_hash,
            expected_size=record.stored_size_bytes,
            max_bytes=max_bytes,
            locator_kind=f"replica {record.replica_id}",
        )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> ReplicaRecord:
        return ReplicaRecord(
            replica_id=str(row["replica_id"]),
            content_hash=str(row["content_hash"]),
            tier=str(row["tier"]),
            backend_id=str(row["backend_id"]),
            locator=str(row["locator"]),
            failure_domain=str(row["failure_domain"]),
            representation=str(row["representation"]),
            stored_size_bytes=int(row["stored_size_bytes"]),
            state=str(row["state"]),
            state_version=int(row["state_version"]),
            verified_at=str(row["verified_at"]),
        )

    @staticmethod
    def _typed_failure(action: str, content_hash: str, exc: OSError) -> OSError:
        """Map raw OS failures to typed resolver errors without masking typed ones."""
        message = str(exc)
        for token in (
            "EXACT_H1_UNAVAILABLE",
            "REPLICA_INTEGRITY_FAILED",
            "REPLICA_QUARANTINED",
            "LEGACY_LOCATOR_REJECTED",
            "OBJECT_TOO_LARGE",
            "OBJECT_ROOT_UNKNOWN",
        ):
            if token in message:
                return exc
        return OSError(
            f"EXACT_H1_UNAVAILABLE: {action} failed for {content_hash[:12]} "
            f"({type(exc).__name__}: {exc})"
        )

    # -- canonical read API ------------------------------------------------

    def list_replicas(self, content_hash: str) -> tuple[ReplicaRecord, ...]:
        normalized = _normalize_hash(content_hash)
        if not self.db_path.is_file():
            return ()
        with self._connect() as connection:
            rows = self._replica_rows(connection, normalized)
            records = [self._record_from_row(row) for row in rows]
        records.sort(key=lambda item: (_TIER_RANK.get(item.tier, 99), item.replica_id))
        return tuple(records)

    def _verified_candidates(self, content_hash: str) -> list[ReplicaRecord]:
        return [
            record
            for record in self.list_replicas(content_hash)
            if record.state == "VERIFIED"
        ]

    def read_object_exact(
        self, content_hash: str, *, max_bytes: int = DEFAULT_MAX_OBJECT_BYTES
    ) -> bytes:
        """Return exactly the H1 bytes or raise OSError (never H2/latest)."""
        normalized = _normalize_hash(content_hash)
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if not self.db_path.is_file():
            raise OSError(f"EXACT_H1_UNAVAILABLE: no database at {self.db_path}")

        candidates = self._verified_candidates(normalized)
        if candidates:
            for record in candidates:
                try:
                    return self._prove_replica(record, max_bytes=max_bytes)
                except OSError:
                    continue
            raise OSError(
                "EXACT_H1_UNAVAILABLE: no accessible VERIFIED replica "
                f"for {normalized[:12]}"
            )

        with self._connect() as connection:
            rows = self._replica_rows(connection, normalized)
            states = {str(row["state"]) for row in rows}
            legacy = self._legacy_row(connection, normalized)
        if rows:
            if "QUARANTINED" in states:
                raise OSError(
                    f"REPLICA_QUARANTINED: {normalized[:12]} has a quarantined "
                    "replica and no VERIFIED replica"
                )
            raise OSError(
                f"EXACT_H1_UNAVAILABLE: {normalized[:12]} has replica records "
                f"but none VERIFIED (states={sorted(states)})"
            )
        if legacy is None:
            raise OSError(
                f"EXACT_H1_UNAVAILABLE: no replica records and no legacy "
                f"object for {normalized[:12]}"
            )
        try:
            return self._prove_legacy(
                str(legacy["object_path"]),
                content_hash=normalized,
                max_bytes=max_bytes,
            )
        except OSError as exc:
            raise self._typed_failure(
                "legacy compatibility read", normalized, exc
            ) from exc

    def open_compatible_exact(self, content_hash: str) -> io.BytesIO:
        """Return a pinned in-memory stream over verified H1 bytes.

        A live file handle is never returned: the exact buffer handed to the
        caller is itself hash-proven, so post-verification mutation cannot
        escape as trusted historical bytes.
        """
        return io.BytesIO(self.read_object_exact(content_hash))

    def exact_object_available(self, content_hash: str) -> bool:
        """H1-specific availability probe; never raises, never substitutes."""
        try:
            normalized = _normalize_hash(content_hash)
        except ValueError:
            return False
        try:
            self.read_object_exact(normalized)
        except Exception:
            return False
        return True

    def verify_exact(self, content_hash: str) -> ExactVerification:
        """Resolve H1 once and report which replica satisfied the read."""
        normalized = _normalize_hash(content_hash)
        if not self.db_path.is_file():
            return ExactVerification(
                content_hash=normalized,
                available=False,
                tier=None,
                replica_id=None,
                reason=f"EXACT_H1_UNAVAILABLE: no database at {self.db_path}",
            )
        candidates = self._verified_candidates(normalized)
        if candidates:
            for record in candidates:
                try:
                    self._prove_replica(record, max_bytes=DEFAULT_MAX_OBJECT_BYTES)
                except OSError:
                    continue
                return ExactVerification(
                    content_hash=normalized,
                    available=True,
                    tier=record.tier,
                    replica_id=record.replica_id,
                    reason="VERIFIED",
                )
            return ExactVerification(
                content_hash=normalized,
                available=False,
                tier=None,
                replica_id=None,
                reason="EXACT_H1_UNAVAILABLE: no accessible VERIFIED replica",
            )
        with self._connect() as connection:
            rows = self._replica_rows(connection, normalized)
            states = {str(row["state"]) for row in rows}
            legacy = self._legacy_row(connection, normalized)
        if rows:
            if "QUARANTINED" in states:
                return ExactVerification(
                    content_hash=normalized,
                    available=False,
                    tier=None,
                    replica_id=None,
                    reason="REPLICA_QUARANTINED",
                )
            return ExactVerification(
                content_hash=normalized,
                available=False,
                tier=None,
                replica_id=None,
                reason=f"EXACT_H1_UNAVAILABLE: states={sorted(states)}",
            )
        if legacy is None:
            return ExactVerification(
                content_hash=normalized,
                available=False,
                tier=None,
                replica_id=None,
                reason="EXACT_H1_UNAVAILABLE: no replica records and no legacy object",
            )
        try:
            self._prove_legacy(
                str(legacy["object_path"]),
                content_hash=normalized,
                max_bytes=DEFAULT_MAX_OBJECT_BYTES,
            )
        except OSError as exc:
            typed = self._typed_failure(
                "legacy compatibility read", normalized, exc
            )
            return ExactVerification(
                content_hash=normalized,
                available=False,
                tier=None,
                replica_id=None,
                reason=str(typed),
            )
        return ExactVerification(
            content_hash=normalized,
            available=True,
            tier="HOT",
            replica_id=None,
            reason="LEGACY_COMPATIBILITY",
        )

    def shadow_compare_legacy_and_replica(
        self, content_hash: str
    ) -> ShadowComparison:
        """Compare legacy bytes vs strict replica bytes without writing anything."""
        normalized = _normalize_hash(content_hash)
        legacy_hash: str | None = None
        replica_hash: str | None = None
        replica_id: str | None = None
        if self.db_path.is_file():
            with self._connect() as connection:
                legacy = self._legacy_row(connection, normalized)
            if legacy is not None:
                try:
                    legacy_hash = hashlib.sha256(
                        self._prove_legacy(
                            str(legacy["object_path"]),
                            content_hash=normalized,
                            max_bytes=DEFAULT_MAX_OBJECT_BYTES,
                        )
                    ).hexdigest()
                except OSError:
                    legacy_hash = None
        for record in self._verified_candidates(normalized):
            try:
                replica_hash = hashlib.sha256(
                    self._prove_replica(
                        record, max_bytes=DEFAULT_MAX_OBJECT_BYTES
                    )
                ).hexdigest()
            except OSError:
                continue
            replica_id = record.replica_id
            break
        return ShadowComparison(
            content_hash=normalized,
            legacy_hash=legacy_hash,
            replica_hash=replica_hash,
            replica_id=replica_id,
            equal=legacy_hash is not None
            and legacy_hash == normalized
            and replica_hash == normalized,
        )

    # -- explicit byte-proven backfill (no auto-backfill from metadata) -----

    def adopt_legacy_as_replica(
        self,
        content_hash: str,
        *,
        tier: str,
        backend_id: str,
        failure_domain: str,
        locator: Path | str | None = None,
        backend_version_token: str = "local-v1",
    ) -> str:
        """Prove legacy bytes are H1 and register them as a VERIFIED replica.

        The bytes are opened and hashed; a database claim alone never creates
        a VERIFIED replica. Only RAW representation exists in M1B.
        """
        normalized = _normalize_hash(content_hash)
        if tier not in TIERS:
            raise ValueError(f"unknown tier {tier!r}; expected one of {TIERS}")
        if not backend_id or not failure_domain:
            raise ValueError("backend_id and failure_domain are required")
        if locator is None:
            if not self.db_path.is_file():
                raise OSError(
                    f"EXACT_H1_UNAVAILABLE: no database at {self.db_path}"
                )
            with self._connect() as connection:
                legacy = self._legacy_row(connection, normalized)
                if legacy is None:
                    raise OSError(
                        f"EXACT_H1_UNAVAILABLE: no legacy object for "
                        f"{normalized[:12]}"
                    )
                source = Path(str(legacy["object_path"])).expanduser()
                contained = self._contained(source, self.objects_root)
                if contained is None:
                    raise OSError(
                        "LEGACY_LOCATOR_REJECTED: legacy locator escapes the "
                        "legacy object root or is a symlink"
                    )
                source = contained
        else:
            source = Path(locator).expanduser()
            if not source.is_absolute():
                raise OSError("REPLICA_INTEGRITY_FAILED: replica locator not absolute")
            if source.is_symlink():
                raise OSError(
                    "REPLICA_INTEGRITY_FAILED: replica locator is a symlink"
                )
        payload = self._prove_bytes(
            source,
            content_hash=normalized,
            expected_size=None,
            max_bytes=DEFAULT_MAX_OBJECT_BYTES,
            locator_kind="backfill source",
        )
        replica_id = (
            "rep_"
            + hashlib.sha256(
                f"{normalized}|{tier}|{backend_id}|{source}".encode()
            ).hexdigest()[:32]
        )
        now = _utc_now()
        with self._connect() as connection:
            if "rhist04_replicas" not in self._tables(connection):
                raise OSError(
                    "OBJECT_ROOT_UNKNOWN: replica catalog absent; "
                    "run schema initialization first"
                )
            connection.execute(
                """
                INSERT OR IGNORE INTO rhist04_replicas(
                    replica_id, content_hash, tier, backend_id, locator,
                    failure_domain, backend_version_token, representation,
                    representation_version, storage_hash, logical_size_bytes,
                    stored_size_bytes, state, state_version, verified_at,
                    created_at, quarantine_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    replica_id,
                    normalized,
                    tier,
                    backend_id,
                    str(source),
                    failure_domain,
                    backend_version_token,
                    "RAW",
                    "v1",
                    hashlib.sha256(payload).hexdigest(),
                    len(payload),
                    len(payload),
                    "VERIFIED",
                    1,
                    now,
                    now,
                    None,
                ),
            )
            connection.commit()
        return replica_id

    def register_verified_replica(
        self,
        content_hash: str,
        *,
        tier: str,
        backend_id: str,
        locator: Path | str,
        failure_domain: str,
        backend_version_token: str = "local-v1",
        initial_state: str = "VERIFIED",
    ) -> str:
        """Register an independently proven destination as a replica row.

        The bytes at ``locator`` are opened and hashed here; a caller claim
        alone never creates a row. Identity uses the same deterministic
        scheme as :meth:`adopt_legacy_as_replica` so journal and catalog
        agree. Only RAW representation exists (M5 owns codecs).
        """
        normalized = _normalize_hash(content_hash)
        if tier not in TIERS:
            raise ValueError(f"unknown tier {tier!r}; expected one of {TIERS}")
        if not backend_id or not failure_domain:
            raise ValueError("backend_id and failure_domain are required")
        if initial_state not in STATES:
            raise ValueError(f"unknown state {initial_state!r}")
        source = Path(locator).expanduser()
        if not source.is_absolute():
            raise OSError("REPLICA_INTEGRITY_FAILED: replica locator not absolute")
        if source.is_symlink():
            raise OSError(
                "REPLICA_INTEGRITY_FAILED: replica locator is a symlink"
            )
        payload = self._prove_bytes(
            source,
            content_hash=normalized,
            expected_size=None,
            max_bytes=DEFAULT_MAX_OBJECT_BYTES,
            locator_kind="registration source",
        )
        replica_id = (
            "rep_"
            + hashlib.sha256(
                f"{normalized}|{tier}|{backend_id}|{source}".encode()
            ).hexdigest()[:32]
        )
        now = _utc_now()
        with self._connect() as connection:
            if "rhist04_replicas" not in self._tables(connection):
                raise OSError(
                    "OBJECT_ROOT_UNKNOWN: replica catalog absent; "
                    "run schema initialization first"
                )
            connection.execute(
                """
                INSERT OR IGNORE INTO rhist04_replicas(
                    replica_id, content_hash, tier, backend_id, locator,
                    failure_domain, backend_version_token, representation,
                    representation_version, storage_hash, logical_size_bytes,
                    stored_size_bytes, state, state_version, verified_at,
                    created_at, quarantine_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    replica_id,
                    normalized,
                    tier,
                    backend_id,
                    str(source),
                    failure_domain,
                    backend_version_token,
                    "RAW",
                    "v1",
                    hashlib.sha256(payload).hexdigest(),
                    len(payload),
                    len(payload),
                    initial_state,
                    1,
                    now,
                    now,
                    None,
                ),
            )
            connection.commit()
        return replica_id

    def set_replica_state(
        self,
        replica_id: str,
        *,
        expected_state: str,
        new_state: str,
        expected_version: int | None = None,
        quarantine_reason: str | None = None,
    ) -> bool:
        """Compare-and-swap a replica state; False when authority is lost."""
        if expected_state not in STATES:
            raise ValueError(f"unknown state {expected_state!r}")
        if new_state not in STATES:
            raise ValueError(f"unknown state {new_state!r}")
        if new_state == "QUARANTINED" and not quarantine_reason:
            raise ValueError("quarantine_reason is required to quarantine")
        with self._connect() as connection:
            if "rhist04_replicas" not in self._tables(connection):
                return False
            cursor = connection.execute(
                """
                UPDATE rhist04_replicas
                SET state = ?, state_version = state_version + 1,
                    quarantine_reason = ?
                WHERE replica_id = ?
                  AND state = ?
                  AND (? IS NULL OR state_version = ?)
                """,
                (
                    new_state,
                    quarantine_reason,
                    replica_id,
                    expected_state,
                    expected_version,
                    expected_version,
                ),
            )
            connection.commit()
            return cursor.rowcount == 1


__all__ = [
    "DEFAULT_MAX_OBJECT_BYTES",
    "ExactVerification",
    "ReplicaRecord",
    "RetentionTieringStore",
    "ShadowComparison",
    "STATES",
    "TIERING_MIGRATION_VERSION",
    "TIERS",
    "apply_tiering_schema",
    "record_objects_root",
]
