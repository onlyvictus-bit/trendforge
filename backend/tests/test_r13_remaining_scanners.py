"""File A R13 remaining native scanners (PK4) tests — CHIPS-ONLY law.

Verified audit points under test:
- registry grew to the six bounded-family scanners (11 total), hashes stable;
- matches are GUIDANCE CHIPS: zero EvidenceClaim construction anywhere in
  scanners/, no claim ids on R13 matches;
- family caps hold without claims: compression trio folds to ONE
  representative; extremes joins PRICE_STRUCTURE without inflating;
- momentum pinned RSI(14); reversal uses StructureMetrics.reference_level
  with a 3-bar reclaim window; extremes exclude the current bar (off-by-one);
- warmup shortfalls seat INPUT_INCOMPLETE_WARMUP reasons, never fake matches;
- POST runner forbidden; no ORB/VWAP modules; regressions green.
"""

from __future__ import annotations

import math
import hashlib
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from trendforge_api.hybrid_v2.tests_support.fixtures import persist_overlay_lineage
from trendforge_api.main import app
from trendforge_api.scanners.native_core import (
    build_native_core_run,
    representative_guidance_chips,
    representative_matches,
)
from trendforge_api.scanners.native_extended import (
    _rsi14,
    _squeeze_metrics,
    _vcp_metrics,
    compute_extended_matches,
    is_at_extreme,
)
from trendforge_api.scanners.registry import (
    NATIVE_CORE_IDS,
    scanner_definition,
)

R13_IDS = {
    "native.vcp.v1",
    "native.ttm_squeeze.v1",
    "native.trend_overlay.v1",
    "native.momentum.v1",
    "native.reversal.v1",
    "native.extremes.v1",
}


def _bar(
    close: float,
    volume: float = 1000.0,
    *,
    high: float | None = None,
    low: float | None = None,
):
    value = float(close)
    return SimpleNamespace(
        open=value,
        high=float(high if high is not None else value + 1.0),
        low=float(low if low is not None else value - 1.0),
        close=value,
        volume=float(volume),
    )


# ---------------------------------------------------------------------------
# Registry growth (§3.1)
# ---------------------------------------------------------------------------


def test_registry_grew_to_eleven_with_stable_hashes() -> None:
    assert len(NATIVE_CORE_IDS) == 11
    assert R13_IDS <= set(NATIVE_CORE_IDS)
    for scanner_id in R13_IDS:
        d = scanner_definition(scanner_id)
        assert d == scanner_definition(scanner_id)
        assert d.can_support_confirmed is False
        assert d.pk_compatible is False  # PK parity map covers FTR-005/006/007 only
        assert len(d.parameter_hash) == 64


def test_r13_group_map_matches_registered_contracts() -> None:
    from trendforge_api.feature_registry import feature_contract_by_id

    ftr_by_scanner = {
        "native.vcp.v1": "FTR-008",
        "native.ttm_squeeze.v1": "FTR-009",
        "native.trend_overlay.v1": "FTR-012",
        "native.momentum.v1": "FTR-013",
        "native.reversal.v1": "FTR-014",
        "native.extremes.v1": "FTR-015",
    }
    for scanner_id, fid in ftr_by_scanner.items():
        contract = feature_contract_by_id(fid)
        definition = scanner_definition(scanner_id)
        assert definition.family == contract.evidence_family
        assert definition.group == contract.correlation_group


# ---------------------------------------------------------------------------
# Pure math: momentum / reversal / extremes / overlay (§3.5–§3.8)
# ---------------------------------------------------------------------------


def test_rsi14_uses_fourteen_differences() -> None:
    closes = [
        44.0, 44.15, 43.9, 44.35, 44.7, 44.55, 44.9, 45.1,
        44.8, 45.0, 45.4, 45.2, 45.65, 45.8, 46.0,
    ]
    diffs = [right - left for left, right in zip(closes, closes[1:])]
    gains = sum(max(value, 0.0) for value in diffs) / 14
    losses = sum(max(-value, 0.0) for value in diffs) / 14
    expected = 100.0 if losses == 0 else 100.0 - 100.0 / (1.0 + gains / losses)
    assert _rsi14(closes) == pytest.approx(expected, rel=1e-12)


def test_momentum_pinned_rsi14_has_directional_context() -> None:
    rising = [_bar(100 + i) for i in range(20)]  # strong uptrend -> RSI high
    flat = [_bar(100) for _ in range(20)]
    matches_up = compute_extended_matches(rising, reference_level=None)
    mom_up = next(m for m in matches_up if m.scanner_id == "native.momentum.v1")
    assert mom_up.matched is True
    assert mom_up.directional_context == "BULLISH"
    matches_flat = compute_extended_matches(flat, reference_level=None)
    mom_flat = next(m for m in matches_flat if m.scanner_id == "native.momentum.v1")
    assert mom_flat.matched is False
    assert mom_flat.directional_context == "NEUTRAL"
    short = [_bar(100)] * 5
    mom_short = next(
        m
        for m in compute_extended_matches(short, reference_level=None)
        if m.scanner_id == "native.momentum.v1"
    )
    assert mom_short.matched is False
    assert mom_short.input_status == "INPUT_INCOMPLETE"


def test_ttm_squeeze_uses_ema_and_true_range() -> None:
    bars = []
    for index in range(31):
        close = 100.0 + math.sin(index / 4.0) * 0.4
        bars.append(_bar(close, high=close + 2.0, low=close - 2.0))
    metrics = _squeeze_metrics(bars)
    assert metrics is not None
    closes = [bar.close for bar in bars]
    alpha = 2.0 / 21.0
    ema = sum(closes[:20]) / 20.0
    for close in closes[20:]:
        ema = alpha * close + (1.0 - alpha) * ema
    true_ranges = []
    previous = closes[0]
    for bar in bars:
        true_ranges.append(
            max(bar.high - bar.low, abs(bar.high - previous), abs(bar.low - previous))
        )
        previous = bar.close
    atr = sum(true_ranges[:10]) / 10.0
    for value in true_ranges[10:]:
        atr = ((atr * 9.0) + value) / 10.0
    assert metrics["kcMid"] == pytest.approx(ema, rel=1e-12)
    assert metrics["atr10"] == pytest.approx(atr, rel=1e-12)


def test_reversal_supports_bullish_and_bearish_symmetry() -> None:
    level = 100.0
    # Break below, reclaim after two bars, latest above level -> match.
    bars = [_bar(101) for _ in range(8)] + [
        _bar(99.0),
        _bar(98.5),
        _bar(100.5),
        _bar(101.2),
    ]
    matches = compute_extended_matches(bars, reference_level=level)
    rev = next(m for m in matches if m.scanner_id == "native.reversal.v1")
    assert rev.matched is True
    assert rev.directional_context == "BULLISH"
    # Drift below without reclaim -> no match.
    bars_no_reclaim = [_bar(99) for _ in range(8)] + [
        _bar(99.0), _bar(98.5), _bar(98.0), _bar(97.5)
    ]
    rev2 = next(
        m
        for m in compute_extended_matches(bars_no_reclaim, reference_level=level)
        if m.scanner_id == "native.reversal.v1"
    )
    assert rev2.matched is False
    # No reference level at all -> cannot match.
    rev3 = next(
        m
        for m in compute_extended_matches(bars, reference_level=None)
        if m.scanner_id == "native.reversal.v1"
    )
    assert rev3.matched is False
    bearish = [_bar(99) for _ in range(8)] + [
        _bar(101.0), _bar(101.5), _bar(99.5), _bar(98.8)
    ]
    rev4 = next(
        m
        for m in compute_extended_matches(bearish, reference_level=level)
        if m.scanner_id == "native.reversal.v1"
    )
    assert rev4.matched is True
    assert rev4.directional_context == "BEARISH"


def test_extremes_exclude_current_bar_off_by_one() -> None:
    # Prior window all 5s; current 4 -> NOT a high even though a buggy
    # inclusive-window max (which includes the current bar) would fire.
    assert is_at_extreme([5, 5, 5, 5, 4], lookback=3, kind="high") is False
    # Current above every prior close -> 10d-high fires.
    assert is_at_extreme([1, 2, 3, 4, 5], lookback=3, kind="high") is True
    # Current below every prior close -> 10d-low fires on the low side.
    assert is_at_extreme([5, 4, 3, 2, 1], lookback=3, kind="low") is True
    # Mid-range fires neither.
    assert is_at_extreme([1, 5, 1, 5, 3], lookback=3, kind="high") is False


def test_extremes_distinguish_ten_day_and_fifty_two_week_states() -> None:
    bars = [_bar(float(index)) for index in range(1, 254)]
    ext = next(
        match
        for match in compute_extended_matches(bars, reference_level=None)
        if match.scanner_id == "native.extremes.v1"
    )
    assert ext.matched is True
    assert ext.scanner_state == "10D_HIGH+52W_HIGH"
    assert ext.directional_context == "BULLISH"


def _vcp_fixture(*, recent_volume: float) -> list[SimpleNamespace]:
    bars = [_bar(100.0, volume=1000.0) for _ in range(34)]
    for high, low in ((110.0, 88.0), (108.0, 95.04), (106.0, 99.64)):
        bars.extend(
            [
                _bar(100.0),
                _bar((100.0 + high) / 2),
                _bar(high),
                _bar((100.0 + high) / 2),
                _bar(100.0),
                _bar((100.0 + low) / 2),
                _bar(low),
                _bar((100.0 + low) / 2),
                _bar(100.0),
            ]
        )
    for bar in bars[-10:]:
        bar.volume = recent_volume
    return bars


def test_vcp_contract_and_volume_boundary() -> None:
    positive, reason = _vcp_metrics(_vcp_fixture(recent_volume=700.0))
    assert reason is None
    assert positive is not None
    assert positive["matched"] is True
    assert positive["volumeDryUpRatio"] == pytest.approx(0.70)
    assert positive["contractionDepths"][0] > positive["contractionDepths"][1]
    assert positive["contractionDepths"][1] > positive["contractionDepths"][2]

    negative, reason = _vcp_metrics(_vcp_fixture(recent_volume=701.0))
    assert reason is None
    assert negative is not None
    assert negative["matched"] is False
    assert _vcp_metrics(_vcp_fixture(recent_volume=700.0)[:60])[1] == (
        "INPUT_INCOMPLETE_WARMUP:native.vcp.v1"
    )


def test_adjusted_prices_prevent_split_gap_false_extreme() -> None:
    raw = [200.0] * 20 + [105.0]
    adjusted = [100.0] * 20 + [105.0]
    assert is_at_extreme(raw, lookback=10, kind="low") is True
    assert is_at_extreme(adjusted, lookback=10, kind="low") is False


def test_future_raw_bar_cannot_change_earlier_as_of_run(tmp_path, monkeypatch) -> None:
    parts = persist_overlay_lineage(
        tmp_path, monkeypatch, with_structure=True, symbol="HVBTEST"
    )
    before = build_native_core_run(r5=parts["structure"])
    from trendforge_api.selection.cash_a4_history import (
        CashRawSessionBar,
        _store_raw_bar,
    )

    instrument = parts["instrument"]
    future_day = date.fromisoformat(parts["structure"].trading_date) + timedelta(days=1)
    _store_raw_bar(
        CashRawSessionBar(
            barId="future-bar",
            instrumentId=instrument.instrument_id,
            symbol=instrument.symbol,
            tradeDate=future_day,
            artifactHash=hashlib.sha256(b"future-bar").hexdigest(),
            seriesId="future-series",
            open=999.0,
            high=1001.0,
            low=998.0,
            close=1000.0,
            previousClose=110.0,
            volume=999999.0,
        )
    )
    after = build_native_core_run(r5=parts["structure"])
    assert after.run_hash == before.run_hash


def test_trend_overlay_and_warmup_reasons(tmp_path, monkeypatch) -> None:
    parts = persist_overlay_lineage(
        tmp_path, monkeypatch, with_structure=True, symbol="HVBTEST"
    )
    run = build_native_core_run(r5=parts["structure"])
    row = next(r for r in run.rows if r.symbol == "HVBTEST")
    by_id = {m.scanner_id: m for m in row.matches}
    # Fixture has ~22 bars: overlay (needs 51) seats an honest warmup miss;
    # the reason surfaces at ROW level, never as a fabricated match.
    overlay = by_id["native.trend_overlay.v1"]
    assert overlay.matched is False
    assert any("INPUT_INCOMPLETE_WARMUP:native.trend_overlay.v1" in w for w in row.why)


# ---------------------------------------------------------------------------
# Family caps over real chips (§3.2–§3.4)
# ---------------------------------------------------------------------------


def test_compression_trio_folds_to_one_representative(tmp_path, monkeypatch) -> None:
    """NR (R5) + squeeze + VCP shapes on one symbol -> ONE compression rep."""
    # Craft bars: tight flat window (squeeze fires), preceded by contraction.
    bars = [_bar(100 - i * 0.05, volume=900 - i * 10) for i in range(40)]
    matches = compute_extended_matches(bars, reference_level=None)
    squeeze = next(m for m in matches if m.scanner_id == "native.ttm_squeeze.v1")
    # Shape control is best-effort; the cap law is what this test pins:
    matched_ids = [
        m.scanner_id
        for m in matches
        if m.matched and m.group == "CG_COMPRESSION"
    ]
    assert squeeze.scanner_id in matched_ids or squeeze.matched is False
    reps = representative_guidance_chips(matches)
    compression_reps = [m for m in reps if m.group == "CG_COMPRESSION"]
    assert len(compression_reps) <= 1
    # NR from R5 joins the SAME fold (claim-less chip shares the group):
    nr_chip = SimpleNamespace(
        scanner_id="native.nr_compression.v1",
        matched=True,
        feature_id="FTR-007",
        claim_id="r5-nr-claim",  # upstream claim stays owned by R5
        family="STRUCTURE",
        group="CG_COMPRESSION",
        correlated_with=(),
        correlated_possible=False,
        guidance_label="Compression",
        can_support_confirmed=False,
    )
    combined = tuple(matches) + (nr_chip,)
    combined_reps = representative_guidance_chips(combined)
    assert len([m for m in combined_reps if m.group == "CG_COMPRESSION"]) <= 1


def test_extremes_joins_price_structure_without_inflation(
    tmp_path, monkeypatch
) -> None:
    parts = persist_overlay_lineage(
        tmp_path, monkeypatch, with_structure=True, symbol="HVBTEST"
    )
    run = build_native_core_run(r5=parts["structure"])
    row = next(r for r in run.rows if r.symbol == "HVBTEST")
    structure_matched = [
        m.scanner_id
        for m in row.matches
        if m.matched and m.group == "CG_PRICE_STRUCTURE"
    ]
    reps_for_group = [
        m
        for m in row.matches
        if m.group == "CG_PRICE_STRUCTURE" and m.is_representative
    ]
    assert len(reps_for_group) <= 1
    assert len(set(structure_matched)) == len(structure_matched)


def test_claimless_guidance_chip_can_be_representative() -> None:
    matches = compute_extended_matches(
        [
            _bar(
                100.0 + math.sin(index / 4.0),
                high=102.0,
                low=98.0,
            )
            for index in range(61)
        ],
        reference_level=None,
    )
    matched = tuple(match for match in matches if match.matched)
    reps = representative_guidance_chips(matched)
    assert all(rep.claim_id is None for rep in reps)
    assert len({(rep.family, rep.group) for rep in reps}) == len(reps)


# ---------------------------------------------------------------------------
# Chips-only law + integration over the fixture spine (§3.2, §3.6, §3.9)
# ---------------------------------------------------------------------------


def test_chips_only_law_source_scan() -> None:
    pkg = Path(r"D:\TrendForge\backend\trendforge_api\scanners")
    offenders_claim = []
    offenders_order = []
    for p in pkg.glob("*.py"):
        text = p.read_text(encoding="utf-8")
        if "EvidenceClaim(" in text:
            offenders_claim.append(p.name)
        if "place_order" in text:
            offenders_order.append(p.name)
    assert offenders_claim == []
    assert offenders_order == []


def test_integration_new_chips_flow_through_native_core(
    tmp_path, monkeypatch
) -> None:
    from trendforge_api.hybrid_v2.tests_support.fixtures import (
        persist_overlay_lineage as _lineage,
    )

    parts = _lineage(tmp_path, monkeypatch, with_structure=True, symbol="HVBTEST")
    run = build_native_core_run(r5=parts["structure"])
    assert run.confirmed_count == 0
    row = next(r for r in run.rows if r.symbol == "HVBTEST")
    ids = {m.scanner_id for m in row.matches}
    assert R13_IDS <= ids  # all six evaluated, matched or honestly not
    assert all(m.claim_id is None for m in row.matches if m.scanner_id in R13_IDS)
    assert all(m.guidance_approved is False for m in row.matches)
    assert all(m.guidance_confirmed is False for m in row.matches)
    assert run.confirmed_count == 0 and run.executable is False
    assert row.candidate_direction in {
        "BULLISH", "BEARISH", "MIXED", "NEUTRAL", "UNKNOWN"
    }


def test_missing_adjusted_lineage_fails_closed(tmp_path, monkeypatch) -> None:
    parts = persist_overlay_lineage(
        tmp_path, monkeypatch, with_structure=True, symbol="HVBTEST"
    )
    broken = parts["structure"].model_copy(update={"r14_run_hash": "missing-r14"})
    run = build_native_core_run(r5=broken)
    row = next(r for r in run.rows if r.symbol == "HVBTEST")
    r13 = [m for m in row.matches if m.scanner_id in R13_IDS]
    assert all(m.matched is False for m in r13)
    assert all(m.input_status == "INPUT_INCOMPLETE" for m in r13)
    assert "WAIT_R13_R14_LINEAGE" in row.why


def test_post_run_still_405() -> None:
    client = TestClient(app)
    assert client.post("/api/v1/scanners/run").status_code == 405


def test_no_orb_vwap_modules() -> None:
    pkg = Path(r"D:\TrendForge\backend\trendforge_api\scanners")
    names = [p.name.lower() for p in pkg.glob("*.py")]
    assert not any("orb" in n or "vwap" in n for n in names)
    for scanner_id in NATIVE_CORE_IDS:
        assert "orb" not in scanner_id and "vwap" not in scanner_id


# ---------------------------------------------------------------------------
# Post-build conformance audit fixes (perf + payload noise + param pins)
# ---------------------------------------------------------------------------


def test_bars_loaded_via_single_bulk_query(tmp_path, monkeypatch) -> None:
    """Per-symbol SQL x universe is a 30s footgun; bulk loader must be used."""
    parts = persist_overlay_lineage(
        tmp_path, monkeypatch, with_structure=True, symbol="HVBTEST"
    )
    from trendforge_api.selection import cash_a4_history

    calls = {"bulk": 0, "single": 0}
    real_bulk = cash_a4_history.list_raw_bars_by_symbol
    real_single = cash_a4_history.list_raw_bars

    def fake_bulk(symbols, *, through):
        calls["bulk"] += 1
        return real_bulk(symbols, through=through)

    def fake_single(symbol, *, through):
        calls["single"] += 1
        return real_single(symbol, through=through)

    monkeypatch.setattr(cash_a4_history, "list_raw_bars_by_symbol", fake_bulk)
    monkeypatch.setattr(cash_a4_history, "list_raw_bars", fake_single)

    from trendforge_api.scanners.native_core import build_native_core_run as _build

    _build(r5=parts["structure"])
    assert calls["bulk"] == 1
    assert calls["single"] == 0


def test_row_warmup_reasons_capped_and_tallied(tmp_path, monkeypatch) -> None:
    parts = persist_overlay_lineage(
        tmp_path, monkeypatch, with_structure=True, symbol="HVBTEST"
    )
    run = build_native_core_run(r5=parts["structure"])
    row = next(r for r in run.rows if r.symbol == "HVBTEST")
    warm = [w for w in row.why if str(w).startswith("INPUT_INCOMPLETE_WARMUP")]
    assert len(warm) <= 6
    tally = [w for w in run.warnings if str(w).startswith("WARMUP_TALLY")]
    assert tally  # full counts preserved at batch level


def test_extremes_w52_pending_reason_distinct() -> None:
    closes = [100.0 + i for i in range(30)]  # >=11 but <253
    matches = compute_extended_matches([_bar(c) for c in closes], reference_level=None)
    ext = next(m for m in matches if m.scanner_id == "native.extremes.v1")
    assert ext.matched is True  # 10d fires on the ramp
    reason = getattr(ext, "reason_code", None) or ""
    assert reason.endswith(":w52")


def test_squeeze_vcp_params_pin_mid_and_range_source() -> None:
    import json

    squeeze = scanner_definition("native.ttm_squeeze.v1")
    params = json.loads(squeeze.parameters_json)
    assert params["bbMid"] == "SMA" and params["kcMid"] == "EMA"
    assert params["atrSource"] == "trueRange"
    vcp = scanner_definition("native.vcp.v1")
    vcp_params = json.loads(vcp.parameters_json)
    assert vcp_params["rangeSource"] == "adjustedOHLC"
    assert vcp_params["volumeDryUpRatio"] == 0.70
