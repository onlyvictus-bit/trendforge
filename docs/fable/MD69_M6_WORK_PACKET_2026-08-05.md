# MD69-M6 Work Packet — Verification, Documentation, and Safe Dry Run

Status: **COMPLETE — VERIFIED WITH CAVEATS**

## Intent and ceiling

INTENT: adversarially verify M1-M5, execute one deterministic no-network run
through the real registry/service/store/scheduler path, retain sample
manifest/status evidence, classify full-suite failures honestly, and update the
project map.

M6 must not fetch a market URL, migrate the production database, start a
background scheduler, change scoring/voting, or activate broker/order behavior.

## Done criteria

1. Fixture runner cannot reach `requests` or `httpx` and still completes.
2. Sample manifest has exactly 69 unique entries and sample status has 69 health
   rows.
3. Registry remains provisional and not activation-ready.
4. Focused and full backend suites, frontend suites, lint and compilation are
   observed; inherited failures are separated from new regressions.
5. Exact commands, scope files, caveats, rollback and M7 gate are documented.

## Observed evidence

The deterministic runner used the real M1 registry, M2 store, M3 service and
M4 scheduler with `NoNetworkFixtureTransport`. Tests patched both `requests`
and `httpx` network entry points to raise.

```text
M6 dry-run tests: 2 passed
combined MD69 M1-M6 focused suite: 89 passed, 1 warning
full TrendForge backend: 622 passed, 8 failed, 2 warnings
frontend Node suites: 10 passed
Ruff over all MD69 code/tests: All checks passed
Python compilation over all MD69 code/tests: PASS
```

Safe-run evidence:

```text
registry sources / manifest unique entries / health rows: 69 / 69 / 69
due / completed fixture sources: 25 / 25
network mode: FIXTURE_ONLY_NO_NETWORK
schedule authority / activation ready: PROVISIONAL / false
report SHA-256: 748DB2E736ABB7323491587DB3382A1D768A4C2AA147C1AA36CB6D8A4F572E2C
manifest SHA-256: 0817CCC5F33BE2E2F1062518A795F184C1F18F3A6D9C9B03B227AF55B901F467
```

Evidence root: `docs/fable/evidence/md69-m6-20260805/`.

The eight full-suite failures are outside MD69 files and match recorded
pre-MD69 failure families: legacy NSE seed-route expectations, one async test
without the asyncio plugin, and current workbook/source-map hash drift. The
pre-MD69 run had 24 failures; current environment reproduced eight of those
families and no MD69 focused test failed. Therefore the application-wide suite
is not clean and this milestone is not represented as an unconditional pass.

No production DB was opened for migration, no market URL was called, no
background process was started, and M7 remains blocked by provisional schedules
and its separate activation approval.

Safety audit caveat: the legacy full backend suite updated the filesystem mtime
of `data/trendforge_research.db`. A subsequent SQLite `mode=ro` inspection found
neither MD69 migration version, none of the six MD69 tables, and therefore zero
MD69 production rows. No Python/uvicorn background process remained running.
