# TrendForge — Discovery Detail Plan (modes, UI, PK shadow fields)

**Date:** 2026-07-27  
**Updated:** 2026-08-01 — modes/G\* catalogs clarified vs File A; S# build IDs = File A only  
**Status:** PLAN ONLY — product workflow detail for discovery, PK shadow, OI/UI tools  
**Name:** **Discovery Detail Plan** (never call this “File B”; File B = Hybrid)

### Catalog lock (do not invent alternate meanings)

| Catalog | Meaning here | Not the same as |
|---|---|---|
| **Modes A–E** | A intraday equity · B swing · C options-flow cheap FO · D positional · E MCX/commodity | Generic TA labels (breakout/pullback/reversal/squeeze/event) |
| **Integrity G1–G8** | Delivery, circuit, float/pledge, peer divergence, deal verify, options–spot, chain isolation, catalyst latency | File A product gates **G00–G14** |
| **Pipeline S#** | Detail only; map into File A **S3 cheap / S5 enrich** via File A §9.3 | FMR-002 story S# or any third S-map |
| **E1 / E2** | E1 official discovery · E2 PK **shadow** (no public state) | Dual Combined_Score engines |

**Scores:** No `Combined_Score` product. Public state only from File A resolver + §10.4. M-Factor / discovery rank prioritizes enrichment only.

## Authority (mandatory)

### Requirement authority

```text
current instruction
  → AGENTS.md
  → File A: docs/fable/new_merge_PLAN_2026-07-18.md  (R0–R18 plus File A CROSS/TDG residual IDs)
  → DECISIONS.md
  → FINAL_MERGE_PLAN.md via File A §25.21 (FMR-001..011)
  → Hybrid File B: TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md
       (only when File A §0.5/§25 points there)
  → THIS FILE + OPTIONS_INTELLIGENCE_PLAN.md  (detail only)
  -> PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md  (research math detail only)
```

### Implementation evidence (not authority)

```text
observed runtime → code and tests
  → docs/BUILD_STATUS.md + docs/VALIDATION.md
  → coverage CSV (traceability only)
```

**Rules**

- **Select one File A requirement ID: `R0-R18`, `CROSS-###`, or `TDG-GAP-###`; never `M/T/PK`.** File A requirement IDs select work; detail tags do not.
- `M0–M23`, `T0–T4`, `PK-A..PK-D` are **detail tags** for modules/UI. They map to R/FMR below.
- Before coding: open mapped **FMR** sections + Hybrid sections File A requires.
- Code/tests use **File A stable IDs**, not FMR alone.
- Research-only; no broker orders; PK never alone → CONFIRMED.
- **Do not hardcode** `sourceActivationReady`. Read current activation and state ceiling from **runtime + BUILD_STATUS + VALIDATION**.
- Inventory law: every usable key is (1) wired to mode/family/UI/stage, (2) on VERIFY batch, or (3) out of scope with reason.

## Professional mathematics navigation (detail only)

docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md does not add a milestone,
score, state or frontend promise. File A selects the owning work.

| Tool/detail | Governing owner | Mathematics use |
|---|---|---|
| M-Factor | R3 / FUS-009 | Show canonical bullish/ bearish evidence strength and balance only; never convert it to win probability |
| Index Dashboard / Sector Scope | R8, R9 | Residual return subtracts alpha plus aligned market and sector exposure; estimates are PIT/versioned |
| OI Analysis / OI Tracker | R12, FTR-020 | Keep the four observable OI_* codes already specified here; inferred intent is inspector commentary only and never a fact |
| Expiry Prediction | R16, R18 | Any future target-before-invalidation probability must be finite-horizon, cost-aware and calibrated; until then show descriptive range/scenario only |
| Strike Explorer / options tools | R12 plus mapped Final Merge/Options contracts | Existing parity, surface, max-pain, cash-Gamma and eligibility definitions remain canonical |
| Theta / gamma attribution / VRP context | R12/R16 through mapped FMR-005/FMR-006; R18 for model governance | Hidden-inspector research only: complete model/time convention, local delta-hedged variance attribution and same-horizon VRP context; `VRP_UNKNOWN` on missing proof; never a trade command |
| Microstructure fields | postponed pending source proof | Do not fabricate microprice, OFI or market impact from LTP, aggregate volume or shallow snapshots |
## Exhaustive detail-tag -> File A / FMR owners

This is the machine-validated navigation table. `File_A_owners` select the
controlling File A work; `FMR_refs` open mandatory addendum detail; `Notes`
carry only local prerequisites or scope caveats. No row creates a build order.

| Detail tag | File_A_owners | FMR_refs | Notes |
|---|---|---|---|
| **M0** | R0, R2, R15 | FMR-001, FMR-009, FMR-010 | depends_on: none |
| **M1** | R0, R2 | FMR-001, FMR-010 | depends_on: M0 |
| **M2** | R2 | FMR-001, FMR-002 | depends_on: M1 |
| **M3** | R2 | FMR-001, FMR-002 | depends_on: M2 |
| **M4** | R2, R3 | FMR-001, FMR-002, FMR-010 | depends_on: M3 |
| **M5** | R15 | FMR-009, FMR-010 | depends_on: M4 |
| **M6** | R4, R7 | FMR-008 | depends_on: M0 |
| **M7** | R4, R7 | FMR-008 | depends_on: M6 |
| **M8** | R4, R7, R3 | FMR-002, FMR-008 | depends_on: M4, M7 |
| **M9** | R10, R4 | FMR-008, FMR-010 | depends_on: M7; FMR-010 carries R10 acceptance ownership |
| **M10** | R12 | FMR-003, FMR-010 | depends_on: none inside the selected R12 packet |
| **M11** | R12, R3, R15 | FMR-003, FMR-004, FMR-005, FMR-006, FMR-007 | depends_on: M8, M10 |
| **M12** | R8, R9 | FMR-002, FMR-010 | depends_on: M5 |
| **M13** | R8, R9 | FMR-002 | depends_on: M12 |
| **M14** | R0, R15 | FMR-001, FMR-009, FMR-010 | depends_on: none |
| **M15** | R15, R16, R18 | FMR-010, FMR-011 | depends_on: M5, M8 |
| **M16** | R8, R13 | FMR-008, FMR-010 | depends_on: M9, M15; FMR-010 carries R8/R13 acceptance ownership |
| **M17** | R0 | FMR-010 | depends_on: M16; conditional File A amendment only |
| **M18** | R15 | FMR-009, FMR-010 | depends_on: M5 |
| **M19** | R15 | FMR-009 | depends_on: M4, M18 |
| **M20** | R12, R15 | FMR-007, FMR-009 | depends_on: M14, M18 |
| **M21** | R12, R15 | FMR-004, FMR-009 | depends_on: M4, M18 |
| **M22** | R12, R15 | FMR-003, FMR-004, FMR-005, FMR-006, FMR-009 | depends_on: M10, M11, M18 |
| **M23** | R2, R3, R15 | FMR-002, FMR-009 | depends_on: M4, M8, M18 |
| **T0** | R0 | FMR-001, FMR-010 | depends_on: none |
| **T1** | R2, R3 | FMR-001, FMR-002 | depends_on: T0 |
| **T2** | R8, R9 | FMR-002 | depends_on: T1 |
| **T3** | R12 | FMR-003..008 | depends_on: M10, M11 inside the selected R12 packet |
| **T4** | R0 | FMR-001, FMR-010 | depends_on: T0 |
| **PK-A** | R4 | FMR-008 | depends_on: none |
| **PK-B** | R7 | FMR-008 | depends_on: PK-A |
| **PK-C** | R10 | FMR-008, FMR-010 | depends_on: PK-B; FMR-010 carries R10 acceptance ownership |
| **PK-D** | R8, R13 | FMR-008, FMR-010 | depends_on: PK-C and governed parity evidence; FMR-010 carries R8/R13 acceptance ownership |

If a tag is used without a row above, stop and extend this table plus File A
mapping before coding. Every detail tag has a File A owner and validated FMR
coverage. These rows provide navigation and acceptance detail only; they never
select the next implementation milestone.
---

## Path index (refer while coding)

Absolute paths on this machine. Open these when implementing milestones.

### This plan and UI mocks

| Role | Path |
|------|------|
| **This detail catalog (non-authoritative)** | `D:\TrendForge\docs\DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` |
| Product build-order / safety law | `D:\TrendForge\docs\fable\new_merge_PLAN_2026-07-18.md` |
| Research signal console mock | `D:\TrendForge\docs\TRENDFORGE_RESEARCH_SIGNAL_CONSOLE.html` |
| System flow map (interactive) | `D:\TrendForge\docs\interactive_system_data_flow_map.html` |
| Compact brain (TrendForge) | `D:\TrendForge\docs\PROJECT_BRAIN.html` |
| Architecture + node guide | `D:\TrendForge\docs\ARCHITECTURE.md` |
| Validation + map audit | `D:\TrendForge\docs\VALIDATION.md` |
| Build status log | `D:\TrendForge\docs\BUILD_STATUS.md` |

### Options + OI/chain companion files (open when File A selects R12)

These four paths are **required reading** when building Live OI Dashboard, Option Chain Analyzer, or `options_intelligence/`. Keep this list in this plan so nothing is lost.

| # | File | Absolute path | When to open | Role |
|---|------|---------------|--------------|------|
| 1 | **OPTIONS_INTELLIGENCE_PLAN.md** | `D:\TrendForge\docs\OPTIONS_INTELLIGENCE_PLAN.md` | After File A selects R12 options work | **Options detail plan** (one package, contracts, day-one studies) |
| 2 | **GITHUB_OI_CHAIN_REFERENCE_REPOS.md** | `D:\TrendForge\docs\GITHUB_OI_CHAIN_REFERENCE_REPOS.md` | If official chain/OI build is stuck | **3 GitHub repos** as code fallback only (not data authority) |
| 3 | **shadowflow_deep_dive.md** | `D:\TrendForge\grok_plan\shadowflow_deep_dive.md` | Extra formula/ops detail after file #1 | OPT_FLOW + package law — read **§0–§17 only**; LEGACY ARCHIVE = do not implement |
| 4 | **convexity_intelligence_engine.md** | `D:\TrendForge\grok_plan\convexity_intelligence_engine.md` | Surface/PCR/max-pain/gamma detail after file #1 | OPT_SURFACE law — read **§0–§17 only**; LEGACY ARCHIVE = do not implement |

**Reference-use order after File A selects R12:**

```text
Selected owner: File A R12
  → required detail: FINAL_MERGE FMR-003..008
  → package catalog: D:\TrendForge\docs\OPTIONS_INTELLIGENCE_PLAN.md
  → code fallback only if blocked: D:\TrendForge\docs\GITHUB_OI_CHAIN_REFERENCE_REPOS.md
  → optional formula detail:
       D:\TrendForge\grok_plan\shadowflow_deep_dive.md
       D:\TrendForge\grok_plan\convexity_intelligence_engine.md
```

**GitHub repos listed inside file #2 (do not lose):**

- https://github.com/krishnabhokare27/et-signal-radar  
- https://github.com/raghavs-stack/nse-oi-dashboard  
- https://github.com/VarunS2002/Python-NSE-Option-Chain-Analyzer  

### Other options / priority notes

| Role | Path |
|------|------|
| Product priority (R0 first; options not next) | `D:\TrendForge\grok_plan\REAL_PATH_FORWARD.md` |
| Dual-engine audit (historical; dual voters rejected) | `D:\TrendForge\grok_plan\AUDIT_2026-07-23.md` |

**Permanent options law (see OPTIONS_INTELLIGENCE_PLAN for full text):** one package; M10 chain gate; shortlist first; day-one studies only; no dual scores; confidence ≠ P(win); VERIFY in §1A–1K.

### Input inventories / AI merge notes

| Role | Path |
|------|------|
| Links + 5-screener / 105 usable inventory notes | `D:\TrendForge\docs\links data use.txt` |

| Source link master workbook (if present) | `D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx` |
| Source registry (meaning) | `D:\TrendForge\TREND_FORGE_SOURCE_REGISTRY.md` |

### Code touchpoints (current repo)

| Role | Path |
|------|------|
| Scanner boss (to thin later) | `D:\TrendForge\backend\trendforge_api\scanner_scheduler.py` |
| Radar / source health | `D:\TrendForge\backend\trendforge_api\engine.py` |
| Gates + activation | `D:\TrendForge\backend\trendforge_api\gate_readiness.py` |
| Inventory compiler | `D:\TrendForge\backend\trendforge_api\source_inventory_compiler.py` |
| Market activity (vol gainers etc.) | `D:\TrendForge\backend\trendforge_api\market_activity.py` |
| Institutional endpoints list | `D:\TrendForge\backend\trendforge_api\institutional_sources.py` |
| Causal | `D:\TrendForge\backend\trendforge_api\causal_engine.py` |
| Harmonic / structure | `D:\TrendForge\backend\trendforge_api\harmonic_advanced.py` |
| Evidence | `D:\TrendForge\backend\trendforge_api\evidence_builder.py` |
| Derivatives / Greeks | `D:\TrendForge\backend\trendforge_api\derivatives_engine.py` |
| PK shadow harness | `D:\TrendForge\backend\trendforge_api\scanners\pk_compatibility.py` |
| PK fixture worker | `D:\TrendForge\backend\trendforge_api\scanners\pk_fixture_worker.py` |
| PK tests | `D:\TrendForge\backend\tests\test_q5_pk_compatibility.py` |
| API entry | `D:\TrendForge\backend\trendforge_api\main.py` |
| Frontend panel | `D:\TrendForge\frontend\app.js` |
| Proposed new (not created yet) | `D:\TrendForge\backend\trendforge_api\discovery\` |
| Proposed new (not created yet) | `D:\TrendForge\backend\trendforge_api\options_intelligence\` |
| PK shadow artifacts (runtime) | `D:\TrendForge\data\pk_shadow\` |

### Governance / plan authority

| Role | Path |
|------|------|
| Engineering rules | `D:\TrendForge\AGENTS.md` |
| Product build-order + safety law | `D:\TrendForge\docs\fable\new_merge_PLAN_2026-07-18.md` |
| Remaining build guide | `D:\TrendForge\docs\fable\remaining_build\README.md` |

### Deleted (content already in this file)

| Former file | Status |
|-------------|--------|
| `RESTRUCTURE_DISCOVERY_SCREENERS_PLAN_2026-07-27.md` | **Deleted** 2026-07-27 |
| `PKSCREENER_ENGINE2_INTEGRATION_PLAN_2026-07-27.md` | **Deleted** 2026-07-27 |
| `TrendForge_GPT56_Architecture_Audit(1).md` | **Deleted** 2026-07-27 (rules in §1M) |
| `HOW_TO_ASK_AI_ARCHITECTURE_WIRING.md` | **Deleted** 2026-07-27 |

---

## Canonical final-product visual target

- Persistent artifact: `D:\TrendForge\docs\TRENDFORGE_FINAL_PRODUCT.html`
- Local preview: `http://127.0.0.1:8765/TRENDFORGE_FINAL_PRODUCT.html`
- Component reference: `docs/TRENDFORGE_RESEARCH_SIGNAL_CONSOLE.html`

`TRENDFORGE_FINAL_PRODUCT.html` is the canonical fixture-backed visual target for the runtime frontend. The localhost URL is only a preview address and works while a local static server is running; the saved HTML file is the persistent authority.

File A R15 must implement the runtime frontend to match this artifact's information architecture: grouped Decision Tools navigation, primary decision terminal, compact secondary cards, Signals / How validated / Track record / Engines used tabs, source and calculation lineage, explicit public-state ceilings, responsive behavior and the hidden evidence inspector. Runtime values must come from canonical DTOs and APIs; fixture values must never be copied into production evidence.

`TRENDFORGE_RESEARCH_SIGNAL_CONSOLE.html` remains a component and interaction reference for signal cards, validation layers and track-record layout. It is not a competing final-product shell.
---

## How to use this detail catalog

1. Select the active `R0-R18` owner from File A; this file cannot select it.  
2. Resolve that R owner through the exhaustive detail-tag table and File A §25.21 FMR map.  
3. Use only the mapped capability, contract and acceptance details for the selected R work packet.  
4. Add or update tests required by that R milestone before implementation.  
5. Record observed results in `docs/BUILD_STATUS.md` and `docs/VALIDATION.md`.  
6. R12 options work requires eligible chain evidence and mapped FMR-003..008 detail.  
7. For each UI capability selected by File A, preserve API DTO, frontend presentation and verify-strip lineage requirements.  

---
## 1A. Frontend Decision Tools (left navigation) — required product map

### Shell layout (target)

```text
┌────────────┬──────────────────────────────────────────────┐
│ LEFT NAV   │  TOP: as-of · refresh warn · lightning · hist │
│            ├──────────────────────────────────────────────┤
│ M-Factor   │  MAIN: tool output + VERIFY panel             │
│ Sector Scope│     - Table / chart / cards                  │
│ …          │     - Calculation strip (inputs → formula →   │
│            │       output, source_key, data_date, hash)    │
│            │     - Research state banner (WAIT/WATCH/…)    │
└────────────┴──────────────────────────────────────────────┘
```

**Global rules for every panel**

| Rule | Meaning |
|------|---------|
| Research only | No broker order buttons |
| Verify strip | Always show: formula_version, inputs used, null reasons, source keys |
| Fail-closed | Missing source → empty table + `WAIT_*` reason, not fake zeros as “signal” |
| Activation | If the current observed runtime reports `sourceActivationReady=false`, banner `RESEARCH_SHADOW_ONLY` |
| Testability | Each panel has `GET …/debug` or expandable “Show calc” with the numbers a human can recompute |

### Left-nav tools (14) — calculation + API + UI + milestone

| # | Nav label | What it shows (output) | Core calculations (backend) | Primary sources / engines | FE verify / test | Milestone |
|---|-----------|------------------------|-----------------------------|---------------------------|------------------|-----------|
| 1 | **M-Factor** | Dual-hypothesis FUS-009 priority view (not win%) | Canonical bullish/ bearish `FUS-009` strengths, balance, class, completeness and freshness; no second score | Canonical selection claims + closed structure + typed context | Expand row -> selected/suppressed claims, support/opposition, versions and reasons | **M4, M5, M18** |
| 2 | **Sector Scope** | Sector leaders/laggards; stocks under each header | Sector %chg, sector volume z (if available), membership map; stock filter = activity ∩ sector | `nse_all_indices` (verify), sector constituents, volume gainers, instruments industry | Toggle sector → list updates; show map coverage % | **M2, M3, M5** |
| 3 | **M-Factor History** | Time series of M-Factor / component tags for a symbol | Point-in-time snapshots by session date; no look-ahead | Stored discovery/scan runs + journal | Date scrubber; compare day T vs T-1 components | **M15, M19** |
| 4 | **Index Dashboard** | NIFTY + BANKNIFTY (and breadth) research board | Spot/fut premium-discount if available, index OI/volume from live equity derivatives lists, gainer/loser breadth | `nse_live_equity_derivatives_*`, `nse_variations_*`, index chain when verified | Side-by-side NIFTY vs BANKNIFTY cards; as-of per metric | **M14, M20** |
| 5 | **OI Context** | Neutral FO OI board + link into **hidden inspector** (not top-level options dashboard) | Σ OI, OIΔ%, vol/OI; participant OI = regime only | `nse_fo_bhavcopy`, `nse_participant_oi`, `nse_oi_spurts` | Sortable OIΔ; lineage; no chain surface claim | **M4, M18, M21** |
| 6 | **OI Tracker** | Watchlist / shortlist OI over time | Session-to-session OI series (observable only) | FO bhav history archive + spurts | Chart + last 5 sessions; null if no history | **M19, M21** |
| 7 | **Heatmap** | Sector × metric heat (volume z, %chg, OIΔ) | Cross-sectional z-scores / ranks within session | Indices + bhav + FO aggregates | Click cell → opens Sector Scope / symbol list | **M5, M18** |
| 8 | **Strike Explorer** | Chain by strike — **hidden evidence inspector** (CIE v7.1 / §1M.2) | Bid/ask, OI, volume, IV, greeks | `nse_option_chain_*` | Not top-level until OOS+product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`); empty → `SURFACE_UNAVAILABLE` | **M10–M11, M22** |
| 9 | **Expiry context** | Max pain / walls — **hidden inspector** | Max pain (**index-only** first), walls, straddle; **NOT A FORECAST GUARANTEE** | Chain + FO bhav | Same placement as Strike; disable if chain bad | **M11, M22** |
| 10 | **Swing Finder** | Swing candidates list | Delivery %, multi-day structure, PK VCP/pipe optional, announcements/sponsor tags | Mode B sources + E2 swing pipes | Mode=SWING filter; delivery column verified vs bhav row | **M4, M8, M9** |
| 11 | **Speculation Movers** | High-speculation / high-activity names | RVol, range%, FO volume rank, most-active value, low delivery flag (speculation tag) | Volume gainers, most active, FO lists | Separate from “accumulation”; tag honesty | **M4, M18** |
| 12 | **Trend + Accumulation** | Combined view: structure trend + delivery/accumulation | Trend state from structure/harmonic; accumulation score from delivery z, price+delivery co-move | OHLCV + bhav delivery + structure | Two columns: trend label + accum label + raw delivery | **M4, M12** |
| 13 | **Accumulation Signals** | Focused accumulation-only board | Rising delivery + rising/holding price; sponsor buy disclosures; not FII aggregate | Bhav delivery, Reg29/PIT/deals | Exclude pure volume spikes with low delivery | **M4, M18** |
| 14 | **Multibagger Research** | Long-horizon **research** shortlist (not tips) | Positional mode: Nifty500 + MF sector tilt (AMFI delayed) + multi-week structure + low pledge preference; **explicit multi-year uncertainty** | Mode D sources + structure | Banner: research only; no price target promises | **M4, M14, M23** |

### Coverage of your earlier “minimum 7” (plan ≥ these)

| Minimum capability | Primary left-nav tool(s) |
|--------------------|---------------------------|
| Intraday F&O ranking | M-Factor + Speculation Movers + Heatmap |
| NIFTY / BANKNIFTY analysis | Index Dashboard |
| Options OI tracking | OI Analysis + OI Tracker |
| PCR movement | Strike Explorer + OI Analysis (when chain OK) |
| Expiry-range context | Expiry Range Context (estimate only) |
| Swing scanning | Swing Finder |
| Delivery / accumulation | Accumulation Signals + Trend + Accumulation |

**Plus extra:** Sector Scope, M-Factor History, Heatmap, Multibagger Research, PK pipes, safety gates.

### Frontend verification protocol (every tool)

For each panel, acceptance includes a **Verify strip**:

```text
[INPUTS] source_key, data_date, row counts, snapshot_id
[CALC]   canonical owner + formula/version (FUS-009 / FTR / options formula pin)
[OUTPUT] displayed number/tag
[RECOMPUTE] optional “copy JSON” for pytest / manual check
[STATE]  WAIT reason if any
```

**API pattern (suggested):**

```text
GET /api/v1/tools/{tool_id}?symbol=&as_of=&debug=1
→ {
    toolId, asOf, ceiling,
    rows: [...],
    debug: { inputs, formulaId, formulaVersion, lineage[] }
  }
```

Tool ids (stable):

`m_factor | sector_scope | m_factor_history | index_dashboard | oi_analysis | oi_tracker | heatmap | strike_explorer | expiry_prediction | swing_finder | speculation_movers | trend_accumulation | accumulation_signals | multibagger_research`

### UI mock growth requirement

`docs/TRENDFORGE_FINAL_PRODUCT.html` is the current static product-direction fixture and includes all 14 tools plus the shared evidence tabs. Runtime wiring belongs to File A R15 after canonical DTO/API owners exist. The static artifact must keep fixture/run labels and a Verify strip; it cannot be reported as live implementation.

---

## 1B. Product-contract integration status

| Feature area | Written contract | Static Final Product fixture | Runtime status |
|---|---|---|---|
| M-Factor market strip and full row | Present in 1D | Present | Canonical live BFF not implemented by this document |
| Dual FUS-009 strengths / balance / class | Present in 1D | Present | Requires File A R3 canonical output |
| Direction / readiness / public state separation | Present | Present | State remains File A-owned |
| Detection, RVol, OI, delivery, futures and ORB fields | Contracted | Representative fixture | Source/profile eligibility still required |
| Index Dashboard | Present in 1E | Present | Live chain/breadth depend on verified sources |
| OI Tracker and PCR timeline | Present in 1F | Present | Feature-specific chain eligibility required |
| Strike Explorer | Governing options detail retained | Inspector fixture | Runtime follows R12/R15 |
| Expiry Range Context | Present in 1G | Present | Estimate disabled for mixed/invalid bundles |
| Trend + Accumulation | Present in 1H | Present | EOD swing cadence only |
| Signals / How validated / Track record / Engines used | Present in 1K.1 | Present | Runtime follows canonical `ToolResultV1` |
| Track record | Locked `PIT_NOT_VALIDATED` | Locked, sample 0 | Unlock only through R16 |
| All 14 navigation tools | Mapped above | Present | No production claim |

**Verdict:** Product design and detail contracts are now aligned. Remaining work is runtime implementation under the single File A R0-R18 sequence, not more parallel planning.

---
## 1C. Product positioning (decision terminal, not beginner card-only)

| Style | What it is | TrendForge choice |
|-------|------------|-------------------|
| **Power Bull–like** | Pattern → BUY/SELL → entry/stop/target card only | Optional **card view** on M-Factor / signal console |
| **TradeNethram–like** | Market condition → ranked F&O → OI/PCR → index confirm → decision | **Primary shell** (this plan) |

**Primary UX:** decision terminal with left tools.  
**Secondary UX:** compact signal cards (already mocked).  
Both share same backend DTOs and Verify strip.

---

## 1D. M-Factor Scanner (main intraday F&O ranking) - governing detail contract

### Purpose

Shortlist eligible NSE F&O names without opening hundreds of charts. M-Factor is a transparent presentation and prioritization view over the authoritative File A `FUS-009` resolver. It must not calculate a second hidden weighted score and it must never be presented as win probability, expected return or trading advice.

### Applicable profile and snapshot law

- Profile: NSE F&O equities only. Broad cash-equity, index, MCX and swing profiles use their own contracts.
- Every row is computed from one immutable `run_id` and `snapshot_bundle_id`.
- Price, OI, delivery, sector, event and options observations from different runs cannot be silently mixed.
- Current price may refresh visually, but it cannot rewrite the detection snapshot or its historical class.

### Top market-condition strip (required)

| Field | Calculation / source | Frontend presentation |
|---|---|---|
| Market condition | Versioned breadth + closed index structure -> `BULLISH_MARKET`, `BEARISH_MARKET`, `MIXED` or `WAIT_DATA` | Prominent regime banner |
| Advancing / declining | Eligible F&O universe breadth | Counts plus denominator |
| Average move | Mean session change for the declared universe | Percent with universe version |
| Bullish / bearish classes | Count from this immutable scan | Counts, never market probability |
| Data cut-off | Maximum eligible `available_at` included | IST timestamp |
| Run truth | `run_id`, `snapshot_bundle_id`, profile, source ceiling | Always visible in Verify strip |

### Single rank law (no second score)

```text
long_strength  = FUS-009 evidence_strength for the bullish hypothesis
short_strength = FUS-009 evidence_strength for the bearish hypothesis
m_balance      = long_strength - short_strength
rank_strength  = max(long_strength, short_strength)
```

Both hypothesis strengths use the File A `FUS-009` representative-claim, family-weight, missing-family, contradiction and no-renormalization rules. The M-Factor API consumes the selected and suppressed claims returned by the resolver instead of recomputing factor contributions.

Ranking order is `rank_strength` descending, then completeness descending, freshness descending, and symbol ascending for deterministic ties.

### Directional class (fixture-only cut-points)

| `m_balance` | `directional_class` |
|---:|---|
| `>= +60` | Strong Bull |
| `+20` to `+59.99` | Bull |
| `-19.99` to `+19.99` | Neutral |
| `-59.99` to `-20` | Bear |
| `<= -60` | Strong Bear |

The versioned cut-points are `M_FACTOR_CLASS_V0`. They are uncalibrated research defaults until R16 PIT/OOS evidence and explicit approval permit promotion.

### Direction, readiness and public state are separate

| Field | Values | Meaning |
|---|---|---|
| `directional_class` | Strong Bull / Bull / Neutral / Bear / Strong Bear | Relative eligible evidence direction |
| `readiness_tag` | DEVELOPING / SETUP_READY / EXPIRED / INVALIDATED | Setup lifecycle detail |
| `public_state` | WATCH / WAIT / CONFIRMED / REJECT | File A state machine only |

A strong class cannot bypass a WAIT gate. `SETUP_READY` is not `CONFIRMED`. An expired or invalidated candidate instance remains historically visible.

### Per-stock table (visible or toggleable)

| Field | Owner / logic | Safety note |
|---|---|---|
| Symbol, sector, profile | PIT instrument and sector map | F&O eligibility required |
| Directional class | `m_balance` -> `M_FACTOR_CLASS_V0` | Not advice |
| Long / short strength | Two `FUS-009` hypotheses | Evidence strength, not probability |
| M-balance / rank strength | Difference / maximum | No extra votes |
| Detection price / time | First qualifying immutable snapshot | Never rewritten by current price |
| Current price / session change | Latest eligible quote | Cadence and age shown |
| Relative volume | Session volume / versioned comparable baseline | Same activity root counted once |
| OI velocity / OI change | Matched contract/expiry observations | Observable participation only |
| Delivery percent | Official EOD delivery where available | Swing context; never intraday delivery |
| Futures OI / volume / basis | Eligible futures package | One derivatives correlation group |
| OI-price code | Four observable co-move codes from Product Law C-05 | No long/short buildup or institution claim |
| ORB / closed structure | Versioned closed-bar rule | Unclosed bars cannot permanently qualify |
| Readiness / hold time | Lifecycle evaluator | Separate from state |
| Edge label | Discrete UI summary of selected evidence and conflict | Not EV or hit rate |
| Sector / index alignment | Context resolver | Cannot invent stock direction or sponsor |
| PK tags | Finite shadow/native-parity output | No state or rank authority unless natively promoted |
| Safety / restriction | Surveillance, ban, MWPL, identity and freshness gates | Explicit WAIT/REJECT reasons |
| Public state / next proof | File A state machine | Show exact blocker |

### Eligible evidence families shown in expansion

Structure, participation, derivatives, delivery/accumulation, sponsor events, sector/regime, optional PK shadow diagnostics and optional options context remain typed and capped. Mirrored or same-root values may improve explanation but cannot manufacture independent support. Options surface and flow form at most one `OPTIONS_CONTEXT` package contribution.

### Index conflict

Bull/Strong Bull stock evidence plus Strong Bear index structure and weak breadth emits `INDEX_CONFLICT`. If index agreement is profile-required the public state is WAIT. If it is optional, the UI may weaken the displayed class but cannot create an opposite trade, change quantity or invent sponsor evidence.

### API and UI contract

`GET /api/v1/tools/m_factor?debug=1` is a read-only BFF/composition route over canonical selection, feature, gate and source-health outputs. It performs no independent scoring and cannot write state. Row expansion shows selected/suppressed claim IDs, raw and normalized values, family/group, weights, support/opposition, formula versions, source ages and reasons.

### Acceptance tests

1. Fixed eligible claims produce fixed long strength, short strength, balance, class and deterministic ordering.
2. Duplicated activity, OI, transport and mirror roots do not raise strength.
3. Missing required evidence remains zero, is not renormalized, and emits WAIT.
4. Strong Bull plus a hard gate remains WAIT or REJECT according to File A.
5. Open-bar ORB cannot permanently emit SETUP_READY.
6. Current-price refresh does not rewrite detection price/time or the frozen run.
7. Index conflict is visible and cannot manufacture direction or quantity.
8. Debug output equals the canonical resolver output exactly.

---
## 1E. Index Dashboard (NIFTY + BANKNIFTY) - context contract

### Purpose

Show NIFTY and BANKNIFTY side by side so isolated stock evidence is interpreted against closed index structure, breadth and one capped derivatives package.

### Required board for each index

| Block | Fields / rule |
|---|---|
| Identity | Index, profile, session, run and snapshot bundle |
| Spot / futures | Spot, session change, futures price, basis and observation age |
| Directional context | Closed-bar Strong Bull...Strong Bear or `WAIT_DATA`; context only |
| Breadth | Advancers, decliners, denominator and average move |
| PCR | OI PCR and volume PCR separately, with inclusion policy and coverage |
| OI geometry | Call/put concentration and nearest eligible walls, never writer identity |
| Structure | Candles, declared closed bar, versioned moving averages and levels |
| Volume | Futures/index activity with source age |
| Explanation | Deterministic supporting, opposing, missing and conflicting conditions |
| Permission | Data quality, state ceiling and next missing proof |

All blocks in one board share the same `run_id`/`snapshot_bundle_id`. If index chain data is unavailable, spot/structure/breadth may remain visible while PCR/walls are `UNKNOWN` with `WAIT_CHAIN`; they are never fabricated as neutral.

### Stock conflict behavior

```text
Stock directional class: BULL
Index context: STRONG BEAR
Breadth: weak
=> INDEX_CONFLICT
```

The conflict weakens optional context or produces WAIT when the profile requires index agreement. The dashboard never predicts the close, creates a stock sponsor claim or acts as an independent confirmation vote.

### Sources and engine ownership

Use verified index spot/closed bars, breadth/turnover, index futures, participant OI as regime context and an eligible index option snapshot. Any deterministic explanation is generated from those typed facts. Optional AI prose, if later allowed, is non-authoritative and cannot add facts or change a state.

### Acceptance tests

- NIFTY and BANKNIFTY observations from different runs cannot compose one board.
- Missing chain leaves PCR/walls unknown while independent spot/structure remains usable.
- Open candles cannot permanently set directional context.
- Index conflict is identical on dashboard, M-Factor row and evidence inspector.
- Participant OI is labelled regime context, not stock-level live flow.

---
## 1F. OI Tracker + PCR timeline - observable-path contract

### Purpose

Show the path of open interest and PCR through aligned observations instead of over-interpreting one snapshot.

### Required fields

| Field | Rule |
|---|---|
| Opening PCR | First eligible observation after the declared open |
| Current PCR | Latest eligible observation from the same inclusion policy |
| OI PCR / volume PCR | Separate series; denominator-zero -> UNKNOWN |
| Timeline | Observation time, bundle ID, coverage and freshness per point |
| Call / put activity | OI and volume change, no buyer/writer identity |
| Strike changes | Matched strike/expiry observations or inspector link |
| OI-price code | Only `OI_RISE_PRICE_RISE`, `OI_RISE_PRICE_FALL`, `OI_FALL_PRICE_RISE`, `OI_FALL_PRICE_FALL` |
| Trend descriptor | Rising / falling / flat PCR using a versioned threshold |
| Threshold zones | Research reference lines, never truth or probability |
| Missing points | Gap reason; no interpolation unless method and eligibility are explicit |

### Interpretation boundaries

PCR is context-dependent. Falling PCR can result from several different public-position changes, and public OI does not reveal buyer, writer, dealer or institution identity. Every interpretation must be shown beside price, strike movement, expiry/DTE and chain quality.

If a chain snapshot is invalid, FO EOD OI history may remain visible under its own cadence while PCR/strike features become `WAIT_CHAIN` or `UNKNOWN`. A successful empty result remains different from a blocked, parse-failed or incomplete chain.

### Acceptance tests

- Opening and current PCR use the same policy and expiry set.
- Zero call OI denominator returns UNKNOWN, not zero or infinity.
- Expiry roll starts a new comparable series unless an explicit economic-coordinate bridge exists.
- Same timestamp with different bundle IDs cannot merge.
- Missing interval remains a visible gap.
- No UI copy contains writer, dealer or institutional-position claims.

---
## 1G. Expiry Range Context - estimate-only contract

The user-facing name is **Expiry Range Context**, not a prediction promise.

### Preconditions

A valid same-expiry option surface must prove underlying/contract identity, expiry, strike continuity, aligned spot/forward time, quote/OI policy, coverage, freshness and snapshot lineage. Feature eligibility is independent: valid PCR does not automatically validate max pain, walls, IV/skew or a range estimate.

### Required fields

| Field | Rule |
|---|---|
| Conventional max pain | Deterministic value plus policy/version |
| Distance to spot/forward | Absolute and percent, timestamp aligned |
| Component agreement | Agreement among eligible range components; not probability |
| Data quality | Coverage, liquidity, quote age and feature status |
| Estimated range | Low/high plus method, horizon, DTE and sensitivity |
| OI walls | Eligible call/put concentrations with migration state |
| Pain curve | Conventional curve and sensitivity, not destination forecast |
| OI distribution | Call/put OI and volume by strike |
| Supporting/opposing/missing | Exact components and null reasons |
| Public ceiling | `UNKNOWN`, WATCH or WAIT according to profile/gates; options cannot confirm alone |

The options package may report contextual `SUPPORT`, `WEAKEN`, `CONFLICT` or `UNKNOWN`. It cannot independently invent stock/index direction. Max pain and OI walls are reference levels that can move; expiry/news/liquidity risk remains explicit.

### Acceptance tests

- Mixed expiries or bundle IDs block the estimate.
- Partial-chain eligibility cannot leak from PCR into max pain or range.
- Sensitivity changes are visible; one precise target is never shown.
- `component_agreement` and `data_quality` are never labelled confidence or win chance.
- Empty/stale/one-sided chains produce explicit UNKNOWN/WAIT reasons.
- Conventional max pain is an expiry reference, not an entry or target.

---
## 1H. Trend + Accumulation - swing research contract

### Purpose and profile

Find NSE swing candidates with closed multi-day structure and official EOD delivery-backed participation. This profile is not an intraday scalp engine and delayed aggregate institutional data cannot be described as live stock buying.

### Required fields

| Field | Rule |
|---|---|
| Symbol / current price | PIT identity and observation age |
| Closed trend | Versioned daily/weekly structure owner |
| Accumulation evidence | Delivery ratio/trend plus price co-movement; raw values visible |
| Relative volume | Comparable multi-session baseline |
| Range context | 30-day compression and location, versioned |
| Directional class | Bull / Neutral / Bear research context from eligible evidence |
| Readiness tag | DEVELOPING / SETUP_READY / EXPIRED / INVALIDATED |
| Public state | WATCH / WAIT / CONFIRMED / REJECT from File A only |
| Entry zone | Non-executable research geometry from closed structure |
| Invalidation reference | Structural invalidation plus declared buffer; not an order |
| Targets | Structural objectives with obstacles and uncertainty |
| Explanation | Deterministic support, opposition, missing proof and next condition |
| Snapshot truth | Run, bundle, data cutoff, formula/source versions |

`SETUP_READY` never means CONFIRMED. An unclosed bar cannot permanently qualify the setup. Entry/invalidation/targets have no quantity, account, order or autonomous-routing semantics.

### Evidence ownership

Closed structure owns direction and scenario geometry. Delivery/participation may support or oppose it. Sponsor filings remain a separate family. PK VCP/compression is shadow or natively promoted under its own contract. Aggregate FII/AMFI context cannot become stock-level sponsor proof.

### Acceptance tests

- Intraday volume cannot populate EOD delivery fields.
- Open daily/weekly bars cannot permanently qualify the setup.
- Missing official delivery stays UNKNOWN; weights are not renormalized.
- Entry, invalidation and targets derive from one frozen adjusted-price snapshot.
- Corporate-action revision invalidates affected geometry and creates a new version.
- Public state and readiness tag cannot be substituted for each other.
- No quantity, broker or order field is exposed.

---
## 1I. Product wording and safety law

| Unsafe or ambiguous wording | Required wording / behavior |
|---|---|
| M-Score, confidence, conviction, win chance | `long_strength`, `short_strength`, `m_balance`, `rank_strength`, `component_agreement`, `data_quality`; evidence strength is not probability |
| Buildup, unwinding, writer, dealer, institutional OI | Observable OI/price/volume concentration and change only |
| Expiry prediction or probable target | **Expiry Range Context**, estimated interval, method, sensitivity and uncertainty |
| Signal means ready | Keep `directional_class`, `readiness_tag` and `public_state` separate |
| Stop-loss / target order | Non-executable invalidation reference and research objective |
| Delayed delivery/institutional data is live | Show actual cadence and use-specific freshness; delayed context stays delayed |
| Missing value rendered as zero | `UNKNOWN` plus reason; observed zero remains `0` |
| HTTP 200/parser call proves data | Require identity, schema, freshness, completeness, authority and feature eligibility |
| Performance fixture | `PIT_NOT_VALIDATED`, sample count `0`, win rate and benchmark delta `null` |
| Broker execution | Absent; no account, position, order, quantity or autonomous route |

These labels are required in the primary tool views, compact cards, exports and hidden inspector.

---
## 1J. End-to-end: discovery + PK + thinking engines → left nav

```text
E1 Official discovery (sector, vol, OI EOD, deals, safety)
E2 PK pipes (ORB/breakout/VCP/momentum) → TECH_SHADOW tags
        ↓
M-Factor table (rank F&O + classes + all columns)
Sector Scope / Heatmap (headers)
        ↓
Index Dashboard (NIFTY/BN) → conflict badges on M-Factor rows
OI Analysis / OI Tracker / PCR timeline
Strike Explorer / Expiry context (if chain OK)
        ↓
Structure + Harmonic (direction)
Evidence + Causal (agreement)
        ↓
Swing / Accumulation / Speculation / Multibagger boards
        ↓
Signal cards (optional compact view) + Track record (journal)
        ↓
Verify strip on every number for FE/pytest recompute
```

**No thinking engine left out of the map:**

| Engine | Feeds which nav tools |
|--------|----------------------|
| Compiler / Gates / Activation | All (ceiling banner) |
| Safety | All (veto) |
| Calendar / Market context | Index, M-Factor market strip |
| Market activity | M-Factor, Spec movers, Sector |
| FO bhav / spurts | OI Analysis, Tracker, M-Factor OI cols |
| Option chain + surface/flow package | Strike, Expiry, PCR timeline |
| Structure / Harmonic | M-Factor class, Trend+Accum, Swing |
| Features | RVol, delivery metrics |
| Evidence / Causal | Explanations, sponsor tags |
| PK Engine 2 | ORB/pipe labels on M-Factor / Swing |
| Risk engine | Entry/stop/target geometry only (qty=0) |
| Derivatives engine | Greeks on Strike Explorer |
| Q5 / Institutional / TradeVision | Side/export — not left-nav bosses |

---

## 1K. Frontend acceptance matrix

| Test | Pass criteria |
|---|---|
| FUS-009 golden | Fixed claims -> fixed long/short strengths, balance, class and order |
| Null/failed source | UNKNOWN/WAIT with reason; no hidden zero or neutral evidence |
| Valid empty | Distinct from blocked, transport, parse and schema failure |
| Index conflict | Badge and state/class effect agree across M-Factor, dashboard and inspector |
| Chain unavailable | Independent spot/OI facts remain; chain features show WAIT_CHAIN/UNKNOWN |
| PK unavailable | Official discovery remains usable; PK cannot alter state or rank |
| Activation false | No CONFIRMED styling or state, regardless of directional class |
| Delivery cadence | EOD delivery cannot populate intraday evidence |
| Atomic run | Tool rejects mixed `run_id` or `snapshot_bundle_id` inputs |
| BFF parity | `/api/v1/tools/*` values exactly match canonical domain DTOs |
| Track record lock | `PIT_NOT_VALIDATED`, sample 0, no win rate or benchmark delta |
| Accessible states | Color is not the only state indicator; keyboard and screen-reader labels exist |
| Responsive shell | No document overflow; nav/table use contained scrolling on mobile |
| Debug/Verify | Displayed number equals inputs, formula/version and canonical API payload |

---

## 1K.1 Shared ToolResult and evidence-tab contract

All 14 decision tools use one composition envelope. Specialized DTOs may add fields but cannot weaken it.

```text
ToolResultV1
  tool_id
  tool_version
  profile_id
  instrument_id / universe_id
  run_id
  snapshot_bundle_id
  publication_id
  observed_at
  data_cutoff
  data_mode
  public_state
  state_ceiling
  gate_codes[]
  directional_class?        # optional, never public state
  readiness_tag?            # optional, never public state
  metrics: FeatureObservationV1[]
  selected_claim_ids[]
  suppressed_claim_ids[]
  supporting[] / opposing[] / missing[] / conflicts[]
  source_result_ids[]
  dataset_roots[] / correlation_groups[]
  formula_versions[] / source_contract_versions[]
  warnings[] / next_required_proof[]
```

### Route boundary

```text
GET /api/v1/tools/{tool_id}
```

This is a read-only frontend composition/BFF route. It calls canonical selection, features, options, source-health and history contracts and returns one atomic view. It must not implement a second scoring engine, rewrite state, fabricate missing fields or merge different runs. Canonical calculation owners remain the domain modules and versioned `/api/v1/selection/*`, feature and options routes.

### Shared tabs

| Tab | Required content |
|---|---|
| **Signals** | Primary decision-useful values, explicit state/ceiling, direction/readiness separation and next proof |
| **How validated** | Source contract, identity, freshness, completeness, formula/version, family cap and gate result |
| **Track record** | Locked as `PIT_NOT_VALIDATED`; sample count 0 and performance fields null until R16 passes |
| **Engines used** | Calculation owner, evidence family, correlation group, state permission and failure behavior |

### Profile applicability

| Tool family | Allowed profile |
|---|---|
| M-Factor / speculation / intraday heat | Eligible NSE F&O equities |
| Index Dashboard / PCR timeline | NIFTY and BANKNIFTY index profiles |
| OI / Strike / Expiry Range Context | Verified derivatives with valid identity and same-expiry snapshot |
| Swing Finder / Trend + Accumulation | NSE swing profile with closed EOD bars and official delivery cadence |
| MCX tools | Separate commodity, contract-master, expiry/session and local-market profile |
| Multibagger Research | Long-horizon research profile; no target promise |

### File A placement (not a second sequence)

| File A owner | Product work unlocked |
|---|---|
| R0 | Freeze contracts, profile applicability, atomic run/snapshot and wording law |
| R1 | `ToolResultV1` fixture DTO and primary radar/tool shell |
| R2 | Canonical cheap live-safe pipeline; WATCH/WAIT/REJECT ceiling |
| R3 | Authoritative `FUS-009` dual-hypothesis composition and anti-double-counting |
| R4/R7 | Finite PK compatibility/shadow evidence only |
| R5/R9 | Closed structure, ORB and lifecycle/readiness behavior |
| R6/R11 | Sponsor, delivery, F&O/MCX enrichment under profile gates |
| R12 | OI/PCR/Strike/Expiry Range Context with feature-specific eligibility |
| R15 | Runtime tool navigation, compact primary view and hidden inspector |
| R16 | PIT track-record unlock only after leakage, costs, survivorship and sample gates |
| R17 | Optional disabled-by-default read-only OpenAlgo data boundary |
| R18 | Governed model/challenger promotion, drift and rollback |

The static `docs/TRENDFORGE_FINAL_PRODUCT.html` is a fixture product-direction artifact only. It is not evidence that runtime APIs, live sources or production states exist.

---
## 1. Detail capability catalog (never a build order)

File A selects one requirement ID first. When that requirement is owned by `R0-R18`, the `M*` rows below are retained
only to locate requirements, proposed modules, prerequisites and acceptance
evidence for that selected R owner. Do not code these rows from top to bottom.

| ID | Track | Name | Deliverable (code) | Acceptance (done when) | depends_on detail tags inside the selected R packet |
|----|-------|------|--------------------|------------------------|----------------------------------------------------|
| **M0** | T0 | Radar COMPLETE + async run + **vocab freeze** | COMPLETE runs only; async token; **state rename table** (§1M.7): no internal `final_state` unless master owner; Stage2 CONFIRMED→`STAGE2_THRESHOLD_MET`; statusGroup→`analysis_disposition`. Lineage IDs: `run_id`, `request_id`, `manifest_hash`, `input_bundle_root`, `publication_id` (not run_hash alone) | Tests + import guards for legacy field names | — |
| **M1** | T0 | Manifest + dual permissions + **G1** | `RunManifestV1` / `GateDecisionManifest`; **`research_execution_permission`** vs **`state_publication_permission`** (when observed runtime activation is false → public WAIT, shadow collect OK). Demo isolation (`data_class=DEMO`). **G1** delivery_integrity prototype | Snapshot readable; dual perms tested; delivery fixtures | M0 |
| **M2** | E1 | Sector map + fail-soft headers | symbol→sector map; fallbacks; SECTOR_UNKNOWN | Unit tests empty map / partial map | M1 |
| **M3** | E1 | Sector-relative volume + **G2** | Volume gainers ∩ leading sectors. **G2** circuit_behavior. **ASM/GSM soft-flag** (§1M.1): not auto hard REJECT without product-plan safety disposition | Fixtures; no direction from discovery alone | M2 |
| **M4** | E1 | Discovery S2 + modes + **G3/G8** + adaptive budgets | POST /api/discovery/run?mode=… Full §4 keys. **Adaptive** `discovery_budget` / `shortlist_budget` in RunManifest (not fixed 40–60 / 10–25). **G3** float_risk · **G8** catalyst. Contracts: DiscoveryCandidateV1, SourceResultV1, HypothesisV0Config, ManipulationRiskV1, FeatureObservationV1 | 5 modes; OPT_SURFACE weight 0; F&O modes need eligibility master not raw equity universe alone | M3 |
| **M5** | UI | Radar headers + shadow banner | Group by sector/macro; RESEARCH_SHADOW_ONLY when observed runtime activation is false | Frontend shows headers; no CONFIRMED styling from discovery | M4 |
| **M6** | E2 | PK pin + sidecar | Pin MIT commit/Docker; CLI/Docker runner writes artifact under data/pk_shadow/ | Artifact SHA-256; timeout/crash → empty set | M0 |
| **M7** | E2 | PK shadow API | POST /api/v1/shadow/pkscreener/run + result GET; sanitize rows | Tests: crash isolation; oversized reject; no confirm flag | M6 |
| **M8** | E1+E2 | Merge engines | Default E1_THEN_E2; config INTERSECT / UNION_RANK | Radar columns E1 tags + E2 pipe; PK down still E1-only | M4, M7 |
| **M9** | E2 | Pipe profile library | Register pipes: INTRADAY_BREAKOUT, SWING_VCP, REVERSAL (params versioned) | Config-driven; no hardcode in API | M7 |
| **M10** | Opt | Chain unblock + **G7** + SnapshotBundleV1 | Session + fixture + live. Per-symbol try/except. **UI:** surface in **hidden inspector** only (§1M.2). Companions: OPTIONS_INTELLIGENCE_PLAN + GitHub + shadowflow/CIE | Structured or WAIT_CHAIN; batch isolation; snapshot_bundle_id | parallel |
| **M11** | Opt | S3–S6 package + **G6** + feature eligibility | Adaptive shortlist; one OPTIONS_PACKAGE. **G6** spot/options diverge. Per-feature status (PCR OK while RR25 UNKNOWN). **Max pain index-only** until stock study promotion. Math tests G-10 | No Combined_Score; SUPPORT/WEAKEN/CONFLICT/UNKNOWN only; index max-pain gate | M8, M10 |
| **M12** | Arch | Controllers + **B0–B6 barriers** | Ingestion/Gate/Symbol stages; barriers freeze manifest → atomic publish; dataset_root / correlation_group tracking | God-object reduced; order-independent ranks; tests pass | M5 stable |
| **M13** | Arch | Parallel symbol CPU | Worker pool; serial DB; SQLite WAL; no Redis day-1 | Faster scan; no corruption | M12 |
| **M14** | Data | Config VERIFY + **G4** + F&O master | §6.4 P0/P1. **G4** peer divergence. **F&O eligibility master** required for F&O modes (§1M.4) | VERIFY + eligibility contract in BUILD_STATUS | parallel |
| **M15** | Quality | Journal / OOS + PIT rules | Beat volume-only baseline; no future constituent leakage; `available_at` on every SourceResult | Beats baseline or demote; PIT tests pass | M5+ |
| **M16** | Gov | Native PK promotion | Promote one pipe to TECH_NATIVE via parity harness | pk_compatibility APPROVE; can_support_confirmed still false until product-plan amendment | M9, M15 |
| **M17** | Gov | product-plan amendment (if needed) | Formal IDs for discovery families + options package | Only if productizing CONFIRMED language | before CONFIRMED |
| **M18** | UI | Shell + VerifyStripV1 + **OI Context** | Left nav; Verify strip; **Strike/Expiry in hidden inspector**; security: bind 127.0.0.1 default | No number without inputs; no top-level options dashboard | M5 |
| **M19** | UI | M-Factor + History + **G5** | M-Factor API; **G5** deal verify; co-move labels only (§1M.5) | FE matches backend; no intent labels | M4, M18 |
| **M20** | UI | Index Dashboard | NIFTY + BANKNIFTY + breadth; FeatureObservationV1 fields | As-of per metric; empty→WAIT | M14, M18 |
| **M21** | UI | OI Context tables + OI Tracker | FO OI tables + history (not chain surface) | Sort/filter; lineage visible | M4, M18 |
| **M22** | UI | Strike + Expiry **in inspector** | Chain grid + max-pain context; promote top-level only after OOS+product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) | Chain empty banner; disclaimer | M10, M11, M18 |
| **M23** | UI | Swing / Spec / Accum / Multibagger | Four list tools wired to modes | Delivery/accum columns testable vs bhav | M4, M8, M18 |

### Unordered capability groups

These groups preserve the former sprint themes without assigning a global
schedule. Open a group only after the selected File A requirement maps to an R owner, then use the
machine table above and the matching detail rows for local `depends_on` tags.

| Capability group | Theme | Detail tags and retained deliverables |
|---|---|---|
| Authority and lineage | COMPLETE radar, async, vocabulary, dual permissions and delivery integrity | M0, M1, T0, T4 |
| Source and discovery | Maturity, scope, sector map, adaptive budgets, ASM handling, modes and discovery contracts | M2, M3, M4, T1 |
| Trader surfaces | Headers, shadow banner, Verify strip, OI Context and inspector-only Strike/Expiry | M5, M18, M19, M21, M22, M23 |
| PK shadow compatibility | Finite sidecar/CLI evidence, shadow API, merge rules and pipe definitions | M6, M7, M8, M9, PK-A, PK-B, PK-C |
| Modular execution | Controllers, barriers, parallel CPU and dataset-root/correlation controls | M12, M13, T2 |
| Options research | Chain quality, feature eligibility, package outputs and scenario labels | M10, M11, T3 |
| Configuration and index context | Config verification, F&O master and index dashboard | M14, M20 |
| PIT journal and validation | Outcome lineage, M-Factor, OI history, swing boards and options math tests | M15 |
| Native promotion | Governed parity and native PK promotion under File A ownership | M16, PK-D |
| Conditional amendment | Product-plan amendment only when File A explicitly selects it | M17 |

The groups are unordered catalogs. They do not authorize a next step, phase,
sprint or implementation sequence.
---

## 1M. Product law (safety, UI, budgets, lineage, contracts)

These rules are **in force for coding**. They are not optional notes.

### Quick index — core rules (C-01…C-07)

| ID | Topic | Adopted rule |
|----|--------|--------------|
| **C-01** | ASM/GSM soft-flag | Soft-flag only — full steps in **§1M.1** (no silent HARD DROP) |
| **C-02** | Options UI | Strike/Expiry (surface) in **hidden inspector**; left-nav **OI Context** only until OOS + product-plan amendment |
| **C-03** | Candidate counts | **Adaptive** `discovery_budget` / `shortlist_budget` in RunManifest — not fixed 40–60 / 10–25 |
| **C-04** | F&O universe | `nse_equity_universe` ≠ F&O proof; need **versioned F&O eligibility master** for F&O modes |
| **C-05** | OI labels | Observable co-move codes only — **no** long buildup / short covering / smart money |
| **C-06** | Lineage IDs | `run_id`, `request_id`, `manifest_hash`, `input_bundle_root`, `publication_id` (+ optional `short_display_id`) |
| **C-07** | State vocab | Stage2 CONFIRMED→`STAGE2_THRESHOLD_MET`; `statusGroup`→`analysis_disposition`; no module publishes `final_state` unless master owner; machine-disable legacy |

### Quick index — build gaps (G-01…G-16)

| ID | Item | Where |
|----|------|--------|
| **G-01** | Source maturity ladder (lite 4-stage for S2; full for P0/P1 VERIFY) | Source registry + M4/M14 · detail §1M.9 |
| **G-02** | 8-class gate taxonomy in **logs/DTOs**; UI collapses to WAIT_DATA / WAIT_QUALITY / WAIT_SAFETY / REJECT | gate_readiness + FE banners |
| **G-03** | Barriers **B0–B6** (manifest freeze → atomic publish) | M12 · detail §1M.10 |
| **G-04** | `research_execution_permission` vs `state_publication_permission` | RunManifestV1 / M1 · §1M.8 |
| **G-05** | Formal DTOs as coding gates | M1/M4/M10/M11/M18 · §1M.12 |
| **G-06** | Feature-specific options eligibility | M11 surface · §1M.13 |
| **G-07** | Source capability matrix fields | Registry schema |
| **G-08** | `dataset_root` + `correlation_group` anti double-count | Candidates + options package · §1M.11 |
| **G-09** | `FeatureObservationV1` for every metric / Verify strip | M18 tools · §1M.12 |
| **G-10** | Options math test matrix | M11 + pytest · §1M.13 |
| **G-11** | Security tests (loopback, CORS, no secrets in logs) | M18 / S10 · §1M.14 |
| **G-12** | Demo isolation (`data_class=DEMO`, no journal/export as evidence) | M1/M18 · §1M.14 |
| **G-13** | PIT/OOS specifics + `available_at` | M15 |
| **G-14** | Source activation work package for VERIFY keys | M14 · §1M.9 |
| **G-15** | Ban smart money / institutional intent / dealer sign language | §9 non-goals · §1M.5 |
| **G-16** | Max-pain liquid **index only** until stock promotion | M11 · §1M.13 |

### Quick index — do not build day-1 (O-01…O-07)

| ID | Reject | Note |
|----|--------|------|
| **O-01** | Full P5 participation taxonomy (precision/recall regimes) | After M15 baseline |
| **O-02** | Full 11-stage ladder on all 370 keys day-1 | Lite 4-stage for S2 |
| **O-03** | Expose all 8 gate classes in UI | Backend full; UI collapsed |
| **O-04** | 6-step greek performance policy before M10 | Memoize baseline; profile after M11 |
| **O-05** | Full latency p50/p95 matrix before shadow options | `UNSET_PENDING_MEASUREMENT` then measure |
| **O-06** | Redis/Celery/SSE rewrite | Not day-1 |
| **O-07** | Microservices split | Modular monolith + typed contracts |

---

### 1M.1 ASM / GSM surveillance (C-01 full steps)

| Step | Behavior |
|------|----------|
| 1 | Fetch official `nse_asm` / `nse_gsm` (and ban lists when defined). |
| 2 | If symbol on list → attach tags: `SAFETY_VETO_CANDIDATE`, reason `WAIT_SURVEILLANCE`, list source + as-of date. |
| 3 | Keep symbol **visible** for research shortlist with audit record (do not silent-delete). |
| 4 | Public research state ceiling: **WAIT** (or WATCH if other families allow) — **not** auto **REJECT**. |
| 5 | Emit **REJECT** / hard block for trading readiness **only if** product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) has an explicit safety disposition for that surveillance class. |
| 6 | UI: red/amber **Surveillance** badge + reason; never green CONFIRMED while flagged. |

**Live code gap:** `gate_readiness.py` may still emit `BLOCKED_SURVEILLANCE` as a hard block. Align discovery/safety path to the table above at **M3**.  
**Not the same as:** F&O ban, MWPL, exchange cannot-trade — those use their own eligibility contracts.

### 1M.2 Options surface UI

| Surface UI | Placement |
|------------|-----------|
| Strike grid, expiry max-pain/walls, PCR timeline from chain | **Hidden evidence inspector** |
| Left-nav | Neutral **OI Context** (FO bhav OIΔ / vol/OI) only |
| Promote Strike/Expiry to top-level nav | Only after OOS proof **and** product-plan amendment |
| Theta, local delta-hedged variance attribution and VRP context | **Hidden evidence inspector** only; show model, time convention, implied/realized method, horizon, costs, calibration and status. Missing or mismatched inputs render `VRP_UNKNOWN`; positive/negative VRP and IV/RV cannot display automatic buy/sell language. |

Aligns with options surface law in `grok_plan/convexity_intelligence_engine.md` (governing top): inspector, not a second product dashboard.
The inspector may expose `IV_RICH_CONTEXT`, `IV_CHEAP_CONTEXT` or `VRP_UNKNOWN` only after the mapped R12/R16 contracts pass. It must keep `directional_class`, public state, options-package support and volatility context separate, and must link every value to Professional Mathematics section 17.5/17.6 plus its formula/source versions.

### 1M.3 Adaptive budgets (not fixed cut-points)

| Field | Meaning |
|-------|---------|
| `discovery_budget` | Max S2 candidates (from source health, latency, mode) — **not** hard-coded 40–60 |
| `shortlist_budget` | Max S3–S6 deep symbols — **not** hard-coded 10–25 |

Both live on `RunManifestV1`.

### 1M.4 F&O eligibility

`nse_equity_universe` is **not** F&O eligibility proof. F&O modes require a **versioned F&O eligibility / contract master**. Equity universe may only bound broad equity scope.

### 1M.5 OI + price labels (observable only)

Allowed co-move codes only:

- `OI_RISE_PRICE_RISE`
- `OI_RISE_PRICE_FALL`
- `OI_FALL_PRICE_RISE`
- `OI_FALL_PRICE_FALL`

**Forbidden in UI and code:** long buildup, short covering, smart money, institutional intent, dealer long/short gamma.

### 1M.6 Run lineage identity

Use separate fields (do not rely on a truncated `run_hash` alone):

| Field | Role |
|-------|------|
| `run_id` | Stable run identity (e.g. UUIDv7) |
| `request_id` | API idempotency |
| `manifest_hash` | Frozen config/activation snapshot |
| `input_bundle_root` | Content/Merkle root of inputs |
| `publication_id` | Immutable published revision |
| `short_display_id` | Optional human short id |

### 1M.7 State vocabulary (no collisions)

| Internal / legacy | Required name |
|-------------------|---------------|
| Causal Stage-2 “CONFIRMED” threshold label | `STAGE2_THRESHOLD_MET` |
| Scanner `statusGroup` | `analysis_disposition` |
| Module-local `final_state` | **Forbidden** unless that module is the selected **master public-state owner** |

Public research states remain only: **WATCH / WAIT / CONFIRMED / REJECT**. Machine-disable legacy score/route/field names at import time when possible.

### 1M.8 Dual permissions on every run

| Flag | Meaning when true |
|------|-------------------|
| `research_execution_permission` | Safe to fetch, normalize, shadow-score, replay |
| `state_publication_permission` | Allowed to publish higher public states |

When the current observed runtime reports `sourceActivationReady=false`: public **state ceiling = WAIT**; research execution may still collect and shadow.

### 1M.9 Source maturity (lite for discovery)

S2 may use a source only if at least **FRESH_FOR_DECLARED_USE** (or stronger). Lite ladder:

```text
INVENTORIED → SCHEMA_PROVEN → FRESH_FOR_USE → GATE_AUTHORIZED
```

P0/P1 VERIFY-batch keys use the full ladder / activation work package before they can unlock public-state uses.

### 1M.10 Pipeline barriers B0–B6

| Barrier | Meaning |
|---------|---------|
| B0 | Freeze run manifest |
| B1–B5 | Cross-sectional work, then per-symbol work, without order-dependent ranks |
| B6 | Atomic publish of run |

Cross-sectional ranks and family independence must not depend on which symbol finished first.

### 1M.11 Dataset roots / anti double-count

Every candidate and options package carries `dataset_roots[]` and `correlation_groups[]`. Families that share a root cannot multiply into multiple independent votes. Options surface+flow ≤ **one** package contribution.

### 1M.12 Contracts (coding gates)

| Contract | Required by |
|----------|-------------|
| `RunManifestV1` | M1 |
| `GateDecisionManifest` | M1 |
| `SourceResultV1` | M4 |
| `DiscoveryCandidateV1` | M4 |
| `HypothesisV0Config` | M4 |
| `ManipulationRiskV1` | M4 |
| `FeatureObservationV1` | M4 / M18 (every Verify-strip metric) |
| `SnapshotBundleV1` | M10 |
| `OptionsPackageSupportV1` | M11 |
| `PublishedDecisionV1` | M5 / M18 |
| `VerifyStripV1` | M18 |

### 1M.13 Options feature eligibility + max pain

- Chain quality is **per feature**, not one global switch (PCR may be OK while RR25 is UNKNOWN).
- Missing dividend → `DIVIDEND_INPUT_UNKNOWN` on carry-dependent outputs only.
- **Max pain:** liquid **index** (NIFTY / BANKNIFTY) first; stock max-pain only after separate promotion proof.
- Options math tests (PCR zero denominator → UNKNOWN, gamma units, RR25 brackets, max-pain payoff) gate **M11**.

### 1M.14 Security + demo

- Default bind **127.0.0.1**; no wildcard external exposure without review.
- No credentials in logs/archives; panic-lock protected.
- Demo: `data_class=DEMO`, permanent DEMO banner; no export/journal as real evidence.

### 1M.15 Do not build day-1

| Defer | Until |
|-------|--------|
| Full precision/recall participation research program | After M15 discovery beats volume-only baseline |
| Full maturity ladder on all ~370 inventory rows | P0/P1 VERIFY keys first |
| All 8 gate classes in user banners | Backend full taxonomy; UI: WAIT_DATA / WAIT_QUALITY / WAIT_SAFETY / REJECT |
| Full greek perf 6-step + latency p50/p95 matrix | After M11 thin vertical shows CPU need |
| Redis / Celery / SSE / microservices | Measured pain after M12–M13 |

---

## 1L. Integrity modules + discovery runtime

### Integrity modules (build these)

| ID | Module / behavior | Emit (examples) | Code home | Milestone |
|----|-------------------|-----------------|-----------|-----------|
| **G1** | **Delivery-Volume Integrity** — delivery % vs 20d avg; up vs down-day delivery; volume spike without delivery spike | `WAIT_DELIVERY_FRAUD_RISK`, `REJECT_SYNTHETIC_VOLUME` | `discovery/delivery_integrity.py` or gate G04 | **S1 / M1** |
| **G2** | **Circuit Filter Behavior** — >3 upper circuits / 5d; circuit break + delivery&lt;10%; reversal patterns | `WAIT_CIRCUIT_PUMP`, `REJECT_VOLATILITY_TRAP` | `discovery/circuit_behavior.py` or gate G05 | **S2 / M3** |
| **G3** | **Float / Promoter Pledge** — free float&lt;20% + vol spike; pledge ↑&gt;5%; public hold&lt;25% | `WAIT_LOW_FLOAT_TRAP`, `WAIT_PROMOTER_STRESS` | `discovery/float_risk.py` | **S2 / M4** (shareholding VERIFY P1) |
| **G4** | **Sector/Peer Divergence** — stock +8% while sector −1%; vol 20× sector median; peer isolation | `WAIT_SECTOR_DIVERGENCE`, `WAIT_PEER_ISOLATION` | extend `sector_relative.py` | **S7 / M14** |
| **G5** | **Block/Bulk Deal Verify** — &gt;10% move with zero deals; bulk price ≠ VWAP | weaken SPONSOR / reason codes | `discovery/sponsor_layer.py` | **S5 / M19** |
| **G6** | **Options–Spot Divergence** — spot vol 10× call OI flat; far-OTM IV spike no spot; PCR drop no spot | `WAIT_SPOT_FAKE_OPTIONS_DEAD`, `WAIT_OPTION_PREMIUM_TRAP` | `options_intelligence/fusion.py` or `manipulation.py` | **S6 / M11** |
| **G7** | **Per-symbol S4 chain isolation** — try/except per symbol in chain loop | `WAIT_CHAIN` per symbol only | chain fetch in options package | **S6 / M10** acceptance |
| **G8** | **Catalyst latency** — +20% with zero official announcements; news only unofficial; announce after move | demote CAUSE / tag | evidence / discovery catalyst check | **S2 / M4** |

**Rule:** Research risk flags / soft–hard gates only. Data from the 105 usable set. **No CONFIRMED.** Run before deep harmonic/options when possible.

### Phase A — Cheap discovery runtime (absorbed; S2)

Runs pre-market / EOD or on demand. Output: up to **`discovery_budget`** candidates (adaptive; not fixed 40–60) + tags + lineage. Ceiling WAIT when observed runtime activation is false.

```text
S0  Governance → research_execution_permission vs state_publication_permission
      observed runtime activation is false → public ceiling WAIT; shadow collect may continue
S1  Safety + calendar + identity → ASM/GSM soft-flag WAIT_SURVEILLANCE (§1M.1);
      F&O modes use eligibility master (not equity_universe alone)
S2  Cheap fetches (mode profile keys — §4):
      bhav EOD, FO bhav, volume gainers, most-active, deals, announcements,
      pledge/reg, FII/FPI (regime only), macro for Mode D/E headers
    Features: volume_z, delivery_pct, oi_velocity, vol/oi, deal flags, co-move codes
    Integrity: G1 delivery_integrity (when ready)
    Rank: HYPOTHESIS_V0 — missing NOT renormalized; OPT_SURFACE weight = 0 until M10
    Return top N = discovery_budget; no direction; no CONFIRMED
```

### Phase B — Shortlist deep runtime (absorbed; S3–S6)

```text
S3  Tradability / liquidity / eligibility → shortlist size = shortlist_budget (adaptive)
S4  Budgeted option chain per shortlist symbol
      G7: try/except per symbol → WAIT_CHAIN on that symbol only; batch continues
S5  Quality / identity / coverage validation
S6  Surface + flow → one OPTIONS_PACKAGE (SUPPORT/WEAKEN/CONFLICT/UNKNOWN)
      G6: options–spot divergence; per-feature eligibility (G-06)
      Surface UI → hidden inspector only (§1M.2)
S7+ Structure owns direction; master SM owns public state
```

### Over-engineering rejected (do not build day-1)

| ID | Item | Why reject | Keep as note? |
|----|------|------------|---------------|
| **O1** | Redis day-1 queue/cache/SSE | Non-goal; R0 first; SQLite + threads enough under WAIT ceiling | Yes — post-M15 if load proves pain |
| **O2** | Celery task queue | Ops complexity before activation | Yes — post-activation infra |
| **O3** | Parquet as **primary** OHLCV | SQLite primary; Parquet optional export only | Yes — experimental T2 batch export |
| **O4** | Streaming causal per symbol | Breaks two-phase draft → batch independence → commit | Yes — only if independence proven unnecessary |
| **O5** | Event bus / DAG / Kafka-like | Overkill for ~105 sources / research scanner | Yes — v2 vision only |
| **O6** | Tick spoofing detection | No tick book in 105 inventory | **No** — out of scope |

### Contracts to add (before / with milestones)

| Contract | Milestone | Outline |
|----------|-----------|---------|
| `RunManifestV1` | M1 | run_id, manifest_hash, activation_status, gate_decisions_json, mode_profile, snapshot_at, compiler_version |
| `GateDecisionManifest` | M1 | global_status, per_symbol_flags, safety_veto_list, activation_status, manifest_version, timestamp |
| `SourceResultV1` | M4 | source_key, data_date, content_hash, raw_hash, row_count, parser_version, freshness_status, available_at |
| `DiscoveryCandidateV1` | M4 | symbol, discovery_rank, tags[], header_id, lineage[], ceiling, mode, source_keys_used[], missing_reasons[] |
| `HypothesisV0Config` | M4 | version_id, weights_map, class_bands, thresholds, renorm_policy, journal_ref |
| `ManipulationRiskV1` | M4 / S2 | symbol, risk_flags[], delivery/circuit/float/divergence flags, as_of |
| `SnapshotBundleV1` | M10 | snapshot_bundle_id, source_keys[], data_dates[], raw_hashes[], available_at, bundle_hash |
| `OptionsPackageSupportV1` | M11 | SUPPORT/WEAKEN/CONFLICT/UNKNOWN + surface/flow summaries + lineage |
| `PublishedDecisionV1` | M5/M18 | symbol, state, reason_codes[], evidence_families[], run_id, manifest_hash |
| `VerifyStripV1` | M18 | tool_id, inputs, formula_id/version, output, recompute, source_keys, data_date |

**Enums before M4:**  
`DiscoveryMode` = {INTRADAY, SWING, OPT_FLOW, POSITIONAL, COMMODITY}  
`ResearchState` = {WATCH, WAIT, CONFIRMED, REJECT} — **one vocabulary** (audit C1)  
`SupportType` = {SUPPORT, WEAKEN, CONFLICT, UNKNOWN}  
`CeilingReason` includes: `SOURCE_ACTIVATION_BLOCKED`, `WAIT_BREADTH`, `WAIT_CHAIN`, `WAIT_STRUCTURE_CONFLICT`, `WAIT_LOW_FAMILY_COUNT`, `REJECT_SYNTHETIC_VOLUME`, `WAIT_CIRCUIT_PUMP`, `WAIT_DELIVERY_FRAUD_RISK`, `WAIT_LOW_FLOAT_TRAP`, `WAIT_SECTOR_DIVERGENCE`, `WAIT_SPOT_FAKE_OPTIONS_DEAD`, …

**Config before M4:** `mode_keys.py` required/optional/verify_first per §4; HYPOTHESIS_V0 weights versioned + journal-linked. **S2 must zero OPT_SURFACE** until M10 (chain gate).

## 2. Easy product flow (both engines)

```text
Excel / official links (Engine 1)
  → sector find
  → volume / OI / deals shortlist
  → safety ASM/GSM
       +
PKScreener pipes (Engine 2)  [optional same run]
  → vol× → momentum → breakout → ATR (or VCP swing pipes)
       ↓
MERGE (default E1_THEN_E2)
       ↓
Native thinking: harmonic / trend / evidence / causal
       ↓
Options package later (one package, not dual CIE+Shadow scores)
       ↓
LEFT NAV tools (M-Factor, OI, Swing, Index…) show calc + verify strip
       ↓
Radar under sector headers — research only (WAIT ceiling if observed runtime activation is false)
```

| Engine | Job | Never does |
|--------|-----|------------|
| **E1 TrendForge discovery** | Official sector + vol/OI + sponsor tags | CONFIRMED alone |
| **E2 PKScreener** | TA action pipes (breakout/VCP/…) | Own gates, CONFIRMED, orders |
| **Native structure/causal** | Direction + multi-family research state | Trust PK data as official |
| **Options package** | SUPPORT/WEAKEN/CONFLICT | Independent CONFIRMED |

---

## 3. Detail Part A — Discovery restructure & design audit

(From former RESTRUCTURE plan.)

**Date:** 2026-07-27  
**Status:** PLAN ONLY — not product-plan authority; not implemented  
**Design audit:** Section **0A** (failures found + fixed flow)  
**Inputs (read fully):**
- `docs/links data use.txt` (Kimi-style 5-screener design + GLM 105-link inventory + gate tiers)
- ~~`docs/new flow to update.txt`~~ **deleted** — absorbed into this plan §1L
- Project governance: `AGENTS.md`, product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`), `BUILD_STATUS` / `VALIDATION`, live code ceiling  
- Live code spot-check: `engine.py`, `scanner_scheduler.py`, `market_activity.py`, `institutional_sources.py`  
**Companion formula catalog (opened only when File A selects R12; §0–§17):** `grok_plan/shadowflow_deep_dive.md` (v9.2), `grok_plan/convexity_intelligence_engine.md` (CIE v7.1); priority: `grok_plan/REAL_PATH_FORWARD.md`  
**Inventory fact (from inputs):** ~105 linked usable rows / ~62 unique active source keys; ~370 inventoried rows total; option chain still weak (`CONNECTED_EMPTY_NO_SIGNAL` / research-only)

---

## 0A. Design audit — failures, flow errors, fixes

This section audits **(1)** the three-AI inputs, **(2)** the first draft of this plan, and **(3)** the live codebase wiring.  
Each row: **failure → why it breaks → fix adopted in this plan.**

### A1. Critical (will produce wrong product if ignored)

| ID | Failure | Evidence | Fix (adopted) |
|----|---------|----------|----------------|
| **C1** | **Gate PASS ≠ product activation** | GLM inventory lists many keys as `Gate State: PASS` while current observed code reports `sourceActivationReady=false`, `gateAuthorizedSourceKeyCount=0` | Always treat inventory PASS as “structured row usable for research.” Product ceiling remains WAIT until compiler activation + product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`). UI banner `RESEARCH_SHADOW_ONLY`. |
| **C2** | **SQL multi-gate example implies CONFIRMED path** | Kimi/GLM sample query joins PCR + FII + delivery as if READY | Discovery outputs **tags + rank only**. No SQL path to CONFIRMED. State machine owns state. |
| **C3** | **discovery_rank uses OPT_SURFACE before chain works** | GPT rank formula weights surface interest while chain is EMPTY | S2 rank uses only **available families** (participation, FO EOD flow, sponsor, regime). OPT_SURFACE weight = 0 until chain yields structured rows. Missing weights **not** renormalized. |
| **C4** | **FII/DII used as stock-level sponsor** | Screener SQL: `fii.net_value_crore > 0` as stock filter | FII/DII is **REGIME context only** (market-wide). Never stock sponsor vote. Stock sponsor = deals, Reg29/31, PIT, announcements. |
| **C8** | **~40% inventory only wired; Mode E/D/sponsor/breadth orphaned** | Kimi coverage audit vs 105 usable keys | Full §4 key maps + §6.0–6.7 efficiency law; Mode E macro header; Mode B full sponsor; live deriv on VERIFY + Mode C/Index |
| **C9** | **Integrity modules (delivery/circuit/float/deals/options-spot) must live in spine** | Integrity requirements | **§1L** G1–G8 detail, opened only through the mapped File A R owner; no separate phase;  |
| **C5** | **Radar can show incomplete/crashed run** | `engine._latest_real_candidates` → `list_scanner_runs(limit=1)` by `started_at`, no `status=COMPLETE` filter | When File A selects the mapped R owner, require latest COMPLETE only (`finished_at` / `status=COMPLETE`). |
| **C6** | **Dual-engine / score→state still leaks in AI drafts** | Fixed 84/88, Combined_Score, dealer GEX, families≥3→CONFIRMED without product-plan safety disposition proof | Quarantine. Options = one package SUPPORT/WEAKEN/CONFLICT. Family count rule = **UNVERIFIED until product-plan amendment**. |
| **C7** | **Plan vs product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) order conflict** | Shipping full S0–S10 options + scanner rewrite could freeze R0 residuals | File A R owners alone decide timing. Discovery remains additive and **never** claims to unlock CONFIRMED; T0/S2 tags do not create a global prerequisite or authorize a scanner big-bang refactor. |

### A2. Major flow / design errors

| ID | Failure | Why | Fix (adopted) |
|----|---------|-----|----------------|
| **M1** | **Sector header depends on unverified keys** | `nse_all_indices`, `nse_sector_constituents` often TIER4 VERIFY | Sector-relative has **fallback ladder:** (1) verified indices API (2) existing `market_context` / sector snapshots (3) Nifty500 industry map from instruments (4) if none → tag `[SECTOR_UNKNOWN]` and **do not fake** sector leader. |
| **M2** | **Volume gainer without sector map = empty shortlist** | Filter “only top sectors” needs symbol→sector join | Require explicit **symbol_sector_map** source with lineage. If map incomplete, degrade to “show unmapped under OTHER header” instead of dropping all. |
| **M3** | **5 screeners as 5 bosses** | Duplicate fetch, double-count families | **One discovery engine**, five **mode profiles** (PRF). Same pipeline stages. |
| **M4** | **Parallel SymbolWorkers + SQLite writes** | SQLite writer lock; plan said parallel then also said no Redis | Parallel **CPU** work OK; **serialize DB writes** through one writer queue. Or write per-symbol JSON then single commit. |
| **M5** | **Stream causal vs independence penalties** | Independence needs full batch scores | Two-phase: per-symbol **draft** causal → final **batch** independence pass → then commit. |
| **M6** | **S2 and existing scanner path undefined** | Risk of two radars fighting | **Discovery is additive:** new `/api/discovery/*` + radar section. Existing harmonic/causal scanner stays until orchestrator migration. Do not dual-write conflicting statusGroups without run type. |
| **M7** | **Ignoring modules that already exist** | `market_activity.py`, `institutional_sources.market_activity_requests`, `intraday_stock_details` sector ranks | **Reuse** market_activity for volume/most-active; extend, don’t re-fetch in parallel with different schemas. |
| **M8** | **Magic thresholds** (delivery>50%, price>2%, rank weights) | Unversioned rules become fake science | All thresholds in **HYPOTHESIS_V0** config with id + version; journal outcomes; no state machine hardcode until validated. |
| **M9** | **Intraday mode on pure EOD baseline** | Volume z from EOD bhav vs “live” gainers mixes cadences | Tag features with `cadence` (EOD vs session). Intraday mode must label **[SESSION_LIST + EOD_BASELINE]** honesty, not “live confirmed momentum.” |
| **M10** | **Option chain empty still in “options mode” UI** | Users think surface is live | Options mode UI: if chain empty, show **FO EOD flow only** + banner `SURFACE_UNAVAILABLE`. |

### A3. Corrected end-to-end flow (fixes applied)

```text
[0] TRIGGER (async)
    POST /api/discovery/run?mode=…  OR  POST /api/scanner/run-once
         → returns {runId, status:QUEUED} immediately
         → background worker owns work
         → UI polls GET …/status/{runId}

[1] PREFLIGHT (once per run, cached)
    Load ActivationManifest (compiler snapshot; do not recompile workbook per symbol)
    Safety snapshot + calendar + market/sector context
    If observed runtime activation is false → run.ceiling = WAIT (still produce research candidates)

[2] INGEST (cheap sources only for mode)
    Prefer existing market_activity / source_monitor paths
    Parse → domain rows with data_date + source_key + content_hash
    Fail-closed per source: missing source = feature null, not invent

[3] UNIVERSE + SAFETY
    equity_universe ∩ mode universe (e.g. Nifty500 for positional)
    SOFT-FLAG ASM/GSM: WAIT_SURVEILLANCE (§1M.1)
    Soft flag: high pledge / SLB pressure (tag, not silent drop unless policy says)

[4] SECTOR / MACRO HEADER (fail-soft)
    Build sector ranks IF map available else SECTOR_UNKNOWN
    Build macro headers for commodity mode from FRED/EIA/WGC

[5] S2 DISCOVERY (no direction, no OPT_SURFACE unless chain ok)
    Features from available families only
    discovery_rank = HYPOTHESIS_V0 percentiles (no renorm)
    Output up to discovery_budget: symbol, tags, header_id, rank, lineage, ceiling=WAIT

[6] S3 SHORTLIST (optional same run or second job)
    shortlist_budget by rank + liquidity + F&O eligibility master

[7] S4–S6 DEEP OPTIONS (only shortlist; isolate failures)
    IF chain empty/blocked → options_support=UNKNOWN, reason=CHAIN_UNAVAILABLE
    ELSE surface+flow same snapshot_bundle_id → one OPTIONS_PACKAGE support

[8] S7 STRUCTURE (existing closed-bar path — independent)
    Direction ONLY from structure module (harmonic/structure), not discovery rank

[9] S9 STATE (single owner)
    safety → REJECT
    observed runtime activation is false → WAIT (max research display)
    conflict / unknown structure / low families → WAIT*
    never: score threshold → CONFIRMED
    never: options alone → CONFIRMED

[10] MATERIALIZE
    Commit only when status=COMPLETE
    Radar reads COMPLETE runs by finished_at
    Group UI by header (sector/macro)
```

### A4. Live code bugs confirmed (fix independent of new screeners)

| Bug | Location | Severity | Fix milestone |
|-----|----------|----------|---------------|
| Latest run ignores COMPLETE | `engine._latest_real_candidates` / `list_scanner_runs(limit=1)` | **High** | T0 |
| Scanner is sequential god-object | `scanner_scheduler._run_once` | Medium (scale) | T2 after S2 |
| Compiler/gates re-entered each scan | `gate_readiness` + compiler cache | Medium | T0 manifest snapshot |
| Status vocabulary triple-split | scanner wait\|reject vs causal READY vs Q5 four-state | High (UX) | **§1M.7 / D-01:** rename table + machine-disable legacy; master owner only publishes public state |
| Option chain not production-ready | inventory + institutional_sources | High for surface | Chain P0 |

### A5. Audit verdict

| Area | Verdict |
|------|---------|
| Overall 3-AI fusion idea (cheap→deep, sector-relative, one options package) | **Sound** after fixes C1–C8, M1–M10; inventory efficiency Kimi patch §4+§6 |
| Full S0–S10 capability detail | Retained, but blocked by chain evidence, File A ownership and R0 governance |
| T0 + sector-relative S2 capability detail | Available as catalog detail only; implementation still requires the selected File A R owner |
| Win-probability product | **Rejected** — quality metrics only |

---

## 0. Hard rules (non-negotiable)

These override any AI proposal that conflicts:

| Rule | Source |
|------|--------|
| Research-only v1 — **no broker orders**, no executable quantity product | `AGENTS.md` |
| Missing / stale / metadata-only / unofficial-only / conflicting evidence **cannot** produce product `CONFIRMED` | `AGENTS.md` |
| When the current observed runtime reports `sourceActivationReady=false`, the scan ceiling is **WAIT** (research shadow) | Code + BUILD_STATUS |
| Dual CIE + ShadowFlow as separate voting engines, Combined_Score, synergy multipliers, fixed 84/88, dealer-intent GEX → **REJECTED** | Options v9.2 / CIE v7.1 / REAL_PATH_FORWARD |
| File A (`docs/fable/new_merge_PLAN_2026-07-18.md`) alone controls build order; this catalog supplies mapped capability detail and cannot select work or amend File A | `AGENTS.md` |
| **No “win probability %” product claim** — improve *research shortlist quality* and journal outcomes; do not ship fake accuracy | Project safety + deferred dual-engine audit |

**Honest goal reframe:**  
Not “guarantee high win-rate stocks.”  
Instead: **maximize quality of attention shortlist** (sector-relative, multi-family, fail-closed, cheap-to-expensive) so the human (and later structure/options support) works only on stocks with real participation, sponsor, and regime context.

---

## 1. What each AI got right (keep) vs wrong (drop)

### Keep (consensus, high value)

| Idea | From | Keep because |
|------|------|--------------|
| **Sector-relative volume discovery** (volume gainer ∩ leading sector) | Kimi | Institutional-style filter; kills isolated noise |
| **5 research modes** (intraday / swing / options-flow / positional / commodity) using *different link subsets* | Kimi | Matches how traders think; uses 105 links well |
| **Radar grouped under sector/macro headers** | Kimi | UI clarity without inventing direction |
| **Tiered inventory** (gate / scanner / research / config / macro) | GLM | Matches real workbook usability |
| **Pipeline:** Universe → Eligibility veto → Sponsor → Price/flow → (optional options support) | GLM + GPT | Aligns with fail-closed gates |
| **Cheap discovery (S2) then deep chain (S3–S6)** | GPT / v9.2 | Prevents 400× option-chain hammering |
| **One OPTIONS_PACKAGE** (surface+flow max 1 vote; no dual engine) | GPT / v9.2 | Prevents double-count |
| **Direction only from closed-bar structure** | GPT / v9.2 | Options SUPPORT/WEAKEN/CONFLICT only |
| **Scanner is God Object; need stage controllers + COMPLETE radar + async run token** | GPT + Kimi topology | Real code pain (`scanner_scheduler` sequential) |
| **Compiler → cached activation manifest**, not live workbook every scan | GPT + Kimi | Robust + faster |
| **Do not activate ChartInk/TV/secondary wrappers as gates** | GPT | Official preference |
| **Unlock ~40 CONFIG first via explicit §6.4 batches** (not all 370; list live-deriv + breadth + PIT) | GPT + Kimi | Highest ROI; no orphan T4 keys |

### Drop or reframe (dangerous / unproven)

| Idea | Why drop/reframe |
|------|------------------|
| Score ≥ threshold → CONFIRMED | Explicitly killed in v9.2 |
| Dealer short gamma / smart money intent from OI alone | Intent inference banned |
| Two independent CIE + ShadowFlow voters | Dual-engine rejected |
| “High win probability stocks” as product copy | Unmeasured; no OOS proof |
| Activate all 370 links | Many REFERENCE/DUPLICATE/DOCUMENT only |
| Live option surface before chain fetch works | S4 blocked until chain fixed |
| Redis/event-bus rewrite as day-1 | Premature vs product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) R0 activation residuals |
| SQL fantasy joins as if all tables exist | Conceptual only until normalizers land |

### Reconcile the “2 screeners” vs “5 screeners”

| Layer | Name | Role |
|-------|------|------|
| **Screener family modes (UI)** | Intraday / Swing / Options-flow / Positional / Commodity | *Which discovery recipe* and which links to emphasize |
| **Pipeline stages (engine)** | **S2 Discovery** + **S3–S6 Deep shortlist** | *When* and *how deep* data is fetched |

**Best design:** One discovery engine, **five mode profiles** (PRF-style), two depth stages (cheap → deep). Not five separate bosses.

**Reuse first (audit M7):** extend `market_activity.py` / `institutional_sources.market_activity_requests()` and sector helpers in `intraday_stock_details.py` before inventing parallel fetchers.

---

## 2. Target architecture (future-proof)

### 2.1 Topology (merge GPT + Kimi; keep governance)

```text
TRIGGER (non-blocking)
  UI / Scheduler → API → run_token QUEUED → background orchestrator

INGEST (can be continuous or scan-start)
  External markets → SourceMonitor → SourceParser
  → raw_source_archive + structured domain tables/Parquet

PRE-FLIGHT GOVERNANCE (daily / on workbook change — not every symbol)
  InventoryCompiler → ActivationManifest (immutable JSON in storage)
  GateController reads manifest + safety snapshot + calendar + market context
  → GateDecisionManifest (global + optional per-symbol flags)

DISCOVERY (S2) — uses ~105 usable / 62 keys — NO direction
  Mode profile (INTRADAY | SWING | OPT_FLOW | POSITIONAL | COMMODITY)
  + Master filter: Sector/Macro header ∩ activity list
  → up to discovery_budget attention candidates (discovery_rank, tags, lineage)

SHORTLIST (S3)
  Tradability / liquidity / F&O / ban / ASM / DTE
  → up to shortlist_budget deep candidates

DEEP OPTIONS (S4–S6) — only if chain fetch works; else WAIT reason
  Budgeted chain fetch → quality → surface (CIE facts) + flow (ShadowFlow facts)
  → OptionsPackageSupport {SUPPORT|WEAKEN|CONFLICT|UNKNOWN}
  OPT_SURFACE + OPT_FLOW share snapshot_bundle_id; count as ONE package

STRUCTURE (S7) — independent family
  Closed-bar price structure owns DIRECTION

STATE MACHINE (S9) — single owner
  Safety veto → REJECT
  observed runtime activation is false → WAIT (ceiling)
  conflicts / low families / missing structure → WAIT*
  else WATCH / research CONFIRMED only if product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) + activation allow
  Options never independently CONFIRMED

MATERIALIZE
  Radar reads COMPLETE runs only (not latest started_at)
  UI polls run_hash / status; RESEARCH_SHADOW_ONLY banner while observed runtime activation is false
```

### 2.2 Scanner refactor (do not throw away modules)

| Today | Target |
|-------|--------|
| `ScannerScheduler._run_once` calls ~11 modules | **ScanOrchestrator** state machine: INGEST → PREFLIGHT → DISCOVER → SHORTLIST → (optional DEEP) → STRUCTURE → COMMIT |
| Sequential symbols | **SymbolWorker** pool for symbol-local work; batch only for true cross-symbol penalties |
| Compiler live each scan | **ActivationManifest** cached |
| Radar `ORDER BY started_at` | **status=COMPLETE ORDER BY finished_at** |
| Sync run-once from UI | **Enqueue** + poll status |

**Do not:** introduce Redis on day one. Prefer SQLite queue + background thread first; upgrade stores only after load proves pain.

### 2.3 Evidence families (one vote each)

| Family | Max vote | Typical sources (from 105 usable set) |
|--------|----------|----------------------------------------|
| SAFETY | Soft-flag default; hard only if product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) | `nse_asm`, `nse_gsm` → WAIT_SURVEILLANCE; ban/MWPL per product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`); calendar; pledge stress flags |
| REGIME | Context | `nse_all_indices`, variations/turnover breadth, FII/DII, FPI, FRED, AMFI, CFTC/EIA/WGC/SGE/MCX headers |
| PARTICIPATION | 1 | volume gainers, most active vol/value, bhavcopy delivery/volume z, preopen FO (optional) |
| SPONSOR_EVENT | 1 | **full layer:** large_deals + large_deals_snapshot, block/bulk (NSE+BSE), Reg29/31, PIT, SAST, pledge, announcements, buyback, financial results, order-win |
| OPT_FLOW | ⊂ OPTIONS_PACKAGE | FO bhav OI velocity, vol/OI, oi_spurts, live equity derivatives lists (when verified) |
| OPT_SURFACE | ⊂ OPTIONS_PACKAGE | chain IV/PCR/skew/gamma conc/max pain — **blocked until chain works** |
| PRICE_STRUCT | 1 | closed-bar OHLCV structure (existing harmonic/structure path) |

**OPTIONS_PACKAGE = OPT_FLOW + OPT_SURFACE ≤ 1 contribution.**

---

## 3. Master discovery concept (from Kimi — adopted)

### Sector-Relative Volume Discovery (default spine for equity modes)

1. Load sector/index move list (`nse_all_indices` after VERIFY; else sector context already in system).  
2. Rank top sectors by % change + volume/participation proxy.  
3. Load `nse_volume_gainers` + most-active lists.  
4. **Keep only stocks in leading (or lagging, for short research) sectors.**  
5. Attach header tag: `[SECTOR LEADER: NIFTY METAL +2.5%] → TATASTEEL (Vol Z=3.1)`.  
6. **No direction** from this step alone.

This is the single highest-ROI filter across AI proposals.

---

## 4. Five mode profiles (UI/research recipes) — full inventory key maps

Each profile is a **source subset + feature recipe + output tags**. All share S2→S3 pipeline and global ceilings.  
**Rule:** Keys listed here must appear in `discovery/modes.py` (or equivalent) as `required` / `optional` / `verify_first`.  
**Fail-soft:** Missing optional key → tag `SOURCE_MISSING:<key>` on run lineage; never invent values.

### Shared strips (all equity modes A/B/C + Index UI)

| Strip | Keys | Role |
|-------|------|------|
| **Sector header** | `nse_all_indices`, `nse_sector_constituents` (VERIFY P0) | Leading/lagging sector headers |
| **Breadth** | `nse_variations_gainers`, `nse_variations_loosers`, `nse_market_turnover` | Adv/dec, turnover context (M-Factor + Index) |
| **Pre-open FO** | `nse_preopen_fo` | Session-open FO interest (optional; VERIFY) |
| **Safety** | `nse_asm`, `nse_gsm` | Soft-flag `WAIT_SURVEILLANCE` (§1M.1); hard REJECT only if product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) |
| **Calendar** | `nse_trading_calendar` | Session validity |
| **Universe** | `nse_equity_universe` | Symbol master (not F&O eligibility proof alone) |

---

### Mode A — Intraday equity (momentum / breakout attention)

| Use | Keys (inventory) | Integration |
|-----|------------------|-------------|
| Activity | `nse_volume_gainers`, `nse_most_active_volume`, `nse_most_active_value` | S2 core |
| Baseline | `nse_bhavcopy_eod` | Volume z / delivery baseline |
| **Breadth (required strip)** | `nse_variations_gainers`, `nse_variations_loosers`, `nse_market_turnover` | Market-condition banner |
| **Pre-open (optional)** | `nse_preopen_fo` | Open interest / gap context |
| **Sponsor (full layer)** | `nse_large_deals_snapshot` **and** `nse_large_deals` (archive CSV — different contract), `nse_block_deal`, `nse_block_deal_live`, `bse_block_deals`, `bse_bulk_deals` | Deal tags; do not treat snapshot ≡ archive |
| Sector header | `nse_all_indices`, `nse_sector_constituents` | Sector-relative filter |
| Safety | `nse_asm`, `nse_gsm` | Soft-flag WAIT_SURVEILLANCE (§1M.1) |

**Logic:** Safety veto → sector header → breadth strip → volume z vs bhavcopy → deal tags (snapshot + archive + block/bulk).  
**Ceiling:** WAIT/WATCH research; no CONFIRMED from discovery.  
**Tags:** `[SECTOR], [VolZ], [Breadth], [Deal:snapshot|archive|block|bulk], [PREOPEN?]`

---

### Mode B — Swing equity (delivery + sponsor + catalysts) — **full sponsor layer**

| Use | Keys | Integration |
|-----|------|-------------|
| Delivery / price | `nse_bhavcopy_eod`, `bse_bhavcopy_eod` | Delivery %, multi-day |
| **Catalyst NSE** | `nse_announcements`, `nse_corporate_filings_actions`, `nse_daily_buyback` (0 rows OK → VALID_EMPTY not crash), `nse_financial_results` (VERIFY; earnings guard) | Event tags |
| **Catalyst BSE** | `bse_corporate_announcements`, `bse_order_win_announcements` (revenue/order-win; VERIFY) | Cross-exchange catalysts |
| **Sponsor deals** | `nse_large_deals`, `nse_large_deals_snapshot`, `nse_block_deal`, `nse_block_deal_live`, `nse_bulk_deal_symbol`, `bse_block_deals`, `bse_bulk_deals` | Full deal graph |
| **Sponsor ownership** | `nse_regulation_29`, `nse_regulation_31`, `nse_pit_symbol`, `nse_pit_current`, `bse_sast` | Promoter / SAST / PIT |
| **Pledge** | `nse_pledge_data`, `bse_pledge_data` | High-pledge risk / trend |
| **Shareholding** | `nse_shareholding_pattern` (VERIFY; quarterly context) | Multibagger / swing context |
| Borrow proxy | `nse_slb` | Borrow pressure flag only |
| Safety | `nse_asm`, `nse_gsm` | Soft-flag WAIT_SURVEILLANCE (§1M.1) |
| Sector | Shared sector header strip | Same as Mode A |

**Logic:** High delivery + price move + sector trend + full disclosure tags (deals ≠ PIT ≠ Reg29).  
**Ceiling:** WAIT until multi-family + structure.  
**Contract note:** `nse_large_deals` (archive CSV) and `nse_large_deals_snapshot` (API) are **different contracts** — both assigned; never collapse to one key.

---

### Mode C — Options flow (cheap FO; surface later)

| Use | Keys | Integration |
|-----|------|-------------|
| FO EOD | `nse_fo_bhavcopy`, `nse_participant_oi` | OIΔ, vol/OI; participant = **regime only** |
| Spurts | `nse_oi_spurts`, `nse_oi_spurts_contracts` | VERIFY first (T4) |
| Active underlyings | `nse_most_active_underlying` | S2 FO attention |
| **Live equity derivatives (all 7)** | parent `nse_live_equity_derivatives` + `…_banknifty_fut`, `…_banknifty_opt`, `…_index_fut`, `…_index_opt`, `…_stock_fut`, `…_stock_opt` | VERIFY M14; Index Dashboard + Mode C shortlist |
| Pre-open FO | `nse_preopen_fo` | Open session FO |
| Chain (deep only) | `nse_option_chain`, `nse_option_chain_equity` | **M10 gate**; S4–S6 only |
| Header | Mode A sector + breadth strip | Sector-relative FO |

**Logic:** OI change %, vol/OI, spurts, live most-active lists; participant OI = regime only.  
**Explicit:** Until chain returns structured rows → **no IV/skew/gamma walls**. Tags: `[OIΔ], [Vol/OI], [LiveFO?], [Spurts?]`.

---

### Mode D — Positional (macro + fund rotation) — **macro suite filled**

| Use | Keys | Integration |
|-----|------|-------------|
| India flow | `nse_fii_dii`, `nsdl_fpi_daily`, `nsdl_fpi_fortnightly` (if present) | **REGIME only** — never stock sponsor |
| MF sector | `amfi_scheme_wise` | Sector rotation preference (delayed) |
| Universe | `nse_nifty500_constituents`, `nse_equity_universe` | Cap focus |
| Sector map | `nse_all_indices`, `nse_sector_constituents` | Map MF tilt → symbols |
| **Macro rates/USD** | `fred_real_yield_10y`, `fred_broad_dollar_index` | Growth vs value / EM risk |
| **Global positioning** | `cftc_cot`, `cftc_legacy_futures_only`, `cftc_disagg_futures_only`, `cftc_tff_futures_only` | Commodity/position context (not stock signal) |
| Energy bias | `eia_weekly_petroleum_stocks` | Energy sector tilt |
| Gold bias | `wgc_gold_etf_holdings`, `wgc_gold_etf_flows`, `world_gold_council_oi`, `sge_benchmark_gold` | Safe-haven / metal tilt |
| Pledge preference | `nse_pledge_data`, `bse_pledge_data` | Prefer lower pledge for multibagger research |
| Shareholding | `nse_shareholding_pattern` | Quarterly sponsor structure |
| Structure | closed-bar multi-week | PRICE_STRUCT family |

**Logic:** Nifty500 ∩ MF-preferred sectors ∩ macro not hostile → research shortlist.  
**Ceiling:** research WAIT; AMFI delayed = **not** intraday truth. FII/FPI never stock-level sponsor.

---

### Mode E — Commodity (MCX + global) — **macro header sub-table required**

#### E1. Macro header (build first — was orphaned)

| Header driver | Keys | Tag example |
|---------------|------|-------------|
| USD | `fred_broad_dollar_index` | `[USD_STRONG]` / `[USD_WEAK]` |
| Real yields | `fred_real_yield_10y` | `[YIELDS_UP]` headwind for gold |
| Crude inventory | `eia_weekly_petroleum_stocks` | `[EIA_DRAW]` / `[EIA_BUILD]` |
| Gold ETF | `wgc_gold_etf_holdings`, `wgc_gold_etf_flows` | `[GOLD_ETF_IN]` |
| Gold OI | `world_gold_council_oi` | Context only |
| SGE | `sge_benchmark_gold` | PASS_CONTEXT_ONLY |
| CFTC suite | `cftc_cot`, `cftc_legacy_futures_only`, `cftc_disagg_futures_only`, `cftc_tff_futures_only` | Positioning extremes (context) |

**Output:** One or more macro headers, e.g.  
`[HEADER: GLOBAL CRUDE | EIA drawdown | USD weak]`  
`[HEADER: GOLD | yields down | ETF inflow]`

#### E2. Local MCX action

| Use | Keys | Notes |
|-----|------|--------|
| MCX EOD | `mcx_bhavcopy` | Volume/price movers; **not** live intraday claim |
| Align | Compare MCX mover commodity class to macro header | Tag `[MacroAligned]` / `[MacroConflict]` / `[MacroUnknown]` |

**Logic:** Macro header (E1) → MCX movers (E2) → alignment tags.  
**Ceiling:** MCX research; no dealer/intent claims; no fake live MCX from EOD bhav.

---

### Mode → UI tool map (efficiency)

| Mode | Primary left-nav tools |
|------|------------------------|
| A | M-Factor, Speculative, OI Analysis (equity) |
| B | Swing Finder, Accumulation, Trend+Accum |
| C | OI Tracker, Strike, Expiry (after M10), Index (live FO) |
| D | Multibagger Research |
| E | Commodity radar section / macro headers on radar |

---

## 5. Two-depth pipeline (from GPT — adopted)

### Screener Stage S2 — Cheap Discovery

- **Input:** Mode profile + ~105 usable sources  
- **Output:** up to `discovery_budget` candidates with:
  - `discovery_rank` (percentile formula is **HYPOTHESIS_V0**, not state gate)
  - tags (sector, volume z, deal, OIΔ, delivery, …)
  - full source lineage (keys, data dates, snapshot ids)
- **Forbidden:** direction, CONFIRMED, intent language, full-chain fetch for whole universe

### Screener Stage S3–S6 — Deep shortlist

- **Input:** top shortlist from S2 (size = `shortlist_budget`)  
- **S3:** tradability / liquidity / ban  
- **S4:** option chain fetch **only** for shortlist (blocked today → `WAIT_CHAIN_EMPTY` per symbol)  
- **S5:** quality validation  
- **S6:** surface + flow descriptive metrics → **one** OptionsPackageSupport  
- **Forbidden:** CIE_Score, Combined_Score, synergy, dealer sign GEX, dual voters

### Master state (S9) — simplified, File-A-safe

```text
IF hard safety veto → REJECT
ELIF sourceActivationReady == false → WAIT (RESEARCH_SHADOW_ONLY)
ELIF required data for mode missing → WAIT + reason
ELIF options package CONFLICT with structure → WAIT_STRUCTURE_CONFLICT
ELIF closed structure UNKNOWN → WAIT_STRUCTURE
ELIF independent families insufficient → WAIT_LOW_FAMILY_COUNT
ELIF activation true and product-plan law allows AND all gates pass → research CONFIRMED (structure owns direction)
ELSE → WATCH / WAIT (research)
```

**Note:** Exact family-count rule must be confirmed against product-plan law before coding as hard law (GPT labeled this UNVERIFIED_PARENT_AUTHORITY).

---

## 6. How the 105 links map into the pipeline

### 6.0 Coverage target (Kimi audit — plan must hit this)

| Layer | Inventory keys (approx) | **Deeply integrated** (mode/family/UI/stage) | Mention-only (forbidden after this patch) | Completely absent (forbidden unless intentional) |
|-------|------------------------:|---------------------------------------------:|-------------------------------------------:|--------------------------------------------------:|
| **T1** Gate dependencies | ~10 | **All T1 PASS keys** assigned in §4 / families | 0 | 0 |
| **T2** Scanner operational | ~3–4 | Universe, calendar, corp actions | 0 | 0 |
| **T3** Research context | ~9+ | Deals, announcements, volume, most-active, macro | 0 | 0 |
| **T4** Config endpoints | ~30+ | On VERIFY batch §6.4 + mode optional slots | 0 after list | 0 (list every key) |
| **T5** Macro / MCX | ~11 | Mode E header + Mode D macro | 0 | 0 |
| **Overall unique ~62–70** | — | **Target ≥85% wired or VERIFY-listed** | — | Intentional only |

**Before this patch (Kimi):** ~40% deeply integrated; Mode E macro orphaned; live derivatives missing; sponsor half-built.  
**After this patch (plan law):** every gap below is either **assigned in §4** or **on VERIFY batch §6.4** with milestone.

### 6.1 Inventory summary (from inputs)

| Bucket | Count (approx) | Role |
|--------|----------------|------|
| Linked usable rows | **105** | Working for research/discovery |
| Unique active keys | **~62** | Deduped keys |
| CONNECTED_FRESH_STRUCTURED | **~75** | Strongest |
| CONNECTED_WORKING_SCREENER_ENDPOINT | **~30** | Need VERIFY_FETCH_AND_NORMALIZER |
| Not usable of ~370 | **~231** | Do not all need unlock |

### 6.2 Tier use (GLM + this plan)

| Tier | Use in pipeline |
|------|-----------------|
| **T1 Gate dependencies** | S1 veto / sponsor / FO context (when PASS) — still cannot unlock product CONFIRMED alone if observed runtime activation is false |
| **T2 Scanner operational** | Universe, calendar, corp actions |
| **T3 Research context** | Deals, announcements, volume gainers, most-active, macro |
| **T4 Config screener endpoints** | **Explicit VERIFY list §6.4** (live deriv, oi spurts, indices, chain, variations, PIT, …) |
| **T5 MCX/macro** | **Mode E macro header + Mode D** (not MCX-only) |

### 6.3 Gap register (Kimi) — closed in this plan

| Gap | Intentional? | Plan fix |
|-----|--------------|----------|
| Mode E only `mcx_bhavcopy` | **No** | §4 Mode E1 macro header table (FRED, EIA, WGC, SGE, CFTC suite) |
| Live equity derivatives (7 keys) missing | **Partial → closed** | Mode C + Index Dashboard + §6.4 P1 VERIFY batch |
| Sponsor half-built (5 of 13) | **No** | Mode A/B full deal+PIT+SAST+pledge list; archive ≠ snapshot |
| Corporate catalysts thin | **No** | Mode B: buyback, financial results, BSE corp + order-win |
| Breadth / pre-open absent from modes | **No** | Shared strip + Mode A; Index Dashboard source table |
| Mode D under-populated | **No** | Mode D: FRED, AMFI, FPI daily+fortnightly, CFTC, EIA, WGC |
| T4 ~27 unverified | **Yes (verify first)** | Still VERIFY — but **every key listed** in §6.4 |
| Option chain subtypes | **Yes** | M10 gate; not S2 |

### 6.4 VERIFY / unlock batches (M14 + M10) — full key lists

#### P0 — discovery headers (block empty shortlist)

| Keys | Feeds |
|------|--------|
| `nse_all_indices`, `nse_sector_constituents` | Sector header (M2–M3) |
| `nse_variations_gainers`, `nse_variations_loosers`, `nse_market_turnover` | Breadth strip / M-Factor / Index |
| `nse_oi_spurts`, `nse_oi_spurts_contracts` | Mode C |

#### P1 — live FO + index tools (M14 / M20)

| Keys | Feeds |
|------|--------|
| `nse_live_equity_derivatives` (parent) | Mode C, Index |
| `nse_live_equity_derivatives_banknifty_fut` | Index / Mode C |
| `nse_live_equity_derivatives_banknifty_opt` | Index / Mode C |
| `nse_live_equity_derivatives_index_fut` | Index / Mode C |
| `nse_live_equity_derivatives_index_opt` | Index / Mode C |
| `nse_live_equity_derivatives_stock_fut` | Mode C shortlist |
| `nse_live_equity_derivatives_stock_opt` | Mode C shortlist |
| `nse_most_active_underlying` | Mode C |
| `nse_preopen_fo` | Mode A/C open context |

#### P1 — sponsor / catalyst config (Mode B)

| Keys | Feeds |
|------|--------|
| `nse_pit_symbol`, `nse_pit_current` | Sponsor |
| `nse_bulk_deal_symbol` | Sponsor history |
| `nse_block_deal`, `nse_block_deal_live` | Live block |
| `nse_shareholding_pattern` | Mode B/D |
| `nse_financial_results` | Earnings guard |
| `nse_daily_buyback` | Catalyst (VALID_EMPTY OK) |
| `bse_order_win_announcements` | Revenue catalyst |
| `bse_sast`, `bse_pledge_data` | Already T3-ish; keep assigned |

#### P0/P1 — chain (M10)

| Keys | Feeds |
|------|--------|
| `nse_option_chain`, `nse_option_chain_equity` | S4–S6 surface only |

#### Already PASS / wire without waiting VERIFY (T1–T3 examples)

`nse_asm`, `nse_gsm`, `nse_slb`, `nse_bhavcopy_eod`, `nse_fo_bhavcopy`, `nse_participant_oi`, `nse_large_deals`, `nse_large_deals_snapshot`, `nse_pledge_data`, `nse_fii_dii`, `nse_volume_gainers`, `nse_most_active_*`, `nse_announcements`, `nse_regulation_29/31`, `nse_corporate_filings_actions`, `bse_block_deals`, `bse_bulk_deals`, `bse_corporate_announcements`, `amfi_scheme_wise`, `nsdl_fpi_daily`, `mcx_bhavcopy`, `fred_*`, `eia_*`, `wgc_*`, `world_gold_council_oi`, `sge_benchmark_gold`, `cftc_*`, `nse_equity_universe`, `nse_nifty500_constituents`, `nse_trading_calendar`.

### 6.5 Critical path unlock order (not “all 370”)

| Priority | Work | Why |
|----------|------|-----|
| **P0** | Fix radar COMPLETE + async run token | Honest materialization |
| **P0** | Sector map + sector-relative filter | Kimi master concept |
| **P0** | VERIFY §6.4 P0 breadth + indices | Headers without empty shortlist |
| **P0** | Wire Mode B full sponsor + Mode E macro (even if some keys empty) | Close non-intentional gaps before coding modes as stubs |
| **P0** | Fix / fixture `nse_option_chain*` | Unblocks S4–S6 surface |
| **P1** | §6.4 live derivatives + PIT + catalysts VERIFY | Index Dashboard + Mode B/C depth |
| **P2** | HTML_SCHEMA_PENDING parsers where official tables matter | Completeness |
| **P3** | FETCH_BLOCKED session/TLS (remaining) | Edge depth |
| **Never as gate** | ChartInk / Trendlyne / TV / secondary wrappers | Non-authority |

### 6.6 Unusable-link breakdown (~231 of ~370) — do not try to “fix all”

From GPT inventory analysis (inputs). **Activate only high-ROI official contracts.**

| Category (approx) | Count | Action |
|-------------------|------:|--------|
| `REFERENCE_ONLY` / `SECONDARY_DISCOVERY` (ChartInk, Trendlyne, StockEdge, TradingView, etc.) | ~50 | **Do not activate** as gates |
| `DUPLICATE_NO_NEW_CONTRACT` | ~20 | Skip — already covered |
| `DOCUMENT_ONLY` (SEBI PDFs, methodology notes) | ~15 | Reference only |
| `CONFIG_CONTRACT_NOT_YET_VERIFIED_LIVE` | ~40 | **§6.4 priority unlock** |
| `HTML_SCHEMA_PENDING` | ~30 | Build parsers only if official tables needed |
| `FETCH_BLOCKED` (403/404/TLS/timeout) | ~20 | Session/TLS fixes case-by-case |
| `METADATA_ONLY` / landing pages | ~40 | Need real file/API contract first |
| `ARTIFACT_CAPTURED_SCHEMA_PENDING` / XLS/ZIP | ~10 | Sheet-level parsers + fixtures |
| Other / mixed | remainder | Case-by-case |

**You do not need all 370 links.** Cheap discovery uses the **~105 usable** set fully mapped in §4; deep chain only for shortlist.

### 6.7 Acceptance test (inventory efficiency)

Before calling discovery “done” for a mode:

1. Every key in that mode’s §4 table appears in code config or as `SOURCE_MISSING` with reason.  
2. Mode E run produces **at least one macro header object** when any FRED/EIA/WGC key returns data (not MCX-only).  
3. Mode B tags distinguish `large_deals_snapshot` vs `large_deals` archive.  
4. Index Dashboard refuses fake OI if all 7 live-deriv keys are unverified (shows VERIFY pending).  
5. Breadth strip empty → `WAIT_BREADTH` / unknown — not a silent 0/0 fake market.

---

## 7. Topology detail catalog

`T0-T4` are historical topology tags mapped in the owner table. They describe
cohesive capabilities but do not establish phase order, dates or permission to
implement.

### Detail tag T0 — Correctness

1. Radar: **latest COMPLETE run only**.  
2. `POST /api/scanner/run-once` returns `{runId, status: QUEUED|RUNNING}` immediately; work stays background.  
3. Persist **activation/gate snapshot JSON** at run start (manifest).  
4. UI banner: `RESEARCH_SHADOW_ONLY` while observed runtime activation is false.  
5. Sector-relative filter **prototype** as pure function + unit tests (no new engine).

### Detail tag T1 — Discovery package

1. New module tree (example):

```text
backend/trendforge_api/discovery/
  modes.py              # INTRADAY, SWING, OPT_FLOW, POSITIONAL, COMMODITY — full §4 key maps
  mode_keys.py          # required/optional/verify_first registries (inventory efficiency)
  sector_relative.py
  breadth.py            # variations + turnover strip
  sponsor_layer.py      # deals archive≠snapshot, PIT, SAST, Reg29/31, pledge
  macro_headers.py      # Mode E + Mode D FRED/EIA/WGC/CFTC/AMFI/FPI
  features.py           # PIT percentiles, no renorm of missing
  rank.py               # HYPOTHESIS_V0 weights, versioned
  pipeline.py           # S2 entry
```

2. API: `POST /api/discovery/run?mode=INTRADAY|SWING|OPT_FLOW|POSITIONAL|COMMODITY` → candidates + headers + lineage.  
3. Wire radar view: **group by sector/macro header** (Mode E uses macro headers from day one).  
4. Inventory efficiency tests (§6.7).  
5. Do **not** auto-promote to CONFIRMED.

### Detail tag T2 — Scanner decomposition

1. Extract `IngestionController`, `GateController`, `SymbolPipeline`.  
2. Parallel SymbolWorkers after gates (bounded concurrency).  
3. Parquet for bulk OHLCV analytics path; SQLite for lineage/runs (CQRS-lite).  
4. Causal independence penalties stay final commit step only if cross-symbol.

### Detail tag T3 — Options package

1. Single package `options_intelligence/` per v9.2 §0.3: contracts, surface, flow, fusion, quality; **`patterns.py` stub only**.  
2. ShadowFlow + CIE **modules only**, not dual engines; implement once (no second fetch/score).  
3. Day-one studies: PCR, max pain (index), unsigned gamma, OI velocity, raw quality — not 14/12 pattern bibles.  
4. Settlement/exercise required for state-eligible Greeks; EOD max pain ≠ intraday pin in UI.  
5. Journal + walk-forward before any promotion language; product-plan amendment before CONFIRMED support.

### Detail tag T4 — R0 activation residuals

Continue: CROSS-006 maturity counts, TDG-GAP-011 history, CROSS-007/TDG-GAP-024, extended contracts — **activation remains separate governance**.

---

## 8. “High quality shortlist” metrics (replace win-probability theater)

Track in journal (research only):

| Metric | Definition |
|--------|------------|
| **Hit@K structure** | Of top-K discovery names, how many later print closed-bar structure event within N sessions |
| **False breakout rate** | Volume gainers **outside** leading sectors vs **inside** (expect lower false rate inside) |
| **Survival after surveillance soft-flag** | Names tagged WAIT_SURVEILLANCE that later worked / failed (research journal; not auto-REJECT count) |
| **Sponsor coincidence** | Fraction of shortlist with deal/disclosure same day (descriptive) |
| **OOS vs baseline** | Discovery rank vs simple “top volume gainer” baseline — must beat baseline before calling it better |

Only after multi-session OOS and product-plan law permission: discuss support for higher research states — never ship “82% win rate” UI.

---

## 9. Explicit non-goals

- OMS / live orders / OpenAlgo placeorder  
- React/Redis rewrite as prerequisite (**O1 / O-06**)  
- Celery / task broker day-1 (**O2 / O-06**)  
- Parquet as primary OHLCV store (**O3** — optional export only)  
- Streaming causal scoring per symbol (**O4** — keep batch independence pass)  
- Event bus / Kafka-like DAG day-1 (**O5**)  
- Tick-level spoofing detection (**O6** — no book in inventory)  
- Microservices split day-1 (**O-07**)  
- ShadowFlow 14-pattern bible as next milestone  
- Activating unofficial screeners as READY authorities  
- Score-driven CONFIRMED / SSI / Combined_Score as state  
- Hardcoded discovery_rank with OPT_SURFACE weight before M10  
- Fixed 40–60 / 10–25 as scientific cut-points (use adaptive budgets)  
- Top-level Options Intelligence dashboard before OOS + product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) (§1M.2)  
- Auto hard REJECT from ASM/GSM without product-plan safety disposition disposition (§1M.1)  
- Labels: long buildup, short covering, smart money, institutional intent, dealer sign (§1M.5 / G-15)  
- Claiming dealer mind-reading  
- Full P5 precision/recall participation research before M15 baseline (**O-01**)  

---

## 10. R-owned capability cross-reference (not ordered)

File A is the only selector. This table preserves the former sequence's useful
deliverables and dependencies while attaching each item to its controlling R
owner. Row order has no implementation meaning.

| Detail tags | File A owners | Deliverable | Internal prerequisite note | Closes audit IDs |
|---|---|---|---|---|
| **T0** | R0 | COMPLETE radar; async run token; gate/activation snapshot at run start | Current observed code | C5, A4 |
| **M2, M3** | R2 | symbol→sector map + fail-soft headers + tests | T0 detail may be relevant | M1, M2 |
| **M4** | R2, R3 | 5 modes; adaptive discovery budget; tags; lineage; macro and sponsor context | usable source contracts | C3, C4, C8, M3–M9 |
| **M5** | R15 | Group by sector/macro; shadow banner | discovery contract | C1, M10 |
| **M10** | R12 | Option-chain fixture + live verify; inspector-only surface | approved inventory contract | C3, M10 |
| **M11** | R3, R12, R15 | adaptive shortlist; one options package | eligible M10 chain evidence | C6, M5 |
| **M12, M13** | R8, R9 | Controllers; parallel CPU; serial DB commit | stable controller contracts | M4, A4 god-object |
| **M14** | R0, R15 | Verify high-value source contracts | source compiler evidence | link unlock |
| **M15** | R15, R16, R18 | Journal and OOS harness against volume-only baseline | PIT discovery evidence | win-rate theater ban |
| **M17** | R0 | Formal amendment when requirements or state language change | required before new CONFIRMED semantics | C6, C7 |

---

## 11. File / package map (proposed)

| Path | Responsibility |
|------|----------------|
| `discovery/*` | Modes, sector-relative, S2 rank, mode_keys |
| `discovery/delivery_integrity.py` | **G1** delivery vs volume fraud flags |
| `discovery/circuit_behavior.py` | **G2** circuit pump / volatility trap |
| `discovery/float_risk.py` | **G3** float + pledge stress |
| `discovery/sponsor_layer.py` | Deals + **G5** block/bulk verify |
| `discovery/sector_relative.py` | Sector filter + **G4** peer divergence |
| `selection/*` | Keep Q5 contracts; discovery feeds selection fixtures later |
| `options_intelligence/*` | surface + flow + quality (not dual engines) |
| `options_intelligence/fusion.py` or `manipulation.py` | **G6** options–spot divergence |
| `scanner_scheduler.py` | Thin orchestrator only (over time) |
| `gate_readiness.py` | Consume ActivationManifest; optional G04/G05 wire-in |
| `engine.py` | Radar COMPLETE only |
| `frontend/app.js` | Headers + run_hash poll + shadow banner + Verify strip |

---

## 12. Decision log (locked rules)

| Topic | Rule in this file |
|-------|-------------------|
| Screeners | Five mode profiles x two depths (S2 cheap / S3-S6 deep) |
| Inventory | Full section 4 mode keys + section 6 VERIFY batches |
| Options | One options_intelligence package (surface + flow <= 1 vote) |
| Win probability UI | Forbidden |
| Redis / Celery / SSE day-1 | Forbidden |
| Sector-relative volume | Default equity discovery filter |
| Integrity modules | G1-G8 in section 1L |
| State vocabulary | section 1M.7 renames |
| Options UI | section 1M.2 hidden inspector |
| ASM/GSM | section 1M.1 soft-flag WAIT_SURVEILLANCE |
| DTOs | section 1M.12 coding gates |
| Candidate counts | section 1M.3 adaptive budgets |
| Lineage | section 1M.6 run_id suite |
| OI labels | section 1M.5 co-move codes only |
| F&O universe | section 1M.4 eligibility master |
| OPT_SURFACE in S2 rank | Weight 0 until chain works (M10) |


---


## 13. Success criteria (plan done when)

1. Human can open radar and see **sector/macro headers** with multi-mode tags.  
2. Discovery uses **only verified usable keys** with lineage on every row.  
3. Deep options path runs **only** on shortlist_budget names and fails closed when chain empty.  
4. Scanner is **not** the only place governance/structure/options logic lives.  
5. Journal shows discovery **beats volume-only baseline** on agreed metrics.  
6. Still **zero** broker execution and zero fake CONFIRMED when the observed runtime activation is false.

---

## 14. Immediate next action (if you approve implementation)

When File A selects owner `R0`, open detail tags `T0`, `M0`, `M1` and `T4` as applicable. This is navigation only: it does not preselect a next phase, bypass option-chain gates, or alter File A fail-closed ceilings.

---

*End of plan. Authority: subordinate to AGENTS.md and product-plan law. Amend product plan only via explicit amendment if discovery/options package IDs must become formal requirements.*

---

## 4. Detail Part B — PKScreener Engine 2

(From former PKSCREENER_ENGINE2 plan.)

**Date:** 2026-07-27  
**Status:** PLAN — aligns with existing `scanners/pk_compatibility.py` shadow design  
**Upstream:** https://github.com/pkjmesra/PKScreener (MIT)  
**Authority:** AGENTS.md + product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) still win; PK never owns CONFIRMED or broker execution  

---

## 1. What PK is good for (use it)

PKScreener is a **rules-based technical scanner** (NSE/F&O universes, breakouts, volume, momentum, VCP, pipes, optional monitor/backtest/Telegram).

**Best role:**

> **Engine 2 — Technical candidate discovery (TA filter + pipes).**  
> Not the final decision engine. Not the official-source gate owner.

**You already have in TrendForge:** offline PK shadow harness + fixture worker + tests (`pk_compatibility.py`, `pk_fixture_worker.py`, `test_q5_pk_compatibility.py`).  
**You do not yet have:** live CLI/Docker sidecar wiring into radar, or native promotion of full PK catalog.

---

## 2. Two-engine model (clear split)

| Engine | Name | Job | Data it trusts |
|--------|------|-----|----------------|
| **E1 — Regime & official discovery** | TrendForge Discovery | Sector header, official volume/OI/deals/safety, sponsor | NSE/BSE/MCX/AMFI inventory (~105 usable keys) |
| **E2 — Technical action screener** | PKScreener (shadow → native) | Breakout / volume / momentum / VCP / pipes | PK OHLCV path (isolated); results sanitized |

```text
                    ┌─────────────────────┐
                    │  Universe (F&O / 500) │
                    └──────────┬──────────┘
           ┌───────────────────┴───────────────────┐
           ▼                                       ▼
   ENGINE 1 (TrendForge)                    ENGINE 2 (PKScreener)
   Sector find                              Piped TA scanners
   Official vol / OI / deals                Volume× momentum × breakout
   ASM/GSM safety                           VCP / patterns / ATR
           │                                       │
           │         symbols + tags                │
           └───────────────────┬───────────────────┘
                               ▼
                    MERGE (union or intersect)
                               ▼
                    SAFETY + GATES (TrendForge only)
                               ▼
                    STRUCTURE / HARMONIC / TREND (native)
                               ▼
                    EVIDENCE + CAUSAL (native)
                               ▼
                    OPTIONS package later (optional)
                               ▼
                    STATE MACHINE → RADAR
                    (WAIT/WATCH/REJECT research;
                     PK never alone → CONFIRMED)
```

---

## 3. How E2 plugs into the easy funnel

```text
Excel/official links (E1)
    → sector leaders
    → official volume/OI heat
        +
PKScreener (E2)
    → F&O universe
    → pipe: Vol 2.5× → Momentum → Breakout now → ATR
    → 5–20 technical candidates
        ↓
MERGE shortlist
    → intersect (strict) OR union+rank (wide)
        ↓
TrendForge thinking engines
    → safety → harmonic/structure → trend → evidence → causal
        ↓
Radar (research only)
```

### Merge modes (pick one per product profile)

| Mode | Rule | When |
|------|------|------|
| **INTERSECT (strict)** | Symbol must appear in **E1 and E2** | Highest trust shortlist |
| **UNION_RANK (wide)** | Keep either; boost if both | Discovery / research breadth |
| **E2_THEN_E1** | PK first 20 → filter by sector/safety from E1 | When you trust TA heat first |
| **E1_THEN_E2** | Sector×vol first → run PK pipes only on those names | Saves PK runtime; preferred default |

**Default recommendation:** **E1_THEN_E2**  
1) Official sector + volume/OI shortlist (adaptive discovery_budget)  
2) PK pipes only on that list (or on full F&O if list empty)  
3) Intersect or re-rank  

---

## 4. PK scanners mapped to TrendForge modes

| TrendForge mode | PK pipe / scanner idea (Engine 2) |
|-----------------|-------------------------------------|
| **Intraday** | F&O → Volume > 2.5× → High momentum → Breaking out now → ATR cross |
| **ORB-style** | F&O → Intraday price+volume breakout → RVOL → HH/HL |
| **Swing** | Nifty500/F&O → VCP → Chart pattern → MA support → ATR trail |
| **Reversal** | F&O → LH/LL → RSI/PSAR reverse → volume → ATR |
| **Options-flow mode** | PK only for **cash TA**; FO OI still from **official** `nse_fo_bhavcopy` (E1) |

PK does **not** replace official OI/PCR/chain work.

---

## 5. Hard contracts (so PK cannot poison the system)

| Contract | Rule |
|----------|------|
| **Isolation** | PK runs in **pinned env / Docker / subprocess** — not import of full PK into API process at first |
| **Sanitized output only** | Symbols + scanner_key + params + as_of + raw_hash; strip AI labels, potential profit, telegram fluff |
| **Authority** | Every PK hit is family **`TECH_SHADOW`** or later **`TECH_NATIVE`** with `can_support_confirmed=false` until product-plan amendment promotion |
| **No data fallback authority** | PK’s own Yahoo/cache/pickle **cannot** unlock gates or CONFIRMED |
| **Fail-closed** | PK crash/timeout → empty E2 set + reason `PK_ENGINE_UNAVAILABLE`; E1 still runs |
| **No broker** | PK Telegram/alerts optional; **no order path** |
| **MIT pin** | Record commit + license hash (existing `PKUpstreamPin` model) |
| **Backtest** | PK backtest/Growth-of-10k = **research journal only**, not product edge claim |

This matches existing `PKPromotionStatus`: `REGISTERED_NOT_ACTIVE` → `NATIVE_PROMOTION_CANDIDATE` → `NATIVE_PROMOTED`.

---

## 6. PK capability catalog (selected only through File A owners)

### Detail tag PK-A — Connect sidecar

1. Pin version: Docker `pkjmesra/pkscreener:latest` **or** git commit (prefer **commit pin**).  
2. Wrapper script:

```bash
# example conceptual — actual flags from pinned CLI docs
pkscreenercli.py -a Y -o "X:12:9:2.5:>|X:0:31:>|X:0:27" -e
# write JSON/CSV to data/pk_shadow/out/{run_id}.json
```

3. TrendForge API:

```text
POST /api/v1/shadow/pkscreener/run
  body: { universe, pipe_id, params }
  → { runId, status }

GET /api/v1/shadow/pkscreener/result/{runId}
  → sanitized rows[]
```

4. Store under `data/pk_shadow/` with SHA-256 of stdout artifact.  
5. UI: optional panel **“TA shadow hits”** — never green CONFIRMED styling.

### Detail tag PK-B — Wire as Engine 2 in discovery

1. `discovery/engine2_pk.py`:  
   - input: optional symbol universe from E1  
   - call sidecar  
   - return `Engine2Hit{symbol, pipe_id, tags[], evidence_family: TECH_SHADOW}`  
2. Merge policy config: `E1_THEN_E2` default.  
3. Radar columns: `E1_tags | E2_pipe | merge_rank`.  
4. Tests: PK fail does not crash discovery; empty pipe; oversized output reject (harness already has fault modes).

### Detail tag PK-C — Piped profile library

Register pipes as data, not code forks:

| pipe_id | Meaning | PK option string (example — re-verify on pin) |
|---------|---------|-----------------------------------------------|
| `PIPE_INTRADAY_BREAKOUT` | Vol→Mom→Breakout→ATR | document exact string at pin time |
| `PIPE_SWING_VCP` | VCP + pattern + MA | … |
| `PIPE_REVERSAL` | structure reverse + volume | … |

### Detail tag PK-D — Native promotion after governed parity evidence

For each pipe that journals well:

1. Reimplement rules on **TrendForge OHLCV + closed bars** (native scanner).  
2. Parity tests via existing `pk_compatibility` harness.  
3. Promote family to `TECH_NATIVE` with product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`)/test evidence.  
4. Optionally **stop calling** upstream for that pipe.

**Long-term:** PK becomes a **recipe library + parity oracle**, not a permanent runtime dependency.

---

## 7. Where this sits vs other “thinking engines”

```text
E1 Official discovery     → attention (sector, OI, deals)
E2 PK technical pipes     → attention (TA action)
Safety / gates            → veto
Harmonic / structure      → direction
Evidence / causal         → multi-family research state
Options package           → support/weaken (later)
Q5 / risk / deriv / inst  → side tools
```

PK is **only** in the **attention** layer (with E1), never final judge.

---

## 8. Trade Vision vs TrendForge (same idea, two products)

| Product | PK role | After PK |
|---------|---------|----------|
| **TrendForge** | Engine 2 TA shortlist → native structure/causal/radar | Official gates + activation ceiling |
| **Trade Vision** | First-stage 5–20 candidates → MTF / VWAP / paper arbiter | Paper WAIT/WATCH only |

Do **not** share PK output as automatic paper ENTER without TV/TF gates.

---

## 9. What NOT to do

| Don’t | Why |
|-------|-----|
| Import full PK into FastAPI process day 1 | Dependency / license / crash risk |
| Let PK data feed unlock ASM pass or CONFIRMED | Authority leak |
| Show PK backtest % as product win rate | Unaudited assumptions |
| Run PK on all NSE every minute + full option chains | Rate limits + noise |
| Skip sanitization | AI/profit fields pollute evidence |
| Dual-boss (PK score vs causal score) | State machine chaos |

---

## 10. Success criteria

- [ ] PK sidecar run produces sanitized JSON in &lt; N seconds for F&O universe pipe  
- [ ] Discovery merge shows E1 + E2 columns on radar  
- [ ] PK down → discovery still returns E1-only with clear banner  
- [ ] Zero CONFIRMED attributed to PK-only hits  
- [ ] At least one pipe has native parity candidate registered  

---

## 11. PK-A capability record

When File A selects owner `R4`, detail tag `PK-A` consists of a pinned
Docker/CLI wrapper, `POST /api/v1/shadow/pkscreener/run`, sanitization and
artifact storage. It excludes radar redesign and cannot be selected directly
from this catalog.

---

*End. Subordinate to AGENTS.md and product-plan law. PKScreener MIT capabilities are inputs; TrendForge governance is output authority.*

---

## 5. Non-goals (both parts)

- Broker execution / OpenAlgo placeorder  
- Win-probability % product UI  
- Dual CIE + ShadowFlow voting engines / Combined_Score / 84–88 thresholds  
- Activating ChartInk/Trendlyne as gate authority  
- Day-1 Redis rewrite  
- PK alone driving CONFIRMED  

---

## 6. Success criteria (program done when)

- [ ] Radar never shows incomplete runs as primary (M0)  
- [ ] Discovery S2 returns mode-based shortlist with lineage (M4)  
- [ ] Sector headers on UI (M5)  
- [ ] PK sidecar + sanitize + merge works; PK down does not kill E1 (M6–M8)  
- [ ] Options deep path fail-closed when chain empty (M10–M11)  
- [ ] At least one PK pipe natively promoted with parity (M16)  
- [ ] Still research-only; observed runtime activation is false → WAIT honesty  

---

*Detail catalog only. File A selects work; BUILD_STATUS records completion
against the selected R owner and may cite M/T/PK tags as navigation evidence.*

---

## 7. Verification log (2026-07-27) — nothing material skipped

Checked merged product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`)gainst both former full plans (now stubs).

| Source plan | Key topics | Status |
|-------------|------------|--------|
| Restructure / discovery | R-owned detail catalog; §1M product law; G1–G8; modes; inventory | **Present** |
| PK Engine 2 | Two-engine split; E1_THEN_E2; sanitize; shadow API; PK-A–D; promotion; TV vs TF; non-goals | **Present** |
| Detail-tag catalog | M0–M23 / T0–T4 / PK-A..D mapped to R owners | **Present; non-sequencing** |

| Item | Note |
|------|------|
| Full 105 URL line-by-line dump | **Intentionally not** re-pasted (lives in `links data use.txt` / inventory xlsx) |
| Full GPT Python mock-ups | **Intentionally abbreviated** to contracts + milestones (code will implement) |
| Unusable-link category table | **Was thin; added above** under §6 |
| ShadowFlow/CIE full pattern bibles | **Not merged** — legacy archive only under LEGACY banners in grok_plan; day-one whitelist in v9.2/v7.1 §0 |
| product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) full text | **Not duplicated** — authority stays product-plan law (`docs/fable/new_merge_PLAN_2026-07-18.md`) |

**Verdict:** No material coding-plan detail was dropped. Inventory URL encyclopedia stays in inventory files, not this milestone doc.
