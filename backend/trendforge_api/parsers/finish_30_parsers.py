"""Parsers for remaining 30-pack sources (finish set)."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any

from .common import decode_bytes, extract_data_date, source_result

_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9&.\-]{0,30}$")


def _json_payload(content: bytes) -> Any:
    return json.loads(decode_bytes(content))


def parse_yahoo_chart(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    try:
        payload = _json_payload(content)
    except Exception as exc:  # noqa: BLE001
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary=f"Yahoo chart not JSON: {exc}",
            output={"rows": []},
            error=str(exc),
        )
    # Multi-symbol batch from phase3_multi_step_fetch.fetch_yahoo_symbols
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        rows = [r for r in payload["records"] if isinstance(r, dict)]
        if rows:
            return source_result(
                parser_state="PARSED_STRUCTURED",
                data_date=data_date,
                record_count=len(rows),
                summary=f"Yahoo batch rows={len(rows)}",
                output={"dateSource": date_source, "rows": rows, "records": rows},
            )
    try:
        result = payload["chart"]["result"][0]
        q = result["indicators"]["quote"][0]
        ts = result.get("timestamp") or []
        meta = result.get("meta") or {}
        symbol = str(meta.get("symbol") or "").upper() or "YAHOO"
        rows = []
        for i, t in enumerate(ts):
            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": t,
                    "open": (q.get("open") or [None])[i] if i < len(q.get("open") or []) else None,
                    "high": (q.get("high") or [None])[i] if i < len(q.get("high") or []) else None,
                    "low": (q.get("low") or [None])[i] if i < len(q.get("low") or []) else None,
                    "close": (q.get("close") or [None])[i] if i < len(q.get("close") or []) else None,
                    "volume": (q.get("volume") or [None])[i] if i < len(q.get("volume") or []) else None,
                }
            )
        rows = [r for r in rows if r.get("close") is not None]
    except Exception as exc:  # noqa: BLE001
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary=f"Yahoo chart shape mismatch: {exc}",
            output={"rows": []},
            error=str(exc),
        )
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="Yahoo chart empty bars",
            output={"rows": []},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Yahoo {rows[0]['symbol']} bars={len(rows)}",
        output={"dateSource": date_source, "rows": rows, "records": rows},
    )


def parse_mcx_json_watch(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    try:
        payload = _json_payload(content)
    except Exception as exc:  # noqa: BLE001
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary=f"MCX JSON invalid: {exc}",
            output={"rows": []},
            error=str(exc),
        )
    # Yahoo research proxy batch used when MCX WAF blocks the collector IP
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        y_rows = [r for r in payload["records"] if isinstance(r, dict) and r.get("symbol")]
        if y_rows:
            for r in y_rows:
                r.setdefault("proxySource", "yahoo_when_mcx_blocked")
            return source_result(
                parser_state="PARSED_STRUCTURED",
                data_date=data_date,
                record_count=len(y_rows),
                summary=f"MCX proxy yahoo rows={len(y_rows)}",
                output={
                    "dateSource": date_source,
                    "rows": y_rows,
                    "records": y_rows,
                    "proxySource": "yahoo_when_mcx_blocked",
                },
            )
    # ASP.NET often wraps as {d: "..."} or {d: {...}}
    if isinstance(payload, dict) and "d" in payload:
        inner = payload["d"]
        if isinstance(inner, str):
            try:
                payload = json.loads(inner)
            except Exception:
                payload = {"raw": inner}
        else:
            payload = inner

    rows: list[dict[str, Any]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, list):
            for item in obj:
                walk(item)
            return
        if not isinstance(obj, dict):
            return
        # leaf-ish market row
        sym = (
            obj.get("Symbol")
            or obj.get("symbol")
            or obj.get("Commodity")
            or obj.get("commodity")
            or obj.get("InstrumentName")
        )
        if sym and any(k in obj for k in ("LTP", "LastPrice", "Close", "close", "OI", "OpenInterest", "Volume")):
            rec = dict(obj)
            rec["symbol"] = str(sym).strip().upper().replace(" ", "")
            rows.append(rec)
            return
        for v in obj.values():
            if isinstance(v, (list, dict)):
                walk(v)

    walk(payload)
    if not rows and isinstance(payload, dict):
        # single quote object
        if payload:
            rows.append({**payload, "symbol": str(payload.get("Symbol") or "MCX").upper()})

    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="MCX watch/chain empty after unwrap",
            output={"dateSource": date_source, "rows": [], "rawKeys": list(payload)[:20] if isinstance(payload, dict) else []},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"MCX rows={len(rows)}",
        output={"dateSource": date_source, "rows": rows, "records": rows},
    )


def parse_amfi_portfolio_directory(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    # The Next.js page embeds the AMC disclosure directory as escaped JSON.
    # Generic <a> extraction captured social-media links and falsely presented
    # them as holdings. Only the explicit monthly-disclosure field is accepted.
    normalized = text.replace('\\"', '"').replace("\\u0026", "&")
    matches = re.finditer(
        r'"mf_id":"(?P<id>\d+)".{0,5000}?'
        r'"mf_name":"(?P<mf>.*?)".{0,5000}?'
        r'"amc_name":"(?P<amc>.*?)".{0,5000}?'
        r'"amc_monthly_portfolio_disclosure":"(?P<url>.*?)"',
        normalized,
        flags=re.I | re.S,
    )
    rows = []
    for match in matches:
        disclosure_url = match.group("url").strip()
        if not disclosure_url.startswith(("https://", "http://")):
            continue
        rows.append(
            {
                "mfId": int(match.group("id")),
                "mfName": match.group("mf").strip(),
                "amcName": match.group("amc").strip(),
                "monthlyPortfolioDisclosureUrl": disclosure_url,
                "recordType": "AMC_MONTHLY_PORTFOLIO_DISCLOSURE_DIRECTORY",
                "isHoldingsData": False,
            }
        )
    seen: set[str] = set()
    uniq = []
    for row in rows:
        if row["monthlyPortfolioDisclosureUrl"] in seen:
            continue
        seen.add(row["monthlyPortfolioDisclosureUrl"])
        uniq.append(row)
    if not uniq:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="AMFI portfolio page had no explicit monthly disclosure URLs.",
            output={"rows": [], "isHoldingsData": False},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(uniq),
        summary=f"Parsed {len(uniq)} AMFI AMC monthly disclosure directory rows.",
        output={
            "dateSource": date_source,
            "rows": uniq,
            "records": uniq,
            "isHoldingsData": False,
            "warning": "Directory URLs only; stock holdings require the linked workbook parser.",
        },
    )


def parse_nse_trade_info(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    try:
        payload = _json_payload(content)
    except Exception as exc:  # noqa: BLE001
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary=f"trade_info not JSON: {exc}",
            output={"rows": []},
            error=str(exc),
        )
    if not isinstance(payload, dict):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary="trade_info root not object",
            output={"rows": []},
        )
    # typical quote-equity trade_info sections
    info = payload.get("marketDeptOrderBook") or payload.get("securityWiseDP") or payload
    symbol = None
    if url and "symbol=" in url:
        m = re.search(r"symbol=([^&]+)", url)
        if m:
            symbol = urllib_unquote(m.group(1)).upper()
    rec = dict(info) if isinstance(info, dict) else {"raw": info}
    if symbol:
        rec["symbol"] = symbol
    # flatten nested delivery
    if isinstance(payload.get("securityWiseDP"), dict):
        rec.update({f"dp_{k}": v for k, v in payload["securityWiseDP"].items()})
        if not rec.get("symbol"):
            rec["symbol"] = symbol or "UNKNOWN"
    rows = [rec] if rec.get("symbol") else []
    # also accept bulk arrays
    if isinstance(payload.get("data"), list):
        for item in payload["data"]:
            if isinstance(item, dict):
                s = item.get("symbol") or symbol
                if s:
                    rows.append({**item, "symbol": str(s).upper()})
    if not rows:
        rows = [{**rec, "symbol": symbol or "UNKNOWN"}]
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"trade_info rows={len(rows)}",
        output={"dateSource": date_source, "rows": rows, "records": rows},
    )


def urllib_unquote(value: str) -> str:
    from urllib.parse import unquote

    return unquote(value)


def parse_nse_bulk_deals_csv(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader or []:
        if not row:
            continue
        rec = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
        sym = rec.get("Symbol") or rec.get("symbol") or rec.get("SYMBOL")
        if sym:
            rec["symbol"] = str(sym).upper()
            rows.append(rec)
    if not rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="bulk deals CSV empty",
            output={"rows": []},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"bulk deals rows={len(rows)}",
        output={"dateSource": date_source, "rows": rows, "records": rows},
    )


def parse_nse_bulk_deal_symbol_json(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    try:
        payload = _json_payload(content)
    except Exception as exc:  # noqa: BLE001
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary=str(exc),
            output={"rows": []},
            error=str(exc),
        )
    rows = []
    if isinstance(payload, dict):
        for key in ("data", "BULK_DEALS_DATA", "bulk_deals", "records"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
        if not rows and payload:
            rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    out = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        rec = dict(item)
        sym = rec.get("symbol") or rec.get("Symbol")
        if sym:
            rec["symbol"] = str(sym).upper()
        out.append(rec)
    if not out:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="bulk deal symbol archive empty",
            output={"rows": []},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(out),
        summary=f"bulk deal symbol rows={len(out)}",
        output={"dateSource": date_source, "rows": out, "records": out},
    )


def parse_generic_table_or_json(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """NCDEX / warehouse / top participants fallback: JSON or HTML tables or XLSX zip."""
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    # xlsx
    if content[:2] == b"PK":
        try:
            import zipfile
            import xml.etree.ElementTree as ET

            rows = []
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                shared = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                    for si in root.findall(".//m:si", ns):
                        shared.append("".join(t.text or "" for t in si.findall(".//m:t", ns)))
                sheet_name = next((n for n in zf.namelist() if n.startswith("xl/worksheets/sheet")), None)
                if sheet_name:
                    root = ET.fromstring(zf.read(sheet_name))
                    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                    for i, row in enumerate(root.findall(".//m:sheetData/m:row", ns)):
                        vals = []
                        for c in row.findall("m:c", ns):
                            t = c.attrib.get("t")
                            v = c.find("m:v", ns)
                            raw = v.text if v is not None else ""
                            if t == "s" and raw.isdigit() and int(raw) < len(shared):
                                vals.append(shared[int(raw)])
                            else:
                                vals.append(raw or "")
                        if any(vals):
                            rec = {f"c{j}": vals[j] for j in range(len(vals))}
                            rec["symbol"] = re.sub(r"[^A-Z0-9]+", "_", str(vals[0]).upper())[:24] or f"R{i}"
                            rows.append(rec)
            if rows:
                return source_result(
                    parser_state="PARSED_STRUCTURED",
                    data_date=data_date,
                    record_count=len(rows),
                    summary=f"xlsx rows={len(rows)}",
                    output={"dateSource": date_source, "rows": rows, "records": rows},
                )
        except Exception as exc:  # noqa: BLE001
            return source_result(
                parser_state="WAIT_SCHEMA_MISMATCH",
                data_date=data_date,
                record_count=0,
                summary=f"xlsx parse failed: {exc}",
                output={"rows": []},
                error=str(exc),
            )

    # json
    if text.lstrip()[:1] in "{[":
        try:
            return parse_mcx_json_watch(content, url=url, last_modified=last_modified)
        except Exception:
            pass

    # html tables
    tables = re.findall(r"<table[^>]*>(.*?)</table>", text, flags=re.I | re.S)
    records = []
    for tb in tables:
        trs = re.findall(r"<tr[^>]*>(.*?)</tr>", tb, flags=re.I | re.S)
        for tr in trs[1:]:
            cells = [
                re.sub(r"<[^>]+>", "", c).strip()
                for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.I | re.S)
            ]
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue
            rec = {f"c{i}": cells[i] for i in range(len(cells))}
            rec["name"] = cells[0]
            rec["symbol"] = re.sub(r"[^A-Z0-9]+", "_", cells[0].upper())[:24] or "ROW"
            records.append(rec)
    if records:
        return source_result(
            parser_state="PARSED_STRUCTURED",
            data_date=data_date,
            record_count=len(records),
            summary=f"html table rows={len(records)}",
            output={"dateSource": date_source, "rows": records, "records": records},
        )
    return source_result(
        parser_state="WAIT_EMPTY_PARSE",
        data_date=data_date,
        record_count=0,
        summary="no rows from generic table/json/xlsx",
        output={"dateSource": date_source, "rows": []},
    )
