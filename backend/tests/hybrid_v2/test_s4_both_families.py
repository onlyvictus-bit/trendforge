"""C6/C7: the overlay S4 must match `s4s5_compare` on the same fixture."""

from __future__ import annotations

from trendforge_api.hybrid_v2.pipeline import build_hybrid_v2_overlay
from trendforge_api.hybrid_v2.stages.s4_probability import book_z, side_z
from trendforge_api.hybrid_v2.tests_support.fixtures import persist_overlay_lineage
from trendforge_api.selection.s4s5_compare import (
    BIAS,
    SIDE_WEIGHT,
    _sigmoid,
    build_s4s5_compare,
)


def _batches(tmp_path, monkeypatch):
    persist_overlay_lineage(tmp_path, monkeypatch)
    overlay = build_hybrid_v2_overlay(limit=5)
    compare = build_s4s5_compare(limit=5)
    return overlay, compare


def test_overlay_matches_s4s5_compare_within_1e6(tmp_path, monkeypatch) -> None:
    overlay, compare = _batches(tmp_path, monkeypatch)
    assert compare.row_count == overlay.row_count == 1
    o = overlay.rows[0]
    c = compare.rows[0]
    assert abs(o.with_s4s5.p_hat - c.with_s4s5.p_hat) < 1e-6
    assert abs(o.without_s4s5.p_hat - c.without_s4s5.p_hat) < 1e-6
    assert abs(o.with_s4s5.logit - c.with_s4s5.logit) < 1e-6
    assert abs(o.without_s4s5.logit - c.without_s4s5.logit) < 1e-6
    # PASS/FAIL chips must agree at the rounding boundary too.
    assert o.with_s4s5.would_pass_p_min == c.with_s4s5.would_pass_p_min
    assert o.without_s4s5.would_pass_p_min == c.without_s4s5.would_pass_p_min
    assert o.kelly_illustration == c.without_s4s5.kelly_illustration


def test_c6_with_exceeds_without_when_book_z_positive(tmp_path, monkeypatch) -> None:
    overlay, _compare = _batches(tmp_path, monkeypatch)
    row = overlay.rows[0]
    # Fixture R5 row carries setups + accepted metrics -> positive book z.
    assert row.without_s4s5.package == "SUPPORT"
    assert row.with_s4s5.p_hat > row.without_s4s5.p_hat


def test_c7_without_logit_omits_book_term(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    overlay = build_hybrid_v2_overlay(limit=5)
    row = overlay.rows[0]
    attention_row_side = side_z(
        state=row.r2_public_state,
        priority=None,
    )
    expected_without = BIAS + SIDE_WEIGHT * 0.6  # fixture priority is 0.6
    del attention_row_side
    assert abs(row.without_s4s5.logit - expected_without) < 1e-6
    assert row.with_s4s5.logit > row.without_s4s5.logit
    assert "z_book" in row.with_s4s5.formula


def test_side_z_matches_registry_values() -> None:
    from trendforge_api.selection.contracts import SelectionState

    assert side_z(state=SelectionState.WATCH, priority=None) == 0.55
    assert side_z(state=SelectionState.WAIT, priority=None) == 0.25
    assert side_z(state=SelectionState.REJECT, priority=None) == 0.0
    assert side_z(state=SelectionState.WATCH, priority=0.42) == 0.42


def test_book_z_zero_without_r5_row() -> None:
    assert book_z(None) == 0.0
    assert _sigmoid(BIAS + SIDE_WEIGHT * 0.25) > 0
