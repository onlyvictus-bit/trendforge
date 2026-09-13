from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from trendforge_api import storage
from trendforge_api.market_data_registry import load_market_data_registry
from trendforge_api.market_data_service import (
    MarketDataService,
    ParameterContext,
    ParsedSourcePayload,
    RawAcquisition,
)
from trendforge_api.market_data_store import ManifestStatus, MarketDataStore
from trendforge_api.selection.cash_a1_staging import (
    persist_cash_staging,
    stage_cash_last_good,
)
from trendforge_api.selection.cash_a2_identity import (
    build_cash_identity_batch,
    persist_cash_identity,
)
from trendforge_api.selection.cash_a4_history import (
    build_cash_history_batch,
    list_raw_bars,
    persist_cash_history,
)
from trendforge_api.selection.cash_post_commit import (
    CashPipelineRunContext,
    run_existing_cash_pipeline,
)
from trendforge_api.selection.inventory_source_bundle import latest_inventory_source_bundle
from trendforge_api.selection.r16_store import apply_r16_schema
from trendforge_api.selection.r5_live import latest_r5_structure_batch

TRADE_DATE = date(2026, 8, 14)
SYMBOLS = ("RELIANCE", "TCS", "INFY", "HDFCBANK")
ISINS = {
    "RELIANCE": "INE002A01018",
    "TCS": "INE467B01029",
    "INFY": "INE009A01021",
    "HDFCBANK": "INE040A01034",
}


def _at_close(day: date) -> datetime:
    # 16:30 IST, safely after the NSE cash close.
    return datetime(day.year, day.month, day.day, 11, 0, tzinfo=UTC)


def _trading_days(through: date, count: int) -> tuple[date, ...]:
    days: list[date] = []
    cursor = through
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return tuple(reversed(days))


def _records(day: date) -> list[dict[str, Any]]:
    # Cross-sectional differences make RELIANCE a deterministic bullish WATCH
    # candidate while every session remains a valid immutable history input.
    specs = {
        "RELIANCE": (100.0, 112.0, 114.0, 99.0, 4_000_000.0),
        "TCS": (100.0, 102.0, 103.0, 99.0, 2_000_000.0),
        "INFY": (100.0, 100.0, 101.0, 99.0, 1_000_000.0),
        "HDFCBANK": (100.0, 98.0, 101.0, 97.0, 500_000.0),
    }
    rows: list[dict[str, Any]] = []
    for symbol in SYMBOLS:
        previous, close, high, low, volume = specs[symbol]
        rows.append(
            {
                "tradeDate": day.isoformat(),
                "symbol": symbol,
                "series": "EQ",
                "isin": ISINS[symbol],
                "open": previous,
                "high": high,
                "low": low,
                "close": close,
                "previousClose": previous,
                "volume": volume,
                "tradedValue": close * volume,
            }
        )
    return rows


class _CashSourceTransport:
    def __init__(self) -> None:
        self.raw_by_date: dict[date, bytes] = {}

    async def fetch_resolver(
        self, source_key: str, catalog_url: str, trading_date: date | None = None
    ) -> RawAcquisition:
        assert source_key == "nse_bhavcopy_eod"
        assert trading_date is not None
        body = json.dumps(
            {"records": _records(trading_date)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        self.raw_by_date[trading_date] = body
        return RawAcquisition.success(
            source_url=catalog_url,
            status_code=200,
            media_type="application/json",
            content=body,
            payload=json.loads(body),
            fetched_at=_at_close(trading_date),
        )

    async def fetch_endpoint(
        self, endpoint_key: str, parameters: dict[str, str]
    ) -> RawAcquisition:
        raise AssertionError(
            f"cash fixture must use the resolver path, got {endpoint_key} {parameters}"
        )


def _cash_normalizer(
    _contract, acquisitions: tuple[RawAcquisition, ...], context: ParameterContext
) -> ParsedSourcePayload:
    assert len(acquisitions) == 1
    payload = json.loads(acquisitions[0].content)
    records = tuple(payload["records"])
    return ParsedSourcePayload(
        parser_state="PARSED_STRUCTURED",
        records=records,
        data_date=context.trading_date,
        payload={"fixture": "03E_SOURCE_TO_END"},
        source_row_count=len(records),
    )


def _context(day: date) -> ParameterContext:
    return ParameterContext(
        trading_date=day,
        market_session="CLOSED",
        symbols=SYMBOLS,
        now=_at_close(day),
    )


def test_source_to_s8_retains_exact_r5_history_before_r16(tmp_path: Path, monkeypatch) -> None:
    """Prove the real source/R1/R5 evidence set is the one protected by S8."""

    store = MarketDataStore(
        root=tmp_path / "market-data",
        db_path=tmp_path / "trendforge.db",
    )
    monkeypatch.setattr(storage, "DB_PATH", store.db_path)
    storage._INITIALIZED_DB_PATHS.clear()

    transport = _CashSourceTransport()
    service = MarketDataService(
        transport=transport,
        normalizer=_cash_normalizer,
        store=store,
    )
    contract = load_market_data_registry().by_key["nse_bhavcopy_eod"]

    final_result = None
    for day in _trading_days(TRADE_DATE, 22):
        result = asyncio.run(
            service.run_source(
                contract,
                context=_context(day),
                run_id=f"source-{day.isoformat()}",
                slot="eod",
            )
        )
        assert result.status is ManifestStatus.SUCCESS_NEW
        assert result.raw_content_hashes == (
            hashlib.sha256(transport.raw_by_date[day]).hexdigest(),
        )

        # Use the same canonical A1 -> A2 -> A4 owners as the production pipeline
        # to accumulate immutable history; no direct SQL fixture inserts.
        staging = persist_cash_staging(stage_cash_last_good(store))
        identity = persist_cash_identity(build_cash_identity_batch(staging, store=store))
        history = persist_cash_history(
            build_cash_history_batch(identity, decision_at=_at_close(day))
        )
        assert history.raw_bar_count == len(SYMBOLS)
        final_result = result

    assert final_result is not None
    status = apply_r16_schema()
    assert status["applied"] is True
    assert status["retentionReady"] is True

    execution = run_existing_cash_pipeline(
        CashPipelineRunContext(
            store=store,
            collector_run_id="source-to-end-final",
            trading_date=TRADE_DATE,
            results={"nse_bhavcopy_eod": final_result},
            trigger_source_keys=("nse_bhavcopy_eod",),
            fingerprint="e" * 64,
            observed_at=_at_close(TRADE_DATE),
        )
    )
    states = {stage.stage_id: stage for stage in execution.stages}
    assert states["R5"].state == "COMPLETED"
    assert states["S8"].state == "COMPLETED"
    assert execution.s8_run_id is not None

    r1 = latest_inventory_source_bundle()
    assert r1 is not None
    cash_source = next(
        row for row in r1.source_records if row.source_key == "nse_bhavcopy_eod"
    )
    assert cash_source.raw_content_hash == hashlib.sha256(
        transport.raw_by_date[TRADE_DATE]
    ).hexdigest()

    r5 = latest_r5_structure_batch()
    assert r5 is not None
    reliance = next(row for row in r5.rows if row.symbol == "RELIANCE")
    assert reliance.history_count >= 21
    assert reliance.facts, "fixture must exercise real R5 closed-bar analysis"
    used_bar_ids = {
        str(bar_id)
        for fact in reliance.facts
        for bar_id in fact.payload.get("bar_ids", ())
    }
    assert len(used_bar_ids) >= 21
    used_hashes = {
        bar.artifact_hash
        for bar in list_raw_bars("RELIANCE", through=TRADE_DATE)
        if bar.bar_id in used_bar_ids
    }
    assert len(used_hashes) >= 21

    # Read the immutable S8 publication itself. 03E must not accept an S8/R16
    # chain whose R5 historical inputs were never protected by that S8 decision.
    conn = storage.connect()
    try:
        publication = conn.execute(
            "SELECT lineage_json, status FROM historical_retention_publications "
            "WHERE artifact_type='S8_DECISION_VERSION' AND artifact_id=?",
            (execution.s8_run_id,),
        ).fetchone()
    finally:
        conn.close()
    assert publication is not None
    assert publication["status"] == "PUBLISHED"
    lineage = json.loads(publication["lineage_json"])
    retained_hashes = {
        str(root["contentHash"])
        for root in lineage["evidenceRoots"]
        if root.get("contentHash")
    }
    assert used_hashes <= retained_hashes, (
        "S8 retention omitted immutable A4/R5 bar artifacts used by the decision; "
        f"missing={sorted(used_hashes - retained_hashes)}"
    )

    assert states["R16"].state == "COMPLETED"
