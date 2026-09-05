"""Option-chain surface metrics: PCR, walls, max pain, unsigned gamma.

PCR with a zero call-OI denominator is UNKNOWN, never 0 or infinity.
Walls are OI concentration candidates that only become useful when they
persist and price reacts; they carry first_known_at/touches/persistence
fields so a later backtest can check non-repainting behaviour. Gamma is
an UNSIGNED cash-gamma proxy: public OI cannot reveal dealer inventory,
so dealer-GEX claims are forbidden (GEX_PROXY_ASSUMPTION_DEPENDENT).
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .chain_quality import StrikeQuote
from .pricing import OptionRight, black76_greeks

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def pcr_oi(*, put_oi: float, call_oi: float) -> float | None:
    if call_oi is None or put_oi is None or call_oi <= 0:
        return None  # UNKNOWN, not 0 and not infinity
    return round(put_oi / call_oi, 4)


class WallCandidate(BaseModel):
    model_config = MODEL_CONFIG

    role: str
    strike: float
    open_interest: float
    first_known_at: str
    touches: int = Field(default=0, ge=0)
    persistence_snapshots: int = Field(default=1, ge=1)
    oi_change_since_previous: float | None = None
    unwind_flag: bool = False


def _top_oi(rows: list[StrikeQuote], right: OptionRight) -> StrikeQuote | None:
    candidates = [row for row in rows if row.right == right.value]
    if not candidates:
        return None
    return max(candidates, key=lambda r: (r.open_interest, -r.strike if right is OptionRight.CE else r.strike))


def walls(
    rows: list[StrikeQuote],
    *,
    previous_walls: dict[str, float] | None = None,
    known_at: datetime | None = None,
) -> tuple[WallCandidate | None, WallCandidate | None]:
    """Call wall = resistance candidate; put wall = support candidate."""
    previous = previous_walls or {}
    stamp = (known_at or datetime.now(timezone.utc)).isoformat()
    call_row = _top_oi(rows, OptionRight.CE)
    put_row = _top_oi(rows, OptionRight.PE)

    def build(row: StrikeQuote | None, role: str) -> WallCandidate | None:
        if row is None:
            return None
        prev_strike = previous.get(role)
        persisted = prev_strike == row.strike
        change = (
            None
            if prev_strike != row.strike or row.open_interest <= 0
            else None
        )
        return WallCandidate(
            role=role,
            strike=row.strike,
            open_interest=row.open_interest,
            first_known_at=stamp,
            touches=1 if persisted else 0,
            persistence_snapshots=2 if persisted else 1,
            oi_change_since_previous=change,
            unwind_flag=False,
        )

    return build(call_row, "CALL_WALL"), build(put_row, "PUT_WALL")


def max_pain_reference(
    rows: list[StrikeQuote], *, multiplier: float = 1.0
) -> float | None:
    strikes = sorted({row.strike for row in rows})
    ce = {r.strike: r.open_interest for r in rows if r.right == OptionRight.CE.value}
    pe = {r.strike: r.open_interest for r in rows if r.right == OptionRight.PE.value}
    if not strikes or (not ce and not pe):
        return None

    def pain(settlement: float) -> float:
        total = 0.0
        for strike, oi in ce.items():
            total += max(settlement - strike, 0.0) * oi
        for strike, oi in pe.items():
            total += max(strike - settlement, 0.0) * oi
        return total * multiplier

    best = min(strikes, key=lambda s: (pain(s), s))
    value = pain(best)
    return round(best, 2) if isfinite(value) else None


def unsigned_cash_gamma_per_strike(
    rows: list[StrikeQuote],
    *,
    forward: float,
    years: float,
    lot_size: float = 1.0,
) -> dict[float, float]:
    """Unsigned 1% cash-gamma proxy per strike. NEVER labeled dealer GEX."""
    out: dict[float, float] = {}
    for row in rows:
        sigma = row.implied_volatility
        if not sigma or years <= 0 or forward <= 0:
            out[row.strike] = 0.0 if not out.get(row.strike) else out[row.strike]
            continue
        greeks = black76_greeks(
            forward=forward,
            strike=row.strike,
            years=years,
            sigma=sigma / 100.0,
            rate=0.0,
            right=row.right,
        )
        contribution = abs(greeks.gamma) * row.open_interest * lot_size * forward * forward * 0.01
        existing = out.get(row.strike)
        out[row.strike] = round(contribution + (existing or 0.0), 4)
    return dict(sorted(out.items()))
