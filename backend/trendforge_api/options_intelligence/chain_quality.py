"""Chain quality gate: spread, crossed books and completeness.

A strike ladder is only shown after the same-expiry snapshot passes this
gate; otherwise the room stays WAIT_CHAIN. Spread percentage above the
hero-zero limit is a HARD BLOCK for paper guidance, not a warning.
"""

from __future__ import annotations

from math import isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)

DEFAULT_SPREAD_LIMIT_PCT = 8.0


class StrikeQuote(BaseModel):
    model_config = MODEL_CONFIG

    expiry: str
    strike: float = Field(gt=0)
    right: str
    bid: float | None = Field(default=None, ge=0)
    ask: float | None = Field(default=None, ge=0)
    ltp: float | None = Field(default=None, ge=0)
    open_interest: float = Field(ge=0)
    volume: float = Field(ge=0)
    implied_volatility: float | None = None


class ChainQualityResult(BaseModel):
    model_config = MODEL_CONFIG

    state: str
    row_count: int = Field(ge=0)
    complete_strikes: int = Field(ge=0)
    completeness: float = Field(ge=0, le=1)
    crossed_rows: int = Field(ge=0)
    max_spread_pct: float | None = None
    reasons: tuple[str, ...] = ()
    hard_block_code: str | None = None


def _quote_mid_spread_pct(row: StrikeQuote) -> float | None:
    if row.bid is None or row.ask is None or row.bid <= 0 or row.ask <= 0:
        return None
    mid = 0.5 * (row.bid + row.ask)
    if mid <= 0:
        return None
    return (row.ask - row.bid) / mid * 100.0


def assess_chain(
    rows: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    *,
    expected_strike_count: int,
    spread_limit_pct: float = DEFAULT_SPREAD_LIMIT_PCT,
) -> ChainQualityResult:
    quotes: list[StrikeQuote] = []
    crossed = 0
    invalid = 0
    for raw in rows:
        try:
            quote = StrikeQuote.model_validate(raw)
        except Exception:
            invalid += 1
            continue
        if quote.bid is not None and quote.ask is not None and quote.ask < quote.bid:
            crossed += 1
        quotes.append(quote)

    strikes = {q.strike for q in quotes}
    sides = {
        strike: {q.right for q in quotes if q.strike == strike} for strike in strikes
    }
    complete = {s for s, pair in sides.items() if pair == {"CE", "PE"}}
    completeness = (
        min(len(complete) / expected_strike_count, 1.0) if expected_strike_count > 0 else 0.0
    )
    spreads = [pct for q in quotes if (pct := _quote_mid_spread_pct(q)) is not None]
    max_spread = round(max(spreads), 4) if spreads else None

    reasons: list[str] = []
    block: str | None = None
    if invalid:
        reasons.append(f"INVALID_ROWS_{invalid}")
    if crossed:
        reasons.append("CROSSED_BOOK")
    if len(complete) < expected_strike_count:
        reasons.append("INCOMPLETE_STRIKE_SET")
    if not quotes:
        reasons.append("EMPTY_CHAIN")

    ok = (
        quotes
        and not crossed
        and len(complete) >= expected_strike_count
        and max_spread is not None
        and max_spread <= spread_limit_pct
    )
    eod_oi = (
        quotes
        and not crossed
        and len(complete) >= expected_strike_count
        and max_spread is None
    )
    if quotes and not crossed and max_spread is not None and max_spread > spread_limit_pct:
        reasons.append(f"SPREAD_ABOVE_{spread_limit_pct:g}_PCT")
        block = "HARD_BLOCK_SPREAD"
    if eod_oi:
        reasons.append("EOD_NO_BOOK")
        state = "CHAIN_EOD_OI"
    elif ok:
        state = "CHAIN_OK"
    else:
        state = "WAIT_CHAIN"
    return ChainQualityResult(
        state=state,
        row_count=len(quotes),
        complete_strikes=len(complete),
        completeness=round(completeness, 4),
        crossed_rows=crossed,
        max_spread_pct=max_spread,
        reasons=tuple(reasons),
        hard_block_code=block,
    )


def all_finite(values: list[float]) -> bool:
    return all(isfinite(v) for v in values)
