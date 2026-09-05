# GLM / OPENCODE BUILD PROMPT — File A S9 PIT homework (SEL-010)
## Offline labels on free NSE EOD · no win-rate UI · no auto-trade · no broker · PIT_NOT_APPROVED

Copy **this entire file**. Think first. Build. Then run **§9 GATES** and debug every fail before claiming done.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. Chain with `;` not `&&`.  
**Date: 2026-08-24.** Run **after** `S8_PERSIST_RUN_GLM_PROMPT.md` GATES are green. This is the last File A S-stage. It is **not** R16/R18 complete and **not** `PIT_APPROVED`.

Authority: File A `docs/fable/new_merge_PLAN_2026-07-18.md` §9 S9 / FTR-034 / STO-015 / STO-017 / UI-009 / T-059..063 / T-087 / T-102 / T-109 / REJ-009 / REJ-010. Overlay: S9 row in `docs/fable/S0_S9_RUN_OVERLAY_MAP_2026-08-24.md`. Reuse: `validation_engine.label_price_path`, `hybrid_v2.as_lab.triple_barrier.label_event` (lab only).

If S8 `GET /api/v1/selection/scans/latest` is missing or GATES red: **stop**. Do not label from a live S7 GET without a persisted run id (that is look-ahead theater).

---

## 0. What “production ready” means here

TrendForge is a **localhost research screener**. Labels use **later official NSE EOD bars already on disk** (A4 / bhavcopy last-good). No broker account. No Yahoo. No OpenAlgo candles.

**Production-ready S9 = homework artifacts:** given a reconstructable S8 run, attach later path observations (WIN/LOSS/CENSORED/…) with leakage checks, costs declared, survivorship honest. The Validation tab stays **locked**. `validationStatus=PIT_NOT_APPROVED`. No performance chart. No auto-trade. No quantity.

This ticket **cannot** promote a model, show win %, or flip File A first CONFIRMED.

---

## 0.1 Outcome (done = observed)

1. One GET returns PIT **homework** for the latest hash-matched S8 run: per shortlist symbol a STO-017 observation (status, MFE/MAE, bars, fill policy, costs flag, censor reason).
2. `validationStatus=PIT_NOT_APPROVED`. `confirmedCount=0`. No route returns a win-rate, hit-rate, Brier, ECE, or equity curve.
3. Future bars with `available_at` after the S8 `asOf` only. Signal-day close fill **rejected**. Fill = **next session open** after `available_at` (declared `EntryPolicyV1`).
4. Incomplete horizon → `CENSORED` + cutoff, **never** forced LOSS/0 (T-087). Delist → `DELISTED`, not a zero price. Same-bar stop+target → **stop-first** (File A STO-017).
5. Manual notes cannot enter calibration stats (T-109). POST 405. No broker.
6. T-059 fixture: current-universe-only backtest **fails**. T-060: revised value unavailable at simulation time **fails**. T-063: UI has no performance chart.
7. §9 GATES all pass.

---

## 0.2 Forbidden

- Broker, OMS, OpenAlgo ExecutionProvider, Telegram, paper/live orders (REJ-010 / REJ-011).
- Quantity, Kelly, SPAN, “final_qty”.
- `PIT_APPROVED=true`, `validationStatus=PIT_APPROVED`, or any UI that looks like a scoreboard.
- Combined_Score, win %, P(win), EV, accuracy, “this setup works 62%”.
- yfinance / paid vendor / scraped unofficial candles as the PIT series.
- Signal-day close fill; using bars whose `available_at` ≤ decision time.
- Imported TradingView/PK/upstream backtest returns as truth (REJ-009).
- Writing Hybrid `predicted_p` / `realised_p` (those stay None in `hybrid_v2/stages/s9_attribution.py` — **different S9**, story overlay, do not merge).
- Auto-trade, scheduler that places orders, or flipping `sourceActivationReady`.
- DuckDB as default store (POST-HYB-06).

---

## 1. What S9 is (File A §9 wins)

| Stage | ID | Work | Ceiling |
|---|---|---|---|
| **S9** | `SEL-010` | Offline PIT labels, walk-forward evaluation, calibration/drift/demotion **artifacts** | Validation artifacts only, never live auto-trading |
| **R16** | PK8 | Full PIT approval before performance UI | **Not this ticket** — homework only |
| **R18** | model gov | Promotion / drift / demotion process | **Not this ticket** |

| This ticket IS | This ticket is NOT |
|---|---|
| STO-017 observations on free NSE EOD | A trading engine |
| Right-censored MFE/MAE (STO-015) | Win-rate product |
| Leakage + survivorship **tests that can fail** | `PIT_APPROVED` |
| Hidden Validation tab copy | Scanner Lab performance chart (UI-009) |

File A §9.3: FMR story “S9 radar/inspector/PIT” is **narrative**. Hybrid V2 `stages/s9_attribution.py` is an **empty overlay schema**. Code this ticket as **File A `SEL-010`**. Do not invent a third S9.

---

## 2. Module (keep these names)

`D:\TrendForge\backend\trendforge_api\selection\s9_pit_homework.py`  
Optional tiny helper (not a second engine): `backend/trendforge_api/validation/outcomes.py` that **calls** existing `validation_engine.label_price_path` and/or `hybrid_v2.as_lab.triple_barrier.label_event`.

Do **not** rewrite the harmonic backtester. Do **not** persist Hybrid attribution numbers.

| Piece | Contract |
|-------|----------|
| Schema | `trendforge.s9-pit.v1` |
| Profile | `PRF-S9-PIT-HOMEWORK` version `1.0.0` |
| Ceiling | `LIVE_S9_PIT_NOT_APPROVED` |
| `validationStatus` | always `PIT_NOT_APPROVED` |
| `sourceActivationReady` | always `false` |
| `canUnlockConfirmed` | always `false` |
| `confirmedCount` | `0` |
| Frozen pydantic | camelCase aliases, `frozen=True` |

### 2.1 Entry policy (versioned, required)

Live S7 idea cards have **null** entry/stop/qty. File A still requires an entry policy for observations.

```text
entryPolicyId = NEXT_SESSION_OPEN_AFTER_AVAILABLE_AT
fill          = next official NSE cash session OPEN after S8 asOf/available_at
horizon       = 5 completed sessions (versioned; store on the batch)
direction     = S7 evidenceDirection; UNKNOWN/FLAT → status NO_ENTRY
geometry      = if S4 invalidationCondition is a parseable price, pass as stop
                into validation_engine.label_price_path
                else RESEARCH_PROXY_ATR using TripleBarrierSpec
                (mfe_atr=1.5, mae_atr=-1.0, fill=next_open) — labelled PROXY
                never "calibrated stop"
```

Reject `fill=signal_close` in code (hybrid upgrade 19 + File A leakage).

### 2.2 Status vocabulary (STO-017)

```text
WIN                         target / MFE barrier before MAE (stop-first if both one bar)
LOSS                        stop / MAE barrier first
CENSORED                    horizon not complete; store cutoff; never coerce to 0
INVALIDATED_BEFORE_ENTRY    structure invalidation before fill bar
NO_ENTRY                    no direction, ban/REJECT, or missing fill bar
DELISTED                    identity lost / official delist in PIT universe
NO_FORWARD_SESSION          no later official bar on disk
ATR_MISSING                 proxy path cannot compute ATR
WAIT_COST_SCHEDULE          cost table missing — still persist observation,
                            but this ALONE already blocks PIT_APPROVED (locked anyway)
```

Manual annotation field: `annotationOnly=true`, **excluded** from any list used as “outcomes” (T-109). No live POST to write WIN/LOSS as truth.

### 2.3 Bars and costs (free NSE only)

- Series: official **adjusted** cash EOD already produced by A4 + R14 CA join. Same instrument ids as S8. If UNADJUSTED / WAIT_CA → do not label WIN/LOSS; `CENSORED` or `WAIT_CA`.
- Only bars with `available_at` **strictly after** the S8 decision `available_at` / `asOf`.
- PIT universe: the S1 eligible set **as of that asOf**, not “who is listed today” (T-059).
- Costs: declared research placeholder schedule id `VAL-001-RESEARCH-PLACEHOLDER` (STT/slippage constants in a frozen dict on the batch). **Do not** pull broker contract notes. Missing schedule → cannot approve (already locked). T-062: an approval path without costs must fail — write that test even though approval is unreachable.
- Walk-forward this ticket: label the **latest** S8 run against whatever later sessions exist on disk (often 0–N days). That is enough for the mechanism. Do **not** claim multi-year purged WF (R16). If zero later sessions: every row `NO_FORWARD_SESSION` / `CENSORED` — still a valid homework GET.

### 2.4 Persist

Use existing `persist_selection_payload` under `PRF-S9-PIT-HOMEWORK`. Prefer **not** to add `selection_outcomes` table this ticket (durable new table needs explicit migration approval). If you must add it: append-only, documented migration, never overwrite.

Pin `sourceS8RunId` + S8 lineage hashes on the S9 payload. Hash mismatch vs current spine → 503; do not label a foreign run as latest.

### 2.5 Routes

```
GET  /api/v1/selection/pit-homework
GET  /api/v1/selection/pit-homework/{symbol}
GET  /api/v1/selection/scans/{run_id}/outcomes     # homework for that S8 run; 404 if none
POST /api/v1/selection/pit-homework                → 405
POST /api/v1/validation/approve                    → 405   (do not create an approve write)
```

No `winRate` field. If a caller asks, the DTO has `performanceUiAllowed=false` and `validationStatus=PIT_NOT_APPROVED`.

---

## 3. Frontend

- Inspector **Validation** tab (File A §13.2 item 9): show lock copy:

  `PIT homework — not approved. Path observations only. Not a win rate. Not an order.`

- List a few rows: symbol, S8 publicState, status, mfe/mae, censor reason. **No chart. No %.**
- File: `frontend/s9-pit-homework.js` + mount + adapter fetch name count = fetch count.
- Cache-bust `?v=20260824-s9-1`.
- Acceptance-check: script mounted; strings `PIT_NOT_APPROVED` or lock copy present; no `winRate` / `Combined_Score` / `PIT_APPROVED=true` in product JS.

Do not unhide performance views (UI-009 / T-063).

---

## 4. Tests (mandatory File A teeth)

`backend/tests/test_s9_pit_homework.py`

1. `validationStatus == PIT_NOT_APPROVED`; `confirmedCount==0`; no `winRate` key.
2. **T-059** survivorship: labeling with *today’s* listed names while a fixture name was eligible at `asOf` but later delisted must **not** drop it as if it never existed; current-constituent-only helper **fails**.
3. **T-060** leakage: a bar / revision with `available_at` after simulation time must not enter the label path.
4. **T-061** future feature beyond horizon cannot sit on the training/homework row as a live feature.
5. **T-062** a fake `PIT_APPROVED` without costs/slippage/delist fields is rejected (keep approval unreachable).
6. **T-087** incomplete horizon → `CENSORED`, mfe/mae still stored, not zeroed as LOSS.
7. **T-102** target/MFE hit before max horizon → `WIN` on a valid path; pre-entry leakage rejected.
8. **T-109** `annotationOnly` WIN cannot appear in `calibrationEligible` list (that list is empty this ticket).
9. Signal-day close fill rejected; `next_open` used.
10. Same-bar both barriers → LOSS / MAE-first.
11. REJECT/ban S8 row → `NO_ENTRY`, not WIN.
12. POST 405. S8 missing → 503/404 named, no invented labels.
13. POST-approve route 405 or absent.
14. No yfinance/openalgo import in `s9_pit_homework.py`.

Also no regression: `test_s8_persist_run.py`, `test_s7_state_gates.py`, `test_s6_family_resolution.py`. Default `pytest tests` collection must not error.

---

## 5. Docs

- `BUILD_STATUS.md`: S9 coded at `LIVE_S9_PIT_NOT_APPROVED`; R16/R18 still open; no performance UI.
- `VALIDATION.md`: observed GET, status counts (how many CENSORED vs NO_FORWARD_SESSION), `validationStatus`.
- Overlay: S9 row = CODED homework; weekly diary cadence still not planned.
- Throwaways: `D:\TrendForge\delete\s9_wip_2026-08-24\` only.
- GATES: `D:\TrendForge\delete\gates_s9_2026-08-24\GATES.md`.

---

## 6. Free-data note (do not open a broker)

Use last-good official artifacts already in TrendForge:

- NSE EOD bhavcopy / UDiFF cash, A4 adjusted bars, R14 CA factors, fo_secban, combineoi (ban/MWPL already on S8 rows).
- Later sessions: whatever additional EOD files the collector already stored **after** S8 `asOf`. If the calendar has no later session (weekend/holiday/same-day): honest `NO_FORWARD_SESSION`.
- Do **not** log into a broker “for historical”. Do **not** Yahoo. Missing file → UNKNOWN/CENSORED, never invent closes.

---

## 7. Audit after build (you must run)

```text
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s9_pit_homework.py tests/test_s8_persist_run.py tests/test_s7_state_gates.py -q --tb=short
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests -q --tb=no
# Known: at most the same 6 pre-existing failures. Zero NEW fails.

cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Live (restart :8000 after code):

```text
GET  /api/v1/selection/scans/latest              200
GET  /api/v1/selection/pit-homework              200; validationStatus=PIT_NOT_APPROVED
GET  /api/v1/selection/pit-homework/ABCAPITAL    200 or 404
POST /api/v1/selection/pit-homework              405
```

JSON must **not** contain: `winRate`, `hitRate`, `pWin`, `combinedScore`, `PIT_APPROVED` as true.

Grep:

```text
s9_pit_homework.py  — no yfinance, no place_order, no sourceActivationReady=True
frontend/s9-pit-homework.js — lock copy present; no win %
```

**Debug until GET observations hold.** File A S0–S9 research pipe is then **coded at WAIT/homework ceiling**. Still not live CONFIRMED. Still not R16 approved. Stop.

---

## 8. Debug catalog (every class — fix, do not skip)

| Symptom | Likely cause | Fix |
|---|---|---|
| All rows WIN | used signal close or today’s universe | next_open + as-of PIT universe |
| All LOSS with mae=0 | coerced unresolved → 0 | CENSORED + cutoff (T-087) |
| Win % in UI | copied Hybrid overlay | delete; lock copy only |
| `PIT_APPROVED` | eager promotion | freeze enum; no approve route |
| 503 forever | S8 lineage vs current hashes | persist S9 against **that** S8 runId; GET by run |
| `NO_FORWARD_SESSION` for all (weekday with later bhavcopy) | date tz / asOf midnight | compare session dates in IST, not wall clock |
| Delisted name vanished | survivorship bug | T-059 must fail the bad helper |
| Import yfinance “just for labels” | forbidden | use A4 last-good only |
| Hybrid V2 s9_attribution filled | wrong S9 | leave predicted_p None |
| Collection error `tests.test_m_factor_claims` | old relative import | fix; default pytest must collect |
| New full-suite fails | regression | revert unrelated; known 6 unchanged |
| Broker login “to get history” | out of product | stop; NSE zip is enough |
| SQLite locked / stale routes | two uvicorn | one process, restart after edits |

---

## 9. GATES (write + run before claiming done)

Create `D:\TrendForge\delete\gates_s9_2026-08-24\GATES.md`. Debug until green.

```text
G1 module
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from trendforge_api.selection.s9_pit_homework import SCHEMA_VERSION, PROFILE_ID, ACCEPTANCE_CEILING; print(SCHEMA_VERSION, PROFILE_ID, ACCEPTANCE_CEILING)"
EXPECT: trendforge.s9-pit.v1

G2 focused pytest
CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s9_pit_homework.py tests/test_s8_persist_run.py -q --tb=short
EXPECT: passed

G3 no broker / no win-rate / no activation
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from pathlib import Path; t=Path(r'D:\\TrendForge\\backend\\trendforge_api\\selection\\s9_pit_homework.py').read_text(encoding='utf-8'); assert 'yfinance' not in t.lower(); assert 'place_order' not in t; assert 'winRate' not in t; assert 'sourceActivationReady=True' not in t; print('S9_CLEAN')"
EXPECT: S9_CLEAN

G4 live homework locked
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/pit-homework')); vs=d.get('validationStatus') or d.get('validation_status'); print(vs); assert vs=='PIT_NOT_APPROVED'; assert d.get('confirmedCount', d.get('confirmed_count'))==0; assert 'winRate' not in d and 'win_rate' not in d; print('HOMEWORK_LOCKED')"
EXPECT: HOMEWORK_LOCKED

G5 POST 405 (PowerShell-safe runner — create `post405.py` in this ticket's
GATES folder with the same 6-line helper as the S7 prompt's G5)
CHECK: D:\TrendForge\.venv\Scripts\python.exe D:\TrendForge\delete\gates_s9_2026-08-24\post405.py http://127.0.0.1:8000/api/v1/selection/pit-homework
EXPECT: 405

G6 frontend lock
CHECK: node tests/acceptance-check.js
EXPECT: ok
CWD: D:\TrendForge\frontend
```

After G1–G6: File A S-flow is implemented at the **research ceiling**. Do not start R2-B activation, R16 `PIT_APPROVED`, or any broker ticket from this prompt.
