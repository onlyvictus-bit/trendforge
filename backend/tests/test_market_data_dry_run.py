from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import requests

from trendforge_api.market_data_dry_run import run_no_network_dry_run
from trendforge_api.market_data_registry import EXPECTED_SOURCE_COUNT


def test_no_network_dry_run_writes_complete_manifest_and_status(
    tmp_path: Path, monkeypatch
) -> None:
    def network_forbidden(*_args, **_kwargs):
        raise AssertionError("network access is forbidden in MD69 M6 dry run")

    monkeypatch.setattr(requests.sessions.Session, "request", network_forbidden)
    monkeypatch.setattr(httpx.AsyncClient, "request", network_forbidden)

    report = asyncio.run(run_no_network_dry_run(tmp_path / "evidence"))

    assert report["networkMode"] == "FIXTURE_ONLY_NO_NETWORK"
    assert report["productionActivation"] is False
    assert report["registrySourceCount"] == EXPECTED_SOURCE_COUNT
    assert report["scheduleAuthority"] == "PROVISIONAL"
    assert report["activationReady"] is False
    assert report["run"]["state"] == "COMPLETED"
    assert 0 < report["run"]["due_count"] < EXPECTED_SOURCE_COUNT
    assert report["run"]["completed_count"] == report["run"]["due_count"]
    assert report["transport"]["totalCalls"] > 0

    manifest_path = Path(report["run"]["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["entries"]) == EXPECTED_SOURCE_COUNT
    assert (
        len({entry["sourceKey"] for entry in manifest["entries"]})
        == EXPECTED_SOURCE_COUNT
    )
    assert len(report["status"]["health"]) == EXPECTED_SOURCE_COUNT
    assert Path(report["reportPath"]).is_file()


def test_dry_run_is_deterministic_and_suppresses_same_slot_refetch(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evidence"
    first = asyncio.run(run_no_network_dry_run(root))
    first_objects = tuple((root / "market_data" / "objects").rglob("*.json"))
    second = asyncio.run(run_no_network_dry_run(root))
    second_objects = tuple((root / "market_data" / "objects").rglob("*.json"))

    assert first["run"]["run_id"] == second["run"]["run_id"]
    manifest = json.loads(
        Path(second["run"]["manifest_path"]).read_text(encoding="utf-8")
    )
    statuses = {entry["status"] for entry in manifest["entries"]}
    assert "CACHED_CURRENT" in statuses
    # Some finish-pack / session sources re-check and land SUCCESS_UNCHANGED
    # instead of CACHED_CURRENT; still no new failures and no object growth.
    assert not (statuses & {"FAILED", "ERROR", "SCHEMA_MISMATCH"})
    assert second["run"]["due_count"] <= first["run"]["due_count"]
    assert len(second_objects) == len(first_objects)
    assert second["status"]["sourceCount"] == EXPECTED_SOURCE_COUNT
