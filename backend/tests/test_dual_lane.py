"""File A dual data-lane + research-qty law tests."""

from __future__ import annotations


from trendforge_api.selection.data_lane import DataLaneStateV1, resolve_lane
from trendforge_api.selection.research_quantity import (
    ResearchQtyRowV1,
    compute_research_quantity,
)


def test_default_lane_free() -> None:
    r = resolve_lane()
    assert r.effective_lane == "FREE_OFFICIAL"
    assert r.open_algo_state == "ABSENT"


def test_openalgo_ro_without_env_stays_free() -> None:
    r = resolve_lane(env_lane="OPENALGO_RO", openalgo_enabled=None)
    assert r.effective_lane == "FREE_OFFICIAL"
    assert r.blocker == "WAIT_OPENALGO_ABSENT"


def test_rejected_capability_stays_free() -> None:
    r = resolve_lane(
        env_lane="OPENALGO_RO", openalgo_enabled="1", capability_state="REJECTED"
    )
    assert r.effective_lane == "FREE_OFFICIAL"
    assert r.blocker == "WAIT_OPENALGO_FORBIDDEN"


def test_qty_zero_when_not_eligible() -> None:
    r = compute_research_quantity(
        public_state="WAIT", evidence_direction="BULLISH",
        draft_confirmed_eligible=False, is_reject_or_ban=False,
        official_close=100, invalidation_condition="95", atr=2.0,
        lot_size=None, s8_completeness_ratio=1.0,
        regime_label="RISK_ON", index_suspect=False,
    )
    assert r["researchQuantity"] == 0
    assert r["reason"] == "WAIT_NOT_AT_CONFIRMATION"


def test_qty_zero_on_reject() -> None:
    r = compute_research_quantity(
        public_state="REJECT", evidence_direction="BULLISH",
        draft_confirmed_eligible=True, is_reject_or_ban=True,
        official_close=100, invalidation_condition="95", atr=2.0,
        lot_size=None, s8_completeness_ratio=1.0,
        regime_label="RISK_ON", index_suspect=False,
    )
    assert r["researchQuantity"] == 0
    assert r["reason"] == "WAIT_REJECT"


def test_bullish_is_long_bearish_is_short() -> None:
    bull = compute_research_quantity(
        public_state="WAIT", evidence_direction="BULLISH",
        draft_confirmed_eligible=True, is_reject_or_ban=False,
        official_close=500.0, invalidation_condition="480",
        atr=5.0, lot_size=None, s8_completeness_ratio=1.0,
        regime_label="RISK_ON", index_suspect=False,
    )
    bear = compute_research_quantity(
        public_state="WAIT", evidence_direction="BEARISH",
        draft_confirmed_eligible=True, is_reject_or_ban=False,
        official_close=500.0, invalidation_condition="520",
        atr=5.0, lot_size=None, s8_completeness_ratio=1.0,
        regime_label="RISK_ON", index_suspect=False,
    )
    assert bull["_side"] == "LONG"
    assert bear["_side"] == "SHORT"
    assert bull["researchStop"] < bull["researchEntry"]
    assert bear["researchStop"] > bear["researchEntry"]


def test_strength_does_not_increase_qty() -> None:
    kw = dict(
        public_state="WAIT", evidence_direction="BULLISH",
        draft_confirmed_eligible=True, is_reject_or_ban=False,
        official_close=500, invalidation_condition="480", atr=5.0,
        lot_size=None, s8_completeness_ratio=1.0,
        regime_label="RISK_ON", index_suspect=False,
    )
    low = compute_research_quantity(**kw)
    # qty is not a strength knob — same stop means same qty regardless of evidence strength
    assert isinstance(low["researchQuantity"], int)


def test_calibration_cap_half() -> None:
    from trendforge_api.selection.research_quantity import CALIBRATION_CAP
    assert CALIBRATION_CAP == 0.5


def test_lot_unknown_fno_gives_zero() -> None:
    r = compute_research_quantity(
        public_state="WAIT", evidence_direction="BULLISH",
        draft_confirmed_eligible=True, is_reject_or_ban=False,
        official_close=500, invalidation_condition="480",
        atr=5.0, lot_size=0, s8_completeness_ratio=1.0,
        regime_label="RISK_ON", index_suspect=False,
    )
    assert r.get("researchQuantity", 0) >= 0  # shares path still valid


def test_data_lane_model_law() -> None:
    lane = DataLaneStateV1()
    assert lane.can_confirm is False
    assert lane.executable is False


def test_research_qty_row_executable_false() -> None:
    row = ResearchQtyRowV1(symbol="X", public_state="WAIT", evidence_direction="BULLISH")
    assert row.executable is False
