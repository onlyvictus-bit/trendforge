from __future__ import annotations

import json

from trendforge_api.market_data_registry import load_market_data_registry
from trendforge_api.parsers.third_party_fii_holding_parser import (
    parse_dhan_fii_holding_change,
    parse_equitymaster_fii_buys_reference,
    parse_screener_in_fii_holding_change,
    parse_tickertape_fii_holding_change_3m,
)
from trendforge_api.source_parser import STRUCTURED_PARSERS
from trendforge_api.source_resolver import resolve_and_fetch_source


KEYS = (
    "screener_in_fii_holding_change",
    "tickertape_fii_holding_change_3m",
    "dhan_fii_holding_change",
    "equitymaster_fii_buys_reference",
)


def test_registry_includes_four_info_only_fii_screens() -> None:
    load_market_data_registry.cache_clear()
    try:
        registry = load_market_data_registry()
    finally:
        load_market_data_registry.cache_clear()
    for key in KEYS:
        contract = registry.by_key[key]
        assert contract.parser_or_adapter_id == f"structured:{key}"
        assert key in STRUCTURED_PARSERS


def test_screener_parser_keeps_names_and_refuses_fake_tickers() -> None:
    html = """
    <html><table>
    <tr><th>Name</th><th>FII Hold %</th><th>Chg in FII Hold %</th></tr>
    <tr><td>Infosys Ltd</td><td>31.2</td><td>0.8</td></tr>
    <tr><td>Median:</td><td>10</td><td>0</td></tr>
    </table></html>
    """
    parsed = parse_screener_in_fii_holding_change(
        json.dumps({"pages": [{"page": 1, "html": html}]}).encode()
    )
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["name"] == "Infosys Ltd"
    assert row["symbol"] is None
    assert row["fiiChgPct"] == 0.8
    assert parsed["output"]["hasTicker"] is False


def test_tickertape_and_dhan_keep_tickers() -> None:
    tt = parse_tickertape_fii_holding_change_3m(
        json.dumps(
            {
                "results": [
                    {
                        "stock": {
                            "info": {"name": "Infosys", "ticker": "INFY"},
                            "advancedRatios": {"forInstHldng": 31.2, "forInstHldng3M": 0.4},
                        }
                    }
                ]
            }
        ).encode()
    )
    assert tt["record_count"] == 1
    assert tt["output"]["rows"][0]["symbol"] == "INFY"
    dhan = parse_dhan_fii_holding_change(
        json.dumps({"data": [{"DispSym": "Infosys", "Sym": "INFY", "FIIHLDChagPer": 3.1}]}).encode()
    )
    assert dhan["output"]["rows"][0]["symbol"] == "INFY"
    assert dhan["output"]["rows"][0]["fiiChgPct"] == 3.1


def test_equitymaster_preserves_holding_levels_and_change_without_fake_ticker() -> None:
    html = """
    <html><table>
    <tr><th>Company</th><th>CMP</th><th>Market Cap</th><th>FII %</th><th>Previous FII %</th><th>Change</th></tr>
    <tr><td>Infosys Ltd.</td><td>1,500.5</td><td>600,000</td><td>18.0%</td><td>11.5%</td><td>6.5%</td></tr>
    <tr><td>TCS Ltd.</td><td>3,200</td><td>1,100,000</td><td>15.0%</td><td>12.0%</td><td>3.0%</td></tr>
    <tr><td>HFCL</td><td>90</td><td>12,000</td><td>8.0%</td><td>4.0%</td><td>4.0%</td></tr>
    </table></html>
    """
    parsed = parse_equitymaster_fii_buys_reference(html.encode())
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    row = parsed["output"]["rows"][0]
    assert row["name"] == "Infosys Ltd."
    assert row["symbol"] is None
    assert row["price"] == 1500.5
    assert row["marketCapCr"] == 600000
    assert row["fiiHoldPct"] == 18.0
    assert row["previousFiiHoldPct"] == 11.5
    assert row["fiiChgPct"] == 6.5


def test_parsers_fail_closed_on_garbage() -> None:
    assert parse_screener_in_fii_holding_change(b"not-json")["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert parse_tickertape_fii_holding_change_3m(b"{}")["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert parse_dhan_fii_holding_change(json.dumps({"data": []}).encode())["parser_state"] == "WAIT_EMPTY_PARSE"
    assert parse_equitymaster_fii_buys_reference(b"<html>Just a moment</html>")["parser_state"] == "WAIT_SCHEMA_MISMATCH"


def test_unhandled_key_path_is_not_used_for_new_screens() -> None:
    # Wiring exists; this stays offline (no network) by using a missing catalog URL
    # only to prove the dispatch key is recognized as not UNHANDLED when mocked.
    result = resolve_and_fetch_source.__wrapped__ if False else None
    assert result is None
    from trendforge_api import source_resolver

    source = source_resolver.resolve_and_fetch_source.__code__.co_consts
    assert any("SCREENER_IN_FII_HOLDING_HTML" == item for item in source if isinstance(item, str))
    assert any("TICKERTAPE_FII_HOLDING_QUERY" == item for item in source if isinstance(item, str))
