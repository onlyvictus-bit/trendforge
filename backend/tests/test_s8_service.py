"""Shared S8 service ownership tests."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest


def test_service_passes_real_s3_batch_to_s8(monkeypatch) -> None:
    from trendforge_api.selection import s8_service

    s3 = SimpleNamespace(run_id="s3-real", completeness=1.0)
    blob = SimpleNamespace(run_id="s8-real")
    captured = {}
    monkeypatch.setattr(s8_service, "build_s3_cheap_discovery", lambda **_: s3)
    monkeypatch.setattr(s8_service, "build_native_core_run", lambda **_: SimpleNamespace(run_hash="native"))
    monkeypatch.setattr(s8_service, "build_s2_market_weather", lambda: SimpleNamespace())
    monkeypatch.setattr(s8_service, "build_s4_structure_pack", lambda **_: SimpleNamespace())
    monkeypatch.setattr(s8_service, "build_s5_enrichment", lambda **_: None)
    monkeypatch.setattr(s8_service, "build_s6_resolution", lambda **_: SimpleNamespace())
    monkeypatch.setattr(s8_service, "build_s7_state", lambda **_: SimpleNamespace())
    monkeypatch.setattr(s8_service, "latest_selection_payload", lambda *_: None)

    def build_s8_scan(**kwargs):
        captured.update(kwargs)
        return blob

    monkeypatch.setattr(s8_service, "build_s8_scan", build_s8_scan)
    monkeypatch.setattr(s8_service, "persist_s8_scan", lambda value, **_: value)
    result = s8_service.build_and_persist_current_s8(
        r5_batch=SimpleNamespace(run_hash="r5"),
        discovery=SimpleNamespace(),
        attention=SimpleNamespace(),
        built_at=datetime(2026, 8, 28, tzinfo=UTC),
    )
    assert result is blob
    assert captured["s3_batch"] is s3


def test_service_does_not_persist_when_s3_fails(monkeypatch) -> None:
    from trendforge_api.selection import s8_service

    monkeypatch.setattr(
        s8_service,
        "build_s3_cheap_discovery",
        lambda **_: (_ for _ in ()).throw(ValueError("WAIT_S3_LINEAGE_MISMATCH")),
    )
    persisted = []
    monkeypatch.setattr(s8_service, "persist_s8_scan", lambda value, **_: persisted.append(value))
    with pytest.raises(ValueError, match="WAIT_S3_LINEAGE_MISMATCH"):
        s8_service.build_and_persist_current_s8(
            r5_batch=SimpleNamespace(run_hash="r5"),
            discovery=SimpleNamespace(),
            attention=SimpleNamespace(),
        )
    assert persisted == []



def test_service_rebuilds_legacy_match_without_trading_date(monkeypatch) -> None:
    from trendforge_api.selection import s8_service

    legacy = SimpleNamespace(
        trading_date=None,
        lineage=SimpleNamespace(missing_stages=()),
    )
    rebuilt = SimpleNamespace(run_id="s8-rebuilt", trading_date="2026-08-28")
    monkeypatch.setattr(s8_service, "latest_r5_structure_batch", lambda: SimpleNamespace(run_hash="r5"))
    monkeypatch.setattr(s8_service, "latest_attention_order", lambda: SimpleNamespace(run_hash="r2"))
    monkeypatch.setattr(s8_service, "build_native_core_run", lambda **_: SimpleNamespace(run_hash="native"))
    monkeypatch.setattr(s8_service, "latest_matching_s8", lambda **_: legacy)
    monkeypatch.setattr(s8_service, "build_and_persist_current_s8", lambda **_: rebuilt)

    assert s8_service.latest_or_build_current_s8() is rebuilt


def test_service_rebuilds_when_only_stale_lineage_exists(monkeypatch) -> None:
    from trendforge_api.selection import s8_service

    rebuilt = SimpleNamespace(run_id="s8-rebuilt", trading_date="2026-08-28")
    monkeypatch.setattr(s8_service, "latest_r5_structure_batch", lambda: SimpleNamespace(run_hash="r5"))
    monkeypatch.setattr(s8_service, "latest_attention_order", lambda: SimpleNamespace(run_hash="r2"))
    monkeypatch.setattr(s8_service, "build_native_core_run", lambda **_: SimpleNamespace(run_hash="native"))
    monkeypatch.setattr(
        s8_service,
        "latest_matching_s8",
        lambda **_: (_ for _ in ()).throw(ValueError("WAIT_S8_LINEAGE")),
    )
    monkeypatch.setattr(s8_service, "build_and_persist_current_s8", lambda **_: rebuilt)

    assert s8_service.latest_or_build_current_s8() is rebuilt


def test_service_rebuilds_match_without_s2_identity(monkeypatch) -> None:
    from trendforge_api.selection import s8_service

    incomplete = SimpleNamespace(
        trading_date="2026-08-28",
        lineage=SimpleNamespace(s2_run_id=None, missing_stages=()),
    )
    rebuilt = SimpleNamespace(run_id="s8-rebuilt", trading_date="2026-08-28")
    monkeypatch.setattr(s8_service, "latest_r5_structure_batch", lambda: SimpleNamespace(run_hash="r5"))
    monkeypatch.setattr(s8_service, "latest_attention_order", lambda: SimpleNamespace(run_hash="r2"))
    monkeypatch.setattr(s8_service, "build_native_core_run", lambda **_: SimpleNamespace(run_hash="native"))
    monkeypatch.setattr(s8_service, "latest_matching_s8", lambda **_: incomplete)
    monkeypatch.setattr(s8_service, "build_and_persist_current_s8", lambda **_: rebuilt)

    assert s8_service.latest_or_build_current_s8() is rebuilt
