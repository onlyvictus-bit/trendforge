from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .models import OHLCVCandle, ParquetStatus
from .storage import DATA_DIR


PARQUET_DIR = DATA_DIR / "parquet"
LOGGER = logging.getLogger("trendforge.parquet")


def parquet_available() -> tuple[bool, str]:
    try:
        import pyarrow  # noqa: F401
    except Exception as exc:
        return False, f"pyarrow unavailable: {exc}"
    return True, "pyarrow available"


def candle_parquet_path(symbol: str, timeframe: str, source: str = "mixed") -> Path:
    clean_symbol = symbol.upper().strip().replace("/", "_")
    clean_timeframe = timeframe.lower().replace("/", "_")
    clean_source = source.lower().replace("/", "_")
    return PARQUET_DIR / clean_timeframe / clean_source / f"{clean_symbol}.parquet"


def write_candles_to_parquet(
    candles: list[OHLCVCandle], source: str | None = None
) -> Path:
    available, message = parquet_available()
    if not available:
        raise RuntimeError(message)
    if not candles:
        raise ValueError("no candles supplied")

    first = candles[0]
    selected_source = source or first.source
    path = candle_parquet_path(first.symbol, first.timeframe, selected_source)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        [candle.model_dump(mode="json", by_alias=True) for candle in candles]
    )
    frame.to_parquet(path, index=False)
    return path


def read_candles_from_parquet(
    symbol: str, timeframe: str, source: str = "mixed"
) -> list[dict]:
    available, message = parquet_available()
    if not available:
        raise RuntimeError(message)
    path = candle_parquet_path(symbol, timeframe, source)
    if not path.exists():
        return []
    return pd.read_parquet(path).to_dict(orient="records")


def get_parquet_status() -> ParquetStatus:
    available, message = parquet_available()
    if not PARQUET_DIR.exists():
        return ParquetStatus(
            available=available,
            basePath=str(PARQUET_DIR),
            fileCount=0,
            rowCount=0,
            message=message,
        )
    files = list(PARQUET_DIR.rglob("*.parquet"))
    rows = 0
    unreadable = 0
    if available:
        for file in files:
            try:
                rows += len(pd.read_parquet(file))
            except Exception as exc:
                unreadable += 1
                LOGGER.warning("parquet_status_read_failed path=%s error=%s", file, exc)
    if unreadable:
        message = f"{message}; {unreadable} parquet file(s) unreadable"
    return ParquetStatus(
        available=available,
        basePath=str(PARQUET_DIR),
        fileCount=len(files),
        rowCount=rows,
        message=message,
    )
