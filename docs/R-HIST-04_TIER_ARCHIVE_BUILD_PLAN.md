# R-HIST-04 HOT / WARM / COLD Tier Archive Build Plan

**Stage:** R-HIST-04 — physical historical storage lifecycle without deleting research memory  
**Depends on:** fully wired R-HIST-03 producer retention graph  
**Status at plan creation:** PLAN ONLY; implementation must not begin before the R-HIST-03 gate  
**Governing rule:** **Delete copies, not history.**

## 1. Mission

R-HIST-04 changes the retention model from “old unreferenced data may be removed from the detailed store” to a tiered archive in which canonical research history remains reconstructable while expensive storage is reduced.

Target lifecycle:

```text
TEMP / scratch / retry copies: 1-7 days
HOT:  0-90 days
WARM: 91-365 days
COLD: >365 days
PERMANENT REFERENCES: may move tiers, must not be routine-deleted
```

Tiering changes physical location and access cost. It must never change historical identity, content hash, trading date, manifest lineage, or decision meaning.

## 2. Core laws

1. **Content identity is independent of storage path.** SHA-256 is the object identity; HOT/WARM/COLD are locations.
2. **Copy first, verify, commit, quarantine, then remove the source copy.** Never move-first.
3. **At least one verified canonical copy must exist at every state.** Prefer two during transitions.
4. **Referenced evidence is movable, not routine-deletable.** Permanent references protect history regardless of tier.
5. **PIT reads are tier-transparent.** A consumer resolves by manifest/content hash, not by guessing a current path.
6. **Age uses market/trading semantics, not filesystem mtime.**
7. **Current trading day is never archived/pruned.**
8. **Protection is rechecked before source-copy removal.** A new reference or policy change blocks/replans destructive steps.
9. **Every transition is durable and recoverable.** A process crash at any line has a deterministic next action.
10. **No cross-filesystem rename assumption.** Rename is not a substitute for verified copy across storage media.
11. **No blind object-store trust.** Verify size/hash after write; provider ETag alone is not universally a SHA-256 proof.
12. **No history loss for storage savings.** If target verification cannot be proven, keep source and fail closed.

## 3. Wire / flow

```text
R-HIST-01/02/03 RETENTION GRAPH
          |
          v
TIER PLANNER
  - policy version
  - as_of date
  - age calculation
  - active references
  - existing verified locations
  - capacity/health constraints
          |
          v
IMMUTABLE TRANSITION PLAN
  candidate hashes/runs
  source -> target tier
  expected bytes + hashes
  protection snapshot hash
  plan hash
          |
          v
COPY TARGET
          |
          v
VERIFY TARGET
  exists + exact size + SHA256
          |
          v
REGISTER VERIFIED LOCATION
          |
          v
COMMIT LOCATION METADATA
          |
          v
QUARANTINE SOURCE COPY
          |
          v
RECHECK plan/protection/lease/hash
          |
          +---- changed/unsafe ----> BLOCKED / recover / replan
          |
          v
REMOVE SOURCE COPY AFTER GRACE
          |
          v
COMPLETE + IMMUTABLE AUDIT RECORD
```

PIT read:

```text
manifest run -> content_hash -> location resolver
   HOT verified? use HOT
   else WARM verified? use WARM
   else COLD verified? restore/read COLD
   else FAIL CLOSED: historical evidence unavailable
```

## 4. Tier calculations

Let:

```text
age_days = as_of_date - trading_date
```

Policy:

```text
if age_days < 0: INVALID / clock or lineage defect
if 0 <= age_days <= hot_days: HOT
if hot_days < age_days <= warm_days: WARM
if age_days > warm_days: COLD
```

Default policy target:
- `hot_days = 90`
- `warm_days = 365`
- TEMP retention independently bounded, default 7 days.

Do not use file creation time, modification time, ingestion host clock, or last-access time as business age.

Referenced history uses the same tier calculation for **placement**, but routine deletion eligibility remains false.

## 5. Storage location model

Add an additive table such as `historical_storage_locations`:

| Column | Meaning |
|---|---|
| `content_hash` | immutable SHA-256 identity |
| `tier` | HOT / WARM / COLD |
| `location_uri` | normalized controlled location |
| `byte_size` | expected/verified size |
| `sha256` | reverified identity, normally same content hash |
| `state` | WRITING / VERIFIED / QUARANTINED / LOST / CORRUPT |
| `generation` | monotonically increasing location generation |
| `provider` | filesystem/object-store adapter ID |
| `provider_metadata_json` | non-authoritative operational metadata |
| `verified_at` | last strong verification |
| `created_at` | location creation time |
| `last_scrub_at` | integrity scrub time |

Recommended uniqueness:

```text
UNIQUE(content_hash, tier, location_uri, generation)
```

A content hash may have multiple verified copies.

## 6. Durable transition journal

Add `historical_tier_transitions`:

- `transition_id` primary key
- `content_hash`
- optional `run_id` / `trading_date`
- `source_tier`
- `target_tier`
- `source_location`
- `target_location`
- `expected_size`
- `policy_version`
- `protection_snapshot_hash`
- `plan_hash`
- `state`
- `attempts`
- `lease_owner`
- `lease_expires_at`
- `created_at`, `updated_at`, `completed_at`
- `last_error`

State machine:

```text
PLANNED
  -> COPYING
  -> VERIFIED
  -> COMMITTED
  -> SOURCE_QUARANTINED
  -> COMPLETE

any non-destructive state -> FAILED_RECOVERABLE
any unsafe protection/policy/integrity state -> BLOCKED
```

Every state must be restartable from durable facts, not process memory.

## 7. Transition identity and plan hash

A plan must be immutable. Canonical plan material should include:

```text
policy_version
as_of_date
candidate content_hashes
source locations + generations
target tier/location class
expected byte sizes
protection_snapshot_hash
manifest/run identities where relevant
```

Calculation:

```text
plan_hash = SHA256(canonical_json(plan_material))
transition_id = "rhist04:" + SHA256(content_hash + source_generation + target_tier + plan_hash)
```

Before source-copy removal, recalculate the current protection snapshot and compare it to the plan. If it differs, do not delete; transition becomes BLOCKED or returns to planning.

## 8. Protection snapshot

The planner takes a stable view of:
- active retention reference IDs;
- protected dates;
- protected run IDs;
- protected content hashes;
- policy version;
- current day;
- any active legal/governance hold introduced in future.

Canonicalize and hash this set:

```text
protection_snapshot_hash = SHA256(canonical_json(sorted protection facts))
```

A protection snapshot is not itself permission to delete history; it is a change detector used with current deletion/move law.

## 9. Copy / verify / commit algorithm

For one object:

1. Resolve source by controlled location registry, not arbitrary path input.
2. Verify source exists, is a regular file/object, is within approved root/namespace, has expected size and SHA-256.
3. Acquire durable lease/claim for transition.
4. Mark COPYING.
5. Copy bytes to a temporary target name/key.
6. Flush buffered data; on filesystem call durable flush/fsync where supported.
7. Close target.
8. Reopen/read target and calculate SHA-256 + byte size.
9. Require exact match with immutable content hash and expected size.
10. Atomically finalize target name inside the target filesystem/namespace when supported.
11. Reverify finalized target.
12. Insert/update location record to VERIFIED and mark transition VERIFIED/COMMITTED in one metadata transaction.
13. Confirm at least one VERIFIED target copy exists.
14. Re-read retention protection and transition plan hash.
15. Quarantine source by controlled same-filesystem rename when safe; never delete immediately across an unverified boundary.
16. Mark SOURCE_QUARANTINED.
17. After grace/recovery window and another verification, remove only the old source copy.
18. Mark COMPLETE and write immutable audit facts.

If any verification fails: keep the source; target is CORRUPT/FAILED and must not become canonical.

## 10. Why quarantine is required

A direct source delete after target verification still leaves recovery hazards around metadata commits and unexpected target failures. Quarantine provides a reversible period:

```text
source canonical -> target verified -> source quarantine
```

If a later metadata/read validation fails, source can be restored from quarantine without reconstructing data externally.

Quarantine itself is a copy/location state, not “deleted history.”

## 11. PIT storage resolver

Create a tier-independent resolver contract:

```python
resolve(content_hash, *, require_verified=True) -> HistoricalObjectLocation
open_verified(content_hash) -> BinaryIO / controlled reader
```

Resolution ordering can prefer HOT -> WARM -> COLD for latency, but correctness is identical. Every selected location must be VERIFIED and hash-bound.

Cold restores must not rewrite historical timestamps/lineage. A restored HOT cache is a TEMP/HOT **copy** whose identity is still the same SHA-256.

## 12. Filesystem adapter first, provider abstraction later

Initial implementation should support local/attached filesystem because current MarketDataStore is filesystem-based. Define a narrow adapter boundary:
- `stat`
- `open_read`
- `write_temp`
- `flush_durable`
- `finalize`
- `compute_sha256`
- `quarantine`
- `delete_copy`
- `exists`

A future object-store adapter may implement the same semantics using multipart upload, provider version IDs, server-side integrity metadata, and explicit read-back verification.

Do not bind business policy to S3/Azure/GCS-specific ETag behavior.

## 13. Path and namespace safety

Carry forward R-HIST-02 protections:
- approved roots only;
- resolved path must remain under root;
- reject symlink/reparse traversal where unsafe;
- refuse current-day destructive operations;
- refuse storage-root or object-root deletion;
- target cannot alias source unexpectedly;
- normalize target path/URI before writing;
- no path derived directly from user-controlled hash without strict hex validation;
- quarantine stays under controlled root.

## 14. Failure-recovery matrix

| Failure point | Recovery law |
|---|---|
| disk full during copy | keep source; remove/mark temp target; FAILED_RECOVERABLE |
| process crash while COPYING | inspect target temp; verify or restart copy |
| partial target | never register VERIFIED |
| target hash mismatch | mark CORRUPT; keep source; BLOCKED if repeated |
| target preexists with correct hash | reuse idempotently after verification |
| target preexists with wrong bytes | never overwrite silently; isolate/corrupt state |
| metadata DB failure after target verified | target remains extra copy; reconcile by hash |
| crash after location COMMITTED | resume from durable state |
| source quarantine rename fails | keep both; FAILED_RECOVERABLE |
| crash after quarantine | journal locates source quarantine; resume/restore |
| new retention ref appears mid-transition | protection snapshot mismatch; block source removal |
| policy version changes | replan before destructive action |
| lease owner dies | lease expiry permits deterministic recovery |
| simultaneous movers | conditional lease permits one owner; other exits/reloads |
| DB locked | no source deletion without committed metadata |
| source disappears unexpectedly | target must independently verify; raise integrity incident |
| target disappears after verification | restore/use source if still present; mark target LOST |
| cross-filesystem rename | do not assume atomic; use copy/verify protocol |
| object-store outage | keep local/source copy; retry later |
| provider ETag mismatch semantics | use SHA-256 readback, not ETag assumption |
| clock/timezone anomaly | business age derives from trading_date/as_of date |
| manifest/hash disagreement | fail closed; do not move/delete |

## 15. Immutable archive/cleanup audit ledger

R-HIST-02 currently returns cleanup information but does not create a complete persistent immutable cleanup journal. R-HIST-04 should close this gap with an append-only operational audit record containing:
- archive/cleanup run ID;
- policy version;
- plan hash;
- protection snapshot hash;
- candidate set hash;
- per-object source/target location generations;
- expected/actual size and SHA-256;
- protected/skipped reason;
- copied/verified/quarantined/deleted-copy facts;
- failure/recovery reason;
- timestamps and worker identity.

The audit ledger records **copy lifecycle actions**. It must never be used as authority to rewrite original market evidence.

## 16. Cleanup law after R-HIST-04

Routine cleanup becomes a copy-management operation:

```text
Can I remove this physical copy?
  1. Is it TEMP/duplicate/obsolete source generation?
  2. Is another VERIFIED canonical location available?
  3. Does the manifest/reference graph still resolve?
  4. Did protection/policy stay unchanged?
  5. Is it outside quarantine/grace requirements?
  6. Did path and hash verification pass?
YES -> delete copy, record audit
NO  -> retain/block
```

Deleting the final verified copy of canonical historical evidence is outside routine cleanup authority.

## 17. Tier planner intelligence

The first policy is deterministic age-based placement. Future extensions may optimize cost without changing correctness:
- access frequency;
- anticipated replay/backtest schedule;
- dataset/model dependency fan-out;
- archive provider cost;
- restore latency;
- storage health;
- duplicate count;
- compliance/legal hold.

These inputs may choose **where copies live**, never whether required history exists.

A possible future priority score:

```text
warmth_score =
  0.35 * normalized_recent_access
+ 0.25 * dependency_fanout
+ 0.20 * scheduled_replay_need
+ 0.10 * restore_latency_penalty
+ 0.10 * operational_risk
```

This score must not override retention protections. It is a placement optimization only and must be calibrated/validated before use.

## 18. Storage/reliability calculations

Required measurements:

```text
bytes_by_tier[tier]
objects_by_tier[tier]
verified_copy_ratio = objects_with_verified_location / canonical_objects
redundant_copy_bytes
eligible_to_move_count
transition_success_ratio
transition_failure_ratio
oldest_recovery_backlog_seconds
orphan_location_count
missing_location_count
corrupt_location_count
PIT_resolve_success_ratio_by_tier
PIT_restore_latency_p50/p95/p99
hash_scrub_failure_rate
```

Savings should be reported as moved/reclaimed duplicate bytes, never as “history deleted.”

## 19. Integrity scrubber

Tiered history needs periodic verification. Build a scrubber that:
- samples or schedules every VERIFIED location;
- streams SHA-256 calculation;
- validates size;
- marks CORRUPT/LOST rather than hiding failure;
- checks another verified copy exists;
- raises urgent alert if redundancy falls to one or zero;
- can enqueue repair copy from another verified location.

Scrubbing must be read-only with respect to evidence content.

## 20. R-HIST-04 test plan

### Tier calculation tests
- exact day 0, 90, 91, 365, 366 boundaries;
- leap years/date arithmetic;
- future trading date rejects;
- current day never destructive;
- policy version changes replan.

### Copy/integrity tests
- byte-for-byte copy;
- SHA-256 verify;
- wrong size/hash blocks;
- existing correct target idempotent;
- existing corrupt target isolated;
- fsync/finalization errors retain source.

### Crash/fault injection
Simulate process death after each state:
- PLANNED;
- COPYING partial;
- copied but not verified;
- VERIFIED but metadata uncommitted;
- COMMITTED before quarantine;
- SOURCE_QUARANTINED before source-copy delete;
- source-copy deleted before COMPLETE marker.

Every restart must converge without losing the final verified copy.

### Protection-race tests
- reference created during copy;
- reference created after verification but before quarantine;
- reference created during quarantine grace;
- cleanup/tier process overlap;
- concurrent planners/movers.

### PIT replay tests
For the same historical decision/dataset:
- all evidence HOT;
- mixture HOT/WARM;
- mixture WARM/COLD;
- all COLD;
- restored cold cache;
- one corrupt location with another valid copy.

Resulting reconstructed input hashes and decision-replay inputs must be identical across tiers.

### Path adversarial tests
- symlink escape;
- reparse point;
- `..` traversal;
- root deletion attempt;
- alias source/target;
- invalid hash-derived path;
- quarantine path outside root.

## 21. Build phases and STOP gates

1. **04A metadata + tier policy + dry-run planner.** No byte movement.
2. STOP: plan determinism, protection snapshot, exact candidate proof.
3. **04B filesystem copy/verify adapter.** No source deletion.
4. STOP: fault injection proves every target verified by SHA-256/size.
5. **04C durable journal + leases + recovery.** Still retain old source.
6. STOP: crash at every state recovers deterministically.
7. **04D quarantine + source-copy removal after grace.**
8. STOP: prove at least one verified copy before/after every operation.
9. **04E tier-transparent PIT resolver/read-through cache.**
10. STOP: historical replay hashes identical HOT/WARM/COLD.
11. **04F immutable archive/cleanup audit + scrubber.**
12. **04G real-data volume/capacity/failure acceptance.**
13. Only then can R-HIST-04 be called TESTED. Production acceptance remains a separate explicit gate.

## 22. Migration strategy from current cleanup behavior

Do not switch directly from old deletion to tiering in one destructive deployment.

Recommended rollout:
1. inventory all existing manifests/objects and calculate missing location records;
2. backfill location metadata without moving bytes;
3. run dry-run tier planner and compare with current cleanup candidates;
4. prove every referenced hash/run/date maps to at least one verified location;
5. enable copy-to-WARM only, source retained;
6. observe/replay;
7. enable quarantine only;
8. observe recovery window;
9. enable old source-copy deletion with strict feature flag/governance gate;
10. later enable COLD transition.

Any unexplained object/manifest mismatch is a STOP condition.

## 23. Definition of done

R-HIST-04 is complete only when:
- canonical objects have location metadata;
- tier placement is deterministic and versioned;
- copy/verify uses exact SHA-256 + size;
- transition journal recovers every tested crash point;
- protection is rechecked before destructive copy removal;
- no final verified canonical copy is routine-deletable;
- PIT resolver is tier-transparent;
- historical replay produces identical evidence hashes across HOT/WARM/COLD;
- quarantine and audit ledger are durable;
- integrity scrubber detects corruption/loss;
- backend/Ruff and relevant regression checks pass on exact head;
- live-data volume tests are performed before LIVE-DATA-VERIFIED;
- production operations/recovery drills occur before PRODUCTION-ACCEPTED.

## 24. Future upgrade hooks

The design supports future:
- cloud/object storage adapters;
- multiple archive providers/regions;
- erasure coding or redundancy policies;
- signed manifests and transparency logs;
- cost-aware but protection-constrained placement;
- predictive prefetch before scheduled backtests;
- provenance graph queries from model -> dataset -> decision -> evidence;
- automatic repair from redundant verified copies.

None of these future optimizations may weaken the invariant: **storage optimization is allowed to delete redundant copies, not the historical evidence needed to reproduce TrendForge's past reasoning.**
