"""Unit tests for the 15 failed registry sources repaired 2026-08-06.

Covers future effective-date clamp, option-chain date hygiene, WASDE text,
DGCIS form field names, MCX/NCDEX yahoo proxy parse, NSE bulk/trade_info
fallbacks, and CDSL/NSDL directory parse.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timezone

import pytest

from trendforge_api.market_data_registry import load_market_data_registry
from trendforge_api.market_data_service import (
    MarketDataService,
    ParameterContext,
    ParsedSourcePayload,
    RawAcquisition,
)
from trendforge_api.market_data_store import ManifestStatus
from trendforge_api.parsers.finish_30_parsers import (
    parse_mcx_json_watch,
    parse_nse_bulk_deal_symbol_json,
    parse_nse_trade_info,
)
from trendforge_api.parsers.nse_mwpl_parser import parse_nse_fno_ban
from trendforge_api.parsers.phase2_screener_parsers import (
    parse_eia_natgas_storage,
    parse_nse_index_option_chain,
    parse_usda_wasde_index,
)
from trendforge_api.parsers.surveillance_pledge_fpi_parser import (
    parse_cdsl_fpi_fortnightly_sector,
)
from trendforge_api.phase3_multi_step_fetch import (
    fetch_dgcis_imports,
    fetch_eia_natgas_storage,
)


NOW = datetime(2026, 8, 6, 4, 0, tzinfo=timezone.utc)


def _context(**changes):
    values = {
        "trading_date": date(2026, 8, 6),
        "market_session": "OPEN",
        "symbols": ("RELIANCE",),
        "scrip_codes": {"RELIANCE": "500325"},
        "sector_indices": ("NIFTY 50",),
        "option_expiries": {"RELIANCE": "25-Aug-2026"},
    }
    values.update(changes)
    return ParameterContext(**values)


def test_fno_ban_future_effective_date_is_clamped_not_failed() -> None:
    """Ban list 'for trade date' can be next session; still publish rows."""
    registry = load_market_data_registry()
    contract = registry.by_key["nse_fno_ban"]
    body = b"Securities in Ban For Trade Date 07-AUG-2026:\n1,BANDHANBNK\n2,LICI\n"
    # Use real normalizer path via structured parse
    from trendforge_api.market_data_service import default_normalizer

    acq = (
        RawAcquisition.success(
            source_url="https://nsearchives.nseindia.com/content/fo/fo_secban.csv",
            status_code=200,
            media_type="text/csv",
            content=body,
            payload={},
            fetched_at=NOW,
        ),
    )
    parsed = default_normalizer(contract, acq, _context())
    assert parsed.records
    assert parsed.data_date == date(2026, 8, 7)  # parser keeps ban-for date

    class _T:
        async def fetch_endpoint(self, *a, **k):
            raise AssertionError("endpoint not used")

        async def fetch_resolver(self, source_key, catalog_url, trading_date=None):
            return acq[0]

    result = asyncio.run(
        MarketDataService(transport=_T()).run_source(contract, context=_context())
    )
    assert result.status is ManifestStatus.SUCCESS_NEW
    assert result.data_date == date(2026, 8, 6)  # clamped to trading_date
    assert result.normalized_row_count >= 1


def test_option_chain_ignores_expiry_in_url_as_data_date() -> None:
    payload = {
        "records": {
            "expiryDates": ["11-Aug-2026", "18-Aug-2026"],
            "underlyingValue": 24500,
            "timestamp": "06-Aug-2026 15:30:00",
            "data": [],
        },
        "filtered": {
            "data": [
                {
                    "strikePrice": 24500,
                    "CE": {"openInterest": 100, "underlying": "NIFTY", "timestamp": "06-Aug-2026 15:30:00"},
                    "PE": {"openInterest": 90, "underlying": "NIFTY"},
                }
            ]
        },
    }
    parsed = parse_nse_index_option_chain(
        json.dumps(payload).encode(),
        url="https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol=NIFTY&expiry=11-Aug-2026",
    )
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] >= 1
    # Must not stamp data_date as the expiry in the URL
    assert parsed["data_date"] != "2026-08-11"
    if parsed["data_date"]:
        assert parsed["data_date"] <= "2026-08-06" or parsed["data_date"] == "2026-08-06"


def test_wasde_plain_text_body_parses() -> None:
    text = (
        "                                WASDE - 673 - 8                        July 2026\n"
        "                  World and U.S. Supply and Use for Grains  1/\n"
        "================================================================================\n"
        "Wheat                                       100.5      101.2       50.0\n"
        "Corn                                        200.1      198.4       40.2\n"
    )
    parsed = parse_usda_wasde_index(text.encode("utf-8"), url="https://usda.example/wasde0726.txt")
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] >= 1


def test_mcx_parser_accepts_yahoo_proxy_batch() -> None:
    body = {
        "records": [
            {"symbol": "GC=F", "close": 2400.5, "volume": 10},
            {"symbol": "SI=F", "close": 28.1, "volume": 5},
        ],
        "rows": [
            {"symbol": "GC=F", "close": 2400.5},
            {"symbol": "SI=F", "close": 28.1},
        ],
    }
    parsed = parse_mcx_json_watch(json.dumps(body).encode())
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 2
    assert parsed["output"].get("proxySource") == "yahoo_when_mcx_blocked"


def test_bulk_deal_symbol_parser_accepts_largedeal_shape() -> None:
    body = {
        "as_on_date": "05-Aug-2026",
        "BULK_DEALS_DATA": [
            {"symbol": "RELIANCE", "buySell": "BUY", "qty": 1000},
            {"symbol": "TCS", "buySell": "SELL", "qty": 500},
        ],
    }
    parsed = parse_nse_bulk_deal_symbol_json(json.dumps(body).encode())
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] >= 1


def test_trade_info_parser_accepts_bhav_delivery_proxy() -> None:
    body = {
        "symbol": "RELIANCE",
        "securityWiseDP": {
            "SYMBOL": "RELIANCE",
            "DELIV_QTY": "100000",
            "DELIV_PER": "45.5",
            "DATE1": "06-Aug-2026",
        },
        "proxySource": "sec_bhavdata_full",
        "data": [{"symbol": "RELIANCE", "DELIV_PER": "45.5"}],
    }
    parsed = parse_nse_trade_info(
        json.dumps(body).encode(),
        url="https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_06082026.csv",
    )
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] >= 1


def test_cdsl_parser_accepts_nsdl_directory_links() -> None:
    html = b"""
    <html><body>
    <a href="/Reports/FPI_Fortnightly_Sector.pdf">FPI Fortnightly Sector Report</a>
    <a href="/other">Ignore me</a>
    </body></html>
    """
    parsed = parse_cdsl_fpi_fortnightly_sector(html)
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] >= 1


def test_far_future_non_allowlist_still_quarantined() -> None:
    registry = load_market_data_registry()
    contract = registry.by_key["nse_oi_spurts"]

    class _T:
        async def fetch_endpoint(self, endpoint_key, parameters):
            return RawAcquisition.success(
                source_url="https://example/x",
                status_code=200,
                media_type="application/json",
                content=b'{"data":[{"symbol":"X"}]}',
                payload={"data": [{"symbol": "X"}]},
                fetched_at=NOW,
            )

        async def fetch_resolver(self, source_key, catalog_url):
            raise AssertionError("resolver not used")

    service = MarketDataService(
        transport=_T(),
        normalizer=lambda *_: ParsedSourcePayload(
            parser_state="PARSED_STRUCTURED",
            records=({"symbol": "POISON"},),
            data_date=date(2026, 12, 1),
        ),
    )
    result = asyncio.run(service.run_source(contract, context=_context()))
    assert result.status is ManifestStatus.FAILED


def test_dgcis_import_form_fields_live_smoke() -> None:
    """Optional live smoke — skip if network/site unavailable.

    Year must be a form option (e.g. 2025 for FY 2025-26), not raw calendar year.
    """
    try:
        # Default path picks latest year from the form when year is omitted/invalid
        result = fetch_dgcis_imports(hs_level="2")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"network unavailable: {exc}")
    if not result.ok:
        pytest.skip(f"DGCIS unavailable: {result.error}")
    assert result.status_code < 400
    assert b"HSCode" in result.content or b"Commodity" in result.content
    assert len(result.content) > 5000


def test_fno_ban_parser_still_extracts_symbols() -> None:
    parsed = parse_nse_fno_ban(
        b"Securities in Ban For Trade Date 07-AUG-2026:\n1,BANDHANBNK\n2,LICI\n"
    )
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert "BANDHANBNK" in parsed["output"]["symbols"]


def test_eia_natgas_storage_live_or_xls_path() -> None:
    """ir.eia.gov CSV is often 403; multi-step must land on dnav XLS and parse."""
    try:
        fetched = fetch_eia_natgas_storage()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"network unavailable: {exc}")
    if not fetched.ok:
        pytest.skip(f"EIA storage unavailable: {fetched.error}")
    parsed = parse_eia_natgas_storage(fetched.content, url=fetched.url)
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] >= 1
    assert any(
        "East" in str(r.get("region") or "") or "Lower" in str(r.get("region") or "")
        for r in parsed["output"]["rows"]
    )
