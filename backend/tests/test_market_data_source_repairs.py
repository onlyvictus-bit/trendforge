from __future__ import annotations

import json
from datetime import UTC, date, datetime
from urllib.error import URLError

from trendforge_api.market_data_registry import AcquisitionOwner, load_market_data_registry
from trendforge_api.market_data_service import (
    ParameterContext,
    RawAcquisition,
    default_normalizer,
)
from trendforge_api.parsers.cftc_cot_parser import parse_cftc_cot_positions
from trendforge_api.parsers.surveillance_pledge_fpi_parser import (
    parse_nsdl_fpi_fortnightly,
)
from trendforge_api.source_resolver import (
    AMFI_SCHEME_DIRECTORY_URL,
    _fetch_with_retry,
    _nsdl_fortnightly_report_is_usable,
    discover_nsdl_fortnightly_report_links,
)


NOW = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


def _context() -> ParameterContext:
    return ParameterContext(
        trading_date=date(2026, 8, 5),
        market_session="CLOSED",
    )


def test_slb_registry_uses_archive_resolver_not_dead_api() -> None:
    contract = load_market_data_registry().by_key["nse_slb"]

    assert contract.acquisition_owner is AcquisitionOwner.RESOLVER_MONITOR
    assert contract.endpoint_key is None
    assert contract.parser_or_adapter_id == "structured:nse_slb"


def test_structured_alias_uses_declared_large_deals_parser() -> None:
    contract = load_market_data_registry().by_key["nse_large_deals_snapshot"]
    payload = {
        "as_on_date": "05-Aug-2026",
        "BULK_DEALS_DATA": [
            {
                "symbol": "ALPHA",
                "clientName": "FUND A",
                "buySell": "BUY",
                "qty": "100",
                "watp": "125.50",
            }
        ],
        "BLOCK_DEALS_DATA": [],
        "SHORT_DEALS_DATA": [],
    }
    raw = RawAcquisition.success(
        source_url="https://www.nseindia.com/api/snapshot-capital-market-largedeal",
        status_code=200,
        media_type="application/json",
        content=json.dumps(payload).encode(),
        payload=payload,
        fetched_at=NOW,
    )

    parsed = default_normalizer(contract, (raw,), _context())

    assert contract.normalized_source_key == "nse_market_activity"
    assert parsed.parser_state == "PARSED_STRUCTURED"
    assert parsed.data_date == date(2026, 8, 5)
    assert len(parsed.records) == 1
    assert parsed.records[0]["symbol"] == "ALPHA"


def test_cftc_legacy_layout_is_parsed_without_managed_money_mislabel() -> None:
    payload = [
        {
            "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
            "report_date_as_yyyy_mm_dd": "2026-07-28T00:00:00.000",
            "cftc_contract_market_code": "088691",
            "open_interest_all": "100000",
            "noncomm_positions_long_all": "60000",
            "noncomm_positions_short_all": "30000",
            "comm_positions_long_all": "20000",
            "comm_positions_short_all": "25000",
            "nonrept_positions_long_all": "5000",
            "nonrept_positions_short_all": "7000",
        }
    ]

    parsed = parse_cftc_cot_positions(json.dumps(payload).encode())

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    row = parsed["output"]["positions"][0]
    assert row["sourceLayout"] == "CFTC_LEGACY"
    assert row["nonCommercialNet"] == 30000.0
    assert "managedMoneyNet" not in row
    assert parsed["output"]["regimes"][0]["signalFamily"] == "NON_COMMERCIAL"


def test_cftc_tff_layout_is_parsed_as_financial_context() -> None:
    payload = [
        {
            "market_and_exchange_names": "U.S. DOLLAR INDEX - ICE FUTURES U.S.",
            "report_date_as_yyyy_mm_dd": "2026-07-28T00:00:00.000",
            "cftc_contract_market_code": "098662",
            "open_interest_all": "50000",
            "dealer_positions_long_all": "10000",
            "dealer_positions_short_all": "12000",
            "asset_mgr_positions_long": "18000",
            "asset_mgr_positions_short": "9000",
            "lev_money_positions_long": "14000",
            "lev_money_positions_short": "17000",
            "other_rept_positions_long": "3000",
            "other_rept_positions_short": "2500",
        }
    ]

    parsed = parse_cftc_cot_positions(json.dumps(payload).encode())

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    row = parsed["output"]["positions"][0]
    assert row["sourceLayout"] == "CFTC_TFF"
    assert row["scope"] == "FINANCIAL_REGIME_ONLY"
    assert row["leveragedMoneyNet"] == -3000.0
    assert parsed["output"]["regimes"][0]["signalFamily"] == "LEVERAGED_MONEY"


def test_nsdl_latest_report_link_is_discovered_without_posting() -> None:
    selection = b"""<select name='ddlfortnighly'>
    <option value='~/StaticReports/Fortnightly_Sector_wise_FII_Investment_Data/FIIInvestSector_Jul312026.html'>JUL 31, 2026</option>
    <option value='~/StaticReports/Fortnightly_Sector_wise_FII_Investment_Data/FIIInvestSector_Jul152026.html'>JUL 15, 2026</option>
    </select>"""

    links = discover_nsdl_fortnightly_report_links(
        "https://pilot.fpi.nsdl.co.in/Reports/FPI_Fortnightly_Selection.aspx",
        selection,
    )

    assert links[0] == (
        "https://pilot.fpi.nsdl.co.in/StaticReports/"
        "Fortnightly_Sector_wise_FII_Investment_Data/"
        "FIIInvestSector_Jul312026.html"
    )


def test_nsdl_static_report_uses_url_date_and_sector_column() -> None:
    html = b"""<html><body>
    <script>var unrelatedBuildDate = '12-Aug-2024';</script>
    <table>
      <tr><th>Sr No</th><th>Sector</th><th>AUC</th><th>Net Investment</th></tr>
      <tr><td>1</td><td>Automobile and Auto Components</td><td>4,99,910</td><td>2,372</td></tr>
    </table>
    </body></html>"""

    parsed = parse_nsdl_fpi_fortnightly(
        html,
        url=(
            "https://pilot.fpi.nsdl.co.in/StaticReports/"
            "Fortnightly_Sector_wise_FII_Investment_Data/"
            "FIIInvestSector_Jul312026.html"
        ),
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-31"
    assert parsed["output"]["rows"][0]["sector"] == (
        "Automobile and Auto Components"
    )


def test_nsdl_resolver_rejects_table_only_page_without_sector_rows() -> None:
    url = (
        "https://pilot.fpi.nsdl.co.in/StaticReports/"
        "Fortnightly_Sector_wise_FII_Investment_Data/"
        "FIIInvestSector_Jul312026.html"
    )
    empty = b"<html><table><tr><td>No data available</td></tr></table></html>"
    populated = b"""<html><table>
      <tr><th>Sr No</th><th>Sector</th><th>AUC</th></tr>
      <tr><td>1</td><td>Financial Services</td><td>100</td></tr>
    </table></html>"""

    assert not _nsdl_fortnightly_report_is_usable(empty, url)
    assert _nsdl_fortnightly_report_is_usable(populated, url)


def test_transient_fetch_retries_without_retrying_permanent_http_errors() -> None:
    calls = 0

    def flaky(_url: str, _timeout: int):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise URLError("temporary")
        return 200, {"content-type": "application/json"}, b"[]"

    result = _fetch_with_retry(
        "https://www.amfiindia.com/api/example",
        10,
        fetcher=flaky,
        sleeper=lambda _seconds: None,
    )

    assert calls == 3
    assert result[0] == 200


def test_amfi_resolver_seeds_from_official_directory_not_registry_api_label() -> None:
    contract = load_market_data_registry().by_key["amfi_scheme_wise"]

    assert "quarter=resolved" in contract.canonical_url
    assert AMFI_SCHEME_DIRECTORY_URL == (
        "https://www.amfiindia.com/otherdata/scheme-wise-disclosure"
    )
