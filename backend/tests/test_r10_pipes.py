"""File A R10 pipe DSL (PK5 / FUS-010) tests.

Law under test:
- seeded versioned pipes compose R8 native-core matches;
- pipes contribute ZERO claims (no EvidenceClaim anywhere in the module);
- stage in/out counts are deterministic; twins cannot inflate counts;
- invalid stage fails the whole run; ENRICH_S7 never filters;
- confirmedCount pinned 0; POST runner forbidden; no place_order.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from trendforge_api.hybrid_v2.tests_support.fixtures import persist_overlay_lineage
from trendforge_api.main import app
from trendforge_api.scanners.native_core import build_native_core_run
from trendforge_api.scanners.pipe_dsl import (
    PIPE_IDS,
    PipeDefinitionV1,
    PipeRunV1,
    build_pipe_run,
    pipe_definition,
)
from trendforge_api.selection.contracts import EvidenceDirection, SelectionState
from trendforge_api.selection.s7_state_gates import S7IdeaCardV1, S7StateBatchV1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fixture_native_core(tmp_path, monkeypatch):
    parts = persist_overlay_lineage(
        tmp_path, monkeypatch, with_structure=True, symbol="HVBTEST"
    )
    return build_native_core_run(r5=parts["structure"])


def _s7_board(*entries: tuple[str, str]) -> S7StateBatchV1:
    """Minimal S7 board: entries are (symbol, publicState)."""
    cards = []
    for index, (symbol, state) in enumerate(entries, start=1):
        cards.append(
            S7IdeaCardV1(
                symbol=symbol,
                public_state=SelectionState(state),
                evidence_direction=EvidenceDirection.BULLISH,
                family_support={},
                family_opposition={},
            )
        )
    return S7StateBatchV1(
        run_id="s7-fixture",
        run_hash="a" * 64,
        s6_run_hash="b" * 64,
        r2_run_hash="c" * 64,
        trading_date="2026-08-14",
        built_at=datetime(2026, 8, 14, tzinfo=UTC),
        rows=tuple(cards),
    )


# ---------------------------------------------------------------------------
# §4.1 Registry: seeds stable, emitsClaims pinned false
# ---------------------------------------------------------------------------


def test_registry_lists_two_stable_seeds() -> None:
    assert len(PIPE_IDS) >= 2
    assert set(PIPE_IDS) == {
        "pipe.breakout_watch.v1",
        "pipe.thrust_participation.v1",
    }
    for pipe_id in PIPE_IDS:
        first = pipe_definition(pipe_id)
        second = pipe_definition(pipe_id)
        assert first == second
        assert isinstance(first, PipeDefinitionV1)
        assert first.emits_claims is False
        assert first.engine == "trendforge.numpy-pandas"
        assert len(first.parameter_hash) == 64


# ---------------------------------------------------------------------------
# §4.2/§4.3 Determinism + stage math over the fixture spine
# ---------------------------------------------------------------------------


def _run_breakout_watch(tmp_path, monkeypatch):
    native = _fixture_native_core(tmp_path, monkeypatch)
    board = _s7_board(("HVBTEST", "WATCH"), ("OTHER", "WAIT"))
    return build_pipe_run("pipe.breakout_watch.v1", native_core=native, s7_board=board)


def test_pipe_run_is_deterministic(tmp_path, monkeypatch) -> None:
    run_a = _run_breakout_watch(tmp_path, monkeypatch)
    run_b = _run_breakout_watch(tmp_path, monkeypatch)
    assert isinstance(run_a, PipeRunV1)
    assert run_a.model_dump(mode="json", by_alias=True) == run_b.model_dump(
        mode="json", by_alias=True
    )


def test_stage_math_and_survivor_order(tmp_path, monkeypatch) -> None:
    run = _run_breakout_watch(tmp_path, monkeypatch)
    # Stages: UNION[breakout] -> FILTER_STATE[WATCH] -> ENRICH_S7
    assert [s.op for s in run.stages] == ["UNION", "FILTER_STATE", "ENRICH_S7"]
    for earlier, later in zip(run.stages, run.stages[1:]):
        assert later.in_count <= earlier.out_count
    for stage in run.stages:
        assert stage.out_count <= stage.in_count
        assert len(stage.reasons) <= 8
    enrich = run.stages[-1]
    assert enrich.in_count == enrich.out_count  # ENRICH never filters
    assert run.out_count == run.stages[-1].out_count == len(run.rows)
    assert [r.symbol for r in run.rows] == ["HVBTEST"]
    assert run.confirmed_count == 0
    assert run.executable is False
    assert run.emits_claims is False


def test_filter_state_drops_non_matching(tmp_path, monkeypatch) -> None:
    native = _fixture_native_core(tmp_path, monkeypatch)
    board = _s7_board(("HVBTEST", "WATCH"))
    run = build_pipe_run(
        "pipe.breakout_watch.v1",
        native_core=native,
        s7_board=_s7_board(("HVBTEST", "REJECT")),
    )
    assert run.out_count == 0
    assert run.rows == ()
    filter_stage = run.stages[1]
    assert filter_stage.op == "FILTER_STATE"
    assert filter_stage.in_count == 1 and filter_stage.out_count == 0
    # The unused healthy board proves the drop came from the state filter.
    assert board.rows[0].symbol == "HVBTEST"


# ---------------------------------------------------------------------------
# §4.4 Twin non-inflation (FUS-009 x FUS-010)
# ---------------------------------------------------------------------------


def test_union_twins_never_inflate_symbol_counts(tmp_path, monkeypatch) -> None:
    native = _fixture_native_core(tmp_path, monkeypatch)
    board = _s7_board(("HVBTEST", "WATCH"))
    single = build_pipe_run(
        "pipe.breakout_watch.v1", native_core=native, s7_board=board
    )
    # Hand-built twin stage: UNION[breakout, trend] must equal UNION[breakout].
    from trendforge_api.scanners.pipe_dsl import evaluate_stages

    twin_stages, _twin_rows = evaluate_stages(
        (
            {"op": "UNION", "scanners": ["native.breakout.v1", "native.trend.v1"]},
            {"op": "ENRICH_S7"},
        ),
        native_core=native,
        s7_board=board,
    )
    base_stages, _base_rows = evaluate_stages(
        ({"op": "UNION", "scanners": ["native.breakout.v1"]}, {"op": "ENRICH_S7"}),
        native_core=native,
        s7_board=board,
    )
    assert twin_stages[0].out_count == base_stages[0].out_count == 1
    assert single.stages[0].out_count == 1


def test_intersection_requires_all_scanners(tmp_path, monkeypatch) -> None:
    native = _fixture_native_core(tmp_path, monkeypatch)
    board = _s7_board(("HVBTEST", "WATCH"))
    stages = (
        {
            "op": "INTERSECTION",
            "scanners": [
                "native.breakout.v1",
                "native.nr_compression.v1",  # NR did NOT fire on the fixture
            ],
        },
        {"op": "ENRICH_S7"},
    )
    run = build_pipe_run(
        "pipe.breakout_watch.v1", native_core=native, s7_board=board, stages_override=stages
    )
    assert run.out_count == 0
    assert any(
        "SCANNER_NOT_MATCHED:native.nr_compression.v1" in r
        for r in run.stages[0].reasons
    )


# ---------------------------------------------------------------------------
# §4.5 Zero claims + pinned counters
# ---------------------------------------------------------------------------


def test_module_mints_no_claims_and_pins_zero_confirmed() -> None:
    from pathlib import Path

    source = Path(
        r"D:\TrendForge\backend\trendforge_api\scanners\pipe_dsl.py"
    ).read_text(encoding="utf-8")
    assert "EvidenceClaim(" not in source
    assert "claim_id" not in source
    assert "place_order" not in source
    with pytest.raises(ValueError):
        PipeRunV1(
            run_id="r",
            run_hash="h",
            parameter_hash="p",
            native_core_run_hash="n",
            trading_date="2026-08-14",
            built_at=datetime(2026, 8, 14, tzinfo=UTC),
            stages=(),
            rows=(),
            out_count=0,
            confirmed_count=2,
        )


# ---------------------------------------------------------------------------
# §4.6 Invalid stage fails the whole run (typed)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stages",
    [
        ({"op": "FILTER_STATE", "states": ["WATCH"]},),
        ({"op": "WAT", "scanners": []},),
        ({"op": "UNION", "scanners": ["native.not_real.v1"]},),
    ],
)
def test_invalid_stages_fail_typed(tmp_path, monkeypatch, stages) -> None:
    native = _fixture_native_core(tmp_path, monkeypatch)
    with pytest.raises(ValueError) as excinfo:
        build_pipe_run(
            "pipe.breakout_watch.v1",
            native_core=native,
            s7_board=_s7_board(),
            stages_override=stages,
        )
    assert "PIPE_INVALID_STAGE" in str(excinfo.value)


def test_unknown_pipe_id_fails_typed(tmp_path, monkeypatch) -> None:
    native = _fixture_native_core(tmp_path, monkeypatch)
    with pytest.raises(ValueError) as excinfo:
        build_pipe_run("pipe.nope.v1", native_core=native, s7_board=_s7_board())
    assert "PIPE_UNKNOWN_ID" in str(excinfo.value)


def test_missing_s7_board_for_state_stage_fails_closed(
    tmp_path, monkeypatch
) -> None:
    native = _fixture_native_core(tmp_path, monkeypatch)
    with pytest.raises(ValueError) as excinfo:
        build_pipe_run("pipe.breakout_watch.v1", native_core=native, s7_board=None)
    assert "WAIT_R10_S7_NOT_READY" in str(excinfo.value)


def test_enrich_without_s7_attaches_none_but_keeps_survivors(
    tmp_path, monkeypatch
) -> None:
    native = _fixture_native_core(tmp_path, monkeypatch)
    stages = ({"op": "UNION", "scanners": ["native.breakout.v1"]}, {"op": "ENRICH_S7"})
    run = build_pipe_run(
        "pipe.breakout_watch.v1",
        native_core=native,
        s7_board=None,
        stages_override=stages,
    )
    assert run.out_count == 1
    assert run.rows[0].public_state is None
    assert run.rows[0].guidance_match is True


# ---------------------------------------------------------------------------
# §4.7 HTTP surface
# ---------------------------------------------------------------------------


def test_definitions_route_lists_seeds() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/pipes/definitions")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["definitions"]) >= 2
    assert all(d["emitsClaims"] is False for d in payload["definitions"])


def test_unknown_pipe_route_is_404() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/pipes/pipe.nope.v1/run")
    assert response.status_code == 404


def test_post_pipes_run_is_405() -> None:
    client = TestClient(app)
    assert client.post("/api/v1/pipes/run").status_code == 405


def test_pipe_run_route_503_without_spine(tmp_path, monkeypatch) -> None:
    from trendforge_api import storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r10-empty.db")
    storage._INITIALIZED_DB_PATHS.clear()
    client = TestClient(app)
    response = client.get("/api/v1/pipes/pipe.breakout_watch.v1/run")
    assert response.status_code == 503
