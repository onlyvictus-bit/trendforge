from __future__ import annotations

from typing import Any, Iterable, Literal

from .models import SourceMonitorSummary, SourceParseResult
from .records import AlertCreate, AlertRecord
from .storage import save_general_alert


PARSER_ALERT_STATES = {
    "BROKEN",
    "WAIT_FETCH_REQUIRED",
    "WAIT_PARSE_ERROR",
    "WAIT_SCHEMA_MISMATCH",
    "WAIT_SOURCE_DATE",
    "WAIT_STALE_DATA",
}


def emit_source_health_alerts(
    monitor: SourceMonitorSummary,
    parse_results: Iterable[SourceParseResult],
) -> list[AlertRecord]:
    alerts: list[AlertRecord] = []
    for snapshot in monitor.results:
        if snapshot.check_state != "BROKEN":
            continue
        alerts.append(
            save_general_alert(
                AlertCreate(
                    alertType="SOURCE_FAILURE",
                    severity="CRITICAL",
                    state=snapshot.check_state,
                    reason=f"{snapshot.name} fetch failed: {snapshot.error or 'unknown transport error'}",
                    risk={
                        "sourceKey": snapshot.source_key,
                        "url": snapshot.url,
                        "statusCode": snapshot.status_code,
                        "gateEffect": "Affected evidence remains WAIT and cannot unlock READY.",
                    },
                )
            )
        )
    for parsed in parse_results:
        if parsed.parser_state not in PARSER_ALERT_STATES:
            continue
        severity: Literal["WARN", "CRITICAL"] = (
            "CRITICAL"
            if parsed.parser_state in {"BROKEN", "WAIT_SCHEMA_MISMATCH"}
            else "WARN"
        )
        alerts.append(
            save_general_alert(
                AlertCreate(
                    alertType="SOURCE_PARSE_HEALTH",
                    severity=severity,
                    state=parsed.parser_state,
                    reason=f"{parsed.source_key} structured evidence unavailable: {parsed.summary}",
                    risk={
                        "sourceKey": parsed.source_key,
                        "snapshotId": parsed.snapshot_id,
                        "dataDate": parsed.data_date,
                        "recordCount": parsed.record_count,
                        "gateEffect": "Affected layer remains WAIT/STALE.",
                    },
                )
            )
        )
    return alerts


def emit_regime_change_alert(
    previous: dict[str, Any] | None, current: dict[str, Any]
) -> AlertRecord | None:
    previous_state = str(previous.get("state")) if previous else None
    current_state = str(current.get("state") or "WAIT_DATA_WEAK")
    if previous_state is None or previous_state == current_state:
        return None
    severe = current_state in {"NO_TRADE", "WAIT_DATA_WEAK"}
    return save_general_alert(
        AlertCreate(
            alertType="REGIME_CHANGE",
            severity="CRITICAL" if severe else "WARN",
            state=current_state,
            reason=f"Market regime changed from {previous_state} to {current_state}: {current.get('reason', 'reason unavailable')}",
            risk={
                "previousState": previous_state,
                "currentState": current_state,
                "gateOutcome": current.get("gateOutcome"),
                "sourceDate": current.get("sourceDate"),
                "action": "Reassess open research plans and block directionally conflicting new entries.",
            },
        )
    )


def emit_context_wait_alert(errors: list[str]) -> AlertRecord | None:
    if not errors:
        return None
    return save_general_alert(
        AlertCreate(
            alertType="MARKET_CONTEXT_WAIT",
            severity="WARN",
            state="WAIT_DATA_WEAK",
            reason="Official market/sector context could not be rebuilt: "
            + " | ".join(errors),
            risk={
                "gateEffect": "Market or sector context cannot confirm READY.",
                "errors": errors,
            },
        )
    )
