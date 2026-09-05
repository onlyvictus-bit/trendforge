"""File A S3 cheap discovery over the full R2 cash universe.

S3 is an additive research projection. It does not rebuild A3 profiles, change
R2 attention priority, query delivery/MTO, or unlock CONFIRMED. Optional source
failures become explicit UNKNOWN reasons and never remove a stock.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, time
from statistics import median
from typing import Any, Callable
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ..fii_stock_signals import CanonicalLatestResultLoader
from .attention_order import InventoryDiscoveryV1, latest_attention_order
from .cash_a1_staging import default_market_data_store
from .cash_a3_discovery import CashDiscoveryBatch, latest_cash_discovery
from .cash_a4_history import CashRawSessionBar, list_raw_bars, list_raw_bars_by_symbol
from .contracts import SelectionState, stable_id

SCHEMA_VERSION = "trendforge.s3-cheap-discovery.v1"
PROFILE_ID = "PRF-S3-CHEAP-DISCOVERY"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_S3_WATCH_WAIT_ONLY"
DEFAULT_COMPLETENESS_THRESHOLD = 0.95
MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    frozen=True,
)

PREOPEN_SOURCE_KEYS = ("nse_preopen_cash", "nse_preopen_fo")
ACTIVITY_SOURCE_KEYS = (
    "nse_most_active_volume",
    "nse_most_active_value",
    "nse_volume_gainers",
)
OI_SOURCE_KEYS = ("nse_oi_spurts", "nse_oi_spurts_contracts")
EVENT_SOURCE_KEYS = (
    "nse_large_deals",
    "nse_large_deals_snapshot",
    "nse_announcements",
)
ALL_OPTIONAL_SOURCE_KEYS = (
    *PREOPEN_SOURCE_KEYS,
    *ACTIVITY_SOURCE_KEYS,
    *OI_SOURCE_KEYS,
    *EVENT_SOURCE_KEYS,
)

ResultLoader = Callable[[str], Any]
HistoryLoader = Callable[..., list[CashRawSessionBar]]


class S3CheapDiscoveryRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    instrument_id: str
    public_state: SelectionState
    attention_priority: float | None = Field(default=None, ge=0.0, le=1.0)
    a3_profiles: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    why: tuple[str, ...] = ()
    why_unknown: tuple[str, ...] = ()
    rvol_eod: float | None = Field(default=None, ge=0.0)
    rs_1d: float | None = None
    rs_5d: float | None = None
    completeness_contribution: float = Field(ge=0.0, le=1.0)
    research_state: SelectionState
    can_unlock_confirmed: bool = False

    @model_validator(mode="after")
    def enforce_s3_ceiling(self) -> "S3CheapDiscoveryRowV1":
        if self.public_state is SelectionState.CONFIRMED:
            raise ValueError("S3 cannot accept CONFIRMED input")
        if self.research_state is SelectionState.CONFIRMED:
            raise ValueError("S3 cannot produce CONFIRMED")
        if self.can_unlock_confirmed:
            raise ValueError("S3 cannot unlock CONFIRMED")
        return self


class S3CheapDiscoveryBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    run_id: str
    run_hash: str
    a3_batch_id: str
    r2_run_id: str
    r2_run_hash: str
    trading_date: str
    built_at: datetime
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    confirmed_count: int = 0
    delivery_queried: bool = False
    eligible_count: int = Field(ge=0)
    scanned_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    unattempted_count: int = Field(ge=0)
    completeness: float = Field(ge=0.0, le=1.0)
    completeness_threshold: float = Field(ge=0.0, le=1.0)
    wait_partial_scan: bool
    layer_status: dict[str, str]
    native_core_matches: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    rows: tuple[S3CheapDiscoveryRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_contract(self) -> "S3CheapDiscoveryBatchV1":
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("S3 cannot activate sources or unlock CONFIRMED")
        if self.confirmed_count != 0 or self.delivery_queried:
            raise ValueError("S3 confirmation and delivery contracts are locked")
        if self.scanned_count + self.failed_count + self.unattempted_count != self.eligible_count:
            raise ValueError("S3 completeness counts do not reconcile")
        if self.eligible_count + self.excluded_count != len(self.rows):
            raise ValueError("S3 universe counts do not reconcile")
        if any(row.research_state is SelectionState.CONFIRMED for row in self.rows):
            raise ValueError("S3 cannot contain CONFIRMED")
        return self


class S3WatchQueueV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = "trendforge.s3-watch-queue.v1"
    source_run_id: str
    source_run_hash: str
    built_at: datetime
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    completeness: float = Field(ge=0.0, le=1.0)
    wait_partial_scan: bool
    limit: int = Field(gt=0)
    total_watch_count: int = Field(ge=0)
    rows: tuple[S3CheapDiscoveryRowV1, ...]


def default_result_loader() -> ResultLoader:
    return CanonicalLatestResultLoader(default_market_data_store())


def _usable(result: Any) -> tuple[list[dict[str, Any]], str] | None:
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
    rows: list[dict[str, Any]] = []
    for key in ("rows", "records", "data", "deals"):
        value = output.get(key)
        if isinstance(value, list):
            rows = [row for row in value if isinstance(row, dict)]
            break
    return rows, str(data_date or "")


def _normalized(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "".join(ch for ch in str(key).lower() if ch.isalnum()): value
        for key, value in row.items()
    }


def _text(row: dict[str, Any], *aliases: str) -> str | None:
    values = _normalized(row)
    for alias in aliases:
        key = "".join(ch for ch in alias.lower() if ch.isalnum())
        value = values.get(key)
        if value not in (None, ""):
            text = str(value).strip()
            if text:
                return text
    return None


def _symbol(row: dict[str, Any]) -> str | None:
    direct = _text(row, "symbol", "underlying", "securitySymbol", "ticker")
    if direct:
        return direct.upper()
    for key in ("metadata", "detail", "preOpenMarket"):
        nested = row.get(key)
        if isinstance(nested, dict):
            value = _symbol(nested)
            if value:
                return value
    return None


def _source_indexes(loader: ResultLoader | None) -> tuple[dict[str, set[str]], dict[str, str]]:
    indexes: dict[str, set[str]] = {}
    status: dict[str, str] = {}
    for key in ALL_OPTIONAL_SOURCE_KEYS:
        usable = _usable(loader(key)) if callable(loader) else None
        if usable is None:
            indexes[key] = set()
            status[key] = "UNKNOWN_MISSING_OR_UNUSABLE"
            continue
        rows, data_date = usable
        indexes[key] = {symbol for row in rows if (symbol := _symbol(row))}
        status[key] = "VALID_EMPTY" if not rows else f"USABLE:{data_date or 'DATE_UNKNOWN'}"
    return indexes, status


def _preopen_active(built_at: datetime, trading_date: str) -> bool:
    ist = built_at.astimezone(ZoneInfo("Asia/Kolkata"))
    return ist.date().isoformat() == trading_date and time(8, 55) <= ist.time() <= time(9, 15)


def _history_metrics(
    symbol: str,
    *,
    through: date,
    history_loader: HistoryLoader,
    wait_ca: bool,
) -> tuple[float | None, float | None, float | None, tuple[str, ...], tuple[str, ...]]:
    tags: list[str] = []
    unknown: list[str] = []
    bars = history_loader(symbol, through=through)
    bars = sorted((bar for bar in bars if bar.trade_date <= through), key=lambda bar: bar.trade_date)

    rvol: float | None = None
    if len(bars) >= 21:
        current = bars[-1]
        baseline = median(float(bar.volume) for bar in bars[-21:-1])
        if baseline > 0:
            rvol = round(float(current.volume) / baseline, 4)
            tags.append("RVOL_EOD")
        else:
            unknown.append("UNKNOWN_RVOL_ZERO_BASELINE")
    else:
        unknown.append("UNKNOWN_RVOL_NEEDS_20_PRIOR_SESSIONS")

    if len(bars) >= 8:
        current = bars[-1]
        if current.high is not None and current.low is not None:
            current_range = float(current.high) - float(current.low)
            prior_ranges = [
                float(bar.high) - float(bar.low)
                for bar in bars[-8:-1]
                if bar.high is not None and bar.low is not None
            ]
            if len(prior_ranges) == 7 and current_range <= min(prior_ranges):
                tags.append("NR7")
        else:
            unknown.append("UNKNOWN_NR7_BAR_FIELDS")
    else:
        unknown.append("UNKNOWN_NR7_NEEDS_8_SESSIONS")

    if wait_ca:
        unknown.append("UNKNOWN_RS_WAIT_CA")
        return rvol, None, None, tuple(tags), tuple(unknown)

    benchmark: list[CashRawSessionBar] = []
    for key in ("NIFTY 50", "NIFTY50"):
        benchmark = history_loader(key, through=through)
        if benchmark:
            break
    benchmark_by_date = {bar.trade_date: bar for bar in benchmark}
    aligned = [(bar, benchmark_by_date.get(bar.trade_date)) for bar in bars]
    aligned = [(stock, index) for stock, index in aligned if index is not None]

    def relative_return(period: int) -> float | None:
        if len(aligned) < period + 1:
            return None
        stock_now, index_now = aligned[-1]
        stock_then, index_then = aligned[-period - 1]
        if stock_then.close <= 0 or index_then.close <= 0:
            return None
        stock_return = float(stock_now.close) / float(stock_then.close) - 1.0
        index_return = float(index_now.close) / float(index_then.close) - 1.0
        return round((stock_return - index_return) * 100.0, 4)

    rs_1d = relative_return(1)
    rs_5d = relative_return(5)
    if rs_1d is not None:
        tags.append("RS_1D")
    else:
        unknown.append("UNKNOWN_RS_1D_NO_ALIGNED_BENCHMARK")
    if rs_5d is not None:
        tags.append("RS_5D")
    else:
        unknown.append("UNKNOWN_RS_5D_NO_ALIGNED_BENCHMARK")
    return rvol, rs_1d, rs_5d, tuple(tags), tuple(unknown)


def _lineage_is_current(discovery: CashDiscoveryBatch, attention: InventoryDiscoveryV1) -> bool:
    if not attention.rows:
        return False
    for row in attention.rows:
        if row.lineage.get("cashPipelineRunId") != attention.cash_pipeline_run_id:
            return False
        if row.lineage.get("discoveryBatchId") != discovery.batch_id:
            return False
    return True


def build_s3_cheap_discovery(
    *,
    discovery: CashDiscoveryBatch | None = None,
    attention: InventoryDiscoveryV1 | None = None,
    loader: ResultLoader | None = None,
    history_loader: HistoryLoader = list_raw_bars,
    built_at: datetime | None = None,
    completeness_threshold: float = DEFAULT_COMPLETENESS_THRESHOLD,
) -> S3CheapDiscoveryBatchV1:
    a3 = discovery or latest_cash_discovery()
    r2 = attention or latest_attention_order()
    if a3 is None or r2 is None:
        raise ValueError("WAIT_S3_SPINE_NOT_READY")
    if not _lineage_is_current(a3, r2):
        raise ValueError("WAIT_S3_LINEAGE_MISMATCH")
    if not 0 <= completeness_threshold <= 1:
        raise ValueError("S3 completeness threshold must be between 0 and 1")

    at = built_at or datetime.now(UTC)
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("S3 built_at must be timezone-aware")
    effective_loader = loader if loader is not None else default_result_loader()
    indexes, layer_status = _source_indexes(effective_loader)
    a3_by_symbol = {row.symbol.upper(): row for row in a3.rows}
    trading_date = date.fromisoformat(r2.trading_date)
    preopen_active = _preopen_active(at, r2.trading_date)
    history_for_run = history_loader
    if history_loader is list_raw_bars:
        wanted_symbols = {row.symbol.upper() for row in r2.rows}
        wanted_symbols.update({"NIFTY 50", "NIFTY50"})
        history_cache = list_raw_bars_by_symbol(wanted_symbols, through=trading_date)

        def cached_history(symbol: str, *, through: date) -> list[CashRawSessionBar]:
            del through
            return history_cache.get(symbol.upper(), [])

        history_for_run = cached_history

    rows: list[S3CheapDiscoveryRowV1] = []
    scanned = 0
    failed = 0
    unattempted = 0
    excluded = 0
    for attention_row in r2.rows:
        symbol = attention_row.symbol.upper()
        if attention_row.public_state is SelectionState.REJECT:
            excluded += 1
            rows.append(
                S3CheapDiscoveryRowV1(
                    symbol=symbol,
                    instrument_id="",
                    public_state=SelectionState.REJECT,
                    attention_priority=None,
                    why=("S1/R2 rejection preserved; S3 did not scan or override it.",),
                    why_unknown=(),
                    completeness_contribution=0.0,
                    research_state=SelectionState.REJECT,
                )
            )
            continue

        a3_row = a3_by_symbol.get(symbol)
        if a3_row is None:
            unattempted += 1
            rows.append(
                S3CheapDiscoveryRowV1(
                    symbol=symbol,
                    instrument_id="",
                    public_state=attention_row.public_state,
                    attention_priority=attention_row.attention_priority,
                    why=("R2 row retained, but its A3 row is absent.",),
                    why_unknown=("WAIT_S3_A3_ROW_MISSING",),
                    completeness_contribution=0.0,
                    research_state=SelectionState.WAIT,
                )
            )
            continue

        try:
            tags = [profile.value for profile in a3_row.discovery_profiles]
            why = [a3_row.discovery_reason]
            unknown: list[str] = ["NATIVE_SCANNER_NOT_REGISTERED"]

            if preopen_active:
                if any(symbol in indexes[key] for key in PREOPEN_SOURCE_KEYS):
                    tags.append("PREOPEN_SESSION")
                elif all(layer_status[key] == "VALID_EMPTY" for key in PREOPEN_SOURCE_KEYS):
                    why.append("Official pre-open sources are valid-empty for this session.")
                else:
                    unknown.append("UNKNOWN_PREOPEN_NO_SYMBOL_ROW")
            else:
                unknown.append("UNKNOWN_PREOPEN_OUTSIDE_WINDOW")

            activity_hits = [key for key in ACTIVITY_SOURCE_KEYS if symbol in indexes[key]]
            if activity_hits:
                tags.append("ACTIVITY_LIST")
                why.append("Seen in official activity list(s): " + ", ".join(activity_hits))
            elif any(layer_status[key].startswith("UNKNOWN") for key in ACTIVITY_SOURCE_KEYS):
                unknown.append("UNKNOWN_ACTIVITY_SOURCE")

            oi_hits = [key for key in OI_SOURCE_KEYS if symbol in indexes[key]]
            if oi_hits:
                tags.append("OI_SPURT")
                why.append("F&O symbol seen in official OI-spurt context.")

            event_hits = [key for key in EVENT_SOURCE_KEYS if symbol in indexes[key]]
            if event_hits:
                tags.append("HAS_OFFICIAL_EVENT")
                why.append("Official event/deal index contains this symbol; no direction inferred.")
            elif any(layer_status[key].startswith("UNKNOWN") for key in EVENT_SOURCE_KEYS):
                unknown.append("UNKNOWN_OFFICIAL_EVENT_INDEX")

            wait_ca = any("WAIT_CA" in str(value).upper() for value in attention_row.why_not_confirmed)
            rvol, rs_1d, rs_5d, history_tags, history_unknown = _history_metrics(
                symbol,
                through=trading_date,
                history_loader=history_for_run,
                wait_ca=wait_ca,
            )
            tags.extend(history_tags)
            unknown.extend(history_unknown)
            scanned += 1
            research_state = (
                SelectionState.WATCH
                if attention_row.public_state is SelectionState.WATCH
                else SelectionState.WAIT
            )
            rows.append(
                S3CheapDiscoveryRowV1(
                    symbol=symbol,
                    instrument_id=a3_row.instrument_id,
                    public_state=attention_row.public_state,
                    attention_priority=attention_row.attention_priority,
                    a3_profiles=tuple(profile.value for profile in a3_row.discovery_profiles),
                    tags=tuple(dict.fromkeys(tags)),
                    why=tuple(dict.fromkeys(why)),
                    why_unknown=tuple(dict.fromkeys(unknown)),
                    rvol_eod=rvol,
                    rs_1d=rs_1d,
                    rs_5d=rs_5d,
                    completeness_contribution=1.0,
                    research_state=research_state,
                )
            )
        except Exception as exc:
            failed += 1
            rows.append(
                S3CheapDiscoveryRowV1(
                    symbol=symbol,
                    instrument_id=a3_row.instrument_id,
                    public_state=attention_row.public_state,
                    attention_priority=attention_row.attention_priority,
                    a3_profiles=tuple(profile.value for profile in a3_row.discovery_profiles),
                    why=("S3 row processing failed closed.",),
                    why_unknown=(f"WAIT_S3_ROW_FAILED:{type(exc).__name__}",),
                    completeness_contribution=0.0,
                    research_state=SelectionState.WAIT,
                )
            )

    eligible = len(r2.rows) - excluded
    completeness = round(scanned / eligible, 6) if eligible else 1.0
    partial = completeness < completeness_threshold
    if partial:
        rows = [
            row.model_copy(
                update={
                    "research_state": (
                        SelectionState.WAIT
                        if row.research_state is SelectionState.WATCH
                        else row.research_state
                    ),
                    "why_unknown": tuple(dict.fromkeys((*row.why_unknown, "WAIT_PARTIAL_SCAN"))),
                }
            )
            for row in rows
        ]

    identity = {
        "a3BatchId": a3.batch_id,
        "r2RunId": r2.run_id,
        "r2RunHash": r2.run_hash,
        "tradingDate": r2.trading_date,
        "profileVersion": PROFILE_VERSION,
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
        "layerStatus": layer_status,
    }
    run_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return S3CheapDiscoveryBatchV1(
        run_id=stable_id("s3-cheap", a3.batch_id, r2.run_id, run_hash),
        run_hash=run_hash,
        a3_batch_id=a3.batch_id,
        r2_run_id=r2.run_id,
        r2_run_hash=r2.run_hash,
        trading_date=r2.trading_date,
        built_at=at,
        eligible_count=eligible,
        scanned_count=scanned,
        excluded_count=excluded,
        failed_count=failed,
        unattempted_count=unattempted,
        completeness=completeness,
        completeness_threshold=completeness_threshold,
        wait_partial_scan=partial,
        layer_status=layer_status,
        rows=tuple(rows),
        warnings=(
            "S3 tags are cheap research context, not independent votes or win probability.",
            "Delivery/MTO is intentionally excluded from S3.",
        ),
    )


def build_s3_watch_queue(batch: S3CheapDiscoveryBatchV1, *, limit: int = 50) -> S3WatchQueueV1:
    if limit < 1:
        raise ValueError("S3 watch limit must be positive")
    watch = sorted(
        (
            row
            for row in batch.rows
            if row.public_state is SelectionState.WATCH
            and row.research_state is SelectionState.WATCH
        ),
        key=lambda row: (
            -(row.attention_priority if row.attention_priority is not None else -1.0),
            row.symbol,
        ),
    )
    return S3WatchQueueV1(
        source_run_id=batch.run_id,
        source_run_hash=batch.run_hash,
        built_at=batch.built_at,
        completeness=batch.completeness,
        wait_partial_scan=batch.wait_partial_scan,
        limit=limit,
        total_watch_count=len(watch),
        rows=tuple(watch[:limit]),
    )
