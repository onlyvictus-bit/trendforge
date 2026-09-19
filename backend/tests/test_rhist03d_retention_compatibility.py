from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, date, datetime

import pytest

from trendforge_api.historical_retention import RetentionReference, RetentionReferenceType
from trendforge_api.retention_producer import RetentionEvidenceIntent


NOW = datetime(2026, 9, 9, 1, 30, tzinfo=UTC)
DAY = date(2026, 9, 8)
HASH = "a" * 64
EXPECTED_DIGEST = "b52b2e1df11b2cec05eba1f6bf5402e2739d3d87ec9d3b4143aea0b55d39ad87"


def test_legacy_identity_regression_anchor_is_unchanged() -> None:
    intent = RetentionEvidenceIntent(
        artifact_type="S8_DECISION_VERSION",
        artifact_id="s8-run-001",
        artifact_version="1.0.0",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        run_id="collector-run-001",
        trading_date=DAY,
        content_hash=HASH,
        created_at=NOW,
    )

    assert "artifactHash" not in intent.canonical_payload()
    assert intent.lineage_digest == EXPECTED_DIGEST
    assert intent.event_id == f"rhist03:{EXPECTED_DIGEST}"
    assert intent.reference_id == f"decision_version:{EXPECTED_DIGEST}"


def test_typed_intent_uses_artifact_hash_without_market_locator() -> None:
    intent = RetentionEvidenceIntent(
        artifact_type="R18_STRATEGY_PROFILE",
        artifact_id="PRF-001",
        artifact_version="1.0.0",
        reference_type=RetentionReferenceType.STRATEGY_PROFILE,
        artifact_hash=HASH.upper(),
        created_at=NOW,
    )

    payload = intent.canonical_payload()
    assert payload["artifactHash"] == HASH
    assert payload["contentHash"] is None
    assert payload["runId"] is None
    assert payload["tradingDate"] is None


def test_intent_rejects_mixed_market_and_artifact_identity() -> None:
    with pytest.raises(ValueError, match="exactly one evidence identity mode"):
        RetentionEvidenceIntent(
            artifact_type="R18_STRATEGY_PROFILE",
            artifact_id="PRF-001",
            artifact_version="1.0.0",
            reference_type=RetentionReferenceType.STRATEGY_PROFILE,
            content_hash=HASH,
            artifact_hash=HASH,
            created_at=NOW,
        )


def test_reference_rejects_typed_hash_for_market_reference_type() -> None:
    with pytest.raises(ValueError, match="only valid for typed 03D"):
        RetentionReference(
            reference_id="decision_version:typed",
            reference_type=RetentionReferenceType.DECISION_VERSION,
            artifact_id="D1",
            artifact_version="1",
            artifact_hash=HASH,
            created_at=NOW,
        )


def test_reference_rejects_partial_typed_identity() -> None:
    with pytest.raises(ValueError, match="requires artifact_id, artifact_version, and artifact_hash"):
        RetentionReference(
            reference_id="strategy_profile:partial",
            reference_type=RetentionReferenceType.STRATEGY_PROFILE,
            artifact_id="PRF-001",
            artifact_hash=HASH,
            created_at=NOW,
        )


def test_additive_outbox_column_preserves_legacy_payload_bytes(tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    payload = {
        "artifactId": "s8-run-001",
        "artifactType": "S8_DECISION_VERSION",
        "artifactVersion": "1.0.0",
        "contentHash": HASH,
        "createdAt": NOW.isoformat(),
        "referenceType": "DECISION_VERSION",
        "runId": "collector-run-001",
        "tradingDate": DAY.isoformat(),
    }
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE historical_retention_outbox (
                event_id TEXT PRIMARY KEY,
                reference_id TEXT NOT NULL UNIQUE,
                artifact_type TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                artifact_version TEXT NOT NULL,
                reference_type TEXT NOT NULL,
                run_id TEXT,
                trading_date TEXT,
                content_hash TEXT,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                applied_at TEXT,
                last_error TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO historical_retention_outbox VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                f"rhist03:{EXPECTED_DIGEST}",
                f"decision_version:{EXPECTED_DIGEST}",
                "S8_DECISION_VERSION",
                "s8-run-001",
                "1.0.0",
                "DECISION_VERSION",
                "collector-run-001",
                DAY.isoformat(),
                HASH,
                payload_json,
                payload_hash,
                "APPLIED",
                1,
                NOW.isoformat(),
                NOW.isoformat(),
                None,
            ),
        )
        before = conn.execute(
            "SELECT event_id,payload_json,payload_hash,content_hash FROM historical_retention_outbox"
        ).fetchone()
        conn.execute("ALTER TABLE historical_retention_outbox ADD COLUMN artifact_hash TEXT")
        after = conn.execute(
            "SELECT event_id,payload_json,payload_hash,content_hash,artifact_hash FROM historical_retention_outbox"
        ).fetchone()

    assert after[:4] == before
    assert after[4] is None
