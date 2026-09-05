"""File A S5 (SEL-006): bounded shortlist enrichment over S4 structure claims.

This stage is NOT:
- An all-universe expensive loop. Input is the S4 structure-claimed shortlist
  (>=1 CG_PRICE_STRUCTURE / CG_COMPRESSION representative). Fallback (S4 pack
  missing) is R2 WATCH intersect latest R5 detected_setups, never bare
  WATCH-40 and never all-universe MTO/FO/options.
- Per-stock FII tape: `nse_fii_dii` stays a board-level chip
  (MARKET_WIDE_NOT_PER_STOCK). Unnamed deals are never labelled FII.
- Options intelligence: one OPTIONS_PACKAGE family field; without a fresh
  expiry-scoped chain contract it stays UNKNOWN_NEEDS_R12 with score 0, so a
  cash-only name is never punished.
- CONFIRMED, quantity or source activation. Ceiling LIVE_S5_ENRICH_WAIT_ONLY.

Delivery is EOD-only (FTR-019); on INTRADAY horizons the field is forbidden,
not zero. SHP FII delta has no normalized parser and stays null. AMFI deltas
are delayed months, never "bought today".
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .attention_order import InventoryDiscoveryV1
from .contracts import SelectionState, StateCeiling, stable_id
from .evidence_radar.calculate import (
    FactDirection,
    amfi_fact,
    fo_package_fact,
    named_deal_fact,
    options_fact,
    shp_context_fact,
)
from .evidence_radar.loads import MIN_DELIVERY_SESSIONS, robust_delivery_z
from .fo_a6_enrichment import FoEnrichmentBatch, latest_fo_enrichment
from .r5_live import R5StructureBatchV1, latest_r5_structure_batch
from .r6_live import _load_amfi_map, _load_delivery_map, _load_market_fii
from .s4_structure_pack import S4StructurePackBatchV1, build_s4_structure_pack

SCHEMA_VERSION = "trendforge.s5-enrichment.v1"
PROFILE_ID = "PRF-S5-ENRICH-WAIT"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_S5_ENRICH_WAIT_ONLY"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class S5DeliveryFieldV1(BaseModel):
    model_config = MODEL_CONFIG

    status: str
    z: float | None = None
    pct: float | None = None
    sessions: int = Field(default=0, ge=0)
    horizon_guard: Literal["EOD_ONLY"] = "EOD_ONLY"
    why: str


class S5FoPackageV1(BaseModel):
    model_config = MODEL_CONFIG

    status: str
    quadrant: str | None = None
    oi_change: int | None = None
    can_support_confirmed: Literal[False] = False
    why: str


class S5OptionsPackageV1(BaseModel):
    model_config = MODEL_CONFIG

    status: Literal[
        "SUPPORT", "WEAKEN", "CONFLICT", "UNKNOWN", "UNKNOWN_NEEDS_R12"
    ] = "UNKNOWN_NEEDS_R12"
    can_support_confirmed: Literal[False] = False
    score_contribution: Literal[0] = 0
    why: str


class S5DealFieldV1(BaseModel):
    model_config = MODEL_CONFIG

    code: str
    is_fii_claim: bool = False
    direction: str | None = None
    why: str


class S5DelayedMfV1(BaseModel):
    model_config = MODEL_CONFIG

    code: str
    month: str | None = None
    net_quantity_change: float | None = None
    delayed: Literal[True] = True
    why: str


class S5ShpContextV1(BaseModel):
    model_config = MODEL_CONFIG

    promoter_pct: float | None = None
    public_pct: float | None = None
    fii_delta: None = None
    why: str


class S5EnrichmentRowV1(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    symbol: str
    structure_claim_groups: tuple[str, ...]
    delivery: S5DeliveryFieldV1
    fo_package: S5FoPackageV1
    options_package: S5OptionsPackageV1
    named_deal: S5DealFieldV1
    delayed_mf: S5DelayedMfV1 | None = None
    shp_context: S5ShpContextV1
    mcx_note: str | None = None
    why_unknown: tuple[str, ...] = ()
    research_state: SelectionState = SelectionState.WAIT
    can_unlock_confirmed: bool = False

    @model_validator(mode="after")
    def enforce_s5_ceiling(self) -> "S5EnrichmentRowV1":
        if self.research_state is not SelectionState.WAIT:
            raise ValueError("S5 enrichment rows are ceiling WAIT")
        if self.can_unlock_confirmed:
            raise ValueError("S5 cannot unlock CONFIRMED")
        return self


class MarketFiiChipProjectionV1(BaseModel):
    model_config = MODEL_CONFIG

    data_date: str | None = None
    net_crore: float | None = None
    status: str
    scope: Literal["MARKET_WIDE_NOT_PER_STOCK"] = "MARKET_WIDE_NOT_PER_STOCK"


class S5EnrichmentBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    run_id: str
    run_hash: str
    r1_bundle_hash: str
    r2_run_hash: str
    r14_run_hash: str | None = None
    trading_date: str
    built_at: datetime
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    state_ceiling: StateCeiling = StateCeiling.WAIT
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    confirmed_count: int = 0
    shortlist_source: Literal[
        "S4_STRUCTURE_CLAIMS", "R2_WATCH_INTERSECT_R5_SETUPS"
    ]
    shortlist_count: int = Field(ge=0)
    universe_count: int = Field(ge=0)
    market_fii: MarketFiiChipProjectionV1
    rows: tuple[S5EnrichmentRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_batch(self) -> "S5EnrichmentBatchV1":
        if self.universe_count != len(self.rows):
            raise ValueError("S5 universe count does not match rows")
        if self.universe_count > self.shortlist_count:
            raise ValueError("S5 enrichment cannot exceed its shortlist")
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("S5 cannot activate sources or unlock CONFIRMED")
        if any(row.research_state is not SelectionState.WAIT for row in self.rows):
            raise ValueError("S5 rows are WAIT only")
        return self


def _direction_name(direction: FactDirection) -> str | None:
    if direction in {FactDirection.BULLISH, FactDirection.BEARISH}:
        return direction.value
    return None


def _delivery_field(
    *,
    horizon: str,
    history: list[float] | None,
    fallback_pct: float | None,
) -> S5DeliveryFieldV1:
    """EOD-only delivery. INTRADAY never carries the field."""
    if horizon == "INTRADAY":
        return S5DeliveryFieldV1(
            status="FORBIDDEN_ON_INTRADAY",
            why="Delivery evidence is forbidden on the intraday horizon.",
        )
    series = history or []
    if len(series) >= MIN_DELIVERY_SESSIONS:
        z, median_pct = robust_delivery_z(series)
        if z is not None:
            return S5DeliveryFieldV1(
                status="DELIVERY_Z_PIT20",
                z=round(z, 4),
                pct=round(series[-1], 4),
                sessions=len(series),
                why=(
                    f"{len(series)} PIT MTO sessions; median={median_pct:.2f}. "
                    "Quality number, not a buy/sell vote."
                ),
            )
        return S5DeliveryFieldV1(
            status="CURRENT_PCT_Z_UNKNOWN_MAD0",
            pct=round(series[-1], 4),
            sessions=len(series),
            why=f"{len(series)} MTO sessions but MAD=0 so z is UNKNOWN.",
        )
    if fallback_pct is not None:
        return S5DeliveryFieldV1(
            status="CURRENT_PCT_NO_Z_HISTORY",
            pct=round(fallback_pct, 4),
            sessions=len(series),
            why=(
                f"Only today's MTO pct ({fallback_pct:.2f}); fewer than "
                f"{MIN_DELIVERY_SESSIONS} PIT sessions so no z."
            ),
        )
    return S5DeliveryFieldV1(
        status="UNKNOWN_MISSING_SOURCE",
        sessions=len(series),
        why="No usable nse_mto_delivery last-good for this symbol.",
    )


def _fo_field(
    symbol: str,
    fo_symbols: set[str],
    quadrants: dict[str, str],
    oi_changes: dict[str, int] | None,
    fo_available: bool,
) -> S5FoPackageV1:
    if not fo_available:
        return S5FoPackageV1(
            status="UNKNOWN_MISSING_SOURCE",
            why="A6 futures enrichment batch unavailable; cash-only is not punished.",
        )
    fact = fo_package_fact(symbol, fo_symbols, quadrants, oi_changes)
    key = symbol.upper()
    return S5FoPackageV1(
        status=fact.code,
        quadrant=quadrants.get(key) if fact.ok else None,
        oi_change=(oi_changes or {}).get(key) if fact.ok else None,
        why=fact.why,
    )


def _options_field() -> S5OptionsPackageV1:
    fact = options_fact()
    return S5OptionsPackageV1(status="UNKNOWN_NEEDS_R12", why=fact.why)


def _deal_field(deals: list[Any], symbol: str) -> S5DealFieldV1:
    fact = named_deal_fact(symbol, deals)
    return S5DealFieldV1(
        code=fact.code,
        is_fii_claim=False,
        direction=_direction_name(fact.direction),
        why=fact.why,
    )


def _mf_field(amfi_map: dict[str, dict[str, Any]], symbol: str) -> S5DelayedMfV1 | None:
    fact = amfi_fact(symbol, amfi_map)
    if not fact.ok:
        return None
    entry = amfi_map.get(symbol.upper()) or {}
    return S5DelayedMfV1(
        code=fact.code,
        month=str(entry.get("month")) if entry.get("month") else None,
        net_quantity_change=float(entry.get("net_quantity_change") or 0),
        why=fact.why,
    )


def _shp_field(shp_rows: list[dict[str, Any]] | None, symbol: str) -> S5ShpContextV1:
    fact = shp_context_fact(symbol, shp_rows)
    row = next(
        (
            item
            for item in (shp_rows or [])
            if str(item.get("symbol") or "").upper() == symbol.upper()
        ),
        None,
    )
    promoter = row.get("promoter_holding_pct") if isinstance(row, dict) else None
    public = row.get("public_holding_pct") if isinstance(row, dict) else None
    return S5ShpContextV1(promoter_pct=promoter, public_pct=public, why=fact.why)


def _shortlist_entries_from_pack(
    pack: S4StructurePackBatchV1,
) -> list[tuple[str, str, tuple[str, ...]]]:
    entries: list[tuple[str, str, tuple[str, ...]]] = []
    for row in pack.rows:
        groups = tuple(
            tag.correlation_group
            for tag in row.setup_tags
            if tag.correlation_group in {"CG_PRICE_STRUCTURE", "CG_COMPRESSION"}
        )
        if not groups:
            continue
        entries.append((row.candidate_id, row.symbol, groups))
    return entries


def _fallback_entries(
    attention: InventoryDiscoveryV1 | None,
    batch5: R5StructureBatchV1,
    limit: int,
) -> list[tuple[str, str, tuple[str, ...]]]:
    """R2 WATCH intersect latest R5 detected_setups. Never bare WATCH-40."""
    if attention is None:
        raise ValueError("WAIT_S5_FALLBACK_NEEDS_R2_WATCH")
    setups_by_symbol = {
        row.symbol: row.detected_setups for row in batch5.rows if row.detected_setups
    }
    candidate_by_symbol = {
        row.symbol: row.candidate_id
        for row in attention.rows
        if row.public_state is SelectionState.WATCH
    }
    return [
        (candidate_by_symbol[symbol], symbol, ("CG_PRICE_STRUCTURE",))
        for symbol in sorted(set(candidate_by_symbol) & set(setups_by_symbol))
    ][:limit]


def build_s5_enrichment(
    *,
    s4: S4StructurePackBatchV1 | None = None,
    r5: R5StructureBatchV1 | None = None,
    attention: InventoryDiscoveryV1 | None = None,
    loader: Any = None,
    signals: Any = None,
    fo: FoEnrichmentBatch | None = None,
    delivery_history: dict[str, list[float]] | None = None,
    shp_rows: list[dict[str, Any]] | None = None,
    horizon: str = "SWING",
    limit: int = 200,
    built_at: datetime | None = None,
) -> S5EnrichmentBatchV1:
    """Enrich ONLY the structure-claimed shortlist with typed honest fields."""
    from ..fii_stock_signals import build_fii_stock_signals

    shortlist_source: str = "S4_STRUCTURE_CLAIMS"
    pack: S4StructurePackBatchV1 | None = s4
    if pack is not None:
        entries = _shortlist_entries_from_pack(pack)
    else:
        batch5 = r5 if r5 is not None else latest_r5_structure_batch()
        if batch5 is None:
            raise ValueError("WAIT_S5_SHORTLIST_NOT_READY")
        entries = _fallback_entries(attention, batch5, limit)
        shortlist_source = "R2_WATCH_INTERSECT_R5_SETUPS"
        pack = build_s4_structure_pack(r5=batch5)
    entries = entries[:limit]

    effective_loader = loader if callable(loader) else None
    market_fii = _load_market_fii(effective_loader)
    delivery_map = _load_delivery_map(effective_loader)
    amfi_map = _load_amfi_map()
    fo_batch = fo if fo is not None else latest_fo_enrichment()
    fo_available = fo_batch is not None
    fo_symbols = {row.symbol.upper() for row in fo_batch.rows} if fo_batch else set()
    quadrants = (
        {
            row.symbol.upper(): (
                row.near_future.oi_quadrant if row.near_future is not None else None
            )
            for row in fo_batch.rows
        }
        if fo_batch
        else {}
    )
    oi_changes = (
        {
            row.symbol.upper(): int(
                (row.near_future.oi_change if row.near_future is not None else 0) or 0
            )
            for row in fo_batch.rows
        }
        if fo_batch
        else {}
    )

    snapshot = signals
    if snapshot is None:
        snapshot = (
            build_fii_stock_signals(loader=effective_loader)
            if effective_loader is not None
            else build_fii_stock_signals()
        )
    deals = getattr(snapshot, "large_deals", []) or []

    history = delivery_history if delivery_history is not None else {}

    rows: list[S5EnrichmentRowV1] = []
    for candidate_id, symbol, groups in entries:
        key = symbol.upper()
        deal_field = _deal_field(deals, symbol)
        mf_field = _mf_field(amfi_map, symbol)
        shp_field = _shp_field(shp_rows, symbol)
        delivery_field = _delivery_field(
            horizon=horizon,
            history=history.get(key),
            fallback_pct=delivery_map.get(key),
        )
        fo_field = _fo_field(symbol, fo_symbols, quadrants, oi_changes, fo_available)
        why_unknown: list[str] = ["SHP_FII_DELTA_NOT_NORMALIZED"]
        if delivery_field.status.startswith("UNKNOWN"):
            why_unknown.append(f"DELIVERY_{delivery_field.status}")
        if mf_field is None:
            why_unknown.append("MF_UNKNOWN_NO_AMFI_ROW")
        if fo_field.status != "FO_OI_PACKAGE_NEUTRAL_OR_UNKNOWN" and not fo_field.quadrant:
            why_unknown.append(fo_field.status)
        rows.append(
            S5EnrichmentRowV1(
                candidate_id=candidate_id or f"s4-{key}",
                symbol=key,
                structure_claim_groups=tuple(dict.fromkeys(groups)),
                delivery=delivery_field,
                fo_package=fo_field,
                options_package=_options_field(),
                named_deal=deal_field,
                delayed_mf=mf_field,
                shp_context=shp_field,
                why_unknown=tuple(dict.fromkeys(why_unknown)),
            )
        )

    identity = {
        "s4RunHash": pack.run_hash,
        "profileVersion": PROFILE_VERSION,
        "shortlistSource": shortlist_source,
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    now = built_at or datetime.now(UTC)
    return S5EnrichmentBatchV1(
        run_id=stable_id("s5-enrich", pack.r1_bundle_hash, pack.r2_run_hash, run_hash),
        run_hash=run_hash,
        r1_bundle_hash=pack.r1_bundle_hash,
        r2_run_hash=pack.r2_run_hash,
        r14_run_hash=pack.r14_run_hash,
        trading_date=pack.trading_date,
        built_at=now,
        shortlist_source=shortlist_source,
        shortlist_count=len(entries),
        universe_count=len(rows),
        market_fii=MarketFiiChipProjectionV1(
            data_date=market_fii.data_date,
            net_crore=market_fii.net_crore,
            status=market_fii.status,
        ),
        rows=tuple(rows),
        warnings=(
            "S5 enrichment is display research on a bounded shortlist; "
            "missing FO/options never penalizes a cash-only name.",
            "OPTIONS_PACKAGE stays UNKNOWN_NEEDS_R12 until a fresh "
            "expiry-scoped chain contract is proven.",
        ),
    )


__all__ = [
    "ACCEPTANCE_CEILING",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "MarketFiiChipProjectionV1",
    "S5DelayedMfV1",
    "S5DealFieldV1",
    "S5DeliveryFieldV1",
    "S5EnrichmentBatchV1",
    "S5EnrichmentRowV1",
    "S5FoPackageV1",
    "S5OptionsPackageV1",
    "S5ShpContextV1",
    "build_s5_enrichment",
]
