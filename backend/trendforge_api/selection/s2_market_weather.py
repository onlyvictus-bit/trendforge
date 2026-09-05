"""File A S2 market weather: context chips that never vote on a stock.

One DTO, four blocks - index/VIX, breadth, sector ranks, commodity local vs
delayed-global grey text. Ceiling LIVE_S2_CONTEXT_WAIT_ONLY. The index is a
companion: Nifty being up can never add a second reason to buy a stock.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ..storage import get_latest_source_parse_result
from .r6_live import _float, _rows, _text, _usable

SCHEMA_VERSION = "trendforge.s2-market-weather.v1"
PROFILE_ID = "PRF-S2-WEATHER-WAIT"
ACCEPTANCE_CEILING = "LIVE_S2_CONTEXT_WAIT_ONLY"
CALIBRATION = "RESEARCH_CONTEXT_NOT_CONFIRMED"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

REGIME_RULES_VERSION = "s2-regime-v1"
VIX_BANDS_VERSION = "s2-vix-bands-v1"

SECTOR_INDEX_NAMES = (
    "NIFTY IT",
    "NIFTY AUTO",
    "NIFTY METAL",
    "NIFTY PHARMA",
    "NIFTY FMCG",
    "NIFTY ENERGY",
    "NIFTY REALTY",
    "NIFTY PSU BANK",
    "NIFTY PRIVATE BANK",
    "NIFTY FIN SERVICE",
    "NIFTY MEDIA",
    "NIFTY CHEMICALS",
)

# MCX symbol prefixes: (weather base, accepted contract prefixes).
MCX_WEATHER_SYMBOLS = (
    ("GOLD", ("GOLD", "GOLDM", "GOLDPETAL", "GOLDGUINEA")),
    ("SILVER", ("SILVER", "SILVERM", "SILVERPETAL")),
    ("CRUDEOIL", ("CRUDEOIL", "CRUDEOILM")),
    ("COPPER", ("COPPER",)),
    ("ZINC", ("ZINC",)),
    ("ALUMINIUM", ("ALUMINI", "ALUMINIUM")),
    ("NICKEL", ("NICKEL",)),
    ("NATURALGAS", ("NATURALGAS", "MNG")),
    ("MENTHAOIL", ("MENTHAOIL",)),
    ("COTTONCNDY", ("COTTONCNDY",)),
)


def _mcx_base(symbol: str) -> str | None:
    for base, prefixes in MCX_WEATHER_SYMBOLS:
        if any(symbol.startswith(prefix) for prefix in prefixes):
            return base
    return None


def _vix_band(level: float | None) -> str:
    """Versioned level bands. A band is weather, never a direction call."""
    if level is None:
        return "UNKNOWN"
    if level < 12:
        return "LOW"
    if level <= 20:
        return "NORMAL"
    return "HIGH"


def _regime_label(
    *,
    nifty_pct: float | None,
    vix_band: str,
    breadth_status: str,
    breadth_ratio: float | None,
) -> str:
    """Versioned research labels. They never touch a stock's four-state."""
    if nifty_pct is None:
        return "UNKNOWN"
    breadth_on = breadth_status == "BREADTH_RISK_ON"
    breadth_off = breadth_status == "BREADTH_RISK_OFF"
    risk_on = nifty_pct > 0 and vix_band != "HIGH" and not breadth_off
    risk_off = nifty_pct < 0 and (vix_band == "HIGH" or breadth_off or not breadth_on)
    if abs(nifty_pct) < 0.05 and not breadth_on and not breadth_off:
        return "RANGE"
    if risk_on and not risk_off:
        return "RISK_ON"
    if risk_off and not risk_on:
        return "RISK_OFF"
    return "MIXED"


class IndexQuoteV1(BaseModel):
    model_config = MODEL_CONFIG

    close: float | None = None
    changePercent: float | None = None
    changePercentStatus: str = "UNKNOWN_NO_LAST_GOOD"
    previousClose: float | None = None
    pointsChange: float | None = None


class VixQuoteV1(BaseModel):
    model_config = MODEL_CONFIG

    close: float | None = None
    changePercent: float | None = None
    band: str


class BreadthV1(BaseModel):
    model_config = MODEL_CONFIG

    advances: int | None = None
    declines: int | None = None
    unchanged: int | None = None
    ratio: float | None = None
    status: str

    @model_validator(mode="after")
    def missing_is_never_zero(self) -> "BreadthV1":
        if self.status.startswith("UNKNOWN") and (
            self.advances is not None
            or self.declines is not None
            or self.ratio is not None
        ):
            raise ValueError("unknown breadth may not carry invented numbers")
        if self.advances is None and self.declines is None and self.ratio is not None:
            raise ValueError("breadth ratio without counts is invented")
        return self


class SectorRowV1(BaseModel):
    model_config = MODEL_CONFIG

    name: str
    close: float | None = None
    changePercent: float | None = None
    rank: int | None = Field(default=None, gt=0)


class CommodityLocalV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    changePercent: float | None = None
    dte: int | None = Field(default=None, ge=0)
    status: str


class CommodityGlobalV1(BaseModel):
    model_config = MODEL_CONFIG

    sourceKey: str
    summary: str
    lagLabel: str = "DELAYED_OFFICIAL_CONTEXT"
    canDirectContract: bool = False

    @model_validator(mode="after")
    def global_context_cannot_direct(self) -> "CommodityGlobalV1":
        if self.canDirectContract:
            raise ValueError("delayed global context cannot direct an MCX contract")
        return self


class S2MarketWeatherV1(BaseModel):
    model_config = MODEL_CONFIG

    schemaVersion: str = SCHEMA_VERSION
    profileId: str = PROFILE_ID
    tradingDate: str | None = None
    builtAt: datetime
    freshness: str
    nifty50: IndexQuoteV1
    bankNifty: IndexQuoteV1 | None = None
    indiaVix: VixQuoteV1
    breadth: BreadthV1
    regimeLabel: Literal["RISK_ON", "RISK_OFF", "MIXED", "RANGE", "UNKNOWN"]
    regimeRulesVersion: str = REGIME_RULES_VERSION
    why: tuple[str, ...] = ()
    whyUnknown: tuple[str, ...] = ()
    sectors: tuple[SectorRowV1, ...] = ()
    commodityLocal: tuple[CommodityLocalV1, ...] = ()
    commodityGlobal: tuple[CommodityGlobalV1, ...] = ()
    stateCeiling: str = "WAIT"
    sourceActivationReady: bool = False
    canUnlockConfirmed: bool = False
    canRank: bool = False
    acceptanceCeiling: str = ACCEPTANCE_CEILING
    calibration: str = CALIBRATION

    @model_validator(mode="after")
    def weather_is_not_confirmation(self) -> "S2MarketWeatherV1":
        if self.canUnlockConfirmed or self.sourceActivationReady or self.canRank:
            raise ValueError("S2 weather cannot unlock CONFIRMED, activate, or rank")
        return self


def _quote_from_row(row: dict[str, Any]) -> IndexQuoteV1:
    quote = IndexQuoteV1(
        close=_float(row, "close"),
        changePercent=_float(row, "changePercent"),
        changePercentStatus=_text(row, "changePercentStatus") or "UNKNOWN",
        previousClose=_float(row, "previousClose"),
        pointsChange=_float(row, "pointsChange"),
    )
    return _harden_stored_quote(quote)


def _harden_stored_quote(quote: IndexQuoteV1) -> IndexQuoteV1:
    """Stored parses may predate the honest-percent parser fix.

    Recompute whenever corroboration (previousClose or pointsChange) exists;
    a claim that fights its own numbers loses. A claim whose magnitude matches
    pointsChange is points mislabelled as percent. Without corroboration,
    claims beyond ±5% on an index are treated as suspect and fail closed.
    """
    close = quote.close
    previous = quote.previousClose
    if (previous is None or previous <= 0) and close and quote.pointsChange is not None:
        prior = close - quote.pointsChange
        if prior > 0:
            previous = round(prior, 6)
            quote = quote.model_copy(update={"previousClose": previous})
    recomputed: float | None = None
    source = ""
    if close and previous and previous > 0:
        candidate = (close - previous) / previous * 100.0
        if abs(candidate) <= 30.0:
            recomputed = round(candidate, 6)
            source = "RECOMPUTED_STALE_PARSE_FROM_PREVIOUS_CLOSE"
    if recomputed is None and close and quote.pointsChange is not None:
        prior = close - quote.pointsChange
        if prior > 0:
            candidate = (close - prior) / prior * 100.0
            if abs(candidate) <= 30.0:
                recomputed = round(candidate, 6)
                source = "RECOMPUTED_STALE_PARSE_FROM_POINTS"

    claimed = quote.changePercent
    if claimed is None:
        if recomputed is not None:
            return quote.model_copy(update={"changePercent": recomputed, "changePercentStatus": source})
        return quote

    if recomputed is not None and abs(claimed - recomputed) > 0.5:
        return quote.model_copy(update={"changePercent": recomputed, "changePercentStatus": source})

    if quote.pointsChange is not None and abs(abs(claimed) - abs(quote.pointsChange)) < 1.0:
        if recomputed is not None:
            return quote.model_copy(update={"changePercent": recomputed, "changePercentStatus": source})
        return quote.model_copy(
            update={"changePercent": None, "changePercentStatus": "INDEX_PCT_STALE_PARSE_SUSPECT"}
        )

    if abs(claimed) > 5.0 and recomputed is None:
        return quote.model_copy(
            update={
                "changePercent": None,
                "changePercentStatus": "INDEX_PCT_STALE_PARSE_SUSPECT",
            }
        )
    return quote


def _index_rows(loader, key: str) -> tuple[list[dict[str, Any]], str | None, str]:
    usable = _usable(loader(key))
    if usable is None:
        return [], None, "MISSING_LAST_GOOD"
    output, data_date = usable
    return _rows(output), data_date, "CURRENT"


def _vix_prior_percent(index_name: str) -> tuple[float | None, str | None]:
    from ..storage import list_nse_index_eod

    history = list_nse_index_eod(index_name=index_name, limit=2)
    if len(history) < 2:
        return None, "UNKNOWN_VIX_PRIOR_SESSION_MISSING"
    current = history[-1]
    prior = history[-2]
    close = current.get("close") or current.get("closing_index_value")
    prev = prior.get("close") or prior.get("closing_index_value")
    if not close or not prev or float(prev) <= 0:
        return None, "UNKNOWN_VIX_PRIOR_SESSION_MISSING"
    return round((float(close) - float(prev)) / float(prev) * 100.0, 4), None


_BREADTH_KEYS = ("nse_pr_market_snapshot", "nse_market_status")
_BREADTH_ADVANCE_KEYS = ("advances", "advancing", "numAdvances", "adv")
_BREADTH_DECLINE_KEYS = ("declines", "declining", "numDeclines", "dec")
_BREADTH_UNCHANGED_KEYS = ("unchanged", "unchangedCount")


def _breadth(loader) -> tuple[BreadthV1, str]:
    for key in _BREADTH_KEYS:
        usable = _usable(loader(key)) if callable(loader) else None
        if usable is None:
            continue
        for row in _rows(usable[0]):
            advances = _float(row, *_BREADTH_ADVANCE_KEYS)
            declines = _float(row, *_BREADTH_DECLINE_KEYS)
            if advances is None or declines is None:
                continue
            unchanged = _float(row, *_BREADTH_UNCHANGED_KEYS)
            ratio = round(advances / max(declines, 1.0), 4)
            status = (
                "BREADTH_RISK_ON" if ratio >= 1.5
                else "BREADTH_RISK_OFF" if ratio <= 0.67
                else "BREADTH_MIXED"
            )
            return BreadthV1(
                advances=int(advances),
                declines=int(declines),
                unchanged=int(unchanged) if unchanged is not None else None,
                ratio=ratio,
                status=status,
            ), "SNAPSHOT"
    cash = _breadth_from_official_cash_session()
    if cash is not None:
        return cash, "CASH_SESSION"
    return BreadthV1(status="UNKNOWN_MISSING_OFFICIAL_BREADTH"), "MISSING"


def _breadth_from_official_cash_session() -> BreadthV1 | None:
    """Stock A/D from official cash bhavcopy session direction (A3).

    This is not the NSE advances/declines snapshot. It is still official:
    each eligible cash row's close vs previous close. Tests with an empty
    DB stay UNKNOWN.
    """
    from .cash_a3_discovery import SessionDirection, latest_cash_discovery

    batch = latest_cash_discovery()
    if batch is None or not batch.rows:
        return None
    advances = declines = unchanged = 0
    for row in batch.rows:
        if not row.eligible:
            continue
        direction = row.metrics.session_direction
        if direction is SessionDirection.UP:
            advances += 1
        elif direction is SessionDirection.DOWN:
            declines += 1
        elif direction is SessionDirection.FLAT:
            unchanged += 1
    if advances + declines + unchanged == 0:
        return None
    ratio = round(advances / max(declines, 1), 4)
    status = (
        "BREADTH_RISK_ON" if ratio >= 1.5
        else "BREADTH_RISK_OFF" if ratio <= 0.67
        else "BREADTH_MIXED"
    )
    return BreadthV1(
        advances=advances,
        declines=declines,
        unchanged=unchanged,
        ratio=ratio,
        status=status,
    )


def _sectors(rows: list[dict[str, Any]]) -> list[SectorRowV1]:
    sector_rows: list[tuple[float | None, SectorRowV1]] = []
    for row in rows:
        name = (_text(row, "indexName", "index", "indexSymbol") or "").upper()
        if name not in SECTOR_INDEX_NAMES:
            continue
        quote = _quote_from_row(row)
        sector_rows.append(
            (
                quote.changePercent,
                SectorRowV1(
                    name=name,
                    close=quote.close,
                    changePercent=quote.changePercent,
                ),
            )
        )
    ranked = sorted(
        sector_rows,
        key=lambda item: -(item[0] if item[0] is not None else -1e9),
    )
    out: list[SectorRowV1] = []
    for rank, (_pct, sector) in enumerate(ranked, start=1):
        out.append(sector.model_copy(update={"rank": rank}))
    return out


def _commodity_local(loader) -> list[CommodityLocalV1]:
    out: list[CommodityLocalV1] = []
    for key in ("mcx_bhavcopy", "mcx_bhavcopy_daily"):
        usable = _usable(loader(key)) if callable(loader) else None
        if usable is None:
            continue
        for row in _rows(usable[0]):
            raw_symbol = (_text(row, "symbol", "commodity", "ticker") or "").upper()
            base = _mcx_base(raw_symbol)
            if base is None:
                continue
            pct = _float(
                row,
                "changePercent",
                "percentChange",
                "pct_change",
                "pChange",
                "priceChangePercent",
            )
            if pct is None:
                previous = _float(row, "previousClose", "prev_close")
                close = _float(row, "close", "lastPrice", "settle_price")
                if close and previous and previous > 0:
                    pct = round((close - previous) / previous * 100.0, 4)
            expiry = (_text(row, "expiry", "expiryDate") or "").upper()
            dte: int | None = None
            if expiry:
                parsed_expiry = None
                for fmt in ("%d%b%Y", "%d-%b-%Y", "%Y-%m-%d"):
                    try:
                        parsed_expiry = datetime.strptime(expiry, fmt).date()
                        break
                    except ValueError:
                        continue
                if parsed_expiry is not None:
                    dte = max(0, (parsed_expiry - datetime.now(UTC).date()).days)
            status = (
                "CURRENT_LOCAL_BAR"
                if pct is not None
                else "UNKNOWN_NO_PRIOR_LOCAL_BAR"
            )
            existing = next((item for item in out if item.symbol == base), None)
            if existing is not None and existing.changePercent is not None:
                continue
            entry = CommodityLocalV1(symbol=base, changePercent=pct, dte=dte, status=status)
            if existing is None:
                out.append(entry)
            else:
                out[out.index(existing)] = entry
        if out:
            break
    return sorted(out, key=lambda item: item.symbol)


_GLOBAL_SLOTS = (
    ("cftc_cot_positions", "Weekly positioning; grey background only."),
    ("eia_petroleum_schedule", "Inventory schedule; grey background only."),
    ("wgc_gold_demand_trends", "Quarterly demand; grey background only."),
)


def build_s2_market_weather(
    *, loader: Any = None, built_at: datetime | None = None
) -> S2MarketWeatherV1:
    effective_loader = loader if callable(loader) else get_latest_source_parse_result
    rows, data_date, freshness = _index_rows(effective_loader, "nse_index_close_eod")

    why: list[str] = ["A5_COMPANION_CONTEXT_NEVER_A_VOTE"]
    why_unknown: list[str] = []
    nifty_row = next((r for r in rows if (_text(r, "indexName") or "") == "NIFTY 50"), None)
    bank_row = next((r for r in rows if (_text(r, "indexName") or "") == "NIFTY BANK"), None)
    vix_row = next((r for r in rows if (_text(r, "indexName") or "") == "INDIA VIX"), None)

    if nifty_row is None:
        nifty = IndexQuoteV1()
        why_unknown.append("UNKNOWN_NIFTY_LAST_GOOD_MISSING")
    else:
        nifty = _quote_from_row(nifty_row)
        if nifty.changePercent is None:
            why_unknown.append(nifty.changePercentStatus)

    bank = _quote_from_row(bank_row) if bank_row else None

    if vix_row is None:
        vix_level = None
        why_unknown.append("UNKNOWN_VIX_LAST_GOOD_MISSING")
    else:
        vix_level = _float(vix_row, "close")
    vix_prior_pct, vix_code = _vix_prior_percent("INDIA VIX")
    if vix_code:
        why_unknown.append(vix_code)
    vix = VixQuoteV1(close=vix_level, changePercent=vix_prior_pct, band=_vix_band(vix_level))

    breadth, breadth_source = _breadth(effective_loader)
    if breadth.status.startswith("UNKNOWN"):
        why_unknown.append(breadth.status)
    elif breadth_source == "CASH_SESSION":
        why.append("BREADTH_FROM_OFFICIAL_CASH_BHAVCOPY")
    elif breadth_source == "SNAPSHOT":
        why.append("BREADTH_FROM_OFFICIAL_AD_SNAPSHOT")

    regime = _regime_label(
        nifty_pct=nifty.changePercent,
        vix_band=vix.band,
        breadth_status=breadth.status,
        breadth_ratio=breadth.ratio,
    )

    sectors = _sectors(rows)
    if not sectors:
        why_unknown.append("UNKNOWN_SECTOR_ROWS_MISSING")

    commodity_local = _commodity_local(effective_loader)
    if not commodity_local:
        why_unknown.append("UNKNOWN_NO_LOCAL_MCX_BAR")
    commodity_global = [
        CommodityGlobalV1(sourceKey=key, summary=summary)
        for key, summary in _GLOBAL_SLOTS
    ]

    if nifty.changePercent is not None:
        why.append(f"NIFTY_PCT_{nifty.changePercent}")
    if vix.band != "UNKNOWN":
        why.append(f"VIX_BAND_{vix.band}")

    return S2MarketWeatherV1(
        tradingDate=data_date,
        builtAt=built_at or datetime.now(UTC),
        freshness=freshness,
        nifty50=nifty,
        bankNifty=bank,
        indiaVix=vix,
        breadth=breadth,
        regimeLabel=regime,  # type: ignore[arg-type]
        why=tuple(why),
        whyUnknown=tuple(dict.fromkeys(why_unknown)),
        sectors=tuple(sectors),
        commodityLocal=tuple(commodity_local),
        commodityGlobal=tuple(commodity_global),
    )


__all__ = [
    "ACCEPTANCE_CEILING",
    "CALIBRATION",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "S2MarketWeatherV1",
    "build_s2_market_weather",
]
