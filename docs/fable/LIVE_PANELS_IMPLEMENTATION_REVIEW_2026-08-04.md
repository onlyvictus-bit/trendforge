# Live Panels Implementation Review — 2026-08-04

## Outcome

M1-M3 are implemented in code. M4 is verified except for production-database activation and an open-market browser observation. The feature remains intentionally disabled and the real SQLite projection has not been created because production-database migration requires separate approval.

## Implemented

- Ten P0 live adapters on the existing `AsyncEndpointClient` fetch/archive plane.
- `trendforge.livePanels.v1` contract with current trading date, `dataAsOf`, age, source diagnostics, panel state, and bounded inventory overlay.
- Exact Sector, Consensus, and Screener critical-source sets.
- 300-second hard gate, wrong-day/future-date quarantine, 500 rows/source, 3,000 total rows, and 2 MiB response target.
- Kill switch default-off, concurrency 3, single-flight, source cooldown, 15/30-minute global breaker, pre-open/open/closed/holiday handling, 120-second visible-session scheduler, and 48-hour projection retention.
- Localhost API route and port-8080 CORS allowance.
- SPA clone-and-overlay controller; catalog inventory is not mutated and stale calculation records are removed.

## Observed evidence

- `node tests/live_panels.test.js`: PASS.
- All ten inventory-app Node suites: PASS, including Consensus/Nifty, Screener financial golden, seven-feed enrichment, sector, and collapse UI tests.
- `node --check live_panels.js` and `node --check app.js`: PASS.
- Python AST parse for `live_panels.py`, `main.py`, and `test_live_panels.py`: PASS.
- Isolated `D:\TrendForge\.venv` created from pinned `backend/requirements-dev.txt`.
- Focused backend suite: `10 passed`; Ruff: PASS; mypy: PASS.
- Disabled HTTP route: 200 with `WAIT_DISABLED`, empty overlay, and no client/database work.
- Full legacy backend suite: `538 passed / 24 failed`. The failures are outside this feature and include existing workbook-hash drift, absent `pytest-asyncio`, changed legacy NSE seed expectations, and sandbox-blocked database/parquet tests.
- Bounded real-network smoke test populated all ten configured sources: gainers 20, losers 20, volume gainers 25, most-active volume 20, most-active value 20, all indices 139, OI spurts 213, most-active underlying 213, large deals 296, pre-open F&O 208.
- Closed-market truth gate: all three panels `MARKET_CLOSED`; intraday rows `STALE` (>300s), prior-day large deals `QUARANTINED`, and pre-open explicitly `SESSION_CONTEXT` rather than `FRESH`.
- Browser at `http://localhost:8080/` with API inactive: three OFFLINE badges; Sector data unavailable; Consensus 0 active boards / 0 symbols; Screener no rows. No cached price, score, or vote leakage was observed.
- Browser console: no JavaScript errors; expected fail-closed API-unavailable warning only.

## Not yet verified or activated

- No migration was run against `D:\TrendForge\data\trendforge_research.db`.
- No open-market <=300-second browser observation is possible after market close.
- `TRENDFORGE_LIVE_PANELS_ENABLED` remains false by default.

## Verdict

**VERIFIED WITH CAVEATS; ACTIVATION BLOCKED BY SEPARATE CONSENT.** Frontend fail-closed behavior, backend contract/safety tests, and real-source normalization are verified. Production activation still requires approval for the bounded projection migration and localhost service start.
