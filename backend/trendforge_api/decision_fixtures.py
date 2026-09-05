from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel

from . import storage
from .causal_engine import (
    CausalBatchRequest,
    CausalEvaluationResult,
    evaluate_causal_batch,
)


DEMO_AS_OF = datetime(
    2026, 7, 10, 10, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))
)


class NamedStateFixtureBatch(BaseModel):
    request: CausalBatchRequest
    results: list[CausalEvaluationResult]


def _evidence(
    evidence_id: str,
    layer: str,
    contribution: float,
    *,
    signal_type: str,
    explanation: str,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "evidenceId": evidence_id,
        "layer": layer,
        "signalType": signal_type,
        "contribution": contribution,
        "source": "TrendForge deterministic fixture",
        "sourceDate": DEMO_AS_OF.isoformat(),
        "observedAt": DEMO_AS_OF.isoformat(),
        "trustLevel": "SYNTHETIC_TEST",
        "explanation": explanation,
        "rawInputKeys": [],
    }
    if layer == "CAUSE" and contribution > 0:
        item["causeType"] = "FUNDAMENTAL_RERATING"
    if layer == "SPONSOR" and contribution > 0:
        item["sponsorActor"] = "PROMOTER_INSIDER"
    return item


def _base_candidate(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "direction": "LONG",
        "asOf": DEMO_AS_OF.isoformat(),
        "evaluationMode": "DEMO",
        "evidence": [
            _evidence(
                "cause",
                "CAUSE",
                5,
                signal_type="EARNINGS",
                explanation="Controlled earnings rerating.",
            ),
            _evidence(
                "sponsor",
                "SPONSOR",
                8,
                signal_type="PROMOTER_BUY",
                explanation="Controlled promoter sponsorship.",
            ),
            _evidence(
                "structure",
                "STRUCTURE",
                5,
                signal_type="VCP",
                explanation="Controlled VCP structure.",
            ),
            _evidence(
                "flow",
                "FLOW",
                5,
                signal_type="RVOL_TOD",
                explanation="Controlled time-normalized flow.",
            ),
        ],
        "gates": [
            {
                "code": "G00_DATA_HEALTHY",
                "outcome": "PASS",
                "reason": "Fixture data contract is complete.",
            }
        ],
        "execution": {"score": 14, "triggerActive": True, "gates": []},
    }


def _scenario_candidates() -> list[dict[str, Any]]:
    ready = _base_candidate("TF_READY")

    wait = _base_candidate("TF_WAIT")
    wait["execution"]["triggerActive"] = False

    reject = _base_candidate("TF_REJECT")
    reject["evidence"][0]["contribution"] = 0
    reject["evidence"][1]["contribution"] = 0

    no_trade = _base_candidate("TF_NO_TRADE")
    no_trade["gates"].append(
        {
            "code": "MARKET_REGIME_OVERRIDE",
            "outcome": "HARD_FAIL",
            "reason": "Controlled market-wide NO_TRADE regime.",
            "overrideState": "NO_TRADE",
        }
    )

    stale = _base_candidate("TF_STALE")
    stale["gates"].append(
        {
            "code": "SOURCE_FRESHNESS",
            "outcome": "STALE",
            "reason": "Controlled critical-source staleness.",
        }
    )

    operator = _base_candidate("TF_OPERATOR")
    operator["gates"].append(
        {
            "code": "OPERATOR_PUMP",
            "outcome": "HARD_FAIL",
            "reason": "Controlled low-float operator-pump hard gate.",
        }
    )

    safety = _base_candidate("TF_SAFETY")
    safety["gates"].append(
        {
            "code": "DAILY_LOSS_LOCK",
            "outcome": "HARD_FAIL",
            "reason": "Controlled daily-loss safety lock.",
            "overrideState": "LOCKED_NO_TRADE",
        }
    )

    fomo = _base_candidate("TF_FOMO")
    fomo["gates"].append(
        {
            "code": "FOMO_DISTANCE",
            "outcome": "SOFT_FAIL",
            "reason": "Controlled price extension above one ATR from ideal entry.",
            "overrideState": "WAIT_FOMO",
        }
    )
    return [ready, wait, reject, no_trade, stale, operator, safety, fomo]


def build_named_state_fixture_batch() -> NamedStateFixtureBatch:
    request = CausalBatchRequest.model_validate(
        {"candidates": deepcopy(_scenario_candidates())}
    )
    return NamedStateFixtureBatch(
        request=request, results=evaluate_causal_batch(request)
    )


def _status_group(state: str) -> str:
    if state == "READY":
        return "ready"
    if state in {"REJECT", "NO_TRADE", "LOCKED_NO_TRADE", "STOP_TRADING_NOW"}:
        return "reject"
    return "wait"


def _state_tone(status_group: str) -> str:
    return {"ready": "good", "reject": "bad"}.get(status_group, "warn")


def _radar_payload(result: CausalEvaluationResult) -> dict[str, Any]:
    status_group = _status_group(result.final_state)
    quality = round(100 * result.stage1_score / result.stage1_maximum)
    return {
        "symbol": result.symbol,
        "type": "stock",
        "state": result.final_state,
        "stateTone": _state_tone(status_group),
        "statusGroup": status_group,
        "setup": "Deterministic causal-state fixture",
        "timeframe": ["1d", "15m"],
        "price": "FIXTURE",
        "move": "deterministic demo",
        "reason": " ".join(result.reasons[:2]),
        "decisionTitle": f"{result.final_state} - {result.symbol}",
        "decisionText": "Explicit synthetic scenario for UI and end-to-end validation; never broker executable.",
        "trade": {"entry": "N/A", "stop": "N/A", "target": "N/A"},
        "quality": quality,
        "metrics": [
            {
                "label": "Stage 1",
                "value": f"{result.stage1_score:.2f}/28",
                "note": result.stage1_label,
            },
            {
                "label": "Stage 2",
                "value": f"{result.stage2_score:.2f}/16"
                if result.stage2_score is not None
                else "NOT RUN",
                "note": result.stage2_label,
            },
            {
                "label": "Percentile",
                "value": f"{result.percentile_rank:.2f}",
                "note": "Fixture batch rank",
            },
        ],
        "proof": [
            {
                "label": item.layer.value,
                "value": f"{item.final_score:.2f}/{item.maximum:.0f}",
            }
            for item in result.layer_scores
        ],
        "risk": [
            {"label": "Executable", "value": "NO"},
            {"label": "Data", "value": "SYNTHETIC_TEST"},
        ],
        "sources": [{"label": "Deterministic fixture", "value": "SYNTHETIC_TEST"}],
        "series": [100, 101, 100, 102, 103, 102, 104, 105, 104, 106, 107, 108],
        "gateRatio": round(result.passing_layer_count / 4, 4),
        "falseScreenReason": None
        if result.final_state == "READY"
        else "Controlled non-READY scenario.",
        "dataCutoff": DEMO_AS_OF.isoformat(),
        "outcomeLabel": "UNLABELLED_FIXTURE",
        "causalEvaluation": result.model_dump(mode="json", by_alias=True),
        "demoOnly": True,
        "executable": False,
    }


def load_demo_decision_run() -> dict[str, Any]:
    fixture_batch = build_named_state_fixture_batch()
    run_id = storage.create_scanner_run(
        "DETERMINISTIC_DEMO",
        "demo_named_states",
        {
            "mode": "DETERMINISTIC_DEMO",
            "rule": "Synthetic fixtures cannot unlock broker execution.",
        },
        {"state": "SYNTHETIC_TEST", "asOf": DEMO_AS_OF.isoformat()},
    )
    for result in fixture_batch.results:
        storage.save_gate_decision(
            run_id=str(run_id),
            symbol=result.symbol,
            gate_key="STAGE1_CAUSAL",
            decision="CAN_CONFIRM"
            if result.stage1_label == "ELIGIBLE"
            else "DO_NOT_PASS_READY",
            state=result.stage1_label,
            required_sources=[
                {
                    "source": evidence.source,
                    "sourceDate": evidence.source_date.isoformat(),
                    "trustLevel": evidence.trust_level.value,
                }
                for evidence in result.evidence
            ],
            reasons=result.reasons,
        )
        for gate in result.gates:
            storage.save_gate_decision(
                run_id=str(run_id),
                symbol=result.symbol,
                gate_key=gate.code,
                decision="CAN_CONFIRM"
                if gate.outcome.value == "PASS"
                else "DO_NOT_PASS_READY",
                state=gate.outcome.value,
                required_sources=[],
                reasons=[gate.reason],
            )
        storage.save_scanner_candidate(run_id, _radar_payload(result))

    counts = Counter(result.final_state for result in fixture_batch.results)
    storage.finish_scanner_run(
        run_id, status="COMPLETE", candidate_count=len(fixture_batch.results)
    )
    return {
        "runId": run_id,
        "mode": "DETERMINISTIC_DEMO",
        "candidateCount": len(fixture_batch.results),
        "stateCounts": dict(sorted(counts.items())),
        "dataCutoff": DEMO_AS_OF.isoformat(),
        "executable": False,
    }
