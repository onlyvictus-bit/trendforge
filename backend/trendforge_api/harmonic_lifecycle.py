from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


LifecycleState = Literal[
    "FORMING",
    "COMPLETE",
    "TRIGGERED",
    "INVALIDATED",
    "WIN_T1",
    "WIN_T2",
    "WIN_T3",
    "LOSS",
    "EXPIRED",
]


class LifecyclePriceBar(BaseModel):
    timestamp: datetime
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_bar(self) -> "LifecyclePriceBar":
        if self.timestamp.utcoffset() is None:
            raise ValueError("lifecycle bar timestamp must be timezone-aware")
        if self.high < max(self.low, self.close):
            raise ValueError("bar high must be greater than or equal to low and close")
        if self.low > min(self.high, self.close):
            raise ValueError("bar low must be less than or equal to high and close")
        return self


class HarmonicLifecycleInput(BaseModel):
    pattern_key: str = Field(alias="patternKey", min_length=1, max_length=160)
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(min_length=1, max_length=20)
    pattern_name: str = Field(alias="patternName", min_length=1, max_length=80)
    direction: Literal["bullish", "bearish"]
    as_of: datetime = Field(alias="asOf")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    prz_low: float = Field(alias="przLow", gt=0)
    prz_high: float = Field(alias="przHigh", gt=0)
    trigger_price: float = Field(alias="triggerPrice", gt=0)
    invalidation_price: float = Field(alias="invalidationPrice", gt=0)
    target1: float = Field(gt=0)
    target2: float = Field(gt=0)
    target3: float = Field(gt=0)
    bars: list[LifecyclePriceBar] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_contract(self) -> "HarmonicLifecycleInput":
        timestamps = [self.as_of, self.completed_at, self.expires_at]
        if any(value is not None and value.utcoffset() is None for value in timestamps):
            raise ValueError("lifecycle timestamps must be timezone-aware")
        if self.prz_low > self.prz_high:
            raise ValueError("przLow must be less than or equal to przHigh")
        if self.direction == "bullish":
            if (
                not self.invalidation_price
                < self.prz_low
                <= self.prz_high
                < self.trigger_price
            ):
                raise ValueError("bullish lifecycle levels are not ordered")
            if not self.trigger_price < self.target1 < self.target2 < self.target3:
                raise ValueError("bullish targets must rise above trigger")
        else:
            if (
                not self.invalidation_price
                > self.prz_high
                >= self.prz_low
                > self.trigger_price
            ):
                raise ValueError("bearish lifecycle levels are not ordered")
            if not self.trigger_price > self.target1 > self.target2 > self.target3:
                raise ValueError("bearish targets must fall below trigger")
        return self


class HarmonicLifecycleEvent(BaseModel):
    sequence: int = Field(ge=1)
    state: LifecycleState
    event_at: datetime = Field(alias="eventAt")
    price: float | None = None
    reason: str

    model_config = {"populate_by_name": True}


class HarmonicLifecycleResult(BaseModel):
    pattern_key: str = Field(alias="patternKey")
    symbol: str
    timeframe: str
    state: LifecycleState
    reason: str
    transitions: list[HarmonicLifecycleEvent]
    executable: Literal[False] = False

    model_config = {"populate_by_name": True}


def _hit_invalidation(payload: HarmonicLifecycleInput, bar: LifecyclePriceBar) -> bool:
    if payload.direction == "bullish":
        return bar.low <= payload.invalidation_price
    return bar.high >= payload.invalidation_price


def _hit_trigger(payload: HarmonicLifecycleInput, bar: LifecyclePriceBar) -> bool:
    if payload.direction == "bullish":
        return bar.high >= payload.trigger_price
    return bar.low <= payload.trigger_price


def _highest_target(payload: HarmonicLifecycleInput, bar: LifecyclePriceBar) -> int:
    targets = (payload.target1, payload.target2, payload.target3)
    hits = []
    for index, target in enumerate(targets, start=1):
        if payload.direction == "bullish" and bar.high >= target:
            hits.append(index)
        if payload.direction == "bearish" and bar.low <= target:
            hits.append(index)
    return max(hits, default=0)


def evaluate_harmonic_lifecycle(
    payload: HarmonicLifecycleInput,
) -> HarmonicLifecycleResult:
    transitions: list[HarmonicLifecycleEvent] = []

    def add(
        state: LifecycleState, event_at: datetime, price: float | None, reason: str
    ) -> None:
        transitions.append(
            HarmonicLifecycleEvent(
                sequence=len(transitions) + 1,
                state=state,
                eventAt=event_at,
                price=price,
                reason=reason,
            )
        )

    if payload.completed_at is None:
        add("FORMING", payload.as_of, None, "Pattern has not completed at D/PRZ.")
        return HarmonicLifecycleResult(
            patternKey=payload.pattern_key,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            state="FORMING",
            reason=transitions[-1].reason,
            transitions=transitions,
            executable=False,
        )

    add("COMPLETE", payload.completed_at, None, "Pattern completed at the defined PRZ.")
    terminal: set[LifecycleState] = {
        "INVALIDATED",
        "WIN_T1",
        "WIN_T2",
        "WIN_T3",
        "LOSS",
        "EXPIRED",
    }
    state: LifecycleState = "COMPLETE"
    triggered = False
    bars = sorted(
        (
            bar
            for bar in payload.bars
            if payload.completed_at <= bar.timestamp <= payload.as_of
        ),
        key=lambda bar: bar.timestamp,
    )
    for bar in bars:
        if payload.expires_at and bar.timestamp > payload.expires_at:
            add(
                "EXPIRED",
                payload.expires_at,
                None,
                "Pattern expired before a valid trigger or terminal outcome.",
            )
            state = "EXPIRED"
            break
        invalidation_hit = _hit_invalidation(payload, bar)
        trigger_hit = _hit_trigger(payload, bar)
        target_hit = _highest_target(payload, bar)
        if (triggered or trigger_hit) and invalidation_hit and target_hit:
            add(
                "LOSS",
                bar.timestamp,
                bar.close,
                "Target and stop were touched in the same bar; conservative ordering records LOSS.",
            )
            state = "LOSS"
            break
        if not triggered and invalidation_hit:
            add(
                "INVALIDATED",
                bar.timestamp,
                bar.close,
                "Invalidation was reached before the entry trigger.",
            )
            state = "INVALIDATED"
            break
        if not triggered and trigger_hit:
            add(
                "TRIGGERED",
                bar.timestamp,
                bar.close,
                "Entry trigger became active after pattern completion.",
            )
            state = "TRIGGERED"
            triggered = True
        if triggered and invalidation_hit:
            add(
                "LOSS",
                bar.timestamp,
                bar.close,
                "Invalidation was reached after the entry trigger.",
            )
            state = "LOSS"
            break
        if triggered and target_hit:
            win_states: dict[int, LifecycleState] = {
                1: "WIN_T1",
                2: "WIN_T2",
                3: "WIN_T3",
            }
            win_state = win_states[target_hit]
            add(
                win_state,
                bar.timestamp,
                bar.close,
                f"Target {target_hit} was reached after trigger.",
            )
            state = win_state
            break

    if (
        state not in terminal
        and payload.expires_at
        and payload.as_of > payload.expires_at
    ):
        add(
            "EXPIRED",
            payload.expires_at,
            None,
            "Pattern expired before a terminal outcome.",
        )
        state = "EXPIRED"
    return HarmonicLifecycleResult(
        patternKey=payload.pattern_key,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        state=state,
        reason=transitions[-1].reason,
        transitions=transitions,
        executable=False,
    )
