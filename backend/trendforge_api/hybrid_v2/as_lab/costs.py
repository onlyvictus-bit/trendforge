"""Cost schedule for p_min / Kelly illustration. Default ILLUSTRATION_* only.

A dated cost config may replace the defaults later; 2024 STT is never
hard-coded as truth. Read rates from a config with effective dates.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ...selection.s4s5_compare import (
    ILLUSTRATION_B,
    ILLUSTRATION_C,
    ILLUSTRATION_Q,
    ILLUSTRATION_SE,
)

COST_SCHEDULE_VERSION = "ILLUSTRATION-1"


def default_cost_schedule() -> dict:
    return {
        "version": COST_SCHEDULE_VERSION,
        "label": "ILLUSTRATION_NOT_INDIAN_LIVE_STT",
        "effective_from": "1970-01-01",
        "payoff_b": ILLUSTRATION_B,
        "cost_c": ILLUSTRATION_C,
        "loss_q": ILLUSTRATION_Q,
        "se": ILLUSTRATION_SE,
    }


def load_cost_schedule(path: str | Path | None = None) -> dict:
    """Load a dated cost config, or the illustration defaults."""
    if path is None:
        return default_cost_schedule()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("cost schedule must be an object")
    for field in ("effective_from", "payoff_b", "cost_c", "loss_q", "se"):
        if field not in payload:
            raise ValueError(f"cost schedule missing {field}")
    date.fromisoformat(str(payload["effective_from"]))
    return payload


def p_min(*, b: float = ILLUSTRATION_B, c: float = ILLUSTRATION_C) -> float:
    """p_min = (1 + c) / (1 + b). Cost-derived, never chosen."""
    return (1.0 + c) / (1.0 + b)
