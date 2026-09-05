# OPENCODE BUILD PROMPT — File A S4 closed-bar structure pack
## Breakout / acceptance / NR / trend — WAIT only, not CONFIRMED, not Hybrid p̂

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. Shell: PowerShell. Chain with `;` not `&&`.

Copy this **entire file**. Think first.

**S1 cash safety, S2 weather, and S3 cheap discovery are upstream.**  
This ticket is **S4 only** = File A `SEL-005`.

Do **not** rebuild S1–S3, R1–R4, R14, R6, S2 weather, or the evidence radar.  
Do **not** set `sourceActivationReady=true`. Do **not** emit CONFIRMED or qty. Do **not** dual-start the collector.  
Do **not** paste Hybrid V2/V3 S4/S5 (`p̂`, Kelly, B1–B5) into `r5_live.py`.

Do **not** open `docs/OPTIONS_INTELLIGENCE_PLAN.md` for this ticket. Options start at **S5**.

---

## 0. Outcome (done means this was **observed**)

1. `GET /api/v1/selection/structure` (or a sibling `…/s4-structure`) returns a **closed-bar structure pack** for the **S3 WATCH/WAIT shortlist** (not a fresh 2,463-name expensive loop if S3 exists; if S3 API is missing, consume latest A3+R2 WATCH as the cheap queue — do not scan all bars for every REJECT).
2. Each row has: closed-bar **setup tags**, **nextTrigger**, **invalidationCondition**, adjusted-series lineage (`r14RunHash`), `researchState=WAIT`, **0 CONFIRMED**.
3. WAIT_CA / REJECT / ban never get a breakout claim. Unclosed bars never confirm.
4. Structure inspector / All Stocks shows tags + next trigger. `entry/t1/t2` stay **not a trade**.
5. Existing `tests/test_r5_live_structure.py` still pass. R5 hash-match to R14 still required.

---

## 1. What S4 is (File A §9 wins)

| Stage | ID | Work | Ceiling |
|---|---|---|---|
| **S4** | `SEL-005` | Minimal closed-bar structure pack: breakout/acceptance, NR/compression, trend, optional pattern lane | Structure claims + next trigger. **WAIT** until S7+R2-B |

File A §25.25.6 uses **different** S# labels (there S5 = history/structure). **Ignore that numbering.** Authority is §9 `SEL-005`.

| This ticket IS | This ticket is NOT |
|---|---|
| Closed adjusted OHLCV claims (`FTR-005/006/007`, optional pattern `FTR-011` as WATCH) | Hybrid overlay S4 `p̂` |
| Next trigger + invalidation **labels** | Live entry/T1/T2 as orders |
| Shortlist structure (S3 survivors) | Full-universe VCP/harmonic storm |
| R5 WAIT tags completed into a pack DTO | File A first CONFIRMED |

**Already live — READ:** `selection/r5_live.py` `LIVE_WAIT_REJECT_ONLY`, `GET /api/v1/selection/structure`, IST clock, R14 CA authority, `detected_setups`, `confirmedCount=0`.  
S4 **extends/consumes R5**. Do not rewrite the R5 ceiling validators.

---

## 2. Authority

| Rank | File | Use |
|---|---|---|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` | §9 S4; `FTR-005` trend acceptance; `FTR-006` breakout; `FTR-007` NR; `FTR-011` pattern max WATCH; §11 `CG_PRICE_STRUCTURE` / `CG_COMPRESSION`; no qty |
| 2 | `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md` | R5 is WAIT; R14 is CA authority; workbench is glass |
| 3 | `docs/fable/FINAL_MERGE_PLAN.md` | Paint All Stocks / structure panel, not workbench |
| 4 | `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` | Formula detail only |

R5 already tags breakout / NR / RVOL-like facts. **Fill gaps:** next trigger, invalidation, trend-acceptance claim, compression one-group cap, pattern lane **cannot vote**.

---

## 3. Already live — do not rewrite

```
selection/r5_live.py              WAIT structure tags; forbids CONFIRMED
selection/r14_live.py             CA join; WAIT_CA drops claims
selection/series_layers.py        adjusted series; never mutate RAW
selection/structure.py            ClosedBar / StructureMetrics / analyze_closed_bar_structure
selection/s2_market_weather.py    context; not a structure vote
selection/s3_cheap_discovery.py   if present after S3 ticket; else A3+R2 WATCH
GET /api/v1/selection/structure
```

---

## 4. Structure recipes (closed bars only)

All prices from **adjusted** series after R14. IST session. Unclosed → no claim.

| Claim | Formula / rule | Group | Ceiling |
|---|---|---|---|
| Breakout/breakdown `FTR-006` | Close crosses versioned prior N-bar high/low by tick tolerance; acceptance = close holds N bars | `CG_PRICE_STRUCTURE` | Forming WATCH; test WAIT; **no CONFIRMED** |
| Trend acceptance `FTR-005` | Close above/below level for configured closed bars; record bar_id | `CG_PRICE_STRUCTURE` | Same root as breakout — **one** representative |
| NR4/NR7 `FTR-007` | Current true range lowest of prior N completed periods | `CG_COMPRESSION` | Compression alone max WATCH |
| Optional pattern `FTR-011` | Existing harmonic/pattern modules if pivots valid | `CG_PATTERN_STRUCTURE` | Pattern-only **never** supports CONFIRMED; display lane |
| RVOL-EOD | Volume / PIT median ≥20 sessions (participation companion, not a second structure vote) | `CG_ACTIVITY_SESSION` | Do not add on top of R2 volume |

Same bars cannot emit breakout **and** new-high as two votes (`CG_PRICE_STRUCTURE`).

**Next trigger / invalidation** (required on every WATCH/WAIT structure row):

```text
nextTrigger          e.g. "WAIT close hold above prior high on next completed bar"
invalidationCondition e.g. "close back inside prior range on adjusted series"
```

Never fill `entry/t1/t2` as executable geometry. If R5 already has `NONE — R5 research, not a trade`, keep that.

WAIT_CA → no structure claim; `UNKNOWN_GAP_WAIT_CA` / drop `claim_ids` (already R5).

---

## 5. What to build (paths — reuse the designed shell)

Prefer **extend R5 DTO** over a second structure engine. Validators on `r5_live.py` stay locked (`source_activation_ready` / `can_unlock_confirmed` false).

**Create / touch**

| Role | Path |
|---|---|
| New pack (preferred) | `D:\TrendForge\backend\trendforge_api\selection\s4_structure_pack.py` |
| Tests | `D:\TrendForge\backend\tests\test_s4_structure_pack.py` |
| Route | `D:\TrendForge\backend\trendforge_api\main.py` — keep `GET /api/v1/selection/structure`; optional sibling `GET /api/v1/selection/s4-structure`; POST 405 |
| Frontend paint | `D:\TrendForge\frontend\s4-structure.js` |
| Shell mount | `D:\TrendForge\frontend\index.html` — existing `section#structure` `#structureContent` `#structureSymbols` |
| Live adapter | `D:\TrendForge\frontend\selection-live-adapter.js` — already fetches structure; **extend**, do not add a 2nd app |
| All Stocks | `D:\TrendForge\frontend\product-fixture.js` `applyLiveSelection` — tags + nextTrigger only; geometry stays `NONE — R5 research, not a trade` |
| Styles | `D:\TrendForge\frontend\styles.css` |
| Acceptance | `D:\TrendForge\frontend\tests\acceptance-check.js` |

**Do not create** a new nav item, a second S0–S9 strip, or overwrite `#flow`. On `#flow`, File A label **S4 = PK shadow** — that is **not** this ticket. Hybrid `#s4s5ComparePanel` is overlay `p̂` — **do not paint File A S4 there**.

Input: latest R5 hash-matched to R14 + S3 watch if `GET /api/v1/selection/cheap-discovery` exists (`#s3WatchQueue` already live).

Ceiling: `LIVE_S4_WAIT_REJECT_ONLY`. `confirmedCount=0`.

**Scratch / delete**

- Failed dumps, tmp parsers, scratch notebooks → `D:\TrendForge\delete\s4_structure_wip_<YYYY-MM-DD>\`
- **No** `tmp_*.py` in repo root or `backend/`
- Do not dual-start the collector to “get bars”

---

## 6. Forbidden

- CONFIRMED, qty, broker, live T1/T2 as orders  
- Hybrid `p̂` / Kelly / S4/S5-compare formulas inside R5  
- Unclosed bar claims  
- Delivery, options chain, AMFI as structure  
- Index % as a breakout vote (S2 is context)  
- PK/workbench scanners as structure votes  
- Rebuild R14 CA join  
- Dual-start collector  

---

## 7. Tests

| ID | Assert |
|---|---|
| T1 | Unclosed / missing bars → no BREAKOUT claim |
| T2 | WAIT_CA → no claim_ids / no CONFIRMED |
| T3 | Breakout + new high from same bars → one `CG_PRICE_STRUCTURE` representative |
| T4 | NR7 alone cannot set researchState CONFIRMED |
| T5 | Pattern lane `can_support_confirmed=false` |
| T6 | nextTrigger and invalidationCondition non-empty (UNKNOWN codes allowed) |
| T7 | R2 `runHash` unchanged; R14 hash required or 503 |
| T8 | `confirmedCount=0`; POST 405 |
| T9 | `tests/test_r5_live_structure.py` still passes |

```
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s4_structure_pack.py tests/test_r5_live_structure.py tests/test_r14_live_ca_join.py tests/test_s2_market_weather.py -q
cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Scratch → `delete/s4_structure_wip_<date>/`.

---

## 8. Docs (after observed tests — short patches)

| File | Patch |
|---|---|
| `D:\TrendForge\fileindex.md` | New S4 files + route + `#structureContent` |
| `D:\TrendForge\docs\BUILD_STATUS.md` | S4 WAIT pack observed; not CONFIRMED |
| `D:\TrendForge\docs\DECISIONS.md` | **D-047**: S4 = SEL-005 on live R5; not Hybrid S4 `p̂`; not CONFIRMED |
| `D:\TrendForge\docs\VALIDATION.md` | pytest + acceptance counts |
| `D:\TrendForge\docs\fable\remaining_build\README.md` | Status row: S4 coded at WAIT ceiling |
| `D:\TrendForge\docs\ARCHITECTURE.md` | One line: structure pack consumes R5/R14 |

Do **not** mark S5/S6/S7, R2-B unlock, or File A first CONFIRMED done.

---

## 9. Stop

Success: shortlist names show **why the chart is WAIT** (tag + next bar + invalidation), still **0 CONFIRMED**.
