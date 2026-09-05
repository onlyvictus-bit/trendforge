from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class AlertCreate(BaseModel):
    alert_type: str = Field(alias="alertType", min_length=1, max_length=80)
    severity: Literal["INFO", "WARN", "CRITICAL"]
    symbol: str | None = Field(default=None, max_length=32)
    state: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=2000)
    risk: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True, "extra": "forbid"}


class AlertRecord(AlertCreate):
    id: int
    acknowledged: bool
    created_at: datetime = Field(alias="createdAt")


class JournalCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    mode: Literal["INTRADAY", "SWING"]
    direction: Literal["LONG", "SHORT"]
    decision_state: str = Field(alias="decisionState", min_length=1, max_length=80)
    setup: str = Field(min_length=1, max_length=120)
    quantity: int | None = Field(default=None, gt=0)
    entry_price: float | None = Field(default=None, alias="entryPrice", gt=0)
    stop_price: float | None = Field(default=None, alias="stopPrice", gt=0)
    opened_at: datetime = Field(alias="openedAt")
    notes: str = Field(default="", max_length=5000)

    model_config = {"populate_by_name": True, "extra": "forbid"}

    @model_validator(mode="after")
    def validate_manual_trade(self) -> "JournalCreate":
        if self.opened_at.utcoffset() is None:
            raise ValueError("openedAt must be timezone-aware")
        if self.entry_price is not None and self.stop_price is not None:
            if self.direction == "LONG" and self.stop_price >= self.entry_price:
                raise ValueError("LONG stopPrice must be below entryPrice")
            if self.direction == "SHORT" and self.stop_price <= self.entry_price:
                raise ValueError("SHORT stopPrice must be above entryPrice")
        return self


class JournalOutcomeUpdate(BaseModel):
    outcome_state: Literal[
        "OPEN", "WIN", "LOSS", "BREAKEVEN", "EXPIRED", "CANCELLED"
    ] = Field(alias="outcomeState")
    exit_price: float | None = Field(default=None, alias="exitPrice", gt=0)
    closed_at: datetime | None = Field(default=None, alias="closedAt")
    pnl: float | None = None
    r_multiple: float | None = Field(default=None, alias="rMultiple")
    notes: str | None = Field(default=None, max_length=5000)

    model_config = {"populate_by_name": True, "extra": "forbid"}

    @model_validator(mode="after")
    def validate_outcome(self) -> "JournalOutcomeUpdate":
        if self.closed_at is not None and self.closed_at.utcoffset() is None:
            raise ValueError("closedAt must be timezone-aware")
        if self.outcome_state != "OPEN" and (
            self.exit_price is None or self.closed_at is None
        ):
            raise ValueError("closed outcomes require exitPrice and closedAt")
        return self


class JournalRecord(JournalCreate):
    id: int
    outcome_state: str = Field(alias="outcomeState")
    exit_price: float | None = Field(default=None, alias="exitPrice")
    closed_at: datetime | None = Field(default=None, alias="closedAt")
    pnl: float | None = None
    r_multiple: float | None = Field(default=None, alias="rMultiple")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
