"""R17 read-only OpenAlgo shadow projection and activation boundary.

This module is deliberately additive. It can explain OpenAlgo observations and
research sizing, but it cannot mutate the canonical R1-R16 state, confirm a
setup, place an order, or treat configuration as observed live readiness.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, date, datetime
from enum import StrEnum
from statistics import fmean
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .openalgo_identity import IdentityState, InstrumentIdentityResult
from .openalgo_stream import OpenAlgoStreamManager, StreamState
from .options_intelligence.chain_quality import StrikeQuote, assess_chain
from .options_intelligence.pricing import black76_greeks
from .options_intelligence.surface import (
    max_pain_reference,
    pcr_oi,
    unsigned_cash_gamma_per_strike,
    walls,
)
from .selection.research_quantity import compute_research_quantity


SCHEMA_VERSION = "trendforge.openalgo-shadow.v1"
MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    frozen=True,
)


class ActivationStage(StrEnum):
    DISABLED = "DISABLED"
    CONTRACT_PINNED = "CONTRACT_PINNED"
    FIXTURE_VERIFIED = "FIXTURE_VERIFIED"
    REST_SHADOW_OBSERVED = "REST_SHADOW_OBSERVED"
    STREAM_SHADOW_OBSERVED = "STREAM_SHADOW_OBSERVED"
    SHADOW_LIVE = "SHADOW_LIVE"


class OptionApplicability(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    WAIT_PARTIAL_CHAIN = "WAIT_PARTIAL_CHAIN"


class OpenAlgoActivationEvidenceV1(BaseModel):
    model_config = MODEL_CONFIG

    enabled: bool = False
    contract_pinned: bool = False
    fixture_verified: bool = False
    live_observation_approved: bool = False
    rest_observed: bool = False
    rest_replay_verified: bool = False
    stream_observed: bool = False
    reconnect_verified: bool = False
    stream_replay_verified: bool = False
    provider_sequence_available: bool = False


class OpenAlgoActivationV1(BaseModel):
    model_config = MODEL_CONFIG

    stage: ActivationStage
    blocker_codes: tuple[str, ...] = ()
    network_allowed: bool = False
    storage_allowed: bool = False
    projection_allowed: bool = False
    shadow_live: bool = False
    executable: bool = False


def assess_openalgo_activation(
    evidence: OpenAlgoActivationEvidenceV1,
) -> OpenAlgoActivationV1:
    """Resolve proof stage. Flags describe evidence; they do not create it."""
    if not evidence.enabled:
        return OpenAlgoActivationV1(
            stage=ActivationStage.DISABLED,
            blocker_codes=("OPENALGO_DISABLED",),
        )

    blockers: list[str] = []
    if not evidence.contract_pinned:
        blockers.append("WAIT_CONTRACT_PIN")
        return OpenAlgoActivationV1(
            stage=ActivationStage.CONTRACT_PINNED,
            blocker_codes=tuple(blockers),
        )
    if not evidence.fixture_verified:
        blockers.append("WAIT_FIXTURE_VERIFICATION")
        return OpenAlgoActivationV1(
            stage=ActivationStage.CONTRACT_PINNED,
            blocker_codes=tuple(blockers),
        )

    network_allowed = evidence.live_observation_approved
    storage_allowed = evidence.live_observation_approved
    stage = ActivationStage.FIXTURE_VERIFIED

    if not evidence.rest_observed:
        blockers.append("WAIT_REST_OBSERVATION")
    elif not evidence.rest_replay_verified:
        blockers.append("WAIT_REST_REPLAY")
    else:
        stage = ActivationStage.REST_SHADOW_OBSERVED

    stream_proof = (
        evidence.stream_observed
        and evidence.reconnect_verified
        and evidence.stream_replay_verified
    )
    if evidence.rest_observed and evidence.rest_replay_verified:
        if not evidence.stream_observed:
            blockers.append("WAIT_STREAM_OBSERVATION")
        elif not evidence.reconnect_verified:
            blockers.append("WAIT_STREAM_RECONNECT")
        elif not evidence.stream_replay_verified:
            blockers.append("WAIT_STREAM_REPLAY")
        elif stream_proof:
            stage = ActivationStage.STREAM_SHADOW_OBSERVED
            if not evidence.provider_sequence_available:
                blockers.append("WAIT_STREAM_SEQUENCE_UNAVAILABLE")

    shadow_live = bool(
        evidence.live_observation_approved
        and evidence.rest_observed
        and evidence.rest_replay_verified
        and stream_proof
        and evidence.provider_sequence_available
    )
    if shadow_live:
        stage = ActivationStage.SHADOW_LIVE
        blockers.clear()

    return OpenAlgoActivationV1(
        stage=stage,
        blocker_codes=tuple(dict.fromkeys(blockers)),
        network_allowed=network_allowed,
        storage_allowed=storage_allowed,
        projection_allowed=True,
        shadow_live=shadow_live,
        executable=False,
    )


def activation_from_environment() -> OpenAlgoActivationV1:
    """Return the local safe checkpoint without performing broker I/O.

    Environment configuration may expose the fixture-verified boundary only.
    Live stages require observed replay records and are never inferred here.
    """
    enabled = os.environ.get("OPENALGO_ENABLED") == "1"
    if not enabled:
        return assess_openalgo_activation(OpenAlgoActivationEvidenceV1())
    return assess_openalgo_activation(
        OpenAlgoActivationEvidenceV1(
            enabled=True,
            contract_pinned=True,
            fixture_verified=True,
        )
    )


class OpenAlgoBaseCandidateV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    base_public_state: str
    evidence_direction: str
    draft_confirmed_eligible: bool = False
    invalidation_condition: str | None = None
    atr: float | None = None
    is_reject_or_ban: bool = False
    completeness_ratio: float | None = None
    regime_label: str | None = None
    index_suspect: bool = False
    base_row_hash: str
    fno_eligible: bool = False


class OpenAlgoRestObservationV1(BaseModel):
    model_config = MODEL_CONFIG

    quality_state: str
    last_price: float | None = Field(default=None, gt=0)
    data_at: datetime
    received_at: datetime
    max_age_seconds: int = Field(gt=0)
    raw_content_hash: str
    replay_content_hash: str
    route: str

    @model_validator(mode="after")
    def require_aware_clocks(self) -> "OpenAlgoRestObservationV1":
        if self.data_at.tzinfo is None or self.received_at.tzinfo is None:
            raise ValueError("OpenAlgo observation clocks must be timezone-aware")
        return self

    def is_fresh(self, *, as_of: datetime) -> bool:
        age = (as_of.astimezone(UTC) - self.data_at.astimezone(UTC)).total_seconds()
        return 0 <= age <= self.max_age_seconds


class OpenAlgoOptionSnapshotV1(BaseModel):
    model_config = MODEL_CONFIG

    applicable: bool
    underlying: str
    exchange: str
    expiry: date
    captured_at: datetime
    max_age_seconds: int = Field(gt=0)
    spot: float = Field(gt=0)
    years_to_expiry: float = Field(gt=0)
    lot_size: int = Field(gt=0)
    expected_strike_count: int = Field(gt=0)
    rows: tuple[StrikeQuote, ...] = ()
    iv_percentile: float | None = Field(default=None, ge=0, le=100)
    snapshot_id: str
    dataset_root_id: str
    raw_content_hash: str

    @model_validator(mode="after")
    def require_aware_capture(self) -> "OpenAlgoOptionSnapshotV1":
        if self.captured_at.tzinfo is None:
            raise ValueError("option snapshot clock must be timezone-aware")
        return self


class OptionPurposeVoteV1(BaseModel):
    model_config = MODEL_CONFIG

    vote_id: str
    purpose: str
    applicability: OptionApplicability
    raw_value: Any = None
    interpretation: str
    formula_version: str
    dataset_root_id: str
    snapshot_id: str
    raw_content_hash: str
    can_confirm: bool = False


class OptionConcentrationDiagnosticV1(BaseModel):
    model_config = MODEL_CONFIG

    vote_count: int = Field(ge=0)
    dataset_root_count: int = Field(ge=0)
    independent_confirmation_count: int = Field(ge=0)
    message: str


OPTION_PURPOSES: tuple[tuple[str, str, str], ...] = (
    ("OPTION_PCR_CROWDING", "put/call OI crowding", "R17-PCR-OI-v1"),
    ("OPTION_OI_WALL_STRUCTURE", "largest OI support/resistance candidates", "R17-OI-WALL-v1"),
    ("OPTION_MAX_PAIN_MAGNET", "expiry settlement magnet reference", "R17-MAX-PAIN-v1"),
    ("OPTION_IV_REGIME", "implied-volatility regime", "R17-IV-REGIME-v1"),
    ("OPTION_GREEKS_CONVEXITY", "Black-76 convexity context", "R17-BLACK76-v1"),
    ("OPTION_VOLUME_LIQUIDITY", "tradability and chain participation", "R17-CHAIN-LIQ-v1"),
    ("OPTION_GAMMA_FRAGILITY", "unsigned gamma concentration fragility", "R17-UNSIGNED-GAMMA-v1"),
)


def _uniform_votes(
    snapshot: OpenAlgoOptionSnapshotV1,
    applicability: OptionApplicability,
    interpretation: str,
) -> tuple[OptionPurposeVoteV1, ...]:
    return tuple(
        OptionPurposeVoteV1(
            vote_id=vote_id,
            purpose=purpose,
            applicability=applicability,
            interpretation=interpretation,
            formula_version=formula,
            dataset_root_id=snapshot.dataset_root_id,
            snapshot_id=snapshot.snapshot_id,
            raw_content_hash=snapshot.raw_content_hash,
        )
        for vote_id, purpose, formula in OPTION_PURPOSES
    )


def build_option_purpose_votes(
    snapshot: OpenAlgoOptionSnapshotV1,
    *,
    as_of: datetime | None = None,
) -> tuple[tuple[OptionPurposeVoteV1, ...], OptionConcentrationDiagnosticV1]:
    """Calculate seven purpose-specific views without seven confirmations."""
    concentration = OptionConcentrationDiagnosticV1(
        vote_count=7,
        dataset_root_count=1,
        independent_confirmation_count=0,
        message="Seven purpose views share one option-chain dataset root.",
    )
    if not snapshot.applicable:
        return (
            _uniform_votes(
                snapshot,
                OptionApplicability.NOT_APPLICABLE,
                "Underlying is not eligible for option-chain enrichment.",
            ),
            concentration,
        )

    clock = as_of or snapshot.captured_at
    age = (clock.astimezone(UTC) - snapshot.captured_at.astimezone(UTC)).total_seconds()
    if age < 0 or age > snapshot.max_age_seconds:
        return (
            _uniform_votes(
                snapshot,
                OptionApplicability.STALE,
                "Option-chain snapshot is outside its freshness contract.",
            ),
            concentration,
        )

    quality = assess_chain(
        [row.model_dump(mode="python") for row in snapshot.rows],
        expected_strike_count=snapshot.expected_strike_count,
    )
    if quality.state != "CHAIN_OK":
        return (
            _uniform_votes(
                snapshot,
                OptionApplicability.WAIT_PARTIAL_CHAIN,
                "Chain is crossed, partial, empty, or outside the spread gate.",
            ),
            concentration,
        )

    rows = list(snapshot.rows)
    call_oi = sum(row.open_interest for row in rows if row.right == "CE")
    put_oi = sum(row.open_interest for row in rows if row.right == "PE")
    pcr = pcr_oi(put_oi=put_oi, call_oi=call_oi)
    call_wall, put_wall = walls(rows, known_at=snapshot.captured_at)
    max_pain = max_pain_reference(rows, multiplier=snapshot.lot_size)

    greek_rows: list[dict[str, float]] = []
    for row in rows:
        if not row.implied_volatility:
            continue
        greek = black76_greeks(
            forward=snapshot.spot,
            strike=row.strike,
            years=snapshot.years_to_expiry,
            sigma=row.implied_volatility / 100.0,
            rate=0.0,
            right=row.right,
        )
        greek_rows.append(
            {
                "strike": row.strike,
                "delta": round(greek.delta, 6),
                "gamma": round(greek.gamma, 8),
                "vega": round(greek.vega, 6),
            }
        )

    spreads: list[float] = []
    for row in rows:
        if row.bid and row.ask:
            mid = (row.bid + row.ask) / 2
            if mid > 0:
                spreads.append((row.ask - row.bid) / mid * 100)
    liquidity = {
        "volume": sum(row.volume for row in rows),
        "openInterest": call_oi + put_oi,
        "meanSpreadPct": round(fmean(spreads), 4) if spreads else None,
    }
    gamma = unsigned_cash_gamma_per_strike(
        rows,
        forward=snapshot.spot,
        years=snapshot.years_to_expiry,
        lot_size=snapshot.lot_size,
    )

    values: dict[str, tuple[Any, OptionApplicability, str]] = {
        "OPTION_PCR_CROWDING": (
            pcr,
            OptionApplicability.AVAILABLE if pcr is not None else OptionApplicability.UNAVAILABLE,
            "Put OI divided by call OI; context only." if pcr is not None else "Call OI denominator is zero.",
        ),
        "OPTION_OI_WALL_STRUCTURE": (
            {
                "callWall": call_wall.model_dump(mode="json", by_alias=True) if call_wall else None,
                "putWall": put_wall.model_dump(mode="json", by_alias=True) if put_wall else None,
            },
            OptionApplicability.AVAILABLE if call_wall or put_wall else OptionApplicability.UNAVAILABLE,
            "Largest OI strikes are candidates, not guaranteed barriers.",
        ),
        "OPTION_MAX_PAIN_MAGNET": (
            max_pain,
            OptionApplicability.AVAILABLE if max_pain is not None else OptionApplicability.UNAVAILABLE,
            "Minimum aggregate expiry payout reference; not a price target.",
        ),
        "OPTION_IV_REGIME": (
            snapshot.iv_percentile,
            OptionApplicability.AVAILABLE if snapshot.iv_percentile is not None else OptionApplicability.UNAVAILABLE,
            "IV percentile describes volatility regime, not direction.",
        ),
        "OPTION_GREEKS_CONVEXITY": (
            greek_rows or None,
            OptionApplicability.AVAILABLE if greek_rows else OptionApplicability.UNAVAILABLE,
            "Black-76 model estimates using explicit snapshot inputs.",
        ),
        "OPTION_VOLUME_LIQUIDITY": (
            liquidity,
            OptionApplicability.AVAILABLE,
            "Volume, OI and spread describe chain tradability.",
        ),
        "OPTION_GAMMA_FRAGILITY": (
            gamma or None,
            OptionApplicability.AVAILABLE if gamma else OptionApplicability.UNAVAILABLE,
            "Unsigned cash-gamma concentration proxy only.",
        ),
    }
    votes = tuple(
        OptionPurposeVoteV1(
            vote_id=vote_id,
            purpose=purpose,
            applicability=values[vote_id][1],
            raw_value=values[vote_id][0],
            interpretation=values[vote_id][2],
            formula_version=formula,
            dataset_root_id=snapshot.dataset_root_id,
            snapshot_id=snapshot.snapshot_id,
            raw_content_hash=snapshot.raw_content_hash,
            can_confirm=False,
        )
        for vote_id, purpose, formula in OPTION_PURPOSES
    )
    return votes, concentration


class OpenAlgoShadowRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    base_public_state: str
    public_state: str
    openalgo_profile_state: str
    evidence_direction: str
    rest_quality_state: str | None = None
    rest_age_seconds: float | None = None
    research_entry: float | None = None
    research_stop: float | None = None
    research_t1: float | None = None
    research_t2: float | None = None
    research_quantity: int = 0
    qty_unit: str = "shares"
    option_votes: tuple[OptionPurposeVoteV1, ...] = ()
    option_concentration: OptionConcentrationDiagnosticV1 | None = None
    missing_or_conflicting: tuple[str, ...] = ()
    next_condition: str
    base_row_hash: str
    executable: bool = False


class OpenAlgoShadowBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    activation: OpenAlgoActivationV1
    base_run_hash: str
    rows: tuple[OpenAlgoShadowRowV1, ...] = ()
    base_output_unchanged: bool = True
    confirmed_count: int = 0
    executable: bool = False

    @model_validator(mode="after")
    def enforce_shadow_ceiling(self) -> "OpenAlgoShadowBatchV1":
        if self.confirmed_count != 0 or self.executable:
            raise ValueError("OpenAlgo shadow cannot confirm or execute")
        if any(row.public_state != row.base_public_state for row in self.rows):
            raise ValueError("OpenAlgo shadow cannot mutate base public state")
        return self


def build_openalgo_shadow_batch(
    *,
    base_run_hash: str,
    candidates: tuple[OpenAlgoBaseCandidateV1, ...],
    activation: OpenAlgoActivationV1,
    identities: Mapping[str, InstrumentIdentityResult],
    rest_observations: Mapping[str, OpenAlgoRestObservationV1],
    option_snapshots: Mapping[str, OpenAlgoOptionSnapshotV1],
    as_of: datetime,
) -> OpenAlgoShadowBatchV1:
    if activation.stage is ActivationStage.DISABLED:
        return OpenAlgoShadowBatchV1(
            activation=activation,
            base_run_hash=base_run_hash,
        )

    rows: list[OpenAlgoShadowRowV1] = []
    for candidate in candidates:
        blockers: list[str] = []
        identity = identities.get(candidate.symbol)
        rest = rest_observations.get(candidate.symbol)
        profile_state = "WATCH"
        if not activation.projection_allowed:
            blockers.append("WAIT_OPENALGO_PROJECTION")
        if identity is None or identity.state is not IdentityState.EXACT:
            blockers.append("WAIT_IDENTITY")
        if rest is None:
            blockers.append("WAIT_REST_MISSING")
        elif rest.quality_state != "VALID_POPULATED":
            blockers.append("WAIT_REST_QUALITY")
        elif not rest.is_fresh(as_of=as_of):
            blockers.append("WAIT_REST_STALE")
        if blockers:
            profile_state = "WAIT"

        option_votes: tuple[OptionPurposeVoteV1, ...] = ()
        concentration: OptionConcentrationDiagnosticV1 | None = None
        snapshot = option_snapshots.get(candidate.symbol)
        if snapshot is not None:
            option_votes, concentration = build_option_purpose_votes(snapshot, as_of=as_of)
        elif candidate.fno_eligible:
            blockers.append("WAIT_OPTION_CHAIN_MISSING")

        qty_result: dict[str, Any] = {"researchQuantity": 0, "reason": "WAIT_OPENALGO_PROFILE"}
        if profile_state == "WATCH" and identity and identity.contract and rest:
            qty_result = compute_research_quantity(
                public_state=candidate.base_public_state,
                evidence_direction=candidate.evidence_direction,
                draft_confirmed_eligible=candidate.draft_confirmed_eligible,
                is_reject_or_ban=candidate.is_reject_or_ban,
                official_close=rest.last_price,
                invalidation_condition=candidate.invalidation_condition,
                atr=candidate.atr,
                lot_size=identity.contract.lot_size,
                s8_completeness_ratio=candidate.completeness_ratio,
                regime_label=candidate.regime_label,
                index_suspect=candidate.index_suspect,
                lane="OPENALGO_RO",
            )
            if qty_result.get("reason"):
                blockers.append(str(qty_result["reason"]))

        entry = qty_result.get("researchEntry")
        stop = qty_result.get("researchStop")
        t2: float | None = None
        if entry is not None and stop is not None:
            risk = abs(float(entry) - float(stop))
            t2 = round(float(entry) + 2 * risk, 2) if candidate.evidence_direction.upper() in {"BULLISH", "BUY"} else round(float(entry) - 2 * risk, 2)

        age = None
        if rest is not None:
            age = max(0.0, (as_of.astimezone(UTC) - rest.data_at.astimezone(UTC)).total_seconds())
        rows.append(
            OpenAlgoShadowRowV1(
                symbol=candidate.symbol,
                base_public_state=candidate.base_public_state,
                public_state=candidate.base_public_state,
                openalgo_profile_state=profile_state,
                evidence_direction=candidate.evidence_direction,
                rest_quality_state=rest.quality_state if rest else None,
                rest_age_seconds=age,
                research_entry=entry,
                research_stop=stop,
                research_t1=qty_result.get("researchT1"),
                research_t2=t2,
                research_quantity=int(qty_result.get("researchQuantity") or 0),
                qty_unit=str(qty_result.get("qtyUnit") or "shares"),
                option_votes=option_votes,
                option_concentration=concentration,
                missing_or_conflicting=tuple(dict.fromkeys(blockers)),
                next_condition=(
                    "Resolve: " + ", ".join(dict.fromkeys(blockers))
                    if blockers
                    else "Keep REST and option evidence inside freshness contracts."
                ),
                base_row_hash=candidate.base_row_hash,
            )
        )
    return OpenAlgoShadowBatchV1(
        activation=activation,
        base_run_hash=base_run_hash,
        rows=tuple(rows),
    )


class OpenAlgoRollbackV1(BaseModel):
    model_config = MODEL_CONFIG

    before_base_hash: str
    after_base_hash: str
    stream_state: StreamState
    network_activity_after_disable: int = 0
    storage_activity_after_disable: int = 0


class OpenAlgoShadowRuntime:
    """Small runtime guard proving disabled mode is inert and reversible."""

    def __init__(
        self,
        *,
        base_payload: Mapping[str, Any],
        stream_manager: OpenAlgoStreamManager | None = None,
    ) -> None:
        self._base_payload = dict(base_payload)
        self.stream_manager = stream_manager or OpenAlgoStreamManager(enabled=False)
        self.enabled = self.stream_manager.enabled
        self.network_activity = 0
        self.storage_activity = 0

    @property
    def base_output_hash(self) -> str:
        encoded = json.dumps(
            self._base_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def note_network_activity(self) -> None:
        if not self.enabled:
            raise RuntimeError("OpenAlgo shadow is disabled")
        self.network_activity += 1

    def note_storage_activity(self) -> None:
        if not self.enabled:
            raise RuntimeError("OpenAlgo shadow is disabled")
        self.storage_activity += 1

    def disable(self) -> OpenAlgoRollbackV1:
        before = self.base_output_hash
        self.enabled = False
        self.stream_manager.enabled = False
        self.stream_manager.stop()
        after = self.base_output_hash
        return OpenAlgoRollbackV1(
            before_base_hash=before,
            after_base_hash=after,
            stream_state=self.stream_manager.state,
            network_activity_after_disable=0,
            storage_activity_after_disable=0,
        )


def disabled_shadow_batch() -> OpenAlgoShadowBatchV1:
    return OpenAlgoShadowBatchV1(
        activation=activation_from_environment(),
        base_run_hash="DISABLED_NO_BASE_RUN",
    )
