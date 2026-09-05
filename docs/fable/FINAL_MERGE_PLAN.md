# TrendForge Final Merge Plan
## Implemented File A R4/R5 checkpoint - 2026-08-23

- R4 is implemented through `selection/r4_live.py`, the pinned PK inventory in
  `scanners/pk_compatibility.py`, and read-only
  `GET /api/v1/selection/identity-pin`. It reuses A2 identity, rejects numeric
  companion scrip codes as NSE identity, quarantines unknown PK IDs, and grants
  PK zero rank/state/vote authority. The finite JSON worker remains an offline
  developer boundary, not a production sidecar.

- R5 is implemented through `selection/r5_live.py` and read-only
  `GET /api/v1/selection/structure`. It computes deterministic adjusted
  closed-bar breakout, NR7 and RVOL research tags from official cash history.
  The hash-matched R14 corporate-action join and A5 index context fail closed.
  Live output remains WATCH/WAIT/REJECT with zero CONFIRMED and no trade
  geometry, quantity, probability, broker or execution fields.

- R1 continues to retain all 123 registry-job dispositions. R4 and R5 consume
  only inputs appropriate to identity tagging and closed-bar structure; other
  sources remain in lineage/missing-evidence records for later File A families.
  They are not removed and must not be flattened into independent votes.


**Updated:** 2026-08-16 — cash A1–C1 is implementation evidence only. Remaining
File A **R1** is the live evidence DTO; remaining **R2** is attention order over
that spine. The Inventory Workbench / Source Operations page is **not** connected
to live stock evidence or ranking. File A still owns R0–R18 and activation
ceilings. Naming lock: File B = Hybrid only; Discovery is not File B.

## Implementation evidence — cash research path (2026-08-15)

This section is **observed code/tests**, not a second build spine and not
permission to mark FMR-001/002 complete.

| File A owner | Final Merge alias | Status |
|---|---|---|
| R0-A / R0-B / R0-C | FMR-001 (partial) | Compiler honesty closed; R0-B reviewed non-voting; R0-C quarantined |
| R1 STO + cash facts | FMR-002 (partial) | WAIT storage + cash A1–A4 **modules done**. Remaining R1 = live DTO / why-not-confirmed / alias-aware last-good bundle — **not** on the workbench page |
| R2-A S0–S3 cash attention | FMR-001 / FMR-002 (partial) | Cash WATCH + C1 **modules done**. Remaining R2 = attention order + **R2-SHADOW** queue — **not** painted on Source Operations. File A **R2-B remains activation (closed)** — do not name shadow `R2-B` |
| R2-B activation | FMR-001 | **Not started** — `sourceActivationReady=false` |
| Live CONFIRMED | FMR-002 later structure | **Not authorized** |

**Cash pipeline (research only):** A1 staging → A2 identity/S0–S1 → A3 §25.25.4
WATCH discovery → A4 PIT history/CA vintages → A5 index context + CA integrity →
A6 futures-only shortlist enrich → C0 use matrix → B MWPL optional → C1 rank if
`can_rank`. Plan: `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md`.
Evidence: `docs/BUILD_STATUS.md`, `docs/VALIDATION.md` (A1–C1 suite **19 passed**).

**Still open for Final Merge product completeness:** R1 live evidence DTO,
R2 attention-order + shadow runs, **then** live R3 resolver on those claims
(not Q5 fixtures, not workbench Consensus). R14 CA join before any live R5
CONFIRMED. R6/R8/R11/R12 on the shortlist only. R15 Scanner Lab is the
TrendForge frontend (`TRENDFORGE_FINAL_PRODUCT.html` IA), **not** the
Inventory Workbench. Full debug: locked plan §12. Also later: R16 PIT lab,
activation, live CONFIRMED, quantity (postponed), OMS (rejected).

**R3–R15 run warning:** four parallel paths exist (A1–C1, Q5 fixtures,
`/api/radar`, workbench). Wiring the workbench or fixture radar to R3/R15
cannot satisfy FMR-002/FMR-007/FMR-009.

**R3 (locked, not started):** Execute `R0_R1_R2_LOCKED_PLAN` **§13 including binding correction §13.9** only.
R1/R2 are live. R3 = FUS-009 diagnostics on those bundles, `state_ceiling=WAIT`,
no second ranker, no workbench, no live CONFIRMED. Do not re-audit before build.

## Naming (mandatory)

| Name | Path | Role |
|---|---|---|
| **File A** | `docs/fable/new_merge_PLAN_2026-07-18.md` | Only build sequence (`R0-R18`), IDs, states, ceilings |
| **File B (Hybrid)** | `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` | Formula / inventory / long recipes via File A §0.5/§25 |
| **Discovery Detail Plan** | `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` | Product workflow, modes, UI fields — **not** a build sequence |
| **Options Detail Plan** | `docs/OPTIONS_INTELLIGENCE_PLAN.md` | Options package layout — **not** a build sequence |
| **Professional mathematics** | `docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md` | Research definitions and canonical formula crosswalk; **not** a build/state authority |
| **This file** | `docs/fable/FINAL_MERGE_PLAN.md` | Mandatory product/design addendum via File A §25.21 `FMR-*` |

Never call Discovery or Options “File B”. That name is reserved for Hybrid.

## How to use this file

1. Select a File A `R*` / CROSS / TDG requirement first.
2. Open every mapped `FMR-*` section (File A §25.21).
3. Open Hybrid (File B) sections File A requires.
4. Use Discovery/Options detail plans only for fields, modes, and UI.
5. Never run a parallel `M0-M23`, `T0-T4`, or `PK-A..PK-D` board as build order.
6. Do not hardcode `sourceActivationReady` in plans; read current ceiling from runtime + `BUILD_STATUS` / `VALIDATION`.

## Mathematics detail boundary (mandatory)

docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md supplies mapped research
mathematics only. File A still owns order, state, permissions and acceptance;
this Final Merge file and the Options Detail Plan remain the canonical detailed
owners for option eligibility, identity, parity, surface, max-pain and cash-Gamma
contracts.

- Current CONFIRMED is evidence-based and does not imply calibrated probability or positive EV.
- General EV uses conditional gain/loss/cost distributions; any future gate uses conservative probability, payoff and cost bounds under R16/R18.
- The closed-form barrier equation is infinite-horizon. Finite-horizon target-before-invalidation includes the no-hit-by-H outcome and requires PIT numerical/replay proof.
- Risk-neutral density is an option-price diagnostic, not physical target-hit probability.
- Observable OI facts use the four OI_* price/OI codes. Long/short buildup, covering, participant identity and dealer intent are interpretations.
- Covariance-weighted research cannot replace FUS-009; microprice/OFI/impact remain unavailable until a verified timestamped event source and calibrated units exist.
## Requirement authority vs implementation evidence

```text
REQUIREMENT AUTHORITY
  current instruction → AGENTS → File A + DECISIONS
  → mapped FMR (this file) + Hybrid (File B) sections
  → Discovery/Options detail only

IMPLEMENTATION EVIDENCE
  observed runtime → code and tests
  → BUILD_STATUS / VALIDATION
  → coverage CSV (traceability only, never authority)
```

## Executive Verdict

**Decision:** `BUILD_A_HYBRID`

File A, `new_merge_PLAN_2026-07-18.md`, remains the sole authority for
architecture, safety, public states, source governance, acceptance, and the
`R0-R18` build sequence.

The **Discovery Detail Plan** supplies product workflow, candidate-discovery,
scanner-mode, navigation, verification-surface, and PKScreener feature ideas.
It does not create a second build order and cannot grant source activation,
gate permission, CONFIRMED, quantity, or execution.

## Corrected Assessment

1. File A is not merely abstract. It already defines source roles,
   point-in-time controls, feature contracts, the `S0-S9` pipeline, evidence
   families, state gates, storage, APIs, tests, and implementation order. Its
   main weakness is limited trader-workflow and navigation detail.
2. The Discovery Detail Plan contributes useful discovery modes, sector-relative workflows,
   shortlist-first enrichment, trader navigation, verification surfaces, and
   PKScreener feature ideas.
3. A permanent PKScreener runtime sidecar is not the default. The first
   permitted integration is a pinned, offline, sanitized, schema-validated
   JSON or CLI adapter operating in shadow mode.
4. Entry, stop, and target levels are allowed only as non-executable research
   scenarios. They require adjusted fresh closed bars, point-in-time corporate
   action handling, costs, structural invalidation, and adequate reward/risk.
5. `HYPOTHESIS_V0` is not a probability, confidence, or state authority. Any
   retained discovery rank must be transparent, deterministic, family-capped,
   versioned, and unable to authorize CONFIRMED.

## Stable Merge Decisions

| ID | Topic | Decision | Final rule |
|---|---|---|---|
| CMP-001 | Architecture authority | A_BETTER | File A and `R0-R18` remain authoritative. |
| CMP-002 | Source semantics | A_BETTER | Linked or HTTP-successful is not activated or scanner-ready. |
| CMP-003 | Discovery workflow | MERGE | Adopt Discovery Detail Plan modes under File A eligibility gates. |
| CMP-004 | Sector-relative funnel | DISCOVERY_BETTER | Add as a deterministic discovery profile, not independent evidence. |
| CMP-005 | PKScreener boundary | MERGE | Offline shadow adapter first; native promotion only after proof. |
| CMP-006 | M-Factor and ranking | IMPROVE | Transparent family-capped discovery rank; never win probability. |
| CMP-007 | Entry, stop, and targets | MERGE | Research scenario only; no order or quantity semantics. |
| CMP-008 | Public state | A_BETTER | Only WATCH, WAIT, CONFIRMED, and REJECT. |
| CMP-009 | Navigation | MERGE | Group Discovery Detail Plan tools into five coherent workspaces. |
| CMP-010 | Implementation order | A_BETTER | Reject parallel `M`, `T`, or `PK` roadmaps as authorities. |
| CMP-011 | Engine composition | IMPROVE | Engines emit EvidenceClaims into one resolver. |
| CMP-012 | Production readiness | A_BETTER | Require observed acceptance and runtime evidence. |

## Canonical Hybrid Flow

```text
activated source contract
  -> structured FetchResult
  -> immutable raw artifact and content hash
  -> parser and schema validation
  -> symbol/ISIN resolution
  -> point-in-time timestamps and revision handling
  -> S0/S1 eligibility gates
  -> E1 official-source discovery
  -> optional E2 PK shadow tags
  -> canonical EvidenceClaims
  -> evidence-family resolver and double-counting caps
  -> freshness, conflict, surveillance, F&O-ban, and risk gates
  -> non-executable research scenario
  -> one CandidateDecision
  -> primary radar and hidden evidence inspector
```

Successful-empty, blocked, transport failure, parse failure, schema failure,
stale evidence, and gate denial remain separate typed outcomes. No stage may
convert an unknown or failed outcome into positive evidence.

## Trader Workspaces

The Discovery Detail Plan's fourteen tools are retained as capabilities but grouped into five
workspaces:

1. **Radar:** ranked candidates, public state, profile, catalyst, risk, missing
   proof, and exact exclusion or no-action reason.
2. **Discovery:** sector scope, gaps, liquidity, volume, OI, accumulation,
   speculation, and swing filters.
3. **Derivatives:** OI, option chain, strike and expiry context, basis, MWPL,
   and F&O-ban state.
4. **Research:** ownership, announcements, institutional context, historical
   behavior, and point-in-time research evidence.
5. **System Health:** source activation, freshness, failures, revisions,
   lineage, formula versions, hashes, and gate ceilings.

The primary radar remains concise. The hidden inspector carries source keys,
data and retrieval timestamps, formulas, hashes, supporting, opposing, and
missing evidence, family caps, conflicts, revisions, stale reasons, and state
ceilings.

## Discovery Detail Plan capability mapping

The complete seven-capability mapping is preserved in
`docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md`, section **Coverage of your
earlier "minimum 7"** (current snapshot lines 263-273; first mapping row line
267). It covers intraday F&O ranking, NIFTY/BANKNIFTY analysis, options OI
tracking, PCR movement, descriptive expiry-range context, swing scanning, and
delivery/accumulation. File A selects the owning requirement; this reference
cannot authorize a separate `M/T/PK` order.

| Discovery Detail capability | Authoritative milestone |
|---|---|
| Correctness and source-contract prerequisites | R0 and R2 |
| Five discovery modes and sector-relative funnel | R2 |
| Evidence merge and candidate explanation | R3 |
| PK dependency pinning and offline shadow adapter | R4 and R7 |
| Research entry, stop, and target scenario | R5 after formal acceptance amendment |
| Native replacement of proven PK features | R8 and R13 |
| Candidate lifecycle and reconstruction | R9 |
| Pipe and filter language | R10 |
| Options and derivatives workspace | R12 |
| Radar, inspector, and verification surfaces | R15 |
| Point-in-time replay and calibration | R16 |
| Paper Lab / governed batch ML (FMR-011) | R15, R16, R18 |

## Rejected or Postponed Behavior

The following are not authorized:

1. A competing `M0-M17`, `T0-T4`, or `PK-A-PK-D` implementation sequence.
2. Treating linked inventory rows, HTTP 200, parser invocation, or raw
   artifacts as usable or gate-authorized sources.
3. A permanent PKScreener service that votes directly or bypasses canonical
   source, freshness, family, and evidence contracts.
4. Opaque M-Factor, confidence, win-rate, or probability labels.
5. Missing-weight renormalization that increases conviction when evidence is
   absent.
6. Counting correlated OI, volume, derivatives, mirrors, or transport variants
   as independent confirmations.
7. Entry, stop, target, or reward/risk derived from unadjusted, stale, partial,
   or unclosed bars.
8. Broker execution, order placement, account access, position management, or
   executable quantity.

## Current State Ceiling

At the currently recorded R0 baseline, zero source contracts are
gate-authorized and `sourceActivationReady=false`. Product and UI work may
expose research visibility, source health, WATCH, WAIT, and REJECT behavior,
but it cannot claim live scanner confirmation.

CONFIRMED remains unavailable until its independent source activation,
evidence, closed-bar, replay, and milestone acceptance contracts pass.

This file is the final merge verdict for combining File A with Discovery/Options
product design under File B (Hybrid) detail. It does not replace, reorder, or
weaken File A's safety and acceptance rules.

## Maximum Signal Utilization Architecture

No downloaded value or derived signal is silently discarded. Every signal is assigned one or more explicit jobs: discovery, direction, timing, context, risk, research scenario, and diagnostics.

Every normalized signal preserves its source key, dataset root, instrument, profile, role, evidence family, correlation group, direction, raw and normalized values, data and retrieval timestamps, freshness, quality, formula version, lineage hash, state permission, and warnings.

### M-Factor utilization

M-Factor is an opportunity-priority and decomposition surface. It shows the observed rank, data coverage, strongest, weakest, and opposing components, sector-relative comparison, trend, and state ceiling. It is not win probability and cannot directly produce CONFIRMED. It may prioritize candidates for expensive enrichment.

### PKScreener utilization

The pinned isolated PK adapter may contribute breakout, VCP/compression, momentum, reversal, moving-average support, candle-pattern, ATR, volatility, direction, and invalidation observations. Agreement with native structure emits `TECHNICAL_CONSENSUS`; disagreement emits `TECHNICAL_CONFLICT`. PK failure does not stop official-source discovery or bypass canonical gates.

### Macro and institutional utilization

FRED, CFTC, EIA, WGC, AMFI, NSDL, FII/DII, and related delayed sources may produce versioned sector, commodity, or instrument sensitivity estimates when point-in-time history is sufficient. Driver direction, sensitivity, effect, publication date, and data lag remain visible. These are context modifiers unless a separately validated contract authorizes a stronger role.

### Correlated-signal utilization

Correlated signals are not deleted. Within each atomic correlation group and evidence family they calculate family strength, agreement, dispersion, coverage, and one representative claim. Volume, delivery, turnover, futures volume, and option volume can all improve `FLOW_ACTIVITY` quality without becoming independent confirmation votes.

### Missing-evidence utilization

Missing data is a diagnostic and state-ceiling input. The UI exposes observed score, coverage, conservative score, best-case sensitivity, missing required inputs, and state ceiling. Missing-weight renormalization cannot silently increase conviction.

### Tiered derivatives utilization

1. Cheap universe pass: F&O bhavcopy, futures OI, basis, volume, MWPL, and ban.
2. Medium shortlist pass: PCR history, OI concentration, rollover, and futures.
3. Deep candidate pass: chain quality, IV, skew, Greeks, OI walls, max pain, expiry behavior, and liquidity.

One `OPTIONS_CONTEXT` package reports `SUPPORT`, `WEAKEN`, `CONFLICT`, or `UNKNOWN`, plus call wall, put wall, PCR trend, IV condition, expiry risk, and chain quality. Options cannot independently produce CONFIRMED.

### Unverified-source utilization

Unverified and research-only sources remain available for research discovery, anomaly detection, cross-source comparison, parser-change detection, and official-evidence gap discovery. Their stored output is labeled `RESEARCH_SIGNAL` with verification and freshness limitations and cannot exceed its state-permission ceiling.

### Canonical candidate output

Every evaluated instrument produces one versioned object containing opportunity rank, evidence direction, timing readiness, independent-family support, opposition, coverage, freshness, conflicts, risk, macro and sector effects, PK consensus, options context, research scenario, public state, selection reason, and exact WAIT or REJECT reason.

### Trader presentation

All fourteen retained tools read from the same candidate and lineage contracts. Selecting an instrument exposes why selected, why now, supporting and opposing signals, market/sector/macro effects, OI/options, PK/native agreement, authorized research levels, risk and invalidation, missing/stale/unverified/conflicting data, and complete source and calculation lineage.

This architecture uses every available signal while keeping discovery rank, evidence strength, coverage, public state, and research scenario separate.

## Options Intelligence Integration

The final hybrid explicitly incorporates these companion plans:

1. `D:\TrendForge\grok_plan\shadowflow_deep_dive.md`
2. `D:\TrendForge\grok_plan\convexity_intelligence_engine.md`

Only governing sections `0-17` of each file define implementation contracts. Material under a `LEGACY ARCHIVE` banner remains available in a versioned `RESEARCH_LEGACY` catalog for study, fixture comparison, and possible future promotion. Legacy formulas, scores, intent labels, or pattern bibles cannot enter the production state path without a separately approved feature contract, point-in-time fixtures, replay, and acceptance evidence.

### Authority and package boundary

`shadowflow_deep_dive.md` governs the shared options-package contracts, identity, source use, quality, carry, IV, Greeks, flow, storage, replay, and operational behavior. `convexity_intelligence_engine.md` governs the `OPT_SURFACE` studies inside that same package.

There is one package, one source path, one snapshot identity, one parent-family cap, and one master TrendForge state machine:

```text
backend/trendforge_api/options_intelligence/
    contracts.py
    source_adapter.py
    snapshot_builder.py
    identity.py
    quality.py
    carry.py
    iv.py
    greeks.py
    flow.py
    surface.py
    surface_interpolation.py
    surface_quality.py
    surface_studies.py
    fusion.py
    replay.py
    storage.py
    observability.py
    api.py
    patterns.py
```

`patterns.py` begins as a registry/stub. Legacy studies may be registered as research candidates, but they remain unrouted until their individual eligibility and replay contracts pass. Do not create separate ShadowFlow or CIE services, databases, fetchers, scores, state machines, or independent confirmation votes.

### Shared snapshot contract

Flow and surface calculations consume the same immutable economic snapshot:

```text
OptionsSnapshotBundleV1
    snapshot_bundle_id
    underlying_id
    contract_master_version
    expiry_set
    spot_observation_id
    futures_observation_ids
    option_observation_ids
    source_result_ids
    raw_hashes
    dataset_root_ids
    market_session
    data_date
    published_at
    available_at
    retrieved_at
    freshness_state
    revision_id
    parser_version
    quality_version
```

Flow and surface bundle mismatch produces `WAIT_SNAPSHOT_BUNDLE_MISMATCH`. Values from different timestamps, expiries, contract masters, or revision states cannot be averaged into one package.

### Source and runtime behavior

The options package does not own a second NSE session or independent network budget. It uses shared source adapters, request budget, cache, retry policy, circuit breaker, raw artifact store, and source-health contracts.

```text
background collectors
  -> normalized F&O and chain snapshots
  -> shortlist request
  -> point-in-time bundle selection
  -> per-feature quality and eligibility
  -> flow and surface studies
  -> one capped package result
```

Full option-chain work runs only for the eligible shortlist or an explicit on-demand inspector request. Cheap flow-lite may run before chain activation using F&O bhavcopy, futures OI, basis, volume, rollover, MWPL, and ban data. Chain-dependent outputs remain `UNKNOWN` until their chain contract passes.

### Study utilization ladder

All proposed studies remain registered with explicit maturity and permission:

| Study | Initial use | Promotion requirement |
|---|---|---|
| OI PCR and volume PCR | Research display and context | Complete chain and expiry coverage |
| Max pain | Index-first EOD reference and sensitivity | Liquid chain, formula verification, no target language |
| Unsigned gamma concentration | Surface concentration | Stable Greeks and settlement-compatible model |
| Raw parity/monotonicity/convexity | Chain-quality diagnostics | Valid bid/ask and contract identity |
| OI velocity | Flow-lite research | Stable interval alignment |
| Roll migration | Futures/expiry context | Expiry identity and continuous history |
| PCR/skew conflict | Conflict observation | Eligible PCR and skew from same bundle |
| RR25/Fly25 | Research surface study | Bracketed liquid-node fixtures |
| Term structure | Research context | Multi-expiry time alignment |
| Variance-risk-premium proxy | `POSTPONE` / research context | Same-horizon implied-variance method, PIT realized-variance forecast, calibration, costs and tail-risk controls |

| Theta/Vanna/Charm/Vomma/Speed | Modeled sensitivities | Exercise, settlement, carry, IV, and replay proof |
| Legacy ShadowFlow/CIE patterns | `RESEARCH_LEGACY` output | Individual contract, parity fixtures, PIT replay |

No registered study is deleted. Unpromoted studies remain visible in the research inspector with maturity, data-quality, and permission labels.

### Hard options semantics

1. OI does not reveal buyer, seller, writer, hedge, dealer, or institution.
2. Gamma multiplied by OI is unsigned concentration unless a separately proven position-sign model exists. It is not dealer GEX.
3. Modeled Greeks and higher-order sensitivities are model outputs, not observed flow.
4. High or low PCR is not universally bullish or bearish.
5. Max pain is an OI-derived reference, not an automatic target or defended level.
6. EOD max pain and intraday pin research are separate outputs.
7. A fitted surface does not prove that raw quotes are trustworthy.
8. Raw, interpolated, and fitted nodes are different objects with different eligibility.
9. A partial discovery feed cannot become a valid volatility surface.
10. Quality is feature-specific. Valid PCR does not make invalid skew or Greeks usable.
11. Physical-settlement stock options and European-model assumptions require an explicit compatibility decision.
12. Surface conflicts produce `UNKNOWN`, `CONFLICT`, or `WAIT`; only a governed safety rule may produce `REJECT`.
13. Full Theta includes dividend/carry terms and declared calendar/trading-time conventions; near-expiry model sensitivity can become `UNKNOWN`.
14. Delta-hedged gamma/variance attribution is path-, hedge-frequency- and cost-dependent. It is not directional P&L or an observed market flow.
15. A variance-risk-premium proxy compares synchronized same-horizon risk-neutral implied variance with a PIT physical expected-realized-variance forecast.
16. Positive or negative VRP, IV-versus-RV, backwardation or contango cannot automatically authorize option sale/purchase, direction, state, quantity or execution.

### Family and fusion model

```text
DERIVATIVES_FLOW
    futures OI
    basis
    rollover
    F&O volume
    OI velocity

OPTIONS_SURFACE
    chain quality
    PCR
    IV and skew
    Greeks
    concentration
    OI walls
    max pain
```

Both sit under capped parent family `DERIVATIVES_CONTEXT`. Every detailed signal contributes to family strength, agreement, dispersion, coverage, and conflict, while the parent produces at most one independent package contribution.

The final `OptionsPackageSupportV1` result is `SUPPORT`, `WEAKEN`, `CONFLICT`, or `UNKNOWN`. Options and derivatives never independently own direction or CONFIRMED.

### Failure and null behavior

The package distinguishes:

```text
VALID_EMPTY
WAIT_CHAIN
SURFACE_UNAVAILABLE
WAIT_SNAPSHOT_BUNDLE_MISMATCH
WAIT_CONTRACT_IDENTITY
WAIT_EXPIRY_ALIGNMENT
WAIT_SETTLEMENT_UNKNOWN
WAIT_EXERCISE_STYLE_UNKNOWN
WAIT_CARRY_INPUT
WAIT_UNDERLYING_STALE
WAIT_QUOTE_QUALITY
WAIT_MODEL_INCOMPATIBLE
INPUT_INCOMPLETE
CONFLICT
```

Missing IV, OI, quote, strike, expiry, carry, or model inputs remain null with reason codes. They never become zero.

### Options API and trader presentation

```text
GET /api/v1/options/{underlying}/context
GET /api/v1/tools/oi_analysis
GET /api/v1/tools/oi_tracker
GET /api/v1/tools/strike_explorer
GET /api/v1/tools/expiry_prediction
```

The primary radar shows compact derivatives support, conflict, quality, and freshness. The hidden inspector exposes snapshot bundle and raw hashes, contract and expiry identity, flow-lite observations, PCR timeline, OI walls and concentration, max-pain reference and sensitivity, raw/interpolated/fitted surface nodes, IV/skew/eligible Greeks, feature-level quality and null reasons, formula/model versions, package cap, and state permission.

Any user-facing `confidence` value means component agreement or data coverage, not probability of profit. Prefer `ComponentAgreement`, `DataQuality`, and `CalibrationStatus`.

### Options acceptance tests

At minimum, verify:

1. Flow and surface bundle mismatch yields `WAIT_SNAPSHOT_BUNDLE_MISMATCH`.
2. Empty chain preserves flow-lite while surface remains unavailable.
3. Stale parent bundle invalidates all dependent surface outputs.
4. Missing IV remains null, not zero.
5. Zero call OI does not divide by zero in PCR.
6. Duplicate expiries or strikes fail identity validation.
7. Raw, interpolated, and fitted nodes cannot be substituted silently.
8. Invalid put-call parity lowers raw surface quality.
9. Non-monotonic or non-convex raw quotes remain visible as diagnostics.
10. Max pain is labeled as a reference, not a target.
11. EOD max pain cannot be presented as intraday pin evidence.
12. Single-stock max pain cannot outrank liquid-index evidence without proof.
13. Unsigned gamma concentration cannot be labeled dealer GEX.
14. Settlement or exercise-style uncertainty blocks state-eligible Greeks.
15. RR25/Fly25 requires valid bracket nodes.
16. Multi-expiry term structure requires aligned timestamps.
17. Futures flow and options surface respect one parent cap.
18. A valid subfeature does not validate an ineligible sibling feature.
19. Legacy CIE, ShadowFlow, synergy, or combined scores cannot route into the master state.
20. Legacy studies remain visible as research outputs with zero state permission.
21. Options-package failure cannot stop official discovery or native structure.
22. Shortlist budget prevents uncontrolled full-universe chain fetching.
23. Every displayed value traces to its bundle, raw hash, and formula version.
24. Replay reproduces the package result from the same point-in-time bundle.

## Guidance Reconciliation

The final hybrid retains and reconciles all previously supplied guidance:

| Guidance area | Final treatment |
|---|---|
| Complete link inventory | Every source receives a role, maturity, profile binding, and permission or explicit research-backlog status. |
| Real-time source use | Background cadence-aware collectors feed immutable local snapshots; scans do not call every link. |
| Five scanner modes | Intraday, Swing, Options/F&O, Positional, and MCX remain profile-driven. |
| Official E1 discovery | Sector, volume, liquidity, OI, deals, catalysts, ownership, and safety feed official discovery. |
| Native E2N discovery | Closed-bar trend, breakout, compression, reversal, and harmonics remain native observations. |
| PK E2P discovery | Full useful PK scanner, pipe, monitoring, backtest-research, parity, and native-promotion outputs remain available. |
| PK operation | Pinned batch is default; optional isolated local shadow service uses the same sanitized output contract. |
| M-Factor | Multi-output opportunity, direction-attention, coverage, conflict, freshness, risk, and scenario-quality scorecard. |
| Correlated signals | All inputs improve family strength/agreement/dispersion; they do not create duplicate independent votes. |
| Missing evidence | Coverage, conservative score, sensitivity range, missing requirements, and state ceiling remain visible. |
| Macro/institutional | Used for lag-aware regime, sector, commodity, and validated sensitivity context. |
| G1-G8 integrity | Retained and typed individually as veto, gate, warning, evidence, or diagnostic. |
| Fourteen tools | All retained under Radar, Discovery, Derivatives, Research, and System Health workspaces. |
| Verify Strip | Inputs, timestamps, source keys, formula versions, outputs, hashes, and null reasons are available on every tool. |
| Research scenarios | Trigger, invalidation, stops, objectives, costs, and reward/risk are retained when their closed-bar contract passes. |
| Public states | WATCH, WAIT, CONFIRMED, and REJECT remain the only public states. |
| Candidate lifecycle | One immutable CandidateDecision and event history preserve every transition and correction. |
| Progressive activation | Verified sources power vertical research slices without treating the entire inventory as globally authorized. |
| Shadow live feeds | May display and rank research with `can_support_confirmed=false` until replay and activation pass. |
| Options intelligence | ShadowFlow flow contracts and CIE surface studies share one bundle, package, parent cap, store, replay, and state ceiling. |
| MCX | Contract master, expiry, roll, lot, tick, session, limits, delivery, currency, and global publication timing remain mandatory. |
| Validation | Fixture, failure, PIT, revision, replay, OOS, calibration, frontend, and runtime-observation tests remain required. |

Nothing in this reconciliation claims that all sources, PK capabilities, options studies, tools, or scenarios are already implemented or production-ready. Each capability remains subject to its recorded maturity, quality, permission, and acceptance evidence.

## Options Intelligence Governing Detail Addendum

This addendum closes omissions found by re-reading the complete governing zones of `shadowflow_deep_dive.md` v9.2 lines 1-465 and `convexity_intelligence_engine.md` v7.1 sections 0-17. The canonical short reference is `D:\TrendForge\docs\OPTIONS_INTELLIGENCE_PLAN.md`.

The Grok files govern only the options-intelligence module. File A and this final merge plan continue to own product order, source activation, public states, and acceptance. Internal `OI-0` through `OI-8` steps are module checklists mapped into the authoritative `R0-R18` roadmap; they are not a second project roadmap.

### Existing component reuse

| Existing component | Required use |
|---|---|
| `derivatives_engine.py` | Characterize and reuse dividend-aware pricing, IV solver, and first-order Greeks; do not add a second solver. |
| `selection/options_domain.py` | Reuse PIT identity/completeness checks, PCR/walls/max-pain context, unknown handling, and state ceiling. |
| NSE session/source layer | Extend bounded session and structured source-result contracts. |
| Existing persistence | Extend governed storage; do not require a PostgreSQL-only replacement. |
| Existing state machine | Sole owner of WATCH, WAIT, CONFIRMED, and REJECT. |
| Existing frontend | Extend current frontend; no framework rewrite prerequisite. |
| `openalgo_client.py` | Disabled read-only comparison boundary; agreement cannot grant authority. |

Compatibility adapters may preserve existing API consumers during migration. Legacy scores, synergy, and duplicate state paths cannot execute beside the unified package.

### Versioned source runtime profile

Every options source or endpoint must bind:

```text
source_key
base_url
warmup_urls
referer_policy
user_agent_policy
accept_policy
minimum_interval
request_timeout
retry_limit
retryable_statuses
cookie_refresh_triggers
block_signatures
response_size_limit
freshness_profile_id
budget_profile_id
circuit_breaker_profile_id
cache_profile_id
```

Cookie names are discovered and preserved by the session rather than permanently hardcoded. Stable browser-compatible identity is allowed; fingerprint rotation, CAPTCHA bypass, and access-control evasion are not.

Block detection combines status, redirect, content type, body signatures, and expected schema. `Retry-After` is respected; otherwise bounded exponential backoff with jitter applies. Failed warm-up or cookie refresh remains an explicit failure.

### Adaptive request-budget contract

Every options scan records:

```text
budget_profile_id
budget_capacity
budget_remaining
requests_attempted
requests_completed
requests_retried
requests_blocked
requests_rate_limited
requests_served_from_valid_cache
symbols_planned
symbols_completed
symbols_partial
symbols_not_attempted
```

The scheduler uses shortlist-first retrieval, source-specific token buckets, bounded concurrency, and jitter. Budget exhaustion produces `WAIT_RATE_LIMIT_BUDGET_EXHAUSTED`; remaining symbols are not silently omitted and the scan cannot claim complete coverage.

Circuit breakers are scoped per source/endpoint unless observed evidence proves a shared failure. States are `CLOSED`, `OPEN`, and `HALF_OPEN`. Threshold, window, cooldown, probe count, and closing criteria are versioned profiles derived from observation. Longer server `Retry-After` overrides the local cooldown.

### Cache and schema-drift contract

Each cache entry stores:

```text
source_event_time
retrieved_at
cached_at
expires_at
payload_hash
schema_version
source_result_state
cache_profile_id
```

Invalidators include contract/corporate-action version changes, market-phase transitions, schema changes, source corrections, administrative invalidation, and freshness expiry. `VALID_EMPTY` is not automatically a cache failure. A lineage-valid cache can support a calculation only while its use-specific freshness contract passes.

On schema mismatch:

1. Retain sanitized raw evidence.
2. Stop affected normalization and derived features.
3. Keep unaffected sources and symbols visible as partial.
4. Emit structured operations reasons.
5. Replay fixtures against the proposed parser update.
6. Version the schema and normalizer.
7. Require regression proof before reactivation.

A grace parser cannot guess renamed fields on a state-support path.

### Source, option-row, feature, and package DTOs

Every fetch result preserves endpoint/request identity; request, response, event, publication, and availability timestamps; HTTP/content metadata; parser state; schema version; row count; explicit empty semantics; raw hash/path; warnings; errors; attempts; budget consumption; and cache provenance.

A normalized option row preserves exchange, segment, underlying, instrument, contract, expiry, strike, option side, currency, and dataset root. ISIN, event/publication time, OI change, exchange IV, quotes, exercise style, and settlement style remain nullable with reason codes when unproven. Raw and normalized values are stored separately and numerical precision must be appropriate to each field.

Every surface feature returns:

```text
value
status
unit
method
formula_version
input_snapshot_bundle_id
source_keys
dataset_roots
observed_at
available_at
quality_dimensions
null_or_wait_reasons
state_eligible
```

`OptionsPackageSupportV1` contains:

```text
schema_version
symbol
instrument_identity
snapshot_id
decision_time
available_at
source_activation_ready
gate_authorized
research_shadow_only
discovery_rank
discovery_rank_version
closed_structure_direction
options_support
state_ceiling
reason_codes
options_package_quality
surface_summary
flow_summary
dataset_roots
correlation_groups
source_results
conflict_flags
formula_versions
feature_versions
lineage_links
generated_at
```

Enums and nullability live in generated Pydantic/OpenAPI contracts. Unsupported schema versions are rejected by consumers.

### Identity, timing, continuity, and support data

The PIT instrument master maps exchange symbol, normalized symbol, series, ISIN, F&O eligibility, underlying type, contract aliases, effective-from/to, and source authority. Suffix removal is mapping-driven; ambiguity produces `IDENTITY_CONFLICT`.

Calendar handling stores actual calendar time, trading-session time, expiry-session rules, and declared day-count convention separately. Holiday and weekend effects cannot be attributed only to Theta.

Contract-master revisions, exchange circulars, and corporate actions reconcile ex-date, adjustment factor, lot/strike changes, aliases, exercise style, settlement style, and same-economic-contract continuity. Physical settlement is a regime/risk fact, not proof that max pain is invalid.

Required safety and eligibility facts are rechecked immediately before state publication. Mid-scan changes invalidate affected pending assessments and create a new PIT result without rewriting earlier observations.

Rate inputs use a governed PIT Government of India curve or approved fallback hierarchy. If approved inputs fail, carry-dependent outputs become unknown or WAIT. Discontinued MIFOR is prohibited.

Observed futures basis requires a validated matching contract and aligned quote. Parity-implied forward is a separate modeled fact and cannot be labeled observed basis.

SLB may be a timestamped borrow-pressure proxy only after source proof. It is not exact borrow fee, exact short interest, or confirmation authority.

Cross-sectional baseline jobs cover liquidity, OI velocity, volume/OI, PCR, skew, and concentration by comparable universe, DTE, expiry, and market phase. Baselines record universe version, sample count, transform, winsorization, lookback, available-at time, and revision version and cannot use future constituents.

### Parity, IV, quality, and interpolation

Generic forward parity is:

```text
C - P = exp(-rT) * (F - K)
F_implied = K + exp(rT) * (C - P)
```

Implied forward is estimated from several liquid paired strikes using a robust statistic. Parity validates paired quotes, alignment, carry, and forward assumptions; it does not prove IV-solver correctness.

With valid bid/ask quotes:

```text
observed_parity_low  = call_bid - put_ask
observed_parity_high = call_ask - put_bid
theoretical_parity   = exp(-rT) * (F - K)
```

The theoretical value is checked against the observed interval plus separately modeled uncertainty for underlying/futures spread, timestamp skew, tick size, and carry quality. Store the interval, uncertainty components, residual, and tolerance-profile version. Do not use a universal `1.5 * max(spread)` rule.

IV priority is valid exchange IV as an observation, independent midpoint solution, then liquidity/recency-qualified LTP solution. Solver failure is `UNKNOWN`. Validate price bounds, convergence, repricing residual, tick tolerance, and timestamps. There is no universal theoretical maximum IV; numerical bounds are versioned safeguards.

IV node classes remain distinct:

```text
OBSERVED_EXCHANGE_IV
SOLVED_MIDPOINT_IV
SOLVED_LTP_IV
INTERPOLATED_IV
FITTED_IV
UNKNOWN_IV
```

Interpolated nodes are lower authority and cannot become separate evidence. Fitted nodes remain diagnostic until promoted.

Quality dimensions remain separate: authority, freshness, schema, identity, completeness, quote quality, temporal alignment, carry quality, and cross-sectional consistency. Mandatory failures are gates, not hidden inside an average quality score. No universal freshness or completeness threshold is assumed.

Surface interpolation uses a pinned method, minimum liquid strikes, declared coordinates, residual limits, and no silent extrapolation.

### Deterministic RR25 and Fly25

For each wing:

1. Calculate eligible raw-node IV and model Delta with one carry/model version.
2. Sort nodes by absolute Delta.
3. Require two liquid nodes bracketing absolute Delta `0.25` on each wing.
4. Reject duplicate/nonmonotonic coordinates or excessive versioned gaps.
5. Linearly interpolate total variance `w = IV^2 * T` against absolute Delta.
6. Do not extrapolate.
7. Calculate:

```text
RR25  = IV_25_call - IV_25_put
Fly25 = 0.5 * (IV_25_call + IV_25_put) - IV_ATM
```

Store bracket nodes, interpolation weight, coordinate gap, residual diagnostics, and method `LINEAR_TOTAL_VARIANCE_ABS_DELTA_V1`. Missing brackets produce `SKEW_COVERAGE_UNKNOWN`. A separately labeled moneyness-skew proxy cannot impersonate RR25 and remains correlated with it.

### Greek and gamma-concentration stability

Reuse and characterize `derivatives_engine.py` price, Delta, Gamma, Theta, Vega, and Rho against analytical and finite-difference fixtures before integration.

State-eligible Greeks require known exercise and settlement style. Model incompatibility produces `GREEKS_MODEL_MISMATCH`. Near-expiry eligibility uses a versioned stability profile covering positive T, quote/tick quality, IV residual, finite-difference error, sensitivity conditioning, and timestamp alignment; failed stability produces `GREEKS_UNSTABLE_NEAR_EXPIRY`.

Canonical cash-Gamma concentration is:

```text
cash_gamma_for_1pct_spot_move_inr = gamma * OI * lot_size * spot^2 * 0.01
cash_gamma_for_1pct_spot_move_inr_crore = cash_gamma_for_1pct_spot_move_inr / 10_000_000
```

It is approximate hedge-notional change for a one-percent spot move, not Gamma P&L. Calls and puts remain unsigned and separate. No extra `*100` factor or dealer sign is permitted on the state path. Dealer sign remains `SCENARIO_ONLY_NOT_OBSERVED_POSITION`.

Higher-order Greeks remain research outputs until first-order, carry, alignment, finite-difference, and OOS gates pass.

### PCR, concentration, max pain, term, and surface diagnostics

OI PCR and volume PCR are calculated per expiry and declared strike-inclusion policy. Zero denominator is `UNKNOWN`. Store coverage and inclusion policy.

Gamma concentration is reported by strike, normalized moneyness, expiry, and distance from forward. Migration compares matched economic coordinates across valid snapshots. Dust sensitivity uses versioned inclusion/sensitivity analysis rather than a permanent OI cutoff.

Max pain retains the conventional all-valid-strike result and sensitivity variants under documented liquidity/coverage policies. Store included/excluded strikes, coverage, OI totals, policy version, conventional result, sensitivity range, and migration status. Do not silently redefine it with a fixed OI floor or +/-15% band.

The Expiry/Strike tools show conventional value, sensitivity range, policy version, `EOD` versus `INTRADAY_RESEARCH`, and `NOT A FORECAST GUARANTEE` with the formula.

Term-structure comparisons require aligned quote times, carry versions, underlying observations, and normalized coordinates. Dynamic strikes map through forward log-moneyness and contract continuity. Changing coverage cannot masquerade as surface movement.

Monotonicity, convexity, parity, wing coverage, quote spreads, and fitting residuals are quality diagnostics, not independent directional evidence. Raw defects remain visible after fitting.

### Explicit conflict behavior

| Situation | Result |
|---|---|
| Flow and surface use different bundles | `WAIT_SNAPSHOT_BUNDLE_MISMATCH` |
| Surface opposes closed structure | `WAIT_STRUCTURE_CONFLICT` |
| Surface components disagree materially | `WAIT_OPTION_SURFACE_CONFLICT` |
| Raw surface invalid but flow valid | Surface unknown; flow descriptive and parent-capped |
| Several required surface conflicts | Preserve every reason and aggregate to WAIT |
| Governed hard safety veto | REJECT |

Options disagreement alone cannot become `REJECT_OPTIONS_CONFLICT`.

### Storage, API, replay, and operations

Raw payloads remain immutable native files with sanitized sidecars. Normalized analytical snapshots use versioned Parquet/Arrow schemas. Lineage and state records extend the existing governed database. Compatible nullable additions are allowed; rename, type, or semantic changes require a schema version plus migration/replay proof. Decision records and revisions are append-only.

Logical entities include source fetch, instrument-master version, option snapshot/quote, underlying observation, contract/corporate-action version, carry input, baseline version, surface/flow metric, pattern observation, package support, evidence claim, replay outcome, surface node, coordinate map, quality observation, feature, conflict, and study observation.

Canonical detailed routes are:

```text
GET /api/v1/options-intelligence/symbol/{symbol}/context
GET /api/v1/options-intelligence/symbol/{symbol}/surface
GET /api/v1/options-intelligence/symbol/{symbol}/lineage/{snapshot_id}
```

The earlier `/api/v1/options/{underlying}/context` may remain a compatibility facade that returns the same versioned parent DTO; it cannot become a second implementation.

Intraday replay requires archived intraday chains. EOD UDiFF/bhavcopy supports EOD references and baselines only. Replay uses matched coordinates, PIT carry/master/universe versions, quote/spread availability, cost scenarios, corporate-action continuity, and competing-event handling. Raw and fitted studies are evaluated separately against simpler OHLCV/liquidity baselines with sample size and uncertainty by DTE, regime, expiry, and liquidity.

Outcome records distinguish completed horizon, missing future data, halt, delisting/contract termination, corporate-action discontinuity, safety intervention, forced termination, and competing event. Informative interruptions are not silently right-censored.

Operations emit structured redacted logs and metrics for run, source, endpoint, stage, symbol/contract, profile versions, attempts, latency, bytes, result state, budget, cache, breaker, rows, warnings, reasons, and lineage. Operations UI exposes planned/attempted/completed/partial symbols, source-state counts, budget, cache age, breaker state, schema mismatches, and next probe.

A valid-empty storm is investigated through calendar, expected universe, cross-source health, previous history, schema/version, and symbol distribution. It is not automatically classified as either outage or success.

REST polling is the initial transport. SSE/WebSocket may be added only after measured latency or interaction requirements justify it.

### Numeric and surface-inspector contract

Every numeric field carries `value`, `status`, `unit`, `observed_at`, `source`, and optional reason. Observed zero renders as `0`; missing or invalid renders as `UNKNOWN`. Stale values show age and visual degradation.

The Surface inspector shows raw nodes separately from interpolated/fitted nodes; expiry, strike, forward log-moneyness, Delta coordinate, and coverage; IV method and interpolation brackets; RR25/Fly25, term, PCR, gamma concentration, and max-pain sensitivity; quote/parity/arbitrage defects; carry, calendar, lot, settlement, and corporate-action assumptions; status/reasons; units, versions, roots, and lineage. Surface values remain visually neutral unless independent closed structure supplies direction.

### Internal module sequence

The internal options checklist is:

1. `OI-0` contract and disposition freeze.
2. `OI-1` thin vertical for one liquid index and five liquid stocks.
3. `OI-2` source budgets, breaker, cache, schema recovery, safety revalidation, and observability.
4. `OI-3` carry, alignment, parity, IV residuals, first-order Greeks, and units.
5. `OI-4` surface/flow facts, PIT baselines, and one package cap.
6. `OI-5` five versioned research hypotheses only.
7. `OI-6` PIT replay, costs, competing events, baselines, and holdout.
8. `OI-7` radar/inspector and API verification.
9. `OI-8` measured scaling at 50/100/250 within observed source limits.

These steps execute only when their mapped authoritative `R0-R18` milestone permits them.

### Stable options test adoption

All `CIE7-001` through `CIE7-028` tests in CIE v7.1 section 16 are adopted by reference with their exact meanings and IDs. The consolidated ShadowFlow section 15 coverage is also mandatory for transport, identity, math, family caps, state ceilings, PIT/revision/cost/replay, lineage, API-version, and UI agreement behavior.

Additional final-plan tests must prove source-profile versioning, request-budget accounting, circuit-breaker recovery, valid-cache use, cache invalidation, schema-drift quarantine, safety revalidation immediately before publication, no future constituents in baselines, no silent carry fallback, observed-versus-implied basis separation, SLB proxy labeling, feature-level eligibility, no duplicate options vote, and accurate partial-scan coverage.

### Options definition of done

The options integration is complete only when:

1. One package replaces duplicate runtime paths.
2. Legacy material is quarantined from the state path but retained for research comparison.
3. Source, session, result, budget, cache, breaker, and schema contracts are observed and bounded.
4. Identity, timing, carry, continuity, IV, Greeks, units, and feature eligibility are proven.
5. Partial feeds cannot enter full-surface calculations.
6. Flow and surface share one snapshot and capped parent influence.
7. Initial studies remain versioned, traced hypotheses.
8. PIT replay passes leakage, cost, competing-event, and holdout tests.
9. API/UI render unknown, zero, stale, conflict, ceiling, coverage, units, and lineage correctly.
10. Options never independently own CONFIRMED.
11. `BUILD_STATUS.md` and `VALIDATION.md` record observed behavior and remaining limits.

Until those gates pass, the product must display:

> Experimental options-flow and options-surface research evidence. Fail-closed, non-executable, and not a validated trading edge.

### Legacy research utilization

Legacy and corrected-away concepts are not deleted. `Shadow_Score`, `Combined_Score`, synergy multipliers, fixed 84/88 gates, dealer-sign GEX, intent labels, fixed OI floors, fixed max-pain bands, fixed parity multipliers, default-zero dividend assumptions, fixed TTL/rate constants, dual-voter behavior, and higher-order pattern catalogs remain registered as `RESEARCH_LEGACY` or negative-control hypotheses.

They may produce inspector-only comparison outputs and CI negative fixtures. They have zero state permission and cannot impersonate the corrected formulas. Promotion requires an independent feature definition, versioned inputs, PIT replay, OOS incremental value, and a manual recorded decision.

## All-Source Research Universe And Derivatives Decision Laboratory Addendum

### Additive status

This section is additive. It does not delete, replace, weaken, or reorder any earlier rule in this file or File A. It makes the use of every available source, every resolved stock, PKScreener, option-chain facts, strike analytics, Gamma, IV, and Greeks operationally clear.

The `FMR-*` IDs below are plan-local traceability IDs. Before implementation, map them to the applicable File A `R0-R18` requirement and acceptance IDs. They do not create another build order.

### Owner crosswalk mirror

| Final Merge alias | R owners | Linked requirements |
|---|---|---|
| `FMR-001` | `R0`, `R2`, `R16` | None |
| `FMR-002` | `R0`, `R2`, `R3`, `R8`, `R9`, `R15`, `R16` | None |
| `FMR-003` | `R12` | None |
| `FMR-004` | `R12`, `R16` | None |
| `FMR-005` | `R12`, `R16` | None |
| `FMR-006` | `R12`, `R16` | None |
| `FMR-007` | `R3`, `R12`, `R15` | None |
| `FMR-008` | `R4`, `R7`, `R12`, `R17` | None |
| `FMR-009` | `R15` | None |
| `FMR-010` | Applicable `R0-R18` | None |
| `FMR-011` | `R15`, `R16`, `R18` | `FTR-034`, `STO-017`, `UI-009` |

This table mirrors File A section 25.21. Only `R owners` select work; linked
requirements are obligations, not milestones. Any mismatch fails governance validation.

### FMR-001: Use every source and every resolved stock for research

`Use all links` means:

1. Attempt every permitted canonical source binding using its schedule, market phase, request budget, and source contract.
2. Preserve every successful artifact and every explicit failure state.
3. Normalize every valid row and resolve every stock, index, commodity, and contract identity without guessing.
4. Put every resolved stock into a versioned `ResearchUniverseSnapshotV1`, even when it is not shortlisted.
5. Calculate every feature whose identity, freshness, completeness, quality, and point-in-time inputs pass.
6. Preserve unavailable, stale, conflicting, unsupported, and invalid features as `UNKNOWN` with reasons. Never replace them with zero.
7. Show why a stock was included, not shortlisted, not attempted for expensive enrichment, or prevented from reaching a higher state.

No fixed count such as 100 or 105 is permanent. Each run uses a versioned `SourceBindingSetV1` compiled from the canonical registry. Every source binding has one or more roles:

```text
UNIVERSE_IDENTITY
DISCOVERY
CAUSE_CATALYST
SPONSOR_OWNERSHIP
STRUCTURE_PRICE
FLOW_ACTIVITY
DERIVATIVES_CONTEXT
TRADABILITY_RISK
REGIME_CONTEXT
CROSS_VALIDATION
DIAGNOSTIC_ONLY
RESEARCH_ONLY
```

A source can perform several research jobs, but one dataset root cannot create several independent confirmation votes. Non-stock sources attach to market, sector, commodity, expiry, or macro context through a versioned PIT exposure map; they are not forced into fake stock rows.

### FMR-002: Complete all-stock research flow

**Story labels only.** The `S0–S9` block below is a **product narrative** for all-stock research.  
**Build authority remains File A §9 `SEL-001..010`.** Full stage crosswalk: File A **§9.3**.  
Do not implement “FMR S4” as File A structure, or invent a third S-map.

| FMR-002 story | Maps primarily to File A build |
|---|---|
| S0 Run truth | S0 (+ activation/publication ceilings) |
| S1 Collection | S0/S1 transport + raw archive |
| S2 Identity / universe | S1 |
| S3 Cheap pass | **S3** cheap discovery |
| S4 Shortlist | Budget cut after S3 (not File A S4) |
| S5 Closed structure | **S4** structure pack |
| S6 Deep derivatives | **S5** enrichment (options/futures portion) |
| S7 Evidence resolution | **S6** family resolver |
| S8 Research scenario | Research geometry only; qty never; after gates |
| S9 Radar / inspector / PIT journal | **S7** state display + **S8** persist + UI; offline PIT = File A **S9** |

```text
S0 RUN TRUTH
  RunManifestV1 + SourceBindingSetV1 + data_mode + session phase
  + source activation + gate permission + publication permission

S1 ALL-SOURCE COLLECTION
  VALID_DATA / VALID_EMPTY / BLOCKED / TRANSPORT_ERROR / PARSE_ERROR
  -> immutable raw artifact and lineage

S2 IDENTITY AND COMPLETE UNIVERSE
  Symbol + ISIN + series + sector + F&O eligibility + contracts
  -> ResearchUniverseSnapshotV1
  -> preserve unresolved and ambiguous rows separately

S3 CHEAP PASS FOR EVERY RESOLVED STOCK
  Liquidity/activity + sector-relative position + price availability
  + catalyst/sponsor availability + restrictions + cheap futures/OI
  -> transparent attention rank and source coverage

S4 SHORTLIST
  Profile + request budget + completeness floor
  -> preserve every non-shortlisted stock and reason
  -> optional pinned PKScreener shadow tags

S5 CLOSED STRUCTURE
  Adjusted closed bars -> trend, range, breakout, compression,
  reversal, timing, invalidation and initial evidence direction

S6 DEEP DERIVATIVES LAB FOR SHORTLIST
  Futures basis/rollover + option-chain quality + strike/OI/volume
  + IV/skew/term + Greeks/Gamma + expiry/settlement risk
  -> one capped OPTIONS_CONTEXT package

S7 EVIDENCE RESOLUTION
  Cause + sponsor + structure + flow + risk
  -> correlation caps, support, opposition, conflict, missing proof

S8 RESEARCH SCENARIO
  Entry zone + structural invalidation + target scenarios
  + costs + uncertainty; never an order or quantity

S9 RADAR, INSPECTOR AND PIT JOURNAL
  Show every stock, shortlist, calculations, missing data and lineage
```

Discovery decides where expensive research is spent. It does not decide the public state. Options enrich shortlisted stocks; they do not replace cheap discovery or closed structure.

**No Combined_Score product.** Public state is only `WATCH` / `WAIT` / `CONFIRMED` / `REJECT` from File A §10.4 after family resolution. M-Factor / attention rank prioritizes enrichment only. OPTIONS_PACKAGE remains `SUPPORT` / `WEAKEN` / `CONFLICT` / `UNKNOWN` and never independently owns CONFIRMED.

Every resolved stock receives a `StockResearchRecordV1` containing run/publication/universe/binding versions, identity, profile, data mode, session phase, attempted/completed/empty/failed/not-attempted sources, feature-family coverage, cheap features, PK observations, structure, derivatives, cause/sponsor, restrictions, sector/macro context, rank components, shortlist reason, state ceiling, public state, supporting/opposing/missing evidence, conflicts, research scenario, and lineage.

The frontend must provide both `All Downloaded/Resolved Stocks` and `Research Shortlist`. The first view prevents shortlist logic from hiding stocks or creating false complete-scan claims.

### FMR-003: Option-chain truth contract

Before interpretation, each chain must prove or explicitly mark unknown:

```text
underlying and contract identity
expiry, strike, option side and time to expiry
lot, tick, currency, exercise and settlement style
spot/forward and aligned timestamps
bid, ask, LTP, volume, OI and change in OI
exchange IV and IV method
rate, dividend/carry and corporate-action versions
chain completeness, strike continuity and expiry coverage
snapshot_bundle_id, source result and freshness
```

Every strike row exposes distance from spot and forward; CE/PE bid, ask, spread, LTP, volume, OI and change in OI; IV and method; Delta, Gamma, Theta and Vega; cash-Gamma concentration; quote age; liquidity; wall/concentration rank; and quality/null reasons.

Feature eligibility is independent. A partial chain may support PCR when PCR coverage passes; it cannot automatically support max pain, skew, surface fitting, Gamma migration, or term structure.
Theta/variance/VRP fields are separately eligible and typed: `theta_model`, `theta_time_convention`, `theta_status`, `delta_hedged_variance_attribution_status`, `implied_variance_method`, `realized_variance_forecast_method`, `variance_horizon`, `vrp_proxy`, `vrp_context`, `vrp_status`, `cost_model_version`, `calibration_version`, and explicit null/reason fields. Missing synchronized horizons, carry, exercise/settlement compatibility, forecast lineage or costs produces `VRP_UNKNOWN`; no field is silently filled.

### FMR-004: Strike, OI and expiry intelligence

The Strike/Expiry laboratory calculates:

1. Call and put OI walls by expiry and distance from forward.
2. Change-in-OI walls showing where participation builds or reduces.
3. Volume concentration and session attention.
4. OI PCR and volume PCR separately, with inclusion policy and coverage.
5. OI-wall migration across matched economic coordinates.
6. ATM, spot, observed futures forward and synthetic forward as separate facts.
7. Conventional max pain plus a policy-driven sensitivity range.
8. ATM IV, IV smile, skew, RR25/Fly25 when bracket rules pass.
9. Matched-expiry term structure and change.
10. Spread, quote-age, one-sided-market, volume, OI and tick-quality maps.

Wall labels remain research hypotheses: `PUT_OI_WALL_RESEARCH`, `CALL_OI_WALL_RESEARCH`, `OI_WALL_MIGRATING`, `WALL_NOT_LIQUID`, and `WALL_COVERAGE_UNKNOWN`. Put OI is not guaranteed support; call OI is not guaranteed resistance. Public OI does not reveal whether positions are bought, written, hedged, or spread.

Conventional max pain is:

```text
pain_at_settlement(x) =
    sum(call_oi_i * max(0, x - strike_i))
  + sum(put_oi_i  * max(0, strike_i - x))

max_pain = argmin_x(pain_at_settlement(x))
```

It is an expiry reference, not a target guarantee.

### FMR-005: Gamma exposure and convexity intelligence

TrendForge keeps three Gamma views separate.

#### Canonical unsigned Gamma concentration

```text
cash_gamma_1pct_inr =
    gamma * open_interest * lot_size * spot^2 * 0.01

cash_gamma_1pct_inr_crore = cash_gamma_1pct_inr / 10_000_000
```

Calls and puts remain unsigned and separate. Do not add another `*100`. This is modeled hedge-notional sensitivity for a one-percent spot move. It is not Gamma P&L or observed dealer positioning.

Calculate and display call/put Gamma by strike, total absolute concentration, call/put shares, top Gamma strikes, cluster share, concentration HHI, distance to the nearest cluster, cluster migration, Gamma by expiry, and Gamma by forward moneyness.

#### Signed GEX scenarios

Dealer inventory is not publicly observed. The common call-positive/put-negative result is stored only as:

```text
GEX_PROXY_CALL_POSITIVE_PUT_NEGATIVE
SCENARIO_ONLY_NOT_OBSERVED_POSITION
```

All-long, all-short, or change-in-OI-weighted assumptions may be sensitivity scenarios. They remain inspector-only and cannot vote, set direction, create `CONFIRMED`, or be called dealer flow.

A `gamma_flip_proxy` is allowed only as the zero crossing of a declared signed scenario. It must show sign convention, included expiries and strikes, coverage, timestamps, and sensitivity range. It is never an observed market-maker flip.

#### Research questions

PIT replay must test whether high absolute Gamma near spot is associated with lower movement or pinning after controlling for liquidity, DTE, events and regime; whether cluster migration leads or follows spot; whether low concentration or negative signed scenarios relate to larger moves after costs; and whether Gamma/wall agreement adds value beyond structure and volume. Index results cannot be assumed to transfer to physically settled single-stock options.

Until those tests pass, Gamma is a convexity and strike-attention tool, not a prediction engine.
Professional Mathematics section 17.5 owns the complete dividend-adjusted Theta equations and the local delta-hedged realized-versus-implied variance attribution. FMR-005 consumes those versioned outputs only after model, clock, carry, quote, liquidity and cost gates pass. The attribution remains inspector-only research and cannot supply direction or an independent evidence-family vote.

### FMR-006: IV, Greeks and contract research

The lab also calculates ATM IV, PIT IV percentile/rank, IV minus realized volatility, skew, RR25/Fly25, term slope/change, Delta distribution, Gamma stability, Theta decay, Vega concentration, parity residual, synthetic-forward quality, expiry roll and concentration migration.
`IV minus realized volatility` is descriptive and is not the variance risk premium. A VRP research context requires same-horizon variance units: a governed risk-neutral implied-variance estimate and a point-in-time physical expected-realized-variance forecast. Model-free implied variance is preferred when chain coverage permits; `ATM_IV^2 * T` is stored only as `ATM_VARIANCE_PROXY`, never mislabeled model-free. Allowed descriptive outputs are `IV_RICH_CONTEXT`, `IV_CHEAP_CONTEXT`, and `VRP_UNKNOWN`, based on versioned PIT distributions and calibration rather than universal volatility-point thresholds. This context is `POSTPONE` until R12 data contracts and R16 replay are proven; any model promotion, drift or demotion remains R18-governed.

Research interpretation examples:

| Observation | Possible research use | Required caution |
|---|---|---|
| Bullish structure plus liquid put wall | Possible structure-support zone | Wall may disappear or be part of a spread |
| Bullish structure plus nearby call wall | Overhead participation conflict | Not automatic rejection |
| Gamma cluster close to spot | Convexity/pinning area to monitor | Dealer sign is unknown |
| Gamma cluster moving with spot | Migration regime | Must test whether it leads or follows |
| High IV versus PIT history | Expensive-volatility/event-risk context | Not automatically bearish |
| Low IV plus compression | Expansion-candidate research | Needs cause and structure |
| Skew opposing structure | Tail-risk/hedge-demand conflict | Needs good quotes and carry |
| Near-expiry unstable Gamma/Theta | Model and liquidity uncertainty | Feature may become `UNKNOWN` |

Vanna, Charm, Vomma and Speed may appear in the hidden research inspector only after first-order model, carry, timing and replay gates pass. They remain correlated parts of one options package.

TrendForge may rank contracts for research inspection by identity, expiry/DTE, strike/Delta bucket, distance from spot/forward, spread, quote age, volume, OI, change in OI, IV/model status, Greeks, settlement, corporate actions, scenario role and exclusion reason. Scenario roles include ATM structure reference, call/put wall reference, Gamma-cluster reference, skew-wing reference, term reference, hedge-cost reference and event-volatility reference. A contract rank is never an order or quantity.

### FMR-007: How derivatives help select stocks

The shortlist receives one `OptionsPackageSupportV1` output: `SUPPORT`, `WEAKEN`, `CONFLICT`, or `UNKNOWN`. It explains structure direction, futures basis/OI, nearest liquid walls, wall/Gamma migration, unsigned Gamma regime, signed-GEX sensitivity, PCR trend, IV/skew/term regime, expiry/settlement/event risk, chain quality, and supporting/opposing/missing components.

Examples:

1. Bullish closed structure + improving cause/sponsor + liquid put-wall support + non-conflicting skew may produce options `SUPPORT`.
2. Bullish structure + heavy nearby call wall + adverse skew or expiry instability may produce `WEAKEN` or `CONFLICT`.
3. Strong Gamma/OI activity without closed structure remains discovery attention, without final direction.
4. Empty, stale or partial chain produces `UNKNOWN`; non-options research continues.
5. Futures and options from one root remain one derivatives-family contribution.

No stock is selected by Gamma, PCR, max pain, OI, PKScreener or an opaque score alone. The stronger research candidate has valid identity and liquidity, explainable cause/sponsor/structure/flow, acceptable restrictions, independent-family coverage, and limited unresolved conflict.

### FMR-008: Open-source projects and websites

Open-source software supplies calculations and comparison. It is not automatically authoritative market data.

| Project | Research use | Boundary |
|---|---|---|
| `vollib` / `py_vollib` compatibility namespace (`https://github.com/vollib/py_vollib`) | Independent IV, option-price and first-order Greek fixtures | Compare with the existing engine; pin version, formula and units before dependency approval |
| QuantLib (`https://www.quantlib.org/`) | Independent pricing, settlement-aware model research and fixtures | Optional reference adapter; never a second production calculation path |
| OpenAlgo (`https://github.com/marketcalls/openalgo`) | Future read-only chain, multi-Greeks, IV smile, GEX, OI, max-pain and surface comparison | Disabled/read-only until validated; never use order, account or position routes |
| PKScreener (`https://github.com/pkjmesra/PKScreener`) | Breakout, compression, momentum, reversal, candles and technical shadow tags | Pinned sanitized batch by default; optional isolated local shadow service; no state authority |
| NumPy/Pandas/SciPy | Normalization, statistics, interpolation and deterministic calculations | Reuse approved dependencies and version formulas |
| Other GitHub scanners | Feature discovery, fixture comparison and negative controls | Audit license, source, timing, lookahead, survivorship and semantics first |

Current project documentation identifies `vollib` as the canonical package name while retaining `py_vollib` imports as a compatibility namespace. This is research information, not approval to install or replace the present engine.

OpenAlgo contains analytics and execution functions. TrendForge may use only a separately approved read-only analytics boundary. Future broker data does not change the no-execution rule.

Every third-party integration records repository URL and commit/tag, licenses, feature mapping, input source and timing, lookahead/survivorship audit, credential boundary, output schema, failure behavior, numerical fixtures, state permission, and upgrade/removal procedure.

### FMR-009: Frontend workflow

Primary radar rows show symbol/sector, research rank, public state, data mode/session, structure direction, cause/sponsor/flow coverage, source completion, nearest call/put wall, Gamma regime, PCR trend, IV regime, options support/conflict, expiry/restriction warning, and why selected or not shortlisted.

### Decision-tool composition amendment

The primary product is a dense decision terminal. Compact signal cards are a secondary view over the same immutable result; they are not a simpler scoring engine. The 14 retained tools are grouped under Radar, Discovery, Derivatives, Research and System Health, while each tool exposes the shared tabs `Signals`, `How validated`, `Track record` and `Engines used`.
The canonical fixture-backed visual target is `docs/TRENDFORGE_FINAL_PRODUCT.html` (local preview `http://127.0.0.1:8765/TRENDFORGE_FINAL_PRODUCT.html`). File A R15 must make the runtime frontend match its information architecture and interaction hierarchy while replacing all fixture values with canonical API DTOs. The preview URL is operational convenience only; the saved HTML artifact and this contract remain authoritative when the server is offline.

M-Factor is governed by `FUS-009` only:

```text
long_strength  = FUS-009 evidence_strength for the bullish hypothesis
short_strength = FUS-009 evidence_strength for the bearish hypothesis
m_balance      = long_strength - short_strength
rank_strength  = max(long_strength, short_strength)
```

The directional class is derived from versioned, initially uncalibrated `m_balance` bands. `directional_class`, lifecycle `readiness_tag` and public `state` remain separate. A strong class or `SETUP_READY` tag cannot bypass WAIT, safety, freshness, closed-bar or activation gates. Ranking uses rank strength, then completeness, freshness and deterministic symbol order; no second M-Factor weighted score is permitted.

Every tool response carries one `run_id`, `snapshot_bundle_id`, publication/data cutoff, profile, state/ceiling, gate reasons, typed metrics, selected/suppressed claims, source result IDs, dataset roots, correlation groups and formula/source versions. Price, OI, delivery, event, sector and expiry observations from different runs cannot silently compose one result.

`GET /api/v1/tools/{tool_id}` is a read-only frontend composition/BFF boundary over canonical selection, feature, options, history and source-health DTOs. It cannot calculate an independent score, rewrite state, fabricate missing values or mix runs. Tool-specific calculations remain owned by the canonical domain modules.

Profile applicability is explicit: M-Factor uses eligible NSE F&O equities; Index Dashboard and PCR timeline use NIFTY/BANKNIFTY profiles; Strike/Expiry Range Context requires verified same-expiry derivatives; Trend + Accumulation uses closed EOD swing data and official delivery cadence; MCX uses a separate commodity/contract/session profile. Delayed data remains delayed context.

The `Track record` tab is visible but locked as `PIT_NOT_VALIDATED`, with sample count `0`, and null win-rate/benchmark fields until R16 leakage, survivorship, costs, censoring, minimum-sample and walk-forward gates pass. Fixture and static-product values cannot unlock performance presentation.

The detailed field lists, wording law, shared `ToolResultV1`, evidence-tab behavior and fixture-only class bands live in `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md`; that file is a detail catalog only and cannot create another build order.
The hidden Strike/Expiry inspector shows:

1. Strike ladder centered on spot and forward.
2. CE/PE OI, change in OI, volume, IV, Delta, Gamma, Theta, Vega, spread and quote age.
3. OI-wall and change-in-OI heatmaps.
4. Unsigned cash-Gamma bars by strike and expiry.
5. Signed GEX scenario toggle with permanent `SCENARIO_ONLY_NOT_OBSERVED_POSITION` label.
6. Gamma-cluster and OI-wall migration timeline.
7. IV smile, skew, term and raw-quality defects.
8. Max-pain conventional value and sensitivity range.
9. OI/volume PCR with inclusion policy and coverage.
10. Settlement, carry, dividend, corporate-action, lot and tick assumptions.
11. Supporting, opposing, missing and conflict evidence.
12. Source timestamps, formula versions, dataset roots and lineage.
13. Full Theta model/time convention, local delta-hedged variance attribution, and VRP context with method, same-horizon proof, costs, calibration, status and `VRP_UNKNOWN` reasons. These remain research calculator/context fields, never trade commands.

The All Stocks view shows resolved stocks that were not shortlisted, not attempted for deep chain, valid-empty, partial, stale, identity-conflicted or research-only, plus the exact next missing proof.

### FMR-010: Acceptance tests and build placement

Tests must prove all resolved stocks appear; exclusions retain reasons; blocked is not empty; unresolved identity cannot calculate; dynamic binding sets replace fixed counts; partial-universe arithmetic is correct; one root is not counted twice; PK/options failure does not stop cheap discovery; PK cannot write state; partial-chain eligibility is per feature; PCR zero denominator is unknown; max pain exposes policy/sensitivity; canonical Gamma is unsigned with correct units; signed GEX and flip are scenarios; dealer position is never inferred; wall migration matches economic contracts; lot/tick/expiry/corporate-action changes invalidate old values; stale/one-sided quotes cannot produce eligible Greeks; missing carry is not zero; surface and flow share one bundle and one family cap; options cannot independently confirm; radar and inspector agree; zero differs from unknown; data modes do not mix; PIT replay uses only then-available versions; third-party disagreement causes audit, not silent replacement; OpenAlgo cannot reach execution routes; and exports include manifest/lineage IDs.

Additional decision-tool acceptance must prove:

1. M-Factor long/short strengths exactly equal the two canonical `FUS-009` hypothesis outputs.
2. Duplicate activity, OI, options and mirror roots cannot increase rank.
3. Directional class, readiness tag and public state cannot substitute for each other.
4. Bullish stock evidence plus required bearish index conflict produces WAIT; optional context only weakens the class.
5. OI/PCR copy never claims buyer, writer, dealer or institutional identity.
6. Expiry output is labelled `Expiry Range Context`; mixed expiry/run snapshots block the estimate.
7. EOD delivery cannot populate intraday evidence.
8. BFF tool output equals canonical DTO values and rejects mixed run/bundle input.
9. Track record remains `PIT_NOT_VALIDATED` with sample zero until R16 approval.
10. Static fixture HTML cannot be reported as runtime or production implementation.
Implementation stays inside File A `R0-R18`: R0 establishes dynamic bindings, run truth, permissions and universe accounting; discovery builds the all-stock cheap pass with a `WAIT` ceiling; closed structure provides the first eligible direction path; deep options starts only after chain, identity, contract-master, quality and snapshot proof; frontend first shows all-stock coverage, then Strike/Expiry details; PIT/OOS proof is required before any claim that Gamma, walls, skew, PK or combined ranking improves outcomes.

Until activation and acceptance pass, these calculations remain useful research outputs under the existing state ceiling. Using every source means extracting its honest research value, not converting weak data into false certainty.

### FMR-011: Research Paper Lab and governed ML learning loop

#### Purpose and boundary

TrendForge shall retain every published research decision as an immutable,
point-in-time experiment and replay it through a local deterministic paper
simulator. Resulting path observations may improve research ranking models.
This is validation, not a broker simulator, OMS, account ledger, executable
quantity engine or permission to trade.

Owner split: `R15` owns only the Paper Lab presentation shell and inspector
surfaces; `R16` owns deterministic replay, objective path labels and the
point-in-time dataset; `R18` owns challenger evaluation, human promotion, drift
demotion and rollback. The R16 simulation core does not absorb the R15 or R18
obligations.

The Paper Lab never calls broker order, account, position, margin or portfolio
routes; never stores broker credentials; never mutates historical decisions;
and never lets ML bypass source, freshness, identity, surveillance, F&O-ban,
structure, options-quality or hard-risk gates. Manual `WIN` or `LOSS` remains
annotation rather than the primary training label. The deterministic four-state
resolver remains the independent fallback.

#### Immutable decision and paper contracts

Each case binds `decision_snapshot_id`, `scan_run_id`, manifest/input hashes,
instrument identity, mode/timeframe/data mode/session, decision time, original
public state and ceiling, structure direction, entry zone, trigger,
invalidation, targets, holding/expiry limit, source keys, dataset roots,
feature/formula/model versions, corporate-action version, universe version and
restriction snapshot. Only evidence available at decision time is eligible.
Corrections create a new version and never rewrite the original row.

A simulated position exists only after its versioned trigger becomes true on a
later eligible closed bar. The run records trigger/fill/close times, reference
and simulated prices, fill/spread/slippage/fee/gap policy versions,
corporate-action handling and exit reason. Missing bars, spread, costs,
contract-master or corporate-action proof yields `PAPER_UNSCORABLE`, not a
free fill. Same-bar target/stop ambiguity follows a declared conservative
policy. No executable quantity is required; normalized percentage and
R-multiple outcomes are sufficient.

#### Objective path outcomes

Primary labels are path-derived:

```text
TRIGGER_NOT_REACHED
TARGET_1_BEFORE_INVALIDATION
TARGET_2_BEFORE_INVALIDATION
TARGET_3_BEFORE_INVALIDATION
INVALIDATION_BEFORE_TARGET
EXPIRED_OR_TIMED_OUT
AMBIGUOUS_SAME_BAR
DATA_INCOMPLETE
CORPORATE_ACTION_INVALIDATED
CONTRACT_EXPIRED_OR_ROLLED
```

Store MFE, MAE, cost-adjusted R, time to trigger/MFE/MAE/targets, holding bars,
gap loss, liquidity penalty, maximum adverse gap and censoring reason. Manual
journal notes cannot overwrite these labels. `WATCH`, `WAIT`, `CONFIRMED` and
`REJECT` cases remain available for counterfactual evaluation so the dataset
does not learn only from selected winners.

#### ML learning and relearning

`TrainingExampleV1` joins the immutable decision snapshot to the objective
outcome by IDs and hashes. It preserves failed, missing and unknown features,
delisted stocks, rejected cases and non-triggered cases.

Use separate models for discovery attention, trigger quality, harmonic
continuation/invalidation, options support/conflict, holding-time/adverse
excursion and data-quality/false-positive research. Intraday, swing, NSE equity,
NSE derivatives and MCX remain separate until pooling proves incremental value.
PKScreener, harmonic, options and Gamma/GEX fields retain source, availability,
family, correlation-group and dataset-root controls.

Relearning is a bounded offline batch:

```text
freeze PIT dataset
  -> validate lineage and labels
  -> purged walk-forward splits with embargo
  -> train baseline and challengers
  -> evaluate costs, calibration, stability and subgroups
  -> shadow replay on untouched data
  -> human promotion decision
  -> signed registry entry with rollback
```

Scheduled challenger training is allowed; automatic champion replacement is
not. Promotion requires unchanged hard gates, no leakage, declared sample
minimums, untouched-period improvement over the deterministic baseline,
acceptable calibration when probabilities are evaluated, stable subgroup and
regime behavior, reproducible hashes and explicit review. Drift may demote a
model to `SHADOW`, `STALE_MODEL` or `DISABLED`. Before `PIT_APPROVED`, the UI
cannot show win probability, guaranteed accuracy or model-driven `CONFIRMED`.

#### Storage, API and frontend

Planned stores: `paper_decision_snapshots`, `paper_runs`, `paper_fills`,
`paper_path_outcomes`, `training_examples`, `ml_dataset_versions`,
`ml_training_runs`, `ml_model_registry`, `ml_evaluation_reports`,
`ml_drift_events` and `ml_promotion_reviews`.

Planned backend owners: `selection/paper_lab.py`, `selection/outcomes.py`,
`selection/training_dataset.py`, `selection/model_training.py`,
`selection/model_registry.py` and `selection/model_monitor.py`.

Research-only APIs use `/api/research/paper/*` and `/api/research/ml/*`. A
promotion endpoint records a review only; it cannot place orders or enable
broker routes.

Radar shows only `ML_SUPPORT`, `ML_WEAKEN`, `ML_CONFLICT`, `ML_UNKNOWN` or
`MODEL_UNAVAILABLE`, plus model version and validation date. The hidden Paper
and Learning inspector shows simulated trigger/fill/invalidation/targets/costs,
bar path with MFE/MAE, exact source lineage, feature null reasons,
champion/challenger walk-forward comparison, drift/subgroup diagnostics,
review queues and promotion history. It permanently displays
`RESEARCH_SIMULATION_ONLY - NO BROKER ORDER`.

#### Acceptance tests and placement

Tests must prove no paper/ML route reaches broker code; no future or corrected
evidence leaks backward; delisted/rejected/non-triggered cases remain; unclosed
bars cannot trigger; fill ambiguity and gaps follow conservative policies;
missing costs produces `PAPER_UNSCORABLE`; correlated PK/options fields retain
caps; manual labels cannot replace path labels; purged walk-forward and embargo
work; challengers cannot auto-promote; drift restores deterministic behavior;
ML-disabled state explanations stay unchanged; probability UI stays hidden
before approval; artifacts reproduce by hash; and no quantity/live/autonomous
action appears.

Map this requirement to File A `R15` for inspector UI, `R16` for PIT outcomes
and paper replay, and `R18` for training, drift, registry, promotion and
rollback. Existing ML snapshots and manual journal records are partial inputs,
not proof of completion. Build deterministic replay and outcome data before
any predictive model.
