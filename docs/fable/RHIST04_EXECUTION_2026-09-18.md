# R-HIST-04 execution record — M1B exact-H1 reader cutover (2026-09-18)

Branch: `feat/rhist04-m1b-reader-cutover` (local only, tracking
`origin/fix/retention-evidence-safety`).
Baseline: commit `72467e0a7d4fe6f922f12c8e12e3647a30bff899`,
tree `6133e6b4fad27e6a1926eff9eb3b785b47163e9a` (both independently
re-verified against GitHub before any edit; worktree was clean).
No commit, no push, no PR, no merge, no deployment, no real-data migration.

## Requirements

R-HIST-04 master: `docs/HISTORICAL_DATA_RETENTION_AND_ML_MEMORY_PLAN.md`
(R-HIST-04 section + safety invariants 1–11). M1B goal: governed readers
resolve `content_hash` H1 through one canonical resolver; legacy locators
become provenance only; no H2/latest substitution; `BLOCKED_INPUT` preserved.

## Changed files

```text
backend/trendforge_api/retention_tiering.py          NEW (canonical resolver + 0024 catalog)
backend/trendforge_api/market_data_store.py          facade + schema wiring (object_path_for_hash kept)
backend/trendforge_api/r16_retention.py              _verify_objects via resolver (error strings preserved)
backend/trendforge_api/market_data_alignment.py      manifest entries via resolver
backend/trendforge_api/derived_market_outputs.py     _load via resolver
backend/trendforge_api/fii_stock_signals.py          loader via store.read_object_exact
backend/trendforge_api/market_data_parameters.py     fanout via resolver (size bound kept)
backend/trendforge_api/openalgo_replay.py            _read_verified_object via resolver (ValueError kept)
backend/trendforge_api/selection/cash_a1_staging.py  bytes via resolver, raw_path stays provenance
backend/trendforge_api/selection/cash_a2_identity.py ban bytes via resolver
backend/trendforge_api/selection/cash_post_commit.py _read_content via resolver + exact availability gate
backend/trendforge_api/selection/tradability.py      restriction bytes via resolver
backend/tests/test_rhist04_m1b_reader_cutover.py     NEW (23 tests)
backend/tests/test_rhist04_m1b_static_gate.py        NEW (verifier enforcement)
backend/tools/verify_m1b_cutover.py                  NEW (static gate script)
backend/tests/test_fii_stock_signals.py              Store doubles -> read_object_exact
backend/tests/test_tradability_sources.py            FakeStore doubles -> read_object_exact
docs/fable/RHIST04_EXECUTION_2026-09-18.md           NEW (this record)
```

## Test-first evidence

New M1B suite RED before implementation (`ModuleNotFoundError:
retention_tiering` at collection), then per-behavior RED for legacy
corruption/escape/quarantine paths during construction; GREEN after the
minimal resolver (23 tests: 22 passed + 1 platform symlink skip at last
count, including the cash HOT-loss BLOCKED_INPUT test).

## Decisions

- One canonical resolver (`RetentionTieringStore`); no duplicate implementations.
- Reads never write (missing catalog table = no replicas, never auto-created
  on read paths).
- Returned buffers are themselves hash-proven (no live-handle TOCTOU).
- Legacy compatibility only with zero replica rows + no-follow + root
  containment + size + SHA-256 proof.
- R16 coverage error strings preserved exactly (MISSING/DAMAGED/HASH_MISMATCH
  mapping) so 03E/03F oracles keep their meaning.
- OpenAlgo keeps raising ValueError (existing contract, asserted by r17 tests).
- `object_path_for_hash` kept for provenance/diagnostics; static gate forbids
  governed-reader use.
- Objects-root discovery via `rhist04_store_meta` (first writer wins);
  unknown root fails closed, never silently uses an unrooted path.
- Availability probe never raises and never substitutes.
- CAS state transitions carry `state_version`; worker-epoch fencing is M1C scope.
- Only RAW representation in M1B; compressed representations rejected until M5.
- RETIRING replicas do not satisfy reads (fail closed during transition).

## Unexpected findings

- Scoped single-producer PASS baselines do not apply here (carried learning).
- `test_r17_e_corrupted_raw_object_fails_replay` pins ValueError("content hash
  mismatch") — resolver OSError is translated at the OpenAlgo boundary rather
  than weakening the test.
- PowerShell `Measure-Object -Line` undercounts file lines; git/python newline
  counts are authoritative (carried learning, no action).
- Pre-existing Ruff E402s in `backend/tools/` (build_gap112/export scripts)
  are untouched; canonical CI scope (`trendforge_api tests`) is clean.

## TWINS searches

- `object_path_for_hash` / `market_data_objects` project-wide: 10 governed
  readers migrated + s8 routing COUNT kept (embraces only existence, reads no
  bytes) — enforced ongoing by `tools/verify_m1b_cutover.py`.
- `except Exception` in new code: exactly one site
  (`exact_object_available`), mapping to False (fail-closed), never success.
- Destructive surface in `retention_tiering.py`: none (no shutil/replace/
  unlink/rename/move/delete) — enforced by the static gate.

## Unverified items

- Symlink-rejection test skips where the platform forbids symlink creation
  (logic reviewed; containment+rehash still protect).
- Full backend regression / frontend / Mypy delta: pending (ladder below).
- M1C+ not started. LIVE-DATA-VERIFIED = NO. PRODUCTION-ACCEPTED = NO.
  Trading authority unchanged.

## Acceptance-gate checklist (M1B)

- [x] baseline re-verified (72467e0 / 6133e6b)
- [x] guarded source check (baseline files absent → reconstruction, no forcing)
- [x] TDD RED observed, GREEN observed (23 tests)
- [x] static verifier PASS + enforced in-suite
- [x] affected existing suites green (r16 57/57; batch details below)
- [x] full backend regression: 1813 passed, 1 skipped (platform symlink),
      0 failures, 2 warnings, 3226.92s (= 1790 baseline + 23 M1B + 1 gate)
- [x] compile full (`compileall trendforge_api tests`): PASS
- [x] Ruff canonical scope (`trendforge_api tests`): clean (pre-existing
      tools/ E402s untouched, outside CI scope)
- [x] frontend npm test: PASS (all suites incl. 220/220 acceptance)
- [x] Mypy: 510 errors / 70 files / 278 checked (the +1 file is the new
      resolver with zero attributed errors) — NOT A PASS, zero M1B delta
- [x] adversarial review (13 lenses, all hold) + final TWINS (0 production
      `object_path_for_hash` callers; remaining `.object_path` uses are
      provenance writes/conditions/manifest reads only)
- [x] M1B accepted locally on scratch evidence (no commit per authority)

## M1C evidence (2026-09-19) — durable movement journal + fencing + reconciler

Metadata/control-plane only. No bytes copied, moved, deleted, compressed,
restored or repointed. New module `backend/trendforge_api/retention_moves.py`
(migration `0025_rhist04_move_journal`, verified non-conflicting: 0021 taken
by scheduler, 0025 free) + `MoveJournalStore` with own WAL/FULL/FK journal
connections (durability observed, not assumed). `market_data_store.init`
applies the journal schema additively.

TDD: 26-test suite RED (`ModuleNotFoundError: retention_moves`) → GREEN
26 passed, including stale-worker rejection, time-skew immunity, terminal
finality, crash/reopen/reconcile, and 8-thread claim/intent races.
One existing-test pin held without weakening (r17 hash-mismatch ValueError
preserved via OSError translation at the OpenAlgo boundary); two test-only
defects of mine fixed (Windows-absolute locators, Row-vs-dataclass access).

Ladder: M1B suite preserved (23 passed); full backend 1839 passed + 1
platform skip, 0 failures (1777 + 62 across two batches after a 60-min tool
timeout killed the single run — no stuck state, batches partition the suite
exactly once); compile PASS; Ruff canonical scope clean; frontend PASS;
Mypy 510/70/279 NOT A PASS with zero attributed to `retention_moves.py`.
TWINS: journal writes/epochs/destructive-move tokens exist only in
`retention_moves.py`; `.unlink(` hits are pre-existing store paths;
`except Exception` in M1C maps to BLOCKED, never success.

Observed environment note: a `D:\TrendForge` checkout (e2d501b, dirty,
scheduler running against its own research DB) exists outside this worktree;
it was inspected read-only and never touched. All M1C work stayed in the
temp worktree on scratch DBs.

M1C accepted locally on scratch evidence. No commit/push per authority.

## M2A evidence (2026-09-19) — RAW local/scratch HOT→WARM COPY-ONLY

GATE 0 first: new `test_rhist04_m1c_multiprocess_fencing.py` (2 tests) proves
8/4 independent OS processes produce exactly one claim winner and stale
tokens cannot transition. M1C authority holds under real contention.

New module `backend/trendforge_api/retention_copy.py` (~1000 lines):
journal-driven copier (intent → claim → COPY_IN_PROGRESS → stream →
COPIED_UNVERIFIED → readback → catalog VERIFIED → DESTINATION_VERIFIED),
capability probe, deterministic destination identity, crash-injection seams,
fenced failure recording. Additive `register_verified_replica` on the
tiering store (same deterministic ID scheme as adopt). Ends at
DESTINATION_VERIFIED; SOURCE_REMOVAL_PENDING/COMPLETED structurally
unreachable (foreign-state refusal, no deletion API exists).

Faults found while building (all fixed at source, tests kept honest):
- Windows CRT text-mode translation corrupted binary streams (found by the
  1 MiB test): O_BINARY on every data fd in copier + tiering resolver.
- Read-only handles cannot fsync on Windows: fsync moved onto the write
  handle before close.
- Unclosed temp fd blocked atomic publish on Windows: single-ownership
  close discipline with quiet-close helper.
- Duplicate `_record_failure_unless_untouched` definition (caught by Mypy
  as the single M2A-attributed error; removed, back to zero delta).

TDD: 42-test matrix RED (collection) → GREEN 42 passed + 2 platform symlink
skips. No existing test weakened (r17 ValueError pin held; doubles migrated
by API, assertions intact).

Ladder: M1A/M1B/M1C preserved (93-test combined file run green); affected
reader/pipeline suites green; full backend 1883 passed + 3 skipped,
0 failures (1821 + 62 across the proven two-batch partition); compile PASS;
Ruff canonical scope clean; frontend PASS; Mypy 510 errors / 70 files /
280 checked — NOT A PASS, zero M2A-attributed errors.

Destructive audit: copier unlink/rmdir confined to scoped temp/probe
cleaners (test-enforced); os.replace only for temp→final atomic publish
(pre-checked absent); no move/delete/retire APIs. TWINS: no second market
mover; `delete_research_record` (storage.py) is a pre-existing unrelated
subsystem, untouched.

M2A accepted locally on scratch evidence. No commit/push per authority.
M2B (crash/durability/fencing sweep) not started. LIVE-DATA-VERIFIED = NO.
PRODUCTION-ACCEPTED = NO. Trading authority unchanged.

## CI finding + fix (PR #7, run 35432686869)

Exact-head CI reported 1 failed / 1885 passed:
`test_source_path_replacement_during_copy_fails_closed` — DID NOT RAISE on
Ubuntu. Root cause: a post-open path swap is a no-op on POSIX (the open fd
pins the original inode, so the copy is byte-correct and legitimately
succeeds); on Windows the same swap is refused by file locking, so the old
test passed locally for the wrong reason. This was a platform-fragile test
expectation, not a production defect. Fix: split into a deterministic
pre-open swap test (expects SOURCE_CHANGED_DURING_COPY everywhere) and a
post-open test asserting the true invariant (H2 bytes never land as the H1
copy, either via failure or via byte-exact success). Follow-up run:
43 passed + 2 platform skips.
