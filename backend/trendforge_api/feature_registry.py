from __future__ import annotations

import ast
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

from .indicator_engine import (
    INDICATOR_ENGINE_ID,
    INDICATOR_ENGINE_VERSION,
    IndicatorEnginePin,
    RuntimeEngineCheck,
    pinned_indicator_engine,
    verify_indicator_runtime,
)


MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    frozen=True,
)
FEATURE_REGISTRY_VERSION = "1.1.0"
MODULE_ROOT = Path(__file__).resolve().parent
EXPECTED_FEATURE_IDS = frozenset(f"FTR-{index:03d}" for index in range(1, 41))
MANDATORY_FEATURE_FIELDS = (
    "feature_id",
    "feature_version",
    "trader_problem",
    "horizon",
    "required_inputs",
    "preferred_source_role",
    "authority_and_freshness",
    "deterministic_calculation",
    "evidence_family",
    "correlation_group",
    "double_count_rule",
    "failure_and_stale_behavior",
    "state_ceiling",
    "closed_bar_required",
    "storage_and_versioning",
    "backend_module",
    "api_field_or_route",
    "radar_or_inspector_presentation",
    "acceptance_and_adversarial_tests",
    "dependencies",
    "difficulty",
    "priority",
)


class FeatureActivationState(StrEnum):
    REGISTERED_NOT_ACTIVE = "REGISTERED_NOT_ACTIVE"
    FIXTURE_ONLY = "FIXTURE_ONLY"
    RESEARCH_ACTIVE = "RESEARCH_ACTIVE"
    PIT_APPROVED = "PIT_APPROVED"


class FeatureContract(BaseModel):
    model_config = MODEL_CONFIG

    feature_id: str = Field(pattern=r"^FTR-\d{3}$")
    feature_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    trader_problem: str = Field(min_length=1)
    horizon: tuple[Literal["INTRADAY", "SWING", "BOTH", "VALIDATION"], ...]
    required_inputs: tuple[str, ...]
    preferred_source_role: str = Field(min_length=1)
    authority_and_freshness: str = Field(min_length=1)
    deterministic_calculation: str = Field(min_length=1)
    evidence_family: str = Field(min_length=1)
    correlation_group: str = Field(pattern=r"^CG_[A-Z0-9_]+$")
    double_count_rule: str = Field(min_length=1)
    failure_and_stale_behavior: str = Field(min_length=1)
    state_ceiling: Literal["WATCH", "WAIT", "CONFIRMED"]
    closed_bar_required: bool
    storage_and_versioning: str = Field(min_length=1)
    backend_module: str = Field(min_length=1)
    api_field_or_route: str = Field(min_length=1)
    radar_or_inspector_presentation: str = Field(min_length=1)
    acceptance_and_adversarial_tests: tuple[str, ...]
    dependencies: tuple[str, ...]
    difficulty: Literal["LOW", "MEDIUM", "HIGH"]
    priority: Literal["P0", "P1", "P2", "P3"]
    activation_state: FeatureActivationState
    indicator_engine_id: str | None = None
    indicator_engine_version: str | None = None
    minimum_warmup_bars: int = Field(default=0, ge=0)

    @field_validator(
        "trader_problem",
        "preferred_source_role",
        "authority_and_freshness",
        "deterministic_calculation",
        "evidence_family",
        "double_count_rule",
        "failure_and_stale_behavior",
        "storage_and_versioning",
        "backend_module",
        "api_field_or_route",
        "radar_or_inspector_presentation",
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("feature contract text fields cannot be blank")
        return clean

    @field_validator(
        "horizon",
        "required_inputs",
        "acceptance_and_adversarial_tests",
        "dependencies",
    )
    @classmethod
    def require_non_empty_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not str(item).strip() for item in value):
            raise ValueError("feature contract tuple fields cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_indicator_binding(self) -> "FeatureContract":
        if (self.indicator_engine_id is None) != (
            self.indicator_engine_version is None
        ):
            raise ValueError(
                "indicator engine ID and version must be supplied together"
            )
        if self.indicator_engine_id is not None:
            if (
                self.indicator_engine_id != INDICATOR_ENGINE_ID
                or self.indicator_engine_version != INDICATOR_ENGINE_VERSION
            ):
                raise ValueError("feature uses an engine other than the R0 pin")
            if self.minimum_warmup_bars <= 0:
                raise ValueError("indicator-backed feature needs a positive warm-up")
        elif self.minimum_warmup_bars:
            raise ValueError("non-indicator feature cannot declare indicator warm-up")
        return self


class FeatureRegistryManifest(BaseModel):
    model_config = MODEL_CONFIG

    registry_version: str
    indicator_engine: IndicatorEnginePin
    features: tuple[FeatureContract, ...]
    research_only: Literal[True] = True
    can_unlock_confirmed: Literal[False] = False

    @model_validator(mode="after")
    def validate_complete_registry(self) -> "FeatureRegistryManifest":
        ids = [feature.feature_id for feature in self.features]
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        if duplicates:
            raise ValueError(f"duplicate feature IDs: {duplicates}")
        missing = sorted(EXPECTED_FEATURE_IDS - set(ids))
        unexpected = sorted(set(ids) - EXPECTED_FEATURE_IDS)
        if missing or unexpected:
            raise ValueError(
                f"feature registry ID mismatch: missing={missing}, unexpected={unexpected}"
            )
        return self


class FeatureRegistryLintReport(BaseModel):
    model_config = MODEL_CONFIG

    ok: bool
    registry_version: str
    expected_feature_count: int = Field(ge=0)
    validated_feature_count: int = Field(ge=0)
    required_fields: tuple[str, ...]
    runtime_engine: RuntimeEngineCheck
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    research_only: Literal[True] = True
    can_unlock_confirmed: Literal[False] = False


def _feature(
    feature_id: str,
    trader_problem: str,
    horizon: tuple[Literal["INTRADAY", "SWING", "BOTH", "VALIDATION"], ...],
    required_inputs: tuple[str, ...],
    preferred_source_role: str,
    authority_and_freshness: str,
    deterministic_calculation: str,
    evidence_family: str,
    correlation_group: str,
    double_count_rule: str,
    failure_and_stale_behavior: str,
    state_ceiling: Literal["WATCH", "WAIT", "CONFIRMED"],
    closed_bar_required: bool,
    storage_and_versioning: str,
    backend_module: str,
    api_field_or_route: str,
    radar_or_inspector_presentation: str,
    acceptance_and_adversarial_tests: tuple[str, ...],
    dependencies: tuple[str, ...],
    difficulty: Literal["LOW", "MEDIUM", "HIGH"],
    priority: Literal["P0", "P1", "P2", "P3"],
    *,
    activation_state: FeatureActivationState = FeatureActivationState.REGISTERED_NOT_ACTIVE,
    indicator_warmup: int = 0,
) -> FeatureContract:
    engine_id = INDICATOR_ENGINE_ID if indicator_warmup else None
    engine_version = INDICATOR_ENGINE_VERSION if indicator_warmup else None
    return FeatureContract(
        feature_id=feature_id,
        feature_version="1.0.0",
        trader_problem=trader_problem,
        horizon=horizon,
        required_inputs=required_inputs,
        preferred_source_role=preferred_source_role,
        authority_and_freshness=authority_and_freshness,
        deterministic_calculation=deterministic_calculation,
        evidence_family=evidence_family,
        correlation_group=correlation_group,
        double_count_rule=double_count_rule,
        failure_and_stale_behavior=failure_and_stale_behavior,
        state_ceiling=state_ceiling,
        closed_bar_required=closed_bar_required,
        storage_and_versioning=storage_and_versioning,
        backend_module=backend_module,
        api_field_or_route=api_field_or_route,
        radar_or_inspector_presentation=radar_or_inspector_presentation,
        acceptance_and_adversarial_tests=acceptance_and_adversarial_tests,
        dependencies=dependencies,
        difficulty=difficulty,
        priority=priority,
        activation_state=activation_state,
        indicator_engine_id=engine_id,
        indicator_engine_version=engine_version,
        minimum_warmup_bars=indicator_warmup,
    )


FEATURES = (
    _feature(
        "FTR-001",
        "Avoid unstable pre-open gap chasing",
        ("INTRADAY",),
        (
            "iep",
            "previous_close",
            "matched_quantity",
            "buy_sell_imbalance",
            "snapshot_time",
        ),
        "SRC-NSE-PREOPEN",
        "Official live auction snapshots inside the declared pre-open window",
        "Compute gap percent, bounded IEP stability and normalized imbalance across snapshots",
        "MARKET_AND_SECTOR_CONTEXT",
        "CG_PREOPEN",
        "All pre-open views contribute through one auction group",
        "Outside-window, sparse or stale snapshots produce WAIT and never live reuse",
        "WAIT",
        False,
        "Versioned pre-open snapshots and calculation profile",
        "preopen_features.py",
        "/api/selection/context/preopen",
        "Radar context chip and inspector timeline",
        ("T-017", "T-018", "T-199"),
        ("exchange_calendar", "official_preopen_source"),
        "MEDIUM",
        "P1",
    ),
    _feature(
        "FTR-002",
        "Avoid directional selection against hostile market breadth",
        ("BOTH",),
        ("index_snapshot", "advances", "declines", "aligned_timestamp"),
        "SRC-NSE-CONTEXT",
        "Official aligned index/breadth observations; VIX only when separately verified",
        "Apply versioned breadth ratio, dispersion and deterministic regime profile",
        "MARKET_AND_SECTOR_CONTEXT",
        "CG_MARKET_REGIME",
        "Breadth and regime are one context contribution",
        "Missing or misaligned required context caps the profile at WAIT",
        "WAIT",
        False,
        "Versioned market_context_snapshots",
        "market_context.py",
        "/api/market-context/evaluate",
        "Radar regime strip and inspector components",
        ("T-011", "T-017", "T-197"),
        ("official_index_source", "exchange_calendar"),
        "MEDIUM",
        "P0",
        activation_state=FeatureActivationState.REGISTERED_NOT_ACTIVE,
    ),
    _feature(
        "FTR-003",
        "Prefer stocks aligned with point-in-time sector leadership",
        ("BOTH",),
        ("pit_constituents", "sector_bars", "stock_bars"),
        "SRC-SECTOR",
        "PIT constituents and aligned official/verified closed bars",
        "Rank sector returns, then rank stocks inside the contemporaneous sector universe",
        "MARKET_AND_SECTOR_CONTEXT",
        "CG_SECTOR_RS",
        "Sector and stock claims stay distinct but capped as context",
        "Missing membership or date alignment returns UNKNOWN/WAIT",
        "WAIT",
        True,
        "Universe and ranking versions stored with snapshots",
        "market_context.py",
        "/api/sector-context/evaluate",
        "Sector chip and hidden ranking",
        ("T-016", "T-017", "T-204"),
        ("pit_universe", "adjusted_bars"),
        "MEDIUM",
        "P1",
        activation_state=FeatureActivationState.REGISTERED_NOT_ACTIVE,
    ),
    _feature(
        "FTR-004",
        "Measure persistent stock strength versus benchmark and sector",
        ("SWING",),
        ("adjusted_stock_bars", "benchmark_bars", "sector_bars", "pit_universe"),
        "SRC-NSE-EOD",
        "PIT-adjusted aligned EOD bars from approved sources",
        "Stock return minus benchmark return over versioned horizons; percentile within PIT universe",
        "STRUCTURE",
        "CG_RELATIVE_STRENGTH",
        "One representative relative-strength contribution",
        "Corporate-action or alignment failure returns INPUT_INCOMPLETE",
        "WAIT",
        True,
        "Versioned feature snapshots and universe identity",
        "selection/relative_strength.py",
        "/api/selection/features/relative-strength",
        "Hidden structure inspector",
        ("T-013", "T-016", "T-204"),
        ("adjusted_bars", "pit_universe"),
        "MEDIUM",
        "P1",
    ),
    _feature(
        "FTR-005",
        "Prevent repainting by accepting structure only on closed bars",
        ("BOTH",),
        ("adjusted_closed_bars", "versioned_level", "profile"),
        "SRC-NSE-EOD_OR_VERIFIED_INTRADAY",
        "Closed adjusted bars; intraday source must pass read-only integrity",
        "Require configured closes beyond the versioned level and record bar IDs/invalidation",
        "STRUCTURE",
        "CG_PRICE_STRUCTURE",
        "One price-structure representative per direction/profile",
        "Unclosed or malformed bars produce WAIT/INPUT_INCOMPLETE",
        "CONFIRMED",
        True,
        "Normalized facts and immutable structure claims",
        "selection/structure.py",
        "/api/v1/selection/fixtures/q5-r3",
        "Primary reason/level plus inspector lineage",
        ("T-012", "T-028", "T-031"),
        ("adjusted_bars", "session_calendar"),
        "MEDIUM",
        "P0",
        activation_state=FeatureActivationState.FIXTURE_ONLY,
    ),
    _feature(
        "FTR-006",
        "Detect accepted breakout or breakdown without volume double count",
        ("BOTH",),
        ("adjusted_closed_bars", "prior_range", "tick_size", "profile"),
        "SRC-NSE-EOD_OR_VERIFIED_INTRADAY",
        "Approved closed bars with adjustment and tick metadata",
        "Exclude candidate bar from lookback; cross versioned range by tolerance and acceptance bars",
        "STRUCTURE",
        "CG_PRICE_STRUCTURE",
        "Volume stays in participation; related structure contributes once",
        "Forming is WATCH; failed/unclosed acceptance is WAIT",
        "CONFIRMED",
        True,
        "Versioned structure metrics and claim lineage",
        "selection/structure.py",
        "/api/v1/selection/fixtures/q5-r3",
        "Radar setup reason and invalidation",
        ("T-012", "T-031", "T-068"),
        ("adjusted_bars", "instrument_tick"),
        "MEDIUM",
        "P0",
        activation_state=FeatureActivationState.FIXTURE_ONLY,
    ),
    _feature(
        "FTR-007",
        "Find range compression before expansion",
        ("BOTH",),
        ("adjusted_closed_bars", "nr_window"),
        "SRC-NSE-EOD_OR_VERIFIED_INTRADAY",
        "Approved closed bars with enough prior completed periods",
        "Current true range is the minimum of N completed ranges with the candidate included only as current",
        "STRUCTURE",
        "CG_COMPRESSION",
        "NR, VCP and squeeze share one compression cap",
        "Insufficient history returns INPUT_INCOMPLETE; compression alone max WATCH",
        "WATCH",
        True,
        "Versioned NR metrics and bar IDs",
        "selection/structure.py",
        "/api/v1/selection/fixtures/q5-r3",
        "Inspector compression marker",
        ("T-023", "T-028", "T-031"),
        ("adjusted_bars",),
        "LOW",
        "P1",
        activation_state=FeatureActivationState.FIXTURE_ONLY,
    ),
    _feature(
        "FTR-008",
        "Find orderly volatility and volume contraction",
        ("SWING",),
        ("adjusted_eod_bars", "volume", "pivot_profile"),
        "SRC-NSE-EOD",
        "PIT-adjusted EOD bars and versioned pivot rules",
        "Require a versioned sequence of decreasing swing ranges plus volume dry-up",
        "STRUCTURE",
        "CG_COMPRESSION",
        "VCP shares the compression cap with NR and squeeze",
        "Ambiguous pivots or sparse history produce no claim; max WATCH",
        "WATCH",
        True,
        "Pivot, profile and feature versions retained",
        "selection/compression.py",
        "/api/selection/features/vcp",
        "Scanner Lab and inspector only",
        ("T-023", "T-028", "T-030"),
        ("adjusted_bars", "pivot_engine"),
        "HIGH",
        "P2",
    ),
    _feature(
        "FTR-009",
        "Detect Bollinger/Keltner volatility squeeze consistently",
        ("BOTH",),
        ("adjusted_closed_bars", "bollinger_profile", "keltner_profile"),
        "SRC-NSE-EOD_OR_VERIFIED_INTRADAY",
        "Approved bars and the R0-pinned indicator engine",
        "Bollinger envelope lies inside Keltner envelope under one versioned parameter set",
        "STRUCTURE",
        "CG_COMPRESSION",
        "Squeeze shares one bounded compression contribution",
        "Engine mismatch or warm-up failure returns INPUT_INCOMPLETE",
        "WATCH",
        True,
        "Feature snapshot records engine/profile versions",
        "selection/compression.py",
        "/api/selection/features/squeeze",
        "Hidden compression inspector",
        ("T-023", "T-028", "T-029", "T-030"),
        ("adjusted_bars", "pinned_indicator_engine"),
        "MEDIUM",
        "P2",
        indicator_warmup=20,
    ),
    _feature(
        "FTR-010",
        "Confirm intraday opening-range and VWAP acceptance",
        ("INTRADAY",),
        ("verified_intraday_closed_bars", "session", "vwap_inputs"),
        "SRC-NSE-INTRADAY",
        "Only broker/read-only intraday data after sequence, clock and close-status integrity",
        "Versioned ORB range plus close/VWAP displacement velocity over fixed completed intervals",
        "STRUCTURE",
        "CG_INTRADAY_ACCEPTANCE",
        "ORB and VWAP acceptance are one intraday structure group",
        "No verified intraday mode or partial bar keeps the candidate at WAIT",
        "WAIT",
        True,
        "Session/profile/bar versions retained",
        "selection/intraday_structure.py",
        "/api/selection/features/intraday-acceptance",
        "Radar next trigger and hidden session chart",
        ("T-012", "T-017", "T-196"),
        ("verified_intraday_feed", "exchange_calendar"),
        "HIGH",
        "P2",
    ),
    _feature(
        "FTR-011",
        "Track forming, testing, accepted and invalidated patterns",
        ("BOTH",),
        ("adjusted_closed_bars", "pivot_profile", "ratio_tolerances"),
        "SRC-NSE-EOD_OR_VERIFIED_INTRADAY",
        "Approved closed bars and versioned deterministic geometry",
        "Map pattern lifecycle to WATCH/WAIT/eligible/REJECT while retaining every transition",
        "STRUCTURE",
        "CG_PATTERN_STRUCTURE",
        "Pattern variants under one geometry group",
        "Pattern-only cannot confirm; pivot revisions preserve prior lineage",
        "CONFIRMED",
        True,
        "Immutable lifecycle events and algorithm version",
        "harmonic_scan_lifecycle.py",
        "/api/harmonic/lifecycle",
        "Inspector geometry and transition history",
        ("T-012", "T-032", "T-033"),
        ("adjusted_bars", "pinned_pivots"),
        "HIGH",
        "P2",
        activation_state=FeatureActivationState.REGISTERED_NOT_ACTIVE,
    ),
    _feature(
        "FTR-012",
        "Provide trend-overlay context without vote stacking",
        ("BOTH",),
        ("adjusted_closed_bars", "overlay_parameters"),
        "SRC-NSE-EOD_OR_VERIFIED_INTRADAY",
        "Approved bars and the R0-pinned indicator engine",
        "Compute versioned MA, Ichimoku, SuperTrend and PSAR subclaims; select one representative",
        "STRUCTURE",
        "CG_TREND_OVERLAYS",
        "All trend overlays contribute at most one bounded representative",
        "Mixed engine or insufficient warm-up returns INPUT_INCOMPLETE",
        "WAIT",
        True,
        "Engine, parameters and selected/suppressed IDs retained",
        "indicator_engine.py",
        "/api/selection/features/trend-overlays",
        "Technical inspector only",
        ("T-022", "T-028", "T-029", "T-030"),
        ("adjusted_bars", "pinned_indicator_engine"),
        "MEDIUM",
        "P2",
        indicator_warmup=200,
    ),
    _feature(
        "FTR-013",
        "Describe momentum condition without an opaque oscillator score",
        ("BOTH",),
        ("adjusted_closed_bars", "oscillator_parameters"),
        "SRC-NSE-EOD_OR_VERIFIED_INTRADAY",
        "Approved bars and the R0-pinned indicator engine",
        "Compute versioned RSI, MFI, CCI, MACD and Aroon values as separate subclaims",
        "STRUCTURE",
        "CG_MOMENTUM_OSCILLATORS",
        "Oscillators contribute one bounded representative",
        "Mixed engine, non-finite output or insufficient warm-up is INPUT_INCOMPLETE",
        "WAIT",
        True,
        "Engine, parameters and null reasons retained",
        "institutional_features.py",
        "/api/institutional/features",
        "Scanner Lab/technical inspector",
        ("T-022", "T-028", "T-029", "T-030"),
        ("adjusted_bars", "pinned_indicator_engine"),
        "MEDIUM",
        "P2",
        activation_state=FeatureActivationState.RESEARCH_ACTIVE,
        indicator_warmup=200,
    ),
    _feature(
        "FTR-014",
        "Detect failed auction or breakout reclaim",
        ("BOTH",),
        ("adjusted_closed_bars", "reference_level", "reclaim_window"),
        "SRC-NSE-EOD_OR_VERIFIED_INTRADAY",
        "Approved closed bars with versioned reference level",
        "Require excursion beyond level followed by a closed reclaim/rejection inside configured bars",
        "STRUCTURE",
        "CG_REVERSAL",
        "Reversal variants share one reclaim group",
        "No reclaim or invalidation keeps WATCH/WAIT; oscillator alone is insufficient",
        "WAIT",
        True,
        "Reference level, bar IDs and profile version retained",
        "selection/reversal.py",
        "/api/selection/features/reversal",
        "Radar trigger and invalidation",
        ("T-012", "T-032", "T-068"),
        ("adjusted_bars",),
        "HIGH",
        "P2",
    ),
    _feature(
        "FTR-015",
        "Identify point-in-time 10-day and 52-week extremes",
        ("BOTH",),
        ("pit_adjusted_closed_bars", "lookback"),
        "SRC-NSE-EOD",
        "PIT-adjusted bars with complete lookback",
        "Current closed high/low exceeds prior N completed periods; candidate bar excluded from prior range",
        "STRUCTURE",
        "CG_PRICE_STRUCTURE",
        "Extremes share price-structure cap",
        "Insufficient history or adjustment uncertainty returns INPUT_INCOMPLETE",
        "WATCH",
        True,
        "Lookback and adjustment versions retained",
        "selection/extremes.py",
        "/api/selection/features/extremes",
        "Scanner Lab and structure inspector",
        ("T-013", "T-028", "T-031"),
        ("pit_adjusted_bars",),
        "LOW",
        "P2",
    ),
    _feature(
        "FTR-016",
        "Standardize volatility reference levels without sizing",
        ("BOTH",),
        ("adjusted_closed_bars", "atr_period"),
        "SRC-NSE-EOD_OR_VERIFIED_INTRADAY",
        "Approved bars and the R0-pinned indicator engine",
        "True range uses max of range and prior-close gaps; ATR smoothing/period are versioned",
        "STRUCTURE",
        "CG_VOLATILITY",
        "ATR is one volatility attribute and never an extra confirmation",
        "Unknown ATR produces no fabricated stop/reference and remains INPUT_INCOMPLETE",
        "WAIT",
        True,
        "Engine, period, warm-up and value retained",
        "indicator_engine.py",
        "/api/selection/features/volatility",
        "Inspector reference only",
        ("T-028", "T-029", "T-030"),
        ("adjusted_bars", "pinned_indicator_engine"),
        "LOW",
        "P1",
        indicator_warmup=14,
    ),
    _feature(
        "FTR-017",
        "Separate genuine participation from ordinary volume",
        ("BOTH",),
        ("closed_volume_bars", "pit_baseline", "session_elapsed"),
        "SRC-NSE-EOD_OR_VERIFIED_INTRADAY",
        "Verified closed bars and comparable PIT baseline sessions",
        "RVOL uses comparable baseline; TOD uses same completed exchange-local interval across sessions",
        "PARTICIPATION",
        "CG_ACTIVITY_SESSION",
        "RVOL, volume-gainer and most-active views share one activity cap",
        "Partial bar or thin/misaligned baseline returns UNKNOWN/WAIT",
        "CONFIRMED",
        True,
        "Baseline coverage, session IDs and feature version retained",
        "selection/structure.py",
        "/api/v1/selection/fixtures/q5-r3",
        "Radar participation reason and baseline inspector",
        ("T-017", "T-021", "T-028"),
        ("verified_volume_bars", "pit_baseline"),
        "MEDIUM",
        "P0",
        activation_state=FeatureActivationState.FIXTURE_ONLY,
    ),
    _feature(
        "FTR-018",
        "Discover liquid or unusually active stocks cheaply",
        ("INTRADAY",),
        ("official_activity_rows", "source_timestamp"),
        "SRC-NSE-ACTIVITY",
        "Official NSE activity endpoints under the seeded session contract",
        "Normalize rank/value/volume fields for candidate discovery only",
        "PARTICIPATION",
        "CG_ACTIVITY_SESSION",
        "Activity endpoints do not add votes beyond RVOL/participation",
        "Valid-empty is distinct from blocked, stale or schema-changed",
        "WATCH",
        False,
        "Raw activity snapshot, parser and source versions retained",
        "market_activity.py",
        "/api/market-activity/latest",
        "WATCH queue discovery chip",
        ("T-001", "T-006", "T-021"),
        ("nse_seeded_session", "official_activity_source"),
        "LOW",
        "P0",
        activation_state=FeatureActivationState.RESEARCH_ACTIVE,
    ),
    _feature(
        "FTR-019",
        "Distinguish settled delivery participation from churn",
        ("SWING",),
        ("eod_traded_quantity", "deliverable_quantity", "pit_delivery_baseline"),
        "SRC-NSE-EOD",
        "Official finalized EOD delivery with publication lag retained",
        "Compute delivery percentage and z-score against PIT rolling baseline after availability",
        "PARTICIPATION",
        "CG_DELIVERY_EOD",
        "Delivery is one swing-only participation contribution",
        "Missing/stale/provisional delivery is null and forbidden for intraday confirmation",
        "WAIT",
        True,
        "Versioned delivery facts and baseline snapshots",
        "selection/delivery_features.py",
        "/api/selection/features/delivery",
        "Swing inspector with lag label",
        ("T-019", "T-034", "T-118"),
        ("official_delivery_source", "pit_baseline"),
        "MEDIUM",
        "P1",
    ),
    _feature(
        "FTR-020",
        "Classify aligned futures price and OI behavior",
        ("BOTH",),
        (
            "contract_price",
            "prior_price",
            "open_interest",
            "prior_open_interest",
            "expiry",
        ),
        "SRC-NSE-FO",
        "Official/verified same-contract and same-expiry snapshots",
        "Map price/OI signs to long buildup, short buildup, short covering or long unwinding",
        "DERIVATIVES_OI",
        "CG_FUTURES_OI",
        "OI level, delta, velocity, quadrant and basis share one derivatives cap",
        "Missing prior OI, equality or contract mismatch returns NEUTRAL/UNKNOWN",
        "CONFIRMED",
        False,
        "Aligned contract snapshots and calculation version",
        "selection/derivatives_features.py",
        "/api/selection/features/oi-quadrant",
        "Radar OI classification and inspector inputs",
        ("T-025", "T-027", "T-038"),
        ("fo_contract_identity", "official_fo_source"),
        "MEDIUM",
        "P0",
    ),
    _feature(
        "FTR-021",
        "Detect OI acceleration without another conviction vote",
        ("BOTH",),
        ("time_aligned_oi_snapshots", "sampling_interval"),
        "SRC-NSE-FO",
        "Stable same-contract snapshots at a declared interval",
        "Compute first difference or percent change with versioned denominator and interval",
        "DERIVATIVES_OI",
        "CG_FUTURES_OI",
        "Velocity is descriptive inside the existing futures-OI cap",
        "Sparse or irregular sampling returns UNKNOWN",
        "WAIT",
        False,
        "Timestamped OI snapshots and interval policy",
        "selection/derivatives_features.py",
        "/api/selection/features/oi-velocity",
        "Derivatives inspector timeline",
        ("T-025", "T-038", "T-082"),
        ("fo_contract_identity", "snapshot_store"),
        "MEDIUM",
        "P1",
    ),
    _feature(
        "FTR-022",
        "Explain futures carry and expiry rollover",
        ("BOTH",),
        ("spot", "near_future", "next_future", "days_to_expiry", "near_oi", "next_oi"),
        "SRC-NSE-FO",
        "Aligned spot/futures contracts and official expiry calendar",
        "Basis=future-spot; rollover=next_OI/(near_OI+next_OI) only in versioned roll window",
        "DERIVATIVES_OI",
        "CG_FUTURES_OI",
        "Basis/rollover remain within one futures-OI contribution",
        "Bad expiry, zero denominator or identity mismatch returns UNKNOWN",
        "WAIT",
        False,
        "Contract, expiry, inputs and formula version retained",
        "selection/derivatives_features.py",
        "/api/selection/features/futures-basis",
        "Derivatives inspector only",
        ("T-025", "T-038", "T-046"),
        ("fo_contract_identity", "exchange_calendar"),
        "MEDIUM",
        "P1",
    ),
    _feature(
        "FTR-023",
        "Track option positioning change instead of one static PCR",
        ("INTRADAY",),
        ("same_expiry_option_snapshots", "ce_oi", "pe_oi", "spot"),
        "SRC-NSE-OPTIONS",
        "Fresh complete expiry-scoped chain snapshots",
        "PCR_OI=sum(PE_OI)/sum(CE_OI); retain fixed-interval delta and spot alignment",
        "OPTIONS_CONTEXT",
        "CG_OPTION_CHAIN",
        "PCR, walls, max pain, volume, IV and skew count once",
        "Zero CE denominator, mixed expiry, sparse or stale chain returns null reason/WAIT",
        "WAIT",
        False,
        "Immutable option snapshots and formula version",
        "selection/options_domain.py",
        "/api/selection/options/timeline",
        "Hidden PCR timeline",
        ("T-024", "T-026", "T-027", "T-085"),
        ("validated_option_chain", "snapshot_store"),
        "HIGH",
        "P1",
        activation_state=FeatureActivationState.FIXTURE_ONLY,
    ),
    _feature(
        "FTR-024",
        "Show option OI reference walls and max-pain level",
        ("BOTH",),
        ("same_expiry_option_chain", "strike_completeness"),
        "SRC-NSE-OPTIONS",
        "Fresh schema-valid chain with declared strike coverage",
        "Walls use versioned concentration; max pain minimizes aggregate intrinsic payout",
        "OPTIONS_CONTEXT",
        "CG_OPTION_CHAIN",
        "All chain-derived levels share one options-context cap",
        "Incomplete strikes, mixed expiry or stale data returns UNKNOWN; never zero-fill",
        "WAIT",
        False,
        "Chain hash, expiry, strike set and formula version",
        "selection/options_domain.py",
        "/api/selection/options/levels",
        "Hidden strike explorer",
        ("T-024", "T-027", "T-085"),
        ("validated_option_chain",),
        "HIGH",
        "P1",
        activation_state=FeatureActivationState.FIXTURE_ONLY,
    ),
    _feature(
        "FTR-025",
        "Explain option volatility and sensitivities without fake certainty",
        ("BOTH",),
        ("option_quote", "spot_or_forward", "strike", "expiry", "rate", "multiplier"),
        "SRC-NSE-OPTIONS",
        "Source IV preferred; calculated values require complete validated model inputs",
        "Versioned IV/Greeks model; calculated values labelled CALCULATED_PROXY",
        "OPTIONS_CONTEXT",
        "CG_OPTION_CHAIN",
        "Greeks, IV and skew remain one options-context contribution",
        "Missing/non-finite/crossed/expired inputs return UNKNOWN",
        "WAIT",
        False,
        "Model/input versions and null reasons retained",
        "derivatives_engine.py",
        "/api/options/greeks",
        "Hidden derivatives tab",
        ("T-027", "T-148", "T-149", "T-151"),
        ("validated_option_chain", "versioned_rate"),
        "HIGH",
        "P2",
        activation_state=FeatureActivationState.REGISTERED_NOT_ACTIVE,
    ),
    _feature(
        "FTR-026",
        "Identify official corporate catalysts and sponsor risk",
        ("BOTH",),
        ("official_event", "actor", "event_time", "available_at", "revision"),
        "SRC-NSE-EVENTS",
        "Official NSE/BSE filing or reconciled official artifact with PIT timestamps",
        "Normalize event, actor, dates and explicit terms; dedupe exchange mirrors by dataset root",
        "EVENT_AND_SPONSOR",
        "CG_EVENT_ROOT",
        "One economic event contributes once across mirrors",
        "Metadata-only or secondary discovery cannot confirm; conflicts produce WAIT",
        "CONFIRMED",
        False,
        "Versioned event claims, source links and revisions",
        "parsers/corporate_events_parser.py",
        "/api/selection/events",
        "Radar catalyst/warning and event inspector",
        ("T-015", "T-019", "T-113"),
        ("official_event_source", "event_reconciliation"),
        "HIGH",
        "P0",
    ),
    _feature(
        "FTR-027",
        "Add delayed institutional context without claiming live buying",
        ("SWING",),
        ("amfi_or_institutional_periods", "available_at", "security_mapping"),
        "SRC-DELAYED-CONTEXT",
        "Official delayed observations with publication and revision timestamps",
        "Compute PIT period-over-period deltas only after comparable mapping",
        "SPONSOR_DELAYED_CONTEXT",
        "CG_DELAYED_SPONSOR",
        "Delayed sponsor observations contribute once and never substitute events",
        "Stale, aggregate-only or unmapped data is UNKNOWN and cannot be live flow",
        "WATCH",
        False,
        "Period, lag, mapping and revision versions retained",
        "institutional_sources.py",
        "/api/institutional/context",
        "Inspector with explicit lag",
        ("T-019", "T-037", "T-116"),
        ("official_delayed_source", "pit_mapping"),
        "HIGH",
        "P2",
    ),
    _feature(
        "FTR-028",
        "Prevent wrong MCX contract, expiry or tender-window selection",
        ("BOTH",),
        ("mcx_contract_master", "expiry", "lot", "tick", "tender_delivery_calendar"),
        "SRC-MCX-MASTER",
        "Official verified master/calendar and local contract identity",
        "Resolve canonical contract and versioned commodity-specific veto windows",
        "TRADABILITY_AND_SAFETY",
        "CG_MCX_CONTRACT",
        "Contract-safety facts are gates, never positive votes",
        "Missing master/calendar/local identity caps MCX at WAIT; hard tender/expiry rule may REJECT",
        "WAIT",
        False,
        "Master/calendar/profile versions and restriction facts",
        "selection/mcx_contracts.py",
        "/api/v1/selection/fixtures/q5-r4",
        "Radar expiry warning and contract inspector",
        ("T-038", "T-046", "T-071"),
        ("verified_mcx_master", "mcx_calendar"),
        "HIGH",
        "P0",
        activation_state=FeatureActivationState.FIXTURE_ONLY,
    ),
    _feature(
        "FTR-029",
        "Measure local MCX structure and positioning",
        ("BOTH",),
        ("mcx_local_ohlcv", "mcx_local_oi", "contract_identity", "roll_event"),
        "SRC-MCX-LOCAL",
        "Verified local MCX contract artifact; global proxies prohibited as substitutes",
        "Apply closed-bar structure and same-contract OI quadrant with explicit roll continuity",
        "DERIVATIVES_OI",
        "CG_MCX_LOCAL_OI",
        "Local price/OI views share one MCX derivatives cap",
        "No local artifact or identity mismatch returns UNKNOWN/WAIT",
        "WAIT",
        True,
        "Contract-specific bars/OI and roll versions retained",
        "selection/mcx_features.py",
        "/api/selection/mcx/local",
        "MCX radar and local evidence inspector",
        ("T-038", "T-046", "T-145"),
        ("verified_mcx_local", "mcx_master"),
        "HIGH",
        "P1",
    ),
    _feature(
        "FTR-030",
        "Add commodity macro context without false recency",
        ("SWING",),
        ("cftc", "eia", "wgc_or_metals", "fx", "available_at"),
        "SRC-GLOBAL-COMMODITY",
        "Official delayed sources with explicit lag and revision time",
        "Compute versioned standardized changes/surprises by commodity profile",
        "MACRO_AND_COMMODITY_CONTEXT",
        "CG_COMMODITY_CONTEXT",
        "Correlated macro views share one context cap",
        "Delayed/stale observations are grey context and cannot create local OI",
        "WATCH",
        False,
        "Release, revision, lag and profile versions retained",
        "commodity_context.py",
        "/api/commodity/context",
        "Hidden macro context tab",
        ("T-019", "T-037", "T-060"),
        ("official_macro_sources", "availability_calendar"),
        "HIGH",
        "P2",
        activation_state=FeatureActivationState.REGISTERED_NOT_ACTIVE,
    ),
    _feature(
        "FTR-031",
        "Reuse broad deterministic scanner ideas under native contracts",
        ("BOTH",),
        ("pinned_upstream_definition", "normalized_bars", "native_feature_mapping"),
        "OPEN_SOURCE_REFERENCE",
        "Pinned offline reference only; native TrendForge source contracts govern runtime",
        "Map each scanner ID to versioned native feature/profile/correlation group",
        "EXPERIMENTAL",
        "CG_PK_SOURCE_RULE",
        "Scanner matches never become independent votes",
        "Unknown/unpinned ID is REGISTERED_NOT_ACTIVE and cannot emit a production claim",
        "WATCH",
        True,
        "Scanner definition, license, fixture and parity artifacts",
        "scanners/pk_compatibility.py",
        "CLI_OFFLINE_ONLY",
        "Scanner Lab development view",
        ("T-049", "T-057", "T-191"),
        ("pk_offline_harness", "native_feature_registry"),
        "HIGH",
        "P1",
        activation_state=FeatureActivationState.FIXTURE_ONLY,
    ),
    _feature(
        "FTR-032",
        "Compose deterministic screening stages reproducibly",
        ("BOTH",),
        ("versioned_pipe", "registered_scanners", "candidate_identity"),
        "LOCAL_DETERMINISTIC",
        "Local versioned profiles and registered native scanner outputs",
        "INTERSECTION, UNION, SEQUENCE and ENRICH record survivors/rejections; pipe emits zero claims",
        "EXPERIMENTAL",
        "CG_PIPE_COMPOSITION",
        "Family caps apply to native component claims after composition",
        "Invalid or missing stage fails the run and never silently skips",
        "WATCH",
        False,
        "Immutable pipe definition/run and stage counts",
        "scanners/pk_pipe_dsl.py",
        "/api/selection/scanner-pipes",
        "Scanner Lab stage flow",
        ("T-054", "T-072", "T-103"),
        ("native_scanner_registry",),
        "HIGH",
        "P1",
    ),
    _feature(
        "FTR-033",
        "Show what changed since a comparable prior run",
        ("BOTH",),
        ("current_candidate", "comparable_prior_candidate", "version_manifest"),
        "LOCAL_DERIVED",
        "Comparable runs must share profile, universe, strategy, parameters and data mode",
        "Diff state, gates, families, features, sources, freshness, completeness and versions",
        "EXPERIMENTAL",
        "CG_PRESENTATION_DIFF",
        "Presentation diff is never evidence",
        "No comparable run returns NO_BASELINE rather than invented change",
        "WATCH",
        False,
        "Append-only state events and comparison identity",
        "selection/history_validation.py",
        "/api/v1/selection/fixtures/q5-r6",
        "Primary change summary and full inspector diff",
        ("T-064", "T-104", "T-105"),
        ("selection_state_events",),
        "MEDIUM",
        "P0",
        activation_state=FeatureActivationState.FIXTURE_ONLY,
    ),
    _feature(
        "FTR-034",
        "Measure later candidate behavior without leakage",
        ("VALIDATION",),
        ("pit_candidates", "future_adjusted_bars", "cost_profile", "delistings"),
        "PIT_VALIDATION",
        "Only point-in-time datasets with publication availability and historical membership",
        "Versioned horizon outcomes, MFE/MAE, costs and walk-forward/holdout evaluation",
        "EXPERIMENTAL",
        "CG_OFFLINE_VALIDATION",
        "Offline outcomes never enter live evidence fusion",
        "Missing PIT/cost/delisting proof blocks PIT_APPROVED and performance UI",
        "WAIT",
        True,
        "Versioned datasets, outcomes, splits and drift artifacts",
        "selection/history_validation.py",
        "/api/v1/selection/fixtures/q5-r6",
        "Hidden validation tab only after PIT approval",
        ("T-059", "T-060", "T-204"),
        ("pit_store", "cost_profiles"),
        "HIGH",
        "P3",
        activation_state=FeatureActivationState.FIXTURE_ONLY,
    ),
    _feature(
        "FTR-035",
        "Block restricted or untradeable research candidates",
        ("BOTH",),
        ("t2t", "esm_asm_gsm", "fno_ban", "mwpl", "price_band", "halt", "session"),
        "SRC-NSE-SURVEILLANCE",
        "Official point-in-time restriction facts with profile-specific applicability",
        "Evaluate each restriction deterministically; hard rule REJECT, unknown required fact WAIT",
        "TRADABILITY_AND_SAFETY",
        "CG_TRADABILITY",
        "Restrictions are gates and add no positive score",
        "Unknown tick/lot/freeze/restriction cannot produce derivative or MCX CONFIRMED",
        "WAIT",
        False,
        "Versioned component outcomes and source fact IDs",
        "gate_readiness.py",
        "/api/gates/readiness",
        "Radar warning and hidden component table",
        ("T-043", "T-077", "T-118"),
        ("official_surveillance_sources", "profile_rules"),
        "HIGH",
        "P0",
    ),
    _feature(
        "FTR-036",
        "Explain sustained option positioning shifts",
        ("INTRADAY",),
        ("same_expiry_timeline", "pcr", "walls", "spot", "price_oi"),
        "SRC-NSE-OPTIONS",
        "Approved fresh option snapshots at a versioned interval",
        "Compute PCR delta, wall migration, completeness and aligned price/OI change",
        "OPTIONS_CONTEXT",
        "CG_OPTION_CHAIN",
        "Velocity remains inside the single option-chain family",
        "Sparse, mixed-expiry, incomplete or stale timeline returns null reason/WAIT",
        "WAIT",
        False,
        "Timestamped snapshot sequence and interval version",
        "selection/options_domain.py",
        "/api/selection/options/timeline",
        "PCR/wall inspector charts",
        ("T-082", "T-085", "T-118"),
        ("validated_option_chain", "snapshot_store"),
        "HIGH",
        "P1",
    ),
    _feature(
        "FTR-037",
        "Show point-in-time swing sector rotation",
        ("SWING",),
        ("pit_sector_constituents", "adjusted_sector_bars", "benchmark_bars"),
        "SRC-SECTOR",
        "PIT-adjusted EOD sector/index bars",
        "Versioned RS ratio and momentum classify leading, weakening, lagging or improving",
        "MARKET_AND_SECTOR_CONTEXT",
        "CG_SECTOR_RS",
        "RRG is context and cannot duplicate stock structure",
        "Missing PIT membership, alignment or CA state returns UNKNOWN; no intraday use",
        "WATCH",
        True,
        "Sector/universe/feature versions and history",
        "selection/relative_strength.py",
        "/api/selection/sector-rotation",
        "Sector chip and hidden quadrant history",
        ("T-086", "T-113", "T-204"),
        ("pit_universe", "adjusted_sector_bars"),
        "MEDIUM",
        "P2",
    ),
    _feature(
        "FTR-038",
        "Prevent wrong MCX roll-chain and synthetic-series decisions",
        ("BOTH",),
        ("mcx_master", "near_next_contracts", "local_liquidity", "roll_calendar"),
        "SRC-MCX-MASTER",
        "Verified official/local contract master, calendar and local price/OI",
        "Select eligible active contract with versioned liquidity tie-break; continuous series remains research-only",
        "TRADABILITY_AND_SAFETY",
        "CG_MCX_CONTRACT",
        "Near/next contracts resolve inside one roll group",
        "Missing master/calendar/local OI caps MCX at WAIT; synthetic symbol is never tradeable",
        "WAIT",
        False,
        "Contract master, roll event and continuous-series version",
        "selection/mcx_contracts.py",
        "/api/selection/mcx-rolls",
        "Expiry/roll warning and hidden details",
        ("T-141", "T-142", "T-145"),
        ("verified_mcx_master", "verified_mcx_local"),
        "HIGH",
        "P1",
    ),
    _feature(
        "FTR-039",
        "Reject invalid option quotes and model inputs",
        ("BOTH",),
        ("dated_chain", "bid_ask", "spot_forward", "strike", "expiry", "rate"),
        "SRC-NSE-OPTIONS",
        "Validated chain and versioned model inputs with source clocks",
        "Require finite non-negative quote/OI, ask>=bid, T>0 and declared strike completeness before metrics",
        "OPTIONS_CONTEXT",
        "CG_OPTION_CHAIN",
        "Domain guard protects the one option-chain family and adds no vote",
        "Crossed/zero/expired/stale/incomplete inputs make affected metrics UNKNOWN and required profile WAIT",
        "WAIT",
        False,
        "Versioned validity assessment, inputs and null reasons",
        "derivatives_engine.py",
        "/api/options/validate",
        "Option-domain warning in inspector",
        ("T-148", "T-149", "T-150", "T-151"),
        ("validated_option_chain", "versioned_option_math"),
        "MEDIUM",
        "P0",
        activation_state=FeatureActivationState.REGISTERED_NOT_ACTIVE,
    ),
    _feature(
        "FTR-040",
        "Rank closed cash-session participation without treating attention as probability",
        ("SWING",),
        ("current_nse_cash_fact", "r2_attention_priority", "r2_evidence_direction", "compiled_source_contract"),
        "SRC-NSE-CASH-EOD",
        "Official closed NSE cash bhavcopy for the expected trading session",
        "Use deterministic R2 attention priority as bounded participation strength; direction comes from the matching R2 row",
        "PARTICIPATION",
        "CG_ACTIVITY_SESSION",
        "Return, volume and turnover from one bhavcopy root produce at most one claim per symbol",
        "Missing, stale, unmatched, non-directional or compiler-unapproved inputs produce no selected claim and keep R3 WAIT",
        "WATCH",
        True,
        "Persist exact A1/A2 lineage, R1/R2 hashes, compiler permission fingerprint and feature version",
        "selection/r3_claim_adapter.py",
        "/api/v1/selection/resolution",
        "Hidden evidence inspector participation row; never a win probability",
        ("R3-T-001", "R3-T-004", "R3-T-009", "R3-T-012"),
        ("nse_bhavcopy_eod", "R1", "R2", "FUS-009"),
        "MEDIUM",
        "P0",
        activation_state=FeatureActivationState.RESEARCH_ACTIVE,
    ),)


def feature_contract_by_id(feature_id: str) -> FeatureContract | None:
    return next(
        (feature for feature in FEATURES if feature.feature_id == feature_id),
        None,
    )


def _declared_backend_routes() -> frozenset[str]:
    routes: set[str] = set()
    for module_path in MODULE_ROOT.rglob("*.py"):
        if module_path == Path(__file__).resolve():
            continue
        try:
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue
            if node.func.attr not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "api_route",
            }:
                continue
            if node.args and isinstance(node.args[0], ast.Constant):
                route = node.args[0].value
                if isinstance(route, str) and route.startswith("/"):
                    routes.add(route)
    return frozenset(routes)


def build_feature_registry() -> FeatureRegistryManifest:
    return FeatureRegistryManifest(
        registry_version=FEATURE_REGISTRY_VERSION,
        indicator_engine=pinned_indicator_engine(),
        features=FEATURES,
    )


def lint_feature_contract_rows(
    rows: list[dict[str, Any]],
) -> FeatureRegistryLintReport:
    errors: list[str] = []
    parsed: list[FeatureContract] = []
    for index, raw in enumerate(rows, start=1):
        missing_fields = sorted(set(MANDATORY_FEATURE_FIELDS) - set(raw))
        if missing_fields:
            errors.append(f"row {index} missing mandatory fields: {missing_fields}")
            continue
        try:
            parsed.append(FeatureContract.model_validate(raw))
        except ValidationError as exc:
            errors.append(f"row {index} schema error: {exc.errors(include_url=False)}")

    ids = [feature.feature_id for feature in parsed]
    duplicates = sorted({feature_id for feature_id in ids if ids.count(feature_id) > 1})
    missing_ids = sorted(EXPECTED_FEATURE_IDS - set(ids))
    unexpected_ids = sorted(set(ids) - EXPECTED_FEATURE_IDS)
    if duplicates:
        errors.append(f"duplicate feature IDs: {duplicates}")
    if missing_ids:
        errors.append(f"missing feature IDs: {missing_ids}")
    if unexpected_ids:
        errors.append(f"unexpected feature IDs: {unexpected_ids}")

    declared_routes = _declared_backend_routes()
    for feature in parsed:
        if feature.activation_state is FeatureActivationState.REGISTERED_NOT_ACTIVE:
            continue
        module_path = (MODULE_ROOT / feature.backend_module).resolve()
        if MODULE_ROOT not in module_path.parents or not module_path.is_file():
            errors.append(
                f"{feature.feature_id} {feature.activation_state.value} backend module "
                f"does not exist: {feature.backend_module}"
            )
        if (
            feature.activation_state
            in {
                FeatureActivationState.RESEARCH_ACTIVE,
                FeatureActivationState.PIT_APPROVED,
            }
            and feature.api_field_or_route.startswith("/")
            and feature.api_field_or_route not in declared_routes
        ):
            errors.append(
                f"{feature.feature_id} {feature.activation_state.value} API route "
                f"is not declared: {feature.api_field_or_route}"
            )

    runtime = verify_indicator_runtime()
    if not runtime.ok:
        errors.extend(runtime.errors)
    return FeatureRegistryLintReport(
        ok=not errors,
        registry_version=FEATURE_REGISTRY_VERSION,
        expected_feature_count=len(EXPECTED_FEATURE_IDS),
        validated_feature_count=len(parsed),
        required_fields=MANDATORY_FEATURE_FIELDS,
        runtime_engine=runtime,
        errors=tuple(errors),
        warnings=(
            "Registry presence is not implementation, live-source, PIT or CONFIRMED proof.",
        ),
    )


def lint_feature_registry() -> FeatureRegistryLintReport:
    rows = [feature.model_dump(mode="python") for feature in FEATURES]
    return lint_feature_contract_rows(rows)


def main() -> int:
    report = lint_feature_registry()
    print(report.model_dump_json(by_alias=True, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
