from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from .historical_retention import HistoricalRetentionAuthority, RetentionReferenceType
from .retention_producer import DurableRetentionRegistrar
from .retention_publication import (
    RetentionEvidenceRoot,
    RetentionPublicationRequest,
    RetentionPublicationStatus,
    RetentionPublicationStore,
)

MARKET_DB_ENV = "TRENDFORGE_MARKET_DATA_DB_PATH"
ARTIFACT_TYPE = "S8_DECISION_VERSION"


def _market_db_contains_run(db_path: Path, run_id: str, trading_date: date) -> bool:
    if not db_path.is_file():
        return False
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT trading_date FROM market_data_manifests WHERE run_id = ? LIMIT 1",
                (run_id,),
            ).fetchone()
    except sqlite3.Error:
        return False
    return row is not None and row[0] == trading_date.isoformat()


def resolve_market_db_path(
    *,
    research_db_path: Path,
    collector_run_id: str,
    trading_date: date,
    explicit: Path | None = None,
) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    configured = os.getenv(MARKET_DB_ENV)
    if configured:
        candidates.append(Path(configured))
    candidates.append(research_db_path)
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        if _market_db_contains_run(resolved, collector_run_id, trading_date):
            return resolved
    raise RuntimeError(
        "WAIT_RHIST03_MARKET_LINEAGE_UNBOUND: exact collector run is not present in an approved market-data DB"
    )


def persist_protected_s8(
    *,
    blob: Any,
    prior_payload: dict[str, Any] | None,
    collector_run_id: str,
    trading_date: date,
    market_db_path: Path | None = None,
):
    """Protect exact collector evidence before publishing immutable S8."""

    from . import storage
    from .selection.s8_persist_run import persist_s8_scan

    if not collector_run_id.strip():
        raise ValueError("WAIT_RHIST03_COLLECTOR_RUN_REQUIRED")
    if getattr(blob, "trading_date", None) != trading_date.isoformat():
        raise ValueError("WAIT_RHIST03_TRADING_DATE_LINEAGE_MISMATCH")
    research_db = Path(storage.DB_PATH).expanduser().resolve(strict=False)
    market_db = resolve_market_db_path(
        research_db_path=research_db,
        collector_run_id=collector_run_id,
        trading_date=trading_date,
        explicit=market_db_path,
    )
    authority = HistoricalRetentionAuthority(db_path=market_db)
    registrar = DurableRetentionRegistrar(db_path=research_db, authority=authority)
    publications = RetentionPublicationStore(db_path=research_db, registrar=registrar)
    lineage = getattr(blob, "lineage", None)
    lineage_payload = (
        lineage.model_dump(mode="json", by_alias=True)
        if lineage is not None and hasattr(lineage, "model_dump")
        else {}
    )
    request = RetentionPublicationRequest(
        artifact_type=ARTIFACT_TYPE,
        artifact_id=str(blob.run_id),
        artifact_version=str(getattr(blob, "schema_version", "unknown")),
        reference_type=RetentionReferenceType.DECISION_VERSION,
        evidence_roots=(
            RetentionEvidenceRoot(
                role="COLLECTOR_RUN",
                run_id=collector_run_id,
                trading_date=trading_date,
            ),
        ),
        lineage={
            "collectorRunId": collector_run_id,
            "tradingDate": trading_date.isoformat(),
            "s8": lineage_payload,
            "profileId": getattr(blob, "profile_id", None),
            "profileVersion": getattr(blob, "profile_version", None),
        },
        created_at=blob.built_at,
    )
    staged = publications.stage_owned(request)
    protected = publications.finalize(staged.publication_id)
    if protected.status is not RetentionPublicationStatus.PROTECTED_PENDING_ARTIFACT:
        raise RuntimeError(
            f"WAIT_RHIST03_RETENTION_BLOCKED:{protected.last_error or protected.status.value}"
        )
    stored = persist_s8_scan(blob, prior_payload=prior_payload)
    published = publications.mark_published(staged.publication_id)
    if published.status is not RetentionPublicationStatus.PUBLISHED:
        raise RuntimeError("WAIT_RHIST03_PUBLICATION_INCOMPLETE")
    return stored
