"""Shared overlay fixtures: a hash-matched R1->R5 spine plus official MTO rows.

Test support only; never imported by production code.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from typing import Any

from trendforge_api import storage
from trendforge_api.models import SourceParseResult
from trendforge_api.selection.attention_order import (
    AttentionRowV1,
    InventoryDiscoveryV1,
    persist_attention_order,
)
from trendforge_api.selection.cash_a1_staging import CashStagingBatch
from trendforge_api.selection.cash_a2_identity import (
    CashIdentityBatch,
    CashIdentityRow,
    RestrictionAssessment,
    latest_cash_identity,
    persist_cash_identity,
)
from trendforge_api.selection.cash_a4_history import (
    CashHistoryBatch,
    CashHistoryRow,
    CashRawSessionBar,
    ParticipationBaseline,
    _store_raw_bar,
)
from trendforge_api.selection.contracts import (
    EvidenceDirection,
    InstrumentIdentity,
    NormalizedFact,
    PointInTimeLineage,
    SelectionState,
)
from trendforge_api.selection.index_a5_context import CashContextBatch, IndexContext
from trendforge_api.selection.inventory_source_bundle import (
    InventorySourceBundleV1,
    StockEvidenceRecordV1,
    persist_inventory_source_bundle,
)
from trendforge_api.selection.r14_live import (
    build_r14_ca_join,
    persist_r14_ca_join,
)
from trendforge_api.selection.r4_live import build_r4_identity_pin, persist_r4_identity_pin
from trendforge_api.selection.r5_live import (
    build_r5_structure_batch,
    persist_r5_structure_batch,
)
from trendforge_api.source_contracts import SourceResult, SourceResultState, SourceRole

TRADING_DATE = date(2026, 8, 14)
DECISION_AT = datetime(2026, 8, 14, 17, 0, tzinfo=UTC)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def store_mto_parse_result(
    *,
    data_date: date,
    parsed_at: datetime,
    rows: list[dict[str, Any]],
    parser_state: str = "PARSED_STRUCTURED",
    snapshot_id: int = 1,
) -> SourceParseResult:
    return storage.save_source_parse_result(
        SourceParseResult(
            source_key="nse_mto_delivery",
            snapshot_id=snapshot_id,
            parser_state=parser_state,
            data_date=data_date.isoformat(),
            record_count=len(rows),
            summary="fixture MTO delivery rows",
            output={"dateSource": "FILENAME", "rows": rows, "records": rows},
            error=None,
            parsed_at=parsed_at.isoformat(),
        )
    )


def mto_row(symbol: str, pct: float, *, series: str = "EQ") -> dict[str, Any]:
    return {
        "symbol": symbol.upper(),
        "series": series,
        "qty_traded": 100000,
        "deliverable_qty": int(100000 * pct / 100),
        "delivery_pct": pct,
    }


def store_flat_history(instrument: InstrumentIdentity, *, days: int = 22) -> None:
    first = TRADING_DATE - timedelta(days=days - 1)
    for index in range(days):
        trade_date = first + timedelta(days=index)
        _store_raw_bar(
            CashRawSessionBar(
                bar_id=f"hvb-flat-{instrument.symbol}-{index}",
                instrument_id=instrument.instrument_id,
                symbol=instrument.symbol,
                trade_date=trade_date,
                artifact_hash=_hash(f"hvb-bar-{trade_date}"),
                series_id="raw-series",
                open=99.5,
                high=100.5,
                low=99.0,
                close=100.0,
                previous_close=100.0,
                volume=1000.0,
                traded_value=100000.0,
            )
        )


def store_breakout_history(instrument: InstrumentIdentity, *, days: int = 22) -> None:
    first = TRADING_DATE - timedelta(days=days - 1)
    previous = 100.0
    for index in range(days):
        trade_date = first + timedelta(days=index)
        close = 110.0 if index == days - 1 else 100.0 + index * 0.1
        high = 111.0 if index == days - 1 else close + 0.5
        _store_raw_bar(
            CashRawSessionBar(
                bar_id=f"hvb-bo-{instrument.symbol}-{index}",
                instrument_id=instrument.instrument_id,
                symbol=instrument.symbol,
                trade_date=trade_date,
                artifact_hash=_hash(f"hvb-bo-bar-{trade_date}"),
                series_id="raw-series",
                open=close - 0.2,
                high=high,
                low=close - 0.5,
                close=close,
                previous_close=previous,
                volume=2500 if index == days - 1 else 1000,
                traded_value=close * (2500 if index == days - 1 else 1000),
            )
        )
        previous = close


def persist_overlay_lineage(
    tmp_path,
    monkeypatch,
    *,
    symbol: str = "HVBTEST",
    r2_state=SelectionState.WATCH,
    with_structure: bool = True,
    with_history: bool = True,
) -> dict[str, Any]:
    """Persist a full hash-matched R1/R2/R4/R14(/R5) spine and return the parts."""
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "hybrid-overlay.db")
    storage._INITIALIZED_DB_PATHS.clear()

    instrument = InstrumentIdentity.create(
        exchange="NSE",
        segment="EQ",
        symbol=symbol if not symbol.isdigit() else "RELIANCE",
        series="EQ",
        isin="INE000H01001",
    )
    lineage = PointInTimeLineage(
        event_time=DECISION_AT - timedelta(hours=2),
        published_at=DECISION_AT - timedelta(hours=1),
        received_at=DECISION_AT,
        available_at=DECISION_AT - timedelta(minutes=30),
        retrieved_at=DECISION_AT,
        revision_id="r1",
        artifact_hash=_hash("latest-cash"),
    )
    fact = NormalizedFact.create(
        instrument_id=instrument.instrument_id,
        source_id="nse_bhavcopy_eod",
        dataset_root="NSE_CASH_EOD",
        business_keys={"symbol": instrument.symbol, "trade_date": TRADING_DATE.isoformat()},
        data_date=TRADING_DATE,
        lineage=lineage,
        quality_state="STRUCTURED_OK",
        payload={"symbol": instrument.symbol, "close": 110.0},
    )
    identity = CashIdentityBatch(
        batch_id="a2-batch-hvb",
        staging_result_id="a1-result-hvb",
        calendar_state="OPEN",
        restriction=RestrictionAssessment(
            source_id="nse_fno_ban",
            proven=True,
            can_veto=True,
            state="READY",
            reason="fixture empty ban list",
            data_date=TRADING_DATE.isoformat(),
            artifact_hash=_hash("ban"),
        ),
        fact_count=1,
        rows=(
            CashIdentityRow(
                instrument=instrument,
                fact=fact,
                public_state=SelectionState.WAIT,
                gates=(),
            ),
        ),
    )
    stock = StockEvidenceRecordV1(
        candidate_id=f"candidate-{symbol}",
        symbol=symbol,
        instrument_id=instrument.instrument_id,
        fact_id=fact.fact_id,
        public_state=r2_state,
        evidence_direction=EvidenceDirection.BULLISH,
        research_class="CASH_RESEARCH",
        why_visible="Current official cash row.",
        why_not_confirmed=("SOURCE_ACTIVATION_FALSE",),
        attempted_sources=("nse_bhavcopy_eod",),
        completed_sources=("nse_bhavcopy_eod",),
        valid_empty_sources=(),
        failed_sources=(),
        not_attempted_sources=(),
        family_coverage={"PARTICIPATION": "AVAILABLE"},
        dataset_root_ids=("NSE_CASH_EOD",),
        supporting_claims=(),
        opposing_claims=(),
        cheap_features={
            "returnPercentile": 0.9,
            "volumePercentile": 0.9,
            "turnoverPercentile": 0.9,
        },
        source_clock={
            "nse_bhavcopy_eod": {
                "usabilityState": "USABLE_CURRENT",
                "dataDate": TRADING_DATE.isoformat(),
            }
        },
        lineage={"artifactHash": lineage.artifact_hash},
        restriction_state="READY",
        completeness=1.0,
    )
    bundle = InventorySourceBundleV1(
        bundle_id="r1-bundle-hvb",
        bundle_hash=_hash("r1-hvb"),
        collector_run_id="collector-hvb",
        cash_pipeline_run_id="cash-hvb",
        cash_pipeline_fingerprint=_hash("pipeline-hvb"),
        permission_fingerprint=_hash("permission-hvb"),
        snapshot_bundle_id="snapshot-hvb",
        trading_date=TRADING_DATE,
        built_at=DECISION_AT,
        registry_sha256=_hash("registry"),
        source_contract_count=0,
        stock_record_count=1,
        stage_states={"C1": "COMPLETED"},
        source_records=(),
        stock_records=(stock,),
    )
    attention = InventoryDiscoveryV1(
        run_id="r2-run-hvb",
        run_hash=_hash("r2-hvb"),
        r1_bundle_id=bundle.bundle_id,
        r1_bundle_hash=bundle.bundle_hash,
        collector_run_id=bundle.collector_run_id,
        cash_pipeline_run_id=bundle.cash_pipeline_run_id,
        cash_pipeline_fingerprint=bundle.cash_pipeline_fingerprint,
        permission_fingerprint=bundle.permission_fingerprint,
        snapshot_bundle_id=bundle.snapshot_bundle_id,
        trading_date=TRADING_DATE.isoformat(),
        built_at=DECISION_AT,
        universe_count=1,
        watch_count=1 if r2_state is SelectionState.WATCH else 0,
        wait_count=1 if r2_state is SelectionState.WAIT else 0,
        reject_count=1 if r2_state is SelectionState.REJECT else 0,
        rows=(
            AttentionRowV1(
                candidate_id=stock.candidate_id,
                symbol=symbol,
                public_state=r2_state,
                evidence_direction=EvidenceDirection.BULLISH,
                display_order=1,
                attention_rank=1 if r2_state is SelectionState.WATCH else None,
                attention_priority=0.6 if r2_state is SelectionState.WATCH else None,
                attention_band="MEDIUM" if r2_state is SelectionState.WATCH else "UNRANKED",
                supporting_families=("CASH_SESSION_ROOT",),
                opposing_claims=(),
                missing_evidence=(),
                conflicts=(),
                completeness=1.0,
                freshness="CURRENT",
                source_quality="OFFICIAL_STRUCTURED",
                restriction_state="READY",
                why_visible=stock.why_visible,
                why_not_confirmed=stock.why_not_confirmed,
                lineage=stock.lineage,
                dataset_root_ids=stock.dataset_root_ids,
            ),
        ),
    )

    pin = build_r4_identity_pin(bundle=bundle, attention=attention, identity=identity)
    ca_join = build_r14_ca_join(
        bundle=bundle,
        attention=attention,
        identity=identity,
        pin=pin,
        observations=[],
        vintages=[],
        decision_at=DECISION_AT,
    )

    structure = None
    if with_structure:
        if with_history:
            store_breakout_history(instrument)
        history_row = CashHistoryRow(
            symbol=symbol,
            instrument_id=instrument.instrument_id,
            raw_series_id="raw-series",
            ca_state="NONE",
            baseline=ParticipationBaseline(
                session_count=20,
                median_volume=1000,
                median_turnover=100000,
                median_range_pct=0.02,
                complete=True,
                reason="fixture",
            ),
            public_note="No visible corporate action.",
        )
        history = CashHistoryBatch(
            batch_id="a4-batch-hvb",
            identity_batch_id=identity.batch_id,
            decision_at=DECISION_AT,
            raw_bar_count=22,
            row_count=1,
            rows=(history_row,),
        )
        source_result = SourceResult(
            source_id="nse_bhavcopy_eod",
            contract_version="a1-staging-1",
            role=SourceRole.OFFICIAL_GATE,
            state=SourceResultState.STRUCTURED_OK,
            record_count=1,
            data_date=TRADING_DATE,
            published_at=DECISION_AT - timedelta(hours=1),
            received_at=DECISION_AT,
            available_at=DECISION_AT - timedelta(minutes=30),
            retrieved_at=DECISION_AT,
            schema_version="fixture",
            parser_version="fixture",
            revision_id="r1",
            artifact_hash=_hash("latest-cash"),
            freshness="FRESH",
            can_support_confirmed=False,
            state_ceiling="WAIT",
        )
        staging = CashStagingBatch(
            result_id=identity.staging_result_id,
            source_result=source_result,
            row_count=1,
            rows=({"symbol": symbol},),
        )
        context = CashContextBatch(
            batch_id="a5-batch-hvb",
            index=IndexContext(
                contract_digest=_hash("index-contract"),
                parser_state="PARSED_STRUCTURED",
                data_date=TRADING_DATE.isoformat(),
                artifact_hash=_hash("index"),
                nifty50_close=25000,
                registry_note="fixture official index context",
            ),
            row_count=0,
            rows=(),
        )
        structure = build_r5_structure_batch(
            bundle=bundle,
            attention=attention,
            identity=identity,
            history=history,
            staging=staging,
            context=context,
            ca_join=ca_join,
            decision_at=DECISION_AT,
        )

    persist_inventory_source_bundle(bundle)
    persist_attention_order(attention)
    existing_identity = latest_cash_identity()
    if existing_identity is None or existing_identity.batch_id != identity.batch_id:
        persist_cash_identity(identity)
    persist_r4_identity_pin(pin)
    persist_r14_ca_join(ca_join)
    if structure is not None:
        persist_r5_structure_batch(structure)

    return {
        "instrument": instrument,
        "identity": identity,
        "bundle": bundle,
        "attention": attention,
        "pin": pin,
        "ca_join": ca_join,
        "structure": structure,
        "with_history": with_history,
    }
