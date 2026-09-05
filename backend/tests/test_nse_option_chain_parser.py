"""Focused fixtures for NSE option-chain empty vs populated shapes."""
from __future__ import annotations

import json

from trendforge_api.parsers.supplemental_market_parser import parse_nse_option_chain

EMPTY_OBJECT = b"{}"

POPULATED = json.dumps(
    {
        "records": {
            "timestamp": "31-Jul-2026 15:30:00",
            "underlyingValue": 3010.0,
            "expiryDates": ["30-Jul-2026"],
            "data": [
                {
                    "expiryDate": "30-Jul-2026",
                    "strikePrice": 3000,
                    "CE": {
                        "underlying": "RELIANCE",
                        "openInterest": 100,
                        "changeinOpenInterest": 10,
                        "totalTradedVolume": 50,
                        "impliedVolatility": 18.5,
                        "lastPrice": 40.0,
                    },
                    "PE": {
                        "underlying": "RELIANCE",
                        "openInterest": 200,
                        "changeinOpenInterest": -5,
                        "totalTradedVolume": 80,
                        "impliedVolatility": 20.0,
                        "lastPrice": 25.0,
                    },
                },
                {
                    "expiryDate": "30-Jul-2026",
                    "strikePrice": 3050,
                    "CE": {
                        "underlying": "RELIANCE",
                        "openInterest": 300,
                        "changeinOpenInterest": 20,
                        "totalTradedVolume": 90,
                        "impliedVolatility": 17.0,
                        "lastPrice": 18.0,
                    },
                    "PE": {
                        "underlying": "RELIANCE",
                        "openInterest": 100,
                        "changeinOpenInterest": 8,
                        "totalTradedVolume": 40,
                        "impliedVolatility": 21.0,
                        "lastPrice": 55.0,
                    },
                },
            ],
        }
    }
).encode()


def test_empty_object_is_soft_empty_not_populated() -> None:
    result = parse_nse_option_chain(EMPTY_OBJECT)
    assert result["parser_state"] == "WAIT_EMPTY_PARSE"
    assert result["record_count"] == 0
    assert result["output"]["softEmptyObject"] is True
    assert result["output"]["rows"] == []


def test_populated_chain_yields_ce_pe_rows_pcr_and_max_pain() -> None:
    result = parse_nse_option_chain(POPULATED)
    assert result["parser_state"] == "PARSED_STRUCTURED"
    assert result["record_count"] == 4
    rows = result["output"]["rows"]
    assert {row["optionType"] for row in rows} == {"CE", "PE"}
    assert all(row["symbol"] == "RELIANCE" for row in rows)
    assert all("openInterest" in row and "iv" in row for row in rows)
    metrics = result["output"]["metrics"]
    assert metrics["callOiTotal"] == 400
    assert metrics["putOiTotal"] == 300
    assert metrics["pcrOi"] == 0.75
    assert metrics["maxPainStrike"] in {3000.0, 3050.0}
    assert metrics["callOiWalls"][0]["strike"] == 3050.0
    assert metrics["putOiWalls"][0]["strike"] == 3000.0


def test_v3_contract_identity_falls_back_to_request_url() -> None:
    payload = json.dumps(
        {
            "records": {
                "timestamp": "10-Aug-2026 15:40:00",
                "underlyingValue": 1327.3,
                "data": [
                    {
                        "strikePrice": 1300,
                        "CE": {"openInterest": 100, "lastPrice": 36.5},
                        "PE": {
                            "underlying": "RELIANCE",
                            "expiryDate": "25-08-2026",
                            "openInterest": 200,
                            "lastPrice": 10.05,
                        },
                    }
                ],
            }
        }
    ).encode()

    result = parse_nse_option_chain(
        payload,
        url=(
            "https://www.nseindia.com/api/option-chain-v3"
            "?type=Equity&symbol=RELIANCE&expiry=25-Aug-2026"
        ),
    )

    assert result["parser_state"] == "PARSED_STRUCTURED"
    assert result["record_count"] == 2
    assert all(row["symbol"] == "RELIANCE" for row in result["output"]["rows"])
    assert all(row["expiry"] for row in result["output"]["rows"])
    assert result["output"]["invalidRowCount"] == 0
    assert result["output"]["parserVersion"] == "1.1.0"


def test_contracts_without_any_identity_fail_closed() -> None:
    payload = json.dumps(
        {
            "records": {
                "timestamp": "10-Aug-2026 15:40:00",
                "underlyingValue": 1327.3,
                "data": [{"strikePrice": 1300, "CE": {"openInterest": 100}}],
            }
        }
    ).encode()

    result = parse_nse_option_chain(payload)

    assert result["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert result["record_count"] == 0
