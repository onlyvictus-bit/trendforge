from __future__ import annotations

from datetime import datetime
from math import isfinite

from .feature_registry import FEATURE_REGISTRY_VERSION
from .indicator_engine import (
    INDICATOR_ENGINE_ID,
    INDICATOR_ENGINE_VERSION,
    verify_indicator_runtime,
)
from .models import OHLCVCandle


FEATURE_VERSION = "1.1.0"
FEATURE_MANIFEST = {
    "featureRegistryVersion": FEATURE_REGISTRY_VERSION,
    "indicatorEngineId": INDICATOR_ENGINE_ID,
    "indicatorEngineVersion": INDICATOR_ENGINE_VERSION,
}


def _input_error(candles: list[OHLCVCandle]) -> str | None:
    if len(candles) < 20:
        return "INSUFFICIENT_WARMUP: 20 closed bars are required"
    if any(candle.bar_state != "COMPLETE" for candle in candles):
        return "UNCLOSED_BAR: only COMPLETE bars count toward warm-up"
    if len({candle.timestamp for candle in candles}) != len(candles):
        return "DUPLICATE_BAR: warm-up requires distinct timestamps"
    try:
        timestamps = [
            datetime.fromisoformat(candle.timestamp.replace("Z", "+00:00"))
            for candle in candles
        ]
    except ValueError:
        return "INVALID_TIMESTAMP: every bar needs an ISO timestamp"
    if any(timestamp.utcoffset() is None for timestamp in timestamps):
        return "NAIVE_TIMESTAMP: every bar timestamp needs a timezone"
    if timestamps != sorted(timestamps):
        return "UNORDERED_BARS: bars must be oldest-to-newest"
    for field in ("symbol", "timeframe", "source"):
        if len({getattr(candle, field) for candle in candles}) != 1:
            return f"MIXED_{field.upper()}: warm-up bars must share one {field}"
    return None


def build_point_in_time_features(candles: list[OHLCVCandle]) -> dict:
    runtime = verify_indicator_runtime()
    if not runtime.ok:
        return {
            "featureVersion": FEATURE_VERSION,
            **FEATURE_MANIFEST,
            "state": "ENGINE_MISMATCH",
            "nullReason": "; ".join(runtime.errors),
            "candleCount": len(candles),
        }
    input_error = _input_error(candles)
    if input_error:
        return {
            "featureVersion": FEATURE_VERSION,
            **FEATURE_MANIFEST,
            "state": "INPUT_INCOMPLETE",
            "nullReason": input_error,
            "candleCount": len(candles),
        }
    closes = [candle.close for candle in candles]
    latest = candles[-1]
    previous = candles[-2]
    returns_1 = (latest.close / previous.close - 1) if previous.close > 0 else 0.0
    returns_5 = (latest.close / candles[-6].close - 1) if candles[-6].close > 0 else 0.0
    true_ranges = []
    for index in range(max(1, len(candles) - 14), len(candles)):
        candle = candles[index]
        prior_close = candles[index - 1].close
        true_ranges.append(
            max(
                candle.high - candle.low,
                abs(candle.high - prior_close),
                abs(candle.low - prior_close),
            )
        )
    atr14 = sum(true_ranges) / len(true_ranges)
    recent = candles[-20:]
    average_volume = sum(max(candle.volume, 0) for candle in recent[:-1]) / max(
        len(recent) - 1, 1
    )
    rvol20 = latest.volume / average_volume if average_volume > 0 else 0.0
    total_volume = sum(max(candle.volume, 0) for candle in recent)
    vwap20 = (
        sum(candle.close * max(candle.volume, 0) for candle in recent) / total_volume
        if total_volume > 0
        else None
    )
    ema20 = _ema(closes[-60:], 20)
    values = {
        "return1": returns_1,
        "return5": returns_5,
        "atr14Percent": atr14 / latest.close if latest.close > 0 else 0.0,
        "rvol20": rvol20,
        "vwap20Distance": (latest.close / vwap20 - 1)
        if vwap20 and vwap20 > 0
        else None,
        "ema20Distance": (latest.close / ema20 - 1) if ema20 > 0 else 0.0,
        "rangePosition20": _range_position(recent, latest.close),
    }
    if not all(value is None or isfinite(value) for value in values.values()):
        return {
            "featureVersion": FEATURE_VERSION,
            **FEATURE_MANIFEST,
            "state": "REJECT_DATA_INTEGRITY",
            "candleCount": len(candles),
        }
    return {
        "featureVersion": FEATURE_VERSION,
        **FEATURE_MANIFEST,
        "state": "OK",
        "candleCount": len(candles),
        "dataCutoff": latest.timestamp,
        "source": latest.source,
        "trustLevel": latest.trust_level.value,
        **{
            key: round(value, 8) if isinstance(value, float) else value
            for key, value in values.items()
        },
    }


def _ema(values: list[float], period: int) -> float:
    alpha = 2 / (period + 1)
    result = values[0]
    for value in values[1:]:
        result = alpha * value + (1 - alpha) * result
    return result


def _range_position(candles: list[OHLCVCandle], close: float) -> float:
    low = min(candle.low for candle in candles)
    high = max(candle.high for candle in candles)
    if high <= low:
        return 0.5
    return (close - low) / (high - low)
