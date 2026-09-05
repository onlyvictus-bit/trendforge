"""Triple-barrier label spec (lab only). No live CONFIRMED, no persisted labels.

Success = MFE >= +1.5 ATR before MAE <= -1.0 ATR within 5 sessions on the
adjusted series. Fill assumption is next-day open; a signal-day close fill is
rejected outright (V2 upgrade 19).
"""

from __future__ import annotations

from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

DEFAULT_HORIZON = 5
DEFAULT_MFE_ATR = 1.5
DEFAULT_MAE_ATR = -1.0


class TripleBarrierSpec(BaseModel):
    model_config = MODEL_CONFIG

    horizon: int = DEFAULT_HORIZON
    mfe_atr: float = DEFAULT_MFE_ATR
    mae_atr: float = DEFAULT_MAE_ATR
    fill: Literal["next_open"] = "next_open"


class TripleBarrierLabelV1(BaseModel):
    model_config = MODEL_CONFIG

    success: bool | None = None
    censored: bool = False
    fill_price: float | None = None
    mfe_r: float | None = None
    mae_r: float | None = None
    reason: str


def true_range(
    *, high: float, low: float, previous_close: float | None
) -> float:
    if previous_close is None:
        return high - low
    return max(high - low, abs(high - previous_close), abs(low - previous_close))


def atr(
    *,
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> float | None:
    if len(highs) != len(lows) or len(lows) != len(closes):
        raise ValueError("bar series length mismatch")
    if len(closes) < period + 1:
        return None
    ranges = [
        true_range(high=highs[i], low=lows[i], previous_close=closes[i - 1])
        for i in range(1, len(closes))
    ]
    window = ranges[-(period):]
    return sum(window) / len(window)


def label_event(
    *,
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    signal_index: int,
    entry_atr: float,
    spec: TripleBarrierSpec | None = None,
) -> TripleBarrierLabelV1:
    """Label one event. Bars are indexed; signal at signal_index, fill next open."""
    barrier_spec = spec or TripleBarrierSpec()
    if barrier_spec.fill != "next_open":
        raise ValueError("signal-day close fill is rejected; use next_open (upgrade 19)")
    if entry_atr is None or entry_atr <= 0:
        return TripleBarrierLabelV1(reason="ATR_MISSING")
    fill_index = signal_index + 1
    last_index = len(closes) - 1
    if fill_index > last_index:
        return TripleBarrierLabelV1(reason="NO_FORWARD_SESSION")
    fill_price = float(opens[fill_index])
    upper = fill_price + barrier_spec.mfe_atr * entry_atr
    lower = fill_price + barrier_spec.mae_atr * entry_atr
    horizon_end = min(fill_index + barrier_spec.horizon - 1, last_index)
    mfe = 0.0
    mae = 0.0
    for index in range(fill_index, horizon_end + 1):
        high = float(highs[index])
        low = float(lows[index])
        mfe = max(mfe, (high - fill_price) / entry_atr)
        mae = min(mae, (low - fill_price) / entry_atr)
        hit_mae = low <= lower
        hit_mfe = high >= upper
        if hit_mae and hit_mfe:
            # Both barriers inside one bar: conservative MAE-first resolution.
            return TripleBarrierLabelV1(
                success=False,
                fill_price=fill_price,
                mfe_r=round(mfe, 6),
                mae_r=round(mae, 6),
                reason="BOTH_BARRIERS_ONE_BAR_MAE_FIRST",
            )
        if hit_mae:
            return TripleBarrierLabelV1(
                success=False,
                fill_price=fill_price,
                mfe_r=round(mfe, 6),
                mae_r=round(mae, 6),
                reason="MAE_BARRIER",
            )
        if hit_mfe:
            return TripleBarrierLabelV1(
                success=True,
                fill_price=fill_price,
                mfe_r=round(mfe, 6),
                mae_r=round(mae, 6),
                reason="MFE_BARRIER",
            )
    return TripleBarrierLabelV1(
        censored=True,
        fill_price=fill_price,
        mfe_r=round(mfe, 6),
        mae_r=round(mae, 6),
        reason="HORIZON_CENSORED",
    )
