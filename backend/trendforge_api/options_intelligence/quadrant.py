"""Observation-first futures price/OI quadrant codes.

Law (merged spec v2 L3): the four observable combinations of closed-price
direction and futures open-interest direction are observations. Textbook
names such as "long buildup" are interpretations and must never replace
the code as a fact. Equality, missing prior OI, expiry mismatch or
roll-window pollution all degrade to UNKNOWN instead of a direction.
"""

from __future__ import annotations

from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ObservationCode(StrEnum):
    PRICE_UP_OI_UP = "PRICE_UP_OI_UP"
    PRICE_DOWN_OI_UP = "PRICE_DOWN_OI_UP"
    PRICE_UP_OI_DOWN = "PRICE_UP_OI_DOWN"
    PRICE_DOWN_OI_DOWN = "PRICE_DOWN_OI_DOWN"
    UNKNOWN = "UNKNOWN"


LEGACY_CODES: dict[str, str] = {
    ObservationCode.PRICE_UP_OI_UP.value: "OI_RISE_PRICE_RISE",
    ObservationCode.PRICE_DOWN_OI_UP.value: "OI_RISE_PRICE_FALL",
    ObservationCode.PRICE_UP_OI_DOWN.value: "OI_FALL_PRICE_RISE",
    ObservationCode.PRICE_DOWN_OI_DOWN.value: "OI_FALL_PRICE_FALL",
}


def legacy_code(code: ObservationCode) -> str | None:
    """Old FTR-020 display alias; kept only so history stays readable."""
    if code is ObservationCode.UNKNOWN:
        return None
    return LEGACY_CODES[code.value]


class QuadrantResult(BaseModel):
    model_config = MODEL_CONFIG

    code: ObservationCode
    legacy_code: str | None = None
    price_change_pct: float | None = None
    oi_change_pct: float | None = None
    interval: str
    reasons: tuple[str, ...] = ()
    interpretation: str = (
        "Observed co-movement of closed price and futures OI on the aligned "
        "interval. Consistent with several positioning stories; not a fact "
        "about who initiated."
    )
    authority: str = "CONTEXT_ONLY"
    can_confirm: bool = False


def observation_quadrant(
    *,
    close: float,
    previous_close: float,
    open_interest: int,
    prior_open_interest: int | None,
    interval: str = "EOD",
    same_expiry: bool = True,
    roll_window: bool = False,
) -> QuadrantResult:
    """Classify one aligned price/OI observation, fail-closed to UNKNOWN."""

    reasons: list[str] = []
    if not same_expiry:
        reasons.append("EXPIRY_MISMATCH")
    if roll_window:
        reasons.append("ROLL_WINDOW_POLLUTION")
    if reasons:
        # Identity/pollution failures degrade to UNKNOWN before any direction.
        return QuadrantResult(code=ObservationCode.UNKNOWN, interval=interval, reasons=tuple(reasons))
    if prior_open_interest is None:
        reasons.append("PRIOR_OI_MISSING")
        return QuadrantResult(
            code=ObservationCode.UNKNOWN,
            interval=interval,
            reasons=tuple(reasons),
        )
    if prior_open_interest <= 0:
        reasons.append("PRIOR_OI_NON_POSITIVE")
        return QuadrantResult(
            code=ObservationCode.UNKNOWN,
            interval=interval,
            reasons=tuple(reasons),
        )
    values = (close, previous_close, float(open_interest))
    if not all(isfinite(value) for value in values):
        reasons.append("NON_FINITE_INPUT")
        return QuadrantResult(
            code=ObservationCode.UNKNOWN,
            interval=interval,
            reasons=tuple(reasons),
        )
    price_delta = close - previous_close
    oi_delta = open_interest - prior_open_interest
    if price_delta == 0 or oi_delta == 0:
        # Equality is not a direction; the textbook quadrant needs both signs.
        if price_delta == 0:
            reasons.append("PRICE_EQUALITY_NOT_DIRECTION")
        if oi_delta == 0:
            reasons.append("OI_EQUALITY_NOT_DIRECTION")
        return QuadrantResult(
            code=ObservationCode.UNKNOWN,
            price_change_pct=_pct(price_delta, previous_close),
            oi_change_pct=_pct(oi_delta, float(prior_open_interest)),
            interval=interval,
            reasons=tuple(reasons),
        )
    if price_delta > 0 and oi_delta > 0:
        code = ObservationCode.PRICE_UP_OI_UP
    elif price_delta < 0 and oi_delta > 0:
        code = ObservationCode.PRICE_DOWN_OI_UP
    elif price_delta > 0 and oi_delta < 0:
        code = ObservationCode.PRICE_UP_OI_DOWN
    else:
        code = ObservationCode.PRICE_DOWN_OI_DOWN
    return QuadrantResult(
        code=code,
        legacy_code=legacy_code(code),
        price_change_pct=_pct(price_delta, previous_close),
        oi_change_pct=_pct(oi_delta, float(prior_open_interest)),
        interval=interval,
        reasons=tuple(reasons),
    )


def _pct(delta: float, base: float) -> float | None:
    if base <= 0 or not isfinite(base):
        return None
    return round(delta / abs(base) * 100.0, 4)
