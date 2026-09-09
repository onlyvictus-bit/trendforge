# TrendForge Trading Brain / Strategy Engine Reference

**Purpose:** permanent plain-English reference for how TrendForge should discover, calculate, compare, publish and later evaluate trading opportunities across equity intraday, equity swing, event/ownership and commodities.

**Architecture status:** intended system architecture and future-build reference. This document does **not** claim that every strategy path is runtime-complete, profitable, live-data-verified, model-approved or execution-authorized. Always read `docs/CURRENT_STATE.md` and inspect the current code before changing or activating anything.

**Primary architecture authority:** `docs/TRENDFORGE_SYSTEM_BRAIN_AND_IMPLEMENTATION_ROADMAP_2026-09-08.md`.

---

## 1. Simple mental model

Think of TrendForge like a smart student:

```text
Eyes        = collect market and contextual data
Notebook    = R-HIST: remember exactly what was known at that time
Brain       = discover, calculate and compare independent trading opportunities
Teacher     = safety, tradability, event, liquidity and publication gates
Report card = outcome tracking, backtesting and research/model governance
```

Historical retention is not the whole trading brain. It is the memory layer that makes later strategy learning and evaluation trustworthy.

The brain must never train on information that became available only after the decision was made.

---

## 2. The non-negotiable identity rule

```text
INSTRUMENT != OPPORTUNITY != DECISION VERSION
```

### Instrument

The thing being traded or investigated.

Examples:

```text
INFY equity
MCX GOLD October futures contract
MCX CRUDEOIL November futures contract
```

### Opportunity

One independent strategy/timeframe/direction/setup episode for that instrument.

For example, one INFY instrument may simultaneously have:

```text
INFY / 5m / bearish continuation / SHORT
INFY / 5m / failed-breakdown reversal / LONG
INFY / daily / swing continuation / LONG
INFY / event-ownership / post-event acceptance / WAIT
```

These are different opportunities. They must not overwrite each other just because the symbol is the same.

### Decision version

One immutable evaluation of one opportunity against one exact dependency snapshot.

Example:

```text
Opportunity:
INFY / 5m / failed-breakdown reversal / LONG

10:05 decision version:
WATCH
VWAP = 1520
RVOL = 2.1x
Trigger = 1528
Invalidation = 1512

10:20 decision version:
CONFIRMED or still WATCH, based only on what is known at 10:20
```

The old 10:05 decision stays in history. A later decision creates another version.

---

## 3. What the complete TrendForge thinking brain should do

In simple terms:

```text
1. FIND SOMETHING INTERESTING
        |
        v
2. RECORD WHY IT IS INTERESTING
        |
        v
3. CREATE ALL APPLICABLE INDEPENDENT TRADE HYPOTHESES
        |
        v
4. CALCULATE THE FEATURES REQUIRED BY EACH STRATEGY
        |
        v
5. ASK WHETHER THE EVIDENCE SUPPORTS EACH HYPOTHESIS
        |
        v
6. APPLY SAFETY / EVENT / TRADABILITY / LIQUIDITY / COST GATES
        |
        v
7. COMPARE ONLY WITH GENUINELY COMPARABLE OPPORTUNITIES
        |
        v
8. OUTPUT A RESEARCH STATE
   CONFIRMED / WATCH / WAIT / REJECT / NO_ENTRY / other explicit state
        |
        v
9. FREEZE THE DECISION VERSION AND ITS EXACT EVIDENCE
        |
        v
10. LATER RECORD WHAT ACTUALLY HAPPENED WITHOUT REWRITING THE DECISION
```

This is deliberately **not** one giant `stock_score.py` and not one universal bullish/bearish score.

---

## 4. Current connected path versus target architecture

At the reviewed architecture checkpoint, the most mature connected route is primarily the NSE cash/EOD, swing-style research path:

```text
Market-data collection
   |
   v
Cash preparation / canonical source evidence
   |
   v
R1 source evidence
   |
   v
R2 attention
   |
   v
R3 evidence adaptation
   |
   v
R4 identity
   |
   v
R14 corporate-action treatment
   |
   v
R5 daily market structure
   |
   v
S3 discovery
   |
   v
S4 structure
   |
   v
S5 enrichment
   |
   v
S6 evidence-family resolution
   |
   v
S7 research/safety gates
   |
   v
S8 frozen/published research decision
   |
   v
R16 historical outcome evaluation
   |
   v
R18 model/research governance
```

This means TrendForge is **not starting from zero**.

However, do not infer from existing modules, profiles or source registrations that all intraday and commodity strategy brains are end-to-end complete. The system-brain roadmap explicitly records that the cash/EOD route is currently the most mature, while full independent intraday and commodity strategy paths remain future completion/verification work unless newer runtime evidence says otherwise.

---

## 5. Discovery brain: investigate first, decide direction later

Discovery answers only:

> Which instruments deserve investigation, and why?

Examples:

```text
INFY
- unusual volume
- large negative return
- gap down
- sector weakness

RELIANCE
- breakout attempt
- abnormal turnover

HDFCBANK
- official event or ownership change
```

A discovery fact is **not** a trading direction.

For example:

```text
INFY down 3.2%
```

must not automatically mean:

```text
SHORT
```

It means:

```text
INFY is unusually active/interesting. Route it to all applicable strategies.
```

The same negative move may later support:

```text
bearish continuation
bullish failed-breakdown reversal
mean reversion
WAIT
REJECT
NO_ENTRY
```

This is why TrendForge must keep **discovery attention separate from strategy direction**.

Roadmap ownership: **TF-11 — Multi-reason admission and neutral attention**.

---

## 6. Opportunity identity: allow several ideas for one instrument

Roadmap ownership: **TF-10 — Stable opportunity and episode identity**.

TrendForge must carry stable identity for:

```text
instrument/contract
strategy
holding horizon
timeframe
direction
setup episode
opportunity ID
decision version
```

Without this identity, a new INFY result can accidentally replace another independent INFY opportunity.

Example:

```text
INFY
 |
 +-- 5m continuation / SHORT
 |
 +-- 5m reversal / LONG
 |
 +-- daily continuation / LONG
 |
 +-- event strategy / WAIT
```

All four must be allowed to coexist.

---

## 7. Strategy router: send one instrument to the right specialists

Roadmap ownership: **TF-13 — Executable profile bindings**.

The router asks:

> Which strategy evaluators are applicable to this instrument and this situation?

Conceptually:

```text
                    INFY
                     |
        +------------+-------------+
        |            |             |
        v            v             v
  Intraday       Reversal        Swing
 continuation    specialist      specialist
        |            |             |
        +------------+-------------+
                     |
          independent opportunities
```

Every executable strategy/profile must explicitly declare:

- evaluator,
- required features,
- optional inputs,
- prohibited inputs,
- relative-strength contract,
- safety/gate policy,
- comparable ranking group,
- publication path.

A profile declaration alone is not proof of a complete runtime strategy path.

---

## 8. Shared calculation brain: reuse functions without mixing meanings

Roadmap ownership: **TF-12 — Versioned feature reuse**.

TrendForge should reuse validated calculations where appropriate, but the result identity must include its semantics.

For example, ATR can be calculated with the same function on both 5-minute and daily bars, but these are not the same feature result:

```text
ATR / INFY / 5m / session-specific inputs
ATR / INFY / daily / adjusted daily inputs
```

Likewise:

```text
VWAP
RVOL
relative strength
structure
volatility
OI
liquidity
```

must preserve timeframe, parameters, session, source vintage, cutoff and adjustment policy.

Do not mix an intraday feature value into a swing opportunity just because the function name matches.

---

## 9. Equity swing brain

Roadmap ownership: **TF-14 — Equity swing baseline first**.

This is planned first because the current cash/EOD path is closest to a complete implementation.

Example:

```text
INFY daily swing-continuation opportunity

Adjusted daily trend       PASS
Daily structure            PASS
Daily participation        PASS
Strategy-specific RS       PASS
Corporate-action lineage   PASS
Event clearance            PASS
Tradability                PASS
Trigger                     1535
Invalidation                1490
Expected reward/cost       acceptable
```

Possible decision:

```text
Instrument: INFY
Strategy: equity swing continuation
Direction: LONG
State: WATCH
Reason: trigger not yet reached
```

Later, if valid new evidence arrives:

```text
price closes above trigger
participation still valid
event/tradability gates still valid
```

TrendForge may create a **new immutable decision version**.

It must never rewrite the earlier WATCH record.

---

## 10. Equity intraday continuation brain

Roadmap ownership: **TF-15 — Equity intraday continuation**.

Intraday continuation needs different evidence and timing rules from daily swing.

Example:

```text
INFY / 5m / bearish continuation / SHORT

Closed 5m bars valid?        YES
Below session VWAP?          YES
Same-time RVOL elevated?     YES
Current liquidity valid?     YES
Sector weak?                 YES
Index regime supportive?     YES
Breakdown confirmed?         YES
Invalidation known?          YES
Costs reasonable?            YES
```

The strategy can then produce its own state:

```text
WATCH
CONFIRMED
WAIT
REJECT
NO_ENTRY
```

Intraday continuation must explicitly define:

- closed-bar rules,
- session VWAP,
- same-time relative volume,
- current spread/liquidity,
- sector/index context,
- exact entry-timing assumptions,
- trigger and invalidation.

A daily swing score or monthly ownership fact cannot substitute for the intraday trigger.

---

## 11. Reversal brain

Roadmap ownership: **TF-16 — Reversal strategies**.

Reversal must be evaluated independently from continuation.

Do **not** implement reversal as:

```text
continuation score * -1
```

Example:

```text
selloff
  |
  v
breakdown attempt
  |
  v
failed acceptance below support
  |
  v
buyers absorb selling
  |
  v
closed reclaim / reversal confirmation
  |
  v
possible LONG reversal opportunity
```

The same INFY can simultaneously contain:

```text
Opportunity A
INFY / 5m / bearish continuation / SHORT
Evidence: weakening

Opportunity B
INFY / 5m / failed-breakdown reversal / LONG
Evidence: strengthening
```

One opportunity must not delete or reverse the other.

---

## 12. Event and ownership brain

Roadmap ownership: **TF-17 — Event and ownership opportunity strategy**.

Event/ownership research must use actual event and actor identity rather than market-wide context as proof of a symbol-specific claim.

Potential required evidence includes:

```text
event identity
publication/availability time
actor identity
reported holdings quantity change
corporate-action-adjusted comparability
post-event price acceptance
```

Example distinction:

```text
FII market-wide net buying
```

is useful market context but does **not** prove:

```text
A named FII bought INFY
```

unless a source that actually supports that actor/instrument claim is retained.

---

## 13. Commodity brain

Roadmap ownership: **TF-18 — Commodity strategies**.

Commodity strategies must be contract-aware and cannot simply reuse an NSE equity score.

For example:

```text
MCX GOLD OCT FUTURE
```

requires the actual tradable contract identity, not only the word `GOLD`.

Potential inputs include:

```text
exact contract
expiry
tender/delivery restrictions
tick size
lot size
spread/liquidity
local price structure
local volume
open interest
session
rollover state
currency context
relevant slow fundamental/context releases
```

### Commodity intraday

Example:

```text
GOLD Oct / 5m / continuation / LONG
```

may depend strongly on:

```text
local closed bars
local volume/OI
spread/liquidity
session state
contract eligibility
```

Slow macro/fundamental releases may be context, not an intraday trigger unless the strategy explicitly requires them.

### Commodity swing

Example:

```text
CRUDEOIL / daily / swing continuation
```

may additionally depend on:

```text
contract-aware daily structure
rollover treatment
USD/currency context
inventory data such as relevant official releases
positioning data
supply/demand context
publication vintages
expiry/roll restrictions
```

### No universal commodity score

Do not do:

```text
GOLD score = 84
CRUDE score = 82
NATGAS score = 80
COPPER score = 79
```

and assume the same feature meaning or strategy policy applies to all of them.

Gold, crude oil, natural gas, copper and agricultural contracts have different drivers, calendars and risk/roll behavior. They must have strategy/profile-specific evidence contracts.

---

## 14. Safety, tradability and cost are separate from direction

The strategy brain can form a directional hypothesis, but qualification requires independent checks.

Conceptually:

```text
strategy evidence
      |
      v
possible direction/setup
      |
      v
EVENT CLEARANCE
TRADABILITY
LIQUIDITY
CONTRACT ELIGIBILITY
FRESHNESS
COST / SLIPPAGE / CHARGES
      |
      v
qualified research state
```

A good-looking setup can still become:

```text
WAIT
REJECT
NO_ENTRY
```

because liquidity, event risk, expiry/tender rules, stale data, missing proof or costs make it unsuitable.

Safety gates must not invent direction and strategy direction must not bypass safety gates.

---

## 15. Comparable ranking brain

Roadmap ownership: **TF-19 — Net-cost eligibility and comparable ranking**.

Do not rank unrelated opportunities with one universal score.

Bad design:

```text
INFY 5m reversal        88
GOLD 7-day swing        84
RELIANCE intraday       80

=> INFY is universally best
```

These opportunities have different horizons, risk, market microstructure and cost structures.

Preferred design:

```text
NSE INTRADAY CONTINUATION
1. INFY SHORT
2. SBIN LONG
3. RELIANCE LONG
```

separately from:

```text
NSE SWING CONTINUATION
1. HCLTECH LONG
2. INFY LONG
3. TCS WAIT
```

and separately from:

```text
MCX ENERGY INTRADAY
1. CRUDEOIL SHORT
2. NATGAS WAIT
```

Rank only within an explicitly declared **comparable ranking group**.

Ranking must account for applicable spread, slippage, charges, tick/lot sizing, liquidity/capacity and reward relative to cost/invalidation.

The system must be allowed to return fewer than a requested top-N when too few opportunities qualify.

---

## 16. Immutable decision brain

Roadmap ownership: **TF-21 — Immutable publication**.

After a strategy is evaluated and passes the required publication boundary, TrendForge should freeze:

```text
opportunity ID
instrument/contract
strategy/profile version
timeframe
direction
setup episode
dependency/input digest
data cutoff
decision time
publication time
valid-until/expiry
feature versions
gate-policy versions
missing proof
trigger/invalidation/target plan where applicable
cost assumptions
```

If a dependency changes, create a new decision version.

Never silently rewrite the old decision.

---

## 17. R-HIST is the notebook for the brain

R-HIST protects the historical evidence graph so TrendForge can later reconstruct what the brain actually knew.

Example:

At **10:05**:

```text
INFY / 5m / reversal / LONG
VWAP = 1520
RVOL = 2.1x
Trigger = 1528
Decision = WATCH
```

At **10:45**:

```text
price reaches 1550
target condition eventually occurs
```

Correct history stores these separately:

```text
T1 DECISION
10:05 knowledge and exact evidence
WATCH

T2 OUTCOME
later market path / target result
```

It must never rewrite the 10:05 evidence to make it look as though the system already knew the 10:45 result.

That would create future-data leakage and false model/backtest performance.

This is why historical-retention hardening is a prerequisite for trustworthy ML, outcome learning and strategy evaluation.

Refer to the current R-HIST build documents and `docs/CURRENT_STATE.md` for the live implementation checkpoint; do not infer R-HIST completion from this architecture reference.

---

## 18. Outcome and report-card layer

Roadmap ownership: **TF-23 — Exact outcomes and historical repair**.

For each published opportunity/decision version, append later observations such as:

```text
trigger reached
entry valid
entry never reached
invalidation reached
target hit
stop hit
expired
ambiguous same-bar target/stop
censored
data gap
MFE
MAE
time to trigger
time to target
time to stop
contract-roll issue
```

An outcome is not a replacement decision.

A later source correction is not permission to rewrite the old decision either. Corrections/revisions must remain explicit and traceable.

---

## 19. ML and governance relationship

A model must learn from a frozen point-in-time population, not whatever the database looks like today.

Required conceptual graph:

```text
model version
   |
   v
frozen training/evaluation dataset manifest
   |
   v
exact decisions / outcomes / revisions selected under a PIT cutoff
   |
   v
exact feature/evidence manifests
   |
   v
original market evidence hashes/runs
```

A model binary by itself is insufficient historical proof.

Example:

```text
Decision D100 v1 -> Outcome O1 -> Dataset D7 -> Model M9
```

If a later correction creates:

```text
Outcome O2 -> Dataset D8
```

Model M9 must still reconstruct as having learned from D7/O1 if that is what actually happened.

Do not silently substitute D8/O2 and pretend M9 had future knowledge.

---

## 20. Full future build sequence for the trading brain

The system-brain roadmap remains authoritative for exact dependency ordering. The high-level brain sequence is:

```text
TRUSTWORTHY FOUNDATION
|
+-- reliable/versioned observations
+-- exact availability and revision identity
+-- historical retention / point-in-time memory
+-- safety and publication correctness
        |
        v
COMMON THINKING SKELETON
TF-10 opportunity identity
TF-11 discovery + neutral attention
TF-12 versioned feature reuse/cache
TF-13 executable strategy router/profile bindings
        |
        v
REAL STRATEGY BRAINS
TF-14 equity swing
TF-15 equity intraday continuation
TF-16 reversal
TF-17 event/ownership
TF-18 commodities
        |
        v
TF-19 cost + comparable ranking
        |
        v
TF-20 dependency/time/contract recalculation
        |
        v
TF-21 immutable decisions
        |
        v
TF-22 UI/API/alerts read published opportunity versions
        |
        v
TF-23 exact outcomes
        |
        v
TF-24 whole-selector historical validation
        |
        v
TF-25 real-data / shadow / paper operational acceptance
```

Do not jump directly to TF-14/15/18 merely because strategy logic is more visible or exciting. Earlier correctness, identity, point-in-time, safety and routing dependencies exist to prevent the strategy brain from producing convincing but invalid results.

---

## 21. What future agents must not do

Do **not**:

1. create one universal stock/commodity bullish score;
2. use instrument symbol as the opportunity identity;
3. let one opportunity overwrite another for the same instrument;
4. make discovery direction become strategy direction;
5. treat a large negative move as automatically SHORT;
6. implement reversal as continuation with the sign flipped;
7. use daily/swing evidence as an intraday trigger unless the strategy contract explicitly allows it;
8. use one commodity policy for GOLD, CRUDE, NATGAS, COPPER and agriculture;
9. rank unrelated horizons/markets in one global score table;
10. train ML only on winners or only on entered trades;
11. discard WAIT/REJECT/NO_ENTRY/expired/ambiguous/censored populations;
12. rebuild historical decisions from latest/current/corrected data;
13. let browser reads or UI refresh create new historical decisions;
14. let a model, strategy profile or source correction rewrite earlier decisions;
15. interpret a declared profile or registered source as proof of a runtime-complete strategy;
16. activate broker/live execution merely because the research brain becomes more complete.

---

## 22. Future-agent checklist before changing a strategy

Before editing an intraday, swing, event or commodity strategy, answer:

```text
1. What exact instrument/contract is being evaluated?
2. What is the opportunity ID and setup episode?
3. Which strategy/profile/version owns the direction?
4. Why did discovery admit the instrument?
5. Which inputs are REQUIRED_TO_CALCULATE?
6. Which inputs are REQUIRED_TO_QUALIFY?
7. Which inputs are OPTIONAL_CONTEXT?
8. Which inputs are PROHIBITED for this strategy/condition?
9. Were all inputs actually available at decision time?
10. Are feature semantics/timeframe/session/version correct?
11. What event/tradability/liquidity/contract gates apply?
12. What is the trigger, invalidation and entry-timing assumption?
13. What costs/slippage/tick/lot rules apply?
14. Which comparable ranking group owns this opportunity?
15. What immutable decision version will be published?
16. What exact evidence roots must R-HIST protect?
17. How will later outcomes be recorded without rewriting the decision?
18. What adversarial/backtest/real-data evidence is required before approval?
```

If these questions cannot be answered from code and retained evidence, the strategy is not ready for production acceptance.

---

## 23. Short architecture summary

```text
                 DISCOVERY BRAIN
                       |
                       v
                 STRATEGY ROUTER
          +------------+-------------+
          |            |             |
          v            v             v
      INTRADAY       SWING       COMMODITY
        BRAIN         BRAIN          BRAIN
          |            |             |
          +------------+-------------+
                       |
             independent opportunities
                       |
                       v
             SAFETY + TRADABILITY
             LIQUIDITY + EVENT + COST
                       |
                       v
             COMPARABLE-GROUP RANKING
                       |
                       v
              IMMUTABLE DECISION
                       |
              +--------+---------+
              |                  |
              v                  v
          R-HIST MEMORY       UI / ALERTS
              |
              v
       OUTCOMES / BACKTEST
              |
              v
        ML / GOVERNANCE
```

The central rule remains:

```text
ONE INSTRUMENT
CAN HAVE MANY OPPORTUNITIES
AND EACH OPPORTUNITY
CAN HAVE MANY IMMUTABLE DECISION VERSIONS.
```

That is the intended TrendForge stock-picking and trading-thinking architecture.