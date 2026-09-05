"""
FII-buying stock data downloader for a custom scanner.

HONEST SCOPE (read before using):
  These four sites are THIRD-PARTY screeners. They are NOT NSE/BSE daily
  FII/DII stock tape. Typical field is FII *holding % change* (often 3M / QoQ
  from shareholding). That is quarterly ownership change, not "FII bought
  RELIANCE today".

  - screener.in  -> company Name, usually NO ticker
  - tickertape   -> ticker + forInstHldng3M (3-month FII holding change)
  - dhan         -> Sym + FIIHLDChagPer (holding-change %, not daily flow)
  - equitymaster -> Cloudflare; name-first; already catalogued as reference

  Rail: INFO / DISCOVERY only. Do NOT register as consensus VOTE.
  Do NOT pin MD69 / EXPECTED_SOURCE_COUNT from this script.
  Scraping may violate site terms; unofficial; can break without notice.

  Official daily FII file remains market totals (nse_fii_dii / bse_fii_dii).
  Official stock-level FII % is quarterly shareholding, when parsed.

Sources & how the data is actually obtained:
  1. Screener.in   -> server-rendered HTML table, paginated (?page=N) -> pandas.read_html
  2. Tickertape    -> public JSON screener API  POST https://api.tickertape.in/screener/query
                      (the /stocks/collections/fii-buying-stocks page is a wrapper around a
                       prebuilt screen; the prebuilt endpoint wants a token, but /screener/query
                       is open and lets you rebuild the same filter: forInstHldng3M > 0)
  3. Dhan          -> public JSON API  POST https://ow-scanx-analytics.dhan.co/customscan/fetchdt
                      (same payload the website sends: FIIHLDChagPer gte 3, Seg=E, OgInst=ES)
  4. Equitymaster  -> Cloudflare-protected. Plain HTTP often returns 403 from cloud IPs.
                      Falls back to Playwright (real browser). Run from your own machine.

Install:
    pip install requests pandas lxml html5lib
    # only needed for Equitymaster:
    pip install playwright && playwright install chromium

Usage:
    python fii_sources.py                     # fetch all, write CSVs to ./data
    python fii_sources.py --only screener tickertape
    python fii_sources.py --outdir ./data --tt-min-change 0.5 --dhan-min-change 3
    python fii_sources.py --catalog           # dump Tickertape field catalog
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
TIMEOUT = 30


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        }
    )
    return s


def _num(x: Any) -> Optional[float]:
    """'Rs 1,24,211' / '4.38%' / '-' -> float or None"""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).replace(",", "").replace("\u20b9", "").replace("%", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


# ----------------------------------------------------------------------------
# 1. SCREENER.IN
# ----------------------------------------------------------------------------
SCREENER_URL = "https://www.screener.in/screens/{screen_id}/{slug}/"


def fetch_screener(
    screen_id: str = "343087",
    slug: str = "fii-buying",
    max_pages: int = 25,
    pause: float = 1.0,
) -> pd.DataFrame:
    """Scrape a Screener.in saved screen (all pages).

    Columns for screen 343087 include:
      Name, CMP Rs., P/E, Mar Cap Rs.Cr., Div Yld %, NP Qtr, Qtr Profit Var %,
      Sales Qtr, Qtr Sales Var %, ROCE %, 'Chg in FII Hold %', 'FII Hold %'
    """
    s = _session()
    base = SCREENER_URL.format(screen_id=screen_id, slug=slug)
    frames: List[pd.DataFrame] = []
    total_pages: Optional[int] = None

    for page in range(1, max_pages + 1):
        r = s.get(base, params={"page": page}, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text

        if total_pages is None:
            m = re.search(r"Showing page\s+\d+\s+of\s+(\d+)", html)
            total_pages = int(m.group(1)) if m else 1

        try:
            df = pd.read_html(io.StringIO(html))[0]
        except (ValueError, IndexError):
            break

        df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
        if "Name" not in df.columns:
            break

        # last row of each page is the "Median" summary row -> drop it
        df = df[df["Name"].notna() & (df["Name"].astype(str).str.strip() != "Median:")]
        if "S.No." in df.columns:
            df = df[df["S.No."].astype(str).str.strip().str.lower() != "nan"]
        df = df.copy()
        df["page"] = page
        frames.append(df)

        if page >= total_pages:
            break
        time.sleep(pause)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    out = out.drop(columns=[c for c in out.columns if c.startswith("Unnamed")], errors="ignore")
    out["source"] = "screener.in"
    return out


# ----------------------------------------------------------------------------
# 2. TICKERTAPE
# ----------------------------------------------------------------------------
TT_QUERY = "https://api.tickertape.in/screener/query"
TT_FILTERS = "https://api.tickertape.in/screener/filters"

# handy ownership field ids (see tickertape_filter_catalog()):
#   forInstHldng    Foreign Institutional Holding %
#   forInstHldng3M  FII Holding Change - 3M
#   forInstHldng6M  FII Holding Change - 6M
#   domInstHldng / domInstHldng3M                    DII
#   instown / instown3                               Mutual funds
#   strown / strown3                                 Promoters
#   promShrPled, retailHolding
TT_PROJECT = [
    "forInstHldng",
    "forInstHldng3M",
    "forInstHldng6M",
    "domInstHldng",
    "domInstHldng3M",
    "instown",
    "instown3",
    "strown",
    "strown3",
    "promShrPled",
    "lastPrice",
    "mrktCapf",
    "pr1y",
    "pr3m",
    "pr1mnth",
    "apef",
    "pbr",
    "roe",
    "divYieldf",
    "subindustry",
]


def tickertape_filter_catalog() -> pd.DataFrame:
    """All available Tickertape screener fields (id -> display name)."""
    r = _session().get(TT_FILTERS, timeout=TIMEOUT)
    r.raise_for_status()
    rows: List[Dict[str, Any]] = []

    def rec(o: Any, group: Optional[str] = None) -> None:
        if isinstance(o, dict):
            if "label" in o and "display" in o:
                rows.append(
                    {
                        "field": o.get("label"),
                        "display": re.sub(r"\s+", " ", str(o.get("display"))).strip(),
                        "category": o.get("category") or group,
                        "premium": o.get("premium"),
                    }
                )
            for k, v in o.items():
                rec(v, k if isinstance(v, (dict, list)) else group)
        elif isinstance(o, list):
            for v in o:
                rec(v, group)

    rec(r.json().get("data"))
    df = pd.DataFrame(rows)
    return df.drop_duplicates("field") if not df.empty else df


def fetch_tickertape(
    min_fii_change_3m: float = 0.01,
    universe: str = "AllStocks",
    project: Iterable[str] = TT_PROJECT,
    page_size: int = 100,
    max_rows: int = 5000,
    pause: float = 0.4,
) -> pd.DataFrame:
    """Rebuild the 'FII buying stocks' collection via the public screener API.

    match syntax: {"<field>": {"g": <greater-than>, "l": <less-than>}}
    """
    s = _session()
    s.headers.update({"Content-Type": "application/json", "Origin": "https://www.tickertape.in"})
    rows: List[Dict[str, Any]] = []
    offset = 0
    total: Optional[int] = None

    while offset < max_rows:
        payload = {
            "match": {"forInstHldng3M": {"g": min_fii_change_3m, "l": 100}},
            "sortBy": "forInstHldng3M",
            "sortOrder": -1,
            "project": list(project),
            "offset": offset,
            "count": page_size,
            "sids": [],
            "universe": universe,
        }
        r = s.post(TT_QUERY, data=json.dumps(payload), timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data") or {}
        results = data.get("results") or []
        total = (data.get("stats") or {}).get("count", total)
        if not results:
            break
        for item in results:
            stock = item.get("stock", {}) or {}
            info = stock.get("info", {}) or {}
            rec = {
                "sid": item.get("sid"),
                "name": info.get("name"),
                "ticker": info.get("ticker"),
                "sector": info.get("sector"),
                "url": "https://www.tickertape.in" + (stock.get("slug") or ""),
            }
            rec.update(stock.get("advancedRatios", {}) or {})
            rows.append(rec)
        offset += page_size
        if total is not None and offset >= total:
            break
        time.sleep(pause)

    df = pd.DataFrame(rows)
    if not df.empty:
        df["source"] = "tickertape"
    return df


# ----------------------------------------------------------------------------
# 3. DHAN
# ----------------------------------------------------------------------------
DHAN_API = "https://ow-scanx-analytics.dhan.co/customscan/fetchdt"

DHAN_FIELDS = [
    "Isin", "DispSym", "Sym", "Seosym", "Exch", "Inst", "Seg", "Sid",
    "Ltp", "Pchange", "PPerchange", "Volume", "Mcap", "Pe", "Pb", "Ind_Pe",
    "Eps", "Roe", "ROCE", "DivYeild", "High1Yr", "Low1Yr",
    "PricePerchng1week", "PricePerchng1mon", "PricePerchng3mon",
    "PricePerchng1year", "PricePerchng3year", "PricePerchng5year",
    "DaySMA50CurrentCandle", "DaySMA200CurrentCandle", "DayRSI14CurrentCandle",
    "Revenue", "NetProfitMargin", "YoYLastQtrlyProfitGrowth",
    "Year1RevenueGrowth", "Year1CAGREPSGrowth", "FreeCashFlow",
    "FIIHLDChagPer",
]


def fetch_dhan(
    min_fii_change_pct: float = 3,
    page_size: int = 50,
    max_pages: int = 40,
    sort: str = "Mcap",
    pause: float = 0.4,
) -> pd.DataFrame:
    """Dhan 'FII Buying Stocks' scanner API (same params the web page sends)."""
    s = _session()
    s.headers.update(
        {
            "Content-Type": "application/json",
            "Origin": "https://dhan.co",
            "Referer": "https://dhan.co/stocks/market/fii-buying-stocks/",
        }
    )
    rows: List[Dict[str, Any]] = []
    pgno = 1
    while pgno <= max_pages:
        payload = {
            "data": {
                "sort": sort,
                "sorder": "desc",
                "count": page_size,
                "params": [
                    {"field": "FIIHLDChagPer", "op": "gte", "val": str(min_fii_change_pct)},
                    {"field": "Seg", "op": "", "val": "E"},
                    {"field": "OgInst", "op": "", "val": "ES"},
                ],
                "fields": DHAN_FIELDS,
                "pgno": pgno,
            }
        }
        r = s.post(DHAN_API, data=json.dumps(payload), timeout=TIMEOUT)
        r.raise_for_status()
        js = r.json()
        chunk = js.get("data") or []
        if not chunk:
            break
        rows.extend(chunk)
        if pgno >= int(js.get("tot_pg") or 1):
            break
        pgno += 1
        time.sleep(pause)

    df = pd.json_normalize(rows) if rows else pd.DataFrame()
    if not df.empty:
        df["source"] = "dhan"
    return df


# ----------------------------------------------------------------------------
# 4. EQUITYMASTER  (Cloudflare -> needs a real browser)
# ----------------------------------------------------------------------------
EM_URL = (
    "https://www.equitymaster.com/stock-screener/"
    "stocks-recently-bought-by-institutional-investors"
)


def _tables_from_html(html: str) -> List[pd.DataFrame]:
    try:
        return pd.read_html(io.StringIO(html))
    except (ValueError, IndexError):
        return []


def _pick_biggest(html: str) -> pd.DataFrame:
    tables = [t for t in _tables_from_html(html) if t.shape[0] > 3 and t.shape[1] >= 3]
    if not tables:
        return pd.DataFrame()
    df = max(tables, key=lambda t: t.shape[0] * t.shape[1]).copy()
    df["source"] = "equitymaster"
    return df


def fetch_equitymaster(use_browser: bool = True, headless: bool = True) -> pd.DataFrame:
    """Equitymaster screener. Tries plain HTTP first; falls back to Playwright.

    NOTE: Cloudflare blocks datacenter/cloud IPs (403 + endless JS challenge).
    From a normal home/office connection the plain request or the browser path works.
    """
    try:
        r = _session().get(
            EM_URL, timeout=TIMEOUT, headers={"Referer": "https://www.equitymaster.com/"}
        )
        if r.status_code == 200:
            df = _pick_biggest(r.text)
            if not df.empty:
                return df
        print(f"[equitymaster] plain HTTP failed (status {r.status_code})", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"[equitymaster] plain HTTP error: {exc}", file=sys.stderr)

    if not use_browser:
        return pd.DataFrame()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[equitymaster] pip install playwright && playwright install chromium", file=sys.stderr)
        return pd.DataFrame()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(user_agent=UA, viewport={"width": 1440, "height": 900})
        page.goto(EM_URL, wait_until="domcontentloaded", timeout=90_000)
        try:
            page.wait_for_selector("table tr td", timeout=60_000)  # waits out the CF challenge
        except Exception:  # noqa: BLE001
            print("[equitymaster] blocked by Cloudflare; retry with headless=False", file=sys.stderr)
        html = page.content()
        browser.close()

    return _pick_biggest(html)


# ----------------------------------------------------------------------------
# Normalisation + merge (scanner-friendly output)
# ----------------------------------------------------------------------------
def normalize(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per (source, stock) with a common schema your scanner can consume."""
    out: List[pd.DataFrame] = []

    d = dfs.get("screener")
    if d is not None and not d.empty:
        cols = {c.lower(): c for c in d.columns}

        def col(key: str):
            for k, orig in cols.items():
                if k.startswith(key):
                    return d[orig].map(_num)
            return None

        out.append(
            pd.DataFrame(
                {
                    "source": "screener.in",
                    "name": d[cols["name"]] if "name" in cols else None,
                    "symbol": None,
                    "price": col("cmp rs."),
                    "mcap_cr": col("mar cap rs.cr."),
                    "pe": col("p/e"),
                    "fii_hold_pct": col("fii hold %"),
                    "fii_chg_pct": col("chg in fii hold %"),
                }
            )
        )

    d = dfs.get("tickertape")
    if d is not None and not d.empty:
        out.append(
            pd.DataFrame(
                {
                    "source": "tickertape",
                    "name": d.get("name"),
                    "symbol": d.get("ticker"),
                    "price": d.get("lastPrice"),
                    "mcap_cr": d.get("mrktCapf"),
                    "pe": d.get("apef"),
                    "fii_hold_pct": d.get("forInstHldng"),
                    "fii_chg_pct": d.get("forInstHldng3M"),
                }
            )
        )

    d = dfs.get("dhan")
    if d is not None and not d.empty:
        out.append(
            pd.DataFrame(
                {
                    "source": "dhan",
                    "name": d.get("DispSym"),
                    "symbol": d.get("Sym"),
                    "price": d.get("Ltp"),
                    "mcap_cr": d.get("Mcap"),
                    "pe": d.get("Pe"),
                    "fii_hold_pct": None,
                    "fii_chg_pct": d.get("FIIHLDChagPer"),
                }
            )
        )

    d = dfs.get("equitymaster")
    if d is not None and not d.empty:
        first = d.columns[0]
        out.append(pd.DataFrame({"source": "equitymaster", "name": d[first], "symbol": None}))

    if not out:
        return pd.DataFrame()
    merged = pd.concat(out, ignore_index=True)
    merged["name_key"] = (
        merged["name"].astype(str).str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
    )
    return merged


FETCHERS = {
    "screener": lambda a: fetch_screener(a.screen_id, a.screen_slug),
    "tickertape": lambda a: fetch_tickertape(min_fii_change_3m=a.tt_min_change),
    "dhan": lambda a: fetch_dhan(min_fii_change_pct=a.dhan_min_change),
    "equitymaster": lambda a: fetch_equitymaster(use_browser=not a.no_browser),
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Download FII-buying stock data from 4 sources")
    ap.add_argument("--outdir", default="data")
    ap.add_argument("--only", nargs="*", choices=list(FETCHERS), default=list(FETCHERS))
    ap.add_argument("--screen-id", default="343087")
    ap.add_argument("--screen-slug", default="fii-buying")
    ap.add_argument("--tt-min-change", type=float, default=0.01, help="min FII holding change (3M) %%")
    ap.add_argument("--dhan-min-change", type=float, default=3, help="min FII holding change QoQ %%")
    ap.add_argument("--no-browser", action="store_true", help="skip Playwright fallback")
    ap.add_argument("--catalog", action="store_true", help="also dump Tickertape field catalog")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d")
    results: Dict[str, pd.DataFrame] = {}

    for name in args.only:
        print(f"[{name}] fetching...", flush=True)
        try:
            df = FETCHERS[name](args)
        except Exception as exc:  # noqa: BLE001
            print(f"[{name}] FAILED: {exc}", file=sys.stderr)
            continue
        results[name] = df
        if df.empty:
            print(f"[{name}] no rows")
            continue
        path = os.path.join(args.outdir, f"{name}_fii_{stamp}.csv")
        df.to_csv(path, index=False)
        print(f"[{name}] {len(df)} rows -> {path}")

    if args.catalog:
        cat = tickertape_filter_catalog()
        cat.to_csv(os.path.join(args.outdir, "tickertape_fields.csv"), index=False)
        print(f"[catalog] {len(cat)} fields -> tickertape_fields.csv")

    merged = normalize(results)
    if not merged.empty:
        path = os.path.join(args.outdir, f"fii_merged_{stamp}.csv")
        merged.to_csv(path, index=False)
        print(f"[merged] {len(merged)} rows -> {path}")


if __name__ == "__main__":
    main()
