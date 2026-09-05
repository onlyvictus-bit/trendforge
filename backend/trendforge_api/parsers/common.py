from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from datetime import UTC, date, datetime, timedelta
from typing import Any


def decode_bytes(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("latin-1", errors="replace")


def normalize_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def compact_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def parse_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text or text.lower() in {"nan", "none", "-"}:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def parse_int(value: Any, default: int = 0) -> int:
    return int(round(parse_float(value, float(default))))


def parse_date_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)) and 1 <= float(value) <= 2_958_465:
        try:
            return (datetime(1899, 12, 30) + timedelta(days=float(value))).date().isoformat()
        except (OverflowError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    dotnet = re.search(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/", text)
    if dotnet:
        try:
            return datetime.fromtimestamp(
                int(dotnet.group(1)) / 1000, tz=UTC
            ).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    text = text.replace("/", "-")
    patterns = (
        ("%d-%b-%Y %H:%M:%S%z", r"\d{1,2}-[A-Za-z]{3}-\d{4}\s+\d{1,2}:\d{2}:\d{2}[+-]\d{2}:?\d{2}"),
        ("%d-%b-%Y %H:%M:%S", r"\d{1,2}-[A-Za-z]{3}-\d{4}\s+\d{1,2}:\d{2}:\d{2}"),
        ("%Y-%m-%d", r"\d{4}-\d{1,2}-\d{1,2}"),
        ("%d-%m-%Y", r"\d{1,2}-\d{1,2}-\d{4}"),
        ("%d-%b-%Y", r"\d{1,2}-[A-Za-z]{3}-\d{4}"),
        ("%d-%B-%Y", r"\d{1,2}-[A-Za-z]+-\d{4}"),
        ("%d %b %Y", r"\d{1,2}\s+[A-Za-z]{3}\s+\d{4}"),
        ("%d %B %Y", r"\d{1,2}\s+[A-Za-z]+\s+\d{4}"),
        ("%Y%m%d", r"\d{8}"),
    )
    for fmt, pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            return datetime.strptime(match.group(0), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def extract_data_date(
    text: str, url: str | None = None, last_modified: str | None = None
) -> tuple[str | None, str]:
    labelled = re.search(
        r"(?:report|trade|business|bhavcopy|data|as\s+on|date)\s*(?:date)?\s*[:\-]\s*([0-9]{1,4}[-/][0-9A-Za-z]{1,9}[-/][0-9]{2,4})",
        text,
        re.IGNORECASE,
    )
    if labelled:
        parsed = parse_date_value(labelled.group(1))
        if parsed:
            return parsed, "content_label"
    parsed = parse_date_value(text[:5000])
    if parsed:
        return parsed, "content"
    if url:
        parsed = parse_date_value(url)
        if parsed:
            return parsed, "url"
    if last_modified:
        try:
            return datetime.strptime(
                last_modified[:29], "%a, %d %b %Y %H:%M:%S %Z"
            ).date().isoformat(), "last_modified"
        except ValueError:
            parsed = parse_date_value(last_modified)
            if parsed:
                return parsed, "last_modified"
    return None, "missing"


def csv_rows_from_text(text: str) -> list[dict[str, str]]:
    lines = [line.strip("\ufeff ") for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    first_line = lines[0].lower()
    if any(
        token in first_line
        for token in ("report_date", "report date", "trade_date", "symbol,")
    ):
        fast_rows = _csv_rows_from_offset(lines, 0)
        if fast_rows:
            return fast_rows
    candidates: list[list[dict[str, str]]] = []
    for start in range(min(20, len(lines))):
        rows = _csv_rows_from_offset(lines, start)
        if rows:
            candidates.append(rows)
    if not candidates:
        return []
    return max(candidates, key=len)


def _csv_rows_from_offset(lines: list[str], start: int) -> list[dict[str, str]]:
    block = "\n".join(lines[start:])
    try:
        sample = "\n".join(lines[start : start + 5])
        dialect = csv.Sniffer().sniff(sample, delimiters=",|\t;")
    except csv.Error:
        dialect = csv.excel
    try:
        reader = csv.DictReader(io.StringIO(block), dialect=dialect)
        if not reader.fieldnames:
            return []
        field_score = sum(
            1 for name in reader.fieldnames if name and re.search(r"[A-Za-z]", name)
        )
        if field_score < 2:
            return []
        rows = []
        for row in reader:
            clean = {
                normalize_name(key): (value or "").strip()
                for key, value in row.items()
                if key
            }
            if any(value for value in clean.values()):
                rows.append(clean)
        return rows
    except csv.Error:
        return []


def rows_from_content(content: bytes) -> tuple[list[dict[str, str]], str]:
    text = decode_bytes(content)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        for key in ("data", "rows", "results", "records", "table", "Table"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if isinstance(payload, list):
        rows: list[dict[str, str]] = []
        for raw in payload:
            if not isinstance(raw, dict):
                continue
            row = {
                normalize_name(key): (
                    ""
                    if value is None
                    else json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (dict, list))
                    else str(value).strip()
                )
                for key, value in raw.items()
            }
            if any(row.values()):
                rows.append(row)
        return rows, "json"
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            if "[Content_Types].xml" in names and any(
                name.startswith("xl/") for name in names
            ):
                return _excel_rows(content)
            best_rows: list[dict[str, str]] = []
            best_name = ""
            for name in names:
                if not name.lower().endswith((".csv", ".txt")):
                    continue
                rows = csv_rows_from_text(decode_bytes(archive.read(name)))
                if len(rows) > len(best_rows):
                    best_rows = rows
                    best_name = name
            return best_rows, best_name or "zip"
    return csv_rows_from_text(text), "text"


def _excel_rows(content: bytes) -> tuple[list[dict[str, str]], str]:
    try:
        import pandas as pd

        sheets = pd.read_excel(
            io.BytesIO(content), sheet_name=None, header=None, dtype=str
        )
    except Exception:
        return [], "excel_unreadable"

    best_rows: list[dict[str, str]] = []
    best_sheet = "excel"
    for sheet_name, frame in sheets.items():
        if frame.empty:
            continue
        for header_index in range(min(30, len(frame))):
            header_values = [
                str(value).strip() if not pd.isna(value) else ""
                for value in frame.iloc[header_index].tolist()
            ]
            normalized = [normalize_name(value) for value in header_values]
            if len({value for value in normalized if value}) < 2:
                continue
            rows: list[dict[str, str]] = []
            for _, raw_row in frame.iloc[header_index + 1 :].iterrows():
                item: dict[str, str] = {}
                for column_index, key in enumerate(normalized):
                    if not key or key in item:
                        continue
                    value = (
                        raw_row.iloc[column_index]
                        if column_index < len(raw_row)
                        else ""
                    )
                    item[key] = "" if pd.isna(value) else str(value).strip()
                if any(item.values()):
                    rows.append(item)
            if len(rows) > len(best_rows):
                best_rows = rows
                best_sheet = f"excel:{sheet_name}:header={header_index + 1}"
    return best_rows, best_sheet


def find_value(row: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    """Map a logical field onto a row.

    Exact compact-key match wins. Substring match is a fallback only, and
    prefers the shortest matching column so ``opn_intrst`` is not stolen by
    ``chng_in_opn_intrst``. Empty aliases (for example ``%``) are ignored.
    """

    compact_items = [(compact_key(key), value) for key, value in row.items() if key]
    compact_candidates = [compact_key(item) for item in candidates if compact_key(item)]
    for candidate in compact_candidates:
        for ckey, value in compact_items:
            if ckey == candidate:
                return value
    for candidate in sorted(set(compact_candidates), key=len, reverse=True):
        if len(candidate) < 4:
            continue
        matches = [(ckey, value) for ckey, value in compact_items if candidate in ckey]
        if matches:
            matches.sort(key=lambda item: (len(item[0]), item[0]))
            return matches[0][1]
    return None


def source_result(
    *,
    parser_state: str,
    data_date: str | None,
    record_count: int,
    summary: str,
    output: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "parser_state": parser_state,
        "data_date": data_date,
        "record_count": record_count,
        "summary": summary,
        "output": output or {},
        "error": error,
    }


def today_iso() -> str:
    return date.today().isoformat()
