# MD69-M1 Work Packet - 2026-08-05

Status: **complete; verified with full-suite caveats recorded in VALIDATION**.

Selected File A requirement ID: `R0` residual source inventory/contracts.

Objective and acceptance ceiling: freeze the exact 69-primary-feed refresh CSV,
compile it with typed YAML profiles into a complete acquisition/parameter/
validation/normalization matrix, and prove the result offline. This is contract
readiness only, not source activation or live-data proof.

Mapped FMR refs: `FMR-001`, `FMR-010`.

Mapped Hybrid sections: four-lane/source-contract detail in sections 15.2,
16.3, 16.12 and 18.4, through File A section 25 only.

Discovery/Options detail tags: none; no discovery, option formula, Greek, or
scanner behavior changes in this milestone.

Local dependency tags: existing `AsyncEndpointClient`, `SOURCE_CATALOG`,
`STRUCTURED_PARSERS`, disclosure/live/market-activity/intraday adapters, and
the unchanged 69-row inventory audit CSV.

Observed source activation and evidence timestamp:

- all 69 CSV schedules are
  `PROVISIONAL_UNVERIFIED_NEEDS_OFFICIAL_WEB_CHECK` as of 2026-08-05;
- compiled `schedule_authority=PROVISIONAL`;
- compiled `activation_ready=false`.

Required fail-closed/public-state ceiling: missing/duplicate registry keys,
hash drift, missing profiles, unknown endpoints/monitors/parsers/adapters,
unprovided parameters, inconsistent reuse modes, or attempted provisional
activation fail compilation. No public research state is promoted.

Focused and adversarial tests:

- exact CSV and primary-key hashes;
- 69 rows, 69 unique keys, exact inventory-key equality;
- 69/69 acquisition, parameter, validator and normalizer coverage;
- existing endpoint/monitor/parser/callable references;
- parameter providers and endpoint fan-out;
- response reuse versus session sharing;
- duplicate/missing/unknown/activation failures;
- patched network entry points prove zero network calls.

Full regression commands:

```text
cd D:\TrendForge\backend
..\.venv\Scripts\python.exe -m pytest tests\test_market_data_registry.py -q
..\.venv\Scripts\python.exe -m pytest tests\test_source_runtime_hardening.py tests\test_exchange_calendar.py tests\test_live_panels.py -q
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe -m compileall trendforge_api tests
..\.venv\Scripts\ruff.exe check trendforge_api\market_data_registry.py tests\test_market_data_registry.py
```

Allowed changed files:

```text
config/source_refresh_registry_69.csv
config/source_refresh_registry_69.csv.sha256
config/source_refresh_profiles.yaml
backend/trendforge_api/market_data_registry.py
backend/tests/test_market_data_registry.py
docs/fable/MD69_M1_WORK_PACKET_2026-08-05.md
docs/BUILD_STATUS.md
docs/VALIDATION.md
```

Pre-edit runtime manifest hash:
`C010A7A847933CFA40C8E202BD910811B85F8E519B7B3471557CC9922C1A8C8B`.

Excluded/postponed behavior: MD69-M2 through MD69-M7, object store, manifests,
database schema/migration, retention deletion, scheduler/CLI activation, live
fetches, panel overlay changes, consensus scoring, screener formula changes,
broker integration, quantities and orders.

INTENT: add a non-networking compiler that proves every approved primary feed
has explicit existing acquisition and normalization ownership without claiming
that provisional publication schedules are official or ready to run.
