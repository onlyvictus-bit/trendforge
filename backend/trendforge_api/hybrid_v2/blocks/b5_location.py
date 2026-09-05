"""B5 price geometry / location. Labels only; never votes on p-hat.

T1 = entry + 0.382 x R and T2 = entry + 0.618 x R with R = prior_range from
R5 metrics when present. If the width is missing the label is kept without a
fabricated number (never invent 3.82% of price).
"""

from __future__ import annotations

from ...selection.r5_live import R5StructureRowV1

B5_LABEL_STATE_LABEL_ONLY = "LABEL_ONLY"
B5_LABEL_STATE_WAIT_WIDTH = "WAIT_WIDTH"


def b5_location_labels(
    row: R5StructureRowV1 | None,
    *,
    prior_range_width: float | None = None,
) -> dict[str, str]:
    """Labels only. LABEL_ONLY requires the actual R width; an entry level
    alone is never enough — T1/T2 stay width-waiting without it."""
    del row  # reference level surfaces via the S4/S5 result entry_level only
    if prior_range_width is None:
        return {
            "state": B5_LABEL_STATE_WAIT_WIDTH,
            "entry": "entry PENDING — structure box not on this proxy row",
            "t1": "T1=entry+0.382×R (R=prior_range; width not on this proxy row)",
            "t2": "T2=entry+0.618×R (R=prior_range; width not on this proxy row)",
        }
    return {
        "state": B5_LABEL_STATE_LABEL_ONLY,
        "entry": "LABEL_ONLY entry zone (structure box reference)",
        "t1": "T1=entry+0.382×R (R=prior_range)",
        "t2": "T2=entry+0.618×R (R=prior_range)",
    }
