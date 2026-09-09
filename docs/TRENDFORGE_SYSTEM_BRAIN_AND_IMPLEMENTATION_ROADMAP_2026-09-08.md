# TrendForge System Brain and Implementation Roadmap

**Status:** living architecture and implementation reference  
**Created:** 2026-09-08  
**Repository:** `onlyvictus-bit/trendforge`  
**Primary reviewed application revision:** `14301ff1abbc475423e7a06cd2bd0e96f35b4481` on the atomic-snapshot branch stack  
**Default branch at audit time:** `main` at `e2d501b793c6f329d91c65399255dace5b9acc8a`  

---

## 1. Why this document exists

This file is the long-lived architecture, wiring, behavior and upgrade reference for TrendForge.

Use it before making future changes to:

- data collection,
- parsers and normalization,
- candidate discovery,
- feature calculation,
- strategy routing,
- evidence resolution,
- R2/R3/R4/R5/S2/S3/S4/S5/S6/S7/S8 behavior,
- equity intraday,
- equity swing,
- event/ownership research,
- MCX/commodity research,
- tradability and safety,
- opportunity ranking,
- snapshot/publication behavior,
- R16 outcome analysis,
- R18 governance,
- UI current/history behavior,
- broker/order extensions.

The purpose is to stop future patches from treating a local symptom as if it were an isolated function. Every important change should be checked against the whole producer -> contract -> consumer -> state -> publication chain.

This document is not proof that a feature is live or profitable. Runtime evidence wins over documentation.

### Evidence language

Use these exact meanings when reviewing future work:

- **VERIFIED RUNTIME-CONNECTED**: producer and consumer wiring were found in code and the path is operationally exercised by the reviewed implementation/tests.
- **DECLARED BUT NOT PROVEN ACTIVE**: registry/profile/contract exists, but a complete evaluator/publication path was not proven.
- **FIXTURE/TEST ONLY**: behavior exists or passes with fixtures/test data but live-source acceptance was not established.
- **NOT VERIFIED**: evidence was insufficient.

Do not allow registry declarations, UI labels, comments, document claims or function names to override observed runtime behavior.

---

## 2. Core architectural principle

TrendForge should evolve toward this model:

```text
SOURCE-SPECIFIC COLLECTION
Each source follows its real timing, revision and availability rules
                         |
                         v
VALIDATED + VERSIONED OBSERVATIONS
instrument/contract identity
source timestamp
availability timestamp
quality + hash + parser/schema version
freshness
corporate-action/rollover treatment
                         |
                         v
CHEAP ELIGIBILITY + SHARED BASIC FEATURES
                         |
                         v
MULTI-REASON DISCOVERY POOL
volume / gap / abnormal movement / event / ownership / disclosure /
OI / liquidity / developing structure / sector-index dislocation /
commodity context / other validated reasons
                         |
                         v
INSTRUMENT
One identified instrument may have several discovery reasons
                         |
                         v
STRATEGY ROUTER
market x holding period x setup x actual instrument/contract
                         |
                         v
STRATEGY-SPECIFIC OPPORTUNITY
One instrument may produce several independent opportunities
                         |
                         v
REUSE VALID SHARED FEATURES
COMPUTE ONLY MISSING DEPENDENCIES
                         |
                         v
STRATEGY-SPECIFIC QUALIFICATION
trigger / direction / evidence / missing proof / invalidation / freshness
                         |
                         v
EVENT / SAFETY / LIQUIDITY / COST / ELIGIBILITY
                         |
                         v
COMPARABLE OPPORTUNITY RANKING
                         |
                         v
IMMUTABLE PUBLISHED DECISION VERSION
                         |
                         v
UI / ALERTS / HISTORY / OUTCOMES / BACKTESTING / GOVERNANCE
```

Do not interpret this as a command to rebuild the application. Reuse existing good contracts and modules where they already express the right responsibility.

---

## 3. Three identities that must remain separate

### 3.1 Instrument

The actual security or commodity contract.

Examples:

- `INFY` equity,
- a particular MCX GOLD futures contract with expiry,
- a particular MCX CRUDEOIL contract with expiry.

### 3.2 Opportunity

One strategy/timeframe/direction/setup episode for one instrument.

Example:

```text
INFY / 5m / intraday bearish continuation / SHORT
INFY / 5m / failed-breakdown reversal / LONG
INFY / daily / swing continuation / LONG
INFY / event strategy / post-announcement acceptance / WAITING
```

These must not overwrite each other merely because the symbol is the same.

### 3.3 Decision version

One immutable assessment of one opportunity against one exact dependency snapshot.

A decision version should preserve:

- opportunity ID,
- instrument/contract identity,
- strategy/profile version,
- setup episode,
- timeframe,
- direction,
- dependency/input digest,
- data cutoff,
- decision time,
- publication time,
- valid-until/expiry time,
- feature versions,
- gate-policy versions,
- missing proof,
- entry/invalidation/target plan where applicable,
- cost/sizing assumptions.

Browser fetch time is not decision time.

`selection/contracts.py::SelectionCandidate` already contains useful pieces: instrument identity, market, profile/version, timeframe, state, state ceiling, evidence direction, missing proof, next confirmation, invalidation, freshness and completeness. Prefer extending and consistently carrying this contract rather than creating a competing universal candidate model.

---

## 4. What TrendForge is doing now

The main connected research flow is cash/EOD-centered. Other legacy, intraday, contextual, scanner and commodity paths exist around it.

```text
Configuration / source contracts / permissions
                 |
                 v
Market-data scheduler + source clients/parsers
                 |
                 v
Canonical market-data store + last-good lineage
                 |
                 v
Cash post-commit orchestrator for recognized source keys
                 |
                 v
A1 staging -> A2 identity/restrictions -> A3 discovery
                 |
                 v
history / index / F&O / corporate-action context
                 |
                 v
R1 source bundle
                 |
                 v
R2 attention order
                 |
                 v
R3 evidence adaptation/diagnostics
                 |
                 v
R4 identity -> R14 corporate actions -> R5 daily structure
                 |
                 v
S3 cheap discovery + S2 market weather + native guidance
                 |
                 v
S4 structure -> S5 enrichment -> S6 family resolution
                 |
                 v
S7 public research-state gates
                 |
                 v
S8 persistence/publication attempt
                 |
                 v
R16 point-in-time historical evaluation
                 |
                 v
R18 model/research governance
```

Important: numeric `R` labels are implementation milestones and `S` labels are workflow stages. They are not one single numeric runtime sequence.

---

## 5. Current strong foundations to preserve

### 5.1 Source lineage and canonical storage

Key owners include:

- `backend/trendforge_api/market_data_scheduler.py`
- `backend/trendforge_api/market_data_service.py`
- `backend/trendforge_api/market_data_store.py`

The system already tracks source keys, attempts, timestamps, hashes and normalized objects. Future work should strengthen availability/revision semantics rather than replace the store casually.

### 5.2 Cash post-commit orchestration

`backend/trendforge_api/selection/cash_post_commit.py`

Useful properties:

- separates data collection from downstream research processing,
- records stage state,
- avoids treating every source update as an unconditional full rebuild,
- can serve as a starting pattern for future dependency-driven recomputation.

Its trigger set is currently too narrow for the desired multi-strategy system; that is a wiring limitation, not a reason to discard the orchestrator.

### 5.3 Feature contracts

`backend/trendforge_api/feature_registry.py::FeatureContract`

Useful existing fields include:

- feature ID/version,
- horizon,
- inputs,
- deterministic calculation,
- evidence family,
- correlation group,
- double-count rule,
- stale/failure behavior,
- closed-bar requirement,
- storage/versioning,
- dependencies,
- tests,
- activation state.

Use this as the basis for versioned shared-feature reuse.

### 5.4 Evidence-family resolution

`backend/trendforge_api/selection/s6_family_resolution.py`

The design correctly attempts to prevent correlated evidence from being counted as multiple independent proofs. Preserve the separation between evidence strength and win probability.

### 5.5 S3 bulk history loading

`backend/trendforge_api/selection/s3_cheap_discovery.py`

The function already bulk-loads history for the desired symbols and benchmark rather than issuing a query per symbol. Preserve this pattern.

### 5.6 Snapshot consistency work

Key branch modules:

- `backend/trendforge_api/read_snapshot.py`
- `backend/trendforge_api/selection/snapshot_service.py`
- `backend/trendforge_api/selection/s8_service.py`
- `frontend/research-snapshot.js`

The snapshot work fixes mixed-generation display risks by using one request-scoped read view and one response envelope. Preserve that consistency guarantee while moving heavy calculations out of routine UI reads over time.

### 5.7 R16 replay/lease patterns

`backend/trendforge_api/selection/r16_service.py`

Worker lease, replay and incremental history patterns are useful for future dependency workers. They do not yet constitute the complete live dependency engine.

---

## 6. Discovery must be separate from direction

### Discovery question

> Why should TrendForge investigate this instrument?

Possible reasons:

- unusual volume,
- abnormal return magnitude,
- gap,
- pre-open imbalance,
- OI change,
- official company event,
- ownership change,
- institutional disclosure,
- developing technical structure,
- relative strength or weakness,
- sector/index dislocation,
- commodity-specific report/context,
- liquidity/activity change.

### Direction question

> What does this specific strategy conclude?

A negative mover with exceptional activity must be able to receive HIGH ATTENTION and then be evaluated independently for:

- bearish continuation,
- reversal,
- mean reversion,
- no trade.

Do not let one early bullish/bearish discovery assumption constrain every later strategy.

---

## 7. Verified findings register A01-A44

The findings below are the permanent short-form register. Before fixing one, open the named producer and consumer and reproduce the behavior on the current revision.

### A01 - Transport completeness is used as event clearance

**Files/functions:**

- `backend/trendforge_api/macro_event_context.py::build_macro_event_context_snapshot`
- `backend/trendforge_api/selection/s7_state_gates.py::build_s7_state`

The macro snapshot's `RESEARCH_ONLY` state is derived from source collection completeness. S7 uses `event_snapshot.state == "RESEARCH_ONLY"` as `blackout_known_clear=True`.

The producer also keeps `can_unlock_ready=False`, so collection completeness is not instrument-specific event clearance.

**Risk:** downloaded pages can be mistaken for proof that one instrument/strategy has no blocking event.

**Required replacement:** typed `EventClearanceResult` with instrument/contract, profile/strategy, event window, checked sources, coverage, evidence refs, assessment time, expiry and `CLEAR/BLOCKED/UNKNOWN`.

Metadata-only evidence must never create `CLEAR`. `UNKNOWN` must never silently become `CLEAR`.

### A02 - S7 and S8 disagree about CONFIRMED

**Files/functions:**

- `selection/s7_state_gates.py::classify_row/build_s7_state`
- `selection/s8_persist_run.py::S8RowV1.enforce_s8_row_law`
- `selection/s8_persist_run.py::S8ScanBlobV1`

S7 can produce CONFIRMED under its gated profile path, while S8's row/blob laws reject or pin away CONFIRMED.

**Risk:** state semantics differ across decision and publication layers.

**Rule:** do not fix this by simply deleting S8's safety prohibition. First repair proof semantics and design an explicitly versioned publication contract.

### A03 - Blocking gate outcomes are flattened to reason strings

**File/function:** `selection/s7_state_gates.py::classify_row`

Some upstream waits can survive as explanatory reasons rather than structured mandatory conditions consumed by the final gate.

**Risk:** a required block can become text instead of an enforced condition.

**Fix:** typed mandatory gate propagation with strategy-specific applicability.

### A04 - Guarded order extension lacks per-opportunity qualification check

**File:** `selection/guidance_oms.py`

Global environment/lane/arm controls exist, but the extension needs a current per-opportunity authorization boundary tied to a qualified immutable decision version.

**Required pre-trade proof:** decision version, matching instrument/contract, fresh market evidence, all applicable current gates, finite validated quantity, costs and idempotency.

### A05 - Loose market/security states can pass tradability

**File:** `selection/tradability.py`

Adversarial component inputs showed ambiguous state strings can be treated too loosely.

**Fix:** strict enums/normalization plus parser-boundary and gate-boundary rejection tests.

### A06 - Non-finite price bands and missing current-price handling

**File:** `selection/tradability.py`

NaN/infinite/missing numeric values require explicit fail-closed handling when they are mandatory for a restriction check.

### A07 - Tradability HTTP route reads nonexistent R5 `built_at`

**File:** `backend/trendforge_api/main.py`

The route accesses `r5_batch.built_at`, while `R5StructureBatchV1` uses `decision_at`.

**Fix:** choose an explicit time policy: snapshot decision time versus current tradability assessment time. Do not mix them accidentally.

### A08 - Main discovery cannot independently admit event-only instruments

**File:** `selection/s3_cheap_discovery.py::build_s3_cheap_discovery`

S3 iterates existing R2 rows and decorates them. A symbol present only in an event/ownership source can fail to enter the canonical discovery path if absent from R2.

**Fix:** multi-reason discovery admission. Admission must not imply WATCH/CONFIRMED qualification.

### A09 - Universal attention ordering favors positive returns

**File:** `selection/attention_order.py::_priority/build_attention_order`

Current formula:

```text
priority = 0.5 * returnPercentile
         + 0.5 * max(volumePercentile, turnoverPercentile)
```

With equal activity, strongly negative movers receive much lower priority than strongly positive movers.

**Fix candidates to test:** direction-neutral abnormality, separate bullish/bearish queues, separate strategy candidate budgets. Choose by whole-selector replay, not intuition.

### A10 - R5 structural direction is constrained by discovery direction

**File:** `selection/r5_live.py`

R5 chooses its structure profile using the upstream attention row's evidence direction.

**Risk:** downstream continuation/reversal hypotheses are not fully independent.

**Fix:** strategy router creates separate opportunity hypotheses; R5/structure evaluates the hypothesis passed by the strategy.

### A11 - Attention priority is reused as participation evidence strength

**File:** `selection/r3_claim_adapter.py::claims_from_cash_pipeline`

`attention_priority` becomes `strength_before_caps` for a participation claim.

**Risk:** investigation priority leaks into evidence strength.

**Fix:** attention remains queue priority. Participation evidence must be derived from an explicit participation feature.

### A12 - Relative strength is calculated but not used by the S7 RS companion

**Files:**

- `selection/s3_cheap_discovery.py::_history_metrics`
- `selection/s7_state_gates.py`

S3 computes RS outputs, but the main S7 path passes `rs_ok=None`.

**Fix:** strategy-specific RS contract: benchmark, lookback, timeframe, threshold, direction interpretation, freshness and expiry.

### A13 - Seven source profiles are ahead of executable routing

**File:** `selection/profile_source_contracts.py`

The project declares seven source profiles, but declaration does not prove seven independent evaluators/publication paths.

Main scan/tradability remains strongly coupled to PRF-003.

### A14 - Source registration gaps can hide behind profile completeness

Example: exact mandatory intraday key `openalgo_intraday_candles` has registration/wiring gaps.

**Rule:** track `DECLARED`, `REGISTERED`, `RUNTIME-CONNECTED`, `LIVE-DATA-VERIFIED` separately.

### A15 - Cadence intervals are not actual independent schedules

**File:** `market_data_scheduler.py`

Checkpoint dispatch and due-state suppression do not necessarily create an independent recurring execution at every declared interval.

**Fix:** executable next-due/release scheduling with retries and calendars.

### A16 - Commodity EOD and slow releases need their own calendars

Commodity data, weekly positioning, inventory reports, market holidays and contract events cannot share one generic cadence model.

**Fix:** source-specific publication/revision calendars.

### A17 - Pipeline invalidation covers only six source keys

**File:** `selection/cash_post_commit.py::RELEVANT_SOURCE_KEYS`

The main cash post-commit invalidation set is limited to cash EOD, F&O ban/MWPL, index, F&O bhavcopy and corporate actions.

Events, ownership, commodity releases and many other sources need explicit dependency routing.

### A18 - Canonical bar history loses information-availability time

**File:** `selection/r16_service.py::_bar_payload` and downstream availability handling.

Actual information availability can be dropped and later inferred using a conventional timestamp.

**Risk:** historical research can accidentally treat data as available earlier than it really was.

### A19 - History is immutable but does not support corrected bar vintages

A revised observation needs its own version/supersession relationship. Immutable storage alone is not enough when historical data can be corrected.

### A20 - Different intraday and daily feature meanings coexist

Examples:

- S3 relative volume uses a median baseline.
- R5 relative volume uses a mean baseline.
- intraday same-time cumulative volume is conceptually different from daily completed-session volume.

**Rule:** reuse tested functions only when semantics are identical. Give semantically different features separate names/versions.

### A21 - Enrichment display is not equivalent to decision evidence

S5/UI can display useful context that is not a qualifying evidence family in S6/S7.

**Rule:** document whether each field is `DISPLAY_ONLY`, `DISCOVERY`, `QUALIFICATION`, `RANKING`, `VETO`, or `OPTIONAL_CONTEXT`.

### A22 - Feature declarations, actual routes and equivalent implementations differ

A feature registry entry does not prove one canonical runtime producer/consumer path. Audit declarations against the actual function used by the strategy.

### A23 - Snapshot is consistent but compute-heavy

**Files:**

- `selection/snapshot_service.py`
- `selection/s8_service.py::assemble_current_scan`

One request now gets a consistent research snapshot, but the request still builds shared research/context such as S3/S4/S5/S6/S7, native guidance, Top 10, radar, comparison and MCX readiness depending on availability.

**Fix direction:** recompute affected results when dependencies change; publish immutable outputs; make UI primarily a reader.

### A24 - Canonical object reads are repeated within an assembly

**File:** `fii_stock_signals.py::CanonicalLatestResultLoader`

Repeated calls for the same source can reread bytes, rehash and decode JSON again.

**Fix:** request/assembly-scoped cache keyed by immutable content hash + parser/schema identity, without bypassing freshness or permission checks.

### A25 - Percentile calculation is quadratic across the universe

**File:** `selection/cash_a3_discovery.py::_percentile`

Current helper rescans the list for each value.

Fresh audit microbenchmark on 3,000 synthetic values:

- repeated scan: approximately 333 ms median for one metric,
- sort-once equivalent preserving tested tie semantics: approximately 1.44 ms.

This is a microbenchmark, not an application-wide speed claim.

### A26 - CLI and shared scan service assemble different pipelines

Multiple scan assembly paths can diverge over time.

**Fix:** one canonical assembly/evaluation service; CLI/HTTP become adapters and presentation layers.

### A27 - Opportunity identity collapses to symbol in downstream persistence

Some joins/persistence are symbol-oriented, which is insufficient once one instrument has multiple timeframes/strategies/setup episodes.

**Fix:** stable `opportunity_id` and `decision_version_id` end to end.

### A28 - Published identity and current pointers need stronger lineage semantics

Current/latest should point to an immutable validated result, not imply that a recomputed browser response is the published decision.

### A29 - Compatibility reads can build and persist research

Some GET/latest compatibility paths can trigger assembly/persistence rather than act as pure reads.

**Fix:** explicit command/query separation. UI reads published state; update workers own writes.

### A30 - Saved artifacts can outlive retained source evidence

If source retention is shorter than decision-history retention, a decision can become impossible to reconstruct.

**Fix:** retain referenced evidence by content hash/object root for as long as any decision/outcome requires it.

### A31 - R16 rejects legitimate multiple intraday versions on one date

**File:** `selection/r16_service.py::_select_s8_history`

Grouping conflict logic can reject differing valid same-day scans.

**Fix:** decision-version identity must support multiple decisions per date.

### A32 - R16 labels proxy hypotheses rather than every exact published plan

Historical outcome labels should evaluate the exact published strategy plan/version when it exists, not reconstruct a different proxy.

### A33 - R18 governance cannot itself prove valid training or holdout isolation

Governance code can enforce metadata/workflow rules; it cannot prove that the research design avoided leakage unless the dataset construction and chronology are valid.

### A34 - Cash identity stage applies derivative ban before strategy applicability

A derivative-specific restriction must not block a cash-only strategy unless that strategy actually uses the derivative instrument/risk condition.

### A35 - Parameter fanout reads lack the canonical loader integrity contract

Alternative data-read paths must preserve the same integrity/hash/schema/lineage guarantees as the canonical loader.

### A36 - Liquidity and costs are not a unified final opportunity-quality model

The repository has separate liquidity/sizing/cost pieces, but the final comparable opportunity ranking does not yet have one coherent net-executable quality contract.

### A37 - UI freshness is mostly refresh-event driven

A result can become stale simply because time passes. UI should show validity expiry and update stale state on the clock, not only after another fetch.

### A38 - Readiness and execution claims in documentation need a versioned capability ledger

A feature can be:

- code implemented,
- test passed,
- real data observed,
- data fresh,
- strategy activated,
- PIT approved,
- model approved,
- execution authorized.

These are different facts. Maintain a current versioned capability ledger.

### A39 - Full local tests are not a pinned-environment certification

Audit run result:

- backend: 1,493 passed, 17 failed, 2 skipped,
- frontend: passed,
- 15 backend failures related to NumPy/Pandas engine-pin mismatch,
- 2 related to unavailable PyArrow.

Do not weaken engine/version guards to make tests green.

### A40 - Ranking partitions and final shortlist quality need explicit policy

Do not rank a 5-minute equity reversal directly against a 7-day GOLD swing with one generic score.

Rank within compatible groups such as market, strategy, holding period, direction/risk class and instrument class. Permit fewer than N qualified candidates.

### A41 - R16 time changes and research dataset recalculation are not live dependency routing

R16 is useful for replay/history but does not automatically provide live instrument/sector/index/universe/strategy/time/contract invalidation.

### A42 - Optional native claim-ID projection is duplicated without family re-resolution

Native/scanner projections must not create additional independent evidence by duplicating claim identities or family representatives without going back through the canonical resolver.

### A43 - Legacy indicator labels hide different window and session semantics

Labels such as VWAP/volume/compression can refer to calculations with different windows or session-reset behavior.

**Fix:** explicit feature semantics, timeframe/session and version in storage/API/UI.

### A44 - Last-finite indicator extraction loses the value timestamp

Returning the last finite value can silently use an older bar if the newest value is invalid/warming up.

**Fix:** return value + source bar timestamp + validity state together.

---

## 8. Correct event-clearance model

Introduce an explicit scoped contract rather than using macro collection state.

Suggested fields:

```text
EventClearanceResult
- instrument_id / contract_id
- opportunity_id
- profile_id / strategy_version
- event_window_start
- event_window_end
- checked_source_keys
- source_coverage
- parser/semantic coverage
- evidence_refs
- assessed_at
- valid_until
- result: CLEAR | BLOCKED | UNKNOWN
- reason_codes
```

Rules:

1. download success != parse success,
2. parse success != semantic completeness,
3. semantic completeness != correct instrument mapping,
4. instrument mapping != strategy-specific event clearance,
5. missing mandatory coverage -> UNKNOWN,
6. expired clearance -> UNKNOWN until recalculated,
7. only a valid scoped assessment can produce CLEAR.

This prevents the failure pattern:

```text
pages downloaded
-> collection state looks complete
-> S7 treats blackout clear
-> other gates pass
-> false qualification attempt
```

and replaces it with:

```text
pages downloaded
-> parsing/mapping incomplete
-> EventClearanceResult.UNKNOWN
-> strategy cannot qualify
```

---

## 9. Discovery pool design

Create one instrument-level discovery object containing multiple reasons, each with provenance and expiry.

Suggested reason identity:

```text
DiscoveryReason
- instrument_id/contract_id
- reason_type
- direction_of_observed_fact (optional; not strategy direction)
- detected_at
- data_cutoff
- valid_until
- source_refs
- feature_refs
- magnitude/abnormality
- admission_policy_version
```

Admission uses OR logic across validated reasons.

Examples:

```text
ABC:
  unusual volume
  gap up
  official event
  near daily resistance
```

This is one instrument with four investigation reasons, not four independent confirming votes.

Do not automatically change public state because a reason exists.

---

## 10. Strategy routing and evidence contracts

Each strategy should declare every input as one of:

- `REQUIRED_TO_CALCULATE`
- `REQUIRED_TO_QUALIFY`
- `OPTIONAL_CONTEXT`
- `PROHIBITED_FOR_THIS_CONDITION`

### Equity intraday continuation

Core concepts:

- verified closed intraday bars,
- session VWAP,
- same-time relative volume,
- liquidity/spread/trade quality,
- index/sector regime,
- trigger/invalidation.

Monthly ownership change may be optional context; it cannot replace the intraday trigger.

### Equity intraday reversal

Core concepts:

- failed acceptance/breakout,
- closed reclaim/reversal confirmation,
- distance from reference levels,
- current participation,
- strategy-specific relative weakness/reclaim logic.

Large gap or high volume alone is not a reversal trigger.

### Equity swing continuation

Core concepts:

- adjusted closed daily bars,
- R14-consistent corporate-action treatment,
- daily structure,
- daily relative volume,
- strategy-specific relative strength,
- volatility/geometry-based invalidation,
- event clearance and tradability.

### Equity event/ownership

Core concepts:

- verified event identity,
- publication/availability time,
- actor identity when claimed,
- reported holdings quantity change,
- corporate-action-adjusted comparability,
- post-event price acceptance.

Market-wide FII/DII flow cannot prove that a named institution bought one stock.

### Commodity intraday

Core concepts:

- exact tradable contract,
- local bars,
- local volume/OI,
- bid/ask spread,
- lot/tick size,
- session,
- expiry/tender/delivery restrictions.

Slow macro data is context, not an intraday trigger.

### Commodity swing

Core concepts:

- contract-aware daily structure,
- rollover treatment,
- currency context,
- relevant inventory/positioning/supply-demand data,
- publication vintages,
- expiry/roll restrictions.

Gold, crude oil, natural gas, copper and agriculture should not share one undifferentiated commodity score.

---

## 11. Shared feature and cache policy

### Reuse functions, not incompatible results

Same code can calculate ATR on 5m and daily bars, but the outputs are different features because timeframe/session/input versions differ.

Feature key should include at least:

```text
instrument/contract
feature ID + version
parameters
timeframe/session
input-vintage digest
corporate-action/roll policy
data cutoff
validity interval
```

Cross-sectional features additionally need comparison-universe/cohort version.

### Proposed cache layers

1. **Decoded source cache**
   - content hash,
   - parser/schema version,
   - access/permission scope.

2. **Feature cache**
   - instrument/contract,
   - timeframe/session,
   - feature/version/parameters,
   - dependency digest,
   - adjustment/roll policy,
   - cutoff.

3. **Cross-sectional cache**
   - above + cohort/universe version.

4. **Strategy-evaluation cache**
   - opportunity identity,
   - strategy version,
   - dependency digest,
   - gate-policy version,
   - validity interval.

5. **Published decision store**
   - immutable decision-version ID.

Caching immutable data must not freeze time-sensitive freshness, permissions, event clearance, market state or contract eligibility.

---

## 12. Dependency-driven recalculation

Every feature/strategy must declare one or more dependency classes:

- `INSTRUMENT_LOCAL`
- `SECTOR_WIDE`
- `INDEX_WIDE`
- `UNIVERSE_WIDE`
- `STRATEGY_WIDE`
- `MARKET_WIDE`
- `TIME_DRIVEN`
- `SOURCE_DRIVEN`
- `CONTRACT_DRIVEN`

Examples:

### New instrument 5m bar

```text
instrument local features
-> applicable intraday opportunities
-> if cross-sectional input changed, relevant cohort ranking
```

### New sector/index value

```text
sector/index features
-> relative-strength results for dependent instruments
-> dependent strategies
```

### New company filing

```text
affected instrument event facts
-> event clearance/event strategy
-> swing strategies that declare event dependency
```

### New monthly fund portfolio

```text
changed holdings only
-> ownership features for affected instruments
-> event/ownership strategies
```

Do not recalculate every instrument's intraday indicators.

### New natural-gas storage report

```text
natural-gas context vintage
-> dependent gas strategies only
```

### Session change

```text
reset/invalidate session VWAP
same-time volume baseline context
session state
intraday opportunity validity
```

### Time passes beyond clearance expiry

No source file is required. Time itself invalidates the gate and dependent decision.

### Commodity contract approaches expiry/tender window

Contract-driven recalculation of eligibility and opportunity validity.

---

## 13. Publication model

Preferred flow:

```text
source/clock/contract event
-> determine affected dependency graph
-> recompute affected features/opportunities
-> validate complete strategy result
-> write immutable decision version
-> atomically move that strategy/opportunity current pointer
-> publish notification/outbox event
```

The UI should primarily read completed decision versions.

Keep the previous version accessible, but if it is no longer valid show it as stale/expired. Do not retain its former readiness as if it were current.

Separate timestamps:

- source event time,
- source availability time,
- data cutoff,
- decision time,
- publication time,
- browser fetch time.

Never rewrite decision history after a formula or dataset changes.

---

## 14. UI rules

The UI must clearly distinguish:

- current published result,
- stale/expired result,
- historical result,
- fixture/demo result,
- research-only result,
- incomplete result,
- unknown evidence,
- missing data,
- qualification failure,
- safety block.

Consistency does not mean freshness.

A recalculation failure must not leave an old CONFIRMED/READY-looking card without an explicit stale/expired label.

Every displayed opportunity should expose enough provenance to locate:

- opportunity ID,
- decision version,
- strategy/profile version,
- decision time,
- valid-until,
- data cutoff,
- primary missing proof/blocker.

---

## 15. Outcome tracking

For every published opportunity, append outcome events rather than overwriting the decision.

Track:

- trigger occurred,
- entry became valid,
- entry was never reached,
- invalidation occurred,
- target reached,
- stop reached,
- expired without entry,
- MFE,
- MAE,
- time to trigger,
- time to target,
- time to stop,
- gap-through behavior,
- same-bar ambiguity,
- missing/invalid bar problems,
- data-quality problems,
- contract roll issues.

Outcome analysis must evaluate the exact published strategy plan/version whenever possible.

---

## 16. Backtesting/research validity rules

Audit every historical strategy for:

- lookahead,
- revised-data leakage,
- source publication-time leakage,
- corporate-action leakage,
- contract-roll leakage,
- same-bar execution assumptions,
- intrabar ambiguity,
- bar-close timing,
- survivorship bias,
- universe leakage,
- selection bias,
- transaction cost omission,
- slippage omission,
- repeated strategy/configuration search overfitting.

Historical evaluation must reconstruct what was actually knowable at the decision time.

The whole selector must be tested:

```text
historical source availability
-> discovery admission
-> strategy routing
-> qualification
-> ranking
-> execution assumptions
-> outcome
```

Do not backtest only the final chosen stocks using today's candidate list.

---

## 17. Exact implementation order TF-00 to TF-25

Future work should follow this dependency order unless a new audit proves a better ordering.

### Phase A - establish a trustworthy decision contract

#### TF-00 - Verified baseline

- reproduce backend/frontend/type-checks in repository-pinned dependencies,
- compare current branch/PR state,
- record failures without disabling guards,
- establish exact revision under test.

#### TF-01 - Event clearance and typed mandatory gates

- replace macro-state-as-clearance behavior,
- create scoped EventClearanceResult,
- carry mandatory gates as typed conditions,
- test metadata-only, partial, expired, contradictory and unknown evidence.

#### TF-02 - Tradability correctness

- strict state enums,
- finite numeric checks,
- explicit current-price inputs,
- explicit time policy,
- strategy applicability,
- fix `R5StructureBatchV1.built_at` misuse.

#### TF-03 - Order-extension boundary

- add per-opportunity qualified decision proof,
- current-market/tradability recheck,
- idempotency,
- quantity/cost validation,
- mock rejection tests,
- do not activate live orders.

#### TF-04 - S7/S8 state compatibility

- define one versioned publication state contract,
- carry proof references,
- preserve safety ceilings intentionally,
- do not remove S8 controls before S7 proof semantics are correct.

#### TF-05 - Canonical assembly

- one canonical strategy assembly/evaluation service,
- HTTP/CLI/collector become adapters,
- explicit event/gate inputs,
- explicit persistence ownership,
- no hidden write inside compatibility reads.

**Phase-A exit:** equivalent inputs produce equivalent decisions across callers; missing required proof cannot become qualification.

### Phase B - repair observation identity, timing and revisions

#### TF-06 - Availability and revision vintages

- preserve actual release/availability/receipt timestamps,
- support corrected/superseded observations,
- retain transitive evidence roots,
- never infer an earlier historical availability without proof.

#### TF-07 - Temporal security/contract identity

- symbol aliases/changes,
- corporate-action version,
- actual MCX contract,
- expiry,
- rollover policy,
- units and currency.

#### TF-08 - Reconcile source/parser/permission contracts

For every named source and endpoint, record:

- owner,
- parser,
- schedule,
- source timestamp,
- availability timestamp,
- revision policy,
- mapping scope,
- permitted strategy uses,
- live acceptance evidence.

Resolve exact-key gaps rather than hiding behind aggregate completeness.

#### TF-09 - Executable source scheduling

- next-due/release logic,
- market calendars,
- publisher calendars,
- retry/backoff,
- revisions,
- one clear acquisition owner per dataset.

**Phase-B exit:** every observation can be traced to true identity, vintage, availability and permitted use.

### Phase C - separate discovery from opportunity evaluation

#### TF-10 - Stable opportunity and episode identity

Extend existing contracts to carry:

- opportunity ID,
- setup episode,
- strategy/timeframe/direction,
- decision version.

#### TF-11 - Multi-reason admission and neutral attention

- allow validated source-specific reasons to introduce instruments,
- preserve multiple reasons without duplicate votes,
- test bearish/gap-down/event-only admissions,
- compare neutral abnormality and separate strategy budgets.

#### TF-12 - Versioned feature reuse and low-risk speed fixes

- optimize percentile with exact tie-parity tests,
- cache validated decoded objects per immutable hash,
- version different RVOL/VWAP/compression semantics,
- carry value timestamps,
- define dependency digests.

#### TF-13 - Executable profile bindings

For every strategy/profile, bind:

- evaluator,
- required features,
- optional/prohibited inputs,
- RS contract,
- gate policy,
- ranking group,
- publication path.

**Phase-C exit:** discovery reason, observed move direction, strategy direction, qualification and rank are independently represented.

### Phase D - complete strategies one by one

#### TF-14 - Equity swing baseline first

Complete and validate PRF-003-style daily continuation with:

- adjusted daily structure,
- R14 lineage,
- daily participation,
- strategy-specific RS,
- event clearance,
- tradability,
- trigger/invalidation,
- proof-carrying publication.

#### TF-15 - Equity intraday continuation

Require:

- verified closed bars,
- session VWAP,
- same-time RVOL,
- current liquidity,
- sector/index context,
- exact entry timing assumptions.

#### TF-16 - Reversal strategies

Implement intraday reversal independently and define swing reversal as a separate explicit policy if required. Do not treat direction sign inversion as a complete strategy.

#### TF-17 - Event and ownership opportunity strategy

- actor/event identity,
- reporting/publication period,
- availability time,
- adjusted holdings quantity,
- post-event acceptance,
- explicit optional versus mandatory context.

#### TF-18 - Commodity strategies

Separate by:

- commodity group,
- intraday versus swing horizon,
- actual contract,
- local structure/OI/liquidity,
- currency/unit rules,
- expiry/roll/tender rules,
- relevant slow context.

#### TF-19 - Net-cost eligibility and comparable ranking

- spread/slippage/charges,
- lot/tick sizing,
- capacity/turnover,
- reward relative to cost/invalidation,
- ranking within comparable groups,
- permit fewer than requested N results.

**Phase-D exit:** each strategy can be tested independently and remains unapproved until its own acceptance evidence exists.

### Phase E - incremental computation, publication and UI

#### TF-20 - Dependency and clock-driven incremental tasks

- implement dependency classes,
- bounded worker ownership/retries,
- event/time/contract invalidation,
- incremental versus full-recompute equivalence tests.

#### TF-21 - Immutable publication

- validated immutable result version,
- atomic current pointer per strategy/opportunity,
- complete dependency hash,
- transactional notification outbox.

#### TF-22 - UI/API/alerts for opportunity versions

- read published versions,
- display expiry/stale/incomplete states,
- preserve history,
- no stale readiness after failed recalculation.

#### TF-23 - Exact outcomes and historical repair

- multiple decisions per day,
- exact plans,
- actual availability,
- trigger/no-entry/expiry/ambiguous/censored outcomes.

**Phase-E exit:** browser refresh cannot create a new decision, mix generations or make an expired result appear current.

### Phase F - prove value and reliability

#### TF-24 - Whole-selector research validation

Compare, in order:

1. simple price/volume/gap baseline,
2. strategy-specific routing,
3. event/institutional context,
4. additional source families individually.

Use chronological holdouts, realistic costs and a record of failed experiments.

#### TF-25 - Real-data operational acceptance

Verify:

- entitled source behavior,
- target-machine latency/load,
- recovery after failures/restarts,
- corrections/revisions,
- stale handling,
- source outages,
- shadow/paper forward operation.

Do not automatically activate live trading.

---

## 18. Acceptance invariants for all future patches

1. **No mandatory UNKNOWN becomes PASS.**
2. **Optional missing context does not freeze unrelated strategies.**
3. **Discovery attention cannot substitute for strategy evidence.**
4. **One instrument can hold multiple independent opportunities.**
5. **One opportunity can have multiple immutable decision versions.**
6. **Decision direction belongs to the strategy, not the discovery queue.**
7. **A source download does not prove semantic completeness.**
8. **A parsed source does not prove instrument mapping.**
9. **A mapped source does not automatically prove strategy qualification.**
10. **UI consistency does not imply freshness.**
11. **Browser fetch must not rewrite historical decision time.**
12. **Different feature semantics retain different IDs/versions.**
13. **Cross-sectional updates can invalidate more than one instrument.**
14. **Time and contract state are dependencies even without new files.**
15. **Published decision evidence must remain reconstructable.**
16. **No scanner/context duplicate becomes an independent evidence family without canonical resolution.**
17. **No live-order boundary relies only on a global arm switch.**
18. **Historical tests use what was available then, not what is known now.**
19. **A passing test proves only the tested contract/environment, not live profitability.**
20. **Architecture changes require before/after whole-flow regression evidence.**

---

## 19. Current source/profile interpretation

Declared source profiles in `selection/profile_source_contracts.py`:

- PRF-001 - NSE intraday continuation,
- PRF-002 - NSE intraday reversal,
- PRF-003 - NSE swing continuation,
- PRF-004 - NSE event and accumulation,
- PRF-005 - MCX precious metals,
- PRF-006 - MCX energy,
- PRF-007 - MCX base metals and agriculture.

Treat these as source/evidence contracts until the full strategy evaluator + gates + publication + live-data verification chain is proven.

At the reviewed revision, the main connected selection assembly remains most mature around the cash/EOD PRF-003 path.

---

## 20. Performance priorities

Do not optimize by deleting sources or merging semantically different calculations.

Highest-value efficiency work after correctness:

1. sort-once percentile/rank calculations,
2. decoded immutable source cache within assembly,
3. feature cache keyed by exact dependency digest,
4. dependency-driven recalculation,
5. publish-on-change rather than calculate-on-screen-open,
6. bulk history/source reads,
7. bounded expensive enrichment only for routed candidates,
8. time-driven invalidation without full recomputation,
9. cross-sectional recomputation only for affected cohorts,
10. metrics for download-to-decision latency, cache hits, stale incidents and mixed-version rejection.

---

## 21. What remains NOT VERIFIED

Unless newer evidence is recorded in a later current-state document, do not assume:

- every configured provider is currently reachable,
- every parser matches the provider's present schema,
- every one of the declared strategies has a live runtime evaluator,
- live intraday candles are accepted end to end for all intended profiles,
- every commodity profile has a complete contract-aware strategy path,
- production target-machine latency is acceptable,
- broker connectivity is currently valid,
- PIT approval is granted,
- model approval is granted,
- execution is authorized,
- any architecture change improves trading profitability.

---

## 22. How future engineers/AI agents should use this file

Before modifying TrendForge:

1. identify the affected finding/ticket/stage in this file,
2. inspect the current code rather than trusting this document blindly,
3. identify producer -> contract -> consumer -> state -> publication path,
4. verify source/timeframe/strategy applicability,
5. write adversarial tests before or with the patch,
6. preserve lineage and historical behavior intentionally,
7. run focused tests,
8. run full regression in the pinned environment,
9. inspect UI/read behavior if the contract reaches the UI,
10. update current capability/readiness documentation,
11. record observed results separately from intended design,
12. do not advance the next activation stage until the current stage's acceptance gate is satisfied.

For debugging, ask these questions in order:

```text
What exact observation entered?
Was it available at the decision time?
Which parser/normalizer produced the fact?
Which feature/version consumed it?
Which discovery reason admitted the instrument?
Which opportunity/strategy evaluated it?
Which mandatory evidence was required?
Which gates were PASS/BLOCKED/UNKNOWN?
Which rank group compared it?
Which immutable decision version was published?
What did the UI actually read?
What exact outcome version later evaluated it?
```

---

## 23. Relationship to other repository documents

Use this file for the **application skeleton, wiring, behavioral boundaries and ordered upgrade roadmap**.

Use `docs/CURRENT_STATE.md` for the latest concise implementation/readiness summary.

Use `docs/ATOMIC_RESEARCH_SNAPSHOT.md` and `docs/ATOMIC_SNAPSHOT_VERIFICATION.md` for the atomic-snapshot contract and observed verification.

Use the older `fileindex.md` checkpoints only as historical navigation after reading the current boundary. Their wording such as "current", "next", "implemented" or "passed" belongs to those dated checkpoints.

The pre-system-brain version of `fileindex.md` is preserved at:

`docs/archive/fileindex_before_system_brain_2026-09-08.md`

This preservation exists so no historical navigation or audit trail is lost when `fileindex.md` is simplified into the current navigation layer.

---

## 24. Current priority

The approved correction order from this audit is:

```text
1. Reproduce pinned baseline.
2. Correct event-clearance and mandatory-gate semantics.
3. Repair tradability and current-time/current-price semantics.
4. Strengthen the per-opportunity execution boundary without activating it.
5. Align S7/S8 publication state contracts.
6. Consolidate canonical assembly and side-effect ownership.
7. Repair availability/revision identity.
8. Repair temporal security/contract identity.
9. Reconcile source/parser/permission contracts.
10. Implement executable source scheduling.
11. Introduce stable opportunity identity.
12. Build multi-reason discovery and neutral attention.
13. Version/reuse features and apply safe performance fixes.
14. Make profile declarations executable.
15. Complete strategies one at a time.
16. Add net-cost comparable ranking.
17. Add dependency/clock incremental recomputation.
18. Publish immutable results and make UI a reader.
19. Record exact outcomes.
20. Validate the whole selector and only then advance operational acceptance.
```

Do not skip correctness phases because a later feature appears more exciting.

---

## 25. Change-control rule for this system-brain document

When a future patch materially changes architecture, ownership, state meaning, source timing, strategy routing or publication behavior:

- update the relevant section here,
- cite the new owning file/function,
- record whether the result is VERIFIED, DECLARED, FIXTURE/TEST ONLY or NOT VERIFIED,
- keep older observed history in an explicitly dated history/reference document,
- never rewrite a past verification claim to make it look as though it was always true.

This file is a navigation and reasoning authority for future implementation work, but runtime behavior remains the final authority.

---

## 26. Production-readiness execution checkpoint — TF-00 baseline and TF-01 entry gate

**Recorded:** 2026-09-08  
**Baseline branch:** `docs/trendforge-system-brain`  
**Baseline commit under CI:** `9d72a409efccd6d50ba77131283acb198bea4b6a`  
**PR CI run:** `34234433122`  

This section is the starting verification checkpoint for using the TF roadmap to drive TrendForge toward production readiness. It does not declare the system production-ready, AGI-ready, profitable, execution-authorized or live-data-verified.

### 26.1 TF-00 — Verified Production Baseline

TF-00 exists to establish a truthful, reproducible starting point before any safety/architecture patch.

The documentation/index change initially exposed a frontend contract requirement: `fileindex.md` needed to retain the explicit `CURRENT_STATE_HISTORY_BOUNDARY` marker. Commit `9d72a409efccd6d50ba77131283acb198bea4b6a` restored that boundary.

At the time this checkpoint is written, the CI for that commit has **completed**. The earlier wording that backend/typecheck were still running is superseded by these final observed results:

| Check | Final observed result |
| --- | ---: |
| Full backend tests | **1,512 passed** |
| Backend warnings | **2 warnings** |
| Ruff | **Passed** |
| Frontend | **Passed** |
| Mypy/type checking | **513 errors in 70 files; 266 source files checked** |

The GitHub workflow is overall green because the typecheck job is intentionally non-blocking, but the Mypy result remains a real unresolved engineering baseline. Do not interpret a green workflow badge as proof that the codebase is production-ready.

The error population spans parsers, market-data service/scheduler, intraday analysis, commodity code, R16/PIT code, tradability, scanners, selection/resolution code, source/profile contracts, UI-support modules and other areas. Some errors appear to be model-construction or annotation mismatches; others involve `None` handling, invalid attribute assumptions, incompatible states, numeric optionality and other conditions that may correspond to runtime risk.

#### Known concrete baseline defect

The CI still reports:

```text
trendforge_api/main.py:1795:
"R5StructureBatchV1" has no attribute "built_at"
```

This independently confirms finding **A07** remains present at the TF-00 baseline.

#### TF-00 error-classification policy

Do **not** attempt to mechanically eliminate all 513 Mypy errors before architecture work. First classify them into:

1. **RUNTIME_DANGEROUS**
   - possible `None` dereference,
   - wrong/nonexistent attribute,
   - invalid numeric operation,
   - wrong state/contract assumption,
   - invalid scheduler/data-flow return type,
   - anything that can change data, gate, publication or execution correctness.

2. **CONTRACT_TYPE_MISMATCH**
   - alias/model constructor mismatch,
   - literal/enum narrowing issue,
   - list/tuple variance or declared interface mismatch that needs review but is not automatically a runtime bug.

3. **FIXTURE_TEST_ONLY**
   - errors confined to fixture/test-support code that cannot enter production runtime.

4. **LOW_RISK_TYPING_CLEANUP**
   - annotation/style issues that do not affect runtime semantics after inspection.

A Mypy error must not be classified from its error code alone; inspect the actual producer, consumer and runtime reachability.

#### TF-00 completion gate

TF-00 may be considered complete only when all of the following are recorded:

- pinned/declared dependency environment reproduced,
- exact tested revision recorded,
- backend result recorded,
- Ruff result recorded,
- frontend result recorded,
- full Mypy baseline recorded,
- the 513 errors classified by risk/reachability,
- P0 runtime defects that would make TF-01 testing unreliable are fixed or explicitly isolated,
- remaining risk is documented.

**Current TF-00 status:** **CI baseline captured; Mypy risk classification remains open.**

Do not advance TF-01 into implementation/activation until TF-00's classification and P0-baseline gate are closed. Investigation and test design for TF-01 may proceed in parallel, but production claims may not.

### 26.2 TF-01 — first runtime production-safety correction

Once TF-00 is closed, the first code-level safety stage is:

**TF-01 — Event clearance + mandatory gate semantics**

This comes before discovery optimization, new indicators, ranking changes, additional data links or strategy activation because a qualification gate must mean what its name claims.

The already reproduced dangerous semantic pattern is:

```text
Event-related pages successfully collected
        |
        v
macro event state = RESEARCH_ONLY
        |
        v
S7 interprets that state as event blackout clear
        |
        v
other required gates pass
        |
        v
S7 may produce CONFIRMED
```

The correct contract is:

```text
Sources downloaded
        |
        v
Sources parsed
        |
        v
Events mapped to the exact instrument/contract
        |
        v
Determine whether each event applies to THIS strategy/profile
        |
        v
Evaluate the relevant event window and source coverage
        |
        v
EventClearanceResult = CLEAR | BLOCKED | UNKNOWN
        |
        v
Only valid, unexpired CLEAR may satisfy the mandatory event gate
```

#### Practical example — INFY results event

Dangerous interpretation:

```text
NSE announcement page downloaded successfully
-> source system healthy
-> treated as event-clear
-> swing breakout passes the other gates
-> CONFIRMED candidate may be produced at S7
```

But source availability is not instrument-specific semantic clearance.

Correct behavior:

```text
Announcement page downloaded
-> parser/mapping coverage is incomplete
-> INFY event coverage is not proven complete
-> EventClearanceResult = UNKNOWN
-> the affected swing opportunity remains WAIT
```

This prevents the system from qualifying a stock immediately before a material result/event merely because the source website responded successfully.

TF-01 must also repair the broader **mandatory-gate propagation** issue from finding A03: required upstream WAIT/UNKNOWN conditions must remain typed enforced conditions, not become explanatory strings that can be ignored by later classification.

### 26.3 TF-01 required acceptance tests

At minimum, TF-01 must adversarially prove:

1. transport success + no semantic parsing -> `UNKNOWN`, never `CLEAR`,
2. parsed source + incomplete coverage -> `UNKNOWN`,
3. correct instrument mapping + relevant blocking event -> `BLOCKED`,
4. complete applicable coverage + no blocking event -> `CLEAR`,
5. expired `CLEAR` -> no longer passes until recalculated,
6. event for another instrument cannot block/clear this opportunity,
7. event relevant to one strategy does not automatically block unrelated strategies unless their evidence contract declares it,
8. contradictory sources -> `UNKNOWN` or explicit conflict policy, never silent `CLEAR`,
9. missing mandatory upstream gate cannot be converted to a reason string and then ignored,
10. S7/S8 publication behavior remains fail-closed while TF-04 has not yet aligned their state contract,
11. no change activates live orders.

### 26.4 Production-readiness sequence from this checkpoint

```text
TF-00  Verified baseline
   |
   v
TF-01  Event + mandatory gates
   |
   v
TF-02  Tradability correctness
   |
   v
TF-03  Live-order/pre-trade boundary
   |
   v
TF-04  S7 <-> S8 state/publication contract
   |
   v
TF-05  One canonical assembly path
   |
   v
TF-06  Data timestamps + revisions
   |
   v
TF-07  Instrument / contract identity
   |
   v
TF-08  Verify every source contract
   |
   v
TF-09  Correct source-specific scheduling
   |
   v
TF-10  Instrument -> multiple opportunities
   |
   v
TF-11  Multi-reason discovery
   |
   v
TF-12  Shared feature reuse + performance
   |
   v
TF-13  Executable strategy profiles
   |
   v
TF-14  Equity swing
TF-15  Equity intraday continuation
TF-16  Reversal strategies
TF-17  Event / ownership
TF-18  Commodities
TF-19  Cost / liquidity / ranking
   |
   v
TF-20  Incremental recalculation
TF-21  Immutable publication
TF-22  UI / alerts
TF-23  Exact outcome tracking
   |
   v
TF-24  Whole-system backtest
TF-25  Real-data / shadow production acceptance
```

### 26.5 Stage-advance rule

Do not move a TF stage to **complete/accepted** until the current stage has all of these:

1. reproduced current-state problem or explicit verified requirement,
2. exact contract/behavior change defined,
3. implementation where needed,
4. adversarial tests,
5. focused tests,
6. full pinned regression evidence,
7. before/after evidence,
8. remaining-risk statement,
9. documentation/current-state update,
10. no accidental expansion of execution authority.

The controlling rule is:

> **A green test suite is necessary evidence, not production-readiness proof. A stage is accepted only when its semantic contract, failure behavior, runtime wiring and remaining risk are all verified.**
