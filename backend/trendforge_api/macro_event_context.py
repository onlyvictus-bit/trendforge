from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
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


class EventClearanceOutcome(StrEnum):
    CLEAR = "CLEAR"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class EventClearanceEvidence(MacroEventModel):
    """Parsed, lineage-backed event evidence scoped to one strategy/instrument."""

    evidence_id: str = Field(min_length=1)
    source_key: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    event_window_start: datetime
    event_window_end: datetime
    assessed_at: datetime
    valid_until: datetime
    semantic_coverage_complete: bool = False
    source_outcome: EventClearanceOutcome
    parser_version: str | None = None
    content_hash: str | None = None
    event_id: str | None = None

    @model_validator(mode="after")
    def validate_evidence_window(self) -> "EventClearanceEvidence":
        for field_name in (
            "event_window_start",
            "event_window_end",
            "assessed_at",
            "valid_until",
        ):
            value = getattr(self, field_name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        if self.event_window_end < self.event_window_start:
            raise ValueError("event window end cannot precede start")
        return self


class EventClearanceResult(MacroEventModel):
    """Fail-closed semantic clearance consumed by S7; never transport state."""

    instrument_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    decision_at: datetime
    outcome: EventClearanceOutcome
    evidence_ids: tuple[str, ...] = ()
    source_keys: tuple[str, ...] = ()
    blocking_event_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    semantic_coverage_complete: bool = False
    assessed_at: datetime | None = None
    valid_until: datetime | None = None
    event_window_start: datetime | None = None
    event_window_end: datetime | None = None
    can_satisfy_mandatory_gate: bool = False

    @model_validator(mode="after")
    def validate_clearance(self) -> "EventClearanceResult":
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise ValueError("decision_at must be timezone-aware")
        for field_name in (
            "assessed_at",
            "valid_until",
            "event_window_start",
            "event_window_end",
        ):
            value = getattr(self, field_name)
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{field_name} must be timezone-aware")
        temporal_clear = (
            self.assessed_at is not None
            and self.valid_until is not None
            and self.event_window_start is not None
            and self.event_window_end is not None
            and self.assessed_at <= self.decision_at <= self.valid_until
            and self.event_window_start <= self.decision_at <= self.event_window_end
        )
        may_clear = (
            self.outcome is EventClearanceOutcome.CLEAR
            and self.semantic_coverage_complete
            and bool(self.evidence_ids)
            and bool(self.source_keys)
            and not self.blocking_event_ids
            and temporal_clear
        )
        if self.can_satisfy_mandatory_gate != may_clear:
            raise ValueError("only current, complete, lineage-backed CLEAR may satisfy the mandatory event gate")
        return self


def _unknown_event_clearance(
    *,
    instrument_id: str,
    symbol: str,
    profile_id: str,
    profile_version: str,
    decision_at: datetime,
    reason_codes: tuple[str, ...],
    evidence: tuple[EventClearanceEvidence, ...] = (),
) -> EventClearanceResult:
    return EventClearanceResult(
        instrument_id=instrument_id,
        symbol=symbol.upper(),
        profile_id=profile_id,
        profile_version=profile_version,
        decision_at=decision_at,
        outcome=EventClearanceOutcome.UNKNOWN,
        evidence_ids=tuple(item.evidence_id for item in evidence),
        source_keys=tuple(dict.fromkeys(item.source_key for item in evidence)),
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        semantic_coverage_complete=False,
        assessed_at=max(item.assessed_at for item in evidence) if evidence else None,
        valid_until=min(item.valid_until for item in evidence) if evidence else None,
        event_window_start=(
            max(item.event_window_start for item in evidence) if evidence else None
        ),
        event_window_end=(
            min(item.event_window_end for item in evidence) if evidence else None
        ),
        can_satisfy_mandatory_gate=False,
    )


def evaluate_event_clearance(
    *,
    instrument_id: str,
    symbol: str,
    profile_id: str,
    profile_version: str,
    decision_at: datetime,
    evidence: tuple[EventClearanceEvidence, ...] | list[EventClearanceEvidence],
) -> EventClearanceResult:
    """Evaluate exact-scope parsed event evidence; collection health is irrelevant."""
    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise ValueError("decision_at must be timezone-aware")
    scoped = tuple(
        item
        for item in evidence
        if item.instrument_id == instrument_id
        and item.symbol.upper() == symbol.upper()
        and item.profile_id == profile_id
        and item.profile_version == profile_version
    )
    if not scoped:
        return _unknown_event_clearance(
            instrument_id=instrument_id,
            symbol=symbol,
            profile_id=profile_id,
            profile_version=profile_version,
            decision_at=decision_at,
            reason_codes=("WAIT_EVENT_CLEARANCE_NO_SCOPED_EVIDENCE",),
        )

    invalid_reasons: list[str] = []
    valid: list[EventClearanceEvidence] = []
    for item in scoped:
        if item.assessed_at > decision_at:
            invalid_reasons.append("WAIT_EVENT_CLEARANCE_FUTURE_EVIDENCE")
            continue
        if item.valid_until < decision_at:
            invalid_reasons.append("WAIT_EVENT_CLEARANCE_EXPIRED")
            continue
        if not (item.event_window_start <= decision_at <= item.event_window_end):
            invalid_reasons.append("WAIT_EVENT_CLEARANCE_WINDOW_MISS")
            continue
        if (
            not item.semantic_coverage_complete
            or not item.parser_version
            or not item.content_hash
        ):
            invalid_reasons.append("WAIT_EVENT_CLEARANCE_INCOMPLETE_COVERAGE")
            continue
        valid.append(item)

    valid_outcomes = {item.source_outcome for item in valid}
    if {EventClearanceOutcome.CLEAR, EventClearanceOutcome.BLOCKED} <= valid_outcomes:
        return _unknown_event_clearance(
            instrument_id=instrument_id,
            symbol=symbol,
            profile_id=profile_id,
            profile_version=profile_version,
            decision_at=decision_at,
            reason_codes=("WAIT_EVENT_CLEARANCE_CONTRADICTORY",),
            evidence=scoped,
        )

    blockers = tuple(
        item for item in valid if item.source_outcome is EventClearanceOutcome.BLOCKED
    )
    if blockers:
        return EventClearanceResult(
            instrument_id=instrument_id,
            symbol=symbol.upper(),
            profile_id=profile_id,
            profile_version=profile_version,
            decision_at=decision_at,
            outcome=EventClearanceOutcome.BLOCKED,
            evidence_ids=tuple(item.evidence_id for item in valid),
            source_keys=tuple(dict.fromkeys(item.source_key for item in valid)),
            blocking_event_ids=tuple(
                dict.fromkeys(
                    item.event_id for item in blockers if item.event_id is not None
                )
            ),
            reason_codes=("WAIT_EVENT_BLACKOUT_BLOCKED",),
            semantic_coverage_complete=True,
            assessed_at=max(item.assessed_at for item in valid),
            valid_until=min(item.valid_until for item in valid),
            event_window_start=max(item.event_window_start for item in valid),
            event_window_end=min(item.event_window_end for item in valid),
            can_satisfy_mandatory_gate=False,
        )

    if invalid_reasons or not valid:
        return _unknown_event_clearance(
            instrument_id=instrument_id,
            symbol=symbol,
            profile_id=profile_id,
            profile_version=profile_version,
            decision_at=decision_at,
            reason_codes=tuple(invalid_reasons) or ("WAIT_EVENT_CLEARANCE_UNKNOWN",),
            evidence=scoped,
        )

    if all(item.source_outcome is EventClearanceOutcome.CLEAR for item in valid):
        return EventClearanceResult(
            instrument_id=instrument_id,
            symbol=symbol.upper(),
            profile_id=profile_id,
            profile_version=profile_version,
            decision_at=decision_at,
            outcome=EventClearanceOutcome.CLEAR,
            evidence_ids=tuple(item.evidence_id for item in valid),
            source_keys=tuple(dict.fromkeys(item.source_key for item in valid)),
            reason_codes=("EVENT_CLEARANCE_CLEAR",),
            semantic_coverage_complete=True,
            assessed_at=max(item.assessed_at for item in valid),
            valid_until=min(item.valid_until for item in valid),
            event_window_start=max(item.event_window_start for item in valid),
            event_window_end=min(item.event_window_end for item in valid),
            can_satisfy_mandatory_gate=True,
        )

    return _unknown_event_clearance(
        instrument_id=instrument_id,
        symbol=symbol,
        profile_id=profile_id,
        profile_version=profile_version,
        decision_at=decision_at,
        reason_codes=("WAIT_EVENT_CLEARANCE_UNKNOWN",),
        evidence=scoped,
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
    from .read_snapshot import borrow_connection
    borrowed = borrow_connection(db_path)
    if borrowed is not None:
        return borrowed
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
    from .read_snapshot import borrow_connection
    with _connect(db_path) as connection:
        if borrow_connection(db_path) is None:
            _initialize(connection)
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='macro_event_context_runs'"
        ).fetchone()
        row = connection.execute(
            """
            SELECT payload_json FROM macro_event_context_runs
            ORDER BY fetched_at DESC LIMIT 1
            """
        ).fetchone() if exists else None
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
