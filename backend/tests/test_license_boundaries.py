from __future__ import annotations

import pytest

from trendforge_api.demo_data import generate_demo_daily_candles
from trendforge_api.harmonic_detector import attempt_pyharmonics
from trendforge_api.ohlcv_adapter import DataSourceUnavailable
from trendforge_api.source_adapters import fetch_nsepython_ohlcv
from trendforge_api import parquet_store


def test_restrictive_pyharmonics_package_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("TRENDFORGE_ENABLE_PYHARMONICS", raising=False)
    count, note = attempt_pyharmonics(
        generate_demo_daily_candles(sessions=100), "TFDEMO", "1d"
    )
    assert count == 0
    assert note and "restrictive NOC license" in note


def test_gpl_nsepython_adapter_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("TRENDFORGE_ENABLE_GPL_NSEPYTHON", raising=False)
    with pytest.raises(DataSourceUnavailable, match="GPL-3.0"):
        fetch_nsepython_ohlcv("RELIANCE", "1d", "1mo")


def test_unreadable_parquet_is_visible_in_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(parquet_store, "PARQUET_DIR", tmp_path)
    (tmp_path / "broken.parquet").write_bytes(b"not parquet")
    status = parquet_store.get_parquet_status()
    assert status.file_count == 1
    assert status.row_count == 0
    assert "1 parquet file(s) unreadable" in status.message
