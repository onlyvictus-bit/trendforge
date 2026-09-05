from __future__ import annotations

from datetime import datetime, timedelta
from statistics import fmean
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .models import DataTrust


ContextGateOutcome = Literal["PASS", "SOFT_FAIL", "WAIT", "HARD_FAIL", "STALE"]
MarketState = Literal[
    "TRADEABLE_BULLISH",
    "TRADEABLE_BEARISH",
    "TRADEABLE_SELECTIVE",
    "RANGE",
    "NO_TRADE",
    "WAIT_DATA_WEAK",
]
RRGState = Literal["LEADING", "IMPROVING", "WEAKENING", "LAGGING"]


class MarketContextInput(BaseModel):
    as_of: datetime = Field(alias="asOf")
    source_date: datetime = Field(alias="sourceDate")
    nifty_closes: list[float] = Field(alias="niftyCloses", min_length=200)
    nifty_return_percent: float = Field(alias="niftyReturnPercent")
    india_vix: float = Field(alias="indiaVix", gt=0)
    india_vix_change_percent: float = Field(alias="indiaVixChangePercent")
    advances: int = Field(ge=0)
    declines: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    trust_level: DataTrust = Field(alias="trustLevel")
    max_age_hours: int = Field(default=36, alias="maxAgeHours", ge=1, le=168)

    model_config = {"populate_by_name": True, "extra": "forbid"}

    @field_validator("nifty_closes")
    @classmethod
    def prices_are_positive(cls, values: list[float]) -> list[float]:
        if any(value <= 0 for value in values):
            raise ValueError("niftyCloses must contain only positive values")
        return values

    @model_validator(mode="after")
    def timestamps_are_aware(self) -> "MarketContextInput":
        if self.as_of.utcoffset() is None or self.source_date.utcoffset() is None:
            raise ValueError("market context timestamps must include timezone")
        if self.advances + self.declines + self.unchanged <= 0:
            raise ValueError("breadth counts cannot all be zero")
        return self


class MarketContextResult(BaseModel):
    state: MarketState
    gate_outcome: ContextGateOutcome = Field(alias="gateOutcome")
    trend_state: str = Field(alias="trendState")
    vix_state: str = Field(alias="vixState")
    breadth_state: str = Field(alias="breadthState")
    breadth_ratio: float = Field(alias="breadthRatio")
    narrow_index_divergence: bool = Field(alias="narrowIndexDivergence")
    allow_long: bool = Field(alias="allowLong")
    allow_short: bool = Field(alias="allowShort")
    close: float
    dma20: float
    dma50: float
    dma200: float
    india_vix: float = Field(alias="indiaVix")
    reason: str
    source_date: datetime = Field(alias="sourceDate")
    as_of: datetime = Field(alias="asOf")
    trust_level: DataTrust = Field(alias="trustLevel")
    executable: Literal[False] = False

    model_config = {"populate_by_name": True}


class SectorContextInput(BaseModel):
    sector: str = Field(min_length=2, max_length=120)
    direction: Literal["LONG", "SHORT"]
    as_of: datetime = Field(alias="asOf")
    source_date: datetime = Field(alias="sourceDate")
    sector_closes: list[float] = Field(alias="sectorCloses", min_length=60)
    benchmark_closes: list[float] = Field(alias="benchmarkCloses", min_length=60)
    trust_level: DataTrust = Field(alias="trustLevel")
    verified_catalyst_override: bool = Field(
        default=False, alias="verifiedCatalystOverride"
    )
    max_age_hours: int = Field(default=36, alias="maxAgeHours", ge=1, le=168)

    model_config = {"populate_by_name": True, "extra": "forbid"}

    @model_validator(mode="after")
    def validate_series(self) -> "SectorContextInput":
        if self.as_of.utcoffset() is None or self.source_date.utcoffset() is None:
            raise ValueError("sector context timestamps must include timezone")
        if len(self.sector_closes) != len(self.benchmark_closes):
            raise ValueError("sector and benchmark series must have equal length")
        if any(value <= 0 for value in self.sector_closes + self.benchmark_closes):
            raise ValueError("sector context prices must be positive")
        return self


class SectorContextResult(BaseModel):
    sector: str
    direction: str
    rrg_state: RRGState = Field(alias="rrgState")
    gate_outcome: ContextGateOutcome = Field(alias="gateOutcome")
    relative_strength_index: float = Field(alias="relativeStrengthIndex")
    relative_momentum: float = Field(alias="relativeMomentum")
    verified_catalyst_override: bool = Field(alias="verifiedCatalystOverride")
    reason: str
    source_date: datetime = Field(alias="sourceDate")
    as_of: datetime = Field(alias="asOf")
    trust_level: DataTrust = Field(alias="trustLevel")
    executable: Literal[False] = False

    model_config = {"populate_by_name": True}


def _mean_tail(values: list[float], count: int) -> float:
    return fmean(values[-count:])


def evaluate_market_context(payload: MarketContextInput) -> MarketContextResult:
    close = payload.nifty_closes[-1]
    dma20 = _mean_tail(payload.nifty_closes, 20)
    dma50 = _mean_tail(payload.nifty_closes, 50)
    dma200 = _mean_tail(payload.nifty_closes, 200)
    breadth_ratio = (
        payload.advances / payload.declines
        if payload.declines > 0
        else float(payload.advances)
    )
    breadth_state = (
        "DANGER"
        if breadth_ratio < 1 / 3
        else "WEAK"
        if breadth_ratio < 1
        else "HEALTHY"
        if breadth_ratio >= 1.5
        else "BALANCED"
    )
    vix_state = (
        "LOW"
        if payload.india_vix < 12
        else "NORMAL"
        if payload.india_vix < 15
        else "ELEVATED"
        if payload.india_vix < 20
        else "HIGH"
        if payload.india_vix < 25
        else "EXTREME"
    )
    if close > dma20 > dma50 > dma200:
        trend_state = "STRONG_UPTREND"
    elif close > dma50 > dma200:
        trend_state = "UPTREND"
    elif close < dma20 < dma50 < dma200:
        trend_state = "STRONG_DOWNTREND"
    elif close < dma50 < dma200:
        trend_state = "DOWNTREND"
    else:
        trend_state = "RANGE"
    narrow = payload.nifty_return_percent > 0 and breadth_ratio < 1

    state: MarketState
    if payload.source_date > payload.as_of:
        state = "WAIT_DATA_WEAK"
        outcome: ContextGateOutcome = "HARD_FAIL"
        reason = "Market context violates point-in-time ordering; source data is from the future."
    elif payload.as_of - payload.source_date > timedelta(hours=payload.max_age_hours):
        state = "WAIT_DATA_WEAK"
        outcome = "STALE"
        reason = "Market context is older than its configured freshness window."
    elif (
        payload.india_vix_change_percent >= 30
        or vix_state == "EXTREME"
        or breadth_state == "DANGER"
    ):
        state = "NO_TRADE"
        outcome = "HARD_FAIL"
        reason = (
            "VIX shock/extreme volatility or breadth below 1:3 blocks fresh entries."
        )
    elif narrow:
        state = "TRADEABLE_SELECTIVE"
        outcome = "SOFT_FAIL"
        reason = "Nifty is positive while breadth is weak; low-quality breakouts are blocked."
    elif trend_state in {"STRONG_UPTREND", "UPTREND"} and payload.india_vix < 20:
        state = "TRADEABLE_BULLISH"
        outcome = "PASS"
        reason = "Trend, VIX and breadth permit selective long strategies."
    elif trend_state in {"STRONG_DOWNTREND", "DOWNTREND"}:
        state = "TRADEABLE_BEARISH"
        outcome = "PASS"
        reason = (
            "Downtrend regime permits only directionally aligned bearish strategies."
        )
    else:
        state = "RANGE"
        outcome = "SOFT_FAIL"
        reason = "Market structure is range-bound; breakout strategies require extra confirmation."
    return MarketContextResult(
        state=state,
        gateOutcome=outcome,
        trendState=trend_state,
        vixState=vix_state,
        breadthState=breadth_state,
        breadthRatio=round(breadth_ratio, 4),
        narrowIndexDivergence=narrow,
        allowLong=state in {"TRADEABLE_BULLISH", "TRADEABLE_SELECTIVE", "RANGE"},
        allowShort=state in {"TRADEABLE_BEARISH", "TRADEABLE_SELECTIVE", "RANGE"},
        close=round(close, 4),
        dma20=round(dma20, 4),
        dma50=round(dma50, 4),
        dma200=round(dma200, 4),
        indiaVix=payload.india_vix,
        reason=reason,
        sourceDate=payload.source_date,
        asOf=payload.as_of,
        trustLevel=payload.trust_level,
    )


def evaluate_sector_context(payload: SectorContextInput) -> SectorContextResult:
    ratios = [
        sector / benchmark
        for sector, benchmark in zip(
            payload.sector_closes, payload.benchmark_closes, strict=True
        )
    ]
    relative_strength = ratios[-1] / fmean(ratios)
    relative_momentum = ratios[-1] / ratios[-10] - 1
    strong = relative_strength >= 1
    improving = relative_momentum > 0
    rrg_state: RRGState = (
        "LEADING"
        if strong and improving
        else "IMPROVING"
        if not strong and improving
        else "WEAKENING"
        if strong
        else "LAGGING"
    )
    aligned = (
        payload.direction == "LONG" and rrg_state in {"LEADING", "IMPROVING"}
    ) or (payload.direction == "SHORT" and rrg_state in {"LAGGING", "WEAKENING"})
    if payload.source_date > payload.as_of:
        outcome: ContextGateOutcome = "HARD_FAIL"
        reason = "Sector context violates point-in-time ordering."
    elif payload.as_of - payload.source_date > timedelta(hours=payload.max_age_hours):
        outcome = "STALE"
        reason = "Sector context is older than its freshness window."
    elif aligned:
        outcome = "PASS"
        reason = (
            f"{payload.direction} direction aligns with {rrg_state} sector rotation."
        )
    elif payload.verified_catalyst_override:
        outcome = "SOFT_FAIL"
        reason = (
            f"Verified stock-specific catalyst partially overrides {rrg_state} sector conflict; "
            "position aggression must remain reduced."
        )
    elif rrg_state in {"LAGGING", "LEADING"}:
        outcome = "HARD_FAIL"
        reason = (
            f"{payload.direction} direction conflicts with {rrg_state} sector rotation."
        )
    else:
        outcome = "SOFT_FAIL"
        reason = f"{payload.direction} direction has weakening sector alignment."
    return SectorContextResult(
        sector=payload.sector,
        direction=payload.direction,
        rrgState=rrg_state,
        gateOutcome=outcome,
        relativeStrengthIndex=round(relative_strength, 6),
        relativeMomentum=round(relative_momentum, 6),
        verifiedCatalystOverride=payload.verified_catalyst_override,
        reason=reason,
        sourceDate=payload.source_date,
        asOf=payload.as_of,
        trustLevel=payload.trust_level,
    )
