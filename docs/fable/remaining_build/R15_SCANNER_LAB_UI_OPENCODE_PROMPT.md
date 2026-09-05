# OPENCODE BUILD PROMPT — File A R15 Scanner Lab UI (PK7 / UI-007 / PK-013)
## One lab: definitions · pipe flow · native/PK parity · no radar column explosion · guidance not Combined_Score

Copy **this entire file**. Load skills. Think. Build. Run **§9 GATES**.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. `;` not `&&`.  
**Date: 2026-08-25.** Build **after R10** (pipe panel). R11 may be parallel. R9 skipped. Do **not** explode All Stocks columns.

Also read: `TRADE_GUIDANCE_LAW_2026-08-25.md`. File A §13.2 item 5 Scanner Lab tab. S9 Validation tab already owns PIT guidance win % — **do not duplicate a second scoreboard on All Stocks**.

Skills: `using-superpowers` → `unlazy` → `verification-before-completion` → `systematic-debugging` → `requesting-code-review`.

Existing chrome: `#q5Inspector` `#q5InspectorTabs` `#q5InspectorPanel`, `#scannerRunButton`, `#scannerPipePanel` if R10 shipped, S9 `#s9PitHomeworkPanel`. Product fixture All Stocks.

---

## 0. Expected output (done = observed)

1. Inspector has a **Scanner Lab** tab (add to `#q5InspectorTabs` if tabs are JS-built — wire in `q5-contract.js` / inspector renderer **or** a dedicated `scanner-lab.js` that registers the tab).  
2. Lab shows, without adding columns to `#radarList`:  
   - native / pipe definitions (id, version, hash, family)  
   - last pipe run stage flow (in/out/drop reasons) from R10 GET  
   - per-symbol match/fail for selected name  
   - PK shadow parity: `PK_SHADOW` / `PARITY_OK` / `PARITY_UNKNOWN` — **cannot** change S7  
   - correlation warning: `correlated_possible`  
3. `#scannerRunButton` = **refresh GET** of pipe/native latest, **not** collector dual-start, **not** `placeorder`.  
4. Guidance: “matched — trade guidance, not an order.” Optional join to S9 `guidanceWinRate` **inside the lab only** (already labelled not a promise).  
5. All Stocks table column count **does not increase**. Matches stay chips on inspector / lab.  
6. Adapter names = fetches. If R10 fetch already exists, Lab **reuses** it — do not fetch twice.  
7. Docs updated. Flow S7/S8/qty/OMS/S9 still green.

---

## 0.1 Flow (must not break)

```text
User opens inspector → Scanner Lab tab
  reads GET /scanners/pipes/run/latest   (R10)
  reads GET /scanners/definitions        (R10 or R8 if present)
  reads GET /scanners/native-core        (optional; WAIT if R8 absent)
  reads GET /pit-homework                (already adapter — reuse apply)
  paints lab only
S7 publicState unchanged
All Stocks unchanged columns
```

If R10 GET 503: lab shows `WAIT_R10_PIPE` — do not invent survivors.

---

## W. Folder map

```text
CREATE
  D:\TrendForge\frontend\scanner-lab.js
  D:\TrendForge\delete\gates_r15_lab_2026-08-25\GATES.md
  D:\TrendForge\delete\r15_wip_2026-08-25\

EXTEND
  D:\TrendForge\frontend\index.html
      #scannerLabPanel inside #q5Inspector (after S9 or as tab body)
      mount scanner-lab.js?v=20260825-r15-1
  D:\TrendForge\frontend\q5-contract.js and/or product-fixture.js
      register tab id scanner-lab without new radar columns
  D:\TrendForge\frontend\selection-live-adapter.js
      TrendForgeScannerLab.apply(...) using payloads already fetched
      add fetch ONLY if R10/native routes not already in Promise.all
  D:\TrendForge\frontend\app.js
      scannerRunButton → adapter reload, not /api/scanners legacy fire
  D:\TrendForge\frontend\tests\acceptance-check.js
  D:\TrendForge\frontend\styles.css
  backend: none required unless a thin GET /api/v1/scanners/lab-bundle is kinder
      (optional BFF aggregating definitions+pipe+pk shadow — POST 405)
  docs/BUILD_STATUS.md, VALIDATION.md, DECISIONS.md (D-0xx R15_LAB_NO_RADAR_INFLATION)
  remaining_build/README.md, fileindex.md
```

Prefer **optional** `GET /api/v1/scanners/lab-bundle` so the lab is one 200 with named 503s inside. If you add it, adapter +1 and drop duplicate pipe fetch.

---

## 1. UI contract

`window.TrendForgeScannerLab = { apply, CONTRACT: "trendforge.scanner-lab.v1" }`

IDs: `#scannerLabPanel`, `#scannerLabTabs` (Definitions | Pipe flow | Symbol | PK shadow), `#scannerLabBody`.

Do **not** new left-nav. Do **not** add win % on All Stocks (S9 tab already has guidance win %). Lab may show S9 guidanceWinRate as a **footnote** for the selected symbol only.

`#scannerRunButton` visible label: “Refresh lab (GET)” — 405 if anything POSTs run.

---

## 2. Tests

Acceptance-check:

- `#scannerLabPanel` exists  
- `scanner-lab.js?v=20260825-r15-1` mounted  
- adapter `TrendForgeScannerLab`  
- All Stocks table: no new `<th>` for scanner counts (assert current headers unchanged or lab-only IDs)  
- no Combined_Score  
- scannerRunButton does not contain `place_order`  
- S7 CONFIRMED still only from S7 module  

Backend: if lab-bundle exists, POST 405; bundle `confirmedCount=0`.  
Regression: `test_r10_pipe_dsl.py` if present, `test_s7_state_gates.py`.

---

## 3. Production-grade checks (flow not broken)

After code:

```text
GET /api/v1/selection/s7-state
GET /api/v1/selection/scans/latest
GET /api/v1/scanners/pipes/run/latest     (R10)
GET /api/v1/selection/mcx-master          (R11 if live; 503 WAIT ok)
GET /api/v1/selection/pit-homework
GET /api/v1/selection/guidance-oms/ABCAPITAL   if ticket 4 present
```

All: 200 or named 503/404. `confirmedCount` still obeys R2-B last-goods. Adapter fetch count = apply names.

---

## 4. GATES

`D:\TrendForge\delete\gates_r15_lab_2026-08-25\GATES.md`

```text
G1 frontend
CHECK: node tests/acceptance-check.js
EXPECT: 0 failed checks
CWD: D:\TrendForge\frontend

G2 adapter lab
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from pathlib import Path; t=Path(r'D:\\TrendForge\\frontend\\scanner-lab.js').read_text(encoding='utf-8'); a=Path(r'D:\\TrendForge\\frontend\\selection-live-adapter.js').read_text(encoding='utf-8'); assert 'TrendForgeScannerLab' in t and 'TrendForgeScannerLab' in a; assert 'Combined_Score' not in t; print('LAB_WIRED')"
EXPECT: LAB_WIRED

G3 s7 still owner
CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s7_state_gates.py -q --tb=line
EXPECT: passed
CWD: D:\TrendForge\backend
```

Stop. Next File A after this pack: **R13** remaining scanners, **R17** OpenAlgo live RO shadow, or **data ops** to refresh NSE last-goods so D-053 CONFIRMED can leave 0. Not R9.
