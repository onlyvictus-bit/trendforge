"""Phase-2 parsers for the 30-pack expansion (verified URL families, 2026-08)."""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime
from typing import Any
from xml.etree import ElementTree

from .common import decode_bytes, extract_data_date, parse_date_value, source_result

_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9&.\-]{0,24}$")


def _empty(reason: str, data_date: str | None = None, date_source: str | None = None) -> dict[str, Any]:
    return source_result(
        parser_state="WAIT_EMPTY_PARSE",
        data_date=data_date,
        record_count=0,
        summary=reason,
        output={"dateSource": date_source, "rows": [], "records": []},
    )


def parse_bse_insider_trading(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse BSE insider-trading JSON (Table / list of disclosures)."""
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary="BSE insider payload is not JSON",
            output={"dateSource": date_source, "rows": []},
        )

    raw_rows = payload.get("Table") if isinstance(payload, dict) else None
    if raw_rows is None and isinstance(payload, list):
        raw_rows = payload
    if not isinstance(raw_rows, list):
        raw_rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(raw_rows, list) or not raw_rows:
        return _empty("BSE insider Table empty", data_date, date_source)

    rows: list[dict[str, Any]] = []
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        rec = dict(item)
        # Normalize a few common field aliases for screener
        symbol = (
            rec.get("scrip_symbol")
            or rec.get("ScripCode")
            or rec.get("Fld_ScripCode")
            or rec.get("symbol")
            or rec.get("scripcode")
        )
        name = (
            rec.get("company_name")
            or rec.get("Fld_CompanyName")
            or rec.get("CompanyName")
            or rec.get("name")
        )
        if symbol is not None:
            rec["symbol"] = str(symbol).strip().upper()
        if name is not None:
            rec["companyName"] = str(name).strip()
        rec["insider"] = True
        rows.append(rec)

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"BSE insider disclosures={len(rows)}",
        output={"dateSource": date_source, "rows": rows, "records": rows},
    )


def parse_nse_index_option_chain(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse NSE option-chain JSON (v3 Indices/Equity or equities chain)."""
    text = decode_bytes(content)
    # Never treat option *expiry* embedded in the URL as the market data date.
    data_date, date_source = extract_data_date(text, None, last_modified)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary="Option chain payload is not JSON",
            output={"dateSource": date_source, "rows": []},
        )

    if not isinstance(payload, dict) or not payload:
        return _empty("Option chain empty object", data_date, date_source)

    filtered = (payload.get("filtered") or {}).get("data") or []
    records = (payload.get("records") or {})
    underlying = records.get("underlyingValue")
    expiry_dates = records.get("expiryDates") or payload.get("expiryDates") or []
    timestamp = records.get("timestamp") or payload.get("timestamp")
    if timestamp is None and isinstance(payload.get("records"), dict):
        timestamp = payload["records"].get("timestamp")
    if timestamp and not data_date:
        from .common import parse_date_value

        parsed_ts = parse_date_value(str(timestamp))
        if parsed_ts:
            data_date, date_source = parsed_ts, "payload_timestamp"

    rows: list[dict[str, Any]] = []
    for row in filtered if isinstance(filtered, list) else []:
        if not isinstance(row, dict):
            continue
        strike = row.get("strikePrice")
        rec: dict[str, Any] = {
            "strikePrice": strike,
            "underlyingValue": underlying,
            "symbol": row.get("underlying") or row.get("symbol"),
        }
        for side in ("CE", "PE"):
            side_obj = row.get(side) or {}
            if not isinstance(side_obj, dict):
                continue
            for k, v in side_obj.items():
                if k in {"expiryDates", "identifier", "underlying", "optionType", "expiryDate"}:
                    continue
                rec[f"{side}_{k}"] = v
            if side_obj.get("underlying"):
                rec["symbol"] = side_obj.get("underlying")
            if not data_date and side_obj.get("timestamp"):
                from .common import parse_date_value

                parsed_ts = parse_date_value(str(side_obj.get("timestamp")))
                if parsed_ts:
                    data_date, date_source = parsed_ts, "leg_timestamp"
        if rec.get("symbol"):
            rec["symbol"] = str(rec["symbol"]).strip().upper()
        rows.append(rec)

    if not rows:
        # contract-info only payloads — expiry list is not a future dataDate
        if expiry_dates:
            return source_result(
                parser_state="PARSED_STRUCTURED",
                data_date=data_date,
                record_count=len(expiry_dates),
                summary=f"Option chain expiries={len(expiry_dates)}",
                output={
                    "dateSource": date_source,
                    "expiries": expiry_dates,
                    "rows": [{"expiry": e} for e in expiry_dates],
                    "records": [{"expiry": e} for e in expiry_dates],
                },
            )
        return _empty("Option chain had no strike rows", data_date, date_source)

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Option chain strikes={len(rows)} underlying={underlying}",
        output={
            "dateSource": date_source,
            "underlying": underlying,
            "expiries": expiry_dates,
            "rows": rows,
            "records": rows,
        },
    )


def parse_lbma_fixings(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse LBMA prices.lbma.org.uk JSON list [{d, v:[usd,gbp,eur]}]."""
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary="LBMA payload is not JSON",
            output={"dateSource": date_source, "rows": []},
        )
    if not isinstance(payload, list) or not payload:
        return _empty("LBMA list empty", data_date, date_source)

    fixing = "unknown"
    if url:
        if "gold_am" in url:
            fixing = "gold_am"
        elif "gold_pm" in url:
            fixing = "gold_pm"
        elif "silver" in url:
            fixing = "silver"

    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict) or "d" not in item:
            continue
        vals = item.get("v") or []
        if not isinstance(vals, list) or len(vals) < 1:
            continue
        rows.append(
            {
                "date": item.get("d"),
                "fixing": fixing,
                "usd": vals[0] if len(vals) > 0 else None,
                "gbp": vals[1] if len(vals) > 1 else None,
                "eur": vals[2] if len(vals) > 2 else None,
                "symbol": fixing.upper(),
            }
        )

    if not rows:
        return _empty("LBMA rows empty after parse", data_date, date_source)

    # Prefer latest few for inventory sample
    rows_sorted = sorted(rows, key=lambda r: str(r.get("date") or ""), reverse=True)
    latest_date = rows_sorted[0].get("date")
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=str(latest_date) if latest_date else data_date,
        record_count=len(rows_sorted),
        summary=f"LBMA {fixing} rows={len(rows_sorted)}",
        output={"dateSource": date_source, "fixing": fixing, "rows": rows_sorted, "records": rows_sorted},
    )


def parse_eia_natgas_storage(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse EIA weekly natural gas storage (wngsr.csv or NG_STOR_WKLY_S1_W.xls)."""
    # Prefer official dnav XLS when CSV is WAF-blocked (OLE signature).
    if content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        try:
            import xlrd

            book = xlrd.open_workbook(file_contents=content)
            sheet_name = "Data 1" if "Data 1" in book.sheet_names() else book.sheet_names()[-1]
            sh = book.sheet_by_name(sheet_name)
            if sh.nrows < 4:
                return _empty("EIA storage XLS has no data rows")
            headers = [str(sh.cell_value(2, j) or "") for j in range(sh.ncols)]
            # region labels from row 2 descriptions
            region_labels = []
            for h in headers[1:]:
                low = h.lower()
                if "lower 48" in low:
                    region_labels.append("Lower 48")
                elif "east region" in low:
                    region_labels.append("East")
                elif "midwest" in low:
                    region_labels.append("Midwest")
                elif "mountain" in low:
                    region_labels.append("Mountain")
                elif "pacific" in low:
                    region_labels.append("Pacific")
                elif "nonsalt" in low:
                    region_labels.append("South Central Nonsalt")
                elif "salt south" in low:
                    region_labels.append("South Central Salt")
                elif "south central" in low:
                    region_labels.append("South Central")
                else:
                    region_labels.append(h[:40] or "Region")
            last_i = sh.nrows - 1
            prev_i = sh.nrows - 2 if sh.nrows > 4 else last_i
            raw_date = sh.cell_value(last_i, 0)
            try:
                data_date = xlrd.xldate_as_datetime(raw_date, book.datemode).date().isoformat()
                date_source = "xls_date"
            except Exception:
                data_date, date_source = extract_data_date("", url, last_modified)
            rows = []
            for j, label in enumerate(region_labels, start=1):
                stocks = sh.cell_value(last_i, j) if j < sh.ncols else None
                week_ago = sh.cell_value(prev_i, j) if j < sh.ncols else None
                try:
                    stocks_f = float(stocks) if stocks not in ("", None) else None
                except (TypeError, ValueError):
                    stocks_f = None
                try:
                    week_ago_f = float(week_ago) if week_ago not in ("", None) else None
                except (TypeError, ValueError):
                    week_ago_f = None
                net = None
                if stocks_f is not None and week_ago_f is not None:
                    net = round(stocks_f - week_ago_f, 3)
                rows.append(
                    {
                        "region": label,
                        "stocks_bcf": stocks_f,
                        "week_ago_bcf": week_ago_f,
                        "net_change_bcf": net,
                        "implied_flow_bcf": net,
                        "symbol": re.sub(r"[^A-Z0-9]+", "_", label.upper())[:24] or "NATGAS",
                    }
                )
            if not rows:
                return _empty("EIA storage XLS empty after parse", data_date, date_source)
            return source_result(
                parser_state="PARSED_STRUCTURED",
                data_date=data_date,
                record_count=len(rows),
                summary=f"EIA storage XLS regions={len(rows)}",
                output={
                    "dateSource": date_source,
                    "rows": rows,
                    "records": rows,
                    "sourceFormat": "xls_dnav",
                },
            )
        except Exception as exc:  # noqa: BLE001
            return source_result(
                parser_state="WAIT_SCHEMA_MISMATCH",
                data_date=None,
                record_count=0,
                summary=f"EIA storage XLS parse failed: {exc}",
                output={"rows": []},
                error=str(exc),
            )

    text = decode_bytes(content).replace("\x1a", "")
    data_date, date_source = extract_data_date(text, url, last_modified)
    released = next((ln.strip().strip('"') for ln in text.splitlines() if ln.startswith('"Released')), None)
    next_rel = next((ln.strip().strip('"') for ln in text.splitlines() if ln.startswith('"Next Release')), None)

    rows: list[dict[str, Any]] = []
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        head = row[0].strip()
        if head in {"", "Region"} or head.startswith(("Note", "It ", "which", "Energy", '"')):
            continue
        if len(row) < 8:
            continue

        def num(i: int) -> float | None:
            if i >= len(row):
                return None
            v = row[i].replace(",", "").strip()
            if not re.fullmatch(r"-?\d+(\.\d+)?", v or ""):
                return None
            return float(v)

        rows.append(
            {
                "region": head,
                "stocks_bcf": num(1),
                "week_ago_bcf": num(4) if len(row) > 4 else None,
                "net_change_bcf": num(7) if len(row) > 7 else None,
                "implied_flow_bcf": num(10) if len(row) > 10 else None,
                "year_ago_bcf": num(13) if len(row) > 13 else None,
                "year_ago_pct": num(16) if len(row) > 16 else None,
                "five_yr_avg_bcf": num(19) if len(row) > 19 else None,
                "five_yr_pct": num(22) if len(row) > 22 else None,
                "symbol": re.sub(r"[^A-Z0-9]+", "_", head.upper())[:24] or "NATGAS",
            }
        )

    if not rows:
        return _empty("EIA natgas table empty", data_date, date_source)

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"EIA natgas regions={len(rows)} released={released}",
        output={
            "dateSource": date_source,
            "released": released,
            "next_release": next_rel,
            "rows": rows,
            "records": rows,
        },
    )


def parse_usda_wasde_index(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse official WASDE XML/ESMIS bundle or the retained Cornell fallbacks."""
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)

    # ESMIS discovery bundle preserves both release metadata and original XML.
    release: dict[str, Any] = {}
    xml_text = text
    if text.lstrip().startswith("{"):
        try:
            bundle = json.loads(text)
        except json.JSONDecodeError:
            bundle = None
        if isinstance(bundle, dict) and isinstance(bundle.get("xml"), str):
            xml_text = bundle["xml"]
            release = bundle.get("release") if isinstance(bundle.get("release"), dict) else {}
            release_date = parse_date_value(release.get("release_datetime"))
            if release_date:
                data_date = release_date
                date_source = "esmis_release_datetime"

    if "<Report" in xml_text[:2000] and "<Cell" in xml_text:
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            return source_result(
                parser_state="WAIT_SCHEMA_MISMATCH",
                data_date=data_date,
                record_count=0,
                summary="WASDE XML is malformed.",
                output={"dateSource": date_source, "rows": []},
                error=str(exc),
            )

        report_month = next(
            (
                str(node.attrib.get("Report_Month"))
                for node in root.iter()
                if node.attrib.get("Report_Month")
            ),
            None,
        )
        if not release and report_month:
            try:
                data_date = datetime.strptime(report_month, "%B %Y").date().replace(day=1).isoformat()
                date_source = "xml_report_month"
            except ValueError:
                pass

        rows: list[dict[str, Any]] = []
        cell_count = 0
        invalid = 0

        def pick(context: dict[str, str], pattern: str) -> str | None:
            matcher = re.compile(pattern, re.I)
            return next((value for key, value in context.items() if matcher.search(key) and value.strip()), None)

        def visit(
            node: ElementTree.Element,
            context: dict[str, str],
            matrix: str | None = None,
            path: str = "",
        ) -> None:
            nonlocal cell_count, invalid
            current = {**context, **{str(k): str(v) for k, v in node.attrib.items()}}
            current_matrix = node.tag if re.fullmatch(r"matrix\d+", node.tag, re.I) else matrix
            if node.tag == "Cell":
                value_items = [
                    (key, value)
                    for key, value in node.attrib.items()
                    if key.casefold().startswith("cell_value") and str(value).strip()
                ]
                if not value_items:
                    invalid += 1
                    return
                for value_key, raw_value in value_items:
                    cell_count += 1
                    clean = " ".join(str(raw_value).split())
                    try:
                        value: float | str = float(clean.replace(",", ""))
                    except ValueError:
                        value = clean
                    commodity = pick(current, r"^commodity\d+$")
                    market_year = pick(current, r"^market_year\d+$")
                    forecast_month = pick(current, r"^forecast_month\d+$")
                    attribute = pick(current, r"^attribute\d+$")
                    report_name = pick(current, r"^Name$") or "WASDE"
                    rows.append(
                        {
                            "symbol": "WASDE",
                            "reportName": report_name,
                            "reportMonth": pick(current, r"^Report_Month$") or report_month,
                            "releaseDate": data_date,
                            "pageTitle": pick(current, r"^page_title$") or None,
                            "subReportTitle": pick(current, r"^sub_report_title$") or None,
                            "unit": pick(current, r"^sub_report_subtitle$") or None,
                            "matrix": current_matrix,
                            "market": pick(current, r"^commodity_header\d+$") or None,
                            "commodity": commodity,
                            "marketYear": market_year,
                            "forecastMonth": forecast_month,
                            "attribute": attribute,
                            "valueField": value_key,
                            "value": value,
                            "rawValue": clean,
                            "xmlPath": path,
                            "sourceUrl": url,
                            "sourceTrust": "OFFICIAL",
                            "scope": "COMMODITY_CONTEXT_ONLY",
                            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
                        }
                    )
                return
            for position, child in enumerate(node, start=1):
                visit(
                    child,
                    current,
                    current_matrix,
                    f"{path}/{child.tag}[{position}]",
                )

        visit(root, {}, path=f"/{root.tag}[1]")
        if rows:
            return source_result(
                parser_state="PARSED_STRUCTURED",
                data_date=data_date,
                record_count=len(rows),
                summary=f"WASDE official XML values={len(rows)}.",
                output={
                    "dateSource": date_source,
                    "releaseMetadata": release,
                    "sourceCellValueCount": cell_count,
                    "invalidCellCount": invalid,
                    "rows": rows,
                    "records": rows,
                    "parserVersion": "2.0.0",
                    "sourceTrust": "OFFICIAL",
                    "scope": "COMMODITY_CONTEXT_ONLY",
                    "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
                },
            )
        return _empty("WASDE XML contains no populated cell values", data_date, date_source)

    links = re.findall(r'href="(/sites/default/release-files/\d+/wasde[^"]+)"', text)
    seen: set[str] = set()
    ordered: list[str] = []
    for link in links:
        if link not in seen:
            seen.add(link)
            ordered.append(link)
    if ordered:
        rows = []
        for link in ordered[:30]:
            ext = link.rsplit(".", 1)[-1].lower() if "." in link else ""
            rows.append(
                {
                    "path": link,
                    "url": f"https://usda.library.cornell.edu{link}",
                    "ext": ext,
                    "symbol": "WASDE",
                    "name": link.rsplit("/", 1)[-1],
                }
            )
        return source_result(
            parser_state="PARSED_STRUCTURED",
            data_date=data_date,
            record_count=len(rows),
            summary=f"WASDE release files listed={len(rows)}",
            output={"dateSource": date_source, "rows": rows, "records": rows},
        )

    # Direct .txt body (multi-step may already resolve the release file)
    if "WASDE" in text[:4000] or "World and U.S. Supply" in text[:8000]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        section = "WASDE"
        rows = []
        for ln in lines[:400]:
            if re.match(r"^[A-Za-z].{8,}$", ln) and not ln.startswith("="):
                if "Supply and Use" in ln or "WASDE" in ln:
                    section = ln[:80]
                    continue
            # commodity-ish numeric lines: name + numbers
            if re.search(r"\d+\.\d+", ln) and len(ln) > 12:
                rows.append(
                    {
                        "symbol": "WASDE",
                        "section": section,
                        "line": ln[:240],
                        "name": ln[:80],
                    }
                )
        if rows:
            return source_result(
                parser_state="PARSED_STRUCTURED",
                data_date=data_date,
                record_count=len(rows),
                summary=f"WASDE text lines={len(rows)}",
                output={"dateSource": date_source, "rows": rows, "records": rows},
            )
    return _empty("WASDE release links not found on page", data_date, date_source)


def parse_rbi_usdinr_html(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse RBI Reference Rate Archive HTML table for USD/INR rows."""
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    if "USD" not in text and "INR" not in text:
        # Form page without submitted results is not a failure of schema forever
        if "__VIEWSTATE" in text:
            return source_result(
                parser_state="WAIT_EMPTY_PARSE",
                data_date=data_date,
                record_count=0,
                summary="RBI page is the form shell (POST required for rates table)",
                output={"dateSource": date_source, "rows": [], "needsPost": True},
            )

    rows: list[dict[str, Any]] = []
    # Rough table cell extraction without hard bs4 dependency requirement
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.I | re.S):
        cells = [
            re.sub(r"<[^>]+>", "", c).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.I | re.S)
        ]
        cells = [c for c in cells if c]
        if len(cells) < 2:
            continue
        if not re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", cells[0]):
            continue
        rate_raw = cells[1].replace(",", "")
        try:
            rate = float(rate_raw)
        except ValueError:
            continue
        rows.append(
            {
                "date": cells[0],
                "usdinr": rate,
                "symbol": "USDINR",
                "pair": "USDINR",
            }
        )

    if not rows:
        return _empty("RBI USDINR rate rows not found", data_date, date_source)

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"RBI USDINR rows={len(rows)}",
        output={"dateSource": date_source, "rows": rows, "records": rows},
    )


def parse_nse_fii_derivatives_stats_text(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Best-effort parse for FII derivatives stats (XLS via xlrd, else text)."""
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    # OLE compound file signature for classic .xls — prefer xlrd path
    if content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        try:
            from ..phase3_multi_step_fetch import parse_fii_derivatives_xls

            return parse_fii_derivatives_xls(content, url=url)
        except Exception as exc:  # noqa: BLE001
            return source_result(
                parser_state="WAIT_SCHEMA_MISMATCH",
                data_date=data_date,
                record_count=0,
                summary=f"FII derivatives XLS parse failed: {exc}",
                output={"dateSource": date_source, "rows": [], "needsXlrd": True},
                error=str(exc),
            )

    rows: list[dict[str, Any]] = []
    # CSV archive (fao_participant_fii_YYYYMMDD.csv from audit downloader)
    if "," in text[:800] and "\n" in text:
        import csv
        import io

        try:
            reader = csv.DictReader(io.StringIO(text))
            for raw in reader:
                if not raw:
                    continue
                name = str(
                    raw.get("instrument")
                    or raw.get("Instrument")
                    or raw.get("Instrument Type")
                    or raw.get("instrument_type")
                    or raw.get("Client Type")
                    or raw.get("client_type")
                    or ""
                ).strip()
                if not name or name.lower() in {
                    "instrument",
                    "instrument type",
                    "client type",
                }:
                    continue

                def pf(*keys: str) -> float | None:
                    for k in keys:
                        if k in raw and raw[k] not in (None, ""):
                            try:
                                return float(str(raw[k]).replace(",", "").strip())
                            except ValueError:
                                continue
                    return None

                rows.append(
                    {
                        "instrument": name,
                        "buy_contracts": pf(
                            "buy_contracts", "Buy Contracts", "buyContracts"
                        ),
                        "buy_amt_cr": pf(
                            "buy_amt_cr", "Buy Amt in Cr", "buyValue", "buy_amt"
                        ),
                        "sell_contracts": pf(
                            "sell_contracts", "Sell Contracts", "sellContracts"
                        ),
                        "sell_amt_cr": pf(
                            "sell_amt_cr", "Sell Amt in Cr", "sellValue", "sell_amt"
                        ),
                        "oi_contracts": pf(
                            "oi_contracts", "OI Contracts", "openInterest"
                        ),
                        "oi_amt_cr": pf("oi_amt_cr", "OI Amt in Cr", "oiValue"),
                        "symbol": re.sub(r"[^A-Z0-9]+", "_", name.upper())[:32],
                    }
                )
        except csv.Error:
            rows = []

    if not rows:
        for line in text.splitlines():
            if not line.strip() or line.lower().startswith("instrument"):
                continue
            parts = re.split(r"[\t,;]+", line.strip())
            if len(parts) < 3:
                continue
            name = parts[0].strip()
            if not name or len(name) < 3:
                continue
            if not re.search(
                r"INDEX|STOCK|FUTURE|OPTION|FII|CLIENT|PRO|DII", name, re.I
            ):
                if not re.search(r"[A-Za-z]", name):
                    continue
            nums: list[float | None] = []
            for p in parts[1:7]:
                try:
                    nums.append(float(str(p).replace(",", "")))
                except ValueError:
                    nums.append(None)
            while len(nums) < 6:
                nums.append(None)
            rows.append(
                {
                    "instrument": name,
                    "buy_contracts": nums[0],
                    "buy_amt_cr": nums[1],
                    "sell_contracts": nums[2],
                    "sell_amt_cr": nums[3],
                    "oi_contracts": nums[4],
                    "oi_amt_cr": nums[5],
                    "symbol": re.sub(r"[^A-Z0-9]+", "_", name.upper())[:32],
                }
            )

    if not rows:
        return _empty("FII derivatives stats rows not parseable as text", data_date, date_source)

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"FII derivatives text/CSV rows={len(rows)}",
        output={"dateSource": date_source, "rows": rows, "records": rows},
    )
