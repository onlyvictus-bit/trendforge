# OPEN-MODEL BUILD PROMPT — Hybrid V2 remaining code (research overlay only)

Copy this **entire file** into the other model. Attach also:

1. `C:\Users\sakth\Downloads\TRENDFORGE_HYBRID_V3.md` (verbatim V2 + original V3 + binding S4/S5 amendment)
2. `D:\TrendForge\delete\plans_archived_2026-08-19\TRENDFORGE_HYBRID_V2.md` (V2-only copy)

**Frontend / design — READ these before any UI change (absolute paths):**

3. `D:\TrendForge\frontend\index.html` — shell, nav, `#flow` File A S0–S9, `#s4s5ComparePanel`, All Stocks, tools, SE, OL, paper
4. `D:\TrendForge\frontend\app.js` — `TOOL_REGISTRY` (14 tools), `renderToolRoom()` WAIT_DTO rooms
5. `D:\TrendForge\frontend\product-fixture.js` — `applyLiveSelection`, All Stocks / radar / `#scenario` geometry
6. `D:\TrendForge\frontend\selection-live-adapter.js` — live GET attention/evidence/structure/identity-pin
7. `D:\TrendForge\frontend\s4s5-compare.js` — WITH/WITHOUT/BOTH; GET `/api/v1/selection/s4s5-compare`
8. `D:\TrendForge\frontend\q5-contract.js` — public WATCH/WAIT/REJECT; not overlay `p̂`
9. `D:\TrendForge\frontend\styles.css` — `.s4s5-*` and shell layout
10. `D:\TrendForge\frontend\theme-final.css` — FINAL_PRODUCT theme
11. `D:\TrendForge\frontend\tests\acceptance-check.js` — must stay green; add overlay ID checks
12. `D:\TrendForge\docs\TRENDFORGE_FINAL_PRODUCT.html` — original product-direction fixture (same S0–S9 File A labels as `#flow`)

Do **not** invent V2 formulas. If a number is not in those files or in live TrendForge code cited below, the field is `UNKNOWN` / `WAIT`, never guessed.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. Shell: PowerShell. Chain commands with `;` not `&&`.

---

## 0. Success definition (all must be true)

You are **not** building File A. You are **not** finishing R2-B. You are **not** unlocking CONFIRMED.

You are building the **remaining Hybrid V2 trading-OS overlay** as a **paper research package** that:

1. Reads the live File A spine **read-only** (R1, R2-A, R3, R4, R14, R5).
2. Computes V2 S0–S9 / B1–B5 **proxies** with explicit `RESEARCH_PROXY_NOT_CALIBRATED`.
3. Implements **V2 Phase 2 first**: AS (delivery accumulation) + triple-barrier labels + cost-aware `p_min` / Kelly **illustration**.
4. Stubs every other V2 module so it cannot vote until its own IC admits it.
5. Keeps **both** S4/S5 families (already live). Do not delete either.
6. Lives in a **new folder tree**. Does not rewrite `r5_live.py`, `r14_live.py`, `r4_live.py`, `attention_order.py`, `cash_post_commit.py`.
7. After build: move scratch / failed experiments / unused dumps into `D:\TrendForge\delete\hybrid_v2_wip_<YYYY-MM-DD>\`.
8. **Paint the existing FINAL_PRODUCT rooms** listed in §0.1. Do **not** invent a second nav, a second S0–S9 strip, or a lone overlay page that the user cannot open from the current shell.

If the overlay can change R2 `public_state`, emit CONFIRMED, set qty, or write into R5, the build has failed.

---

## 0.1 UI wiring — verified against live `frontend/index.html` (do not assume)

**Verified 2026-08-21 by reading the real DOM and JS. The previous overlay sketch that only added `#s4s5ComparePanel`-style extra chrome is incomplete.** The shell already has Hybrid V2 **module names** in the nav and File A **S0–S9** on Decision Flow. Those two “S0–S9” are **not the same language**. Mixing them is a hallucination.

### Two different S0–S9 (must keep both labels; do not rename)

| Where | IDs | Meaning | Hybrid V3 Part 3? |
|---|---|---|---|
| Nav **DF** `section#flow` | static `.pipeline .step` S0…S9 | **File A** cheap-discovery → PK shadow → structure → options package → resolution → paper | **No.** File A S4 here = PK shadow, not log-odds `p̂` |
| V3 Part 3 chain | not a dedicated view yet | Integrity → Safety → Market → Discovery → **p̂** → Levels → Vehicle → Risk → Fills → Attribution | **Yes.** Must be a **labelled research strip**, not a rewrite of `#flow` |

Do **not** overwrite `#flow` step text. Add a sibling research strip, e.g. `#hybridV2Chain` **inside** `section#flow` (or Live Ops), titled `Hybrid V2/V3 S0–S9 (paper overlay — not File A)`. File A DF stays File A.

### V2 21 modules already have nav buttons (this is the designed UI)

`frontend/index.html` nav + `frontend/app.js` `TOOL_REGISTRY` (14 tools) + extra views:

| V2 module | UI to paint | Current live behavior | Overlay must do |
|---|---|---|---|
| **AL** All Stocks | `section#all-stocks` `#allStockContent` `#allStockSummary` | `product-fixture.js` `applyLiveSelection` from R1/R2/R5; geometry = `NONE — R5 research, not a trade` | Keep R2 state. Overlay may add **label-only** columns: `pHatWithout`, `pHatWith`, `asStatus`, `s6Status`. Never fill `entry/t1/t2` as live orders |
| **M** | `button[data-tool="m_factor"]` `#toolContent` | `WAIT_SOURCE_ACTIVATION` empty room | Optional B3/M display DTO; still WAIT; no win-probability title |
| **SC** | `data-tool="sector_scope"` | `WAIT_DTO_UNAVAILABLE` | B2 z if official sector last-good else keep WAIT |
| **MH** | `data-tool="m_factor_history"` | `PIT_HISTORY_NOT_WIRED` | leave unless you persist overlay vintages |
| **HM** | `data-tool="heatmap"` | shadow | no invented heat |
| **IX** | `data-tool="index_dashboard"` | WAIT_DTO | B1 if A5 index exists else WAIT |
| **OI / OT** | `oi_analysis` / `oi_tracker` | WAIT_CHAIN / shadow | B4 **package only**; numeric z UNKNOWN_NEEDS_R12 |
| **ST / EX** | `strike_explorer` / `expiry_prediction` | WAIT_CHAIN | stay UNKNOWN_NEEDS_R12 |
| **SF** | `swing_finder` | WAIT_DTO | pass-through R2 shortlist only |
| **SL** | `section#structure` `#structureContent` | fixture Elliott/harmonic | Tier-3 display; never vote; do not replace R5 WAIT |
| **SM** | `speculation_movers` | shadow | veto-only flag, not a point |
| **TA** | `trend_accumulation` | WAIT_SOURCE_ACTIVATION | combine R5 tags + AS if usable |
| **AS** | `accumulation_signals` **`#toolContent` when tool=accumulation_signals** | `WAIT_DTO_UNAVAILABLE` | **Phase-2 primary paint:** delivery z / UNKNOWN |
| **MR** | `multibagger_research` | separate book | do not share F&O p̂ |
| **RR** | `section#radar` `#radarRows` `#summary` | fixture + live adapter | keep WATCH/WAIT/REJECT; no CONFIRMED |
| **SE** | `section#stock` `#stockTitle` `#scenario` `#tabContent` | scenario entry/stop/t1/t2 from fixture or “NOT AVAILABLE UNTIL R5” | Hybrid S5 labels only if R width exists; else PENDING/UNKNOWN |
| **OL** | `section#options` `#optionLab` | PARTIAL FIXTURE | S6 UNKNOWN_NEEDS_R12 |
| **PL** | `section#paper` | FMR-011 NOT BUILT | triple-barrier schema only; “NOT BUILT” stays until labels persist |
| **SH** | `section#sources` `#sourceHealthLadder` | compiler ladder | do not treat GREEN as activation |
| **LO** Live Ops | `#liveDecisionPanel` `#s4s5ComparePanel` | R1 list + S4/S5 A/B | **keep S4/S5 checkboxes**; overlay GET is extra, not a replacement |
| **Q5 band** | `#q5SelectionState` `#q5RadarAnswers` | “Evidence strength - not win probability” | do **not** write overlay `p̂` into Q5 as if it were File A state |

`frontend/app.js` `renderToolRoom()` currently always paints `WAIT_DTO_*` and **refuses invented OI/IV/GEX**. That is correct. Overlay wiring = supply a **named DTO** per tool and a small renderer; if DTO missing, keep the wait copy.

### Live adapter already wired (extend, don’t fork)

`frontend/selection-live-adapter.js` fetches:

- `GET /api/v1/selection/attention`
- `GET /api/v1/selection/evidence`
- `GET /api/v1/selection/structure` (503 → null)
- `GET /api/v1/selection/identity-pin` (503 → null)

Then `product-fixture.js` `applyLiveSelection(...)`.

**Required UI wire:** also `fetchOptionalJson("/api/v1/hybrid-v2/overlay?limit=40")` (503 → null). Pass overlay map by symbol into a **new** `applyHybridOverlay(overlay)` that only fills Hybrid fields. If 503, rooms stay WAIT_DTO. Never fall back to fixture geometry as if it were overlay.

Also fetch `GET /api/v1/selection/ca-join` optional so SE/AS can show `r14.caState` (WAIT_CA hides fake delivery z).

Event `trendforge:selection-ready` already reloads S4/S5. Overlay JS must listen to the same event.

### IDs you may add (minimal)

Only if a mount is missing for Hybrid S0–S9 paper chain and AS numbers:

- `section#flow` → `#hybridV2Chain` (10 cells: Hybrid S0…S9 statuses for **selected** symbol)
- `#toolContent` wait box already exists — replace innerHTML only when `appState.activeTool` has overlay DTO
- Live Ops: optional `#hybridV2OverlayPanel` **under** `#s4s5ComparePanel`, not instead of it

Do **not** create `frontend/hybrid_v2/` as a separate HTML app. One shell: `frontend/index.html`.

### Field → pixel map (this is the contract)

| Overlay JSON (camelCase) | Where the user must see it |
|---|---|
| `asStatus`, `asDeliveryZ` | tool **AS** `#toolContent`; optional All Stocks extra tag |
| `withS4S5.pHat`, `withoutS4S5.pHat`, `pHatInflation` | **existing** `#s4s5CompareList` (already GET `/s4s5-compare`) — overlay must **match** those numbers, not draw a third p̂ |
| `b4Package` | OI/OT rooms + All Stocks tag; **not** mixed into WITHOUT p̂ |
| `s5` T1/T2 labels | `#scenario` / All Stocks geometry **only if** `entryLevel` and range width exist; else keep `PENDING` / `NONE — R5 research, not a trade` |
| `s6VehicleStatus=UNKNOWN_NEEDS_R12` | OL `#optionLab` + EX/ST wait chip |
| `kellyIllustration` | S4/S5 cards already show this; do not add a size input |
| `researchState` | must stay WATCH/WAIT/REJECT chips already on the board |
| `whyWait` | radar `#summary` “Next proof” / All Stocks reason |

### Explicit non-wires

- `#decisionTitle` / `#q5SelectionState` stay File A/Q5 WAIT — overlay `p̂` is **not** public state
- `#flow` File A S4 “PK shadow” ≠ Hybrid S4 `p̂`
- Fixture `product-fixture.js` `stocks.TATASTEEL.scenario.entry` must not be shown as overlay live levels
- `TOOL_REGISTRY` 14 keys must remain; do not add a 15th invented nav key for “hybrid”

---

## 1. Authority (later files do not override earlier)

| Rank | File | Role |
|---|---|---|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` | File A. Sole live selection spine. |
| 2 | `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md` §12.4 / §13 | Live how-to. R2-B closed. Next File A code = R6. |
| 3 | Live code listed in §3 | Clone persistence/API style. Do not replace. |
| 4 | Hybrid V3 merge file (V2 verbatim + binding amendment) | Overlay math. Binding amendment **wins** over V2 Part E S4/S5 mix. |
| 5 | This prompt | What to code now. |

Inventory Workbench, catalog cards, Consensus v4, `/api/radar`, Q5 fixtures, yfinance as trigger: **forbidden inputs**.

---

## 2. What is already live (do not rebuild, do not “fix”)

| Stage | Path | Ceiling |
|---|---|---|
| Collector 123 jobs | `config/source_refresh_registry_69.csv` | no 124th job |
| A1–C1 cash | `selection/cash_a1_staging.py` … `cash_c1_rank.py` | WATCH attention only |
| R1 | `selection/inventory_source_bundle.py` `GET /api/v1/selection/evidence` | research DTO |
| R2-A | `selection/attention_order.py` `GET /api/v1/selection/attention` | BASELINE list; **not** R2-B |
| R3 | `selection/r3_live.py` `GET /api/v1/selection/resolution` | WAIT FTR-040 |
| R4 | `selection/r4_live.py` `GET /api/v1/selection/identity-pin` | ID pin, PK zero vote |
| R14 | `selection/r14_live.py` `GET /api/v1/selection/ca-join` | CA join WAIT-only; DAT-022 reuse |
| R5 | `selection/r5_live.py` `GET /api/v1/selection/structure` | setup tags; `confirmedCount=0`; **consumes R14** |
| Pipeline | `selection/cash_post_commit.py` | `A1…R3,R4,R14,R5` version `a1-c1-r1-r2-r3-r4-r14-r5-orchestrator-7` |
| S4/S5 A/B | `selection/s4s5_compare.py` `GET /api/v1/selection/s4s5-compare` `frontend/s4s5-compare.js` | WITH / WITHOUT / BOTH; user has **not** picked |
| CA formulas | `corporate_actions.py` | reuse; do not rewrite |
| Scheduler | `market_data_scheduler.py` | IST; do not dual-start |

**Still closed (do not flip):**

- `sourceActivationReady=false`
- `gateAuthorized=0`
- R2-B named activation
- live CONFIRMED, qty, broker
- File A R6–R13, R15
- Hybrid S4/S5 family pick

R2-A ≠ R2-B. The attendance list exists. The “this source may confirm” signature does not. Overlay must keep `sourceActivationReady=false`.

---

## 3. Files you must read before writing code

**Spine (backend):**

```
D:\TrendForge\backend\trendforge_api\selection\s4s5_compare.py
D:\TrendForge\backend\trendforge_api\selection\r14_live.py
D:\TrendForge\backend\trendforge_api\selection\r5_live.py
D:\TrendForge\backend\trendforge_api\selection\r4_live.py
D:\TrendForge\backend\trendforge_api\selection\attention_order.py
D:\TrendForge\backend\trendforge_api\selection\inventory_source_bundle.py
D:\TrendForge\backend\trendforge_api\selection\cash_post_commit.py
D:\TrendForge\backend\trendforge_api\selection\store.py
D:\TrendForge\backend\trendforge_api\corporate_actions.py
D:\TrendForge\backend\trendforge_api\main.py
D:\TrendForge\backend\tests\test_s4s5_compare.py
D:\TrendForge\backend\tests\test_r14_live_ca_join.py
```

**Frontend / design (READ, then extend — do not replace the shell):**

```
D:\TrendForge\frontend\index.html
D:\TrendForge\frontend\app.js
D:\TrendForge\frontend\product-fixture.js
D:\TrendForge\frontend\selection-live-adapter.js
D:\TrendForge\frontend\s4s5-compare.js
D:\TrendForge\frontend\q5-contract.js
D:\TrendForge\frontend\styles.css
D:\TrendForge\frontend\theme-final.css
D:\TrendForge\frontend\tests\acceptance-check.js
D:\TrendForge\docs\TRENDFORGE_FINAL_PRODUCT.html
```

Open `index.html` and `app.js` first. Nav IDs and `TOOL_REGISTRY` are the designed Hybrid module rooms. `#flow` S0–S9 is File A, not V3.

Clone: frozen pydantic + `alias_generator=to_camel` + `populate_by_name=True` + validators that **raise** on CONFIRMED / executable / can_unlock_confirmed. Persist with `persist_selection_payload`. GET hash-scoped; mismatch 503; POST 405.

Pydantic `to_camel("with_s4s5")` → `withS4S5`. Name fields so aliases are obvious.

---

## 4. Folder structure (create this; do not dump files in `selection/`)

Hybrid overlay is a **sibling package**, not a File A R-step.

```
backend/trendforge_api/hybrid_v2/
  __init__.py                 # package; export SCHEMA_VERSION only
  README.md                   # 20-line overlay ceiling (not a new roadmap)
  contracts.py                # shared DTOs, ceiling constants, UNKNOWN policy
  spine_adapter.py            # READ-ONLY load of latest R1/R2/R4/R14/R5; lineage check
  pipeline.py                 # build_hybrid_v2_overlay()
  persist.py                  # persist / latest
  blocks/
    __init__.py
    b1_regime.py              # stub unless official index+VIX last-good exists
    b2_sector.py              # stub unless official sector last-good exists
    b3_cash.py                # PHASE-2 REAL: AS delivery if nse_mto_delivery usable
    b4_positioning.py         # STUB: UNKNOWN until File A R12; package-only like WITHOUT S4
    b5_location.py            # from R5 tags / metrics only; never votes on p̂
  stages/
    __init__.py
    s0_integrity.py           # lineage + freshness flags; WAIT_STALE
    s1_safety.py              # copy R2 restriction / ban as veto; do not invent ASM
    s2_environment.py         # uses B1/B2 if present else SKIP
    s3_discovery.py           # pass-through of R2 display_order shortlist (limit)
    s4_probability.py         # BOTH families: WITH mix vs WITHOUT split (call existing s4s5 or share helpers)
    s5_levels.py              # labels only; T1/T2 need prior_range width — if missing, label not fake %
    s6_vehicle.py             # STUB: VRP/gamma UNKNOWN (needs R12 + 5-min RV)
    s7_size.py                # Kelly ILLUSTRATION only, cap 0.02, not qty
    s8_fills.py               # next-day VWAP / mid±½spread RULE TEXT + flags, not broker
    s9_attribution.py         # schema for MFE/MAE later; empty until labels exist
  as_lab/
    __init__.py
    delivery.py               # official MTO last-good → z; else UNKNOWN
    triple_barrier.py         # label spec only + fixture tests; no live CONFIRMED
    costs.py                  # c,b,q from config with effective dates; default ILLUSTRATION_*
  scorecard/
    __init__.py
    ic.py                     # IC table: most modules IC=None → cannot contribute β
  tests_support/
    fixtures.py               # shared overlay fixtures; not production

backend/tests/hybrid_v2/
  test_ceiling.py
  test_spine_adapter.py
  test_as_delivery.py
  test_triple_barrier.py
  test_s4_both_families.py
  test_s6_vehicle_stub.py
  test_api_overlay.py
  test_no_file_a_mutation.py

frontend/  (same shell — do not create a second HTML app)
  hybrid-v2-overlay.js        # paints §0.1 IDs; listen to trendforge:selection-ready
  index.html                  # add #hybridV2Chain only; keep #s4s5ComparePanel
  selection-live-adapter.js   # also GET overlay + ca-join, 503 = null
  app.js                      # renderToolRoom(accumulation_signals) consumes overlay DTO

delete/hybrid_v2_wip_<date>/  # AFTER tests: move scratch here (see §12)
```

Do **not** create `selection/r2b_*.py`, `selection/hybrid_s4_live.py`, or a second `cash_post_commit`.

---

## 5. Purpose of each new unit (no extras)

| Unit | Purpose | May vote on overlay `p̂`? | Live CONFIRMED? |
|---|---|---|---|
| `spine_adapter` | Load hash-matched R1/R2/R4/R14/R5 | no | no |
| `b3_cash` / AS | Delivery z, accumulation-day count from official MTO if usable | yes, overlay only | no |
| `b1`,`b2` | Regime/sector z when official last-good exists | only if fields present; else UNKNOWN | no |
| `b4_positioning` | `SUPPORT/WEAKEN/CONFLICT/UNKNOWN` package | **no** (adopted split) | no |
| `b5_location` | entry label / distance if R5 metrics exist | **no** | no |
| `s4_probability` | WITH and WITHOUT `p̂` side by side | overlay display | no |
| `s5_levels` | T1=`entry+0.382R`, T2=`entry+0.618R` if R width known | no | no |
| `s6_vehicle` | VRP/gamma **UNKNOWN** until R12 | no | no |
| `s7_size` | Kelly illustration | no (not qty) | no |
| `as_lab.triple_barrier` | success label spec for future IC | no | no |
| `scorecard.ic` | admit/kill β | kill is default | no |

Reuse `selection/s4s5_compare.py` helpers if possible (`_sigmoid`, `_p_min`, `_kelly`, BIAS/SIDE_WEIGHT/BOOK_WEIGHT). Do not fork a third S4 formula. Do not replace the existing A/B API.

---

## 6. Data connections (real keys only)

Read last-good / selection payloads. **Do not fetch new unofficial sites. Do not add registry rows.**

| Need | Official key / API | If missing |
|---|---|---|
| Universe / state | latest R2 `GET /api/v1/selection/attention` | 503 `WAIT_HYBRID_R2_NOT_READY` |
| Identity | R4 pin + A2 `instrument_id` | UNKNOWN_ID rows skip AS |
| CA / adjusted bars | R14 join + R5 structure | WAIT_CA_* copy; no structure claims |
| Cash session | `nse_bhavcopy_eod` via R1 cheap_features / A4 raw bars | WAIT |
| Delivery AS | `nse_mto_delivery` last-good **if** parser_state structured and `data_date` matches research session | AS = UNKNOWN; do **not** use volume as delivery |
| Index companion | `nse_index_close_eod` A5 (not a 124th voter) | B1 WAIT, not invented Nifty |
| Ban / safety | existing A2 restriction / `nse_fno_ban` | S1 veto WAIT/REJECT copy of R2 |
| Option chain / VRP / GEX | File A R12 **not live** | S6/B4 numeric z = UNKNOWN |
| 5-min RV | V3 upgrade 30 recorder **not this ticket** | VRP stays UNKNOWN |
| yfinance | unofficial | never a trigger |

Lineage: overlay `r1_bundle_hash`, `r2_run_hash`, `r14_run_hash`, `r5_run_hash` must match current latest. Else 503, never last-good.

Research session date: use existing `exchange_calendar.expected_research_session_date` / IST phases. Do not use UTC as NSE session.

---

## 7. Overlay batch contract

**Schema:** `trendforge.hybrid-v2-overlay.v1`  
**Profile:** `PRF-HYBRID-V2-OVERLAY`  
**Ceiling:** `RESEARCH_PROXY_NOT_CALIBRATED`  
**`can_unlock_confirmed=false` `executable=false` `source_activation_ready=false`**

Row must include:

- `symbol`, `instrument_id` (from R4 or null), `r2_public_state`, `r5_structure_state`, `r14_ca_state`
- `research_state` = WAIT or copy of R2 REJECT — **never CONFIRMED**
- `b1_z`…`b5_z` as `float | None` (None = UNKNOWN)
- `with_s4s5` and `without_s4s5` (reuse S4S5FormulaResult shape)
- `s6_vehicle_status` = `UNKNOWN_NEEDS_R12`
- `kelly_illustration` ∈ [0, 0.02]
- `as_delivery_z`, `as_status` = `USABLE` \| `UNKNOWN` \| `STALE` \| `WAIT_CA`
- `why_wait` non-empty
- no `qty`, `entry`, `stop`, `target` as tradeable numbers unless labelled `LABEL_ONLY` and R width present

Batch warnings must include:  
`HYBRID_V2_OVERLAY_NOT_FILE_A. Not R2-B. Not CONFIRMED. Not size. S4/S5 both families kept.`

API:

```
GET /api/v1/hybrid-v2/overlay?limit=40
GET /api/v1/hybrid-v2/overlay/{symbol}
```

Hash mismatch → 503 `{code: WAIT_HYBRID_LINEAGE_MISMATCH}`. POST → 405.

Do **not** insert this into `cash_post_commit` stages. Overlay is computed on GET from latest spine (or persist on a dedicated profile after GET-build, like s4s5). Prefer **compute from latest spine on GET** (like `build_s4s5_compare`) to avoid a second orchestrator. If you persist, profile_id must not collide with R1–R14.

---

## 8. Formulas you may implement (copy, do not “improve”)

**Adopted S4 WITHOUT (default display family for “split”):**

```
logit = -0.4 + 1.2 * z_side
p̂ = σ(logit)
```

`z_side` from R2 `attention_priority` if WATCH, else 0.25 WAIT / 0 REJECT (same as `s4s5_compare._side_z`).

**S4 WITH (keep for A/B):**

```
logit = -0.4 + 1.2 * z_side + 1.2 * z_book
```

`z_book` from R5 setups/metrics as in `_book_z`. Do not add B4/B5 as extra β until user picks and File A amendment exists.

**p_min / Kelly illustration (already in s4s5_compare):**

```
b=1.2  q=0.5  c=0.08  SE=0.05
p_min = (1+c)/(1+b) = 1.08/2.2
p_used = max(0, p̂ − SE)
f = min(0.02, 0.25 * max(0, (p_used*b − q)/b))
```

These are **illustration**, not Indian live STT. A dated cost config may exist later; default to these constants. Do not hard-code 2024 STT as “truth.”

**T1/T2:** `entry + 0.382×R` and `entry + 0.618×R` where `R = prior_range` from R5 metrics if present. If width missing: keep the **label**, do not invent 3.82% of price.

**AS (Phase 2 only real module):**  
If official delivery% series length ≥ 20 closed sessions at `available_at ≤ decision_at`:

```
z_delivery = (x − median_20) / (1.4826 * MAD_20)   # robust; if MAD=0 → UNKNOWN
accumulation_days = count of last 20 sessions with delivery% > median_20 and session return quiet
```

“Quiet” must be defined in code as `|session_return| ≤ median_range` using A4 raw bars — if bars missing, accumulation_days = UNKNOWN.  
V2 G.2 example numbers (`z>2`, `≥5 of 20`) are **display thresholds**, not File A confirms.

**Triple-barrier label (lab only):**  
Success = `MFE ≥ +1.5 ATR before MAE ≤ −1.0 ATR` within 5 sessions, on **adjusted** series from R14/R5 rules. If R14 WAIT_CA, skip label. Fill assumption: next-day open (equity). Do not use signal-day close (V2 upgrade 19).

**VRP (must stub):**

```
VRP = IV²_ATM(T) − E[RV²(T)]
```

Without official chain + 5-min RV history this is UNKNOWN. Do not use IV Rank as VRP. Do not download Yahoo.

**Conflict precedence (display only):**  
Integrity > Safety > Margin/Liquidity > Regime > Positioning > Cash-flow > Sector > Geometry.  
Geometry never overrides WAIT_CA or S1 veto.

---

## 9. Implementation order (TDD)

0. `tests/hybrid_v2/test_ceiling.py` failing: overlay cannot CONFIRMED; cannot mutate R2/R5 hashes.
1. `contracts.py` + `spine_adapter.py` + lineage 503 tests.
2. `as_lab/delivery.py` + `test_as_delivery.py` (usable / missing / stale / WAIT_CA).
3. `triple_barrier.py` fixture tests (no live bars invention).
4. `s4_probability.py` must match `s4s5_compare` on the same R2/R5 fixture within 1e-6.
5. Stubs B4/S6 return UNKNOWN + why.
6. `pipeline.py` + GET routes in `main.py` (two new routes only).
7. Frontend: extend `selection-live-adapter.js` (optional overlay + ca-join GETs) and paint **existing** rooms in §0.1. Keep `#s4s5ComparePanel`. Add `#hybridV2Chain` inside `section#flow` without rewriting File A steps. `renderToolRoom('accumulation_signals')` must show AS DTO or keep `WAIT_DTO_UNAVAILABLE`.
8. Acceptance: existing S4/S5 checks stay; add checks for `#hybridV2Chain`, adapter overlay fetch, and AS tool still has no invented GEX.
9. Docs: short note in `fileindex.md`, `docs/BUILD_STATUS.md`, `docs/DECISIONS.md` (new D-040 overlay), `docs/ARCHITECTURE.md`. No third roadmap file.
10. Move scratch → `delete/hybrid_v2_wip_<date>/`.

Do **not** start V2 Phase 3 chain reconstruction, Phase 4 live S0–S9 wiring, Phase 6 SPRT live, or File A R6 in this ticket.

---

## 10. Test cases (must exist and pass)

| ID | Assert |
|---|---|
| C1 | Overlay batch `canUnlockConfirmed is False`, no CONFIRMED rows |
| C2 | POST overlay → 405 |
| C3 | R1/R2 hash mismatch → 503, no 200 last-good |
| C4 | R14 WAIT_CA → AS UNKNOWN and S5 no fake entry |
| C5 | Missing `nse_mto_delivery` → `as_status=UNKNOWN`, not volume proxy |
| C6 | WITH p̂ > WITHOUT p̂ when book_z>0 (same as s4s5) |
| C7 | WITHOUT omits book from logit |
| C8 | Kelly ≤ 0.02; p̂=0.1 → kelly 0 |
| C9 | S6 always `UNKNOWN_NEEDS_R12` in this milestone |
| C10 | B4 package never changes WITHOUT p̂ |
| C11 | T1 label without R width does not contain a fabricated price |
| C12 | Triple-barrier using signal-day close is rejected |
| C13 | Future CA (`available_at > decision_at`) does not enter AS z |
| C14 | Overlay run does not change `latest_attention_order().run_hash` or R5 `run_hash` |
| C15 | `source_activation_ready` stays false |
| C16 | Numeric scrip / UNKNOWN_ID never get AS z |
| C17 | Frontend still has `#s4s5With` `#s4s5Without` `#s4s5Both` |
| C18 | New overlay panel exists; does not use word READY as live state |

Run:

```
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/hybrid_v2 tests/test_s4s5_compare.py tests/test_r14_live_ca_join.py tests/test_r5_live_structure.py tests/test_r4_live_identity_pin.py tests/test_cash_post_commit_pipeline.py -q
```

Must stay green. Then `cd D:\TrendForge\frontend ; node tests/acceptance-check.js`.

Do not “fix” the known unrelated failures (`test_failed_15_source_repairs`, `test_market_data_service` stub kwargs, `test_vyom_source_resolution`) unless you already touch those signatures. Out of scope.

---

## 11. Failure-proof rules (hard fail)

- Guessing delivery, Nifty close, IV, VRP, pre_ex_close, ISIN, successor ticker
- `sourceActivationReady=true`
- `can_unlock_confirmed=True` or live CONFIRMED
- qty / broker / OpenAlgo orders
- Pasting S4–S9 into `r5_live.py`
- Deleting WITH or WITHOUT S4/S5
- Adding registry jobs / 124th voter
- Treating HTTP 200 or last-good as fresh
- UTC as NSE session
- Workbench as input
- yfinance as trigger
- Counting “5 of 9” confirmations (V2 B.1 forbids it)
- IV Rank as the premium buy/sell decision (V2 B.17: VRP is primary; stub if no VRP)
- Kelly as live size
- Silent last-good on hash mismatch
- Drive-by refactors of File A modules
- New top-level plan MD besides the listed doc patches
- Leaving `tmp_*.py`, notebooks, debug JSON in repo root or `backend/`

---

## 12. Delete-folder rule (required)

Allowed scratch **during** build: `D:\TrendForge\delete\hybrid_v2_wip_<YYYY-MM-DD>\`

When tests pass:

1. Move unused prototypes, one-off scripts, dumped JSON, failed modules into that folder.
2. Keep only the package tree in §4 plus tests plus the two GET routes plus the frontend panel.
3. Do not delete File A code, R14, S4/S5 A/B, or `delete/plans_archived_2026-08-19/`.
4. Do not use `delete/` as a dump for production overlay code.

---

## 13. Frontend example (what the user must see after wire)

**Live Ops** — existing S4/S5 panel (already works if API is up):

```
ALLCARGO · WATCH · BULLISH · inflation 0.138
WITH p̂ 0.827  WITHOUT p̂ 0.689  Kelly illustration 0.02 (not size)
```

**Decision Flow** — File A S0–S9 strip unchanged; **below it** Hybrid paper chain for the selected symbol:

```
Hybrid S0 WAIT_STALE? or OK · S1 copy of R2 restriction · S4 WITHOUT p̂ 0.689 / WITH 0.827
S5 T1/T2 LABEL_ONLY or WAIT_WIDTH · S6 UNKNOWN_NEEDS_R12 · S7 illustration 0.02 · S8 next-day VWAP rule
```

**Nav AS (Accumulation Signals)** — `#toolContent`:

```
WAIT_DTO_UNAVAILABLE           ← if nse_mto_delivery missing
or  ALLCARGO  asDeliveryZ 2.1  asStatus USABLE  ·  still not CONFIRMED
```

**All Stocks** — same WATCH/WAIT list as R2; extra tags optional; entry column stays `NONE — R5 research, not a trade` unless overlay has real range width (then LABEL_ONLY, not an order).

**OL / ST / EX** — still wait chain / UNKNOWN_NEEDS_R12. No fake GEX.

No CONFIRMED badge. No qty. No broker button. No second website.

---

## 14. Future-proof hooks (implement as closed doors, not features)

| Later | Hook now |
|---|---|
| User picks WITH vs WITHOUT | keep both; overlay reads `trendforge.s4s5.view` for display only |
| File A R6 enrichment | B3 may later read pledge/deals; today UNKNOWN if missing |
| File A R12 options | S6/B4 numeric z stay UNKNOWN until that join exists |
| R2-B | overlay still cannot confirm even if someone flips a flag in another PR |
| 5-min recorder (V3-30) | VRP function accepts RV series; default None |
| Cost schedule | `costs.py` reads dated config; default ILLUSTRATION_* |
| IC admission | `ic.py` returns None → β=0; never auto-admit |

---

## 15. Docs to patch (short, with file paths)

- `fileindex.md` — overlay folder + GET route + ceiling
- `docs/ARCHITECTURE.md` — one table row: Hybrid V2 overlay, not File A
- `docs/BUILD_STATUS.md` — 2026-08-21/22 overlay note
- `docs/DECISIONS.md` — D-040: overlay ≠ R2-B ≠ CONFIRMED
- `docs/VALIDATION.md` — pytest path `tests/hybrid_v2`
- `docs/fable/remaining_build/README.md` — row IMPLEMENTED at overlay ceiling

Do not mark File A R6 or R2-B done.

---

## 16. Done checklist

- [ ] Package exists only under `hybrid_v2/` as specified
- [ ] GET overlay 200/503 typed; POST 405
- [ ] AS never invented from volume
- [ ] S6 UNKNOWN_NEEDS_R12
- [ ] Both S4/S5 families remain
- [ ] R2/R5/R14 hashes unchanged by overlay tests
- [ ] `confirmedCount` still 0 on live R5 tests
- [ ] Frontend panel + acceptance checks
- [ ] Scratch in `delete/hybrid_v2_wip_*`
- [ ] Docs name the new paths

Stop. Do not start R6, R2-B, SPRT live, or chain reconstruction.
