"""Probe NSE option-chain with multi-step cookie warm (no CAPTCHA bypass)."""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

OUT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\loop1_option_chain"
)
OUT.mkdir(parents=True, exist_ok=True)

BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def main() -> None:
    results: list[dict] = []
    with httpx.Client(headers=BROWSER, timeout=40.0, follow_redirects=True) as client:
        seed_pages = [
            "https://www.nseindia.com/",
            "https://www.nseindia.com/market-data/live-equity-market",
            "https://www.nseindia.com/option-chain",
            "https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE",
        ]
        for url in seed_pages:
            try:
                response = client.get(
                    url,
                    headers={
                        "Accept": (
                            "text/html,application/xhtml+xml,application/xml;q=0.9,"
                            "image/avif,image/webp,*/*;q=0.8"
                        ),
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                    },
                )
                print(
                    "SEED",
                    response.status_code,
                    url,
                    "cookies=",
                    sorted(client.cookies.keys()),
                    "len=",
                    len(response.content),
                )
            except Exception as exc:  # noqa: BLE001
                print("SEED FAIL", url, type(exc).__name__, exc)
            time.sleep(1.5)

        api_urls = [
            "https://www.nseindia.com/api/option-chain-equities?symbol=RELIANCE",
            "https://www.nseindia.com/api/option-chain-equities?symbol=TCS",
            "https://www.nseindia.com/api/option-chain-equities?symbol=INFY",
            "https://www.nseindia.com/api/option-chain-equities?symbol=NIFTY",
            "https://www.nseindia.com/api/option-chain-equities?symbol=BANKNIFTY",
            "https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol=NIFTY&expiry=",
            "https://www.nseindia.com/api/option-chain-v3?type=Equity&symbol=RELIANCE&expiry=",
            "https://www.nseindia.com/api/allIndices",
            "https://www.nseindia.com/api/quote-equity?symbol=RELIANCE",
            "https://www.nseindia.com/api/live-analysis-variations?index=gainers",
        ]
        for url in api_urls:
            response = client.get(
                url,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://www.nseindia.com/option-chain",
                    "Origin": "https://www.nseindia.com",
                    "X-Requested-With": "XMLHttpRequest",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                },
            )
            name = (
                url.split("/api/")[-1]
                .replace("?", "_")
                .replace("=", "-")
                .replace("&", "_")[:90]
            )
            path = OUT / f"api_{name}.bin"
            path.write_bytes(response.content)
            row: dict = {
                "url": url,
                "status": response.status_code,
                "bytes": len(response.content),
                "path": str(path),
                "head": response.content[:180].decode("utf-8", errors="replace"),
            }
            try:
                payload = response.json()
                row["payload_type"] = type(payload).__name__
                if isinstance(payload, dict):
                    row["keys"] = list(payload.keys())[:20]
                    records = payload.get("records")
                    if isinstance(records, dict):
                        data = records.get("data")
                        row["records_data_len"] = (
                            len(data) if isinstance(data, list) else None
                        )
                        row["underlyingValue"] = records.get("underlyingValue")
                        row["timestamp"] = records.get("timestamp")
                    # also check filtered data
                    filtered = payload.get("filtered")
                    if isinstance(filtered, dict) and isinstance(
                        filtered.get("data"), list
                    ):
                        row["filtered_data_len"] = len(filtered["data"])
            except Exception as exc:  # noqa: BLE001
                row["json_error"] = f"{type(exc).__name__}: {exc}"
            results.append(row)
            print(
                "API",
                response.status_code,
                len(response.content),
                row.get("records_data_len"),
                url,
            )
            print(" ", row.get("head", "")[:120])
            time.sleep(1.2)

    (OUT / "probe_summary.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("WROTE", OUT / "probe_summary.json")


if __name__ == "__main__":
    main()
