# TrendForge R0 Governance Ceiling Coding Plan

Status: DRAFT - READY FOR READ-ONLY BASELINE ONLY

Purpose: one fail-closed coding runbook for finishing only genuinely incomplete R0 source-governance work. This file is subordinate to File A, `D:\TrendForge\docs\fable\new_merge_PLAN_2026-07-18.md`. It does not change File A scope, sequence, IDs, states, or acceptance ceilings.

## 1. Selected Approach

Use the smallest technically complete hybrid:

1. Capture a genuinely read-only current baseline.
2. Resolve source-key drift and semantic overlaps before changing pins.
3. Separate mirror/resolver identity from review status.
4. Build maturity history only with a real append writer and fixture-tested migration.
5. Apply a live migration only after separate explicit approval.
6. Expose the File B activation-review backlog without granting authority.
7. Verify focused, complete, runtime, adversarial, and documentation behavior before claiming the R0 governance ceiling.

Rejected approaches:

| Alternative | Reason rejected |
|---|---|
| Do nothing | Leaves known R0 governance gaps unresolved. |
| Re-pin immediately | Can bless unreviewed additions, removals, aliases, or overlaps. |
| Rename `UNSPECIFIED` values | Changes wording without resolving identity and may form false groups. |
| Create history storage without a writer | The table can remain empty forever. |
| Apply raw SQL then `INSERT OR IGNORE` a migration row | Can split schema state from the migration ledger. |
| Implement everything in one diff | Excessive blast radius and weak rollback. |

Weakest link: the latest repository state, migration level, map membership, DTO schema, and `canVote` contract are not yet freshly observed.

Cheapest falsifier: complete R0-M0. Any missing field, existing implementation, different migration framework, or authority contradiction reopens planning.

Pivot: when R0-M0 proves a proposed gap already works and has current evidence, mark it `NO_CHANGE_VERIFIED`; do not rebuild it.

## 2. Authority

1. Current explicit user instruction.
2. `D:\TrendForge\AGENTS.md`.
3. File A: `D:\TrendForge\docs\fable\new_merge_PLAN_2026-07-18.md`.
4. `D:\TrendForge\docs\DECISIONS.md`.
5. `D:\TrendForge\TREND_FORGE_ARCHITECTURE.md`.
6. Current code and observed tests/runtime behavior.
7. `D:\TrendForge\docs\BUILD_STATUS.md`.
8. `D:\TrendForge\docs\VALIDATION.md`.
9. `D:\TrendForge\docs\ARCHITECTURE.md`.
10. File B detail only through File A pointers: `D:\TrendForge\docs\fable\TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md`.

Before R0-M0, read File A R0 in Section 15; CROSS-001..007; TDG-GAP-001..026; Sections 25.19, 25.20, and 25.20.1. Read File B Sections 16.3, 16.4, 16.6, 16.16, 18.4, and 19.2 when their mapped milestone is reached.

## 3. Target and Boundaries

Target: complete only unfinished R0 source-contract governance requirements with observed evidence.

R0 governance ceiling requires:

- an exact persisted reviewed living-key set;
- added and removed keys derived from full sets, not counts or hashes;
- every overlap reviewed or quarantined before pins change;
- dataset-root identity separated from review status;
- maturity changes appended by a real reconciliation writer;
- a versioned, non-authorizing activation-review backlog;
- separately approved and verified live migration, if required;
- passing focused/full tests, runtime observation, adversarial checks, and zero unexplained coverage drift.

Non-goals:

- no source activation or new `CONFIRMED` path;
- no orders, broker/account access, positions, margins, or executable quantity;
- no workbook modification;
- no parallel downloader, duplicate database, or competing status file;
- no invented source proof, freshness, mapping, decision job, or migration number;
- no rebuilding already verified behavior.

## 4. Safety Invariants

```text
sourceActivationReady = false
gateAuthorizedSourceKeyCount = 0
executionAuthorizedCount = 0
canUnlockConfirmed = false for every R0-governed source
workbook bytes and SHA-256 unchanged from R0-M0
no new source gains vote, gate, confirmation, or execution authority
h1a0AcceptancePassed == h1a0AcceptanceTotal
```

Do not assume `canVote=false` globally. R0-M0 must verify File A and current behavior. Research visibility/voting and authority to unlock `CONFIRMED` are separate.

Missing, stale, malformed, metadata-only, unofficial-only, conflicting, valid-empty, unreviewed, or compiler-unapproved evidence cannot unlock `CONFIRMED`.

## 5. Requirements

| ID | Requirement | Milestone | Proof |
|---|---|---|---|
| R0-REQ-001 | Current baseline and authority reconciliation | R0-M0 | Opened authority and exact outputs |
| R0-REQ-002 | Reviewed living-key manifest and drift classification | R0-M1 | Persisted full set plus added/removed dispositions |
| R0-REQ-003 | Zero unexplained overlap before re-pin | R0-M1 | H1A0-04 and registry checks |
| R0-REQ-004 | Typed root identity and review state | R0-M2 | Schema, compatibility, compiler, and API tests |
| R0-REQ-005 | Append-only maturity history with writer | R0-M3 | Fixture migration, writer, concurrency, lineage, API |
| R0-REQ-006 | Safe live migration, if required | R0-M4 | Approval, backup, canonical migration, integrity/runtime |
| R0-REQ-007 | Versioned activation-review backlog | R0-M5 | File B order, DTO/API tests, zero authority |
| R0-REQ-008 | Governance ceiling verification and close-out | R0-M6 | Full suites, runtime battery, adversarial tests, coverage |

## 6. R0-M0 - Pure Read-Only Baseline

Intent: observe current state without writing code, documentation, databases, generated files, caches, or evidence folders.

Read the authorities above, current BUILD_STATUS/VALIDATION/remaining-build files, and the compiler, key-map review, overlap, R0-B/R0-C, migration, DTO, API, and corresponding tests.

Capture repository state:

```powershell
git -C D:\TrendForge status --short
git -C D:\TrendForge rev-parse HEAD
```

Record size, mtime, and SHA-256 for expected future edit targets. Preserve unrelated changes.

Backend:

```powershell
Set-Location D:\TrendForge\backend
& 'D:\TrendForge\.venv\Scripts\python.exe' -m pytest tests -q
if ($LASTEXITCODE -ne 0) { throw "Backend baseline failed: $LASTEXITCODE" }
& 'D:\TrendForge\.venv\Scripts\python.exe' -m compileall trendforge_api -q
if ($LASTEXITCODE -ne 0) { throw "Compilation failed: $LASTEXITCODE" }
```

Frontend and coverage:

```powershell
Set-Location D:\TrendForge\frontend
cmd /c npm test
if ($LASTEXITCODE -ne 0) { throw "Frontend baseline failed: $LASTEXITCODE" }
Set-Location D:\TrendForge
& 'D:\TrendForge\.venv\Scripts\python.exe' docs\fable\remaining_build\build_coverage_csv.py --check
if ($LASTEXITCODE -ne 0) { throw "Coverage check failed: $LASTEXITCODE" }
```

Capture exactly:

1. Workbook path, actual/reviewed SHA-256, and equality.
2. Complete named, runtime, and living key sets.
3. Exact previously reviewed key set, if persisted.
4. Added, removed, and unchanged key sets.
5. Every H1A0 check ID, rule, result, and evidence.
6. Governance, activation, vote, gate, confirmation, and execution separately.
7. Unexplained/stale/invalid overlaps and registry validity.
8. R0-B/R0-C membership, partition, and proof/waiver/missing dimensions.
9. Dataset-root fields, serializers, consumers, and every `UNSPECIFIED` use.
10. Migration runner, latest version/checksum, DB path, and integrity.
11. Existing maturity history, writer hooks, routes, and tests.
12. File B Section 16.16 exact backlog IDs/order.
13. Coverage status schema, API field casing, and runtime start command.

Correct cohort diagnostic:

```python
for member in report.members:
    print(member.source_key, member.proven, member.reviewed, member.quarantined)
    for dimension in member.dimensions:
        print("  ", dimension.id, dimension.state, dimension.evidence)
```

Stop when authority conflicts, baseline tests fail, a named field/module is absent, no exact prior key set exists, DB/migration identity is ambiguous, the worktree changes, or a proposed gap is already complete.

Acceptance: all observations exist in command output; no file changes; no process left running; first unfinished requirement identified. Present evidence and request approval for only that milestone.

## 7. R0-M1 - Living-Key and Overlap Review

Run only if R0-M0 proves drift, incomplete dispositions, or unexplained overlaps.

Persist the exact reviewed key set in the existing key-map mechanism. Each record needs source key, inventory/runtime origin, review status, disposition, contract/descriptor presence, safe/blocked use, evidence basis, UTC review time, and review version.

Compute full sets:

```text
added = current_living - reviewed_living
removed = reviewed_living - current_living
unchanged = current_living intersect reviewed_living
```

Required order:

1. Classify every addition and removal without truncation.
2. Confirm no key silently enters the fixed R0-B cohort.
3. Detect all changed semantic overlaps.
4. Resolve each with a typed disposition or `QUARANTINED_UNPROVEN`.
5. Reject URL-only evidence.
6. Persist key and overlap dispositions.
7. Recompute counts/digests.
8. Update one canonical review-version value imported by all consumers.
9. Re-pin only after all preceding checks pass.

Likely surfaces: `source_key_map_review.py`, `source_overlap_resolutions.py`, `source_inventory_compiler.py`, and existing focused tests.

Tests: exact set equality; dispositions for every addition/removal; deterministic ordering/digests; zero unexplained/stale/invalid overlaps; quarantined sources cannot authorize; one-key addition/removal fails closed; disposition changes invalidate review digest; workbook unchanged; H1A0 passed equals total without changing the approved check count.

Runtime: observe compiler-report version, counts, map/overlap validity, and unchanged authority ceilings.

Rollback: restore only this milestone's manifest, resolutions, pins, and version from the pre-edit baseline.

Completion rule: quarantine completes map review but does not prove activation readiness.

## 8. R0-M2 - Typed Dataset-Root Identity

Run only when R0-M0 proves ambiguous fields remain and File A requires correction in R0.

Preferred contract:

```text
mirror_group_id: string | null
mirror_review_status: REVIEWED | NOT_REVIEWED | QUARANTINED | NOT_APPLICABLE
mirror_review_reason: string
resolver_id: string | null
resolver_review_status: REVIEWED | NOT_REVIEWED | QUARANTINED | NOT_APPLICABLE
resolver_review_reason: string
authority_cap: existing typed value
authority_cap_reason: string
contract_version: string
```

Rules:

- never put status text in identity fields;
- null IDs never form a shared mirror/correlation group;
- deduplication ignores null identities;
- official publisher status does not prove parser, freshness, wiring, vote, gate, or confirmation authority;
- reviewed IDs remain unchanged;
- unknown stays unknown;
- CROSS-007/TDG-GAP-024 stay partial until every required identity has evidence-backed disposition.

Before editing, find all constructors, serializers, API schemas, persistence, equality/hash logic, frontend consumers, and tests. Update them atomically or add a versioned compatibility adapter.

Tests: null IDs do not merge roots; statuses serialize; reviewed IDs remain stable; official status grants no permission; missing status fails; old DTOs are compatible or explicitly rejected; compiler/API contract versions agree; authority ceilings unchanged.

Runtime: inspect actual compiler/API JSON and compatibility behavior.

Rollback: revert producer and all consumers together.

## 9. R0-M3 - Maturity History With Real Writer

Run only when R0-M0 proves history and writer are absent/incomplete.

Architecture:

1. One explicit immutable maturity-order mapping.
2. Versioned transition record/repository.
3. Fixture-only migration numbered by the canonical runner.
4. Explicit reconciliation service comparing compiler maturity with persisted maturity.
5. Read-only paginated APIs.
6. No GET/compiler-report write side effects.

Transition fields:

```text
transition_id, source_key, from_state, to_state, transition_reason,
evidence_summary, evidence_hash, evidence_reference, observed_at_utc,
recorded_at_utc, reviewer_or_process, compiler_version,
source_contract_version, predecessor_transition_id,
gate_authorized, execution_authorized=false
```

The transition ID is a hash of the canonical serialization of all identity-bearing fields, including predecessor and evidence reference.

Bootstrap existing sources with one honest row:

```text
from_state=null
to_state=current observed state
transition_reason=BASELINE_SNAPSHOT
```

Do not fabricate earlier history.

Writer requirements:

- run only from an approved reconciliation command or governed scheduler hook;
- read latest state and append inside one transaction;
- validate predecessor/current state;
- no write for unchanged state/evidence identity;
- identical duplicate is idempotent; conflicting duplicate raises;
- prevent concurrent forked successors;
- require explicit regression/invalidation reasons for demotion;
- never grant gate or execution authority.

Resolve gate schema before coding. Do not expose a gate-authorized writer while also enforcing `CHECK(gate_authorized=0)`. Either permanently reject that transition or add future-compatible relational constraints while R0 writes none.

Migration rules: discover next version; use canonical migration/checksum ledger; test scratch and copied DBs; canonical UTC; append-only protection; allowed-state/boolean checks; source/time/predecessor indexes; tested rollback; no live application here.

API rules: distinguish known-empty from unknown source; paginate all-history output; include as-of and contract version; rely on framework 405 unless project convention differs.

Tests: explicit order; baseline snapshot; repeated no-op; one-step advancement; skipped advancement rejection; controlled demotion; identical/conflicting duplicates; concurrent writers; UPDATE/DELETE rejection; execution rejection in code/DB; selected gate behavior; known-empty/unknown distinction; deterministic pagination; restart persistence; malformed inputs; migration version/checksum collision.

Runtime on temporary DB: reconcile twice, introduce one controlled fixture transition, observe one append, restart, and observe identical ordered history through API.

Rollback: discard fixture DB and revert only new code/routes/tests. Live data remains untouched.

## 10. R0-M4 - Separately Approved Live Migration

Approval of this plan does not authorize this milestone.

Preconditions: R0-M3 verified; exact configured DB and canonical migration runner known; database writers can be quiesced; backup/restore tested on a copy.

Approval packet must show exact version, filename, checksum, SQL, DB path/size/integrity, backup path, copied-DB results, rollback procedure, downtime, affected APIs, and confirmation that no activation/backfill occurs.

After approval:

1. Quiesce writers.
2. Recheck DB identity, mtime, size, version, and integrity.
3. Create and integrity/hash verify backup.
4. Apply through canonical migration runner.
5. Reject same-version/different-checksum; never ignore it.
6. Verify ledger, schema, triggers, indexes, and integrity.
7. Restart service.
8. Observe APIs and one governed baseline reconciliation.
9. Run focused/full backend and frontend tests.
10. Restore on failed integrity, migration, startup, or runtime verification.

Completion requires live integrity, ledger, restart, runtime, and regression proof. It does not activate sources.

## 11. R0-M5 - Activation-Review Backlog

Run only if R0-M0 proves CROSS-005/TDG-GAP-021 unfinished and File A requires it.

Rules:

- use exact IDs/order from File B Section 16.16; do not assume 20;
- validate duplicate and unknown IDs;
- read maturity/blockers from current compiler;
- aliases/companions do not gain independent authority;
- every entry remains activation-ineligible, unable to unlock confirmation, gate-ineligible, and non-executable;
- blockers are never empty; use `R0_NON_ACTIVATING_CEILING` when no source-specific blocker exists;
- include as-of, compiler version, backlog contract version, map-review version, and source-contract version.

Prefer extending an existing DTO/module. Create one focused module only if none exists.

Tests: exact File B order; duplicate/unknown handling; deterministic output; dynamic maturity; non-empty blockers; alias handling; all authority false; version/timestamp present; POST 405; stale compiler/map fails closed.

Runtime: compare every returned ID/order with File B and inspect authority/version fields.

Rollback: remove only the new route/module/tests or revert the existing extension.

## 12. R0-M6 - Verification and Close-Out

Run only after every preceding requirement is `VERIFIED` or `NO_CHANGE_VERIFIED`.

Complete regression:

```powershell
Set-Location D:\TrendForge\backend
& 'D:\TrendForge\.venv\Scripts\python.exe' -m compileall trendforge_api -q
if ($LASTEXITCODE -ne 0) { throw 'Compilation failed' }
& 'D:\TrendForge\.venv\Scripts\python.exe' -m pytest tests -q
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
Set-Location D:\TrendForge\frontend
cmd /c npm test
if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed' }
Set-Location D:\TrendForge
& 'D:\TrendForge\.venv\Scripts\python.exe' docs\fable\remaining_build\build_coverage_csv.py --check
if ($LASTEXITCODE -ne 0) { throw 'Coverage drift check failed' }
```

Record exact collected/passed/failed/skipped/warning counts; require zero failures, not stale totals.

Runtime must inspect actual contracts for compiler report, R0-B/R0-C, maturity history if built, activation backlog if built, live selection, and named source authority.

Verify separately:

```text
DATA_PRESENT
DATA_FRESH_FOR_PUBLICATION_CALENDAR
RESEARCH_VISIBLE_OR_VOTE_ELIGIBLE according to File A
GATE_AUTHORIZED=false
CAN_UNLOCK_CONFIRMED=false
EXECUTION_AUTHORIZED=false
```

Do not require `confirmedCount=0` unless File A and runtime mode require it.

Adversarial checks: key addition/removal; changed overlap disposition; URL-only overlap evidence; null root IDs; stale review version; malformed transition; identical/conflicting duplicate; concurrent writers; interrupted scratch migration; version/checksum collision; unknown backlog source; stale compiler; restart; unchanged workbook.

Update only existing authoritative files after proof:

- `docs/BUILD_STATUS.md`;
- `docs/VALIDATION.md`;
- `docs/DECISIONS.md` for durable decisions only;
- `docs/fable/remaining_build/REMAINING_PROJECT_BUILD_FILES.md`;
- coverage builder/CSV only for genuinely changed requirements;
- source registry only if source meaning/authority/freshness changed;
- `fileindex.md` only for durable modules, not temporary evidence folders.

Use existing coverage status values. If only `IMPLEMENTED` is allowed, put `R0_GOVERNANCE_CEILING` in detail/notes rather than inventing a status.

Allowed completion wording:

```text
R0 GOVERNANCE CEILING VERIFIED.
Sources remain non-activating and cannot unlock CONFIRMED or execution.
```

Do not claim production-ready, live-trading ready, all sources operational, or source activation complete.

Acceptance: mapped focused tests are non-vacuous; all complete suites pass; runtime behavior is observed; coverage has zero unexplained drift; workbook is unchanged; no user changes overwritten; exact next milestone is named but not started.

## 13. Execution Discipline

- One milestone per coding run unless a named range is explicitly approved.
- Before editing: `INTENT: current behavior; requested behavior; governing requirement`.
- Recheck size, mtime, and hash of edit targets immediately before writing.
- Add/update safety-critical tests before implementation.
- Use existing modules/migration infrastructure; no parallel paths.
- Stop after three evidence-equivalent failed attempts.
- Contradiction, missing dependency, migration ambiguity, or concurrent edit returns to planning.
- Installs, commits, pushes, deployments, workbook changes, live migrations, credentials, external writes, and broker/trading actions require separate approval.

## 14. Resume Record

After each implemented milestone, update existing status/validation files with:

```text
MILESTONE
VERDICT = VERIFIED | VERIFIED_WITH_CAVEATS | REFUTED | BLOCKED | NO_CHANGE_VERIFIED
INTENT
FILES CHANGED
FOCUSED TESTS
FULL REGRESSION
RUNTIME OBSERVATION
ADVERSARIAL CHECK
WORKBOOK HASH RESULT
AUTHORITY INVARIANTS
REMAINING RISKS
EXACT NEXT MILESTONE, NOT STARTED
```

This plan does not authorize implementation. The next permitted action is R0-M0, the pure read-only baseline.
