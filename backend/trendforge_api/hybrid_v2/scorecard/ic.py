"""Per-module IC scorecard with the kill rule: no IC means no beta.

A module whose IC confidence interval contains zero cannot contribute a beta
to any S4 model. In this milestone every module's IC is None (unknown), so
every beta admission returns 0.0. Admission is never automatic.
"""

from __future__ import annotations

MODULES = ("B1", "B2", "B3", "B4", "B5")

IC_TABLE: dict[str, float | None] = {module: None for module in MODULES}


def ic(module: str) -> float | None:
    """Rolling Spearman IC for one module; None = UNKNOWN = cannot vote."""
    return IC_TABLE.get(module)


def beta_admission(module: str) -> tuple[float, str]:
    """(beta, reason). Default kill: unknown IC admits beta 0.0 only."""
    value = IC_TABLE.get(module)
    if value is None:
        return 0.0, "IC_UNKNOWN_NO_BETA"
    return 0.0, "ADMISSION_NOT_IMPLEMENTED_IN_MILESTONE"
