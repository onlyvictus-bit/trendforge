from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, model_validator

from ..source_contracts import SourceResult, SourceResultState, SourceRole
from .contracts import (
    BarIdentity,
    DataMode,
    EvidenceDirection,
    EvidenceFamily,
    GateOutcome,
    InstrumentIdentity,
    MODEL_CONFIG,
    SelectionGateResult,
    SelectionState,
    StateCeiling,
)
from .resolver import EvidenceResolution, ResolutionProfile, resolve_evidence
from .structure import (
    ClosedBar,
    StructureAnalysis,
    StructureMetrics,
    StructureProfile,
    analyze_closed_bar_structure,
)


IST = timezone(timedelta(hours=5, minutes=30))
R3_AS_OF = datetime(2026, 7, 19, 9, 0, tzinfo=IST)
R3_DATA_DATE = date(2026, 7, 17)

R3_RESOLUTION_PROFILE = ResolutionProfile(
    profile_id="PRF-Q5-R3-EOD-SWING",
    profile_version="1.0.0",
    family_weights={
        EvidenceFamily.STRUCTURE: 0.60,
        EvidenceFamily.PARTICIPATION: 0.40,
    },
    required_families=(
        EvidenceFamily.STRUCTURE,
        EvidenceFamily.PARTICIPATION,
    ),
    required_source_ids=("SRC-NSE-EOD",),
    min_completeness=1.0,
    state_ceiling=StateCeiling.CONFIRMED,
    allowed_data_modes=(DataMode.EOD_RESEARCH,),
)

R3_STRUCTURE_PROFILE = StructureProfile(
    profile_id="STR-Q5-R3-BREAKOUT-RVOL",
    profile_version="1.0.0",
    direction=EvidenceDirection.BULLISH,
    prior_range_bars=5,
    acceptance_bars=1,
    tolerance_bps=10,
    volume_baseline_bars=5,
    min_rvol=1.5,
    nr_window=7,
    session_calendar_version="NSE-CM-2026-V1",
)


class Q5R3Decision(BaseModel):
    model_config = MODEL_CONFIG

    instrument: InstrumentIdentity
    state: SelectionState
    state_ceiling: StateCeiling
    evidence_direction: EvidenceDirection
    data_mode: DataMode
    evidence_strength: float
    reason: str
    gate_results: tuple[SelectionGateResult, ...]
    metrics: StructureMetrics
    selected_claim_ids: tuple[str, ...]
    fixture_only: Literal[True] = True
    production_authorized: Literal[False] = False
    research_priority_only: Literal[True] = True
    executable: Literal[False] = False

    @model_validator(mode="after")
    def enforce_research_boundary(self) -> "Q5R3Decision":
        if self.state is SelectionState.CONFIRMED:
            if self.data_mode is not DataMode.EOD_RESEARCH:
                raise ValueError("Q5-R3 CONFIRMED is EOD_RESEARCH only")
            if self.state_ceiling is not StateCeiling.CONFIRMED:
                raise ValueError("CONFIRMED exceeds state ceiling")
        if self.state is SelectionState.REJECT and not any(
            gate.outcome is GateOutcome.REJECT for gate in self.gate_results
        ):
            raise ValueError("REJECT requires a deterministic veto")
        return self


class Q5R3FixtureBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: Literal["Q5-R3"] = "Q5-R3"
    acceptance_ceiling: Literal["EOD_CLOSED_BAR_RESEARCH_ONLY"] = (
        "EOD_CLOSED_BAR_RESEARCH_ONLY"
    )
    fixture_only: Literal[True] = True
    production_authorized: Literal[False] = False
    executable: Literal[False] = False
    resolution_profile: ResolutionProfile
    structure_profile: StructureProfile
    source_results: tuple[SourceResult, ...]
    analyses: tuple[StructureAnalysis, ...]
    resolutions: tuple[EvidenceResolution, ...]
    decisions: tuple[Q5R3Decision, ...]

    @model_validator(mode="after")
    def enforce_r3_acceptance_contract(self) -> "Q5R3FixtureBatch":
        states = {decision.state for decision in self.decisions}
        if states != set(SelectionState):
            raise ValueError("Q5-R3 fixtures must cover all four public states")
        if not any(
            decision.state is SelectionState.CONFIRMED for decision in self.decisions
        ):
            raise ValueError("Q5-R3 requires one observed EOD confirmation")
        return self


def _digest(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


def _instrument(symbol: str) -> InstrumentIdentity:
    return InstrumentIdentity.create(
        exchange="NSE",
        segment="EQUITY",
        symbol=symbol,
        isin=f"INE{_digest(symbol)[:7].upper()}01010",
        series="EQ",
        tick_size=0.05,
    )


def _source_result() -> SourceResult:
    return SourceResult(
        source_id="SRC-NSE-EOD",
        contract_version="1.0.0",
        role=SourceRole.OFFICIAL_GATE,
        state=SourceResultState.STRUCTURED_OK,
        record_count=45,
        data_date=R3_DATA_DATE,
        published_at=datetime(2026, 7, 17, 17, 45, tzinfo=IST),
        received_at=datetime(2026, 7, 17, 18, 0, 1, tzinfo=IST),
        available_at=datetime(2026, 7, 17, 18, 0, tzinfo=IST),
        retrieved_at=datetime(2026, 7, 17, 18, 0, 2, tzinfo=IST),
        schema_version="q5-r3-fixture-schema-1",
        parser_version="q5-r3-fixture-parser-1",
        revision_id="q5-r3-fixture-1",
        artifact_hash=_digest("q5-r3-eod-bars"),
        freshness="FRESH",
        can_support_confirmed=True,
        state_ceiling="CONFIRMED",
    )


def build_fixture_bars(
    instrument: InstrumentIdentity,
    *,
    scenario: Literal[
        "BREAKOUT",
        "UNCLOSED",
        "WEAK_PARTICIPATION",
        "COMPRESSION",
        "INVALIDATED",
    ],
    data_mode: DataMode = DataMode.EOD_RESEARCH,
    adjustment_version: str = "ADJ-2026-07-18-V1",
) -> tuple[ClosedBar, ...]:
    closes = [96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 106.0]
    widths = [2.0] * len(closes)
    volumes = [1000.0] * len(closes)

    if scenario == "COMPRESSION":
        closes = [100.0, 100.2, 100.1, 100.15, 100.10, 100.08, 100.06, 100.05, 100.04]
        widths = [3.0, 2.8, 2.5, 2.2, 1.8, 1.4, 1.0, 0.7, 0.4]
        volumes[-1] = 800.0
    elif scenario == "WEAK_PARTICIPATION":
        volumes[-1] = 1100.0
    else:
        volumes[-1] = 2000.0

    sessions = (
        date(2026, 7, 7),
        date(2026, 7, 8),
        date(2026, 7, 9),
        date(2026, 7, 10),
        date(2026, 7, 13),
        date(2026, 7, 14),
        date(2026, 7, 15),
        date(2026, 7, 16),
        date(2026, 7, 17),
    )
    bars: list[ClosedBar] = []
    for offset, (close, width, volume) in enumerate(
        zip(closes, widths, volumes, strict=True)
    ):
        session_date = sessions[offset]
        open_time = datetime.combine(
            session_date,
            datetime.min.time(),
            tzinfo=IST,
        ).replace(hour=9, minute=15)
        close_time = open_time.replace(hour=15, minute=30)
        open_price = close - 0.2
        high = max(open_price, close) + width / 2
        low = min(open_price, close) - width / 2
        identity = BarIdentity.create(
            instrument_id=instrument.instrument_id,
            timeframe="1d",
            session_id=session_date.isoformat(),
            open_time=open_time,
            close_time=close_time,
            is_closed=not (scenario == "UNCLOSED" and offset == len(closes) - 1),
            adjustment_version=adjustment_version,
            raw_hash=_digest(f"{instrument.symbol}-{scenario}-{offset}"),
            source_mode=data_mode,
        )
        bars.append(
            ClosedBar(
                identity=identity,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return tuple(bars)


def _reason(resolution: EvidenceResolution) -> str:
    if resolution.state is SelectionState.CONFIRMED:
        return (
            "Closed EOD breakout and independent completed-bar RVOL passed; "
            "research priority only."
        )
    return resolution.reason


def build_q5_r3_fixture_batch() -> Q5R3FixtureBatch:
    source_result = _source_result()
    scenarios = (
        ("TF_R3_CONFIRMED", "BREAKOUT", False, False),
        ("TF_R3_WAIT_OPEN", "UNCLOSED", False, False),
        ("TF_R3_WAIT_RVOL", "WEAK_PARTICIPATION", False, False),
        ("TF_R3_WATCH_NR7", "COMPRESSION", False, True),
        ("TF_R3_REJECT", "INVALIDATED", True, False),
    )
    analyses: list[StructureAnalysis] = []
    resolutions: list[EvidenceResolution] = []
    decisions: list[Q5R3Decision] = []

    for symbol, scenario, invalidated, discovery_only in scenarios:
        instrument = _instrument(symbol)
        bars = build_fixture_bars(instrument, scenario=scenario)
        analysis = analyze_closed_bar_structure(
            instrument=instrument,
            bars=bars,
            source_result=source_result,
            profile=R3_STRUCTURE_PROFILE,
            decision_at=R3_AS_OF,
            hard_invalidation=invalidated,
        )
        resolution = resolve_evidence(
            profile=R3_RESOLUTION_PROFILE,
            decision_at=R3_AS_OF,
            evidence_direction=R3_STRUCTURE_PROFILE.direction,
            claims=analysis.claims,
            facts=(analysis.fact,),
            source_results=(source_result,),
            completeness=1.0,
            existing_gates=analysis.gate_results,
            discovery_only=discovery_only,
            data_mode=bars[-1].identity.source_mode,
        )
        analyses.append(analysis)
        resolutions.append(resolution)
        decisions.append(
            Q5R3Decision(
                instrument=instrument,
                state=resolution.state,
                state_ceiling=resolution.state_ceiling,
                evidence_direction=resolution.evidence_direction,
                data_mode=bars[-1].identity.source_mode,
                evidence_strength=resolution.evidence_strength,
                reason=_reason(resolution),
                gate_results=resolution.gate_results,
                metrics=analysis.metrics,
                selected_claim_ids=resolution.selected_claim_ids,
            )
        )

    return Q5R3FixtureBatch(
        resolution_profile=R3_RESOLUTION_PROFILE,
        structure_profile=R3_STRUCTURE_PROFILE,
        source_results=(source_result,),
        analyses=tuple(analyses),
        resolutions=tuple(resolutions),
        decisions=tuple(decisions),
    )
