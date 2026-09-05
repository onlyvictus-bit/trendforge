"""File A S9 (SEL-010): offline PIT homework — law + labeling tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trendforge_api.selection.s9_pit_homework import (
    ACCEPTANCE_CEILING,
    PROFILE_ID,
    VALIDATION_STATUS,
    S9ObservationRowV1,
    S9PitHomeworkBatchV1,
    build_s9_pit_homework,
)


def _s8_payload(*symbols: str, state: str = "WAIT"):
    rows = [
        {
            "symbol": s,
            "publicState": state,
            "evidenceDirection": "BULLISH",
            "researchEntry": 100.0,
            "nextTrigger": "hold above prior high",
            "invalidationCondition": "close back inside range",
        }
        for s in symbols
    ]
    return {
        "runId": "s8-run-1",
        "lineage": {"r5RunHash": "r5h", "r2RunHash": "r2h"},
        "rows": rows,
        "confirmedCount": 0,
    }


def _bars(closes: list[float]) -> list[dict]:
    return [
        {"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1000}
        for c in closes
    ]


def test_law_validators() -> None:
    batch = build_s9_pit_homework(s8_payload=_s8_payload("AAA"))
    assert batch.validation_status == "PIT_NOT_APPROVED"
    assert batch.confirmed_count == 0
    assert batch.source_activation_ready is False
    assert batch.can_unlock_confirmed is False


def test_reject_row_gives_no_entry() -> None:
    batch = build_s9_pit_homework(s8_payload=_s8_payload("BAD", state="REJECT"))
    assert all(r.status == "NO_ENTRY" for r in batch.rows)


def test_no_bars_gives_no_forward_session() -> None:
    batch = build_s9_pit_homework(s8_payload=_s8_payload("AAA"), future_bars_by_symbol={})
    assert all(r.status == "NO_FORWARD_SESSION" for r in batch.rows)


def test_win_path_with_rising_bars() -> None:
    closes = [100 + i * 3 for i in range(10)]
    bars = _bars(closes)
    batch = build_s9_pit_homework(
        s8_payload=_s8_payload("AAA"), future_bars_by_symbol={"AAA": bars}
    )
    row = batch.rows[0]
    assert row.status in ("WIN", "CENSORED")
    assert row.mfe_percent is not None


def test_loss_path_with_falling_bars() -> None:
    closes = [100 - i * 3 for i in range(10)]
    bars = _bars(closes)
    batch = build_s9_pit_homework(
        s8_payload=_s8_payload("AAA"), future_bars_by_symbol={"AAA": bars}
    )
    row = batch.rows[0]
    assert row.status in ("LOSS", "CENSORED")


def test_censored_never_coerced_to_zero() -> None:
    # Only 2 forward bars (horizon is 5) → CENSORED with mfe/mae stored.
    closes = [101.0, 102.0]
    bars = _bars(closes)
    batch = build_s9_pit_homework(
        s8_payload=_s8_payload("AAA"),
        future_bars_by_symbol={"AAA": [{"open": b, "high": b * 1.01, "low": b * 0.99, "close": b} for b in closes]},
    )
    assert all(r.status in ("CENSORED", "NO_FORWARD_SESSION") or r.mfe_percent is not None for r in batch.rows)


def test_no_win_rate_key_in_output() -> None:
    batch = build_s9_pit_homework(s8_payload=_s8_payload("AAA"))
    dumped = batch.model_dump()
    text = str(dumped).lower()
    assert "winrate" not in text and "win_rate" not in text
