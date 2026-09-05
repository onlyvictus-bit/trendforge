# TrendForge — Options Detail Plan

**Version:** 1.6  
**Date:** 2026-07-27  
**Updated:** 2026-08-24 — §19 and §20 added (merge maps v9.2⊕CIE v7.1 and Professional-Mathematics⊕GitHub-references; lens taxonomy + extensions). Additive navigation aid; no prior law changed.  
**Status:** PLAN ONLY — research package design; **not implemented** as a product claim  
**Name:** **Options Detail Plan** (never “File B”; File B = Hybrid)

---

## 0. How to use this file

### Requirement authority

```text
AGENTS → File A (new_merge) R12 (+ R16 when PIT/replay)
  → FINAL_MERGE FMR-003, FMR-004, FMR-005, FMR-006, FMR-007, FMR-008 (as applicable)
  → Hybrid File B sections File A points to
  → THIS FILE (package layout, day-one studies, contracts)
  → Discovery Detail Plan only for UI placement / shortlist context
```

### Implementation evidence (not authority)

```text
runtime → code/tests → BUILD_STATUS / VALIDATION → coverage CSV (trace only)
```

| You want… | Do this |
|-----------|---------|
| **Work selector** | One File A requirement ID: `R0-R18`, `CROSS-###`, or `TDG-GAP-###`; never `M/T/PK`. Options implementation remains owned by R12 (+ R16 for PIT/replay), **not** “next M”. |
| **Options vertical** | Open **FMR-003..008** before coding this file’s modules |
| **Best stock/strike/expiry research use** | **§18 Best research playbook** (this file) — operational rules filtered to File A law |
| **Product UI placement** | Final Merge + Discovery Detail Plan (inspector rules) |
| Deep formula appendices | `grok_plan/shadowflow_deep_dive.md` §0–§17 · `convexity_intelligence_engine.md` §0–§17 |
| Legacy scores / dual engines | **Never** |

**Do not hardcode activation.** Read current `sourceActivationReady` and state ceiling from runtime + BUILD_STATUS + VALIDATION.

### GEX / gamma wording (mandatory)

- Unsigned cash-gamma / concentration = research **proxy** with explicit model label.  
- **Signed GEX / dealer sign** = `SCENARIO_ONLY_NOT_OBSERVED_POSITION` only (FMR-005).  
- Never on state path as observed dealer position; never alone for CONFIRMED.
### Theta, delta-hedged variance and VRP wording (mandatory)

- Professional Mathematics section 17.5 owns the complete dividend-adjusted call/put Theta equations and local delta-hedged realized-versus-implied variance attribution.
- Store model, exercise/settlement style, rate/dividend/carry versions, calendar/trading clock, hedge interval, quote basis and cost-model version. Incompatibility or missing inputs makes the feature `UNKNOWN`.
- Delta-hedged variance attribution is path- and cost-dependent research. It is not directional option P&L, guaranteed gamma-scalping profit, observed flow or an independent vote.
- VRP context compares synchronized same-horizon risk-neutral implied variance with a PIT physical expected-realized-variance forecast. `ATM_IV^2 * T` is `ATM_VARIANCE_PROXY`, not model-free variance.
- Allowed labels are `IV_RICH_CONTEXT`, `IV_CHEAP_CONTEXT`, and `VRP_UNKNOWN` after PIT percentile/calibration gates. Positive/negative VRP, IV/RV, backwardation or contango never automatically means sell/buy options.

---

## 1. One-line design

**One package** `options_intelligence/` with two modules — **surface** (chain shape) + **flow** (OI activity) — that together may only `SUPPORT` / `WEAKEN` / `CONFLICT` / `UNKNOWN`.  
Structure owns direction. Master state machine owns `WATCH` / `WAIT` / `CONFIRMED` / `REJECT`.  
Options **never** own `CONFIRMED` alone. Dual engines, Combined scores, and win-% theater are **rejected**.  
**Pipeline IDs:** implement under File A `R12` + File A §9 **S5 enrich / S6 resolve** (see File A §9.3). FMR-002 “S6 deep derivatives” is story language only, not a second build spine.  
**Operational playbook:** **§18** (stock + strike + expiry + geometry + R-order).

---

## 2. Why this is the best plan (vs old dual docs)

| Old idea | Problem | This plan |
|----------|---------|-----------|
| ShadowFlow + CIE as two voters | Double-count, synergy, fake confidence | **One package cap** |
| Combined_Score / 84–88 gates | Unmeasured folklore | **No scores that own state** |
| Dealer GEX / institutional intent | Not observed on NSE OI | **Unsigned concentration only** |
| 14 + 12 pattern bibles day one | Overbuild, unproven | **5 studies max, day one** |
| Full chain on full universe | Rate limits, empty chain | **R12 shortlist-bounded fetch with chain-quality gate** |
| Options selected outside File A | Creates a second build spine | **R12 selects work; M10/M11 are detail tags only** |

---

## 3. Unbreakable contracts

1. HTTP 200 / hash / URL is **not** proof of scanner-ready evidence.  
2. `VALID_EMPTY` ≠ parse/block/timeout/schema failure.  
3. Missing, stale, partial, unofficial-only, or compiler-unapproved data cannot support `CONFIRMED`.  
4. OI does **not** identify buyer, seller, writer, hedge, dealer, or institution.  
5. Gamma × OI is **unsigned** model concentration — not observed dealer GEX.  
6. Quality = eligibility, not bullish/bearish direction.  
7. Evidence strength ≠ win probability. Any “confidence” = component agreement / coverage only.  
8. One snapshot root cannot mint multiple independent confirmations.  
9. Unclosed candles cannot permanently confirm.  
10. Delayed data must not be labeled live flow.  
11. **No silent fill** for IV, Greeks, rates, dividends, lot size, identity, or quotes on a state path.  
12. OpenAlgo stays disabled / non-authoritative until separately validated.  
13. **No orders**, accounts, positions, margin, qty, or autonomous trading in this package.  
14. Exercise + settlement style required for state-eligible Greeks; model mismatch → unknown / fail-closed.  
15. EOD max pain ≠ intraday pin; UI must say **NOT A FORECAST GUARANTEE**.

---

## 4. Place in the full system

**Build-stage authority is File A §9 `SEL-001..010` only** (crosswalk: File A §9.3).  
The list below is **package-internal narrative** for options work after shortlist — not a second global spine and not FMR-002 story numbers.

```text
Package-internal (after File A cheap path + shortlist):
  P0  Governance / activation ceiling (read runtime; do not hardcode)
  P1  Safety, calendar, identity, F&O eligibility
  P2  Cheap discovery already done (File A S3); M-Factor / attention rank only
  P3  Shortlist + tradability (budget)
  P4  Closed-bar structure is direction owner (File A S4) — must already exist before options enrich
  P5  Budgeted option chain on shortlist only (File A S5 enrichment start)
  P6  Identity / timing / coverage / quote quality on chain
  P7  Surface + flow → ONE OPTIONS_PACKAGE support (File A S5 enrichment)
  P8  Conflict resolution + state publication (File A S6–S7 / SEL-007–008)
  P9  PIT / journal / radar-inspector (File A S8–S9 + UI)
```

**Rule:** Options deep path runs **only** on shortlist. Options never replace M-Factor / discovery.  
**File A map (build authority = §9 SEL only):** structure **S4** before options enrich **S5**; family fuse **S6** (SEL-007); public state **S7** (SEL-008); tools under R12/R15.  
File A §25.25.6 uses different S# narrative labels and must be crosswalked to §9 — it is not a second build spine.

---

## 5. Package architecture

### 5.1 Single tree (day one)

```text
backend/trendforge_api/options_intelligence/
  contracts.py           # OptionsPackageSupportV1
  source_adapter.py      # inherits session/budget/breaker
  snapshot_builder.py    # snapshot_bundle_id
  identity.py
  quality.py             # multi-dimension eligibility
  carry.py
  iv.py                  # exchange IV → mid solve → LTP solve → unknown
  greeks.py              # reuse derivatives_engine only
  surface.py             # PCR, max pain, gamma conc, integrity, later RR25
  flow.py                # OI velocity, vol/OI (FO bhav lite first)
  fusion.py              # one package cap
  storage.py
  replay.py
  observability.py
  api.py
  patterns.py            # STUB ONLY — do not fill with pattern bible
```

### 5.2 Reuse (do not rewrite)

| Existing | Use for |
|----------|---------|
| `derivatives_engine.py` | Dividend-aware BS, IV, first-order Greeks |
| `selection/options_domain.py` | PIT, PCR/walls/max-pain context, ceilings |
| NSE session / source contracts | Bounded fetch, source-result states |
| Current DB / storage | Extend; no PostgreSQL-only rewrite |
| Master state machine | Sole owner of public states |
| Vanilla frontend | Extend; no React rewrite |

### 5.3 Forbidden structures

- Separate `shadowflow/` or `cie/` services  
- `cie.db` or second options score DB  
- Combined_Score, CIE_Score, Shadow_Score, synergy multipliers  
- Two options votes into the state machine  
- Dealer-sign GEX on any state path  

---

## 6. Output contract (state support only)

`OptionsPackageSupportV1` (conceptual fields):

```text
schema_version
symbol / instrument_identity
snapshot_id / snapshot_bundle_id
decision_time / available_at
source_activation_ready
gate_authorized
research_shadow_only
discovery_rank (+ version)
closed_structure_direction          # from structure engine, not options
options_support                     # SUPPORT | WEAKEN | CONFLICT | UNKNOWN
state_ceiling                       # never self-CONFIRMED
reason_codes[]
options_package_quality
surface_summary
  theta_attribution_summary
  variance_risk_premium_context
flow_summary
dataset_roots / correlation_groups
source_results
conflict_flags
formula_versions / feature_versions
lineage_links
generated_at
```

Surface and flow **must share** the same `snapshot_bundle_id` when fused.  
Mismatch → `WAIT_SNAPSHOT_BUNDLE_MISMATCH` (never average two scores).

---

## 7. Surface module (formerly “CIE”)

Describes chain **shape**, not intent.

### 7.1 Semantics

| Fact | Meaning |
|------|---------|
| PCR (OI / volume) | Descriptive; not universal bull/bear |
| Max pain | OI-derived **reference** + sensitivity range |
| Cash-gamma concentration | Unsigned proxy for 1% spot move notional |
| RR25 / Fly25 | Skew diagnostics only if liquid brackets exist |
| Raw integrity | Monotonicity, convexity, parity defects |
| Theta / delta-hedged variance attribution | Model/time/cost-sensitive calculator output; not direction or flow |
| VRP context | Same-horizon implied-versus-expected-realized variance; no automatic premium trade |

### 7.2 Day-one surface whitelist

| ID | Study | Day one? | Gate |
|----|--------|----------|------|
| S-PCR | OI + volume PCR per expiry | Yes | Chain + coverage |
| S-MP | Max pain + sensitivity (index first) | Yes | Chain; stocks later |
| S-GCONC | Unsigned cash-gamma by strike | Yes | Stable Greeks + OI |
| S-RAWQ | Quote/arbitrage diagnostics | Yes | Quotes |
| S-RR25 | RR25 / Fly25 | After fixtures | Bracket both wings; no extrapolate |
| S-TERM | Term structure change | Later | Multi-expiry alignment |
| S-VRP | Variance-risk-premium context | **No / postponed** | R12 synchronized variance contract + R16 PIT forecast/calibration; R18 promotion/drift |
| S-12PAT | Legacy 12 patterns | **No** | Quarantined |

### 7.3 Canonical cash-gamma (unsigned)

```text
cash_gamma_1pct_inr = gamma * OI * lot_size * spot^2 * 0.01
cash_gamma_1pct_inr_crore = cash_gamma_1pct_inr / 10_000_000
```

Calls and puts separate. No dealer sign. No extra ×100 folklore.  
Label: `MODEL_PROXY_NOT_OBSERVED_FLOW`.

### 7.4 RR25 / Fly25 (when ready)

1. Valid IV + model delta per wing.  
2. Two liquid nodes **bracketing** |Δ| = 0.25 each wing.  
3. Interpolate total variance `w = IV² × T` vs |Δ|; **no extrapolate**.  
4. `RR25 = IV_25c − IV_25p` · `Fly25 = 0.5×(IV_25c + IV_25p) − IV_ATM`.  
5. Missing brackets → `SKEW_COVERAGE_UNKNOWN`.

### 7.5 Theta, delta-hedged variance and VRP context

The canonical equations, assumptions and units live in Professional Mathematics sections 17.5-17.7. This package stores only versioned inputs and typed outputs. Required VRP fields are `implied_variance_method`, `realized_variance_forecast_method`, `variance_horizon`, `vrp_proxy`, `vrp_context`, `vrp_status`, `cost_model_version`, `calibration_version` and reason codes. Horizon, timestamp, annualization, trading session and corporate-action conventions must match. Any mismatch, stale forecast, invalid chain, missing costs or unapproved calibration returns `VRP_UNKNOWN`.

This study is postponed from day one. It cannot alter direction, create a second options vote, authorize `CONFIRMED`, or produce quantity/execution.

### 7.6 Chain empty

All surface features → `UNKNOWN` / `SURFACE_UNAVAILABLE`.  
Package surface weight = **0**. Never invent strikes or IV.

---

## 8. Flow module (formerly “ShadowFlow”)

Describes **activity**, not smart money.

### 8.1 Day-one flow whitelist

| ID | Study | Needs full chain? | Notes |
|----|--------|-------------------|--------|
| F-OIVEL | OI velocity vs PIT baseline | No (FO bhav lite OK) | Primary early win for OI UI |
| F-VOI | Volume / OI | Often no | Heuristic only |
| F-ROLL | Near/next expiry migration | Yes | Needs continuity map |
| F-WALL | Gamma wall persistence | Yes | Shares surface gamma |

### 8.2 Five initial research studies (package-level)

All thresholds = `HYPOTHESIS_V0` until OOS.

1. **Gamma concentration wall** — unsigned call/put walls across continuous snapshots.  
2. **OI velocity concentration** — robust anomaly vs PIT peers.  
3. **PCR / skew conflict veto** — inconsistency → WEAKEN/CONFLICT, not direction.  
4. **Expiry roll migration** — near vs next with economic continuity.  
5. **Max-pain pin candidate** — **liquid index only** at first; stocks need settlement/liquidity/OOS proof.

---

## 9. Quality, carry, IV (shared)

### 9.1 Quality dimensions (separate gates)

Authority · freshness · schema · identity · completeness · quote quality · temporal alignment · carry quality · cross-section consistency.

Mandatory failures are hard gates — not hidden inside one average “q score”.

### 9.2 IV hierarchy

1. Valid **exchange IV** (observation)  
2. **Midpoint** solve  
3. **LTP** solve with recency/liquidity penalty  
4. Else **UNKNOWN**

Store method, residual, times, formula version. No silent fallback.

### 9.3 Carry / parity

- Missing dividend ≠ silent `q=0` (unless explicitly versioned assumption).  
- Parity uses bid/ask **interval**, not arbitrary midpoint residual rules.  
- Observed futures basis ≠ implied forward (keep separate).

### 9.4 Settlement

Physical settlement is a **risk fact**. State-eligible model Greeks need known exercise + settlement; else fail-closed.

---

## 10. Ops: session, budget, breaker, cache

Versioned **profiles** per source (no folklore RPM):

- Session: warmup, UA, referer, interval, timeout, retry, block signatures  
- Budget: capacity remaining; shortlist-first; exhausted → `WAIT_RATE_LIMIT_BUDGET_EXHAUSTED`  
- Breaker: CLOSED / OPEN / HALF_OPEN; respect Retry-After  
- Cache: event time, hash, schema version, freshness profile; stale never silent-current  
- Schema drift: archive raw → stop bad normalizer → alert → fixture replay → version bump  

One symbol’s failure must not poison another.

---

## 11. Runtime: cheap → expensive

```text
Discovery E1 (official) + optional E2 (PK shadow)
  → shortlist (10–25)
  → FO flow-lite (optional, no chain)
  → M10: prove chain fetch (or honest WAIT_CHAIN)
  → M11: surface + flow on shared snapshot_bundle_id
  → fusion: one OPTIONS_PACKAGE contribution
  → structure + safety + master SM
  → FE tools with VERIFY strip
```

| Milestone | What | Gate |
|-----------|------|------|
| **M10** | Chain unblock (fixture + live) | Rows **or** explicit empty/block states |
| **M11** | One package surface+flow | No dual score; surface 0 if chain empty |
| **M22** | Strike + Expiry UI | Disclaimer + chain-empty banner |
| Earlier | FO OI velocity for OI panels | No fake surface |

Internal OI steps when coding: OI-0 freeze → OI-1 thin vertical → OI-2 ops → OI-3 math → OI-4 facts → OI-5 five studies → OI-6 PIT → OI-7 UI → OI-8 scale.

---

## 12. Frontend honesty (tools)

Owned with discovery plan left-nav (M-Factor, Index, OI Tracker, Strike, Expiry, …).

Every numeric cell:

```text
value | status | unit | observed_at | source | reason?
```

- Zero ≠ unknown  
- Stale shows age  
- Options-only evidence cannot paint CONFIRMED styling  
- VERIFY strip: source key, freshness, formula version, ceiling  

**Expiry tool:** max pain + walls + ATM IV context + **NOT A FORECAST GUARANTEE**.
**VRP/Theta inspector:** show model, time convention, same-horizon methods, costs, calibration, context/status and reasons. Never show `SELL VOL`, `BUY VOL`, trade direction or probability from this context alone.

---

## 13. Storage & API (sketch)

- Raw: immutable native payloads + sanitized sidecars  
- Normalized: versioned Parquet/Arrow snapshots  
- Lineage/state: existing governed DB (extend)  
- Routes under one API prefix, e.g.:

```text
GET /api/v1/options-intelligence/symbol/{symbol}
GET /api/v1/options-intelligence/symbol/{symbol}/surface
GET /api/v1/options-intelligence/symbol/{symbol}/flow
GET /api/v1/options-intelligence/symbol/{symbol}/lineage/{snapshot_id}
```

No independent CIE/Shadow public state endpoint.

---

## 14. Explicitly rejected (do not plan these)

| Rejected | Why |
|----------|-----|
| Dual CIE + ShadowFlow voters | Double counting |
| Combined_Score / synergy / 84–88 | Unproven folklore |
| Win-rate product claims | Governance + honesty |
| Dealer-signed GEX as truth | Not observed |
| Institutional intent from OI | Not identifiable |
| 14 / 12 pattern bibles day one | Premature scale |
| Full-universe chain every N minutes | Budget / empty chain reality |
| Silent IV / Greek fills | Fail-closed law |
| `IV > RV => sell` / `IV < RV => buy`, fixed VRP thresholds or term-structure trade commands | Horizon mismatch, unpriced tails/costs and absent PIT calibration |
| Orders / OMS / qty | Out of scope forever here |
| React/Redis rewrite for this | Out of scope |

Revival of any rejected item needs **new** File A / requirement ID — not a legacy appendix.

---

## 15. Definition of done (package)

This plan is “implemented enough” only when:

1. One package exists; no dual score path importable.  
2. Chain empty → honest surface unavailable (tests).  
3. Surface + flow share snapshot bundle or WAIT.  
4. Day-one studies only; `patterns.py` still stub or five hypotheses max.  
5. No silent IV/Greek fills on state path.  
6. Exercise/settlement gate on state-eligible Greeks.  
7. Options cannot independently publish CONFIRMED.  
8. UI shows unknown/zero/stale/conflict/ceiling correctly.  
9. PIT replay fixtures exist for at least one index path.  
10. `BUILD_STATUS` / `VALIDATION` record remaining limits.
11. Full Theta fixtures cover dividend/carry, time convention and exercise/settlement compatibility.
12. Delta-hedged variance attribution fixtures include hedge interval, costs and path dependence and never produce direction.
13. VRP fixtures prove same-horizon methods, PIT forecast lineage, `VRP_UNKNOWN` failure states and rejection of automatic option buy/sell language.  

Until then, product copy:

> Experimental options research evidence. Fail-closed, non-executable, not a validated trading edge.

---

## 16. Reference-use catalog

This file never selects implementation work. When File A selects `R12`, derive
one R-first work packet and open the mapped `FMR-003..008` sections. Use this
catalog for package contracts, the Discovery catalog for inspector placement,
and the ShadowFlow/CIE appendices only when a formula detail is missing.
Pattern bibles and dual scores remain rejected. `M10` and `M11` are navigation
tags, not sequential milestones.

---

## 17. Path index

| Role | Path |
|------|------|
| **Options detail catalog** | `D:\TrendForge\docs\OPTIONS_INTELLIGENCE_PLAN.md` |
| Discovery + PK context catalog | `D:\TrendForge\docs\DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` |
| Build priority (R0 first) | `D:\TrendForge\grok_plan\REAL_PATH_FORWARD.md` |
| Deep package law (optional) | `D:\TrendForge\grok_plan\shadowflow_deep_dive.md` |
| Deep surface law (optional) | `D:\TrendForge\grok_plan\convexity_intelligence_engine.md` |
| Historical dual-engine audit | `D:\TrendForge\grok_plan\AUDIT_2026-07-23.md` |
| **GitHub OI/chain fallback (3 repos)** | `D:\TrendForge\docs\GITHUB_OI_CHAIN_REFERENCE_REPOS.md` |
| Proposed code root | `D:\TrendForge\backend\trendforge_api\options_intelligence\` |
| Greeks reuse | `D:\TrendForge\backend\trendforge_api\derivatives_engine.py` |

### Build fallback (if official path stuck)

See **`docs/GITHUB_OI_CHAIN_REFERENCE_REPOS.md`**:

1. https://github.com/krishnabhokare27/et-signal-radar — radar UI / FastAPI shell  
2. https://github.com/raghavs-stack/nse-oi-dashboard — Live OI dashboard patterns  
3. https://github.com/VarunS2002/Python-NSE-Option-Chain-Analyzer — NSE chain fetch/analyze  

**Reference code only** — reimplement under our contracts; no SSI/4-factor score as state.

---

*File A remains supreme. This document does not activate sources, unlock CONFIRMED, or authorize trading.*

## 18. Best research playbook (stock + strike + expiry)

**Purpose:** Operational playbook for research on **stocks, strikes, expiries, geometry
(qty=0)** — and to show the **truth behind maths/numbers** that scanners and many AIs
hide from a common researcher.

**Hybrid source (locked 2026-08-02):** File A (§9–11, §10.4) + FMR-003..008 + this plan
§0–§15 + adversarial Kimi design audit (claim classes, OI side-anonymity, anti-lie
attacks) + Grok enforcement locks (L7/L9/L12 residual risks). Filtered: no invented
public states, no Combined_Score, no third S-map.

**Not authority over File A.** Work selector: `R12` (+ `R16`/`R18` for PIT/proposal).
Bands = **`RESEARCH_DEFAULT_v0.1`** (uncalibrated placeholders, not market law).

### 18.0 One-screen law (memorize)

| Law | Rule |
|-----|------|
| Public states | Only `WATCH` \| `WAIT` \| `CONFIRMED` \| `REJECT` |
| Options package | Only `SUPPORT` \| `WEAKEN` \| `CONFLICT` \| `UNKNOWN` |
| Direction owner | Closed equity **structure** (File A S4); options never own direction |
| Options alone | **Never** CONFIRMED; never CONFIRMED styling |
| Independent family for CONFIRMED | File A §10.4; not correlated echoes of the same chain (see §18.0C) |
| Scores | No Combined_Score / CIE / Shadow / win% / P(win) as truth |
| Rank | File A `evidence_strength` = research rank only (versioned numeric prioritization). UI/API label must remain **“Evidence strength - not win probability”**. Display bands `LOW`/`MED`/`HIGH` optional — never probability |
| GEX | Unsigned cash-gamma attention only; **signed** = `SCENARIO_ONLY_NOT_OBSERVED_POSITION` |
| Max pain | EOD arithmetic reference; **NOT A FORECAST GUARANTEE**; ≠ intraday pin |
| IV / Greeks | Hierarchy fail-closed; no silent fill; near-expiry → `UNKNOWN` when unstable |
| Qty / OMS | Ordinary scanner rows: `qty=0` always; geometry structure-derived only. See §25.23 VRP exception below |
| Activation | When the current observed runtime reports `sourceActivationReady=false`, publication ceiling stays research — no live CONFIRMED even if gates look green |
| Build IDs | File A `R*` + §9 SEL; package P-steps are narrative only |

### 18.0A Truth behind the maths (what other tools hide)

Use this before trusting any Greek, OI label, or “score” on a stock.

| What the screen shows | What it actually is | Honest class |
|----------------------|---------------------|--------------|
| Delta, Gamma, Theta, Vega, Rho | One option **price rewritten** through a **pricing model** + an IV | **MODEL** |
| “Exchange IV” / solved IV | Insurance price of the option, **backed out** from quotes — not a measured destiny of the stock | **MODEL** (from quote FACT) |
| OI, change in OI | Count of **open contracts** | **FACT** (count) |
| “Long buildup / smart money buying” from price↑+OI↑ | **Category error** — every open contract has a buyer **and** a seller; initiator not published on NSE OI | **LIE** (blocked) |
| PCR | Put vs call ratio (OI stock vs volume flow) | **CONTEXT**, never alone |
| Cash-gamma “wall” | `γ·OI·lot·S²·0.01` **unsigned** concentration map | **SCENARIO / attention** — not dealer force |
| Signed GEX / “dealers short gamma” | Needs **assumed** inventory sign | **SCENARIO only** |
| Max pain | EOD OI **bookkeeping**: strike minimizing option-holder payout arithmetic | **FACT as formula result**; **not gravity** |
| Combined_Score / win% / “84 confidence” | Usually **correlated echoes** of the same price+OI, unmeasured without PIT | **Rejected** as product truth |
| Deep OTM “hero-zero” | Lottery path; most expire near zero | **LOTTERY** — quarantine |
| Missing IV filled as 0 | Poisons every Greek while looking precise | **Forbidden** → **UNKNOWN** |

**Five truths for a common researcher (keep):**

1. **Greeks are not five independent facts** — they are model shadows of one price+IV.  
2. **OI is not intention** — side-anonymous; no initiator, dealer, or “smart money” field.  
3. **High IV means insurance is expensive** — not “a big move is guaranteed; buy options.”  
4. **Max pain is arithmetic, not a magnet** — no force law on spot.  
5. **One fused score mostly fuses echoes** — rank to look first is OK; probability theater is not.

**Claim class discipline (every strong claim must pick one):**  
`FACT` | `MODEL` | `SCENARIO` | `LOTTERY` | `UNKNOWN` | `REJECTED_LIE`

### 18.0B False-confidence attacks this package must kill

| # | Attack (how scanners / AIs lie) | Kill rule |
|---|----------------------------------|-----------|
| 1 | “Long buildup confirmed” from OI+price | OI side-anonymous (L13 spirit) |
| 2 | Combined_Score / CIE / Confidence Index | No score owns state |
| 3 | win% / accuracy without PIT | Reject probability theater |
| 4 | Signed GEX as observed dealers | Scenario watermark only |
| 5 | Max pain pin guarantee | NOT A FORECAST GUARANTEE |
| 6 | Silent IV/Greek/lot zero-fill | Fail-closed → UNKNOWN |
| 7 | Unclosed bar “CONFIRMED” | Closed-bar only |
| 8 | Hero-zero as master strategy | `LOTTERY_RESEARCH` quarantine |
| 9 | Stale lot after corporate action | Master + effective date or UNKNOWN |
| 10 | Illiquid LTP as true mark | Liquidity gate → exclude/UNKNOWN |

### 18.0C Residual risks (hybrid enforcement locks)

These are the places design is right but **misuse** creates false belief:

| Risk | Mandatory operator rule |
|------|-------------------------|
| **Cash-gamma proxy worship** | Walls = attention overlay only; hard-capped rank whisper; never “must hold / dealers defend” |
| **Mid-solve IV on wide spread** | Spread gate **before** mid-solve; if fail → IV/Greeks `UNKNOWN` (do not display fake precision) |
| **Independent family double-count** | Declared families (e.g. STRUCTURE, PARTICIPATION, OPTIONS_CONTEXT, EVENT, MARKET_CONTEXT) + correlation groups. PCR + walls + gamma from same chain are **one** OPTIONS_CONTEXT package contribution — not three independent confirms. |
| **Structure + options SUPPORT only** | May raise **review priority**; **CONFIRMED** only if File A §10.4 fully met **and** profile allows OPTIONS_CONTEXT as the independent family. **When unsure → WAIT** with `why_not_confirmed` (safer default than easy CONFIRMED-eligible). |
| **CONFIRMED-eligible ≠ published CONFIRMED** | Activation/research ceiling → `WAIT` + reason even if gates look green |
| **Package reorders review, not universe law** | Cheap shortlist ordinal first; package demotes/prioritizes **inside** shortlist only |

### 18.1 Correct-use matrix (efficient)

| Concept | Measures | Correct research use | Reject as product lie | Status |
|---------|----------|----------------------|----------------------|--------|
| **Delta** | Model ∂V/∂S | Strike band, exposure context | “Delta = P(profit) / true P(ITM)” | MODEL allowed |
| **Gamma** | Convexity / delta change | Instability flag; cash-gamma input | “High gamma = sure big move” | MODEL; near-expiry → UNKNOWN |
| **Cash-gamma wall** | `γ·OI·lot·S²·0.01` unsigned | Concentration attention | Dealer inventory / forced hedge | Attention only |
| **Theta** | Model time decay | Cost drag; expiry warning | Free daily income | MODEL allowed |
| **Vega** | IV sensitivity | Event / IV-crush context | “IV high → buy options” | MODEL allowed |
| **Rho** | Rate sensitivity | Long-dated sanity | Intraday rho theater | Low priority |
| **IV hierarchy** | exchange → mid → LTP → UNKNOWN | Provenance for all Greeks | Silent fill / ATM copy | Fail-closed |
| **PCR-OI / PCR-vol** | Positioning stock vs activity flow | Context / conflict input | Fixed bull/bear law | Context only |
| **Max pain (EOD)** | OI payout arithmetic | Reference panel + disclaimer | Magnet / target | Reference, not forecast |
| **Intraday pin** | Separate study if data | Scenario chat (liquid index) | Same as EOD max pain | Scenario |
| **Signed GEX / flip** | Assumed dealer sign | “IF sign… THEN…” scenario | Observed dealers | SCENARIO_ONLY |
| **RR25 / Fly25** | Skew shape | Surface quality / conflict | Direction without structure | When surface ready |
| **OI velocity** | ΔOI vs baseline | Where activity moves fast | “Smart money entered” | Attention only |
| **VRP** | Same-horizon IV vs expected RV | Labels only: `IV_RICH_CONTEXT` / `IV_CHEAP_CONTEXT` / `VRP_UNKNOWN` (Options plan + File A math boundary) | Auto sell/buy vol; `IV>RV ⇒ sell` | Context; full PIT later |
| **Expiry-day** | γ/θ regime | Tighter freshness; Greeks degrade | Casino sure-pin | Own format + ceilings |
| **Hero-zero** | Deep-OTM lottery | Quarantine list only | Master rank / CONFIRMED | LOTTERY |
| **Physical settlement** | Delivery obligation (stock F&O) | Near-expiry risk flag | Treat as cash-settled index | FACT + gate |
| **Lot / tick / carry / MWPL ban** | Specs + safety | All ₹ math + hard reject paths | Hardcode from memory | Master required |

**Cash-gamma (canonical):**  
`cash_gamma_1pct_inr = gamma * OI * lot_size * spot^2 * 0.01`  
No extra ×100. CE/PE separate. No dealer sign on state path.

### 18.2 Best stock selection (options-aware)

**Order of power (do not invert):**

1. Hygiene: F&O, ban/MWPL, circuit, CA, liquidity floor → else REJECT  
2. Cheap full-universe attention (File A **S3**) — **ordinal rank only**, not confirmation  
3. **Closed structure** (File A **S4**) — owns **LONG/SHORT/NONE** eligibility  
4. Fixed shortlist budget (top-N ordinal)  
5. One **snapshot_bundle** deep chain (File A **S5** / R12) — shortlist only  
6. One OPTIONS_PACKAGE (SUPPORT/WEAKEN/CONFLICT/UNKNOWN)  
7. Family fuse + profile gates → public state (**File A S6–S7 / SEL-007–008**); see File A **§10.4** for confirmation prerequisites (checklist, not a stage ID)  
8. Geometry qty=0 on ordinary rows + `why_not_confirmed` + `missing_evidence` + lineage  

**Decision tree**

| # | Condition | Action |
|---|-----------|--------|
| 1 | Hygiene fail | `REJECT` |
| 2 | Missing/stale/partial data | `WAIT` + `missing_evidence` — never invent |
| 3 | No closed bar / structure NONE | `WATCH` or `WAIT` only — pretty options cannot raise state |
| 4 | Structure + package CONFLICT | Prefer `WAIT` (not auto REJECT unless safety) |
| 5 | Structure + package WEAKEN | Demote rank; usually WATCH/WAIT |
| 6 | Options-only (no structure) | Public state **≤ WAIT** |
| 7 | Structure + SUPPORT + full File A §10.4 prerequisites + profile families + activation allows | May be CONFIRMED-eligible; else **WAIT** with ceiling reason. If the current observed runtime reports `sourceActivationReady=false`, stay research WAIT regardless of gate color |
| 8 | Hero-zero / lottery path | Quarantine — no state authority |
| 9 | CONFIRMED upgrade | File A §10.4 requires **current** closed data and gates on the comparable run; **no** mandatory multi-run hysteresis in File A. Teams may apply hysteresis only as an uncalibrated operational preference, not a product rule |

**Format focus**

| Format | Primary sort | Options role |
|--------|--------------|--------------|
| INTRADAY | Closed session structure + RVOL | Often WAIT without verified live chain |
| SWING | EOD structure + lag-labelled participation | Full package on shortlist |
| FNO | F&O master + chain health | Package required for deep row |
| EXPIRY_DAY | Index first; Greek stability | Tighter UNKNOWN/WAIT; pin = scenario |
| POSITIONAL | Multi-week structure + macro/sector | Options secondary |

**Fusion matrix (structure × package) — no Combined_Score**

| Structure | SUPPORT | WEAKEN | CONFLICT | UNKNOWN |
|-----------|---------|--------|----------|---------|
| Strong closed | May advance **only if** §10.4 + profile families OK; else WAIT | Demote / WAIT | WAIT | Equity path continues; list gaps |
| Weak / none | WATCH/WAIT only | WATCH/WAIT | WATCH/WAIT | Equity only |
| Invalidated | REJECT instance | REJECT | REJECT | REJECT |

**Options effect without owning state:** package may change **review priority** inside the shortlist (SUPPORT up, WEAKEN/CONFLICT down) and may force WAIT — it **cannot** create CONFIRMED alone or rescue structure=NONE.

### 18.3 Best strike selection

**Preconditions (any fail → strike UNKNOWN / exclude)**  
Two-sided quote · bid>0 · freshness · lot/spec match master · OI present · IV hierarchy or UNKNOWN · spread gate before mid-solve · near-expiry stability else `GREEKS_UNSTABLE_NEAR_EXPIRY`.

**Goals (`RESEARCH_DEFAULT_v0.1`)**

| Goal | Role | Δ band (abs) | Master-rank? |
|------|------|--------------|--------------|
| `ATM_LAB` | Pricing / microstructure | ~0.45–0.55 | Lab/context |
| `DIRECTIONAL` | Express structure bias (research) | ~0.35–0.55 | Yes as research context only |
| `HEDGE_CONTEXT` | Protection cost / skew | ~0.15–0.30 | Context |
| `WALL_ATTENTION` | High unsigned cash-gamma overlay | n/a | **Flag only** |
| `LOTTERY_OTM` / hero-zero | Asymmetry study | ~0.05–0.15 | **No** |

**Rules**

- Prefer **liquidity** over perfect theoretical delta.  
- Max pain + walls **inform** tools; **never** set public state.  
- One `snapshot_bundle_id` for surface + flow + Greeks.  
- Index max-pain reference preferred over thin single-stock pin stories.  
- Expiry matched to structure horizon; expiry-day format uses L10 degradation.

### 18.4 Entry / exit research geometry (qty = 0)

| Field | Source | Rule |
|-------|--------|------|
| `entry_zone` | Closed structure | Band only — never strike/wall/max-pain derived |
| `invalidation` | Structure void level | Required; if none → stay WAIT |
| `targets[]` | Structure / measured move | Labeled research geometry, not promise |
| `time_stop` | Profile horizon | Prevents zombie rows; expiry-aware |
| `cost_drag` | Spread + charges + theta notes | Estimate; disclose RESEARCH_DEFAULT if uncalibrated |
| `rr` | Geometry-only reward/risk sketch | Invalid if stop inside noise band → demote WAIT; never sizing |
| `qty` | — | **0 for ordinary scanner rows**. After File A **R12+R16+R18**, a hidden non-executable `VRP_RESEARCH_PROPOSAL` may carry a **research lot count** from manually supplied assumptions only (File A §25.23 + VRP addendum after §18.11). That lot is not an order, cannot change public state, and cannot access broker data |

**Combine:** structure owns geometry; package only annotates context (SUPPORT note / WEAKEN demote / CONFLICT stand-down / UNKNOWN list gaps).

**Banned UI / speech (non-exhaustive):**  
SELL VOL · BUY VOL · pin guaranteed · max pain magnet · dealers must buy/sell · GEX shows dealers long · smart money buying (from OI) · long/short buildup confirmed · win rate · P(win) · accuracy · sure shot · hero-zero jackpot · delta = probability of profit · Combined_Score · fill/OMS language · BUY NOW / guaranteed target.

### 18.5 Expiry-day and hero-zero (honest)

**Allowed:** liquidity collapse, spread blowout, wall migration, max pain **reference**, settlement/exercise risk, tighter freshness, Greeks → UNKNOWN when unstable.  
**Forbidden:** price must pin · one PCR = direction · signed GEX as force · invent chain.  
**Hero-zero:** separate `LOTTERY_RESEARCH` view; full premium at risk; expectancy UNKNOWN without PIT; never master rank, never CONFIRMED authority, no “opportunity” framing.

### 18.6 Output contract (one research row)

```text
symbol, format ∈ {INTRADAY,SWING,FNO,EXPIRY_DAY,POSITIONAL}
asof: { bar_close_ts, chain_snapshot_ts }
public_state ∈ {WATCH,WAIT,CONFIRMED,REJECT}
structure: { bias LONG|SHORT|NONE, closed_bar, basis }
options_package ∈ {SUPPORT,WEAKEN,CONFLICT,UNKNOWN}
evidence_strength: File A research rank (numeric prioritization OK if labelled not win%); optional band LOW|MED|HIGH
claim_notes[]: each tagged FACT|MODEL|SCENARIO|LOTTERY|UNKNOWN
missing_evidence[]                     # required when gaps exist
why_not_confirmed[]                    # required unless CONFIRMED
freshness_ok, safety_veto[]
preferred_strikes[]: role ∈ {ATM_LAB,DIRECTIONAL,HEDGE_CONTEXT,WALL_ATTENTION,LOTTERY_OTM}
  + greek_status ∈ {OK,UNKNOWN,UNSTABLE_NEAR_EXPIRY}
max_pain: { value?, disclaimer: NOT_A_FORECAST_GUARANTEE }
gex_signed: { status: SCENARIO_ONLY_NOT_OBSERVED_POSITION }
geometry: {
  entry_zone, invalidation, targets, time_stop, cost_drag, rr?,
  qty: 0   # ordinary scanner rows; VRP_RESEARCH_PROPOSAL research lot only per File A §25.23 after R12+R16+R18
}
lineage: { snapshot_bundle_id, engine_versions, rule_version }
evidence_strength_label: "Evidence strength - not win probability"
```

**Validate:** ordinary qty==0 · no win% · no options-only CONFIRMED · missing→UNKNOWN not zero · UI state = resolver state · activation ceiling respected.

### 18.7 Implementation priority (R-order only)

| Order | Work | Acceptance (one) |
|------:|------|------------------|
| 1 | R0 residual honesty / provenance | Missing feed → UNKNOWN, no fabricate |
| 2 | R2 cheap S0–S3 live-safe | Completeness + WAIT ceiling without activation lies |
| 3 | R5 closed structure path | Closed-bar only; unclosed → WAIT |
| 4 | R12 chain identity + quality + one package | Empty chain honest; no dual score importable |
| 5 | PCR / walls / max pain compute | Degenerate OI → UNKNOWN not 0 |
| 6 | Greeks via `derivatives_engine` | Spread/near-expiry fail → UNKNOWN; no NaN |
| 7 | Strike Explorer + Expiry tool | Disclaimers + VERIFY + claim-class labels |
| 8 | Fuse package into equity state | Options alone cannot CONFIRMED (test) |
| 9 | Property tests | No Combined_Score; no signed GEX on state path; no silent IV; no OI side-language |
| 10 | R15 research UX | Inspector shows why_not_confirmed + missing_evidence |
| 11 | R16 PIT replay | Then-available only |
| 12 | R18 promotion/rollback | No P(win) UI without PIT_APPROVED; still no OMS |

### 18.8 Fail-closed gates (binding)

| Gate | Failure |
|------|---------|
| IV hierarchy or spread-gate fail | IV/Greeks UNKNOWN |
| Spec/lot/expiry master stale | UNKNOWN / WAIT |
| F&O ban / MWPL hard rule | REJECT or block fresh FO research |
| Chain quality / bundle mismatch | WAIT_CHAIN / WAIT_SNAPSHOT_BUNDLE_MISMATCH |
| Near-expiry greek instability | GREEKS_UNSTABLE_NEAR_EXPIRY |
| Liquidity/spread beyond profile | Strike excluded / UNKNOWN |
| Options-only path | Public state ≤ WAIT |
| Combined_Score / win% / OMS / dealer-as-fact | Reject row / fail CI |

### 18.9 What free models / humans must not invent

1. Dealer sign/size or “smart money” from OI  
2. Lot, expiry weekday, weekly scope, STT, CTM from memory — **contract master only**  
3. Phantom strikes / OI / IV not in snapshot  
4. Alternate public states (`TRADEABLE`, `NO_TRADE`, etc.)  
5. Bare magic thresholds without `RESEARCH_DEFAULT_vX.Y`  
6. Second build spine (M-order or third S-map)  
7. win% / Combined_Score under a new name (“confidence index”)  
8. Mid-solve Greeks on wide/one-sided books  

### 18.10 Daily self-test (any wrong answer = stop trusting the row)

1. Ordinary scanner row qty = 0? (VRP research lot only via §25.23 path if ever shown)  
2. public_state only WATCH/WAIT/CONFIRMED/REJECT?  
3. Any CONFIRMED from options alone? (must be **no**)  
4. Any win% / fused probability score? (must be **no**)  
5. IV provenance known for every displayed Greek?  
6. Any zero/silent fill of IV/Greek/lot/carry? (must be **no**)  
7. Signed GEX framed as scenario only?  
8. Max pain labeled NOT A FORECAST GUARANTEE?  
9. Near-expiry unstable Greeks → UNKNOWN?  
10. Unclosed bar driving CONFIRMED? (must be **no**)  
11. Ban/MWPL/circuit/CA checked before strong states?  
12. why_not_confirmed + missing_evidence present when not CONFIRMED?  
13. Any “buildup confirmed / smart money” language? (must be **no**)  
14. Claim class tagged (FACT/MODEL/SCENARIO/LOTTERY/UNKNOWN)?  

### 18.11 Best-of-best (hybrid creed)

Let **closed-bar structure** alone own directional eligibility; run hygiene and cheap attention first; spend expensive chain only on a shortlist; compress all options into one package that can **SUPPORT / WEAKEN / CONFLICT / UNKNOWN** but never self-anoint CONFIRMED; treat walls, signed GEX, and max pain as **labeled scenarios/references**, not forces; fail IV and Greeks **closed to UNKNOWN**; keep ranks **ordinal**; quarantine hero-zero as **lottery**; stamp **qty=0**, **why_not_confirmed**, **missing_evidence**, and **lineage** on every row; force every strong claim into **FACT / MODEL / SCENARIO / LOTTERY / UNKNOWN** so the system’s most common honest answer is **WAIT**, and its rarest, most audited answer is **CONFIRMED**. Design confidence can be high; **live numbers stay UNKNOWN** without a real timestamped snapshot_bundle.

---

### Conditional VRP research proposal addendum

File A section 25.23 and Professional Mathematics section 17.10 replace only
the former blanket ban on displaying a VRP-derived position, quantity or hedge
proposal. After `R12`, `R16` and `R18` acceptance, the hidden inspector may
show a defined-risk, non-executable `VRP_RESEARCH_PROPOSAL`, research lot count
and hedge structure. Missing chain quality, calibration, costs, liquidity,
stress, instrument mechanics or hedge inputs returns
`NO_RESEARCH_PROPOSAL`.

The proposal cannot alter a public state or evidence vote, cannot recommend
naked/unbounded short volatility, cannot access broker/account data and cannot
create an order or execution intent.

---

### 18.12 Research Overlay Notes (Upgrades 28–33 — not live R1–R5) - 2026-08-19

These notes preserve India-specific microstructure research safeguards from Hybrid V3 (Upgrades 28–33). They are research overlay notes only and do NOT alter live R1–R5 ceilings, source counts, or selection states:

1. **Upgrade 28 (Physical settlement & expiry-week margin ramp - S1/S6 research overlay):** All Indian stock F&O are physically settled (cash delivery obligation on ITM options / short futures with escalating margin ramps in the final 3 sessions). Research backtests must model delivery-feasibility and forced exit before margin ramp rather than theoretical expiry settlement. Index options remain cash-settled.
2. **Upgrade 29 (Publication-lag PIT timestamps - S0/SH research overlay):** Datasets carry actual publication timestamps (`WHERE published_at <= plan_time`); missing or lagging EOD bhavcopy / participant OI files must trigger `WAIT_STALE` rather than silent assumption of instant availability.
3. **Upgrade 30 (Intraday bar capture for long-horizon VRP):** Phase-1/research data collection benefits from recording 5-minute bars for benchmark indices and F&O universe from day one to build continuous realized volatility (HAR-RV / Yang-Zhang) history for long-horizon VRP research.
4. **Upgrade 31 (Participation-rate sizing cap - S7 research overlay):** Capacity constraint safeguard in research backtests: order quantity capped at \(\le 10\%\) of strike OI and \(\le 5\%\) of 20-day ADV / traded value to avoid modeling fictional liquidity.
5. **Upgrade 32 (Macro event calendar layer - S1/S2 research overlay):** Scheduled macro volatility blackout (RBI MPC, Union Budget, election results, US FOMC/CPI) within 24h for short-gamma / naked-long index research setups unless specifically modeled as defined-risk event trades.
6. **Upgrade 33 (Option-leg fill realism: mid \(\pm\) half-spread):** Backtest option leg entries at \(\text{mid} + \frac{1}{2}\text{spread}\) (buys) / \(\text{mid} - \frac{1}{2}\text{spread}\) (sells) reconstructed from historical chains with a \(\ge 1\)-tick slippage floor, never theoretical bhavcopy settlement prices.
7. **S4/S5 paper A/B (not live):** keep **both** original compressed S4/S5 (`p̂ = σ(-0.4 + 1.2·z_side + 1.2·z_book)`, wall as entry) and the split family (`p̂` from B1–B3; B4 package; B5 location) until paper days decide. UI: `#s4s5ComparePanel` WITH / WITHOUT / BOTH. API: `GET /api/v1/selection/s4s5-compare`. New files: `backend/trendforge_api/selection/s4s5_compare.py`, `backend/tests/test_s4s5_compare.py`, `frontend/s4s5-compare.js`. `RESEARCH_PROXY_NOT_CALIBRATED`. Not size. Not CONFIRMED. Not File A rank.

---

## 19. Merge Map (ShadowFlow v9.2 ⊕ CIE v7.1) + Lens-Purpose Taxonomy - 2026-08-24

**Status:** Navigation/planning aid only — adds no law and changes no ceiling.
Formula authority stays with the deep laws (`grok_plan/shadowflow_deep_dive.md`
§0–§17, `grok_plan/convexity_intelligence_engine.md` §0–§17); File A remains
supreme; all §18 claim-class rules apply to every row below.

### 19.1 Decision record (why this merge shape)

| Candidate | Verdict |
|-----------|---------|
| Physically merge both grok files into one document | REJECTED — destroys quarantine/traceability banners; LEGACY ARCHIVE zones must stay isolated below their banners |
| Companion laws + one merge-map section here | CHOSEN — canonical short plan carries navigation; deep files untouched |
| No doc map; merge only in code | REJECTED — future sessions re-litigate ownership |

### 19.2 Document-level ownership after merge

| Owner | Governs | Maps to code (`options_intelligence/`) |
|-------|---------|----------------------------------------|
| Parent v9.2 (ShadowFlow deep dive) | session/budget/breaker/cache · identity · carry · IV hierarchy · Greeks reuse · quality gates · storage/replay · ops contracts | `contracts.py` `source_adapter.py` `snapshot_builder.py` `identity.py` `quality.py` `carry.py` `iv.py` `greeks.py` `flow.py` `fusion.py` `replay.py` `storage.py` `observability.py` `api.py` |
| Child v7.1 (CIE) | surface studies ONLY (its §0.2 whitelist) · IV node classes · RR25/Fly25 method · max-pain policy · gamma-concentration units | `surface.py` `surface_interpolation.py` `surface_quality.py` `surface_studies.py` `surface_api.py` |
| Forbidden for both | second engine/score/DB/state path · anything under LEGACY ARCHIVE banners · Combined_Score/CIE_Score/synergy · pattern bibles | `patterns.py` stays STUB until OI-5 |

### 19.3 Four runtime hooks (where child output enters parent flow)

| # | Hook | Rule | Failure code |
|---|------|------|--------------|
| H1 | Shared snapshot | surface + flow consume the same `snapshot_bundle_id` | `WAIT_SNAPSHOT_BUNDLE_MISMATCH` |
| H2 | Output contract | CIE emits one `surface_summary` into `OptionsPackageSupportV1` ∈ {SUPPORT, WEAKEN, CONFLICT, UNKNOWN} | — |
| H3 | Vote cap | OPT_SURFACE + OPT_FLOW = ONE OPTIONS_CONTEXT package contribution (§18.0C correlation groups) | dual vote must fail CI |
| H4 | State ceiling | master state machine owns public states; options never CONFIRMED alone | ceiling WAIT |

### 19.4 Lens-purpose taxonomy (question-first)

Reading rule: **direction owner = closed equity structure (File A S4)**.
Every option lens may only SUPPORT / WEAKEN / CONFLICT / UNKNOWN. The
independence column marks same-dataset-root twins: twins share ONE package
vote but MAY be overlapped to grade a research reference zone (zone drawing ≠
extra votes; authority basis: §18.1 correct-use matrix + the research-reference-
zone acceptance display from CIE §18.4).

**A. WHERE — levels / reference zones (S&R attention)**

| Lens | Input data | Question it answers | Independence | Power |
|------|------------|---------------------|--------------|-------|
| OI strike walls | OI by strike (FACT count) | Where puts/calls stack below/above spot | chain root #1 | Attention zone; never entry authority (§18.4) |
| Cash-gamma wall (S-GCONC) | γ·OI·lot·S²·0.01 (MODEL proxy) | Where hedge-notional concentrates; pin / speed-bump candidates near expiry | chain root #1 — twin of OI walls | Same single vote; label `MODEL_PROXY_NOT_OBSERVED_FLOW` |
| Max pain (S-MP) | OI payout arithmetic (FACT result) | Which strike minimizes holder payout at expiry | chain root #1 — twin | EOD reference + NOT A FORECAST GUARANTEE |

**B. WHICH WAY — trend/direction context**

| Lens | Input data | Question it answers | Independence | Power |
|------|------------|---------------------|--------------|-------|
| Closed-bar structure | OHLCV (File A S4/R5) | LONG / SHORT / NONE — sole owner | independent of chain | OWNS direction |
| OI PCR | positioning stock of OI | Slow structural bias | chain root #1 | CONTEXT only |
| Volume PCR | day's traded volume | Fast sentiment pulse | chain root #1 — twin of OI PCR | CONTEXT only |
| RR25 / Fly25 (after fixtures) | IV wings at 25Δ | Fear/greed tilt of insurance pricing | IV slice of chain root | Diagnostics / conflict input |
| Term structure (later) | multi-expiry IV | Stress regime (contango/backwardation) | IV slice — correlated with RR25 | Context |

**C. HOW FAST — short-period speed / momentum / decay**

| Lens | Input data | Question it answers | Independence | Class | Notes |
|------|------------|---------------------|--------------|-------|-------|
| Gamma (per contract) | model ∂Δ/∂S | Why a strike "accelerates": hedge amplification near ATM + expiry | chain root #1 (OI×IV priced) | MODEL | Near-expiry instability → UNKNOWN (`GREEKS_UNSTABLE_NEAR_EXPIRY`) |
| OI velocity (F-OIVEL) | ΔOI vs PIT baseline | Which strikes' OI is changing fastest vs baseline | chain root #1 | FACT-computed | Attention only; no intent/buildup language |
| Volume / OI (F-VOI) | volume ÷ OI | Today's conviction vs stock of existing positions | chain root #1 — twin of OI velocity | FACT-computed | Heuristic only |
| Theta | model time decay | Buyer's cost bleed into expiry | pricing-model inputs | MODEL | Cost-drag context; strategy-finder input later |
| Roll migration (F-ROLL) | near vs next expiry OI | Rotation → continuation vs exhaustion clue | near+next chain roots, same bundle | FACT-computed | Needs economic-contract continuity map |

**C+. DELTA — the five jobs of positive/negative delta (explicit)**

Delta was implicit above (skew coordinates, gamma's base). Its five legal uses:

| # | Job | Positive delta | Negative delta | Family | Law limits |
|---|-----|----------------|----------------|--------|------------|
| 1 | Payoff direction of one option | Calls (+0→+1) gain when stock rises | Puts (−1→0) gain when stock falls | B context | `MODEL` claim class; never "Δ = P(win)" (`§18.1`) |
| 2 | Equivalent share exposure | Δ 0.50 call ≈ half-share per lot | Δ −0.40 put ≈ short 0.40-share hedge | strike picker (§18.3 bands: DIRECTIONAL \|Δ| 0.35–0.55 · HEDGE 0.15–0.30 · LOTTERY 0.05–0.15) | Liquidity beats perfect delta |
| 3 | Skew coordinate axis | Call wing node at +0.25Δ | Put wing node at −0.25Δ → RR25/Fly25 | B diagnostics | Needs liquid brackets; else `SKEW_COVERAGE_UNKNOWN` |
| 4 | Gamma's underlying | γ = speed at which Δ changes near ATM/expiry | same | C | Near-expiry → UNKNOWN gate |
| 5 | OI-weighted delta map by strike | Where cumulative call Δ stacks below spot | Where cumulative put Δ stacks above spot | SCENARIO overlay | Sign of who-holds-what unobserved → `SCENARIO_ONLY_NOT_OBSERVED_POSITION`; never state path |

Reading: delta answers **"how much like the stock does this strike behave, and in which direction"** — it bridges WHERE (strike choice) and HOW FAST (via gamma), but stays a MODEL shadow of one price+IV (§18.0A truth #1).

**D. WHEN TO DOUBT — reversal/conflict guards**

| Signal | Meaning | Result |
|--------|---------|--------|
| Surface internals disagree (PCR vs skew vs term) | Internal contradiction | `WAIT_OPTION_SURFACE_CONFLICT` |
| Package opposes closed structure | Options say opposite of chart | `WAIT_STRUCTURE_CONFLICT` — seats WAIT, never creates an opposite trade |
| RAWQ parity/monotonicity defect | Chain data untrustworthy | surface UNKNOWN; package weight 0 |
| Term-structure flip / event IV-crush window | Regime-shift risk | Context warning; no automatic trade |

Trend/reversal law restated: options NEVER calculate trend and never confirm
reversal — they flag doubt (WAIT) or support/weaken. Trend and reversal stay
owned by closed-bar structure.

### 19.5 Trending-stock pick chain (who does what)

```text
hygiene gate (REJECT on ban/MWPL/CA/liquidity fail)
  → cheap full-universe attention rank: gap / RVOL / volume (ordinal only)
  → closed-bar structure: LONG / SHORT / NONE (direction owner)
  → shortlist budget (top-N)
  → ONE budgeted chain snapshot (shortlist only)
  → families A+B+C+D compress into ONE package vote
  → fusion matrix (§18.2) → research row (state ≤ ceiling, qty=0, lineage)
  → strategy-finder app consumes rows downstream (separate project; no write-back)
```

### 19.6 Self-test additions (extend §18.10)

15. Any row treating walls + max pain + PCR as three separate confirms from one chain snapshot? (must be **no**)
16. Any "trend from options" language anywhere in a row? (must be **no** — structure owns)
17. Merge-map respected: new surface code lands only under `surface*.py`? (must be **yes**)
18. Any row using delta as win-probability / "true P(ITM)" / dealer inventory fact? (must be **no** — MODEL + SCENARIO limits, §19.4-C+)

### 19.7 Deep-law pointers not duplicated above (audit pass 2026-08-24)

Second audit over both governing files (v9.2 §0–§17; CIE v7.1 §0–§20). Items
below live ONLY in the deep laws today; each is retained here so the short
plan's reader knows it exists without opening the appendices. Nothing here
changes law — it points at it.

| # | Pointer | Source | Why it matters |
|---|---------|--------|----------------|
| a | **IV node authority ladder:** `OBSERVED > SOLVED_MID > SOLVED_LTP > INTERPOLATED > FITTED`; interpolated nodes can never become separate evidence; fitted nodes stay diagnostic until manually promoted | CIE §6.1 | Stops skew/term studies quietly counting twice |
| b | **Gamma P&L ≠ cash-gamma:** `gamma_pnl_1pct = 0.5·γ·OI·lot·S²·(0.01²)` lives in its OWN field/formula; never share the `cash_gamma_1pct` field | CIE §19.3 | Dimensional lie otherwise looks precise |
| c | **Premium-OI put/call ratio** (`put_call_premium_oi_ratio`) kept as correlated descriptive diagnostic; state-ineligible; never replaces OI/volume PCR | CIE §18.4 | Useful context that must not become vote #2 |
| d | **Research reference zones carry acceptance state:** price accepted / rejected / not-yet-tested displayed next to every wall/max-pain zone | CIE §18.4 | Turns static levels into testable zones; entry authority still structure-owned |
| e | **NSE single-stock options are EUROPEAN exercise + PHYSICALLY settled**, stored independently in contract master; American models forbidden without master proof (`CIE7-029..032`) | CIE §19.2 | Prevents wrong pricing engine on stock options |
| f | **Cross-sectional PIT baseline jobs** (by comparable universe, DTE, expiry, market phase) feed velocity/PCR/skew/concentration comparisons | v9.2 §5.6 | "High PCR" is meaningless without its peer baseline |
| g | **Replay cost scenarios are versioned** (instrument, liquidity, DTE, spread, time) and outcome classes include competing events — informative interruptions are never silently censored | v9.2 §11 | Strategy-finder app consumes these bands later; no invented market impact |
| h | **Source-offline honesty:** `SURFACE_RESEARCH_OFFLINE` + last attempt/success + reason; archived payloads stay visible but marked stale, never current | CIE §19.5.7 | Empty card ≠ offline; stale ≠ live |
| i | **Expiry lifecycle records:** listed expiries, expiry type, last-trading/settlement dates, rollover mapping; strike-grid/expiry-set change resets migration matching (`CIE7-040`) | CIE §19.5.2 | Roll-migration study dies without continuity anchors |

Deliberately NOT carried into the short plan (already governed as rejected):
Combined_Score / CIE_Score / synergy, signed GEX as fact, writer-side Theta,
pattern bibles, fixed folklore constants (84/88 gates, OI>500, ±15% bands,
universal TTLs), ML auto-weights. Revival requires a new File A requirement.

---

## 20. Merge Map (Professional Mathematics ⊕ GitHub OI References) + Taxonomy Extensions - 2026-08-24

**Status:** Navigation/planning aid only. `PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md`
is opened through File A §25.22 and stays research math until R16/R18 +
`PIT_APPROVED`; `GITHUB_OI_CHAIN_REFERENCE_REPOS.md` is build-fallback
reference, never gate authority. File A remains supreme. Two audit passes over
both files completed 2026-08-24.

### 20.1 Decision record

| Candidate | Verdict |
|-----------|---------|
| Physically merge both files into this plan | REJECTED — math book keeps its own File-A-scoped authority chain; GitHub file is an ops catalog whose value is its steal/quarantine lanes |
| Pointer-map + taxonomy extension here | CHOSEN — the short plan becomes the single place a reader learns these lenses exist |
| No map (already in path index §17) | REJECTED — lens additions and fallback playbook were invisible to planners |

### 20.2 What each file IS (purpose · function · use)

| | `PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md` | `GITHUB_OI_CHAIN_REFERENCE_REPOS.md` |
|--|--|--|
| Type | 1,305-line research-math reference | 213-line build-fallback catalog |
| Purpose | Defines HOW to judge honestly: exact event Y_t, calibrated p_t, EV after costs, barrier probability, true Greek math | Defines WHERE to borrow proven patterns when official build is stuck |
| Key contents | EV = p·G − (1−p)·L − C; break-even p_min=(L+C)/(G+L); residual strength; time-of-day RVOL; GARCH Z-return; barrier formula; OI quadrant codes; RND/SVI; FUS-009 + M-Factor canonical formulas; cost model C; 15-condition decision gate; 0DTE framework audit (claim-by-claim rejections) | G1 et-signal-radar (UI shell) · G2 nse-oi-dashboard (OI/PCR/max-pain patterns) · G3 Python-NSE-Option-Chain-Analyzer (NSE session/headers/brotli unblock); symptom→repo playbook; pin+license rules |
| When opened | Through File A §25.22 only | When M10 chain fetch stuck, OI UI layout needed, or PCR/max-pain display wrong |
| Never | Second build order; win% before R16/R18; auto premium sell/buy from VRP sign | Gate source; CONFIRMED unlock; dual voter; SSI/4-factor scores as truth |

### 20.3 Lens taxonomy extensions (extends §19.4 — read with its law)

These rows ADD to families B/C/D. Independence column marks dataset roots;
correlated lenses share one family vote per §18.0C.

**Family B additions — WHICH WAY (trend QUALITY for picking trending stocks)**

| New lens | Formula / input | Question it answers | Independence | Class | Power |
|----------|-----------------|---------------------|--------------|-------|-------|
| **Residual strength** | `r_resid = r_stock − α − β_mkt·r_mkt − β_sec·r_sec` (rolling β shrunk toward priors on small samples, closed bars, CA/regime-invalidated, residual uncertainty reported) | Is the stock REALLY leading, or riding its sector? Rising 1% while sector rises 2% = negative leadership | equity-bars root — independent of chain | FACT-computed on MODEL betas | Structure-family context; the honest "trending stock" filter (`math §4`) |
| **VWAP displacement** | `Z_VWAP = (Price − VWAP)/σ_intraday` | Location vs fair intraday price | equity-bars root | FACT-computed | Weak alone; needs residual + RVOL + spread + structure agreement list (`math §4`) |
| **Futures basis residual** | `ln(F/S)/T − (r−q)` annualized | Bullish carry pressure / financing demand in futures | derivatives root (futures+spot quotes), distinct from chain options | FACT-computed context | Context, never direction alone; basis ≠ implied forward (`math §7, §14.4`) |
| **Implied quantile range** | `S_T band = S₀·exp[(r−q−½σ²)T ± z·σ√T]` | Risk-neutral scenario range for target sanity | chain root #1 (IV-derived) | MODEL | Reference only; not physical forecast |

**Family C additions — HOW FAST**

| New lens | Formula / input | Question it answers | Independence | Class | Notes |
|----------|-----------------|---------------------|--------------|-------|-------|
| **Time-of-day RVOL** | cumulative volume ÷ median of COMPARABLE sessions (expiry/event/short-day aware) | Is participation genuinely abnormal right now? | equity-volume root | FACT-computed | Replaces naive vs-yesterday RVOL (`math §4`) |
| **Volatility-standardized move** | `Z_return = r/σ_t` (GARCH-style conditional σ) | Is this % move big FOR THIS STOCK? | equity-bars + MODEL σ | MODEL-assisted | 2% can be noise for one name, signal for another (`math §5`) |
| **Variance decomposition split** | overnight vs session σ² · upside/downside semivariance · jump share · vol-of-vol | WHERE does the speed come from: gap, churn, or crash-vol? | equity-bars root | FACT-computed | Refines every C-row; an NSE overnight gap is not intraday momentum (`math §5`) |
| **Trade-sign cumulative delta** | IF aggressor side existed: `Σ(signᵢ·qtyᵢ)` buyer-initiated + / seller-initiated − | Net aggressive order-flow momentum | tick-trade root (NSE publishes no aggressor side) | unbuildable today | POSTPONED; inference method must be stored if ever sourced (`math §17.4`). Distinct from option delta (§19.4-C+) |
| **Gamma-scalping break-even move** | `\|dS\|_be = √(−2Θ·dt/Γ)` (local, no-cost) | How far must price move before a long-gamma strike pays its theta bleed? | pricing-model inputs | MODEL | Expiry-week speed honesty; strategy-finder input; never a direction call |

**Family D refinement — OI quadrant FACT codes (replaces buildup folklore)**

| Price | OI | Stored code | Folklore word BANNED from product copy |
|-------|----|-------------|----------------------------------------|
| up | up | `OI_RISE_PRICE_RISE` | "long buildup confirmed" |
| down | up | `OI_RISE_PRICE_FALL` | "short buildup" |
| up | down | `OI_FALL_PRICE_RISE` | "short covering" |
| down | down | `OI_FALL_PRICE_FALL` | "long unwinding" |

Codes are observable co-movement FACTS; the folklore words are interpretations
of unobserved intent (`math §7`). Feeds OI-velocity interpretation only.

**P. Declared-but-postponed lenses (name reserved; needs data TrendForge lacks)**

| Lens | Formula | Blocker | Status |
|------|---------|---------|--------|
| Full order-flow imbalance / microprice | `Δm = λ·OFI + ε`; queue imbalance, cancellations | Needs timestamped L2 order-book events; LTP+volume insufficient | POSTPONED (`math §3`) |
| Barrier target-before-stop probability | `P(τ_b < τ_a)` drift formula; MUST also estimate finite-horizon `τ_b ≤ H` + neither-barrier case | Only via PIT replay/Monte-Carlo under R16/R18 | POSTPONED (`math §6`) |
| Calibrated probability display | Beta posterior / logit models, Brier score, reliability-by-bucket | Immutable PIT outcomes + costs + calibration + File A approval | Unavailable until R16/R18 (`math §8,15`) |
| RND / state-price-density tail | Breeden–Litzenberger: `f_Q(K,T) = e^{rT}·∂²C/∂K²`; `Q(S_T>K)` from strike slope | Risk-neutral tail mass at a strike — NOT physical crash probability | POSTPONED under mapped R12/R16/R18; needs smooth arbitrage-checked surface (`math §7, §17.7`) |
| Abstention/coverage reporting | accuracy must always ship with coverage %, drawdown, tail loss, decay | Part of any future performance report; prevents cherry-picking | Required at R16/R18 reporting (`math §12–13`) |

### 20.4 Guardrails each file contributes (best details, line-by-line)

From the math book:
1. **Eight research evidence families** (structure, rel-strength, participation, derivatives, catalyst, ownership/sponsorship, regime, execution-feasibility) — RESEARCH FRAMING ONLY. The BINDING caps stay §18.0C's declared families + correlation groups (STRUCTURE, PARTICIPATION, OPTIONS_CONTEXT, EVENT, MARKET_CONTEXT); File A wins on any collision (`§9`).
2. **FUS-009 / M-Factor canonical formulas mirrored** (`§14.2–14.3`): group-max then family-max, clamp 0–100 — evidence RANK, never probability.
3. **Cost model**: `C = half_spread + fees + slippage + impact ≈ Y·σ·√(Q/ADV)` — scenario model, versioned (`§10`).
4. **15-condition professional decision gate** incl. `p_low > p_min` and positive conservative EV — future R16/R18 only (`§11`).
5. **Strike-derivative trap**: `[C(K+ε)−C(K−ε)]/2ε` estimates dC/**dK**, NOT Delta (dC/dS) — normally negative (`§17.3`).
6. **Theta/Gamma ratio is NOT a constant** — carry/value term must vanish first; no universal 0.5 threshold (`§17.3`).
7. **SVI parameterizes total variance w(k,T)**, IV = √(w/T) — common audit error corrected (`§17.2`).
8. Full dividend-adjusted Theta equations + delta-hedged P&L attribution = `0.5·Γ·S²·(σ²_realized − σ²_implied)·dt − costs` (`§17.5`).
9. VRP labels only (`IV_RICH_CONTEXT` / `IV_CHEAP_CONTEXT` / `VRP_UNKNOWN`), forward-variance intervals for non-overlapping horizons; conditional research proposal states under File A §25.23 (`§17.6/17.9/17.10`).

From the GitHub references:
10. Per-repo **steal lanes vs quarantine lanes** (e.g., G3's NSE headers/brotli = highest-value unblock; its bullish/bearish OI labels and zero-fill-on-error = forbidden).
11. **Symptom→repo fallback playbook**: chain blocked → G3 session tricks; PCR/max-pain display wrong → reimplement G2 formulas; radar shell weak → G1 layout. **Rate-limit/CAPTCHA → NEVER rotate fingerprints or bypass access controls; fail-closed WAIT** (`repos §5`).
12. **Integration rules**: pin commit SHA, license check (G3 = GPL-3 — re-implement, don't paste), ports land off state-path, CI test that no foreign score imports into CONFIRMED path.

### 20.5 Pipeline plugs

```text
Math book   → R16/R18 probability/EV gates · strategy-finder app foundation
              (EV-after-costs scoring; accuracy always reported WITH coverage,
              walk-forward + embargoed holdout; backtests MUST include
              delisted/failed securities, conservative same-bar barrier
              ordering, and a strategy-selection (multiple-testing) correction
              — `math §13`)
              · M-Factor/FUS-009 formula mirror (§14)
GitHub refs → M10 chain-unblock emergency kit (G3) · OI dashboard UI patterns (G2)
              · radar shell ideas (G1) · never on gate/state path
```

### 20.6 Self-test additions (extend §18.10)

19. Any OI quadrant code translated into buildup/covering language in product copy? (must be **no**)
20. Any "trending stock" picked on raw % change without residual-strength check? (must be **no** — `math §4`)
21. Any use of strike-slope finite difference labelled as Delta? (must be **no** — it is dC/dK, `math §17.3`)
