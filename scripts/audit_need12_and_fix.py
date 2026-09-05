"""Probe the unique keys still missing populated evidence among 105 linked rows."""
from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

from trendforge_api.institutional_sources import AsyncEndpointClient, ENDPOINTS
from trendforge_api.parsers import (
    parse_bse_pledge_data,
    parse_cdsl_fpi_fortnightly_sector,
    parse_nse_option_chain,
    parse_nse_pit_current,
    parse_nse_regulation_disclosure,
)

OUT = Path(r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105")
OUT.mkdir(parents=True, exist_ok=True)


def _raw(res) -> bytes:
    if res.raw_path and Path(res.raw_path).exists():
        return Path(res.raw_path).read_bytes()
    return b""


async def main() -> None:
    today = date.today().strftime("%d-%m-%Y")
    client = AsyncEndpointClient()
    results: list[dict] = []
    try:
        jobs: list[tuple[str, dict]] = [
            ("nse_tender_buyback", {}),
            (
                "nse_pit_symbol",
                {"symbol": "INFY", "from_date": "01-01-2024", "to_date": today},
            ),
            (
                "nse_pit_symbol",
                {"symbol": "RELIANCE", "from_date": "01-01-2024", "to_date": today},
            ),
            ("nse_pit", {}),
            (
                "nse_pit_annual",
                {"from_date": "01-01-2024", "to_date": today},
            ),
            ("nse_regulation_29", {}),
            ("nse_regulation_31", {}),
            ("nse_regulation_29_symbol", {"symbol": "INFY"}),
            ("nse_regulation_31_symbol", {"symbol": "INFY"}),
            ("nse_option_chain_equity", {"symbol": "RELIANCE"}),
            ("nse_live_equity_derivatives_stock_opt", {}),
            ("nsdl_fpi_fortnightly", {}),
            ("cdsl_fpi_fortnightly_sector", {"report_date": "July 15, 2026"}),
            ("bse_sast", {}),
            ("bse_pledge_data", {}),
            ("bse_buyback_tender", {}) if "bse_buyback_tender" in ENDPOINTS else ("bse_sast", {}),
        ]
        # buyback offers if present
        for key in list(ENDPOINTS):
            if "buyback" in key.lower() or "tender" in key.lower():
                if (key, {}) not in jobs and not ENDPOINTS[key].required_parameters:
                    jobs.append((key, {}))

        for key, params in jobs:
            if key not in ENDPOINTS:
                results.append({"key": key, "error": "not in ENDPOINTS", "usable": 0})
                continue
            # fill required empty if needed
            req = list(ENDPOINTS[key].required_parameters)
            for rp in req:
                params.setdefault(rp, "")
            # skip if still missing required non-empty
            missing = [rp for rp in req if not str(params.get(rp) or "").strip()]
            if missing and key not in {"cdsl_fpi_fortnightly_sector", "nse_pit_symbol", "nse_pit_annual", "nse_regulation_29_symbol", "nse_regulation_31_symbol", "nse_option_chain_equity"}:
                # try with defaults already set
                pass
            print("FETCH", key, params, flush=True)
            try:
                res = await client.fetch(key, params)
            except Exception as exc:  # noqa: BLE001
                print("  ERR", exc, flush=True)
                results.append({"key": key, "params": params, "error": str(exc), "usable": 0})
                continue
            raw = _raw(res)
            usable = 0
            sample = None
            summary = res.reason
            state = res.state.value if hasattr(res.state, "value") else str(res.state)

            if key.startswith("nse_pit") and raw:
                pr = parse_nse_pit_current(raw)
                usable = int(pr.get("record_count") or 0)
                sample = (pr.get("output") or {}).get("rows", [])[:2]
                summary = pr.get("summary")
            elif "regulation" in key and raw:
                pr = parse_nse_regulation_disclosure(raw)
                usable = int(pr.get("record_count") or 0)
                sample = (pr.get("output") or {}).get("rows", [])[:2]
                summary = pr.get("summary")
            elif "option_chain" in key and raw:
                pr = parse_nse_option_chain(raw)
                usable = int(pr.get("record_count") or 0)
                summary = pr.get("summary")
            elif key == "cdsl_fpi_fortnightly_sector" and raw:
                pr = parse_cdsl_fpi_fortnightly_sector(raw)
                usable = int(pr.get("record_count") or 0)
                sample = (pr.get("output") or {}).get("rows", [])[:2]
                summary = pr.get("summary")
            elif key == "bse_pledge_data" and raw:
                pr = parse_bse_pledge_data(raw)
                usable = int(pr.get("record_count") or 0)
                sample = (pr.get("output") or {}).get("rows", [])[:2]
                summary = pr.get("summary")
            elif isinstance(res.payload, list):
                usable = len(res.payload)
                sample = res.payload[:2]
            elif isinstance(res.payload, dict):
                data = res.payload.get("data")
                if isinstance(data, list):
                    usable = len(data)
                    sample = data[:2]
                else:
                    usable = int(res.record_count or 0)
                    sample = [res.payload] if usable else None
            else:
                usable = int(res.record_count or 0)

            # soft empty classification
            head = raw[:60]
            if usable <= 0 and b"Request Rejected" in head:
                classification = "BLOCKED"
            elif usable > 0 and state == "RAW_ARCHIVED":
                classification = "POPULATED"
            elif usable <= 0:
                classification = "EMPTY"
            else:
                classification = state

            item = {
                "key": key,
                "params": params,
                "url": res.url,
                "state": state,
                "status_code": res.status_code,
                "usable": usable,
                "classification": classification,
                "summary": summary,
                "sample": sample,
                "raw_path": res.raw_path,
            }
            results.append(item)
            print(" ", classification, usable, flush=True)
            if usable > 0:
                (OUT / f"{key}_sample.json").write_text(
                    json.dumps(item, indent=2, default=str)[:200000],
                    encoding="utf-8",
                )
    finally:
        await client.aclose()

    path = OUT / "need12_probe.json"
    path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("WROTE", path)


if __name__ == "__main__":
    asyncio.run(main())
