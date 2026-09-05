from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from .models import BarState, DataTrust, OHLCVCandle


NSE_SESSION_START = time(9, 15)
NSE_SESSION_END = time(15, 30)
NSE_TIMEZONE = ZoneInfo("Asia/Kolkata")
SUPPORTED_NSE_TIMEFRAMES = {"30m", "1h", "4h_custom", "1d", "1w"}


@dataclass(frozen=True)
class ResampleResult:
    candles: list[OHLCVCandle]
    warnings: list[str]


def resample_nse_session(candles: list[OHLCVCandle], timeframe: str) -> ResampleResult:
    if timeframe not in SUPPORTED_NSE_TIMEFRAMES:
        raise ValueError(f"Unsupported NSE target timeframe: {timeframe}")
    if not candles:
        return ResampleResult([], ["WAIT_DATA_WEAK: no source candles supplied."])
    symbols = {row.symbol for row in candles}
    sources = {row.source for row in candles}
    if len(symbols) != 1 or len(sources) != 1:
        return ResampleResult(
            [],
            [
                "REJECT_DATA_INTEGRITY: mixed symbols or sources cannot be resampled together."
            ],
        )

    frame = _canonical_frame(candles)
    if frame.empty:
        return ResampleResult(
            [],
            ["WAIT_DATA_WEAK: no valid NSE-session rows remain after normalization."],
        )
    if timeframe == "1w":
        daily = _daily_rows(frame, candles)
        return _weekly_rows(daily)
    if timeframe == "1d":
        return ResampleResult(_daily_rows(frame, candles), [])

    interval_minutes = _infer_interval_minutes(frame.index)
    warnings: list[str] = []
    output: list[OHLCVCandle] = []
    width = {"30m": 30, "1h": 60, "4h_custom": 240}[timeframe]
    for session_date, day_data in frame.groupby(frame.index.date):
        windows = _intraday_windows(session_date, width, timeframe)
        for start, end, planned_partial in windows:
            rows = day_data.loc[(day_data.index >= start) & (day_data.index < end)]
            if rows.empty:
                warnings.append(
                    f"WAIT_DATA_WEAK: {session_date} {timeframe} window {start.time()} is missing."
                )
                continue
            expected_minutes = int((end - start).total_seconds() / 60)
            expected_rows = max(1, round(expected_minutes / interval_minutes))
            completeness = min(1.0, len(rows) / expected_rows)
            state: BarState = "PARTIAL_NSE_SESSION" if planned_partial else "COMPLETE"
            if completeness < 0.8:
                state = "INCOMPLETE_SOURCE"
                warnings.append(
                    f"WAIT_DATA_WEAK: {session_date} {timeframe} {start.time()} completeness {completeness:.0%}."
                )
            output.append(
                _aggregate(
                    rows,
                    candles,
                    timeframe,
                    start,
                    state,
                    str(session_date),
                    completeness,
                )
            )
    return ResampleResult(output, warnings)


def build_nse_4h_custom(
    candles: list[OHLCVCandle],
) -> tuple[list[OHLCVCandle], list[str]]:
    result = resample_nse_session(candles, "4h_custom")
    warnings = list(result.warnings)
    warnings.extend(
        f"{row.session_date} afternoon bar is 135 minutes: PARTIAL_CANDLE_CAUTION."
        for row in result.candles
        if row.bar_state == "PARTIAL_NSE_SESSION"
    )
    return result.candles, warnings


def _canonical_frame(candles: list[OHLCVCandle]) -> pd.DataFrame:
    frame = pd.DataFrame(
        [row.model_dump(mode="json", by_alias=True) for row in candles]
    )
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()
    frame.index = frame.index.tz_convert(NSE_TIMEZONE)
    frame = frame[~frame.index.duplicated(keep="last")]
    if frame.empty:
        return frame
    intraday = not all(
        str(value).lower() in {"1d", "1w"} for value in frame["timeframe"]
    )
    if intraday:
        in_session = (
            (frame.index.weekday < 5)
            & (frame.index.time >= NSE_SESSION_START)
            & (frame.index.time < NSE_SESSION_END)
        )
        frame = frame.loc[in_session]
    return frame


def _intraday_windows(session_date, width_minutes: int, timeframe: str):
    start = datetime.combine(session_date, NSE_SESSION_START, tzinfo=NSE_TIMEZONE)
    session_end = datetime.combine(session_date, NSE_SESSION_END, tzinfo=NSE_TIMEZONE)
    if timeframe == "4h_custom":
        split = start + timedelta(minutes=240)
        return [(start, split, False), (split, session_end, True)]
    windows = []
    current = start
    while current < session_end:
        natural_end = current + timedelta(minutes=width_minutes)
        end = min(natural_end, session_end)
        windows.append((current, end, end < natural_end))
        current = end
    return windows


def _daily_rows(
    frame: pd.DataFrame, source_candles: list[OHLCVCandle]
) -> list[OHLCVCandle]:
    output: list[OHLCVCandle] = []
    interval_minutes = _infer_interval_minutes(frame.index)
    source_is_daily = all(
        str(value).lower() in {"1d", "1w"} for value in frame["timeframe"]
    )
    for session_date, rows in frame.groupby(frame.index.date):
        expected_rows = 1 if source_is_daily else max(1, round(375 / interval_minutes))
        completeness = min(1.0, len(rows) / expected_rows)
        state: BarState = "COMPLETE" if completeness >= 0.8 else "INCOMPLETE_SOURCE"
        start = datetime.combine(session_date, NSE_SESSION_START, tzinfo=NSE_TIMEZONE)
        output.append(
            _aggregate(
                rows,
                source_candles,
                "1d",
                start,
                state,
                str(session_date),
                completeness,
            )
        )
    return output


def _weekly_rows(daily: list[OHLCVCandle]) -> ResampleResult:
    if not daily:
        return ResampleResult(
            [], ["WAIT_DATA_WEAK: no daily rows available for weekly resampling."]
        )
    frame = _canonical_frame(daily)
    output: list[OHLCVCandle] = []
    warnings: list[str] = []
    iso = frame.index.isocalendar()
    frame = frame.assign(iso_year=iso.year.to_numpy(), iso_week=iso.week.to_numpy())
    for (_, _), rows in frame.groupby(["iso_year", "iso_week"]):
        first = rows.index[0]
        completeness = min(1.0, len(rows) / 5)
        state: BarState = "COMPLETE" if len(rows) >= 5 else "PARTIAL_PERIOD"
        if state == "PARTIAL_PERIOD":
            warnings.append(
                f"WAIT_PARTIAL_PERIOD: week containing {first.date()} has {len(rows)} session rows."
            )
        output.append(
            _aggregate(
                rows,
                daily,
                "1w",
                first.to_pydatetime(),
                state,
                str(first.date()),
                completeness,
            )
        )
    return ResampleResult(output, warnings)


def _aggregate(
    rows: pd.DataFrame,
    source_candles: list[OHLCVCandle],
    timeframe: str,
    timestamp: datetime,
    bar_state: BarState,
    session_date: str,
    completeness: float,
) -> OHLCVCandle:
    last = rows.iloc[-1]
    source = str(last["source"])
    suffix = "nse_session" if timeframe != "1w" else "nse_week"
    return OHLCVCandle(
        symbol=str(last["symbol"]),
        timeframe=timeframe,
        source=f"{source}_{suffix}",
        timestamp=timestamp.isoformat(),
        open=float(rows["open"].iloc[0]),
        high=float(rows["high"].max()),
        low=float(rows["low"].min()),
        close=float(rows["close"].iloc[-1]),
        volume=float(rows["volume"].sum()),
        trustLevel=DataTrust(str(last["trustLevel"])),
        fetchedAt=max(row.fetched_at for row in source_candles),
        barState=bar_state,
        sessionDate=session_date,
        completeness=round(completeness, 6),
    )


def _infer_interval_minutes(index: pd.DatetimeIndex) -> int:
    if len(index) < 2:
        return 375
    differences = index.to_series().diff().dropna()
    intraday = differences[
        (differences > timedelta(0)) & (differences <= timedelta(hours=2))
    ]
    if intraday.empty:
        return 375
    return max(1, int(round(intraday.median().total_seconds() / 60)))


def is_nse_market_time(ts: datetime) -> bool:
    if ts.tzinfo is not None:
        ts = ts.astimezone(NSE_TIMEZONE)
    if ts.weekday() >= 5:
        return False
    return NSE_SESSION_START <= ts.time() <= NSE_SESSION_END
