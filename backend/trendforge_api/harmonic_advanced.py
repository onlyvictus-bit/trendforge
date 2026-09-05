from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from .models import (
    GateResult,
    HarmonicAdvancedAnalysis,
    HarmonicAlertRecord,
    OHLCVCandle,
    PivotPoint,
    RatioValidation,
)


ZIGZAG_CONFIGS: dict[str, list[int]] = {
    "5m": [5, 8, 13],
    "15m": [5, 8, 13],
    "30m": [5, 8, 13],
    "1h": [5, 8, 13],
    "4h": [3, 5, 8],
    "4h_custom": [3, 5, 8],
    "1d": [5, 8, 13],
    "1w": [3, 5, 8],
}


TIMEFRAME_WEIGHTS = {
    "5m": 0.25,
    "15m": 0.45,
    "30m": 0.55,
    "1h": 0.65,
    "4h": 0.75,
    "4h_custom": 0.80,
    "1d": 0.90,
    "1w": 1.00,
}


RATIO_TABLE: dict[str, dict[str, tuple[float, float]]] = {
    "Gartley": {
        "XAB": (0.588, 0.648),
        "ABC": (0.382, 0.886),
        "BCD": (1.272, 1.618),
        "XAD": (0.746, 0.826),
    },
    "Bat": {
        "XAB": (0.382, 0.500),
        "ABC": (0.382, 0.886),
        "BCD": (1.618, 2.618),
        "XAD": (0.846, 0.926),
    },
    "Butterfly": {
        "XAB": (0.746, 0.826),
        "ABC": (0.382, 0.886),
        "BCD": (1.618, 2.618),
        "XAD": (1.272, 1.618),
    },
    "Crab": {
        "XAB": (0.382, 0.618),
        "ABC": (0.382, 0.886),
        "BCD": (2.240, 3.618),
        "XAD": (1.568, 1.668),
    },
    "Deep Crab": {
        "XAB": (0.846, 0.926),
        "ABC": (0.382, 0.886),
        "BCD": (2.000, 3.618),
        "XAD": (1.568, 1.668),
    },
    "Cypher": {"XAB": (0.382, 0.618), "ABC": (1.130, 1.414), "XCD": (0.746, 0.826)},
    "Shark": {"XAB": (0.382, 0.886), "ABC": (1.130, 1.618), "XAD": (0.886, 1.130)},
    "Five-0": {"ABC": (1.618, 2.240), "BCD": (0.450, 0.550)},
    "ABCD": {"ABC": (0.618, 0.786), "BCD": (1.272, 1.618)},
    "AB=CD": {"ABCD": (0.950, 1.050)},
}


@dataclass
class RawPivot:
    index: int
    kind: str
    timestamp: str
    price: float
    sensitivity: int


def _volume_ratio(candles: list[OHLCVCandle], index: int, lookback: int = 20) -> float:
    start = max(0, index - lookback)
    base = candles[start:index]
    if not base:
        return 0.0
    avg = sum(candle.volume for candle in base) / len(base)
    if avg <= 0:
        return 0.0
    return candles[index].volume / avg


def _wick_score(candle: OHLCVCandle) -> float:
    body = abs(candle.close - candle.open)
    full_range = max(candle.high - candle.low, 0.0001)
    wick = full_range - body
    return max(0.0, min(1.0, wick / full_range))


def _detect_pivots_for_sensitivity(
    candles: list[OHLCVCandle], sensitivity: int
) -> list[RawPivot]:
    pivots: list[RawPivot] = []
    if len(candles) < sensitivity * 2 + 5:
        return pivots
    for index in range(sensitivity, len(candles) - sensitivity):
        window = candles[index - sensitivity : index + sensitivity + 1]
        candle = candles[index]
        if candle.high == max(row.high for row in window):
            pivots.append(
                RawPivot(index, "high", candle.timestamp, candle.high, sensitivity)
            )
        if candle.low == min(row.low for row in window):
            pivots.append(
                RawPivot(index, "low", candle.timestamp, candle.low, sensitivity)
            )
    return pivots


def build_multi_sensitivity_pivots(
    candles: list[OHLCVCandle], timeframe: str
) -> list[PivotPoint]:
    sensitivities = ZIGZAG_CONFIGS.get(timeframe, [5, 8, 13])
    raw: list[RawPivot] = []
    for sensitivity in sensitivities:
        raw.extend(_detect_pivots_for_sensitivity(candles, sensitivity))
    raw.sort(key=lambda pivot: (pivot.index, pivot.kind))

    groups: list[list[RawPivot]] = []
    for pivot in raw:
        matched = False
        for group in groups:
            anchor = group[0]
            price_distance = abs(pivot.price - anchor.price) / max(
                abs(anchor.price), 0.0001
            )
            if (
                pivot.kind == anchor.kind
                and abs(pivot.index - anchor.index) <= 2
                and price_distance <= 0.003
            ):
                group.append(pivot)
                matched = True
                break
        if not matched:
            groups.append([pivot])

    points: list[PivotPoint] = []
    for group in groups:
        kind = group[0].kind
        selected = (
            max(group, key=lambda p: p.price)
            if kind == "high"
            else min(group, key=lambda p: p.price)
        )
        found_sensitivities = sorted({item.sensitivity for item in group})
        consensus = len(found_sensitivities) / len(sensitivities)
        volume_score = min(1.0, _volume_ratio(candles, selected.index) / 2.0)
        wick_score = _wick_score(candles[selected.index])
        quality = round(
            min(1.0, consensus * 0.60 + volume_score * 0.20 + wick_score * 0.20), 3
        )
        points.append(
            PivotPoint(
                index=selected.index,
                kind=kind,  # type: ignore[arg-type]
                timestamp=selected.timestamp,
                price=round(selected.price, 4),
                sensitivities=found_sensitivities,
                quality=quality,
            )
        )

    return _dedupe_alternating(points)


def _dedupe_alternating(points: list[PivotPoint]) -> list[PivotPoint]:
    if not points:
        return []
    points = sorted(points, key=lambda p: p.index)
    cleaned: list[PivotPoint] = []
    for point in points:
        if not cleaned:
            cleaned.append(point)
            continue
        last = cleaned[-1]
        if point.kind == last.kind:
            replace = (
                point.price > last.price
                if point.kind == "high"
                else point.price < last.price
            )
            if replace or point.quality > last.quality:
                cleaned[-1] = point
        else:
            cleaned.append(point)
    return cleaned


def _ratio(value: float, base: float) -> float:
    if abs(base) <= 0.000001:
        return 0.0
    return abs(value / base)


def _latest_xabcd(points: list[PivotPoint]) -> list[PivotPoint] | None:
    if len(points) < 5:
        return None
    return points[-5:]


def _pattern_ratios(points: list[PivotPoint]) -> dict[str, float]:
    x, a, b, c, d = points
    xa = abs(a.price - x.price)
    ab = abs(b.price - a.price)
    bc = abs(c.price - b.price)
    cd = abs(d.price - c.price)
    xc = abs(c.price - x.price)
    return {
        "XAB": round(_ratio(ab, xa), 4),
        "ABC": round(_ratio(bc, ab), 4),
        "BCD": round(_ratio(cd, bc), 4),
        "XAD": round(_ratio(abs(d.price - a.price), xa), 4),
        "XCD": round(_ratio(abs(d.price - c.price), xc), 4),
        "ABCD": round(_ratio(cd, ab), 4),
    }


def _score_ratio(actual: float, low: float, high: float) -> tuple[bool, float]:
    if actual <= 0:
        return False, 0.0
    center = (low + high) / 2
    width = max((high - low) / 2, 0.03)
    distance = abs(actual - center)
    score = max(0.0, 1.0 - distance / max(center * 0.18, width))
    return low <= actual <= high, score


def validate_harmonic_ratios(points: list[PivotPoint]) -> list[RatioValidation]:
    latest = _latest_xabcd(points)
    if latest is None:
        return []
    x, a, b, c, d = latest
    ratios = _pattern_ratios(latest)
    direction: Literal["bullish", "bearish"] = (
        "bullish" if d.kind == "low" else "bearish"
    )
    validations: list[RatioValidation] = []
    for pattern_name, required in RATIO_TABLE.items():
        scores: list[float] = []
        failures: list[str] = []
        required_text: dict[str, str] = {}
        for key, bounds in required.items():
            low, high = bounds
            actual = ratios.get(key, 0.0)
            passed, score = _score_ratio(actual, low, high)
            scores.append(score)
            required_text[key] = f"{low:.3f}-{high:.3f}"
            if not passed:
                failures.append(f"{key} {actual:.3f} outside {low:.3f}-{high:.3f}")
        score = sum(scores) / max(len(scores), 1)
        if score >= 0.80 and not failures:
            tier = "STRICT"
        elif score >= 0.62 and len(failures) <= 1:
            tier = "NORMAL"
        elif score >= 0.45:
            tier = "EXPLORATORY"
        else:
            tier = "FAIL"

        span = abs(c.price - d.price)
        # PRZ is a cluster around D, not the full C-D leg.
        prz_low = d.price - span * 0.03
        prz_high = d.price + span * 0.03
        invalidation = d.price * (0.985 if direction == "bullish" else 1.015)
        target1 = d.price + (span * 0.382 if direction == "bullish" else -span * 0.382)
        target2 = d.price + (span * 0.618 if direction == "bullish" else -span * 0.618)
        target3 = d.price + (span if direction == "bullish" else -span)

        validations.append(
            RatioValidation(
                patternName=pattern_name,
                direction=direction,
                toleranceTier=tier,
                score=round(score, 3),
                passed=tier in {"STRICT", "NORMAL"},
                ratios=ratios,
                required=required_text,
                przLow=round(prz_low, 2),
                przHigh=round(prz_high, 2),
                invalidationPrice=round(invalidation, 2),
                target1=round(target1, 2),
                target2=round(target2, 2),
                target3=round(target3, 2),
                reasons=failures,
            )
        )
    return sorted(validations, key=lambda item: item.score, reverse=True)


def _vwap(candles: list[OHLCVCandle]) -> float | None:
    total_volume = sum(max(candle.volume, 0.0) for candle in candles)
    if total_volume <= 0:
        return None
    return (
        sum(candle.close * max(candle.volume, 0.0) for candle in candles) / total_volume
    )


def hybrid_quality_score(
    candles: list[OHLCVCandle],
    pivots: list[PivotPoint],
    validation: RatioValidation | None,
    timeframe: str,
) -> float:
    if not validation:
        return 0.0
    pivot_score = sum(point.quality for point in pivots[-5:]) / max(len(pivots[-5:]), 1)
    maturity_score = (
        1.0
        if validation.prz_low
        and validation.prz_high
        and validation.prz_low <= candles[-1].close <= validation.prz_high
        else 0.55
    )
    volume_score = min(1.0, _volume_ratio(candles, len(candles) - 1) / 2.0)
    tf_score = TIMEFRAME_WEIGHTS.get(timeframe, 0.5)
    symmetry = (
        min(1.0, validation.ratios.get("ABCD", 0.0)) if validation.ratios else 0.0
    )
    score = (
        validation.score * 0.35
        + pivot_score * 0.20
        + maturity_score * 0.15
        + volume_score * 0.15
        + tf_score * 0.10
        + symmetry * 0.05
    )
    return round(max(0.0, min(1.0, score)), 3)


def score_gates(
    candles: list[OHLCVCandle],
    pivots: list[PivotPoint],
    validation: RatioValidation | None,
    timeframe: str,
) -> tuple[list[GateResult], float, str]:
    gates: list[GateResult] = []

    def add(
        code: str,
        name: str,
        result: Literal["PASS", "FAIL", "NEUTRAL", "UNKNOWN"],
        weight: int,
        reason: str,
    ) -> None:
        gates.append(
            GateResult(
                code=code, name=name, result=result, weight=weight, reason=reason
            )
        )

    data_ok = len(candles) >= 40 and bool(pivots)
    add(
        "G00_DATA_HEALTHY",
        "Data healthy",
        "PASS" if data_ok else "FAIL",
        0,
        "Enough candles and pivots" if data_ok else "Insufficient candles or pivots",
    )
    if not validation:
        add(
            "G01_RATIO_STRICT",
            "Ratio strict/normal",
            "FAIL",
            3,
            "No valid ratio candidate",
        )
    else:
        add(
            "G01_RATIO_STRICT",
            "Ratio strict/normal",
            "PASS" if validation.passed else "FAIL",
            3,
            validation.tolerance_tier,
        )

    pivot_ok = len(pivots) >= 5 and all(point.quality >= 0.50 for point in pivots[-5:])
    add(
        "G02_PIVOT_QUALITY",
        "Pivot quality",
        "PASS" if pivot_ok else "FAIL",
        2,
        "Last five pivots quality >= 0.50"
        if pivot_ok
        else "Pivot quality below threshold",
    )

    cluster_ok = bool(
        validation
        and validation.prz_low
        and validation.prz_high
        and (validation.prz_high - validation.prz_low) / max(validation.prz_high, 1)
        <= 0.08
    )
    add(
        "G03_PRZ_CLUSTER",
        "PRZ cluster",
        "PASS" if cluster_ok else "UNKNOWN",
        2,
        "PRZ range is tight" if cluster_ok else "Full Fib cluster engine pending",
    )

    add(
        "G04_HTF_ALIGNED",
        "HTF aligned",
        "UNKNOWN",
        3,
        "Higher timeframe adapter pending",
    )
    add(
        "G05_SAME_PATTERN_MTF",
        "Same pattern MTF",
        "UNKNOWN",
        2,
        "MTF pattern map pending",
    )
    add(
        "G06_NO_MTF_CONFLICT",
        "No MTF conflict",
        "UNKNOWN",
        2,
        "MTF conflict engine pending",
    )

    latest = candles[-1] if candles else None
    prz_reject = False
    if latest and validation and validation.prz_low and validation.prz_high:
        if validation.direction == "bullish":
            prz_reject = (
                latest.low <= validation.prz_high and latest.close >= validation.prz_low
            )
        elif validation.direction == "bearish":
            prz_reject = (
                latest.high >= validation.prz_low
                and latest.close <= validation.prz_high
            )
    add(
        "G07_PRZ_REJECTION",
        "PRZ rejection",
        "PASS" if prz_reject else "UNKNOWN",
        3,
        "Price interacted with PRZ" if prz_reject else "No confirmed PRZ rejection yet",
    )

    vol_ratio = _volume_ratio(candles, len(candles) - 1) if candles else 0.0
    add(
        "G08_VOLUME_SURGE",
        "Volume surge",
        "PASS" if vol_ratio >= 1.5 else "FAIL",
        2,
        f"Latest volume {vol_ratio:.2f}x 20-bar average",
    )

    vwap = _vwap(candles[-80:]) if candles else None
    vwap_pass = False
    if latest and vwap and validation:
        vwap_pass = (
            latest.close >= vwap
            if validation.direction == "bullish"
            else latest.close <= vwap
        )
    add(
        "G09_VWAP_RECLAIM",
        "VWAP reclaim/reject",
        "PASS" if vwap_pass else "UNKNOWN",
        2,
        f"VWAP {vwap:.2f}" if vwap else "VWAP unavailable",
    )

    add(
        "G10_MOMENTUM_DIVERGENCE",
        "Momentum divergence",
        "UNKNOWN",
        1,
        "RSI/MACD divergence engine pending",
    )
    add("G11_SECTOR_ALIGNED", "Sector aligned", "UNKNOWN", 1, "Sector adapter pending")
    add(
        "G12_SMART_MONEY",
        "Smart money",
        "UNKNOWN",
        1,
        "AMFI/deal/delivery adapter pending",
    )
    add("G13_OI_CONFIRMS", "OI confirms", "UNKNOWN", 1, "OI/MWPL/basis adapter pending")

    rr_ok = False
    if latest and validation and validation.invalidation_price and validation.target1:
        risk = abs(latest.close - validation.invalidation_price)
        reward = abs(validation.target1 - latest.close)
        rr_ok = risk > 0 and reward / risk >= 1.5
    add(
        "G14_RISK_REWARD",
        "Risk/reward",
        "PASS" if rr_ok else "FAIL",
        0,
        "Target 1 R:R >= 1.5" if rr_ok else "Target 1 R:R below 1.5 or unavailable",
    )

    positive_weight = sum(gate.weight for gate in gates if gate.weight > 0)
    pass_weight = sum(
        gate.weight for gate in gates if gate.weight > 0 and gate.result == "PASS"
    )
    gate_ratio = round(pass_weight / positive_weight, 3) if positive_weight else 0.0
    final_state = assign_gate_state(gates, gate_ratio, validation)
    return gates, gate_ratio, final_state


def assign_gate_state(
    gates: list[GateResult], gate_ratio: float, validation: RatioValidation | None
) -> str:
    gate_map = {gate.code: gate.result for gate in gates}
    if gate_map.get("G00_DATA_HEALTHY") == "FAIL":
        return "WAIT_DATA_WEAK"
    if gate_map.get("G14_RISK_REWARD") == "FAIL":
        return "REJECT_RISK_REWARD_WEAK"
    if (
        gate_ratio >= 0.70
        and gate_map.get("G07_PRZ_REJECTION") == "PASS"
        and gate_map.get("G08_VOLUME_SURGE") == "PASS"
    ):
        if validation and validation.direction == "bearish":
            return "HARMONIC_CONFIRMED_BEARISH"
        return "HARMONIC_CONFIRMED_BULLISH"
    if gate_ratio >= 0.45:
        return "HARMONIC_PRZ_ACTIVE"
    if gate_ratio >= 0.25:
        return "HARMONIC_WATCH_FORMING"
    return "REJECT_PATTERN_LOW_QUALITY"


def lifecycle_state(
    candles: list[OHLCVCandle], validation: RatioValidation | None, final_state: str
) -> str:
    if not validation or not candles:
        return "FORMING"
    latest = candles[-1].close
    if validation.invalidation_price:
        if (
            validation.direction == "bullish"
            and latest <= validation.invalidation_price
        ):
            return "INVALIDATED"
        if (
            validation.direction == "bearish"
            and latest >= validation.invalidation_price
        ):
            return "INVALIDATED"
    targets = [validation.target1, validation.target2, validation.target3]
    for idx, target in reversed(list(enumerate(targets, start=1))):
        if target is None:
            continue
        if validation.direction == "bullish" and latest >= target:
            return f"WIN_T{idx}"
        if validation.direction == "bearish" and latest <= target:
            return f"WIN_T{idx}"
    if final_state.startswith("HARMONIC_CONFIRMED"):
        return "TRIGGERED"
    if (
        validation.prz_low
        and validation.prz_high
        and validation.prz_low <= latest <= validation.prz_high
    ):
        return "COMPLETE"
    return "FORMING"


def build_alerts(
    symbol: str,
    timeframe: str,
    validation: RatioValidation | None,
    final_state: str,
    lifecycle: str,
) -> list[HarmonicAlertRecord]:
    alerts: list[HarmonicAlertRecord] = []
    if not validation:
        return alerts
    if final_state == "WAIT_DATA_WEAK":
        alerts.append(
            HarmonicAlertRecord(
                symbol=symbol,
                timeframe=timeframe,
                alertType="DATA_STALE",
                message="Data health blocks harmonic signal.",
                state=final_state,
            )
        )
    elif lifecycle == "COMPLETE":
        alerts.append(
            HarmonicAlertRecord(
                symbol=symbol,
                timeframe=timeframe,
                alertType="PRZ_ENTERED",
                message=f"{validation.pattern_name} reached PRZ; wait for confirmation.",
                state=final_state,
            )
        )
    elif final_state.startswith("HARMONIC_CONFIRMED"):
        alerts.append(
            HarmonicAlertRecord(
                symbol=symbol,
                timeframe=timeframe,
                alertType="CONFIRMED",
                message=f"{validation.pattern_name} confirmed; still check full TrendForge gates.",
                state=final_state,
            )
        )
    elif lifecycle.startswith("WIN_"):
        alerts.append(
            HarmonicAlertRecord(
                symbol=symbol,
                timeframe=timeframe,
                alertType="TARGET_HIT",
                message=f"{validation.pattern_name} {lifecycle}.",
                state=final_state,
            )
        )
    elif lifecycle == "INVALIDATED":
        alerts.append(
            HarmonicAlertRecord(
                symbol=symbol,
                timeframe=timeframe,
                alertType="INVALIDATED",
                message=f"{validation.pattern_name} invalidated.",
                state=final_state,
            )
        )
    return alerts


def analyze_harmonic_advanced(
    candles: list[OHLCVCandle], symbol: str, timeframe: str
) -> HarmonicAdvancedAnalysis:
    pivots = build_multi_sensitivity_pivots(candles, timeframe)
    validations = validate_harmonic_ratios(pivots)
    best = validations[0] if validations else None
    gates, gate_ratio, final_state = score_gates(candles, pivots, best, timeframe)
    quality = hybrid_quality_score(candles, pivots, best, timeframe)
    lifecycle = lifecycle_state(candles, best, final_state)
    alerts = [
        alert.message
        for alert in build_alerts(symbol, timeframe, best, final_state, lifecycle)
    ]
    return HarmonicAdvancedAnalysis(
        symbol=symbol,
        timeframe=timeframe,
        candleCount=len(candles),
        pivots=pivots,
        validations=validations[:5],
        gates=gates,
        hybridQualityScore=quality,
        gateRatio=gate_ratio,
        finalState=final_state,
        lifecycleState=lifecycle,
        alerts=alerts,
    )


def benchmark_analysis(candles: list[OHLCVCandle], symbol: str, timeframe: str) -> dict:
    started = perf_counter()
    analysis = analyze_harmonic_advanced(candles, symbol, timeframe)
    duration = perf_counter() - started
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "durationSeconds": round(duration, 4),
        "candleCount": len(candles),
        "pivotCount": len(analysis.pivots),
        "validationCount": len(analysis.validations),
        "target": "WATCHLIST_ONLY all core TFs under 30 seconds",
        "passed": duration < 30,
    }


def chart_overlay_payload(
    candles: list[OHLCVCandle], analysis: HarmonicAdvancedAnalysis
) -> dict:
    best = analysis.validations[0] if analysis.validations else None
    pivots = analysis.pivots[-5:]
    values = [
        candle.model_dump(mode="json", by_alias=True) for candle in candles[-160:]
    ]
    return {
        "symbol": analysis.symbol,
        "timeframe": analysis.timeframe,
        "candles": values,
        "pivots": [pivot.model_dump(mode="json") for pivot in pivots],
        "pattern": best.model_dump(mode="json", by_alias=True) if best else None,
        "prz": {"low": best.prz_low, "high": best.prz_high} if best else None,
        "targets": {"t1": best.target1, "t2": best.target2, "t3": best.target3}
        if best
        else None,
        "invalidation": best.invalidation_price if best else None,
        "finalState": analysis.final_state,
        "gateRatio": analysis.gate_ratio,
        "hybridQualityScore": analysis.hybrid_quality_score,
    }


def liquidity_prefilter(
    candles: list[OHLCVCandle],
    *,
    min_avg_volume: float = 500_000,
    min_price: float = 50,
    min_avg_value: float = 10_000_000,
) -> dict:
    recent = candles[-20:]
    if len(recent) < 20:
        return {
            "state": "WAIT_DATA_WEAK",
            "passed": False,
            "reason": "Need at least 20 candles for liquidity check.",
            "avgVolume20d": 0,
            "avgValue20d": 0,
            "lastPrice": candles[-1].close if candles else 0,
            "unknown": ["market_cap", "ASM_GSM"],
        }
    avg_volume = sum(candle.volume for candle in recent) / len(recent)
    last_price = recent[-1].close
    avg_value = sum(candle.volume * candle.close for candle in recent) / len(recent)
    failures: list[str] = []
    if avg_volume < min_avg_volume:
        failures.append(f"avg volume {avg_volume:.0f} < {min_avg_volume:.0f}")
    if last_price < min_price:
        failures.append(f"price {last_price:.2f} < {min_price:.2f}")
    if avg_value < min_avg_value:
        failures.append(f"avg traded value {avg_value:.0f} < {min_avg_value:.0f}")
    return {
        "state": "PASS" if not failures else "SKIP_LIQUIDITY_WEAK",
        "passed": not failures,
        "reason": "Liquidity gate passed." if not failures else "; ".join(failures),
        "avgVolume20d": round(avg_volume, 2),
        "avgValue20d": round(avg_value, 2),
        "lastPrice": round(last_price, 2),
        "thresholds": {
            "minAvgVolume": min_avg_volume,
            "minPrice": min_price,
            "minAvgValue": min_avg_value,
        },
        "unknown": ["market_cap", "ASM_GSM"],
    }
