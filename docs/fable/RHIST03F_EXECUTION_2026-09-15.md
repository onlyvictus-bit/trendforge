# R-HIST-03F execution record — fault, replay, concurrency, golden acceptance

This record executes `../R-HIST-03F_FAULT_INJECTION_CONCURRENCY_GOLDEN_ACCEPTANCE_BUILD_PLAN.md`
under the master fault-acceptance directive. It is not a trading, model-approval, or execution plan.

## Status

```text
R-HIST-03F = IN PROGRESS (M0)
FULL R-HIST-03 = NOT COMPLETE
LIVE-DATA-VERIFIED = NO
PRODUCTION-ACCEPTED = NO
```

## Accepted dependencies (preserved, not reopened)

- 03A/B/C/D ACCEPTED at recorded checkpoints (unchanged).
- 03E ACCEPTED: code `0a514bd`, doc head `7905a63`, doc-head CI `34935106879` SUCCESS,
  final head `f8ee7d4` CI `34935669603` SUCCESS. M0 starts exactly at `f8ee7d4`.
- 03E accepted at its recorded contract. If 03F exposes a cross-stage defect, it is
  recorded as "03E accepted; 03F exposed defect X under scenario Y; 03F repaired X".
- Known stale metadata: PR #6 body still says "03E NOT ACCEPTED / 03F GATED".
  Stale prose is not runtime truth; it is corrected at the final 03F doc stage.
- Known governance risk (preserved): new governed producer requires explicit registry +
  test update (03E case #6 FUTURE). 03F does not claim this solved unless a safe
  mechanism with executable tests is added.

## Test population (M0)

M0 proves the harness pattern on the fastest canonical path:

- `STRATEGY_PROFILE` R18 artifacts via `r18_store.persist_strategy_profile` +
  `finalize_rhist03d_artifact` (same-transaction artifact+intent, `BEGIN IMMEDIATE`,
  CAS-guarded finalize, governed `fault_point` seams).
- `ML_DATASET` persist path for the after-artifact-insert rollback proof
  (`persist_frozen_dataset(..., fault_point="AFTER_ARTIFACT_INSERT")`).
- Full source→R18 golden population (S8/R16/DATASET/MODEL/PROFILE/AUDIT) is M1 scope
  and reuses the accepted 03E source-to-end builders; M0 does not duplicate the pipeline.

## Fault matrix (IDs stable across milestones)

Crash (`Cxx` = plan §6 point; `F-*` = master directive):

| ID | Fault | Expected persisted state | Expected coverage | Recovery | Milestone |
|----|-------|--------------------------|-------------------|----------|-----------|
| F_GOLDEN_00 | none (baseline) | full graph APPLIED, 1 semantic ref each | PASS, stable manifest + reportHash | restart preserves identities | M0 |
| F_CRASH_01 | before artifact txn | nothing persisted | EMPTY, no phantom | n/a | M0 |
| F_CRASH_02 | inside artifact txn (AFTER_ARTIFACT_INSERT / enqueue raises) | artifact+outbox+link absent (rollback) | EMPTY | n/a | M0 |
| F_CRASH_03 | after COMMIT, pre-dispatch | artifact+PENDING, hidden from governed reads | PENDING_RETENTION, non-PASS | reconcile → APPLIED, same identities | M0 |
| F_CRASH_04 | authority ok, crash before APPLIED ack (`AFTER_AUTHORITY_REGISTERED`) | ref exists + outbox PENDING | non-PASS | redispatch converges, 1 semantic ref | M0 |
| F_CRASH_05 | APPLIED, visibility not finalized | staged publication hidden | non-PASS | finalize resumes | M1 |
| F_CRASH_06 | during S8 publication finalization | staged only | non-PASS | resume | M1 |
| F_CRASH_07 | during R16 finalization | staged only | non-PASS | resume | M1 |
| F_CRASH_08 | during R18 finalization (BEFORE_DISPATCH/AFTER_OUTBOX_APPLIED/AFTER_PARENT_PROOF/AFTER_LINK_APPLIED/BEFORE_LOCAL_COMMIT) | per-seam staged state | non-PASS | idempotent re-finalize | M1 |
| F_CRASH_09 | restart after every durable boundary | identities stable | agrees with direct oracle | deterministic resume only | M1 |
| F_REPLAY_01/02 | same intent / APPLIED redispatch | same event+ref, no duplicate | unchanged | n/a | M0 |
| F_REPLAY_03/04/05 | publication/R18/source replay | same identities | unchanged | n/a | M1 |
| F_REPLAY_06 | same id, changed material | REJECT immutable repoint | non-PASS/blocked | never overwrite | M0 |
| F_RACE_01..08 | concurrent dispatch/finalize/audit/reconcile | 1 semantic ref, convergence | coherent, never false PASS | idempotent convergence | M2 |
| F_IO_01..05 | lock/unavailable store/object failure | no partial/false-complete | non-PASS, retryable stays PENDING | canonical retry | M2 |
| F_TAMPER_01..12 | outbox/payload/parent/member/hash tamper | blocked before authority/use | non-PASS | never repair-on-read | M2/M3 |
| cross-store | external orphan/missing/wrong-hash/unavailable | declared audit non-PASS | non-PASS, heals on removal | legitimate removal only | M3 |
| cleanup | referenced survives, unreferenced deletable | protected roots intact | honest transitional state | n/a | M3 |
| invention | H1 missing, H2 latest available | BLOCKED, no substitution | non-PASS | never | M3 |

Scenario status values: `PROVEN` (executable test green) / `CODE-INSPECTED ONLY` /
`NOT APPLICABLE + reason` / `MISSING`. Acceptance requires zero MISSING mandatory cases.

## Golden manifest (M0)

`GoldenGraphManifest` per golden build (deterministic order, fixed `NOW`):

```text
profiles: [{profile_id, version, content_hash, event_id, reference_id}]
outbox: {event_id: status}
authority: {reference_id: {type, artifact_hash}}
coverage: {expectedCount, coveredCount, coverage, orphans, blocking, verdict, reportHash}
```

Non-semantic exclusions (by contract): `applied_at`, `auditAt`, attempt counters.
Semantic (never excluded): artifact/version/lineage/content hashes, reference/
publication/event IDs, dataset membership, publication members.

## Recovery rules

- Resume known deterministic PENDING work only (`reconcile_pending_coverage`,
  redispatch, re-finalize). Never infer parents, never use latest data, never
  fabricate evidence, never rewrite immutables, never delete bad rows for 100%.
- Reads never repair: `audit_coverage` stays read-only (M3A-pinned); recovery is explicit.
- Restart simulation: close connections, clear `storage._INITIALIZED_DB_PATHS`,
  reinstantiate registrar/stores, re-read from disk. Calling a method twice is not a restart.

## Dual oracles (every scenario)

- Oracle A (direct): SQL/file/hash inspection of artifact rows, outbox rows,
  reference rows, publication rows, links, states.
- Oracle B (03E): `audit_coverage()` verdict + counts.
- Broken persisted graph + PASS coverage = CRITICAL DEFECT, stop and fix.

## STOP conditions

Golden baseline cannot PASS; artifact commits without same-DB intent; replay repoints
identity; duplicate dispatch creates conflicting ref; authority-crash cannot recover;
PENDING appears healthy; incomplete publication exposed; audit PASS on broken graph;
missing evidence substituted from latest; wrong-hash R18 verifies; external orphan
escapes; read path writes; cleanup deletes protected roots; recovery mutates meaning;
concurrency loses updates; locks cause false completion; any mandatory test fails;
backend/compile/Ruff/frontend fail; new touched-file Mypy diagnostics; code-head or
doc-head CI fails.

## Non-goals

No scanner/direction/entry/stop/target/ranking/routing/regime/options/broker change.
No universal score. No live network (synthetic bytes, scratch DBs, fixed time).
No production database. No installs/commits/pushes without separate approval.

## Milestones

- M0 (this): execution doc + shared harness + golden baseline + F_CRASH_01..04 +
  F_REPLAY_01/02/06 green + R-HIST regression. No production-code change expected.

## M0 evidence (2026-09-15, local, scratch DBs only)

New files (tests + doc only, zero production-code change):

```text
backend/tests/rhist03f_harness.py            shared fixture/manifest/dual-oracle/restart helpers
backend/tests/test_rhist03f_crash_recovery.py  10 scenarios
docs/fable/RHIST03F_EXECUTION_2026-09-15.md    this record
```

Focused: `test_rhist03f_crash_recovery.py` → **10 passed in 9.02s**.
Neighborhood: all R-HIST/retention/R16/R18/S8 suites incl. M0 →
**219 passed, 0 failures in 748.47s** (source-to-end + M3A dominate runtime).

Scenario outcomes:

| ID | Result |
|----|--------|
| F_GOLDEN_00 | PROVEN — 3-profile golden PASS on both oracles, reportHash stable, manifest identical after realistic restart |
| F_CRASH_01 | PROVEN — unknown dispatch KeyError, EMPTY (never PASS), zero rows |
| F_CRASH_02a/02b | PROVEN — injected mid-transaction crash rolls back artifact+intent+link on both dataset and profile paths |
| F_CRASH_03 | PROVEN — PENDING hidden from governed reads (`WAIT_RHIST03D_ARTIFACT_NOT_APPLIED`), coverage FAIL/PENDING, reconcile → APPLIED with identical event/reference IDs, 1 authority ref |
| F_CRASH_04 | PROVEN — `AFTER_AUTHORITY_REGISTERED` leaves ref + PENDING outbox; redispatch converges APPLIED, 1 semantic ref |
| F_REPLAY_01/02 | PROVEN — duplicate persist/finalize/dispatch idempotent, attempts stable, 1 ref |
| F_REPLAY_06 | PROVEN — same event_id + changed material rejected (`immutable`); tampered payload_json blocks dispatch before authority, coverage never PASS |

No defect exposed by M0; 03E checkpoints stand unmodified. Statuses above are the
only matrix rows leaving MISSING; all other rows remain M1–M3 scope.

M0 code-head CI: commit `4794b9c`, PR-head run `34980119941` (`pull_request`,
head `4794b9c`) — overall SUCCESS: backend **1736 passed** (1726 + 10 new),
2 warnings, 316.75s; compile PASS; Ruff PASS; frontend PASS; typecheck the
accepted non-blocking legacy failure. PR #6 head == `4794b9c`.

## M1 evidence (2026-09-15, local, scratch DBs only, uncommitted)

New files (tests only, zero production-code change):

```text
backend/tests/test_rhist03f_r18_recovery.py    11 scenarios
backend/tests/test_rhist03f_pipeline_recovery.py  4 scenarios (real pipeline reuse)
```

Focused: `test_rhist03f_r18_recovery.py` + `test_rhist03f_crash_recovery.py` →
**21 passed in ~11s**. `test_rhist03f_pipeline_recovery.py` → **4 passed in ~86s**.

Scenario outcomes:

| ID | Result |
|----|--------|
| F_GOLDEN_S8R16 | PROVEN — real 22-day pipeline graph (1 S8 + 9 decisions + 9 outcomes, all PUBLISHED) PASS on both oracles, reportHash stable, restart-stable |
| F_CRASH_05a/b | PROVEN — AFTER_LINK_APPLIED / BEFORE_LOCAL_COMMIT roll back atomically; re-finalize converges; coverage PASS |
| F_CRASH_05c | PROVEN — crafted split state raises SPLIT_PUBLICATION_STATE; governed reads refuse; coverage never PASS (canonical path cannot create a split) |
| F_CRASH_05d | PROVEN — AFTER_OUTBOX_APPLIED leaves APPLIED outbox + PENDING pair (coverage FAIL/PENDING); re-finalize converges |
| F_CRASH_06a | PROVEN — staged publication survives restart; finalize→publish resumes; re-stage idempotent; zero duplicate members |
| F_CRASH_06b | PROVEN — real-pipeline S8 crash before mark_published leaves persisted row + PROTECTED protection; resume → exactly one PUBLISHED, members unique |
| F_CRASH_07 | PROVEN — real-pipeline R16 commit-without-finalize leaves staged rows hidden; `resume_pending_publications` converges; second resume returns 0; no PENDING left in coverage |
| F_CRASH_08 ×4 | PROVEN — per-type finalize crashes (BEFORE_DISPATCH / AFTER_PARENT_PROOF / AFTER_LINK_APPLIED / BEFORE_LOCAL_COMMIT) recover with identical event/reference/hash IDs, 1 authority ref, idempotent re-finalize |
| honest accounting | PROVEN — parentless APPLIED dataset/model → LINEAGE_MISSING; profile/audit with unverifiable parent → LINEAGE_BROKEN; never PASS |
| F_CRASH_09 | PROVEN — restart after persist / dispatch / finalize preserves identities; PASS |
| F_REPLAY_03/04 | PROVEN — repeat publication finalize and dataset finalize idempotent |

Harness fix (Type A, test-only): `_build_chain` no longer persists (pure builders);
`_persist_upto(chain, target)` stages prerequisites honoring the model→APPLIED-dataset
binding law. No production-code change. 03E checkpoints stand unmodified.
- M1: full source→R18 golden + F_CRASH_05..09 + F_REPLAY_03..05 + golden restart.
- M2: concurrency (F_RACE), storage failures (F_IO), tamper matrix, dual-oracle proof.
- M3: cross-store, cleanup safety, invention-negative, full regression, code-head CI,
  final docs + PR metadata, doc-head CI, FULL R-HIST-03 gate.
