# OPENCODE BUILD PROMPT — File A S2 market weather
## Index / VIX / breadth / sector / commodity **context** (never a stock vote)

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. Shell: PowerShell. Chain with `;` not `&&`.

Copy this **entire file**. Think first.

Cash **S1 is already usable** at research/WAIT (IDs, ban, MWPL, CA join). **Do not rebuild S1, R1–R5, R14, R6, or the evidence radar.**  
This ticket finishes **S2 only**: the market weather layer that A5 started and then lied about (Nifty **20.15%** was points, not percent).

Do **not** set `sourceActivationReady=true`. Do **not** emit CONFIRMED or qty. Do **not** dual-start the collector.

---

## 0. Outcome (done means this was **observed**)

1. **Nifty day-change is a real percent**, recomputed from close vs previous close (or points ÷ previous). A fixture where `CHANGE=20.15` (points) and Nifty close ~24000 must **not** print `20.15%`. Honest value is about **0.08%**.
2. Live Ops / All Stocks shows a **market-weather strip**: Nifty, Bank Nifty, India VIX, breadth (or UNKNOWN), top/bottom sector indices, commodity local vs delayed-global — all labelled **CONTEXT**.
3. **IX** (`index_dashboard`) and **SC** (`sector_scope`) rooms paint from the same DTO. They are no longer empty `WAIT_DTO_UNAVAILABLE` **when last-good exists**. Missing last-good stays WAIT with a named code, not invented numbers.
4. Public stock state stays **WATCH / WAIT / REJECT**. Index/VIX/sector/commodity **cannot** confirm a stock. Radar fusion family `MARKET_AND_SECTOR_CONTEXT` stays **weight 0**.
5. CFTC / WGC / EIA **cannot** put a name on the commodity BUY/SELL board. Local MCX weather is separate from delayed global grey text.

---

## 1. What S2 is (and is not)

File A build pipeline **S2 = `SEL-003`**: *Build market, breadth, VIX, sector and commodity context. Context priors, never stock confirmation alone.*

| This ticket IS | This ticket is NOT |
|---|---|
| File A S2 / `FTR-002` / `FTR-003` / `FTR-030` | Hybrid V2 overlay S2 (`s2_environment.py`) |
| A5 companion weather, fixed and completed | A 124th inventory job / extra vote |
| Context chips + IX/SC rooms | `allowLong` / `TRADEABLE_BULLISH` as public_state |
| Honest UNKNOWN when a source is missing | yfinance sector RRG (already **REJECTED**) |

`market_context.py` already has `TRADEABLE_BULLISH`, `allow_long`, and a **200-bar** Nifty series. That is a **fixture/research engine**, not File A live S2. **Do not** promote those fields onto All Stocks or R2 `public_state`. Live S2 labels are only:

`RISK_ON` | `RISK_OFF` | `MIXED` | `RANGE` | `UNKNOWN`

They never change a stock’s four-state.

---

## 2. Authority (File A wins)

| Rank | File | Use |
|---|---|---|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` | S2 `SEL-003`; `FTR-002` market/VIX/breadth; `FTR-003` sector; `FTR-030` commodity macro; profiles PRF-001…007; FUS-009 families; no qty |
| 2 | `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md` | A5 is index **companion**, not a voter. Do not rebuild R1–R5 |
| 3 | `docs/fable/FINAL_MERGE_PLAN.md` | Paint All Stocks / Live Ops / IX / SC, not `/inventory-workbench` |
| 4 | `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` | Detail only. No File B qty / OpenAlgo |

Hybrid V2 B1/B2 stubs (`hybrid_v2/blocks/b1_regime.py`, `b2_sector.py`) may **read** S2 numbers as overlay later. **Do not** make Hybrid `p̂` or Kelly from this ticket.

---

## 3. Already live — READ, do not rewrite

```
selection/index_a5_context.py          A5: Nifty close + VIX close; companion
parsers/nse_index_close_parser.py      BUG: changePercent reads "change" first (points)
storage.list_nse_index_eod             history for NIFTY 50 / INDIA VIX
selection/evidence_radar/              3rd-eye; MARKET family weight 0; MCX local boards
commodity_context.py                   older MCX/global panel
hybrid_v2/blocks/b1_regime.py          STUB — leave stub or point at S2 DTO, no votes
frontend/app.js  TOOL_REGISTRY
  index_dashboard  WAIT_DTO_UNAVAILABLE
  sector_scope     WAIT_DTO_UNAVAILABLE
```

Verified last-good shape for `nse_all_indices` (JSON, 139 rows):

```text
index / indexSymbol, last, variation, percentChange, previousClose, open, high, low
example: NIFTY 50 last=24383.6 variation=66.45 percentChange=0.27 previousClose=24317.15
```

EOD all-indices **CSV** often has `CHANGE` = **points** and a separate percent column (`PERCHANGE` / `PERCENTAGE_CHANGE`). The live A5 parser currently does:

```python
"changePercent": parse_float(find_value(row, ("change", "change_percent")))
```

That is the **20.15 bug**: points land in a percent field.

---

## 4. Percent formula (mandatory, test this first)

Never treat these as percent: `change`, `variation`, `points_change`, `pointsChange`.

Prefer, in order:

1. `percentChange` / `percent_change` / `pChange` / `PERCHANGE` / `PERCENTAGE_CHANGE` / `change_percent` (only if the key is clearly percent, **not** the bare word `change`)
2. Else recompute:

```text
previous = previousClose  OR  (close - pointsChange) if pointsChange is present
if previous > 0:
    changePercent = (close - previous) / previous * 100
else:
    changePercent = null  (UNKNOWN, do not use 0)
```

Sanity (Nifty/Bank Nifty **EOD**, not a circuit-limit claim):

- If `|claimedPercent| > 5` **and** `|claimedPercent - |pointsChange|| < 1`, it is points mislabelled as percent → **recompute or null**.
- Do not silently clamp 20.15 → 0. A wrong parse must fail closed to `UNKNOWN` + `INDEX_PCT_PARSE_REJECTED`, not a pretty 0.00.

VIX is a **level**. Do not call VIX change a market direction.

---

## 5. S2 contract (what to compute)

One DTO, four weather blocks, one family: `MARKET_AND_SECTOR_CONTEXT` / `CG_MARKET_REGIME` (sectors use `CG_SECTOR_RS` as **context ranks**, still not stock votes). Commodity delayed block uses `MACRO_AND_COMMODITY_CONTEXT` / `CG_COMMODITY_CONTEXT`.

### 5.1 Index + VIX (`FTR-002`)

From **hash-matched** A5 / `nse_index_close_eod` last-good, **plus** `nse_all_indices` last-good if present (same trading date or labelled stale).

| Field | Rule |
|---|---|
| `nifty50.close` | Official close |
| `nifty50.changePercent` | Formula in §4 |
| `bankNifty` | Same, index name `NIFTY BANK` |
| `indiaVix.close` | Level |
| `indiaVix.changePercent` | vs **prior session** VIX close from `list_nse_index_eod`, not vs Nifty |
| `vixBand` | Versioned: e.g. `<12 LOW`, `12–20 NORMAL`, `>20 HIGH` — **context**, not short/long |
| `dataDate` | file date |
| `freshness` | CURRENT / STALE / MISSING |

Missing Nifty or VIX → weather `UNKNOWN`, stocks **unchanged**. Do not invent closes.

### 5.2 Breadth (`FTR-002`)

Official advances / declines / unchanged if a last-good row actually has them (`nse_pr_market_snapshot`, `nse_market_status`, or all-indices payload fields).  

**Missing → `breadthStatus=UNKNOWN`, not 0/0.** Zero advances is not “flat tape.”

If present: `breadthRatio = advances / max(declines, 1)` and a versioned label `BREADTH_RISK_ON` / `BREADTH_MIXED` / `BREADTH_RISK_OFF`. Still not a stock vote.

### 5.3 Sector leadership (`FTR-003`)

**Do not** fetch yfinance. Derive from official index rows already in `nse_all_indices` / all-indices EOD (NIFTY IT, AUTO, METAL, PHARMA, FMCG, ENERGY, REALTY, PSU BANK, PRIVATE BANK, …).

- One row per sector index: name, close, **honest** percent, rank by percent.
- Board-level list (e.g. 8 leaders / 8 laggards), not 2,463 stock scores.
- Stock-vs-sector RS (`FTR-004`) may be a **chip** on radar rows **only if** PIT constituents + aligned dates exist. If constituents last-good is missing → `SECTOR_RS=UNKNOWN`. Do **not** guess a stock’s sector from the ticker string.

Constituent source keys if present: `nse_nifty50_constituents`, `nse_nifty500_constituents`, sector lists in the registry. HTTP 200 ≠ usable.

### 5.4 Commodity weather (`FTR-030` + local `FTR-029` read-only)

Two layers, never mixed:

| Layer | Source | Allowed |
|---|---|---|
| **Local** | `mcx_bhavcopy_daily` last-good (already used by evidence radar) | Gold/silver/crude/copper close % vs prior **local** bar; DTE if expiry parses |
| **Delayed global** | CFTC / EIA / WGC last-good | Grey `CONTEXT_DELAYED`; `available_at` required; **cannot** create MCX direction |

Missing local MCX → commodity weather `UNKNOWN_NO_LOCAL_BAR`. Global still may show as grey. Radar commodity boards stay as they are (local-only seats).

---

## 6. What to build

**Backend**

- Fix `parsers/nse_index_close_parser.py` percent field (tests first). Keep A5 extracting Nifty + VIX, but percent must be honest. Optionally keep **all** index rows on the parse output so S2 can rank sectors without a second download.
- New: `backend/trendforge_api/selection/s2_market_weather.py`  
  `build_s2_market_weather()` reads latest A5 **or** last-good index artifacts + optional all-indices + breadth + MCX local + delayed global.  
  Ceiling: `LIVE_S2_CONTEXT_WAIT_ONLY`. Validators: `canUnlockConfirmed=false`, `sourceActivationReady=false`, `canRank=false`.
- Routes:
  - `GET /api/v1/selection/market-weather`
  - `GET /api/v1/selection/market-weather/sectors`
  - POST → **405**
- Prefer GET compute-on-read from last-good (like s4s5 / radar). If persist: new profile `PRF-S2-WEATHER-WAIT`, never flip activation.
- Wire a **read-only** chip into evidence radar explain `where` / market line. **Do not** change `FUSION_WEIGHTS_V1["MARKET_AND_SECTOR_CONTEXT"]` off `0.0`. **Do not** add a second cash vote.

**DTO (camelCase), all WAIT:**

```
schemaVersion, profileId=PRF-S2-WEATHER-WAIT,
tradingDate, builtAt, freshness,
nifty50 { close, changePercent, previousClose, pointsChange },
bankNifty { ... } | null,
indiaVix { close, changePercent, band },
breadth { advances, declines, unchanged, ratio, status },
regimeLabel,          # RISK_ON|RISK_OFF|MIXED|RANGE|UNKNOWN  (research only)
why[], whyUnknown[],
sectors: [{ name, close, changePercent, rank }],
commodityLocal: [{ symbol, changePercent, dte, status }],
commodityGlobal: [{ sourceKey, summary, lagLabel, canDirectContract=false }],
canUnlockConfirmed=false,
calibration=RESEARCH_CONTEXT_NOT_CONFIRMED
```

**Frontend (one shell)**

Do **not** create a second app.

- Paint `TOOL_REGISTRY.index_dashboard` and `sector_scope` from this GET (replace `WAIT_DTO_UNAVAILABLE` when payload exists).
- Live Ops / All Stocks: compact `#s2WeatherStrip` — Nifty %, VIX band, breadth or UNKNOWN, one leader / one laggard sector.
- Reuse `#commodityContextList` if it can consume `commodityLocal` + grey global; do not invent a second commodity page.
- Files: `frontend/s2-market-weather.js`, mounts in `frontend/index.html`, `app.js` tool rooms, `acceptance-check.js`, `styles.css`.
- 503 → rooms keep WAIT copy with the API `code`.

---

## 7. Forbidden (instant fail)

- Nifty `change` points shown as `%`
- Index / VIX / sector percent added into R2 `attention_priority`
- `nse_fii_dii` as “FII bought this stock”
- yfinance / Yahoo sector RRG
- CFTC/WGC confirming a commodity board seat
- `allowLong` / `TRADEABLE_BULLISH` as Q5 public_state
- Rebuilding R1–R5 / R14 / radar fusion weights
- Dual-starting the collector
- `sourceActivationReady=true`, CONFIRMED, qty, live T1/T2 as orders
- Missing breadth displayed as 0/0
- Pasting Hybrid S4/S5 into `r5_live.py`

---

## 8. Tests (must pass)

| ID | Assert |
|---|---|
| T1 | Fixture `CHANGE=20.15` points, close=24050, prev=24029.85 → `changePercent` ≈ **0.084** not 20.15 |
| T2 | JSON `percentChange=0.27` + `variation=66.45` keeps 0.27; does not replace with 66.45 |
| T3 | Rejected parse → `changePercent is None` + `INDEX_PCT_PARSE_REJECTED`, not 0 |
| T4 | VIX band is level context; VIX cannot set a stock BUY/SELL |
| T5 | Missing advances/declines → breadth UNKNOWN, not 0 |
| T6 | Sector list comes from official index rows; no yfinance import in S2 module |
| T7 | `commodityGlobal[].canDirectContract is False`; CFTC cannot appear as local % |
| T8 | `canUnlockConfirmed=false`; 0 CONFIRMED; R2 `runHash` unchanged |
| T9 | POST 405; lineage/last-good missing → 503 with named code |
| T10 | Existing `tests/test_cash_a5_c1.py`, `tests/test_evidence_radar.py`, `tests/test_r5_live_structure.py` still pass |

```
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s2_market_weather.py tests/test_cash_a5_c1.py tests/test_evidence_radar.py tests/test_r5_live_structure.py tests/test_r6_live.py tests/test_top10_research.py -q
cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Scratch → `delete/s2_weather_wip_<date>/`. No `tmp_*.py` in repo root.

---

## 9. Docs (short)

Patch `fileindex.md`, `docs/BUILD_STATUS.md`, `docs/DECISIONS.md` (**D-045**: S2 weather is context; Nifty % is recomputed; 20.15 points ≠ 20.15%; not CONFIRMED), `docs/VALIDATION.md`, remaining_build README.

Do **not** mark File A first CONFIRMED, R2-B unlock, or R11 MCX safety complete. MCX **weather** ≠ MCX **contract safety** (`FTR-028` still later).

---

## 10. Stop

Do not start live T1/T2 trades, Kelly, R12 chains, OpenAlgo, or `sourceActivationReady=true`.

**Success observed:**

1. Nifty % on IX / weather strip matches close vs previous, not the points column.  
2. VIX is a band, breadth is honest or UNKNOWN.  
3. SC shows official sector index ranks.  
4. Commodity strip: local % if MCX bhav exists; CFTC grey only.  
5. A cash BUY research name does **not** gain a second vote from Nifty being up.  
6. Public state still **0 CONFIRMED**.

That is S2: **the tape’s weather, not another reason to buy the stock.**
