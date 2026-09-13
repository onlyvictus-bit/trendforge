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

## Remaining acceptance blockers

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
