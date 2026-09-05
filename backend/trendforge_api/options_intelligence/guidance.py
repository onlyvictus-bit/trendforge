"""Frozen guidance JSON: hero-zero and trend-time use cases.

The JSON emitted here is the only thing an LLM may render, verbatim.
prob_touch_Q is a risk-neutral barrier approximation; prob_touch_P stays
null until a physical distribution is calibrated (Brier-gated at R16).
Printing Q as a win rate is a contract failure. Authority is always
CONTEXT_ONLY with can_confirm=false; OI/options never confirm direction.
"""

from __future__ import annotations

from math import isfinite, log, sqrt

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .pricing import OptionRight, norm_cdf
from .quadrant import QuadrantResult

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)

EXPECTED_MOVE_STRADDLE_FACTOR = 0.8


def _expected_move(atm_straddle: float) -> float:
    return EXPECTED_MOVE_STRADDLE_FACTOR * atm_straddle


def hero_zero_guidance(
    *,
    symbol: str,
    expiry: str,
    strike: float,
    right: str,
    spot: float,
    premium: float,
    atm_straddle: float,
    sigma: float,
    years: float,
    rate: float = 0.0,
    costs_total: float = 0.0,
    blockers: tuple[str, ...] | list[str] = (),
    next_years: float | None = None,
) -> dict:
    """Hero-zero / extreme-convexity research card for one strike."""
    right_enum = OptionRight(right)
    expected_move = _expected_move(atm_straddle)
    if expected_move <= 0 or spot <= 0 or not all(
        isfinite(v) for v in (strike, spot, premium, atm_straddle, sigma, years)
    ):
        dist_sigma = None
        prob_touch_q = None
        prob_keep_premium_q = None
        ev_after_costs = None
    else:
        log_ratio = log(strike / spot)
        dist_sigma = round(abs(log_ratio) * spot / expected_move, 4)
        denom = sigma * sqrt(years)
        if denom <= 0:
            prob_touch_q = None
            prob_keep_premium_q = None
        else:
            if right_enum is OptionRight.CE:
                above = strike > spot
            else:
                above = strike < spot
            one_sided = norm_cdf(-abs(log_ratio) / denom)
            prob_touch_q = round(min(1.0, 2.0 * one_sided), 4) if above else None
            d2 = (log_ratio - 0.5 * sigma * sigma * years) / denom
            prob_keep_premium_q = (
                round(norm_cdf(-d2), 4)
                if right_enum is OptionRight.CE
                else round(norm_cdf(d2), 4)
            )
        from .pricing import black76_price

        terminal_call = max(strike - 0.0, 0.0)
        del terminal_call
        fwd = spot * 1.0  # forward approximated by carry-adjusted caller input
        price_now = black76_price(
            forward=fwd,
            strike=strike,
            years=years,
            sigma=sigma,
            rate=rate,
            right=right_enum,
        )
        ev_after_costs = round(price_now - premium - costs_total, 4)

    state = "WAIT" if blockers else "WATCH"
    decay_capture = None
    if next_years is not None and years > next_years:
        from .pricing import black76_price, decay_by_reprice

        capture = decay_by_reprice(
            forward=spot,
            strike=strike,
            years=years,
            sigma=sigma,
            rate=rate,
            right=right_enum,
            next_years=next_years,
        )
        decay_capture = None if capture is None else round(capture, 4)
        del black76_price
    return {
        "useCase": "HERO_ZERO",
        "contract": f"{symbol.upper()}-{expiry}-{strike:g}-{right_enum.value}",
        "observed": {
            "spot": spot,
            "premium": premium,
            "distSigma": dist_sigma,
            "atmStraddle": atm_straddle,
            "spreadPct": None,
        },
        "inferred": {
            "probTouchQ": prob_touch_q,
            "probTouchP": None,
            "probKeepPremiumQ": prob_keep_premium_q,
            "evAfterCosts": ev_after_costs,
            "decayByReprice": decay_capture,
        },
        "authority": "CONTEXT_ONLY",
        "canConfirm": False,
        "state": state,
        "blockers": list(blockers),
        "invalidation": "spot trades beyond the short strike with hold, or wall OI unwinds against the structure",
        "notes": [
            "Q-probabilities are model-implied, never win rates.",
            "Premium can go to zero; that is the strategy's definition of total loss on the buy side.",
        ],
    }


def trend_time_guidance(
    *, result: QuadrantResult, volume_z: float | None, persistence_intervals: int
) -> dict:
    """Participation-geometry guidance around one futures quadrant row."""
    vol_ok = volume_z is not None and volume_z > 1.5
    persisted = persistence_intervals >= 3
    supports = (
        result.code.value in {"PRICE_UP_OI_UP", "PRICE_DOWN_OI_DOWN"} and vol_ok
    )
    return {
        "useCase": "TREND_TIME",
        "contract": result.interval,
        "observed": {
            "code": result.code.value,
            "priceChangePct": result.price_change_pct,
            "oiChangePct": result.oi_change_pct,
            "volumeZ": volume_z,
            "persistenceIntervals": persistence_intervals,
        },
        "inferred": {
            "participationBuilding": bool(vol_ok and persisted),
            "supportsStructure": bool(supports),
        },
        "interpretation": result.interpretation,
        "alternativeExplanations": ["HEDGE", "SPREAD", "ROLL"],
        "authority": "CONTEXT_ONLY",
        "canConfirm": False,
        "state": "WATCH" if result.code is not result.code.UNKNOWN else "WAIT",
        "blockers": [f"QUADRANT_{reason}" for reason in result.reasons],
        "invalidation": "next aligned interval shows opposite OI direction or volume z collapses below baseline",
    }
