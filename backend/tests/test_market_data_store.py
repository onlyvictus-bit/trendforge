from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from trendforge_api.market_data_store import (
    MANIFEST_SCHEMA_VERSION,
    STORE_MIGRATION_VERSION,
    ManifestEntry,
    ManifestStatus,
    MarketDataStore,
    SnapshotManifest,
)


NOW = datetime(2026, 8, 5, 9, 17, tzinfo=UTC)
REGISTRY_HASH = "4" * 64


def _store(tmp_path: Path) -> MarketDataStore:
    store = MarketDataStore(
        root=tmp_path / "market_data",
        db_path=tmp_path / "research.db",
    )
    store.initialize_schema()
    return store


def _success(
    store: MarketDataStore,
    *,
    source_key: str = "nse_all_indices",
    run_id: str = "run-1",
    trading_date: date = date(2026, 8, 5),
    body: bytes = b'{"data":[{"symbol":"NIFTY 50"}]}',
):
    return store.commit_success(
        run_id=run_id,
        source_key=source_key,
        trading_date=trading_date,
        slot="0917",
        attempted_at=NOW,
        fetched_at=NOW,
        data_date=trading_date,
        source_url="https://example.test/api",
        http_status=200,
        media_type="application/json",
        content=body,
        extension="json",
        normalized_row_count=1,
        retry_count=0,
    )


def test_migration_is_additive_and_uses_only_caller_database(tmp_path: Path) -> None:
    db_path = tmp_path / "temporary.db"
    store = MarketDataStore(root=tmp_path / "market_data", db_path=db_path)
    assert not db_path.exists()

    store.initialize_schema()

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        versions = {
            row[0]
            for row in connection.execute("SELECT version FROM schema_migrations")
        }
    assert {
        "market_data_objects",
        "market_data_attempts",
        "market_data_latest",
        "market_data_manifests",
        "market_data_manifest_objects",
    }.issubset(tables)
    assert STORE_MIGRATION_VERSION in versions


def test_identical_bytes_deduplicate_across_days(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = _success(store, run_id="run-1", trading_date=date(2026, 8, 4))
    second = _success(store, run_id="run-2", trading_date=date(2026, 8, 5))

    assert first.status is ManifestStatus.SUCCESS_NEW
    assert second.status is ManifestStatus.SUCCESS_UNCHANGED
    assert first.content_hash == second.content_hash
    assert first.object_path == second.object_path
    object_files = [path for path in store.objects_root.rglob("*") if path.is_file()]
    assert object_files == [Path(first.object_path)]
    assert store.latest_for("nse_all_indices").attempt_id == second.attempt_id


def test_failed_attempt_never_replaces_last_good(tmp_path: Path) -> None:
    store = _store(tmp_path)
    good = _success(store)

    failed = store.record_attempt(
        run_id="run-2",
        source_key="nse_all_indices",
        trading_date=date(2026, 8, 5),
        slot="1030",
        attempted_at=NOW + timedelta(minutes=73),
        status=ManifestStatus.FAILED,
        source_url="https://example.test/api",
        error="schema drift",
        retry_count=3,
    )

    assert failed.status is ManifestStatus.FAILED
    latest = store.latest_for("nse_all_indices")
    assert latest is not None
    assert latest.attempt_id == good.attempt_id
    assert latest.content_hash == good.content_hash


def test_manifest_writes_exactly_69_unique_entries_atomically(tmp_path: Path) -> None:
    store = _store(tmp_path)
    entries = tuple(
        ManifestEntry(
            source_key=f"source_{index:02d}",
            status=ManifestStatus.NOT_DUE_NO_DATA,
            retry_count=0,
        )
        for index in range(69)
    )
    manifest = SnapshotManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        run_id="slot-0917",
        registry_sha256=REGISTRY_HASH,
        trading_date=date(2026, 8, 5),
        slot="0917",
        generated_at=NOW,
        entries=entries,
    )

    saved = store.write_manifest(manifest)

    # Fixture uses range(69) synthetic keys — not live EXPECTED_SOURCE_COUNT.
    assert saved.entry_count == 69
    payload = json.loads(Path(saved.manifest_path).read_text(encoding="utf-8"))
    assert payload["runId"] == "slot-0917"
    assert len(payload["entries"]) == 69
    assert not list(Path(saved.manifest_path).parent.glob("*.part"))
    with sqlite3.connect(store.db_path) as connection:
        row = connection.execute(
            "SELECT entry_count, manifest_hash FROM market_data_manifests WHERE run_id = ?",
            ("slot-0917",),
        ).fetchone()
    assert row == (69, saved.manifest_hash)


def test_manifest_rejects_duplicate_source_keys() -> None:
    entry = ManifestEntry(
        source_key="duplicate",
        status=ManifestStatus.NOT_DUE_NO_DATA,
        retry_count=0,
    )
    with pytest.raises(ValidationError, match="unique source_key"):
        SnapshotManifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            run_id="bad-run",
            registry_sha256=REGISTRY_HASH,
            trading_date=date(2026, 8, 5),
            slot="0917",
            generated_at=NOW,
            entries=(entry, entry),
        )


def test_atomic_manifest_failure_preserves_previous_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    first = SnapshotManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        run_id="same-run",
        registry_sha256=REGISTRY_HASH,
        trading_date=date(2026, 8, 5),
        slot="0917",
        generated_at=NOW,
        entries=(),
    )
    saved = store.write_manifest(first)
    before = Path(saved.manifest_path).read_bytes()

    def fail_replace(_source: str | bytes | os.PathLike[str], _target: str | bytes | os.PathLike[str]) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    changed = first.model_copy(update={"generated_at": NOW + timedelta(seconds=1)})
    with pytest.raises(OSError, match="simulated"):
        store.write_manifest(changed)

    assert Path(saved.manifest_path).read_bytes() == before
    assert not list(Path(saved.manifest_path).parent.glob("*.part"))


def test_manifest_database_failure_restores_previous_file(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = SnapshotManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        run_id="same-run",
        registry_sha256=REGISTRY_HASH,
        trading_date=date(2026, 8, 5),
        slot="0917",
        generated_at=NOW,
        entries=(),
    )
    saved = store.write_manifest(first)
    before = Path(saved.manifest_path).read_bytes()
    missing_hash = "a" * 64
    invalid = first.model_copy(
        update={
            "generated_at": NOW + timedelta(seconds=1),
            "entries": (
                ManifestEntry(
                    source_key="unknown-object",
                    status=ManifestStatus.SUCCESS_NEW,
                    content_hash=missing_hash,
                    object_path=str(store.root / "objects" / "aa" / f"{missing_hash}.json"),
                    normalized_row_count=1,
                    retry_count=0,
                ),
            ),
        }
    )

    with pytest.raises(ValueError, match="unknown object"):
        store.write_manifest(invalid)

    assert Path(saved.manifest_path).read_bytes() == before


def test_object_extension_is_strictly_sanitized(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="extension"):
        _success(store, body=b"unsafe", run_id="unsafe").model_copy()
        # The unsafe call is deliberately separate so the valid helper stays useful.
        store.install_object(b"unsafe", extension="../json", media_type="text/plain")


def _write_day_manifest(
    store: MarketDataStore, *, day: date, run_id: str, content_hash: str | None = None
) -> Path:
    entry = ManifestEntry(
        source_key=f"source_{run_id}",
        status=(
            ManifestStatus.SUCCESS_NEW
            if content_hash
            else ManifestStatus.NOT_DUE_NO_DATA
        ),
        content_hash=content_hash,
        object_path=(
            str(store.object_path_for_hash(content_hash)) if content_hash else None
        ),
        normalized_row_count=1 if content_hash else 0,
        retry_count=0,
    )
    manifest = SnapshotManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        run_id=run_id,
        registry_sha256=REGISTRY_HASH,
        trading_date=day,
        slot="1500",
        generated_at=NOW,
        entries=(entry,),
    )
    return Path(store.write_manifest(manifest).manifest_path)


def test_retention_dry_run_and_five_completed_trading_days(tmp_path: Path) -> None:
    store = _store(tmp_path)
    completed = [date(2026, 7, 29) + timedelta(days=index) for index in range(7)]
    for index, day in enumerate(completed):
        _write_day_manifest(store, day=day, run_id=f"run-{index}")

    report = store.cleanup_retention(
        as_of_date=date(2026, 8, 5),
        completed_trading_days=completed,
        detailed_trading_days=5,
    )
    assert report.dry_run is True
    assert {Path(path).name for path in report.eligible_day_paths} == {
        "2026-07-29",
        "2026-07-30",
    }
    assert all(Path(path).exists() for path in report.eligible_day_paths)

    applied = store.cleanup_retention(
        as_of_date=date(2026, 8, 5),
        completed_trading_days=completed,
        detailed_trading_days=5,
        dry_run=False,
    )
    assert len(applied.deleted_day_paths) == 2
    assert not (store.root / "2026-07-29").exists()
    assert (store.root / "2026-07-31").exists()


def test_retention_never_deletes_current_day_or_last_good_object(tmp_path: Path) -> None:
    store = _store(tmp_path)
    attempt = _success(store, trading_date=date(2026, 7, 29))
    _write_day_manifest(
        store,
        day=date(2026, 7, 29),
        run_id="old",
        content_hash=attempt.content_hash,
    )
    current = store.root / "2026-08-05" / "logs"
    current.mkdir(parents=True)
    (current / "health.csv").write_text("keep", encoding="utf-8")

    report = store.cleanup_retention(
        as_of_date=date(2026, 8, 5),
        completed_trading_days=[date(2026, 7, 29)],
        detailed_trading_days=0,
        dry_run=False,
    )

    assert store.root / "2026-08-05" not in {
        Path(path) for path in report.deleted_day_paths
    }
    assert (current / "health.csv").exists()
    assert Path(attempt.object_path).exists()


def test_cleanup_rejects_untrusted_day_and_root_targets(tmp_path: Path) -> None:
    store = _store(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="beneath market-data root"):
        store.assert_safe_delete_target(outside, as_of_date=date(2026, 8, 5))
    with pytest.raises(ValueError, match="root itself"):
        store.assert_safe_delete_target(store.root, as_of_date=date(2026, 8, 5))
    current = store.root / "2026-08-05"
    current.mkdir()
    with pytest.raises(ValueError, match="current trading day"):
        store.assert_safe_delete_target(current, as_of_date=date(2026, 8, 5))


def test_cleanup_rejects_nested_reparse_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    day_root = store.root / "2026-07-29"
    nested = day_root / "nested-junction"
    nested.mkdir(parents=True)
    monkeypatch.setattr(
        store,
        "_is_reparse_point",
        lambda path: path.name == "nested-junction",
    )

    with pytest.raises(ValueError, match="nested symlink or reparse"):
        store.cleanup_retention(
            as_of_date=date(2026, 8, 5),
            completed_trading_days=[date(2026, 7, 29)],
            detailed_trading_days=0,
            dry_run=False,
        )

    assert nested.exists()


def test_unreferenced_object_is_collected_only_after_manifest_expiry(tmp_path: Path) -> None:
    store = _store(tmp_path)
    object_ref = store.install_object(
        b"orphan-after-retention", extension="json", media_type="application/json"
    )
    _write_day_manifest(
        store,
        day=date(2026, 7, 29),
        run_id="only-reference",
        content_hash=object_ref.content_hash,
    )

    dry = store.cleanup_retention(
        as_of_date=date(2026, 8, 5),
        completed_trading_days=[date(2026, 7, 29)],
        detailed_trading_days=0,
    )
    assert str(object_ref.path) in dry.eligible_object_paths
    assert object_ref.path.exists()

    applied = store.cleanup_retention(
        as_of_date=date(2026, 8, 5),
        completed_trading_days=[date(2026, 7, 29)],
        detailed_trading_days=0,
        dry_run=False,
    )
    assert str(object_ref.path) in applied.deleted_object_paths
    assert not object_ref.path.exists()
    assert hashlib.sha256(b"orphan-after-retention").hexdigest() == object_ref.content_hash
