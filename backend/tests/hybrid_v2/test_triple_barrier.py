"""Triple-barrier label spec: fixture tests only, no live bars invention."""

from __future__ import annotations

import pytest

from trendforge_api.hybrid_v2.as_lab.triple_barrier import (
    TripleBarrierSpec,
    atr,
    label_event,
)


def _series(count: int = 10, *, base: float = 100.0):
    opens = [base] * count
    highs = [base + 0.5] * count
    lows = [base - 0.5] * count
    closes = [base] * count
    return opens, highs, lows, closes


def test_mfe_barrier_success_within_horizon() -> None:
    opens, highs, lows, closes = _series()
    highs[5] = 110.0  # fill at opens[4]=100; +1.5 ATR (ATR=1) barrier hit
    label = label_event(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        signal_index=3,
        entry_atr=1.0,
    )
    assert label.success is True
    assert label.fill_price == 100.0
    assert label.reason == "MFE_BARRIER"


def test_mae_barrier_failure() -> None:
    opens, highs, lows, closes = _series()
    lows[5] = 98.0  # below 100 - 1.0 ATR
    label = label_event(
        opens=opens, highs=highs, lows=lows, closes=closes,
        signal_index=3, entry_atr=1.0,
    )
    assert label.success is False
    assert label.reason == "MAE_BARRIER"


def test_both_barriers_one_bar_resolves_mae_first() -> None:
    opens, highs, lows, closes = _series()
    highs[5] = 110.0
    lows[5] = 98.0
    label = label_event(
        opens=opens, highs=highs, lows=lows, closes=closes,
        signal_index=3, entry_atr=1.0,
    )
    assert label.success is False
    assert label.reason == "BOTH_BARRIERS_ONE_BAR_MAE_FIRST"


def test_horizon_censored_is_not_a_claim() -> None:
    opens, highs, lows, closes = _series(count=6)
    label = label_event(
        opens=opens, highs=highs, lows=lows, closes=closes,
        signal_index=3, entry_atr=1.0,
    )
    assert label.censored is True
    assert label.success is None


def test_c12_signal_day_close_fill_is_rejected() -> None:
    # The spec type forbids any other fill mode; injecting signal_close must
    # fail validation, which is the code-level rejection of upgrade 19.
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TripleBarrierSpec.model_validate({"fill": "signal_close"})
    assert TripleBarrierSpec().fill == "next_open"


def test_atr_requires_full_window() -> None:
    opens, highs, lows, closes = _series(count=5)
    assert atr(highs=highs, lows=lows, closes=closes, period=14) is None
    opens, highs, lows, closes = _series(count=20)
    assert atr(highs=highs, lows=lows, closes=closes, period=14) == 1.0


def test_no_forward_session_is_explicit() -> None:
    opens, highs, lows, closes = _series(count=5)
    label = label_event(
        opens=opens, highs=highs, lows=lows, closes=closes,
        signal_index=4, entry_atr=1.0,
    )
    assert label.reason == "NO_FORWARD_SESSION"
    assert label.success is None
