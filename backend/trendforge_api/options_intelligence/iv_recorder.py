"""Append-only IV-surface and option-chain snapshot recorders (Day 1).

IV Rank needs at least one year of stored surfaces; until then the rank
stays UNKNOWN. The recorder still writes today - that is its whole
purpose. Missing IV never becomes zero and rank is never invented.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from .. import storage

_IV_TABLE = """
CREATE TABLE IF NOT EXISTS iv_surface_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    underlying TEXT NOT NULL,
    expiry TEXT NOT NULL,
    data_date TEXT,
    artifact_hash TEXT,
    atm_iv REAL,
    rank_status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    persisted_at TEXT NOT NULL
)
"""

_CHAIN_TABLE = """
CREATE TABLE IF NOT EXISTS option_chain_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    underlying TEXT NOT NULL,
    expiry TEXT NOT NULL,
    quality_state TEXT NOT NULL,
    spot REAL,
    artifact_hash TEXT,
    payload_json TEXT NOT NULL,
    persisted_at TEXT NOT NULL
)
"""


def _connect():
    storage.init_db()
    conn = storage.connect()
    conn.execute(_IV_TABLE)
    conn.execute(_CHAIN_TABLE)
    conn.commit()
    return conn


def record_iv_surface(
    *,
    underlying: str,
    expiry: str,
    rows: list[dict[str, Any]],
    atm_iv: float | None,
    data_date: str | None = None,
) -> dict[str, Any]:
    """Append one IV surface observation. Always inserts a row."""
    payload_json = storage.encode_json(rows)
    artifact_hash = hashlib.sha256(payload_json.encode()).hexdigest()
    history_days = _iv_history_days(underlying)
    rank_status = (
        "RANK_COMPUTABLE"
        if history_days >= 365
        else "UNKNOWN_INSUFFICIENT_HISTORY"
    )
    now = datetime.now(UTC).isoformat()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO iv_surface_snapshots (
                underlying, expiry, data_date, artifact_hash, atm_iv,
                rank_status, payload_json, persisted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                underlying.upper(),
                expiry,
                data_date,
                artifact_hash,
                atm_iv,
                rank_status,
                payload_json,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "underlying": underlying.upper(),
        "expiry": expiry,
        "atmIv": atm_iv,
        "rankStatus": rank_status,
        "historyDays": history_days,
        "artifactHash": artifact_hash,
        "persistedAt": now,
    }


def _iv_history_days(underlying: str) -> int:
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT MIN(persisted_at) AS first, MAX(persisted_at) AS last
            FROM iv_surface_snapshots WHERE underlying = ?
            """,
            (underlying.upper(),),
        ).fetchone()
    finally:
        conn.close()
    if row is None or row["first"] is None:
        return 0
    first = datetime.fromisoformat(row["first"])
    span = datetime.now(UTC) - first
    return max(0, span.days)


def record_chain_snapshot(
    *,
    underlying: str,
    expiry: str,
    quality_state: str,
    spot: float | None,
    payload: Any,
) -> str:
    payload_json = storage.encode_json(payload)
    artifact_hash = hashlib.sha256(payload_json.encode()).hexdigest()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO option_chain_snapshots (
                underlying, expiry, quality_state, spot, artifact_hash,
                payload_json, persisted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                underlying.upper(),
                expiry,
                quality_state,
                spot,
                artifact_hash,
                payload_json,
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return artifact_hash


def chain_snapshots(
    *, underlying: str, expiry: str | None = None, limit: int = 2
) -> list[dict[str, Any]]:
    """Newest-first snapshots; expiry=None spans every expiry (PCR path)."""
    conn = _connect()
    try:
        if expiry is None:
            rows = conn.execute(
                """
                SELECT * FROM option_chain_snapshots
                WHERE underlying = ?
                ORDER BY id DESC LIMIT ?
                """,
                (underlying.upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM option_chain_snapshots
                WHERE underlying = ? AND expiry = ?
                ORDER BY id DESC LIMIT ?
                """,
                (underlying.upper(), expiry, limit),
            ).fetchall()
    finally:
        conn.close()
    return [
        {
            "underlying": row["underlying"],
            "expiry": row["expiry"],
            "qualityState": row["quality_state"],
            "spot": row["spot"],
            "artifactHash": row["artifact_hash"],
            "payload": storage.decode_json(row["payload_json"]),
            "persistedAt": row["persisted_at"],
        }
        for row in rows
    ]


def latest_chain_snapshot(*, underlying: str, expiry: str) -> dict[str, Any] | None:
    snapshots = chain_snapshots(underlying=underlying, expiry=expiry, limit=1)
    return snapshots[0] if snapshots else None


def chain_snapshot_count(*, underlying: str, expiry: str) -> int:
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n FROM option_chain_snapshots
            WHERE underlying = ? AND expiry = ?
            """,
            (underlying.upper(), expiry),
        ).fetchone()
    finally:
        conn.close()
    return int(row["n"]) if row is not None else 0
