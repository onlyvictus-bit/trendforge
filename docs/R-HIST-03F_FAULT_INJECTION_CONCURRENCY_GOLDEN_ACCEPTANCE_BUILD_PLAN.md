# R-HIST-03F — Fault Injection, Concurrency, Replay, and Golden Acceptance Build Plan

**Stage:** R-HIST-03F — prove the complete R-HIST-03 memory system survives crashes, races, corruption and restart without producing false history  
**Parent plan:** `docs/R-HIST-03_PRODUCER_WIRING_BUILD_PLAN.md`  
**Depends on:** R-HIST-03D + R-HIST-03E IMPLEMENTED + TESTED  
**Status:** PLAN READY — IMPLEMENTATION NOT STARTED  
**Next after PASS:** FULL R-HIST-03 acceptance gate only  
**Safety ceiling:** resilience/integrity testing only; no strategy activation, model auto-approval, broker authority, or live-order expansion.

---

## 1. Mission

03F is the final proof stage for R-HIST-03.

03A–03E can make individual contracts look correct. 03F asks the harder production question:

> What happens when the process crashes at the worst possible instruction boundary, two workers race, a lease holder dies, bytes are tampered, cleanup runs concurrently, storage locks, a retry occurs after an uncertain success, or a reader observes the system while recovery is in progress?

TrendForge must never convert operational uncertainty into false historical certainty.

The core 03F rule is:

```text
UNCERTAIN / PARTIAL / CORRUPT STATE
          |
          v
BLOCK / PENDING / RECOVERABLE

NEVER
          |
          v
FALSE PUBLISHED / FALSE 100% COVERAGE / REWRITTEN HISTORY
```

03F therefore proves that the historical notebook supporting the future trading brain remains trustworthy under adverse real-world execution conditions.

---

## 2. Why 03F matters for an autonomous research/trading brain

A high-autonomy research agent can be dangerous even without broker access if it learns from corrupted memory.

For example:

```text
worker A writes dataset D7
worker B sees only half the publication graph
cleanup removes an evidence object
model M9 trains from the surviving subset
agent concludes reversal setup improved
```

This is unacceptable even if every individual function passed happy-path unit tests.

03F must prove that an autonomous agent instead sees:

```text
PENDING / BROKEN / UNKNOWN
```

and refuses to learn, promote, compare or claim certainty until integrity is restored.

The resilience contract applies to:

```text
DECISION_VERSION
OUTCOME
REVISION
ML_DATASET
MODEL_VERSION
STRATEGY_PROFILE
AUDIT
```

and to all transitive evidence roots they depend on.

---

## 3. Non-negotiable 03F laws

1. **Deterministic identity is the safety foundation.** Retry after uncertainty must converge on the same event/reference/artifact identity.
2. **Leases optimize concurrency; they do not define correctness.** Even duplicate workers must remain semantically idempotent.
3. **No partial publication.** Artifact visibility is governed by complete retention proof, never by the presence of one row alone.
4. **Crash-before-commit means nothing survived.** Artifact and outbox intent must roll back together when they share a transaction.
5. **Crash-after-commit remains recoverable.** Durable PENDING state survives and can be resumed.
6. **Authority-success-before-ack is replayable.** A retry must not create a second semantic reference or repoint the first.
7. **Reads never repair.** Readers may detect broken state, not heal it.
8. **Coverage never lies.** 03E coverage must not report 100% from mixed-generation or partially recovered state.
9. **Tamper detection fails closed.** Payload, indexed columns, hashes, evidence bytes, parent chains and publication records are all verified.
10. **Cleanup cannot outrun protection.** Referenced evidence must survive cleanup even when cleanup races a producer/reconciler.
11. **No permanent worker lockout.** A dead claimant must be recoverable after lease expiry according to policy.
12. **No infinite hot loop.** Retry/claim behavior is bounded and observable.
13. **Clock uncertainty is explicit.** Lease and expiry logic must not assume perfect clocks where monotonic/DB-time semantics are required.
14. **No future-data repair.** Recovery never substitutes newer evidence for a missing historical parent.
15. **All historical states survive.** Negative, waiting, no-entry, expired, ambiguous and censored cases receive the same crash/tamper protection as winners.
16. **No test flakiness accepted as success.** Concurrency/fault tests must be deterministic or bounded-repeat stable.
17. **No live-order expansion.** 03F cannot grant execution authority.

---

## 4. System-under-test graph

03F validates the entire R-HIST-03 producer/publication chain:

```text
IMMUTABLE PRODUCER
 decision / outcome / revision / dataset / model / profile / audit
        |
        | same transaction where possible
        +-------------------------+
        |                         |
        v                         v
   ARTIFACT ROW              RETENTION INTENT
                                  |
                                  v
                              OUTBOX
                                  |
                           claim / lease
                                  |
                                  v
                         VERIFY EXACT LINEAGE
                                  |
                                  v
                HISTORICAL RETENTION AUTHORITY
                                  |
                                  v
                          APPLIED PUBLICATION
                                  |
                                  v
                   GOVERNED READ VISIBILITY
                                  |
                                  v
                    03E COVERAGE / ORPHAN AUDIT
```

03F injects faults at every meaningful transition.

---

## 5. Fault domains

03F must cover at least these domains:

### Producer transaction

- before artifact insert;
- after artifact insert but before retention intent;
- after both writes but before commit;
- commit failure;
- DB lock/busy;
- disk/storage exception where testable;
- duplicate producer replay.

### Outbox/registrar

- before claim;
- after claim before verification;
- during verification;
- after verification before authority call;
- authority call fails;
- authority succeeds but process dies before APPLIED acknowledgement;
- APPLIED written but external publication visibility step not completed;
- duplicate dispatch;
- stale lease/claim recovery.

### Evidence store

- missing referenced object;
- altered bytes under same locator;
- altered stored content hash;
- wrong run/date/hash mapping;
- newer object available but original missing;
- cleanup/deletion race.

### Historical parent graph

- wrong S8 parent;
- wrong R16 decision/outcome/revision predecessor;
- broken revision chain;
- dataset member manifest tamper;
- model dataset/evaluation mismatch;
- profile version repoint;
- audit predecessor/evidence tamper.

### Coverage/reconciliation

- audit while producer is PENDING;
- audit while registrar owns a lease;
- crash in reconciliation batch;
- mixed-generation read attempt;
- orphan introduced concurrently;
- registry drift.

### Read paths

- governed read during PENDING;
- governed read after tamper;
- historical list while recovery is happening;
- UI/API refresh must not write or repair;
- repeated reads must not alter outbox/authority counts.

---

## 6. Crash-point matrix

03F should use deterministic fault hooks/test seams around transaction and publication boundaries. Do not rely on random process killing as the only proof.

Minimum crash points:

```text
C01 before artifact INSERT
C02 after artifact INSERT before retention intent INSERT
C03 after retention intent INSERT before COMMIT
C04 immediately after COMMIT before dispatcher starts
C05 after claim acquisition
C06 after payload/hash verification
C07 immediately before authority.register()
C08 immediately after authority.register() succeeds
C09 after authority success before outbox APPLIED
C10 after outbox APPLIED before governed publication visibility
C11 after governed publication visibility before worker acknowledgement/logging
C12 during reconciliation scan
C13 after one artifact in a bounded batch, before next
C14 during cleanup eligibility evaluation
C15 after successor OUTCOME but before linked REVISION
C16 after frozen DATASET commit before retention finalize
C17 after MODEL_VERSION commit before retention finalize
C18 after STRATEGY_PROFILE commit before retention finalize
C19 after AUDIT commit before retention finalize
```

Expected behavior must be specified for every point.

### Example expected states

```text
C02/C03
 -> transaction rollback
 -> no artifact
 -> no outbox event

C04
 -> artifact stored internally
 -> PENDING intent survives
 -> governed read hidden
 -> recovery worker can resume

C08/C09
 -> downstream authority may already contain exact reference
 -> retry uses same deterministic reference_id
 -> no duplicate semantic registration
 -> APPLIED eventually converges
```

---

## 7. Claim/lease design

03F is the stage that hardens high-volume concurrent dispatch.

Recommended additive outbox claim fields, subject to inspection of the current schema before implementation:

```text
claim_owner
lease_expires_at
claimed_at
attempts
next_attempt_at
last_error
```

Use current existing fields where equivalents already exist.

### Claim law

A worker may claim only through a conditional state transition such as:

```text
status = PENDING
AND (claim_owner IS NULL OR lease_expires_at <= authoritative_now)
```

The claim must identify the worker with a unique run/worker UUID.

### Lease law

- lease duration is bounded;
- worker renews only while it owns the claim;
- another worker cannot steal an unexpired claim;
- expired claim is recoverable;
- completion checks current claim ownership when needed;
- worker death never creates permanent lockout.

### Correctness law

Even if two workers both reach downstream registration because of a race or uncertain lease timing:

```text
same deterministic event_id
same deterministic reference_id
same immutable payload
```

must converge safely.

Lease correctness is therefore defense-in-depth, not the only idempotency layer.

---

## 8. Retry and backoff contract

Retries must distinguish semantic blocking from operational retryability once typed errors exist.

Conceptually:

```text
MISSING/TAMPERED/WRONG LINEAGE
 -> FAILED_BLOCKING
 -> no blind retry loop

DB LOCK / TRANSIENT STORAGE / TEMPORARY OPERATIONAL ERROR
 -> retryable according to bounded policy
```

If the current authority does not expose typed operational errors safely, preserve the existing fail-closed behavior rather than guessing retryability.

Required properties:

- bounded attempts per immediate processing cycle;
- backoff/next-attempt state is durable when introduced;
- restart does not reset history invisibly;
- no tight spin under persistent failure;
- exact attempts/errors observable;
- retry never changes immutable artifact identity.

---

## 9. Clock and lease safety

Time-based coordination can fail if host clocks differ.

Preferred policy:

- use database-authoritative UTC time for persisted lease comparison where feasible;
- timestamps are timezone-aware;
- tests include forward/backward host-clock skew around lease boundaries if host time participates;
- decision/event/source timestamps are never reused as worker lease time;
- lease expiry has no trading-semantic meaning.

Clock skew must not let a worker rewrite or repoint an artifact even if it causes duplicate operational work.

---

## 10. Tamper/corruption matrix

03F must prove detection before governed use.

### Outbox tamper

- `payload_json` modified;
- `payload_hash` modified;
- indexed duplicate columns modified;
- event/reference identity modified;
- reference type changed;
- artifact version changed.

### Publication/link tamper

- publication lineage hash modified;
- artifact-retention link repointed;
- member/reference list altered;
- publication state manually changed;
- parent publication ID/version altered.

### Evidence-object tamper

- bytes altered;
- DB hash altered;
- manifest mapping altered;
- object removed;
- wrong object inserted under locator.

### R16/revision tamper

- hypothesis hash altered;
- outcome parent changed;
- revision predecessor changed;
- decision input normalized value changed;
- outcome path evidence changed.

### 03D tamper

- frozen dataset member added/removed;
- member split/fold changed;
- dataset PIT cutoff changed;
- dataset exclusion policy changed;
- model points to another dataset;
- model binary/manifest hash changed;
- strategy profile gates/inputs changed under same version;
- audit review predecessor/evidence changed.

Every one must yield blocking/verification failure, not silent repair.

---

## 11. Cleanup/deletion race tests

HistoricalRetentionAuthority exists to stop evidence cleanup from breaking retained artifacts. 03F must prove this under races.

Scenarios:

```text
producer commits retained artifact
 -> cleanup starts before registrar final acknowledgement
```

Expected: publication remains non-governed until protection is established; cleanup must obey the current authority/protected-root law.

```text
APPLIED artifact exists
 -> cleanup concurrently evaluates same evidence day/hash
```

Expected: retained object survives.

```text
legacy/unprotected artifact exists
 -> cleanup may treat it according to legacy policy
```

Expected: system must not later pretend the legacy artifact is governed/reconstructable.

Also test source-correction coexistence: cleanup of newer or older unreferenced revisions cannot remove an exact root referenced by a frozen historical artifact.

---

## 12. Read/write concurrency and snapshot consistency

Governed reads must see a coherent classification:

```text
PUBLISHED and fully verifiable
OR
not governed-visible / blocking
```

They must not observe:

```text
artifact exists + old publication status + new parent link
```

as a healthy mixed generation.

Where multiple DBs/stores are involved, use existing snapshot/read-consistency patterns and verification hashes rather than pretending cross-store atomicity exists.

03F should test:

- read during producer transaction;
- read immediately after producer commit before retention apply;
- read during recovery;
- read after APPLIED;
- read during source correction;
- repeated GET/history/list calls leave DB/outbox/reference state unchanged.

---

## 13. 03E coverage oracle under concurrency

The coverage system is itself part of the system under test.

Required rule:

```text
PENDING != APPLIED
BLOCKING != APPLIED
BROKEN TRANSITIVE LINEAGE != HEALTHY
```

During active producer/reconciler work, 03E may report transient PENDING, but it must never report false 100% mandatory coverage from a mixed snapshot.

Acceptance coverage should run either:

- against a stable snapshot that includes artifact and publication states consistently, or
- at a controlled quiescent boundary after bounded reconciliation.

03F must inject a concurrent commit while coverage is running and verify the result is coherent rather than mathematically attractive.

---

## 14. Multi-worker concurrency matrix

Minimum scenarios:

1. two workers claim same PENDING event simultaneously;
2. worker A claims, worker B sees unexpired lease;
3. worker A dies, lease expires, worker B recovers;
4. worker A resumes late after worker B completed;
5. two duplicate producers enqueue same immutable intent;
6. same deterministic event arrives with changed payload;
7. authority receives duplicate exact reference concurrently;
8. reconciliation and dispatcher process same event concurrently;
9. cleanup runs while dispatcher registers reference;
10. coverage audit runs while reconciliation mutates PENDING->APPLIED;
11. DB lock causes one worker to fail/retry;
12. stale lease owner tries to complete after ownership moved;
13. claim renewal race;
14. bounded batch workers divide events without semantic omission;
15. restart with many PENDING events preserves deterministic order/policy.

Assertions must focus on final semantic state, not only which thread won.

---

## 15. Golden historical population matrix

03F must validate representative artifacts across the complete memory population.

### Decision states

```text
CONFIRMED historical record where allowed by preserved history
WATCH
WAIT
REJECT
NO_ENTRY
EXPIRED/PAUSED/other current explicit non-trade states
```

Historical `CONFIRMED` never grants present execution authority.

### Outcome classes

```text
TARGET_HIT
STOP_HIT
NO_ENTRY
EXPIRED
AMBIGUOUS
CENSORED
DATA_GAP
NO_GEOMETRY
INVALIDATED_BEFORE_ENTRY
```

Use exact current enums at implementation time.

### Revision classes

```text
SOURCE_CORRECTION
OUTCOME_CORRECTION
INTERPRETATION / rebuild lineage
```

### 03D classes

```text
frozen dataset containing positive + negative + non-trade populations
model version bound to exact frozen dataset
distinct strategy profile version
governance review/audit chain
drift/demotion/rollback where current R18 supports it
```

For every golden case prove:

- exact replay;
- reconstruction after newer data exists;
- cleanup survival;
- tamper detection;
- read purity;
- coverage accounting.

---

## 16. Golden end-to-end scenarios

### G01 — Original decision survives future correction

```text
S8 original evidence
 -> R16 decision D1
 -> outcome O1
 -> dataset DS1
 -> model M1

later source correction
 -> revision R1
 -> dataset DS2
```

Proof:

- D1/O1/DS1/M1 still reconstruct from original roots;
- DS2 is separate;
- no current/latest substitution.

### G02 — Same instrument, opposing opportunities

```text
INFY / 5m continuation / SHORT
INFY / 5m reversal / LONG
INFY / daily swing / LONG
```

Proof:

- all survive independently;
- dataset membership cannot collapse by symbol;
- outcomes/revisions remain attached to correct opportunity.

### G03 — Crash after authority success

```text
artifact committed
 -> retention registered
 -> crash before APPLIED ack
 -> restart
```

Proof:

- same deterministic reference replayed;
- one semantic publication;
- coverage eventually healthy.

### G04 — Worker death under lease

Proof:

- no permanent lock;
- stale claim recovered;
- duplicate work does not create duplicate semantic history.

### G05 — Tampered old evidence with newer good evidence available

Proof:

- old artifact blocks;
- verifier does not pick newer good evidence;
- autonomous research workflow refuses to learn from broken history.

### G06 — Cleanup race

Proof:

- APPLIED roots survive;
- PENDING artifact is not falsely published;
- coverage reflects transitional state honestly.

### G07 — Winner-selection bias attack

Attempt to construct a frozen dataset after deleting/excluding losses/non-trades without explicit versioned policy.

Proof:

- base-population validation or coverage diagnostics exposes the omission;
- old population is not rewritten.

### G08 — Profile/model semantic repoint attack

Proof:

- same version ID with changed model/gates/features is rejected;
- new semantics require new immutable version.

---

## 17. Fault-injection test architecture

Tests should use deterministic fault seams, for example:

- injected callback/hooks at explicit transaction/publication boundaries;
- test doubles for retention authority that can succeed then raise/terminate before acknowledgement;
- controlled SQLite connections to create lock/contention states;
- temporary canonical evidence stores with known byte hashes;
- deterministic worker IDs and authoritative test clock;
- barriers/events for thread/process ordering where concurrency is required.

Avoid:

- arbitrary sleeps as the main synchronization mechanism;
- nondeterministic random kills without a reproducible seed/boundary;
- tests that pass only because timing happened to work;
- production-only chaos without corresponding deterministic contract tests.

Randomized/chaos-style repetitions may supplement deterministic tests, not replace them.

---

## 18. Repeatability / soak policy

Concurrency tests must demonstrate stability without creating an impractical CI suite.

Recommended pattern:

```text
fast deterministic contract tests on every CI run
+
bounded repeated race/replay loop for critical scenarios
+
optional longer local/nightly soak if repository CI policy later supports it
```

The exact repeat count should be chosen from runtime cost during implementation, recorded in validation evidence, and high enough to expose ordering mistakes without arbitrary long sleeps.

Any intermittent failure is treated as a real concurrency defect until explained.

---

## 19. Required observability

03F should make operational integrity diagnosable through existing/admin research mechanisms.

Required metrics/state include:

```text
outbox_pending_count
outbox_claimed_count
outbox_blocking_count
stale_lease_count
claim_recovery_count
duplicate_dispatch_count
duplicate_idempotent_apply_count
oldest_pending_age_seconds
retry_attempts_total
retry_exhaustion/blocking_count
tamper_detection_count
broken_lineage_count
orphan_artifact_count
orphan_reference_count
mandatory_coverage_ratio
cleanup_protection_conflict_count
read_verification_failure_count
```

Do not leak secrets/tokens through error text.

---

## 20. Minimum adversarial test matrix

### Crash/transaction

1. C01 before artifact insert;
2. C02 artifact insert before intent;
3. C03 intent before commit;
4. C04 post-commit pre-dispatch;
5. C05 post-claim;
6. C06 post-verify;
7. C07 pre-authority;
8. C08 authority success then injected crash;
9. C09 pre-APPLIED ack crash;
10. C10 APPLIED before visibility completion;
11. outcome-before-revision crash recovery;
12. dataset pre-finalize crash;
13. model pre-finalize crash;
14. profile pre-finalize crash;
15. audit pre-finalize crash.

### Lease/concurrency

16. duplicate simultaneous claim;
17. unexpired lease not stolen;
18. expired lease recovered;
19. dead worker no permanent lockout;
20. stale former owner cannot repoint/duplicate completion;
21. duplicate exact downstream register converges;
22. same event ID changed payload rejected;
23. reconcile-vs-dispatch race converges;
24. bounded batch restart resumes correctly;
25. DB lock returns safe state;
26. claim renewal race safe;
27. clock skew around lease boundary cannot change semantic identity.

### Tamper

28. outbox payload tamper;
29. payload hash tamper;
30. indexed-column tamper;
31. publication lineage tamper;
32. reference/link repoint;
33. evidence-byte tamper;
34. manifest/hash mapping tamper;
35. decision parent tamper;
36. outcome parent tamper;
37. revision predecessor tamper;
38. dataset member tamper;
39. dataset cutoff/split tamper;
40. model-dataset repoint;
41. model artifact/hash tamper;
42. profile semantic tamper under same version;
43. audit predecessor/evidence tamper.

### Cleanup/coverage/read

44. APPLIED evidence survives cleanup;
45. cleanup race during registration safe;
46. correction cleanup preserves exact old root;
47. coverage never counts PENDING as APPLIED;
48. coverage under concurrent transition is coherent;
49. broken transitive lineage reduces healthy coverage;
50. read during PENDING hidden/blocking;
51. read after tamper fails closed;
52. read does not enqueue/register/repair;
53. repeated reads do not mutate counts;
54. legacy row not auto-upgraded.

### Golden population

55. WAIT retained/replayed;
56. REJECT retained/replayed;
57. NO_ENTRY retained/replayed;
58. EXPIRED retained/replayed;
59. TARGET_HIT retained/replayed;
60. STOP_HIT retained/replayed;
61. AMBIGUOUS not coerced into definite win/loss;
62. CENSORED/DATA_GAP retained;
63. source revision chain reconstructs;
64. opposing same-symbol opportunities remain separate;
65. frozen dataset retains complete selected population;
66. model retains original dataset after newer dataset exists;
67. profile version remains immutable;
68. audit/drift/rollback chain reconstructs;
69. winner-only silent population rewrite rejected/exposed;
70. autonomous research request blocks on broken memory.

This is a minimum baseline; implementation findings should add cases.

---

## 21. 03F acceptance report

Generate a deterministic validation summary recording:

```text
exact commit/head
schema/migration versions
fault matrix version
lease/claim policy version
focused test counts
bounded race-repeat results
coverage ratio
orphan counts
tamper cases exercised
cleanup race cases exercised
full backend result
Ruff result
compile result
frontend result if affected
Mypy current + baseline comparison
exact PR-head CI run/jobs
known limitations
```

Do not describe green workflow status as a Mypy pass if typecheck remains non-blocking/failing.

---

## 22. Acceptance gate for R-HIST-03F

03F may be declared **IMPLEMENTED + TESTED** only when all are true:

1. fault seams cover every critical producer/publication transition;
2. producer rollback/commit crash semantics pass;
3. authority-success-before-ack replay passes;
4. deterministic identities converge under duplicate workers;
5. lease/claim ownership and stale recovery pass;
6. worker death causes no permanent lockout;
7. retry/backoff is bounded and observable where implemented;
8. all tamper classes fail closed;
9. cleanup cannot remove protected roots;
10. source-correction/newer-data fallback attacks are rejected;
11. read paths remain side-effect free under failure;
12. 03E coverage cannot report false 100%;
13. orphan/transitive-break detectors remain correct under races;
14. complete representative state/outcome/revision population passes golden replay;
15. frozen datasets/models/profiles/audits survive restart/replay/tamper tests;
16. same-instrument independent opportunities stay distinct;
17. critical concurrency tests are stable over the chosen bounded repeat profile;
18. no unexplained flaky test remains;
19. focused 03F + full R-HIST retention suite passes;
20. full backend regression passes in pinned/CI environment;
21. Ruff passes;
22. Python compilation passes;
23. frontend passes if affected;
24. Mypy is compared honestly against the current baseline with no unexplained new diagnostics;
25. exact final PR-head GitHub CI is observed and recorded;
26. no live-order/model-auto-approval/strategy-activation authority changed.

**STOP:** if any item fails, FULL R-HIST-03 must remain NOT COMPLETE.

---

## 23. FULL R-HIST-03 gate after 03F

After 03F passes, run one final aggregate acceptance review. Do not infer full-stage completion only from the 03F test module.

Required full-stage assertions:

```text
03A IMPLEMENTED + TESTED
03B IMPLEMENTED + TESTED
03C IMPLEMENTED + TESTED
03D IMPLEMENTED + TESTED
03E IMPLEMENTED + TESTED
03F IMPLEMENTED + TESTED

mandatory producer coverage = 100%
unexplained orphan artifacts = 0
unexplained orphan references = 0
broken transitive lineage = 0
critical crash/replay matrix = PASS
critical concurrency/lease matrix = PASS
critical tamper matrix = PASS
cleanup protection matrix = PASS
read purity = PASS
latest/current substitution attacks = BLOCKED
all-state historical population preservation = PASS
exact PR-head CI = observed
```

Only then may documentation say:

```text
R-HIST-03 = IMPLEMENTED + TESTED
```

That still does **not** mean:

```text
LIVE-DATA-VERIFIED
PIT_APPROVED
MODEL_APPROVED
PRODUCTION_ACCEPTED
EXECUTION_AUTHORIZED
```

Those remain separate capability gates.

---

## 24. Handoff to R-HIST-04

R-HIST-04 may begin implementation only after the full R-HIST-03 gate passes.

03F hands R-HIST-04 a trusted graph that can be moved/copied across HOT/WARM/COLD tiers without losing identity.

R-HIST-04 must then preserve:

- exact object/reference hashes;
- copy verification;
- quarantine on mismatch;
- safe old-copy removal only after verified replacement;
- the same no-latest-substitution law.

03F itself does not implement R-HIST-04.

---

## 25. Autonomous research-agent behavior under failure

A future autonomous TrendForge research agent must follow this rule:

```text
if historical integrity is verified:
    reason from the exact frozen graph
else:
    return BLOCKED / UNKNOWN
    identify the broken reference
    do not learn/promote/rewrite around the fault
```

The agent may assist recovery by:

- locating the exact failed producer/reference;
- explaining which evidence root is missing/tampered;
- replaying an existing deterministic PENDING intent through an approved recovery command;
- proposing remediation.

It may not:

- invent provenance;
- substitute latest data;
- delete evidence of failure;
- reduce the coverage denominator;
- silently regenerate old decisions/features;
- self-approve models/profiles after a fault;
- activate execution.

---

## 26. One-stretch execution rule

The intended continuous build is:

```text
03D RED TESTS
 -> 03D IMPLEMENTATION
 -> 03D GATE

PASS
 -> 03E RED TESTS
 -> 03E IMPLEMENTATION
 -> 03E GATE

PASS
 -> 03F RED TESTS
 -> 03F IMPLEMENTATION
 -> 03F GATE

PASS
 -> FULL R-HIST-03 AGGREGATE GATE

FAIL AT ANY POINT
 -> STOP THERE
 -> preserve evidence
 -> fix/retest same stage
 -> never skip forward
```

This is one continuous engineering stretch with autonomous progression **between passed gates**, not permission to bulldoze through failures.

---

## 27. Final 03F definition

03F is complete when TrendForge can truthfully say:

> Even when processes crash, workers race, leases expire, retries occur after uncertain success, bytes are tampered, cleanup runs concurrently, or newer data exists, my governed historical memory either reconstructs exactly or fails closed. I do not manufacture a healthy past from partial evidence, and my future research brain refuses to learn from memory it cannot prove.

Until that statement is mechanically verified, `R-HIST-03F = NOT COMPLETE` and full `R-HIST-03 = NOT COMPLETE`.
