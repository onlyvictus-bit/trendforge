from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, log, pi, sqrt
from statistics import NormalDist
from typing import Literal

from pydantic import BaseModel, Field


OptionType = Literal["call", "put"]
NORMAL = NormalDist()


@dataclass(frozen=True)
class OptionGreeks:
    delta: float
    gamma: float
    theta_per_day: float
    vega_per_vol_point: float
    rho_per_rate_point: float


class OptionPricingInput(BaseModel):
    spot: float = Field(gt=0)
    strike: float = Field(gt=0)
    time_years: float = Field(gt=0, le=10)
    rate: float = Field(default=0.065, ge=-0.05, le=0.5)
    volatility: float = Field(gt=0, le=5)
    option_type: OptionType
    dividend_yield: float = Field(default=0, ge=-0.05, le=0.5)


class ImpliedVolatilityInput(BaseModel):
    market_price: float = Field(gt=0)
    spot: float = Field(gt=0)
    strike: float = Field(gt=0)
    time_years: float = Field(gt=0, le=10)
    rate: float = Field(default=0.065, ge=-0.05, le=0.5)
    option_type: OptionType
    dividend_yield: float = Field(default=0, ge=-0.05, le=0.5)


def _validate_inputs(
    spot: float, strike: float, time_years: float, volatility: float | None = None
) -> None:
    values = (
        (spot, strike, time_years)
        if volatility is None
        else (spot, strike, time_years, volatility)
    )
    if not all(isfinite(value) for value in values):
        raise ValueError("option inputs must be finite")
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if time_years <= 0:
        raise ValueError("time_years must be positive")
    if volatility is not None and volatility <= 0:
        raise ValueError("volatility must be positive")


def _d1_d2(
    spot: float,
    strike: float,
    time_years: float,
    rate: float,
    volatility: float,
    dividend_yield: float,
) -> tuple[float, float]:
    sigma_root_t = volatility * sqrt(time_years)
    d1 = (
        log(spot / strike) + (rate - dividend_yield + 0.5 * volatility**2) * time_years
    ) / sigma_root_t
    return d1, d1 - sigma_root_t


def black_scholes_price(
    *,
    spot: float,
    strike: float,
    time_years: float,
    rate: float,
    volatility: float,
    option_type: OptionType,
    dividend_yield: float = 0.0,
) -> float:
    _validate_inputs(spot, strike, time_years, volatility)
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be call or put")
    d1, d2 = _d1_d2(spot, strike, time_years, rate, volatility, dividend_yield)
    discounted_spot = spot * exp(-dividend_yield * time_years)
    discounted_strike = strike * exp(-rate * time_years)
    if option_type == "call":
        return discounted_spot * NORMAL.cdf(d1) - discounted_strike * NORMAL.cdf(d2)
    return discounted_strike * NORMAL.cdf(-d2) - discounted_spot * NORMAL.cdf(-d1)


def black_scholes_greeks(
    *,
    spot: float,
    strike: float,
    time_years: float,
    rate: float,
    volatility: float,
    option_type: OptionType,
    dividend_yield: float = 0.0,
) -> OptionGreeks:
    _validate_inputs(spot, strike, time_years, volatility)
    d1, d2 = _d1_d2(spot, strike, time_years, rate, volatility, dividend_yield)
    pdf_d1 = exp(-0.5 * d1**2) / sqrt(2 * pi)
    discount_q = exp(-dividend_yield * time_years)
    discount_r = exp(-rate * time_years)
    gamma = discount_q * pdf_d1 / (spot * volatility * sqrt(time_years))
    vega = spot * discount_q * pdf_d1 * sqrt(time_years) / 100
    common_theta = -(spot * discount_q * pdf_d1 * volatility) / (2 * sqrt(time_years))
    if option_type == "call":
        delta = discount_q * NORMAL.cdf(d1)
        theta = (
            common_theta
            - rate * strike * discount_r * NORMAL.cdf(d2)
            + dividend_yield * spot * discount_q * NORMAL.cdf(d1)
        )
        rho = strike * time_years * discount_r * NORMAL.cdf(d2) / 100
    elif option_type == "put":
        delta = discount_q * (NORMAL.cdf(d1) - 1)
        theta = (
            common_theta
            + rate * strike * discount_r * NORMAL.cdf(-d2)
            - dividend_yield * spot * discount_q * NORMAL.cdf(-d1)
        )
        rho = -strike * time_years * discount_r * NORMAL.cdf(-d2) / 100
    else:
        raise ValueError("option_type must be call or put")
    return OptionGreeks(
        delta=delta,
        gamma=gamma,
        theta_per_day=theta / 365,
        vega_per_vol_point=vega,
        rho_per_rate_point=rho,
    )


def implied_volatility(
    *,
    market_price: float,
    spot: float,
    strike: float,
    time_years: float,
    rate: float,
    option_type: OptionType,
    dividend_yield: float = 0.0,
    tolerance: float = 1e-7,
    max_iterations: int = 200,
) -> float:
    _validate_inputs(spot, strike, time_years)
    if not isfinite(market_price) or market_price <= 0:
        raise ValueError("market_price must be positive and finite")
    discounted_spot = spot * exp(-dividend_yield * time_years)
    discounted_strike = strike * exp(-rate * time_years)
    lower_bound = (
        max(0.0, discounted_spot - discounted_strike)
        if option_type == "call"
        else max(0.0, discounted_strike - discounted_spot)
    )
    upper_bound = discounted_spot if option_type == "call" else discounted_strike
    if not lower_bound <= market_price <= upper_bound:
        raise ValueError("market_price violates no-arbitrage bounds")

    low, high = 1e-6, 5.0
    for _ in range(max_iterations):
        mid = (low + high) / 2
        value = black_scholes_price(
            spot=spot,
            strike=strike,
            time_years=time_years,
            rate=rate,
            volatility=mid,
            option_type=option_type,
            dividend_yield=dividend_yield,
        )
        if abs(value - market_price) <= tolerance:
            return mid
        if value < market_price:
            low = mid
        else:
            high = mid
    raise ValueError("implied volatility solver did not converge")
