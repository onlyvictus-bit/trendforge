# TrendForge TF-10 -> TF-21 Scanner / Strategy Trading-Brain Architecture and Build Plan

**Audit date:** 2026-09-13  
**Repository:** `onlyvictus-bit/trendforge`  
**Audited branch before this document commit:** `feat/rhist03-producer-wiring` at `79e82a0e2a02d5c62d7b901438e3d2633734984f`  
**Current accepted R-HIST code checkpoint:** R-HIST-03D at `fce62874a61e4e2bb6d939bef6d0811e5a266996`  
**Status:** **PLAN / ARCHITECTURE ONLY — TRADING-BRAIN IMPLEMENTATION NOT STARTED BY THIS DOCUMENT**  
**Immediate current stage:** R-HIST-03E producer coverage/reconciliation  
**Hard prerequisite after 03E:** R-HIST-03F full fault/concurrency/golden acceptance  
**Trading authority:** unchanged. TrendForge v1 remains research-only/read-only. This plan adds no broker execution, account access, order placement, autonomous trading authority, probability-of-profit claim, model approval, strategy activation, or source activation.

---

## 0. Why this document exists

The system-brain roadmap already states the correct future direction:

```text
TF-10  Stable Opportunity / Episode Identity
   |
   v
TF-11  Neutral Discovery + Multi-reason Admission
   |
   v
TF-12  Versioned Feature Reuse
   |
   v
TF-13  Executable Strategy/Profile Bindings
   |
   v
TF-14  Equity Swing Strategy
   |
   v
TF-15  Equity Intraday Continuation
   |
   v
TF-16  Reversal Strategies
   |
   v
TF-17  Event / Ownership Strategy
   |
   v
TF-18  Commodity Strategies
   |
   v
TF-19  Net-Cost Eligibility + Comparable Ranking
   |
   v
TF-20  Dependency / Clock / Contract Incremental Recalculation
   |
   v
TF-21  Immutable Strategy Decision Publication
```

The roadmap also already says that discovery must be separated from direction, that one instrument can own several independent opportunities, and that a profile declaration is not proof of an executable strategy.

What was missing was one coding-grade document that joins those requirements to the **current code owners, current defects, identity model, strategy contract, scanner contract, caching/dependency model, persistence model, R-HIST memory, fault semantics, performance model, migration path and stage-by-stage acceptance gates**.

This file fills that gap. It does **not** replace File A, `AGENTS.md`, the system-brain roadmap, the R-HIST plans, CURRENT_STATE, BUILD_STATUS or VALIDATION. Runtime code and observed test/runtime evidence remain the final truth.

---

# 1. Authority and conflict rules

Use this order when implementing anything described here:

```text
current explicit user instruction
        |
        v
AGENTS.md
        |
        v
File A: docs/fable/new_merge_PLAN_2026-07-18.md
        |
        v
docs/TRENDFORGE_SYSTEM_BRAIN_AND_IMPLEMENTATION_ROADMAP_2026-09-08.md
        |
        v
docs/CURRENT_STATE.md
        |
        +--> docs/BUILD_STATUS.md
        +--> docs/VALIDATION.md
        |
        v
R-HIST plans / accepted implementation evidence
        |
        v
this TF-10 -> TF-21 coding plan
        |
        v
current code + tests + current runtime evidence
```

If this file conflicts with File A on product scope, public states, no-execution rules, source authority, evidence-strength semantics, PIT requirements, or safety ceilings, **File A / the stricter safety rule wins**.

If this file conflicts with newer proven runtime code, stop and amend this file; do not force code to match stale documentation.

---

# 2. Audit method and scope

The following current governing and affected files were reviewed before writing this plan:

### Current authority / readiness / build order

- `AGENTS.md`
- `docs/CURRENT_STATE.md`
- `docs/BUILD_STATUS.md`
- `docs/VALIDATION.md`
- `docs/fable/new_merge_PLAN_2026-07-18.md`
- `docs/fable/remaining_build/README.md`
- `docs/fable/remaining_build/REMAINING_PROJECT_BUILD_FILES.md`
- `docs/TRENDFORGE_SYSTEM_BRAIN_AND_IMPLEMENTATION_ROADMAP_2026-09-08.md`
- `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md`

### Historical-memory safety

- `docs/HISTORICAL_DATA_RETENTION_AND_ML_MEMORY_PLAN.md`
- `docs/R-HIST-03E_PRODUCER_COVERAGE_RECONCILIATION_BUILD_PLAN.md`
- `docs/R-HIST-03F_FAULT_INJECTION_CONCURRENCY_GOLDEN_ACCEPTANCE_BUILD_PLAN.md`
- `docs/fable/RHIST03E_EXECUTION_2026-09-11.md`
- PR #6 current description/head and accepted 03D evidence

### Current contracts / discovery / strategy-adjacent runtime

- `backend/trendforge_api/selection/contracts.py`
- `backend/trendforge_api/feature_registry.py`
- `backend/trendforge_api/selection/profile_source_contracts.py`
- `backend/trendforge_api/selection/attention_order.py`
- `backend/trendforge_api/selection/cash_c1_rank.py`
- `backend/trendforge_api/selection/s3_cheap_discovery.py`
- `backend/trendforge_api/selection/r5_live.py`
- `backend/trendforge_api/scanners/registry.py`
- `backend/trendforge_api/selection/s7_state_gates.py`
- `backend/trendforge_api/selection/s8_persist_run.py`
- `backend/trendforge_api/selection/store.py`
- `backend/trendforge_api/scanner_scheduler.py`

Repository-wide symbol searches were also performed for first-class `opportunity_id`, `strategy_id`, `setup_episode`, `decision_version_id` and `StrategyDefinition`. No current runtime implementation of those first-class concepts was found in the inspected branch.

This is a line-by-line review of the current governing and affected architecture surface, not a claim that every historical archive, generated file, binary/data inventory or obsolete backup in the repository was semantically re-audited. Historical files remain evidence, not current authority.

---

# 3. Executive audit verdict

## 3.1 The intended architecture is correct

The future brain should remain:

```text
MARKET DATA
    |
    v
SCANNERS / DISCOVERY
    |
    |  question: "Which instruments are interesting enough to investigate?"
    |
    v
DISCOVERY CANDIDATE + ONE OR MORE REASONS
    |
    v
STRATEGY ROUTER
    |
    +----------------+----------------+----------------+----------------+
    |                |                |                |
    v                v                v                v
INTRADAY         REVERSAL          SWING            EVENT
CONTINUATION
    |                |                |                |
    v                v                v                v
INDEPENDENT STRATEGY-SPECIFIC OPPORTUNITIES
    |
    v
STRATEGY-SPECIFIC FEATURES + GATES + TRIGGER / INVALIDATION / COST
    |
    v
COMPARABLE OPPORTUNITY RANKING
    |
    v
IMMUTABLE DECISION VERSION
```

The scanner must **not** decide the trade direction for every downstream strategy.

Example:

```text
Scanner discovers INFY
reasons:
- abnormal activity
- -3.2% move
- sector weakness

Scanner output is NOT:
INFY = SHORT

Correct fan-out:
INFY
 |
 +-- 5m bearish continuation opportunity
 |      -> strategy evaluates SHORT independently
 |
 +-- 5m failed-breakdown reversal opportunity
 |      -> strategy evaluates LONG independently
 |
 +-- Daily swing opportunity
 |      -> evaluates independently
 |
 +-- Event / ownership opportunity
        -> evaluates independently
```

## 3.2 The codebase contains valuable foundations

Preserve and extend these rather than rebuilding them:

- `InstrumentIdentity` and deterministic `stable_id()`.
- point-in-time lineage contracts.
- typed gates and mandatory/stage-local gate scope.
- `FeatureContract` and the existing feature registry.
- scanner definitions that are explicitly non-authoritative for confirmation.
- source-profile contracts that explicitly say registration is not runtime activation.
- evidence-family/correlation controls.
- bulk history loading patterns.
- request-scoped snapshot consistency.
- immutable R-HIST retention/publication/outbox foundations.
- R16/R18 PIT/governance foundations.

## 3.3 The brain layer is not fully implemented yet

The following are not currently first-class runtime contracts:

```text
stable setup_episode_id
stable opportunity_id
strategy_id + strategy_version as an executable registry
strategy router
neutral multi-reason canonical discovery pool
strategy-specific direction hypothesis independent of discovery direction
feature artifact/dependency digest contract usable for exact reuse
strategy-evaluation cache identity
comparable_group identity
immutable per-opportunity decision_version_id
atomic per-opportunity current publication pointer
```

## 3.4 Four current couplings are especially important

### Coupling A — current attention is not direction-neutral

`selection/attention_order.py` and `cash_c1_rank.py` use positive return percentile in attention ranking. With equal activity, a strong negative mover can rank below an equally abnormal positive mover.

**TF-11 must separate abnormality/attention from bullish/bearish strategy direction.**

### Coupling B — S3 cannot independently admit event-only instruments

`build_s3_cheap_discovery()` iterates `r2.rows`. Therefore an instrument that appears only in a valid event/ownership source cannot independently enter the canonical S3 pool if R2 did not already contain it.

**TF-11 must allow OR-style multi-reason admission from validated reason producers.**

### Coupling C — R5 structure profile follows discovery direction

`r5_live.py::_profile(direction)` receives upstream `EvidenceDirection` and chooses the structural profile from it.

That means discovery direction can constrain later structure hypotheses.

**TF-10/TF-13 must move direction ownership to each strategy opportunity.**

### Coupling D — persistence is still scan/profile/symbol oriented

Current selection persistence stores scan runs plus symbol candidates. S8 is one scan blob and current S8 laws intentionally reject `CONFIRMED`.

**TF-21 needs an additive opportunity-level immutable publication model. Existing S8/R16 history must not be rewritten in place.**

---

# 4. Non-negotiable identity law

TrendForge must permanently distinguish these identities:

```text
SOURCE OBSERVATION
       !=
INSTRUMENT
       !=
DISCOVERY REASON
       !=
DISCOVERY CANDIDATE
       !=
SETUP EPISODE
       !=
OPPORTUNITY
       !=
STRATEGY EVALUATION
       !=
DECISION VERSION
       !=
OUTCOME VERSION
```

Also:

```text
DISCOVERY DIRECTION
       !=
STRATEGY DIRECTION

DISCOVERY PRIORITY
       !=
EVIDENCE STRENGTH
       !=
WIN PROBABILITY
       !=
EXECUTION AUTHORITY
```

No future patch may collapse these simply to save database columns or DTOs.

---

# 5. Hard build gate: do not build the brain before memory is certified

The immediate sequence remains:

```text
CURRENT
   |
   v
R-HIST-03E
Producer coverage / reconciliation
   |
   | PASS only
   v
R-HIST-03F
fault + race + restart + corruption + golden acceptance
   |
   | PASS only
   v
FULL R-HIST-03 ACCEPTANCE
   |
   | historical memory foundation certified
   v
============================================================
TRADING-BRAIN BUILD MAY START
============================================================
   |
   v
TF-10 -> TF-11 -> TF-12 -> TF-13 -> TF-14 ... TF-21
```

### Why this order is mandatory

Once the strategy brain exists, TrendForge will produce and later learn from:

```text
discovery reasons
opportunity episodes
strategy evaluations
WAIT / WATCH / REJECT populations
published decision versions
no-entry cases
outcomes
feature vintages
cost assumptions
strategy/profile versions
failed setups
```

If historical protection is incomplete, the future research/ML layer may learn from a selectively surviving subset and produce false confidence.

Therefore:

> **The brain must not be allowed to become more intelligent than its memory is trustworthy.**

---

# 6. Full upline -> brain -> downline architecture

```text
UPLINE: SOURCE / TIME / IDENTITY TRUTH
============================================================
Official / approved source-specific acquisition
       |
       v
raw immutable bytes / content hash
       |
       v
parser + schema + source identity
       |
       v
normalized versioned observation
       |
       +-- event time
       +-- published time
       +-- available time
       +-- received time
       +-- revision identity
       +-- content hash
       |
       v
point-in-time canonical store
       |
       v
R-HIST protected evidence roots

CHEAP SHARED COMPUTATION
============================================================
       |
       v
identity / tradability prerequisites
       |
       v
cheap shared feature plane
       |
       +-- activity abnormality
       +-- absolute move abnormality
       +-- gap
       +-- event presence
       +-- ownership/disclosure reason
       +-- OI activity
       +-- liquidity/activity change
       +-- developing structure reason
       +-- sector/index dislocation
       +-- commodity context reason
       |
       v
TF-11 NEUTRAL MULTI-REASON DISCOVERY POOL
       |
       v
DiscoveryCandidate(instrument, reasons[])

STRATEGY BRAIN
============================================================
       |
       v
TF-10 identity / episode layer
       |
       v
TF-13 strategy router
       |
       +----------------+----------------+----------------+
       |                |                |                |
       v                v                v                v
TF-14 Swing       TF-15 Intraday   TF-16 Reversal   TF-17 Event
                                                     |
                                                     +-- TF-18 Commodity families
       |
       v
Independent OpportunityIdentity objects
       |
       v
TF-12 feature dependency resolution
       |
       +-- reuse exact valid feature
       +-- compute only missing dependency
       |
       v
strategy evaluator
       |
       +-- required features
       +-- optional context
       +-- prohibited inputs
       +-- closed-bar/session/freshness rules
       +-- RS contract
       +-- event contract
       +-- liquidity/tradability
       +-- trigger / invalidation / target
       +-- cost eligibility
       |
       v
typed StrategyEvaluation

FINAL QUALITY + PUBLICATION
============================================================
       |
       v
TF-19 comparable-group eligibility + ranking
       |
       v
TF-21 immutable DecisionVersion
       |
       +-- exact strategy definition hash/version
       +-- exact opportunity identity
       +-- exact discovery reason references
       +-- exact feature references
       +-- exact gate policy/results
       +-- exact source/evidence roots
       +-- exact cost/tradability assumptions
       +-- decision time / cutoff / valid-until
       |
       v
atomic current pointer per opportunity
       |
       v
transactional publication/outbox event

DOWNLINE
============================================================
       |
       +--> read-only UI / alerts
       +--> immutable history
       +--> R16 exact outcome evaluation
       +--> R18 governance
       +--> PIT datasets / failure memory
       +--> whole-selector backtesting
       +--> future ML / analog research
```

---

# 7. Hybrid execution model: fast scanner, bounded strategies, deep offline research

The future system should be hybrid, not one giant synchronous `scan_everything()` function.

## Lane A — FAST DISCOVERY LANE

Purpose:

> Find instruments worth investigating as cheaply as possible.

Properties:

- broad universe;
- batch reads;
- cheap deterministic features;
- direction-neutral admission;
- multiple reasons preserved;
- no full strategy calculation;
- no expensive options/event enrichment unless needed for discovery;
- no public CONFIRMED authority;
- no quantity/order output.

Target complexity should be approximately proportional to the universe and already-batched source roots rather than per-symbol network calls.

## Lane B — STRATEGY EVALUATION LANE

Purpose:

> Evaluate only routed opportunities using the exact features each strategy declares.

Properties:

- bounded candidate population;
- independent strategy opportunities;
- exact required/optional/prohibited feature contract;
- feature reuse by semantic key + dependency digest;
- strategy-specific gates;
- expensive enrichment only after routing says it is relevant;
- fail closed on missing mandatory proof.

## Lane C — PUBLICATION / CURRENT-STATE LANE

Purpose:

> Validate and publish complete immutable decisions.

Properties:

- no browser-triggered recomputation requirement;
- append immutable decision version;
- atomic current pointer;
- outbox/notification after committed decision;
- stale/expired state comes from time/dependency invalidation, not hidden browser logic.

## Lane D — PIT / OUTCOME / ML RESEARCH LANE

Purpose:

> Learn only from reconstructed historical truth.

Properties:

- asynchronous/offline;
- exact then-available data;
- complete opportunity population, not only traded/winning rows;
- frozen datasets;
- walk-forward/holdout governance;
- no feedback from future outcome into an earlier decision artifact.

---

# 8. TF-10 — Stable Opportunity and Setup-Episode Identity

## 8.1 Goal

One instrument must be able to hold several independent opportunities at the same time without overwriting or joining by symbol alone.

## 8.2 Reuse existing identity foundations

Do not create a competing instrument identity system. Reuse:

- `InstrumentIdentity`
- `stable_id()`
- existing PIT/event/bar identities

Add the missing identities additively.

## 8.3 Proposed contracts

### `SetupEpisodeIdentity`

Conceptually:

```text
SetupEpisodeIdentity
- setup_episode_id
- instrument_id
- setup_family
- timeframe
- episode_anchor_id
- episode_anchor_time
- session_or_window_id
- opened_at
- reset_policy_version
```

The episode is a market/setup episode, not a decision version.

A new evaluation of the same still-open episode must not generate a new episode merely because a browser refreshed.

A new episode begins only through the strategy/setup's explicit reset/re-arm policy.

### `OpportunityIdentity`

```text
OpportunityIdentity
- opportunity_id
- instrument_id
- strategy_id
- setup_episode_id
- market
- instrument_type
- horizon
- timeframe
- direction_hypothesis: LONG | SHORT | NON_DIRECTIONAL
```

Recommended identity law:

```text
opportunity_id = stable_id(
    instrument_id,
    strategy_id,
    setup_episode_id,
    timeframe,
    direction_hypothesis
)
```

**Do not include the strategy version in `opportunity_id`.** Strategy versions belong to immutable decision versions, allowing the same market opportunity to be re-evaluated by a newer strategy version without rewriting the opportunity identity.

### `DecisionVersionIdentity`

```text
DecisionVersionIdentity
- decision_version_id
- opportunity_id
- strategy_version
- strategy_definition_hash
- dependency_digest
- gate_policy_version
- evaluator_version
- decision_at
- data_cutoff
```

A new strategy version, dependency vintage, gate policy, cutoff or decision timestamp produces a new immutable decision version.

## 8.4 Compatibility migration

Do not rewrite old S8/R16 rows.

Use an additive migration path:

```text
legacy candidate_id / symbol history
        |
        | remains immutable
        v
new TF-10 opportunity identity for new brain outputs
```

If a legacy row can be mapped exactly, store an explicit compatibility link. If exact mapping cannot be proven, leave it historical/legacy; never invent an episode retrospectively from current data.

## 8.5 TF-10 tests

At minimum prove:

1. same INFY + same episode + same intraday continuation hypothesis -> same opportunity ID;
2. same INFY + same episode + continuation SHORT vs reversal LONG -> different opportunity IDs;
3. same INFY + 5m vs daily -> different opportunities;
4. same market episode + new strategy version -> same opportunity, new decision version;
5. new reset/re-arm episode -> new episode and opportunity;
6. retry/restart -> stable identity;
7. two concurrent workers derive the same deterministic ID;
8. symbol alias alone cannot merge different temporal instrument identities;
9. commodity contracts with different expiry cannot collide;
10. no existing historical row is rewritten.

### TF-10 STOP gate

Do not start TF-11 implementation if opportunity identity still collapses by symbol, profile, scan run, or date.

---

# 9. TF-11 — Neutral Discovery + Multi-Reason Admission

## 9.1 Scanner responsibility

A scanner answers only:

> **Why should this instrument enter the investigation pool?**

It may observe directional facts, but it does not own the final strategy direction.

## 9.2 Canonical discovery contracts

### `DiscoveryReason`

```text
DiscoveryReason
- reason_id
- instrument_id
- reason_type
- observed_fact_direction: UP | DOWN | MIXED | NONE
- detected_at
- event_time
- available_at
- data_cutoff
- valid_until
- magnitude / abnormality
- source_fact_ids
- feature_refs
- scanner_id + scanner_version if applicable
- admission_policy_version
```

### `DiscoveryCandidate`

```text
DiscoveryCandidate
- instrument
- candidate_id
- reasons[]
- discovery_priority
- priority_policy_version
- admitted_at
- valid_until
- data_cutoff
- provenance_digest
```

There is one instrument-level candidate with many reasons, not one candidate per reason.

## 9.3 Multi-reason OR admission

Valid reason producers may include:

```text
cash activity
absolute return abnormality
gap / pre-open imbalance
event / filing
ownership / institutional disclosure
OI abnormality
liquidity change
developing structure
sector/index dislocation
commodity-specific context
```

Admission rule:

```text
VALID(reason_1)
OR VALID(reason_2)
OR ...
=> instrument may enter DiscoveryPool
```

Admission does not mean qualification.

## 9.4 Repair current event-only exclusion

TF-11 must not use `for attention_row in r2.rows` as the sole discovery universe.

Instead:

```text
R2/cash reasons ---------+
S3/native reasons -------+
event reasons -----------+
ownership reasons -------+--> canonical reason merge --> DiscoveryPool
OI/activity reasons -----+
commodity reasons -------+
```

## 9.5 Neutral attention

Do not simply reuse signed return percentile as universal attention.

Candidate policies to replay/test include:

- absolute return abnormality + activity;
- tail-distance from median + activity;
- separate positive/negative queues with bounded budgets;
- reason-type budgets so event-only instruments cannot be starved by price movers.

The exact formula must be selected by whole-selector replay, not intuition.

The sign of the move remains metadata:

```text
-3.2% abnormal move
```

not a universal command:

```text
SHORT
```

## 9.6 Scanner definitions remain non-voting

Existing native scanner definitions are useful. Keep their non-confirming rule.

A scanner hit can become a `DiscoveryReason` or a reference to an already-computed feature; it must not automatically become an independent evidence family or final strategy vote.

Correlated scanner twins remain correlated.

## 9.7 TF-11 acceptance

Must prove:

- bearish mover is not penalized merely because return is negative;
- event-only instrument can enter discovery;
- multiple reasons merge under one instrument candidate;
- duplicate/correlated scanner reasons do not multiply evidence strength;
- discovery does not emit trade direction authority;
- discovery cannot emit `CONFIRMED` merely from a hit;
- missing optional reason source does not remove an otherwise valid candidate;
- missing mandatory source for one reason invalidates that reason, not unrelated valid reasons;
- candidate priority is stable/deterministic for the same snapshot;
- all reason provenance is reconstructable.

---

# 10. TF-12 — Versioned Feature Reuse and Safe Performance Foundation

## 10.1 Extend the existing `FeatureContract`; do not replace it

The existing feature registry already owns feature ID/version, horizon, required inputs, deterministic calculation, evidence family, correlation group, stale behavior, closed-bar requirement, storage/versioning, dependencies and tests.

TF-12 should add/standardize the runtime identity needed to reuse actual computed feature artifacts safely.

## 10.2 Semantic feature key

Every reusable feature artifact must be keyed by semantics, not by display label.

Conceptually:

```text
FeatureArtifactKey
- instrument_id / contract_id
- feature_id
- feature_version
- parameter_digest
- timeframe
- session_id / session_policy_version
- input_vintage_digest
- adjustment_policy_version / rollover_policy_version
- data_cutoff
- comparison_cohort_version       # cross-sectional features only
```

`VWAP`, `RVOL`, `ATR`, `RS`, `compression` etc. are not reusable merely because the names match.

Examples:

```text
5m session VWAP != daily VWAP
same-time cumulative intraday RVOL != completed-session daily RVOL
5m ATR != daily ATR
pre-adjustment structure != post-adjustment structure
NIFTY50 cohort percentile != NIFTY500 cohort percentile
```

## 10.3 Runtime feature artifact

```text
FeatureArtifact
- key
- value / typed payload
- source_bar_time / source_event_time
- calculated_at
- available_at
- valid_until
- quality_state
- source_fact_ids
- dependency_digest
- content_hash
```

Never return only the last finite numeric value without its source timestamp and validity state.

## 10.4 Cache layers

### L1 — decoded immutable source cache

Key:

```text
content_hash + parser/schema version + access scope
```

Purpose: avoid rereading/rehashing/decoding the same immutable object repeatedly in one assembly/worker.

### L2 — feature cache

Key: full semantic feature key + dependency digest.

### L3 — cross-sectional cache

Add exact universe/cohort version and cutoff.

### L4 — strategy-evaluation cache

Key:

```text
opportunity_id
+ strategy_version
+ dependency_digest
+ gate_policy_version
+ valid_until
```

### L5 — immutable published decisions

Published decisions are not a mutable cache. They are historical truth.

## 10.5 Performance changes to preserve correctness

Implement only with parity tests:

- sort-once percentile/rank computation instead of repeated O(N^2) rescans;
- bulk history reads, preserving the good S3 pattern;
- fetch each immutable canonical object once per assembly;
- route candidate first, then compute expensive strategy-only features;
- recalculate only affected cohort for cross-sectional changes;
- time-only expiry invalidation without rerunning unrelated indicators;
- content-addressable cache reuse across strategies where semantic keys match exactly.

## 10.6 Cache safety laws

Never cache away:

- freshness expiry;
- source permissions;
- event clearance expiry;
- session changes;
- market state;
- contract expiry/tender state;
- corporate-action revision;
- comparison-universe revision.

A cached value may remain historically valid while becoming invalid for a current decision.

---

# 11. TF-13 — Executable Strategy Definition, Registry and Router

This is the stage where a declared source profile becomes an actual executable **research evaluator**.

## 11.1 Critical distinction

Current `StrategySourceProfile` is a **source dependency contract** and explicitly has `executable=False`.

It must remain a sub-contract.

Do not mutate its meaning until it becomes a fake strategy registry.

Instead create a first-class strategy definition that references the source profile plus feature/gate/evaluator contracts.

## 11.2 Canonical `StrategyDefinition`

Each strategy must declare at least:

```text
StrategyDefinition
|
+-- strategy_id
+-- strategy_version
+-- definition_hash
+-- market
+-- instrument_type
+-- horizon
+-- timeframe
+-- direction_policy
|
+-- discovery_reasons_allowed
+-- discovery_reasons_required (usually empty unless truly required)
|
+-- evaluator_id / evaluator_version / callable binding
|
+-- source_profile_id
|
+-- required_features
+-- optional_features
+-- prohibited_features
|
+-- bar_close_policy
+-- session_policy
+-- freshness_policy
|
+-- relative_strength_contract
+-- event_policy
+-- liquidity_policy
+-- tradability_policy
+-- cost_policy
|
+-- trigger_contract
+-- invalidation_contract
+-- target_contract
+-- expiry_contract
|
+-- gate_policy_version
+-- comparable_group
+-- publication_policy
+-- outcome_definition
|
+-- activation_state
+-- acceptance_evidence_ref
```

## 11.3 Input classifications

Every input must be one of:

```text
REQUIRED_TO_CALCULATE
REQUIRED_TO_QUALIFY
OPTIONAL_CONTEXT
PROHIBITED_FOR_THIS_STRATEGY
```

Do not represent these only as prose.

## 11.4 Strategy registry linter

Before a strategy can be runnable even in research mode, CI/tests should prove:

- unique strategy ID/version;
- definition hash stable;
- evaluator binding exists;
- evaluator version matches declaration;
- all required feature IDs/versions exist;
- no feature is both required and prohibited;
- timeframe/horizon compatible with feature semantics;
- source profile exists;
- mandatory source groups are not silently optionalized;
- delayed context cannot satisfy an intraday trigger unless explicitly permitted for that exact condition;
- closed-bar requirement matches strategy;
- RS benchmark/lookback/direction interpretation is explicit;
- event scope and expiry are explicit;
- ranking group exists;
- publication policy exists;
- outcome definition exists;
- strategy cannot grant broker authority.

## 11.5 Strategy router

Router input:

```text
DiscoveryCandidate + StrategyRegistry + current market/instrument identity
```

Router output:

```text
0..N OpportunityIdentity records
```

Routing uses compatibility, not conviction:

```text
market compatible?
instrument type compatible?
horizon/timeframe supported?
allowed discovery reason present?
strategy activation ceiling allows research evaluation?
```

The router must not calculate the final strategy result itself.

## 11.6 Strategy evaluation contract

Conceptually:

```text
StrategyEvaluation
- opportunity_id
- strategy_id/version/hash
- evaluated_at
- data_cutoff
- public_state: WATCH | WAIT | CONFIRMED | REJECT
- entry_disposition
- direction_hypothesis
- feature_refs
- source_refs
- gate_results
- missing_proof
- trigger_plan
- invalidation_plan
- target_plan
- expiry
- tradability_result
- cost_result
- relative_strength_result
- event_result
- dependency_digest
- valid_until
- evaluator_version
```

### Important File-A compatibility rule for `NO_ENTRY`

File A currently owns exactly four public states:

```text
WATCH / WAIT / CONFIRMED / REJECT
```

Therefore `NO_ENTRY` must **not** silently become a fifth public state through this plan.

Represent it separately, for example:

```text
entry_disposition:
- NOT_EVALUATED
- NO_ENTRY
- TRIGGER_NOT_REACHED
- ENTRY_CONDITION_MET_RESEARCH_ONLY
- EXPIRED_WITHOUT_ENTRY
```

This preserves the user's required `NO_ENTRY` semantic without violating the four-state public contract. A future authority amendment may change this, but TF-13 must not assume one.

---

# 12. Example executable strategy definition — NSE equity intraday continuation

Conceptual example only; do not mark executable until TF-15 acceptance.

```text
strategy_id:
NSE_EQUITY_INTRADAY_CONTINUATION

strategy_version:
1.0.0

market:
NSE

instrument_type:
EQUITY

horizon:
INTRADAY

timeframe:
5m

direction_policy:
LONG_OR_SHORT_FROM_STRATEGY_STRUCTURE

required features / proof:
- verified CLOSED 5m candles
- session VWAP with exact session reset
- same-time intraday RVOL
- current liquidity / spread / trade-quality state
- sector state
- index regime
- strategy structure/acceptance

optional context:
- derivatives participation when applicable
- current material-event context

prohibited as entry trigger:
- future candles
- revised data that was unavailable at decision time
- monthly ownership data
- delayed CFTC/AMFI-style context
- discovery rank
- scanner hit count
- generic Combined_Score

outputs:
public state = WATCH | WAIT | CONFIRMED | REJECT
entry_disposition may additionally express NO_ENTRY
```

---

# 13. TF-14 — Equity Swing Strategy

Build the most mature PRF-003-style path first.

Required final contract:

```text
adjusted closed daily bars
+ R14-consistent corporate-action lineage
+ daily structure
+ daily participation / RVOL semantics
+ strategy-specific relative strength
+ event clearance
+ tradability
+ trigger
+ invalidation
+ target/expiry
+ cost eligibility
+ immutable decision proof
```

## Reuse

Wrap/refactor the current R5/S4/S5/S6/S7 logic into the strategy evaluator rather than cloning those formulas into a new engine.

## Remove old coupling

The strategy passes its own direction hypothesis to structure evaluation. Do not let R2 discovery direction choose the strategy profile.

## TF-14 acceptance examples

- bullish continuation and bearish continuation can be evaluated independently if strategy policy permits;
- event clearance UNKNOWN -> WAIT;
- corporate-action ambiguity -> WAIT;
- strategy-specific RS missing when mandatory -> WAIT;
- discovery priority cannot substitute for participation;
- exact trigger/invalidation/expiry stored;
- no read route builds/persists the strategy result;
- exact decision can be reconstructed from R-HIST roots.

---

# 14. TF-15 — Equity Intraday Continuation

Do not activate merely because a 5m source name exists.

Required:

```text
verified live/read-only intraday bar contract
closed 5m bars
session identity
session VWAP
same-time cumulative RVOL
current liquidity/spread/trade quality
index/sector context aligned to time
structure acceptance
freshness/latency policy
entry timing model
invalidation/target/expiry
cost eligibility
```

No forming candle may become a closed-bar confirmation.

Monthly ownership, delayed institutional portfolio data, daily flow summaries or future/revised bars cannot satisfy an intraday trigger.

Acceptance must include session-boundary reset, first-bars-of-session warmup, lunch/low-activity behavior, stale stream, missing bars, duplicate bars, out-of-order bars, late corrections and exact bar-close timing.

---

# 15. TF-16 — Reversal Strategies

A reversal is not `continuation_direction * -1`.

An intraday reversal needs its own contract such as:

```text
prior move/extreme context
failed acceptance / failed break
closed reclaim/reversal confirmation
reference-level distance
current participation
liquidity
sector/index relationship
strategy-specific RS/reclaim semantics
invalidation
cost viability
```

A large negative move plus high volume is only a discovery reason. It is not proof of LONG reversal.

Swing reversal, if implemented, is a separate strategy definition/version with separate outcome statistics.

---

# 16. TF-17 — Event / Ownership Strategy

Required identity chain:

```text
official event / actor observation
        |
        +-- event identity
        +-- instrument mapping
        +-- publication / availability timestamp
        +-- reporting period
        +-- actor identity where claimed
        +-- original quantity/holding facts
        +-- corporate-action comparability
        |
        v
post-event price acceptance
        |
        v
strategy evaluation
```

Rules:

- market-wide FII/DII data cannot prove that a named institution bought one stock;
- ownership data available monthly cannot be treated as intraday real-time evidence;
- corrected filing creates a new vintage, never rewrites what the strategy knew earlier;
- event-only instruments may enter discovery through TF-11;
- event presence is not automatic LONG/SHORT direction.

---

# 17. TF-18 — Commodity Strategies

Do not build one generic commodity strategy.

At minimum partition by:

```text
commodity group
intraday vs swing
actual contract
expiry / rollover / tender policy
local price/OI/liquidity
lot/tick/unit/currency
relevant delayed context
```

Examples:

- precious metals;
- energy;
- base metals;
- agriculture where supported.

Slow CFTC/EIA/WGC/warehouse/weather context may affect swing/context rules but cannot replace a current local intraday trigger.

No continuous generic symbol may overwrite contract identity needed for actual tradability/outcome research.

---

# 18. TF-19 — Net-Cost Eligibility and Comparable Ranking

## 18.1 Rank opportunities, not raw instruments

Incorrect:

```text
INFY rank = 4
```

Correct:

```text
INFY / 5m / bearish continuation / SHORT / episode E1
ranked inside its comparable group
```

## 18.2 Comparable group

Conceptually:

```text
ComparableGroup
- market
- instrument_type
- strategy_family
- horizon
- timeframe_class
- direction/risk class where required
- cost model version
- ranking policy version
```

Never rank a 5m NSE reversal directly against a seven-day GOLD swing using one universal score.

## 18.3 Eligibility before ranking

An opportunity enters ranking only when the ranking policy allows its current state and all mandatory rank prerequisites are valid.

A missing cost/spread estimate when mandatory is not `0 cost`; it is WAIT/INELIGIBLE according to strategy policy.

## 18.4 Avoid a new Combined_Score

Prefer a versioned ranking vector or transparent policy:

```text
eligibility
-> net reward relative to invalidation/cost
-> evidence quality
-> liquidity/capacity
-> freshness
-> tie-break identity
```

If a scalar is ever used internally, it must be strategy/comparable-group specific, versioned, fully reconstructable and explicitly **not win probability**.

The system may return fewer than requested N opportunities.

---

# 19. TF-20 — Dependency / Clock / Contract Driven Incremental Recalculation

The future brain should recompute only what changed.

Every feature/strategy declares dependency classes:

```text
INSTRUMENT_LOCAL
SECTOR_WIDE
INDEX_WIDE
UNIVERSE_WIDE
STRATEGY_WIDE
MARKET_WIDE
SOURCE_DRIVEN
TIME_DRIVEN
CONTRACT_DRIVEN
```

## Examples

### New 5m bar for INFY

```text
INFY local 5m features
 -> INFY intraday opportunities only
 -> affected comparable cohort if ranking inputs changed
```

### New NIFTY/sector bar

```text
index/sector features
 -> dependent RS/regime features
 -> strategies for affected instruments
```

### New company announcement

```text
instrument event facts
 -> event discovery reason
 -> event strategy
 -> any other strategy declaring event dependency
```

### Time passes beyond `valid_until`

```text
no new source file needed
 -> expiry event
 -> affected gate/decision becomes stale/WAIT according to policy
```

### Commodity contract enters tender window

```text
contract-driven eligibility invalidation
```

## Worker laws

- deterministic work key;
- bounded retries;
- idempotent recomputation;
- no duplicate semantic decision version;
- dependency digest changes when a real dependency changes;
- full recompute and incremental recompute must be equivalence-tested.

---

# 20. TF-21 — Immutable Strategy Decision Publication

TF-21 is the point where strategy evaluation becomes an immutable published research decision version.

## 20.1 Decision artifact

Conceptually:

```text
StrategyDecisionVersion
- decision_version_id
- opportunity_id
- setup_episode_id
- instrument identity
- strategy_id / strategy_version / definition_hash
- direction_hypothesis
- public_state
- entry_disposition
- discovery_reason_refs
- feature_artifact_refs
- gate results
- missing proof
- event/tradability/liquidity/cost results
- trigger / invalidation / target / expiry
- source/evidence root references
- dependency_digest
- data_cutoff
- decision_at
- published_at
- valid_until
- evaluator_version
- publication_policy_version
- decision_content_hash
```

## 20.2 Publication flow

```text
strategy evaluation complete
       |
       v
validate required proof
       |
       v
freeze complete decision payload
       |
       v
write immutable decision version + R-HIST retention intent
       |
       v
commit
       |
       v
atomically move current pointer for THAT opportunity only
       |
       v
transactional outbox notification
```

## 20.3 Current pointer

A current pointer must be keyed by opportunity, not merely symbol/profile.

```text
current(opportunity_id) -> decision_version_id
```

Updating the pointer never mutates or deletes the prior decision version.

## 20.4 Browser/API rule

Read routes read already-published decision versions.

They do not silently run strategies, write history or change decision time.

## 20.5 R-HIST rule

Any new immutable store/producer introduced by TF-10..TF-21 must be added to the R-HIST producer coverage registry and pass its drift/orphan checks before the stage can be accepted.

The future brain is not allowed to create an unregistered historical producer after 03E.

---

# 21. R-HIST / PIT / ML integration

Every published decision should later be reconstructable as:

```text
DecisionVersion
    |
    +--> exact StrategyDefinition version/hash
    +--> exact OpportunityIdentity / SetupEpisode
    +--> exact DiscoveryReason refs
    +--> exact FeatureArtifact refs
    +--> exact source observation roots
    +--> exact gate policy/results
    +--> exact cost/tradability assumptions
```

Outcome evaluation appends later facts:

```text
trigger reached?
entry became valid?
NO_ENTRY?
expired?
invalidation?
target?
MFE / MAE?
time to trigger/target/stop?
ambiguous same-bar path?
data gap?
```

Do not overwrite the original decision after outcome is known.

Future learning populations must include:

```text
CONFIRMED
WATCH
WAIT
REJECT
NO_ENTRY disposition
expired
ambiguous
censored
data-gap cases
```

This is required to avoid selection/survivorship bias.

---

# 22. Concurrency and fault-safety rules for the trading brain

The brain must inherit the R-HIST philosophy:

> Operational uncertainty may block publication; it may never create false certainty.

## Mandatory cases

### Mixed feature generations

Never evaluate:

```text
old 5m structure
+ new event clearance
+ different-universe RS
```

as one coherent decision unless the strategy's dependency snapshot explicitly permits those vintages.

### Duplicate trigger

Two workers receiving the same dependency event must converge on the same work identity and semantic result.

### Strategy definition changes mid-evaluation

The evaluation is either pinned to the original definition hash or marked stale/retried. Never publish a half-old/half-new definition.

### Feature becomes stale before publication

Revalidate mandatory freshness at publication boundary. If invalid, do not publish a false current CONFIRMED result.

### Current pointer race

Use optimistic version/compare-and-swap or equivalent transactional semantics so an older worker cannot move the pointer backwards over a newer valid decision.

### Crash after immutable decision commit but before pointer/outbox completion

Recovery must be deterministic and idempotent; the immutable decision remains reconstructable.

### Read during update

Reader sees:

```text
old complete published decision
OR
new complete published decision
```

not a mixed partial state.

---

# 23. Efficiency and speed design

Correctness wins first, then optimize exact semantics.

## 23.1 Route first, enrich second

Bad:

```text
500 stocks
 x every strategy
 x every expensive feature
 x every options/event/context query
```

Preferred:

```text
500 instruments
 -> cheap shared discovery
 -> K candidates
 -> strategy compatibility fan-out
 -> M opportunities
 -> compute only missing exact dependencies
```

## 23.2 Share computation only when semantics are identical

A feature used by swing and intraday can share code but not necessarily the same artifact.

## 23.3 Batch I/O

Preserve/extend:

- S3-style bulk history load;
- immutable object cache;
- one cohort load for percentile/RS calculations;
- one event/ownership batch mapped to affected instruments;
- one source read per content hash per assembly.

## 23.4 Sort once

Replace repeated percentile scans with sort/rank-once algorithms only after exact tie-behavior parity tests.

## 23.5 Compute-on-change, read-on-open

Move expensive strategy calculation toward source/dependency workers over time.

UI refresh should primarily be:

```text
read immutable current decision pointers
```

not:

```text
rebuild entire research brain
```

## 23.6 Performance telemetry

Measure before/after:

```text
source-commit -> discovery latency
discovery -> routed opportunity latency
feature cache hit rate
strategy evaluation count per dependency event
recomputed instruments / total universe
published decisions / evaluations
stale-before-publication count
mixed-version rejection count
per-strategy evaluation latency
cross-sectional cohort recompute latency
```

Do not claim speed improvement from a microbenchmark alone.

---

# 24. Proposed code ownership — subject to current-tree verification at implementation time

Do not blindly create every proposed file. Before each stage, search for an existing owner and extend it when responsibility already exists.

## Existing owners to preserve

```text
selection/contracts.py
    instrument/PIT/gate/evidence/candidate primitives

feature_registry.py
    feature semantic registry

selection/profile_source_contracts.py
    source dependency profiles only

scanners/registry.py
    scanner definitions; discovery-only/non-confirming

selection/s3_cheap_discovery.py
    useful bulk-read/discovery patterns

selection/s6_family_resolution.py
    evidence-family correlation control

selection/s7_state_gates.py
    existing PRF-003 public gate semantics to wrap/refactor

selection/store.py
    legacy immutable selection artifacts/history

historical retention / R16 / R18 owners
    historical proof and governance
```

## Likely additive owners

Names are proposals, not pre-approved paths:

```text
selection/discovery_contracts.py
selection/discovery_pool.py
selection/opportunity_identity.py
selection/strategy_contracts.py
selection/strategy_registry.py
selection/strategy_router.py
selection/strategy_evaluation.py
selection/strategies/
selection/feature_artifacts.py
selection/dependency_graph.py
selection/strategy_publication.py
```

If equivalent modules already exist when implementation starts, use them instead.

## Legacy scanner scheduler

`scanner_scheduler.py` currently combines many concerns. Do not make it the new strategy brain.

Use it only as an existing/legacy adapter where required while new canonical contracts are wired through tested owners.

---

# 25. Stage-by-stage coding sequence

## PRE-0 — finish the current memory foundation

```text
03E PASS
03F PASS
FULL R-HIST-03 ACCEPTED
```

No TF-10 implementation before this gate.

## TF-10A — identity contracts and RED tests

Add deterministic setup episode, opportunity and decision-version identity contracts.

No strategy behavior change yet.

## TF-10B — compatibility propagation

Carry identities through a fixture/shadow flow without changing public decisions.

Prove same-symbol independent opportunities do not collide.

## TF-11A — discovery reason contract

Adapters from current R2/S3/native/event/ownership producers into `DiscoveryReason`.

No new confirmation authority.

## TF-11B — canonical neutral pool

Merge/dedupe reasons; implement/test neutral attention policy; event-only admission.

## TF-12A — semantic feature artifact key

Extend registry/runtime contract; add timestamp + dependency digest.

## TF-12B — safe cache/performance parity

Bulk/cache/sort-once improvements with output parity tests.

## TF-13A — `StrategyDefinition` + registry linter

Definitions only; all remain non-executable until evaluator binding/acceptance.

## TF-13B — router

Discovery candidate -> 0..N independent opportunity identities.

## TF-13C — evaluation interface

Typed strategy evaluation, public-state compatibility, entry disposition, dependency digest.

## TF-14 — swing evaluator

Refactor/wrap mature PRF-003 path into the new strategy interface.

## TF-15 — intraday continuation

Only after verified intraday source contract exists.

## TF-16 — reversal

Independent evaluator; no sign inversion shortcut.

## TF-17 — event/ownership

Exact event/actor/vintage identity.

## TF-18 — commodity strategies

Contract/group-specific evaluators.

## TF-19 — cost eligibility + comparable ranking

No universal cross-strategy score.

## TF-20 — incremental dependency workers

Source/time/contract-driven invalidation and recomputation.

## TF-21 — immutable opportunity decision publication

Additive schema/store/current pointer/outbox + R-HIST registration.

---

# 26. Test matrix by architectural layer

## Discovery tests

- positive and negative abnormal movers receive symmetric eligibility under neutral policy;
- event-only admission;
- multiple reasons preserved;
- duplicate reason idempotency;
- stale reason expiry;
- correlated scanner reason does not become extra evidence vote;
- discovery rank cannot enter strategy evidence-strength field.

## Router tests

- one candidate routes to zero/one/many strategies;
- market mismatch excluded;
- instrument-type mismatch excluded;
- timeframe/horizon mismatch excluded;
- discovery reason allowlist only controls routing eligibility, not direction;
- same instrument can create simultaneous LONG and SHORT opportunities under different strategies.

## Feature tests

- semantic-key collision impossible across timeframe/session/parameters;
- dependency digest changes only on dependency changes;
- stale cached feature rejected;
- cohort version changes cross-sectional identity;
- same input snapshot -> deterministic output/hash;
- sort-once percentile parity including ties.

## Strategy tests

For each strategy:

- required missing -> WAIT;
- prohibited input cannot influence result;
- optional missing does not incorrectly block;
- forming candle cannot satisfy closed-bar rule;
- future evidence rejected;
- corrected later vintage cannot leak backward;
- wrong instrument/event mapping rejected;
- RS contract uses declared benchmark/lookback;
- event expiry enforced;
- tradability/liquidity/cost policy enforced;
- trigger/invalidation/target deterministic;
- exact evaluator/definition version retained.

## Publication tests

- immutable write;
- identical replay idempotent;
- same ID different payload rejected;
- old pointer cannot overwrite newer pointer;
- crash/retry safe;
- reads perform zero repair writes;
- prior decision remains accessible;
- expired old current decision is not displayed as current-ready;
- R-HIST retention intent and 03E producer registry coverage present.

## Whole-flow tests

```text
source vintage
 -> discovery reason
 -> candidate
 -> opportunities
 -> feature resolution
 -> strategy evaluation
 -> ranking
 -> immutable publication
 -> outcome
```

Replay the entire chain with PIT cutoffs, not only the final selected stocks.

---

# 27. Stage acceptance law

No TF stage is complete merely because a unit test passed.

Every stage requires:

1. exact current revision recorded;
2. current-state problem/requirement reproduced;
3. contract change documented;
4. RED/adversarial tests where applicable;
5. implementation;
6. focused tests;
7. relevant upstream/downstream integration tests;
8. full backend regression;
9. compile;
10. Ruff;
11. frontend when contract reaches it;
12. accepted Mypy policy reported honestly;
13. exact final PR-head CI observed;
14. R-HIST registry updated for every new governed producer;
15. remaining risk documented;
16. no source/model/PIT/strategy/execution authority accidentally expanded.

---

# 28. STOP conditions

Stop stage advancement if any of these is true:

```text
scanner output directly becomes universal LONG/SHORT

opportunity still joins/persists by symbol alone

strategy/profile declaration has no real evaluator binding

profile registration is treated as data freshness/activation proof

future/revised data can enter an earlier decision

required UNKNOWN is converted to PASS

forming bar can satisfy closed-bar confirmation

monthly/delayed context can replace intraday trigger

feature reuse ignores timeframe/session/vintage/cohort semantics

cache can bypass freshness or permission checks

discovery priority becomes evidence strength

scanner match count becomes win probability

rank compares incompatible strategy groups

missing cost is treated as zero when cost is mandatory

read/UI route performs hidden strategy persistence

new immutable producer is absent from R-HIST registry

old decision history must be rewritten to make new design work

incremental recompute differs from full recompute without explained versioned policy

exact-head CI is not proven

broker/order authority expands
```

---

# 29. Before / after architecture comparison

## Current mixed behavior

```text
cash/EOD spine
 -> R2 attention with signed-return influence
 -> S3 only decorates existing R2 rows
 -> R5 structure direction follows upstream evidence direction
 -> S7 mainly owns PRF-003 decision semantics
 -> S8 stores one scan blob
 -> selection persistence remains scan/profile/symbol oriented
```

Useful, but not sufficient for a general multi-strategy brain.

## Target

```text
validated observations
 -> neutral multi-reason discovery
 -> instrument candidate
 -> stable setup episode
 -> strategy router
 -> independent opportunities
 -> exact shared-feature reuse
 -> independent strategy evaluators
 -> cost/tradability gates
 -> comparable opportunity ranking
 -> immutable per-opportunity decision version
 -> PIT outcome/failure memory
```

---

# 30. Efficiency example

Suppose 500 NSE equities are available.

Bad future implementation:

```text
500
 x 6 strategies
 x every expensive feature/source
 = thousands of unnecessary evaluations and duplicated reads
```

Preferred hybrid:

```text
500 instruments
 -> cheap batch discovery
 -> 35 candidates
 -> compatibility router
 -> 70 opportunity hypotheses
 -> feature cache reuses exact shared calculations
 -> expensive enrichment only for opportunities that require it
 -> maybe 20 fully qualified/rankable opportunities
 -> immutable publication only when dependency result changed
```

Numbers above are explanatory, not performance promises. Actual candidate/evaluation counts must be measured on replay and live-safe shadow runs.

---

# 31. Trading usefulness of this separation

The design improves research quality because TrendForge can distinguish:

```text
"INFY moved down unusually"
```

from:

```text
"INFY continuation SHORT is qualified"
```

and from:

```text
"INFY reversal LONG is qualified"
```

and from:

```text
"both are unqualified because mandatory proof is missing"
```

That allows historical analysis to ask strategy-specific questions:

```text
When a -3% high-volume move occurred:
- how often did continuation trigger?
- how often did failed-break reversal trigger?
- how often did neither trigger?
- what was MFE/MAE after each exact trigger?
- which regime/sector/liquidity conditions changed the result?
```

This is substantially more useful than training on a generic symbol-level bullish/bearish score.

---

# 32. Future learning / analog engine compatibility

The identity and memory model is deliberately compatible with later analog research:

```text
OpportunityIdentity
 + exact FeatureArtifact vector
 + exact market/sector/event context
 + exact StrategyDefinition
 + exact DecisionVersion
 + exact Outcome
```

can later support:

```text
similar historical episodes
regime-conditioned failure memory
strategy calibration
MFE/MAE distributions
time-to-trigger / time-to-target
cost/slippage behavior
feature drift
strategy-version comparison
```

But similarity/ML must remain downstream of the deterministic PIT contracts. It must never replace missing source/gate proof.

---

# 33. Requirement traceability

| User / roadmap requirement | Current evidence | Plan owner |
|---|---|---|
| Scanner and Strategy are different | System brain states discovery != direction; native scanners non-confirming | TF-11 / TF-13 |
| One instrument -> multiple opportunities | Roadmap target exists; first-class runtime ID missing | TF-10 |
| Stable episode/opportunity identity | `InstrumentIdentity` exists; opportunity/episode symbols absent | TF-10 |
| Neutral multi-reason admission | Current S3 iterates R2 only; event-only gap known | TF-11 |
| Versioned feature reuse | `FeatureContract` exists; runtime semantic artifact key incomplete | TF-12 |
| Executable strategy definition | Source profiles exist with `executable=False`; no `StrategyDefinition` runtime | TF-13 |
| Equity swing | PRF-003/S7 is most mature existing path | TF-14 |
| Intraday continuation | profile declared; verified live bar acceptance remains separate | TF-15 |
| Reversal independent of continuation | current R5 direction coupling must be removed | TF-16 |
| Event/ownership | source contracts exist; canonical admission/evaluator incomplete | TF-17 |
| Commodities | source profiles/readiness exist; complete strategy paths not proven | TF-18 |
| Net cost + comparable ranking | current ranking is symbol/attention oriented | TF-19 |
| Efficient incremental recompute | snapshot is consistent but compute-heavy; dependency classes already designed | TF-20 |
| Immutable strategy publication | S8/selection history exists but not per-opportunity final model | TF-21 |
| Historical memory before brain | R-HIST-03E/03F still open | hard prerequisite |

---

# 34. Definition of complete trading-brain foundation through TF-21

Do not declare the TF-10..TF-21 foundation complete until TrendForge can truthfully prove all of the following:

```text
[ ] R-HIST-03E accepted
[ ] R-HIST-03F accepted
[ ] full R-HIST-03 foundation accepted

[ ] scanner/discovery contract is direction-neutral by authority
[ ] event-only/multi-reason admission works
[ ] discovery reason provenance is immutable/reconstructable

[ ] stable setup episode identity exists
[ ] stable opportunity identity exists
[ ] same symbol can hold independent strategy/timeframe/direction opportunities
[ ] immutable decision-version identity exists

[ ] feature artifacts have exact semantic/version/dependency identity
[ ] feature reuse cannot mix incompatible timeframe/session/vintage/cohort semantics
[ ] cache/freshness/permission rules are adversarially tested

[ ] every runnable strategy has a real evaluator binding
[ ] required/optional/prohibited inputs are typed
[ ] bar/session/freshness/RS/event/liquidity/tradability/cost policies are explicit
[ ] trigger/invalidation/target/expiry contracts are explicit
[ ] strategy/profile declaration alone cannot claim runtime readiness

[ ] swing evaluator accepted
[ ] intraday continuation accepted only with verified intraday inputs
[ ] reversal evaluator independent
[ ] event/ownership evaluator independent
[ ] commodity evaluators contract-aware

[ ] comparable ranking partitions are explicit
[ ] net cost eligibility is enforced
[ ] no universal Combined_Score / fake win probability is introduced

[ ] dependency graph recomputes only affected outputs
[ ] incremental/full recompute equivalence proven
[ ] time/contract events can invalidate without a new source file

[ ] immutable per-opportunity publication exists
[ ] current pointer moves atomically
[ ] history never overwritten
[ ] reads do not repair/write
[ ] every new immutable producer is covered by R-HIST registry
[ ] exact outcomes can attach without rewriting original decisions

[ ] focused + full regression pass at exact final head
[ ] runtime/readiness documentation updated honestly
[ ] no broker/execution authority added
```

---

# 35. Exact next action from this document

This document does **not** authorize TF-10 coding today.

The correct next execution remains:

```text
1. Finish R-HIST-03E using its existing build plan.
2. Meet every 03E acceptance gate including exact-head CI.
3. Execute R-HIST-03F fault/concurrency/golden acceptance.
4. Close the full R-HIST-03 foundation gate.
5. Re-audit the then-current branch/head against this file.
6. Start TF-10 with RED identity tests only.
7. Advance one stage at a time through the gates above.
```

The first trading-brain coding commit after R-HIST acceptance should therefore be narrow:

> **TF-10: introduce deterministic setup-episode, opportunity and decision-version identity contracts plus adversarial collision/idempotency tests, without changing strategy outputs or activation.**

That creates the stable spine required for every scanner, strategy, feature, ranking, publication, outcome and future learning system that follows.
