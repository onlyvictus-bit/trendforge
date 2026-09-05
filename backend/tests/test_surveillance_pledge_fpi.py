from __future__ import annotations

import json
from datetime import date

from trendforge_api import storage
from trendforge_api.gate_readiness import dependency_state, gate_readiness
from trendforge_api.parsers.surveillance_pledge_fpi_parser import (
    parse_nsdl_fpi_daily,
    parse_nse_asm,
    parse_nse_gsm,
    parse_nse_oi_spurts,
    parse_nse_pledge_data,
)
from trendforge_api.source_monitor import build_source_snapshot, get_source_descriptor
from trendforge_api.source_parser import parse_source


def test_asm_combines_long_and_short_term_lists():
    row = {
        "asmSurvIndicator": "Stage I",
        "asmTime": "13-Jul-2026",
        "companyName": "Example Limited",
        "isin": "INE000A01001",
        "survCode": "LTASM - I (13)",
        "survDesc": "Long Term Additional Surveillance Measure",
        "symbol": "EXAMPLE",
    }
    payload = {
        "longterm": {"data": [row]},
        "shortterm": {"data": [{**row, "survCode": "STASM - I (11)"}]},
    }
    parsed = parse_nse_asm(json.dumps(payload).encode())
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 2
    assert {item["measure"] for item in parsed["output"]["rows"]} == {
        "LONG_TERM_ASM",
        "SHORT_TERM_ASM",
    }


def test_empty_gsm_is_valid_current_empty_list():
    parsed = parse_nse_gsm(b"[]")
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 0
    assert parsed["output"]["validEmpty"] is True
    assert parsed["output"]["noDataNow"] is True


def test_pledge_parser_preserves_reporting_date_and_risk_fields():
    payload = {
        "data": [
            {
                "comName": "Example Limited",
                "shp": "30-Jun-2026",
                "broadcastDt": "13-Jul-2026 16:32:50",
                "numSharesPledged": "1506729",
                "percPromoterHolding": "45.04",
                "percSharesPledged": "4.27",
                "totIssuedShares": "35286502",
                "totPromoterHolding": "15893364",
            }
        ]
    }
    parsed = parse_nse_pledge_data(json.dumps(payload).encode())
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-06-30"
    assert parsed["output"]["rows"][0]["pledgedPercent"] == 4.27
    assert parsed["output"]["symbolMappingRequired"] is True


def test_oi_spurts_are_not_mwpl_percentages():
    payload = {
        "timestamp": "13-Jul-2026 15:30:15",
        "currTradingDate": "13-Jul-2026",
        "prevTradingDate": "10-Jul-2026",
        "data": [
            {
                "symbol": "DMART",
                "latestOI": 81004,
                "prevOI": 63850,
                "changeInOI": 17154,
                "avgInOI": 26.87,
                "volume": 159146,
                "underlyingValue": 3994,
            }
        ],
    }
    parsed = parse_nse_oi_spurts(json.dumps(payload).encode())
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["output"]["canCalculateMwplPercent"] is False
    assert parsed["output"]["rows"][0]["oiChangePercent"] == 26.87


def test_nsdl_html_rows_are_daily_trends_not_stock_holdings():
    html = b"""<html><head><title>Latest (Daily Trends in FPI Investments)</title></head><body>
<table><tr><th>Daily Trends in FPI Investments on 13-Jul-2026</th></tr>
<tr><th>Reporting Date</th><th>Category</th><th>Route</th><th>Gross Purchases</th><th>Gross Sales</th><th>Net Investment</th><th>Net USD</th><th>Conversion</th></tr>
<tr><td>13-Jul-2026</td><td>Equity</td><td>Stock Exchange</td><td>100</td><td>80</td><td>20</td><td>2.1</td><td>95.31</td></tr></table>
</body></html>"""
    parsed = parse_nsdl_fpi_daily(html)
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-13"
    assert parsed["output"]["scope"] == "AGGREGATE_FPI_DAILY_TRENDS_ONLY"
    assert parsed["output"]["canProveStockHoldings"] is False
    assert parsed["output"]["rows"][0]["netInvestmentCrore"] == 20.0


def test_nsdl_derivative_table_is_normalized_without_claiming_stock_holdings():
    html = b"""<html><body><table>
    <tr><th>Daily Trends in FPI Derivative Trades on 13-Jul-2026</th></tr>
    <tr><th>Open Interest at the end of the date</th></tr>
    <tr><td>13-Jul-2026</td><td>Index Futures</td><td>18993</td><td>3115.26</td><td>7429</td><td>1200.55</td><td>324540</td><td>52757.51</td></tr>
    <tr><td>Stock Futures</td><td>298962</td><td>20472.09</td><td>252105</td><td>17168.62</td><td>7043778</td><td>468846.89</td></tr>
    </table></body></html>"""

    parsed = parse_nsdl_fpi_daily(html)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 2
    row = parsed["output"]["rows"][0]
    assert row["tableType"] == "DERIVATIVES"
    assert row["routeOrProduct"] == "Index Futures"
    assert row["openInterestContracts"] == 324540.0


def _save_and_parse(source_key: str, content: bytes):
    descriptor = get_source_descriptor(source_key)
    assert descriptor is not None
    storage.save_source_snapshot(
        build_source_snapshot(
            descriptor,
            status_code=200,
            content=content,
            headers={"last-modified": "Mon, 13 Jul 2026 12:00:00 GMT"},
        )
    )
    return parse_source(source_key)


def test_valid_empty_gsm_is_persisted_as_fresh_structured_source(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sources.db")
    parsed = _save_and_parse("nse_gsm", b"[]")

    assert parsed.parser_state == "PARSED_STRUCTURED"
    state = dependency_state("nse_gsm")
    assert state["state"] == "WAIT_SOURCE_ACTIVATION"
    assert state["compilerActivationReady"] is False
    assert state["contractGatePermission"] is False
    output = storage.list_source_parser_outputs("nse_gsm", limit=1)[0]
    assert output["parser_status"] == "STRUCTURED_OK"
    assert output["record_count"] == 0


def test_surveillance_gate_passes_clean_symbol_and_blocks_listed_symbol(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sources.db")
    current = date.today().strftime("%d-%b-%Y")
    row = {
        "asmSurvIndicator": "Stage I",
        "asmTime": current,
        "companyName": "Example Limited",
        "isin": "INE000A01001",
        "survCode": "LTASM - I (13)",
        "survDesc": "Long Term Additional Surveillance Measure",
        "symbol": "EXAMPLE",
    }
    payload = {"longterm": {"data": [row]}, "shortterm": {"data": []}}
    _save_and_parse("nse_asm", json.dumps(payload).encode())
    _save_and_parse("nse_gsm", b"[]")

    blocked = {row["code"]: row for row in gate_readiness("EXAMPLE")["gates"]}[
        "G03_STOCK_SAFETY"
    ]
    clean = {row["code"]: row for row in gate_readiness("RELIANCE")["gates"]}[
        "G03_STOCK_SAFETY"
    ]

    assert blocked["state"] == "BLOCKED_SURVEILLANCE"
    assert blocked["tradeGateEffect"] == "DO_NOT_PASS_READY"
    assert clean["state"] == "WAIT_SOURCE_ACTIVATION"
    assert clean["tradeGateEffect"] == "DO_NOT_PASS_READY"


def test_new_structured_sources_persist_domain_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sources.db")
    today = date.today().strftime("%d-%b-%Y")
    pledge = {
        "data": [
            {
                "comName": "Example Limited",
                "shp": today,
                "broadcastDt": today,
                "numSharesPledged": "1000",
                "percPromoterHolding": "45.04",
                "percSharesPledged": "4.27",
                "totIssuedShares": "50000",
                "totPromoterHolding": "22520",
            }
        ]
    }
    oi_spurts = {
        "currTradingDate": today,
        "prevTradingDate": "10-Jul-2026",
        "data": [
            {
                "symbol": "EXAMPLE",
                "latestOI": 81004,
                "prevOI": 63850,
                "changeInOI": 17154,
                "avgInOI": 26.87,
                "volume": 159146,
                "underlyingValue": 3994,
            }
        ],
    }
    nsdl = f"""<html><body><table>
    <tr><th>Daily Trends in FPI Investments on {today}</th></tr>
    <tr><th>Reporting Date</th><th>Category</th><th>Route</th><th>Gross Purchases</th><th>Gross Sales</th><th>Net Investment</th><th>Net USD</th><th>Conversion</th></tr>
    <tr><td>{today}</td><td>Equity</td><td>Stock Exchange</td><td>100</td><td>80</td><td>20</td><td>2.1</td><td>95.31</td></tr>
    </table></body></html>""".encode()

    _save_and_parse("nse_pledge_data", json.dumps(pledge).encode())
    _save_and_parse("nse_oi_spurts", json.dumps(oi_spurts).encode())
    _save_and_parse("nsdl_fpi_daily", nsdl)

    assert len(storage.list_source_domain_rows("nse_pledge_data")) == 1
    assert len(storage.list_source_domain_rows("nse_oi_spurts")) == 1
    assert len(storage.list_source_domain_rows("nsdl_fpi_daily")) == 1
    assert (
        storage.list_source_domain_rows("nse_pledge_data")[0]["symbol_mapping_status"]
        == "PENDING"
    )
