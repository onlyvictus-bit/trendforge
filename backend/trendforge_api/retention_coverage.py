"""R-HIST-03E authoritative producer coverage proof.

The mandatory denominator comes from governed S8/R16/R18 artifact stores, never
from retention tables. Audit is read-only. Reconciliation is explicit, bounded,
and delegates only to accepted producer owners.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable

from . import storage
from .historical_retention import RetentionReferenceType

REGISTRY_VERSION = "rhist03e/v1"


class CoverageStatus(StrEnum):
    COVERED = "COVERED"
    MISSING_RETENTION = "MISSING_RETENTION"
    PENDING_RETENTION = "PENDING_RETENTION"
    FAILED_BLOCKING = "FAILED_BLOCKING"
    INVALID_RETENTION_STATE = "INVALID_RETENTION_STATE"
    RETENTION_ORPHAN = "RETENTION_ORPHAN"
    LINEAGE_MISSING = "LINEAGE_MISSING"
    LINEAGE_BROKEN = "LINEAGE_BROKEN"
    LINEAGE_CYCLE = "LINEAGE_CYCLE"
    LINEAGE_TYPE_MISMATCH = "LINEAGE_TYPE_MISMATCH"
    UNKNOWN_PRODUCER = "UNKNOWN_PRODUCER"
    UNSUPPORTED_ARTIFACT_VERSION = "UNSUPPORTED_ARTIFACT_VERSION"
    DUPLICATE_PROOF = "DUPLICATE_PROOF"
    INCONSISTENT_IDENTITY = "INCONSISTENT_IDENTITY"
    LEGACY_UNGOVERNED = "LEGACY_UNGOVERNED"
    LEGACY_UNVERIFIABLE = "LEGACY_UNVERIFIABLE"
    REGISTRY_ERROR = "REGISTRY_ERROR"
    VERIFIER_ERROR = "VERIFIER_ERROR"


@dataclass(frozen=True, slots=True)
class ProducerSpec:
    producer_id: str
    artifact_type: str
    reference_type: RetentionReferenceType
    table: str
    id_col: str
    version_col: str | None
    hash_col: str | None
    proof_style: str
    row_filter: str | None = None
    row_args: tuple[object, ...] = ()
    state_col: str | None = None


REGISTRY: tuple[ProducerSpec, ...] = (
    ProducerSpec(
        "S8_DECISION_VERSION",
        "S8_DECISION_VERSION",
        RetentionReferenceType.DECISION_VERSION,
        "selection_scan_runs",
        "run_id",
        None,
        None,
        "PUBLICATION",
        "profile_id=?",
        ("PRF-S8-SCAN-RUN",),
    ),
    ProducerSpec(
        "R16_DECISION_VERSION",
        "R16_DECISION_VERSION",
        RetentionReferenceType.DECISION_VERSION,
        "pit_hypotheses",
        "hypothesis_id",
        None,
        "content_hash",
        "PUBLICATION",
    ),
    ProducerSpec(
        "R16_OUTCOME",
        "R16_OUTCOME",
        RetentionReferenceType.OUTCOME,
        "pit_observations",
        "observation_id",
        None,
        "content_hash",
        "PUBLICATION",
    ),
    ProducerSpec(
        "R16_REVISION",
        "R16_REVISION",
        RetentionReferenceType.REVISION,
        "pit_revisions",
        "revision_id",
        None,
        "content_hash",
        "PUBLICATION",
    ),
    ProducerSpec(
        "R18_ML_DATASET",
        "ML_DATASET",
        RetentionReferenceType.ML_DATASET,
        "ml_frozen_datasets",
        "dataset_id",
        "dataset_version",
        "dataset_hash",
        "R18",
        state_col="publication_state",
    ),
    ProducerSpec(
        "R18_MODEL_VERSION",
        "MODEL_VERSION",
        RetentionReferenceType.MODEL_VERSION,
        "ml_governed_model_versions",
        "model_id",
        "model_version",
        "model_hash",
        "R18",
        state_col="publication_state",
    ),
    ProducerSpec(
        "R18_STRATEGY_PROFILE",
        "STRATEGY_PROFILE",
        RetentionReferenceType.STRATEGY_PROFILE,
        "strategy_profile_versions",
        "profile_id",
        "profile_version",
        "content_hash",
        "R18",
        state_col="publication_state",
    ),
    ProducerSpec(
        "R18_AUDIT",
        "AUDIT",
        RetentionReferenceType.AUDIT,
        "governance_audit_records",
        "audit_id",
        None,
        "record_hash",
        "R18",
        state_col="publication_state",
    ),
)


@dataclass(frozen=True, slots=True)
class Artifact:
    spec: ProducerSpec
    artifact_id: str
    version: str
    semantic_hash: str | None
    state: str | None
    payload: dict[str, Any] | None

    @property
    def legacy(self) -> bool:
        return self.state == "LEGACY_UNGOVERNED"

    @property
    def key(self) -> tuple[str, str, str]:
        return self.spec.producer_id, self.artifact_id, self.version


def producer_registry() -> tuple[ProducerSpec, ...]:
    return REGISTRY


def validate_registry(
    registry: Iterable[ProducerSpec] = REGISTRY,
) -> tuple[str, ...]:
    specs = tuple(registry)
    errors: list[str] = []
    ids = [row.producer_id for row in specs]
    scopes = [(row.table, row.row_filter, row.row_args) for row in specs]
    if len(ids) != len(set(ids)):
        errors.append("DUPLICATE_PRODUCER_ID")
    if len(scopes) != len(set(scopes)):
        errors.append("DUPLICATE_AUTHORITATIVE_STORE_SCOPE")
    for row in specs:
        if row.proof_style not in {"PUBLICATION", "R18"}:
            errors.append(f"UNKNOWN_PROOF_STYLE:{row.producer_id}")
        if row.proof_style == "R18" and row.artifact_type != row.reference_type.value:
            errors.append(f"TYPE_REFERENCE_MISMATCH:{row.producer_id}")
    return tuple(sorted(errors))


def _exists(conn: sqlite3.Connection, table: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        is not None
    )


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not _exists(conn, table):
        return set()
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _connect(path: Path) -> sqlite3.Connection:
    path = path.expanduser().resolve(strict=False)
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("BEGIN")
    return conn


def _selected(values: Iterable[str] | None) -> tuple[ProducerSpec, ...]:
    if values is None:
        return REGISTRY
    wanted = {str(value) for value in values}
    return tuple(
        row
        for row in REGISTRY
        if row.producer_id in wanted
        or row.artifact_type in wanted
        or row.reference_type.value in wanted
    )


def _version(
    spec: ProducerSpec,
    row: sqlite3.Row,
    payload: dict[str, Any],
) -> str:
    if spec.version_col:
        return str(row[spec.version_col])
    if spec.producer_id == "R18_AUDIT":
        return "1"
    return str(
        payload.get("schemaVersion") or payload.get("schema_version") or "unknown"
    )


def _enumerate(
    conn: sqlite3.Connection,
    spec: ProducerSpec,
) -> tuple[list[Artifact], list[dict[str, str]]]:
    if not _exists(conn, spec.table):
        return [], [
            _finding(
                spec.producer_id,
                "*",
                "*",
                CoverageStatus.REGISTRY_ERROR,
                f"AUTHORITATIVE_TABLE_MISSING:{spec.table}",
            )
        ]
    required = {spec.id_col, "payload_json"} | {
        x for x in (spec.version_col, spec.hash_col, spec.state_col) if x
    }
    missing = required - _columns(conn, spec.table)
    if missing:
        return [], [
            _finding(
                spec.producer_id,
                "*",
                "*",
                CoverageStatus.REGISTRY_ERROR,
                "AUTHORITATIVE_COLUMNS_MISSING:" + ",".join(sorted(missing)),
            )
        ]
    cols = [spec.id_col, "payload_json"] + [
        x for x in (spec.version_col, spec.hash_col, spec.state_col) if x
    ]
    cols = list(dict.fromkeys(cols))
    sql = f"SELECT {','.join(cols)} FROM {spec.table}"
    if spec.row_filter:
        sql += f" WHERE {spec.row_filter}"
    sql += f" ORDER BY {spec.id_col}"
    if spec.version_col:
        sql += f",{spec.version_col}"
    artifacts: list[Artifact] = []
    findings: list[dict[str, str]] = []
    for row in conn.execute(sql, spec.row_args):
        artifact_id = str(row[spec.id_col])
        try:
            payload = json.loads(str(row["payload_json"]))
            if not isinstance(payload, dict):
                raise ValueError("PAYLOAD_NOT_OBJECT")
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            artifact = Artifact(
                spec,
                artifact_id,
                "unknown",
                str(row[spec.hash_col]) if spec.hash_col else None,
                None,
                None,
            )
            artifacts.append(artifact)
            findings.append(
                _finding(
                    spec.producer_id,
                    artifact_id,
                    "unknown",
                    CoverageStatus.LINEAGE_BROKEN,
                    f"PAYLOAD_JSON_INVALID:{type(exc).__name__}",
                )
            )
            continue
        artifacts.append(
            Artifact(
                spec,
                artifact_id,
                _version(spec, row, payload),
                str(row[spec.hash_col]) if spec.hash_col else None,
                str(row[spec.state_col]) if spec.state_col else None,
                payload,
            )
        )
    return artifacts, findings


def _finding(
    producer: str,
    artifact_id: str,
    version: str,
    status: CoverageStatus,
    detail: str | None = None,
) -> dict[str, str]:
    row = {
        "producerId": producer,
        "artifactId": artifact_id,
        "artifactVersion": version,
        "status": status.value,
    }
    if detail:
        row["detail"] = detail
    return row


def _exception_status(exc: Exception) -> CoverageStatus:
    text = str(exc).upper()
    if "CYCLE" in text:
        return CoverageStatus.LINEAGE_CYCLE
    if "TYPE" in text and ("MISMATCH" in text or "INVALID" in text):
        return CoverageStatus.LINEAGE_TYPE_MISMATCH
    if "VERSION" in text and ("UNKNOWN" in text or "INVALID" in text):
        return CoverageStatus.UNSUPPORTED_ARTIFACT_VERSION
    if "MISSING" in text or "UNBOUND" in text or "NOT_PROTECTED" in text:
        return CoverageStatus.LINEAGE_MISSING
    if "HASH" in text or "MISMATCH" in text or "CORRUPT" in text:
        return CoverageStatus.INCONSISTENT_IDENTITY
    return CoverageStatus.LINEAGE_BROKEN


def _publication_proof(
    conn: sqlite3.Connection,
    path: Path,
    artifact: Artifact,
) -> dict[str, str]:
    spec = artifact.spec
    if not _exists(conn, "historical_retention_publications"):
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.MISSING_RETENTION,
            "PUBLICATION_TABLE_MISSING",
        )
    rows = conn.execute(
        "SELECT * FROM historical_retention_publications "
        "WHERE artifact_type=? AND artifact_id=? AND artifact_version=?",
        (spec.artifact_type, artifact.artifact_id, artifact.version),
    ).fetchall()
    if not rows:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.MISSING_RETENTION,
        )
    if len(rows) != 1:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.DUPLICATE_PROOF,
            f"PUBLICATION_COUNT:{len(rows)}",
        )
    row = rows[0]
    if str(row["reference_type"]) != spec.reference_type.value:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.LINEAGE_TYPE_MISMATCH,
            f"REFERENCE_TYPE:{row['reference_type']}",
        )
    state = str(row["status"])
    if state == "FAILED_BLOCKING":
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.FAILED_BLOCKING,
            str(row["last_error"] or state),
        )
    if state != "PUBLISHED":
        status = (
            CoverageStatus.PENDING_RETENTION
            if state in {"PENDING_RETENTION", "PROTECTED_PENDING_ARTIFACT"}
            else CoverageStatus.INVALID_RETENTION_STATE
        )
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            status,
            state,
        )
    if path.resolve(strict=False) != Path(storage.DB_PATH).resolve(strict=False):
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.VERIFIER_ERROR,
            "DB_PATH_NOT_CONFIGURED_STORAGE_DB",
        )
    try:
        from .selection.r16_pit import SCHEMA_VERSION as R16_VERSION
        from .selection.s8_persist_run import SCHEMA_VERSION as S8_VERSION

        if spec.producer_id == "S8_DECISION_VERSION":
            from .r16_retention import resolve_s8_parent
            from .selection.r16_pit import _payload_hash

            if artifact.version != S8_VERSION:
                return _finding(
                    spec.producer_id,
                    artifact.artifact_id,
                    artifact.version,
                    CoverageStatus.UNSUPPORTED_ARTIFACT_VERSION,
                    f"EXPECTED:{S8_VERSION}",
                )
            if artifact.payload is None:
                raise ValueError("S8_PAYLOAD_MISSING")
            resolve_s8_parent(
                conn,
                run_id=artifact.artifact_id,
                expected_hash=_payload_hash(artifact.payload),
                expected_version=artifact.version,
            )
        else:
            from .r16_retention import verified_record

            if artifact.version != R16_VERSION:
                return _finding(
                    spec.producer_id,
                    artifact.artifact_id,
                    artifact.version,
                    CoverageStatus.UNSUPPORTED_ARTIFACT_VERSION,
                    f"EXPECTED:{R16_VERSION}",
                )
            verified_record(
                conn,
                spec.reference_type.value,
                artifact.artifact_id,
            )
    except (RuntimeError, ValueError, KeyError, sqlite3.Error, OSError) as exc:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            _exception_status(exc),
            str(exc),
        )
    return _finding(
        spec.producer_id,
        artifact.artifact_id,
        artifact.version,
        CoverageStatus.COVERED,
    )


def _r18_proof(
    conn: sqlite3.Connection,
    path: Path,
    artifact: Artifact,
) -> dict[str, str]:
    spec = artifact.spec
    if artifact.legacy:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.LEGACY_UNGOVERNED,
            artifact.state,
        )
    if not _exists(conn, "r18_retention_links"):
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.MISSING_RETENTION,
            "R18_LINK_TABLE_MISSING",
        )
    rows = conn.execute(
        "SELECT * FROM r18_retention_links "
        "WHERE artifact_type=? AND artifact_id=? AND artifact_version=?",
        (spec.artifact_type, artifact.artifact_id, artifact.version),
    ).fetchall()
    if not rows:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.MISSING_RETENTION,
        )
    if len(rows) != 1:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.DUPLICATE_PROOF,
            f"R18_LINK_COUNT:{len(rows)}",
        )
    link = rows[0]
    if artifact.semantic_hash and str(link["artifact_hash"]) != artifact.semantic_hash:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.INCONSISTENT_IDENTITY,
            "R18_LINK_HASH_MISMATCH",
        )
    states = {str(artifact.state or ""), str(link["publication_state"])}
    if "PENDING_RETENTION" in states:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.PENDING_RETENTION,
            "/".join(sorted(states)),
        )
    if states != {"APPLIED"}:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.INVALID_RETENTION_STATE,
            "/".join(sorted(states)),
        )
    if path.resolve(strict=False) != Path(storage.DB_PATH).resolve(strict=False):
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            CoverageStatus.VERIFIER_ERROR,
            "DB_PATH_NOT_CONFIGURED_STORAGE_DB",
        )
    try:
        from .selection import r18_store

        r18_store.verify_governed_rhist03d_artifact(
            spec.artifact_type,
            artifact.artifact_id,
            artifact.version,
            verify_parents=True,
        )
    except (RuntimeError, ValueError, KeyError, sqlite3.Error, OSError) as exc:
        return _finding(
            spec.producer_id,
            artifact.artifact_id,
            artifact.version,
            _exception_status(exc),
            str(exc),
        )
    return _finding(
        spec.producer_id,
        artifact.artifact_id,
        artifact.version,
        CoverageStatus.COVERED,
    )


def _external_inverse(
    conn: sqlite3.Connection,
    specs: tuple[ProducerSpec, ...],
    market_db_paths: Iterable[str | Path],
    research_resolved: Path,
) -> list[dict[str, str]]:
    """Flag authority references in EXTERNAL market/evidence stores that no
    research outbox event owns.

    The same-store :func:`_inverse` cannot see these rows at all: S8/R16
    dispatch registers market-mode references through
    ``HistoricalRetentionAuthority`` in the market database while the outbox
    lives in the research database. Every external reference must therefore
    resolve to a research outbox ``reference_id``; anything else is an
    unexplained retention orphan. Read-only; never mutates either store.

    A declared market path without a references table contributes no
    findings: with no authority rows present nothing can escape. A path that
    is the research database itself is skipped to avoid double counting.
    """
    owned = {
        str(row["reference_id"])
        for row in conn.execute(
            "SELECT reference_id FROM historical_retention_outbox"
        ).fetchall()
    } if _exists(conn, "historical_retention_outbox") else set()
    wanted = {s.reference_type.value for s in specs}
    findings: list[dict[str, str]] = []
    seen: set[Path] = {research_resolved}
    for candidate in market_db_paths:
        path = Path(candidate).expanduser().resolve(strict=False)
        if path in seen or not path.is_file():
            if path not in seen and path.suffix == ".db":
                findings.append(
                    _finding(
                        "REGISTRY",
                        "*",
                        "*",
                        CoverageStatus.REGISTRY_ERROR,
                        f"MARKET_STORE_UNAVAILABLE:{path.name}",
                    )
                )
            seen.add(path)
            continue
        seen.add(path)
        market = _connect(path)
        try:
            if not _exists(market, "historical_retention_references"):
                continue
            for row in market.execute(
                "SELECT reference_id,reference_type,artifact_id,artifact_version "
                "FROM historical_retention_references"
            ).fetchall():
                reference_id = str(row["reference_id"])
                if str(row["reference_type"]) not in wanted:
                    findings.append(
                        _finding(
                            CoverageStatus.UNKNOWN_PRODUCER.value,
                            str(row["artifact_id"] or reference_id),
                            str(row["artifact_version"] or "unknown"),
                            CoverageStatus.UNKNOWN_PRODUCER,
                            f"EXTERNAL_AUTHORITY_REFERENCE:{reference_id}@{path.name}",
                        )
                    )
                    continue
                if reference_id not in owned:
                    findings.append(
                        _finding(
                            CoverageStatus.UNKNOWN_PRODUCER.value,
                            str(row["artifact_id"] or reference_id),
                            str(row["artifact_version"] or "unknown"),
                            CoverageStatus.RETENTION_ORPHAN,
                            f"EXTERNAL_AUTHORITY_REFERENCE:{reference_id}@{path.name}",
                        )
                    )
        finally:
            market.rollback()
            market.close()
    return findings


def _inverse(
    conn: sqlite3.Connection,
    specs: tuple[ProducerSpec, ...],
    real: set[tuple[str, str, str]],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    pubs = {s.artifact_type: s for s in specs if s.proof_style == "PUBLICATION"}
    r18 = {s.artifact_type: s for s in specs if s.proof_style == "R18"}
    if _exists(conn, "historical_retention_publications"):
        for row in conn.execute(
            "SELECT artifact_type,artifact_id,artifact_version,reference_type,publication_id "
            "FROM historical_retention_publications"
        ):
            raw = str(row["artifact_type"])
            spec = pubs.get(raw)
            if spec is None:
                if raw.startswith(("S8_", "R16_")):
                    findings.append(
                        _finding(
                            CoverageStatus.UNKNOWN_PRODUCER.value,
                            str(row["artifact_id"]),
                            str(row["artifact_version"]),
                            CoverageStatus.UNKNOWN_PRODUCER,
                            raw,
                        )
                    )
                continue
            key = (
                spec.producer_id,
                str(row["artifact_id"]),
                str(row["artifact_version"]),
            )
            if str(row["reference_type"]) != spec.reference_type.value:
                findings.append(
                    _finding(
                        spec.producer_id,
                        key[1],
                        key[2],
                        CoverageStatus.LINEAGE_TYPE_MISMATCH,
                        f"REFERENCE_TYPE:{row['reference_type']}",
                    )
                )
            if key not in real:
                findings.append(
                    _finding(
                        spec.producer_id,
                        key[1],
                        key[2],
                        CoverageStatus.RETENTION_ORPHAN,
                        f"PUBLICATION:{row['publication_id']}",
                    )
                )
    if _exists(conn, "r18_retention_links"):
        for row in conn.execute(
            "SELECT artifact_type,artifact_id,artifact_version,reference_id "
            "FROM r18_retention_links"
        ):
            spec = r18.get(str(row["artifact_type"]))
            if spec is None:
                findings.append(
                    _finding(
                        CoverageStatus.UNKNOWN_PRODUCER.value,
                        str(row["artifact_id"]),
                        str(row["artifact_version"]),
                        CoverageStatus.UNKNOWN_PRODUCER,
                        f"R18_LINK:{row['artifact_type']}",
                    )
                )
                continue
            key = (
                spec.producer_id,
                str(row["artifact_id"]),
                str(row["artifact_version"]),
            )
            if key not in real:
                findings.append(
                    _finding(
                        spec.producer_id,
                        key[1],
                        key[2],
                        CoverageStatus.RETENTION_ORPHAN,
                        f"R18_REFERENCE:{row['reference_id']}",
                    )
                )
    if _exists(conn, "historical_retention_outbox"):
        r18_events = {f"R18_{name}": spec for name, spec in r18.items()}
        for row in conn.execute(
            "SELECT artifact_type,artifact_id,artifact_version,reference_type,event_id "
            "FROM historical_retention_outbox"
        ):
            raw = str(row["artifact_type"])
            spec = r18_events.get(raw)
            if spec is None and ":" in raw:
                spec = pubs.get(raw.split(":", 1)[0])
            if spec is None:
                if raw.startswith(("S8_", "R16_", "R18_")):
                    findings.append(
                        _finding(
                            CoverageStatus.UNKNOWN_PRODUCER.value,
                            str(row["artifact_id"]),
                            str(row["artifact_version"]),
                            CoverageStatus.UNKNOWN_PRODUCER,
                            f"OUTBOX:{raw}",
                        )
                    )
                continue
            key = (
                spec.producer_id,
                str(row["artifact_id"]),
                str(row["artifact_version"]),
            )
            if key not in real:
                findings.append(
                    _finding(
                        spec.producer_id,
                        key[1],
                        key[2],
                        CoverageStatus.RETENTION_ORPHAN,
                        f"OUTBOX_EVENT:{row['event_id']}",
                    )
                )
            if str(row["reference_type"]) != spec.reference_type.value:
                findings.append(
                    _finding(
                        spec.producer_id,
                        key[1],
                        key[2],
                        CoverageStatus.LINEAGE_TYPE_MISMATCH,
                        f"OUTBOX_REFERENCE_TYPE:{row['reference_type']}",
                    )
                )
    if _exists(conn, "historical_retention_references") and _exists(
        conn, "historical_retention_outbox"
    ):
        wanted = {s.reference_type.value for s in specs}
        for row in conn.execute(
            "SELECT reference_id,reference_type,artifact_id,artifact_version "
            "FROM historical_retention_references"
        ):
            if str(row["reference_type"]) not in wanted:
                continue
            owner = conn.execute(
                "SELECT 1 FROM historical_retention_outbox WHERE reference_id=?",
                (row["reference_id"],),
            ).fetchone()
            if owner is None:
                findings.append(
                    _finding(
                        CoverageStatus.UNKNOWN_PRODUCER.value,
                        str(row["artifact_id"] or row["reference_id"]),
                        str(row["artifact_version"] or "unknown"),
                        CoverageStatus.RETENTION_ORPHAN,
                        f"UNOWNED_AUTHORITY_REFERENCE:{row['reference_id']}",
                    )
                )
    return findings


def _report(
    artifacts: list[Artifact],
    findings: list[dict[str, str]],
    specs: tuple[ProducerSpec, ...],
) -> dict[str, Any]:
    mandatory = {a.key for a in artifacts if not a.legacy}
    covered = {
        (f["producerId"], f["artifactId"], f["artifactVersion"])
        for f in findings
        if f["status"] == CoverageStatus.COVERED.value
    } & mandatory
    legacy = {a.key for a in artifacts if a.legacy}
    blockers = [
        f
        for f in findings
        if f["status"]
        not in {
            CoverageStatus.COVERED.value,
            CoverageStatus.LEGACY_UNGOVERNED.value,
        }
    ]
    expected = len(mandatory)
    if expected == 0 and not blockers:
        verdict = "EMPTY"
    elif expected and len(covered) == expected and not blockers:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    counts = Counter(f["status"] for f in findings)
    per_producer = {}
    for spec in specs:
        exp = sum(k[0] == spec.producer_id for k in mandatory)
        cov = sum(k[0] == spec.producer_id for k in covered)
        per_producer[spec.producer_id] = {
            "expected": exp,
            "covered": cov,
            "legacy": sum(k[0] == spec.producer_id for k in legacy),
            "coverage": cov / exp if exp else 0.0,
        }
    return {
        "registryVersion": REGISTRY_VERSION,
        "verdict": verdict,
        "expectedCount": expected,
        "coveredCount": len(covered),
        "legacyCount": len(legacy),
        "coverage": len(covered) / expected if expected else 0.0,
        "orphanCount": counts[CoverageStatus.RETENTION_ORPHAN.value],
        "blockingCount": len(blockers),
        "countsByStatus": dict(sorted(counts.items())),
        "perProducer": per_producer,
        "findings": sorted(
            findings,
            key=lambda f: (
                f["producerId"],
                f["artifactId"],
                f["artifactVersion"],
                f["status"],
                f.get("detail", ""),
            ),
        ),
    }


def audit_coverage(
    *,
    db_path: Path | None = None,
    artifact_types: Iterable[str] | None = None,
    audit_at: datetime | None = None,
    market_db_paths: Iterable[str | Path] | None = None,
) -> dict[str, Any]:
    """Read-only 03E audit. ``reportHash`` excludes the observation timestamp.

    ``market_db_paths`` optionally declares the external market/evidence
    stores whose authority references must each resolve to a research outbox
    event. When omitted, only the research database is audited and external
    references are out of view; pass the participating stores explicitly for
    acceptance. Never mutates any store.
    """
    path = Path(db_path or storage.DB_PATH).expanduser().resolve(strict=False)
    specs = _selected(artifact_types)
    findings = [
        _finding("REGISTRY", "*", "*", CoverageStatus.REGISTRY_ERROR, error)
        for error in validate_registry(specs)
    ]
    artifacts: list[Artifact] = []
    try:
        conn = _connect(path)
    except (FileNotFoundError, sqlite3.Error) as exc:
        findings.append(
            _finding(
                "REGISTRY",
                "*",
                "*",
                CoverageStatus.REGISTRY_ERROR,
                f"DATABASE_UNAVAILABLE:{type(exc).__name__}",
            )
        )
        report = _report([], findings, specs)
        return {
            **report,
            "auditAt": (audit_at or datetime.now(UTC)).isoformat(),
            "reportHash": _hash(report),
        }
    try:
        for spec in specs:
            rows, errors = _enumerate(conn, spec)
            artifacts.extend(rows)
            findings.extend(errors)
        preclassified = {
            (f["producerId"], f["artifactId"], f["artifactVersion"])
            for f in findings
            if f["artifactId"] != "*"
        }
        for artifact in artifacts:
            if artifact.key in preclassified:
                continue
            findings.append(
                _r18_proof(conn, path, artifact)
                if artifact.spec.proof_style == "R18"
                else _publication_proof(conn, path, artifact)
            )
        findings.extend(_inverse(conn, specs, {a.key for a in artifacts}))
        if market_db_paths:
            findings.extend(
                _external_inverse(conn, specs, market_db_paths, path.resolve(strict=False))
            )
    finally:
        conn.rollback()
        conn.close()
    report = _report(artifacts, findings, specs)
    return {
        **report,
        "auditAt": (audit_at or datetime.now(UTC)).isoformat(),
        "reportHash": _hash(report),
    }


def _hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def reconcile_pending_coverage(*, limit: int = 100) -> dict[str, Any]:
    """Resume only known deterministic pending R16/R18 work, bounded by ``limit``."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    before = audit_coverage()
    actions: list[dict[str, str]] = []
    remaining = limit

    from .r16_retention import finalize_publications

    with storage.connect() as conn:
        rows = (
            conn.execute(
                "SELECT rp.publication_id,rl.record_type,rl.record_id "
                "FROM pit_retention_links rl "
                "JOIN historical_retention_publications rp "
                "ON rp.publication_id=rl.publication_id "
                "WHERE rp.status<>'PUBLISHED' "
                "ORDER BY CASE rl.record_type "
                "WHEN 'DECISION_VERSION' THEN 0 WHEN 'OUTCOME' THEN 1 ELSE 2 END,"
                "rp.created_at,rp.publication_id LIMIT ?",
                (remaining,),
            ).fetchall()
            if _exists(conn, "pit_retention_links")
            else []
        )
    for row in rows:
        finalize_publications([str(row["publication_id"])])
        remaining -= 1
        actions.append(
            {
                "producer": "R16_" + str(row["record_type"]),
                "artifactId": str(row["record_id"]),
                "action": "RESUME_EXISTING_PUBLICATION",
            }
        )
        if not remaining:
            break

    if remaining:
        from .selection import r18_store

        with storage.connect() as conn:
            rows = (
                conn.execute(
                    "SELECT artifact_type,artifact_id,artifact_version "
                    "FROM r18_retention_links "
                    "WHERE publication_state='PENDING_RETENTION' "
                    "ORDER BY artifact_type,artifact_id,artifact_version LIMIT ?",
                    (remaining,),
                ).fetchall()
                if _exists(conn, "r18_retention_links")
                else []
            )
        for row in rows:
            r18_store.finalize_rhist03d_artifact(
                str(row["artifact_type"]),
                str(row["artifact_id"]),
                str(row["artifact_version"]),
                verify_parents=True,
            )
            remaining -= 1
            actions.append(
                {
                    "producer": "R18_" + str(row["artifact_type"]),
                    "artifactId": str(row["artifact_id"]),
                    "action": "FINALIZE_EXISTING_TYPED_RETENTION",
                }
            )
            if not remaining:
                break
    return {
        "limit": limit,
        "processed": len(actions),
        "actions": actions,
        "before": before,
        "after": audit_coverage(),
    }


__all__ = [
    "CoverageStatus",
    "ProducerSpec",
    "REGISTRY_VERSION",
    "audit_coverage",
    "producer_registry",
    "reconcile_pending_coverage",
    "validate_registry",
]
