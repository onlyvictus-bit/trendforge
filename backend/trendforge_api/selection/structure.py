from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from math import isfinite

from pydantic import BaseModel, Field, field_validator, model_validator

from ..source_contracts import SourceResult, SourceResultState
from .contracts import (
    BarIdentity,
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    GateOutcome,
    InstrumentIdentity,
    MODEL_CONFIG,
    NormalizedFact,
    PointInTimeLineage,
    SelectionGateResult,
    StateCeiling,
)


class ClosedBar(BaseModel):
    """Validated adjusted OHLCV bar with canonical point-in-time identity."""

    model_config = MODEL_CONFIG

    identity: BarIdentity
    open: float
    high: float
    low: float
    close: float
    volume: float = Field(ge=0)

    @field_validator("open", "high", "low", "close", "volume")
    @classmethod
    def require_finite_number(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("bar values must be finite")
        return value

    @model_validator(mode="after")
    def validate_ohlc(self) -> "ClosedBar":
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high must contain open, low and close")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low must contain open, high and close")
        return self


class StructureProfile(BaseModel):
    """Versioned deterministic FTR-005/006/007/017 parameters."""

    model_config = MODEL_CONFIG

    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    direction: EvidenceDirection
    prior_range_bars: int = Field(default=5, ge=2, le=100)
    acceptance_bars: int = Field(default=1, ge=1, le=5)
    tolerance_bps: float = Field(default=0, ge=0, le=500)
    volume_baseline_bars: int = Field(default=5, ge=2, le=100)
    min_rvol: float = Field(default=1.5, gt=0, le=20)
    nr_window: int = Field(default=7, ge=4, le=30)
    session_calendar_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_directional_profile(self) -> "StructureProfile":
        if self.direction not in {
            EvidenceDirection.BULLISH,
            EvidenceDirection.BEARISH,
        }:
            raise ValueError("structure profile must be bullish or bearish")
        return self


class StructureMetrics(BaseModel):
    model_config = MODEL_CONFIG

    reference_level: float | None = None
    acceptance_threshold: float | None = None
    accepted: bool = False
    relative_volume: float | None = None
    volume_baseline: float | None = None
    narrow_range: bool | None = None
    current_true_range: float | None = None
    reference_bar_ids: tuple[str, ...] = ()
    acceptance_bar_ids: tuple[str, ...] = ()
    volume_baseline_bar_ids: tuple[str, ...] = ()
    nr_bar_ids: tuple[str, ...] = ()


class StructureAnalysis(BaseModel):
    model_config = MODEL_CONFIG

    profile: StructureProfile
    instrument: InstrumentIdentity
    fact: NormalizedFact
    claims: tuple[EvidenceClaim, ...]
    gate_results: tuple[SelectionGateResult, ...]
    metrics: StructureMetrics

    @model_validator(mode="after")
    def enforce_closed_bar_claims(self) -> "StructureAnalysis":
        if any(
            claim.can_support_confirmed
            and claim.state_ceiling is not StateCeiling.CONFIRMED
            for claim in self.claims
        ):
            raise ValueError("confirming structure claims need CONFIRMED ceiling")
        return self


def _gate(
    code: str,
    outcome: GateOutcome,
    reason: str,
    *,
    required: bool = True,
) -> SelectionGateResult:
    return SelectionGateResult(
        code=code,
        outcome=outcome,
        blocks_confirmed=(
            required
            and outcome in {GateOutcome.WAIT, GateOutcome.REJECT, GateOutcome.UNKNOWN}
        ),
        reason=reason,
        required=required,
    )


def _digest(*parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    return sha256(payload.encode("utf-8")).hexdigest()


def _true_range(current: ClosedBar, previous_close: float) -> float:
    return max(
        current.high - current.low,
        abs(current.high - previous_close),
        abs(current.low - previous_close),
    )


def _build_fact(
    *,
    instrument: InstrumentIdentity,
    source_result: SourceResult,
    profile: StructureProfile,
    bars: tuple[ClosedBar, ...],
    metrics: StructureMetrics,
    quality_state: str,
) -> NormalizedFact:
    latest = bars[-1]
    available_at = source_result.available_at
    lineage = PointInTimeLineage(
        event_time=latest.identity.close_time,
        published_at=source_result.published_at or available_at,
        available_at=available_at,
        received_at=source_result.received_at,
        retrieved_at=source_result.retrieved_at,
        revision_id=source_result.revision_id,
        artifact_hash=_digest(
            source_result.artifact_hash,
            profile.profile_id,
            profile.profile_version,
            *(bar.identity.bar_id for bar in bars),
        ),
    )
    return NormalizedFact.create(
        instrument_id=instrument.instrument_id,
        source_id=source_result.source_id,
        dataset_root="Q5_CLOSED_BAR_STRUCTURE",
        business_keys={
            "symbol": instrument.symbol,
            "close_time": latest.identity.close_time.isoformat(),
            "profile": profile.profile_id,
            "profile_version": profile.profile_version,
        },
        data_date=latest.identity.close_time.date(),
        lineage=lineage,
        quality_state=quality_state,
        payload={
            "metrics": metrics.model_dump(mode="json"),
            "bar_ids": [bar.identity.bar_id for bar in bars],
        },
    )


def analyze_closed_bar_structure(
    *,
    instrument: InstrumentIdentity,
    bars: tuple[ClosedBar, ...],
    source_result: SourceResult,
    profile: StructureProfile,
    decision_at: datetime,
    hard_invalidation: bool = False,
) -> StructureAnalysis:
    """Build native closed-bar claims without treating them as probabilities."""

    if not bars:
        raise ValueError("at least one bar is required")
    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise ValueError("decision_at must be timezone-aware")

    gates: list[SelectionGateResult] = []
    latest = bars[-1]
    bar_ids = [bar.identity.bar_id for bar in bars]
    session_ids = [bar.identity.session_id for bar in bars]
    identity_ok = all(
        bar.identity.instrument_id == instrument.instrument_id for bar in bars
    )
    timeframe_ok = len({bar.identity.timeframe for bar in bars}) == 1
    mode_ok = len({bar.identity.source_mode for bar in bars}) == 1
    adjustment_versions = {bar.identity.adjustment_version for bar in bars}
    chronological = all(
        left.identity.close_time < right.identity.close_time
        for left, right in zip(bars, bars[1:], strict=False)
    )

    if (
        not identity_ok
        or not timeframe_ok
        or not mode_ok
        or len(set(bar_ids)) != len(bar_ids)
        or len(set(session_ids)) != len(session_ids)
    ):
        gates.append(
            _gate(
                "WAIT_BAR_IDENTITY",
                GateOutcome.WAIT,
                (
                    "Bars must have one instrument, timeframe, data mode, "
                    "unique bar IDs and unique session IDs."
                ),
            )
        )
    if not chronological:
        gates.append(
            _gate(
                "WAIT_BAR_SEQUENCE",
                GateOutcome.WAIT,
                "Bars are not in a strict point-in-time sequence.",
            )
        )
    if not latest.identity.is_closed:
        gates.append(
            _gate(
                "WAIT_BAR_NOT_CLOSED",
                GateOutcome.WAIT,
                "The acceptance bar is not closed and cannot confirm structure.",
            )
        )
    if latest.identity.close_time > decision_at:
        gates.append(
            _gate(
                "WAIT_BAR_FUTURE",
                GateOutcome.WAIT,
                "The latest bar closes after the decision time.",
            )
        )
    if len(adjustment_versions) != 1 or any(
        value.strip().upper() in {"UNKNOWN", "UNRESOLVED"}
        for value in adjustment_versions
    ):
        gates.append(
            _gate(
                "WAIT_ADJUSTMENT_UNRESOLVED",
                GateOutcome.WAIT,
                "Corporate-action adjustment identity is unresolved or mixed.",
            )
        )
    if hard_invalidation:
        gates.append(
            _gate(
                "REJECT_STRUCTURE_INVALIDATED",
                GateOutcome.REJECT,
                "A deterministic structure invalidation condition was observed.",
            )
        )

    required_history = max(
        profile.prior_range_bars + profile.acceptance_bars,
        profile.volume_baseline_bars + 1,
    )
    if len(bars) < required_history:
        gates.append(
            _gate(
                "WAIT_INSUFFICIENT_HISTORY",
                GateOutcome.WAIT,
                (
                    f"Need {required_history} bars for structure and RVOL; "
                    f"received {len(bars)}."
                ),
            )
        )

    metrics = StructureMetrics()
    structurally_valid = not any(gate.blocks_confirmed for gate in gates)
    if len(bars) >= required_history and identity_ok and chronological:
        acceptance = bars[-profile.acceptance_bars :]
        prior = bars[
            -(
                profile.prior_range_bars + profile.acceptance_bars
            ) : -profile.acceptance_bars
        ]
        if profile.direction is EvidenceDirection.BULLISH:
            level = max(bar.high for bar in prior)
            threshold = level * (1 + profile.tolerance_bps / 10_000)
            accepted = all(bar.close > threshold for bar in acceptance)
        else:
            level = min(bar.low for bar in prior)
            threshold = level * (1 - profile.tolerance_bps / 10_000)
            accepted = all(bar.close < threshold for bar in acceptance)

        volume_baseline_bars = bars[-(profile.volume_baseline_bars + 1) : -1]
        volume_baseline = sum(bar.volume for bar in volume_baseline_bars) / len(
            volume_baseline_bars
        )
        relative_volume = (
            latest.volume / volume_baseline if volume_baseline > 0 else None
        )
        if volume_baseline <= 0:
            gates.append(
                _gate(
                    "WAIT_RVOL_BASELINE_UNKNOWN",
                    GateOutcome.WAIT,
                    "Comparable closed-bar volume baseline is zero or unknown.",
                )
            )

        metrics = StructureMetrics(
            reference_level=level,
            acceptance_threshold=threshold,
            accepted=accepted,
            relative_volume=relative_volume,
            volume_baseline=volume_baseline,
            reference_bar_ids=tuple(bar.identity.bar_id for bar in prior),
            acceptance_bar_ids=tuple(bar.identity.bar_id for bar in acceptance),
            volume_baseline_bar_ids=tuple(
                bar.identity.bar_id for bar in volume_baseline_bars
            ),
        )

    if len(bars) >= profile.nr_window + 1 and identity_ok and chronological:
        nr_bars = bars[-profile.nr_window :]
        preceding = bars[-(profile.nr_window + 1)]
        ranges: list[float] = []
        previous_close = preceding.close
        for bar in nr_bars:
            ranges.append(_true_range(bar, previous_close))
            previous_close = bar.close
        current_range = ranges[-1]
        metrics = metrics.model_copy(
            update={
                "narrow_range": current_range == min(ranges),
                "current_true_range": current_range,
                "nr_bar_ids": tuple(bar.identity.bar_id for bar in nr_bars),
            }
        )
    else:
        gates.append(
            _gate(
                "NR_HISTORY_INCOMPLETE",
                GateOutcome.UNKNOWN,
                "NRx requires one preceding close plus the configured window.",
                required=False,
            )
        )

    quality_state = (
        "REJECTED"
        if any(gate.outcome is GateOutcome.REJECT for gate in gates)
        else "INPUT_INCOMPLETE"
        if any(gate.blocks_confirmed for gate in gates)
        else "STRUCTURED_OK"
    )
    fact = _build_fact(
        instrument=instrument,
        source_result=source_result,
        profile=profile,
        bars=bars,
        metrics=metrics,
        quality_state=quality_state,
    )

    claims: list[EvidenceClaim] = []
    source_can_confirm = (
        source_result.state is SourceResultState.STRUCTURED_OK
        and source_result.freshness == "FRESH"
        and source_result.can_support_confirmed
    )
    claim_can_confirm = structurally_valid and source_can_confirm
    if quality_state == "STRUCTURED_OK" and metrics.accepted:
        claims.append(
            EvidenceClaim.create(
                feature_id="FTR-006",
                feature_version="1.0.0",
                family=EvidenceFamily.STRUCTURE,
                correlation_group="CG_PRICE_STRUCTURE",
                direction=profile.direction,
                strength_before_caps=1.0,
                source_fact_ids=(fact.fact_id,),
                authority=source_result.role,
                available_at=fact.lineage.available_at,
                event_time=fact.lineage.event_time,
                published_at=fact.lineage.published_at,
                received_at=fact.lineage.received_at,
                revision_id=fact.lineage.revision_id,
                artifact_hash=fact.lineage.artifact_hash,
                state_ceiling=(
                    StateCeiling.CONFIRMED if claim_can_confirm else StateCeiling.WAIT
                ),
                can_support_confirmed=claim_can_confirm,
                explanation=(
                    "Closed adjusted bars accepted the versioned prior-range level."
                ),
            )
        )
    if (
        quality_state == "STRUCTURED_OK"
        and metrics.relative_volume is not None
        and metrics.relative_volume >= profile.min_rvol
    ):
        rvol_strength = min(metrics.relative_volume / profile.min_rvol, 2.0) / 2
        claims.append(
            EvidenceClaim.create(
                feature_id="FTR-017",
                feature_version="1.0.0",
                family=EvidenceFamily.PARTICIPATION,
                correlation_group="CG_ACTIVITY_SESSION",
                direction=profile.direction,
                strength_before_caps=rvol_strength,
                source_fact_ids=(fact.fact_id,),
                authority=source_result.role,
                available_at=fact.lineage.available_at,
                event_time=fact.lineage.event_time,
                published_at=fact.lineage.published_at,
                received_at=fact.lineage.received_at,
                revision_id=fact.lineage.revision_id,
                artifact_hash=fact.lineage.artifact_hash,
                state_ceiling=(
                    StateCeiling.CONFIRMED if claim_can_confirm else StateCeiling.WAIT
                ),
                can_support_confirmed=claim_can_confirm,
                explanation=(
                    "Completed-bar volume exceeded its point-in-time comparable "
                    "baseline."
                ),
            )
        )
    if quality_state == "STRUCTURED_OK" and metrics.narrow_range:
        claims.append(
            EvidenceClaim.create(
                feature_id="FTR-007",
                feature_version="1.0.0",
                family=EvidenceFamily.STRUCTURE,
                correlation_group="CG_COMPRESSION",
                direction=profile.direction,
                strength_before_caps=0.35,
                source_fact_ids=(fact.fact_id,),
                authority=source_result.role,
                available_at=fact.lineage.available_at,
                state_ceiling=StateCeiling.WATCH,
                can_support_confirmed=False,
                explanation="NRx compression is discovery evidence only.",
            )
        )

    return StructureAnalysis(
        profile=profile,
        instrument=instrument,
        fact=fact,
        claims=tuple(claims),
        gate_results=tuple(gates),
        metrics=metrics,
    )
