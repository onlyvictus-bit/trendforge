"""Loop verification for TrendForge focus sources 2-10 (evidence only; no workbook edit)."""
from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta
from pathlib import Path

from trendforge_api.institutional_sources import AsyncEndpointClient
from trendforge_api.parsers import (
    parse_bse_pledge_data,
    parse_nsdl_fpi_daily,
    parse_nsdl_fpi_fortnightly,
    parse_nse_block_deal_live,
    parse_nse_option_chain,
    parse_nse_pit_current,
    parse_nse_regulation_disclosure,
    parse_sge_benchmark_gold,
)

OUT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\loop_evidence"
)
OUT.mkdir(parents=True, exist_ok=True)

PARSERS = {
    "bse_pledge_data": parse_bse_pledge_data,
    "nse_regulation_31": parse_nse_regulation_disclosure,
    "nse_regulation_29": parse_nse_regulation_disclosure,
    "nse_pit_symbol": parse_nse_pit_current,
    "nse_pit": parse_nse_pit_current,
    "nse_block_deal": parse_nse_block_deal_live,
    "nsdl_fpi_daily_reportdetail": parse_nsdl_fpi_daily,
    "nsdl_fpi": parse_nsdl_fpi_daily,
    "nsdl_fpi_fortnightly": parse_nsdl_fpi_fortnightly,
    "sge_benchmark_gold": parse_sge_benchmark_gold,
    "nse_option_chain_equity": parse_nse_option_chain,
}


def _raw(res) -> bytes:
    if res.raw_path and Path(res.raw_path).exists():
        return Path(res.raw_path).read_bytes()
    if res.payload is None:
        return b""
    if isinstance(res.payload, (bytes, bytearray)):
        return bytes(res.payload)
    if isinstance(res.payload, str):
        return res.payload.encode("utf-8", errors="replace")
    return json.dumps(res.payload).encode("utf-8")


def _classify(state: str, usable_rows: int, parser_state: str | None, summary: str) -> str:
    if usable_rows > 0 and state == "RAW_ARCHIVED":
        return "POPULATED_USABLE"
    if state == "STALE_FALLBACK":
        return "STALE_FALLBACK"
    if state == "NO_DATA_NOW" or parser_state == "WAIT_EMPTY_PARSE":
        if "softEmptyObject" in (summary or "") or "empty object" in (summary or "").lower():
            return "SOFT_EMPTY"
        return "VALID_EMPTY"
    if "rejected" in (summary or "").lower() or "WAF" in (summary or ""):
        return "BLOCKED"
    if parser_state == "WAIT_SCHEMA_MISMATCH":
        return "SCHEMA_CHANGED_OR_PARSE_FAILED"
    return "NOT_USABLE"


async def fetch_one(client: AsyncEndpointClient, key: str, params: dict) -> dict:
    print("FETCH", key, params, flush=True)
    try:
        res = await client.fetch(key, params)
    except Exception as exc:  # noqa: BLE001
        return {
            "source_key": key,
            "params": params,
            "status": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
            "usable_rows": 0,
        }
    raw = _raw(res)
    parser = PARSERS.get(key)
    parsed = parser(raw) if parser and raw else None
    rows = []
    if isinstance(parsed, dict):
        rows = list((parsed.get("output") or {}).get("rows") or [])
    usable = int((parsed or {}).get("record_count") or 0)
    if usable <= 0 and isinstance(res.payload, dict):
        data = res.payload.get("data") or res.payload.get("Table")
        if isinstance(data, list) and data and isinstance(data[0], dict):
            rows = data
            usable = len(data)
    state = res.state.value if hasattr(res.state, "value") else str(res.state)
    parser_state = (parsed or {}).get("parser_state")
    summary = (parsed or {}).get("summary") or res.reason or ""
    # Stale never counts as populated usable for live success.
    if state == "STALE_FALLBACK":
        classification = "STALE_FALLBACK"
        usable_live = 0
    else:
        classification = _classify(state, usable, parser_state, summary)
        usable_live = usable if classification == "POPULATED_USABLE" else 0
    sample = rows[:2]
    out = {
        "source_key": key,
        "params": params,
        "url": res.url,
        "state": state,
        "status_code": res.status_code,
        "classification": classification,
        "usable_rows": usable_live,
        "parsed_rows": usable,
        "parser_state": parser_state,
        "summary": summary,
        "sample_fields": list(sample[0].keys()) if sample and isinstance(sample[0], dict) else [],
        "sample_rows": sample,
        "raw_path": res.raw_path,
        "reason": res.reason,
    }
    if usable > 0 and parsed:
        (OUT / f"{key}_parsed.json").write_text(
            json.dumps(parsed, indent=2, default=str)[:400000], encoding="utf-8"
        )
    print(" ", classification, "rows=", usable_live, "parsed=", usable, flush=True)
    return out


async def main() -> None:
    today = date.today()
    month = today.strftime("%Y-%m")
    windows = [
        ((today - timedelta(days=7)).strftime("%d-%m-%Y"), today.strftime("%d-%m-%Y")),
        ((today - timedelta(days=30)).strftime("%d-%m-%Y"), today.strftime("%d-%m-%Y")),
        ((today - timedelta(days=90)).strftime("%d-%m-%Y"), today.strftime("%d-%m-%Y")),
        ((today - timedelta(days=365)).strftime("%d-%m-%Y"), today.strftime("%d-%m-%Y")),
        ("01-01-2025", "31-12-2025"),
        ("01-01-2024", "31-12-2024"),
    ]
    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "ITC"]

    requests: list[tuple[str, dict]] = [
        ("bse_pledge_data", {}),
        ("sge_benchmark_gold", {"start": month, "end": month}),
        ("sge_benchmark_gold", {"start": "2026-01", "end": "2026-08"}),
        ("nsdl_fpi", {}),
        ("nsdl_fpi_daily_reportdetail", {}),
        ("nsdl_fpi_fortnightly", {}),
        ("nse_block_deal", {}),
        ("nse_regulation_29", {}),
        ("nse_regulation_31", {}),
        ("nse_pit", {}),
    ]
    for symbol in symbols:
        for frm, to in windows[:3]:
            requests.append(
                ("nse_pit_symbol", {"symbol": symbol, "from_date": frm, "to_date": to})
            )
    # Historical wide windows for reg/pit bulk
    for frm, to in windows:
        requests.append(("nse_pit", {}))  # current list no date params
        break

    # Derivatives fan-out children for loop 10
    for key in (
        "nse_live_equity_derivatives_stock_opt",
        "nse_live_equity_derivatives_stock_fut",
        "nse_live_equity_derivatives_index_opt",
        "nse_live_equity_derivatives_index_fut",
        "nse_live_equity_derivatives_banknifty_opt",
        "nse_live_equity_derivatives_banknifty_fut",
    ):
        requests.append((key, {}))

    results: list[dict] = []
    client = AsyncEndpointClient()
    try:
        for key, params in requests:
            # de-dupe identical sequential pit without params
            results.append(await fetch_one(client, key, params))
    finally:
        await client.aclose()

    # Summarize best per key
    best: dict[str, dict] = {}
    for row in results:
        key = row["source_key"]
        prev = best.get(key)
        if prev is None or (row.get("usable_rows") or 0) > (prev.get("usable_rows") or 0):
            best[key] = row
        elif prev and row.get("classification") == "POPULATED_USABLE":
            best[key] = row

    summary = {
        "tested_at": date.today().isoformat(),
        "best_by_key": best,
        "all_attempts": results,
    }
    path = OUT / "LOOP_02_10_live_results.json"
    path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print("WROTE", path)
    for key, row in sorted(best.items()):
        print(
            f"{key}: {row.get('classification')} usable={row.get('usable_rows')} "
            f"parsed={row.get('parsed_rows')} state={row.get('state')}"
        )


if __name__ == "__main__":
    asyncio.run(main())
