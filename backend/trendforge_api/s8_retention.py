from __future__ import annotations

import hashlib
import json
import os
import re
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
CASH_SOURCE_KEY = "nse_bhavcopy_eod"
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def _source_role(source_key: str) -> str:
    normalized = "".join(
        character if character.isalnum() else "_" for character in source_key.upper()
    )
    return f"R1_SOURCE_{normalized}"


def evidence_roots_from_bundle(bundle: Any) -> tuple[RetentionEvidenceRoot, ...]:
    """Return exact object-backed R1 roots without consulting current/latest data."""

    roots: list[RetentionEvidenceRoot] = []
    cash_root_found = False
    for source in sorted(
        getattr(bundle, "source_records", ()), key=lambda row: str(row.source_key)
    ):
        digest = getattr(source, "last_good_hash", None)
        if digest is None:
            continue
        normalized = str(digest).casefold()
        if not _HASH_PATTERN.fullmatch(normalized):
            raise ValueError(
                f"WAIT_RHIST03_INVALID_EVIDENCE_HASH:{source.source_key}"
            )
        source_key = str(source.source_key)
        roots.append(
            RetentionEvidenceRoot(
                role=_source_role(source_key),
                content_hash=normalized,
            )
        )
        if source_key == CASH_SOURCE_KEY:
            cash_root_found = True
    if not cash_root_found:
        raise ValueError("WAIT_RHIST03_CASH_EVIDENCE_ROOT_REQUIRED")
    return tuple(roots)


def _market_db_contains_roots(
    db_path: Path, evidence_roots: tuple[RetentionEvidenceRoot, ...]
) -> bool:
    hashes = tuple(
        sorted({root.content_hash for root in evidence_roots if root.content_hash})
    )
    if not hashes or not db_path.is_file():
        return False
    try:
        with sqlite3.connect(db_path) as conn:
            placeholders = ",".join("?" for _ in hashes)
            count = conn.execute(
                "SELECT COUNT(*) FROM market_data_objects "
                f"WHERE content_hash IN ({placeholders})",
                hashes,
            ).fetchone()[0]
    except sqlite3.Error:
        return False
    return int(count) == len(hashes)


def resolve_market_db_path(
    *,
    research_db_path: Path,
    evidence_roots: tuple[RetentionEvidenceRoot, ...],
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
        if _market_db_contains_roots(resolved, evidence_roots):
            return resolved
    raise RuntimeError(
        "WAIT_RHIST03_MARKET_LINEAGE_UNBOUND: exact R1 evidence hashes are not "
        "present in an approved market-data DB"
    )


def persist_protected_s8(
    *,
    blob: Any,
    prior_payload: dict[str, Any] | None,
    evidence_roots: tuple[RetentionEvidenceRoot, ...],
    publication_lineage: dict[str, Any],
    trading_date: date,
    market_db_path: Path | None = None,
):
    """Protect exact collector evidence before making the immutable S8 artifact public.

    Cross-database atomicity is impossible without a distributed transaction.
    This uses a fail-closed two-phase publication: stage durable intent -> apply
    exact market retention -> persist immutable S8 -> mark publication PUBLISHED.
    A crash can create extra protection, never an unprotected successful decision.
    """

    from . import storage
    from .selection.s8_persist_run import persist_s8_scan

    if not evidence_roots:
        raise ValueError("WAIT_RHIST03_EVIDENCE_ROOTS_REQUIRED")
    if any(root.content_hash is None for root in evidence_roots):
        raise ValueError("WAIT_RHIST03_CONTENT_HASH_REQUIRED")
    if getattr(blob, "trading_date", None) != trading_date.isoformat():
        raise ValueError("WAIT_RHIST03_TRADING_DATE_LINEAGE_MISMATCH")
    research_db = Path(storage.DB_PATH).expanduser().resolve(strict=False)
    market_db = resolve_market_db_path(
        research_db_path=research_db,
        evidence_roots=evidence_roots,
        explicit=market_db_path,
    )
    authority = HistoricalRetentionAuthority(db_path=market_db)
    registrar = DurableRetentionRegistrar(db_path=research_db, authority=authority)
    publications = RetentionPublicationStore(db_path=research_db, registrar=registrar)
    s8_lineage = getattr(blob, "lineage", None)
    lineage_payload = (
        s8_lineage.model_dump(mode="json", by_alias=True)
        if s8_lineage is not None and hasattr(s8_lineage, "model_dump")
        else {}
    )
    request = RetentionPublicationRequest(
        artifact_type=ARTIFACT_TYPE,
        artifact_id=str(blob.run_id),
        artifact_version=str(getattr(blob, "schema_version", "unknown")),
        reference_type=RetentionReferenceType.DECISION_VERSION,
        evidence_roots=evidence_roots,
        lineage={
            **publication_lineage,
            "tradingDate": trading_date.isoformat(),
            "s8": lineage_payload,
            # Seal the exact persisted payload, not merely its upstream IDs.
            "s8PayloadHash": hashlib.sha256(json.dumps(
                blob.model_copy(update={"persisted": True}).model_dump(mode="json", by_alias=True),
                sort_keys=True, separators=(",", ":"), default=str,
            ).encode()).hexdigest(),
            "profileId": getattr(blob, "profile_id", None),
            "profileVersion": getattr(blob, "profile_version", None),
        },
        created_at=blob.built_at,
    )
    staged = publications.stage_owned(request)
    protected = publications.finalize(staged.publication_id)
    if protected.status not in {
        RetentionPublicationStatus.PROTECTED_PENDING_ARTIFACT,
        RetentionPublicationStatus.PUBLISHED,
    }:
        raise RuntimeError(
            f"WAIT_RHIST03_RETENTION_BLOCKED:{protected.last_error or protected.status.value}"
        )
    stored = persist_s8_scan(blob, prior_payload=prior_payload)
    published = publications.mark_published(staged.publication_id)
    if published.status is not RetentionPublicationStatus.PUBLISHED:
        raise RuntimeError("WAIT_RHIST03_PUBLICATION_INCOMPLETE")
    return stored
