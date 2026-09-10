from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from trendforge_api import storage
from trendforge_api.historical_retention import RetentionReferenceType
from trendforge_api.retention_producer import (
    DurableRetentionRegistrar,
    RetentionEvidenceIntent,
    RetentionOutboxStatus,
)
from trendforge_api.selection import r18_governance as governance
from trendforge_api.selection import r18_history as history
from trendforge_api.selection import r18_history_completion as completion
from trendforge_api.selection import r18_store

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
DECISION = NOW - timedelta(days=8)
LABEL = DECISION + timedelta(days=3)
H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64
H6 = "6" * 64


def _set_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "rhist03d-completion.db")
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    r18_store.apply_rhist03d_schema()


def _member(**changes):
    values = dict(
        instrument_id="NSE:INFY:EQ",
        opportunity_id="INFY:EOD:continuation:SHORT",
        profile_id="PRF-R16-NSE-CASH-EOD-SWING",
        profile_version="1.0.0",
        strategy_id="R16_SWING",
        strategy_version="1.0.0",
        setup_id="SWING_BREAKOUT_BREAKDOWN_V1",
        setup_episode_id="episode-1",
        timeframe="EOD",
        horizon="SWING",
        direction="BEARISH",
        decision_version_id="D100v1",
        decision_version_hash=H1,
        decision_at=DECISION,
        decision_data_cutoff=DECISION,
        max_feature_available_at=DECISION - timedelta(seconds=1),
        public_state="WATCH",
        outcome_id="O1",
        outcome_hash=H2,
        outcome_state="TARGET",
        outcome_available_at=LABEL,
        revision_id=None,
        revision_hash=None,
        revision_available_at=None,
        label_available_at=LABEL,
        feature_manifest_id="r16-source-features-v1",
        feature_manifest_hash=H3,
        formula_set_version="r16-policy-bundle-v1",
        formula_set_hash=H4,
        input_hashes=(H5,),
        evidence_roots=(
            {"role": "DECISION_MARKET_EVIDENCE", "contentHash": H5},
            {"role": "OUTCOME_MARKET_EVIDENCE", "contentHash": H6},
        ),
        split="TRAIN",
        fold="F1",
        inclusion_reason="BASE_POPULATION",
        exclusion_reason=None,
    )
    values.update(changes)
    return governance.build_frozen_dataset_member(**values)


def _profile(**changes):
    values = dict(
        profile_id="PRF-CANON",
        profile_version="1.0.0",
        strategy_id="CONTINUATION",
        strategy_version="1.0.0",
        market="NSE",
        instrument_class="EQUITY",
        horizon="INTRADAY",
        timeframes=("15m", "5m"),
        setups=("BREAKOUT", "RETEST"),
        directions=("SHORT", "LONG"),
        required_to_calculate=("volume", "closed_bars"),
        required_to_qualify=("liquidity",),
        optional_context=("event",),
        prohibited_for_condition=("future_data",),
        relative_strength_contract="same-time-sector-v1",
        gate_policy="tradability-v1",
        ranking_group="intraday-continuation",
        risk_cost_assumptions=("slippage-v1", "cost-v1"),
        model_id=None,
        model_version=None,
        model_hash=None,
        research_ceiling="WAIT",
        activation_allowed=False,
        created_at=NOW,
        valid_from=NOW,
    )
    values.update(changes)
    return governance.build_strategy_profile_version(**values)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), object()])
def test_semantic_identity_rejects_non_json_or_non_finite_values(bad):
    with pytest.raises(ValueError, match="SEMANTIC|FINITE|UNSUPPORTED"):
        history.canonical_json({"bad": bad})


def test_semantic_identity_rejects_non_string_mapping_keys():
    with pytest.raises(ValueError, match="KEYS|STRING"):
        history.canonical_json({1: "not-semantic-json"})


def test_member_identity_normalizes_hash_case_and_set_like_input_order():
    first = _member(
        input_hashes=(H5, H6),
        evidence_roots=({"role": "A", "contentHash": H5}, {"role": "B", "contentHash": H6}),
    )
    second = _member(
        decision_version_hash=H1.upper(),
        outcome_hash=H2.upper(),
        feature_manifest_hash=H3.upper(),
        formula_set_hash=H4.upper(),
        input_hashes=(H6.upper(), H5.upper()),
        evidence_roots=({"role": "B", "contentHash": H6.upper()}, {"role": "A", "contentHash": H5.upper()}),
    )
    assert second.decision_version_hash == H1
    assert second.input_hashes == first.input_hashes
    assert second.member_hash == first.member_hash


def test_profile_identity_normalizes_timezone_and_set_like_semantic_order():
    india = timezone(timedelta(hours=5, minutes=30))
    first = _profile()
    second = _profile(
        timeframes=("5m", "15m"),
        setups=("RETEST", "BREAKOUT"),
        directions=("LONG", "SHORT"),
        required_to_calculate=("closed_bars", "volume"),
        risk_cost_assumptions=("cost-v1", "slippage-v1"),
        created_at=NOW.astimezone(india),
        valid_from=NOW.astimezone(india),
    )
    assert second.created_at.tzinfo == UTC
    assert second.content_hash == first.content_hash


def test_rhist03d_artifact_and_link_identity_are_sql_immutable(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    assert r18_store.persist_strategy_profile(profile) is True
    with storage.connect() as conn:
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            conn.execute(
                "UPDATE strategy_profile_versions SET model_id='tampered' WHERE profile_id=?",
                (profile.profile_id,),
            )
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            conn.execute(
                "DELETE FROM r18_retention_links WHERE artifact_id=?",
                (profile.profile_id,),
            )


class _LockedAuthority:
    def register(self, _reference):
        raise sqlite3.OperationalError("database is locked")


def test_typed_sqlite_lock_remains_retryable_pending(tmp_path):
    db_path = tmp_path / "typed-lock.db"
    registrar = DurableRetentionRegistrar(db_path=db_path, authority=_LockedAuthority())
    receipt = registrar.enqueue(
        RetentionEvidenceIntent(
            artifact_type="R18_STRATEGY_PROFILE",
            artifact_id="P1",
            artifact_version="1",
            reference_type=RetentionReferenceType.STRATEGY_PROFILE,
            artifact_hash=H1,
            created_at=NOW,
        )
    )
    result = registrar.dispatch(receipt.event_id)
    assert result.status is RetentionOutboxStatus.PENDING
    assert result.attempts == 1
    assert result.last_error is not None and "locked" in result.last_error.lower()


def test_legacy_sqlite_lock_keeps_existing_blocking_semantics(tmp_path):
    db_path = tmp_path / "legacy-lock.db"
    registrar = DurableRetentionRegistrar(db_path=db_path, authority=_LockedAuthority())
    receipt = registrar.enqueue(
        RetentionEvidenceIntent(
            artifact_type="S8_DECISION_VERSION:R1_INPUT",
            artifact_id="S8-1",
            artifact_version="v1",
            reference_type=RetentionReferenceType.DECISION_VERSION,
            content_hash=H1,
            created_at=NOW,
        )
    )
    result = registrar.dispatch(receipt.event_id)
    assert result.status is RetentionOutboxStatus.FAILED_BLOCKING


def test_preflight_detects_pre_fix_applied_typed_reference_even_without_old_outbox(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    with storage.connect() as conn:
        conn.execute(
            "INSERT INTO historical_retention_references("
            "reference_id,reference_type,content_hash,run_id,trading_date,artifact_id,"
            "artifact_version,artifact_hash,permanent,retain_until,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            ("old-profile-ref", "STRATEGY_PROFILE", H1, None, None, None, None, None, 1, None, NOW.isoformat()),
        )
        conn.commit()
    inventory = r18_store.rhist03d_preflight_inventory()
    assert inventory["preFixAppliedTypedReferences"] == 1
    assert inventory["stopRequired"] is True


def test_authoritative_parent_availability_cannot_be_backdated(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    decision = {
        "schemaVersion": "trendforge.r16-pit.v1",
        "decisionCutoffAt": DECISION.isoformat(),
        "maxInputAvailableAt": (DECISION + timedelta(minutes=1)).isoformat(),
        "profileId": "PRF-R16-NSE-CASH-EOD-SWING",
        "profileVersion": "1.0.0",
        "timeframe": "EOD",
        "publicState": "WATCH",
        "setupPolicyId": "SWING_BREAKOUT_BREAKDOWN_V1",
        "sourceBarHashes": [H5],
        "sourceFeatureHashes": {"s8": H3},
    }
    decision_hash = completion.r16_payload_hash(decision)
    publication = SimpleNamespace(evidence_roots=(SimpleNamespace(content_hash=H5),))

    def _verified(_conn, record_type, record_id):
        assert record_type == "DECISION_VERSION"
        assert record_id == "D100v1"
        return SimpleNamespace(), decision, publication

    payload = {
        "members": [{
            "decisionVersionId": "D100v1",
            "decisionVersionHash": decision_hash,
            "decisionAt": DECISION.isoformat(),
            "decisionDataCutoff": DECISION.isoformat(),
            "maxFeatureAvailableAt": (DECISION - timedelta(seconds=1)).isoformat(),
            "profileId": "PRF-R16-NSE-CASH-EOD-SWING",
            "profileVersion": "1.0.0",
            "timeframe": "EOD",
            "publicState": "WATCH",
            "setupId": "SWING_BREAKOUT_BREAKDOWN_V1",
            "inputHashes": [H5],
            "evidenceRoots": [{"role": "DECISION", "contentHash": H5}],
        }]
    }
    with pytest.raises(RuntimeError, match="AVAILABILITY|CUTOFF|FEATURE"):
        completion.verify_dataset_r16_parents(payload, verifier=_verified)
