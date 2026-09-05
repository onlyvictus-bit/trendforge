"""Read-only BFF for the four OI/options rooms.

Contract owner: docs/fable/remaining_build/OI_OPTIONS_ROOMS_GLM_PROMPT.md
Endpoints (wired in main.py):
    GET /api/v1/tools/oi_analysis?symbol=&limit=
    GET /api/v1/tools/oi_tracker?underlying=&limit=
    GET /api/v1/tools/strike_explorer?underlying=&expiry=
    GET /api/v1/tools/expiry_prediction?underlying=&expiry=
POST on any of these is rejected with 405 by main.py.

Law: futures OI never mixes with option OI; observation codes are
PRICE_*_OI_* with legacy aliases; official MWPL/ban gates run BEFORE the
quadrant; PCR denominators of zero stay UNKNOWN; fixture demo strings
never appear in live DTOs; nothing here emits File A CONFIRMED and no
row carries trade geometry.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from .. import storage
from ..gate_readiness import stock_safety_state
from ..selection.contracts import MODEL_CONFIG
from ..selection.fo_a6_enrichment import FoEnrichmentBatch, latest_fo_enrichment
from ..storage import get_latest_source_parse_result
from .calendars import expiry_context
from .chain_quality import DEFAULT_SPREAD_LIMIT_PCT, StrikeQuote, assess_chain
from .guidance import hero_zero_guidance
from .hard_blocks import WAIT_MARGIN_API, evaluate_hard_blocks
from .iv_recorder import chain_snapshots
from .mwpl_gate import official_mwpl_state
from .quadrant import ObservationCode, QuadrantResult, observation_quadrant
from .surface import max_pain_reference, pcr_oi, unsigned_cash_gamma_per_strike, walls

SCHEMA_VERSION = "trendforge.tools.oi-options.v1"
STATE_CEILING = "RESEARCH_SHADOW_ONLY"

COLUMNS_SPEC: tuple[dict[str, str], ...] = (
    {"column": "Price path", "meaning": "Rising / falling over the ALIGNED interval", "trap": "Not a breakout call"},
    {"column": "OI delta", "meaning": "% change in futures OI", "trap": "Must be the same contract/expiry as price"},
    {"column": "Volume / OI", "meaning": "Activity vs outstanding positions", "trap": "Not smart-money quality"},
    {"column": "Descriptive bucket", "meaning": "One of four codes or UNKNOWN", "trap": "Never BUY/SELL"},
    {"column": "State", "meaning": "WATCH / WAIT / REJECT", "trap": "OI cannot push to CONFIRMED"},
)

_FORBIDDEN_DEMO_STRINGS = ("TATASTEEL", "+18.4%", "ILLUSTRATIVE FIXTURE")


class OiToolsNotReady(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class TrackRecordV1(BaseModel):
    model_config = MODEL_CONFIG
    state: str = "PIT_NOT_VALIDATED"
    sample_count: int = 0
    win_rate: float | None = None
    unlock_owner: str = "R16"


class MwplViewV1(BaseModel):
    model_config = MODEL_CONFIG
    official_state: str
    oi_percent_of_mwpl: float | None = None
    in_ban_list: bool | None = None
    alert60_active: bool | None = None
    internal_band: str | None = None


class OiAnalysisRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    instrument_class: str = "FUTURE"
    expiry: str
    close: float
    previous_close: float
    price_change_pct: float | None = None
    open_interest: int
    prior_open_interest: int | None = None
    oi_change_pct: float | None = None
    volume_to_oi: float | None = None
    observation_code: str
    legacy_code: str | None = None
    interval: str = "EOD"
    roll_window: bool = False
    mwpl: MwplViewV1
    surveillance_stage: str | None = None
    public_state: str
    blockers: tuple[str, ...] = ()
    interpretation: str
    trader_read: str = ""
    if_long_bias: str = ""
    if_short_bias: str = ""
    next_step: str = ""
    activity_note: str | None = None
    authority: str = "CONTEXT_ONLY"
    can_confirm: bool = False
    entry: None = None
    stop: None = None
    quantity: None = None

    def validate_row(self) -> "OiAnalysisRowV1":
        if self.public_state == "CONFIRMED":
            raise ValueError("OI rows cannot be CONFIRMED")
        return self


class OiAnalysisBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    tool: str = "oi_analysis"
    state_ceiling: str = STATE_CEILING
    data_date: str | None = None
    artifact_hash: str | None = None
    row_count: int = Field(ge=0)
    columns_spec: tuple[dict[str, str], ...]
    rows: tuple[OiAnalysisRowV1, ...]
    warnings: tuple[str, ...] = ()
    track: TrackRecordV1 = TrackRecordV1()


class OiTrackerRowV1(BaseModel):
    model_config = MODEL_CONFIG

    underlying: str
    observations: int = Field(ge=0)
    first_data_date: str | None = None
    last_data_date: str | None = None
    first_oi: int | None = None
    last_oi: int | None = None
    oi_path_label: str
    pcr_open: float | None = None
    pcr_current: float | None = None
    roll_aware_window: bool = True
    public_state: str
    authority: str = "CONTEXT_ONLY"
    can_confirm: bool = False


class OiTrackerBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    tool: str = "oi_tracker"
    state_ceiling: str = "WAIT_CHAIN_WHEN_SURFACE_MISSING"
    row_count: int = Field(ge=0)
    rows: tuple[OiTrackerRowV1, ...]
    track: TrackRecordV1 = TrackRecordV1()


class StrikeLadderRowV1(BaseModel):
    model_config = MODEL_CONFIG

    strike: float
    right: str
    open_interest: float
    volume: float
    bid: float | None = None
    ask: float | None = None
    ltp: float | None = None
    implied_volatility: float | None = None
    spread_pct: float | None = None
    cash_gamma_proxy: float | None = None


class WallViewV1(BaseModel):
    model_config = MODEL_CONFIG

    role: str
    strike: float | None = None
    open_interest: float | None = None
    persistence_snapshots: int = 1
    first_known_at: str | None = None


class StrikeExplorerBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    tool: str = "strike_explorer"
    underlying: str
    expiry: str
    quality_state: str
    completeness: float = Field(ge=0, le=1)
    max_spread_pct: float | None = None
    ladder: tuple[StrikeLadderRowV1, ...]
    call_wall: WallViewV1
    put_wall: WallViewV1
    max_pain_reference: float | None = None
    gamma_label: str = "UNSIGNED_CASH_GAMMA_PROXY_NOT_DEALER_GEX"
    blockers: tuple[str, ...] = ()
    state_ceiling: str = "WATCH"
    track: TrackRecordV1 = TrackRecordV1()


class ExpiryRangeBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    tool: str = "expiry_prediction"
    underlying: str
    expiry: str
    dte_calendar_days: int
    is_tuesday_expiry: bool
    is_mega_expiry: bool
    mega_stress_tag: str
    physical_block_active_from: str | None = None
    range_low: float | None = None
    range_high: float | None = None
    range_method: str = "STRADDLE_EXPECTED_MOVE_V0"
    max_pain_reference: float | None = None
    agreement_fraction: float | None = None
    hero_zero: dict | None = None
    blockers: tuple[str, ...] = ()
    margin_slot: str = WAIT_MARGIN_API
    state_ceiling: str = "WATCH"
    track: TrackRecordV1 = TrackRecordV1()


# ---------------------------------------------------------------------------
# loaders (monkeypatch targets in tests)
# ---------------------------------------------------------------------------


def _load_fo_batch() -> FoEnrichmentBatch | None:
    return latest_fo_enrichment()


def list_fo_enrichment_history(limit: int = 30) -> list[FoEnrichmentBatch]:
    storage.init_db()
    conn = storage.connect()
    try:
        heads = conn.execute(
            """
            SELECT payload_json FROM fo_enrichment_runs
            ORDER BY persisted_at DESC, batch_id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    out: list[FoEnrichmentBatch] = []
    for head in heads:
        try:
            out.append(FoEnrichmentBatch.model_validate(storage.decode_json(head["payload_json"])))
        except Exception:
            continue
    return out


def _mwpl_percent_map() -> dict[str, float]:
    parsed = get_latest_source_parse_result("nse_mwpl_percentages")
    if parsed is None or parsed.parser_state != "PARSED_STRUCTURED":
        return {}
    out: dict[str, float] = {}
    for row in parsed.output.get("rows") or []:
        symbol = str(row.get("symbol") or "").strip().upper()
        for key in ("percentOfMwpl", "mwplPercent", "percentage", "percent"):
            if row.get(key) is not None:
                try:
                    out[symbol] = float(row[key])
                    break
                except (TypeError, ValueError):
                    continue
    return out


def _safety(symbol: str) -> dict[str, Any]:
    try:
        return stock_safety_state(symbol)
    except Exception:
        return {"state": "UNKNOWN", "reason": "unavailable", "matches": []}


def _ban(symbol: str) -> bool:
    try:
        from ..gate_readiness import _symbol_has_fno_ban

        return bool(_symbol_has_fno_ban(symbol))
    except Exception:
        return False


def _assert_no_demo_strings(batch: BaseModel) -> None:
    text = storage.encode_json(batch.model_dump(mode="json", by_alias=True)).upper()
    for needle in _FORBIDDEN_DEMO_STRINGS:
        if needle.upper() in text:
            raise ValueError(f"fixture demo string leaked into live DTO: {needle}")

def build_oi_analysis_batch(
    *, symbol: str | None = None, limit: int = 40, fo_batch: FoEnrichmentBatch | None = None
) -> OiAnalysisBatchV1:
    """OI Analysis snapshot: futures-only quadrant rows behind official gates."""
    fo = fo_batch if fo_batch is not None else _load_fo_batch()
    if fo is None or fo.parser_state != "PARSED_STRUCTURED" or not fo.artifact_hash:
        raise OiToolsNotReady(
            "WAIT_FO_LINEAGE",
            "No hash-proven FO bhavcopy lineage. Rooms stay empty rather than mixing snapshots.",
        )
    mwpl_map = _mwpl_percent_map()
    wanted = symbol.strip().upper() if symbol else None
    built: list[OiAnalysisRowV1] = []
    for row in sorted(fo.rows, key=lambda r: r.symbol):
        if wanted and row.symbol != wanted:
            continue
        if len(built) >= limit:
            break
        near = row.near_future
        if near is None or row.fo_state != "FUTURES_OK":
            continue
        prior_oi = near.open_interest - near.oi_change
        # Next/near OI share is a roll *label*. It does not mix two expiries
        # into this row's OI delta (A6 already isolated the near contract).
        roll_window = bool(row.rollover_ratio is not None and row.rollover_ratio > 0.5)
        quad = observation_quadrant(
            close=near.close,
            previous_close=near.previous_close,
            open_interest=near.open_interest,
            prior_open_interest=prior_oi,
            interval="EOD",
            same_expiry=True,
            roll_window=False,
        )
        gate = official_mwpl_state(oi_percent_of_mwpl=mwpl_map.get(row.symbol), in_ban_list=_ban(row.symbol))
        safety = _safety(row.symbol)
        matches = safety.get("matches") or []
        blockers = [
            b.code
            for b in evaluate_hard_blocks(symbol=row.symbol, in_ban_list=gate.in_ban_list is True)
        ]
        if gate.hard_block_code and gate.hard_block_code not in blockers:
            blockers.append(gate.hard_block_code)
        if safety.get("state") == "BLOCKED_SURVEILLANCE":
            public_state = "REJECT"
        elif blockers or not gate.can_guide_fno or quad.code is ObservationCode.UNKNOWN:
            public_state = "WAIT"
        else:
            public_state = "WATCH"
        built.append(
            OiAnalysisRowV1(
                symbol=row.symbol,
                expiry=near.expiry,
                close=near.close,
                previous_close=near.previous_close,
                price_change_pct=quad.price_change_pct,
                open_interest=near.open_interest,
                prior_open_interest=prior_oi,
                oi_change_pct=quad.oi_change_pct,
                volume_to_oi=(round(near.volume / near.open_interest, 4) if near.open_interest > 0 else None),
                observation_code=quad.code.value,
                legacy_code=quad.legacy_code,
                roll_window=roll_window,
                mwpl=MwplViewV1(
                    official_state=gate.official_state.value,
                    oi_percent_of_mwpl=gate.oi_percent_of_mwpl,
                    in_ban_list=gate.in_ban_list,
                    alert60_active=gate.alert60_active,
                    internal_band=gate.internal_band,
                ),
                surveillance_stage=(
                    "; ".join(f"{m.get('measure')}({m.get('stage')})" for m in matches) if matches else None
                ),
                public_state=public_state,
                blockers=tuple(blockers),
                interpretation=quad.interpretation,
                trader_read=_TRADER_READS.get(quad.code.value, ""),
                if_long_bias=_BIAS_READS.get(quad.code.value, ("", ""))[0],
                if_short_bias=_BIAS_READS.get(quad.code.value, ("", ""))[1],
                next_step=_next_step(public_state, quad.code.value, tuple(blockers), gate.official_state.value),
                activity_note=_activity_note(
                    round(near.volume / near.open_interest, 6) if near.open_interest > 0 else None
                ),
            ).validate_row()
        )
    batch = OiAnalysisBatchV1(
        data_date=fo.data_date,
        artifact_hash=fo.artifact_hash,
        row_count=len(built),
        columns_spec=COLUMNS_SPEC,
        rows=tuple(built),
        warnings=(
            "Observation codes are participation geometry, never institutional intent.",
            "Fixture demo strings are absent by construction; a hit means a wiring bug.",
            "rollWindow is next-month OI share, not a mixed-expiry OI delta.",
        ),
    )
    _assert_no_demo_strings(batch)
    return batch


def build_oi_tracker_batch(
    *,
    underlying: str | None = None,
    limit: int = 40,
    history: list[FoEnrichmentBatch] | None = None,
) -> OiTrackerBatchV1:
    """OI/PCR path over persisted FO runs (roll-aware window)."""
    runs = history if history is not None else list_fo_enrichment_history(30)
    series: dict[str, list[dict[str, Any]]] = {}
    for batch in runs:
        stamp = batch.data_date or ""
        for row in batch.rows:
            if row.near_future is None or row.fo_state != "FUTURES_OK":
                continue
            if row.near_future.open_interest <= 0:
                continue
            series.setdefault(row.symbol, []).append(
                {"dataDate": stamp, "oi": row.near_future.open_interest}
            )
    wanted = underlying.strip().upper() if underlying else None
    out_rows: list[OiTrackerRowV1] = []
    for sym in sorted(series):
        if wanted and sym != wanted:
            continue
        obs = [e for e in series[sym] if e["dataDate"]]
        obs.sort(key=lambda e: e["dataDate"])
        if len(obs) < 2:
            label, state = "UNKNOWN", "WAIT_PATH"
        else:
            delta = obs[-1]["oi"] - obs[0]["oi"]
            label = "RISING" if delta > 0 else "FALLING" if delta < 0 else "FLAT"
            state = "WAIT"
        pcr_open = _chain_pcr(sym, oldest=True)
        pcr_current = _chain_pcr(sym, oldest=False)
        if len(obs) >= 2 and pcr_open is None and pcr_current is None:
            state = "WAIT_CHAIN"
        out_rows.append(
            OiTrackerRowV1(
                underlying=sym,
                observations=len(obs),
                first_data_date=obs[0]["dataDate"] or None,
                last_data_date=obs[-1]["dataDate"] or None,
                first_oi=obs[0]["oi"],
                last_oi=obs[-1]["oi"],
                oi_path_label=label,
                pcr_open=pcr_open,
                pcr_current=pcr_current,
                public_state=state,
            )
        )
        if len(out_rows) >= limit:
            break
    return OiTrackerBatchV1(row_count=len(out_rows), rows=tuple(out_rows))


def _chain_pcr(underlying: str, *, oldest: bool) -> float | None:
    snaps = chain_snapshots(underlying=underlying, expiry=None, limit=200)
    if not snaps:
        return None
    chosen = snaps[-1] if oldest else snaps[0]
    rows = (chosen.get("payload") or {}).get("rows") or []
    ce = sum(float(r.get("openInterest") or 0) for r in rows if str(r.get("right")).upper() == "CE")
    pe = sum(float(r.get("openInterest") or 0) for r in rows if str(r.get("right")).upper() == "PE")
    return pcr_oi(put_oi=pe, call_oi=ce)


_CHAIN_READY_STATES = frozenset({"CHAIN_OK", "CHAIN_EOD_OI"})


def _require_chain_snaps(underlying: str, expiry: str) -> list[dict[str, Any]]:
    snaps = chain_snapshots(underlying=underlying, expiry=expiry, limit=2)
    if not any(s.get("qualityState") in _CHAIN_READY_STATES for s in snaps):
        raise OiToolsNotReady(
            "WAIT_CHAIN",
            "No quality-passed same-expiry chain snapshot for this underlying/expiry pair.",
        )
    return snaps


def _chain_parts(underlying: str, expiry: str, today: date | None = None) -> dict[str, Any]:
    snaps = _require_chain_snaps(underlying, expiry)
    newest_row = snaps[0]
    payload = newest_row.get("payload") or {}
    spot = newest_row.get("spot")
    if spot is None:
        spot = payload.get("spot")
    quotes = [StrikeQuote.model_validate(r) for r in (payload.get("rows") or [])]
    expected = int(payload.get("expectedStrikeCount") or len({q.strike for q in quotes}))
    quality = assess_chain(
        [q.model_dump(mode="json", by_alias=True) for q in quotes],
        expected_strike_count=max(expected, 1),
    )

    def prev_strike(role: str) -> float | None:
        if len(snaps) < 2:
            return None
        prev_rows = [StrikeQuote.model_validate(r) for r in ((snaps[1].get("payload") or {}).get("rows") or [])]
        right = "CE" if role == "CALL_WALL" else "PE"
        cands = [q for q in prev_rows if q.right == right]
        return max((q for q in cands), key=lambda q: q.open_interest).strike if cands else None

    call_wall, put_wall = walls(
        quotes,
        previous_walls={
            role: prev_strike(role)
            for role in ("CALL_WALL", "PUT_WALL")
            if prev_strike(role) is not None
        },
    )
    pain = max_pain_reference(quotes)
    exp_day = date.fromisoformat(expiry)
    context = expiry_context(exp_day, today=today or date.today())
    years = max(context.dte_calendar_days, 1) / 365.0
    gamma_map = (
        unsigned_cash_gamma_per_strike(quotes, forward=float(spot), years=years)
        if spot
        else {}
    )
    ladder: list[StrikeLadderRowV1] = []
    for q in sorted(quotes, key=lambda r: (r.strike, r.right)):
        mid = 0.5 * ((q.bid or 0) + (q.ask or 0)) if q.bid and q.ask else None
        spread_pct = round((q.ask - q.bid) / mid * 100, 4) if mid else None
        ladder.append(
            StrikeLadderRowV1(
                strike=q.strike,
                right=q.right,
                open_interest=q.open_interest,
                volume=q.volume,
                bid=q.bid,
                ask=q.ask,
                ltp=q.ltp,
                implied_volatility=q.implied_volatility,
                spread_pct=spread_pct,
                cash_gamma_proxy=gamma_map.get(q.strike),
            )
        )
    blockers = tuple(
        b.code
        for b in evaluate_hard_blocks(
            symbol=underlying,
            max_spread_pct=quality.max_spread_pct,
            spread_limit_pct=DEFAULT_SPREAD_LIMIT_PCT,
            stock_fno_itm_near_expiry=False,
        )
    )
    return {
        "quotes": quotes,
        "quality": quality,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "pain": pain,
        "context": context,
        "spot": spot,
        "years": years,
        "ladder": ladder,
        "blockers": blockers,
    }


def _wall_view(wall, role: str) -> WallViewV1:
    return WallViewV1(
        role=role,
        strike=wall.strike if wall else None,
        open_interest=wall.open_interest if wall else None,
        persistence_snapshots=wall.persistence_snapshots if wall else 1,
        first_known_at=wall.first_known_at if wall else None,
    )


def build_strike_explorer_batch(*, underlying: str, expiry: str) -> StrikeExplorerBatchV1:
    sym = underlying.strip().upper()
    parts = _chain_parts(sym, expiry.strip())
    quality = parts["quality"]
    eod_only = quality.state == "CHAIN_EOD_OI"
    return StrikeExplorerBatchV1(
        underlying=sym,
        expiry=expiry.strip(),
        quality_state=quality.state,
        completeness=quality.completeness,
        max_spread_pct=quality.max_spread_pct,
        ladder=tuple(parts["ladder"]),
        call_wall=_wall_view(parts["call_wall"], "CALL_WALL"),
        put_wall=_wall_view(parts["put_wall"], "PUT_WALL"),
        max_pain_reference=parts["pain"],
        blockers=parts["blockers"],
        state_ceiling="WAIT" if parts["blockers"] or eod_only else "WATCH",
    )


def build_expiry_range_batch(
    *, underlying: str, expiry: str, today: date | None = None
) -> ExpiryRangeBatchV1:
    sym = underlying.strip().upper()
    exp = expiry.strip()
    parts = _chain_parts(sym, exp, today=today)
    spot = float(parts["spot"]) if parts["spot"] else None
    quotes = parts["quotes"]

    def mid_of(q: StrikeQuote) -> float | None:
        if q.bid and q.ask:
            return 0.5 * (q.bid + q.ask)
        return q.ltp

    range_low = range_high = hero_zero = None
    if spot and quotes:
        atm = min((q.strike for q in quotes), key=lambda s: abs(s - spot))
        ce = next((q for q in quotes if q.strike == atm and q.right == "CE"), None)
        pe = next((q for q in quotes if q.strike == atm and q.right == "PE"), None)
        if ce is not None and pe is not None:
            ce_mid, pe_mid = mid_of(ce), mid_of(pe)
            if ce_mid is not None and pe_mid is not None:
                straddle = ce_mid + pe_mid
                range_low = round(spot - 0.8 * straddle, 2)
                range_high = round(spot + 0.8 * straddle, 2)
                ivs = [v for v in (ce.implied_volatility, pe.implied_volatility) if v]
                sigma = sum(ivs) / len(ivs) if ivs else 15.0
                hero_zero = hero_zero_guidance(
                    symbol=sym,
                    expiry=exp,
                    strike=float(atm),
                    right="CE",
                    spot=spot,
                    premium=ce_mid,
                    atm_straddle=straddle,
                    sigma=sigma,
                    years=parts["years"],
                    costs_total=round(ce_mid * 0.0015, 4),
                    blockers=parts["blockers"],
                    next_years=max(parts["years"] - 1.0 / (24.0 * 365.0), 0.0),
                )
    present = sum(
        1 for c in (range_low is not None, parts["pain"] is not None, parts["call_wall"], parts["put_wall"]) if c
    )
    ctx = parts["context"]
    return ExpiryRangeBatchV1(
        underlying=sym,
        expiry=exp,
        dte_calendar_days=ctx.dte_calendar_days,
        is_tuesday_expiry=ctx.is_tuesday,
        is_mega_expiry=ctx.is_mega_expiry,
        mega_stress_tag=ctx.mega_expiry_stress_tag,
        physical_block_active_from=ctx.physical_block_active_from,
        range_low=range_low,
        range_high=range_high,
        max_pain_reference=parts["pain"],
        agreement_fraction=round(present / 4, 4),
        hero_zero=hero_zero,
        blockers=parts["blockers"],
        state_ceiling="WAIT" if parts["blockers"] or parts["quality"].state == "CHAIN_EOD_OI" else "WATCH",
    )


_TRADER_READS: dict[str, str] = {
    "PRICE_UP_OI_UP": (
        "Price rose while futures positions EXPANDED: fresh positioning is leaning WITH the move. Interpretation, not proof of who is buying."
    ),
    "PRICE_UP_OI_DOWN": (
        "Price rose while futures positions SHRANK: an unwinding-style advance (exits, not a fresh attack). Such rallies often have weaker footing. Interpretation, not a fact."
    ),
    "PRICE_DOWN_OI_UP": (
        "Price fell while futures positions EXPANDED: pressure is building WITH the drop. Interpretation, not a fact."
    ),
    "PRICE_DOWN_OI_DOWN": (
        "Price fell while futures positions SHRANK: an unwinding-style decline (longs exiting, not a fresh attack). Can exhaust once the exit crowd thins. Interpretation, not a fact."
    ),
    "UNKNOWN": (
        "Not decodable this interval (identity, data or roll pollution). No read is available and none is invented."
    ),
}

_BIAS_READS: dict[str, tuple[str, str]] = {
    "PRICE_UP_OI_UP": (
        "SUPPORTS a long structure hypothesis: participation expanded with the rise.",
        "CONFLICTS with a short hypothesis: the rise carried fresh positioning.",
    ),
    "PRICE_UP_OI_DOWN": (
        "WEAKENS a long hypothesis: the rally ran on shrinking OI (unwind, not fresh buying). Inspect before adding.",
        "CONTEXT for a short thesis: the advance lacked fresh positioning, but price still rose against you. Do not fade on OI alone.",
    ),
    "PRICE_DOWN_OI_UP": (
        "CONFLICTS with a long hypothesis: the fall carried fresh positioning against price.",
        "SUPPORTS a short structure hypothesis: pressure expanded with the drop.",
    ),
    "PRICE_DOWN_OI_DOWN": (
        "CONTEXT for a long thesis: the decline lacked fresh positioning, but price still fell. OI alone is not a bottom call.",
        "WEAKENS a short hypothesis: the drop ran on shrinking OI (unwind, not a fresh attack).",
    ),
    "UNKNOWN": (
        "No bias read available this interval.",
        "No bias read available this interval.",
    ),
}


def _activity_note(volume_to_oi: float | None) -> str | None:
    if volume_to_oi is None:
        return None
    pct = volume_to_oi * 100.0
    if pct < 1.0:
        return f"Thin activity vs outstanding positions ({pct:.2f}% of OI traded) - moves carry less conviction signal."
    if pct < 10.0:
        return f"Moderate activity vs outstanding positions ({pct:.2f}% of OI traded)."
    return f"Active session vs outstanding positions ({pct:.2f}% of OI traded)."


def _next_step(public_state: str, code: str, blockers: tuple[str, ...], gate_state: str) -> str:
    if "HARD_BLOCK_BAN_ADD" in blockers or gate_state == "BAN":
        return (
            "STOP here for the derivative story: scrip is banned / over the MWPL cap. "
            "Only offsetting is legal; read cash structure instead."
        )
    if gate_state == "MWPL_MISSING":
        return "MWPL unproven - treat F&O reads as WAIT. Fix the official artifact before trusting participation."
    if code == "UNKNOWN":
        return "Fix data alignment first (same expiry/instrument, prior OI, roll window). No trade read exists yet."
    if public_state == "REJECT":
        return "Surveillance/reject state outranks OI. Work the cash structure only."
    return (
        "1) Take your closed-bar structure call FIRST (this row never replaces it). "
        "2) Read IF-LONG / IF-SHORT above as agreement or friction. "
        "3) Confirm persistence in OI Tracker (one snapshot is not a path). "
        "4) Only then look at Strike walls. Still not an order."
    )
