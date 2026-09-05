from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .market_data_service import ParameterContext
from .market_data_store import MarketDataStore, StoredAttempt


MAX_PARAMETER_OBJECT_BYTES = 64 * 1024 * 1024
MAX_SECTOR_INDICES = 32
DEFAULT_OPTION_SYMBOL_LIMIT = 8
MAX_OPTION_SYMBOL_LIMIT = 20
INDEX_UNDERLYINGS = {
    "BANKNIFTY",
    "FINNIFTY",
    "MIDCPNIFTY",
    "NIFTY",
    "NIFTYNXT50",
}


def _clean_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _safe_limit() -> int:
    raw = os.getenv("MARKET_DATA_OPTION_SYMBOL_LIMIT", str(DEFAULT_OPTION_SYMBOL_LIMIT))
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_OPTION_SYMBOL_LIMIT
    return max(1, min(value, MAX_OPTION_SYMBOL_LIMIT))


class SavedMarketParameterProvider:
    """Build bounded fan-out inputs from committed last-good market objects.

    The provider never fetches the network. A scheduler run can therefore run
    independent/base feeds first, rebuild this context, and then run only the
    parameter-dependent feeds without hard-coded symbols or sector names.
    """

    def __init__(self, store: MarketDataStore, *, option_symbol_limit: int | None = None) -> None:
        self.store = store
        selected_limit = _safe_limit() if option_symbol_limit is None else option_symbol_limit
        self.option_symbol_limit = max(1, min(selected_limit, MAX_OPTION_SYMBOL_LIMIT))

    def _records(
        self,
        latest: dict[str, StoredAttempt],
        source_key: str,
    ) -> tuple[dict[str, Any], ...]:
        attempt = latest.get(source_key)
        if attempt is None or not attempt.object_path:
            return ()
        path = Path(attempt.object_path).resolve(strict=False)
        objects_root = self.store.objects_root.resolve(strict=False)
        try:
            path.relative_to(objects_root)
        except ValueError:
            return ()
        if not path.is_file() or path.stat().st_size > MAX_PARAMETER_OBJECT_BYTES:
            return ()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return ()
        rows = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return ()
        return tuple(row for row in rows if isinstance(row, dict))

    @staticmethod
    def _sector_indices(rows: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
        sectors = {
            str(row.get("index") or row.get("indexSymbol") or "").strip()
            for row in rows
            if str(row.get("key") or "").strip().upper() == "SECTORAL INDICES"
        }
        return tuple(sorted(item for item in sectors if item))[:MAX_SECTOR_INDICES]

    @staticmethod
    def _nearest_option_expiries(
        rows: tuple[dict[str, Any], ...], trading_date: date
    ) -> dict[str, str]:
        nearest: dict[str, date] = {}
        for row in rows:
            symbol = _clean_symbol(row.get("symbol"))
            if not symbol or symbol in INDEX_UNDERLYINGS:
                continue
            if str(row.get("optionType") or "").upper() not in {"CE", "PE"}:
                continue
            try:
                expiry = date.fromisoformat(str(row.get("expiry") or ""))
            except ValueError:
                continue
            if expiry < trading_date:
                continue
            if symbol not in nearest or expiry < nearest[symbol]:
                nearest[symbol] = expiry
        return {
            symbol: expiry.strftime("%d-%b-%Y")
            for symbol, expiry in nearest.items()
        }

    def _active_option_contracts(
        self,
        activity_rows: tuple[dict[str, Any], ...],
        expiries: dict[str, str],
    ) -> tuple[tuple[str, str], ...]:
        ranked = sorted(
            activity_rows,
            key=lambda row: float(
                row.get("optVolume")
                or row.get("totVolume")
                or row.get("totTurnover")
                or 0
            ),
            reverse=True,
        )
        selected: list[tuple[str, str]] = []
        seen: set[str] = set()
        for row in ranked:
            symbol = _clean_symbol(row.get("symbol") or row.get("underlying"))
            if symbol in seen or symbol not in expiries:
                continue
            seen.add(symbol)
            selected.append((symbol, expiries[symbol]))
            if len(selected) >= self.option_symbol_limit:
                break
        return tuple(selected)

    def __call__(
        self, trading_date: date, market_session: str, at: datetime
    ) -> ParameterContext:
        latest = self.store.latest_all()
        sector_rows = self._records(latest, "nse_all_indices")
        fo_rows = self._records(latest, "nse_fo_bhavcopy")
        activity_rows = self._records(latest, "nse_most_active_underlying")
        expiries = self._nearest_option_expiries(fo_rows, trading_date)
        contracts = self._active_option_contracts(activity_rows, expiries)
        return ParameterContext(
            trading_date=trading_date,
            market_session=market_session,
            symbols=tuple(symbol for symbol, _ in contracts),
            sector_indices=self._sector_indices(sector_rows),
            option_expiries=dict(contracts),
            now=at,
        )
