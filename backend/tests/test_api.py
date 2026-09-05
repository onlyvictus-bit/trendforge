import unittest
import tempfile
import zipfile
import os
import json
from io import BytesIO
from statistics import pstdev
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from trendforge_api.harmonic_detector import detect_harmonic_patterns
from trendforge_api.models import (
    DataTrust,
    OHLCVCandle,
    SourceParseResult,
    SourceSnapshotRecord,
)
from trendforge_api.derivatives_engine import (
    black_scholes_greeks,
    black_scholes_price,
    implied_volatility,
)
from trendforge_api.risk_engine import PositionSizingInput, calculate_position_size
from trendforge_api.validation_engine import label_price_path
from trendforge_api.feature_engineering import build_point_in_time_features
from trendforge_api.demo_data import (
    generate_demo_daily_candles,
    generate_demo_intraday_candles,
)
from trendforge_api.cftc_analytics import build_cftc_feature_history
from trendforge_api.cftc_history import _validate_archive
from trendforge_api.scanner_scheduler import ScannerScheduler
from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.gate_readiness import dependency_state
from trendforge_api.parsers.source_freshness import is_data_date_fresh
from trendforge_api.parsers.amfi_portfolio_parser import parse_amfi_portfolio
from trendforge_api.parsers.cftc_cot_parser import parse_cftc_cot_positions
from trendforge_api.parsers.nse_participant_oi_parser import parse_nse_participant_oi
from trendforge_api.source_contracts import (
    can_source_unlock_ready,
    parser_can_unlock_gate,
)
from trendforge_api.source_adapters import _nse_frame_to_candles
from trendforge_api.nse_session import resample_nse_session
from trendforge_api.source_monitor import build_source_snapshot, get_source_descriptor
from trendforge_api.source_resolver import direct_download_candidates
from trendforge_api.source_registry_contracts import (
    build_registry_coverage,
    classify_registry_urls,
    load_saved_link_inventory,
)
import pandas as pd


def synthetic_harmonic_candles(symbol="TEST", timeframe="1d", count_prefix=35):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    prices = [100 + (idx % 3) for idx in range(count_prefix)]
    prices += [
        112,
        108,
        104,
        100,
        96,
        92,
        88,
        92,
        96,
        100,
        104,
        100,
        96,
        92,
        88,
        84,
        88,
        92,
        96,
        100,
        104,
        100,
        96,
    ]
    candles = []
    for idx, price in enumerate(prices):
        candles.append(
            OHLCVCandle(
                symbol=symbol,
                timeframe=timeframe,
                source="synthetic",
                timestamp=(start + timedelta(days=idx)).isoformat(),
                open=price - 0.5,
                high=price + 0.25,
                low=price - 0.75,
                close=price,
                volume=1000 + idx * 10,
                trustLevel=DataTrust.SYNTHETIC_TEST,
                fetchedAt=datetime.now(timezone.utc).isoformat(),
            )
        )
    return candles


def synthetic_intraday_candles(symbol="INTRA", days=2):
    candles = []
    start = datetime(2026, 1, 1, 9, 15, tzinfo=ZoneInfo("Asia/Kolkata"))
    for day in range(days):
        session_start = start + timedelta(days=day)
        for idx in range(75):
            ts = session_start + timedelta(minutes=idx * 5)
            price = 100 + day + idx * 0.05
            candles.append(
                OHLCVCandle(
                    symbol=symbol,
                    timeframe="5m",
                    source="synthetic",
                    timestamp=ts.isoformat(),
                    open=price,
                    high=price + 0.4,
                    low=price - 0.3,
                    close=price + 0.1,
                    volume=10000 + idx * 100,
                    trustLevel=DataTrust.SYNTHETIC_TEST,
                    fetchedAt=datetime.now(timezone.utc).isoformat(),
                )
            )
    return candles


class TrendForgeApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = storage.DB_PATH
        storage.DB_PATH = Path(self.temp_dir.name) / "test_research.db"
        self.original_demo_mode = os.environ.get("TRENDFORGE_DEMO_MODE")
        os.environ["TRENDFORGE_DEMO_MODE"] = "1"
        self.client = TestClient(app)

    def tearDown(self):
        if self.original_demo_mode is None:
            os.environ.pop("TRENDFORGE_DEMO_MODE", None)
        else:
            os.environ["TRENDFORGE_DEMO_MODE"] = self.original_demo_mode
        storage.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "trendforge-api")
        self.assertEqual(payload["mode"], "guarded-research")
        self.assertTrue(response.headers.get("X-Request-ID"))

    def test_demo_candles_are_deterministic_and_nse_session_bounded(self):
        daily_first = generate_demo_daily_candles(symbol="TFDEMO", sessions=60)
        daily_second = generate_demo_daily_candles(symbol="TFDEMO", sessions=60)
        self.assertEqual(
            [row.model_dump(mode="json", by_alias=True) for row in daily_first],
            [row.model_dump(mode="json", by_alias=True) for row in daily_second],
        )
        self.assertEqual(len(daily_first), 60)
        self.assertTrue(
            all(
                row.low
                <= min(row.open, row.close)
                <= max(row.open, row.close)
                <= row.high
                for row in daily_first
            )
        )

        intraday = generate_demo_intraday_candles(symbol="TFDEMO", sessions=3)
        self.assertEqual(len(intraday), 225)
        timestamps = [
            datetime.fromisoformat(row.timestamp).astimezone(ZoneInfo("Asia/Kolkata"))
            for row in intraday
        ]
        self.assertTrue(all(ts.weekday() < 5 for ts in timestamps))
        self.assertEqual({(ts.hour, ts.minute) for ts in timestamps[::75]}, {(9, 15)})
        self.assertEqual(
            {(ts.hour, ts.minute) for ts in timestamps[74::75]}, {(15, 25)}
        )
        self.assertTrue(
            all(row.trust_level == DataTrust.SYNTHETIC_TEST for row in intraday)
        )

    def test_nse_session_resampling_marks_planned_partial_bars(self):
        source = generate_demo_intraday_candles(symbol="SESSION", sessions=5)
        expected_counts = {"30m": 65, "1h": 35, "4h_custom": 10, "1d": 5, "1w": 2}
        for timeframe, expected_count in expected_counts.items():
            result = resample_nse_session(source, timeframe)
            self.assertEqual(len(result.candles), expected_count, timeframe)
            self.assertFalse(
                [
                    warning
                    for warning in result.warnings
                    if warning.startswith("REJECT")
                ],
                timeframe,
            )
            self.assertTrue(
                all(0 < row.completeness <= 1 for row in result.candles), timeframe
            )

        thirty = resample_nse_session(source, "30m").candles
        hourly = resample_nse_session(source, "1h").candles
        custom = resample_nse_session(source, "4h_custom").candles
        self.assertEqual(
            sum(row.bar_state == "PARTIAL_NSE_SESSION" for row in thirty), 5
        )
        self.assertEqual(
            sum(row.bar_state == "PARTIAL_NSE_SESSION" for row in hourly), 5
        )
        self.assertEqual(
            sum(row.bar_state == "PARTIAL_NSE_SESSION" for row in custom), 5
        )
        self.assertTrue(all(row.session_date for row in custom))
        storage.save_ohlcv_candles(custom)
        restored = storage.list_ohlcv_candles(
            "SESSION", "4h_custom", source="deterministic_fixture_nse_session", limit=20
        )
        self.assertEqual(len(restored), 10)
        self.assertEqual(
            sum(row.bar_state == "PARTIAL_NSE_SESSION" for row in restored), 5
        )
        self.assertTrue(
            all(row.session_date and 0 < row.completeness <= 1 for row in restored)
        )

        storage.save_ohlcv_candles(source)
        response = self.client.post(
            "/api/nse/resample",
            params={
                "symbol": "SESSION",
                "source": "deterministic_fixture",
                "sourceTimeframe": "5m",
                "targetTimeframe": "30m",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["candleCount"], 65)
        self.assertEqual(
            sum(row["barState"] == "PARTIAL_NSE_SESSION" for row in payload["candles"]),
            5,
        )

    def test_radar_returns_candidates(self):
        response = self.client.get("/api/radar")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 1)
        self.assertIn("symbol", payload[0])
        self.assertIn("metrics", payload[0])
        self.assertTrue(all(row["statusGroup"] != "ready" for row in payload))

        status_response = self.client.get("/api/ml-snapshots/status")
        self.assertEqual(status_response.status_code, 200)
        status = status_response.json()
        self.assertEqual(status["totalRuns"], 1)
        self.assertEqual(status["totalCandidates"], len(payload))

    def test_normal_mode_never_falls_back_to_implicit_mock_candidates(self):
        os.environ.pop("TRENDFORGE_DEMO_MODE", None)
        radar = self.client.get("/api/radar")
        self.assertEqual(radar.status_code, 200)
        self.assertEqual(radar.json(), [])
        health = self.client.get("/api/source-health").json()
        names = {row["name"] for row in health}
        self.assertIn("NSE Bhavcopy / EOD Data", names)
        self.assertNotIn("NSE Paid Data", names)
        source = next(row for row in health if row["name"] == "NSE Bhavcopy / EOD Data")
        self.assertIn("lastAttemptedAt", source)
        self.assertIn("lastSuccessfulAt", source)
        self.assertEqual(source["consecutiveFailures"], 0)
        self.assertIsInstance(source["limitation"], str)
        self.assertTrue(source["limitation"])

    def test_source_health_exposes_attempt_success_and_failure_streak(self):
        os.environ.pop("TRENDFORGE_DEMO_MODE", None)
        checked = datetime.now(timezone.utc)
        storage.save_source_snapshot(
            SourceSnapshotRecord(
                sourceKey="nse_bhavcopy_eod",
                name="NSE Bhavcopy / EOD Data",
                url="https://example.test/success.csv",
                checkState="NEW",
                statusCode=200,
                contentHash="a" * 64,
                contentLength=10,
                rawPath="raw/success.csv",
                checkedAt=(checked - timedelta(minutes=2)).isoformat(),
                changed=True,
            )
        )
        for minute in (1, 0):
            storage.save_source_snapshot(
                SourceSnapshotRecord(
                    sourceKey="nse_bhavcopy_eod",
                    name="NSE Bhavcopy / EOD Data",
                    url="https://example.test/failure.csv",
                    checkState="BROKEN",
                    error="fixture failure",
                    checkedAt=(checked - timedelta(minutes=minute)).isoformat(),
                    changed=False,
                )
            )

        payload = self.client.get("/api/source-health").json()
        source = next(
            row for row in payload if row["name"] == "NSE Bhavcopy / EOD Data"
        )
        self.assertEqual(source["state"], "RED")
        self.assertEqual(source["consecutiveFailures"], 2)
        self.assertEqual(
            source["lastSuccessfulAt"],
            (checked - timedelta(minutes=2)).isoformat(),
        )
        self.assertEqual(
            source["lastAttemptedAt"],
            checked.isoformat(),
        )

    def test_source_health_preserves_latest_structured_data_after_skip(self):
        os.environ.pop("TRENDFORGE_DEMO_MODE", None)
        checked = datetime.now(timezone.utc)
        success = storage.save_source_snapshot(
            SourceSnapshotRecord(
                sourceKey="nse_bhavcopy_eod",
                name="NSE Bhavcopy / EOD Data",
                url="https://example.test/current.csv",
                checkState="NEW",
                statusCode=200,
                contentHash="b" * 64,
                contentLength=10,
                rawPath="raw/current.csv",
                checkedAt=(checked - timedelta(minutes=1)).isoformat(),
                changed=True,
            )
        )
        data_date = checked.date().isoformat()
        storage.save_source_parse_result(
            SourceParseResult(
                sourceKey="nse_bhavcopy_eod",
                snapshotId=success.id,
                parserState="PARSED_STRUCTURED",
                dataDate=data_date,
                recordCount=1,
                summary="fixture current data",
                output={"rows": []},
                parsedAt=(checked - timedelta(seconds=30)).isoformat(),
            )
        )
        storage.save_source_snapshot(
            SourceSnapshotRecord(
                sourceKey="nse_bhavcopy_eod",
                name="NSE Bhavcopy / EOD Data",
                url="https://example.test/current.csv",
                checkState="SKIPPED",
                error="calendar guard",
                checkedAt=checked.isoformat(),
                changed=False,
            )
        )
        storage.save_source_parse_result(
            SourceParseResult(
                sourceKey="nse_bhavcopy_eod",
                parserState="WAIT_FETCH_REQUIRED",
                recordCount=0,
                summary="calendar guard skipped fetch",
                parsedAt=checked.isoformat(),
            )
        )

        payload = self.client.get("/api/source-health").json()
        source = next(
            row for row in payload if row["name"] == "NSE Bhavcopy / EOD Data"
        )
        self.assertEqual(source["state"], "GREEN")
        self.assertEqual(source["latestDataDate"], data_date)
        self.assertEqual(source["lastAttemptedAt"], checked.isoformat())
        self.assertEqual(
            source["lastSuccessfulAt"],
            (checked - timedelta(minutes=1)).isoformat(),
        )

    def test_radar_filter_by_mode(self):
        response = self.client.get("/api/radar", params={"mode": "harmonic"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload)
        self.assertTrue(all(row["type"] == "harmonic" for row in payload))

        status_response = self.client.get("/api/ml-snapshots/status")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["totalRuns"], 0)

    def test_radar_filter_by_status(self):
        response = self.client.get("/api/radar", params={"status": "ready"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload, [])

    def test_radar_detail(self):
        response = self.client.get("/api/radar/COFORGE")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["symbol"], "COFORGE")
        self.assertEqual(payload["state"], "WAIT_DEMO_DATA")

    def test_source_health(self):
        response = self.client.get("/api/source-health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = {row["name"] for row in payload}
        self.assertIn("AMFI Monthly Portfolio Disclosure", names)
        self.assertIn("NSE Paid Data", names)

    def test_source_health_exposes_compiler_maturity_ladder(self):
        """CROSS-006: operational GREEN is not maturity or activation-ready."""
        response = self.client.get("/api/source-health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(len(payload), 0)
        with_key = [row for row in payload if row.get("sourceKey")]
        self.assertGreater(len(with_key), 0, "expected catalog keys on source-health")
        for row in with_key:
            self.assertIn("maturityState", row)
            self.assertIn("gatePermission", row)
            self.assertIn("sourceActivationReady", row)
            self.assertIs(row["sourceActivationReady"], False)
            self.assertIs(row["gatePermission"], False)
            if row.get("maturityState") is not None:
                self.assertNotEqual(row["maturityState"], "GATE_AUTHORIZED")
                self.assertNotEqual(row["maturityState"], "EXECUTION_AUTHORIZED")

    def test_harmonic_sources_registry(self):
        response = self.client.get("/api/harmonic-sources")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = {row["name"] for row in payload}
        self.assertGreaterEqual(len(payload), 20)
        self.assertIn("pyharmonics", names)
        self.assertIn("HarmonicPatterns", names)
        self.assertIn("Patterns Hunters", names)
        self.assertIn("TRN Trading Harmonic Patterns Scanner docs", names)
        self.assertIn("JustTicks Harmonic Screener", names)
        self.assertIn("ChartAlert Basic Scanner", names)
        self.assertIn("Investar Harmonic Trading", names)
        self.assertIn("MotiveWave Scanner", names)
        self.assertIn("TrendSpider", names)

    def test_manual_ml_capture_and_candidates(self):
        capture_response = self.client.post("/api/ml-snapshots/capture")
        self.assertEqual(capture_response.status_code, 200)
        run = capture_response.json()
        self.assertEqual(run["candidateCount"], 5)

        candidates_response = self.client.get(
            "/api/ml-snapshots/candidates",
            params={"runId": run["id"]},
        )
        self.assertEqual(candidates_response.status_code, 200)
        candidates = candidates_response.json()
        self.assertEqual(len(candidates), 5)
        symbols = {row["symbol"] for row in candidates}
        self.assertIn("COFORGE", symbols)
        self.assertIn("TCS", symbols)

    def test_research_record_lifecycle(self):
        create_response = self.client.post(
            "/api/research-records",
            json={
                "symbol": "COFORGE",
                "title": "COFORGE morning radar",
                "note": "Strong confluence, save for review.",
                "tags": ["priority", "smart-money"],
            },
        )
        self.assertEqual(create_response.status_code, 200)
        record = create_response.json()
        self.assertEqual(record["symbol"], "COFORGE")
        self.assertEqual(record["title"], "COFORGE morning radar")
        self.assertEqual(record["candidate"]["state"], "WAIT_DEMO_DATA")
        self.assertIn("sourceHealth", record)

        record_id = record["id"]
        list_response = self.client.get("/api/research-records")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        detail_response = self.client.get(f"/api/research-records/{record_id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["id"], record_id)

        delete_response = self.client.delete(f"/api/research-records/{record_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json(), {"deleted": True})

        empty_response = self.client.get("/api/research-records")
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_response.json(), [])

    def test_ohlcv_storage_dedupes_candles(self):
        candles = synthetic_harmonic_candles(count_prefix=5)
        first_save = storage.save_ohlcv_candles(candles)
        second_save = storage.save_ohlcv_candles(candles)

        self.assertEqual(first_save, len(candles))
        self.assertEqual(second_save, 0)

        stored = storage.list_ohlcv_candles("TEST", "1d", limit=100)
        self.assertEqual(len(stored), len(candles))
        self.assertEqual(stored[0].symbol, "TEST")

    def test_harmonic_detector_blocks_ready_without_confirmation_gates(self):
        candles = synthetic_harmonic_candles()
        patterns, warning = detect_harmonic_patterns(candles, "TEST", "1d")

        self.assertIsNone(warning)
        self.assertTrue(patterns)
        self.assertTrue(all(pattern.final_state != "READY" for pattern in patterns))
        self.assertTrue(any("Smart-money" in reason for reason in patterns[0].reasons))

    def test_harmonic_detector_rejects_weak_data(self):
        candles = synthetic_harmonic_candles(count_prefix=0)[:20]
        patterns, warning = detect_harmonic_patterns(candles, "TEST", "1d")

        self.assertEqual(patterns, [])
        self.assertIn("WAIT_DATA_WEAK", warning)

    def test_harmonic_stored_scan_saves_pattern_and_ml_snapshot(self):
        candles = synthetic_harmonic_candles(symbol="TESTSCAN")
        storage.save_ohlcv_candles(candles)

        response = self.client.post(
            "/api/harmonic/scan",
            json={
                "symbol": "TESTSCAN",
                "timeframe": "1d",
                "useStored": True,
                "saveMlSnapshot": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["symbol"], "TESTSCAN")
        self.assertGreaterEqual(payload["candleCount"], 40)
        self.assertTrue(payload["patterns"])
        self.assertIsNotNone(payload["savedMlRunId"])
        self.assertTrue(
            all(row["finalState"] != "READY" for row in payload["patterns"])
        )

        candidates_response = self.client.get(
            "/api/ml-snapshots/candidates",
            params={"runId": payload["savedMlRunId"]},
        )
        self.assertEqual(candidates_response.status_code, 200)
        candidates = candidates_response.json()
        self.assertEqual(len(candidates), len(payload["patterns"]))
        self.assertTrue(all(row["candidateType"] == "harmonic" for row in candidates))

    def test_source_registry_and_missing_optional_adapter_are_safe(self):
        registry_response = self.client.get("/api/sources/registry")
        self.assertEqual(registry_response.status_code, 200)
        names = {row["name"] for row in registry_response.json()}
        self.assertIn("yfinance", names)
        self.assertIn("openchart", names)

        smoke_response = self.client.post(
            "/api/sources/smoke-test",
            params={"source": "openchart", "symbol": "TCS", "timeframe": "5m"},
        )
        self.assertEqual(smoke_response.status_code, 200)
        payload = smoke_response.json()
        self.assertEqual(payload["status"], "FAIL")
        self.assertIn("openchart", payload["error"])

    def test_saved_link_inventory_has_complete_machine_readable_roles(self):
        urls = load_saved_link_inventory()
        self.assertEqual(len(urls), 211)
        records = classify_registry_urls(urls)
        self.assertEqual(len(records), len(urls))
        self.assertFalse(
            [record for record in records if record.source_role == "UNCLASSIFIED"]
        )
        self.assertTrue(all(record.allowed_jobs for record in records))
        self.assertTrue(
            all(
                not record.can_unlock_ready
                for record in records
                if record.source_role
                in {"REFERENCE_ONLY", "SECONDARY_DISCOVERY", "UNOFFICIAL_RESEARCH"}
            )
        )

    def test_source_contract_coverage_endpoint_is_fail_closed_and_complete(self):
        coverage = build_registry_coverage()
        self.assertGreater(coverage.inventory_url_count, 300)
        self.assertEqual(
            coverage.classified_url_count + coverage.unclassified_url_count,
            coverage.inventory_url_count,
        )
        self.assertEqual(coverage.active_source_count, coverage.contracted_source_count)
        self.assertEqual(coverage.gate_source_count, 0)
        self.assertGreater(coverage.pending_live_verification_count, 0)
        self.assertEqual(coverage.compiler_state, "OK")
        self.assertFalse(coverage.source_activation_ready)
        self.assertTrue(
            all(not row.standalone_ready_authority for row in coverage.active_sources)
        )
        self.assertTrue(all(not row.can_unlock_gate for row in coverage.active_sources))
        self.assertTrue(
            all(row.missing_contract_fields for row in coverage.active_sources)
        )
        self.assertEqual(
            len({row.source_key for row in coverage.active_sources}),
            len(coverage.active_sources),
        )

        response = self.client.get("/api/source-contracts/coverage")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(payload["inventoryUrlCount"], 300)
        self.assertEqual(payload["gateSourceCount"], 0)
        self.assertFalse(payload["sourceActivationReady"])
        self.assertEqual(payload["activeSourceCount"], payload["contractedSourceCount"])

    def test_nse_frame_adapter_handles_nselib_comma_price_schema(self):
        frame = pd.DataFrame(
            [
                {
                    "Date": "07-Jul-2026",
                    "OpenPrice": "1,323.50",
                    "HighPrice": "1,328.00",
                    "LowPrice": "1,304.10",
                    "ClosePrice": "1,308.40",
                    "TotalTradedQuantity": 14335554,
                }
            ]
        )
        candles = _nse_frame_to_candles(
            frame, "RELIANCE", "1d", "nselib", DataTrust.UNOFFICIAL_WRAPPER
        )
        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0].open, 1323.5)
        self.assertEqual(candles[0].close, 1308.4)
        self.assertEqual(candles[0].volume, 14335554.0)

    def test_source_monitor_catalog_check_history_and_scheduler(self):
        catalog_response = self.client.get("/api/source-monitor/catalog")
        self.assertEqual(catalog_response.status_code, 200)
        catalog = catalog_response.json()
        keys = {row["key"] for row in catalog}
        self.assertIn("amfi_monthly_portfolio", keys)
        self.assertIn("nse_participant_oi", keys)
        self.assertIn("mcx_bhavcopy", keys)
        self.assertIn("world_gold_council_oi", keys)
        self.assertIn("wgc_gold_etf_holdings", keys)
        self.assertIn("wgc_gold_etf_flows", keys)
        self.assertIn("sge_daily_report", keys)
        self.assertIn("lme_warehouse_stocks", keys)
        self.assertIn("mcx_delivery_reports", keys)
        self.assertIn("yfinance", keys)

        check_response = self.client.post(
            "/api/source-monitor/check",
            params={"sourceKey": "amfi_monthly_portfolio", "fetch": False},
        )
        self.assertEqual(check_response.status_code, 200)
        check_payload = check_response.json()
        self.assertEqual(check_payload["checked"], 1)
        self.assertEqual(check_payload["skippedCount"], 1)

        history_response = self.client.get(
            "/api/source-monitor/history",
            params={"sourceKey": "amfi_monthly_portfolio"},
        )
        self.assertEqual(history_response.status_code, 200)
        self.assertGreaterEqual(len(history_response.json()), 1)

        run_response = self.client.post(
            "/api/source-monitor/scheduler/run-once",
            params={"fetch": False, "sourceKey": "nse_fii_dii"},
        )
        self.assertEqual(run_response.status_code, 200)
        self.assertEqual(run_response.json()["checked"], 1)

        status_response = self.client.get("/api/source-monitor/scheduler/status")
        self.assertEqual(status_response.status_code, 200)
        self.assertIn("lastRunAt", status_response.json())

    def test_source_monitor_detects_new_unchanged_and_changed_content(self):
        descriptor = get_source_descriptor("nse_bhavcopy_eod")
        self.assertIsNotNone(descriptor)

        first = storage.save_source_snapshot(
            build_source_snapshot(
                descriptor,
                status_code=200,
                content=b"same-content",
                headers={"last-modified": "Mon, 06 Jul 2026 10:00:00 GMT"},
            )
        )
        second = storage.save_source_snapshot(
            build_source_snapshot(
                descriptor,
                status_code=200,
                content=b"same-content",
                headers={"last-modified": "Mon, 06 Jul 2026 10:00:00 GMT"},
            )
        )
        third = storage.save_source_snapshot(
            build_source_snapshot(
                descriptor,
                status_code=200,
                content=b"changed-content",
                headers={"last-modified": "Tue, 07 Jul 2026 10:00:00 GMT"},
            )
        )

        self.assertEqual(first.check_state, "NEW")
        self.assertEqual(second.check_state, "UNCHANGED")
        self.assertEqual(third.check_state, "CHANGED")
        self.assertTrue(first.raw_path)
        self.assertTrue(third.changed)

    def test_source_monitor_hash_change_wins_over_stale_http_headers(self):
        descriptor = get_source_descriptor("cftc_cot")
        self.assertIsNotNone(descriptor)
        stable_header = {"last-modified": "Mon, 06 Jul 2026 19:30:20 GMT"}

        first = storage.save_source_snapshot(
            build_source_snapshot(
                descriptor,
                status_code=200,
                content=b"dynamic token A same-length",
                headers=stable_header,
            )
        )
        second = storage.save_source_snapshot(
            build_source_snapshot(
                descriptor,
                status_code=200,
                content=b"dynamic token B same-length",
                headers=stable_header,
            )
        )

        self.assertEqual(first.check_state, "NEW")
        self.assertEqual(second.check_state, "CHANGED")
        self.assertTrue(second.changed)

    def test_source_parser_waits_without_snapshot_and_parses_cftc_links(self):
        wait_response = self.client.post(
            "/api/source-parser/run",
            params={"sourceKey": "cftc_cot"},
        )
        self.assertEqual(wait_response.status_code, 200)
        wait_payload = wait_response.json()
        self.assertEqual(wait_payload[0]["parserState"], "WAIT_SOURCE_SNAPSHOT")

        descriptor = get_source_descriptor("cftc_cot")
        html = b"""
        <html><body>
          <a href="/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm">Historical COT</a>
          <a href="/dea/newcot/deafut.txt">Current Legacy Futures Only</a>
          <a href="/not-relevant">About</a>
        </body></html>
        """
        snapshot = storage.save_source_snapshot(
            build_source_snapshot(
                descriptor,
                status_code=200,
                content=html,
                headers={"last-modified": "Mon, 06 Jul 2026 19:30:20 GMT"},
            )
        )
        self.assertEqual(snapshot.check_state, "NEW")

        parse_response = self.client.post(
            "/api/source-parser/run",
            params={"sourceKey": "cftc_cot"},
        )
        self.assertEqual(parse_response.status_code, 200)
        parsed = parse_response.json()[0]
        self.assertEqual(parsed["parserState"], "PARSED_METADATA_ONLY")
        self.assertGreaterEqual(parsed["recordCount"], 2)
        self.assertIn("reportLinks", parsed["output"])

        history_response = self.client.get(
            "/api/source-parser/results",
            params={"sourceKey": "cftc_cot"},
        )
        self.assertEqual(history_response.status_code, 200)
        self.assertGreaterEqual(len(history_response.json()), 2)

    def test_gate_readiness_blocks_ready_without_structured_source_parsers(self):
        response = self.client.get(
            "/api/gates/readiness", params={"symbol": "RELIANCE"}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["symbol"], "RELIANCE")
        gates = {row["code"]: row for row in payload["gates"]}
        self.assertIn("G12_SMART_MONEY", gates)
        self.assertIn("G13_OI_CONFIRMS", gates)
        self.assertNotEqual(gates["G12_SMART_MONEY"]["tradeGateEffect"], "CAN_CONFIRM")
        self.assertNotEqual(gates["G13_OI_CONFIRMS"]["tradeGateEffect"], "CAN_CONFIRM")

    def save_source_content(self, source_key, content: bytes):
        descriptor = get_source_descriptor(source_key)
        self.assertIsNotNone(descriptor)
        return storage.save_source_snapshot(
            build_source_snapshot(
                descriptor,
                status_code=200,
                content=content,
                headers={"last-modified": "Wed, 08 Jul 2026 12:00:00 GMT"},
            )
        )

    def test_structured_mwpl_parser_does_not_pass_full_oi_gate_alone(self):
        today = datetime.now(timezone.utc).date().isoformat()
        content = f"""Report Date: {today}
Symbol,MWPL,Total OI,Percentage
RELIANCE,1000000,450000,45.0
TCS,1000000,925000,92.5
""".encode()
        self.save_source_content("nse_mwpl_percentages", content)

        response = self.client.post(
            "/api/source-parser/run", params={"sourceKey": "nse_mwpl_percentages"}
        )
        self.assertEqual(response.status_code, 200)
        parsed = response.json()[0]
        self.assertEqual(parsed["parserState"], "PARSED_STRUCTURED")
        self.assertEqual(parsed["recordCount"], 2)
        rows = {row["symbol"]: row for row in parsed["output"]["rows"]}
        self.assertEqual(rows["RELIANCE"]["banStatus"], "SAFE")
        self.assertEqual(rows["TCS"]["banStatus"], "ORANGE")

        gate = self.client.get(
            "/api/gates/readiness", params={"symbol": "RELIANCE"}
        ).json()
        gates = {row["code"]: row for row in gate["gates"]}
        self.assertNotEqual(gates["G13_OI_CONFIRMS"]["state"], "PASS")
        self.assertNotEqual(gates["G13_OI_CONFIRMS"]["tradeGateEffect"], "CAN_CONFIRM")

        domain = self.client.get(
            "/api/source-parser/domain-rows",
            params={"sourceKey": "nse_mwpl_percentages"},
        )
        self.assertEqual(domain.status_code, 200)
        self.assertGreaterEqual(len(domain.json()["rows"]), 2)

        archive = self.client.get(
            "/api/raw-source-archive", params={"sourceKey": "nse_mwpl_percentages"}
        )
        self.assertEqual(archive.status_code, 200)
        self.assertGreaterEqual(len(archive.json()), 1)
        self.assertEqual(
            archive.json()[0]["parser_state_after_parse"], "PARSED_STRUCTURED"
        )

    def test_official_fno_ban_is_a_symbol_level_hard_veto(self):
        self.save_source_content(
            "nse_fno_ban",
            b"Securities in Ban For Trade Date 13-JUL-2026:\n1,KAYNES\n",
        )
        parsed = self.client.post(
            "/api/source-parser/run", params={"sourceKey": "nse_fno_ban"}
        ).json()[0]
        self.assertEqual(parsed["output"]["evidenceCoverage"], "FNO_BAN_ONLY")

        gates = self.client.get(
            "/api/gates/readiness", params={"symbol": "KAYNES"}
        ).json()
        g13 = {row["code"]: row for row in gates["gates"]}["G13_OI_CONFIRMS"]
        self.assertEqual(g13["state"], "BLOCKED_FNO_BAN")
        self.assertEqual(g13["tradeGateEffect"], "DO_NOT_PASS_READY")

    def test_structured_large_deals_parser_confirms_stock_level_anchor(self):
        today = datetime.now(timezone.utc).date().isoformat()
        content = f"""Date: {today}
Symbol,Buyer,Seller,Quantity,Price,Close Price,Deal Type
RELIANCE,Blackstone,Public,100000,102.00,100.00,BULK
""".encode()
        self.save_source_content("nse_large_deals", content)

        response = self.client.post(
            "/api/source-parser/run", params={"sourceKey": "nse_large_deals"}
        )
        self.assertEqual(response.status_code, 200)
        parsed = response.json()[0]
        self.assertEqual(parsed["parserState"], "PARSED_STRUCTURED")
        self.assertEqual(parsed["output"]["anchors"][0]["anchorType"], "BUYER_PREMIUM")

        gate = self.client.get(
            "/api/gates/readiness", params={"symbol": "RELIANCE"}
        ).json()
        gates = {row["code"]: row for row in gate["gates"]}
        self.assertEqual(gates["G12_SMART_MONEY"]["state"], "WAIT_SOURCE_ACTIVATION")
        self.assertEqual(
            gates["G12_SMART_MONEY"]["tradeGateEffect"], "DO_NOT_PASS_READY"
        )

    def test_metadata_empty_stale_and_parse_states_block_ready(self):
        today = datetime.now(timezone.utc).date().isoformat()
        self.assertFalse(is_data_date_fresh("cftc_cot", None))
        self.assertFalse(is_data_date_fresh("unknown_source", today))

        html = (
            b"<html><body><a href='/dea/newcot/deafut.txt'>COT file</a></body></html>"
        )
        self.save_source_content("cftc_cot", html)
        parsed = self.client.post(
            "/api/source-parser/run", params={"sourceKey": "cftc_cot"}
        ).json()[0]
        self.assertEqual(parsed["parserState"], "PARSED_METADATA_ONLY")
        self.assertEqual(dependency_state("cftc_cot")["state"], "WAIT_STRUCTURED_PARSE")

        stale_content = b"Report Date: 2000-01-01\nSymbol,MWPL,Total OI,Percentage\nRELIANCE,1000,500,50"
        self.save_source_content("nse_mwpl_percentages", stale_content)
        stale = self.client.post(
            "/api/source-parser/run", params={"sourceKey": "nse_mwpl_percentages"}
        ).json()[0]
        self.assertEqual(stale["parserState"], "PARSED_STRUCTURED")
        self.assertEqual(
            dependency_state("nse_mwpl_percentages")["state"], "WAIT_STALE_DATA"
        )

    def test_new_snapshot_blocks_old_structured_parse_until_reparsed(self):
        today = datetime.now(timezone.utc).date().isoformat()
        content = f"Report Date: {today}\nSymbol,MWPL,Total OI,Percentage\nRELIANCE,1000,500,50\n".encode()
        self.save_source_content("nse_mwpl_percentages", content)
        self.client.post(
            "/api/source-parser/run", params={"sourceKey": "nse_mwpl_percentages"}
        )
        self.assertEqual(
            dependency_state("nse_mwpl_percentages")["state"],
            "WAIT_SOURCE_ACTIVATION",
        )
        self.save_source_content("nse_mwpl_percentages", content + b"TCS,1000,500,50\n")
        self.assertEqual(
            dependency_state("nse_mwpl_percentages")["state"],
            "WAIT_PARSE_LATEST_SNAPSHOT",
        )

    def test_participant_amfi_cftc_and_mcx_structured_parsers_keep_scope_labels(self):
        today = datetime.now(timezone.utc).date().isoformat()
        fixtures = {
            "nse_participant_oi": f"""Report Date: {today}
Participant Type,Future Index Long,Future Index Short,Option Index Long,Option Index Short
FII,5000,1000,3000,1000
DII,2000,500,1000,200
""".encode(),
            "amfi_monthly_portfolio": f"""Report Date: {today}
AMC,Scheme,ISIN,Stock,Quantity,Market Value,Percent AUM
SBI MF,SBI Bluechip,INE002A01018,RELIANCE,100000,1000000000,5.0
HDFC MF,HDFC Top 100,INE002A01018,RELIANCE,80000,800000000,4.0
""".encode(),
            "cftc_cot": f"""Market_and_Exchange_Names,Report_Date_as_YYYY-MM-DD,Open_Interest_All,M_Money_Positions_Long_All,M_Money_Positions_Short_All,Prod_Merc_Positions_Long_All,Prod_Merc_Positions_Short_All,NonRept_Positions_Long_All,NonRept_Positions_Short_All
GOLD - COMEX,{today},100000,60000,30000,20000,25000,5000,3000
""".encode(),
            "mcx_bhavcopy": f"""Date: {today}
Symbol,Expiry,Close,Volume,Open Interest,Change in OI
GOLD,2026-08-05,68940,12000,45000,4200
""".encode(),
        }
        for source_key, content in fixtures.items():
            self.save_source_content(source_key, content)
            response = self.client.post(
                "/api/source-parser/run", params={"sourceKey": source_key}
            )
            self.assertEqual(response.status_code, 200)
            parsed = response.json()[0]
            self.assertEqual(parsed["parserState"], "PARSED_STRUCTURED")
            self.assertGreater(parsed["recordCount"], 0)

        participant = storage.get_latest_source_parse_result("nse_participant_oi")
        self.assertEqual(participant.output["scope"], "AGGREGATE_CONTEXT_ONLY")
        amfi = storage.get_latest_source_parse_result("amfi_monthly_portfolio")
        self.assertEqual(amfi.output["scope"], "SWING_CONFIRMATION_ONLY")
        cftc = storage.get_latest_source_parse_result("cftc_cot")
        self.assertEqual(cftc.output["scope"], "COMMODITY_REGIME_ONLY")
        mcx = storage.get_latest_source_parse_result("mcx_bhavcopy")
        self.assertEqual(mcx.output["scope"], "MCX_FUTURES_EOD_CONFIRMATION")

    def test_fo_slb_corporate_and_sebi_parser_contracts(self):
        today = datetime.now(timezone.utc).date().isoformat()
        fixtures = {
            "nse_fo_bhavcopy": f"""Report Date: {today}
Ticker Symbol,Financial Instrument Type,Expiry Date,Closing Price,Previous Closing Price,Underlying Price,Open Interest,Change in Open Interest,Total Trading Volume
RELIANCE,FUTSTK,2026-07-30,1510,1500,1490,100000,5000,25000
""".encode(),
            "nse_slb": f"""Report Date: {today}
Symbol,Open Positions,Volume,Annualised Yield,Turnover
RELIANCE,10000,2500,12.5,50000000
""".encode(),
            "nse_corporate_filings_actions": f"""Report Date: {today}
Symbol,Company Name,Action Type,Announcement Date,Ex Date,Record Date,Offer Price,Quantity
RELIANCE,Reliance Industries,BUYBACK,{today},2026-07-20,2026-07-21,1600,1000000
""".encode(),
            "sebi_pit_sast": f"""Report Date: {today}
Symbol,ISIN,Person Name,Relationship,Transaction Type,Transaction Date,Disclosure Date,Quantity,Price,Pre Holding,Post Holding
RELIANCE,INE002A01018,Promoter A,PROMOTER,OPEN MARKET BUY,{today},{today},100000,1500,50,50.1
""".encode(),
        }
        for source_key, content in fixtures.items():
            self.save_source_content(source_key, content)
            response = self.client.post(
                "/api/source-parser/run", params={"sourceKey": source_key}
            )
            self.assertEqual(response.status_code, 200)
            parsed = response.json()[0]
            self.assertEqual(parsed["parserState"], "PARSED_STRUCTURED")
            self.assertGreater(parsed["recordCount"], 0)
            domain = self.client.get(
                "/api/source-parser/domain-rows", params={"sourceKey": source_key}
            )
            self.assertEqual(domain.status_code, 200)
            self.assertGreater(len(domain.json()["rows"]), 0)

        fo = storage.get_latest_source_parse_result("nse_fo_bhavcopy")
        self.assertEqual(fo.output["rows"][0]["oiQuadrant"], "LONG_BUILD_UP")
        self.assertEqual(fo.output["rows"][0]["basis"], 20)
        slb = storage.get_latest_source_parse_result("nse_slb")
        self.assertEqual(slb.output["rows"][0]["pressure"], "HIGH_BORROW_PRESSURE")
        sebi = storage.get_latest_source_parse_result("sebi_pit_sast")
        self.assertEqual(
            sebi.output["rows"][0]["evidenceType"], "DIRECT_PUBLIC_DISCLOSURE"
        )

    def test_g13_waits_for_percentages_when_ban_and_fo_are_fresh(self):
        today = datetime.now(timezone.utc).date().isoformat()
        self.save_source_content(
            "nse_fno_ban",
            f"Securities in Ban For Trade Date {today}:\n".encode(),
        )
        self.client.post("/api/source-parser/run", params={"sourceKey": "nse_fno_ban"})
        self.save_source_content(
            "nse_fo_bhavcopy",
            f"""Report Date: {today}
Ticker Symbol,Financial Instrument Type,Expiry Date,Closing Price,Previous Closing Price,Underlying Price,Open Interest,Change in Open Interest,Total Trading Volume
RELIANCE,FUTSTK,2026-07-30,1510,1500,1490,100000,5000,25000
""".encode(),
        )
        self.client.post(
            "/api/source-parser/run", params={"sourceKey": "nse_fo_bhavcopy"}
        )

        self.assertEqual(
            dependency_state("nse_fno_ban")["state"], "WAIT_SOURCE_ACTIVATION"
        )
        self.assertEqual(
            dependency_state("nse_mwpl_percentages")["state"],
            "WAIT_MWPL_PERCENTAGES",
        )
        payload = self.client.get(
            "/api/gates/readiness", params={"symbol": "RELIANCE"}
        ).json()
        g13 = {row["code"]: row for row in payload["gates"]}["G13_OI_CONFIRMS"]
        self.assertEqual(g13["state"], "WAIT_SOURCE_ACTIVATION")
        self.assertNotEqual(g13["tradeGateEffect"], "CAN_CONFIRM")

    def test_g13_requires_both_mwpl_and_fo_evidence(self):
        today = datetime.now(timezone.utc).date().isoformat()
        self.save_source_content(
            "nse_mwpl_percentages",
            f"Report Date: {today}\nSymbol,MWPL,Total OI,Percentage\nRELIANCE,1000000,450000,45.0\n".encode(),
        )
        self.client.post(
            "/api/source-parser/run", params={"sourceKey": "nse_mwpl_percentages"}
        )
        self.save_source_content(
            "nse_fno_ban",
            f"Securities in Ban For Trade Date {today}:\n".encode(),
        )
        self.client.post("/api/source-parser/run", params={"sourceKey": "nse_fno_ban"})
        before = self.client.get(
            "/api/gates/readiness", params={"symbol": "RELIANCE"}
        ).json()
        self.assertNotEqual(
            {row["code"]: row for row in before["gates"]}["G13_OI_CONFIRMS"]["state"],
            "PASS",
        )

        self.save_source_content(
            "nse_fo_bhavcopy",
            f"""Report Date: {today}
Ticker Symbol,Financial Instrument Type,Expiry Date,Closing Price,Previous Closing Price,Underlying Price,Open Interest,Change in Open Interest,Total Trading Volume
RELIANCE,FUTSTK,2026-07-30,1510,1500,1490,100000,5000,25000
""".encode(),
        )
        self.client.post(
            "/api/source-parser/run", params={"sourceKey": "nse_fo_bhavcopy"}
        )
        after = self.client.get(
            "/api/gates/readiness", params={"symbol": "RELIANCE"}
        ).json()
        g13_after = {row["code"]: row for row in after["gates"]}["G13_OI_CONFIRMS"]
        self.assertEqual(g13_after["state"], "WAIT_SOURCE_ACTIVATION")
        self.assertEqual(g13_after["tradeGateEffect"], "DO_NOT_PASS_READY")
        self.assertTrue(
            all(
                source["compilerActivationReady"] is False
                and source["contractGatePermission"] is False
                for source in g13_after["sources"]
            )
        )
        wrong_symbol = self.client.get(
            "/api/gates/readiness", params={"symbol": "TCS"}
        ).json()
        self.assertNotEqual(
            {row["code"]: row for row in wrong_symbol["gates"]}["G13_OI_CONFIRMS"][
                "state"
            ],
            "PASS",
        )

    def test_cftc_official_headerless_disaggregated_file_parses_positions(self):
        today = datetime.now(timezone.utc).date().isoformat()
        content = f""""GOLD - COMMODITY EXCHANGE INC.",260708,{today},088691,CMX ,00,088 ,100000,20000,25000,10000,12000,500,60000,30000,7000,5000,6000,1000,95000,93000,5000,7000,"(CONTRACTS)","088691","CMX ","088 ","A10","FutOnly"
"SILVER - COMMODITY EXCHANGE INC.",260708,{today},084691,CMX ,00,084 ,50000,9000,12000,3000,5000,200,22000,18000,1000,7000,4000,500,45000,43000,5000,7000,"(CONTRACTS)","084691","CMX ","084 ","A10","FutOnly"
""".encode()
        self.save_source_content("cftc_cot", content)

        response = self.client.post(
            "/api/source-parser/run", params={"sourceKey": "cftc_cot"}
        )
        self.assertEqual(response.status_code, 200)
        parsed = response.json()[0]
        self.assertEqual(parsed["parserState"], "PARSED_STRUCTURED")
        self.assertEqual(parsed["recordCount"], 2)
        self.assertEqual(parsed["output"]["positions"][0]["managedMoneyNet"], 30000.0)
        self.assertEqual(parsed["output"]["positions"][0]["commercialNet"], -5000.0)
        self.assertEqual(
            parsed["output"]["regimes"][0]["regime"], "MANAGED_MONEY_NET_LONG"
        )
        self.assertEqual(
            parsed["output"]["regimes"][0]["commercialInterpretation"],
            "HEDGING_CATEGORY_CONTEXT_ONLY",
        )
        self.assertEqual(
            parsed["output"]["regimes"][0]["crowdingInterpretation"],
            "WITHHELD_INSUFFICIENT_HISTORY",
        )

        domain_rows = self.client.get(
            "/api/source-parser/domain-rows", params={"sourceKey": "cftc_cot"}
        )
        self.assertEqual(domain_rows.status_code, 200)
        self.assertGreaterEqual(len(domain_rows.json()["rows"]), 2)

        parser_outputs = self.client.get(
            "/api/source-parser/outputs", params={"sourceKey": "cftc_cot"}
        )
        self.assertEqual(parser_outputs.status_code, 200)
        self.assertEqual(parser_outputs.json()[0]["parser_status"], "STRUCTURED_OK")
        self.assertEqual(parser_outputs.json()[0]["freshness_status"], "FRESH")

        freshness = self.client.get("/api/source-freshness-status")
        self.assertEqual(freshness.status_code, 200)
        freshness_by_key = {row["source_key"]: row for row in freshness.json()}
        self.assertTrue(freshness_by_key["cftc_cot"]["is_fresh"])

    def test_cftc_analytics_are_point_in_time_and_detect_crowding(self):
        start = datetime(2020, 1, 7, tzinfo=timezone.utc)
        positions = []
        prices = {}
        for idx in range(261):
            report_date = (start + timedelta(weeks=idx)).date().isoformat()
            managed_net = 10_000 + idx * 100
            positions.append(
                {
                    "market": "GOLD - COMMODITY EXCHANGE INC.",
                    "contract_market_code": "088691",
                    "report_date": report_date,
                    "open_interest": 100_000 + idx * 250,
                    "managed_money_net": managed_net,
                    "commercial_net": -managed_net,
                    "swap_dealer_net": -2_000 + idx,
                    "other_reportable_net": 500 + idx,
                    "non_reportable_net": 1_000 - idx,
                }
            )
            prices[report_date] = 2_500 - idx

        history = build_cftc_feature_history(positions, price_by_date=prices)
        self.assertEqual(len(history), 261)
        latest = history[-1]
        self.assertEqual(latest["managedMoneyNetChange1w"], 100)
        self.assertEqual(latest["managedMoneyPercentile52w"], 1.0)
        self.assertEqual(latest["managedMoneyPercentile260w"], 1.0)
        self.assertEqual(latest["crowdingState"], "CROWDED_LONG")
        self.assertEqual(latest["positionPriceDivergence"], "FUNDS_BUYING_WEAKNESS")
        self.assertFalse(latest["canUnlockReady"])

        cutoff_history = build_cftc_feature_history(
            positions[:200], price_by_date=prices
        )
        self.assertEqual(cutoff_history[-1], history[199])
        self.assertIsNone(history[50]["managedMoneyZscore156w"])

    def test_cftc_historical_parse_persists_analytics_and_reference_is_non_authoritative(
        self,
    ):
        latest_tuesday = datetime.now(timezone.utc).date()
        while latest_tuesday.weekday() != 1:
            latest_tuesday -= timedelta(days=1)
        lines = [
            "Market_and_Exchange_Names,Report_Date_as_YYYY-MM-DD,CFTC_Contract_Market_Code,Open_Interest_All,M_Money_Positions_Long_All,M_Money_Positions_Short_All,Prod_Merc_Positions_Long_All,Prod_Merc_Positions_Short_All,Swap_Positions_Long_All,Swap_Positions_Short_All,Other_Rept_Positions_Long_All,Other_Rept_Positions_Short_All,NonRept_Positions_Long_All,NonRept_Positions_Short_All"
        ]
        dates = []
        for offset in reversed(range(60)):
            report_date = latest_tuesday - timedelta(weeks=offset)
            dates.append(report_date.isoformat())
            idx = 60 - offset
            lines.append(
                f"GOLD - COMMODITY EXCHANGE INC.,{report_date.isoformat()},088691,{100000 + idx * 100},{60000 + idx * 100},30000,20000,25000,10000,12000,5000,6000,5000,7000"
            )
        self.save_source_content("cftc_cot", ("\n".join(lines) + "\n").encode())
        parsed = self.client.post(
            "/api/source-parser/run", params={"sourceKey": "cftc_cot"}
        ).json()[0]
        self.assertEqual(parsed["parserState"], "PARSED_STRUCTURED")
        self.assertEqual(parsed["output"]["historyCount"], 60)

        analytics = self.client.get(
            "/api/cftc/analytics", params={"market": "GOLD", "limit": 5}
        ).json()
        self.assertEqual(analytics["state"], "WAIT_SOURCE_ACTIVATION")
        self.assertEqual(len(analytics["rows"]), 5)
        self.assertEqual(analytics["rows"][0]["reportDate"], dates[-1])
        self.assertEqual(analytics["sourceRole"], "OFFICIAL_DELAYED_CONTEXT")
        self.assertFalse(analytics["canUnlockReady"])

        as_of = self.client.get(
            "/api/cftc/analytics",
            params={"market": "GOLD", "asOf": dates[-10], "limit": 5},
        ).json()
        self.assertTrue(all(row["reportDate"] <= dates[-10] for row in as_of["rows"]))

        replacement_rows = {
            row["source_key"]: row
            for row in self.client.get("/api/source-replacement-map").json()
        }
        reference = replacement_rows["kustex_cftc_cot_report"]
        self.assertEqual(reference["source_role"], "REFERENCE_ONLY_ANALYTICS")
        self.assertFalse(reference["can_unlock_ready"])

    def test_cftc_legacy_layout_is_parsed_and_history_resolver_is_disaggregated_only(
        self,
    ):
        legacy = b"""Market_and_Exchange_Names,Report_Date_as_YYYY-MM-DD,Open_Interest_All,NonComm_Positions_Long_All,NonComm_Positions_Short_All,Comm_Positions_Long_All,Comm_Positions_Short_All
GOLD - COMMODITY EXCHANGE INC.,2026-07-07,100000,60000,30000,20000,25000
"""
        parsed = parse_cftc_cot_positions(legacy)
        self.assertEqual(parsed["parser_state"], "PARSED_STRUCTURED")
        self.assertEqual(
            parsed["output"]["positions"][0]["sourceLayout"], "CFTC_LEGACY"
        )
        self.assertEqual(
            parsed["output"]["positions"][0]["nonCommercialNet"], 30000.0
        )
        self.assertNotIn("managedMoneyNet", parsed["output"]["positions"][0])

        candidates = direct_download_candidates(
            "cftc_cot", today=datetime(2026, 7, 10).date()
        )
        self.assertTrue(any("fut_disagg_txt_2026.zip" in url for url in candidates))
        self.assertFalse(
            any(
                "deafut" in url or "deacom" in url or "dea_com_xls" in url
                for url in candidates
            )
        )

        preview = self.client.post(
            "/api/cftc/history/import", params={"years": 5, "fetch": False}
        )
        self.assertEqual(preview.status_code, 200)
        payload = preview.json()
        self.assertEqual(payload["state"], "WAIT_FETCH_REQUIRED")
        self.assertEqual(len(payload["urls"]), 5)
        self.assertTrue(all("fut_disagg_txt_" in url for url in payload["urls"]))

    def test_cftc_reference_metrics_are_reproduced_without_future_rows(self):
        start = datetime(2025, 1, 7, tzinfo=timezone.utc)
        positions = [
            {
                "market": "GOLD - COMMODITY EXCHANGE INC.",
                "contract_market_code": "088691",
                "report_date": (start + timedelta(weeks=idx)).date().isoformat(),
                "open_interest": 100_000 + idx,
                "managed_money_net": idx,
            }
            for idx in range(52)
        ]
        latest = build_cftc_feature_history(positions)[-1]
        expected_zscore = round((51 - 25.5) / pstdev(range(52)), 4)
        self.assertEqual(latest["managedMoneyMean52w"], 25.5)
        self.assertEqual(latest["managedMoneyZscore52w"], expected_zscore)
        self.assertEqual(latest["managedMoneyNetChange1w"], 1)

    def test_cftc_history_archive_rejects_path_traversal(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("../outside.txt", "unsafe")
        self.assertEqual(
            _validate_archive(buffer.getvalue()), "Archive contains an unsafe path."
        )

    def test_source_replacement_map_and_unlock_helper_are_fail_closed(self):
        response = self.client.get("/api/source-replacement-map")
        self.assertEqual(response.status_code, 200)
        rows = {row["source_key"]: row for row in response.json()}
        self.assertIn("openchart", rows)
        self.assertEqual(rows["openchart"]["source_role"], "UNUSABLE_FAIL_CLOSED")
        self.assertFalse(rows["openchart"]["can_unlock_ready"])
        self.assertFalse(
            can_source_unlock_ready("REFERENCE_ONLY", "STRUCTURED_OK", "FRESH")
        )
        self.assertFalse(
            can_source_unlock_ready(
                "OFFICIAL_GATE_SOURCE", "PARSED_METADATA_ONLY", "FRESH"
            )
        )
        self.assertFalse(
            can_source_unlock_ready("OFFICIAL_GATE_SOURCE", "STRUCTURED_OK", "FRESH")
        )
        self.assertTrue(
            can_source_unlock_ready(
                "OFFICIAL_GATE_SOURCE",
                "STRUCTURED_OK",
                "FRESH",
                source_activation_ready=True,
                compiler_gate_permission=True,
            )
        )
        self.assertTrue(all(not row["can_unlock_ready"] for row in rows.values()))

        result = parser_can_unlock_gate(
            parser_status="PARSED_METADATA_ONLY",
            data_date=datetime.now(timezone.utc).date(),
            record_count=5,
            max_age_days=2,
            can_be_valid_empty=False,
            today=datetime.now(timezone.utc).date(),
        )
        self.assertFalse(result.can_pass)
        self.assertEqual(result.state, "PARSED_METADATA_ONLY")

    def test_source_resolver_candidates_and_scanner_run_are_fail_closed(self):
        resolver = self.client.get(
            "/api/source-resolver/candidates", params={"sourceKey": "cftc_cot"}
        )
        self.assertEqual(resolver.status_code, 200)
        self.assertIn(
            "https://www.cftc.gov/dea/newcot/f_disagg.txt",
            resolver.json()["candidates"],
        )

        storage.save_ohlcv_candles(synthetic_harmonic_candles(symbol="REALSTORED"))
        response = self.client.post(
            "/api/scanner/run-once",
            params={"universe": "WATCHLIST_ONLY", "fetch": False},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "COMPLETE")
        self.assertGreater(payload["candidateCount"], 0)
        self.assertTrue(payload["sourceGatesBlocked"])

        runs = self.client.get("/api/scanner/runs")
        self.assertEqual(runs.status_code, 200)
        self.assertGreaterEqual(len(runs.json()), 1)

        candidates = self.client.get(
            "/api/scanner/candidates", params={"runId": payload["runId"]}
        )
        self.assertEqual(candidates.status_code, 200)
        rows = candidates.json()
        self.assertEqual(len(rows), payload["candidateCount"])
        self.assertTrue(all(not row["final_state"].startswith("READY") for row in rows))
        self.assertEqual({row["symbol"] for row in rows}, {"REALSTORED"})
        causal = rows[0]["payload"]["causalEvaluation"]
        self.assertIn(causal["stage1Label"], {"WAIT", "INELIGIBLE"})
        self.assertEqual(causal["stage2Label"], "BLOCKED")
        self.assertFalse(causal["executable"])
        self.assertTrue(
            any(
                "CAUSE" in reason or "SPONSOR" in reason for reason in causal["reasons"]
            )
        )
        radar = self.client.get("/api/radar").json()
        self.assertEqual({row["symbol"] for row in radar}, {"REALSTORED"})
        self.assertTrue(all(row["statusGroup"] != "ready" for row in radar))

        gate_decisions = self.client.get(
            "/api/gate-decisions", params={"runId": str(payload["runId"])}
        )
        self.assertEqual(gate_decisions.status_code, 200)
        self.assertGreaterEqual(len(gate_decisions.json()), 3)

    def test_scanner_persists_symbol_level_asm_gsm_rejection(self):
        today = datetime.now(timezone.utc).date().strftime("%d-%b-%Y")
        asm = {
            "longterm": {
                "data": [
                    {
                        "asmSurvIndicator": "Stage I",
                        "asmTime": today,
                        "companyName": "Example Limited",
                        "isin": "INE000A01001",
                        "survCode": "LTASM - I (13)",
                        "survDesc": "Long Term Additional Surveillance Measure",
                        "symbol": "EXAMPLE",
                    }
                ]
            },
            "shortterm": {"data": []},
        }
        self.save_source_content("nse_asm", json.dumps(asm).encode())
        self.save_source_content("nse_gsm", b"[]")
        self.client.post("/api/source-parser/run", params={"sourceKey": "nse_asm"})
        self.client.post("/api/source-parser/run", params={"sourceKey": "nse_gsm"})
        storage.save_ohlcv_candles(synthetic_harmonic_candles(symbol="EXAMPLE"))

        run = self.client.post(
            "/api/scanner/run-once",
            params={"universe": "WATCHLIST_ONLY", "fetch": False},
        ).json()
        candidates = self.client.get(
            "/api/scanner/candidates", params={"runId": run["runId"]}
        ).json()
        candidate = next(row for row in candidates if row["symbol"] == "EXAMPLE")
        safety_metric = next(
            row
            for row in candidate["payload"]["metrics"]
            if row["label"] == "ASM/GSM Safety"
        )
        decisions = self.client.get(
            "/api/gate-decisions", params={"runId": str(run["runId"])}
        ).json()
        symbol_decision = next(
            row
            for row in decisions
            if row["symbol"] == "EXAMPLE" and row["gate_key"] == "G03_STOCK_SAFETY"
        )

        self.assertEqual(candidate["final_state"], "REJECT")
        self.assertEqual(safety_metric["value"], "BLOCKED_SURVEILLANCE")
        self.assertEqual(symbol_decision["state"], "BLOCKED_SURVEILLANCE")
        self.assertEqual(symbol_decision["decision"], "DO_NOT_PASS_READY")

    def test_parquet_store_endpoint_writes_stored_candles(self):
        candles = synthetic_harmonic_candles(symbol="PARQ")
        storage.save_ohlcv_candles(candles)

        response = self.client.post(
            "/api/parquet/write",
            params={"symbol": "PARQ", "timeframe": "1d", "source": "synthetic"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["candleCount"], len(candles))
        self.assertTrue(payload["path"].endswith("PARQ.parquet"))

        status_response = self.client.get("/api/parquet/status")
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.json()["available"])

    def test_nse_4h_custom_builder_endpoint(self):
        candles = synthetic_intraday_candles(symbol="INTRA", days=2)
        storage.save_ohlcv_candles(candles)

        response = self.client.post(
            "/api/nse/4h-custom/build",
            params={"symbol": "INTRA", "sourceTimeframe": "5m"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 4)
        self.assertTrue(all(row["timeframe"] == "4h_custom" for row in payload))

    def test_nse_4h_custom_uses_input_interval_for_completeness(self):
        from trendforge_api.nse_session import build_nse_4h_custom

        candles = synthetic_intraday_candles(symbol="COMPLETE", days=1)
        built, warnings = build_nse_4h_custom(candles)
        self.assertEqual(len(built), 2)
        self.assertFalse(any("completeness" in warning for warning in warnings))

    def test_participant_oi_columns_are_not_double_counted(self):
        today = datetime.now(timezone.utc).date().isoformat()
        content = f"""Report Date: {today}
Participant Type,Future Index Long,Future Index Short,Option Index Long,Option Index Short
FII,5000,1000,3000,1000
""".encode()
        parsed = parse_nse_participant_oi(content)
        row = parsed["output"]["rows"][0]
        self.assertEqual(row["futuresLongOi"], 5000)
        self.assertEqual(row["futuresShortOi"], 1000)
        self.assertEqual(row["optionsLongOi"], 3000)
        self.assertEqual(row["optionsShortOi"], 1000)
        self.assertEqual(
            parsed["output"]["regimeBasis"], "FUTURES_ONLY_DIRECTIONAL_PROXY"
        )

    def test_daily_freshness_uses_business_days(self):
        monday = datetime(2026, 7, 13, tzinfo=timezone.utc).date()
        self.assertTrue(
            is_data_date_fresh("nse_mwpl_percentages", "2026-07-10", now=monday)
        )
        self.assertFalse(
            is_data_date_fresh("nse_mwpl_percentages", "2026-07-08", now=monday)
        )

    def test_amfi_xlsx_disclosure_is_parsed(self):
        frame = pd.DataFrame(
            [
                {
                    "AMC": "SBI MF",
                    "Scheme": "SBI Bluechip",
                    "ISIN": "INE002A01018",
                    "Stock": "RELIANCE",
                    "Quantity": 100000,
                    "Market Value": 1000000000,
                    "Percent AUM": 5.0,
                }
            ]
        )
        payload = BytesIO()
        with pd.ExcelWriter(payload, engine="openpyxl") as writer:
            frame.to_excel(writer, index=False, sheet_name="Portfolio")
        parsed = parse_amfi_portfolio(
            payload.getvalue(), last_modified="Fri, 10 Jul 2026 10:00:00 GMT"
        )
        self.assertEqual(parsed["parser_state"], "PARSED_STRUCTURED")
        self.assertEqual(parsed["record_count"], 1)
        self.assertEqual(parsed["output"]["holdings"][0]["stock"], "RELIANCE")

    def test_amfi_deltas_compare_against_prior_month(self):
        june = b"""Report Date: 2026-06-30
AMC,Scheme,ISIN,Stock,Quantity,Market Value,Percent AUM
SBI MF,SBI Bluechip,INE002A01018,RELIANCE,100,100000,5
"""
        july = b"""Report Date: 2026-07-10
AMC,Scheme,ISIN,Stock,Quantity,Market Value,Percent AUM
SBI MF,SBI Bluechip,INE002A01018,RELIANCE,130,130000,5
"""
        self.save_source_content("amfi_monthly_portfolio", june)
        self.client.post(
            "/api/source-parser/run", params={"sourceKey": "amfi_monthly_portfolio"}
        )
        self.save_source_content("amfi_monthly_portfolio", july)
        self.client.post(
            "/api/source-parser/run", params={"sourceKey": "amfi_monthly_portfolio"}
        )
        conn = storage.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM amfi_stock_deltas WHERE stock = 'RELIANCE'"
            ).fetchall()
        finally:
            conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["net_quantity_change"], 30)
        self.assertEqual(rows[0]["schemes_added"], 0)

    def test_amfi_deltas_track_added_reduced_and_exited_schemes(self):
        june = b"""Report Date: 2026-06-30
AMC,Scheme,ISIN,Stock,Quantity,Market Value,Percent AUM
SBI MF,SBI Bluechip,INE002A01018,RELIANCE,100,100000,5
HDFC MF,HDFC Top 100,INE002A01018,RELIANCE,50,50000,3
"""
        july = b"""Report Date: 2026-07-31
AMC,Scheme,ISIN,Stock,Quantity,Market Value,Percent AUM
SBI MF,SBI Bluechip,INE002A01018,RELIANCE,80,80000,4
ICICI MF,ICICI Value,INE002A01018,RELIANCE,20,20000,1
"""
        self.save_source_content("amfi_monthly_portfolio", june)
        self.client.post(
            "/api/source-parser/run", params={"sourceKey": "amfi_monthly_portfolio"}
        )
        self.save_source_content("amfi_monthly_portfolio", july)
        self.client.post(
            "/api/source-parser/run", params={"sourceKey": "amfi_monthly_portfolio"}
        )
        conn = storage.connect()
        try:
            row = conn.execute(
                "SELECT * FROM amfi_stock_deltas WHERE disclosure_month = '2026-07' AND stock = 'RELIANCE'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["schemes_added"], 1)
        self.assertEqual(row["schemes_reduced"], 1)
        self.assertEqual(row["schemes_exited"], 1)
        self.assertEqual(row["net_quantity_change"], -50)

    def test_sqlite_connections_enable_integrity_pragmas(self):
        storage.init_db()
        conn = storage.connect()
        try:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(
                conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal"
            )
            self.assertGreaterEqual(
                conn.execute("PRAGMA busy_timeout").fetchone()[0], 5000
            )
        finally:
            conn.close()

    def test_position_sizing_is_postponed_and_never_executable(self):
        sized = calculate_position_size(
            PositionSizingInput(
                entry=100,
                stop=95,
                target=112,
                confidence=85,
                source_ready=True,
                candidate_state="READY",
            )
        )
        self.assertEqual(sized.quantity, 0)
        self.assertEqual(sized.max_loss, 0)
        self.assertFalse(sized.executable)
        self.assertEqual(sized.state, "POSTPONED_NO_QUANTITY")

        blocked = calculate_position_size(
            PositionSizingInput(
                entry=100,
                stop=95,
                target=112,
                confidence=95,
                source_ready=False,
                candidate_state="READY",
            )
        )
        self.assertEqual(blocked.quantity, 0)
        self.assertFalse(blocked.executable)
        self.assertEqual(blocked.state, "POSTPONED_NO_QUANTITY")

    def test_black_scholes_and_iv_reference_round_trip(self):
        price = black_scholes_price(
            spot=100,
            strike=100,
            time_years=1,
            rate=0.05,
            volatility=0.20,
            option_type="call",
        )
        self.assertAlmostEqual(price, 10.4506, places=3)
        solved = implied_volatility(
            market_price=price,
            spot=100,
            strike=100,
            time_years=1,
            rate=0.05,
            option_type="call",
        )
        self.assertAlmostEqual(solved, 0.20, places=4)
        greeks = black_scholes_greeks(
            spot=100,
            strike=100,
            time_years=1,
            rate=0.05,
            volatility=0.20,
            option_type="call",
        )
        self.assertAlmostEqual(greeks.delta, 0.6368, places=3)
        self.assertGreater(greeks.gamma, 0)

    def test_risk_settings_and_derivatives_api(self):
        settings = self.client.get("/api/settings/risk")
        self.assertEqual(settings.status_code, 200)
        self.assertEqual(settings.json()["account_size"], 100000)

        updated = settings.json()
        updated["max_open_positions"] = 2
        response = self.client.put("/api/settings/risk", json=updated)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["max_open_positions"], 2)

        sized = self.client.post(
            "/api/risk/position-size",
            json={
                "entry": 100,
                "stop": 95,
                "target": 112,
                "confidence": 85,
                "candidate_state": "READY",
                "source_ready": True,
            },
        )
        self.assertEqual(sized.status_code, 200)
        self.assertEqual(sized.json()["quantity"], 0)
        self.assertFalse(sized.json()["executable"])
        self.assertEqual(sized.json()["state"], "POSTPONED_NO_QUANTITY")

        priced = self.client.post(
            "/api/derivatives/price",
            json={
                "spot": 100,
                "strike": 100,
                "time_years": 1,
                "rate": 0.05,
                "volatility": 0.2,
                "option_type": "call",
            },
        )
        self.assertEqual(priced.status_code, 200)
        self.assertAlmostEqual(priced.json()["price"], 10.4506, places=3)

    def test_outcome_labeller_uses_conservative_same_bar_rule(self):
        candle = OHLCVCandle(
            symbol="PATH",
            timeframe="1d",
            source="synthetic",
            timestamp="2026-07-10T00:00:00+00:00",
            open=100,
            high=112,
            low=94,
            close=105,
            volume=1000,
            trustLevel=DataTrust.SYNTHETIC_TEST,
            fetchedAt=datetime.now(timezone.utc).isoformat(),
        )
        outcome = label_price_path(
            [candle], entry=100, stop=95, target=110, direction="bullish"
        )
        self.assertEqual(outcome.label, "LOSS")
        self.assertEqual(outcome.bars, 1)

    def test_point_in_time_features_are_finite_and_cutoff_bound(self):
        candles = synthetic_harmonic_candles(symbol="FEATURE")
        features = build_point_in_time_features(candles)
        self.assertEqual(features["state"], "OK")
        self.assertEqual(features["dataCutoff"], candles[-1].timestamp)
        self.assertEqual(features["featureVersion"], "1.1.0")
        self.assertEqual(features["featureRegistryVersion"], "1.1.0")
        self.assertEqual(features["indicatorEngineId"], "trendforge.numpy-pandas")
        self.assertEqual(features["indicatorEngineVersion"], "1.0.0")
        self.assertIn("atr14Percent", features)

    def test_scanner_rejects_overlapping_run(self):
        scheduler = ScannerScheduler()
        scheduler._run_lock.acquire()
        try:
            result = scheduler.run_once()
        finally:
            scheduler._run_lock.release()
        self.assertEqual(result["status"], "SKIPPED_ALREADY_RUNNING")

    def test_scanner_rejects_unknown_universe(self):
        scheduler = ScannerScheduler()
        result = scheduler.run_once(universe="ALL_THE_INTERNET")
        self.assertEqual(result["status"], "REJECT_INVALID_UNIVERSE")

    def test_scheduler_configuration_is_persisted(self):
        storage.save_scheduler_config(
            "scanner",
            enabled=True,
            interval_seconds=900,
            universe="WATCHLIST_ONLY",
            fetch=False,
        )
        config = storage.get_scheduler_config("scanner")
        self.assertEqual(config["enabled"], 1)
        self.assertEqual(config["interval_seconds"], 900)
        self.assertEqual(config["universe"], "WATCHLIST_ONLY")

    def test_research_input_limits_are_enforced(self):
        response = self.client.post(
            "/api/research-records",
            json={"symbol": "COFORGE", "note": "x" * 5001, "tags": []},
        )
        self.assertEqual(response.status_code, 422)

    def test_validation_endpoint_persists_report(self):
        candles = synthetic_harmonic_candles(symbol="VALIDATE", count_prefix=80)
        storage.save_ohlcv_candles(candles)
        response = self.client.post(
            "/api/validation/harmonic-backtest",
            params={
                "symbol": "VALIDATE",
                "timeframe": "1d",
                "source": "synthetic",
                "warmup": 80,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["validationRunId"])
        runs = self.client.get("/api/validation/runs", params={"symbol": "VALIDATE"})
        self.assertEqual(runs.status_code, 200)
        self.assertEqual(len(runs.json()), 1)

    def test_advanced_harmonic_analysis_alert_benchmark_and_overlay(self):
        candles = synthetic_harmonic_candles(symbol="ADV")
        storage.save_ohlcv_candles(candles)

        analysis_response = self.client.post(
            "/api/harmonic/advanced/analyze",
            params={"symbol": "ADV", "timeframe": "1d", "persistAlerts": True},
        )
        self.assertEqual(analysis_response.status_code, 200)
        analysis = analysis_response.json()
        self.assertEqual(analysis["symbol"], "ADV")
        self.assertIn("finalState", analysis)
        self.assertGreaterEqual(len(analysis["gates"]), 10)
        self.assertIn("hybridQualityScore", analysis)

        benchmark_response = self.client.post(
            "/api/harmonic/benchmark",
            params={"symbol": "ADV", "timeframe": "1d"},
        )
        self.assertEqual(benchmark_response.status_code, 200)
        self.assertIn("durationSeconds", benchmark_response.json())

        overlay_response = self.client.get(
            "/api/harmonic/chart-overlay",
            params={"symbol": "ADV", "timeframe": "1d"},
        )
        self.assertEqual(overlay_response.status_code, 200)
        overlay = overlay_response.json()
        self.assertEqual(overlay["symbol"], "ADV")
        self.assertIn("pivots", overlay)
        self.assertIn("finalState", overlay)

        alerts_response = self.client.get(
            "/api/harmonic/alerts", params={"symbol": "ADV"}
        )
        self.assertEqual(alerts_response.status_code, 200)
        self.assertIsInstance(alerts_response.json(), list)

    def test_liquidity_prefilter_endpoint(self):
        candles = synthetic_harmonic_candles(symbol="LIQ")
        storage.save_ohlcv_candles(candles)

        response = self.client.get(
            "/api/harmonic/liquidity-check",
            params={
                "symbol": "LIQ",
                "timeframe": "1d",
                "minAvgVolume": 500,
                "minPrice": 50,
                "minAvgValue": 50000,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["symbol"], "LIQ")
        self.assertIn("passed", payload)
        self.assertIn("unknown", payload)


if __name__ == "__main__":
    unittest.main()
