from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, model_validator

from . import storage
from .records import AlertCreate
from .risk_engine import RiskSettings


IST = ZoneInfo("Asia/Kolkata")
SafetyState = Literal[
    "GREEN",
    "RISK_REDUCED",
    "COOLDOWN_ACTIVE",
    "WAIT_EMOTIONAL_RISK",
    "LOCKED_NO_TRADE",
    "STOP_TRADING_NOW",
    "BROKER_DATA_TRAUMA",
]
LOCKING_STATES = {"LOCKED_NO_TRADE", "STOP_TRADING_NOW", "BROKER_DATA_TRAUMA"}


class SafetyStatus(BaseModel):
    state: SafetyState
    locked: bool
    risk_multiplier: float = Field(alias="riskMultiplier", ge=0, le=1)
    daily_realized_pnl: float = Field(alias="dailyRealizedPnl")
    consecutive_losses: int = Field(alias="consecutiveLosses", ge=0)
    trades_today: int = Field(alias="tradesToday", ge=0)
    cooldown_until: datetime | None = Field(default=None, alias="cooldownUntil")
    reason: str
    next_allowed_action: str = Field(alias="nextAllowedAction")
    active_event_ids: list[int] = Field(default_factory=list, alias="activeEventIds")
    as_of: datetime = Field(alias="asOf")
    executable: Literal[False] = False

    model_config = {"populate_by_name": True}


class PanicLockRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    cooldown_minutes: int | None = Field(
        default=None, alias="cooldownMinutes", ge=1, le=1440
    )

    model_config = {"populate_by_name": True, "extra": "forbid"}


class RecoveryUnlockRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    recovery_checklist: list[bool] = Field(alias="recoveryChecklist")

    model_config = {"populate_by_name": True, "extra": "forbid"}

    @model_validator(mode="after")
    def complete_checklist_required(self) -> "RecoveryUnlockRequest":
        if len(self.recovery_checklist) != 5 or not all(self.recovery_checklist):
            raise ValueError("all five recovery checklist items must be accepted")
        return self


def _aware(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.utcoffset() is None:
        raise ValueError("safety evaluation timestamp must be timezone-aware")
    return current


def _journal_snapshot(as_of: datetime) -> tuple[list, list]:
    entries = storage.list_journal_entries(limit=5000)
    as_of_ist = as_of.astimezone(IST)
    today = []
    closed = []
    for row in entries:
        if (
            row.opened_at <= as_of
            and row.opened_at.astimezone(IST).date() == as_of_ist.date()
        ):
            today.append(row)
        if (
            row.closed_at is not None
            and row.closed_at <= as_of
            and row.closed_at.astimezone(IST).date() == as_of_ist.date()
        ):
            closed.append(row)
    closed.sort(key=lambda item: (item.closed_at, item.id))
    return today, closed


def _trailing_losses(closed: list) -> int:
    count = 0
    for row in reversed(closed):
        if row.outcome_state == "LOSS" or (row.pnl is not None and row.pnl < 0):
            count += 1
        else:
            break
    return count


def _active_manual_events(as_of: datetime) -> list[dict]:
    return [
        row
        for row in storage.list_safety_events(active=True, limit=100)
        if datetime.fromisoformat(row["created_at"]) <= as_of
    ]


def evaluate_safety_status(
    *, as_of: datetime | None = None, settings: RiskSettings | None = None
) -> SafetyStatus:
    current = _aware(as_of)
    settings = settings or storage.get_risk_settings()
    today, closed = _journal_snapshot(current)
    daily_pnl = round(sum(float(row.pnl or 0) for row in closed), 2)
    consecutive_losses = _trailing_losses(closed)
    active_events = _active_manual_events(current)
    locking = [row for row in active_events if row["state"] in LOCKING_STATES]
    if locking:
        latest = max(locking, key=lambda row: (row["created_at"], row["id"]))
        cooldown = (
            datetime.fromisoformat(latest["cooldown_until"])
            if latest.get("cooldown_until")
            else None
        )
        return _status(
            state=latest["state"],
            risk_multiplier=0,
            daily_pnl=daily_pnl,
            consecutive_losses=consecutive_losses,
            trades_today=len(today),
            cooldown_until=cooldown,
            reason=latest["reason"],
            next_action=latest["next_allowed_action"],
            active_event_ids=[int(row["id"]) for row in locking],
            as_of=current,
        )

    hard_loss = settings.account_size * settings.daily_hard_lock_percent
    if daily_pnl <= -hard_loss or consecutive_losses >= settings.max_consecutive_losses:
        reason = (
            "Daily hard-loss threshold reached."
            if daily_pnl <= -hard_loss
            else f"{consecutive_losses} consecutive losses reached the configured lock."
        )
        return _status(
            state="LOCKED_NO_TRADE",
            risk_multiplier=0,
            daily_pnl=daily_pnl,
            consecutive_losses=consecutive_losses,
            trades_today=len(today),
            reason=reason,
            next_action="Monitor only; reassess in the next valid trading session.",
            as_of=current,
        )

    latest_loss = next(
        (
            row
            for row in reversed(closed)
            if row.outcome_state == "LOSS" or (row.pnl is not None and row.pnl < 0)
        ),
        None,
    )
    cooldown_until = None
    if latest_loss and latest_loss.closed_at:
        minutes = (
            settings.cooldown_after_two_losses_minutes
            if consecutive_losses >= 2
            else settings.cooldown_after_one_loss_minutes
        )
        cooldown_until = latest_loss.closed_at + timedelta(minutes=minutes)
    if cooldown_until and current < cooldown_until:
        return _status(
            state="COOLDOWN_ACTIVE",
            risk_multiplier=0,
            daily_pnl=daily_pnl,
            consecutive_losses=consecutive_losses,
            trades_today=len(today),
            cooldown_until=cooldown_until,
            reason=f"Post-loss cooldown is active after {consecutive_losses} consecutive loss(es).",
            next_action="Wait for the timer, then require a fresh setup and recovery review.",
            as_of=current,
        )

    if len(today) >= settings.max_trades_per_day:
        return _status(
            state="WAIT_EMOTIONAL_RISK",
            risk_multiplier=0,
            daily_pnl=daily_pnl,
            consecutive_losses=consecutive_losses,
            trades_today=len(today),
            reason="Maximum configured trades for this session has been reached.",
            next_action="Do not open another position in this session.",
            as_of=current,
        )

    soft_loss = settings.account_size * settings.daily_soft_stop_percent
    if daily_pnl <= -soft_loss:
        return _status(
            state="RISK_REDUCED",
            risk_multiplier=0.5,
            daily_pnl=daily_pnl,
            consecutive_losses=consecutive_losses,
            trades_today=len(today),
            reason="Daily soft-loss threshold reached; new risk is reduced by 50%.",
            next_action="Use only a fresh confirmed setup at reduced risk.",
            as_of=current,
        )

    return _status(
        state="GREEN",
        risk_multiplier=1,
        daily_pnl=daily_pnl,
        consecutive_losses=consecutive_losses,
        trades_today=len(today),
        reason="No persisted account or emotional safety rule is currently active.",
        next_action="Normal guarded research workflow may continue.",
        as_of=current,
    )


def _status(
    *,
    state: SafetyState,
    risk_multiplier: float,
    daily_pnl: float,
    consecutive_losses: int,
    trades_today: int,
    reason: str,
    next_action: str,
    as_of: datetime,
    cooldown_until: datetime | None = None,
    active_event_ids: list[int] | None = None,
) -> SafetyStatus:
    return SafetyStatus(
        state=state,
        locked=state in LOCKING_STATES,
        riskMultiplier=risk_multiplier,
        dailyRealizedPnl=daily_pnl,
        consecutiveLosses=consecutive_losses,
        tradesToday=trades_today,
        cooldownUntil=cooldown_until,
        reason=reason,
        nextAllowedAction=next_action,
        activeEventIds=active_event_ids or [],
        asOf=as_of,
    )


def activate_panic_lock(
    payload: PanicLockRequest, *, now: datetime | None = None
) -> SafetyStatus:
    current = _aware(now)
    settings = storage.get_risk_settings()
    minutes = payload.cooldown_minutes or settings.panic_lock_minutes
    cooldown_until = current + timedelta(minutes=minutes)
    event_id = storage.create_safety_event(
        event_type="MANUAL_PANIC_LOCK",
        state="LOCKED_NO_TRADE",
        reason=payload.reason,
        system_action="Block all new entries; keep monitoring and risk reduction visible.",
        next_allowed_action="Complete cooldown and all recovery checklist items.",
        cooldown_until=cooldown_until.isoformat(),
        created_at=current.isoformat(),
        active=True,
    )
    storage.save_general_alert(
        AlertCreate(
            alertType="SAFETY_LOCK",
            severity="CRITICAL",
            state="LOCKED_NO_TRADE",
            reason=payload.reason,
            risk={"eventId": event_id, "cooldownUntil": cooldown_until.isoformat()},
        )
    )
    return evaluate_safety_status(as_of=current, settings=settings)


def recover_from_manual_lock(
    payload: RecoveryUnlockRequest, *, now: datetime | None = None
) -> SafetyStatus:
    current = _aware(now)
    active = _active_manual_events(current)
    locks = [row for row in active if row["state"] in LOCKING_STATES]
    if locks:
        future_cooldowns = [
            datetime.fromisoformat(row["cooldown_until"])
            for row in locks
            if row.get("cooldown_until")
            and datetime.fromisoformat(row["cooldown_until"]) > current
        ]
        if future_cooldowns:
            raise RuntimeError(
                f"manual safety cooldown remains active until {max(future_cooldowns).isoformat()}"
            )
        for row in locks:
            storage.resolve_safety_event(
                int(row["id"]), resolved_at=current.isoformat()
            )
        storage.create_safety_event(
            event_type="RECOVERY_UNLOCK",
            state="GREEN",
            reason=payload.reason,
            system_action="Manual lock released after deterministic recovery checklist.",
            next_allowed_action="Only a fresh TrendForge-confirmed setup may proceed.",
            created_at=current.isoformat(),
            active=False,
            metadata={"resolvedEventIds": [int(row["id"]) for row in locks]},
        )
    return evaluate_safety_status(as_of=current, settings=storage.get_risk_settings())
