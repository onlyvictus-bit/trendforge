"""Live File A R4: PK0 pin + explicit ID inventory overlay.

This is NOT:
- A2 canonical identity (`cash_a2_identity.py` already owns that)
- A4 PIT bars / CA vintages (`cash_a4_history.py`)
- Q5-R4 enrichment/MCX/options fixtures (`r4_fixtures.py`)
- R7 PK shadow worker (`pk_fixture_worker.py`)
- R3 family resolution or R5 closed-bar structure

This IS:
- Bind each live R2 row to an A2 instrument_id, or mark UNKNOWN_ID
- Refuse companion scripCode / numeric card IDs as identity
- Persist the pinned PK inventory digest (zero vote, no sidecar runtime)
- Apply early PIT/delisting membership only when fixtures are supplied;
  otherwise PIT_UNPROVEN (do not invent a live delist master)
- Never rewrite R2 public_state, R3 resolution, or R5 structure
- Never emit CONFIRMED, quantity, or broker fields
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ..scanners.pk_compatibility import (
    PKUniverseMembershipFixture,
    build_pk_r4_inventory,
)
from .attention_order import InventoryDiscoveryV1, latest_attention_order
from .cash_a2_identity import CashIdentityBatch, latest_cash_identity
from .contracts import SelectionState, StateCeiling, stable_id
from .inventory_source_bundle import (
    InventorySourceBundleV1,
    latest_inventory_source_bundle,
)
from .store import latest_selection_payload, persist_selection_payload

SCHEMA_VERSION = "trendforge.identity-pin.v1"
PROFILE_ID = "PRF-R4-LIVE-PIN"
PROFILE_VERSION = "1.0.0"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)
SCRIP_LIKE = re.compile(r"^\d{5,}$")

IdentityStatus = Literal["PINNED", "UNKNOWN_ID", "COMPANION_REJECTED"]
PitStatus = Literal["PIT_UNPROVEN", "PIT_ELIGIBLE", "PIT_DELISTED_OR_OUT"]


class R4IdentityRowV1(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    symbol: str
    instrument_id: str | None = None
    isin: str | None = None
    series: str | None = None
    r2_public_state: SelectionState
    r4_state: SelectionState = SelectionState.WAIT
    identity_status: IdentityStatus
    pit_status: PitStatus
    pk_runtime_used: bool = False
    pk_can_vote: bool = False
    can_affect_rank: bool = False
    can_affect_state: bool = False
    can_support_confirmed: bool = False
    display_order: int = Field(gt=0)
    why_wait: tuple[str, ...] = ()

    @model_validator(mode="after")
    def live_ceiling(self) -> "R4IdentityRowV1":
        if self.r4_state is SelectionState.CONFIRMED:
            raise ValueError("live R4 cannot emit CONFIRMED")
        if self.pk_can_vote or self.pk_runtime_used or self.can_affect_rank:
            raise ValueError("R4 PK pin cannot vote or affect rank")
        if self.can_affect_state or self.can_support_confirmed:
            raise ValueError("R4 cannot change public state or unlock CONFIRMED")
        return self


class R4IdentityPinV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    run_id: str
    run_hash: str
    r1_bundle_id: str
    r1_bundle_hash: str
    r2_run_id: str
    r2_run_hash: str
    collector_run_id: str
    cash_pipeline_run_id: str
    permission_fingerprint: str
    trading_date: str
    decision_at: datetime
    state_ceiling: StateCeiling = StateCeiling.WAIT
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    acceptance_ceiling: str = "LIVE_ID_PIN_WAIT_ONLY"
    pk_inventory_version: str
    pk_upstream_commit: str
    pk_inventory_digest: str
    pk_upstream_can_vote: bool = False
    pk_runtime_required: bool = False
    pinned_id_count: int = Field(ge=0)
    unknown_id_count: int = Field(ge=0)
    companion_rejected_count: int = Field(ge=0)
    pit_unproven_count: int = Field(ge=0)
    universe_count: int = Field(ge=0)
    persisted: bool = False
    rows: tuple[R4IdentityRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def live_ceiling(self) -> "R4IdentityPinV1":
        if self.universe_count != len(self.rows):
            raise ValueError("R4 universe count does not match rows")
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("R4 cannot activate sources or unlock CONFIRMED")
        if self.pk_upstream_can_vote or self.pk_runtime_required:
            raise ValueError("R4 cannot require or vote through PK runtime")
        if any(row.r4_state is SelectionState.CONFIRMED for row in self.rows):
            raise ValueError("R4 live rows cannot be CONFIRMED")
        return self


def _companion_rejected(symbol: str, instrument_id: str | None) -> bool:
    if SCRIP_LIKE.fullmatch(symbol.strip()):
        return True
    if instrument_id is not None and SCRIP_LIKE.fullmatch(instrument_id.strip()):
        return True
    return False


def _pit_status(
    *,
    instrument_id: str | None,
    decision_at: datetime,
    membership: tuple[PKUniverseMembershipFixture, ...],
) -> PitStatus:
    if instrument_id is None or not membership:
        return "PIT_UNPROVEN"
    matches = [item for item in membership if item.instrument_id == instrument_id]
    if not matches:
        return "PIT_UNPROVEN"
    if any(item.eligible_at(decision_at) for item in matches):
        return "PIT_ELIGIBLE"
    return "PIT_DELISTED_OR_OUT"


def _inventory_digest() -> tuple[str, str, str]:
    inventory = build_pk_r4_inventory()
    payload = {
        "commit": inventory.upstream_pin.commit,
        "licenseHash": inventory.upstream_pin.license_hash,
        "menuHash": inventory.menu_source_hash,
        "scannerHash": inventory.scanner_source_hash,
        "dependencyHash": inventory.dependency_lock_hash,
        "entries": [entry.scanner_id for entry in inventory.entries],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return (
        inventory.manifest_version,
        inventory.upstream_pin.commit,
        digest,
    )


def build_r4_identity_pin(
    *,
    bundle: InventorySourceBundleV1 | None = None,
    attention: InventoryDiscoveryV1 | None = None,
    identity: CashIdentityBatch | None = None,
    membership: tuple[PKUniverseMembershipFixture, ...] = (),
    decision_at: datetime | None = None,
) -> R4IdentityPinV1:
    r1 = bundle or latest_inventory_source_bundle()
    r2 = attention or latest_attention_order()
    a2 = identity if identity is not None else latest_cash_identity()
    if r1 is None or r2 is None:
        raise ValueError("WAIT_R4_R1_R2_NOT_READY")
    if r2.r1_bundle_id != r1.bundle_id or r2.r1_bundle_hash != r1.bundle_hash:
        raise ValueError("WAIT_R4_LINEAGE_MISMATCH")
    at = decision_at or r2.built_at
    by_symbol = {}
    if a2 is not None:
        by_symbol = {row.instrument.symbol.upper(): row for row in a2.rows}
    pk_version, pk_commit, pk_digest = _inventory_digest()
    rows: list[R4IdentityRowV1] = []
    for item in r2.rows:
        symbol = item.symbol.upper()
        matched = by_symbol.get(symbol)
        instrument_id = None if matched is None else matched.instrument.instrument_id
        reasons: list[str] = ["R4_LIVE_WAIT_CEILING"]
        if _companion_rejected(symbol, instrument_id):
            status: IdentityStatus = "COMPANION_REJECTED"
            instrument_id = None
            reasons.append("COMPANION_SCRIP_CODE_NOT_IDENTITY")
        elif matched is None:
            status = "UNKNOWN_ID"
            reasons.append("UNKNOWN_ID")
        else:
            status = "PINNED"
        pit = _pit_status(
            instrument_id=instrument_id, decision_at=at, membership=membership
        )
        if pit == "PIT_UNPROVEN":
            reasons.append("PIT_UNPROVEN")
        elif pit == "PIT_DELISTED_OR_OUT":
            reasons.append("PIT_DELISTED_OR_OUT")
        rows.append(
            R4IdentityRowV1(
                candidate_id=item.candidate_id,
                symbol=symbol,
                instrument_id=instrument_id,
                isin=None if matched is None else matched.instrument.isin,
                series=None if matched is None else matched.instrument.series,
                r2_public_state=item.public_state,
                identity_status=status,
                pit_status=pit,
                display_order=item.display_order,
                why_wait=tuple(dict.fromkeys(reasons)),
            )
        )
    identity_payload = {
        "r1BundleHash": r1.bundle_hash,
        "r2RunHash": r2.run_hash,
        "pkInventoryDigest": pk_digest,
        "profileVersion": PROFILE_VERSION,
        "decisionAt": at.isoformat(),
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return R4IdentityPinV1(
        run_id=stable_id("r4-identity-pin", r1.bundle_id, r2.run_id, run_hash),
        run_hash=run_hash,
        r1_bundle_id=r1.bundle_id,
        r1_bundle_hash=r1.bundle_hash,
        r2_run_id=r2.run_id,
        r2_run_hash=r2.run_hash,
        collector_run_id=r1.collector_run_id,
        cash_pipeline_run_id=r1.cash_pipeline_run_id,
        permission_fingerprint=r1.permission_fingerprint,
        trading_date=r1.trading_date.isoformat(),
        decision_at=at,
        pk_inventory_version=pk_version,
        pk_upstream_commit=pk_commit,
        pk_inventory_digest=pk_digest,
        pinned_id_count=sum(row.identity_status == "PINNED" for row in rows),
        unknown_id_count=sum(row.identity_status == "UNKNOWN_ID" for row in rows),
        companion_rejected_count=sum(
            row.identity_status == "COMPANION_REJECTED" for row in rows
        ),
        pit_unproven_count=sum(row.pit_status == "PIT_UNPROVEN" for row in rows),
        universe_count=len(rows),
        rows=tuple(rows),
        warnings=(
            "R4 pins identity and the PK inventory. It is not A2, not A4, not R5, "
            "and cannot confirm a trade.",
        ),
    )


def persist_r4_identity_pin(value: R4IdentityPinV1) -> R4IdentityPinV1:
    stored = value.model_copy(update={"persisted": True})
    persist_selection_payload(
        run_id=stored.run_id,
        profile_id=PROFILE_ID,
        as_of=stored.decision_at,
        payload=stored.model_dump(mode="json", by_alias=True),
        candidates=tuple(
            (
                row.candidate_id,
                row.symbol,
                row.r4_state.value,
                row.model_dump(mode="json", by_alias=True),
            )
            for row in stored.rows
        ),
    )
    return stored


def latest_r4_identity_pin() -> R4IdentityPinV1 | None:
    payload = latest_selection_payload(PROFILE_ID)
    return R4IdentityPinV1.model_validate(payload) if payload is not None else None
