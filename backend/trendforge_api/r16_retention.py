"""R-HIST-03C: exact-parent R16 publication, never latest-data inference.

The canonical artifacts remain in the existing PIT tables. Their immutable link
and retention outbox are committed in the same transaction. Public readers see
only PUBLISHED links; a crash can leave hidden rows, never successful unprotected
history. Replaying the producer command completes the same publication.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from . import storage
from .historical_retention import HistoricalRetentionAuthority, RetentionReferenceType
from .retention_producer import DurableRetentionRegistrar, RetentionEvidenceIntent
from .retention_publication import (
    RetentionEvidenceRoot,
    RetentionPublicationRequest,
    RetentionPublicationStatus,
    RetentionPublicationStore,
)
from .s8_retention import resolve_market_db_path
from .selection.r16_pit import (
    R16FrozenHypothesisV1,
    R16ObservationV1,
    R16RevisionV1,
    _payload_hash,
    build_frozen_hypotheses,
)

MIGRATION_VERSION = "0023_r16_outcome_revision_retention"
RECORD_TABLES = {
    "DECISION_VERSION": ("pit_hypotheses", "hypothesis_id"),
    "OUTCOME": ("pit_observations", "observation_id"),
    "REVISION": ("pit_revisions", "revision_id"),
}


def _fail(reason: str) -> RuntimeError:
    return RuntimeError("WAIT_RHIST03_" + reason)


def apply_schema(connection: sqlite3.Connection) -> None:
    """Called only by the explicitly approved R16 schema command, not by GET."""
    connection.execute("""
        CREATE TABLE IF NOT EXISTS pit_revisions (
            revision_id TEXT PRIMARY KEY, hypothesis_id TEXT NOT NULL,
            dataset_run_id TEXT NOT NULL, predecessor_type TEXT NOT NULL,
            predecessor_id TEXT NOT NULL, predecessor_hash TEXT NOT NULL,
            revision_kind TEXT NOT NULL, recorded_at TEXT NOT NULL,
            content_hash TEXT NOT NULL UNIQUE, payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(hypothesis_id) REFERENCES pit_hypotheses(hypothesis_id),
            FOREIGN KEY(dataset_run_id) REFERENCES pit_dataset_runs(run_id)
        )
    """)
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_pit_revision_parent "
        "ON pit_revisions(hypothesis_id, recorded_at, revision_id)"
    )
    connection.execute("""
        CREATE TABLE IF NOT EXISTS pit_retention_links (
            record_type TEXT NOT NULL, record_id TEXT NOT NULL,
            publication_id TEXT NOT NULL UNIQUE, payload_hash TEXT NOT NULL,
            PRIMARY KEY(record_type, record_id),
            FOREIGN KEY(publication_id)
                REFERENCES historical_retention_publications(publication_id)
        )
    """)
    RetentionPublicationStore(db_path=Path(storage.DB_PATH)).initialize_schema(
        connection=connection
    )
    # Artifact values and their identity links are immutable even through SQL.
    # Delivery/publication state lives separately and remains replayable.
    for table in (
        "pit_hypotheses",
        "pit_observations",
        "pit_revisions",
        "pit_retention_links",
    ):
        for operation in ("UPDATE", "DELETE"):
            connection.execute(
                f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation.lower()} "
                f"BEFORE {operation} ON {table} BEGIN "
                "SELECT RAISE(ABORT, 'R16 historical artifact is immutable'); END"
            )
    connection.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
        (
            MIGRATION_VERSION,
            "R-HIST-03C exact parent, outcome and revision retention",
            datetime.now(UTC).isoformat(),
        ),
    )


def schema_ready(connection: sqlite3.Connection) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM schema_migrations WHERE version=?", (MIGRATION_VERSION,)
        ).fetchone()
        is not None
        and connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
            "AND name IN ('pit_retention_links', 'pit_revisions')"
        ).fetchone()[0]
        == 2
    )


def _root(value: dict[str, Any]) -> RetentionEvidenceRoot:
    return RetentionEvidenceRoot(
        role=value["role"],
        content_hash=value.get("contentHash"),
        run_id=value.get("runId"),
        trading_date=date.fromisoformat(value["tradingDate"])
        if value.get("tradingDate")
        else None,
    )


def _verify_objects(
    market: sqlite3.Connection, roots: tuple[RetentionEvidenceRoot, ...]
) -> None:
    if any(root.content_hash is None for root in roots):
        raise _fail("CONTENT_HASH_REQUIRED")
    for content_hash in sorted(
        {root.content_hash for root in roots if root.content_hash}
    ):
        row = market.execute(
            "SELECT object_path, size_bytes FROM market_data_objects WHERE content_hash=?",
            (content_hash,),
        ).fetchone()
        if row is None:
            raise _fail("EVIDENCE_OBJECT_MISSING")
        path = Path(row["object_path"])
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != row["size_bytes"]
        ):
            raise _fail("EVIDENCE_OBJECT_DAMAGED")
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != content_hash:
            raise _fail("EVIDENCE_OBJECT_HASH_MISMATCH")


def _verified_publication(
    connection: sqlite3.Connection,
    publication_id: str,
    *,
    published: bool = True,
) -> RetentionPublicationRequest:
    """Verify material, members, outbox, authority and bytes; no schema writes."""
    try:
        row = connection.execute(
            "SELECT * FROM historical_retention_publications WHERE publication_id=?",
            (publication_id,),
        ).fetchone()
        allowed = (
            {"PUBLISHED"} if published else {"PROTECTED_PENDING_ARTIFACT", "PUBLISHED"}
        )
        if row is None or row["status"] not in allowed:
            raise _fail("PARENT_NOT_PUBLISHED")
        body = json.loads(row["lineage_json"])
        request = RetentionPublicationRequest(
            artifact_type=row["artifact_type"],
            artifact_id=row["artifact_id"],
            artifact_version=row["artifact_version"],
            reference_type=RetentionReferenceType(row["reference_type"]),
            evidence_roots=tuple(_root(root) for root in body["evidenceRoots"]),
            lineage=body["lineage"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        if (
            request.publication_id != publication_id
            or request.lineage_json != row["lineage_json"]
            or request.lineage_hash != row["lineage_hash"]
        ):
            raise _fail("PUBLICATION_HASH_MISMATCH")
        members = connection.execute(
            "SELECT * FROM historical_retention_publication_members WHERE publication_id=?",
            (publication_id,),
        ).fetchall()
        if (
            len(members) != len(request.evidence_roots)
            or row["required_count"] != len(members)
            or row["applied_count"] != len(members)
        ):
            raise _fail("PUBLICATION_MEMBER_MISMATCH")
        by_role = {member["evidence_role"]: member for member in members}
        market_path = resolve_market_db_path(
            research_db_path=Path(storage.DB_PATH),
            evidence_roots=request.evidence_roots,
        )
        market = sqlite3.connect(f"{market_path.as_uri()}?mode=ro", uri=True)
        market.row_factory = sqlite3.Row
        try:
            for root in request.evidence_roots:
                member = by_role.get(root.role)
                intent = RetentionEvidenceIntent(
                    artifact_type=f"{request.artifact_type}:{root.role}",
                    artifact_id=request.artifact_id,
                    artifact_version=request.artifact_version,
                    reference_type=request.reference_type,
                    run_id=root.run_id,
                    trading_date=root.trading_date,
                    content_hash=root.content_hash,
                    created_at=request.created_at,
                )
                if (
                    member is None
                    or member["event_id"] != intent.event_id
                    or member["reference_id"] != intent.reference_id
                    or json.loads(member["root_json"]) != root.canonical()
                ):
                    raise _fail("PUBLICATION_MEMBER_MISMATCH")
                event = connection.execute(
                    "SELECT * FROM historical_retention_outbox WHERE event_id=?",
                    (intent.event_id,),
                ).fetchone()
                if (
                    event is None
                    or event["status"] != "APPLIED"
                    or event["payload_json"] != intent.payload_json
                    or event["payload_hash"] != intent.payload_hash
                    or event["reference_id"] != intent.reference_id
                ):
                    raise _fail("OUTBOX_PROOF_MISMATCH")
                for key in (
                    "artifact_type",
                    "artifact_id",
                    "artifact_version",
                    "content_hash",
                    "run_id",
                ):
                    if event[key] != getattr(intent, key):
                        raise _fail("OUTBOX_COLUMN_MISMATCH")
                if (
                    event["reference_type"] != request.reference_type.value
                    or event["trading_date"]
                    != (root.trading_date.isoformat() if root.trading_date else None)
                    or event["created_at"] != request.created_at.isoformat()
                ):
                    raise _fail("OUTBOX_COLUMN_MISMATCH")
                ref = market.execute(
                    "SELECT * FROM historical_retention_references WHERE reference_id=?",
                    (intent.reference_id,),
                ).fetchone()
                if (
                    ref is None
                    or ref["reference_type"] != request.reference_type.value
                    or not ref["permanent"]
                    or ref["retain_until"] is not None
                    or ref["content_hash"] != root.content_hash
                    or ref["run_id"] != root.run_id
                    or ref["trading_date"]
                    != (root.trading_date.isoformat() if root.trading_date else None)
                    or ref["created_at"] != request.created_at.isoformat()
                ):
                    raise _fail("AUTHORITY_PROOF_MISMATCH")
            _verify_objects(market, request.evidence_roots)
        finally:
            market.close()
        return request
    except (sqlite3.Error, KeyError, ValueError, OSError) as exc:
        raise _fail("PUBLICATION_PROOF_INVALID") from exc


@dataclass(frozen=True)
class S8Parent:
    payload: dict[str, Any]
    request: RetentionPublicationRequest


def resolve_s8_parent(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    expected_hash: str,
    expected_version: str,
    expected_publication_id: str | None = None,
    expected_lineage_hash: str | None = None,
) -> S8Parent:
    from .selection.s8_persist_run import PROFILE_ID

    row = connection.execute(
        "SELECT payload_json FROM selection_scan_runs WHERE profile_id=? AND run_id=?",
        (PROFILE_ID, run_id),
    ).fetchone()
    if row is None:
        raise _fail("S8_PARENT_MISSING")
    payload = json.loads(row["payload_json"])
    if (
        _payload_hash(payload) != expected_hash
        or payload.get("schemaVersion") != expected_version
    ):
        raise _fail("S8_PARENT_HASH_OR_VERSION_MISMATCH")
    publication = connection.execute(
        "SELECT publication_id FROM historical_retention_publications "
        "WHERE artifact_type='S8_DECISION_VERSION' AND artifact_id=? AND artifact_version=?",
        (run_id, expected_version),
    ).fetchone()
    if publication is None:
        raise _fail("S8_PARENT_UNPROTECTED")
    request = _verified_publication(connection, publication["publication_id"])
    if (
        request.lineage.get("s8PayloadHash") != expected_hash
        or request.lineage.get("s8") != payload.get("lineage")
        or request.lineage.get("tradingDate") != payload.get("tradingDate")
        or (
            expected_publication_id is not None
            and request.publication_id != expected_publication_id
        )
        or (
            expected_lineage_hash is not None
            and request.lineage_hash != expected_lineage_hash
        )
    ):
        # Older publications without a payload seal need explicit audited repair,
        # never an on-read backfill that blesses whatever is stored today.
        raise _fail("S8_PARENT_SEAL_MISMATCH")
    return S8Parent(payload=payload, request=request)


def _parent_bars(
    connection: sqlite3.Connection, parent: S8Parent
) -> dict[str, list[dict[str, Any]]]:
    """Read only raw hashes named by the exact S8 evidence manifest."""
    hashes = sorted(
        {
            root.content_hash
            for root in parent.request.evidence_roots
            if root.content_hash
        }
    )
    result: dict[str, list[dict[str, Any]]] = {}
    for offset in range(0, len(hashes), 400):
        chunk = hashes[offset : offset + 400]
        placeholders = ",".join("?" for _ in chunk)
        rows = connection.execute(
            f"SELECT artifact_hash, payload_json FROM cash_raw_session_bars WHERE artifact_hash IN ({placeholders}) "
            "AND trade_date < ? ORDER BY symbol, trade_date, bar_id",
            (*chunk, parent.payload["tradingDate"]),
        ).fetchall()
        for row in rows:
            bar = json.loads(row["payload_json"])
            if bar.get("artifactHash") != row["artifact_hash"]:
                raise _fail("NORMALIZED_BAR_LINEAGE_MISMATCH")
            result.setdefault(bar["symbol"], []).append(
                {
                    "trade_date": bar["tradeDate"],
                    "artifact_hash": bar["artifactHash"],
                    **{
                        key: bar.get(key)
                        for key in ("open", "high", "low", "close", "volume")
                    },
                }
            )
    return result


def freeze_s8_hypotheses(
    *, s8_payload: dict[str, Any], dataset_revision_hash: str
) -> tuple[R16FrozenHypothesisV1, ...]:
    conn = storage.connect()
    try:
        parent = resolve_s8_parent(
            conn,
            run_id=str(s8_payload.get("runId", "")),
            expected_hash=_payload_hash(s8_payload),
            expected_version=str(s8_payload.get("schemaVersion", "")),
        )
        bars = _parent_bars(conn, parent)
        frozen = build_frozen_hypotheses(
            s8_payload=parent.payload,
            bars_by_symbol=bars,
            dataset_revision_hash=dataset_revision_hash,
        )
        return tuple(
            row.model_copy(
                update={
                    "source_s8_publication_id": parent.request.publication_id,
                    "source_s8_version": parent.request.artifact_version,
                    "source_s8_publication_lineage_hash": parent.request.lineage_hash,
                    "decision_inputs": tuple(
                        bar
                        for bar in bars.get(row.symbol, ())
                        if bar["artifact_hash"] in row.source_bar_hashes
                    ),
                }
            )
            for row in frozen
        )
    finally:
        conn.close()


def _stored_record(
    connection: sqlite3.Connection, record_type: str, record_id: str
) -> tuple[sqlite3.Row, dict[str, Any]]:
    if record_type not in RECORD_TABLES:
        raise _fail("RECORD_TYPE_INVALID")
    table, key = RECORD_TABLES[record_type]
    row = connection.execute(
        f"SELECT * FROM {table} WHERE {key}=?", (record_id,)
    ).fetchone()
    if (
        row is None
        or hashlib.sha256(row["payload_json"].encode()).hexdigest()
        != row["content_hash"]
    ):
        raise _fail("RECORD_HASH_OR_PARENT_MISSING")
    return row, json.loads(row["payload_json"])


def verified_record(
    connection: sqlite3.Connection,
    record_type: str,
    record_id: str,
    *,
    ancestors: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[sqlite3.Row, dict[str, Any], RetentionPublicationRequest]:
    identity = (record_type, record_id)
    if identity in ancestors:
        raise _fail("PREDECESSOR_CYCLE")
    ancestors = ancestors | {identity}
    row, payload = _stored_record(connection, record_type, record_id)
    link = connection.execute(
        "SELECT * FROM pit_retention_links WHERE record_type=? AND record_id=?",
        (record_type, record_id),
    ).fetchone()
    if link is None or link["payload_hash"] != _payload_hash(payload):
        raise _fail("RECORD_NOT_PROTECTED")
    request = _verified_publication(connection, link["publication_id"])
    if (
        request.reference_type.value != record_type
        or request.artifact_id != record_id
        or request.artifact_type != "R16_" + record_type
        or request.artifact_version != payload.get("schemaVersion")
        or request.lineage.get("recordHash") != link["payload_hash"]
        or request.lineage.get("datasetRunId") != row["dataset_run_id"]
    ):
        raise _fail("RECORD_PUBLICATION_MISMATCH")
    # Reads verify the original parent as well; a cached PUBLISHED flag is not
    # a substitute for reconstruction proof and this path creates no intent.
    if record_type == "DECISION_VERSION":
        resolve_s8_parent(
            connection,
            run_id=payload["sourceS8RunId"],
            expected_hash=payload["sourceS8Hash"],
            expected_version=str(payload.get("sourceS8Version") or ""),
            expected_publication_id=payload.get("sourceS8PublicationId"),
            expected_lineage_hash=payload.get("sourceS8PublicationLineageHash"),
        )
    else:
        _, frozen, original = verified_record(
            connection, "DECISION_VERSION", payload["hypothesisId"], ancestors=ancestors
        )
        if record_type == "OUTCOME" and (
            payload.get("sourceHypothesisHash") != _payload_hash(frozen)
            or request.lineage.get("parentPublicationId") != original.publication_id
        ):
            raise _fail("OUTCOME_PARENT_MISMATCH")
        if record_type == "REVISION":
            _, previous, predecessor = verified_record(
                connection,
                payload["predecessorType"],
                payload["predecessorId"],
                ancestors=ancestors,
            )
            if (
                _payload_hash(previous) != payload["predecessorHash"]
                or previous.get("hypothesisId") != payload["hypothesisId"]
                or request.lineage.get("parentPublicationId")
                != predecessor.publication_id
            ):
                raise _fail("REVISION_PREDECESSOR_MISMATCH")
            if payload.get("replacementHypothesisId"):
                _, replacement, _ = verified_record(
                    connection,
                    "DECISION_VERSION",
                    payload["replacementHypothesisId"],
                    ancestors=ancestors,
                )
                if _payload_hash(replacement) != payload["replacementHypothesisHash"]:
                    raise _fail("REVISION_REPLACEMENT_MISMATCH")
        elif payload.get("predecessorObservationId"):
            _, previous, _ = verified_record(
                connection,
                "OUTCOME",
                payload["predecessorObservationId"],
                ancestors=ancestors,
            )
            if (
                _payload_hash(previous) != payload.get("predecessorObservationHash")
                or previous.get("hypothesisId") != payload["hypothesisId"]
            ):
                raise _fail("OUTCOME_PREDECESSOR_MISMATCH")
    return row, payload, request


class R16RetentionWriter:
    """One caller-owned transaction; parent validation is cached only within it."""

    def __init__(self, connection: sqlite3.Connection):
        if not schema_ready(connection):
            raise _fail("R16_SCHEMA_NOT_APPLIED")
        self.connection = connection
        self.publications = RetentionPublicationStore(db_path=Path(storage.DB_PATH))
        self.parents: dict[tuple[str, ...], S8Parent] = {}

    def parent(self, model: R16FrozenHypothesisV1) -> S8Parent:
        key = (
            model.source_s8_run_id,
            model.source_s8_hash,
            model.source_s8_version or "",
            model.source_s8_publication_id or "",
            model.source_s8_publication_lineage_hash or "",
        )
        if not all(key):
            raise _fail("S8_PARENT_IDENTITY_REQUIRED")
        if key not in self.parents:
            self.parents[key] = resolve_s8_parent(
                self.connection,
                run_id=key[0],
                expected_hash=key[1],
                expected_version=key[2],
                expected_publication_id=key[3],
                expected_lineage_hash=key[4],
            )
        parent = self.parents[key]
        if _payload_hash(parent.payload["lineage"]) != model.source_s8_lineage_hash:
            raise _fail("S8_LINEAGE_HASH_MISMATCH")
        return parent

    def _stage(
        self,
        *,
        record_type: str,
        record_id: str,
        dataset_run_id: str,
        payload: dict[str, Any],
        roots: tuple[RetentionEvidenceRoot, ...],
        lineage: dict[str, Any],
    ) -> str:
        artifact_row, _ = _stored_record(self.connection, record_type, record_id)
        request = RetentionPublicationRequest(
            artifact_type="R16_" + record_type,
            artifact_id=record_id,
            artifact_version=str(payload["schemaVersion"]),
            reference_type=RetentionReferenceType(record_type),
            evidence_roots=roots,
            lineage={
                **lineage,
                "recordHash": _payload_hash(payload),
                "datasetRunId": dataset_run_id,
            },
            # Actual persistence time is separate from decision/observation
            # time in lineage; retries use this same immutable stored value.
            created_at=datetime.fromisoformat(artifact_row["created_at"]),
        )
        receipt = self.publications.stage(request, connection=self.connection)
        existing = self.connection.execute(
            "SELECT * FROM pit_retention_links WHERE record_type=? AND record_id=?",
            (record_type, record_id),
        ).fetchone()
        if existing is not None:
            if existing["publication_id"] != receipt.publication_id or existing[
                "payload_hash"
            ] != _payload_hash(payload):
                raise ValueError("R16 retention identity is immutable")
        else:
            self.connection.execute(
                "INSERT INTO pit_retention_links VALUES (?, ?, ?, ?)",
                (
                    record_type,
                    record_id,
                    receipt.publication_id,
                    _payload_hash(payload),
                ),
            )
        return receipt.publication_id

    def hypothesis(self, dataset_run_id: str, payload: dict[str, Any]) -> str:
        model = R16FrozenHypothesisV1.model_validate(payload)
        parent = self.parent(model)
        dataset = self.connection.execute(
            "SELECT * FROM pit_dataset_runs WHERE run_id=?", (dataset_run_id,)
        ).fetchone()
        if (
            dataset is None
            or dataset["source_s8_run_id"] != model.source_s8_run_id
            or dataset["source_s8_hash"] != model.source_s8_hash
            or dataset["dataset_revision_hash"] != model.dataset_revision_hash
        ):
            raise _fail("HYPOTHESIS_DATASET_MISMATCH")
        matching = [
            row
            for row in parent.payload.get("rows", ())
            if row.get("candidateId") == model.candidate_id
            and row.get("symbol") == model.symbol
        ]
        if (
            len(matching) != 1
            or matching[0].get("publicState") != model.public_state
            or datetime.fromisoformat(parent.payload["asOf"].replace("Z", "+00:00"))
            != model.decision_cutoff_at
            or parent.payload["tradingDate"] != model.trading_date
        ):
            raise _fail("HYPOTHESIS_S8_ROW_MISMATCH")
        roots = parent.request.evidence_roots
        if not set(model.source_bar_hashes).issubset(
            {root.content_hash for root in roots}
        ):
            raise _fail("HYPOTHESIS_INPUT_NOT_IN_PARENT")
        expected_features = {
            str(k): str(v)
            for k, v in parent.payload["lineage"].items()
            if isinstance(v, str) and v
        }
        if model.source_feature_hashes != expected_features:
            raise _fail("HYPOTHESIS_FEATURE_LINEAGE_MISMATCH")
        original_inputs = _parent_bars(self.connection, parent).get(model.symbol, [])
        exact_inputs = tuple(
            bar
            for bar in original_inputs
            if bar["artifact_hash"] in model.source_bar_hashes
        )
        if list(exact_inputs) != list(model.decision_inputs):
            raise _fail("HYPOTHESIS_NORMALIZED_INPUT_MISMATCH")
        # Store the normalized input values as well as their raw-object identity.
        # Rebuild only from this frozen material, never current feature tables.
        expected = build_frozen_hypotheses(
            s8_payload=parent.payload,
            bars_by_symbol={model.symbol: list(model.decision_inputs)},
            dataset_revision_hash=model.dataset_revision_hash,
        )
        target = next(
            (row for row in expected if row.hypothesis_id == model.hypothesis_id), None
        )
        ignored = {
            "source_s8_publication_id",
            "source_s8_version",
            "source_s8_publication_lineage_hash",
            "decision_inputs",
        }
        if target is None or target.model_dump(exclude=ignored) != model.model_dump(
            exclude=ignored
        ):
            raise _fail("HYPOTHESIS_FROZEN_INPUT_MISMATCH")
        return self._stage(
            record_type="DECISION_VERSION",
            record_id=model.hypothesis_id,
            dataset_run_id=dataset_run_id,
            payload=payload,
            roots=roots,
            lineage={
                "sourceS8PublicationId": parent.request.publication_id,
                "sourceS8PublicationLineageHash": parent.request.lineage_hash,
                "decisionAt": model.decision_cutoff_at.isoformat(),
            },
        )

    def observation(self, dataset_run_id: str, payload: dict[str, Any]) -> str:
        model = R16ObservationV1.model_validate(payload)
        row, frozen, parent = verified_record(
            self.connection, "DECISION_VERSION", model.hypothesis_id
        )
        hypothesis = R16FrozenHypothesisV1.model_validate(frozen)
        self.parent(hypothesis)
        if (
            row["dataset_run_id"] != dataset_run_id
            or model.source_hypothesis_hash != _payload_hash(frozen)
            or any(
                getattr(model, field) != getattr(hypothesis, field)
                for field in (
                    "source_s8_run_id",
                    "dataset_revision_hash",
                    "symbol",
                    "direction",
                    "horizon_sessions",
                )
            )
        ):
            raise _fail("OUTCOME_PARENT_MISMATCH")
        if model.label_computed_at < hypothesis.decision_cutoff_at:
            raise _fail("OUTCOME_TIME_BEFORE_DECISION")
        for instant in (model.entry_at, model.outcome_at):
            if instant is not None and (
                instant.tzinfo is None
                or instant <= hypothesis.decision_cutoff_at
                or instant > model.label_computed_at
            ):
                raise _fail("OUTCOME_TIME_INVALID")
        path = {
            "hypothesis": model.hypothesis_id,
            "bars": list(model.path_evidence),
            "labelPolicy": hypothesis.label_policy_version,
            "gapPolicy": hypothesis.gap_policy_version,
        }
        if _payload_hash(path) != model.path_hash:
            raise _fail("OUTCOME_PATH_HASH_MISMATCH")
        if (
            tuple(item["hash"] for item in model.path_evidence if item.get("hash"))
            != model.outcome_bar_hashes
        ):
            raise _fail("OUTCOME_PATH_ROOT_MISMATCH")
        for item in model.path_evidence:
            available = datetime.fromisoformat(
                str(item["availableAt"]).replace("Z", "+00:00")
            )
            if (
                available.tzinfo is None
                or available <= hypothesis.decision_cutoff_at
                or available > model.label_computed_at
                or not item.get("hash")
            ):
                raise _fail("OUTCOME_PATH_TIME_OR_HASH_INVALID")
        if model.predecessor_observation_id:
            previous_row, previous, _ = verified_record(
                self.connection, "OUTCOME", model.predecessor_observation_id
            )
            if (
                previous_row["hypothesis_id"] != model.hypothesis_id
                or _payload_hash(previous) != model.predecessor_observation_hash
                or datetime.fromisoformat(
                    previous["labelComputedAt"].replace("Z", "+00:00")
                )
                > model.label_computed_at
                or model.predecessor_observation_id == model.observation_id
            ):
                raise _fail("OUTCOME_PREDECESSOR_MISMATCH")
        elif (
            not self.connection.execute(
                "SELECT 1 FROM pit_retention_links WHERE record_type='OUTCOME' AND record_id=?",
                (model.observation_id,),
            ).fetchone()
            and self.connection.execute(
                "SELECT 1 FROM pit_observations WHERE hypothesis_id=? AND observation_id<>? LIMIT 1",
                (model.hypothesis_id, model.observation_id),
            ).fetchone()
        ):
            raise _fail("OUTCOME_PREDECESSOR_REQUIRED")
        roots = _additional_roots(
            parent.evidence_roots, model.outcome_bar_hashes, "OUTCOME"
        )
        return self._stage(
            record_type="OUTCOME",
            record_id=model.observation_id,
            dataset_run_id=dataset_run_id,
            payload=payload,
            roots=roots,
            lineage={
                "hypothesisId": model.hypothesis_id,
                "hypothesisHash": model.source_hypothesis_hash,
                "parentPublicationId": parent.publication_id,
                "decisionAt": hypothesis.decision_cutoff_at.isoformat(),
                "observedAt": model.label_computed_at.isoformat(),
                "predecessorId": model.predecessor_observation_id,
            },
        )

    def revision(self, dataset_run_id: str, payload: dict[str, Any]) -> str:
        model = R16RevisionV1.model_validate(payload)
        row, frozen, hypothesis_publication = verified_record(
            self.connection, "DECISION_VERSION", model.hypothesis_id
        )
        hypothesis = R16FrozenHypothesisV1.model_validate(frozen)
        self.parent(hypothesis)
        previous_row, previous, predecessor = verified_record(
            self.connection, model.predecessor_type, model.predecessor_id
        )
        previous_hypothesis = previous.get("hypothesisId")
        previous_time = (
            previous.get("recordedAt")
            or previous.get("labelComputedAt")
            or previous.get("decisionCutoffAt")
        )
        if (
            row["dataset_run_id"] != dataset_run_id
            or previous_row["dataset_run_id"] != dataset_run_id
            or previous_hypothesis != model.hypothesis_id
            or _payload_hash(previous) != model.predecessor_hash
            or model.recorded_at
            < datetime.fromisoformat(str(previous_time).replace("Z", "+00:00"))
            or model.predecessor_id == model.revision_id
        ):
            raise _fail("REVISION_PREDECESSOR_MISMATCH")
        if model.replacement_hypothesis_id:
            _, replacement, replacement_publication = verified_record(
                self.connection, "DECISION_VERSION", model.replacement_hypothesis_id
            )
            if _payload_hash(replacement) != model.replacement_hypothesis_hash or any(
                replacement[key] != frozen[key]
                for key in ("symbol", "candidateId", "horizonSessions")
            ):
                raise _fail("REVISION_REPLACEMENT_MISMATCH")
            replacement_roots = tuple(
                root.content_hash
                for root in replacement_publication.evidence_roots
                if root.content_hash
            )
        else:
            replacement_roots = ()
        roots = _additional_roots(
            hypothesis_publication.evidence_roots,
            tuple(
                root.content_hash
                for root in predecessor.evidence_roots
                if root.content_hash
            )
            + replacement_roots
            + model.evidence_hashes,
            "REVISION",
        )
        return self._stage(
            record_type="REVISION",
            record_id=model.revision_id,
            dataset_run_id=dataset_run_id,
            payload=payload,
            roots=roots,
            lineage={
                "hypothesisId": model.hypothesis_id,
                "predecessorType": model.predecessor_type,
                "predecessorId": model.predecessor_id,
                "predecessorHash": model.predecessor_hash,
                "parentPublicationId": predecessor.publication_id,
                "decisionAt": hypothesis.decision_cutoff_at.isoformat(),
                "revisedAt": model.recorded_at.isoformat(),
            },
        )


def _additional_roots(
    roots: tuple[RetentionEvidenceRoot, ...], hashes: tuple[str, ...], role: str
) -> tuple[RetentionEvidenceRoot, ...]:
    known = {root.content_hash for root in roots}
    return roots + tuple(
        RetentionEvidenceRoot(role=f"{role}_{value}", content_hash=value)
        for value in sorted(set(hashes) - known)
    )


def finalize_publications(publication_ids: list[str]) -> None:
    """After artifact+intent commit. A failure leaves canonical rows hidden."""
    for publication_id in dict.fromkeys(publication_ids):
        conn = storage.connect()
        try:
            row = conn.execute(
                "SELECT lineage_json FROM historical_retention_publications WHERE publication_id=?",
                (publication_id,),
            ).fetchone()
            if row is None:
                raise _fail("PUBLICATION_MISSING")
            roots = tuple(
                _root(value)
                for value in json.loads(row["lineage_json"])["evidenceRoots"]
            )
        finally:
            conn.close()
        market = resolve_market_db_path(
            research_db_path=Path(storage.DB_PATH), evidence_roots=roots
        )
        publications = RetentionPublicationStore(
            db_path=Path(storage.DB_PATH),
            registrar=DurableRetentionRegistrar(
                db_path=Path(storage.DB_PATH),
                authority=HistoricalRetentionAuthority(db_path=market),
            ),
        )
        result = publications.finalize(publication_id)
        if result.status not in {
            RetentionPublicationStatus.PROTECTED_PENDING_ARTIFACT,
            RetentionPublicationStatus.PUBLISHED,
        }:
            raise _fail("RETENTION_PUBLICATION_BLOCKED")
        conn = storage.connect()
        try:
            request = _verified_publication(conn, publication_id, published=False)
            kind = request.reference_type.value
            artifact, payload = _stored_record(conn, kind, request.artifact_id)
            if (
                request.lineage.get("recordHash") != _payload_hash(payload)
                or request.lineage.get("datasetRunId") != artifact["dataset_run_id"]
            ):
                raise _fail("PUBLICATION_ARTIFACT_MISMATCH")
            if kind == "DECISION_VERSION":
                R16RetentionWriter(conn).parent(
                    R16FrozenHypothesisV1.model_validate(payload)
                )
            else:
                verified_record(conn, "DECISION_VERSION", payload["hypothesisId"])
        finally:
            conn.close()
        publications.mark_published(publication_id)


def resume_pending_publications() -> int:
    """Explicit worker recovery, never a read-route side effect."""
    conn = storage.connect()
    try:
        if not schema_ready(conn):
            raise _fail("R16_SCHEMA_NOT_APPLIED")
        rows = conn.execute(
            "SELECT rp.publication_id FROM pit_retention_links rl "
            "JOIN historical_retention_publications rp ON rp.publication_id=rl.publication_id "
            "WHERE rp.status<>'PUBLISHED' "
            "ORDER BY CASE rl.record_type WHEN 'DECISION_VERSION' THEN 0 WHEN 'OUTCOME' THEN 1 ELSE 2 END, "
            "rp.created_at, rp.publication_id"
        ).fetchall()
    finally:
        conn.close()
    finalize_publications([row["publication_id"] for row in rows])
    return len(rows)


def publication_predicate(table: str) -> str:
    """SQL filter only; never make an unregistered legacy row look protected."""
    matches = [
        (kind, key) for kind, (name, key) in RECORD_TABLES.items() if name == table
    ]
    if not matches:
        return "1=1"
    kind, key = matches[0]
    return (
        "EXISTS (SELECT 1 FROM pit_retention_links AS rl "
        "JOIN historical_retention_publications AS rp ON rp.publication_id=rl.publication_id "
        f"WHERE rl.record_type='{kind}' AND rl.record_id={table}.{key} AND rp.status='PUBLISHED')"
    )
