from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .storage import get_latest_source_parse_result


DEAL_SOURCE_KEYS = (
    "nse_bulk_deals_today_csv",
    "nse_large_deals",
    "nse_large_deals_snapshot",
    "nse_block_deal",
    "bse_bulk_deals",
    "bse_block_deals",
)
SHAREHOLDING_SOURCE_KEYS = (
    "nse_shareholding_pattern",
    "bse_shareholding_pattern",
)
APPROVED_SOURCE_KEYS = DEAL_SOURCE_KEYS + SHAREHOLDING_SOURCE_KEYS
# Refresh-collected third-party screens. Only ticker rows become INFO pills.
# Screener/Equitymaster stay catalog-only (usually no ticker).
THIRD_PARTY_FII_SCREEN_KEYS = (
    "screener_in_fii_holding_change",
    "tickertape_fii_holding_change_3m",
    "dhan_fii_holding_change",
    "equitymaster_fii_buys_reference",
)
TICKER_HOLDING_SCREEN_KEYS = (
    "tickertape_fii_holding_change_3m",
    "dhan_fii_holding_change",
)

WARNING = (
    "Bulk/block deals are large deals with named clients, not certified FII "
    "trades. Shareholding FII/FPI changes are quarterly ownership evidence. "
    "Third-party screens (Screener/Tickertape/Dhan/Equitymaster) are lagged "
    "FII holding-change lists, not 'FII bought this stock today'."
)


class SignalModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class LargeDealSignal(SignalModel):
    signal_type: Literal["LARGE_DEAL"] = "LARGE_DEAL"
    symbol: str
    side: Literal["BUY", "SELL"] | None = None
    client: str | None = None
    quantity: float | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, ge=0)
    value: float | None = Field(default=None, ge=0)
    deal_type: Literal["BULK", "BLOCK"]
    date: str
    source_key: str
    fetched_at: datetime | None = None
    scope: Literal["STOCK_LEVEL_DEAL_ANCHOR"] = "STOCK_LEVEL_DEAL_ANCHOR"


class FIIHoldingChangeSignal(SignalModel):
    signal_type: Literal["FII_HOLDING_CHANGE"] = "FII_HOLDING_CHANGE"
    symbol: str | None = None
    company_name: str | None = None
    fii_pct: float | None = Field(default=None, ge=0, le=100)
    fii_pct_change: float | None = Field(default=None, ge=-100, le=100)
    holding_level_note: str | None = None
    identity_status: Literal[
        "TICKER_IN_UNIVERSE",
        "TICKER_UNVERIFIED",
        "ISIN_MAPPED",
        "NAME_MAPPED",
        "NAME_AMBIGUOUS",
        "NAME_ONLY",
    ] = "TICKER_UNVERIFIED"
    date: str
    source_key: str
    fetched_at: datetime | None = None
    scope: Literal[
        "QUARTERLY_OWNERSHIP_ONLY",
        "THIRD_PARTY_HOLDING_CHANGE",
    ] = "QUARTERLY_OWNERSHIP_ONLY"


class FIIStockSignalsSnapshot(SignalModel):
    generated_at: datetime
    latest_fetched_at: datetime | None = None
    warning: str = WARNING
    large_deals: list[LargeDealSignal] = Field(default_factory=list)
    fii_holding_changes: list[FIIHoldingChangeSignal] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)


ResultLoader = Callable[[str], Any]


class CanonicalLatestResultLoader:
    """Adapt one canonical MD69 latest-object snapshot to the signal loader API."""

    def __init__(
        self,
        store: Any,
        *,
        fallback: ResultLoader = get_latest_source_parse_result,
    ) -> None:
        self._fallback = fallback
        self._attempts = store.latest_all()
        self._objects_root = (Path(store.root) / "objects").resolve(strict=False)

    @staticmethod
    def _invalid(source_key: str) -> dict[str, Any]:
        return {
            "sourceKey": source_key,
            "parserState": "BROKEN_CANONICAL_OBJECT",
            "output": {},
        }

    def __call__(self, source_key: str) -> Any:
        attempt = self._attempts.get(source_key)
        if attempt is None:
            return self._fallback(source_key)
        object_path_value = getattr(attempt, "object_path", None)
        expected_hash = str(getattr(attempt, "content_hash", "") or "").casefold()
        if not object_path_value or len(expected_hash) != 64:
            return self._invalid(source_key)
        unresolved = Path(object_path_value)
        if unresolved.is_symlink():
            return self._invalid(source_key)
        try:
            object_path = unresolved.resolve(strict=True)
            object_path.relative_to(self._objects_root)
            content = object_path.read_bytes()
        except (OSError, ValueError):
            return self._invalid(source_key)
        if hashlib.sha256(content).hexdigest() != expected_hash:
            return self._invalid(source_key)
        try:
            normalized = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._invalid(source_key)
        if not isinstance(normalized, dict) or normalized.get("sourceKey") != source_key:
            return self._invalid(source_key)
        records = normalized.get("records")
        if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
            return self._invalid(source_key)
        data_date = normalized.get("dataDate") or getattr(attempt, "data_date", None)
        return {
            "sourceKey": source_key,
            "parserState": normalized.get("parserState"),
            "dataDate": str(data_date) if data_date else None,
            "fetchedAt": getattr(attempt, "fetched_at", None),
            "output": {"records": records},
        }

_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9&_.-]{0,31}$")
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
)

_CURRENT_FII_ALIASES = (
    "fiiPct",
    "fiiHoldPct",
    "fpiPct",
    "fiiPercentage",
    "fpiPercentage",
    "fiiHoldingPct",
    "fpiHoldingPct",
    "foreignInstitutionalHoldingPct",
    "foreignInstitutionalInvestorPct",
    "foreignInstitutionalInvestorsPct",
    "foreignPortfolioInvestorPct",
    "foreignPortfolioInvestorsPct",
)
_CHANGE_FII_ALIASES = (
    "fiiPctChange",
    "fiiChgPct",
    "fpiPctChange",
    "fiiHoldingChangePct",
    "fpiHoldingChangePct",
    "foreignInstitutionalHoldingChangePct",
    "foreignPortfolioInvestorChangePct",
)
_PREVIOUS_FII_ALIASES = (
    "previousFiiPct",
    "prevFiiPct",
    "fiiPctPrevious",
    "previousFpiPct",
    "prevFpiPct",
    "fpiPctPrevious",
    "previousForeignInstitutionalHoldingPct",
    "previousForeignPortfolioInvestorPct",
)


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _row_lookup(row: dict[str, Any], *aliases: str) -> Any:
    normalized = {_normalized_key(key): value for key, value in row.items()}
    for alias in aliases:
        key = _normalized_key(alias)
        if key in normalized and normalized[key] not in (None, ""):
            return normalized[key]
    return None


def _result_value(result: Any, snake_name: str, camel_name: str) -> Any:
    if isinstance(result, dict):
        return result.get(snake_name, result.get(camel_name))
    return getattr(result, snake_name, getattr(result, camel_name, None))


def _utc_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _usable_output(
    result: Any,
) -> tuple[dict[str, Any], str | None, datetime | None] | None:
    if result is None:
        return None
    state = str(_result_value(result, "parser_state", "parserState") or "").upper()
    if state not in {"PARSED", "PARSED_STRUCTURED", "PARSED_ADAPTER"}:
        return None
    output = _result_value(result, "output", "output")
    if not isinstance(output, dict):
        return None
    data_date = _result_value(result, "data_date", "dataDate")
    fetched_at = _result_value(result, "fetched_at", "fetchedAt")
    if fetched_at is None:
        fetched_at = _result_value(result, "parsed_at", "parsedAt")
    return output, str(data_date) if data_date else None, _utc_datetime(fetched_at)


def _rows_from_output(output: dict[str, Any]) -> list[dict[str, Any]]:
    # Parsers often publish the same objects under rows + records/deals.
    # Taking the first recognized container prevents duplicate signals.
    for key in ("deals", "rows", "records", "bulkRows", "blockRows"):
        value = output.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _symbol(row: dict[str, Any]) -> str | None:
    raw = _row_lookup(
        row,
        "symbol",
        "Symbol",
        "SYMBOL",
        "ticker",
        "TckrSymb",
        "securitySymbol",
    )
    value = str(raw or "").strip().upper()
    return value if _SYMBOL_RE.fullmatch(value) else None


def _text(row: dict[str, Any], *aliases: str) -> str | None:
    value = _row_lookup(row, *aliases)
    text = str(value or "").strip()
    return text or None


def _number(row: dict[str, Any], *aliases: str) -> float | None:
    value = _row_lookup(row, *aliases)
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _non_negative(row: dict[str, Any], *aliases: str) -> float | None:
    value = _number(row, *aliases)
    return value if value is not None and value >= 0 else None


def _iso_date(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value or "").strip()
    if not raw:
        return None
    iso_candidate = raw[:10]
    try:
        return date.fromisoformat(iso_candidate).isoformat()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _side(row: dict[str, Any]) -> Literal["BUY", "SELL"] | None:
    raw = _text(
        row,
        "side",
        "buySell",
        "Buy/Sell",
        "BUY_SELL",
        "TRANSACTION_TYPE",
        "transactionType",
    )
    value = str(raw or "").strip().upper()
    if value in {"B", "BUY", "P", "PURCHASE"}:
        return "BUY"
    if value in {"S", "SELL", "SALE"}:
        return "SELL"
    buyer = _text(row, "buyer", "buyClient", "buy_client")
    seller = _text(row, "seller", "sellClient", "sell_client")
    if buyer and not seller:
        return "BUY"
    if seller and not buyer:
        return "SELL"
    return None


def _client(row: dict[str, Any], side: str | None) -> str | None:
    explicit = _text(row, "client", "clientName", "CLIENT_NAME", "client_name")
    if explicit:
        return explicit
    if side == "BUY":
        return _text(row, "buyer", "buyClient", "buy_client")
    if side == "SELL":
        return _text(row, "seller", "sellClient", "sell_client")
    return None


def _deal_type(row: dict[str, Any], source_key: str) -> Literal["BULK", "BLOCK"] | None:
    raw = str(_row_lookup(row, "dealType", "deal_type", "type") or "").upper()
    if "BLOCK" in raw:
        return "BLOCK"
    if "BULK" in raw:
        return "BULK"
    if source_key in {"nse_block_deal", "bse_block_deals"}:
        return "BLOCK"
    if source_key in {
        "nse_bulk_deals_today_csv",
        "bse_bulk_deals",
    }:
        return "BULK"
    return None


def _normalize_deal(
    row: dict[str, Any],
    source_key: str,
    fallback_date: str | None,
    fetched_at: datetime | None,
) -> LargeDealSignal | None:
    symbol = _symbol(row)
    deal_type = _deal_type(row, source_key)
    event_date = _iso_date(
        _row_lookup(row, "date", "tradeDate", "DEAL_DATE", "eventDate")
        or fallback_date
    )
    if not symbol or not deal_type or not event_date:
        return None
    side = _side(row)
    quantity = _non_negative(
        row, "quantity", "qty", "tradedQty", "Quantity Traded", "QUANTITY"
    )
    price = _non_negative(
        row,
        "price",
        "tradePrice",
        "watp",
        "Trade Price / Wght. Avg. Price",
        "PRICE",
    )
    value = _non_negative(row, "value", "tradeValue", "notional", "turnover")
    if value is None and quantity is not None and price is not None:
        value = quantity * price
    return LargeDealSignal(
        symbol=symbol,
        side=side,
        client=_client(row, side),
        quantity=quantity,
        price=price,
        value=value,
        deal_type=deal_type,
        date=event_date,
        source_key=source_key,
        fetched_at=fetched_at,
    )


def _fold_company_name(value: Any) -> str:
    text = str(value or "").casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\b(private|pvt|limited|ltd|plc|inc|llp)\b", " ", text)
    return " ".join(text.split())


def _build_identity_index(loader: ResultLoader) -> dict[str, Any]:
    tickers: set[str] = set()
    isins: dict[str, str] = {}
    names: dict[str, set[str]] = {}
    for source_key in ("nse_nifty500_constituents", "nse_equity_universe"):
        usable = _usable_output(loader(source_key))
        if usable is None:
            continue
        for row in _rows_from_output(usable[0]):
            symbol = _symbol(row)
            if not symbol:
                continue
            tickers.add(symbol)
            isin = _text(row, "ISIN Code", "ISIN NUMBER", "isin", "ISIN")
            if isin:
                isins[isin.upper()] = symbol
            folded = _fold_company_name(
                _text(row, "Company Name", "Company", "companyName", "name")
            )
            if folded:
                names.setdefault(folded, set()).add(symbol)
    return {"tickers": tickers, "isins": isins, "names": names}


def _resolve_identity(
    row: dict[str, Any],
    source_key: str,
    index: dict[str, Any],
) -> tuple[str | None, str | None, str | None]:
    name = _text(row, "name", "company", "Company Name", "Company", "DispSym")
    isin = _text(row, "isin", "ISIN", "ISIN Code")
    symbol = _symbol(row)
    if isin:
        mapped = index["isins"].get(isin.upper())
        if mapped:
            return mapped, name, "ISIN_MAPPED"
    if symbol:
        status = (
            "TICKER_IN_UNIVERSE"
            if symbol in index["tickers"]
            else "TICKER_UNVERIFIED"
        )
        return symbol, name, status
    folded = _fold_company_name(name)
    if folded:
        matches = index["names"].get(folded) or set()
        if len(matches) == 1:
            return next(iter(matches)), name, "NAME_MAPPED"
        if len(matches) > 1:
            return None, name, "NAME_AMBIGUOUS"
    if name:
        return None, name, "NAME_ONLY"
    return None, None, None


def _normalize_holding(
    row: dict[str, Any],
    source_key: str,
    fallback_date: str | None,
    fetched_at: datetime | None,
    identity_index: dict[str, Any] | None = None,
) -> FIIHoldingChangeSignal | None:
    index = identity_index or {"tickers": set(), "isins": {}, "names": {}}
    symbol, company_name, identity_status = _resolve_identity(row, source_key, index)
    event_date = _iso_date(
        _row_lookup(
            row,
            "date",
            "quarterEnd",
            "reportDate",
            "asOnDate",
            "filingDate",
        )
        or fallback_date
    )
    current = _number(row, *_CURRENT_FII_ALIASES)
    change = _number(row, *_CHANGE_FII_ALIASES)
    if current is not None and not 0 <= current <= 100:
        current = None
    third_party = source_key in THIRD_PARTY_FII_SCREEN_KEYS
    if not event_date:
        return None
    if not third_party:
        if not symbol or current is None:
            return None
        if change is None:
            previous = _number(row, *_PREVIOUS_FII_ALIASES)
            if previous is None or not 0 <= previous <= 100:
                return None
            change = current - previous
        if not -100 <= change <= 100:
            return None
        return FIIHoldingChangeSignal(
            symbol=symbol,
            company_name=company_name,
            fii_pct=current,
            fii_pct_change=round(change, 6),
            identity_status=identity_status or "TICKER_UNVERIFIED",
            date=event_date,
            source_key=source_key,
            fetched_at=fetched_at,
        )
    if change is None and current is None:
        return None
    if change is not None and not -100 <= change <= 100:
        return None
    if not symbol and not company_name:
        return None
    note = None if current is not None else "holding level not supplied"
    return FIIHoldingChangeSignal(
        symbol=symbol,
        company_name=company_name,
        fii_pct=current,
        fii_pct_change=None if change is None else round(change, 6),
        holding_level_note=note,
        identity_status=identity_status or "NAME_ONLY",
        date=event_date,
        source_key=source_key,
        fetched_at=fetched_at,
        scope="THIRD_PARTY_HOLDING_CHANGE",
    )


def _deal_identity(item: LargeDealSignal) -> tuple[Any, ...]:
    return (
        item.source_key,
        item.symbol,
        item.date,
        item.deal_type,
        item.side,
        item.client,
        item.quantity,
        item.price,
    )


def _holding_identity(item: FIIHoldingChangeSignal) -> tuple[Any, ...]:
    return (
        item.source_key,
        item.symbol or "",
        (item.company_name or "").casefold(),
        item.date,
        item.fii_pct,
        item.fii_pct_change,
        item.identity_status,
    )


def build_fii_stock_signals(
    *,
    loader: ResultLoader = get_latest_source_parse_result,
    generated_at: datetime | None = None,
) -> FIIStockSignalsSnapshot:
    large_deals: list[LargeDealSignal] = []
    holding_changes: list[FIIHoldingChangeSignal] = []
    identity_index = _build_identity_index(loader)

    for source_key in (*APPROVED_SOURCE_KEYS, *THIRD_PARTY_FII_SCREEN_KEYS):
        usable = _usable_output(loader(source_key))
        if usable is None:
            continue
        output, data_date, fetched_at = usable
        rows = _rows_from_output(output)
        if source_key in DEAL_SOURCE_KEYS:
            large_deals.extend(
                signal
                for row in rows
                if (
                    signal := _normalize_deal(
                        row, source_key, data_date, fetched_at
                    )
                )
                is not None
            )
        else:
            holding_changes.extend(
                signal
                for row in rows
                if (
                    signal := _normalize_holding(
                        row, source_key, data_date, fetched_at, identity_index
                    )
                )
                is not None
            )

    large_deals = list({_deal_identity(item): item for item in large_deals}.values())
    holding_changes = list(
        {_holding_identity(item): item for item in holding_changes}.values()
    )
    # Stable two-pass sort: newest evidence first, then ascending source/symbol.
    large_deals.sort(key=lambda item: (item.source_key, item.symbol or ""))
    large_deals.sort(key=lambda item: item.date, reverse=True)
    holding_changes.sort(
        key=lambda item: (item.source_key, item.symbol or item.company_name or "")
    )
    holding_changes.sort(key=lambda item: item.date, reverse=True)
    symbols = sorted(
        {item.symbol for item in large_deals if item.symbol}
        | {item.symbol for item in holding_changes if item.symbol}
    )
    fetched_times = [
        item.fetched_at
        for item in [*large_deals, *holding_changes]
        if item.fetched_at is not None
    ]
    timestamp = generated_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return FIIStockSignalsSnapshot(
        generated_at=timestamp.astimezone(UTC),
        latest_fetched_at=max(fetched_times) if fetched_times else None,
        large_deals=large_deals,
        fii_holding_changes=holding_changes,
        symbols=symbols,
    )


__all__ = [
    "APPROVED_SOURCE_KEYS",
    "CanonicalLatestResultLoader",
    "DEAL_SOURCE_KEYS",
    "SHAREHOLDING_SOURCE_KEYS",
    "WARNING",
    "LargeDealSignal",
    "FIIHoldingChangeSignal",
    "FIIStockSignalsSnapshot",
    "build_fii_stock_signals",
]
