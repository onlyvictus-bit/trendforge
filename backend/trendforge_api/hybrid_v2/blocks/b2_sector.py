"""B2 sector block. STUB until an official sector last-good exists."""

from __future__ import annotations

B2_WHY = ("B2_WAIT_OFFICIAL_SECTOR_LAST_GOOD",)


def b2_z(*, sector_rs: list[float] | None = None) -> float | None:
    if not sector_rs:
        return None
    return None
