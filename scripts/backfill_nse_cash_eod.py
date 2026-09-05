"""Backfill official NSE cash EQ bhavcopy history into A4 raw session bars.

Downloads dated official bhavcopy zips (same archive URLs the collector uses),
parses them with the existing cash parser, and stores EQ session bars through
the existing immutable A4 path (INSERT OR IGNORE; a changed hash is refused).

This script never writes market_data latest-good manifests, never touches the
anchor (last-good) day, never refreshes the other 122 sources, and never
changes R5 state authority: after backfill it rebuilds R5 only, which remains
LIVE_WAIT_REJECT_ONLY.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from trendforge_api.parsers.nse_cash_bhavcopy_parser import parse_nse_cash_bhavcopy
from trendforge_api.selection.cash_a2_identity import latest_cash_identity
from trendforge_api.selection.cash_a4_history import (  # noqa: E402
    CashRawSessionBar,
    _store_raw_bar,
    list_raw_bars,
)
from trendforge_api.selection.contracts import stable_id
from trendforge_api.selection.r5_live import (
    build_r5_structure_batch,
    persist_r5_structure_batch,
)
from trendforge_api.selection.series_layers import raw_series
from trendforge_api.source_resolver import direct_download_candidates, fetch_url

MAX_DAYS = 15
SAMPLE_SYMBOLS = ("RELIANCE", "TATASTEEL")


def anchor_date() -> date:
    from trendforge_api.selection.cash_a1_staging import latest_cash_staging

    staging = latest_cash_staging()
    if staging is not None and staging.source_result.data_date is not None:
        return staging.source_result.data_date
    identity = latest_cash_identity()
    if identity is not None:
        for row in identity.rows:
            return row.fact.data_date
    raise SystemExit("No cash last-good anchor date available; nothing to backfill from.")


def trading_days_before(anchor: date, count: int) -> list[date]:
    days: list[date] = []
    cursor = anchor - timedelta(days=1)
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(days))


def urls_for_day(day: date) -> list[str]:
    wanted = [day.strftime("%Y%m%d"), day.strftime("%d%m%y")]
    urls = direct_download_candidates("nse_bhavcopy_eod", today=day)
    matched = [url for url in urls if any(token in url for token in wanted)]
    # The official CM bhavcopy csv.zip is the schema the cash parser targets;
    # PR zips bundle many files and parse as WAIT_EMPTY_PARSE, so try them last.
    matched.sort(key=lambda url: "BhavCopy_NSE_CM_" not in url)
    seen: set[str] = set()
    ordered: list[str] = []
    for url in matched:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def fetch_day(day: date, timeout_seconds: int) -> tuple[bytes | None, str]:
    for url in urls_for_day(day):
        try:
            status, _headers, content = fetch_url(url, timeout_seconds)
        except HTTPError as exc:
            if exc.code == 404:
                continue
            return None, f"HTTP {exc.code} {url}"
        except (URLError, TimeoutError, OSError) as exc:
            return None, f"{type(exc).__name__}: {exc} {url}"
        if status >= 400 or not content:
            continue
        return content, url
    return None, "MISSING_404"


def backfill(days: int, through: date | None, timeout_seconds: int) -> dict[str, int]:
    anchor = through or anchor_date()
    targets = trading_days_before(anchor, days)
    identity = latest_cash_identity()
    if identity is None:
        raise SystemExit("No A2 identity batch; cannot map instrument ids.")
    instrument_by_symbol = {
        row.instrument.symbol: row.instrument.instrument_id for row in identity.rows
    }
    print(f"anchor last-good date: {anchor} (never touched)")
    print(f"target weekdays: {targets[0]} .. {targets[-1]} ({len(targets)} days)")

    stats = {
        "days_attempted": len(targets),
        "days_saved": 0,
        "days_missing": 0,
        "days_failed": 0,
        "bars_new": 0,
        "bars_present": 0,
        "bars_hash_conflict": 0,
        "rows_no_ohlc": 0,
        "rows_unknown_symbol": 0,
    }
    for day in targets:
        content, info = fetch_day(day, timeout_seconds)
        if content is None:
            if info == "MISSING_404":
                stats["days_missing"] += 1
                print(f"{day}: missing/404 (holiday or not published) - skipped")
            else:
                stats["days_failed"] += 1
                print(f"{day}: FAILED {info}")
            continue
        parsed = parse_nse_cash_bhavcopy(content)
        if parsed.get("parser_state") != "PARSED_STRUCTURED":
            stats["days_failed"] += 1
            print(f"{day}: parse {parsed.get('parser_state')} - skipped")
            continue
        if str(parsed.get("data_date")) != day.isoformat():
            stats["days_failed"] += 1
            print(
                f"{day}: data_date {parsed.get('data_date')} != requested - skipped"
            )
            continue
        import hashlib

        artifact = hashlib.sha256(content).hexdigest()
        new_bars = present = conflicts = no_ohlc = unknown = 0
        for row in parsed["output"]["rows"]:
            symbol = str(row["symbol"]).upper()
            instrument_id = instrument_by_symbol.get(symbol)
            if instrument_id is None:
                unknown += 1
                continue
            open_ = row.get("open")
            high = row.get("high")
            low = row.get("low")
            if not open_ or not high or not low:
                no_ohlc += 1
                continue
            existing = list_raw_bars(symbol, through=day)
            already = any(bar.trade_date == day for bar in existing)
            bar = CashRawSessionBar(
                bar_id=stable_id("cbar", instrument_id, day.isoformat(), artifact),
                instrument_id=instrument_id,
                symbol=symbol,
                trade_date=day,
                artifact_hash=artifact,
                series_id=raw_series(
                    instrument_key=f"NSE:{symbol}:EQ", artifact_hash=artifact
                ).series_id,
                open=float(open_),
                high=float(high),
                low=float(low),
                close=float(row["close"]),
                previous_close=float(row["previousClose"]),
                volume=float(row.get("volume") or 0),
                traded_value=float(row.get("tradedValue") or 0),
            )
            try:
                _store_raw_bar(bar)
            except ValueError:
                conflicts += 1
                continue
            new_bars += 0 if already else 1
            present += 1 if already else 0
        stats["bars_new"] += new_bars
        stats["bars_present"] += present
        stats["bars_hash_conflict"] += conflicts
        stats["rows_no_ohlc"] += no_ohlc
        stats["rows_unknown_symbol"] += unknown
        stats["days_saved"] += 1
        print(
            f"{day}: saved {new_bars} new bars "
            f"(present {present}, conflict {conflicts}, no-ohlc {no_ohlc}, "
            f"unknown-symbol {unknown}) from {info}"
        )
        time.sleep(0.5)
    return stats


def rebuild_r5() -> None:
    batch = build_r5_structure_batch()
    stored = persist_r5_structure_batch(batch)
    confirmed = sum(
        row.structure_state.value == "CONFIRMED" for row in stored.rows
    )
    with_setups = sum(1 for row in stored.rows if row.detected_setups)
    print("\nR5 rebuild:")
    print(f"  run_id={stored.run_id}")
    print(f"  trading_date={stored.trading_date} universe={stored.universe_count}")
    print(
        f"  wait={stored.wait_count} reject={stored.reject_count} "
        f"CONFIRMED={confirmed} (must be 0)"
    )
    print(f"  rows with detectedSetups: {with_setups}")
    for symbol in SAMPLE_SYMBOLS:
        bars = list_raw_bars(symbol, through=date.fromisoformat(stored.trading_date))
        dates = ", ".join(bar.trade_date.isoformat() for bar in bars)
        print(f"  {symbol}: historyCount={len(bars)} [{dates}]")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=10, help="trading days to backfill")
    parser.add_argument("--through", type=date.fromisoformat, default=None)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--skip-rebuild", action="store_true", help="do not rebuild R5 after backfill"
    )
    args = parser.parse_args()
    if not 1 <= args.days <= MAX_DAYS:
        parser.error(f"--days must be between 1 and {MAX_DAYS}")
    stats = backfill(args.days, args.through, args.timeout)
    print("\nBackfill summary:")
    for key in (
        "days_attempted",
        "days_saved",
        "days_missing",
        "days_failed",
        "bars_new",
        "bars_present",
        "bars_hash_conflict",
    ):
        print(f"  {key}: {stats[key]}")
    if not args.skip_rebuild:
        rebuild_r5()


if __name__ == "__main__":
    main()
