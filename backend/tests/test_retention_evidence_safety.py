from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from trendforge_api.market_data_store import (
    ManifestEntry,
    ManifestStatus,
    MarketDataStore,
    RetentionReferenceType,
    SnapshotManifest,
)


NOW = datetime(2026, 9, 8, 10, 0, tzinfo=UTC)
REGISTRY_HASH = "7" * 64


def _store(tmp_path: Path) -> MarketDataStore:
    store = MarketDataStore(
        root=tmp_path / "market_data",
        db_path=tmp_path / "research.db",
    )
    store.initialize_schema()
    return store


def _manifest_for_object(
    store: MarketDataStore,
    *,
    day: date,
    run_id: str,
    payload: bytes,
) -> tuple[str, Path]:
    object_ref = store.install_object(
        payload,
        extension="json",
        media_type="application/json",
    )
    manifest = SnapshotManifest(
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
    store.write_manifest(manifest)
    return object_ref.content_hash, object_ref.path


def test_decision_reference_prevents_age_based_deletion(tmp_path: Path) -> None:
    store = _store(tmp_path)
    old_day = date(2025, 1, 15)
    content_hash, object_path = _manifest_for_object(
        store,
        day=old_day,
        run_id="decision-source",
        payload=b"decision-evidence",
    )
    store.register_retention_reference(
        reference_id="decision-version-42",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        trading_date=old_day,
        run_id="decision-source",
        content_hash=content_hash,
    )

    report = store.cleanup_retention(
        as_of_date=date(2026, 9, 8),
        completed_trading_days=[old_day],
        detailed_trading_days=0,
        dry_run=False,
    )

    assert str(store.root / old_day.isoformat()) not in report.deleted_day_paths
    assert str(object_path) not in report.deleted_object_paths
    assert old_day in report.protected_trading_dates
    assert content_hash in report.protected_content_hashes
    assert (store.root / old_day.isoformat()).exists()
    assert object_path.exists()


def test_ml_dataset_reference_protects_source_object_after_day_manifest_expiry(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    old_day = date(2025, 2, 3)
    content_hash, object_path = _manifest_for_object(
        store,
        day=old_day,
        run_id="ml-source",
        payload=b"point-in-time-training-evidence",
    )
    store.register_retention_reference(
        reference_id="dataset-v17",
        reference_type=RetentionReferenceType.ML_DATASET,
        content_hash=content_hash,
    )

    report = store.cleanup_retention(
        as_of_date=date(2026, 9, 8),
        completed_trading_days=[old_day],
        detailed_trading_days=0,
        dry_run=False,
    )

    assert str(object_path) not in report.deleted_object_paths
    assert object_path.exists()
    assert content_hash in report.protected_content_hashes


def test_expired_temporary_reference_does_not_create_permanent_protection(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    old_day = date(2026, 1, 5)
    content_hash, object_path = _manifest_for_object(
        store,
        day=old_day,
        run_id="temporary-source",
        payload=b"temporary-cache-evidence",
    )
    store.register_retention_reference(
        reference_id="temporary-debug-copy",
        reference_type=RetentionReferenceType.TEMPORARY,
        content_hash=content_hash,
        retain_until=date(2026, 2, 1),
        permanent=False,
    )

    report = store.cleanup_retention(
        as_of_date=date(2026, 9, 8),
        completed_trading_days=[old_day],
        detailed_trading_days=0,
        dry_run=False,
    )

    assert str(object_path) in report.deleted_object_paths
    assert not object_path.exists()


def test_permanent_reference_cannot_have_expiry(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="permanent retention reference"):
        store.register_retention_reference(
            reference_id="bad-decision-ref",
            reference_type=RetentionReferenceType.DECISION_VERSION,
            content_hash="a" * 64,
            retain_until=date(2027, 1, 1),
            permanent=True,
        )


def test_non_permanent_reference_requires_expiry(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="retain_until"):
        store.register_retention_reference(
            reference_id="bad-temp-ref",
            reference_type=RetentionReferenceType.TEMPORARY,
            content_hash="a" * 64,
            permanent=False,
        )


def test_reference_to_unknown_content_hash_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="unknown content_hash"):
        store.register_retention_reference(
            reference_id="unknown-evidence",
            reference_type=RetentionReferenceType.OUTCOME,
            content_hash="b" * 64,
        )


def test_reference_to_unknown_manifest_run_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="unknown run_id"):
        store.register_retention_reference(
            reference_id="unknown-run",
            reference_type=RetentionReferenceType.DECISION_VERSION,
            run_id="missing-run",
            trading_date=date(2026, 9, 1),
        )


def test_age_tiers_do_not_override_protection(tmp_path: Path) -> None:
    store = _store(tmp_path)
    hot_day = date(2026, 8, 15)
    warm_day = date(2026, 4, 15)
    cold_day = date(2025, 4, 15)

    assert store.retention_tier_for(hot_day, as_of_date=date(2026, 9, 8)).value == "HOT"
    assert store.retention_tier_for(warm_day, as_of_date=date(2026, 9, 8)).value == "WARM"
    assert store.retention_tier_for(cold_day, as_of_date=date(2026, 9, 8)).value == "COLD"


def test_future_retain_until_reference_remains_active(tmp_path: Path) -> None:
    store = _store(tmp_path)
    old_day = date(2025, 12, 1)
    content_hash, object_path = _manifest_for_object(
        store,
        day=old_day,
        run_id="bounded-source",
        payload=b"bounded-retention",
    )
    store.register_retention_reference(
        reference_id="bounded-audit",
        reference_type=RetentionReferenceType.AUDIT,
        content_hash=content_hash,
        retain_until=date(2026, 10, 1),
        permanent=False,
    )

    report = store.cleanup_retention(
        as_of_date=date(2026, 9, 8),
        completed_trading_days=[old_day],
        detailed_trading_days=0,
        dry_run=False,
    )
    assert object_path.exists()
    assert content_hash in report.protected_content_hashes


def test_reference_registration_is_idempotent_and_updates_protection(tmp_path: Path) -> None:
    store = _store(tmp_path)
    day = date(2026, 1, 2)
    content_hash, _ = _manifest_for_object(
        store,
        day=day,
        run_id="idempotent-source",
        payload=b"idempotent",
    )
    store.register_retention_reference(
        reference_id="decision-version-100",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        content_hash=content_hash,
        trading_date=day,
    )
    store.register_retention_reference(
        reference_id="decision-version-100",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        content_hash=content_hash,
        trading_date=day,
    )

    references = store.active_retention_references(as_of_date=date(2026, 9, 8))
    assert len([ref for ref in references if ref.reference_id == "decision-version-100"]) == 1
