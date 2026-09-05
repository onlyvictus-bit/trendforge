"""Nothing-skipped coverage report for GET /evidence-radar/coverage."""

from __future__ import annotations

from .catalog import SlotCatalog, build_slot_catalog
from ..inventory_source_bundle import InventorySourceBundleV1
from .slots import CoverageReportV1, SlotStatus, SourceSlotV1, fill_slots

__all__ = [
    "CoverageReportV1",
    "SlotCatalog",
    "SlotStatus",
    "SourceSlotV1",
    "build_coverage",
    "build_slot_catalog",
]


def build_coverage(
    bundle: InventorySourceBundleV1 | None = None,
) -> tuple[CoverageReportV1, SlotCatalog]:
    from ..inventory_source_bundle import latest_inventory_source_bundle

    r1 = bundle or latest_inventory_source_bundle()
    if r1 is None:
        raise ValueError("WAIT_RADAR_SPINE_NOT_READY")
    catalog = build_slot_catalog(r1)
    return fill_slots(r1, catalog), catalog

