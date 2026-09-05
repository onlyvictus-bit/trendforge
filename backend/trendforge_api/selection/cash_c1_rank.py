"""C1 attention rank. Resolver consumes C0 flags; it cannot grant them."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .. import storage
from .cash_a3_discovery import CashDiscoveryBatch, latest_cash_discovery
from .cash_a4_history import latest_cash_history
from .contracts import SelectionState
from .fo_a6_enrichment import latest_fo_enrichment
from .index_a5_context import latest_cash_context
from .mwpl_b import MwplAssessment, assess_mwpl, latest_mwpl
from .use_matrix_c0 import (
    build_source_use_matrix,
    latest_source_use_matrix,
    permission_for,
)

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CashRankRow(BaseModel):
    model_config = MODEL_CONFIG

    rank: int | None
    symbol: str
    public_state: SelectionState
    attention_score: float | None = None
    support: tuple[str, ...] = ()
    opposition: tuple[str, ...] = ()
    reason: str


class CashRankBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: str = "C1"
    acceptance_ceiling: str = "WATCH_WAIT_REJECT"
    batch_id: str
    matrix_id: str | None
    can_rank_cash: bool
    can_unlock_confirmed: bool = False
    mwpl_state: str
    row_count: int = Field(ge=0)
    rows: tuple[CashRankRow, ...] = ()
    persisted: bool = False


def _conflict(session_dir: str, fo_quadrant: str | None) -> bool:
    if not fo_quadrant:
        return False
    if session_dir == "UP" and fo_quadrant == "SHORT_BUILD_UP":
        return True
    if session_dir == "DOWN" and fo_quadrant == "LONG_BUILD_UP":
        return True
    return False


def build_cash_rank_batch(
    *,
    discovery: CashDiscoveryBatch | None = None,
    mwpl_content: bytes | None = None,
    mwpl: MwplAssessment | None = None,
) -> CashRankBatch:
    disc = discovery if discovery is not None else latest_cash_discovery()
    matrix = latest_source_use_matrix() or build_source_use_matrix()
    cash = permission_for(matrix, "nse_bhavcopy_eod")
    history = latest_cash_history()
    context = latest_cash_context()
    fo = latest_fo_enrichment()
    mwpl = mwpl or latest_mwpl() or assess_mwpl(mwpl_content)
    ca = {row.symbol: row.ca_state for row in (history.rows if history else ())}
    ctx = {row.symbol: row for row in (context.rows if context else ())}
    fo_map = {row.symbol: row for row in (fo.rows if fo else ())}
    rows: list[CashRankRow] = []
    if disc is None:
        return CashRankBatch(
            batch_id=str(uuid4()),
            matrix_id=matrix.matrix_id,
            can_rank_cash=cash.can_rank,
            mwpl_state=mwpl.state,
            row_count=0,
            rows=(),
        )
    scored: list[tuple[float, CashRankRow]] = []
    for item in disc.rows:
        if item.public_state is SelectionState.REJECT:
            rows.append(
                CashRankRow(
                    rank=None,
                    symbol=item.symbol,
                    public_state=SelectionState.REJECT,
                    reason="Hard veto. Not ranked.",
                )
            )
            continue
        if ca.get(item.symbol) == "WAIT_CA":
            rows.append(
                CashRankRow(
                    rank=None,
                    symbol=item.symbol,
                    public_state=SelectionState.WAIT,
                    reason="Unresolved corporate action. Integrity WAIT, not ranked.",
                )
            )
            continue
        if ctx.get(item.symbol) and ctx[item.symbol].public_state is SelectionState.WAIT:
            rows.append(
                CashRankRow(
                    rank=None,
                    symbol=item.symbol,
                    public_state=SelectionState.WAIT,
                    reason=ctx[item.symbol].context_note,
                )
            )
            continue
        if not cash.can_rank:
            rows.append(
                CashRankRow(
                    rank=None,
                    symbol=item.symbol,
                    public_state=item.public_state,
                    reason="C0 can_rank=false for cash. Resolver cannot invent rank.",
                )
            )
            continue
        if item.public_state is not SelectionState.WATCH or not item.eligible:
            rows.append(
                CashRankRow(
                    rank=None,
                    symbol=item.symbol,
                    public_state=item.public_state,
                    reason="Not on WATCH shortlist.",
                )
            )
            continue
        session = item.metrics.session_direction.value
        fo_row = fo_map.get(item.symbol)
        quadrant = (
            fo_row.near_future.oi_quadrant
            if fo_row and fo_row.near_future is not None
            else None
        )
        if _conflict(session, quadrant):
            rows.append(
                CashRankRow(
                    rank=None,
                    symbol=item.symbol,
                    public_state=SelectionState.WAIT,
                    support=("PRICE",),
                    opposition=("FUTURES_OI",),
                    reason="Price and futures OI disagree. WAIT, not confirmation.",
                )
            )
            continue
        ret = item.metrics.return_percentile or 0.0
        part = max(
            v
            for v in (item.metrics.volume_percentile, item.metrics.turnover_percentile)
            if v is not None
        ) if any(
            v is not None
            for v in (item.metrics.volume_percentile, item.metrics.turnover_percentile)
        ) else 0.0
        score = 0.5 * ret + 0.5 * part
        scored.append(
            (
                score,
                CashRankRow(
                    rank=0,
                    symbol=item.symbol,
                    public_state=SelectionState.WATCH,
                    attention_score=score,
                    support=("PRICE", "ACTIVITY"),
                    opposition=(),
                    reason="Attention score from quality-weighted cash percentiles. Not win%.",
                ),
            )
        )
    scored.sort(key=lambda item: item[0], reverse=True)
    for index, (_, row) in enumerate(scored, start=1):
        rows.append(row.model_copy(update={"rank": index}))
    return CashRankBatch(
        batch_id=str(uuid4()),
        matrix_id=matrix.matrix_id,
        can_rank_cash=cash.can_rank,
        mwpl_state=mwpl.state,
        row_count=len(rows),
        rows=tuple(rows),
    )


def persist_cash_rank(batch: CashRankBatch) -> CashRankBatch:
    if batch.can_unlock_confirmed:
        raise ValueError("C1 cannot unlock CONFIRMED")
    if any(row.public_state is SelectionState.CONFIRMED for row in batch.rows):
        raise ValueError("C1 cannot persist CONFIRMED")
    storage.init_db()
    conn = storage.connect()
    try:
        conn.execute(
            """
            INSERT INTO cash_rank_runs (
                batch_id, payload_json, persisted_at
            ) VALUES (?, ?, ?)
            """,
            (
                batch.batch_id,
                storage.encode_json(batch.model_dump(mode="json", by_alias=True)),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return batch.model_copy(update={"persisted": True})
