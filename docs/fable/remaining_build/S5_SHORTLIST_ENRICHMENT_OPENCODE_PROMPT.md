# OPENCODE BUILD PROMPT — File A S5 shortlist enrichment
## Delivery, FO OI, options **package**, events, delayed sponsor, MCX — expensive loop on shortlist only

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. Shell: PowerShell. Chain with `;` not `&&`.

Copy this **entire file**. Think first.

**S4 structure pack is upstream** (R5 WAIT). This ticket is **S5 only** = File A `SEL-006`.

Do **not** rebuild S1–S4, R1–R5, R14, or S2. Do **not** run this on the full 2,463-name universe.  
Do **not** set `sourceActivationReady=true`. Do **not** emit CONFIRMED or qty.  
Do **not** paste Hybrid S4/S5 `p̂`/Kelly into R5 or R6.

**Options:** for the options **timeline/package** slice only, open  
`docs/OPTIONS_INTELLIGENCE_PLAN.md` as **detail** (P5–P7, OPTIONS_PACKAGE SUPPORT/WEAKEN/CONFLICT/UNKNOWN).  
File A still wins: options never confirm a stock; GEX is not dealer positioning; no chain → `UNKNOWN_NEEDS_R12`.  
Do **not** implement the whole options tree in this ticket. One package field is enough.

---

## 0. Outcome (done means this was **observed**)

1. Enrichment runs **only** on the S4 structure-claimed shortlist: names with ≥1 `CG_PRICE_STRUCTURE` / `CG_COMPRESSION` claim from `GET /api/v1/selection/structure` (or the s4-structure pack). FALLBACK (only if S4 GET missing): R2 WATCH-40 ∩ latest R5 `detected_setups` ≠ ∅ — **never bare R2 WATCH-40**, never all-universe MTO/FO/options.
2. Each shortlist row has typed fields: delivery (EOD z or UNKNOWN), FO OI package, options package, named deal, delayed MF, SHP promoter/public with `shpFiiDelta=null`, MCX local if commodity, `whyUnknown[]`.
3. `nse_fii_dii` remains **market chip only**. Unnamed deal ≠ FII. Delivery **forbidden** on intraday horizon.
4. Options: `OPTIONS_PACKAGE=UNKNOWN_NEEDS_R12` unless a **fresh expiry-scoped** chain exists; then package SUPPORT/WEAKEN/CONFLICT/UNKNOWN — **score 0 on missing chain**, cash-only not punished.
5. Public state still WATCH/WAIT/REJECT. **0 CONFIRMED. qty=0.**
6. Existing `test_r6_live.py`, `test_top10_research.py`, `test_r5_live_structure.py` still pass.

---

## 1. What S5 is (File A §9 wins)

| Stage | ID | Work | Ceiling |
|---|---|---|---|
| **S5** | `SEL-006` | Shortlist enrichment: delivery, futures OI/basis, options timeline, filings, PIT/SAST/deals, pledge/shareholding, event/earnings, MCX context | Typed claims; **no all-universe expensive loop** |

§25.25.6 “S4 = events, S6 = F&O” is **narrative**. Events + FO + options belong here under §9 S5.

| This ticket IS | This ticket is NOT |
|---|---|
| Expensive joins on a **bounded** list | S3 cheap full-universe pass |
| Delivery z swing-only (`FTR-019`) | Intraday delivery (`REJ-004`) |
| One FO OI package (`CG_FUTURES_OI`) | OI level + change + basis as 3 votes |
| One OPTIONS_PACKAGE (`CG_OPTION_CHAIN`) | PCR/walls/GEX as several votes or dealer GEX |
| R6 stickers completed into claims | A second top-10 sort |

**Already live:** `selection/r6_live.py` WATCH-40 stickers; `top10_research.py` display sort; evidence radar recipes (delivery z, AMFI, deals, FO, SHP null). **Reuse those functions.** Do not duplicate parsers.

---

## 2. Authority

| Rank | File | Use |
|---|---|---|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` | S5 `SEL-006`; `FTR-019` delivery; `FTR-026` events; `FTR-027` delayed sponsor; FO family; options context; `FTR-028/029/030` MCX |
| 2 | `docs/OPTIONS_INTELLIGENCE_PLAN.md` | **Options package contract only** (P5–P7). Not File A sequence. No GEX-as-dealer |
| 3 | Locked R0/R1/R2 plan | R6 is stickers; R12 options later |
| 4 | Hybrid File B | Named deals / AMFI lag. No qty |

---

## 3. Honest source contract (memorize)

| Key | Grain | S5 use |
|---|---|---|
| `nse_mto_delivery` | symbol, EOD | Delivery z if ≥20 PIT sessions; else UNKNOWN. **Not** S3, **not** intra |
| `nse_fo_bhavcopy` / A6 | F&O shortlist | One OI quadrant+change+basis **package** |
| Option chain last-good | expiry-scoped | OPTIONS_PACKAGE; missing → UNKNOWN_NEEDS_R12 |
| `nse_large_deals` / bulk/block | symbol if named | EVENT; empty client → UNNAMED_DEAL ≠ FII |
| `nse_shareholding_pattern` | quarter | promoter/public context; **`shpFiiDelta=null`** |
| AMFI deltas | delayed month | `DELAYED_MF`; never “bought today” |
| `nse_fii_dii` | **market** | Chip only |
| Announcements / results / PIT / SAST / pledge | symbol + available_at | EVENT_AND_SPONSOR, dataset-root once |
| MCX bhav + master | contract | Local % / DTE; CFTC grey only |
| Third-party FII screens | — | INFO +0 |

Forbidden sentence: “FII bought {symbol} last week” unless a **dated official named deal or SHP FII% parser** (parser still missing → null).

---

## 4. Options slice (from Options Detail Plan — bounded)

If you cannot prove a fresh chain in a test on real last-good:

```text
optionsPackage.status = UNKNOWN_NEEDS_R12
optionsPackage.canSupportConfirmed = false
```

If a chain **is** last-good and complete enough for the plan’s day-one package:

- One `OPTIONS_PACKAGE` ∈ `SUPPORT | WEAKEN | CONFLICT | UNKNOWN`
- PCR/walls/max pain/IV share `CG_OPTION_CHAIN` — **one** family
- GEX unsigned concentration = proxy label; **never** “dealer hedging”
- Surface weight 0 if chain empty
- **Shortlist only** (plan P5). Never full-universe chains

Do **not** build `options_intelligence/` entire tree unless the package field is blocked without it. Prefer a 40-line adapter over a new product.

---

## 5. What to build (paths — reuse the designed shell)

**Create / touch**

| Role | Path |
|---|---|
| New or extend | `D:\TrendForge\backend\trendforge_api\selection\s5_shortlist_enrichment.py` **or** extend `r6_live.py` without changing R2 attention-priority computation |
| Tests | `D:\TrendForge\backend\tests\test_s5_shortlist_enrichment.py` |
| Routes | `D:\TrendForge\backend\trendforge_api\main.py` — **extend** existing `GET /api/v1/selection/enrichment`; optional `GET /api/v1/selection/s5-enrichment`; POST 405. Do not break `GET /api/v1/selection/top10` |
| Frontend | `D:\TrendForge\frontend\s5-enrichment.js` **or** extend `frontend/top10-research.js` |
| Shell | `D:\TrendForge\frontend\index.html` — keep `#top10ResearchPanel` (R6 stickers). Paint UNKNOWN chips on `section#all-stocks` `#allStockContent` |
| Adapter | `D:\TrendForge\frontend\selection-live-adapter.js` — if you add a fetch, extend the existing Promise.all **and** the name list (do not leave a 7th fetch with 6 names) |
| OI rooms | `D:\TrendForge\frontend\app.js` `TOOL_REGISTRY` `oi_analysis` / `oi_tracker` — may **read** FO package; still CONTEXT, not CONFIRMED. Do not invent GEX |
| Styles + accept | `frontend/styles.css`, `frontend/tests/acceptance-check.js` |

`build_s5_enrichment(shortlist)` reads S4/R5 + R6 recipes + options stub.

Reuse (do not copy-paste parsers): `r6_live._load_delivery_map`, radar `delivery_fact` / `fo_package_fact` / `amfi_fact` / `named_deal_fact` / `shp_context_fact`.

**Do not** create a second All Stocks page. **Do not** fill `entry/t1/t2` as trades. **Do not** overwrite `#flow` (File A S5 there is not this enrichment).

Ceiling: `LIVE_S5_ENRICH_WAIT_ONLY`.

**Scratch / delete**

- Scratch → `D:\TrendForge\delete\s5_enrich_wip_<YYYY-MM-DD>\`
- No `tmp_*.py` in repo root
- Do not dual-start the collector to “get MTO/FO”

---

## 6. Forbidden

- Bare R2 WATCH-40 as S5 input (bypasses the S4 direction owner)
- All-universe option chains or all-universe MTO z  
- Delivery on INTRADAY  
- Volume added again on R2  
- `nse_fii_dii` per stock  
- GEX as observed dealer book (`REJ-007`)  
- Static PCR as direction (`REJ-006`)  
- CFTC confirming MCX  
- CONFIRMED / qty / `sourceActivationReady`  
- Dual-start collector  
- Hybrid `p̂` as enrichment strength  

---

## 7. Tests

| ID | Assert |
|---|---|
| T1 | Enrichment row count ≤ shortlist; not 2463 unless shortlist is 2463 |
| T2 | `nse_fii_dii` cannot set per-symbol fiiBought |
| T3 | Unnamed deal ≠ FII |
| T4 | Delivery absent from any INTRADAY-tagged row |
| T5 | Missing chain → UNKNOWN_NEEDS_R12; cash-only not punished |
| T6 | `shpFiiDelta is None`; AMFI labelled delayed |
| T7 | FO missing ≠ score penalty |
| T8 | `canUnlockConfirmed=false`; R6/R5 hashes unchanged if read-only |
| T9 | POST 405 |
| T10 | `test_r6_live.py` + `test_top10_research.py` still pass |
| T11 | Row with no S4 structure claim (`CG_PRICE_STRUCTURE`/`CG_COMPRESSION` empty) ⇒ excluded from enrichment |

```
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s5_shortlist_enrichment.py tests/test_r6_live.py tests/test_top10_research.py tests/test_r5_live_structure.py tests/test_s2_market_weather.py -q
cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Scratch → `delete/s5_enrich_wip_<date>/`.

---

## 8. Docs (after observed tests — short patches)

| File | Patch |
|---|---|
| `D:\TrendForge\fileindex.md` | S5 files + enrichment route; top10 still stickers |
| `D:\TrendForge\docs\BUILD_STATUS.md` | S5 WAIT enrich observed; options UNKNOWN_NEEDS_R12 unless proven |
| `D:\TrendForge\docs\DECISIONS.md` | **D-048**: S5 = SEL-006 shortlist only; Options Detail Plan package not R12 complete; not CONFIRMED |
| `D:\TrendForge\docs\VALIDATION.md` | pytest + 405 + acceptance |
| `D:\TrendForge\docs\fable\remaining_build\README.md` | Status row |
| `D:\TrendForge\docs\ARCHITECTURE.md` | Enrichment consumes R6; does not replace R2 |

Do **not** mark R12, S6/S7, or File A first CONFIRMED done.

---

## 9. Stop

Success: a WATCH name shows **delivery / FO / event / options UNKNOWN** honestly, still **0 CONFIRMED**. Expensive work did not run on the whole NSE.
