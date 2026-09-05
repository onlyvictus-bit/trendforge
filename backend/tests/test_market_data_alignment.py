from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from trendforge_api.live_panels import (
    CLOSED_RESEARCH_SOURCE_KEYS,
    LivePanelsService,
    P0_SOURCE_KEYS,
)
from trendforge_api.market_data_alignment import (
    AlignmentState,
    CanonicalManifestSourceProvider,
    DerivedInput,
    build_derived_bundle,
)
from trendforge_api.market_data_store import (
    MANIFEST_SCHEMA_VERSION,
    ManifestEntry,
    MarketDataStore,
    SnapshotManifest,
)


NOW = datetime(2026, 8, 5, 4, 0, tzinfo=UTC)  # 09:30 IST
TRADING_DATE = date(2026, 8, 5)


def _input(key: str, *, seconds: int = 0, day: date = TRADING_DATE) -> DerivedInput:
    return DerivedInput(
        source_key=key,
        content_hash=hashlib.sha256(key.encode()).hexdigest(),
        data_as_of=NOW + timedelta(seconds=seconds),
        fetched_at=NOW + timedelta(seconds=seconds),
        trading_date=day,
        records=({"symbol": "ALPHA"},),
    )


def test_derived_bundle_records_hashes_times_and_skew() -> None:
    bundle = build_derived_bundle(
        {
            "spot": _input("spot"),
            "futures": _input("futures", seconds=20),
            "options": _input("options", seconds=40),
        },
        required_keys=("spot", "futures", "options"),
        trading_date=TRADING_DATE,
        evaluated_at=NOW + timedelta(seconds=45),
        max_skew_seconds=60,
    )

    assert bundle.state is AlignmentState.VALID
    assert bundle.maximum_skew_seconds == 40
    assert {item.source_key for item in bundle.inputs} == {"spot", "futures", "options"}
    assert all(item.content_hash for item in bundle.inputs)


def test_derived_bundle_fails_closed_for_missing_wrong_day_future_and_skew() -> None:
    missing = build_derived_bundle(
        {"spot": _input("spot")},
        required_keys=("spot", "futures"),
        trading_date=TRADING_DATE,
        evaluated_at=NOW,
        max_skew_seconds=60,
    )
    wrong_day = build_derived_bundle(
        {"spot": _input("spot", day=TRADING_DATE - timedelta(days=1))},
        required_keys=("spot",),
        trading_date=TRADING_DATE,
        evaluated_at=NOW,
        max_skew_seconds=60,
    )
    future = build_derived_bundle(
        {"spot": _input("spot", seconds=121)},
        required_keys=("spot",),
        trading_date=TRADING_DATE,
        evaluated_at=NOW,
        max_skew_seconds=60,
    )
    skew = build_derived_bundle(
        {"spot": _input("spot"), "options": _input("options", seconds=61)},
        required_keys=("spot", "options"),
        trading_date=TRADING_DATE,
        evaluated_at=NOW + timedelta(seconds=65),
        max_skew_seconds=60,
    )

    assert missing.state is AlignmentState.WAIT_MISSING_INPUT
    assert wrong_day.state is AlignmentState.WAIT_TRADING_DATE
    assert future.state is AlignmentState.WAIT_FUTURE_INPUT
    assert skew.state is AlignmentState.WAIT_TIMESTAMP_SKEW


def _canonical_fixture(
    tmp_path: Path,
    *,
    extra_records: dict[str, list[dict]] | None = None,
) -> CanonicalManifestSourceProvider:
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    entries: list[ManifestEntry] = []
    source_records = {
        key: [{"symbol": "ALPHA", "source": key}]
        for key in P0_SOURCE_KEYS
    }
    source_records.update(extra_records or {})
    for key, records in source_records.items():
        payload = {
            "sourceKey": key,
            "normalizedSourceKey": key,
            "parserState": "PARSED_STRUCTURED",
            "dataDate": TRADING_DATE.isoformat(),
            "records": records,
            "payload": {},
            "rawContentHashes": [hashlib.sha256(f"raw-{key}".encode()).hexdigest()],
        }
        attempt = store.commit_success(
            run_id="canonical-0917",
            source_key=key,
            trading_date=TRADING_DATE,
            slot="0917",
            attempted_at=NOW,
            fetched_at=NOW,
            data_date=TRADING_DATE,
            source_url=f"https://example.test/{key}",
            http_status=200,
            media_type="application/vnd.trendforge.normalized+json",
            content=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
            extension="json",
            normalized_row_count=len(records),
            retry_count=0,
        )
        entries.append(
            ManifestEntry(
                source_key=key,
                status=attempt.status,
                attempted_at=NOW,
                source_url=attempt.source_url,
                http_status=200,
                media_type=attempt.media_type,
                content_hash=attempt.content_hash,
                object_path=attempt.object_path,
                data_date=TRADING_DATE,
                fetched_at=NOW,
                normalized_row_count=len(records),
                retry_count=0,
            )
        )
    store.write_manifest(
        SnapshotManifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            run_id="canonical-0917",
            registry_sha256="4" * 64,
            trading_date=TRADING_DATE,
            slot="0917",
            generated_at=NOW,
            entries=tuple(entries),
        )
    )
    return CanonicalManifestSourceProvider(
        db_path=store.db_path,
        data_root=store.root,
    )


def _closed_research_fixture(tmp_path: Path) -> CanonicalManifestSourceProvider:
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    key = "nse_bhavcopy_eod"
    records = [
        {
            "tradeDate": TRADING_DATE.isoformat(),
            "symbol": "TODAY",
            "series": "EQ",
            "close": 123.45,
            "previousClose": 120.0,
            "volume": 1000,
        }
    ]
    payload = {
        "sourceKey": key,
        "normalizedSourceKey": key,
        "parserState": "PARSED_STRUCTURED",
        "dataDate": TRADING_DATE.isoformat(),
        "records": records,
        "payload": {},
        "rawContentHashes": [hashlib.sha256(b"raw-eod").hexdigest()],
    }
    attempt = store.commit_success(
        run_id="canonical-eod",
        source_key=key,
        trading_date=TRADING_DATE,
        slot="eod-1600",
        attempted_at=NOW,
        fetched_at=NOW,
        data_date=TRADING_DATE,
        source_url="https://example.test/nse-bhavcopy",
        http_status=200,
        media_type="application/vnd.trendforge.normalized+json",
        content=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
        extension="json",
        normalized_row_count=len(records),
        retry_count=0,
    )
    store.write_manifest(
        SnapshotManifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            run_id="canonical-eod",
            registry_sha256="4" * 64,
            trading_date=TRADING_DATE,
            slot="eod-1600",
            generated_at=NOW,
            entries=(
                ManifestEntry(
                    source_key=key,
                    status=attempt.status,
                    attempted_at=NOW,
                    source_url=attempt.source_url,
                    http_status=200,
                    media_type=attempt.media_type,
                    content_hash=attempt.content_hash,
                    object_path=attempt.object_path,
                    data_date=TRADING_DATE,
                    fetched_at=NOW,
                    normalized_row_count=len(records),
                    retry_count=0,
                ),
            ),
        )
    )
    return CanonicalManifestSourceProvider(db_path=store.db_path, data_root=store.root)


def test_canonical_provider_reads_current_manifest_without_mutating_objects(tmp_path: Path) -> None:
    provider = _canonical_fixture(tmp_path)
    before = {
        path: path.read_bytes()
        for path in (tmp_path / "market_data" / "objects").rglob("*")
        if path.is_file()
    }

    sources = provider(
        now=NOW + timedelta(seconds=60),
        market_trading_date=TRADING_DATE.isoformat(),
        max_age_sec=300,
        source_keys=P0_SOURCE_KEYS,
    )

    assert set(sources) == set(P0_SOURCE_KEYS)
    assert all(item["eligible"] for item in sources.values())
    assert all(item["recordsSample"] for item in sources.values())
    assert {path: path.read_bytes() for path in before} == before


def test_newer_missed_scheduler_manifest_does_not_mask_last_good_snapshot(
    tmp_path: Path,
) -> None:
    provider = _canonical_fixture(tmp_path)
    store = MarketDataStore(root=provider.data_root, db_path=provider.db_path)
    store.write_manifest(
        SnapshotManifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            run_id="missed-1330",
            registry_sha256="4" * 64,
            trading_date=TRADING_DATE,
            slot="1330-missed-143700",
            generated_at=NOW + timedelta(minutes=1),
            entries=(),
        )
    )

    sources = provider(
        now=NOW + timedelta(minutes=2),
        market_trading_date=TRADING_DATE.isoformat(),
        max_age_sec=300,
        source_keys=P0_SOURCE_KEYS,
    )

    assert set(sources) == set(P0_SOURCE_KEYS)
    assert all(item["recordsSample"] for item in sources.values())


def test_wrong_day_canonical_manifest_never_becomes_live(tmp_path: Path) -> None:
    provider = _canonical_fixture(tmp_path)
    sources = provider(
        now=NOW,
        market_trading_date="2026-08-06",
        max_age_sec=300,
        source_keys=P0_SOURCE_KEYS,
    )
    assert sources == {}


def test_tampered_manifest_hash_is_rejected(tmp_path: Path) -> None:
    provider = _canonical_fixture(tmp_path)
    manifest = next((tmp_path / "market_data" / "2026-08-05").rglob("manifest.json"))
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["tampered"] = True
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    sources = provider(
        now=NOW,
        market_trading_date=TRADING_DATE.isoformat(),
        max_age_sec=300,
        source_keys=P0_SOURCE_KEYS,
    )

    assert sources == {}


def test_live_panels_use_canonical_provider_and_never_construct_fetch_client(
    tmp_path: Path,
) -> None:
    provider = _canonical_fixture(tmp_path)
    client_calls = 0

    def forbidden_client():
        nonlocal client_calls
        client_calls += 1
        raise AssertionError("legacy fetch plane must not be constructed")

    service = LivePanelsService(
        db_path=tmp_path / "panel.db",
        client_factory=forbidden_client,
        canonical_source_provider=provider,
        enabled=True,
        calendar_evaluator=lambda _at: {
            "state": "OPEN_NORMAL",
            "isTradingDay": True,
            "tradingDate": TRADING_DATE.isoformat(),
            "reason": "fixture",
        },
    )

    snapshot = asyncio.run(
        service.get_snapshot(refresh=True, force=True, now=NOW + timedelta(seconds=60))
    )

    assert client_calls == 0
    assert snapshot["refresh"]["state"] == "CANONICAL_MANIFEST"
    assert snapshot["inventoryOverlay"]
    assert {panel["state"] for panel in snapshot["panels"].values()} == {"LIVE"}


def test_disabled_live_fetch_still_projects_verified_saved_manifest(
    tmp_path: Path,
) -> None:
    provider = _canonical_fixture(tmp_path)
    client_calls = 0

    def forbidden_client():
        nonlocal client_calls
        client_calls += 1
        raise AssertionError("saved-manifest display must not construct a fetch client")

    service = LivePanelsService(
        db_path=tmp_path / "panel.db",
        client_factory=forbidden_client,
        canonical_source_provider=provider,
        enabled=False,
        calendar_evaluator=lambda _at: {
            "state": "OPEN_NORMAL",
            "isTradingDay": True,
            "tradingDate": TRADING_DATE.isoformat(),
            "reason": "fixture",
        },
    )

    snapshot = asyncio.run(
        service.get_snapshot(refresh=True, force=True, now=NOW + timedelta(seconds=60))
    )

    assert client_calls == 0
    assert snapshot["refresh"]["state"] == "CANONICAL_MANIFEST"
    assert snapshot["inventoryOverlay"]
    assert {panel["state"] for panel in snapshot["panels"].values()} == {"LIVE"}


def test_new_manifest_source_enters_supporting_overlay_without_static_key_edit(
    tmp_path: Path,
) -> None:
    dynamic_key = "future_normalized_source"
    provider = _canonical_fixture(
        tmp_path,
        extra_records={
            dynamic_key: [
                {"symbol": f"DYNAMIC{index}", "value": index}
                for index in range(25)
            ]
        },
    )
    service = LivePanelsService(
        db_path=tmp_path / "panel.db",
        client_factory=lambda: (_ for _ in ()).throw(
            AssertionError("dynamic saved overlay must not fetch the network")
        ),
        canonical_source_provider=provider,
        enabled=False,
        calendar_evaluator=lambda _at: {
            "state": "OPEN_NORMAL",
            "isTradingDay": True,
            "tradingDate": TRADING_DATE.isoformat(),
            "reason": "fixture",
        },
    )

    snapshot = asyncio.run(
        service.get_snapshot(refresh=True, force=True, now=NOW + timedelta(seconds=60))
    )
    dynamic_source = snapshot["sources"][dynamic_key]
    dynamic_overlay = next(
        row for row in snapshot["inventoryOverlay"] if row["source_key"] == dynamic_key
    )

    assert dynamic_source["state"] == "RESEARCH_ONLY"
    assert dynamic_source["eligible"] is False
    assert dynamic_source["researchEligible"] is True
    assert dynamic_source["sourceRowCount"] == 25
    assert dynamic_overlay["live_source_status"] == "RESEARCH_ONLY"
    assert len(dynamic_overlay["records_sample"]) == 10


def test_canonical_provider_failure_never_falls_back_to_legacy_client(
    tmp_path: Path,
) -> None:
    client_calls = 0

    def forbidden_client():
        nonlocal client_calls
        client_calls += 1
        raise AssertionError("legacy fetch plane must not be constructed")

    def failed_provider(**_kwargs):
        raise ValueError("fixture manifest failure")

    service = LivePanelsService(
        db_path=tmp_path / "panel.db",
        client_factory=forbidden_client,
        canonical_source_provider=failed_provider,
        enabled=True,
        calendar_evaluator=lambda _at: {
            "state": "OPEN_NORMAL",
            "isTradingDay": True,
            "tradingDate": TRADING_DATE.isoformat(),
            "reason": "fixture",
        },
    )

    snapshot = asyncio.run(
        service.get_snapshot(refresh=True, force=True, now=NOW)
    )

    assert client_calls == 0
    assert snapshot["refresh"]["state"] == "CANONICAL_MANIFEST_FAILED"
    assert snapshot["inventoryOverlay"] == []


def test_market_close_uses_current_downloaded_eod_as_research_overlay(
    tmp_path: Path,
) -> None:
    provider = _closed_research_fixture(tmp_path)
    client_calls = 0

    def forbidden_client():
        nonlocal client_calls
        client_calls += 1
        raise AssertionError("legacy fetch plane must not be constructed")

    service = LivePanelsService(
        db_path=tmp_path / "panel.db",
        client_factory=forbidden_client,
        canonical_source_provider=provider,
        enabled=True,
        calendar_evaluator=lambda _at: {
            "state": "OPEN_NORMAL",
            "isTradingDay": True,
            "tradingDate": TRADING_DATE.isoformat(),
            "reason": "fixture",
        },
    )
    after_close = datetime(2026, 8, 5, 11, 0, tzinfo=UTC)  # 16:30 IST

    snapshot = asyncio.run(service.get_snapshot(refresh=True, now=after_close))

    assert client_calls == 0
    assert snapshot["market"]["session"] == "MARKET_CLOSED"
    assert snapshot["refresh"]["state"] == "CANONICAL_MANIFEST"
    assert {panel["state"] for panel in snapshot["panels"].values()} == {
        "MARKET_CLOSED"
    }
    source = snapshot["sources"]["nse_bhavcopy_eod"]
    assert source["eligible"] is False
    assert source["researchEligible"] is True
    assert source["state"] == "RESEARCH_ONLY"
    assert source["tradingDate"] == TRADING_DATE.isoformat()
    assert snapshot["panels"]["screener"]["researchSources"] == [
        "nse_bhavcopy_eod"
    ]
    assert snapshot["inventoryOverlay"] == [
        {
            "active_source_keys": "nse_bhavcopy_eod",
            "source_key": "nse_bhavcopy_eod",
            "records_sample": [
                {
                    "close": 123.45,
                    "previousClose": 120.0,
                    "series": "EQ",
                    "symbol": "TODAY",
                    "tradeDate": TRADING_DATE.isoformat(),
                    "volume": 1000,
                }
            ],
            "records_scope": "saved_research_records",
            "data_date": TRADING_DATE.isoformat(),
            "fetched_at": NOW.isoformat(),
            "source_row_count": 1,
            "normalized_row_count": 1,
            "live_source_status": "RESEARCH_ONLY",
        }
    ]
    assert "nse_bhavcopy_eod" in CLOSED_RESEARCH_SOURCE_KEYS
