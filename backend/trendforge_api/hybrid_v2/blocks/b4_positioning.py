"""B4 derivative positioning package (adopted split: package, not a beta).

Output is SUPPORT / WEAKEN / CONFLICT / UNKNOWN only. The numeric z stays
UNKNOWN until File A R12 exists. B4 never changes the WITHOUT p-hat.
"""

from __future__ import annotations

from typing import Literal

from ...selection.r5_live import R5StructureRowV1
from ...selection.s4s5_compare import _package

B4Package = Literal["SUPPORT", "WEAKEN", "CONFLICT", "UNKNOWN"]

B4_WHY = ("B4_NUMERIC_UNKNOWN_NEEDS_R12",)


def b4_package(row: R5StructureRowV1 | None) -> B4Package:
    result: str = _package(row)
    return result  # type: ignore[return-value]


def b4_z(*, chain_present: bool = False) -> float | None:
    if not chain_present:
        return None
    return None
