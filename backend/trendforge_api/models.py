from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class CandidateType(str, Enum):
    STOCK = "stock"
    HARMONIC = "harmonic"
    MCX = "mcx"


class StatusGroup(str, Enum):
    READY = "ready"
    WAIT = "wait"
    REJECT = "reject"


class Tone(str, Enum):
    GOOD = "good"
    WARN = "warn"
    BAD = "bad"
    INFO = "info"


class SourceState(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    WARN = "WARN"
    RED = "RED"
    NA = "NA"


class PairRow(BaseModel):
    label: str
    value: str


class MetricRow(BaseModel):
    label: str
    value: str
    note: str


class TradePlan(BaseModel):
    entry: str
    stop: str
    target: str


class RadarCandidate(BaseModel):
    symbol: str
    type: CandidateType
    state: str
    state_tone: Tone = Field(alias="stateTone")
    status_group: StatusGroup = Field(alias="statusGroup")
    setup: str
    timeframe: list[str]
    price: str
    move: str
    reason: str
    decision_title: str = Field(alias="decisionTitle")
    decision_text: str = Field(alias="decisionText")
    trade: TradePlan
    quality: int = Field(ge=0, le=100)
    metrics: list[MetricRow]
    proof: list[PairRow]
    risk: list[PairRow]
    sources: list[PairRow]
    series: list[int]

    model_config = {"populate_by_name": True}


class CommandBar(BaseModel):
    system: str
    regime: str
    india_vix: str = Field(alias="indiaVix")
    safety: str
    liquidity_window: str = Field(alias="liquidityWindow")
    expiry_mode: str = Field(alias="expiryMode")
    no_trade_override: str = Field(alias="noTradeOverride")

    model_config = {"populate_by_name": True}


class SourceHealth(BaseModel):
    name: str
    owner: str
    state: SourceState
    trust_label: str = Field(alias="trustLabel")
    update_frequency: str = Field(alias="updateFrequency")
    latest_data_date: str = Field(alias="latestDataDate")
    decision_use: str = Field(alias="decisionUse")
    url: str
    last_attempted_at: str | None = Field(default=None, alias="lastAttemptedAt")
    last_successful_at: str | None = Field(default=None, alias="lastSuccessfulAt")
    consecutive_failures: int = Field(default=0, alias="consecutiveFailures")
    stale_threshold_hours: int | None = Field(default=None, alias="staleThresholdHours")
    limitation: str = ""
    # CROSS-006: Hybrid §16.3 ladder joined from inventory compiler (not GREEN=ready).
    source_key: str | None = Field(default=None, alias="sourceKey")
    maturity_state: str | None = Field(default=None, alias="maturityState")
    gate_permission: bool = Field(default=False, alias="gatePermission")
    source_activation_ready: bool = Field(default=False, alias="sourceActivationReady")

    model_config = {"populate_by_name": True}


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    mode: str


class ResearchCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9&._ -]+$")
    title: str | None = Field(default=None, max_length=200)
    note: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: list[str]) -> list[str]:
        cleaned = []
        for value in values:
            item = value.strip()
            if not item:
                continue
            if len(item) > 64:
                raise ValueError("each tag must be at most 64 characters")
            cleaned.append(item)
        return cleaned


class ResearchRecord(BaseModel):
    id: int
    symbol: str
    title: str
    note: str
    tags: list[str]
    created_at: str = Field(alias="createdAt")
    candidate: dict[str, Any]
    command_bar: dict[str, Any] = Field(alias="commandBar")
    source_health: list[dict[str, Any]] = Field(alias="sourceHealth")

    model_config = {"populate_by_name": True}


class MLScanRun(BaseModel):
    id: int
    run_hash: str = Field(alias="runHash")
    trigger: str
    candidate_count: int = Field(alias="candidateCount")
    created_at: str = Field(alias="createdAt")
    command_bar: dict[str, Any] = Field(alias="commandBar")
    source_health: list[dict[str, Any]] = Field(alias="sourceHealth")

    model_config = {"populate_by_name": True}


class MLScanCandidate(BaseModel):
    id: int
    run_id: int = Field(alias="runId")
    symbol: str
    candidate_type: str = Field(alias="candidateType")
    state: str
    status_group: str = Field(alias="statusGroup")
    quality: int
    payload: dict[str, Any]
    outcome_label: str | None = Field(default=None, alias="outcomeLabel")
    false_screen_reason: str | None = Field(default=None, alias="falseScreenReason")
    created_at: str = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class MLScanStatus(BaseModel):
    total_runs: int = Field(alias="totalRuns")
    total_candidates: int = Field(alias="totalCandidates")
    latest_run: MLScanRun | None = Field(default=None, alias="latestRun")

    model_config = {"populate_by_name": True}


class HarmonicSource(BaseModel):
    name: str
    url: str
    category: str
    trust_level: str = Field(alias="trustLevel")
    use_now: str = Field(alias="useNow")
    limitation: str
    backend_role: str = Field(alias="backendRole")

    model_config = {"populate_by_name": True}


class DataTrust(str, Enum):
    OFFICIAL = "OFFICIAL"
    OFFICIAL_OR_LICENSED = "OFFICIAL_OR_LICENSED"
    OFFICIAL_FREE_EOD = "OFFICIAL_FREE_EOD"
    OPEN_SOURCE_UNOFFICIAL = "OPEN_SOURCE_UNOFFICIAL"
    UNOFFICIAL_WRAPPER = "UNOFFICIAL_WRAPPER"
    UNOFFICIAL_TEMP = "UNOFFICIAL_TEMP"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"


class FreshnessState(str, Enum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    STALE = "STALE"
    BROKEN = "BROKEN"
    UNKNOWN = "UNKNOWN"


class OHLCVFetchRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: Literal[
        "1m", "5m", "15m", "30m", "1h", "4h", "4h_custom", "1d", "1w"
    ] = "1d"
    period: str | None = None
    source: Literal[
        "openalgo", "yfinance", "nsepython", "nselib", "openchart", "static_csv"
    ] = "yfinance"


BarState = Literal[
    "COMPLETE", "PARTIAL_NSE_SESSION", "PARTIAL_PERIOD", "INCOMPLETE_SOURCE"
]
AdjustmentStatus = Literal["UNKNOWN", "NOT_REQUIRED", "ADJUSTED", "UNADJUSTED"]


class OHLCVCandle(BaseModel):
    symbol: str
    timeframe: str
    source: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    trust_level: DataTrust = Field(alias="trustLevel")
    fetched_at: str = Field(alias="fetchedAt")
    bar_state: BarState = Field(default="COMPLETE", alias="barState")
    session_date: str | None = Field(default=None, alias="sessionDate")
    completeness: float = Field(default=1.0, gt=0, le=1)
    adjustment_status: AdjustmentStatus = Field(
        default="UNKNOWN", alias="adjustmentStatus"
    )
    adjustment_factor: float = Field(default=1.0, alias="adjustmentFactor", gt=0)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_market_geometry(self) -> "OHLCVCandle":
        prices = (self.open, self.high, self.low, self.close)
        if any(value <= 0 for value in prices):
            raise ValueError("OHLC prices must be positive")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError(
                "high must be greater than or equal to open, low, and close"
            )
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low must be less than or equal to open, high, and close")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")
        return self


class OHLCVFetchResponse(BaseModel):
    symbol: str
    requested_symbol: str = Field(alias="requestedSymbol")
    timeframe: str
    source: str
    trust_level: DataTrust = Field(alias="trustLevel")
    candle_count: int = Field(alias="candleCount")
    saved_count: int = Field(alias="savedCount")
    warning: str | None = None
    candles: list[OHLCVCandle] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class NSEResampleResponse(BaseModel):
    symbol: str
    source: str
    source_timeframe: str = Field(alias="sourceTimeframe")
    target_timeframe: str = Field(alias="targetTimeframe")
    candle_count: int = Field(alias="candleCount")
    saved_count: int = Field(alias="savedCount")
    warnings: list[str] = Field(default_factory=list)
    candles: list[OHLCVCandle] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class HarmonicScanRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: Literal["5m", "15m", "30m", "1h", "4h", "4h_custom", "1d", "1w"] = "1d"
    period: str | None = None
    source: Literal["yfinance", "nsepython", "nselib", "openchart", "static_csv"] = (
        "yfinance"
    )
    use_stored: bool = Field(default=False, alias="useStored")
    save_ml_snapshot: bool = Field(default=True, alias="saveMlSnapshot")

    model_config = {"populate_by_name": True}


class HarmonicPoint(BaseModel):
    label: Literal["X", "A", "B", "C", "D"]
    timestamp: str
    price: float


class HarmonicPatternResult(BaseModel):
    id: int | None = None
    symbol: str
    timeframe: str
    direction: Literal["bullish", "bearish", "unknown"]
    pattern_name: str = Field(alias="patternName")
    state: str
    source_engine: str = Field(alias="sourceEngine")
    points: list[HarmonicPoint] = Field(default_factory=list)
    prz_low: float | None = Field(default=None, alias="przLow")
    prz_high: float | None = Field(default=None, alias="przHigh")
    invalidation_price: float | None = Field(default=None, alias="invalidationPrice")
    target1: float | None = None
    target2: float | None = None
    confidence: int = Field(ge=0, le=100)
    confirmation_state: str = Field(alias="confirmationState")
    final_state: str = Field(alias="finalState")
    reasons: list[str] = Field(default_factory=list)
    gates: list[PairRow] = Field(default_factory=list)
    created_at: str | None = Field(default=None, alias="createdAt")

    model_config = {"populate_by_name": True}


class HarmonicScanResponse(BaseModel):
    symbol: str
    timeframe: str
    source: str
    trust_level: DataTrust = Field(alias="trustLevel")
    candle_count: int = Field(alias="candleCount")
    patterns: list[HarmonicPatternResult]
    saved_ml_run_id: int | None = Field(default=None, alias="savedMlRunId")
    warning: str | None = None

    model_config = {"populate_by_name": True}


class SourceRegistryRecord(BaseModel):
    name: str
    adapter: str
    authority: DataTrust
    freshness: FreshnessState
    status: SourceState
    last_success_at: str | None = Field(default=None, alias="lastSuccessAt")
    last_error: str | None = Field(default=None, alias="lastError")
    updated_at: str = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class SourceCatalogRecord(BaseModel):
    key: str
    name: str
    url: str
    category: str
    authority: DataTrust
    expected_frequency: str = Field(alias="expectedFrequency")
    decision_use: str = Field(alias="decisionUse")
    parser_status: str = Field(alias="parserStatus")
    freshness_required: bool = Field(alias="freshnessRequired")
    stale_after_hours: int | None = Field(default=None, alias="staleAfterHours")
    limitation: str

    model_config = {"populate_by_name": True}


class SourceSnapshotRecord(BaseModel):
    id: int | None = None
    source_key: str = Field(alias="sourceKey")
    name: str
    url: str
    check_state: Literal[
        "NEW", "UNCHANGED", "CHANGED", "STALE", "BROKEN", "SKIPPED"
    ] = Field(alias="checkState")
    status_code: int | None = Field(default=None, alias="statusCode")
    content_hash: str | None = Field(default=None, alias="contentHash")
    content_length: int | None = Field(default=None, alias="contentLength")
    last_modified: str | None = Field(default=None, alias="lastModified")
    etag: str | None = None
    raw_path: str | None = Field(default=None, alias="rawPath")
    error: str | None = None
    checked_at: str = Field(alias="checkedAt")
    previous_hash: str | None = Field(default=None, alias="previousHash")
    changed: bool

    model_config = {"populate_by_name": True}


class SourceMonitorSummary(BaseModel):
    total_sources: int = Field(alias="totalSources")
    checked: int
    new_count: int = Field(alias="newCount")
    changed_count: int = Field(alias="changedCount")
    unchanged_count: int = Field(alias="unchangedCount")
    broken_count: int = Field(alias="brokenCount")
    skipped_count: int = Field(alias="skippedCount")
    results: list[SourceSnapshotRecord]

    model_config = {"populate_by_name": True}


class SourceInventoryAuditRequest(BaseModel):
    fetch_ids: list[int] = Field(default_factory=list, alias="fetchIds", max_length=25)
    use_browser: bool = Field(default=False, alias="useBrowser")
    timeout_seconds: int = Field(default=15, alias="timeoutSeconds", ge=1, le=60)
    max_bytes: int = Field(default=5_000_000, alias="maxBytes", ge=1024, le=20_000_000)
    throttle_ms: int = Field(default=250, alias="throttleMs", ge=0, le=5000)

    model_config = {"populate_by_name": True}

    @field_validator("fetch_ids")
    @classmethod
    def validate_fetch_ids(cls, values: list[int]) -> list[int]:
        if any(value < 1 for value in values):
            raise ValueError("fetchIds must contain positive inventory IDs")
        if len(set(values)) != len(values):
            raise ValueError("fetchIds must not contain duplicates")
        return values


class SourceParseResult(BaseModel):
    id: int | None = None
    source_key: str = Field(alias="sourceKey")
    snapshot_id: int | None = Field(default=None, alias="snapshotId")
    parser_state: Literal[
        "PARSED",
        "PARSED_STRUCTURED",
        "PARSED_METADATA_ONLY",
        "WAIT_SOURCE_SNAPSHOT",
        "WAIT_FETCH_REQUIRED",
        "WAIT_EMPTY_PARSE",
        "WAIT_STALE_DATA",
        "WAIT_PARSE_ERROR",
        "WAIT_SCHEMA_MISMATCH",
        "WAIT_SOURCE_DATE",
        "NO_PARSER",
        "BROKEN",
    ] = Field(alias="parserState")
    data_date: str | None = Field(default=None, alias="dataDate")
    record_count: int = Field(default=0, alias="recordCount")
    summary: str
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    parsed_at: str = Field(alias="parsedAt")

    model_config = {"populate_by_name": True}


class ParquetStatus(BaseModel):
    available: bool
    base_path: str = Field(alias="basePath")
    file_count: int = Field(alias="fileCount")
    row_count: int = Field(alias="rowCount")
    message: str

    model_config = {"populate_by_name": True}


class PivotPoint(BaseModel):
    index: int
    kind: Literal["high", "low"]
    timestamp: str
    price: float
    sensitivities: list[int]
    quality: float


class RatioValidation(BaseModel):
    pattern_name: str = Field(alias="patternName")
    direction: Literal["bullish", "bearish", "unknown"]
    tolerance_tier: str = Field(alias="toleranceTier")
    score: float
    passed: bool
    ratios: dict[str, float]
    required: dict[str, str]
    prz_low: float | None = Field(default=None, alias="przLow")
    prz_high: float | None = Field(default=None, alias="przHigh")
    invalidation_price: float | None = Field(default=None, alias="invalidationPrice")
    target1: float | None = None
    target2: float | None = None
    target3: float | None = None
    reasons: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class GateResult(BaseModel):
    code: str
    name: str
    result: Literal["PASS", "FAIL", "NEUTRAL", "UNKNOWN"]
    weight: int
    reason: str


class HarmonicAdvancedAnalysis(BaseModel):
    symbol: str
    timeframe: str
    candle_count: int = Field(alias="candleCount")
    pivots: list[PivotPoint]
    validations: list[RatioValidation]
    gates: list[GateResult]
    hybrid_quality_score: float = Field(alias="hybridQualityScore")
    gate_ratio: float = Field(alias="gateRatio")
    final_state: str = Field(alias="finalState")
    lifecycle_state: str = Field(alias="lifecycleState")
    alerts: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class HarmonicAlertRecord(BaseModel):
    id: int | None = None
    symbol: str
    timeframe: str
    alert_type: str = Field(alias="alertType")
    message: str
    state: str
    created_at: str | None = Field(default=None, alias="createdAt")

    model_config = {"populate_by_name": True}
