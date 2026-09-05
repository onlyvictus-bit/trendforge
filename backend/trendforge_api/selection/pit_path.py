"""Deterministic point-in-time path evidence for Q5-R6 validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .contracts import MODEL_CONFIG, stable_id


class PITDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class PITBarObservation(BaseModel):
    """One immutable closed bar and the time it became usable."""

    model_config = MODEL_CONFIG

    bar_id: str = Field(min_length=1)
    close_time: datetime
    available_at: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    raw_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    is_closed: Literal[True] = True

    @field_validator("close_time", "available_at")
    @classmethod
    def require_timezone(cls, value: datetime, info) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{info.field_name} must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_bar(self) -> "PITBarObservation":
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("PIT bar high is below an OHLC value")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("PIT bar low is above an OHLC value")
        if self.available_at < self.close_time:
            raise ValueError("closed PIT bar cannot be available before close")
        expected = stable_id(
            "pitbar",
            self.close_time,
            self.open,
            self.high,
            self.low,
            self.close,
            self.raw_hash,
        )
        if self.bar_id != expected:
            raise ValueError("PIT bar identity does not match immutable inputs")
        return self

    @classmethod
    def create(
        cls,
        *,
        close_time: datetime,
        available_at: datetime,
        open: float,
        high: float,
        low: float,
        close: float,
        raw_hash: str,
    ) -> "PITBarObservation":
        normalized_hash = raw_hash.lower()
        return cls(
            bar_id=stable_id(
                "pitbar",
                close_time,
                open,
                high,
                low,
                close,
                normalized_hash,
            ),
            close_time=close_time,
            available_at=available_at,
            open=open,
            high=high,
            low=low,
            close=close,
            raw_hash=normalized_hash,
        )


class PITPathEvidence(BaseModel):
    """Versioned raw inputs from which an outcome is derived."""

    model_config = MODEL_CONFIG

    evidence_id: str = Field(min_length=1)
    calculation_version: Literal["pit-path-1"] = "pit-path-1"
    direction: PITDirection
    entry_at: datetime | None = None
    entry_price: float | None = Field(default=None, gt=0)
    target_price: float | None = Field(default=None, gt=0)
    stop_price: float | None = Field(default=None, gt=0)
    bars: tuple[PITBarObservation, ...] = Field(min_length=1)
    source_artifact_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_event: Literal[
        "NONE",
        "INVALIDATED_BEFORE_ENTRY",
        "DELISTED_OR_UNPRICED",
        "DATA_INCOMPLETE",
    ] = "NONE"
    terminal_event_at: datetime | None = None
    terminal_event_available_at: datetime | None = None
    terminal_event_artifact_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )

    @field_validator("entry_at", "terminal_event_at", "terminal_event_available_at")
    @classmethod
    def require_optional_timezone(
        cls,
        value: datetime | None,
        info,
    ) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError(f"{info.field_name} must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_path(self) -> "PITPathEvidence":
        close_times = tuple(bar.close_time for bar in self.bars)
        if close_times != tuple(sorted(close_times)):
            raise ValueError("PIT bars must be sorted by close time")
        if len(close_times) != len(set(close_times)):
            raise ValueError("PIT bars must have unique close times")

        price_fields = (self.entry_price, self.target_price, self.stop_price)
        if self.entry_at is None and any(value is not None for value in price_fields):
            raise ValueError(
                "non-entry path cannot carry entry, target, or stop prices"
            )
        if self.entry_at is not None:
            if any(value is None for value in price_fields):
                raise ValueError("entered path requires entry, target, and stop prices")
            assert self.entry_price is not None
            assert self.target_price is not None
            assert self.stop_price is not None
            if self.direction is PITDirection.LONG and not (
                self.stop_price < self.entry_price < self.target_price
            ):
                raise ValueError("LONG path requires stop < entry < target")
            if self.direction is PITDirection.SHORT and not (
                self.target_price < self.entry_price < self.stop_price
            ):
                raise ValueError("SHORT path requires target < entry < stop")

        event_fields = (
            self.terminal_event_at,
            self.terminal_event_available_at,
            self.terminal_event_artifact_hash,
        )
        if self.terminal_event == "NONE" and any(
            value is not None for value in event_fields
        ):
            raise ValueError("NONE terminal event cannot carry event lineage")
        if self.terminal_event != "NONE" and any(
            value is None for value in event_fields
        ):
            raise ValueError(
                "terminal event requires time, availability, and artifact hash"
            )
        if (
            self.terminal_event_at is not None
            and self.terminal_event_available_at is not None
            and self.terminal_event_available_at < self.terminal_event_at
        ):
            raise ValueError("terminal event cannot be available before occurrence")

        expected = stable_id(
            "pitpath",
            self.calculation_version,
            self.direction,
            self.entry_at,
            self.entry_price,
            self.target_price,
            self.stop_price,
            tuple(bar.bar_id for bar in self.bars),
            self.source_artifact_hash,
            self.terminal_event,
            self.terminal_event_at,
            self.terminal_event_available_at,
            self.terminal_event_artifact_hash,
        )
        if self.evidence_id != expected:
            raise ValueError("PIT path identity does not match immutable inputs")
        return self

    @classmethod
    def create(
        cls,
        *,
        direction: PITDirection,
        bars: tuple[PITBarObservation, ...],
        source_artifact_hash: str,
        entry_at: datetime | None = None,
        entry_price: float | None = None,
        target_price: float | None = None,
        stop_price: float | None = None,
        terminal_event: Literal[
            "NONE",
            "INVALIDATED_BEFORE_ENTRY",
            "DELISTED_OR_UNPRICED",
            "DATA_INCOMPLETE",
        ] = "NONE",
        terminal_event_at: datetime | None = None,
        terminal_event_available_at: datetime | None = None,
        terminal_event_artifact_hash: str | None = None,
    ) -> "PITPathEvidence":
        normalized_source_hash = source_artifact_hash.lower()
        normalized_event_hash = (
            terminal_event_artifact_hash.lower()
            if terminal_event_artifact_hash is not None
            else None
        )
        evidence_id = stable_id(
            "pitpath",
            "pit-path-1",
            direction,
            entry_at,
            entry_price,
            target_price,
            stop_price,
            tuple(bar.bar_id for bar in bars),
            normalized_source_hash,
            terminal_event,
            terminal_event_at,
            terminal_event_available_at,
            normalized_event_hash,
        )
        return cls(
            evidence_id=evidence_id,
            direction=direction,
            entry_at=entry_at,
            entry_price=entry_price,
            target_price=target_price,
            stop_price=stop_price,
            bars=bars,
            source_artifact_hash=normalized_source_hash,
            terminal_event=terminal_event,
            terminal_event_at=terminal_event_at,
            terminal_event_available_at=terminal_event_available_at,
            terminal_event_artifact_hash=normalized_event_hash,
        )


@dataclass(frozen=True)
class DerivedPITPath:
    label: str
    gross_return: float
    mfe: float | None
    mae: float | None
    outcome_available_at: datetime
    entered: bool


def derive_pit_path(
    path: PITPathEvidence,
    *,
    decision_at: datetime,
    horizon_end: datetime,
    cutoff_at: datetime,
) -> DerivedPITPath:
    """Derive a conservative target/stop/censored path from immutable bars."""

    if path.terminal_event != "NONE":
        if path.terminal_event_at != cutoff_at:
            raise ValueError("terminal-event cutoff must equal event time")
        assert path.terminal_event_available_at is not None
        return DerivedPITPath(
            label=path.terminal_event,
            gross_return=0.0,
            mfe=None,
            mae=None,
            outcome_available_at=path.terminal_event_available_at,
            entered=path.entry_at is not None,
        )

    eligible = tuple(
        bar for bar in path.bars if decision_at < bar.close_time <= cutoff_at
    )
    if not eligible:
        raise ValueError("PIT path has no closed bars in its observation window")

    if path.entry_at is None:
        if cutoff_at != horizon_end or eligible[-1].close_time != horizon_end:
            raise ValueError("NO_ENTRY path must be observed through horizon end")
        return DerivedPITPath(
            label="NO_ENTRY",
            gross_return=0.0,
            mfe=None,
            mae=None,
            outcome_available_at=eligible[-1].available_at,
            entered=False,
        )

    if not decision_at < path.entry_at <= cutoff_at:
        raise ValueError("entry time must follow decision and precede cutoff")
    assert path.entry_price is not None
    assert path.target_price is not None
    assert path.stop_price is not None
    bars = tuple(bar for bar in eligible if bar.close_time >= path.entry_at)
    if not bars:
        raise ValueError("entered PIT path has no closed bars after entry")

    mfe = 0.0
    mae = 0.0
    label: str | None = None
    terminal_bar = bars[-1]
    for bar in bars:
        if path.direction is PITDirection.LONG:
            mfe = max(mfe, (bar.high - path.entry_price) / path.entry_price)
            mae = min(mae, (bar.low - path.entry_price) / path.entry_price)
            target_hit = bar.high >= path.target_price
            stop_hit = bar.low <= path.stop_price
        else:
            mfe = max(mfe, (path.entry_price - bar.low) / path.entry_price)
            mae = min(mae, (path.entry_price - bar.high) / path.entry_price)
            target_hit = bar.low <= path.target_price
            stop_hit = bar.high >= path.stop_price

        if target_hit and stop_hit:
            label = "SAME_BAR_STOP_FIRST"
        elif stop_hit:
            label = "STOP_FIRST"
        elif target_hit:
            label = "TARGET_FIRST"
        if label is not None:
            terminal_bar = bar
            break

    if label is None:
        if cutoff_at != horizon_end:
            raise ValueError("unresolved path must remain censored through horizon")
        label = "HORIZON_CENSORED"
        terminal_price = terminal_bar.close
    elif label == "TARGET_FIRST":
        terminal_price = path.target_price
    else:
        terminal_price = path.stop_price

    if terminal_bar.close_time != cutoff_at:
        raise ValueError("PIT cutoff must equal terminal closed-bar time")
    if path.direction is PITDirection.LONG:
        gross_return = (terminal_price - path.entry_price) / path.entry_price
    else:
        gross_return = (path.entry_price - terminal_price) / path.entry_price

    return DerivedPITPath(
        label=label,
        gross_return=round(gross_return, 8),
        mfe=round(mfe, 8),
        mae=round(mae, 8),
        outcome_available_at=terminal_bar.available_at,
        entered=True,
    )
