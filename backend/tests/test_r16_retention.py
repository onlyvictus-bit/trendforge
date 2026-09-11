"""R-HIST-03C adversarial acceptance against real SQLite and market objects."""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from trendforge_api import storage
from trendforge_api.historical_retention import (
    HistoricalRetentionAuthority,
    RetentionReferenceType,
)
from trendforge_api.market_data_store import (
    MANIFEST_SCHEMA_VERSION,
    ManifestEntry,
    ManifestStatus,
    MarketDataStore,
    SnapshotManifest,
)
from trendforge_api.retention_producer import DurableRetentionRegistrar
from trendforge_api.retention_publication import (
    RetentionEvidenceRoot,
    RetentionPublicationRequest,
    RetentionPublicationStore,
)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def install_bar(env, day, *, high=101.0, low=99.0, close=100.0):
    from trendforge_api.selection.cash_a4_history import (
        CashRawSessionBar,
        _store_raw_bar,
    )

    raw = {"day": day.isoformat(), "high": high, "low": low, "close": close}
    obj = env.market.install_object(
        json.dumps(raw).encode(), extension="json", media_type="application/json"
    )
    _store_raw_bar(
        CashRawSessionBar(
            bar_id="bar-" + obj.content_hash,
            instrument_id="NSE:AAA:EQ",
            symbol="AAA",
            trade_date=day,
            artifact_hash=obj.content_hash,
            series_id="raw-AAA",
            open=close,
            high=high,
            low=low,
            close=close,
            previous_close=close,
            volume=1000,
            traded_value=100000,
        )
    )
    return obj


def publish_parent(env, payload=None, roots=None):
    from trendforge_api.selection.s8_persist_run import PROFILE_ID
    from trendforge_api.selection.store import persist_selection_payload

    payload = copy.deepcopy(payload or env.s8)
    roots = roots or env.roots
    request = RetentionPublicationRequest(
        artifact_type="S8_DECISION_VERSION",
        artifact_id=payload["runId"],
        artifact_version=payload["schemaVersion"],
        reference_type=RetentionReferenceType.DECISION_VERSION,
        evidence_roots=roots,
        lineage={
            "s8": payload["lineage"],
            "s8PayloadHash": digest(payload),
            "tradingDate": payload["tradingDate"],
        },
        created_at=datetime.fromisoformat(payload["asOf"]),
    )
    receipt = env.publications.stage_owned(request)
    env.publications.finalize(receipt.publication_id)
    persist_selection_payload(
        run_id=payload["runId"],
        profile_id=PROFILE_ID,
        as_of=datetime.fromisoformat(payload["asOf"]),
        payload=payload,
    )
    env.publications.mark_published(receipt.publication_id)
    return request


@pytest.fixture
def env(tmp_path, monkeypatch):
    from trendforge_api.selection.r16_store import apply_r16_schema

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "research.db")
    monkeypatch.delenv("TRENDFORGE_MARKET_DATA_DB_PATH", raising=False)
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    apply_r16_schema()
    market = MarketDataStore(root=tmp_path / "market", db_path=storage.DB_PATH)
    market.initialize_schema()
    authority = HistoricalRetentionAuthority(db_path=storage.DB_PATH)
    authority.initialize_schema()
    publications = RetentionPublicationStore(
        db_path=storage.DB_PATH,
        registrar=DurableRetentionRegistrar(
            db_path=storage.DB_PATH, authority=authority
        ),
    )
    obj = SimpleNamespace(market=market, authority=authority, publications=publications)
    objects = []
    for index in range(22):
        high, low, close = (101.0, 99.0, 100.0) if index < 8 else (110.0, 108.0, 109.0)
        if index == 19:
            low = 107.9
        objects.append(
            install_bar(
                obj,
                date(2026, 7, 1) + timedelta(days=index),
                high=high,
                low=low,
                close=close,
            )
        )
    obj.objects = objects
    obj.roots = tuple(
        RetentionEvidenceRoot(role=f"R1_INPUT_{index}", content_hash=bar.content_hash)
        for index, bar in enumerate(objects)
    )
    obj.s8 = {
        "schemaVersion": "trendforge.s8-scan.v1",
        "runId": "s8-original",
        "asOf": "2026-08-03T14:00:00+00:00",
        "tradingDate": "2026-08-03",
        "lineage": {
            key: "exact-" + key
            for key in (
                "r1RunHash",
                "r2RunHash",
                "r14RunHash",
                "r5RunHash",
                "s2RunId",
                "s3RunId",
                "s4PackId",
                "s5RunId",
                "s6RunId",
                "s7RunId",
                "nativeGuidanceRunHash",
            )
        },
        "s3Completeness": {"ratio": 1.0, "threshold": 0.95},
        "rows": [
            {
                "candidateId": "AAA-breakout",
                "symbol": "AAA",
                "publicState": "WATCH",
                "evidenceDirection": "BULLISH",
            }
        ],
    }
    obj.request = publish_parent(obj)
    return obj


def freeze(env, *, payload=None, revision="r16-original"):
    from trendforge_api.r16_retention import freeze_s8_hypotheses
    from trendforge_api.selection.r16_service import _dataset_payload
    from trendforge_api.selection.r16_store import persist_dataset_run

    s8 = payload or env.s8
    hypotheses = freeze_s8_hypotheses(s8_payload=s8, dataset_revision_hash=revision)
    dataset = _dataset_payload(
        s8_payload=s8, revision_hash=revision, hypotheses=hypotheses
    )
    persist_dataset_run(dataset)
    return dataset, hypotheses


def save_hypothesis(env):
    from trendforge_api.selection.r16_store import persist_hypotheses

    dataset, hypotheses = freeze(env)
    persist_hypotheses(
        dataset["runId"],
        [row.model_dump(mode="json", by_alias=True) for row in hypotheses],
    )
    return dataset, hypotheses[0]


def observation(env, hypothesis, day=date(2026, 8, 4)):
    from trendforge_api.selection.r16_pit import label_hypothesis

    obj = install_bar(env, day, high=113.0, low=109.0, close=110.0)
    return label_hypothesis(
        hypothesis,
        bars=[
            {
                "trade_date": day.isoformat(),
                "available_at": f"{day.isoformat()}T13:00:00+00:00",
                "open": 110.0,
                "high": 113.0,
                "low": 109.0,
                "close": 110.0,
                "artifact_hash": obj.content_hash,
            }
        ],
    )


def test_exact_parent_is_accepted_with_immutable_identity(env):
    from trendforge_api.selection.r16_store import list_hypotheses

    dataset, hypothesis = save_hypothesis(env)
    assert hypothesis.source_s8_publication_id == env.request.publication_id
    assert hypothesis.source_s8_version == env.s8["schemaVersion"]
    assert hypothesis.source_s8_publication_lineage_hash == env.request.lineage_hash
    assert len(list_hypotheses(dataset["runId"])) == 3
    assert hypothesis.geometry_status == "READY"
    assert set(hypothesis.source_bar_hashes).issubset(
        {root.content_hash for root in env.roots}
    )


@pytest.mark.parametrize(
    "change",
    [
        {"source_s8_run_id": "absent"},
        {"source_s8_version": "trendforge.s8-scan.v999"},
        {"source_s8_hash": "f" * 64},
        {"source_s8_lineage_hash": "e" * 64},
        {"source_s8_publication_id": "wrong-publication"},
        {"source_s8_publication_lineage_hash": "d" * 64},
        {"source_bar_hashes": ("c" * 64,)},
    ],
)
def test_wrong_missing_or_mismatched_parent_fails_closed(env, change):
    from trendforge_api.selection.r16_store import list_hypotheses, persist_hypotheses

    dataset, rows = freeze(env)
    changed = rows[0].model_copy(update=change)
    with pytest.raises((ValueError, RuntimeError), match="WAIT_RHIST03"):
        persist_hypotheses(
            dataset["runId"], [changed.model_dump(mode="json", by_alias=True)]
        )
    assert list_hypotheses(dataset["runId"]) == []


@pytest.mark.parametrize(
    "tamper", ["payload", "lineage", "member", "outbox", "reference", "object"]
)
def test_parent_corruption_is_not_trusted_even_when_marked_published(env, tamper):
    from trendforge_api.r16_retention import freeze_s8_hypotheses

    with storage.connect() as conn:
        if tamper == "payload":
            bad = copy.deepcopy(env.s8)
            bad["rows"][0]["publicState"] = "REJECT"
            conn.execute(
                "UPDATE selection_scan_runs SET payload_json=? WHERE run_id=?",
                (storage.encode_json(bad), env.s8["runId"]),
            )
        elif tamper == "lineage":
            conn.execute(
                "UPDATE historical_retention_publications SET lineage_hash='tampered'"
            )
        elif tamper == "member":
            conn.execute(
                "DELETE FROM historical_retention_publication_members WHERE evidence_role='R1_INPUT_0'"
            )
        elif tamper == "outbox":
            conn.execute(
                "UPDATE historical_retention_outbox SET payload_hash='tampered'"
            )
        elif tamper == "reference":
            conn.execute("DELETE FROM historical_retention_references")
        else:
            env.objects[0].path.write_bytes(b"corrupt")
    with pytest.raises((ValueError, RuntimeError), match="WAIT_RHIST03"):
        freeze_s8_hypotheses(s8_payload=env.s8, dataset_revision_hash="revision")


def test_newer_s8_and_unbound_corrected_bars_cannot_replace_original(env):
    first_dataset, first = save_hypothesis(env)
    newer = copy.deepcopy(env.s8)
    newer["runId"] = "s8-newer"
    newer["asOf"] = "2026-08-04T14:00:00+00:00"
    newer["tradingDate"] = "2026-08-04"
    newer["rows"][0]["evidenceDirection"] = "BEARISH"
    publish_parent(env, newer)
    install_bar(env, date(2026, 7, 25), high=9000, low=8000, close=8500)
    dataset, hypotheses = freeze(env)
    assert dataset == first_dataset
    assert hypotheses[0] == first
    assert hypotheses[0].direction == "BULLISH"


@pytest.mark.parametrize(
    "state", ["CONFIRMED", "WATCH", "WAIT", "REJECT", "NO_ENTRY", "EXPIRED", "PAUSED"]
)
def test_all_original_states_are_retained_without_execution_authority(env, state):
    from trendforge_api.selection.r16_store import list_hypotheses, persist_hypotheses

    payload = copy.deepcopy(env.s8)
    payload["runId"] = "s8-state-" + state
    payload["rows"][0]["publicState"] = state
    publish_parent(env, payload)
    dataset, rows = freeze(env, payload=payload)
    assert {row.public_state for row in rows} == {state}
    persist_hypotheses(
        dataset["runId"], [row.model_dump(mode="json", by_alias=True) for row in rows]
    )
    assert len(list_hypotheses(dataset["runId"])) == 3
    assert all(
        not row.execution_authorized and not row.confirmation_authorized for row in rows
    )


def test_outcome_is_separate_and_duplicate_replay_is_idempotent(env):
    from trendforge_api.selection.r16_store import (
        list_hypotheses,
        list_observations,
        persist_observations,
    )

    dataset, hypothesis = save_hypothesis(env)
    before = list_hypotheses(dataset["runId"])
    result = observation(env, hypothesis)
    payload = result.model_dump(mode="json", by_alias=True)
    assert persist_observations(dataset["runId"], [payload]) == 1
    assert persist_observations(dataset["runId"], [payload]) == 0
    assert list_hypotheses(dataset["runId"]) == before
    assert len(list_observations(dataset["runId"])) == 1
    assert result.label_computed_at > hypothesis.decision_cutoff_at
    refs = env.authority.active_references(as_of_date=date(2026, 9, 9))
    assert any(ref.reference_type == RetentionReferenceType.OUTCOME for ref in refs)
    assert set(result.outcome_bar_hashes).issubset({ref.content_hash for ref in refs})


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_hypothesis_hash", "f" * 64),
        ("symbol", "OTHER"),
        ("dataset_revision_hash", "wrong"),
        ("source_s8_run_id", "newer"),
        ("path_hash", "e" * 64),
        ("label_computed_at", datetime(2026, 8, 1, tzinfo=UTC)),
    ],
)
def test_outcome_cannot_repoint_parent_or_time_or_path(env, field, value):
    from trendforge_api.selection.r16_store import (
        list_observations,
        persist_observations,
    )

    dataset, hypothesis = save_hypothesis(env)
    result = observation(env, hypothesis).model_copy(update={field: value})
    with pytest.raises((ValueError, RuntimeError), match="WAIT_RHIST03"):
        persist_observations(
            dataset["runId"], [result.model_dump(mode="json", by_alias=True)]
        )
    assert list_observations(dataset["runId"]) == []


def test_revision_links_predecessor_and_retains_new_evidence_without_rewriting(env):
    from trendforge_api.selection.r16_pit import R16RevisionV1
    from trendforge_api.selection.r16_store import (
        list_hypotheses,
        list_revisions,
        persist_revisions,
    )

    dataset, hypothesis = save_hypothesis(env)
    before = list_hypotheses(dataset["runId"])
    correction = env.market.install_object(
        b"corrected source", extension="txt", media_type="text/plain"
    )
    revision = R16RevisionV1(
        revision_id="revision-1",
        hypothesis_id=hypothesis.hypothesis_id,
        predecessor_type="DECISION_VERSION",
        predecessor_id=hypothesis.hypothesis_id,
        predecessor_hash=digest(hypothesis.model_dump(mode="json", by_alias=True)),
        revision_kind="SOURCE_CORRECTION",
        recorded_at=datetime(2026, 8, 6, tzinfo=UTC),
        reason="Later exchange correction",
        changes={"correctedClose": 900.0},
        evidence_hashes=(correction.content_hash,),
    )
    payload = revision.model_dump(mode="json", by_alias=True)
    assert persist_revisions(dataset["runId"], [payload]) == 1
    assert persist_revisions(dataset["runId"], [payload]) == 0
    second = revision.model_copy(
        update={
            "revision_id": "revision-2",
            "predecessor_type": "REVISION",
            "predecessor_id": "revision-1",
            "predecessor_hash": digest(payload),
            "revision_kind": "INTERPRETATION",
            "changes": {"note": "Later interpretation"},
            "recorded_at": datetime(2026, 8, 7, tzinfo=UTC),
        }
    )
    persist_revisions(dataset["runId"], [second.model_dump(mode="json", by_alias=True)])
    assert len(list_revisions(hypothesis.hypothesis_id)) == 2
    assert list_hypotheses(dataset["runId"]) == before
    refs = env.authority.active_references(as_of_date=date(2026, 9, 9))
    assert any(
        ref.reference_type == RetentionReferenceType.REVISION
        and ref.content_hash == correction.content_hash
        for ref in refs
    )
    bad = second.model_copy(update={"changes": {"note": "rewritten"}})
    with pytest.raises(ValueError, match="immutable"):
        persist_revisions(
            dataset["runId"], [bad.model_dump(mode="json", by_alias=True)]
        )


def test_artifact_and_outbox_rollback_together(env, monkeypatch):
    from trendforge_api.selection.r16_store import persist_hypotheses

    dataset, hypotheses = freeze(env)
    original = RetentionPublicationStore.stage

    def crash(self, request, *, connection):
        original(self, request, connection=connection)
        raise RuntimeError("injected crash before commit")

    monkeypatch.setattr(RetentionPublicationStore, "stage", crash)
    with pytest.raises(RuntimeError, match="injected crash"):
        persist_hypotheses(
            dataset["runId"], [hypotheses[0].model_dump(mode="json", by_alias=True)]
        )
    with storage.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM pit_hypotheses").fetchone()[0] == 0
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM historical_retention_outbox WHERE artifact_type LIKE 'R16_%'"
            ).fetchone()[0]
            == 0
        )


def test_crash_after_commit_is_hidden_and_retry_recovers(env, monkeypatch):
    from trendforge_api.selection.r16_store import list_hypotheses, persist_hypotheses

    dataset, hypotheses = freeze(env)
    payload = hypotheses[0].model_dump(mode="json", by_alias=True)
    original = RetentionPublicationStore.finalize
    monkeypatch.setattr(
        RetentionPublicationStore,
        "finalize",
        lambda *args: (_ for _ in ()).throw(RuntimeError("crash after commit")),
    )
    with pytest.raises(RuntimeError, match="crash after commit"):
        persist_hypotheses(dataset["runId"], [payload])
    assert list_hypotheses(dataset["runId"]) == []
    with storage.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM pit_hypotheses").fetchone()[0] == 1
    monkeypatch.setattr(RetentionPublicationStore, "finalize", original)
    assert persist_hypotheses(dataset["runId"], [payload]) == 0
    assert len(list_hypotheses(dataset["runId"])) == 1


def test_old_decision_outcome_and_revision_survive_real_cleanup(env):
    from trendforge_api.selection.r16_pit import R16RevisionV1
    from trendforge_api.selection.r16_store import (
        list_hypotheses,
        list_observations,
        list_revisions,
        persist_observations,
        persist_revisions,
    )

    dataset, hypothesis = save_hypothesis(env)
    result = observation(env, hypothesis)
    persist_observations(
        dataset["runId"], [result.model_dump(mode="json", by_alias=True)]
    )
    correction = env.market.install_object(
        b"cleanup-test correction", extension="txt", media_type="text/plain"
    )
    revision = R16RevisionV1(
        revision_id="cleanup-revision",
        hypothesis_id=hypothesis.hypothesis_id,
        predecessor_type="OUTCOME",
        predecessor_id=result.observation_id,
        predecessor_hash=digest(result.model_dump(mode="json", by_alias=True)),
        revision_kind="SOURCE_CORRECTION",
        recorded_at=datetime(2026, 8, 6, tzinfo=UTC),
        reason="Later correction must survive cleanup",
        evidence_hashes=(correction.content_hash,),
    )
    persist_revisions(
        dataset["runId"], [revision.model_dump(mode="json", by_alias=True)]
    )
    old_day = date(2026, 7, 22)
    entries = tuple(
        ManifestEntry(
            source_key=f"source_{i}",
            status=ManifestStatus.SUCCESS_NEW,
            content_hash=obj.content_hash,
            object_path=str(obj.path),
            normalized_row_count=1,
            retry_count=0,
        )
        for i, obj in enumerate(env.objects)
    )
    env.market.write_manifest(
        SnapshotManifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            run_id="old-manifest",
            registry_sha256="7" * 64,
            trading_date=old_day,
            slot="1500",
            generated_at=datetime(2026, 7, 22, 16, tzinfo=UTC),
            entries=entries,
        )
    )
    install_bar(env, date(2026, 9, 8), high=600, low=500, close=550)
    cleanup = env.market.cleanup_retention(
        as_of_date=date(2026, 9, 9),
        completed_trading_days=[old_day],
        detailed_trading_days=0,
        dry_run=False,
    )
    assert old_day in cleanup.retained_trading_dates
    assert all(obj.path.is_file() for obj in env.objects)
    assert len(list_hypotheses(dataset["runId"])) == 3
    assert len(list_observations(dataset["runId"])) == len(list_revisions()) == 1
    assert correction.path.is_file()


def test_sql_cannot_update_or_delete_frozen_hypothesis(env):
    save_hypothesis(env)
    with storage.connect() as conn:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE pit_hypotheses SET public_state='CONFIRMED'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("DELETE FROM pit_hypotheses")


def test_worker_uses_exact_parent_then_appends_linked_outcome_revisions(env):
    from trendforge_api.selection.r16_service import run_incremental
    from trendforge_api.selection.r16_store import (
        list_hypotheses,
        list_observations,
        list_revisions,
    )

    # This valid but unbound historical bar must never enter decision features.
    install_bar(env, date(2026, 7, 25), high=999, low=900, close=950)
    install_bar(env, date(2026, 8, 4), high=109.5, low=108.5, close=109)
    first = run_incremental(owner_id="retention-worker-1")
    assert first["replay"]["observationsAppended"] == 3
    before = list_hypotheses()
    assert all(row["geometryStatus"] == "READY" for row in before)
    install_bar(env, date(2026, 8, 5), high=110.5, low=109, close=110.2)
    second = run_incremental(owner_id="retention-worker-2")
    assert second["replay"]["observationsAppended"] == 3
    assert len(list_revisions()) == 3
    observations = list_observations()
    successors = [row for row in observations if row.get("predecessorObservationId")]
    assert len(successors) == 3
    assert len({row["observationId"] for row in observations}) == 6
    assert list_hypotheses() == before
    repeated = run_incremental(owner_id="retention-worker-3")
    assert repeated["replay"]["observationsAppended"] == 0
    assert len(list_revisions()) == 3


def test_original_outcome_remains_replayable_after_successor(env):
    from trendforge_api.selection.r16_store import persist_observations

    dataset, hypothesis = save_hypothesis(env)
    first = observation(env, hypothesis)
    payload = first.model_dump(mode="json", by_alias=True)
    persist_observations(dataset["runId"], [payload])
    successor = observation(env, hypothesis, date(2026, 8, 5)).model_copy(
        update={
            "predecessor_observation_id": first.observation_id,
            "predecessor_observation_hash": digest(payload),
        }
    )
    persist_observations(
        dataset["runId"], [successor.model_dump(mode="json", by_alias=True)]
    )
    assert persist_observations(dataset["runId"], [payload]) == 0


def test_read_detects_parent_corruption_without_creating_retention(env):
    from trendforge_api.selection.r16_store import list_hypotheses

    save_hypothesis(env)
    with storage.connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM historical_retention_outbox"
        ).fetchone()[0]
        conn.execute(
            "UPDATE historical_retention_publications SET lineage_hash='tampered' "
            "WHERE artifact_type='S8_DECISION_VERSION'"
        )
    with pytest.raises(RuntimeError, match="WAIT_RHIST03"):
        list_hypotheses()
    with storage.connect() as conn:
        assert (
            conn.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[
                0
            ]
            == count
        )


def test_forged_normalized_input_with_real_hash_is_rejected(env):
    from trendforge_api.r16_retention import freeze_s8_hypotheses
    from trendforge_api.selection.r16_pit import build_frozen_hypotheses
    from trendforge_api.selection.r16_store import persist_hypotheses

    dataset, original = freeze(env)
    inputs = copy.deepcopy(list(original[0].decision_inputs))
    for row in inputs:
        for key in ("open", "high", "low", "close"):
            row[key] += 1000
    fake = build_frozen_hypotheses(
        s8_payload=env.s8,
        bars_by_symbol={"AAA": inputs},
        dataset_revision_hash=original[0].dataset_revision_hash,
    )[0]
    fake = fake.model_copy(
        update={
            "source_s8_publication_id": original[0].source_s8_publication_id,
            "source_s8_version": original[0].source_s8_version,
            "source_s8_publication_lineage_hash": original[
                0
            ].source_s8_publication_lineage_hash,
            "decision_inputs": tuple(inputs),
        }
    )
    with pytest.raises(RuntimeError, match="WAIT_RHIST03"):
        persist_hypotheses(
            dataset["runId"], [fake.model_dump(mode="json", by_alias=True)]
        )
    assert (
        freeze_s8_hypotheses(s8_payload=env.s8, dataset_revision_hash="r16-original")
        == original
    )


def test_ambiguous_stop_is_not_counted_as_certain_loss(env):
    from trendforge_api.selection.r16_metrics import build_metrics
    from trendforge_api.selection.r16_pit import label_hypothesis

    dataset, hypothesis = save_hypothesis(env)
    row = label_hypothesis(
        hypothesis,
        bars=[
            {
                "trade_date": "2026-08-04",
                "artifact_hash": "a" * 64,
                "open": 110,
                "high": 120,
                "low": 100,
                "close": 111,
            }
        ],
    )
    assert row.intrabar_ambiguous
    metrics, _ = build_metrics(
        dataset_run_id=dataset["runId"],
        hypotheses=[hypothesis],
        observations=[row],
        expected_s8_dates=1,
        available_s8_dates=1,
        calendar_verified=True,
    )
    assert metrics[0]["ambiguousCount"] == 1
    assert metrics[0]["resolvedCount"] == metrics[0]["stopCount"] == 0
    assert metrics[0]["countsReconcile"]
    assert metrics[0]["profileConclusion"] == "INCONCLUSIVE"


def test_real_s8_producer_seals_the_full_persisted_payload(env):
    from trendforge_api.r16_retention import freeze_s8_hypotheses
    from trendforge_api.s8_retention import persist_protected_s8
    from trendforge_api.selection.s8_persist_run import S8ScanBlobV1

    material = copy.deepcopy(env.s8)
    material["runId"] = "s8-real-producer"
    material["builtAt"] = material["asOf"]
    blob = S8ScanBlobV1.model_validate(material)
    stored = persist_protected_s8(
        blob=blob,
        prior_payload=None,
        evidence_roots=env.roots,
        publication_lineage={"r1BundleId": "exact-original"},
        trading_date=date(2026, 8, 3),
        market_db_path=storage.DB_PATH,
    )
    payload = stored.model_dump(mode="json", by_alias=True)
    frozen = freeze_s8_hypotheses(
        s8_payload=payload, dataset_revision_hash="real-producer"
    )
    assert frozen[0].source_s8_hash == digest(payload)
    assert frozen[0].geometry_status == "READY"
    assert (
        persist_protected_s8(
            blob=blob,
            prior_payload=None,
            evidence_roots=env.roots,
            publication_lineage={"r1BundleId": "exact-original"},
            trading_date=date(2026, 8, 3),
            market_db_path=storage.DB_PATH,
        )
        == stored
    )


def test_legacy_parent_without_payload_seal_is_not_silently_backfilled(env):
    from trendforge_api.r16_retention import freeze_s8_hypotheses

    # Simulate a valid older publication, whose lineage did not seal its payload.
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT lineage_json FROM historical_retention_publications WHERE publication_id=?",
            (env.request.publication_id,),
        ).fetchone()
        lineage = json.loads(row[0])["lineage"]
        lineage.pop("s8PayloadHash")
        legacy = RetentionPublicationRequest(
            artifact_type=env.request.artifact_type,
            artifact_id=env.request.artifact_id,
            artifact_version=env.request.artifact_version,
            reference_type=env.request.reference_type,
            evidence_roots=env.roots,
            lineage=lineage,
            created_at=env.request.created_at,
        )
        conn.execute(
            "UPDATE historical_retention_publications SET lineage_json=?, lineage_hash=? WHERE publication_id=?",
            (legacy.lineage_json, legacy.lineage_hash, legacy.publication_id),
        )
        before = conn.execute(
            "SELECT COUNT(*) FROM historical_retention_outbox"
        ).fetchone()[0]
    with pytest.raises(RuntimeError, match="WAIT_RHIST03_S8_PARENT_SEAL_MISMATCH"):
        freeze_s8_hypotheses(s8_payload=env.s8, dataset_revision_hash="legacy")
    with storage.connect() as conn:
        assert (
            conn.execute("SELECT COUNT(*) FROM historical_retention_outbox").fetchone()[
                0
            ]
            == before
        )


@pytest.mark.parametrize(
    "status",
    [
        "NO_ENTRY",
        "EXPIRED",
        "AMBIGUOUS",
        "CENSORED",
        "DATA_GAP",
        "NO_GEOMETRY",
        "INVALIDATED_BEFORE_ENTRY",
    ],
)
def test_nonbinary_outcome_population_is_retained_explicitly(env, status):
    from trendforge_api.selection.r16_pit import label_hypothesis
    from trendforge_api.selection.r16_store import (
        list_observations,
        persist_observations,
    )

    dataset, hypothesis = save_hypothesis(env)
    # Explicit external status records still need an exact parent and path,
    # even when no later price path exists (expiry/data-gap/censoring).
    outcome = label_hypothesis(hypothesis, bars=[]).model_copy(
        update={
            "status": status,
            "observation_id": "explicit-" + status,
            "censor_reason": "Explicit no-path diagnostic",
        }
    )
    persist_observations(
        dataset["runId"], [outcome.model_dump(mode="json", by_alias=True)]
    )
    assert list_observations(dataset["runId"])[0]["status"] == status


@pytest.mark.parametrize(
    "field,value",
    [
        ("predecessor_id", "absent"),
        ("predecessor_hash", "f" * 64),
        ("hypothesis_id", "other-hypothesis"),
        ("recorded_at", datetime(2026, 1, 1, tzinfo=UTC)),
    ],
)
def test_revision_cannot_repoint_or_precede_its_parent(env, field, value):
    from trendforge_api.selection.r16_pit import R16RevisionV1
    from trendforge_api.selection.r16_store import list_revisions, persist_revisions

    dataset, hypothesis = save_hypothesis(env)
    revision = R16RevisionV1(
        revision_id="bad-revision",
        hypothesis_id=hypothesis.hypothesis_id,
        predecessor_type="DECISION_VERSION",
        predecessor_id=hypothesis.hypothesis_id,
        predecessor_hash=digest(hypothesis.model_dump(mode="json", by_alias=True)),
        revision_kind="INTERPRETATION",
        recorded_at=datetime(2026, 8, 6, tzinfo=UTC),
        reason="Adversarial revision",
    ).model_copy(update={field: value})
    with pytest.raises(
        (RuntimeError, sqlite3.IntegrityError), match="WAIT_RHIST03|FOREIGN KEY"
    ):
        persist_revisions(
            dataset["runId"], [revision.model_dump(mode="json", by_alias=True)]
        )
    assert list_revisions() == []


def test_authority_failure_leaves_outcome_hidden_without_changing_decision(
    env, monkeypatch
):
    from trendforge_api.selection.r16_store import (
        list_hypotheses,
        list_observations,
        persist_observations,
    )

    dataset, hypothesis = save_hypothesis(env)
    before = list_hypotheses()
    outcome = observation(env, hypothesis)
    monkeypatch.setattr(
        HistoricalRetentionAuthority,
        "register",
        lambda *args: (_ for _ in ()).throw(RuntimeError("authority unavailable")),
    )
    with pytest.raises(RuntimeError, match="WAIT_RHIST03"):
        persist_observations(
            dataset["runId"], [outcome.model_dump(mode="json", by_alias=True)]
        )
    assert list_observations() == []
    assert list_hypotheses() == before
    with storage.connect() as conn:
        assert (
            conn.execute(
                "SELECT status FROM historical_retention_publications WHERE artifact_type='R16_OUTCOME'"
            ).fetchone()[0]
            == "FAILED_BLOCKING"
        )


def test_crash_after_authority_registration_replays_same_outcome_reference(
    env, monkeypatch
):
    from trendforge_api.selection.r16_store import (
        list_observations,
        persist_observations,
    )

    dataset, hypothesis = save_hypothesis(env)
    outcome = observation(env, hypothesis).model_dump(mode="json", by_alias=True)
    original = HistoricalRetentionAuthority.register
    crashed = False

    def stop_after_register(self, reference):
        nonlocal crashed
        result = original(self, reference)
        if not crashed:
            crashed = True
            raise KeyboardInterrupt("simulated process death")
        return result

    monkeypatch.setattr(HistoricalRetentionAuthority, "register", stop_after_register)
    with pytest.raises(KeyboardInterrupt, match="simulated process death"):
        persist_observations(dataset["runId"], [outcome])
    assert list_observations() == []
    monkeypatch.setattr(HistoricalRetentionAuthority, "register", original)
    assert persist_observations(dataset["runId"], [outcome]) == 0
    assert len(list_observations()) == 1


def test_rebuild_creates_linked_immutable_decision_versions(env):
    from trendforge_api.selection.r16_service import run_incremental
    from trendforge_api.selection.r16_store import list_hypotheses, list_revisions

    run_incremental(owner_id="original-build")
    originals = list_hypotheses()
    result = run_incremental(
        mode="rebuild",
        rebuild_reason="Explicit later interpretation",
        owner_id="rebuild-owner",
    )
    assert result["replay"]["revisionsAppended"] == 3
    all_rows = {row["hypothesisId"]: row for row in list_hypotheses()}
    assert len(all_rows) == 6
    assert all(all_rows[row["hypothesisId"]] == row for row in originals)
    assert all(row["replacementHypothesisId"] in all_rows for row in list_revisions())
    run_incremental(
        mode="rebuild",
        rebuild_reason="Explicit later interpretation",
        owner_id="rebuild-replay",
    )
    assert len(list_revisions()) == 3


def test_worker_recovers_outcome_revision_gap_after_crash(env, monkeypatch):
    from trendforge_api.selection import r16_service
    from trendforge_api.selection.r16_store import (
        list_hypotheses,
        list_observations,
        list_revisions,
    )

    install_bar(env, date(2026, 8, 4), high=109.5, low=108.5, close=109)
    r16_service.run_incremental(owner_id="first-worker")
    originals = list_hypotheses()
    install_bar(env, date(2026, 8, 5), high=110.5, low=109, close=110.2)
    original = r16_service.persist_revisions
    monkeypatch.setattr(
        r16_service,
        "persist_revisions",
        lambda *args: (_ for _ in ()).throw(RuntimeError("crash at revision boundary")),
    )
    with pytest.raises(RuntimeError, match="crash at revision boundary"):
        r16_service.run_incremental(owner_id="crashed-worker")
    assert len(list_observations()) == 6 and list_revisions() == []
    monkeypatch.setattr(r16_service, "persist_revisions", original)
    r16_service.run_incremental(owner_id="recovery-worker")
    assert len(list_observations()) == 6 and len(list_revisions()) == 3
    assert list_hypotheses() == originals


def test_revision_read_rejects_tampered_predecessor_publication(env):
    from trendforge_api.selection.r16_pit import R16RevisionV1
    from trendforge_api.selection.r16_store import (
        list_revisions,
        persist_observations,
        persist_revisions,
    )

    dataset, hypothesis = save_hypothesis(env)
    outcome = observation(env, hypothesis)
    persist_observations(
        dataset["runId"], [outcome.model_dump(mode="json", by_alias=True)]
    )
    revision = R16RevisionV1(
        revision_id="read-proof-revision",
        hypothesis_id=hypothesis.hypothesis_id,
        predecessor_type="OUTCOME",
        predecessor_id=outcome.observation_id,
        predecessor_hash=digest(outcome.model_dump(mode="json", by_alias=True)),
        revision_kind="INTERPRETATION",
        recorded_at=datetime(2026, 8, 6, tzinfo=UTC),
        reason="Review of exact outcome",
    )
    persist_revisions(
        dataset["runId"], [revision.model_dump(mode="json", by_alias=True)]
    )
    with storage.connect() as conn:
        conn.execute(
            "UPDATE historical_retention_publications SET lineage_hash='tampered' WHERE artifact_type='R16_OUTCOME'"
        )
    with pytest.raises(RuntimeError, match="WAIT_RHIST03"):
        list_revisions()
