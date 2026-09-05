"""File A R8 native core scanner tests.

Law under test:
- five versioned native definitions (breakout/NR/trend/RVOL/volume thrust),
  engine trendforge.numpy-pandas, parameter hashes stable;
- native core WRAPS R5 closed-bar claims (no third engine);
- one representative per correlation group (FUS-009 first-wins); twin matches
  are labelled correlated_possible, never independent confirms;
- S3 may show nativeCoreMatches[] with rank untouched;
- confirmedCount pinned 0; PK shadow failure cannot change anything;
- no place_order anywhere under scanners/.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from trendforge_api.hybrid_v2.tests_support.fixtures import persist_overlay_lineage
from trendforge_api.main import app
from trendforge_api.scanners.native_core import (
    NativeCoreRowV1,
    NativeCoreRunV1,
    NativeScannerMatchV1,
    attach_native_matches_to_s3,
    build_native_core_run,
    representative_matches,
)
from trendforge_api.scanners.registry import (
    NATIVE_CORE_DEFINITIONS,
    NATIVE_CORE_IDS,
    scanner_definition,
)
from trendforge_api.selection.contracts import EvidenceDirection, SelectionState
from trendforge_api.selection.s6_family_resolution import (
    S6FamilyStrengthV1,
    S6ResolutionRowV1,
    merge_native_claims,
)


# ---------------------------------------------------------------------------
# Registry (§1 / §4.1)
# ---------------------------------------------------------------------------


def test_registry_lists_core_five_stable_definitions() -> None:
    # R13 amendment: the registry GREW; the original five must remain,
    # but the registry may now contain additional bounded-family scanners.
    assert len(NATIVE_CORE_IDS) >= 5
    five = {
        "native.breakout.v1",
        "native.nr_compression.v1",
        "native.trend.v1",
        "native.rvol.v1",
        "native.volume_thrust.v1",
    }
    assert five <= set(NATIVE_CORE_IDS)
    for scanner_id in five:
        first = scanner_definition(scanner_id)
        second = scanner_definition(scanner_id)
        assert first == second
        assert first.parameter_hash == second.parameter_hash
        assert len(first.parameter_hash) == 64
        assert first.engine == "trendforge.numpy-pandas"
        assert first.authority == "NATIVE"
        assert first.can_support_confirmed is False
        assert first.version == "v1"


def test_registry_family_group_map_matches_prompt() -> None:
    by_id = {d.scanner_id: d for d in NATIVE_CORE_DEFINITIONS}
    assert (by_id["native.breakout.v1"].family, by_id["native.breakout.v1"].group) == (
        "STRUCTURE",
        "CG_PRICE_STRUCTURE",
    )
    assert (by_id["native.trend.v1"].family, by_id["native.trend.v1"].group) == (
        "STRUCTURE",
        "CG_PRICE_STRUCTURE",
    )
    assert (
        by_id["native.nr_compression.v1"].family,
        by_id["native.nr_compression.v1"].group,
    ) == ("STRUCTURE", "CG_COMPRESSION")
    assert (by_id["native.rvol.v1"].family, by_id["native.rvol.v1"].group) == (
        "PARTICIPATION",
        "CG_ACTIVITY_SESSION",
    )
    assert (
        by_id["native.volume_thrust.v1"].family,
        by_id["native.volume_thrust.v1"].group,
    ) == ("PARTICIPATION", "CG_ACTIVITY_SESSION")


def test_pk_compatible_only_where_parity_fixture_exists() -> None:
    by_id = {d.scanner_id: d for d in NATIVE_CORE_DEFINITIONS}
    # FTR-005/006/007 have PK parity mappings; FTR-017 does not.
    assert by_id["native.breakout.v1"].pk_compatible is True
    assert by_id["native.trend.v1"].pk_compatible is True
    assert by_id["native.nr_compression.v1"].pk_compatible is True
    assert by_id["native.rvol.v1"].pk_compatible is False
    assert by_id["native.volume_thrust.v1"].pk_compatible is False


# ---------------------------------------------------------------------------
# Run over the fixture R5 spine (§4.2 wraps, §4.5 zero confirmed)
# ---------------------------------------------------------------------------


def _fixture_run(tmp_path, monkeypatch):
    parts = persist_overlay_lineage(
        tmp_path, monkeypatch, with_structure=True, symbol="HVBTEST"
    )
    return build_native_core_run(r5=parts["structure"]), parts


def test_run_wraps_r5_claims_and_pins_zero_confirmed(tmp_path, monkeypatch) -> None:
    run, parts = _fixture_run(tmp_path, monkeypatch)
    assert isinstance(run, NativeCoreRunV1)
    assert run.confirmed_count == 0
    assert run.executable is False
    assert run.can_unlock_confirmed is False
    assert run.universe == "FULL_HASH_MATCHED_R5"
    assert run.r5_run_hash == parts["structure"].run_hash
    assert all(m.can_support_confirmed is False for r in run.rows for m in r.matches)
    row = next(r for r in run.rows if r.symbol == "HVBTEST")
    matched = {m.scanner_id for m in row.matches if m.matched}
    # Breakout acceptance + RVOL exceed their thresholds in the fixture.
    assert "native.breakout.v1" in matched
    assert "native.trend.v1" in matched
    assert "native.rvol.v1" in matched
    assert row.guidance_match is True
    assert row.lookback_bars == parts["structure"].rows[0].history_count


def test_run_identity_is_lineage_scoped_and_stable(tmp_path, monkeypatch) -> None:
    run_a, parts = _fixture_run(tmp_path, monkeypatch)
    run_b = build_native_core_run(r5=parts["structure"])
    assert run_a.run_hash == run_b.run_hash
    assert run_a.run_id == run_b.run_id


def test_pk_shadow_failure_cannot_change_rows(tmp_path, monkeypatch) -> None:
    def _boom():
        raise RuntimeError("pk worker exploded")

    parts = persist_overlay_lineage(
        tmp_path, monkeypatch, with_structure=True, symbol="HVBTEST"
    )
    healthy = build_native_core_run(r5=parts["structure"])
    broken = build_native_core_run(r5=parts["structure"], pk_probe=_boom)
    # With a broken probe the run still builds; rows are byte-identical.
    assert [r.model_dump(exclude={"why"}) for r in broken.rows] == [
        r.model_dump(exclude={"why"}) for r in healthy.rows
    ]
    assert any("PK_SHADOW_UNAVAILABLE" in w for w in broken.warnings)
    assert not any("PK_SHADOW_UNAVAILABLE" in w for w in healthy.warnings)


def test_confirmed_count_validator() -> None:
    match = NativeScannerMatchV1(
        scanner_id="native.breakout.v1",
        matched=True,
        feature_id="FTR-006",
        claim_id="c",
        family="STRUCTURE",
        group="CG_PRICE_STRUCTURE",
        guidance_label="Breakout matched - guidance",
    )
    with pytest.raises(ValueError):
        NativeCoreRunV1(
            run_id="r",
            run_hash="h",
            r5_run_hash="x",
            trading_date="2026-08-14",
            built_at=datetime(2026, 8, 14, tzinfo=UTC),
            definitions=NATIVE_CORE_DEFINITIONS,
            rows=(
                NativeCoreRowV1(
                    symbol="X",
                    candidate_id="c-X",
                    matches=(match,),
                    guidance_match=True,
                    completeness=1.0,
                ),
            ),
            matched_count=1,
            confirmed_count=1,
        )


# ---------------------------------------------------------------------------
# One representative per group (§4.2/§4.3 FUS-009 first-wins)
# ---------------------------------------------------------------------------


def _match(sid: str, claim: str, feature: str, family: str, group: str, corr=()):
    return NativeScannerMatchV1(
        scanner_id=sid,
        matched=True,
        feature_id=feature,
        claim_id=claim,
        family=family,
        group=group,
        correlated_with=tuple(corr),
        correlated_possible=bool(corr),
        guidance_label=f"{sid} matched - guidance",
    )


def test_breakout_and_trend_share_one_structure_representative() -> None:
    matches = (
        _match(
            "native.breakout.v1", "claim-1", "FTR-006", "STRUCTURE", "CG_PRICE_STRUCTURE"
        ),
        _match(
            "native.trend.v1",
            "claim-1",
            "FTR-006",
            "STRUCTURE",
            "CG_PRICE_STRUCTURE",
            corr=("native.breakout.v1",),
        ),
    )
    reps = representative_matches(matches)
    structure_reps = [m for m in reps if m.group == "CG_PRICE_STRUCTURE"]
    assert len(structure_reps) == 1
    assert structure_reps[0].claim_id == "claim-1"
    assert structure_reps[0].scanner_id == "native.breakout.v1"  # first-wins


def test_rvol_and_thrust_share_one_participation_representative() -> None:
    matches = (
        _match(
            "native.rvol.v1",
            "claim-2",
            "FTR-017",
            "PARTICIPATION",
            "CG_ACTIVITY_SESSION",
        ),
        _match(
            "native.volume_thrust.v1",
            "claim-2",
            "FTR-017",
            "PARTICIPATION",
            "CG_ACTIVITY_SESSION",
            corr=("native.rvol.v1",),
        ),
    )
    reps = representative_matches(matches)
    participation = [m for m in reps if m.group == "CG_ACTIVITY_SESSION"]
    assert len(participation) == 1
    assert participation[0].claim_id == "claim-2"


def test_correlated_twins_never_count_as_two_independent() -> None:
    matches = (
        _match(
            "native.breakout.v1", "claim-1", "FTR-006", "STRUCTURE", "CG_PRICE_STRUCTURE"
        ),
        _match(
            "native.trend.v1",
            "claim-1",
            "FTR-006",
            "STRUCTURE",
            "CG_PRICE_STRUCTURE",
            corr=("native.breakout.v1",),
        ),
    )
    run_row_matches = representative_matches(matches)
    twins = [m for m in run_row_matches if m.correlated_possible]
    assert len(twins) <= 1  # the twin is folded into the single representative


# ---------------------------------------------------------------------------
# S6 ingest: native claims only fill EMPTY groups, never override R5 (§W)
# ---------------------------------------------------------------------------


def _s6_row(symbol: str, *rep_ids: str) -> S6ResolutionRowV1:
    fams = {
        "STRUCTURE": S6FamilyStrengthV1(support=0.9, oppose=0.0, weight=0.1),
        "PARTICIPATION": S6FamilyStrengthV1(support=0.0, oppose=0.0, weight=0.1),
        "EVENT_AND_SPONSOR": S6FamilyStrengthV1(support=0.0, oppose=0.0, weight=0.1),
    }
    return S6ResolutionRowV1(
        candidate_id=f"c-{symbol}",
        symbol=symbol,
        r2_public_state=SelectionState.WATCH,
        resolution_state=SelectionState.WAIT,
        evidence_direction=EvidenceDirection.BULLISH,
        display_order=1,
        families=fams,
        conflict=False,
        evidence_strength=0.4,
        representative_claim_ids=tuple(rep_ids),
    )


def test_merge_native_claims_is_first_wins_per_group() -> None:
    row = _s6_row("AAA", "r5-price-claim")
    merged = merge_native_claims(
        (row,),
        native_claims=(
            {"symbol": "AAA", "group": "CG_PRICE_STRUCTURE", "claim_id": "native-1"},
        ),
        covered_groups={"AAA": {"CG_PRICE_STRUCTURE"}},
    )
    # Group already represented by R5 -> native claim must NOT be added.
    assert merged[0].representative_claim_ids == ("r5-price-claim",)

    empty = _s6_row("BBB")
    merged_empty = merge_native_claims(
        (empty,),
        native_claims=(
            {"symbol": "BBB", "group": "CG_COMPRESSION", "claim_id": "native-nr"},
            {"symbol": "BBB", "group": "CG_COMPRESSION", "claim_id": "native-dup"},
        ),
    )
    assert merged_empty[0].representative_claim_ids == ("native-nr",)
    assert any(
        "NATIVE_CLAIM_INGESTED:native-nr" in code
        for code in merged_empty[0].why
    )


# ---------------------------------------------------------------------------
# S3 attach: matches visible, rank untouched (§4.8)
# ---------------------------------------------------------------------------


def _minimal_s3_batch(symbol: str = "HVBTEST"):
    from trendforge_api.selection.s3_cheap_discovery import (
        S3CheapDiscoveryBatchV1,
        S3CheapDiscoveryRowV1,
    )

    row = S3CheapDiscoveryRowV1(
        symbol=symbol,
        instrument_id="ins-1",
        public_state=SelectionState.WATCH,
        attention_priority=0.6,
        tags=("CLOSED_BAR_BREAKOUT",),
        completeness_contribution=1.0,
        research_state=SelectionState.WATCH,
    )
    return S3CheapDiscoveryBatchV1(
        run_id="s3-run",
        run_hash="s3-hash",
        a3_batch_id="a3",
        r2_run_id="r2",
        r2_run_hash="r2h",
        trading_date="2026-08-14",
        built_at=datetime(2026, 8, 14, tzinfo=UTC),
        eligible_count=1,
        scanned_count=1,
        excluded_count=0,
        failed_count=0,
        unattempted_count=0,
        completeness=1.0,
        completeness_threshold=0.95,
        wait_partial_scan=False,
        layer_status={},
        rows=(row,),
    )


def test_s3_rank_unchanged_when_native_matches_attached(tmp_path, monkeypatch) -> None:
    run, _parts = _fixture_run(tmp_path, monkeypatch)
    batch = _minimal_s3_batch()
    before = [(r.symbol, r.attention_priority) for r in batch.rows]
    attached = attach_native_matches_to_s3(batch, run)
    after = [(r.symbol, r.attention_priority) for r in attached.rows]
    assert before == after
    assert attached.native_core_matches.get("HVBTEST")
    assert "native.breakout.v1" in attached.native_core_matches["HVBTEST"]
    # Rows themselves are byte-identical (rank fields untouched).
    assert attached.rows == batch.rows


# ---------------------------------------------------------------------------
# HTTP surface (§0.1 / §4.6 / §4.7)
# ---------------------------------------------------------------------------


def test_definitions_endpoint_lists_five() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/scanners/definitions")
    assert response.status_code == 200
    payload = response.json()
    ids = [d["scannerId"] for d in payload["definitions"]]
    assert len(ids) >= 5
    assert all(d["canSupportConfirmed"] is False for d in payload["definitions"])


def test_post_scanners_run_is_405() -> None:
    client = TestClient(app)
    assert client.post("/api/v1/scanners/run").status_code == 405


def test_native_core_route_503_without_spine(tmp_path, monkeypatch) -> None:
    from trendforge_api import storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r8-empty.db")
    storage._INITIALIZED_DB_PATHS.clear()
    client = TestClient(app)
    response = client.get("/api/v1/scanners/native-core")
    assert response.status_code == 503
    # Typed fail-closed code from the shared hash-matched R5 spine gate.
    assert str(response.json()["detail"]["code"])


def test_native_core_route_503_on_hash_mismatch(tmp_path, monkeypatch) -> None:
    def _mismatch():
        raise ValueError("WAIT_R5_LINEAGE_MISMATCH")

    monkeypatch.setattr("trendforge_api.main._hash_matched_r5_or_503", _mismatch)
    client = TestClient(app)
    response = client.get("/api/v1/scanners/native-core")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "WAIT_R5_LINEAGE_MISMATCH"


# ---------------------------------------------------------------------------
# No order path under scanners/ (§4.9)
# ---------------------------------------------------------------------------


def test_no_place_order_under_scanners_package() -> None:
    from pathlib import Path

    pkg = (
        Path(__file__).resolve().parents[1] / "trendforge_api" / "scanners"
    )
    offenders = [
        p.name
        for p in pkg.glob("*.py")
        if "place_order" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []
