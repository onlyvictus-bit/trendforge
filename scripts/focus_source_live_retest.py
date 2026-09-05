"""Live retest of focus TrendForge linked sources that were not usable."""
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
    parse_sge_benchmark_gold,
)
from trendforge_api.source_parser import parse_source_content

OUT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\focus_fix"
)
OUT.mkdir(parents=True, exist_ok=True)

KEY_TO_PARSER = {
    "bse_pledge_data": parse_bse_pledge_data,
    "nsdl_fpi_daily_reportdetail": parse_nsdl_fpi_daily,
    "nsdl_fpi_daily": parse_nsdl_fpi_daily,
    "nsdl_fpi_fortnightly": parse_nsdl_fpi_fortnightly,
    "sge_benchmark_gold": parse_sge_benchmark_gold,
    "nse_block_deal": parse_nse_block_deal_live,
    "nse_block_deal_live": parse_nse_block_deal_live,
    "nse_option_chain_equity": parse_nse_option_chain,
    "nse_option_chain_nifty": parse_nse_option_chain,
    "nse_option_chain": parse_nse_option_chain,
    "nse_pit_symbol": parse_nse_pit_current,
    "nse_pit": parse_nse_pit_current,
    "nse_pit_current": parse_nse_pit_current,
}


def _raw_bytes(res) -> bytes:
    if res.raw_path and Path(res.raw_path).exists():
        return Path(res.raw_path).read_bytes()
    if res.payload is None:
        return b""
    if isinstance(res.payload, (bytes, bytearray)):
        return bytes(res.payload)
    if isinstance(res.payload, str):
        return res.payload.encode("utf-8", errors="replace")
    return json.dumps(res.payload, ensure_ascii=True).encode("utf-8")


def _parse(key: str, raw: bytes, url: str | None) -> dict:
    parser = KEY_TO_PARSER.get(key)
    if parser is not None and raw:
        return parser(raw)
    if raw:
        try:
            pr = parse_source_content(key, raw, url=url)
            return {
                "parser_state": pr.parser_state,
                "record_count": pr.record_count,
                "summary": pr.summary,
                "output": pr.output,
                "data_date": pr.data_date,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "parser_state": "WAIT_SCHEMA_MISMATCH",
                "record_count": 0,
                "summary": f"parse_source_content failed: {exc}",
                "output": {"rows": []},
            }
    return {
        "parser_state": "WAIT_EMPTY_PARSE",
        "record_count": 0,
        "summary": "No raw body available",
        "output": {"rows": []},
    }


def _fallback_payload_rows(payload) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") or payload.get("Table") or payload.get("records")
    if isinstance(data, dict):
        data = data.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return [row for row in data if isinstance(row, dict)]
    return []


async def main() -> None:
    today = date.today()
    month = today.strftime("%Y-%m")
    nse_from = (today - timedelta(days=90)).strftime("%d-%m-%Y")
    nse_to = today.strftime("%d-%m-%Y")

    requests = [
        ("bse_pledge_data", {}),
        ("nsdl_fpi_daily_reportdetail", {}),
        ("nsdl_fpi_fortnightly", {}),
        ("sge_benchmark_gold", {"start": month, "end": month}),
        ("nse_block_deal", {}),
        ("nse_option_chain_equity", {"symbol": "RELIANCE"}),
        ("nse_option_chain_nifty", {}),
        (
            "nse_pit_symbol",
            {"symbol": "RELIANCE", "from_date": nse_from, "to_date": nse_to},
        ),
        ("nse_pit", {}),
        ("nse_regulation_29", {}),
        ("nse_regulation_31", {}),
    ]

    results: list[dict] = []
    client = AsyncEndpointClient()
    try:
        for key, params in requests:
            print("FETCH", key, params, flush=True)
            try:
                res = await client.fetch(key, params)
            except Exception as exc:  # noqa: BLE001
                print("  EXC", type(exc).__name__, exc, flush=True)
                results.append(
                    {
                        "source_key": key,
                        "error": f"{type(exc).__name__}: {exc}",
                        "verdict": "NOT_USABLE",
                        "usable_rows": 0,
                    }
                )
                continue

            raw = _raw_bytes(res)
            parsed = _parse(key, raw, res.url)
            rows = []
            if isinstance(parsed.get("output"), dict):
                rows = list(parsed["output"].get("rows") or [])
            if not rows:
                rows = _fallback_payload_rows(res.payload)

            usable_rows = int(parsed.get("record_count") or 0)
            if usable_rows <= 0 and rows:
                usable_rows = len(rows)

            sample_rows = rows[:2]
            sample_fields = (
                list(sample_rows[0].keys())
                if sample_rows and isinstance(sample_rows[0], dict)
                else []
            )
            state = res.state.value if hasattr(res.state, "value") else str(res.state)
            parser_state = parsed.get("parser_state")

            # Stale fallback never counts as live populated usable data.
            if state == "STALE_FALLBACK":
                verdict = "STALE_FALLBACK_NOT_USABLE"
            elif usable_rows > 0 and state in {"RAW_ARCHIVED", "NO_DATA_NOW"}:
                # NO_DATA_NOW with rows is unusual; treat positive parse as usable only when archived live.
                verdict = (
                    "DIRECT_USABLE_POPULATED"
                    if state == "RAW_ARCHIVED"
                    else "CONDITIONAL_EMPTY"
                )
            elif usable_rows > 0:
                verdict = "DIRECT_USABLE_POPULATED"
            elif state == "NO_DATA_NOW" or parser_state == "WAIT_EMPTY_PARSE":
                verdict = "CONDITIONAL_EMPTY"
            else:
                verdict = "NOT_USABLE"

            row = {
                "source_key": key,
                "url": res.url,
                "state": state,
                "status_code": res.status_code,
                "record_count_raw": res.record_count,
                "usable_rows": usable_rows if state != "STALE_FALLBACK" else 0,
                "parsed_rows_including_stale": usable_rows,
                "parser_state": parser_state,
                "summary": parsed.get("summary") or res.reason,
                "sample_fields": ";".join(sample_fields) if sample_fields else None,
                "sample_row_json": json.dumps(sample_rows, default=str)[:2000]
                if sample_rows
                else None,
                "raw_path": res.raw_path,
                "reason": res.reason,
                "verdict": verdict,
                "data_date": parsed.get("data_date"),
            }
            print(
                " ",
                verdict,
                "rows=",
                row["usable_rows"],
                "parsed=",
                usable_rows,
                "state=",
                state,
                "parser=",
                parser_state,
                flush=True,
            )
            results.append(row)
            if usable_rows > 0:
                (OUT / f"{key}_parsed.json").write_text(
                    json.dumps(parsed, indent=2, default=str)[:500000],
                    encoding="utf-8",
                )
    finally:
        await client.aclose()

    out_json = OUT / "focus_live_retest_results.json"
    out_json.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("WROTE", out_json)
    for item in results:
        print(
            f"{item.get('source_key')}: {item.get('verdict')} "
            f"usable={item.get('usable_rows')} state={item.get('state')} "
            f"parser={item.get('parser_state')}"
        )


if __name__ == "__main__":
    asyncio.run(main())
