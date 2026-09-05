# TrendForge Hybrid Data-to-Decision Plan

Date: 2026-07-17  
Status: DOMAIN DETAIL LIBRARY + HISTORICAL PLAN (not current sprint board)  
Scope: NSE stocks and MCX, intraday and swing, single-user local research system  
Execution boundary: OpenAlgo read-only, shadow, and paper phases must precede any separately approved live execution

## Authority And Dual-File Usage Preamble (Mandatory)

**MANDATORY for humans and AI agents before using this document to implement code.**

| Document | Short name | Path | Authority |
|---|---|---|---|
| **Merge plan** | **File A / MERGE** | `docs/fable/new_merge_PLAN_2026-07-18.md` | **Only build-sequence authority** (R0–R18, Q5-R*, acceptance ceilings, product scope) |
| **This file** | **File B / HYBRID** | `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` | **Detail library**: inventory, formulas, strategy source combinations, ops SM, tradability fields, failure narratives |
| **Discovery Detail Plan** | **Product/UI detail catalog** | `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` | Seven-capability mapping and full fields; **not** a build sequence |
| **Professional mathematics** | **Research math detail** | `docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md` | EV, probability, price-process, volatility, microstructure and formula crosswalk; **not** build/state authority |

### Hard rules

1. **Do not use this file as the current sprint order.** H1–H10 and H1A* are historical / detail map keys. Map them through File A **§25** into R0–R18 / Q5 targets.
2. **Do not full-merge this file into File A.** Keep this text intact so domain recipes are not lost.
3. **Conflict rule:** File A wins on four public states (`WATCH` / `WAIT` / `CONFIRMED` / `REJECT`), research-only scope, no order quantity / OMS / live execution, PK non-authority, and evidence-strength ≠ win probability. Map legacy READY/WAIT_* language in this file to File A states and **reason codes**.
4. **Quantity, INR 1L caps, paper/live OpenAlgo, final_qty formulas** remain **POSTPONE** under File A unless File A is later amended. Do not implement them as active selection product from this file alone.
5. When File A §25 lists a CROSS/GAP row that points here, open the cited section and supply fields, lists, and formulas; then apply File A overrides.
6. Completeness of dual-file mapping: File A §25; audits under `docs/fable/remaining_build/INDEPENDENT_AUDIT_*`.
7. Observed implementation truth: `docs/BUILD_STATUS.md` and `docs/VALIDATION.md` — not this file’s historical “awaiting implementation” status alone.
8. Remaining-build pack: `docs/fable/remaining_build/README.md`. Kimi+GLM guide and CSV live in that folder.
9. The seven-capability product mapping is preserved in
   `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md`, section **Coverage of your
   earlier "minimum 7"** (current snapshot lines 263-273; first mapping row line
   267): intraday F&O ranking, NIFTY/BANKNIFTY analysis, options OI tracking,
   PCR movement, descriptive expiry-range context, swing scanning, and
   delivery/accumulation. File A still selects the work; `M/T/PK` remain detail
   tags only.
10. docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md is a research detail reference selected through File A section 25.22. It cannot remove evidence-based CONFIRMED, replace FUS-009, activate a source, authorize quantity/execution, or expose probability/EV before R16/R18 approval and PIT validation.

### Cross-reference matrix (detail → File A target)

| Domain rule in this file | Primary sections | File A target (see also §25) |
|---|---|---|
| Inventory compiler / defects | §16.4, §18.4 | R0 residual / CROSS-001, CROSS-007 |
| Source keys and 354 disposition | §16.5–16.6, §18 | CROSS-002 |
| Decision jobs J01–J14 | §19.2 | CROSS-003 |
| Strategy source combinations | §16.7 | CROSS-004 / PRF-* |
| Activation backlog | §16.16 | CROSS-005 |
| Maturity ladder | §16.3, §19.1 | CROSS-006 |
| Two-speed lanes | §15.2 | CROSS-010 |
| Trust combinations | §15.4 | CROSS-011 |
| Recovery SM / fallback | §16.12 | CROSS-012 |
| E2E vertical slices | §16.17 | CROSS-013 |
| Legacy scorer quarantine | §16.10, §17.2 P0.6, §19.11 | CROSS-014 / FUS-008 |
| TradabilityRestriction | §17.2 P0.1 | CROSS-015 / FTR-035 |
| Ban vs MWPL; FBIL vs live FX | §19.4–19.5 | CROSS-008, CROSS-009 |
| Event match ambiguity | §19.8 | CROSS-016 |
| Productivity / FOMO / journal | §9–10 | CROSS-017 (research-safe) |
| Confidence vs rank labels | §15.5, §16.9 | CROSS-018 |
| Raw vs adjusted series | §17.2 P0.2 | CROSS-020 |
| OpenAlgo RO / tick integrity | §16.13, §17.3 P1.3 | CROSS-022 / Q5-R7 / R17 |
| PIT / calibration guards | §16.11, §17.6 | CROSS-023 / R16 (no auto live ML) |
| Quantity / circuit stress sizing | §8, §16.14, §17.2 P0.5 | **POSTPONE** (File A) |
| H10 live execution | §16.17 H10 | **Not authorized** by File A |

### Required math (research reference; sizing POSTPONE)

Quality score (claim availability, not win probability):

```text
q_i = authority_i * freshness_i * schema_i * completeness_i
    * scope_match_i * timestamp_integrity_i
```

Unit risk and quantity (File A: **do not emit order quantity** until scope amendment):

```text
realizable_unit_risk = max(
  stop_unit_risk, gap_stress_unit_risk,
  circuit_stress_unit_risk, liquidity_stress_unit_risk
)
final_qty = floor(base_qty * data_quality_cap * regime_cap
  * liquidity_cap * calibration_cap)
```

### Unresolved external gaps

- Fast-lane vs near-real-time latency needs observed OpenAlgo telemetry (File A R17 / Q5-R7).
- Legacy scorer full production call-graph quarantine needs continuous tests (File A FUS-008 / `can_size=false`, `can_create_order_intent=false`).
- Gemini dual-file recheck completeness lives in File A **§25.15** (aliases HYBRID-*/MERGE-H*, CI planned-not-live, Hybrid §§1–19 proof table).

## 1. Objective

Convert TrendForge's source inventory into a point-in-time, fail-closed decision system that answers:

1. Which symbols deserve attention now?
2. Why is the movement occurring?
3. Is independent evidence confirming or contradicting it?
4. What exact evidence is still missing?
5. What event or price condition changes WAIT into READY?
6. Where is the thesis invalidated?
7. What quantity keeps account risk inside a deterministic limit?

The system ranks evidence. It must not describe an uncalibrated score as win probability. Probability may be displayed only after point-in-time outcome calibration proves reliability.

## 2. Current Inventory Baseline

The canonical active source partition at plan creation is:

```text
MASTER_CURRENT                 370
ALL_LINKS_FROM_REPORTS         354
LINKED_SOURCES                 105
NOT_LINKED_SOURCES             231
SUPPRESSED_NOT_LINKED_DUPES     18
```

Invariant: `105 + 231 + 18 = 354`. The workbook reports no canonical-URL overlap between linked and not-linked partitions. Section 16 records a separate source-contract overlap defect hidden by malformed `active_source_keys` serialization; URL-level disjointness must not be described as contract-level disjointness.

`LINKED_SOURCES` means an accepted source contract or persisted evidence path exists. It does not mean the source is fresh, parsed, scanner-ready, independent, production-authoritative, or allowed to unlock READY.

## 3. Governing Principles

1. Cheap deterministic filters run before expensive parsing.
2. Hard vetoes cannot be overridden by confidence, rank, AI, or another source.
3. A hard veto closes executability for the current snapshot; a later fresh snapshot may be evaluated again.
4. NO_TRADE blocks executable READY but does not stop monitoring, persistence, or WAIT analysis.
5. Delayed evidence is labelled delayed and cannot prove live flow.
6. Mirror sources confirm transport or identity but do not create independent votes.
7. Missing, stale, blocked, metadata-only, schema-mismatched, scope-incompatible, or unofficial-only evidence fails closed.
8. Risk sizing is deterministic and runs after evidence and gate decisions.
9. AI may explain an approved deterministic result but cannot change state, quantity, source authority, or gates.
10. Every decision must be reproducible from immutable raw artifacts and content hashes.

## 4. Source Decision Contract

Every canonical source must have one versioned contract:

```text
source_key
canonical_url
source_role
authority
market_scope
symbol_scope
decision_jobs
independence_family
expected_frequency
freshness_policy
parser_status
normalization_status
can_discover
can_score
can_veto
can_unlock_ready
fallback_source
limitations
visible_panel
```

Source roles:

| Role | Permitted use |
| --- | --- |
| OFFICIAL_GATE_SOURCE | May affect READY only when structured, fresh, dated, schema-valid, and scope-compatible |
| OFFICIAL_DELAYED_CONTEXT | May affect regime or swing context; cannot prove live flow |
| LICENSED_OR_BROKER_SOURCE | May support execution checks after entitlement and contract validation |
| SECONDARY_DISCOVERY | May create a lead that must be reconciled to primary evidence |
| REFERENCE_ONLY | Design, taxonomy, parser, or research reference only |
| PROTOTYPE_ONLY | Development and research fallback; never READY authority |
| UNUSABLE_FAIL_CLOSED | Retained for audit but contributes no current evidence |

## 5. Hybrid Processing Pipeline

### Stage 0 - Source Governance and Immutable Landing

Input: all 354 canonical source rows.  
Work: resolve source contract, fetch with bounded retries, archive original bytes, compute SHA-256, record status/content type/size/retrieval time, and reject block pages or wrong content.  
Output: immutable raw artifact plus manifest or explicit fetch failure.  
Reason: no data reaches a parser without provenance and integrity evidence.

### Stage 1 - Universe, Identity, Safety and Adjustment

Sources: instrument masters, symbol/ISIN maps, index constituents, trading calendar, ASM, GSM, F&O ban, contract masters, corporate actions.  
Work: establish point-in-time identity, eligibility, exchange/segment, adjusted-price requirements, contract expiry, and surveillance state.  
Output: eligible, research-visible-but-vetoed, or invalid universe rows.  
Rules: surveillance and ban rows may remain visible for research, but executable derivatives or equity intents are blocked according to policy. Unadjusted split, bonus, merger, dividend, or symbol-change history blocks price-derived READY.

### Stage 2 - Data Quality and Session Gate

Work: validate schema, data date, published time, retrieval time, parser version, expected frequency, market session, contract expiry, and required field completeness.  
Output: STRUCTURED_OK, STRUCTURED_STALE, VALID_EMPTY, WAIT_FETCH_REQUIRED, WAIT_SOURCE_DATE, SCHEMA_MISMATCH, BLOCKED, or BROKEN.  
Rule: valid empty is distinct from fetch or parse failure.

### Stage 3 - Regime, Sector and Commodity Context

Stock context: indices, breadth, India VIX, FII/DII cash, participant OI, sector relative strength, turnover and liquidity regime.  
MCX context: local MCX price/OI plus only relevant drivers, such as CFTC/WGC/SGE/USDINR for gold or EIA/rig counts/USDINR for crude.  
Output: BULL_TRADEABLE, BULL_CAUTIOUS, RANGE, BEAR_TRADEABLE, or NO_TRADE; allowed directions; size-reduction multiplier.  
Rules: participant OI is aggregate regime evidence, not stock-level FII proof. USDA/EIA and other commodity sources apply only to relevant contracts. NO_TRADE blocks READY but does not stop candidate storage.

### Stage 4 - Cheap Candidate Discovery

Sources: pre-open imbalance, RVOL by time of day, most-active value/volume, volume gainers, OI spurts, variation screens, announcement indexes, daily deals and sector leaders/laggards.  
Work: rank abnormal activity against historical and time-of-day baselines, attach lightweight event summaries, and reduce the universe before detailed parsing.  
Output: bounded candidate set with discovery reasons and expiry/recheck times.  
Rule: discovery evidence cannot independently unlock READY.

### Stage 5 - Candidate-Only Cause, Sponsor and Ownership Enrichment

Sources: detailed XBRL/PDF announcements, results, order wins, buybacks, PIT, SAST, regulation 29/31, shareholding, AMFI portfolios, pledges, named bulk/block deals and corporate-action terms.  
Work: parse details only for discovered candidates, identify actors and event types, calculate ownership deltas, pledge risk, supply overhang and deal anchors, and maintain sponsor history.  
Output: cause claims, sponsor claims, deal anchors, supply risks and missing-evidence warnings.  
Rules: AMFI and shareholding are delayed swing evidence. NSDL sector reports are not stock-level FPI proof. ESOPs, gifts and inter-se transfers are not graded like open-market promoter purchases. Time decay is source-specific and configurable, not one universal half-life.

### Stage 6 - Structure, Derivatives and Trap Detection

Price work: real OHLCV, VWAP/AVWAP, ATR, pivots, trend, acceptance/rejection, harmonic lifecycle, spread and slippage.  
Derivative work: stock futures OI, OI quadrant, futures basis, official MWPL, F&O ban, PCR, max pain, IV, Greeks, expiry concentration and pin risk.  
Output: trigger, entry zone, structural invalidation, targets, OI/basis interpretation and trap flags.  
Rules: participant OI does not replace stock-level OI. MWPL is not derived from participant OI. GEX requires chain Greeks, multiplier, spot and expiry; absent verified dealer positioning it must be labelled GEX_PROXY.

### Stage 7 - Evidence Resolution and G00-G14 Gates

Order:

```text
point-in-time validity
-> source/scope/freshness validation
-> source-specific time decay
-> independence-family cap
-> strategy requirement check
-> regime scaling
-> conflict matrix
-> G00-G14 gates
-> block scores
-> canonical state
```

Evidence families: REGIME, CAUSE, SPONSOR, FLOW, STRUCTURE, DERIVATIVES, EXECUTION and RISK. NSE and BSE copies of the same deal remain one family vote. A raw input reused across indicators is not independent confirmation.

Canonical states:

```text
PRIORITY_RADAR
READY
WAIT_DATA
WAIT_TRIGGER
WAIT_PULLBACK
WAIT_EVENT
WAIT_FOMO
WAIT_OI_UNRELIABLE
WAIT_BASIS_CONFLICT
WAIT_SUPPLY_OVERHANG
WAIT_EMOTIONAL
REJECT
NO_TRADE
LOCKED_NO_TRADE
```

**AMEND-B-002 (2026-07-20):** The states listed above are **historical domain
labels**. The controlling public API vocabulary is `WATCH` / `WAIT` /
`CONFIRMED` / `REJECT` per File A (`new_merge_PLAN`) §10. Labels such as
`WAIT_OI_UNRELIABLE`, `WAIT_DATA`, `READY`, `NO_TRADE` and `LOCKED` map to
**reason codes**, global safety locks, or research CONFIRMED — not extra public
states. See File A STA-005 and §25.16 CONFLICT-001.

### Stage 8 - Deterministic Risk, Guidance and Persistence

Risk order:

```text
structural invalidation
-> ATR/spread/gap sanity guard
-> effective risk per share or lot
-> fixed-fraction account risk
-> regime reduction
-> liquidity/slippage reduction
-> portfolio correlation/exposure reduction
-> final quantity
```

Confidence or evidence rank may reduce quantity but cannot exceed the hard risk cap. Half-Kelly is disabled until a point-in-time, cost-aware, walk-forward outcome sample produces calibrated probabilities and passes promotion thresholds.

Default INR 100,000 account limits:

| Mode | Maximum account risk |
| --- | ---: |
| Probe | INR 250 |
| Normal | INR 500 |
| Exceptional, fully verified | INR 750 |
| Daily soft limit | INR 1,000 |
| Daily hard lock | INR 1,500 |
| Maximum simultaneous positions | 3 |

Averaging down is disabled. Planned multi-tranche entry is allowed only when every tranche, combined stop, maximum quantity and total risk are defined before the first entry.

**AMEND-B-004 (2026-07-20):** Risk sizing formulas and INR tables in this file
(including §16.14) are **domain reference only** for a future separately
authorized milestone. Current File A build scope explicitly excludes position
sizing, order quantity and execution (GOV-002). Do not implement as selection
product from this section alone.

### Stage 9 - OpenAlgo Boundary

Promotion order:

```text
read-only market-data verification
-> shadow intent generation
-> paper execution
-> reconciliation and failure tests
-> separately approved live execution
```

The broker boundary must independently reject stale, non-READY, oversized, duplicated, expired, schema-invalid, emotionally locked or corrupt intents.

## 6. Strategy-Specific Requirements

One universal cause-and-flow rule would discard legitimate strategies. Each profile has explicit mandatory evidence:

| Profile | Mandatory combination |
| --- | --- |
| Intraday continuation | Tradeable regime, sector alignment, RVOL-TOD, liquidity and price acceptance |
| Intraday reversal | Exhaustion, sweep/reclaim, liquidity, defined invalidation and no unresolved event trap |
| Event/PEAD | Verified cause, confirming flow and post-event price acceptance |
| Swing breakout | Daily/weekly structure, sponsor quality and volume quality |
| Swing pullback | Established trend, support acceptance and controlled volatility |
| MCX | Local MCX price/OI, relevant global driver, currency context and delivery/expiry safety |

## 7. Evidence and Guidance Contracts

Every normalized observation becomes an EvidenceClaim:

```text
symbol
asset
timeframe
strategy
job
direction
strength
reliability
source_key
independence_family
data_date
published_at
valid_until
supporting_fields
limitations
can_score
can_veto
can_unlock_ready
raw_artifact_hash
```

Every candidate produces deterministic guidance:

```text
headline
action: ACT | WAIT | AVOID | LOCKED
why_now
supporting_facts
contradicting_facts
missing_evidence
next_trigger
invalidation
recheck_at
expires_at
entry_zone
stop
targets
quantity
maximum_loss
binding_risk_cap
size_explanation
alternative_scenario
source_hashes
```

`detail_score` or evidence rank must be labelled `Evidence strength - not win probability` until calibration is approved.

## 8. Storage Model

Use existing project storage before adding another database engine:

| Data | Store | Reason |
| --- | --- | --- |
| Original response | Immutable ZIP/CSV/JSON/HTML/XLSX | Replay, audit and parser repair |
| Raw manifest | JSON plus registry persistence | Integrity, retrieval and failure evidence |
| OHLCV and rolling history | Parquet | Efficient time-series and ML reads |
| Events and source state | SQLite | Indexed symbol/date/entity queries |
| Evidence claims and gates | SQLite plus typed JSON | Reproducible decisions and API transport |
| Candidate snapshots | SQLite plus immutable JSON payload | State history and exact decision replay |
| Outcome labels | Point-in-time SQLite/Parquet tables | Calibration without future leakage |

DuckDB may be introduced only after profiling demonstrates a material query bottleneck and a migration milestone is separately approved.

## 9. Trader Experience

### Primary Decision Screen

The first screen answers what to watch, why, what must happen next and how much can be risked. It contains:

1. Command bar: mode, session, regime, freshness, account risk, exposure and safety state.
2. Radar queue: symbol, asset, strategy, timeframe, state, evidence rank, why now, age, next trigger, expiry/recheck and change since the previous scan.
3. Selected setup: real chart, direction, market/sector context, strongest support, strongest contradiction, missing proof, trigger and invalidation.
4. Risk/action rail: entry zone, stop, targets, R:R, quantity, maximum loss, binding cap, warnings, recheck time and Evidence Inspector button.

Confirmed and waiting candidates remain visible. Rejected candidates are persisted and available through filters/history without crowding the primary queue.

### Hidden Evidence Inspector

Open as a right-side drawer of approximately 52% desktop width and a full-screen mobile view:

| Tab | Content |
| --- | --- |
| Decision Proof | G00-G14, block scores, supporting, contradicting and missing claims |
| Price and Structure | Candles, VWAP/AVWAP, ATR, levels, harmonic lifecycle and calculations |
| Derivatives | OI quadrant, basis, MWPL, PCR, max pain, IV, Greeks, expiry and trap warnings |
| Events and Ownership | Announcements, PIT, SAST, deals, shareholding, AMFI and pledge history |
| Sources and Lineage | URL, role, parser version, timestamps, hash, raw artifact and freshness |
| Risk and Scenarios | Quantity formula, slippage, correlation, gap stress and alternatives |
| History | Earlier states, changed evidence, journal notes and outcome labels |

Parser controls, manual factor inputs, source operations and raw diagnostics belong in the inspector or an operations view, not on the main decision screen.

## 10. Productivity Requirements

1. Saved scan profiles for each strategy and timeframe.
2. What-changed-since-last-scan summaries.
3. Side-by-side comparison of the top three candidates.
4. Automatic persistence of READY, WAIT, REJECT and NO_TRADE.
5. Grouped source failures instead of repeated per-symbol noise.
6. Candidate expiry and automatic FOMO downgrade.
7. Incremental candidate enrichment rather than full-universe expensive parsing.
8. One-click journal snapshot containing exact evidence hashes.
9. Daily review of false READY, useful WAIT, rejected losers and missed winners.
10. Search by symbol, state, setup, source, event or blocker.

## 11. Versioned API and Persistence Additions

Planned APIs:

```text
POST /api/v1/scans
GET  /api/v1/scans/{run_id}/candidates
GET  /api/v1/candidates/{candidate_id}
GET  /api/v1/candidates/{candidate_id}/evidence
GET  /api/v1/candidates/{candidate_id}/changes
GET  /api/v1/candidates/{candidate_id}/guidance
GET  /api/v1/sources/status
GET  /api/v1/sources/{source_key}/artifacts
POST /api/v1/risk/evaluate
```

Planned tables:

```text
source_decision_contracts
evidence_claims
evidence_conflicts
candidate_gate_results
candidate_block_scores
candidate_guidance
candidate_state_history
risk_evaluations
scan_profile_versions
outcome_labels
```

## 12. Mandatory Failure Tests

1. HTML block page returned with HTTP 200.
2. Successful valid-empty response versus fetch failure.
3. Corrected source artifact with the same data date.
4. Schema change, missing required field or changed units.
5. New unparsed snapshot while an older parse exists.
6. Stale, future-dated or wrong-market evidence.
7. Duplicate NSE/BSE representation of the same event.
8. Participant OI incorrectly attached as stock-level proof.
9. Delayed AMFI/CFTC/NSDL evidence treated as live.
10. MWPL or F&O-ban conflict.
11. Unadjusted corporate action affecting price history.
12. Missing IV/Greeks producing UNKNOWN instead of invented values.
13. GEX proxy presented as verified dealer positioning.
14. Backtest look-ahead or revised data used before publication.
15. Confidence increasing quantity past the hard cap.
16. WAIT, REJECT, stale or emotionally locked intent reaching OpenAlgo.
17. Duplicate or expired broker intent.
18. UI state disagreeing with backend state.

## 13. Implementation Milestones

**AMEND-B-003 (2026-07-20):** H1–H9 / H1A* / H10 below are **superseded for
sprint order** by File A §15 R0–R18 and §24.13 Q5-R0…R7. This section is kept
for dependency context and domain rationale only. Map detail through File A
§25 / §25.16. Do not treat H* as the active task board.

### H1 - Canonical Plan and Traceability

Acceptance: this document is canonical, `present.md` points to it, and no competing copy is created.

### H2 - Source Decision Map

Acceptance: all 354 canonical links have roles, decision jobs, freshness, independence family and gate authority; partitions remain disjoint.

### H3 - Unified Evidence Pipeline

Acceptance: immutable artifacts, strict parser result states, typed claims, lineage and conflict persistence work end to end.

### H4 - Strategy Profiles and Decision Contract

Acceptance: stock intraday, swing, event and MCX profiles have separate mandatory evidence and canonical WAIT reasons.

### H5 - Risk and Guidance Contract

Acceptance: deterministic quantity, hard account limits, candidate expiry and explanation output pass failure tests.

### H6 - Primary Decision Screen

Acceptance: mock chart is replaced by real data; first viewport answers what, why, next trigger, invalidation and risk without source-operation clutter.

### H7 - Evidence Inspector

Acceptance: all decision proof, lineage, calculations, conflicts and history are inspectable without losing radar position.

### H8 - Point-in-Time Outcome Calibration

Acceptance: walk-forward results include costs, slippage, false-READY rate, calibration error and drawdown; uncalibrated rank remains clearly labelled.

### H9 - OpenAlgo Shadow Boundary

Acceptance: read-only and shadow/paper intents are independently validated and no unsafe state reaches live execution.

## 14. Completion Definition

The plan is implemented only when:

1. Every source used in a decision has an immutable, dated artifact and contract.
2. Every candidate is reproducible from saved evidence and hashes.
3. Conflicts and missing evidence produce explicit WAIT/REJECT states.
4. Strategy-specific gates prevent one universal score from authorizing every setup.
5. Quantity never exceeds deterministic account, liquidity, correlation or daily-loss limits.
6. The primary screen gives guidance rather than merely displaying source data.
7. The hidden inspector exposes full proof and lineage.
8. Outcome calibration is point-in-time and cost-aware.
9. OpenAlgo remains behind separately approved promotion gates.

## 15. Fable Audit Findings - 2026-07-18

Audit verdict: `VERIFIED_WITH_MAJOR_GAPS`. The plan is a strong target architecture but was not yet a complete executable production specification. This section records the gaps found by comparison with the current TrendForge backend, official market-data documentation and the existing OpenAlgo boundary.

### 15.1 Confirmed Plan-to-Implementation Mismatches

| Priority | Finding | Current evidence | Required correction |
| --- | --- | --- | --- |
| Critical | Live intraday authority is absent | `docs/BUILD_STATUS.md` records no legal live NSE/MCX intraday feed and no configured OpenAlgo session | Keep intraday execution research-only until a licensed or broker entitlement is verified end to end |
| Critical | Planned evidence families exceed current engine model | `causal_engine.py` currently scores CAUSE, SPONSOR, STRUCTURE and FLOW only | Version the model before adding REGIME, DERIVATIVES, EXECUTION and RISK as first-class families |
| Critical | Planned states do not match current state enum | Current code uses `WAIT_DATA_WEAK`, `WAIT_MTF_CONFLICT`, `SHORT_WATCH` and other existing labels | Publish one canonical state contract plus explicit backward-compatible migration mapping |
| Critical | Independence rule is weaker than required | Current engine applies a cross-layer shared-input penalty; it does not cap a full source/event family | Add event identity and independence-family aggregation before score calculation |
| High | Current source scheduler is fixed-interval | `source_scheduler.py` is a single thread with one interval and no per-source policy | Implement source-specific schedules, bounded queues, source health and recovery state |
| High | Evidence model lacks event-time/revision semantics | Current causal input has source date and observed time but no published time, receive time, revision or valid interval | Add event-time watermarks, revisions and recomputation rules |
| High | Derivative plan can overstate certainty | OI, PCR and option chain alone do not reveal dealer positioning | Require full validated inputs for Greeks; label dealer/GEX interpretation `GEX_PROXY` |
| High | Risk plan omits exchange mechanics | Current risk plan does not yet specify lot, tick, freeze quantity, margin, band, delivery or fill behaviour | Add instrument and broker preflight checks before paper or live order routes |
| High | Probability promotion is underspecified | No label, sample, calibration or drift standard is defined | Add point-in-time outcome and calibration specification before probability is displayed |

### 15.2 Real-Time Reliability Contract

The scanner must use a two-speed architecture. Fast data controls triggers and execution quality; slower evidence controls context, cause, sponsorship and safety.

| Lane | Inputs | Cadence | Decision authority |
| --- | --- | --- | --- |
| Fast lane | Licensed/broker candles, quotes, depth, option chain and derivatives | Tick to one minute according to entitlement | Trigger, stop, spread, liquidity and immediate invalidation |
| Near-real-time lane | Permitted NSE/BSE public activity endpoints and pre-open data | Source-specific bounded cadence | Discovery or context only unless separately contracted as gate authority |
| EOD lane | Bhavcopies, delivery, corporate-action adjustment and official reports | After publication | Swing structure, historical baseline and reconciliation |
| Slow evidence lane | Filings, shareholding, AMFI, CFTC, NSDL, macro and commodity reports | Event, daily, weekly or monthly | Cause, sponsor or regime context with explicit lag |

Every artifact must retain `event_time`, `data_date`, `published_at`, `received_at`, `revision_id`, `valid_from`, `valid_until`, `schema_version`, `parser_version`, `artifact_hash` and `source_key`.

Decision rule: a late or corrected artifact may trigger a new candidate evaluation, downgrade an existing candidate or explain a historical result. It must never be inserted into an earlier decision as if it had been available then.

### 15.3 Source Contract Additions

Add these fields to the Section 4 Source Decision Contract:

```text
timezone
publication_calendar
session_dependency
entitlement_required
legal_use_mode
rate_budget
retry_policy
circuit_breaker_policy
content_signature
schema_version
correction_policy
event_identity_fields
fallback_authority
watermark_policy
retention_policy
```

Fallback rule: a fallback may preserve discovery or display availability, but it cannot inherit the gate authority of a missing primary source.

### 15.4 Trust-Producing Combinations

No source combination guarantees a profitable trade. It improves reliability only by adding timely, independent and strategy-relevant information.

| Combination | What it establishes | What it does not establish |
| --- | --- | --- |
| Instrument master + corporate action adjustment + price series | Correct identity and mathematically comparable prices | Direction |
| Regime + breadth + sector relative strength | Market and sector context | Stock-specific institutional buying |
| Verified event + RVOL-TOD + price acceptance | Cause with market participation | Durable sponsorship |
| PIT/SAST/named deal + AVWAP or deal anchor | Actor quality and acceptance/rejection around a reference price | Guaranteed follow-through |
| Cash flow + stock futures OI + basis | Cross-market confirmation | Exact FII/DII ownership |
| Option chain + validated IV/Greeks + expiry concentration | Pin, volatility and expiry risk | Actual dealer inventory direction |
| Local MCX OI + relevant global driver + currency | Commodity thesis consistency | Intraday entry timing |
| Structure + spread + slippage + portfolio exposure | Whether a setup is executable at planned risk | Winning outcome |

### 15.5 Probability, Prediction and Learning Rules

The application must keep these values separate:

```text
Data Confidence   = freshness, authority, completeness and schema quality
Evidence Rank     = relative quality among current candidates
Calibrated P(win) = validated historical probability for the same profile/regime/timeframe
Expected Value    = P(win) * average win - P(loss) * average loss - all costs
```

Prediction promotion requirements:

1. Define labels before training, for example target reached before stop within the strategy horizon.
2. Use point-in-time data availability, corrected-data policy, purged walk-forward splits and embargo.
3. Separate calibration by strategy, timeframe, long/short direction and market regime.
4. Include brokerage, tax, spread, slippage, partial-fill and rejected-order assumptions.
5. Track Brier score, expected calibration error, precision-at-K, coverage, expectancy after costs, drawdown and false-READY rate.
6. Require a conservative lower confidence bound on expectancy above zero; raw hit rate is insufficient.
7. Detect drift and automatically demote stale or degraded models to research-only.

Until these requirements pass, TrendForge may display evidence rank and expected scenario ranges, but not a claimed win probability.

### 15.6 Risk and Execution Additions

Before paper or live OpenAlgo handoff, evaluate:

```text
tick size
lot size
freeze quantity
available margin and product rules
price bands and auction state
short-sale and delivery restrictions
physical-delivery or expiry restrictions
estimated spread, impact and slippage
partial fill and cancel/replace state
portfolio correlation, sector and gross-notional caps
broker position and order reconciliation
```

Order handling requires an idempotency key, intent expiry, order-state machine, broker reconciliation, kill switch, duplicate suppression, restart recovery and audit trail. Current OpenAlgo work remains read-only. The correct promotion route is read-only verification, shadow intents, OpenAlgo Analyzer or paper mode, reconciliation tests, then separately approved live execution.

### 15.7 Data-Licensing and Compliance Boundary

NSE describes real-time, snapshot and analytics feeds as licensed market-data products and applies usage controls. Public endpoint availability must not be treated as production feed entitlement.

SEBI retail-algorithm requirements and current broker/exchange operational rules must be reviewed immediately before enabling any live order workflow. This plan does not authorize trading or bypass exchange, broker, data-license or regulatory requirements.

### 15.8 Alternatives Evaluated

| Option | Result |
| --- | --- |
| Preserve the plan without changes | Safe documentation, but runtime gaps remain implicit |
| Implement stages directly | Faster initial progress, but state, contract and scheduling conflicts will create rework |
| ML-first predictor | Rejected until point-in-time outcomes, costs and calibration exist |
| Deterministic gates + source-aware runtime + calibrated ranking later | Recommended hybrid |

### 15.9 New H1A Milestone and Revised Build Order

H1A executes before H2.

Acceptance:

1. One versioned state vocabulary is mapped or migrated across causal engine, scanner, API, persistence and frontend.
2. One EvidenceClaim contract includes source/publish/receive/event time, revision, validity, artifact hash, independence family, authority and scope.
3. Source contracts include entitlement, legal-use mode, timezone, publication calendar, rate budget, circuit-breaker policy, correction policy and fallback authority.
4. Inventory counts are generated from the current source inventory snapshot rather than copied as permanent constants.
5. The source scheduler supports per-source cadence, bounded concurrency, jitter, Retry-After, circuit breaker, valid-empty handling and run watermarks.
6. Late data and corrected artifacts can downgrade or recompute a decision without using future information.

```text
H1 canonical plan
-> H1A runtime reliability and contract alignment
-> H2 source decision map
-> H3 unified evidence pipeline
-> H4 strategy profiles and decision contract
-> H5 risk and guidance contract
-> H6 primary decision screen
-> H7 Evidence Inspector
-> H8 point-in-time outcome calibration
-> H9 OpenAlgo shadow boundary
```

The highest-value next correction is H1A. Activating more links before it would make the system wider without making its decisions more trustworthy.

## 16. Full-Inventory Utilization and Decision-Science Upgrade - 2026-07-18

### 16.1 Audit Scope, Evidence and Honest Boundary

This section supersedes any earlier interpretation that a connected URL is automatically usable trading evidence.

The row-level source of truth remains the existing master workbook rather than another Markdown inventory:

```text
D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx
SHA-256: 1F76DAB1C75252AA8185C97F69FC4E6F74B5710918B9D4B3E4A1566D9C646A43

D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.csv
SHA-256: 6108466BD1CCB9DCC1537D11CEB4DFCD688BE4139BB7C5B773D407E22127B3AA
```

Verified inventory shape:

```text
MASTER_CURRENT rows                         370
Unique canonical URL rows                   354
LINKED_SOURCES rows                         105
NOT_LINKED_SOURCES rows                     231
SUPPRESSED_NOT_LINKED_DUPES rows             18
FETCH_EVIDENCE history rows                3680
Exact duplicate URL groups                   16
Rows participating in exact URL duplicates   32
```

All 370 master rows and all 354 canonical URL rows were structurally reconciled. This is not a claim that every remote URL was hammered or live-tested on the same minute. Live verification must respect each publisher's calendar, session controls, rate budget and data terms. The audit combines the complete local row inventory, persisted fetch evidence, current parser/code inspection and focused verification of high-value official contracts.

No plan can guarantee profit, eliminate all faults or be proven future-proof before implementation and continued observation. The objective is narrower and testable: reduce false confidence, detect breakage quickly, prevent invalid evidence from reaching READY, and create calibrated probability only after enough point-in-time outcomes exist.

Personal, local use reduces distribution and multi-user security requirements. It does not waive publisher terms, exchange market-data controls, broker entitlements or rate limits. NSE explicitly governs usage of real-time, snapshot, delayed, EOD, historical and corporate data, and separately offers licensed real-time and snapshot products. Public website access therefore remains research-only unless the applicable use contract says otherwise:

- [NSE Data Sharing and Usage Policy](https://www.nseindia.com/static/market-data/nse-data-policy)
- [NSE Real-Time Data Subscription](https://www.nseindia.com/static/market-data/real-time-data-subscription)
- [NSE Website Disclaimer](https://www.nseindia.com/static/nse-disclaimer)

### 16.2 Executive Verdict

The existing hybrid plan has the correct guarded architecture, but it does not yet use the inventory to its full decision potential.

The principal gaps are:

1. The plan names source families but does not contain an executable exact `source_key -> feature -> strategy -> gate -> UI` map.
2. `LINKED_SOURCES=105` mixes fresh structured evidence with working endpoints, support/referer pages and unverified research routes.
3. Multiple URLs can represent one source contract, one URL can contain multiple contracts, and malformed source-key arrays hide semantic overlap.
4. Current scoring rewards several directionless or correlated observations and is an evidence rank only, not a probability model.
5. Source independence, event availability time, revision handling and strategy-specific mandatory evidence are not yet enforced end to end.
6. The future broker feed is absent, so current public intraday routes cannot honestly become execution authority.
7. MCX local price/OI, expiry mechanics and global commodity context are not yet complete enough for live commodity decisions.

Recommended option: preserve the current guarded foundation and add an inventory compiler, exact decision map, independent evidence-family fusion, point-in-time feature/outcome store and OpenAlgo shadow boundary. A wide generic scraper is not the recommendation.

### 16.3 Correct Source-State Ladder

Every URL and source contract must move through separate, persisted states:

```text
REGISTERED
-> TRANSPORT_OK
-> ARTIFACT_VALID
   -> VALID_EMPTY
   -> PARSER_SCHEMA_OK
      -> NORMALIZED
      -> FRESH_FOR_JOB
      -> DECISION_WIRED
      -> GATE_AUTHORIZED
      -> EXECUTION_AUTHORIZED
```

Definitions:

| State | Required proof |
| --- | --- |
| REGISTERED | Canonical URL, source owner, purpose and role are known |
| TRANSPORT_OK | Bounded request completed with expected HTTP/content behavior |
| ARTIFACT_VALID | Non-block page, non-login page, non-truncated content, hash and raw archive saved |
| VALID_EMPTY | Source contract proves that no rows is a legitimate result for this publication window; it cannot be inferred from an empty body |
| PARSER_SCHEMA_OK | Required columns, types, row invariants and source date passed a versioned contract |
| NORMALIZED | Symbols, instruments, dates, units and event identities map to canonical schemas |
| FRESH_FOR_JOB | Data is fresh for the specific decision job and exchange calendar, not merely recently fetched |
| DECISION_WIRED | A named feature or veto consumes the normalized dataset with tests |
| GATE_AUTHORIZED | Authority and scope permit the evidence to affect READY |
| EXECUTION_AUTHORIZED | Licensed/broker data, account state and reconciliation permit order checks |

Counts must be generated for every state. `CONNECTED` must never be used as a substitute for any later state.

Current caution:

- 75 linked rows are labelled fresh structured.
- 30 linked rows are labelled working screener endpoints, which does not establish source-date freshness, parser completeness or gate authority.
- Four linked routes are unverified research contracts.
- Three linked routes are support/referer URLs rather than independent evidence.

The dashboard and documentation must report these categories separately.

### 16.4 Inventory Defects That Must Be Fixed Before Broad Activation

The H1A milestone is split. New H1A0 inventory compilation and cleanup runs before runtime reliability work.

Observed defects:

1. Sixteen exact URL duplicate groups involve 32 rows.
2. Thirty-three raw `url` cells contain a source-key prefix rather than a plain canonical URL.
3. Two cells contain two URLs joined by `|` and must become two endpoint rows under one source family.
4. Four non-HTTP sentinels currently occupy URL fields: `lme_warehouse_stocks:no_snapshot`, `mca_master_data:no_snapshot`, `mcx_delivery_reports:no_snapshot`, and `rbi_fpi_monitoring:no_snapshot`.
5. Sixty-three master rows lack normalized `purpose_jobs`.
6. Some newer rows put free-form prose into `purpose_jobs`; the field needs a controlled taxonomy plus a separate notes field.
7. Five of six test/example placeholders are queued as not-linked candidates and must be quarantined from activation metrics.
8. Several fragments are documents or examples rather than market-data contracts, including an FAQ block-deal ZIP, service-provider lists, circular ZIPs, fake-trading-app reports and example report URLs.
9. `active_source_keys` contains JSON-array text in some rows, including `['amfi_monthly_portfolio']`, `['msei_fii_dii']`, and paired F&O keys. A pipe-only splitter cannot normalize these.
10. `nse_fo_bhavcopy` and `nse_participant_oi` therefore appear semantically in both linked and not-linked sets even though URL-level overlap is zero.
11. The gate layer references `nse_mwpl_ban`, but the current exact active-key lists do not contain a clean canonical MWPL/F&O-ban contract. This is a registry-to-runtime mismatch.

Required compiler behavior:

```text
parse plain string, JSON array and pipe-delimited key cells
extract and canonicalize every HTTP(S) URL
split compound endpoint cells without losing family lineage
move sentinels into source_status/reason fields
separate page URL, API URL, download URL and referer URL
generate normalized endpoint_id and source_contract_id
dedupe exact URL, resolved endpoint and semantic source contract separately
quarantine examples, support pages, reference pages and local routes
validate controlled purpose_jobs and independence_family values
produce stage counts directly from rows
write a migration manifest; never silently delete an inventory row
```

H1A0 acceptance:

1. Zero malformed source-key cells.
2. Zero compound URL cells.
3. Zero sentinel values in canonical URL fields.
4. Zero unexplained source-contract overlap.
5. Every canonical row has a role, purpose, safe use, blocked use and next action.
6. `nse_mwpl_ban` is added or the runtime gate is remapped to the actual authoritative contract.

### 16.5 How All 354 Canonical URLs Are Used Without Polluting Decisions

Using every link does not mean fetching every link every minute or allowing every link to score a stock. It means each row receives an explicit operational disposition.

| Canonical role | Rows | Correct utilization |
| --- | ---: | --- |
| OFFICIAL_OR_PRIMARY | 222 | Candidate for fetch/parser contracts; gate use only after authority, schema, date, scope and freshness pass |
| CONFIG_ENDPOINT_CONTRACT | 47 | Executable endpoint recipe; evidence exists only after a valid artifact and parse |
| UNVERIFIED_RESEARCH | 17 | Shadow collection and comparison; cannot unlock READY |
| CONFIG_SUPPORT_URL | 10 | Session seed, referer, download discovery or documentation; never an independent vote |
| REFERENCE_ONLY | 24 | Feature taxonomy, UX, parser research or methodology; no copied signal or data authority |
| SECONDARY_DISCOVERY | 20 | Lead generation only; reconcile to an official or licensed source |
| TEST_OR_PLACEHOLDER | 6 | Offline fixtures and negative tests; excluded from coverage and source-health production metrics |
| OPEN_SOURCE_REFERENCE | 5 | Review algorithms, tests and adapters; do not assume code license or data authority transfers |
| LOCAL_APPLICATION | 2 | Local integration/health endpoints; not market evidence |
| LICENSED_CANDIDATE | 1 | Future broker/vendor contract; execution authority only after entitlement validation |

This table accounts for all 354 unique canonical rows. The 370-row master additionally preserves duplicate and fragment history for auditability.

### 16.6 Exact Source-Contract Coverage

Many of the 354 URLs are pages, downloads, referers, fragments or alternate endpoints for the same logical source. The current normalized contract view contains 69 linked keys and 43 not-linked keys, with two semantic duplicates caused by malformed serialization.

Current linked contract keys, retained exactly for H2 mapping:

```text
amfi_scheme_wise
bse_bhavcopy_eod
bse_block_deals
bse_bulk_deals
bse_corporate_announcements
bse_order_win_announcements
bse_pledge_data
bse_sast
cftc_cot
cftc_disagg_futures_only
cftc_legacy_futures_only
cftc_tff_futures_only
eia_weekly_petroleum_stocks
fred_broad_dollar_index
fred_real_yield_10y
mcx_bhavcopy
nsdl_fpi_daily
nsdl_fpi_daily_reportdetail
nsdl_fpi_fortnightly
nse_all_indices
nse_announcements
nse_asm
nse_bhavcopy_eod
nse_block_deal
nse_block_deal_live
nse_corporate_filings_actions
nse_daily_buyback
nse_equity_universe
nse_fii_dii
nse_financial_results
nse_fo_bhavcopy
nse_gsm
nse_large_deals
nse_large_deals_snapshot
nse_live_equity_derivatives
nse_live_equity_derivatives_banknifty_fut
nse_live_equity_derivatives_banknifty_opt
nse_live_equity_derivatives_index_fut
nse_live_equity_derivatives_index_opt
nse_live_equity_derivatives_stock_fut
nse_live_equity_derivatives_stock_opt
nse_market_turnover
nse_market_variations
nse_most_active_underlying
nse_most_active_value
nse_most_active_volume
nse_nifty500_constituents
nse_oi_spurts
nse_oi_spurts_contracts
nse_option_chain
nse_option_chain_equity
nse_participant_oi
nse_pit_current
nse_pit_symbol
nse_pledge_data
nse_preopen_fo
nse_regulation_29
nse_regulation_31
nse_sector_constituents
nse_shareholding_pattern
nse_slb
nse_trading_calendar
nse_variations_gainers
nse_variations_loosers
nse_volume_gainers
sge_benchmark_gold
wgc_gold_etf_flows
wgc_gold_etf_holdings
world_gold_council_oi
```

Current not-linked contract keys, retained exactly for H2/H2A disposition:

```text
amfi_monthly_portfolio
amfi_nav
baker_hughes_na_rig_count
bse_buyback_tender
bse_insider_trading
bse_scrip_header
bse_sensex
bse_takeover_open_offer
bse_xbrl_announcements
china_nbs_indicator
des_crop_estimates
dgcis_trade_data
equitymaster_fii_buys_reference
imd_rainfall_timeseries
lme_warehouse_stocks
mca_company_master_data
mca_master_data
mcx_circulars
mcx_delivery_reports
mcx_future_prices
mcx_market_watch
mcx_option_chain
mcx_trading_holidays
mfapi_history
mfapi_schemes
msei_fii_dii
nse_bulk_deal_symbol
nse_index_banknifty
nse_index_midcap100
nse_index_nifty50
nse_index_smallcap100
nse_pit_annual
nse_preopen_nifty
nse_preopen_sme
nse_quote_derivative
nse_quote_equity
nse_quote_equity_trade_info
nse_xbrl_taxonomy
rbi_fpi_monitoring
shfe_weekly_stock
usda_wasde
nse_fo_bhavcopy
nse_participant_oi
```

The last two not-linked entries are not new contracts. H1A0 must merge their malformed representations into their linked contract records while retaining row lineage.

H2 must generate a machine-readable map for every normalized contract with:

```text
source_key
endpoint_ids
artifact_kind
parser_id and parser_version
dataset_id
decision_jobs
feature_ids
strategy_profiles
mandatory_for
confirmation_for
veto_for
independence_family
authority_cap
freshness_by_job
fallback_chain
primary_panel_field
inspector_sections
tests
```


### 16.7 Decision Families and Source Combination Logic

Source count is not confidence. Each strategy uses a small set of mandatory families, optional confirmations and hard vetoes.

#### Universal Safety and Identity

Mandatory before any stock decision:

```text
nse_equity_universe or authoritative instrument master
nse_trading_calendar
nse_bhavcopy_eod or licensed/broker price history
nse_corporate_filings_actions plus split/dividend/bonus adjustment state
nse_asm
nse_gsm
nse_mwpl_ban for derivative-dependent setups
```

Failure behavior:

- Unknown symbol/series/lot/expiry: `WAIT_INSTRUMENT_IDENTITY`.
- Unadjusted corporate action: `WAIT_PRICE_ADJUSTMENT`.
- ASM/GSM restriction conflict: risk downgrade or veto according to configured rule.
- F&O ban: derivative-dependent entry is blocked, not merely penalized.

#### Intraday Continuation

Mandatory families:

```text
licensed/OpenAlgo quote and intraday candles after integration
market session and fresh timestamp
liquidity/spread/price-band checks
sector and index regime
volume relative to the same time of day
```

Candidate discovery:

```text
nse_preopen_fo
nse_volume_gainers
nse_most_active_volume
nse_most_active_value
nse_sector_constituents
nse_all_indices
```

Independent confirmation:

```text
nse_oi_spurts_contracts or nse_fo_bhavcopy-derived OI family
nse_quote_equity_trade_info or broker delivery/trade-quality family
material event family from NSE/BSE announcements
```

Vetoes:

```text
wide spread, thin depth, stale quote, price-band proximity
event ambiguity or pending result
F&O ban for derivative-dependent setup
sector/index contradiction beyond tested tolerance
```

#### Intraday Reversal

Require exhaustion, not merely a large move:

```text
failed price acceptance beyond a level
volume climax followed by declining participation
OI transition consistent with covering/unwinding
sector/index divergence
reclaimed VWAP or auction level
defined stop beyond the failed extreme
```

Pre-open gap magnitude alone is never bullish. Direction, auction imbalance, IEP stability, opening acceptance and gap type must be preserved.

#### Swing Catalyst Continuation and PEAD Research

Mandatory:

```text
point-in-time NSE/BSE announcement or XBRL event
event materiality and direction
adjusted EOD candles and liquidity
event publication timestamp versus next tradable session
```

Confirmation:

```text
nse_financial_results
bse_order_win_announcements
nse_daily_buyback or bse_buyback_tender
nse_pit_current, nse_pit_symbol, bse_insider_trading
nse_shareholding_pattern, amfi_monthly_portfolio, nsdl_fpi sources
nse_large_deals and BSE deal sources
```

An event's existence is not positive. Earnings require surprise, guidance, quality and market response. An order win requires order value relative to revenue/order book, counterparty, execution period and cancellation risk. Deals require buyer/seller direction, entity classification, price and later acceptance.

#### Swing Accumulation or Distribution

Require multiple dates and independent ownership families:

```text
delivery or volume anomaly versus symbol history
deal direction and deal-price acceptance
promoter/PIT/SAST changes
pledge creation/release/invocation
quarterly shareholding and delayed AMFI/NSDL sponsor evidence
price structure and sector relative strength
```

Participant OI and aggregate FII/DII flows provide regime context. They must not be described as stock-level institutional buying.

#### MCX Gold and Silver

Mandatory local family:

```text
mcx_bhavcopy or future OpenAlgo MCX quote/candle/OI contract
contract identity, expiry, lot and delivery/expiry rules
USD/INR or validated currency context
```

Independent global context:

```text
cftc_cot and its disaggregated reports
fred_real_yield_10y
fred_broad_dollar_index
wgc_gold_etf_holdings
wgc_gold_etf_flows
world_gold_council_oi
sge_benchmark_gold
```

CFTC is weekly regime context, not intraday flow. Official CFTC reports generally publish Friday for prior-Tuesday positions, so their availability timestamp and lag must be explicit: [CFTC release schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm).

#### MCX Crude and Energy

```text
mcx local price/OI and contract mechanics
eia_weekly_petroleum_stocks
baker_hughes_na_rig_count
CFTC energy positioning
USD/INR and broad dollar context
```

EIA inventory surprises require the released value, prior value, revision and consensus source if used. The absolute inventory level alone is not a directional signal.

#### MCX Base Metals and Agriculture

Base metals:

```text
lme_warehouse_stocks
shfe_weekly_stock
china_nbs_indicator
DGCI&S trade data
local MCX price/OI and USD/INR
```

Agriculture:

```text
imd_rainfall_timeseries
usda_wasde
des_crop_estimates
DGCI&S trade data
local MCX price/OI, contract seasonality and delivery rules
```

Weather and crop reports are slow causal context. They cannot confirm an intraday trigger without fresh local price/liquidity evidence.

### 16.8 High-Value Derived Feature Catalog

Every feature must state its source family, as-of time, lookback, unit, null behavior and whether it is observed, derived, estimated or proxy.

#### Auction and Opening Features

```text
gap_pct_signed
IEP_change_path
IEP_stability
matched_quantity_zscore
buy_sell_imbalance = (buy_qty - sell_qty) / max(buy_qty + sell_qty, 1)
indicative_to_open_slippage
gap_fill_acceptance
opening_range_acceptance
```

Use multiple snapshots where available. One final pre-open row cannot establish stability.

#### Price, Liquidity and Relative Activity

```text
RVOL_TOD = cumulative_volume_now / median_cumulative_volume_same_minute
trade_value_TOD_zscore
spread_bps
depth_imbalance
turnover_to_free_float
delivery_pct_zscore
close_location_value
sector_relative_return
index_relative_return
breadth_thrust and breadth_divergence
```

Intraday delivery values must be marked provisional when the source does not represent final EOD delivery.

#### Derivatives

```text
price_OI_quadrant
OI_change_zscore
futures_basis_bps
annualized_cost_of_carry
basis_change and basis_curve
near_next_rollover_pct
roll_cost
PCR_OI and PCR_volume by expiry
IV_rank and IV_percentile
put_call_skew
term_structure_slope
OI_wall_persistence
max_pain_context
GEX_PROXY
```

Rules:

1. OI quadrant needs symbol price change and OI change from matching contracts and dates.
2. Basis must be expiry-aware and compared with carry; raw positive basis is not automatically bullish.
3. PCR and max pain are contextual, expiry-specific and unstable near expiry; neither is a standalone signal.
4. `GEX_PROXY` is explicitly not dealer gamma exposure because dealer inventory and side are unknown.
5. Greeks must use validated contract identity, option price, underlying choice, time to expiry, rate and model assumptions.

Future options implementation should first reuse OpenAlgo's service boundary where broker data is available. OpenAlgo documents `/api/v1/multioptiongreeks` using Black-76 and live market inputs: [OpenAlgo MultiOptionGreeks](https://docs.openalgo.in/api-documentation/v1/data-api/multioptiongreeks).

For direct research calculations, the current canonical package is `vollib`; the project must pin and test an adapter rather than add deprecated imports blindly: [vollib repository and migration notes](https://github.com/vollib/py_vollib).

#### Events, Ownership and Sponsor Quality

```text
event_materiality = event_value / trailing_revenue_or_market_cap
event_novelty and duplicate_hash
event_direction with UNKNOWN allowed
order_execution_horizon and counterparty_quality
earnings_surprise and guidance_delta
deal_notional_to_ADTV
deal_price_acceptance after 1D/5D/20D
insider_net_value by role and rolling window
promoter_holding_delta
pledge_level and pledge_event_severity
AMFI holding delta adjusted for split/merger/name changes
FPI/DII context with scope labels
```

Text classification may prioritize review, but the original filing, extracted fields and deterministic rules remain visible. Ambiguous text returns `WAIT_EVENT_PARSE`, not a guessed direction.

### 16.9 Evidence Fusion, Trust and Contradiction Handling

Each EvidenceClaim receives a quality value, not a win probability:

```text
q_i = authority_i
    * freshness_i
    * schema_i
    * completeness_i
    * scope_match_i
    * timestamp_integrity_i
```

Each component is bounded in `[0, 1]`. Any hard failure makes the claim unavailable. Unofficial research sources receive a low authority cap and `can_unlock_ready=false`.

Claims are grouped by independence family:

```text
PRICE_AND_LIQUIDITY
DERIVATIVES_OI
OPTIONS_VOLATILITY
MARKET_AND_SECTOR_REGIME
CORPORATE_EVENT
OWNERSHIP_AND_SPONSOR
SURVEILLANCE_AND_RESTRICTION
MACRO_AND_CURRENCY
COMMODITY_FUNDAMENTALS
BROKER_EXECUTION
```

Rules:

1. Multiple endpoints derived from the same exchange dataset produce one family contribution, not multiple votes.
2. Mirror sources improve transport confidence and cross-check identity but do not double directional weight.
3. The highest-quality claim may represent a family; additional same-family claims add only bounded corroboration.
4. Contradiction is persisted as evidence, not averaged away.
5. Mandatory-family absence forces WAIT regardless of optional confirmations.
6. A hard veto cannot be overcome by a high evidence rank.
7. Delayed context can alter regime priors but cannot prove live stock flow.

Pre-calibration display:

```text
Data Confidence      source quality and mandatory-family coverage
Evidence Rank        relative candidate ordering within one strategy profile
Conflict Level       independent bullish versus bearish family disagreement
Prediction Status    UNCALIBRATED or CALIBRATED
```

No source count, confidence meter or evidence rank is labelled probability.

### 16.10 Replace the Current Heuristic Scorer

**AMEND-B-005 (2026-07-20):** Line references below are as of **2026-07-17**.
Verify against current code before implementation. File A FUS-008 / CROSS-014
controls quarantine (`can_size=false`, `can_create_order_intent=false`).

The present intraday implementation is useful for research ranking but cannot be promoted unchanged.

Observed issues in `backend/trendforge_api/intraday_stock_details.py`:

1. Lines 887-890 add option volume, futures volume, underlying total and most-active total even when they are correlated views of the same activity.
2. Line 893 rewards the absolute pre-open gap in both directions.
3. Lines 894-895 reward any block or bulk deal without buyer/seller direction or price acceptance.
4. Lines 899-900 use static delivery thresholds without symbol/time historical normalization.
5. Lines 901-902 use static PCR thresholds without expiry, regime or historical calibration.
6. Lines 903-904 treat raw basis percentages without carry, expiry or curve context.
7. Line 911 rewards any recent financial result regardless of surprise, quality or price response.
8. Lines 919-931 start at 40 and mix discovery activity, direction and evidence completeness into one bounded score.

`market_activity.py` correctly states `can_unlock_ready=false`, but its fixed volume-spurt and deal thresholds remain discovery heuristics.

Migration:

```text
keep the current score as legacy_discovery_rank_v1
never feed legacy_discovery_rank_v1 into position sizing or READY
emit separate normalized feature values
aggregate once per independence family
apply strategy-profile mandatory gates
persist contradictions and missing evidence
train/calibrate a new model only from point-in-time outcomes
retire the legacy rank after shadow comparison and migration tests
```

### 16.11 Prediction and Data-Science Plan

The way to improve measured win probability is not to add more links to a score. It is to improve labels, point-in-time correctness, independent evidence, calibration and risk-adjusted selection.

#### Point-in-Time Feature Store

Every feature row stores:

```text
symbol and instrument_id
strategy_profile and timeframe
event_time
published_at
received_at
available_at
source_data_date
revision_id
raw_artifact_hash
parser_version
feature_version
value and null_reason
authority and independence_family
```

Backtests may only read rows whose `available_at <= simulated_decision_time`.

#### Label Definition

Define labels separately by strategy, direction and horizon:

```text
target_before_stop
maximum_favorable_excursion
maximum_adverse_excursion
time_to_target_or_stop
net_return_after_all_costs
slippage_and_fill_quality
decision_state_at_entry
```

WAIT, REJECT and no-trade candidates are retained to measure selection bias and false negatives.

#### Validation

```text
purged walk-forward splits
embargo around overlapping labels
symbol/date grouping to reduce leakage
corporate-action-safe prices
revision-aware macro/event data
all brokerage, tax, spread, impact and rejection assumptions
regime/timeframe/direction calibration
bootstrap confidence intervals by trading day
```

Metrics:

```text
Brier score
log loss
expected calibration error
precision and expectancy at K
coverage
false-READY rate
net expectancy
drawdown
turnover and capacity
probability lower confidence bound
```

Probability is displayed only when the relevant strategy has adequate effective sample size and beats a simple base-rate model out of sample. Recommended initial promotion guard:

```text
at least 200 effective closed outcomes for the broad strategy profile
at least 50 local outcomes in a regime/timeframe bucket, using shrinkage to the broad profile
positive net-expectancy lower confidence bound
ECE <= 0.05 or a stricter profile-specific threshold
no material false-READY or drawdown breach in the latest shadow window
```

If these conditions are not met, show `UNCALIBRATED` and an evidence rank only.

#### Model Order

1. Deterministic gates and a regularized logistic baseline.
2. Calibrated tree model only if it improves out-of-sample probability and stability.
3. Champion/challenger shadow comparison.
4. Optional regime model only after its states are stable and interpretable.
5. No LSTM, HMM, ensemble or online learner is mandatory merely to satisfy an architecture checklist.

ML never overrides a veto or source authority.

#### Drift and Learning

Drift detection monitors feature distributions, calibration and outcome residuals. It may demote a model to research-only. It must not silently retrain and promote live decisions.

Potential libraries, each requiring separate dependency/license approval and tests:

| Candidate | Safe intended use | Decision |
| --- | --- | --- |
| [Pandera](https://github.com/unionai-oss/pandera) | Dataframe schema and statistical validation | Recommended candidate for parser contracts |
| [statsmodels RollingOLS](https://www.statsmodels.org/stable/generated/statsmodels.regression.rolling.RollingOLS.html) | Rolling beta and factor exposure | Prefer over hand-rolled rolling regression |
| [River](https://github.com/online-ml/river) | Drift monitoring and research-only online metrics | Optional after labels exist; no automatic live learning |
| [vollib](https://github.com/vollib/py_vollib) | IV and Greeks adapter | Candidate with pinned version and model tests |
| vectorbt | Research backtest acceleration | Do not add by default; current license carries a Commons Clause and project compatibility needs review |

No install is authorized by this plan.


### 16.12 Real-Time Breakage and Recovery Architecture

Each source uses a calendar-aware state machine:

```text
IDLE
FETCH_DUE
FETCHING
TRANSPORT_OK
VALIDATING_ARTIFACT
PARSING
STRUCTURED_FRESH
VALID_EMPTY
STALE
RATE_LIMITED
BLOCKED
SCHEMA_CHANGED
CORRECTION_PENDING
BROKEN
```

Required controls:

1. Per-source cadence, timezone, publication calendar and expected quiet periods.
2. Bounded concurrency by domain and polite minimum intervals.
3. Session/cookie refresh only for permitted public flows.
4. `Retry-After` handling, bounded exponential backoff and circuit breakers.
5. Content-Type, magic-byte, compression, size and block-page checks.
6. SHA-256 raw archive before parse.
7. Schema fingerprint, required fields, row-count range and source-date validation.
8. `VALID_EMPTY` distinct from transport or parser failure.
9. Last valid data remains visible with `data_date`, `received_at`, age and STALE label.
10. Fallback sources inherit their own authority cap; no silent authority upgrade.
11. Late or corrected artifacts create a new revision and recompute affected decisions.
12. Source health cannot by itself create a trade candidate.

Fallback hierarchy:

```text
official/licensed current source
-> official delayed source for context only
-> verified unofficial research fallback with explicit cap
-> cached last-valid artifact marked STALE
-> WAIT_SOURCE
```

No browser automation or alternate mirror is used to evade authentication, CAPTCHA, deliberate access controls or publisher restrictions.

### 16.13 OpenAlgo Integration Boundary

OpenAlgo is planned as a separate local service boundary, not copied into TrendForge. Its project is AGPL-3.0 and provides unified broker APIs, live streaming, option analytics and sandbox/analyzer capabilities: [OpenAlgo repository](https://github.com/marketcalls/openalgo) and [Analyzer architecture](https://docs.openalgo.in/developers/design-documentation/configuration).

Required provider interface:

```text
MarketDataProvider
  get_instruments()
  get_quote()
  get_history()
  stream_quotes()
  get_option_chain()
  get_multi_option_greeks()
  get_positions()
  get_orders()
  get_funds()

ExecutionProvider
  create_shadow_intent()
  place_order()            disabled until separate approval
  modify_order()           disabled until separate approval
  cancel_order()           disabled until separate approval
  reconcile()
```

Promotion sequence:

```text
read-only symbol and data-contract verification
-> historical parity and timestamp tests
-> live read-only shadow feed
-> shadow intents without orders
-> OpenAlgo Analyzer/sandbox
-> restart, duplicate, partial-fill and reconciliation tests
-> separately approved paper or broker sandbox
-> separately approved live execution
```

TrendForge must retain its own decision snapshot and idempotent intent. Broker/order state remains authoritative for execution. No broker credentials are stored in source inventory or sent to external AI.

### 16.14 Risk and Quantity Logic for the INR 1 Lakh Account

**AMEND-B-004 (applies here):** Domain reference only under current File A scope.
See note under §8 Stage 8 / account limits.

Confidence does not directly determine quantity. Quantity is bounded first by loss at the invalidation level:

```text
risk_budget = min(
    configured_trade_risk,
    remaining_daily_loss_budget,
    remaining_portfolio_heat,
    sector_and_correlation_budget
)

unit_risk = abs(entry - stop) + expected_slippage + fees_per_unit
base_qty = floor(risk_budget / unit_risk)
final_qty = floor(base_qty * data_quality_cap * regime_cap * liquidity_cap * calibration_cap)
```

Rules:

1. Missing stop, invalid price, stale quote or non-positive unit risk means zero quantity.
2. A higher evidence rank may never expand quantity beyond deterministic risk and liquidity caps.
3. Uncalibrated setups use a conservative calibration cap.
4. Correlated positions share one portfolio heat budget.
5. Gap risk, earnings, expiry, physical delivery, price bands and MCX lot risk can reduce quantity or veto.
6. Averaging down is disabled by default. Any scaling plan must be defined before entry with total worst-case risk fixed.
7. Daily lock persists until the configured recovery checklist and objective risk conditions pass; acknowledgement alone does not bypass hard limits.

Exact percentages remain configuration parameters requiring offline validation and user approval, not learned directly from a confidence meter.

### 16.15 Trader-Facing Product Design

The first screen is a decision workspace, not a raw-data dashboard.

Primary radar row:

```text
symbol / contract
strategy profile and timeframe
READY / WAIT / REJECT / LOCKED
directional thesis
top three independent reasons
strongest contradiction
missing mandatory evidence
next trigger that can change state
invalidation and stop basis
proposed quantity and maximum rupee loss
data confidence, evidence rank and prediction status
oldest mandatory-source age
event/expiry/surveillance badges
```

Default views:

```text
Confirmed
Waiting
Recently changed
Rejected archive
Stocks
MCX
Intraday
Swing
```

WAIT rows remain visible with reason and timeframe. WAIT, REJECT and READY snapshots are automatically saved to notes/outcomes for later study.

Hidden Evidence Inspector:

```text
gate matrix G00-G14
source lineage and raw artifact hashes
observed/published/received/available timestamps
parser/schema versions and field warnings
feature calculations with units and lookbacks
independence-family contributions and caps
contradictory and rejected evidence
corporate event original filing links
option/OI/IV/Greeks assumptions
model version, sample size, calibration and drift status
counterfactual: what would change WAIT to READY
legacy scorer comparison during migration
source health, rate limit and retry history
```

The 354 raw URLs belong in source administration and lineage views, not on the primary trader screen.

### 16.16 Priority Activation Backlog by Marginal Decision Value

Activate sources because they close a decision gap, not to increase a link count.

| Priority | Contract | Decision gap closed |
| ---: | --- | --- |
| 1 | `nse_mwpl_ban` | Hard derivative veto and MWPL reliability; currently referenced by runtime but missing clean registry contract |
| 2 | `nse_quote_equity` | Current stock price/price bands; public route remains research until broker feed replaces it |
| 3 | `nse_quote_equity_trade_info` | Delivery, traded quantity and market-depth context |
| 4 | `nse_quote_derivative` | Contract-level futures basis, OI and expiry identity |
| 5 | `mcx_market_watch` | Current local commodity quote/OI context |
| 6 | `mcx_future_prices` | Local futures curve and basis |
| 7 | `mcx_option_chain` | MCX options OI/IV/Greeks context |
| 8 | `mcx_delivery_reports` | Expiry and delivery-pressure veto/context |
| 9 | `bse_insider_trading` | Cross-exchange promoter/KMP transaction evidence |
| 10 | `bse_xbrl_announcements` | Structured corporate-event confirmation |
| 11 | `bse_buyback_tender` | Corporate demand, record-date and offer-price anchor |
| 12 | `bse_takeover_open_offer` | Open-offer event risk and anchor |
| 13 | `amfi_monthly_portfolio` | Delayed stock-level mutual-fund sponsorship |
| 14 | `nse_pit_annual` | Long-horizon insider behavior and corrections |
| 15 | `lme_warehouse_stocks` | Base-metal inventory pressure |
| 16 | `shfe_weekly_stock` | China exchange inventory confirmation |
| 17 | `baker_hughes_na_rig_count` | Crude supply regime context |
| 18 | `imd_rainfall_timeseries` | Domestic agricultural weather regime |
| 19 | `usda_wasde` and `des_crop_estimates` | Global/domestic crop supply context |
| 20 | `dgcis_trade_data` and `china_nbs_indicator` | Trade and China-demand context |

`nse_preopen_nifty`, `nse_preopen_sme`, index routes, MFAPI mapping routes, RBI/MCA background sources and reference sites remain in the contract map but are activated according to the strategy jobs they close. `equitymaster_fii_buys_reference` remains reference/discovery only.

### 16.17 Revised Build Order

```text
H1  canonical plan and authority
H1A0 inventory compiler, normalization and semantic dedupe
H1A1 runtime state vocabulary and EvidenceClaim alignment
H1A2 calendar-aware scheduler, source health and correction handling
H2  exact source-contract-to-decision map for all 354 rows
H2A high-value missing-contract activation with fixtures and shadow evidence
H3  immutable raw -> parser -> dataset -> EvidenceClaim pipeline
H4  strategy profiles, derived features and independent-family fusion
H4A legacy scorer isolation and shadow replacement
H5  deterministic risk, account heat and quantity guidance
H6  primary decision radar
H7  hidden Evidence Inspector and source administration
H8  point-in-time outcomes, walk-forward validation and calibration
H8A drift monitoring and champion/challenger governance
H9  OpenAlgo read-only and shadow boundary
H9A Analyzer/sandbox and reconciliation tests
H10 separately approved execution milestone, not authorized by this plan
```

Do not wait for every slow context source before building H3-H5. Implement vertical slices:

1. Stock intraday slice with official EOD plus research intraday and fail-closed execution authority.
2. Stock swing event slice with filings, adjusted prices and sponsor evidence.
3. MCX gold slice with local EOD plus delayed global regime.
4. MCX crude slice with local EOD plus EIA/CFTC/dollar context.

Each slice must pass end-to-end lineage and WAIT tests before more URLs are activated.

### 16.18 Completion and Adversarial Review Criteria

Inventory and contracts:

1. All 354 canonical rows have an explicit disposition and next action.
2. All 69 linked and 43 not-linked exact source keys are mapped or deliberately merged.
3. URL, endpoint, contract, dataset and evidence counts are reported separately.
4. No malformed source-key arrays, compound URLs, sentinels or unexplained overlaps remain.
5. Source counts are generated, not hand-maintained in prose.

Data integrity:

6. Every fetch distinguishes valid-empty, stale, blocked, schema-changed and broken states.
7. Every normalized row links to a raw artifact hash and parser version.
8. Every source-date and correction test is calendar-aware.
9. Fallback evidence cannot inherit authority it does not possess.

Decision integrity:

10. Every displayed reason traces to one EvidenceClaim and one independence family.
11. Same-family endpoints cannot create duplicate votes.
12. Mandatory evidence absence and vetoes always prevent READY.
13. Event direction is UNKNOWN when not proven.
14. GEX remains `GEX_PROXY` unless actual positioning authority exists.
15. Current legacy scores never drive probability, risk or orders.

Prediction and risk:

16. Backtests reject future-available data and overlapping-label leakage.
17. Probability remains hidden until sample, calibration, expectancy and drift guards pass.
18. Quantity is reproducible from account risk, stop, costs, liquidity and portfolio heat.
19. WAIT, REJECT and no-trade outcomes are retained to audit selection bias.

OpenAlgo and operations:

20. Read-only parity, symbol mapping, timestamps and reconnect behavior pass before shadow intents.
21. Analyzer/sandbox reconciliation passes across restart, duplicate, reject, partial-fill and cancel cases.
22. No live broker action occurs without a separately approved milestone and kill switch.

Product:

23. Primary radar explains state, reason, missing evidence, trigger, invalidation, size and staleness without exposing raw-link noise.
24. Evidence Inspector reconstructs every decision from immutable evidence.
25. Notes automatically retain READY, WAIT and REJECT histories with later outcomes.

The correct external-AI review question is not whether this plan is "supreme" or impossible to fault. It is whether a reviewer can produce a concrete counterexample that violates one of these contracts, failure tests or acceptance criteria. Any valid counterexample becomes a versioned requirement and test before implementation.


## 17. Antigravity Panel Corrections - 2026-07-18

### 17.1 Review Boundary and Decision

Claude Sonnet 4.6 Thinking and Gemini 3.1 Pro High reviewed a de-identified architecture brief through the read-only Antigravity advisory boundary. Tenant policy prevented transmission of the private full plan, so the panel did not perform a line-by-line repository review. Their output is untrusted advisory input. The corrections below were accepted only where they are consistent with the canonical plan and verified implementation evidence.

This section supersedes Sections 15 and 16 only where it explicitly changes a contract or milestone order. All fail-closed rules remain in force.

The most important accepted correction is a new tradability and realizable-exit layer. Good source evidence cannot make a setup executable when the instrument cannot be entered or exited safely under its current exchange, settlement, circuit, auction, margin or contract state.

### 17.2 P0 Blocking Corrections

#### P0.1 TradabilityRestriction Contract

Create one derived, point-in-time contract:

```text
TradabilityRestriction
  instrument_id
  exchange
  segment
  series
  trade_to_trade_state
  enhanced_surveillance_state
  asm_state
  gsm_state
  fno_ban_state
  mwpl_utilization
  lower_price_band
  upper_price_band
  last_traded_price
  distance_to_lower_band_bps
  distance_to_upper_band_bps
  exchange_halt_state
  auction_state
  short_sale_or_delivery_constraint
  physical_delivery_state
  expiry_state
  source_data_date
  effective_from
  effective_to
  published_at
  received_at
  source_keys
  limitations
```

New source contracts must be registered only after official endpoint or file discovery and verification:

```text
nse_t2t_securities
nse_esm
nse_price_bands
nse_market_halts
```

These proposed keys are not included in the existing 354-row baseline until H1A0 adds their verified source records. Existing `nse_asm`, `nse_gsm` and the required clean `nse_mwpl_ban` contract remain part of the same derived tradability state.

Gate rules:

1. T2T or another delivery-only series blocks intraday entry.
2. Active exchange halt, unknown auction state or structurally unavailable exit blocks READY.
3. F&O ban blocks derivative-dependent entries.
4. ASM, GSM and ESM behavior is policy-configured by stage and strategy; severe stages may veto while lower stages reduce risk.
5. Price-band risk is based on current band, side, available depth, volatility and expected impact. Do not hard-code one universal distance such as 1 percent.
6. Expiry, physical-delivery and tender restrictions are instrument-specific hard checks.
7. Unknown tradability state returns `WAIT_TRADABILITY`, never a neutral value.

#### P0.2 Immutable Raw and Versioned Adjustment Layers

Replace any ambiguous adjusted-price storage with two explicit layers:

```text
RawMarketArtifact
  immutable source bytes and source fields
  source timestamp and content hash
  never rewritten for later corporate actions

AdjustedMarketSeries
  raw artifact references
  adjustment_event_ids
  adjustment_method
  adjustment_factor
  adjustment_version
  effective_date
  generated_at
  generated_by_version
```

Rules:

1. Split, bonus, dividend, merger, demerger and symbol-change adjustments create a new derived version.
2. Historical raw values and historical decision snapshots are never rewritten.
3. Backtests select the adjustment version available under their declared research policy.
4. A correction may mark a prior research result superseded, but cannot mutate the original decision evidence.
5. Gap, return, ATR, volume and pattern features must reference the same adjustment version.

#### P0.3 Timestamp and Revision Semantics

Every artifact, normalized row and EvidenceClaim must distinguish:

```text
event_time
exchange_time
published_at
vendor_time
received_at
available_at
data_date
effective_from
effective_to
revision_id
supersedes_revision_id
```

Requirements:

1. Backtests use `available_at`, not event date or exchange publication time alone.
2. Provisional and final institutional-flow data remain separate revisions.
3. Withdrawn, corrected or replaced corporate announcements invalidate dependent current claims and trigger recomputation.
4. Report-driven commodity features require actual release datetime and revision state.
5. A content hash proves byte identity, not freshness, authority or publication date.

#### P0.4 Hierarchical Evidence Families

The earlier families remain useful but must not be described as statistically independent.

Add a parent family:

```text
MARKET_FLOW
  PRICE_AND_LIQUIDITY
  DERIVATIVES_OI
  OPTIONS_VOLATILITY
```

Fusion rules:

1. Child families preserve distinct observations and explanations.
2. Their combined directional contribution is capped at the MARKET_FLOW parent.
3. Historical conditional correlation and shared-source lineage determine any additional penalty.
4. Price, OI and IV movement caused by one underlying order-flow event cannot become three full votes.
5. One regulatory filing creates one root filing identity. Event, ownership and pledge facets may serve different decision jobs but share one directional contribution cap.
6. NSE/BSE mirrors and vendor copies deduplicate by filing identity, instrument, event time and issuer, not URL or byte hash alone.
7. Correlation penalties affect ranking only after deterministic mandatory gates and vetoes.

#### P0.5 Realizable-Exit and Circuit Stress Risk

Rename deterministic risk to reproducible risk calculation. Inputs are versioned and calculations are deterministic, but future slippage and exit price are uncertain.

```text
stop_unit_risk = abs(entry - stop) + configured_costs
gap_stress_unit_risk = adverse_gap_scenario + costs
circuit_stress_unit_risk = locked_market_scenario + next_realizable_exit_loss
liquidity_stress_unit_risk = impact_model(order_size, depth, spread, regime)

realizable_unit_risk = max(
    stop_unit_risk,
    gap_stress_unit_risk,
    circuit_stress_unit_risk,
    liquidity_stress_unit_risk
)
```

Quantity uses `realizable_unit_risk`, not only stop distance.

Hard behavior:

1. A stop already breached at the open means no normal entry.
2. A locked or unreliable exit may force zero quantity.
3. Margin availability and exchange/broker margin multipliers are checked after stress quantity and before intent creation.
4. Stress assumptions are strategy-, segment- and liquidity-specific and versioned.
5. Display maximum planned stop loss and stressed realizable loss separately.

#### P0.6 Legacy Scorer Quarantine

Move legacy scorer isolation before the unified evidence pipeline is allowed to emit current decisions.

```text
legacy_discovery_rank_v1
  can_discover = true
  can_rank_research = true
  can_score_decision = false
  can_size = false
  can_unlock_ready = false
  can_create_order_intent = false
```

Acceptance:

1. No READY, probability, position size or order-intent path imports the legacy rank.
2. Shadow comparison stores legacy and replacement outputs separately.
3. Correlated activity inputs are not silently migrated into the new family score.
4. A regression test fails if the legacy score enters the decision contract.

### 17.3 P1 Integrity Corrections

#### P1.1 Outcome Logging Before Calibration

Build outcome capture with the first vertical evidence pipeline rather than waiting for the model milestone.

Store:

```text
decision_snapshot_id
strategy_profile
state_at_decision
entry_eligibility
WAIT_or_REJECT_reason
counterfactual_trigger
outcome_observation_window
right_censor_reason
target_before_stop
MFE
MAE
time_to_event
net_cost_adjusted_return
realized_fill_quality
data_revision_after_decision
```

Calibration remains in H8 after sufficient outcomes. WAIT and REJECT observations that do not complete the full outcome window are marked right-censored rather than silently dropped.

#### P1.2 Model Demotion Fallback

When a model is unavailable, stale, uncalibrated or demoted:

```text
MODEL_ACTIVE
-> MODEL_RESEARCH_ONLY
-> DETERMINISTIC_GATES_ONLY
```

The system must not freeze a stale probability or automatically promote a challenger. Deterministic gates may continue to produce WAIT/REJECT and an uncalibrated evidence rank. READY permissions for deterministic-only operation are strategy-configured and require separate validation.

#### P1.3 Broker Tick and Candle Integrity

Future OpenAlgo read-only integration must track:

```text
connection_id
subscription_id
exchange_timestamp
local_receive_timestamp
sequence_or_monotonic_counter where available
last_tick_age
reconnect_count
duplicate_tick_count
out_of_order_tick_count
gap_detected
candle_rebuild_state
history_reconciliation_state
```

On a detected gap:

1. Mark affected live candles incomplete.
2. Stop fresh READY decisions that depend on them.
3. Re-fetch bounded authoritative history through the broker/provider.
4. Rebuild candles deterministically.
5. Compare OHLCV and timestamps before restoring freshness.
6. Persist the outage and decisions affected by it.

#### P1.4 Versioned Dynamic Rule Inputs

Create effective-dated datasets for:

```text
brokerage and statutory fee schedule by segment/product
SPAN and exposure margin inputs
lot size
tick size
freeze quantity
price-band category
free-float value
index and sector membership
contract expiry and physical-delivery rules
trading and settlement calendars
```

Every quantity and feature calculation stores the versions it used.

#### P1.5 Release-Time and Revision Handling

Mandatory point-in-time controls include:

1. Pre-open snapshots carry auction phase and are not treated as final before the official equilibrium cutoff.
2. FII/DII provisional and final values are separate revisions.
3. EIA, crop, weather and other scheduled reports use actual release time.
4. Corporate filings carry original, corrected and withdrawn states.
5. Index reconstitution uses effective membership dates.
6. NSE equity and MCX holiday/session calendars are evaluated independently.

### 17.4 Strategy-Specific Additions

#### Stock Intraday

Add mandatory or veto checks for:

```text
T2T/delivery-only series
ESM/ASM/GSM state
dynamic price bands and distance
exchange halt and auction state
current index/sector membership
scheduled earnings or event blackout
usable depth or bounded impact estimate
tick/candle integrity
```

Delivery evidence is split:

- Final EOD/T+1 delivery supports swing and later-session research.
- Intraday delivery may be used only when the exact source contract proves provisional availability, timestamp and limitations.
- Missing final delivery cannot be replaced by an unofficial estimate and called official.

#### Stock Swing and Event

Add:

```text
record date and ex-date proximity
scheduled earnings and RBI/macro event overlap with holding horizon
filing publication/availability time
withdrawal/correction state
guidance history source and revision
free-float effective date
pledge severity and configurable veto threshold
gap-through-stop behavior
```

#### MCX

Add:

```text
commodity-specific circuit and halt state
contract lot/tick/freeze and delivery rules
expiry-day mode
timestamp-aligned USD/INR
global-to-local unit and purity conversion version
report release datetime
Indian/global holiday divergence
government export/import ban, MSP or intervention events where applicable
```

MCX and global reference comparisons must store the conversion formula and all input timestamps.

### 17.5 Feature Corrections

| Feature | Revised contract |
| --- | --- |
| Delivery anomaly | Separate provisional intraday and final post-session datasets; no cross-use without explicit scope |
| RVOL_TOD | Baseline records minute-of-day, lookback, expiry/non-expiry cohort, rebalance/event-day cohort and minimum observations |
| Matched quantity | Exclude or separately label block-window/pre-arranged activity where identifiable |
| PCR | Use change and percentile by expiry; proxy-only and never a standalone direction |
| Max pain | PROTOTYPE_ONLY, no gate, size or READY permission |
| GEX_PROXY | PROTOTYPE_ONLY until an approved test proves incremental value; always display missing dealer-position limitation |
| Spread | Use a rolling observation distribution where available, not one snapshot |
| Turnover/free float | Store free-float source and effective date; stale float reduces quality |
| Basis | Expiry-aware carry and curve context; suppress in defined expiry-day invalid windows |
| Sector relative strength | Require effective index membership and avoid ETF/index duplicate contributions |

### 17.6 Data-Science Corrections

Accepted rules:

1. Purging removes samples whose label windows overlap.
2. Embargo is based primarily on label overlap and empirically measured dependence, not automatically the longest feature lookback.
3. Use day/block bootstrap or clustered uncertainty to account for correlated observations.
4. Compare Brier score with a base-rate model and record reliability, resolution and uncertainty components.
5. Preserve right-censored WAIT/REJECT outcomes with explicit censor policy.
6. Model promotion still requires the Section 16 sample, calibration, expectancy and drift guards.
7. A shared corrupted feature store can invalidate champion and challenger simultaneously; source-health canaries and a simple deterministic baseline remain independent controls.
8. Logistic regression does not require a blanket stationarity test, but temporal stability, regime sensitivity and out-of-sample calibration must pass.
9. Complex commodity models remain prohibited until effective sample size supports them.
10. No automatic online retraining or promotion is allowed.

### 17.7 Risk and Cost Corrections

Required versioned inputs:

```text
STT
exchange transaction charges
GST
SEBI charges
stamp duty
brokerage
segment/product
effective date
intraday versus delivery classification
expected and stressed slippage model
margin multipliers
portfolio beta/correlation lookback
```

Correlation budget must define:

```text
return series
lookback
sampling interval
shrinkage method
regime
update cadence
missing-data policy
sector and beta exposure caps
```

Scaling or averaging requires revalidation of source freshness, thesis and tradability at every tranche. A preplanned tranche is cancelled when the original thesis, data quality or exit reliability degrades.

### 17.8 UI Corrections

Primary radar adds:

```text
T2T / ESM / ASM / GSM / F&O-ban badges
upper/lower band distance
halt/auction/expiry state
stale versus valid-empty versus zero-trade state
contradiction count plus strongest contradiction
missing-evidence reason and expected update time
planned stop loss versus stressed realizable loss
UNCALIBRATED quantity cap
```

Inspector adds:

```text
fee schedule version
margin-rule version
slippage and circuit-stress assumptions
free-float and membership effective dates
provisional/final revision chain
tick-gap and candle-rebuild history
proxy/prototype permission flags
model-demotion fallback state
right-censor reason
```

WAIT and REJECT remain visually distinct:

- WAIT is retryable and shows the next possible source publication or gate event.
- REJECT is closed for the current setup/snapshot and shows why a new setup is required.
- Zero quantity always displays the blocking reason and cannot appear as a silent blank.

### 17.9 Corrected Milestone Order

This order supersedes Section 16.17 where they conflict:

```text
H1    canonical plan and authority
H1A0  inventory compiler, state vocabulary and semantic dedupe
H1A1  EvidenceClaim envelope plus immutable raw/versioned-adjustment storage contract
H1A2  tradability restrictions and effective-dated exchange/broker rules
H1A3  legacy scorer quarantine plus outcome-logging skeleton
H1A4  calendar-aware scheduler, correction lineage and source health

H2    exact source-contract -> dataset -> feature -> strategy -> gate map
H2R   manual/adversarial review gate for every mandatory, confirmation and veto path
H2A   high-value missing-source activation with fixtures and shadow evidence

H3    unified raw -> parser -> normalized dataset -> EvidenceClaim pipeline
H3A   early point-in-time outcome collection and censor tracking
H4    strategy profiles, feature definitions and hierarchical evidence fusion
H5    reproducible risk, stressed exit, costs, margin and quantity
H6    primary decision radar
H7    Evidence Inspector and source administration

H8    probability calibration after sufficient accumulated outcomes
H8A   drift monitoring and champion/challenger governance

H9    OpenAlgo read-only parity, timestamp and tick-integrity boundary
H9R   mandatory read-only sign-off
H9A   shadow intents, Analyzer/sandbox and reconciliation
H10   separately approved execution milestone; not authorized here
```

### 17.10 New Mandatory Failure Tests

1. Corporate-action test: raw artifact hash stays unchanged while adjusted-series version changes.
2. T2T test: intraday READY is impossible for a delivery-only series.
3. Circuit trap test: a locked lower-band and next-session gap cannot be recorded as an exit at the theoretical stop.
4. Tradability unknown test: missing price-band/halt state yields `WAIT_TRADABILITY`.
5. Valid-empty test: a schema-valid zero-row result reaches `VALID_EMPTY`; an empty body fails transport/artifact validation.
6. Filing mirror test: NSE/BSE copies of the same filing create one root directional contribution.
7. Parent-family test: correlated price, OI and IV evidence cannot exceed the MARKET_FLOW cap.
8. Ex-date test: adjusted reference price prevents a false overnight gap signal.
9. Expiry-day test: invalid carry/basis windows are suppressed.
10. Provisional/final revision test: a later revision does not mutate the original decision snapshot.
11. WebSocket gap test: missing ticks mark candles incomplete and block dependent READY until reconstruction passes.
12. Candle spike test: historical reconciliation detects and rejects an impossible wick caused by malformed ticks.
13. Fee-version test: the same trade evaluated across a fee-effective date uses the correct schedule.
14. Margin-stress test: a volatility-driven margin increase cannot produce quantity above available margin.
15. Model-demotion test: a stale or degraded model falls back to deterministic gates with no frozen probability.
16. Overconfidence test: a deliberately overconfident model fails calibration promotion.
17. Censor test: unfinished WAIT outcomes are retained with a right-censor reason.
18. Holiday-divergence test: MCX-open/NSE-closed context is unavailable or delayed, never default zero.
19. Zero-quantity UI test: the blocking reason is visible and auditable.
20. Legacy-isolation test: no legacy score reaches READY, probability, size or order intent.

### 17.11 Panel Suggestions Not Adopted as Written

1. ASM, GSM and F&O-ban logic were not absent; the real defect is incomplete tradability coverage and the missing clean `nse_mwpl_ban` registry contract.
2. `VALID_EMPTY` already existed in the runtime state machine. It is now also explicit in the primary source-state ladder.
3. Hash integrity and freshness were already separate stages; the plan now adds a direct regression test rather than redesigning them.
4. ECE <= 0.05 and OpenAlgo phase separation were already present.
5. GEX was already a proxy; this revision adds an explicit PROTOTYPE_ONLY permission.
6. Feature lookback alone does not determine embargo length.
7. Logistic regression does not require a universal stationarity gate.
8. A fixed one-percent circuit-distance veto is rejected in favor of instrument-, side-, liquidity- and impact-aware policy.
9. The full evidence pipeline does not move ahead of the source map. The envelope and storage contract are defined first, the source map is reviewed, then the implementation pipeline is built.

### 17.12 Revised Completion Gate

TrendForge cannot be promoted beyond research-only until:

1. TradabilityRestriction is populated from verified current contracts.
2. Raw and adjusted price layers pass corporate-action replay tests.
3. The legacy scorer is technically unable to influence decision state, probability or size.
4. Source and broker timestamp gaps fail closed.
5. Stressed realizable loss remains within configured account and portfolio budgets.
6. Dynamic fees, margin, lot, tick, freeze and membership versions are reproducible.
7. The first vertical slices collect point-in-time outcomes including WAIT and REJECT.
8. UI states distinguish unavailable, stale, valid-empty, zero-trade, proxy and calibrated evidence.
9. OpenAlgo remains read-only until H9R sign-off.
10. Every accepted panel correction has a requirement, owner, test and observed result.

The panel review improves the failure model and operational realism. It does not increase claimed win probability. Only point-in-time outcomes and calibrated out-of-sample evidence may do that.

## 18. Full 354-Source Panel Reconciliation - 2026-07-18

### 18.1 Review Scope and Evidence Boundary

This section reconciles the existing canonical plan with the full-source advisory review requested from Claude Sonnet 4.6 (Thinking) and Gemini 3.5 Flash (High). Their responses are untrusted design advice. Repository code, the source workbook, official-source behavior and observed tests remain the authority.

The compact review packet represented every one of the 354 canonical URL rows through lossless host/path codebooks and included each row's inventory group, source role, active source key, placeholder state and canonical URL. The packet did not transmit every column of the approximately 748 KB workbook, raw artifacts, credentials or private broker data. Two localhost URLs were redacted because they are local TrendForge application routes, not external market-data sources.

Review packet evidence:

```text
SHA-256: 5fcf0201c7ff10ff168213cfae66446a48066b237057fe407ffa2ca033dd3bec
Packet size: 27,824 bytes
Canonical URL rows represented: 354
Providers consulted: Claude Sonnet 4.6 (Thinking), Gemini 3.5 Flash (High)
Consultation role: read-only advisory review
```

No external-model statement is sufficient to activate a source, change a gate, increase quantity or claim a higher win probability. Each accepted statement still requires repository evidence, an official contract or fixture, point-in-time validation and an observed test.

### 18.2 Reconciled Inventory Baseline

The source-of-truth workbook remains:

```text
D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx
```

Verified workbook baseline at this amendment:

| Inventory measure | Count | Meaning |
|---|---:|---|
| Canonical unique URLs | 354 | Every normalized URL discovered across current and historical reports |
| Linked usable URLs | 105 | Best-matching source is connected and usable under its current research scope |
| Not linked / not usable URLs | 231 | Not scanner-ready, including pending contracts and unavailable sources |
| Suppressed not-linked duplicates | 18 | Rows excluded from the not-linked queue because URL or active source key is already linked |
| Placeholder/test URLs | 5 | Preserved for audit visibility and prohibited from scanner evidence |
| `MASTER_CURRENT` rows | 370 | Current inventory plus preserved fragment-only discoveries |
| Linked normalized source keys | 69 | Active source contracts represented in this plan |
| Not-linked normalized source keys | 43 | Planned contracts represented in this plan |

These counts describe inventory and integration state, not independent evidence. A linked webpage, mirror, API route, archive file and derived metric may all describe one underlying dataset. They must never be counted as separate confirmations merely because their URLs differ.

### 18.3 Panel Claim Ledger

Every material panel recommendation is assigned one of these statuses before implementation:

```text
ACCEPTED
PARTIALLY_ACCEPTED
ALREADY_IMPLEMENTED
REJECTED
REQUIRES_OFFICIAL_VERIFICATION
```

| Recommendation | Status | Canonical decision |
|---|---|---|
| Group URLs by dataset/evidence family instead of counting URL votes | ACCEPTED | Dataset-root identity and family caps are mandatory. |
| Deduplicate transport variants, mirrors and cross-exchange copies of one event | ACCEPTED | Preserve all artifacts, but contribute once at the root-event level. |
| Track publication, effective, observation and revision time separately | ACCEPTED | Required for point-in-time replay and correction lineage. |
| Resolve date-template URLs dynamically and validate hash/schema | ACCEPTED | Resolver output cannot enter parsing until artifact gates pass. |
| Invalidate PCR, Greeks, skew, Max Pain and GEX when the parent chain is stale | ACCEPTED | All option-derived evidence inherits the same chain identity, expiry and freshness ceiling. |
| Strengthen MCX expiry, delivery, contract-specification, calendar and basis controls | ACCEPTED | Required before MCX READY. |
| Keep AMFI, NSDL and CFTC as delayed context | ACCEPTED | They cannot prove live symbol-level institutional flow. |
| Maintain separate NSE intraday, NSE swing, MCX intraday and MCX swing chains | ACCEPTED | Evidence requirements, clocks and vetoes differ by strategy. |
| Show surveillance, source health, contradictions and stressed loss in UI | ACCEPTED | Primary radar summarizes; inspector preserves detailed lineage. |
| Add duplicate, valid-empty, schema-drift, expiry and date-template tests | ACCEPTED | Added to the mandatory failure suite below. |
| Treat every official/support webpage as gate authority | REJECTED | Authority requires a structured, dated, schema-valid contract, not URL ownership alone. |
| Use previous close when pre-open evidence is absent | REJECTED | Missing auction evidence produces WAIT/open-confirmation logic. |
| Force an exit whenever a source fails | REJECTED | Source failure blocks new reliance; exits follow risk/tradability policy and last valid evidence. |
| Use a universal 50 percent pledge veto | REJECTED | Pledge risk is contextual, effective-dated and strategy-specific. |
| Apply one universal freshness interval to all sources | REJECTED | Cadence comes from exchange calendar, source frequency and decision horizon. |
| Count AMFI as independent live confirmation | REJECTED | AMFI is delayed sponsorship context only. |
| Use NSDL data as a trade outcome label | REJECTED | NSDL is evidence/context, not realized market outcome. |
| Declare bhavcopy production-ready without contract tests | REJECTED | Production authority requires resolver, hash, schema, date and replay tests. |
| Make BSE ASM/GSM a P0 execution gate now | PARTIALLY_ACCEPTED | Required only if BSE becomes an execution universe; current execution scope remains NSE/MCX. |
| Add MCX participant OI or pre-open immediately | REQUIRES_OFFICIAL_VERIFICATION | Add only after an official, stable and legally usable artifact contract is proven. |
| Collapse CFTC legacy, disaggregated and TFF into one duplicate | REJECTED | They overlap at market level but have distinct trader-category semantics; cap the family instead. |

### 18.4 Dataset-Root Identity and Dedupe Model

The registry must distinguish a dataset from the URLs used to reach it. Add these fields to the canonical source contract before broad activation:

```text
dataset_root_id
transport_variant_id
mirror_group_id
resolver_id
publisher_authority
endpoint_role
activation_state
decision_jobs
evidence_family
family_weight_cap
fallback_authority_cap
```

Definitions:

- `dataset_root_id` identifies the economic or regulatory dataset, such as NSE participant OI, NSE equity bhavcopy or one issuer filing event.
- `transport_variant_id` identifies API, CSV, ZIP, HTML, PDF or archive routes carrying the same dataset.
- `mirror_group_id` links official cross-published copies without discarding lineage.
- `resolver_id` points to the date/expiry/template resolver used to obtain the current artifact.
- `publisher_authority` records the organization that owns the data.
- `endpoint_role` distinguishes landing page, discovery route, download route, data endpoint, mirror and reference.
- `activation_state` separates inventoried, raw-connected, parsed, normalized, shadow and gate-authorized states.
- `decision_jobs` lists the exact strategy and gate jobs the dataset may serve.
- `evidence_family` prevents correlated facts from being treated as independent.
- `family_weight_cap` limits the total directional contribution of related features.
- `fallback_authority_cap` prevents unofficial fallback data from inheriting official authority.

Required identity chain:

```text
canonical_url
  -> transport_variant_id
  -> dataset_root_id
  -> normalized_dataset_version
  -> evidence_claim_id
  -> root_event_id
  -> decision_snapshot_id
```

Examples:

- NSE and BSE copies of the same issuer filing retain two artifacts but map to one `root_event_id` contribution.
- NSE option-chain CE/PE OI, PCR, Max Pain, skew, Greeks and GEX proxy map to one option-chain dataset root and share its freshness ceiling.
- CFTC legacy, disaggregated and TFF reports retain distinct category features but share one CFTC positioning family cap.
- A landing webpage and the CSV it discovers are one source workflow, not two confidence votes.

### 18.5 Four Separate Data-to-Decision Chains

The 354 URLs are assigned by decision job, not pushed into one universal score.

#### NSE intraday

```text
official/licensed intraday price and depth
-> pre-open/open confirmation
-> market and sector breadth
-> futures/option activity and liquidity
-> surveillance, ban, band, halt and event vetoes
-> execution-cost and stressed-exit check
-> READY / WAIT / REJECT with quantity
```

Delayed shareholding, AMFI, NSDL and CFTC evidence may alter context or risk caps but cannot confirm a live entry.

#### NSE swing

```text
official EOD price/delivery
-> adjusted corporate-action history
-> trend, volatility and liquidity
-> filings, deals, pledge and ownership deltas
-> futures/OI/option confirmation where available
-> event and tradability vetoes
-> calibrated swing outcome model
-> READY / WAIT / REJECT with quantity
```

#### MCX intraday

```text
OpenAlgo/licensed MCX intraday feed later
-> verified active contract and expiry
-> local OI, volume, spread and margin
-> commodity-specific global context with publication lag
-> exchange calendar, delivery and limit controls
-> stressed exit and lot sizing
-> READY / WAIT / REJECT with quantity
```

Global proxies cannot replace missing local MCX price/OI evidence.

#### MCX swing

```text
official MCX bhavcopy and contract specification
-> continuous-contract and rollover-safe history
-> CFTC/EIA/WGC/LME/SGE/FX context by commodity
-> inventory, seasonality and macro regime
-> delivery, expiry, basis and margin risk
-> calibrated commodity outcome model
-> READY / WAIT / REJECT with quantity
```

The same source may support multiple chains with different lag, authority and weight. A source must declare those permissions explicitly.

### 18.6 Accepted Code and Contract Corrections

The following are confirmed implementation items, not speculative features:

1. Replace fixed request defaults in `backend/trendforge_api/main.py` for SHFE date, MCX date and year-month with calendar-aware resolvers. A default must resolve at request time, validate against the source calendar and expose the selected date.
2. In `backend/trendforge_api/parsers/surveillance_pledge_fpi_parser.py`, never substitute `today_iso()` as GSM source date when the source has no date. Store `data_date=None`, preserve retrieval time separately and return `WAIT_SOURCE_DATE` for freshness-dependent use.
3. Ensure every row in `SUPPRESSED_NOT_LINKED_DUPES` is excluded from the active fetch queue while remaining visible in audit lineage.
4. Give the option-chain dataset one parent validity object. PCR, IV, Greeks, skew, Max Pain, OI walls and `GEX_PROXY` must all become unavailable when the parent chain is stale, empty outside its valid session, schema-invalid, expiry-mismatched or missing spot/time inputs.
5. Resolve active derivative/commodity contracts from official contract masters. Do not infer the active contract only from ticker text or the largest current volume.
6. Separate raw and adjusted OHLC histories. Corporate-action revisions create a new adjusted-series version and never mutate raw artifacts.
7. Preserve `observed_at`, `published_at`, `effective_at`, `retrieved_at` and `revised_at` where applicable. Backtests may use only evidence published by the simulated decision time.
8. Apply evidence-family caps after symbol mapping and event dedupe, before probability calibration and quantity sizing.
9. Make fallback authority explicit. An unofficial source can keep a research screen operating but cannot silently unlock an official READY gate.

### 18.7 Already Implemented - Preserve and Extend

Repository inspection found these capabilities already present. Do not create duplicate modules for them:

1. Dynamic NSE cash bhavcopy resolution already uses a `{yyyymmdd}` template in `backend/trendforge_api/source_resolver.py`.
2. Dynamic participant-OI and SLB resolution already use `{ddmmyyyy}` templates in the same resolver.
3. ASM and GSM stage extraction already exists in `backend/trendforge_api/parsers/surveillance_pledge_fpi_parser.py`.
4. OpenAlgo already has a partial read-only boundary. Extend it through approved read-only milestones rather than describing it as absent.
5. Immutable raw archive, parser result, source health and fail-closed readiness foundations already exist.
6. `VALID_EMPTY` already exists as a distinct runtime state and must remain distinct from transport, parse and schema failure.

These findings supersede any panel statement claiming the functions are wholly missing. The remaining work is contract completion, propagation, testing and gate wiring.

### 18.8 Official-Verification Backlog

The following remain planned but cannot be activated from advisory guidance alone:

| Candidate | Required proof before build/activation | Allowed interim behavior |
|---|---|---|
| MCX pre-open/auction evidence | Official endpoint/file, field semantics, session clock and valid-empty behavior | `UNKNOWN`; never substitute previous close |
| MCX participant-category positioning | Official artifact and category definitions | Use CFTC/global context only with delayed label |
| INR commodity spot references | Stable official/licensed contract and symbol mapping | Keep global proxy as context, not local price proof |
| BSE ASM/GSM | Official contract plus decision that BSE is an execution universe | Inventory/reference only for current NSE/MCX scope |
| MCX contract specification | Lot, tick, expiry, delivery, freeze and margin effective dates | Block MCX quantity when unknown |
| MCX delivery notices | Official dated artifact and deterministic parser | Apply conservative expiry/delivery WAIT policy |
| LME/SGE/WGC web datasets | Stable downloadable contract or deterministic embedded-data parser | Metadata/reference only when structured data is absent |
| Licensed live NSE/MCX feed | OpenAlgo/broker credentials, timestamp parity and read-only sign-off | Research-only EOD/prototype behavior |

### 18.9 Suggestions Explicitly Not Adopted

The implementation must not introduce any of these shortcuts:

1. A source is not production-ready merely because its URL is linked or its publisher is official.
2. Multiple URLs, report formats or mirrors do not create multiple votes.
3. Previous close is not pre-open evidence.
4. Source unavailability blocks new evidence-dependent entries but does not automatically liquidate an existing position.
5. Pledge risk has no universal percentage veto independent of company, trend, liquidity, change rate and strategy horizon.
6. There is no universal three-minute polling cadence or universal 10/15-minute freshness limit.
7. AMFI cannot confirm intraday institutional buying.
8. NSDL sector data cannot label a symbol-level trade as a win or loss.
9. Reference-only, discovery-only, prototype-only and unofficial-only sources cannot unlock READY.
10. CFTC report variants are not deleted as duplicates; their shared family is capped and their distinct category semantics are preserved.
11. MCX participant or pre-open features are not built from guessed endpoints.
12. Source failure, valid-empty, zero trade, stale data and market-closed state are never collapsed into one empty response.

### 18.10 Integration with the Existing Milestones

This section does not create a competing roadmap. It refines the corrected order in Section 17.9:

```text
H1A0  Add dataset roots, mirrors, transport variants, endpoint roles and decision jobs.
H1A1  Remove fixed-date defaults and false freshness; complete timestamp semantics.
H1A2  Add option-parent validity and derivative/commodity contract lifecycle controls.
H1A3  Add duplicate suppression, event-root identity and legacy-score isolation tests.

H2    Complete the 354-URL -> dataset root -> feature -> strategy -> gate map.
H2R   Human/adversarial review of authority, evidence family, lag and fallback caps.
H2A   Activate only verified high-value contracts through fixtures and shadow evidence.

H3    Route accepted datasets through one EvidenceClaim and immutable lineage pipeline.
H4    Apply strategy-specific fusion and family caps to the four decision chains.
H5    Use contract-aware costs, margin, lot, liquidity and stressed-exit sizing.
H6    Surface decision state, contradiction, source health and stressed loss.
H7    Surface complete evidence lineage and source administration in the inspector.
H8+   Calibrate only from point-in-time outcomes after sample and drift gates pass.
H9+   Preserve read-only OpenAlgo boundaries until separately approved sign-off.
```

Implementation order inside this amendment:

1. H1A0 registry schema and deterministic inventory compiler.
2. H1A1 fixed-date and false-freshness corrections.
3. H1A2 option-parent and contract-lifecycle validity.
4. H1A3 dedupe/event-root regression tests.
5. H2 complete source-to-decision mapping for all 354 canonical URLs.
6. H2R manual authority/family/fallback review.
7. H2A bounded source activation in priority order.

### 18.11 Additional Mandatory Failure Tests

1. Suppressed duplicate test: no `SUPPRESSED_NOT_LINKED_DUPES` row enters the active fetch queue.
2. Dataset-root test: two transport variants of one dataset create one directional contribution.
3. Cross-exchange filing test: matching NSE/BSE issuer events share one `root_event_id` while preserving both artifacts.
4. Dynamic-date test: resolver date changes with the requested session and never remains pinned to a historical default.
5. Source-date-absent test: undated GSM/ASM evidence cannot become fresh from retrieval date.
6. Option-parent test: stale or invalid parent chain invalidates PCR, Max Pain, Greeks, skew, OI walls and GEX proxy together.
7. Expiry-boundary test: expired strikes and contracts cannot leak into current-chain metrics.
8. Contract-master test: quantity is zero when lot, tick, expiry or symbol mapping is unknown.
9. Valid-empty test: schema-valid zero rows remain valid-empty; HTML block pages and empty bodies remain failures.
10. Schema-drift test: renamed or missing mandatory fields quarantine the artifact and preserve raw bytes.
11. Date-template artifact test: resolved URL date, parsed data date and expected trading session must agree.
12. CFTC family-cap test: legacy, disaggregated and TFF features cannot exceed the commodity-positioning cap.
13. Delayed-context test: AMFI, NSDL and CFTC cannot satisfy a live-flow gate.
14. Pre-open-missing test: absence of auction data yields WAIT/open confirmation, never previous-close substitution.
15. Source-outage position test: outage blocks new evidence-dependent entry without forcing an unplanned exit.
16. Four-chain isolation test: NSE/MCX and intraday/swing requirements cannot silently substitute for one another.
17. Placeholder test: all five placeholder/test URLs remain audit-only and cannot fetch or score.
18. Fallback-cap test: unofficial research fallback cannot inherit official source authority.

### 18.12 Amendment Acceptance Gate

This reconciliation is complete only when all of the following are observed:

1. Exactly 354 canonical URL rows are accounted for by the source-to-decision map.
2. The workbook baseline remains reconciled as 105 linked usable, 231 not linked/not usable, 18 suppressed duplicates and 5 placeholders unless a new verified inventory build intentionally changes it.
3. All 69 linked and 43 not-linked normalized source keys in this plan match the workbook with no missing, extra or duplicate key.
4. Every active URL maps to one `dataset_root_id`, `endpoint_role`, evidence family and allowed decision job.
5. Mirrors and transport variants cannot create independent confidence.
6. Missing source dates cannot become fresh from retrieval time.
7. Option-derived evidence cannot outlive or exceed the validity of its parent chain.
8. MCX quantity remains zero when active contract, lot, margin, delivery or expiry rules are unknown.
9. Delayed and unofficial sources remain visibly capped and cannot unlock live official gates.
10. Every accepted correction has an owner, fixture, failure test and observed result before completion is claimed.
11. Every rejected suggestion is represented by a test or invariant that prevents accidental introduction.
12. No second implementation roadmap or source-plan file is created; this file remains the single canonical plan.

This amendment improves source utilization by assigning each URL a controlled job, identity, authority and failure policy. It does not claim that all 354 URLs should be fetched on every scan, that 354 URLs equal 354 independent signals, or that more sources automatically increase accuracy. Better probability estimates require clean point-in-time features, independent evidence families, realistic costs, right-censored outcomes and out-of-sample calibration.

## 19. Independent Architecture Review Reconciliation - 2026-07-18

### 19.1 Review Coverage and Authority

The independent review package was inspected line by line against this canonical plan, the 354-URL inventory workbook and the current backend implementation. The three supplied review documents contain 1,392 physical lines. The third document substantially repeats the closing portion of the second and is supporting duplication, not an additional independent review.

The review's generated `SOURCE_UTILIZATION_MATRIX_354.csv` is accepted as planning evidence. It does not become runtime authority until each row is reconciled against the source registry, live or fixture-backed transport behavior, parser schema, source date, evidence scope, lineage and gate wiring.

Inventory and source status must use this maturity ladder:

```text
REGISTERED
-> TRANSPORT_CONNECTED
-> ARTIFACT_VALID
-> STRUCTURED_PARSED
-> SOURCE_DATE_VALID
-> SCOPE_VALID
-> SHADOW_WIRED
-> GATE_AUTHORIZED
```

`LINKED`, HTTP 200, a non-empty body or a successful parser invocation is not proof of gate-authorized evidence. The compiler must publish counts at every stage and preserve the reason a source stopped advancing.

### 19.2 Decision-Job Taxonomy

Every dataset root must map to one or more explicit decision jobs. Sources without an allowed job remain reference-only, discovery-only or quarantined.

| Job | Decision purpose | Scope restriction |
|---|---|---|
| J01 | Identity, symbols, ISINs, calendars and contract masters | No directional vote |
| J02 | Tradability restrictions, bans, bands, halts, auctions and surveillance | Veto or quantity cap only |
| J03 | Price, volume, delivery, spread, depth and liquidity | Timeframe-specific market evidence |
| J04 | Pre-open auction state and open confirmation | Session-bound; cannot use previous close as substitute |
| J05 | Market regime, breadth, index and sector leadership | Context; not symbol-specific institutional proof |
| J06 | Futures OI, basis, rollover and participant positioning | Participant data remains regime context |
| J07 | Options, IV, Greeks, PCR, Max Pain, OI walls and GEX proxy | One parent-chain validity ceiling |
| J08 | Deals, PIT, SAST, pledge and ownership events | Event identity and direction required |
| J09 | Corporate filings, results, announcements and corporate actions | Publication-time and revision aware |
| J10 | AMFI and NSDL institutional context | Delayed swing evidence only |
| J11 | MCX local price, OI, contracts, expiry, margin and delivery state | Local MCX evidence required for MCX READY |
| J12 | Global commodity positioning, inventory, physical and macro context | Context cannot replace local MCX evidence |
| J13 | Portfolio risk, costs, sizing and stressed realizable loss | May reduce quantity to zero |
| J14 | Outcomes, calibration, drift and model degradation | Point-in-time research only |

The inventory compiler must emit `decision_jobs`, `allowed_timeframes`, `allowed_instruments`, `directional_permission`, `veto_permission`, `quantity_permission` and `gate_permission` for each dataset root.

### 19.3 Shared NSE Transport Contract

The backend currently has more than one NSE transport behavior. `source_resolver.py` uses an unseeded request path while `institutional_sources.py` contains a seeded asynchronous NSE client. Replace this split with one shared transport contract used by resolvers, monitors and fetchers.

Required behavior:

1. Seed the public NSE session before API calls and retain one cookie jar per client lifecycle.
2. Refresh once after 401 or 403, then fail closed rather than looping.
3. Apply bounded exponential backoff with jitter and honor `Retry-After` for 429.
4. Rate-limit by host and endpoint class; do not apply one universal polling interval.
5. Validate status, content type, body size and expected response class before parsing.
6. Detect access-denied, CAPTCHA, login, maintenance and bot-block HTML returned with HTTP 200.
7. Preserve raw blocked/error artifacts separately from valid data and never classify them as valid-empty.
8. Return structured transport states distinguishing failure, blocked, schema mismatch, valid-empty and usable data.
9. Prefer verified official APIs/files; browser automation is not the default fallback.

Add milestone `H1A4`: build the shared seeded NSE transport and prove resolver, monitor and endpoint clients use the same response classifier.
### 19.4 F&O Ban and MWPL Contract Split

The current `nse_mwpl_ban` path is partially implemented, so it must not be described as wholly missing. Its current official artifact supplies F&O-ban evidence but not complete symbol-level MWPL utilization percentages.

Split the contract:

```text
nse_fno_ban
  role: official hard veto
  valid-empty: allowed for a dated trading session
  failure: WAIT_SOURCE_SNAPSHOT

nse_mwpl_percentages
  role: symbol-level utilization, near-ban risk and OI reliability
  required proof: verified official artifact or endpoint, dated schema and symbol coverage
  failure: WAIT_MWPL_PERCENTAGES
```

F&O-ban absence from a valid dated file means no listed bans for that session. Fetch failure, stale file, undated file and schema failure must never be interpreted as no bans. No exact MWPL percentage endpoint may be added until official live verification and fixtures prove the contract.

### 19.5 USD/INR Role Split for MCX

FBIL and live USD/INR serve different jobs:

```text
fbil_usdinr_reference
  authority: official
  frequency: daily
  use: MCX swing parity, daily currency context and reconciliation
  cannot: confirm synchronized intraday translation

usd_inr_live
  authority: official or licensed through the approved OpenAlgo boundary
  frequency: synchronized live
  use: MCX intraday parity, conflict checks and executable sizing
  missing: MCX intraday quantity remains zero
```

Completing the FBIL parser improves daily and swing context. It does not unblock MCX intraday READY by itself.

### 19.6 Canonical State Compatibility

One versioned compatibility layer must map all runtime and historical states to the canonical decision vocabulary:

```text
READY
WAIT
REJECT
NO_TRADE
LOCKED
```

Legacy states such as `WATCH_LONG`, `WATCH_SHORT`, `SHORT_WATCH`, `WAIT_DATA_WEAK` and `WAIT_CONFIRMATION` must declare their canonical state, directional hint, execution permission and migration version. Unknown states fail closed to `WAIT_STATE_MAPPING`; they must not silently appear as READY, disappear from the dashboard or bypass note storage.

Backend model, API serialization, frontend rendering, journal storage and ML snapshot tests must use the same state contract. Historical stored values remain immutable and are interpreted through the versioned adapter.

### 19.7 Unified Point-in-Time Outcome Worker

TrendForge already has partial primitives for path labels, MFE/MAE, walk-forward validation and outcome-related storage. The missing component is one automated worker joining these primitives to the exact decision snapshot.

The worker must record:

- decision ID, symbol, instrument, direction, strategy and timeframe;
- READY, WAIT and REJECT states, including counterfactual observation without simulated execution;
- entry eligibility time, target, stop, time stop and censoring reason;
- MFE, MAE, target/stop ordering and bars-to-event;
- spread, slippage, fees, impact assumption and stressed realizable loss;
- source, parser, feature, rule, model and configuration versions;
- publication cutoffs, source revisions and missing-evidence states;
- regime, liquidity and tradability context at decision time.

No training or calibration row may use evidence published after the simulated decision. Revised source data creates a new lineage version and triggers bounded recomputation rather than mutating the original snapshot.

Promotion thresholds must use effective sample size by strategy/regime, confidence intervals, calibration error, expectancy after costs, drawdown, false-READY rate and drift. A fixed count such as 200 outcomes is not a universal promotion rule.
### 19.8 Cross-Exchange Event Matching

NSE and BSE records that may describe the same deal or filing must retain separate artifacts and publisher lineage. Matching creates a shared root event only when identity is sufficiently strong.

Required match states:

```text
MATCHED
POSSIBLE_MATCH
DISTINCT
MANUAL_REVIEW
```

Candidate features include mapped symbol/ISIN, event type, event date and publication time, buyer/seller or filing entity, direction, quantity, price, value, attachment hash and revision relationship. Symbol/date/price/quantity similarity alone cannot force deduplication because partial fills, corrections and separate executions may look similar.

Only `MATCHED` records share one directional contribution. `POSSIBLE_MATCH` is capped or excluded from directional scoring until resolved.

### 19.9 Dataset-Root Priority Correction

Implementation priority is assigned to dataset roots, not raw URL rows. The review's 13 P0 URL rows include landing pages, APIs, downloads and mirrors for fewer underlying datasets.

True P0 roots are:

1. Instrument universe, symbol/ISIN mapping and active-contract identity.
2. Trading calendar, session state and publication expectation.
3. Tradability restrictions: ASM, GSM, F&O ban, MWPL, T2T/ESM where in scope, price bands, halts and auctions.
4. Corporate-action adjustment and raw-versus-adjusted series state.
5. Shared source transport, response classification, source date, freshness and immutable lineage.

Large deals, SLB, ownership, options and global context remain valuable strategy evidence but are not universal P0 prerequisites for every scan. Their priority is determined by the strategy chain they serve.

### 19.10 Conflict and Fusion Rules

1. Official structured evidence outranks secondary discovery and unofficial fallback evidence.
2. Authority does not override freshness, scope, schema or publication-time failure.
3. Valid-empty is accepted only when the expected report/session date and schema are valid.
4. Stale evidence remains visible with timestamps but contributes zero gate authority.
5. Market, sector, participant and symbol evidence cannot substitute for one another.
6. Missing MWPL, active contract, currency leg, corporate-action state or tradability state forces WAIT or zero quantity where required by the strategy.
7. Multiple transports, mirrors and derived fields from one dataset root share one family cap.
8. Revisions preserve prior versions and re-evaluate affected decisions.
9. Contradictory authoritative evidence produces an explicit contradiction state; averaging is not resolution.
10. Source outage blocks new evidence-dependent entries but does not automatically force an unplanned exit from an existing position.

Independent combinations that may add evidence after point-in-time validation include price acceptance plus delivery quality, futures OI/basis plus liquidity, option positioning plus spot/futures confirmation, filing events plus adjusted price response, and local MCX state plus lag-aware global context.

Combinations that must not create extra confidence include URL mirrors, API/page/download variants, PCR/Max Pain/Greeks/GEX from one option chain without a family cap, multiple CFTC report variants without a positioning cap, participant OI treated as symbol-level FII proof, and AMFI/NSDL treated as live flow.
### 19.11 Legacy Discovery Scorer Quarantine

The existing intraday discovery scorer combines overlapping activity totals, rewards the absolute size of pre-open gaps in either direction, gives positive points for any block/bulk notional without complete direction semantics, uses static PCR thresholds and rewards any recent result. It may remain a discovery rank during migration but must be technically unable to affect READY, position size, confidence calibration or order payloads.

Required controls:

1. Rename or label output as `LEGACY_DISCOVERY_SCORE` in APIs and UI.
2. Add a call-graph/contract test proving READY and quantity do not consume it.
3. Replace absolute-gap reward with direction, auction quality, acceptance and open-confirmation evidence in the new engine.
4. Deduplicate activity by dataset root and normalize relative to symbol/time-of-day history.
5. Require buyer/seller direction and event identity before deal contribution.
6. Make option thresholds regime-, expiry- and liquidity-aware after calibration.
7. Treat results as an event-risk state and measured surprise/response, not an automatic positive score.

### 19.12 Risk Policy Treatment

Exact risk percentages, correlation cutoffs, daily-loss limits and slippage thresholds proposed by reviewers are research defaults, not permanent constants. Store them in versioned configuration and validate them through historical and shadow evidence.

Final quantity remains the minimum permitted by account risk, stop distance, stressed slippage, liquidity, lot/freeze constraints, portfolio exposure, correlation, event risk, data quality and strategy confidence. Any mandatory unknown can reduce quantity to zero. Confidence may reduce risk but cannot relax hard loss, liquidity, tradability or account limits.

### 19.13 Milestone Amendments

These amendments extend the roadmap in Sections 17 and 18; they do not create another roadmap:

```text
H1A4  Shared seeded NSE transport and response classifier.
H1A5  Source maturity ladder and dataset-root priority report.
H2R   Manual reconciliation of the 354-row utilization matrix before runtime authority.
H3A   F&O-ban/MWPL and daily/live USD-INR contract splits.
H4A   Canonical state compatibility layer and API/frontend contract tests.
H7A   Automated point-in-time outcome and counterfactual worker.
H8A   Cross-exchange event matching with ambiguity and revision lineage.
```

Each amendment requires an owner module, requirement ID, source contract, fixture, failure behavior, observed test and rollback condition.
### 19.14 Additional Failure Tests

1. Seeded-transport test: resolver, monitor and fetcher use the same NSE session/response classifier.
2. HTTP-200-block-page test: HTML access denial cannot become JSON, valid-empty or fresh evidence.
3. Ban-valid-empty test: a dated schema-valid empty ban file differs from fetch or parse failure.
4. MWPL-split test: F&O-ban evidence cannot satisfy `FULL_MWPL_PERCENTAGES`.
5. FBIL-role test: daily FBIL context cannot satisfy the live MCX currency gate.
6. State-migration test: every stored/API/UI state maps deterministically; unknown states fail closed.
7. Legacy-isolation test: changing the legacy discovery score cannot change READY or quantity.
8. Outcome-cutoff test: post-decision publications and revisions cannot leak into original outcomes.
9. Counterfactual test: WAIT/REJECT outcomes are observed without being recorded as executed trades.
10. Deal-ambiguity test: possible cross-exchange matches remain separate contributions until resolved.
11. Dataset-root-priority test: landing pages and transport variants cannot inflate P0 work count.
12. Family-cap test: option-chain and CFTC derivatives cannot exceed their root-family caps.
13. Risk-configuration test: policy changes are versioned and reproduce historical decisions.
14. Gate-authorization test: linked or parsed status alone cannot set `can_unlock_ready=true`.

### 19.15 Recommendations Not Adopted

1. Do not activate all 354 URLs as fetchers; many are references, landing pages, mirrors or unsupported candidates.
2. Do not delete reference/documentation URLs; keep them in inventory and remove them only from active fetch/scoring roles.
3. Do not accept the unsupported assertion that 28 contracts are currently gate-authorized. Authorization is derived from role, authority, schema, source date, freshness, scope and wiring.
4. Do not treat the 13 P0 URL rows as 13 independent build tasks.
5. Do not describe F&O-ban/MWPL support or outcome infrastructure as wholly absent; preserve existing partial implementations and complete their contracts.
6. Do not use FBIL as a synchronized MCX intraday feed.
7. Do not force NSE/BSE deduplication when event identity is ambiguous.
8. Do not hardcode reviewer-proposed risk thresholds or a universal 200-outcome promotion rule.
9. Do not preserve dated 403, 404 or row-count observations as timeless source facts; mark them `REQUIRES_LIVE_REVERIFICATION`.
10. Do not assume an official MWPL-percentage endpoint exists until verified.
11. Do not default to browser automation where an official file or verified direct API exists.
12. Do not allow EOD, delayed or unofficial-only evidence to unlock executable intraday READY.
13. Do not interpret all public sources as permanently prohibited from READY. An official public source may become gate-authorized after its complete contract is structured, fresh, scoped, fixture-tested and wired.

### 19.16 Acceptance Gate

This reconciliation is accepted only when:

1. The 354-row utilization matrix is reviewed by dataset root and does not become runtime authority automatically.
2. Every active dataset reports its maturity-ladder state and blocking reason.
3. Shared NSE transport behavior is observed across resolver, monitor and fetch paths.
4. F&O-ban and MWPL percentages cannot satisfy each other's contracts.
5. FBIL daily context and live USD/INR cannot substitute for each other.
6. Legacy and canonical decision states render consistently across storage, API and frontend.
7. The legacy discovery score cannot influence READY, calibrated probability, quantity or execution payloads.
8. Outcomes preserve point-in-time cutoffs, costs, censoring, revisions and decision-state counterfactuals.
9. Cross-exchange ambiguity cannot create duplicate confidence or destructive deduplication.
10. P0 priority is produced by dataset root rather than URL count.
11. Every accepted recommendation has a requirement, owner, fixture, failure test and observable result.
12. Every rejected shortcut is protected by a test or invariant.

No implementation completion is claimed by this section. Historical status
`CANONICAL_PLAN_INDEPENDENT_REVIEW_RECONCILED_AWAITING_IMPLEMENTATION` remains
documentary. **Current build authority is File A** (`new_merge_PLAN_2026-07-18.md`)
with dual-file detail rules in File A §25 and the preamble at the top of this file.

## 20. Dual-File Pointer Back To File A (2026-07-20)

This section does not replace §§1–19. It records that:

1. File A §25 is the index of which Hybrid sections builders must open.
2. CROSS-001…024 / GAP-001…018 / POST-HYB / CONFLICT IDs live in File A §25.
3. Implementation progress is recorded only in `docs/BUILD_STATUS.md` and
   `docs/VALIDATION.md`.
4. Do not create a third competing “final” plan. Do not full-merge this file
   into File A.
5. Gemini dual-file governance is adopted **only** as dual-file pointers +
   conflict rules; corrected where it assumed H1–H10 as File A sequence or
   required live quantity sizing under the current research-only product.
## 21. Professional Mathematics Cross-Reference (2026-07-30)

This section is a navigation amendment, not another implementation sequence.
File A remains the only work selector. Open
docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md only when the selected File A
requirement needs the corresponding research definition.

| Mathematics detail | File A owner | Binding interpretation |
|---|---|---|
| General and conservative EV; break-even probability | R16, R18 | Future calibrated outcome research only; current evidence-based CONFIRMED neither implies nor requires probability/EV |
| Factor residual, rolling beta and volatility regime | R8, R9, R16 | Subtract alpha and aligned market/sector exposure; PIT estimates and replay required |
| Infinite- and finite-horizon barrier probability | R16, R18 | Infinite-horizon closed form cannot be labeled finite-horizon; include no-hit-by-H outcomes |
| Microprice, OFI and market impact | POSTPONE until mapped source proof | LTP/volume/top-five snapshots are insufficient; units, event horizon and calibration are mandatory |
| Observable price/OI quadrant | R12, FTR-020 | Store four OI_* co-movement codes only; buildup/covering and participant intent remain interpretations |
| Covariance-aware experimental fusion | R16, R18 research | Requires regularization, condition diagnostics and OOS proof; cannot replace FUS-009 |
| Options, M-Factor and corporate-action formulas | Existing R3/R12/DAT-022 owners | Use the canonical formulas and eligibility rules in File A, Final Merge, Discovery and Hybrid; the mathematics file only cross-references them |
| Dividend-aware Theta and delta-hedged variance attribution | R12, R16 through FMR-005/FMR-006 | Professional Mathematics section 17.5 owns the equations and units; Hybrid supplies PIT, cost and replay controls; outputs are modeled attribution, not direction or flow |
| Variance-risk-premium context | R12, R16; R18 for promotion/drift | Compare synchronized same-horizon risk-neutral implied variance with a PIT physical expected-realized-variance forecast; label ATM-IV proxy; `VRP_UNKNOWN` on missing lineage/calibration; no automatic option buy/sell |

Hybrid q_i remains the claim-quality definition. File A FUS-009 remains the
production evidence-rank calculation. Neither is win probability, expected
return, accuracy, confidence, quantity, or execution authority.
The detailed call/put Theta formulas, local delta-hedged variance attribution and VRP proxy are versioned in Professional Mathematics sections 17.5-17.7. Hybrid must not replace them with `IV > RV => sell`, `IV < RV => buy`, a fixed volatility-point threshold, or a directional interpretation of backwardation/contango. Any useful context remains one correlated options-package component under File A ceilings.