from __future__ import annotations

from datetime import datetime, timedelta, timezone

from trendforge_api import storage
from trendforge_api.harmonic_scan_lifecycle import track_detected_harmonic
from trendforge_api.models import (
    GateResult,
    HarmonicAdvancedAnalysis,
    OHLCVCandle,
    PivotPoint,
    RatioValidation,
)


BASE = datetime(2026, 7, 1, 9, 15, tzinfo=timezone.utc)


def candle(offset: int, *, high: float, low: float, close: float) -> OHLCVCandle:
    return OHLCVCandle(
        symbol="LIFESCAN",
        timeframe="1d",
        source="fixture",
        timestamp=(BASE + timedelta(days=offset)).isoformat(),
        open=close,
        high=high,
        low=low,
        close=close,
        volume=1_000_000,
        trustLevel="SYNTHETIC_TEST",
        fetchedAt=(BASE + timedelta(days=offset, hours=1)).isoformat(),
    )


def analysis() -> HarmonicAdvancedAnalysis:
    prices = [120.0, 140.0, 125.0, 120.0, 100.0]
    kinds = ["low", "high", "low", "high", "low"]
    pivots = [
        PivotPoint(
            index=index,
            kind=kind,
            timestamp=(BASE + timedelta(days=index)).isoformat(),
            price=price,
            sensitivities=[5, 8, 13],
            quality=0.9,
        )
        for index, (kind, price) in enumerate(zip(kinds, prices, strict=True))
    ]
    validation = RatioValidation(
        patternName="Gartley",
        direction="bullish",
        toleranceTier="STRICT",
        score=0.95,
        passed=True,
        ratios={"XAB": 0.618, "ABC": 0.5, "BCD": 1.5, "XAD": 0.786},
        required={},
        przLow=99.4,
        przHigh=100.6,
        invalidationPrice=98.5,
        target1=107.64,
        target2=112.36,
        target3=120.0,
    )
    return HarmonicAdvancedAnalysis(
        symbol="LIFESCAN",
        timeframe="1d",
        candleCount=5,
        pivots=pivots,
        validations=[validation],
        gates=[
            GateResult(
                code="G00_DATA_HEALTHY",
                name="Data healthy",
                result="PASS",
                weight=3,
                reason="fixture",
            )
        ],
        hybridQualityScore=0.9,
        gateRatio=0.7,
        finalState="HARMONIC_PRZ_ACTIVE",
        lifecycleState="COMPLETE",
    )


def test_scheduled_tracking_uses_stable_key_and_progressive_events(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "scheduled-life.db")
    detected = analysis()
    through_d = [candle(i, high=101, low=100, close=100.5) for i in range(5)]

    first = track_detected_harmonic(
        through_d,
        detected,
        source="fixture",
        trust_level="SYNTHETIC_TEST",
    )
    assert first.status == "TRACKED"
    assert first.lifecycle_state == "COMPLETE"
    assert first.saved_events == 1

    progressed = through_d + [
        candle(5, high=102, low=100.8, close=101.8),
        candle(6, high=108, low=101.5, close=107.8),
    ]
    second = track_detected_harmonic(
        progressed,
        detected,
        source="fixture",
        trust_level="SYNTHETIC_TEST",
    )
    assert second.pattern_key == first.pattern_key
    assert second.lifecycle_state == "WIN_T1"
    assert second.saved_events == 2
    assert [
        row["state"]
        for row in storage.list_harmonic_lifecycle_events(pattern_key=first.pattern_key)
    ] == ["COMPLETE", "TRIGGERED", "WIN_T1"]

    repeated = track_detected_harmonic(
        progressed,
        detected,
        source="fixture",
        trust_level="SYNTHETIC_TEST",
    )
    assert repeated.saved_events == 0
    assert len(storage.list_general_alerts(symbol="LIFESCAN")) == 3


def test_lifecycle_tracking_rejects_unpassed_and_naive_source_data(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "scheduled-wait.db")
    weak = analysis()
    weak.validations[0].passed = False
    rows = [candle(i, high=101, low=100, close=100.5) for i in range(5)]
    skipped = track_detected_harmonic(
        rows, weak, source="fixture", trust_level="SYNTHETIC_TEST"
    )
    assert skipped.status == "NOT_APPLICABLE"
    assert skipped.saved_events == 0

    healthy = analysis()
    rows[-1].timestamp = "2026-07-05T09:15:00"
    waiting = track_detected_harmonic(
        rows, healthy, source="fixture", trust_level="SYNTHETIC_TEST"
    )
    assert waiting.status == "WAIT_TIMEZONE"
    assert waiting.saved_events == 0


def test_existing_sequence_conflict_is_fail_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "scheduled-conflict.db")
    detected = analysis()
    initial = [candle(i, high=101, low=100, close=100.5) for i in range(5)] + [
        candle(5, high=102, low=100.8, close=101.8)
    ]
    tracked = track_detected_harmonic(
        initial, detected, source="fixture", trust_level="SYNTHETIC_TEST"
    )
    assert tracked.lifecycle_state == "TRIGGERED"

    corrected = initial[:-1] + [candle(5, high=101, low=98, close=98.4)]
    conflict = track_detected_harmonic(
        corrected, detected, source="fixture", trust_level="SYNTHETIC_TEST"
    )
    assert conflict.status == "CONFLICT_DATA_REVISION"
    assert conflict.saved_events == 0
    assert "sequence 2" in conflict.reason
    assert [
        row["state"]
        for row in storage.list_harmonic_lifecycle_events(
            pattern_key=tracked.pattern_key
        )
    ] == ["COMPLETE", "TRIGGERED"]
