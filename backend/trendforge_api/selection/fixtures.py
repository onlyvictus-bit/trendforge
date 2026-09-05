from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256

from ..source_contracts import SourceResult, SourceResultState, SourceRole
from .contracts import (
    DataMode,
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    GateOutcome,
    InstrumentIdentity,
    NormalizedFact,
    PointInTimeLineage,
    SelectionCandidate,
    SelectionFixtureBatch,
    SelectionGateResult,
    SelectionScanRun,
    SelectionState,
    StateCeiling,
    stable_id,
)


IST = timezone(timedelta(hours=5, minutes=30))
FIXTURE_AS_OF = datetime(2026, 7, 19, 10, 30, tzinfo=IST)
FIXTURE_AVAILABLE_AT = datetime(2026, 7, 19, 9, 0, tzinfo=IST)
FIXTURE_DATA_DATE = date(2026, 7, 18)


def _digest(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


def _lineage(label: str) -> PointInTimeLineage:
    return PointInTimeLineage(
        event_time=datetime(2026, 7, 18, 15, 30, tzinfo=IST),
        published_at=datetime(2026, 7, 18, 18, 0, tzinfo=IST),
        available_at=FIXTURE_AVAILABLE_AT,
        received_at=datetime(2026, 7, 19, 9, 0, 1, tzinfo=IST),
        retrieved_at=datetime(2026, 7, 19, 9, 0, 2, tzinfo=IST),
        revision_id="fixture-r1",
        artifact_hash=_digest(label),
    )


def _source_results() -> tuple[SourceResult, ...]:
    common = {
        "contractVersion": "1.0.0",
        "role": SourceRole.OFFICIAL_GATE,
        "dataDate": FIXTURE_DATA_DATE,
        "publishedAt": datetime(2026, 7, 18, 18, 0, tzinfo=IST),
        "receivedAt": datetime(2026, 7, 19, 9, 0, 1, tzinfo=IST),
        "availableAt": FIXTURE_AVAILABLE_AT,
        "retrievedAt": datetime(2026, 7, 19, 9, 0, 2, tzinfo=IST),
        "schemaVersion": "fixture-schema-1",
        "parserVersion": "fixture-parser-1",
        "revisionId": "fixture-r1",
    }
    return (
        SourceResult.model_validate(
            {
                **common,
                "sourceId": "SRC-NSE-EOD",
                "state": SourceResultState.STRUCTURED_OK,
                "recordCount": 4,
                "artifactHash": _digest("q5-r1-eod"),
                "freshness": "FRESH",
                "canSupportConfirmed": True,
                "stateCeiling": "CONFIRMED",
            }
        ),
        SourceResult.model_validate(
            {
                **common,
                "sourceId": "SRC-NSE-GSM",
                "state": SourceResultState.VALID_EMPTY,
                "recordCount": 0,
                "artifactHash": _digest("q5-r1-gsm-empty"),
                "emptySemantics": "No symbols were present in the dated GSM list.",
                "freshness": "FRESH",
                "canSupportConfirmed": False,
                "stateCeiling": "WAIT",
            }
        ),
        SourceResult.model_validate(
            {
                **common,
                "sourceId": "SRC-NSE-OPTIONS",
                "state": SourceResultState.BLOCKED,
                "recordCount": 0,
                "artifactHash": None,
                "freshness": "UNKNOWN",
                "canSupportConfirmed": False,
                "stateCeiling": "WAIT",
                "errorType": "BLOCK_PAGE",
                "errorMessage": "Controlled fixture access-denied response.",
            }
        ),
    )


def _instrument(symbol: str) -> InstrumentIdentity:
    return InstrumentIdentity.create(
        exchange="NSE",
        segment="EQUITY",
        symbol=symbol,
        isin=f"INE{_digest(symbol)[:7].upper()}01010",
        series="EQ",
    )


def _fact(instrument: InstrumentIdentity) -> NormalizedFact:
    lineage = _lineage(f"q5-r1-{instrument.symbol}")
    return NormalizedFact.create(
        instrument_id=instrument.instrument_id,
        source_id="SRC-NSE-EOD",
        dataset_root="NSE_EOD_EQUITY",
        business_keys={
            "symbol": instrument.symbol,
            "data_date": FIXTURE_DATA_DATE.isoformat(),
        },
        data_date=FIXTURE_DATA_DATE,
        lineage=lineage,
        quality_state="STRUCTURED_OK",
        payload={"close": 100.0, "volume": 1000.0, "fixture": True},
    )


def _claim(
    fact: NormalizedFact,
    *,
    feature_id: str,
    family: EvidenceFamily,
    group: str,
    direction: EvidenceDirection,
    strength: float,
    explanation: str,
) -> EvidenceClaim:
    return EvidenceClaim.create(
        feature_id=feature_id,
        feature_version="1.0.0",
        family=family,
        correlation_group=group,
        direction=direction,
        strength_before_caps=strength,
        source_fact_ids=(fact.fact_id,),
        authority=SourceRole.EXPERIMENTAL,
        available_at=fact.lineage.available_at,
        state_ceiling=StateCeiling.WAIT,
        can_support_confirmed=False,
        explanation=explanation,
    )


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


def _candidate(
    *,
    run: SelectionScanRun,
    instrument: InstrumentIdentity,
    state: SelectionState,
    direction: EvidenceDirection,
    supports: tuple[EvidenceFamily, ...],
    opposes: tuple[EvidenceFamily, ...] = (),
    missing: tuple[EvidenceFamily, ...] = (),
    gates: tuple[SelectionGateResult, ...] = (),
    discovery_reason: str,
    top_reason: str,
    contradiction: str | None,
    missing_proof: tuple[str, ...],
    next_confirmation: str,
    invalidation: str,
    what_changed: str,
    strength: float,
) -> SelectionCandidate:
    return SelectionCandidate(
        candidate_id=stable_id("cand", run.run_id, instrument.instrument_id),
        run_id=run.run_id,
        instrument=instrument,
        market="NSE",
        profile_id=run.profile_id,
        profile_version=run.profile_version,
        timeframe="1d",
        state=state,
        state_ceiling=StateCeiling.WAIT,
        evidence_direction=direction,
        discovery_reason=discovery_reason,
        family_supports=supports,
        family_opposes=opposes,
        family_missing=missing,
        top_reason=top_reason,
        contradiction=contradiction,
        missing_proof=missing_proof,
        next_confirmation=next_confirmation,
        invalidation_condition=invalidation,
        context="Synthetic Q5-R1 contract fixture; research-only.",
        freshness="MIXED" if missing else "FRESH",
        completeness=run.completeness,
        what_changed=what_changed,
        evidence_strength=strength,
        gate_results=gates,
        source_ages_seconds={
            "SRC-NSE-EOD": int((FIXTURE_AS_OF - FIXTURE_AVAILABLE_AT).total_seconds()),
            "SRC-NSE-GSM": int((FIXTURE_AS_OF - FIXTURE_AVAILABLE_AT).total_seconds()),
            "SRC-NSE-OPTIONS": None,
        },
        data_mode=DataMode.SYNTHETIC_TEST,
        demo_only=True,
        executable=False,
    )


def build_q5_r1_fixture_batch() -> SelectionFixtureBatch:
    instruments = tuple(
        _instrument(symbol)
        for symbol in (
            "TF_WATCH",
            "TF_WAIT_CLOSE",
            "TF_WAIT_EARLY_CONFIRM",
            "TF_REJECT",
        )
    )
    facts = tuple(_fact(instrument) for instrument in instruments)
    claims = (
        _claim(
            facts[0],
            feature_id="FTR-018",
            family=EvidenceFamily.PARTICIPATION,
            group="CG_ACTIVITY_SESSION",
            direction=EvidenceDirection.BULLISH,
            strength=0.35,
            explanation="Discovery participation is visible but not confirmation.",
        ),
        _claim(
            facts[1],
            feature_id="FTR-006",
            family=EvidenceFamily.STRUCTURE,
            group="CG_PRICE_STRUCTURE",
            direction=EvidenceDirection.BULLISH,
            strength=0.52,
            explanation="Structure is forming on an unclosed bar.",
        ),
        _claim(
            facts[2],
            feature_id="FTR-006",
            family=EvidenceFamily.STRUCTURE,
            group="CG_PRICE_STRUCTURE",
            direction=EvidenceDirection.BULLISH,
            strength=0.78,
            explanation="Strong synthetic inputs remain capped until Q5-R3.",
        ),
        _claim(
            facts[3],
            feature_id="FTR-035",
            family=EvidenceFamily.TRADABILITY_AND_SAFETY,
            group="CG_TRADABILITY",
            direction=EvidenceDirection.NEUTRAL,
            strength=0.0,
            explanation="A deterministic safety veto rejects the fixture.",
        ),
    )
    run = SelectionScanRun.create(
        profile_id="PRF-Q5-R1-FIXTURE",
        profile_version="1.0.0",
        as_of=FIXTURE_AS_OF,
        universe_version="fixture-universe-1",
        data_mode=DataMode.SYNTHETIC_TEST,
        eligible_count=4,
        scanned_count=4,
    )
    candidates = (
        _candidate(
            run=run,
            instrument=instruments[0],
            state=SelectionState.WATCH,
            direction=EvidenceDirection.BULLISH,
            supports=(EvidenceFamily.PARTICIPATION,),
            missing=(EvidenceFamily.STRUCTURE,),
            discovery_reason=("Participation discovery entered the research queue."),
            top_reason="Early participation exists without closed structure.",
            contradiction=None,
            missing_proof=("Closed structure evidence",),
            next_confirmation=("Wait for the configured closed-bar structure trigger."),
            invalidation="Remove from WATCH if participation normalizes.",
            what_changed="New discovery claim appeared in this comparable run.",
            strength=0.35,
        ),
        _candidate(
            run=run,
            instrument=instruments[1],
            state=SelectionState.WAIT,
            direction=EvidenceDirection.BULLISH,
            supports=(EvidenceFamily.STRUCTURE,),
            missing=(EvidenceFamily.PARTICIPATION,),
            gates=(
                _gate(
                    "WAIT_BAR_CLOSE",
                    GateOutcome.WAIT,
                    "The structure bar is not closed.",
                ),
            ),
            discovery_reason=("A forming structure activated a named close gate."),
            top_reason="Open-bar evidence cannot confirm.",
            contradiction=None,
            missing_proof=("Closed bar", "Independent participation family"),
            next_confirmation=(
                "Re-evaluate after the bar closes and participation is available."
            ),
            invalidation="Reject if the forming level fails before close.",
            what_changed=(
                "The candidate moved from discovery to a specific close wait."
            ),
            strength=0.52,
        ),
        _candidate(
            run=run,
            instrument=instruments[2],
            state=SelectionState.WAIT,
            direction=EvidenceDirection.BULLISH,
            supports=(
                EvidenceFamily.STRUCTURE,
                EvidenceFamily.PARTICIPATION,
            ),
            gates=(
                _gate(
                    "WAIT_Q5_R1_NO_CONFIRMED",
                    GateOutcome.WAIT,
                    (
                        "Q5-R1 cannot emit CONFIRMED before the closed-bar pack "
                        "and resolver pass."
                    ),
                ),
            ),
            discovery_reason=(
                "Synthetic independent-looking inputs test the milestone ceiling."
            ),
            top_reason="The Q5-R1 acceptance ceiling blocks early confirmation.",
            contradiction="Fixture evidence is synthetic and non-voting.",
            missing_proof=(
                "Accepted Q5-R2 resolver",
                "Accepted Q5-R3 closed-bar pack",
            ),
            next_confirmation=(
                "Remain WAIT until Q5-R2 and Q5-R3 acceptance gates pass."
            ),
            invalidation="Reject if a hard safety or structure veto appears.",
            what_changed=(
                "Additional support appeared, but the milestone ceiling did not change."
            ),
            strength=0.78,
        ),
        _candidate(
            run=run,
            instrument=instruments[3],
            state=SelectionState.REJECT,
            direction=EvidenceDirection.NEUTRAL,
            supports=(),
            opposes=(EvidenceFamily.TRADABILITY_AND_SAFETY,),
            gates=(
                _gate(
                    "REJECT_HARD_SAFETY_FIXTURE",
                    GateOutcome.REJECT,
                    "Controlled hard tradability veto.",
                ),
            ),
            discovery_reason=("A controlled candidate exercises hard-veto handling."),
            top_reason="Hard tradability veto dominates all other evidence.",
            contradiction="Safety evidence invalidates the setup.",
            missing_proof=(),
            next_confirmation=(
                "A new comparable run may reopen only after the veto expires."
            ),
            invalidation="The current setup remains invalid while the veto is active.",
            what_changed="A hard veto appeared in the comparable run.",
            strength=0.0,
        ),
    )
    return SelectionFixtureBatch(
        run=run,
        candidates=candidates,
        source_results=_source_results(),
        facts=facts,
        claims=claims,
    )
