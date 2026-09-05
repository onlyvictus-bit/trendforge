# GLM / OPENCODE BUILD PROMPT — File A S7 state gates (SEL-008)
## One public-state owner · PRF-003 live swing on free NSE EOD · CONFIRMED unreachable while activation=false · production research (no broker)

Copy **this entire file**. Think first. Build. Then run **§9 GATES** and debug every fail before claiming done.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. Chain with `;` not `&&`.  
**Date: 2026-08-24.** Run **this ticket first**, then `S8_PERSIST_RUN_GLM_PROMPT.md`, then `S9_PIT_HOMEWORK_GLM_PROMPT.md`.

Authority: File A `docs/fable/new_merge_PLAN_2026-07-18.md` §9 S7 / §9.4 / §10 / PRF-003. Overlay: `docs/fable/S0_S9_RUN_OVERLAY_MAP_2026-08-24.md`. Status: `docs/BUILD_STATUS.md`.

---

## 0. What “production ready” means here

TrendForge is a **localhost research screener**. All primary data is **free official NSE/NCL** (bhavcopy, UDiFF FO, fo_secban, combineoi, index close, deals, AMFI delayed).  

**There is no broker, no OMS, no OpenAlgo orders, no quantity, no auto-trade.**  
Production-ready = one honest scan: named WATCH / WAIT / REJECT, why, missing proof, structure-owned **labels** for next trigger / invalidation — reconstructable, fail-closed, green tests.

**Do not** set `sourceActivationReady=true`. **Do not** emit live File A `CONFIRMED`. File A §9.4: activation false ⇒ publication ceiling WAIT. Compute `draftConfirmedEligible` so the pipe is complete; never publish CONFIRMED.

---

## 0.1 Outcome (done = observed on live 2026-08-21 lineage)

1. **One S6 GET** is the only family resolver the UI uses for this run.  
2. That GET uses `merged_feed` (cash FTR-040 ∪ R5 structure claims), **S5 shortlist symbols only** (not all 2,633 R5 rows).  
3. **S7 GET** projects **one** stored public state per symbol. M-Factor / OI / Hybrid **read** it; they do not re-score.  
4. Live states: `WATCH` | `WAIT` | `REJECT` only. `confirmedCount=0`.  
5. Idea card: symbol, state, `why[]`, `missingEvidence[]`, `nextTrigger` / `invalidationCondition` from S4 **labels**. `entry`/`stop`/`t1`/`t2`/`quantity` stay **null**.  
6. S2 weather is a **gate flag** (`WAIT_WEATHER_UNKNOWN` if regime UNKNOWN) — **not** a stock vote, **not** a required family.  
7. POST on new routes = 405.  
8. §9 GATES all pass.

---

## 0.2 Forbidden

- Broker, qty, Kelly, SPAN, order intent, OpenAlgo write.  
- `Combined_Score`, win %, P(win), EV.  
- `sourceActivationReady=true` or live `CONFIRMED`.  
- Options-only upgrade of state. Removing options must not raise state (File A §9.6.2).  
- GEX as dealer fact. “FII bought this stock.”  
- Third S-map (Final Merge story S4 ≠ File A S4).  
- Rebuilding R5 bar engine. S4 pack already projects R5.  
- Silent drop of symbols when optional S5 fields are UNKNOWN.

---

## 1. Session 0 — must land before S7 (pipe honesty)

Without this, S7 gates air.

### 1.1 One resolver

- Keep `GET /api/v1/selection/s6-resolution` as **canonical S6**.  
- `GET /api/v1/selection/resolution` (old R3) must **either** alias the same hash-matched S6 payload **or** return 410/`WAIT_USE_S6_RESOLUTION` with a pointer. No two public states.  
- `build_s6_resolution` **must** call `s6_claim_feed.merged_feed(cash, r5_batch)` — cash ∪ structure, first-wins `claim_id`.  
- Loop **S5 shortlist symbols** (or S4 structure-claimed entries), not `for row in all R5 rows`.  
- Pass `s5=` from the S5 builder used in the same request (same S4 pack).  
- Attach S2 via `attach_market_context` / `S6MarketContextBlockV1` (`canSupportConfirmed=false`).  
- Hash-match R1/R2/R14/R5 or 503 `WAIT_*_LINEAGE`.
- **Old `/resolution` migration (RESOLVED 2026-08-24):** grep found one real consumer — the M-Factor BFF subsume-check. Decision: legacy `/resolution` is RETAINED as the read-only R3 diagnostic (with deprecation pointer in its docstring); it is NOT a second public state because the UI never reads it — All Stocks/inspector project S7 only. Canonical family resolution = `/s6-resolution`.

### 1.2 Tests for session 0

- `merged_feed` used by `build_s6_resolution` (not only unit-tested in isolation).  
- S6 row count ≤ S5 `shortlistCount` when S5 builds.  
- Old `/resolution` does not disagree with `/s6-resolution` on `publicState`.  
- Fixture: confirming claim still rejected at R5 boundary.

---

## 2. S7 module (keep)

`D:\TrendForge\backend\trendforge_api\selection\s7_state_gates.py`

| Piece | Contract |
|-------|----------|
| Schema | `trendforge.s7-state.v1` |
| Profile live | **PRF-003** NSE swing continuation (File A §9.2): closed STRUCTURE + (PARTICIPATION **or** EVENT) + no event blackout. Data mode `EOD_RESEARCH`. |
| PRF-003 RS note | Stock/sector RS currently lives as an ACTIVITY companion fact (radar `rs_fact`), not a resolver family. This ticket: RS above the PIT median satisfies the PARTICIPATION-or-EVENT alternative **only alongside structure**; emit reason code `PRF003_RS_AS_COMPANION` in `reasons[]`. A File A amendment owns any family promotion. |
| Event blackout | Source = `macro_event_context` last-good. Absent / stale / unknown → gate `WAIT_EVENT_BLACKOUT_UNKNOWN` (fail-closed). Never assumed-clear. |
| Other PRF-001/002/004–007 | Return empty boards + `WAIT_HORIZON_*` / `WAIT_MCX_MASTER` — do not fake. |
| Ceiling | `LIVE_S7_WATCH_WAIT_REJECT_ONLY` |
| `sourceActivationReady` | always `false` |
| `canUnlockConfirmed` | always `false` |
| `confirmedCount` | `0` |
| `draftConfirmedEligible` | bool per row: §10.4 checklist **would** pass **if** activation were true **and** some claim had `can_support_confirmed=true`. Today almost all claims are false ⇒ this stays false. **Never** copy it into `publicState=CONFIRMED`. |

### 2.1 Public state rules (owner)

Exactly one owner: S6 resolution + this gate file (File A §9.4).

```text
REJECT  if R2 already REJECT, or ban/MWPL BAN, or WAIT_CA identity-break,
        or structure_state REJECT, or hard G-code veto
WAIT    if activation false (always, this ticket)
        OR required family missing
        OR completeness < profile.min
        OR S2 regimeLabel == UNKNOWN (flag WAIT_WEATHER_UNKNOWN, not a vote)
        OR conflict above profile threshold
        OR draftConfirmedEligible is the only “yes” (still WAIT — locked)
WATCH   if discovery/forming: structure tags exist, no hard veto,
        not all required families present, still a look-at-me name
CONFIRMED  unreachable this ticket
```

Map File A G00–G14 into `reasons[]` (codes, not API states). Reuse existing safety: `_symbol_has_fno_ban`, MWPL from combineoi, R14 `caState`.

### 2.2 Idea card (not geometry)

Fields allowed: `symbol`, `publicState`, `evidenceDirection`, `evidenceStrength` (label **must** contain “not win probability”), `familySupport`, `familyOpposition`, `missingFamilies`, `why`, `missingEvidence`, `nextTrigger`, `invalidationCondition` (from S4 **only**), `weatherRegime` (display), `foPackage` / `optionsPackage` **status strings** from S5 (not votes).

**Null forever this ticket:** `entry`, `stop`, `t1`, `t2`, `quantity`. Hybrid V3 A/B/C stays ⊕ overlay if already on Hybrid panel — **do not** write it as S7 law.

### 2.3 Routes

```
GET  /api/v1/selection/s7-state
GET  /api/v1/selection/s7-state/{symbol}
POST /api/v1/selection/s7-state        → 405
```

Build: hash-matched R5 → S4 pack → S5 enrich → S6 resolve (`merged_feed`) → S7 gates. 503 on lineage miss. Optional persist via S8 ticket — S7 may call `persist_selection_payload` **if** S8 is not yet merged; prefer leaving persist to S8 if you land both in order.

---

## 3. Frontend

- Do **not** invent a new nav group. Paint:
  - All Stocks: `publicState` from **S7** when adapter loaded (same run id), not a second score.
  - Live Ops + Evidence inspector: S7 why / missing / next trigger.
- File: `frontend/s7-state.js` + mount in `index.html` + adapter fetch `/api/v1/selection/s7-state`.
- Copy: “Research state — not an order.”
- Acceptance-check.js: script mounted, no CONFIRMED in s7-state.js product path, GET path present.
- Cache-bust `?v=20260824-s7-1`.

---

## 4. Tests (mandatory File A §9.6 teeth)

`backend/tests/test_s7_state_gates.py`

1. `sourceActivationReady=false` ⇒ zero CONFIRMED in S7 payload.  
2. Options-only (no structure family) ⇒ state ≤ WAIT; stripping options does not upgrade.  
3. Two activity claims same CG ⇒ one participation contribution (resolver already; assert S7 doesn’t double).  
4. Ban / WAIT_CA → REJECT or WAIT with named code, never WATCH.  
5. UI/API state equality: fixture S7 row `publicState` == stored payload.  
6. POST 405.  
7. Hash mismatch → 503.  
8. `draftConfirmedEligible` never copied to `publicState`.  
9. Idea card has no entry/stop/qty keys or they are null.  
10. S6 input to S7 uses shortlist, not 2,633-wide R5, when S5 present.

Also: no regression `test_s4_structure_pack.py`, `test_s5_shortlist_enrichment.py`, `test_s6_family_resolution.py`, `test_s6_claim_feed.py`, `test_r5_live_structure.py`, `test_r14_live_ca_join.py`.

Fix `test_s6_claim_feed.py` import (`tests.test_m_factor_claims` collection error) if it still fails default pytest.

---

## 5. Docs

- Append `BUILD_STATUS.md` + `VALIDATION.md` with observed GET 200, counts, `confirmedCount=0`.  
- Overlay map: S7 row = CODED WAIT; keep CONFIRMED unreachable.  
- Throwaways: `D:\TrendForge\delete\s7_wip_2026-08-24\` only.  
- GATES file: `D:\TrendForge\delete\gates_s7_2026-08-24\GATES.md`.

---

## 6. Free-data note (do not scrape new paid APIs)

Use last-good official artifacts already in TrendForge:

- Cash / FO UDiFF zips, `fo_secban.csv`, `combineoi_*.zip`, index close, A4 bars, A6 futures, AMFI delayed.  
- Do not add broker candles. Do not require OpenAlgo.  
- If a free file is missing: UNKNOWN / WAIT code, never invent.

---

## 7. Audit after build (you must run)

```text
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s7_state_gates.py tests/test_s6_family_resolution.py tests/test_s6_claim_feed.py tests/test_s4_structure_pack.py tests/test_s5_shortlist_enrichment.py -q --tb=short
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests -q --tb=no
# Known: at most the same 6 pre-existing failures. Zero NEW fails.

cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Live (server on :8000, restart after code):

```text
GET /api/v1/selection/s6-resolution   → 200; STRUCTURE family support > 0 on some rows
GET /api/v1/selection/s7-state        → 200; confirmedCount=0; no CONFIRMED in rows
GET /api/v1/selection/s7-state/ABCAPITAL
POST /api/v1/selection/s7-state       → 405
```

Grep: `s7_state_gates.py` has no `sourceActivationReady=True`, no `SelectionState.CONFIRMED` assigned to `public_state`.

**Debug until those GET observations hold.** Then stop. Do not start S8 until this ticket’s GATES are green.

---

## 8. Debug catalog (every class — fix, do not skip)

| Symptom | Likely cause | Fix |
|---|---|---|
| pytest collection error `tests.test_m_factor_claims` | relative import in `test_s6_claim_feed.py` | change to `trendforge_api…` import; collection must pass under default `pytest tests` |
| GET 200 but `confirmedCount` missing / rows CONFIRMED | validator not frozen; UI invented state | pydantic `frozen=True`; reject CONFIRMED at model_validator |
| GET 503 `WAIT_*_LINEAGE` | hash mismatch R1/R2/R14/R5 | fail closed; do not last-good-swap |
| S6 still 2,633 rows | session-0 shortlist loop not landed | S5 symbols only |
| Two different `publicState` on All Stocks vs inspector | adapter still reading R3 `/resolution` | one S6 GET + S7 projection |
| Frontend blank | stale uvicorn / cache | restart API; cache-bust `?v=20260824-s7-1` |
| POST 200 | route not 405 | add POST 405 like S4–S6 |
| Idea card shows entry/qty | Hybrid overlay leaked into S7 DTO | null those keys |
| New full-suite fails beyond the known 6 | regression | revert unrelated files; do not “fix” baseline 6 |
| Accidental broker / OpenAlgo write | out of scope | delete; research uses last-good NSE zips only |

---

## 9. GATES (write + run before claiming done)

Create `D:\TrendForge\delete\gates_s7_2026-08-24\GATES.md` with these oracles. Every CHECK must exit 0 and match EXPECT. Debug until green.

```text
G1 S7 module exists
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from trendforge_api.selection.s7_state_gates import SCHEMA_VERSION, PROFILE_ID, ACCEPTANCE_CEILING; print(SCHEMA_VERSION, PROFILE_ID, ACCEPTANCE_CEILING)"
EXPECT: trendforge.s7-state.v1

G2 focused pytest
CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s7_state_gates.py tests/test_s6_family_resolution.py tests/test_s6_claim_feed.py tests/test_s4_structure_pack.py tests/test_s5_shortlist_enrichment.py -q --tb=short
EXPECT: passed

G3 no CONFIRMED assignment in product path
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from pathlib import Path; t=Path(r'D:\\TrendForge\\backend\\trendforge_api\\selection\\s7_state_gates.py').read_text(encoding='utf-8'); assert 'sourceActivationReady=True' not in t; assert 'public_state=SelectionState.CONFIRMED' not in t; print('NO_CONFIRMED_ASSIGN')"
EXPECT: NO_CONFIRMED_ASSIGN

G4 live GET confirmedCount=0 (server must be the new code on :8000)
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/s7-state')); print(d.get('confirmedCount', d.get('confirmed_count'))); assert d.get('confirmedCount', d.get('confirmed_count'))==0; states={r.get('publicState') or r.get('public_state') for r in d.get('rows') or d.get('candidates') or []}; assert 'CONFIRMED' not in states; print('STATES', sorted(states))"
EXPECT: 0

G5 POST 405 (PowerShell-safe: ship a tiny runner, no multi-line -c)
CHECK: D:\TrendForge\.venv\Scripts\python.exe D:\TrendForge\delete\gates_s7_2026-08-24\post405.py http://127.0.0.1:8000/api/v1/selection/s7-state
EXPECT: 405

Create `post405.py` next to the GATES file with exactly:

```python
import sys, urllib.request, urllib.error
url = sys.argv[1]
req = urllib.request.Request(url, method="POST", data=b"{}", headers={"Content-Type": "application/json"})
try:
    r = urllib.request.urlopen(req)
    print(getattr(r, "status", 200))
except urllib.error.HTTPError as e:
    print(e.code)
```

G6 frontend acceptance
CHECK: node tests/acceptance-check.js
EXPECT: ok
CWD: D:\TrendForge\frontend
```

Stop. Do **not** open S8 until G1–G6 are observed green.
