"""READ-ONLY load of the latest hash-matched spine (R1, R2-A, R4, R14, R5).

The adapter never persists, never mutates, and never falls back to last-good
on a hash mismatch: any mismatch is a hard WAIT_HYBRID_LINEAGE_MISMATCH.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from ..selection.attention_order import (
    InventoryDiscoveryV1,
    latest_attention_order,
)
from ..selection.inventory_source_bundle import (
    InventorySourceBundleV1,
    latest_inventory_source_bundle,
)
from ..selection.r14_live import R14CaJoinBatchV1, latest_r14_ca_join
from ..selection.r4_live import R4IdentityPinV1, latest_r4_identity_pin
from ..selection.r5_live import R5StructureBatchV1, latest_r5_structure_batch

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class HybridSpineV1(BaseModel):
    model_config = MODEL_CONFIG

    bundle: InventorySourceBundleV1
    attention: InventoryDiscoveryV1
    r4_pin: R4IdentityPinV1 | None = None
    ca_join: R14CaJoinBatchV1 | None = None
    structure: R5StructureBatchV1 | None = None
    decision_at: datetime


def load_hybrid_spine() -> HybridSpineV1:
    bundle = latest_inventory_source_bundle()
    attention = latest_attention_order()
    if bundle is None or attention is None:
        raise ValueError("WAIT_HYBRID_R2_NOT_READY")
    if (
        attention.r1_bundle_id != bundle.bundle_id
        or attention.r1_bundle_hash != bundle.bundle_hash
        or attention.collector_run_id != bundle.collector_run_id
        or attention.cash_pipeline_fingerprint != bundle.cash_pipeline_fingerprint
        or attention.permission_fingerprint != bundle.permission_fingerprint
    ):
        raise ValueError("WAIT_HYBRID_LINEAGE_MISMATCH")

    pin = latest_r4_identity_pin()
    if pin is not None and (
        pin.r1_bundle_id != bundle.bundle_id
        or pin.r1_bundle_hash != bundle.bundle_hash
        or pin.r2_run_id != attention.run_id
        or pin.r2_run_hash != attention.run_hash
    ):
        raise ValueError("WAIT_HYBRID_LINEAGE_MISMATCH")

    ca_join = latest_r14_ca_join()
    if ca_join is None:
        raise ValueError("WAIT_HYBRID_R14_NOT_READY")
    if (
        ca_join.r1_bundle_hash != bundle.bundle_hash
        or ca_join.r2_run_hash != attention.run_hash
        or (pin is not None and ca_join.r4_run_hash != pin.run_hash)
    ):
        raise ValueError("WAIT_HYBRID_LINEAGE_MISMATCH")

    structure = latest_r5_structure_batch()
    if structure is not None and (
        structure.r1_bundle_hash != bundle.bundle_hash
        or structure.r2_run_hash != attention.run_hash
        or structure.r14_run_hash != ca_join.run_hash
    ):
        raise ValueError("WAIT_HYBRID_LINEAGE_MISMATCH")

    return HybridSpineV1(
        bundle=bundle,
        attention=attention,
        r4_pin=pin,
        ca_join=ca_join,
        structure=structure,
        decision_at=attention.built_at,
    )
