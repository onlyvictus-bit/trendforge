"""R2 deterministic research-attention ordering over one accepted R1 bundle."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .contracts import EvidenceDirection, SelectionState, StateCeiling, stable_id
from .inventory_source_bundle import InventorySourceBundleV1, StockEvidenceRecordV1
from .store import latest_selection_payload, persist_selection_payload

SCHEMA_VERSION = "trendforge.inventory-discovery.v1"
PROFILE_ID = "PRF-R2-ATTENTION"
FORMULA_ID = "ATTN-CASH-V1"
FORMULA_VERSION = "1.0.0"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class AttentionRowV1(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    symbol: str
    public_state: SelectionState
    state_ceiling: StateCeiling = StateCeiling.WAIT
    evidence_direction: EvidenceDirection
    display_order: int = Field(gt=0)
    attention_rank: int | None = Field(default=None, gt=0)
    attention_priority: float | None = Field(default=None, ge=0.0, le=1.0)
    attention_band: str
    supporting_families: tuple[str, ...]
    opposing_claims: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    conflicts: tuple[str, ...]
    completeness: float = Field(ge=0.0, le=1.0)
    freshness: str
    source_quality: str
    restriction_state: str
    why_visible: str
    why_not_confirmed: tuple[str, ...]
    lineage: dict[str, str | None]
    dataset_root_ids: tuple[str, ...]
    entry: None = None
    target: None = None
    stop: None = None
    risk_reward: None = None

    @model_validator(mode="after")
    def attention_is_not_trade_authority(self) -> "AttentionRowV1":
        if self.public_state is SelectionState.CONFIRMED:
            raise ValueError("R2 cannot contain CONFIRMED")
        if self.public_state is not SelectionState.WATCH and self.attention_rank is not None:
            raise ValueError("only WATCH rows can receive attention rank")
        return self


class InventoryDiscoveryV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    run_id: str
    run_hash: str
    r1_bundle_id: str
    r1_bundle_hash: str
    collector_run_id: str
    cash_pipeline_run_id: str
    cash_pipeline_fingerprint: str
    permission_fingerprint: str
    snapshot_bundle_id: str
    trading_date: str
    built_at: datetime
    formula_id: str = FORMULA_ID
    formula_version: str = FORMULA_VERSION
    mode: str = "BASELINE"
    source_activation_ready: bool = False
    acceptance_ceiling: str = "WATCH_WAIT_REJECT"
    universe_count: int = Field(ge=0)
    watch_count: int = Field(ge=0)
    wait_count: int = Field(ge=0)
    reject_count: int = Field(ge=0)
    persisted: bool = False
    rows: tuple[AttentionRowV1, ...]
    shadow_comparison: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_counts_and_ceiling(self) -> "InventoryDiscoveryV1":
        if self.universe_count != len(self.rows):
            raise ValueError("R2 universe count does not match rows")
        if self.watch_count + self.wait_count + self.reject_count != len(self.rows):
            raise ValueError("R2 state counts do not match rows")
        if self.source_activation_ready:
            raise ValueError("R2 source activation is not approved")
        if any(row.public_state is SelectionState.CONFIRMED for row in self.rows):
            raise ValueError("R2 cannot contain CONFIRMED")
        return self


def _priority(stock: StockEvidenceRecordV1) -> float | None:
    ret = stock.cheap_features.get("returnPercentile")
    volume = stock.cheap_features.get("volumePercentile")
    turnover = stock.cheap_features.get("turnoverPercentile")
    if not isinstance(ret, (int, float)):
        return None
    activity_values = [value for value in (volume, turnover) if isinstance(value, (int, float))]
    if not activity_values:
        return None
    # Both components belong to one cash-session dataset root; this orders attention only.
    return round(0.5 * float(ret) + 0.5 * max(float(value) for value in activity_values), 6)


def _source_quality(stock: StockEvidenceRecordV1) -> tuple[str, str]:
    cash = stock.source_clock.get("nse_bhavcopy_eod") or {}
    usability = cash.get("usabilityState")
    if usability == "USABLE_CURRENT":
        return "CURRENT", "OFFICIAL_STRUCTURED"
    if usability == "VALID_EMPTY_CURRENT":
        return "VALID_EMPTY", "NO_STOCK_EVIDENCE"
    if usability == "STALE_LAST_GOOD":
        return "STALE", "LAST_GOOD_ONLY"
    if usability == "STALE_DATA":
        return "STALE", "SOURCE_DATA_OLD"
    return "MISSING", "UNPROVEN"


def _band(value: float | None) -> str:
    if value is None:
        return "UNRANKED"
    if value >= 0.75:
        return "HIGH"
    if value >= 0.50:
        return "MEDIUM"
    return "LOW"


def _prepared_row(stock: StockEvidenceRecordV1) -> tuple[SelectionState, float | None, tuple[str, ...], str, str]:
    freshness, quality = _source_quality(stock)
    missing = list(stock.why_not_confirmed)
    priority = _priority(stock)
    state = stock.public_state
    if state is SelectionState.WATCH and (freshness != "CURRENT" or priority is None):
        state = SelectionState.WAIT
        missing.append("CURRENT_COMPLETE_CASH_FEATURES")
        priority = None
    if state is SelectionState.REJECT:
        priority = None
    return state, priority, tuple(dict.fromkeys(missing)), freshness, quality


def build_attention_order(
    bundle: InventorySourceBundleV1,
    *,
    expected_permission_fingerprint: str | None = None,
    shadow_comparison: dict[str, Any] | None = None,
    built_at: datetime | None = None,
) -> InventoryDiscoveryV1:
    if bundle.schema_version != "trendforge.inventory-source-bundle.v1":
        raise ValueError("WAIT_LINEAGE_INCOMPLETE: unsupported R1 bundle schema")
    if expected_permission_fingerprint is not None and bundle.permission_fingerprint != expected_permission_fingerprint:
        raise ValueError("WAIT_PERMISSION_MATRIX_MISMATCH")
    if not bundle.permission_fingerprint or not bundle.cash_pipeline_fingerprint:
        raise ValueError("WAIT_LINEAGE_INCOMPLETE")
    if bundle.stage_states.get("C1") != "COMPLETED":
        raise ValueError("WAIT_MIXED_SNAPSHOT_INPUTS: C1 is not completed")

    prepared: list[tuple[StockEvidenceRecordV1, SelectionState, float | None, tuple[str, ...], str, str]] = []
    for stock in bundle.stock_records:
        state, priority, missing, freshness, quality = _prepared_row(stock)
        prepared.append((stock, state, priority, missing, freshness, quality))

    watch = sorted(
        (item for item in prepared if item[1] is SelectionState.WATCH),
        key=lambda item: (-(item[2] if item[2] is not None else -1.0), item[0].symbol, item[0].candidate_id),
    )
    rank_by_candidate = {item[0].candidate_id: index for index, item in enumerate(watch, start=1)}
    ordered = sorted(
        prepared,
        key=lambda item: (
            0 if item[1] is SelectionState.WATCH else 1 if item[1] is SelectionState.WAIT else 2,
            -(item[2] if item[2] is not None else -1.0),
            item[0].symbol,
            item[0].candidate_id,
        ),
    )
    rows: list[AttentionRowV1] = []
    for display_order, (stock, state, priority, missing, freshness, quality) in enumerate(ordered, start=1):
        rows.append(
            AttentionRowV1(
                candidate_id=stock.candidate_id,
                symbol=stock.symbol,
                public_state=state,
                evidence_direction=stock.evidence_direction,
                display_order=display_order,
                attention_rank=rank_by_candidate.get(stock.candidate_id),
                attention_priority=priority,
                attention_band=_band(priority),
                supporting_families=("CASH_SESSION_ROOT",) if priority is not None else (),
                opposing_claims=stock.opposing_claims,
                missing_evidence=missing,
                conflicts=stock.opposing_claims,
                completeness=stock.completeness,
                freshness=freshness,
                source_quality=quality,
                restriction_state=stock.restriction_state,
                why_visible=stock.why_visible,
                why_not_confirmed=missing,
                lineage=stock.lineage,
                dataset_root_ids=stock.dataset_root_ids,
            )
        )

    identity = {
        "r1BundleId": bundle.bundle_id,
        "r1BundleHash": bundle.bundle_hash,
        "formulaId": FORMULA_ID,
        "formulaVersion": FORMULA_VERSION,
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
        "shadowComparison": shadow_comparison,
    }
    run_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    run_id = stable_id("r2-attention", bundle.bundle_id, run_hash)
    now = built_at or datetime.now(UTC)
    return InventoryDiscoveryV1(
        run_id=run_id,
        run_hash=run_hash,
        r1_bundle_id=bundle.bundle_id,
        r1_bundle_hash=bundle.bundle_hash,
        collector_run_id=bundle.collector_run_id,
        cash_pipeline_run_id=bundle.cash_pipeline_run_id,
        cash_pipeline_fingerprint=bundle.cash_pipeline_fingerprint,
        permission_fingerprint=bundle.permission_fingerprint,
        snapshot_bundle_id=bundle.snapshot_bundle_id,
        trading_date=bundle.trading_date.isoformat(),
        built_at=now,
        universe_count=len(rows),
        watch_count=sum(row.public_state is SelectionState.WATCH for row in rows),
        wait_count=sum(row.public_state is SelectionState.WAIT for row in rows),
        reject_count=sum(row.public_state is SelectionState.REJECT for row in rows),
        rows=tuple(rows),
        shadow_comparison=shadow_comparison,
        warnings=("Attention priority is ordinal research order, not evidence strength or win probability.",),
    )


def persist_attention_order(order: InventoryDiscoveryV1) -> InventoryDiscoveryV1:
    stored = order.model_copy(update={"persisted": True})
    payload = stored.model_dump(mode="json", by_alias=True)
    candidates = tuple(
        (
            row.candidate_id,
            row.symbol,
            row.public_state.value,
            row.model_dump(mode="json", by_alias=True),
        )
        for row in stored.rows
    )
    persist_selection_payload(
        run_id=stored.run_id,
        profile_id=PROFILE_ID,
        as_of=stored.built_at,
        payload=payload,
        candidates=candidates,
    )
    return stored


def latest_attention_order() -> InventoryDiscoveryV1 | None:
    payload = latest_selection_payload(PROFILE_ID)
    return InventoryDiscoveryV1.model_validate(payload) if payload is not None else None