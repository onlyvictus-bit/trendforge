from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api import storage
from trendforge_api.cli import migrate_database
from trendforge_api.demo_data import generate_demo_daily_candles
from trendforge_api.models import OHLCVCandle
from trendforge_api.main import app


def test_schema_migration_status_records_baseline_and_candle_lineage(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "migrations.db")
    result = migrate_database()
    assert result["status"] == "PASS"
    assert [row["version"] for row in result["migrations"]] == [
        "0001_existing_baseline",
        "0002_candle_quality_lineage",
        "0003_normalized_evidence_claims",
        "0004_harmonic_lifecycle_events",
        "0005_alerts_and_manual_journal",
        "0006_corporate_action_adjustment_lineage",
        "0007_bse_offer_xbrl_lineage",
        "0007_selection_r1_runs",
        "0008_cash_a1_staging",
        "0008_corporate_reconstruction_terms",
        "0009_cash_a2_identity",
        "0009_safety_state_events",
        "0010_cash_a3_discovery",
        "0010_nse_instrument_universe",
        "0011_cash_a4_history",
        "0011_market_sector_context",
        "0012_cash_a5_c1",
        "0012_nse_trading_calendar",
        "0013_nse_official_market_context_inputs",
        "0014_source_fetch_attempt_ledger",
        "0015_source_inventory_audit",
        "0016_fred_macro_series",
        "0017_eia_petroleum_weekly",
        "0018_gold_physical_context",
    ]


def test_changed_candle_is_versioned_then_updates_canonical_row(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "revisions.db")
    original = generate_demo_daily_candles(symbol="REVISION", sessions=1)[0]
    assert storage.save_ohlcv_candles([original]) == 1
    assert storage.save_ohlcv_candles([original]) == 0

    payload = original.model_dump(mode="json", by_alias=True)
    payload["close"] = original.close + 1
    payload["high"] = max(original.high, payload["close"])
    payload["fetchedAt"] = "2026-07-11T12:00:00+00:00"
    corrected = OHLCVCandle.model_validate(payload)
    assert storage.save_ohlcv_candles([corrected]) == 1

    current = storage.list_ohlcv_candles(
        "REVISION", "1d", source=original.source, limit=5
    )
    assert len(current) == 1
    assert current[0].close == corrected.close
    revisions = storage.list_candle_revisions(symbol="REVISION")
    assert len(revisions) == 1
    assert revisions[0]["old_payload"]["close"] == original.close
    assert revisions[0]["new_payload"]["close"] == corrected.close
    assert revisions[0]["old_hash"] != revisions[0]["new_hash"]


def test_partial_candle_writes_quality_warning_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "quality.db")
    candle = generate_demo_daily_candles(symbol="QUALITY", sessions=1)[0]
    payload = candle.model_dump(mode="json", by_alias=True)
    payload.update({"barState": "PARTIAL_PERIOD", "completeness": 0.6})
    partial = OHLCVCandle.model_validate(payload)
    storage.save_ohlcv_candles([partial])
    storage.save_ohlcv_candles([partial])
    records = storage.list_candle_quality_records(symbol="QUALITY")
    assert len(records) == 1
    assert records[0]["quality_state"] == "WARN"
    assert "PARTIAL_PERIOD" in records[0]["issues"]
    assert "LOW_COMPLETENESS" in records[0]["issues"]


def test_invalid_ohlcv_geometry_is_rejected_before_storage() -> None:
    payload = generate_demo_daily_candles(symbol="INVALID", sessions=1)[0].model_dump(
        mode="json", by_alias=True
    )
    payload["high"] = payload["low"] - 1
    with pytest.raises(ValidationError, match="high must"):
        OHLCVCandle.model_validate(deepcopy(payload))


def test_migration_and_candle_lineage_api_contracts(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "lineage-api.db")
    candle = generate_demo_daily_candles(symbol="LINEAGEAPI", sessions=1)[0]
    storage.save_ohlcv_candles([candle])
    client = TestClient(app)
    migrations = client.get("/api/storage/migrations")
    assert migrations.status_code == 200
    assert migrations.json()["migrationCount"] == 24
    quality = client.get("/api/storage/candle-quality", params={"symbol": "LINEAGEAPI"})
    assert quality.status_code == 200
    assert len(quality.json()) == 1
    revisions = client.get(
        "/api/storage/candle-revisions", params={"symbol": "LINEAGEAPI"}
    )
    assert revisions.status_code == 200
    assert revisions.json() == []
