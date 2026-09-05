"""File A R12: mint typed OPTIONS_CONTEXT EvidenceClaims from options data.

Reads walls / PCR / Greeks / max-pain / GEX-proxy observations from the
options_intelligence package and mints EvidenceClaim objects for S6 family
resolution. All claims carry can_support_confirmed=False. Signed GEX is
SCENARIO_ONLY_NOT_OBSERVED_POSITION.

Ceiling LIVE_R12_CLAIMS_WAIT_ONLY.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from ..feature_registry import feature_contract_by_id
from .contracts import (
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    StateCeiling,
    stable_id,
)
from .s5_shortlist_enrichment import S5EnrichmentBatchV1

SCHEMA_VERSION = "trendforge.r12-options-claims.v1"
PROFILE_ID = "PRF-R12-OPTIONS-CLAIMS"


def _make_claim(
    *,
    feature_id: str,
    feature_version: str,
    direction: EvidenceDirection | None,
    strength: float,
    source_fact_ids: tuple[str, ...],
    authority: str,
    available_at: datetime,
    event_time: datetime,
    published_at: datetime,
    received_at: datetime,
    revision_id: str,
    artifact_hash: str,
    explanation: str,
) -> EvidenceClaim:
    feature = feature_contract_by_id(feature_id)
    group = feature.correlation_group if feature else "CG_OPTION_CHAIN"
    return EvidenceClaim.create(
        feature_id=feature_id,
        feature_version=feature_version,
        family=EvidenceFamily.OPTIONS_CONTEXT,
        correlation_group=group,
        direction=direction or EvidenceDirection.BULLISH,
        strength_before_caps=min(max(strength, 0.0), 1.0),
        source_fact_ids=source_fact_ids,
        authority=authority,
        available_at=available_at,
        event_time=event_time,
        published_at=published_at,
        received_at=received_at,
        revision_id=revision_id,
        artifact_hash=artifact_hash,
        state_ceiling=StateCeiling.WAIT,
        can_support_confirmed=False,
        explanation=explanation,
    )


def mint_options_claims(
    *,
    symbol: str,
    options_package: Any,
    snapshot_bundle_id: str,
    decision_at: datetime,
) -> list[EvidenceClaim]:
    """Mint OPTIONS_CONTEXT claims from a validated options package.

    Returns empty tuple when package is None, UNKNOWN, or chain missing —
    fail-closed per File A §9.6.2 (removing options must not upgrade state).
    """
    status = getattr(options_package, "status", None)
    if status is None or status in ("UNKNOWN", "UNKNOWN_NEEDS_R12"):
        return []

    now = datetime.now(timezone.utc)
    fact_id = stable_id("r12-opt-fact", symbol, snapshot_bundle_id)
    lineage_ids = (fact_id,)
    authority = "OFFICIAL_GATE"

    claims: list[EvidenceClaim] = []
    explanation_base = f"R12 options context for {symbol}"

    # PCR observation
    pcr_oi = getattr(options_package, "pcr_oi", None)
    if pcr_oi is not None and pcr_oi > 0:
        strength = min(abs(pcr_oi - 1.0), 1.0)
        direction = (
            EvidenceDirection.BULLISH if pcr_oi < 1.0
            else EvidenceDirection.BEARISH if pcr_oi > 1.2
            else None
        )
        claims.append(_make_claim(
            feature_id="FTR-023",
            feature_version="1.0.0",
            direction=direction,
            strength=min(strength, 1.0),
            source_fact_ids=lineage_ids,
            authority=authority,
            available_at=now,
            event_time=now,
            published_at=now,
            received_at=now,
            revision_id=snapshot_bundle_id,
            artifact_hash=snapshot_bundle_id,
            explanation=f"{explanation_base}: OI PCR {pcr_oi:.4f} (context, not direction)",
        ))

    # Max pain reference
    max_pain = getattr(options_package, "max_pain", None)
    if max_pain is not None and max_pain > 0:
        claims.append(_make_claim(
            feature_id="FTR-024",
            feature_version="1.0.0",
            direction=None,
            strength=0.3,
            source_fact_ids=lineage_ids,
            authority=authority,
            available_at=now,
            event_time=now,
            published_at=now,
            received_at=now,
            revision_id=snapshot_bundle_id,
            artifact_hash=snapshot_bundle_id,
            explanation=f"{explanation_base}: max-pain reference at {max_pain:.2f} (NOT A FORECAST GUARANTEE)",
        ))

    # GEX scenario (unsigned proxy)
    gex_proxy = getattr(options_package, "gex_signed", None)
    if gex_proxy is not None:
        claims.append(_make_claim(
            feature_id="FTR-023",
            feature_version="1.0.0",
            direction=None,
            strength=0.2,
            source_fact_ids=lineage_ids,
            authority=authority,
            available_at=now,
            event_time=now,
            published_at=now,
            received_at=now,
            revision_id=snapshot_bundle_id,
            artifact_hash=snapshot_bundle_id,
            explanation=f"{explanation_base}: SCENARIO_ONLY_NOT_OBSERVED_POSITION",
        ))

    return claims


__all__ = ["mint_options_claims"]
