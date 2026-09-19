from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from trendforge_api.historical_retention import (
    HistoricalRetentionAuthority,
    RetentionReference,
    RetentionReferenceType,
)
from trendforge_api.market_data_store import (
    MANIFEST_SCHEMA_VERSION,
    ManifestEntry,
    ManifestStatus,
    MarketDataStore,
    SnapshotManifest,
)


NOW = datetime(2026, 8, 5, 9, 17, tzinfo=UTC)
AS_OF_DATE = date(2026, 8, 5)
OLD_DAY = date(2026, 7, 29)
REGISTRY_HASH = "7" * 64


def _store(tmp_path: Path) -> MarketDataStore:
    store = MarketDataStore(
        root=tmp_path / "market_data",
        db_path=tmp_path / "research.db",
    )
    store.initialize_schema()
    return store


def _manifest_with_object(
    store: MarketDataStore,
    *,
    run_id: str = "old-run",
    day: date = OLD_DAY,
    body: bytes = b'{"source":"point-in-time"}',
):
    object_ref = store.install_object(
        body,
        extension="json",
        media_type="application/json",
    )
    manifest = SnapshotManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        run_id=run_id,
        registry_sha256=REGISTRY_HASH,
        trading_date=day,
        slot="1500",
        generated_at=NOW,
        entries=(
            ManifestEntry(
                source_key=f"source_{run_id}",
                status=ManifestStatus.SUCCESS_NEW,
                content_hash=object_ref.content_hash,
                object_path=str(object_ref.path),
                normalized_row_count=1,
                retry_count=0,
            ),
        ),
    )
    saved = store.write_manifest(manifest)
    return object_ref, saved


def _authority(store: MarketDataStore) -> HistoricalRetentionAuthority:
    authority = HistoricalRetentionAuthority(db_path=store.db_path)
    authority.initialize_schema()
    return authority


def test_decision_reference_protects_old_day_manifest_and_object_from_real_cleanup(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    object_ref, saved = _manifest_with_object(store)
    authority = _authority(store)
    authority.register(
        RetentionReference(
            reference_id="decision:INFY:2026-07-29:v1",
            reference_type=RetentionReferenceType.DECISION_VERSION,
            run_id=saved.run_id,
            trading_date=OLD_DAY,
            created_at=NOW,
        )
    )

    dry = store.cleanup_retention(
        as_of_date=AS_OF_DATE,
        completed_trading_days=[OLD_DAY],
        detailed_trading_days=0,
    )

    assert OLD_DAY in dry.retained_trading_dates
    assert str(store.root / OLD_DAY.isoformat()) not in dry.eligible_day_paths
    assert str(object_ref.path) not in dry.eligible_object_paths

    applied = store.cleanup_retention(
        as_of_date=AS_OF_DATE,
        completed_trading_days=[OLD_DAY],
        detailed_trading_days=0,
        dry_run=False,
    )

    assert applied.deleted_day_paths == ()
    assert applied.deleted_object_paths == ()
    assert Path(saved.manifest_path).exists()
    assert object_ref.path.exists()
    with sqlite3.connect(store.db_path) as connection:
        assert connection.execute(
            "SELECT 1 FROM market_data_manifests WHERE run_id = ?",
            (saved.run_id,),
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT 1 FROM market_data_objects WHERE content_hash = ?",
            (object_ref.content_hash,),
        ).fetchone() == (1,)


def test_ml_hash_reference_protects_manifest_date_transitively(tmp_path: Path) -> None:
    store = _store(tmp_path)
    object_ref, saved = _manifest_with_object(store, run_id="ml-source-run")
    authority = _authority(store)
    authority.register(
        RetentionReference(
            reference_id="dataset:walk-forward:001",
            reference_type=RetentionReferenceType.ML_DATASET,
            content_hash=object_ref.content_hash,
            created_at=NOW,
        )
    )

    applied = store.cleanup_retention(
        as_of_date=AS_OF_DATE,
        completed_trading_days=[OLD_DAY],
        detailed_trading_days=0,
        dry_run=False,
    )

    assert OLD_DAY in applied.retained_trading_dates
    assert applied.deleted_day_paths == ()
    assert applied.deleted_object_paths == ()
    assert Path(saved.manifest_path).exists()
    assert object_ref.path.exists()


def test_expired_temporary_reference_does_not_block_cleanup(tmp_path: Path) -> None:
    store = _store(tmp_path)
    object_ref, saved = _manifest_with_object(store, run_id="temporary-run")
    authority = _authority(store)
    authority.register(
        RetentionReference(
            reference_id="temporary:retry:001",
            reference_type=RetentionReferenceType.TEMPORARY,
            run_id=saved.run_id,
            trading_date=OLD_DAY,
            permanent=False,
            retain_until=date(2026, 8, 4),
            created_at=NOW,
        )
    )

    applied = store.cleanup_retention(
        as_of_date=AS_OF_DATE,
        completed_trading_days=[OLD_DAY],
        detailed_trading_days=0,
        dry_run=False,
    )

    assert str(store.root / OLD_DAY.isoformat()) in applied.deleted_day_paths
    assert str(object_ref.path) in applied.deleted_object_paths
    assert not Path(saved.manifest_path).exists()
    assert not object_ref.path.exists()


def test_cleanup_fails_closed_if_protected_run_disappears(tmp_path: Path) -> None:
    store = _store(tmp_path)
    object_ref, saved = _manifest_with_object(store, run_id="protected-run")
    authority = _authority(store)
    authority.register(
        RetentionReference(
            reference_id="audit:protected-run",
            reference_type=RetentionReferenceType.AUDIT,
            run_id=saved.run_id,
            trading_date=OLD_DAY,
            created_at=NOW,
        )
    )
    with sqlite3.connect(store.db_path) as connection:
        connection.execute(
            "DELETE FROM market_data_manifests WHERE run_id = ?",
            (saved.run_id,),
        )

    with pytest.raises(
        RuntimeError,
        match=r"protected (run_id|trading_date) disappeared",
    ):
        store.cleanup_retention(
            as_of_date=AS_OF_DATE,
            completed_trading_days=[OLD_DAY],
            detailed_trading_days=0,
            dry_run=False,
        )

    assert (store.root / OLD_DAY.isoformat()).exists()
    assert object_ref.path.exists()


def test_cleanup_rechecks_protection_before_first_destructive_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path)
    object_ref, saved = _manifest_with_object(store, run_id="race-run")
    authority = _authority(store)
    original = HistoricalRetentionAuthority.protection_set
    calls = 0

    def changing_protection(
        self: HistoricalRetentionAuthority, *, as_of_date: date
    ):
        nonlocal calls
        calls += 1
        if calls == 2:
            authority.register(
                RetentionReference(
                    reference_id="decision:arrived-during-cleanup",
                    reference_type=RetentionReferenceType.DECISION_VERSION,
                    run_id=saved.run_id,
                    trading_date=OLD_DAY,
                    created_at=NOW,
                )
            )
        return original(self, as_of_date=as_of_date)

    monkeypatch.setattr(
        HistoricalRetentionAuthority,
        "protection_set",
        changing_protection,
    )

    with pytest.raises(RuntimeError, match="protection changed"):
        store.cleanup_retention(
            as_of_date=AS_OF_DATE,
            completed_trading_days=[OLD_DAY],
            detailed_trading_days=0,
            dry_run=False,
        )

    assert calls >= 2
    assert Path(saved.manifest_path).exists()
    assert object_ref.path.exists()


def test_unprotected_old_history_remains_deletable_after_guard_wiring(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    object_ref, saved = _manifest_with_object(store, run_id="unprotected-run")
    _authority(store)

    applied = store.cleanup_retention(
        as_of_date=AS_OF_DATE,
        completed_trading_days=[OLD_DAY],
        detailed_trading_days=0,
        dry_run=False,
    )

    assert str(store.root / OLD_DAY.isoformat()) in applied.deleted_day_paths
    assert str(object_ref.path) in applied.deleted_object_paths
    assert not Path(saved.manifest_path).exists()
    assert not object_ref.path.exists()
