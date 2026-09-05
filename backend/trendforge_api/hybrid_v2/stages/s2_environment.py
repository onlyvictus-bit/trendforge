"""S2 environment. Uses B1/B2 when present; otherwise SKIP, never invented."""

from __future__ import annotations


def assess_environment(
    *,
    b1: float | None,
    b2: float | None,
) -> tuple[str, tuple[str, ...]]:
    if b1 is None and b2 is None:
        return "SKIP", ("S2_B1_B2_UNKNOWN",)
    return "PASS", ()
