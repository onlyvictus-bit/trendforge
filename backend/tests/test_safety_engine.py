from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.demo_data import generate_demo_daily_candles
from trendforge_api.records import JournalCreate, JournalOutcomeUpdate
from trendforge_api.risk_engine import (
    PositionSizingInput,
    RiskSettings,
    calculate_position_size,
)
from trendforge_api.safety_engine import (
    RecoveryUnlockRequest,
    evaluate_safety_status,
    recover_from_manual_lock,
)
from trendforge_api.scanner_scheduler import ScannerScheduler


IST = timezone(timedelta(hours=5, minutes=30))
AS_OF = datetime(2026, 7, 11, 14, 0, tzinfo=IST)


def save_loss(*, opened_at: datetime, pnl: float = -500) -> None:
    entry = storage.save_journal_entry(
        JournalCreate(
            symbol="INFY",
            mode="INTRADAY",
            direction="LONG",
            decisionState="READY",
            setup="ORB",
            quantity=10,
            entryPrice=100,
            stopPrice=95,
            openedAt=opened_at,
            notes="Controlled loss fixture.",
        )
    )
    storage.update_journal_outcome(
        entry.id,
        JournalOutcomeUpdate(
            outcomeState="LOSS",
            exitPrice=95,
            closedAt=opened_at + timedelta(minutes=10),
            pnl=pnl,
            rMultiple=-1,
            notes="Controlled outcome.",
        ),
    )


def test_safety_status_derives_cooldown_soft_reduction_and_hard_lock(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "safety-derived.db")
    settings = RiskSettings()
    save_loss(opened_at=AS_OF - timedelta(minutes=20))
    one = evaluate_safety_status(as_of=AS_OF, settings=settings)
    assert one.state == "COOLDOWN_ACTIVE"
    assert one.consecutive_losses == 1
    assert one.cooldown_until is not None

    save_loss(opened_at=AS_OF - timedelta(minutes=15))
    two = evaluate_safety_status(as_of=AS_OF, settings=settings)
    assert two.state == "COOLDOWN_ACTIVE"
    assert two.daily_realized_pnl == -1_000
    after_cooldown = evaluate_safety_status(
        as_of=AS_OF + timedelta(minutes=40), settings=settings
    )
    assert after_cooldown.state == "RISK_REDUCED"
    assert after_cooldown.risk_multiplier == 0.5

    save_loss(opened_at=AS_OF - timedelta(minutes=11), pnl=-500)
    three = evaluate_safety_status(as_of=AS_OF, settings=settings)
    assert three.state == "LOCKED_NO_TRADE"
    assert three.locked is True
    assert three.consecutive_losses == 3
    assert three.daily_realized_pnl == -1_500


def test_manual_panic_lock_requires_elapsed_cooldown_and_recovery_checklist(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "safety-panic.db")
    event_id = storage.create_safety_event(
        event_type="MANUAL_PANIC_LOCK",
        state="LOCKED_NO_TRADE",
        reason="User activated emergency lock.",
        system_action="Block all new entries.",
        next_allowed_action="Complete recovery checklist after cooldown.",
        cooldown_until=(AS_OF + timedelta(minutes=30)).isoformat(),
        created_at=AS_OF.isoformat(),
        active=True,
    )
    status = evaluate_safety_status(as_of=AS_OF, settings=RiskSettings())
    assert status.state == "LOCKED_NO_TRADE"
    assert status.active_event_ids == [event_id]

    payload = RecoveryUnlockRequest(
        reason="Cooldown complete and risk accepted.",
        recoveryChecklist=[True, True, True, True, True],
    )
    with pytest.raises(RuntimeError, match="cooldown remains active"):
        recover_from_manual_lock(payload, now=AS_OF)
    unlocked = recover_from_manual_lock(payload, now=AS_OF + timedelta(minutes=31))
    assert unlocked.state == "GREEN"
    events = storage.list_safety_events(limit=10)
    assert events[0]["event_type"] == "RECOVERY_UNLOCK"
    assert any(row["resolved_at"] for row in events if row["id"] == event_id)


def test_position_size_is_research_only_and_safety_lock_has_precedence() -> None:
    settings = RiskSettings(max_total_open_risk_percent=0.05)
    base = PositionSizingInput(
        entry=100,
        stop=95,
        target=112,
        confidence=95,
        candidate_state="READY",
        source_ready=True,
        exceptional_risk_allowed=False,
    )
    normal = calculate_position_size(base, settings=settings)
    assert normal.state == "POSTPONED_NO_QUANTITY"
    assert normal.executable is False
    assert normal.risk_percent == 0
    assert normal.quantity == 0
    assert normal.max_loss == 0

    reduced = calculate_position_size(
        base.model_copy(
            update={
                "safety_state": "RISK_REDUCED",
                "safety_risk_multiplier": 0.5,
                "total_open_risk": 4_900,
                "sector_open_risk": 1_450,
                "highest_portfolio_correlation": 0.85,
                "correlated_open_positions": 1,
            }
        ),
        settings=settings,
    )
    assert reduced.state == "POSTPONED_NO_QUANTITY"
    assert reduced.executable is False
    assert reduced.quantity == 0
    assert reduced.max_loss == 0

    locked = calculate_position_size(
        base.model_copy(update={"safety_state": "LOCKED_NO_TRADE"}),
        settings=settings,
    )
    assert locked.state == "LOCKED_NO_TRADE"
    assert locked.executable is False
    assert locked.quantity == 0


def test_risk_api_uses_persisted_safety_and_panic_is_audited(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "safety-api.db")
    client = TestClient(app)
    panic = client.post(
        "/api/safety/panic-lock",
        json={"reason": "Manual emergency stop.", "cooldownMinutes": 30},
    )
    assert panic.status_code == 200
    assert panic.json()["state"] == "LOCKED_NO_TRADE"

    sized = client.post(
        "/api/risk/position-size",
        json={
            "entry": 100,
            "stop": 95,
            "target": 112,
            "confidence": 90,
            "candidate_state": "READY",
            "source_ready": True,
        },
    )
    assert sized.status_code == 200
    assert sized.json()["state"] == "LOCKED_NO_TRADE"
    assert sized.json()["executable"] is False
    assert sized.json()["quantity"] == 0
    assert storage.list_safety_events(limit=10)
    assert storage.list_general_alerts(limit=10)[0].alert_type == "SAFETY_LOCK"


def test_scanner_cannot_bypass_persisted_safety_lock(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "safety-scanner.db")
    storage.save_ohlcv_candles(
        generate_demo_daily_candles(symbol="SAFELOCK", sessions=45)
    )
    storage.create_safety_event(
        event_type="MANUAL_PANIC_LOCK",
        state="LOCKED_NO_TRADE",
        reason="Controlled scanner safety lock.",
        system_action="Block new entries.",
        next_allowed_action="Complete recovery.",
        cooldown_until=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        active=True,
    )
    summary = ScannerScheduler().run_once(
        universe="WATCHLIST_ONLY", fetch=False, trigger="safety-lock-test"
    )
    assert summary["status"] == "COMPLETE"
    rows = storage.list_scanner_candidates(run_id=summary["runId"], limit=10)
    assert rows[0]["payload"]["state"] == "LOCKED_NO_TRADE"
    assert rows[0]["payload"]["safety"]["locked"] is True
    decisions = storage.list_gate_decisions(run_id=str(summary["runId"]))
    assert any(
        row["gate_key"] == "TRADER_SAFETY" and row["state"] == "LOCKED_NO_TRADE"
        for row in decisions
    )
