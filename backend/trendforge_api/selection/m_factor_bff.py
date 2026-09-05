"""M-Factor read-only BFF: two File A FUS-009 hypotheses projected onto boards.

Contract owners:
- docs/fable/remaining_build/M_FACTOR_LIVE_UI_OPENCODE_PROMPT.md (build prompt)
- docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md par 1D (scanner contract)
- docs/fable/new_merge_PLAN_2026-07-18.md FUS-009 (resolver law)

This module composes the hash-matched R1/R2/R3 lineage. It never recomputes
factor weights, never writes state, never unlocks CONFIRMED and never emits
trade geometry. long/short are exactly two `resolve_evidence` outputs for the
same claims; m_balance/rank_strength are difference/max of those two outputs.
Strengths are exposed in 0-100 display points (FUS-009 raw output is 0-1);
M_FACTOR_CLASS_V0 bands are uncalibrated until R16.
"""

from __future__ import annotations

import os
import time as _time
from datetime import date, datetime
from enum import StrEnum
from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, model_validator

from ..source_inventory_compiler import compile_default_inventory
from .attention_order import InventoryDiscoveryV1, latest_attention_order
from .cash_a1_staging import latest_cash_staging
from .cash_a2_identity import latest_cash_identity
from .cash_a4_history import list_raw_bars
from .contracts import (
    MODEL_CONFIG,
    DataMode,
    EvidenceDirection,
    EvidenceFamily,
    SelectionState,
    StateCeiling,
    stable_id,
)
from .index_a5_context import latest_cash_context
from .inventory_source_bundle import (
    InventorySourceBundleV1,
    latest_inventory_source_bundle,
)
from .m_factor_claims import (
    INDEX_SESSION_CHANGE_SANITY_PERCENT,
    StructureRebuild,
    index_session_conflict,
    merge_symbol_claims,
    rebuild_r5_claims,
    structure_how_text,
    what_label,
)
from .r3_live import (
    PROFILE_ID,
    PROFILE_VERSION,
    R3ResolutionV1,
    _r2_gate,
    latest_r3_resolution,
    live_profile,
)
from .r3_claim_adapter import claims_from_cash_pipeline
from .r5_live import latest_r5_structure_batch
from .r14_live import latest_r14_ca_join
from .r6_live import build_r6_enrichment
from .resolver import ClaimDisposition, resolve_evidence

SCHEMA_VERSION = "trendforge.tools.m-factor.v1"
CLASS_VERSION = "M_FACTOR_CLASS_V0"
CALIBRATION = "UNCALIBRATED_M_FACTOR_CLASS_V0"
IST = ZoneInfo("Asia/Kolkata")
LONG_FORMULA = "FUS-009 evidence_strength(BULLISH) x100 display points"
SHORT_FORMULA = "FUS-009 evidence_strength(BEARISH) x100 display points"


class MFactorHorizon(StrEnum):
    INTRA = "intra"
    SWING = "swing"
    POSITION = "position"
    COMMODITY = "commodity"


class MFactorSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
    BOTH = "both"


HORIZON_WAIT_CODES: dict[MFactorHorizon, str] = {
    MFactorHorizon.INTRA: "WAIT_HORIZON_INTRADAY_NOT_ACTIVATED",
    MFactorHorizon.POSITION: "WAIT_HORIZON_POSITION_NOT_WIRED",
    MFactorHorizon.COMMODITY: "WAIT_HORIZON_COMMODITY_MCX_LOCAL_NOT_WIRED",
}

_BASE_WARNINGS = (
    "Evidence strength is not win probability.",
    "M_FACTOR_CLASS_V0 bands are uncalibrated research defaults until R16 PIT/OOS approval.",
    "Live lineage is EOD_RESEARCH cash diagnostic; the intraday F&O eyebrow is product intent, not live data.",
)


class MFactorNotReady(Exception):
    """Raised when the BFF must fail closed instead of mixing snapshots."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _cache_enabled() -> bool:
    """Read-only lineage cache; disabled under pytest so loader monkeypatches stay authoritative."""
    return "PYTEST_CURRENT_TEST" not in os.environ


@lru_cache(maxsize=1)
def _compiled_contracts() -> tuple:
    return compile_default_inventory().source_contracts


# EOD lineage changes only when a new pipeline run persists. The batch carries
# its own runId/availableAt, so serving a 10-minute-old composition stays
# honest while avoiding a ~16-20s cold rebuild (R5 claim rebuilds across the
# setup universe) on every 30s of idle.
_LINEAGE_TTL_SECONDS = 600.0
_lineage_cache: dict[str, object] = {"expires": 0.0, "value": None}
_BATCH_CACHE_LIMIT = 8
_batch_cache: dict[tuple, MFactorBatchV1] = {}


def directional_class(m_balance_points: float) -> str:
    """M_FACTOR_CLASS_V0 display bands over 0-100 display points."""
    if m_balance_points >= 60:
        return "Strong Bull"
    if m_balance_points >= 20:
        return "Bull"
    if m_balance_points > -20:
        return "Neutral"
    if m_balance_points > -60:
        return "Bear"
    return "Strong Bear"


def assign_board(
    long_points: float,
    short_points: float,
    row_class: str,
    *,
    public_state: str,
    index_conflict: bool = False,
) -> tuple[str, str | None]:
    """One seat per horizon. Gates beat class; conflict means WAIT, not dual seat."""
    if public_state == SelectionState.REJECT.value:
        return "wait", "PUBLIC_REJECT"
    if index_conflict:
        return "wait", "INDEX_CONFLICT"
    if long_points > short_points and row_class in {"Bull", "Strong Bull"}:
        return "buy", None
    if short_points > long_points and row_class in {"Bear", "Strong Bear"}:
        return "sell", None
    return "wait", "NEUTRAL_OR_UNRESOLVED"


def _freshness_rank(freshness: str) -> int:
    return 0 if freshness == "FRESH" else 1


def _display_points(raw_strength: float) -> float:
    return round(raw_strength * 100, 2)


class MFactorTrackV1(BaseModel):
    model_config = MODEL_CONFIG

    state: str = "PIT_NOT_VALIDATED"
    sample_count: int = 0
    win_rate: float | None = None
    benchmark_delta: float | None = None
    unlock_owner: str = "R16"


class MFactorMarketStripV1(BaseModel):
    model_config = MODEL_CONFIG

    condition: str
    advancers: int | None = None
    decliners: int | None = None
    average_move: float | None = None
    universe_size: int
    cutoff_ist: str


class MFactorFamilyDebugV1(BaseModel):
    model_config = MODEL_CONFIG

    family: str
    weight: float
    support_strength: float
    opposition_strength: float


class MFactorSuppressedV1(BaseModel):
    model_config = MODEL_CONFIG

    claim_id: str | None = None
    disposition: str
    reason: str


class MFactorRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    instrument_id: str
    horizon: MFactorHorizon
    long_strength: float = Field(ge=0, le=100)
    short_strength: float = Field(ge=0, le=100)
    m_balance: float = Field(ge=-100, le=100)
    rank_strength: float = Field(ge=0, le=100)
    directional_class: str
    readiness_tag: str
    public_state: str
    how: str
    what: str
    where: str
    when: str
    next_proof: str
    why_wait: tuple[str, ...] = ()
    gate_codes: tuple[str, ...] = ()
    completeness: float = Field(ge=0, le=1)
    freshness: str
    entry: None = None
    stop: None = None
    t1: None = None
    t2: None = None
    quantity: None = None
    selected_support_claim_ids: tuple[str, ...] = ()
    selected_opposition_claim_ids: tuple[str, ...] = ()
    suppressed: tuple[MFactorSuppressedV1, ...] = ()
    index_conflict: bool = False
    r3_evidence_strength: float | None = None
    families: tuple[MFactorFamilyDebugV1, ...] = ()

    @model_validator(mode="after")
    def row_stays_non_executable(self) -> "MFactorRowV1":
        if self.public_state == SelectionState.CONFIRMED.value:
            raise ValueError("M-Factor rows cannot be CONFIRMED")
        if any(value is not None for value in (self.entry, self.stop, self.t1, self.t2, self.quantity)):
            raise ValueError("M-Factor rows cannot carry trade geometry")
        return self


class MFactorBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    horizon: MFactorHorizon
    data_mode: str = DataMode.EOD_RESEARCH.value
    side_filter: MFactorSide
    limit: int
    debug: bool = False
    horizon_wait_code: str | None = None
    run_id: str
    snapshot_bundle_id: str
    r1_bundle_id: str
    r1_bundle_hash: str
    r2_run_id: str
    r2_run_hash: str
    r3_run_id: str
    r3_run_hash: str
    trading_date: str
    available_at: datetime
    cutoff_ist: str
    state_ceiling: str = StateCeiling.WAIT.value
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    calibration: str = CALIBRATION
    class_version: str = CLASS_VERSION
    long_formula: str = LONG_FORMULA
    short_formula: str = SHORT_FORMULA
    market_strip: MFactorMarketStripV1
    buy_rows: tuple[MFactorRowV1, ...] = ()
    sell_rows: tuple[MFactorRowV1, ...] = ()
    wait_rows: tuple[MFactorRowV1, ...] = ()
    track: MFactorTrackV1 = MFactorTrackV1()
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def batch_stays_read_only(self) -> "MFactorBatchV1":
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("M-Factor BFF cannot activate sources or unlock CONFIRMED")
        for row in self.buy_rows + self.sell_rows + self.wait_rows:
            if row.horizon is not self.horizon:
                raise ValueError("rows cannot cross horizons")
        return self


def _load_lineage() -> tuple[
    InventorySourceBundleV1, InventoryDiscoveryV1, R3ResolutionV1
]:
    if _cache_enabled():
        now = _time.monotonic()
        cached = _lineage_cache["value"]
        if cached is not None and now < float(_lineage_cache["expires"]):
            return cached  # type: ignore[return-value]
    bundle = latest_inventory_source_bundle()
    if bundle is None:
        raise MFactorNotReady("WAIT_R1_BUNDLE_NOT_READY", "No persisted R1 inventory bundle.")
    attention = latest_attention_order()
    if attention is None:
        raise MFactorNotReady("WAIT_R2_ATTENTION_NOT_READY", "No persisted R2 attention order.")
    resolution = latest_r3_resolution()
    if resolution is None:
        raise MFactorNotReady(
            "R3_RESOLUTION_NOT_READY", "No persisted R3 resolution for the current lineage."
        )
    if (
        resolution.r1_bundle_id != bundle.bundle_id
        or resolution.r1_bundle_hash != bundle.bundle_hash
        or resolution.r2_run_id != attention.run_id
        or resolution.r2_run_hash != attention.run_hash
        or resolution.permission_fingerprint != bundle.permission_fingerprint
    ):
        raise MFactorNotReady(
            "WAIT_MIXED_SNAPSHOT",
            "Persisted R3 does not hash-match the current R1/R2 lineage.",
        )
    value = (bundle, attention, resolution)
    if _cache_enabled():
        _lineage_cache["value"] = value
        _lineage_cache["expires"] = _time.monotonic() + _LINEAGE_TTL_SECONDS
    return value


def _market_strip(
    bundle: InventorySourceBundleV1, attention: InventoryDiscoveryV1
) -> MFactorMarketStripV1:
    returns = [
        value
        for record in bundle.stock_records
        if isinstance((value := record.cheap_features.get("sessionReturn")), (int, float))
    ]
    advancers = sum(1 for value in returns if value > 0)
    decliners = sum(1 for value in returns if value < 0)
    average_move = round(sum(returns) / len(returns), 4) if returns else None
    cutoff = attention.built_at.astimezone(IST).isoformat()
    return MFactorMarketStripV1(
        condition="WAIT_DATA",
        advancers=advancers if returns else None,
        decliners=decliners if returns else None,
        average_move=average_move,
        universe_size=attention.universe_count,
        cutoff_ist=cutoff,
    )


def _empty_horizon_batch(
    *,
    horizon: MFactorHorizon,
    side: MFactorSide,
    limit: int,
    bundle: InventorySourceBundleV1,
    attention: InventoryDiscoveryV1,
    resolution: R3ResolutionV1,
) -> MFactorBatchV1:
    code = HORIZON_WAIT_CODES[horizon]
    warnings = _BASE_WARNINGS + (
        code,
        "No rows are minted for this horizon; global commodity and delayed sponsors never create board seats.",
    )
    return MFactorBatchV1(
        horizon=horizon,
        side_filter=side,
        limit=limit,
        horizon_wait_code=code,
        run_id=stable_id("m-factor-bff", resolution.run_id, horizon.value),
        snapshot_bundle_id=attention.snapshot_bundle_id,
        r1_bundle_id=bundle.bundle_id,
        r1_bundle_hash=bundle.bundle_hash,
        r2_run_id=attention.run_id,
        r2_run_hash=attention.run_hash,
        r3_run_id=resolution.run_id,
        r3_run_hash=resolution.run_hash,
        trading_date=attention.trading_date,
        available_at=attention.built_at,
        cutoff_ist=attention.built_at.astimezone(IST).isoformat(),
        market_strip=_market_strip(bundle, attention),
        warnings=warnings,
    )


def build_m_factor_batch(
    *,
    horizon: MFactorHorizon | str = MFactorHorizon.SWING,
    side: MFactorSide | str = MFactorSide.BOTH,
    limit: int = 40,
    debug: bool = False,
) -> MFactorBatchV1:
    horizon = MFactorHorizon(horizon)
    side = MFactorSide(side)
    bundle, attention, resolution = _load_lineage()

    cache_key = (bundle.bundle_id, attention.run_id, resolution.run_id, horizon.value, side.value, limit, debug)
    if _cache_enabled() and cache_key in _batch_cache:
        return _batch_cache[cache_key]
    stale_keys = [
        key
        for key in _batch_cache
        if key[0] != bundle.bundle_id or key[1] != attention.run_id or key[2] != resolution.run_id
    ]
    for key in stale_keys:
        _batch_cache.pop(key, None)

    if horizon is not MFactorHorizon.SWING:
        batch = _empty_horizon_batch(
            horizon=horizon,
            side=side,
            limit=limit,
            bundle=bundle,
            attention=attention,
            resolution=resolution,
        )
        if _cache_enabled() and len(_batch_cache) < _BATCH_CACHE_LIMIT:
            _batch_cache[cache_key] = batch
        return batch

    staging = latest_cash_staging()
    identity = latest_cash_identity()
    if staging is None or identity is None:
        raise MFactorNotReady(
            "WAIT_MFACTOR_LINEAGE_NOT_READY",
            "A1 staging or A2 identity is missing for the persisted R3 lineage.",
        )
    adapter = claims_from_cash_pipeline(
        bundle=bundle,
        attention=attention,
        source_result=staging.source_result,
        identity=identity,
        compiled_source_contracts=_compiled_contracts(),
    )
    r3_by_symbol = {row.symbol: row for row in resolution.rows}
    r1_by_symbol = {row.symbol: row for row in bundle.stock_records}
    identity_by_symbol = {
        row.instrument.symbol: row for row in identity.rows
    }

    r5_batch = latest_r5_structure_batch()
    r5_by_symbol = {}
    r5_warnings: list[str] = []
    if r5_batch is not None:
        if (
            r5_batch.r1_bundle_hash == bundle.bundle_hash
            and r5_batch.r2_run_hash == attention.run_hash
        ):
            r5_by_symbol = {row.symbol: row for row in r5_batch.rows}
        else:
            r5_warnings.append("R5_STRUCTURE_STALE_WITHHELD: geometry withheld, snapshot hashes differ.")

    r14_batch = latest_r14_ca_join()
    ca_by_symbol = (
        {row.symbol.upper(): row for row in r14_batch.rows}
        if r14_batch is not None
        else {}
    )
    if (
        r5_batch is not None
        and r5_by_symbol
        and (r14_batch is None or r5_batch.r14_run_hash != r14_batch.run_hash)
    ):
        r5_warnings.append(
            "R14_CA_STALE_WITHHELD: STRUCTURE claims withheld; the latest CA join is not the one R5 used."
        )
        r5_by_symbol = {}

    context = latest_cash_context()
    index_change_percent = None
    if (
        context is not None
        and context.index.parser_state == "PARSED_STRUCTURED"
        and context.index.data_date == attention.trading_date
    ):
        index_change_percent = context.index.nifty50_change_percent
        if (
            index_change_percent is not None
            and abs(index_change_percent) > INDEX_SESSION_CHANGE_SANITY_PERCENT
        ):
            r5_warnings.append(
                "INDEX_CHANGE_SUSPECT: nifty50_change_percent "
                f"{index_change_percent}% exceeds the sanity bound; INDEX_CONFLICT_V0 stays unproven."
            )
            index_change_percent = None
    elif r5_by_symbol and any(
        "WAIT_INDEX_CONTEXT_MISSING" in row.gate_codes for row in r5_by_symbol.values()
    ):
        r5_warnings.append("INDEX_CONTEXT_MISSING: INDEX_CONFLICT_V0 cannot be evaluated.")

    r6_by_symbol = {}
    try:
        r6_batch = build_r6_enrichment()
        if (
            r6_batch.r1_bundle_hash == bundle.bundle_hash
            and r6_batch.r2_run_hash == attention.run_hash
        ):
            r6_by_symbol = {row.symbol: row for row in r6_batch.rows}
        else:
            r5_warnings.append("R6_ENRICHMENT_STALE_WITHHELD: WHAT labels fall back to UNKNOWN.")
    except ValueError:
        r5_warnings.append(
            "R6_ENRICHMENT_NOT_READY: WHAT labels fall back to UNKNOWN_NO_LARGE_DEAL_ROW."
        )

    trading_date = date.fromisoformat(attention.trading_date)
    profile = live_profile()
    buy_rows: list[MFactorRowV1] = []
    sell_rows: list[MFactorRowV1] = []
    wait_rows: list[MFactorRowV1] = []

    for r2 in attention.rows:
        r3_row = r3_by_symbol.get(r2.symbol)
        if r3_row is None:
            raise MFactorNotReady(
                "WAIT_MIXED_SNAPSHOT", f"R3 has no row for R2 symbol {r2.symbol}."
            )
        r5 = r5_by_symbol.get(r2.symbol)
        structure: StructureRebuild | None = None
        if r5 is not None and r5.detected_setups and r5.metrics is not None:
            identity_row = identity_by_symbol.get(r2.symbol)
            ca_row = ca_by_symbol.get(r2.symbol.upper())
            if identity_row is None or ca_row is None:
                structure = StructureRebuild(
                    codes=("WAIT_R5_REBUILD_INPUTS_MISSING",),
                    detected_setups=r5.detected_setups,
                )
            else:
                structure = rebuild_r5_claims(
                    r5_row=r5,
                    instrument=identity_row.instrument,
                    raw_bars=list_raw_bars(r2.symbol, through=trading_date),
                    ca_row=ca_row,
                    source_result=adapter.source_results[0],
                    decision_at=attention.built_at,
                )
        merged = merge_symbol_claims(
            cash_claims=adapter.claims_by_symbol.get(r2.symbol, ()),
            cash_facts=adapter.facts_by_symbol.get(r2.symbol, ()),
            adapter_suppressions=adapter.suppressions_by_symbol.get(r2.symbol, ()),
            structure=structure,
        )
        shared = dict(
            profile=profile,
            decision_at=attention.built_at,
            claims=merged.claims,
            facts=merged.facts,
            source_results=adapter.source_results,
            completeness=r2.completeness,
            existing_gates=(_r2_gate(r2.public_state),),
            data_mode=DataMode.EOD_RESEARCH,
        )
        long_run = resolve_evidence(evidence_direction=EvidenceDirection.BULLISH, **shared)
        short_run = resolve_evidence(evidence_direction=EvidenceDirection.BEARISH, **shared)

        direction_run = (
            long_run if r2.evidence_direction is EvidenceDirection.BULLISH else short_run
        )

        long_points = _display_points(long_run.evidence_strength)
        short_points = _display_points(short_run.evidence_strength)
        m_balance = round(long_points - short_points, 2)
        rank_strength = max(long_points, short_points)
        row_class = directional_class(m_balance)

        r1 = r1_by_symbol.get(r2.symbol)
        index_conflict = index_session_conflict(
            row_class=row_class, index_change_percent=index_change_percent
        )

        why_wait: list[str] = []
        why_wait.extend(gate.code for gate in direction_run.gate_results if gate.blocks_confirmed)
        why_wait.extend(merged.suppressions)
        why_wait.extend(merged.structure_codes)
        why_wait.extend(r2.why_not_confirmed)
        if r5 is not None:
            why_wait.extend(r5.why_wait)

        structure_family = next(
            (item for item in direction_run.families if item.family is EvidenceFamily.STRUCTURE),
            None,
        )
        structure_voted = structure_family is not None and structure_family.support_strength > 0
        if r3_row.resolution_state is SelectionState.REJECT:
            readiness = "INVALIDATED"
        elif structure_voted:
            readiness = "SETUP_READY"
        else:
            readiness = "DEVELOPING"

        structure_selected_ids = tuple(
            claim.claim_id
            for claim in direction_run.claims
            if claim.disposition is ClaimDisposition.SELECTED_SUPPORT
            and claim.family is EvidenceFamily.STRUCTURE
        )
        how = structure_how_text(
            merged,
            structure_claim_ids=structure_selected_ids,
            structure_state=r5.structure_state.value if r5 is not None else None,
        )
        r6_row = r6_by_symbol.get(r2.symbol)
        what = what_label(
            deal_summary=r6_row.deal_summary if r6_row is not None else None,
            deal_tag=r6_row.deal_tag if r6_row is not None else None,
        )
        board, seat_reason = assign_board(
            long_points,
            short_points,
            row_class,
            public_state=r3_row.resolution_state.value,
            index_conflict=index_conflict,
        )
        if r1 is not None and r1.restriction_state == "VETO":
            board, seat_reason = "wait", "SAFETY_BAN_VETO"
        if seat_reason:
            why_wait.append(seat_reason)

        row = MFactorRowV1(
            symbol=r2.symbol,
            instrument_id=r1.instrument_id if r1 is not None else "IDENTITY_UNRESOLVED",
            horizon=MFactorHorizon.SWING,
            long_strength=long_points,
            short_strength=short_points,
            m_balance=m_balance,
            rank_strength=rank_strength,
            directional_class=row_class,
            readiness_tag=readiness,
            public_state=r3_row.resolution_state.value,
            how=how,
            what=what,
            where=(
                f"{r1.instrument_id} | NSE_EQ EOD | restriction {r1.restriction_state}"
                if r1 is not None
                else "IDENTITY_UNRESOLVED: no R1 stock record for this symbol"
            ),
            when=(
                f"snapshot {attention.trading_date}; availableAt "
                f"{attention.built_at.astimezone(IST).isoformat()}; freshness {r2.freshness}"
            ),
            next_proof=direction_run.reason
            or "SOURCE_ACTIVATION: sources are not unlocked for CONFIRMED",
            why_wait=tuple(dict.fromkeys(item for item in why_wait if item)),
            gate_codes=tuple(gate.code for gate in direction_run.gate_results),
            completeness=r2.completeness,
            freshness=r2.freshness,
            selected_support_claim_ids=long_run.selected_claim_ids,
            selected_opposition_claim_ids=tuple(
                claim_id
                for claim in long_run.claims
                if claim.disposition is ClaimDisposition.SELECTED_OPPOSITION
                for claim_id in (claim.claim_id,)
            ),
            suppressed=tuple(
                MFactorSuppressedV1(
                    claim_id=claim.claim_id, disposition=claim.disposition.value, reason=claim.reason
                )
                for claim in long_run.claims
                if claim.disposition
                not in {ClaimDisposition.SELECTED_SUPPORT, ClaimDisposition.SELECTED_OPPOSITION}
            ),
            index_conflict=index_conflict,
            r3_evidence_strength=_display_points(r3_row.evidence_strength),
            families=(
                tuple(
                    MFactorFamilyDebugV1(
                        family=item.family.value,
                        weight=item.weight,
                        support_strength=item.support_strength,
                        opposition_strength=item.opposition_strength,
                    )
                    for item in long_run.families
                )
                if debug
                else ()
            ),
        )
        if board == "buy":
            buy_rows.append(row)
        elif board == "sell":
            sell_rows.append(row)
        else:
            wait_rows.append(row)

    def sort_and_cap(rows: list[MFactorRowV1]) -> tuple[MFactorRowV1, ...]:
        ordered = sorted(
            rows,
            key=lambda item: (
                -item.rank_strength,
                -item.completeness,
                _freshness_rank(item.freshness),
                item.symbol,
            ),
        )
        return tuple(ordered[:limit])

    warnings = list(_BASE_WARNINGS) + r5_warnings + [
        "STRUCTURE claims are rebuilt from hash-matched R5 rows (FTR-006/007/017); the R5 WAIT ceiling is unchanged.",
        "EVENT family: named deals surface as WHAT labels only; FTR-026 fact wiring is not live yet.",
        "INDEX_CONFLICT_V0 is a +/-1.0% NIFTY session-change heuristic; the versioned breadth+structure rule is not built yet.",
        "M-Factor composes a richer claim set than the persisted R3 diagnostic; r3EvidenceStrength is shown per row for comparison.",
    ]
    if side is MFactorSide.BUY:
        sell_rows, wait_rows = [], []
    elif side is MFactorSide.SELL:
        buy_rows, wait_rows = [], []

    batch = MFactorBatchV1(
        horizon=MFactorHorizon.SWING,
        side_filter=side,
        limit=limit,
        debug=debug,
        run_id=stable_id("m-factor-bff", resolution.run_id, MFactorHorizon.SWING.value),
        snapshot_bundle_id=attention.snapshot_bundle_id,
        r1_bundle_id=bundle.bundle_id,
        r1_bundle_hash=bundle.bundle_hash,
        r2_run_id=attention.run_id,
        r2_run_hash=attention.run_hash,
        r3_run_id=resolution.run_id,
        r3_run_hash=resolution.run_hash,
        trading_date=attention.trading_date,
        available_at=attention.built_at,
        cutoff_ist=attention.built_at.astimezone(IST).isoformat(),
        market_strip=_market_strip(bundle, attention),
        buy_rows=sort_and_cap(buy_rows),
        sell_rows=sort_and_cap(sell_rows),
        wait_rows=sort_and_cap(wait_rows),
        warnings=tuple(warnings),
    )
    if _cache_enabled() and len(_batch_cache) < _BATCH_CACHE_LIMIT:
        _batch_cache[cache_key] = batch
    return batch
