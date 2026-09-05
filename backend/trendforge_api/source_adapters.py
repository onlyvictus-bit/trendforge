from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Literal

import pandas as pd

from .models import DataTrust, OHLCVCandle
from .ohlcv_adapter import (
    DataSourceUnavailable,
    fetch_yfinance_ohlcv,
    normalize_nse_symbol,
)
from .openalgo_client import (
    OpenAlgoConfig,
    OpenAlgoDataClient,
    OpenAlgoUnavailable,
    parse_openalgo_history_timestamp,
)


SourceName = Literal[
    "openalgo", "yfinance", "nsepython", "nselib", "openchart", "static_csv"
]


SOURCE_AUTHORITY: dict[str, DataTrust] = {
    "openalgo": DataTrust.OFFICIAL_OR_LICENSED,
    "yfinance": DataTrust.UNOFFICIAL_TEMP,
    "nsepython": DataTrust.UNOFFICIAL_WRAPPER,
    "nselib": DataTrust.UNOFFICIAL_WRAPPER,
    "openchart": DataTrust.OPEN_SOURCE_UNOFFICIAL,
    "static_csv": DataTrust.SYNTHETIC_TEST,
}


def fetch_ohlcv_from_source(
    source: SourceName,
    symbol: str,
    timeframe: str,
    period: str | None = None,
) -> tuple[str, str, list[OHLCVCandle]]:
    if source == "openalgo":
        return fetch_openalgo_ohlcv(symbol, timeframe, period)
    if source == "yfinance":
        return fetch_yfinance_ohlcv(symbol, timeframe, period)  # type: ignore[arg-type]
    if source == "nsepython":
        return fetch_nsepython_ohlcv(symbol, timeframe, period)
    if source == "nselib":
        return fetch_nselib_ohlcv(symbol, timeframe, period)
    if source == "openchart":
        return fetch_openchart_ohlcv(symbol, timeframe, period)
    if source == "static_csv":
        raise DataSourceUnavailable(
            "static_csv adapter requires an explicit file path and is not configured yet"
        )
    raise DataSourceUnavailable(f"Unsupported OHLCV source: {source}")


def fetch_openalgo_ohlcv(
    symbol: str,
    timeframe: str,
    period: str | None = None,
) -> tuple[str, str, list[OHLCVCandle]]:
    requested_symbol = symbol.strip().upper()
    if ":" in requested_symbol:
        exchange, display_symbol = requested_symbol.split(":", 1)
    else:
        exchange = os.getenv("OPENALGO_DEFAULT_EXCHANGE", "NSE").strip().upper()
        display_symbol = requested_symbol
        requested_symbol = f"{exchange}:{display_symbol}"
    if timeframe == "4h_custom":
        raise DataSourceUnavailable(
            "OpenAlgo 4h_custom must be built from stored 1-minute candles"
        )
    api_interval = "D" if timeframe in {"1d", "1w"} else timeframe
    candle_timeframe = "1d" if timeframe == "1w" else timeframe
    start_text, end_text = _period_to_dates(period or "1y")
    start_date = datetime.strptime(start_text, "%d-%m-%Y").date()
    end_date = datetime.strptime(end_text, "%d-%m-%Y").date()
    try:
        client = OpenAlgoDataClient(OpenAlgoConfig.from_env())
        rows = client.history(
            symbol=display_symbol,
            exchange=exchange,
            interval=api_interval,
            start_date=start_date,
            end_date=end_date,
        )
    except (OpenAlgoUnavailable, ValueError) as exc:
        raise DataSourceUnavailable(
            f"OpenAlgo history failed for {requested_symbol}: {exc}"
        ) from exc
    fetched_at = datetime.now(timezone.utc).isoformat()
    candles: list[OHLCVCandle] = []
    for index, row in enumerate(rows):
        try:
            timestamp = parse_openalgo_history_timestamp(row["timestamp"]).isoformat()
            candles.append(
                OHLCVCandle(
                    symbol=display_symbol,
                    timeframe=candle_timeframe,
                    source="openalgo",
                    timestamp=timestamp,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    trustLevel=DataTrust.OFFICIAL_OR_LICENSED,
                    fetchedAt=fetched_at,
                )
            )
        except (KeyError, TypeError, ValueError, OpenAlgoUnavailable) as exc:
            raise DataSourceUnavailable(
                f"OpenAlgo returned an unusable candle at row {index} for "
                f"{requested_symbol}: {exc}"
            ) from exc
    if timeframe == "1w" and candles:
        candles = _weekly_resample(candles)
    if not candles:
        raise DataSourceUnavailable(
            f"OpenAlgo returned no usable candles for {requested_symbol}"
        )
    return display_symbol, requested_symbol, candles


def _period_to_dates(period: str | None) -> tuple[str, str]:
    days = 365
    if period:
        cleaned = period.lower().strip()
        if cleaned.endswith("mo"):
            days = int(cleaned[:-2]) * 31
        elif cleaned.endswith("y"):
            days = int(cleaned[:-1]) * 365
        elif cleaned.endswith("d"):
            days = int(cleaned[:-1])
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    return start.strftime("%d-%m-%Y"), end.strftime("%d-%m-%Y")


def _find_column(frame: pd.DataFrame, names: list[str]) -> str | None:
    normalized = {
        str(col)
        .replace("\ufeff", "")
        .strip()
        .strip('"')
        .lower()
        .replace(" ", "_")
        .replace(".", ""): col
        for col in frame.columns
    }
    for name in names:
        key = (
            name.replace("\ufeff", "")
            .strip()
            .strip('"')
            .lower()
            .replace(" ", "_")
            .replace(".", "")
        )
        if key in normalized:
            return normalized[key]
    return None


def _to_float(value) -> float:
    if pd.isna(value):
        return 0.0
    return float(str(value).replace(",", "").strip())


def _nse_frame_to_candles(
    frame: pd.DataFrame,
    symbol: str,
    timeframe: str,
    source: str,
    trust: DataTrust,
) -> list[OHLCVCandle]:
    if frame.empty:
        return []
    date_col = _find_column(frame, ["date", "CH_TIMESTAMP", "timestamp", "Date"])
    open_col = _find_column(frame, ["open", "OPEN", "OpenPrice", "CH_OPENING_PRICE"])
    high_col = _find_column(frame, ["high", "HIGH", "HighPrice", "CH_TRADE_HIGH_PRICE"])
    low_col = _find_column(frame, ["low", "LOW", "LowPrice", "CH_TRADE_LOW_PRICE"])
    close_col = _find_column(
        frame, ["close", "CLOSE", "ClosePrice", "CH_CLOSING_PRICE", "last", "LastPrice"]
    )
    volume_col = _find_column(
        frame,
        [
            "volume",
            "VOLUME",
            "TotalTradedQuantity",
            "CH_TOT_TRADED_QTY",
            "total_traded_quantity",
        ],
    )
    required = [date_col, open_col, high_col, low_col, close_col]
    if any(col is None for col in required):
        raise DataSourceUnavailable(
            f"{source} returned unsupported columns: {list(frame.columns)}"
        )

    fetched_at = datetime.now(timezone.utc).isoformat()
    candles: list[OHLCVCandle] = []
    for _, row in frame.iterrows():
        try:
            ts = pd.to_datetime(row[date_col]).to_pydatetime().isoformat()  # type: ignore[index]
            candles.append(
                OHLCVCandle(
                    symbol=symbol,
                    timeframe=timeframe,
                    source=source,
                    timestamp=ts,
                    open=_to_float(row[open_col]),  # type: ignore[index]
                    high=_to_float(row[high_col]),  # type: ignore[index]
                    low=_to_float(row[low_col]),  # type: ignore[index]
                    close=_to_float(row[close_col]),  # type: ignore[index]
                    volume=_to_float(row[volume_col]) if volume_col else 0.0,
                    trustLevel=trust,
                    fetchedAt=fetched_at,
                )
            )
        except Exception:
            continue
    return candles


def fetch_nsepython_ohlcv(
    symbol: str,
    timeframe: str,
    period: str | None = None,
) -> tuple[str, str, list[OHLCVCandle]]:
    if os.getenv("TRENDFORGE_ENABLE_GPL_NSEPYTHON", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        raise DataSourceUnavailable(
            "nsepython adapter is disabled by default because the installed package is GPL-3.0; use official EOD adapters instead"
        )
    if timeframe not in {"1d", "1w"}:
        raise DataSourceUnavailable(
            "nsepython adapter currently supports EOD daily/weekly only"
        )
    try:
        from nsepython import equity_history
    except Exception as exc:
        raise DataSourceUnavailable("nsepython is not installed") from exc

    display_symbol, _ = normalize_nse_symbol(symbol)
    start, end = _period_to_dates(period or "1y")
    try:
        frame = equity_history(display_symbol, "EQ", start, end)
    except Exception as exc:
        raise DataSourceUnavailable(
            f"nsepython fetch failed for {display_symbol}: {exc}"
        ) from exc
    candles = _nse_frame_to_candles(
        frame,
        display_symbol,
        "1d",
        "nsepython",
        DataTrust.UNOFFICIAL_WRAPPER,
    )
    if timeframe == "1w" and candles:
        candles = _weekly_resample(candles)
    if not candles:
        raise DataSourceUnavailable(
            f"nsepython returned no usable candles for {display_symbol}"
        )
    return display_symbol, display_symbol, candles


def fetch_nselib_ohlcv(
    symbol: str,
    timeframe: str,
    period: str | None = None,
) -> tuple[str, str, list[OHLCVCandle]]:
    if timeframe not in {"1d", "1w"}:
        raise DataSourceUnavailable(
            "nselib adapter currently supports EOD daily/weekly only"
        )
    try:
        from nselib import capital_market
    except Exception as exc:
        raise DataSourceUnavailable("nselib is not installed") from exc

    display_symbol, _ = normalize_nse_symbol(symbol)
    lib_period = "1Y"
    if period:
        lib_period = period.upper()
    try:
        frame = capital_market.price_volume_and_deliverable_position_data(
            display_symbol, period=lib_period
        )
    except Exception as exc:
        raise DataSourceUnavailable(
            f"nselib fetch failed for {display_symbol}: {exc}"
        ) from exc
    candles = _nse_frame_to_candles(
        frame,
        display_symbol,
        "1d",
        "nselib",
        DataTrust.UNOFFICIAL_WRAPPER,
    )
    if timeframe == "1w" and candles:
        candles = _weekly_resample(candles)
    if not candles:
        raise DataSourceUnavailable(
            f"nselib returned no usable candles for {display_symbol}"
        )
    return display_symbol, display_symbol, candles


def fetch_openchart_ohlcv(
    symbol: str,
    timeframe: str,
    period: str | None = None,
) -> tuple[str, str, list[OHLCVCandle]]:
    interval_map = {
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "1d": "1d",
        "1w": "1wk",
    }
    if timeframe not in interval_map:
        raise DataSourceUnavailable(
            "openchart adapter supports 5m/15m/30m/1h/1d/1w only"
        )
    try:
        from openchart import NSEData
    except Exception as exc:
        raise DataSourceUnavailable("openchart is not installed") from exc

    display_symbol, _ = normalize_nse_symbol(symbol)
    default_period = "10d" if timeframe in {"5m", "15m", "30m", "1h"} else "1y"
    start, end = _period_to_dates(period or default_period)
    start_dt = datetime.strptime(start, "%d-%m-%Y")
    end_dt = datetime.strptime(end, "%d-%m-%Y")
    try:
        client = NSEData()
        frame = client.historical(
            display_symbol,
            segment="EQ",
            start=start_dt,
            end=end_dt,
            interval=interval_map[timeframe],
        )
    except Exception as exc:
        raise DataSourceUnavailable(
            f"openchart fetch failed for {display_symbol}: {exc}"
        ) from exc
    candles = _nse_frame_to_candles(
        frame,
        display_symbol,
        timeframe,
        "openchart",
        DataTrust.OPEN_SOURCE_UNOFFICIAL,
    )
    if not candles:
        raise DataSourceUnavailable(
            f"openchart returned no usable candles for {display_symbol}"
        )
    return display_symbol, display_symbol, candles


def _weekly_resample(candles: list[OHLCVCandle]) -> list[OHLCVCandle]:
    frame = pd.DataFrame([candle.model_dump(by_alias=True) for candle in candles])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame = frame.set_index("timestamp").sort_index()
    resampled = (
        frame.resample("W-MON")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
                "symbol": "last",
                "source": "last",
                "trustLevel": "last",
                "fetchedAt": "last",
            }
        )
        .dropna(subset=["open", "high", "low", "close"])
    )
    rows: list[OHLCVCandle] = []
    for timestamp, row in resampled.iterrows():
        rows.append(
            OHLCVCandle(
                symbol=str(row["symbol"]),
                timeframe="1w",
                source=str(row["source"]),
                timestamp=timestamp.to_pydatetime().isoformat(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                trustLevel=DataTrust(str(row["trustLevel"])),
                fetchedAt=str(row["fetchedAt"]),
            )
        )
    return rows
