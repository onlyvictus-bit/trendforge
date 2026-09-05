from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .institutional_sources import (
    EndpointFetchResult,
    FetchState,
    MACRO_EVENT_ENDPOINTS,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT_DIR / "data" / "trendforge_research.db"
USABLE_FETCH_STATES = {FetchState.RAW_ARCHIVED, FetchState.NO_DATA_NOW}


SOURCE_USE: dict[str, tuple[str, str, str]] = {
    "usda_wasde": (
        "AGRI_REGIME",
        "Global crop supply context for sugar, wheat, corn, oilseed, fertilizer and agrochem stocks.",
        "Schema parser pending; use only as delayed research context.",
    ),
    "dgcis_trade_data": (
        "INDIA_TRADE_FLOW",
        "Commodity import/export trend context for gold, oil, chemicals, refiners, autos and rural demand.",
        "TRADESTAT is form-driven; raw page/archive cannot score until a stable data contract is parsed.",
    ),
    "imd_rainfall_timeseries": (
        "MONSOON_REGIME",
        "Rainfall deviation context for agri, fertilizer, rural FMCG, sugar and irrigation-linked stocks.",
        "District and subdivision tables must be parsed before scoring.",
    ),
    "des_crop_estimates": (
        "CROP_SUPPLY",
        "Advance crop-estimate context for acreage and production deltas.",
        "PDF/document discovery only until table extraction is fixture-tested.",
    ),
    "shfe_weekly_stock": (
        "CHINA_METALS_INVENTORY",
        "SHFE stock changes for copper, aluminium and zinc base-metal regime.",
        "Weekly China inventory context only; not a standalone MCX or stock trigger.",
    ),
    "china_nbs_indicator": (
        "CHINA_MACRO_REGIME",
        "China PMI/manufacturing indicator context for metals, chemicals and global cyclicals.",
        "Indicator code mapping and seasonal interpretation must be versioned before scoring.",
    ),
    "mcx_future_prices": (
        "MCX_DISTORTION_GUARD",
        "Commodity futures price context for abnormal price or expiry distortion veto.",
        "Public contract remains research-only until MCX session and contract identity are verified.",
    ),
    "mcx_trading_holidays": (
        "MCX_SESSION_GUARD",
        "MCX holiday guard to avoid stale commodity scans on closed sessions.",
        "Can guard schedule after date parser is verified; does not create signal.",
    ),
    "mcx_circulars": (
        "MCX_RULE_CHANGE",
        "Margin, lot-size, expiry, delivery and contract rule-change alerts.",
        "Use as execution-risk warning only until circular categories are parsed.",
    ),
    "fbil_usdinr_reference": (
        "FX_PARITY",
        "USD/INR reference rate for MCX gold parity and currency-leg confirmation.",
        "HTML page must be parsed to a dated USD/INR row before parity calculations.",
    ),
    "bse_xbrl_announcements": (
        "MATERIAL_EVENT",
        "BSE structured material events and XBRL announcement discovery.",
        "Event taxonomy and scrip mapping are required before G12 use.",
    ),
    "nse_xbrl_taxonomy": (
        "DISCLOSURE_SCHEMA",
        "NSE XBRL taxonomy reference used to parse corporate filings consistently.",
        "Reference/schema source only; cannot score directly.",
    ),
    "nse_pit_annual": (
        "INSIDER_HISTORY",
        "Annual PIT history for promoter, KMP and insider behavior scoring.",
        "Historical behavior context only; current PIT source still controls live evidence.",
    ),
    "nse_shareholding_pattern": (
        "OWNERSHIP_TREND",
        "Promoter, FII, DII and public holding trend context.",
        "Quarterly lagged context only; never intraday institutional buying proof.",
    ),
    "mca_company_master_data": (
        "COMPANY_IDENTITY_RISK",
        "MCA company master-data, CIN, status and charges discovery.",
        "Catalog/source discovery only until a resource CSV/API is selected and parsed.",
    ),
    "cdsl_fpi_fortnightly": (
        "FPI_FLOW_CONTEXT",
        "CDSL FPI fortnightly publication context for confirmed depository flow.",
        "Workbook link discovery and parser are pending.",
    ),
    "rbi_fpi_caution": (
        "FPI_LIMIT_HEADROOM",
        "RBI caution/breach context for foreign ownership headroom and demand constraints.",
        "Table parser pending; use as risk context after source-date validation.",
    ),
    "msei_fii_dii": (
        "INSTITUTIONAL_FLOW_CROSSCHECK",
        "MSEI FII/DII activity cross-check for combined exchange cash-flow context.",
        "Download resolver and schema parser are pending.",
    ),
    "cftc_legacy_futures_only": (
        "COT_REGIME_REFERENCE",
        "CFTC legacy futures-only positioning rows for commodity regime cross-checks.",
        "Research-only cross-check; TrendForge primary COT parser remains the official disaggregated file contract.",
    ),
    "cftc_disagg_futures_only": (
        "COT_COMMODITY_REGIME",
        "CFTC disaggregated futures-only positioning rows for gold, crude and base-metal regime context.",
        "Weekly delayed context only; cannot prove intraday commodity flow or unlock READY alone.",
    ),
    "cftc_tff_futures_only": (
        "COT_FINANCIAL_REGIME",
        "CFTC traders-in-financial-futures positioning rows for cross-market risk context.",
        "Financial-futures COT is broad regime context, not symbol-level stock evidence.",
    ),
    "cftc_release_schedule": (
        "COT_RELEASE_GUARD",
        "CFTC release schedule for COT freshness and blackout windows.",
        "Schedule parser pending; does not replace COT position parser.",
    ),
    "eia_petroleum_schedule": (
        "CRUDE_EVENT_BLACKOUT",
        "EIA petroleum release schedule for crude event blackout windows.",
        "Schedule parser pending; crude trade signals still require EIA data and price confirmation.",
    ),
}


class MacroEventModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class MacroEventSource(MacroEventModel):
    endpoint_key: str
    fetch_state: str
    scanner_use: str
    purpose: str
    limitation: str
    fetched_at: datetime
    record_count: int = Field(ge=0)
    content_hash: str | None = None
    raw_path: str | None = None
    from_cache: bool = False
    can_unlock_ready: bool = False
    reason: str | None = None


class MacroEventContextSnapshot(MacroEventModel):
    run_id: str
    fetched_at: datetime
    state: Literal["RESEARCH_ONLY", "WAIT_PARTIAL_SOURCE", "WAIT_SOURCE", "WAIT_NO_SNAPSHOT"]
    source_completeness: float = Field(ge=0, le=1)
    sources: list[MacroEventSource] = Field(default_factory=list)
    missing_source_keys: list[str] = Field(default_factory=list)
    can_unlock_ready: bool = False
    required_confirmations: list[str] = Field(default_factory=list)
    reason: str


def build_macro_event_context_snapshot(
    results: list[EndpointFetchResult],
) -> MacroEventContextSnapshot:
    by_key = {result.endpoint_key: result for result in results}
    sources: list[MacroEventSource] = []
    for endpoint_key in MACRO_EVENT_ENDPOINTS:
        result = by_key.get(endpoint_key)
        scanner_use, purpose, limitation = SOURCE_USE[endpoint_key]
        if result is None:
            continue
        sources.append(
            MacroEventSource(
                endpoint_key=endpoint_key,
                fetch_state=result.state.value,
                scanner_use=scanner_use,
                purpose=purpose,
                limitation=limitation,
                fetched_at=result.fetched_at,
                record_count=result.record_count,
                content_hash=result.content_hash,
                raw_path=result.raw_path,
                from_cache=result.from_cache,
                can_unlock_ready=False,
                reason=result.reason,
            )
        )
    fresh = [
        source
        for source in sources
        if FetchState(source.fetch_state) in USABLE_FETCH_STATES
    ]
    completeness = len(fresh) / len(MACRO_EVENT_ENDPOINTS)
    missing = [
        key
        for key in MACRO_EVENT_ENDPOINTS
        if key not in by_key or by_key[key].state not in USABLE_FETCH_STATES
    ]
    state: Literal["RESEARCH_ONLY", "WAIT_PARTIAL_SOURCE", "WAIT_SOURCE"]
    if not fresh:
        state = "WAIT_SOURCE"
    elif completeness < 1:
        state = "WAIT_PARTIAL_SOURCE"
    else:
        state = "RESEARCH_ONLY"
    return MacroEventContextSnapshot(
        run_id=str(uuid4()),
        fetched_at=max((result.fetched_at for result in results), default=datetime.now(UTC)),
        state=state,
        source_completeness=round(completeness, 4),
        sources=sources,
        missing_source_keys=missing,
        can_unlock_ready=False,
        required_confirmations=[
            "Source-specific parser with data_date and freshness policy",
            "Symbol or commodity mapping before stock-level score impact",
            "Price, volume, VWAP, OI/MWPL or basis confirmation before candidate READY",
            "Risk and safety gates must pass independently",
        ],
        reason=(
            "Macro, agri, China, MCX operational and regulatory sources are research context only. They can veto, downgrade or explain candidates after structured parsers exist, but cannot unlock READY alone."
        ),
    )


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS macro_event_context_runs (
            run_id TEXT PRIMARY KEY,
            fetched_at TEXT NOT NULL,
            state TEXT NOT NULL,
            source_completeness REAL NOT NULL,
            source_count INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_macro_event_context_latest
        ON macro_event_context_runs(fetched_at DESC);
        """
    )


def save_macro_event_context_snapshot(
    snapshot: MacroEventContextSnapshot, db_path: Path = DEFAULT_DB
) -> None:
    payload = snapshot.model_dump(mode="json", by_alias=True)
    with _connect(db_path) as connection:
        _initialize(connection)
        connection.execute(
            """
            INSERT OR REPLACE INTO macro_event_context_runs(
                run_id, fetched_at, state, source_completeness, source_count, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.run_id,
                snapshot.fetched_at.isoformat(),
                snapshot.state,
                snapshot.source_completeness,
                len(snapshot.sources),
                json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
            ),
        )


def latest_macro_event_context_snapshot(
    db_path: Path = DEFAULT_DB,
) -> MacroEventContextSnapshot:
    with _connect(db_path) as connection:
        _initialize(connection)
        row = connection.execute(
            """
            SELECT payload_json FROM macro_event_context_runs
            ORDER BY fetched_at DESC LIMIT 1
            """
        ).fetchone()
    if row is None:
        return MacroEventContextSnapshot(
            run_id="NO_SNAPSHOT",
            fetched_at=datetime.now(UTC),
            state="WAIT_NO_SNAPSHOT",
            source_completeness=0,
            sources=[],
            missing_source_keys=list(MACRO_EVENT_ENDPOINTS),
            can_unlock_ready=False,
            required_confirmations=[
                "Run POST /api/institutional/macro-event-sources/fetch before using macro context.",
            ],
            reason="No macro event context snapshot has been saved yet.",
        )
    return MacroEventContextSnapshot.model_validate_json(row["payload_json"])
