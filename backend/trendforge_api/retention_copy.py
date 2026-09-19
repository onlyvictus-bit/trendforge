"""R-HIST-04 M2A: RAW local/scratch HOT->WARM COPY-ONLY replication.

Creates a second exact H1. Never deletes, moves, renames, or repoints the
first one: this module contains no evidence-source deletion capability at
all (no shutil.move/rename, no unlink/rmdir of evidence, no
SOURCE_REMOVAL_PENDING advancement).

Authority comes exclusively from the M1C movement journal
(``MoveJournalStore``): intent -> claim -> fenced CAS transitions. A stale
worker fails at the journal and performs no filesystem effects.

Crash model: the process may die after any step. Retries converge because
the destination identity is deterministic, publication is atomic, and every
recovery path re-verifies bytes before advancing the journal.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat as stat_module
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .retention_moves import MoveAuthorityLostError, MoveClaim, MoveJournalStore
from .retention_tiering import (
    DEFAULT_MAX_OBJECT_BYTES,
    RetentionTieringStore,
)

_CHUNK_SIZE = 256 * 1024
_TEMP_SUFFIX = ".part"
# Windows CRT file descriptors default to text mode (CRLF translation),
# which silently corrupts binary evidence. Every data fd takes O_BINARY
# where the platform provides it (no-op on POSIX).
_BINARY = getattr(os, "O_BINARY", 0)


class CopyError(Exception):
    """A fenced copy failure. ``code`` is a stable failure category."""

    def __init__(self, code: str, detail: str = "", *, move_id: str | None = None):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail
        self.move_id = move_id


class CopyInjectedFault(Exception):
    """Test/recovery-driver seam: simulates a crash at a named boundary."""


@dataclass(frozen=True, slots=True)
class LocalBackendCapabilities:
    exclusive_create: bool
    file_fsync: bool
    atomic_publish: bool
    readback_ok: bool
    directory_fsync: bool
    durable_publish_proven: bool
    detail: str


@dataclass(frozen=True, slots=True)
class CopyResult:
    move_id: str
    content_hash: str
    source_replica_id: str
    destination_replica_id: str
    destination_locator: str
    bytes_copied: int
    chunks: int
    state: str
    worker_epoch: int
    directory_fsync_proven: bool
    independent_failure_domain: bool


def probe_local_capabilities(warm_root: Path) -> LocalBackendCapabilities:
    """Prove the local publish primitives with a real temp-file cycle.

    Only files this probe creates are removed, tracked by exact path.
    """
    root = Path(warm_root).expanduser()
    probe_dir = root / ".capability-probe"
    created: list[Path] = []
    flags = {
        "exclusive_create": False,
        "file_fsync": False,
        "atomic_publish": False,
        "readback_ok": False,
        "directory_fsync": False,
    }
    detail = "ok"
    try:
        probe_dir.mkdir(parents=True, exist_ok=True)
        nonce = uuid.uuid4().hex[:12]
        temp = probe_dir / f".probe-{nonce}.part"
        final = probe_dir / f"probe-{nonce}.bin"
        created.extend([temp, final])
        payload = b"capability-probe" * 64
        try:
            fd = os.open(
                temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | _BINARY, 0o600
            )
        except OSError as exc:
            detail = f"exclusive_create failed: {exc}"
            return LocalBackendCapabilities(
                **flags, durable_publish_proven=False, detail=detail
            )
        flags["exclusive_create"] = True
        try:
            with os.fdopen(fd, "wb", closefd=True) as handle:
                handle.write(payload)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError as exc:
                    detail = f"file_fsync failed: {exc}"
                    return LocalBackendCapabilities(
                        **flags, durable_publish_proven=False, detail=detail
                    )
            flags["file_fsync"] = True
            try:
                os.replace(temp, final)
            except OSError as exc:
                detail = f"atomic_publish failed: {exc}"
                return LocalBackendCapabilities(
                    **flags, durable_publish_proven=False, detail=detail
                )
            flags["atomic_publish"] = True
            try:
                with open(final, "rb") as handle:
                    seen = handle.read()
            except OSError as exc:
                detail = f"readback failed: {exc}"
                return LocalBackendCapabilities(
                    **flags, durable_publish_proven=False, detail=detail
                )
            if seen != payload:
                detail = "readback bytes differ"
                return LocalBackendCapabilities(
                    **flags, durable_publish_proven=False, detail=detail
                )
            flags["readback_ok"] = True
            flags["directory_fsync"] = _fsync_dir(probe_dir)
        finally:
            for path in created:
                try:
                    if path.is_file() and not path.is_symlink():
                        path.unlink()
                except OSError:
                    pass
        try:
            probe_dir.rmdir()
        except OSError:
            pass
        return LocalBackendCapabilities(
            **flags, durable_publish_proven=True, detail="ok"
        )
    except OSError as exc:
        return LocalBackendCapabilities(
            **flags, durable_publish_proven=False, detail=f"probe failed: {exc}"
        )


def _fsync_dir(directory: Path) -> bool:
    """Best-effort directory fsync; False where the platform forbids it."""
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return False
    try:
        os.fsync(fd)
    except OSError:
        return False
    finally:
        os.close(fd)
    return True


def _destination_paths(
    warm_root: Path, content_hash: str, suffix: str
) -> tuple[Path, Path]:
    """Deterministic (shard dir, final file) destination identity."""
    shard = Path(warm_root).expanduser() / content_hash[:2]
    return shard, shard / f"{content_hash}{suffix}"


def _source_suffix(source_locator: str) -> str:
    suffix = Path(source_locator).suffix
    if suffix and re.fullmatch(r"\.[A-Za-z0-9]{1,12}", suffix):
        return suffix.casefold()
    return ".bin"


def _cleanup_temp(temp_path: Path, warm_root: Path) -> None:
    """Remove M2A-owned temp debris only; reject anything else."""
    root = Path(warm_root).expanduser().resolve(strict=False)
    candidate = Path(temp_path).expanduser()
    if candidate.suffix != _TEMP_SUFFIX:
        raise CopyError("UNSAFE_DESTINATION", f"refusing non-temp path: {candidate}")
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise CopyError(
            "UNSAFE_DESTINATION", f"temp path escapes warm root: {candidate}"
        ) from exc
    try:
        if candidate.is_file() and not candidate.is_symlink():
            candidate.unlink()
    except OSError:
        pass


def _stat_identity(path: Path) -> tuple[int, int]:
    """Return (st_dev, st_ino); fail closed where identity is unavailable."""
    try:
        info = path.stat()
        dev, ino = info.st_dev, info.st_ino
    except (OSError, AttributeError) as exc:
        raise CopyError(
            "UNSAFE_DESTINATION", f"cannot establish file identity for {path}: {exc}"
        )
    if not dev and not ino:
        raise CopyError(
            "UNSAFE_DESTINATION",
            f"platform exposes no file identity for {path}",
        )
    return dev, ino


def copy_hot_to_warm(
    *,
    journal: MoveJournalStore,
    tiering: RetentionTieringStore,
    content_hash: str,
    warm_root: Path | str,
    backend_id: str = "local-warm",
    failure_domain: str = "local-single-failure-domain",
    source_replica_id: str | None = None,
    chunk_size: int = _CHUNK_SIZE,
    max_bytes: int = DEFAULT_MAX_OBJECT_BYTES,
    capabilities: LocalBackendCapabilities | None = None,
    claim: MoveClaim | None = None,
    inject_fault_at: str | None = None,
    on_checkpoint: Callable[[str], None] | None = None,
) -> CopyResult:
    """Copy one VERIFIED RAW HOT H1 to an independent VERIFIED WARM file.

    Scratch/local only. Ends at DESTINATION_VERIFIED (or COPIED_UNVERIFIED
    when the backend cannot prove durable publish). Never advances to
    SOURCE_REMOVAL_PENDING or COMPLETED. ``inject_fault_at`` /
    ``on_checkpoint`` are explicit test/recovery-driver seams.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    root = Path(warm_root).expanduser()
    if not str(root) or not root.is_absolute():
        raise CopyError("UNSAFE_DESTINATION", "warm root must be an absolute path")
    if root.is_symlink():
        raise CopyError("UNSAFE_DESTINATION", "warm root must not be a symlink")

    caps = capabilities if capabilities is not None else probe_local_capabilities(root)

    normalized = content_hash.casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError("content_hash must be a SHA-256 hex digest")

    source = _resolve_source(tiering, normalized, source_replica_id)
    suffix = _source_suffix(source.locator)
    shard_dir, final_path = _destination_paths(root, normalized, suffix)
    destination_object_key = f"warm/{normalized[:2]}/{normalized}{suffix}"
    destination_locator = str(final_path)

    intent = journal.create_move_intent(
        content_hash=normalized,
        source_replica_id=source.replica_id,
        destination_tier="WARM",
        destination_backend_id=backend_id,
        destination_object_key=destination_object_key,
        destination_locator=destination_locator,
        representation="RAW",
        representation_version="v1",
        operation_kind="COPY",
    )
    entry_snapshot = (intent.state, intent.state_version)
    if claim is not None and (
        claim.move_id != intent.move_id
        or claim.state != intent.state
        or claim.state_version != intent.state_version
        or claim.worker_epoch != intent.worker_epoch
    ):
        raise CopyError("STALE_WORKER", "supplied fencing token is not current",
                        move_id=intent.move_id)

    state = intent.state
    if state in ("SOURCE_REMOVAL_PENDING", "DEST_VERIFIED_SOURCE_PRESENT",
                 "COMPLETED"):
        raise CopyError("JOURNAL_CONFLICT",
                        f"refusing M2A copy from foreign state {state}",
                        move_id=intent.move_id)
    if state == "FAILED_BLOCKING":
        raise CopyError("JOURNAL_CONFLICT",
                        "operation is FAILED_BLOCKING; operator action required",
                        move_id=intent.move_id)
    try:
        if state == "DESTINATION_VERIFIED":
            return _adopt_completed(journal, tiering, intent, caps)
        if state == "COPY_IN_PROGRESS":
            _recover_interrupted(journal, intent.move_id)
            intent = _must_get(journal, intent.move_id)
        if intent.state == "COPIED_UNVERIFIED":
            return _finish_from_published(
                journal, tiering, intent, caps, normalized,
                inject_fault_at, on_checkpoint, max_bytes, failure_domain,
            )
        return _run_copy(
            journal, tiering, intent, source, caps, normalized,
            shard_dir, final_path,
            backend_id, failure_domain, chunk_size, max_bytes,
            inject_fault_at, on_checkpoint,
        )
    except CopyInjectedFault:
        raise
    except MoveAuthorityLostError as exc:
        raise CopyError("FENCE_REJECTED", str(exc), move_id=intent.move_id) from exc
    except CopyError as exc:
        if exc.move_id is None:
            exc.move_id = intent.move_id
        _record_failure_unless_untouched(journal, intent.move_id, entry_snapshot, exc)
        raise
    except Exception as exc:
        # Unknown failure: never success, never silent. Best-effort record,
        # then a loud typed conflict. (KeyboardInterrupt/SystemExit are not
        # Exception subclasses and propagate untouched.)
        try:
            _record_failure_unless_untouched(
                journal, intent.move_id, entry_snapshot,
                CopyError("JOURNAL_CONFLICT", str(exc), move_id=intent.move_id),
            )
        except Exception:
            pass
        raise CopyError(
            "JOURNAL_CONFLICT", f"unexpected {type(exc).__name__}: {exc}",
            move_id=intent.move_id,
        ) from exc


def _must_get(journal: MoveJournalStore, move_id: str):
    record = journal.get_move(move_id)
    if record is None:
        raise CopyError("JOURNAL_CONFLICT", f"movement {move_id} vanished",
                        move_id=move_id)
    return record


def _record_failure_unless_untouched(
    journal: MoveJournalStore,
    move_id: str,
    entry_snapshot: tuple[str, int],
    exc: CopyError,
) -> None:
    """Best-effort fenced failure recording.

    Skipped when this call never mutated the journal (entry snapshot intact:
    nothing of ours to record) or when the row already sits terminal (another
    recording owns it). Fencing loss while recording propagates instead of
    masking the original failure.
    """
    try:
        current = _must_get(journal, move_id)
    except CopyError:
        return
    if (current.state, current.state_version) == entry_snapshot:
        return
    if current.state in ("FAILED_BLOCKING", "FAILED_RETRYABLE",
                         "COMPLETED", "DESTINATION_VERIFIED"):
        return
    state, code = _failure_plan(exc)
    claim = journal.claim_move(
        move_id,
        expected_state=current.state,
        expected_version=current.state_version,
    )
    journal.transition_move(
        move_id,
        expected_state=current.state,
        expected_version=claim.state_version,
        worker_epoch=claim.worker_epoch,
        new_state=state,
        error_code=code,
    )


def _recover_interrupted(journal: MoveJournalStore, move_id: str) -> None:
    """Fenced recovery for an interrupted COPY_IN_PROGRESS (reconciler path)."""
    current = _must_get(journal, move_id)
    if current.state != "COPY_IN_PROGRESS":
        return
    claim = journal.claim_move(
        move_id,
        expected_state="COPY_IN_PROGRESS",
        expected_version=current.state_version,
    )
    journal.transition_move(
        move_id,
        expected_state="COPY_IN_PROGRESS",
        expected_version=claim.state_version,
        worker_epoch=claim.worker_epoch,
        new_state="FAILED_RETRYABLE",
        error_code="COPY_INTERRUPTED",
    )


def _checkpoint(
    name: str,
    inject_fault_at: str | None,
    on_checkpoint: Callable[[str], None] | None,
) -> None:
    if on_checkpoint is not None:
        on_checkpoint(name)
    if inject_fault_at == name:
        raise CopyInjectedFault(f"injected crash at {name}")


def _resolve_source(tiering: RetentionTieringStore, normalized: str,
                    source_replica_id: str | None):
    if source_replica_id is not None:
        candidates = [
            record for record in tiering.list_replicas(normalized)
            if record.replica_id == source_replica_id
        ]
        if not candidates:
            raise CopyError("SOURCE_H1_UNAVAILABLE",
                            f"source replica {source_replica_id} unknown")
        record = candidates[0]
    else:
        hots = [
            record for record in tiering.list_replicas(normalized)
            if record.tier == "HOT" and record.representation == "RAW"
            and record.state == "VERIFIED"
        ]
        if not hots:
            raise CopyError("SOURCE_H1_UNAVAILABLE",
                            f"no VERIFIED RAW HOT replica for {normalized[:12]}")
        record = sorted(hots, key=lambda item: item.replica_id)[0]
    if record.state != "VERIFIED":
        raise CopyError("SOURCE_H1_UNAVAILABLE",
                        f"source replica {record.replica_id} is {record.state}")
    if record.representation != "RAW":
        raise CopyError("SOURCE_H1_UNAVAILABLE",
                        f"source replica {record.replica_id} is not RAW")
    if record.content_hash != normalized:
        raise CopyError("SOURCE_HASH_MISMATCH",
                        "source replica H1 disagrees with request")
    return record


def _run_copy(
    journal: MoveJournalStore,
    tiering: RetentionTieringStore,
    intent,
    source,
    caps: LocalBackendCapabilities,
    normalized: str,
    shard_dir: Path,
    final_path: Path,
    backend_id: str,
    failure_domain: str,
    chunk_size: int,
    max_bytes: int,
    inject_fault_at: str | None,
    on_checkpoint: Callable[[str], None] | None,
) -> CopyResult:
    move_id = intent.move_id
    if intent.state not in ("PENDING_COPY", "FAILED_RETRYABLE"):
        raise CopyError("JOURNAL_CONFLICT",
                        f"cannot start copy from {intent.state}",
                        move_id=move_id)
    claim = journal.claim_move(
        move_id,
        expected_state=intent.state,
        expected_version=intent.state_version,
    )
    journal.transition_move(
        move_id,
        expected_state=intent.state,
        expected_version=claim.state_version,
        worker_epoch=claim.worker_epoch,
        new_state="COPY_IN_PROGRESS",
    )
    _checkpoint("after_claim", inject_fault_at, on_checkpoint)
    _inspect_destination(move_id, normalized, final_path, max_bytes)
    bytes_copied, chunks = _copy_bytes(
        move_id, tiering, source, caps,
        shard_dir, final_path, chunk_size, max_bytes,
        inject_fault_at, on_checkpoint,
    )
    return _finish_from_published(
        journal, tiering, _must_get(journal, move_id), caps, normalized,
        inject_fault_at, on_checkpoint, max_bytes, failure_domain,
        stream_stats=(bytes_copied, chunks),
    )


def _copy_bytes(
    move_id: str,
    tiering: RetentionTieringStore,
    source,
    caps: LocalBackendCapabilities,
    shard_dir: Path,
    final_path: Path,
    chunk_size: int,
    max_bytes: int,
    inject_fault_at: str | None,
    on_checkpoint: Callable[[str], None] | None,
) -> tuple[int, int]:
    """Stream source H1 to an exclusive temp file; return (bytes, chunks)."""
    if not caps.exclusive_create:
        raise CopyError("BACKEND_CAPABILITY_UNPROVEN",
                        "backend cannot prove exclusive temp creation",
                        move_id=move_id)
    try:
        shard_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CopyError("WRITE_FAILED", f"cannot create shard dir: {exc}",
                        move_id=move_id) from exc
    temp_path = shard_dir / f".{source.content_hash[:16]}.{uuid.uuid4().hex[:12]}.part"
    try:
        source_fd = os.open(
            source.locator,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | _BINARY,
        )
    except OSError as exc:
        raise CopyError("UNSAFE_SOURCE", f"cannot safely open source: {exc}",
                        move_id=move_id) from exc
    try:
        try:
            source_stat = os.fstat(source_fd)
        except OSError as exc:
            raise CopyError("UNSAFE_SOURCE", f"cannot stat source: {exc}",
                            move_id=move_id) from exc
        if not stat_module.S_ISREG(source_stat.st_mode):
            raise CopyError("UNSAFE_SOURCE", "source is not a regular file",
                            move_id=move_id)
        _checkpoint("before_stream", inject_fault_at, on_checkpoint)
        try:
            temp_fd = os.open(
                temp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | _BINARY, 0o600
            )
        except OSError as exc:
            raise CopyError("WRITE_FAILED", f"cannot create temp file: {exc}",
                            move_id=move_id) from exc
        try:
            _checkpoint("after_temp_create", inject_fault_at, on_checkpoint)
            hasher = hashlib.sha256()
            bytes_copied = 0
            chunks = 0
            while True:
                try:
                    chunk = os.read(source_fd, chunk_size)
                except OSError as exc:
                    raise CopyError("SOURCE_CHANGED_DURING_COPY",
                                    f"source read failed: {exc}",
                                    move_id=move_id) from exc
                if not chunk:
                    break
                if bytes_copied + len(chunk) > max_bytes:
                    raise CopyError("SOURCE_CHANGED_DURING_COPY",
                                    "source exceeds bound during copy",
                                    move_id=move_id)
                try:
                    os.write(temp_fd, chunk)
                except OSError as exc:
                    raise CopyError("WRITE_FAILED", f"temp write failed: {exc}",
                                    move_id=move_id) from exc
                hasher.update(chunk)
                bytes_copied += len(chunk)
                chunks += 1
                if inject_fault_at == "after_partial_write" and bytes_copied > 0:
                    raise CopyInjectedFault("injected crash at after_partial_write")
                if on_checkpoint is not None:
                    on_checkpoint("after_chunk")
            _checkpoint("after_stream_complete", inject_fault_at, on_checkpoint)
            if hasher.hexdigest() != source.content_hash:
                _cleanup_temp(temp_path, final_path.parent.parent)
                raise CopyError("SOURCE_CHANGED_DURING_COPY",
                                "consumed source bytes do not hash to H1",
                                move_id=move_id)
            try:
                # fsync through the write handle itself: on Windows a
                # read-only handle lacks the access needed to flush.
                os.fsync(temp_fd)
            except OSError as exc:
                raise CopyError("FSYNC_FAILED", f"temp fsync failed: {exc}",
                                move_id=move_id) from exc
            finally:
                # Closed before publish: Windows forbids renaming an open file.
                temp_fd = _close_quietly(temp_fd)
            _checkpoint("after_fsync", inject_fault_at, on_checkpoint)
            _publish_temp(move_id, temp_path, final_path)
            _checkpoint("after_publish", inject_fault_at, on_checkpoint)
            _fsync_dir_best_effort(final_path.parent)
            return bytes_copied, chunks
        finally:
            temp_fd = _close_quietly(temp_fd)
    finally:
        os.close(source_fd)


def _inspect_destination(
    move_id: str,
    normalized: str,
    final_path: Path,
    max_bytes: int,
) -> None:
    """Pre-stream destination triage (Case B adopt / C conflict / D unsafe)."""
    if final_path.is_symlink():
        raise CopyError("UNSAFE_DESTINATION",
                        "destination is a symlink", move_id=move_id)
    if not final_path.is_file():
        return
    hasher = hashlib.sha256()
    size = 0
    try:
        with open(final_path, "rb") as handle:
            while True:
                chunk = handle.read(262144)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise CopyError("DESTINATION_CONFLICT",
                                    "existing destination exceeds bound; preserved",
                                    move_id=move_id)
                hasher.update(chunk)
    except OSError as exc:
        raise CopyError("UNSAFE_DESTINATION",
                        f"cannot inspect destination: {exc}",
                        move_id=move_id) from exc
    if hasher.hexdigest() != normalized:
        raise CopyError("DESTINATION_CONFLICT",
                        "NO_CLOBBER_CONFLICT: existing destination is not H1; "
                        "preserved for investigation",
                        move_id=move_id)


def _publish_temp(
    move_id: str, temp_path: Path, final_path: Path,
) -> None:
    """Atomically publish temp; a racer-published file is left alone."""
    if final_path.exists() or final_path.is_symlink():
        return
    try:
        os.replace(temp_path, final_path)
    except OSError as exc:
        raise CopyError("PUBLISH_FAILED", f"atomic publish failed: {exc}",
                        move_id=move_id) from exc


def _close_quietly(fd: int) -> int:
    """Close a raw fd, swallowing errors; returns -1 as the spent marker."""
    if fd >= 0:
        try:
            os.close(fd)
        except OSError:
            pass
    return -1


def _fsync_dir_best_effort(directory: Path) -> bool:
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return False
    try:
        os.fsync(fd)
    except OSError:
        return False
    finally:
        os.close(fd)
    return True


def _readback_and_register(
    journal: MoveJournalStore,
    tiering: RetentionTieringStore,
    intent,
    backend_id: str,
    failure_domain: str,
    max_bytes: int,
    inject_fault_at: str | None,
    on_checkpoint: Callable[[str], None] | None,
    register_state: str = "VERIFIED",
) -> tuple[str, int]:
    """Independently re-read the published destination and catalog it.

    Returns (replica_id, verified byte count). With ``verify_only`` the row
    is still registered (idempotent adopt); registration always re-proves.
    """
    normalized = intent.content_hash
    final_path = Path(intent.destination_locator)
    _checkpoint("before_readback", inject_fault_at, on_checkpoint)
    if final_path.is_symlink():
        raise CopyError("UNSAFE_DESTINATION",
                        "published destination is a symlink",
                        move_id=intent.move_id)
    try:
        dest_fd = os.open(
            final_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | _BINARY
        )
    except OSError as exc:
        raise CopyError("DESTINATION_HASH_MISMATCH",
                        f"cannot reopen destination: {exc}",
                        move_id=intent.move_id) from exc
    try:
        try:
            dest_stat = os.fstat(dest_fd)
        except OSError as exc:
            raise CopyError("UNSAFE_DESTINATION",
                            f"cannot stat destination: {exc}",
                            move_id=intent.move_id) from exc
        if not stat_module.S_ISREG(dest_stat.st_mode):
            raise CopyError("UNSAFE_DESTINATION",
                            "published destination is not a regular file",
                            move_id=intent.move_id)
        hasher = hashlib.sha256()
        size = 0
        while True:
            _checkpoint("during_readback", inject_fault_at, on_checkpoint)
            try:
                chunk = os.read(dest_fd, 262144)
            except OSError as exc:
                raise CopyError("DESTINATION_HASH_MISMATCH",
                                f"destination read failed: {exc}",
                                move_id=intent.move_id) from exc
            if not chunk:
                break
            if size + len(chunk) > max_bytes:
                raise CopyError("DESTINATION_HASH_MISMATCH",
                                "destination exceeds bound on readback",
                                move_id=intent.move_id)
            hasher.update(chunk)
            size += len(chunk)
    finally:
        os.close(dest_fd)
    _checkpoint("after_readback", inject_fault_at, on_checkpoint)
    if hasher.hexdigest() != normalized:
        raise CopyError("DESTINATION_HASH_MISMATCH",
                        "published destination bytes do not hash to H1",
                        move_id=intent.move_id)
    source_stat = _source_identity(tiering, intent)
    if (dest_stat.st_dev, dest_stat.st_ino) != (0, 0) and (
        dest_stat.st_dev, dest_stat.st_ino
    ) == source_stat:
        raise CopyError("DESTINATION_HARDLINK",
                        "destination aliases the source file",
                        move_id=intent.move_id)
    _checkpoint("before_catalog", inject_fault_at, on_checkpoint)
    try:
        replica_id = tiering.register_verified_replica(
            normalized,
            tier="WARM",
            backend_id=backend_id,
            locator=str(final_path),
            failure_domain=failure_domain,
            initial_state=register_state,
        )
    except (OSError, ValueError) as exc:
        raise CopyError("CATALOG_PUBLICATION_FAILED", str(exc),
                        move_id=intent.move_id) from exc
    _checkpoint("after_catalog", inject_fault_at, on_checkpoint)
    return replica_id, size


def _source_identity(tiering: RetentionTieringStore, intent) -> tuple[int, int]:
    """Best-effort (dev, ino) of the source replica file for alias checks."""
    for record in tiering.list_replicas(intent.content_hash):
        if record.replica_id == intent.source_replica_id:
            try:
                info = os.stat(record.locator)
                return info.st_dev, info.st_ino
            except OSError:
                return -1, -1
    return -1, -1


def _finish_from_published(
    journal: MoveJournalStore,
    tiering: RetentionTieringStore,
    intent,
    caps: LocalBackendCapabilities,
    normalized: str,
    inject_fault_at: str | None,
    on_checkpoint: Callable[[str], None] | None,
    max_bytes: int,
    failure_domain: str,
    stream_stats: tuple[int, int] | None = None,
) -> CopyResult:
    """Adopt-or-verify an existing published destination, then close the op."""
    final_path = Path(intent.destination_locator)
    backend_id = intent.destination_backend_id
    register_state = "VERIFIED" if caps.durable_publish_proven else "DISCOVERED"
    if intent.state != "COPIED_UNVERIFIED":
        claim = journal.claim_move(
            intent.move_id,
            expected_state=intent.state,
            expected_version=intent.state_version,
        )
        journal.transition_move(
            intent.move_id,
            expected_state=intent.state,
            expected_version=claim.state_version,
            worker_epoch=claim.worker_epoch,
            new_state="COPIED_UNVERIFIED",
        )
        intent = _must_get(journal, intent.move_id)
    else:
        if final_path.is_symlink():
            raise CopyError("UNSAFE_DESTINATION",
                            "destination is a symlink", move_id=intent.move_id)
        if not final_path.is_file():
            raise CopyError("DESTINATION_HASH_MISMATCH",
                            "no published destination to adopt",
                            move_id=intent.move_id)
        with open(final_path, "rb") as handle:
            probe = handle.read()
        if hashlib.sha256(probe).hexdigest() != normalized:
            raise CopyError("DESTINATION_CONFLICT",
                            "NO_CLOBBER_CONFLICT: existing destination is not H1; "
                            "preserved for investigation",
                            move_id=intent.move_id)
        source_stat = _source_identity(tiering, intent)
        try:
            dest_stat = final_path.stat()
            dest_identity = (dest_stat.st_dev, dest_stat.st_ino)
        except OSError as exc:
            raise CopyError("UNSAFE_DESTINATION",
                            f"cannot stat destination: {exc}",
                            move_id=intent.move_id) from exc
        if dest_identity != (0, 0) and dest_identity == source_stat:
            raise CopyError("DESTINATION_HARDLINK",
                            "existing destination aliases the source file",
                            move_id=intent.move_id)
    replica_id, verified_size = _readback_and_register(
        journal, tiering, _must_get(journal, intent.move_id), backend_id,
        failure_domain, max_bytes, inject_fault_at, on_checkpoint,
        register_state,
    )
    return _close_verified(
        journal, tiering, intent.move_id, caps, normalized,
        replica_id, verified_size,
        0 if stream_stats is None else stream_stats[1],
        inject_fault_at, on_checkpoint,
    )


def _adopt_completed(
    journal: MoveJournalStore,
    tiering: RetentionTieringStore,
    intent,
    caps: LocalBackendCapabilities,
) -> CopyResult:
    """Idempotent success return for an already DESTINATION_VERIFIED op."""
    matches = [
        record for record in tiering.list_replicas(intent.content_hash)
        if record.replica_id == intent.destination_replica_id
        and record.state == "VERIFIED"
        and record.tier == "WARM"
    ]
    if not matches:
        raise CopyError("JOURNAL_CONFLICT",
                        "DESTINATION_VERIFIED without a VERIFIED WARM catalog row",
                        move_id=intent.move_id)
    try:
        payload = tiering.read_object_exact(intent.content_hash)
    except OSError as exc:
        raise CopyError("JOURNAL_CONFLICT",
                        f"cataloged destination unreadable: {exc}",
                        move_id=intent.move_id) from exc
    return CopyResult(
        move_id=intent.move_id,
        content_hash=intent.content_hash,
        source_replica_id=intent.source_replica_id,
        destination_replica_id=intent.destination_replica_id,
        destination_locator=intent.destination_locator,
        bytes_copied=len(payload),
        chunks=0,
        state="DESTINATION_VERIFIED",
        worker_epoch=intent.worker_epoch,
        directory_fsync_proven=caps.directory_fsync,
        independent_failure_domain=False,
    )


def _close_verified(
    journal: MoveJournalStore,
    tiering: RetentionTieringStore,
    move_id: str,
    caps: LocalBackendCapabilities,
    normalized: str,
    replica_id: str,
    verified_size: int,
    chunks: int,
    inject_fault_at: str | None,
    on_checkpoint: Callable[[str], None] | None,
) -> CopyResult:
    """Final independent readback through the resolver, then close the op."""
    _checkpoint("before_journal_verified", inject_fault_at, on_checkpoint)
    current = _must_get(journal, move_id)
    if not caps.durable_publish_proven:
        return CopyResult(
            move_id=move_id,
            content_hash=normalized,
            source_replica_id=current.source_replica_id,
            destination_replica_id=replica_id,
            destination_locator=current.destination_locator,
            bytes_copied=verified_size,
            chunks=chunks,
            state="COPIED_UNVERIFIED",
            worker_epoch=current.worker_epoch,
            directory_fsync_proven=caps.directory_fsync,
            independent_failure_domain=False,
        )
    try:
        payload = tiering.read_object_exact(normalized)
    except OSError as exc:
        raise CopyError("DESTINATION_HASH_MISMATCH",
                        f"resolver cannot serve the cataloged destination: {exc}",
                        move_id=move_id) from exc
    if hashlib.sha256(payload).hexdigest() != normalized:  # defensive; proven above
        raise CopyError("DESTINATION_HASH_MISMATCH",
                        "resolver bytes do not hash to H1", move_id=move_id)
    claim = journal.claim_move(
        move_id,
        expected_state=current.state,
        expected_version=current.state_version,
    )
    journal.transition_move(
        move_id,
        expected_state=current.state,
        expected_version=claim.state_version,
        worker_epoch=claim.worker_epoch,
        new_state="DESTINATION_VERIFIED",
    )
    closed = _must_get(journal, move_id)
    return CopyResult(
        move_id=move_id,
        content_hash=normalized,
        source_replica_id=closed.source_replica_id,
        destination_replica_id=replica_id,
        destination_locator=closed.destination_locator,
        bytes_copied=len(payload),
        chunks=chunks,
        state="DESTINATION_VERIFIED",
        worker_epoch=closed.worker_epoch,
        directory_fsync_proven=caps.directory_fsync,
        independent_failure_domain=False,
    )


def _failure_plan(exc: CopyError) -> tuple[str, str]:
    """Map a copy failure to (journal state, bounded error code)."""
    blocking = {
        "DESTINATION_CONFLICT": "INTEGRITY_FAILED",
        "DESTINATION_HARDLINK": "INTEGRITY_FAILED",
        "DESTINATION_HASH_MISMATCH": "INTEGRITY_FAILED",
        "UNSAFE_DESTINATION": "INTEGRITY_FAILED",
        "UNSAFE_SOURCE": "INTEGRITY_FAILED",
        "CATALOG_PUBLICATION_FAILED": "RECONCILIATION_REQUIRED",
    }
    retryable = {
        "SOURCE_H1_UNAVAILABLE": "SOURCE_UNPROVEN",
        "SOURCE_HASH_MISMATCH": "INTEGRITY_FAILED",
        "SOURCE_CHANGED_DURING_COPY": "INTEGRITY_FAILED",
        "WRITE_FAILED": "BACKEND_UNAVAILABLE",
        "FSYNC_FAILED": "BACKEND_UNAVAILABLE",
        "PUBLISH_FAILED": "BACKEND_UNAVAILABLE",
        "BACKEND_CAPABILITY_UNPROVEN": "DURABILITY_UNPROVEN",
        "JOURNAL_CONFLICT": "RECONCILIATION_REQUIRED",
    }
    if exc.code in blocking:
        return "FAILED_BLOCKING", blocking[exc.code]
    return "FAILED_RETRYABLE", retryable.get(exc.code, "RECONCILIATION_REQUIRED")


__all__ = [
    "CopyError",
    "CopyInjectedFault",
    "CopyResult",
    "LocalBackendCapabilities",
    "_cleanup_temp",
    "_destination_paths",
    "copy_hot_to_warm",
    "probe_local_capabilities",
]
