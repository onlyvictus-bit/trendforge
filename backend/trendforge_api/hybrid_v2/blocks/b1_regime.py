"""B1 regime/market block. STUB until official index + VIX last-good exists.

A5 index context is not a 124th voter; B1 stays UNKNOWN rather than inventing
a Nifty close or a VIX percentile.
"""

from __future__ import annotations

B1_WHY = ("B1_WAIT_OFFICIAL_INDEX_VIX",)


def b1_z(
    *,
    nifty_close: float | None = None,
    vix_percentile: float | None = None,
    term_structure_slope: float | None = None,
) -> float | None:
    if nifty_close is None or vix_percentile is None:
        return None
    return None
