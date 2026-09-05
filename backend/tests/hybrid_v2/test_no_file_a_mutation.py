"""C14: the overlay must never mutate the File A spine it reads."""

from __future__ import annotations

from trendforge_api.hybrid_v2.pipeline import build_hybrid_v2_overlay
from trendforge_api.hybrid_v2.tests_support.fixtures import persist_overlay_lineage
from trendforge_api.selection.attention_order import latest_attention_order
from trendforge_api.selection.r14_live import latest_r14_ca_join
from trendforge_api.selection.r5_live import latest_r5_structure_batch


def test_c14_overlay_run_does_not_change_spine_hashes(tmp_path, monkeypatch) -> None:
    parts = persist_overlay_lineage(tmp_path, monkeypatch)
    before_r2 = latest_attention_order().run_hash
    before_r14 = latest_r14_ca_join().run_hash
    before_r5 = latest_r5_structure_batch().run_hash

    for _ in range(3):
        batch = build_hybrid_v2_overlay(limit=5)

    assert latest_attention_order().run_hash == before_r2
    assert latest_r14_ca_join().run_hash == before_r14
    assert latest_r5_structure_batch().run_hash == before_r5
    # And the overlay row carries exactly those hashes.
    row = batch.rows[0]
    assert row.r1_bundle_hash == parts["bundle"].bundle_hash
    assert row.r2_run_hash == before_r2
    assert row.r14_run_hash == before_r14
    assert row.r5_run_hash == before_r5


def test_c14_confirmed_count_stays_zero_on_persisted_r5(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    build_hybrid_v2_overlay(limit=5)
    structure = latest_r5_structure_batch()
    assert structure.confirmed_count == 0
    assert all(
        item.structure_state.value != "CONFIRMED" for item in structure.rows
    )


def test_c15_source_activation_ready_stays_false_everywhere(tmp_path, monkeypatch) -> None:
    from trendforge_api.selection.r14_live import latest_r14_ca_join as latest_join

    persist_overlay_lineage(tmp_path, monkeypatch)
    build_hybrid_v2_overlay(limit=5)
    assert latest_attention_order().source_activation_ready is False
    assert latest_join().source_activation_ready is False
