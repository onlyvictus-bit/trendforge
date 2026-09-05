"""Single owner for building and persisting the current S8 scan.

Both the HTTP route and the cash post-commit pipeline call this module.  It
binds the real S3 projection to S8 and never synthesizes a historical run.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .attention_order import InventoryDiscoveryV1, latest_attention_order
from .cash_a3_discovery import CashDiscoveryBatch, latest_cash_discovery
from .r5_live import R5StructureBatchV1, latest_r5_structure_batch
from .s2_market_weather import build_s2_market_weather
from .s3_cheap_discovery import build_s3_cheap_discovery
from .s4_structure_pack import build_s4_structure_pack
from .s5_shortlist_enrichment import build_s5_enrichment
from .s6_family_resolution import build_s6_resolution
from .s7_state_gates import build_s7_state
from .tradability import TradabilityBatchV1, build_tradability_batch
from .s8_persist_run import (
    PROFILE_ID,
    S8ScanBlobV1,
    build_s8_scan,
    latest_matching_s8,
    persist_s8_scan,
)
from .store import latest_selection_payload
from ..scanners.native_core import NativeCoreRunV1, build_native_core_run


def build_and_persist_current_s8(
    *,
    r5_batch: R5StructureBatchV1 | None = None,
    discovery: CashDiscoveryBatch | None = None,
    attention: InventoryDiscoveryV1 | None = None,
    native_core: NativeCoreRunV1 | None = None,
    tradability_batch: TradabilityBatchV1 | None = None,
    built_at: datetime | None = None,
) -> S8ScanBlobV1:
    """Build one current, lineage-complete S8 blob and persist it immutably."""

    r5 = r5_batch or latest_r5_structure_batch()
    a3 = discovery or latest_cash_discovery()
    r2 = attention or latest_attention_order()
    if r5 is None:
        raise ValueError("WAIT_R5_NOT_READY")
    if a3 is None or r2 is None:
        raise ValueError("WAIT_S3_SPINE_NOT_READY")

    effective_time = built_at or getattr(r5, "built_at", None) or datetime.now(timezone.utc)
    symbols = tuple(
        str(row.symbol).upper() for row in getattr(r5, "rows", ())
        if getattr(row, "symbol", None)
    )
    tradability = tradability_batch or build_tradability_batch(
        symbols=symbols,
        profile_id="PRF-003",
        decision_at=effective_time,
        sources={} if not symbols else None,
    )

    s3 = build_s3_cheap_discovery(
        discovery=a3,
        attention=r2,
        built_at=built_at,
    )
    native = native_core or build_native_core_run(r5=r5)
    weather = build_s2_market_weather()
    prior = latest_selection_payload(PROFILE_ID)
    pack = build_s4_structure_pack(r5=r5)
    try:
        s5 = build_s5_enrichment(s4=pack)
    except ValueError:
        s5 = None
    s6 = build_s6_resolution(s4=pack, r5=r5, s5=s5, weather=weather)
    s7 = build_s7_state(
        r5=r5,
        s4=pack,
        s5=s5,
        s6=s6,
        weather=weather,
        tradability=tradability,
    )
    blob = build_s8_scan(
        s7=s7,
        s6=s6,
        pack=pack,
        r5=r5,
        s5=s5,
        weather=weather,
        s3_batch=s3,
        native_core=native,
        prior_payload=prior,
    )
    return persist_s8_scan(blob, prior_payload=prior)


def latest_or_build_current_s8() -> S8ScanBlobV1:
    """Return a current hash-matched S8 blob, or build the missing one."""

    r5 = latest_r5_structure_batch()
    r2 = latest_attention_order()
    if r5 is None:
        raise ValueError("WAIT_R5_NOT_READY")
    if r2 is None:
        raise ValueError("WAIT_R2_NOT_READY")
    native = build_native_core_run(r5=r5)
    effective_time = getattr(r5, "built_at", None) or datetime.now(timezone.utc)
    symbols = tuple(
        str(row.symbol).upper() for row in getattr(r5, "rows", ())
        if getattr(row, "symbol", None)
    )
    tradability = build_tradability_batch(
        symbols=symbols,
        profile_id="PRF-003",
        decision_at=effective_time,
        sources={} if not symbols else None,
    )
    try:
        matched = latest_matching_s8(
            current_r5_run_hash=r5.run_hash,
            current_r2_run_hash=r2.run_hash,
            current_native_guidance_run_hash=native.run_hash,
            current_tradability_run_hash=tradability.run_hash,
        )
    except ValueError as exc:
        if str(exc) != "WAIT_S8_LINEAGE":
            raise
        matched = None
    if (
        matched is not None
        and matched.trading_date is not None
        and getattr(matched.lineage, "s2_run_id", None) is not None
        and getattr(matched.lineage, "tradability_run_hash", None) is not None
        and not matched.lineage.missing_stages
    ):
        return matched
    return build_and_persist_current_s8(
        r5_batch=r5,
        attention=r2,
        native_core=native,
        tradability_batch=tradability,
        built_at=effective_time,
    )


__all__ = ["build_and_persist_current_s8", "latest_or_build_current_s8"]
