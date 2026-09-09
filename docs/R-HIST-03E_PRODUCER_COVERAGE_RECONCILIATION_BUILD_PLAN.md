# R-HIST-03E — Producer Coverage Registry, Orphan Detection, and Reconciliation Build Plan

**Stage:** R-HIST-03E — prove that every governed immutable artifact is retention-protected  
**Parent plan:** `docs/R-HIST-03_PRODUCER_WIRING_BUILD_PLAN.md`  
**Depends on:** R-HIST-03D IMPLEMENTED + TESTED  
**Status:** PLAN READY — IMPLEMENTATION NOT STARTED  
**Next after PASS:** R-HIST-03F only  
**Safety ceiling:** integrity/reconciliation only; no model approval, strategy activation, broker authority, or live-order expansion.

---

## 1. Mission

03E turns R-HIST from a collection of individually protected producers into a **self-auditing retention system**.

The system must be able to answer mechanically:

> Which immutable artifact classes are supposed to be protected, how many governed artifacts exist, how many have exact APPLIED retention proof, which are missing or orphaned, and whether the system is safe to proceed?

03E exists because manually checking a few producers is not enough. A future autonomous trading/research agent can create many artifacts across decisions, outcomes, datasets, models, strategy profiles and audits. If one producer silently forgets to emit retention intent, history can become unreconstructable even if all other producers are correct.

The stage therefore creates a machine-enumerable coverage contract and requires **100% mandatory coverage with zero unexplained orphans** before R-HIST-03 can advance.

---

## 2. Core invariant

```text
EVERY GOVERNED IMMUTABLE ARTIFACT
      |
      v
HAS EXACT DECLARED PRODUCER OWNERSHIP
      |
      v
HAS EXACT REQUIRED RETENTION REFERENCE TYPE
      |
      v
HAS EXACT RETENTION INTENT / PUBLICATION RECORD
      |
      v
HAS APPLIED AUTHORITY PROOF
      |
      v
HAS RECONSTRUCTABLE EVIDENCE ROOTS
```

If any mandatory artifact violates this chain:

```text
coverage < 100%
```

and the stage fails closed.

---

## 3. Why 03E matters for the autonomous trading brain

The trading brain will eventually produce many independent artifact streams:

```text
discovery / opportunity evaluation
 -> decision versions
 -> outcomes and revisions
 -> frozen datasets
 -> challenger models
 -> strategy/profile versions
 -> governance/audit records
```

An autonomous agent must not be allowed to reason:

> "Most of the history is probably retained."

It must be able to prove:

```text
mandatory artifact count = N
protected/APPLIED count = N
unexplained orphan count = 0
coverage ratio = 1.000000
```

03E therefore gives the future research agent an integrity conscience: it must check population coverage before trusting historical memory.

---

## 4. Required governed classes

03E must inspect the current head and derive the exact active producer registry. Expected classes after 03D include:

```text
DECISION_VERSION
OUTCOME
REVISION
ML_DATASET
MODEL_VERSION
STRATEGY_PROFILE
AUDIT
```

`TEMPORARY` or other non-mandatory classes may exist, but their treatment must be explicitly declared.

Do not hardcode a class just because it appears in this plan. Confirm its current producer/table/store and publication semantics before registration.

---

## 5. Producer registry contract

Build one canonical registry of governed producers. It should be code-owned, testable and machine-enumerable.

Each entry must declare at least:

```text
ProducerCoverageSpec
- producer_id
- artifact_type
- authoritative_store/table
- immutable_primary_key
- immutable_version/hash fields
- required_retention_reference_type
- lineage extractor / verifier
- publication-state source
- mandatory_retention: true/false
- legacy policy
- reconciliation query/function
- artifact count query/function
- protected/APPLIED count query/function
- orphan detection function
- current-reader visibility policy
- owning module/function
- policy version
```

A registry declaration is not sufficient by itself. Tests must prove that it actually enumerates the authoritative producer population.

---

## 6. Coverage calculations

Minimum calculations:

```text
mandatory_artifacts = count(all governed immutable artifacts that require retention)
applied_artifacts   = count(mandatory artifacts with exact APPLIED retention proof)
blocking_artifacts  = count(mandatory artifacts with FAILED_BLOCKING or equivalent)
pending_artifacts   = count(mandatory artifacts still awaiting retention)
legacy_unverifiable = count(old artifacts explicitly outside governed history)

mandatory_coverage_ratio = applied_artifacts / mandatory_artifacts
```

Special case:

```text
if mandatory_artifacts == 0:
  coverage is not silently treated as production-ready
```

Return a typed state such as EMPTY/NO_POPULATION or equivalent current contract semantics.

### Acceptance target

```text
mandatory_coverage_ratio = 1.0
blocking_artifacts = 0
pending_artifacts = 0 after reconciliation window
unexplained_orphan_artifacts = 0
unexplained_orphan_references = 0
```

Legacy rows may remain outside governed history only when explicitly classified and not exposed as governed artifacts.

---

## 7. Orphan definitions

03E must detect both directions.

### Orphan artifact

An immutable governed artifact exists but its mandatory retention graph is missing, invalid, unresolvable or not APPLIED.

Examples:

```text
R16 decision row without retention publication
frozen dataset without ML_DATASET reference
model registry row without MODEL_VERSION retention
strategy profile version without STRATEGY_PROFILE retention
promotion review without AUDIT retention
```

### Orphan reference

A retention reference/outbox/publication points at an artifact that does not exist, cannot be resolved, belongs to the wrong artifact type/version, or has been tampered/repointed.

### Broken transitive reference

An artifact has an APPLIED top-level reference but one required parent/evidence root no longer verifies.

This is not considered healthy coverage.

---

## 8. Reconciliation model

03E reconciliation must be conservative.

### Allowed reconciliation

- resume known deterministic PENDING outbox events;
- verify APPLIED publication/reference integrity;
- classify legacy/unverifiable records;
- report missing mandatory intents;
- quarantine or block governed visibility where current architecture supports it;
- produce exact remediation diagnostics.

### Forbidden reconciliation

- infer a missing historical parent from latest data;
- create a retention relationship for an old artifact using present-day hashes when original proof is missing;
- mutate old immutable records to make coverage reach 100%;
- delete unexplained artifacts or references just to improve the metric;
- silently downgrade a mandatory producer to optional;
- mark FAILED_BLOCKING as healthy;
- repair on a read/UI route.

03E is a proof and reconciliation stage, not a history-forgery stage.

---

## 9. Registry-driven reconciliation loop

Preferred flow:

```text
LOAD PRODUCER REGISTRY
      |
      v
FOR EACH PRODUCER
      |
      +--> enumerate governed artifact population
      |
      +--> verify immutable identity/version
      |
      +--> find required retention publication/outbox/reference
      |
      +--> verify APPLIED authority proof
      |
      +--> verify transitive evidence graph
      |
      +--> classify HEALTHY / PENDING / BLOCKING / ORPHAN / LEGACY
      |
      v
AGGREGATE COVERAGE
      |
      v
IF mandatory coverage != 100%
      -> FAIL CLOSED
ELSE
      -> eligible for 03F
```

The loop must be deterministic and restart-safe.

---

## 10. Reconciliation states

Use current state enums/contracts where possible. Conceptually, every enumerated artifact should end in one of:

```text
HEALTHY_APPLIED
PENDING_RETENTION
FAILED_BLOCKING
ORPHAN_ARTIFACT
BROKEN_REFERENCE
BROKEN_TRANSITIVE_LINEAGE
LEGACY_UNGOVERNED
LEGACY_UNVERIFIABLE
OPTIONAL_NOT_REQUIRED
```

Do not collapse these to one generic failure string.

---

## 11. Self-auditing behavior for future autonomous agents

A future high-autonomy TrendForge research agent should be able to ask before learning:

```text
Is historical memory coverage complete for the artifact classes I depend on?
```

The correct behavior is:

```text
if coverage = 100% and no integrity errors:
    research may proceed under other gates
else:
    block/flag the affected analysis
```

Examples:

```text
Model-training request
 -> requires R16 + ML_DATASET + MODEL_VERSION lineage coverage
 -> if one frozen dataset is orphaned, training/promotion workflow blocks
```

```text
Failure-memory analysis
 -> requires decisions + outcomes + revisions
 -> if outcome retention coverage is incomplete, confidence is downgraded/blocked
```

This prevents an agent from learning strong conclusions from a selectively surviving subset of history.

---

## 12. Drift between registry and code

03E must detect when a new producer appears in code but is not registered for coverage.

Recommended tests/mechanisms:

- declared artifact/reference types match known retention reference enum/contract;
- authoritative governed tables/stores are mapped exactly once;
- no mandatory governed table is left unregistered;
- duplicate registry ownership fails;
- registry points to real existing modules/tables/functions;
- new migration/table for a governed artifact must update the registry or tests fail;
- code review/CI reports registry drift.

Do not rely solely on a hand-maintained Markdown list.

---

## 13. Transaction and locking behavior

Coverage audit must not corrupt active producer writes.

Design rules:

- use read-only/snapshot transactions for population audits where possible;
- avoid long exclusive locks;
- do not count half-written uncommitted artifacts;
- publication state must be read consistently with artifact identity;
- reconciliation workers must use bounded batches;
- write-side recovery must be explicit and idempotent;
- concurrent producer writes may create a short PENDING window, but coverage acceptance runs only after the defined reconciliation window or a quiescent test boundary.

The metric must never claim 100% from a mixed-generation read.

---

## 14. Required observability

At minimum:

```text
producer_registry_count
mandatory_producer_count
mandatory_artifact_count
applied_artifact_count
pending_artifact_count
blocking_artifact_count
legacy_ungoverned_count
orphan_artifact_count
orphan_reference_count
broken_transitive_lineage_count
mandatory_coverage_ratio
oldest_pending_age_seconds
per_producer_coverage_ratio
per_reference_type_coverage_ratio
reconciliation_runs_total
reconciliation_failures_total
```

Expose exact IDs/reasons through an admin/research diagnostic path or CLI where current architecture allows, but do not expose secrets.

---

## 15. Alerts and stop conditions

Mandatory failure conditions:

```text
any mandatory producer missing from registry
any mandatory coverage < 1.0
any unexplained orphan artifact > 0
any unexplained orphan reference > 0
any broken transitive lineage > 0
any FAILED_BLOCKING mandatory artifact > 0
pending older than allowed reconciliation SLA
registry duplicate/conflict
coverage query/verifier error
```

A coverage-verifier exception is not treated as PASS.

---

## 16. Test-first adversarial matrix

### Registry integrity

1. all expected current governed producer classes registered;
2. duplicate producer registration rejected;
3. duplicate authoritative table ownership rejected;
4. unknown reference type rejected;
5. registry points at missing table/store -> failure;
6. mandatory new governed table without registry entry causes test failure;
7. optional producer does not inflate mandatory denominator.

### Coverage math

8. 10/10 APPLIED -> 1.0;
9. 9/10 APPLIED -> fail;
10. PENDING not counted as APPLIED;
11. FAILED_BLOCKING not counted as APPLIED;
12. broken transitive lineage not counted healthy;
13. zero-population state is explicit, not false production-ready;
14. legacy-unverifiable rows excluded only according to explicit policy.

### Orphan artifact/reference

15. artifact without outbox/publication detected;
16. APPLIED reference pointing to missing artifact detected;
17. wrong artifact version/hash detected;
18. wrong reference type detected;
19. publication exists but authority reference missing detected;
20. top-level reference valid but parent evidence deleted/tampered detected;
21. stale/newer parent substitution rejected.

### Reconciliation

22. PENDING event resumes and reaches APPLIED;
23. deterministic replay is idempotent;
24. FAILED_BLOCKING not silently repaired;
25. missing original proof remains blocking;
26. legacy row is not backfilled from latest;
27. reconciliation can restart after crash;
28. bounded batch ordering deterministic;
29. read-only coverage report performs no mutation;
30. explicit recovery write is separated from report/read.

### Concurrency/snapshot

31. concurrent producer commit does not create mixed artifact/publication count;
32. uncommitted artifact not counted;
33. audit during active PENDING window reports PENDING, not orphan corruption;
34. repeated coverage run yields stable result at unchanged state;
35. lock/storage failure returns failure/unknown, never 100%.

### Cross-stage population

36. DECISION_VERSION covered;
37. OUTCOME covered;
38. REVISION covered;
39. ML_DATASET covered;
40. MODEL_VERSION covered;
41. STRATEGY_PROFILE covered;
42. AUDIT covered;
43. all-state/non-trade populations remain visible in counts;
44. same-symbol independent opportunity records do not collapse.

Minimum coverage only; implementation should add cases discovered during D0/03D ownership inspection.

---

## 17. Acceptance artifact/report

03E should produce a deterministic machine-readable and human-readable coverage report containing:

```text
run_id / audit_id
code/commit identity
registry policy version
audit time
per-producer counts
per-reference-type counts
mandatory denominator
APPLIED numerator
coverage ratio
orphan IDs
blocking IDs
pending IDs + ages
legacy counts
transitive verification failures
overall result: PASS / FAIL
```

The report itself should be immutable/auditable according to current repository patterns where feasible. Do not create a circular rule in which 03E cannot run until its own report is already retention-protected; define report retention separately and explicitly if needed.

---

## 18. Acceptance gate for R-HIST-03E

03E may be declared **IMPLEMENTED + TESTED** only when:

1. canonical producer registry exists;
2. every governed mandatory producer is mapped once;
3. registry entries point to actual authoritative stores/writers;
4. coverage math is deterministic and tested;
5. orphan artifacts and orphan references are both detected;
6. transitive lineage verification is included;
7. PENDING/FAILED/legacy states are classified separately;
8. reconciliation is bounded, restart-safe and idempotent;
9. report/read paths perform zero repair writes;
10. latest-data backfill is impossible by contract/tests;
11. coverage report is reproducible at unchanged state;
12. mandatory coverage reaches exactly 100% on the controlled acceptance fixture/current governed test population;
13. unexplained orphan count is zero;
14. focused 03E tests pass;
15. 03A–03D regression tests pass;
16. full backend passes in pinned/CI environment;
17. Ruff passes;
18. Python compilation passes;
19. frontend passes if contracts/UI are affected;
20. Mypy baseline is reported honestly with no unexplained new diagnostics;
21. exact final PR-head CI is observed and recorded.

**STOP:** do not start 03F implementation unless this gate passes.

---

## 19. Handoff to 03F

03E hands 03F a complete declared producer set and a deterministic coverage oracle.

03F will use that oracle during crash/race/tamper tests to prove that failures never create a false healthy state.

Required handoff invariants:

```text
producer registry stable
coverage ratio calculation stable
orphan detectors stable
reconciliation deterministic
all mandatory producer classes represented
```

---

## 20. One-stretch execution rule

```text
03D PASS
 -> 03E RED TESTS
 -> IMPLEMENT 03E
 -> FOCUSED + FULL GATE

PASS
 -> start 03F

FAIL
 -> STOP
 -> record exact producer/coverage failure
 -> do not begin 03F
```

Continuous execution is allowed only through explicit passing gates.

---

## 21. Final 03E definition

03E is complete when TrendForge can truthfully say:

> I know every immutable artifact class whose history must be protected, I can enumerate its authoritative population, I can prove every mandatory artifact has exact applied retention and intact transitive evidence, and I detect any missing/orphaned producer instead of assuming coverage.

Until that statement is mechanically verified, `R-HIST-03E = NOT COMPLETE`.
