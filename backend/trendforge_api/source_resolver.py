from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from html.parser import HTMLParser
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .amfi_scheme_wise import build_amfi_scheme_bundle
from .vyom_resolver import BrowserDiscovery, discover_links_with_vyom


AMFI_SCHEME_DIRECTORY_URL = (
    "https://www.amfiindia.com/otherdata/scheme-wise-disclosure"
)


@dataclass(frozen=True)
class SourceFetchAttempt:
    url: str
    fetcher: str
    stage: str
    result_state: str
    status_code: int | None = None
    content_type: str | None = None
    content_length: int | None = None
    duration_ms: int | None = None
    error: str | None = None
    can_unlock_ready: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "fetcher": self.fetcher,
            "stage": self.stage,
            "result_state": self.result_state,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "content_length": self.content_length,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "can_unlock_ready": self.can_unlock_ready,
        }


@dataclass(frozen=True)
class ResolvedFetch:
    url: str
    status_code: int
    headers: dict[str, str]
    content: bytes
    resolver_state: str
    attempted_urls: tuple[str, ...]
    attempts: tuple[SourceFetchAttempt, ...] = ()


class LinkExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_map = {key.lower(): value for key, value in attrs if value}
        href = attrs_map.get("href")
        if href:
            self._href = urljoin(self.base_url, href)
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append(
                {
                    "url": self._href,
                    "text": " ".join(part for part in self._text if part),
                }
            )
            self._href = None
            self._text = []


def recent_dates(days: int = 7, today: date | None = None) -> list[date]:
    current = today or date.today()
    return [current - timedelta(days=offset) for offset in range(days)]


def direct_download_candidates(source_key: str, today: date | None = None) -> list[str]:
    key = source_key.strip().lower()
    days = recent_dates(today=today)
    urls: list[str] = []
    if key == "nse_equity_universe":
        urls.append("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv")
    elif key == "nse_trading_calendar":
        urls.append("https://www.nseindia.com/api/holiday-master?type=trading")
    elif key == "nse_nifty500_constituents":
        urls.append(
            "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
        )
    elif key == "nse_nifty50_constituents":
        urls.append(
            "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
        )
    elif key == "nse_bhavcopy_eod":
        for item in days:
            if item.weekday() < 5:
                urls.append(
                    "https://archives.nseindia.com/archives/equities/bhavcopy/pr/"
                    f"PR{item.strftime('%d%m%y')}.zip"
                )
            yyyymmdd = item.strftime("%Y%m%d")
            urls.extend(
                [
                    f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{yyyymmdd}_F_0000.csv.zip",
                    f"https://archives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{yyyymmdd}_F_0000.csv.zip",
                ]
            )
    elif key in {"nse_trade_to_trade", "nse_pr_market_snapshot"}:
        for item in days:
            if item.weekday() < 5:
                urls.append(
                    "https://archives.nseindia.com/archives/equities/bhavcopy/pr/"
                    f"PR{item.strftime('%d%m%y')}.zip"
                )
    elif key == "kite_derivatives_contract_master":
        urls.append("https://api.kite.trade/instruments")
    elif key == "nse_board_meetings":
        urls.append(
            "https://www.nseindia.com/api/corporate-board-meetings?index=equities"
        )
    elif key == "nse_most_active_futures":
        urls.append(
            "https://www.nseindia.com/api/snapshot-derivatives-equity?index=futures"
        )
    elif key == "nse_most_active_options":
        urls.append(
            "https://www.nseindia.com/api/snapshot-derivatives-equity?index=options"
        )
    elif key == "nse_ipo_issue_calendar":
        # The two endpoint responses are bundled in resolve_and_fetch_source so
        # current, Closed and Forthcoming statuses retain their own labels.
        urls.extend(
            [
                "https://www.nseindia.com/api/ipo-current-issue",
                "https://www.nseindia.com/api/all-upcoming-issues?category=ipo",
            ]
        )
    elif key == "nse_index_close_eod":
        for item in days:
            urls.append(
                "https://nsearchives.nseindia.com/content/indices/"
                f"ind_close_all_{item.strftime('%d%m%Y')}.csv"
            )
    elif key == "nse_fii_dii":
        urls.append("https://www.nseindia.com/api/fiidiiTradeReact")
    elif key == "bse_fii_dii":
        urls.append("https://api.bseindia.com/BseIndiaAPI/api/CategoryTurnover/w")
    elif key == "bse_participant_oi":
        urls.append(
            "https://api.bseindia.com/BseIndiaAPI/api/DeriMarketDisclosureData_ng/w"
        )
    elif key == "nse_option_chain":
        urls.append(
            "https://www.nseindia.com/api/option-chain-equities?symbol=RELIANCE"
        )
    elif key == "nse_pit_current":
        urls.append("https://www.nseindia.com/api/corporates-pit")
    elif key == "nse_block_deal_live":
        urls.append("https://www.nseindia.com/api/block-deal")
    elif key == "nse_asm":
        urls.append("https://www.nseindia.com/api/reportASM")
    elif key == "nse_gsm":
        urls.append("https://www.nseindia.com/api/reportGSM")
    elif key == "nse_esm":
        urls.append("https://www.nseindia.com/api/reportESM")
    elif key == "nse_price_bands":
        for item in days:
            if item.weekday() < 5:
                urls.append(
                    "https://nsearchives.nseindia.com/content/equities/"
                    f"sec_list_{item.strftime('%d%m%Y')}.csv"
                )
    elif key == "nse_pledge_data":
        urls.append("https://www.nseindia.com/api/corporate-pledgeData")
    elif key == "nse_oi_spurts":
        urls.append("https://www.nseindia.com/api/live-analysis-oi-spurts-underlyings")
    elif key == "nsdl_fpi_daily":
        urls.append("https://fpi.nsdl.co.in/web/Reports/Latest.aspx")
    elif key == "cftc_cot":
        current_year = (today or date.today()).year
        urls.extend(
            [
                f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{current_year}.zip",
                "https://www.cftc.gov/dea/newcot/f_disagg.txt",
                "https://www.cftc.gov/dea/newcot/c_disagg.txt",
            ]
        )
    elif key == "eia_weekly_petroleum_stocks":
        urls.append("https://ir.eia.gov/wpsr/table1.csv")
    elif key == "world_gold_council_oi":
        urls.append("https://fsapi.gold.org/datawarehouseapi/api/total-open-interest")
    elif key == "wgc_gold_etf_holdings":
        urls.append(
            "https://fsapi.gold.org/api/v11/charts/etfv2/revised/holdings-chart2"
        )
    elif key == "wgc_gold_etf_flows":
        urls.append("https://fsapi.gold.org/api/v11/charts/etfv2/revised/flows-chart2")
    elif key == "sge_daily_report":
        for item in days:
            if item.weekday() < 5:
                day = item.isoformat()
                urls.append(
                    "https://en.sge.com.cn/h5_data_DailyReport?"
                    f"start_date={day}&end_date={day}"
                )
    elif key == "nse_participant_oi":
        for item in days:
            ddmmyyyy = item.strftime("%d%m%Y")
            urls.extend(
                [
                    f"https://archives.nseindia.com/content/nsccl/fao_participant_oi_{ddmmyyyy}.csv",
                    f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{ddmmyyyy}.csv",
                ]
            )
    elif key in {"nse_fno_ban", "nse_mwpl_ban"}:
        # Generic latest + dated archives (user-verified 2026-08 path family)
        urls.append("https://nsearchives.nseindia.com/content/fo/fo_secban.csv")
        urls.append("https://archives.nseindia.com/content/fo/fo_secban.csv")
        for item in days:
            ddmmyyyy = item.strftime("%d%m%Y")
            urls.extend(
                [
                    f"https://archives.nseindia.com/archives/fo/sec_ban/fo_secban_{ddmmyyyy}.csv",
                    f"https://nsearchives.nseindia.com/archives/fo/sec_ban/fo_secban_{ddmmyyyy}.csv",
                ]
            )
    elif key == "nse_mwpl_percentages":
        # NCL combined (market-wide) OI zip. Verified 2026-08-23: HTTP 200
        # application/zip at nsearchives .../archives/nsccl/mwpl/combineoi_DDMMYYYY.zip
        # containing combineoi_DDMMYYYY.csv with NSE Symbol, MWPL, Open Interest,
        # Future Equivalent Open Interest, Limit for Next Day.
        for item in days:
            ddmmyyyy = item.strftime("%d%m%Y")
            urls.extend(
                [
                    f"https://nsearchives.nseindia.com/archives/nsccl/mwpl/combineoi_{ddmmyyyy}.zip",
                    f"https://archives.nseindia.com/archives/nsccl/mwpl/combineoi_{ddmmyyyy}.zip",
                ]
            )
    elif key == "nse_mto_delivery":
        for item in days:
            ddmmyyyy = item.strftime("%d%m%Y")
            urls.extend(
                [
                    f"https://archives.nseindia.com/archives/equities/mto/MTO_{ddmmyyyy}.DAT",
                    f"https://nsearchives.nseindia.com/archives/equities/mto/MTO_{ddmmyyyy}.DAT",
                ]
            )
    elif key == "nse_short_selling":
        for item in days:
            ddmmyyyy = item.strftime("%d%m%Y")
            urls.extend(
                [
                    f"https://archives.nseindia.com/archives/equities/shortSelling/shortselling_{ddmmyyyy}.csv",
                    f"https://nsearchives.nseindia.com/archives/equities/shortSelling/shortselling_{ddmmyyyy}.csv",
                ]
            )
    elif key == "bse_fo_bhavcopy":
        for item in days:
            if item.weekday() < 5:
                yyyymmdd = item.strftime("%Y%m%d")
                urls.append(
                    "https://www.bseindia.com/download/BhavCopy/Derivative/"
                    f"BhavCopy_BSE_FO_0_0_0_{yyyymmdd}_F_0000.CSV"
                )
    elif key == "nse_preopen_cash":
        # Cash pre-open (constituents). Distinct from F&O pre-open.
        urls.extend(
            [
                "https://www.nseindia.com/api/market-data-pre-open?key=ALL",
                "https://www.nseindia.com/api/market-data-pre-open?key=NIFTY",
            ]
        )
    elif key == "bse_insider_trading":
        # Latest default set (Isdefault=1) — verified path family in 30-pack file
        urls.extend(
            [
                "https://api.bseindia.com/BseIndiaAPI/api/getCorp_Regulation_ng/w?scripCode=&Regulation=&fromDT=&ToDate=&Isdefault=1",
                "https://api.bseindia.com/BseIndiaAPI/api/InsiderTrade15/w?fromdt=&todt=&pageno=1&scripcode=",
            ]
        )
    elif key in {"nse_option_chain_nifty", "nse_index_option_chain_v3"}:
        urls.extend(
            [
                "https://www.nseindia.com/api/option-chain-contract-info?symbol=NIFTY",
                "https://www.nseindia.com/api/option-chain-equities?symbol=NIFTY",
            ]
        )
    elif key == "nse_option_chain_banknifty":
        urls.extend(
            [
                "https://www.nseindia.com/api/option-chain-contract-info?symbol=BANKNIFTY",
                "https://www.nseindia.com/api/option-chain-equities?symbol=BANKNIFTY",
            ]
        )
    elif key == "lbma_gold_silver_fix":
        urls.extend(
            [
                "https://prices.lbma.org.uk/json/gold_pm.json",
                "https://prices.lbma.org.uk/json/gold_am.json",
                "https://prices.lbma.org.uk/json/silver.json",
            ]
        )
    elif key == "eia_natgas_storage":
        urls.append("https://ir.eia.gov/ngs/wngsr.csv")
    elif key == "usda_wasde_cornell":
        urls.append(
            "https://usda.library.cornell.edu/concern/publications/3t945q76s?locale=en"
        )
    elif key == "rbi_fbil_usdinr":
        # GET yields the form shell; structured rates need form POST (parser marks needsPost).
        urls.append("https://www.rbi.org.in/scripts/ReferenceRateArchive.aspx")
    elif key == "nse_fii_derivatives_stats":
        for item in days:
            if item.weekday() < 5:
                # Prefer archive CSV (audit script pack) then classic XLS
                ymd = item.strftime("%Y%m%d")
                mon = item.strftime("%d-%b-%Y")
                urls.extend(
                    [
                        f"https://archives.nseindia.com/content/nsccl/fao_participant_fii_{ymd}.csv",
                        f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_fii_{ymd}.csv",
                        f"https://archives.nseindia.com/content/fo/fii_stats_{mon}.xls",
                        f"https://nsearchives.nseindia.com/content/fo/fii_stats_{mon}.xls",
                    ]
                )
    elif key == "nse_fo_bhavcopy":
        for item in days:
            yyyymmdd = item.strftime("%Y%m%d")
            urls.extend(
                [
                    f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv.zip",
                    f"https://archives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv.zip",
                ]
            )
    elif key == "nse_slb":
        for item in days:
            ddmmyyyy = item.strftime("%d%m%Y")
            urls.append(
                "https://nsearchives.nseindia.com/archives/slbs/open_pos/"
                f"slb_openpos_{ddmmyyyy}.csv"
            )
    elif key == "nse_large_deals":
        urls.extend(
            [
                "https://archives.nseindia.com/content/equities/bulk.csv",
                "https://archives.nseindia.com/content/equities/block.csv",
                "https://nsearchives.nseindia.com/content/equities/bulk.csv",
                "https://nsearchives.nseindia.com/content/equities/block.csv",
            ]
        )
    elif key == "nse_corporate_filings_actions":
        urls.append(
            "https://www.nseindia.com/api/corporates-corporateActions?index=equities"
        )
    elif key == "nse_daily_buyback":
        urls.append("https://www.nseindia.com/api/corporates-daily-buyback?")
    elif key == "bse_buyback_tender":
        urls.append(
            "https://api.bseindia.com/BseIndiaAPI/api/"
            "Mkt_Pubissues_FIS_BuybackTenderoffer_isd_ng/w?fromdt=&todt=&company="
        )
    elif key == "bse_takeover_open_offer":
        urls.append(
            "https://api.bseindia.com/BseIndiaAPI/api/"
            "Mkt_Pubissues_FIS_Takeover_isd_ng/w?fromdt=&todt=&company="
        )
    elif key in {"amfi_monthly_portfolio", "amfi_scheme_wise"}:
        urls.extend(
            [
                "https://www.amfiindia.com/online-center/portfolio-disclosure",
                "https://www.amfiindia.com/otherdata/scheme-wise-disclosure",
                "https://portal.amfiindia.com/DownloadSchemeData.aspx?mf=0",
            ]
        )
    elif key == "amfi_nav":
        urls.append("https://www.amfiindia.com/spages/NAVAll.txt")
    elif key == "bse_bhavcopy_eod":
        for item in days:
            if item.weekday() < 5:
                urls.extend(
                    [
                        "https://www.bseindia.com/download/BhavCopy/Equity/"
                        f"BhavCopy_BSE_CM_0_0_0_{item.strftime('%Y%m%d')}_F_0000.csv",
                        "https://www.bseindia.com/download/BhavCopy/Equity/"
                        f"EQ{item.strftime('%d%m%y')}_CSV.ZIP",
                    ]
                )
    elif key == "fred_real_yield_10y":
        urls.append("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10")
    elif key == "fred_broad_dollar_index":
        urls.append("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS")
    # MCX has no verified stable direct artifact contract in this build. Do not
    # manufacture dated URLs: the catalog page must remain fail-closed until a
    # real download contract is captured and fixture-tested.
    return urls


def request_headers(url: str) -> dict[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 TrendForgeLocalResearch/0.1",
        "Accept": "text/csv,application/json,application/zip,application/octet-stream,text/plain,text/html,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if "api.bseindia.com" in url.lower():
        headers.update(
            {
                "Origin": "https://www.bseindia.com",
                "Referer": "https://www.bseindia.com/",
            }
        )
    if "nseindia.com/api/" in url.lower():
        headers["Referer"] = "https://www.nseindia.com/"
        headers["Accept"] = "application/json,text/plain,*/*"
    if "amfiindia.com/api/" in url.lower():
        headers["Referer"] = (
            "https://www.amfiindia.com/otherdata/scheme-wise-disclosure"
        )
    if "fsapi.gold.org" in url.lower():
        headers["Referer"] = "https://www.gold.org/"
    return headers


def fetch_url(url: str, timeout_seconds: int = 15) -> tuple[int, dict[str, str], bytes]:
    request = Request(
        url,
        headers=request_headers(url),
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        return int(getattr(response, "status", 200)), headers, response.read()


def _fetch_with_retry(
    url: str,
    timeout_seconds: int,
    *,
    fetcher: Callable[[str, int], tuple[int, dict[str, str], bytes]] | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    max_attempts: int = 3,
) -> tuple[int, dict[str, str], bytes]:
    """Retry bounded transient transport failures without hiding permanent errors."""
    operation = fetcher or fetch_url
    attempts = max(1, min(max_attempts, 3))
    for attempt in range(1, attempts + 1):
        try:
            return operation(url, timeout_seconds)
        except HTTPError as exc:
            if exc.code not in {408, 425, 429, 500, 502, 503, 504} or attempt == attempts:
                raise
        except (URLError, TimeoutError, OSError):
            if attempt == attempts:
                raise
        sleeper(0.25 * attempt)
    raise RuntimeError("unreachable retry state")


def looks_like_data(url: str, content: bytes) -> bool:
    lower_url = url.lower()
    head = content[:500].lstrip().lower()
    if "fiiinvestsector_" in lower_url or "fiiinestsector_" in lower_url:
        return b"<table" in content.lower()
    if "en.sge.com.cn/h5_data_dailyreport" in lower_url:
        query_date = re.search(r"start_date=(\d{4}-\d{2}-\d{2})", lower_url)
        if not query_date:
            return False
        marker = f"<td>{query_date.group(1)}</td>".encode()
        normalized = re.sub(rb"\s+", b"", content.lower())
        return marker in normalized and b"<td>au(t+d)</td>" in normalized
    if any(
        lower_url.endswith(ext) for ext in (".csv", ".txt", ".zip", ".gz", ".xls", ".xlsx")
    ):
        if b"<!doctype html" in head or b"<html" in head:
            return False
        return bool(content)
    if (
        b"<!doctype html" in head or b"<html" in head
    ) and b"<table" not in content[:5000].lower():
        return False
    return bool(content)


def filter_download_links(
    links_to_filter: list[dict[str, str]], source_key: str
) -> list[str]:
    keywords = {
        "nse_equity_universe": ("equity", "securities", "equity_l"),
        "nse_trading_calendar": ("holiday", "trading calendar", "session"),
        "nse_nifty500_constituents": ("nifty 500", "constituents", "stocks"),
        "nse_bhavcopy_eod": ("bhavcopy", "cm udiff", "capital market"),
        "nse_index_close_eod": ("indices", "index close", "historical index"),
        "nse_fno_ban": ("ban", "fo_secban"),
        "nse_mwpl_ban": ("ban", "fo_secban"),
        "nse_mwpl_percentages": ("mwpl", "position limit", "utilization"),
        "nse_participant_oi": ("participant", "oi", "fao_participant"),
        "nse_large_deals": ("bulk", "block", "large"),
        "amfi_monthly_portfolio": ("portfolio", "scheme", "download"),
        "amfi_scheme_wise": ("scheme", "portfolio", "download"),
        "mcx_bhavcopy": ("bhav", "bhavcopy", "download"),
        "cftc_cot": ("cot", "commitment", "newcot", "disagg"),
        "nse_corporate_filings_actions": (
            "corporate",
            "action",
            "download",
        ),
        "nse_daily_buyback": ("buyback", "buy back", "download"),
        "nse_auction_securities": (
            "illiquid",
            "periodic call auction",
            "contract_mas_illiquid_sec",
        ),
    }.get(source_key, ())
    links: list[str] = []
    for link in links_to_filter:
        combined = f"{link['text']} {link['url']}".lower()
        if "#" in link["url"] or "javascript:" in link["url"].lower():
            continue
        if keywords and not any(keyword in combined for keyword in keywords):
            continue
        if re.search(r"\.(csv|txt|zip|xls|xlsx)(?:$|\?)", link["url"].lower()) or any(
            keyword in combined for keyword in keywords
        ):
            links.append(link["url"])
    return list(dict.fromkeys(links))


def discover_download_links(base_url: str, html: bytes, source_key: str) -> list[str]:
    extractor = LinkExtractor(base_url)
    try:
        extractor.feed(html.decode("utf-8", errors="replace"))
    except Exception:
        return []
    return filter_download_links(extractor.links, source_key)


def discover_nsdl_fortnightly_report_links(
    selection_url: str, html: bytes
) -> list[str]:
    """Extract newest-first official NSDL static report links from the selector."""
    text = html.decode("utf-8", errors="replace")
    values = re.findall(
        r"<option\b[^>]*\bvalue\s*=\s*['\"]([^'\"]+)['\"]",
        text,
        flags=re.IGNORECASE,
    )
    links: list[str] = []
    for value in values:
        if "fortnightly_sector_wise_fii_investment_data" not in value.casefold():
            continue
        if not re.search(r"FIIIn?vestSector_.*\.html?$", value, re.IGNORECASE):
            continue
        relative = f"/{value[2:]}" if value.startswith("~/") else value
        links.append(urljoin(selection_url, relative))
    return list(dict.fromkeys(links))


def _nsdl_fortnightly_report_is_usable(content: bytes, url: str) -> bool:
    from .parsers.surveillance_pledge_fpi_parser import parse_nsdl_fpi_fortnightly

    parsed = parse_nsdl_fpi_fortnightly(content, url=url)
    return (
        parsed.get("parser_state") == "PARSED_STRUCTURED"
        and int(parsed.get("record_count") or 0) > 0
    )


def _http_attempt(
    url: str,
    stage: str,
    timeout_seconds: int,
    *,
    fetcher: Callable[[str, int], tuple[int, dict[str, str], bytes]] | None = None,
) -> tuple[tuple[int, dict[str, str], bytes] | None, SourceFetchAttempt]:
    started = time.perf_counter()
    try:
        active_fetcher = fetcher or fetch_url
        status, headers, content = active_fetcher(url, timeout_seconds)
        data_candidate = status < 400 and looks_like_data(url, content)
        state = (
            "DATA_CANDIDATE"
            if data_candidate
            else "HTTP_ERROR"
            if status >= 400
            else "NON_DATA_RESPONSE"
        )
        attempt = SourceFetchAttempt(
            url=url,
            fetcher="TRENDFORGE_HTTP",
            stage=stage,
            result_state=state,
            status_code=status,
            content_type=headers.get("content-type"),
            content_length=len(content),
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
        return (status, headers, content), attempt
    except Exception as exc:
        return None, SourceFetchAttempt(
            url=url,
            fetcher="TRENDFORGE_HTTP",
            stage=stage,
            result_state="FETCH_ERROR",
            duration_ms=round((time.perf_counter() - started) * 1000),
            error=f"{type(exc).__name__}: {str(exc)[:500]}",
        )


def resolve_and_fetch_source(
    source_key: str,
    catalog_url: str,
    timeout_seconds: int = 15,
    browser_discoverer: Callable[[str, int], BrowserDiscovery] | None = None,
    today: date | None = None,
) -> ResolvedFetch:
    attempts: list[SourceFetchAttempt] = []
    key = source_key.strip().lower()

    # Phase-3 multi-step fetchers (form POST / cookie + expiry resolve)
    if key in {
        "rbi_fbil_usdinr",
        "nse_index_option_chain_v3",
        "dgcis_trade_data",
        "yahoo_cme_proxy",
        "yahoo_lme_proxy",
        "mcx_top_participants",
        "mcx_bhavcopy",
        "mcx_market_watch",
        "mcx_option_chain",
        "mcx_warehouse_stocks",
        "mcx_delivery_reports",
        "ncdex_bhavcopy",
        "amfi_portfolio_disclosure",
        "nse_bulk_deals_today_csv",
        "nse_bulk_deal_symbol",
        "nse_quote_equity_trade_info",
        "cdsl_fpi_fortnightly",
        "usda_wasde_cornell",
        "eia_natgas_storage",
        # Institutional / commodity regime feeds (from scripts/incoming_40pack audit)
        "nse_fii_dii",
        "bse_fii_dii",
        "bse_participant_oi",
        "nse_participant_oi",
        "nse_fii_derivatives_stats",
        "cftc_cot",
        "tradingeconomics_bdi",
        "yahoo_bdry_shipping_proxy",
        "google_trends_india_rss",
        "crisil_ratings",
        "icra_ratings",
        "care_ratings",
        "google_news_rss",
        "angelone_instrument_master",
        "dhan_instrument_master",
        "nse_market_status",
        "rupeevest_mf_flows",
        "amfi_monthly_aum",
        "lme_warehouse_stocks",
        "eia_steo_opec_supply",
        "opec_production_adjustment",
        "rbi_tbill_yield",
        "screener_in_fii_holding_change",
        "tickertape_fii_holding_change_3m",
        "dhan_fii_holding_change",
        "equitymaster_fii_buys_reference",
    }:
        from .phase3_multi_step_fetch import (
            fetch_bse_fii_dii_category_turnover,
            fetch_bse_participant_oi_disclosure,
            fetch_cdsl_or_nsdl_fpi,
            fetch_cftc_cot_disagg,
            fetch_dgcis_imports,
            fetch_eia_natgas_storage,
            fetch_mcx_post_json,
            fetch_mcx_bhavcopy_page,
            fetch_mcx_top_participants,
            fetch_mcx_warehouse_position,
            fetch_ncdex_bhav_or_watch,
            fetch_nse_bulk_deal_symbol,
            fetch_nse_fii_derivatives_archive,
            fetch_nse_fii_dii_api,
            fetch_nse_index_option_chain_v3,
            fetch_nse_participant_oi_archive,
            fetch_nse_trade_info,
            fetch_rbi_usdinr_form_post,
            fetch_google_trends_india_rss,
            fetch_crisil_ratings,
            fetch_icra_ratings,
            fetch_care_ratings,
            fetch_google_news_rss,
            fetch_angelone_instrument_master,
            fetch_dhan_instrument_master,
            fetch_nse_market_status,
            fetch_rupeevest_mf_flows,
            fetch_amfi_monthly_aum,
            fetch_westmetall_lme,
            fetch_eia_steo_opec_supply,
            fetch_opec_production_adjustment,
            fetch_rbi_tbill_yield,
            fetch_screener_in_fii_holding_change,
            fetch_tickertape_fii_holding_change_3m,
            fetch_dhan_fii_holding_change,
            fetch_equitymaster_fii_buys_reference,
            fetch_tradingeconomics_bdi,
            fetch_usda_wasde,
            fetch_yahoo_symbols,
        )

        if key == "rbi_fbil_usdinr":
            multi = fetch_rbi_usdinr_form_post()
            method = "RBI_USDINR_FORM_POST"
        elif key == "nse_index_option_chain_v3":
            multi = fetch_nse_index_option_chain_v3("NIFTY")
            method = "NSE_INDEX_OPTION_CHAIN_V3"
        elif key == "dgcis_trade_data":
            multi = fetch_dgcis_imports()
            method = "DGCIS_CSRF_FORM"
        elif key == "yahoo_cme_proxy":
            multi = fetch_yahoo_symbols(
                ["GC=F", "SI=F", "HG=F", "CL=F", "NG=F", "ZW=F", "ZC=F", "ZS=F"]
            )
            method = "YAHOO_CME_PROXY"
        elif key == "yahoo_lme_proxy":
            multi = fetch_yahoo_symbols(["ALI=F", "HG=F"])
            method = "YAHOO_LME_PROXY"
        elif key == "mcx_top_participants":
            multi = fetch_mcx_top_participants()
            method = "MCX_TOP_PARTICIPANTS"
        elif key == "mcx_bhavcopy":
            multi = fetch_mcx_bhavcopy_page()
            method = "MCX_BHAVCOPY_CHROME_TLS"
        elif key == "mcx_market_watch":
            multi = fetch_mcx_post_json("/backpage.aspx/GetMarketWatch", {})
            method = "MCX_MARKET_WATCH_POST"
        elif key == "mcx_option_chain":
            multi = fetch_mcx_post_json(
                "/backpage.aspx/GetOptionChain",
                {"Commodity": "GOLD", "Expiry": "", "Symbol": "GOLD"},
            )
            method = "MCX_OPTION_CHAIN_POST"
        elif key in {"mcx_warehouse_stocks", "mcx_delivery_reports"}:
            # Prefer official MCXCCL stock-position path; then legacy watch/proxy
            multi = fetch_mcx_warehouse_position()
            if not multi.ok:
                multi = fetch_mcx_post_json("/backpage.aspx/GetMarketWatch", {})
            if not multi.ok:
                multi = fetch_mcx_top_participants()
            method = "MCX_WAREHOUSE_OR_DELIVERY"
        elif key == "ncdex_bhavcopy":
            multi = fetch_ncdex_bhav_or_watch()
            method = "NCDEX_BHAV_OR_WATCH"
        elif key == "amfi_portfolio_disclosure":
            from .phase3_multi_step_fetch import MultiStepFetchResult as MSR
            import requests as _req

            u = "https://www.amfiindia.com/online-center/portfolio-disclosure"
            try:
                rr = _req.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
                multi = MSR(
                    rr.status_code < 400,
                    u,
                    rr.status_code,
                    rr.content,
                    rr.headers.get("content-type", "text/html"),
                    None if rr.status_code < 400 else f"HTTP {rr.status_code}",
                )
            except Exception as exc:  # noqa: BLE001
                multi = MSR(False, catalog_url, 0, b"", "text/html", str(exc))
            method = "AMFI_PORTFOLIO_DIR"
        elif key == "nse_bulk_deals_today_csv":
            from .phase3_multi_step_fetch import MultiStepFetchResult as MSR
            import requests as _req

            u = "https://archives.nseindia.com/content/equities/bulk.csv"
            try:
                rr = _req.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
                multi = MSR(
                    rr.status_code < 400,
                    u,
                    rr.status_code,
                    rr.content,
                    rr.headers.get("content-type", "text/csv"),
                    None if rr.status_code < 400 else f"HTTP {rr.status_code}",
                )
            except Exception as exc:  # noqa: BLE001
                multi = MSR(False, u, 0, b"", "text/csv", str(exc))
            method = "NSE_BULK_CSV"
        elif key == "nse_bulk_deal_symbol":
            multi = fetch_nse_bulk_deal_symbol("RELIANCE")
            method = "NSE_BULK_DEAL_SYMBOL"
        elif key == "nse_quote_equity_trade_info":
            multi = fetch_nse_trade_info("RELIANCE")
            method = "NSE_TRADE_INFO"
        elif key == "cdsl_fpi_fortnightly":
            multi = fetch_cdsl_or_nsdl_fpi()
            method = "CDSL_OR_NSDL_FPI"
        elif key == "usda_wasde_cornell":
            multi = fetch_usda_wasde()
            method = "USDA_WASDE"
        elif key == "eia_natgas_storage":
            multi = fetch_eia_natgas_storage()
            method = "EIA_NATGAS_STORAGE"
        elif key == "nse_fii_dii":
            multi = fetch_nse_fii_dii_api()
            method = "NSE_FII_DII_COOKIE_API"
        elif key == "bse_fii_dii":
            multi = fetch_bse_fii_dii_category_turnover()
            method = "BSE_CATEGORY_TURNOVER_FII_DII"
        elif key == "bse_participant_oi":
            multi = fetch_bse_participant_oi_disclosure()
            method = "BSE_DERI_MARKET_DISCLOSURE_OI"
        elif key == "nse_participant_oi":
            multi = fetch_nse_participant_oi_archive()
            method = "NSE_PARTICIPANT_OI_ARCHIVE"
        elif key == "nse_fii_derivatives_stats":
            multi = fetch_nse_fii_derivatives_archive()
            method = "NSE_FII_DERIVATIVES_ARCHIVE"
        elif key == "cftc_cot":
            multi = fetch_cftc_cot_disagg()
            method = "CFTC_COT_DISAGG"
        elif key == "tradingeconomics_bdi":
            multi = fetch_tradingeconomics_bdi()
            method = "TRADINGECONOMICS_BDI_HTML"
        elif key == "yahoo_bdry_shipping_proxy":
            multi = fetch_yahoo_symbols(["BDRY"], range_="1y")
            method = "YAHOO_BDRY_SHIPPING_ETF_PROXY"
        elif key == "google_trends_india_rss":
            multi = fetch_google_trends_india_rss()
            method = "GOOGLE_TRENDS_INDIA_RSS"
        elif key == "crisil_ratings":
            multi = fetch_crisil_ratings()
            method = "CRISIL_RATING_RATIONALES_JSON"
        elif key == "icra_ratings":
            multi = fetch_icra_ratings()
            method = "ICRA_RATING_RATIONALES_CSRF_HTML"
        elif key == "care_ratings":
            multi = fetch_care_ratings()
            method = "CARE_RATING_RATIONALES_JSON"
        elif key == "google_news_rss":
            multi = fetch_google_news_rss()
            method = "GOOGLE_NEWS_RSS_BUNDLE"
        elif key == "angelone_instrument_master":
            multi = fetch_angelone_instrument_master()
            method = "ANGELONE_PUBLIC_INSTRUMENT_MASTER"
        elif key == "dhan_instrument_master":
            multi = fetch_dhan_instrument_master()
            method = "DHAN_PUBLIC_INSTRUMENT_MASTER"
        elif key == "nse_market_status":
            multi = fetch_nse_market_status()
            method = "NSE_MARKET_STATUS_COOKIE_API"
        elif key == "rupeevest_mf_flows":
            multi = fetch_rupeevest_mf_flows()
            method = "RUPEEVEST_PUBLIC_MF_FLOW_BUNDLE"
        elif key == "amfi_monthly_aum":
            multi = fetch_amfi_monthly_aum()
            method = "AMFI_MONTHLY_AUM_WORKBOOK"
        elif key == "lme_warehouse_stocks":
            multi = fetch_westmetall_lme()
            method = "WESTMETALL_LME_SHARED_SESSION_FALLBACK"
        elif key == "eia_steo_opec_supply":
            multi = fetch_eia_steo_opec_supply()
            method = "EIA_STEO_OPEC_SUPPLY_WORKBOOK"
        elif key == "opec_production_adjustment":
            multi = fetch_opec_production_adjustment()
            method = "OPEC_PRODUCTION_ADJUSTMENT_RELEASE"
        elif key == "rbi_tbill_yield":
            multi = fetch_rbi_tbill_yield()
            method = "RBI_TBILL_LATEST_FULL_AUCTION_RESULT"
        elif key == "screener_in_fii_holding_change":
            multi = fetch_screener_in_fii_holding_change()
            method = "SCREENER_IN_FII_HOLDING_HTML"
        elif key == "tickertape_fii_holding_change_3m":
            multi = fetch_tickertape_fii_holding_change_3m()
            method = "TICKERTAPE_FII_HOLDING_QUERY"
        elif key == "dhan_fii_holding_change":
            multi = fetch_dhan_fii_holding_change()
            method = "DHAN_FII_HOLDING_CUSTOMSCAN"
        elif key == "equitymaster_fii_buys_reference":
            multi = fetch_equitymaster_fii_buys_reference()
            method = "EQUITYMASTER_FII_BUYS_HTML"
        else:
            from .phase3_multi_step_fetch import MultiStepFetchResult as MSR

            multi = MSR(False, catalog_url, 0, b"", "text/plain", "unhandled key")
            method = "UNHANDLED"
        return ResolvedFetch(
            multi.url or catalog_url,
            (
                multi.status_code
                if multi.ok and multi.status_code
                else 200
                if multi.ok
                else 599
            ),
            {"content-type": multi.media_type},
            multi.content if multi.ok else b"",
            method if multi.ok else f"{method}_FAILED",
            (multi.url or catalog_url,),
            (),
        )

    if source_key.strip().lower() == "nsdl_fpi_fortnightly":
        selection_urls = list(
            dict.fromkeys(
                (
                    catalog_url,
                    "https://www.fpi.nsdl.co.in/web/Reports/FPI_Fortnightly_Selection.aspx",
                    "https://pilot.fpi.nsdl.co.in/Reports/FPI_Fortnightly_Selection.aspx",
                )
            )
        )
        for selection_url in selection_urls:
            selection, selection_attempt = _http_attempt(
                selection_url,
                "NSDL_FORTNIGHTLY_DIRECTORY_FETCH",
                timeout_seconds,
                fetcher=_fetch_with_retry,
            )
            attempts.append(selection_attempt)
            if not selection or selection[0] >= 400:
                continue
            report_links = discover_nsdl_fortnightly_report_links(
                selection_url, selection[2]
            )
            for report_url in report_links[:5]:
                report, report_attempt = _http_attempt(
                    report_url,
                    "NSDL_FORTNIGHTLY_REPORT_FETCH",
                    timeout_seconds,
                    fetcher=_fetch_with_retry,
                )
                attempts.append(report_attempt)
                if (
                    report
                    and report[0] < 400
                    and _nsdl_fortnightly_report_is_usable(report[2], report_url)
                ):
                    status, headers, content = report
                    return ResolvedFetch(
                        report_url,
                        status,
                        headers,
                        content,
                        "NSDL_FORTNIGHTLY_STATIC_REPORT",
                        tuple(item.url for item in attempts),
                        tuple(attempts),
                    )
        return ResolvedFetch(
            catalog_url,
            599,
            {},
            b"",
            "NSDL_FORTNIGHTLY_REPORT_UNAVAILABLE",
            tuple(item.url for item in attempts),
            tuple(attempts),
        )
    if source_key.strip().lower() == "nse_ipo_issue_calendar":
        combined: list[dict[str, object]] = []
        for section, url in (
            ("current", "https://www.nseindia.com/api/ipo-current-issue"),
            ("issue_calendar", "https://www.nseindia.com/api/all-upcoming-issues?category=ipo"),
        ):
            fetched, attempt = _http_attempt(url, "NSE_IPO_SECTION_FETCH", timeout_seconds)
            attempts.append(attempt)
            if not fetched or attempt.result_state != "DATA_CANDIDATE":
                continue
            try:
                payload = json.loads(fetched[2])
                rows = payload if isinstance(payload, list) else payload.get("data", [])
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                rows = []
            for raw in rows:
                if isinstance(raw, dict):
                    combined.append({**raw, "feedSection": section})
        if combined:
            content = json.dumps({"data": combined}, ensure_ascii=False).encode("utf-8")
            return ResolvedFetch(
                "https://www.nseindia.com/api/ipo-current-issue|all-upcoming-issues?category=ipo",
                200,
                {
                    "content-type": "application/vnd.trendforge.nse-ipo-bundle+json",
                    "content-length": str(len(content)),
                },
                content,
                "NSE_IPO_OFFICIAL_API_BUNDLE",
                tuple(item.url for item in attempts),
                tuple(attempts),
            )
        return ResolvedFetch(
            catalog_url,
            599,
            {},
            b"",
            "NSE_IPO_BUNDLE_EMPTY",
            tuple(item.url for item in attempts),
            tuple(attempts),
        )
    if source_key.strip().lower() == "amfi_scheme_wise":
        directory_url = AMFI_SCHEME_DIRECTORY_URL
        catalog_fetch, catalog_attempt = _http_attempt(
            directory_url,
            "AMFI_DIRECTORY_FETCH",
            timeout_seconds,
            fetcher=_fetch_with_retry,
        )
        attempts.append(catalog_attempt)
        if not catalog_fetch or catalog_fetch[0] >= 400:
            return ResolvedFetch(
                directory_url,
                catalog_fetch[0] if catalog_fetch else 599,
                catalog_fetch[1] if catalog_fetch else {},
                b"",
                "AMFI_DIRECTORY_ERROR",
                tuple(item.url for item in attempts),
                tuple(attempts),
            )
        try:
            bundle, amfi_attempts = build_amfi_scheme_bundle(
                catalog_fetch[2],
                fetcher=_fetch_with_retry,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            attempts.append(
                SourceFetchAttempt(
                    url=directory_url,
                    fetcher="TRENDFORGE_AMFI_API",
                    stage="AMFI_BUNDLE_BUILD",
                    result_state="FETCH_ERROR",
                    error=f"{type(exc).__name__}: {str(exc)[:500]}",
                )
            )
            return ResolvedFetch(
                directory_url,
                599,
                {},
                b"",
                "AMFI_BUNDLE_ERROR",
                tuple(item.url for item in attempts),
                tuple(attempts),
            )
        attempts.extend(
            SourceFetchAttempt(
                url=item.url,
                fetcher="TRENDFORGE_AMFI_API",
                stage="AMFI_SCHEME_API_FETCH",
                result_state=item.result_state,
                status_code=item.status_code,
                content_type=item.content_type,
                content_length=item.content_length,
                error=item.error,
            )
            for item in amfi_attempts
        )
        return ResolvedFetch(
            "https://www.amfiindia.com/api/schemewisedisclosure-investment?quarter=resolved",
            200,
            {
                "content-type": "application/vnd.trendforge.amfi-scheme-bundle+json",
                "content-length": str(len(bundle)),
            },
            bundle,
            "AMFI_OFFICIAL_API_BUNDLE",
            tuple(item.url for item in attempts),
            tuple(attempts),
        )
    direct_candidates = direct_download_candidates(source_key, today=today)
    for url in direct_candidates:
        fetched, attempt = _http_attempt(url, "DIRECT_CANDIDATE_FETCH", timeout_seconds)
        attempts.append(attempt)
        if fetched and attempt.result_state == "DATA_CANDIDATE":
            status, headers, content = fetched
            return ResolvedFetch(
                url,
                status,
                headers,
                content,
                "DIRECT_DOWNLOAD",
                tuple(item.url for item in attempts),
                tuple(attempts),
            )

    catalog_fetch, catalog_attempt = _http_attempt(
        catalog_url, "CATALOG_FETCH", timeout_seconds
    )
    attempts.append(catalog_attempt)
    if catalog_fetch:
        status, headers, content = catalog_fetch
        static_links = discover_download_links(catalog_url, content, source_key)
        for link in static_links:
            fetched, attempt = _http_attempt(
                link, "STATIC_DISCOVERED_FETCH", timeout_seconds
            )
            attempts.append(attempt)
            if fetched and attempt.result_state == "DATA_CANDIDATE":
                link_status, link_headers, link_content = fetched
                return ResolvedFetch(
                    link,
                    link_status,
                    link_headers,
                    link_content,
                    "DISCOVERED_DOWNLOAD",
                    tuple(item.url for item in attempts),
                    tuple(attempts),
                )
    else:
        status, headers, content = 599, {}, b""

    discoverer = browser_discoverer or discover_links_with_vyom
    started = time.perf_counter()
    discovery = discoverer(catalog_url, timeout_seconds)
    attempts.append(
        SourceFetchAttempt(
            url=catalog_url,
            fetcher="VYOM_CRAWL4AI",
            stage="VYOM_DISCOVERY",
            result_state=discovery.state,
            content_type="application/vnd.trendforge.link-candidates+json",
            content_length=len(discovery.links),
            duration_ms=round((time.perf_counter() - started) * 1000),
            error=discovery.error,
            can_unlock_ready=False,
        )
    )
    browser_links = filter_download_links(list(discovery.links), source_key)
    for link in browser_links:
        fetched, attempt = _http_attempt(link, "VYOM_CANDIDATE_FETCH", timeout_seconds)
        attempts.append(attempt)
        if fetched and attempt.result_state == "DATA_CANDIDATE":
            link_status, link_headers, link_content = fetched
            return ResolvedFetch(
                link,
                link_status,
                link_headers,
                link_content,
                "VYOM_DISCOVERED_DOWNLOAD",
                tuple(item.url for item in attempts),
                tuple(attempts),
            )

    resolver_state = "CATALOG_PAGE"
    if status >= 400:
        resolver_state = "CATALOG_HTTP_ERROR"
    return ResolvedFetch(
        catalog_url,
        status,
        headers,
        content,
        resolver_state,
        tuple(item.url for item in attempts),
        tuple(attempts),
    )
