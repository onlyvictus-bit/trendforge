# MD69-M4 Work Packet — Scheduler, Lease, Health, CLI

Status: **COMPLETE — VERIFIED**

## Intent and safety ceiling

INTENT: add one foreground-only scheduler over the MD69 registry/service/store.
It plans only due sources at six IST checkpoints, emits a 69-entry manifest,
tracks EOD completion and health, and uses a SQLite lease for restart safety.

All 69 schedules are still provisional. Real work remains kill-switched and
activation-blocked; tests may explicitly use the provisional fixture policy.
No background service is installed or started and no production DB is migrated.

## Allowed surfaces

- `backend/trendforge_api/market_data_scheduler.py`
- narrow additive command routing in `backend/trendforge_api/cli.py`
- `backend/tests/test_market_data_scheduler.py`
- MD69 campaign/status/validation/review documentation

## Done criteria

1. Slots are exactly 09:00, 09:17, 10:30, 12:30, 13:30, and 15:00 IST.
2. Only due sources reach the service; every completed slot manifests all 69.
3. Holiday/closed rules suppress NSE-session work; late slots are `MISSED`.
4. EOD begins at 15:35 and stops per source only after current-date success.
5. Lease expiry supports restart while concurrent ownership is rejected.
6. Health exposes attempts, failure streak, last success/error, and EOD state.
7. Kill-switch/provisional blocks produce zero service calls.
8. All requested CLI names parse and route through one foreground owner.

## Observed result

- 14 scheduler/CLI tests and 80 combined registry/store/service/scheduler/
  calendar/live-panel tests passed; one dependency warning remains.
- Six IST slots, no-DST offset, due-only calls, 69-entry manifests, holiday
  publisher filtering, immutable missed audits, per-source EOD stop, bulk DB
  reads, restart miss recovery, singleton lease and health were observed.
- Kill-switch and provisional activation gates made zero service calls.
- No foreground loop, background service, or production DB was activated.
