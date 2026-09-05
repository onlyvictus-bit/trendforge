"""S7 size stage. Kelly ILLUSTRATION only; capped at 2%; never qty."""

from __future__ import annotations

from ...selection.s4s5_compare import _kelly


def kelly_illustration(p_hat: float) -> float:
    """Quarter-Kelly illustration on p̂ with SE haircut, capped at 0.02."""
    return _kelly(p_hat)
