"""Single owner for building and persisting the current S8 scan.

Both the HTTP route and the cash post-commit pipeline call this module.  It
binds the real S3 projection to S8 and never synthesizes a historical run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any

from .attention_order import InventoryDiscoveryV1, latest_attention_order
from .cash_a3_discovery import CashDiscoveryBatch, latest_cash_discovery
from .r5_live import R5StructureBatchV1, latest_r5_structure_batch
from .s2_market_weather import S2MarketWeatherV1, build_s2_market_weather
from .s3_cheap_discovery import S3CheapDiscoveryBatchV1, build_s3_cheap_discovery
from .s4_structure_pack import S4StructurePackBatchV1, build_s4_structure_pack
from .s5_shortlist_enrichment import S5EnrichmentBatchV1, build_s5_enrichment
from .s6_family_resolution import S6ResolutionBatchV1, build_s6_resolution
from .s7_state_gates import S7StateBatchV1, build_s7_state
from .inventory_source_bundle import InventorySourceBundleV1
from .r14_live import R14CaJoinBatchV1
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


@dataclass(frozen=True)
class CurrentScanAssembly:
    """One assembly shared by persistence and the read-only snapshot endpoint."""

    blob: S8ScanBlobV1
    s3: S3CheapDiscoveryBatchV1
    native: NativeCoreRunV1
    weather: S2MarketWeatherV1
    pack: S4StructurePackBatchV1
    s5: S5EnrichmentBatchV1 | None
    s6: S6ResolutionBatchV1
    s7: S7StateBatchV1
    tradability: TradabilityBatchV1
    prior: dict[str, Any] | None


def assemble_current_scan(
    *,
    r5_batch: R5StructureBatchV1 | None = None,
    discovery: CashDiscoveryBatch | None = None,
    attention: InventoryDiscoveryV1 | None = None,
    native_core: NativeCoreRunV1 | None = None,
    tradability_batch: TradabilityBatchV1 | None = None,
    built_at: datetime | None = None,
    bundle: InventorySourceBundleV1 | None = None,
    ca_join: R14CaJoinBatchV1 | None = None,
    loader: Any = None,
    lane: Any = None,
    event_snapshot: Any = None,
    activation_ready: bool | None = None,
) -> CurrentScanAssembly:
    """Assemble once, without persistence; caller owns its input read scope."""

    r5 = r5_batch or latest_r5_structure_batch()
    a3 = discovery or latest_cash_discovery()
    r2 = attention or latest_attention_order()
    if r5 is None:
        raise ValueError("WAIT_R5_NOT_READY")
    if a3 is None or r2 is None:
        raise ValueError("WAIT_S3_SPINE_NOT_READY")

    # Current projection time is distinct from the persisted R5 decision time.
    # The snapshot endpoint supplies one captured time for every stage.
    effective_time = built_at or datetime.now(timezone.utc)
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
        built_at=effective_time,
        loader=loader,
    )
    native = native_core or build_native_core_run(r5=r5)
    weather = build_s2_market_weather(built_at=effective_time, loader=loader)
    prior = latest_selection_payload(PROFILE_ID)
    pack = build_s4_structure_pack(r5=r5, built_at=effective_time)
    try:
        s5 = build_s5_enrichment(s4=pack, built_at=effective_time, loader=loader)
    except ValueError:
        s5 = None
    s6 = build_s6_resolution(
        s4=pack, r5=r5, s5=s5, weather=weather, attention=r2,
        bundle=bundle, ca_join=ca_join, built_at=effective_time,
        allow_enrichment_fallback=False,
    )
    s7 = build_s7_state(
        r5=r5,
        s4=pack,
        s5=s5,
        s6=s6,
        weather=weather,
        tradability=tradability,
        lane=lane,
        event_snapshot=event_snapshot,
        activation_ready=activation_ready,
        allow_enrichment_fallback=False,
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
        built_at=effective_time,
    )
    return CurrentScanAssembly(blob, s3, native, weather, pack, s5, s6, s7, tradability, prior)


def build_and_persist_current_s8(
    *,
    r5_batch: R5StructureBatchV1 | None = None,
    discovery: CashDiscoveryBatch | None = None,
    attention: InventoryDiscoveryV1 | None = None,
    native_core: NativeCoreRunV1 | None = None,
    tradability_batch: TradabilityBatchV1 | None = None,
    built_at: datetime | None = None,
    activation_ready: bool | None = None,
) -> S8ScanBlobV1:
    assembly = assemble_current_scan(
        r5_batch=r5_batch, discovery=discovery, attention=attention,
        native_core=native_core, tradability_batch=tradability_batch,
        built_at=built_at, activation_ready=activation_ready,
    )
    return persist_s8_scan(assembly.blob, prior_payload=assembly.prior)


def latest_or_build_current_s8() -> S8ScanBlobV1:
    """Return a current hash-matched S8 blob, or build the missing one."""

    r5 = latest_r5_structure_batch()
    r2 = latest_attention_order()
    if r5 is None:
        raise ValueError("WAIT_R5_NOT_READY")
    if r2 is None:
        raise ValueError("WAIT_R2_NOT_READY")
    native = build_native_core_run(r5=r5)
    effective_time = datetime.now(timezone.utc)
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


__all__ = ["assemble_current_scan", "build_and_persist_current_s8", "latest_or_build_current_s8"]
