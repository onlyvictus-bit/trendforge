#!/usr/bin/env python3
"""
Market Data Downloader for Stock Prediction Scanner
---------------------------------------------------
Pulls:
  1. CFTC Commitment of Traders (COT) — global commodity OI
  2. NSE FII/DII + Participant-wise OI (India F&O)
  3. BSE Participant-wise OI + FII/DII cash
  4. MSE Participant-wise OI (xlsx)
  5. MCX warehouse stock-position PDFs (metals)

Usage:
    pip install requests pandas openpyxl
    # Optional: pip install playwright && playwright install chromium
    python market_data_downloader.py
"""

import os
import re
import json
import time
import zipfile
import io
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

import requests

# ── CONFIG ─────────────────────────────────────────────────────
BASE = Path("market_data")
BASE.mkdir(exist_ok=True)

DAYS_BACK = 5          # How many trading days to fetch for daily reports
CFTC_YEAR = 2026     # CFTC report year
MAX_RETRIES = 3
RETRY_DELAY = 2

# Historical routes retained as explicit hints only. They must never be
# requested by this prototype. Production acquisition is owned by the typed
# TrendForge registry and the replacement source keys below.
NOT_IN_USE_ROUTES = {
    "bse_participant_oi_legacy": {
        "route": "https://api.bseindia.com/BseIndiaAPI/api/ParticipantWiseOI/w",
        "reason": "HTTP 200 HTML shell; no usable participant-OI records.",
        "replacement_source_keys": ["bse_participant_oi"],
    },
    "bse_fii_dii_legacy": {
        "route": "https://api.bseindia.com/BseIndiaAPI/api/FIIDII/w",
        "reason": "HTTP 200 HTML shell; no usable FII/DII records.",
        "replacement_source_keys": ["bse_fii_dii"],
    },
}

# Real browser fingerprint — mandatory for NSE/BSE
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ── UTILITIES ──────────────────────────────────────────────────
def log_ok(msg: str):
    print(f"  ✅ {msg}")

def log_warn(msg: str):
    print(f"  ⚠️  {msg}")

def log_fail(msg: str):
    print(f"  ❌ {msg}")

def trading_days_back(n: int) -> List[datetime]:
    """Return last n trading days (Mon-Fri)"""
    days = []
    d = datetime.now()
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    return days

def fetch(url: str, session: Optional[requests.Session] = None,
          headers: Optional[Dict] = None, timeout: int = 30,
          retries: int = MAX_RETRIES, **kwargs) -> requests.Response:
    """Robust fetch with retries and exponential backoff."""
    s = session or requests
    hdrs = {**HEADERS, **(headers or {})}
    for attempt in range(1, retries + 1):
        try:
            r = s.get(url, headers=hdrs, timeout=timeout, **kwargs)
            if r.status_code == 403 and attempt < retries:
                log_warn(f"403 on attempt {attempt}, backing off...")
                time.sleep(RETRY_DELAY * attempt)
                continue
            return r
        except Exception as e:
            if attempt == retries:
                raise
            log_warn(f"Error ({e}), retrying...")
            time.sleep(RETRY_DELAY * attempt)
    return r  # type: ignore

# ── 1. CFTC ───────────────────────────────────────────────────
def download_cftc(year: int = CFTC_YEAR):
    """
    CFTC publishes yearly ZIP archives of COT data.
    All files update weekly (Tuesday EOD).
    """
    out_dir = BASE / "cftc" / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "fut_disagg_txt": "Disaggregated Futures Only",
        "com_disagg_txt": "Disaggregated Futures+Options",
        "fut_fin_txt": "Traders in Financial Futures (TFF) Futures Only",
        "com_fin_txt": "TFF Futures+Options Combined",
        "deacot2026": "Legacy COT Futures Only (text)",
        "dea_fut_xls": "Legacy COT Futures Only (Excel)",
        "dea_com_xls": "Legacy COT Futures+Options (Excel)",
        "dea_cit_txt": "Commodity Index Trader Supplement",
    }

    print("\n" + "=" * 60)
    print(f"[1/5] CFTC Commitment of Traders — {year}")
    print("=" * 60)

    for stem, desc in files.items():
        # deacot2026 has no _year suffix
        if stem == "deacot2026":
            url = f"https://www.cftc.gov/files/dea/history/{stem}.zip"
            fname = out_dir / f"{stem}.zip"
        else:
            url = f"https://www.cftc.gov/files/dea/history/{stem}_{year}.zip"
            fname = out_dir / f"{stem}_{year}.zip"

        if fname.exists():
            log_ok(f"{fname.name} already exists")
            continue

        try:
            r = fetch(url, timeout=60)
            r.raise_for_status()
            fname.write_bytes(r.content)
            log_ok(f"{fname.name} ({len(r.content):,} bytes) — {desc}")
            time.sleep(0.5)
        except Exception as e:
            log_fail(f"{stem}: {e}")

    # Optional: auto-extract
    for zf in out_dir.glob("*.zip"):
        try:
            with zipfile.ZipFile(zf, 'r') as z:
                z.extractall(out_dir / "extracted")
        except Exception as e:
            log_warn(f"Could not extract {zf.name}: {e}")

# ── 2. NSE ────────────────────────────────────────────────────
def _nse_session() -> requests.Session:
    """NSE requires cookies from homepage + Referer header."""
    s = requests.Session()
    s.headers.update(HEADERS)
    s.headers.update({
        "Referer": "https://www.nseindia.com/",
        "Origin": "https://www.nseindia.com",
    })
    try:
        # Prime cookies
        r = s.get("https://www.nseindia.com", timeout=20)
        log_ok(f"NSE session primed (cookies={len(s.cookies)})") if r.status_code == 200 else log_warn("NSE homepage returned non-200")
        time.sleep(1)
    except Exception as e:
        log_warn(f"NSE session prime failed: {e}")
    return s

def download_nse_fii_dii():
    """NSE daily FII/DII cash activity JSON."""
    out_dir = BASE / "nse" / "fii_dii"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 60)
    print("[2a] NSE FII/DII Activity (cash segment)")
    print("=" * 60)

    s = _nse_session()
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    try:
        r = s.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        fname = out_dir / f"fiidii_{datetime.now():%Y%m%d}.json"
        fname.write_text(json.dumps(data, indent=2))
        rows = len(data.get("data", []))
        log_ok(f"{rows} rows → {fname}")
    except Exception as e:
        log_fail(f"NSE FII/DII API failed: {e}")
        log_warn("If you see 403, your IP is blocked. Try from a residential connection or use the browser fallback.")

def download_nse_participant_oi(days_back: int = DAYS_BACK):
    """NSE F&O Participant-wise Open Interest CSV archives."""
    out_dir = BASE / "nse" / "participant_oi"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 60)
    print("[2b] NSE Participant-wise OI (F&O)")
    print("=" * 60)

    for d in trading_days_back(days_back):
        fname = f"fao_participant_oi_{d:%Y%m%d}.csv"
        url = f"https://archives.nseindia.com/content/nsccl/{fname}"
        fpath = out_dir / fname
        if fpath.exists():
            log_ok(f"{fname} already exists")
            continue
        try:
            r = fetch(url, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000:
                fpath.write_bytes(r.content)
                log_ok(f"{fname} ({len(r.content):,} bytes)")
            else:
                log_warn(f"{fname} not available yet (HTTP {r.status_code})")
            time.sleep(0.5)
        except Exception as e:
            log_fail(f"{fname}: {e}")

def download_nse_fii_derivatives(days_back: int = DAYS_BACK):
    """NSE FII Derivatives Statistics CSV archives."""
    out_dir = BASE / "nse" / "fii_derivatives"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 60)
    print("[2c] NSE FII Derivatives Statistics")
    print("=" * 60)

    for d in trading_days_back(days_back):
        fname = f"fao_participant_fii_{d:%Y%m%d}.csv"
        url = f"https://archives.nseindia.com/content/nsccl/{fname}"
        fpath = out_dir / fname
        if fpath.exists():
            log_ok(f"{fname} already exists")
            continue
        try:
            r = fetch(url, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000:
                fpath.write_bytes(r.content)
                log_ok(f"{fname} ({len(r.content):,} bytes)")
            else:
                log_warn(f"{fname} not available (HTTP {r.status_code})")
            time.sleep(0.5)
        except Exception as e:
            log_fail(f"{fname}: {e}")

# ── 3. BSE ────────────────────────────────────────────────────
def _bse_session() -> requests.Session:
    """BSE api.bseindia.com needs cookies + Referer from www.bseindia.com."""
    s = requests.Session()
    s.headers.update(HEADERS)
    s.headers.update({
        "Referer": "https://www.bseindia.com/markets/Derivatives/DeriReports/DeriMarketDisclosures",
        "Origin": "https://www.bseindia.com",
    })
    try:
        r = s.get("https://www.bseindia.com", timeout=20)
        log_ok(f"BSE session primed (cookies={len(s.cookies)})") if r.status_code == 200 else log_warn("BSE homepage non-200")
        time.sleep(1)
    except Exception as e:
        log_warn(f"BSE session prime failed: {e}")
    return s

def download_bse_participant_oi(days_back: int = DAYS_BACK):
    """NOT_IN_USE compatibility stub; performs no network or file writes."""
    route = NOT_IN_USE_ROUTES["bse_participant_oi_legacy"]
    log_warn(
        "NOT_IN_USE: legacy BSE ParticipantWiseOI route is disabled; "
        f"use {route['replacement_source_keys'][0]} through TrendForge Refresh"
    )
    return route

def download_bse_fii_dii(days_back: int = DAYS_BACK):
    """NOT_IN_USE compatibility stub; performs no network or file writes."""
    route = NOT_IN_USE_ROUTES["bse_fii_dii_legacy"]
    log_warn(
        "NOT_IN_USE: legacy BSE FIIDII route is disabled; "
        f"use {route['replacement_source_keys'][0]} through TrendForge Refresh"
    )
    return route

# ── 4. MSE ────────────────────────────────────────────────────
def download_mse_participant_oi(days_back: int = DAYS_BACK):
    """MSE daily Participant-wise OI as .xlsx."""
    out_dir = BASE / "mse" / "participant_oi"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 60)
    print("[4/5] MSE Participant-wise OI (Excel)")
    print("=" * 60)

    for d in trading_days_back(days_back):
        url = (
            f"https://www.msei.in/SX-Content/daily/Equity-Derivatives/"
            f"{d:%Y}/{d:%B}/{d.day:02d}/"
            f"Participant-wise-Open-Interest---{d:%d%m%Y}.xlsx"
        )
        fname = out_dir / f"participant_oi_{d:%Y%m%d}.xlsx"
        if fname.exists():
            log_ok(f"{fname.name} already exists")
            continue
        try:
            r = fetch(url, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000:
                fname.write_bytes(r.content)
                log_ok(f"{d:%Y-%m-%d} ({len(r.content):,} bytes)")
            else:
                log_warn(f"{d:%Y-%m-%d} HTTP {r.status_code} (may be holiday)")
            time.sleep(0.5)
        except Exception as e:
            log_fail(f"{d:%Y-%m-%d}: {e}")

# ── 5. MCX ────────────────────────────────────────────────────
def download_mcx_stock_pdfs(max_pdfs: int = 10):
    """MCX metal stock position PDFs — scrape listing page for links."""
    out_dir = BASE / "mcx" / "stock_position_pdfs"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 60)
    print("[5/5] MCX Warehouse Stock Position (PDFs)")
    print("=" * 60)

    listing_url = "https://www.mcxccl.com/warehousing-logistics/stock-position-in-lots"
    try:
        r = fetch(listing_url, timeout=30)
        r.raise_for_status()
        pdf_links = re.findall(
            r'href="(/docs/mcxccllibraries/warehousing-operations/stock-position-in-lots/[^"]+\.pdf)"',
            r.text, re.I
        )
        pdf_links = list(dict.fromkeys(pdf_links))  # dedupe
        log_ok(f"Found {len(pdf_links)} PDF links on listing page")

        for i, path in enumerate(pdf_links[:max_pdfs]):
            url = f"https://www.mcxccl.com{path}"
            m = re.search(r'as-on-(?:date-)?(\d{2}-\d{2}-\d{4})', path)
            date_tag = m.group(1) if m else f"file_{i}"
            fname = out_dir / f"mcx_stock_{date_tag}.pdf"
            if fname.exists():
                log_ok(f"{fname.name} already exists")
                continue
            try:
                pr = fetch(url, timeout=60)
                if pr.status_code == 200 and len(pr.content) > 5000:
                    fname.write_bytes(pr.content)
                    log_ok(f"{fname.name} ({len(pr.content)//1024} KB)")
                else:
                    log_warn(f"{date_tag} HTTP {pr.status_code}")
                time.sleep(0.5)
            except Exception as e:
                log_fail(f"{date_tag}: {e}")
    except Exception as e:
        log_fail(f"MCX listing page: {e}")

# ── BROWSER FALLBACK (Playwright) ─────────────────────────────
def browser_fallback_nse_fii_dii():
    """
    If requests.get() returns 403, use this to drive a real browser.
    Requires: pip install playwright && playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log_warn("Playwright not installed. Skipping browser fallback.")
        return

    out_dir = BASE / "nse" / "fii_dii"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n[Browser Fallback] NSE FII/DII via Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.goto("https://www.nseindia.com/reports/fii-dii", wait_until="networkidle", timeout=30000)

        # Extract table data via page.evaluate
        data = page.evaluate("""() => {
            const rows = document.querySelectorAll('table tr');
            return Array.from(rows).map(r => Array.from(r.querySelectorAll('td,th')).map(c => c.innerText.trim()));
        }""")
        fname = out_dir / f"fiidii_{datetime.now():%Y%m%d}_browser.json"
        fname.write_text(json.dumps(data, indent=2))
        log_ok(f"Browser extracted {len(data)} rows → {fname}")
        browser.close()

# ── MAIN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("  MARKET DATA DOWNLOADER FOR STOCK PREDICTION SCANNER")
    print(f"  Run time: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    # 1. CFTC — always works
    download_cftc()

    # 2. NSE — may 403 on datacenter IPs
    download_nse_fii_dii()
    download_nse_participant_oi()
    download_nse_fii_derivatives()

    # 3. BSE legacy calls are deliberately NOT_IN_USE. Keep the compatibility
    # stubs above as migration hints only. Production replacements:
    #   bse_participant_oi -> DeriMarketDisclosureData_ng/w
    #   bse_fii_dii       -> CategoryTurnover/w

    # 4. MSE — direct XLSX
    download_mse_participant_oi()

    # 5. MCX — PDF scrape
    download_mcx_stock_pdfs(max_pdfs=10)

    # Optional: browser fallback if APIs failed
    # browser_fallback_nse_fii_dii()

    # Summary
    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)
    print("\nDirectory structure:")
    for root, dirs, files in os.walk(BASE):
        level = root.replace(str(BASE), "").count(os.sep)
        indent = "  " * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = "  " * (level + 1)
        for f in sorted(files)[:8]:
            sz = os.path.getsize(os.path.join(root, f))
            print(f"{subindent}{f}  ({sz//1024} KB)")
        if len(files) > 8:
            print(f"{subindent}... +{len(files)-8} more")
# Historical pack note: run market_data_pipeline.py only for isolated audit
# smoke tests. Production collection must use TrendForge Refresh.

