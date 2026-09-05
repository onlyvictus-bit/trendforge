"""Phase-3 multi-step fetch helpers for sources that need more than one HTTP GET.

Used by source_resolver.resolve_and_fetch_source special cases.
Research-only; no broker credentials.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import requests  # type: ignore

try:  # curl-cffi is required for MCX's Akamai TLS/browser fingerprint.
    from curl_cffi import requests as _curl_requests  # type: ignore
except ImportError:  # pragma: no cover - dependency guard for partial installs
    _curl_requests = None

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
TIMEOUT = 25


@dataclass(frozen=True)
class MultiStepFetchResult:
    ok: bool
    url: str
    status_code: int
    content: bytes
    media_type: str
    error: str | None = None


class _RbiPressReleaseLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = dict(attrs).get("href")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            text = re.sub(r"\s+", " ", "".join(self._text)).strip()
            self.links.append((text, self._href))
            self._href = None
            self._text = []


def _session(headers: dict[str, str] | None = None) -> requests.Session:
    s = requests.Session()
    base = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        base.update(headers)
    s.headers.update(base)
    return s


def fetch_mcx_bhavcopy_page(*, session: Any | None = None) -> MultiStepFetchResult:
    """Fetch the official MCX EOD page with a browser TLS fingerprint.

    MCX's Akamai edge intermittently blocks ordinary requests with HTTP 403.
    A 200 Sitefinity status page is also not data, so this helper accepts only
    a page containing the populated embedded bhavcopy payload used by the
    existing fail-closed parser.
    """

    urls = (
        "https://www.mcxindia.com/market-data/bhavcopy",
        "https://www.mcxindia.com/market-data/BhavCopy",
        "https://www.mcxindia.com/market-data/bhav-copy",
    )
    if session is None:
        if _curl_requests is None:
            return MultiStepFetchResult(
                False,
                urls[0],
                0,
                b"",
                "text/html",
                "curl-cffi is unavailable for the MCX browser-TLS request",
            )
        session = _curl_requests.Session(impersonate="chrome")

    errors: list[str] = []
    last_status = 0
    last_url = urls[0]
    headers = {
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.mcxindia.com/",
        "Upgrade-Insecure-Requests": "1",
    }
    for url in urls:
        try:
            response = session.get(
                url,
                headers=headers,
                timeout=max(TIMEOUT, 60),
                allow_redirects=True,
            )
        except Exception as exc:  # noqa: BLE001 - transport boundary
            errors.append(f"{url}: {type(exc).__name__}")
            continue
        last_status = int(response.status_code)
        last_url = str(response.url)
        body = bytes(response.content or b"")
        redirected_to_status = "/sitefinity/status" in last_url.casefold()
        has_embedded_payload = bool(
            re.search(
                rb'id=["\']bhavcopy-data["\'][^>]*>\s*\[\s*\{',
                body,
                re.IGNORECASE | re.DOTALL,
            )
        )
        if last_status == 200 and not redirected_to_status and has_embedded_payload:
            return MultiStepFetchResult(
                True,
                last_url,
                last_status,
                body,
                response.headers.get("content-type", "text/html"),
                None,
            )
        reason = "Sitefinity status page" if redirected_to_status else "embedded bhavcopy data missing"
        errors.append(f"{url}: HTTP {last_status} {reason}")

    return MultiStepFetchResult(
        False,
        last_url,
        last_status,
        b"",
        "text/html",
        "; ".join(errors)[-1200:] or "MCX bhavcopy fetch failed",
    )


def fetch_rbi_usdinr_form_post(
    *, days_back: int = 14
) -> MultiStepFetchResult:
    """GET RBI archive form, then POST date range for USD/INR table HTML."""
    url = "https://www.rbi.org.in/scripts/ReferenceRateArchive.aspx"
    end = datetime.now()
    start = end - timedelta(days=days_back)
    start_s = start.strftime("%d-%b-%Y")
    end_s = end.strftime("%d-%b-%Y")
    s = _session({"Accept": "text/html,application/xhtml+xml"})
    try:
        r0 = s.get(url, timeout=TIMEOUT)
        if r0.status_code >= 400:
            return MultiStepFetchResult(
                False, url, r0.status_code, r0.content, r0.headers.get("content-type", "text/html"),
                f"RBI form GET failed HTTP {r0.status_code}",
            )
        html = r0.text

        def _field(name: str) -> str:
            m = re.search(
                rf'name="{re.escape(name)}"[^>]*value="([^"]*)"',
                html,
                flags=re.I,
            )
            if m:
                return m.group(1)
            m = re.search(
                rf'name="{re.escape(name)}"[^>]*value=\'([^\']*)\'',
                html,
                flags=re.I,
            )
            return m.group(1) if m else ""

        payload = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": _field("__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": _field("__VIEWSTATEGENERATOR"),
            "__EVENTVALIDATION": _field("__EVENTVALIDATION"),
            "txtFromDate": start_s,
            "txtToDate": end_s,
            "chkUSD": "on",
            "btnSubmit": "Submit",
        }
        if not payload["__VIEWSTATE"]:
            return MultiStepFetchResult(
                False, url, r0.status_code, r0.content, "text/html",
                "RBI form VIEWSTATE missing",
            )
        r1 = s.post(url, data=payload, timeout=TIMEOUT)
        return MultiStepFetchResult(
            r1.status_code < 400 and b"USD" in r1.content,
            str(r1.url),
            r1.status_code,
            r1.content,
            r1.headers.get("content-type", "text/html"),
            None if r1.status_code < 400 else f"RBI POST HTTP {r1.status_code}",
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "text/html", str(exc))


def fetch_rbi_tbill_yield() -> MultiStepFetchResult:
    """Discover and fetch RBI's newest full Treasury-bill auction result."""
    index_url = "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx"
    session = _session({"Accept": "text/html,application/xhtml+xml"})
    try:
        index_response = session.get(index_url, timeout=TIMEOUT)
        if index_response.status_code != 200:
            return MultiStepFetchResult(
                False,
                index_url,
                index_response.status_code,
                b"",
                "text/html",
                f"RBI press-release index HTTP {index_response.status_code}",
            )
        parser = _RbiPressReleaseLinkParser()
        parser.feed(index_response.text)
        detail_url = next(
            (
                urljoin(index_url, href)
                for text, href in parser.links
                if text.casefold() == "treasury bills: full auction result"
                and "BS_PressReleaseDisplay.aspx?prid=" in href
            ),
            None,
        )
        if detail_url is None:
            return MultiStepFetchResult(
                False,
                index_url,
                index_response.status_code,
                b"",
                "text/html",
                "RBI index has no exact Treasury Bills full-auction-result link",
            )
        detail = session.get(
            detail_url,
            headers={"Referer": index_url},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, index_url, 0, b"", "text/html", str(exc))
    body = detail.content
    ok = (
        detail.status_code == 200
        and 5_000 < len(body) < 5_000_000
        and b"Treasury Bills: Full Auction Result" in body
        and b"91-Day" in body
        and b"182-Day" in body
        and b"364-Day" in body
        and b"Weighted Average Price" in body
    )
    return MultiStepFetchResult(
        ok,
        detail.url,
        detail.status_code,
        body if ok else b"",
        detail.headers.get("content-type", "text/html"),
        None if ok else "RBI full-auction detail failed schema/size validation",
    )


def fetch_nse_index_option_chain_v3(
    symbol: str = "NIFTY",
) -> MultiStepFetchResult:
    """Prime NSE cookies, resolve nearest expiry, fetch option-chain-v3 Indices."""
    home = "https://www.nseindia.com"
    s = _session(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    try:
        s.get(home, timeout=TIMEOUT)
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{home}/option-chain",
            "X-Requested-With": "XMLHttpRequest",
        }
        info_url = f"{home}/api/option-chain-contract-info?symbol={urllib.parse.quote(symbol)}"
        r_info = s.get(info_url, headers=headers, timeout=TIMEOUT)
        if r_info.status_code >= 400 or "json" not in (r_info.headers.get("content-type") or ""):
            # re-prime once
            s.get(home, timeout=TIMEOUT)
            r_info = s.get(info_url, headers=headers, timeout=TIMEOUT)
        if r_info.status_code >= 400:
            return MultiStepFetchResult(
                False, info_url, r_info.status_code, r_info.content,
                r_info.headers.get("content-type", "application/json"),
                f"contract-info HTTP {r_info.status_code}",
            )
        try:
            info = r_info.json()
        except ValueError:
            return MultiStepFetchResult(
                False, info_url, r_info.status_code, r_info.content, "application/json",
                "contract-info not JSON",
            )
        expiries = info.get("expiryDates") or []
        if not expiries:
            return MultiStepFetchResult(
                False, info_url, r_info.status_code, r_info.content, "application/json",
                "no expiryDates in contract-info",
            )
        expiry = expiries[0]
        chain_url = (
            f"{home}/api/option-chain-v3?type=Indices&symbol={urllib.parse.quote(symbol)}"
            f"&expiry={urllib.parse.quote(str(expiry))}"
        )
        r_chain = s.get(chain_url, headers=headers, timeout=TIMEOUT)
        if r_chain.status_code >= 400 or "json" not in (r_chain.headers.get("content-type") or ""):
            s.get(home, timeout=TIMEOUT)
            r_chain = s.get(chain_url, headers=headers, timeout=TIMEOUT)
        ok = r_chain.status_code < 400 and b"{" in r_chain.content[:20]
        return MultiStepFetchResult(
            ok,
            chain_url,
            r_chain.status_code,
            r_chain.content,
            r_chain.headers.get("content-type", "application/json"),
            None if ok else f"option-chain-v3 HTTP {r_chain.status_code}",
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(
            False,
            f"https://www.nseindia.com/api/option-chain-v3?symbol={symbol}",
            0,
            b"",
            "application/json",
            str(exc),
        )


def fetch_dgcis_imports(
    *,
    year: str | None = None,
    hs_level: str = "2",
    report_unit: str = "2",
) -> MultiStepFetchResult:
    """CSRF GET+POST against DGCIS TradeStat commodity import form (current Laravel UI)."""
    candidates = [
        "https://tradestat.commerce.gov.in/eidb/commodity_wise_import",
        "https://tradestat.commerce.gov.in/eidb/commodity_wise_all_countries_import",
    ]
    last_err = "no candidate"
    # Fresh session + token each attempt — site flakes under concurrent registry runs.
    for attempt in range(1, 4):
        s = _session({"Accept": "text/html,application/xhtml+xml"})
        for page_url in candidates:
            try:
                r0 = s.get(page_url, timeout=TIMEOUT)
                if r0.status_code >= 400:
                    last_err = f"GET {page_url} HTTP {r0.status_code}"
                    continue
                html = r0.text
                tok_m = re.search(r'name="_token"[^>]*value="([^"]+)"', html)
                if not tok_m:
                    last_err = f"GET {page_url} missing CSRF token"
                    continue
                # Form year options are fiscal starts (e.g. value "2025" = 2025-26).
                year_opts = re.findall(
                    r'<select[^>]*name="Eidb_YearCwi"[^>]*>(.*?)</select>',
                    html,
                    flags=re.I | re.S,
                )
                available_years: list[str] = []
                if year_opts:
                    available_years = [
                        o
                        for o in re.findall(
                            r'<option[^>]*value="([^"]*)"', year_opts[0], flags=re.I
                        )
                        if o.isdigit()
                    ]
                if year and str(year) in available_years:
                    form_year = str(year)
                elif available_years:
                    form_year = sorted(available_years, reverse=True)[0]
                else:
                    form_year = str(date.today().year - 1)
                data: dict[str, str] = {
                    "_token": tok_m.group(1),
                    "commodityType": "all",
                    "Eidb_YearCwi": form_year,
                    "Eidb_ComLevelCwi": hs_level if hs_level not in {"0", ""} else "2",
                    "Eidb_hscodeCwi": "",
                    "hscode_value": "",
                    "description_value": "",
                    "Eidb_ReportCwi": report_unit,
                }
                if "all_countries" in page_url:
                    data = {
                        "_token": tok_m.group(1),
                        "EidbYear_cmaci": form_year,
                        "EidbReport_cmaci": report_unit,
                    }
                    for sel in re.finditer(
                        r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>',
                        html,
                        flags=re.I | re.S,
                    ):
                        name = sel.group(1)
                        opts = [
                            o
                            for o in re.findall(
                                r'<option[^>]*value="([^"]*)"', sel.group(2), flags=re.I
                            )
                            if o
                        ]
                        if opts and name not in data:
                            data[name] = opts[0]
                        if name in {"EidbYear_cmaci", "Eidb_YearCwi"} and available_years:
                            data[name] = form_year
                r1 = s.post(
                    page_url,
                    data=data,
                    timeout=90,
                    headers={
                        "Referer": page_url,
                        "Origin": "https://tradestat.commerce.gov.in",
                    },
                )
                content = r1.content
                ok = (
                    r1.status_code < 400
                    and len(content) > 1000
                    and (
                        b"<table" in content.lower()
                        or b"HSCode" in content
                        or b"Commodity" in content
                    )
                )
                if ok:
                    return MultiStepFetchResult(
                        True,
                        str(r1.url),
                        r1.status_code,
                        content,
                        r1.headers.get("content-type", "text/html"),
                        None,
                    )
                last_err = (
                    f"POST {page_url} empty/no table len={len(content)} attempt={attempt}"
                )
            except requests.RequestException as exc:
                last_err = f"{exc} attempt={attempt}"
    return MultiStepFetchResult(
        False, candidates[0], 0, b"", "text/html", last_err
    )


def fetch_eia_natgas_storage() -> MultiStepFetchResult:
    """Weekly US working gas storage. ir.eia.gov CSV is often 403; use dnav XLS."""
    s = _session(
        {
            "Accept": "text/csv,application/vnd.ms-excel,*/*",
            "Referer": "https://www.eia.gov/naturalgas/weekly/",
        }
    )
    candidates = [
        "https://ir.eia.gov/ngs/wngsr.csv",
        "https://www.eia.gov/dnav/ng/xls/NG_STOR_WKLY_S1_W.xls",
        "https://www.eia.gov/dnav/ng/xls/ng_stor_wkly_s1_w.xls",
    ]
    last_err = "no candidate"
    last_url = candidates[0]
    for url in candidates:
        last_url = url
        try:
            r = s.get(url, timeout=TIMEOUT)
            if r.status_code >= 400:
                last_err = f"HTTP {r.status_code} {url}"
                continue
            body = r.content
            if body[:1] in (b"<", b"\n") and b"Access Denied" in body[:500]:
                last_err = f"access denied {url}"
                continue
            # CSV path
            if url.endswith(".csv") and (b"Region" in body[:2000] or b"East" in body[:4000]):
                return MultiStepFetchResult(
                    True,
                    url,
                    r.status_code,
                    body,
                    r.headers.get("content-type", "text/csv"),
                    None,
                )
            # XLS OLE signature
            if body[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" or url.endswith(".xls"):
                if len(body) > 5000:
                    return MultiStepFetchResult(
                        True,
                        url,
                        r.status_code,
                        body,
                        r.headers.get("content-type", "application/vnd.ms-excel"),
                        None,
                    )
            last_err = f"unexpected body {url} len={len(body)}"
        except requests.RequestException as exc:
            last_err = str(exc)
    return MultiStepFetchResult(False, last_url, 0, b"", "application/octet-stream", last_err)


def fetch_eia_steo_opec_supply(*, months_back: int = 8) -> MultiStepFetchResult:
    """Discover/download the latest official STEO workbook without an API key."""
    index_url = "https://www.eia.gov/outlooks/steo/outlook.php"
    session = _session({"Accept": "text/html,application/xhtml+xml,*/*"})
    candidates: list[str] = []
    try:
        index = session.get(index_url, timeout=TIMEOUT)
        if index.status_code < 400:
            for href in re.findall(
                r'href=["\']([^"\']+_base\.xlsx)["\']', index.text, re.I
            ):
                candidates.append(urllib.parse.urljoin(index.url, href))
    except requests.RequestException:
        pass
    current = date.today().replace(day=1)
    for offset in range(max(1, months_back)):
        month_index = current.year * 12 + current.month - 1 - offset
        year, zero_month = divmod(month_index, 12)
        month = zero_month + 1
        token = date(year, month, 1).strftime("%b%y").casefold()
        candidates.append(f"https://www.eia.gov/outlooks/steo/archives/{token}_base.xlsx")
    last_url = index_url
    last_status = 0
    last_error = "no STEO workbook candidate"
    for url in dict.fromkeys(candidates):
        last_url = url
        try:
            response = session.get(url, timeout=60)
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
        last_status = response.status_code
        body = response.content
        if (
            response.status_code == 200
            and body.startswith(b"PK")
            and 100_000 < len(body) < 15_000_000
        ):
            return MultiStepFetchResult(
                True,
                response.url,
                response.status_code,
                body,
                response.headers.get(
                    "content-type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                None,
            )
        last_error = f"HTTP/size/signature validation failed at {url}"
    return MultiStepFetchResult(
        False,
        last_url,
        last_status,
        b"",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        last_error,
    )


def fetch_opec_production_adjustment() -> MultiStepFetchResult:
    """Fetch the latest verified free OPEC production-adjustment release."""
    # OPEC's list and sitemap are Cloudflare-blocked from this collector while
    # individual releases remain public. Keep bounded newest-first candidates.
    candidates = (
        "https://www.opec.org/pr-detail/604-16-june-2026.html",
        "https://www.opec.org/pr-detail/1779602-3-may-2026.html",
        "https://www.opec.org/pr-detail/597-5-april-2026.html",
        "https://www.opec.org/pr-detail/1619593-1-march-2026.html",
    )
    session = _session({"Accept": "text/html,application/xhtml+xml"})
    last_status = 0
    last_error = "no OPEC adjustment release candidate"
    for url in candidates:
        try:
            response = session.get(url, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
        last_status = response.status_code
        body = response.content
        if (
            response.status_code == 200
            and len(body) < 5_000_000
            and re.search(br"production\s+adjustment\s+of", body, re.I)
            and re.search(br"implemented\s+in", body, re.I)
        ):
            return MultiStepFetchResult(
                True,
                response.url,
                response.status_code,
                body,
                response.headers.get("content-type", "text/html"),
                None,
            )
        last_error = f"HTTP/schema validation failed at {url}"
    return MultiStepFetchResult(
        False, candidates[0], last_status, b"", "text/html", last_error
    )


def fetch_yahoo_symbols(symbols: list[str], *, range_: str = "1mo") -> MultiStepFetchResult:
    """Fetch multiple Yahoo chart symbols; return combined JSON payload."""
    s = _session({"Accept": "application/json"})
    combined: list[dict[str, Any]] = []
    last_url = ""
    last_status = 0
    for sym in symbols:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
            f"?range={range_}&interval=1d"
        )
        last_url = url
        try:
            r = s.get(url, timeout=TIMEOUT)
            last_status = r.status_code
            if r.status_code >= 400:
                continue
            payload = r.json()
            result = (payload.get("chart") or {}).get("result") or []
            if not result:
                continue
            res0 = result[0]
            meta = res0.get("meta") or {}
            q = (res0.get("indicators") or {}).get("quote") or [{}]
            quote = q[0] if q else {}
            ts = res0.get("timestamp") or []
            for i, t in enumerate(ts):
                close = (quote.get("close") or [None])
                c = close[i] if i < len(close) else None
                if c is None:
                    continue
                combined.append(
                    {
                        "symbol": str(meta.get("symbol") or sym).upper(),
                        "timestamp": t,
                        "open": (quote.get("open") or [None])[i] if i < len(quote.get("open") or []) else None,
                        "high": (quote.get("high") or [None])[i] if i < len(quote.get("high") or []) else None,
                        "low": (quote.get("low") or [None])[i] if i < len(quote.get("low") or []) else None,
                        "close": c,
                        "volume": (quote.get("volume") or [None])[i] if i < len(quote.get("volume") or []) else None,
                    }
                )
        except Exception:
            continue
    if not combined:
        return MultiStepFetchResult(False, last_url, last_status, b"", "application/json", "yahoo empty")
    body = json.dumps({"records": combined, "rows": combined}).encode("utf-8")
    return MultiStepFetchResult(True, last_url, 200, body, "application/json", None)


def fetch_amfi_monthly_aum(*, months_back: int = 8) -> MultiStepFetchResult:
    """Walk backward to the latest published official AMFI monthly AUM workbook."""
    session = _session({"Accept": "application/vnd.ms-excel,*/*"})
    current = date.today().replace(day=1)
    last_error = "no AMFI monthly workbook candidate"
    last_url = "https://portal.amfiindia.com/spages/"
    for offset in range(max(1, months_back)):
        month_index = current.year * 12 + current.month - 1 - offset
        year, zero_month = divmod(month_index, 12)
        month = zero_month + 1
        token = date(year, month, 1).strftime("%b%Y").casefold()
        url = f"https://portal.amfiindia.com/spages/am{token}repo.xls"
        last_url = url
        try:
            response = session.get(url, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
        body = response.content
        if (
            response.status_code < 400
            and body.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
            and len(body) > 10_000
        ):
            return MultiStepFetchResult(
                True,
                url,
                response.status_code,
                body,
                response.headers.get("content-type", "application/vnd.ms-excel"),
                None,
            )
        last_error = f"HTTP {response.status_code} or invalid OLE workbook at {url}"
    return MultiStepFetchResult(
        False, last_url, 0, b"", "application/vnd.ms-excel", last_error
    )


def fetch_tradingeconomics_bdi() -> MultiStepFetchResult:
    """Fetch the approved third-party Baltic Dry Index page with schema guards."""
    url = "https://tradingeconomics.com/commodity/baltic"
    session = _session({"Accept": "text/html,application/xhtml+xml"})
    try:
        response = session.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "text/html", str(exc))
    body = response.content
    ok = (
        response.status_code < 400
        and len(body) < 5_000_000
        and b"Baltic Dry" in body
        and b"<table" in body.lower()
    )
    return MultiStepFetchResult(
        ok,
        url,
        response.status_code,
        body if ok else b"",
        response.headers.get("content-type", "text/html"),
        None if ok else f"TradingEconomics BDI unusable HTTP {response.status_code}",
    )


def fetch_google_trends_india_rss() -> MultiStepFetchResult:
    """Fetch Google's official current India trends RSS feed."""
    url = "https://trends.google.com/trending/rss?geo=IN"
    session = _session(
        {"Accept": "application/rss+xml,application/xml,text/xml,*/*"}
    )
    try:
        response = session.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "application/xml", str(exc))
    body = response.content
    ok = (
        response.status_code < 400
        and len(body) < 1_000_000
        and b"<rss" in body[:500].lower()
        and b"<item>" in body
    )
    return MultiStepFetchResult(
        ok,
        url,
        response.status_code,
        body if ok else b"",
        response.headers.get("content-type", "application/xml"),
        None if ok else f"Google Trends RSS unusable HTTP {response.status_code}",
    )


def fetch_google_news_rss() -> MultiStepFetchResult:
    """Fetch the Pack-3 bounded India-equity Google News RSS query bundle."""
    base_url = "https://news.google.com/rss/search"
    queries = (
        "Indian stock market NSE BSE",
        "NSE BSE stock order win upgrade",
        "Indian stocks rating downgrade pledge default",
        "India corporate news merger acquisition QIP buyback",
        "Nifty Sensex stock specific news",
    )
    session = _session({"Accept": "application/rss+xml,application/xml,text/xml,*/*"})
    feeds: list[dict[str, str]] = []
    errors: list[str] = []
    total_bytes = 0
    last_status = 0
    last_url = base_url
    for query in queries:
        try:
            response = session.get(
                base_url,
                params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            errors.append(f"{query}: {exc}")
            continue
        last_status = response.status_code
        last_url = response.url
        body = response.content
        total_bytes += len(body)
        if total_bytes > 5_000_000:
            return MultiStepFetchResult(
                False,
                last_url,
                last_status,
                b"",
                "application/json",
                "Google News RSS bundle exceeds the 5 MB safety limit",
            )
        if (
            response.status_code != 200
            or not body
            or b"<rss" not in body[:1000].lower()
            or b"<item>" not in body
        ):
            errors.append(f"{query}: unusable HTTP {response.status_code}")
            continue
        feeds.append(
            {
                "query": query,
                "url": response.url,
                "xml": body.decode(response.encoding or "utf-8", errors="replace"),
            }
        )
    if not feeds:
        return MultiStepFetchResult(
            False,
            last_url,
            last_status,
            b"",
            "application/json",
            "Google News RSS returned no populated feeds: " + "; ".join(errors[:3]),
        )
    payload = json.dumps(
        {
            "feeds": feeds,
            "requestedFeedCount": len(queries),
            "successfulFeedCount": len(feeds),
            "errors": errors,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return MultiStepFetchResult(
        True,
        base_url,
        200,
        payload,
        "application/json",
        None,
    )


def fetch_nse_market_status() -> MultiStepFetchResult:
    """Fetch NSE's official market-session state after one cookie warm-up."""
    home = "https://www.nseindia.com/"
    url = "https://www.nseindia.com/api/marketStatus"
    session = _session(
        {
            "Accept": "application/json,text/plain,*/*",
            "Referer": home,
        }
    )
    try:
        session.get(home, timeout=TIMEOUT)
        response = session.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "application/json", str(exc))
    body = response.content
    ok = response.status_code == 200 and 100 < len(body) < 500_000
    error: str | None = None
    if ok:
        try:
            payload = response.json()
            states = payload.get("marketState") if isinstance(payload, dict) else None
            # marketStatus also includes auxiliary index-only rows without a
            # market/session label.  Require at least one usable session row;
            # the parser will count and ignore auxiliary rows deterministically.
            ok = isinstance(states, list) and bool(states) and any(
                isinstance(row, dict) and row.get("market") and row.get("marketStatus")
                for row in states
            )
            if not ok:
                error = "NSE marketStatus failed populated schema checks"
        except ValueError as exc:
            ok = False
            error = f"NSE marketStatus is invalid JSON: {exc}"
    if not ok and error is None:
        error = f"NSE marketStatus unusable HTTP {response.status_code}"
    return MultiStepFetchResult(
        ok,
        response.url,
        response.status_code,
        body if ok else b"",
        response.headers.get("content-type", "application/json"),
        error,
    )


def fetch_rupeevest_mf_flows() -> MultiStepFetchResult:
    """Fetch RupeeVest identity plus monthly MF buy/sell aggregates once each."""
    page_url = "https://www.rupeevest.com/Mutual-Fund-Holdings"
    routes = {
        "search": "https://www.rupeevest.com/mf_stock_portfolio/get_search_data_stock",
        "buys": "https://www.rupeevest.com/stock_price_difference/get_compare_data_stock",
        "sells": "https://www.rupeevest.com/stock_price_difference/get_compare_data_stock_1",
    }
    session = _session(
        {
            "Accept": "application/json,text/plain,*/*",
            "Referer": page_url,
            "X-Requested-With": "XMLHttpRequest",
        }
    )
    payload: dict[str, Any] = {"urls": routes}
    total_bytes = 0
    last_status = 0
    try:
        session.get(page_url, timeout=TIMEOUT)
        for name, route in routes.items():
            response = session.get(route, timeout=TIMEOUT)
            last_status = response.status_code
            total_bytes += len(response.content)
            if response.status_code != 200 or not response.content or total_bytes > 2_000_000:
                return MultiStepFetchResult(
                    False,
                    route,
                    response.status_code,
                    b"",
                    "application/json",
                    f"RupeeVest {name} response failed HTTP/size checks",
                )
            try:
                payload[name] = response.json()
            except ValueError as exc:
                return MultiStepFetchResult(
                    False,
                    route,
                    response.status_code,
                    b"",
                    "application/json",
                    f"RupeeVest {name} is invalid JSON: {exc}",
                )
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, page_url, last_status, b"", "application/json", str(exc))
    identities = payload.get("search", {}).get("stock_data_search", [])
    buys = payload.get("buys", {}).get("stock_compare_data", [])
    sells = payload.get("sells", {}).get("stock_compare_data_1", [])
    ok = (
        isinstance(identities, list)
        and len(identities) >= 100
        and isinstance(buys, list)
        and bool(buys)
        and isinstance(sells, list)
        and bool(sells)
    )
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return MultiStepFetchResult(
        ok,
        page_url,
        last_status,
        body if ok else b"",
        "application/json",
        None if ok else "RupeeVest bundle failed populated row/schema checks",
    )


def fetch_crisil_ratings(*, limit: int = 100) -> MultiStepFetchResult:
    """Fetch CRISIL's official latest rating-rationales JSON listing."""
    url = (
        "https://www.crisilratings.com/content/crisilratings/en/home/our-business/"
        "ratings/rating-rationale/_jcr_content/wrapper_100_par/"
        "ratingresultlisting.results.json"
    )
    bounded_limit = max(1, min(int(limit), 250))
    session = _session({"Accept": "application/json"})
    try:
        response = session.get(
            url,
            params={"cmd": "RR", "start": 0, "limit": bounded_limit, "filters": "{}"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "application/json", str(exc))
    content_type = response.headers.get("content-type", "application/octet-stream")
    ok = response.status_code == 200 and "json" in content_type.casefold()
    error: str | None = None
    if ok:
        if not response.content or len(response.content) > 5_000_000:
            ok = False
            error = "CRISIL response is empty or exceeds the 5 MB safety limit"
        else:
            try:
                payload = response.json()
                docs = payload.get("docs") if isinstance(payload, dict) else None
                ok = isinstance(docs, list) and bool(docs)
                if not ok:
                    error = "CRISIL response has no populated docs list"
            except ValueError as exc:
                ok = False
                error = f"CRISIL response is invalid JSON: {exc}"
    elif error is None:
        error = f"CRISIL rating-rationales unusable HTTP {response.status_code}"
    return MultiStepFetchResult(
        ok,
        response.url,
        response.status_code,
        response.content if ok else b"",
        content_type,
        error,
    )


def fetch_icra_ratings(*, page: int = 1) -> MultiStepFetchResult:
    """Fetch one official ICRA rating-rationales page using its CSRF session."""
    landing = "https://www.icra.in/Rating/AllRatingRationales?Keyword="
    endpoint = f"https://www.icra.in/Rating/GetAllRatingRational?page={max(1, int(page))}&type=Search"
    session = _session({"Accept": "text/html,application/xhtml+xml"})
    try:
        initial = session.get(landing, timeout=TIMEOUT)
        match = re.search(
            r'name=["\']__RequestVerificationToken["\'][^>]*value=["\']([^"\']+)',
            initial.text,
            re.I,
        )
        if initial.status_code != 200 or not match:
            return MultiStepFetchResult(False, landing, initial.status_code, b"", "text/html", "ICRA landing page or CSRF token unavailable")
        response = session.post(
            endpoint,
            data={"__RequestVerificationToken": match.group(1), "KeyWord": "", "PageType": "Search", "pageNumber": str(max(1, int(page)))},
            headers={"Referer": landing, "X-Requested-With": "XMLHttpRequest"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, endpoint, 0, b"", "text/html", str(exc))
    body = response.content
    ok = response.status_code == 200 and 0 < len(body) < 2_000_000 and b"<tr" in body.lower() and b"Rationale" in body
    return MultiStepFetchResult(ok, response.url, response.status_code, body if ok else b"", response.headers.get("content-type", "text/html"), None if ok else "ICRA rating-rationales table is empty or invalid")


def fetch_care_ratings() -> MultiStepFetchResult:
    """Fetch CARE's page-owned latest rating-rationale JSON contract."""
    landing = "https://www.careratings.com/find-ratings"
    endpoint = "https://www.careratings.com/rrcompany"
    session = _session({"Accept": "text/html,application/xhtml+xml"})
    try:
        initial = session.get(landing, timeout=TIMEOUT)
        if initial.status_code != 200 or "/rrcompany" not in initial.text:
            return MultiStepFetchResult(False, landing, initial.status_code, b"", "text/html", "CARE landing page does not expose the rating JSON contract")
        response = session.get(
            endpoint,
            params={"companyName": "IDBI", "YearID": "2022", "fdate": "", "tdate": ""},
            headers={"Accept": "application/json", "Referer": landing},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, endpoint, 0, b"", "application/json", str(exc))
    body = response.content
    ok = response.status_code == 200 and 0 < len(body) < 5_000_000
    error: str | None = None
    if ok:
        try:
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            ok = isinstance(data, list) and bool(data)
            if not ok:
                error = "CARE response has no populated data list"
        except ValueError as exc:
            ok = False
            error = f"CARE response is invalid JSON: {exc}"
    if not ok and error is None:
        error = f"CARE rating-rationale endpoint unusable HTTP {response.status_code}"
    return MultiStepFetchResult(
        ok,
        response.url,
        response.status_code,
        body if ok else b"",
        response.headers.get("content-type", "application/json"),
        error,
    )


def fetch_angelone_instrument_master() -> MultiStepFetchResult:
    """Fetch Angel One's public full instrument master with strict integrity caps."""
    url = (
        "https://margincalculator.angelone.in/OpenAPI_File/files/"
        "OpenAPIScripMaster.json"
    )
    session = _session({"Accept": "application/json"})
    try:
        response = session.get(url, timeout=60)
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "application/json", str(exc))
    body = response.content
    ok = response.status_code == 200 and 1_000_000 < len(body) < 45_000_000
    error: str | None = None
    if ok:
        try:
            payload = response.json()
            ok = (
                isinstance(payload, list)
                and len(payload) >= 10_000
                and isinstance(payload[0], dict)
                and {"token", "symbol", "exch_seg"} <= set(payload[0])
            )
            if not ok:
                error = "Angel One master failed minimum row/schema integrity checks"
        except ValueError as exc:
            ok = False
            error = f"Angel One master is invalid JSON: {exc}"
    if not ok and error is None:
        error = f"Angel One public master unusable HTTP {response.status_code}"
    return MultiStepFetchResult(
        ok,
        response.url,
        response.status_code,
        body if ok else b"",
        response.headers.get("content-type", "application/json"),
        error,
    )


def fetch_dhan_instrument_master() -> MultiStepFetchResult:
    """Fetch Dhan's public detailed instrument CSV with strict integrity caps."""
    url = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"
    session = _session({"Accept": "text/csv,application/octet-stream,*/*"})
    try:
        response = session.get(url, timeout=60)
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "text/csv", str(exc))
    body = response.content
    header = body[:2000].upper()
    ok = (
        response.status_code == 200
        and 1_000_000 < len(body) < 45_000_000
        and b"EXCH_ID" in header
        and b"SECURITY_ID" in header
        and b"LOT_SIZE" in header
        and body.count(b"\n") >= 10_000
    )
    return MultiStepFetchResult(
        ok,
        response.url,
        response.status_code,
        body if ok else b"",
        response.headers.get("content-type", "text/csv"),
        None if ok else f"Dhan public master failed HTTP/size/schema checks ({response.status_code})",
    )


def fetch_westmetall_lme() -> MultiStepFetchResult:
    """Fetch all six Westmetall LME tables in one shared-session source result."""
    fields = {
        "copper": "LME_Cu_cash",
        "aluminium": "LME_Al_cash",
        "zinc": "LME_Zn_cash",
        "lead": "LME_Pb_cash",
        "nickel": "LME_Ni_cash",
        "tin": "LME_Sn_cash",
    }
    base = "https://www.westmetall.com/en/markdaten.php?action=table&field="
    session = _session({"Accept": "text/html,application/xhtml+xml"})
    pages: list[dict[str, str]] = []
    last_error = "no Westmetall page"
    last_status = 0
    last_url = base + fields["copper"]
    for metal, field in fields.items():
        url = base + field
        last_url = url
        try:
            response = session.get(url, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last_error = f"{metal}: {exc}"
            break
        last_status = response.status_code
        body = response.content
        if not (
            response.status_code < 400
            and len(body) < 1_000_000
            and b"<table" in body.lower()
            and b"stock" in body.lower()
        ):
            last_error = f"{metal}: unusable HTTP {response.status_code}"
            break
        pages.append(
            {
                "metal": metal,
                "url": url,
                "html": body.decode(response.encoding or "utf-8", errors="replace"),
            }
        )
    if len(pages) != len(fields):
        return MultiStepFetchResult(
            False, last_url, last_status, b"", "application/json", last_error
        )
    content = json.dumps(
        {"source": "westmetall_lme", "pages": pages}, ensure_ascii=False
    ).encode("utf-8")
    return MultiStepFetchResult(
        True, base + "{metal}", 200, content, "application/json", None
    )


def fetch_mcx_top_participants() -> MultiStepFetchResult:
    """Try MCX official paths; on WAF 403 fall back to Yahoo commodity proxy rows."""
    s = _session({"Referer": "https://www.mcxindia.com/", "Accept": "*/*"})
    day = datetime.now() - timedelta(days=1)
    tried = []
    for back in range(0, 10):
        d = day - timedelta(days=back)
        if d.weekday() >= 5:
            continue
        ymd = d.strftime("%Y%m%d")
        urls = [
            f"https://www.mcxindia.com/docs/default-source/market-data/top-participants/top_participants_{ymd}.xlsx",
            f"https://www.mcxindia.com/docs/default-source/market-data/market-wide-oi/market_wide_oi_{ymd}.xlsx",
            "https://www.mcxindia.com/market-data/top-participants",
            "https://www.mcxindia.com/market-data/market-watch",
        ]
        for url in urls:
            tried.append(url)
            try:
                r = s.get(url, timeout=60)
                if r.status_code < 400 and (
                    r.content[:2] == b"PK"
                    or b"<table" in r.content.lower()
                    or (r.content[:1] == b"{" and b"Access Denied" not in r.content[:200])
                ):
                    return MultiStepFetchResult(
                        True,
                        url,
                        r.status_code,
                        r.content,
                        r.headers.get("content-type", "application/octet-stream"),
                        None,
                    )
            except requests.RequestException:
                continue
    # Research proxy when MCX WAF blocks the collector IP
    proxy = fetch_yahoo_symbols(
        ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "ALI=F"], range_="5d"
    )
    if proxy.ok:
        return MultiStepFetchResult(
            True,
            proxy.url,
            proxy.status_code,
            proxy.content,
            "application/json",
            None,
        )
    return MultiStepFetchResult(
        False,
        tried[-1] if tried else "https://www.mcxindia.com/",
        0,
        b"",
        "application/octet-stream",
        "mcx top participants not downloadable",
    )


def fetch_mcx_post_json(path: str, body: dict[str, Any] | None = None) -> MultiStepFetchResult:
    """POST MCX ASP.NET backpage JSON endpoints; Yahoo proxy on Access Denied."""
    seed = "https://www.mcxindia.com/market-data/market-watch"
    url = path if path.startswith("http") else f"https://www.mcxindia.com{path}"
    s = _session(
        {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": seed,
            "Origin": "https://www.mcxindia.com",
        }
    )
    try:
        s.get(seed, timeout=TIMEOUT)
        s.get("https://www.mcxindia.com/", timeout=TIMEOUT)
        r = s.post(url, data=json.dumps(body or {}), timeout=60)
        ok = (
            r.status_code < 400
            and len(r.content) > 2
            and b"Access Denied" not in r.content[:200]
        )
        if ok:
            return MultiStepFetchResult(
                True,
                url,
                r.status_code,
                r.content,
                r.headers.get("content-type", "application/json"),
                None,
            )
    except requests.RequestException:
        pass
    # Honest research proxy: liquid commodity futures OHLC (not MCX venue LTP)
    proxy_syms = {
        "/backpage.aspx/GetOptionChain": ["GC=F", "SI=F"],
        "/backpage.aspx/GetMarketWatch": ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "ALI=F"],
    }
    symbols = proxy_syms.get(path if path.startswith("/") else "/" + path.split("/")[-1], ["GC=F", "SI=F", "CL=F"])
    proxy = fetch_yahoo_symbols(symbols, range_="5d")
    if proxy.ok:
        return MultiStepFetchResult(
            True, proxy.url, 200, proxy.content, "application/json", None
        )
    return MultiStepFetchResult(False, url, 403, b"", "application/json", "MCX POST HTTP 403")


def fetch_ncdex_bhav_or_watch() -> MultiStepFetchResult:
    """Best-effort NCDEX public pages; agri Yahoo proxy when SPA/WAF blocks."""
    s = _session({"Referer": "https://www.ncdex.com/"})
    candidates = [
        "https://www.ncdex.com/market-data/live-futures-prices",
        "https://www.ncdex.com/market-data/bhavcopy",
        "https://ncdex.com/market-data/live-futures-prices",
        "https://www.ncdex.com/Downloads/Bhavcopy/Future/",
    ]
    last = candidates[0]
    for url in candidates:
        last = url
        try:
            r = s.get(url, timeout=TIMEOUT)
            # Bot wall returns tiny loader HTML without table/data
            if (
                r.status_code < 400
                and len(r.content) > 5000
                and (b"<table" in r.content.lower() or b"csv" in r.content.lower() or b"{" in r.content[:20])
            ):
                return MultiStepFetchResult(
                    True,
                    url,
                    r.status_code,
                    r.content,
                    r.headers.get("content-type", "text/html"),
                    None,
                )
        except requests.RequestException:
            continue
    proxy = fetch_yahoo_symbols(["ZW=F", "ZC=F", "ZS=F", "KC=F", "CT=F"], range_="1mo")
    if proxy.ok:
        return MultiStepFetchResult(
            True, proxy.url, 200, proxy.content, "application/json", None
        )
    return MultiStepFetchResult(False, last, 0, b"", "text/html", "ncdex unavailable")


def fetch_nse_bulk_deal_symbol(symbol: str = "RELIANCE") -> MultiStepFetchResult:
    """Prefer bulk-deal archives; fall back to capital-market large-deal snapshot."""
    s = _session({"Accept": "application/json,text/html,*/*"})
    try:
        s.get("https://www.nseindia.com", timeout=TIMEOUT)
        u = f"https://www.nseindia.com/api/bulk-deal-archives?symbol={urllib.parse.quote(symbol)}"
        r = s.get(
            u,
            headers={
                "Accept": "application/json",
                "Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
            },
            timeout=TIMEOUT,
        )
        if r.status_code < 400 and r.content[:1] == b"{":
            return MultiStepFetchResult(
                True, u, r.status_code, r.content, "application/json", None
            )
    except requests.RequestException:
        pass
    # Working public snapshot (no Akamai block observed)
    u2 = "https://www.nseindia.com/api/snapshot-capital-market-largedeal"
    try:
        r2 = s.get(u2, headers={"Accept": "application/json"}, timeout=TIMEOUT)
        if r2.status_code < 400 and r2.content[:1] == b"{":
            try:
                payload = r2.json()
            except ValueError:
                return MultiStepFetchResult(
                    False, u2, r2.status_code, r2.content, "application/json", "largedeal not JSON"
                )
            rows = payload.get("BULK_DEALS_DATA") or payload.get("data") or []
            filtered = [
                row
                for row in rows
                if isinstance(row, dict)
                and symbol.upper()
                in str(row.get("symbol") or row.get("Symbol") or row.get("name") or "").upper()
            ]
            out = {
                "as_on_date": payload.get("as_on_date"),
                "symbolFilter": symbol.upper(),
                "data": filtered or (rows[:50] if isinstance(rows, list) else []),
                "BULK_DEALS_DATA": filtered or (rows[:50] if isinstance(rows, list) else []),
                "proxySource": "snapshot-capital-market-largedeal",
            }
            body = json.dumps(out).encode("utf-8")
            return MultiStepFetchResult(True, u2, 200, body, "application/json", None)
        return MultiStepFetchResult(
            False, u2, getattr(r2, "status_code", 0), getattr(r2, "content", b""), "application/json", "largedeal fail"
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, u2, 0, b"", "application/json", str(exc))


def fetch_nse_trade_info(symbol: str = "RELIANCE") -> MultiStepFetchResult:
    """quote-equity trade_info with cookie prime; archives bhav delivery fallback."""
    s = _session({"Accept": "application/json,text/html,*/*"})
    u = f"https://www.nseindia.com/api/quote-equity?symbol={urllib.parse.quote(symbol)}&section=trade_info"
    try:
        s.get("https://www.nseindia.com", timeout=TIMEOUT)
        s.get(
            f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
            timeout=TIMEOUT,
        )
        r = s.get(
            u,
            headers={
                "Accept": "application/json",
                "Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
            },
            timeout=TIMEOUT,
        )
        if r.status_code < 400 and r.content[:1] == b"{" and b"Access Denied" not in r.content[:80]:
            return MultiStepFetchResult(
                True, u, r.status_code, r.content, "application/json", None
            )
    except requests.RequestException:
        pass
    # Official archives full bhav includes DELIV_QTY / DELIV_PER
    day = date.today()
    for back in range(0, 10):
        d = day - timedelta(days=back)
        if d.weekday() >= 5:
            continue
        dd = d.strftime("%d%m%Y")
        for base in (
            "https://nsearchives.nseindia.com/products/content",
            "https://archives.nseindia.com/products/content",
        ):
            bu = f"{base}/sec_bhavdata_full_{dd}.csv"
            try:
                rr = s.get(bu, timeout=TIMEOUT)
                if rr.status_code >= 400 or len(rr.content) < 200:
                    continue
                text = rr.content.decode("utf-8", errors="replace")
                lines = text.splitlines()
                if not lines:
                    continue
                header = lines[0]
                hit = None
                for line in lines[1:]:
                    if line.upper().startswith(f"{symbol.upper()},") or f",{symbol.upper()}," in f",{line.upper()}":
                        # first column SYMBOL
                        if line.split(",")[0].strip().upper() == symbol.upper():
                            hit = line
                            break
                if not hit:
                    continue
                cols = [c.strip() for c in header.split(",")]
                vals = [c.strip() for c in hit.split(",")]
                rec = {cols[i]: vals[i] if i < len(vals) else "" for i in range(len(cols))}
                rec["symbol"] = symbol.upper()
                body = json.dumps(
                    {
                        "symbol": symbol.upper(),
                        "securityWiseDP": rec,
                        "proxySource": "sec_bhavdata_full",
                        "dataDate": rec.get("DATE1") or d.isoformat(),
                        "data": [rec],
                    }
                ).encode("utf-8")
                return MultiStepFetchResult(True, bu, 200, body, "application/json", None)
            except requests.RequestException:
                continue
    return MultiStepFetchResult(False, u, 403, b"", "application/json", "NSE_SYMBOL_JSON_FAILED")


def fetch_cdsl_or_nsdl_fpi() -> MultiStepFetchResult:
    """CDSL fortnightly page is often 403; use NSDL FPI fortnightly selection as research peer."""
    s = _session({"Accept": "text/html,application/xhtml+xml"})
    for url in (
        "https://www.cdslindia.com/publications/FII/FortnightlySecWisePages/",
        "https://www.cdslindia.com/Publications/ForeignInvestments.html",
        "https://www.fpi.nsdl.co.in/web/Reports/FPI_Fortnightly_Selection.aspx",
        "https://www.fpi.nsdl.co.in/web/Reports/ReportsListing.aspx",
    ):
        try:
            r = s.get(url, timeout=TIMEOUT)
            if r.status_code < 400 and len(r.content) > 2000 and b"Access Denied" not in r.content[:200]:
                return MultiStepFetchResult(
                    True,
                    url,
                    r.status_code,
                    r.content,
                    r.headers.get("content-type", "text/html"),
                    None,
                )
        except requests.RequestException:
            continue
    return MultiStepFetchResult(
        False,
        "https://www.cdslindia.com/publications/FII/FortnightlySecWisePages/",
        403,
        b"",
        "text/html",
        "CDSL/NSDL FPI pages unavailable",
    )


def fetch_usda_wasde() -> MultiStepFetchResult:
    """Discover the latest official ESMIS WASDE XML, then use bounded fallbacks."""
    s = _session({"Accept": "application/json,application/xml,text/xml,text/plain,*/*"})
    discovery = "https://esmis.nal.usda.gov/api/v1/release/findByIdentifier/WASDE"
    errors: list[str] = []
    try:
        release_response = s.get(discovery, timeout=TIMEOUT)
        if release_response.status_code == 200:
            release_payload = release_response.json()
            results = (
                release_payload.get("results")
                if isinstance(release_payload, dict)
                else None
            )
            if isinstance(results, list):
                for release in results[:25]:
                    if not isinstance(release, dict):
                        continue
                    xml_url = next(
                        (
                            str(item)
                            for item in release.get("files", [])
                            if str(item).casefold().endswith(".xml")
                        ),
                        None,
                    )
                    if not xml_url:
                        continue
                    xml_response = s.get(xml_url, timeout=TIMEOUT)
                    xml = xml_response.content
                    if (
                        xml_response.status_code == 200
                        and 200 < len(xml) < 10_000_000
                        and b"<Report" in xml[:1000]
                        and b"<Cell" in xml
                    ):
                        body = json.dumps(
                            {
                                "discoveryUrl": discovery,
                                "release": release,
                                "xmlUrl": xml_url,
                                "xml": xml.decode(
                                    xml_response.encoding or "utf-8",
                                    errors="replace",
                                ),
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ).encode("utf-8")
                        return MultiStepFetchResult(
                            True,
                            xml_url,
                            200,
                            body,
                            "application/json",
                            None,
                        )
                errors.append("ESMIS releases contained no populated XML file")
            else:
                errors.append("ESMIS release response has no results list")
        else:
            errors.append(f"ESMIS release discovery HTTP {release_response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        errors.append(f"ESMIS discovery failed: {exc}")

    # Official direct month path when ESMIS metadata is temporarily unavailable.
    month = date.today().replace(day=1)
    for _ in range(6):
        direct = (
            "https://www.usda.gov/oce/commodity/wasde/"
            f"wasde{month.strftime('%m%y')}.xml"
        )
        try:
            response = s.get(direct, timeout=TIMEOUT)
            if (
                response.status_code == 200
                and 200 < len(response.content) < 10_000_000
                and b"<Report" in response.content[:1000]
                and b"<Cell" in response.content
            ):
                return MultiStepFetchResult(
                    True,
                    direct,
                    200,
                    response.content,
                    response.headers.get("content-type", "application/xml"),
                    None,
                )
        except requests.RequestException as exc:
            errors.append(f"{direct}: {exc}")
        month = (month - timedelta(days=1)).replace(day=1)

    # Cornell remains a last fallback for continuity with the existing key.
    index = "https://usda.library.cornell.edu/concern/publications/3t945q76s?locale=en"
    try:
        r0 = s.get(index, timeout=TIMEOUT)
        if r0.status_code < 400:
            links = re.findall(
                r'href="(/sites/default/release-files/\d+/wasde[^"]+\.txt)"',
                r0.text,
                flags=re.I,
            )
            if links:
                path = links[0]
                file_url = f"https://usda.library.cornell.edu{path}"
                r1 = s.get(file_url, timeout=TIMEOUT)
                if r1.status_code < 400 and len(r1.content) > 500:
                    return MultiStepFetchResult(
                        True,
                        file_url,
                        r1.status_code,
                        r1.content,
                        r1.headers.get("content-type", "text/plain"),
                        None,
                    )
            if b"wasde" in r0.content.lower() or b"release-files" in r0.content:
                return MultiStepFetchResult(
                    True,
                    index,
                    r0.status_code,
                    r0.content,
                    r0.headers.get("content-type", "text/html"),
                    None,
                )
    except requests.RequestException as exc:
        errors.append(f"Cornell fallback failed: {exc}")
    return MultiStepFetchResult(
        False,
        index,
        0,
        b"",
        "text/html",
        "WASDE unavailable: " + "; ".join(errors[-4:]),
    )


def parse_fii_derivatives_xls(
    content: bytes, *, url: str | None = None
) -> dict[str, Any]:
    """Parse classic FII derivatives .xls via xlrd when available."""
    from .parsers.common import extract_data_date, source_result

    data_date, date_source = extract_data_date(
        content.decode("latin-1", errors="replace")[:2000], url, None
    )
    try:
        import xlrd
    except ImportError:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary="xlrd not installed for FII derivatives XLS",
            output={"dateSource": date_source, "rows": [], "needsXlrd": True},
            error="xlrd missing",
        )

    try:
        book = xlrd.open_workbook(file_contents=content)
        sheet = book.sheet_by_index(0)
    except Exception as exc:  # noqa: BLE001
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary=f"XLS open failed: {exc}",
            output={"dateSource": date_source, "rows": []},
            error=str(exc),
        )

    rows: list[dict[str, Any]] = []
    for r in range(sheet.nrows):
        values = [sheet.cell_value(r, c) for c in range(min(7, sheet.ncols))]
        if not values:
            continue
        name = str(values[0]).strip()
        if not name or not re.search(r"INDEX|STOCK|FUTURE|OPTION", name, re.I):
            continue

        def num(i: int) -> float | None:
            if i >= len(values):
                return None
            v = values[i]
            if isinstance(v, (int, float)):
                return float(v)
            try:
                return float(str(v).replace(",", "").strip())
            except ValueError:
                return None

        rows.append(
            {
                "instrument": name,
                "buy_contracts": num(1),
                "buy_amt_cr": num(2),
                "sell_contracts": num(3),
                "sell_amt_cr": num(4),
                "oi_contracts": num(5),
                "oi_amt_cr": num(6),
                "symbol": re.sub(r"[^A-Z0-9]+", "_", name.upper())[:32],
            }
        )

    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="FII derivatives XLS had no instrument rows",
            output={"dateSource": date_source, "rows": []},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"FII derivatives XLS rows={len(rows)}",
        output={"dateSource": date_source, "rows": rows, "records": rows},
    )


# ── NSE cookie-primed institutional stock-regime feeds (from audit script 1.txt)
def _nse_cookie_session() -> requests.Session:
    """Prime NSE cookies the way public scrapers do (homepage + Referer)."""
    s = _session(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.nseindia.com/",
            "Origin": "https://www.nseindia.com",
        }
    )
    try:
        s.get("https://www.nseindia.com", timeout=TIMEOUT)
        s.get("https://www.nseindia.com/reports/fii-dii", timeout=TIMEOUT)
    except requests.RequestException:
        pass
    return s


def _trading_days_back(n: int = 7) -> list[date]:
    """Last n weekdays (calendar Mon–Fri). Holidays still tried; 404 is ok."""
    days: list[date] = []
    d = date.today()
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    return days


def fetch_nse_fii_dii_api() -> MultiStepFetchResult:
    """Cookie-primed GET of NSE FII/DII JSON (fiidiiTradeReact)."""
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    s = _nse_cookie_session()
    try:
        r = s.get(
            url,
            headers={
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.nseindia.com/reports/fii-dii",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=TIMEOUT,
        )
        body = r.content or b""
        ok = (
            r.status_code < 400
            and len(body) > 20
            and b"Access Denied" not in body[:200]
            and (body.lstrip()[:1] in (b"{", b"[") or b"buyValue" in body or b"Buy" in body)
        )
        return MultiStepFetchResult(
            ok,
            url,
            r.status_code,
            body if ok else b"",
            r.headers.get("content-type", "application/json"),
            None if ok else f"NSE FII/DII HTTP {r.status_code} or non-JSON",
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "application/json", str(exc))


def fetch_nse_participant_oi_archive(*, days_back: int = 7) -> MultiStepFetchResult:
    """Walk recent weekdays for fao_participant_oi_DDMMYYYY.csv archives."""
    last_err = "no candidate"
    last_url = "https://archives.nseindia.com/content/nsccl/"
    for d in _trading_days_back(days_back):
        ddmmyyyy = d.strftime("%d%m%Y")
        for base in (
            "https://archives.nseindia.com/content/nsccl",
            "https://nsearchives.nseindia.com/content/nsccl",
        ):
            url = f"{base}/fao_participant_oi_{ddmmyyyy}.csv"
            last_url = url
            try:
                r = requests.get(
                    url,
                    headers={"User-Agent": UA, "Accept": "text/csv,*/*"},
                    timeout=TIMEOUT,
                )
                body = r.content or b""
                if (
                    r.status_code < 400
                    and len(body) > 200
                    and b"<!DOCTYPE" not in body[:80]
                    and b"<html" not in body[:80].lower()
                ):
                    return MultiStepFetchResult(
                        True,
                        url,
                        r.status_code,
                        body,
                        r.headers.get("content-type", "text/csv"),
                        None,
                    )
                last_err = f"HTTP {r.status_code} {url}"
            except requests.RequestException as exc:
                last_err = str(exc)
    return MultiStepFetchResult(False, last_url, 0, b"", "text/csv", last_err)


def fetch_cftc_cot_disagg(*, year: int | None = None) -> MultiStepFetchResult:
    """Primary CFTC disaggregated COT — dynamic year ZIP then live f_disagg.txt.

    Replaces hard-coded year scrapers; feeds existing parse_cftc_cot_positions.
    """
    y = year or date.today().year
    candidates: list[str] = []
    for yr in (y, y - 1):
        candidates.append(
            f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{yr}.zip"
        )
    candidates.extend(
        [
            "https://www.cftc.gov/dea/newcot/f_disagg.txt",
            "https://www.cftc.gov/dea/newcot/c_disagg.txt",
        ]
    )
    last_err = "no candidate"
    last_url = candidates[0]
    s = _session({"Accept": "*/*"})
    for url in candidates:
        last_url = url
        try:
            r = s.get(url, timeout=60)
            body = r.content or b""
            if r.status_code >= 400 or len(body) < 500:
                last_err = f"HTTP {r.status_code} len={len(body)} {url}"
                continue
            # ZIP → extract first .txt for existing text parser
            if url.endswith(".zip") or body[:2] == b"PK":
                import zipfile
                import io

                try:
                    with zipfile.ZipFile(io.BytesIO(body)) as zf:
                        names = [
                            n
                            for n in zf.namelist()
                            if n.lower().endswith((".txt", ".csv"))
                            and not n.endswith("/")
                        ]
                        if not names:
                            last_err = f"zip empty {url}"
                            continue
                        # Prefer disagg-like names
                        names.sort(
                            key=lambda n: (
                                0 if "disagg" in n.lower() else 1,
                                len(n),
                            )
                        )
                        extracted = zf.read(names[0])
                        if len(extracted) < 500:
                            last_err = f"zip member tiny {names[0]}"
                            continue
                        return MultiStepFetchResult(
                            True,
                            url + f"#{names[0]}",
                            200,
                            extracted,
                            "text/plain",
                            None,
                        )
                except zipfile.BadZipFile as exc:
                    last_err = f"bad zip {exc}"
                    continue
            # Plain text body
            if b"<!DOCTYPE" in body[:80] or b"<html" in body[:80].lower():
                last_err = f"HTML not COT {url}"
                continue
            return MultiStepFetchResult(
                True,
                url,
                r.status_code,
                body,
                r.headers.get("content-type", "text/plain"),
                None,
            )
        except requests.RequestException as exc:
            last_err = str(exc)
    return MultiStepFetchResult(False, last_url, 0, b"", "text/plain", last_err)


def fetch_mcx_warehouse_position(*, max_pdfs: int = 3) -> MultiStepFetchResult:
    """MCX/MCXCCL stock-position listing + optional latest PDF metadata/rows.

    Prefer structured JSON of PDF inventory dates (always useful). If pdfplumber
    is installed, also parse the newest PDF tables into flat rows.
    Falls back to empty fail only when listing is unreachable.
    """
    listing_url = "https://www.mcxccl.com/warehousing-logistics/stock-position-in-lots"
    s = _session(
        {
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Referer": "https://www.mcxccl.com/",
        }
    )
    try:
        r = s.get(listing_url, timeout=TIMEOUT)
        if r.status_code >= 400 or len(r.content) < 200:
            # Fall back to existing Yahoo/MCX watch proxy chain via caller
            return MultiStepFetchResult(
                False,
                listing_url,
                r.status_code,
                b"",
                "text/html",
                f"MCXCCL listing HTTP {r.status_code}",
            )
        pdf_paths = re.findall(
            r'href="(/docs/mcxccllibraries/warehousing-operations/stock-position-in-lots/[^"]+\.pdf)"',
            r.text,
            flags=re.I,
        )
        pdf_paths = list(dict.fromkeys(pdf_paths))
        records: list[dict[str, Any]] = []
        for i, path in enumerate(pdf_paths[: max(1, max_pdfs)]):
            m = re.search(r"as-on-(?:date-)?(\d{2}-\d{2}-\d{4})", path, flags=re.I)
            date_tag = m.group(1) if m else f"file_{i}"
            full = f"https://www.mcxccl.com{path}"
            rec: dict[str, Any] = {
                "name": path.rsplit("/", 1)[-1],
                "url": full,
                "as_on": date_tag,
                "symbol": "MCX_WAREHOUSE",
                "source": "mcxccl_stock_position",
            }
            # Best-effort PDF table parse (optional dependency)
            try:
                pr = s.get(full, timeout=60)
                if pr.status_code < 400 and len(pr.content) > 5000:
                    rec["pdf_bytes"] = len(pr.content)
                    try:
                        import pdfplumber  # type: ignore
                        import io

                        with pdfplumber.open(io.BytesIO(pr.content)) as pdf:
                            for page in pdf.pages[:3]:
                                tables = page.extract_tables() or []
                                for table in tables[:2]:
                                    if not table or len(table) < 2:
                                        continue
                                    for data_row in table[1:15]:
                                        cells = [
                                            str(c or "").strip() for c in data_row
                                        ]
                                        if not any(cells):
                                            continue
                                        row_obj = {
                                            f"c{j}": cells[j]
                                            for j in range(len(cells))
                                        }
                                        row_obj["as_on"] = date_tag
                                        row_obj["url"] = full
                                        # first non-empty cell as name/symbol hint
                                        label = next(
                                            (c for c in cells if c), "MCX"
                                        )
                                        row_obj["name"] = label[:80]
                                        row_obj["symbol"] = re.sub(
                                            r"[^A-Z0-9]+",
                                            "_",
                                            label.upper(),
                                        )[:24] or "MCX"
                                        records.append(row_obj)
                    except ImportError:
                        records.append(rec)
                    except Exception:
                        records.append(rec)
                else:
                    records.append(rec)
            except requests.RequestException:
                records.append(rec)

        if not records and pdf_paths:
            # Listing found links but no downloads — still emit link index
            for i, path in enumerate(pdf_paths[:10]):
                m = re.search(
                    r"as-on-(?:date-)?(\d{2}-\d{2}-\d{4})", path, flags=re.I
                )
                records.append(
                    {
                        "name": path.rsplit("/", 1)[-1],
                        "url": f"https://www.mcxccl.com{path}",
                        "as_on": m.group(1) if m else f"file_{i}",
                        "symbol": "MCX_WAREHOUSE",
                        "source": "mcxccl_stock_position",
                    }
                )

        if not records:
            # Return listing HTML so generic HTML table parser may still work
            return MultiStepFetchResult(
                True,
                listing_url,
                r.status_code,
                r.content,
                r.headers.get("content-type", "text/html"),
                None,
            )

        body = json.dumps({"records": records, "rows": records}).encode("utf-8")
        return MultiStepFetchResult(
            True, listing_url, 200, body, "application/json", None
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(
            False, listing_url, 0, b"", "text/html", str(exc)
        )


def fetch_bse_participant_oi_disclosure() -> MultiStepFetchResult:
    """BSE derivatives participant-wise OI via DeriMarketDisclosureData_ng.

    Live-verified 2026-08-10. Pack path ParticipantWiseOI/w is a dead HTML shell.
    """
    url = "https://api.bseindia.com/BseIndiaAPI/api/DeriMarketDisclosureData_ng/w"
    s = _session(
        {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.bseindia.com/",
            "Referer": (
                "https://www.bseindia.com/markets/Derivatives/DeriReports/"
                "DeriMarketDisclosures"
            ),
        }
    )
    try:
        try:
            s.get("https://www.bseindia.com/", timeout=TIMEOUT)
        except requests.RequestException:
            pass
        r = s.get(url, timeout=TIMEOUT)
        body = r.content or b""
        ok = (
            r.status_code < 400
            and len(body) > 80
            and body.lstrip()[:1] in (b"{", b"[")
            and b"<!DOCTYPE" not in body[:80]
            and (b"CLIENT_TYPE" in body or b"IND_FUT" in body or b"Table" in body)
        )
        return MultiStepFetchResult(
            ok,
            url,
            r.status_code,
            body if ok else b"",
            r.headers.get("content-type", "application/json"),
            None
            if ok
            else f"BSE DeriMarketDisclosureData_ng HTTP {r.status_code} or non-JSON",
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "application/json", str(exc))


def fetch_bse_fii_dii_category_turnover() -> MultiStepFetchResult:
    """BSE category-wise FII/DII cash turnover (official CategoryTurnover API).

    Verified live 2026-08-10. The script-pack paths FIIDII/w and
    ParticipantWiseOI/w return HTML shells and are intentionally not used.
    """
    url = "https://api.bseindia.com/BseIndiaAPI/api/CategoryTurnover/w"
    s = _session(
        {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.bseindia.com/",
            "Referer": (
                "https://www.bseindia.com/markets/equity/EQReports/categorywise_turnover"
            ),
        }
    )
    try:
        # Homepage prime helps some BSE API routes; harmless if unused.
        try:
            s.get("https://www.bseindia.com/", timeout=TIMEOUT)
        except requests.RequestException:
            pass
        r = s.get(url, timeout=TIMEOUT)
        body = r.content or b""
        ok = (
            r.status_code < 400
            and len(body) > 40
            and body.lstrip()[:1] in (b"{", b"[")
            and b"<!DOCTYPE" not in body[:80]
            and (b"Table" in body or b"PURCHASE" in body or b"FII" in body)
        )
        return MultiStepFetchResult(
            ok,
            url,
            r.status_code,
            body if ok else b"",
            r.headers.get("content-type", "application/json"),
            None if ok else f"BSE CategoryTurnover HTTP {r.status_code} or non-JSON",
        )
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "application/json", str(exc))


def fetch_nse_fii_derivatives_archive(*, days_back: int = 7) -> MultiStepFetchResult:
    """Walk archives for FII FO stats — CSV fao_participant_fii_* then classic fii_stats XLS."""
    last_err = "no candidate"
    last_url = "https://archives.nseindia.com/content/"
    for d in _trading_days_back(days_back):
        ymd = d.strftime("%Y%m%d")
        mon = d.strftime("%d-%b-%Y")
        candidates = [
            f"https://archives.nseindia.com/content/nsccl/fao_participant_fii_{ymd}.csv",
            f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_fii_{ymd}.csv",
            f"https://archives.nseindia.com/content/fo/fii_stats_{mon}.xls",
            f"https://nsearchives.nseindia.com/content/fo/fii_stats_{mon}.xls",
        ]
        for url in candidates:
            last_url = url
            try:
                r = requests.get(
                    url,
                    headers={"User-Agent": UA, "Accept": "*/*"},
                    timeout=TIMEOUT,
                )
                body = r.content or b""
                if r.status_code >= 400 or len(body) < 200:
                    last_err = f"HTTP {r.status_code} {url}"
                    continue
                if b"<!DOCTYPE" in body[:80] or b"<html" in body[:80].lower():
                    last_err = f"HTML not data {url}"
                    continue
                return MultiStepFetchResult(
                    True,
                    url,
                    r.status_code,
                    body,
                    r.headers.get("content-type", "application/octet-stream"),
                    None,
                )
            except requests.RequestException as exc:
                last_err = str(exc)
    return MultiStepFetchResult(False, last_url, 0, b"", "application/octet-stream", last_err)


def fetch_screener_in_fii_holding_change() -> MultiStepFetchResult:
    """GET a bounded Screener.in FII-hold screen and bundle page HTML."""
    base = "https://www.screener.in/screens/343087/fii-buying/"
    session = _session({"Accept": "text/html,application/xhtml+xml"})
    pages: list[dict[str, Any]] = []
    last_status = 0
    last_url = base
    total_pages = 1
    for page in range(1, 6):
        try:
            response = session.get(base, params={"page": page}, timeout=TIMEOUT)
        except requests.RequestException as exc:
            return MultiStepFetchResult(False, last_url, 0, b"", "application/json", str(exc))
        last_status = response.status_code
        last_url = response.url
        html = response.text or ""
        if response.status_code != 200 or "<table" not in html.casefold():
            break
        if page == 1:
            match = re.search(r"Showing page\s+\d+\s+of\s+(\d+)", html, re.I)
            total_pages = int(match.group(1)) if match else 1
        pages.append({"page": page, "url": response.url, "html": html})
        if page >= total_pages:
            break
    if not pages:
        return MultiStepFetchResult(
            False, last_url, last_status, b"", "application/json",
            f"Screener.in FII screen unusable HTTP {last_status}",
        )
    body = json.dumps({"pages": pages, "source": "screener.in"}, ensure_ascii=False).encode("utf-8")
    return MultiStepFetchResult(True, last_url, last_status, body, "application/json", None)


def fetch_tickertape_fii_holding_change_3m() -> MultiStepFetchResult:
    """POST Tickertape public screener query for 3M FII holding change."""
    url = "https://api.tickertape.in/screener/query"
    session = _session({
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://www.tickertape.in",
    })
    results: list[Any] = []
    last_status = 0
    for offset in (0, 100, 200):
        payload = {
            "match": {"forInstHldng3M": {"g": 0.01, "l": 100}},
            "sortBy": "forInstHldng3M",
            "sortOrder": -1,
            "project": [
                "forInstHldng", "forInstHldng3M", "lastPrice", "mrktCapf",
            ],
            "offset": offset,
            "count": 100,
            "sids": [],
            "universe": "AllStocks",
        }
        try:
            response = session.post(url, json=payload, timeout=TIMEOUT)
        except requests.RequestException as exc:
            return MultiStepFetchResult(False, url, 0, b"", "application/json", str(exc))
        last_status = response.status_code
        if response.status_code != 200:
            break
        try:
            data = response.json().get("data") or {}
        except ValueError:
            return MultiStepFetchResult(False, url, last_status, b"", "application/json", "Tickertape JSON invalid")
        chunk = data.get("results") or []
        if not isinstance(chunk, list) or not chunk:
            break
        results.extend(chunk)
        total = (data.get("stats") or {}).get("count")
        if isinstance(total, int) and offset + 100 >= total:
            break
    if not results:
        return MultiStepFetchResult(
            False, url, last_status, b"", "application/json",
            f"Tickertape FII query unusable HTTP {last_status}",
        )
    body = json.dumps({"results": results, "source": "tickertape"}, ensure_ascii=False).encode("utf-8")
    return MultiStepFetchResult(True, url, last_status or 200, body, "application/json", None)


def fetch_dhan_fii_holding_change() -> MultiStepFetchResult:
    """POST Dhan public customscan for FII holding-change percent."""
    url = "https://ow-scanx-analytics.dhan.co/customscan/fetchdt"
    session = _session({
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://dhan.co",
        "Referer": "https://dhan.co/stocks/market/fii-buying-stocks/",
    })
    rows: list[Any] = []
    last_status = 0
    fields = [
        "Isin", "DispSym", "Sym", "Ltp", "Mcap", "Pe", "FIIHLDChagPer",
    ]
    for pgno in range(1, 5):
        payload = {
            "data": {
                "sort": "Mcap",
                "sorder": "desc",
                "count": 50,
                "params": [
                    {"field": "FIIHLDChagPer", "op": "gte", "val": "3"},
                    {"field": "Seg", "op": "", "val": "E"},
                    {"field": "OgInst", "op": "", "val": "ES"},
                ],
                "fields": fields,
                "pgno": pgno,
            }
        }
        try:
            response = session.post(url, json=payload, timeout=TIMEOUT)
        except requests.RequestException as exc:
            return MultiStepFetchResult(False, url, 0, b"", "application/json", str(exc))
        last_status = response.status_code
        if response.status_code != 200:
            break
        try:
            js = response.json()
        except ValueError:
            return MultiStepFetchResult(False, url, last_status, b"", "application/json", "Dhan JSON invalid")
        chunk = js.get("data") or []
        if not isinstance(chunk, list) or not chunk:
            break
        rows.extend(chunk)
        if pgno >= int(js.get("tot_pg") or 1):
            break
    if not rows:
        return MultiStepFetchResult(
            False, url, last_status, b"", "application/json",
            f"Dhan FII scan unusable HTTP {last_status}",
        )
    body = json.dumps({"data": rows, "source": "dhan"}, ensure_ascii=False).encode("utf-8")
    return MultiStepFetchResult(True, url, last_status or 200, body, "application/json", None)


def fetch_equitymaster_fii_buys_reference() -> MultiStepFetchResult:
    """GET Equitymaster institutional-buy HTML. Cloudflare may fail closed."""
    url = (
        "https://www.equitymaster.com/stock-screener/"
        "stocks-recently-bought-by-institutional-investors"
    )
    session = _session({
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://www.equitymaster.com/",
    })
    try:
        response = session.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return MultiStepFetchResult(False, url, 0, b"", "text/html", str(exc))
    body = response.content or b""
    html = body.decode("utf-8", errors="replace")
    ok = (
        response.status_code == 200
        and "<table" in html.casefold()
        and "Just a moment" not in html
        and "cf-challenge" not in html.casefold()
    )
    return MultiStepFetchResult(
        ok,
        response.url,
        response.status_code,
        body if ok else b"",
        response.headers.get("content-type", "text/html"),
        None if ok else f"Equitymaster HTML unusable HTTP {response.status_code}",
    )
