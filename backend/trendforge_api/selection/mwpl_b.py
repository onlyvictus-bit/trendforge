"""B conditional MWPL. Missing official percentage artifact stays MWPL_MISSING."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .. import storage
from ..parsers.nse_mwpl_parser import parse_nse_mwpl_percentages


class MwplAssessment(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    milestone: str = "B"
    source_id: str = "nse_mwpl_percentages"
    state: str
    proven: bool
    can_veto: bool
    can_rank: bool = False
    can_unlock_confirmed: bool = False
    parser_state: str | None = None
    artifact_hash: str | None = None
    data_date: str | None = None
    reason: str
    persisted: bool = False


def assess_mwpl(content: bytes | None) -> MwplAssessment:
    if not content:
        return MwplAssessment(
            state="MWPL_MISSING",
            proven=False,
            can_veto=False,
            reason="No official MWPL percentage artifact. Cash ranking may continue.",
        )
    parsed = parse_nse_mwpl_percentages(content)
    parser_state = str(parsed.get("parser_state"))
    data_date = parsed.get("data_date")
    rows = (parsed.get("output") or {}).get("rows") or []
    proven = parser_state == "PARSED_STRUCTURED" and bool(data_date) and bool(rows)
    if not proven:
        return MwplAssessment(
            state="MWPL_MISSING",
            proven=False,
            can_veto=False,
            parser_state=parser_state,
            artifact_hash=hashlib.sha256(content).hexdigest(),
            data_date=str(data_date) if data_date else None,
            reason="MWPL parse did not prove schema, date and percentage rows.",
        )
    return MwplAssessment(
        state="READY",
        proven=True,
        can_veto=True,
        parser_state=parser_state,
        artifact_hash=hashlib.sha256(content).hexdigest(),
        data_date=str(data_date),
        reason="Official MWPL percentages proven. Gate only. Not a plus family.",
    )


def persist_mwpl(assessment: MwplAssessment) -> MwplAssessment:
    if assessment.can_rank or assessment.can_unlock_confirmed:
        raise ValueError("MWPL cannot rank or unlock CONFIRMED")
    storage.init_db()
    conn = storage.connect()
    try:
        conn.execute(
            """
            INSERT INTO mwpl_assessments (
                assessment_id, payload_json, persisted_at
            ) VALUES (?, ?, ?)
            """,
            (
                str(uuid4()),
                storage.encode_json(assessment.model_dump(mode="json", by_alias=True)),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return assessment.model_copy(update={"persisted": True})


def latest_mwpl() -> MwplAssessment | None:
    storage.init_db()
    conn = storage.connect()
    try:
        head = conn.execute(
            """
            SELECT payload_json FROM mwpl_assessments
            ORDER BY persisted_at DESC, assessment_id DESC LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if head is None:
        return None
    payload = storage.decode_json(head["payload_json"])
    payload["persisted"] = True
    return MwplAssessment.model_validate(payload)
