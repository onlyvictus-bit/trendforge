"""Fetch NSE option-chain via real Chromium session (no CAPTCHA bypass)."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\loop1_option_chain"
)
OUT.mkdir(parents=True, exist_ok=True)

URLS = [
    "https://www.nseindia.com/api/option-chain-equities?symbol=RELIANCE",
    "https://www.nseindia.com/api/option-chain-equities?symbol=NIFTY",
    "https://www.nseindia.com/api/option-chain-equities?symbol=BANKNIFTY",
    "https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol=NIFTY&expiry=",
]


def main() -> None:
    results: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.goto("https://www.nseindia.com/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        page.goto(
            "https://www.nseindia.com/option-chain",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        page.wait_for_timeout(3000)
        for url in URLS:
            response = page.request.get(
                url,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://www.nseindia.com/option-chain",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            body = response.body()
            name = (
                url.split("/api/")[-1]
                .replace("?", "_")
                .replace("=", "-")
                .replace("&", "_")[:80]
            )
            path = OUT / f"playwright_{name}.json"
            path.write_bytes(body)
            row: dict = {
                "url": url,
                "status": response.status,
                "bytes": len(body),
                "path": str(path),
            }
            try:
                payload = json.loads(body)
                row["keys"] = (
                    list(payload.keys())[:20] if isinstance(payload, dict) else None
                )
                if isinstance(payload, dict):
                    records = payload.get("records") or {}
                    data = records.get("data") if isinstance(records, dict) else None
                    row["data_len"] = len(data) if isinstance(data, list) else None
                    row["underlying"] = (
                        records.get("underlyingValue")
                        if isinstance(records, dict)
                        else None
                    )
                    row["timestamp"] = (
                        records.get("timestamp") if isinstance(records, dict) else None
                    )
            except Exception as exc:  # noqa: BLE001
                row["error"] = f"{type(exc).__name__}: {exc}"
                row["head"] = body[:200].decode("utf-8", errors="replace")
            results.append(row)
            print(row)
            page.wait_for_timeout(1200)
        browser.close()
    (OUT / "playwright_summary.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("WROTE", OUT / "playwright_summary.json")


if __name__ == "__main__":
    main()
