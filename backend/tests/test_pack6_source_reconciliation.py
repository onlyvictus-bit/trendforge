from __future__ import annotations

import json
from pathlib import Path

from trendforge_api.market_data_registry import load_market_data_registry
from trendforge_api.source_parser import STRUCTURED_PARSERS


EVIDENCE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "fable"
    / "evidence"
    / "pack6-20260811"
    / "PACK6_SOURCE_RECONCILIATION.json"
)


def test_pack6_every_candidate_has_one_terminal_classification() -> None:
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    candidates = payload["candidates"]
    allowed = {
        "ADDED_NEW",
        "ENHANCED_EXISTING",
        "REPAIRED_EXISTING",
        "REUSED_EXACT_OUTPUT",
        "BLOCKED",
        "REJECTED",
    }

    assert payload["candidateCount"] == 10 == len(candidates)
    assert all(item["classification"] in allowed for item in candidates)
    assert all(item["reason"].strip() for item in candidates)


def test_pack6_reused_and_enhanced_keys_exist_in_production_registry() -> None:
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    registry = load_market_data_registry()
    expected = {
        key
        for item in payload["candidates"]
        if item["classification"] in {"ENHANCED_EXISTING", "REUSED_EXACT_OUTPUT"}
        for key in item["productionKeys"]
    }

    assert expected <= set(registry.by_key)
    assert payload["productionSourceCountBefore"] == 112
    assert payload["productionSourceCountAfter"] == 112


def test_pack6_option_chain_paths_use_existing_structured_parsers() -> None:
    resolver_keys = {
        "nse_option_chain_nifty",
        "nse_option_chain_banknifty",
        "nse_index_option_chain_v3",
    }
    registry = load_market_data_registry()

    assert resolver_keys <= set(STRUCTURED_PARSERS)
    assert (
        registry.by_key["nse_option_chain_equity"].parser_or_adapter_id
        == "structured:nse_option_chain"
    )
    assert "nse_option_chain" in STRUCTURED_PARSERS


def test_pack6_does_not_register_scrapers_or_mock_ingestion_planes() -> None:
    keys = set(load_market_data_registry().by_key)

    assert "screener_in_company_pages" not in keys
    assert "trendlyne_browser_export" not in keys
    assert "generated_unified_scanner_parser" not in keys
    assert "dhan_option_chain" not in keys
