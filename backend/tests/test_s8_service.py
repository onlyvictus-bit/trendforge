"""Shared S8 service ownership and retention-bound producer tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from trendforge_api.retention_publication import RetentionEvidenceRoot


def _r5() -> SimpleNamespace:
    return SimpleNamespace(
        run_hash="r5",
        r1_bundle_id="r1-exact",
        r1_bundle_hash="a" * 64,
        collector_run_id="orchestrator-not-storage-root",
        trading_date="2026-08-28",
        rows=(),
    )


def _r1_and_roots():
    return (
        SimpleNamespace(
            collector_run_id="orchestrator-not-storage-root",
            bundle_id="r1-exact",
            bundle_hash="a" * 64,
        ),
        (RetentionEvidenceRoot(role="R1_SOURCE_0001", content_hash="b" * 64),),
    )


def test_service_passes_real_s3_batch_and_exact_r1_hash_roots(monkeypatch) -> None:
    from trendforge_api.selection import s8_service

    s3 = SimpleNamespace(run_id="s3-real", completeness=1.0)
    blob = SimpleNamespace(run_id="s8-real")
    captured = {}
    monkeypatch.setattr(s8_service, "_exact_r1_evidence", lambda _: _r1_and_roots())
    monkeypatch.setattr(s8_service, "build_s3_cheap_discovery", lambda **_: s3)
    monkeypatch.setattr(s8_service, "build_native_core_run", lambda **_: SimpleNamespace(run_hash="native"))
    monkeypatch.setattr(s8_service, "build_s2_market_weather", lambda **_: SimpleNamespace())
    monkeypatch.setattr(s8_service, "build_s4_structure_pack", lambda **_: SimpleNamespace())
    monkeypatch.setattr(s8_service, "build_s5_enrichment", lambda **_: None)
    monkeypatch.setattr(s8_service, "build_s6_resolution", lambda **_: SimpleNamespace())
    monkeypatch.setattr(s8_service, "build_s7_state", lambda **_: SimpleNamespace())
    monkeypatch.setattr(s8_service, "latest_selection_payload", lambda *_: None)

    def build_s8_scan(**kwargs):
        captured.update(kwargs)
        return blob

    retained = {}
    monkeypatch.setattr(s8_service, "build_s8_scan", build_s8_scan)
    monkeypatch.setattr(
        s8_service,
        "persist_protected_s8",
        lambda **kwargs: retained.update(kwargs) or kwargs["blob"],
    )
    result = s8_service.build_and_persist_current_s8(
        r5_batch=_r5(),
        discovery=SimpleNamespace(),
        attention=SimpleNamespace(),
        built_at=datetime(2026, 8, 28, tzinfo=UTC),
    )
    assert result is blob
    assert captured["s3_batch"] is s3
    assert retained["evidence_roots"][0].content_hash == "b" * 64
    assert retained["publication_lineage"]["r1BundleId"] == "r1-exact"
    assert retained["trading_date"] == date(2026, 8, 28)


def test_service_fails_closed_when_exact_r1_evidence_missing(monkeypatch) -> None:
    from trendforge_api.selection import s8_service

    monkeypatch.setattr(
        s8_service,
        "_exact_r1_evidence",
        lambda _: (_ for _ in ()).throw(ValueError("WAIT_RHIST03_R1_BUNDLE_MISSING")),
    )
    with pytest.raises(ValueError, match="WAIT_RHIST03_R1_BUNDLE_MISSING"):
        s8_service.build_and_persist_current_s8(
            r5_batch=_r5(),
            discovery=SimpleNamespace(),
            attention=SimpleNamespace(),
        )


def test_service_does_not_publish_when_s3_fails(monkeypatch) -> None:
    from trendforge_api.selection import s8_service

    monkeypatch.setattr(s8_service, "_exact_r1_evidence", lambda _: _r1_and_roots())
    monkeypatch.setattr(
        s8_service,
        "build_s3_cheap_discovery",
        lambda **_: (_ for _ in ()).throw(ValueError("WAIT_S3_LINEAGE_MISMATCH")),
    )
    retained = []
    monkeypatch.setattr(s8_service, "persist_protected_s8", lambda **kwargs: retained.append(kwargs))
    with pytest.raises(ValueError, match="WAIT_S3_LINEAGE_MISMATCH"):
        s8_service.build_and_persist_current_s8(
            r5_batch=_r5(),
            discovery=SimpleNamespace(),
            attention=SimpleNamespace(),
        )
    assert retained == []


def test_read_path_rebuild_is_ephemeral_not_persisted(monkeypatch) -> None:
    from trendforge_api.selection import s8_service

    rebuilt = SimpleNamespace(run_id="s8-ephemeral", trading_date="2026-08-28")
    monkeypatch.setattr(s8_service, "latest_r5_structure_batch", lambda: _r5())
    monkeypatch.setattr(s8_service, "latest_attention_order", lambda: SimpleNamespace(run_hash="r2"))
    monkeypatch.setattr(s8_service, "build_native_core_run", lambda **_: SimpleNamespace(run_hash="native"))
    monkeypatch.setattr(s8_service, "build_tradability_batch", lambda **_: SimpleNamespace(run_hash="tradability"))
    monkeypatch.setattr(
        s8_service,
        "latest_matching_s8",
        lambda **_: (_ for _ in ()).throw(ValueError("WAIT_S8_LINEAGE")),
    )
    monkeypatch.setattr(s8_service, "assemble_current_scan", lambda **_: SimpleNamespace(blob=rebuilt))
    monkeypatch.setattr(
        s8_service,
        "persist_protected_s8",
        lambda **_: (_ for _ in ()).throw(AssertionError("read path wrote retention")),
    )
    assert s8_service.latest_or_build_current_s8() is rebuilt


def test_read_path_returns_complete_persisted_match_without_write(monkeypatch) -> None:
    from trendforge_api.selection import s8_service

    complete = SimpleNamespace(
        trading_date="2026-08-28",
        lineage=SimpleNamespace(
            s2_run_id="s2",
            tradability_run_hash="t" * 64,
            missing_stages=(),
        ),
    )
    monkeypatch.setattr(s8_service, "latest_r5_structure_batch", lambda: _r5())
    monkeypatch.setattr(s8_service, "latest_attention_order", lambda: SimpleNamespace(run_hash="r2"))
    monkeypatch.setattr(s8_service, "build_native_core_run", lambda **_: SimpleNamespace(run_hash="native"))
    monkeypatch.setattr(s8_service, "build_tradability_batch", lambda **_: SimpleNamespace(run_hash="tradability"))
    monkeypatch.setattr(s8_service, "latest_matching_s8", lambda **_: complete)
    monkeypatch.setattr(
        s8_service,
        "assemble_current_scan",
        lambda **_: (_ for _ in ()).throw(AssertionError("complete match should be reused")),
    )
    assert s8_service.latest_or_build_current_s8() is complete
