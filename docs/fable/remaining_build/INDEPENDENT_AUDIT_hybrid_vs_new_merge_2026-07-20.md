# Independent Audit: Hybrid Plan vs New Merge Plan

**Date:** 2026-07-20  
**Sources (read completely by section):**

| Ref | File | Role |
|---|---|---|
| `HYBRID` | `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` | 2026-07-17 hybrid data-to-decision plan + §§15–19 amendments (~2776 lines) |
| `MERGE` | `docs/fable/new_merge_PLAN_2026-07-18.md` | 2026-07-18 authoritative future plan (§§0–24) |

**Method:** Section-by-section extraction of every material idea, contract, formula, milestone, test, rejection and backlog item in HYBRID; map to MERGE disposition KEEP / IMPROVE / MERGE / POSTPONE / REJECT / **MISSING** / **THINNER**.  
**Authority rule (project):** When plans conflict on *future build*, MERGE controls — *except* this audit records HYBRID material that was **not fully carried** and should be re-merged as stable IDs before build.

**Verdict:** MERGE is the **better control document** for research selection (four states, anti-double-counting, PK boundary, runnable R/Q5 order, no false execution scope). HYBRID remains **richer operational decision-system content**. Several high-value HYBRID blocks are only partially absorbed or deliberately postponed; a subset is **materially missing detail** and should be folded into MERGE before implementing live S0–S9.

---

## 0. Scope difference (must understand first)

| Topic | HYBRID | MERGE | Best for build |
|---|---|---|---|
| Product goal | Full **decision + guidance + risk sizing** path toward READY | **Research selection + manual review only** | MERGE for current product boundary |
| Public states | READY, many WAIT_*, NO_TRADE, LOCKED, REJECT | Exactly **WATCH / WAIT / CONFIRMED / REJECT** | **MERGE** (simpler, testable) |
| Quantity / entry / stop / targets | Core guidance contract | **Explicitly out of plan** (warnings only) | MERGE for safety; HYBRID for later optional risk module |
| OpenAlgo | RO → shadow → paper → live path described | RO boundary only; execution rejected | MERGE now; keep HYBRID promotion ladder as postponed appendix |
| Inventory | Full 354-row utilization + exact key lists | Dataset roots + roles; counts must recompute | HYBRID detail + MERGE identity model |
| Build order | H1…H10 / H1A* fine grain | R0–R18 + Q5-R0…R7 | MERGE for sequence; HYBRID for inventory-first H1A0 depth |

**Important:** “Missing from MERGE” is **not always a defect**. MERGE intentionally rejected quantity/execution. Those are **POSTPONE**, not accidents. Below, **MISS-CRITICAL** = still needed for trustworthy research selection; **MISS-SCOPE** = only needed if product later expands beyond selection.

---

## 1. Section-by-section comparison

### HYBRID §1 Objective (7 trader questions)

| Idea | MERGE | Disposition |
|---|---|---|
| Which symbols deserve attention | Radar / selection | KEEP (MERGE UI-001) |
| Why movement / independent confirm | Families + claims | **IMPROVE** in MERGE |
| Missing evidence | Required | KEEP |
| WAIT→READY trigger | Next confirmation condition | KEEP as WAIT→CONFIRMED |
| Invalidation | Gates + history | KEEP |
| **Quantity for risk limit** | Explicitly excluded | **POSTPONE** (MISS-SCOPE) |

**Best:** MERGE for research product; HYBRID Q7 is deferred risk.

### HYBRID §2 Inventory baseline (370/354/105/231/18)

| Idea | MERGE | Disposition |
|---|---|---|
| Exact partition + invariant | Mentions recompute; rejects frozen narrative counts | **IMPROVE** in MERGE for honesty |
| Linked ≠ gate-authorized | Explicit in both | KEEP |
| Contract-level overlap vs URL disjoint | HYBRID stronger | **THINNER** in MERGE — retain compiler defect story |

**Best:** MERGE for not freezing stale counts; HYBRID for defect semantics.

### HYBRID §3 Governing principles (10)

All largely KEEP/IMPROVE in MERGE (cheap-before-expensive, hard veto, delayed labels, fail-closed, no AI authority, hash lineage).  
HYBRID **NO_TRADE still monitors** vs MERGE **global lock** — MERGE is cleaner for four-state API.

### HYBRID §4 Source Decision Contract fields

HYBRID fields: `source_key`, roles, `decision_jobs`, `independence_family`, `can_discover/score/veto/unlock_ready`, fallback, limitations, panel…  
MERGE: roles + dataset roots + feature contracts + DAT-* envelopes.  

**Gap:** MERGE does not retain one **machine-readable per-source map** template equal to HYBRID H2:

```text
source_key, endpoint_ids, artifact_kind, parser_id, dataset_id,
decision_jobs, feature_ids, strategy_profiles, mandatory_for,
confirmation_for, veto_for, independence_family, authority_cap,
freshness_by_job, fallback_chain, primary_panel_field,
inspector_sections, tests
```

**Status:** **MISS-CRITICAL** as an executable artifact (DAT/H2). Partial via registry/workbook, not as plan acceptance criterion with full field list.

### HYBRID §5 Stages 0–9 pipeline

| Stage | HYBRID | MERGE | Winner |
|---|---|---|---|
| 0 Immutable landing | Yes | S0 + DAT | Tie / MERGE structure |
| 1 Universe/safety/CA | Yes | S1 | Tie |
| 2 Quality/session | Yes | DAT + gates | Tie |
| 3 Regime/sector/MCX context | Regime labels BULL_TRADEABLE… | Context family | HYBRID labels richer; MERGE safer non-direction |
| 4 Cheap discovery | Yes | S3 | Tie |
| 5 Candidate enrichment | Yes | S5 / R6 | Tie |
| 6 Structure/deriv/traps | Entry/stop/targets | Structure claims, no entry sizing | MERGE research; HYBRID trade UX |
| 7 G00-G14 + multi WAIT states | Dual system risk | G-codes as reasons only | **MERGE better** |
| 8 Risk quantity INR 1L | Full table | **Excluded** | HYBRID detail; MERGE scope |
| 9 OpenAlgo paper path | Full ladder | RO only | MERGE now |

### HYBRID §6 Strategy profiles

Both have intraday/swing/event/MCX.  
HYBRID: mandatory combinations per profile (exhaustion, PEAD surprise, etc.).  
MERGE: PRF-001..007 with ceilings.  

**Gap:** HYBRID **per-profile veto lists** (wide spread, event ambiguity, sector contradiction tolerances) and **event materiality rules** (order-win value/revenue, deal price acceptance 1D/5D/20D) are more concrete. MERGE has FTR-026 but thinner PEAD/order-win acceptance rules.  
**Status:** **THINNER / MISS-CRITICAL** detail for event strategies.

### HYBRID §7 EvidenceClaim + Guidance contracts

EvidenceClaim largely KEEP in MERGE (DAT-019, claims).  

**Guidance contract** fields in HYBRID:

```text
headline, action ACT|WAIT|AVOID|LOCKED, why_now, supporting/contradicting,
missing, next_trigger, invalidation, recheck_at, expires_at,
entry_zone, stop, targets, quantity, maximum_loss, binding_risk_cap,
size_explanation, alternative_scenario, source_hashes
```

MERGE radar: eight questions + evidence strength; **no** entry/stop/qty.  

**Status:** Research presentation **KEEP** MERGE; trade guidance **POSTPONE** (MISS-SCOPE) — but **recheck_at / expires_at / FOMO** candidate expiry is useful for research UI and is **THINNER** in MERGE.

### HYBRID §8 Storage model

Both: raw immutable + SQLite/Parquet.  
HYBRID: DuckDB only after profiling. MERGE: selection_* tables, bar_versions, outcomes.  
Tie; MERGE better selection schema; HYBRID clearer raw/adjusted split narrative (also in MERGE later sections).

### HYBRID §9 Trader UX

| HYBRID | MERGE | Gap |
|---|---|---|
| Command bar: mode, session, regime, freshness, **account risk**, exposure, safety | Completeness/freshness/data mode | Account risk out of scope; command-bar **session/regime** thinner |
| Radar: evidence rank, age, expiry/recheck, change | 8 questions, what-changed | **expires_at / FOMO** thinner |
| Risk/action rail: entry, stop, targets, R:R, qty | Explicitly forbidden | POSTPONE |
| Inspector ~52% drawer + mobile full | Tabs defined | UX chrome detail missing (low) |
| Risk and Scenarios tab | Risk presentation only | THINNER |
| Journal notes + outcomes in history | Manual journal non-calibrating | KEEP MERGE safety |

### HYBRID §10 Productivity (10 items)

| # | Item | In MERGE? |
|---|---|---|
| 1 | Saved scan profiles | PARTIAL (scan_profile_versions / profiles) |
| 2 | What-changed | KEEP (FTR-033) |
| 3 | **Side-by-side top-3 compare** | **MISSING** |
| 4 | Auto-persist READY/WAIT/REJECT/NO_TRADE | PARTIAL (state events; no NO_TRADE state) |
| 5 | Grouped source failures | KEEP (failures tab) |
| 6 | Candidate expiry + **FOMO downgrade** | **MISSING / THINNER** |
| 7 | Incremental enrichment | KEEP (S5) |
| 8 | **One-click journal snapshot with evidence hashes** | **THINNER** |
| 9 | **Daily review: false READY, useful WAIT, rejected losers, missed winners** | **MISSING** as product workflow |
| 10 | Search by symbol/state/setup/source/event/blocker | **THINNER** |

### HYBRID §11 APIs/tables

MERGE has richer selection/scanner/options APIs.  
HYBRID `POST /api/v1/risk/evaluate` and `candidate_guidance` / `risk_evaluations` → **POSTPONE** in MERGE.  
HYBRID `candidate_block_scores` → MERGE uses gates + evidence strength (better).

### HYBRID §12 Failure tests (18)

Largely covered by MERGE T-001..070 and later T-series. Stronger in MERGE volume.  
HYBRID unique emphasis: **confidence increasing quantity past hard cap**, **emotionally locked intent** → POSTPONE with risk module.

### HYBRID §13 H1–H9 milestones

Superseded by MERGE R0–R18 / Q5. **Do not build H-order as primary.**  
Retain H1A0 inventory compiler depth inside R0.

### HYBRID §14 Completion definition (9 points)

MERGE GOV-006 + observed tests is stronger. KEEP MERGE.

### HYBRID §15 Fable audit findings

| Block | MERGE | Note |
|---|---|---|
| 15.1 Implementation mismatches | Absorbed as weaknesses W-* | KEEP |
| **15.2 Two-speed architecture** (fast / NRT / EOD / slow lanes) | data_mode + ceilings | **THINNER** — lane table is valuable |
| 15.3 Extended source contract fields (timezone, rate_budget, circuit_breaker, watermark…) | Partial DAT | **THINNER** |
| **15.4 Trust-producing combinations table** | Implicit | **MISSING** as explicit matrix |
| **15.5 Data Confidence / Evidence Rank / P(win) / EV split** | Strength ≠ probability | **THINNER** — four-way split useful |
| 15.6 Risk/execution preflight (lot, freeze, margin, bands…) | Tradability + POSTPONE qty | Partial FTR-035 |
| 15.7 NSE licensing / SEBI links | Boundary in DECISIONS/AGENTS | **THINNER** in MERGE body |
| 15.8 Alternatives evaluated | Implicit | Low priority |
| 15.9 H1A before H2 | R0 inventory/contracts | KEEP spirit |

### HYBRID §16 Full-inventory utilization (core richness)

#### 16.1–16.2 Inventory truth + verdict

KEEP spirit in MERGE. Exact SHA of workbook is **dated** — MERGE right to recompute.

#### 16.3 Source-state ladder (REGISTERED → EXECUTION_AUTHORIZED)

MERGE has transport/result states + Q5 SourceResult.  
HYBRID ladder is **finer operational maturity** with mandatory **stage counts**.  
**Status:** **THINNER / MISS-CRITICAL** for inventory honesty dashboard.

#### 16.4 H1A0 inventory defects (exact defects 1–11)

Malformed keys, compound URLs, sentinels, purpose_jobs taxonomy, nse_mwpl_ban mismatch…  
MERGE DAT-018 inventory compiler — **partial**. Exact acceptance checklist (zero malformed, zero sentinels, etc.) is **HYBRID-stronger**.  
**Status:** **MISS-CRITICAL detail** — re-import H1A0 acceptance 1–6 into R0.

#### 16.5 All 354 roles utilization table

OFFICIAL_OR_PRIMARY 222, CONFIG 47, … LOCAL 2.  
MERGE has role enum but not **row-count disposition table**.  
**Status:** **THINNER** — recompute from workbook, keep table structure.

#### 16.6 Exact linked 69 + not-linked 43 source_key lists

**Not reproduced in MERGE.**  
**Status:** **MISS-CRITICAL** as living map (belongs in compiler output / registry, plan should require the map artifact).

#### 16.7 Decision families + source combinations per strategy

HYBRID: mandatory masters, intraday continuation/reversal, PEAD, accumulation, MCX gold/energy/base/agri with **named source_keys**.  
MERGE: families + PRF + FTR.  
**Status:** **THINNER** on named-key → job wiring; this is the heart of “use inventory without polluting decisions.”

#### 16.8 High-value feature catalog

Auction features (IEP_stability, buy_sell_imbalance…), RVOL_TOD, OI walls, GEX_PROXY, event_materiality…  
MERGE FTR-001.. covers many; HYBRID has **more auction path features** and **vollib / OpenAlgo multioptiongreeks** pin notes.  
**Status:** mostly KEEP/IMPROVE; pin notes **THINNER**.

#### 16.9 Fusion q_i formula and independence families

```text
q_i = authority * freshness * schema * completeness * scope * timestamp_integrity
```

MERGE uses family resolver + weights; not this explicit multiplicative quality.  
HYBRID independence family names differ slightly (PRICE_AND_LIQUIDITY vs PARTICIPATION…).  
**Status:** formula **THINNER**; families **IMPROVE** in MERGE.

#### 16.10 Legacy scorer quarantine with **line-level** `intraday_stock_details.py` critique

MERGE FUS-008.  
HYBRID lines 887–931 specific bugs (gap both ways, static PCR, stack correlated volumes).  
**Status:** KEEP MERGE contract; **retain line-level migration checklist** from HYBRID as test cases.

#### 16.11 Prediction / data-science plan

Brier, ECE, 200 outcomes, purged WF, embargos, River/Pandera/vollib/vectorbt Commons Clause.  
MERGE: PIT validation, drift, no probability UI until PIT_APPROVED; **no library shortlist**, **no promotion sample rules**.  
**Status:** **THINNER / MISS** for later H8 — re-import as POSTPONE appendix with dependency approval gate.

#### 16.12 Real-time breakage/recovery SM + fallback hierarchy

Very strong operational SM. MERGE has source states + tests; not full **per-source calendar SM** diagram.  
**Status:** **THINNER / MISS-CRITICAL** for live ops.

#### 16.13 OpenAlgo interface (MarketDataProvider / ExecutionProvider)

MERGE: capability states, RO routes only.  
HYBRID: full method surface + paper path.  
**Status:** RO methods KEEP; execution methods **POSTPONE/REJECT** correctly.

#### 16.14 INR 1 lakh quantity math

Full formula + caps. MERGE POSTPONE. **MISS-SCOPE.**

#### 16.15 Product design radar fields

Includes proposed quantity, max loss, prediction status, surveillance badges.  
MERGE: badges partial via FTR-035; quantity out.  
**Surveillance badges / band distance / halt** — re-import UI detail.

#### 16.16 Priority activation backlog (20 contracts)

**Not in MERGE as ordered backlog.**  
**Status:** **MISS-CRITICAL** for build prioritization of sources.

#### 16.17–16.18 Vertical slices + 25 completion criteria

Vertical slices (stock intraday, swing event, MCX gold, MCX crude) excellent delivery advice.  
MERGE has R-order but not **four named E2E slices**.  
**Status:** **MISS-CRITICAL** delivery pattern.

### HYBRID §17 Antigravity P0/P1

| Item | MERGE | Status |
|---|---|---|
| TradabilityRestriction schema | FTR-035 / DAT-027 | **KEEP but HYBRID field list fuller** (T2T, bands, halt, auction…) |
| New source keys nse_t2t, nse_esm, nse_price_bands, nse_market_halts | Not fully registered as planned keys | **THINNER / MISS** until verified |
| Raw vs AdjustedMarketSeries | Present in later MERGE | KEEP |
| Timestamp semantics | DAT timestamps | KEEP |
| MARKET_FLOW parent family cap | Correlation groups / FUS | **THINNER** parent hierarchy |
| **realizable_unit_risk** (gap/circuit/liquidity stress) | “realizable-exit warning” only | **MISS-SCOPE** for qty; **THINNER** for research warnings |
| Legacy quarantine | FUS-008 | KEEP |
| Outcome logging early | STO-015/017 | KEEP spirit |
| Model demotion fallback | Drift demotion | THINNER ladder MODEL_ACTIVE→RESEARCH→DETERMINISTIC |
| Broker tick integrity | DAT-017 / OPN | KEEP partial |
| Versioned fees/lot/tick/margin | POSTPONE costs in VAL-001 offline | Partial |
| Feature corrections (max pain PROTOTYPE_ONLY, etc.) | REJ/PST | KEEP |
| 20 new failure tests | Many T-IDs | Mostly covered / partial |
| Panel rejections (1% circuit veto rejected, etc.) | MERGE agrees | KEEP |

### HYBRID §18 Panel 354 reconciliation

| Item | MERGE | Status |
|---|---|---|
| Panel claim ledger ACCEPTED/REJECTED | Spirit in C-* and REJ | **THINNER** as explicit ledger |
| dataset_root_id / transport_variant / mirror_group / resolver_id | Dataset roots yes; full identity chain thinner | **THINNER / MISS-CRITICAL** fields |
| Four chains NSE/MCX × intra/swing | PRF + data_mode | KEEP spirit; HYBRID flow diagrams clearer |
| Accepted code fixes (SHFE defaults, GSM no today_iso) | May be code-level | **Verify code**; plan-level weaker |
| Official-verification backlog (MCX pre-open, LME, …) | Some POSTPONE | **THINNER list** |
| 18 rejection shortcuts | Strong overlap with REJ | KEEP MERGE |
| Acceptance gate 354 map complete | Not MERGE completion gate | **MISS** as acceptance criterion |

### HYBRID §19 Independent architecture review

| Item | MERGE | Status |
|---|---|---|
| Maturity ladder REGISTERED→GATE_AUTHORIZED | Partial | **THINNER** |
| **J01–J14 decision-job taxonomy** | decision_jobs mentioned | **MISS-CRITICAL** as table |
| Shared seeded NSE transport | DAT-020 | KEEP |
| **nse_fno_ban vs nse_mwpl_percentages split** | DAT-015 freeze owner | **THINNER** — split is important |
| **FBIL daily vs live USD/INR** | MCX-002 / FX context | **THINNER** |
| State compatibility layer for legacy READY/WAIT_* | STA-005 | KEEP MERGE four-state |
| Unified PIT outcome worker | R16 / STO | THINNER automation worker |
| Cross-exchange MATCHED/POSSIBLE_MATCH/DISTINCT/MANUAL_REVIEW | T-015 mirror one event | **THINNER** ambiguity states |
| Dataset-root P0 priority (5 true P0 roots) | R0 | KEEP spirit |
| Fusion rules 1–10 | FUS + gates | KEEP |
| Legacy scorer quarantine detail | FUS-008 | KEEP |
| Risk % as versioned config not constants | POSTPONE | KEEP |
| Extra milestones H1A4/H1A5/H3A… | Mapped into R/Q5 loosely | THINNER |

---

## 2. Best of each plan (format)

### Best of HYBRID (keep as content, even if postponed)

1. **Exact inventory utilization** — 354 disposition, role counts, linked/not-linked key lists, H1A0 defect list.  
2. **source_key → feature → strategy → gate → UI map** template.  
3. **Decision-job taxonomy J01–J14**.  
4. **Per-strategy mandatory/confirmation/veto source combinations** (named keys).  
5. **Priority activation backlog** (20 sources by decision gap).  
6. **Source maturity ladder + stage counts**.  
7. **Two-speed data lanes** (fast / NRT / EOD / slow).  
8. **Trust-producing combinations** (what combo proves / does not prove).  
9. **Four-way score split:** Data Confidence / Evidence Rank / Calibrated P(win) / EV.  
10. **TradabilityRestriction full schema** + proposed band/halt/T2T contracts.  
11. **Realizable-exit stress model** (even as research warning without quantity).  
12. **Legacy scorer line-level bugs** → regression tests.  
13. **E2E vertical slices** (stock intra, swing event, MCX gold, MCX crude).  
14. **Productivity workflows** (side-by-side, FOMO expiry, daily review, journal hash snapshot).  
15. **OpenAlgo interface + promotion ladder** (RO only for now).  
16. **Data-science promotion guards** (Brier/ECE/sample) as POSTPONE appendix.  
17. **Cross-exchange match ambiguity states**.  
18. **F&O ban vs MWPL % split** and **FBIL vs live FX split**.  
19. **Panel claim ledger** discipline (ACCEPTED/REJECTED with reason).  
20. **Licensing/compliance pointers** (NSE data policy).

### Best of MERGE (authoritative for next build)

1. **Single four-state product model** + gate reason codes.  
2. **Research-only boundary** — no quantity/execution in this plan.  
3. **Evidence families + correlation groups + zero corroboration** machine rules.  
4. **Mandatory feature contracts** FTR with formulas and failure behavior.  
5. **S0–S9 cost-aware pipeline** + completeness ceilings.  
6. **Runnable R0–R18 / Q5-R0–R7** with observable verticals.  
7. **PKScreener wholesale under non-authority** (offline harness).  
8. **70–100+ stable adversarial test IDs**.  
9. **data_mode + intraday CONFIRMED ban** until broker integrity.  
10. **MCX CONFIRMED ban** without local master/OI.  
11. **Stable requirement IDs** (GOV/STA/FUS/DAT/SEL/UI/STO/API/OPN/PK).  
12. **Explicit POSTPONE/REJECT ledger** preventing scope creep.  
13. **FUS-008 detail_score quarantine** as hard DTO rule.  
14. **PIT performance UI lock** until approval.  
15. **Traceability** of audits into one document.

---

## 3. Material gaps in MERGE (action list)

### 3.1 MISS-CRITICAL (should amend MERGE before/while live S0–S3)

| ID | HYBRID source | Gap | Suggested MERGE action |
|---|---|---|---|
| G-01 | §16.4 H1A0 | Exact inventory compiler defects + zero-defect acceptance | Add `DAT-INV-001` acceptance criteria to R0 |
| G-02 | §16.6 | Living map of all normalized source_keys → jobs | Require compiler artifact `source_to_decision_map.json` |
| G-03 | §19.2 | J01–J14 decision-job taxonomy table | Add `DAT-JOB-001` |
| G-04 | §16.7 | Per-strategy named source combinations | Extend PRF-001..007 with mandatory/confirm/veto **source_key sets** |
| G-05 | §16.16 | Priority activation backlog 1–20 | Add `SRC-ACT-001` ordered backlog |
| G-06 | §16.3 / §19.1 | Maturity ladder stage counts | Add inventory health UI contract |
| G-07 | §18.4 | dataset_root / transport_variant / mirror_group / endpoint_role | Extend registry schema fields |
| G-08 | §19.4 | Split `nse_fno_ban` vs `nse_mwpl_percentages` | Split DAT-015 ownership |
| G-09 | §19.5 | FBIL vs live USD/INR roles | Harden MCX-002 |
| G-10 | §15.2 | Two-speed lane architecture | Add ops section under DAT |
| G-11 | §15.4 | Trust-producing combinations matrix | Add appendix table |
| G-12 | §16.12 | Per-source recovery SM + fallback hierarchy | Add ops contract |
| G-13 | §16.17 | Four E2E vertical slices | Add delivery pattern under §15 |
| G-14 | §16.10 | Line-level legacy scorer tests | Expand T-073/FUS-008 cases |
| G-15 | §17.2 | Full TradabilityRestriction fields + nse_t2t/bands/halts backlog | Expand FTR-035 + SRC backlog |
| G-16 | §19.8 | MATCHED / POSSIBLE_MATCH / DISTINCT / MANUAL_REVIEW | Extend event dedupe contract |
| G-17 | §10 | FOMO/expiry, side-by-side, daily review, journal hash snapshot | Add UI productivity IDs (research-safe) |
| G-18 | §15.5 | Data Confidence vs Evidence Rank vs UNCALIBRATED | UI label contract |

### 3.2 MISS-SCOPE (correctly out of MERGE product now — preserve as POSTPONE appendix)

| ID | Content |
|---|---|
| S-01 | INR 1L quantity tables, Kelly, averaging-down, multi-tranche |
| S-02 | entry_zone / stop / targets / R:R / binding_risk_cap in primary UI |
| S-03 | OpenAlgo paper/live ExecutionProvider methods |
| S-04 | Full ML library installs (River/Pandera/vollib) without separate approval |
| S-05 | Half-Kelly / probability promotion sample rules as live product |
| S-06 | Risk/action rail for order intent |
| S-07 | SEBI retail algo compliance for live trading |

### 3.3 Intentional MERGE improvements over HYBRID (do not reintroduce)

| Do not bring back | Why |
|---|---|
| Public READY as synonym for CONFIRMED | Confusion |
| WAIT_DATA / WAIT_OI as product states | Use reason codes |
| detail_score as decision evidence | FUS-008 |
| Quantity from evidence rank | False confidence |
| Permanent PK shadow voting | PK-019 |
| Fixed 1% circuit distance veto | Rejected in HYBRID §17.11 |
| Universal fetch of all 354 URLs | Rejected |

---

## 4. Correct build flow after this audit

```text
1) Authority: MERGE is the only build plan.
2) Content patch: fold G-01..G-18 into MERGE as stable IDs (doc amendment)
   OR implement from this audit file with explicit requirement IDs.
3) BUILD_STATUS: Q5-R0..R7 already at fixture ceilings.
4) Next implementation vertical (research-only):
   a. R0 residuals: inventory compiler H1A0 (G-01,G-02,G-06,G-07)
   b. Durable selection storage + live S0–S3
   c. Wire PRF profiles with named source sets (G-04,G-05)
   d. Expand tradability (G-15) + ban/MWPL/FX splits (G-08,G-09)
   e. R8 native core scanners under family caps
5) Do NOT implement S-01..S-07 until a new approved plan expands product boundary.
6) After each slice: VALIDATION + BUILD_STATUS.
```

---

## 5. Final comparative scorecard

| Dimension | Winner | Reason |
|---|---|---|
| Product safety / scope control | **MERGE** | No fake trading path |
| Decision state model | **MERGE** | Four states |
| Anti-double-counting | **MERGE** | Families + CG + zero bonus |
| Feature formula contracts | **MERGE** | FTR tables |
| Screener breadth (PK) | **MERGE** | Wholesale + quarantine |
| Runnable verticals | **MERGE** | Q5/R sequence |
| Source inventory depth | **HYBRID** | 354 map, defects, keys |
| Strategy source wiring | **HYBRID** | Named combinations |
| Ops reliability (scheduler/recovery) | **HYBRID** | SM + fallback hierarchy |
| Tradability realism | **HYBRID** (detail) + MERGE FTR-035 | Need both |
| Risk sizing | **HYBRID** (later) | Correctly postponed |
| UX productivity | **HYBRID** | FOMO, daily review, compare |
| Test ID density | **MERGE** | Larger T-suite |
| **Overall build authority** | **MERGE** | Project rule |
| **Overall content completeness** | **Neither alone** | MERGE + re-merge G-01..G-18 |

---

## 6. Honest limitations of this audit

- HYBRID ~2776 lines and MERGE ~260KB were covered by full section traversal of HYBRID and targeted full-section reads of MERGE core + greps for HYBRID-unique terms across MERGE.  
- Dated inventory counts (354/105/…) must be re-verified against the **current** workbook before activation claims.  
- Code-level “already implemented” claims in HYBRID §18.7 were not re-proven in this document; they require code observation at build time.

**No production-readiness claim.**  
**Next human decision:** approve folding G-01..G-18 into `new_merge_PLAN` as a numbered amendment, then build R0 inventory compiler + live S0–S3.
