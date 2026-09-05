from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .causal_engine import CausalCandidateInput, CausalEvidenceInput
from .models import HarmonicAdvancedAnalysis, OHLCVCandle


def _aware_datetime(value: str) -> tuple[datetime, bool]:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        return parsed.replace(tzinfo=timezone.utc), False
    return parsed, True


def _flow_contribution(features: dict[str, Any]) -> float:
    rvol = float(features.get("rvol20") or 0)
    if rvol >= 2:
        return 4.0
    if rvol >= 1.5:
        return 2.5
    if rvol >= 1:
        return 1.0
    return 0.0


def build_stored_candle_causal_candidate(
    *,
    symbol: str,
    candles: list[OHLCVCandle],
    analysis: HarmonicAdvancedAnalysis,
    features: dict[str, Any],
    source_gates_blocked: bool,
    external_evidence: list[CausalEvidenceInput] | None = None,
) -> CausalCandidateInput:
    if not candles:
        raise ValueError("stored-candle causal evaluation requires candles")
    latest = candles[-1]
    source_date, timestamp_was_aware = _aware_datetime(latest.timestamp)
    fetched_at, fetched_was_aware = _aware_datetime(latest.fetched_at)
    as_of = max(datetime.now(timezone.utc), fetched_at.astimezone(timezone.utc))
    structure_points = (
        min(max(analysis.hybrid_quality_score * 6, 0), 6)
        if analysis.validations
        else 0.0
    )
    flow_points = _flow_contribution(features)
    external = external_evidence or []
    cause_points = sum(
        max(item.contribution, 0) for item in external if item.layer.value == "CAUSE"
    )
    sponsor_points = sum(
        max(item.contribution, 0) for item in external if item.layer.value == "SPONSOR"
    )
    gates: list[dict[str, Any]] = []
    if cause_points < 2 or sponsor_points < 4:
        gates.append(
            {
                "code": "CAUSE_SPONSOR_REQUIRED",
                "outcome": "WAIT",
                "reason": (
                    f"Structured causal evidence is insufficient: CAUSE {cause_points:.2f}/2, "
                    f"SPONSOR {sponsor_points:.2f}/4; setup/flow evidence alone cannot qualify."
                ),
            }
        )
    if source_gates_blocked:
        gates.append(
            {
                "code": "OFFICIAL_SOURCE_CONFIRMATION",
                "outcome": "WAIT",
                "reason": "Required structured official source gates are not all fresh and passing.",
            }
        )
    if features.get("state") != "OK":
        gates.append(
            {
                "code": "POINT_IN_TIME_FEATURES",
                "outcome": "HARD_FAIL",
                "reason": f"Point-in-time feature state is {features.get('state', 'UNKNOWN')}.",
            }
        )
    if not timestamp_was_aware or not fetched_was_aware:
        gates.append(
            {
                "code": "SOURCE_TIMEZONE",
                "outcome": "STALE",
                "reason": "A stored candle timestamp lacked timezone metadata and was conservatively normalized to UTC.",
            }
        )

    evidence: list[dict[str, Any]] = [
        item.model_dump(mode="python", by_alias=True) for item in external
    ]
    if not any(item.layer.value == "CAUSE" for item in external):
        evidence.append(
            {
                "evidenceId": "cause-unavailable",
                "layer": "CAUSE",
                "signalType": "UNAVAILABLE",
                "contribution": 0,
                "source": latest.source,
                "sourceDate": source_date,
                "observedAt": fetched_at,
                "trustLevel": latest.trust_level,
                "explanation": "No structured point-in-time catalyst evidence is attached to this stored-candle scan.",
            }
        )
    if not any(item.layer.value == "SPONSOR" for item in external):
        evidence.append(
            {
                "evidenceId": "sponsor-unavailable",
                "layer": "SPONSOR",
                "signalType": "UNAVAILABLE",
                "contribution": 0,
                "source": latest.source,
                "sourceDate": source_date,
                "observedAt": fetched_at,
                "trustLevel": latest.trust_level,
                "explanation": "No structured stock-level sponsor evidence is attached to this stored-candle scan.",
            }
        )
    evidence.extend(
        [
            {
                "evidenceId": "harmonic-structure",
                "layer": "STRUCTURE",
                "signalType": "HARMONIC_STRUCTURE",
                "contribution": structure_points,
                "source": latest.source,
                "sourceDate": source_date,
                "observedAt": fetched_at,
                "trustLevel": latest.trust_level,
                "explanation": "Auditable harmonic structure quality; this is setup evidence, not a causal trigger.",
                "rawInputKeys": ["ohlcv_price_structure"],
            },
            {
                "evidenceId": "rvol-flow",
                "layer": "FLOW",
                "signalType": "RVOL",
                "contribution": flow_points,
                "source": latest.source,
                "sourceDate": source_date,
                "observedAt": fetched_at,
                "trustLevel": latest.trust_level,
                "explanation": "Stored-candle relative volume is a flow proxy and does not identify an institution.",
                "rawInputKeys": ["ohlcv_volume"],
            },
        ]
    )
    return CausalCandidateInput.model_validate(
        {
            "symbol": symbol,
            "direction": "WATCH",
            "asOf": as_of,
            "evaluationMode": "PRODUCTION",
            "evidence": evidence,
            "gates": gates,
            "execution": {
                "score": round(min(max(analysis.gate_ratio * 16, 0), 16), 4),
                "triggerActive": analysis.final_state.startswith("HARMONIC_CONFIRMED"),
                "gates": [],
            },
        }
    )
