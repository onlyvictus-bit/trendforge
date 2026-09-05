from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trendforge_api.market_data_registry import load_market_data_registry
from trendforge_api.parsers.supplemental_market_parser import parse_nse_option_chain


EVIDENCE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "fable"
    / "evidence"
    / "pack7-20260811"
    / "PACK7_SOURCE_RECONCILIATION.json"
)


def _evidence() -> dict:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def test_pack7_every_candidate_has_one_terminal_classification() -> None:
    payload = _evidence()
    candidates = payload["candidates"]
    allowed = {
        "ADDED_NEW",
        "ENHANCED_EXISTING",
        "REPAIRED_EXISTING",
        "REUSED_EXACT_OUTPUT",
        "BLOCKED",
        "REJECTED",
    }

    assert payload["candidateCount"] == 17 == len(candidates)
    assert all(item["classification"] in allowed for item in candidates)
    assert all(item["reason"].strip() for item in candidates)
    assert Counter(item["classification"] for item in candidates) == {
        "REUSED_EXACT_OUTPUT": 4,
        "BLOCKED": 10,
        "REJECTED": 3,
    }


def test_pack7_reused_keys_exist_and_registry_count_does_not_drift() -> None:
    payload = _evidence()
    registry = load_market_data_registry()
    reused = {
        key
        for item in payload["candidates"]
        if item["classification"] == "REUSED_EXACT_OUTPUT"
        for key in item["productionKeys"]
    }

    assert reused <= set(registry.by_key)
    assert len(registry.contracts) == 126
    assert payload["productionSourceCountBefore"] == 112
    assert payload["productionSourceCountAfter"] == 112


def test_pack7_does_not_add_broker_or_scraper_production_paths() -> None:
    keys = set(load_market_data_registry().by_key)
    forbidden = {
        "dhan_option_chain",
        "fyers_option_chain",
        "zerodha_kite_option_chain",
        "upstox_option_chain",
        "sensibull_option_analytics",
        "opstra_option_analytics",
        "screener_in_company_pages",
        "trendlyne_browser_export",
    }

    assert keys.isdisjoint(forbidden)


def test_existing_option_parser_computes_max_pain_without_inventing_greeks() -> None:
    content = json.dumps(
        {
            "records": {
                "timestamp": "10-Aug-2026 15:40:00",
                "underlyingValue": 100.0,
                "data": [
                    {
                        "expiryDate": "25-Aug-2026",
                        "strikePrice": 90,
                        "CE": {"underlying": "TEST", "openInterest": 10},
                        "PE": {"underlying": "TEST", "openInterest": 30},
                    },
                    {
                        "expiryDate": "25-Aug-2026",
                        "strikePrice": 110,
                        "CE": {"underlying": "TEST", "openInterest": 40},
                        "PE": {"underlying": "TEST", "openInterest": 5},
                    },
                ],
            }
        }
    ).encode()

    parsed = parse_nse_option_chain(content)
    rows = parsed["output"]["rows"]

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["output"]["metrics"]["maxPainStrike"] in {90.0, 110.0}
    assert all("delta" not in row and "gamma" not in row for row in rows)
