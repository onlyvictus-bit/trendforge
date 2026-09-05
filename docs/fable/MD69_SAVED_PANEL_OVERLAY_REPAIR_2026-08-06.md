# MD69 Saved Panel Overlay Repair - 2026-08-06

## Intent

Current behavior: the 69-source refresh committed populated normalized objects,
but `TRENDFORGE_LIVE_PANELS_ENABLED=false` returned `WAIT_DISABLED` before the
canonical manifest provider ran, leaving Sector, Consensus, Nifty Filter and
Screener empty.

Requested behavior: a completed timestamped MD69 manifest must remain available
to the three research panels. The live-fetch kill switch must prevent the
legacy network client, but must not hide already downloaded, hash-verified data.

## Decision

- No-build was rejected because it requires a hidden runtime flag and repeats
  the empty-panel failure after restart.
- Enabling the legacy live fetcher was rejected because MD69 is the production
  acquisition plane.
- Implemented the smallest hybrid: `LivePanelsService` remains fail-closed when
  both live fetching and the canonical provider are unavailable. When a
  canonical provider exists, it may project only the committed MD69 manifest;
  it never constructs the legacy fetch client.

No score formula, consensus voter, source registry, downloader or database
schema changed.

## Changed files

- `backend/trendforge_api/live_panels.py`
- `backend/trendforge_api/market_data_alignment.py`
- `backend/trendforge_api/main.py`
- `backend/tests/test_market_data_alignment.py`
- `backend/tests/test_manual_refresh_api.py`
- `D:\trendforge_inventory_app\live_panels.js`
- `D:\trendforge_inventory_app\tests\manual_refresh.test.js`

## Observed verification

```text
red regression tests                  WAIT_DISABLED; MISSED masked good; force not forwarded
focused MD69/panel backend tests      55 passed
frontend panel/golden tests           4 suites passed
Ruff                                  PASS
Python compileall                     PASS
final browser reload                  populated; no new console error
```

Runtime observation against the committed 2026-08-06 manifest:

- API: `CANONICAL_MANIFEST`, 67 source diagnostics, 67 overlay source rows and
  7,284 projected records.
- Sector: 38/38 sectors rendered with saved fetch time.
- Consensus v4: 8 active boards / 60 symbols and BUY/SELL names rendered.
- Nifty Filter: 3 BUY / 3 SELL names rendered.
- Screener v1.3: 200 visible rows from 2,867 extracted symbols.
- State was `STALE`, not `LIVE`, because the displayed inputs exceeded the
  300-second freshness gate. Records remained visible as research evidence.

Full backend run: 626 passed and 25 existing/environment failures. The failures
were outside the two changed files and included production SQLite/report write
permissions, missing async pytest support, Parquet dependency behavior,
inventory hash drift and older endpoint expectation mismatches.

## Twin search

The active backend has one saved-panel disable gate. Historical baseline copies
under the inventory app outputs still contain the old condition but are evidence
artifacts, not runtime code.

## Dynamic and scheduler safety extension

- Both manual and scheduled collection write the same manifest contract; panel
  selection does not depend on the run name or slot.
- A newer audit manifest with no usable entries (`MISSED`, disabled or blocked)
  is skipped, so it cannot hide the most recent populated manifest.
- Manual completion requests `force=true`, making the panel API reread the new
  committed manifest instead of returning a younger cached panel snapshot.
- New successfully normalized registry keys enter the supporting overlay
  without another static source-key edit. They stay `RESEARCH_ONLY` unless an
  explicit, tested critical-source, extractor or Consensus-plugin decision is
  separately approved.
