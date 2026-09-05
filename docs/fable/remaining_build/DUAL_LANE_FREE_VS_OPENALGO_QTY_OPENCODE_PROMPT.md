# OPENCODE BUILD PROMPT — Option B dual lane (LOCKED)
## Switch OFF = free official NSE (try free intraday; else INTRADAY_OFF) · Switch ON = all OpenAlgo DATA API · research funds/positions math · never place_order

Copy **this entire file** into OpenCode. Load skills first. Think. Build. Run **§9 GATES**. Debug every fail.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. Chain with `;` not `&&`.  
**Date: 2026-08-25.** **Choose Option B only.** S7+S8 are coded. Do **not** rebuild S2–S8. Do **not** implement File A S9.

Skills (OpenCode `skill` tool, in order): `superpowers/using-superpowers` → `unlazy` → `superpowers/verification-before-completion` → `superpowers/systematic-debugging` → `superpowers/test-driven-development` → `superpowers/requesting-code-review`.

**Before coding OpenAlgo:** read official docs (not folklore):

- Repo: https://github.com/marketcalls/openalgo  
- Data API index: https://docs.openalgo.in/api-documentation/v1/data-api  
- History: https://docs.openalgo.in/api-documentation/v1/data-api/history  
- Option chain: https://docs.openalgo.in/api-documentation/v1/data-api/option-chain  
- Greeks: https://docs.openalgo.in/api-documentation/v1/data-api/optiongreeks  
- Existing client: `backend/trendforge_api/openalgo_client.py` (Q5-R7 boundary already forbids order/account routes)

---

## 0. Remaining product — this ticket is Option B only

Already coded: R1–R6, R14, R2-B (`authorizedCount=0`), S2–S8. `sourceActivationReady=false`. Live CONFIRMED unreachable.

| Still open | Need it for live research? | This ticket |
|---|---|---|
| Dual data lane + research qty at confirmation | **Yes — next slice** | **Build** (FREE default, OpenAlgo data ON, qty + calculated funds/position) |
| S9 PIT homework | Later (labels, not trading) | **Do not implement** |
| R12 full options timeline | Partial here (EOD FO + optional OpenAlgo chain) | **Partial only** — not walls/GEX/R12 complete |
| R8–R11, R13, R16–R18 | Later scanners / MCX / PIT_APPROVED | **Do not implement** |
| R2-B unlock → live CONFIRMED | Separate File A amendment | **Do not flip** `sourceActivationReady` |
| OMS / `place_order` | **Never** | **Never** (also never OpenAlgo `/funds` `/positionbook`) |

---

## 0.1 Option B (the only option to build)

One switch. Default **OFF**. App **boots and runs** with OpenAlgo uninstalled and no broker login.

### Switch OFF — free official NSE (same as old Option A)

No broker. No OpenAlgo.

Candles, F&O, ban/MWPL, delivery, CA = official NSE/NCL **last-good**: UDiFF cash/FO, bhavcopy, `combineoi`, `fo_secban`, A4 bars, R14 CA.

**Intraday:** **try** every **already-registered free/official** NRT source in the inventory (pre-open, activity, any official snapshot that is not a broker). If a source returns **usable schema-valid bars/quotes**, set `intradayMode=ON_FREE` but `canSupportConfirmed=false` (File A: free/public NRT ≠ live CONFIRMED). If **no** free usable intraday exists, set `intradayMode=OFF` and run **EOD-only**. Do not fake ticks. Do not yfinance-as-authority.

Quantity still at confirmation point, not an order.

### Switch ON — all market data from OpenAlgo Data API

Connect using GitHub/docs + existing client:

```text
OPENALGO_ENABLED=1
OPENALGO_BASE_URL=http://127.0.0.1:5000    # local OpenAlgo; remote needs OPENALGO_ALLOW_REMOTE=1
OPENALGO_API_KEY=<from OpenAlgo UI, never log>
```

When effective lane is OPENALGO_RO, **fetch market data from OpenAlgo**, not a second Yahoo stack:

| OpenAlgo Data API | Use |
|---|---|
| POST `/api/v1/quotes` + `/multiquotes` | last/ltp for shortlist |
| POST `/api/v1/history` + `/intervals` | candles (intraday intervals when broker/Historify serves them) |
| POST `/api/v1/depth` | inspector depth only; not a vote |
| POST `/api/v1/optionchain` | chain for shortlist underlyings |
| POST `/api/v1/optiongreeks` + `/multioptiongreeks` | inspector Greeks |
| POST `/api/v1/optionsymbol` `/expiry` `/symbol` `/search` `/instruments` | identity for F&O qty/lot |
| POST `/api/v1/syntheticfuture` | display only |

Facts are `BROKER_ORIGINATED` (OPN-003). They **cannot** unlock File A CONFIRMED. They **cannot** replace official NSE EOD as the R5/S4 authority series. They **may** supply fresher last price / chain / ATR for **research qty and inspector**.

If OpenAlgo is down: stay/fallback FREE + `WAIT_OPENALGO_ABSENT`. Do not crash.

**Not Data API (do not call):** `placeorder`, `placesmartorder`, `modifyorder`, `cancelorder`, `funds`, `holdings`, `positionbook`, `openposition`, `orderbook`, `tradebook`, `margin`, `account`.

---

## 0.2 Production-ready (this ticket)

1. Switch OFF: full research path on official last-good; `intradayMode` ON_FREE or OFF with a named reason.  
2. Switch ON: OpenAlgo data hose for quotes/history/chain/greeks on the shortlist.  
3. At `draftConfirmedEligible`: LONG/SHORT `researchQuantity` + **research funds/position card**.  
4. `executable=false`. `confirmedCount=0`.  
5. GATES green.

---

## 0.3 Forbidden

- Any OpenAlgo **order or live-account** route (list in §0.1).  
- `sourceActivationReady=true` or live `CONFIRMED`.  
- Combined_Score, win %, P(win), Kelly as size.  
- yfinance / paid vendor as authority.  
- Dual-start collector. S9 PIT_APPROVED. DuckDB. OMS.
- New nav group, second public-state owner, or S7 DTO field named `quantity` (use `researchQuantity` on the qty DTO; join in UI).

---

## W. Folder map, wiring, delete folder (mandatory — do not improvise)

If a file is not in **OWNS**, do not create a parallel tree. Reuse the existing shell.

### W.1 Allowed paths (OWNS)

```text
BACKEND (create)
  D:\TrendForge\backend\trendforge_api\selection\data_lane.py
  D:\TrendForge\backend\trendforge_api\selection\research_quantity.py
  D:\TrendForge\backend\tests\test_data_lane.py
  D:\TrendForge\backend\tests\test_research_quantity.py

BACKEND (extend only — no second client / no second SQLite)
  D:\TrendForge\backend\trendforge_api\openalgo_client.py
      add Data-API methods if missing; NEVER add forbidden terms
  D:\TrendForge\backend\trendforge_api\main.py
      register GET/POST data-lane; GET research-quantity{,/symbol}; POST qty 405
  D:\TrendForge\backend\trendforge_api\storage.py
      optional: one settings row for lane preference (no secrets). Prefer env-first.

FRONTEND (create)
  D:\TrendForge\frontend\data-lane.js
  D:\TrendForge\frontend\research-quantity.js

FRONTEND (extend — same shell, no new nav group)
  D:\TrendForge\frontend\index.html
      mount both scripts with cache-bust; add the IDs in W.3
  D:\TrendForge\frontend\selection-live-adapter.js
      Promise.all name-count MUST equal fetch-count (today 13; this ticket +2 = 15)
  D:\TrendForge\frontend\product-fixture.js
      paint research qty/side on All Stocks from qty DTO join-by-symbol; never invent CONFIRMED
  D:\TrendForge\frontend\s7-state.js
      idea card may CALL qty helper; do not add `quantity` / `entry` / `stop` keys to S7 schema
  D:\TrendForge\frontend\styles.css
      switch + funds/position card only
  D:\TrendForge\frontend\tests\acceptance-check.js
      needles in W.4

DOCS (append observed evidence only)
  D:\TrendForge\docs\DECISIONS.md
  D:\TrendForge\docs\BUILD_STATUS.md
  D:\TrendForge\docs\VALIDATION.md
  D:\TrendForge\docs\fable\remaining_build\README.md   (status row only)

DELETE / throwaways (all scratch, probes, GATES — never product code)
  D:\TrendForge\delete\dual_lane_qty_2026-08-25\          WIP notes, probe.py, battery snippets
  D:\TrendForge\delete\gates_dual_lane_qty_2026-08-25\GATES.md
```

Do **not** write product modules under `delete/`. Do **not** add `frontend/src/` or a React app.

### W.2 Runtime wiring (one pipe)

```text
index.html
  script data-lane.js?v=20260825-lane-1
  script research-quantity.js?v=20260825-qty-1
  (existing s7-state.js, s8-persist.js, selection-live-adapter.js)

adapter Promise.all  (15 names = 15 fetches)
  ...existing 13...
  fetchOptionalJson("/api/v1/settings/data-lane")
  fetchOptionalJson("/api/v1/selection/research-quantity")

then
  TrendForgeDataLane.apply(laneDto)          # switch + intradayMode chip
  TrendForgeS7State.apply(s7State)           # publicState owner — unchanged contract
  TrendForgeResearchQty.apply(qtyDto, s7State)
       join rows by symbol
       if draftConfirmedEligible → LONG/SHORT + researchQuantity + funds/position card
       else qty 0 copy
  product-fixture paints All Stocks from S7 state + qty join (no second score)
```

Hash-match: qty builder reads **same** S7/S4/S8 run as the adapter’s S7 GET. 503 `WAIT_*_LINEAGE` if mismatch — UI shows WAIT copy, not last-good theater.

POST `/api/v1/settings/data-lane` from the switch only. It does **not** start Refresh/collector.

### W.3 index.html IDs (add once, reuse Live Ops / command bar / inspector)

Do **not** invent a left-nav room. Mount in existing chrome:

| ID | Where | Paints |
|---|---|---|
| `#dataLaneSwitch` | `header.command-bar` `.header-controls` | FREE ⇄ OPENALGO_RO toggle |
| `#dataLaneMeta` | next to switch | effectiveLane + intradayMode + blocker |
| `#s7StatePanel` | already exists | S7 public state (do not duplicate) |
| `#researchQtyPanel` | inside `#s7StatePanel` or idea-card column | qty + “not an order” |
| `#researchFundsPanel` | Live Ops `#liveDecisionPanel` **above** `#liveDecisionList` | calculated funds/remaining |
| `#researchPositionCard` | same | hypothetical LONG/SHORT position or “none” |

Copy on `#liveDecisionMeta` may stay; **add** chip: “Research funds/positions calculated — not a broker account.”

### W.4 acceptance-check.js needles (must add)

```text
data-lane.js?v=20260825-lane-1
research-quantity.js?v=20260825-qty-1
id="dataLaneSwitch"
id="researchQtyPanel"
id="researchFundsPanel"
/api/v1/settings/data-lane          in adapter
/api/v1/selection/research-quantity in adapter
"not an order"
"not a broker account"
adapter Promise.all length comment or names = fetches (15)
no publicState CONFIRMED assignment in data-lane.js / research-quantity.js
```

Adapter rule already used by S4–S8: **fetch list length === apply-name list**. If you add two fetches, add two `TrendForge*.apply` calls. Do not leave an unused 16th fetch.

---

## 1. Data-lane switch

### 1.1 Contract

`D:\TrendForge\backend\trendforge_api\selection\data_lane.py`

```text
schema          trendforge.data-lane.v1
lane            FREE_OFFICIAL | OPENALGO_RO
default         FREE_OFFICIAL
openAlgoState   reuse OpenAlgoCapabilityReport (ABSENT/DISABLED/SHADOW_LIVE/REJECTED)
canConfirm      always false this ticket
executable      always false
```

Resolution order (first wins):

1. Env `TRENDFORGE_DATA_LANE=FREE_OFFICIAL|OPENALGO_RO`  
2. Local settings row (optional, no secrets)  
3. Default `FREE_OFFICIAL`

Switch ON is **ignored** unless `OPENALGO_ENABLED=1` **and** `OpenAlgoConfig.from_env()` succeeds **and** capability has **zero** forbidden routes. Otherwise stay FREE and set `blocker=WAIT_OPENALGO_ABSENT` or `WAIT_OPENALGO_FORBIDDEN`.

`OPENALGO_API_KEY` never appears in API JSON, logs, or frontend.

### 1.2 Routes

```
GET  /api/v1/settings/data-lane
POST /api/v1/settings/data-lane     body {"lane":"FREE_OFFICIAL"|"OPENALGO_RO"}
```

POST only persists the **preference**. It cannot enable execution. If OPENALGO_RO requested but capability ABSENT/DISABLED/REJECTED → store preference but `effectiveLane=FREE_OFFICIAL` + blockers.

Reuse existing `GET /api/v1/integrations/openalgo/capability`. Extend it with `effectiveDataLane` if cheap; do not fork a second capability DTO.

### 1.3 Frontend

See **§W**. Switch lives in `#dataLaneSwitch` (command bar). Labels:

`Data: Free official NSE`  ⇄  `OpenAlgo data API`

`#dataLaneMeta` shows `effectiveLane`, `intradayMode` (`ON_FREE` | `OFF` | `OPENALGO`), blocker. Copy: “Default free — no broker. OpenAlgo ON = quotes/history/chain only. Not an order.”

`data-lane.js` cache-bust `?v=20260825-lane-1`. Adapter: one extra fetch `/api/v1/settings/data-lane` + `TrendForgeDataLane.apply`.

---

## 2. FREE_OFFICIAL lane (must work with OpenAlgo off)

Use **existing** last-good official artifacts. Do not invent downloaders if collector already has the file.

| Need | Authority (free) | If missing |
|---|---|---|
| Stock EOD candles | NSE UDiFF / bhavcopy → A4 bars | WAIT_BARS / researchQuantity=0 |
| **Intraday probe** | Any **registered** free/official NRT job that already yields schema-valid quotes/bars (pre-open, activity, official snapshots). HTTP 200 HTML/`{}` is **not** data. | `intradayMode=OFF`, reason `WAIT_NO_FREE_INTRADAY` — EOD-only; do not invent ticks |
| Index / VIX | NSE index close (S2) | WAIT_WEATHER_UNKNOWN, not a stock vote |
| F&O OI / MWPL / ban | UDiFF FO zip, `combineoi`, `fo_secban` | UNKNOWN / REJECT on BAN |
| Option chain EOD | UDiFF FO strikes for that symbol/expiry | `OPTIONS_PACKAGE=UNKNOWN` score 0; empty NSE `{}` is not a chain |
| Delivery / deals / CA | existing A4/R14/R6 loaders | UNKNOWN, no fake FII |

`intradayMode=ON_FREE` still has `canSupportConfirmed=false`. Qty uses official **closed** close as `researchEntry` unless a free NRT last is proven; if using NRT last, `data_quality_cap<=0.7` and `evidenceKind=PROXY`.

Do **not** add yfinance as a silent fallback.

Expose on data-lane GET: `intradayMode`, `intradayReason`, `triedSourceKeys[]`.

---

## 3. OPENALGO_RO lane (switch ON only)

**Read GitHub + docs first**, then extend `openalgo_client.py` (do not fork a second client).

Allowed **data** surface (docs.openalgo.in Data API). Add methods only if missing, all POST to local OpenAlgo:

```text
quotes, multiquotes, depth, history, intervals,
symbol, search, expiry, instruments,
optionsymbol, optionchain, syntheticfuture,
optiongreeks, multioptiongreeks
```

Keep `OPENALGO_FORBIDDEN_ROUTE_TERMS` as a hard deny. Adding `funds`/`positionbook` methods **fails this ticket**.

Wire as the **shortlist hose** (S5/S7 symbols), not 2,633 names.

| Call | Use | Label |
|---|---|---|
| quotes / history | last + candles for ATR / inspector / researchEntry overlay | BROKER_ORIGINATED |
| optionchain + greeks | options package / inspector | CONTEXT; missing → UNKNOWN |
| expiry / optionsymbol / instruments | lot/tick/expiry for qty | identity; missing → WAIT_LOT |
| depth | inspector | not a vote |

Rules:

- App starts if OpenAlgo is down → effective FREE.  
- T-069 still pass. `intradayConfirmationAllowed=false`.  
- OpenAlgo candles **do not** replace A4 in R5/S4.  
- If history returns intraday intervals: `intradayMode=OPENALGO`, still no CONFIRMED.  
- `data_quality_cap <= 0.7` when OpenAlgo last price is used for qty.

---

## 4. Research quantity at confirmation (LONG / SHORT)

### 4.1 When qty may be non-zero

S7 already computes `draftConfirmedEligible` (checklist would pass **if** activation were true). **That is the confirmation point for this ticket.**

```text
if publicState == REJECT:           researchQuantity = 0; reason WAIT_REJECT
elif not draftConfirmedEligible:    researchQuantity = 0; reason WAIT_NOT_AT_CONFIRMATION
elif entry/stop unusable:           researchQuantity = 0; reason WAIT_NO_STOP
elif lot/tick unknown for F&O:      researchQuantity = 0; reason WAIT_LOT
else: compute researchQuantity
```

Do **not** emit `publicState=CONFIRMED`. Qty is a **label on a WAIT/WATCH row**.

### 4.2 Direction (bull / bear)

From S7 `evidenceDirection` only:

| evidenceDirection | side | copy |
|---|---|---|
| BULLISH / BUY | LONG | “Research size for long — not an order” |
| BEARISH / SELL | SHORT | “Research size for short — not an order” |
| else | FLAT | qty 0, `NO_SIDE` |

S2 weather (bull/bear market) is **regime_cap**, not the stock side. UNKNOWN regime → `regime_cap=0.5` (conservative), never a flip of LONG/SHORT.

### 4.3 Geometry (confirmation point)

Idea card today has null entry/stop. This ticket **fills research geometry only**:

- `researchEntry` = last **official closed** close (EOD). Label `RESEARCH_REF_CLOSE`, not a broker fill.  
- `researchStop` = S4 `invalidationCondition` if parseable as a price **on the correct side of entry**; else `entry - k*ATR` (LONG) / `entry + k*ATR` (SHORT), `k=1.0` versioned.  
- ATR from official A4 bars (`validation_engine` / existing volatility helpers). Missing ATR → qty 0.  
- `researchT1` optional 1.5*R; display only.

Never write `entry`/`stop`/`quantity` as order fields. Use the `research*` prefix. Keep `executable=false`. Hybrid V3 A/B/C overlay stays overlay.

### 4.4 Formula (File B §16.14 as RESEARCH_PROXY_NOT_CALIBRATED)

Capital is **not** broker funds. Config:

```text
researchCapitalInr = 100000     # user setting, default 1L
researchRiskPct    = 0.005      # 0.5% of capital per idea
calibrationCap     = 0.5        # uncalibrated until PIT_APPROVED
```

```text
unit_risk = abs(researchEntry - researchStop) + slippage_per_share + fees_per_share
  slippage_per_share = max(0.001 * researchEntry, tick)   # declared placeholder VAL-001
  fees_per_share     = declared STT/GST placeholder, never live broker contract
risk_budget = researchCapitalInr * researchRiskPct
base_qty    = floor(risk_budget / unit_risk)
researchQuantity = floor(base_qty * data_quality_cap * regime_cap * liquidity_cap * calibrationCap)
```

Caps (all in 0..1, missing → 0 qty):

- `data_quality_cap`: 1.0 if S8 completeness >= profile min and lane FREE with official bars; 0.7 if OpenAlgo PROXY last price used; 0 if completeness WAIT_PARTIAL_SCAN.  
- `regime_cap`: 1.0 if S2 regime not UNKNOWN/suspect; 0.5 if UNKNOWN; 0 if INDEX_CHANGE_SUSPECT and direction disagrees with index (optional conservative).  
- `liquidity_cap`: 1.0 if not ban/T2T-intraday; 0 if F&O BAN / WAIT_CA identity-break.

Lot round: equity → integer shares; F&O → nearest **lower** lot if lot known else 0. Freeze qty cap if known from master else ignore.

`researchQuantity` is **shares or lots** with `qtyUnit` field.

Higher evidence strength **must not** increase qty (File B rule 2). Strength is not a size knob.

### 4.4.1 Research funds + position **calculations** (not broker account)

User asked to **calculate** funds and positions. This is a **paper research ledger** on `researchCapitalInr` (default 1L). It is **not** OpenAlgo `/funds` or `/positionbook`.

When `researchQuantity==0`:

```text
researchFunds.capitalInr        = 100000
researchFunds.reservedRiskInr   = 0
researchFunds.positionNotionalInr = 0
researchFunds.remainingCapitalInr = 100000
researchPosition                = null
```

When qty > 0 at confirmation:

```text
lot_mult     = lot size or 1
notionalInr  = researchQuantity * lot_mult * researchEntry
reservedRisk = researchQuantity * lot_mult * unit_risk   # capped at risk_budget
remaining    = capitalInr - notionalInr     # cash remaining if fully allocated; never negative → cap qty first
```

If `notionalInr > remainingCapital` (single-name 1L book): reduce qty (lot-round down) until it fits, or 0 + `WAIT_FUNDS`.

`researchPosition` card (hypothetical, `executable=false`):

```text
symbol, side=LONG|SHORT, qty, qtyUnit, researchEntry, researchStop,
notionalInr, reservedRiskInr, lane, evidenceKind, asOf
```

UI: “Research funds / position — calculated, not a broker account.”

Do **not** persist these as live OMS positions. Optional attach on the qty GET only.

### 4.5 Module / routes

`D:\TrendForge\backend\trendforge_api\selection\research_quantity.py`  
Schema `trendforge.research-qty.v1`  
Profile `PRF-RESEARCH-QTY-WAIT`  
Ceiling `LIVE_RESEARCH_QTY_NOT_EXECUTABLE`

```
GET /api/v1/selection/research-quantity
GET /api/v1/selection/research-quantity/{symbol}
POST → 405
```

Build from hash-matched S7 (+ S4 pack + S8 completeness if present). 503 on lineage miss.

Attach the qty block onto S7 idea-card GET **additively** (new fields only) OR keep S7 unchanged and let the UI join the qty GET. Prefer **join in UI** so S7 validators that forbid `quantity` stay valid.

### 4.6 Frontend

See **§W**. `research-quantity.js` (`?v=20260825-qty-1`) joins qty DTO to S7 by symbol.

- `#researchQtyPanel`: if `draftConfirmedEligible` → LONG/SHORT + `researchQuantity` + “not an order”; else “qty 0 — not at confirmation”.
- `#researchFundsPanel` / `#researchPositionCard`: calculated 1L ledger; “not a broker account”.
- All Stocks (`product-fixture.js`): same join; do not write S7 `quantity`.
- Adapter: fetch `/api/v1/selection/research-quantity` + `TrendForgeResearchQty.apply(qtyDto, s7State)`.

---

## 5. Tests (mandatory)

`backend/tests/test_data_lane.py`

1. Default lane FREE with OpenAlgo env unset; app imports.  
2. POST OPENALGO_RO without env → effective FREE + WAIT_OPENALGO_ABSENT.  
3. Capability with forbidden route → REJECTED, effective FREE.  
4. POST 405 on qty route; data-lane POST allowed for preference only.  
5. FREE lane: `intradayMode` is `ON_FREE` or `OFF` with `intradayReason` (never silent).  
6. Client has no `funds`/`positionbook`/`placeorder` methods.

`backend/tests/test_research_quantity.py`

1. `draftConfirmedEligible=false` → qty 0.  
2. REJECT/ban/WAIT_CA → qty 0.  
3. BULLISH → LONG; BEARISH → SHORT; FLAT → 0.  
4. Missing stop/ATR → 0.  
5. `executable is False`; no `place_order` / `funds` client call in module.  
6. Evidence strength increase does not increase qty (same stop).  
7. OpenAlgo-only last price → data_quality_cap <= 0.7 and evidenceKind PROXY.  
8. calibrationCap 0.5 until PIT_APPROVED.  
9. Lot unknown on F&O → 0 + WAIT_LOT.  
10. Hash mismatch → 503.  
11. Existing `test_q5_openalgo_boundary.py` still pass (T-069).  
12. `test_s7_state_gates.py` / `test_s8_persist_run.py` still pass; S7 still `confirmedCount=0`.  
13. qty>0 ⇒ `researchPosition.side` in {LONG,SHORT}, `remainingCapitalInr>=0`, `positionNotionalInr` matches qty*entry*lot.  
14. qty=0 ⇒ `researchPosition` null, remaining = capital.  
15. Notional larger than capital ⇒ qty reduced or 0 + WAIT_FUNDS (never negative remaining).

No yfinance import. No new CONFIRMED.

---

## 6. Docs

- `docs/DECISIONS.md`: D-0xx **RESEARCH_QTY_AT_DRAFT_CONFIRMED** — user-requested research size; not File A product `final_qty`; not OMS.  
- `docs/BUILD_STATUS.md` + `VALIDATION.md` with observed GET, default FREE, qty 0 on non-eligible, sample LONG/SHORT when eligible.  
- Throwaways: `D:\TrendForge\delete\dual_lane_qty_2026-08-25\`  
- GATES: `D:\TrendForge\delete\gates_dual_lane_qty_2026-08-25\GATES.md`

---

## 7. Audit after build

```text
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_data_lane.py tests/test_research_quantity.py tests/test_q5_openalgo_boundary.py tests/test_s7_state_gates.py tests/test_s8_persist_run.py -q --tb=short
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests -q --tb=no
# failed=0 (current bar). Zero NEW fails.

cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Live (restart :8000 of **this** tree), OpenAlgo **off**:

```text
GET  /api/v1/settings/data-lane              effectiveLane=FREE_OFFICIAL; intradayMode ON_FREE or OFF
GET  /api/v1/integrations/openalgo/capability  executable=false
GET  /api/v1/selection/s7-state              confirmedCount=0
GET  /api/v1/selection/research-quantity     executable=false; funds remaining>=0; position null unless draftConfirmedEligible
POST /api/v1/selection/research-quantity     405
```

Grep `research_quantity.py` + `data_lane.py` + `openalgo_client.py`: no forbidden route terms as callable methods.

---

## 8. Debug catalog

| Symptom | Fix |
|---|---|
| App fails to boot without OPENALGO_* | default FREE; from_env only when switch ON |
| Switch ON silently uses Yahoo | delete; FREE or OpenAlgo only |
| Qty on every WATCH | gate on draftConfirmedEligible |
| Qty on REJECT | 0 |
| CONFIRMED appears | revert; qty is not a state |
| place_order imported “for later” | delete |
| S7 test fails on `quantity` key | keep research* on qty DTO, not S7 |
| OpenAlgo key in GET JSON | redact |
| Empty NSE option-chain `{}` treated as chain | UNKNOWN, use UDiFF FO EOD |
| All Stocks blank / adapter throw | fetch count ≠ apply names (must be 15) |
| Qty panel missing | forgot index.html IDs / script mount / cache-bust |
| Scratch left in backend/ | move to `delete/dual_lane_qty_2026-08-25/` |
| Full-suite new fails | systematic-debug; do not weaken T-069 |

---

## 9. GATES (write first)

`D:\TrendForge\delete\gates_dual_lane_qty_2026-08-25\GATES.md`

```text
G1 module
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from trendforge_api.selection.data_lane import SCHEMA_VERSION; from trendforge_api.selection.research_quantity import SCHEMA_VERSION as Q; print(SCHEMA_VERSION, Q)"
EXPECT: trendforge.data-lane.v1

G2 pytest
CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_data_lane.py tests/test_research_quantity.py tests/test_q5_openalgo_boundary.py tests/test_s7_state_gates.py -q --tb=short
EXPECT: passed
CWD: D:\TrendForge\backend

G3 no orders
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from pathlib import Path
root=Path(r'D:\\TrendForge\\backend\\trendforge_api')
bad=('placeorder','placesmartorder','place_order')
hits=[f'{p}:{b}' for p in (root/'selection').rglob('*.py') for b in bad if b in p.read_text(encoding='utf-8', errors='replace').lower()]
print('NO_ORDERS' if not hits else hits); raise SystemExit(0 if not hits else 1)"
EXPECT: NO_ORDERS

G4 live default FREE + qty not executable
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request
lane=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/settings/data-lane'))
print(lane.get('effectiveLane') or lane.get('effective_lane'))
q=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/research-quantity'))
assert (q.get('executable') is False)
assert (q.get('confirmedCount', q.get('confirmed_count')) in (0, None))
print('QTY_LOCKED')"
EXPECT: QTY_LOCKED

G5 frontend
CHECK: node tests/acceptance-check.js
EXPECT: 0 failed
CWD: D:\TrendForge\frontend

G6 adapter fetch count
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from pathlib import Path; t=Path(r'D:\\TrendForge\\frontend\\selection-live-adapter.js').read_text(encoding='utf-8'); assert '/api/v1/settings/data-lane' in t; assert '/api/v1/selection/research-quantity' in t; assert 'TrendForgeDataLane' in t; assert 'TrendForgeResearchQty' in t; print('ADAPTER_WIRED')"
EXPECT: ADAPTER_WIRED
```

Stop when GATES green. **Not this file:** S9 PIT, full R12, R8–R11/R13, R16–R18, R2-B CONFIRMED, OMS.
