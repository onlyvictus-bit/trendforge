# GLM / OPEN-MODEL BUILD PROMPT — Make OI Analysis, OI Tracker, Strike Explorer, Expiry Range *useful*
## Four existing nav rooms · observation-first OI · official MWPL/ban hard blocks · Q vs P · IV recorder Day-1 · CONTEXT_ONLY / PAPER_CANDIDATE (not File A CONFIRMED)

Copy **this entire file** into GLM. Think first. Do not invent Combined_Score, SSI, “long buildup” as fact, qty, broker orders, or `sourceActivationReady=true`.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. Chain with `;` not `&&`.  
**Date: 2026-08-23.**

Nav (already in `frontend/index.html`, group **Index & derivatives** — not Discovery):

| Button | `data-tool` | Live ceiling today | BFF today |
|--------|-------------|--------------------|-----------|
| **OI** | `oi_analysis` | `RESEARCH_SHADOW_ONLY` + fixture | **Missing** |
| **OT** | `oi_tracker` | `WAIT_CHAIN` + fixture | **Missing** |
| **ST** | `strike_explorer` | `WAIT_CHAIN` + fixture | **Missing** |
| **EX** | `expiry_prediction` | `WAIT_CHAIN` + fixture (label must stay **Expiry Range Context**) | **Missing** |

Shared tabs already in `#tool`: Signals / How validated / Track record / Engines used. Paint them like `frontend/m-factor-live.js` (live owner, no fixture fallback).

This prompt **adopts the HYBRID LINE-BY-LINE AUDIT merged spec v2** (user paste 2026-08-23) as **research-guidance law for these four rooms**, mapped onto TrendForge inventory. File A still owns public product states WATCH/WAIT/REJECT/CONFIRMED. OI/options **cannot** emit File A `CONFIRMED`. Guidance may emit `PAPER_CANDIDATE` with `authority=CONTEXT_ONLY`, `can_confirm=false`.

---

## 0. Outcome (done = observed)

A trader can open **OI / OT / ST / EX** and see **live, lineage-hashed** numbers (or a typed WAIT code), use them to **screen and paper-guide** F&O, and never confuse Q-probability with a win-rate.

1. **OI Analysis:** futures (not options) price+OI on **aligned expiry**; observation codes; MWPL/ban/ASM gates first.  
2. **OI Tracker:** PCR/OI **path** over same inclusion policy; roll-aware windows.  
3. **Strike Explorer:** strike ladder only if chain quality passes; walls with persistence; spread %.  
4. **Expiry Range:** same-expiry estimate + max-pain **reference**; Tuesday cycle; physical-settlement T−2 block.  
5. **IV surface recorder starts Day 1** even if IV Rank is UNKNOWN for a year.  
6. Track record **sampleCount=0**, winRate=null, until R16.  
7. Unified JSON guidance (hero-zero / trend-time) rendered by LLM **verbatim** — LLM computes nothing.

---

## 0.1 Rule changes this ticket is allowed to make (and forbidden ones)

**Allowed (product copy + FTR-020 display aliases):**

| Old (do not show as primary) | New primary | Rule |
|------------------------------|-------------|------|
| `OI_RISE_PRICE_RISE` | `PRICE_UP_OI_UP` | Observation-first. Keep old code as `legacy_code` for tests. |
| `OI_RISE_PRICE_FALL` | `PRICE_DOWN_OI_UP` | Same |
| `OI_FALL_PRICE_RISE` | `PRICE_UP_OI_DOWN` | Same |
| `OI_FALL_PRICE_FALL` | `PRICE_DOWN_OI_DOWN` | Same |
| Internal MWPL 80/90/95 colour bands as “exchange states” | Official: `BAN` (OI>95% EOD → ban **next day**), `RESUME` (OI≤80%), `ALERT60` (60% alert, 10-min) | Internal yellow/orange = `INTERNAL_CONVENTION` only |
| Unlabeled `N(d2)` as win-rate | Always `prob_touch_Q` and `prob_touch_P` (P null until Brier) | Printing Q as P is a **fail** |
| `theta_per_day = theta × 1` | Decay = reprice `price(t) − price(t+Δ)` one clock | |
| Architecture 80/90/95 “SAFE/YELLOW/ORANGE” as authority | Cite official NSE position-limits; keep architecture bands labeled internal | |

**Forbidden even if user wants “signals”:**

- File A `CONFIRMED` from OI, PCR, max pain, hero-zero, or Greeks.  
- Qty, OMS, auto-add size. **Ban-penalty hard block:** if any future automation would **increase** a banned scrip, the engine must `HARD_BLOCK_BAN_ADD` (NSCC T+1 penalty). Research UI shows blocker; it does not send the order.  
- `LONG_BUILDUP` / writer / dealer / FII as **observed fact**. Inspector may say “textbook interpretation: … (not a fact)”.  
- Silent zero for missing IV/OI/PCR denominator.  
- Mixing futures OI with option OI in one number (`fo_a6_enrichment.py` already forbids this).  
- Shoonya/yfinance as gate authority.  
- Copy-paste GPL `Python-NSE-Option-Chain-Analyzer` into product (reimplement).

**New allowed research state (options rooms only):**  
`WAIT | WATCH | PAPER_CANDIDATE | REJECT`  
`PAPER_CANDIDATE` = “paper this structure”; **not** File A CONFIRMED; `can_confirm=false`.

---

## 0.2 Folder law

| Kind | Path |
|------|------|
| **New package (keep)** | `D:\TrendForge\backend\trendforge_api\options_intelligence\` |
| | `quadrant.py` observation codes + roll window |
| | `mwpl_gate.py` official BAN/RESUME/ALERT60 + internal convention |
| | `chain_quality.py` spread, crossed book, completeness |
| | `surface.py` PCR, walls, max-pain, pin **reference** |
| | `pricing.py` Black-76, IV solver, greeks, synthetic F |
| | `pricing_tests.py` (or `backend/tests/test_options_pricing_suite.py`) suite A5 |
| | `iv_recorder.py` daily surface snapshots **Day 1** |
| | `guidance.py` hero-zero / trend-time JSON; Q vs P |
| | `hard_blocks.py` ban-add, ITM-stock-expiry T−2, event-eve naked short, spread>8% |
| | `calendars.py` Tue weekly NIFTY, last-Tue monthly all-NSE, holiday→prev, mega-expiry flag |
| | `bff.py` four tool DTOs |
| **Wire** | `main.py` `GET /api/v1/tools/oi_analysis\|oi_tracker\|strike_explorer\|expiry_prediction` |
| **Keep existing** | `selection/fo_a6_enrichment.py`, `selection/options_domain.py`, `selection/mwpl_b.py`, `parsers/nse_fo_bhavcopy_parser.py`, `gate_readiness.py` G13 |
| **Frontend keep** | `frontend/oi-options-live.js` (new live owner for the four tools, pattern of `m-factor-live.js`) |
| | bump `?v=20260823-oi1` in `index.html` |
| **Tests create** | `backend/tests/test_oi_analysis_bff.py`, `test_oi_tracker_bff.py`, `test_strike_expiry_bff.py`, `test_options_pricing_suite.py` (none of these exist yet — write them; do not assume they exist) |
| **Docs keep** | this file; `docs/BUILD_STATUS.md`; `docs/VALIDATION.md` |
| **Throwaway** | `D:\TrendForge\delete\oi_options_wip_2026-08-23\` curl, notebooks, cloned OSS **reference only** |
| **OSS clone (optional, not importable)** | `D:\TrendForge\delete\oi_options_wip_2026-08-23\reference\nse-oi-dashboard` etc. **Never** add as pip dep |

Do not grow `product-fixture.js` as live owner. Fixture may delegate: if `TrendForgeOiOptionsLive.ownsActiveTool()` then call it (same pattern as M-Factor).

---

## 1. Authority

| Rank | File | Use |
|------|------|-----|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` FTR-020, R12, no CONFIRMED from options | |
| 2 | `AGENTS.md` | Research-only, no broker |
| 3 | This prompt + user merged spec v2 (L0–L7, A1–A5, C1–C15) | Guidance + hard blocks + official MWPL |
| 4 | `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` §1F, §1G, §1I | Tracker PCR; Expiry Range name; wording law |
| 5 | `docs/fable/FINAL_MERGE_PLAN.md` options APIs / FMR-005/006 | Surface vs flow; unsigned gamma |
| 6 | `docs/GITHUB_OI_CHAIN_REFERENCE_REPOS.md` | Steal **layout/helpers**; reject SSI / 4-factor bias / silent zero |
| 7 | Live: `fo_a6_enrichment.py`, `options_domain.py`, `mwpl_b.py` | |

NSE facts this spec treats as **true** (user-verified 2026-08-23; re-check pages if they change):

- Ban: OI **>95%** MWPL **EOD** → banned **next day**; **only offsetting**; **increasing** position → **penalty T+1** → `HARD_BLOCK_BAN_ADD`.  
- Resume: OI **≤80%**.  
- **ALERT60** at 10-minute intervals.  
- PRISM collateral 70/80/90 warn, 100 withdraw → **broker margin API is authority**; estimates forbidden for execution (research may show `WAIT_MARGIN_API`).  
- TM/FPI/MF combined limit **20–30% MWPL** = wall-strength **context**, not a vote.  
- Legacy bhavcopy ended **2024-07-08**; use **UDiFF Common Bhavcopy Final**.  
- Weekly NIFTY **Tuesday**; weekend gap compresses onto **Monday**; last Tuesday = mega-expiry + stock physical settlement.

---

## 2. Already live — READ

```
selection/fo_a6_enrichment.py     futures slices; oi_quadrant string; futures≠options
selection/options_domain.py       OptionType CE/PE; PCR/walls/max_pain; WAIT_CHAIN; cannot confirm
selection/mwpl_b.py               MWPL_MISSING vs READY; can_veto
parsers/nse_fo_bhavcopy_parser.py
parsers/nse_mwpl_parser.py
gate_readiness.py                 G13_OI_CONFIRMS cannot CAN_CONFIRM
derived_market_outputs.py         option chain + rbi_tbill for some math
frontend/app.js                   TOOL_REGISTRY ceilings
frontend/m-factor-live.js         copy this ownership pattern
```

`GET /api/v1/tools/oi_*` **do not exist**. Fixture paints ILLUSTRATIVE rows (TATASTEEL +18.4% etc.). Those must not appear in live DTOs.

---

## 3. Open source — how to use (user: no restriction on *reading*; product still reimplements)

| Repo | Path to clone under delete/ | Steal | Do not ship |
|------|------------------------------|-------|-------------|
| [nse-oi-dashboard](https://github.com/raghavs-stack/nse-oi-dashboard) | `delete/oi_options_wip_2026-08-23/reference/nse-oi-dashboard` | PCR, max-pain loop, wall clustering, IST hours, dual-tab UI | 4-factor bias, signal 0–100, Shoonya as File A gate, max-pain as target |
| [Python-NSE-Option-Chain-Analyzer](https://github.com/VarunS2002/Python-NSE-Option-Chain-Analyzer) | same `/reference/` | NSE headers/brotli **ideas**, refresh-if-changed, ±N strike OI sums | GPL paste; default missing to 0; “OI Bullish/Bearish” product labels |
| [et-signal-radar](https://github.com/krishnabhokare27/et-signal-radar) | same | FastAPI/UI shell ideas | SSI 0–100, buy/sell AI as state |

Rewrite formulas in `options_intelligence/`. Pin commit SHA in BUILD_STATUS if you copy more than 20 lines (then rewrite anyway).

---

## 4. Data to wire (nothing skipped = named slots)

| Slot | Source keys / modules | Tool | Fail-closed |
|------|----------------------|------|-------------|
| Futures close, prev close, OI, ΔOI, volume, expiry | `nse_fo_bhavcopy` UDiFF via A6 | OI Analysis | Missing prior OI / mismatch expiry → `UNKNOWN` not Neutral-as-direction |
| OI spurts | `nse_oi_spurts` | OI Analysis attention | Not intent |
| Ban list | `nse_fno_ban` | All four | `HARD_BLOCK_BAN_ADD` |
| MWPL % | `nse_mwpl_percentages` | All four | Official BAN/RESUME/ALERT60; missing → `MWPL_MISSING` (cash rank may continue; F&O guidance WAIT) |
| ASM/GSM stage | surveillance parsers | All four | Stage restrictions beside ban |
| Participant OI | `nse_participant_oi` | OI Analysis **regime strip only** | Never “FII bought this stock” |
| Option chain same expiry | `nse_option_chain_equity` / index chain | ST + EX + Tracker PCR | `WAIT_CHAIN`; empty chain ≠ failed FO EOD |
| Rates | `rbi_tbill_yield` | pricing F, carry | Missing → `WAIT_CARRY_INPUT` |
| Spot/cash | R1 bhav / identity R4 | alignment | CA break → `WAIT_CA` (R14) |
| Delivery % | official MTO | OI Analysis swing context | Never intra |
| IV snapshots | new recorder table | all | Rank UNKNOWN until ≥1y; **still write today** |
| Broker margin | optional later | L5 | `WAIT_MARGIN_API` if absent; **no invented SPAN** |
| Event calendar | new small table (budget/RBI/results) | EX / hero-zero | `HARD_BLOCK_EVENT_EVE_NAKED_SHORT` T−1 |
| Lot/tick/expiry | **contract file only** | all | Never hardcode lots |

---

## 5. Data flow

```text
Official last-good (hash, data_date, available_at)
    ├─ FO bhav UDiFF  → futures identity (symbol, expiry, FUT vs OPT)
    ├─ MWPL + ban + ASM/GSM → hard gates BEFORE quadrant
    ├─ R14 CA + R4 pin → reject parallel unadjusted contracts
    ├─ Option chain snapshot (same underlying, one expiry, one bundle)
    └─ IV recorder append-only (even if chain PARTIAL)

OI Analysis (snapshot):
    quality: aligned interval, same expiry, roll-window flag
    Δprice, ΔOI → PRICE_UP_OI_UP | ... | UNKNOWN
    columns_spec (L3):
      Price path     rising/falling ALIGNED interval     trap: not a breakout
      OI delta       % Δ futures OI                      trap: same contract/expiry
      Volume/OI      activity vs outstanding             trap: not smart-money
      Bucket         one of 4 codes or UNKNOWN           trap: never BUY/SELL
      State          WATCH/WAIT/REJECT                   trap: OI ≠ CONFIRMED
    MWPL official state + INTERNAL_CONVENTION caution
    TM/FPI/MF 20–30% MWPL context on walls

OI Tracker (path):
    same PCR inclusion policy open→current
    call OI denom 0 → UNKNOWN not Inf
    expiry roll = new series unless economic bridge
    weekly→monthly migration window: suppress fake ΔOI (C7)

Strike Explorer (chain OK else WAIT_CHAIN):
    CE/PE OI, ΔOI, volume, IV, bid/ask, spread_pct
    walls {first_known_at, touches, persistence, unwind}
    unsigned cash-gamma 1% — NEVER dealer GEX
    spread_pct > 8% → HARD_BLOCK_SPREAD (hero-zero / paper)

Expiry Range Context:
    max_pain reference + sensitivity; not destination
    estimated range + method + DTE + Tuesday-cycle flag
    mega-expiry last-Tuesday stress tag
    physical ITM stock FUT/OPT T−2 HARD_BLOCK_PHYSICAL_DELIVERY
    hero-zero JSON: dist_sigma, prob_touch_Q, prob_touch_P=null, ev_after_costs
    decay by reprice, not theta×1
```

---

## 6. Function / module flow

```text
load_fo_lineage()            # hashes FO + MWPL + ban; 503 WAIT_MIXED_SNAPSHOT
official_mwpl_state()        # BAN | RESUME | ALERT60 | MWPL_MISSING | INTERNAL_CONVENTION extras
observation_quadrant()       # PRICE_* codes; roll-aware
build_oi_analysis_batch()    # GET /api/v1/tools/oi_analysis
build_oi_tracker_batch()     # PCR path
evaluate_option_chain()      # EXISTING options_domain.py — call it
build_strike_batch()
build_expiry_range_batch()
record_iv_surface()          # Day 1, append-only
pricing.black76 / iv_solve / greeks
hard_blocks.evaluate()       # list[blocker]
guidance.emit(use_case)      # frozen JSON; LLM only renders
```

API:

```text
GET /api/v1/tools/oi_analysis?symbol=&limit=
GET /api/v1/tools/oi_tracker?underlying=&expiry=
GET /api/v1/tools/strike_explorer?underlying=&expiry=
GET /api/v1/tools/expiry_prediction?underlying=&expiry=   # name in UI: Expiry Range Context
POST any of these → 405
```

Unified guidance JSON (every L4 use case):

```json
{
  "use_case": "HERO_ZERO",
  "contract": "NIFTY-YYYY-MM-DD-K-CE",
  "observed": {"spot": 0, "premium": 0, "dist_sigma": 0, "spread_pct": 0},
  "inferred": {
    "prob_touch_Q": 0,
    "prob_touch_P": null,
    "prob_keep_premium_Q": 0,
    "ev_after_costs": 0
  },
  "authority": "CONTEXT_ONLY",
  "can_confirm": false,
  "state": "WATCH",
  "blockers": [],
  "invalidation": ""
}
```

LLM (`L7`): display this JSON; **compute nothing**.

---

## 7. UI — where signals and engines show

Same `#tool` room, four tools:

**Signals tab**

- OI Analysis: table = columns_spec above; hero MWPL/ban chip; no BUY/SELL chips from OI.  
- OI Tracker: open PCR, current PCR, path Rising/Falling/Flat, gap reasons.  
- Strike: ladder; wall tags; spread_pct; `HARD_BLOCK_SPREAD` banner.  
- Expiry: range low/high + method; max-pain reference; mega-expiry / physical T−2 banners; hero-zero JSON panel.

**How validated:** chain quality, alignment, MWPL official vs internal, roll window, IV status, event calendar.

**Track record:** locked PIT_NOT_VALIDATED sample 0.

**Engines used:**

| Engine | Authority |
|--------|-----------|
| FO UDiFF parser | FACT futures |
| Quadrant | OBSERVATION only |
| MWPL/ban/ASM | HARD VETO |
| Chain quality | STATE CEILING WAIT_CHAIN |
| Pricing/IV | DERIVED; Q≠P |
| Max pain / walls | REFERENCE |
| Guidance | CONTEXT_ONLY |
| Structure (R5) | Direction owner — OI does not replace it |
| PK / M-Factor | Not an OI vote |

**Workflow (trader):** Structure/M-Factor first → **OI Analysis** agree/fight → **Tracker** persistence → if chain OK **Strike** walls/spread → **Expiry Range** DTE/physical/hero-zero → paper only if no HARD_BLOCK. Still no order ticket.

---

## 8. Mandatory test suite (A5 + product)

`backend/tests/test_options_pricing_suite.py`:

- Put-call parity bounds  
- Finite-difference greeks vs analytic  
- CE/PE known values  
- Zero-vol / zero-time limits  
- Synthetic forward multi-strike consistency `F=K+e^{rT}(C-P)`

Product tests:

- Quadrant UNKNOWN on mismatch/equality/roll pollution  
- PCR denom 0 → UNKNOWN  
- Ban add → blocker present; can_confirm false  
- Fixture 18.4% / TATASTEEL demo strings absent in live DTO  
- POST 405  
- Empty chain: FO EOD OI Analysis still 200; Strike/Expiry WAIT_CHAIN  
- IV recorder inserts a row even when IV Rank UNKNOWN  
- `prob_touch_Q` never labeled winRate  
- `PAPER_CANDIDATE` never stored as File A CONFIRMED  

Frontend acceptance: four tools live-owned; no `|| decisionTools.oi_analysis` fallback when BFF 200/503.

---

## 9. Slice order (ship each)

1. **Package + MWPL official states + quadrant PRICE_* + OI Analysis BFF** from A6 FO bhav (no chain required).  
2. **oi-options-live.js** for `oi_analysis` only; fixture delegates.  
3. **OI Tracker** PCR path from successive FO/chain snapshots; roll window.  
4. **IV recorder** table + append on every accepted chain snapshot.  
5. **Strike + Expiry BFFs** calling `evaluate_option_chain`; WAIT_CHAIN if fail.  
6. **hard_blocks** + guidance JSON (hero-zero Q; P=null).  
7. **pricing_tests** A5.  
8. Calendars: Tuesday weekly, last-Tue mega-expiry, physical T−2.  

Do not start with broker websocket or tax exports (C13/C15) until 1–8 work. Stub `WAIT_MARGIN_API` / `WAIT_FEED_BACKOFF` codes so slots are not silent.

---

## 10. Expected live behaviour

| Tool | 200 with rows when | Else |
|------|-------------------|------|
| OI Analysis | Hash-matched FO bhav + identity | 503 lineage or empty + MWPL_MISSING |
| OI Tracker | ≥2 comparable observations same policy | WAIT_PATH / UNKNOWN PCR |
| Strike / Expiry | Valid same-expiry chain | WAIT_CHAIN; FO snapshot may still show |

**Useful screening:** names with aligned `PRICE_UP_OI_UP` **after** structure, MWPL not BAN, spread OK.  
**Useful paper guidance:** hero-zero JSON with Q probs, EV after costs, blockers.  
**Not useful yet (honest):** P-probability, IV Rank, broker-accurate margin, tick slippage, circuit-freeze gap sizing (stops are assumed to slip through price-band gaps until tick-level slippage lands at R16) — record data now; calibrate at R16.

---

## 11. Stop-if

- You would set `can_support_confirmed=true` on option assessment.  
- You would default missing OI/IV to 0.  
- You would fill Strike from FO bhav only.  
- You would import Shoonya into `gate_readiness`.  
- You would leave probes in `backend/tests` instead of `delete/oi_options_wip_2026-08-23/`.

---

## 12. After merge

Update `docs/BUILD_STATUS.md` and `docs/VALIDATION.md` with pytest commands and live counts.  
Move clones and dumps under `D:\TrendForge\delete\oi_options_wip_2026-08-23\`.

M-Factor remains a **separate** FUS-009 room. OI is **one OPTIONS/FO family**, not a second M-score.
