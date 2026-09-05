"""A1 cash last-good staging.

Persist a typed SourceResult plus source-specific parsed rows.
Does not create NormalizedFact, EvidenceClaim, direction, rank or UI state.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .. import storage
from ..market_data_store import MarketDataStore, ManifestStatus
from ..parsers.nse_cash_bhavcopy_parser import (
    CASH_BHAV_SCHEMA_ID,
    parse_nse_cash_bhavcopy,
)
from ..source_contracts import (
    SourceContract,
    SourceResult,
    SourceResultState,
    SourceRole,
)

CASH_SOURCE_ID = "nse_bhavcopy_eod"
CASH_A1_CONTRACT_VERSION = "a1-staging-1"
CASH_A1_PARSER_VERSION = "nse_cash_bhavcopy_v1"
CASH_A1_MAX_AGE_SECONDS = 36 * 3600

CASH_A1_CONTRACT = SourceContract(
    source_id=CASH_SOURCE_ID,
    version=CASH_A1_CONTRACT_VERSION,
    role=SourceRole.OFFICIAL_GATE,
    schema_version=CASH_BHAV_SCHEMA_ID,
    parser_version=CASH_A1_PARSER_VERSION,
    allows_valid_empty=False,
    max_age_seconds=CASH_A1_MAX_AGE_SECONDS,
)


class CashStagingBatch(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    milestone: str = "A1"
    acceptance_ceiling: str = "STAGING_ONLY"
    result_id: str
    source_result: SourceResult
    row_count: int = Field(ge=0)
    rows: tuple[dict[str, Any], ...] = ()
    last_good_status: str | None = None
    persisted: bool = False


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_market_data_store() -> MarketDataStore:
    root = _project_root()
    return MarketDataStore(
        root=root / "data" / "market_data",
        db_path=root / "data" / "trendforge_research.db",
    )


def _map_parser_state(parser_state: str) -> SourceResultState:
    if parser_state == "PARSED_STRUCTURED":
        return SourceResultState.STRUCTURED_OK
    if parser_state == "WAIT_EMPTY_PARSE":
        return SourceResultState.PARSE_FAILED
    if parser_state == "WAIT_SCHEMA_MISMATCH":
        return SourceResultState.SCHEMA_CHANGED
    return SourceResultState.PARSE_FAILED


def build_cash_source_result(
    *,
    parsed: dict[str, Any],
    artifact_hash: str,
    raw_path: str | None,
    received_at: datetime,
    available_at: datetime,
    retrieved_at: datetime,
    freshness: str,
    last_good_stale: bool,
) -> SourceResult:
    parser_state = str(parsed.get("parserState") or parsed.get("parser_state") or "")
    data_date_raw = parsed.get("dataDate") or parsed.get("data_date")
    data_date = date.fromisoformat(str(data_date_raw)) if data_date_raw else None
    record_count = int(parsed.get("recordCount") or parsed.get("record_count") or 0)
    state = _map_parser_state(parser_state)
    if last_good_stale and state is SourceResultState.STRUCTURED_OK:
        state = SourceResultState.STALE
        freshness = "STALE"
    error_type = None
    error_message = None
    if state is not SourceResultState.STRUCTURED_OK:
        error_type = state.value
        error_message = str(parsed.get("summary") or state.value)
        record_count = 0
    return SourceResult(
        source_id=CASH_SOURCE_ID,
        contract_version=CASH_A1_CONTRACT_VERSION,
        role=SourceRole.OFFICIAL_GATE,
        state=state,
        record_count=record_count,
        data_date=data_date,
        published_at=None,
        received_at=received_at,
        available_at=available_at,
        retrieved_at=retrieved_at,
        schema_version=CASH_BHAV_SCHEMA_ID,
        parser_version=CASH_A1_PARSER_VERSION,
        revision_id=artifact_hash,
        artifact_hash=artifact_hash,
        raw_path=raw_path,
        freshness="STALE" if state is SourceResultState.STALE else freshness,
        can_support_confirmed=False,
        state_ceiling="WAIT",
        error_type=error_type,
        error_message=error_message,
    )


def stage_cash_bytes(
    content: bytes,
    *,
    raw_path: str | None = None,
    fetched_at: datetime | None = None,
    last_good_status: str | None = None,
    freshness: str = "UNKNOWN",
) -> CashStagingBatch:
    if not content:
        raise ValueError("cash last-good content is empty")
    now = fetched_at or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("fetched_at must be timezone-aware")
    artifact_hash = hashlib.sha256(content).hexdigest()
    parsed = parse_nse_cash_bhavcopy(content)
    last_good_stale = last_good_status == ManifestStatus.STALE_LAST_GOOD.value
    source_result = build_cash_source_result(
        parsed=parsed,
        artifact_hash=artifact_hash,
        raw_path=raw_path,
        received_at=now,
        available_at=now,
        retrieved_at=now,
        freshness="STALE" if last_good_stale else freshness,
        last_good_stale=last_good_stale,
    )
    output = parsed.get("output") or {}
    rows = tuple(output.get("rows") or ()) if source_result.ok else ()
    if source_result.state is SourceResultState.STALE:
        rows = tuple(output.get("rows") or ())
    return CashStagingBatch(
        result_id=str(uuid4()),
        source_result=source_result,
        row_count=len(rows),
        rows=rows,
        last_good_status=last_good_status,
        persisted=False,
    )


def stage_cash_last_good(
    store: MarketDataStore | None = None,
) -> CashStagingBatch:
    market = store or default_market_data_store()
    latest = market.latest_for(CASH_SOURCE_ID)
    if latest is None or not latest.content_hash:
        now = datetime.now(UTC)
        result = SourceResult(
            source_id=CASH_SOURCE_ID,
            contract_version=CASH_A1_CONTRACT_VERSION,
            role=SourceRole.OFFICIAL_GATE,
            state=SourceResultState.NOT_ATTEMPTED,
            record_count=0,
            data_date=None,
            published_at=None,
            received_at=now,
            available_at=now,
            retrieved_at=now,
            schema_version=CASH_BHAV_SCHEMA_ID,
            parser_version=CASH_A1_PARSER_VERSION,
            revision_id="missing-last-good",
            artifact_hash=None,
            raw_path=None,
            freshness="UNKNOWN",
            can_support_confirmed=False,
            state_ceiling="WAIT",
            error_type="MISSING_LAST_GOOD",
            error_message="No last-good cash bhavcopy object is stored.",
        )
        return CashStagingBatch(
            result_id=str(uuid4()),
            source_result=result,
            row_count=0,
            rows=(),
            last_good_status=None,
            persisted=False,
        )
    path = Path(latest.object_path) if latest.object_path else market.object_path_for_hash(
        latest.content_hash
    )
    content = Path(path).read_bytes()
    return stage_cash_bytes(
        content,
        raw_path=str(path),
        fetched_at=latest.fetched_at,
        last_good_status=latest.status.value,
        freshness=(
            "STALE"
            if latest.status is ManifestStatus.STALE_LAST_GOOD
            else "UNKNOWN"
        ),
    )


def persist_cash_staging(batch: CashStagingBatch) -> CashStagingBatch:
    if "instrumentId" in batch.model_dump(by_alias=True):
        raise ValueError("A1 staging cannot carry instrumentId")
    payload = batch.source_result.model_dump(mode="json", by_alias=True)
    if payload.get("canSupportConfirmed"):
        raise ValueError("A1 SourceResult cannot support CONFIRMED")
    if payload.get("stateCeiling") == "CONFIRMED":
        raise ValueError("A1 SourceResult cannot use CONFIRMED ceiling")
    storage.init_db()
    conn = storage.connect()
    now = datetime.now(UTC).isoformat()
    try:
        conn.execute(
            """
            INSERT INTO cash_source_results (
                result_id, source_id, artifact_hash, data_date, received_at,
                available_at, retrieved_at, state, freshness, record_count,
                last_good_status, payload_json, persisted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch.result_id,
                batch.source_result.source_id,
                batch.source_result.artifact_hash,
                (
                    batch.source_result.data_date.isoformat()
                    if batch.source_result.data_date
                    else None
                ),
                batch.source_result.received_at.isoformat(),
                batch.source_result.available_at.isoformat(),
                batch.source_result.retrieved_at.isoformat(),
                batch.source_result.state.value,
                batch.source_result.freshness,
                batch.row_count,
                batch.last_good_status,
                storage.encode_json(payload),
                now,
            ),
        )
        for index, row in enumerate(batch.rows):
            conn.execute(
                """
                INSERT INTO cash_staging_rows (
                    result_id, row_index, trade_date, symbol, series, isin,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch.result_id,
                    index,
                    row.get("tradeDate"),
                    row.get("symbol"),
                    row.get("series"),
                    row.get("isin"),
                    storage.encode_json(row),
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return batch.model_copy(update={"persisted": True})


def latest_cash_staging() -> CashStagingBatch | None:
    storage.init_db()
    conn = storage.connect()
    try:
        head = conn.execute(
            """
            SELECT result_id, last_good_status, payload_json
            FROM cash_source_results
            ORDER BY persisted_at DESC, result_id DESC
            LIMIT 1
            """
        ).fetchone()
        if head is None:
            return None
        rows = conn.execute(
            """
            SELECT payload_json FROM cash_staging_rows
            WHERE result_id = ?
            ORDER BY row_index
            """,
            (head["result_id"],),
        ).fetchall()
    finally:
        conn.close()
    source_result = SourceResult.model_validate(storage.decode_json(head["payload_json"]))
    staged = tuple(storage.decode_json(row["payload_json"]) for row in rows)
    return CashStagingBatch(
        result_id=head["result_id"],
        source_result=source_result,
        row_count=len(staged),
        rows=staged,
        last_good_status=head["last_good_status"] if "last_good_status" in head.keys() else None,
        persisted=True,
    )
