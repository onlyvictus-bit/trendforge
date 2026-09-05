from __future__ import annotations

import pytest

from trendforge_api import storage
from trendforge_api.performance import benchmark_cached_nifty50


def test_cached_nifty50_benchmark_processes_exact_universe(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "live.db")
    symbols = [f"N50{index:02d}" for index in range(50)]
    result = benchmark_cached_nifty50(symbols)
    assert result["status"] == "PASS"
    assert result["processedSeries"] == 50
    assert result["candidateCount"] == 50
    assert result["scanSeconds"] < 30
    assert result["executable"] is False


def test_cached_nifty50_benchmark_rejects_incomplete_membership() -> None:
    with pytest.raises(ValueError, match="Exactly 50"):
        benchmark_cached_nifty50(["ONLYONE"])
