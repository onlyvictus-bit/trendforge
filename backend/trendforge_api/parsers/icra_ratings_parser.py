"""Pure parser for ICRA's official rating-rationales HTML fragment."""
from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from .common import parse_date_value, source_result


class _Rows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[dict[str, Any]]] = []
        self._row: list[dict[str, Any]] | None = None
        self._cell: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = {"text": [], "links": []}
        elif tag == "a" and self._cell is not None:
            href = dict(attrs).get("href")
            if href:
                self._cell["links"].append(href)

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._cell["text"] = " ".join("".join(self._cell["text"]).split())
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def _date(value: Any) -> str | None:
    parsed = parse_date_value(value)
    if parsed:
        return parsed
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _action(title: str) -> str:
    value = title.casefold()
    if "upgrad" in value and "assign" in value:
        return "RATING_UPGRADED_AND_ASSIGNED"
    if "downgrad" in value:
        return "RATING_DOWNGRADED"
    if "upgrad" in value:
        return "RATING_UPGRADED"
    if "reaffirm" in value and "assign" in value:
        return "RATING_REAFFIRMED_AND_ASSIGNED"
    if "reaffirm" in value:
        return "RATING_REAFFIRMED"
    if "withdraw" in value:
        return "RATING_WITHDRAWN"
    if "assign" in value:
        return "RATING_ASSIGNED"
    return "OTHER_DISCLOSED_RATING_ACTION"


def parse_icra_ratings(content: bytes, *, url: str | None = None, last_modified: str | None = None, **_kwargs: Any) -> dict[str, Any]:
    text = content.decode("utf-8", errors="replace")
    if "<tr" not in text.casefold() or "sector" not in text.casefold():
        return source_result(parser_state="WAIT_SCHEMA_MISMATCH", data_date=None, record_count=0, summary="ICRA response is not the rating-rationales table.", output={"rows": [], "scope": "STOCK_LEVEL_INFORMATIONAL"}, error="missing table schema")
    parser = _Rows()
    parser.feed(text)
    reference = _date(last_modified)
    rows: list[dict[str, Any]] = []
    invalid = 0
    seen: set[tuple[str, str]] = set()
    for position, cells in enumerate(parser.rows, start=1):
        if len(cells) < 3 or str(cells[0]["text"]).casefold() == "date":
            continue
        publication_date = _date(cells[0]["text"])
        title = str(cells[2]["text"] or "").strip()
        if not publication_date or not title:
            invalid += 1
            continue
        if reference and publication_date > reference:
            invalid += 1
            continue
        links = [link for cell in cells for link in cell["links"]]
        rationale = next((x for x in links if "ShowRationaleReport" in x), "")
        identity = (publication_date, rationale or title)
        if identity in seen:
            continue
        seen.add(identity)
        company = title.split(":", 1)[0].strip()
        facility = next((x for x in links if "BankFacilities" in x), "")
        pdf = next((x for x in links if "GetRationalReportFilePdf" in x), "")
        rows.append({
            "symbol": None, "mappingState": "UNMAPPED_NO_FUZZY_TICKER_MATCH",
            "companyName": company, "sector": str(cells[1]["text"] or "").strip() or None,
            "heading": title, "ratingAction": _action(title), "publicationDate": publication_date,
            "rationaleUrl": urljoin("https://www.icra.in", rationale) if rationale else None,
            "facilityUrl": urljoin("https://www.icra.in", facility) if facility else None,
            "pdfUrl": urljoin("https://www.icra.in", pdf) if pdf else None,
            "sourceRow": position, "sourceUrl": url, "sourceTrust": "OFFICIAL",
            "scope": "STOCK_LEVEL_INFORMATIONAL", "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
        })
    if not rows:
        state = "WAIT_SCHEMA_MISMATCH" if invalid else "WAIT_EMPTY_PARSE"
        return source_result(parser_state=state, data_date=None, record_count=0, summary="ICRA returned no valid dated rating rows.", output={"rows": [], "sourceRowCount": max(0, len(parser.rows)-1), "scope": "STOCK_LEVEL_INFORMATIONAL"}, error="no valid rows")
    data_date = max(row["publicationDate"] for row in rows)
    return source_result(parser_state="PARSED_STRUCTURED", data_date=data_date, record_count=len(rows), summary=f"Parsed {len(rows)} official ICRA rating rationales.", output={"rows": rows, "records": rows, "sourceRowCount": max(0, len(parser.rows)-1), "normalizedRowCount": len(rows), "invalidRowCount": invalid, "unmappedCompanyCount": len(rows), "parserVersion": "1.0.0", "sourceTrust": "OFFICIAL", "scope": "STOCK_LEVEL_INFORMATIONAL", "scoreAuthority": "ZERO_SCORE_INFORMATIONAL", "symbolMappingPolicy": "NO_FUZZY_TICKER_MATCH"})
