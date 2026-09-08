# TrendForge Historical Data Retention, Point-in-Time Memory, and ML Evidence Plan

**Status:** IMPLEMENTATION STARTED — retention authority foundation only  
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

## 2. Defect discovered in the current implementation

`MarketDataStore.cleanup_retention()` currently defaults to retaining only the latest **5 completed trading days** of day directories. With `dry_run=False`, older directories are eligible for deletion. After an old manifest expires, a content-addressed object is also eligible for deletion when it is not referenced by `market_data_latest` or a surviving manifest.

The existing protection set does **not yet know about future decision versions, outcomes, revisions, ML datasets, model evaluations, or audit records**.

This creates a reconstructability defect: a published decision or ML example can outlive the source evidence needed to prove how it was produced.

Changing `5` to `90` would postpone the defect, not solve it. The cleanup authority must become reference-aware first.

## 3. Target lifecycle

| Age / class | Tier | Intended use | Deletion rule |
|---|---|---|---|
| 1–7 days temporary copies | TEMPORARY | retries, downloads, local scratch, duplicate exports | deletable after successful canonicalization if no evidence reference exists |
| 0–90 days | HOT | fast research, recent comparisons, recalculation, debugging | keep online; referenced evidence remains protected regardless of age |
| 91–365 days | WARM | compressed/partitioned historical research | may move to cheaper storage; do not break identity/hash/lineage |
| >365 days | COLD | long-term archive, backtest and ML evidence | may move to archive/object storage; referenced evidence is not routinely deleted |
| Any age with durable evidence reference | PROTECTED | decisions, outcomes, revisions, ML, audit, model/profile lineage | no routine deletion |

The first code foundation implements the HOT/WARM/COLD policy as **classification**, not as destructive movement.

## 4. Evidence classes that require durable retention

The initial retention authority supports these reference types:

1. `DECISION_VERSION` — immutable published assessment of an opportunity.
2. `OUTCOME` — trigger/no-entry/expiry/ambiguous/censored and realized result evidence.
3. `REVISION` — corrected or superseded observations and their prior versions.
4. `ML_DATASET` — frozen point-in-time dataset manifests used for training/evaluation.
5. `MODEL_VERSION` — model artifact/evaluation lineage.
6. `STRATEGY_PROFILE` — exact strategy/profile configuration used by a decision.
7. `AUDIT` — governance and reproducibility evidence.
8. `TEMPORARY` — explicitly bounded, expiring references only.

Decision/outcome/revision/ML/model/profile/audit evidence must not be converted to temporary retention merely to save disk space.

## 5. Identity and transitive protection

A retention reference may identify evidence by one or more of:

- `trading_date`
- collector/manifest `run_id`
- immutable SHA-256 `content_hash`

Protection must expand transitively:

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

A referenced run therefore protects its trading date and all content objects in its point-in-time manifest. A referenced content hash resolves back to manifests/dates that used it. Missing or contradictory identity is a fail-closed error, not permission to delete.

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

Rejected, WAIT, WATCH, no-entry, expired, and ambiguous opportunities are therefore useful research data and should not be discarded merely because no trade was taken.

## 8. Relationship to the main TF roadmap

This branch is a cross-cutting **retention-safety foundation**. It does not claim completion of later roadmap stages and does not skip their dependencies.

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

### R-HIST-01 — Retention authority contract — STARTED

Implement:

- `RetentionPolicy`
- HOT/WARM/COLD classification
- typed durable reference classes
- additive SQLite retention-reference table
- identity validation against content objects/manifests
- active reference resolution
- transitive protection set
- fail-closed deletion assertion
- adversarial tests

No file deletion is performed by this authority.

### R-HIST-02 — Wire protection into destructive cleanup — NEXT

Before `MarketDataStore.cleanup_retention(..., dry_run=False)` may delete anything:

1. load the active protection set;
2. exclude protected trading dates;
3. exclude protected manifest runs;
4. exclude protected content hashes;
5. re-resolve immediately before deletion to avoid stale protection state;
6. fail closed on missing/invalid reference tables or inconsistent lineage;
7. record an immutable cleanup report of what was evaluated, retained, moved, or deleted.

Until this wiring is verified, the existing destructive 5-day cleanup must not be treated as safe for research-history preservation.

### R-HIST-03 — Producer wiring

Register evidence references automatically when these artifacts are created:

- immutable S7/S8 decision versions;
- publication snapshots;
- outcomes;
- revisions/supersessions;
- frozen ML datasets;
- model/profile versions used for evaluation or publication;
- audit/acceptance artifacts.

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

Persist and analyze the complete opportunity population, not only winners/trades. Use it to calibrate strategy-specific ranking, uncertainty, failure risk, and regime behavior.

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
6. **A referenced content hash must exist before the reference is accepted.**
7. **Archive/move operations must verify content hashes before deleting a source copy.**
8. **Historical corrections create new versions/supersession relationships; they do not rewrite the past.**
9. **ML datasets are frozen manifests, never views over mutable current data.**
10. **Retention changes do not grant trading/execution authority.**

## 11. Current implementation checkpoint

As of this branch:

- plan documented: **YES**
- tests-first retention contract: **YES**
- `historical_retention.py` foundation: **IMPLEMENTED**
- additive reference schema: **IMPLEMENTED**
- HOT/WARM/COLD classification: **IMPLEMENTED**
- permanent/temporary evidence rules: **IMPLEMENTED**
- manifest/hash/date validation: **IMPLEMENTED**
- transitive protection-set computation: **IMPLEMENTED**
- fail-closed deletion assertion API: **IMPLEMENTED**
- existing `MarketDataStore.cleanup_retention()` wired to authority: **NO — R-HIST-02**
- decision/outcome/ML producers automatically register references: **NO — R-HIST-03**
- WARM/COLD physical archive mover: **NO — R-HIST-04**
- point-in-time ML dataset builder: **NO — R-HIST-05**
- real-data verification: **NO**
- production acceptance: **NO**
- live orders enabled: **NO**

This distinction is deliberate: green unit tests for the retention authority do not prove end-to-end historical reconstructability or ML quality.
