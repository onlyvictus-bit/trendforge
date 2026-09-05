"""S6 vehicle stage. VRP / gamma / margin stay UNKNOWN_NEEDS_R12.

VRP = IV²_ATM(T) − E[RV²(T)] cannot be computed without the official chain
(File A R12) and a 5-min RV history (V3 upgrade 30 recorder). IV Rank is never
VRP. No Yahoo. No invented Greeks.
"""

from __future__ import annotations

S6_VEHICLE_STATUS = "UNKNOWN_NEEDS_R12"
S6_WHY = (
    "S6_UNKNOWN_NEEDS_R12_OFFICIAL_CHAIN",
    "VRP_UNKNOWN_NEEDS_5MIN_RV_HISTORY",
)


def s6_vehicle_status() -> tuple[str, tuple[str, ...]]:
    return S6_VEHICLE_STATUS, S6_WHY
