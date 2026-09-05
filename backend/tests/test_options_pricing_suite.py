"""Pricing suite A5 (prompt section 8): parity, finite-difference greeks,
known values, zero-vol/zero-time limits and synthetic-forward consistency.

Black-76 on the forward; stdlib only. Tolerances are absolute and chosen
for float64 bisection IV.
"""

from __future__ import annotations

import math

import pytest

from trendforge_api.options_intelligence.pricing import (
    OptionRight,
    black76_greeks,
    black76_price,
    decay_by_reprice,
    implied_vol,
    synthetic_forward,
)


F = 25000.0
K = 25200.0
T = 12.0 / 365.0
SIGMA = 0.14
R = 0.065


def test_put_call_parity_bounds() -> None:
    call = black76_price(forward=F, strike=K, years=T, sigma=SIGMA, rate=R, right=OptionRight.CE)
    put = black76_price(forward=F, strike=K, years=T, sigma=SIGMA, rate=R, right=OptionRight.PE)
    lhs = call - put
    rhs = math.exp(-R * T) * (F - K)
    assert math.isclose(lhs, rhs, rel_tol=1e-9, abs_tol=1e-6)


def test_ce_and_pe_known_values() -> None:
    deep_itm_call = black76_price(
        forward=F, strike=1000.0, years=T, sigma=SIGMA, rate=R, right=OptionRight.CE
    )
    assert math.isclose(deep_itm_call, math.exp(-R * T) * (F - 1000.0), rel_tol=1e-4)
    deep_otm_call = black76_price(
        forward=F, strike=60000.0, years=T, sigma=SIGMA, rate=R, right=OptionRight.CE
    )
    assert deep_otm_call >= 0.0 and deep_otm_call < 1e-3
    put = black76_price(forward=F, strike=F, years=T, sigma=SIGMA, rate=R, right=OptionRight.PE)
    call = black76_price(forward=F, strike=F, years=T, sigma=SIGMA, rate=R, right=OptionRight.CE)
    assert put > 0 and call > 0


def test_zero_volatility_limits() -> None:
    itm_put = black76_price(forward=F, strike=F + 500.0, years=T, sigma=1e-9, rate=R, right=OptionRight.PE)
    assert math.isclose(itm_put, math.exp(-R * T) * 500.0, rel_tol=1e-6)
    otm_call = black76_price(forward=F, strike=F + 500.0, years=T, sigma=1e-9, rate=R, right=OptionRight.CE)
    assert otm_call == pytest.approx(0.0, abs=1e-9)


def test_finite_difference_greeks_match_analytic() -> None:
    greeks = black76_greeks(forward=F, strike=K, years=T, sigma=SIGMA, rate=R, right=OptionRight.CE)

    def price(f: float, t: float, s: float) -> float:
        return black76_price(forward=f, strike=K, years=t, sigma=s, rate=R, right=OptionRight.CE)

    h_f, h_t, h_s = F * 1e-5, T * 1e-3, SIGMA * 1e-3
    fd_delta = (price(F + h_f, T, SIGMA) - price(F - h_f, T, SIGMA)) / (2 * h_f)
    assert math.isclose(greeks.delta, fd_delta, rel_tol=1e-5, abs_tol=1e-6)

    fd_gamma = (price(F + h_f, T, SIGMA) - 2 * price(F, T, SIGMA) + price(F - h_f, T, SIGMA)) / (h_f**2)
    assert math.isclose(greeks.gamma, fd_gamma, rel_tol=1e-3, abs_tol=1e-8)

    fd_theta_annual = -(price(F, T + h_t, SIGMA) - price(F, T - h_t, SIGMA)) / (2 * h_t)
    assert math.isclose(greeks.theta_annual, fd_theta_annual, rel_tol=1e-4, abs_tol=1e-6)

    fd_vega_annual = (price(F, T, SIGMA + h_s) - price(F, T, SIGMA - h_s)) / (2 * h_s)
    assert math.isclose(greeks.vega, fd_vega_annual, rel_tol=1e-5, abs_tol=1e-6)


def test_iv_round_trip() -> None:
    premium = black76_price(forward=F, strike=K, years=T, sigma=SIGMA, rate=R, right=OptionRight.PE)
    solved = implied_vol(premium=premium, forward=F, strike=K, years=T, rate=R, right=OptionRight.PE)
    assert solved is not None
    assert math.isclose(solved, SIGMA, rel_tol=1e-4, abs_tol=1e-6)


def test_iv_outside_bounds_returns_none() -> None:
    assert implied_vol(premium=-1.0, forward=F, strike=K, years=T, rate=R, right=OptionRight.CE) is None
    assert (
        implied_vol(premium=F * 10, forward=F, strike=K, years=T, rate=R, right=OptionRight.CE) is None
    )


def test_synthetic_forward_consistency() -> None:
    call = black76_price(forward=F, strike=K, years=T, sigma=SIGMA, rate=R, right=OptionRight.CE)
    put = black76_price(forward=F, strike=K, years=T, sigma=SIGMA, rate=R, right=OptionRight.PE)
    rebuilt = synthetic_forward(strike=K, call=call, put=put, rate=R, years=T)
    assert math.isclose(rebuilt, F, rel_tol=1e-7, abs_tol=1e-4)


def test_decay_by_reprice_uses_one_clock() -> None:
    capture = decay_by_reprice(
        forward=F,
        strike=K,
        years=T,
        sigma=SIGMA,
        rate=R,
        right=OptionRight.CE,
        next_years=T - 1.0 / (24.0 * 365.0),
    )
    assert capture is not None and capture > 0
    assert decay_by_reprice(
        forward=F, strike=K, years=T, sigma=SIGMA, rate=R, right=OptionRight.CE, next_years=T + 0.01
    ) is None
