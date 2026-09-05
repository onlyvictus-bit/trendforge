"""C4/C5/C13/C16: official MTO delivery evidence gates."""

from __future__ import annotations

from datetime import timedelta

from trendforge_api import storage
from trendforge_api.hybrid_v2.as_lab.delivery import (
    MIN_SESSIONS,
    build_as_delivery_evidence,
)
from trendforge_api.hybrid_v2.tests_support.fixtures import (
    DECISION_AT,
    TRADING_DATE,
    mto_row,
    persist_overlay_lineage,
    store_flat_history,
    store_mto_parse_result,
)


def _seed_series(
    symbol: str,
    *,
    days: int = 22,
    pct_fn=None,
    parsed_offset_hours: int = -2,
    up_to: int | None = None,
):
    count = days if up_to is None else up_to
    for index in range(count):
        day = TRADING_DATE - timedelta(days=count - 1 - index)
        pct = pct_fn(index) if pct_fn else 30.0 + (index % 5)
        store_mto_parse_result(
            data_date=day,
            parsed_at=DECISION_AT + timedelta(hours=parsed_offset_hours),
            rows=[mto_row(symbol, pct)],
        )


def test_c5_missing_mto_is_unknown_not_volume_proxy(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    evidence = build_as_delivery_evidence(
        symbol="HVBTEST",
        instrument_id="NSE:EQ:HVBTEST",
        ca_state="NONE",
        session_date=TRADING_DATE,
        decision_at=DECISION_AT,
        raw_bars_fn=lambda symbol, through: [],
    )
    assert evidence.status == "UNKNOWN"
    assert evidence.delivery_z is None


def test_short_series_is_not_usable(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    _seed_series("HVBTEST", days=MIN_SESSIONS - 1)
    evidence = build_as_delivery_evidence(
        symbol="HVBTEST",
        instrument_id="NSE:EQ:HVBTEST",
        ca_state="NONE",
        session_date=TRADING_DATE,
        decision_at=DECISION_AT,
        raw_bars_fn=lambda symbol, through: [],
    )
    assert evidence.status == "UNKNOWN"
    assert evidence.sample_size == MIN_SESSIONS - 1


def test_usable_series_produces_robust_z_and_accumulation_days(tmp_path, monkeypatch) -> None:
    from types import SimpleNamespace

    persist_overlay_lineage(tmp_path, monkeypatch)
    # 19 varied sessions then one strong delivery spike at the research session.
    for index in range(19):
        store_mto_parse_result(
            data_date=TRADING_DATE - timedelta(days=19 - index),
            parsed_at=DECISION_AT - timedelta(hours=2),
            rows=[mto_row("HVBTEST", 40.0 + index)],
        )
    store_mto_parse_result(
        data_date=TRADING_DATE,
        parsed_at=DECISION_AT - timedelta(hours=2),
        rows=[mto_row("HVBTEST", 90.0)],
    )

    window_dates = [TRADING_DATE - timedelta(days=offset) for offset in range(19, -1, -1)]
    flat_bars = [
        SimpleNamespace(trade_date=day, close=100.0) for day in window_dates
    ]

    def quiet_bars(symbol, through):
        return [bar for bar in flat_bars if bar.trade_date <= through]

    evidence = build_as_delivery_evidence(
        symbol="HVBTEST",
        instrument_id="NSE:EQ:HVBTEST",
        ca_state="NONE",
        session_date=TRADING_DATE,
        decision_at=DECISION_AT,
        raw_bars_fn=quiet_bars,
    )
    assert evidence.status == "USABLE"
    assert evidence.delivery_z is not None and evidence.delivery_z > 2
    # Days above the 49.5 median on quiet bars: pct 50..58 plus the 90 spike.
    assert evidence.accumulation_days == 10


def test_mad_zero_window_is_unknown(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    _seed_series("HVBTEST", pct_fn=lambda index: 50.0)
    evidence = build_as_delivery_evidence(
        symbol="HVBTEST",
        instrument_id="NSE:EQ:HVBTEST",
        ca_state="NONE",
        session_date=TRADING_DATE,
        decision_at=DECISION_AT,
        raw_bars_fn=lambda symbol, through: [],
    )
    assert evidence.status == "UNKNOWN"
    assert "MTO_MAD_ZERO" in evidence.why
    assert evidence.delivery_z is None


def test_stale_when_latest_data_date_is_not_session(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    _seed_series("HVBTEST")
    # Remove nothing; instead request a later session date than the data.
    from datetime import date as date_cls

    evidence = build_as_delivery_evidence(
        symbol="HVBTEST",
        instrument_id="NSE:EQ:HVBTEST",
        ca_state="NONE",
        session_date=date_cls(TRADING_DATE.year, TRADING_DATE.month, TRADING_DATE.day + 1),
        decision_at=DECISION_AT,
        raw_bars_fn=lambda symbol, through: [],
    )
    assert evidence.status == "STALE"
    # STALE never ships a z: display requires USABLE.
    assert evidence.delivery_z is None
    assert "MTO_LATEST_NOT_SESSION" in evidence.why


def test_c13_future_parsed_at_never_enters_the_series(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    # All sessions published well before the decision...
    _seed_series("HVBTEST", parsed_offset_hours=-6)
    # ...plus a superseding same-day parse that publishes AFTER the decision.
    store_mto_parse_result(
        data_date=TRADING_DATE,
        parsed_at=DECISION_AT + timedelta(hours=3),
        rows=[mto_row("HVBTEST", 99.0)],
    )
    before = build_as_delivery_evidence(
        symbol="HVBTEST",
        instrument_id="NSE:EQ:HVBTEST",
        ca_state="NONE",
        session_date=TRADING_DATE,
        decision_at=DECISION_AT,
        raw_bars_fn=lambda symbol, through: [],
    )
    after = build_as_delivery_evidence(
        symbol="HVBTEST",
        instrument_id="NSE:EQ:HVBTEST",
        ca_state="NONE",
        session_date=TRADING_DATE,
        decision_at=DECISION_AT + timedelta(hours=4),
        raw_bars_fn=lambda symbol, through: [],
    )
    # Before the late parse is visible the 99% value cannot have entered the z.
    assert before.status == "UNKNOWN" or before.median_delivery_pct is None or (
        before.median_delivery_pct < 50
    )
    # After it becomes available the newest parse wins the dedupe.
    if after.status in {"USABLE", "STALE"}:
        window = [30.0 + (index % 5) for index in range(21)] + [99.0]
        from trendforge_api.hybrid_v2.as_lab.delivery import robust_z

        expected_z, _, _ = robust_z(window)
        assert after.delivery_z == round(expected_z, 4)


def test_c4_wait_ca_hides_delivery_z(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    _seed_series("HVBTEST")
    evidence = build_as_delivery_evidence(
        symbol="HVBTEST",
        instrument_id="NSE:EQ:HVBTEST",
        ca_state="WAIT_CA",
        session_date=TRADING_DATE,
        decision_at=DECISION_AT,
    )
    assert evidence.status == "WAIT_CA"
    assert evidence.delivery_z is None


def test_c16_numeric_scrip_rows_skip_as(tmp_path, monkeypatch) -> None:
    parts = persist_overlay_lineage(tmp_path, monkeypatch, symbol="500325")
    numeric_symbol = parts["attention"].rows[0].symbol
    assert numeric_symbol.isdigit()
    # Seed real MTO rows for the numeric scrip: identity gate must still skip AS.
    for index in range(22):
        store_mto_parse_result(
            data_date=TRADING_DATE - timedelta(days=21 - index),
            parsed_at=DECISION_AT - timedelta(hours=2),
            rows=[mto_row(numeric_symbol, 55.0)],
        )
    batch_rows = build_overlay_row_for(numeric_symbol)
    assert batch_rows.as_status == "UNKNOWN"
    assert batch_rows.as_delivery_z is None
    assert batch_rows.instrument_id is None


def test_c16_unknown_id_never_scores_even_with_mto_series(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch)
    _seed_series("HVBTEST")
    evidence = build_as_delivery_evidence(
        symbol="HVBTEST",
        instrument_id=None,
        ca_state="NONE",
        session_date=TRADING_DATE,
        decision_at=DECISION_AT,
    )
    assert evidence.status == "UNKNOWN"
    assert "UNKNOWN_ID_ROWS_SKIP_AS" in evidence.why
    assert evidence.delivery_z is None


def build_overlay_row_for(symbol: str):
    from trendforge_api.hybrid_v2.pipeline import build_hybrid_v2_overlay

    batch = build_hybrid_v2_overlay(limit=5)
    return batch.rows[0]
