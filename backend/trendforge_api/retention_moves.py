"""R-HIST-04 M1C: durable movement journal + fencing + restart reconciler.

Metadata/control-plane milestone ONLY. This module remembers movement
intent, state, versions and worker authority. It implements NO evidence
copying, movement, compression, restore, source deletion or tier cleanup:
there is intentionally no shutil/os.replace/unlink/rename/move/delete
anywhere in this file.

Authority model: every mutation is a compare-and-swap over
``(state, state_version, worker_epoch)``. Zero affected rows means authority
is lost and the worker must stop. Wall-clock timestamps are audit metadata
only and never confer ownership.

All failures are loud and typed. Unknown failures default to blocking, never
to success.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .retention_tiering import TIERS, apply_tiering_schema

MOVE_MIGRATION_VERSION = "0025_rhist04_move_journal"

TERMINAL_STATES: tuple[str, ...] = ("COMPLETED", "FAILED_BLOCKING")

TRANSITIONS: dict[str, tuple[str, ...]] = {
    "PENDING_COPY": (
        "COPY_IN_PROGRESS",
        "FAILED_RETRYABLE",
        "FAILED_BLOCKING",
    ),
    "COPY_IN_PROGRESS": (
        "COPIED_UNVERIFIED",
        "FAILED_RETRYABLE",
        "FAILED_BLOCKING",
    ),
    "COPIED_UNVERIFIED": (
        "DESTINATION_VERIFIED",
        "FAILED_RETRYABLE",
        "FAILED_BLOCKING",
    ),
    "DESTINATION_VERIFIED": (
        "SOURCE_REMOVAL_PENDING",
        "DEST_VERIFIED_SOURCE_PRESENT",
        "FAILED_RETRYABLE",
        "FAILED_BLOCKING",
    ),
    "SOURCE_REMOVAL_PENDING": (
        "COMPLETED",
        "DEST_VERIFIED_SOURCE_PRESENT",
        "FAILED_RETRYABLE",
        "FAILED_BLOCKING",
    ),
    "DEST_VERIFIED_SOURCE_PRESENT": (
        "SOURCE_REMOVAL_PENDING",
        "COMPLETED",
        "FAILED_BLOCKING",
    ),
    "FAILED_RETRYABLE": (
        "COPY_IN_PROGRESS",
        "FAILED_BLOCKING",
    ),
}

ERROR_CODES: tuple[str, ...] = (
    "COPY_INTERRUPTED",
    "DESTINATION_UNVERIFIED",
    "SOURCE_UNPROVEN",
    "FENCE_LOST",
    "BACKEND_UNAVAILABLE",
    "INTEGRITY_FAILED",
    "DURABILITY_UNPROVEN",
    "RECONCILIATION_REQUIRED",
)

_OPERATION_KINDS: tuple[str, ...] = ("COPY",)

_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")

_IDENTITY_COLUMNS = (
    "move_id",
    "content_hash",
    "source_replica_id",
    "destination_tier",
    "destination_backend_id",
    "destination_object_key",
    "destination_locator",
    "destination_replica_id",
    "representation",
    "representation_version",
    "operation_kind",
)


class MoveAuthorityLostError(RuntimeError):
    """A CAS mutation affected zero rows: this worker lost authority."""


def _normalize_hash(content_hash: str) -> str:
    normalized = str(content_hash).casefold()
    if not _HASH_PATTERN.fullmatch(normalized):
        raise ValueError("content_hash must be a SHA-256 hex digest")
    return normalized


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _derive_move_id(fields: dict[str, str]) -> str:
    canonical = "|".join(
        fields[name] for name in _IDENTITY_COLUMNS if name != "move_id"
    )
    return "mov_" + hashlib.sha256(canonical.encode()).hexdigest()[:32]


def _derive_destination_replica_id(
    content_hash: str, tier: str, backend_id: str, locator: str
) -> str:
    canonical = f"{content_hash}|{tier}|{backend_id}|{locator}"
    return "rep_" + hashlib.sha256(canonical.encode()).hexdigest()[:32]


def apply_move_schema(connection: sqlite3.Connection) -> None:
    """Create the additive movement journal (idempotent, no deletes)."""
    apply_tiering_schema(connection)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS market_data_tier_moves (
            move_id TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            source_replica_id TEXT NOT NULL,
            destination_tier TEXT NOT NULL,
            destination_backend_id TEXT NOT NULL,
            destination_object_key TEXT NOT NULL,
            destination_locator TEXT NOT NULL,
            destination_replica_id TEXT NOT NULL,
            representation TEXT NOT NULL,
            representation_version TEXT NOT NULL,
            operation_kind TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN (
                'PENDING_COPY', 'COPY_IN_PROGRESS', 'COPIED_UNVERIFIED',
                'DESTINATION_VERIFIED', 'SOURCE_REMOVAL_PENDING',
                'DEST_VERIFIED_SOURCE_PRESENT', 'COMPLETED',
                'FAILED_RETRYABLE', 'FAILED_BLOCKING'
            )),
            state_version INTEGER NOT NULL CHECK(state_version >= 1),
            worker_epoch INTEGER NOT NULL CHECK(worker_epoch >= 0),
            attempt_count INTEGER NOT NULL CHECK(attempt_count >= 0),
            last_error_code TEXT CHECK(
                last_error_code IS NULL OR length(last_error_code) <= 64
            ),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(source_replica_id) REFERENCES rhist04_replicas(replica_id)
        );

        CREATE INDEX IF NOT EXISTS idx_tier_moves_hash
        ON market_data_tier_moves(content_hash);

        CREATE INDEX IF NOT EXISTS idx_tier_moves_state
        ON market_data_tier_moves(state);

        CREATE INDEX IF NOT EXISTS idx_tier_moves_source
        ON market_data_tier_moves(source_replica_id);

        CREATE TRIGGER IF NOT EXISTS trg_tier_moves_immutable_identity
        BEFORE UPDATE ON market_data_tier_moves
        BEGIN
            SELECT RAISE(ABORT, 'move identity is immutable')
            WHERE OLD.move_id IS NOT NEW.move_id
               OR OLD.content_hash IS NOT NEW.content_hash
               OR OLD.source_replica_id IS NOT NEW.source_replica_id
               OR OLD.destination_tier IS NOT NEW.destination_tier
               OR OLD.destination_backend_id IS NOT NEW.destination_backend_id
               OR OLD.destination_object_key IS NOT NEW.destination_object_key
               OR OLD.destination_locator IS NOT NEW.destination_locator
               OR OLD.destination_replica_id IS NOT NEW.destination_replica_id
               OR OLD.representation IS NOT NEW.representation
               OR OLD.representation_version IS NOT NEW.representation_version
               OR OLD.operation_kind IS NOT NEW.operation_kind;
        END;
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at)"
        " VALUES (?, ?, ?)",
        (
            MOVE_MIGRATION_VERSION,
            "R-HIST-04 durable movement journal and fencing",
            _utc_now(),
        ),
    )


@dataclass(frozen=True, slots=True)
class MoveRecord:
    move_id: str
    content_hash: str
    source_replica_id: str
    destination_tier: str
    destination_backend_id: str
    destination_object_key: str
    destination_locator: str
    destination_replica_id: str
    representation: str
    representation_version: str
    operation_kind: str
    state: str
    state_version: int
    worker_epoch: int
    attempt_count: int
    last_error_code: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class MoveClaim:
    move_id: str
    state: str
    state_version: int
    worker_epoch: int


@dataclass(frozen=True, slots=True)
class ReconcileEntry:
    move_id: str
    from_state: str
    to_state: str | None
    classification: str


@dataclass(frozen=True, slots=True)
class ReconcileReport:
    entries: tuple[ReconcileEntry, ...]
    processed: dict[str, int]


class MoveJournalStore:
    """Fenced durable movement journal over one market database file."""

    def __init__(self, *, db_path: Path) -> None:
        self.db_path = Path(db_path).expanduser()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def durability(self) -> dict[str, object]:
        """Observe (never assume) the effective journal durability policy."""
        with self._connect() as connection:
            mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            synchronous = int(connection.execute("PRAGMA synchronous").fetchone()[0])
            foreign_keys = int(connection.execute("PRAGMA foreign_keys").fetchone()[0])
        names = {0: "OFF", 1: "NORMAL", 2: "FULL", 3: "EXTRA"}
        return {
            "journal_mode": str(mode).lower(),
            "synchronous": names.get(synchronous, f"UNKNOWN({synchronous})"),
            "foreign_keys": foreign_keys == 1,
        }

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> MoveRecord:
        return MoveRecord(
            move_id=str(row["move_id"]),
            content_hash=str(row["content_hash"]),
            source_replica_id=str(row["source_replica_id"]),
            destination_tier=str(row["destination_tier"]),
            destination_backend_id=str(row["destination_backend_id"]),
            destination_object_key=str(row["destination_object_key"]),
            destination_locator=str(row["destination_locator"]),
            destination_replica_id=str(row["destination_replica_id"]),
            representation=str(row["representation"]),
            representation_version=str(row["representation_version"]),
            operation_kind=str(row["operation_kind"]),
            state=str(row["state"]),
            state_version=int(row["state_version"]),
            worker_epoch=int(row["worker_epoch"]),
            attempt_count=int(row["attempt_count"]),
            last_error_code=(
                str(row["last_error_code"])
                if row["last_error_code"] is not None
                else None
            ),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def get_move(self, move_id: str) -> MoveRecord | None:
        if not self.db_path.is_file():
            return None
        with self._connect() as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "market_data_tier_moves" not in tables:
                return None
            row = connection.execute(
                "SELECT * FROM market_data_tier_moves WHERE move_id = ?",
                (move_id,),
            ).fetchone()
        return self._record_from_row(row) if row is not None else None

    def create_move_intent(
        self,
        *,
        content_hash: str,
        source_replica_id: str,
        destination_tier: str,
        destination_backend_id: str,
        destination_object_key: str,
        destination_locator: str,
        representation: str,
        representation_version: str,
        operation_kind: str,
        destination_replica_id: str | None = None,
    ) -> MoveRecord:
        """Create (or return the identical existing) movement intent.

        No bytes are copied. The first creation starts PENDING_COPY; an exact
        replay returns the stored operation without resetting its progress.
        """
        normalized = _normalize_hash(content_hash)
        if destination_tier not in TIERS:
            raise ValueError(f"unknown destination tier {destination_tier!r}")
        if not destination_backend_id or not destination_object_key:
            raise ValueError("destination backend and object key are required")
        if not destination_locator or not Path(destination_locator).is_absolute():
            raise ValueError("destination locator must be an absolute path")
        if representation != "RAW":
            raise ValueError("M1C supports only RAW representation")
        if not representation_version:
            raise ValueError("representation_version is required")
        if operation_kind not in _OPERATION_KINDS:
            raise ValueError(f"unsupported operation_kind {operation_kind!r}")
        derived_replica = _derive_destination_replica_id(
            normalized, destination_tier, destination_backend_id, destination_locator
        )
        if destination_replica_id is not None and destination_replica_id != derived_replica:
            raise ValueError(
                "destination_replica_id disagrees with the deterministic identity"
            )
        # Identity is derived from every field except move_id itself.
        identity = {
            "content_hash": normalized,
            "source_replica_id": str(source_replica_id),
            "destination_tier": destination_tier,
            "destination_backend_id": destination_backend_id,
            "destination_object_key": destination_object_key,
            "destination_locator": destination_locator,
            "destination_replica_id": derived_replica,
            "representation": representation,
            "representation_version": representation_version,
            "operation_kind": operation_kind,
        }
        fields = {"move_id": "", **identity}
        move_id = _derive_move_id(fields)
        with self._connect() as connection:
            replica = connection.execute(
                "SELECT content_hash, state FROM rhist04_replicas "
                "WHERE replica_id = ?",
                (fields["source_replica_id"],),
            ).fetchone()
            if replica is None:
                raise ValueError(
                    f"unknown source replica {fields['source_replica_id']}"
                )
            if str(replica["content_hash"]) != normalized:
                raise ValueError(
                    "source replica H1 disagrees with requested content_hash"
                )
            if str(replica["state"]) == "REMOVED":
                raise ValueError(
                    f"source replica {fields['source_replica_id']} is REMOVED"
                )
            if str(replica["state"]) == "QUARANTINED":
                raise ValueError(
                    f"source replica {fields['source_replica_id']} is QUARANTINED"
                )
            source_locator = connection.execute(
                "SELECT locator, tier, backend_id FROM rhist04_replicas "
                "WHERE replica_id = ?",
                (fields["source_replica_id"],),
            ).fetchone()
            if (
                str(source_locator["tier"]) == destination_tier
                and str(source_locator["backend_id"]) == destination_backend_id
                and str(source_locator["locator"]) == destination_locator
            ) or destination_object_key == str(source_locator["locator"]):
                raise ValueError(
                    "destination aliases the source replica; same semantic "
                    "source/destination rejected"
                )
            now = _utc_now()
            connection.execute(
                """
                INSERT OR IGNORE INTO market_data_tier_moves(
                    move_id, content_hash, source_replica_id, destination_tier,
                    destination_backend_id, destination_object_key,
                    destination_locator, destination_replica_id, representation,
                    representation_version, operation_kind, state,
                    state_version, worker_epoch, attempt_count,
                    last_error_code, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    move_id,
                    normalized,
                    fields["source_replica_id"],
                    destination_tier,
                    destination_backend_id,
                    destination_object_key,
                    destination_locator,
                    derived_replica,
                    representation,
                    representation_version,
                    operation_kind,
                    "PENDING_COPY",
                    1,
                    0,
                    0,
                    None,
                    now,
                    now,
                ),
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM market_data_tier_moves WHERE move_id = ?",
                (move_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError("movement intent was not persisted")
        stored = self._record_from_row(row)
        for key in _IDENTITY_COLUMNS:
            if key == "move_id":
                continue
            if getattr(stored, key) != fields[key]:
                raise ValueError(
                    "move identity disagreement: stored intent differs from request"
                )
        return stored

    def claim_move(
        self, move_id: str, *, expected_state: str, expected_version: int
    ) -> MoveClaim:
        """Advance fencing authority without changing operation state."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE market_data_tier_moves
                SET worker_epoch = worker_epoch + 1,
                    state_version = state_version + 1,
                    attempt_count = attempt_count + 1,
                    updated_at = ?
                WHERE move_id = ?
                  AND state = ?
                  AND state_version = ?
                """,
                (_utc_now(), move_id, expected_state, expected_version),
            )
            connection.commit()
            if cursor.rowcount != 1:
                raise MoveAuthorityLostError(
                    f"claim rejected for {move_id}: expected "
                    f"({expected_state}, v{expected_version}) no longer current"
                )
            row = connection.execute(
                "SELECT state, state_version, worker_epoch "
                "FROM market_data_tier_moves WHERE move_id = ?",
                (move_id,),
            ).fetchone()
        assert row is not None
        return MoveClaim(
            move_id=move_id,
            state=str(row["state"]),
            state_version=int(row["state_version"]),
            worker_epoch=int(row["worker_epoch"]),
        )

    def transition_move(
        self,
        move_id: str,
        *,
        expected_state: str,
        expected_version: int,
        worker_epoch: int,
        new_state: str,
        error_code: str | None = None,
    ) -> MoveRecord:
        """Move one legal edge under exact fencing authority."""
        allowed = TRANSITIONS.get(expected_state, ())
        if new_state not in allowed:
            raise ValueError(
                f"illegal transition {expected_state} -> {new_state} "
                f"for {move_id}"
            )
        if new_state in ("FAILED_RETRYABLE", "FAILED_BLOCKING"):
            if error_code not in ERROR_CODES:
                raise ValueError(
                    "failed transitions require a bounded typed error_code "
                    f"(one of {ERROR_CODES})"
                )
        elif error_code is not None:
            raise ValueError("only failed transitions carry an error_code")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE market_data_tier_moves
                SET state = ?,
                    state_version = state_version + 1,
                    last_error_code = ?,
                    updated_at = ?
                WHERE move_id = ?
                  AND state = ?
                  AND state_version = ?
                  AND worker_epoch = ?
                """,
                (
                    new_state,
                    error_code,
                    _utc_now(),
                    move_id,
                    expected_state,
                    expected_version,
                    worker_epoch,
                ),
            )
            connection.commit()
            if cursor.rowcount != 1:
                raise MoveAuthorityLostError(
                    f"transition rejected for {move_id}: fencing data "
                    f"({expected_state}, v{expected_version}, "
                    f"epoch {worker_epoch}) no longer current"
                )
            row = connection.execute(
                "SELECT * FROM market_data_tier_moves WHERE move_id = ?",
                (move_id,),
            ).fetchone()
        assert row is not None
        return self._record_from_row(row)

    def reconcile(self, *, limit: int = 100) -> ReconcileReport:
        """Classify incomplete operations after restart; never invent progress.

        COPY_IN_PROGRESS rows are recovered through the same fenced claim +
        transition path any worker uses, landing them in FAILED_RETRYABLE with
        a typed interruption code. Everything else is left untouched.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        entries: list[ReconcileEntry] = []
        processed: dict[str, int] = {}
        with self._connect() as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "market_data_tier_moves" not in tables:
                return ReconcileReport(entries=(), processed={})
            rows = connection.execute(
                """
                SELECT move_id, state FROM market_data_tier_moves
                WHERE state NOT IN ('COMPLETED', 'FAILED_BLOCKING')
                ORDER BY created_at, move_id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            targets = [(str(row["move_id"]), str(row["state"])) for row in rows]
        for move_id, state in targets:
            try:
                classification, to_state = self._reconcile_one(move_id, state)
            except Exception as exc:  # fail closed per move, keep reconciling
                classification, to_state = "BLOCKED", None
                _ = exc
            entries.append(
                ReconcileEntry(
                    move_id=move_id,
                    from_state=state,
                    to_state=to_state,
                    classification=classification,
                )
            )
            processed[classification] = processed.get(classification, 0) + 1
        return ReconcileReport(entries=tuple(entries), processed=processed)

    def _reconcile_one(
        self, move_id: str, state: str
    ) -> tuple[str, str | None]:
        if state == "PENDING_COPY":
            return "NO_ACTION", None
        if state == "COPY_IN_PROGRESS":
            stored = self.get_move(move_id)
            if stored is None or stored.state != "COPY_IN_PROGRESS":
                return "BLOCKED", None
            claim = self.claim_move(
                move_id,
                expected_state="COPY_IN_PROGRESS",
                expected_version=stored.state_version,
            )
            self.transition_move(
                move_id,
                expected_state="COPY_IN_PROGRESS",
                expected_version=claim.state_version,
                worker_epoch=claim.worker_epoch,
                new_state="FAILED_RETRYABLE",
                error_code="COPY_INTERRUPTED",
            )
            return "RECOVERED_RETRYABLE", "FAILED_RETRYABLE"
        if state in ("COPIED_UNVERIFIED", "DESTINATION_VERIFIED"):
            return "REQUIRES_DESTINATION_REPROOF", None
        if state == "SOURCE_REMOVAL_PENDING":
            return "REQUIRES_SOURCE_REPROOF", None
        if state == "DEST_VERIFIED_SOURCE_PRESENT":
            return "SAFE_REDUNDANCY", None
        if state == "FAILED_RETRYABLE":
            return "NO_ACTION", None
        return "BLOCKED", None


__all__ = [
    "ERROR_CODES",
    "MOVE_MIGRATION_VERSION",
    "MoveAuthorityLostError",
    "MoveClaim",
    "MoveJournalStore",
    "MoveRecord",
    "ReconcileEntry",
    "ReconcileReport",
    "TERMINAL_STATES",
    "TRANSITIONS",
    "apply_move_schema",
]
