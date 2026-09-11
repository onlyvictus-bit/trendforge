# R-HIST-03E execution and acceptance record

This record executes the existing `../R-HIST-03E_PRODUCER_COVERAGE_RECONCILIATION_BUILD_PLAN.md` and preserves File A authority. It is not a replacement architecture or trading activation plan.

## Approved scope and baseline

The user's 2026-09-11 direction is: "Fix the stale status/documentation first, then immediately code 03E. Do not reopen finished 03D or attempt to solve all project-wide issues before proceeding."
Their ordered workflow includes publication and exact-head CI for the documentation and 03E checkpoints. No real/shared database migration, dependency install, broker action or merge is included.

03D acceptance is `fce62874a61e4e2bb6d939bef6d0811e5a266996`, tree `9295187c49ee7fe5f5005d6ec42a92f94775dcf8`, CI `34496385997` completed/success. Backend 1699 passed; compile, Ruff, frontend passed; Mypy 512/70, accepted normalized delta zero. Work starts in the clean isolated checkout on `work/rhist03e-coverage`, tracking the existing PR branch. The original dirty D:/TrendForge checkout is preserved. Expected documentation hashes were recorded before edits; git remains the pre-edit content baseline for later source files.

## Milestones and observable done criteria

1. Correct active status/PR metadata, preserve the accepted 03D source identity, and observe CI for the documentation-only head. Historical evidence stays explicitly dated. 03E unlocks; 03F remains gated.
2. Inspect authoritative producers and their real stores/readers. Add failing tests for the existing 03E plan's registry, arithmetic, two-way orphans, full transitive proof, legacy policy, deterministic bounded reconciliation and snapshot consistency. Implement through existing retention/publication/store owners.
3. Observe exactly 100% mandatory coverage and zero unexplained orphans on a controlled populated acceptance graph, verify all 03A-D regression plus full backend/compile/Ruff/frontend and normalized Mypy delta, obtain independent review, publish and observe exact final-head CI. Only then declare 03E IMPLEMENTED + TESTED. 03F remains the subsequent gated stage; its implementation is not part of this record.

## Design decision and falsification

INTENT: individual producers are protected but there is no population-wide coverage proof; 03E must enumerate every mandatory artifact from its authoritative store, verify exact retention and transitive lineage, detect both artifact and reference orphans, and reconcile only existing deterministic pending work through explicit writes.

No-build preserves missing coverage; a manual enum checklist cannot prove authoritative populations. Prefer a code-owned registry with read-only snapshot audit, existing owner verifiers, explicit bounded reconciliation and machine/human diagnostics. A separate retention database or duplicate publication/recovery engine adds drift and is rejected. The weakest assumption is that all producer paths and all participating databases share a consistent audit boundary. Cheapest falsifiers are an unregistered governed table, a missing reference and a concurrent commit during audit: none may produce false PASS. If existing snapshot/verifier ownership cannot support the required boundary, extend the smallest existing owner and test that boundary before adoption.

Evidence families: current store/writer/schema inspection; explicit adversarial SQLite/runtime observations; full local and CI regression (the same test suite is one correlated evidence family). Confidence remains provisional until non-vacuous population and concurrent-write tests pass.

## Constraints, rollback and separate backlog

Never count pending/failed/unverifiable lineage as APPLIED; never shrink mandatory denominator, substitute latest evidence, rewrite immutable old artifacts or perform repair on reads. Zero population is explicit EMPTY, not production acceptance. Preserve every all-state and independent opportunity. Scratch databases only. Rollback is the scoped code/document diff; no deployed data is changed. Stop on a newly demonstrated 03D defect or unexplained regression that invalidates acceptance.

Separate backlog: real schema deployment, live/PIT evidence, price-band/tick/base-price geometry, source timestamps/freshness, EIA CSV dates, CLI decision-path consolidation and legacy typing debt. These do not block coding 03E unless its tests demonstrate a direct dependency. Research, PIT, model, strategy and execution authority remain unchanged.

## Current checkpoint

Documentation update prepared; its new CI is pending publication. 03E implementation is not started. The native Fable read-only reviewer could not run because the workspace reported it was out of credits. The parent continues direct code inspection, adversarial verification and final diff review; independent model review is unavailable and must not be claimed.
