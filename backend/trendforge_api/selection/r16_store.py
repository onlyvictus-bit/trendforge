"""Approval-gated normalized R16 schema, immutable rows, and replay lease."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Iterable

from .. import storage

MIGRATION_VERSION = "0013_r16_pit_substrate"
TABLES = (
    "pit_dataset_runs",
    "pit_hypotheses",
    "pit_observations",
    "pit_fold_results",
    "pit_metrics",
    "pit_approval_ledger",
)
WORKER_TABLE = "pit_worker_state"


def _now() -> datetime:
    return datetime.now(UTC)


def r16_schema_status() -> dict[str, Any]:
    from ..r16_retention import schema_ready

    storage.init_db()
    conn = storage.connect()
    try:
        existing = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        migration = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?",
            (MIGRATION_VERSION,),
        ).fetchone()
        retention_ready = schema_ready(conn)
    finally:
        conn.close()
    present = tuple(name for name in TABLES if name in existing)
    return {
        "migrationVersion": MIGRATION_VERSION,
        "applied": migration is not None and len(present) == len(TABLES),
        "tables": present,
        "missingTables": tuple(name for name in TABLES if name not in existing),
        "workerStateReady": WORKER_TABLE in existing,
        "retentionReady": retention_ready,
    }


def apply_r16_schema() -> dict[str, Any]:
    """Apply R16 explicitly; ordinary storage.init_db never calls this."""

    storage.init_db()
    now = _now().isoformat()
    conn = storage.connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pit_dataset_runs (
                run_id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                profile_version TEXT NOT NULL,
                market TEXT NOT NULL,
                horizon TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                cutoff_at TEXT NOT NULL,
                source_s8_run_id TEXT NOT NULL,
                source_s8_hash TEXT NOT NULL,
                universe_hash TEXT NOT NULL,
                dataset_revision_hash TEXT NOT NULL,
                dataset_status TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(profile_id, trading_date, source_s8_run_id, dataset_revision_hash)
            );
            CREATE INDEX IF NOT EXISTS idx_pit_dataset_runs_profile_date
                ON pit_dataset_runs(profile_id, trading_date DESC, run_id);
            CREATE INDEX IF NOT EXISTS idx_pit_dataset_runs_revision
                ON pit_dataset_runs(dataset_revision_hash, dataset_status, run_id);

            CREATE TABLE IF NOT EXISTS pit_hypotheses (
                hypothesis_id TEXT PRIMARY KEY,
                dataset_run_id TEXT NOT NULL,
                exact_cell TEXT NOT NULL,
                dataset_revision_hash TEXT NOT NULL,
                source_s8_run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                horizon_sessions INTEGER NOT NULL,
                public_state TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                cutoff_at TEXT NOT NULL,
                geometry_status TEXT NOT NULL,
                setup_policy_id TEXT NOT NULL,
                entry_low REAL,
                entry_high REAL,
                invalidation REAL,
                target_1 REAL,
                target_2 REAL,
                exclusion_reason TEXT,
                content_hash TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (dataset_run_id) REFERENCES pit_dataset_runs(run_id),
                UNIQUE(dataset_run_id, hypothesis_id)
            );
            CREATE INDEX IF NOT EXISTS idx_pit_hypotheses_dataset_symbol
                ON pit_hypotheses(dataset_run_id, symbol, horizon_sessions);
            CREATE INDEX IF NOT EXISTS idx_pit_hypotheses_cell_date
                ON pit_hypotheses(exact_cell, trading_date, geometry_status, hypothesis_id);

            CREATE TABLE IF NOT EXISTS pit_observations (
                observation_id TEXT PRIMARY KEY,
                hypothesis_id TEXT NOT NULL,
                dataset_run_id TEXT NOT NULL,
                dataset_revision_hash TEXT NOT NULL,
                horizon_sessions INTEGER NOT NULL,
                status TEXT NOT NULL,
                label_computed_at TEXT NOT NULL,
                entry_at TEXT,
                outcome_at TEXT,
                path_hash TEXT NOT NULL,
                costs_declared INTEGER NOT NULL,
                intrabar_ambiguous INTEGER NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (hypothesis_id) REFERENCES pit_hypotheses(hypothesis_id),
                FOREIGN KEY (dataset_run_id) REFERENCES pit_dataset_runs(run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_pit_observations_hypothesis_latest
                ON pit_observations(hypothesis_id, label_computed_at DESC, observation_id);
            CREATE INDEX IF NOT EXISTS idx_pit_observations_dataset_status
                ON pit_observations(dataset_run_id, status, horizon_sessions, observation_id);

            CREATE TABLE IF NOT EXISTS pit_fold_results (
                fold_id TEXT PRIMARY KEY,
                dataset_run_id TEXT NOT NULL,
                exact_cell TEXT NOT NULL,
                fold_index INTEGER NOT NULL,
                train_start TEXT NOT NULL,
                train_end TEXT NOT NULL,
                test_start TEXT NOT NULL,
                test_end TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (dataset_run_id) REFERENCES pit_dataset_runs(run_id),
                UNIQUE(dataset_run_id, exact_cell, fold_index, content_hash)
            );
            CREATE INDEX IF NOT EXISTS idx_pit_folds_cell
                ON pit_fold_results(dataset_run_id, exact_cell, fold_index);

            CREATE TABLE IF NOT EXISTS pit_metrics (
                metric_id TEXT PRIMARY KEY,
                dataset_run_id TEXT NOT NULL,
                exact_cell TEXT NOT NULL,
                dataset_revision_hash TEXT NOT NULL,
                observation_set_hash TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (dataset_run_id) REFERENCES pit_dataset_runs(run_id),
                UNIQUE(dataset_run_id, exact_cell, observation_set_hash)
            );
            CREATE INDEX IF NOT EXISTS idx_pit_metrics_cell_latest
                ON pit_metrics(exact_cell, created_at DESC, metric_id);

            CREATE TABLE IF NOT EXISTS pit_approval_ledger (
                ledger_id TEXT PRIMARY KEY,
                dataset_run_id TEXT NOT NULL,
                exact_cell TEXT NOT NULL,
                dataset_status TEXT NOT NULL,
                validation_status TEXT NOT NULL,
                approval_scope TEXT NOT NULL,
                profile_conclusion TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                actor TEXT NOT NULL,
                reason TEXT NOT NULL,
                probability_authorized INTEGER NOT NULL,
                confirmation_authorized INTEGER NOT NULL,
                execution_authorized INTEGER NOT NULL,
                blockers_json TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (dataset_run_id) REFERENCES pit_dataset_runs(run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_pit_approval_cell_created
                ON pit_approval_ledger(exact_cell, created_at DESC, ledger_id);
            CREATE INDEX IF NOT EXISTS idx_pit_approval_dataset_created
                ON pit_approval_ledger(dataset_run_id, created_at DESC, ledger_id);

            CREATE TABLE IF NOT EXISTS pit_worker_state (
                lease_key TEXT PRIMARY KEY,
                owner_id TEXT,
                acquired_at TEXT,
                expires_at TEXT,
                checkpoint_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) "
            "VALUES (?, ?, ?)",
            (
                MIGRATION_VERSION,
                "R16 normalized PIT substrate with append-only replay and approval",
                now,
            ),
        )
        from ..r16_retention import apply_schema

        apply_schema(conn)
        conn.commit()
    finally:
        conn.close()
    return r16_schema_status()


def _require_schema() -> None:
    if not r16_schema_status()["applied"]:
        raise RuntimeError("WAIT_R16_SCHEMA_NOT_APPLIED")


def _content_hash(payload: dict[str, Any]) -> str:
    import hashlib

    return hashlib.sha256(storage.encode_json(payload).encode()).hexdigest()


def _existing_payload(conn, table: str, key_column: str, key: str) -> str | None:
    row = conn.execute(
        f"SELECT payload_json FROM {table} WHERE {key_column} = ?", (key,)
    ).fetchone()
    return row["payload_json"] if row else None


def persist_dataset_run(payload: dict[str, Any]) -> bool:
    _require_schema()
    encoded = storage.encode_json(payload)
    run_id = str(payload["runId"])
    conn = storage.connect()
    try:
        existing = _existing_payload(conn, "pit_dataset_runs", "run_id", run_id)
        if existing is not None:
            if existing != encoded:
                raise ValueError(f"PIT dataset run {run_id} is immutable")
            return False
        conn.execute(
            """
            INSERT INTO pit_dataset_runs (
                run_id, profile_id, profile_version, market, horizon,
                trading_date, cutoff_at, source_s8_run_id, source_s8_hash,
                universe_hash, dataset_revision_hash, dataset_status,
                policy_version, content_hash, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id, payload["profileId"], payload["profileVersion"],
                payload["market"], payload["horizon"], payload["tradingDate"],
                payload["cutoffAt"], payload["sourceS8RunId"],
                payload["sourceS8Hash"], payload["universeHash"],
                payload["datasetRevisionHash"], payload["datasetStatus"],
                payload["policyVersion"], _content_hash(payload), encoded,
                _now().isoformat(),
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def persist_hypotheses(dataset_run_id: str, rows: Iterable[dict[str, Any]]) -> int:
    from ..r16_retention import R16RetentionWriter, finalize_publications
    from .r16_metrics import exact_cell_key
    from .r16_pit import R16FrozenHypothesisV1

    _require_schema()
    conn = storage.connect()
    inserted = 0
    publications: list[str] = []
    try:
        conn.execute("BEGIN IMMEDIATE")
        writer = R16RetentionWriter(conn)
        for payload in rows:
            model = R16FrozenHypothesisV1.model_validate(payload)
            encoded = storage.encode_json(payload)
            existing = _existing_payload(
                conn, "pit_hypotheses", "hypothesis_id", model.hypothesis_id
            )
            if existing is not None:
                if existing != encoded:
                    raise ValueError(f"PIT hypothesis {model.hypothesis_id} is immutable")
                publications.append(writer.hypothesis(dataset_run_id, payload))
                continue
            conn.execute(
                """
                INSERT INTO pit_hypotheses (
                    hypothesis_id, dataset_run_id, exact_cell,
                    dataset_revision_hash, source_s8_run_id, symbol, direction,
                    horizon_sessions, public_state, trading_date, cutoff_at,
                    geometry_status, setup_policy_id, entry_low, entry_high,
                    invalidation, target_1, target_2, exclusion_reason,
                    content_hash, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model.hypothesis_id, dataset_run_id, exact_cell_key(model),
                    model.dataset_revision_hash, model.source_s8_run_id,
                    model.symbol, model.direction, model.horizon_sessions,
                    model.public_state, model.trading_date,
                    model.decision_cutoff_at.isoformat(), model.geometry_status,
                    model.setup_policy_id, model.entry_low, model.entry_high,
                    model.invalidation, model.target_1, model.target_2,
                    model.exclusion_reason, _content_hash(payload), encoded,
                    _now().isoformat(),
                ),
            )
            inserted += 1
            publications.append(writer.hypothesis(dataset_run_id, payload))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    finalize_publications(publications)
    return inserted


def persist_observations(dataset_run_id: str, rows: Iterable[dict[str, Any]]) -> int:
    from ..r16_retention import R16RetentionWriter, finalize_publications
    from .r16_pit import R16ObservationV1

    _require_schema()
    conn = storage.connect()
    inserted = 0
    publications: list[str] = []
    try:
        conn.execute("BEGIN IMMEDIATE")
        writer = R16RetentionWriter(conn)
        for payload in rows:
            model = R16ObservationV1.model_validate(payload)
            encoded = storage.encode_json(payload)
            existing = _existing_payload(
                conn, "pit_observations", "observation_id", model.observation_id
            )
            if existing is not None:
                if existing != encoded:
                    raise ValueError(f"PIT observation {model.observation_id} is immutable")
                publications.append(writer.observation(dataset_run_id, payload))
                continue
            conn.execute(
                """
                INSERT INTO pit_observations (
                    observation_id, hypothesis_id, dataset_run_id,
                    dataset_revision_hash, horizon_sessions, status,
                    label_computed_at, entry_at, outcome_at, path_hash,
                    costs_declared, intrabar_ambiguous, content_hash,
                    payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model.observation_id, model.hypothesis_id, dataset_run_id,
                    model.dataset_revision_hash, model.horizon_sessions,
                    model.status, model.label_computed_at.isoformat(),
                    model.entry_at.isoformat() if model.entry_at else None,
                    model.outcome_at.isoformat() if model.outcome_at else None,
                    model.path_hash, int(model.costs_declared),
                    int(model.intrabar_ambiguous), _content_hash(payload),
                    encoded, _now().isoformat(),
                ),
            )
            inserted += 1
            publications.append(writer.observation(dataset_run_id, payload))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    finalize_publications(publications)
    return inserted


def persist_revisions(dataset_run_id: str, rows: Iterable[dict[str, Any]]) -> int:
    from ..r16_retention import R16RetentionWriter, finalize_publications
    from .r16_pit import R16RevisionV1

    _require_schema()
    conn = storage.connect()
    publications: list[str] = []
    inserted = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        writer = R16RetentionWriter(conn)
        for payload in rows:
            model = R16RevisionV1.model_validate(payload)
            encoded = storage.encode_json(payload)
            existing = _existing_payload(conn, "pit_revisions", "revision_id", model.revision_id)
            if existing is not None:
                if existing != encoded:
                    raise ValueError(f"PIT revision {model.revision_id} is immutable")
            else:
                conn.execute(
                    "INSERT INTO pit_revisions (revision_id, hypothesis_id, dataset_run_id, "
                    "predecessor_type, predecessor_id, predecessor_hash, revision_kind, "
                    "recorded_at, content_hash, payload_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (model.revision_id, model.hypothesis_id, dataset_run_id,
                     model.predecessor_type, model.predecessor_id, model.predecessor_hash,
                     model.revision_kind, model.recorded_at.isoformat(), _content_hash(payload),
                     encoded, _now().isoformat()),
                )
                inserted += 1
            publications.append(writer.revision(dataset_run_id, payload))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    finalize_publications(publications)
    return inserted


def persist_fold(payload: dict[str, Any]) -> bool:
    _require_schema()
    encoded = storage.encode_json(payload)
    fold_id = str(payload["foldId"])
    conn = storage.connect()
    try:
        existing = _existing_payload(conn, "pit_fold_results", "fold_id", fold_id)
        if existing is not None:
            if existing != encoded:
                raise ValueError(f"PIT fold {fold_id} is immutable")
            return False
        conn.execute(
            """
            INSERT INTO pit_fold_results (
                fold_id, dataset_run_id, exact_cell, fold_index,
                train_start, train_end, test_start, test_end,
                content_hash, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fold_id, payload["datasetRunId"], payload["exactCell"],
                int(payload["foldIndex"]), payload["trainStart"],
                payload["trainEnd"], payload["testStart"], payload["testEnd"],
                _content_hash(payload), encoded, _now().isoformat(),
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def persist_metric(payload: dict[str, Any]) -> bool:
    _require_schema()
    encoded = storage.encode_json(payload)
    metric_id = str(payload["metricId"])
    conn = storage.connect()
    try:
        existing = _existing_payload(conn, "pit_metrics", "metric_id", metric_id)
        if existing is not None:
            if existing != encoded:
                raise ValueError(f"PIT metric {metric_id} is immutable")
            return False
        conn.execute(
            """
            INSERT INTO pit_metrics (
                metric_id, dataset_run_id, exact_cell, dataset_revision_hash,
                observation_set_hash, content_hash, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metric_id, payload["datasetRunId"], payload["exactCell"],
                payload["datasetRevisionHash"], payload["observationSetHash"],
                _content_hash(payload), encoded, _now().isoformat(),
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def persist_approval(payload: dict[str, Any]) -> bool:
    _require_schema()
    encoded = storage.encode_json(payload)
    ledger_id = str(payload["ledgerId"])
    conn = storage.connect()
    try:
        existing = _existing_payload(
            conn, "pit_approval_ledger", "ledger_id", ledger_id
        )
        if existing is not None:
            if existing != encoded:
                raise ValueError(f"PIT approval {ledger_id} is immutable")
            return False
        conn.execute(
            """
            INSERT INTO pit_approval_ledger (
                ledger_id, dataset_run_id, exact_cell, dataset_status,
                validation_status, approval_scope, profile_conclusion,
                policy_version, evidence_hash, actor, reason,
                probability_authorized, confirmation_authorized,
                execution_authorized, blockers_json, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ledger_id, payload["datasetRunId"], payload["exactCell"],
                payload["datasetStatus"], payload["validationStatus"],
                payload["approvalScope"], payload["profileConclusion"],
                payload["policyVersion"], payload["evidenceHash"],
                payload["actor"], payload["reason"],
                int(bool(payload["probabilityAuthorized"])),
                int(bool(payload["confirmationAuthorized"])),
                int(bool(payload["executionAuthorized"])),
                storage.encode_json(payload.get("blockers") or []),
                encoded, _now().isoformat(),
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def _page(
    table: str,
    *,
    limit: int,
    cursor: int | None = None,
    where: str = "",
    params: tuple[Any, ...] = (),
) -> dict[str, Any]:
    from ..r16_retention import RECORD_TABLES, publication_predicate, schema_ready, verified_record

    _require_schema()
    if table not in (*TABLES, "pit_revisions"):
        raise ValueError("unsupported PIT table")
    page_size = max(1, min(int(limit), 1000))
    clauses = [where.removeprefix("WHERE ")] if where else []
    governed = next(((kind, key) for kind, (name, key) in RECORD_TABLES.items() if name == table), None)
    if governed:
        clauses.append(publication_predicate(table))
    values: list[Any] = list(params)
    if cursor is not None:
        clauses.append("rowid < ?")
        values.append(int(cursor))
    predicate = " WHERE " + " AND ".join(clauses) if clauses else ""
    conn = storage.connect()
    try:
        if governed and not schema_ready(conn):
            return {"items": [], "nextCursor": None}
        rows = conn.execute(
            f"SELECT rowid AS cursor_id, payload_json FROM {table}"
            f"{predicate} ORDER BY rowid DESC LIMIT ?",
            (*values, page_size + 1),
        ).fetchall()
        if governed:
            kind, key = governed
            identity_key = {"hypothesis_id": "hypothesisId", "observation_id": "observationId", "revision_id": "revisionId"}[key]
            for row in rows[:page_size]:
                payload = storage.decode_json(row["payload_json"])
                verified_record(conn, kind, payload[identity_key])
    finally:
        conn.close()
    has_more = len(rows) > page_size
    selected = rows[:page_size]
    items = [storage.decode_json(row["payload_json"]) for row in selected]
    next_cursor = selected[-1]["cursor_id"] if has_more and selected else None
    return {
        "items": items,
        "nextCursor": str(next_cursor) if next_cursor is not None else None,
    }


def page_dataset_runs(limit: int = 50, cursor: int | None = None) -> dict[str, Any]:
    return _page("pit_dataset_runs", limit=limit, cursor=cursor)


def page_observations(
    dataset_run_id: str | None = None,
    *,
    limit: int = 200,
    cursor: int | None = None,
) -> dict[str, Any]:
    return _page(
        "pit_observations",
        limit=limit,
        cursor=cursor,
        where="WHERE dataset_run_id = ?" if dataset_run_id else "",
        params=(dataset_run_id,) if dataset_run_id else (),
    )


def _list_all(
    table: str,
    *,
    limit: int,
    where: str = "",
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    remaining = max(1, min(int(limit), 500000))
    cursor: int | None = None
    output: list[dict[str, Any]] = []
    while remaining > 0:
        page = _page(
            table,
            limit=min(remaining, 1000),
            cursor=cursor,
            where=where,
            params=params,
        )
        output.extend(page["items"])
        remaining -= len(page["items"])
        next_cursor = page["nextCursor"]
        if next_cursor is None or not page["items"]:
            break
        cursor = int(next_cursor)
    return output


def list_dataset_runs(limit: int = 50) -> list[dict[str, Any]]:
    return _list_all("pit_dataset_runs", limit=limit)


def list_hypotheses(
    dataset_run_id: str | None = None, limit: int = 5000
) -> list[dict[str, Any]]:
    return _list_all(
        "pit_hypotheses",
        limit=limit,
        where="WHERE dataset_run_id = ?" if dataset_run_id else "",
        params=(dataset_run_id,) if dataset_run_id else (),
    )


def list_observations(
    dataset_run_id: str | None = None, limit: int = 5000
) -> list[dict[str, Any]]:
    return _list_all(
        "pit_observations",
        limit=limit,
        where="WHERE dataset_run_id = ?" if dataset_run_id else "",
        params=(dataset_run_id,) if dataset_run_id else (),
    )


def list_revisions(hypothesis_id: str | None = None, limit: int = 5000) -> list[dict[str, Any]]:
    return _list_all(
        "pit_revisions", limit=limit,
        where="WHERE hypothesis_id = ?" if hypothesis_id else "",
        params=(hypothesis_id,) if hypothesis_id else (),
    )


def list_latest_observations(limit: int = 10000) -> list[dict[str, Any]]:
    from ..r16_retention import publication_predicate, schema_ready, verified_record

    _require_schema()
    conn = storage.connect()
    try:
        if not schema_ready(conn):
            return []
        protected = publication_predicate("pit_observations")
        rows = conn.execute(
            f"""
            SELECT o.payload_json
            FROM pit_observations o
            WHERE {protected.replace('pit_observations.', 'o.')} AND o.rowid = (
                SELECT o2.rowid FROM pit_observations o2
                WHERE o2.hypothesis_id = o.hypothesis_id
                  AND {protected.replace('pit_observations.', 'o2.')}
                ORDER BY o2.label_computed_at DESC, o2.rowid DESC
                LIMIT 1
            )
            ORDER BY o.rowid DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 500000)),),
        ).fetchall()
        payloads = [storage.decode_json(row["payload_json"]) for row in rows]
        for payload in payloads:
            verified_record(conn, "OUTCOME", payload["observationId"])
        return payloads
    finally:
        conn.close()


def list_folds(dataset_run_id: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    return _page(
        "pit_fold_results",
        limit=limit,
        where="WHERE dataset_run_id = ?" if dataset_run_id else "",
        params=(dataset_run_id,) if dataset_run_id else (),
    )["items"]


def list_metrics(dataset_run_id: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    return _page(
        "pit_metrics",
        limit=limit,
        where="WHERE dataset_run_id = ?" if dataset_run_id else "",
        params=(dataset_run_id,) if dataset_run_id else (),
    )["items"]


def list_approvals(dataset_run_id: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    return _page(
        "pit_approval_ledger",
        limit=limit,
        where="WHERE dataset_run_id = ?" if dataset_run_id else "",
        params=(dataset_run_id,) if dataset_run_id else (),
    )["items"]


def acquire_worker_lease(
    owner_id: str,
    *,
    now: datetime | None = None,
    ttl_seconds: int = 900,
) -> bool:
    _require_schema()
    instant = now or _now()
    expires = instant + timedelta(seconds=max(30, ttl_seconds))
    conn = storage.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT owner_id, expires_at FROM pit_worker_state WHERE lease_key = ?",
            ("r16-replay",),
        ).fetchone()
        if row and row["owner_id"] != owner_id:
            expiry = datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            if expiry and expiry > instant:
                conn.rollback()
                return False
        conn.execute(
            """
            INSERT INTO pit_worker_state (
                lease_key, owner_id, acquired_at, expires_at,
                checkpoint_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(lease_key) DO UPDATE SET
                owner_id=excluded.owner_id,
                acquired_at=excluded.acquired_at,
                expires_at=excluded.expires_at,
                updated_at=excluded.updated_at
            """,
            (
                "r16-replay", owner_id, instant.isoformat(), expires.isoformat(),
                storage.encode_json({}), instant.isoformat(),
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def save_worker_checkpoint(owner_id: str, checkpoint: dict[str, Any]) -> None:
    _require_schema()
    conn = storage.connect()
    try:
        cursor = conn.execute(
            """
            UPDATE pit_worker_state
            SET checkpoint_json = ?, updated_at = ?
            WHERE lease_key = ? AND owner_id = ?
            """,
            (
                storage.encode_json(checkpoint), _now().isoformat(),
                "r16-replay", owner_id,
            ),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("WAIT_R16_LEASE_NOT_OWNED")
        conn.commit()
    finally:
        conn.close()


def release_worker_lease(owner_id: str) -> None:
    _require_schema()
    conn = storage.connect()
    try:
        conn.execute(
            """
            UPDATE pit_worker_state
            SET owner_id = NULL, expires_at = NULL, updated_at = ?
            WHERE lease_key = ? AND owner_id = ?
            """,
            (_now().isoformat(), "r16-replay", owner_id),
        )
        conn.commit()
    finally:
        conn.close()


def worker_state() -> dict[str, Any] | None:
    _require_schema()
    conn = storage.connect()
    try:
        row = conn.execute(
            "SELECT * FROM pit_worker_state WHERE lease_key = ?", ("r16-replay",)
        ).fetchone()
        if not row:
            return None
        payload = dict(row)
        payload["checkpoint"] = storage.decode_json(payload.pop("checkpoint_json"))
        return payload
    finally:
        conn.close()


def query_plan(table: str, index_probe_sql: str, params: tuple[Any, ...]) -> list[str]:
    _require_schema()
    if table not in TABLES:
        raise ValueError("unsupported PIT query-plan table")
    conn = storage.connect()
    try:
        rows = conn.execute("EXPLAIN QUERY PLAN " + index_probe_sql, params).fetchall()
        return [str(row["detail"]) for row in rows]
    finally:
        conn.close()


__all__ = [
    "MIGRATION_VERSION", "TABLES", "acquire_worker_lease",
    "apply_r16_schema", "list_approvals", "list_dataset_runs", "list_folds",
    "list_hypotheses", "list_latest_observations", "list_metrics",
    "list_observations", "page_dataset_runs", "page_observations",
    "persist_approval", "persist_dataset_run", "persist_fold",
    "persist_hypotheses", "persist_metric", "persist_observations",
    "query_plan", "r16_schema_status", "release_worker_lease",
    "save_worker_checkpoint", "worker_state",
]