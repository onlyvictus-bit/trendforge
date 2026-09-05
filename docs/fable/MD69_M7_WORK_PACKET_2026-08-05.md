# MD69-M7 Work Packet — Production Activation

Status: **COMPLETE — VERIFIED WITH PROVISIONAL-SCHEDULE CAVEAT**

## Approved intent

The user explicitly approved provisional production activation after the risks
were explained. Activate one Windows foreground scheduler owner after a
SQLite-consistent backup and additive schema initialization.

## Safety boundary

- Registry evidence remains `PROVISIONAL`; status and manifests must say so.
- Activation requires both `MARKET_DATA_69_ENABLED=1` and the explicit
  `MARKET_DATA_69_PROVISIONAL_OVERRIDE=1` operator override.
- Keep one scheduled-task instance, SQLite lease protection, fail isolation,
  last-good retention and holiday/session rules.
- No broker, quantity, order or external-write trading path.

## Done criteria

1. Consistent database backup exists and its hash is recorded.
2. Only additive MD69 migrations/tables are installed.
3. One Windows scheduled task starts the foreground collector automatically at
   user logon and ignores duplicate starts.
4. Running process, task state, status projection and first actual acquisition
   attempts are observed.
5. Stop/rollback instructions and remaining provisional-cadence caveat are
   documented.

## Observed activation

```text
backup: D:\TrendForge\data\backups\trendforge_research_pre_md69_m7_20260805_170202.db
backup SHA-256: B9EFD9B74372A0F5F3C932032DB8A632AC2436657AEC7FFF2646EF2B7EB3E757
backup integrity: ok
migrations: 0020_market_data_69_store, 0021_market_data_69_scheduler
production DB integrity after migration: ok
Windows task: TrendForge MD69 Collector — Running
trigger / duplicate policy: user logon / IgnoreNew
focused M1-M7 tests: 90 passed, 1 warning
```

The first real run stored last-good normalized data for eight sources:

- BSE bhavcopy: 4,933 rows, 2026-08-05
- NSE bhavcopy: 2,416 rows, 2026-08-05
- NSE T2T: 431 rows, 2026-08-05
- NSE PR snapshot: 2,476 rows, 2026-08-05
- NSE F&O bhavcopy: 32,322 rows, 2026-08-04
- MCX bhavcopy: 146 rows, 2026-08-04
- NSE large deals: 103 rows, 2026-08-04
- NSE FII/DII: 2 rows, 2026-08-04

The live observation also found and fixed an EOD busy-retry defect. Incomplete
or unpublished EOD sources now wait 15 minutes before another attempt, and a
20-second observation showed no extra attempt, run, or manifest write. Source
failures remain isolated and retain last-good data.

## Stop and rollback

Pause automatic collection without deleting anything:

```powershell
Stop-ScheduledTask -TaskName "TrendForge MD69 Collector"
Disable-ScheduledTask -TaskName "TrendForge MD69 Collector"
```

Re-enable later with `Enable-ScheduledTask`, then `Start-ScheduledTask`.
Database restoration from the recorded backup must be done only after stopping
the task and remains a separate destructive operation.

## Honest caveat

Automatic fetching is active, but refresh times still carry
`scheduleAuthority=PROVISIONAL` and `activationReady=false`. The user approved
that override. It does not make provisional timing official or guarantee that
every source publishes usable data on every cycle.
