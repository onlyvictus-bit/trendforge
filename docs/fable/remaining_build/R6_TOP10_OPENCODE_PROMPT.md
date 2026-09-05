# OPENCODE BUILD PROMPT — R6 shortlist stickers + top-10 BUY/SELL research board

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`

Copy this **entire file**. Do **not** rebuild R1–R5 or R14. Do **not** set `sourceActivationReady=true`. Do **not** emit CONFIRMED or qty.

**Think first.** If a source cannot name a stock, you must not print a stock-level “FII bought X” fact. That lie already happened in planning; your job is the **real** join.

---

## 0. Outcome (done means this was **observed**)

On All Stocks / a Live Ops strip:

- **10 BUY research names** and **10 SELL research names** (or fewer if not enough WATCH rows).
- Each row shows **why**, from **R1→R5 facts + R6 stickers**, with **UNKNOWN** when a layer is missing.
- Public state stays **WATCH / WAIT / REJECT**. **0 CONFIRMED. qty=0.**
- “FII bought this stock last week” appears **only** if an official **named** deal/shareholding row supports it. Daily `nse_fii_dii` is **market net**, never a ticker list.

---

## 1. Authority (File A wins)

| Rank | File | Use for this ticket |
|---|---|---|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` | R6 = shortlist enrichment only. SRC3-008/009/010/013. FUS-009: one EVENT_AND_SPONSOR family. Delayed AMFI/FII ≠ live flow. No qty. |
| 2 | `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md` | Do not rebuild live R1–R5/R14. Workbench is glass. Cheap R2 ≠ FII rank. |
| 3 | `docs/fable/FINAL_MERGE_PLAN.md` | Paint **All Stocks / radar**, not `/inventory-workbench`. FMR-002 flow. |
| 4 | `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` | Event-match / named deals (§19.8). AMFI lag. Do **not** use File B qty/OpenAlgo. |

Overlay V3 S4/S5/Kelly: **do not paste** into R6 or R5.

---

## 2. Already live — READ, do not rewrite

```
selection/inventory_source_bundle.py     R1
selection/attention_order.py             R2-A  (priority = 0.5*returnPct + 0.5*max(volumePct,turnoverPct))
selection/r3_live.py                     WAIT fuse
selection/r4_live.py                     instrument_id
selection/r14_live.py                    CA join
selection/r5_live.py                     WAIT tags, no live T1/T2 CONFIRMED
selection/fo_a6_enrichment.py            futures OI on WATCH only
selection/enrichment.py                  job enum (DELIVERY, CORPORATE_EVENTS, …)
fii_stock_signals.py                     DEAL_SOURCE_KEYS + SHAREHOLDING + third-party INFO pills
evidence_builder.py                      nse_large_deals, amfi_stock_deltas queries
```

R2 **does not** contain FII/MF. That is correct. R6 **adds stickers**. Do **not** put FII inside `_priority()`.

### Gap patches (repo-checked 2026-08-22) — do these first, before scoring

**Gap 2 — R2 field names (verified, map do not rename):**  
In `selection/attention_order.py` `AttentionRowV1`:

| Python | JSON (`to_camel` / `by_alias`) |
|---|---|
| `evidence_direction` | `evidenceDirection` (`BULLISH` / `BEARISH` / …) |
| `public_state` | `publicState` |
| `attention_priority` | `attentionPriority` |
| `attention_rank` | `attentionRank` |
| `display_order` | `displayOrder` |
| `symbol` | `symbol` |

Read the model or `model_dump(by_alias=True)`. **Do not rename** `evidence_direction` on the R2 class. Map into the top-10 DTO only.

**Gap 1 — SHP FII% + prior quarter is NOT a live parser:**  
`nse_shareholding_pattern` last-good exists as **raw/archive**. Current code (`intraday_stock_details._shareholding_evidence`, `disclosure_intelligence._shareholding_events`) only lifts **promoter %** (`pr_and_prgrp`) and **public %** (`public_val`) + a **date**. There is **no** normalized `fiiPct` vs **previous quarter**.

**This ticket’s default (required):** `shpFiiDelta = null` forever in R6/top10. Always add `whyUnknown` code `SHP_FII_DELTA_NOT_NORMALIZED`. **Do not** invent FII% from promoter/public. **Do not** treat SHP date as “last week.” Tag `SHP_QUARTER` **must not fire**.

**Optional stretch (only if you can prove it in a test on a real last-good JSON):** if a row already contains an explicit FII/FPI % field **and** a prior-quarter row for the same symbol, you may add `parsers/nse_shareholding_fii_delta.py` and fill `shpFiiDelta`. If the JSON lacks those fields, keep null. Stretch is **not** required for top-10 success.

---

## 3. Honest source contract (memorize)

| Key | Grain | Allowed use on a **stock** row |
|---|---|---|
| R2 cash (`nse_bhavcopy_eod`) | per symbol, session | volume boost, session return; **attention only** |
| R14/R5/A4 bars | per symbol, adjusted | **gap** = (open−prevClose)/prevClose if CA not WAIT_CA; else UNKNOWN |
| `nse_large_deals` / bulk / block / BSE mirrors | per symbol, **if symbol present** | Named buy/sell + **client string as-is**. Client empty → `UNNAMED_DEAL`. Client containing FII/FPI → `NAMED_FII_LIKE_DEAL` (still EVENT, not daily FII tape) |
| `nse_shareholding_pattern` | per symbol, quarter **raw** | **This ticket: `shpFiiDelta=null`.** Existing parse = promoter/public only. Label `SHP_FII_DELTA_NOT_NORMALIZED`. No `SHP_QUARTER` tag until a tested FII%+prior-quarter normalizer exists |
| AMFI scheme/portfolio last-good | per stock, **quarter/month** | MF **delta**. Label `DELAYED_MF`. Never “bought today” |
| `nse_fii_dii` | **market**, not symbol | Board-level chip: `MARKET_FII_NET`. **Never** copy onto RELIANCE as “FII bought RELIANCE” |
| `nse_mto_delivery` | per symbol | delivery z if ≥20 sessions + PIT; else UNKNOWN. Volume ≠ delivery |
| Third-party FII screens (`fii_stock_signals.THIRD_PARTY_FII_SCREEN_KEYS`) | names/tickers | `INFO_ZERO_SCORE` only. **Cannot** create BUY/SELL. **Cannot** fill a missing official FII fact |
| `nse_fo_bhavcopy` via A6 | WATCH F&O names | OI quadrant **package**. Missing FO does **not** punish cash-only |
| Ban / WAIT_CA / REJECT | already R2/R14 | **Hard veto**: cannot enter BUY/SELL 10 |

**Forbidden sentence in UI or JSON:** “FII bought {symbol} last week” unless the evidence is a **dated official named deal or SHP row** for that symbol. Daily FII/DII is not that.

---

## 4. Screening logic (high-level, File A-safe)

Two-stage (do not one-score everything):

**Stage A — queue (already R2):** official cash move + activity. Same dataset root → **one** participation story (return and volume are not two votes).

**Stage B — R6 stickers on top-N (e.g. 40 WATCH):**  
delivery, named deals, quarterly SHP/AMFI, A6 OI, gap from adjusted bars, market FII as **regime chip only**.

**BUY research 10 / SELL research 10** (display ranks, not public_state):

1. Candidate must be R2 WATCH (or WAIT with no hard REJECT). Direction = R2 Python `evidence_direction` / JSON `evidenceDirection` (`BULLISH`→BUY board, `BEARISH`→SELL board). Map, do not rename. Do not invent direction from FII.
2. Hard veto → drop: REJECT, WAIT_CA, ban.
3. **Score for display only** (not File A CONFIRMED, not p̂):
   - base = R2 `attentionPriority` (0–1)
   - **add tags, do not add a second cash vote:**
     - gap aligned with direction (up for BUY, down for SELL) → tag `GAP_ALIGNED` (small bonus **only as a display key**, document it as the same cash root → **cap** so it cannot dominate FII fiction)
     - volume percentile already in base → **do not add again**
     - delivery z same direction as “quiet accumulation / distribution” → tag `DELIVERY` (B3-style, still not CONFIRMED)
     - **named** official deal same side → tag `NAMED_DEAL` (EVENT_AND_SPONSOR, one family)
     - SHP FII delta → **not used this ticket** (`shpFiiDelta=null`)
     - AMFI delta same side → tag `MF_DELAYED` (delayed sponsor; do not invent SHP FII to pair with it)
   - market FII net → **board context**, not a per-name bonus
   - third-party FII list hit → **info pill only**, score +0
4. Sort BUY and SELL separately; take 10 each.
5. If <10, return what exists. Do **not** backfill with third-party names that are not on R2.

This is **research shortlist**, not a trading system. No Kelly, no T1/T2 required in this ticket (levels are later).

---

## 5. What to build

**Backend**

- First: open `attention_order.py` and dump one R2 row’s aliases. Wire top10 from those names.
- `backend/trendforge_api/selection/r6_live.py`  
  `build_r6_enrichment(limit_watch=40)` reads latest R1/R2/R4/R14/R5 + last-good of the keys above. Hash mismatch → `WAIT_R6_LINEAGE_MISMATCH`.  
  **No SHP FII-delta parser required.** Set `shpFiiDelta=null` + `whyUnknown+=SHP_FII_DELTA_NOT_NORMALIZED`.
- `backend/trendforge_api/selection/top10_research.py`  
  `build_top10_research()` → `{ buy: [...10], sell: [...10], marketFii, calibration: RESEARCH_SHORTLIST_NOT_CONFIRMED }`.
- Reuse `fii_stock_signals.py` and `evidence_builder.py`. Do not duplicate parsers.
- Extend A6; do not replace it.
- Routes:
  - `GET /api/v1/selection/enrichment`
  - `GET /api/v1/selection/top10`
  - POST → 405  
- Pipeline: optional stage after R5 in `cash_post_commit` **or** compute-on-GET like s4s5. Prefer **GET from latest spine** so you don’t invent orchestrator-8 unless tests require persist. If you persist: new profile `PRF-R6-ENRICH-WAIT`, never flip activation.

**Row fields (camelCase):**  
`symbol, r2PublicState, evidenceDirection, attentionPriority, gapPct|null, volumeTag, deliveryStatus, dealSummary, shpFiiDelta|null, mfDelta|null, foPackage, tags[], why[], whyUnknown[], displayRank, researchState=WAIT, canUnlockConfirmed=false`

**Frontend (one shell)**

- Do **not** create a second app.
- Paint `section#all-stocks` and/or Live Ops `#top10ResearchPanel` with BUY 10 / SELL 10 cards: symbol, direction, tags, **UNKNOWN list**.
- Reuse `#allStockContent` if `applyLiveSelection` can take an optional top10 map — **do not** fill entry/T1 as trades.
- Adapter: optional GET `/api/v1/selection/top10` (503 → empty board with WAIT copy).
- Files: `frontend/top10-research.js`, mounts in `frontend/index.html`, `selection-live-adapter.js`, `acceptance-check.js`.

---

## 6. Tests (must pass)

| ID | Assert |
|---|---|
| T1 | `nse_fii_dii` cannot set a per-symbol `fiiBoughtThisStock` field |
| T2 | Unnamed large deal ≠ FII buy |
| T3 | Third-party screen +0 score; names not on R2 cannot enter top 10 |
| T4 | AMFI labelled delayed; SHP `shpFiiDelta is None` and `SHP_FII_DELTA_NOT_NORMALIZED` in whyUnknown; never “last week” |
| T4b | Direction read from `evidence_direction` / JSON `evidenceDirection`; R2 model field not renamed |
| T5 | WAIT_CA / REJECT excluded from BUY/SELL 10 |
| T6 | Cash-only name not punished for missing FO |
| T7 | Volume not added twice on top of R2 priority |
| T8 | `canUnlockConfirmed=false`; no CONFIRMED rows |
| T9 | Lineage mismatch → 503 |
| T10 | POST 405 |
| T11 | Missing MTO → delivery UNKNOWN, not volume proxy |
| T12 | R2 `runHash` unchanged after building R6 (read-only) |

```
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_r6_live.py tests/test_top10_research.py tests/test_r5_live_structure.py tests/test_r14_live_ca_join.py tests/test_r2b_live_named_activation.py -q
cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Scratch → `delete/r6_top10_wip_<date>/`. No `tmp_*.py` in repo root.

---

## 7. Docs (short)

Patch `fileindex.md`, `docs/BUILD_STATUS.md`, `docs/DECISIONS.md` (D-043: R6 stickers ≠ FII daily tape ≠ CONFIRMED), `docs/VALIDATION.md`, remaining_build README.  
Do **not** mark R2-B unlock or File A CONFIRMED done.

---

## 8. Stop

Do not start R5 T1/T2, Kelly, R12, or `sourceActivationReady=true`.  
Success is **10+10 research names with honest why/UNKNOWN**, not a buy stamp.
