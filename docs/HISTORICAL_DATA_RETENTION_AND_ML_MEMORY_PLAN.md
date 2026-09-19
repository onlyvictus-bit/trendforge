# TrendForge Historical Data Retention, Point-in-Time Memory, and ML Evidence Plan

**Status:** R-HIST-01 IMPLEMENTED + TESTED; R-HIST-02 IMPLEMENTED, exact-head CI pending  
**Branch:** `fix/retention-evidence-safety`  
**Base:** TF-01 exact head `19a8c762314cdb7b54556c17c8ae5a46ad7325e8`  
**Trading authority:** unchanged; no live-order capability is added by this work.

## 1. Why this is required

TrendForge cannot become a high-quality decision system if it remembers only the latest market state. A decision engine must be able to answer, later and exactly:

- What did the system know at the decision timestamp?
- Which source bytes and normalized observations were used?
- Which strategy/profile/model version produced the opportunity?
- Which filters and gates were active?
- What entry, stop, target, expiry, and invalidation plan was published?
- What actually happened after publication?
- Was a source corrected later, and did the original decision use the pre-correction or post-correction observation?
- Can the exact decision be reconstructed without using information that was unavailable at the time?

Without that history, outcome analysis, backtesting, ML training, failure-memory, calibration, drift detection, and strategy comparison become unreliable.

The governing rule is:

> **Delete copies, not history.**

Age determines storage tier. Evidence references determine whether data may be deleted.

## 2. Defect and current mitigation

The legacy `MarketDataStore.cleanup_retention()` defaults to retaining only the latest **5 completed trading days** of day directories. Historically, with `dry_run=False`, older directories were eligible for deletion and an old content-addressed object became eligible once it was no longer referenced by `market_data_latest` or a surviving manifest.

R-HIST-02 now wires the historical retention authority into that real cleanup path. A protected decision/outcome/revision/ML/model/profile/audit date, run, or content hash is excluded from ordinary age-based deletion. Cleanup also re-resolves protection immediately before destructive work and fails closed if lineage/protection changed or disappeared.

This does **not** make five days the desired long-term lifecycle. It only prevents age-based cleanup from deleting durable referenced evidence. R-HIST-04 still needs to replace blind aging with HOT -> WARM -> COLD/archive movement.

Changing `5` to `90` alone would still only postpone the reconstructability problem. Reference-aware protection is the required authority.

## 3. Target lifecycle

| Age / class | Tier | Intended use | Deletion rule |
|---|---|---|---|
| 1–7 days temporary copies | TEMPORARY | retries, downloads, local scratch, duplicate exports | deletable after successful canonicalization if no evidence reference exists |
| 0–90 days | HOT | fast research, recent comparisons, recalculation, debugging | keep online; referenced evidence remains protected regardless of age |
| 91–365 days | WARM | compressed/partitioned historical research | may move to cheaper storage; do not break identity/hash/lineage |
| >365 days | COLD | long-term archive, backtest and ML evidence | may move to archive/object storage; referenced evidence is not routinely deleted |
| Any age with durable evidence reference | PROTECTED | decisions, outcomes, revisions, ML, audit, model/profile lineage | no routine deletion |

HOT/WARM/COLD is currently a classification contract. Physical tier movement is R-HIST-04.

## 4. Evidence classes that require durable retention

The retention authority supports these reference types:

1. `DECISION_VERSION` — immutable published assessment of an opportunity.
2. `OUTCOME` — trigger/no-entry/expiry/ambiguous/censored and realized result evidence.
3. `REVISION` — corrected or superseded observations and their prior versions.
4. `ML_DATASET` — frozen point-in-time dataset manifests used for training/evaluation.
5. `MODEL_VERSION` — model artifact/evaluation lineage.
6. `STRATEGY_PROFILE` — exact strategy/profile configuration used by a decision.
7. `AUDIT` — governance and reproducibility evidence.
8. `TEMPORARY` — explicitly bounded, expiring references only.

Decision/outcome/revision/ML/model/profile/audit evidence must not be converted to temporary retention merely to save disk space.

Reference IDs are immutable: registering the same ID with different evidence is rejected rather than silently repointing historical lineage.

## 5. Identity and transitive protection

A retention reference may identify evidence by one or more of:

- `trading_date`
- collector/manifest `run_id`
- immutable SHA-256 `content_hash`

Protection expands transitively:

```text
DECISION / OUTCOME / ML DATASET
            |
            v
      retention reference
            |
     +------+------+
     |             |
     v             v
   run_id      content_hash
     |             |
     v             |
 trading_date <----+
     |
     v
point-in-time manifest
     |
     v
exact source object hash(es)
```

A referenced run protects its trading date and all content objects in its point-in-time manifest. A referenced content hash resolves back to manifests/dates that used it. A date-only reference must resolve to a real manifest. Missing or contradictory identity is a fail-closed error, not permission to delete.

Protection resolution also verifies that protected run/date/hash evidence still exists. If a durable reference survives but its underlying manifest/object disappears, cleanup fails instead of normalizing the corruption away.

## 6. ML and research correctness

ML must never train directly from mutable current-state tables.

Required flow:

```text
Historical immutable evidence
        -> point-in-time reconstruction
        -> feature generation using only then-available inputs
        -> exact decision/opportunity context
        -> outcome labeling
        -> frozen dataset manifest + dependency hashes
        -> train/validation/test split by time/regime
        -> model version
        -> out-of-sample / walk-forward evaluation
        -> shadow comparison
        -> governed promotion
```

This prevents three major errors:

- **Look-ahead leakage:** training with data published after the historical decision timestamp.
- **Revision leakage:** using a corrected value as if the system knew it earlier.
- **Survivorship/history loss:** keeping the final result while deleting the evidence that produced it.

## 7. What should be learned from history

Historical memory is not only for predicting `price up/down`. TrendForge should accumulate evidence for:

- strategy-specific direction probability;
- probability target is reached before stop;
- expected MFE and MAE distributions;
- setup failure modes;
- regime-conditioned performance;
- event-risk behavior;
- liquidity/slippage/cost behavior;
- gap and overnight behavior;
- false-breakout/reversal behavior;
- freshness and source-quality effects;
- calibration of confidence vs realized outcome;
- which gate/filter prevented a bad trade;
- which rejected/WAIT opportunity later became valid;
- model/profile drift across time.

Rejected, WAIT, WATCH, no-entry, expired, ambiguous and censored opportunities are useful research data and should not be discarded merely because no trade was taken.

## 8. Relationship to the main TF roadmap

This branch is a cross-cutting retention-safety foundation. It does not claim completion of later roadmap stages and does not skip their dependencies.

| Roadmap stage | Retention dependency |
|---|---|
| TF-06 timestamps/revisions | preserve observation versions and correction chronology |
| TF-07 identity | stable instrument/opportunity/decision/evidence identifiers |
| TF-20 recalculation | reproduce dependencies and invalidate only affected outputs |
| TF-21 immutable publication | publish decision version + dependency hash/reference set |
| TF-22 UI/history | retrieve immutable current/history without overwriting prior decisions |
| TF-23 outcomes | preserve exact plan and point-in-time outcome evidence |
| TF-24 backtest | reconstruct historical availability without look-ahead |
| TF-25 real-data/shadow acceptance | compare shadow/live-like outputs against preserved evidence |

TF-02 through TF-05 remain separate roadmap work. This change must not be used to silently mark them complete.

## 9. Implementation stages for retention

### R-HIST-01 — Retention authority contract — IMPLEMENTED + TESTED

Implemented:

- `RetentionPolicy`
- HOT/WARM/COLD classification
- typed durable reference classes
- additive SQLite retention-reference table
- evidence identity validation against content objects/manifests/dates
- immutable reference IDs
- active reference resolution
- transitive protection set
- fail-closed disappearance/corruption detection
- fail-closed deletion assertion
- adversarial tests

The authority itself performs no file deletion.

### R-HIST-02 — Wire protection into destructive cleanup — IMPLEMENTED, FINAL CI PENDING

`MarketDataStore.cleanup_retention()` now:

1. loads the active protection set before computing deletion eligibility;
2. excludes protected trading dates from expired day-directory cleanup;
3. excludes protected content hashes from object garbage collection;
4. preserves protected manifest runs through transitive date/hash protection;
5. re-resolves protection immediately before destructive work;
6. fails closed if the protection set changes during the cleanup window;
7. calls deletion assertions for candidate dates/runs/hashes;
8. fails closed when protected run/date/hash lineage has disappeared or is inconsistent;
9. preserves existing current-day, path, symlink/reparse and object-root safety checks;
10. preserves `dry_run=True` as the default.

Adversarial integration tests cover:

- durable decision reference protects old date/run/hash;
- ML hash reference protects its point-in-time manifest transitively;
- expired temporary reference becomes deletable;
- disappeared protected run causes delete-nothing failure;
- a new durable reference appearing during cleanup causes delete-nothing failure;
- genuinely unprotected old history remains eligible for cleanup.

R-HIST-02 is not PRODUCTION-ACCEPTED until exact-head CI and later real-data/shadow acceptance are recorded.

### R-HIST-03 — Producer wiring — NEXT

Register evidence references automatically when these artifacts are created:

- immutable S7/S8 decision versions;
- publication snapshots;
- outcomes;
- revisions/supersessions;
- frozen ML datasets;
- model/profile versions used for evaluation or publication;
- audit/acceptance artifacts.

This is the next major correctness step. Manual retention references alone are not enough for autonomous historical memory.

### R-HIST-04 — Tier movement, not blind deletion

Implement storage movement with hash verification:

- HOT -> WARM compression/partitioning;
- WARM -> COLD archive/object storage;
- retain stable logical identity and content hash;
- verify destination hash before deleting a source copy;
- keep restore/read path deterministic;
- maintain archive health checks.

### R-HIST-05 — Point-in-time dataset builder

Build deterministic historical datasets from exact availability timestamps and revisions. Every generated dataset receives:

- `dataset_version_id`;
- creation timestamp;
- feature schema/version;
- strategy/profile/version;
- source dependency hashes;
- label definition/version;
- train/validation/test periods;
- leakage audit result;
- content hash.

### R-HIST-06 — Outcome/failure memory

Persist and analyze the complete opportunity population, not only winners/trades. Use it to calibrate strategy-specific ranking, uncertainty, failure risk and regime behavior.

### R-HIST-07 — Acceptance gates

Do not call historical memory production-accepted until:

- cleanup cannot delete referenced evidence;
- archived objects round-trip with the same hash;
- historical decisions reproduce from retained inputs;
- corrections/revisions reconstruct what was known at each timestamp;
- dataset leakage tests pass;
- whole-system backtest uses point-in-time availability;
- shadow results and outcome labeling have been verified on real data.

## 10. Safety invariants

1. **Age never overrides an active evidence reference.**
2. **Unknown evidence identity fails closed.**
3. **A permanent evidence class cannot receive an expiry.**
4. **A temporary reference must have an explicit expiry.**
5. **A protected run must resolve to the same trading date recorded by its reference.**
6. **A referenced content hash must exist before the reference is accepted and while it remains protected.**
7. **Reference IDs are immutable and cannot be repointed to different evidence.**
8. **Archive/move operations must verify content hashes before deleting a source copy.**
9. **Historical corrections create new versions/supersession relationships; they do not rewrite the past.**
10. **ML datasets are frozen manifests, never views over mutable current data.**
11. **Retention changes do not grant trading/execution authority.**

## 11. Current implementation checkpoint

As of this branch:

- plan documented: **YES**
- tests-first retention contract: **YES**
- `historical_retention.py` foundation: **IMPLEMENTED**
- additive reference schema: **IMPLEMENTED**
- HOT/WARM/COLD classification: **IMPLEMENTED**
- permanent/temporary evidence rules: **IMPLEMENTED**
- immutable reference identity: **IMPLEMENTED**
- manifest/hash/date validation: **IMPLEMENTED**
- transitive protection-set computation: **IMPLEMENTED**
- protected-evidence disappearance detection: **IMPLEMENTED**
- fail-closed deletion assertion API: **IMPLEMENTED**
- existing `MarketDataStore.cleanup_retention()` wired to authority: **IMPLEMENTED — R-HIST-02**
- R-HIST-02 exact final-head CI: **PENDING**
- decision/outcome/ML producers automatically register references: **NO — R-HIST-03**
- WARM/COLD physical archive mover: **NO — R-HIST-04**
- point-in-time ML dataset builder: **NO — R-HIST-05**
- complete opportunity/outcome failure memory: **NO — R-HIST-06**
- real-data verification: **NO — R-HIST-07**
- production acceptance: **NO**
- live orders enabled: **NO**

Green unit tests for retention do not by themselves prove end-to-end historical reconstructability, leakage-free ML quality, profitable trading, or live execution safety.
