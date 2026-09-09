"""R-HIST-03D red matrix for frozen dataset/model/profile/audit history.

These tests deliberately target the existing R18 governance/store owners. 03D must
extend those owners and the existing retention publication path rather than create
a parallel model registry or retention database.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from trendforge_api import storage
from trendforge_api.selection import r18_governance as governance
from trendforge_api.selection import r18_store


NOW = datetime(2026, 9, 9, 4, 0, tzinfo=UTC)
DECISION = NOW - timedelta(days=8)
DECISION_CUTOFF = DECISION + timedelta(hours=1)
LABEL = DECISION + timedelta(days=3)
BUILD = DECISION + timedelta(days=5)
H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64
H6 = "6" * 64
H7 = "7" * 64
H8 = "8" * 64


def _required(module, name: str):
    value = getattr(module, name, None)
    assert value is not None, f"R-HIST-03D API missing from canonical owner: {name}"
    return value


def _member(**changes):
    build = _required(governance, "build_frozen_dataset_member")
    values = dict(
        instrument_id="NSE:INFY:EQ",
        opportunity_id="INFY:5m:continuation:SHORT",
        profile_id="PRF-001",
        profile_version="1.0.0",
        strategy_id="CONTINUATION",
        strategy_version="1.0.0",
        setup_id="BREAKOUT_CONTINUATION",
        setup_episode_id="episode-1",
        timeframe="5m",
        horizon="INTRADAY",
        direction="SHORT",
        decision_version_id="D100v1",
        decision_version_hash=H1,
        decision_at=DECISION,
        decision_data_cutoff=DECISION,
        max_feature_available_at=DECISION - timedelta(seconds=1),
        public_state="WATCH",
        outcome_id="O1",
        outcome_hash=H2,
        outcome_available_at=LABEL,
        revision_id=None,
        revision_hash=None,
        revision_available_at=None,
        label_available_at=LABEL,
        feature_manifest_id="feature-manifest-v1",
        feature_manifest_hash=H3,
        formula_set_version="formula-v1",
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
    return build(**values)


def _dataset(*members, **changes):
    build = _required(governance, "build_frozen_dataset_manifest")
    if not members:
        members = (_member(),)
    values = dict(
        dataset_id="D7",
        dataset_version="1.0.0",
        purpose="TRAIN",
        created_at=BUILD,
        decision_cutoff=DECISION_CUTOFF,
        label_cutoff=LABEL + timedelta(hours=1),
        build_cutoff=BUILD,
        population_policy_id="R16_COMPLETE_BASE_POPULATION",
        population_policy_version="1.0.0",
        label_policy_id="R16_LABEL_POLICY",
        label_policy_version="1.0.0",
        feature_manifest_id="feature-manifest-v1",
        feature_manifest_hash=H3,
        formula_set_version="formula-v1",
        formula_set_hash=H4,
        cost_model_version="cost-v1",
        members=tuple(members),
        base_population=True,
        source_population_count=len(members),
        exclusion_reason_distribution={},
        parent_dataset_id=None,
        parent_dataset_hash=None,
        code_digest=H7,
    )
    values.update(changes)
    return build(**values)


def _set_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "rhist03d.db")
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()


def test_schema_is_additive_explicit_and_has_first_class_history_tables(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    status_fn = _required(r18_store, "rhist03d_schema_status")
    apply_fn = _required(r18_store, "apply_rhist03d_schema")
    assert status_fn()["applied"] is False
    applied = apply_fn()
    assert applied["applied"] is True
    assert set(applied["tables"]) >= {
        "ml_frozen_datasets",
        "ml_frozen_dataset_members",
        "ml_governed_model_versions",
        "strategy_profile_versions",
        "governance_audit_records",
        "r18_retention_links",
    }


def test_same_symbol_independent_opportunities_are_distinct_members():
    first = _member()
    second = _member(
        opportunity_id="INFY:5m:failed-breakdown:LONG",
        strategy_id="FAILED_BREAKDOWN_REVERSAL",
        setup_id="FAILED_BREAKDOWN_REVERSAL",
        setup_episode_id="episode-2",
        direction="LONG",
        decision_version_id="D101v1",
        decision_version_hash=H8,
    )
    manifest = _dataset(first, second, source_population_count=2)
    assert manifest.member_count == 2
    assert len({row.member_id for row in manifest.members}) == 2
    assert {row.direction for row in manifest.members} == {"LONG", "SHORT"}


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"max_feature_available_at": DECISION + timedelta(seconds=1)}, "FUTURE_FEATURE"),
        ({"decision_data_cutoff": DECISION - timedelta(seconds=1)}, "DECISION_CUTOFF"),
        ({"outcome_available_at": BUILD + timedelta(days=1)}, "FUTURE_LABEL"),
        ({"label_available_at": BUILD + timedelta(days=1)}, "FUTURE_LABEL"),
    ],
)
def test_future_information_is_rejected(changes, message):
    with pytest.raises(ValueError, match=message):
        _member(**changes)


def test_dataset_separates_decision_label_and_build_cutoffs():
    member = _member()
    manifest = _dataset(member)
    assert manifest.decision_cutoff < manifest.label_cutoff < manifest.build_cutoff
    with pytest.raises(ValueError, match="DATASET_CUTOFF_ORDER"):
        _dataset(member, label_cutoff=DECISION_CUTOFF - timedelta(seconds=1))


def test_duplicate_members_are_rejected_deterministically():
    member = _member()
    with pytest.raises(ValueError, match="DUPLICATE_DATASET_MEMBER"):
        _dataset(member, member, source_population_count=2)


def test_dataset_hash_is_deterministic_and_member_order_independent():
    first = _member()
    second = _member(
        opportunity_id="INFY:daily:swing:LONG",
        profile_id="PRF-003",
        strategy_id="SWING_CONTINUATION",
        setup_id="SWING_CONTINUATION",
        setup_episode_id="episode-3",
        timeframe="EOD",
        horizon="SWING",
        direction="LONG",
        decision_version_id="D102v1",
        decision_version_hash=H8,
    )
    forward = _dataset(first, second, source_population_count=2)
    reverse = _dataset(second, first, source_population_count=2)
    assert forward.dataset_hash == reverse.dataset_hash
    assert forward.member_manifest_hash == reverse.member_manifest_hash


def test_complete_nontrade_ambiguous_and_censored_population_is_frozen():
    members = (
        _member(public_state="WAIT", outcome_id=None, outcome_hash=None, outcome_available_at=None, label_available_at=None),
        _member(
            opportunity_id="INFY:reject", decision_version_id="D101v1", decision_version_hash=H7,
            public_state="REJECT", outcome_id=None, outcome_hash=None, outcome_available_at=None,
            label_available_at=None, setup_episode_id="episode-2",
        ),
        _member(
            opportunity_id="INFY:ambiguous", decision_version_id="D102v1", decision_version_hash=H8,
            public_state="WATCH", outcome_id="O2", outcome_hash=H6, outcome_state="AMBIGUOUS",
            setup_episode_id="episode-3",
        ),
        _member(
            opportunity_id="INFY:censored", decision_version_id="D103v1", decision_version_hash="9" * 64,
            public_state="WATCH", outcome_id="O3", outcome_hash="a" * 64, outcome_state="CENSORED",
            setup_episode_id="episode-4",
        ),
    )
    manifest = _dataset(*members, source_population_count=4)
    assert manifest.state_distribution["WAIT"] == 1
    assert manifest.state_distribution["REJECT"] == 1
    assert manifest.outcome_distribution["AMBIGUOUS"] == 1
    assert manifest.outcome_distribution["CENSORED"] == 1


def test_winner_only_base_population_is_prohibited():
    winner = _member(outcome_state="TARGET_HIT")
    with pytest.raises(ValueError, match="BASE_POPULATION_INCOMPLETE"):
        _dataset(winner, source_population_count=10)


def test_transformed_population_requires_frozen_exclusion_policy_and_counts():
    winner = _member(outcome_state="TARGET_HIT")
    with pytest.raises(ValueError, match="EXCLUSION_POLICY_REQUIRED"):
        _dataset(
            winner,
            base_population=False,
            source_population_count=10,
            exclusion_reason_distribution={"NO_ENTRY": 9},
            transformation_policy_id=None,
            transformation_policy_version=None,
        )


def test_feature_manifest_or_member_evidence_tamper_is_detected():
    verify = _required(governance, "verify_frozen_dataset_manifest")
    manifest = _dataset()
    verify(manifest, available_evidence_hashes={H5, H6})
    payload = manifest.model_dump(mode="json")
    payload["featureManifestHash"] = "f" * 64
    with pytest.raises(ValueError, match="DATASET_HASH_MISMATCH|FEATURE_MANIFEST"):
        verify(payload, available_evidence_hashes={H5, H6})
    with pytest.raises(ValueError, match="EVIDENCE.*MISSING"):
        verify(manifest, available_evidence_hashes={H5})


def test_source_and_outcome_corrections_create_new_dataset_without_rewriting_old():
    original = _dataset(_member())
    corrected = _dataset(
        _member(outcome_id="O2", outcome_hash=H8, outcome_available_at=LABEL + timedelta(minutes=5), label_available_at=LABEL + timedelta(minutes=5)),
        dataset_id="D8",
        parent_dataset_id=original.dataset_id,
        parent_dataset_hash=original.dataset_hash,
        label_cutoff=LABEL + timedelta(hours=2),
    )
    assert corrected.dataset_hash != original.dataset_hash
    assert corrected.parent_dataset_hash == original.dataset_hash
    assert original.members[0].outcome_id == "O1"
    assert original.members[0].outcome_hash == H2


def test_model_version_binds_exact_training_evaluation_and_artifact_hashes():
    build = _required(governance, "build_governed_model_version")
    train = _dataset()
    evaluation = _dataset(_member(split="VALIDATION", fold="HOLDOUT"), dataset_id="D7-eval", purpose="VALIDATION")
    model = build(
        model_id="trigger-quality",
        model_version="2.0.0",
        purpose="trigger quality",
        market="NSE_EQUITY",
        horizon="INTRADAY",
        training_dataset=train,
        evaluation_dataset=evaluation,
        holdout_dataset=evaluation,
        feature_set_hash=H3,
        formula_set_hash=H4,
        model_artifact_hash=H5,
        code_build_hash=H7,
        config_hash=H8,
        hyperparameters={"depth": 3},
        random_seeds=(17,),
        cost_model_version="cost-v1",
        evaluation_id="eval-1",
        evaluation_hash=H6,
        created_at=BUILD,
    )
    assert model.training_dataset_id == train.dataset_id
    assert model.training_dataset_hash == train.dataset_hash
    assert model.evaluation_dataset_hash == evaluation.dataset_hash
    assert model.model_artifact_hash == H5


def test_model_rejects_wrong_dataset_artifact_and_evaluation_bindings():
    build = _required(governance, "build_governed_model_version")
    dataset = _dataset()
    with pytest.raises(ValueError, match="MODEL_DATASET_BINDING"):
        build(
            model_id="m", model_version="1", purpose="p", market="NSE_EQUITY", horizon="INTRADAY",
            training_dataset=dataset, training_dataset_hash="f" * 64,
            evaluation_dataset=dataset, feature_set_hash=H3, formula_set_hash=H4,
            model_artifact_hash="bad", code_build_hash=H7, config_hash=H8,
            hyperparameters={}, random_seeds=(17,), cost_model_version="cost-v1",
            evaluation_id="eval", evaluation_hash=H6, created_at=BUILD,
        )


def test_profile_semantic_change_requires_new_version_and_exact_model_binding():
    build = _required(governance, "build_strategy_profile_version")
    profile = build(
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
        model_id="trigger-quality",
        model_version="2.0.0",
        model_hash=H5,
        research_ceiling="WAIT",
        activation_allowed=False,
        created_at=BUILD,
        valid_from=BUILD,
    )
    same = build(**profile.model_dump(exclude={"content_hash"}))
    assert same.content_hash == profile.content_hash
    mutated = profile.model_dump(exclude={"content_hash"})
    mutated["ranking_group"] = "changed"
    changed = build(**mutated)
    assert changed.content_hash != profile.content_hash


def test_profile_store_rejects_semantic_mutation_under_same_version(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    _required(r18_store, "apply_rhist03d_schema")()
    build = _required(governance, "build_strategy_profile_version")
    persist = _required(r18_store, "persist_strategy_profile")
    base = build(
        profile_id="PRF-001", profile_version="1.0.0", strategy_id="CONT", strategy_version="1",
        market="NSE", instrument_class="EQUITY", horizon="INTRADAY", timeframes=("5m",),
        setups=("CONT",), directions=("LONG", "SHORT"), required_to_calculate=("bars",),
        required_to_qualify=("liquidity",), optional_context=(), prohibited_for_condition=("future",),
        relative_strength_contract="rs-v1", gate_policy="gates-v1", ranking_group="g1",
        risk_cost_assumptions=("cost-v1",), model_id=None, model_version=None, model_hash=None,
        research_ceiling="WAIT", activation_allowed=False, created_at=BUILD, valid_from=BUILD,
    )
    assert persist(base) is True
    changed = build(**{**base.model_dump(exclude={"content_hash"}), "ranking_group": "g2"})
    with pytest.raises(ValueError, match="PROFILE_VERSION_IMMUTABLE"):
        persist(changed)


def test_audit_chain_rejects_predecessor_tamper_and_approval_without_pit():
    build = _required(governance, "build_governance_audit_record")
    first = build(
        audit_id="A1", reviewed_artifact_type="MODEL_VERSION", artifact_id="m",
        artifact_version="1", artifact_hash=H5, dataset_id="D7", dataset_hash=H1,
        model_id="m", model_hash=H5, profile_id="PRF-001", profile_hash=H6,
        evaluation_id="eval", evaluation_hash=H7, predecessor_audit_hash=None,
        decision="REJECT", reviewer="risk", reason="insufficient proof", reviewed_at=BUILD,
        evidence_hash=H8, governance_policy_version="gov-v1", pit_prerequisite_proven=False,
        resulting_state="REJECTED",
    )
    assert len(first.record_hash) == 64
    with pytest.raises(ValueError, match="PIT_PREREQUISITE"):
        build(**{**first.model_dump(exclude={"record_hash"}), "audit_id": "A2", "decision": "APPROVE", "pit_prerequisite_proven": False})


def test_audit_store_refuses_wrong_predecessor_hash(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    _required(r18_store, "apply_rhist03d_schema")()
    build = _required(governance, "build_governance_audit_record")
    persist = _required(r18_store, "persist_audit_record")
    first = build(
        audit_id="A1", reviewed_artifact_type="MODEL_VERSION", artifact_id="m", artifact_version="1",
        artifact_hash=H5, dataset_id="D7", dataset_hash=H1, model_id="m", model_hash=H5,
        profile_id=None, profile_hash=None, evaluation_id="eval", evaluation_hash=H7,
        predecessor_audit_hash=None, decision="REJECT", reviewer="risk", reason="reason",
        reviewed_at=BUILD, evidence_hash=H8, governance_policy_version="gov-v1",
        pit_prerequisite_proven=False, resulting_state="REJECTED",
    )
    assert persist(first) is True
    second = build(**{
        **first.model_dump(exclude={"record_hash"}), "audit_id": "A2",
        "predecessor_audit_hash": "f" * 64, "reviewed_at": BUILD + timedelta(seconds=1),
    })
    with pytest.raises(ValueError, match="AUDIT_PREDECESSOR"):
        persist(second)


def test_dataset_persist_is_artifact_plus_outbox_atomic(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    _required(r18_store, "apply_rhist03d_schema")()
    persist = _required(r18_store, "persist_frozen_dataset")
    with pytest.raises(RuntimeError, match="INJECTED_AFTER_ARTIFACT"):
        persist(_dataset(), fault_point="AFTER_ARTIFACT_INSERT")
    with storage.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM ml_frozen_datasets").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[0] == 0


def test_post_commit_dispatch_failure_keeps_dataset_governed_hidden(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    _required(r18_store, "apply_rhist03d_schema")()
    persist = _required(r18_store, "persist_frozen_dataset")
    governed = _required(r18_store, "get_governed_frozen_dataset")
    dataset = _dataset()
    receipt = persist(dataset)
    assert receipt["stored"] is True
    assert receipt["publicationStatus"] == "PENDING_RETENTION"
    assert governed(dataset.dataset_id, dataset.dataset_version) is None


def test_governed_read_is_pure_and_legacy_rows_are_not_backfilled(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    _required(r18_store, "apply_rhist03d_schema")()
    governed = _required(r18_store, "get_governed_frozen_dataset")
    with storage.connect() as conn:
        conn.execute(
            "INSERT INTO ml_frozen_datasets(record_id,dataset_id,dataset_version,dataset_hash,payload_json,content_hash,created_at) VALUES(?,?,?,?,?,?,?)",
            ("legacy", "D-legacy", "0", H1, "{}", H2, BUILD.isoformat()),
        )
        conn.commit()
        before = conn.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[0]
    assert governed("D-legacy", "0") is None
    with storage.connect() as conn:
        after = conn.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[0]
        assert after == before
        assert conn.total_changes == 0


def test_corrupt_dataset_payload_or_retention_link_is_refused_on_read(tmp_path, monkeypatch):
    _set_db(tmp_path, monkeypatch)
    _required(r18_store, "apply_rhist03d_schema")()
    persist = _required(r18_store, "persist_frozen_dataset")
    verify_stored = _required(r18_store, "verify_stored_rhist03d_artifact")
    dataset = _dataset()
    persist(dataset)
    with storage.connect() as conn:
        conn.execute("UPDATE ml_frozen_datasets SET payload_json='{}' WHERE dataset_id=?", (dataset.dataset_id,))
        conn.commit()
    with pytest.raises(ValueError, match="CORRUPT|HASH"):
        verify_stored("ML_DATASET", dataset.dataset_id, dataset.dataset_version)


def test_model_profile_and_audit_artifacts_are_not_execution_authority():
    assert _required(governance, "R_HIST_03D_EXECUTION_AUTHORIZED") is False
    assert _required(governance, "R_HIST_03D_AUTOMATIC_PROMOTION_ALLOWED") is False
