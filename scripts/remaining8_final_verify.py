"""Final live verification for remaining focus sources + companions."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from trendforge_api.institutional_sources import AsyncEndpointClient
from trendforge_api.parsers import (
    parse_bse_pledge_data,
    parse_cdsl_fpi_fortnightly_sector,
    parse_nse_large_deals_snapshot,
    parse_nse_pit_current,
    parse_nse_regulation_disclosure,
)

OUT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\remaining_fix"
)
OUT.mkdir(parents=True, exist_ok=True)


def _raw(res) -> bytes:
    if res.raw_path and Path(res.raw_path).exists():
        return Path(res.raw_path).read_bytes()
    return b""


async def main() -> None:
    client = AsyncEndpointClient()
    results: list[dict] = []
    try:
        jobs = [
            ("cdsl_fpi_fortnightly_sector", {"report_date": "July 15, 2026"}),
            ("nse_large_deals_snapshot", {}),
            (
                "nse_pit_symbol",
                {
                    "symbol": "INFY",
                    "from_date": "01-01-2024",
                    "to_date": "01-08-2026",
                },
            ),
            ("nse_regulation_29_symbol", {"symbol": "RELIANCE"}),
            ("nse_regulation_31_symbol", {"symbol": "RELIANCE"}),
            ("bse_sast", {}),
            ("bse_pledge_data", {}),
            ("nse_option_chain_equity", {"symbol": "RELIANCE"}),
            ("nse_block_deal", {}),
            ("nsdl_fpi_fortnightly", {}),
        ]
        for key, params in jobs:
            print("FETCH", key, params, flush=True)
            res = await client.fetch(key, params)
            raw = _raw(res)
            parsed = None
            if key == "cdsl_fpi_fortnightly_sector" and raw:
                parsed = parse_cdsl_fpi_fortnightly_sector(raw)
            elif key == "nse_large_deals_snapshot" and raw:
                parsed = parse_nse_large_deals_snapshot(raw)
            elif key.startswith("nse_pit") and raw:
                parsed = parse_nse_pit_current(raw)
            elif "regulation" in key and raw:
                parsed = parse_nse_regulation_disclosure(raw)
            elif key == "bse_pledge_data" and raw:
                parsed = parse_bse_pledge_data(raw)
            elif key == "bse_sast" and isinstance(res.payload, list):
                parsed = {
                    "parser_state": "PARSED_STRUCTURED",
                    "record_count": len(res.payload),
                    "summary": f"Parsed {len(res.payload)} BSE SAST rows.",
                    "output": {"rows": res.payload},
                }
            rows = []
            if isinstance(parsed, dict):
                rows = list((parsed.get("output") or {}).get("rows") or [])
            usable = int((parsed or {}).get("record_count") or 0)
            if usable <= 0 and isinstance(res.payload, list):
                usable = len(res.payload)
                rows = res.payload
            state = res.state.value if hasattr(res.state, "value") else str(res.state)
            if usable > 0 and state == "RAW_ARCHIVED":
                classification = "POPULATED_USABLE"
            elif state == "NO_DATA_NOW" or usable == 0 and state == "RAW_ARCHIVED":
                # WAF body or soft empty
                head = raw[:80].decode("utf-8", errors="replace") if raw else ""
                if "Request Rejected" in head:
                    classification = "BLOCKED"
                elif raw.strip() in (b"{}", b"[]") or head.startswith("{"):
                    classification = "VALID_EMPTY_OR_SOFT_EMPTY"
                else:
                    classification = "NOT_POPULATED"
            else:
                classification = state
            item = {
                "source_key": key,
                "params": params,
                "url": res.url,
                "state": state,
                "status_code": res.status_code,
                "classification": classification,
                "usable_rows": usable if classification == "POPULATED_USABLE" else 0,
                "parsed_rows": usable,
                "summary": (parsed or {}).get("summary") or res.reason,
                "sample_rows": rows[:2],
                "raw_path": res.raw_path,
            }
            results.append(item)
            print(" ", classification, "rows=", item["usable_rows"], flush=True)
            if usable > 0 and parsed:
                safe = key.replace(":", "_")
                (OUT / f"final_{safe}_parsed.json").write_text(
                    json.dumps(parsed, indent=2, default=str)[:400000],
                    encoding="utf-8",
                )
    finally:
        await client.aclose()

    out = OUT / "REMAINING_8_FINAL.json"
    out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("WROTE", out)


if __name__ == "__main__":
    asyncio.run(main())
