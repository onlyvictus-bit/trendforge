"""Official MWPL gate for F&O guidance.

Verified NSE mechanics (user-verified 2026-08-23; re-check pages if they
change): a scrip whose aggregate OI ends the day above 95% of its Market
Wide Position Limit is banned from the NEXT day (offsetting trades only;
increasing positions draws an NSCC penalty at T+1); normal trading
resumes only when OI falls to 80% or below; the trading system displays
a 60% alert at 10-minute intervals. The 80/90 colour bands are internal
risk conventions, not exchange states, and are always labelled as such.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)

BAN_THRESHOLD_PCT = 95.0
RESUME_THRESHOLD_PCT = 80.0
ALERT60_THRESHOLD_PCT = 60.0


class OfficialMwplState(StrEnum):
    BAN = "BAN"
    RESUME = "RESUME"
    ALERT60 = "ALERT60"
    MWPL_MISSING = "MWPL_MISSING"


class InternalBand(StrEnum):
    INTERNAL_SAFE = "INTERNAL_SAFE_BELOW_80"
    INTERNAL_YELLOW = "INTERNAL_YELLOW_80_90"
    INTERNAL_ORANGE = "INTERNAL_ORANGE_90_95"
    INTERNAL_RED = "INTERNAL_RED_AT_OR_ABOVE_95"


class MwplGateResult(BaseModel):
    model_config = MODEL_CONFIG

    official_state: OfficialMwplState
    oi_percent_of_mwpl: float | None = None
    in_ban_list: bool | None = None
    alert60_active: bool | None = None
    internal_band: str | None = None
    can_guide_fno: bool
    hard_block_code: str | None = None
    reason: str


def _internal_band(pct: float) -> str:
    if pct >= BAN_THRESHOLD_PCT:
        return InternalBand.INTERNAL_RED.value
    if pct >= 90.0:
        return InternalBand.INTERNAL_ORANGE.value
    if pct >= RESUME_THRESHOLD_PCT:
        return InternalBand.INTERNAL_YELLOW.value
    return InternalBand.INTERNAL_SAFE.value


def official_mwpl_state(
    *,
    oi_percent_of_mwpl: float | None,
    in_ban_list: bool | None,
) -> MwplGateResult:
    """Classify one symbol against official MWPL mechanics, fail-closed."""

    if in_ban_list:
        return MwplGateResult(
            official_state=OfficialMwplState.BAN,
            oi_percent_of_mwpl=oi_percent_of_mwpl,
            in_ban_list=True,
            alert60_active=None if oi_percent_of_mwpl is None else oi_percent_of_mwpl > ALERT60_THRESHOLD_PCT,
            internal_band=(
                None
                if oi_percent_of_mwpl is None
                else _internal_band(oi_percent_of_mwpl)
            ),
            can_guide_fno=False,
            hard_block_code="HARD_BLOCK_BAN_ADD",
            reason=(
                "Scrip is on the official F&O ban list. Only offsetting "
                "trades are legal; increasing a position draws an NSCC "
                "penalty recovered at T+1."
            ),
        )
    if oi_percent_of_mwpl is None:
        return MwplGateResult(
            official_state=OfficialMwplState.MWPL_MISSING,
            oi_percent_of_mwpl=None,
            in_ban_list=bool(in_ban_list) if in_ban_list is not None else None,
            alert60_active=None,
            internal_band=None,
            can_guide_fno=False,
            hard_block_code=None,
            reason=(
                "Official MWPL percentage artifact missing or unproven. "
                "Cash ranking may continue; F&O guidance stays WAIT."
            ),
        )
    if oi_percent_of_mwpl > BAN_THRESHOLD_PCT:
        return MwplGateResult(
            official_state=OfficialMwplState.BAN,
            oi_percent_of_mwpl=oi_percent_of_mwpl,
            in_ban_list=False,
            alert60_active=True,
            internal_band=_internal_band(oi_percent_of_mwpl),
            can_guide_fno=False,
            hard_block_code="HARD_BLOCK_BAN_ADD",
            reason=(
                "Aggregate OI ended the day above 95% of MWPL; the scrip "
                "is banned from the next trading day."
            ),
        )
    if oi_percent_of_mwpl > RESUME_THRESHOLD_PCT:
        return MwplGateResult(
            official_state=OfficialMwplState.ALERT60,
            oi_percent_of_mwpl=oi_percent_of_mwpl,
            in_ban_list=False,
            alert60_active=True,
            internal_band=_internal_band(oi_percent_of_mwpl),
            can_guide_fno=True,
            hard_block_code=None,
            reason=(
                "No ban declared. Trading system shows the 60% alert every "
                "10 minutes; OI readings near the cap lose information and "
                "the internal convention flags caution."
            ),
        )
    return MwplGateResult(
        official_state=OfficialMwplState.RESUME,
        oi_percent_of_mwpl=oi_percent_of_mwpl,
        in_ban_list=False,
        alert60_active=oi_percent_of_mwpl > ALERT60_THRESHOLD_PCT,
        internal_band=_internal_band(oi_percent_of_mwpl),
        can_guide_fno=True,
        hard_block_code=None,
        reason=(
            "Aggregate OI is at or below 80% of MWPL, the level at which "
            "normal trading officially resumes after any ban."
        ),
    )
