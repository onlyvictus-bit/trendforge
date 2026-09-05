"""R5 live adjusted closed-bar structure over exact persisted R1/R2 lineage.

This stage is research-only. It can surface deterministic breakout, relative-volume
and narrow-range facts, but live rows remain WAIT or REJECT. No source activation,
trade geometry, quantity, probability or broker behavior exists here.

R5 reads A2 identity and A4 bars. Its corporate-action authority is the R14
ca-join batch: raw A4 vintage lists are storage, not the live join. R5 cannot
run without a hash-matched R14 batch. R4 cannot unlock R5 CONFIRMED.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time
from math import isfinite
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ..source_contracts import SourceResult
from .attention_order import InventoryDiscoveryV1, latest_attention_order
from .cash_a1_staging import CashStagingBatch, latest_cash_staging
from .cash_a2_identity import CashIdentityBatch, latest_cash_identity
from .cash_a4_history import (
    CashHistoryBatch,
    CashRawSessionBar,
    latest_cash_history,
    list_raw_bars,
)
from .contracts import (
    BarIdentity,
    DataMode,
    EvidenceClaim,
    EvidenceDirection,
    InstrumentIdentity,
    NormalizedFact,
    SelectionState,
    StateCeiling,
    stable_id,
)
from .index_a5_context import CashContextBatch, latest_cash_context
from .inventory_source_bundle import (
    InventorySourceBundleV1,
    latest_inventory_source_bundle,
)
from .r14_live import R14CaJoinBatchV1, R14CaJoinRowV1, latest_r14_ca_join
from .r4_live import latest_r4_identity_pin
from .store import latest_selection_payload, persist_selection_payload
from .structure import (
    ClosedBar,
    StructureMetrics,
    StructureProfile,
    analyze_closed_bar_structure,
)

SCHEMA_VERSION = "trendforge.structure-batch.v2"
PROFILE_ID = "PRF-R5-EOD-STRUCTURE"
PROFILE_VERSION = "1.1.0"
IST = ZoneInfo("Asia/Kolkata")
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class R5StructureRowV1(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    symbol: str
    instrument_id: str
    r2_public_state: SelectionState
    structure_state: SelectionState
    state_ceiling: StateCeiling = StateCeiling.WAIT
    evidence_direction: EvidenceDirection
    display_order: int = Field(gt=0)
    source_mode: str
    history_count: int = Field(ge=0)
    ca_state: str
    index_context_state: str
    detected_setups: tuple[str, ...] = ()
    gate_codes: tuple[str, ...]
    why_wait: tuple[str, ...]
    metrics: StructureMetrics | None = None
    claim_ids: tuple[str, ...] = ()
    claims: tuple[EvidenceClaim, ...] = ()
    facts: tuple[NormalizedFact, ...] = ()
    source_fact_id: str | None = None
    can_support_confirmed: bool = False

    @model_validator(mode="after")
    def enforce_confirmed_safety(self) -> "R5StructureRowV1":
        if any(
            claim.can_support_confirmed or claim.state_ceiling is StateCeiling.CONFIRMED
            for claim in self.claims
        ):
            raise ValueError("R5 rows cannot carry confirming claims")
        if self.structure_state is SelectionState.CONFIRMED:
            if not self.can_support_confirmed:
                raise ValueError("cannot emit CONFIRMED when can_support_confirmed is False")
            if any(code.startswith("WAIT_") or code.startswith("REJECT_") for code in self.gate_codes):
                raise ValueError("cannot emit CONFIRMED with blocking gate codes")
            if not self.detected_setups:
                raise ValueError("cannot emit CONFIRMED without detected setups")
        return self


class R5StructureBatchV1(BaseModel):
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
    r14_run_hash: str | None = None
    collector_run_id: str
    cash_pipeline_run_id: str
    cash_pipeline_fingerprint: str
    permission_fingerprint: str
    trading_date: str
    decision_at: datetime
    state_ceiling: StateCeiling = StateCeiling.WAIT
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    acceptance_ceiling: str = "LIVE_WAIT_REJECT_ONLY"
    universe_count: int = Field(ge=0)
    confirmed_count: int = Field(ge=0, default=0)
    wait_count: int = Field(ge=0)
    reject_count: int = Field(ge=0)
    persisted: bool = False
    rows: tuple[R5StructureRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_live_batch(self) -> "R5StructureBatchV1":
        if self.universe_count != len(self.rows):
            raise ValueError("R5 universe count does not match rows")
        if self.wait_count + self.reject_count != len(self.rows):
            raise ValueError("R5 state counts do not match rows")
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("R5 cannot activate sources or unlock CONFIRMED")
        if any(row.structure_state is SelectionState.CONFIRMED for row in self.rows):
            raise ValueError("R5 live rows cannot be CONFIRMED")
        return self


def _profile(direction: EvidenceDirection) -> StructureProfile | None:
    if direction not in {EvidenceDirection.BULLISH, EvidenceDirection.BEARISH}:
        return None
    return StructureProfile(
        profile_id=f"{PROFILE_ID}-{direction.value}",
        profile_version=PROFILE_VERSION,
        direction=direction,
        prior_range_bars=20,
        acceptance_bars=1,
        tolerance_bps=0,
        volume_baseline_bars=20,
        min_rvol=1.5,
        nr_window=7,
        session_calendar_version="NSE-CM-V1",
    )


def _wait_ca_gate(join_status: str) -> str:
    specific = {
        "CONFLICT": "WAIT_CA_CONFLICT",
        "IDENTITY_BREAK": "WAIT_CA_IDENTITY_BREAK",
        "WAIT_DETAILS": "WAIT_CA_WAIT_DETAILS",
    }
    return specific.get(join_status, "WAIT_CA_UNRESOLVED")


def _r14_factors(trade_date: date, ca_row: R14CaJoinRowV1) -> tuple[float, float]:
    """Cumulative DAT-022 price and volume factors for one bar."""
    price_factor = 1.0
    volume_factor = 1.0
    for event in ca_row.joined_events:
        if trade_date < event.effective_date:
            price_factor *= event.adjustment_factor
            if event.affects_volume:
                volume_factor *= event.adjustment_factor
    return price_factor, volume_factor


def _closed_bars(
    *,
    instrument: InstrumentIdentity,
    raw_bars: list[CashRawSessionBar],
    decision_at: datetime,
    ca_row: R14CaJoinRowV1,
) -> tuple[tuple[ClosedBar, ...], tuple[str, ...]]:
    if ca_row.ca_state == "WAIT_CA":
        return (), (_wait_ca_gate(ca_row.join_status),)
    if any(
        not isfinite(event.adjustment_factor) or event.adjustment_factor <= 0
        for event in ca_row.joined_events
    ):
        return (), ("WAIT_CA_UNRESOLVED",)
    if ca_row.ca_state == "ADJUSTED" and not ca_row.adjusted_series_id:
        return (), ("WAIT_ADJUSTED_SERIES_MISSING",)

    adjustment_version = (
        f"ADJUSTED:{ca_row.adjusted_series_id}"
        if ca_row.ca_state == "ADJUSTED"
        else f"NO_CA:{ca_row.raw_series_id}"
    )
    bars: list[ClosedBar] = []
    for raw in raw_bars:
        if raw.instrument_id != instrument.instrument_id:
            return (), ("WAIT_BAR_IDENTITY",)
        if raw.open is None or raw.high is None or raw.low is None:
            return (), ("WAIT_OHLC_INCOMPLETE",)
        price_factor, volume_factor = _r14_factors(raw.trade_date, ca_row)
        if price_factor <= 0 or volume_factor <= 0:
            return (), ("WAIT_CA_UNRESOLVED",)
        session_open = datetime.combine(raw.trade_date, time(9, 15), tzinfo=IST)
        session_close = datetime.combine(raw.trade_date, time(15, 30), tzinfo=IST)
        adjusted_volume = raw.volume / volume_factor
        bars.append(
            ClosedBar(
                identity=BarIdentity.create(
                    instrument_id=instrument.instrument_id,
                    timeframe="1D",
                    session_id=f"NSE-CM:{raw.trade_date.isoformat()}",
                    open_time=session_open,
                    close_time=session_close,
                    is_closed=session_close <= decision_at.astimezone(IST),
                    adjustment_version=adjustment_version,
                    raw_hash=raw.artifact_hash,
                    source_mode=DataMode.EOD_RESEARCH,
                ),
                open=float(raw.open) * price_factor,
                high=float(raw.high) * price_factor,
                low=float(raw.low) * price_factor,
                close=float(raw.close) * price_factor,
                volume=float(adjusted_volume),
            )
        )
    return tuple(bars), ()


# R13 reuses the exact R5/R14 point-in-time adjustment implementation.
build_adjusted_closed_bars = _closed_bars


def _index_state(context: CashContextBatch | None, trading_date: str) -> tuple[str, str | None]:
    if context is None:
        return "MISSING", "WAIT_INDEX_CONTEXT_MISSING"
    if (
        context.index.parser_state != "PARSED_STRUCTURED"
        or context.index.data_date != trading_date
        or context.index.nifty50_close is None
    ):
        return context.index.parser_state, "WAIT_INDEX_CONTEXT_MISSING"
    return "CURRENT", None


def _safe_source_result(staging: CashStagingBatch) -> SourceResult:
    return staging.source_result.model_copy(
        update={"can_support_confirmed": False, "state_ceiling": "WAIT"}
    )


def _row_without_analysis(
    *,
    r2,
    instrument: InstrumentIdentity,
    state: SelectionState,
    source_mode: str,
    history_count: int,
    ca_state: str,
    index_state: str,
    codes: list[str],
) -> R5StructureRowV1:
    reasons = tuple(dict.fromkeys(codes + ["R5_LIVE_WAIT_CEILING"]))
    return R5StructureRowV1(
        candidate_id=r2.candidate_id,
        symbol=r2.symbol,
        instrument_id=instrument.instrument_id,
        r2_public_state=r2.public_state,
        structure_state=state,
        state_ceiling=StateCeiling.WAIT,
        evidence_direction=r2.evidence_direction,
        display_order=r2.display_order,
        source_mode=source_mode,
        history_count=history_count,
        ca_state=ca_state,
        index_context_state=index_state,
        gate_codes=reasons,
        why_wait=reasons,
    )


def build_r5_structure_batch(
    *,
    bundle: InventorySourceBundleV1 | None = None,
    attention: InventoryDiscoveryV1 | None = None,
    identity: CashIdentityBatch | None = None,
    history: CashHistoryBatch | None = None,
    staging: CashStagingBatch | None = None,
    context: CashContextBatch | None = None,
    ca_join: R14CaJoinBatchV1 | None = None,
    decision_at: datetime | None = None,
) -> R5StructureBatchV1:
    r1 = bundle or latest_inventory_source_bundle()
    r2 = attention or latest_attention_order()
    a2 = identity or latest_cash_identity()
    a4 = history or latest_cash_history()
    a1 = staging or latest_cash_staging()
    a5 = context if context is not None else latest_cash_context()
    if r1 is None or r2 is None:
        raise ValueError("WAIT_R5_R1_R2_NOT_READY")
    if (
        r2.r1_bundle_id != r1.bundle_id
        or r2.r1_bundle_hash != r1.bundle_hash
        or r2.collector_run_id != r1.collector_run_id
        or r2.cash_pipeline_fingerprint != r1.cash_pipeline_fingerprint
        or r2.permission_fingerprint != r1.permission_fingerprint
    ):
        raise ValueError("WAIT_R5_LINEAGE_MISMATCH")
    if decision_at is not None and (
        decision_at.tzinfo is None or decision_at.utcoffset() is None
    ):
        raise ValueError("decision_at must be timezone-aware")
    at = decision_at or r2.built_at
    if a1 is None:
        raise ValueError("WAIT_R5_A1_NOT_READY")
    ca_join_batch = ca_join if ca_join is not None else latest_r14_ca_join()
    if (
        ca_join_batch is None
        or ca_join_batch.r1_bundle_hash != r1.bundle_hash
        or ca_join_batch.r2_run_hash != r2.run_hash
    ):
        raise ValueError("WAIT_R5_R14_JOIN_NOT_READY")
    r4_pin = latest_r4_identity_pin()
    if (
        r4_pin is not None
        and r4_pin.r1_bundle_hash == r1.bundle_hash
        and r4_pin.r2_run_hash == r2.run_hash
        and ca_join_batch.r4_run_hash != r4_pin.run_hash
    ):
        raise ValueError("WAIT_R5_R14_JOIN_NOT_READY")

    stock_by_candidate = {item.candidate_id: item for item in r1.stock_records}
    identity_by_symbol = {
        item.instrument.symbol: item for item in (a2.rows if a2 is not None else ())
    }
    history_by_symbol = {
        item.symbol: item for item in (a4.rows if a4 is not None else ())
    }
    ca_row_by_symbol = {row.symbol.upper(): row for row in ca_join_batch.rows}
    index_state, index_wait = _index_state(a5, r1.trading_date.isoformat())
    source_result = _safe_source_result(a1)
    rows: list[R5StructureRowV1] = []

    for attention_row in r2.rows:
        stock = stock_by_candidate.get(attention_row.candidate_id)
        identity_row = identity_by_symbol.get(attention_row.symbol)
        if stock is None or identity_row is None:
            placeholder = InstrumentIdentity.create(
                exchange="NSE",
                segment="EQ",
                symbol=attention_row.symbol,
                series="EQ",
            )
            rows.append(
                _row_without_analysis(
                    r2=attention_row,
                    instrument=placeholder,
                    state=(
                        SelectionState.REJECT
                        if attention_row.public_state is SelectionState.REJECT
                        else SelectionState.WAIT
                    ),
                    source_mode="OFFICIAL_LAST_GOOD",
                    history_count=0,
                    ca_state="MISSING",
                    index_state=index_state,
                    codes=["WAIT_A2_CANONICAL_IDENTITY"],
                )
            )
            continue

        instrument = identity_row.instrument
        codes: list[str] = []
        if stock.instrument_id != instrument.instrument_id:
            codes.append("WAIT_A2_IDENTITY_MISMATCH")
        history_row = history_by_symbol.get(attention_row.symbol)
        ca_row = ca_row_by_symbol.get(attention_row.symbol.upper())
        history_lineage_ok = (
            a4 is not None
            and a2 is not None
            and a4.identity_batch_id == a2.batch_id
            and history_row is not None
            and history_row.instrument_id == instrument.instrument_id
        )
        if not history_lineage_ok:
            codes.append("WAIT_A4_LINEAGE_MISMATCH")
        if index_wait:
            codes.append(index_wait)
        if attention_row.public_state is SelectionState.REJECT:
            codes.append("R2_PUBLIC_REJECT")
            rows.append(
                _row_without_analysis(
                    r2=attention_row,
                    instrument=instrument,
                    state=SelectionState.REJECT,
                    source_mode="OFFICIAL_LAST_GOOD",
                    history_count=0,
                    ca_state=(
                        ca_row.ca_state
                        if ca_row is not None
                        else history_row.ca_state
                        if history_row
                        else "MISSING"
                    ),
                    index_state=index_state,
                    codes=codes,
                )
            )
            continue
        if not history_lineage_ok or history_row is None:
            rows.append(
                _row_without_analysis(
                    r2=attention_row,
                    instrument=instrument,
                    state=SelectionState.WAIT,
                    source_mode="OFFICIAL_LAST_GOOD",
                    history_count=0,
                    ca_state="MISSING",
                    index_state=index_state,
                    codes=codes,
                )
            )
            continue
        if ca_row is None:
            codes.append("WAIT_R14_ROW_MISSING")
            rows.append(
                _row_without_analysis(
                    r2=attention_row,
                    instrument=instrument,
                    state=SelectionState.WAIT,
                    source_mode="OFFICIAL_LAST_GOOD",
                    history_count=0,
                    ca_state="MISSING",
                    index_state=index_state,
                    codes=codes,
                )
            )
            continue

        raw = list_raw_bars(instrument.symbol, through=r1.trading_date)
        bars, bar_waits = _closed_bars(
            instrument=instrument,
            raw_bars=raw,
            decision_at=at,
            ca_row=ca_row,
        )
        codes.extend(bar_waits)
        profile = _profile(attention_row.evidence_direction)
        if profile is None:
            codes.append("WAIT_DIRECTION_UNRESOLVED")
        if not bars:
            codes.append("WAIT_HISTORY_NOT_READY")
        blocking_codes = [code for code in codes if code != "WAIT_INDEX_CONTEXT_MISSING"]
        if blocking_codes or profile is None:
            rows.append(
                _row_without_analysis(
                    r2=attention_row,
                    instrument=instrument,
                    state=SelectionState.WAIT,
                    source_mode="OFFICIAL_LAST_GOOD",
                    history_count=len(raw),
                    ca_state=history_row.ca_state,
                    index_state=index_state,
                    codes=codes,
                )
            )
            continue

        analysis = analyze_closed_bar_structure(
            instrument=instrument,
            bars=bars,
            source_result=source_result,
            profile=profile,
            decision_at=at,
        )
        analysis_codes = [gate.code for gate in analysis.gate_results]
        setups: list[str] = []
        if analysis.metrics.accepted:
            setups.append("CLOSED_BAR_BREAKOUT")
        if analysis.metrics.narrow_range:
            setups.append(f"NR{profile.nr_window}")
        if (
            analysis.metrics.relative_volume is not None
            and analysis.metrics.relative_volume >= profile.min_rvol
        ):
            setups.append("RVOL")

        reasons = tuple(
            dict.fromkeys(analysis_codes + codes + ["R5_LIVE_WAIT_CEILING"])
        )
        rows.append(
            R5StructureRowV1(
                candidate_id=attention_row.candidate_id,
                symbol=attention_row.symbol,
                instrument_id=instrument.instrument_id,
                r2_public_state=attention_row.public_state,
                structure_state=SelectionState.WAIT,
                state_ceiling=StateCeiling.WAIT,
                evidence_direction=attention_row.evidence_direction,
                display_order=attention_row.display_order,
                source_mode="OFFICIAL_LAST_GOOD",
                history_count=len(bars),
                ca_state=ca_row.ca_state,
                index_context_state=index_state,
                detected_setups=tuple(setups),
                gate_codes=reasons,
                why_wait=reasons,
                metrics=analysis.metrics,
                claim_ids=tuple(claim.claim_id for claim in analysis.claims),
                claims=tuple(analysis.claims),
                facts=(analysis.fact,),
                source_fact_id=analysis.fact.fact_id,
                can_support_confirmed=False,
            )
        )

    identity_payload = {
        "r1BundleHash": r1.bundle_hash,
        "r2RunHash": r2.run_hash,
        "r14RunHash": ca_join_batch.run_hash,
        "profileVersion": PROFILE_VERSION,
        "decisionAt": at.isoformat(),
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return R5StructureBatchV1(
        run_id=stable_id("r5-structure", r1.bundle_id, r2.run_id, run_hash),
        run_hash=run_hash,
        r1_bundle_id=r1.bundle_id,
        r1_bundle_hash=r1.bundle_hash,
        r2_run_id=r2.run_id,
        r2_run_hash=r2.run_hash,
        r14_run_id=ca_join_batch.run_id,
        r14_run_hash=ca_join_batch.run_hash,
        collector_run_id=r1.collector_run_id,
        cash_pipeline_run_id=r1.cash_pipeline_run_id,
        cash_pipeline_fingerprint=r1.cash_pipeline_fingerprint,
        permission_fingerprint=r1.permission_fingerprint,
        trading_date=r1.trading_date.isoformat(),
        decision_at=at,
        can_unlock_confirmed=False,
        acceptance_ceiling="LIVE_WAIT_REJECT_ONLY",
        universe_count=len(rows),
        confirmed_count=0,
        wait_count=sum(row.structure_state is SelectionState.WAIT for row in rows),
        reject_count=sum(row.structure_state is SelectionState.REJECT for row in rows),
        rows=tuple(rows),
        warnings=(
            "R5 structure is deterministic research evidence, not win probability.",
        ),
    )


def persist_r5_structure_batch(value: R5StructureBatchV1) -> R5StructureBatchV1:
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
                row.structure_state.value,
                row.model_dump(mode="json", by_alias=True),
            )
            for row in stored.rows
        ),
    )
    return stored


def latest_r5_structure_batch() -> R5StructureBatchV1 | None:
    payload = latest_selection_payload(PROFILE_ID)
    return R5StructureBatchV1.model_validate(payload) if payload is not None else None

