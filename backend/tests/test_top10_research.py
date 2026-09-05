"""Top-10 BUY/SELL research board tests: vetoes, direction source, honesty."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from trendforge_api import storage
from trendforge_api.selection.contracts import EvidenceDirection, SelectionState
from trendforge_api.selection.r6_live import build_r6_enrichment
from trendforge_api.selection.top10_research import (
    BOARD_SIZE,
    Top10ResearchBoardV1,
    build_top10_research,
)
from tests.test_r6_live import (
    DECISION_AT,
    TRADING_DATE,
    _deal,
    _hash,
    _loader,
    _r14,
    _signals,
    _spine,
)


def _enrichment(tmp_path, monkeypatch, specs, ca_by_candidate=None):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-board.db")
    bundle, attention = _spine(specs)
    return build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, ca_by_candidate or {}),
        signals=_signals(),
        loader=_loader(),
        built_at=DECISION_AT,
    )


def test_t4b_direction_comes_from_r2_evidence_direction(tmp_path, monkeypatch) -> None:
    enrichment = _enrichment(
        tmp_path,
        monkeypatch,
        [
            ("cand-aaa", "AAA", EvidenceDirection.BULLISH),
            ("cand-bbb", "BBB", EvidenceDirection.BEARISH),
            ("cand-nnn", "NNN", EvidenceDirection.NEUTRAL),
        ],
    )
    board = build_top10_research(enrichment=enrichment)
    assert [entry.symbol for entry in board.buy] == ["AAA"]
    assert [entry.symbol for entry in board.sell] == ["BBB"]
    assert all(entry.symbol != "NNN" for entry in (*board.buy, *board.sell))
    for entry in (*board.buy, *board.sell):
        assert entry.can_unlock_confirmed is False
        assert entry.research_state is SelectionState.WAIT


def test_t5_wait_ca_and_ban_vetoed_from_boards(tmp_path, monkeypatch) -> None:
    enrichment = _enrichment(
        tmp_path,
        monkeypatch,
        [
            ("cand-aaa", "AAA", EvidenceDirection.BULLISH),
            ("cand-bbb", "BBB", EvidenceDirection.BULLISH),
            ("cand-ccc", "CCC", EvidenceDirection.BEARISH),
        ],
        ca_by_candidate={"cand-bbb": "WAIT_CA"},
    )
    # Mark CCC banned via restriction state on its R2 row.
    rows = list(enrichment.rows)
    patched_rows = []
    for row in rows:
        if row.symbol == "CCC":
            patched_rows.append(row.model_copy(update={"restriction_state": "FNO_BAN"}))
        else:
            patched_rows.append(row)
    enrichment = enrichment.model_copy(update={"rows": tuple(patched_rows)})

    board = build_top10_research(enrichment=enrichment)
    symbols_on_board = {entry.symbol for entry in (*board.buy, *board.sell)}
    assert symbols_on_board == {"AAA"}
    assert board.vetoed_count == 2  # WAIT_CA + F&O ban


def test_t5_reject_row_never_reaches_boards(tmp_path, monkeypatch) -> None:
    enrichment = _enrichment(
        tmp_path,
        monkeypatch,
        [("cand-aaa", "AAA", EvidenceDirection.BULLISH)],
    )
    rejected = enrichment.model_copy(
        update={
            "rows": tuple(
                row.model_copy(
                    update={
                        "r2_public_state": SelectionState.REJECT,
                        "attention_priority": None,
                        "display_score": None,
                    }
                )
                for row in enrichment.rows
            )
        }
    )
    board = build_top10_research(enrichment=rejected)
    assert board.buy == ()
    assert board.vetoed_count == 1


def test_t3_off_radar_deal_names_cannot_enter_boards(tmp_path, monkeypatch) -> None:
    """A large deal for a symbol that is not on R2 cannot create a candidate."""
    from trendforge_api.fii_stock_signals import (
        FIIStockSignalsSnapshot,
        LargeDealSignal,
    )

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-t3.db")
    bundle, attention = _spine([("cand-aaa", "AAA", EvidenceDirection.BULLISH)])
    off_radar_snapshot = FIIStockSignalsSnapshot(
        generated_at=DECISION_AT,
        large_deals=[
            LargeDealSignal(
                symbol="OFFRADAR",
                side="BUY",
                client="BIG FII NAME",
                quantity=999999,
                price=10.0,
                value=9999990.0,
                deal_type="BLOCK",
                date="2026-08-13",
                source_key="nse_block_deal",
            ),
            _deal("AAA", side="BUY", client="NAMED CLIENT"),
        ],
    )
    enrichment = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {}),
        signals=off_radar_snapshot,
        loader=_loader(),
        built_at=DECISION_AT,
    )
    assert all(row.symbol != "OFFRADAR" for row in enrichment.rows)
    board = build_top10_research(enrichment=enrichment)
    assert {entry.symbol for entry in board.buy} == {"AAA"}


def test_board_caps_at_ten_and_reports_fewer_honestly(tmp_path, monkeypatch) -> None:
    specs = [
        (f"cand-{index:03d}", f"S{index:03d}", EvidenceDirection.BEARISH)
        for index in range(12)
    ]
    enrichment = _enrichment(tmp_path, monkeypatch, specs)
    assert len(enrichment.rows) == 12
    board = build_top10_research(enrichment=enrichment)
    assert len(board.sell) == BOARD_SIZE
    assert len(board.buy) == 0  # no bullish evidence exists; no backfill
    assert board.calibration == "RESEARCH_SHORTLIST_NOT_CONFIRMED"


def test_t8_board_ceiling_validators(tmp_path, monkeypatch) -> None:
    enrichment = _enrichment(
        tmp_path, monkeypatch, [("cand-aaa", "AAA", EvidenceDirection.BULLISH)]
    )
    board = build_top10_research(enrichment=enrichment)
    payload = board.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError):
        Top10ResearchBoardV1.model_validate({**payload, "canUnlockConfirmed": True})
    with pytest.raises(ValidationError):
        Top10ResearchBoardV1.model_validate({**payload, "sourceActivationReady": True})
    entries = list(payload["buy"])
    entries[0]["researchState"] = "CONFIRMED"
    with pytest.raises(ValidationError):
        Top10ResearchBoardV1.model_validate({**payload, "buy": entries})
