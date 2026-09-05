from __future__ import annotations

from datetime import datetime, time
from typing import Literal
from zoneinfo import ZoneInfo

from .market_context import (
    MarketContextInput,
    MarketContextResult,
    SectorContextInput,
    SectorContextResult,
    evaluate_market_context,
    evaluate_sector_context,
)
from .exchange_calendar import expected_latest_nse_eod_date
from .models import DataTrust
from .storage import (
    latest_nse_cash_eod_date,
    list_nse_cash_eod,
    list_nse_index_eod,
    save_market_context_snapshot,
    save_sector_context_snapshot,
)


IST = ZoneInfo("Asia/Kolkata")

SECTOR_INDEX_MAP = {
    "Information Technology": "NIFTY IT",
    "Automobile and Auto Components": "NIFTY AUTO",
    "Fast Moving Consumer Goods": "NIFTY FMCG",
    "Healthcare": "NIFTY HEALTHCARE INDEX",
    "Metals & Mining": "NIFTY METAL",
    "Financial Services": "NIFTY FINANCIAL SERVICES",
    "Realty": "NIFTY REALTY",
    "Media Entertainment & Publication": "NIFTY MEDIA",
    "Oil Gas & Consumable Fuels": "NIFTY OIL & GAS",
    "Consumer Durables": "NIFTY CONSUMER DURABLES",
}


class ContextDataUnavailable(RuntimeError):
    """Raised when official point-in-time inputs cannot satisfy a context contract."""


def _source_timestamp(data_date: str) -> datetime:
    return datetime.combine(
        datetime.fromisoformat(data_date).date(), time(15, 30), tzinfo=IST
    )


def _as_of(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(IST)
    if value.utcoffset() is None:
        raise ValueError("as_of must include timezone")
    return value.astimezone(IST)


def build_official_market_context(
    *, as_of: datetime | None = None
) -> MarketContextResult:
    current = _as_of(as_of)
    nifty = list_nse_index_eod(
        index_name="NIFTY 50", as_of=current.date().isoformat(), limit=200
    )
    if len(nifty) < 200:
        raise ContextDataUnavailable(
            f"Official NIFTY 50 history has {len(nifty)} rows; 200 are required."
        )
    latest_date = str(nifty[-1]["index_date"])
    expected_date = expected_latest_nse_eod_date(current)
    if expected_date is None:
        raise ContextDataUnavailable(
            "Official NSE calendar cannot establish the expected latest EOD session."
        )
    if latest_date != expected_date.isoformat():
        raise ContextDataUnavailable(
            f"Latest official index date {latest_date} does not match expected session {expected_date.isoformat()}."
        )
    vix = list_nse_index_eod(index_name="INDIA VIX", as_of=latest_date, limit=2)
    if len(vix) < 2 or str(vix[-1]["index_date"]) != latest_date:
        raise ContextDataUnavailable(
            "Current and prior official INDIA VIX rows are required."
        )
    cash_date = latest_nse_cash_eod_date(as_of=latest_date)
    if cash_date != latest_date:
        raise ContextDataUnavailable(
            f"Cash breadth date {cash_date or 'missing'} does not match index date {latest_date}."
        )
    cash = list_nse_cash_eod(trade_date=latest_date, series="EQ", limit=10000)
    advances = sum(row["advance_state"] == "ADVANCE" for row in cash)
    declines = sum(row["advance_state"] == "DECLINE" for row in cash)
    unchanged = sum(row["advance_state"] == "UNCHANGED" for row in cash)
    if advances + declines + unchanged == 0:
        raise ContextDataUnavailable("Official cash breadth rows are empty.")

    result = evaluate_market_context(
        MarketContextInput(
            asOf=current,
            sourceDate=_source_timestamp(latest_date),
            niftyCloses=[float(row["close"]) for row in nifty],
            niftyReturnPercent=float(nifty[-1]["change_percent"]),
            indiaVix=float(vix[-1]["close"]),
            indiaVixChangePercent=float(vix[-1]["change_percent"]),
            advances=advances,
            declines=declines,
            unchanged=unchanged,
            trustLevel=DataTrust.OFFICIAL_FREE_EOD,
            maxAgeHours=168,
        )
    )
    save_market_context_snapshot(result.model_dump(mode="json", by_alias=True))
    return result


def build_official_sector_contexts(
    *,
    as_of: datetime | None = None,
    direction: Literal["LONG", "SHORT"] = "LONG",
) -> list[SectorContextResult]:
    current = _as_of(as_of)
    benchmark = list_nse_index_eod(
        index_name="NIFTY 50", as_of=current.date().isoformat(), limit=60
    )
    if len(benchmark) < 60:
        raise ContextDataUnavailable(
            f"Official NIFTY 50 history has {len(benchmark)} rows; 60 are required for sector context."
        )
    expected_date = expected_latest_nse_eod_date(current)
    if (
        expected_date is None
        or str(benchmark[-1]["index_date"]) != expected_date.isoformat()
    ):
        raise ContextDataUnavailable(
            "Sector benchmark history does not match the calendar-derived expected EOD session."
        )
    benchmark_by_date = {str(row["index_date"]): row for row in benchmark}
    results: list[SectorContextResult] = []
    for sector, index_name in SECTOR_INDEX_MAP.items():
        index_rows = list_nse_index_eod(
            index_name=index_name,
            as_of=current.date().isoformat(),
            limit=90,
        )
        aligned = [
            (benchmark_by_date[str(row["index_date"])], row)
            for row in index_rows
            if str(row["index_date"]) in benchmark_by_date
        ][-60:]
        if len(aligned) < 60:
            continue
        source_date = str(aligned[-1][1]["index_date"])
        result = evaluate_sector_context(
            SectorContextInput(
                sector=sector,
                direction=direction,
                asOf=current,
                sourceDate=_source_timestamp(source_date),
                sectorCloses=[float(row[1]["close"]) for row in aligned],
                benchmarkCloses=[float(row[0]["close"]) for row in aligned],
                trustLevel=DataTrust.OFFICIAL_FREE_EOD,
                maxAgeHours=168,
            )
        )
        save_sector_context_snapshot(result.model_dump(mode="json", by_alias=True))
        results.append(result)
    if not results:
        raise ContextDataUnavailable(
            "No sector index has 60 date-aligned official observations."
        )
    return results
