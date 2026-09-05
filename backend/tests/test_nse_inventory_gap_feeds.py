from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import date

from trendforge_api.parsers.nse_inventory_gap_parser import (
    parse_kite_derivatives_contract_master,
    parse_nse_board_meetings,
    parse_nse_ipo_issue_calendar,
    parse_nse_most_active_derivatives,
    parse_nse_pr_market_snapshot,
    parse_nse_trade_to_trade,
)
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_resolver import direct_download_candidates


def csv_bytes(rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def pr_zip() -> bytes:
    pd_rows = [
        {
            "SERIES": series,
            "SYMBOL": f"SYM{index}",
            "SECURITY": f"Security {index}",
            "PREV_CL_PR": "100",
            "OPEN_PRICE": "100",
            "HIGH_PRICE": "121" if index == 0 else "105",
            "LOW_PRICE": "79" if index == 1 else "95",
            "CLOSE_PRICE": str(120 - index),
            "NET_TRDVAL": "1000000",
            "NET_TRDQTY": "1000",
            "TRADES": "10",
            "HI_52_WK": "120",
            "LO_52_WK": "80",
        }
        for index, series in enumerate(["BE", "BT", "IT", "ST", "BZ", "SZ", "EQ", "SM"])
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("pd04082026.csv", csv_bytes(pd_rows))
        archive.writestr(
            "bc04082026.csv",
            csv_bytes(
                [
                    {
                        "SYMBOL": "SYM6",
                        "SERIES": "EQ",
                        "SECURITY": "Security 6",
                        "EX_DT": "05-Aug-2026",
                        "RECORD_DT": "06-Aug-2026",
                        "PURPOSE": "Dividend",
                    },
                    {
                        "SYMBOL": "DEBT",
                        "SERIES": "N1",
                        "SECURITY": "Debt security",
                        "EX_DT": "05-Aug-2026",
                        "RECORD_DT": "06-Aug-2026",
                        "PURPOSE": "Interest",
                    },
                ]
            ),
        )
        archive.writestr(
            "mcap04082026.csv",
            csv_bytes(
                [
                    {
                        "Symbol": "SYM6",
                        "Series": "EQ",
                        "Security Name": "Security 6",
                        "Close Price/Paid up value(Rs.)": "114",
                        "Market Cap(Rs.)": "25000000000",
                        "Category": "A",
                    }
                ]
            ),
        )
    return buffer.getvalue()


def test_t2t_includes_all_six_series_and_excludes_eq_sm() -> None:
    result = parse_nse_trade_to_trade(
        pr_zip(), url="https://archives.nseindia.com/archives/equities/bhavcopy/pr/PR040826.zip"
    )
    assert result["parser_state"] == "PARSED_STRUCTURED"
    assert {row["series"] for row in result["output"]["rows"]} == {
        "BE",
        "BT",
        "IT",
        "ST",
        "BZ",
        "SZ",
    }
    assert all(row["intradayEligible"] is False for row in result["output"]["rows"])


def test_kite_dump_filters_and_aggregates_without_embedding_raw_contracts() -> None:
    head = "exchange,instrument_type,name,lot_size,expiry\n"
    rows = ["NFO,FUT,ALPHA,50,2026-08-27"] * 89998
    rows += ["NFO,CE,ALPHA,50,2026-08-27", "NSE,EQ,IGNORE,1,2026-08-27", "MCX,FUT,GOLD,1,2026-09-04"]
    result = parse_kite_derivatives_contract_master((head + "\n".join(rows)).encode())
    assert result["parser_state"] == "PARSED_STRUCTURED"
    assert result["output"]["sourceRowCount"] == 90001
    assert result["output"]["filteredContractCount"] == 90000
    assert result["record_count"] == 2
    alpha = next(row for row in result["output"]["rows"] if row["symbol"] == "ALPHA")
    assert alpha["nearestLotSize"] == 50
    assert alpha["contractTypes"] == ["CE", "FUT"]


def test_board_meeting_and_ipo_status_are_preserved() -> None:
    board = parse_nse_board_meetings(
        json.dumps(
            [
                {
                    "bm_symbol": "ALPHA",
                    "bm_date": "14-Aug-2026",
                    "bm_purpose": "Financial Results/Other business matters",
                    "bm_desc": "Quarterly results",
                }
            ]
        ).encode()
    )
    assert board["output"]["rows"][0]["resultsEvent"] is True
    assert board["output"]["rows"][0]["meetingDate"] == "2026-08-14"

    ipo = parse_nse_ipo_issue_calendar(
        json.dumps(
            {
                "data": [
                    {"symbol": "ACTIVE", "status": "Active", "feedSection": "current"},
                    {"symbol": "CLOSED", "status": "Closed", "feedSection": "issue_calendar"},
                    {"symbol": "FORTH", "status": "Forthcoming", "feedSection": "issue_calendar"},
                ]
            }
        ).encode()
    )
    assert [row["status"] for row in ipo["output"]["rows"]] == [
        "Active",
        "Closed",
        "Forthcoming",
    ]


def test_most_active_merges_volume_value_and_uses_endpoint_section() -> None:
    contract = {
        "underlying": "ALPHA",
        "identifier": "FUTSTKALPHA27-08-2026XX0.00",
        "instrumentType": "FUTSTK",
        "expiryDate": "27-Aug-2026",
        "numberOfContractsTraded": 25,
        "openInterest": 100,
    }
    result = parse_nse_most_active_derivatives(
        json.dumps(
            {"volume": {"data": [contract]}, "value": {"data": [contract]}}
        ).encode(),
        url="https://www.nseindia.com/api/snapshot-derivatives-equity?index=futures",
    )
    assert result["record_count"] == 1
    assert result["output"]["rows"][0]["basis"] == "volume+value"
    assert result["output"]["rows"][0]["section"] == "futures"


def test_pr_snapshot_has_symbols_and_drops_debt_corporate_action() -> None:
    result = parse_nse_pr_market_snapshot(
        pr_zip(), url="https://archives.nseindia.com/archives/equities/bhavcopy/pr/PR040826.zip"
    )
    rows = result["output"]["rows"]
    assert result["parser_state"] == "PARSED_STRUCTURED"
    assert rows and all(row.get("symbol") for row in rows)
    assert not any(row["symbol"] == "DEBT" for row in rows)
    mcap = next(row for row in rows if row["section"] == "mcap")
    assert mcap["marketCapCr"] == 2500.0


def test_catalog_and_resolver_expose_all_seven_keys() -> None:
    keys = {
        "nse_trade_to_trade",
        "kite_derivatives_contract_master",
        "nse_board_meetings",
        "nse_most_active_futures",
        "nse_most_active_options",
        "nse_ipo_issue_calendar",
        "nse_pr_market_snapshot",
    }
    assert all(get_source_descriptor(key) is not None for key in keys)
    for key in keys:
        assert direct_download_candidates(key, today=date(2026, 8, 4))
