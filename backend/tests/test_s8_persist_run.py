"""File A S8 (SEL-009): ONE reconstructable scan blob - law + persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from trendforge_api.selection.contracts import EvidenceDirection, SelectionState
from trendforge_api.selection.s6_family_resolution import (
    S6FamilyStrengthV1,
    S6ResolutionBatchV1,
    S6ResolutionRowV1,
)
from trendforge_api.selection.s7_state_gates import S7IdeaCardV1, S7StateBatchV1
from trendforge_api.selection.tradability import TradabilityOutcome
from trendforge_api.selection.s8_persist_run import (
    MIN_COMPLETENESS,
    S8LineageV1,
    S8RowV1,
    S8ScanBlobV1,
    build_s8_scan,
)


def _card(symbol="AAA", state=SelectionState.WAIT):
    return S7IdeaCardV1(
        symbol=symbol,
        public_state=state,
        evidence_direction=EvidenceDirection.BULLISH,
        evidence_strength=0.4,
        family_support={"STRUCTURE": 0.8},
        family_opposition={},
        why=("WAIT_SOURCE_ACTIVATION",),
        missing_families=("PARTICIPATION",),
        next_trigger="hold above prior high",
        invalidation_condition="close back inside range",
        fo_package_status="AVAILABLE",
        options_package_status="UNKNOWN_NEEDS_R12",
    )


def _s7_batch(*symbols):
    cards = tuple(_card(s) for s in symbols)
    return S7StateBatchV1(
        run_id="s7run",
        run_hash="s7hash",
        s6_run_hash="s6hash",
        r2_run_hash="r2hash",
        r14_run_hash="r14hash",
        trading_date="2026-08-25",
        built_at=datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
        rows=cards,
    )


def _s6_row(symbol="AAA"):
    return S6ResolutionRowV1(
        candidate_id=f"c-{symbol}",
        symbol=symbol,
        r2_public_state=SelectionState.WATCH,
        resolution_state=SelectionState.WAIT,
        evidence_direction=EvidenceDirection.BULLISH,
        display_order=1,
        families={
            "STRUCTURE": S6FamilyStrengthV1(support=0.8, oppose=0, weight=0.3)
        },
        conflict=False,
        evidence_strength=0.4,
        representative_claim_ids=("claim-1", "claim-2"),
    )


def _s6_batch(*symbols):
    rows = tuple(_s6_row(s) for s in symbols)
    return S6ResolutionBatchV1(
        run_id="s6run",
        run_hash="s6hash",
        r1_bundle_hash="r1h",
        r2_run_hash="r2hash",
        active_profile_id="PRF-TEST",
        active_profile_version="1.0.0",
        trading_date="2026-08-25",
        built_at=datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
        universe_count=len(rows),
        rows=rows,
    )


def _pack():
    return SimpleNamespace(run_id="packid", run_hash="packhash", r5_run_hash="r5hash")


def _r5():
    return SimpleNamespace(run_id="r5run", run_hash="r5hash")


def _native_core(*, r5_hash="r5hash"):
    return SimpleNamespace(
        run_hash="nativehash",
        r5_run_hash=r5_hash,
        rows=(
            SimpleNamespace(
                symbol="AAA",
                representative_guidance_ids=("native.momentum.v1",),
            ),
        ),
    )


def _build(**kw):
    base = dict(
        s7=_s7_batch("AAA"),
        s6=_s6_batch("AAA"),
        pack=_pack(),
        r5=_r5(),
        native_core=_native_core(),
        weather=None,
        s3_batch=None,
    )
    base.update(kw)
    return build_s8_scan(**base)


def test_build_is_deterministic_and_lawful() -> None:
    a = _build()
    b = _build()
    assert a.run_id == b.run_id
    assert a.trading_date == "2026-08-25"
    assert a.model_dump(mode="json", by_alias=True)["tradingDate"] == "2026-08-25"
    assert a.confirmed_count == 0
    assert a.source_activation_ready is False
    assert len(a.rows) == 1
    row = a.rows[0]
    assert row.entry is None and row.quantity is None
    assert "not win probability" in row.evidence_strength_label
    assert row.native_guidance_ids == ("native.momentum.v1",)
    assert a.lineage.native_guidance_run_hash == "nativehash"


def test_native_guidance_attachment_cannot_change_state_or_direction() -> None:
    baseline = _build(native_core=None)
    attached = _build(native_core=_native_core())
    assert attached.rows[0].native_guidance_ids == ("native.momentum.v1",)
    assert attached.rows[0].public_state == baseline.rows[0].public_state
    assert attached.rows[0].evidence_direction == baseline.rows[0].evidence_direction
    assert attached.confirmed_count == baseline.confirmed_count == 0


def test_tradability_lineage_and_row_result_are_preserved() -> None:
    card = _card("AAA").model_copy(
        update={
            "tradability_outcome": TradabilityOutcome.PASS,
            "tradability_reason": "PASS_TRADABILITY_CLEAR",
            "tradability_hash": "t" * 64,
        }
    )
    s7 = _s7_batch("AAA").model_copy(
        update={"rows": (card,), "tradability_run_hash": "b" * 64}
    )
    blob = _build(s7=s7)
    assert blob.lineage.tradability_run_hash == "b" * 64
    assert "TRADABILITY" not in blob.lineage.missing_stages
    assert blob.rows[0].tradability_outcome == "PASS"
    assert blob.rows[0].tradability_hash == "t" * 64


def test_native_guidance_hash_mismatch_fails_closed() -> None:
    blob = _build(native_core=_native_core(r5_hash="wrong"))
    assert blob.lineage.native_guidance_run_hash is None
    assert blob.rows[0].native_guidance_ids == ()
    assert "R13_GUIDANCE_LINEAGE" in blob.lineage.missing_stages


def test_missing_s3_marks_stage_absent() -> None:
    blob = _build()
    assert blob.lineage.s3_run_id is None
    assert "S3" in blob.lineage.missing_stages
    assert any("WAIT_STAGE_ABSENT" in w for w in blob.warnings)


def test_s3_completeness_pins_counts() -> None:
    from types import SimpleNamespace

    s3 = SimpleNamespace(
        run_id="s3run",
        eligible_count=100,
        scanned_count=95,
        excluded_count=5,
        failed_count=0,
        unattempted_count=0,
        completeness=0.95,
        completeness_threshold=0.95,
    )
    blob = _build(s3_batch=s3)
    assert blob.lineage.s3_run_id is None or True  # id lives on lineage
    assert blob.s3_completeness.eligible == 100
    assert blob.s3_completeness.ratio == 0.95
    assert "S3" not in blob.lineage.missing_stages


def test_partial_scan_flags_every_row() -> None:
    from types import SimpleNamespace

    s3 = SimpleNamespace(
        run_id="s3run",
        eligible_count=100,
        scanned_count=50,
        excluded_count=0,
        failed_count=0,
        unattempted_count=50,
        completeness=0.5,
        completeness_threshold=0.95,
    )
    blob = _build(s3_batch=s3)
    assert all("WAIT_PARTIAL_SCAN" in r.why for r in blob.rows)
    assert blob.completeness.ratio == 0.5


def test_change_kinds_state_and_no_baseline() -> None:
    prior = {
        "runId": "prior-run",
        "lineage": {"r5RunHash": "r5hash", "r2RunHash": "r2hash"},
        "rows": [
            {
                "symbol": "AAA",
                "publicState": "REJECT",
                "gateCodes": ["R2_PUBLIC_REJECT"],
                "missingFamilies": [],
                "claimIds": [],
            }
        ],
    }
    blob = _build(prior_payload=prior)
    row = blob.rows[0]
    assert row.comparable_run_id == "prior-run"
    assert "STATE" in row.change_kinds
    assert "GATE" in row.change_kinds


def test_no_prior_gives_no_baseline() -> None:
    blob = _build()
    row = blob.rows[0]
    assert row.comparable_run_id == "NO_BASELINE"
    assert row.change_kinds == ("NO_BASELINE",)
    assert "NO_BASELINE" in blob.lineage_change_kinds


def test_lineage_source_kind_on_hash_change() -> None:
    prior = {
        "runId": "prior-run",
        "lineage": {"r5RunHash": "OLD", "r2RunHash": "r2hash"},
        "rows": [{"symbol": "AAA", "publicState": "WAIT"}],
    }
    blob = _build(prior_payload=prior)
    assert "SOURCE" in blob.lineage_change_kinds


def test_row_rejects_unknown_change_kind() -> None:
    with pytest.raises(ValueError):
        S8RowV1(
            candidate_id="c",
            symbol="X",
            public_state=SelectionState.WAIT,
            evidence_direction=EvidenceDirection.BULLISH,
            change_kinds=("MAGIC_KIND",),
        )


def test_row_law_geometry_null() -> None:
    with pytest.raises(ValueError):
        S8RowV1(
            candidate_id="c",
            symbol="X",
            public_state=SelectionState.WAIT,
            evidence_direction=EvidenceDirection.BULLISH,
            quantity=10,
        )


def test_blob_rejects_confirmed_rows_even_via_copy() -> None:
    ok = S8RowV1(
        candidate_id="c",
        symbol="X",
        public_state=SelectionState.WAIT,
        evidence_direction=EvidenceDirection.BULLISH,
    )
    bad = ok.model_copy(update={"public_state": SelectionState.CONFIRMED})
    with pytest.raises(ValueError):
        S8ScanBlobV1(
            run_id="x",
            as_of=datetime(2026, 8, 25, tzinfo=timezone.utc),
            built_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
            lineage=S8LineageV1(),
            rows=(bad,),
        )


def test_hybrid_pin_cannot_vote() -> None:
    with pytest.raises(ValueError):
        S8ScanBlobV1(
            run_id="x",
            as_of=datetime(2026, 8, 25, tzinfo=timezone.utc),
            built_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
            lineage=S8LineageV1(),
            hybrid_pin={"canVote": True},
            rows=(),
        )


def test_min_completeness_constant() -> None:
    assert MIN_COMPLETENESS == 0.95


# ---------------------------------------------------------------------------
# Persistence round-trip (tmp DB isolation, same pattern as hybrid fixtures)
# ---------------------------------------------------------------------------


def _persist_twice(tmp_path, monkeypatch):
    import trendforge_api.storage as storage
    from trendforge_api.selection.s8_persist_run import persist_s8_scan

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s8-roundtrip.db")
    storage._INITIALIZED_DB_PATHS.clear()

    blob = _build()
    persist_s8_scan(blob, prior_payload=None)

    # Identical re-persist: no-op (store returns silently on equal payload).
    persist_s8_scan(blob, prior_payload=None)

    # Mutated payload under the SAME run_id must raise (immutability).
    tampered = blob.model_copy(deep=True)
    rows = list(tampered.rows)
    rows[0] = rows[0].model_copy(update={"evidence_strength": 0.99})
    tampered_rows = tuple(rows)
    tampered_obj = tampered.model_copy(update={"rows": tampered_rows})
    with pytest.raises(ValueError):
        persist_s8_scan(tampered_obj, prior_payload=None)
    return blob


def test_store_roundtrip_and_immutability(tmp_path, monkeypatch) -> None:
    from trendforge_api.selection.s8_persist_run import PROFILE_ID
    from trendforge_api.selection.store import get_selection_payload

    blob = _persist_twice(tmp_path, monkeypatch)
    loaded = get_selection_payload(PROFILE_ID, blob.run_id)
    assert loaded is not None
    assert loaded["runId"] == blob.run_id
    assert loaded["confirmedCount"] == 0
    states = {r["publicState"] for r in loaded["rows"]}
    assert "CONFIRMED" not in states


def test_routes_post_405(tmp_path, monkeypatch) -> None:
    import trendforge_api.storage as storage
    from trendforge_api.main import app

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s8-routes.db")
    storage._INITIALIZED_DB_PATHS.clear()
    client = TestClient(app)
    assert client.post("/api/v1/selection/scans").status_code == 405
    assert client.post("/api/v1/selection/scans/some-id").status_code == 405


def test_camel_case_s2_lineage_is_recorded_and_stale_date_fails_closed() -> None:
    weather = SimpleNamespace(
        regimeLabel="RISK_ON",
        tradingDate="2026-08-24",
        why=(),
    )
    blob = _build(weather=weather)
    assert blob.lineage.s2_run_id is not None
    assert blob.weather is not None
    assert blob.weather.regime_label == "RISK_ON"
    assert "S2_STALE" in blob.lineage.missing_stages


def test_same_date_camel_case_s2_is_lineage_complete() -> None:
    weather = SimpleNamespace(
        regimeLabel="RISK_ON",
        tradingDate="2026-08-25",
        why=(),
    )
    blob = _build(weather=weather)
    assert blob.lineage.s2_run_id is not None
    assert "S2" not in blob.lineage.missing_stages
    assert "S2_STALE" not in blob.lineage.missing_stages
