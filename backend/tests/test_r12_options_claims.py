"""R12 OPTIONS_CONTEXT claims from options data — law tests."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from trendforge_api.selection.r12_options_claims import mint_options_claims

NOW = datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc)
SB = "sb-1"


def _pkg(status="SUPPORT", **extra):
    defaults = dict(pcr_oi=1.2, max_pain=2450.0, gex_signed={"status": "SCENARIO_ONLY"})
    defaults.update(extra)
    return SimpleNamespace(status=status, **defaults)


def test_unknown_package_returns_empty() -> None:
    assert mint_options_claims(symbol="X", options_package=None, snapshot_bundle_id=SB, decision_at=NOW) == []


def test_unknown_status_returns_empty() -> None:
    pkg = _pkg(status="UNKNOWN_NEEDS_R12")
    claims = mint_options_claims(symbol="X", options_package=pkg, snapshot_bundle_id=SB, decision_at=NOW)
    assert claims == []


def test_support_package_mints_multiple_claims() -> None:
    pkg = _pkg()
    claims = mint_options_claims(symbol="X", options_package=pkg, snapshot_bundle_id=SB, decision_at=NOW)
    assert len(claims) >= 2
    assert all(not c.can_support_confirmed for c in claims)


def test_all_share_one_correlation_group() -> None:
    pkg = _pkg()
    claims = mint_options_claims(symbol="X", options_package=pkg, snapshot_bundle_id=SB, decision_at=NOW)
    groups = {c.correlation_group for c in claims}
    assert len(groups) <= 1


def test_gex_scenario_label() -> None:
    pkg = _pkg(gex_signed={"status": "LONG"})
    claims = mint_options_claims(symbol="X", options_package=pkg, snapshot_bundle_id=SB, decision_at=NOW)
    gex = [c for c in claims if "GEX" in c.feature_id]
    if gex:
        assert any("SCENARIO_ONLY" in c.explanation for c in gex)


def test_no_place_order_in_module() -> None:
    import trendforge_api.selection.r12_options_claims as m
    src = open(m.__file__, encoding="utf-8").read().lower()
    assert "place_order" not in src
    assert "placeorder" not in src
