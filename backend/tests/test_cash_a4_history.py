from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

import pytest

from trendforge_api import source_resolver, storage
from trendforge_api.market_data_store import ManifestStatus, MarketDataStore
from trendforge_api.selection import cash_a4_history
from trendforge_api.selection.cash_a1_staging import persist_cash_staging, stage_cash_bytes
from trendforge_api.selection.cash_a2_identity import (
    build_cash_identity_batch,
    persist_cash_identity,
)
from trendforge_api.selection.cash_a4_history import (
    CorporateActionVintage,
    build_cash_history_batch,
    ensure_official_raw_history,
    list_raw_bars,
    persist_cash_history,
)
from trendforge_api.selection.series_layers import SeriesKind, open_adjusted_series, raw_series

DAY1 = b"""TradDt,TckrSymb,SctySrs,ISIN,OpnPric,HghPric,LwPric,ClsPric,PrvsClsgPric,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd
13-Aug-2026,RELIANCE,EQ,INE002A01018,100,110,99,105,100,1000,105000,10
"""
DAY2 = b"""TradDt,TckrSymb,SctySrs,ISIN,OpnPric,HghPric,LwPric,ClsPric,PrvsClsgPric,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd
14-Aug-2026,RELIANCE,EQ,INE002A01018,105,112,104,110,105,1200,132000,12
"""
BAN_EMPTY = b"Securities in Ban For Trade Date 14-AUG-2026:\n"
FETCH1 = datetime(2026, 8, 13, 16, 0, tzinfo=UTC)
FETCH2 = datetime(2026, 8, 14, 16, 0, tzinfo=UTC)
DECISION = datetime(2026, 8, 14, 18, 0, tzinfo=UTC)


def _identity(tmp_path, monkeypatch, csv: bytes, fetched):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "cash-a4.db")
    storage._INITIALIZED_DB_PATHS.clear()
    staging = persist_cash_staging(stage_cash_bytes(csv, fetched_at=fetched))
    return persist_cash_identity(
        build_cash_identity_batch(
            staging,
            ban_content=BAN_EMPTY,
            ban_status=ManifestStatus.SUCCESS_NEW.value,
            ban_fetched_at=fetched,
        )
    )


def test_a4_raw_bars_are_immutable_and_baseline_needs_history(tmp_path, monkeypatch) -> None:
    first = _identity(tmp_path, monkeypatch, DAY1, FETCH1)
    persist_cash_history(build_cash_history_batch(first, decision_at=FETCH1))
    second = _identity(tmp_path, monkeypatch, DAY2, FETCH2)
    batch = persist_cash_history(build_cash_history_batch(second, decision_at=DECISION))
    assert batch.milestone == "A4"
    assert batch.can_rank is False
    row = batch.rows[0]
    assert row.raw_series_id.startswith("raw_")
    assert row.adjusted_series_id is None
    assert row.ca_state == "NONE"
    assert row.baseline.complete is True
    assert row.baseline.session_count == 2
    with pytest.raises(ValueError, match="immutable"):
        persist_cash_history(
            build_cash_history_batch(
                _identity(tmp_path, monkeypatch, DAY2.replace(b"110", b"111"), FETCH2),
                decision_at=DECISION,
            )
        )


def test_official_history_bootstrap_persists_exact_object_before_bar(
    tmp_path, monkeypatch
) -> None:
    _identity(tmp_path, monkeypatch, DAY2, FETCH2)
    store = MarketDataStore(root=tmp_path / "market-data", db_path=storage.DB_PATH)
    store.initialize_schema()
    monkeypatch.setattr(
        cash_a4_history,
        "_official_cash_urls",
        lambda day: [f"https://fixture.invalid/{day.isoformat()}.csv"],
    )
    monkeypatch.setattr(
        source_resolver,
        "fetch_url",
        lambda _url, _timeout: (200, {"content-type": "text/csv"}, DAY1),
    )

    stats = ensure_official_raw_history(
        date(2026, 8, 14), days=2, timeout_seconds=1, store=store
    )
    assert stats["days_saved"] == 1
    expected_hash = hashlib.sha256(DAY1).hexdigest()
    bars = list_raw_bars("RELIANCE", through=date(2026, 8, 14))
    assert len(bars) == 1
    assert bars[0].artifact_hash == expected_hash

    conn = storage.connect()
    try:
        objects = conn.execute(
            "SELECT content_hash, size_bytes FROM market_data_objects WHERE content_hash=?",
            (expected_hash,),
        ).fetchall()
    finally:
        conn.close()
    assert len(objects) == 1
    assert objects[0]["size_bytes"] == len(DAY1)

    # Replaying the same bootstrap cannot duplicate the content-addressed object.
    ensure_official_raw_history(
        date(2026, 8, 14), days=2, timeout_seconds=1, store=store
    )
    conn = storage.connect()
    try:
        object_count = conn.execute(
            "SELECT COUNT(*) FROM market_data_objects WHERE content_hash=?",
            (expected_hash,),
        ).fetchone()[0]
    finally:
        conn.close()
    assert object_count == 1


def test_official_history_bootstrap_rejects_oversize_before_parse(
    tmp_path, monkeypatch
) -> None:
    _identity(tmp_path, monkeypatch, DAY2, FETCH2)
    store = MarketDataStore(root=tmp_path / "market-data", db_path=storage.DB_PATH)
    store.initialize_schema()
    monkeypatch.setattr(
        cash_a4_history,
        "_official_cash_urls",
        lambda day: [f"https://fixture.invalid/{day.isoformat()}.csv"],
    )
    oversized = b"x" * (cash_a4_history.OFFICIAL_HISTORY_MAX_BYTES + 1)
    monkeypatch.setattr(
        source_resolver,
        "fetch_url",
        lambda _url, _timeout: (200, {}, oversized),
    )

    stats = ensure_official_raw_history(
        date(2026, 8, 14), days=2, timeout_seconds=1, store=store
    )
    assert int(stats["days_failed"]) >= 1
    assert list_raw_bars("RELIANCE", through=date(2026, 8, 14)) == []


def test_official_history_bootstrap_store_failure_never_writes_bar(
    tmp_path, monkeypatch
) -> None:
    _identity(tmp_path, monkeypatch, DAY2, FETCH2)
    store = MarketDataStore(root=tmp_path / "market-data", db_path=storage.DB_PATH)
    store.initialize_schema()
    monkeypatch.setattr(
        cash_a4_history,
        "_official_cash_urls",
        lambda day: [f"https://fixture.invalid/{day.isoformat()}.csv"],
    )
    monkeypatch.setattr(
        source_resolver,
        "fetch_url",
        lambda _url, _timeout: (200, {"content-type": "text/csv"}, DAY1),
    )

    def fail_install(*_args, **_kwargs):
        raise RuntimeError("fixture object-store failure")

    monkeypatch.setattr(store, "install_object", fail_install)
    stats = ensure_official_raw_history(
        date(2026, 8, 14), days=2, timeout_seconds=1, store=store
    )
    assert int(stats["days_failed"]) >= 1
    assert list_raw_bars("RELIANCE", through=date(2026, 8, 14)) == []


def test_a4_future_ca_is_hidden_and_visible_ca_opens_new_series(
    tmp_path, monkeypatch
) -> None:
    identity = _identity(tmp_path, monkeypatch, DAY2, FETCH2)
    future = CorporateActionVintage(
        event_id="CA-SPLIT-FUTURE",
        symbol="RELIANCE",
        action_class="SPLIT",
        effective_date=date(2026, 8, 20),
        available_at=datetime(2026, 8, 20, 6, 0, tzinfo=UTC),
        revision_id="rev-future",
        adjustment_factor=0.5,
    )
    visible = CorporateActionVintage(
        event_id="CA-SPLIT-NOW",
        symbol="RELIANCE",
        action_class="SPLIT",
        effective_date=date(2026, 8, 14),
        available_at=datetime(2026, 8, 14, 6, 0, tzinfo=UTC),
        revision_id="rev-now",
        adjustment_factor=0.5,
    )
    early = build_cash_history_batch(
        identity,
        decision_at=datetime(2026, 8, 13, 18, 0, tzinfo=UTC),
        vintages=[future, visible],
    )
    assert early.rows[0].hidden_future_ca_count == 2
    assert early.rows[0].ca_state == "NONE"
    assert early.rows[0].adjusted_series_id is None
    later = build_cash_history_batch(identity, decision_at=DECISION)
    assert later.rows[0].ca_state == "ADJUSTED"
    assert later.rows[0].adjusted_series_id != later.rows[0].raw_series_id
    assert later.rows[0].hidden_future_ca_count == 1
    raw = raw_series(instrument_key="NSE:RELIANCE:EQ", artifact_hash="a" * 64)
    adjusted = open_adjusted_series(raw, adjustment_event_id="CA-SPLIT-NOW")
    assert adjusted.kind is SeriesKind.ADJUSTED
    assert adjusted.source_artifact_hash == raw.source_artifact_hash


def test_a4_unresolved_ca_is_wait_not_bullish(tmp_path, monkeypatch) -> None:
    identity = _identity(tmp_path, monkeypatch, DAY2, FETCH2)
    batch = build_cash_history_batch(
        identity,
        decision_at=DECISION,
        vintages=[
            CorporateActionVintage(
                event_id="CA-WAIT",
                symbol="RELIANCE",
                action_class="SPLIT",
                effective_date=date(2026, 8, 14),
                available_at=datetime(2026, 8, 14, 6, 0, tzinfo=UTC),
                revision_id="rev-wait",
                adjustment_factor=None,
            )
        ],
    )
    assert batch.rows[0].ca_state == "WAIT_CA"
    assert batch.rows[0].adjusted_series_id is None
    assert "not bullish" in batch.rows[0].public_note.lower()
    assert batch.can_unlock_confirmed is False