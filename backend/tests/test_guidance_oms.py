"""File A guidance OMS (R2-B activation amendment) tests.

Law under test:
- paper ticket + OpenAlgo order JSON preview always available;
- live placement blocked unless env + lane + UI arm ALL hold (default 409);
- s7_state_gates.py never contains a place_order path.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from trendforge_api.hybrid_v2.tests_support.fixtures import persist_overlay_lineage
from trendforge_api.main import app
from trendforge_api.selection import guidance_oms
from trendforge_api.selection.guidance_oms import (
    GuidanceLiveBlocked,
    build_paper_ticket,
    compute_paper_plan,
    openalgo_placeorder_json,
)


class _Lane:
    def __init__(self, effective_lane: str, intraday_mode: str = "OFF"):
        self.lane = "FREE_OFFICIAL"
        self.effective_lane = effective_lane
        self.intraday_mode = intraday_mode


@pytest.fixture(autouse=True)
def _reset_arm(monkeypatch):
    guidance_oms.set_live_orders_armed(False)
    monkeypatch.delenv("TRENDFORGE_LIVE_ORDERS", raising=False)
    yield
    guidance_oms.set_live_orders_armed(False)


def test_default_boot_blocks_live_placement() -> None:
    snapshot = guidance_oms.arm_snapshot(lane=_Lane("FREE_OFFICIAL"))
    assert snapshot.env_live_orders is False
    assert snapshot.lane_openalgo_ro is False
    assert snapshot.ui_armed is False
    assert snapshot.live_orders_allowed() is False
    with pytest.raises(GuidanceLiveBlocked) as excinfo:
        guidance_oms.ensure_live_placement_allowed(snapshot)
    assert excinfo.value.code == "LIVE_ORDERS_ARMED_OFF"


def test_partial_arms_still_block() -> None:
    import os

    original = os.environ.get("TRENDFORGE_LIVE_ORDERS")
    os.environ["TRENDFORGE_LIVE_ORDERS"] = "1"
    try:
        # lane off, arm off -> blocked
        with pytest.raises(GuidanceLiveBlocked):
            guidance_oms.ensure_live_placement_allowed(
                guidance_oms.arm_snapshot(lane=_Lane("FREE_OFFICIAL"))
            )
        guidance_oms.set_live_orders_armed(True)
        # lane still off -> blocked
        with pytest.raises(GuidanceLiveBlocked):
            guidance_oms.ensure_live_placement_allowed(
                guidance_oms.arm_snapshot(lane=_Lane("FREE_OFFICIAL"))
            )
        # all three hold -> allowed
        guidance_oms.ensure_live_placement_allowed(
            guidance_oms.arm_snapshot(lane=_Lane("OPENALGO_RO"))
        )
    finally:
        if original is None:
            os.environ.pop("TRENDFORGE_LIVE_ORDERS", None)
        else:
            os.environ["TRENDFORGE_LIVE_ORDERS"] = original


def test_paper_ticket_zero_state_lists_blockers() -> None:
    plan, close = compute_paper_plan(
        symbol="HVBTEST",
        public_state="WAIT",
        evidence_direction="BULLISH",
        draft_confirmed_eligible=False,
        invalidation_condition=None,
        trading_date=None,
    )
    assert plan["researchQuantity"] == 0
    ticket = build_paper_ticket(symbol="HVBTEST", public_state="WAIT", plan=plan)
    assert ticket.side == "FLAT"
    assert ticket.research_quantity == 0
    assert ticket.executable is False
    assert ticket.openalgo_order_json == {}
    assert ticket.blockers


def test_paper_ticket_confirmed_with_geometry_previews_order_json() -> None:
    plan = {
        "side": "LONG",
        "_side": "LONG",
        "researchQuantity": 20,
        "qtyUnit": "shares",
        "researchEntry": 110.0,
        "researchStop": 105.0,
        "researchT1": 117.5,
        "reason": "",
        "notionalInr": 2200.0,
        "reservedRiskInr": 100.0,
        "remainingCapitalInr": 97800.0,
    }
    ticket = build_paper_ticket(
        symbol="HVBTEST", public_state="CONFIRMED", plan=plan
    )
    assert ticket.side == "LONG"
    assert ticket.research_quantity == 20
    assert ticket.notional_inr == pytest.approx(2200.0)
    order = openalgo_placeorder_json(ticket)
    assert order["symbol"] == "HVBTEST"
    assert order["action"] == "BUY"
    assert order["quantity"] == 20
    assert order["apikey"].startswith("REDACTED")
    assert ticket.openalgo_order_json["action"] == "BUY"


def test_dispatch_blocked_by_default_and_allowed_when_fully_armed() -> None:
    plan = {
        "side": "LONG",
        "_side": "LONG",
        "researchQuantity": 10,
        "qtyUnit": "shares",
        "researchEntry": 110.0,
        "researchStop": 105.0,
        "researchT1": 117.5,
        "reason": "",
        "notionalInr": 1100.0,
        "reservedRiskInr": 50.0,
        "remainingCapitalInr": 98900.0,
    }
    ticket = build_paper_ticket(symbol="HVBTEST", public_state="CONFIRMED", plan=plan)

    captured: list[tuple[str, dict]] = []

    def fake_transport(url: str, payload: dict, timeout: float) -> dict:
        captured.append((url, payload))
        return {"status": "success", "data": {"orderid": "PAPER-1"}}

    import os

    with pytest.raises(GuidanceLiveBlocked):
        guidance_oms.dispatch_live_placement(ticket, lane=_Lane("FREE_OFFICIAL"), transport=fake_transport)

    original = os.environ.get("TRENDFORGE_LIVE_ORDERS")
    os.environ["TRENDFORGE_LIVE_ORDERS"] = "1"
    guidance_oms.set_live_orders_armed(True)
    try:
        from types import SimpleNamespace

        fake_config = SimpleNamespace(
            base_url="http://127.0.0.1:9000",
            api_key="test-key",
            timeout_seconds=1.0,
        )
        result = guidance_oms.dispatch_live_placement(
            ticket,
            lane=_Lane("OPENALGO_RO"),
            transport=fake_transport,
            config=fake_config,
        )
        assert result["status"] == "success"
        assert len(captured) == 1
        url, payload = captured[0]
        assert url.endswith("/api/v1/placeorder")
        assert payload["quantity"] == 10
        assert payload["symbol"] == "HVBTEST"
    finally:
        if original is None:
            os.environ.pop("TRENDFORGE_LIVE_ORDERS", None)
        else:
            os.environ["TRENDFORGE_LIVE_ORDERS"] = original


def test_s7_gates_module_has_no_order_path() -> None:
    from pathlib import Path

    source = Path(
        r"D:\TrendForge\backend\trendforge_api\selection\s7_state_gates.py"
    ).read_text(encoding="utf-8")
    assert "place_order" not in source
    print("NO_ORDERS")


def test_guidance_oms_routes(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch, with_structure=True)
    client = TestClient(app)
    listed = client.get("/api/v1/selection/guidance-oms/HVBTEST")
    assert listed.status_code == 200
    body = listed.json()
    assert body["schemaVersion"] == "trendforge.guidance-oms.v1"
    assert body["executable"] is False
    preview = client.post(
        "/api/v1/selection/guidance-oms/preview", json={"symbol": "HVBTEST"}
    )
    assert preview.status_code == 200
    assert "arm" in preview.json()
    place = client.post(
        "/api/v1/selection/guidance-oms/place", json={"symbol": "HVBTEST"}
    )
    assert place.status_code == 409
    assert place.json()["detail"]["code"] == "LIVE_ORDERS_ARMED_OFF"

    arm_get = client.get("/api/v1/settings/live-orders-arm")
    assert arm_get.status_code == 200
    assert arm_get.json()["uiArmed"] is False
    arm_set = client.post(
        "/api/v1/settings/live-orders-arm", json={"armed": True}
    )
    assert arm_set.status_code == 200
    assert arm_set.json()["uiArmed"] is True
    assert client.post(
        "/api/v1/settings/live-orders-arm", json={"armed": False}
    ).json()["uiArmed"] is False
    missing = client.get("/api/v1/selection/guidance-oms/NOSUCH")
    assert missing.status_code in {404, 503}
