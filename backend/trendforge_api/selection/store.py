"""STO-006/007/008 persistence for R1 live selection batches."""

from __future__ import annotations

from datetime import UTC, datetime

from .. import storage
from .contracts import SelectionCandidate, SelectionState, stable_id
from .live_run import LiveSelectionBatch


def _strip_computed(payload: dict) -> dict:
    payload.pop("gateCodes", None)
    payload.pop("gate_codes", None)
    candidates = payload.get("candidates") or payload.get("Candidates")
    if isinstance(candidates, list):
        for item in candidates:
            if isinstance(item, dict):
                item.pop("gateCodes", None)
                item.pop("gate_codes", None)
    return payload


def latest_live_selection_batch() -> LiveSelectionBatch | None:
    storage.init_db()
    conn = storage.connect()
    try:
        row = conn.execute(
            """
            SELECT payload_json FROM selection_scan_runs
            WHERE profile_id = 'PRF-R1-LIVE'
            ORDER BY persisted_at DESC, run_id DESC LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    payload = _strip_computed(storage.decode_json(row["payload_json"]))
    return LiveSelectionBatch.model_validate(payload)


def latest_selection_payload(profile_id: str) -> dict | None:
    """Return the latest immutable payload for one selection profile."""
    storage.init_db()
    conn = storage.connect()
    try:
        row = conn.execute(
            """
            SELECT payload_json FROM selection_scan_runs
            WHERE profile_id = ?
            ORDER BY persisted_at DESC, run_id DESC LIMIT 1
            """,
            (profile_id,),
        ).fetchone()
    finally:
        conn.close()
    return storage.decode_json(row["payload_json"]) if row is not None else None


def get_selection_payload(profile_id: str, run_id: str) -> dict | None:
    """One stored artifact by exact run id under a profile (or None)."""
    storage.init_db()
    conn = storage.connect()
    try:
        row = conn.execute(
            """
            SELECT payload_json FROM selection_scan_runs
            WHERE profile_id = ? AND run_id = ?
            """,
            (profile_id, run_id),
        ).fetchone()
        return storage.decode_json(row["payload_json"]) if row is not None else None
    finally:
        conn.close()


def list_latest_selection_payloads(profile_id: str, limit: int = 20) -> list[dict]:
    """Newest-first stored artifacts for one profile (reconstructable history)."""
    storage.init_db()
    conn = storage.connect()
    try:
        rows = conn.execute(
            """
            SELECT payload_json FROM selection_scan_runs
            WHERE profile_id = ?
            ORDER BY persisted_at DESC, rowid DESC
            LIMIT ?
            """,
            (profile_id, int(limit)),
        ).fetchall()
        return [storage.decode_json(r["payload_json"]) for r in rows]
    finally:
        conn.close()


def persist_selection_payload(
    *,
    run_id: str,
    profile_id: str,
    as_of: datetime,
    payload: dict,
    candidates: tuple[tuple[str, str, str, dict], ...] = (),
) -> None:
    """Persist one immutable selection artifact using the existing STO-006 tables."""
    encoded = storage.encode_json(payload)
    now = datetime.now(UTC).isoformat()
    storage.init_db()
    conn = storage.connect()
    try:
        existing = conn.execute(
            "SELECT payload_json FROM selection_scan_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if existing is not None:
            if existing["payload_json"] != encoded:
                raise ValueError(f"selection artifact {run_id} is immutable")
            return
        conn.execute(
            """
            INSERT INTO selection_scan_runs (
                run_id, profile_id, as_of, persisted_at, payload_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, profile_id, as_of.isoformat(), now, encoded),
        )
        for candidate_id, symbol, state, candidate_payload in candidates:
            conn.execute(
                """
                INSERT INTO selection_candidates (
                    run_id, candidate_id, symbol, state, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    candidate_id,
                    symbol,
                    state,
                    storage.encode_json(candidate_payload),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def persist_live_selection_batch(batch: LiveSelectionBatch) -> LiveSelectionBatch:
    if any(item.state is SelectionState.CONFIRMED for item in batch.candidates):
        raise ValueError("persisted R1 batch cannot contain CONFIRMED")
    stored = batch.model_copy(update={"persisted": True, "storage": "STORED"})
    payload = _strip_computed(stored.model_dump(mode="json", by_alias=True))
    now = datetime.now(UTC).isoformat()
    storage.init_db()
    conn = storage.connect()
    try:
        conn.execute(
            """
            INSERT INTO selection_scan_runs (
                run_id, profile_id, as_of, persisted_at, payload_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                stored.run.run_id,
                stored.run.profile_id,
                stored.run.as_of.isoformat(),
                now,
                storage.encode_json(payload),
            ),
        )
        for candidate in stored.candidates:
            conn.execute(
                """
                INSERT INTO selection_candidates (
                    run_id, candidate_id, symbol, state, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    stored.run.run_id,
                    candidate.candidate_id,
                    candidate.instrument.symbol,
                    candidate.state.value,
                    storage.encode_json(
                        _strip_computed(
                            candidate.model_dump(mode="json", by_alias=True)
                        )
                    ),
                ),
            )
            event_id = stable_id("evt", stored.run.run_id, candidate.candidate_id)
            conn.execute(
                """
                INSERT INTO selection_state_events (
                    event_id, run_id, candidate_id, sequence, prior_state,
                    resulting_state, accepted, reason_code, payload_json, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    stored.run.run_id,
                    candidate.candidate_id,
                    1,
                    SelectionState.WAIT.value,
                    candidate.state.value,
                    0,
                    "WAIT_SOURCE_ACTIVATION",
                    storage.encode_json(
                        {
                            "reason": "R1 persist records WAIT; confirmation is not accepted.",
                            "gateCodes": [gate.code for gate in candidate.gate_results],
                        }
                    ),
                    now,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return stored


def apply_comparable_diff(
    current: LiveSelectionBatch, prior: LiveSelectionBatch | None
) -> LiveSelectionBatch:
    if prior is None:
        return current
    prior_by_symbol = {
        item.instrument.symbol: item for item in prior.candidates
    }
    updated: list[SelectionCandidate] = []
    for candidate in current.candidates:
        previous = prior_by_symbol.get(candidate.instrument.symbol)
        if previous is None:
            updated.append(
                candidate.model_copy(
                    update={
                        "comparable_baseline": "COMPARED",
                        "comparable_run_id": prior.run.run_id,
                        "change_kinds": ("VERSION",),
                        "what_changed": "NEW_SYMBOL",
                    }
                )
            )
            continue
        kinds: list[str] = ["VERSION"]
        if previous.state != candidate.state:
            kinds.append("STATE")
        if previous.gate_results != candidate.gate_results:
            kinds.append("GATE")
        if previous.family_missing != candidate.family_missing:
            kinds.append("FAMILY")
        if previous.freshness != candidate.freshness:
            kinds.append("FRESHNESS")
        if previous.completeness != candidate.completeness:
            kinds.append("COMPLETENESS")
        updated.append(
            candidate.model_copy(
                update={
                    "comparable_baseline": "COMPARED",
                    "comparable_run_id": prior.run.run_id,
                    "change_kinds": tuple(kinds),
                    "what_changed": ",".join(kinds),
                }
            )
        )
    return current.model_copy(update={"candidates": tuple(updated)})
