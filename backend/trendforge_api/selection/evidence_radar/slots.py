"""Stage A: fill one typed slot status per R1 source key. Silence is a bug."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .catalog import Grain, SlotCatalog, SourceSlotCatalogEntry
from ..inventory_source_bundle import InventorySourceBundleV1

SCHEMA_VERSION = "trendforge.evidence-radar-coverage.v1"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class SlotStatus(str, Enum):
    PRESENT = "PRESENT"
    VALID_EMPTY = "VALID_EMPTY"
    STALE = "STALE"
    WRONG_GRAIN = "WRONG_GRAIN"
    BLOCKED = "BLOCKED"
    UNPROVEN = "UNPROVEN"
    NOT_NORMALIZED = "NOT_NORMALIZED"
    COMPANION_ONLY = "COMPANION_ONLY"
    NOT_APPLICABLE_TO_HORIZON = "NOT_APPLICABLE_TO_HORIZON"


_USABILITY_TO_STATUS = {
    "USABLE_CURRENT": SlotStatus.PRESENT,
    "VALID_EMPTY_CURRENT": SlotStatus.VALID_EMPTY,
    "STALE_LAST_GOOD": SlotStatus.STALE,
    "STALE_DATA": SlotStatus.STALE,
    "CATALOG_ONLY": SlotStatus.NOT_NORMALIZED,
    "BLOCKED": SlotStatus.BLOCKED,
    "FETCH_FAILED": SlotStatus.UNPROVEN,
    "PARSE_FAILED": SlotStatus.NOT_NORMALIZED,
    "SCHEMA_MISMATCH": SlotStatus.NOT_NORMALIZED,
    "MISSING_REQUIRED_PARAMETER": SlotStatus.UNPROVEN,
    "NOT_APPLICABLE": SlotStatus.NOT_APPLICABLE_TO_HORIZON,
}

# Sources whose last-good is archived raw but whose normalized FII% parser is
# still pending stay honestly NOT_NORMALIZED instead of pretending PRESENT.
_NOT_NORMALIZED_KEYS = ("nse_shareholding_pattern", "bse_shareholding_pattern")


class SourceSlotV1(BaseModel):
    model_config = MODEL_CONFIG

    source_key: str
    status: SlotStatus
    reason: str
    family: str
    correlation_group: str
    decision_jobs: tuple[str, ...] = ()
    calculate: str
    data_date: str | None = None


class CoverageReportV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    bundle_id: str
    bundle_hash: str
    built_at: datetime
    totalJobs: int = Field(ge=0)
    represented: int = Field(ge=0)
    skippedCount: int = 0
    unknownCount: int = Field(ge=0)
    presentCount: int = Field(ge=0, default=0)
    notNormalizedKeys: tuple[str, ...] = ()
    slots: tuple[SourceSlotV1, ...]

    @model_validator(mode="after")
    def nothing_skipped(self) -> "CoverageReportV1":
        if self.skippedCount != 0:
            raise ValueError("evidence radar may never skip a source key")
        if self.totalJobs != len(self.slots):
            raise ValueError("coverage total does not match slot count")
        if self.represented != sum(
            slot.status is not SlotStatus.NOT_APPLICABLE_TO_HORIZON
            for slot in self.slots
        ):
            raise ValueError("coverage represented count mismatch")
        return self


def _status_for(entry: SourceSlotCatalogEntry, record) -> tuple[SlotStatus, str]:
    usability = str(
        getattr(record.usability_state, "value", record.usability_state)
    ).upper()
    if entry.source_key in _NOT_NORMALIZED_KEYS:
        return (
            SlotStatus.NOT_NORMALIZED,
            "Last-good exists but the normalized FII%/prior-quarter parser is pending.",
        )
    status = _USABILITY_TO_STATUS.get(usability)
    if status is None:
        return (
            SlotStatus.UNPROVEN,
            f"Unmapped usability state {usability}; treated fail-closed as unproven.",
        )
    return status, record.reason or usability


def fill_slots(
    bundle: InventorySourceBundleV1, catalog: SlotCatalog, *, built_at: datetime | None = None
) -> CoverageReportV1:
    records_by_key = {record.source_key: record for record in bundle.source_records}
    slots: list[SourceSlotV1] = []
    for entry in catalog.entries:
        record = records_by_key.get(entry.source_key)
        if record is None:
            slots.append(
                SourceSlotV1(
                    source_key=entry.source_key,
                    status=SlotStatus.UNPROVEN,
                    reason="R1 catalog entry had no matching evidence record.",
                    family=entry.evidence_family,
                    correlation_group=entry.correlation_group,
                    decision_jobs=entry.decision_jobs,
                    calculate=entry.calculate,
                )
            )
            continue
        status, reason = _status_for(entry, record)
        if entry.grain is Grain.COMPANION:
            status = SlotStatus.COMPANION_ONLY
        slots.append(
            SourceSlotV1(
                source_key=entry.source_key,
                status=status,
                reason=reason,
                family=entry.evidence_family,
                correlation_group=entry.correlation_group,
                decision_jobs=entry.decision_jobs,
                calculate=entry.calculate,
                data_date=record.data_date.isoformat() if record.data_date else None,
            )
        )
    unknown_statuses = {
        SlotStatus.VALID_EMPTY,
        SlotStatus.STALE,
        SlotStatus.WRONG_GRAIN,
        SlotStatus.BLOCKED,
        SlotStatus.UNPROVEN,
        SlotStatus.NOT_NORMALIZED,
        SlotStatus.COMPANION_ONLY,
        SlotStatus.NOT_APPLICABLE_TO_HORIZON,
    }
    return CoverageReportV1(
        bundle_id=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        built_at=built_at or datetime.now(UTC),
        totalJobs=len(slots),
        represented=sum(slot.status is not SlotStatus.NOT_APPLICABLE_TO_HORIZON for slot in slots),
        skippedCount=0,
        unknownCount=sum(slot.status in unknown_statuses for slot in slots),
        presentCount=sum(slot.status is SlotStatus.PRESENT for slot in slots),
        notNormalizedKeys=tuple(
            slot.source_key for slot in slots if slot.status is SlotStatus.NOT_NORMALIZED
        ),
        slots=tuple(slots),
    )


__all__ = [
    "SCHEMA_VERSION",
    "CoverageReportV1",
    "SlotStatus",
    "SourceSlotV1",
    "fill_slots",
]

