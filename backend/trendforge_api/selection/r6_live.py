"""Live File A R6: shortlist-only enrichment stickers + top-10 research board.

This is NOT:
- A second ranker over R2 attention (`attention_order.py` owns the base;
  R6 adds stickers on a bounded shortlist and never re-adds volume)
- A per-stock FII tape (`nse_fii_dii` is market net; it can never say
  "FII bought {symbol}")
- A SHP FII-delta producer (no normalized FII%/prior-quarter parser exists,
  so `shpFiiDelta` stays null with `SHP_FII_DELTA_NOT_NORMALIZED`)
- CONFIRMED, quantity, broker action, Kelly, S4/S5, or R2-B activation

This IS:
- A bounded sticker pass (default top 40 WATCH rows) over the persisted spine
- Lineage-checked reads of R1/R2/R14 last-good batches (R5 optional)
- Gap from RAW A4 bars only when the R14 CA state is not WAIT_CA
- Named official large deals and delayed AMFI facts as capped display keys
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .. import storage
from ..fii_stock_signals import FIIStockSignalsSnapshot, build_fii_stock_signals
from .attention_order import InventoryDiscoveryV1, latest_attention_order
from .cash_a4_history import list_raw_bars
from .contracts import EvidenceDirection, SelectionState, StateCeiling, stable_id
from .fo_a6_enrichment import FoEnrichmentBatch, latest_fo_enrichment
from .inventory_source_bundle import InventorySourceBundleV1, latest_inventory_source_bundle
from .r14_live import latest_r14_ca_join
from .r5_live import R5StructureBatchV1, latest_r5_structure_batch
from .store import persist_selection_payload

SCHEMA_VERSION = "trendforge.r6-enrichment.v1"
PROFILE_ID = "PRF-R6-ENRICH-WAIT"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "RESEARCH_SHORTLIST_NOT_CONFIRMED"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

# Display-key bonuses. Sticker bonuses are capped in total so they can never
# dominate the R2 attention base. The cash-root gap bonus is small and capped.
GAP_ALIGNED_BONUS = 0.02
NAMED_DEAL_BONUS = 0.05
MF_DELAYED_BONUS = 0.04
STICKER_BONUS_CAP = 0.10

_BULLISH = {EvidenceDirection.BULLISH}
_BEARISH = {EvidenceDirection.BEARISH}


class R6EnrichRowV1(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    symbol: str
    r2_public_state: SelectionState
    evidence_direction: EvidenceDirection
    attention_priority: float | None = Field(default=None, ge=0.0, le=1.0)
    display_score: float | None = Field(default=None, ge=0.0, le=2.0)
    ca_state: str
    gap_pct: float | None = None
    gap_status: str
    delivery_status: str
    delivery_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    deal_summary: str | None = None
    deal_tag: str | None = None
    shp_fii_delta: None = None
    mf_delta: str | None = None
    mf_month: str | None = None
    fo_package: str
    restriction_state: str
    tags: tuple[str, ...] = ()
    why: tuple[str, ...] = ()
    why_unknown: tuple[str, ...] = ()
    research_state: SelectionState = SelectionState.WAIT

    @model_validator(mode="after")
    def r6_is_not_confirmation(self) -> "R6EnrichRowV1":
        if self.research_state is not SelectionState.WAIT:
            raise ValueError("R6 enrichment rows are ceiling WAIT")
        if self.shp_fii_delta is not None:
            raise ValueError("SHP FII delta has no normalized parser; must stay null")
        return self


class MarketFiiChipV1(BaseModel):
    model_config = MODEL_CONFIG

    data_date: str | None = None
    net_crore: float | None = None
    status: str
    scope: str = "MARKET_WIDE_NOT_PER_STOCK"


class R6EnrichmentBatchV1(BaseModel):
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
    r14_run_id: str | None = None
    trading_date: str
    built_at: datetime
    limit_watch: int = Field(gt=0)
    state_ceiling: StateCeiling = StateCeiling.WAIT
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    market_fii: MarketFiiChipV1
    universe_count: int = Field(ge=0)
    persisted: bool = False
    rows: tuple[R6EnrichRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def live_ceiling(self) -> "R6EnrichmentBatchV1":
        if self.universe_count != len(self.rows):
            raise ValueError("R6 universe count does not match rows")
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("R6 cannot activate sources or unlock CONFIRMED")
        if any(row.research_state is not SelectionState.WAIT for row in self.rows):
            raise ValueError("R6 rows are WAIT only")
        return self


# ---------------------------------------------------------------------------
# last-good helpers (same parser-state contract as fii_stock_signals)
# ---------------------------------------------------------------------------


def _usable(result: Any) -> tuple[dict[str, Any], str | None] | None:
    if result is None:
        return None
    if isinstance(result, dict):
        state = str(result.get("parserState") or "").upper()
        output = result.get("output")
        data_date = result.get("dataDate") or result.get("data_date")
    else:
        state = str(getattr(result, "parser_state", "") or "").upper()
        output = getattr(result, "output", None)
        data_date = getattr(result, "data_date", None)
    if state not in {"PARSED", "PARSED_STRUCTURED", "PARSED_ADAPTER"}:
        return None
    if not isinstance(output, dict):
        return None
    return output, str(data_date) if data_date else None


def _rows(output: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("rows", "records", "deals"):
        value = output.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _float(row: dict[str, Any], *aliases: str) -> float | None:
    normalized = {
        "".join(ch for ch in str(key).lower() if ch.isalnum()): value
        for key, value in row.items()
    }
    for alias in aliases:
        key = "".join(ch for ch in alias.lower() if ch.isalnum())
        value = normalized.get(key)
        if value in (None, ""):
            continue
        try:
            return float(str(value).replace(",", "").replace("%", "").strip())
        except (TypeError, ValueError):
            continue
    return None


def _text(row: dict[str, Any], *aliases: str) -> str | None:
    normalized = {
        "".join(ch for ch in str(key).lower() if ch.isalnum()): value
        for key, value in row.items()
    }
    for alias in aliases:
        key = "".join(ch for ch in alias.lower() if ch.isalnum())
        value = normalized.get(key)
        if value in (None, ""):
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _load_market_fii(loader) -> MarketFiiChipV1:
    """Market-level FII net chip. Never a per-stock fact."""
    usable = _usable(loader("nse_fii_dii")) if callable(loader) else None
    if usable is None:
        return MarketFiiChipV1(status="UNKNOWN_MISSING_SOURCE")
    output, data_date = usable
    by_date: dict[str, float] = {}
    for row in _rows(output):
        category = (_text(row, "category") or "").upper()
        if "FII" not in category and "FPI" not in category:
            continue
        net = _float(
            row,
            "netValueCrore",
            "netValue",
            "net_value",
        )
        if net is None:
            buy = _float(row, "buyValueCrore", "buyValue", "buy_value")
            sell = _float(row, "sellValueCrore", "sellValue", "sell_value")
            if buy is None or sell is None:
                continue
            net = buy - sell
        date_key = _text(row, "date") or data_date or ""
        try:
            by_date[date_key] = by_date.get(date_key, 0.0) + net
        except TypeError:
            continue
    if not by_date:
        return MarketFiiChipV1(data_date=data_date or None, status="NO_FII_ROWS")
    latest_date = max(by_date)
    return MarketFiiChipV1(
        data_date=latest_date or None,
        net_crore=round(by_date[latest_date], 2),
        status="CURRENT",
    )


def _load_delivery_map(loader) -> dict[str, float]:
    usable = _usable(loader("nse_mto_delivery")) if callable(loader) else None
    if usable is None:
        return {}
    delivery: dict[str, float] = {}
    for row in _rows(usable[0]):
        symbol = (_text(row, "symbol") or "").upper()
        pct = _float(row, "delivery_pct", "deliveryPct", "deliveryPercentage")
        if symbol and pct is not None and 0 <= pct <= 100:
            # EQ series wins over duplicate non-EQ rows for the same symbol.
            series = (_text(row, "series") or "").upper()
            if symbol in delivery and series != "EQ":
                continue
            delivery[symbol] = pct
    return delivery


def _load_amfi_map() -> dict[str, dict[str, Any]]:
    storage.init_db()
    conn = storage.connect()
    try:
        rows = conn.execute(
            """
            SELECT disclosure_month, stock, schemes_added, schemes_reduced,
                   net_quantity_change
            FROM amfi_stock_deltas
            ORDER BY stock, disclosure_month
            """
        ).fetchall()
    finally:
        conn.close()
    deltas: dict[str, dict[str, Any]] = {}
    for row in rows:
        deltas[str(row["stock"]).upper()] = {
            "month": row["disclosure_month"],
            "schemes_added": int(row["schemes_added"] or 0),
            "schemes_reduced": int(row["schemes_reduced"] or 0),
            "net_quantity_change": int(row["net_quantity_change"] or 0),
        }
    return deltas


# ---------------------------------------------------------------------------
# sticker computation
# ---------------------------------------------------------------------------


def _gap_sticker(symbol: str, trading_date, ca_state: str) -> tuple[float | None, str, str | None]:
    """Gap from RAW bars; gated by the R14 CA state."""
    if ca_state == "WAIT_CA":
        return None, "UNKNOWN_WAIT_CA", "GAP_UNKNOWN_WAIT_CA"
    bars = list_raw_bars(symbol, through=trading_date)
    recent = [bar for bar in bars if bar.open is not None and bar.close is not None]
    if len(recent) < 2:
        return None, "UNKNOWN_BARS_MISSING", "GAP_BARS_MISSING"
    current, previous = recent[-1], recent[-2]
    if current.trade_date == previous.trade_date or not previous.close:
        return None, "UNKNOWN_BARS_MISSING", "GAP_BARS_MISSING"
    gap = (float(current.open) - float(previous.close)) / float(previous.close)
    return round(gap * 100.0, 4), "CURRENT_ADJUSTED_SAFE", None


def _deal_sticker(
    deals: list[Any], direction: EvidenceDirection
) -> tuple[str | None, str | None, bool]:
    """Latest named-deal summary. Tag fires only when the side aligns."""
    if not deals:
        return None, None, False
    latest = max(deals, key=lambda item: item.date)
    client = (latest.client or "").strip()
    if client:
        summary = (
            f"{latest.date} {latest.deal_type} "
            f"{'BUY' if latest.side == 'BUY' else 'SELL' if latest.side == 'SELL' else 'SIDE?'}"
            f" qty={latest.quantity or '?'} client={client}"
        )
    else:
        summary = f"{latest.date} {latest.deal_type} UNNAMED_DEAL"
    upper = client.upper()
    base_tag = None
    if client and ("FII" in upper or "FPI" in upper):
        base_tag = "NAMED_FII_LIKE_DEAL"
    elif client:
        base_tag = "NAMED_DEAL"
    aligned = bool(base_tag and latest.side and (
        (latest.side == "BUY" and direction in _BULLISH)
        or (latest.side == "SELL" and direction in _BEARISH)
    ))
    return summary, (base_tag if aligned else None), aligned


def _mf_sticker(
    amfi: dict[str, dict[str, Any]] | None, symbol: str, direction: EvidenceDirection
) -> tuple[str | None, str | None, str | None, bool]:
    entry = (amfi or {}).get(symbol.upper())
    if not entry:
        return None, None, "MF_UNKNOWN_NO_AMFI_ROW", False
    net_qty = entry["net_quantity_change"]
    added = entry["schemes_added"]
    reduced = entry["schemes_reduced"]
    if net_qty > 0 or (added > reduced and net_qty >= 0):
        delta = "NET_ADDED"
    elif net_qty < 0 or (reduced > added):
        delta = "NET_REDUCED"
    else:
        delta = "FLAT"
    aligned = (delta == "NET_ADDED" and direction in _BULLISH) or (
        delta == "NET_REDUCED" and direction in _BEARISH
    )
    return f"{delta}_{entry['month']}", entry["month"], None, aligned


# ---------------------------------------------------------------------------
# builder
# ---------------------------------------------------------------------------


def build_r6_enrichment(
    *,
    limit_watch: int = 40,
    bundle: InventorySourceBundleV1 | None = None,
    attention: InventoryDiscoveryV1 | None = None,
    r14: Any | None = None,
    r5: R5StructureBatchV1 | None = None,
    fo: FoEnrichmentBatch | None = None,
    signals: FIIStockSignalsSnapshot | None = None,
    loader: Any = None,
    built_at: datetime | None = None,
) -> R6EnrichmentBatchV1:
    r1 = bundle or latest_inventory_source_bundle()
    r2 = attention or latest_attention_order()
    if r1 is None or r2 is None:
        raise ValueError("WAIT_R6_SPINE_NOT_READY")
    if r2.r1_bundle_id != r1.bundle_id or r2.r1_bundle_hash != r1.bundle_hash:
        raise ValueError("WAIT_R6_LINEAGE_MISMATCH")
    batch_14 = r14 if r14 is not None else latest_r14_ca_join()
    if batch_14 is None:
        raise ValueError("WAIT_R6_SPINE_NOT_READY")
    if batch_14.r2_run_id != r2.run_id or batch_14.r2_run_hash != r2.run_hash:
        raise ValueError("WAIT_R6_LINEAGE_MISMATCH")

    batch_5 = r5 if r5 is not None else latest_r5_structure_batch()
    warnings: list[str] = []
    r5_setups: dict[str, tuple[str, ...]] = {}
    if batch_5 is not None:
        if (
            batch_5.r1_bundle_id == r1.bundle_id
            and batch_5.r1_bundle_hash == r1.bundle_hash
            and batch_5.r2_run_id == r2.run_id
            and batch_5.r2_run_hash == r2.run_hash
        ):
            r5_setups = {
                row.candidate_id: row.detected_setups for row in batch_5.rows
            }
        else:
            warnings.append("R5_LINEAGE_SKIPPED")

    fo_batch = fo if fo is not None else latest_fo_enrichment()
    fo_symbols = {row.symbol.upper() for row in fo_batch.rows} if fo_batch else set()

    if signals is not None:
        snapshot = signals
    elif loader is not None:
        snapshot = build_fii_stock_signals(loader=loader)
    else:
        snapshot = build_fii_stock_signals()
    deals_by_symbol: dict[str, list[Any]] = {}
    for deal in snapshot.large_deals:
        deals_by_symbol.setdefault(deal.symbol.upper(), []).append(deal)

    # When no loader is supplied (tests, or scheduler absent), market FII and
    # delivery degrade to UNKNOWN_MISSING_SOURCE; large-deal signals still use
    # the fii_stock_signals default storage loader.
    effective_loader = loader if callable(loader) else None
    market_fii = _load_market_fii(effective_loader)
    delivery_map = _load_delivery_map(effective_loader)
    amfi_map = _load_amfi_map()

    watch_rows = sorted(
        (row for row in r2.rows if row.public_state is SelectionState.WATCH),
        key=lambda row: (
            -(row.attention_priority if row.attention_priority is not None else -1.0),
            row.symbol,
            row.candidate_id,
        ),
    )[:limit_watch]

    r14_by_candidate = {row.candidate_id: row for row in batch_14.rows}
    enriched: list[R6EnrichRowV1] = []
    for item in watch_rows:
        ca_row = r14_by_candidate.get(item.candidate_id)
        ca_state = ca_row.ca_state if ca_row is not None else "WAIT_CA"
        why_unknown: list[str] = ["SHP_FII_DELTA_NOT_NORMALIZED"]
        tags: list[str] = []
        bonus = 0.0

        gap_pct, gap_status, gap_unknown = _gap_sticker(
            item.symbol.upper(), r1.trading_date, ca_state
        )
        if gap_unknown:
            why_unknown.append(gap_unknown)
        if gap_status == "CURRENT_ADJUSTED_SAFE" and gap_pct is not None:
            aligned_gap = (
                (gap_pct > 0 and item.evidence_direction in _BULLISH)
                or (gap_pct < 0 and item.evidence_direction in _BEARISH)
            )
            if aligned_gap:
                tags.append("GAP_ALIGNED")
                bonus += GAP_ALIGNED_BONUS

        delivery_pct = delivery_map.get(item.symbol.upper())
        if delivery_pct is None:
            delivery_status = "UNKNOWN_MISSING_SOURCE"
            why_unknown.append("DELIVERY_SOURCE_MISSING")
        else:
            delivery_status = "CURRENT_PCT_FACT"

        deal_summary, deal_tag, _aligned = _deal_sticker(
            deals_by_symbol.get(item.symbol.upper(), []), item.evidence_direction
        )
        if deal_tag:
            tags.append(deal_tag)
            bonus += NAMED_DEAL_BONUS
        elif deal_summary is None:
            why_unknown.append("NO_LARGE_DEAL_ROW")

        mf_delta, mf_month, mf_unknown, mf_aligned = _mf_sticker(
            amfi_map, item.symbol, item.evidence_direction
        )
        if mf_unknown:
            why_unknown.append(mf_unknown)
        if mf_aligned:
            tags.append("MF_DELAYED")
            bonus += MF_DELAYED_BONUS

        fo_package = (
            "AVAILABLE" if item.symbol.upper() in fo_symbols else "NOT_IN_A6_SHORTLIST"
        )

        why = ["R2_ATTENTION_BASE"]
        setups = r5_setups.get(item.candidate_id) or ()
        for setup in setups:
            why.append(f"R5_SETUP_{setup}")

        display_score = (
            round(
                (item.attention_priority or 0.0)
                + min(STICKER_BONUS_CAP, bonus),
                6,
            )
            if item.attention_priority is not None
            else None
        )
        enriched.append(
            R6EnrichRowV1(
                candidate_id=item.candidate_id,
                symbol=item.symbol,
                r2_public_state=item.public_state,
                evidence_direction=item.evidence_direction,
                attention_priority=item.attention_priority,
                display_score=display_score,
                ca_state=ca_state,
                gap_pct=gap_pct,
                gap_status=gap_status,
                delivery_status=delivery_status,
                delivery_pct=delivery_pct,
                deal_summary=deal_summary,
                deal_tag=deal_tag,
                shp_fii_delta=None,
                mf_delta=mf_delta,
                mf_month=mf_month,
                fo_package=fo_package,
                restriction_state=item.restriction_state,
                tags=tuple(tags),
                why=tuple(dict.fromkeys(why)),
                why_unknown=tuple(dict.fromkeys(why_unknown)),
            )
        )

    identity = {
        "r1BundleHash": r1.bundle_hash,
        "r2RunHash": r2.run_hash,
        "r14RunId": batch_14.run_id,
        "limitWatch": limit_watch,
        "marketFii": market_fii.model_dump(mode="json", by_alias=True),
        "rows": [row.model_dump(mode="json", by_alias=True) for row in enriched],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    now = built_at or datetime.now(UTC)
    return R6EnrichmentBatchV1(
        run_id=stable_id("r6-enrich", r1.bundle_id, r2.run_id, run_hash),
        run_hash=run_hash,
        r1_bundle_id=r1.bundle_id,
        r1_bundle_hash=r1.bundle_hash,
        r2_run_id=r2.run_id,
        r2_run_hash=r2.run_hash,
        r14_run_id=batch_14.run_id,
        trading_date=r1.trading_date.isoformat(),
        built_at=now,
        limit_watch=limit_watch,
        market_fii=market_fii,
        universe_count=len(enriched),
        rows=tuple(enriched),
        warnings=tuple(
            warnings
            + [
                "R6 stickers are research display keys, not confirmation, "
                "probability, or trade authority.",
                "shpFiiDelta stays null: no normalized FII% prior-quarter "
                "parser exists.",
            ]
        ),
    )


def persist_r6_enrichment(value: R6EnrichmentBatchV1) -> R6EnrichmentBatchV1:
    stored = value.model_copy(update={"persisted": True})
    persist_selection_payload(
        run_id=stored.run_id,
        profile_id=PROFILE_ID,
        as_of=stored.built_at,
        payload=stored.model_dump(mode="json", by_alias=True),
        candidates=tuple(
            (
                row.candidate_id,
                row.symbol,
                row.research_state.value,
                row.model_dump(mode="json", by_alias=True),
            )
            for row in stored.rows
        ),
    )
    return stored


__all__ = [
    "ACCEPTANCE_CEILING",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "MarketFiiChipV1",
    "R6EnrichmentBatchV1",
    "R6EnrichRowV1",
    "build_r6_enrichment",
    "persist_r6_enrichment",
]
