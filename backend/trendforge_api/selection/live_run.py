"""R1 on-demand WAIT projection from latest stored scanner symbols.

This is not a persisted decision record. No new table. No quantity.
No live CONFIRMED.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable, Literal

from pydantic import BaseModel, Field

from ..source_inventory_compiler import compile_default_inventory
from .contracts import (
    MODEL_CONFIG,
    DataMode,
    EvidenceDirection,
    EvidenceFamily,
    GateOutcome,
    InstrumentIdentity,
    SelectionCandidate,
    SelectionGateResult,
    SelectionScanRun,
    SelectionState,
    StateCeiling,
    stable_id,
)
from .transitions import apply_selection_transition


class LiveSelectionBatch(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = "trendforge.legacy-selection-live.v1"
    legacy_projection: bool = True
    milestone: str = "R1-LIVE"
    acceptance_ceiling: str = "NO_LIVE_CONFIRMED"
    compiled_at: datetime
    workbook_sha256: str | None = None
    row_count: int = Field(ge=0)
    endpoint_count: int = Field(ge=0)
    contract_count: int = Field(ge=0)
    h1a0_passed: int = Field(ge=0)
    h1a0_total: int = Field(ge=0)
    source_activation_ready: bool = False
    gate_authorized_source_key_count: int = 0
    live_confirmed_count: int = 0
    persisted: bool = False
    storage: Literal["NONE", "STORED"] = "NONE"
    run: SelectionScanRun
    candidates: tuple[SelectionCandidate, ...] = ()


def _attention_symbols() -> list[str]:
    try:
        from ..storage import list_scanner_candidates, list_scanner_runs
    except Exception:
        return []
    runs = list_scanner_runs(limit=1)
    if not runs:
        return []
    run_id = runs[0].get("run_id")
    if not run_id:
        return []
    rows = list_scanner_candidates(run_id)
    seen: list[str] = []
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if symbol and symbol not in seen:
            seen.append(symbol)
    return seen


def build_live_selection_run(
    *,
    symbols: Iterable[str] | None = None,
    as_of: datetime | None = None,
) -> LiveSelectionBatch:
    now = as_of or datetime.now(UTC)
    report = compile_default_inventory()
    names = [item.strip().upper() for item in (symbols or _attention_symbols()) if item]
    unique: list[str] = []
    for name in names:
        if name not in unique:
            unique.append(name)
    unique = unique[:50]
    run = SelectionScanRun.create(
        profile_id="PRF-R1-LIVE",
        profile_version="1",
        as_of=now,
        universe_version=report.workbook_sha256 or "NO_WORKBOOK",
        data_mode=DataMode.EOD_RESEARCH,
        eligible_count=len(unique),
        scanned_count=len(unique),
    )
    candidates: list[SelectionCandidate] = []
    for symbol in unique:
        instrument = InstrumentIdentity.create(
            exchange="NSE",
            segment="EQ",
            symbol=symbol,
            series="EQ",
        )
        resulting, accepted, decision = apply_selection_transition(
            SelectionState.WAIT,
            SelectionState.CONFIRMED,
            source_activation_ready=report.source_activation_ready,
            closed_structure_accepted=False,
        )
        gate = SelectionGateResult(
            code="WAIT_SOURCE_ACTIVATION",
            outcome=GateOutcome.WAIT,
            blocks_confirmed=True,
            reason=(
                "Live confirmation is blocked until sourceActivationReady and "
                f"closed-bar structure are proven ({decision.value})."
            ),
        )
        candidates.append(
            SelectionCandidate(
                candidate_id=stable_id("cand", run.run_id, instrument.instrument_id),
                run_id=run.run_id,
                instrument=instrument,
                market="NSE",
                profile_id=run.profile_id,
                profile_version=run.profile_version,
                timeframe="1d",
                state=resulting,
                state_ceiling=StateCeiling.WAIT,
                evidence_direction=EvidenceDirection.UNKNOWN,
                discovery_reason=(
                    f"{symbol} is visible as research attention only. "
                    "Legacy scanner rank cannot set public state."
                ),
                family_missing=(EvidenceFamily.STRUCTURE,),
                top_reason="WAIT_SOURCE_ACTIVATION",
                missing_proof=("SOURCE_ACTIVATION", "CLOSED_BAR_STRUCTURE"),
                next_confirmation=(
                    "Named source activation plus accepted closed-bar structure."
                ),
                invalidation_condition=(
                    "Hard veto, stale required family, or denied transition."
                ),
                context="R1 on-demand WAIT projection. Quantity and execution are absent.",
                freshness="UNKNOWN",
                completeness=0.0,
                what_changed="NO_BASELINE",
                evidence_strength=0.0,
                gate_results=(gate,),
                source_ages_seconds={},
                data_mode=run.data_mode,
                demo_only=False,
                executable=False,
                comparable_baseline="NO_BASELINE",
            )
        )
        if accepted:
            raise RuntimeError("live R1 path cannot accept CONFIRMED")
    live_confirmed = sum(
        1 for item in candidates if item.state is SelectionState.CONFIRMED
    )
    return LiveSelectionBatch(
        compiled_at=now,
        workbook_sha256=report.workbook_sha256,
        row_count=report.row_count,
        endpoint_count=report.normalized_endpoint_count,
        contract_count=report.normalized_source_contract_count,
        h1a0_passed=report.h1a0_acceptance_passed,
        h1a0_total=report.h1a0_acceptance_total,
        source_activation_ready=report.source_activation_ready,
        gate_authorized_source_key_count=report.gate_authorized_source_key_count,
        live_confirmed_count=live_confirmed,
        run=run,
        candidates=tuple(candidates),
    )
