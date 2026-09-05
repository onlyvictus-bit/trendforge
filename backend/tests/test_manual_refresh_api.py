import asyncio
from unittest.mock import patch

from fastapi.testclient import TestClient

from trendforge_api import main


class FakeManualRefresh:
    def __init__(self) -> None:
        self.start_calls = 0

    async def start(self) -> dict:
        self.start_calls += 1
        return {
            "state": "RUNNING",
            "accepted": True,
            "sourceCount": 69,
            "scheduledTimesIst": [
                "09:00", "09:17", "10:30", "12:30", "13:30", "15:00"
            ],
        }

    def status(self) -> dict:
        return {
            "state": "IDLE",
            "accepted": False,
            "sourceCount": 69,
            "scheduledTimesIst": [
                "09:00", "09:17", "10:30", "12:30", "13:30", "15:00"
            ],
        }


def test_manual_refresh_http_contract_uses_coordinator_without_fixed_source_count() -> None:
    coordinator = FakeManualRefresh()
    with patch.object(main, "_MD69_MANUAL_REFRESH", coordinator):
        client = TestClient(main.app)
        started = client.post("/api/market-data/refresh")
        status = client.get("/api/market-data/refresh/status")

    assert started.status_code == 202
    assert started.json()["state"] == "RUNNING"
    assert started.json()["sourceCount"] == 69
    assert status.status_code == 200
    assert status.json()["sourceCount"] == 69
    assert status.json()["scheduledTimesIst"] == [
        "09:00", "09:17", "10:30", "12:30", "13:30", "15:00"
    ]
    assert coordinator.start_calls == 1


def test_manual_refresh_http_contract_fails_closed_when_collector_disabled() -> None:
    with patch.object(main, "_MD69_MANUAL_REFRESH", None):
        client = TestClient(main.app)
        response = client.post("/api/market-data/refresh")

    assert response.status_code == 503
    assert response.json()["detail"] == "MD69 collector is disabled"


def test_live_panel_endpoint_forwards_force_after_manual_refresh() -> None:
    class FakeLivePanels:
        def __init__(self) -> None:
            self.kwargs = None

        async def get_snapshot(self, **kwargs):
            self.kwargs = kwargs
            return {"contract": "trendforge.livePanels.v1"}

    service = FakeLivePanels()
    with patch.object(main, "LIVE_PANELS_SERVICE", service):
        client = TestClient(main.app)
        response = client.get("/api/panels/live?refresh=true&force=true")

    assert response.status_code == 200
    assert service.kwargs is not None
    assert service.kwargs["refresh"] is True
    assert service.kwargs["force"] is True
class FakeLifecycleScanner:
    def __init__(self) -> None:
        self.restore_calls = 0
        self.stop_calls = 0

    def restore(self) -> None:
        self.restore_calls += 1

    def stop(self, *, persist: bool) -> None:
        assert persist is False
        self.stop_calls += 1


class FakeLifecyclePanels:
    def __init__(self) -> None:
        self.start_calls = 0
        self.stop_calls = 0

    def start(self, *, interval_sec: int) -> None:
        assert interval_sec == 120
        self.start_calls += 1

    async def stop(self) -> None:
        self.stop_calls += 1


class FakeForegroundScheduler:
    def __init__(self) -> None:
        self.start_calls = 0
        self.cancelled = False

    async def start_foreground(self, *, poll_seconds: int) -> dict:
        assert poll_seconds == 15
        self.start_calls += 1
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise


def test_api_lifespan_starts_and_stops_one_md69_foreground_scheduler(
    monkeypatch,
) -> None:
    scanner = FakeLifecycleScanner()
    panels = FakeLifecyclePanels()
    scheduler = FakeForegroundScheduler()
    monkeypatch.setenv("MARKET_DATA_69_AUTOSTART", "1")
    monkeypatch.setattr(main, "SCANNER_SCHEDULER", scanner)
    monkeypatch.setattr(main, "LIVE_PANELS_SERVICE", panels)
    monkeypatch.setattr(main, "_MD69_SCHEDULER", scheduler)

    async def exercise() -> None:
        async with main.app_lifespan(main.app):
            await asyncio.sleep(0)
            assert scheduler.start_calls == 1

    asyncio.run(exercise())

    assert scheduler.start_calls == 1
    assert scheduler.cancelled is True
    assert scanner.restore_calls == 1
    assert scanner.stop_calls == 1
    assert panels.start_calls == 1
    assert panels.stop_calls == 1


def test_api_lifespan_does_not_autostart_md69_without_explicit_flag(
    monkeypatch,
) -> None:
    scanner = FakeLifecycleScanner()
    panels = FakeLifecyclePanels()
    scheduler = FakeForegroundScheduler()
    monkeypatch.delenv("MARKET_DATA_69_AUTOSTART", raising=False)
    monkeypatch.setattr(main, "SCANNER_SCHEDULER", scanner)
    monkeypatch.setattr(main, "LIVE_PANELS_SERVICE", panels)
    monkeypatch.setattr(main, "_MD69_SCHEDULER", scheduler)

    async def exercise() -> None:
        async with main.app_lifespan(main.app):
            await asyncio.sleep(0)

    asyncio.run(exercise())

    assert scheduler.start_calls == 0
    assert scheduler.cancelled is False
