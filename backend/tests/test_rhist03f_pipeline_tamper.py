"""R-HIST-03F M3 — pipeline-graph tamper probes (R16 parents, market bytes).

Each scenario builds the real 22-day S8+R16 graph via the accepted 03E builder,
records the declared coverage finding map, injects exactly one controlled
fault, and requires the independent coverage oracle to fail closed for the
affected artifact — while nothing else heals. R16 rows carry SQL immutability
triggers: naive writes must abort at the trigger layer; past dropped triggers,
the sealed verifiers must refuse.

Baseline note: the full-registry baseline verdict here is FAIL because this
builder persists no R18 tables (out-of-scope REGISTRY_ERROR blockers) and the
same-store inverse sees cross-producer references. Detection is therefore
proven by per-artifact COVERED → typed-fail-closed transitions plus covered
count movement — never by the top-level verdict alone.

Dual oracles throughout — Oracle A is direct persisted-state evidence
(SQL rows, hashes, parents, files, bytes); Oracle B is the declared
``audit_coverage()``. A test that only repeats the oracle's verdict without
independent state proof is not accepted.

F_TAMPER_03 (market object deletion), F_TAMPER_04 (market bytes corruption),
F_TAMPER_35 (R16 decision-parent tamper, two layers), F_TAMPER_36 (R16 outcome
repointed to a valid-but-wrong decision). Scratch DBs only. Synthetic bytes
only.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from trendforge_api import storage
from trendforge_api.retention_coverage import audit_coverage

from tests.test_rhist03e_source_to_end import _run_eligible_pipeline

S8_PRODUCER = "S8_DECISION_VERSION"
R16_DECISION_PRODUCER = "R16_DECISION_VERSION"
R16_OUTCOME_PRODUCER = "R16_OUTCOME"

# Any typed fail-closed status is accepted for a corrupted artifact; COVERED
# for that artifact is impossible. The sets below document the currently
# observed mapping, not an exhaustive contract.
T35_ACCEPT = {"LINEAGE_BROKEN", "LINEAGE_MISSING", "INCONSISTENT_IDENTITY", "MISSING_RETENTION"}
T03_ACCEPT = {"LINEAGE_BROKEN", "LINEAGE_MISSING", "MISSING_RETENTION"}
T04_ACCEPT = {"LINEAGE_BROKEN", "INCONSISTENT_IDENTITY"}


def _db() -> Path:
    return Path(str(storage.DB_PATH))


def _full(db_path: Path) -> dict[str, Any]:
    """Oracle B: the declared full-registry audit (fail-closed typing)."""
    report: dict[str, Any] = audit_coverage(db_path=db_path)
    assert isinstance(report, dict), (
        "03E audit_coverage contract violation: "
        f"expected dict, got {type(report).__name__}"
    )
    return report


def _status_map(report: dict[str, Any]) -> dict[tuple[str, str], str]:
    return {
        (str(finding["producerId"]), str(finding["artifactId"])): str(finding["status"])
        for finding in report["findings"]
    }


def _covered_keys(statuses: dict[tuple[str, str], str]) -> set[tuple[str, str]]:
    return {key for key, status in statuses.items() if status == "COVERED"}


def _s8_root_hashes(db_path: Path) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT lineage_json FROM historical_retention_publications "
            "WHERE artifact_type='S8_DECISION_VERSION'"
        ).fetchone()
    assert row is not None
    return [
        str(root["contentHash"])
        for root in json.loads(row["lineage_json"])["evidenceRoots"]
        if root.get("contentHash")
    ]


def _drop_r16_trigger(db_path: Path, table: str, operation: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"DROP TRIGGER IF EXISTS immutable_{table}_{operation}")
        conn.commit()


def test_F_TAMPER_35_r16_decision_parent_tamper_fails_closed(tmp_path, monkeypatch) -> None:
    """F_TAMPER_35 — corrupt the sealed S8-parent pointer of one R16 decision.

    Layer A (prevention): the SQL immutability trigger rejects even a no-op
    rewrite. Layer B (detection past a defensive bypass): with the row trigger
    dropped in the scratch DB only, rewriting ``sourceS8Hash`` to a bogus
    value must move exactly the victim decision (and at most its dependents)
    out of COVERED, and the direct state oracle must prove the stored parent
    — and only the parent field — was corrupted.
    """
    _run_eligible_pipeline(tmp_path, monkeypatch, "03f-t35")
    db_path = _db()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT hypothesis_id, content_hash, payload_json FROM pit_hypotheses "
            "ORDER BY hypothesis_id LIMIT 1"
        ).fetchone()
    assert row is not None
    victim = (R16_DECISION_PRODUCER, str(row["hypothesis_id"]))
    payload = json.loads(str(row["payload_json"]))
    original_parent = str(payload["sourceS8Hash"])
    bogus_parent = ("0" if not original_parent.startswith("0") else "f") * 64
    assert bogus_parent != original_parent

    # Healthy baseline: the victim decision is COVERED.
    base = _full(db_path)
    base_statuses = _status_map(base)
    assert base_statuses[victim] == "COVERED"
    base_covered = _covered_keys(base_statuses)
    with sqlite3.connect(db_path) as conn:
        link_before = conn.execute(
            "SELECT payload_hash FROM pit_retention_links "
            "WHERE record_type='DECISION_VERSION' AND record_id=?",
            (victim[1],),
        ).fetchone()[0]

    # Layer A: the R16 immutability trigger blocks even the naive no-op write.
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE pit_hypotheses SET payload_json=? WHERE hypothesis_id=?",
                (row["payload_json"], victim[1]),
            )
            conn.commit()

    # Layer B: past the dropped row trigger, corrupt only the parent pointer.
    _drop_r16_trigger(db_path, "pit_hypotheses", "update")
    forged = dict(payload)
    forged["sourceS8Hash"] = bogus_parent
    forged_json = json.dumps(forged, sort_keys=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE pit_hypotheses SET payload_json=? WHERE hypothesis_id=?",
            (forged_json, victim[1]),
        )
        conn.commit()

    # Oracle A (direct): the stored parent is corrupted; seals disagree.
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        stored = conn.execute(
            "SELECT content_hash, payload_json FROM pit_hypotheses WHERE hypothesis_id=?",
            (victim[1],),
        ).fetchone()
    assert stored is not None
    stored_payload = json.loads(str(stored["payload_json"]))
    assert stored_payload["sourceS8Hash"] == bogus_parent
    assert stored_payload["sourceS8RunId"] == payload["sourceS8RunId"]
    assert hashlib.sha256(str(stored["payload_json"]).encode()).hexdigest() != stored["content_hash"]
    with sqlite3.connect(db_path) as conn:
        link_after = conn.execute(
            "SELECT payload_hash FROM pit_retention_links "
            "WHERE record_type='DECISION_VERSION' AND record_id=?",
            (victim[1],),
        ).fetchone()[0]
    assert link_after == link_before, "link seal must still bind the original payload"

    # Oracle B: the victim decision loses coverage with a typed fail-closed
    # status, and nothing else gains coverage.
    after = _full(db_path)
    after_statuses = _status_map(after)
    assert after_statuses[victim] in T35_ACCEPT
    assert after_statuses[victim] != "COVERED"
    after_covered = _covered_keys(after_statuses)
    assert after_covered < base_covered
    assert after_covered <= base_covered - {victim}
    assert after["coveredCount"] < base["coveredCount"]


def test_F_TAMPER_36_r16_outcome_valid_wrong_parent_fails_closed(tmp_path, monkeypatch) -> None:
    """F_TAMPER_36 — repoint outcome O1 (of D1) at D2, a valid-but-wrong parent.

    D1 and D2 are each independently valid, retained, hash-correct and
    published. After the repoint, O1 must NOT verify: TrendForge validates the
    *correct* historical parent, not merely that *some* valid parent exists
    (which is what future win-rate/model statistics will be built on).
    The wrong parent D2 itself must stay COVERED throughout.
    """
    from trendforge_api.r16_retention import verified_record

    _run_eligible_pipeline(tmp_path, monkeypatch, "03f-t36")
    db_path = _db()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT observation_id, hypothesis_id, payload_json FROM pit_observations "
            "ORDER BY observation_id LIMIT 2"
        ).fetchall()
    assert len(rows) == 2
    o1_key = (R16_OUTCOME_PRODUCER, str(rows[0]["observation_id"]))
    o2_key = (R16_OUTCOME_PRODUCER, str(rows[1]["observation_id"]))
    d1, d2 = str(rows[0]["hypothesis_id"]), str(rows[1]["hypothesis_id"])
    assert d1 != d2
    assert json.loads(str(rows[0]["payload_json"]))["hypothesisId"] == d1

    # Direct oracle, pre-fault: both decisions verify on their own, and O1's
    # publication binds D1's publication (not D2's).
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for did in (d1, d2):
            _row, _payload, _request = verified_record(conn, "DECISION_VERSION", did)
            assert _payload["hypothesisId"] == did
        d1_pub = conn.execute(
            "SELECT publication_id FROM pit_retention_links "
            "WHERE record_type='DECISION_VERSION' AND record_id=?",
            (d1,),
        ).fetchone()[0]
        d2_link = conn.execute(
            "SELECT payload_hash, publication_id FROM pit_retention_links "
            "WHERE record_type='DECISION_VERSION' AND record_id=?",
            (d2,),
        ).fetchone()
        o1_pub = conn.execute(
            "SELECT publication_id FROM pit_retention_links "
            "WHERE record_type='OUTCOME' AND record_id=?",
            (o1_key[1],),
        ).fetchone()[0]
        lineage = json.loads(
            conn.execute(
                "SELECT lineage_json FROM historical_retention_publications "
                "WHERE publication_id=?",
                (o1_pub,),
            ).fetchone()[0]
        )["lineage"]
    assert str(d2_link["publication_id"]) != str(d1_pub)
    assert str(lineage.get("parentPublicationId")) == str(d1_pub)

    # Healthy baseline: O1 is COVERED.
    base = _full(db_path)
    base_statuses = _status_map(base)
    assert base_statuses[o1_key] == "COVERED"
    assert base_statuses[o2_key] == "COVERED"
    base_covered = _covered_keys(base_statuses)

    # Layer A: the R16 immutability trigger blocks the naive join swap.
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE pit_observations SET hypothesis_id=? WHERE observation_id=?",
                (d2, o1_key[1]),
            )
            conn.commit()

    # Layer B: past the dropped row trigger, repoint the SEALED parent
    # (join column + payload hypothesisId + payload parent hash) at D2.
    # Row content_hash and the link/publication seals are deliberately left
    # stale: a complete forgery would have to reforge that whole chain, and
    # every stale seal must fail closed.
    _drop_r16_trigger(db_path, "pit_observations", "update")
    forged = json.loads(str(rows[0]["payload_json"]))
    forged["hypothesisId"] = d2
    forged["sourceHypothesisHash"] = str(d2_link["payload_hash"])
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE pit_observations SET hypothesis_id=?, payload_json=? "
            "WHERE observation_id=?",
            (d2, json.dumps(forged, sort_keys=True), o1_key[1]),
        )
        conn.commit()

    # The link seal is still armed and still binds the original payload.
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE pit_retention_links SET payload_hash=? "
                "WHERE record_type='OUTCOME' AND record_id=?",
                ("0" * 64, o1_key[1]),
            )
            conn.commit()

    # Oracle A (direct): O1 now names D2 everywhere mutable, while its
    # publication still binds D1 — a valid-but-wrong parent.
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        current = conn.execute(
            "SELECT hypothesis_id, payload_json, content_hash FROM pit_observations "
            "WHERE observation_id=?",
            (o1_key[1],),
        ).fetchone()
    assert current is not None
    current_payload = json.loads(str(current["payload_json"]))
    assert str(current["hypothesis_id"]) == d2
    assert str(current_payload["hypothesisId"]) == d2
    assert str(current_payload["sourceHypothesisHash"]) == str(d2_link["payload_hash"])
    assert (
        hashlib.sha256(str(current["payload_json"]).encode()).hexdigest()
        != current["content_hash"]
    )

    # Oracle B: O1 — and only O1 — loses coverage; D2's own outcome and every
    # decision stay COVERED, proving the binding (not D2) is what failed.
    after = _full(db_path)
    after_statuses = _status_map(after)
    assert after_statuses[o1_key] in T35_ACCEPT
    assert after_statuses[o1_key] != "COVERED"
    assert after_statuses[o2_key] == "COVERED"
    changed = {
        key
        for key in base_statuses.keys() | after_statuses.keys()
        if base_statuses.get(key) != after_statuses.get(key)
    }
    assert changed == {o1_key}, f"only O1 may change status: {changed}"
    after_covered = _covered_keys(after_statuses)
    assert after_covered == base_covered - {o1_key}
    assert after["coveredCount"] == base["coveredCount"] - 1


def test_F_TAMPER_03_market_object_delete_fails_closed(tmp_path, monkeypatch) -> None:
    """F_TAMPER_03 — deleting the original market object breaks the S8 seal."""
    s8_run_id = _run_eligible_pipeline(tmp_path, monkeypatch, "03f-t03")
    db_path = _db()
    s8_key = (S8_PRODUCER, s8_run_id)

    victim = _s8_root_hashes(db_path)[0]
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        lineage = json.loads(
            conn.execute(
                "SELECT lineage_json FROM historical_retention_publications "
                "WHERE artifact_type='S8_DECISION_VERSION'"
            ).fetchone()["lineage_json"]
        )
        assert victim in {
            str(root.get("contentHash")) for root in lineage["evidenceRoots"]
        }, "lineage must still name the victim (the binding under test)"
        assert (
            conn.execute(
                "SELECT 1 FROM market_data_objects WHERE content_hash=?",
                (victim,),
            ).fetchone()[0]
            == 1
        )

    # Healthy baseline: the S8 decision is COVERED.
    base = _full(db_path)
    base_statuses = _status_map(base)
    assert base_statuses[s8_key] == "COVERED"
    base_covered = _covered_keys(base_statuses)

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM market_data_objects WHERE content_hash=?", (victim,))
        conn.commit()

    # Oracle A (direct): the row is gone while the lineage still demands it.
    with sqlite3.connect(db_path) as conn:
        assert (
            conn.execute(
                "SELECT 1 FROM market_data_objects WHERE content_hash=?",
                (victim,),
            ).fetchone()
            is None
        )

    # Oracle B: the S8 decision can no longer be COVERED, and nothing heals.
    after = _full(db_path)
    after_statuses = _status_map(after)
    assert after_statuses[s8_key] in T03_ACCEPT
    assert after_statuses[s8_key] != "COVERED"
    after_covered = _covered_keys(after_statuses)
    assert after_covered < base_covered
    assert after_covered <= base_covered - {s8_key}
    assert after["coveredCount"] < base["coveredCount"]


def test_F_TAMPER_04_market_bytes_corrupt_fails_closed(tmp_path, monkeypatch) -> None:
    """F_TAMPER_04 — corrupting retained bytes (identity kept) breaks the seal.

    Stronger than absence: the object row still exists under the same
    identity, but the bytes no longer match it.
    """
    s8_run_id = _run_eligible_pipeline(tmp_path, monkeypatch, "03f-t04")
    db_path = _db()
    s8_key = (S8_PRODUCER, s8_run_id)

    victim = _s8_root_hashes(db_path)[0]
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT object_path, size_bytes FROM market_data_objects WHERE content_hash=?",
            (victim,),
        ).fetchone()
    assert row is not None
    target = Path(str(row["object_path"]))
    if not target.is_absolute():
        target = tmp_path / "market-data" / target
    assert target.is_file(), f"evidence file missing: {target}"
    with open(target, "rb") as handle:
        before_bytes = handle.read()
    assert hashlib.sha256(before_bytes).hexdigest() == victim
    assert len(before_bytes) == int(row["size_bytes"])

    # Healthy baseline: the S8 decision is COVERED with intact bytes.
    base = _full(db_path)
    base_statuses = _status_map(base)
    assert base_statuses[s8_key] == "COVERED"
    base_covered = _covered_keys(base_statuses)

    with open(target, "ab") as handle:
        handle.write(b"\x00corrupt")

    # Oracle A (direct): same identity, different bytes.
    with open(target, "rb") as handle:
        after_bytes = handle.read()
    assert hashlib.sha256(after_bytes).hexdigest() != victim
    assert len(after_bytes) != int(row["size_bytes"])
    with sqlite3.connect(db_path) as conn:
        assert (
            conn.execute(
                "SELECT 1 FROM market_data_objects WHERE content_hash=?",
                (victim,),
            ).fetchone()[0]
            == 1
        ), "identity row must survive; only the bytes are corrupt"

    # Oracle B: the S8 decision can no longer be COVERED, and nothing heals.
    after = _full(db_path)
    after_statuses = _status_map(after)
    assert after_statuses[s8_key] in T04_ACCEPT
    assert after_statuses[s8_key] != "COVERED"
    after_covered = _covered_keys(after_statuses)
    assert after_covered < base_covered
    assert after_covered <= base_covered - {s8_key}
    assert after["coveredCount"] < base["coveredCount"]
