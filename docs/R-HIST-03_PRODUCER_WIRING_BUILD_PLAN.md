# R-HIST-03 Producer Wiring Build Plan

**Stage:** R-HIST-03 — automatic durable evidence retention at immutable producer boundaries  
**Depends on:** R-HIST-01 retention authority and R-HIST-02 deletion protection  
**Status at plan creation:** R-HIST-01 TESTED; R-HIST-02 TESTED; R-HIST-03 design approved for staged implementation; R-HIST-04+ not implied complete  
**Research safety ceiling:** no live-order authority is added or changed by this stage.

## 1. Mission

R-HIST-03 closes the gap between having a retention authority and actually using it for every historical artifact that TrendForge must later reproduce. The system must not rely on a human remembering to create a retention reference. A durable producer must declare its exact evidence dependency at publication time, and the system must make that declaration replayable, immutable, auditable, and fail closed when proof is missing.

The central invariant is:

> An immutable research artifact that depends on historical market evidence is not fully published until a durable, exact retention relationship exists for that evidence.

This stage is deliberately about **wiring and publication integrity**, not prediction logic. It makes future decision memory, outcome memory, PIT backtesting, model governance, and failure learning trustworthy because the original evidence can no longer silently disappear.

## 2. Non-negotiable laws

1. **Producer-side ownership.** Retention intent is emitted by the write path that creates the immutable artifact, never by a UI/read/refresh path.
2. **Exact lineage, never inference.** Use exact `run_id`, `trading_date`, and/or `content_hash` known at write time. Never guess the latest market snapshot later.
3. **Immutable identity.** A durable `reference_id` can be replayed exactly but cannot be repointed to different evidence.
4. **Same-transaction intent.** When artifact persistence and the outbox share SQLite, the artifact record and retention intent must enter the database in the same producer transaction.
5. **Fail closed for mandatory history.** If required historical proof cannot be established, the artifact must not cross its governed publication boundary.
6. **Idempotent retries.** Process restarts, duplicate jobs, timeout retries, and crash replay must converge on one reference.
7. **No retention writes from reads.** UI refresh, `GET` routes, snapshot reads, historical browsing, and comparison reads must not create retention intent as a side effect.
8. **Complete population.** WAIT, WATCH, REJECT, CONFIRMED where allowed by future stages, no-entry, expired, stopped, target-hit, ambiguous, and censored cases must remain representable. Learning only from winners is prohibited.
9. **Point-in-time law.** The retained evidence is what was available when the artifact was produced, not a later corrected/revised/latest dataset unless the artifact explicitly records a revision relationship.
10. **No live-order expansion.** R-HIST-03 never activates broker execution, changes the WATCH/WAIT/REJECT ceiling, or upgrades evidence into direction.

## 3. Wire / flow

```text
MARKET DATA COLLECTOR
   |
   | immutable manifest run_id / trading_date / content hashes
   v
VALIDATED + VERSIONED OBSERVATIONS
   |
   +----------------------> normal research computation
   |                                  |
   |                                  v
   |                        IMMUTABLE PRODUCER ARTIFACT
   |                        decision/S8/outcome/revision/
   |                        ML dataset/model/profile/audit
   |                                  |
   |                         SAME DB TRANSACTION when possible
   |                                  |
   |                    +-------------+-------------+
   |                    |                           |
   |                    v                           v
   |              ARTIFACT ROW                RETENTION OUTBOX
   |                                            PENDING
   |                                                |
   |                                                | after producer commit
   |                                                v
   |                                      DURABLE REGISTRAR
   |                                                |
   |                                  validate hash + immutable identity
   |                                  resolve exact manifest/object proof
   |                                                |
   |                                                v
   +---------------------------------- HISTORICAL RETENTION AUTHORITY
                                                    |
                                          immutable durable reference
                                                    |
                                                    v
                                             OUTBOX APPLIED
                                                    |
                                                    v
                                       GOVERNED PUBLICATION ALLOWED
```

Crash safety:

```text
artifact+outbox COMMIT -> crash -> reconciler finds PENDING -> register -> APPLIED
register succeeds -> crash before APPLIED -> replay same reference_id -> authority idempotent -> APPLIED
bad/missing/tampered proof -> FAILED_BLOCKING -> publication remains blocked
```

## 4. Why an outbox is required

Directly calling `HistoricalRetentionAuthority.register()` after writing an artifact creates a fatal split-brain window:

```text
artifact committed
process crashes
retention reference never committed
cleanup later sees evidence as unreferenced
history can disappear
```

The outbox removes that silent-loss window. The durable **intent** is committed atomically with the artifact when both share the same SQLite database. Registration can then happen after commit and be retried safely.

Where a producer lives in a different physical store, R-HIST-03 must use either:
- an explicit durable publication state (`PENDING_RETENTION` -> `PUBLISHED`), or
- a transactional outbox in the producer store plus a reconciler.

A best-effort callback is not acceptable for governed artifacts.

## 5. R-HIST-03A foundation contract

New module: `backend/trendforge_api/retention_producer.py`

### `RetentionEvidenceIntent`

Required immutable artifact identity:
- `artifact_type`
- `artifact_id`
- `artifact_version`
- `reference_type`

Required evidence identity: at least one of:
- `run_id`
- `trading_date`
- `content_hash`

Additional field:
- timezone-aware `created_at` normalized to UTC.

Validation:
- blank identities rejected;
- blank run IDs rejected;
- content hash must be exactly 64 lowercase/uppercase-compatible SHA-256 hex characters and is normalized to lowercase;
- naive timestamps rejected;
- no evidence locator => reject before writing.

### Deterministic identity calculation

Canonical lineage material excludes mutable delivery state:

```text
identity = canonical_json({
  artifactType,
  artifactId,
  artifactVersion,
  referenceType,
  runId,
  tradingDate,
  contentHash
})
lineage_digest = SHA256(identity)
event_id = "rhist03:" + lineage_digest
reference_id = lower(referenceType) + ":" + lineage_digest
```

Canonical JSON uses sorted keys and compact separators. This makes retries deterministic across process restarts and avoids mutable symbol-only IDs.

The full payload includes `createdAt` and has a separate `payload_hash` for tamper/corruption detection.

## 6. Outbox schema

`historical_retention_outbox`

| Column | Purpose |
|---|---|
| `event_id` PK | deterministic immutable event identity |
| `reference_id` UNIQUE | exact durable retention reference identity |
| `artifact_type` | producer category |
| `artifact_id` | immutable producer artifact ID |
| `artifact_version` | schema/content version or frozen version |
| `reference_type` | DECISION_VERSION / OUTCOME / REVISION / ML_DATASET / MODEL_VERSION / STRATEGY_PROFILE / AUDIT / TEMPORARY |
| `run_id` | exact collector/manifest lineage when available |
| `trading_date` | exact market date when available |
| `content_hash` | exact market object SHA-256 when available |
| `payload_json` | canonical immutable intent |
| `payload_hash` | SHA-256 of canonical payload |
| `status` | state machine |
| `attempts` | dispatch attempts |
| `created_at` | producer intent time |
| `applied_at` | authority completion time |
| `last_error` | blocking diagnostic |

Initial states:

```text
PENDING -> APPLIED
PENDING -> FAILED_BLOCKING
```

`FAILED_BLOCKING` is intentionally conservative in the first foundation. A later hardening slice may introduce typed retryable operational errors only after the authority exposes typed exception classes. Until then, ambiguity fails closed rather than silently publishing.

## 7. Registrar functions and working

### `initialize_schema(connection=None)`
- additive table creation only;
- accepts caller-owned SQLite connection;
- does not commit caller transaction;
- idempotent.

### `enqueue(intent, connection=None)`
1. validate intent before write;
2. compute deterministic IDs and payload hash;
3. if event exists, require exact payload match;
4. exact replay returns existing receipt;
5. same ID/different material raises immutable-repoint error;
6. if caller owns connection, enqueue participates in the producer transaction;
7. if registrar owns connection, it commits atomically itself.

### `dispatch(event_id)`
1. load outbox row;
2. recompute payload SHA-256;
3. compare payload fields against duplicated indexed columns;
4. reject tamper/corruption before touching retention authority;
5. return immediately if already APPLIED;
6. refuse FAILED_BLOCKING replay until explicit remediation/reconciliation policy exists;
7. increment attempts;
8. construct exact `RetentionReference`;
9. call `HistoricalRetentionAuthority.register`;
10. on failure record blocking state/error;
11. on success mark APPLIED.

### `reconcile_pending(limit)`
Deterministically processes oldest PENDING events by `(created_at, event_id)` with a strict positive batch limit. It is restart-safe.

### `assert_publishable(event_id)`
Returns only if status is APPLIED. PENDING/FAILED/unknown states fail closed.

## 8. Producer map and wiring sequence

### R-HIST-03B — S8 / immutable decision publication
Actual inspected boundaries:
- `selection/cash_post_commit.py` owns `collector_run_id` and `trading_date` after committed source collection.
- `selection/s8_service.py` builds/persists the current S8 scan.
- `selection/s8_persist_run.py` persists immutable S8 payload and state events but does **not** itself carry the original collector manifest run ID.

Therefore the system must **not infer market lineage inside S8 persistence by asking for latest data**.

Preferred wiring:
1. carry exact collector lineage from `CashPipelineRunContext` into a dedicated S8 publication/retention context;
2. persist S8 artifact and outbox intent under one governed publication transaction where feasible;
3. use `DECISION_VERSION` for immutable published decision/scan version evidence;
4. verify the referenced collector run/date resolves in the canonical market manifest authority;
5. only mark S8 publication retention-complete after APPLIED.

A read-only route must not create the durable reference. Existing helper paths that can build missing current S8 state need explicit separation between “build/persist producer command” and “read existing snapshot.”

### R-HIST-03C — outcomes and revisions
For each immutable outcome/revision:
- reference the original decision/opportunity lineage;
- preserve outcome time separately from decision time;
- never replace the original reference when labels change;
- corrections create a REVISION artifact linking old -> new;
- ambiguous/censored outcomes stay explicit, never coerced into win/loss.

### R-HIST-03D — ML datasets, models, profiles, audits
Frozen ML dataset manifests must register `ML_DATASET` references to every evidence partition/hash/run required for reconstruction. Model and profile promotion artifacts must retain both their training/evaluation dataset manifests and governance evidence. Audit artifacts use `AUDIT` references.

A model binary alone is insufficient; the retained graph must support:

```text
model version
 -> training/evaluation dataset manifest
 -> PIT feature manifest
 -> decision/opportunity population
 -> original market evidence hashes/runs
```

### R-HIST-03E — coverage reconciliation
Build a producer registry declaring:
- artifact type;
- authoritative table/store;
- immutable primary/version key;
- required retention reference type;
- lineage extractor;
- publication state field;
- whether retention is mandatory;
- reconciliation query.

Coverage audit calculation:

```text
mandatory_artifacts = count(all governed immutable artifacts)
applied_artifacts   = count(governed artifacts with APPLIED exact retention event)
coverage_ratio      = applied_artifacts / mandatory_artifacts
```

Production acceptance target: `coverage_ratio = 1.0` for the declared producer registry, with zero unexplained orphans.

### R-HIST-03F — fault-injection/golden acceptance
Run crash and corruption tests at every state boundary before declaring the full stage TESTED.

## 9. Transaction and publication state law

A producer that shares the SQLite DB should follow:

```text
BEGIN IMMEDIATE / producer transaction
  INSERT immutable artifact
  INSERT retention outbox PENDING with same connection
COMMIT

dispatch retention event
assert_publishable(event_id)
mark external/public publication visible if a separate publication flag exists
```

If artifact creation rolls back, the outbox must roll back too. This is a required test.

If the dispatcher fails after the artifact transaction, the artifact can remain stored internally but must be classified as not retention-complete for governed publication.

## 10. Concurrency design

The R-HIST-03A foundation is safe under duplicate dispatch because the downstream authority is idempotent and immutable. However, duplicate workers can still perform redundant calls. Before high-volume production acceptance, add a lease/claim state with:
- claim owner UUID;
- lease expiry timestamp;
- conditional state transition;
- stale lease recovery;
- bounded attempts/backoff;
- no permanent lockout after worker death.

Safety does not depend on the optimization: duplicate application must still converge to the same immutable reference.

## 11. Revision and learning semantics

R-HIST-03 must preserve the difference between:
- evidence known at decision time;
- later market outcome;
- later corrected source data;
- later strategy interpretation;
- later model/profile version.

Revision chain example:

```text
Decision v1 -> evidence manifest M1
Outcome o1  -> Decision v1 + post-decision market path P1
Source revision r1 -> M1 -> M2 (does not rewrite Decision v1)
Dataset D7 -> selects Decision v1 + o1 under explicit PIT cutoff
Model M9 -> D7 manifest
```

This prevents revision leakage and makes future failure-memory analysis valid.

## 12. Failure matrix

| Failure | Required behavior |
|---|---|
| producer validation fails | artifact transaction aborts |
| missing lineage | no intent; governed publication blocked |
| unknown run/date/hash | authority fails closed; FAILED_BLOCKING |
| artifact+outbox transaction rolls back | neither survives |
| crash after producer commit | PENDING survives; reconciler resumes |
| crash after authority success before APPLIED | deterministic replay; no repoint |
| duplicate enqueue | exact idempotent return |
| same event ID with changed payload | reject as corruption/repoint |
| payload JSON tampered | hash mismatch; fail before authority |
| indexed columns tampered | JSON/column mismatch; fail before authority |
| protected evidence disappears | existing retention authority fails closed |
| DB lock/storage outage | do not claim publication complete |
| read/UI refresh | zero retention writes |
| later source revision | new revision identity; never mutate old decision lineage |
| model training omits rejected/wait population | dataset validation failure |
| concurrent duplicate dispatcher | same reference identity; no semantic duplication |

## 13. Test plan

### Unit/adversarial
- deterministic IDs across identical intents;
- different artifact version or lineage changes ID;
- uppercase hash normalized;
- invalid hash rejected;
- naive time rejected;
- missing locator rejected;
- enqueue idempotent;
- repoint attempt rejected;
- caller transaction rollback removes outbox row;
- APPLIED replay does not re-register;
- authority failure blocks publication;
- payload tamper and column tamper detected;
- bounded reconciliation order;
- concurrent duplicates converge.

### Integration
- create real market manifest/object;
- persist producer artifact + PENDING outbox;
- dispatch with real `HistoricalRetentionAuthority`;
- prove cleanup cannot remove protected day/run/hash;
- simulate process death between every state transition;
- prove read route performs no writes;
- prove old S8/decision can be reconstructed after newer snapshots exist.

### Regression
- entire backend test suite;
- Ruff;
- known non-blocking Mypy baseline reported honestly;
- frontend tests when shared contracts/docs change;
- exact PR-head CI only.

## 14. Observability and calculations

Required metrics:

```text
pending_count
blocking_count
oldest_pending_age_seconds
p95_apply_latency_seconds
apply_success_ratio = APPLIED / dispatched
blocking_ratio = FAILED_BLOCKING / dispatched
mandatory_coverage_ratio = applied governed artifacts / governed artifacts
duplicate_replay_count
orphan_artifact_count
orphan_reference_count
```

Alert conditions:
- any `FAILED_BLOCKING` for a mandatory producer;
- oldest PENDING exceeds producer SLA;
- coverage below 100% after reconciliation window;
- orphan artifact/reference > 0;
- tamper detection > 0;
- referenced evidence disappearance > 0.

## 15. Security and integrity

- SQLite paths remain explicit and controlled by existing storage configuration.
- Never deserialize executable payloads from the outbox.
- Canonical JSON is data only.
- SHA-256 is integrity identity, not authorization.
- Do not trust a path from an artifact to bypass `market_data_objects`/manifest validation.
- Audit actions must avoid secrets/tokens in `last_error`.
- Future multi-host deployment must add DB-level claim/lease semantics or a transactional queue; do not substitute process memory.

## 16. Build order and STOP gates

1. **03A foundation:** outbox/intent/registrar + adversarial tests.
2. STOP: full exact-head backend/Ruff CI must pass.
3. **03B S8/decision producer wiring** using actual collector lineage boundary.
4. STOP: demonstrate old immutable S8 survives cleanup and replays PIT.
5. **03C outcomes/revisions.**
6. STOP: prove censored/ambiguous/revision chains remain immutable.
7. **03D ML/model/profile/audit producers.**
8. STOP: frozen manifest dependency graph reconstructs exactly.
9. **03E producer registry + reconciliation + coverage audit.**
10. **03F fault injection + exact-head acceptance.**
11. Only then may R-HIST-03 be called fully TESTED. LIVE-DATA-VERIFIED and PRODUCTION-ACCEPTED require later explicit gates.

## 17. Definition of done

R-HIST-03 is not complete merely because the registrar exists. Full completion requires:
- every declared mandatory immutable producer wired;
- 100% producer coverage after reconciliation;
- no read-path side effects;
- exact market lineage, never latest-data inference;
- real authority integration tests;
- crash/retry/tamper tests;
- PIT replay of historical decisions with newer data present;
- backend/Ruff/frontend relevant regression green on exact head;
- known Mypy legacy baseline documented without hiding it;
- no live-order authority introduced.

## 18. Future upgrade hooks

This design intentionally creates extension points for:
- typed retryable vs blocking authority errors;
- multi-worker leases;
- external/object-store evidence locations from R-HIST-04;
- graph traversal for R-HIST-05 PIT dataset manifests;
- R-HIST-06 failure-memory/outcome learning;
- cryptographic signing/attestation if governance later requires it;
- immutable audit ledger and lineage graph visualization.

The intelligence benefit is not “AI magic.” It is reliable memory: future models can learn from the exact evidence, decision context, failures, non-trades, and revisions that truly existed at that historical point.
