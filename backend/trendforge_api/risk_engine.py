from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


READY_STATES = {"READY", "PRIORITY_RADAR_READY"}


class PositionSizingInput(BaseModel):
    account_size: float = Field(default=100_000, gt=0)
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float | None = Field(default=None, gt=0)
    confidence: int = Field(ge=0, le=100)
    candidate_state: str = "WAIT"
    source_ready: bool = False
    expected_slippage_per_unit: float = Field(default=0, ge=0)
    fees_per_unit: float = Field(default=0, ge=0)
    lot_size: int = Field(default=1, ge=1)
    liquidity_cap: int | None = Field(default=None, ge=0)
    available_margin: float | None = Field(default=None, ge=0)
    margin_per_lot: float | None = Field(default=None, gt=0)
    daily_pnl: float = 0
    open_positions: int = Field(default=0, ge=0)
    max_open_positions: int = Field(default=3, ge=1)
    exceptional_risk_allowed: bool = False
    safety_state: str = "GREEN"
    safety_risk_multiplier: float = Field(default=1, ge=0, le=1)
    total_open_risk: float = Field(default=0, ge=0)
    sector_open_risk: float = Field(default=0, ge=0)
    highest_portfolio_correlation: float = Field(default=0, ge=-1, le=1)
    correlated_open_positions: int = Field(default=0, ge=0)
    market: str = "NSE"

    @model_validator(mode="after")
    def stop_must_differ_from_entry(self) -> "PositionSizingInput":
        if self.stop == self.entry:
            raise ValueError("stop must differ from entry")
        return self


class PositionSizingResult(BaseModel):
    state: str
    executable: bool
    quantity: int
    lot_count: int
    risk_percent: float
    permitted_risk: float
    risk_per_unit: float
    max_loss: float
    reward_risk: float | None
    reasons: list[str]
    averaging_down_allowed: bool = False


class RiskSettings(BaseModel):
    account_size: float = Field(default=100_000, gt=0)
    normal_risk_percent: float = Field(default=0.005, gt=0, le=0.01)
    exceptional_risk_percent: float = Field(default=0.0075, gt=0, le=0.01)
    probe_risk_percent: float = Field(default=0.0025, gt=0, le=0.01)
    daily_soft_stop_percent: float = Field(default=0.01, gt=0, le=0.05)
    daily_hard_lock_percent: float = Field(default=0.015, gt=0, le=0.05)
    max_open_positions: int = Field(default=3, ge=1, le=20)
    max_total_open_risk_percent: float = Field(default=0.05, gt=0, le=0.10)
    max_sector_share_of_total_risk: float = Field(default=0.30, gt=0, le=1)
    correlation_threshold: float = Field(default=0.70, ge=0, le=1)
    max_correlated_full_risk_positions: int = Field(default=1, ge=0, le=10)
    max_mcx_directional_positions: int = Field(default=1, ge=1, le=10)
    max_trades_per_day: int = Field(default=5, ge=1, le=50)
    max_consecutive_losses: int = Field(default=3, ge=1, le=10)
    cooldown_after_one_loss_minutes: int = Field(default=15, ge=0, le=1440)
    cooldown_after_two_losses_minutes: int = Field(default=30, ge=0, le=1440)
    panic_lock_minutes: int = Field(default=30, ge=1, le=1440)
    averaging_down_allowed: bool = False


def confidence_risk_percent(
    confidence: int, settings: RiskSettings, *, exceptional_allowed: bool
) -> float:
    if confidence >= 90 and exceptional_allowed:
        return settings.exceptional_risk_percent
    if confidence >= 80:
        return settings.normal_risk_percent
    if confidence >= 70:
        return settings.probe_risk_percent
    return 0.0


def calculate_position_size(
    payload: PositionSizingInput, *, settings: RiskSettings | None = None
) -> PositionSizingResult:
    """Return research risk geometry without an executable quantity.

    File A postpones product sizing and the project forbids executable quantity
    recommendations. The legacy response shape remains for compatibility, but
    quantity and lot_count are always zero and executable is always false.
    """

    _ = settings
    risk_per_unit = (
        abs(payload.entry - payload.stop)
        + payload.expected_slippage_per_unit
        + payload.fees_per_unit
    )
    reward_risk = None
    if payload.target is not None and risk_per_unit > 0:
        reward_risk = abs(payload.target - payload.entry) / risk_per_unit
    if payload.safety_state not in {"GREEN", "RISK_REDUCED"}:
        return PositionSizingResult(
            state=payload.safety_state,
            executable=False,
            quantity=0,
            lot_count=0,
            risk_percent=0.0,
            permitted_risk=0.0,
            risk_per_unit=round(risk_per_unit, 4),
            max_loss=0.0,
            reward_risk=round(reward_risk, 3) if reward_risk is not None else None,
            reasons=[
                f"Safety state {payload.safety_state} blocks new action.",
                "Executable quantity is outside the current TrendForge product scope.",
            ],
        )
    return PositionSizingResult(
        state="POSTPONED_NO_QUANTITY",
        executable=False,
        quantity=0,
        lot_count=0,
        risk_percent=0.0,
        permitted_risk=0.0,
        risk_per_unit=round(risk_per_unit, 4),
        max_loss=0.0,
        reward_risk=round(reward_risk, 3) if reward_risk is not None else None,
        reasons=[
            "Executable quantity is outside the current TrendForge product scope.",
            "Entry, stop and target values are research geometry only; no action is permitted.",
        ],
    )


def _blocked(
    account_size: float,
    state: str,
    risk_percent: float,
    risk_per_unit: float,
    reward_risk: float | None,
    reason: str,
) -> PositionSizingResult:
    return PositionSizingResult(
        state=state,
        executable=False,
        quantity=0,
        lot_count=0,
        risk_percent=risk_percent,
        permitted_risk=round(account_size * risk_percent, 2),
        risk_per_unit=round(risk_per_unit, 4),
        max_loss=0,
        reward_risk=round(reward_risk, 3) if reward_risk is not None else None,
        reasons=[reason],
    )
