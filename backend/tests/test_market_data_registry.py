from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import httpx
import pytest
import yaml

from trendforge_api.market_data_registry import (
    PINNED_PRIMARY_KEY_SET_SHA256,
    PINNED_REGISTRY_SHA256,
    AcquisitionOwner,
    FetchGroupMode,
    ScheduleAuthority,
    StaleThresholdAuthority,
    load_market_data_registry,
)
from trendforge_api.institutional_sources import ENDPOINTS
from trendforge_api.source_monitor import SOURCE_CATALOG
from trendforge_api.source_parser import STRUCTURED_PARSERS


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "config"
REGISTRY_PATH = CONFIG_DIR / "source_refresh_registry_69.csv"
HASH_PATH = CONFIG_DIR / "source_refresh_registry_69.csv.sha256"
PROFILES_PATH = CONFIG_DIR / "source_refresh_profiles.yaml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _primary_key_hash(keys: set[str]) -> str:
    canonical = "\n".join(sorted(keys)).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _load_rows() -> list[dict[str, str]]:
    with REGISTRY_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_profiles() -> dict:
    loaded = yaml.safe_load(PROFILES_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_default_registry_compiles_exact_pinned_disabled_contracts() -> None:
    from trendforge_api.market_data_registry import EXPECTED_SOURCE_COUNT

    registry = load_market_data_registry()

    assert registry.registry_sha256 == PINNED_REGISTRY_SHA256
    assert len(registry.contracts) == EXPECTED_SOURCE_COUNT
    assert len(registry.by_key) == EXPECTED_SOURCE_COUNT
    assert EXPECTED_SOURCE_COUNT == 126  # + ESM, price-band and periodic-auction gates
    assert _primary_key_hash(set(registry.by_key)) == PINNED_PRIMARY_KEY_SET_SHA256
    assert all(
        contract.schedule_authority is ScheduleAuthority.PROVISIONAL
        for contract in registry.contracts
    )
    assert all(contract.activation_ready is False for contract in registry.contracts)
    assert all(
        contract.stale_threshold_seconds is None
        and contract.stale_threshold_authority is StaleThresholdAuthority.UNSET
        for contract in registry.contracts
    )


def test_registry_copy_and_hash_file_match_the_approved_original() -> None:
    assert _sha256(REGISTRY_PATH) == PINNED_REGISTRY_SHA256
    assert HASH_PATH.read_text(encoding="ascii").split()[0].upper() == PINNED_REGISTRY_SHA256
    # Historical 69-row audit CSV is an ancestor only. Phase-1 30-pack expansion
    # intentionally adds READY sources; byte identity with the 2026-08-04 audit
    # file is no longer required.


def test_registry_key_set_matches_primary_inventory_feed_set() -> None:
    registry = load_market_data_registry()
    sibling_inventory = (
        ROOT_DIR.parent / "trendforge_inventory_app" / "refresh_audit_primary_feeds.json"
    )
    if sibling_inventory.exists():
        payload = json.loads(sibling_inventory.read_text(encoding="utf-8"))
        inventory_keys = {str(item["source_key"]) for item in payload}
        # Registry may be a superset of the original 69 primary inventory feeds.
        assert inventory_keys.issubset(set(registry.by_key))
    assert _primary_key_hash(set(registry.by_key)) == PINNED_PRIMARY_KEY_SET_SHA256


def test_every_contract_has_executable_acquisition_and_normalization() -> None:
    registry = load_market_data_registry()

    assert registry.component_summary["acquisition_covered"] == 126
    assert registry.component_summary["normalization_covered"] == 126
    assert registry.component_summary["parameter_covered"] == 126
    assert registry.component_summary["component_verified"] == 126
    assert {
        contract.acquisition_owner for contract in registry.contracts
    } == {AcquisitionOwner.ASYNC_ENDPOINT_CLIENT, AcquisitionOwner.RESOLVER_MONITOR}

    monitor_keys = {item.key for item in SOURCE_CATALOG}
    for contract in registry.contracts:
        if contract.acquisition_owner is AcquisitionOwner.ASYNC_ENDPOINT_CLIENT:
            assert contract.endpoint_key in ENDPOINTS
        else:
            assert contract.source_key in monitor_keys
        if contract.parser_or_adapter_id.startswith("structured:"):
            parser_key = contract.parser_or_adapter_id.removeprefix("structured:")
            assert parser_key in STRUCTURED_PARSERS
            assert callable(STRUCTURED_PARSERS[parser_key])


def test_required_parameters_have_provider_or_fanout_strategy() -> None:
    registry = load_market_data_registry()

    for contract in registry.contracts:
        assert set(contract.required_parameters) <= set(contract.provided_parameters)
        if contract.required_parameters:
            assert contract.parameter_provider != "none"
        assert contract.fanout_strategy


def test_shared_downloads_are_not_confused_with_session_pools() -> None:
    registry = load_market_data_registry()

    for key in {"nse_bhavcopy_eod", "nse_trade_to_trade", "nse_pr_market_snapshot"}:
        assert registry.by_key[key].fetch_group_mode is FetchGroupMode.RESPONSE_REUSE
    for key in {
        "nse_variations_gainers",
        "nse_variations_loosers",
        "nse_live_equity_derivatives_stock_fut",
        "nse_live_equity_derivatives_stock_opt",
    }:
        assert registry.by_key[key].fetch_group_mode is FetchGroupMode.SESSION_SHARING
    assert (
        registry.by_key["nse_fo_bhavcopy"].fetch_group_mode
        is FetchGroupMode.SESSION_SHARING
    )


def test_compilation_performs_zero_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    from trendforge_api import source_monitor

    async def fail_request(*_args, **_kwargs):
        raise AssertionError("registry compilation attempted a network request")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("registry compilation attempted urllib network access")

    monkeypatch.setattr(httpx.AsyncClient, "request", fail_request)
    monkeypatch.setattr(source_monitor, "urlopen", fail_urlopen)
    load_market_data_registry.cache_clear()
    try:
        registry = load_market_data_registry()
        assert len(registry.contracts) == 126
    finally:
        load_market_data_registry.cache_clear()


def test_human_schedule_text_is_not_silently_guessed() -> None:
    registry = load_market_data_registry()

    assert registry.by_key["nse_all_indices"].exact_interval_seconds == 120
    assert registry.by_key["bse_bulk_deals"].exact_interval_seconds == 300
    assert registry.by_key["nse_bhavcopy_eod"].exact_interval_seconds is None
    assert registry.by_key["wgc_gold_etf_holdings"].exact_interval_seconds is None
    assert registry.activation_ready is False


def test_duplicate_csv_key_is_rejected(tmp_path: Path) -> None:
    rows = _load_rows()
    rows.append(dict(rows[0]))
    csv_path = tmp_path / "registry.csv"
    _write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="duplicate source_key"):
        load_market_data_registry(
            registry_path=csv_path,
            profiles_path=PROFILES_PATH,
            expected_sha256=_sha256(csv_path),
        )


def test_missing_profile_is_rejected(tmp_path: Path) -> None:
    profiles = _load_profiles()
    profiles["sources"] = profiles["sources"][:-1]
    profiles_path = tmp_path / "profiles.yaml"
    profiles_path.write_text(yaml.safe_dump(profiles, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="profile key set"):
        load_market_data_registry(profiles_path=profiles_path)


def test_unknown_endpoint_is_rejected(tmp_path: Path) -> None:
    profiles = _load_profiles()
    target = next(
        item for item in profiles["sources"] if item["source_key"] == "nse_all_indices"
    )
    target["endpoint_key"] = "missing_endpoint"
    profiles_path = tmp_path / "profiles.yaml"
    profiles_path.write_text(yaml.safe_dump(profiles, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="missing_endpoint"):
        load_market_data_registry(profiles_path=profiles_path)


def test_missing_parameter_provider_is_rejected(tmp_path: Path) -> None:
    profiles = _load_profiles()
    target = next(
        item
        for item in profiles["sources"]
        if item["source_key"] == "nse_option_chain_equity"
    )
    target["parameter_provider"] = "none"
    profiles_path = tmp_path / "profiles.yaml"
    profiles_path.write_text(yaml.safe_dump(profiles, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="required parameters"):
        load_market_data_registry(profiles_path=profiles_path)


def test_activation_cannot_be_enabled_for_provisional_schedule(tmp_path: Path) -> None:
    profiles = _load_profiles()
    profiles["activation_ready"] = True
    profiles_path = tmp_path / "profiles.yaml"
    profiles_path.write_text(yaml.safe_dump(profiles, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="provisional schedules cannot be activation-ready"):
        load_market_data_registry(profiles_path=profiles_path)
