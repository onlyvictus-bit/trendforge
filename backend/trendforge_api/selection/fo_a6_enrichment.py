"""A6 contract-safe F&O enrichment for the cash WATCH shortlist only.

Futures OI never mixes with option OI. Missing F&O does not penalize cash-only names.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .. import storage
from ..parsers.nse_fo_bhavcopy_parser import parse_nse_fo_bhavcopy
from .cash_a3_discovery import CashDiscoveryBatch, latest_cash_discovery
from .contracts import SelectionState

FO_SOURCE_ID = "nse_fo_bhavcopy"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FoContractSlice(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    instrument_class: str
    expiry: str
    close: float
    previous_close: float
    open_interest: int
    oi_change: int
    oi_quadrant: str
    volume: int


class FoEnrichmentRow(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    shortlisted: bool
    fo_state: str
    near_future: FoContractSlice | None = None
    next_future: FoContractSlice | None = None
    rollover_ratio: float | None = None
    option_oi_used: bool = False
    note: str


class FoEnrichmentBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: str = "A6"
    acceptance_ceiling: str = "SHORTLIST_ENRICH_ONLY"
    batch_id: str
    source_id: str = FO_SOURCE_ID
    parser_state: str
    data_date: str | None = None
    artifact_hash: str | None = None
    can_rank: bool = False
    can_unlock_confirmed: bool = False
    row_count: int = Field(ge=0)
    rows: tuple[FoEnrichmentRow, ...] = ()
    persisted: bool = False


def _is_future(row: dict[str, Any]) -> bool:
    instrument = str(row.get("instrument") or "").upper()
    option_type = str(row.get("optionType") or "").upper()
    if option_type in {"CE", "PE", "CA", "PA"}:
        return False
    if any(tag in instrument for tag in ("STO", "IDO", "OPT")):
        return False
    if any(tag in instrument for tag in ("STF", "IDF", "FUT")):
        return True
    strike = float(row.get("strike") or 0)
    return strike <= 0 and not option_type


def _slice(row: dict[str, Any]) -> FoContractSlice:
    return FoContractSlice(
        symbol=str(row.get("symbol") or "").upper(),
        instrument_class="FUTURE",
        expiry=str(row.get("expiry") or ""),
        close=float(row.get("close") or 0),
        previous_close=float(row.get("previousClose") or 0),
        open_interest=int(row.get("openInterest") or 0),
        oi_change=int(row.get("oiChange") or 0),
        oi_quadrant=str(row.get("oiQuadrant") or "NEUTRAL_OR_UNKNOWN"),
        volume=int(row.get("volume") or 0),
    )


def build_fo_enrichment_batch(
    *,
    fo_content: bytes | None,
    discovery: CashDiscoveryBatch | None = None,
) -> FoEnrichmentBatch:
    disc = discovery if discovery is not None else latest_cash_discovery()
    shortlist = {
        row.symbol
        for row in (disc.rows if disc is not None else ())
        if row.public_state is SelectionState.WATCH
    }
    parser_state = "NOT_ATTEMPTED"
    data_date = None
    artifact_hash = None
    futures: dict[str, list[dict[str, Any]]] = {}
    if fo_content:
        parsed = parse_nse_fo_bhavcopy(fo_content)
        parser_state = str(parsed.get("parser_state"))
        data_date = parsed.get("data_date")
        artifact_hash = hashlib.sha256(fo_content).hexdigest()
        for row in (parsed.get("output") or {}).get("rows") or []:
            if not _is_future(row):
                continue
            futures.setdefault(str(row.get("symbol") or "").upper(), []).append(row)
    rows: list[FoEnrichmentRow] = []
    for symbol in sorted(
        {item.symbol for item in (disc.rows if disc is not None else ())}
    ):
        watched = symbol in shortlist
        contracts = sorted(
            futures.get(symbol, []),
            key=lambda item: str(item.get("expiry") or ""),
        )
        if not watched:
            rows.append(
                FoEnrichmentRow(
                    symbol=symbol,
                    shortlisted=False,
                    fo_state="NOT_REQUIRED",
                    note="Cash-only / not on WATCH shortlist. Missing F&O is not a penalty.",
                )
            )
            continue
        if parser_state != "PARSED_STRUCTURED":
            rows.append(
                FoEnrichmentRow(
                    symbol=symbol,
                    shortlisted=True,
                    fo_state="FO_UNAVAILABLE",
                    note="F&O file unproven. Shortlist stays cash-only. Not a FAIL.",
                )
            )
            continue
        if not contracts:
            rows.append(
                FoEnrichmentRow(
                    symbol=symbol,
                    shortlisted=True,
                    fo_state="NO_FUTURES",
                    note="WATCH name has no futures rows. Options OI was not substituted.",
                )
            )
            continue
        near = _slice(contracts[0])
        nxt = _slice(contracts[1]) if len(contracts) > 1 else None
        ratio = None
        if nxt is not None:
            total = near.open_interest + nxt.open_interest
            ratio = (nxt.open_interest / total) if total else None
        rows.append(
            FoEnrichmentRow(
                symbol=symbol,
                shortlisted=True,
                fo_state="FUTURES_OK",
                near_future=near,
                next_future=nxt,
                rollover_ratio=ratio,
                option_oi_used=False,
                note="Near futures OI only. Option OI excluded. Same-expiry identity required.",
            )
        )
    return FoEnrichmentBatch(
        batch_id=str(uuid4()),
        parser_state=parser_state,
        data_date=str(data_date) if data_date else None,
        artifact_hash=artifact_hash,
        can_rank=False,
        can_unlock_confirmed=False,
        row_count=len(rows),
        rows=tuple(rows),
    )


def persist_fo_enrichment(batch: FoEnrichmentBatch) -> FoEnrichmentBatch:
    if batch.can_rank or batch.can_unlock_confirmed or any(row.option_oi_used for row in batch.rows):
        raise ValueError("A6 cannot rank, confirm, or use option OI as futures OI")
    storage.init_db()
    conn = storage.connect()
    try:
        conn.execute(
            """
            INSERT INTO fo_enrichment_runs (
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


def latest_fo_enrichment() -> FoEnrichmentBatch | None:
    storage.init_db()
    conn = storage.connect()
    try:
        head = conn.execute(
            """
            SELECT payload_json FROM fo_enrichment_runs
            ORDER BY persisted_at DESC, batch_id DESC LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if head is None:
        return None
    payload = storage.decode_json(head["payload_json"])
    payload["persisted"] = True
    return FoEnrichmentBatch.model_validate(payload)
