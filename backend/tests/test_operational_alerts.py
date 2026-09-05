from __future__ import annotations

from datetime import datetime, timezone

from trendforge_api import storage
from trendforge_api.models import (
    SourceMonitorSummary,
    SourceParseResult,
    SourceSnapshotRecord,
)
from trendforge_api.operational_alerts import (
    emit_context_wait_alert,
    emit_regime_change_alert,
    emit_source_health_alerts,
)


def broken_summary() -> SourceMonitorSummary:
    snapshot = SourceSnapshotRecord(
        sourceKey="nse_mwpl_ban",
        name="NSE MWPL",
        url="https://example.invalid/mwpl.csv",
        checkState="BROKEN",
        statusCode=503,
        contentHash=None,
        contentLength=None,
        lastModified=None,
        etag=None,
        rawPath=None,
        error="HTTP 503",
        checkedAt=datetime.now(timezone.utc).isoformat(),
        previousHash=None,
        changed=False,
    )
    return SourceMonitorSummary(
        totalSources=1,
        checked=1,
        newCount=0,
        changedCount=0,
        unchangedCount=0,
        brokenCount=1,
        skippedCount=0,
        results=[snapshot],
    )


def stale_parse() -> SourceParseResult:
    return SourceParseResult(
        sourceKey="nse_mwpl_ban",
        snapshotId=1,
        parserState="WAIT_STALE_DATA",
        dataDate="2026-07-01",
        recordCount=0,
        summary="MWPL source is stale.",
        output={},
        parsedAt=datetime.now(timezone.utc).isoformat(),
    )


def test_source_alerts_include_reason_risk_and_dedupe(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "source-alerts.db")
    first = emit_source_health_alerts(broken_summary(), [stale_parse()])
    second = emit_source_health_alerts(broken_summary(), [stale_parse()])
    assert len(first) == 2
    assert len(second) == 2
    saved = storage.list_general_alerts()
    assert len(saved) == 2
    assert {item.alert_type for item in saved} == {
        "SOURCE_FAILURE",
        "SOURCE_PARSE_HEALTH",
    }
    assert all(item.reason and item.risk.get("gateEffect") for item in saved)


def test_regime_change_and_context_wait_are_persisted(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "context-alerts.db")
    changed = emit_regime_change_alert(
        {"state": "TRADEABLE_BULLISH"},
        {
            "state": "NO_TRADE",
            "gateOutcome": "HARD_FAIL",
            "sourceDate": "2026-07-10T15:30:00+05:30",
            "reason": "VIX shock.",
        },
    )
    unchanged = emit_regime_change_alert({"state": "NO_TRADE"}, {"state": "NO_TRADE"})
    waiting = emit_context_wait_alert(["Nifty history has only 10 rows."])
    assert changed is not None and changed.severity == "CRITICAL"
    assert unchanged is None
    assert waiting is not None and waiting.state == "WAIT_DATA_WEAK"
    assert len(storage.list_general_alerts()) == 2
