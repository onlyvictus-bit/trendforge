from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from . import storage
from .demo_data import generate_demo_daily_candles
from .models import SourceParseResult
from .scanner_scheduler import ScannerScheduler


def benchmark_cached_nifty50(symbols: list[str]) -> dict[str, Any]:
    clean = list(
        dict.fromkeys(symbol.strip().upper() for symbol in symbols if symbol.strip())
    )
    if len(clean) != 50:
        raise ValueError(
            f"Exactly 50 unique Nifty 50 symbols are required; received {len(clean)}."
        )
    live_db = storage.DB_PATH
    report_path = live_db.parent / "benchmarks" / "nifty50_cached_latest.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="trendforge_nifty50_benchmark_"
    ) as temp_dir:
        storage.DB_PATH = Path(temp_dir) / "benchmark.db"
        try:
            seed_started = perf_counter()
            storage.init_db()
            membership = SourceParseResult(
                id=1,
                sourceKey="nse_nifty50_constituents",
                snapshotId=None,
                parserState="PARSED_STRUCTURED",
                dataDate=datetime.now(timezone.utc).date().isoformat(),
                recordCount=50,
                summary="Deterministic benchmark membership copied from official current universe.",
                output={
                    "rows": [
                        {
                            "symbol": symbol,
                            "company": f"{symbol} benchmark fixture",
                            "industry": "Benchmark Fixture",
                            "series": "EQ",
                            "isin": f"BENCH{index:07d}",
                            "indexMembership": "NIFTY50",
                            "active": True,
                        }
                        for index, symbol in enumerate(clean)
                    ]
                },
                parsedAt=datetime.now(timezone.utc).isoformat(),
            )
            storage.save_structured_source_rows(membership)
            candles = [
                candle
                for symbol in clean
                for candle in generate_demo_daily_candles(symbol=symbol, sessions=220)
            ]
            stored = storage.save_ohlcv_candles(candles)
            seed_seconds = perf_counter() - seed_started

            scan_started = perf_counter()
            scan = ScannerScheduler().run_once(
                universe="NIFTY50_SMOKE",
                fetch=False,
                trigger="cached_nifty50_benchmark",
            )
            scan_seconds = perf_counter() - scan_started
            processed = int(scan.get("processedSeries", 0))
            passed = (
                scan.get("status") == "COMPLETE"
                and processed == 50
                and scan_seconds < 30
            )
            report = {
                "status": "PASS" if passed else "FAIL",
                "measuredAt": datetime.now(timezone.utc).isoformat(),
                "universe": "NIFTY50",
                "symbolCount": len(clean),
                "candlesStored": stored,
                "seedSeconds": round(seed_seconds, 4),
                "scanSeconds": round(scan_seconds, 4),
                "targetSeconds": 30,
                "processedSeries": processed,
                "candidateCount": scan.get("candidateCount", 0),
                "scannerStatus": scan.get("status"),
                "sourceMode": "SYNTHETIC_TEST_CACHED_OFFLINE",
                "executable": False,
                "note": "Measures the full cached scanner path over exactly 50 official-current symbols with deterministic candles; network/bootstrap time is excluded.",
            }
            report_path.write_text(
                json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
            )
            return report
        finally:
            storage.DB_PATH = live_db
