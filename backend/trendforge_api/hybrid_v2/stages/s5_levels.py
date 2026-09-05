"""S5 levels stage. Labels only; T1/T2 need a prior_range width from R5."""

from __future__ import annotations

from ..blocks.b5_location import (
    B5_LABEL_STATE_LABEL_ONLY,
    B5_LABEL_STATE_WAIT_WIDTH,
    b5_location_labels,
)

s5_labels = b5_location_labels

__all__ = ["s5_labels", "B5_LABEL_STATE_LABEL_ONLY", "B5_LABEL_STATE_WAIT_WIDTH"]
