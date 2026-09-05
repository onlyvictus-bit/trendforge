"""Parse DGCIS TradeStat HTML tables into flat commodity import rows."""

from __future__ import annotations

import re
from typing import Any

from .common import decode_bytes, extract_data_date, source_result


def parse_dgcis_trade_html(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    tables = re.findall(r"<table[^>]*>(.*?)</table>", text, flags=re.I | re.S)
    records: list[dict[str, Any]] = []
    for tb in tables:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tb, flags=re.I | re.S)
        grid: list[list[str]] = []
        for tr in rows:
            cells = [
                re.sub(r"<[^>]+>", "", c).strip()
                for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.I | re.S)
            ]
            cells = [c for c in cells if c]
            if cells:
                grid.append(cells)
        if len(grid) < 2:
            continue
        header = grid[0]
        for data in grid[1:]:
            if len(data) < 2:
                continue
            rec = {f"col_{i}": data[i] if i < len(data) else "" for i in range(len(header))}
            # Prefer first text column as name
            rec["name"] = data[0]
            rec["symbol"] = re.sub(r"[^A-Z0-9]+", "_", data[0].upper())[:32] or "DGCIS"
            for i, h in enumerate(header):
                key = re.sub(r"[^a-z0-9]+", "_", h.lower()).strip("_") or f"c{i}"
                if i < len(data):
                    rec[key] = data[i]
            records.append(rec)

    if not records:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="DGCIS HTML had no parseable table rows",
            output={"dateSource": date_source, "rows": []},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(records),
        summary=f"DGCIS table rows={len(records)}",
        output={"dateSource": date_source, "rows": records, "records": records},
    )
