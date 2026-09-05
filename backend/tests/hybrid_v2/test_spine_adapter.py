"""C3: lineage. Missing R2 fails closed; any hash mismatch is 503, never last-good."""

from __future__ import annotations

import hashlib

import pytest

from trendforge_api import storage
from trendforge_api.hybrid_v2.pipeline import build_hybrid_v2_overlay
from trendforge_api.hybrid_v2.spine_adapter import load_hybrid_spine
from trendforge_api.hybrid_v2.tests_support.fixtures import persist_overlay_lineage
from trendforge_api.selection.attention_order import persist_attention_order


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def test_missing_r1_or_r2_fails_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "empty.db")
    storage._INITIALIZED_DB_PATHS.clear()
    with pytest.raises(ValueError, match="WAIT_HYBRID_R2_NOT_READY"):
        load_hybrid_spine()


def test_r1_r2_hash_mismatch_is_lineage_mismatch(tmp_path, monkeypatch) -> None:
    parts = persist_overlay_lineage(tmp_path, monkeypatch)
    tampered = parts["attention"].model_copy(
        update={
            "run_id": "r2-run-hvb-tampered",
            "run_hash": _hash("tampered-r2"),
        }
    )
    persist_attention_order(tampered)
    with pytest.raises(ValueError, match="WAIT_HYBRID_LINEAGE_MISMATCH"):
        load_hybrid_spine()
    with pytest.raises(ValueError, match="WAIT_HYBRID_LINEAGE_MISMATCH"):
        build_hybrid_v2_overlay(limit=5)


def test_r14_mismatch_is_lineage_mismatch(tmp_path, monkeypatch) -> None:
    from trendforge_api.selection.r14_live import R14CaJoinBatchV1

    parts = persist_overlay_lineage(tmp_path, monkeypatch)
    join = parts["ca_join"]
    stale = join.model_copy(update={"r2_run_hash": _hash("older-r2")})
    # Re-persist a mismatched R14 under the same profile so latest no longer matches.
    from trendforge_api.selection.store import persist_selection_payload

    persist_selection_payload(
        run_id="r14-run-hvb-stale",
        profile_id=join.profile_id,
        as_of=join.decision_at,
        payload=R14CaJoinBatchV1.model_validate(
            {
                **join.model_dump(mode="json", by_alias=True),
                "runId": "r14-run-hvb-stale",
                "r2RunHash": _hash("older-r2"),
            }
        ).model_dump(mode="json", by_alias=True),
    )
    del stale
    with pytest.raises(ValueError, match="WAIT_HYBRID_LINEAGE_MISMATCH"):
        build_hybrid_v2_overlay(limit=5)


def test_spine_is_read_only_view_of_latest(tmp_path, monkeypatch) -> None:
    parts = persist_overlay_lineage(tmp_path, monkeypatch)
    spine = load_hybrid_spine()
    assert spine.bundle.bundle_hash == parts["bundle"].bundle_hash
    assert spine.attention.run_hash == parts["attention"].run_hash
    assert spine.ca_join.run_hash == parts["ca_join"].run_hash
    assert spine.structure.run_hash == parts["structure"].run_hash
    batch = build_hybrid_v2_overlay(limit=5)
    row = batch.rows[0]
    assert row.r1_bundle_hash == spine.bundle.bundle_hash
    assert row.r2_run_hash == spine.attention.run_hash
    assert row.r14_run_hash == spine.ca_join.run_hash
