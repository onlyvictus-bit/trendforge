"""R-HIST-03D red tests for semantic artifact retention through the canonical authority."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trendforge_api import storage
from trendforge_api.historical_retention import HistoricalRetentionAuthority
from trendforge_api.retention_producer import DurableRetentionRegistrar, RetentionOutboxStatus
from trendforge_api.selection import r18_governance as governance
from trendforge_api.selection import r18_store


NOW = datetime(2026, 9, 9, 10, 0, tzinfo=UTC)
H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64
H6 = "6" * 64
H7 = "7" * 64


def _set_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "rhist03d-artifact.db")
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    r18_store.apply_rhist03d_schema()


def _profile():
    return governance.build_strategy_profile_version(
        profile_id="PRF-001",
        profile_version="1.0.0",
        strategy_id="CONTINUATION",
        strategy_version="1.0.0",
        market="NSE",
        instrument_class="EQUITY",
        horizon="INTRADAY",
        timeframes=("5m",),
        setups=("BREAKOUT_CONTINUATION",),
        directions=("LONG", "SHORT"),
        required_to_calculate=("closed_bars",),
        required_to_qualify=("liquidity",),
        optional_context=("event",),
        prohibited_for_condition=("future_data",),
        relative_strength_contract="same-time-sector-v1",
        gate_policy="tradability-v1",
        ranking_group="intraday-continuation",
        risk_cost_assumptions=("cost-v1",),
        model_id=None,
        model_version=None,
        model_hash=None,
        research_ceiling="WAIT",
        activation_allowed=False,
        created_at=NOW,
        valid_from=NOW,
    )


def test_profile_retention_uses_artifact_hash_not_fake_market_object(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    assert r18_store.persist_strategy_profile(profile) is True
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT event_id,content_hash,artifact_hash,status FROM historical_retention_outbox"
        ).fetchone()
        assert row is not None
        assert row["content_hash"] is None
        assert row["artifact_hash"] == profile.content_hash
        assert row["status"] == "PENDING"
        event_id = row["event_id"]

    authority = HistoricalRetentionAuthority(db_path=storage.DB_PATH)
    authority.initialize_schema()
    result = DurableRetentionRegistrar(
        db_path=storage.DB_PATH, authority=authority
    ).dispatch(event_id)
    assert result.status is RetentionOutboxStatus.APPLIED

    with storage.connect() as conn:
        reference = conn.execute(
            "SELECT reference_type,content_hash,artifact_hash "
            "FROM historical_retention_references WHERE reference_id=?",
            (result.reference_id,),
        ).fetchone()
        assert reference is not None
        assert reference["reference_type"] == "STRATEGY_PROFILE"
        assert reference["content_hash"] is None
        assert reference["artifact_hash"] == profile.content_hash
        assert conn.execute(
            "SELECT COUNT(*) FROM historical_retention_outbox WHERE content_hash=?",
            (profile.content_hash,),
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM historical_retention_references WHERE content_hash=?",
            (profile.content_hash,),
        ).fetchone()[0] == 0


def test_authority_rejects_tampered_semantic_artifact_before_registration(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    assert r18_store.persist_strategy_profile(profile) is True
    with storage.connect() as conn:
        row = conn.execute("SELECT event_id FROM historical_retention_outbox").fetchone()
        assert row is not None
        event_id = row["event_id"]
        conn.execute(
            "UPDATE strategy_profile_versions SET payload_json='{}' WHERE profile_id=? AND profile_version=?",
            (profile.profile_id, profile.profile_version),
        )
        conn.commit()

    result = DurableRetentionRegistrar(
        db_path=storage.DB_PATH,
        authority=HistoricalRetentionAuthority(db_path=storage.DB_PATH),
    ).dispatch(event_id)
    assert result.status is RetentionOutboxStatus.FAILED_BLOCKING
    assert result.last_error is not None
    assert "artifact" in result.last_error.lower() or "hash" in result.last_error.lower()
    with storage.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM historical_retention_references"
        ).fetchone()[0] == 0


def test_legacy_market_object_event_identity_is_unchanged_without_artifact_hash():
    from trendforge_api.historical_retention import RetentionReferenceType
    from trendforge_api.retention_producer import RetentionEvidenceIntent

    intent = RetentionEvidenceIntent(
        artifact_type="S8_DECISION_VERSION:R1_INPUT",
        artifact_id="s8-1",
        artifact_version="v1",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        content_hash=H1,
        created_at=NOW,
    )
    assert "artifactHash" not in intent.canonical_payload()
    first_event = intent.event_id
    first_reference = intent.reference_id
    repeated = RetentionEvidenceIntent(
        artifact_type="S8_DECISION_VERSION:R1_INPUT",
        artifact_id="s8-1",
        artifact_version="v1",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        content_hash=H1,
        created_at=NOW,
    )
    assert repeated.event_id == first_event
    assert repeated.reference_id == first_reference


def test_unknown_artifact_hash_cannot_be_registered(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    from trendforge_api.historical_retention import RetentionReference, RetentionReferenceType

    authority = HistoricalRetentionAuthority(db_path=storage.DB_PATH)
    with pytest.raises(ValueError, match="artifact|unknown|hash"):
        authority.register(
            RetentionReference(
                reference_id="strategy_profile:unknown",
                reference_type=RetentionReferenceType.STRATEGY_PROFILE,
                artifact_hash=H7,
                created_at=NOW,
            )
        )
