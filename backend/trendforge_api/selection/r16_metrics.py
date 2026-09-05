"""R16 exact-cell metrics, walk-forward evidence, and fail-closed approval."""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from statistics import mean
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .contracts import stable_id
from .r16_pit import R16FrozenHypothesisV1, R16ObservationV1

POLICY_VERSION = "R16_EXACT_CELL_POLICY_V1"
BOOTSTRAP_SEED = 1601
BOOTSTRAP_RESAMPLES = 1000
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class R16FoldResultV1(BaseModel):
    model_config = MODEL_CONFIG

    fold_id: str
    dataset_run_id: str
    exact_cell: str
    fold_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    purge_sessions: int
    embargo_sessions: int
    train_hash: str
    test_hash: str
    test_observation_count: int
    target_incidence: float | None = None
    stop_incidence: float | None = None
    average_net_r: float | None = None


class R16ApprovalV1(BaseModel):
    model_config = MODEL_CONFIG

    ledger_id: str
    dataset_run_id: str
    exact_cell: str = "UNAVAILABLE"
    policy_version: str = POLICY_VERSION
    evidence_hash: str
    actor: str = "R16_POLICY_ENGINE"
    reason: str
    dataset_status: Literal["BUILDING", "READY", "INVALIDATED"] = "BUILDING"
    validation_status: Literal["PIT_NOT_APPROVED", "PIT_APPROVED"] = "PIT_NOT_APPROVED"
    approval_scope: Literal[
        "DATASET_AND_REPLAY", "RESEARCH_DECISION_CONTEXT"
    ] = "DATASET_AND_REPLAY"
    profile_conclusion: Literal[
        "POSITIVE", "NEGATIVE", "INCONCLUSIVE"
    ] = "INCONCLUSIVE"
    promotion_status: Literal["NOT_PROMOTED"] = "NOT_PROMOTED"
    probability_authorized: bool = False
    confirmation_authorized: bool = False
    execution_authorized: bool = False
    blockers: tuple[str, ...] = ()


def _hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _value(
    metrics: Mapping[str, Any], camel: str, snake: str, default: Any = 0
) -> Any:
    return metrics.get(camel, metrics.get(snake, default))


def exact_cell_key(hypothesis: R16FrozenHypothesisV1) -> str:
    return "|".join(
        (
            hypothesis.market,
            hypothesis.instrument_class,
            hypothesis.profile_id,
            hypothesis.profile_version,
            hypothesis.timeframe,
            hypothesis.direction,
            str(hypothesis.horizon_sessions),
            hypothesis.label_policy_version,
            hypothesis.cost_model_version or "NO_COST_POLICY",
            hypothesis.dataset_revision_hash,
        )
    )


def _latest_observations(
    observations: Iterable[R16ObservationV1],
) -> dict[str, R16ObservationV1]:
    latest: dict[str, R16ObservationV1] = {}
    for row in observations:
        current = latest.get(row.hypothesis_id)
        if current is None or (
            row.label_computed_at,
            row.observation_id,
        ) > (
            current.label_computed_at,
            current.observation_id,
        ):
            latest[row.hypothesis_id] = row
    return latest


def _block_bootstrap_interval(
    rows: list[tuple[str, int]],
    *,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> tuple[float | None, float | None, float]:
    by_day: dict[str, list[int]] = defaultdict(list)
    for trading_date, target_hit in rows:
        by_day[trading_date].append(target_hit)
    days = sorted(by_day)
    if len(days) < 2:
        return None, None, 1.0
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(max(200, resamples)):
        sample_days = [rng.choice(days) for _ in days]
        sample = [value for day in sample_days for value in by_day[day]]
        estimates.append(sum(sample) / len(sample) if sample else 0.0)
    estimates.sort()
    low = estimates[int(0.025 * (len(estimates) - 1))]
    high = estimates[int(0.975 * (len(estimates) - 1))]
    return round(low, 6), round(high, 6), round(high - low, 6)


def _average(values: Iterable[float | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return round(mean(present), 6) if present else None


def _sequential_drawdown(rows: list[tuple[str, str, float | None]]) -> float | None:
    values = [item for item in rows if item[2] is not None]
    if not values:
        return None
    equity = 0.0
    peak = 0.0
    worst = 0.0
    for _, _, value in sorted(values):
        equity += float(value)
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return round(worst, 6)


def _folds(
    *,
    dataset_run_id: str,
    exact_cell: str,
    hypotheses: list[R16FrozenHypothesisV1],
    latest: dict[str, R16ObservationV1],
) -> tuple[R16FoldResultV1, ...]:
    dates = sorted({row.trading_date for row in hypotheses if row.geometry_status == "READY"})
    if len(dates) < 120:
        return ()
    holdout_index = max(1, int(len(dates) * 0.80))
    development = dates[:holdout_index]
    horizon = hypotheses[0].horizon_sessions
    embargo = 1
    folds: list[R16FoldResultV1] = []
    for fold_index, train_fraction in enumerate((0.45, 0.60, 0.75), start=1):
        train_end_index = max(1, int(len(development) * train_fraction)) - 1
        test_start_index = train_end_index + horizon + embargo + 1
        if test_start_index >= len(development):
            continue
        remaining = len(development) - test_start_index
        test_size = max(1, remaining // (4 - fold_index))
        test_dates = development[test_start_index : test_start_index + test_size]
        train_dates = development[: train_end_index + 1]
        if not test_dates:
            continue
        test_set = set(test_dates)
        test_rows = [
            latest[row.hypothesis_id]
            for row in hypotheses
            if row.trading_date in test_set and row.hypothesis_id in latest
        ]
        terminal = [row for row in test_rows if row.status in {"TARGET", "STOP"}]
        fold_id = stable_id(
            "r16fold", dataset_run_id, exact_cell, str(fold_index),
            _hash(train_dates), _hash(test_dates),
        )
        folds.append(
            R16FoldResultV1(
                fold_id=fold_id,
                dataset_run_id=dataset_run_id,
                exact_cell=exact_cell,
                fold_index=fold_index,
                train_start=train_dates[0],
                train_end=train_dates[-1],
                test_start=test_dates[0],
                test_end=test_dates[-1],
                purge_sessions=horizon,
                embargo_sessions=embargo,
                train_hash=_hash(train_dates),
                test_hash=_hash(test_dates),
                test_observation_count=len(test_rows),
                target_incidence=(
                    round(sum(row.status == "TARGET" for row in terminal) / len(terminal), 6)
                    if terminal else None
                ),
                stop_incidence=(
                    round(sum(row.status == "STOP" for row in terminal) / len(terminal), 6)
                    if terminal else None
                ),
                average_net_r=_average(row.net_r for row in test_rows),
            )
        )
    return tuple(folds)


def build_metrics(
    *,
    dataset_run_id: str,
    hypotheses: Iterable[R16FrozenHypothesisV1],
    observations: Iterable[R16ObservationV1],
    expected_s8_dates: int,
    available_s8_dates: int,
    calendar_verified: bool,
    source_date_conflict_count: int = 0,
    source_artifact_rejected_count: int = 0,
) -> tuple[tuple[dict[str, Any], ...], tuple[R16FoldResultV1, ...]]:
    hypotheses_all = tuple(hypotheses)
    latest = _latest_observations(observations)
    grouped: dict[str, list[R16FrozenHypothesisV1]] = defaultdict(list)
    for row in hypotheses_all:
        grouped[exact_cell_key(row)].append(row)

    metrics_out: list[dict[str, Any]] = []
    folds_out: list[R16FoldResultV1] = []
    missing_s8_rate = (
        max(0.0, (expected_s8_dates - available_s8_dates) / expected_s8_dates)
        if expected_s8_dates else 1.0
    )
    for cell, cell_hypotheses in sorted(grouped.items()):
        cell_observations = [
            latest[row.hypothesis_id]
            for row in cell_hypotheses
            if row.hypothesis_id in latest
        ]
        counts = Counter(row.status for row in cell_observations)
        eligible = [row for row in cell_hypotheses if row.geometry_status == "READY"]
        resolved = [row for row in cell_observations if row.status in {"TARGET", "STOP"}]
        eligible_count = len(eligible)
        target_count = counts["TARGET"]
        stop_count = counts["STOP"]
        no_hit_count = counts["NO_HIT"]
        censor_count = counts["CENSORED"]
        bootstrap_rows = [
            (
                next(
                    item.trading_date
                    for item in cell_hypotheses
                    if item.hypothesis_id == row.hypothesis_id
                ),
                1 if row.status == "TARGET" else 0,
            )
            for row in cell_observations
            if row.status in {"TARGET", "STOP", "NO_HIT"}
        ]
        low, high, width = _block_bootstrap_interval(bootstrap_rows)
        folds = _folds(
            dataset_run_id=dataset_run_id,
            exact_cell=cell,
            hypotheses=cell_hypotheses,
            latest=latest,
        )
        folds_out.extend(folds)
        average_net = _average(row.net_r for row in cell_observations)
        conclusion = (
            "POSITIVE" if average_net is not None and average_net > 0
            else "NEGATIVE" if average_net is not None and average_net < 0
            else "INCONCLUSIVE"
        )
        observation_set_hash = _hash(
            sorted(row.observation_id for row in cell_observations)
        )
        first = cell_hypotheses[0]
        metric = {
            "metricId": stable_id(
                "r16metric", dataset_run_id, cell, observation_set_hash, POLICY_VERSION
            ),
            "datasetRunId": dataset_run_id,
            "exactCell": cell,
            "datasetRevisionHash": first.dataset_revision_hash,
            "policyVersion": POLICY_VERSION,
            "market": first.market,
            "instrumentClass": first.instrument_class,
            "profileId": first.profile_id,
            "profileVersion": first.profile_version,
            "timeframe": first.timeframe,
            "direction": first.direction,
            "horizonSessions": first.horizon_sessions,
            "labelPolicyVersion": first.label_policy_version,
            "costModelVersion": first.cost_model_version,
            "eligibleDateCount": len({row.trading_date for row in eligible}),
            "eligibleObservationCount": eligible_count,
            "resolvedCount": len(resolved),
            "distinctDateCount": len({row.trading_date for row in eligible}),
            "foldCount": len(folds),
            "holdoutUntouched": len(folds) >= 3,
            "holdoutFraction": 0.20,
            "censorRate": censor_count / eligible_count if eligible_count else 1.0,
            "missingS8Rate": round(missing_s8_rate, 6),
            "calendarVerified": calendar_verified,
            "sourceDateConflictCount": source_date_conflict_count,
            "sourceArtifactRejectedCount": source_artifact_rejected_count,
            "bootstrapLow": low,
            "bootstrapHigh": high,
            "bootstrapWidth": width,
            "bootstrapSeed": BOOTSTRAP_SEED,
            "bootstrapResamples": BOOTSTRAP_RESAMPLES,
            "pointInTimeUniverse": all(
                row.max_input_available_at is None
                or row.max_input_available_at <= row.decision_cutoff_at
                for row in cell_hypotheses
            ),
            "dataReplayIntegrity": all(
                bool(row.source_s8_hash and row.source_s8_lineage_hash)
                for row in cell_hypotheses
            ),
            "observationSetHash": observation_set_hash,
            "targetCount": target_count,
            "stopCount": stop_count,
            "noHitCount": no_hit_count,
            "noEntryCount": counts["NO_ENTRY"],
            "noGeometryCount": counts["NO_GEOMETRY"],
            "censoredCount": censor_count,
            "noForwardSessionCount": counts["NO_FORWARD_SESSION"],
            "dataGapCount": counts["DATA_GAP"],
            "delistedCount": counts["DELISTED"],
            "unresolvedCaCount": counts["CORPORATE_ACTION_UNRESOLVED"],
            "invalidatedBeforeEntryCount": counts["INVALIDATED_BEFORE_ENTRY"],
            "unobservedCount": len(cell_hypotheses) - len(cell_observations),
            "targetIncidence": target_count / eligible_count if eligible_count else None,
            "stopIncidence": stop_count / eligible_count if eligible_count else None,
            "noHitIncidence": no_hit_count / eligible_count if eligible_count else None,
            "resolvedOnlyRate": target_count / len(resolved) if resolved else None,
            "resolvedOnlyRateIsSecondaryDiagnostic": True,
            "averageMfeR": _average(row.mfe_r for row in cell_observations),
            "averageMaeR": _average(row.mae_r for row in cell_observations),
            "averageGrossR": _average(row.gross_r for row in cell_observations),
            "averageNetR": average_net,
            "averageStressedNetR": _average(
                row.stressed_net_r for row in cell_observations
            ),
            "sequentialPaperDrawdownR": _sequential_drawdown(
                [
                    (
                        next(
                            item.trading_date
                            for item in cell_hypotheses
                            if item.hypothesis_id == row.hypothesis_id
                        ),
                        row.symbol,
                        row.net_r,
                    )
                    for row in cell_observations
                ]
            ),
            "profileConclusion": conclusion,
            "probabilityAuthorized": False,
            "confirmationAuthorized": False,
            "executionAuthorized": False,
        }
        total = (
            sum(counts.values())
            + metric["unobservedCount"]
        )
        metric["countsReconcile"] = total == len(cell_hypotheses)
        metric["metricsHash"] = _hash(metric)
        metrics_out.append(metric)
    return tuple(metrics_out), tuple(folds_out)


def evaluate_approval(
    *, metrics: Mapping[str, Any], dataset_run_id: str
) -> R16ApprovalV1:
    blockers: list[str] = []
    checks = (
        (str(_value(metrics, "market", "market", "")) == "NSE_CASH", "WAIT_UNSUPPORTED_MARKET"),
        (str(_value(metrics, "instrumentClass", "instrument_class", "")) == "EQUITY", "WAIT_UNSUPPORTED_INSTRUMENT"),
        (str(_value(metrics, "timeframe", "timeframe", "")) == "EOD", "WAIT_UNSUPPORTED_TIMEFRAME"),
        (int(_value(metrics, "eligibleDateCount", "eligible_date_count")) >= 120, "WAIT_ELIGIBLE_DATES"),
        (int(_value(metrics, "eligibleObservationCount", "eligible_observation_count")) >= 500, "WAIT_ELIGIBLE_OBSERVATIONS"),
        (int(_value(metrics, "resolvedCount", "resolved_count")) >= 100, "WAIT_RESOLVED_OBSERVATIONS"),
        (int(_value(metrics, "distinctDateCount", "distinct_date_count")) >= 30, "WAIT_DISTINCT_DATES"),
        (int(_value(metrics, "foldCount", "fold_count")) >= 3, "WAIT_WALK_FORWARD_FOLDS"),
        (float(_value(metrics, "censorRate", "censor_rate", 1.0)) <= 0.40, "WAIT_CENSOR_RATE"),
        (float(_value(metrics, "missingS8Rate", "missing_s8_rate", 1.0)) <= 0.05, "WAIT_MISSING_S8_RATE"),
        (bool(_value(metrics, "calendarVerified", "calendar_verified", False)), "WAIT_CALENDAR_VERIFICATION"),
        (int(_value(metrics, "sourceDateConflictCount", "source_date_conflict_count", 0)) == 0, "WAIT_S8_DATE_CONFLICT"),
        (int(_value(metrics, "sourceArtifactRejectedCount", "source_artifact_rejected_count", 0)) == 0, "WAIT_S8_ARTIFACT_REJECTED"),
        (float(_value(metrics, "bootstrapWidth", "bootstrap_width", 1.0)) <= 0.20, "WAIT_BOOTSTRAP_PRECISION"),
        (bool(_value(metrics, "holdoutUntouched", "holdout_untouched", False)), "WAIT_UNTOUCHED_HOLDOUT"),
        (bool(_value(metrics, "pointInTimeUniverse", "point_in_time_universe", False)), "WAIT_PIT_UNIVERSE"),
        (bool(_value(metrics, "dataReplayIntegrity", "data_replay_integrity", False)), "WAIT_REPLAY_INTEGRITY"),
        (bool(_value(metrics, "countsReconcile", "counts_reconcile", False)), "WAIT_COUNT_RECONCILIATION"),
        (bool(_value(metrics, "costModelVersion", "cost_model_version", None)), "WAIT_COST_MODEL"),
    )
    for passed, code in checks:
        if not passed:
            blockers.append(code)
    approved = not blockers
    exact_cell = str(_value(metrics, "exactCell", "exact_cell", "UNAVAILABLE"))
    evidence_hash = str(
        _value(metrics, "metricsHash", "metrics_hash", _hash(dict(metrics)))
    )
    conclusion = str(
        _value(metrics, "profileConclusion", "profile_conclusion", "INCONCLUSIVE")
    )
    if conclusion not in {"POSITIVE", "NEGATIVE", "INCONCLUSIVE"}:
        conclusion = "INCONCLUSIVE"
    return R16ApprovalV1(
        ledger_id=stable_id(
            "r16approval", dataset_run_id, exact_cell, POLICY_VERSION,
            evidence_hash, "PIT_APPROVED" if approved else "PIT_NOT_APPROVED",
        ),
        dataset_run_id=dataset_run_id,
        exact_cell=exact_cell,
        evidence_hash=evidence_hash,
        reason=(
            "Exact-cell dataset and replay sufficiency floors passed"
            if approved else "One or more exact-cell integrity or sufficiency floors remain"
        ),
        dataset_status="READY" if approved else "BUILDING",
        validation_status="PIT_APPROVED" if approved else "PIT_NOT_APPROVED",
        profile_conclusion=conclusion,
        blockers=tuple(blockers),
    )


__all__ = [
    "BOOTSTRAP_RESAMPLES",
    "BOOTSTRAP_SEED",
    "POLICY_VERSION",
    "R16ApprovalV1",
    "R16FoldResultV1",
    "build_metrics",
    "evaluate_approval",
    "exact_cell_key",
]