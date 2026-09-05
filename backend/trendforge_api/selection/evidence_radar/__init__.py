"""3rd-eye evidence radar: all inventory as typed slots, four WAIT horizons.

Slots are never votes. Boards are research displays. 0 CONFIRMED. qty=0.
"""

from .boards import (
    BoardEntryV1,
    EvidenceRadarV1,
    HorizonBoardsV1,
    RadarRowV1,
    build_evidence_radar,
)
from .catalog import (
    Authority,
    Grain,
    Horizon,
    SlotCatalog,
    SourceSlotCatalogEntry,
    build_slot_catalog,
)
from .coverage import CoverageReportV1, build_coverage
from .slots import SlotStatus, SourceSlotV1, fill_slots

__all__ = [
    "Authority",
    "BoardEntryV1",
    "CoverageReportV1",
    "EvidenceRadarV1",
    "Grain",
    "Horizon",
    "HorizonBoardsV1",
    "RadarRowV1",
    "SlotCatalog",
    "SlotStatus",
    "SourceSlotCatalogEntry",
    "SourceSlotV1",
    "build_coverage",
    "build_evidence_radar",
    "build_slot_catalog",
    "fill_slots",
]
