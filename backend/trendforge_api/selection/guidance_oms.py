"""File A guidance OMS (R2-B activation amendment, 2026-08-25).

Paper ticket + OpenAlgo order JSON preview per TRADE_GUIDANCE_LAW_2026-08-25.
This is trade GUIDANCE, not a broker:

- Default boot is preview only. The live placement path exists but fires
  ONLY when ALL THREE gates hold:
    1. TRENDFORGE_LIVE_ORDERS=1 (environment),
    2. effective data lane is OPENALGO_RO,
    3. the UI arm switch (#armLiveOrders) has been switched on this boot.
  Any single missing gate raises GuidanceLiveBlocked("LIVE_ORDERS_ARMED_OFF").
- researchQuantity comes from selection.research_quantity (capped, capped by
  calibration 0.5 until PIT approval); it never becomes product final_qty.
- This module never confirms anything and never touches File A public state.
"""

from __future__ import annotations

import os
import re
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .research_quantity import compute_research_quantity

SCHEMA_VERSION = "trendforge.guidance-oms.v1"
PROFILE_ID = "PRF-GUIDANCE-OMS-PAPER"
ACCEPTANCE_CEILING = "LIVE_GUIDANCE_OMS_PREVIEW_DEFAULT"
GUIDANCE_COPY = "Trade guidance - not a guaranteed win."
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

_TRUTHY = {"1", "true", "yes", "on"}


class GuidanceLiveBlocked(RuntimeError):
    """Raised when a live placement was requested without all three arms."""

    def __init__(self, code: str, detail: dict[str, Any] | None = None):
        super().__init__(code)
        self.code = code
        self.detail = detail or {}


class GuidanceArmSnapshotV1(BaseModel):
    model_config = MODEL_CONFIG

    env_live_orders: bool = False
    lane_openalgo_ro: bool = False
    ui_armed: bool = False

    def live_orders_allowed(self) -> bool:
        return self.env_live_orders and self.lane_openalgo_ro and self.ui_armed


_UI_LIVE_ORDERS_ARMED = False


def set_live_orders_armed(value: bool) -> None:
    global _UI_LIVE_ORDERS_ARMED
    _UI_LIVE_ORDERS_ARMED = bool(value)


def get_live_orders_armed() -> bool:
    return _UI_LIVE_ORDERS_ARMED


def arm_snapshot(*, lane: Any) -> GuidanceArmSnapshotV1:
    env_on = (os.environ.get("TRENDFORGE_LIVE_ORDERS") or "").strip().lower() in _TRUTHY
    effective = getattr(lane, "effective_lane", None) or getattr(lane, "lane", None)
    return GuidanceArmSnapshotV1(
        env_live_orders=env_on,
        lane_openalgo_ro=effective == "OPENALGO_RO",
        ui_armed=_UI_LIVE_ORDERS_ARMED,
    )


def ensure_live_placement_allowed(snapshot: GuidanceArmSnapshotV1) -> None:
    if not snapshot.live_orders_allowed():
        raise GuidanceLiveBlocked(
            "LIVE_ORDERS_ARMED_OFF",
            detail={
                "envLiveOrders": snapshot.env_live_orders,
                "laneOpenAlgoRo": snapshot.lane_openalgo_ro,
                "uiArmed": snapshot.ui_armed,
            },
        )


class GuidanceOMSTicketV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    symbol: str
    public_state: str
    side: Literal["LONG", "SHORT", "FLAT"] = "FLAT"
    research_quantity: int = Field(default=0, ge=0)
    qty_unit: str = "shares"
    research_entry: float | None = None
    research_stop: float | None = None
    research_t1: float | None = None
    capital_inr: float = 100_000.0
    risk_pct: float = 0.005
    notional_inr: float = Field(default=0.0, ge=0)
    reserved_risk_inr: float = Field(default=0.0, ge=0)
    remaining_funds_inr: float = Field(default=100_000.0)
    blockers: tuple[str, ...] = ()
    executable: Literal[False] = False
    guidance_copy: str = GUIDANCE_COPY
    openalgo_order_json: dict[str, Any] = {}

    @model_validator(mode="after")
    def paper_law(self) -> "GuidanceOMSTicketV1":
        if self.side == "FLAT" and self.research_quantity != 0:
            raise ValueError("FLAT guidance tickets must carry quantity 0")
        if self.research_quantity > 0:
            if self.side == "FLAT" or self.research_entry is None or (
                self.research_stop is None
            ):
                raise ValueError("sized tickets require side, entry and stop")
            if not self.openalgo_order_json:
                raise ValueError("sized tickets must carry an order JSON preview")
        return self


def last_official_close(symbol: str, trading_date: Any) -> float | None:
    """Last official closed cash bar close for one symbol, else None."""
    from datetime import date as _date

    from .cash_a4_history import list_raw_bars

    day: _date | None = None
    if isinstance(trading_date, str):
        try:
            day = _date.fromisoformat(trading_date[:10])
        except ValueError:
            day = None
    elif hasattr(trading_date, "year") and not hasattr(trading_date, "tzinfo"):
        day = trading_date  # date instance
    elif trading_date is not None and hasattr(trading_date, "date"):
        try:
            day = trading_date.date()
        except Exception:
            day = None
    if day is None:
        return None
    try:
        bars = list_raw_bars(symbol.strip().upper(), through=day)
    except Exception:
        return None
    if not bars:
        return None
    close = getattr(bars[-1], "close", None)
    try:
        value = float(close)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def parse_stop_price(text: str | None) -> float | None:
    if text is None:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(text))
    if match is None:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def compute_paper_plan(
    *,
    symbol: str,
    public_state: str,
    evidence_direction: str,
    draft_confirmed_eligible: bool,
    invalidation_condition: str | None,
    trading_date: Any,
    regime_label: str | None = None,
    lane: str = "FREE_OFFICIAL",
    research_capital_inr: float = 100_000.0,
    risk_pct: float = 0.005,
) -> tuple[dict[str, Any], float | None]:
    """Pure plan computation; returns (plan_dict, official_close)."""
    close = last_official_close(symbol, trading_date)
    stop = parse_stop_price(invalidation_condition)
    plan = compute_research_quantity(
        public_state=public_state,
        evidence_direction=evidence_direction,
        draft_confirmed_eligible=draft_confirmed_eligible,
        is_reject_or_ban=public_state == "REJECT",
        official_close=close,
        invalidation_condition=None if stop is None else f"stop {stop}",
        atr=None,
        lot_size=None,
        s8_completeness_ratio=None,
        regime_label=regime_label,
        index_suspect=False,
        lane=lane,
        research_capital_inr=research_capital_inr,
        risk_pct=risk_pct,
    )
    return plan, close


def openalgo_placeorder_json(ticket: GuidanceOMSTicketV1) -> dict[str, Any]:
    """Preview payload for OpenAlgo /api/v1/placeorder. API key REDACTED."""
    action = "BUY" if ticket.side == "LONG" else "SELL"
    price = "" if ticket.research_entry is None else f"{ticket.research_entry:.2f}"
    return {
        "apikey": "REDACTED_SET_VIA_OPENALGO_API_KEY",
        "strategy": "TrendForge",
        "symbol": ticket.symbol.upper(),
        "exchange": "NSE",
        "action": action,
        "pricetype": "LIMIT",
        "price": price,
        "product_type": "MIS",
        "quantity": ticket.research_quantity,
        "disclosed_quantity": 0,
        "trigger_price": None,
        "is_amo": False,
        "remarks": f"TrendForge guidance ticket {ticket.symbol.upper()}",
    }


def build_paper_ticket(
    *,
    symbol: str,
    public_state: str,
    plan: dict[str, Any],
) -> GuidanceOMSTicketV1:
    side_value = plan.get("side") or plan.get("_side") or "FLAT"
    side: Literal["LONG", "SHORT", "FLAT"] = (
        side_value if side_value in ("LONG", "SHORT", "FLAT") else "FLAT"
    )
    qty = int(plan.get("researchQuantity") or 0)
    blockers = [str(plan.get("reason"))] if plan.get("reason") else []
    entry = plan.get("researchEntry")
    stop = plan.get("researchStop")
    t1 = plan.get("researchT1")
    entry_f = float(entry) if entry is not None else None
    stop_f = float(stop) if stop is not None else None
    t1_f = float(t1) if t1 is not None else None
    preview: dict[str, Any] = {}
    if qty > 0:
        action = "BUY" if side == "LONG" else "SELL"
        preview = {
            "apikey": "REDACTED_SET_VIA_OPENALGO_API_KEY",
            "strategy": "TrendForge",
            "symbol": symbol.upper(),
            "exchange": "NSE",
            "action": action,
            "pricetype": "LIMIT",
            "price": "" if entry_f is None else f"{entry_f:.2f}",
            "product_type": "MIS",
            "quantity": qty,
            "disclosed_quantity": 0,
            "trigger_price": None,
            "is_amo": False,
            "remarks": f"TrendForge guidance ticket {symbol.upper()}",
        }
    return GuidanceOMSTicketV1(
        symbol=symbol.upper(),
        public_state=str(public_state).upper(),
        side=side,
        research_quantity=qty,
        qty_unit=str(plan.get("qtyUnit") or "shares"),
        research_entry=entry_f,
        research_stop=stop_f,
        research_t1=t1_f,
        capital_inr=100_000.0,
        notional_inr=float(plan.get("notionalInr") or 0.0),
        reserved_risk_inr=float(plan.get("reservedRiskInr") or 0.0),
        remaining_funds_inr=float(plan.get("remainingCapitalInr") or 100_000.0),
        blockers=tuple(blockers),
        openalgo_order_json=preview,
    )


def dispatch_live_placement(
    ticket: GuidanceOMSTicketV1,
    *,
    lane: Any,
    transport: Callable[[str, dict[str, Any], float], dict[str, Any]] | None = None,
    config: Any = None,
) -> dict[str, Any]:
    """Triple-gated placement path. Never called on default boot.

    The preview payload's REDACTED apikey placeholder is replaced with the
    configured key only inside this function, after all three arms pass.
    """
    ensure_live_placement_allowed(arm_snapshot(lane=lane))
    if ticket.research_quantity <= 0 or ticket.side == "FLAT":
        raise GuidanceLiveBlocked(
            "NO_SIZED_TICKET",
            detail={"symbol": ticket.symbol, "blockers": list(ticket.blockers)},
        )

    from ..openalgo_client import OpenAlgoConfig, _post_json

    cfg = config or OpenAlgoConfig.from_env()
    payload = dict(ticket.openalgo_order_json)
    payload["apikey"] = cfg.api_key
    send = transport or _post_json
    url = f"{cfg.base_url.rstrip('/')}/api/v1/placeorder"
    response = send(url, payload, cfg.timeout_seconds)
    if not isinstance(response, dict):
        raise GuidanceLiveBlocked("PLACEORDER_BAD_RESPONSE", {})
    filtered = {
        key: response.get(key)
        for key in ("status", "message", "data", "error")
        if key in response
    }
    return filtered
