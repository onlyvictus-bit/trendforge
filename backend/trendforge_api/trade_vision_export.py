from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .engine import current_command_bar
from .source_monitor import SOURCE_CATALOG
from .storage import (
    get_latest_source_parse_result,
    get_latest_source_snapshot,
    list_gate_decisions,
    list_scanner_candidates,
    list_scanner_runs,
)


SCHEMA_VERSION = "trendforge-tradevision-evidence.v1"
SIGNATURE_VERSION = "trendforge-tradevision-hmac-sha256.v1"


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _decode_saved_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _safe_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run.get("id"),
        "runHash": run.get("run_hash"),
        "universe": run.get("universe"),
        "trigger": run.get("trigger"),
        "status": run.get("status"),
        "pausedReason": run.get("paused_reason"),
        "candidateCount": run.get("candidate_count"),
        "startedAt": run.get("started_at"),
        "finishedAt": run.get("finished_at"),
        "gateReadiness": _decode_saved_json(run.get("gate_readiness_json")),
        "sourceHealthAtRun": _decode_saved_json(run.get("source_health_json")),
    }


def _latest_completed_run() -> dict[str, Any] | None:
    for run in list_scanner_runs(limit=100):
        if run.get("status") == "COMPLETE" and run.get("finished_at"):
            return run
    return None


def _candidate_records(run_id: int) -> list[dict[str, Any]]:
    return [
        {
            "recordId": row.get("id"),
            "symbol": row.get("symbol"),
            "state": row.get("final_state"),
            "createdAt": row.get("created_at"),
            "payload": row.get("payload"),
        }
        for row in list_scanner_candidates(run_id=run_id, limit=10_000)
    ]


def _source_lineage() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for descriptor in SOURCE_CATALOG:
        snapshot = get_latest_source_snapshot(descriptor.key)
        parsed = get_latest_source_parse_result(descriptor.key)
        rows.append(
            {
                "sourceKey": descriptor.key,
                "authority": descriptor.authority.value,
                "snapshotId": snapshot.id if snapshot else None,
                "snapshotState": snapshot.check_state if snapshot else "MISSING",
                "contentHash": snapshot.content_hash if snapshot else None,
                "snapshotCheckedAt": snapshot.checked_at if snapshot else None,
                "parserOutputId": parsed.id if parsed else None,
                "parserState": parsed.parser_state if parsed else "MISSING",
                "dataDate": parsed.data_date if parsed else None,
                "recordCount": parsed.record_count if parsed else 0,
            }
        )
    return rows


def build_trade_vision_evidence_packet() -> dict[str, Any]:
    run = _latest_completed_run()
    if run is None:
        raise ValueError("No completed TrendForge scanner run is available for export.")
    run_id = int(run["id"])
    evidence_as_of = str(run.get("finished_at") or run.get("started_at"))
    evidence = {
        "producer": {
            "service": "trendforge-api",
            "mode": "guarded-research",
        },
        "run": _safe_run(run),
        "commandBar": current_command_bar().model_dump(by_alias=True, mode="json"),
        "candidates": _candidate_records(run_id),
        "gateDecisions": list_gate_decisions(run_id=str(run_id), limit=50_000),
        "sourceLineage": _source_lineage(),
        "safety": {
            "researchOnly": True,
            "tradeAllowed": False,
            "orderRoutingEnabled": False,
            "brokerOrderCreated": False,
            "liveTradingBlocked": True,
        },
    }
    payload_hash = _canonical_hash(evidence)
    packet_id = str(
        uuid5(
            NAMESPACE_URL,
            f"trendforge:tradevision:{run.get('run_hash')}:{payload_hash}",
        )
    )
    secret = os.getenv("TRENDFORGE_TRADEVISION_SHARED_SECRET", "").strip()
    signing_input = (
        f"{SIGNATURE_VERSION}.{packet_id}.{evidence_as_of}.{payload_hash}"
    ).encode("utf-8")
    signature = (
        hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).hexdigest()
        if secret
        else None
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "signatureVersion": SIGNATURE_VERSION,
        "packetId": packet_id,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "evidenceAsOf": evidence_as_of,
        "payloadSha256": payload_hash,
        "serviceSignature": signature,
        "transportReady": bool(secret),
        "evidence": evidence,
    }


def verify_packet_hash(packet: dict[str, Any]) -> bool:
    supplied = packet.get("payloadSha256")
    evidence = packet.get("evidence")
    return (
        isinstance(supplied, str)
        and isinstance(evidence, dict)
        and hmac.compare_digest(supplied, _canonical_hash(evidence))
    )
