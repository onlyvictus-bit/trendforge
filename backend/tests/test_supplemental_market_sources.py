from __future__ import annotations

import io
import json
import zipfile

from trendforge_api.parsers.supplemental_market_parser import (
    parse_bse_bhavcopy,
    parse_nse_block_deal_live,
    parse_nse_option_chain,
    parse_nse_pit_current,
)
from trendforge_api.source_resolver import looks_like_data


def test_empty_option_chain_is_connected_no_data_now():
    parsed = parse_nse_option_chain(b"{}")
    assert parsed["parser_state"] == "WAIT_EMPTY_PARSE"
    assert parsed["output"]["endpointConnected"] is True
    assert parsed["output"]["noDataNow"] is True


def test_option_chain_parses_contract_rows():
    payload = {
        "records": {
            "timestamp": "13-Jul-2026 10:15:00",
            "underlying": "RELIANCE",
            "underlyingValue": 1510.5,
            "data": [
                {
                    "strikePrice": 1500,
                    "expiryDate": "30-Jul-2026",
                    "CE": {
                        "openInterest": 100,
                        "changeinOpenInterest": 10,
                        "totalTradedVolume": 20,
                        "impliedVolatility": 18.5,
                        "lastPrice": 25,
                    },
                    "PE": {
                        "openInterest": 80,
                        "changeinOpenInterest": -5,
                        "totalTradedVolume": 15,
                        "impliedVolatility": 19.2,
                        "lastPrice": 14,
                    },
                }
            ],
        }
    }
    parsed = parse_nse_option_chain(json.dumps(payload).encode())
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 2
    assert parsed["output"]["rows"][0]["optionType"] == "CE"


def test_empty_pit_is_connected_no_data_now():
    parsed = parse_nse_pit_current(b'{"acqNameList":[],"data":[]}')
    assert parsed["parser_state"] == "WAIT_EMPTY_PARSE"
    assert parsed["output"]["endpointConnected"] is True


def test_pit_preserves_actual_disposal_direction_and_lineage():
    payload = {
        "acqNameList": ["Test Insider"],
        "data": [
            {
                "did": "563850",
                "pid": "1194033",
                "symbol": "RELIANCE",
                "company": "Reliance Industries Limited",
                "acqName": "Test Insider",
                "date": "18-Feb-2026 19:06",
                "acqfromDt": "13-Feb-2026",
                "acqMode": "Off Market",
                "tdpTransactionType": "Sell",
                "secType": "Equity Shares",
                "secAcq": "2320",
                "secVal": "3294168",
                "afterAcqSharesNo": "1600",
                "afterAcqSharesPer": "0",
                "xbrl": "https://nsearchives.nseindia.com/corporate/xbrl/test.xml",
            }
        ],
    }
    parsed = parse_nse_pit_current(
        json.dumps(payload).encode(), last_modified="2026-08-10T12:00:00Z"
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    row = parsed["output"]["rows"][0]
    assert row["transactionDirection"] == "SELL"
    assert row["transactionMode"] == "Off Market"
    assert row["xbrlLink"].endswith("test.xml")
    assert row["scoreAuthority"] == "ZERO_SCORE_INFORMATIONAL"
    assert parsed["output"]["sourceRowCount"] == 1
    assert parsed["output"]["parserVersion"] == "1.1.0"


def test_pit_dedupes_and_quarantines_future_or_invalid_rows():
    valid = {
        "did": "1",
        "symbol": "INFY",
        "company": "Infosys Limited",
        "acqName": "Employee Trust",
        "date": "06-Apr-2026 16:07",
        "acqMode": "Off Market",
        "tdpTransactionType": "Buy",
        "secType": "Equity Shares",
        "secAcq": "25",
        "secVal": "31743",
    }
    payload = {
        "data": [
            valid,
            dict(valid),
            {**valid, "did": "2", "date": "11-Aug-2026 10:00"},
            {**valid, "did": "3", "symbol": ""},
        ]
    }
    parsed = parse_nse_pit_current(
        json.dumps(payload).encode(), last_modified="2026-08-10T12:00:00Z"
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 1
    assert parsed["output"]["duplicateRowCount"] == 1
    assert parsed["output"]["invalidRowCount"] == 2


def test_bse_html_is_connected_wrong_content_now():
    parsed = parse_bse_bhavcopy(b"<html><body>Download page</body></html>")
    assert parsed["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert parsed["output"]["endpointConnected"] is True
    assert parsed["output"]["noDataNow"] is True


def test_download_resolver_rejects_html_disguised_as_csv_or_zip():
    content = b"  <!DOCTYPE html><html><body>Download page</body></html>"
    assert not looks_like_data("https://example.test/bhavcopy.csv", content)
    assert not looks_like_data("https://example.test/bhavcopy.zip", content)


def test_download_resolver_keeps_declared_html_tables_parseable():
    content = (
        b"<html><body><table><tr><td>market row</td></tr></table></body></html>"
    )
    assert looks_like_data("https://example.test/official-report", content)


def test_bse_zip_parses_when_file_is_published():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr(
            "EQ130726.CSV",
            "SC_CODE,SC_NAME,OPEN,HIGH,LOW,CLOSE,NO_OF_SHRS,NET_TURNOV\n500325,RELIANCE,1500,1520,1490,1510,100000,151000000\n",
        )
    parsed = parse_bse_bhavcopy(payload.getvalue(), url="EQ130726_CSV.ZIP")
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-13"
    assert parsed["output"]["rows"][0]["scripCode"] == "500325"


def test_bse_udiff_zip_parses_current_schema():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr(
            "BhavCopy_BSE_CM_0_0_0_20260713_F_0000.csv",
            (
                "FinInstrmId,TckrSymb,TradDt,OpnPric,HghPric,LwPric,ClsPric,"
                "TtlTradgVol,TtlTrfVal\n"
                "500325,RELIANCE,2026-07-13,1500,1520,1490,1510,100000,151000000\n"
            ),
        )
    parsed = parse_bse_bhavcopy(payload.getvalue())

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-13"
    assert parsed["output"]["rows"][0]["name"] == "RELIANCE"
    assert parsed["output"]["rows"][0]["volume"] == 100000


def test_bse_udiff_direct_csv_parses_current_schema():
    content = (
        "FinInstrmId,TckrSymb,TradDt,OpnPric,HghPric,LwPric,ClsPric,"
        "TtlTradgVol,TtlTrfVal\n"
        "500325,RELIANCE,2026-07-15,1500,1520,1490,1510,100000,151000000\n"
    ).encode()

    parsed = parse_bse_bhavcopy(content)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-15"
    assert parsed["record_count"] == 1


def test_live_block_deal_is_context_not_named_sponsor_proof():
    payload = {
        "timestamp": "13-Jul-2026 08:54:51",
        "data": [
            {
                "session": "Session 1",
                "symbol": "JSFB",
                "lastPrice": 26.5,
                "totalTradedQuantity": 100000,
                "totalTradedValue": 2650000,
                "orderType": "Buy",
            }
        ],
    }
    parsed = parse_nse_block_deal_live(json.dumps(payload).encode())
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["output"]["canProveNamedSponsor"] is False
    assert parsed["output"]["rows"][0]["symbol"] == "JSFB"
