"""File A dual data-lane switch: FREE_OFFICIAL (default) vs OPENALGO_RO."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "trendforge.data-lane.v1"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

Lane = Literal["FREE_OFFICIAL", "OPENALGO_RO"]
IntradayMode = Literal["ON_FREE", "OFF", "OPENALGO"]


class DataLaneStateV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    lane: Lane = "FREE_OFFICIAL"
    effective_lane: Lane = "FREE_OFFICIAL"
    open_algo_state: str = "ABSENT"
    blocker: str | None = None
    intraday_mode: IntradayMode = "OFF"
    intraday_reason: str = "WAIT_NO_FREE_INTRADAY"
    tried_source_keys: tuple[str, ...] = ()
    can_confirm: bool = False
    executable: bool = False


def resolve_lane(
    *,
    env_lane: str | None = None,
    openalgo_enabled: str | None = None,
    capability_state: str | None = None,
) -> DataLaneStateV1:
    """Resolve effective data lane. First-wins: env > default FREE_OFFICIAL."""
    lane: Lane = "FREE_OFFICIAL"
    blocker: str | None = None
    oa_state = capability_state or "ABSENT"

    if env_lane == "OPENALGO_RO":
        if openalgo_enabled != "1":
            blocker = "WAIT_OPENALGO_ABSENT"
        elif oa_state == "REJECTED":
            blocker = "WAIT_OPENALGO_FORBIDDEN"
        elif oa_state != "SHADOW_LIVE":
            blocker = "WAIT_OPENALGO_ABSENT"
        else:
            lane = "OPENALGO_RO"

    return DataLaneStateV1(
        lane="FREE_OFFICIAL",
        effective_lane=lane,
        open_algo_state=str(oa_state),
        blocker=blocker,
        can_confirm=False,
        executable=False,
    )
