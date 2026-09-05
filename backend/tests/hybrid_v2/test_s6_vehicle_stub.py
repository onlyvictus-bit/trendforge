"""C9/C10: S6 stays UNKNOWN_NEEDS_R12 and B4 never touches the WITHOUT p-hat."""

from __future__ import annotations

from trendforge_api.hybrid_v2.blocks.b4_positioning import b4_package, b4_z
from trendforge_api.hybrid_v2.contracts import S6_VEHICLE_STATUS
from trendforge_api.hybrid_v2.pipeline import build_hybrid_v2_overlay
from trendforge_api.hybrid_v2.stages.s6_vehicle import s6_vehicle_status
from trendforge_api.hybrid_v2.tests_support.fixtures import persist_overlay_lineage
from trendforge_api.selection.r5_live import R5StructureRowV1


def test_c9_s6_is_always_unknown_needs_r12(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    batch = build_hybrid_v2_overlay(limit=5)
    status, why = s6_vehicle_status()
    assert status == S6_VEHICLE_STATUS == "UNKNOWN_NEEDS_R12"
    assert any("R12" in code for code in why)
    assert all(row.s6_vehicle_status == "UNKNOWN_NEEDS_R12" for row in batch.rows)


def test_c9_b4_numeric_z_is_none_without_chain() -> None:
    assert b4_z(chain_present=False) is None
    assert b4_z() is None


def test_c10_b4_package_does_not_change_without_phat(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch, with_structure=True)
    with_batch = build_hybrid_v2_overlay(limit=5)
    row = with_batch.rows[0]
    # The package is derived from the same R5 row but must not enter the logit.
    from trendforge_api.selection.s4s5_compare import BIAS, SIDE_WEIGHT

    expected = round(BIAS + SIDE_WEIGHT * 0.6, 4)
    assert row.b4_package in {"SUPPORT", "WEAKEN", "CONFLICT", "UNKNOWN"}
    assert abs(row.without_s4s5.logit - expected) < 1e-6


def test_b4_package_matches_registry_for_missing_row(tmp_path, monkeypatch) -> None:
    from trendforge_api.selection.s4s5_compare import _package

    assert b4_package(None) == _package(None) == "UNKNOWN"
