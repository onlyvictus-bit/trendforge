from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from trendforge_api import storage
from trendforge_api.gate_readiness import GATE_DEPENDENCIES
from trendforge_api.parsers.sge_daily_parser import parse_sge_daily_report
from trendforge_api.parsers.wgc_gold_parser import (
    parse_wgc_gold_etf_series,
    parse_wgc_gold_open_interest,
)
from trendforge_api.source_resolver import direct_download_candidates
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_parser import parse_source_content


WGC_OPEN_INTEREST = json.dumps(
    {
        "system": {"request_time": "2026-07-13 14:54:39"},
        "chartData": {
            "asOfDate": "2026-07-10",
            "periodicity": "WEEKLY",
            "series": [
                {
                    "name": "Comex",
                    "data": [["2026-07-03", 180.2], ["2026-07-10", 184.5]],
                },
                {
                    "name": "Shanghai Futures Exchange",
                    "data": [["2026-07-03", 12.1], ["2026-07-10", 12.8]],
                },
            ],
        },
    }
).encode()


WGC_ETF_HOLDINGS = json.dumps(
    {
        "system": {"request_time": "2026-07-13 11:17:47"},
        "chartData": {
            "asOfDate": "2026-07-10",
            "data": {
                "Weekly": {
                    "tonnes": {
                        "columns": [
                            "Date",
                            "North America",
                            "Europe",
                            "Asia",
                            "Other",
                            "Gold, US$/oz",
                        ],
                        "set": [
                            [1783036800000, 20.0, 15.0, 8.0, 2.0, 4300.0],
                            [1783641600000, 21.0, 16.0, 9.0, 2.0, 4310.0],
                        ],
                    }
                }
            },
        },
    }
).encode()


WGC_ETF_FLOWS = json.dumps(
    {
        "system": {"request_time": "2026-07-13 11:17:45"},
        "chartData": {
            "asOfDate": "2026-07-10",
            "data": {
                "Weekly": {
                    "series": {
                        "tonnes": [
                            {
                                "name": "North America",
                                "data": [
                                    [1783036800000, 1.25],
                                    [1783641600000, -0.75],
                                ],
                            },
                            {
                                "name": "Europe",
                                "data": [
                                    [1783036800000, 0.5],
                                    [1783641600000, 0.25],
                                ],
                            },
                            {
                                "name": "Gold Price (rhs)",
                                "data": [
                                    [1783036800000, 4300.0],
                                    [1783641600000, 4310.0],
                                ],
                            },
                        ]
                    }
                }
            },
        },
    }
).encode()


SGE_DAILY_REPORT = b"""
<html><body><table>
<tr><th>Date</th><th>Contract</th><th>Open</th><th>Highest</th><th>Lowest</th>
<th>Close</th><th>Up/Down</th><th>Up/Down (%)</th><th>Weighted Average Price</th>
<th>Volume (Kg)</th><th>Amount (yuan)</th><th>Open Interest (Lot)</th>
<th>Direction</th><th>Delivery Volume (Lot)</th></tr>
<tr><td>2026-07-10</td><td>Au(T+D)</td><td>888.50</td><td>898.30</td>
<td>881.00</td><td>897.46</td><td>-5.44</td><td>-0.60%</td><td>891.03</td>
<td>34142</td><td>30421575200</td><td>193266</td><td>Long to Short</td><td>3584</td></tr>
</table></body></html>
"""


def test_wgc_open_interest_parser_normalizes_venue_history() -> None:
    parsed = parse_wgc_gold_open_interest(WGC_OPEN_INTEREST)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-10"
    assert parsed["record_count"] == 4
    assert parsed["output"]["scope"] == "GOLD_FUTURES_OI_DELAYED_CONTEXT"
    assert parsed["output"]["rows"][-1] == {
        "venue": "Shanghai Futures Exchange",
        "observationDate": "2026-07-10",
        "openInterestUsdBn": 12.8,
        "frequency": "WEEKLY",
        "units": "USD_BILLION",
    }


def test_wgc_etf_parser_preserves_regional_holdings_and_derived_total() -> None:
    parsed = parse_wgc_gold_etf_series(
        WGC_ETF_HOLDINGS,
        url="https://fsapi.gold.org/api/v11/charts/etfv2/revised/holdings-chart2",
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-10"
    assert parsed["record_count"] == 10
    assert parsed["output"]["dataset"] == "HOLDINGS"
    latest_total = parsed["output"]["rows"][-1]
    assert latest_total == {
        "dataset": "HOLDINGS",
        "period": "WEEKLY",
        "observationDate": "2026-07-10",
        "region": "WORLD_TOTAL",
        "value": 48.0,
        "units": "TONNES",
        "goldPriceUsdOz": 4310.0,
        "isDerived": True,
    }


def test_wgc_etf_parser_normalizes_flow_series_and_separates_gold_price() -> None:
    parsed = parse_wgc_gold_etf_series(
        WGC_ETF_FLOWS,
        url="https://fsapi.gold.org/api/v11/charts/etfv2/revised/flows-chart2",
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 6
    assert parsed["output"]["dataset"] == "FLOWS"
    assert parsed["output"]["rows"][-1] == {
        "dataset": "FLOWS",
        "period": "WEEKLY",
        "observationDate": "2026-07-10",
        "region": "WORLD_TOTAL",
        "value": -0.5,
        "units": "TONNES",
        "goldPriceUsdOz": 4310.0,
        "isDerived": True,
    }


def test_gold_parsers_fail_closed_on_missing_schema_or_wrong_endpoint() -> None:
    missing_series = parse_wgc_gold_open_interest(b'{"chartData": {}}')
    ambiguous_etf = parse_wgc_gold_etf_series(WGC_ETF_HOLDINGS)
    malformed_sge = parse_sge_daily_report(
        b"<html><table><tr><td>bad</td></tr></table>"
    )

    assert missing_series["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert ambiguous_etf["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert malformed_sge["parser_state"] == "WAIT_SCHEMA_MISMATCH"


def test_sge_parser_normalizes_price_oi_direction_and_delivery() -> None:
    parsed = parse_sge_daily_report(SGE_DAILY_REPORT)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-10"
    assert parsed["record_count"] == 1
    assert parsed["output"]["scope"] == "CHINA_PHYSICAL_GOLD_DELAYED_CONTEXT"
    assert parsed["output"]["rows"][0] == {
        "tradeDate": "2026-07-10",
        "contract": "Au(T+D)",
        "open": 888.5,
        "high": 898.3,
        "low": 881.0,
        "close": 897.46,
        "change": -5.44,
        "changePercent": -0.6,
        "weightedAveragePrice": 891.03,
        "volumeKg": 34142.0,
        "amountCny": 30421575200.0,
        "openInterestLots": 193266,
        "direction": "Long to Short",
        "deliveryVolumeLots": 3584,
    }


def test_gold_context_direct_candidates_are_official_and_date_bounded() -> None:
    assert direct_download_candidates("world_gold_council_oi") == [
        "https://fsapi.gold.org/datawarehouseapi/api/total-open-interest"
    ]
    assert direct_download_candidates("wgc_gold_etf_holdings") == [
        "https://fsapi.gold.org/api/v11/charts/etfv2/revised/holdings-chart2"
    ]
    assert direct_download_candidates("wgc_gold_etf_flows") == [
        "https://fsapi.gold.org/api/v11/charts/etfv2/revised/flows-chart2"
    ]
    sge = direct_download_candidates("sge_daily_report", today=date(2026, 7, 13))
    assert sge[0].endswith("start_date=2026-07-13&end_date=2026-07-13")
    assert all("start_date=" in url and "end_date=" in url for url in sge)


def test_gold_context_rows_are_persisted_with_source_specific_lineage(
    tmp_path: Path,
) -> None:
    original_db_path = storage.DB_PATH
    storage.DB_PATH = tmp_path / "gold-context.db"
    try:
        wgc = storage.save_source_parse_result(
            parse_source_content(
                "world_gold_council_oi",
                WGC_OPEN_INTEREST,
                url="https://fsapi.gold.org/datawarehouseapi/api/total-open-interest",
            )
        )
        etf = storage.save_source_parse_result(
            parse_source_content(
                "wgc_gold_etf_holdings",
                WGC_ETF_HOLDINGS,
                url="https://fsapi.gold.org/api/v11/charts/etfv2/revised/holdings-chart2",
            )
        )
        sge = storage.save_source_parse_result(
            parse_source_content(
                "sge_daily_report",
                SGE_DAILY_REPORT,
                url=(
                    "https://en.sge.com.cn/h5_data_DailyReport?"
                    "start_date=2026-07-10&end_date=2026-07-10"
                ),
            )
        )
        reduced_payload = json.loads(WGC_ETF_HOLDINGS)
        for point in reduced_payload["chartData"]["data"]["Weekly"]["tonnes"]["set"]:
            point[2:5] = [None, None, None]
        storage.save_source_parse_result(
            parse_source_content(
                "wgc_gold_etf_holdings",
                json.dumps(reduced_payload).encode(),
                url="https://fsapi.gold.org/api/v11/charts/etfv2/revised/holdings-chart2",
            )
        )

        assert wgc.parser_state == "PARSED_STRUCTURED"
        assert etf.parser_state == "PARSED_STRUCTURED"
        assert sge.parser_state == "PARSED_STRUCTURED"
        oi_rows = storage.list_source_domain_rows("world_gold_council_oi", limit=10)
        etf_rows = storage.list_source_domain_rows("wgc_gold_etf_holdings", limit=20)
        sge_rows = storage.list_source_domain_rows("sge_daily_report", limit=10)
        assert oi_rows[0]["venue"] == "Shanghai Futures Exchange"
        assert etf_rows[0]["dataset"] == "HOLDINGS"
        assert etf_rows[0]["region"] == "WORLD_TOTAL"
        assert not any(row["region"] == "EUROPE" for row in etf_rows)
        assert sge_rows[0]["contract"] == "Au(T+D)"
        assert sge_rows[0]["delivery_volume_lots"] == 3584
    finally:
        storage.DB_PATH = original_db_path


def test_blocked_lme_and_mcx_delivery_sources_remain_visible() -> None:
    lme = get_source_descriptor("lme_warehouse_stocks")
    mcx = get_source_descriptor("mcx_delivery_reports")

    assert lme is not None
    assert lme.parser_status == "STRUCTURED_THIRD_PARTY_FALLBACK_READY_2026_08_11"
    assert lme.authority.value == "OPEN_SOURCE_UNOFFICIAL"
    assert "informational and zero-score" in lme.limitation
    assert mcx is not None and "PARSER_PENDING" in mcx.parser_status
    assert "not substitutes" in mcx.limitation


def test_mcx_gate_lists_new_gold_context_without_relaxing_core_pass_set() -> None:
    dependency = next(item for item in GATE_DEPENDENCIES if item.code == "MCX_CONTEXT")

    assert "world_gold_council_oi" in dependency.source_keys
    assert "wgc_gold_etf_holdings" in dependency.source_keys
    assert "wgc_gold_etf_flows" in dependency.source_keys
    assert "sge_daily_report" in dependency.source_keys
