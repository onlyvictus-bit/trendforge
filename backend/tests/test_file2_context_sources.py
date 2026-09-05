from __future__ import annotations

import json
import io
from datetime import UTC, datetime

import pytest

from trendforge_api import phase3_multi_step_fetch
from trendforge_api import source_parser as source_parser_module
from trendforge_api.models import SourceSnapshotRecord
from trendforge_api.market_data_registry import CadenceClass, load_market_data_registry
from trendforge_api.market_data_scheduler import MarketDataScheduler
from trendforge_api.market_data_service import MarketDataService
from trendforge_api.market_data_store import MarketDataStore
from trendforge_api.parsers.file2_context_parser import (
    parse_amfi_monthly_aum,
    parse_google_trends_india_rss,
    parse_tradingeconomics_bdi,
    parse_westmetall_lme,
    parse_yahoo_bdry_proxy,
)
from trendforge_api.parsers.finish_30_parsers import parse_amfi_portfolio_directory
from trendforge_api.phase3_multi_step_fetch import MultiStepFetchResult
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_parser import (
    PARSER_MAP,
    STRUCTURED_PARSERS,
    parse_source_content,
)
from trendforge_api.source_resolver import resolve_and_fetch_source


def test_amfi_monthly_aum_parses_official_category_rows() -> None:
    import pandas as pd

    frame = pd.DataFrame(
        [
            ["Data for the month of July 2026", None, None, None],
            [None, None, None, None],
            [
                "Scheme Name",
                "No. of Schemes",
                "No. of Folios",
                "Net Assets Under Management as on 31 July 2026",
            ],
            ["Equity Scheme", 401, 123456, 321000.5],
        ]
    )
    workbook = io.BytesIO()
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, header=False, sheet_name="Table 3")

    parsed = parse_amfi_monthly_aum(workbook.getvalue())

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-31"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["schemeCategory"] == "Equity Scheme"
    assert row["numberOfSchemes"] == 401
    assert row["closingAumCr"] == 321000.5
    assert parsed["output"]["canProveLiveFundBuying"] is False


def test_westmetall_lme_is_third_party_delayed_context() -> None:
    content = json.dumps(
        {
            "source": "westmetall_lme",
            "pages": [
                {
                    "metal": "copper",
                    "html": """
                    <table><tr><th>Date</th><th>Cash Settlement</th><th>3-month</th><th>Stock</th></tr>
                    <tr><td>10. August 2026</td><td>9,850.00</td><td>9,900.00</td><td>145,200</td></tr></table>
                    """,
                }
            ],
        }
    ).encode()

    parsed = parse_westmetall_lme(content)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["metal"] == "COPPER"
    assert row["warehouseStockTonnes"] == 145200.0
    assert row["sourceTrust"] == "THIRD_PARTY_MIRROR"
    assert row["officialLmeArtifact"] is False


def test_amfi_portfolio_directory_keeps_only_actual_monthly_disclosure_urls() -> None:
    content = b'''<script>self.__next_f.push([1,"{\\"mf_id\\":\\"41\\",\\"mf_name\\":\\"Quantum Mutual Fund\\",\\"amc_name\\":\\"Quantum Asset Management\\",\\"amc_website\\":\\"https://quantum.example\\",\\"amc_monthly_portfolio_disclosure\\":\\"https://quantum.example/portfolio-july.xlsx\\"}"])</script>
    <a href="https://www.linkedin.com/company/amfi">LinkedIn</a>'''

    parsed = parse_amfi_portfolio_directory(content)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["mfId"] == 41
    assert row["mfName"] == "Quantum Mutual Fund"
    assert row["monthlyPortfolioDisclosureUrl"].endswith("portfolio-july.xlsx")
    assert row["isHoldingsData"] is False
    assert "symbol" not in row


def test_tradingeconomics_bdi_parses_one_dated_context_record() -> None:
    content = b"""
    <html><body><div>2026-08-10</div><table>
      <tr><th>Commodity</th><th>Price</th><th>Daily</th><th>Month</th><th>Year</th><th>Date</th></tr>
      <tr><td>Baltic Dry</td><td>3,083</td><td>-0.19%</td><td>4.16%</td><td>51.28%</td><td>Aug/10</td></tr>
    </table></body></html>
    """

    parsed = parse_tradingeconomics_bdi(content)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["series"] == "BALTIC_DRY_INDEX"
    assert row["value"] == 3083.0
    assert row["dailyChangePct"] == -0.19
    assert row["sourceTrust"] == "THIRD_PARTY_APPROVED"
    assert parsed["output"]["canProveStockDirection"] is False


def test_tradingeconomics_bdi_exposes_absolute_change_and_previous_value() -> None:
    content = b"""
    <html><body><div>2026-08-10</div><table>
      <tr><td>Baltic Dry</td><td>3,083.00</td><td></td><td>-6.00</td><td>-0.19%</td><td>4.16%</td><td>51.28%</td><td>Aug/10</td></tr>
    </table></body></html>
    """

    parsed = parse_tradingeconomics_bdi(content)

    row = parsed["output"]["rows"][0]
    assert row["value"] == 3083.0
    assert row["dailyChange"] == -6.0
    assert row["previousValue"] == 3089.0
    assert row["dailyChangePct"] == -0.19


def test_tradingeconomics_bdi_rejects_shell_or_missing_row() -> None:
    parsed = parse_tradingeconomics_bdi(
        b"<html><body><div>2026-08-10</div><table><tr><td>Shell</td></tr></table></body></html>"
    )

    assert parsed["parser_state"] == "WAIT_EMPTY_PARSE"
    assert parsed["record_count"] == 0


def test_yahoo_bdry_is_explicit_proxy_and_never_official_bdi() -> None:
    payload = {
        "records": [
            {
                "symbol": "BDRY",
                "timestamp": 1786368600,
                "open": 13.8,
                "high": 13.9,
                "low": 13.7,
                "close": 13.87,
                "volume": 3083,
            }
        ]
    }

    parsed = parse_yahoo_bdry_proxy(json.dumps(payload).encode())

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["symbol"] == "BDRY"
    assert row["proxyMetric"] == "DRY_BULK_SHIPPING_ETF_SENTIMENT"
    assert row["officialBalticDryIndex"] is False
    assert parsed["output"]["officialBalticDryIndex"] is False


def test_yahoo_bdry_rejects_other_symbols_and_empty_history() -> None:
    wrong_symbol = json.dumps(
        {
            "records": [
                {
                    "symbol": "BADI",
                    "timestamp": 1786368600,
                    "close": 1.0,
                    "volume": 1,
                }
            ]
        }
    ).encode()

    parsed = parse_yahoo_bdry_proxy(wrong_symbol)

    assert parsed["parser_state"] == "WAIT_EMPTY_PARSE"
    assert parsed["record_count"] == 0


def test_google_trends_india_rss_parses_current_topics_not_keyword_history() -> None:
    content = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0">
      <channel><item>
        <title>sample topic</title>
        <link>https://trends.google.com/trending/rss?geo=IN</link>
        <pubDate>Mon, 10 Aug 2026 15:10:00 +0000</pubDate>
        <ht:approx_traffic>20K+</ht:approx_traffic>
      </item></channel>
    </rss>"""

    parsed = parse_google_trends_india_rss(content)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["title"] == "sample topic"
    assert row["approxTrafficLowerBound"] == 20_000
    assert row["geo"] == "IN"
    assert parsed["output"]["isKeywordInterestHistory"] is False


def test_google_trends_invalid_or_empty_rss_fails_closed() -> None:
    invalid = parse_google_trends_india_rss(b"<html>rate limited</html>")
    empty = parse_google_trends_india_rss(b"<rss><channel /></rss>")

    assert invalid["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert invalid["record_count"] == 0
    assert empty["parser_state"] == "WAIT_EMPTY_PARSE"
    assert empty["record_count"] == 0


@pytest.mark.parametrize(
    ("source_key", "expected_trust"),
    [
        ("tradingeconomics_bdi", "OPEN_SOURCE_UNOFFICIAL"),
        ("yahoo_bdry_shipping_proxy", "OPEN_SOURCE_UNOFFICIAL"),
        ("google_trends_india_rss", "OFFICIAL"),
    ],
)
def test_file2_sources_are_catalogued_and_structured_only(
    source_key: str, expected_trust: str
) -> None:
    descriptor = get_source_descriptor(source_key)

    assert descriptor is not None
    assert descriptor.authority.value == expected_trust
    assert source_key in STRUCTURED_PARSERS
    assert source_key in PARSER_MAP
    assert (
        "score" in descriptor.limitation.casefold()
        or "voter" in descriptor.limitation.casefold()
    )


def test_source_parser_routes_google_rss_through_integrity_and_schema() -> None:
    content = b"""<?xml version="1.0"?><rss version="2.0"><channel><item>
    <title>topic</title><link>https://trends.google.com/trending/rss?geo=IN</link>
    <pubDate>Mon, 10 Aug 2026 15:10:00 +0000</pubDate>
    </item></channel></rss>"""

    parsed = parse_source_content(
        "google_trends_india_rss",
        content,
        url="https://trends.google.com/trending/rss?geo=IN",
    )

    assert parsed.parser_state == "PARSED_STRUCTURED"
    assert parsed.data_date == "2026-08-10"
    assert parsed.record_count == 1


def test_resolver_uses_existing_multistep_fetchers_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []

    def result(url: str, body: bytes, media_type: str) -> MultiStepFetchResult:
        return MultiStepFetchResult(True, url, 200, body, media_type, None)

    def fake_te() -> MultiStepFetchResult:
        calls.append(("te", None))
        return result(
            "https://tradingeconomics.com/commodity/baltic",
            b"<html><table><tr><td>Baltic Dry</td><td>3083</td><td>-0.19%</td><td>4.16%</td><td>51.28%</td><td>Aug/10</td></tr></table></html>",
            "text/html",
        )

    def fake_google() -> MultiStepFetchResult:
        calls.append(("google", None))
        return result(
            "https://trends.google.com/trending/rss?geo=IN",
            b"<rss><channel><item><title>topic</title></item></channel></rss>",
            "application/rss+xml",
        )

    def fake_yahoo(symbols: list[str], *, range_: str = "1mo") -> MultiStepFetchResult:
        calls.append(("yahoo", (symbols, range_)))
        return result(
            "https://query1.finance.yahoo.com/v8/finance/chart/BDRY?range=1y&interval=1d",
            b'{"records":[{"symbol":"BDRY","timestamp":1786368600,"close":13.87,"volume":3083}]}',
            "application/json",
        )

    monkeypatch.setattr(phase3_multi_step_fetch, "fetch_tradingeconomics_bdi", fake_te)
    monkeypatch.setattr(
        phase3_multi_step_fetch, "fetch_google_trends_india_rss", fake_google
    )
    monkeypatch.setattr(phase3_multi_step_fetch, "fetch_yahoo_symbols", fake_yahoo)

    resolved = {
        key: resolve_and_fetch_source(key, get_source_descriptor(key).url)  # type: ignore[union-attr]
        for key in (
            "tradingeconomics_bdi",
            "yahoo_bdry_shipping_proxy",
            "google_trends_india_rss",
        )
    }

    assert (
        resolved["tradingeconomics_bdi"].resolver_state == "TRADINGECONOMICS_BDI_HTML"
    )
    assert (
        resolved["google_trends_india_rss"].resolver_state == "GOOGLE_TRENDS_INDIA_RSS"
    )
    assert (
        resolved["yahoo_bdry_shipping_proxy"].resolver_state
        == "YAHOO_BDRY_SHIPPING_ETF_PROXY"
    )
    assert ("yahoo", (["BDRY"], "1y")) in calls
    assert all(item.status_code == 200 and item.content for item in resolved.values())


def test_amfi_aum_and_lme_use_existing_multistep_fetchers_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_amfi() -> MultiStepFetchResult:
        calls.append("amfi")
        return MultiStepFetchResult(
            True,
            "https://portal.amfiindia.com/spages/amjul2026repo.xls",
            200,
            b"amfi-workbook",
            "application/vnd.ms-excel",
            None,
        )

    def fake_lme() -> MultiStepFetchResult:
        calls.append("lme")
        return MultiStepFetchResult(
            True,
            "https://www.westmetall.com/en/markdaten.php?action=table&field={metal}",
            200,
            b'{"source":"westmetall_lme","pages":[]}',
            "application/json",
            None,
        )

    monkeypatch.setattr(phase3_multi_step_fetch, "fetch_amfi_monthly_aum", fake_amfi)
    monkeypatch.setattr(phase3_multi_step_fetch, "fetch_westmetall_lme", fake_lme)

    amfi_descriptor = get_source_descriptor("amfi_monthly_aum")
    lme_descriptor = get_source_descriptor("lme_warehouse_stocks")
    assert amfi_descriptor is not None
    assert lme_descriptor is not None

    amfi = resolve_and_fetch_source("amfi_monthly_aum", amfi_descriptor.url)
    lme = resolve_and_fetch_source("lme_warehouse_stocks", lme_descriptor.url)

    assert amfi.resolver_state == "AMFI_MONTHLY_AUM_WORKBOOK"
    assert lme.resolver_state == "WESTMETALL_LME_SHARED_SESSION_FALLBACK"
    assert amfi.content == b"amfi-workbook"
    assert lme.content.startswith(b'{"source":"westmetall_lme"')
    assert calls == ["amfi", "lme"]


@pytest.mark.parametrize(
    ("source_key", "content", "expected_count"),
    [
        (
            "tradingeconomics_bdi",
            b"<html><div>2026-08-10</div><table><tr><td>Baltic Dry</td><td>3083</td><td>-0.19%</td><td>4.16%</td><td>51.28%</td><td>Aug/10</td></tr></table></html>",
            1,
        ),
        (
            "yahoo_bdry_shipping_proxy",
            b'{"records":[{"symbol":"BDRY","timestamp":1786368600,"close":13.87,"volume":3083}]}',
            1,
        ),
        (
            "google_trends_india_rss",
            b"<rss><channel><item><title>topic</title><pubDate>Mon, 10 Aug 2026 15:10:00 +0000</pubDate></item></channel></rss>",
            1,
        ),
    ],
)
def test_failed_refresh_retains_last_populated_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    source_key: str,
    content: bytes,
    expected_count: int,
) -> None:
    descriptor = get_source_descriptor(source_key)
    assert descriptor is not None
    broken = SourceSnapshotRecord(
        id=2,
        sourceKey=source_key,
        name=descriptor.name,
        url=descriptor.url,
        checkState="BROKEN",
        error="simulated fetch failure",
        checkedAt="2026-08-10T15:30:00+00:00",
        changed=False,
    )
    populated = SourceSnapshotRecord(
        id=1,
        sourceKey=source_key,
        name=descriptor.name,
        url=descriptor.url,
        checkState="NEW",
        statusCode=200,
        contentHash="abc",
        contentLength=len(content),
        rawPath="ignored.bin",
        checkedAt="2026-08-10T15:00:00+00:00",
        changed=True,
    )
    monkeypatch.setattr(
        source_parser_module, "get_latest_source_snapshot", lambda _key: broken
    )
    monkeypatch.setattr(
        source_parser_module,
        "get_latest_populated_source_snapshot",
        lambda _key: populated,
    )
    monkeypatch.setattr(
        source_parser_module, "read_snapshot_bytes", lambda _path: content
    )

    parsed = source_parser_module.structured_parse(source_key)

    assert parsed.parser_state == "PARSED_STRUCTURED"
    assert parsed.record_count == expected_count
    assert parsed.snapshot_id == 1
    assert parsed.output["latestFetchState"] == "BROKEN"
    assert parsed.output["retainedSnapshotAfterFetchFailure"] is True


def test_registry_scheduler_discovers_all_three_contracts(tmp_path) -> None:
    registry = load_market_data_registry()
    store = MarketDataStore(
        root=tmp_path / "objects",
        db_path=tmp_path / "scheduler.sqlite3",
    )
    scheduler = MarketDataScheduler(
        registry=registry,
        store=store,
        service=MarketDataService(store=store),
        enabled=False,
    )

    assert len(registry.contracts) == 126
    assert (
        registry.by_key["tradingeconomics_bdi"].cadence_class is CadenceClass.DAILY_EOD
    )
    assert (
        registry.by_key["yahoo_bdry_shipping_proxy"].cadence_class
        is CadenceClass.DAILY_EOD
    )
    assert (
        registry.by_key["google_trends_india_rss"].cadence_class
        is CadenceClass.INTRADAY
    )
    due = {
        item.source_key: item
        for item in scheduler.due_decisions(
            slot="0917",
            at=datetime(2026, 8, 10, 3, 47, tzinfo=UTC),
            calendar={"isTradingDay": True},
        )
    }
    assert due["google_trends_india_rss"].due is True
    assert due["tradingeconomics_bdi"].due is False
    assert due["yahoo_bdry_shipping_proxy"].due is False
