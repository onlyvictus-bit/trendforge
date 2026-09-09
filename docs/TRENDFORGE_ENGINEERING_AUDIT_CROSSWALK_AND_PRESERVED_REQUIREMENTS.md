# TrendForge Engineering Audit Crosswalk and Preserved Requirements

**Purpose:** preserve and cross-check the detailed engineering audit that produced the 44 findings and 26 ordered implementation tickets against the repository's current architecture references.

**Status:** documentation/audit reference only. This file does not declare any finding repaired, any strategy live-data-verified, any model approved, any broker/execution path authorized, or any historical test result current.

**Primary architecture authority:** `docs/TRENDFORGE_SYSTEM_BRAIN_AND_IMPLEMENTATION_ROADMAP_2026-09-08.md`

**Plain-English strategy-brain reference:** `docs/TRENDFORGE_TRADING_BRAIN_STRATEGY_ENGINE_REFERENCE.md`

**Current implementation/readiness authority:** `docs/CURRENT_STATE.md` plus current runtime/code/tests on the branch actually being developed.

---

## 1. Why this crosswalk exists

The detailed engineering audit concluded that TrendForge should evolve the existing application rather than be rebuilt into separate download/strategy systems. It produced:

- **44 findings** (`A01` through `A44`),
- **26 ordered implementation tickets** (`TF-00` through `TF-25`),
- source/feature/profile/gate/dependency/file-coverage matrices in the original audit package,
- a stage-by-stage repair order,
- explicit distinction between declarations, fixture/test behavior, runtime-connected behavior and live-data verification.

The repository System Brain already carries the substantive A01-A44 and TF-00-TF-25 architecture/repair requirements. This crosswalk records that verification and preserves a few audit details that are easy to lose when reading only the shorter finding register.

Runtime behavior always wins over this document.

---

## 2. Verification result: what is already present in Git

### 2.1 Core recommendation — PRESENT

The System Brain already says to strengthen/reuse existing contracts and modules rather than interpret the target architecture as a command to rebuild the application.

### 2.2 Three identities — PRESENT

The System Brain and trading-brain reference both preserve:

```text
INSTRUMENT != OPPORTUNITY != DECISION VERSION
```

This is the required basis for independent intraday continuation, reversal, swing, event/ownership and commodity opportunities for the same instrument.

### 2.3 Current connected flow — PRESENT

The repository documents the cash/EOD-centered connected path through collection, R1/R2/R3/R4/R14/R5, S3/S4/S5/S6/S7/S8, R16 and R18, while explicitly refusing to treat declared intraday/commodity profiles as proof of complete runtime strategy paths.

### 2.4 A01-A44 finding register — PRESENT

All finding identifiers `A01` through `A44` are present in the System Brain, including the major audit issues:

- macro collection completeness incorrectly standing in for scoped event clearance,
- S7/S8 state-contract mismatch,
- mandatory restrictions flattened to reason strings,
- order-extension qualification boundary,
- tradability fail-closed defects,
- event-only discovery admission gap,
- positive-return attention bias,
- R5 direction constrained by upstream attention direction,
- attention reused as participation evidence strength,
- RS calculated but not connected to the intended final gate,
- declared profiles ahead of executable strategy routing,
- scheduling/calendar gaps,
- historical availability/revision defects,
- conflicting feature semantics,
- repeated canonical reads and percentile performance issue,
- symbol-level opportunity identity collapse,
- read paths that can build/persist,
- retention/reconstruction risk,
- R16 same-day-version rejection,
- proxy-plan outcome evaluation,
- governance/holdout limitations,
- strategy-applicability issues,
- incomplete net cost/liquidity ranking contract,
- UI clock-freshness gap,
- capability/readiness-state distinctions,
- comparable ranking partitions,
- dependency-routing gap,
- duplicate native evidence projection risk,
- legacy feature naming ambiguity,
- last-finite timestamp loss.

### 2.5 Event-clearance target contract — PRESENT

The System Brain already defines a scoped `EventClearanceResult` with instrument/contract/opportunity/profile scope, checked sources/coverage/evidence, assessment/expiry and explicit `CLEAR | BLOCKED | UNKNOWN` semantics.

### 2.6 Multi-reason discovery — PRESENT

The repository already specifies a discovery object that can hold several reasons with provenance/expiry while preserving the rule that discovery admission does not imply trade qualification.

### 2.7 Strategy input classes — PRESENT

The strategy-routing section already requires:

```text
REQUIRED_TO_CALCULATE
REQUIRED_TO_QUALIFY
OPTIONAL_CONTEXT
PROHIBITED_FOR_THIS_CONDITION
```

and applies them separately to equity intraday continuation, reversal, swing, event/ownership, commodity intraday and commodity swing.

### 2.8 Feature/cache semantics — PRESENT

The System Brain already preserves separate identities for timeframe/session/formula/version/input vintage/adjustment policy and defines decoded-source, feature, cross-sectional, strategy-evaluation and published-decision cache layers.

### 2.9 Nine dependency classes — PRESENT

All nine audit dependency classes are present:

```text
INSTRUMENT_LOCAL
SECTOR_WIDE
INDEX_WIDE
UNIVERSE_WIDE
STRATEGY_WIDE
MARKET_WIDE
TIME_DRIVEN
SOURCE_DRIVEN
CONTRACT_DRIVEN
```

The examples also preserve cross-sectional invalidation, time-only expiry and contract-expiry/tender-window invalidation.

### 2.10 Immutable publication/outcomes — PRESENT

The repository already requires immutable decision versions, atomic current pointers/publication, separate source/data/decision/publication/browser times and append-only later outcomes rather than historical rewrite.

### 2.11 Whole-selector backtest validity — PRESENT

The System Brain already requires testing the full historical selector:

```text
historical source availability
-> discovery admission
-> strategy routing
-> qualification
-> ranking
-> execution assumptions
-> outcome
```

and explicitly covers lookahead, revised-data leakage, source-availability leakage, corporate-action/roll leakage, same-bar ambiguity, survivorship/universe/selection bias, costs/slippage and repeated-search overfitting.

### 2.12 Exact TF-00 -> TF-25 implementation order — PRESENT

All 26 tickets are already preserved in dependency order:

```text
TF-00..05  trustworthy decision contract
TF-06..09  observation/source identity, revision and scheduling
TF-10..13  opportunity identity, neutral discovery, feature semantics, strategy routing
TF-14..19  swing, intraday, reversal, event/ownership, commodity, cost/ranking
TF-20..23  dependency updates, immutable publication, UI/alerts, exact outcomes
TF-24..25  whole-selector research and real-data operational acceptance
```

The existing phase gates must remain authoritative. Later strategy work must not bypass earlier correctness dependencies merely because the later feature is more visible.

---

## 3. Audit details that must remain explicit

The items below were either compressed in the short A01-A44 register or easy for a future agent to miss. They are preserved here as mandatory investigation points.

### 3.1 Collector/persistence versus screen event-input discrepancy

The audit observed that different assembly callers did not supply equivalent event inputs:

- the screen snapshot path supplied a macro/event snapshot,
- `build_and_persist_current_s8()` did not accept/supply the same event snapshot in the reviewed implementation.

Therefore one path could evaluate the flawed macro collection state while another remained blocked by unknown event clearance.

**Required future behavior:** canonical assembly must receive explicit, equivalent typed gate inputs across collector, persistence, HTTP and CLI adapters. Do not fix this by adding hidden default PASS behavior.

This is part of the `A01/A02/A26` family and the `TF-01/TF-04/TF-05` repair sequence.

### 3.2 R16 exact-plan limitation and missing S8 geometry

The audit observed that R16 could construct proxy hypotheses instead of evaluating every exact published strategy plan, while the reviewed S8 geometry fields were fixed to `None`.

**Required future behavior:** outcome evaluation must bind to the exact immutable published plan/version when one exists, including trigger/invalidation/target geometry and exact evidence known at the decision time. Missing historical geometry must remain explicit; it must not be guessed from later bars or current formulas.

This belongs to `A32`, TF-21/TF-23 and the current R-HIST point-in-time retention work.

### 3.3 Multiple legitimate same-day decision versions

The audit reproduced R16 logic that could reject differing same-day S8 payloads as conflicts.

**Required future behavior:** a trading date is not a decision identity. Intraday and repeated assessments require several immutable decision versions on the same date, distinguished by opportunity/version/dependency snapshot.

This belongs to `A31`, TF-10, TF-21 and TF-23.

### 3.4 Availability time must never be guessed earlier

The audit demonstrated a path where the original market object's availability timestamp could be dropped and a conventional earlier time inferred downstream.

**Required future behavior:** source publication/availability/receipt time must be retained whenever required for point-in-time validity. If historical availability cannot be proven, fail closed/mark unknown rather than assign an earlier timestamp.

This belongs to `A18`, TF-06 and all PIT/backtest/model-dataset work.

### 3.5 Attention is both queue priority and evidence in the reviewed path

The audit specifically corrected the simplistic statement that attention affects only investigation order. In the reviewed code, `attention_priority` also fed a participation claim's `strength_before_caps`.

**Required future behavior:** discovery/attention priority must not silently become strategy evidence. Participation evidence requires its own explicit feature/contract and lineage.

This belongs to `A09-A11`, TF-11/TF-12/TF-13.

### 3.6 Snapshot consistency is not freshness or precomputation

The atomic snapshot work gives one consistent read scope, but the audit noted that the request could still perform substantial research/context calculation.

**Required future behavior:** distinguish:

```text
consistent generation
fresh result
precomputed/published result
retention-complete result
```

They are different properties.

This belongs to `A23/A29/A37`, TF-20/TF-21/TF-22.

---

## 4. Preserved stage 0 -> 14 audit crosswalk

This crosswalk is not a second implementation roadmap. It explains where the A-findings sit in the end-to-end trading system.

| Stage | Audit conclusion | Main finding families |
| --- | --- | --- |
| 0 — Configuration/contracts | Good contracts exist, but declaration/runtime authority/publication state can disagree. | A02, A13, A14, A22, A38 |
| 1 — Collection | Cadence declarations do not by themselves prove executable schedules; calendars/acquisition ownership need consolidation. | A15-A17, A35 |
| 2 — Normalization/identity | Preserve current identity/corporate-action work; repair availability, revised vintages, temporal aliases and contract treatment. | A18, A19, A34, A35 |
| 3 — Features | Reuse tested kernels but preserve conflicting formulas, value timestamps, stale semantics and actual consumers. | A20-A25, A43, A44 |
| 4 — Discovery | Canonical admission is constrained by the cash/R2 universe; validated source-only reasons need controlled admission. | A08, A09 |
| 5 — Routing | Profiles do not yet prove independent evaluators/opportunity identities. | A13, A27 |
| 6 — Evidence | Display enrichment is not automatically decision evidence; attention also entered participation evidence in the reviewed path. | A03, A11, A21 |
| 7 — Direction | Upstream direction can constrain structural analysis instead of allowing independent hypotheses. | A09, A10 |
| 8 — Gates | Event semantics, typed propagation, defaults, malformed input handling and strategy applicability require fail-closed repair. | A01-A07, A34 |
| 9 — Costs/liquidity | Existing pieces do not yet prove one net executable opportunity-quality contract. | A04, A36 |
| 10 — Ranking | Rank only comparable opportunities; do not interpret one universal score as cross-strategy quality. | A09, A40 |
| 11 — Publication | Repair state compatibility, opportunity/version identity, dependency hashing and transactional publication. | A02, A26-A30 |
| 12 — UI | Keep provenance/history consistency but add explicit validity/expiry and completed-version reading. | A23, A29, A37, A38 |
| 13 — Outcomes | Track exact setup episodes/plans including no-entry, expiry, ambiguous and censored cases. | A31, A32 |
| 14 — Research validity | Use actual historical availability/versioning and validate the whole selector, not winners/current candidates alone. | A18, A19, A31-A33, A41 |

---

## 5. Historical audit provenance — do not treat as current status

The detailed source audit reported the following historical inventory/verification boundary for the revision it inspected:

- 179 named source keys,
- 387 normalized endpoint entries,
- 40 registered features,
- seven strategy-source profiles,
- 258 HTTP route declarations,
- 54 selected additional numerical outputs,
- a 676-file coverage register,
- 86 selected manually reviewed spans across 35 files supplemented by static extraction/lookups/tests.

Its local test snapshot reported:

```text
backend: 1,493 passed, 17 failed, 2 skipped
coverage: 82.47% statement coverage
frontend: passed
```

The audit attributed 15 backend failures to numerical-engine pin differences and 2 to unavailable PyArrow, and explicitly refused to weaken version guards to make them green.

**These numbers are historical audit evidence only.** They must never replace newer branch-specific CI/runtime evidence in `docs/CURRENT_STATE.md`, `docs/VALIDATION.md`, an active PR, or a later verified checkpoint.

---

## 6. Original audit artifact boundary

The original audit text referenced additional generated deliverables such as an HTML engineering report, an Excel workbook with matrices and a ZIP evidence/reproducibility package.

Those generated artifacts are **not proven present in this Git repository by this crosswalk**. Do not invent Git paths for them and do not claim their matrix contents are repository-backed unless the actual files are later checked in and verified.

The requirements derived from that audit that matter for future implementation are preserved in:

1. `docs/TRENDFORGE_SYSTEM_BRAIN_AND_IMPLEMENTATION_ROADMAP_2026-09-08.md` — authoritative architecture/finding/ticket roadmap.
2. `docs/TRENDFORGE_TRADING_BRAIN_STRATEGY_ENGINE_REFERENCE.md` — plain-English stock-picking/strategy-brain reference.
3. this crosswalk — audit provenance, stage map and details that could be lost by summarization.
4. `docs/CURRENT_STATE.md` — latest concise readiness/capability boundary.

If the original matrix/evidence artifacts are later supplied, verify their hashes/content and add them as historical evidence rather than silently changing the current architecture claims.

---

## 7. Required future-agent reading order

Before changing collection, features, strategy routing, opportunity calculation, ranking, publication, history, ML/model governance or execution boundaries:

```text
1. docs/CURRENT_STATE.md
2. docs/TRENDFORGE_SYSTEM_BRAIN_AND_IMPLEMENTATION_ROADMAP_2026-09-08.md
3. docs/TRENDFORGE_ENGINEERING_AUDIT_CROSSWALK_AND_PRESERVED_REQUIREMENTS.md
4. docs/TRENDFORGE_TRADING_BRAIN_STRATEGY_ENGINE_REFERENCE.md
5. current owning code + current tests + current PR/commit state
```

Then inspect the complete producer -> contract -> consumer -> gate -> publication -> retention/outcome path before editing.

A future agent must not use this historical audit as permission to skip a newer tested dependency stage such as the active R-HIST sequence.

---

## 8. Final preservation rule

The repository must keep these distinctions explicit:

```text
architecture intent
!=
implemented code
!=
tests passed
!=
real data observed
!=
data currently fresh
!=
strategy activated
!=
PIT/model approved
!=
execution authorized
```

Likewise:

```text
INSTRUMENT
!=
OPPORTUNITY
!=
DECISION VERSION
!=
OUTCOME
!=
LATER REVISION
```

These distinctions are foundational to the TrendForge trading brain, R-HIST memory, backtesting validity and future model governance.