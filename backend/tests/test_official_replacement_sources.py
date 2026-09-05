from __future__ import annotations

import asyncio
import json

import httpx

from trendforge_api.institutional_sources import AsyncEndpointClient, ENDPOINTS, FetchState
from trendforge_api.parsers.official_replacement_parser import (
    parse_bse_financial_results_index,
    parse_bse_shareholding_index,
    parse_rbi_tbill_yield,
)


def test_bse_index_endpoints_warm_their_official_page_sessions() -> None:
    financial = ENDPOINTS["bse_financial_results_xbrl"]
    shareholding = ENDPOINTS["bse_shareholding_pattern"]
    assert financial.seed_url == financial.referer
    assert financial.seed_url.endswith("/corporates/comp_results.aspx")
    assert shareholding.seed_url == shareholding.referer
    assert shareholding.seed_url.endswith("/corporates/shpdrPercnt.aspx")


def test_bse_bare_empty_session_response_retries_before_valid_empty(tmp_path) -> None:
    api_calls = 0
    default_warm_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal api_calls, default_warm_calls
        if request.url.host == "www.bseindia.com":
            return httpx.Response(200, text="<html>BSE</html>", request=request)
        if request.url.params.get("flag") == "":
            default_warm_calls += 1
            return httpx.Response(200, json={"Table": []}, request=request)
        api_calls += 1
        payload = {} if api_calls == 1 else {"Table": [{"FLD_ScripCode": 500696}]}
        return httpx.Response(200, json=payload, request=request)

    async def run_fetch():
        client = AsyncEndpointClient(
            archive_root=tmp_path / "archive",
            cache_db=tmp_path / "cache.db",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.fetch("bse_shareholding_pattern")
        finally:
            await client.aclose()

    result = asyncio.run(run_fetch())

    assert api_calls == 2
    assert result.state is FetchState.RAW_ARCHIVED
    assert result.record_count == 1
    assert result.attempts == 2
    assert default_warm_calls == 1


def test_bse_financial_empty_response_reseeds_and_warms_dropdown(tmp_path) -> None:
    seed_calls = 0
    financial_calls = 0
    dropdown_calls = 0
    default_warm_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seed_calls, financial_calls, dropdown_calls, default_warm_calls
        if request.url.host == "www.bseindia.com":
            seed_calls += 1
            return httpx.Response(200, text="<html>BSE</html>", request=request)
        if request.url.path.endswith("/Corp_GetFINANCE_DRDOWN_ng/w"):
            dropdown_calls += 1
            return httpx.Response(
                200,
                json={"Table": [{"FlagDur": 4, "FlagDISPLAY": "Last 1 month"}]},
                request=request,
            )
        if request.url.params.get("FlagDur") == "1":
            default_warm_calls += 1
            return httpx.Response(200, json={"Table": []}, request=request)
        financial_calls += 1
        payload = (
            {}
            if financial_calls == 1
            else {
                "Table": [
                    {
                        "Scrip_cd": 500325,
                        "Fld_CreateDate": "2026-08-14T18:30:00",
                    }
                ]
            }
        )
        return httpx.Response(200, json=payload, request=request)

    async def run_fetch():
        client = AsyncEndpointClient(
            archive_root=tmp_path / "archive",
            cache_db=tmp_path / "cache.db",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.fetch("bse_financial_results_xbrl")
        finally:
            await client.aclose()

    result = asyncio.run(run_fetch())

    assert result.state is FetchState.RAW_ARCHIVED
    assert result.record_count == 1
    assert result.attempts == 2
    assert seed_calls == 2
    assert dropdown_calls == 1
    assert default_warm_calls == 1
    assert financial_calls == 2


def test_bse_browser_transport_fallback_replaces_bare_httpx_response(tmp_path) -> None:
    api_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal api_calls
        if request.url.host == "www.bseindia.com":
            return httpx.Response(200, text="<html>BSE</html>", request=request)
        api_calls += 1
        return httpx.Response(200, json={}, request=request)

    async def run_fetch():
        client = AsyncEndpointClient(
            archive_root=tmp_path / "archive",
            cache_db=tmp_path / "cache.db",
            transport=httpx.MockTransport(handler),
        )
        client._use_bse_browser_fallback = True
        client._bse_browser_fetch_sync = lambda **kwargs: httpx.Response(
            200,
            json={"Table": [{"FLD_ScripCode": 500696}]},
            request=httpx.Request("GET", kwargs["url"]),
        )
        try:
            return await client.fetch("bse_shareholding_pattern")
        finally:
            await client.aclose()

    result = asyncio.run(run_fetch())

    assert api_calls == 1
    assert result.state is FetchState.RAW_ARCHIVED
    assert result.record_count == 1
    assert result.attempts == 1

def test_bse_financial_results_keeps_actual_xbrl_and_dedupes_display_rows() -> None:
    payload = {
        "Table": [
            {
                "Scrip_cd": 500696,
                "scrip_name": "HINDUNILVR",
                "company_name": "Hindustan Unilever Ltd",
                "quarter_code": "130.00",
                "Qtr": "374",
                "Fld_CreateDate": "2026-07-28T19:41:55",
                "DT_TM": "2026-07-28T19:41:55",
                "Industry_name": "FMCG",
                "Fld_NatureOfReport": "Consolidated",
                "XMLName": "IFIndasDuplicateUploadDocument/HUL_IFIndAs.html",
                "Consol_XMLName": None,
            },
            {
                "Scrip_cd": 500696,
                "scrip_name": "HINDUNILVR",
                "company_name": "Hindustan Unilever Ltd",
                "quarter_code": "130.00",
                "Qtr": "130",
                "Fld_CreateDate": "2026-07-28T19:41:55",
                "DT_TM": "2026-07-28T19:41:55",
                "Industry_name": "FMCG",
                "Fld_NatureOfReport": "Consolidated",
                "XMLName": "IFIndasUploadDocument/HUL.xml",
                "Consol_XMLName": None,
            },
        ]
    }

    parsed = parse_bse_financial_results_index(json.dumps(payload).encode())

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-28"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["scripCode"] == "500696"
    assert row["symbol"] == "HINDUNILVR"
    assert row["detailUrl"].endswith("HUL_IFIndAs.html")
    assert row["recordsScope"] == "FILING_INDEX_XBRL_DISCOVERY"
    assert row["scoreEligible"] is False
    assert row["voteEligible"] is False


def test_bse_financial_parser_accepts_live_timestamp_and_relative_xbrl_path() -> None:
    payload = {
        "Table": [
            {
                "Scrip_cd": 543829,
                "scrip_name": "Global Surfaces Ltd",
                "company_name": "Global Surfaces Ltd",
                "quarter_code": "JQ2026-2027",
                "audited": "Unaudited",
                "DT_TM": "Aug 10 2026 11:56PM",
                "Fld_CreateDate": "2026-08-10T23:56:15",
                "XMLName": "IFIndasDuplicateUploadDocument/Integrated_Finance_Ind_As_543829_11082026120022_IFIndAs.html",
            }
        ]
    }

    parsed = parse_bse_financial_results_index(json.dumps(payload).encode())

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    row = parsed["output"]["rows"][0]
    assert row["detailUrl"].startswith("https://www.bseindia.com/XBRLFILES/")
    assert row["detailUrl"].endswith("_IFIndAs.html")


def test_bse_filing_indexes_wrong_schema_fail_closed() -> None:
    invalid_payloads = (
        b"{}",
        b'{"Data":"<table></table>"}',
        b"<html>Error page</html>",
    )
    for parser in (parse_bse_financial_results_index, parse_bse_shareholding_index):
        for content in invalid_payloads:
            parsed = parser(content)
            assert parsed["parser_state"] == "WAIT_SCHEMA_MISMATCH"
            assert parsed["record_count"] == 0


def test_bse_shareholding_index_preserves_filing_identity_without_inventing_holdings() -> None:
    payload = {
        "Table": [
            {
                "FLD_ScripCode": 500696,
                "Company_NAme": "Hindustan Unilever Ltd",
                "industry_name": "FMCG",
                "sQtrName": "June 2026",
                "nqtrid": "130.00&Flag=New",
                "broadcastTime": "2026-07-21T12:08:05.98",
                "EndDate": "30 Jun 2026",
                "IsXBRL": "Y",
                "XBRLAttachment": "/XBRLFILES/SHPXBRLDataXML/HUL_SP.html",
            }
        ]
    }

    parsed = parse_bse_shareholding_index(json.dumps(payload).encode())

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-21"
    row = parsed["output"]["rows"][0]
    assert row["scripCode"] == "500696"
    assert row["quarterEnd"] == "2026-06-30"
    assert row["detailUrl"].endswith("HUL_SP.html")
    assert "promoterHoldingPct" not in row
    assert row["recordsScope"] == "FILING_INDEX_XBRL_DISCOVERY"
    assert row["scoreEligible"] is False


def test_rbi_tbill_parser_extracts_all_three_tenors_and_rate_convention() -> None:
    html = b"""
    <html><body>
      <h1>Treasury Bills: Full Auction Result</h1>
      <p>August 05, 2026</p>
      <table>
        <tr><th>Item</th><th>91 Day T-Bill</th><th>182 Day T-Bill</th><th>364 Day T-Bill</th></tr>
        <tr><td>Cut-off price / Yield</td><td>98.7012 / 5.2780%</td><td>97.3071 / 5.5501%</td><td>94.6215 / 5.6998%</td></tr>
        <tr><td>Weighted Average Price / Yield</td><td>98.7073 / 5.2529%</td><td>97.3094 / 5.5452%</td><td>94.6359 / 5.6837%</td></tr>
      </table>
    </body></html>
    """

    parsed = parse_rbi_tbill_yield(html)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-05"
    assert parsed["record_count"] == 3
    rows = {row["tenorDays"]: row for row in parsed["output"]["rows"]}
    assert rows[91]["cutoffYtmPct"] == 5.278
    assert rows[91]["annualRateDecimal"] == 0.05278
    assert rows[182]["weightedAverageYtmPct"] == 5.5452
    assert rows[364]["rateConvention"] == "ANNUAL_YTM_PERCENT"
    assert all(row["scoreEligible"] is False for row in rows.values())


def test_rbi_tbill_parser_rejects_partial_or_implausible_auction() -> None:
    partial = b"Treasury Bills: Full Auction Result 05-08-2026 91 Day T-Bill 98.7012 5.2780"
    parsed = parse_rbi_tbill_yield(partial)
    assert parsed["parser_state"] != "PARSED_STRUCTURED"
    assert parsed["record_count"] == 0
