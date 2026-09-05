from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Literal, cast

from pydantic import BaseModel, Field

from .harmonic_lifecycle import (
    HarmonicLifecycleInput,
    LifecyclePriceBar,
    evaluate_harmonic_lifecycle,
)
from .models import HarmonicAdvancedAnalysis, OHLCVCandle, PivotPoint, RatioValidation
from .records import AlertCreate
from .storage import (
    list_harmonic_lifecycle_events,
    save_general_alert,
    save_harmonic_lifecycle_events,
)


TrackingStatus = Literal[
    "TRACKED",
    "NOT_APPLICABLE",
    "WAIT_TIMEZONE",
    "WAIT_LEVELS",
    "WAIT_CHRONOLOGY",
    "CONFLICT_DATA_REVISION",
]


class HarmonicTrackingResult(BaseModel):
    status: TrackingStatus
    pattern_key: str | None = Field(default=None, alias="patternKey")
    lifecycle_state: str | None = Field(default=None, alias="lifecycleState")
    saved_events: int = Field(default=0, alias="savedEvents")
    alerts_created: int = Field(default=0, alias="alertsCreated")
    trigger_price: float | None = Field(default=None, alias="triggerPrice")
    reason: str
    executable: Literal[False] = False

    model_config = {"populate_by_name": True}


EXPIRY_WINDOWS = {
    "5m": timedelta(days=2),
    "15m": timedelta(days=4),
    "30m": timedelta(days=7),
    "1h": timedelta(days=10),
    "4h": timedelta(days=30),
    "4h_custom": timedelta(days=30),
    "1d": timedelta(days=45),
    "1w": timedelta(days=180),
}


def _aware_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def stable_pattern_key(
    symbol: str,
    timeframe: str,
    validation: RatioValidation,
    pivots: list[PivotPoint],
) -> str:
    identity = {
        "symbol": symbol.upper().strip(),
        "timeframe": timeframe,
        "pattern": validation.pattern_name,
        "direction": validation.direction,
        "anchors": [
            {
                "kind": pivot.kind,
                "timestamp": pivot.timestamp,
                "price": round(pivot.price, 4),
            }
            for pivot in pivots[-5:]
        ],
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    pattern = validation.pattern_name.upper().replace(" ", "_")
    return f"HARM:{identity['symbol']}:{timeframe}:{pattern}:{digest}"


def _trigger_price(validation: RatioValidation) -> float | None:
    if (
        validation.prz_low is None
        or validation.prz_high is None
        or validation.target1 is None
    ):
        return None
    if validation.direction == "bullish":
        distance = validation.target1 - validation.prz_high
        return round(validation.prz_high + distance * 0.10, 4) if distance > 0 else None
    if validation.direction == "bearish":
        distance = validation.prz_low - validation.target1
        return round(validation.prz_low - distance * 0.10, 4) if distance > 0 else None
    return None


def _required_levels_present(validation: RatioValidation) -> bool:
    return all(
        value is not None and value > 0
        for value in (
            validation.prz_low,
            validation.prz_high,
            validation.invalidation_price,
            validation.target1,
            validation.target2,
            validation.target3,
        )
    )


def _transition_alert(
    *,
    symbol: str,
    timeframe: str,
    pattern_key: str,
    pattern_name: str,
    transition: dict,
    validation: RatioValidation,
    trigger_price: float,
    source: str,
    trust_level: str,
    data_cutoff: str,
) -> None:
    state = str(transition["state"])
    severity: Literal["INFO", "WARN", "CRITICAL"] = (
        "WARN" if state in {"INVALIDATED", "LOSS"} else "INFO"
    )
    save_general_alert(
        AlertCreate(
            alertType=f"HARMONIC_{state}",
            severity=severity,
            symbol=symbol,
            state=state,
            reason=f"{pattern_name} lifecycle changed to {state}: {transition['reason']}",
            risk={
                "patternKey": pattern_key,
                "timeframe": timeframe,
                "eventAt": transition["eventAt"],
                "triggerPrice": trigger_price,
                "invalidationPrice": validation.invalidation_price,
                "target1": validation.target1,
                "target2": validation.target2,
                "target3": validation.target3,
                "source": source,
                "trustLevel": trust_level,
                "dataCutoff": data_cutoff,
                "executable": False,
            },
        )
    )


def track_detected_harmonic(
    candles: list[OHLCVCandle],
    analysis: HarmonicAdvancedAnalysis,
    *,
    source: str,
    trust_level: str,
    persist: bool = True,
) -> HarmonicTrackingResult:
    validation = analysis.validations[0] if analysis.validations else None
    if (
        not candles
        or validation is None
        or not validation.passed
        or validation.direction not in {"bullish", "bearish"}
        or len(analysis.pivots) < 5
    ):
        return HarmonicTrackingResult(
            status="NOT_APPLICABLE",
            reason="No completed STRICT/NORMAL harmonic is available for lifecycle tracking.",
        )
    if not _required_levels_present(validation):
        return HarmonicTrackingResult(
            status="WAIT_LEVELS",
            reason="Lifecycle tracking requires PRZ, invalidation, and all three targets.",
        )
    trigger_price = _trigger_price(validation)
    if trigger_price is None:
        return HarmonicTrackingResult(
            status="WAIT_LEVELS",
            reason="A reaction trigger cannot be placed between the PRZ and target 1.",
        )
    assert validation.direction in {"bullish", "bearish"}
    assert validation.prz_low is not None
    assert validation.prz_high is not None
    assert validation.invalidation_price is not None
    assert validation.target1 is not None
    assert validation.target2 is not None
    assert validation.target3 is not None
    direction = cast(Literal["bullish", "bearish"], validation.direction)

    parsed_candles: list[tuple[datetime, OHLCVCandle]] = []
    for candle in candles:
        timestamp = _aware_datetime(candle.timestamp)
        if timestamp is None:
            return HarmonicTrackingResult(
                status="WAIT_TIMEZONE",
                reason=f"Candle timestamp lacks a valid source timezone: {candle.timestamp}",
            )
        parsed_candles.append((timestamp, candle))
    parsed_candles.sort(key=lambda item: item[0])
    completed_at = _aware_datetime(analysis.pivots[-1].timestamp)
    if completed_at is None:
        return HarmonicTrackingResult(
            status="WAIT_TIMEZONE",
            reason="The D pivot timestamp lacks a valid source timezone.",
        )
    as_of = parsed_candles[-1][0]
    if as_of < completed_at:
        return HarmonicTrackingResult(
            status="WAIT_CHRONOLOGY",
            reason="The candle cutoff precedes the detected D pivot.",
        )

    pattern_key = stable_pattern_key(
        analysis.symbol, analysis.timeframe, validation, analysis.pivots
    )
    bars = [
        LifecyclePriceBar(
            timestamp=timestamp,
            high=candle.high,
            low=candle.low,
            close=candle.close,
        )
        for timestamp, candle in parsed_candles
        if timestamp >= completed_at
    ]
    payload = HarmonicLifecycleInput(
        patternKey=pattern_key,
        symbol=analysis.symbol,
        timeframe=analysis.timeframe,
        patternName=validation.pattern_name,
        direction=direction,
        asOf=as_of,
        completedAt=completed_at,
        expiresAt=completed_at
        + EXPIRY_WINDOWS.get(analysis.timeframe, timedelta(days=45)),
        przLow=validation.prz_low,
        przHigh=validation.prz_high,
        triggerPrice=trigger_price,
        invalidationPrice=validation.invalidation_price,
        target1=validation.target1,
        target2=validation.target2,
        target3=validation.target3,
        bars=bars,
    )
    result = evaluate_harmonic_lifecycle(payload)
    serialized = result.model_dump(mode="json", by_alias=True)

    existing = list_harmonic_lifecycle_events(pattern_key=pattern_key)
    existing_by_sequence = {row["sequence"]: row for row in existing}
    new_transitions: list[dict] = []
    for transition in serialized["transitions"]:
        prior = existing_by_sequence.get(transition["sequence"])
        if prior is None:
            new_transitions.append(transition)
            continue
        if (
            prior["state"] != transition["state"]
            or prior["event_at"] != transition["eventAt"]
        ):
            return HarmonicTrackingResult(
                status="CONFLICT_DATA_REVISION",
                patternKey=pattern_key,
                lifecycleState=prior["state"],
                triggerPrice=trigger_price,
                reason=(
                    f"Stored lifecycle sequence {transition['sequence']} conflicts with "
                    "the revised candle evaluation; history was not rewritten."
                ),
            )

    saved_events = save_harmonic_lifecycle_events(serialized) if persist else 0
    if persist and saved_events != len(new_transitions):
        return HarmonicTrackingResult(
            status="CONFLICT_DATA_REVISION",
            patternKey=pattern_key,
            lifecycleState=result.state,
            triggerPrice=trigger_price,
            reason="Lifecycle persistence count did not match the expected new transitions.",
        )
    if persist:
        for transition in new_transitions:
            _transition_alert(
                symbol=analysis.symbol,
                timeframe=analysis.timeframe,
                pattern_key=pattern_key,
                pattern_name=validation.pattern_name,
                transition=transition,
                validation=validation,
                trigger_price=trigger_price,
                source=source,
                trust_level=trust_level,
                data_cutoff=parsed_candles[-1][1].timestamp,
            )
    return HarmonicTrackingResult(
        status="TRACKED",
        patternKey=pattern_key,
        lifecycleState=result.state,
        savedEvents=saved_events,
        alertsCreated=len(new_transitions) if persist else 0,
        triggerPrice=trigger_price,
        reason=result.reason,
    )
