"""C0 generated source permission / use matrix.

Flags live on this generated governance view, not on a resolver profile.
canVote from R0-B is not can_rank.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .. import storage
from ..source_cohort_r0b import evaluate_r0b_cohort
from ..source_inventory_compiler import compile_default_inventory

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)
Job = Literal["RANK", "GATE", "ENRICH", "CONTEXT", "FALLBACK", "QUARANTINE"]


class SourceUseRow(BaseModel):
    model_config = MODEL_CONFIG

    source_key: str
    desk: str
    job: Job
    family: str
    can_rank: bool
    can_veto: bool
    can_unlock_confirmed: bool
    can_vote: bool
    ceiling: str
    note: str


class SourceUseMatrix(BaseModel):
    model_config = MODEL_CONFIG

    milestone: str = "C0"
    acceptance_ceiling: str = "PERMISSIONS_ONLY"
    matrix_id: str
    source_activation_ready: bool = False
    gate_authorized: int = 0
    row_count: int = Field(ge=0)
    rows: tuple[SourceUseRow, ...] = ()
    persisted: bool = False


def _job_for(key: str) -> tuple[str, Job, str, bool, bool, str, str]:
    table = {
        "nse_bhavcopy_eod": (
            "SWING",
            "RANK",
            "PRICE/ACTIVITY",
            True,
            False,
            "WATCH",
            "Attention rank only after A3. Not CONFIRMED.",
        ),
        "nse_fno_ban": (
            "INTRADAY",
            "GATE",
            "TRADABILITY_AND_SAFETY",
            False,
            True,
            "REJECT",
            "Veto only when runtime artifact is proven.",
        ),
        "nse_mwpl_percentages": (
            "INTRADAY",
            "GATE",
            "TRADABILITY_AND_SAFETY",
            False,
            False,
            "WAIT",
            "MWPL_MISSING until official percentage artifact exists.",
        ),
        "nse_index_close_eod": (
            "SWING",
            "CONTEXT",
            "MARKET_AND_SECTOR_CONTEXT",
            False,
            False,
            "WAIT",
            "Context only. Not required per symbol.",
        ),
        "nse_all_indices": (
            "SWING",
            "CONTEXT",
            "MARKET_AND_SECTOR_CONTEXT",
            False,
            False,
            "WAIT",
            "Context alias. Cannot vote.",
        ),
        "nse_fo_bhavcopy": (
            "INTRADAY",
            "ENRICH",
            "DERIVATIVES_OI",
            False,
            False,
            "WAIT",
            "Shortlist futures enrichment only.",
        ),
        "nse_corporate_filings_actions": (
            "SWING",
            "ENRICH",
            "EVENT_AND_SPONSOR",
            False,
            False,
            "WAIT",
            "Integrity / adjustment. Not bullish.",
        ),
    }
    return table.get(
        key,
        (
            "RESEARCH",
            "QUARANTINE",
            "UNKNOWN",
            False,
            False,
            "WAIT",
            "Generated default: quarantined, cannot rank or confirm.",
        ),
    )


def build_source_use_matrix() -> SourceUseMatrix:
    report = compile_default_inventory()
    cohort = evaluate_r0b_cohort()
    vote = {item.source_key: item.can_vote for item in cohort.members}
    keys = {item.source_contract_id for item in report.source_contracts}
    keys.update(vote)
    keys.update(
        {
            "nse_bhavcopy_eod",
            "nse_fno_ban",
            "nse_mwpl_percentages",
            "nse_index_close_eod",
            "nse_fo_bhavcopy",
            "nse_corporate_filings_actions",
        }
    )
    rows = []
    for key in sorted(keys):
        desk, job, family, can_rank, can_veto, ceiling, note = _job_for(key)
        rows.append(
            SourceUseRow(
                source_key=key,
                desk=desk,
                job=job,
                family=family,
                can_rank=can_rank,
                can_veto=can_veto,
                can_unlock_confirmed=False,
                can_vote=bool(vote.get(key, False)),
                ceiling=ceiling,
                note=note,
            )
        )
    return SourceUseMatrix(
        matrix_id=str(uuid4()),
        source_activation_ready=False,
        gate_authorized=int(report.gate_authorized_source_key_count),
        row_count=len(rows),
        rows=tuple(rows),
    )


def permission_for(matrix: SourceUseMatrix, source_key: str) -> SourceUseRow:
    for row in matrix.rows:
        if row.source_key == source_key:
            return row
    desk, job, family, can_rank, can_veto, ceiling, note = _job_for(source_key)
    return SourceUseRow(
        source_key=source_key,
        desk=desk,
        job=job,
        family=family,
        can_rank=can_rank,
        can_veto=can_veto,
        can_unlock_confirmed=False,
        can_vote=False,
        ceiling=ceiling,
        note=note,
    )


def persist_source_use_matrix(matrix: SourceUseMatrix) -> SourceUseMatrix:
    if matrix.source_activation_ready or any(row.can_unlock_confirmed for row in matrix.rows):
        raise ValueError("C0 cannot activate sources or unlock CONFIRMED")
    if any(row.can_vote for row in matrix.rows):
        raise ValueError("C0 must not promote R0-B canVote")
    storage.init_db()
    conn = storage.connect()
    try:
        conn.execute(
            """
            INSERT INTO source_use_matrices (
                matrix_id, payload_json, persisted_at
            ) VALUES (?, ?, ?)
            """,
            (
                matrix.matrix_id,
                storage.encode_json(matrix.model_dump(mode="json", by_alias=True)),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return matrix.model_copy(update={"persisted": True})


def latest_source_use_matrix() -> SourceUseMatrix | None:
    storage.init_db()
    conn = storage.connect()
    try:
        head = conn.execute(
            """
            SELECT payload_json FROM source_use_matrices
            ORDER BY persisted_at DESC, matrix_id DESC LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if head is None:
        return None
    payload = storage.decode_json(head["payload_json"])
    payload["persisted"] = True
    return SourceUseMatrix.model_validate(payload)
