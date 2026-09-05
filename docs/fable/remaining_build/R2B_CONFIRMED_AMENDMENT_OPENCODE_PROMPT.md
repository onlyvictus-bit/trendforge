# OPENCODE BUILD PROMPT — 4/4 R2-B activation amendment (live CONFIRMED + guidance OMS)
## Execute the draft · PRF-003 EOD CONFIRMED · **paper OMS / order preview** · **intraday guidance CONFIRMED**

**Also read:** `docs/fable/remaining_build/TRADE_GUIDANCE_LAW_2026-08-25.md`

Copy **this entire file**. Load skills. **This is the only ticket that may emit File A CONFIRMED.** Do it last. Requires explicit operator intent (you have it: this prompt).

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. `;` not `&&`.  
**Date: 2026-08-25.** Ticket **4 of 4**. Read first: `docs/fable/remaining_build/FILE_A_R2B_ACTIVATION_AMENDMENT_DRAFT.md` and `selection/r2b_live.py`.

Skills: `using-superpowers` → `unlazy` → `verification-before-completion` → `systematic-debugging` → `test-driven-development` → `requesting-code-review`.

---

## 0. Hard law + **needed trade guidance** (user 2026-08-25)

- **File A public CONFIRMED** for **PRF-003 NSE swing EOD** on the five named official sources (draft §A). Ban / WAIT_CA / incomplete scan → never public CONFIRMED.  
- MWPL % is not a confirming **authority**. Index close is companion.  
- **Needed — guidance OMS:** paper ticket (side, researchQuantity, entry/stop, notional, remaining funds) + **OpenAlgo order JSON preview**.  
- **Needed — place_order path:** implement the client call, but **do not fire** unless `TRENDFORGE_LIVE_ORDERS=1` **and** data-lane `OPENALGO_RO` **and** UI `#armLiveOrders` is on (default **off**). Default boot = preview only.  
- **Needed — intraday guidance CONFIRMED:** when `intradayMode` is `ON_FREE` or `OPENALGO`, S7 may set `intradayGuidanceConfirmed=true` (PRF-001 shape, closed **or** last OpenAlgo bar labeled PROXY). File A **public** CONFIRMED for intraday stays off unless a named intraday source is later authorized (not in the five EOD keys).  
- Options-only public CONFIRMED still no; options `guidanceConfirmed` comes from ticket 3.

If live last-good for any of the five is missing: **do not flip globally**. Keep `sourceActivationReady=false` and write blockers.

---

## 0.1 Named confirm-path (draft §A — only these)

1. `nse_bhavcopy_eod`  
2. `nse_fno_ban`  
3. `nse_fo_bhavcopy`  
4. `nse_index_close_eod` (companion)  
5. `nse_corporate_filings_actions` (R14)

When **all five** have current official last-good **and** R14 join is clean **and** S7 `draftConfirmedEligible` **and** PRF-003 required families support **and** activation ledger says authorized:

S7 may set `publicState=CONFIRMED` for that symbol. `confirmedCount` may leave 0.

Otherwise WAIT/WATCH/REJECT as today.

---

## 0.2 Outcome (observed)

1. `GET /api/v1/selection/named-activation` shows those five as authorized **or** named WAIT_PROOF / NOT_AUTHORIZED. `authorizedCount` matches.  
2. Compiler/runtime `sourceActivationReady` is **true only if** the five are authorized; else false. Do not hardcode true.  
3. Live `GET /s7-state`: `confirmedCount` may be >0 for PRF-003 EOD. Rows carry why[], nextTrigger/invalidation, `researchQuantity`, **`guidanceOrderTicket`** (preview). `executable` follows live-arm flags (default false).  
4. `GET /api/v1/selection/guidance-oms/{symbol}` returns paper OMS card. POST `/guidance-oms/preview` 200. POST `/guidance-oms/place` → **409 `LIVE_ORDERS_ARMED_OFF`** unless env+switch+arm.  
5. Intraday: `intradayGuidanceConfirmed` visible; public CONFIRMED still EOD-only this amendment.  
6. Draft file marked **EXECUTED**. Overlay: public CONFIRMED = PRF-003 EOD; guidance OMS + intraday guidance included.

---

## W. Folder map

```text
EXTEND
  D:\TrendForge\backend\trendforge_api\selection\r2b_live.py
  D:\TrendForge\backend\trendforge_api\selection\s7_state_gates.py
      allow CONFIRMED when activation true AND draftConfirmedEligible AND PRF-003
      keep model_validator: CONFIRMED forbidden when sourceActivationReady is false
  D:\TrendForge\backend\trendforge_api\source_inventory_compiler.py  only if ledger must expose ready
  D:\TrendForge\backend\tests\test_r2b_live_named_activation.py
  D:\TrendForge\backend\tests\test_s7_state_gates.py   add CONFIRMED-allowed + CONFIRMED-forbidden cases
  D:\TrendForge\docs\fable\remaining_build\FILE_A_R2B_ACTIVATION_AMENDMENT_DRAFT.md  mark EXECUTED
  D:\TrendForge\docs\DECISIONS.md, BUILD_STATUS.md, VALIDATION.md
  D:\TrendForge\delete\gates_r2b_confirmed_2026-08-25\GATES.md
  frontend/s7-state.js  CONFIRMED chip + “research CONFIRMED — guidance OMS below”
  frontend/guidance-oms.js  paper ticket + Arm live (default off)
  GET/POST guidance-oms routes in main.py
```

Do not widen the named list. Do not enable OpenAlgo as confirm authority (OPN-003). Do not unlock PRF-001/002 intraday.

---

## 1. Implementation sequence

1. Tests first: fixture with activation false → 0 CONFIRMED (already).  
2. Fixture with five sources authorized + PRF-003 families + clean R14 → CONFIRMED allowed.  
3. Same fixture minus R14 → WAIT_CA, 0 CONFIRMED.  
4. Ban → not CONFIRMED.  
5. Then flip runtime ledger from observed last-good, not from a constant `True`.  
6. S7 reads `named-activation` / compiler flag; does not invent it.

UI: All Stocks already has a Confirmed filter. Wire it to S7 `publicState`. Header chip may change from `CONFIRMED LOCKED` to `CONFIRMED EOD PRF-003 ONLY` when `sourceActivationReady` is true — still `NO BROKER ORDERS`.

---

## 2. Forbidden vs needed

**Needed:** public EOD CONFIRMED, paper OMS, order preview, gated `placeorder`, intraday **guidance** CONFIRMED.  
**Forbidden:** firing live orders on default boot; Combined_Score as public state; Telegram; confirming from MWPL% or options PCR alone.

---

## 3. GATES

`D:\TrendForge\delete\gates_r2b_confirmed_2026-08-25\GATES.md`

```text
G1 r2b + s7 pytest
CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_r2b_live_named_activation.py tests/test_s7_state_gates.py -q --tb=short
EXPECT: passed
CWD: D:\TrendForge\backend

G2 live activation is observed not hardcoded
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/named-activation', timeout=60)); print(d.get('sourceActivationReady') or d.get('source_activation_ready'), d.get('authorizedCount') or d.get('authorized_count')); s7=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/s7-state', timeout=120)); print('confirmed', s7.get('confirmedCount') or s7.get('confirmed_count')); print('ACTIVATION_OBSERVED')"
EXPECT: ACTIVATION_OBSERVED

G3 no orders
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from pathlib import Path; t=Path(r'D:\\TrendForge\\backend\\trendforge_api\\selection\\s7_state_gates.py').read_text(encoding='utf-8'); assert 'place_order' not in t; print('NO_ORDERS')"
EXPECT: NO_ORDERS
```

G2 EXPECT is the token `ACTIVATION_OBSERVED`, **not** a hardcoded `true`. Record actual ready/count/confirmedCount in VALIDATION.md.

If the five last-goods are not all current: leave ready=false, confirmedCount=0, document blockers — that is a **successful fail-closed execute**, not a failed ticket.

Stop. No further File A S-stage. Next would be R8 scanners / R11 MCX / R15 UX — new prompts, not this file.
