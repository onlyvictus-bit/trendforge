"""CROSS-015 / TDG-GAP-022 unified tradability gate tests."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from trendforge_api.selection.tradability import (
    RestrictionSourceV1,
    SourceEvidenceState,
    TradabilityOutcome,
    build_tradability_batch,
    evaluate_tradability,
)


NOW = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)


def _source(key: str, rows=(), *, state=SourceEvidenceState.POPULATED):
    return RestrictionSourceV1(
        sourceKey=key,
        evidenceState=state,
        dataDate="2026-09-03",
        parserVersion="test-v1",
        contentHash=(key[0] * 64),
        rows=tuple(rows),
    )


def _clear_nse_sources():
    return {
        "nse_trade_to_trade": _source(
            "nse_trade_to_trade", state=SourceEvidenceState.VALID_EMPTY
        ),
        "nse_asm": _source("nse_asm", state=SourceEvidenceState.VALID_EMPTY),
        "nse_gsm": _source("nse_gsm", state=SourceEvidenceState.VALID_EMPTY),
        "nse_esm": _source("nse_esm", state=SourceEvidenceState.VALID_EMPTY),
        "nse_price_bands": _source(
            "nse_price_bands",
            rows=({"symbol": "AAA", "lowerBand": 90, "upperBand": 110},),
        ),
        "nse_market_status": _source(
            "nse_market_status", rows=({"market": "Capital Market", "status": "Open"},)
        ),
        "nse_equity_universe": _source(
            "nse_equity_universe", rows=({"symbol": "AAA", "series": "EQ", "active": 1},)
        ),
    }


def test_clear_swing_symbol_passes_without_creating_a_vote() -> None:
    result = evaluate_tradability(
        symbol="AAA",
        profile_id="PRF-003",
        decision_at=NOW,
        sources=_clear_nse_sources(),
        current_price=100,
    )
    assert result.outcome is TradabilityOutcome.PASS
    assert result.can_confirm is False
    assert result.vote_eligible is False


def test_t2t_rejects_intraday_and_waits_swing() -> None:
    sources = _clear_nse_sources()
    sources["nse_trade_to_trade"] = _source(
        "nse_trade_to_trade", ({"symbol": "AAA", "t2t": True},)
    )
    intraday = evaluate_tradability(
        symbol="AAA", profile_id="PRF-001", decision_at=NOW, sources=sources
    )
    swing = evaluate_tradability(
        symbol="AAA", profile_id="PRF-003", decision_at=NOW, sources=sources
    )
    assert intraday.outcome is TradabilityOutcome.REJECT
    assert intraday.primary_reason == "REJECT_T2T_INTRADAY"
    assert swing.outcome is TradabilityOutcome.WAIT
    assert "WAIT_T2T_DELIVERY_ONLY" in swing.reason_codes


def test_surveillance_is_fail_closed_per_symbol() -> None:
    sources = _clear_nse_sources()
    sources["nse_asm"] = _source(
        "nse_asm", ({"symbol": "AAA", "stage": "Stage I"},)
    )
    result = evaluate_tradability(
        symbol="AAA", profile_id="PRF-003", decision_at=NOW, sources=sources
    )
    assert result.outcome is TradabilityOutcome.WAIT
    assert "WAIT_ASM_ACTIVE" in result.reason_codes


def test_high_gsm_and_esm_stages_reject_intraday() -> None:
    for key, row, reason in (
        ("nse_gsm", {"symbol": "AAA", "stage": "Stage IV"}, "REJECT_GSM_STAGE"),
        ("nse_esm", {"symbol": "AAA", "stage": "Stage 2"}, "REJECT_ESM_STAGE"),
    ):
        sources = _clear_nse_sources()
        sources[key] = _source(key, (row,))
        result = evaluate_tradability(
            symbol="AAA", profile_id="PRF-001", decision_at=NOW, sources=sources
        )
        assert result.outcome is TradabilityOutcome.REJECT
        assert reason in result.reason_codes


def test_missing_stale_malformed_and_conflicting_sources_never_pass() -> None:
    for state in (
        SourceEvidenceState.MISSING,
        SourceEvidenceState.STALE,
        SourceEvidenceState.MALFORMED,
        SourceEvidenceState.CONFLICTING,
    ):
        sources = _clear_nse_sources()
        sources["nse_esm"] = _source("nse_esm", state=state)
        result = evaluate_tradability(
            symbol="AAA", profile_id="PRF-003", decision_at=NOW, sources=sources
        )
        assert result.outcome is TradabilityOutcome.WAIT
        assert result.can_confirm is False


def test_valid_empty_is_different_from_missing() -> None:
    clear = evaluate_tradability(
        symbol="AAA", profile_id="PRF-003", decision_at=NOW, sources=_clear_nse_sources()
    )
    sources = _clear_nse_sources()
    sources["nse_asm"] = _source("nse_asm", state=SourceEvidenceState.MISSING)
    missing = evaluate_tradability(
        symbol="AAA", profile_id="PRF-003", decision_at=NOW, sources=sources
    )
    assert clear.component("ASM").outcome is TradabilityOutcome.PASS
    assert missing.component("ASM").outcome is TradabilityOutcome.WAIT


def test_locked_price_band_rejects_but_near_band_waits() -> None:
    sources = _clear_nse_sources()
    locked = evaluate_tradability(
        symbol="AAA", profile_id="PRF-001", decision_at=NOW, sources=sources,
        current_price=110,
    )
    near = evaluate_tradability(
        symbol="AAA", profile_id="PRF-001", decision_at=NOW, sources=sources,
        current_price=109.5,
    )
    assert locked.outcome is TradabilityOutcome.REJECT
    assert "REJECT_PRICE_BAND_LOCKED" in locked.reason_codes
    assert near.outcome is TradabilityOutcome.WAIT
    assert "WAIT_PRICE_BAND_PROXIMITY" in near.reason_codes


def test_official_no_band_classification_passes_without_fake_boundaries() -> None:
    sources = _clear_nse_sources()
    sources["nse_price_bands"] = _source(
        "nse_price_bands",
        ({"symbol": "AAA", "bandPercent": None, "hasPriceBand": False},),
    )
    result = evaluate_tradability(
        symbol="AAA",
        profile_id="PRF-003",
        decision_at=NOW,
        sources=sources,
        current_price=100,
    )
    assert result.component("PRICE_BAND").outcome is TradabilityOutcome.PASS
    assert result.component("PRICE_BAND").reason_code == "PASS_PRICE_BAND_NOT_APPLICABLE"


def test_market_halt_rejects_and_unknown_status_waits() -> None:
    halted_sources = _clear_nse_sources()
    halted_sources["nse_market_status"] = _source(
        "nse_market_status", ({"market": "Capital Market", "status": "Closed"},)
    )
    halted = evaluate_tradability(
        symbol="AAA", profile_id="PRF-001", decision_at=NOW, sources=halted_sources
    )
    unknown_sources = _clear_nse_sources()
    unknown_sources["nse_market_status"] = _source(
        "nse_market_status", state=SourceEvidenceState.MISSING
    )
    unknown = evaluate_tradability(
        symbol="AAA", profile_id="PRF-001", decision_at=NOW, sources=unknown_sources
    )
    assert halted.outcome is TradabilityOutcome.REJECT
    assert unknown.outcome is TradabilityOutcome.WAIT


def test_suspended_symbol_rejects_and_missing_master_row_waits() -> None:
    suspended_sources = _clear_nse_sources()
    suspended_sources["nse_equity_universe"] = _source(
        "nse_equity_universe", ({"symbol": "AAA", "active": 0},)
    )
    suspended = evaluate_tradability(
        symbol="AAA", profile_id="PRF-003", decision_at=NOW, sources=suspended_sources,
        current_price=100,
    )
    missing = evaluate_tradability(
        symbol="BBB", profile_id="PRF-003", decision_at=NOW,
        sources=_clear_nse_sources(), current_price=100,
    )
    assert suspended.outcome is TradabilityOutcome.REJECT
    assert "REJECT_SECURITY_SUSPENDED" in suspended.reason_codes
    assert missing.outcome is TradabilityOutcome.WAIT
    assert "WAIT_SECURITY_STATUS_SYMBOL_MISSING" in missing.reason_codes


def test_fno_ban_and_mwpl_apply_only_when_derivatives_are_used() -> None:
    sources = _clear_nse_sources()
    sources.update(
        {
            "nse_fno_ban": _source("nse_fno_ban", ({"symbol": "AAA", "isBanned": True},)),
            "nse_mwpl_percentages": _source(
                "nse_mwpl_percentages", ({"symbol": "AAA", "mwplPercent": 96},)
            ),
        }
    )
    cash = evaluate_tradability(
        symbol="AAA", profile_id="PRF-003", decision_at=NOW, sources=sources
    )
    derivative = evaluate_tradability(
        symbol="AAA", profile_id="PRF-001", decision_at=NOW, sources=sources,
        derivatives_used=True,
    )
    assert cash.component("FNO_BAN").outcome is TradabilityOutcome.NOT_APPLICABLE
    assert derivative.outcome is TradabilityOutcome.REJECT


def test_underlying_restriction_propagates_to_options() -> None:
    sources = _clear_nse_sources()
    sources["nse_gsm"] = _source(
        "nse_gsm", ({"symbol": "AAA", "stage": "Stage IV"},)
    )
    result = evaluate_tradability(
        symbol="AAA", profile_id="PRF-001", decision_at=NOW, sources=sources,
        derivatives_used=True,
    )
    assert result.outcome is TradabilityOutcome.REJECT
    assert result.applies_to_underlying is True


def test_batch_hash_is_deterministic_and_changes_with_restriction() -> None:
    clear = build_tradability_batch(
        symbols=("AAA", "BBB"), profile_id="PRF-003", decision_at=NOW,
        sources=_clear_nse_sources(),
    )
    repeated = build_tradability_batch(
        symbols=("BBB", "AAA"), profile_id="PRF-003", decision_at=NOW,
        sources=_clear_nse_sources(),
    )
    blocked_sources = _clear_nse_sources()
    blocked_sources["nse_asm"] = _source(
        "nse_asm", ({"symbol": "AAA", "stage": "Stage I"},)
    )
    blocked = build_tradability_batch(
        symbols=("AAA", "BBB"), profile_id="PRF-003", decision_at=NOW,
        sources=blocked_sources,
    )
    assert clear.run_hash == repeated.run_hash
    assert clear.run_hash != blocked.run_hash
    assert clear.rows[0].tradability_hash != blocked.rows[0].tradability_hash


def test_mc_x_without_typed_assessment_waits_instead_of_using_nse_rules() -> None:
    result = evaluate_tradability(
        symbol="GOLD", profile_id="PRF-005", decision_at=NOW, sources={}
    )
    assert result.outcome is TradabilityOutcome.WAIT
    assert result.primary_reason == "WAIT_MCX_CONTRACT_ASSESSMENT"
    assert all(component.market == "MCX" for component in result.components)


def test_read_only_routes_return_batch_and_symbol(monkeypatch) -> None:
    import trendforge_api.main as main

    batch = build_tradability_batch(
        symbols=("AAA",), profile_id="PRF-003", decision_at=NOW,
        sources=_clear_nse_sources(), prices_by_symbol={"AAA": 100},
    )
    monkeypatch.setattr(
        main,
        "_hash_matched_r5_or_503",
        lambda: SimpleNamespace(
            rows=(SimpleNamespace(symbol="AAA"),), built_at=NOW
        ),
    )
    monkeypatch.setattr(main, "build_tradability_batch", lambda **_: batch)
    client = TestClient(main.app)
    board = client.get("/api/v1/selection/tradability")
    symbol = client.get("/api/v1/selection/tradability/AAA")
    assert board.status_code == 200
    assert board.json()["runHash"] == batch.run_hash
    assert symbol.status_code == 200
    assert symbol.json()["tradabilityHash"] == batch.rows[0].tradability_hash
    assert client.post("/api/v1/selection/tradability").status_code == 405
