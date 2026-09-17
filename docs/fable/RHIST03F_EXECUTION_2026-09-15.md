# R-HIST-03F execution record — fault, replay, concurrency, golden acceptance

This record executes `../R-HIST-03F_FAULT_INJECTION_CONCURRENCY_GOLDEN_ACCEPTANCE_BUILD_PLAN.md`
under the master fault-acceptance directive. It is not a trading, model-approval, or execution plan.

## Status

```text
R-HIST-03F = IN PROGRESS (M0 VERIFIED, M1 VERIFIED, M2 VERIFIED, M3 VERIFIED)
M3 CODE CHECKPOINT = 2e957082bad34829cf9e7bed1487a69399566f42 (pushed)
M3 CODE-HEAD CI = run 35222154939 SUCCESS
FINAL DOC-HEAD CI = PENDING
R-HIST-03F = IMPLEMENTED + CONTROLLED ACCEPTANCE TESTED, NOT YET FORMALLY ACCEPTED
FULL R-HIST-03 = NOT COMPLETE
LIVE-DATA-VERIFIED = NO
PRODUCTION-ACCEPTED = NO
```

(2026-09-17: M0/M1/M2 evidence below is preserved unchanged. M3 evidence is
appended in the "M3 evidence" section at the end of this record.)

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

M1 code-head CI: commit `049fdac`, PR-head run `34989717719` (`pull_request`,
head `049fdac`) — overall SUCCESS: backend **1751 passed** (1736 + 15 new),
compile/Ruff/frontend passed; typecheck the accepted non-blocking legacy failure.

## M2 evidence (2026-09-15, local, scratch DBs only, uncommitted)

New files (tests only, except one minimal production hardening):

```text
backend/tests/test_rhist03f_concurrency.py   11 scenarios (F_RACE_01..08, F_IO_01/02/03/05)
backend/tests/test_rhist03f_tamper.py        18 scenarios (F_TAMPER_* unit classes)
backend/trendforge_api/retention_publication.py  1-claim fix in finalize()
```

Focused: concurrency + tamper → **29 passed in ~23s**.
Regression (finalize neighbors + all 03F): **177 passed, 0 failures in ~423s**.
Ruff + compile clean.

### Defect found and repaired (Type B)

`RetentionPublicationStore.finalize()` claimed `PROTECTED_PENDING_ARTIFACT` when
`applied == len(members)`, ignoring the staged `required_count`. A lost member
row therefore lowered the protection bar instead of blocking (proven by
F_TAMPER_06 red: PROTECTED with applied 1/2). Governed reads and coverage still
refused via the deep verifier (`PUBLICATION_MEMBER_MISMATCH`), so no false
health escaped — but the local claim was wrong.

Fix (1 claim, `retention_publication.py`): protection additionally requires
`applied == required_count`. Legitimate flows always satisfy it (stage writes
both atomically; no production delete path exists).

TWINS: project-wide search for lenient member counting — the deep verifier
(`r16_retention.py:195`) already enforces the strict triple
(members/roots/required/applied); `mark_published` gates on status only, sound
once the claim is fixed. No second occurrence.

### Scenario outcomes (M2)

| ID | Result |
|----|--------|
| F_RACE_01/02 | PROVEN — barrier-aligned duplicate dispatch/register converge: APPLIED, 1 semantic ref, PASS |
| F_RACE_03 | PROVEN — same-lineage racers: exactly one wins; loser ValueError/IntegrityError; stored row immutable |
| F_RACE_04 | PROVEN — reconciler vs dispatcher converge; 1 ref |
| F_RACE_05 | PROVEN — locked dispatch raises loudly (no silent catch pre-authority); PENDING + attempts preserved; retry converges |
| F_RACE_06 | PROVEN — concurrent finalizers converge via CAS path; 1 ref; PASS |
| F_RACE_07 | PROVEN — audits sampled mid-transition are coherent (FAIL or PASS, counts consistent) |
| F_RACE_08 | PROVEN — independent events keep own identities under aligned races |
| F_IO_01 | PROVEN — locked artifact txn: no partial row, no outbox row, EMPTY; works after release |
| F_IO_03 | PROVEN — unavailable authority: FAILED_BLOCKING, never APPLIED, coverage non-PASS |
| F_IO_05 | PROVEN — ghost evidence dispatch fails closed (`refusing unknown run_id`); inverse proof reports RETENTION_ORPHAN FAIL |
| F_TAMPER_01/02/09/10 | PROVEN — outbox payload/column/version/type tampers blocked before authority |
| F_TAMPER_05/08/11/12/38/43 | PROVEN two-layer — naive writes blocked by immutability triggers (IntegrityError, state intact); past dropped triggers, identity/payload/member verifiers refuse (CORRUPT_*/MISMATCH) |
| auxiliary columns | PROVEN ineffective-or-blocked — cutoff/predecessor column lies past dropped triggers do not reach governed readers (verified sealed payload wins); payload rewrites detected |
| F_TAMPER_06/07 | PROVEN — member removal now FAILED_BLOCKING (repaired); ghost-swap FAILED_BLOCKING; coverage never PASS |
| F_TAMPER_42 | PROVEN — same-version semantic rewrite rejected (PROFILE_VERSION_IMMUTABLE) |

Test-harness fixes (Type A, no production impact): barrier-reuse/starvation in
RACE_04/08 replaced with start-gate + work-queue; RACE_03 rebuilt as a true
same-lineage race; RACE_05/IO_05 asserts pinned to lawful behavior (loud
retryable raise; FAILED_BLOCKING receipt, not an exception).

Remaining for M3: pipeline-level tamper probes (R16 parent, market bytes),
cross-store matrix, cleanup safety, historical-invention negative, golden
restart, false-pass search, full regression, code-head + doc-head CI, PR
metadata refresh, FULL R-HIST-03 gate.
- M1: full source→R18 golden + F_CRASH_05..09 + F_REPLAY_03..05 + golden restart.
- M2: concurrency (F_RACE), storage failures (F_IO), tamper matrix, dual-oracle proof.
- M3: cross-store, cleanup safety, invention-negative, full regression, code-head CI,
  final docs + PR metadata, doc-head CI, FULL R-HIST-03 gate.

## M3 evidence (2026-09-17, local scratch DBs + exact code-head CI, uncommitted test work checkpointed at `2e95708`)

New files (tests only, zero production-code change):

```text
backend/tests/test_rhist03f_pipeline_tamper.py    4 scenarios (F_TAMPER_03/04/35/36)
backend/tests/test_rhist03f_crossstore_cleanup.py 6 scenarios (X1-A/X1-B, F_IO_04, X3, C1, H1)
```

### M3 code/test checkpoint

```text
commit:  2e957082bad34829cf9e7bed1487a69399566f42
message: test(03F): complete M3 cross-store and golden recovery acceptance
scope:   2 new test files only (915 insertions, 0 deletions)
         zero production-code change
         zero documentation change in that checkpoint
```

Temporary `backend/dbg_audit*.py` scratch probes were deleted before checkpoint
creation and were never part of the committed deliverable.

### M3 code-head CI (PR-head-associated integration CI)

```text
GitHub Actions: 35222154939
  (https://github.com/onlyvictus-bit/trendforge/actions/runs/35222154939)
PR branch head: 2e957082bad34829cf9e7bed1487a69399566f42
generated PR merge ref (what GitHub tested): 49e96168950848f7a3dc455a23763b02902b4e9f
overall: SUCCESS
```

Do NOT describe this as a literal raw-head checkout: GitHub tested the
generated PR merge ref containing head `2e95708`. Do NOT reuse it as the
final documentation-head run.

| Check | Observed result |
|---|---|
| Backend tests | 1790 passed, 2 warnings, 410.85s |
| Python compile | PASS |
| Ruff | All checks passed |
| Frontend | PASS (11s) |
| Mypy | Non-blocking failure (accepted legacy baseline); NOT A PASS |

### Dual-oracle model (every M3 scenario)

```text
Oracle A: direct persisted-state SQL/file/hash evidence
Oracle B: R-HIST-03E audit_coverage()
```

A broken direct state combined with PASS coverage would have been a critical
defect. No such false PASS was observed. The oracles share the scratch store
files but exercise independent code paths (raw SQL inspection vs the declared
verifier); no stronger independence is claimed.

Baseline note: the full-registry baseline verdict on the single-store eligible
pipeline is FAIL because that builder persists no R18 tables (out-of-scope
REGISTRY_ERROR blockers). Detection is therefore proven by per-artifact
COVERED → typed-fail-closed transitions plus covered-count movement, never by
the top-level verdict alone.

### Scenario outcomes (M3)

| ID | Result |
|----|--------|
| F_TAMPER_03 | PROVEN — required historical market object deleted. Direct oracle: object row absent while retained lineage still references the original hash. Coverage oracle: victim S8 COVERED → LINEAGE_BROKEN/LINEAGE_MISSING/MISSING_RETENTION; coveredCount drops; nothing heals. Corrupt graph never reports healthy. |
| F_TAMPER_04 | PROVEN — stored market bytes corrupted while identity metadata remains (stronger than absence). Direct oracle: actual SHA256 != declared hash AND actual size != recorded size; identity row survives. Coverage: COVERED → LINEAGE_BROKEN/INCONSISTENT_IDENTITY. |
| F_TAMPER_35 | PROVEN two layers — Layer 1 (prevention): normal SQL mutation rejected by the immutability trigger, even a no-op rewrite. Layer 2 (detection): controlled scratch-only trigger bypass, `sourceS8Hash` corrupted while the retained link seal stays original; deep verification non-PASS. This proves prevention + detection, not merely trigger behavior. |
| F_TAMPER_36 | PROVEN — valid-but-wrong parent rejected. D1 = legitimate original decision, D2 = separate legitimate valid retained published decision, O1 = outcome legitimately bound to D1. Fault: O1 parent D1 → D2 (sealed join column + payload `hypothesisId` + parent hash). Evidence: D1 valid, D2 valid, O2 unaffected, all decisions remain COVERED, only victim O1 becomes non-COVERED, coveredCount decreases by exactly one. The verifier proves semantic parent correctness, not merely existence of a valid parent. This protects future outcome statistics, win/loss attribution, strategy evaluation, failure memory and ML labels from cross-decision contamination. No trading-profitability claim is made. |
| C1 | PROVEN both sides — governed evidence after canonical cleanup: file remains, bytes byte-identical, SHA256 unchanged, size unchanged, authority-reference set unchanged. Eligible unreferenced evidence: index row deleted, disk file deleted, object in `deleted_object_paths`. Retention does not mean "never delete anything": governed history stays protected while genuinely eligible unreferenced evidence stays deletable. |
| H1 | PROVEN — no historical invention. Historical decision references H1; H1 becomes unavailable; a later/current valid H2 exists and is available (proven on disk and in index). Observed: S8 publication remains byte-identical (full row, not just lineage); no publication member or lineage reference rewritten to H2; victim remains non-COVERED; canonical parent resolution raises a fail-closed error. H2 DID NOT substitute H1. Permanent invariant: missing historical evidence must remain missing/broken — never missing → latest/current substitute. Required to avoid look-ahead leakage, revision leakage, false backtest knowledge and false model-training evidence. |
| X1-A | PROVEN — healthy restart needs no repair. Healthy graph PASS → restart process owners → NO reconciliation → same semantic manifest → same reportHash → same S8 identity → PASS. Durable healthy history survives restart unchanged. |
| X1-B | PROVEN — PENDING recovery. PENDING event → restart → `reconcile_pending_coverage()` → processed=1 → same event ID → same reference ID → same semantic hash → exactly one authority reference → PASS. Canonical recovery only. |
| F_IO_04 | PROVEN — declared external market store unavailable fails closed. Declared `.db` path missing, database not recreated by the audit, result non-PASS with typed `MARKET_STORE_UNAVAILABLE` / `REGISTRY_ERROR` finding; PASS restored for the healthy declaration. Rule: declared evidence authority unavailable != ignore and PASS. (Windows holds the live scratch DB open, so the unavailable store is a declared-but-missing path — the identical contract path as rename/delete.) |
| X3 | PROVEN — external orphan fails the declared audit, heals on legitimate removal. Healthy paired graph PASS; injected real authority reference (valid object hash, no governed owner) → FAIL with `RETENTION_ORPHAN`, orphanCount ≥ 1, `EXTERNAL_AUTHORITY_REFERENCE` evidence; legitimate row removal restores PASS. No synthetic artifact/backfill was created. |

### M3 defect classification

```text
M3 production correctness defects found: 0
M3 production files changed: 0
```

All M3 defects were Type A test/harness/environment issues (test-only repairs,
never portrayed as product defects):

```text
- tuple fallback in _declared removed (fail-closed contract assert)
- global-interpreter site-packages/tests shadowing isolated via venv (no sys.path hack, no conftest)
- paired-manifest row_factory test repair
- Windows unavailable-store fixture repair (missing .db path, same contract)
- external-orphan fixture correction (run_id=None, matching production row shape)
- F_TAMPER_36 strengthening (unsealed join swap → sealed valid-wrong-parent repoint)
- full-registry finding-map transition baselines (scoped single-producer PASS unattainable)
- X1-B pending-recovery test added (X1-A keeps zero-reconciliation restart)
```

### Environment finding

The global interpreter contained a `site-packages/tests` package shadowing the
repository `backend/tests` namespace. Verification used an isolated venv with
`requirements-dev.txt`, matching CI-style backend execution. No `sys.path`
hack, conftest file or production change was added.

### M3 local test evidence (observed timings, scratch DBs only)

```text
M3 focused:            10 passed (9 in 326.00s + T03 re-run 1 passed in 42.44s
                       after a test-only Row-vs-tuple repair)
full 03F (7 files):    64 passed in 474.16s  (= 10 M0 + 15 M1 + 29 M2 + 10 M3)
03A–03E neighborhood
(20 files):            249 passed, 2 warnings in 715.15s
full backend:          1790 passed, 0 failures, 2 warnings in 1676.38s
Python compile:        PASS
Ruff:                  PASS
Frontend (npm test):   PASS (220/220 + all suites)
Mypy:                  510 errors / 70 files / 277 checked — NOT A PASS
                       (identical to accepted baseline; zero production files
                       touched by M3, so zero new-diagnostic delta possible)
```

Local verification and GitHub verification are different evidence families:

```text
Local M3/full regression: 1790 passed
GitHub PR integration CI: 1790 passed (run 35222154939, merge ref 49e96168...)
```

### Preserved risks and boundaries

Future governed immutable producers still require explicit producer-registry
updates and corresponding tests; automatic registry-drift discovery is not
proven (03E case #6 FUTURE, unchanged). This does not invalidate controlled
R-HIST-03F acceptance.

```text
LIVE-DATA-VERIFIED = NO
PRODUCTION-ACCEPTED = NO
MODEL APPROVAL = unchanged
STRATEGY ACTIVATION = unchanged
BROKER / EXECUTION AUTHORITY = unchanged
```

Trading significance: 03F proves that crashes, races, retries, tampering,
cleanup and restart cannot silently rewrite the historical evidence used by
future backtesting, outcome evaluation, failure memory or ML datasets. It does
NOT prove profitable trading, predictive accuracy, or authorize execution.

### Remaining for formal acceptance

```text
M3 runtime green (this section)
→ docs commit + push (PENDING AUTHORIZATION)
→ exact doc-head CI (PENDING)
→ final 03F/full R-HIST-03 acceptance (PENDING)
→ then refresh PR #6 metadata (stale prose still says 03E in progress / 03F gated)
```
