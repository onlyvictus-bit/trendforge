from __future__ import annotations

import json

from trendforge_api.parsers.amfi_nav_parser import parse_amfi_nav
from trendforge_api.parsers.nse_fii_dii_parser import parse_bse_fii_dii, parse_nse_fii_dii
from trendforge_api.parsers.nse_participant_oi_parser import parse_bse_participant_oi
from trendforge_api.source_resolver import direct_download_candidates


def test_amfi_nav_parses_scheme_rows_and_context():
    content = b"""Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date

Open Ended Schemes(Equity Scheme - Large Cap Fund)

Example Mutual Fund

100001;INF000A01001;-;Example Large Cap Fund - Direct Growth;123.4567;10-Jul-2026
"""
    parsed = parse_amfi_nav(content)
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-10"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["schemeCode"] == "100001"
    assert row["fundHouse"] == "Example Mutual Fund"
    assert row["category"].startswith("Open Ended Schemes")
    assert row["nav"] == 123.4567
    assert parsed["output"]["canProvePortfolioFlow"] is False


def test_amfi_nav_rejects_bad_header():
    parsed = parse_amfi_nav(b"code;name;value\n1;Fund;100")
    assert parsed["parser_state"] == "WAIT_SCHEMA_MISMATCH"


def test_nse_fii_dii_parses_and_checks_net_values():
    content = json.dumps(
        [
            {
                "buyValue": "17393.46",
                "category": "DII",
                "date": "13-Jul-2026",
                "netValue": "2171.70",
                "sellValue": "15221.76",
            },
            {
                "buyValue": "10386.48",
                "category": "FII/FPI",
                "date": "13-Jul-2026",
                "netValue": "-3062.27",
                "sellValue": "13448.75",
            },
        ]
    ).encode()
    parsed = parse_nse_fii_dii(content)
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-13"
    assert parsed["record_count"] == 2
    assert parsed["output"]["rows"][1]["category"] == "FII_FPI"
    assert parsed["output"]["scope"] == "MARKET_REGIME_ONLY"


def test_nse_fii_dii_rejects_inconsistent_net():
    content = b'[{"buyValue":"100","category":"DII","date":"13-Jul-2026","netValue":"90","sellValue":"20"}]'
    parsed = parse_nse_fii_dii(content)
    assert parsed["parser_state"] == "WAIT_SCHEMA_MISMATCH"


def test_new_sources_have_direct_official_candidates():
    assert direct_download_candidates("amfi_nav") == [
        "https://www.amfiindia.com/spages/NAVAll.txt"
    ]
    assert direct_download_candidates("nse_fii_dii") == [
        "https://www.nseindia.com/api/fiidiiTradeReact"
    ]
    assert direct_download_candidates("bse_fii_dii") == [
        "https://api.bseindia.com/BseIndiaAPI/api/CategoryTurnover/w"
    ]
    assert direct_download_candidates("bse_participant_oi") == [
        "https://api.bseindia.com/BseIndiaAPI/api/DeriMarketDisclosureData_ng/w"
    ]


def test_bse_fii_dii_parses_category_turnover_table():
    content = json.dumps(
        {
            "Table": [
                {
                    "REPORTING_DATE": "2026-08-10T00:00:00",
                    "ORDERFLAG": "1D",
                    "CLIENT_TYPE_BSENSE": "FII_BSENSE",
                    "PURCHASE_BSENSE": 131615600000.0,
                    "SALE_BSENSE": 111868000000.0,
                    "NET_BSENSE": 19747600000.0,
                    "CLIENT_TYPE_DII": "DII_BSENSE",
                    "PURCHASE_DII": 158685100000.0,
                    "SALE_DII": 171588000000.0,
                    "NET_DII": -12902900000.0,
                }
            ]
        }
    ).encode()
    parsed = parse_bse_fii_dii(content)
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    assert parsed["record_count"] == 2
    by_cat = {row["category"]: row for row in parsed["output"]["rows"]}
    assert by_cat["FII_FPI"]["buyValueCrore"] == 13161.56
    assert by_cat["FII_FPI"]["netValueCrore"] == 1974.76
    assert by_cat["DII"]["netValueCrore"] == -1290.29
    assert parsed["output"]["scope"] == "MARKET_REGIME_ONLY"
    assert parsed["output"]["exchange"] == "BSE"


def test_bse_fii_dii_empty_table_waits():
    parsed = parse_bse_fii_dii(b'{"Table":[]}')
    assert parsed["parser_state"] == "WAIT_EMPTY_PARSE"


def test_bse_participant_oi_parses_disclosure_table():
    content = json.dumps(
        {
            "Table": [
                {
                    "CLIENT_TYPE": "FII",
                    "IND_FUT_LONG": 78,
                    "IND_FUT_SHORT": 112,
                    "STK_FUT_LONG": 0,
                    "STK_FUT_SHORT": 0,
                    "IND_CL_LNG_CNTRCTS": 100,
                    "IND_PT_LNG_CNTRCTS": 50,
                    "IND_CL_SHRT_CNTRCTS": 80,
                    "IND_PT_SHRT_CNTRCTS": 40,
                    "STK_CL_LNG_CNTRCTS": 0,
                    "STK_PT_LNG_CNTRCTS": 0,
                    "STK_CL_SHRT_CNTRCTS": 0,
                    "STK_PT_SHRT_CNTRCTS": 0,
                    "RD_DATE": "2026-08-07T00:00:00",
                },
                {
                    "CLIENT_TYPE": "DII",
                    "IND_FUT_LONG": 10,
                    "IND_FUT_SHORT": 5,
                    "STK_FUT_LONG": 0,
                    "STK_FUT_SHORT": 0,
                    "IND_CL_LNG_CNTRCTS": 0,
                    "IND_PT_LNG_CNTRCTS": 0,
                    "IND_CL_SHRT_CNTRCTS": 0,
                    "IND_PT_SHRT_CNTRCTS": 0,
                    "STK_CL_LNG_CNTRCTS": 0,
                    "STK_PT_LNG_CNTRCTS": 0,
                    "STK_CL_SHRT_CNTRCTS": 0,
                    "STK_PT_SHRT_CNTRCTS": 0,
                    "RD_DATE": "2026-08-07T00:00:00",
                },
                {
                    "CLIENT_TYPE": "CLIENT*",
                    "IND_FUT_LONG": 1,
                    "IND_FUT_SHORT": 1,
                    "STK_FUT_LONG": 0,
                    "STK_FUT_SHORT": 0,
                    "IND_CL_LNG_CNTRCTS": 0,
                    "IND_PT_LNG_CNTRCTS": 0,
                    "IND_CL_SHRT_CNTRCTS": 0,
                    "IND_PT_SHRT_CNTRCTS": 0,
                    "STK_CL_LNG_CNTRCTS": 0,
                    "STK_PT_LNG_CNTRCTS": 0,
                    "STK_CL_SHRT_CNTRCTS": 0,
                    "STK_PT_SHRT_CNTRCTS": 0,
                    "RD_DATE": "2026-08-07T00:00:00",
                },
                {
                    "CLIENT_TYPE": "Proprietary",
                    "IND_FUT_LONG": 2,
                    "IND_FUT_SHORT": 3,
                    "STK_FUT_LONG": 0,
                    "STK_FUT_SHORT": 0,
                    "IND_CL_LNG_CNTRCTS": 0,
                    "IND_PT_LNG_CNTRCTS": 0,
                    "IND_CL_SHRT_CNTRCTS": 0,
                    "IND_PT_SHRT_CNTRCTS": 0,
                    "STK_CL_LNG_CNTRCTS": 0,
                    "STK_PT_LNG_CNTRCTS": 0,
                    "STK_CL_SHRT_CNTRCTS": 0,
                    "STK_PT_SHRT_CNTRCTS": 0,
                    "RD_DATE": "2026-08-07T00:00:00",
                },
                {"CLIENT_TYPE": "Total", "IND_FUT_LONG": 91, "IND_FUT_SHORT": 121},
            ]
        }
    ).encode()
    parsed = parse_bse_participant_oi(content)
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-07"
    assert parsed["record_count"] == 4
    by = {r["participant"]: r for r in parsed["output"]["rows"]}
    assert by["FII"]["futuresNetOi"] == -34
    assert by["DII"]["futuresNetOi"] == 5
    assert parsed["output"]["scope"] == "AGGREGATE_CONTEXT_ONLY"
    assert parsed["output"]["exchange"] == "BSE"
