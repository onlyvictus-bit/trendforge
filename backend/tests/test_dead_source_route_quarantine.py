from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

import yaml

from trendforge_api.source_registry_contracts import classify_registry_url


ROOT = Path(__file__).resolve().parents[2]
QUARANTINE_PATH = ROOT / "config" / "source_route_quarantine.yaml"
REGISTRY_PATH = ROOT / "config" / "source_refresh_registry_69.csv"
PROFILES_PATH = ROOT / "config" / "source_refresh_profiles.yaml"
DOWNLOADER_PATH = ROOT / "scripts" / "incoming_40pack" / "market_data_downloader.py"
CATALOG_PATH = next(
    (
        candidate
        for candidate in (
            # Hermetic first: the versioned in-repo snapshot travels with this repo.
            ROOT / "frontend" / "inventory-workbench" / "links_105.json",
            # Fallback: the live sibling app when present beside the checkout.
            ROOT.parent / "trendforge_inventory_app" / "links_105.json",
        )
        if candidate.exists()
    ),
    ROOT / "frontend" / "inventory-workbench" / "links_105.json",
)

EXPECTED_IDS = {
    "yahoo_badi",
    "pytrends",
    "stockedge_api",
    "bse_fiidii_legacy",
    "bse_participant_oi_legacy",
}
EXPECTED_REPLACEMENTS = {
    "tradingeconomics_bdi",
    "yahoo_bdry_shipping_proxy",
    "google_trends_india_rss",
    "bse_fii_dii",
    "bse_participant_oi",
}


def _quarantine_routes() -> list[dict[str, object]]:
    payload = yaml.safe_load(QUARANTINE_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    return payload["routes"]


def test_five_dead_routes_are_hints_not_runtime_contracts() -> None:
    routes = _quarantine_routes()
    assert {row["id"] for row in routes} == EXPECTED_IDS
    assert all(row["status"] == "NOT_IN_USE" for row in routes)
    assert all(row["reason"] and row["replacement_note"] for row in routes)

    with REGISTRY_PATH.open(encoding="utf-8-sig", newline="") as handle:
        registry = list(csv.DictReader(handle))
    active_keys = {row["source_key"] for row in registry}
    active_urls = {row["canonical_url"] for row in registry}
    assert EXPECTED_REPLACEMENTS <= active_keys
    assert not {str(row["route"]) for row in routes} & active_urls
    assert not EXPECTED_IDS & active_keys

    profile_rows = yaml.safe_load(PROFILES_PATH.read_text(encoding="utf-8"))["sources"]
    profile_keys = {row["source_key"] for row in profile_rows}
    assert EXPECTED_REPLACEMENTS <= profile_keys
    assert not EXPECTED_IDS & profile_keys


def test_legacy_bse_stubs_cannot_fetch_and_are_not_called_from_main() -> None:
    tree = ast.parse(DOWNLOADER_PATH.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    dead_functions = {"download_bse_participant_oi", "download_bse_fii_dii"}
    for name in dead_functions:
        calls = {
            node.func.id
            for node in ast.walk(functions[name])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        attributes = {
            node.func.attr
            for node in ast.walk(functions[name])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert not {"fetch", "_bse_session"} & calls
        assert not {"get", "request", "write_bytes", "write_text"} & attributes

    main_guard = next(
        node
        for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
    )
    main_calls = {
        node.func.id
        for node in ast.walk(main_guard)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not dead_functions & main_calls


def test_stockedge_is_classified_not_in_use() -> None:
    contract = classify_registry_url("https://stockedge.com/")
    assert contract.source_role == "NOT_IN_USE"
    assert contract.allowed_jobs == ["NOT_IN_USE"]
    assert contract.can_unlock_ready is False


def test_frontend_catalog_has_replacements_not_dead_active_links() -> None:
    rows = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    active_keys = {
        key.strip()
        for row in rows
        for key in str(row.get("active_source_keys") or "").split("|")
        if key.strip()
    }
    active_urls = {
        str(row.get(field) or "")
        for row in rows
        for field in ("canonical_url", "source_url", "url")
    }
    assert EXPECTED_REPLACEMENTS <= active_keys
    assert not EXPECTED_IDS & active_keys
    assert not {str(row["route"]) for row in _quarantine_routes()} & active_urls
