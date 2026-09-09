"""R16 immutable multi-date replay worker and read-only API projections."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from .. import storage
from ..exchange_calendar import evaluate_nse_calendar
from ..r16_retention import freeze_s8_hypotheses, resume_pending_publications, verified_record
from .cash_a4_history import list_raw_bars_by_symbol
from .contracts import stable_id
from .r16_metrics import POLICY_VERSION, build_metrics, evaluate_approval
from .r16_pit import (
    COST_POLICY_VERSION,
    GEOMETRY_POLICY_VERSION,
    LABEL_POLICY_VERSION,
    PROFILE_ID,
    PROFILE_VERSION,
    R16FrozenHypothesisV1,
    R16ObservationV1,
    R16RevisionV1,
    label_hypothesis,
    validate_s8_contract,
)
from .r16_store import (
    acquire_worker_lease,
    list_approvals,
    list_dataset_runs,
    list_hypotheses,
    list_latest_observations,
    list_metrics,
    list_observations,
    page_dataset_runs,
    page_observations,
    persist_approval,
    persist_dataset_run,
    persist_fold,
    persist_hypotheses,
    persist_metric,
    persist_observations,
    persist_revisions,
    r16_schema_status,
    release_worker_lease,
    save_worker_checkpoint,
    worker_state,
)
from .s8_persist_run import PROFILE_ID as S8_PROFILE_ID
from .store import list_latest_selection_payloads

CONTRACT = "trendforge.r16-service.v2"
DATA_POLICY_VERSION = "R16_NSE_CASH_EOD_EXACT_PARENT_V2"
TERMINAL_STATUSES = frozenset(
    {
        "TARGET", "STOP", "NO_HIT", "NO_ENTRY", "NO_GEOMETRY",
        "DATA_GAP", "DELISTED", "CORPORATE_ACTION_UNRESOLVED",
        "INVALIDATED_BEFORE_ENTRY",
        "AMBIGUOUS", "EXPIRED",
    }
)
ReplayMode = Literal["incremental", "catch_up", "replay", "rebuild"]


def _hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _bar_payload(bar: Any) -> dict[str, Any]:
    if isinstance(bar, dict):
        return dict(bar)
    return {
        "trade_date": bar.trade_date.isoformat(),
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "artifact_hash": bar.artifact_hash,
    }


def _revision_hash(rebuild_reason: str | None) -> str:
    return _hash(
        {
            "dataPolicy": DATA_POLICY_VERSION,
            "profileId": PROFILE_ID,
            "profileVersion": PROFILE_VERSION,
            "geometryPolicy": GEOMETRY_POLICY_VERSION,
            "labelPolicy": LABEL_POLICY_VERSION,
            "costPolicy": COST_POLICY_VERSION,
            "metricsPolicy": POLICY_VERSION,
            "rebuildReason": rebuild_reason,
        }
    )


def _s8_identity(payload: dict[str, Any]) -> tuple[str, date, datetime, str]:
    run_id = str(payload.get("runId") or payload.get("run_id") or "")
    trading_day = _parse_date(payload.get("tradingDate") or payload.get("trading_date"))
    cutoff = _parse_datetime(payload.get("asOf") or payload.get("as_of"))
    if not run_id or trading_day is None or cutoff is None:
        raise ValueError("WAIT_R16_S8_IDENTITY_INCOMPLETE")
    return run_id, trading_day, cutoff, _hash(payload)


def _select_s8_history(
    payloads: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    """Choose one immutable payload per date; conflicting dates are excluded."""

    by_date: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
    rejected: list[dict[str, str]] = []
    for payload in payloads:
        try:
            run_id, trading_day, _, content_hash = _s8_identity(payload)
            validate_s8_contract(payload)
        except ValueError as exc:
            rejected.append(
                {"runId": str(payload.get("runId") or "UNKNOWN"), "reason": str(exc)}
            )
            continue
        by_date.setdefault(trading_day.isoformat(), []).append(
            (content_hash, run_id, payload)
        )

    selected: list[dict[str, Any]] = []
    conflicts = 0
    for trading_day, rows in sorted(by_date.items()):
        if len({item[0] for item in rows}) > 1:
            conflicts += 1
            rejected.extend(
                {
                    "runId": run_id,
                    "reason": f"WAIT_R16_S8_DATE_CONFLICT:{trading_day}",
                }
                for _, run_id, _ in rows
            )
            continue
        selected.append(sorted(rows, key=lambda item: item[1])[-1][2])
    return selected, rejected, conflicts


def _calendar_window(trading_dates: list[date]) -> tuple[int, bool]:
    if not trading_dates:
        return 0, False
    cursor = min(trading_dates)
    end = max(trading_dates)
    expected = 0
    verified = True
    while cursor <= end:
        state = evaluate_nse_calendar(cursor, segment="CM")
        if state.get("state") == "WAIT_CALENDAR_DATA":
            verified = False
        elif state.get("isTradingDay"):
            expected += 1
        cursor += timedelta(days=1)
    return (expected, True) if verified else (len(set(trading_dates)), False)


def _dataset_payload(
    *,
    s8_payload: dict[str, Any],
    revision_hash: str,
    hypotheses: tuple[R16FrozenHypothesisV1, ...],
) -> dict[str, Any]:
    run_id, trading_day, cutoff, s8_hash = _s8_identity(s8_payload)
    dataset_run_id = stable_id(
        "r16dataset", revision_hash, run_id, s8_hash, PROFILE_VERSION, POLICY_VERSION
    )
    return {
        "contract": CONTRACT,
        "runId": dataset_run_id,
        "profileId": PROFILE_ID,
        "profileVersion": PROFILE_VERSION,
        "market": "NSE_CASH",
        "horizon": "SWING",
        "tradingDate": trading_day.isoformat(),
        "cutoffAt": cutoff.isoformat(),
        "sourceS8RunId": run_id,
        "sourceS8Hash": s8_hash,
        "universeHash": _hash(sorted({row.symbol for row in hypotheses})),
        "datasetRevisionHash": revision_hash,
        "datasetStatus": "BUILDING",
        "policyVersion": POLICY_VERSION,
        "hypothesisCount": len(hypotheses),
        "scope": "NSE_CASH_EOD_ONLY",
        "probabilityAuthorized": False,
        "confirmationAuthorized": False,
        "executionAuthorized": False,
    }


def _status_without_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract": CONTRACT,
        "datasetStatus": "BUILDING",
        "validationStatus": "PIT_NOT_APPROVED",
        "approvalScope": "DATASET_AND_REPLAY",
        "profileConclusion": "INCONCLUSIVE",
        "promotionStatus": "NOT_PROMOTED",
        "probabilityAuthorized": False,
        "confirmationAuthorized": False,
        "executionAuthorized": False,
        "blockers": ["WAIT_R16_SCHEMA_NOT_APPLIED"],
        "schema": schema,
        "latestDatasetRunId": None,
        "worker": None,
    }


def _link_rebuild_versions(hypotheses: list[R16FrozenHypothesisV1], reason: str) -> int:
    """Link an explicit reinterpretation to the exact original policy version.

    This is not a latest-decision lookup. A missing original is not fabricated;
    the new initial hypothesis already has its exact S8 parent.
    """
    original_revision = _revision_hash(None)
    keys = ("sourceS8RunId", "sourceS8Hash", "candidateId", "direction", "horizonSessions")
    originals = {
        tuple(row[key] for key in keys): row
        for row in list_hypotheses(limit=500000)
        if row.get("datasetRevisionHash") == original_revision
    }
    original_runs = {
        (row["sourceS8RunId"], row["sourceS8Hash"]): row["runId"]
        for row in list_dataset_runs(limit=500000)
        if row.get("datasetRevisionHash") == original_revision
    }
    inserted = 0
    for hypothesis in hypotheses:
        payload = hypothesis.model_dump(mode="json", by_alias=True)
        previous = originals.get(tuple(payload[key] for key in keys))
        if previous is None or previous["hypothesisId"] == hypothesis.hypothesis_id:
            continue
        conn = storage.connect()
        try:
            _, _, publication = verified_record(conn, "DECISION_VERSION", hypothesis.hypothesis_id)
        finally:
            conn.close()
        revision = R16RevisionV1(
            revision_id=stable_id("r16reinterpretation", previous["hypothesisId"], hypothesis.hypothesis_id),
            hypothesis_id=previous["hypothesisId"], predecessor_type="DECISION_VERSION",
            predecessor_id=previous["hypothesisId"], predecessor_hash=_hash(previous),
            revision_kind="INTERPRETATION", recorded_at=publication.created_at, reason=reason,
            replacement_hypothesis_id=hypothesis.hypothesis_id, replacement_hypothesis_hash=_hash(payload),
            changes={"datasetRevisionHash": hypothesis.dataset_revision_hash},
            evidence_hashes=hypothesis.source_bar_hashes,
        )
        dataset_run_id = original_runs[(hypothesis.source_s8_run_id, hypothesis.source_s8_hash)]
        inserted += persist_revisions(dataset_run_id, [revision.model_dump(mode="json", by_alias=True)])
    return inserted


def status_payload() -> dict[str, Any]:
    schema = r16_schema_status()
    if not schema["applied"]:
        return _status_without_schema(schema)
    if not schema.get("retentionReady"):
        result = _status_without_schema(schema)
        result["blockers"] = ["WAIT_RHIST03_R16_SCHEMA_NOT_APPLIED"]
        return result
    runs = list_dataset_runs(limit=1)
    latest_run_id = runs[0].get("runId") if runs else None
    approvals = (
        list_approvals(dataset_run_id=latest_run_id, limit=1000)
        if latest_run_id else []
    )
    blockers = sorted(
        {str(code) for row in approvals for code in (row.get("blockers") or ())}
    )
    all_approved = bool(approvals) and all(
        row.get("validationStatus") == "PIT_APPROVED" for row in approvals
    )
    conclusions = {row.get("profileConclusion") for row in approvals}
    conclusion = conclusions.pop() if len(conclusions) == 1 else "INCONCLUSIVE"
    if not runs:
        blockers = ["WAIT_R16_NO_DATASET"]
    elif not approvals:
        blockers = ["WAIT_R16_NO_APPROVAL_LEDGER"]
    return {
        "contract": CONTRACT,
        "datasetStatus": "READY" if all_approved else "BUILDING",
        "validationStatus": "PIT_APPROVED" if all_approved else "PIT_NOT_APPROVED",
        "approvalScope": "DATASET_AND_REPLAY",
        "profileConclusion": conclusion or "INCONCLUSIVE",
        "promotionStatus": "NOT_PROMOTED",
        "probabilityAuthorized": False,
        "confirmationAuthorized": False,
        "executionAuthorized": False,
        "blockers": blockers,
        "schema": schema,
        "latestDatasetRunId": latest_run_id,
        "exactCellCount": len(approvals),
        "worker": worker_state(),
    }


def run_incremental(
    *,
    mode: ReplayMode = "incremental",
    rebuild_reason: str | None = None,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Catch up all real persisted S8 dates and append changed label paths."""

    if mode not in {"incremental", "catch_up", "replay", "rebuild"}:
        raise ValueError("unsupported R16 replay mode")
    if mode == "rebuild" and not (rebuild_reason or "").strip():
        raise ValueError("R16 rebuild requires a non-empty reason")
    if not r16_schema_status()["applied"]:
        raise RuntimeError("WAIT_R16_SCHEMA_NOT_APPLIED")

    owner = owner_id or f"r16-{uuid4().hex}"
    if not acquire_worker_lease(owner):
        raise RuntimeError("WAIT_R16_REPLAY_LEASE")
    try:
        resume_pending_publications()
        # Discovery enumerates immutable history; it does not choose an S8
        # parent for an existing hypothesis. Every freeze resolves its exact ID.
        persisted_s8 = list_latest_selection_payloads(S8_PROFILE_ID, limit=500000)
        selected_s8, rejected_s8, conflict_count = _select_s8_history(persisted_s8)
        revision_hash = _revision_hash(
            rebuild_reason.strip() if mode == "rebuild" and rebuild_reason else None
        )
        symbols = {
            str(row.get("symbol") or "").upper()
            for payload in selected_s8
            for row in (payload.get("rows") or ())
            if row.get("symbol")
        }
        if selected_s8:
            trading_days = [_s8_identity(payload)[1] for payload in selected_s8]
            bar_floor = min(trading_days) - timedelta(days=180)
            raw_bars = list_raw_bars_by_symbol(
                symbols, through=date.max, from_date=bar_floor
            )
        else:
            raw_bars = {}
        bars_by_symbol = {
            symbol: [_bar_payload(bar) for bar in rows]
            for symbol, rows in raw_bars.items()
        }

        dataset_rows: list[dict[str, Any]] = []
        build_rejections = list(rejected_s8)
        for s8_payload in selected_s8:
            try:
                hypotheses = freeze_s8_hypotheses(
                    s8_payload=s8_payload,
                    dataset_revision_hash=revision_hash,
                )
            except (ValueError, RuntimeError) as exc:
                build_rejections.append(
                    {
                        "runId": str(s8_payload.get("runId") or "UNKNOWN"),
                        "reason": str(exc),
                    }
                )
                continue
            dataset = _dataset_payload(
                s8_payload=s8_payload,
                revision_hash=revision_hash,
                hypotheses=hypotheses,
            )
            persist_dataset_run(dataset)
            persist_hypotheses(
                dataset["runId"],
                [row.model_dump(mode="json", by_alias=True) for row in hypotheses],
            )
            dataset_rows.append(dataset)

        if not dataset_rows:
            checkpoint = {
                "contract": CONTRACT,
                "mode": mode,
                "state": "WAIT",
                "datasetRunCount": 0,
                "rejectedS8": build_rejections,
                "sourceDateConflictCount": conflict_count,
            }
            save_worker_checkpoint(owner, checkpoint)
            result = status_payload()
            result["replay"] = checkpoint
            return result

        all_hypotheses = [
            R16FrozenHypothesisV1.model_validate(row)
            for row in list_hypotheses(limit=500000)
            if row.get("datasetRevisionHash") == revision_hash
        ]
        latest_before = {
            row.hypothesis_id: row
            for row in (
                R16ObservationV1.model_validate(payload)
                for payload in list_latest_observations(limit=500000)
            )
            if row.dataset_revision_hash == revision_hash
        }
        stored_runs = [
            row for row in list_dataset_runs(limit=500000)
            if row.get("datasetRevisionHash") == revision_hash
        ]
        run_by_s8 = {str(row["sourceS8RunId"]): str(row["runId"]) for row in stored_runs}

        observations_created = 0
        for hypothesis in all_hypotheses:
            prior = latest_before.get(hypothesis.hypothesis_id)
            if prior is not None and prior.status in TERMINAL_STATUSES:
                continue
            observation = label_hypothesis(
                hypothesis, bars=bars_by_symbol.get(hypothesis.symbol, [])
            )
            if prior is not None and prior.observation_id == observation.observation_id:
                continue
            if prior is not None:
                observation = observation.model_copy(update={
                    "predecessor_observation_id": prior.observation_id,
                    "predecessor_observation_hash": _hash(prior.model_dump(mode="json", by_alias=True)),
                })
            dataset_run_id = run_by_s8.get(hypothesis.source_s8_run_id)
            if dataset_run_id is None:
                raise RuntimeError("WAIT_R16_HYPOTHESIS_DATASET_LINEAGE")
            observations_created += persist_observations(
                dataset_run_id,
                [observation.model_dump(mode="json", by_alias=True)],
            )

        # Repair the outcome-revision boundary on every worker retry, including
        # a crash after the outcome published but before its revision published.
        revisions_created = 0
        for payload in list_observations(limit=500000):
            if payload.get("datasetRevisionHash") != revision_hash or not payload.get("predecessorObservationId"):
                continue
            observation = R16ObservationV1.model_validate(payload)
            predecessor_id = observation.predecessor_observation_id
            predecessor_hash = observation.predecessor_observation_hash
            if not predecessor_id or not predecessor_hash:
                raise RuntimeError("WAIT_RHIST03_OUTCOME_PREDECESSOR_REQUIRED")
            revision = R16RevisionV1(
                revision_id=stable_id("r16revision", observation.observation_id, observation.predecessor_observation_id),
                hypothesis_id=observation.hypothesis_id,
                predecessor_type="OUTCOME", predecessor_id=predecessor_id,
                predecessor_hash=predecessor_hash,
                revision_kind="OUTCOME_CORRECTION", recorded_at=observation.label_computed_at,
                reason="Later observed path; the previous outcome remains immutable.",
                changes={"replacementObservationId": observation.observation_id,
                         "replacementObservationHash": _hash(payload), "status": observation.status},
                evidence_hashes=observation.outcome_bar_hashes,
            )
            revisions_created += persist_revisions(
                run_by_s8[observation.source_s8_run_id], [revision.model_dump(mode="json", by_alias=True)],
            )
        if mode == "rebuild" and rebuild_reason:
            revisions_created += _link_rebuild_versions(all_hypotheses, rebuild_reason.strip())

        latest_observations = [
            R16ObservationV1.model_validate(payload)
            for payload in list_latest_observations(limit=500000)
            if payload.get("datasetRevisionHash") == revision_hash
        ]
        trading_dates = [date.fromisoformat(row["tradingDate"]) for row in dataset_rows]
        expected_s8_dates, calendar_verified = _calendar_window(trading_dates)
        latest_dataset = max(dataset_rows, key=lambda row: (row["tradingDate"], row["runId"]))
        metrics, folds = build_metrics(
            dataset_run_id=str(latest_dataset["runId"]),
            hypotheses=all_hypotheses,
            observations=latest_observations,
            expected_s8_dates=expected_s8_dates,
            available_s8_dates=len(set(trading_dates)),
            calendar_verified=calendar_verified,
            source_date_conflict_count=conflict_count,
            source_artifact_rejected_count=len(build_rejections),
        )
        for fold in folds:
            persist_fold(fold.model_dump(mode="json", by_alias=True))
        approval_rows: list[dict[str, Any]] = []
        for metric in metrics:
            persist_metric(metric)
            approval = evaluate_approval(
                metrics=metric, dataset_run_id=str(latest_dataset["runId"])
            )
            approval_payload = approval.model_dump(mode="json", by_alias=True)
            persist_approval(approval_payload)
            approval_rows.append(approval_payload)

        checkpoint = {
            "contract": CONTRACT,
            "mode": mode,
            "state": "COMPLETE",
            "datasetRevisionHash": revision_hash,
            "datasetRunCount": len(dataset_rows),
            "hypothesisCount": len(all_hypotheses),
            "latestObservationCount": len(latest_observations),
            "observationsAppended": observations_created,
            "revisionsAppended": revisions_created,
            "metricCount": len(metrics),
            "foldCount": len(folds),
            "approvalCount": len(approval_rows),
            "calendarVerified": calendar_verified,
            "expectedS8Dates": expected_s8_dates,
            "availableS8Dates": len(set(trading_dates)),
            "sourceDateConflictCount": conflict_count,
            "rejectedS8": build_rejections,
        }
        save_worker_checkpoint(owner, checkpoint)
        return {
            "contract": CONTRACT,
            "dataset": latest_dataset,
            "replay": checkpoint,
            "metrics": list(metrics),
            "approvals": approval_rows,
            "probabilityAuthorized": False,
            "confirmationAuthorized": False,
            "executionAuthorized": False,
        }
    finally:
        release_worker_lease(owner)


def runs_payload(limit: int = 50, cursor: int | None = None) -> dict[str, Any]:
    if not r16_schema_status()["applied"]:
        return {
            "contract": CONTRACT, "runs": [], "count": 0, "nextCursor": None,
            "blockers": ["WAIT_R16_SCHEMA_NOT_APPLIED"],
        }
    page = page_dataset_runs(limit=limit, cursor=cursor)
    return {
        "contract": CONTRACT, "runs": page["items"], "count": len(page["items"]),
        "nextCursor": page["nextCursor"], "blockers": [],
    }


def observations_payload(
    dataset_run_id: str | None = None,
    limit: int = 200,
    cursor: int | None = None,
) -> dict[str, Any]:
    if not r16_schema_status()["applied"]:
        return {
            "contract": CONTRACT, "observations": [], "count": 0,
            "nextCursor": None, "blockers": ["WAIT_R16_SCHEMA_NOT_APPLIED"],
        }
    page = page_observations(dataset_run_id, limit=limit, cursor=cursor)
    return {
        "contract": CONTRACT, "observations": page["items"],
        "count": len(page["items"]), "nextCursor": page["nextCursor"],
        "blockers": [],
    }


def metrics_payload(dataset_run_id: str | None = None) -> dict[str, Any]:
    if not r16_schema_status()["applied"]:
        return {
            "contract": CONTRACT, "metrics": [], "count": 0,
            "blockers": ["WAIT_R16_SCHEMA_NOT_APPLIED"],
        }
    rows = list_metrics(dataset_run_id=dataset_run_id, limit=1000)
    return {"contract": CONTRACT, "metrics": rows, "count": len(rows), "blockers": []}


def approval_payload(dataset_run_id: str | None = None) -> dict[str, Any]:
    if not r16_schema_status()["applied"]:
        return status_payload()
    if dataset_run_id:
        rows = list_approvals(dataset_run_id=dataset_run_id, limit=1000)
        return {
            "contract": CONTRACT, "datasetRunId": dataset_run_id,
            "approvals": rows, "count": len(rows),
            "probabilityAuthorized": False,
            "confirmationAuthorized": False,
            "executionAuthorized": False,
        }
    return status_payload()


def legacy_homework_payload(symbol: str | None = None) -> dict[str, Any]:
    """Read-only compatibility projection; never recomputes client-side PIT."""

    if not r16_schema_status()["applied"]:
        return {
            "schemaVersion": "trendforge.s9-pit-homework.compat-r16.v1",
            "rows": [], "rowCount": 0, "validationStatus": "PIT_NOT_APPROVED",
            "blockers": ["WAIT_R16_SCHEMA_NOT_APPLIED"],
        }
    rows = list_latest_observations(limit=500000)
    if symbol:
        wanted = symbol.strip().upper()
        rows = [row for row in rows if str(row.get("symbol") or "").upper() == wanted]
    return {
        "schemaVersion": "trendforge.s9-pit-homework.compat-r16.v1",
        "rows": rows, "rowCount": len(rows),
        "validationStatus": status_payload()["validationStatus"],
        "probabilityAuthorized": False,
        "confirmationAuthorized": False,
        "executionAuthorized": False,
    }


def legacy_gate_payload() -> dict[str, Any]:
    state = status_payload()
    return {
        "schemaVersion": "trendforge.pit-gate.compat-r16.v1",
        "validationStatus": state["validationStatus"],
        "guidanceStatus": state["validationStatus"],
        "reasonCodes": state["blockers"],
        "profileConclusion": state["profileConclusion"],
        "promotionStatus": "NOT_PROMOTED",
        "probabilityAuthorized": False,
        "confirmationAuthorized": False,
        "executionAuthorized": False,
    }


__all__ = [
    "CONTRACT", "approval_payload", "legacy_gate_payload",
    "legacy_homework_payload", "metrics_payload", "observations_payload",
    "run_incremental", "runs_payload", "status_payload",
]
