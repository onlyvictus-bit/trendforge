"""Acceptance tests for strike_explorer and expiry_prediction BFFs.

Contract: prompt section 8. Without a quality-passed same-expiry chain
snapshot both tools fail closed to WAIT_CHAIN (503). With one, the
ladder carries spread %, walls carry persistence, max pain stays a
reference, the hero-zero JSON keeps prob_touch_P null and can_confirm
false, and spread above 8% raises HARD_BLOCK_SPREAD.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.options_intelligence.bff import (
    build_expiry_range_batch,
    build_strike_explorer_batch,
)
from trendforge_api.options_intelligence.hard_blocks import evaluate_hard_blocks
from trendforge_api.options_intelligence.iv_recorder import record_chain_snapshot

client = TestClient(app)

EXPIRY = "2026-09-29"


@pytest.fixture()
def chain_db(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "market.db")
    storage._INITIALIZED_DB_PATHS.clear()
    return tmp_path


def _rows(spread_pct: float = 1.0) -> list[dict]:
    mid = 100.0
    half = mid * spread_pct / 200.0

    def leg(strike: float, right: str, oi: float) -> dict:
        return {
            "expiry": EXPIRY,
            "strike": strike,
            "right": right,
            "bid": round(mid - half, 4),
            "ask": round(mid + half, 4),
            "ltp": mid,
            "openInterest": oi,
            "volume": 5000.0,
            "impliedVolatility": 14.0,
        }

    return [
        leg(24500.0, "CE", 900_000),
        leg(24500.0, "PE", 300_000),
        leg(25000.0, "CE", 1_400_000),
        leg(25000.0, "PE", 1_100_000),
        leg(25500.0, "CE", 400_000),
        leg(25500.0, "PE", 800_000),
    ]


def test_fails_closed_without_chain_snapshot(chain_db) -> None:
    with pytest.raises(Exception) as exc:
        build_strike_explorer_batch(underlying="NIFTY", expiry=EXPIRY)
    assert getattr(exc.value, "code", "") == "WAIT_CHAIN"
    response = client.get(
        f"/api/v1/tools/strike_explorer?underlying=NIFTY&expiry={EXPIRY}"
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "WAIT_CHAIN"
    expiry_response = client.get(
        f"/api/v1/tools/expiry_prediction?underlying=NIFTY&expiry={EXPIRY}"
    )
    assert expiry_response.status_code == 503


def test_ladder_walls_pain_and_hero_zero(chain_db) -> None:
    record_chain_snapshot(
        underlying="NIFTY",
        expiry=EXPIRY,
        quality_state="CHAIN_OK",
        spot=24950.0,
        payload={"rows": _rows(), "expectedStrikeCount": 3},
    )
    batch = build_strike_explorer_batch(underlying="NIFTY", expiry=EXPIRY)
    assert batch.quality_state == "CHAIN_OK"
    assert len(batch.ladder) == 6
    assert batch.call_wall.strike == 25000.0
    assert batch.put_wall.strike == 25000.0
    assert batch.max_pain_reference is not None
    assert "DEALER" in batch.gamma_label or batch.gamma_label.startswith("UNSIGNED")
    for row in batch.ladder:
        assert row.spread_pct is not None and row.spread_pct < 8.0
        assert row.cash_gamma_proxy is not None

    expiry_batch = build_expiry_range_batch(underlying="NIFTY", expiry=EXPIRY)
    assert expiry_batch.range_low is not None and expiry_batch.range_high is not None
    assert expiry_batch.is_tuesday_expiry is True
    # 2026-09-29 is the LAST Tuesday of September 2026 -> mega expiry.
    assert expiry_batch.is_mega_expiry is True
    assert expiry_batch.mega_stress_tag.startswith("MEGA_EXPIRY")
    assert expiry_batch.physical_block_active_from is not None
    hz = expiry_batch.hero_zero
    assert hz is not None
    assert hz["inferred"]["probTouchP"] is None
    assert hz["authority"] == "CONTEXT_ONLY" and hz["canConfirm"] is False
    assert hz["state"] in {"WATCH", "WAIT"}
    assert expiry_batch.state_ceiling in {"WATCH", "WAIT"}


def test_spread_above_limit_raises_hard_block(chain_db) -> None:
    record_chain_snapshot(
        underlying="BANKNIFTY",
        expiry="2026-09-30",
        quality_state="CHAIN_OK",
        spot=51000.0,
        payload={"rows": _rows(spread_pct=12.0), "expectedStrikeCount": 3},
    )
    blockers = evaluate_hard_blocks(symbol="BANKNIFTY", max_spread_pct=12.0)
    assert "HARD_BLOCK_SPREAD" in [b.code for b in blockers]
    batch = build_strike_explorer_batch(underlying="BANKNIFTY", expiry="2026-09-30")
    assert "HARD_BLOCK_SPREAD" in batch.blockers
    assert batch.state_ceiling == "WAIT"
    assert batch.quality_state == "WAIT_CHAIN"


def test_physical_block_and_mega_expiry_flag(chain_db) -> None:
    import datetime as dt

    record_chain_snapshot(
        underlying="RELIANCE",
        expiry=EXPIRY,
        quality_state="CHAIN_OK",
        spot=3000.0,
        payload={"rows": _rows(), "expectedStrikeCount": 3},
    )
    batch = build_expiry_range_batch(
        underlying="RELIANCE", expiry=EXPIRY, today=dt.date(2026, 9, 25)
    )
    assert batch.is_mega_expiry is True
    assert batch.mega_stress_tag.startswith("MEGA_EXPIRY")
    assert batch.physical_block_active_from is not None
    assert batch.dte_calendar_days == 4


def test_eod_fo_option_rows_unlock_wait_chain_not_503(chain_db) -> None:
    from trendforge_api.options_intelligence.eod_chain import (
        persist_eod_option_chains_from_fo,
    )

    fo_rows = []
    for strike, ce_oi, pe_oi in (
        (24500.0, 900_000, 300_000),
        (25000.0, 1_400_000, 1_100_000),
        (25500.0, 400_000, 800_000),
    ):
        for right, oi in (("CE", ce_oi), ("PE", pe_oi)):
            fo_rows.append(
                {
                    "symbol": "NIFTY",
                    "instrument": "IDO",
                    "expiry": EXPIRY,
                    "strike": strike,
                    "optionType": right,
                    "close": 120.0,
                    "openInterest": oi,
                    "volume": 50,
                    "underlyingPrice": 24950.0,
                }
            )
    written = persist_eod_option_chains_from_fo(fo_rows, symbols={"NIFTY"})
    assert written["written"] == 1
    batch = build_strike_explorer_batch(underlying="NIFTY", expiry=EXPIRY)
    assert batch.quality_state == "CHAIN_EOD_OI"
    assert batch.state_ceiling == "WAIT"
    assert batch.call_wall.strike == 25000.0
    assert batch.max_pain_reference is not None


def test_post_is_rejected_on_all_four_tools() -> None:
    for tool in ("oi_analysis", "oi_tracker", "strike_explorer", "expiry_prediction"):
        assert client.post(f"/api/v1/tools/{tool}").status_code == 405
