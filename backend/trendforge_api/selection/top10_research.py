"""Top-10 BUY/SELL research board over R6 enrichment stickers.

Display ranks only. This module:
- never emits CONFIRMED, quantity, entry, target, or stop
- drops hard-veto rows (REJECT, WAIT_CA, ban) from both boards
- reads direction only from the R2 `evidence_direction` field
- returns fewer than 10 when evidence does not exist (no third-party backfill)
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .contracts import EvidenceDirection, SelectionState, StateCeiling, stable_id
from .r6_live import (
    ACCEPTANCE_CEILING,
    MarketFiiChipV1,
    R6EnrichmentBatchV1,
    R6EnrichRowV1,
    build_r6_enrichment,
)

SCHEMA_VERSION = "trendforge.top10-research.v1"
PROFILE_ID = "PRF-TOP10-RESEARCH"
CALIBRATION = "RESEARCH_SHORTLIST_NOT_CONFIRMED"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)
BOARD_SIZE = 10


class Top10EntryV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    candidate_id: str
    board: str
    display_rank: int = Field(gt=0)
    display_score: float | None = None
    r2_public_state: SelectionState
    evidence_direction: EvidenceDirection
    ca_state: str
    gap_pct: float | None = None
    delivery_status: str
    delivery_pct: float | None = None
    deal_summary: str | None = None
    deal_tag: str | None = None
    mf_delta: str | None = None
    mf_month: str | None = None
    fo_package: str
    tags: tuple[str, ...] = ()
    why: tuple[str, ...] = ()
    why_unknown: tuple[str, ...] = ()
    research_state: SelectionState = SelectionState.WAIT
    can_unlock_confirmed: bool = False

    @model_validator(mode="after")
    def entry_is_not_confirmation(self) -> "Top10EntryV1":
        if self.research_state is not SelectionState.WAIT:
            raise ValueError("top10 entries are WAIT only")
        if self.can_unlock_confirmed:
            raise ValueError("top10 entries cannot unlock CONFIRMED")
        if self.board not in {"BUY", "SELL"}:
            raise ValueError("board must be BUY or SELL")
        return self


class Top10ResearchBoardV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    run_id: str
    run_hash: str
    r6_run_id: str
    r6_run_hash: str
    built_at: datetime
    state_ceiling: StateCeiling = StateCeiling.WAIT
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    calibration: str = CALIBRATION
    market_fii: MarketFiiChipV1
    buy: tuple[Top10EntryV1, ...] = ()
    sell: tuple[Top10EntryV1, ...] = ()
    vetoed_count: int = Field(ge=0, default=0)
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def board_is_not_confirmation(self) -> "Top10ResearchBoardV1":
        if len(self.buy) > BOARD_SIZE or len(self.sell) > BOARD_SIZE:
            raise ValueError(f"boards are capped at {BOARD_SIZE}")
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("top10 cannot activate sources or unlock CONFIRMED")
        for entry in (*self.buy, *self.sell):
            if entry.r2_public_state is SelectionState.REJECT:
                raise ValueError("rejected rows cannot appear on the boards")
            if entry.ca_state == "WAIT_CA":
                raise ValueError("WAIT_CA rows cannot appear on the boards")
        return self


def _is_banned(row: R6EnrichRowV1) -> bool:
    return "BAN" in (row.restriction_state or "").upper()


def _vetoed(row: R6EnrichRowV1) -> bool:
    """Hard veto: REJECT, WAIT_CA, or F&O ban can never enter a board."""
    return row.r2_public_state is SelectionState.REJECT or row.ca_state == "WAIT_CA" or _is_banned(
        row
    )


def _entry(row: R6EnrichRowV1, board: str, rank: int) -> Top10EntryV1:
    return Top10EntryV1(
        symbol=row.symbol,
        candidate_id=row.candidate_id,
        board=board,
        display_rank=rank,
        display_score=row.display_score,
        r2_public_state=row.r2_public_state,
        evidence_direction=row.evidence_direction,
        ca_state=row.ca_state,
        gap_pct=row.gap_pct,
        delivery_status=row.delivery_status,
        delivery_pct=row.delivery_pct,
        deal_summary=row.deal_summary,
        deal_tag=row.deal_tag,
        mf_delta=row.mf_delta,
        mf_month=row.mf_month,
        fo_package=row.fo_package,
        tags=row.tags,
        why=row.why,
        why_unknown=row.why_unknown,
    )


def build_top10_research(
    *,
    enrichment: R6EnrichmentBatchV1 | None = None,
    built_at: datetime | None = None,
) -> Top10ResearchBoardV1:
    batch = enrichment if enrichment is not None else build_r6_enrichment()
    eligible = [row for row in batch.rows if not _vetoed(row)]
    vetoed = len(batch.rows) - len(eligible)

    buy_rows = sorted(
        (row for row in eligible if row.evidence_direction is EvidenceDirection.BULLISH),
        key=lambda row: (
            -(row.display_score if row.display_score is not None else -1.0),
            row.symbol,
        ),
    )[:BOARD_SIZE]
    sell_rows = sorted(
        (row for row in eligible if row.evidence_direction is EvidenceDirection.BEARISH),
        key=lambda row: (
            -(row.display_score if row.display_score is not None else -1.0),
            row.symbol,
        ),
    )[:BOARD_SIZE]

    buy = [_entry(row, "BUY", index) for index, row in enumerate(buy_rows, start=1)]
    sell = [_entry(row, "SELL", index) for index, row in enumerate(sell_rows, start=1)]

    identity = {
        "r6RunHash": batch.run_hash,
        "buy": [entry.model_dump(mode="json", by_alias=True) for entry in buy],
        "sell": [entry.model_dump(mode="json", by_alias=True) for entry in sell],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    now = built_at or datetime.now(UTC)
    return Top10ResearchBoardV1(
        run_id=stable_id("top10-research", batch.run_id, run_hash),
        run_hash=run_hash,
        r6_run_id=batch.run_id,
        r6_run_hash=batch.run_hash,
        built_at=now,
        market_fii=batch.market_fii,
        buy=tuple(buy),
        sell=tuple(sell),
        vetoed_count=vetoed,
        warnings=(
            "BUY/SELL boards are ranked research attention with stickers. "
            "They are not trade advice, confirmation, probability, or "
            "executable signals.",
        ),
    )


__all__ = [
    "BOARD_SIZE",
    "CALIBRATION",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "Top10EntryV1",
    "Top10ResearchBoardV1",
    "build_top10_research",
]
