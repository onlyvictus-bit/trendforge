from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from trendforge_api.historical_retention import (
    HistoricalRetentionAuthority,
    RetentionPolicy,
    RetentionReference,
    RetentionReferenceType,
    RetentionTier,
)
from trendforge_api.market_data_store import (
    ManifestEntry,
    ManifestStatus,
    MarketDataStore,
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


def _authority(store: MarketDataStore) -> HistoricalRetentionAuthority:
    authority = HistoricalRetentionAuthority(db_path=store.db_path)
    authority.initialize_schema()
    return authority


def _manifest_for_object(
    store: MarketDataStore,
    *,
    day: date,
    run_id: str,
    payload: bytes,
) -> str:
    object_ref = store.install_object(
        payload,
        extension="json",
        media_type="application/json",
    )
    store.write_manifest(
        SnapshotManifest(
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
    )
    return object_ref.content_hash


def test_retention_policy_has_hot_warm_cold_tiers() -> None:
    policy = RetentionPolicy()
    as_of = date(2026, 9, 8)

    assert policy.tier_for(date(2026, 8, 15), as_of_date=as_of) is RetentionTier.HOT
    assert policy.tier_for(date(2026, 4, 15), as_of_date=as_of) is RetentionTier.WARM
    assert policy.tier_for(date(2025, 4, 15), as_of_date=as_of) is RetentionTier.COLD


def test_future_trading_date_is_rejected() -> None:
    with pytest.raises(ValueError, match="future"):
        RetentionPolicy().tier_for(
            date(2026, 9, 9),
            as_of_date=date(2026, 9, 8),
        )


def test_decision_reference_expands_to_run_date_and_object_hash(tmp_path: Path) -> None:
    store = _store(tmp_path)
    authority = _authority(store)
    old_day = date(2025, 1, 15)
    content_hash = _manifest_for_object(
        store,
        day=old_day,
        run_id="decision-source",
        payload=b"decision-evidence",
    )

    authority.register(
        RetentionReference(
            reference_id="decision-version-42",
            reference_type=RetentionReferenceType.DECISION_VERSION,
            trading_date=old_day,
            run_id="decision-source",
            created_at=NOW,
        )
    )
    protection = authority.protection_set(as_of_date=date(2026, 9, 8))

    assert old_day in protection.trading_dates
    assert "decision-source" in protection.run_ids
    assert content_hash in protection.content_hashes
    with pytest.raises(PermissionError, match="protected"):
        authority.assert_deletion_allowed(
            content_hash=content_hash,
            as_of_date=date(2026, 9, 8),
        )


def test_ml_dataset_hash_expands_to_point_in_time_manifest(tmp_path: Path) -> None:
    store = _store(tmp_path)
    authority = _authority(store)
    old_day = date(2025, 2, 3)
    content_hash = _manifest_for_object(
        store,
        day=old_day,
        run_id="ml-source",
        payload=b"point-in-time-training-evidence",
    )

    authority.register(
        RetentionReference(
            reference_id="dataset-v17",
            reference_type=RetentionReferenceType.ML_DATASET,
            content_hash=content_hash,
            created_at=NOW,
        )
    )
    protection = authority.protection_set(as_of_date=date(2026, 9, 8))

    assert content_hash in protection.content_hashes
    assert old_day in protection.trading_dates
    assert "ml-source" in protection.run_ids


def test_expired_temporary_reference_is_not_active(tmp_path: Path) -> None:
    store = _store(tmp_path)
    authority = _authority(store)
    content_hash = _manifest_for_object(
        store,
        day=date(2026, 1, 5),
        run_id="temporary-source",
        payload=b"temporary-cache-evidence",
    )
    authority.register(
        RetentionReference(
            reference_id="temporary-debug-copy",
            reference_type=RetentionReferenceType.TEMPORARY,
            content_hash=content_hash,
            permanent=False,
            retain_until=date(2026, 2, 1),
            created_at=NOW,
        )
    )

    protection = authority.protection_set(as_of_date=date(2026, 9, 8))
    assert content_hash not in protection.content_hashes
    authority.assert_deletion_allowed(
        content_hash=content_hash,
        as_of_date=date(2026, 9, 8),
    )


def test_permanent_reference_cannot_have_expiry() -> None:
    with pytest.raises(ValueError, match="permanent retention reference"):
        RetentionReference(
            reference_id="bad-ref",
            reference_type=RetentionReferenceType.TEMPORARY,
            trading_date=date(2026, 1, 1),
            permanent=True,
            retain_until=date(2027, 1, 1),
            created_at=NOW,
        )


def test_non_permanent_reference_requires_expiry() -> None:
    with pytest.raises(ValueError, match="retain_until"):
        RetentionReference(
            reference_id="bad-temp-ref",
            reference_type=RetentionReferenceType.TEMPORARY,
            trading_date=date(2026, 1, 1),
            permanent=False,
            created_at=NOW,
        )


def test_decision_outcome_and_ml_evidence_cannot_be_temporary() -> None:
    for reference_type in (
        RetentionReferenceType.DECISION_VERSION,
        RetentionReferenceType.OUTCOME,
        RetentionReferenceType.REVISION,
        RetentionReferenceType.ML_DATASET,
    ):
        with pytest.raises(ValueError, match="cannot use temporary retention"):
            RetentionReference(
                reference_id=f"bad-{reference_type.value}",
                reference_type=reference_type,
                trading_date=date(2026, 1, 1),
                permanent=False,
                retain_until=date(2027, 1, 1),
                created_at=NOW,
            )


def test_unknown_hash_and_run_fail_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    authority = _authority(store)

    with pytest.raises(ValueError, match="unknown content_hash"):
        authority.register(
            RetentionReference(
                reference_id="unknown-hash",
                reference_type=RetentionReferenceType.OUTCOME,
                content_hash="b" * 64,
                created_at=NOW,
            )
        )

    with pytest.raises(ValueError, match="unknown run_id"):
        authority.register(
            RetentionReference(
                reference_id="unknown-run",
                reference_type=RetentionReferenceType.DECISION_VERSION,
                run_id="missing-run",
                trading_date=date(2026, 9, 1),
                created_at=NOW,
            )
        )


def test_unknown_trading_date_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    authority = _authority(store)

    with pytest.raises(ValueError, match="unknown trading_date"):
        authority.register(
            RetentionReference(
                reference_id="unknown-day",
                reference_type=RetentionReferenceType.AUDIT,
                trading_date=date(2025, 1, 1),
                created_at=NOW,
            )
        )


def test_run_date_mismatch_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    authority = _authority(store)
    _manifest_for_object(
        store,
        day=date(2026, 8, 1),
        run_id="mismatch-source",
        payload=b"mismatch",
    )

    with pytest.raises(ValueError, match="does not match"):
        authority.register(
            RetentionReference(
                reference_id="wrong-date",
                reference_type=RetentionReferenceType.DECISION_VERSION,
                run_id="mismatch-source",
                trading_date=date(2026, 8, 2),
                created_at=NOW,
            )
        )


def test_registration_is_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    authority = _authority(store)
    content_hash = _manifest_for_object(
        store,
        day=date(2026, 1, 2),
        run_id="idempotent-source",
        payload=b"idempotent",
    )
    reference = RetentionReference(
        reference_id="decision-version-100",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        content_hash=content_hash,
        created_at=NOW,
    )

    authority.register(reference)
    authority.register(reference)
    active = authority.active_references(as_of_date=date(2026, 9, 8))

    assert [ref.reference_id for ref in active].count("decision-version-100") == 1


def test_reference_id_cannot_be_repointed_to_different_evidence(tmp_path: Path) -> None:
    store = _store(tmp_path)
    authority = _authority(store)
    first_hash = _manifest_for_object(
        store,
        day=date(2026, 1, 2),
        run_id="immutable-source-1",
        payload=b"immutable-one",
    )
    second_hash = _manifest_for_object(
        store,
        day=date(2026, 1, 3),
        run_id="immutable-source-2",
        payload=b"immutable-two",
    )
    authority.register(
        RetentionReference(
            reference_id="decision-version-immutable",
            reference_type=RetentionReferenceType.DECISION_VERSION,
            content_hash=first_hash,
            created_at=NOW,
        )
    )

    with pytest.raises(ValueError, match="immutable"):
        authority.register(
            RetentionReference(
                reference_id="decision-version-immutable",
                reference_type=RetentionReferenceType.DECISION_VERSION,
                content_hash=second_hash,
                created_at=NOW,
            )
        )


def test_protection_fails_closed_if_referenced_hash_disappears(tmp_path: Path) -> None:
    store = _store(tmp_path)
    authority = _authority(store)
    content_hash = _manifest_for_object(
        store,
        day=date(2026, 1, 4),
        run_id="hash-disappearance-source",
        payload=b"must-not-disappear",
    )
    authority.register(
        RetentionReference(
            reference_id="audit-hash-integrity",
            reference_type=RetentionReferenceType.AUDIT,
            content_hash=content_hash,
            created_at=NOW,
        )
    )
    with sqlite3.connect(store.db_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "DELETE FROM market_data_objects WHERE content_hash = ?",
            (content_hash,),
        )

    with pytest.raises(RuntimeError, match="protected content_hash disappeared"):
        authority.protection_set(as_of_date=date(2026, 9, 8))
