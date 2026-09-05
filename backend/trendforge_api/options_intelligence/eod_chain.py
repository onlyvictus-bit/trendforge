"""Persist EOD option ladders from the official FO UDiFF bhavcopy.

Live NSE chain JSON is free but session-blocked. The same day's FO zip
already carries CE/PE open interest, volume and close by strike. That is
enough for PCR, walls and max-pain reference. Bid/ask are absent, so
quality is CHAIN_EOD_OI rather than CHAIN_OK.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .chain_quality import assess_chain
from .iv_recorder import record_chain_snapshot

_OPTION_TAGS = ("STO", "IDO", "OPT")


def _is_option(row: dict[str, Any]) -> bool:
    instrument = str(row.get("instrument") or "").upper()
    option_type = str(row.get("optionType") or "").upper()
    strike = float(row.get("strike") or 0)
    if option_type not in {"CE", "PE"}:
        return False
    if strike <= 0:
        return False
    return any(tag in instrument for tag in _OPTION_TAGS) or not any(
        tag in instrument for tag in ("STF", "IDF", "FUT")
    )


def persist_eod_option_chains_from_fo(
    fo_rows: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    symbols: set[str] | None = None,
    limit_underlyings: int = 40,
) -> dict[str, int]:
    """Write nearest-expiry EOD ladders for WATCH (or named) underlyings."""

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    spots: dict[tuple[str, str], float] = {}
    wanted = {item.strip().upper() for item in symbols} if symbols else None
    for raw in fo_rows:
        if not _is_option(raw):
            continue
        symbol = str(raw.get("symbol") or "").strip().upper()
        expiry = str(raw.get("expiry") or "").strip()
        if not symbol or not expiry:
            continue
        if wanted is not None and symbol not in wanted:
            continue
        right = str(raw.get("optionType") or "").strip().upper()
        quote = {
            "expiry": expiry,
            "strike": float(raw.get("strike") or 0),
            "right": right,
            "ltp": float(raw.get("close") or 0) or None,
            "openInterest": float(raw.get("openInterest") or 0),
            "volume": float(raw.get("volume") or 0),
        }
        grouped[(symbol, expiry)].append(quote)
        spot = raw.get("underlyingPrice")
        if spot:
            spots[(symbol, expiry)] = float(spot)

    by_symbol: dict[str, list[str]] = defaultdict(list)
    for symbol, expiry in grouped:
        by_symbol[symbol].append(expiry)

    written = 0
    skipped = 0
    for symbol in sorted(by_symbol)[:limit_underlyings]:
        expiry = sorted(by_symbol[symbol])[0]
        rows = grouped[(symbol, expiry)]
        complete = {
            strike
            for strike in {item["strike"] for item in rows}
            if {item["right"] for item in rows if item["strike"] == strike} == {"CE", "PE"}
        }
        if not complete:
            skipped += 1
            continue
        quality = assess_chain(rows, expected_strike_count=max(len(complete), 1))
        record_chain_snapshot(
            underlying=symbol,
            expiry=expiry,
            quality_state=quality.state,
            spot=spots.get((symbol, expiry)),
            payload={
                "rows": rows,
                "expectedStrikeCount": len(complete),
                "spot": spots.get((symbol, expiry)),
                "source": "nse_fo_bhavcopy_eod",
            },
        )
        written += 1
    return {"written": written, "skipped": skipped, "underlyings": len(by_symbol)}
