# OPENCODE BUILD PROMPT — 1/4 S9 UI polish (SEL-010 display)
## Validation tab · join S8 run · **trade guidance: win %, chart, APPROVED-for-guidance**

**Also read:** `docs/fable/remaining_build/TRADE_GUIDANCE_LAW_2026-08-25.md` (user revoked the old hide-win% rule).

Copy **this entire file**. Load skills. Think. Build. Run **§9 GATES**. Debug every fail.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. `;` not `&&`.  
**Date: 2026-08-25.** Ticket **1 of 4**. Do **not** start tickets 2–4 here.

Skills: `superpowers/using-superpowers` → `unlazy` → `superpowers/verification-before-completion` → `superpowers/systematic-debugging` → `superpowers/requesting-code-review`.

Authority: File A §9 S9 / UI-009 / T-063 / T-109. Backend already live: `selection/s9_pit_homework.py`, `GET /api/v1/selection/pit-homework{,/symbol}`, POST 405.

---

## 0. This ticket IS / IS NOT

| IS (needed) | IS NOT |
|---|---|
| Paint S9 homework in inspector **Validation** tab | Rebuilding the whole S9 engine (ticket 2 adds bars) |
| Join rows to **S8 `runId`** | Live broker `placeorder` (ticket 4 paper OMS) |
| **Guidance win % + small path chart** from labeled rows | Pretending File A public CONFIRMED |
| **`PIT_APPROVED_FOR_GUIDANCE`** copy when any WIN/LOSS exist; else `PIT_NOT_APPROVED` | Silent `PIT_APPROVED` with no rows |
| Adapter fetch + apply names = count | Ticket 3 R12 / ticket 4 R2-B |

If GET `/pit-homework` is missing: **stop**. Do not fake labels from S7.

---

## 0.1 Outcome (observed)

1. Inspector Validation tab shows homework **and trade guidance**:
   `PIT homework — trade guidance. Not a live order.`
2. List: symbol, S8 publicState, status, MFE/MAE, censor reason, **source S8 runId**.
3. **Guidance win rate** = WIN / (WIN+LOSS) among resolved rows only; CENSORED excluded from the denominator. Label: `guidanceWinRate (not a promise)`. If no WIN+LOSS yet, show `n/a — waiting later bars (ticket 2)`.
4. **Small chart**: counts of WIN / LOSS / CENSORED / NO_FORWARD_SESSION (bar or spark). Not a broker equity curve if n=0.
5. Status chip: `PIT_NOT_APPROVED` until resolved count ≥ 1, then `PIT_APPROVED_FOR_GUIDANCE` (guidance only; File A product `PIT_APPROVED` still false until ticket 2 gate).
6. Adapter fetch `/api/v1/selection/pit-homework`. Fetch count = apply names (15 → **16**).

---

## W. Folder map (OWNS)

```text
CREATE
  D:\TrendForge\frontend\s9-pit-homework.js
  D:\TrendForge\delete\gates_s9_ui_2026-08-25\GATES.md

EXTEND
  D:\TrendForge\frontend\index.html          mount script + Validation mount IDs
  D:\TrendForge\frontend\selection-live-adapter.js
  D:\TrendForge\frontend\tests\acceptance-check.js
  D:\TrendForge\frontend\styles.css          small lock styles only
  D:\TrendForge\docs\BUILD_STATUS.md
  D:\TrendForge\docs\VALIDATION.md
  D:\TrendForge\docs\fable\S0_S9_RUN_OVERLAY_MAP_2026-08-24.md   S9 row CODED UI
```

Do **not** invent a nav group. Do **not** put product code under `delete/`. Do **not** add React.

### IDs

| ID | Where |
|---|---|
| `#q5ValidationLock` | already exists — **replace** fixture sentence with S9 lock copy + runId |
| `#s9PitHomeworkPanel` | inside `#q5Inspector` after the lock line |
| existing `#q5Inspector` | no new drawer |

Scripts: `s9-pit-homework.js?v=20260825-s9-1`. Cache-bust adapter.

---

## 1. UI contract

`window.TrendForgeS9PitHomework = { apply, CONTRACT }`  
CONTRACT `trendforge.s9-pit.v1`

`apply(batch)`:

- If `batch` null/503: panel `WAIT_S9_NOT_READY` + “needs a persisted S8 run”.
- Always show **guidance** strip: `guidanceWinRate`, WIN/LOSS/CENSORED counts, `PIT_APPROVED_FOR_GUIDANCE` or `PIT_NOT_APPROVED`.
- Table of first N rows (e.g. 20): symbol, s8PublicState, status, mfePercent, maePercent, censorReason.
- Meta: `sourceS8RunId`, `acceptanceCeiling`. Copy: “Trade guidance — not a guaranteed win. Not an order.”
- **Do render** `guidanceWinRate`. Do **not** label it Combined_Score or live P(win) without the word **guidance**.

Join: S8 history panel already has `runId`. S9 meta must show the **same** `sourceS8RunId` when both loaded. If they differ, show `WAIT_S9_S8_MISMATCH` — do not mix runs.

---

## 2. Adapter

Add **one** fetch:

`fetchOptionalJson("/api/v1/selection/pit-homework").catch(() => null)`

Then `TrendForgeS9PitHomework.apply(s9Homework)` **after** S8 apply.

Promise.all destructuring names **must** match fetch count.

---

## 3. Tests

Acceptance-check.js:

- script mounted with cache-bust  
- `#s9PitHomeworkPanel` exists  
- adapter contains `/api/v1/selection/pit-homework` and `TrendForgeS9PitHomework`  
- s9 js has guidance copy + `guidanceWinRate`  
- Combined_Score still absent; `place_order` not called  
- no File A `publicState = CONFIRMED` from this file

Do not weaken `test_s9_pit_homework.py`.

---

## 4. Forbidden vs needed

**Needed:** guidance win %, guidance chart, `PIT_APPROVED_FOR_GUIDANCE`.  
**Forbidden:** live `placeorder`, Combined_Score as state, flipping `sourceActivationReady` in this ticket. Yahoo/OpenAlgo PIT series = **ticket 2**.

---

## 5. GATES

`D:\TrendForge\delete\gates_s9_ui_2026-08-25\GATES.md`

```text
G1 GET exists
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from trendforge_api.selection.s9_pit_homework import SCHEMA_VERSION, VALIDATION_STATUS; print(SCHEMA_VERSION, VALIDATION_STATUS)"
EXPECT: trendforge.s9-pit.v1
CWD: D:\TrendForge\backend

G2 frontend
CHECK: node tests/acceptance-check.js
EXPECT: 0 failed checks
CWD: D:\TrendForge\frontend

G3 adapter
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from pathlib import Path; t=Path(r'D:\\TrendForge\\frontend\\selection-live-adapter.js').read_text(encoding='utf-8'); assert '/api/v1/selection/pit-homework' in t; assert 'TrendForgeS9PitHomework' in t; print('S9_UI_WIRED')"
EXPECT: S9_UI_WIRED
```

Stop. Next file is ticket **2** (`S8_DAYS_R16_R18_PIT_APPROVED_OPENCODE_PROMPT.md`) only after GATES green.
