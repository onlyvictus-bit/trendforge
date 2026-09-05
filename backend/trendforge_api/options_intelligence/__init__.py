"""Options intelligence package for the four OI/options research rooms.

Contract owner: docs/fable/remaining_build/OI_OPTIONS_ROOMS_GLM_PROMPT.md
(merged audit spec v2, sections L0-L7). Observation-first futures OI
quadrants, official MWPL/ban gates, Black-76 pricing with a mandatory
test suite, append-only IV/chain recorders, hard blocks and frozen
guidance JSON. Nothing here can emit File A CONFIRMED.
"""

from .quadrant import ObservationCode, QuadrantResult, observation_quadrant
from .mwpl_gate import MwplGateResult, official_mwpl_state

__all__ = [
    "ObservationCode",
    "QuadrantResult",
    "observation_quadrant",
    "MwplGateResult",
    "official_mwpl_state",
]
