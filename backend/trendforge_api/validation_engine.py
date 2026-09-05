from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .harmonic_advanced import analyze_harmonic_advanced
from .models import OHLCVCandle


@dataclass(frozen=True)
class PathOutcome:
    label: str
    bars: int
    mfe_percent: float
    mae_percent: float


def label_price_path(
    future: list[OHLCVCandle],
    *,
    entry: float,
    stop: float,
    target: float,
    direction: str,
) -> PathOutcome:
    if entry <= 0 or stop <= 0 or target <= 0:
        raise ValueError("entry, stop, and target must be positive")
    best = entry
    worst = entry
    for index, candle in enumerate(future, start=1):
        if direction == "bullish":
            best = max(best, candle.high)
            worst = min(worst, candle.low)
            stop_hit = candle.low <= stop
            target_hit = candle.high >= target
        elif direction == "bearish":
            best = min(best, candle.low)
            worst = max(worst, candle.high)
            stop_hit = candle.high >= stop
            target_hit = candle.low <= target
        else:
            raise ValueError("direction must be bullish or bearish")
        # Intrabar ordering is unknown in OHLC data. Stop-first is the
        # conservative deterministic rule when both levels occur in one bar.
        if stop_hit:
            return _path_result("LOSS", index, entry, best, worst, direction)
        if target_hit:
            return _path_result("WIN", index, entry, best, worst, direction)
    return _path_result("UNRESOLVED", len(future), entry, best, worst, direction)


def _path_result(
    label: str, bars: int, entry: float, best: float, worst: float, direction: str
) -> PathOutcome:
    if direction == "bullish":
        mfe = (best - entry) / entry * 100
        mae = (worst - entry) / entry * 100
    else:
        mfe = (entry - best) / entry * 100
        mae = (entry - worst) / entry * 100
    return PathOutcome(
        label=label, bars=bars, mfe_percent=round(mfe, 4), mae_percent=round(mae, 4)
    )


def backtest_harmonic_series(
    candles: list[OHLCVCandle],
    *,
    symbol: str,
    timeframe: str,
    warmup: int = 80,
    max_holding_bars: int = 40,
) -> dict:
    if len(candles) < warmup + 2:
        return _empty_report(symbol, timeframe, len(candles), "WAIT_DATA_WEAK")
    observations: list[dict] = []
    seen: set[tuple] = set()
    for cutoff in range(warmup - 1, len(candles) - 1):
        prefix = candles[: cutoff + 1]
        analysis = analyze_harmonic_advanced(prefix, symbol, timeframe)
        best = analysis.validations[0] if analysis.validations else None
        if (
            best is None
            or not best.passed
            or best.invalidation_price is None
            or best.target1 is None
        ):
            continue
        pivots = analysis.pivots[-5:]
        if len(pivots) < 5:
            continue
        pattern_key = (
            best.pattern_name,
            best.direction,
            tuple(point.timestamp for point in pivots),
        )
        if pattern_key in seen:
            continue
        seen.add(pattern_key)
        entry = prefix[-1].close
        risk = abs(entry - best.invalidation_price)
        reward = abs(best.target1 - entry)
        if risk <= 0:
            continue
        future = candles[cutoff + 1 : cutoff + 1 + max_holding_bars]
        outcome = label_price_path(
            future,
            entry=entry,
            stop=best.invalidation_price,
            target=best.target1,
            direction=best.direction,
        )
        observations.append(
            {
                "pattern": best.pattern_name,
                "direction": best.direction,
                "detectedAt": prefix[-1].timestamp,
                "dataCutoffIndex": cutoff,
                "entry": round(entry, 4),
                "stop": best.invalidation_price,
                "target": best.target1,
                "rewardRisk": round(reward / risk, 4),
                "outcome": outcome.label,
                "barsToOutcome": outcome.bars,
                "mfePercent": outcome.mfe_percent,
                "maePercent": outcome.mae_percent,
            }
        )
    wins = sum(item["outcome"] == "WIN" for item in observations)
    losses = sum(item["outcome"] == "LOSS" for item in observations)
    unresolved = len(observations) - wins - losses
    resolved = wins + losses
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candleCount": len(candles),
        "observationCount": len(observations),
        "wins": wins,
        "losses": losses,
        "unresolved": unresolved,
        "targetBeforeStopRate": round(wins / resolved, 4) if resolved else None,
        "falsePositiveRate": round(losses / resolved, 4) if resolved else None,
        "averageMfePercent": round(mean(item["mfePercent"] for item in observations), 4)
        if observations
        else None,
        "averageMaePercent": round(mean(item["maePercent"] for item in observations), 4)
        if observations
        else None,
        "sameBarRule": "STOP_FIRST_CONSERVATIVE",
        "validationMethod": "EXPANDING_PREFIX_NO_FUTURE_CANDLES",
        "status": "COMPLETE" if observations else "NO_PATTERNS",
        "observations": observations,
    }


def _empty_report(symbol: str, timeframe: str, candle_count: int, status: str) -> dict:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candleCount": candle_count,
        "observationCount": 0,
        "wins": 0,
        "losses": 0,
        "unresolved": 0,
        "targetBeforeStopRate": None,
        "falsePositiveRate": None,
        "averageMfePercent": None,
        "averageMaePercent": None,
        "sameBarRule": "STOP_FIRST_CONSERVATIVE",
        "validationMethod": "EXPANDING_PREFIX_NO_FUTURE_CANDLES",
        "status": status,
        "observations": [],
    }
