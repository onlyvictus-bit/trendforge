from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal
from http.cookiejar import CookieJar
from urllib.parse import quote, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener

import httpx
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .institutional_config import load_institutional_config
from .observability import configure_logging


logger = configure_logging()
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE_ROOT = ROOT_DIR / "data" / "raw_sources" / "institutional_endpoints"
DEFAULT_CACHE_DB = ROOT_DIR / "data" / "trendforge_research.db"
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9&_.-]{1,32}$")
SCRIP_PATTERN = re.compile(r"^[0-9]{1,12}$")
BSE_SESSION_EMPTY_RETRY_KEYS = frozenset(
    {"bse_financial_results_xbrl", "bse_shareholding_pattern"}
)


class ContractStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED_RESEARCH = "UNVERIFIED_RESEARCH"


@dataclass(frozen=True)
class EndpointSpec:
    key: str
    url_template: str
    response_kind: Literal["json", "text", "html", "binary"]
    purpose: str
    http_method: Literal["GET", "POST"] = "GET"
    body_kind: Literal["none", "form", "json"] = "none"
    body_parameters: tuple[str, ...] = ()
    requires_nse_session: bool = False
    required_parameters: tuple[str, ...] = ()
    normalized_source_key: str | None = None
    contract_status: ContractStatus = ContractStatus.VERIFIED
    referer: str | None = None
    seed_url: str | None = None
    timeout_seconds: float | None = None
    credential_env: str | None = None


ENDPOINTS: dict[str, EndpointSpec] = {
    item.key: EndpointSpec(
        key=item.key,
        url_template=item.url_template,
        response_kind=item.response_kind,
        purpose=item.purpose,
        http_method=item.http_method,
        body_kind=item.body_kind,
        body_parameters=tuple(item.body_parameters),
        requires_nse_session=item.requires_nse_session,
        required_parameters=tuple(item.required_parameters),
        normalized_source_key=item.normalized_source_key,
        contract_status=ContractStatus(item.contract_status),
        referer=item.referer,
        seed_url=item.seed_url,
        timeout_seconds=item.timeout_seconds,
        credential_env=item.credential_env,
    )
    for item in load_institutional_config().endpoint_contracts
}


CORPORATE_DISCLOSURE_ENDPOINTS: tuple[str, ...] = (
    "nse_announcements",
    "nse_shareholding_pattern",
    "nse_pledge",
    "nse_regulation_31",
    "nse_pit",
    "nse_regulation_29",
    "nse_tender_buyback",
    "bse_corporate_announcements",
    "bse_insider_trading",
    "bse_pledge_data",
)


SCANNER_PARSER_ENDPOINTS: tuple[str, ...] = (
    *CORPORATE_DISCLOSURE_ENDPOINTS,
    "bse_sast",
    "bse_bulk_deals",
    "bse_block_deals",
)


EXTENDED_MARKET_ENDPOINTS: tuple[str, ...] = (
    "bse_sast",
    "bse_bulk_deals",
    "bse_block_deals",
    "mcx_option_chain",
    "mcx_market_watch",
    "mcx_delivery_reports",
    "sge_benchmark_gold",
    "baker_hughes_na_rig_count",
)

MARKET_ACTIVITY_ENDPOINTS: tuple[str, ...] = (
    "nse_volume_gainers",
    "nse_most_active_volume",
    "nse_most_active_value",
    "nse_large_deals_snapshot",
)

INTRADAY_STOCK_DETAIL_ENDPOINTS: tuple[str, ...] = (
    "nse_oi_spurts_contracts",
    "nse_live_equity_derivatives_stock_opt",
    "nse_live_equity_derivatives_stock_fut",
    "nse_live_equity_derivatives_index_opt",
    "nse_live_equity_derivatives_index_fut",
    "nse_live_equity_derivatives_banknifty_opt",
    "nse_live_equity_derivatives_banknifty_fut",
    "nse_preopen_fo",
    "nse_all_indices",
    "nse_oi_spurts",
    "nse_most_active_underlying",
    "nse_market_turnover",
    "nse_variations_gainers",
    "nse_variations_loosers",
    "nse_financial_results",
    "nse_block_deal",
    "nse_bulk_deals_today_csv",
    "bse_order_win_announcements",
    "nsdl_fpi_daily_reportdetail",
    "nsdl_fpi_fortnightly",
)

DEFAULT_INTRADAY_SECTOR_INDICES: tuple[str, ...] = (
    "NIFTY AUTO",
    "NIFTY IT",
    "NIFTY PHARMA",
    "NIFTY METAL",
    "NIFTY FMCG",
    "NIFTY PSU BANK",
    "NIFTY REALTY",
    "NIFTY OIL & GAS",
)

MACRO_EVENT_ENDPOINTS: tuple[str, ...] = (
    "usda_wasde",
    "dgcis_trade_data",
    "imd_rainfall_timeseries",
    "des_crop_estimates",
    "shfe_weekly_stock",
    "china_nbs_indicator",
    "mcx_future_prices",
    "mcx_trading_holidays",
    "mcx_circulars",
    "fbil_usdinr_reference",
    "bse_xbrl_announcements",
    "nse_xbrl_taxonomy",
    "nse_pit_annual",
    "nse_shareholding_pattern",
    "mca_company_master_data",
    "cdsl_fpi_fortnightly",
    "rbi_fpi_caution",
    "msei_fii_dii",
    "cftc_legacy_futures_only",
    "cftc_disagg_futures_only",
    "cftc_tff_futures_only",
    "cftc_release_schedule",
    "eia_petroleum_schedule",
)


def market_activity_requests() -> list[tuple[str, dict[str, str]]]:
    """Build the bounded official NSE activity-watch fetch set."""
    return [(endpoint_key, {}) for endpoint_key in MARKET_ACTIVITY_ENDPOINTS]


def intraday_stock_detail_requests(
    *,
    from_date: str,
    to_date: str,
    sector_indices: tuple[str, ...] | list[str] = (),
    symbols: tuple[str, ...] | list[str] = (),
) -> list[tuple[str, dict[str, str]]]:
    """Build the research-only intraday stock-detail fetch set.

    Dates are for BSE order-win announcements and must use YYYY-MM-DD. Sector
    indices are fetched through the corrected NSE equity-stock-indices endpoint.
    """
    try:
        from_value = datetime.strptime(from_date.strip(), "%Y-%m-%d")
        to_value = datetime.strptime(to_date.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("from_date and to_date must use YYYY-MM-DD") from exc
    if from_value > to_value:
        raise ValueError("from_date cannot be after to_date")
    bse_dates = {
        "from_date": from_value.strftime("%Y%m%d"),
        "to_date": to_value.strftime("%Y%m%d"),
    }
    nse_dates = {
        "from_date": from_value.strftime("%d-%m-%Y"),
        "to_date": to_value.strftime("%d-%m-%Y"),
    }
    requests: list[tuple[str, dict[str, str]]] = [
        ("nse_oi_spurts_contracts", {}),
        ("nse_live_equity_derivatives_stock_opt", {}),
        ("nse_live_equity_derivatives_stock_fut", {}),
        ("nse_live_equity_derivatives_index_opt", {}),
        ("nse_live_equity_derivatives_index_fut", {}),
        ("nse_live_equity_derivatives_banknifty_opt", {}),
        ("nse_live_equity_derivatives_banknifty_fut", {}),
        ("nse_preopen_fo", {}),
        ("nse_all_indices", {}),
        ("nse_oi_spurts", {}),
        ("nse_most_active_underlying", {}),
        ("nse_market_turnover", {}),
        ("nse_variations_gainers", {}),
        ("nse_variations_loosers", {}),
        ("nse_financial_results", nse_dates),
        ("nse_block_deal", {}),
        # Populated companion when live /api/block-deal is empty outside session.
        ("nse_large_deals_snapshot", {}),
        ("nse_bulk_deals_today_csv", {}),
        ("bse_order_win_announcements", bse_dates),
        ("nsdl_fpi", {}),
        ("nsdl_fpi_daily_reportdetail", {}),
        ("nsdl_fpi_fortnightly", {}),
        ("bse_sast", {}),  # Reg-29 style acquisition/disposal companion
        ("bse_pledge_data", {}),  # Reg-31 style encumbrance companion
    ]
    for sector_index in sector_indices:
        clean = sector_index.strip().upper()
        if clean:
            requests.append(("nse_sector_constituents", {"sector_index": clean}))
    # Keep the argument for CLI/API compatibility, but do not fetch the
    # currently failing symbol-level quote/option-chain/quote-derivative
    # endpoints in this working-source screener path.
    for symbol in symbols:
        clean_symbol = symbol.strip().upper()
        if not clean_symbol:
            continue
        if not SYMBOL_PATTERN.fullmatch(clean_symbol):
            raise ValueError("symbol contains unsupported characters")
        symbol_params = {"symbol": clean_symbol}
        # PIT event sources often have sparse filings; use at least ~365 calendar
        # days so symbol queries return real disclosures when present.
        pit_from = from_value
        if (to_value - from_value).days < 365:
            from datetime import timedelta as _td

            pit_from = to_value - _td(days=365)
        pit_dates = {
            "from_date": pit_from.strftime("%d-%m-%Y"),
            "to_date": to_value.strftime("%d-%m-%Y"),
        }
        requests.extend(
            [
                ("nse_quote_equity", symbol_params),
                ("nse_quote_equity_trade_info", symbol_params),
                ("nse_option_chain_equity", symbol_params),
                ("nse_quote_derivative", symbol_params),
                ("nse_pit_symbol", {**symbol_params, **pit_dates}),
                ("nse_shareholding_pattern", symbol_params),
            ]
        )
    return requests


def macro_event_requests(
    *,
    symbol: str,
    scripcode: str,
    year_month: str,
    shfe_date: str,
    mcx_date: str,
    year: int,
    nbs_indicator_code: str = "A0B01",
    bse_category: str = "Company Update",
) -> list[tuple[str, dict[str, str]]]:
    """Build the bounded agri/weather/China/MCX/regulatory context fetch set."""
    clean_symbol = symbol.strip().upper()
    clean_scrip = scripcode.strip()
    if not SYMBOL_PATTERN.fullmatch(clean_symbol):
        raise ValueError("symbol contains unsupported characters")
    if not SCRIP_PATTERN.fullmatch(clean_scrip):
        raise ValueError("scripcode must be numeric")
    if not re.fullmatch(r"\d{4}", str(year)):
        raise ValueError("year must use YYYY")
    from_date = f"01-01-{year}"
    to_date = f"31-12-{year}"
    return [
        ("usda_wasde", {"year_month": year_month.strip()}),
        ("dgcis_trade_data", {}),
        ("imd_rainfall_timeseries", {}),
        ("des_crop_estimates", {}),
        ("shfe_weekly_stock", {"date_str": shfe_date.strip()}),
        ("china_nbs_indicator", {"indicator_code": nbs_indicator_code.strip()}),
        ("mcx_future_prices", {"Date": mcx_date.strip()}),
        ("mcx_trading_holidays", {}),
        ("mcx_circulars", {"PageNo": "1", "Records": "50"}),
        ("fbil_usdinr_reference", {}),
        (
            "bse_xbrl_announcements",
            {"category": bse_category.strip(), "scripcode": clean_scrip},
        ),
        ("nse_xbrl_taxonomy", {}),
        ("nse_pit_annual", {"from_date": from_date, "to_date": to_date}),
        ("nse_shareholding_pattern", {"symbol": clean_symbol}),
        ("mca_company_master_data", {}),
        ("cdsl_fpi_fortnightly", {}),
        ("rbi_fpi_caution", {}),
        ("msei_fii_dii", {}),
        ("cftc_legacy_futures_only", {}),
        ("cftc_disagg_futures_only", {}),
        ("cftc_tff_futures_only", {}),
        ("cftc_release_schedule", {}),
        ("eia_petroleum_schedule", {}),
    ]


def corporate_disclosure_requests(
    *, symbol: str, scripcode: str, from_date: str, to_date: str
) -> list[tuple[str, dict[str, str]]]:
    """Build the bounded ten-source corporate-disclosure fetch set."""
    clean_symbol = symbol.strip().upper()
    try:
        from_value = datetime.strptime(from_date.strip(), "%Y-%m-%d")
        to_value = datetime.strptime(to_date.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("from_date and to_date must use YYYY-MM-DD") from exc
    if from_value > to_value:
        raise ValueError("from_date cannot be after to_date")
    shared_bse_insider = {
        "scripcode": scripcode.strip(),
        "from_date": from_value.strftime("%d/%m/%Y"),
        "to_date": to_value.strftime("%d/%m/%Y"),
    }
    bse_announcement = {
        "scripcode": scripcode.strip(),
        "from_date": from_value.strftime("%Y%m%d"),
        "to_date": to_value.strftime("%Y%m%d"),
    }
    return [
        ("nse_announcements", {}),
        ("nse_shareholding_pattern", {"symbol": clean_symbol}),
        ("nse_pledge", {}),
        ("nse_regulation_31", {}),
        ("nse_pit", {}),
        ("nse_regulation_29", {}),
        ("nse_tender_buyback", {}),
        ("bse_corporate_announcements", bse_announcement),
        ("bse_insider_trading", shared_bse_insider),
        ("bse_pledge_data", {}),
    ]


def scanner_parser_requests(
    *, symbol: str, scripcode: str, from_date: str, to_date: str
) -> list[tuple[str, dict[str, str]]]:
    """Build the 13-source scanner parser set from the ChatGPT parser plan.

    The pasted script had 13 distinct network endpoints because BSE XBRL reused
    the BSE announcements endpoint. This builder keeps that shape while using
    the corrected TrendForge contracts where the pasted endpoints were stale.
    """
    disclosure_requests = corporate_disclosure_requests(
        symbol=symbol,
        scripcode=scripcode,
        from_date=from_date,
        to_date=to_date,
    )
    try:
        from_value = datetime.strptime(from_date.strip(), "%Y-%m-%d")
        to_value = datetime.strptime(to_date.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("from_date and to_date must use YYYY-MM-DD") from exc
    if from_value > to_value:
        raise ValueError("from_date cannot be after to_date")
    deal_dates = {
        "from_date": from_value.strftime("%d/%m/%Y"),
        "to_date": to_value.strftime("%d/%m/%Y"),
    }
    return [
        *disclosure_requests,
        ("bse_sast", {}),
        ("bse_bulk_deals", deal_dates),
        ("bse_block_deals", deal_dates),
    ]


def extended_market_requests(
    *,
    scripcode: str,
    from_date: str,
    to_date: str,
    mcx_symbol: str,
    mcx_expiry: str,
) -> list[tuple[str, dict[str, str]]]:
    """Build the bounded official/research endpoint set verified on 2026-07-14."""
    if not SCRIP_PATTERN.fullmatch(scripcode.strip()):
        raise ValueError("scripcode must be numeric")
    try:
        from_value = datetime.strptime(from_date.strip(), "%Y-%m-%d")
        to_value = datetime.strptime(to_date.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("from_date and to_date must use YYYY-MM-DD") from exc
    if from_value > to_value:
        raise ValueError("from_date cannot be after to_date")
    clean_symbol = mcx_symbol.strip().upper()
    clean_expiry = mcx_expiry.strip().upper()
    if not SYMBOL_PATTERN.fullmatch(clean_symbol):
        raise ValueError("mcx_symbol contains unsupported characters")
    if not re.fullmatch(r"\d{2}[A-Z]{3}\d{4}", clean_expiry):
        raise ValueError("mcx_expiry must use DDMMMYYYY")
    month = to_value.strftime("%Y-%m")
    deal_dates = {
        "from_date": from_value.strftime("%d/%m/%Y"),
        "to_date": to_value.strftime("%d/%m/%Y"),
    }
    return [
        ("bse_sast", {}),
        ("bse_bulk_deals", deal_dates),
        ("bse_block_deals", deal_dates),
        (
            "mcx_option_chain",
            {
                "symbol": clean_symbol,
                "expiry": clean_expiry,
                "Commodity": clean_symbol,
                "Expiry": clean_expiry,
            },
        ),
        ("mcx_market_watch", {}),
        ("mcx_delivery_reports", {}),
        ("sge_benchmark_gold", {"start": month, "end": month}),
        ("baker_hughes_na_rig_count", {}),
    ]


class FetchState(StrEnum):
    RAW_ARCHIVED = "RAW_ARCHIVED"
    NO_DATA_NOW = "NO_DATA_NOW"
    STALE_FALLBACK = "STALE_FALLBACK"
    WRONG_CONTENT = "WRONG_CONTENT"
    BROKEN = "BROKEN"


class EndpointFetchResult(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    endpoint_key: str
    state: FetchState
    fetched_at: datetime
    url: str
    content_hash: str | None = None
    raw_path: str | None = None
    media_type: str | None = None
    record_count: int = Field(default=0, ge=0)
    payload: Any = None
    can_score: bool = False
    reason: str | None = None
    from_cache: bool = False
    status_code: int | None = Field(default=None, ge=100, le=599)
    attempts: int = Field(default=0, ge=0)
    error_type: str | None = None


class AsyncEndpointClient:
    def __init__(
        self,
        *,
        archive_root: Path = DEFAULT_ARCHIVE_ROOT,
        cache_db: Path = DEFAULT_CACHE_DB,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        config = load_institutional_config()
        self._config = config
        self._archive_root = archive_root
        self._cache_db = cache_db
        self._client = httpx.AsyncClient(
            timeout=config.cache.request_timeout_seconds,
            transport=transport,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json,text/plain,text/html;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.8",
            },
        )
        self._nse_seeded = False
        self._nse_seed_lock = asyncio.Lock()
        self._seeded_urls: set[str] = set()
        self._seed_locks: dict[str, asyncio.Lock] = {}
        self._use_bse_browser_fallback = transport is None
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._last_request_at: dict[str, float] = {}
        self._initialize_cache()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _connect(self) -> sqlite3.Connection:
        self._cache_db.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._cache_db, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize_cache(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS institutional_endpoint_fetches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint_key TEXT NOT NULL,
                    parameter_hash TEXT NOT NULL,
                    url TEXT NOT NULL,
                    fetch_state TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    media_type TEXT,
                    content_hash TEXT,
                    raw_path TEXT,
                    record_count INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT,
                    reason TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_institutional_endpoint_latest
                ON institutional_endpoint_fetches(endpoint_key, parameter_hash, fetched_at)
                """
            )

    async def _rate_limit(self, host: str) -> None:
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            interval = self._config.cache.per_host_interval_seconds
            elapsed = time.monotonic() - self._last_request_at.get(host, 0.0)
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)
            self._last_request_at[host] = time.monotonic()

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(
                    max(float(retry_after), 0.0),
                    self._config.cache.retry_max_seconds,
                )
            except ValueError:
                pass
        base = min(
            self._config.cache.retry_backoff_seconds * (2 ** (attempt - 1)),
            self._config.cache.retry_max_seconds,
        )
        jitter = random.uniform(0, self._config.cache.retry_jitter_seconds)
        return min(base + jitter, self._config.cache.retry_max_seconds)

    @staticmethod
    def _wrong_content_type(
        response_kind: str, media_type: str, body: bytes
    ) -> str | None:
        sample = body[:16_384].decode("utf-8", errors="ignore").casefold()
        block_markers = (
            "access denied",
            "captcha",
            "cloudflare",
            "akamai",
            "bot detection",
            "request blocked",
        )
        if any(marker in sample for marker in block_markers):
            return "BLOCK_PAGE"
        if response_kind == "json" and (
            "html" in media_type
            or sample.lstrip().startswith("<!doctype html")
            or sample.lstrip().startswith("<html")
        ):
            return "HTML_INSTEAD_OF_JSON"
        return None

    @staticmethod
    def _exception_error_type(exc: Exception) -> str:
        if isinstance(exc, httpx.TimeoutException):
            return "TIMEOUT"
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            if status_code == 429:
                return "RATE_LIMIT"
            if status_code == 401:
                return "AUTH_REQUIRED"
            if status_code == 403:
                return "ACCESS_DENIED"
            return "HTTP_ERROR"
        if isinstance(exc, ValueError) and "response exceeds" in str(exc):
            return "RESPONSE_TOO_LARGE"
        return "REQUEST_FAILED"

    async def _seed_nse(self) -> None:
        if self._nse_seeded:
            return
        async with self._nse_seed_lock:
            if self._nse_seeded:
                return
            # Multi-step browser-like warm: homepage alone often 403; market pages
            # establish Akamai cookies required by public JSON APIs.
            seed_urls = (
                "https://www.nseindia.com/",
                "https://www.nseindia.com/market-data/live-equity-market",
                "https://www.nseindia.com/option-chain",
            )
            last_status: int | None = None
            for seed_url in seed_urls:
                await self._rate_limit("www.nseindia.com")
                response = await self._client.get(
                    seed_url,
                    headers={
                        "Accept": (
                            "text/html,application/xhtml+xml,application/xml;q=0.9,"
                            "image/avif,image/webp,*/*;q=0.8"
                        ),
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                    },
                )
                last_status = response.status_code
                if response.status_code < 400:
                    # Prefer a successful page seed; continue one more page for cookies.
                    continue
            if last_status is not None and last_status >= 400:
                logger.warning(
                    "NSE session seed returned %s; attempting the public API with the same session.",
                    last_status,
                )
            self._nse_seeded = True

    async def _seed_url(self, seed_url: str) -> None:
        if seed_url in self._seeded_urls:
            return
        lock = self._seed_locks.setdefault(seed_url, asyncio.Lock())
        async with lock:
            if seed_url in self._seeded_urls:
                return
            await self._rate_limit(urlparse(seed_url).hostname or "unknown")
            response = await self._client.get(seed_url)
            if response.status_code >= 400:
                logger.warning(
                    "Endpoint seed URL %s returned %s; attempting the data endpoint with the same session.",
                    seed_url,
                    response.status_code,
                )
            self._seeded_urls.add(seed_url)

    def _bse_browser_fetch_sync(
        self,
        *,
        endpoint_key: str,
        spec: EndpointSpec,
        url: str,
        request_headers: dict[str, str],
        timeout: float,
    ) -> httpx.Response | None:
        """Use a bounded browser-style stdlib session when BSE rejects httpx."""

        if endpoint_key not in BSE_SESSION_EMPTY_RETRY_KEYS or not spec.seed_url:
            return None
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        user_agent = self._client.headers.get("User-Agent", "Mozilla/5.0")
        page_headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
        }
        api_headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.8",
            **request_headers,
        }
        if endpoint_key == "bse_financial_results_xbrl":
            warm_urls = (
                "https://api.bseindia.com/BseIndiaAPI/api/"
                "Corp_GetFINANCE_DRDOWN_ng/w?flag=1",
                "https://api.bseindia.com/BseIndiaAPI/api/"
                "Corp_FinanceResult_ng_new/w?SCRIP_CD=&FlagDur=1&HFQ="
                "&ISUBGROUP_CODE=&segment=C",
            )
        else:
            warm_urls = (
                "https://api.bseindia.com/BseIndiaAPI/api/"
                "Corp_Shareholding_ng/w?scripcode=&flag=&indtype=",
            )

        try:
            with opener.open(
                Request(spec.seed_url, headers=page_headers), timeout=timeout
            ) as seed:
                seed.read(self._config.cache.max_response_bytes + 1)
            for warm_url in warm_urls:
                time.sleep(self._config.cache.per_host_interval_seconds)
                with opener.open(Request(warm_url, headers=api_headers), timeout=timeout) as warm:
                    warm.read(self._config.cache.max_response_bytes + 1)
            time.sleep(self._config.cache.per_host_interval_seconds)
            with opener.open(Request(url, headers=api_headers), timeout=timeout) as raw:
                body = raw.read(self._config.cache.max_response_bytes + 1)
                headers = dict(raw.headers.items())
                status_code = raw.status
        except (OSError, TimeoutError) as exc:
            logger.warning("BSE browser-session fallback failed for %s: %s", endpoint_key, exc)
            return None

        return httpx.Response(
            status_code=status_code,
            headers=headers,
            content=body,
            request=httpx.Request("GET", url, headers=request_headers),
        )
    async def _refresh_bse_session(
        self,
        *,
        endpoint_key: str,
        spec: EndpointSpec,
        request_headers: dict[str, str],
        timeout: float,
    ) -> None:
        """Re-warm BSE after its API returns a bare session object."""

        if spec.seed_url:
            self._seeded_urls.discard(spec.seed_url)
            await self._seed_url(spec.seed_url)
        if endpoint_key == "bse_financial_results_xbrl":
            warm_urls = (
                (
                    "financial-results dropdown",
                    "https://api.bseindia.com/BseIndiaAPI/api/"
                    "Corp_GetFINANCE_DRDOWN_ng/w?flag=1",
                ),
                (
                    "financial-results default window",
                    "https://api.bseindia.com/BseIndiaAPI/api/"
                    "Corp_FinanceResult_ng_new/w?SCRIP_CD=&FlagDur=1&HFQ="
                    "&ISUBGROUP_CODE=&segment=C",
                ),
            )
        elif endpoint_key == "bse_shareholding_pattern":
            warm_urls = (
                (
                    "shareholding default window",
                    "https://api.bseindia.com/BseIndiaAPI/api/"
                    "Corp_Shareholding_ng/w?scripcode=&flag=&indtype=",
                ),
            )
        else:
            return

        for warm_name, warm_url in warm_urls:
            await self._rate_limit("api.bseindia.com")
            warm = await self._client.get(
                warm_url,
                headers=request_headers,
                timeout=timeout,
            )
            if warm.status_code >= 400:
                logger.warning("BSE %s warm returned %s.", warm_name, warm.status_code)

    @staticmethod
    def _validate_parameters(spec: EndpointSpec, parameters: dict[str, str]) -> None:
        missing = [key for key in spec.required_parameters if not parameters.get(key)]
        if missing:
            raise ValueError(f"Missing endpoint parameters: {', '.join(missing)}")
        if "symbol" in parameters and not SYMBOL_PATTERN.fullmatch(
            parameters["symbol"].upper()
        ):
            raise ValueError("symbol contains unsupported characters")
        if "scripcode" in parameters and not SCRIP_PATTERN.fullmatch(
            parameters["scripcode"]
        ):
            raise ValueError("scripcode must be numeric")
        if "scheme_code" in parameters and not SCRIP_PATTERN.fullmatch(
            parameters["scheme_code"]
        ):
            raise ValueError("scheme_code must be numeric")
        for key in ("from_date", "to_date"):
            value = parameters.get(key)
            if value and not re.fullmatch(
                r"(?:\d{8}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})", value
            ):
                raise ValueError(f"{key} must use YYYYMMDD, dd/MM/yyyy, or dd-MM-yyyy")
        for key in ("start", "end"):
            value = parameters.get(key)
            if value and not re.fullmatch(r"\d{4}-\d{2}", value):
                raise ValueError(f"{key} must use YYYY-MM")
        year_month = parameters.get("year_month")
        if year_month and not re.fullmatch(r"\d{4}", year_month):
            raise ValueError("year_month must use MMYY, for example 0726")
        date_str = parameters.get("date_str")
        if date_str and not re.fullmatch(r"\d{8}", date_str):
            raise ValueError("date_str must use YYYYMMDD")
        year = parameters.get("year")
        if year and not re.fullmatch(r"\d{4}", year):
            raise ValueError("year must use YYYY")
        indicator_code = parameters.get("indicator_code")
        if indicator_code and not re.fullmatch(r"[A-Za-z0-9_.-]{1,32}", indicator_code):
            raise ValueError("indicator_code contains unsupported characters")
        category = parameters.get("category")
        if category and not re.fullmatch(r"[A-Za-z0-9&_, ./()-]{1,80}", category):
            raise ValueError("category contains unsupported characters")
        for key in ("Date", "PageNo", "Records"):
            value = parameters.get(key)
            if value and not re.fullmatch(r"[A-Za-z0-9/_.:-]{1,32}", value):
                raise ValueError(f"{key} contains unsupported characters")
        expiry = parameters.get("expiry")
        if expiry and not re.fullmatch(
            r"(?:\d{2}[A-Z]{3}\d{4}|\d{2}-[A-Z]{3}-\d{4}|\d{4}-\d{2}-\d{2}|current_week|next_week|far_week|current_month|next_month|far_month)",
            expiry.upper(),
        ):
            raise ValueError(
                "expiry must use an exchange date or supported relative-expiry keyword"
            )
        expiry_date = parameters.get("expiry_date")
        if expiry_date and not re.fullmatch(
            r"(?:\d{4}-\d{2}-\d{2}|current_week|next_week|far_week|current_month|next_month|far_month)",
            expiry_date.lower(),
        ):
            raise ValueError("expiry_date must use YYYY-MM-DD or a relative-expiry keyword")
        isin = parameters.get("isin")
        if isin and not re.fullmatch(r"IN[A-Z0-9]{10}", isin.upper()):
            raise ValueError("isin must be a 12-character Indian ISIN")
        instrument_key = parameters.get("instrument_key")
        if instrument_key and not re.fullmatch(
            r"[A-Za-z0-9_| .:\-]{3,128}", instrument_key
        ):
            raise ValueError("instrument_key contains unsupported characters")
        bucket_interval = parameters.get("bucket_interval")
        if bucket_interval and not (
            bucket_interval.isdigit() and 1 <= int(bucket_interval) <= 1440
        ):
            raise ValueError("bucket_interval must be an integer from 1 to 1440")
        statement_type = parameters.get("statement_type")
        if statement_type and statement_type.lower() not in {
            "consolidated",
            "standalone",
        }:
            raise ValueError("statement_type must be consolidated or standalone")
        full_statement = parameters.get("full_statement")
        if full_statement and full_statement.lower() not in {"true", "false"}:
            raise ValueError("full_statement must be true or false")
        time_period = parameters.get("time_period")
        if time_period and time_period.lower() not in {"yearly", "quarterly"}:
            raise ValueError("time_period must be yearly or quarterly")
        unit = parameters.get("unit")
        if unit and unit.lower() not in {
            "minutes",
            "hours",
            "days",
            "weeks",
            "months",
        }:
            raise ValueError("unit is not supported by the historical-candle contract")
        interval = parameters.get("interval")
        if interval and not (interval.isdigit() and 1 <= int(interval) <= 300):
            raise ValueError("interval must be an integer from 1 to 300")
        instrument_type = parameters.get("instrument_type")
        if instrument_type and not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", instrument_type):
            raise ValueError("instrument_type contains unsupported characters")

    @staticmethod
    def _build_url(spec: EndpointSpec, parameters: dict[str, str]) -> str:
        escaped = {
            key: quote(
                value.upper() if key == "symbol" else value,
                safe="_.-" if key == "sector_index" else "&_.-",
            )
            for key, value in parameters.items()
        }
        return spec.url_template.format(**escaped)

    @staticmethod
    def _build_referer(spec: EndpointSpec, parameters: dict[str, str]) -> str | None:
        if spec.referer is None:
            return None
        escaped = {
            key: quote(
                value.upper() if key == "symbol" else value,
                safe="_.-" if key == "sector_index" else "&_.-",
            )
            for key, value in parameters.items()
        }
        return spec.referer.format(**escaped)

    @staticmethod
    def _build_body(spec: EndpointSpec, parameters: dict[str, str]) -> dict[str, str]:
        return {key: parameters[key] for key in spec.body_parameters}

    @staticmethod
    def _parameter_hash(parameters: dict[str, str]) -> str:
        encoded = json.dumps(parameters, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _record_count(payload: Any, response_kind: str) -> int:
        if response_kind == "binary":
            return 1 if payload else 0
        if isinstance(payload, list):
            return len(payload)
        if isinstance(payload, dict):
            deal_keys = (
                "BULK_DEALS_DATA",
                "BLOCK_DEALS_DATA",
                "SHORT_DEALS_DATA",
            )
            if any(isinstance(payload.get(key), list) for key in deal_keys):
                return sum(
                    len(payload[key])
                    for key in deal_keys
                    if isinstance(payload.get(key), list)
                )
            counts: list[int] = []
            for key in (
                "data",
                "Data",
                "records",
                "rows",
                "Table",
                "zp",
                "wp",
            ):
                value = payload.get(key)
                if isinstance(value, list):
                    counts.append(len(value))
                elif isinstance(value, dict):
                    nested = AsyncEndpointClient._record_count(value, response_kind)
                    if nested:
                        counts.append(nested)
            if counts:
                return max(counts)
            return 1 if payload else 0
        if isinstance(payload, str):
            stripped = payload.strip().strip('"').strip()
            if stripped.lower() in {
                "",
                "no record found!",
                "no records found",
                "no record found",
                "null",
            }:
                return 0
            if response_kind == "text":
                return len([line for line in payload.splitlines() if line.strip()])
            return 1 if stripped else 0
        return 0

    def _archive(
        self, endpoint_key: str, body: bytes, media_type: str, content_hash: str
    ) -> str:
        date_key = datetime.now(UTC).date().isoformat()
        suffix = (
            ".json"
            if "json" in media_type
            else ".xlsx"
            if "spreadsheetml" in media_type or body.startswith(b"PK\x03\x04")
            else ".xls"
            if "excel" in media_type or body.startswith(b"\xd0\xcf\x11\xe0")
            else ".pdf"
            if "pdf" in media_type or body.startswith(b"%PDF")
            else ".html"
            if "html" in media_type
            else ".txt"
        )
        target_dir = self._archive_root / endpoint_key / date_key
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{content_hash}{suffix}"
        if not target.exists():
            temporary = target.with_suffix(target.suffix + ".part")
            temporary.write_bytes(body)
            temporary.replace(target)
        return str(target)

    def _persist(self, result: EndpointFetchResult, parameter_hash: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO institutional_endpoint_fetches(
                    endpoint_key, parameter_hash, url, fetch_state, fetched_at,
                    media_type, content_hash, raw_path, record_count, payload_json, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.endpoint_key,
                    parameter_hash,
                    result.url,
                    result.state.value,
                    result.fetched_at.isoformat(),
                    result.media_type,
                    result.content_hash,
                    result.raw_path,
                    result.record_count,
                    json.dumps(
                        result.payload, ensure_ascii=True, separators=(",", ":")
                    ),
                    result.reason,
                ),
            )

    def _latest_cached(
        self,
        endpoint_key: str,
        parameter_hash: str,
        reason: str,
        *,
        error_type: str,
        status_code: int | None,
        attempts: int,
    ) -> EndpointFetchResult | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM institutional_endpoint_fetches
                WHERE endpoint_key = ? AND parameter_hash = ? AND fetch_state IN ('RAW_ARCHIVED', 'NO_DATA_NOW')
                ORDER BY fetched_at DESC LIMIT 1
                """,
                (endpoint_key, parameter_hash),
            ).fetchone()
        if row is None:
            return None
        return EndpointFetchResult(
            endpoint_key=endpoint_key,
            state=FetchState.STALE_FALLBACK,
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            url=row["url"],
            content_hash=row["content_hash"],
            raw_path=row["raw_path"],
            media_type=row["media_type"],
            record_count=row["record_count"],
            payload=json.loads(row["payload_json"]),
            can_score=False,
            reason=reason,
            from_cache=True,
            status_code=status_code,
            attempts=attempts,
            error_type=error_type,
        )

    async def fetch(
        self,
        endpoint_key: str,
        parameters: dict[str, str] | None = None,
        *,
        force: bool = False,
    ) -> EndpointFetchResult:
        del (
            force
        )  # A refresh is always attempted; stale fallback is explicit on failure.
        if endpoint_key not in ENDPOINTS:
            raise KeyError(f"Unknown endpoint key: {endpoint_key}")
        spec = ENDPOINTS[endpoint_key]
        normalized = {
            key: str(value).strip() for key, value in (parameters or {}).items()
        }
        self._validate_parameters(spec, normalized)
        url = self._build_url(spec, normalized)
        parameter_hash = self._parameter_hash(normalized)
        attempts = 0
        response: httpx.Response | None = None
        try:
            if spec.requires_nse_session:
                await self._seed_nse()
            if spec.seed_url:
                await self._seed_url(spec.seed_url)
            request_headers: dict[str, str] = {}
            if spec.credential_env:
                credential = os.environ.get(spec.credential_env, "").strip()
                if not credential:
                    raise ValueError(
                        f"Required read-only credential is not configured: {spec.credential_env}"
                    )
                request_headers["Authorization"] = f"Bearer {credential}"
            referer = self._build_referer(spec, normalized)
            if referer:
                request_headers["Referer"] = referer
            if (urlparse(url).hostname or "").endswith("bseindia.com"):
                request_headers.setdefault("Referer", "https://www.bseindia.com/")
                request_headers["Origin"] = "https://www.bseindia.com"
                request_headers["X-Requested-With"] = "XMLHttpRequest"
            elif spec.requires_nse_session:
                request_headers.setdefault("Referer", "https://www.nseindia.com/")
                request_headers["X-Requested-With"] = "XMLHttpRequest"
            elif (urlparse(url).hostname or "").endswith("mcxindia.com"):
                request_headers.setdefault("Referer", "https://www.mcxindia.com/")
                request_headers["Origin"] = "https://www.mcxindia.com"
                request_headers["X-Requested-With"] = "XMLHttpRequest"
            elif spec.seed_url:
                request_headers["X-Requested-With"] = "XMLHttpRequest"
            timeout = spec.timeout_seconds or self._config.cache.request_timeout_seconds
            retryable_statuses = {408, 425, 429, 500, 502, 503, 504}
            if spec.requires_nse_session:
                retryable_statuses.update({401, 403})
            for attempts in range(1, self._config.cache.max_retries + 1):
                await self._rate_limit(urlparse(url).hostname or "unknown")
                if spec.http_method == "GET":
                    response = await self._client.get(
                        url, headers=request_headers, timeout=timeout
                    )
                elif spec.body_kind == "form":
                    response = await self._client.post(
                        url,
                        data=self._build_body(spec, normalized),
                        headers=request_headers,
                        timeout=timeout,
                    )
                else:
                    response = await self._client.post(
                        url,
                        json=self._build_body(spec, normalized),
                        headers=request_headers,
                        timeout=timeout,
                    )
                if (
                    endpoint_key in BSE_SESSION_EMPTY_RETRY_KEYS
                    and response.status_code == 200
                    and response.content.strip() in {b"", b"{}"}
                ):
                    # BSE can return a bare object during page/API session. On
                    # some hosts the same official sequence works through the
                    # stdlib transport but BSE returns {} to httpx.
                    if self._use_bse_browser_fallback:
                        fallback = await asyncio.to_thread(
                            self._bse_browser_fetch_sync,
                            endpoint_key=endpoint_key,
                            spec=spec,
                            url=url,
                            request_headers=request_headers,
                            timeout=timeout,
                        )
                        if fallback is not None:
                            response = fallback
                    if (
                        response.content.strip() in {b"", b"{}"}
                        and attempts < self._config.cache.max_retries
                    ):
                        await self._refresh_bse_session(
                            endpoint_key=endpoint_key,
                            spec=spec,
                            request_headers=request_headers,
                            timeout=timeout,
                        )
                        await asyncio.sleep(self._retry_delay(response, attempts))
                        continue
                if response.status_code not in retryable_statuses:
                    break
                if attempts >= self._config.cache.max_retries:
                    break
                if response.status_code in {401, 403} and spec.requires_nse_session:
                    self._nse_seeded = False
                    await self._seed_nse()
                await asyncio.sleep(self._retry_delay(response, attempts))
            if response is None:
                raise RuntimeError("endpoint request completed without a response")
            response.raise_for_status()
            body = response.content
            if len(body) > self._config.cache.max_response_bytes:
                raise ValueError(
                    f"response exceeds {self._config.cache.max_response_bytes} bytes"
                )
            media_type = response.headers.get("content-type", "").split(";", 1)[0]
            content_hash = hashlib.sha256(body).hexdigest()
            raw_path = self._archive(endpoint_key, body, media_type, content_hash)
            wrong_content = self._wrong_content_type(
                spec.response_kind, media_type, body
            )
            if wrong_content:
                result = EndpointFetchResult(
                    endpoint_key=endpoint_key,
                    state=FetchState.WRONG_CONTENT,
                    fetched_at=datetime.now(UTC),
                    url=url,
                    content_hash=content_hash,
                    raw_path=raw_path,
                    media_type=media_type,
                    can_score=False,
                    reason=f"Unexpected response content classified as {wrong_content}.",
                    status_code=response.status_code,
                    attempts=attempts,
                    error_type=wrong_content,
                )
                self._persist(result, parameter_hash)
                return result
            if spec.response_kind == "json":
                try:
                    payload = response.json()
                except json.JSONDecodeError as exc:
                    result = EndpointFetchResult(
                        endpoint_key=endpoint_key,
                        state=FetchState.WRONG_CONTENT,
                        fetched_at=datetime.now(UTC),
                        url=url,
                        content_hash=content_hash,
                        raw_path=raw_path,
                        media_type=media_type,
                        can_score=False,
                        reason=f"JSONDecodeError: {exc}",
                        status_code=response.status_code,
                        attempts=attempts,
                        error_type="INVALID_JSON",
                    )
                    self._persist(result, parameter_hash)
                    return result
                if isinstance(payload, dict) and isinstance(payload.get("d"), str):
                    try:
                        decoded = json.loads(payload["d"])
                    except json.JSONDecodeError:
                        decoded = None
                    if isinstance(decoded, (dict, list)):
                        payload = decoded
                media_type = media_type or "application/json"
            elif spec.response_kind == "binary":
                if not body:
                    payload = None
                elif "spreadsheetml" in media_type and not body.startswith(b"PK\x03\x04"):
                    result = EndpointFetchResult(
                        endpoint_key=endpoint_key,
                        state=FetchState.WRONG_CONTENT,
                        fetched_at=datetime.now(UTC),
                        url=url,
                        content_hash=content_hash,
                        raw_path=raw_path,
                        media_type=media_type,
                        can_score=False,
                        reason="Binary workbook response failed ZIP magic validation.",
                        status_code=response.status_code,
                        attempts=attempts,
                        error_type="BINARY_VALIDATION_FAILED",
                    )
                    self._persist(result, parameter_hash)
                    return result
                else:
                    payload = {"byteLength": len(body)}
            else:
                payload = response.text
                media_type = media_type or (
                    "text/html" if spec.response_kind == "html" else "text/plain"
                )
            record_count = self._record_count(payload, spec.response_kind)
            state = (
                FetchState.RAW_ARCHIVED if record_count > 0 else FetchState.NO_DATA_NOW
            )
            contract_note = (
                " Endpoint contract is unverified and remains research-only."
                if spec.contract_status == ContractStatus.UNVERIFIED_RESEARCH
                else ""
            )
            result = EndpointFetchResult(
                endpoint_key=endpoint_key,
                state=state,
                fetched_at=datetime.now(UTC),
                url=url,
                content_hash=content_hash,
                raw_path=raw_path,
                media_type=media_type,
                record_count=record_count,
                payload=payload,
                can_score=False,
                reason=(
                    "Raw response archived; source-specific schema, data-date, and freshness parsing is still required."
                    + contract_note
                    if state == FetchState.RAW_ARCHIVED
                    else "Endpoint responded successfully but has no records now."
                    + contract_note
                ),
                status_code=response.status_code,
                attempts=attempts,
            )
            self._persist(result, parameter_hash)
            return result

        except (httpx.HTTPError, ValueError) as exc:
            reason = f"{type(exc).__name__}: {exc}"
            error_type = self._exception_error_type(exc)
            status_code = (
                exc.response.status_code
                if isinstance(exc, httpx.HTTPStatusError)
                else response.status_code
                if response is not None
                else None
            )
            cached = self._latest_cached(
                endpoint_key,
                parameter_hash,
                reason,
                error_type=error_type,
                status_code=status_code,
                attempts=attempts,
            )
            if cached is not None:
                return cached
            logger.warning(
                "Institutional endpoint fetch failed for %s: %s", endpoint_key, reason
            )
            result = EndpointFetchResult(
                endpoint_key=endpoint_key,
                state=FetchState.BROKEN,
                fetched_at=datetime.now(UTC),
                url=url,
                can_score=False,
                reason=reason,
                status_code=status_code,
                attempts=attempts,
                error_type=error_type,
            )
            self._persist(result, parameter_hash)
            return result

    async def fetch_many(
        self,
        requests: list[tuple[str, dict[str, str]]],
        *,
        concurrency: int = 4,
    ) -> list[EndpointFetchResult]:
        if not 1 <= concurrency <= 8:
            raise ValueError("concurrency must be between 1 and 8")
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded(
            endpoint_key: str, parameters: dict[str, str]
        ) -> EndpointFetchResult:
            async with semaphore:
                return await self.fetch(endpoint_key, parameters)

        return await asyncio.gather(
            *(
                bounded(endpoint_key, parameters)
                for endpoint_key, parameters in requests
            )
        )
