from __future__ import annotations

import io
import zipfile
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.market_context_ingestion import (
    ContextDataUnavailable,
    build_official_market_context,
    build_official_sector_contexts,
)
from trendforge_api.models import SourceParseResult
from trendforge_api.nse_eod_ingestion import _persist_fetched_artifact
from trendforge_api.parsers.nse_cash_bhavcopy_parser import parse_nse_cash_bhavcopy
from trendforge_api.parsers.nse_index_close_parser import parse_nse_index_close
from trendforge_api.main import app


def zipped_csv(name: str, text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


def test_cash_bhavcopy_parser_normalizes_breadth_and_flow_fields() -> None:
    content = zipped_csv(
        "BhavCopy_NSE_CM_0_0_0_20260710_F_0000.csv",
        "TradDt,Sgmt,FinInstrmTp,ISIN,TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,PrvsClsgPric,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd\n"
        "2026-07-10,CM,STK,INE001,A,EQ,100,112,99,110,100,1000,110000,50\n"
        "2026-07-10,CM,STK,INE002,B,EQ,100,101,89,90,100,2000,180000,70\n"
        "2026-07-10,CM,STK,INE003,C,EQ,100,101,99,100,100,500,50000,20\n"
        "2026-07-10,CM,STK,INE004,ETF,EQ,0,0,0,0,0,0,0,0\n",
    )
    result = parse_nse_cash_bhavcopy(content)
    assert result["parser_state"] == "PARSED_STRUCTURED"
    assert result["data_date"] == "2026-07-10"
    assert [row["advanceState"] for row in result["output"]["rows"]] == [
        "ADVANCE",
        "DECLINE",
        "UNCHANGED",
    ]
    assert result["output"]["rows"][0]["tradedValue"] == 110000


def test_index_close_parser_keeps_nifty_vix_and_sector_history() -> None:
    content = (
        "Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.)\n"
        "Nifty 50,10-07-2026,24000,24250,23950,24206.9,244.1,1.02,313072212,24577.43\n"
        "India VIX,10-07-2026,13.5,14,13,13.8,-0.2,-1.43,0,0\n"
        "Nifty IT,10-07-2026,35000,35500,34900,35400,400,1.14,100,200\n"
    ).encode()
    result = parse_nse_index_close(content)
    assert result["parser_state"] == "PARSED_STRUCTURED"
    assert result["data_date"] == "2026-07-10"
    assert result["record_count"] == 3
    assert result["output"]["rows"][1]["indexName"] == "INDIA VIX"


def test_fetched_official_artifact_is_archived_parsed_and_normalized(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "archive.db")
    content = (
        "Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.)\n"
        "Nifty 50,10-07-2026,24000,24250,23950,24206.9,244.1,1.02,313072212,24577.43\n"
        "India VIX,10-07-2026,13.5,14,13,13.8,-0.2,-1.43,0,0\n"
    ).encode()
    saved = _persist_fetched_artifact(
        {
            "state": "FETCHED",
            "sourceKey": "nse_index_close_eod",
            "date": date(2026, 7, 10),
            "url": "https://nsearchives.nseindia.com/content/indices/ind_close_all_10072026.csv",
            "status": 200,
            "headers": {"content-type": "text/csv"},
            "content": content,
        }
    )
    assert saved["parserState"] == "PARSED_STRUCTURED"
    assert len(storage.list_nse_index_eod(index_name="NIFTY 50")) == 1
    archives = storage.list_raw_source_archive(source_key="nse_index_close_eod")
    assert len(archives) == 1
    assert archives[0]["parser_state_after_parse"] == "PARSED_STRUCTURED"


def save_result(source_key: str, data_date: str, rows: list[dict]) -> None:
    result = SourceParseResult(
        id=1,
        sourceKey=source_key,
        snapshotId=1,
        parserState="PARSED_STRUCTURED",
        dataDate=data_date,
        recordCount=len(rows),
        summary="fixture",
        output={"rows": rows},
        parsedAt=datetime.now(timezone.utc).isoformat(),
    )
    storage.save_structured_source_rows(result)


def save_calendar_coverage(year: int) -> None:
    result = SourceParseResult(
        id=2,
        sourceKey="nse_trading_calendar",
        snapshotId=2,
        parserState="PARSED_STRUCTURED",
        dataDate=f"{year}-01-01",
        recordCount=1,
        summary="fixture coverage",
        output={
            "rows": [],
            "coverage": [
                {
                    "exchange": "NSE",
                    "segment": "CM",
                    "year": year,
                    "validFrom": f"{year}-01-01",
                    "validTo": f"{year}-12-31",
                }
            ],
        },
        parsedAt=datetime.now(timezone.utc).isoformat(),
    )
    storage.save_structured_source_rows(result)


def test_official_market_context_builds_from_point_in_time_stored_rows(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "market-context.db")
    save_calendar_coverage(2026)
    start = date(2025, 9, 1)
    index_rows = []
    for offset in range(220):
        day = start + timedelta(days=offset)
        close = 20_000 + offset * 10
        index_rows.extend(
            [
                {
                    "indexName": "NIFTY 50",
                    "indexDate": day.isoformat(),
                    "open": close - 10,
                    "high": close + 20,
                    "low": close - 20,
                    "close": close,
                    "pointsChange": 10,
                    "changePercent": 0.05,
                    "volume": 1_000_000,
                    "turnoverCrore": 1000,
                },
                {
                    "indexName": "INDIA VIX",
                    "indexDate": day.isoformat(),
                    "open": 13,
                    "high": 14,
                    "low": 12,
                    "close": 13,
                    "pointsChange": 0,
                    "changePercent": 0,
                    "volume": 0,
                    "turnoverCrore": 0,
                },
            ]
        )
    latest = index_rows[-2]["indexDate"]
    save_result("nse_index_close_eod", latest, index_rows)
    save_result(
        "nse_bhavcopy_eod",
        latest,
        [
            {
                "tradeDate": latest,
                "symbol": "A",
                "series": "EQ",
                "close": 110,
                "previousClose": 100,
                "advanceState": "ADVANCE",
            },
            {
                "tradeDate": latest,
                "symbol": "B",
                "series": "EQ",
                "close": 105,
                "previousClose": 100,
                "advanceState": "ADVANCE",
            },
            {
                "tradeDate": latest,
                "symbol": "C",
                "series": "EQ",
                "close": 90,
                "previousClose": 100,
                "advanceState": "DECLINE",
            },
        ],
    )
    as_of = datetime.fromisoformat(f"{latest}T18:30:00+05:30")
    result = build_official_market_context(as_of=as_of)
    assert result.state == "TRADEABLE_BULLISH"
    assert result.breadth_ratio == 2
    assert result.trust_level.value == "OFFICIAL_FREE_EOD"
    assert storage.latest_market_context_snapshot()["state"] == result.state
    client = TestClient(app)
    status = client.get("/api/context/official/status")
    rebuild = client.post("/api/context/official/rebuild")
    assert status.status_code == 200
    assert status.json()["marketContextReady"] is True
    assert (
        rebuild.status_code == 409
    )  # Sector history is intentionally absent in this fixture.


def test_market_context_fails_closed_without_200_nifty_rows(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "missing-context.db")
    with pytest.raises(ContextDataUnavailable, match="200"):
        build_official_market_context()


def test_sector_context_uses_date_aligned_official_index_history(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sector-context.db")
    save_calendar_coverage(2026)
    start = date(2026, 1, 1)
    rows = []
    for offset in range(65):
        day = (start + timedelta(days=offset)).isoformat()
        rows.extend(
            [
                {"indexName": "NIFTY 50", "indexDate": day, "close": 20_000 + offset},
                {
                    "indexName": "NIFTY IT",
                    "indexDate": day,
                    "close": 30_000 + offset * 20,
                },
            ]
        )
    latest = rows[-1]["indexDate"]
    save_result("nse_index_close_eod", latest, rows)
    results = build_official_sector_contexts(
        as_of=datetime.fromisoformat(f"{latest}T18:30:00+05:30")
    )
    it = next(item for item in results if item.sector == "Information Technology")
    assert it.rrg_state in {"LEADING", "IMPROVING"}
    assert (
        storage.latest_sector_context_snapshot(sector="Information Technology")
        is not None
    )
