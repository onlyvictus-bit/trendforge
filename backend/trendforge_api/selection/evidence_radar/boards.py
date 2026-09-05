"""Evidence radar orchestrator: Stage A coverage + Stage B fuse + boards.

Public state stays WATCH / WAIT / REJECT. 0 CONFIRMED. qty=0.
Boards are research display ranks, never File A public_state.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ...fii_stock_signals import FIIStockSignalsSnapshot, build_fii_stock_signals
from .calculate import (
    CalculatedFact,
    activity_join_fact,
    amfi_fact,
    delivery_fact,
    fo_package_fact,
    gap_fact,
    market_fii_chip_fact,
    mcx_dte_days,
    named_deal_fact,
    official_event_fact,
    options_fact,
    preopen_gap_fact,
    r5_setup_fact,
    rs_fact,
    shp_context_fact,
)
from .catalog import build_slot_catalog
from .explain import build_explain
from .fuse import fuse_instrument
from ..inventory_source_bundle import InventorySourceBundleV1
from .slots import CoverageReportV1, fill_slots

SCHEMA_VERSION = "trendforge.evidence-radar.v1"
PROFILE_ID = "PRF-EVIDENCE-RADAR-WAIT"
CALIBRATION = "RESEARCH_RADAR_NOT_CONFIRMED"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)
BOARD_SIZE = 10
DEFAULT_LIMIT_WATCH = 200

_DATA_MODE = {
    "INTRADAY": "DATA_MODE_EOD_OR_UNVERIFIED",
    "SWING": "EOD_RESEARCH",
    "POSITION": "EOD_RESEARCH_DELAYED_OK",
    "COMMODITY": "LOCAL_MCX_REQUIRED",
}

_CASH_HORIZONS = ("INTRADAY", "SWING", "POSITION")


def _load_mcx_local_rows() -> list[dict[str, Any]]:
    """Latest official MCX bhav last-good, one nearest-expiry row per symbol."""
    from ... import storage

    storage.init_db()
    conn = storage.connect()
    try:
        dates = [
            row[0]
            for row in conn.execute(
                """
                SELECT DISTINCT data_date FROM mcx_bhavcopy_daily
                WHERE close_price IS NOT NULL
                ORDER BY data_date DESC
                LIMIT 2
                """
            ).fetchall()
        ]
        if not dates:
            return []
        latest = dates[0]
        prior = dates[1] if len(dates) > 1 else None
        latest_rows = conn.execute(
            """
            SELECT symbol, expiry, close_price, oi_change
            FROM mcx_bhavcopy_daily
            WHERE data_date = ? AND close_price IS NOT NULL
            """,
            (latest,),
        ).fetchall()
        prior_map: dict[tuple[str, str | None], float] = {}
        if prior:
            for row in conn.execute(
                """
                SELECT symbol, expiry, close_price
                FROM mcx_bhavcopy_daily
                WHERE data_date = ? AND close_price IS NOT NULL
                """,
                (prior,),
            ).fetchall():
                prior_map[(str(row[0]), row[1])] = float(row[2])
        by_symbol: dict[str, dict[str, Any]] = {}
        for symbol, expiry, close, oi_change in latest_rows:
            key = str(symbol).upper()
            current = by_symbol.get(key)
            if current is None or (expiry or "") < (current.get("expiry") or "9999"):
                by_symbol[key] = {
                    "symbol": key,
                    "expiry": expiry,
                    "close": float(close),
                    "priorClose": prior_map.get((str(symbol), expiry)),
                    "oiChange": oi_change,
                    "instrumentId": None,
                }
        return list(by_symbol.values())
    finally:
        conn.close()


class FamilySlotV1(BaseModel):
    model_config = MODEL_CONFIG

    status: str
    direction: str
    representative_claim_id: str | None = None
    why: str


class RadarRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    instrument_id: str | None
    market: str
    horizon: str
    publicState: str
    researchBoard: str  # BUY | SELL | NONE
    displayRank: int | None = Field(default=None, gt=0)
    displayRankKey: float | None = None
    families: dict[str, FamilySlotV1]
    slotsSkippedCount: int = 0
    unknownCount: int = Field(ge=0)
    how: str
    what: str
    where: str
    when: str
    why: tuple[str, ...] = ()
    whyUnknown: tuple[str, ...] = ()
    nextConfirmCondition: str
    invalidationCondition: str
    whatChanged: str = "NO_BASELINE"
    freshness: str
    completeness: float = Field(ge=0.0, le=1.0)
    dataMode: str
    canUnlockConfirmed: bool = False
    sourceActivationReady: bool = False
    calibration: str = CALIBRATION

    @model_validator(mode="after")
    def radar_is_not_confirmation(self) -> "RadarRowV1":
        if self.publicState in {"CONFIRMED"}:
            raise ValueError("evidence radar cannot emit CONFIRMED")
        if self.researchBoard not in {"BUY", "SELL", "NONE"}:
            raise ValueError("researchBoard must be BUY, SELL, or NONE")
        if self.slotsSkippedCount != 0:
            raise ValueError("a radar row may never skip a slot; use unknowns")
        if self.canUnlockConfirmed or self.sourceActivationReady:
            raise ValueError("radar rows cannot unlock CONFIRMED or activate sources")
        return self


class BoardEntryV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    displayRank: int = Field(gt=0)
    displayRankKey: float
    researchBoard: str
    publicState: str
    how: str
    what: str
    where: str
    when: str
    whyUnknown: tuple[str, ...] = ()
    nextConfirmCondition: str = "UNKNOWN"


class HorizonBoardsV1(BaseModel):
    model_config = MODEL_CONFIG

    horizon: str
    buy: tuple[BoardEntryV1, ...] = ()
    sell: tuple[BoardEntryV1, ...] = ()

    @model_validator(mode="after")
    def boards_capped(self) -> "HorizonBoardsV1":
        if len(self.buy) > BOARD_SIZE or len(self.sell) > BOARD_SIZE:
            raise ValueError(f"boards are capped at {BOARD_SIZE} per side")
        return self


class EvidenceRadarV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profileId: str = PROFILE_ID
    runId: str
    runHash: str
    r1BundleId: str
    r1BundleHash: str
    r2RunId: str
    r2RunHash: str
    builtAt: datetime
    stateCeiling: str = "WAIT"
    sourceActivationReady: bool = False
    canUnlockConfirmed: bool = False
    acceptanceCeiling: str = "RESEARCH_RADAR_WAIT_ONLY"
    calibration: str = CALIBRATION
    coverage: CoverageReportV1
    marketFiiChip: CalculatedFact
    boards: dict[str, HorizonBoardsV1]
    rows: tuple[RadarRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def radar_ceiling(self) -> "EvidenceRadarV1":
        if self.canUnlockConfirmed or self.sourceActivationReady:
            raise ValueError("radar cannot unlock CONFIRMED or activate sources")
        if any(
            row.publicState == "CONFIRMED" or row.researchBoard not in {"BUY", "SELL", "NONE"}
            for row in self.rows
        ):
            raise ValueError("radar rows violate the WAIT ceiling")
        return self


def _vetoed(public_state: str, ca_state: str, restriction_state: str) -> bool:
    return (
        public_state == "REJECT"
        or ca_state == "WAIT_CA"
        or "BAN" in (restriction_state or "").upper()
    )


def _facts_for_row(
    *,
    row,
    horizon: str,
    ca_state: str,
    trading_date,
    delivery_map: dict[str, float],
    delivery_history: dict[str, list[float]],
    amfi_map: dict[str, dict[str, Any]],
    shp_rows: list[dict[str, Any]] | None,
    deals_by_symbol: dict[str, list[Any]],
    event_map: dict[str, str],
    fo_symbols: set[str],
    fo_quadrants: dict[str, str],
    fo_oi_changes: dict[str, int],
    preopen_map: dict[str, dict[str, float]],
    activity_symbols: set[str],
    r5_setups: dict[str, tuple[str, ...]],
    nifty_closes: list[Any],
) -> list[CalculatedFact]:
    from .calculate import FactDirection

    def _r2_direction() -> FactDirection:
        try:
            return FactDirection(row.evidence_direction.value)
        except ValueError:
            return FactDirection.UNKNOWN

    symbol = row.symbol.upper()
    facts: list[CalculatedFact] = []
    if horizon == "INTRADAY" and preopen_map.get(symbol):
        facts.append(preopen_gap_fact(symbol, preopen_map))
    elif horizon in {"INTRADAY", "SWING"}:
        facts.append(gap_fact(symbol, trading_date, ca_state))
    if horizon in {"SWING", "POSITION"} and r5_setups.get(symbol):
        facts.insert(0, r5_setup_fact(symbol, r5_setups, _r2_direction()))
    if row.attention_priority is not None and horizon in {"INTRADAY", "SWING"}:
        facts.append(
            CalculatedFact(
                family="PARTICIPATION",
                code="R2_ATTENTION_READ",
                ok=True,
                value=row.attention_priority,
                direction=_r2_direction(),
                why="One cash-session participation story read from R2 (never re-added).",
                correlation_group="CG_ACTIVITY_SESSION",
            )
        )
        facts.append(activity_join_fact(symbol, activity_symbols))
    facts.append(named_deal_fact(symbol, deals_by_symbol.get(symbol, [])))
    if event_map.get(symbol):
        facts.append(official_event_fact(symbol, event_map))
    if horizon in {"SWING", "POSITION"}:
        facts.append(
            delivery_fact(
                symbol,
                horizon,
                delivery_map,
                history=delivery_history.get(symbol),
            )
        )
        facts.append(amfi_fact(symbol, amfi_map))
        facts.append(fo_package_fact(symbol, fo_symbols, fo_quadrants, fo_oi_changes))
    if horizon == "INTRADAY":
        facts.append(options_fact())
    if horizon == "POSITION":
        facts.append(shp_context_fact(symbol, shp_rows))
        facts.append(rs_fact(symbol, trading_date, benchmark_bars=nifty_closes or None))
    return facts


__all__ = [
    "BOARD_SIZE",
    "CALIBRATION",
    "SCHEMA_VERSION",
    "BoardEntryV1",
    "EvidenceRadarV1",
    "HorizonBoardsV1",
    "RadarRowV1",
]


def _board_entries(rows: list[RadarRowV1], board: str) -> tuple[BoardEntryV1, ...]:
    selected = [row for row in rows if row.researchBoard == board]
    if board == "SELL":
        selected.sort(key=lambda row: (row.displayRankKey or 0.0, row.symbol))
    else:
        selected.sort(key=lambda row: (-(row.displayRankKey or 0.0), row.symbol))
    entries = []
    for rank, row in enumerate(selected[:BOARD_SIZE], start=1):
        entries.append(
            BoardEntryV1(
                symbol=row.symbol,
                displayRank=rank,
                displayRankKey=row.displayRankKey or 0.0,
                researchBoard=row.researchBoard,
                publicState=row.publicState,
                how=row.how,
                what=row.what,
                where=row.where,
                when=row.when,
                whyUnknown=row.whyUnknown,
                nextConfirmCondition=row.nextConfirmCondition,
            )
        )
    return tuple(entries)


def build_evidence_radar(
    *,
    bundle: InventorySourceBundleV1 | None = None,
    attention=None,
    r14: Any | None = None,
    signals: FIIStockSignalsSnapshot | None = None,
    loader: Any = None,
    fo_batch: Any = None,
    mcx_local_rows: list[dict[str, Any]] | None = None,
    limit_watch: int = DEFAULT_LIMIT_WATCH,
    built_at: datetime | None = None,
) -> EvidenceRadarV1:
    from ..attention_order import latest_attention_order
    from ..inventory_source_bundle import latest_inventory_source_bundle
    from ..r14_live import latest_r14_ca_join
    from .calculate import FactDirection

    r1 = bundle or latest_inventory_source_bundle()
    r2 = attention or latest_attention_order()
    if r1 is None or r2 is None or limit_watch <= 0:
        raise ValueError("WAIT_RADAR_SPINE_NOT_READY")
    if r2.r1_bundle_id != r1.bundle_id or r2.r1_bundle_hash != r1.bundle_hash:
        raise ValueError("WAIT_RADAR_LINEAGE_MISMATCH")
    batch_14 = r14 if r14 is not None else latest_r14_ca_join()
    if batch_14 is None:
        raise ValueError("WAIT_RADAR_SPINE_NOT_READY")
    if batch_14.r2_run_id != r2.run_id or batch_14.r2_run_hash != r2.run_hash:
        raise ValueError("WAIT_RADAR_LINEAGE_MISMATCH")

    catalog = build_slot_catalog(r1, built_at=built_at)
    coverage = fill_slots(r1, catalog, built_at=built_at)

    from .loads import (
        default_parse_loader,
        load_activity_symbols,
        load_delivery_history,
        load_event_map,
        load_nifty_closes,
        load_preopen_map,
        load_shp_rows,
        r5_setup_map,
    )
    from ..r6_live import (
        _load_amfi_map,
        _load_delivery_map,
        _load_market_fii,
    )

    effective_loader = loader if callable(loader) else default_parse_loader()
    market_fii = _load_market_fii(effective_loader)
    delivery_map = _load_delivery_map(effective_loader)
    amfi_map = _load_amfi_map()
    shp_rows = load_shp_rows(effective_loader)
    preopen_map = load_preopen_map(effective_loader)
    activity_symbols = load_activity_symbols(effective_loader)
    event_map = load_event_map(effective_loader)
    nifty_closes = load_nifty_closes(r1.trading_date)
    r5_setups = r5_setup_map(r1.bundle_id, r1.bundle_hash, r2.run_id, r2.run_hash)

    if signals is not None:
        snapshot = signals
    else:
        snapshot = build_fii_stock_signals(loader=effective_loader)
    deals_by_symbol: dict[str, list[Any]] = {}
    for deal in snapshot.large_deals:
        deals_by_symbol.setdefault(deal.symbol.upper(), []).append(deal)

    batch_fo = fo_batch
    if batch_fo is None:
        from ..fo_a6_enrichment import latest_fo_enrichment

        batch_fo = latest_fo_enrichment()
    fo_symbols = {row.symbol.upper() for row in batch_fo.rows} if batch_fo else set()
    fo_quadrants = {
        row.symbol.upper(): (row.near_future.oi_quadrant if row.near_future else "NEUTRAL_OR_UNKNOWN")
        for row in batch_fo.rows
    } if batch_fo else {}
    fo_oi_changes = {
        row.symbol.upper(): int(row.near_future.oi_change)
        for row in (batch_fo.rows if batch_fo else ())
        if row.near_future is not None
    }

    instrument_by_candidate = {
        stock.candidate_id: stock.instrument_id for stock in r1.stock_records
    }
    ca_by_candidate = {row.candidate_id: row.ca_state for row in batch_14.rows}

    # Stage B universe: top-N WATCH by attention + any R2 row with a named
    # official event, even outside the top N.
    watch_rows = sorted(
        (row for row in r2.rows if row.public_state.value == "WATCH"),
        key=lambda row: (
            -(row.attention_priority if row.attention_priority is not None else -1.0),
            row.symbol,
        ),
    )[:limit_watch]
    selected: dict[str, Any] = {row.candidate_id: row for row in watch_rows}
    must_include = {key.upper() for key in deals_by_symbol} | {key.upper() for key in event_map}
    amfi_named = {
        key.upper()
        for key, payload in amfi_map.items()
        if int(payload.get("net_quantity_change") or 0) != 0
    }
    extra_cap = 80
    extra_added = 0
    for row in r2.rows:
        if row.candidate_id in selected:
            continue
        symbol = row.symbol.upper()
        if symbol in must_include or (symbol in amfi_named and extra_added < extra_cap):
            selected[row.candidate_id] = row
            if symbol not in must_include:
                extra_added += 1

    delivery_history = load_delivery_history(
        {row.symbol.upper() for row in selected.values()},
        r1.trading_date,
        built_at or datetime.now(UTC),
    )

    radar_rows: list[RadarRowV1] = []
    for candidate_id, row in selected.items():
        ca_state = ca_by_candidate.get(candidate_id, "WAIT_CA")
        veto = _vetoed(row.public_state.value, ca_state, row.restriction_state)
        instrument_id = instrument_by_candidate.get(candidate_id)

        for horizon in _CASH_HORIZONS:
            facts = _facts_for_row(
                row=row,
                horizon=horizon,
                ca_state=ca_state,
                trading_date=r1.trading_date,
                delivery_map=delivery_map,
                delivery_history=delivery_history,
                amfi_map=amfi_map,
                shp_rows=shp_rows,
                deals_by_symbol=deals_by_symbol,
                event_map=event_map,
                fo_symbols=fo_symbols,
                fo_quadrants=fo_quadrants,
                fo_oi_changes=fo_oi_changes,
                preopen_map=preopen_map,
                activity_symbols=activity_symbols,
                r5_setups=r5_setups,
                nifty_closes=nifty_closes,
            )
            fusion = fuse_instrument(facts, horizon)
            if veto or fusion.conflict or fusion.fused_direction not in {"BULLISH", "BEARISH"}:
                board = "NONE"
            elif fusion.fused_direction == "BULLISH":
                board = "BUY"
            else:
                board = "SELL"
            explanation = build_explain(
                symbol=row.symbol,
                horizon=horizon,
                market="NSE_CASH",
                public_state=row.public_state.value,
                fusion=fusion,
                facts=facts,
                completeness=row.completeness,
                freshness=row.freshness,
                restriction_state=row.restriction_state,
            )
            families = {
                family.family: FamilySlotV1(
                    status=family.status,
                    direction=family.direction,
                    representative_claim_id=family.representative_claim_id,
                    why=family.why,
                )
                for family in fusion.families
            }
            unknowns = tuple(fact.code for fact in facts if not fact.ok)
            if horizon == "POSITION" and "SHP_FII_DELTA_NOT_NORMALIZED" not in unknowns:
                unknowns = unknowns + ("SHP_FII_DELTA_NOT_NORMALIZED",)
            if veto:
                unknowns = unknowns + ("HARD_VETO_NO_BOARD_SEAT",)
            radar_rows.append(
                RadarRowV1(
                    symbol=row.symbol,
                    instrument_id=instrument_id,
                    market="NSE_CASH",
                    horizon=horizon,
                    publicState=row.public_state.value,
                    researchBoard=board,
                    displayRank=None,
                    displayRankKey=fusion.display_rank_key,
                    families=families,
                    slotsSkippedCount=0,
                    unknownCount=len(unknowns),
                    how=explanation.how,
                    what=explanation.what,
                    where=explanation.where,
                    when=explanation.when,
                    why=tuple(
                        family.representative_claim_id or ""
                        for family in fusion.families
                        if family.status in {"SUPPORT", "OPPOSE", "CONFLICT"}
                    ),
                    whyUnknown=unknowns,
                    nextConfirmCondition=explanation.q6_missing_proof_and_state_change_condition,
                    invalidationCondition=explanation.invalidation,
                    whatChanged="NO_BASELINE",
                    freshness=row.freshness,
                    completeness=row.completeness,
                    dataMode=_DATA_MODE[horizon],
                )
            )

    # Commodity rows exist only from local MCX context; without local master +
    # local bar they are WAIT rows with L9 UNKNOWN, never CFTC-ranked seats.
    if mcx_local_rows is None:
        mcx_local_rows = _load_mcx_local_rows()
    commodity_rows: list[RadarRowV1] = []
    for entry in mcx_local_rows or []:
        symbol = str(entry.get("symbol") or "").upper()
        prior_close = entry.get("priorClose")
        close = entry.get("close")
        oi_change = entry.get("oiChange")
        if close is None or prior_close in (None, 0):
            direction, board = "UNKNOWN", "NONE"
        else:
            change = float(close) - float(prior_close)
            direction = "BULLISH" if change > 0 else "BEARISH" if change < 0 else "NEUTRAL"
            board = (
                "BUY" if direction == "BULLISH" else "SELL" if direction == "BEARISH" else "NONE"
            )
        dte = mcx_dte_days(entry.get("expiry"), r1.trading_date)
        dte_note = f"; DTE={dte}" if dte is not None else "; DTE UNKNOWN"
        oi_note = f"; OI change={oi_change}" if oi_change is not None else "; OI UNKNOWN"
        local_ok = close is not None and prior_close not in (None, 0)
        change_pct = (
            round((float(close) - float(prior_close)) / float(prior_close), 6)
            if local_ok
            else None
        )
        local_fact = CalculatedFact(
            family="MCX_LOCAL",
            code="MCX_LOCAL_CLOSE_CHANGE" if local_ok else "UNKNOWN_NO_LOCAL_BAR",
            ok=local_ok,
            value=change_pct,
            direction=(
                FactDirection.BULLISH if direction == "BULLISH"
                else FactDirection.BEARISH if direction == "BEARISH"
                else FactDirection.UNKNOWN
            ),
            why=f"Local MCX bar vs prior local bar{oi_note}{dte_note}; global CFTC/WGC cannot substitute.",
            correlation_group="CG_MCX_LOCAL",
        )
        commodity_fusion = fuse_instrument([local_fact], "COMMODITY")
        explanation = build_explain(
            symbol=symbol,
            horizon="COMMODITY",
            market="MCX",
            public_state="WAIT",
            fusion=commodity_fusion,
            facts=[local_fact],
            completeness=1.0,
            freshness="LOCAL_MASTER_GATED",
            restriction_state="READY",
        )
        commodity_rows.append(
            RadarRowV1(
                symbol=symbol,
                instrument_id=entry.get("instrumentId"),
                market="MCX",
                horizon="COMMODITY",
                publicState="WAIT",
                researchBoard=board,
                displayRank=None,
                displayRankKey=commodity_fusion.display_rank_key,
                families={
                    "MCX_LOCAL": FamilySlotV1(
                        status="SUPPORT" if board != "NONE" else "MISSING",
                        direction=direction,
                        representative_claim_id="MCX_LOCAL_CLOSE_CHANGE",
                        why=explanation.how,
                    )
                },
                slotsSkippedCount=0,
                unknownCount=0 if (close is not None and prior_close not in (None, 0)) else 1,
                how=explanation.how,
                what=explanation.what,
                where=explanation.where,
                when=explanation.when,
                why=("MCX_LOCAL_CLOSE_CHANGE",),
                whyUnknown=("GLOBAL_CONTEXT_IS_BACKGROUND_ONLY",),
                nextConfirmCondition=explanation.q6_missing_proof_and_state_change_condition,
                invalidationCondition="close back through prior local bar on MCX series",
                whatChanged="NO_BASELINE",
                freshness="LOCAL_MASTER_GATED",
                completeness=1.0,
                dataMode=_DATA_MODE["COMMODITY"],
            )
        )
    radar_rows.extend(commodity_rows)

    boards: dict[str, HorizonBoardsV1] = {}
    for horizon in (*_CASH_HORIZONS, "COMMODITY"):
        horizon_rows = [row for row in radar_rows if row.horizon == horizon]
        buy = _board_entries(horizon_rows, "BUY")
        sell = _board_entries(horizon_rows, "SELL")
        boards[horizon] = HorizonBoardsV1(horizon=horizon, buy=buy, sell=sell)

    identity = {
        "r1BundleHash": r1.bundle_hash,
        "r2RunHash": r2.run_hash,
        "r14RunId": batch_14.run_id,
        "coverageHash": hashlib.sha256(
            json.dumps(coverage.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest()[:32],
        "rows": len(radar_rows),
    }
    run_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    now = built_at or datetime.now(UTC)
    return EvidenceRadarV1(
        runId=stable_radar_id(r1.bundle_id, r2.run_id, run_hash),
        runHash=run_hash,
        r1BundleId=r1.bundle_id,
        r1BundleHash=r1.bundle_hash,
        r2RunId=r2.run_id,
        r2RunHash=r2.run_hash,
        builtAt=now,
        coverage=coverage,
        marketFiiChip=market_fii_chip_fact(market_fii),
        boards=boards,
        rows=tuple(radar_rows),
        warnings=(
            "Evidence radar counts every source as one typed slot; slots are "
            "never votes. Boards are WAIT-only research displays.",
            "Market FII net is a whole-market chip and can never say "
            "'FII bought this stock'.",
        ),
    )


def stable_radar_id(bundle_id: str, run_id: str, run_hash: str) -> str:
    import hashlib as _hashlib

    digest = _hashlib.sha256(f"{bundle_id}|{run_id}|{run_hash}".encode()).hexdigest()[:16]
    return f"radar-{digest}"





