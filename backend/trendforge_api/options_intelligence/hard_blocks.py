"""Hard blocks: safety outranks every derivative observation.

Verified law (merged spec v2 L5 / prompt section 1):
- HARD_BLOCK_BAN_ADD: banned scrip; increasing a position draws an NSCC
  penalty recovered at T+1 (research UI shows the blocker; it never
  sends an order).
- HARD_BLOCK_PHYSICAL_DELIVERY: stock F&O ITM within T-2 sessions of the
  last-Tuesday monthly expiry forces share delivery at full margin.
- HARD_BLOCK_EVENT_EVE_NAKED_SHORT: no fresh naked shorts within T-1 of
  a named event (budget / RBI / results).
- HARD_BLOCK_SPREAD: bid/ask spread above limit makes exit cost dominate.
Broker margin is authority: absent a broker margin API the slot stays
WAIT_MARGIN_API and no SPAN estimate is invented.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)

DEFAULT_SPREAD_LIMIT_PCT = 8.0
WAIT_MARGIN_API = "WAIT_MARGIN_API"
WAIT_FEED_BACKOFF = "WAIT_FEED_BACKOFF"


class Blocker(BaseModel):
    model_config = MODEL_CONFIG

    code: str
    message: str
    scope: str


def evaluate_hard_blocks(
    *,
    symbol: str,
    in_ban_list: bool = False,
    stock_fno_itm_near_expiry: bool | None = None,
    event_eve_naked_short: bool = False,
    max_spread_pct: float | None = None,
    spread_limit_pct: float = DEFAULT_SPREAD_LIMIT_PCT,
) -> tuple[Blocker, ...]:
    blockers: list[Blocker] = []
    if in_ban_list:
        blockers.append(
            Blocker(
                code="HARD_BLOCK_BAN_ADD",
                message=(
                    f"{symbol} is on the F&O ban list. Any position increase "
                    "draws an NSCC penalty recovered at T+1."
                ),
                scope="REGULATORY",
            )
        )
    if stock_fno_itm_near_expiry:
        blockers.append(
            Blocker(
                code="HARD_BLOCK_PHYSICAL_DELIVERY",
                message=(
                    "Stock F&O position is ITM within T-2 sessions of the "
                    "last-Tuesday expiry; holding it forces physical share "
                    "delivery at full-value margin."
                ),
                scope="SETTLEMENT",
            )
        )
    if event_eve_naked_short:
        blockers.append(
            Blocker(
                code="HARD_BLOCK_EVENT_EVE_NAKED_SHORT",
                message=(
                    "Named event within one trading day. Fresh naked short "
                    "premium is blocked; defined-risk structures stay "
                    "research-visible."
                ),
                scope="EVENT_RISK",
            )
        )
    if max_spread_pct is not None and max_spread_pct > spread_limit_pct:
        blockers.append(
            Blocker(
                code="HARD_BLOCK_SPREAD",
                message=(
                    f"Chain spread {max_spread_pct}% exceeds the "
                    f"{spread_limit_pct}% research limit; exit cost can "
                    "dominate any modeled edge."
                ),
                scope="LIQUIDITY",
            )
        )
    return tuple(blockers)
