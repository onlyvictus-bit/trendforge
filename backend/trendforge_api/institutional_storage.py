from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from . import storage
from .institutional_backtest import WalkForwardReport
from .institutional_config import InstitutionalConfig
from .institutional_engine import (
    InstitutionalAnalysisRequest,
    InstitutionalAnalysisResult,
)


def _initialize() -> None:
    storage.init_db()
    with storage.connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS institutional_analysis_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                market TEXT NOT NULL,
                as_of TEXT NOT NULL,
                classification TEXT NOT NULL,
                state TEXT NOT NULL,
                executable INTEGER NOT NULL DEFAULT 0,
                config_version TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                request_json TEXT NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_institutional_reports_symbol_asof
            ON institutional_analysis_reports(symbol, as_of, created_at)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS institutional_walk_forward_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_version TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                observation_count INTEGER NOT NULL,
                evaluation_count INTEGER NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO schema_migrations(version, description, applied_at)
            VALUES (?, ?, ?)
            """,
            (
                "0019_institutional_multifactor_engine",
                "Config-versioned institutional source, factor, AI, risk and walk-forward audit records",
                datetime.now(UTC).isoformat(),
            ),
        )


def save_analysis_report(
    request: InstitutionalAnalysisRequest,
    result: InstitutionalAnalysisResult,
    config: InstitutionalConfig,
) -> int:
    _initialize()
    with storage.connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO institutional_analysis_reports(
                symbol, timeframe, market, as_of, classification, state,
                executable, config_version, config_hash, request_json,
                report_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.symbol,
                result.timeframe,
                result.market,
                result.as_of.isoformat(),
                result.classification,
                result.state,
                int(result.executable),
                config.version,
                config.config_hash,
                request.model_dump_json(by_alias=True),
                result.model_dump_json(by_alias=True),
                datetime.now(UTC).isoformat(),
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Institutional analysis was not assigned an audit id")
        return int(cursor.lastrowid)


def list_analysis_reports(
    *, symbol: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    _initialize()
    query = "SELECT * FROM institutional_analysis_reports"
    parameters: list[Any] = []
    if symbol:
        query += " WHERE symbol = ?"
        parameters.append(symbol.upper().strip())
    query += " ORDER BY created_at DESC LIMIT ?"
    parameters.append(limit)
    with storage.connect() as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [
        {
            "id": row["id"],
            "symbol": row["symbol"],
            "timeframe": row["timeframe"],
            "market": row["market"],
            "asOf": row["as_of"],
            "classification": row["classification"],
            "state": row["state"],
            "executable": bool(row["executable"]),
            "configVersion": row["config_version"],
            "configHash": row["config_hash"],
            "request": json.loads(row["request_json"]),
            "report": json.loads(row["report_json"]),
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def save_walk_forward_report(
    report: WalkForwardReport, config: InstitutionalConfig
) -> int:
    _initialize()
    with storage.connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO institutional_walk_forward_runs(
                config_version, config_hash, observation_count,
                evaluation_count, report_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                config.version,
                config.config_hash,
                report.observation_count,
                report.evaluation_count,
                report.model_dump_json(by_alias=True),
                datetime.now(UTC).isoformat(),
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Walk-forward report was not assigned an audit id")
        return int(cursor.lastrowid)
