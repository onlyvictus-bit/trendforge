# OPENCODE BUILD PROMPT — 2/4 accumulate S8 days + R16/R18 PIT gate
## Later bars · **auto-approve guidance** · Yahoo/OpenAlgo as **proxy PIT series** · guidance win % / charts

**Also read:** `docs/fable/remaining_build/TRADE_GUIDANCE_LAW_2026-08-25.md`

Copy **this entire file**. Load skills. Think. Build. Run **§9 GATES**.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. `;` not `&&`.  
**Date: 2026-08-25.** Ticket **2 of 4**. Requires ticket 1 UI **or** at least live `GET /pit-homework`. Do **not** implement R12 or R2-B CONFIRMED here.

Skills: `using-superpowers` → `unlazy` → `verification-before-completion` → `systematic-debugging` → `test-driven-development` → `requesting-code-review`.

Authority: File A S9 / R16 / R18 / FTR-034 / STO-015 / STO-017 / UI-009 / T-059..063 / T-087 / T-102 / T-109. Hybrid File B §16.11 only as formula library. Existing: `s9_pit_homework.build_s9_pit_homework(..., future_bars_by_symbol=)`.

---

## 0. Two phases in ONE ticket (do not skip phase A)

**Phase A — accumulate (must ship even if zero later days exist today)**  
Wire **official A4 / bhavcopy bars with `available_at` strictly after S8 `asOf`** into `build_s9_pit_homework`. Persist homework under `PRF-S9-PIT-HOMEWORK`. Honest `NO_FORWARD_SESSION` when the calendar has no later session.

**Phase B — R16/R18 **guidance approval** (user: include auto-approve + charts)**  
`GET /pit-gate` must compute `guidanceWinRate`, session counts, blockers.  
**Auto-approve for guidance** when: horizon-complete rows ≥ declared min (default 20) **and** T-059/T-060 fixtures pass **and** costs placeholder declared. Then set `validationStatus=PIT_APPROVED_FOR_GUIDANCE` and `performanceUiAllowed=true` for the **guidance** chart only.  
Official NSE EOD = authority PIT series. **Yahoo and OpenAlgo history are allowed as extra guidance series** (`kind=PROXY` / `BROKER_ORIGINATED`); they must not replace NSE as authority. If NSE later bars exist, they win. If only proxy series exist, labels are guidance-only (`evidenceKind=PROXY`).

---

## 0.1 Outcome (observed)

1. GET `/pit-homework` loads later bars from **official cash history** (A4 last-good), not Yahoo, not OpenAlgo.  
2. Bars with `available_at <= S8 asOf` never enter labels (T-060).  
3. Incomplete 5-session horizon → `CENSORED` + cutoff, not LOSS (T-087).  
4. GET `/api/v1/selection/pit-gate` returns: `validationStatus` (`PIT_NOT_APPROVED` or `PIT_APPROVED_FOR_GUIDANCE`), `guidanceWinRate`, `eligibleSessionCount`, `blockers[]`, `performanceUiAllowed` (true only for guidance charts), `series[]` (`OFFICIAL_NSE`, optional `PROXY_YAHOO`, `BROKER_OPENALGO`).  
5. **Needed:** `guidanceWinRate` + guidance chart. Not Combined_Score.  
6. POST `/pit-gate/approve` may exist for **manual** override; auto-approve already runs when minima pass. No live `placeorder`.

---

## W. Folder map

```text
CREATE / EXTEND
  D:\TrendForge\backend\trendforge_api\selection\s9_pit_homework.py
      load_future_bars_from_a4(s8_as_of, symbols) — official only
  D:\TrendForge\backend\trendforge_api\selection\pit_gate.py   NEW
      PitGateV1: status, session counts, blockers, performanceUiAllowed=false
  D:\TrendForge\backend\trendforge_api\main.py
      GET /api/v1/selection/pit-gate   POST 405
      pit-homework GET must call load_future_bars_from_a4
  D:\TrendForge\backend\tests\test_s9_pit_homework.py   extend T-059/060/087
  D:\TrendForge\backend\tests\test_pit_gate.py          NEW
  D:\TrendForge\frontend\s9-pit-homework.js             show session count + blockers
  D:\TrendForge\delete\gates_s8_days_pit_2026-08-25\GATES.md
  docs/BUILD_STATUS.md, docs/VALIDATION.md, DECISIONS.md (D-0xx PIT_GATE_LOCKED)
```

Reuse `cash_a4_history` as **authority**. If data-lane is OPENALGO_RO, also pull OpenAlgo `/history` as guidance overlay. Optional Yahoo only if an existing project helper exists — label PROXY, never authority. Do **not** new DuckDB.

---

## 1. Later-bar loader

```text
for each S8 symbol:
  bars = official adjusted EOD with available_at > s8.asOf (timezone-aware IST/UTC consistent)
  take next 5 completed sessions (HORIZON_SESSIONS)
  if 0 sessions: status NO_FORWARD_SESSION
  if 1..4: label_price_path then CENSORED if UNRESOLVED (T-087)
```

Fill policy remains next-session **open** after asOf (already in module). Signal-day close fill stays rejected.

Survivorship: a name eligible on S8 asOf that later disappears stays in the homework as `DELISTED` / censored — **never dropped** (T-059). Write a fixture that fails a “today’s listings only” helper.

---

## 2. PIT gate (R16/R18 ceiling this ticket)

`GET /api/v1/selection/pit-gate`

```text
validationStatus        PIT_NOT_APPROVED | PIT_APPROVED_FOR_GUIDANCE
performanceUiAllowed    true when guidance-approved
guidanceWinRate         WIN/(WIN+LOSS) or null
s8RunCount, labeledRowCount, horizonCompleteCount
blockers[]              WAIT_INSUFFICIENT_SESSIONS, …
autoApproveGuidance     true when minima pass (user requested auto-approve)
```

Promotion rules (document in DECISIONS; **do not flip in code this ticket** unless every blocker is empty **and** user added an explicit `TRENDFORGE_PIT_APPROVE=1` **and** tests prove T-059..063):

- Default: never APPROVED.  
- If you implement the env flip: still **forbid** win-% fields; only then may Validation tab say “PIT_APPROVED — charts still hidden until UI-009 product work”. Prefer **not** to flip.

R18 (drift/demotion) = schema stub only: `driftStatus=NOT_EVALUATED`. No model lab unlock.

---

## 3. Forbidden vs needed

**Needed:** guidance win %, charts, auto-approve-for-guidance, Yahoo/OpenAlgo as **proxy** PIT series.  
**Forbidden:** treating proxy series as NSE authority; live `placeorder`; flipping File A `sourceActivationReady` (ticket 4).

---

## 4. Tests

1. Future bar `available_at <= asOf` excluded.  
2. Zero later sessions → all `NO_FORWARD_SESSION`, GET still 200.  
3. Unresolved horizon → CENSORED not LOSS.  
4. Delisted-at-asOf name not dropped (T-059).  
5. pit-gate exposes `guidanceWinRate` (may be null).  
6. Auto-approve guidance when min complete rows hit in a fixture.  
7. Proxy series cannot override official `available_at`.  
8. Existing S8/S7/dual-lane tests still pass. No live placeorder.

---

## 5. GATES

`D:\TrendForge\delete\gates_s8_days_pit_2026-08-25\GATES.md`

```text
G1 pytest s9 + pit-gate
CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s9_pit_homework.py tests/test_pit_gate.py -q --tb=short
EXPECT: passed
CWD: D:\TrendForge\backend

G2 live homework guidance fields
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/pit-homework', timeout=120)); print(d.get('validationStatus') or d.get('validation_status')); print('S9_GUIDANCE')"
EXPECT: S9_GUIDANCE

G3 pit-gate
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/pit-gate', timeout=60)); print(d.get('validationStatus') or d.get('validation_status'), d.get('guidanceWinRate') or d.get('guidance_win_rate')); print('GATE_GUIDANCE')"
EXPECT: GATE_GUIDANCE
```

Stop. Ticket **3** (R12 claims) is independent of APPROVED. Ticket **4** (CONFIRMED) is independent of APPROVED. Do not bundle them.
