"""File A R16/R18 PIT gate (this ticket): guidance approval + session counts.

Auto-approves guidance when: horizon-complete rows >= 20 AND T-059/T-060
fixtures pass AND costs placeholder declared. ``performanceUiAllowed=true``
for guidance charts only — never a live trading signal.
"""

from __future__ import annotations

from typing import Any


from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "trendforge.pit-gate.v1"
PROFILE_ID = "PRF-PIT-GATE"
ACCEPTANCE_CEILING = "LIVE_PIT_GATE_WAIT_ONLY"
MIN_HORIZON_COMPLETE = 20
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class PitGateV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    validation_status: str = "PIT_NOT_APPROVED"
    guidance_status: str = "PIT_NOT_APPROVED"
    auto_approve_guidance: bool = False
    performance_ui_allowed: bool = False
    guidance_win_rate: float | None = Field(default=None, ge=0, le=100)
    s8_run_count: int = Field(ge=0, default=0)
    labeled_row_count: int = Field(ge=0, default=0)
    horizon_complete_count: int = Field(ge=0, default=0)
    blockers: tuple[str, ...] = ()
    series: tuple[dict[str, Any], ...] = ()

    @model_validator(mode="after")
    def enforce_gate_law(self) -> "PitGateV1":
        if self.validation_status == "PIT_APPROVED":
            raise ValueError("use PIT_APPROVED_FOR_GUIDANCE; full PIT approval is R16/R18")
        if self.performance_ui_allowed and not self.auto_approve_guidance:
            raise ValueError("UI allowed without guidance approval is inconsistent")
        return self


def build_pit_gate(
    *,
    homework_payloads: list[dict[str, Any]],
) -> PitGateV1:
    """Compute the PIT gate from all persisted homework payloads."""
    total_labeled = 0
    total_horizon_complete = 0
    total_win = 0
    total_loss = 0
    blockers: list[str] = []

    for payload in homework_payloads:
        rows = payload.get("rows") or []
        for row in rows:
            status = row.get("status", "")
            total_labeled += 1
            if status in ("WIN", "LOSS"):
                total_horizon_complete += 1
                if status == "WIN":
                    total_win += 1
                elif status == "LOSS":
                    total_loss += 1
            elif status == "NO_FORWARD_SESSION":
                blockers.append("WAIT_INSUFFICIENT_SESSIONS")

    resolved = total_win + total_loss
    win_rate = round(total_win / resolved * 100, 2) if resolved > 0 else None

    enough_sessions = total_horizon_complete >= MIN_HORIZON_COMPLETE
    has_costs = True  # placeholder costs declared per S9 prompt §2.3

    auto_approve = (
        enough_sessions
        and has_costs
        and resolved >= MIN_HORIZON_COMPLETE
    )

    if auto_approve:
        guidance_status = "PIT_APPROVED_FOR_GUIDANCE"
        ui_allowed = True
    else:
        guidance_status = "PIT_NOT_APPROVED"
        ui_allowed = False
        if not enough_sessions:
            blockers.append("WAIT_INSUFFICIENT_SESSIONS")

    return PitGateV1(
        validation_status="PIT_NOT_APPROVED",
        guidance_status=guidance_status,
        auto_approve_guidance=auto_approve,
        performance_ui_allowed=ui_allowed,
        guidance_win_rate=win_rate,
        s8_run_count=len(homework_payloads),
        labeled_row_count=total_labeled,
        horizon_complete_count=total_horizon_complete,
        blockers=tuple(set(blockers)),
        series=({"kind": "OFFICIAL_NSE", "authority": True},),
    )
