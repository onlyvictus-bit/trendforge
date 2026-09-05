from __future__ import annotations

from pathlib import Path
import asyncio
import os
from contextlib import asynccontextmanager, suppress
from datetime import date, datetime, timezone
from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .selection.contracts import EvidenceDirection, SelectionState

from .causal_engine import (
    CausalBatchRequest,
    CausalEvaluationResult,
    evaluate_causal_batch,
)
from .bse_offer_ingestion import refresh_bse_offer_documents
from .corporate_actions import (
    CandleAdjustmentReconcileRequest,
    reconcile_corporate_actions,
)
from .engine import (
    current_command_bar,
    get_candidate,
    list_candidates,
    list_source_health,
)
from .evidence_builder import build_symbol_evidence, persist_symbol_evidence
from .exchange_calendar import evaluate_nse_calendar
from .feature_registry import (
    FeatureRegistryLintReport,
    FeatureRegistryManifest,
    build_feature_registry,
    lint_feature_registry,
)
from .derivatives_engine import (
    ImpliedVolatilityInput,
    OptionPricingInput,
    black_scholes_greeks,
    black_scholes_price,
    implied_volatility,
)
from .gate_readiness import dependency_state, gate_readiness
from .cftc_history import import_cftc_history
from .decision_fixtures import load_demo_decision_run
from .selection import (
    Q5R2FixtureBatch,
    Q5R3FixtureBatch,
    Q5R4FixtureBatch,
    Q5R6FixtureBatch,
    SelectionFixtureBatch,
    build_q5_r1_fixture_batch,
    build_q5_r2_fixture_batch,
    build_q5_r3_fixture_batch,
    build_q5_r4_fixture_batch,
    build_q5_r6_fixture_batch,
)
from .selection.live_run import LiveSelectionBatch, build_live_selection_run
from .selection.cash_a1_staging import (
    CashStagingBatch,
    latest_cash_staging,
    persist_cash_staging,
    stage_cash_last_good,
)
from .selection.cash_a2_identity import (
    CashIdentityBatch,
    build_cash_identity_batch,
    latest_cash_identity,
    persist_cash_identity,
)
from .selection.cash_a3_discovery import (
    CashDiscoveryBatch,
    build_cash_discovery_batch,
    latest_cash_discovery,
    persist_cash_discovery,
)
from .selection.attention_order import (
    AttentionRowV1,
    InventoryDiscoveryV1,
    latest_attention_order,
)
from .selection.s3_cheap_discovery import (
    S3CheapDiscoveryBatchV1,
    S3WatchQueueV1,
    build_s3_cheap_discovery,
    build_s3_watch_queue,
)
from .selection.cash_a4_history import (
    CashHistoryBatch,
    build_cash_history_batch,
    latest_cash_history,
    persist_cash_history,
)
from .selection.cash_c1_rank import CashRankBatch, build_cash_rank_batch, persist_cash_rank
from .selection.fo_a6_enrichment import (
    FoEnrichmentBatch,
    build_fo_enrichment_batch,
    persist_fo_enrichment,
)
from .selection.index_a5_context import (
    CashContextBatch,
    build_cash_context_batch,
    persist_cash_context,
)
from .selection.inventory_source_bundle import (
    InventorySourceBundleV1,
    latest_inventory_source_bundle,
)
from .selection.m_factor_bff import (
    MFactorBatchV1,
    MFactorHorizon,
    MFactorNotReady,
    MFactorSide,
    build_m_factor_batch,
)
from .options_intelligence.bff import (
    ExpiryRangeBatchV1,
    OiAnalysisBatchV1,
    OiToolsNotReady,
    OiTrackerBatchV1,
    StrikeExplorerBatchV1,
    build_expiry_range_batch,
    build_oi_analysis_batch,
    build_oi_tracker_batch,
    build_strike_explorer_batch,
)
from .selection.mwpl_b import MwplAssessment, assess_mwpl, persist_mwpl
from .selection.r3_live import R3ResolutionV1, latest_r3_resolution
from .selection.r6_live import R6EnrichmentBatchV1, build_r6_enrichment
from .selection.top10_research import Top10ResearchBoardV1, build_top10_research
from .selection.evidence_radar import (
    CoverageReportV1,
    EvidenceRadarV1,
    build_coverage,
    build_evidence_radar,
)
from .selection.s2_market_weather import (
    S2MarketWeatherV1,
    build_s2_market_weather,
)
from .selection.r2b_live import (
    R2BNamedActivationV1,
    R2BNamedSourceV1,
    build_r2b_named_activation,
    latest_r2b_named_activation,
    persist_r2b_named_activation,
)
from .selection.r4_live import R4IdentityPinV1, R4IdentityRowV1, latest_r4_identity_pin
from .selection.r14_live import (
    R14CaJoinBatchV1,
    R14CaJoinRowV1,
    latest_r14_ca_join,
)
from .selection.r5_live import (
    R5StructureBatchV1,
    R5StructureRowV1,
    latest_r5_structure_batch,
)
from .selection.s4s5_compare import S4S5CompareBatchV1, build_s4s5_compare
from .selection.s4_structure_pack import (
    S4StructurePackBatchV1,
    build_s4_structure_pack,
)
from .selection.s5_shortlist_enrichment import (
    S5EnrichmentBatchV1,
    build_s5_enrichment,
)
from .selection.s6_family_resolution import (
    S6ResolutionBatchV1,
    build_s6_resolution,
)
from .selection.s7_state_gates import (
    S7IdeaCardV1,
    S7StateBatchV1,
    build_s7_state,
)
from .selection.tradability import (
    TradabilityBatchV1,
    TradabilityResultV1,
    build_tradability_batch,
)
from .selection.guidance_oms import (
    GuidanceLiveBlocked,
    GuidanceOMSTicketV1,
    arm_snapshot,
    build_paper_ticket,
    compute_paper_plan,
    dispatch_live_placement,
    ensure_live_placement_allowed,
    set_live_orders_armed,
)
from .scanners.registry import (
    SCHEMA_VERSION as R8_REGISTRY_SCHEMA,
    NATIVE_CORE_DEFINITIONS,
    ScannerDefinitionV1,
)
from .scanners.native_core import (
    NativeCoreRowV1,
    NativeCoreRunV1,
    build_native_core_run,
)
from .scanners.pipe_dsl import (
    PIPE_DEFINITIONS,
    PipeDefinitionV1,
    PipeRunV1,
    build_pipe_run,
)
from .selection.s8_persist_run import S8ScanBlobV1
from .selection.s8_service import (
    build_and_persist_current_s8,
    latest_or_build_current_s8,
)
from .selection.r16_service import (
    approval_payload as r16_approval_payload,
    legacy_gate_payload as r16_legacy_gate_payload,
    legacy_homework_payload as r16_legacy_homework_payload,
    metrics_payload as r16_metrics_payload,
    observations_payload as r16_observations_payload,
    runs_payload as r16_runs_payload,
    status_payload as r16_status_payload,
)
from .selection.r18_governance import (
    ChallengerEvaluationV1,
    ModelManifestV1,
    build_promotion_review,
    governance_status as r18_governance_status,
)
from .selection.r18_store import (
    get_payload as r18_get_payload,
    list_payloads as r18_list_payloads,
    persist_review as r18_persist_review,
    schema_status as r18_schema_status,
)
from .selection.profile_source_contracts import (
    StrategySourceRegistry,
    build_strategy_source_registry,
)
from .selection.r11_mcx_live import (
    McxMasterBatchV1,
    McxMasterRowV1,
    build_mcx_master,
)
from .selection.store import list_latest_selection_payloads as _list_payloads
from .selection.data_lane import DataLaneStateV1, resolve_lane
from .selection.research_quantity import ResearchFundsV1, ResearchQtyBatchV1
from .hybrid_v2.contracts import HybridOverlayBatchV1, HybridOverlayRowV1
from .hybrid_v2.pipeline import build_hybrid_v2_overlay
from .selection.use_matrix_c0 import (
    SourceUseMatrix,
    build_source_use_matrix,
    persist_source_use_matrix,
)
from .selection.store import (
    apply_comparable_diff,
    latest_live_selection_batch,
    persist_live_selection_batch,
)
from .harmonic_advanced import (
    analyze_harmonic_advanced,
    benchmark_analysis,
    build_alerts,
    chart_overlay_payload,
    liquidity_prefilter,
)
from .harmonic_detector import detect_harmonic_patterns
from .harmonic_lifecycle import (
    HarmonicLifecycleInput,
    HarmonicLifecycleResult,
    evaluate_harmonic_lifecycle,
)
from .harmonic_sources import HARMONIC_SOURCES
from .models import (
    CandidateType,
    DataTrust,
    FreshnessState,
    HarmonicAdvancedAnalysis,
    HarmonicAlertRecord,
    HealthResponse,
    HarmonicPatternResult,
    HarmonicScanRequest,
    HarmonicScanResponse,
    HarmonicSource,
    MetricRow,
    MLScanCandidate,
    MLScanRun,
    MLScanStatus,
    NSEResampleResponse,
    OHLCVCandle,
    OHLCVFetchRequest,
    OHLCVFetchResponse,
    PairRow,
    ParquetStatus,
    RadarCandidate,
    ResearchCreate,
    ResearchRecord,
    SourceCatalogRecord,
    SourceHealth,
    SourceInventoryAuditRequest,
    SourceMonitorSummary,
    SourceParseResult,
    SourceRegistryRecord,
    SourceSnapshotRecord,
    SourceState,
    StatusGroup,
    Tone,
    TradePlan,
)
from .market_context import (
    MarketContextInput,
    MarketContextResult,
    SectorContextInput,
    SectorContextResult,
    evaluate_market_context,
    evaluate_sector_context,
)
from .market_context_ingestion import (
    ContextDataUnavailable,
    build_official_market_context,
    build_official_sector_contexts,
)
from .nse_eod_ingestion import NSEEODBackfillResult, backfill_nse_eod
from .nse_session import (
    SUPPORTED_NSE_TIMEFRAMES,
    build_nse_4h_custom,
    resample_nse_session,
)
from .ohlcv_adapter import DataSourceUnavailable, normalize_nse_symbol
from .openalgo_client import (
    OpenAlgoCapabilityReport,
    OpenAlgoProviderContractV1,
    assess_openalgo_capability,
    openalgo_provider_contract,
)
from .openalgo_shadow import (
    OpenAlgoShadowBatchV1,
    activation_from_environment,
    disabled_shadow_batch,
)
from .observability import configure_logging
from .parquet_store import (
    get_parquet_status,
    read_candles_from_parquet,
    write_candles_to_parquet,
)
from .source_adapters import fetch_ohlcv_from_source
from .source_monitor import (
    check_sources,
    source_catalog_records,
    source_snapshot_history,
)
from .source_parser import parse_source, parse_sources, source_parse_history
from .source_resolver import direct_download_candidates
from .source_inventory_audit import audit_saved_inventory
from .source_inventory_compiler import (
    InventoryCompilerReport,
    compile_default_inventory,
    decision_job_catalog,
)
from .source_operations import build_source_operations_snapshot
from .source_cohort_r0b import R0BCohortReport, evaluate_r0b_cohort
from .source_cohort_r0c import R0CCohortReport, evaluate_r0c_cohort
from .source_registry_contracts import RegistryCoverage, build_registry_coverage
from .source_scheduler import SOURCE_MONITOR_SCHEDULER
from .validation_engine import backtest_harmonic_series
from .institutional_ai import model_capabilities
from .institutional_backtest import (
    WalkForwardPoint,
    WalkForwardReport,
    walk_forward_validate,
)
from .institutional_config import load_institutional_config
from .institutional_engine import (
    InstitutionalAnalysisRequest,
    InstitutionalAnalysisResult,
    analyze_institutional,
)
from .institutional_features import (
    InstitutionalFeatureResult,
    build_institutional_features,
)
from .disclosure_intelligence import (
    DisclosureDrilldown,
    latest_disclosure_drilldown,
    normalize_and_save_disclosures,
)
from .fii_stock_signals import (
    CanonicalLatestResultLoader,
    FIIStockSignalsSnapshot,
    build_fii_stock_signals,
)
from .commodity_context import (
    CommodityContextSnapshot,
    latest_commodity_context_snapshot,
    normalize_and_save_commodity_context,
)
from .macro_event_context import (
    MacroEventContextSnapshot,
    build_macro_event_context_snapshot,
    latest_macro_event_context_snapshot,
    save_macro_event_context_snapshot,
)
from .institutional_sources import (
    CORPORATE_DISCLOSURE_ENDPOINTS,
    ENDPOINTS,
    EXTENDED_MARKET_ENDPOINTS,
    MACRO_EVENT_ENDPOINTS,
    MARKET_ACTIVITY_ENDPOINTS,
    AsyncEndpointClient,
    EndpointFetchResult,
    corporate_disclosure_requests,
    extended_market_requests,
    macro_event_requests,
    market_activity_requests,
)
from .institutional_storage import (
    list_analysis_reports,
    save_analysis_report,
    save_walk_forward_report,
)
from .market_activity import (
    MarketActivitySnapshot,
    build_market_activity_snapshot,
    latest_market_activity_snapshot,
    save_market_activity_snapshot,
)
from .live_panels import LivePanelsService
from .market_data_alignment import CanonicalManifestSourceProvider
from .market_data_scheduler import ManualRefreshCoordinator, build_default_scheduler
from .scanner_scheduler import SCANNER_SCHEDULER, scanner_candidates, scanner_runs
from .trade_vision_export import build_trade_vision_evidence_packet
from .risk_engine import (
    PositionSizingInput,
    PositionSizingResult,
    RiskSettings,
    calculate_position_size,
)
from .safety_engine import (
    PanicLockRequest,
    RecoveryUnlockRequest,
    SafetyStatus,
    activate_panic_lock,
    evaluate_safety_status,
    recover_from_manual_lock,
)
from .records import (
    AlertCreate,
    AlertRecord,
    JournalCreate,
    JournalOutcomeUpdate,
    JournalRecord,
)
from .storage import (
    DB_PATH,
    acknowledge_general_alert,
    delete_research_record,
    get_ml_scan_status,
    get_risk_settings,
    get_research_record,
    list_candle_quality_records,
    list_candle_revisions,
    list_candle_adjustment_assessments,
    list_corporate_event_observations,
    list_exchange_calendar_days,
    list_bse_offer_documents,
    list_corporate_offer_events,
    reconcile_stored_candle_adjustments,
    list_cftc_analytics,
    list_gate_decisions,
    list_raw_source_archive,
    list_source_fetch_attempts,
    list_source_inventory_audit_rows,
    list_source_inventory_audit_runs,
    list_source_freshness_status,
    list_source_domain_rows,
    list_harmonic_alerts,
    list_harmonic_lifecycle_events,
    list_harmonic_patterns,
    list_general_alerts,
    list_journal_entries,
    list_nse_instruments,
    nse_instrument_universe_status,
    official_market_input_status,
    list_safety_events,
    latest_market_context_snapshot,
    latest_sector_context_snapshot,
    list_ml_scan_candidates,
    list_ml_scan_runs,
    list_ohlcv_candles,
    list_research_records,
    list_schema_migrations,
    list_validation_runs,
    list_source_parser_outputs,
    list_source_replacement_map,
    list_source_registry_records,
    save_harmonic_alerts,
    save_harmonic_lifecycle_events,
    save_harmonic_patterns,
    save_general_alert,
    save_journal_entry,
    save_ml_scan_snapshot,
    save_ohlcv_candles,
    save_research_record,
    save_risk_settings,
    save_market_context_snapshot,
    save_sector_context_snapshot,
    save_validation_report,
    update_source_registry_status,
    update_journal_outcome,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"
LOGGER = configure_logging()
_MD69_PANEL_PROVIDER = (
    CanonicalManifestSourceProvider(
        db_path=DB_PATH,
        data_root=ROOT_DIR / "data" / "market_data",
    )
    if os.getenv("MARKET_DATA_69_ENABLED", "0").strip() == "1"
    else None
)
_MD69_SCHEDULER = (
    build_default_scheduler(
        db_path=DB_PATH,
        data_root=ROOT_DIR / "data" / "market_data",
    )
    if os.getenv("MARKET_DATA_69_ENABLED", "0").strip() == "1"
    else None
)
_MD69_MANUAL_REFRESH = (
    ManualRefreshCoordinator(_MD69_SCHEDULER)
    if _MD69_SCHEDULER is not None
    else None
)
LIVE_PANELS_SERVICE = LivePanelsService(
    canonical_source_provider=_MD69_PANEL_PROVIDER
)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    SCANNER_SCHEDULER.restore()
    LIVE_PANELS_SERVICE.start(interval_sec=120)
    md69_task: asyncio.Task[dict[str, Any]] | None = None
    if (
        _MD69_SCHEDULER is not None
        and os.getenv("MARKET_DATA_69_AUTOSTART", "0").strip() == "1"
    ):
        md69_task = asyncio.create_task(
            _MD69_SCHEDULER.start_foreground(poll_seconds=15),
            name="trendforge-md69-scheduler",
        )
    try:
        yield
    finally:
        if md69_task is not None:
            md69_task.cancel()
            with suppress(asyncio.CancelledError):
                await md69_task
        await LIVE_PANELS_SERVICE.stop()
        SCANNER_SCHEDULER.stop(persist=False)


app = FastAPI(
    title="TrendForge Local Screener API",
    version="0.2.0",
    description="Guarded local research API for TrendForge screening, source evidence, risk, and validation.",
    lifespan=app_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        item.strip()
        for item in os.getenv(
            "TRENDFORGE_ALLOWED_ORIGINS",
            "http://127.0.0.1:8000,http://127.0.0.1:8001,http://localhost:8000,http://localhost:8001,http://127.0.0.1:8080,http://localhost:8080,http://127.0.0.1:5500,http://localhost:5500",
        ).split(",")
        if item.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_audit_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        LOGGER.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        raise
    duration_ms = round((perf_counter() - started) * 1000, 3)
    response.headers["X-Request-ID"] = request_id
    LOGGER.info(
        "request_complete",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok", service="trendforge-api", mode="guarded-research"
    )


@app.get("/api/panels/live")
async def live_panels(
    max_age_sec: int = Query(default=300, alias="maxAgeSec", ge=60, le=900),
    refresh: bool = Query(default=True),
    force: bool = Query(default=False),
) -> dict[str, Any]:
    """Return one fail-closed, current-session snapshot for all research panels."""
    return await LIVE_PANELS_SERVICE.get_snapshot(
        refresh=refresh,
        force=force,
        max_age_sec=max_age_sec,
    )


def _require_local_market_data_control(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(
            status_code=403,
            detail="manual market-data refresh is localhost-only",
        )


@app.post("/api/market-data/refresh", status_code=202)
async def manual_market_data_refresh(request: Request) -> dict[str, Any]:
    """Start one registry-driven refresh through the existing MD69 collector."""
    _require_local_market_data_control(request)
    if _MD69_MANUAL_REFRESH is None:
        raise HTTPException(status_code=503, detail="MD69 collector is disabled")
    return await _MD69_MANUAL_REFRESH.start()


@app.get("/api/market-data/refresh/status")
def manual_market_data_refresh_status(request: Request) -> dict[str, Any]:
    """Return dynamic source count, schedule and current manual-run status."""
    _require_local_market_data_control(request)
    if _MD69_MANUAL_REFRESH is None:
        raise HTTPException(status_code=503, detail="MD69 collector is disabled")
    return _MD69_MANUAL_REFRESH.status()


@app.get("/api/storage/migrations")
def storage_migrations() -> dict:
    migrations = list_schema_migrations()
    return {
        "status": "PASS",
        "migrationCount": len(migrations),
        "migrations": migrations,
    }


@app.get("/api/storage/candle-revisions")
def candle_revisions(
    symbol: str | None = Query(default=None, min_length=1, max_length=32),
    limit: int = Query(default=200, ge=1, le=5000),
) -> list[dict]:
    return list_candle_revisions(symbol=symbol, limit=limit)


@app.get("/api/storage/candle-quality")
def candle_quality(
    symbol: str | None = Query(default=None, min_length=1, max_length=32),
    limit: int = Query(default=200, ge=1, le=5000),
) -> list[dict]:
    return list_candle_quality_records(symbol=symbol, limit=limit)


@app.get("/api/storage/candle-adjustments")
def candle_adjustments(
    symbol: str | None = Query(default=None, min_length=1, max_length=32),
    limit: int = Query(default=200, ge=1, le=5000),
) -> list[dict]:
    return list_candle_adjustment_assessments(symbol=symbol, limit=limit)


@app.post("/api/storage/candle-adjustments/reconcile")
def reconcile_candle_adjustments(
    payload: CandleAdjustmentReconcileRequest,
) -> dict:
    return reconcile_stored_candle_adjustments(
        payload.symbol, payload.timeframe, payload.source
    )


@app.get("/api/corporate-actions/{symbol}/reconciliation")
def corporate_action_reconciliation(
    symbol: str,
    as_of: datetime = Query(alias="asOf"),
) -> dict:
    if as_of.utcoffset() is None:
        raise HTTPException(status_code=422, detail="asOf must be timezone-aware")
    observations = list_corporate_event_observations(symbol=symbol)
    actions = reconcile_corporate_actions(observations, as_of=as_of)
    return {
        "symbol": symbol.upper().strip(),
        "asOf": as_of.isoformat(),
        "observationCount": len(observations),
        "actionCount": len(actions),
        "actions": [
            action.model_dump(mode="json", by_alias=True) for action in actions
        ],
        "executable": False,
    }


@app.get("/api/evidence/{symbol}")
def symbol_evidence(
    symbol: str,
    as_of: datetime = Query(alias="asOf"),
    persist: bool = Query(default=False),
) -> dict:
    claims = build_symbol_evidence(symbol, as_of=as_of)
    saved = persist_symbol_evidence(symbol, as_of=as_of) if persist else 0
    return {
        "symbol": symbol.upper().strip(),
        "asOf": as_of.isoformat(),
        "claimCount": len(claims),
        "savedCount": saved,
        "claims": [claim.model_dump(mode="json", by_alias=True) for claim in claims],
    }


@app.get("/api/alerts", response_model=list[AlertRecord], response_model_by_alias=True)
def alerts(
    symbol: str | None = Query(default=None, max_length=32),
    acknowledged: bool | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
) -> list[AlertRecord]:
    return list_general_alerts(symbol=symbol, acknowledged=acknowledged, limit=limit)


@app.post("/api/alerts", response_model=AlertRecord, response_model_by_alias=True)
def create_alert(payload: AlertCreate) -> AlertRecord:
    return save_general_alert(payload)


@app.put(
    "/api/alerts/{alert_id}/acknowledge",
    response_model=AlertRecord,
    response_model_by_alias=True,
)
def acknowledge_alert(alert_id: int) -> AlertRecord:
    result = acknowledge_general_alert(alert_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return result


@app.get(
    "/api/journal", response_model=list[JournalRecord], response_model_by_alias=True
)
def journal(
    symbol: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=200, ge=1, le=5000),
) -> list[JournalRecord]:
    return list_journal_entries(symbol=symbol, limit=limit)


@app.post("/api/journal", response_model=JournalRecord, response_model_by_alias=True)
def create_journal_entry(payload: JournalCreate) -> JournalRecord:
    return save_journal_entry(payload)


@app.put(
    "/api/journal/{entry_id}/outcome",
    response_model=JournalRecord,
    response_model_by_alias=True,
)
def update_journal_entry_outcome(
    entry_id: int, payload: JournalOutcomeUpdate
) -> JournalRecord:
    try:
        result = update_journal_outcome(entry_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    return result


@app.get("/api/settings/risk", response_model=RiskSettings)
def risk_settings() -> RiskSettings:
    return get_risk_settings()


@app.put("/api/settings/risk", response_model=RiskSettings)
def update_risk_settings(payload: RiskSettings) -> RiskSettings:
    return save_risk_settings(payload)


@app.get("/api/universe/instruments")
def universe_instruments(
    symbol: str | None = Query(default=None, max_length=32),
    as_of: str | None = Query(default=None, alias="asOf"),
    limit: int = Query(default=1000, ge=1, le=10000),
) -> list[dict]:
    return list_nse_instruments(symbol=symbol, as_of=as_of, limit=limit)


@app.get("/api/universe/status")
def universe_status() -> dict:
    return nse_instrument_universe_status()


@app.get("/api/calendar/status")
def calendar_status(
    at: str | None = Query(default=None, max_length=40),
    segment: str = Query(default="CM", min_length=1, max_length=10),
) -> dict:
    parsed_at = None
    if at:
        try:
            parsed_at = datetime.fromisoformat(at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="Invalid ISO timestamp."
            ) from exc
    return evaluate_nse_calendar(parsed_at, segment=segment)


@app.get("/api/calendar/days")
def calendar_days(
    segment: str = Query(default="CM", min_length=1, max_length=10),
    year: int | None = Query(default=None, ge=2000, le=2200),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[dict]:
    return list_exchange_calendar_days(segment=segment, year=year, limit=limit)


@app.post(
    "/api/context/market/evaluate",
    response_model=MarketContextResult,
    response_model_by_alias=True,
)
def market_context_evaluate(payload: MarketContextInput) -> MarketContextResult:
    result = evaluate_market_context(payload)
    save_market_context_snapshot(result.model_dump(mode="json", by_alias=True))
    return result


@app.get("/api/context/market/latest")
def market_context_latest() -> dict:
    result = latest_market_context_snapshot()
    if result is None:
        raise HTTPException(
            status_code=404, detail="No market context snapshot exists."
        )
    return result


@app.get("/api/context/official/status")
def official_context_status() -> dict:
    return official_market_input_status()


@app.post("/api/context/official/rebuild")
def official_context_rebuild() -> dict:
    try:
        market = build_official_market_context()
        sectors = build_official_sector_contexts()
    except ContextDataUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "market": market.model_dump(mode="json", by_alias=True),
        "sectors": [item.model_dump(mode="json", by_alias=True) for item in sectors],
        "executable": False,
    }


@app.post(
    "/api/context/official/backfill",
    response_model=NSEEODBackfillResult,
    response_model_by_alias=True,
)
def official_context_backfill(
    start_date: date = Query(alias="startDate"),
    end_date: date = Query(alias="endDate"),
    include_cash_history: bool = Query(default=False, alias="includeCashHistory"),
) -> NSEEODBackfillResult:
    try:
        return backfill_nse_eod(
            start_date,
            end_date,
            include_cash_history=include_cash_history,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/api/context/sector/evaluate",
    response_model=SectorContextResult,
    response_model_by_alias=True,
)
def sector_context_evaluate(payload: SectorContextInput) -> SectorContextResult:
    result = evaluate_sector_context(payload)
    save_sector_context_snapshot(result.model_dump(mode="json", by_alias=True))
    return result


@app.get("/api/context/sector/latest")
def sector_context_latest(
    sector: str | None = Query(default=None, max_length=120),
    direction: str | None = Query(default=None, max_length=10),
) -> dict:
    result = latest_sector_context_snapshot(sector=sector, direction=direction)
    if result is None:
        raise HTTPException(
            status_code=404, detail="No sector context snapshot exists."
        )
    return result


@app.post("/api/risk/position-size", response_model=PositionSizingResult)
def position_size(payload: PositionSizingInput) -> PositionSizingResult:
    settings = get_risk_settings()
    safety = evaluate_safety_status(settings=settings)
    guarded = payload.model_copy(
        update={
            "account_size": settings.account_size,
            "max_open_positions": settings.max_open_positions,
            "daily_pnl": safety.daily_realized_pnl,
            "safety_state": safety.state,
            "safety_risk_multiplier": safety.risk_multiplier,
        }
    )
    return calculate_position_size(guarded, settings=settings)


@app.get(
    "/api/safety/status", response_model=SafetyStatus, response_model_by_alias=True
)
def safety_status(
    as_of: str | None = Query(default=None, alias="asOf"),
) -> SafetyStatus:
    parsed = None
    if as_of:
        try:
            parsed = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="asOf must be ISO-8601"
            ) from exc
        if parsed.utcoffset() is None:
            raise HTTPException(status_code=422, detail="asOf must include timezone")
    return evaluate_safety_status(as_of=parsed, settings=get_risk_settings())


@app.get("/api/safety/events")
def safety_events(
    active: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict]:
    return list_safety_events(active=active, limit=limit)


@app.post(
    "/api/safety/panic-lock",
    response_model=SafetyStatus,
    response_model_by_alias=True,
)
def panic_lock(payload: PanicLockRequest) -> SafetyStatus:
    return activate_panic_lock(payload)


@app.post(
    "/api/safety/unlock",
    response_model=SafetyStatus,
    response_model_by_alias=True,
)
def safety_unlock(payload: RecoveryUnlockRequest) -> SafetyStatus:
    try:
        return recover_from_manual_lock(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post(
    "/api/causal/evaluate",
    response_model=list[CausalEvaluationResult],
    response_model_by_alias=True,
)
def causal_evaluate(payload: CausalBatchRequest) -> list[CausalEvaluationResult]:
    try:
        return evaluate_causal_batch(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/demo/decision-scenarios/load")
def load_demo_decision_scenarios() -> dict:
    return load_demo_decision_run()


@app.get(
    "/api/v1/selection/live",
    response_model=LiveSelectionBatch,
    response_model_by_alias=True,
)
def r1_live_selection() -> LiveSelectionBatch:
    stored = latest_live_selection_batch()
    if stored is not None:
        return stored
    return build_live_selection_run()


@app.post(
    "/api/v1/selection/live/refresh",
    response_model=LiveSelectionBatch,
    response_model_by_alias=True,
)
def r1_live_selection_refresh() -> LiveSelectionBatch:
    prior = latest_live_selection_batch()
    batch = apply_comparable_diff(build_live_selection_run(), prior)
    return persist_live_selection_batch(batch)


@app.get(
    "/api/v1/selection/evidence",
    response_model=InventorySourceBundleV1,
    response_model_by_alias=True,
)
def r1_inventory_source_evidence() -> InventorySourceBundleV1:
    bundle = latest_inventory_source_bundle()
    if bundle is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "R1_EVIDENCE_NOT_READY",
                "message": "No completed R1 evidence bundle is persisted.",
            },
        )
    return bundle


@app.get(
    "/api/v1/selection/attention",
    response_model=InventoryDiscoveryV1,
    response_model_by_alias=True,
)
def r2_attention_order() -> InventoryDiscoveryV1:
    order = latest_attention_order()
    if order is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "R2_ATTENTION_NOT_READY",
                "message": "No completed R2 attention order is persisted.",
            },
        )
    return order



@app.get(
    "/api/v1/selection/cheap-discovery",
    response_model=S3CheapDiscoveryBatchV1,
    response_model_by_alias=True,
)
def s3_cheap_discovery() -> S3CheapDiscoveryBatchV1:
    try:
        batch = build_s3_cheap_discovery(loader=_r6_loader())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc
    # R8: attach native-core match chips as cheap facts; rank untouched.
    try:
        from .scanners.native_core import attach_native_matches_to_s3
        from .selection.r5_live import latest_r5_structure_batch

        r5_batch = latest_r5_structure_batch()
        if r5_batch is not None:
            batch = attach_native_matches_to_s3(
                batch, build_native_core_run(r5=r5_batch)
            )
    except Exception:
        pass  # matches are optional decoration; never block S3
    return batch


@app.get(
    "/api/v1/selection/cheap-discovery/watch",
    response_model=S3WatchQueueV1,
    response_model_by_alias=True,
)
def s3_cheap_discovery_watch(
    limit: int = Query(default=50, ge=1, le=200),
) -> S3WatchQueueV1:
    try:
        return build_s3_watch_queue(
            build_s3_cheap_discovery(loader=_r6_loader()),
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.post("/api/v1/selection/cheap-discovery")
def s3_cheap_discovery_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.post("/api/v1/selection/cheap-discovery/watch")
def s3_cheap_discovery_watch_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})
def _r6_loader():
    if _MD69_SCHEDULER is None:
        return None
    return CanonicalLatestResultLoader(_MD69_SCHEDULER.store)


@app.get(
    "/api/v1/selection/enrichment",
    response_model=R6EnrichmentBatchV1,
    response_model_by_alias=True,
)
def r6_enrichment() -> R6EnrichmentBatchV1:
    try:
        return build_r6_enrichment(loader=_r6_loader())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.get(
    "/api/v1/selection/top10",
    response_model=Top10ResearchBoardV1,
    response_model_by_alias=True,
)
def selection_top10() -> Top10ResearchBoardV1:
    try:
        enrichment = build_r6_enrichment(loader=_r6_loader())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc
    return build_top10_research(enrichment=enrichment)


def _radar_or_503() -> EvidenceRadarV1:
    try:
        return build_evidence_radar(loader=_r6_loader())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.get(
    "/api/v1/selection/evidence-radar/coverage",
    response_model=CoverageReportV1,
    response_model_by_alias=True,
)
def evidence_radar_coverage() -> CoverageReportV1:
    try:
        report, _catalog = build_coverage()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc
    return report


@app.get(
    "/api/v1/selection/evidence-radar",
    response_model=EvidenceRadarV1,
    response_model_by_alias=True,
)
def evidence_radar(horizon: str = "ALL") -> EvidenceRadarV1:
    radar = _radar_or_503()
    allowed = {"INTRADAY", "SWING", "POSITION", "COMMODITY", "ALL"}
    if horizon not in allowed:
        raise HTTPException(
            status_code=422,
            detail={"code": "UNKNOWN_HORIZON", "allowed": sorted(allowed)},
        )
    if horizon != "ALL":
        radar = radar.model_copy(
            update={
                "boards": {horizon: radar.boards[horizon]},
                "rows": tuple(row for row in radar.rows if row.horizon == horizon),
            }
        )
    return radar


@app.get(
    "/api/v1/selection/evidence-radar/boards",
    response_model=EvidenceRadarV1,
    response_model_by_alias=True,
)
def evidence_radar_boards(horizon: str = "ALL") -> EvidenceRadarV1:
    return evidence_radar(horizon=horizon)


@app.get(
    "/api/v1/selection/market-weather",
    response_model=S2MarketWeatherV1,
    response_model_by_alias=True,
)
def s2_market_weather() -> S2MarketWeatherV1:
    try:
        return build_s2_market_weather(loader=_r6_loader())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.get(
    "/api/v1/selection/market-weather/sectors",
    response_model=S2MarketWeatherV1,
    response_model_by_alias=True,
)
def s2_market_weather_sectors() -> S2MarketWeatherV1:
    return s2_market_weather()


@app.get(
    "/api/v1/selection/resolution",
    response_model=R3ResolutionV1,
    response_model_by_alias=True,
)
def r3_evidence_resolution() -> R3ResolutionV1:
    """LEGACY single-family diagnostic â€” retained for the M-Factor BFF
    subsume-check. Canonical family resolution lives at
    GET /api/v1/selection/s6-resolution (File A Â§9.4 one-owner law):
    the UI must project S7, which projects S6."""
    bundle = latest_inventory_source_bundle()
    if bundle is None:
        raise HTTPException(status_code=503, detail={"code": "R3_EVIDENCE_NOT_READY"})
    attention = latest_attention_order()
    if attention is None:
        raise HTTPException(status_code=503, detail={"code": "R3_ATTENTION_NOT_READY"})
    resolution = latest_r3_resolution()
    if (
        resolution is None
        or resolution.r1_bundle_id != bundle.bundle_id
        or resolution.r1_bundle_hash != bundle.bundle_hash
        or resolution.r2_run_id != attention.run_id
        or resolution.r2_run_hash != attention.run_hash
        or resolution.permission_fingerprint != bundle.permission_fingerprint
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "R3_RESOLUTION_NOT_READY",
                "message": "Persisted R3 does not match the current R1/R2 spine.",
                "pointer": "/api/v1/selection/s6-resolution",
            },
        )
    return resolution


@app.get(
    "/api/v1/tools/m_factor",
    response_model=MFactorBatchV1,
    response_model_by_alias=True,
)
def tools_m_factor(
    horizon: Literal["intra", "swing", "position", "commodity"] = Query(
        default=MFactorHorizon.SWING.value
    ),
    side: Literal["buy", "sell", "both"] = Query(default=MFactorSide.BOTH.value),
    limit: int = Query(default=40, ge=1, le=200),
    debug: bool = Query(default=False),
) -> MFactorBatchV1:
    """Read-only M-Factor BFF over hash-matched R1/R2/R3 (plan Â§1D).

    Two FUS-009 hypotheses per symbol; no second score, no geometry,
    no CONFIRMED. 503 carries a WAIT_* code instead of mixed snapshots.
    """
    try:
        return build_m_factor_batch(horizon=horizon, side=side, limit=limit, debug=debug)
    except MFactorNotReady as exc:
        raise HTTPException(
            status_code=503, detail={"code": exc.code, "message": exc.message}
        ) from exc


_OI_TOOLS = (
    "oi_analysis",
    "oi_tracker",
    "strike_explorer",
    "expiry_prediction",
)


@app.get(
    "/api/v1/tools/oi_analysis",
    response_model=OiAnalysisBatchV1,
    response_model_by_alias=True,
)
def tools_oi_analysis(
    symbol: str | None = Query(default=None),
    limit: int = Query(default=40, ge=1, le=200),
) -> OiAnalysisBatchV1:
    """Read-only futures OI quadrant board behind official MWPL/ban gates.

    503 carries a WAIT_* code instead of mixing snapshots. Fixture demo
    strings are structurally impossible in the payload.
    """
    try:
        return build_oi_analysis_batch(symbol=symbol, limit=limit)
    except OiToolsNotReady as exc:
        raise HTTPException(
            status_code=503, detail={"code": exc.code, "message": exc.message}
        ) from exc


@app.get(
    "/api/v1/tools/oi_tracker",
    response_model=OiTrackerBatchV1,
    response_model_by_alias=True,
)
def tools_oi_tracker(
    underlying: str | None = Query(default=None),
    limit: int = Query(default=40, ge=1, le=200),
) -> OiTrackerBatchV1:
    """Read-only OI/PCR path over persisted FO runs; roll-aware window."""
    try:
        return build_oi_tracker_batch(underlying=underlying, limit=limit)
    except OiToolsNotReady as exc:
        raise HTTPException(
            status_code=503, detail={"code": exc.code, "message": exc.message}
        ) from exc


@app.get(
    "/api/v1/tools/strike_explorer",
    response_model=StrikeExplorerBatchV1,
    response_model_by_alias=True,
)
def tools_strike_explorer(
    underlying: str = Query(...),
    expiry: str = Query(...),
) -> StrikeExplorerBatchV1:
    """Strike ladder only after the same-expiry chain passes quality."""
    try:
        return build_strike_explorer_batch(underlying=underlying, expiry=expiry)
    except OiToolsNotReady as exc:
        raise HTTPException(
            status_code=503, detail={"code": exc.code, "message": exc.message}
        ) from exc


@app.get(
    "/api/v1/tools/expiry_prediction",
    response_model=ExpiryRangeBatchV1,
    response_model_by_alias=True,
)
def tools_expiry_prediction(
    underlying: str = Query(...),
    expiry: str = Query(...),
) -> ExpiryRangeBatchV1:
    """Expiry Range Context (estimate-only); UI name must stay unchanged."""
    try:
        return build_expiry_range_batch(underlying=underlying, expiry=expiry)
    except OiToolsNotReady as exc:
        raise HTTPException(
            status_code=503, detail={"code": exc.code, "message": exc.message}
        ) from exc


@app.post("/api/v1/tools/oi_analysis")
def tools_oi_analysis_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.post("/api/v1/tools/oi_tracker")
def tools_oi_tracker_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.post("/api/v1/tools/strike_explorer")
def tools_strike_explorer_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.post("/api/v1/tools/expiry_prediction")
def tools_expiry_prediction_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get(
    "/api/v1/selection/identity-pin",
    response_model=R4IdentityPinV1,
    response_model_by_alias=True,
)
def r4_identity_pin() -> R4IdentityPinV1:
    bundle = latest_inventory_source_bundle()
    if bundle is None:
        raise HTTPException(status_code=503, detail={"code": "R4_EVIDENCE_NOT_READY"})
    attention = latest_attention_order()
    if attention is None:
        raise HTTPException(status_code=503, detail={"code": "R4_ATTENTION_NOT_READY"})
    pin = latest_r4_identity_pin()
    if (
        pin is None
        or pin.r1_bundle_id != bundle.bundle_id
        or pin.r1_bundle_hash != bundle.bundle_hash
        or pin.r2_run_id != attention.run_id
        or pin.r2_run_hash != attention.run_hash
        or pin.permission_fingerprint != bundle.permission_fingerprint
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "R4_IDENTITY_PIN_NOT_READY",
                "message": "No hash-matched R4 identity pin is persisted for current R1/R2.",
            },
        )
    return pin


@app.get(
    "/api/v1/selection/identity-pin/{symbol}",
    response_model=R4IdentityRowV1,
    response_model_by_alias=True,
)
def r4_identity_pin_symbol(symbol: str) -> R4IdentityRowV1:
    batch = r4_identity_pin()
    key = symbol.strip().upper()
    for row in batch.rows:
        if row.symbol == key:
            return row
    raise HTTPException(
        status_code=404,
        detail={"code": "R4_SYMBOL_NOT_FOUND", "symbol": key},
    )


@app.get(
    "/api/v1/selection/named-activation",
    response_model=R2BNamedActivationV1,
    response_model_by_alias=True,
)
def r2b_named_activation() -> R2BNamedActivationV1:
    bundle = latest_inventory_source_bundle()
    attention = latest_attention_order()
    if bundle is None:
        raise HTTPException(status_code=503, detail={"code": "R2B_EVIDENCE_NOT_READY"})
    if attention is None:
        raise HTTPException(status_code=503, detail={"code": "R2B_ATTENTION_NOT_READY"})
    try:
        built = build_r2b_named_activation()
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": str(exc), "message": "R2-B named activation not ready."},
        ) from exc
    stored = latest_r2b_named_activation()
    if (
        stored is None
        or stored.r1_bundle_hash != bundle.bundle_hash
        or stored.r2_run_hash != attention.run_hash
        or stored.run_hash != built.run_hash
    ):
        stored = persist_r2b_named_activation(built)
    return stored


@app.get(
    "/api/v1/selection/named-activation/{source_key}",
    response_model=R2BNamedSourceV1,
    response_model_by_alias=True,
)
def r2b_named_activation_source(source_key: str) -> R2BNamedSourceV1:
    batch = r2b_named_activation()
    key = source_key.strip()
    for row in batch.rows:
        if row.source_key == key:
            return row
    raise HTTPException(
        status_code=404,
        detail={"code": "R2B_SOURCE_NOT_FOUND", "sourceKey": key},
    )


@app.get(
    "/api/v1/selection/ca-join",
    response_model=R14CaJoinBatchV1,
    response_model_by_alias=True,
)
def r14_ca_join_batch() -> R14CaJoinBatchV1:
    bundle = latest_inventory_source_bundle()
    if bundle is None:
        raise HTTPException(status_code=503, detail={"code": "R14_EVIDENCE_NOT_READY"})
    attention = latest_attention_order()
    if attention is None:
        raise HTTPException(status_code=503, detail={"code": "R14_ATTENTION_NOT_READY"})
    join = latest_r14_ca_join()
    if (
        join is None
        or join.r1_bundle_id != bundle.bundle_id
        or join.r1_bundle_hash != bundle.bundle_hash
        or join.r2_run_id != attention.run_id
        or join.r2_run_hash != attention.run_hash
        or join.permission_fingerprint != bundle.permission_fingerprint
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "R14_CA_JOIN_NOT_READY",
                "message": "No hash-matched R14 CA join is persisted for current R1/R2.",
            },
        )
    return join


@app.get(
    "/api/v1/selection/ca-join/{symbol}",
    response_model=R14CaJoinRowV1,
    response_model_by_alias=True,
)
def r14_ca_join_symbol(symbol: str) -> R14CaJoinRowV1:
    batch = r14_ca_join_batch()
    key = symbol.strip().upper()
    for row in batch.rows:
        if row.symbol == key:
            return row
    raise HTTPException(
        status_code=404,
        detail={"code": "R14_SYMBOL_NOT_FOUND", "symbol": key},
    )


@app.get(
    "/api/v1/selection/s4s5-compare",
    response_model=S4S5CompareBatchV1,
    response_model_by_alias=True,
)
def s4s5_compare(limit: int = 40) -> S4S5CompareBatchV1:
    try:
        return build_s4s5_compare(limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": str(exc), "message": "S4/S5 research compare not ready."},
        ) from exc


@app.get(
    "/api/v1/hybrid-v2/overlay",
    response_model=HybridOverlayBatchV1,
    response_model_by_alias=True,
)
def hybrid_v2_overlay(limit: int = 40) -> HybridOverlayBatchV1:
    try:
        return build_hybrid_v2_overlay(limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": str(exc), "message": "Hybrid V2 overlay not ready."},
        ) from exc


@app.get(
    "/api/v1/hybrid-v2/overlay/{symbol}",
    response_model=HybridOverlayRowV1,
    response_model_by_alias=True,
)
def hybrid_v2_overlay_symbol(symbol: str) -> HybridOverlayRowV1:
    try:
        batch = build_hybrid_v2_overlay(limit=40)
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": str(exc), "message": "Hybrid V2 overlay not ready."},
        ) from exc
    key = symbol.strip().upper()
    for row in batch.rows:
        if row.symbol == key:
            return row
    raise HTTPException(
        status_code=404,
        detail={"code": "HYBRID_V2_SYMBOL_NOT_FOUND", "symbol": key},
    )


@app.get(
    "/api/v1/selection/structure",
    response_model=R5StructureBatchV1,
    response_model_by_alias=True,
)
def r5_structure_batch() -> R5StructureBatchV1:
    return _hash_matched_r5_or_503()


@app.get(
    "/api/v1/selection/structure/{symbol}",
    response_model=R5StructureRowV1,
    response_model_by_alias=True,
)
def r5_structure_symbol(symbol: str) -> R5StructureRowV1:
    batch = r5_structure_batch()
    key = symbol.strip().upper()
    for row in batch.rows:
        if row.symbol == key:
            return row
    raise HTTPException(
        status_code=404,
        detail={"code": "R5_SYMBOL_NOT_FOUND", "symbol": key},
    )


def _hash_matched_r5_or_503() -> R5StructureBatchV1:
    """Shared S4/S5/S6 guard: persisted R5 must match current R1/R2/R14."""
    bundle = latest_inventory_source_bundle()
    if bundle is None:
        raise HTTPException(status_code=503, detail={"code": "R5_EVIDENCE_NOT_READY"})
    attention = latest_attention_order()
    if attention is None:
        raise HTTPException(status_code=503, detail={"code": "R5_ATTENTION_NOT_READY"})
    structure = latest_r5_structure_batch()
    if (
        structure is None
        or structure.r1_bundle_id != bundle.bundle_id
        or structure.r1_bundle_hash != bundle.bundle_hash
        or structure.r2_run_id != attention.run_id
        or structure.r2_run_hash != attention.run_hash
        or structure.collector_run_id != bundle.collector_run_id
        or structure.cash_pipeline_fingerprint != bundle.cash_pipeline_fingerprint
        or structure.permission_fingerprint != bundle.permission_fingerprint
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "R5_STRUCTURE_NOT_READY",
                "message": "No hash-matched R5 structure batch is persisted for current R1/R2.",
            },
        )
    ca_join = latest_r14_ca_join()
    if (
        ca_join is None
        or structure.r14_run_id != ca_join.run_id
        or structure.r14_run_hash != ca_join.run_hash
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "R5_R14_JOIN_NOT_READY",
                "message": "No hash-matched R14 CA join backs this R5 structure batch.",
            },
        )
    return structure


@app.get(
    "/api/v1/selection/s4-structure",
    response_model=S4StructurePackBatchV1,
    response_model_by_alias=True,
)
def s4_structure_pack() -> S4StructurePackBatchV1:
    try:
        return build_s4_structure_pack(r5=_hash_matched_r5_or_503())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.post("/api/v1/selection/s4-structure")
def s4_structure_pack_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get(
    "/api/v1/selection/s5-enrichment",
    response_model=S5EnrichmentBatchV1,
    response_model_by_alias=True,
)
def s5_enrichment() -> S5EnrichmentBatchV1:
    try:
        return build_s5_enrichment(s4=build_s4_structure_pack(r5=_hash_matched_r5_or_503()))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.post("/api/v1/selection/s5-enrichment")
def s5_enrichment_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get(
    "/api/v1/selection/s6-resolution",
    response_model=S6ResolutionBatchV1,
    response_model_by_alias=True,
)
def s6_resolution() -> S6ResolutionBatchV1:
    try:
        r5_batch = _hash_matched_r5_or_503()
        pack = build_s4_structure_pack(r5=r5_batch)
        weather = build_s2_market_weather()
        return build_s6_resolution(s4=pack, r5=r5_batch, weather=weather)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.post("/api/v1/selection/s6-resolution")
def s6_resolution_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get(
    "/api/v1/selection/s7-state",
    response_model=S7StateBatchV1,
    response_model_by_alias=True,
)
def s7_state() -> S7StateBatchV1:
    try:
        r5_batch = _hash_matched_r5_or_503()
        weather = build_s2_market_weather()
        event_snapshot = latest_macro_event_context_snapshot()
        return build_s7_state(
            r5=r5_batch,
            weather=weather,
            event_snapshot=event_snapshot,
            lane=_data_lane_state(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.get(
    "/api/v1/selection/s7-state/{symbol}",
    response_model=S7IdeaCardV1,
    response_model_by_alias=True,
)
def s7_state_symbol(symbol: str) -> S7IdeaCardV1:
    batch = s7_state()
    key = symbol.strip().upper()
    for row in batch.rows:
        if row.symbol == key:
            return row
    raise HTTPException(
        status_code=404,
        detail={"code": "S7_SYMBOL_NOT_FOUND", "symbol": key},
    )


@app.post("/api/v1/selection/s7-state")
def s7_state_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get(
    "/api/v1/selection/tradability",
    response_model=TradabilityBatchV1,
    response_model_by_alias=True,
)
def selection_tradability(profileId: str = "PRF-003") -> TradabilityBatchV1:
    try:
        r5_batch = _hash_matched_r5_or_503()
        return build_tradability_batch(
            symbols=(row.symbol for row in r5_batch.rows),
            profile_id=profileId,
            decision_at=(r5_batch.built_at or datetime.now(timezone.utc)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.get(
    "/api/v1/selection/tradability/{symbol}",
    response_model=TradabilityResultV1,
    response_model_by_alias=True,
)
def selection_tradability_symbol(
    symbol: str, profileId: str = "PRF-003"
) -> TradabilityResultV1:
    key = symbol.strip().upper()
    batch = selection_tradability(profileId=profileId)
    for row in batch.rows:
        if row.symbol == key:
            return row
    raise HTTPException(
        status_code=404,
        detail={"code": "TRADABILITY_SYMBOL_NOT_FOUND", "symbol": key},
    )


@app.post("/api/v1/selection/tradability")
def selection_tradability_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


# ---------------------------------------------------------------------------
# Guidance OMS (R2-B activation amendment): paper ticket + preview + gated
# live path. Default boot is preview only; place returns 409 unless env +
# lane + UI arm all hold.
# ---------------------------------------------------------------------------


def _guidance_card(symbol: str) -> tuple[S7IdeaCardV1, S7StateBatchV1]:
    board = s7_state()
    key = symbol.strip().upper()
    for row in board.rows:
        if row.symbol == key:
            return row, board
    raise HTTPException(
        status_code=404, detail={"code": "GUIDANCE_SYMBOL_NOT_FOUND", "symbol": key}
    )


def _guidance_ticket(card: S7IdeaCardV1, board: S7StateBatchV1) -> GuidanceOMSTicketV1:
    plan, _close = compute_paper_plan(
        symbol=card.symbol,
        public_state=card.public_state.value,
        evidence_direction=str(card.evidence_direction),
        draft_confirmed_eligible=card.draft_confirmed_eligible,
        invalidation_condition=card.invalidation_condition,
        trading_date=board.trading_date,
        lane=_data_lane_state().effective_lane,
    )
    return build_paper_ticket(
        symbol=card.symbol, public_state=card.public_state.value, plan=plan
    )


@app.get(
    "/api/v1/selection/guidance-oms/preview",
    include_in_schema=False,
)
def guidance_oms_preview_get() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.post("/api/v1/selection/guidance-oms/preview")
def guidance_oms_preview(body: dict | None = None) -> dict:
    symbol = str((body or {}).get("symbol") or "").strip()
    if not symbol:
        raise HTTPException(
            status_code=422, detail={"code": "GUIDANCE_SYMBOL_REQUIRED"}
        )
    card, board = _guidance_card(symbol)
    ticket = _guidance_ticket(card, board)
    return {
        **ticket.model_dump(mode="json", by_alias=True),
        "arm": arm_snapshot(lane=_data_lane_state()).model_dump(by_alias=True),
    }


@app.post("/api/v1/selection/guidance-oms/place")
def guidance_oms_place(body: dict | None = None) -> dict:
    symbol = str((body or {}).get("symbol") or "").strip()
    if not symbol:
        raise HTTPException(
            status_code=422, detail={"code": "GUIDANCE_SYMBOL_REQUIRED"}
        )
    card, board = _guidance_card(symbol)
    ticket = _guidance_ticket(card, board)
    lane_state = _data_lane_state()
    try:
        ensure_live_placement_allowed(arm_snapshot(lane=lane_state))
    except GuidanceLiveBlocked as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "detail": exc.detail},
        ) from exc
    try:
        result = dispatch_live_placement(ticket, lane=lane_state)
    except GuidanceLiveBlocked as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "detail": exc.detail},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "PLACEORDER_FAILED", "detail": str(exc)[:200]},
        ) from exc
    return {"ticket": ticket.model_dump(mode="json", by_alias=True), "result": result}


@app.get(
    "/api/v1/selection/guidance-oms/{symbol}",
    response_model=GuidanceOMSTicketV1,
    response_model_by_alias=True,
)
def guidance_oms_symbol(symbol: str) -> GuidanceOMSTicketV1:
    card, board = _guidance_card(symbol)
    return _guidance_ticket(card, board)


@app.get("/api/v1/settings/live-orders-arm")
def get_live_orders_arm() -> dict:
    snapshot = arm_snapshot(lane=_data_lane_state())
    return snapshot.model_dump(mode="json", by_alias=True) | {
        "liveOrdersAllowed": snapshot.live_orders_allowed(),
        "copy": "Default boot is preview only. Live orders need env + OPENALGO_RO lane + this switch.",
    }


@app.post("/api/v1/settings/live-orders-arm")
def post_live_orders_arm(body: dict | None = None) -> dict:
    requested = bool((body or {}).get("armed") is True)
    set_live_orders_armed(requested)
    snapshot = arm_snapshot(lane=_data_lane_state())
    return snapshot.model_dump(mode="json", by_alias=True) | {
        "liveOrdersAllowed": snapshot.live_orders_allowed(),
        "copy": "Default boot is preview only. Live orders need env + OPENALGO_RO lane + this switch.",
    }


# ---------------------------------------------------------------------------
# R8 native core scanners (guidance chips; never CONFIRMED, never orders)
# ---------------------------------------------------------------------------


class NativeScannerDefinitionsV1(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    schema_version: str = R8_REGISTRY_SCHEMA
    definitions: tuple[ScannerDefinitionV1, ...]


@app.get(
    "/api/v1/scanners/definitions",
    response_model=NativeScannerDefinitionsV1,
    response_model_by_alias=True,
)
def scanners_definitions() -> NativeScannerDefinitionsV1:
    return NativeScannerDefinitionsV1(definitions=NATIVE_CORE_DEFINITIONS)


@app.post("/api/v1/scanners/definitions")
def scanners_definitions_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get(
    "/api/v1/scanners/native-core",
    response_model=NativeCoreRunV1,
    response_model_by_alias=True,
)
def scanners_native_core() -> NativeCoreRunV1:
    try:
        r5_batch = _hash_matched_r5_or_503()
        return build_native_core_run(r5=r5_batch)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.get(
    "/api/v1/scanners/native-core/{symbol}",
    response_model=NativeCoreRowV1,
    response_model_by_alias=True,
)
def scanners_native_core_symbol(symbol: str) -> NativeCoreRowV1:
    run = scanners_native_core()
    key = symbol.strip().upper()
    for row in run.rows:
        if row.symbol == key:
            return row
    raise HTTPException(
        status_code=404,
        detail={"code": "R8_SYMBOL_NOT_FOUND", "symbol": key},
    )


@app.post("/api/v1/scanners/run")
def scanners_run_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


# ---------------------------------------------------------------------------
# R15 Scanner Lab bundle: ONE 200 with named inner codes (definitions +
# seeded pipe runs + PK shadow parity state). Zero claims; POST forbidden.
# ---------------------------------------------------------------------------


class LabPipeRunEntryV1(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    pipe_id: str
    run: PipeRunV1 | None = None
    code: str | None = None


class ScannerLabBundleV1(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    schema_version: str = "trendforge.scanner-lab.v1"
    profile_id: str = "PRF-R15-LAB"
    acceptance_ceiling: str = "LIVE_R15_LAB_GUIDANCE_ONLY"
    confirmed_count: int = 0
    executable: Literal[False] = False
    emits_claims: Literal[False] = False
    native_definitions: tuple[ScannerDefinitionV1, ...] = ()
    native_core: NativeCoreRunV1 | None = None
    native_core_code: str | None = None
    pipe_definitions: tuple[PipeDefinitionV1, ...] = ()
    pipe_runs: tuple[LabPipeRunEntryV1, ...] = ()
    pk_shadow: dict[str, str] = Field(
        default_factory=lambda: {"state": "PK_SHADOW", "parity": "PARITY_UNKNOWN"}
    )
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def enforce_lab_law(self) -> "ScannerLabBundleV1":
        if self.confirmed_count != 0:
            raise ValueError("Scanner Lab confirmedCount is pinned to zero")
        return self


@app.get(
    "/api/v1/scanners/lab-bundle",
    response_model=ScannerLabBundleV1,
    response_model_by_alias=True,
)
def scanners_lab_bundle() -> ScannerLabBundleV1:
    from .scanners.native_core import NATIVE_CORE_DEFINITIONS

    pipe_runs: list[LabPipeRunEntryV1] = []
    try:
        r5_batch = _hash_matched_r5_or_503()
        native_core = build_native_core_run(r5=r5_batch)
        board = s7_state()
    except (ValueError, HTTPException) as exc:
        # Named failure INSIDE the 200: lab renders WAIT codes, never invents.
        code = (
            str(exc.detail.get("code"))
            if isinstance(exc, HTTPException) and isinstance(exc.detail, dict)
            else str(exc)
        )
        for definition in PIPE_DEFINITIONS:
            pipe_runs.append(
                LabPipeRunEntryV1(pipeId=definition.pipe_id, code=code)
            )
        return ScannerLabBundleV1(
            nativeDefinitions=NATIVE_CORE_DEFINITIONS,
            nativeCoreCode=code,
            pipeDefinitions=PIPE_DEFINITIONS,
            pipeRuns=tuple(pipe_runs),
            warnings=(
                "Pipes - guidance lens, zero claims.",
                f"PIPE_RUNS_UNAVAILABLE:{code}",
            ),
        )

    for definition in PIPE_DEFINITIONS:
        try:
            run = build_pipe_run(
                definition.pipe_id, native_core=native_core, s7_board=board
            )
            pipe_runs.append(LabPipeRunEntryV1(pipeId=definition.pipe_id, run=run))
        except ValueError as exc:
            pipe_runs.append(
                LabPipeRunEntryV1(pipeId=definition.pipe_id, code=str(exc))
            )
    return ScannerLabBundleV1(
        nativeDefinitions=NATIVE_CORE_DEFINITIONS,
        nativeCore=native_core,
        pipeDefinitions=PIPE_DEFINITIONS,
        pipeRuns=tuple(pipe_runs),
        warnings=("Pipes - guidance lens, zero claims.",),
    )


@app.post("/api/v1/scanners/lab-bundle")
def scanners_lab_bundle_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


# ---------------------------------------------------------------------------
# R10 pipe DSL (FUS-010): named filter recipes over native-core matches.
# Pipes emit zero claims; stage counts deterministic; POST runner forbidden.
# ---------------------------------------------------------------------------


class PipeDefinitionsV1(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    schema_version: str = "trendforge.pipe-registry.v1"
    definitions: tuple[PipeDefinitionV1, ...]


@app.get(
    "/api/v1/pipes/definitions",
    response_model=PipeDefinitionsV1,
    response_model_by_alias=True,
)
def pipes_definitions() -> PipeDefinitionsV1:
    return PipeDefinitionsV1(definitions=PIPE_DEFINITIONS)


@app.post("/api/v1/pipes/definitions")
def pipes_definitions_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get("/api/v1/pipes/run")
def pipes_run_post_guard() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.post("/api/v1/pipes/run")
def pipes_run_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get(
    "/api/v1/pipes/{pipe_id}/run",
    response_model=PipeRunV1,
    response_model_by_alias=True,
)
def pipes_pipe_run(pipe_id: str) -> PipeRunV1:
    known = {d.pipe_id for d in PIPE_DEFINITIONS}
    if pipe_id not in known:
        raise HTTPException(
            status_code=404, detail={"code": "PIPE_UNKNOWN_ID", "pipeId": pipe_id}
        )
    try:
        r5_batch = _hash_matched_r5_or_503()
        native_core = build_native_core_run(r5=r5_batch)
        # Both seeded pipes carry FILTER_STATE/ENRICH_S7: a live S7 join is
        # required; an unhealthy spine fails closed as typed 503 below.
        return build_pipe_run(pipe_id, native_core=native_core, s7_board=s7_state())
    except ValueError as exc:
        code = str(exc)
        if code == "PIPE_UNKNOWN_ID":
            raise HTTPException(
                status_code=404, detail={"code": code, "pipeId": pipe_id}
            ) from exc
        raise HTTPException(status_code=503, detail={"code": code}) from exc


# ---------------------------------------------------------------------------
# R11 MCX master readiness (WAIT without official master + local bars).
# Cash S7 path untouched; FBIL/CFTC/WGC are context-only.
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/selection/mcx-master",
    response_model=McxMasterBatchV1,
    response_model_by_alias=True,
)
def mcx_master_board() -> McxMasterBatchV1:
    return build_mcx_master()


@app.post("/api/v1/selection/mcx-master")
def mcx_master_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get(
    "/api/v1/selection/mcx-master/{symbol}",
    response_model=McxMasterRowV1,
    response_model_by_alias=True,
)
def mcx_master_symbol(symbol: str) -> McxMasterRowV1:
    batch = build_mcx_master()
    key = symbol.strip().upper()
    for row in batch.rows:
        if row.symbol == key:
            return row
    raise HTTPException(
        status_code=404, detail={"code": "R11_SYMBOL_NOT_FOUND", "symbol": key}
    )


@app.post("/api/v1/selection/mcx-master/{symbol}")
def mcx_master_symbol_post(symbol: str) -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


def _s8_from_current_spine(
    native_core: NativeCoreRunV1 | None = None,
) -> S8ScanBlobV1:
    """Compatibility wrapper around the one shared S8 owner."""
    return build_and_persist_current_s8(native_core=native_core)


@app.get(
    "/api/v1/selection/scans/latest",
    response_model=S8ScanBlobV1,
    response_model_by_alias=True,
)
def scans_latest() -> S8ScanBlobV1:
    try:
        return latest_or_build_current_s8()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@app.get("/api/v1/selection/scans")
def scans_list(limit: int = 20):
    from .selection.s8_persist_run import PROFILE_ID as _S8_PROFILE
    from .selection.store import list_latest_selection_payloads

    limit = max(1, min(limit, 100))
    payloads = list_latest_selection_payloads(_S8_PROFILE, limit=limit)
    out = []
    for p in payloads:
        out.append(
            {
                "runId": p.get("runId") or p.get("run_id"),
                "asOf": p.get("asOf") or p.get("as_of"),
                "confirmedCount": p.get("confirmedCount", p.get("confirmed_count", 0)),
                "rowCount": len(p.get("rows") or []),
                "persistedAt": p.get("persistedAt") or p.get("builtAt"),
            }
        )
    return {"runs": out, "count": len(out)}


@app.post("/api/v1/selection/scans")
def scans_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get(
    "/api/v1/selection/scans/{run_id}",
    response_model=S8ScanBlobV1,
    response_model_by_alias=True,
)
def scans_by_run(run_id: str) -> S8ScanBlobV1:
    from .selection.s8_persist_run import PROFILE_ID as _S8_PROFILE
    from .selection.store import get_selection_payload

    payload = get_selection_payload(_S8_PROFILE, run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "S8_RUN_NOT_FOUND", "runId": run_id})
    return S8ScanBlobV1.model_validate(payload)


@app.get("/api/v1/selection/scans/{run_id}/candidates")
def scan_candidates(run_id: str) -> dict:
    from .selection.s8_persist_run import PROFILE_ID as _S8_PROFILE
    from .selection.store import get_selection_payload

    payload = get_selection_payload(_S8_PROFILE, run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "S8_RUN_NOT_FOUND", "runId": run_id})
    rows = payload.get("rows") or []
    return {
        "runId": run_id,
        "count": len(rows),
        "candidates": [
            {
                "candidateId": r.get("candidateId"),
                "symbol": r.get("symbol"),
                "publicState": r.get("publicState"),
            }
            for r in rows
        ],
    }


@app.get("/api/v1/selection/scans/{run_id}/candidates/{symbol}")
def scan_candidate_symbol(run_id: str, symbol: str) -> dict:
    from .selection.s8_persist_run import PROFILE_ID as _S8_PROFILE
    from .selection.store import get_selection_payload

    payload = get_selection_payload(_S8_PROFILE, run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "S8_RUN_NOT_FOUND", "runId": run_id})
    key = symbol.strip().upper()
    for row in payload.get("rows") or []:
        if str(row.get("symbol", "")).upper() == key:
            return row
    raise HTTPException(
        status_code=404,
        detail={"code": "S8_CANDIDATE_NOT_FOUND", "runId": run_id, "symbol": key},
    )


@app.post("/api/v1/selection/scans/{run_id}")
def scans_by_run_post(run_id: str) -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get("/api/v1/selection/pit-homework")
def pit_homework() -> dict[str, Any]:
    return r16_legacy_homework_payload()


@app.get("/api/v1/selection/pit-homework/{symbol}")
def pit_homework_symbol(symbol: str) -> dict[str, Any]:
    payload = r16_legacy_homework_payload(symbol=symbol)
    if payload.get("rowCount", 0) == 0:
        raise HTTPException(
            status_code=404,
            detail={"code": "R16_SYMBOL_NOT_FOUND", "symbol": symbol.strip().upper(),},
        )
    return payload


@app.post("/api/v1/selection/pit-homework")
def pit_homework_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get("/api/v1/selection/pit-gate")
def pit_gate() -> dict[str, Any]:
    return r16_legacy_gate_payload()


@app.post("/api/v1/selection/pit-gate")
def pit_gate_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get("/api/v1/selection/pit/status")
def r16_pit_status() -> dict[str, Any]:
    return r16_status_payload()


@app.post("/api/v1/selection/pit/status")
def r16_pit_status_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get("/api/v1/selection/pit/runs")
def r16_pit_runs(
    limit: int = Query(default=20, ge=1, le=1000),
    cursor: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    return r16_runs_payload(limit=limit, cursor=cursor)


@app.post("/api/v1/selection/pit/runs")
def r16_pit_runs_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get("/api/v1/selection/pit/observations")
def r16_pit_observations(
    dataset_run_id: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    cursor: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    return r16_observations_payload(
        dataset_run_id=dataset_run_id, limit=limit, cursor=cursor
    )


@app.post("/api/v1/selection/pit/observations")
def r16_pit_observations_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get("/api/v1/selection/pit/metrics")
def r16_pit_metrics(dataset_run_id: str | None = None) -> dict[str, Any]:
    return r16_metrics_payload(dataset_run_id=dataset_run_id)


@app.post("/api/v1/selection/pit/metrics")
def r16_pit_metrics_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})


@app.get("/api/v1/selection/pit/approval")
def r16_pit_approval(dataset_run_id: str | None = None) -> dict[str, Any]:
    return r16_approval_payload(dataset_run_id=dataset_run_id)


@app.post("/api/v1/selection/pit/approval")
def r16_pit_approval_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})

# R18 model governance. Evaluation remains an offline operator process; the
# only write route records an explicit human review and cannot place orders.
@app.get("/api/research/ml/governance")
def r18_model_governance() -> dict[str, Any]:
    status = r18_governance_status()
    schema = r18_schema_status()
    drift = r18_list_payloads("ml_drift_events") if schema["applied"] else []
    blockers = list(status.get("blockers") or [])
    if not schema["applied"]:
        blockers.append("WAIT_R18_SCHEMA_NOT_APPLIED")
    return {
        **status,
        "blockers": list(dict.fromkeys(blockers)),
        "schema": schema,
        "models": r18_list_payloads("ml_model_registry") if schema["applied"] else [],
        "evaluations": r18_list_payloads("ml_evaluation_reports") if schema["applied"] else [],
        "reviews": r18_list_payloads("ml_promotion_reviews") if schema["applied"] else [],
        "driftEvents": drift,
        "rollbackHistory": [row for row in drift if row.get("rollbackModelHash")],
    }


@app.post("/api/research/ml/reviews")
def r18_model_review(body: dict[str, Any]) -> dict[str, Any]:
    if not r18_schema_status()["applied"]:
        raise HTTPException(status_code=503, detail={"code": "WAIT_R18_SCHEMA_NOT_APPLIED"})
    model_id = str(body.get("modelId") or "").strip()
    model_hash = str(body.get("modelHash") or "").strip()
    evaluation_id = str(body.get("evaluationId") or "").strip()
    manifest_payload = r18_get_payload(
        "ml_model_registry", model_id + ":" + model_hash
    )
    evaluation_payload = r18_get_payload("ml_evaluation_reports", evaluation_id)
    if manifest_payload is None or evaluation_payload is None:
        raise HTTPException(
            status_code=404, detail={"code": "R18_REVIEW_EVIDENCE_NOT_FOUND"}
        )
    try:
        manifest = ModelManifestV1.model_validate(manifest_payload)
        evaluation = ChallengerEvaluationV1.model_validate(evaluation_payload)
        if evaluation.model_id != manifest.model_id:
            raise ValueError("R18_REVIEW_MODEL_ID_MISMATCH")
        if evaluation.model_hash != manifest.model_hash:
            raise ValueError("R18_REVIEW_MODEL_HASH_MISMATCH")
        review = build_promotion_review(
            manifest=manifest,
            evaluation=evaluation,
            decision=body.get("decision"),
            reviewer=str(body.get("reviewer") or ""),
            reason=str(body.get("reason") or ""),
            r16_validation_status=r16_status_payload().get(
                "validationStatus", "PIT_NOT_APPROVED"
            ),
            previous_record_hash=body.get("previousRecordHash"),
        )
        r18_persist_review(review.model_dump(mode="json", by_alias=True))
        return review.model_dump(mode="json", by_alias=True)
    except ValueError as exc:
        code = str(exc)
        status_code = 409 if "PIT_NOT_APPROVED" in code else 422
        raise HTTPException(status_code=status_code, detail={"code": code}) from exc

@app.get("/api/research/ml/reviews")
def r18_model_reviews() -> dict[str, Any]:
    schema = r18_schema_status()
    return {
        "contract": "trendforge.r18-model-governance.v1",
        "reviews": r18_list_payloads("ml_promotion_reviews") if schema["applied"] else [],
        "blockers": [] if schema["applied"] else ["WAIT_R18_SCHEMA_NOT_APPLIED"],
    }


_DATA_LANE_PREFERENCE = "FREE_OFFICIAL"


def _data_lane_state() -> DataLaneStateV1:
    import os
    env_lane = os.environ.get("TRENDFORGE_DATA_LANE") or _DATA_LANE_PREFERENCE
    oa_enabled = os.environ.get("OPENALGO_ENABLED")
    cap_state = activation_from_environment().stage.value
    return resolve_lane(
        env_lane=env_lane, openalgo_enabled=oa_enabled, capability_state=cap_state
    )


@app.get("/api/v1/settings/data-lane", response_model=DataLaneStateV1, response_model_by_alias=True)
def get_data_lane() -> DataLaneStateV1:
    return _data_lane_state()


@app.post("/api/v1/settings/data-lane", response_model=DataLaneStateV1, response_model_by_alias=True)
def post_data_lane(body: dict | None = None) -> DataLaneStateV1:
    """Persist lane preference only; cannot enable execution."""
    global _DATA_LANE_PREFERENCE
    requested = (body or {}).get("lane") or (body or {}).get("Lane")
    if requested in ("FREE_OFFICIAL", "OPENALGO_RO"):
        _DATA_LANE_PREFERENCE = requested
    return _data_lane_state()


@app.get("/api/v1/selection/research-quantity", response_model=ResearchQtyBatchV1, response_model_by_alias=True)
def research_quantity() -> ResearchQtyBatchV1:
    from .selection.research_quantity import (
        ResearchFundsV1,
        ResearchQtyRowV1,
        compute_research_quantity,
    )
    try:
        r5_batch = _hash_matched_r5_or_503()
        weather = build_s2_market_weather()
        pack = build_s4_structure_pack(r5=r5_batch)
        s7_board = build_s7_state(r5=r5_batch, s4=pack, weather=weather)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "WAIT_RESEARCH_QTY_BUILD_ERROR", "detail": str(exc)[:200]},
        ) from exc

    rows: list[ResearchQtyRowV1] = []
    funds = ResearchFundsV1()
    for card in s7_board.rows:
        try:
            result = compute_research_quantity(
                public_state=card.public_state.value,
                evidence_direction=str(card.evidence_direction),
                draft_confirmed_eligible=card.draft_confirmed_eligible,
                is_reject_or_ban=card.public_state.value == "REJECT",
                official_close=None,
                invalidation_condition=getattr(card, "invalidation_condition", None),
                atr=None,
                lot_size=None,
                s8_completeness_ratio=None,
                regime_label=getattr(weather, "regime_label", None) if weather else None,
                index_suspect=False,
            )
            qty = int(result.get("researchQuantity", 0) or 0)
            if qty > 0:
                funds = ResearchFundsV1(
                    capital_inr=100_000.0,
                    reserved_risk_inr=float(result.get("reservedRiskInr") or 0),
                    position_notional_inr=float(result.get("notionalInr") or 0),
                    remaining_capital_inr=float(result.get("remainingCapitalInr") or 100_000.0),
                )
            rows.append(ResearchQtyRowV1(
                symbol=card.symbol,
                public_state=card.public_state.value,
                evidence_direction=str(card.evidence_direction),
                draft_confirmed_eligible=card.draft_confirmed_eligible,
                side=result.get("side") or result.get("_side", "FLAT"),
                research_quantity=qty,
                qty_unit=str(result.get("qtyUnit") or "shares"),
                research_entry=result.get("researchEntry"),
                research_stop=result.get("researchStop"),
                research_t1=result.get("researchT1"),
                reason=result.get("reason", ""),
                data_quality_cap=float(result.get("dataQualityCap") or 1.0),
                regime_cap=float(result.get("regimeCap") or 1.0),
                liquidity_cap=float(result.get("liquidityCap") or 1.0),
            ))
        except Exception as row_exc:
            rows.append(ResearchQtyRowV1(
                symbol=getattr(card, "symbol", "UNKNOWN"),
                public_state=SelectionState.WAIT,
                evidence_direction=EvidenceDirection.BULLISH,
                reason=f"ROW_ERROR:{row_exc}",
            ))
    return ResearchQtyBatchV1(rows=tuple(rows), executable=False)


@app.post("/api/v1/selection/research-quantity")
def research_quantity_post() -> None:
    raise HTTPException(status_code=405, detail={"code": "POST_NOT_ALLOWED"})

@app.get(
    "/api/v1/selection/attention/{symbol}",
    response_model=AttentionRowV1,
    response_model_by_alias=True,
)
def r2_attention_symbol(symbol: str) -> AttentionRowV1:
    order = latest_attention_order()
    if order is None:
        raise HTTPException(status_code=503, detail={"code": "R2_ATTENTION_NOT_READY"})
    key = symbol.strip().upper()
    for row in order.rows:
        if row.symbol == key:
            return row
    raise HTTPException(status_code=404, detail={"code": "R2_SYMBOL_NOT_FOUND", "symbol": key})


@app.post(
    "/api/v1/selection/cash-staging/refresh",
    response_model=CashStagingBatch,
    response_model_by_alias=True,
)
def a1_cash_staging_refresh() -> CashStagingBatch:
    """A1 only: persist cash last-good as SourceResult + staging rows."""
    return persist_cash_staging(stage_cash_last_good())


@app.get(
    "/api/v1/selection/cash-staging/latest",
    response_model=CashStagingBatch,
    response_model_by_alias=True,
)
def a1_cash_staging_latest() -> CashStagingBatch:
    stored = latest_cash_staging()
    if stored is None:
        raise HTTPException(status_code=404, detail="No cash staging result is stored")
    return stored


@app.post(
    "/api/v1/selection/cash-identity/refresh",
    response_model=CashIdentityBatch,
    response_model_by_alias=True,
)
def a2_cash_identity_refresh() -> CashIdentityBatch:
    """A2 only: identity + NormalizedFact + S0/S1 safety. No rank."""
    return persist_cash_identity(build_cash_identity_batch())


@app.get(
    "/api/v1/selection/cash-identity/latest",
    response_model=CashIdentityBatch,
    response_model_by_alias=True,
)
def a2_cash_identity_latest() -> CashIdentityBatch:
    stored = latest_cash_identity()
    if stored is None:
        raise HTTPException(status_code=404, detail="No cash identity batch is stored")
    return stored


@app.post(
    "/api/v1/selection/cash-discovery/refresh",
    response_model=CashDiscoveryBatch,
    response_model_by_alias=True,
)
def a3_cash_discovery_refresh() -> CashDiscoveryBatch:
    """A3 only: Â§25.25.4 WATCH reasons. No rank, no FTR-018."""
    return persist_cash_discovery(build_cash_discovery_batch())


@app.get(
    "/api/v1/selection/cash-discovery/latest",
    response_model=CashDiscoveryBatch,
    response_model_by_alias=True,
)
def a3_cash_discovery_latest() -> CashDiscoveryBatch:
    stored = latest_cash_discovery()
    if stored is None:
        raise HTTPException(status_code=404, detail="No cash discovery batch is stored")
    return stored


@app.post(
    "/api/v1/selection/cash-history/refresh",
    response_model=CashHistoryBatch,
    response_model_by_alias=True,
)
def a4_cash_history_refresh() -> CashHistoryBatch:
    """A4 only: raw session vintages + visible CA. No rank."""
    return persist_cash_history(build_cash_history_batch())


@app.get(
    "/api/v1/selection/cash-history/latest",
    response_model=CashHistoryBatch,
    response_model_by_alias=True,
)
def a4_cash_history_latest() -> CashHistoryBatch:
    stored = latest_cash_history()
    if stored is None:
        raise HTTPException(status_code=404, detail="No cash history batch is stored")
    return stored


@app.post(
    "/api/v1/selection/cash-context/refresh",
    response_model=CashContextBatch,
    response_model_by_alias=True,
)
def a5_cash_context_refresh() -> CashContextBatch:
    return persist_cash_context(build_cash_context_batch(index_content=None))


@app.post(
    "/api/v1/selection/fo-enrichment/refresh",
    response_model=FoEnrichmentBatch,
    response_model_by_alias=True,
)
def a6_fo_enrichment_refresh() -> FoEnrichmentBatch:
    return persist_fo_enrichment(build_fo_enrichment_batch(fo_content=None))


@app.get(
    "/api/source-inventory/use-matrix",
    response_model=SourceUseMatrix,
    response_model_by_alias=True,
)
def c0_source_use_matrix() -> SourceUseMatrix:
    return persist_source_use_matrix(build_source_use_matrix())


@app.post(
    "/api/v1/selection/mwpl/assess",
    response_model=MwplAssessment,
    response_model_by_alias=True,
)
def b_mwpl_assess() -> MwplAssessment:
    return persist_mwpl(assess_mwpl(None))


@app.post(
    "/api/v1/selection/cash-rank/refresh",
    response_model=CashRankBatch,
    response_model_by_alias=True,
)
def c1_cash_rank_refresh() -> CashRankBatch:
    return persist_cash_rank(build_cash_rank_batch())


@app.get(
    "/api/v1/selection/fixtures/q5-r1",
    response_model=SelectionFixtureBatch,
    response_model_by_alias=True,
)
def q5_r1_selection_fixtures() -> SelectionFixtureBatch:
    return build_q5_r1_fixture_batch()


@app.get(
    "/api/v1/selection/fixtures/q5-r2",
    response_model=Q5R2FixtureBatch,
    response_model_by_alias=True,
)
def q5_r2_selection_fixtures() -> Q5R2FixtureBatch:
    return build_q5_r2_fixture_batch()


@app.get(
    "/api/v1/selection/fixtures/q5-r3",
    response_model=Q5R3FixtureBatch,
    response_model_by_alias=True,
)
def q5_r3_selection_fixtures() -> Q5R3FixtureBatch:
    return build_q5_r3_fixture_batch()


@app.get(
    "/api/v1/selection/fixtures/q5-r4",
    response_model=Q5R4FixtureBatch,
    response_model_by_alias=True,
)
def q5_r4_selection_fixtures() -> Q5R4FixtureBatch:
    return build_q5_r4_fixture_batch()


@app.get(
    "/api/v1/selection/fixtures/q5-r6",
    response_model=Q5R6FixtureBatch,
    response_model_by_alias=True,
)
def q5_r6_selection_fixtures() -> Q5R6FixtureBatch:
    return build_q5_r6_fixture_batch()


@app.get(
    "/api/v1/selection/feature-registry",
    response_model=FeatureRegistryManifest,
    response_model_by_alias=True,
)
def selection_feature_registry() -> FeatureRegistryManifest:
    return build_feature_registry()


@app.get(
    "/api/v1/selection/feature-registry/lint",
    response_model=FeatureRegistryLintReport,
    response_model_by_alias=True,
)
def selection_feature_registry_lint() -> FeatureRegistryLintReport:
    return lint_feature_registry()


@app.get(
    "/api/v1/integrations/openalgo/capability",
    response_model=OpenAlgoCapabilityReport,
    response_model_by_alias=True,
)
def openalgo_capability() -> OpenAlgoCapabilityReport:
    """Report the disabled-by-default read-only boundary without broker I/O."""

    return assess_openalgo_capability()


@app.get(
    "/api/v1/integrations/openalgo/contract",
    response_model=OpenAlgoProviderContractV1,
    response_model_by_alias=True,
)
def openalgo_contract() -> OpenAlgoProviderContractV1:
    """Return the pinned read-only provider contract without broker I/O."""

    return openalgo_provider_contract()


@app.get(
    "/api/v1/integrations/openalgo/shadow",
    response_model=OpenAlgoShadowBatchV1,
    response_model_by_alias=True,
)
def openalgo_shadow() -> OpenAlgoShadowBatchV1:
    """Return the inert/read-only R17 overlay without broker I/O."""

    return disabled_shadow_batch()


@app.post("/api/derivatives/price")
def derivatives_price(payload: OptionPricingInput) -> dict:
    values = payload.model_dump()
    price = black_scholes_price(**values)
    greeks = black_scholes_greeks(**values)
    return {
        "model": "BLACK_SCHOLES_MERTON_EUROPEAN",
        "price": price,
        "greeks": {
            "delta": greeks.delta,
            "gamma": greeks.gamma,
            "thetaPerCalendarDay": greeks.theta_per_day,
            "vegaPerVolPoint": greeks.vega_per_vol_point,
            "rhoPerRatePoint": greeks.rho_per_rate_point,
        },
        "limitations": "European-model estimate; stale quotes, dividends, liquidity, and American exercise effects can invalidate precision.",
    }


@app.post("/api/derivatives/implied-volatility")
def derivatives_iv(payload: ImpliedVolatilityInput) -> dict:
    try:
        value = implied_volatility(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "impliedVolatility": value,
        "annualized": True,
        "solver": "BOUNDED_BISECTION",
    }


@app.get("/api/command-bar")
def command_bar():
    return current_command_bar()


@app.get(
    "/api/radar", response_model=list[RadarCandidate], response_model_by_alias=True
)
def radar(
    mode: CandidateType | None = Query(default=None),
    status: StatusGroup | None = Query(default=None),
    timeframe: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> list[RadarCandidate]:
    rows = list_candidates(mode=mode, status=status, timeframe=timeframe, search=search)
    if mode is None and status is None and timeframe is None and search is None:
        save_ml_scan_snapshot(
            list_candidates(),
            current_command_bar(),
            list_source_health(),
            trigger="api_radar_full_scan",
            dedupe=True,
        )
    return rows


@app.get(
    "/api/radar/{symbol}", response_model=RadarCandidate, response_model_by_alias=True
)
def radar_detail(symbol: str) -> RadarCandidate:
    candidate = get_candidate(symbol)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    return candidate


@app.get(
    "/api/shortlist", response_model=list[RadarCandidate], response_model_by_alias=True
)
def shortlist() -> list[RadarCandidate]:
    return list_candidates(status=StatusGroup.READY)


@app.get(
    "/api/wait-candidates",
    response_model=list[RadarCandidate],
    response_model_by_alias=True,
)
def wait_candidates() -> list[RadarCandidate]:
    return list_candidates(status=StatusGroup.WAIT)


@app.get(
    "/api/rejected-candidates",
    response_model=list[RadarCandidate],
    response_model_by_alias=True,
)
def rejected_candidates() -> list[RadarCandidate]:
    return list_candidates(status=StatusGroup.REJECT)


@app.get("/api/integrations/trade-vision/evidence/latest")
def trade_vision_evidence_latest() -> dict:
    try:
        return build_trade_vision_evidence_packet()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get(
    "/api/source-health",
    response_model=list[SourceHealth],
    response_model_by_alias=True,
)
def source_health() -> list[SourceHealth]:
    return list_source_health()


@app.get(
    "/api/harmonic-sources",
    response_model=list[HarmonicSource],
    response_model_by_alias=True,
)
def harmonic_sources() -> list[HarmonicSource]:
    return HARMONIC_SOURCES


@app.get(
    "/api/sources/registry",
    response_model=list[SourceRegistryRecord],
    response_model_by_alias=True,
)
def sources_registry() -> list[SourceRegistryRecord]:
    return list_source_registry_records()


@app.get(
    "/api/source-monitor/catalog",
    response_model=list[SourceCatalogRecord],
    response_model_by_alias=True,
)
def source_monitor_catalog() -> list[SourceCatalogRecord]:
    return source_catalog_records()


@app.get(
    "/api/source-contracts/coverage",
    response_model=RegistryCoverage,
    response_model_by_alias=True,
)
def source_contract_coverage() -> RegistryCoverage:
    return build_registry_coverage()


@app.get(
    "/api/source-inventory/compiler-report",
    response_model=InventoryCompilerReport,
    response_model_by_alias=True,
)
def source_inventory_compiler_report() -> InventoryCompilerReport:
    """R0 residual: inventory defects, J01â€“J14, dataset roots, maturity counts.

    Research governance only. Does not authorize CONFIRMED or execution.
    """
    return compile_default_inventory()


@app.get("/api/source-operations/snapshot")
def source_operations_snapshot() -> dict[str, Any]:
    """One as-of projection for source flow and the cash A1-C1 post-commit track."""
    return build_source_operations_snapshot(_MD69_SCHEDULER)


@app.get(
    "/api/source-inventory/r0b-cohort",
    response_model=R0BCohortReport,
    response_model_by_alias=True,
)
def source_inventory_r0b_cohort() -> R0BCohortReport:
    """R0-B first official source-contract proof cohort. Does not activate."""
    return evaluate_r0b_cohort()


@app.get(
    "/api/source-inventory/r0c-cohort",
    response_model=R0CCohortReport,
    response_model_by_alias=True,
)
def source_inventory_r0c_cohort() -> R0CCohortReport:
    """R0-C compiler remainder. Quarantined and zero-authority."""
    return evaluate_r0c_cohort()


@app.get(
    "/api/v1/selection/profile-source-contracts",
    response_model=StrategySourceRegistry,
    response_model_by_alias=True,
)
def selection_profile_source_contracts() -> StrategySourceRegistry:
    """Named PRF-001..007 dependencies; registration is not activation."""
    return build_strategy_source_registry()


@app.get("/api/source-inventory/decision-jobs")
def source_inventory_decision_jobs() -> dict[str, object]:
    """Hybrid Â§19.2 decision-job taxonomy (File A CROSS-003 / TDG-GAP-025)."""
    return {
        "jobs": decision_job_catalog(),
        "rule": (
            "Jobs describe allowed research use. "
            "They cannot unlock execution or quantity under File A scope."
        ),
        "researchOnly": True,
    }


@app.post(
    "/api/source-monitor/check",
    response_model=SourceMonitorSummary,
    response_model_by_alias=True,
)
def source_monitor_check(
    source_key: str | None = Query(default=None, alias="sourceKey"),
    fetch: bool = Query(default=False),
    timeout_seconds: int = Query(default=15, ge=3, le=60, alias="timeoutSeconds"),
) -> SourceMonitorSummary:
    keys = [source_key] if source_key else None
    try:
        return check_sources(keys, fetch=fetch, timeout_seconds=timeout_seconds)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get(
    "/api/source-monitor/history",
    response_model=list[SourceSnapshotRecord],
    response_model_by_alias=True,
)
def source_monitor_history(
    source_key: str | None = Query(default=None, alias="sourceKey"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[SourceSnapshotRecord]:
    return source_snapshot_history(source_key=source_key, limit=limit)


@app.post(
    "/api/source-parser/run",
    response_model=list[SourceParseResult],
    response_model_by_alias=True,
)
def source_parser_run(
    source_key: str | None = Query(default=None, alias="sourceKey"),
) -> list[SourceParseResult]:
    if source_key:
        return [parse_source(source_key)]
    return parse_sources()


@app.get(
    "/api/source-parser/results",
    response_model=list[SourceParseResult],
    response_model_by_alias=True,
)
def source_parser_results(
    source_key: str | None = Query(default=None, alias="sourceKey"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[SourceParseResult]:
    return source_parse_history(source_key=source_key, limit=limit)


@app.get("/api/source-resolver/candidates")
def source_resolver_candidates(
    source_key: str = Query(alias="sourceKey"),
) -> dict:
    return {
        "sourceKey": source_key,
        "candidates": direct_download_candidates(source_key),
        "rule": "Candidates are attempted fail-closed; a resolver candidate is not trusted until fetched, archived, parsed, and data-date checked.",
    }


@app.get("/api/source-replacement-map")
def source_replacement_map() -> list[dict]:
    return list_source_replacement_map()


@app.get("/api/cftc/analytics")
def cftc_analytics(
    market: str | None = Query(default=None, min_length=1, max_length=120),
    as_of: str | None = Query(
        default=None, alias="asOf", pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    limit: int = Query(default=20, ge=1, le=500),
) -> dict:
    rows = list_cftc_analytics(market=market, as_of=as_of, limit=limit)
    source_evidence = dependency_state("cftc_cot")
    state = "WAIT_CFTC_HISTORY"
    if rows:
        state = (
            "CFTC_CONTEXT_READY"
            if source_evidence["state"] == "PASS"
            else source_evidence["state"]
        )
    return {
        "state": state,
        "scope": "COMMODITY_REGIME_ONLY",
        "sourceRole": "OFFICIAL_DELAYED_CONTEXT",
        "canUnlockReady": False,
        "warning": "Weekly delayed CFTC category positioning cannot create an intraday trigger or READY state.",
        "referenceProject": {
            "name": "kustex/CFTC-COT-Report",
            "role": "REFERENCE_ONLY_ANALYTICS",
            "url": "https://github.com/kustex/CFTC-COT-Report",
        },
        "sourceEvidence": source_evidence,
        "rows": rows,
    }


@app.post("/api/cftc/history/import")
def cftc_history_import(
    years: int = Query(default=5, ge=1, le=10),
    fetch: bool = Query(default=False),
) -> dict:
    return import_cftc_history(years=years, fetch=fetch)


@app.get("/api/raw-source-archive")
def raw_source_archive(
    source_key: str | None = Query(default=None, alias="sourceKey"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict]:
    return list_raw_source_archive(source_key=source_key, limit=limit)


@app.get("/api/source-fetch-attempts")
def source_fetch_attempts(
    source_key: str | None = Query(default=None, alias="sourceKey"),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[dict]:
    return list_source_fetch_attempts(source_key=source_key, limit=limit)


@app.post("/api/source-inventory/audit")
def source_inventory_audit(request: SourceInventoryAuditRequest) -> dict:
    try:
        return audit_saved_inventory(
            fetch_ids=set(request.fetch_ids),
            use_browser=request.use_browser,
            timeout_seconds=request.timeout_seconds,
            max_bytes=request.max_bytes,
            throttle_seconds=request.throttle_ms / 1000,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/source-inventory/audit-runs")
def source_inventory_audit_runs(
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict]:
    return list_source_inventory_audit_runs(limit=limit)


@app.get("/api/source-inventory/audit-rows")
def source_inventory_audit_rows(
    run_id: str | None = Query(default=None, alias="runId", max_length=64),
    limit: int = Query(default=1000, ge=1, le=5000),
) -> list[dict]:
    return list_source_inventory_audit_rows(run_id=run_id, limit=limit)


@app.post("/api/bse-offers/xbrl/refresh")
def bse_offer_xbrl_refresh(
    source_key: Literal["bse_buyback_tender", "bse_takeover_open_offer"] = Query(
        alias="sourceKey"
    ),
    max_documents: int = Query(default=10, ge=1, le=100, alias="maxDocuments"),
    timeout_seconds: int = Query(default=15, ge=3, le=60, alias="timeoutSeconds"),
    force: bool = Query(default=False),
) -> dict:
    return refresh_bse_offer_documents(
        source_key,
        max_documents=max_documents,
        timeout_seconds=timeout_seconds,
        force=force,
    )


@app.get("/api/bse-offers/xbrl/documents")
def bse_offer_xbrl_documents(
    source_key: str | None = Query(default=None, alias="sourceKey"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict]:
    return list_bse_offer_documents(parent_source_key=source_key, limit=limit)


@app.get("/api/bse-offers/events")
def bse_offer_events(
    symbol: str | None = Query(default=None, min_length=1, max_length=32),
    source_key: str | None = Query(default=None, alias="sourceKey"),
    current_only: bool = Query(default=True, alias="currentOnly"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict]:
    return list_corporate_offer_events(
        symbol=symbol,
        parent_source_key=source_key,
        current_only=current_only,
        limit=limit,
    )


@app.get("/api/source-parser/outputs")
def source_parser_outputs(
    source_key: str | None = Query(default=None, alias="sourceKey"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict]:
    return list_source_parser_outputs(source_key=source_key, limit=limit)


@app.get("/api/source-freshness-status")
def source_freshness_status() -> list[dict]:
    return list_source_freshness_status()


@app.get("/api/source-parser/domain-rows")
def source_parser_domain_rows(
    source_key: str = Query(alias="sourceKey"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict:
    return {
        "sourceKey": source_key,
        "rows": list_source_domain_rows(source_key, limit=limit),
    }


@app.get("/api/gate-decisions")
def api_gate_decisions(
    run_id: str | None = Query(default=None, alias="runId"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[dict]:
    return list_gate_decisions(run_id=run_id, limit=limit)


@app.get("/api/gates/readiness")
def gates_readiness(symbol: str | None = Query(default=None)) -> dict:
    return gate_readiness(symbol=symbol)


@app.get("/api/source-monitor/scheduler/status")
def source_monitor_scheduler_status() -> dict:
    return SOURCE_MONITOR_SCHEDULER.status()


@app.post("/api/source-monitor/scheduler/run-once")
def source_monitor_scheduler_run_once(
    fetch: bool = Query(default=False),
    source_key: str | None = Query(default=None, alias="sourceKey"),
) -> dict:
    SOURCE_MONITOR_SCHEDULER.fetch = fetch
    SOURCE_MONITOR_SCHEDULER.source_keys = [source_key] if source_key else None
    return SOURCE_MONITOR_SCHEDULER.run_once()


@app.post("/api/source-monitor/scheduler/start")
def source_monitor_scheduler_start(
    interval_seconds: int = Query(
        default=3600, ge=60, le=86400, alias="intervalSeconds"
    ),
    fetch: bool = Query(default=False),
    source_key: str | None = Query(default=None, alias="sourceKey"),
) -> dict:
    try:
        return SOURCE_MONITOR_SCHEDULER.start(
            interval_seconds=interval_seconds,
            fetch=fetch,
            source_keys=[source_key] if source_key else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/source-monitor/scheduler/stop")
def source_monitor_scheduler_stop() -> dict:
    return SOURCE_MONITOR_SCHEDULER.stop()


@app.get("/api/scanner/scheduler/status")
def scanner_scheduler_status() -> dict:
    return SCANNER_SCHEDULER.status()


@app.post("/api/scanner/run-once")
def scanner_run_once(
    universe: str = Query(default="WATCHLIST_ONLY"),
    fetch: bool = Query(default=False),
) -> dict:
    return SCANNER_SCHEDULER.run_once(universe=universe, fetch=fetch, trigger="manual")


@app.post("/api/scanner/scheduler/start")
def scanner_scheduler_start(
    interval_seconds: int = Query(
        default=900, ge=60, le=86400, alias="intervalSeconds"
    ),
    universe: str = Query(default="WATCHLIST_ONLY"),
    fetch: bool = Query(default=False),
) -> dict:
    try:
        return SCANNER_SCHEDULER.start(
            interval_seconds=interval_seconds, universe=universe, fetch=fetch
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/scanner/scheduler/stop")
def scanner_scheduler_stop() -> dict:
    return SCANNER_SCHEDULER.stop()


@app.get("/api/scanner/runs")
def api_scanner_runs(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict]:
    return scanner_runs(limit=limit)


@app.get("/api/scanner/latest")
def api_scanner_latest() -> dict:
    runs = scanner_runs(limit=1)
    if not runs:
        raise HTTPException(status_code=404, detail="No scanner run is available.")
    run = runs[0]
    return {
        "run": run,
        "candidates": scanner_candidates(run_id=int(run["id"]), limit=5000),
    }


@app.get("/api/scanner/candidates")
def api_scanner_candidates(
    run_id: int | None = Query(default=None, alias="runId"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[dict]:
    return scanner_candidates(run_id=run_id, limit=limit)


@app.post("/api/sources/smoke-test")
def source_smoke_test(
    source: str = Query(default="yfinance"),
    symbol: str = Query(default="TCS"),
    timeframe: str = Query(default="1d"),
) -> dict:
    try:
        display_symbol, requested_symbol, candles = fetch_ohlcv_from_source(
            source,  # type: ignore[arg-type]
            symbol,
            timeframe,
            "1y",
        )
        update_source_registry_status(
            source,
            freshness=FreshnessState.LIVE
            if timeframe not in {"1d", "1w"}
            else FreshnessState.CACHED,
            status=SourceState.GREEN,
            success=True,
        )
        return {
            "source": source,
            "symbol": display_symbol,
            "requestedSymbol": requested_symbol,
            "timeframe": timeframe,
            "candleCount": len(candles),
            "status": "PASS" if candles else "FAIL",
        }
    except Exception as exc:
        update_source_registry_status(
            source,
            freshness=FreshnessState.BROKEN,
            status=SourceState.RED,
            last_error=str(exc),
        )
        return {
            "source": source,
            "symbol": symbol,
            "timeframe": timeframe,
            "candleCount": 0,
            "status": "FAIL",
            "error": str(exc),
        }


def _pattern_status_group(pattern: HarmonicPatternResult) -> StatusGroup:
    if pattern.final_state.startswith("READY"):
        return StatusGroup.READY
    if pattern.final_state.startswith("REJECT"):
        return StatusGroup.REJECT
    return StatusGroup.WAIT


def _pattern_tone(pattern: HarmonicPatternResult) -> Tone:
    group = _pattern_status_group(pattern)
    if group == StatusGroup.READY:
        return Tone.GOOD
    if group == StatusGroup.REJECT:
        return Tone.BAD
    return Tone.WARN


def _patterns_to_ml_candidates(
    patterns: list[HarmonicPatternResult],
    candles: list[OHLCVCandle],
) -> list[RadarCandidate]:
    latest_close = candles[-1].close if candles else 0.0
    series = [round(candle.close) for candle in candles[-24:]]
    candidates: list[RadarCandidate] = []
    for pattern in patterns:
        status_group = _pattern_status_group(pattern)
        candidates.append(
            RadarCandidate(
                symbol=pattern.symbol,
                type=CandidateType.HARMONIC,
                state=pattern.final_state,
                stateTone=_pattern_tone(pattern),
                statusGroup=status_group,
                setup=f"{pattern.pattern_name} {pattern.direction} harmonic",
                timeframe=[pattern.timeframe],
                price=f"{latest_close:.2f}",
                move="real scan",
                reason="; ".join(pattern.reasons[:2])
                if pattern.reasons
                else pattern.confirmation_state,
                decisionTitle=f"{pattern.final_state} - {pattern.pattern_name}",
                decisionText=(
                    "Pattern saved for ML, but READY is blocked until volume, VWAP, "
                    "smart-money, and OI/MWPL/basis gates confirm."
                ),
                trade=TradePlan(
                    entry=f"{latest_close:.2f}",
                    stop=f"{pattern.invalidation_price:.2f}"
                    if pattern.invalidation_price
                    else "WAIT",
                    target=f"{pattern.target1:.2f} / {pattern.target2:.2f}"
                    if pattern.target1 and pattern.target2
                    else "WAIT",
                ),
                quality=pattern.confidence,
                metrics=[
                    MetricRow(
                        label="Pattern",
                        value=pattern.pattern_name,
                        note="Detected structure",
                    ),
                    MetricRow(
                        label="Direction",
                        value=pattern.direction,
                        note="Bullish/bearish bias",
                    ),
                    MetricRow(
                        label="Final State",
                        value=pattern.final_state,
                        note="Post-gate output",
                    ),
                ],
                proof=pattern.gates,
                risk=[
                    PairRow(
                        label="Invalidation",
                        value=f"{pattern.invalidation_price:.2f}"
                        if pattern.invalidation_price
                        else "WAIT",
                    ),
                    PairRow(
                        label="Source Trust", value=DataTrust.UNOFFICIAL_TEMP.value
                    ),
                ],
                sources=[
                    PairRow(label="OHLCV", value="yfinance temporary adapter"),
                    PairRow(label="Detector", value=pattern.source_engine),
                ],
                series=series,
            )
        )
    return candidates


@app.post(
    "/api/ohlcv/fetch", response_model=OHLCVFetchResponse, response_model_by_alias=True
)
def fetch_ohlcv(payload: OHLCVFetchRequest) -> OHLCVFetchResponse:
    try:
        if payload.timeframe == "4h_custom":
            display_symbol, requested_symbol, base_candles = fetch_ohlcv_from_source(
                payload.source,
                payload.symbol,
                "5m",
                payload.period,
            )
            candles, warnings = build_nse_4h_custom(base_candles)
            if not candles:
                raise DataSourceUnavailable("; ".join(warnings))
        else:
            display_symbol, requested_symbol, candles = fetch_ohlcv_from_source(
                payload.source,
                payload.symbol,
                payload.timeframe,
                payload.period,
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DataSourceUnavailable as exc:
        update_source_registry_status(
            payload.source,
            freshness=FreshnessState.BROKEN,
            status=SourceState.RED,
            last_error=str(exc),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    saved_count = save_ohlcv_candles(candles)
    parquet_warning = None
    try:
        write_candles_to_parquet(candles, source=payload.source)
    except Exception as exc:
        parquet_warning = f"Parquet save skipped: {exc}"
    update_source_registry_status(
        payload.source,
        freshness=FreshnessState.LIVE
        if payload.timeframe not in {"1d", "1w"}
        else FreshnessState.CACHED,
        status=SourceState.GREEN,
        success=True,
    )
    return OHLCVFetchResponse(
        symbol=display_symbol,
        requestedSymbol=requested_symbol,
        timeframe=payload.timeframe,
        source=payload.source,
        trustLevel=candles[-1].trust_level if candles else DataTrust.UNOFFICIAL_TEMP,
        candleCount=len(candles),
        savedCount=saved_count,
        warning=parquet_warning
        or "Source data saved with authority/freshness tracking. Verify trust before trading.",
        candles=candles[-200:],
    )


@app.get(
    "/api/ohlcv/candles", response_model=list[OHLCVCandle], response_model_by_alias=True
)
def ohlcv_candles(
    symbol: str = Query(min_length=1, max_length=32),
    timeframe: str = Query(default="1d"),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[OHLCVCandle]:
    display_symbol, _ = normalize_nse_symbol(symbol)
    return list_ohlcv_candles(display_symbol, timeframe, limit=limit)


@app.post(
    "/api/harmonic/scan",
    response_model=HarmonicScanResponse,
    response_model_by_alias=True,
)
def harmonic_scan(payload: HarmonicScanRequest) -> HarmonicScanResponse:
    display_symbol, _ = normalize_nse_symbol(payload.symbol)
    storage_warning: str | None = None
    if payload.use_stored:
        candles = list_ohlcv_candles(display_symbol, payload.timeframe, limit=1000)
        source = "stored"
    else:
        try:
            if payload.timeframe == "4h_custom":
                display_symbol, _, base_candles = fetch_ohlcv_from_source(
                    payload.source,
                    payload.symbol,
                    "5m",
                    payload.period,
                )
                candles, warnings = build_nse_4h_custom(base_candles)
                if not candles:
                    raise DataSourceUnavailable("; ".join(warnings))
            else:
                display_symbol, _, candles = fetch_ohlcv_from_source(
                    payload.source,
                    payload.symbol,
                    payload.timeframe,
                    payload.period,
                )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except DataSourceUnavailable as exc:
            update_source_registry_status(
                payload.source,
                freshness=FreshnessState.BROKEN,
                status=SourceState.RED,
                last_error=str(exc),
            )
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        save_ohlcv_candles(candles)
        try:
            write_candles_to_parquet(candles, source=payload.source)
        except Exception as exc:
            storage_warning = f"Parquet save skipped: {exc}"
            LOGGER.exception(
                "harmonic_parquet_save_failed",
                extra={"symbol": display_symbol, "timeframe": payload.timeframe},
            )
        update_source_registry_status(
            payload.source,
            freshness=FreshnessState.LIVE
            if payload.timeframe not in {"1d", "1w"}
            else FreshnessState.CACHED,
            status=SourceState.GREEN,
            success=True,
        )
        source = payload.source

    patterns, warning = detect_harmonic_patterns(
        candles, display_symbol, payload.timeframe
    )
    saved_patterns = save_harmonic_patterns(patterns)
    saved_ml_run_id = None
    if saved_patterns and payload.save_ml_snapshot:
        candidates = _patterns_to_ml_candidates(saved_patterns, candles)
        run = save_ml_scan_snapshot(
            candidates,
            current_command_bar(),
            list_source_health(),
            trigger="harmonic_real_scan",
            dedupe=False,
        )
        saved_ml_run_id = run.id

    return HarmonicScanResponse(
        symbol=display_symbol,
        timeframe=payload.timeframe,
        source=source,
        trustLevel=DataTrust.UNOFFICIAL_TEMP,
        candleCount=len(candles),
        patterns=saved_patterns,
        savedMlRunId=saved_ml_run_id,
        warning=storage_warning
        or warning
        or "READY remains blocked until all confirmation gates are live and passing.",
    )


@app.get(
    "/api/harmonic/patterns",
    response_model=list[HarmonicPatternResult],
    response_model_by_alias=True,
)
def harmonic_patterns(
    symbol: str | None = Query(default=None, max_length=32),
    timeframe: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[HarmonicPatternResult]:
    display_symbol = None
    if symbol:
        display_symbol, _ = normalize_nse_symbol(symbol)
    return list_harmonic_patterns(
        symbol=display_symbol, timeframe=timeframe, limit=limit
    )


@app.get(
    "/api/parquet/status", response_model=ParquetStatus, response_model_by_alias=True
)
def parquet_status() -> ParquetStatus:
    return get_parquet_status()


@app.post("/api/parquet/write")
def parquet_write(
    symbol: str = Query(min_length=1, max_length=32),
    timeframe: str = Query(default="1d"),
    source: str = Query(default="yfinance"),
) -> dict:
    display_symbol, _ = normalize_nse_symbol(symbol)
    candles = list_ohlcv_candles(display_symbol, timeframe, source=source, limit=10000)
    if not candles:
        candles = list_ohlcv_candles(display_symbol, timeframe, limit=10000)
    if not candles:
        raise HTTPException(
            status_code=404, detail="No stored candles available for Parquet write"
        )
    try:
        path = write_candles_to_parquet(candles, source=source)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"path": str(path), "candleCount": len(candles)}


@app.get("/api/parquet/candles")
def parquet_candles(
    symbol: str = Query(min_length=1, max_length=32),
    timeframe: str = Query(default="1d"),
    source: str = Query(default="yfinance"),
) -> dict:
    try:
        rows = read_candles_from_parquet(symbol, timeframe, source)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "source": source,
        "candleCount": len(rows),
        "candles": rows[-200:],
    }


@app.post(
    "/api/nse/4h-custom/build",
    response_model=list[OHLCVCandle],
    response_model_by_alias=True,
)
def nse_4h_custom_build(
    symbol: str = Query(min_length=1, max_length=32),
    source_timeframe: str = Query(default="5m", alias="sourceTimeframe"),
) -> list[OHLCVCandle]:
    display_symbol, _ = normalize_nse_symbol(symbol)
    candles = list_ohlcv_candles(display_symbol, source_timeframe, limit=10000)
    built, warnings = build_nse_4h_custom(candles)
    if not built:
        raise HTTPException(status_code=422, detail="; ".join(warnings))
    save_ohlcv_candles(built)
    return built


@app.post(
    "/api/nse/resample",
    response_model=NSEResampleResponse,
    response_model_by_alias=True,
)
def resample_nse_candles(
    symbol: str = Query(min_length=1, max_length=32),
    source: str = Query(min_length=1, max_length=64),
    sourceTimeframe: str = Query(default="5m", min_length=2, max_length=16),
    targetTimeframe: str = Query(default="30m", min_length=2, max_length=16),
    persist: bool = True,
) -> NSEResampleResponse:
    if targetTimeframe not in SUPPORTED_NSE_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported NSE target timeframe: {targetTimeframe}",
        )
    source_rows = list_ohlcv_candles(
        symbol, sourceTimeframe, source=source, limit=100_000
    )
    result = resample_nse_session(source_rows, targetTimeframe)
    saved = save_ohlcv_candles(result.candles) if persist and result.candles else 0
    return NSEResampleResponse(
        symbol=symbol.upper(),
        source=source,
        sourceTimeframe=sourceTimeframe,
        targetTimeframe=targetTimeframe,
        candleCount=len(result.candles),
        savedCount=saved,
        warnings=result.warnings,
        candles=result.candles,
    )


@app.post(
    "/api/harmonic/advanced/analyze",
    response_model=HarmonicAdvancedAnalysis,
    response_model_by_alias=True,
)
def harmonic_advanced_analyze(
    symbol: str = Query(min_length=1, max_length=32),
    timeframe: str = Query(default="1d"),
    persist_alerts: bool = Query(default=True, alias="persistAlerts"),
) -> HarmonicAdvancedAnalysis:
    display_symbol, _ = normalize_nse_symbol(symbol)
    candles = list_ohlcv_candles(display_symbol, timeframe, limit=2000)
    if not candles:
        raise HTTPException(
            status_code=404,
            detail=f"No stored candles for {display_symbol} {timeframe}",
        )
    analysis = analyze_harmonic_advanced(candles, display_symbol, timeframe)
    if persist_alerts and analysis.validations:
        alerts = build_alerts(
            display_symbol,
            timeframe,
            analysis.validations[0],
            analysis.final_state,
            analysis.lifecycle_state,
        )
        save_harmonic_alerts(alerts)
    return analysis


@app.get(
    "/api/harmonic/alerts",
    response_model=list[HarmonicAlertRecord],
    response_model_by_alias=True,
)
def harmonic_alerts(
    symbol: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[HarmonicAlertRecord]:
    display_symbol = None
    if symbol:
        display_symbol, _ = normalize_nse_symbol(symbol)
    return list_harmonic_alerts(symbol=display_symbol, limit=limit)


@app.post(
    "/api/harmonic/lifecycle/evaluate",
    response_model=HarmonicLifecycleResult,
    response_model_by_alias=True,
)
def harmonic_lifecycle_evaluate(
    payload: HarmonicLifecycleInput,
    persist: bool = Query(default=True),
) -> HarmonicLifecycleResult:
    result = evaluate_harmonic_lifecycle(payload)
    if persist:
        save_harmonic_lifecycle_events(result.model_dump(mode="json", by_alias=True))
        terminal = result.transitions[-1]
        severity: Literal["INFO", "WARN", "CRITICAL"] = (
            "CRITICAL"
            if result.state in {"LOSS", "INVALIDATED"}
            else "WARN"
            if result.state in {"EXPIRED", "COMPLETE"}
            else "INFO"
        )
        save_general_alert(
            AlertCreate(
                alertType=f"HARMONIC_{result.state}",
                severity=severity,
                symbol=result.symbol,
                state=result.state,
                reason=terminal.reason,
                risk={
                    "patternKey": result.pattern_key,
                    "invalidationPrice": payload.invalidation_price,
                    "target1": payload.target1,
                    "target2": payload.target2,
                    "target3": payload.target3,
                    "executable": False,
                },
            )
        )
    return result


@app.get("/api/harmonic/lifecycle/events")
def harmonic_lifecycle_event_history(
    pattern_key: str | None = Query(default=None, alias="patternKey", max_length=160),
    limit: int = Query(default=1000, ge=1, le=5000),
) -> list[dict]:
    return list_harmonic_lifecycle_events(pattern_key=pattern_key, limit=limit)


@app.post("/api/harmonic/benchmark")
def harmonic_benchmark(
    symbol: str = Query(min_length=1, max_length=32),
    timeframe: str = Query(default="1d"),
) -> dict:
    display_symbol, _ = normalize_nse_symbol(symbol)
    candles = list_ohlcv_candles(display_symbol, timeframe, limit=3000)
    if not candles:
        raise HTTPException(
            status_code=404,
            detail=f"No stored candles for {display_symbol} {timeframe}",
        )
    return benchmark_analysis(candles, display_symbol, timeframe)


@app.post("/api/validation/harmonic-backtest")
def harmonic_backtest(
    symbol: str = Query(min_length=1, max_length=32),
    timeframe: str = Query(default="1d"),
    source: str | None = Query(default=None),
    warmup: int = Query(default=80, ge=40, le=500),
    max_holding_bars: int = Query(default=40, ge=1, le=500, alias="maxHoldingBars"),
) -> dict:
    display_symbol, _ = normalize_nse_symbol(symbol)
    candles = list_ohlcv_candles(display_symbol, timeframe, source=source, limit=10000)
    if not candles:
        raise HTTPException(
            status_code=404,
            detail=f"No stored candles for {display_symbol} {timeframe}",
        )
    report = backtest_harmonic_series(
        candles,
        symbol=display_symbol,
        timeframe=timeframe,
        warmup=warmup,
        max_holding_bars=max_holding_bars,
    )
    report["validationRunId"] = save_validation_report(report, source=source)
    return report


@app.get("/api/validation/runs")
def validation_runs(
    symbol: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict]:
    return list_validation_runs(symbol=symbol, limit=limit)


@app.get("/api/harmonic/chart-overlay")
def harmonic_chart_overlay(
    symbol: str = Query(min_length=1, max_length=32),
    timeframe: str = Query(default="1d"),
) -> dict:
    display_symbol, _ = normalize_nse_symbol(symbol)
    candles = list_ohlcv_candles(display_symbol, timeframe, limit=3000)
    if not candles:
        raise HTTPException(
            status_code=404,
            detail=f"No stored candles for {display_symbol} {timeframe}",
        )
    analysis = analyze_harmonic_advanced(candles, display_symbol, timeframe)
    return chart_overlay_payload(candles, analysis)


@app.get("/api/harmonic/liquidity-check")
def harmonic_liquidity_check(
    symbol: str = Query(min_length=1, max_length=32),
    timeframe: str = Query(default="1d"),
    min_avg_volume: float = Query(default=500_000, alias="minAvgVolume"),
    min_price: float = Query(default=50, alias="minPrice"),
    min_avg_value: float = Query(default=10_000_000, alias="minAvgValue"),
) -> dict:
    display_symbol, _ = normalize_nse_symbol(symbol)
    candles = list_ohlcv_candles(display_symbol, timeframe, limit=200)
    if not candles:
        raise HTTPException(
            status_code=404,
            detail=f"No stored candles for {display_symbol} {timeframe}",
        )
    payload = liquidity_prefilter(
        candles,
        min_avg_volume=min_avg_volume,
        min_price=min_price,
        min_avg_value=min_avg_value,
    )
    return {"symbol": display_symbol, "timeframe": timeframe, **payload}


@app.get(
    "/api/research-records",
    response_model=list[ResearchRecord],
    response_model_by_alias=True,
)
def research_records(
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ResearchRecord]:
    return list_research_records(limit=limit)


@app.post(
    "/api/research-records", response_model=ResearchRecord, response_model_by_alias=True
)
def create_research_record(payload: ResearchCreate) -> ResearchRecord:
    candidate = get_candidate(payload.symbol)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {payload.symbol}")
    return save_research_record(
        payload, candidate, current_command_bar(), list_source_health()
    )


@app.get(
    "/api/research-records/{record_id}",
    response_model=ResearchRecord,
    response_model_by_alias=True,
)
def research_record_detail(record_id: int) -> ResearchRecord:
    record = get_research_record(record_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown research record: {record_id}"
        )
    return record


@app.delete("/api/research-records/{record_id}")
def remove_research_record(record_id: int) -> dict[str, bool]:
    deleted = delete_research_record(record_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Unknown research record: {record_id}"
        )
    return {"deleted": True}


@app.get(
    "/api/ml-snapshots/status",
    response_model=MLScanStatus,
    response_model_by_alias=True,
)
def ml_snapshot_status() -> MLScanStatus:
    return get_ml_scan_status()


@app.post(
    "/api/ml-snapshots/capture", response_model=MLScanRun, response_model_by_alias=True
)
def capture_ml_snapshot() -> MLScanRun:
    return save_ml_scan_snapshot(
        list_candidates(),
        current_command_bar(),
        list_source_health(),
        trigger="manual_capture_endpoint",
        dedupe=False,
    )


@app.get(
    "/api/ml-snapshots/runs",
    response_model=list[MLScanRun],
    response_model_by_alias=True,
)
def ml_snapshot_runs(limit: int = Query(default=50, ge=1, le=500)) -> list[MLScanRun]:
    return list_ml_scan_runs(limit=limit)


@app.get(
    "/api/ml-snapshots/candidates",
    response_model=list[MLScanCandidate],
    response_model_by_alias=True,
)
def ml_snapshot_candidates(
    run_id: int | None = Query(default=None, alias="runId"),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[MLScanCandidate]:
    return list_ml_scan_candidates(run_id=run_id, limit=limit)


class InstitutionalAPIModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class InstitutionalEndpointFetchRequest(InstitutionalAPIModel):
    endpoint_key: str
    parameters: dict[str, str] = Field(default_factory=dict)


class CorporateDisclosureFetchRequest(InstitutionalAPIModel):
    symbol: str = Field(pattern=r"^[A-Za-z0-9&_.-]{1,32}$")
    scripcode: str = Field(pattern=r"^[0-9]{1,12}$")
    from_date: date
    to_date: date


class ExtendedMarketFetchRequest(InstitutionalAPIModel):
    scripcode: str = Field(pattern=r"^[0-9]{1,12}$")
    from_date: date
    to_date: date
    mcx_symbol: str = Field(default="GOLD", pattern=r"^[A-Za-z0-9&_.-]{1,32}$")
    mcx_expiry: str = Field(pattern=r"^[0-9]{2}[A-Za-z]{3}[0-9]{4}$")


class MacroEventFetchRequest(InstitutionalAPIModel):
    symbol: str = Field(default="RELIANCE", pattern=r"^[A-Za-z0-9&_.-]{1,32}$")
    scripcode: str = Field(default="500325", pattern=r"^[0-9]{1,12}$")
    year_month: str = Field(default="0726", pattern=r"^[0-9]{4}$")
    shfe_date: str = Field(default="20260710", pattern=r"^[0-9]{8}$")
    mcx_date: str = Field(default="15/07/2026", pattern=r"^[0-9]{2}/[0-9]{2}/[0-9]{4}$")
    year: int = Field(default=2026, ge=2000, le=2100)
    nbs_indicator_code: str = Field(default="A0B01", pattern=r"^[A-Za-z0-9_.-]{1,32}$")
    bse_category: str = Field(default="Company Update", max_length=80)


class InstitutionalFeatureRequest(InstitutionalAPIModel):
    candles: list[dict[str, Any]] = Field(min_length=20, max_length=20_000)
    var_confidence: float = Field(default=0.95, gt=0.5, lt=1)


class InstitutionalBatchRequest(InstitutionalAPIModel):
    candidates: list[InstitutionalAnalysisRequest] = Field(min_length=1, max_length=500)


class InstitutionalBacktestRequest(InstitutionalAPIModel):
    points: list[WalkForwardPoint] = Field(min_length=3, max_length=100_000)
    min_train_size: int = Field(default=60, ge=2)
    signal_threshold: float = Field(default=1.5, gt=0)


@app.get("/api/institutional/config")
def institutional_config() -> dict[str, Any]:
    config = load_institutional_config()
    payload = config.model_dump(mode="json")
    payload["configHash"] = payload.pop("config_hash")
    return payload


@app.get("/api/institutional/sources")
def institutional_source_contracts() -> dict[str, Any]:
    return {
        "endpointCount": len(ENDPOINTS),
        "normalizationLinkedCount": sum(
            spec.normalized_source_key is not None for spec in ENDPOINTS.values()
        ),
        "endpoints": [
            {
                "key": spec.key,
                "urlTemplate": spec.url_template,
                "responseKind": spec.response_kind,
                "httpMethod": spec.http_method,
                "bodyKind": spec.body_kind,
                "bodyParameters": list(spec.body_parameters),
                "seedUrl": spec.seed_url,
                "purpose": spec.purpose,
                "requiresNseSession": spec.requires_nse_session,
                "requiredParameters": list(spec.required_parameters),
                "normalizedSourceKey": spec.normalized_source_key,
                "contractStatus": spec.contract_status.value,
                "timeoutSeconds": spec.timeout_seconds,
            }
            for spec in ENDPOINTS.values()
        ],
    }


@app.get("/api/institutional/models")
def institutional_model_status() -> dict[str, Any]:
    capabilities = model_capabilities()
    return {
        "models": {
            key: value.model_dump(mode="json") for key, value in capabilities.items()
        },
        "ready": all(item.can_unlock_ready for item in capabilities.values()),
    }


@app.post(
    "/api/institutional/sources/fetch",
    response_model=EndpointFetchResult,
    response_model_by_alias=True,
)
async def institutional_fetch_source(
    payload: InstitutionalEndpointFetchRequest,
) -> EndpointFetchResult:
    client = AsyncEndpointClient()
    try:
        return await client.fetch(payload.endpoint_key, payload.parameters)
    finally:
        await client.aclose()


@app.post(
    "/api/institutional/corporate-sources/fetch",
    response_model=list[EndpointFetchResult],
    response_model_by_alias=True,
)
async def institutional_fetch_corporate_sources(
    payload: CorporateDisclosureFetchRequest,
) -> list[EndpointFetchResult]:
    if payload.from_date > payload.to_date:
        raise HTTPException(status_code=422, detail="fromDate cannot be after toDate")
    requests = corporate_disclosure_requests(
        symbol=payload.symbol,
        scripcode=payload.scripcode,
        from_date=payload.from_date.isoformat(),
        to_date=payload.to_date.isoformat(),
    )
    if {key for key, _ in requests} != set(CORPORATE_DISCLOSURE_ENDPOINTS):
        raise HTTPException(
            status_code=500, detail="Corporate source contract mismatch"
        )
    client = AsyncEndpointClient()
    try:
        results = await client.fetch_many(requests, concurrency=2)
    finally:
        await client.aclose()
    normalize_and_save_disclosures(results)
    return results


@app.post(
    "/api/institutional/extended-market-sources/fetch",
    response_model=list[EndpointFetchResult],
    response_model_by_alias=True,
)
async def institutional_fetch_extended_market_sources(
    payload: ExtendedMarketFetchRequest,
) -> list[EndpointFetchResult]:
    if payload.from_date > payload.to_date:
        raise HTTPException(status_code=422, detail="fromDate cannot be after toDate")
    requests = extended_market_requests(
        scripcode=payload.scripcode,
        from_date=payload.from_date.isoformat(),
        to_date=payload.to_date.isoformat(),
        mcx_symbol=payload.mcx_symbol,
        mcx_expiry=payload.mcx_expiry,
    )
    if {key for key, _ in requests} != set(EXTENDED_MARKET_ENDPOINTS):
        raise HTTPException(status_code=500, detail="Extended source contract mismatch")
    client = AsyncEndpointClient()
    try:
        results = await client.fetch_many(requests, concurrency=2)
    finally:
        await client.aclose()
    normalize_and_save_disclosures(results)
    normalize_and_save_commodity_context(results)
    return results


@app.get(
    "/api/institutional/disclosures/latest",
    response_model=DisclosureDrilldown,
    response_model_by_alias=True,
)
def institutional_disclosures_latest(
    symbol: str | None = Query(default=None, pattern=r"^[A-Za-z0-9&_.-]{1,32}$"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> DisclosureDrilldown:
    return latest_disclosure_drilldown(symbol=symbol, limit=limit)


@app.get(
    "/api/institutional/fii-stock-signals",
    response_model=FIIStockSignalsSnapshot,
    response_model_by_alias=True,
)
def institutional_fii_stock_signals() -> FIIStockSignalsSnapshot:
    loader = (
        CanonicalLatestResultLoader(_MD69_SCHEDULER.store)
        if _MD69_SCHEDULER is not None
        else None
    )
    return build_fii_stock_signals(loader=loader) if loader else build_fii_stock_signals()


@app.get(
    "/api/institutional/commodity-context/latest",
    response_model=CommodityContextSnapshot,
    response_model_by_alias=True,
)
def institutional_commodity_context_latest() -> CommodityContextSnapshot:
    return latest_commodity_context_snapshot()


@app.post(
    "/api/institutional/macro-event-sources/fetch",
    response_model=MacroEventContextSnapshot,
    response_model_by_alias=True,
)
async def institutional_fetch_macro_event_sources(
    payload: MacroEventFetchRequest,
) -> MacroEventContextSnapshot:
    requests = macro_event_requests(
        symbol=payload.symbol,
        scripcode=payload.scripcode,
        year_month=payload.year_month,
        shfe_date=payload.shfe_date,
        mcx_date=payload.mcx_date,
        year=payload.year,
        nbs_indicator_code=payload.nbs_indicator_code,
        bse_category=payload.bse_category,
    )
    if {key for key, _ in requests} != set(MACRO_EVENT_ENDPOINTS):
        raise HTTPException(
            status_code=500, detail="Macro event source contract mismatch"
        )
    client = AsyncEndpointClient()
    try:
        results = await client.fetch_many(requests, concurrency=2)
    finally:
        await client.aclose()
    snapshot = build_macro_event_context_snapshot(results)
    save_macro_event_context_snapshot(snapshot)
    return snapshot


@app.get(
    "/api/institutional/macro-event-context/latest",
    response_model=MacroEventContextSnapshot,
    response_model_by_alias=True,
)
def institutional_macro_event_context_latest() -> MacroEventContextSnapshot:
    return latest_macro_event_context_snapshot()


@app.post(
    "/api/market-activity/fetch",
    response_model=MarketActivitySnapshot,
    response_model_by_alias=True,
)
async def market_activity_fetch(
    limit: int = Query(default=50, ge=1, le=500),
) -> MarketActivitySnapshot:
    requests = market_activity_requests()
    if {key for key, _ in requests} != set(MARKET_ACTIVITY_ENDPOINTS):
        raise HTTPException(
            status_code=500, detail="Market activity source contract mismatch"
        )
    client = AsyncEndpointClient()
    try:
        results = await client.fetch_many(requests, concurrency=2)
    finally:
        await client.aclose()
    snapshot = build_market_activity_snapshot(results, limit=limit)
    save_market_activity_snapshot(snapshot)
    return snapshot


@app.get(
    "/api/market-activity/latest",
    response_model=MarketActivitySnapshot,
    response_model_by_alias=True,
)
def market_activity_latest(
    limit: int = Query(default=20, ge=1, le=500),
) -> MarketActivitySnapshot:
    return latest_market_activity_snapshot(limit=limit)


@app.post(
    "/api/institutional/features",
    response_model=InstitutionalFeatureResult,
    response_model_by_alias=True,
)
def institutional_features(
    payload: InstitutionalFeatureRequest,
) -> InstitutionalFeatureResult:
    return build_institutional_features(
        payload.candles, var_confidence=payload.var_confidence
    )


@app.post(
    "/api/institutional/analyze",
    response_model=InstitutionalAnalysisResult,
    response_model_by_alias=True,
)
def institutional_analyze(
    payload: InstitutionalAnalysisRequest,
    persist: bool = Query(default=True),
) -> InstitutionalAnalysisResult:
    config = load_institutional_config()
    effective_payload = payload.model_copy(
        update={
            "source_ready": False,
            "models_ready": False,
            "anomaly_state": "UNKNOWN",
        }
    )
    result = analyze_institutional(effective_payload, config=config)
    if persist:
        save_analysis_report(effective_payload, result, config)
    return result


@app.post(
    "/api/institutional/screen",
    response_model=list[InstitutionalAnalysisResult],
    response_model_by_alias=True,
)
def institutional_screen(
    payload: InstitutionalBatchRequest,
    persist: bool = Query(default=True),
) -> list[InstitutionalAnalysisResult]:
    config = load_institutional_config()
    effective_candidates = [
        candidate.model_copy(
            update={
                "source_ready": False,
                "models_ready": False,
                "anomaly_state": "UNKNOWN",
            }
        )
        for candidate in payload.candidates
    ]
    results = [
        analyze_institutional(candidate, config=config)
        for candidate in effective_candidates
    ]
    if persist:
        for candidate, result in zip(effective_candidates, results, strict=True):
            save_analysis_report(candidate, result, config)
    return results


@app.get("/api/institutional/reports")
def institutional_reports(
    symbol: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=5_000),
) -> list[dict[str, Any]]:
    return list_analysis_reports(symbol=symbol, limit=limit)


@app.post(
    "/api/institutional/backtest",
    response_model=WalkForwardReport,
    response_model_by_alias=True,
)
def institutional_backtest(
    payload: InstitutionalBacktestRequest,
    persist: bool = Query(default=True),
) -> WalkForwardReport:
    report = walk_forward_validate(
        payload.points,
        min_train_size=payload.min_train_size,
        signal_threshold=payload.signal_threshold,
    )
    if persist:
        save_walk_forward_report(report, load_institutional_config())
    return report


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")




