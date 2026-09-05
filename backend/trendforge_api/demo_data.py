from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from math import sin
from typing import Any
from zoneinfo import ZoneInfo

from .models import DataTrust, OHLCVCandle
from .nse_session import resample_nse_session
from .parquet_store import write_candles_to_parquet
from .storage import init_db, save_ohlcv_candles


IST = ZoneInfo("Asia/Kolkata")
DEMO_SOURCE = "deterministic_fixture"
DEMO_FETCHED_AT = "2026-01-01T00:00:00+00:00"


def _business_dates(start: date, sessions: int) -> list[date]:
    if sessions < 1:
        raise ValueError("sessions must be positive")
    output: list[date] = []
    current = start
    while len(output) < sessions:
        if current.weekday() < 5:
            output.append(current)
        current += timedelta(days=1)
    return output


def generate_demo_daily_candles(
    *, symbol: str = "TFDEMO", sessions: int = 160
) -> list[OHLCVCandle]:
    candles: list[OHLCVCandle] = []
    previous_close = 100.0
    for index, session_date in enumerate(_business_dates(date(2025, 1, 2), sessions)):
        close = 100.0 + index * 0.085 + sin(index / 6.0) * 2.4
        open_price = previous_close + sin(index / 3.0) * 0.35
        high = max(open_price, close) + 0.8 + abs(sin(index)) * 0.4
        low = min(open_price, close) - 0.75 - abs(sin(index / 2.0)) * 0.35
        volume = 700_000 + (index % 20) * 22_000 + int(abs(sin(index / 4.0)) * 180_000)
        candles.append(
            OHLCVCandle(
                symbol=symbol.upper(),
                timeframe="1d",
                source=DEMO_SOURCE,
                timestamp=datetime.combine(
                    session_date, time(15, 30), tzinfo=IST
                ).isoformat(),
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close, 4),
                volume=float(volume),
                trustLevel=DataTrust.SYNTHETIC_TEST,
                fetchedAt=DEMO_FETCHED_AT,
            )
        )
        previous_close = close
    return candles


def generate_demo_intraday_candles(
    *, symbol: str = "TFDEMO", sessions: int = 10
) -> list[OHLCVCandle]:
    candles: list[OHLCVCandle] = []
    previous_close = 100.0
    for day_index, session_date in enumerate(
        _business_dates(date(2026, 1, 2), sessions)
    ):
        session_start = datetime.combine(session_date, time(9, 15), tzinfo=IST)
        for bar_index in range(75):
            timestamp = session_start + timedelta(minutes=bar_index * 5)
            close = (
                100.0
                + day_index * 0.3
                + bar_index * 0.012
                + sin((bar_index + day_index * 3) / 8.0) * 0.45
            )
            open_price = previous_close
            high = max(open_price, close) + 0.12 + abs(sin(bar_index)) * 0.05
            low = min(open_price, close) - 0.11 - abs(sin(bar_index / 2.0)) * 0.05
            volume = 8_000 + (bar_index % 15) * 350 + day_index * 500
            candles.append(
                OHLCVCandle(
                    symbol=symbol.upper(),
                    timeframe="5m",
                    source=DEMO_SOURCE,
                    timestamp=timestamp.isoformat(),
                    open=round(open_price, 4),
                    high=round(high, 4),
                    low=round(low, 4),
                    close=round(close, 4),
                    volume=float(volume),
                    trustLevel=DataTrust.SYNTHETIC_TEST,
                    fetchedAt=DEMO_FETCHED_AT,
                )
            )
            previous_close = close
    return candles


def load_demo_data(
    *, symbol: str = "TFDEMO", write_parquet: bool = True
) -> dict[str, Any]:
    init_db()
    daily = generate_demo_daily_candles(symbol=symbol)
    intraday = generate_demo_intraday_candles(symbol=symbol)
    saved_daily = save_ohlcv_candles(daily)
    saved_intraday = save_ohlcv_candles(intraday)
    derived = {
        timeframe: resample_nse_session(intraday, timeframe).candles
        for timeframe in ("30m", "1h", "4h_custom", "1d", "1w")
    }
    derived_saved = {
        timeframe: save_ohlcv_candles(rows) for timeframe, rows in derived.items()
    }
    parquet_paths: list[str] = []
    if write_parquet:
        parquet_paths.append(str(write_candles_to_parquet(daily, source=DEMO_SOURCE)))
        parquet_paths.append(
            str(write_candles_to_parquet(intraday, source=DEMO_SOURCE))
        )
        parquet_paths.extend(
            str(write_candles_to_parquet(rows)) for rows in derived.values() if rows
        )
    return {
        "symbol": symbol.upper(),
        "source": DEMO_SOURCE,
        "trustLevel": DataTrust.SYNTHETIC_TEST.value,
        "dailyGenerated": len(daily),
        "intradayGenerated": len(intraday),
        "dailySaved": saved_daily,
        "intradaySaved": saved_intraday,
        "derivedGenerated": {
            timeframe: len(rows) for timeframe, rows in derived.items()
        },
        "derivedSaved": derived_saved,
        "parquetPaths": parquet_paths,
        "executable": False,
        "rule": "Deterministic fixture data is research/test evidence only and cannot unlock READY.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
