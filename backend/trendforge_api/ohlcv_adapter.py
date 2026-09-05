from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from .models import DataTrust, OHLCVCandle


class DataSourceUnavailable(RuntimeError):
    pass


Timeframe = Literal["5m", "15m", "30m", "1h", "4h", "4h_custom", "1d", "1w"]


YFINANCE_INTERVALS: dict[str, str] = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "60m",
    "4h": "60m",
    "4h_custom": "5m",
    "1d": "1d",
    "1w": "1wk",
}


DEFAULT_PERIODS: dict[str, str] = {
    "5m": "60d",
    "15m": "60d",
    "30m": "60d",
    "1h": "60d",
    "4h": "60d",
    "4h_custom": "60d",
    "1d": "2y",
    "1w": "5y",
}


def normalize_nse_symbol(symbol: str) -> tuple[str, str]:
    cleaned = symbol.strip().upper()
    if not cleaned:
        raise ValueError("symbol is required")
    if cleaned.startswith("^") or "." in cleaned:
        display = cleaned.replace(".NS", "")
        return display, cleaned
    return cleaned, f"{cleaned}.NS"


def _frame_to_candles(
    df, symbol: str, timeframe: str, source: str
) -> list[OHLCVCandle]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    candles: list[OHLCVCandle] = []
    for timestamp, row in df.iterrows():
        if row[["Open", "High", "Low", "Close"]].isna().any():
            continue
        ts = (
            timestamp.to_pydatetime()
            if hasattr(timestamp, "to_pydatetime")
            else timestamp
        )
        candles.append(
            OHLCVCandle(
                symbol=symbol,
                timeframe=timeframe,
                source=source,
                timestamp=ts.isoformat(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"])
                if "Volume" in row and row["Volume"] == row["Volume"]
                else 0.0,
                trustLevel=DataTrust.UNOFFICIAL_TEMP,
                fetchedAt=fetched_at,
            )
        )
    return candles


def _normalize_yfinance_columns(df):
    if df.empty:
        return df
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df = df.droplevel(-1, axis=1)
    return df.rename(columns={column: str(column).title() for column in df.columns})


def _resample_four_hour(df):
    resampled = (
        df.resample("4h")
        .agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        )
        .dropna(subset=["Open", "High", "Low", "Close"])
    )
    return resampled


def fetch_yfinance_ohlcv(
    symbol: str,
    timeframe: Timeframe,
    period: str | None = None,
) -> tuple[str, str, list[OHLCVCandle]]:
    try:
        import yfinance as yf
    except (
        Exception
    ) as exc:  # pragma: no cover - exercised only in missing dependency envs
        raise DataSourceUnavailable("yfinance is not installed") from exc

    display_symbol, request_symbol = normalize_nse_symbol(symbol)
    interval = YFINANCE_INTERVALS[timeframe]
    requested_period = period or DEFAULT_PERIODS[timeframe]
    try:
        df = yf.download(
            request_symbol,
            period=requested_period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception as exc:
        raise DataSourceUnavailable(
            f"yfinance fetch failed for {request_symbol}: {exc}"
        ) from exc

    df = _normalize_yfinance_columns(df)
    if df.empty:
        raise DataSourceUnavailable(
            f"yfinance returned no candles for {request_symbol}"
        )

    expected = {"Open", "High", "Low", "Close", "Volume"}
    missing = expected.difference(set(df.columns))
    if missing:
        raise DataSourceUnavailable(
            f"yfinance missing columns for {request_symbol}: {sorted(missing)}"
        )

    if timeframe == "4h":
        df = _resample_four_hour(df)

    candles = _frame_to_candles(df, display_symbol, timeframe, "yfinance")
    if not candles:
        raise DataSourceUnavailable(
            f"yfinance returned no usable candles for {request_symbol}"
        )
    return display_symbol, request_symbol, candles
