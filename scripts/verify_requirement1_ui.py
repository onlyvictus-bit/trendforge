"""Synthetic browser QA for requirement 1; no live data, database or broker calls.

Run after installing Playwright and its Chromium browser:
    python scripts/verify_requirement1_ui.py
"""
from __future__ import annotations

import json
import os
import threading
import subprocess
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "ui-verification"


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "frontend"))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    requests: list[tuple[str, str]] = []
    fail_core = False
    envelope = json.loads(subprocess.check_output([
        "node", "-e", "process.stdout.write(JSON.stringify(require('./frontend/tests/snapshot-fixture.js').snapshotFixture()))"
    ], cwd=ROOT))
    history = {
        "schemaVersion": "trendforge.s8-scan.v1", "runId": "s8-old",
        "asOf": "2026-09-01T10:00:00Z", "builtAt": "2026-09-01T11:00:00Z",
        "tradingDate": "2026-09-01", "acceptanceCeiling": "RESEARCH_ONLY",
        "rows": [{"symbol": "OLD", "publicState": "WAIT", "evidenceDirection": "BEARISH"}],
        "lineage": {"r2RunHash": "old"}
    }
    responses = {
        "/api/v1/selection/snapshot": envelope,
        "/api/v1/selection/scans?limit=100": {"runs": [{"runId": "s8-old", "asOf": history["asOf"]}]},
        "/api/v1/selection/scans/s8-old": history
    }

    def respond(route) -> None:
        request = route.request
        url = request.url.split(str(server.server_port), 1)[-1]
        requests.append((request.method, url))
        payload = responses.get(url)
        if fail_core and url == "/api/v1/selection/snapshot":
            payload = None
        route.fulfill(status=200 if payload is not None else 503,
                      content_type="application/json",
                      body=json.dumps(payload if payload is not None else {"detail": {"code": "SYNTHETIC_UNAVAILABLE"}}))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=os.environ.get("TRENDFORGE_QA_BROWSER") or None
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/api/**", respond)
            page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="networkidle")
            # Preserve bootstrap evidence even if the readiness assertion fails.
            (OUTPUT / "initial-diagnostics.json").write_text(json.dumps({
                "pageErrors": errors, "requests": requests,
                "mode": page.locator("#snapshotMode").inner_text(),
                "failures": page.locator("#snapshotFailures").inner_text(),
                "source": "SYNTHETIC_ONLY",
            }, indent=2))
            page.screenshot(path=str(OUTPUT / "initial-snapshot.png"), full_page=True)
            page.wait_for_function("document.getElementById('snapshotMode').textContent.includes('STORED RESEARCH SNAPSHOT')")
            assert page.locator("#headerRowCount").inner_text() == "1"
            assert page.locator("#snapshotAsOf").inner_text() == "2026-09-04T10:00:00Z"
            assert page.locator("#researchDate").is_disabled()
            assert page.locator("#snapshotBundleId").inner_text() == envelope["snapshotId"]
            assert "NOT saved" in page.locator("#s8HistoryPanel").inner_text()
            forbidden = {"/api/v1/selection/attention", "/api/v1/selection/evidence",
                         "/api/v1/selection/structure", "/api/v1/selection/s7-state",
                         "/api/v1/selection/named-activation", "/api/v1/selection/scans/latest",
                         "/api/v1/scanners/native-core", "/api/v1/scanners/lab-bundle",
                         "/api/v1/selection/market-weather", "/api/v1/selection/top10",
                         "/api/v1/selection/evidence-radar"}
            assert sum(url == "/api/v1/selection/snapshot" for _, url in requests) == 1, requests
            assert not any(url in forbidden for _, url in requests), requests
            assert "PIT STATUS UNKNOWN" in page.locator("#q5ValidationLock").inner_text()
            assert page.locator(".lightning > strong").inner_text() == "Fixture examples"
            assert "UNKNOWN" in page.locator("#r18ModelGovernancePanel").inner_text()
            page.screenshot(path=str(OUTPUT / "current-snapshot.png"), full_page=True)
            page.locator("#headerHistory").click()
            page.wait_for_function("!document.getElementById('historyRunSelect').disabled")
            before = len(requests)
            page.locator("#historyRunSelect").select_option("s8-old")
            page.wait_for_function("document.getElementById('historySnapshot').textContent.includes('HISTORICAL SNAPSHOT - NOT CURRENT')")
            assert page.locator("#snapshotRunId").inner_text() == envelope["panels"]["attention"]["runId"]
            assert page.locator("#historySnapshot").inner_text().find("OLD") >= 0
            assert all(method == "GET" for method, _ in requests[before:])
            page.screenshot(path=str(OUTPUT / "saved-history.png"), full_page=True)
            fail_core = True
            page.evaluate("window.TrendForgeSelectionAdapter.load()")
            assert page.locator("#snapshotMode").inner_text().startswith("STALE")
            assert page.locator("#snapshotAsOf").inner_text() == "2026-09-04T10:00:00Z"
            assert page.locator("#confirmedModeChip").inner_text() == "CONFIRMED STATUS UNAVAILABLE"
            assert sum(url == "/api/v1/selection/snapshot" for _, url in requests) == 2, requests
            assert not any(url in forbidden for _, url in requests), requests
            page.screenshot(path=str(OUTPUT / "stale-snapshot.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            layout = page.evaluate("""() => ({
                width: document.documentElement.scrollWidth,
                viewport: innerWidth,
                controlsBottom: document.querySelector('.top-row').getBoundingClientRect().bottom,
                metricsTop: document.querySelector('.ops-metrics').getBoundingClientRect().top,
                historyHeight: document.getElementById('historySnapshot').getBoundingClientRect().height,
                drawerHidden: getComputedStyle(document.getElementById('inventoryDrawer')).display === 'none'
            })""")
            assert layout["width"] <= layout["viewport"], layout
            assert layout["metricsTop"] >= layout["controlsBottom"], layout
            assert layout["historyHeight"] < 844, layout
            assert layout["drawerHidden"], layout
            page.screenshot(path=str(OUTPUT / "mobile-history.png"), full_page=True)
            browser.close()
            (OUTPUT / "browser-report.json").write_text(json.dumps({
                "pageErrors": errors, "requestCount": len(requests),
                "mobileLayout": layout, "source": "SYNTHETIC_ONLY",
                "snapshotRequests": sum(url == "/api/v1/selection/snapshot" for _, url in requests),
                "legacySelectionRequests": [url for _, url in requests if url in forbidden]
            }, indent=2))
            assert not errors, errors
    finally:
        server.shutdown()
        server.server_close()
    print("Requirement 1 browser verification passed (synthetic API responses only).")


if __name__ == "__main__":
    main()
