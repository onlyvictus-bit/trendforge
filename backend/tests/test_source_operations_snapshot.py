from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from trendforge_api import main
from trendforge_api.source_operations import _classify


def test_http_200_without_parser_or_freshness_is_not_healthy() -> None:
    now = datetime.now(UTC)
    observed = _classify(
        {"staleAfterHours": 72, "expectedFrequency": "daily"},
        None,
        None,
        {
            "result_state": "DATA_CANDIDATE",
            "status_code": 200,
            "attempted_at": (now - timedelta(minutes=5)).isoformat(),
        },
        now=now,
    )

    assert observed["state"] == "STALE_PARTIAL"


def test_last_good_matches_normalized_catalog_alias() -> None:
    from trendforge_api.source_operations import last_good_match

    families = {
        "nse_block_deal_live": frozenset({"nse_block_deal_live", "nse_block_deal"}),
        "nse_block_deal": frozenset({"nse_block_deal_live", "nse_block_deal"}),
    }
    last_good = {"nse_block_deal"}

    hit, via, matched = last_good_match("nse_block_deal_live", last_good, families)
    assert hit is True
    assert via == "alias"
    assert matched == "nse_block_deal"

    exact, exact_via, exact_key = last_good_match("nse_block_deal", last_good, families)
    assert exact is True
    assert exact_via == "exact"
    assert exact_key == "nse_block_deal"

    missing, missing_via, missing_key = last_good_match(
        "nselib", last_good, families
    )
    assert missing is False
    assert missing_via is None
    assert missing_key is None

    wgc_families = {
        "wgc_gold_etf_flows": frozenset(
            {"wgc_gold_etf_flows", "wgc_gold_etf_holdings"}
        )
    }
    wgc_hit, wgc_via, wgc_key = last_good_match(
        "wgc_gold_etf_flows", {"wgc_gold_etf_holdings"}, wgc_families
    )
    assert wgc_hit is True
    assert wgc_via == "alias"
    assert wgc_key == "wgc_gold_etf_holdings"


def test_source_operations_endpoint_exposes_two_tracks_without_activation() -> None:
    payload = {
        "contract": "trendforge.sourceOperations.v1",
        "sourceTrack": {"runtimeCatalogKeys": 132, "rows": []},
        "cashTrack": {"latestRun": {"state": "FAILED_STAGE"}},
        "permissions": {
            "sourceActivationReady": False,
            "canUnlockConfirmed": False,
            "executable": False,
        },
    }
    with patch.object(main, "build_source_operations_snapshot", return_value=payload):
        response = TestClient(main.app).get("/api/source-operations/snapshot")

    assert response.status_code == 200
    assert response.json() == payload
