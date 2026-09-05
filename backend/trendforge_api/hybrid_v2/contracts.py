"""Shared Hybrid V2 overlay DTOs, ceiling constants and the UNKNOWN policy.

Nothing in this package may introduce a tradeable number. Levels appear only
as LABEL_ONLY strings; Kelly is an illustration capped at 2%; S6 is always
UNKNOWN_NEEDS_R12 in this milestone.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ..selection.contracts import SelectionState
from ..selection.s4s5_compare import S4S5FormulaResultV1

SCHEMA_VERSION = "trendforge.hybrid-v2-overlay.v1"
PROFILE_ID = "PRF-HYBRID-V2-OVERLAY"
PROFILE_VERSION = "1.0.0"
CEILING = "RESEARCH_PROXY_NOT_CALIBRATED"
S6_VEHICLE_STATUS = "UNKNOWN_NEEDS_R12"
MANDATORY_WARNING = (
    "HYBRID_V2_OVERLAY_NOT_FILE_A. Not R2-B. Not CONFIRMED. Not size. "
    "S4/S5 both families kept."
)

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

AsStatus = Literal["USABLE", "UNKNOWN", "STALE", "WAIT_CA"]
B4Package = Literal["SUPPORT", "WEAKEN", "CONFLICT", "UNKNOWN"]
S5LabelState = Literal["LABEL_ONLY", "WAIT_WIDTH"]


class HybridOverlayRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    instrument_id: str | None = None
    r2_public_state: SelectionState
    r5_structure_state: SelectionState
    r14_ca_state: str
    research_state: SelectionState = SelectionState.WAIT
    display_order: int = Field(gt=0)
    b1_z: float | None = None
    b2_z: float | None = None
    b3_z: float | None = None
    b4_z: float | None = None
    b5_z: float | None = None
    with_s4s5: S4S5FormulaResultV1
    without_s4s5: S4S5FormulaResultV1
    s6_vehicle_status: Literal["UNKNOWN_NEEDS_R12"] = S6_VEHICLE_STATUS
    kelly_illustration: float = Field(ge=0, le=0.02)
    as_delivery_z: float | None = None
    as_status: AsStatus = "UNKNOWN"
    b4_package: B4Package = "UNKNOWN"
    s5_label_state: S5LabelState = "WAIT_WIDTH"
    s5_entry_label: str
    s5_t1_label: str
    s5_t2_label: str
    why_wait: tuple[str, ...] = Field(min_length=1)
    r1_bundle_hash: str
    r2_run_hash: str
    r14_run_hash: str | None = None
    r5_run_hash: str | None = None

    @model_validator(mode="after")
    def overlay_ceiling(self) -> "HybridOverlayRowV1":
        if self.research_state is SelectionState.CONFIRMED:
            raise ValueError("overlay rows cannot be CONFIRMED")
        if self.r2_public_state is SelectionState.CONFIRMED:
            raise ValueError("overlay cannot copy a CONFIRMED R2 state")
        if self.b5_z is not None:
            raise ValueError("B5 is location only and never votes on p-hat")
        return self


class HybridOverlayBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    calibration: str = CEILING
    can_unlock_confirmed: bool = False
    executable: bool = False
    source_activation_ready: bool = False
    trading_date: str
    decision_at: datetime
    row_count: int = Field(ge=0)
    rows: tuple[HybridOverlayRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def research_ceiling(self) -> "HybridOverlayBatchV1":
        if self.can_unlock_confirmed or self.executable or self.source_activation_ready:
            raise ValueError("hybrid overlay cannot activate, trade or confirm")
        if any(row.research_state is SelectionState.CONFIRMED for row in self.rows):
            raise ValueError("overlay rows cannot be CONFIRMED")
        if any(row.s6_vehicle_status != S6_VEHICLE_STATUS for row in self.rows):
            raise ValueError("S6 vehicle stays UNKNOWN_NEEDS_R12 in this milestone")
        if MANDATORY_WARNING not in self.warnings:
            raise ValueError("overlay batch must carry the mandatory ceiling warning")
        return self
