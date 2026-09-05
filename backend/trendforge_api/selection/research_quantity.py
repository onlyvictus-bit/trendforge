"""File A research quantity at draft-confirmed eligibility (SEL-008 extension).

LONG/SHORT research position sizing on the S7 idea card at the confirmation
point. NOT File A product ``final_qty``; NOT OMS; NOT a broker order.
Ceiling LIVE_RESEARCH_QTY_NOT_EXECUTABLE. ``executable=false`` always.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "trendforge.research-qty.v1"
PROFILE_ID = "PRF-RESEARCH-QTY-WAIT"
ACCEPTANCE_CEILING = "LIVE_RESEARCH_QTY_NOT_EXECUTABLE"
CALIBRATION_CAP = 0.5  # until PIT_APPROVED
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

Side = Literal["LONG", "SHORT", "FLAT"]
QTY_ZERO_REASON = Literal[
    "WAIT_REJECT",
    "WAIT_NOT_AT_CONFIRMATION",
    "WAIT_NO_STOP",
    "WAIT_LOT",
    "WAIT_FUNDS",
    "NO_SIDE",
]


class ResearchFundsV1(BaseModel):
    model_config = MODEL_CONFIG

    capital_inr: float = 100_000.0
    reserved_risk_inr: float = 0.0
    position_notional_inr: float = 0.0
    remaining_capital_inr: float = 100_000.0


class ResearchPositionCardV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    side: Side
    qty: int = 0
    qty_unit: str = "shares"
    research_entry: float | None = None
    research_stop: float | None = None
    notional_inr: float = 0.0
    reserved_risk_inr: float = 0.0
    lane: str = "FREE_OFFICIAL"
    evidence_kind: str = "OFFICIAL_CLOSED"
    as_of: str | None = None
    executable: bool = False


class ResearchQtyRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    public_state: str
    evidence_direction: str
    draft_confirmed_eligible: bool = False
    side: Side = "FLAT"
    research_quantity: int = 0
    qty_unit: str = "shares"
    research_entry: float | None = None
    research_stop: float | None = None
    research_t1: float | None = None
    reason: str = ""
    data_quality_cap: float = Field(ge=0, le=1, default=1.0)
    regime_cap: float = Field(ge=0, le=1, default=1.0)
    liquidity_cap: float = Field(ge=0, le=1, default=1.0)
    calibration_cap: float = CALIBRATION_CAP
    executable: bool = False


class ResearchQtyBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    source_activation_ready: bool = False
    confirmed_count: int = 0
    rows: tuple[ResearchQtyRowV1, ...]
    warnings: tuple[str, ...] = ()
    research_funds: ResearchFundsV1 = Field(default_factory=ResearchFundsV1)
    executable: bool = False

    @model_validator(mode="after")
    def enforce_qty_law(self) -> "ResearchQtyBatchV1":
        if self.source_activation_ready:
            raise ValueError("research qty cannot activate sources")
        if self.confirmed_count != 0:
            raise ValueError("research qty cannot emit CONFIRMED")
        for row in self.rows:
            if row.research_quantity > 0 and row.side == "FLAT":
                raise ValueError("FLAT rows must have qty 0")
        return self


def compute_research_quantity(
    *,
    public_state: str,
    evidence_direction: str,
    draft_confirmed_eligible: bool,
    is_reject_or_ban: bool,
    official_close: float | None,
    invalidation_condition: str | None,
    atr: float | None,
    lot_size: int | None,
    s8_completeness_ratio: float | None,
    regime_label: str | None,
    index_suspect: bool,
    lane: str = "FREE_OFFICIAL",
    research_capital_inr: float = 100_000.0,
    risk_pct: float = 0.005,
    slippage_per_share: float | None = None,
) -> dict[str, Any]:
    """Pure function: PRF-003 confirmation-point sizing. No side effects."""
    if is_reject_or_ban or public_state == "REJECT":
        return _zero("WAIT_REJECT")
    if not draft_confirmed_eligible:
        return _zero("WAIT_NOT_AT_CONFIRMATION")

    # Direction
    dir_upper = evidence_direction.upper()
    if dir_upper in ("BULLISH", "BUY"):
        side = "LONG"
    elif dir_upper in ("BEARISH", "SELL"):
        side = "SHORT"
    else:
        return {**_zero("NO_SIDE"), "_side": "FLAT"}

    # Entry: last official closed close
    if official_close is None or official_close <= 0:
        return {**_zero("WAIT_NO_STOP"), "_side": side}
    entry = official_close

    # Stop from invalidation (parseable price) or ATR fallback
    stop = _parse_price(invalidation_condition)
    if stop is None:
        if atr is None or atr <= 0:
            return {**_zero("WAIT_NO_STOP"), "_side": side}
        k = 1.0
        stop = entry - k * atr if side == "LONG" else entry + k * atr

    # Correct-side check
    if side == "LONG" and stop >= entry:
        return {**_zero("WAIT_NO_STOP"), "_side": side}
    if side == "SHORT" and stop <= entry:
        return {**_zero("WAIT_NO_STOP"), "_side": side}

    declared_cost = max(float(slippage_per_share or 0.0), 0.0)
    unit_risk = abs(entry - stop) + declared_cost

    # Caps
    dq_cap = 1.0
    if lane == "OPENALGO_RO":
        dq_cap = 0.7
    if s8_completeness_ratio is not None and s8_completeness_ratio < MIN_COMPLETENESS:
        dq_cap = 0.0
    if index_suspect:
        dq_cap = 0.0

    regime_cap = 1.0 if regime_label not in (None, "", "UNKNOWN") else 0.5
    liquidity_cap = 0.0 if is_reject_or_ban else 1.0

    risk_budget = research_capital_inr * risk_pct
    if unit_risk <= 0:
        return {**_zero("WAIT_NO_STOP"), "_side": side}
    base_qty = math.floor(risk_budget / unit_risk)

    raw_qty = math.floor(
        base_qty * dq_cap * regime_cap * liquidity_cap * CALIBRATION_CAP
    )

    # Lot round
    if lot_size is not None and lot_size > 0:
        qty = (raw_qty // lot_size) * lot_size
        qty_unit = "shares" if lot_size == 1 else "contracts"
    else:
        qty = raw_qty
        qty_unit = "shares"

    # Funds check: never negative remaining
    max_affordable = max(0, math.floor(research_capital_inr / entry))
    if lot_size is not None and lot_size > 0:
        max_affordable = (max_affordable // lot_size) * lot_size
    qty = min(qty, max_affordable)
    notional = qty * entry

    reserved_risk = min(qty * unit_risk, risk_budget)

    t1 = (
        entry + 1.5 * abs(entry - stop) if side == "LONG"
        else entry - 1.5 * abs(entry - stop)
    )

    return {
        "side": side,
        "researchQuantity": qty,
        "qtyUnit": qty_unit,
        "researchEntry": entry,
        "researchStop": stop,
        "researchT1": round(t1, 2),
        "reason": (
            "WAIT_INDEX_SUSPECT"
            if index_suspect
            else "WAIT_COMPLETENESS"
            if dq_cap == 0.0
            else "WAIT_FUNDS"
            if qty == 0
            else ""
        ),
        "dataQualityCap": dq_cap,
        "regimeCap": regime_cap,
        "liquidityCap": liquidity_cap,
        "calibrationCap": CALIBRATION_CAP,
        "notionalInr": round(notional, 2),
        "reservedRiskInr": round(reserved_risk, 2),
        "remainingCapitalInr": round(research_capital_inr - notional, 2),
        "_side": side,
    }


def _zero(reason: str) -> dict[str, Any]:
    return {
        "researchQuantity": 0,
        "reason": reason,
        "executable": False,
    }


MIN_COMPLETENESS = 0.95


def _parse_price(text: str | None) -> float | None:
    if text is None:
        return None
    import re
    match = re.search(r"(\d+\.?\d*)", text)
    return float(match.group(1)) if match else None
