"""Pure parsers for the three official non-Upstox replacement sources.

The BSE parsers intentionally normalize filing indexes only.  Linked inline
XBRL documents are a second-stage acquisition concern and are never fetched by
these pure parsers.  Every record is informational and cannot vote or score.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

from .common import parse_date_value, source_result


BSE_BASE = "https://www.bseindia.com"
ZERO_SCORE = {
    "scoreEligible": False,
    "voteEligible": False,
    "canUnlockReady": False,
    "sourceTrust": "OFFICIAL",
}


def _json_table(content: bytes) -> tuple[list[dict[str, Any]] | None, str | None]:
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict) or not isinstance(payload.get("Table"), list):
        return None, "missing BSE Table array"
    return [row for row in payload["Table"] if isinstance(row, dict)], None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    parsed = parse_date_value(text)
    if parsed:
        return parsed
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    for pattern in (
        "%b %d %Y %I:%M%p",
        "%B %d %Y %I:%M%p",
        "%b %d %Y %H:%M",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b-%d-%Y",
        "%B-%d-%Y",
    ):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _bse_url(value: Any) -> str | None:
    path = _text(value)
    if not path:
        return None
    if not urlparse(path).scheme and not path.lstrip("/").casefold().startswith(
        "xbrlfiles/"
    ):
        path = f"XBRLFILES/{path.lstrip('/')}"
    url = urljoin(BSE_BASE + "/", path)
    return url if re.search(r"\.(?:xml|html?)(?:$|\?)", url, re.I) else None


def _detail_preference(url: str) -> tuple[int, str]:
    # BSE inline-XBRL HTML is often the accessible representation while the
    # paired XML path can be absent.  Preserve deterministic fallback order.
    return (0 if re.search(r"\.html?(?:$|\?)", url, re.I) else 1, url)


def parse_bse_financial_results_index(
    content: bytes, **_kwargs: Any
) -> dict[str, Any]:
    rows, error = _json_table(content)
    if rows is None:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="BSE financial-results response is not the official Table schema.",
            output={"rows": [], "recordsScope": "FILING_INDEX_XBRL_DISCOVERY"},
            error=error,
        )
    if not rows:
        return source_result(
            parser_state="PARSED_STRUCTURED",
            data_date=None,
            record_count=0,
            summary="BSE financial-results index is valid but currently empty.",
            output={"rows": [], "recordsScope": "FILING_INDEX_XBRL_DISCOVERY"},
        )

    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    candidates: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    invalid = 0
    for raw in rows:
        scrip = _text(raw.get("Scrip_cd") or raw.get("scrip_cd"))
        company = _text(raw.get("company_name") or raw.get("scrip_name"))
        symbol = _text(raw.get("scrip_name")).upper()
        quarter_code = _text(raw.get("quarter_code") or raw.get("qtr"))
        nature = _text(raw.get("Fld_NatureOfReport") or raw.get("audited"))
        filed_at = _text(raw.get("DT_TM") or raw.get("Fld_CreateDate"))
        filing_date = _date(filed_at)
        urls = {
            url
            for value in (
                raw.get("XMLName"),
                raw.get("Consol_XMLName"),
                raw.get("URL"),
            )
            if (url := _bse_url(value)) is not None
        }
        if not scrip or not company or not quarter_code or not filing_date or not urls:
            invalid += 1
            continue
        key = (scrip, quarter_code, nature.upper())
        candidates[key].update(urls)
        current = grouped.get(key)
        if current is None or filed_at > current["filedAt"]:
            grouped[key] = {
                "scripCode": scrip,
                "symbol": symbol or None,
                "company": company,
                "industry": _text(raw.get("Industry_name")) or None,
                "quarterCode": quarter_code,
                "reportNature": nature or None,
                "filingStatus": _text(raw.get("Status")) or None,
                "filedAt": filed_at,
                "filingDate": filing_date,
                "recordsScope": "FILING_INDEX_XBRL_DISCOVERY",
                **ZERO_SCORE,
            }

    normalized: list[dict[str, Any]] = []
    for key, row in grouped.items():
        detail_candidates = sorted(candidates[key], key=_detail_preference)
        normalized.append(
            {
                **row,
                "detailUrl": detail_candidates[0],
                "detailCandidates": detail_candidates,
            }
        )
    normalized.sort(
        key=lambda row: (row["filingDate"], row["filedAt"], row["scripCode"]),
        reverse=True,
    )
    if not normalized:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="BSE financial-results index contained no dated XBRL filing rows.",
            output={
                "rows": [],
                "sourceRowCount": len(rows),
                "invalidRowCount": invalid,
                "recordsScope": "FILING_INDEX_XBRL_DISCOVERY",
            },
            error="zero dated XBRL filing rows",
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(row["filingDate"] for row in normalized),
        record_count=len(normalized),
        summary=f"Parsed {len(normalized)} official BSE financial XBRL filing-index rows.",
        output={
            "rows": normalized,
            "records": normalized,
            "sourceRowCount": len(rows),
            "normalizedRowCount": len(normalized),
            "invalidRowCount": invalid,
            "recordsScope": "FILING_INDEX_XBRL_DISCOVERY",
            "parserVersion": "1.0.0",
            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
        },
    )


def parse_bse_shareholding_index(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    rows, error = _json_table(content)
    if rows is None:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="BSE shareholding response is not the official Table schema.",
            output={"rows": [], "recordsScope": "FILING_INDEX_XBRL_DISCOVERY"},
            error=error,
        )
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    invalid = 0
    for raw in rows:
        scrip = _text(raw.get("FLD_ScripCode") or raw.get("scripcode"))
        company = _text(raw.get("Company_NAme") or raw.get("company_name"))
        broadcast_at = _text(raw.get("broadcastTime") or raw.get("D"))
        filing_date = _date(broadcast_at)
        quarter_end = _date(raw.get("EndDate") or raw.get("sQtrName"))
        detail_url = _bse_url(raw.get("XBRLAttachment"))
        quarter_id_status = _text(raw.get("nqtrid"))
        if not scrip or not company or not filing_date or not quarter_end or not detail_url:
            invalid += 1
            continue
        identity = (scrip, quarter_end, detail_url)
        if identity in seen:
            continue
        seen.add(identity)
        status_match = re.search(r"(?:^|&)Flag=([^&]+)", quarter_id_status, re.I)
        normalized.append(
            {
                "scripCode": scrip,
                "company": company,
                "industry": _text(raw.get("industry_name")) or None,
                "quarterName": _text(raw.get("sQtrName")) or None,
                "quarterEnd": quarter_end,
                "quarterId": quarter_id_status.split("&", 1)[0] or None,
                "filingStatus": status_match.group(1) if status_match else None,
                "filedAt": broadcast_at,
                "filingDate": filing_date,
                "isXbrl": _text(raw.get("IsXBRL")).upper() in {"Y", "YES", "1", "TRUE"},
                "detailUrl": detail_url,
                "recordsScope": "FILING_INDEX_XBRL_DISCOVERY",
                **ZERO_SCORE,
            }
        )
    normalized.sort(
        key=lambda row: (row["filingDate"], row["filedAt"], row["scripCode"]),
        reverse=True,
    )
    if rows and not normalized:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="BSE shareholding index contained no dated XBRL filing rows.",
            output={
                "rows": [],
                "sourceRowCount": len(rows),
                "invalidRowCount": invalid,
                "recordsScope": "FILING_INDEX_XBRL_DISCOVERY",
            },
            error="zero dated XBRL filing rows",
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max((row["filingDate"] for row in normalized), default=None),
        record_count=len(normalized),
        summary=f"Parsed {len(normalized)} official BSE shareholding filing-index rows.",
        output={
            "rows": normalized,
            "records": normalized,
            "sourceRowCount": len(rows),
            "normalizedRowCount": len(normalized),
            "invalidRowCount": invalid,
            "recordsScope": "FILING_INDEX_XBRL_DISCOVERY",
            "parserVersion": "1.0.0",
            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
        },
    )


class _TableRows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "tr":
            self._row = []
        elif tag.lower() in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"td", "th"} and self._cell is not None:
            text = re.sub(r"\s+", " ", unescape("".join(self._cell))).strip()
            if self._row is not None:
                self._row.append(text)
            self._cell = None
        elif tag.lower() == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = None


def _numbers(cells: list[str]) -> list[float]:
    output: list[float] = []
    for cell in cells:
        match = re.search(r"-?\d+(?:\.\d+)?", cell.replace(",", ""))
        if match:
            output.append(float(match.group(0)))
    return output


def _paired_values(cells: list[str]) -> tuple[list[float], list[float]]:
    pairs: list[tuple[float, float]] = []
    for cell in cells:
        values = [
            float(value)
            for value in re.findall(r"-?\d+(?:\.\d+)?", cell.replace(",", ""))
        ]
        if len(values) >= 2:
            pairs.append((values[-2], values[-1]))
    if len(pairs) < 3:
        return [], []
    selected = pairs[-3:]
    return [pair[0] for pair in selected], [pair[1] for pair in selected]


def parse_rbi_tbill_yield(content: bytes, **_kwargs: Any) -> dict[str, Any]:
    try:
        html = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        html = content.decode("cp1252", errors="replace")
    if "Treasury Bills: Full Auction Result" not in html:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="RBI response is not a Treasury Bills full auction result.",
            output={"rows": []},
            error="missing auction title",
        )
    date_match = re.search(
        r"Date\s*:\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", html, re.I
    )
    generic_date = re.search(
        r"([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", html, re.I
    )
    raw_date = date_match.group(1) if date_match else generic_date.group(1) if generic_date else ""
    normalized_date = re.sub(r"[\s,]+", "-", raw_date).strip("-")
    data_date = _date(normalized_date)
    parser = _TableRows()
    parser.feed(html)
    cutoff_price: list[float] = []
    cutoff_yield: list[float] = []
    weighted_price: list[float] = []
    weighted_yield: list[float] = []
    expect: str | None = None
    for cells in parser.rows:
        joined = " ".join(cells)
        values = _numbers(cells)
        if "Cut-off price" in joined:
            paired_price, paired_yield = _paired_values(cells)
            cutoff_price = paired_price or values[-3:]
            cutoff_yield = paired_yield
            expect = None if paired_yield else "cutoff_yield"
            continue
        if expect == "cutoff_yield" and "YTM" in joined:
            cutoff_yield = values[-3:]
            expect = None
            continue
        if "Weighted Average Price" in joined:
            paired_price, paired_yield = _paired_values(cells)
            weighted_price = paired_price or values[-3:]
            weighted_yield = paired_yield
            expect = None if paired_yield else "weighted_yield"
            continue
        if expect == "weighted_yield" and "WAY" in joined:
            weighted_yield = values[-3:]
            expect = None

    valid = (
        data_date is not None
        and all(len(values) == 3 for values in (cutoff_price, cutoff_yield, weighted_price, weighted_yield))
        and all(0 < value < 100 for value in cutoff_price + weighted_price)
        and all(0 < value < 25 for value in cutoff_yield + weighted_yield)
    )
    if not valid:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="RBI auction page lacks one complete, plausible 91/182/364-day result set.",
            output={"rows": []},
            error="incomplete or implausible auction table",
        )
    rows = []
    for index, tenor in enumerate((91, 182, 364)):
        rows.append(
            {
                "dataDate": data_date,
                "tenorDays": tenor,
                "cutoffPrice": cutoff_price[index],
                "cutoffYtmPct": cutoff_yield[index],
                "weightedAveragePrice": weighted_price[index],
                "weightedAverageYtmPct": weighted_yield[index],
                "annualRateDecimal": round(cutoff_yield[index] / 100, 8),
                "rateConvention": "ANNUAL_YTM_PERCENT",
                "recordsScope": "LATEST_FULL_AUCTION_RESULT",
                "sourceTrust": "OFFICIAL_RBI",
                "scoreEligible": False,
                "voteEligible": False,
                "canUnlockReady": False,
            }
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=3,
        summary="Parsed official RBI 91/182/364-day Treasury-bill auction yields.",
        output={
            "rows": rows,
            "records": rows,
            "sourceRowCount": 3,
            "normalizedRowCount": 3,
            "parserVersion": "1.0.0",
            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
        },
    )
