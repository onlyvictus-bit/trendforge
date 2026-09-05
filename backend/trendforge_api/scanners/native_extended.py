"""File A R13 extended native scanners.

The six scanners in this module emit guidance chips only. They never mint an
EvidenceClaim, alter rank/public state, or support CONFIRMED. Inputs are
adjusted, closed, point-in-time EOD bars supplied by native_core.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Literal

from .registry import scanner_definition

FORMULA_VERSION = "R13-GUIDANCE-2.0.0"


def _closes(bars) -> list[float]:
    return [float(bar.close) for bar in bars]


def _volumes(bars) -> list[float]:
    return [float(getattr(bar, "volume", 0.0) or 0.0) for bar in bars]


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5


def _ema_last(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    alpha = 2.0 / (period + 1.0)
    for current in values[period:]:
        value = alpha * current + (1.0 - alpha) * value
    return value


def _wilder_last(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    for current in values[period:]:
        value = ((value * (period - 1)) + current) / period
    return value


def _rsi14(closes: list[float]) -> float | None:
    """Wilder RSI(14), requiring 15 closes and exactly 14 initial deltas."""
    if len(closes) < 15:
        return None
    differences = [
        right - left for left, right in zip(closes, closes[1:], strict=False)
    ]
    gains = [max(value, 0.0) for value in differences]
    losses = [max(-value, 0.0) for value in differences]
    average_gain = sum(gains[:14]) / 14.0
    average_loss = sum(losses[:14]) / 14.0
    for gain, loss in zip(gains[14:], losses[14:], strict=False):
        average_gain = ((average_gain * 13.0) + gain) / 14.0
        average_loss = ((average_loss * 13.0) + loss) / 14.0
    if average_gain == 0 and average_loss == 0:
        return 50.0
    if average_loss == 0:
        return 100.0
    if average_gain == 0:
        return 0.0
    relative_strength = average_gain / average_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def _true_ranges(bars) -> list[float]:
    if not bars:
        return []
    previous_close = float(bars[0].close)
    values: list[float] = []
    for bar in bars:
        high = float(bar.high)
        low = float(bar.low)
        values.append(
            max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        )
        previous_close = float(bar.close)
    return values


def _squeeze_metrics(bars) -> dict[str, float | bool] | None:
    closes = _closes(bars)
    if len(closes) < 31:
        return None
    window = closes[-20:]
    bb_mid = sum(window) / 20.0
    bb_std = _std(window)
    bb_upper = bb_mid + 2.0 * bb_std
    bb_lower = bb_mid - 2.0 * bb_std
    kc_mid = _ema_last(closes, 20)
    atr10 = _wilder_last(_true_ranges(bars), 10)
    if kc_mid is None or atr10 is None:
        return None
    kc_upper = kc_mid + 1.5 * atr10
    kc_lower = kc_mid - 1.5 * atr10
    return {
        "bbMid": bb_mid,
        "bbStd": bb_std,
        "bbUpper": bb_upper,
        "bbLower": bb_lower,
        "kcMid": kc_mid,
        "atr10": atr10,
        "kcUpper": kc_upper,
        "kcLower": kc_lower,
        "squeezeOn": bb_upper < kc_upper and bb_lower > kc_lower,
    }


def _confirmed_pivots(bars, radius: int = 2) -> list[tuple[str, int, float]]:
    """Strict pivots confirmed only after radius bars to the right."""
    pivots: list[tuple[str, int, float]] = []
    for index in range(radius, len(bars) - radius):
        high = float(bars[index].high)
        low = float(bars[index].low)
        neighbours = list(bars[index - radius : index]) + list(
            bars[index + 1 : index + radius + 1]
        )
        high_pivot = all(high > float(bar.high) for bar in neighbours)
        low_pivot = all(low < float(bar.low) for bar in neighbours)
        if high_pivot == low_pivot:
            continue
        kind, value = ("HIGH", high) if high_pivot else ("LOW", low)
        if pivots and pivots[-1][0] == kind:
            previous = pivots[-1]
            more_extreme = value > previous[2] if kind == "HIGH" else value < previous[2]
            if more_extreme:
                pivots[-1] = (kind, index, value)
        else:
            pivots.append((kind, index, value))
    return pivots


def _vcp_metrics(bars) -> tuple[dict[str, Any] | None, str | None]:
    if len(bars) < 61:
        return None, "INPUT_INCOMPLETE_WARMUP:native.vcp.v1"
    pivots = _confirmed_pivots(bars[-61:])
    contractions: list[tuple[float, float, float]] = []
    for left, right in zip(pivots, pivots[1:], strict=False):
        if left[0] != "HIGH" or right[0] != "LOW" or left[2] <= 0:
            continue
        depth = (left[2] - right[2]) / left[2]
        if depth > 0:
            contractions.append((depth, left[2], right[2]))
    if len(contractions) < 3:
        return None, "INPUT_INCOMPLETE_VCP_PIVOTS"
    selected = contractions[-3:]
    depths = [item[0] for item in selected]
    if not (depths[0] > depths[1] > depths[2] > 0):
        return {"contractionDepths": depths, "volumeDryUpRatio": None}, None
    volumes = _volumes(bars)
    prior = sorted(volumes[-60:-10])
    recent = sorted(volumes[-10:])
    if not prior or not recent or prior[len(prior) // 2] <= 0:
        return None, "INPUT_INCOMPLETE_VCP_VOLUME"
    ratio = recent[len(recent) // 2] / prior[len(prior) // 2]
    return {
        "contractionDepths": depths,
        "volumeDryUpRatio": ratio,
        "triggerLevel": selected[-1][1],
        "invalidationLevel": selected[-1][2],
        "matched": ratio <= 0.70,
    }, None


def is_at_extreme(
    closes: list[float], *, lookback: int, kind: Literal["high", "low"]
) -> bool:
    """Compare current close with a prior window that excludes current."""
    if len(closes) < lookback + 1:
        return False
    window = closes[-(lookback + 1) : -1]
    current = closes[-1]
    return current >= max(window) if kind == "high" else current <= min(window)


def _candidate_relationship(
    *, matched: bool, direction: str, candidate_direction: str, input_status: str
) -> str:
    if input_status != "READY":
        return "UNKNOWN"
    if not matched or direction in {"NEUTRAL", "MIXED"}:
        return "NEUTRAL"
    candidate = str(candidate_direction or "UNKNOWN").upper()
    if candidate == "UNKNOWN":
        return "UNKNOWN"
    if candidate in {"MIXED", "NEUTRAL"}:
        return "NEUTRAL"
    return "SUPPORTS" if direction == candidate else "CONFLICTS"


def _bar_as_of(bars) -> str | None:
    if not bars:
        return None
    identity = getattr(bars[-1], "identity", None)
    close_time = getattr(identity, "close_time", None)
    return close_time.isoformat() if close_time is not None else None


def compute_extended_matches(
    bars,
    *,
    reference_level: float | None,
    candidate_direction: str = "UNKNOWN",
    lineage_hash: str | None = None,
    adjustment_version: str | None = None,
    input_reason: str | None = None,
) -> tuple:
    """Return six claimless R13 guidance chips."""
    closes = _closes(bars)
    out: list[Any] = []

    def chip(
        scanner_id: str,
        *,
        matched: bool,
        scanner_state: str,
        direction: str = "NEUTRAL",
        metrics: dict[str, Any] | None = None,
        reason: str | None = None,
        trigger_level: float | None = None,
        invalidation_level: float | None = None,
    ) -> SimpleNamespace:
        definition = scanner_definition(scanner_id)
        parameters = json.loads(definition.parameters_json)
        effective_reason = input_reason or reason
        component_pending = bool(
            effective_reason and str(effective_reason).endswith(":w52")
        )
        input_status = (
            "INPUT_INCOMPLETE"
            if effective_reason and not component_pending
            else "READY"
        )
        effective_matched = bool(matched and input_status == "READY")
        return SimpleNamespace(
            scanner_id=scanner_id,
            matched=effective_matched,
            feature_id=str(parameters.get("featureId", "")),
            claim_id=None,
            family=definition.family,
            group=definition.group,
            correlated_with=(),
            correlated_possible=False,
            guidance_label=definition.guidance_label,
            can_support_confirmed=False,
            reason_code=effective_reason,
            scanner_state=scanner_state if input_status == "READY" else "UNAVAILABLE",
            directional_context=direction if input_status == "READY" else "UNKNOWN",
            candidate_relationship=_candidate_relationship(
                matched=effective_matched,
                direction=direction,
                candidate_direction=candidate_direction,
                input_status=input_status,
            ),
            metrics=metrics or {},
            trigger_level=trigger_level,
            invalidation_level=invalidation_level,
            as_of=_bar_as_of(bars),
            bar_count=len(bars),
            input_status=input_status,
            formula_version=FORMULA_VERSION,
            parameter_hash=definition.parameter_hash,
            lineage_hash=lineage_hash,
            adjustment_version=adjustment_version,
            input_completeness=1.0 if input_status == "READY" else 0.0,
            is_representative=False,
            suppressed_by=None,
            guidance_win_rate=None,
            guidance_approved=False,
            guidance_confirmed=False,
        )

    vcp, vcp_reason = _vcp_metrics(bars)
    out.append(
        chip(
            "native.vcp.v1",
            matched=bool(vcp and vcp.get("matched")),
            scanner_state="VCP_COMPRESSION" if vcp and vcp.get("matched") else "NO_MATCH",
            metrics=vcp,
            reason=vcp_reason,
            trigger_level=(float(vcp["triggerLevel"]) if vcp and vcp.get("triggerLevel") else None),
            invalidation_level=(
                float(vcp["invalidationLevel"])
                if vcp and vcp.get("invalidationLevel")
                else None
            ),
        )
    )

    squeeze = _squeeze_metrics(bars)
    out.append(
        chip(
            "native.ttm_squeeze.v1",
            matched=bool(squeeze and squeeze["squeezeOn"]),
            scanner_state="SQUEEZE_ON" if squeeze and squeeze["squeezeOn"] else "NO_MATCH",
            metrics=squeeze,
            reason=(
                None
                if squeeze is not None
                else "INPUT_INCOMPLETE_WARMUP:native.ttm_squeeze.v1"
            ),
        )
    )

    fast = _sma(closes, 20)
    slow = _sma(closes, 50)
    if len(closes) < 51 or fast is None or slow is None:
        overlay_state, overlay_reason = (
            "UNAVAILABLE",
            "INPUT_INCOMPLETE_WARMUP:native.trend_overlay.v1",
        )
    elif closes[-1] > fast > slow:
        overlay_state, overlay_reason = "BULLISH", None
    elif closes[-1] < fast < slow:
        overlay_state, overlay_reason = "BEARISH", None
    else:
        overlay_state, overlay_reason = "MIXED", None
    out.append(
        chip(
            "native.trend_overlay.v1",
            matched=overlay_state in {"BULLISH", "BEARISH"},
            scanner_state=overlay_state,
            direction=overlay_state if overlay_state != "UNAVAILABLE" else "UNKNOWN",
            metrics={"close": closes[-1] if closes else None, "sma20": fast, "sma50": slow},
            reason=overlay_reason,
        )
    )

    rsi = _rsi14(closes)
    momentum_state = (
        "UNAVAILABLE"
        if rsi is None
        else "BULLISH"
        if rsi > 50.0
        else "BEARISH"
        if rsi < 50.0
        else "NEUTRAL"
    )
    out.append(
        chip(
            "native.momentum.v1",
            matched=momentum_state in {"BULLISH", "BEARISH"},
            scanner_state=(
                "RSI_ABOVE_50"
                if momentum_state == "BULLISH"
                else "RSI_BELOW_50"
                if momentum_state == "BEARISH"
                else momentum_state
            ),
            direction=momentum_state if momentum_state != "UNAVAILABLE" else "UNKNOWN",
            metrics={"rsi14": rsi},
            reason=(
                None
                if rsi is not None
                else "INPUT_INCOMPLETE_WARMUP:native.momentum.v1"
            ),
        )
    )

    reversal_direction = "NEUTRAL"
    reversal_reason = None
    if reference_level is None or len(closes) < 12:
        reversal_reason = (
            "INPUT_INCOMPLETE_REFERENCE:native.reversal.v1"
            if reference_level is None
            else "INPUT_INCOMPLETE_WARMUP:native.reversal.v1"
        )
    else:
        scan = closes[-10:]
        for index in range(len(scan) - 1):
            reclaim = scan[index + 1 : index + 4]
            if scan[index] < reference_level and any(
                value > reference_level for value in reclaim
            ) and scan[-1] > reference_level:
                reversal_direction = "BULLISH"
            if scan[index] > reference_level and any(
                value < reference_level for value in reclaim
            ) and scan[-1] < reference_level:
                reversal_direction = "BEARISH"
    out.append(
        chip(
            "native.reversal.v1",
            matched=reversal_direction in {"BULLISH", "BEARISH"},
            scanner_state=(
                f"{reversal_direction}_FAILED_BREAK_REVERSAL"
                if reversal_direction in {"BULLISH", "BEARISH"}
                else "NO_MATCH"
            ),
            direction=reversal_direction,
            metrics={"referenceLevel": reference_level},
            reason=reversal_reason,
            trigger_level=reference_level,
            invalidation_level=reference_level,
        )
    )

    extreme_states: list[str] = []
    if len(closes) >= 11:
        if is_at_extreme(closes, lookback=10, kind="high"):
            extreme_states.append("10D_HIGH")
        elif is_at_extreme(closes, lookback=10, kind="low"):
            extreme_states.append("10D_LOW")
    if len(closes) >= 253:
        if is_at_extreme(closes, lookback=252, kind="high"):
            extreme_states.append("52W_HIGH")
        elif is_at_extreme(closes, lookback=252, kind="low"):
            extreme_states.append("52W_LOW")
    extremes_reason = (
        "INPUT_INCOMPLETE_WARMUP:native.extremes.v1"
        if len(closes) < 11
        else "INPUT_INCOMPLETE_WARMUP:native.extremes.v1:w52"
        if len(closes) < 253
        else None
    )
    extremes_direction = (
        "BULLISH"
        if any(state.endswith("HIGH") for state in extreme_states)
        else "BEARISH"
        if any(state.endswith("LOW") for state in extreme_states)
        else "NEUTRAL"
    )
    out.append(
        chip(
            "native.extremes.v1",
            matched=bool(extreme_states),
            scanner_state="+".join(extreme_states) if extreme_states else "NO_MATCH",
            direction=extremes_direction,
            metrics={"states": extreme_states},
            reason=extremes_reason,
        )
    )
    return tuple(out)


__all__ = [
    "FORMULA_VERSION",
    "_rsi14",
    "_squeeze_metrics",
    "_vcp_metrics",
    "compute_extended_matches",
    "is_at_extreme",
]
