from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from .causal_engine import CausalBatchRequest, DecisionGateInput, evaluate_causal_batch
from .corporate_actions import assess_adjustment_integrity, reconcile_corporate_actions
from .evidence_builder import build_symbol_evidence
from .exchange_calendar import IST, evaluate_nse_calendar, expected_latest_nse_eod_date
from .market_context_ingestion import (
    ContextDataUnavailable,
    build_official_market_context,
    build_official_sector_contexts,
)
from .gate_readiness import gate_readiness, stock_safety_state
from .harmonic_advanced import analyze_harmonic_advanced
from .harmonic_scan_lifecycle import track_detected_harmonic
from .feature_engineering import build_point_in_time_features
from .source_monitor import check_sources
from .source_parser import parse_sources
from .scanner_causal import build_stored_candle_causal_candidate
from .safety_engine import evaluate_safety_status
from .models import GateResult, HarmonicAdvancedAnalysis
from .operational_alerts import (
    emit_context_wait_alert,
    emit_regime_change_alert,
    emit_source_health_alerts,
)
from .storage import (
    create_scanner_run,
    finish_scanner_run,
    get_scheduler_config,
    list_ohlcv_candles,
    list_ohlcv_series,
    list_nse_instruments,
    list_index_constituents,
    list_corporate_event_observations,
    list_scanner_candidates,
    list_scanner_runs,
    save_gate_decision,
    save_evidence_claims,
    save_scanner_candidate,
    save_scheduler_config,
    latest_market_context_snapshot,
    latest_sector_context_snapshot,
)


CRITICAL_SOURCE_KEYS = [
    "nse_bhavcopy_eod",
    "nse_index_close_eod",
    "nse_fno_ban",
    "nse_large_deals",
    "nse_participant_oi",
    "nse_fii_dii",
    "amfi_monthly_portfolio",
    "cftc_cot",
    "mcx_bhavcopy",
]


UNIVERSE_LIMITS = {
    "WATCHLIST_ONLY": 5,
    "NIFTY50_SMOKE": 50,
    "NIFTY200_LIQUID": 25,
    "NIFTY500_PLUS_FNO": 50,
}


def _runtime_context_gate(
    snapshot: dict[str, Any] | None,
    *,
    current: datetime,
    label: str,
    stale_after_hours: int = 36,
) -> tuple[str, str, str | None]:
    if snapshot is None:
        return "WAIT", f"{label} context is unavailable.", "WAIT_DATA_WEAK"
    try:
        source_date = datetime.fromisoformat(
            str(snapshot["sourceDate"]).replace("Z", "+00:00")
        )
    except (KeyError, ValueError):
        return (
            "HARD_FAIL",
            f"{label} context lacks a valid source date.",
            "WAIT_DATA_WEAK",
        )
    if source_date.utcoffset() is None or source_date > current:
        return (
            "HARD_FAIL",
            f"{label} context violates point-in-time ordering.",
            "WAIT_DATA_WEAK",
        )
    if current - source_date > timedelta(hours=stale_after_hours):
        expected_eod = (
            expected_latest_nse_eod_date(current)
            if label in {"Market", "Sector"}
            else None
        )
        source_ist_date = source_date.astimezone(IST).date()
        if expected_eod is None or source_ist_date != expected_eod:
            return (
                "STALE",
                f"{label} context is stale at scanner runtime.",
                "WAIT_DATA_WEAK",
            )
    outcome = str(snapshot.get("gateOutcome") or "WAIT")
    if outcome not in {"PASS", "SOFT_FAIL", "WAIT", "HARD_FAIL", "STALE"}:
        return (
            "HARD_FAIL",
            f"{label} context has an invalid gate outcome.",
            "WAIT_DATA_WEAK",
        )
    override = "NO_TRADE" if label == "Market" and outcome == "HARD_FAIL" else None
    return (
        outcome,
        str(snapshot.get("reason") or f"{label} context evaluated."),
        override,
    )


class ScannerScheduler:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._run_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.running = False
        self.interval_seconds = 900
        self.last_run_at: str | None = None
        self.last_run_id: int | None = None
        self.last_status = "IDLE"
        self.last_error: str | None = None

    def status(self) -> dict[str, Any]:
        runs = list_scanner_runs(limit=1)
        calendar = evaluate_nse_calendar()
        return {
            "running": self.running,
            "intervalSeconds": self.interval_seconds,
            "lastRunAt": self.last_run_at,
            "lastRunId": self.last_run_id,
            "lastStatus": self.last_status,
            "lastError": self.last_error,
            "latestRun": runs[0] if runs else None,
            "calendar": calendar,
        }

    def run_once(
        self,
        *,
        universe: str = "WATCHLIST_ONLY",
        fetch: bool = False,
        trigger: str = "manual",
    ) -> dict[str, Any]:
        if universe not in UNIVERSE_LIMITS:
            return {
                "runId": None,
                "status": "REJECT_INVALID_UNIVERSE",
                "candidateCount": 0,
                "universe": universe,
            }
        calendar = evaluate_nse_calendar()
        if trigger == "scheduler" and not calendar["canRunScheduledScan"]:
            self.last_run_at = datetime.now(timezone.utc).isoformat()
            self.last_status = str(calendar["state"])
            self.last_error = None
            return {
                "runId": None,
                "status": calendar["state"],
                "candidateCount": 0,
                "universe": universe,
                "calendar": calendar,
            }
        if not self._run_lock.acquire(blocking=False):
            return {
                "runId": None,
                "status": "SKIPPED_ALREADY_RUNNING",
                "candidateCount": 0,
                "universe": universe,
            }
        try:
            return self._run_once(universe=universe, fetch=fetch, trigger=trigger)
        finally:
            self._run_lock.release()

    def _run_once(self, *, universe: str, fetch: bool, trigger: str) -> dict[str, Any]:
        started = datetime.now(timezone.utc).isoformat()
        calendar = evaluate_nse_calendar()
        run_id: int | None = None
        try:
            monitor_summary = check_sources(
                CRITICAL_SOURCE_KEYS, fetch=fetch, timeout_seconds=20
            )
            parse_results = parse_sources(CRITICAL_SOURCE_KEYS)
            emit_source_health_alerts(monitor_summary, parse_results)
            gates = gate_readiness()
            safety = evaluate_safety_status()
            context_now = datetime.now(timezone.utc)
            previous_market_context = latest_market_context_snapshot()
            context_build_errors: list[str] = []
            try:
                build_official_market_context(as_of=context_now)
            except ContextDataUnavailable as exc:
                context_build_errors.append(str(exc))
            try:
                build_official_sector_contexts(as_of=context_now)
            except ContextDataUnavailable as exc:
                context_build_errors.append(str(exc))
            emit_context_wait_alert(context_build_errors)
            market_context = latest_market_context_snapshot()
            if market_context is not None:
                emit_regime_change_alert(previous_market_context, market_context)
            market_outcome, market_reason, market_override = _runtime_context_gate(
                market_context, current=context_now, label="Market"
            )
            run_id = create_scanner_run(
                universe,
                trigger,
                gates,
                {
                    "monitor": monitor_summary.model_dump(mode="json", by_alias=True),
                    "parseResults": [
                        row.model_dump(mode="json", by_alias=True)
                        for row in parse_results
                    ],
                    "contextBuildErrors": context_build_errors,
                },
            )
            save_gate_decision(
                run_id=str(run_id),
                symbol=None,
                gate_key="EXCHANGE_CALENDAR",
                decision="CAN_CONFIRM"
                if calendar["isTradingDay"]
                else "RESEARCH_ONLY_MANUAL_OVERRIDE",
                state=str(calendar["state"]),
                required_sources=[{"sourceKey": "nse_trading_calendar"}],
                reasons=[str(calendar["reason"])],
            )
            gate_rows = gates.get("gates", [])
            global_stock_safety = next(
                (gate for gate in gate_rows if gate.get("code") == "G03_STOCK_SAFETY"),
                None,
            )
            for gate in gate_rows:
                save_gate_decision(
                    run_id=str(run_id),
                    symbol=None,
                    gate_key=gate.get("code", "UNKNOWN_GATE"),
                    decision=gate.get("tradeGateEffect", "DO_NOT_PASS_READY"),
                    state=gate.get("state", "UNKNOWN"),
                    required_sources=gate.get("sources", []),
                    reasons=[gate.get("reason", "No reason saved.")],
                )
            critical_broken = any(
                row.get("state") == "BLOCKED_SOURCE_BROKEN" for row in gate_rows
            )
            blocked = any(
                row.get("tradeGateEffect") != "CAN_CONFIRM" for row in gate_rows
            )
            save_gate_decision(
                run_id=str(run_id),
                symbol=None,
                gate_key="TRADER_SAFETY",
                decision="CAN_CONFIRM"
                if safety.state == "GREEN"
                else "DO_NOT_PASS_READY",
                state=safety.state,
                required_sources=[],
                reasons=[safety.reason],
            )
            save_gate_decision(
                run_id=str(run_id),
                symbol=None,
                gate_key="MARKET_CONTEXT",
                decision="CAN_CONFIRM"
                if market_outcome == "PASS"
                else "DO_NOT_PASS_READY",
                state=str(market_context.get("state"))
                if market_context
                else "WAIT_DATA_WEAK",
                required_sources=[
                    {"sourceKey": "nse_bhavcopy_eod"},
                    {"sourceKey": "nse_participant_oi"},
                ],
                reasons=[market_reason],
            )
            if critical_broken:
                finish_scanner_run(
                    run_id,
                    status="PAUSED",
                    candidate_count=0,
                    paused_reason="critical_source_broken",
                )
                self._remember(run_id, "PAUSED", started, None)
                return {
                    "runId": run_id,
                    "status": "PAUSED",
                    "candidateCount": 0,
                    "pausedReason": "critical_source_broken",
                }

            limit = UNIVERSE_LIMITS.get(universe, UNIVERSE_LIMITS["WATCHLIST_ONLY"])
            available = list_ohlcv_series(min_candles=40, limit=max(limit * 4, limit))
            if universe != "WATCHLIST_ONLY":
                available = [
                    row for row in available if row["timeframe"] in {"1d", "1w"}
                ]
            if universe == "NIFTY50_SMOKE":
                official_members = {
                    str(row["symbol"])
                    for row in list_index_constituents("NIFTY50", limit=100)
                }
                available = [
                    row for row in available if row["symbol"] in official_members
                ]
            selected = []
            seen_symbols: set[str] = set()
            for row in available:
                if row["symbol"] in seen_symbols:
                    continue
                selected.append(row)
                seen_symbols.add(row["symbol"])
                if len(selected) >= limit:
                    break
            prepared = []
            for series in selected:
                candles = list_ohlcv_candles(
                    series["symbol"],
                    series["timeframe"],
                    source=series["source"],
                    limit=5000,
                )
                candle_cutoff = datetime.fromisoformat(
                    candles[-1].timestamp.replace("Z", "+00:00")
                )
                action_rows = list_corporate_event_observations(symbol=series["symbol"])
                reconciled_actions = reconcile_corporate_actions(
                    action_rows, as_of=candle_cutoff
                )
                adjustment_integrity = assess_adjustment_integrity(
                    candles, reconciled_actions
                )
                if adjustment_integrity.state == "PASS":
                    analysis = analyze_harmonic_advanced(
                        candles, series["symbol"], series["timeframe"]
                    )
                else:
                    analysis = HarmonicAdvancedAnalysis(
                        symbol=series["symbol"],
                        timeframe=series["timeframe"],
                        candleCount=len(candles),
                        pivots=[],
                        validations=[],
                        gates=[
                            GateResult(
                                code="G00_DATA_HEALTHY",
                                name="Corporate-action adjustment integrity",
                                result="FAIL",
                                weight=3,
                                reason=adjustment_integrity.reason,
                            )
                        ],
                        hybridQualityScore=0,
                        gateRatio=0,
                        finalState="REJECT_DATA_INTEGRITY",
                        lifecycleState="FORMING",
                        alerts=[adjustment_integrity.reason],
                    )
                lifecycle_tracking = track_detected_harmonic(
                    candles,
                    analysis,
                    source=series["source"],
                    trust_level=series["trust_level"],
                )
                features = build_point_in_time_features(candles)
                evidence_as_of = datetime.now(timezone.utc)
                external_evidence = build_symbol_evidence(
                    series["symbol"], as_of=evidence_as_of
                )
                save_evidence_claims(
                    series["symbol"],
                    [
                        item.model_dump(mode="json", by_alias=True)
                        for item in external_evidence
                    ],
                )
                causal_candidate = build_stored_candle_causal_candidate(
                    symbol=series["symbol"],
                    candles=candles,
                    analysis=analysis,
                    features=features,
                    source_gates_blocked=blocked,
                    external_evidence=external_evidence,
                )
                symbol_safety = stock_safety_state(
                    series["symbol"],
                    global_stock_safety.get("sources") if global_stock_safety else None,
                )
                safety_state = str(symbol_safety["state"])
                causal_candidate.gates.append(
                    DecisionGateInput.model_validate(
                        {
                            "code": "STOCK_SURVEILLANCE",
                            "outcome": "PASS"
                            if safety_state == "PASS"
                            else "HARD_FAIL"
                            if safety_state == "BLOCKED_SURVEILLANCE"
                            else "WAIT",
                            "reason": str(symbol_safety["reason"]),
                        }
                    )
                )
                causal_candidate.gates.append(
                    DecisionGateInput.model_validate(
                        {
                            "code": "MARKET_CONTEXT",
                            "outcome": market_outcome,
                            "reason": market_reason,
                            "overrideState": market_override,
                        }
                    )
                )
                instrument_rows = list_nse_instruments(
                    symbol=series["symbol"],
                    as_of=candle_cutoff.date().isoformat(),
                    limit=1,
                )
                sector = instrument_rows[0].get("industry") if instrument_rows else None
                sector_context = (
                    latest_sector_context_snapshot(sector=sector, direction="LONG")
                    if sector
                    else None
                )
                sector_outcome, sector_reason, _ = _runtime_context_gate(
                    sector_context, current=context_now, label="Sector"
                )
                causal_candidate.gates.append(
                    DecisionGateInput.model_validate(
                        {
                            "code": "SECTOR_CONTEXT",
                            "outcome": sector_outcome,
                            "reason": sector_reason,
                        }
                    )
                )
                if safety.state != "GREEN":
                    if safety.state in {"LOCKED_NO_TRADE", "STOP_TRADING_NOW"}:
                        outcome = "HARD_FAIL"
                        override = safety.state
                    elif safety.state == "RISK_REDUCED":
                        outcome = "SOFT_FAIL"
                        override = None
                    else:
                        outcome = "WAIT"
                        override = "WAIT_EMOTIONAL_RISK"
                    causal_candidate.gates.append(
                        DecisionGateInput.model_validate(
                            {
                                "code": "TRADER_SAFETY",
                                "outcome": outcome,
                                "reason": safety.reason,
                                "overrideState": override,
                            }
                        )
                    )
                prepared.append(
                    (
                        series,
                        candles,
                        analysis,
                        features,
                        causal_candidate,
                        lifecycle_tracking,
                        adjustment_integrity,
                        sector,
                        sector_context,
                        sector_outcome,
                        sector_reason,
                        symbol_safety,
                    )
                )

            causal_results = (
                {
                    result.symbol: result
                    for result in evaluate_causal_batch(
                        CausalBatchRequest(candidates=[item[4] for item in prepared])
                    )
                }
                if prepared
                else {}
            )
            saved = 0
            for (
                series,
                candles,
                analysis,
                features,
                _,
                lifecycle_tracking,
                adjustment_integrity,
                sector,
                sector_context,
                sector_outcome,
                sector_reason,
                symbol_safety,
            ) in prepared:
                causal = causal_results[series["symbol"]]
                best = analysis.validations[0] if analysis.validations else None
                original_state = analysis.final_state
                rejected = original_state.startswith("REJECT")
                final_state = original_state if rejected else causal.final_state
                if safety.state in {"LOCKED_NO_TRADE", "STOP_TRADING_NOW"}:
                    final_state = safety.state
                elif adjustment_integrity.state != "PASS":
                    final_state = "REJECT_DATA_INTEGRITY"
                elif market_outcome == "HARD_FAIL":
                    final_state = "NO_TRADE"
                elif sector_outcome == "HARD_FAIL":
                    final_state = "REJECT"
                elif symbol_safety["state"] == "BLOCKED_SURVEILLANCE":
                    final_state = "REJECT"
                elif safety.state in {"COOLDOWN_ACTIVE", "WAIT_EMOTIONAL_RISK"}:
                    final_state = "WAIT_EMOTIONAL_RISK"
                elif (
                    lifecycle_tracking.status
                    in {
                        "WAIT_TIMEZONE",
                        "WAIT_LEVELS",
                        "WAIT_CHRONOLOGY",
                        "CONFLICT_DATA_REVISION",
                    }
                    or market_outcome in {"WAIT", "STALE"}
                    or sector_outcome
                    in {
                        "WAIT",
                        "STALE",
                    }
                    or symbol_safety["state"] != "PASS"
                ):
                    final_state = "WAIT_DATA_WEAK"
                status_group = (
                    "reject"
                    if rejected
                    or final_state
                    in {"REJECT", "NO_TRADE", "LOCKED_NO_TRADE", "STOP_TRADING_NOW"}
                    else "wait"
                )
                save_gate_decision(
                    run_id=str(run_id),
                    symbol=series["symbol"],
                    gate_key="G03_STOCK_SAFETY",
                    decision="CAN_CONFIRM"
                    if symbol_safety["state"] == "PASS"
                    else "DO_NOT_PASS_READY",
                    state=str(symbol_safety["state"]),
                    required_sources=list(symbol_safety["sources"])
                    if isinstance(symbol_safety["sources"], list)
                    else [],
                    reasons=[str(symbol_safety["reason"])],
                )
                save_gate_decision(
                    run_id=str(run_id),
                    symbol=series["symbol"],
                    gate_key="STAGE1_CAUSAL",
                    decision="CAN_CONFIRM"
                    if causal.stage1_label == "ELIGIBLE"
                    else "DO_NOT_PASS_READY",
                    state=causal.stage1_label,
                    required_sources=[],
                    reasons=causal.reasons,
                )
                save_gate_decision(
                    run_id=str(run_id),
                    symbol=series["symbol"],
                    gate_key="HARMONIC_LIFECYCLE",
                    decision="CAN_CONFIRM"
                    if lifecycle_tracking.status in {"TRACKED", "NOT_APPLICABLE"}
                    else "DO_NOT_PASS_READY",
                    state=lifecycle_tracking.status,
                    required_sources=[],
                    reasons=[lifecycle_tracking.reason],
                )
                save_gate_decision(
                    run_id=str(run_id),
                    symbol=series["symbol"],
                    gate_key="CORPORATE_ACTION_INTEGRITY",
                    decision="CAN_CONFIRM"
                    if adjustment_integrity.state == "PASS"
                    else "DO_NOT_PASS_READY",
                    state=adjustment_integrity.state,
                    required_sources=[{"sourceKey": "nse_corporate_filings_actions"}],
                    reasons=[adjustment_integrity.reason],
                )
                save_gate_decision(
                    run_id=str(run_id),
                    symbol=series["symbol"],
                    gate_key="TRADER_SAFETY",
                    decision="CAN_CONFIRM"
                    if safety.state == "GREEN"
                    else "DO_NOT_PASS_READY",
                    state=safety.state,
                    required_sources=[],
                    reasons=[safety.reason],
                )
                save_gate_decision(
                    run_id=str(run_id),
                    symbol=series["symbol"],
                    gate_key="MARKET_CONTEXT",
                    decision="CAN_CONFIRM"
                    if market_outcome == "PASS"
                    else "DO_NOT_PASS_READY",
                    state=str(market_context.get("state"))
                    if market_context
                    else "WAIT_DATA_WEAK",
                    required_sources=[{"sourceKey": "nse_bhavcopy_eod"}],
                    reasons=[market_reason],
                )
                save_gate_decision(
                    run_id=str(run_id),
                    symbol=series["symbol"],
                    gate_key="SECTOR_CONTEXT",
                    decision="CAN_CONFIRM"
                    if sector_outcome == "PASS"
                    else "DO_NOT_PASS_READY",
                    state=str(sector_context.get("rrgState"))
                    if sector_context
                    else "WAIT_DATA_WEAK",
                    required_sources=[{"sourceKey": "nse_nifty500_constituents"}],
                    reasons=[sector_reason],
                )
                payload = {
                    "symbol": series["symbol"],
                    "type": "harmonic",
                    "state": final_state,
                    "originalState": original_state,
                    "statusGroup": status_group,
                    "stateTone": "bad" if status_group == "reject" else "warn",
                    "setup": f"{best.pattern_name if best else 'No valid harmonic'} stored-candle research scan",
                    "timeframe": [series["timeframe"]],
                    "price": f"{candles[-1].close:.2f}" if candles else "WAIT",
                    "move": "stored EOD research",
                    "reason": " ".join(causal.reasons[:2]),
                    "decisionTitle": f"{final_state} - CAUSAL GATES",
                    "decisionText": "Stored-candle structure and flow cannot bypass missing CAUSE, SPONSOR, or official confirmation.",
                    "trade": {"entry": "-", "stop": "-", "target": "-"},
                    "quality": round(analysis.hybrid_quality_score * 100),
                    "gateRatio": analysis.gate_ratio,
                    "metrics": [
                        {
                            "label": "Pattern",
                            "value": best.pattern_name if best else "NONE",
                            "note": original_state,
                        },
                        {
                            "label": "Data Trust",
                            "value": series["trust_level"],
                            "note": series["source"],
                        },
                        {
                            "label": "ASM/GSM Safety",
                            "value": str(symbol_safety["state"]),
                            "note": str(symbol_safety["reason"]),
                        },
                        {
                            "label": "Corporate Actions",
                            "value": adjustment_integrity.state,
                            "note": adjustment_integrity.reason,
                        },
                        {
                            "label": "Trader Safety",
                            "value": safety.state,
                            "note": safety.reason,
                        },
                        {
                            "label": "Market Regime",
                            "value": str(market_context.get("state"))
                            if market_context
                            else "WAIT_DATA_WEAK",
                            "note": market_reason,
                        },
                        {
                            "label": "Sector RRG",
                            "value": str(sector_context.get("rrgState"))
                            if sector_context
                            else "WAIT_DATA_WEAK",
                            "note": sector_reason,
                        },
                        {
                            "label": "Stage 1",
                            "value": f"{causal.stage1_score:.2f}/28",
                            "note": causal.stage1_label,
                        },
                        {
                            "label": "Stage 2",
                            "value": f"{causal.stage2_score:.2f}/16"
                            if causal.stage2_score is not None
                            else "BLOCKED",
                            "note": causal.stage2_label,
                        },
                    ],
                    "proof": [
                        {
                            "label": layer.layer.value,
                            "value": f"{layer.final_score:.2f}/{layer.maximum:.0f}",
                        }
                        for layer in causal.layer_scores
                    ]
                    + [
                        {"label": gate.code, "value": gate.result}
                        for gate in analysis.gates
                    ],
                    "risk": [
                        {"label": "Executable", "value": "NO"},
                        {
                            "label": "Adjustment Events",
                            "value": str(adjustment_integrity.required_action_count),
                        },
                    ],
                    "sources": [
                        {"label": series["source"], "value": series["trust_level"]}
                    ],
                    "series": [round(candle.close) for candle in candles[-24:]],
                    "falseScreenReason": str(symbol_safety["reason"])
                    if symbol_safety["state"] != "PASS"
                    else "Structured official source gates are not all fresh and passing."
                    if blocked
                    else "Stored-data research scanner never emits executable READY.",
                    "dataCutoff": series["last_timestamp"],
                    "sourceFetchedAt": series["last_fetched_at"],
                    "features": features,
                    "patternKey": lifecycle_tracking.pattern_key,
                    "harmonicLifecycle": lifecycle_tracking.model_dump(
                        mode="json", by_alias=True
                    ),
                    "corporateActionIntegrity": adjustment_integrity.model_dump(
                        mode="json", by_alias=True
                    ),
                    "safety": safety.model_dump(mode="json", by_alias=True),
                    "marketContext": market_context
                    or {
                        "state": "WAIT_DATA_WEAK",
                        "gateOutcome": market_outcome,
                        "reason": market_reason,
                    },
                    "sectorContext": sector_context
                    or {
                        "sector": sector or "UNKNOWN",
                        "gateOutcome": sector_outcome,
                        "reason": sector_reason,
                    },
                    "causalEvaluation": causal.model_dump(mode="json", by_alias=True),
                    "executable": False,
                }
                save_scanner_candidate(run_id, payload)
                saved += 1
            finish_scanner_run(
                run_id,
                status="COMPLETE",
                candidate_count=saved,
                paused_reason="source_gates_blocked" if blocked else None,
            )
            self._remember(run_id, "COMPLETE", started, None)
            return {
                "runId": run_id,
                "status": "COMPLETE",
                "candidateCount": saved,
                "sourceGatesBlocked": blocked,
                "universe": universe,
                "processedSeries": len(selected),
            }
        except Exception as exc:  # pragma: no cover - scheduler boundary
            if run_id is not None:
                finish_scanner_run(
                    run_id,
                    status="ERROR",
                    candidate_count=0,
                    paused_reason=f"{type(exc).__name__}: {exc}",
                )
            self.last_error = str(exc)
            self.last_status = "ERROR"
            return {
                "runId": run_id,
                "status": "ERROR",
                "candidateCount": 0,
                "error": str(exc),
            }

    def start(
        self,
        *,
        interval_seconds: int = 900,
        universe: str = "WATCHLIST_ONLY",
        fetch: bool = False,
    ) -> dict[str, Any]:
        if universe not in UNIVERSE_LIMITS:
            raise ValueError(f"Unsupported universe: {universe}")
        with self._lock:
            if self.running:
                return self.status()
            self.interval_seconds = interval_seconds
            self._stop.clear()
            self.running = True
            self._thread = threading.Thread(
                target=self._loop, args=(universe, fetch), daemon=True
            )
            self._thread.start()
            save_scheduler_config(
                "scanner",
                enabled=True,
                interval_seconds=interval_seconds,
                universe=universe,
                fetch=fetch,
            )
            return self.status()

    def stop(self, *, persist: bool = True) -> dict[str, Any]:
        with self._lock:
            self._stop.set()
            self.running = False
            if persist:
                save_scheduler_config(
                    "scanner",
                    enabled=False,
                    interval_seconds=self.interval_seconds,
                    universe="WATCHLIST_ONLY",
                    fetch=False,
                )
            return self.status()

    def restore(self) -> dict[str, Any]:
        config = get_scheduler_config("scanner")
        if not config or not config.get("enabled"):
            return self.status()
        return self.start(
            interval_seconds=int(config["interval_seconds"]),
            universe=str(config["universe"]),
            fetch=bool(config["fetch"]),
        )

    def _loop(self, universe: str, fetch: bool) -> None:
        while not self._stop.is_set():
            self.run_once(universe=universe, fetch=fetch, trigger="scheduler")
            self._stop.wait(self.interval_seconds)
        self.running = False

    def _remember(
        self, run_id: int, status: str, started: str, error: str | None
    ) -> None:
        self.last_run_id = run_id
        self.last_run_at = started
        self.last_status = status
        self.last_error = error


SCANNER_SCHEDULER = ScannerScheduler()


def scanner_runs(limit: int = 100) -> list[dict[str, Any]]:
    return list_scanner_runs(limit=limit)


def scanner_candidates(
    run_id: int | None = None, limit: int = 200
) -> list[dict[str, Any]]:
    return list_scanner_candidates(run_id=run_id, limit=limit)
