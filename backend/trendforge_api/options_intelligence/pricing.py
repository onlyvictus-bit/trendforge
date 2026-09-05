"""Black-76 pricing, greeks and an IV solver with a mandatory test suite.

Contract: merged spec v2 L2 / prompt section 8. Options on futures (and
Indian index options priced off the synthetic forward) use Black-76:

    C = e^{-rT} [ F N(d1) - K N(d2) ]
    P = e^{-rT} [ K N(-d2) - F N(-d1) ]
    d1 = [ ln(F/K) + 0.5 sigma^2 T ] / (sigma sqrt(T)),  d2 = d1 - sigma sqrt(T)

Only stdlib math is used so the suite runs anywhere. Decay is reported
by repricing at a later timestamp (one clock), never by dividing annual
theta by a fixed 365.
"""

from __future__ import annotations

from enum import StrEnum
from math import erf, exp, isfinite, log, sqrt

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)

_IV_LO = 1e-4
_IV_HI = 5.0
_IV_ITERATIONS = 200


class OptionRight(StrEnum):
    """One right enum everywhere; raw 'C'/'P'/'CE'/'PE' strings stop here."""

    CE = "CE"
    PE = "PE"


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def norm_pdf(x: float) -> float:
    return exp(-0.5 * x * x) / sqrt(2.0 * 3.14159_26535_89793)


def _d1_d2(forward: float, strike: float, years: float, sigma: float) -> tuple[float, float]:
    denom = sigma * sqrt(years)
    d1 = (log(forward / strike) + 0.5 * sigma * sigma * years) / denom
    return d1, d1 - denom


def black76_price(
    *,
    forward: float,
    strike: float,
    years: float,
    sigma: float,
    rate: float,
    right: OptionRight | str,
) -> float:
    right = OptionRight(right)
    discount = exp(-rate * years)
    d1, d2 = _d1_d2(forward, strike, years, sigma)
    if right is OptionRight.CE:
        return discount * (forward * norm_cdf(d1) - strike * norm_cdf(d2))
    return discount * (strike * norm_cdf(-d2) - forward * norm_cdf(-d1))


def black76_greeks(
    *,
    forward: float,
    strike: float,
    years: float,
    sigma: float,
    rate: float,
    right: OptionRight | str,
) -> "GreeksResult":
    right = OptionRight(right)
    discount = exp(-rate * years)
    d1, d2 = _d1_d2(forward, strike, years, sigma)
    density = norm_pdf(d1)
    gamma = discount * density / (forward * sigma * sqrt(years))
    vega = discount * forward * density * sqrt(years)
    if right is OptionRight.CE:
        delta = discount * norm_cdf(d1)
        rho = -years * strike * discount * norm_cdf(d2)
    else:
        delta = discount * (norm_cdf(d1) - 1.0)
        rho = years * strike * discount * norm_cdf(-d2)
    value = black76_price(
        forward=forward,
        strike=strike,
        years=years,
        sigma=sigma,
        rate=rate,
        right=right,
    )
    # Theta = r*V - D * F phi(d1) sigma / (2 sqrt(T)); holds for CE and PE
    # (put-call parity keeps the carry term identical for both rights).
    theta_annual = (
        rate * value - discount * forward * density * sigma / (2.0 * sqrt(years))
    )
    return GreeksResult(
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta_annual=theta_annual,
        rho=rho,
    )


class GreeksResult(BaseModel):
    model_config = MODEL_CONFIG

    delta: float
    gamma: float
    vega: float
    theta_annual: float
    rho: float


def implied_vol(
    *,
    premium: float,
    forward: float,
    strike: float,
    years: float,
    rate: float,
    right: OptionRight | str,
) -> float | None:
    """Bisection IV solver; returns None when premium is outside arbitrage bounds."""
    right = OptionRight(right)
    if not all(isfinite(v) for v in (premium, forward, strike, years)) or years <= 0:
        return None
    discount = exp(-rate * years)
    intrinsic = max(0.0, (forward - strike) if right is OptionRight.CE else (strike - forward))
    lower_bound = discount * intrinsic
    upper_bound = forward if right is OptionRight.CE else strike
    upper_bound *= discount
    if premium < lower_bound - 1e-9 or premium > upper_bound + 1e-9:
        return None
    lo, hi = _IV_LO, _IV_HI
    for _ in range(_IV_ITERATIONS):
        mid = 0.5 * (lo + hi)
        price = black76_price(
            forward=forward,
            strike=strike,
            years=years,
            sigma=mid,
            rate=rate,
            right=right,
        )
        if price < premium:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    solved = 0.5 * (lo + hi)
    check = black76_price(
        forward=forward,
        strike=strike,
        years=years,
        sigma=solved,
        rate=rate,
        right=right,
    )
    if abs(check - premium) > 1e-6:
        return None
    return solved


def synthetic_forward(*, strike: float, call: float, put: float, rate: float, years: float) -> float:
    """F = K + e^{rT}(C - P); large parity dispersion across strikes flags data."""
    return strike + exp(rate * years) * (call - put)


def decay_by_reprice(
    *,
    forward: float,
    strike: float,
    years: float,
    sigma: float,
    rate: float,
    right: OptionRight | str,
    next_years: float,
) -> float | None:
    """price(now) - price(next timestamp). The only decay number we print.

    `next_years` must use the SAME clock convention as `years` (calendar or
    trading year), advanced to the actual next valuation timestamp.
    """
    if next_years >= years or next_years < 0:
        return None
    now_price = black76_price(
        forward=forward,
        strike=strike,
        years=years,
        sigma=sigma,
        rate=rate,
        right=right,
    )
    later = black76_price(
        forward=forward,
        strike=strike,
        years=next_years,
        sigma=sigma,
        rate=rate,
        right=right,
    )
    return now_price - later
