"""A5 verified index context and CA integrity overlay.

Index rows are market context only. They cannot confirm a stock.
Corporate actions remain integrity/WAIT, not bullish events.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .. import storage
from ..parsers.nse_index_close_parser import (
    INDEX_CLOSE_SCHEMA_ID,
    parse_nse_index_close,
)
from ..source_contracts import SourceContract, SourceRole
from .cash_a3_discovery import CashDiscoveryBatch, CashDiscoveryRow, latest_cash_discovery
from .cash_a4_history import CashHistoryBatch, latest_cash_history
from .contracts import SelectionState

INDEX_SOURCE_ID = "nse_index_close_eod"
INDEX_CONTRACT = SourceContract(
    source_id=INDEX_SOURCE_ID,
    version="a5-context-1",
    role=SourceRole.OFFICIAL_DELAYED_CONTEXT,
    schema_version=INDEX_CLOSE_SCHEMA_ID,
    parser_version="nse_index_close_v1",
    allows_valid_empty=False,
    max_age_seconds=36 * 3600,
)
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class IndexContext(BaseModel):
    model_config = MODEL_CONFIG

    source_id: str = INDEX_SOURCE_ID
    schema_version: str = INDEX_CLOSE_SCHEMA_ID
    contract_digest: str
    parser_state: str
    data_date: str | None = None
    artifact_hash: str | None = None
    nifty50_close: float | None = None
    nifty50_change_percent: float | None = None
    india_vix: float | None = None
    role: str = "CONTEXT"
    can_rank: bool = False
    can_unlock_confirmed: bool = False
    registry_note: str


class CashContextRow(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    public_state: SelectionState
    discovery_profiles: tuple[str, ...] = ()
    index_aligned: bool = False
    ca_integrity: str = "NONE"
    context_note: str


class CashContextBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: str = "A5"
    acceptance_ceiling: str = "CONTEXT_AND_INTEGRITY"
    batch_id: str
    index: IndexContext
    discovery_batch_id: str | None = None
    can_rank: bool = False
    can_unlock_confirmed: bool = False
    row_count: int = Field(ge=0)
    rows: tuple[CashContextRow, ...] = ()
    persisted: bool = False


def _digest() -> str:
    payload = (
        f"{INDEX_CONTRACT.source_id}|{INDEX_CONTRACT.version}|"
        f"{INDEX_CONTRACT.schema_version}|{INDEX_CONTRACT.parser_version}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _index_rows_from_content(
    content: bytes,
) -> tuple[str, str | None, list[dict[str, object]]]:
    stripped = content.lstrip()
    if stripped.startswith((b"{", b"[")):
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            records = (
                payload.get("records")
                or (payload.get("output") or {}).get("rows")
                or []
            )
            if isinstance(records, list) and records:
                data_date = payload.get("dataDate") or payload.get("data_date")
                parser_state = (
                    payload.get("parserState")
                    or payload.get("parser_state")
                    or "PARSED_STRUCTURED"
                )
                return str(parser_state), (
                    None if data_date is None else str(data_date)
                ), list(records)
    parsed = parse_nse_index_close(content)
    rows = (parsed.get("output") or {}).get("rows") or []
    return str(parsed.get("parser_state")), parsed.get("data_date"), list(rows)


def build_index_context(content: bytes | None) -> IndexContext:
    if not content:
        return IndexContext(
            contract_digest=_digest(),
            parser_state="NOT_ATTEMPTED",
            registry_note=(
                "nse_index_close_eod is official EOD class-average context. "
                "It is not a 123-job voter and cannot confirm a stock."
            ),
        )
    parser_state, data_date, rows = _index_rows_from_content(content)
    nifty = next((row for row in rows if row.get("indexName") == "NIFTY 50"), None)
    vix = next((row for row in rows if row.get("indexName") == "INDIA VIX"), None)
    return IndexContext(
        contract_digest=_digest(),
        parser_state=parser_state,
        data_date=data_date,
        artifact_hash=hashlib.sha256(content).hexdigest(),
        nifty50_close=None if nifty is None else nifty.get("close"),
        nifty50_change_percent=None if nifty is None else nifty.get("changePercent"),
        india_vix=None if vix is None else vix.get("close"),
        registry_note="Index context parsed. Cannot confirm a stock.",
    )


def build_cash_context_batch(
    *,
    index_content: bytes | None,
    discovery: CashDiscoveryBatch | None = None,
    history: CashHistoryBatch | None = None,
) -> CashContextBatch:
    disc = discovery if discovery is not None else latest_cash_discovery()
    hist = history if history is not None else latest_cash_history()
    index = build_index_context(index_content)
    ca_by_symbol = {
        row.symbol: row.ca_state for row in (hist.rows if hist is not None else ())
    }
    aligned = (
        index.parser_state == "PARSED_STRUCTURED"
        and disc is not None
        and any(
            row.metrics.session_return is not None
            for row in disc.rows
        )
    )
    rows: list[CashContextRow] = []
    for item in disc.rows if disc is not None else ():
        integrity = ca_by_symbol.get(item.symbol, "NONE")
        state = item.public_state
        note = "Index/VIX are context only."
        if integrity == "WAIT_CA":
            state = SelectionState.WAIT
            note = "Unresolved CA keeps WAIT. Not bullish. Index cannot override integrity."
        elif index.parser_state != "PARSED_STRUCTURED":
            note = "Index context unavailable. Stock state unchanged. Not required per symbol."
        rows.append(
            CashContextRow(
                symbol=item.symbol,
                public_state=state,
                discovery_profiles=tuple(profile.value for profile in item.discovery_profiles),
                index_aligned=bool(aligned and index.data_date),
                ca_integrity=integrity,
                context_note=note,
            )
        )
    return CashContextBatch(
        batch_id=str(uuid4()),
        index=index,
        discovery_batch_id=None if disc is None else disc.batch_id,
        can_rank=False,
        can_unlock_confirmed=False,
        row_count=len(rows),
        rows=tuple(rows),
    )


def persist_cash_context(batch: CashContextBatch) -> CashContextBatch:
    if batch.can_rank or batch.can_unlock_confirmed or batch.index.can_rank:
        raise ValueError("A5 cannot authorize rank or CONFIRMED")
    storage.init_db()
    conn = storage.connect()
    try:
        conn.execute(
            """
            INSERT INTO cash_context_runs (
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


def latest_cash_context() -> CashContextBatch | None:
    storage.init_db()
    conn = storage.connect()
    try:
        head = conn.execute(
            """
            SELECT payload_json FROM cash_context_runs
            ORDER BY persisted_at DESC, batch_id DESC LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if head is None:
        return None
    payload = storage.decode_json(head["payload_json"])
    payload["persisted"] = True
    return CashContextBatch.model_validate(payload)
