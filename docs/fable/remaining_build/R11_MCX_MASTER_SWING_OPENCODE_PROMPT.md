# OPENCODE BUILD PROMPT — File A R11 MCX master + swing RS/delivery gates
## Missing master → MCX WAIT · lot/tick/expiry/tender · swing RS/delivery EOD · PRF-005/006/007 empty if unready

Copy **this entire file**. Load skills. Think. Build. Run **§9 GATES**.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. `;` not `&&`.  
**Date: 2026-08-25.** After **R10** GATES (or in parallel if you do not share files). User skipped R9. Cash S7 path must **not** break.

Also read: `TRADE_GUIDANCE_LAW_2026-08-25.md`. File A PRF-005/006/007, FTR-028, MCX-002, CROSS-009 (FBIL ≠ live FX unlock).

Skills: `using-superpowers` → `unlazy` → `verification-before-completion` → `systematic-debugging` → `test-driven-development` → `requesting-code-review`.

Existing: `selection/mcx_contracts.py` (`evaluate_mcx_contract`), commodity context, `mcx_bhavcopy` often **stale**. Do not invent COMEX as gold proof.

---

## 0. Expected output (done = observed)

1. `GET /api/v1/selection/mcx-master` → readiness enum:  
   `MASTER_AND_LOCAL_CONTEXT_READY` | `WAIT_MCX_MASTER` | `WAIT_MCX_LOCAL_BARS` | `WAIT_MCX_STALE` | `WAIT_MCX_CALENDAR`.  
   `confirmedCount=0`. `canUnlockConfirmed=false` for MCX this ticket (PRF-005 still WAIT without named MCX activation — R2-B named **NSE** five only).  
2. Each contract row: symbol/instrument_id, lot, tick, expiry, DTE, tender/delivery window, `available_at`, source hash. Missing field → that name **WAIT**, not a guessed lot.  
3. `GET /api/v1/selection/mcx-master/{symbol}` 404 named if unknown. POST 405.  
4. Swing **cash** RS + delivery already exist in S3/S5 — this ticket **wires them as gates** on PRF-003/004: missing delivery → `WAIT_DELIVERY` on **swing** rows (not a second vote). Do not query delivery on intraday.  
5. S7: MCX symbols cannot be File A public CONFIRMED. They may show **guidance** WAIT + contract warning.  
6. UI: existing MCX mode / commodity panel shows **live** master status, not fixture gold. Copy: “MCX WAIT without official master+local bars.”  
7. Cash All Stocks / S7 CONFIRMED path **regression green**.

---

## 0.1 Flow (do not break cash)

```text
cash spine R1→R8 / S7   UNCHANGED
MCX branch:
  official MCX master + calendar last-good
    → mcx_contracts.evaluate_mcx_contract
    → local mcx_bhavcopy / local OI if present
    → READY context or WAIT_* 
    → never public CONFIRMED this ticket
FBIL USD/INR = delayed FX context; does not unlock MCX intraday
CFTC/WGC = delayed; cannot prove local gold
```

Hash-match MCX artifact to trading date or 503 `WAIT_MCX_LINEAGE`. Stale last-good = `WAIT_MCX_STALE` (honest), not fake READY.

---

## W. Folder map

```text
CREATE
  D:\TrendForge\backend\trendforge_api\selection\r11_mcx_live.py
  D:\TrendForge\backend\tests\test_r11_mcx_live.py
  D:\TrendForge\frontend\mcx-master.js
  D:\TrendForge\delete\gates_r11_mcx_2026-08-25\GATES.md
  D:\TrendForge\delete\r11_wip_2026-08-25\

EXTEND
  D:\TrendForge\backend\trendforge_api\selection\mcx_contracts.py   reuse evaluate_*
  D:\TrendForge\backend\trendforge_api\main.py
      GET /api/v1/selection/mcx-master
      GET /api/v1/selection/mcx-master/{symbol}
      POST 405
  D:\TrendForge\backend\trendforge_api\selection\s5_shortlist_enrichment.py
      delivery gate already EOD-only — assert swing WAIT_DELIVERY when missing (test)
  D:\TrendForge\backend\trendforge_api\selection\s7_state_gates.py
      PRF-005/006/007 still empty boards + WAIT_MCX_MASTER if master not READY
  frontend/index.html   #mcxMasterPanel (commodity / MCX mode — no new nav group)
  frontend/selection-live-adapter.js  +1 fetch
  frontend/tests/acceptance-check.js
  frontend/app.js        if MCX mode still paints fixture, delegate to TrendForgeMcxMaster
  docs/BUILD_STATUS.md, VALIDATION.md, DECISIONS.md (D-0xx MCX_WAIT_WITHOUT_MASTER)
  remaining_build/README.md, fileindex.md
```

Do not download random MCX HTML. Use last-good `mcx_bhavcopy` / master parser already in inventory. If empty: WAIT, `triedSourceKeys[]`.

---

## 1. Contract DTO

`schema trendforge.mcx-master.v1`  
`PROFILE_ID PRF-R11-MCX-WAIT`  
`ACCEPTANCE_CEILING LIVE_MCX_WAIT_WITHOUT_NAMED_ACTIVATION`

Rows frozen pydantic camelCase. `executable=false`. Lot unknown → qty guidance 0 (`WAIT_LOT`) if research-qty asked for MCX.

Swing RS: reuse `features/relative_strength.py` or S3 RS — **gate** only, not a new score.

---

## 2. UI

`mcx-master.js?v=20260825-r11-1`  
`TrendForgeMcxMaster.apply(batch)`  
IDs: `#mcxMasterPanel`, `#mcxMasterMeta`.  
MCX segment `data-mode="mcx"` must call `load()`/`apply`, not fixture gold.

Copy: “MCX contract safety — WAIT without master. Not COMEX. Not an order.”

---

## 3. Tests `test_r11_mcx_live.py`

1. No master artifact → READY count 0, ceiling WAIT.  
2. Lot/tick/expiry missing → WAIT, not invented numbers.  
3. Tender window hit → WAIT_TENDER / veto.  
4. FBIL cannot set MCX public CONFIRMED.  
5. CFTC cannot.  
6. POST 405.  
7. S7 cash tests still pass; `test_s7_state_gates` CONFIRMED law unchanged.  
8. Delivery on INTRADAY still forbidden (existing S5).

---

## 4. GATES

`D:\TrendForge\delete\gates_r11_mcx_2026-08-25\GATES.md`

```text
G1 import
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from trendforge_api.selection.r11_mcx_live import SCHEMA_VERSION, ACCEPTANCE_CEILING; print(SCHEMA_VERSION, ACCEPTANCE_CEILING)"
EXPECT: trendforge.mcx-master.v1
CWD: D:\TrendForge\backend

G2 pytest
CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_r11_mcx_live.py tests/test_s7_state_gates.py tests/test_s5_shortlist_enrichment.py -q --tb=short
EXPECT: passed
CWD: D:\TrendForge\backend

G3 live
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/mcx-master', timeout=60)); print(d.get('acceptanceCeiling') or d.get('acceptance_ceiling'), d.get('confirmedCount', d.get('confirmed_count'))); print('MCX_OK')"
EXPECT: MCX_OK

G4 frontend
CHECK: node tests/acceptance-check.js
EXPECT: 0 failed checks
CWD: D:\TrendForge\frontend
```

If live master is stale, G3 still 200 with WAIT_* — that is production-honest. Stop. Next: R15 Scanner Lab UI (uses R10 panel if present).
