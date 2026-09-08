# TrendForge Audit Findings and Engineering Execution Roadmap

**Date:** 2026-09-08  
**Purpose:** Durable project-brain reference for future audits, patches, upgrades, rewiring, and architecture evolution.  
**Status:** Reference / engineering roadmap. This file does **not** override File A, `AGENTS.md`, accepted Decisions, runtime evidence, or safety gates.

---

## 1. Why this file exists

TrendForge has grown into a multi-stage trading research and decision system with data acquisition, normalization, selection, structure analysis, evidence fusion, replay, governance, UI projections, source-health controls, and multiple experimental/research overlays.

Future upgrades are dangerous if an engineer or AI agent changes one module without understanding:

- what comes before it;
- what comes after it;
- what owns truth;
- what is only context;
- what may vote;
- what may veto;
- what may change public state;
- what is historical/replay only;
- what is experimental;
- what must fail closed;
- which calculations are allowed to use only information available at decision time.

This document records the recovered architecture audit, unresolved design findings, engineering execution order, and the intended separation of responsibilities so that later work can evolve the project without creating a second brain or breaking the existing one.

---

## 2. Authority and interpretation rule

Use this document as an **architecture/audit companion**, not as a replacement build law.

When this file conflicts with current repository authority, use the repository authority order documented in `fileindex.md`:

1. Current user instruction + `AGENTS.md`.
2. File A: `docs/fable/new_merge_PLAN_2026-07-18.md`.
3. Final Merge addendum: `docs/fable/FINAL_MERGE_PLAN.md`.
4. `docs/DECISIONS.md`.
5. Hybrid File B only where File A permits it.
6. Detail plans.
7. Runtime evidence + `docs/BUILD_STATUS.md` + `docs/VALIDATION.md`.

The current executable architecture reference is `docs/ARCHITECTURE.md`; the larger system-boundary reference is `TREND_FORGE_ARCHITECTURE.md`.

### Public-state terminology correction

An earlier audit discussion used the conceptual sequence:

`WAIT -> WATCH -> PAPER-CANDIDATE`

That wording is preserved here only as historical design context. The current repository naming lock defines public states as:

`WATCH / WAIT / CONFIRMED / REJECT`

Do not add `PAPER-CANDIDATE` as a fifth public state unless the governing design is explicitly amended.

---

## 3. Current repository foundation that this audit must respect

At the time of this reference, the executable research spine documented by the repository is broadly:

`R1 -> R2 -> WAIT-only R3 -> R4/R14/R5 -> R6 -> S2-S8 -> R16`

Important existing properties:

- R14 is the corporate-action / identity-continuity authority join required by R5.
- R5 is closed-bar structure analysis and is not itself a buy engine.
- S2-S8 add market weather, discovery, enrichment, family resolution, state handling, and reconstructable persistence.
- R16 owns immutable PIT hypotheses, replay, path labels, metrics, and validation projections.
- R18 is model governance downstream of R16 and must remain approval gated.
- Source registration or successful HTTP transport is not evidence by itself.
- Missing mandatory evidence must remain typed UNKNOWN/WAIT rather than being invented or silently replaced.
- Tradability/restriction logic is a fail-closed veto/readiness layer; PASS is non-voting.
- Existing source, lineage, freshness, state, replay, and governance ceilings must not be bypassed by a new intelligence layer.

This audit therefore recommends **improving the existing architecture**, not replacing TrendForge with independent systems for every data source or feature family.

---

## 4. Recovered architecture audit assessment

The previous architecture review judged TrendForge to be substantially built but still vulnerable to errors caused by ordering, authority mixing, temporal leakage, incompatible score semantics, and over-coupled decision synthesis.

The earlier review roughly characterized the architecture as moving from an approximately low-80s design quality into the mid-90s if the proposed corrections were implemented. These numbers were qualitative engineering scores, not production validation metrics and not trading-performance claims.

The strongest conclusion remains:

> TrendForge does not mainly need more indicators. It needs stricter wiring, time correctness, authority separation, consistent contracts, calibrated evidence handling, and explicit decision ownership.

---

## 5. Core end-to-end mental model

Use this as the conceptual intelligence flow when auditing or extending the system:

```text
RAW / OFFICIAL / DERIVED DATA
        |
        v
SOURCE + DATA QUALITY
        |
        v
IDENTITY / LINEAGE / FRESHNESS / PIT SAFETY
        |
        v
FEATURES
        |
        v
MARKET STATE / CONTEXT
        |
        v
REGIME
        |
        v
HISTORICAL ANALOGS / MEMORY
        |
        v
DIRECTION ESTIMATION
        |
        +-------------------+
        |                   |
        v                   v
FAILURE / FAKEOUT      RISK / TRADABILITY
ANALYSIS               / EXECUTION FEASIBILITY
        |                   |
        +---------+---------+
                  v
          OPPORTUNITY QUALITY
                  |
                  v
          DECISION SYNTHESIS
                  |
                  v
       WATCH / WAIT / CONFIRMED / REJECT
                  |
                  v
      NON-EXECUTABLE PLAN / APPROVED OMS PATH
                  |
                  v
               OUTCOME
                  |
                  v
LABELS / FAILURE MEMORY / CALIBRATION / DRIFT / GOVERNANCE
```

This is a conceptual map. Exact stage identifiers and build sequence remain owned by File A and current Decisions.

---

## 6. Major architectural findings

### 6.1 Direction must be separated from risk and execution authority

A bullish or bearish estimate must not automatically become a trade decision.

Example:

```text
Direction estimate: bullish 82%
Historical continuation analogs: supportive

But:
- fakeout risk = high
- liquidity/tradability = weak
- price is stretched from reference value
- stop distance is unacceptable
- regime confidence is weak
- mandatory evidence incomplete

Result:
WATCH / WAIT, not BUY
```

Required separation:

- **Direction engine:** What direction has evidence?
- **Opportunity engine:** Is there a usable setup/location now?
- **Risk engine:** Is the loss profile acceptable?
- **Tradability/veto engine:** Is the instrument legally/operationally tradable under the current profile?
- **Decision synthesizer:** What state is justified by all of the above?
- **Execution/OMS layer:** May an approved action be previewed or sent?

No single directional score should own all of these questions.

### 6.2 Do not combine unlike scores as if they are interchangeable probabilities

TrendForge contains evidence strength, structure matches, rankings, family support, probabilities, proxies, veto states, completeness, and quality signals.

These are different mathematical objects.

Do not add or average them into one authority score unless:

- scale is defined;
- calibration is proven;
- independence/correlation is handled;
- missingness policy is explicit;
- horizon is identical;
- time-of-availability is compatible;
- training/replay provenance matches;
- output semantics are documented.

Evidence strength must not be displayed or consumed as win probability.

### 6.3 Feature manifest/versioning is foundational

Every model, similarity index, replay record, persisted decision, and calibration result should be traceable to an immutable feature definition.

Minimum identity should include, where relevant:

- feature names and order;
- formula version;
- parameters;
- normalization version;
- timeframe;
- lookback;
- adjustment policy;
- source lineage;
- missingness/mask semantics;
- feature-set hash.

Without this, an old index or model can silently score a new feature layout.

### 6.4 Missing-feature masks must be first-class data

A missing feature is not necessarily zero.

The system should distinguish:

- real zero;
- not applicable;
- not available yet;
- stale;
- parser failure;
- source unavailable;
- excluded by horizon/profile;
- lineage mismatch.

Similarity, models, rankings, and persisted explanations must carry or reconstruct the mask.

### 6.5 Similarity requires masked and compatibility-aware comparison

A historical-analog engine should not compare vectors as if every dimension is valid when either side has missing fields.

A robust implementation should:

1. form the intersection of valid comparable features;
2. enforce a minimum comparable-feature coverage;
3. calculate similarity only on that valid intersection;
4. penalize low overlap/quality;
5. enforce feature-version compatibility;
6. enforce horizon/timeframe compatibility;
7. expose coverage with the similarity score.

A high cosine similarity based on a tiny surviving subset must not look equivalent to a high similarity using the full feature space.

### 6.6 Historical sample quality must affect confidence

An observed 80% outcome rate from 5 analogs is not equivalent to 80% from 500 comparable analogs.

The historical-memory layer should expose at minimum:

- sample count;
- effective sample size after weighting;
- recency distribution;
- regime compatibility;
- feature-overlap quality;
- outcome definition/version;
- uncertainty interval or shrinkage estimate.

Use Bayesian/shrinkage or another explicit small-sample treatment rather than trusting raw percentages.

### 6.7 ATR percentile and similar context features must be prior-only

Any percentile, normalization range, z-score baseline, min/max, calibration bin, or regime threshold used at decision time must be calculated using only data available at that decision time.

For replay at candle `t`, the system must not use statistics computed using candles after `t`.

This applies to:

- ATR percentile;
- volume percentile;
- volatility regime;
- liquidity distribution;
- feature scaling;
- rolling thresholds;
- calibration maps;
- historical-neighbor population where temporal restrictions apply.

### 6.8 Regime needs exact identity plus broader grouping

Exact `regime_id` can become too sparse. A broader `regime_group` allows controlled fallback.

Example hierarchy:

```text
regime_group = TRENDING_BULLISH
regime_id    = TRENDING_BULLISH_HIGH_VOL_STRONG_BREADTH
```

Search/fallback policy can then be explicit:

1. exact regime;
2. compatible regime group;
3. broader population only if policy permits;
4. confidence penalty for each fallback.

Do not silently mix incompatible regimes just to increase sample count.

### 6.9 Replay/backtest freshness must be decision-time freshness

Live freshness and replay freshness are not the same operation.

In replay, a source should be evaluated as it would have appeared at historical decision time, using archived/PIT timestamps and availability rules.

The replay engine must not compare historical records against today's freshness clock or today's last-good object.

Recommended explicit mode:

- `LIVE_FRESHNESS`
- `REPLAY_PIT_FRESHNESS`

Every persisted replay decision should identify which mode was used.

### 6.10 Same-candle TP/SL ambiguity must be explicit

With OHLC bars, both stop and target can be touched within one candle and bar data may not reveal which occurred first.

Backtests must define a deterministic ambiguity policy, for example:

- conservative stop-first;
- optimistic target-first only for sensitivity comparison;
- lower-timeframe resolution if genuinely available PIT;
- mark `AMBIGUOUS_INTRABAR` and exclude/stratify.

Never silently pick the profitable path.

### 6.11 Calibration must be separated from raw model/evidence output

Raw direction scores, similarity percentages, logits, heuristic confidence, and evidence strengths should not be displayed as probabilities unless calibrated and validated.

Calibration must be versioned by:

- model/engine version;
- horizon;
- target/outcome definition;
- regime policy if used;
- training window;
- holdout period;
- calibration method;
- dataset/PIT hash.

Until approved, label outputs honestly as uncalibrated confidence/evidence.

### 6.12 Drift is a governance state, not merely another feature

Keep separate concepts for:

- feature/data distribution drift;
- calibration drift;
- outcome/performance drift;
- source/schema drift;
- regime distribution change.

Drift can reduce trust, trigger WAIT, demote a model, or request review. It must not silently retrain or promote a model in production.

### 6.13 Model and index metadata must prevent silent incompatibility

FAISS or any other retrieval index should carry immutable metadata such as:

- index version/hash;
- feature manifest hash;
- normalization hash;
- mask policy;
- training/PIT cutoff;
- symbols/universe;
- timeframe/horizon;
- regime policy;
- outcome label version;
- build timestamp;
- code/formula revision.

Loading an incompatible index should fail closed or rebuild through an approved path.

---

## 7. Existing stock/indicator application performance finding

A previous performance audit observed approximately:

- 4,680 five-minute bars for the test case;
- about 17.2 MB full response;
- about 85.8 seconds total request time;
- about 76.4 seconds inside `compute_all()`;
- roughly 122 indicator keys;
- indicator toggles causing excessive refetch/recompute.

These figures are historical benchmark observations from the earlier audit and should be re-measured before being treated as current performance evidence.

The preferred migration pattern was additive rather than destructive:

```text
legacy full endpoint
        |
        +--> /base
        +--> /indicator/{key}
        +--> POST /indicators/batch
        +--> /quote
```

with:

```text
Indicator Registry
      |
      v
compute_selected()
      |
      v
Backend cache
      |
      v
API
      |
      v
Frontend cache
      |
      v
Incremental chart update
```

Required protections include:

- cache keys containing parameter/version/freshness identity;
- in-flight request deduplication;
- unknown-indicator handling;
- batch fetching;
- marker merging;
- correct chart-pane routing;
- replay-safe arrays;
- batched redraws;
- feature flags;
- cache invalidation;
- old-vs-new reconstruction tests.

Do not remove the legacy path until parity is demonstrated.

---

## 8. Engineering execution roadmap

The audit recommends the following order. This is a dependency-aware engineering roadmap, not a replacement for File A stage authority.

### Stage 1 - Establish a trusted baseline

Before modifying intelligence logic:

- pin branch/commit;
- run current tests;
- record known failures;
- capture runtime source/state evidence;
- record current schema/migrations;
- identify active feature flags;
- identify current model/index hashes;
- save representative decision/replay fixtures.

Exit condition: later changes can be compared against a known baseline.

### Stage 2 - Map the actual runtime dataflow

For every engine/module, record:

- inputs;
- outputs;
- owner;
- caller;
- consumer;
- timing;
- freshness authority;
- whether it can vote;
- whether it can veto;
- whether it can alter state;
- whether it can affect execution;
- persistence path;
- replay path.

Exit condition: no important producer/consumer connection is implicit.

### Stage 3 - Fix data and feature correctness

Priorities:

- feature manifest/version;
- source/feature lineage;
- missing masks;
- deterministic normalization;
- typed UNKNOWN handling;
- corporate-action consistency;
- schema compatibility.

Exit condition: feature vectors are reconstructable and comparable.

### Stage 4 - Fix temporal and replay correctness

Audit for future leakage in:

- rolling statistics;
- resampling;
- higher-timeframe bars;
- percentile ranks;
- normalization;
- labels;
- source availability timestamps;
- historical retrieval;
- corporate actions;
- calibration.

Exit condition: replay at time `t` cannot observe information that became available after `t`.

### Stage 5 - Strengthen market-state and regime contracts

Implement/version:

- exact regime identity;
- regime grouping;
- compatibility/fallback matrix;
- regime confidence;
- unknown regime behavior.

Exit condition: memory/model layers know exactly which regimes they are allowed to compare.

### Stage 6 - Repair historical-memory / similarity intelligence

Implement:

- masked similarity;
- minimum overlap threshold;
- coverage penalty;
- feature-version checks;
- sample-size quality;
- regime fallback hierarchy;
- freshness/recency weighting;
- immutable index metadata.

Exit condition: every analog answer can explain why each neighbor was eligible.

### Stage 7 - Probability and calibration layer

Separate:

- raw direction evidence;
- heuristic confidence;
- historical rate;
- calibrated probability.

Add:

- calibration datasets;
- PIT/OOS boundaries;
- reliability diagnostics;
- uncertainty/sample-count reporting;
- approval state.

Exit condition: only validated calibrated outputs are called probabilities.

### Stage 8 - Separate decision authorities

Create/strengthen explicit contracts between:

- direction;
- opportunity/setup quality;
- fakeout/failure risk;
- tradability;
- risk;
- evidence completeness;
- decision synthesis;
- execution/OMS.

Exit condition: directional agreement alone cannot bypass a veto or create execution authority.

### Stage 9 - Fix final decision synthesis

The final synthesizer should consume typed upstream results, not recalculate their internal logic.

It should support:

- hard veto precedence;
- WAIT for missing mandatory evidence;
- conflict handling;
- confidence penalties;
- traceable reasons;
- horizon-specific policy;
- no double counting of correlated evidence families.

Exit condition: every public state can be reconstructed from upstream facts and policy versions.

### Stage 10 - Optimize indicator/API architecture

Only after correctness is protected:

- selective computation;
- batch endpoints;
- backend caching;
- frontend caching;
- incremental rendering;
- request dedupe;
- cache invalidation/version keys;
- parity testing against legacy full computation.

Exit condition: performance improves without output drift.

### Stage 11 - Failure memory, drift, and index lifecycle

Define separately:

- failure-event schema;
- fakeout taxonomy;
- outcome labels;
- recency decay;
- index rebuild conditions;
- drift thresholds;
- demotion/review behavior;
- retention policy.

Exit condition: learning-related state is governed, versioned, replayable, and cannot auto-promote production behavior.

### Stage 12 - Backtest, replay, and shadow validation

Minimum validation matrix:

- deterministic replay;
- no-lookahead tests;
- same-candle ambiguity tests;
- old/new parity fixtures;
- regime-stratified results;
- sample-size reporting;
- transaction-cost sensitivity;
- slippage sensitivity;
- missing-data behavior;
- stale-source behavior;
- corporate-action cases;
- index/model incompatibility failure;
- shadow/live-read-only comparison.

Exit condition: improvements survive realistic and adversarial validation, not only happy-path examples.

### Stage 13 - Production gates

Require explicit evidence for:

- data readiness;
- lineage integrity;
- PIT approval;
- model/calibration approval where applicable;
- drift state;
- tradability;
- risk policy;
- execution arming and broker safeguards if that path is ever enabled.

Exit condition: unsafe or incomplete state fails closed.

---

## 9. Upgrade rules for future AI/coding agents

Before changing TrendForge, an AI agent should answer all of these:

1. Which governing requirement authorizes this change?
2. Which current module owns this responsibility?
3. Is the proposed code extending that owner or accidentally creating a second owner?
4. Which upstream data does it consume?
5. Are those inputs PIT-safe and lineage-bound?
6. What does it output?
7. Who consumes that output?
8. Can it vote, veto, rank, change public state, size, or execute?
9. What happens when data is missing/stale/malformed?
10. Does the change alter replay semantics?
11. Does it alter historical labels?
12. Does it alter feature/model/index compatibility?
13. What tests prove no future leakage?
14. What tests prove no authority bypass?
15. What old behavior must remain byte/semantic compatible?
16. What is the rollback path?

If these cannot be answered, the code change is not ready.

---

## 10. Anti-patterns to prevent

Do not:

- create a second independent source downloader when an existing canonical acquisition/store path owns the source;
- treat HTTP 200 or source registration as evidence;
- convert missing data to zero without explicit semantics;
- combine evidence scores, rankings, probabilities, and vetoes into one unexplained score;
- allow an indicator or direction model to directly place/authorize a trade;
- use future candles in higher-timeframe or rolling calculations;
- use today's last-good source in a historical replay unless PIT rules prove it was available then;
- silently load an index/model built from incompatible features;
- use a tiny historical sample as high-confidence probability;
- hide same-bar target/stop ambiguity;
- allow automatic online retraining/promotion to bypass R16/R18-style governance;
- rebuild stable working architecture simply because a new engine is added;
- let UI presentation become a second calculation authority;
- double count correlated scanners/features as independent confirmations.

---

## 11. Recommended implementation contract for new intelligence modules

Every new engine should declare a small machine-readable or documented contract containing:

```text
engine_id
version
purpose
horizon
timeframe
inputs
input_schema_versions
feature_manifest_hash
source_lineage_requirements
freshness_policy
missingness_policy
regime_policy
output_schema
output_semantics
can_vote
can_veto
can_rank
can_change_public_state
can_size
can_execute
replay_mode
persistence_owner
calibration_status
governance_status
```

This makes the architecture auditable as the project grows.

---

## 12. Decision-quality hierarchy

A future intelligent TrendForge should reason in this order:

```text
1. Is the data trustworthy and available at this decision time?
2. Is identity/lineage correct?
3. Is the instrument eligible/tradable for this profile?
4. What is the current market/regime context?
5. What direction is supported?
6. How similar are valid historical cases?
7. How strong is that historical sample?
8. What failure/fakeout patterns are present?
9. Is the current location/setup usable?
10. Is risk acceptable?
11. Is mandatory evidence complete?
12. Are evidence families independent enough to count separately?
13. What public state is justified?
14. If an execution path exists, is it separately authorized and armed?
15. How will the outcome be recorded for later replay/calibration/drift analysis?
```

This ordering is intentionally different from "calculate many indicators and average them".

---

## 13. Relationship to the existing project-brain files

Use this file together with:

- `fileindex.md` - navigation and authority pointers.
- `AGENTS.md` - engineering/safety behavior.
- `docs/fable/new_merge_PLAN_2026-07-18.md` - governing File A build sequence and state/fusion law.
- `docs/fable/FINAL_MERGE_PLAN.md` - product/design addendum.
- `docs/DECISIONS.md` - accepted lasting decisions.
- `docs/ARCHITECTURE.md` - current executable module map.
- `TREND_FORGE_ARCHITECTURE.md` - larger system-boundary architecture reference.
- `TREND_FORGE_SOURCE_REGISTRY.md` - source meaning and authority.
- `docs/BUILD_STATUS.md` - implementation status evidence/history.
- `docs/VALIDATION.md` - observed validation evidence and limitations.
- `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` - discovery detail.
- `docs/OPTIONS_INTELLIGENCE_PLAN.md` - options detail and mathematical context.
- `docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md` - research mathematics reference, not build authority.

This audit file exists to explain **how to think about the wiring across those files** when patching or evolving the project.

---

## 14. Future update rule for this file

When a finding in this document is implemented:

- do not erase the finding;
- mark it implemented with date, commit, module, tests, and governing Decision/File A reference;
- add measured before/after evidence;
- record any changed assumptions;
- update `fileindex.md` if the implementation creates a new canonical file/module;
- update `docs/BUILD_STATUS.md` and `docs/VALIDATION.md` through their existing append-only conventions where applicable;
- create/update `docs/DECISIONS.md` only when a lasting architectural decision is formally adopted.

This preserves the reasoning history instead of repeatedly rediscovering the same architecture problems.

---

## 15. Current unresolved audit checklist

The following items should remain visible until repository evidence proves they are solved in the relevant path:

- [ ] Feature manifest/version compatibility is enforced end to end where model/similarity inputs are used.
- [ ] Missing-feature masks are first-class and not silently zero-filled.
- [ ] Similarity is masked, coverage-aware, and compatibility gated.
- [ ] Historical analog confidence accounts for sample size/effective sample quality.
- [ ] ATR percentile and comparable rolling context calculations are prior-only in replay.
- [ ] Exact `regime_id` plus broader `regime_group` fallback is defined where analog/model logic needs it.
- [ ] Replay freshness is explicitly PIT/decision-time aware.
- [ ] Same-candle TP/SL ambiguity has a deterministic documented policy.
- [ ] Raw scores are clearly separated from calibrated probabilities.
- [ ] Model/index metadata prevents incompatible loading.
- [ ] Direction, opportunity, risk, veto, state, and execution authorities remain separated.
- [ ] Indicator/API optimization is implemented only with parity/reconstruction tests.
- [ ] Drift/failure-memory/index-refresh lifecycle is governed and replayable.

A checkbox must not be marked complete from design intent alone. It requires code + tests + observed evidence.
