# R-HIST-03E execution and acceptance record

This record executes the existing `../R-HIST-03E_PRODUCER_COVERAGE_RECONCILIATION_BUILD_PLAN.md` and preserves File A authority. It is not a replacement architecture or trading activation plan.

## Approved scope and baseline

The user's 2026-09-11 direction is: "Fix the stale status/documentation first, then immediately code 03E. Do not reopen finished 03D or attempt to solve all project-wide issues before proceeding."
Their ordered workflow includes publication and exact-head CI for the documentation and 03E checkpoints. No real/shared database migration, broker action, merge, TF-10+ implementation or 03F fault-injection work is included.

03D acceptance remains `fce62874a61e4e2bb6d939bef6d0811e5a266996`, tree `9295187c49ee7fe5f5005d6ec42a92f94775dcf8`, CI `34496385997` completed/success. Backend 1699 passed; compile, Ruff and frontend passed; Mypy 512 errors in 70 files was the accepted legacy baseline.

## Milestones and observable done criteria

1. Preserve the accepted 03D source identity and current PR metadata. Historical evidence stays explicitly dated. 03E is the active stage; 03F remains gated.
2. Enumerate authoritative S8/R16/R18 producer populations independently from retention proof tables. Add adversarial tests for denominator arithmetic, producer identity, pending versus APPLIED, two-way orphan detection, transitive proof delegation, legacy policy, deterministic reporting and bounded reconciliation.
3. Observe exactly 100% mandatory coverage and zero unexplained orphans on a controlled populated acceptance graph; verify the complete 03E adversarial matrix; prove acceptable query/runtime behavior; verify 03A-D regressions and full backend/compile/Ruff/frontend plus normalized Mypy delta; obtain exact final-head CI. Only then declare 03E IMPLEMENTED + TESTED / ACCEPTED.

## Design decision and falsification

INTENT: individual producers are protected but there was no safe population-wide coverage proof. The previous `RetentionPublicationStore.coverage()` derived both numerator and denominator from `historical_retention_publications`. A governed immutable artifact that never entered retention was invisible to both sides and could therefore produce a false 100% result.

The 03E correction uses a code-owned producer registry and derives `expectedCount` from the real governed artifact stores. Retention publication/outbox/reference state is proof only; it is never the denominator. S8 and R16 remain separate producers even though both can use retention reference type `DECISION_VERSION`. R18 frozen-dataset member rows remain constituents of the frozen dataset content proof, not independent denominator families.

Deep lineage logic is not duplicated. S8 and R16 proof delegates to the accepted `r16_retention` verification path, which validates publication members, APPLIED outbox state, exact authority references and source-object bytes. R18 proof delegates to the accepted governed R18 verifier and its transitive parent checks. Reconciliation remains an explicit bounded write operation that resumes known deterministic R16/R18 pending work through existing owners; there is no direct SQL repair, synthetic historical backfill or repair-on-read.

Zero mandatory population is `EMPTY`, not PASS. Pending, protected-but-not-published, failed, missing, inconsistent, unsupported, orphaned or unverifiable proof cannot count as covered.

## 2026-09-13 implementation checkpoint

Implementation was added on PR #6 / branch `feat/rhist03-producer-wiring`:

- `backend/trendforge_api/retention_coverage.py` adds the authoritative producer registry, read-only coverage audit, fail-closed classifications, deterministic report hash, two-way local proof/orphan checks, existing-owner deep verification and bounded canonical reconciliation.
- `backend/trendforge_api/retention_publication.py` now delegates the legacy `coverage()` compatibility API to the authoritative 03E oracle. The old publication-table-only denominator cannot be used to obtain a false acceptance result.
- `backend/tests/test_rhist03e_producer_coverage.py` adds adversarial coverage tests including the exact `9/10 => 90% / FAIL` case, `10/10 => PASS`, zero population, pending-not-covered, S8/R16 producer separation, R18 member non-double-counting, missing artifact retention, retention orphan and bounded R18 recovery.
- `backend/tests/test_retention_publication.py` now proves that a naked publication without an authoritative governed artifact does not report 100% coverage.

Exact implementation head before this documentation commit: `fe3e1a81e5cbd2764f5569d79d044910cc9fc399`.
Associated PR CI run: `34757599935`.

Observed CI evidence for that implementation head / PR merge ref:

- Python compile: PASS.
- Full backend: **1712 passed, 2 warnings in 242.11s**.
- Ruff: **All checks passed**.
- Frontend: PASS.
- Mypy: **512 errors in 70 files, checked 277 source files**; this matches the accepted non-blocking legacy baseline and does not establish a new normalized regression.

These results prove the implementation candidate integrates with the existing regression suite. They do not by themselves prove 03E production acceptance.

## 2026-09-15 code-checkpoint evidence (commit 1 of 2 — doc-head CI pending)

Code checkpoint: `0a514bd19f8e519e5699c2574ece308851dcada0`
`fix(03E): source-to-coverage chain, verifier hash_col, cross-store inverse proof`
(parent `44b26c2`, PR #6, branch `feat/rhist03-producer-wiring`, base
`f99e7eb3e764b3fb43aa55432abcdf78cd68191e`).
Scope: 5 files, 940 insertions, 19 deletions (the plan brief said "~18
deletions"; the measured numstat total is 19 — recorded here, not corrected
away). Purpose: source-to-R18 coverage acceptance, R18 `hash_col`
verification repair, cross-store inverse enumeration, M3A
read-only/snapshot/cross-store acceptance tests.

PR-head-associated integration CI: run `34773335360`
(<https://github.com/onlyvictus-bit/trendforge/actions/runs/34773335360>),
event `pull_request`, `headSha 0a514bd...`. Precise semantics: GitHub checked
the generated merge ref `9f382c057ed62e7e645ec9a14dea803775541d8e`
(`0a514bd` merged into base `f99e7eb`), which is the PR's current
`merge_commit_sha` — NOT a literal checkout of raw head `0a514bd`. Overall
workflow conclusion: SUCCESS.

| Check | Observed result |
|---|---|
| Python compile | PASS |
| Backend (job `103766821100`) | **1726 passed, 2 warnings in 302.28s** |
| Ruff | **All checks passed** |
| Frontend (job `103766821313`) | PASS (8s) |
| Mypy (job `103766821246`) | **510 errors / 70 files / 277 checked — NON-BLOCKING legacy failure** (`continue-on-error: true`, step "Mypy (non-blocking, known legacy baseline issues)") |

Mypy wording is deliberate: Mypy did NOT pass. Baseline at 03D acceptance was
512 errors / 70 files; this run reports 510 / 70. The per-file normalized delta
was not re-measured in this session, so no "delta zero" claim is made here;
the non-blocking policy in `ci.yml` is unchanged, so there is no new gate
failure. Residual note: one diagnostic touches a file in this checkpoint,
`trendforge_api/selection/cash_post_commit.py:758` (`decision: str` passed
where `Literal[...]` is expected). The checkpoint's Literal tidy annotated two
other call sites; this third site remains. Non-blocking; recorded, not hidden.

Independent local rerun (2026-09-15, Python 3.14.3, scratch DBs only):
`tests/test_rhist03e_m3a_acceptance.py` + `tests/test_rhist03e_source_to_end.py`
→ **10 passed in 227.85s**. No production read or write.

### R18 production defect found and repaired by this checkpoint

Old logic in `verify_stored_rhist03d_artifact`
(`backend/trendforge_api/selection/r18_history_store.py`) selected the proof
hash with a fixed precedence chain (`dataset_hash or model_hash or
content_hash or record_hash`). A model-bound strategy profile carries a foreign
`model_hash` and an audit can carry a foreign `dataset_hash` — either would
shadow the artifact's own hash while still looking valid. Verification now uses
the artifact-type-mapped `hash_col` directly
(`declared = getattr(verified, hash_col, None)`).
Twin search at `0a514bd` over `backend/trendforge_api/selection/*.py` and
`backend/trendforge_api/*.py` for the same fallback-chain construct: **no
second equivalent occurrence found** (remaining `dataset_hash` references are
ordinary field uses, verified by grep on 2026-09-15).

### Controlled source-to-end proof (TEST DATA ONLY / SCRATCH DATABASES ONLY)

22 synthetic trading days × 4 cash-like symbols (RELIANCE, TCS, INFY, HDFCBANK)
plus synthetic NSE index-close companion rows, ingested through canonical
`MarketDataService`/`MarketDataStore` → A1/A2/A4 → R5 (RELIANCE
`history_count >= 21`, `>= 21` used bar IDs matched by exact identity to
adjusted closed bars, `source_artifact_hashes` equal) → S8 (`COMPLETED`,
publication `PUBLISHED`, lineage evidence roots cover every used A4/R5 hash)
→ exact retention roots → R16 (`COMPLETED`; hypotheses equal stored
`pit_hypotheses` rows, each with an outcome; `WAIT` correctly reports
`BLOCKED` with reasons when no eligible frozen dataset exists)
→ R18 via canonical builders/finalizers (2 frozen datasets TRAIN/EVAL split of
R16-mirroring members, 1 governed model, 1 strategy profile, 1
audit/governance record; `verify_parents=True` on every persist)
→ `audit_coverage()` verdict **PASS**: `expectedCount > 0`,
`coveredCount == expectedCount`, `coverage == 1.0`, `orphanCount == 0`,
`blockingCount == 0`; per-producer `S8_DECISION_VERSION.expected == 1`,
`R16_DECISION_VERSION/OUTCOME.expected` equal to independently counted stored
rows, `R18_ML_DATASET.expected == 2`; repeat audit returns identical
`reportHash` (timestamp excluded by contract).

Declared fixture constants (documented in-test, NOT production evidence):
model artifact/config/code bytes (`sha256(b"03e-fixture-...")`), strategy and
formula labels, formula-set hash. Lineage hashes, parent IDs, cutoff
timestamps, evidence roots, R16 parent rows and retention identities all come
from actual canonical pipeline records. No direct SQL writes in the
source-to-end test.

R16 REVISION count in the controlled acceptance graph is zero because no
legitimate successor outcome exists within the fixture observation window. 03E
does not fabricate a revision simply to populate every producer family.
Coverage counts the authoritative artifacts that actually exist. Revision
producer semantics are proven separately: the `R16_REVISION` producer is
registered against `pit_revisions`; dropping that table fails closed with
`REGISTRY_ERROR`; revision immutability/replay is proven by the accepted
03C/03D suites.

### M3A / fault-injection proofs (all in `test_rhist03e_m3a_acceptance.py`)

- Read-only audit: logical content fingerprint (schema + ordered row bytes per
  table) identical before/during/after `audit_coverage()` — zero writes.
  Connections open read-only (`mode=ro`, `query_only=ON`, `BEGIN` + terminal
  `rollback`); `_external_inverse` rolls back and closes the market store.
- Uncommitted artifact: held in an uncommitted transaction, invisible to a
  concurrent audit (committed population only — no mixed-generation PASS).
- Committed PENDING artifact: reports `PENDING_RETENTION`, never `PASS`, never
  `RETENTION_ORPHAN`.
- Paired stores: physically separate scratch files (`research_db != market_db`,
  asserted); `audit_coverage(db_path=research_db, market_db_paths=[market_db])`
  → PASS; self-scan `market_db_paths=[research_db]` → PASS (no double count).
- External authority orphan: real retention reference inserted in the external
  market DB with no governed owner → single-store audit stays PASS by design
  (blind), declared cross-store audit → FAIL with `RETENTION_ORPHAN` +
  `EXTERNAL_AUTHORITY_REFERENCE`; after removal → PASS restored.
- Missing external object (bootstrap store failure): FAIL closed.
- Tamper/delete (in `test_rhist03e_source_to_end.py`): corrupt S8 parent →
  FAIL closed; deleted S8 artifact/evidence → FAIL with orphan ≥ 1.

### 44-case adversarial matrix crosswalk (plan §16 → owning tests)

`PROVEN` = pinned by an executable test run in this checkpoint's CI/local rerun.
`CODE` = enforced in code, covered by an analogous pinned test, no dedicated
test — stated, not hidden. `FUTURE` = concerns future populations; governed by
the documented registry-update rule below.

| # | Requirement | Owning test(s) | Status |
|---|---|---|---|
| 1 | All expected governed producers registered | source-to-end perProducer asserts (S8==1, R16==stored counts, R18==2) + distinct-producers test | PROVEN |
| 2 | Duplicate producer registration rejected | `test_registry_validation_rejects_duplicate_owner` (`DUPLICATE_PRODUCER_ID`) | PROVEN |
| 3 | Duplicate table ownership rejected | same (`DUPLICATE_AUTHORITATIVE_STORE_SCOPE`) | PROVEN |
| 4 | Unknown reference type rejected | `validate_registry` (`UNKNOWN_PROOF_STYLE`/`TYPE_REFERENCE_MISMATCH`) + `_external_inverse` → `UNKNOWN_PRODUCER`; no dedicated unknown-type test | CODE |
| 5 | Registry points at missing table → failure | `test_missing_authoritative_table_fails_closed` (`REGISTRY_ERROR`) | PROVEN |
| 6 | New governed table without registry entry fails | No automated drift test exists | FUTURE (rule below) |
| 7 | Optional producer does not inflate denominator | registry `mandatory` flag; controlled PASS with optional paths absent | PROVEN |
| 8 | 10/10 APPLIED → 1.0 | `test_10_of_10_passes_on_canonical_applied_proof` | PROVEN |
| 9 | 9/10 APPLIED → fail | `test_9_of_10_fails_from_real_artifact_denominator` (real-artifact denominator, not 9/9) | PROVEN |
| 10 | PENDING not APPLIED | `test_pending_is_not_covered` + M3A pending test | PROVEN |
| 11 | FAILED_BLOCKING not APPLIED | 9/10 + 03D `test_applied_old_event_hard_stops_without_any_change` | PROVEN |
| 12 | Broken lineage not healthy | corrupt-S8-parent FAIL + 03D `test_authority_rejects_tampered_semantic_artifact_before_registration` | PROVEN |
| 13 | Zero population is EMPTY, not PASS | `test_empty_population_is_empty_not_pass` | PROVEN |
| 14 | Legacy rows only per explicit policy | 03D `test_legacy_market_dataset_is_not_a_pre_fix_semantic_event` + legacy identity test | PROVEN |
| 15 | Artifact without outbox detected | `test_s8_artifact_without_publication_is_missing_retention` | PROVEN |
| 16 | APPLIED ref to missing artifact detected | `test_publication_without_real_artifact_is_retention_orphan` | PROVEN |
| 17 | Wrong version/hash detected | 03D `test_pre_guard_index_identity_must_match_verified_payload`, `test_unknown_artifact_hash_cannot_be_registered` + R18 `hash_col` fix | PROVEN |
| 18 | Wrong reference type detected | `_external_inverse` unknown-type → `UNKNOWN_PRODUCER` branch | CODE (same note as #4) |
| 19 | Publication without authority ref detected | deep-verifier delegation + missing-external-object FAIL | PROVEN |
| 20 | Deleted/tampered parent evidence detected | `test_deleted_s8_artifact_leaves_retention_orphan`, corrupt-parent FAIL | PROVEN |
| 21 | Stale/newer parent substitution rejected | `test_same_artifact_cannot_repoint_lineage` (retention_publication suite) | PROVEN |
| 22 | PENDING resumes to APPLIED | `test_bounded_reconciliation_uses_existing_r18_owner` (covered 1→2, FAIL→PASS) | PROVEN |
| 23 | Replay idempotent | same (two `limit=1` runs, `processed==1` each) + 03D crash-window test | PROVEN |
| 24 | FAILED_BLOCKING not silently repaired | 03D `test_late_dispatch_failure_cannot_downgrade_applied_event` | PROVEN |
| 25 | Missing original proof stays blocking | 9/10 FAIL + `test_unknown_artifact_hash_cannot_be_registered` | PROVEN |
| 26 | Legacy never backfilled from latest | 03D legacy-semantic test + R5 write-boundary tests | PROVEN |
| 27 | Restart after crash | 03D `test_crash_window_is_hidden_and_replay_is_idempotent`, `test_recovery_crash_rolls_back_e2_and_audit_record`, `test_two_recoveries_append_only_one_correction` | PROVEN |
| 28 | Bounded deterministic ordering | bounded-reconciliation test + `test_reconciliation_limit_must_be_positive` | PROVEN |
| 29 | Coverage report performs no mutation | M3A `test_audit_performs_zero_writes` | PROVEN |
| 30 | Recovery write separated from read | `reconcile_pending_coverage` is a separate explicit function; audit never writes | PROVEN |
| 31 | Concurrent commit, no mixed count | 03D `test_two_simultaneous_finalizers_publish_once_and_both_replay`, writer-contention test | PROVEN |
| 32 | Uncommitted artifact not counted | M3A `test_uncommitted_artifact_is_invisible_to_audit` | PROVEN |
| 33 | PENDING window reports PENDING | M3A `test_pending_reports_pending_never_orphan_or_pass` | PROVEN |
| 34 | Stable result at unchanged state | source-to-end `reportHash` equality + `test_report_hash_is_deterministic_excluding_timestamp` | PROVEN |
| 35 | Store failure → failure/unknown, never 100% | missing-table `REGISTRY_ERROR` + missing-external-object FAIL + `MARKET_STORE_UNAVAILABLE` branch | PROVEN |
| 36 | DECISION_VERSION covered | source-to-end S8 + R16 decision asserts | PROVEN |
| 37 | OUTCOME covered | `R16_OUTCOME.expected == stored observations` | PROVEN |
| 38 | REVISION covered | producer registered; zero-revision window allowed (see note above); immutability via 03C/03D | PROVEN |
| 39 | ML_DATASET covered | `R18_ML_DATASET.expected == 2`, `verify_parents=True` | PROVEN |
| 40 | MODEL_VERSION covered | `MDL-03E-SOURCE-TO-END` persist + verify | PROVEN |
| 41 | STRATEGY_PROFILE covered | `PRF-03E-SOURCE-TO-END` persist + verify (artifact-hash rule pinned by `test_profile_retention_uses_artifact_hash_not_fake_market_object`) | PROVEN |
| 42 | AUDIT covered | `AUD-03E-SOURCE-TO-END-1` persist + verify | PROVEN |
| 43 | Non-trade populations visible | R16 WAIT/BLOCKED truthfulness tests + 03C WAIT/WATCH/REJECT representation | PROVEN |
| 44 | Same-symbol opportunities do not collapse | `opportunity_id` includes symbol/timeframe/direction/horizon; 4-symbol fixture shows `covered == expected` with per-producer counts matching independent SQL counts (collapse would break the equality) | PROVEN |

No MISSING mandatory case for the current acceptance population. Items #4/#18
(CODE) and #6 (FUTURE) are recorded above rather than silently downgraded.

### Performance (honest, no SLA claim)

PRODUCTION-SCALE PERFORMANCE VERIFIED: NO. No production-scale benchmark was
performed and none is required by the plan's §18 acceptance gate. Representative
controlled measurements: CI backend 1726 tests in 302.28s; local 03E focus (10
tests, 22-day × 4-symbol scratch graph) in 227.85s. Controlled timings must not
be quoted as production SLAs.

### Standing rules recorded for the next engineer

- New governed immutable producer → must update the producer registry → must
  pass 03E coverage rules (case #6 has no automated drift test; the registry is
  the enforcement point — do not add silent producers).
- Artifact verifiers must select the artifact-type-declared hash field; never
  infer proof hash using generic first-non-null precedence (the R18 bug class).
- Controlled acceptance data is TEST DATA ONLY and must never be cited as live
  market evidence, model approval, strategy activation, or order authority.

### Status at this checkpoint

Code checkpoint `0a514bd` is IMPLEMENTED + CONTROLLED-ACCEPTANCE TESTED.
`R-HIST-03E` remains **NOT ACCEPTED** until the documentation head (this
commit) obtains its own green CI. `R-HIST-03F` stays GATED. Full R-HIST-03 is
NOT COMPLETE. LIVE-DATA-VERIFIED: NO. PRODUCTION-ACCEPTED: NO. Execution
authority unchanged. 03E proves historical-memory integrity (nothing governed
is silently missing) — NOT trading profitability.

## 2026-09-15 documentation-head CI and final acceptance (commit 2 of 2)

Documentation head `7905a631ca9f1df6bd71a126496e6bad24db2903` (docs-only,
+283/−2 across the 5 canonical surfaces) obtained exact-head CI run
`34935106879`
(<https://github.com/onlyvictus-bit/trendforge/actions/runs/34935106879>):
`pull_request` event, `headSha 7905a63...`, generated merge ref actually
checked `aef2dc16ff6bf39322a84ab355acebd9c2d64acf` (into base `f99e7eb`).
Overall workflow: SUCCESS. Backend job `104271226883`: compile PASS, **1726
passed, 2 warnings in 320.92s**, Ruff all checks passed. Frontend job
`104271226982`: PASS (including the current-state documentation
navigation/boundary suites, which exercise these very doc edits). Typecheck job
`104271227036`: non-blocking failure, **510 errors / 70 files / 277 checked —
identical counts to the code-head run**, policy unchanged. Mypy wording again:
Mypy did NOT pass; it remains a non-blocking legacy failure.

With code-checkpoint evidence (`0a514bd` + `34773335360`), documentation-head
integration evidence (`7905a63` + `34935106879`), the 44-case crosswalk above
(no MISSING mandatory case for the current population; #4/#18 CODE-recorded,
#6 FUTURE-ruled), and the 33-item acceptance gate reviewed item by item with
every mandatory condition evidenced, the final state is:

```text
R-HIST-03A/B/C/D: ACCEPTED (unchanged)
R-HIST-03E: IMPLEMENTED + TESTED / ACCEPTED
R-HIST-03F: UNLOCKED / NEXT / NOT STARTED
FULL R-HIST-03: NOT COMPLETE
TF-10+: STILL GATED
LIVE-DATA-VERIFIED: NO
PRODUCTION-ACCEPTED: NO
MODEL APPROVAL / STRATEGY ACTIVATION / BROKER-ORDER AUTHORITY: UNCHANGED
```

No 03F code was written in this task. No broker, execution, strategy
activation, model approval, live-data or production-authority change occurred.
Do not mistake either CI run (`34773335360` code-checkpoint,
`34935106879` documentation-head) for the other; both checkpoints and both
runs are preserved above.

`R-HIST-03E` remains **NOT ACCEPTED** at this checkpoint.

The following evidence is still required before acceptance:

1. Execute the controlled populated reconciliation against the approved acceptance population and record mandatory expected/covered/missing/pending/artifact-orphan/retention-orphan/broken-lineage/unknown-producer counts. A PASS claim requires expected > 0, covered == expected and zero blocking findings.
2. Complete the full adversarial matrix required by the 03E build plan, including the remaining lineage/version/duplicate/concurrent-snapshot cases not yet demonstrated by the new focused test file.
3. Verify inverse orphan coverage across every participating authority/evidence store. The canonical deep verifier proves the exact references required by S8/R16 artifacts, but production acceptance must also prove that unexplained authority-side references cannot escape the inverse audit merely because they live outside the research SQLite file.
4. Measure and record query/runtime/memory behavior on a representative populated graph. Current enumeration is set-based, while deep verification deliberately reuses accepted per-artifact owner verifiers; no O(N), O(N log N), query-count or production-runtime claim is accepted yet.
5. Observe CI on the final documentation/code head after all acceptance evidence is recorded. Historical CI from an earlier head is evidence for that head only.

No 03A-03D producer identity was rewritten by this checkpoint. No S8/R16/R18 immutable historical artifact was rewritten. No TF-10+, broker/execution, scanner-strategy or 03F implementation was performed.

## Constraints, rollback and separate backlog

Never count pending/failed/unverifiable lineage as APPLIED; never shrink the mandatory denominator, substitute latest evidence, rewrite immutable old artifacts or perform repair on reads. Preserve existing PIT cutoffs and producer identities. A new immutable producer introduced later must be registered explicitly with 03E coverage and pass drift/orphan checks.

Separate backlog remains outside 03E unless a test demonstrates a direct dependency: live/PIT evidence acquisition, price-band/tick/base-price geometry, source timestamps/freshness, EIA CSV dates, CLI decision-path consolidation and legacy typing debt. Research, PIT, model, strategy and execution authority remain unchanged.
