from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from .institutional_ai import blend_probabilities
from .institutional_config import InstitutionalConfig, load_institutional_config
from .risk_engine import PositionSizingInput, RiskSettings, calculate_position_size


FACTOR_KEYS = (
    "smart_money",
    "trend",
    "volatility",
    "momentum",
    "fundamental",
    "risk",
)


class InstitutionalModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FactorSnapshot(InstitutionalModel):
    smart_money: float | None = Field(default=None, ge=-3, le=3)
    trend: float | None = Field(default=None, ge=-3, le=3)
    volatility: float | None = Field(default=None, ge=-3, le=3)
    momentum: float | None = Field(default=None, ge=-3, le=3)
    fundamental: float | None = Field(default=None, ge=-3, le=3)
    risk: float | None = Field(default=None, ge=-3, le=3)


class HardFilterSnapshot(InstitutionalModel):
    asm: bool = False
    gsm: bool = False
    pledge_percent: float | None = Field(default=None, ge=0, le=100)
    traded_value_lacs: float | None = Field(default=None, ge=0)
    earnings_within_hours: float | None = Field(default=None, ge=0)
    material_event_pending: bool = False


class InstitutionalAnalysisRequest(InstitutionalModel):
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Z0-9&_.-]+$")
    as_of: datetime
    timeframe: str = "1D"
    market: str = "NSE"
    factors: FactorSnapshot
    hard_filters: HardFilterSnapshot = Field(default_factory=HardFilterSnapshot)
    source_ready: bool = False
    models_ready: bool = False
    anomaly_state: Literal["CLEAR", "ANOMALY", "UNKNOWN"] = "UNKNOWN"
    model_probabilities: dict[str, float] = Field(default_factory=dict)
    entry: float | None = Field(default=None, gt=0)
    stop: float | None = Field(default=None, gt=0)
    target: float | None = Field(default=None, gt=0)
    highest_portfolio_correlation: float = Field(default=0, ge=-1, le=1)
    open_positions: int = Field(default=0, ge=0)
    daily_pnl: float = 0

    @field_validator("as_of")
    @classmethod
    def as_of_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class InstitutionalAnalysisResult(InstitutionalModel):
    symbol: str
    as_of: datetime
    timeframe: str
    market: str
    classification: str
    state: str
    executable: bool = False
    factor_score: float
    bayesian_probability: float
    bull_probability: float
    confidence: int = Field(ge=0, le=100)
    factor_contributions: dict[str, float]
    missing_factors: list[str]
    suggested_quantity: int = Field(ge=0)
    max_loss: float = Field(ge=0)
    reward_risk: float | None = None
    reasons: list[str]
    model_probabilities: dict[str, float]


def _hard_filter_reasons(
    filters: HardFilterSnapshot, config: InstitutionalConfig
) -> list[str]:
    reasons: list[str] = []
    if filters.gsm:
        reasons.append("GSM surveillance blocks a new trade.")
    if filters.asm:
        reasons.append("ASM surveillance blocks production readiness.")
    if (
        filters.pledge_percent is not None
        and filters.pledge_percent > config.screening.max_pledge_pct
    ):
        reasons.append(
            f"Promoter pledge {filters.pledge_percent:.1f}% exceeds the configured limit."
        )
    if (
        filters.traded_value_lacs is not None
        and filters.traded_value_lacs < config.screening.min_volume_lacs
    ):
        reasons.append("Traded value is below the configured liquidity floor.")
    if (
        filters.earnings_within_hours is not None
        and filters.earnings_within_hours <= 48
    ):
        reasons.append("Financial results are within 48 hours.")
    if filters.material_event_pending:
        reasons.append("A material event is pending or unresolved.")
    return reasons


def _blocked_result(
    request: InstitutionalAnalysisRequest,
    *,
    classification: str,
    state: str,
    score: float,
    bayesian_probability: float,
    bull_probability: float,
    contributions: dict[str, float],
    missing: list[str],
    reasons: list[str],
) -> InstitutionalAnalysisResult:
    return InstitutionalAnalysisResult(
        symbol=request.symbol,
        as_of=request.as_of,
        timeframe=request.timeframe,
        market=request.market,
        classification=classification,
        state=state,
        factor_score=score,
        bayesian_probability=bayesian_probability,
        bull_probability=bull_probability,
        confidence=round(100 * max(bull_probability, 1 - bull_probability)),
        factor_contributions=contributions,
        missing_factors=missing,
        suggested_quantity=0,
        max_loss=0,
        reasons=reasons,
        model_probabilities=request.model_probabilities,
    )


def analyze_institutional(
    request: InstitutionalAnalysisRequest,
    *,
    config: InstitutionalConfig | None = None,
) -> InstitutionalAnalysisResult:
    config = config or load_institutional_config()
    factor_values = request.factors.model_dump()
    missing = sorted(key for key in FACTOR_KEYS if factor_values[key] is None)
    weights = config.weights.model_dump()
    contributions = {
        key: float(factor_values[key]) * weights[key]
        for key in FACTOR_KEYS
        if factor_values[key] is not None
    }
    score = sum(contributions.values())
    bayesian_probability = 1 / (1 + math.exp(-(score * config.ai.probability_slope)))
    bull_probability = bayesian_probability
    hard_reasons = _hard_filter_reasons(request.hard_filters, config)
    if hard_reasons:
        return _blocked_result(
            request,
            classification="NO_TRADE",
            state="REJECT_HARD_FILTER",
            score=score,
            bayesian_probability=bayesian_probability,
            bull_probability=bull_probability,
            contributions=contributions,
            missing=missing,
            reasons=hard_reasons,
        )
    coverage = (len(FACTOR_KEYS) - len(missing)) / len(FACTOR_KEYS)
    if missing or coverage < config.screening.min_factor_coverage:
        return _blocked_result(
            request,
            classification="WATCHLIST",
            state="WAIT_DATA_WEAK",
            score=score,
            bayesian_probability=bayesian_probability,
            bull_probability=bull_probability,
            contributions=contributions,
            missing=missing,
            reasons=["Required factor evidence is incomplete."],
        )
    if not request.source_ready:
        return _blocked_result(
            request,
            classification="WATCHLIST",
            state="WAIT_SOURCE_STRUCTURED_PENDING",
            score=score,
            bayesian_probability=bayesian_probability,
            bull_probability=bull_probability,
            contributions=contributions,
            missing=missing,
            reasons=["Required official or licensed source evidence is not ready."],
        )
    if request.anomaly_state != "CLEAR":
        reason = (
            "Isolation Forest marked the observation as anomalous."
            if request.anomaly_state == "ANOMALY"
            else "Isolation Forest has not evaluated this observation."
        )
        return _blocked_result(
            request,
            classification="WATCHLIST",
            state="WAIT_MODEL_ANOMALY",
            score=score,
            bayesian_probability=bayesian_probability,
            bull_probability=bull_probability,
            contributions=contributions,
            missing=missing,
            reasons=[reason],
        )
    if not request.models_ready:
        return _blocked_result(
            request,
            classification="WATCHLIST",
            state="WAIT_MODEL_UNTRAINED",
            score=score,
            bayesian_probability=bayesian_probability,
            bull_probability=bull_probability,
            contributions=contributions,
            missing=missing,
            reasons=["Configured AI ensemble is untrained or unavailable."],
        )
    required_models = set(config.ai.ensemble_weights)
    blended = blend_probabilities(
        probabilities=request.model_probabilities,
        weights=config.ai.ensemble_weights,
        required_models=required_models,
    )
    if not blended.ready or blended.probability is None:
        return _blocked_result(
            request,
            classification="WATCHLIST",
            state="WAIT_MODEL_UNTRAINED",
            score=score,
            bayesian_probability=bayesian_probability,
            bull_probability=bull_probability,
            contributions=contributions,
            missing=missing,
            reasons=[
                f"Missing model probabilities: {', '.join(blended.missing_models)}"
            ],
        )
    bull_probability = blended.probability
    probability_floor = config.screening.min_direction_probability
    if (
        score >= config.screening.bull_threshold
        and bull_probability >= probability_floor
    ):
        classification, state = "BULLISH", "WATCH"
    elif (
        score <= config.screening.bear_threshold
        and bull_probability <= 1 - probability_floor
    ):
        classification, state = "BEARISH", "WATCH"
    elif abs(score) < config.screening.neutral_zone:
        return _blocked_result(
            request,
            classification="NO_TRADE",
            state="NO_TRADE_NEUTRAL",
            score=score,
            bayesian_probability=bayesian_probability,
            bull_probability=bull_probability,
            contributions=contributions,
            missing=missing,
            reasons=["Composite score is inside the neutral zone."],
        )
    else:
        return _blocked_result(
            request,
            classification="WATCHLIST",
            state="WAIT_CONFLUENCE",
            score=score,
            bayesian_probability=bayesian_probability,
            bull_probability=bull_probability,
            contributions=contributions,
            missing=missing,
            reasons=["Factor score and ensemble probability do not fully agree."],
        )
    confidence = round(100 * max(bull_probability, 1 - bull_probability))
    if request.entry is None or request.stop is None:
        return InstitutionalAnalysisResult(
            symbol=request.symbol,
            as_of=request.as_of,
            timeframe=request.timeframe,
            market=request.market,
            classification=classification,
            state=state,
            executable=False,
            factor_score=score,
            bayesian_probability=bayesian_probability,
            bull_probability=bull_probability,
            confidence=confidence,
            factor_contributions=contributions,
            missing_factors=[],
            suggested_quantity=0,
            max_loss=0,
            reward_risk=None,
            reasons=[
                "Evidence direction is research-only; no action is authorized.",
                "Risk geometry is unavailable because entry or stop is missing.",
            ],
            model_probabilities=request.model_probabilities,
        )
    risk_result = calculate_position_size(
        PositionSizingInput(
            account_size=config.risk.account_size,
            entry=request.entry,
            stop=request.stop,
            target=request.target,
            confidence=confidence,
            candidate_state=state,
            source_ready=True,
            open_positions=request.open_positions,
            highest_portfolio_correlation=request.highest_portfolio_correlation,
            daily_pnl=request.daily_pnl,
            market=request.market,
        ),
        settings=RiskSettings(
            account_size=config.risk.account_size,
            max_open_positions=config.risk.max_open_positions,
            daily_hard_lock_percent=config.risk.max_daily_loss_pct,
            max_sector_share_of_total_risk=config.risk.max_sector_risk_share,
            correlation_threshold=config.risk.correlation_threshold,
        ),
    )
    return InstitutionalAnalysisResult(
        symbol=request.symbol,
        as_of=request.as_of,
        timeframe=request.timeframe,
        market=request.market,
        classification=classification,
        state=state,
        executable=False,
        factor_score=score,
        bayesian_probability=bayesian_probability,
        bull_probability=bull_probability,
        confidence=confidence,
        factor_contributions=contributions,
        missing_factors=[],
        suggested_quantity=risk_result.quantity,
        max_loss=risk_result.max_loss,
        reward_risk=risk_result.reward_risk,
        reasons=[
            "Evidence direction is research-only; no action is authorized.",
            *risk_result.reasons,
        ],
        model_probabilities=request.model_probabilities,
    )
