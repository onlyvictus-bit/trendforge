"""Harmonic pattern detector: thin adapter over the harmonic_advanced engine.

No detection math lives here. Pivots, ratio validation, gates, lifecycle and
weak-data semantics all come from ``harmonic_advanced``; this module only
maps the advanced analysis into ``HarmonicPatternResult`` rows (the shape
``save_harmonic_patterns`` persists) plus a fail-closed weak-data path, and
gates the optional third-party pyharmonics comparison behind an env flag.
"""

from __future__ import annotations

import os

from .harmonic_advanced import analyze_harmonic_advanced
from .models import HarmonicPatternResult, HarmonicPoint, OHLCVCandle, PairRow

MIN_CANDLES = 40  # mirrors G00_DATA_HEALTHY in harmonic_advanced.score_gates
_XABCD = ("X", "A", "B", "C", "D")


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def detect_harmonic_patterns(
    candles: list[OHLCVCandle], symbol: str, timeframe: str
) -> tuple[list[HarmonicPatternResult], str | None]:
    """Return (patterns, warning) for closed candles.

    Weak input yields ([], "WAIT_DATA_WEAK: ...") — never fabricated
    patterns. READY is never emitted here; confirmation gates own it.
    """
    if len(candles) < MIN_CANDLES:
        return (
            [],
            f"WAIT_DATA_WEAK: need >= {MIN_CANDLES} closed candles, saw {len(candles)}",
        )
    analysis = analyze_harmonic_advanced(candles, symbol, timeframe)
    if not analysis.validations:
        return [], "WAIT_DATA_WEAK: no ratio candidate"
    best = analysis.validations[0]
    tail = analysis.pivots[-5:]
    points = [
        HarmonicPoint(label=_XABCD[index], timestamp=point.timestamp, price=point.price)
        for index, point in enumerate(tail[:5])
    ]
    smart_money = next(
        (gate for gate in analysis.gates if gate.code == "G12_SMART_MONEY"), None
    )
    reasons = [
        f"Smart-money context: {smart_money.reason if smart_money else 'adapter pending'}",
        *(best.reasons or []),
        f"lifecycle: {analysis.lifecycle_state}",
    ]
    result = HarmonicPatternResult(
        symbol=symbol,
        timeframe=timeframe,
        direction=best.direction,
        patternName=best.pattern_name,
        state=analysis.lifecycle_state,
        sourceEngine="harmonic_advanced",
        points=points,
        przLow=best.prz_low,
        przHigh=best.prz_high,
        invalidationPrice=best.invalidation_price,
        target1=best.target1,
        target2=best.target2,
        confidence=max(0, min(100, int(round(analysis.gate_ratio * 100)))),
        confirmationState="UNCONFIRMED",
        finalState=analysis.final_state,
        reasons=reasons,
        gates=[PairRow(label=gate.code, value=f"{gate.result}: {gate.reason}") for gate in analysis.gates],
    )
    return [result], None


def attempt_pyharmonics(
    candles: list[OHLCVCandle], symbol: str, timeframe: str
) -> tuple[int, str]:
    """Best-effort third-party comparison. Disabled by default (license)."""
    if not _env_truthy("TRENDFORGE_ENABLE_PYHARMONICS"):
        return (
            0,
            "pyharmonics comparison disabled by default (restrictive NOC license); "
            "set TRENDFORGE_ENABLE_PYHARMONICS=1 to attempt",
        )
    try:
        import pyharmonics  # type: ignore[import-not-found]  # noqa: F401
    except Exception as exc:
        return 0, f"pyharmonics unavailable: {type(exc).__name__}"
    return (
        0,
        "pyharmonics present but comparison harness is not wired; "
        "the internal engine remains the source of truth",
    )

