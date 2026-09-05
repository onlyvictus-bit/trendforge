from __future__ import annotations

import hashlib
import hmac

from trendforge_api import trade_vision_export
from trendforge_api.trade_vision_export import (
    SIGNATURE_VERSION,
    build_trade_vision_evidence_packet,
    verify_packet_hash,
)


def test_latest_completed_run_skips_newer_running_and_error_runs(monkeypatch) -> None:
    monkeypatch.setattr(
        trade_vision_export,
        "list_scanner_runs",
        lambda limit: [
            {"id": 3, "status": "RUNNING", "finished_at": None},
            {"id": 2, "status": "ERROR", "finished_at": "2026-07-12T01:00:00+00:00"},
            {"id": 1, "status": "COMPLETE", "finished_at": "2026-07-11T01:00:00+00:00"},
        ],
    )

    assert trade_vision_export._latest_completed_run()["id"] == 1


def test_export_is_signed_point_in_time_and_non_executable(monkeypatch) -> None:
    monkeypatch.setenv("TRENDFORGE_TRADEVISION_SHARED_SECRET", "test-shared-secret")
    packet = build_trade_vision_evidence_packet()

    assert packet["schemaVersion"] == "trendforge-tradevision-evidence.v1"
    assert packet["signatureVersion"] == SIGNATURE_VERSION
    assert packet["transportReady"] is True
    assert verify_packet_hash(packet) is True
    assert packet["evidence"]["safety"] == {
        "researchOnly": True,
        "tradeAllowed": False,
        "orderRoutingEnabled": False,
        "brokerOrderCreated": False,
        "liveTradingBlocked": True,
    }
    assert packet["evidence"]["run"]["id"]
    assert packet["evidence"]["candidates"]
    assert packet["evidence"]["gateDecisions"]
    assert packet["evidence"]["sourceLineage"]
    signing_input = (
        f"{packet['signatureVersion']}.{packet['packetId']}."
        f"{packet['evidenceAsOf']}.{packet['payloadSha256']}"
    ).encode()
    expected = hmac.new(
        b"test-shared-secret", signing_input, hashlib.sha256
    ).hexdigest()
    assert hmac.compare_digest(packet["serviceSignature"], expected)


def test_export_without_service_secret_stays_transport_blocked(monkeypatch) -> None:
    monkeypatch.delenv("TRENDFORGE_TRADEVISION_SHARED_SECRET", raising=False)
    packet = build_trade_vision_evidence_packet()

    assert packet["transportReady"] is False
    assert packet["serviceSignature"] is None
    assert verify_packet_hash(packet) is True
