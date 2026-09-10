from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trendforge_api import storage
from trendforge_api.selection import r18_governance as governance
from trendforge_api.selection import r18_store


NOW = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)


def _set_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "rhist03d-finalize.db")
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    r18_store.apply_rhist03d_schema()


def _profile():
    return governance.build_strategy_profile_version(
        profile_id="PRF-FINALIZE",
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
        optional_context=(),
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


def test_profile_finalizer_applies_exact_typed_retention_and_replays(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    assert r18_store.persist_strategy_profile(profile) is True

    result = r18_store.finalize_rhist03d_artifact(
        "STRATEGY_PROFILE",
        profile.profile_id,
        profile.profile_version,
        verify_parents=False,
    )
    assert result["contentHash"] == profile.content_hash

    replay = r18_store.finalize_rhist03d_artifact(
        "STRATEGY_PROFILE",
        profile.profile_id,
        profile.profile_version,
        verify_parents=False,
    )
    assert replay == result

    with storage.connect() as conn:
        artifact = conn.execute(
            "SELECT publication_state FROM strategy_profile_versions WHERE profile_id=?",
            (profile.profile_id,),
        ).fetchone()
        link = conn.execute(
            "SELECT publication_state FROM r18_retention_links WHERE artifact_type='STRATEGY_PROFILE' "
            "AND artifact_id=? AND artifact_version=?",
            (profile.profile_id, profile.profile_version),
        ).fetchone()
        outbox = conn.execute(
            "SELECT status,content_hash,artifact_hash FROM historical_retention_outbox"
        ).fetchone()
        reference = conn.execute(
            "SELECT content_hash,artifact_hash FROM historical_retention_references"
        ).fetchone()
    assert artifact["publication_state"] == "APPLIED"
    assert link["publication_state"] == "APPLIED"
    assert outbox["status"] == "APPLIED"
    assert outbox["content_hash"] is None
    assert outbox["artifact_hash"] == profile.content_hash
    assert reference["content_hash"] is None
    assert reference["artifact_hash"] == profile.content_hash


def test_crash_after_outbox_applied_keeps_local_state_hidden_then_replays(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    r18_store.persist_strategy_profile(profile)

    with pytest.raises(RuntimeError, match="INJECTED_AFTER_OUTBOX_APPLIED"):
        r18_store.finalize_rhist03d_artifact(
            "STRATEGY_PROFILE",
            profile.profile_id,
            profile.profile_version,
            fault_point="AFTER_OUTBOX_APPLIED",
            verify_parents=False,
        )

    with storage.connect() as conn:
        artifact = conn.execute(
            "SELECT publication_state FROM strategy_profile_versions WHERE profile_id=?",
            (profile.profile_id,),
        ).fetchone()
        link = conn.execute(
            "SELECT publication_state FROM r18_retention_links WHERE artifact_id=?",
            (profile.profile_id,),
        ).fetchone()
        outbox = conn.execute("SELECT status FROM historical_retention_outbox").fetchone()
    assert artifact["publication_state"] == "PENDING_RETENTION"
    assert link["publication_state"] == "PENDING_RETENTION"
    assert outbox["status"] == "APPLIED"

    result = r18_store.finalize_rhist03d_artifact(
        "STRATEGY_PROFILE",
        profile.profile_id,
        profile.profile_version,
        verify_parents=False,
    )
    assert result["contentHash"] == profile.content_hash


def test_crash_before_local_commit_rolls_back_both_local_states(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    profile = _profile()
    r18_store.persist_strategy_profile(profile)

    with pytest.raises(RuntimeError, match="INJECTED_BEFORE_LOCAL_COMMIT"):
        r18_store.finalize_rhist03d_artifact(
            "STRATEGY_PROFILE",
            profile.profile_id,
            profile.profile_version,
            fault_point="BEFORE_LOCAL_COMMIT",
            verify_parents=False,
        )

    with storage.connect() as conn:
        artifact = conn.execute(
            "SELECT publication_state FROM strategy_profile_versions WHERE profile_id=?",
            (profile.profile_id,),
        ).fetchone()
        link = conn.execute(
            "SELECT publication_state FROM r18_retention_links WHERE artifact_id=?",
            (profile.profile_id,),
        ).fetchone()
    assert artifact["publication_state"] == "PENDING_RETENTION"
    assert link["publication_state"] == "PENDING_RETENTION"


def test_preflight_stops_on_old_applied_typed_event(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    with storage.connect() as conn:
        conn.execute(
            "INSERT INTO historical_retention_outbox("
            "event_id,reference_id,artifact_type,artifact_id,artifact_version,reference_type,"
            "run_id,trading_date,content_hash,artifact_hash,payload_json,payload_hash,status,"
            "attempts,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "old-event",
                "old-ref",
                "R18_STRATEGY_PROFILE",
                "OLD",
                "1",
                "STRATEGY_PROFILE",
                None,
                None,
                "a" * 64,
                None,
                "{}",
                "b" * 64,
                "APPLIED",
                1,
                NOW.isoformat(),
            ),
        )
        conn.commit()

    inventory = r18_store.rhist03d_preflight_inventory()
    assert inventory["preFixAppliedTypedEvents"] == 1
    assert inventory["stopRequired"] is True
    with pytest.raises(RuntimeError, match="PREFIX_APPLIED_TYPED_IDENTITY"):
        r18_store.assert_rhist03d_upgrade_safe()
