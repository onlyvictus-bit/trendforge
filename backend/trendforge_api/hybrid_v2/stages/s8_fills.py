"""S8 fills stage. Rule text + flags only; no broker, no orders.

Cash: next-day open+slippage or first-30-min VWAP, never signal-day close.
Options: buy = mid + ½ spread; sell = mid − ½ spread; floor one tick per leg;
stress at 2× spread; never fo-bhavcopy settlement prices.
"""

from __future__ import annotations

FILL_RULES = {
    "cash": "next_day_open_or_first_30min_vwap",
    "options_buy": "mid_plus_half_spread",
    "options_sell": "mid_minus_half_spread",
    "spread_floor_ticks_per_leg": 1,
    "stress_multiplier": 2,
    "forbidden": ["signal_day_close", "fo_bhav_settlement"],
    "limit_slippage_max": 0.0015,
}
