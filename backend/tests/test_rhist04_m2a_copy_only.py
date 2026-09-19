"""R-HIST-04 M2A — RAW local/scratch HOT->WARM COPY-ONLY replication.

COPY-ONLY: a second exact H1 may be created; the first one is never
deleted, moved, renamed, or repointed by this milestone. No compression,
no restore, no COLD, no cloud. Scratch DBs and scratch files only.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

import pytest

from trendforge_api.market_data_store import MarketDataStore
from trendforge_api.retention_copy import (
    CopyError,
    CopyInjectedFault,
    copy_hot_to_warm,
    probe_local_capabilities,
)
from trendforge_api.retention_moves import MoveJournalStore
from trendforge_api.retention_tiering import RetentionTieringStore


def _scratch(tmp_path: Path, payload: bytes, db_name: str = "market.db"):
    """Build a HOT store with one adopted VERIFIED source replica."""
    store = MarketDataStore(
        root=tmp_path / "market-data", db_path=tmp_path / db_name
    )
    ref = store.install_object(
        payload, extension="json", media_type="application/json"
    )
    tiering = RetentionTieringStore(
        objects_root=tmp_path / "market-data" / "objects",
        db_path=tmp_path / db_name,
    )
    source_replica_id = tiering.adopt_legacy_as_replica(
        ref.content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-hot",
    )
    journal = MoveJournalStore(db_path=tmp_path / db_name)
    return {
        "store": store,
        "tiering": tiering,
        "journal": journal,
        "content_hash": ref.content_hash,
        "payload": payload,
        "source_replica_id": source_replica_id,
        "warm_root": tmp_path / "warm",
        "db_path": tmp_path / db_name,
    }


def _copy(ctx, **overrides):
    kwargs = {
        "journal": ctx["journal"],
        "tiering": ctx["tiering"],
        "content_hash": ctx["content_hash"],
        "warm_root": ctx["warm_root"],
        "backend_id": "local-warm",
        "failure_domain": "test-fd-warm",
    }
    kwargs.update(overrides)
    return copy_hot_to_warm(**kwargs)


def _hot_path(ctx) -> Path:
    with sqlite3.connect(ctx["db_path"]) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT object_path FROM market_data_objects WHERE content_hash = ?",
            (ctx["content_hash"],),
        ).fetchone()
    assert row is not None
    return Path(row["object_path"])


def assert_source_H1_intact(ctx) -> None:
    """Reusable oracle: the HOT source is byte-exact H1 and still governed."""
    hot = _hot_path(ctx)
    assert hot.is_file() and not hot.is_symlink()
    data = hot.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ctx["content_hash"]
    assert data == ctx["payload"]
    with sqlite3.connect(ctx["db_path"]) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT state FROM rhist04_replicas WHERE replica_id = ?",
            (ctx["source_replica_id"],),
        ).fetchone()
    assert row is not None and row["state"] == "VERIFIED"


def _warm_replica_rows(ctx):
    with sqlite3.connect(ctx["db_path"]) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM rhist04_replicas WHERE content_hash = ? AND tier = 'WARM'",
            (ctx["content_hash"],),
        ).fetchall()


# ---------------------------------------------------------------------------
# Happy path + identity
# ---------------------------------------------------------------------------


def test_happy_raw_hot_to_warm(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "happy"}')
    result = _copy(ctx)
    assert result.state == "DESTINATION_VERIFIED"
    assert result.bytes_copied == len(ctx["payload"])
    assert result.content_hash == ctx["content_hash"]
    rows = _warm_replica_rows(ctx)
    assert len(rows) == 1
    assert rows[0]["state"] == "VERIFIED"
    assert rows[0]["representation"] == "RAW"
    assert rows[0]["replica_id"] == result.destination_replica_id
    # Journal identity agrees with catalog identity.
    move = ctx["journal"].get_move(result.move_id)
    assert move is not None
    assert move.destination_replica_id == result.destination_replica_id
    assert move.state == "DESTINATION_VERIFIED"
    assert move.worker_epoch >= 1
    # Destination bytes are exactly H1 on disk.
    dest = Path(result.destination_locator)
    assert dest.is_file()
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == ctx["content_hash"]
    assert_source_H1_intact(ctx)


def test_zero_byte_object_copies_normally(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b"")
    assert ctx["content_hash"] == hashlib.sha256(b"").hexdigest()
    result = _copy(ctx)
    assert result.state == "DESTINATION_VERIFIED"
    assert result.bytes_copied == 0
    assert Path(result.destination_locator).read_bytes() == b""
    assert_source_H1_intact(ctx)


def test_large_object_streams_in_chunks(tmp_path: Path) -> None:
    payload = os.urandom(1 << 20)  # 1 MiB, spans many 64 KiB chunks
    ctx = _scratch(tmp_path, payload)
    result = _copy(ctx, chunk_size=64 * 1024)
    assert result.state == "DESTINATION_VERIFIED"
    assert result.bytes_copied == len(payload)
    assert result.chunks and result.chunks > 1
    assert hashlib.sha256(Path(result.destination_locator).read_bytes()).hexdigest() == (
        ctx["content_hash"]
    )
    assert_source_H1_intact(ctx)


def test_capability_probe_reports_real_primitives(tmp_path: Path) -> None:
    warm_root = tmp_path / "warm"
    capabilities = probe_local_capabilities(warm_root)
    assert capabilities.exclusive_create is True
    assert capabilities.file_fsync is True
    assert capabilities.atomic_publish is True
    assert capabilities.readback_ok is True
    # Directory fsync is platform-dependent (Windows forbids opening a
    # directory handle this way); the probe must report honestly either way.
    assert isinstance(capabilities.directory_fsync, bool)
    assert capabilities.durable_publish_proven is True
    # Probe cleans up after itself.
    leftovers = [p for p in warm_root.rglob("*") if p.is_file()]
    assert leftovers == []


# ---------------------------------------------------------------------------
# Source-side negatives
# ---------------------------------------------------------------------------


def test_wrong_source_h1_fails_closed(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "real"}')
    store = MarketDataStore(
        root=tmp_path / "market-data", db_path=tmp_path / "market.db"
    )
    store.install_object(
        b'{"h2": "decoy"}', extension="json", media_type="application/json"
    )
    missing = hashlib.sha256(b'{"h1": "absent"}').hexdigest()
    with pytest.raises(CopyError) as excinfo:
        _copy(ctx, content_hash=missing)
    assert excinfo.value.code in ("SOURCE_H1_UNAVAILABLE", "SOURCE_HASH_MISMATCH")
    assert_source_H1_intact(ctx)


def test_h1_missing_with_valid_h2_never_substitutes(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "original"}')
    h2_store = MarketDataStore(
        root=tmp_path / "market-data", db_path=tmp_path / "market.db"
    )
    h2_ref = h2_store.install_object(
        b'{"h2": "newer"}', extension="json", media_type="application/json"
    )
    ctx["tiering"].adopt_legacy_as_replica(
        h2_ref.content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-hot",
    )
    missing = hashlib.sha256(b'{"h1": "gone"}').hexdigest()
    with pytest.raises(CopyError):
        _copy(ctx, content_hash=missing)
    # H2 was never read, copied, or registered as WARM for the H1 operation.
    with sqlite3.connect(ctx["db_path"]) as conn:
        warm_h2 = conn.execute(
            "SELECT COUNT(*) FROM rhist04_replicas WHERE content_hash = ? "
            "AND tier = 'WARM'",
            (h2_ref.content_hash,),
        ).fetchone()[0]
    assert warm_h2 == 0
    moves = [
        row for row in _all_moves(ctx) if row["content_hash"] == missing
    ]
    assert moves == [] or all(
        row["state"] not in ("DESTINATION_VERIFIED", "COMPLETED") for row in moves
    )


def _all_moves(ctx):
    with sqlite3.connect(ctx["db_path"]) as conn:
        conn.row_factory = sqlite3.Row
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "market_data_tier_moves" not in tables:
            return []
        return conn.execute("SELECT * FROM market_data_tier_moves").fetchall()


def test_source_mutation_during_copy_fails_closed(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b"A" * 4096)

    def _mutate(name: str) -> None:
        if name == "before_stream":
            _hot_path(ctx).write_bytes(b"B" * 4096)

    with pytest.raises(CopyError) as excinfo:
        _copy(ctx, on_checkpoint=_mutate)
    assert excinfo.value.code in ("SOURCE_CHANGED_DURING_COPY", "SOURCE_HASH_MISMATCH")
    assert _warm_replica_rows(ctx) == []
    # Restore the true source for the intactness oracle (mutation was the fault).
    _hot_path(ctx).write_bytes(b"A" * 4096)
    assert_source_H1_intact(ctx)
    with sqlite3.connect(ctx["db_path"]) as conn:
        verified = conn.execute(
            "SELECT COUNT(*) FROM market_data_tier_moves WHERE content_hash = ? "
            "AND state = 'DESTINATION_VERIFIED'",
            (ctx["content_hash"],),
        ).fetchone()[0]
    assert verified == 0


def test_source_path_replacement_before_open_fails_closed(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "swap-me"}')
    hot = _hot_path(ctx)
    swapped = tmp_path / "swapped.json"
    swapped.write_bytes(b'{"h2": "intruder"}')

    def _swap(name: str) -> None:
        # No file is open yet at after_claim, so the swap lands on all
        # platforms; the copier must then read intruder bytes and refuse.
        if name == "after_claim":
            hot.unlink()
            swapped.rename(hot)

    with pytest.raises(CopyError) as excinfo:
        _copy(ctx, on_checkpoint=_swap)
    assert excinfo.value.code == "SOURCE_CHANGED_DURING_COPY"
    assert _warm_replica_rows(ctx) == []
    swapped_back = tmp_path / "restored.json"
    swapped_back.write_bytes(ctx["payload"])
    hot.unlink(missing_ok=True)
    swapped_back.rename(hot)
    assert_source_H1_intact(ctx)


def test_source_path_swap_after_open_never_copies_h2(tmp_path: Path) -> None:
    """Post-open swap: POSIX pins the open inode (copy stays correct),
    Windows locks the file (operation fails closed). Either outcome is
    safe; what must never happen is H2 bytes landing as the H1 copy."""
    ctx = _scratch(tmp_path, b'{"h1": "swap-late"}')
    hot = _hot_path(ctx)
    swapped = tmp_path / "swapped-late.json"
    swapped.write_bytes(b'{"h2": "intruder"}')

    def _swap(name: str) -> None:
        if name == "before_stream":
            try:
                hot.unlink()
                swapped.rename(hot)
            except OSError:
                pass  # locked open file: platform refused the swap itself

    try:
        result = _copy(ctx, on_checkpoint=_swap)
    except CopyError:
        result = None
    if result is not None:
        dest = Path(result.destination_locator)
        assert hashlib.sha256(dest.read_bytes()).hexdigest() == ctx["content_hash"]
    for row in _warm_replica_rows(ctx):
        data = Path(row["locator"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == ctx["content_hash"]
    hot.unlink(missing_ok=True)
    swapped.unlink(missing_ok=True)
    hot.write_bytes(ctx["payload"])
    assert_source_H1_intact(ctx)


# ---------------------------------------------------------------------------
# Destination-side negatives
# ---------------------------------------------------------------------------


def test_existing_exact_destination_adopts_without_overwrite(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "preexisting"}')
    from trendforge_api.retention_copy import _destination_paths

    _, final = _destination_paths(
        ctx["warm_root"], ctx["content_hash"], ".json"
    )
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(ctx["payload"])
    before = (final.stat().st_dev, final.stat().st_ino)
    result = _copy(ctx)
    assert result.state == "DESTINATION_VERIFIED"
    after = (final.stat().st_dev, final.stat().st_ino)
    assert before == after, "exact destination must be adopted, not rewritten"
    assert len(_warm_replica_rows(ctx)) == 1
    assert_source_H1_intact(ctx)


def test_existing_wrong_destination_conflicts_without_clobber(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "collision"}')
    from trendforge_api.retention_copy import _destination_paths

    _, final = _destination_paths(
        ctx["warm_root"], ctx["content_hash"], ".json"
    )
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(b'{"hx": "wrong bytes here"}')
    with pytest.raises(CopyError) as excinfo:
        _copy(ctx)
    assert excinfo.value.code == "DESTINATION_CONFLICT"
    assert final.read_bytes() == b'{"hx": "wrong bytes here"}'
    assert _warm_replica_rows(ctx) == []
    move = ctx["journal"].get_move(excinfo.value.move_id)
    assert move is not None and move.state == "FAILED_BLOCKING"
    assert_source_H1_intact(ctx)


def test_destination_final_symlink_rejected(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "link-final"}')
    from trendforge_api.retention_copy import _destination_paths

    _, final = _destination_paths(
        ctx["warm_root"], ctx["content_hash"], ".json"
    )
    final.parent.mkdir(parents=True, exist_ok=True)
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_bytes(ctx["payload"])
    try:
        os.symlink(elsewhere, final)
    except OSError:
        pytest.skip("platform forbids symlink creation here")
    with pytest.raises(CopyError) as excinfo:
        _copy(ctx)
    assert excinfo.value.code in ("UNSAFE_DESTINATION", "DESTINATION_CONFLICT")
    assert _warm_replica_rows(ctx) == []
    assert_source_H1_intact(ctx)


def test_unsafe_parent_symlink_rejected(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "parent-link"}')
    outside = tmp_path / "outside"
    outside.mkdir()
    link_parent = tmp_path / "warm-link"
    try:
        os.symlink(outside, link_parent, target_is_directory=True)
    except OSError:
        pytest.skip("platform forbids symlink creation here")
    with pytest.raises(CopyError) as excinfo:
        _copy(ctx, warm_root=link_parent)
    assert excinfo.value.code == "UNSAFE_DESTINATION"
    assert_source_H1_intact(ctx)


def test_destination_hardlink_to_source_rejected(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "hardlink"}')
    from trendforge_api.retention_copy import _destination_paths

    _, final = _destination_paths(
        ctx["warm_root"], ctx["content_hash"], ".json"
    )
    final.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(_hot_path(ctx), final)
    except OSError:
        pytest.skip("platform forbids hardlink creation here")
    with pytest.raises(CopyError) as excinfo:
        _copy(ctx)
    assert excinfo.value.code in ("DESTINATION_HARDLINK", "DESTINATION_CONFLICT")
    assert _warm_replica_rows(ctx) == []
    assert_source_H1_intact(ctx)


# ---------------------------------------------------------------------------
# Filesystem / durability fault injection (monkeypatched OS layer)
# ---------------------------------------------------------------------------


def _break(monkeypatch, name: str, errno_code: int = 28, after: int = 0):
    """Fail the OS call once past the threshold, then disarm for recovery."""
    calls = {"n": 0}
    fired = {"once": False}
    real = getattr(os, name)

    def _failing(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] > after and not fired["once"]:
            fired["once"] = True
            raise OSError(errno_code, os.strerror(errno_code))
        return real(*args, **kwargs)

    monkeypatch.setattr(os, name, _failing)
    return calls


def test_partial_destination_write_recovers(tmp_path: Path, monkeypatch) -> None:
    ctx = _scratch(tmp_path, b"C" * 65536)
    _break(monkeypatch, "write", after=2)
    with pytest.raises(CopyError):
        _copy(ctx, chunk_size=1024)
    assert_source_H1_intact(ctx)
    assert _warm_replica_rows(ctx) == []
    result = _copy(ctx, chunk_size=1024)
    assert result.state == "DESTINATION_VERIFIED"
    assert len(_warm_replica_rows(ctx)) == 1
    assert_source_H1_intact(ctx)


def test_write_failure_fails_closed(tmp_path: Path, monkeypatch) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "write-fail"}')
    _break(monkeypatch, "write")
    with pytest.raises(CopyError) as excinfo:
        _copy(ctx)
    assert excinfo.value.code == "WRITE_FAILED"
    assert_source_H1_intact(ctx)


def test_disk_full_equivalent_fails_closed(tmp_path: Path, monkeypatch) -> None:
    import errno

    ctx = _scratch(tmp_path, b"D" * 65536)
    _break(monkeypatch, "write", errno_code=errno.ENOSPC, after=1)
    with pytest.raises(CopyError):
        _copy(ctx, chunk_size=1024)
    assert_source_H1_intact(ctx)
    assert _warm_replica_rows(ctx) == []


def _proven_capabilities():
    from trendforge_api.retention_copy import LocalBackendCapabilities

    return LocalBackendCapabilities(
        exclusive_create=True,
        file_fsync=True,
        atomic_publish=True,
        readback_ok=True,
        directory_fsync=False,
        durable_publish_proven=True,
        detail="test-attested proven backend",
    )


def test_fsync_failure_fails_closed(tmp_path: Path, monkeypatch) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "fsync-fail"}')
    _break(monkeypatch, "fsync")
    with pytest.raises(CopyError) as excinfo:
        _copy(ctx, capabilities=_proven_capabilities())
    assert excinfo.value.code == "FSYNC_FAILED"
    assert_source_H1_intact(ctx)


def test_publish_failure_fails_closed(tmp_path: Path, monkeypatch) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "publish-fail"}')
    _break(monkeypatch, "replace")
    with pytest.raises(CopyError) as excinfo:
        _copy(ctx, capabilities=_proven_capabilities())
    assert excinfo.value.code == "PUBLISH_FAILED"
    assert_source_H1_intact(ctx)


def test_destination_corruption_before_verification(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "corrupt-dest"}')

    def _corrupt(name: str) -> None:
        if name == "before_readback":
            from trendforge_api.retention_copy import _destination_paths

            _, final = _destination_paths(
                ctx["warm_root"], ctx["content_hash"], ".json"
            )
            final.write_bytes(b'{"hx": "mutated after publish"}')

    with pytest.raises(CopyError) as excinfo:
        _copy(ctx, on_checkpoint=_corrupt)
    assert excinfo.value.code == "DESTINATION_HASH_MISMATCH"
    assert _warm_replica_rows(ctx) == []
    assert_source_H1_intact(ctx)


def test_destination_changed_between_verify_phases(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "phase-change"}')
    seen = {"n": 0}

    def _flip(name: str) -> None:
        if name == "before_catalog":
            from trendforge_api.retention_copy import _destination_paths

            _, final = _destination_paths(
                ctx["warm_root"], ctx["content_hash"], ".json"
            )
            if seen["n"] == 0:
                final.write_bytes(b'{"hx": "flipped"}')
                seen["n"] += 1

    with pytest.raises(CopyError):
        _copy(ctx, on_checkpoint=_flip)
    assert _warm_replica_rows(ctx) == []
    assert_source_H1_intact(ctx)


# ---------------------------------------------------------------------------
# Crash windows A-N (simulated crash = injected fault + fresh instances)
# ---------------------------------------------------------------------------


def _crash_recover(ctx, fault_at: str):
    with pytest.raises(CopyInjectedFault):
        _copy(ctx, inject_fault_at=fault_at)
    assert_source_H1_intact(ctx)
    fresh_journal = MoveJournalStore(db_path=ctx["db_path"])
    fresh_tiering = RetentionTieringStore(
        objects_root=ctx["db_path"].parent / "market-data" / "objects",
        db_path=ctx["db_path"],
    )
    result = copy_hot_to_warm(
        journal=fresh_journal,
        tiering=fresh_tiering,
        content_hash=ctx["content_hash"],
        warm_root=ctx["warm_root"],
        backend_id="local-warm",
        failure_domain="test-fd-warm",
    )
    assert result.state == "DESTINATION_VERIFIED"
    assert len(_warm_replica_rows(ctx)) == 1
    assert_source_H1_intact(ctx)
    return result


def test_crash_after_claim(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b'{"h1": "crash-b"}'), "after_claim")


def test_crash_after_temp_create(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b'{"h1": "crash-c"}'), "after_temp_create")


def test_crash_after_partial_write(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b"E" * 131072), "after_partial_write")


def test_crash_after_stream_complete(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b'{"h1": "crash-e"}'), "after_stream_complete")


def test_crash_after_fsync(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b'{"h1": "crash-f"}'), "after_fsync")


def test_crash_after_publish(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b'{"h1": "crash-g"}'), "after_publish")


def test_crash_before_readback(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b'{"h1": "crash-h"}'), "before_readback")


def test_crash_during_readback(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b'{"h1": "crash-i"}'), "during_readback")


def test_crash_after_readback(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b'{"h1": "crash-j"}'), "after_readback")


def test_crash_before_catalog(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b'{"h1": "crash-k"}'), "before_catalog")


def test_crash_after_catalog(tmp_path: Path) -> None:
    _crash_recover(_scratch(tmp_path, b'{"h1": "crash-l"}'), "after_catalog")


def test_crash_before_journal_verified(tmp_path: Path) -> None:
    _crash_recover(
        _scratch(tmp_path, b'{"h1": "crash-m"}'), "before_journal_verified"
    )


def test_crash_after_journal_verified_is_idempotent(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "crash-n"}')
    first = _copy(ctx)
    assert first.state == "DESTINATION_VERIFIED"
    # A retry after completion converges without a second authoritative copy.
    second = _copy(ctx)
    assert second.state == "DESTINATION_VERIFIED"
    assert second.destination_replica_id == first.destination_replica_id
    assert len(_warm_replica_rows(ctx)) == 1
    assert_source_H1_intact(ctx)


def test_retry_after_crash_before_journal_update_converges(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "retry-idem"}')
    with pytest.raises(CopyInjectedFault):
        _copy(ctx, inject_fault_at="before_journal_verified")
    assert len(_warm_replica_rows(ctx)) == 1
    result = _copy(ctx)
    assert result.state == "DESTINATION_VERIFIED"
    assert len(_warm_replica_rows(ctx)) == 1
    assert_source_H1_intact(ctx)


# ---------------------------------------------------------------------------
# Fencing at the copier layer
# ---------------------------------------------------------------------------


def test_stale_claim_cannot_drive_copy(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "stale-claim"}')
    journal = ctx["journal"]
    intent = journal.create_move_intent(
        content_hash=ctx["content_hash"],
        source_replica_id=ctx["source_replica_id"],
        destination_tier="WARM",
        destination_backend_id="local-warm",
        destination_object_key=f"warm/{ctx['content_hash'][:2]}.json",
        destination_locator=str(
            ctx["warm_root"] / ctx["content_hash"][:2] / f"{ctx['content_hash']}.json"
        ),
        representation="RAW",
        representation_version="v1",
        operation_kind="COPY",
    )
    stale = journal.claim_move(
        intent.move_id,
        expected_state="PENDING_COPY",
        expected_version=intent.state_version,
    )
    journal.claim_move(
        intent.move_id,
        expected_state="PENDING_COPY",
        expected_version=stale.state_version,
    )
    import glob as _glob

    temps_before = _glob.glob(str(ctx["warm_root"] / "**" / "*.part"), recursive=True)
    with pytest.raises(CopyError) as excinfo:
        _copy(ctx, claim=stale)
    assert excinfo.value.code in ("STALE_WORKER", "FENCE_REJECTED")
    temps_after = _glob.glob(str(ctx["warm_root"] / "**" / "*.part"), recursive=True)
    assert temps_after == temps_before
    assert_source_H1_intact(ctx)


def test_two_competing_workers_one_semantic_replica(tmp_path: Path) -> None:
    import threading as _threading

    ctx = _scratch(tmp_path, b'{"h1": "compete"}')
    outcomes: list[str] = []

    def _worker():
        try:
            worker_tiering = RetentionTieringStore(
                objects_root=ctx["db_path"].parent / "market-data" / "objects",
                db_path=ctx["db_path"],
            )
            worker_journal = MoveJournalStore(db_path=ctx["db_path"])
            result = copy_hot_to_warm(
                journal=worker_journal,
                tiering=worker_tiering,
                content_hash=ctx["content_hash"],
                warm_root=ctx["warm_root"],
                backend_id="local-warm",
                failure_domain="test-fd-warm",
            )
            outcomes.append(f"done:{result.state}")
        except CopyError as exc:
            outcomes.append(f"fenced:{exc.code}")
        except Exception as exc:  # noqa: BLE001 - must surface, never swallow
            outcomes.append(f"unexpected:{type(exc).__name__}")

    threads = [_threading.Thread(target=_worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes, "workers must report"
    assert all(
        outcome.startswith("done:DESTINATION_VERIFIED")
        or outcome.startswith("fenced:")
        for outcome in outcomes
    ), outcomes
    assert len(_warm_replica_rows(ctx)) == 1
    assert_source_H1_intact(ctx)


def test_multiprocess_competing_workers_converge(tmp_path: Path) -> None:
    import subprocess
    import sys as _sys

    ctx = _scratch(tmp_path, b'{"h1": "mp-compete"}')
    worker_path = tmp_path / "mp_copy_worker.py"
    worker_path.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "from trendforge_api.retention_copy import copy_hot_to_warm, CopyError\n"
        "from trendforge_api.retention_moves import MoveJournalStore\n"
        "from trendforge_api.retention_tiering import RetentionTieringStore\n"
        "\n"
        "db = Path(sys.argv[1])\n"
        "h1 = sys.argv[2]\n"
        "warm = Path(sys.argv[3])\n"
        "tiering = RetentionTieringStore(\n"
        "    objects_root=db.parent / 'market-data' / 'objects', db_path=db)\n"
        "journal = MoveJournalStore(db_path=db)\n"
        "try:\n"
        "    result = copy_hot_to_warm(journal=journal, tiering=tiering,\n"
        "                              content_hash=h1, warm_root=warm,\n"
        "                              backend_id='local-warm',\n"
        "                              failure_domain='test-fd-warm')\n"
        "    print(f'RESULT ok:{result.state}')\n"
        "except CopyError as exc:\n"
        "    print(f'RESULT fenced:{exc.code}')\n",
        encoding="utf-8",
    )
    import os as _os

    backend = Path(__file__).resolve().parents[1]
    env = dict(_os.environ)
    env["PYTHONPATH"] = str(backend) + _os.pathsep + env.get("PYTHONPATH", "")
    argv = [
        _sys.executable, str(worker_path),
        str(ctx["db_path"]), ctx["content_hash"], str(ctx["warm_root"]),
    ]
    processes = [
        subprocess.Popen(
            argv,
            cwd=str(backend),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(4)
    ]
    try:
        outputs = []
        for process in processes:
            try:
                stdout, stderr = process.communicate(timeout=300)
            except subprocess.TimeoutExpired:
                process.kill()
                raise
            outputs.append((process.returncode, stdout, stderr))
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
    assert all(code == 0 for code, _, _ in outputs), outputs
    assert any("ok:DESTINATION_VERIFIED" in out for _, out, _ in outputs), outputs
    assert all(
        "ok:DESTINATION_VERIFIED" in out or "fenced:" in out
        for _, out, _ in outputs
    ), outputs
    assert len(_warm_replica_rows(ctx)) == 1
    assert_source_H1_intact(ctx)


def test_sqlite_failure_never_becomes_success(tmp_path: Path, monkeypatch) -> None:
    import sqlite3 as _sqlite3

    ctx = _scratch(tmp_path, b'{"h1": "db-fail"}')

    def _flaky(self, *args, **kwargs):
        raise _sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(MoveJournalStore, "claim_move", _flaky)
    with pytest.raises(CopyError):
        _copy(ctx)
    assert _warm_replica_rows(ctx) == []
    assert_source_H1_intact(ctx)


def test_unsupported_backend_runs_mechanics_without_verified_label(
    tmp_path: Path,
) -> None:
    from trendforge_api.retention_copy import LocalBackendCapabilities

    ctx = _scratch(tmp_path, b'{"h1": "unproven"}')
    capabilities = LocalBackendCapabilities(
        exclusive_create=True,
        file_fsync=True,
        atomic_publish=True,
        readback_ok=True,
        directory_fsync=False,
        durable_publish_proven=False,
        detail="test-simulated unproven backend",
    )
    result = _copy(ctx, capabilities=capabilities)
    assert result.state == "COPIED_UNVERIFIED"
    dest = Path(result.destination_locator)
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == ctx["content_hash"]
    rows = _warm_replica_rows(ctx)
    assert len(rows) == 1
    assert rows[0]["state"] == "DISCOVERED"
    move = ctx["journal"].get_move(result.move_id)
    assert move is not None and move.state == "COPIED_UNVERIFIED"
    assert_source_H1_intact(ctx)


# ---------------------------------------------------------------------------
# Reader end-to-end + legacy immutability + static surface
# ---------------------------------------------------------------------------


def test_reader_resolves_warm_after_hot_unavailable(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "e2e"}')
    before = ctx["store"].read_object_exact(ctx["content_hash"])
    assert before == ctx["payload"]
    result = _copy(ctx)
    assert result.state == "DESTINATION_VERIFIED"
    # Simulate HOT loss ONLY in the scratch fixture (no deletion code exists).
    _hot_path(ctx).unlink()
    assert ctx["store"].exact_object_available(ctx["content_hash"]) is True
    returned = ctx["store"].read_object_exact(ctx["content_hash"])
    assert hashlib.sha256(returned).hexdigest() == ctx["content_hash"]
    assert returned == ctx["payload"]


def _provenance_snapshot(ctx):
    with sqlite3.connect(ctx["db_path"]) as conn:
        conn.row_factory = sqlite3.Row
        objects = {
            row["content_hash"]: row["object_path"]
            for row in conn.execute(
                "SELECT content_hash, object_path FROM market_data_objects"
            )
        }
        latest = {
            row["source_key"]: (row["content_hash"], row["object_path"])
            for row in conn.execute(
                "SELECT source_key, content_hash, object_path "
                "FROM market_data_latest"
            )
        }
        attempts = conn.execute("SELECT COUNT(*) FROM market_data_attempts").fetchone()[0]
    return objects, latest, attempts


def test_legacy_provenance_paths_unchanged_by_copy(tmp_path: Path) -> None:
    ctx = _scratch(tmp_path, b'{"h1": "provenance"}')
    before = _provenance_snapshot(ctx)
    result = _copy(ctx)
    assert result.state == "DESTINATION_VERIFIED"
    after = _provenance_snapshot(ctx)
    assert after[0] == before[0], "market_data_objects locators must not move"
    assert after[1] == before[1], "market_data_latest locators must not move"
    assert after[2] == before[2], "no attempt rows may be fabricated by copy"


def test_no_source_deletion_capability_in_copier() -> None:
    root = Path(__file__).resolve().parents[1] / "trendforge_api"
    text = (root / "retention_copy.py").read_text(encoding="utf-8")
    code = _code_only(text)
    for token in (
        "shutil.move",
        "shutil.rmtree",
        "os.rename",
        "def move_",
        "def delete_",
        "def remove_",
        "def retire_",
    ):
        assert token not in code, f"copier must not contain {token!r}"
    # SOURCE_REMOVAL_PENDING may appear ONLY in the foreign-state refusal
    # guard (never as a transition target): M2A must not drive ops that
    # later milestones own.
    lines = code.splitlines()
    for index, line in enumerate(lines):
        if "SOURCE_REMOVAL_PENDING" in line:
            window = "\n".join(lines[index:index + 4])
            assert "foreign state" in window or "refusing M2A" in window, (
                f"SOURCE_REMOVAL_PENDING outside refusal guard: {line.strip()}"
            )
    # .unlink( / .rmdir( are allowed ONLY inside provably-scoped cleaners:
    # _cleanup_temp (rejects non-.part / outside-warm-root paths) and the
    # capability probe (removes only exact paths it created itself).
    # os.remove / shutil / renames must not appear at all.
    for token in ("os.remove", "shutil.move", "shutil.rmtree", "os.rename"):
        assert token not in code, f"copier must not contain {token!r}"
    current: str | None = None
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("def "):
            current = stripped[4:].split("(")[0]
        for token in (".unlink(", ".rmdir("):
            if token in line:
                assert current in ("_cleanup_temp", "probe_local_capabilities"), (
                    f"{token} outside scoped cleaners: {current}:{stripped}"
                )
    assert "CopyInjectedFault" in code  # fault seams are explicit, not hidden


def _code_only(text: str) -> str:
    out: list[str] = []
    in_docstring = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('"""'):
            if stripped.count('"""') == 2 and len(stripped) > 3:
                continue
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        out.append(line.split("#", 1)[0])
    return "\n".join(out)


def test_temp_cleanup_helper_rejects_arbitrary_paths(tmp_path: Path) -> None:
    from trendforge_api.retention_copy import _cleanup_temp

    warm_root = tmp_path / "warm"
    warm_root.mkdir()
    legit = warm_root / "ab" / ".h1aaaa.12345678.part"
    legit.parent.mkdir(parents=True)
    legit.write_bytes(b"temp debris")
    _cleanup_temp(legit, warm_root)  # scoped temp: allowed, best effort
    assert not legit.exists()
    with pytest.raises(CopyError):
        _cleanup_temp(tmp_path / "market-data" / "objects" / "x.json", warm_root)
    hot = _hot_path(_scratch(tmp_path, b'{"h1": "guard"}'))
    with pytest.raises(CopyError):
        _cleanup_temp(hot, warm_root)


def test_trading_authority_surface_absent_from_copier() -> None:
    root = Path(__file__).resolve().parents[1] / "trendforge_api"
    code = _code_only((root / "retention_copy.py").read_text(encoding="utf-8")).casefold()
    for token in ("broker", "place_order", "promote_model", "activate_strategy",
                  "execution_authority", "live_trade", "import ccxt"):
        assert token not in code, f"copier must not contain {token!r}"
