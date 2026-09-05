"""A2 cash identity and S0/S1 safety.

Creates NormalizedFact after instrument identity. Does not rank, invent
direction, unlock CONFIRMED, or treat missing/stale ban as a pass or reject.

This is NOT File A R4. Live R4 (`r4_live.py`) only pins these A2 IDs and the
PK inventory; it must not rebuild identity here.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .. import storage
from ..exchange_calendar import evaluate_nse_calendar
from ..market_data_store import ManifestStatus, MarketDataStore
from ..parsers.nse_mwpl_parser import parse_nse_fno_ban
from ..source_contracts import SourceResultState
from .cash_a1_staging import (
    CASH_SOURCE_ID,
    CashStagingBatch,
    default_market_data_store,
    latest_cash_staging,
)
from .contracts import (
    GateOutcome,
    InstrumentIdentity,
    NormalizedFact,
    PointInTimeLineage,
    SelectionGateResult,
    SelectionState,
)

BAN_SOURCE_ID = "nse_fno_ban"
CASH_DATASET_ROOT = "SRC-NSE-EOD"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RestrictionAssessment(BaseModel):
    model_config = MODEL_CONFIG

    source_id: str
    proven: bool
    can_veto: bool
    state: Literal["READY", "WAIT_RESTRICTION", "MWPL_MISSING"]
    reason: str
    data_date: str | None = None
    artifact_hash: str | None = None
    symbols: tuple[str, ...] = ()


class CashIdentityRow(BaseModel):
    model_config = MODEL_CONFIG

    instrument: InstrumentIdentity
    fact: NormalizedFact
    public_state: SelectionState
    gates: tuple[SelectionGateResult, ...]
    banned: bool = False


class CashIdentityBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: str = "A2"
    acceptance_ceiling: str = "IDENTITY_AND_SAFETY"
    batch_id: str
    staging_result_id: str | None
    can_rank: bool = False
    can_unlock_confirmed: bool = False
    calendar_state: str
    restriction: RestrictionAssessment
    fact_count: int = Field(ge=0)
    rows: tuple[CashIdentityRow, ...] = ()
    persisted: bool = False


def _lineage_from_staging(staging: CashStagingBatch) -> PointInTimeLineage | None:
    result = staging.source_result
    if not result.artifact_hash:
        return None
    stamp = result.available_at
    return PointInTimeLineage(
        event_time=stamp,
        published_at=result.published_at or stamp,
        received_at=result.received_at,
        available_at=result.available_at,
        retrieved_at=result.retrieved_at,
        revision_id=result.revision_id,
        artifact_hash=result.artifact_hash,
    )


def _quality_state(staging: CashStagingBatch) -> Literal[
    "STRUCTURED_OK", "VALID_EMPTY", "INPUT_INCOMPLETE", "STALE", "REJECTED"
]:
    state = staging.source_result.state
    if state is SourceResultState.STALE or staging.source_result.freshness == "STALE":
        return "STALE"
    if state is SourceResultState.STRUCTURED_OK:
        return "STRUCTURED_OK"
    if state is SourceResultState.VALID_EMPTY:
        return "VALID_EMPTY"
    return "INPUT_INCOMPLETE"


def assess_ban_restriction(
    *,
    store: MarketDataStore | None = None,
    ban_content: bytes | None = None,
    last_good_status: str | None = None,
    fetched_at: datetime | None = None,
) -> RestrictionAssessment:
    if ban_content is None:
        market = store or default_market_data_store()
        latest = market.latest_for(BAN_SOURCE_ID)
        if latest is None or not latest.content_hash:
            ban_content = None
        else:
            path = (
                Path(latest.object_path)
                if latest.object_path
                else market.object_path_for_hash(latest.content_hash)
            )
            ban_content = Path(path).read_bytes()
            last_good_status = latest.status.value
            fetched_at = latest.fetched_at
    if not ban_content:
        return RestrictionAssessment(
            source_id=BAN_SOURCE_ID,
            proven=False,
            can_veto=False,
            state="WAIT_RESTRICTION",
            reason="Ban last-good artifact is missing. Restriction cannot pass or reject.",
        )
    parsed = parse_nse_fno_ban(ban_content)
    parser_state = parsed.get("parser_state")
    data_date = parsed.get("data_date")
    artifact_hash = hashlib.sha256(ban_content).hexdigest()
    stale = last_good_status == ManifestStatus.STALE_LAST_GOOD.value
    output = parsed.get("output") or {}
    symbols = tuple(str(item).upper() for item in (output.get("symbols") or ()))
    proven = (
        parser_state == "PARSED_STRUCTURED"
        and bool(data_date)
        and bool(artifact_hash)
        and not stale
        and fetched_at is not None
    )
    if not proven:
        return RestrictionAssessment(
            source_id=BAN_SOURCE_ID,
            proven=False,
            can_veto=False,
            state="WAIT_RESTRICTION",
            reason="Ban artifact, date, schema or freshness is unproven. Wait, do not invent REJECT or pass.",
            data_date=str(data_date) if data_date else None,
            artifact_hash=artifact_hash,
            symbols=symbols,
        )
    return RestrictionAssessment(
        source_id=BAN_SOURCE_ID,
        proven=True,
        can_veto=True,
        state="READY",
        reason="Ban artifact, date, schema and freshness are proven. Veto only, not a plus family.",
        data_date=str(data_date),
        artifact_hash=artifact_hash,
        symbols=symbols,
    )


def mwpl_missing() -> RestrictionAssessment:
    return RestrictionAssessment(
        source_id="nse_mwpl_percentages",
        proven=False,
        can_veto=False,
        state="MWPL_MISSING",
        reason="No verified official MWPL percentage artifact. Cash identity continues.",
    )


def _s0_gate(staging: CashStagingBatch) -> SelectionGateResult:
    result = staging.source_result
    ok = (
        result.state is SourceResultState.STRUCTURED_OK
        and result.artifact_hash
        and result.data_date is not None
        and result.freshness != "STALE"
    )
    if ok:
        return SelectionGateResult(
            code="S0_SOURCE_HEALTH",
            outcome=GateOutcome.PASS,
            blocks_confirmed=False,
            reason="Cash last-good has hash, session date, schema and structured rows.",
            required=True,
        )
    return SelectionGateResult(
        code="S0_SOURCE_HEALTH",
        outcome=GateOutcome.WAIT,
        blocks_confirmed=True,
        reason=(
            f"Cash source is {result.state.value}/{result.freshness}; "
            "S0 cannot treat last-good as fresh."
        ),
        required=True,
    )


def _calendar_gate(data_date) -> tuple[dict[str, Any], SelectionGateResult]:
    calendar = evaluate_nse_calendar(data_date, segment="CM")
    if calendar["state"] == "WAIT_CALENDAR_DATA":
        return calendar, SelectionGateResult(
            code="S1_CALENDAR",
            outcome=GateOutcome.WAIT,
            blocks_confirmed=True,
            reason=str(calendar["reason"]),
            required=True,
        )
    return calendar, SelectionGateResult(
        code="S1_CALENDAR",
        outcome=GateOutcome.PASS,
        blocks_confirmed=False,
        reason=str(calendar["reason"]),
        required=True,
    )


def _ban_gate(symbol: str, restriction: RestrictionAssessment) -> SelectionGateResult:
    if not restriction.proven or not restriction.can_veto:
        return SelectionGateResult(
            code="S1_BAN",
            outcome=GateOutcome.WAIT,
            blocks_confirmed=True,
            reason=restriction.reason,
            required=True,
        )
    if symbol.upper() in restriction.symbols:
        return SelectionGateResult(
            code="S1_BAN",
            outcome=GateOutcome.REJECT,
            blocks_confirmed=True,
            reason=f"{symbol} is on the proven F&O ban list.",
            required=True,
        )
    return SelectionGateResult(
        code="S1_BAN",
        outcome=GateOutcome.PASS,
        blocks_confirmed=False,
        reason="Not banned. Eligibility only; not a supporting family.",
        required=True,
    )


def build_cash_identity_batch(
    staging: CashStagingBatch | None = None,
    *,
    store: MarketDataStore | None = None,
    ban_content: bytes | None = None,
    ban_status: str | None = None,
    ban_fetched_at: datetime | None = None,
    restriction: RestrictionAssessment | None = None,
) -> CashIdentityBatch:
    batch = staging if staging is not None else latest_cash_staging()
    restriction = restriction or assess_ban_restriction(
        store=store if ban_content is None else None,
        ban_content=ban_content,
        last_good_status=ban_status,
        fetched_at=ban_fetched_at,
    )
    if batch is None:
        return CashIdentityBatch(
            batch_id=str(uuid4()),
            staging_result_id=None,
            calendar_state="WAIT_CALENDAR_DATA",
            restriction=restriction,
            fact_count=0,
            rows=(),
        )
    s0 = _s0_gate(batch)
    lineage = _lineage_from_staging(batch)
    calendar = {"state": "WAIT_CALENDAR_DATA", "reason": "No cash data_date."}
    calendar_gate = SelectionGateResult(
        code="S1_CALENDAR",
        outcome=GateOutcome.WAIT,
        blocks_confirmed=True,
        reason="Cash data_date is missing.",
        required=True,
    )
    if batch.source_result.data_date is not None:
        calendar, calendar_gate = _calendar_gate(batch.source_result.data_date)
    rows: list[CashIdentityRow] = []
    if lineage is not None and batch.rows:
        quality = _quality_state(batch)
        for raw in batch.rows:
            symbol = str(raw.get("symbol") or "").strip().upper()
            series = str(raw.get("series") or "").strip().upper()
            if not symbol or series != "EQ":
                continue
            instrument = InstrumentIdentity.create(
                exchange="NSE",
                segment="EQ",
                symbol=symbol,
                series=series,
                isin=raw.get("isin"),
            )
            trade_date = raw.get("tradeDate") or (
                batch.source_result.data_date.isoformat()
                if batch.source_result.data_date
                else None
            )
            if not trade_date:
                continue
            identity_gate = SelectionGateResult(
                code="S1_IDENTITY",
                outcome=GateOutcome.PASS,
                blocks_confirmed=False,
                reason="Symbol, EQ series and exchange identity resolved.",
                required=True,
            )
            ban_gate = _ban_gate(symbol, restriction)
            fact = NormalizedFact.create(
                instrument_id=instrument.instrument_id,
                source_id=CASH_SOURCE_ID,
                dataset_root=CASH_DATASET_ROOT,
                business_keys={
                    "symbol": symbol,
                    "series": series,
                    "trade_date": str(trade_date),
                },
                data_date=datetime.fromisoformat(str(trade_date)).date(),
                lineage=lineage,
                quality_state=quality,
                payload={
                    "symbol": symbol,
                    "series": series,
                    "isin": raw.get("isin"),
                    "open": raw.get("open"),
                    "high": raw.get("high"),
                    "low": raw.get("low"),
                    "close": raw.get("close"),
                    "previousClose": raw.get("previousClose"),
                    "volume": raw.get("volume"),
                    "tradedValue": raw.get("tradedValue"),
                    "tradeCount": raw.get("tradeCount"),
                },
            )
            if "evidenceDirection" in fact.payload:
                raise ValueError("A2 must not invent evidenceDirection")
            if ban_gate.outcome is GateOutcome.REJECT:
                public_state = SelectionState.REJECT
            else:
                public_state = SelectionState.WAIT
            rows.append(
                CashIdentityRow(
                    instrument=instrument,
                    fact=fact,
                    public_state=public_state,
                    gates=(s0, identity_gate, calendar_gate, ban_gate),
                    banned=ban_gate.outcome is GateOutcome.REJECT,
                )
            )
    return CashIdentityBatch(
        batch_id=str(uuid4()),
        staging_result_id=batch.result_id,
        can_rank=False,
        can_unlock_confirmed=False,
        calendar_state=str(calendar.get("state") or "WAIT_CALENDAR_DATA"),
        restriction=restriction,
        fact_count=len(rows),
        rows=tuple(rows),
    )


def persist_cash_identity(batch: CashIdentityBatch) -> CashIdentityBatch:
    if batch.can_rank or batch.can_unlock_confirmed:
        raise ValueError("A2 cannot set can_rank or can_unlock_confirmed")
    if any(row.public_state is SelectionState.CONFIRMED for row in batch.rows):
        raise ValueError("A2 cannot persist CONFIRMED")
    storage.init_db()
    conn = storage.connect()
    now = datetime.now(UTC).isoformat()
    try:
        conn.execute(
            """
            INSERT INTO cash_identity_runs (
                batch_id, staging_result_id, calendar_state, restriction_json,
                fact_count, payload_json, persisted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch.batch_id,
                batch.staging_result_id,
                batch.calendar_state,
                storage.encode_json(
                    batch.restriction.model_dump(mode="json", by_alias=True)
                ),
                batch.fact_count,
                storage.encode_json(batch.model_dump(mode="json", by_alias=True)),
                now,
            ),
        )
        for row in batch.rows:
            conn.execute(
                """
                INSERT INTO cash_normalized_facts (
                    batch_id, fact_id, instrument_id, symbol, series,
                    public_state, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch.batch_id,
                    row.fact.fact_id,
                    row.instrument.instrument_id,
                    row.instrument.symbol,
                    row.instrument.series,
                    row.public_state.value,
                    storage.encode_json(row.model_dump(mode="json", by_alias=True)),
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return batch.model_copy(update={"persisted": True})


def latest_cash_identity() -> CashIdentityBatch | None:
    storage.init_db()
    conn = storage.connect()
    try:
        head = conn.execute(
            """
            SELECT payload_json FROM cash_identity_runs
            ORDER BY persisted_at DESC, batch_id DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if head is None:
        return None
    payload = storage.decode_json(head["payload_json"])
    payload["persisted"] = True
    return CashIdentityBatch.model_validate(payload)
