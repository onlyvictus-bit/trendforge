from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel

from .feature_registry import FEATURE_REGISTRY_VERSION, feature_contract_by_id
from .indicator_engine import (
    INDICATOR_ENGINE_ID,
    INDICATOR_ENGINE_VERSION,
    verify_indicator_runtime,
)


INSTITUTIONAL_FEATURE_KEYS = (
    "ema_9",
    "ema_20",
    "ema_50",
    "ema_200",
    "sma_20",
    "sma_50",
    "sma_200",
    "rsi_7",
    "rsi_14",
    "atr_14",
    "natr_14",
    "adx_14",
    "plus_di_14",
    "minus_di_14",
    "roc_10",
    "roc_20",
    "stochastic_k_14",
    "williams_r_14",
    "cci_20",
    "mfi_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    "bollinger_width",
    "donchian_high_20",
    "donchian_low_20",
    "obv",
    "cmf_20",
    "vwap",
    "max_drawdown",
    "var_historical",
    "cvar_historical",
    "annualized_volatility",
    "sharpe",
    "sortino",
)
_INSTITUTIONAL_CONTRACT = feature_contract_by_id("FTR-013")
if _INSTITUTIONAL_CONTRACT is None:
    raise RuntimeError("FTR-013 is missing from the feature registry")
INSTITUTIONAL_MINIMUM_WARMUP_BARS = _INSTITUTIONAL_CONTRACT.minimum_warmup_bars


class InstitutionalFeatureResult(BaseModel):
    values: dict[str, float | None]
    missing: list[str]
    observation_count: int
    state: Literal["OK", "INPUT_INCOMPLETE", "ENGINE_MISMATCH"]
    null_reason: str | None = None
    feature_registry_version: str = FEATURE_REGISTRY_VERSION
    indicator_engine_id: str = INDICATOR_ENGINE_ID
    indicator_engine_version: str = INDICATOR_ENGINE_VERSION
    minimum_warmup_bars: int = INSTITUTIONAL_MINIMUM_WARMUP_BARS


def _last_finite(series: pd.Series) -> float | None:
    clean = series.replace([np.inf, -np.inf], np.nan).dropna()
    return float(clean.iloc[-1]) if not clean.empty else None


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + relative_strength))


def _true_range(frame: pd.DataFrame) -> pd.Series:
    previous_close = frame["close"].shift(1)
    return pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _adx(
    frame: pd.DataFrame, period: int = 14
) -> tuple[pd.Series, pd.Series, pd.Series]:
    up_move = frame["high"].diff()
    down_move = -frame["low"].diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=frame.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=frame.index,
    )
    atr = _true_range(frame).ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    denominator = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / denominator
    return dx.ewm(alpha=1 / period, adjust=False).mean(), plus_di, minus_di


def _input_issue(candles: list[dict[str, Any]]) -> str | None:
    if any(row.get("barState") != "COMPLETE" for row in candles):
        return "UNCLOSED_OR_UNKNOWN_BAR: every input row must declare barState=COMPLETE"
    raw_timestamps = [row.get("timestamp") for row in candles]
    if len(set(raw_timestamps)) != len(raw_timestamps):
        return "DUPLICATE_BAR: warm-up requires distinct timestamps"
    try:
        timestamps = pd.to_datetime(raw_timestamps, utc=True, errors="raise")
    except (ValueError, TypeError):
        return "INVALID_TIMESTAMP: every bar needs a timezone-aware timestamp"
    if not timestamps.is_monotonic_increasing:
        return "UNORDERED_BARS: bars must be oldest-to-newest"
    for field in ("symbol", "timeframe", "source"):
        present = [row.get(field) for row in candles if row.get(field) is not None]
        if present and (len(present) != len(candles) or len(set(present)) != 1):
            return f"MIXED_{field.upper()}: warm-up bars must share one {field}"
    return None


def _incomplete_result(
    observation_count: int,
    reason: str,
    *,
    state: Literal["INPUT_INCOMPLETE", "ENGINE_MISMATCH"] = "INPUT_INCOMPLETE",
) -> InstitutionalFeatureResult:
    return InstitutionalFeatureResult(
        values={key: None for key in INSTITUTIONAL_FEATURE_KEYS},
        missing=list(INSTITUTIONAL_FEATURE_KEYS),
        observation_count=observation_count,
        state=state,
        null_reason=reason,
    )


def _prepare(candles: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(candles)
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"OHLCV candles are missing fields: {', '.join(missing)}")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    frame = frame.sort_values("timestamp")
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[["open", "high", "low", "close", "volume"]].isna().any().any():
        raise ValueError("OHLCV candles contain non-numeric or missing values")
    if (frame[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC prices must be positive")
    if (frame["volume"] < 0).any():
        raise ValueError("volume cannot be negative")
    if (frame["high"] < frame[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("high is inconsistent with OHLC values")
    if (frame["low"] > frame[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("low is inconsistent with OHLC values")
    return frame.reset_index(drop=True)


def build_institutional_features(
    candles: list[dict[str, Any]], *, var_confidence: float = 0.95
) -> InstitutionalFeatureResult:
    if not 0.5 < var_confidence < 1:
        raise ValueError("var_confidence must be between 0.5 and 1")
    runtime = verify_indicator_runtime()
    if not runtime.ok:
        return _incomplete_result(
            len(candles),
            "; ".join(runtime.errors),
            state="ENGINE_MISMATCH",
        )
    input_issue = _input_issue(candles)
    if input_issue:
        return _incomplete_result(len(candles), input_issue)
    frame = _prepare(candles)
    if len(frame) < INSTITUTIONAL_MINIMUM_WARMUP_BARS:
        return _incomplete_result(
            len(frame),
            "INSUFFICIENT_WARMUP: full institutional feature vector requires "
            f"{INSTITUTIONAL_MINIMUM_WARMUP_BARS} closed bars",
        )
    close = frame["close"]
    high = frame["high"]
    low = frame["low"]
    volume = frame["volume"]
    true_range = _true_range(frame)
    atr_14 = true_range.ewm(alpha=1 / 14, adjust=False).mean()
    adx_14, plus_di_14, minus_di_14 = _adx(frame)
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd = ema_12 - ema_26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    middle = close.rolling(20).mean()
    deviation = close.rolling(20).std(ddof=0)
    bollinger_width = (4 * deviation) / middle
    lowest_14 = low.rolling(14).min()
    highest_14 = high.rolling(14).max()
    stochastic_k = 100 * (close - lowest_14) / (highest_14 - lowest_14)
    typical = (high + low + close) / 3
    raw_money_flow = typical * volume
    direction = typical.diff()
    positive_flow = raw_money_flow.where(direction > 0, 0.0).rolling(14).sum()
    negative_flow = raw_money_flow.where(direction < 0, 0.0).rolling(14).sum()
    mfi_14 = 100 - (100 / (1 + positive_flow / negative_flow.replace(0, np.nan)))
    signed_volume = np.sign(close.diff()).fillna(0) * volume
    obv = signed_volume.cumsum()
    money_flow_multiplier = ((close - low) - (high - close)) / (high - low).replace(
        0, np.nan
    )
    cmf_20 = (money_flow_multiplier * volume).rolling(20).sum() / volume.rolling(
        20
    ).sum()
    vwap = (typical * volume).cumsum() / volume.cumsum().replace(0, np.nan)
    returns = close.pct_change().dropna()
    loss_quantile = (
        float(returns.quantile(1 - var_confidence)) if not returns.empty else np.nan
    )
    tail = returns[returns <= loss_quantile]
    running_peak = close.cummax()
    drawdown = close / running_peak - 1
    downside = returns[returns < 0]
    annualized_return = returns.mean() * 252 if not returns.empty else np.nan
    annualized_volatility = (
        returns.std(ddof=0) * np.sqrt(252) if not returns.empty else np.nan
    )
    downside_volatility = (
        downside.std(ddof=0) * np.sqrt(252) if not downside.empty else np.nan
    )
    values: dict[str, float | None] = {
        "ema_9": _last_finite(close.ewm(span=9, adjust=False).mean()),
        "ema_20": _last_finite(close.ewm(span=20, adjust=False).mean()),
        "ema_50": _last_finite(close.ewm(span=50, adjust=False).mean()),
        "ema_200": _last_finite(close.ewm(span=200, adjust=False).mean()),
        "sma_20": _last_finite(middle),
        "sma_50": _last_finite(close.rolling(50).mean()),
        "sma_200": _last_finite(close.rolling(200).mean()),
        "rsi_7": _last_finite(_rsi(close, 7)),
        "rsi_14": _last_finite(_rsi(close, 14)),
        "atr_14": _last_finite(atr_14),
        "natr_14": _last_finite(100 * atr_14 / close),
        "adx_14": _last_finite(adx_14),
        "plus_di_14": _last_finite(plus_di_14),
        "minus_di_14": _last_finite(minus_di_14),
        "roc_10": _last_finite(close.pct_change(10) * 100),
        "roc_20": _last_finite(close.pct_change(20) * 100),
        "stochastic_k_14": _last_finite(stochastic_k),
        "williams_r_14": _last_finite(
            -100 * (highest_14 - close) / (highest_14 - lowest_14)
        ),
        "cci_20": _last_finite(
            (typical - typical.rolling(20).mean())
            / (0.015 * typical.rolling(20).std(ddof=0))
        ),
        "mfi_14": _last_finite(mfi_14),
        "macd": _last_finite(macd),
        "macd_signal": _last_finite(macd_signal),
        "macd_histogram": _last_finite(macd - macd_signal),
        "bollinger_width": _last_finite(bollinger_width),
        "donchian_high_20": _last_finite(high.rolling(20).max()),
        "donchian_low_20": _last_finite(low.rolling(20).min()),
        "obv": _last_finite(obv),
        "cmf_20": _last_finite(cmf_20),
        "vwap": _last_finite(vwap),
        "max_drawdown": float(drawdown.min()),
        "var_historical": max(-loss_quantile, 0.0)
        if np.isfinite(loss_quantile)
        else None,
        "cvar_historical": max(-float(tail.mean()), 0.0) if not tail.empty else None,
        "annualized_volatility": float(annualized_volatility)
        if np.isfinite(annualized_volatility)
        else None,
        "sharpe": float(annualized_return / annualized_volatility)
        if annualized_volatility > 0
        else None,
        "sortino": float(annualized_return / downside_volatility)
        if downside_volatility > 0
        else None,
    }
    missing = sorted(
        key for key, value in values.items() if value is None or not np.isfinite(value)
    )
    for key in missing:
        values[key] = None
    if missing:
        return InstitutionalFeatureResult(
            values=values,
            missing=missing,
            observation_count=len(frame),
            state="INPUT_INCOMPLETE",
            null_reason="NON_FINITE_OUTPUT: " + ", ".join(missing),
        )
    return InstitutionalFeatureResult(
        values=values,
        missing=missing,
        observation_count=len(frame),
        state="OK",
    )
