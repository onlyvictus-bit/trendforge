from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trendforge_api.institutional_sources import (
    AsyncEndpointClient,
    EndpointFetchResult,
    FetchState,
    intraday_stock_detail_requests,
)
from trendforge_api.intraday_stock_details import (
    build_intraday_stock_detail_snapshot,
    save_intraday_stock_detail_snapshot,
)


NOW = datetime(2026, 7, 17, 10, 30, tzinfo=UTC)


def _result(endpoint_key: str, payload, *, url: str | None = None) -> EndpointFetchResult:
    return EndpointFetchResult(
        endpoint_key=endpoint_key,
        state=FetchState.RAW_ARCHIVED,
        fetched_at=NOW,
        url=url or f"https://www.nseindia.com/api/{endpoint_key}",
        content_hash=f"hash-{endpoint_key}",
        record_count=1,
        payload=payload,
        can_score=False,
    )


def test_intraday_request_builder_uses_new_stock_detail_sources() -> None:
    requests = intraday_stock_detail_requests(
        from_date="2026-07-01",
        to_date="2026-07-17",
        sector_indices=("NIFTY AUTO", "NIFTY OIL & GAS"),
        symbols=("RELIANCE",),
    )

    keys = [key for key, _ in requests]
    assert "nse_oi_spurts_contracts" in keys
    assert "nse_live_equity_derivatives_stock_opt" in keys
    assert "nse_live_equity_derivatives_index_opt" in keys
    assert "nse_live_equity_derivatives_banknifty_fut" in keys
    assert "bse_order_win_announcements" in keys
    assert "nsdl_fpi_daily_reportdetail" in keys
    assert "nsdl_fpi_fortnightly" in keys
    assert "nse_preopen_fo" in keys
    assert "nse_block_deal" in keys
    assert "nse_most_active_underlying" in keys
    assert "nse_market_turnover" in keys
    assert "nse_variations_gainers" in keys
    assert "nse_variations_loosers" in keys
    assert "nse_financial_results" in keys
    assert "nse_bulk_deals_today_csv" in keys
    assert keys.count("nse_sector_constituents") == 2
    assert "nse_quote_equity" in keys
    assert "nse_quote_equity_trade_info" in keys
    assert "nse_option_chain_equity" in keys
    assert "nse_quote_derivative" in keys
    assert "nse_pit_symbol" in keys
    assert "nse_shareholding_pattern" in keys


def test_sector_index_ampersand_is_encoded_for_nse_query() -> None:
    spec = AsyncEndpointClient._build_url
    endpoint = __import__(
        "trendforge_api.institutional_sources",
        fromlist=["ENDPOINTS"],
    ).ENDPOINTS["nse_sector_constituents"]

    url = spec(endpoint, {"sector_index": "NIFTY OIL & GAS"})

    assert "NIFTY%20OIL%20%26%20GAS" in url


def test_intraday_snapshot_merges_oi_derivatives_and_sector_evidence() -> None:
    results = [
        _result(
            "nse_oi_spurts_contracts",
            {
                "data": [
                    {
                        "Rise-in-OI-Rise": [
                            {
                                "symbol": "RELIANCE",
                                "instrument": "Stock Futures",
                                "latestOI": 120000,
                                "prevOI": 90000,
                            }
                        ],
                        "Rise-in-OI-Slide": [
                            {
                                "symbol": "INFY",
                                "instrument": "Stock Futures",
                                "latestOI": 100000,
                                "prevOI": 80000,
                            }
                        ],
                    }
                ]
            },
        ),
        _result(
            "nse_live_equity_derivatives_stock_opt",
            {
                "data": [
                    {
                        "underlying": "RELIANCE",
                        "contract": "RELIANCE 3000 CE",
                        "volume": 50000,
                        "openInterest": 200000,
                    }
                ]
            },
        ),
        _result(
            "nse_live_equity_derivatives_stock_fut",
            {
                "data": [
                    {
                        "underlying": "RELIANCE",
                        "contract": "RELIANCE FUT",
                        "volume": 30000,
                        "openInterest": 150000,
                    }
                ]
            },
        ),
        _result(
            "nse_live_equity_derivatives_index_opt",
            {
                "data": [
                    {
                        "underlying": "NIFTY",
                        "instrumentType": "Index Options",
                        "volume": 120000,
                        "openInterest": 900000,
                    }
                ]
            },
        ),
        _result(
            "nse_live_equity_derivatives_index_fut",
            {
                "data": [
                    {
                        "underlying": "NIFTY",
                        "instrumentType": "Index Futures",
                        "volume": 15000,
                        "openInterest": 300000,
                    }
                ]
            },
        ),
        _result(
            "nse_live_equity_derivatives_banknifty_opt",
            {
                "data": [
                    {
                        "underlying": "BANKNIFTY",
                        "instrumentType": "Index Options",
                        "volume": 90000,
                        "openInterest": 700000,
                    }
                ]
            },
        ),
        _result(
            "nse_live_equity_derivatives_banknifty_fut",
            {
                "data": [
                    {
                        "underlying": "BANKNIFTY",
                        "instrumentType": "Index Futures",
                        "volume": 12000,
                        "openInterest": 250000,
                    }
                ]
            },
        ),
        _result(
            "nse_oi_spurts",
            {
                "data": [
                    {
                        "symbol": "RELIANCE",
                        "total": 250000,
                        "underlyingValue": 2975,
                    }
                ]
            },
        ),
        _result(
            "nse_most_active_underlying",
            {"data": [{"underlying": "RELIANCE", "total": 180000, "volume": 12000}]},
        ),
        _result("nse_market_turnover", {"data": [{"name": "CM", "value": 1000}]}),
        _result("nse_variations_gainers", {"allSec": {"data": [{"symbol": "A"}, {"symbol": "B"}]}, "FOSec": {"data": [{"symbol": "C"}]}}),
        _result("nse_variations_loosers", {"allSec": {"data": [{"symbol": "D"}]}, "FOSec": {"data": []}}),
        _result(
            "nse_financial_results",
            {"data": [{"symbol": "RELIANCE", "periodEnded": "30-Jun-2026"}]},
        ),
        _result(
            "nse_quote_equity",
            {
                "priceInfo": {
                    "lastPrice": 3010,
                    "pChange": 1.2,
                    "vwap": 2990,
                    "upperCP": 3200,
                    "lowerCP": 2800,
                },
                "securityInfo": {"derivatives": "Yes"},
            },
            url="https://www.nseindia.com/api/quote-equity?symbol=RELIANCE",
        ),
        _result(
            "nse_quote_equity_trade_info",
            {
                "securityWiseDP": {
                    "deliveryQuantity": 70000,
                    "quantityTraded": 100000,
                    "deliveryToTradedQuantity": 70,
                },
                "marketDeptOrderBook": {
                    "totalBuyQuantity": 250000,
                    "totalSellQuantity": 200000,
                    "tradeInfo": {"totalTradedValue": 3500},
                },
            },
            url="https://www.nseindia.com/api/quote-equity?symbol=RELIANCE&section=trade_info",
        ),
        _result(
            "nse_option_chain_equity",
            {
                "records": {
                    "underlyingValue": 3010,
                    "expiryDates": ["30-Jul-2026"],
                    "data": [
                        {
                            "expiryDate": "30-Jul-2026",
                            "strikePrice": 3000,
                            "CE": {"openInterest": 100, "impliedVolatility": 18},
                            "PE": {"openInterest": 200, "impliedVolatility": 20},
                        },
                        {
                            "expiryDate": "30-Jul-2026",
                            "strikePrice": 3050,
                            "CE": {"openInterest": 300, "impliedVolatility": 17},
                            "PE": {"openInterest": 100, "impliedVolatility": 21},
                        },
                    ],
                }
            },
            url="https://www.nseindia.com/api/option-chain-equities?symbol=RELIANCE",
        ),
        _result(
            "nse_quote_derivative",
            {
                "underlyingValue": 3010,
                "stocks": [
                    {
                        "metadata": {"instrumentType": "Stock Futures", "lastPrice": 3025},
                        "marketDeptOrderBook": {
                            "tradeInfo": {
                                "openInterest": 250000,
                                "pchangeinOpenInterest": 4.5,
                            }
                        },
                    }
                ],
            },
            url="https://www.nseindia.com/api/quote-derivative?symbol=RELIANCE",
        ),
        _result(
            "nse_pit_symbol",
            {
                "data": [
                    {
                        "symbol": "RELIANCE",
                        "tdpTransactionType": "Market Purchase",
                        "secVal": "1000000",
                    }
                ]
            },
            url="https://www.nseindia.com/api/corporates-pit?index=equities&symbol=RELIANCE&from_date=01-07-2026&to_date=17-07-2026",
        ),
        _result(
            "nse_shareholding_pattern",
            [
                {
                    "symbol": "RELIANCE",
                    "name": "Reliance Industries Limited",
                    "date": "30-JUN-2026",
                    "pr_and_prgrp": "50.48",
                    "public_val": "49.52",
                    "xbrl": "https://nsearchives.nseindia.com/corporate/xbrl/SHP.xml",
                }
            ],
            url="https://www.nseindia.com/api/corporate-share-holdings-master?index=equities&symbol=RELIANCE",
        ),
        _result(
            "nse_all_indices",
            {
                "data": [
                    {"key": "SECTORAL INDICES", "index": "NIFTY AUTO", "percentChange": 2.5},
                    {"key": "SECTORAL INDICES", "index": "NIFTY IT", "percentChange": -2.0},
                ]
            },
        ),
        _result(
            "nse_sector_constituents",
            {
                "data": [
                    {"index": "NIFTY AUTO", "pChange": 2.5},
                    {"symbol": "RELIANCE", "pChange": 3.1},
                ]
            },
            url="https://www.nseindia.com/api/equity-stock-indices?index=NIFTY%20AUTO",
        ),
        _result(
            "bse_order_win_announcements",
            {"Table": [{"SCRIP_CD": "500325", "NEWSSUB": "Award of order", "ATTACHMENTNAME": "order.pdf"}]},
        ),
        _result(
            "nse_preopen_fo",
            {
                "data": [
                    {
                        "metadata": {
                            "symbol": "RELIANCE",
                            "iep": 3034.5,
                            "previousClose": 2975.0,
                            "pChange": 2.0,
                            "finalQuantity": 125000,
                        }
                    }
                ]
            },
        ),
        _result(
            "nse_block_deal",
            {
                "data": [
                    {
                        "symbol": "RELIANCE",
                        "clientName": "INSTITUTION A",
                        "buySell": "BUY",
                        "quantity": 10000,
                        "tradePrice": 3000,
                    }
                ]
            },
        ),
        _result(
            "nse_bulk_deals_today_csv",
            (
                "Date,Symbol,Security Name,Client Name,Buy/Sell,Quantity Traded,Trade Price / Wght. Avg. Price,Remarks\n"
                "16-JUL-2026,RELIANCE,Reliance Industries Limited,INSTITUTION B,BUY,5000,3010,-\n"
            ),
            url="https://archives.nseindia.com/content/equities/bulk.csv",
        ),
        _result(
            "nsdl_fpi_daily_reportdetail",
            "<html><table><tr><td>FPI daily</td></tr></table><table><tr><td>Debt</td></tr></table></html>",
        ),
        _result(
            "nsdl_fpi_fortnightly",
            "<html><table id='rpt'><tr><td>Financial Services</td></tr></table></html>",
        ),
    ]

    snapshot = build_intraday_stock_detail_snapshot(results)

    candidate = next(item for item in snapshot.candidates if item.symbol == "RELIANCE")
    assert candidate.state == "WAIT_CONFIRMATION"
    assert candidate.direction_hint == "BULLISH_EVIDENCE"
    assert candidate.detail_score >= 55
    assert candidate.can_unlock_ready is False
    assert "LONG_BUILDUP" in candidate.oi_signals
    assert candidate.top_active_contract == "RELIANCE 3000 CE"
    assert candidate.preopen_gap_pct == 2.0
    assert candidate.preopen_iep == 3034.5
    assert candidate.preopen_matched_qty == 125000
    assert candidate.block_deal_notional == 30_000_000
    assert candidate.bulk_deal_notional == 15_050_000
    assert candidate.last_price == 3010
    assert candidate.vwap == 2990
    assert candidate.delivery_pct == 70
    assert candidate.pcr == 0.75
    assert candidate.resistance == 3050
    assert candidate.support == 3000
    assert candidate.derivative_contract_count == 1
    assert candidate.derivative_quote_oi == 250000
    assert candidate.futures_basis == 15
    assert candidate.futures_oi_change_pct == 4.5
    assert candidate.most_active_derivative_value == 180000
    assert candidate.insider_net_value == 1_000_000
    assert candidate.promoter_holding_pct == 50.48
    assert candidate.public_holding_pct == 49.52
    assert candidate.shareholding_date == "30-JUN-2026"
    assert candidate.recent_financial_result is True
    assert snapshot.bse_order_wins[0].attachment_url.endswith("/order.pdf")
    assert snapshot.nse_block_deals[0].client_name == "INSTITUTION A"
    assert snapshot.nse_bulk_deals[0].client_name == "INSTITUTION B"
    assert snapshot.nsdl_fpi_table_count == 3
    assert snapshot.market_context["cashGainers"] == 2
    assert snapshot.market_context["cashLosers"] == 1
    assert snapshot.market_context["nsdlFpiDailyTableCount"] == 2
    assert snapshot.market_context["nsdlFpiFortnightlyTableCount"] == 1
    assert snapshot.market_context["niftyIndexOptionRecordCount"] == 1
    assert snapshot.market_context["niftyIndexOptionVolume"] == 120000
    assert snapshot.market_context["bankNiftyIndexFutureOpenInterest"] == 250000


def test_intraday_snapshot_persists_for_future_analysis(tmp_path: Path) -> None:
    snapshot = build_intraday_stock_detail_snapshot(
        [_result("nse_oi_spurts_contracts", {"Rise-in-OI-Rise": [{"symbol": "TCS"}]})]
    )
    db_path = tmp_path / "research.sqlite3"

    save_intraday_stock_detail_snapshot(snapshot, db_path=db_path)

    assert db_path.exists()
