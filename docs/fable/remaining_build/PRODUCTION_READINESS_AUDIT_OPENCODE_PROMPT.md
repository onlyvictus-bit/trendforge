# OPENCODE MASTER PROMPT — Production-readiness audit of ALL TrendForge builds so far
## Research screener ceiling · free NSE last-good · no broker · evidence before any “ready” claim

Copy **this entire file** into OpenCode. Do not skim. **Load skills first.** Then write GATES. Then measure. Then debug root causes. Then re-verify. Then verdict.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. Chain with `;` not `&&`.  
**Date: 2026-08-25.** This is an **audit + debug + re-test** ticket, not S8/S9 implementation.

---

## 0. Load these OpenCode skills BEFORE any grep, test, or edit

Use OpenCode’s native `skill` tool. Load each skill and **follow it**, do not name-drop.

| Order | Skill | Why this ticket |
|---|---|---|
| 1 | `superpowers/using-superpowers` | Session start. Find/load skills before work. |
| 2 | `unlazy` (personal/project if present) | Write `GATES.md` **before** running. Observable oracles. No vibes. |
| 3 | `superpowers/verification-before-completion` | Zero “pass/fixed/ready” without **this session’s** command output. |
| 4 | `superpowers/dispatching-parallel-agents` | Independent failure domains in parallel after the first full-suite snapshot. |
| 5 | `superpowers/systematic-debugging` | Every fail: Phase 1 root cause **before** any patch. No shotgun. |
| 6 | `superpowers/test-driven-development` | If you fix: failing test first (or prove existing test already fails), then fix. |
| 7 | `superpowers/requesting-code-review` | After fixes, dispatch `superpowers:code-reviewer`. Fix Critical/Important. |
| 8 | `superpowers/receiving-code-review` | Do not rubber-stamp the reviewer. Push back only with evidence. |

If a skill is missing: state `SKILL_ABSENT:<name>` and still obey its iron law from this file.

**Iron laws (copied, binding):**

- No completion claims without fresh verification evidence.
- No fixes without root-cause investigation first.
- 3+ failed fix attempts on the same bug → stop and question architecture; do not patch #4.
- HTTP 200 ≠ usable data. Fixture green ≠ live-source verified.
- `sourceActivationReady` stays **false**. Live File A `CONFIRMED` stays unreachable.
- No broker, OMS, OpenAlgo write, qty, Kelly, Combined_Score, win %, yfinance as truth.

---

## 0.1 What “production ready” means (the only definition allowed)

TrendForge **so far** is a **localhost research screener** over **free official NSE/NCL last-good** (bhavcopy, UDiFF FO, fo_secban, combineoi, index close, deals, AMFI delayed).

**PRODUCTION_RESEARCH_READY** (the target of this ticket) means all of:

1. Full backend pytest: **zero NEW failures**; the historical “same six” are either **fixed with evidence** or **named waivers** with root cause + why they do not break the live S0–S7 research path.
2. Frontend `acceptance-check.js` **0 failed checks**.
3. Live GET battery on **one** uvicorn of **this** tree: every File A spine route **200 with usable schema**, or **honest 503/404** with a named `WAIT_*` code — never empty theater, never CONFIRMED.
4. `confirmedCount=0` on S2, S3, S4, S5, S6, S7, R5, R2, R3. Grep-clean: no `sourceActivationReady=True` in product path.
5. POST on selection research routes = **405**.
6. No qty / order / win-rate / Combined_Score in product UI/API.
7. One public-state owner: **S7** when loaded; M-Factor/OI/Hybrid **read**, they do not re-score public state.
8. Code-reviewer: no open Critical/Important on the diff you made this ticket.

**Not in this ticket, and never call them production-ready from this audit:**

- Live CONFIRMED / R2-B `sourceActivationReady=true`
- S8 persist blob / S9 PIT homework (prompts exist; **do not implement** unless already coded — then include them in the battery)
- R8–R13, R15–R18 complete, OpenAlgo execution, broker paper/live
- `PIT_APPROVED` performance UI

If S8/S9 modules are **absent**, record `NOT_CODED` and continue. Do **not** start those prompts here.

---

## 0.2 Forbidden

- Dual-starting the collector / Refresh during the audit.
- Weakening assertions so the six go green.
- Marking production-ready from docs, HTTP 200, or old VALIDATION.md numbers.
- Adding broker candles, yfinance, or paid APIs.
- Flipping activation. Emitting CONFIRMED. Qty rail. Win % charts.
- Rewriting R5 bar engine, File A, or Hybrid into a third S-map.
- “Should pass” / “looks good” / “I am confident”.

---

## 1. First 15 minutes (orchestrator — you, not subagents)

1. Load skills (§0).  
2. Read: `AGENTS.md`, File A §9 + §9.4, `docs/BUILD_STATUS.md` **top dated entries only**, `docs/fable/S0_S9_RUN_OVERLAY_MAP_2026-08-24.md` (current build truth + remaining gaps), this file.  
3. **Write** `D:\TrendForge\delete\gates_prod_audit_2026-08-25\GATES.md` from §9 **before** any pytest. Unchecked boxes.  
4. Confirm **one** API: if something already listens on `:8000`, identify whose tree it is. Prefer a **fresh** uvicorn of `D:\TrendForge` after you know tests; do not audit a stale process from another folder.  
5. Snapshot git dirty files. Audit may fix bugs; do not mix S8/S9 feature work.

Python path for all CHECKs: `D:\TrendForge\.venv\Scripts\python.exe`. CWD for pytest: `D:\TrendForge\backend`.

---

## 2. What is in the “so far” product (measure, do not assume)

Built at research WAIT ceiling (verify in code, not only BUILD_STATUS):

| Layer | Expect present | Ceiling |
|---|---|---|
| R0–R2, R2-B named ledger | inventory + attention + activation **WAIT-only** | `sourceActivationReady=false`, `authorizedCount=0` |
| R3 / R4 / R14 / R5 / R6 | resolution diagnostic, ID pin, CA join, structure, stickers | 0 CONFIRMED |
| S2 weather | context, never stock vote | INDEX suspect path exists |
| S3 cheap discovery | full R2 universe, completeness | WAIT |
| S4 / S5 / S6 | structure pack, shortlist enrich, FUS-009 board | WAIT; S6 `merged_feed` + S5 bound |
| S7 | public state owner PRF-003 swing EOD | WAIT; `draftConfirmedEligible` never published CONFIRMED |
| OI / M-Factor / Hybrid V2 | **rooms/views** | not state owner |
| S8 / S9 | prompt-only unless modules exist | report coded or NOT_CODED |

---

## 3. Parallel audit leaves (after GATES file exists)

Dispatch **read-only** agents in parallel (`dispatching-parallel-agents`). They must **not** edit. Each returns: findings + exact commands they ran + output tails.

**Leaf A — Suite truth**  
Full backend pytest + frontend acceptance + compile. Capture **exact** failing node ids (not “the usual six”).

**Leaf B — Live spine**  
If a current-tree server is up, GET the battery in §5. If not, report `SERVER_ABSENT` — orchestrator starts one **after** suite snapshot.

**Leaf C — Safety grep**  
CONFIRMED assignment, `sourceActivationReady=True`, `place_order`, `Combined_Score`, `winRate`, qty fields on S7 idea card, broker/yfinance imports in `selection/`.

**Leaf D — Pipe honesty**  
S6 uses `merged_feed`? Bound to S5 shortlist? `/resolution` vs `/s6-resolution` disagreement? Adapter fetch count = name count? S7 is public-state owner?

**Leaf E — Known-six autopsy**  
VALIDATION.md names: hybrid overlay 503 isolation, F&O-ban fake transport, market_data_service ×3, vyom resolver fake callback. Open the **actual** failing tests this run. Classify each: `PRODUCT_BUG` | `STALE_FIXTURE` | `ENV_ONLY` | `WRONG_TEST`.

Orchestrator merges leaves. Then **only** PRODUCT_BUG / STALE_FIXTURE that block the research ceiling get fixes, via systematic-debugging + TDD, one domain at a time. Independent domains may be parallel **fix** agents with disjoint `OWNS:` paths.

---

## 4. Commands you must run (fresh, this session)

### 4.1 Compile + focused spine

```text
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m compileall trendforge_api -q
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s2_market_weather.py tests/test_s3_cheap_discovery.py tests/test_s4_structure_pack.py tests/test_s5_shortlist_enrichment.py tests/test_s6_family_resolution.py tests/test_s6_claim_feed.py tests/test_s7_state_gates.py tests/test_r5_live_structure.py tests/test_r14_live_ca_join.py tests/test_r6_live.py tests/test_top10_research.py -q --tb=short
```

If `test_s7_state_gates.py` or S8/S9 tests are missing, record NOT_CODED for that stage; do not skip the rest.

### 4.2 Full backend (the production bar)

```text
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests -q --tb=line
```

Save full output to `D:\TrendForge\delete\gates_prod_audit_2026-08-25\pytest_full.txt`.  
Count passed/failed/errors/skipped from **this** file. Collection errors count as failed audit.

### 4.3 Frontend

```text
cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

### 4.4 Static safety (PowerShell-safe; no grep required)

```text
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -c "from pathlib import Path
root=Path('trendforge_api/selection')
needles=['sourceActivationReady=True','place_order','Combined_Score','winRate','yfinance']
hits=[]
for p in root.rglob('*.py'):
 t=p.read_text(encoding='utf-8', errors='replace')
 for n in needles:
  if n in t: hits.append(f'{p}:{n}')
print('HITS', len(hits));
print('\n'.join(hits) if hits else 'SELECTION_CLEAN')"
```

S7 idea-card geometry must be null on live payload (entry/stop/qty).

### 4.5 Ruff only on files **you** touch this ticket

Do not mass-format the repo.

---

## 5. Live GET battery (restart API from this tree)

Start **one** server after code freeze for the measurement:

```text
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m uvicorn trendforge_api.main:app --host 127.0.0.1 --port 8000
```

If 8000 is a foreign process, use 8001 and say so. Kill extras.

For each GET: record HTTP, schema/profile/ceiling if present, `confirmedCount`, row/candidate count, first `WAIT_*` if 503.

**Spine (must):**

```text
GET /api/health
GET /api/v1/selection/market-weather
GET /api/v1/selection/cheap-discovery
GET /api/v1/selection/s4-structure
GET /api/v1/selection/s5-enrichment
GET /api/v1/selection/s6-resolution
GET /api/v1/selection/s7-state
GET /api/v1/selection/s7-state/ABCAPITAL
GET /api/v1/selection/ca-join
GET /api/v1/selection/identity-pin
GET /api/v1/selection/named-activation
GET /api/v1/selection/top10
GET /api/v1/selection/evidence-radar
GET /api/source-operations/snapshot
```

**Honesty extras:**

```text
GET /api/v1/selection/resolution          # thin R3; must not disagree with S7 publicState if UI still mounts it
POST /api/v1/selection/s7-state           # 405
POST /api/v1/selection/s6-resolution      # 405
POST /api/v1/selection/s4-structure       # 405
```

Usable means: JSON parses; `confirmedCount` is 0 or absent-with-named-WAIT; rows that exist have `publicState`/`researchState` in `{WATCH,WAIT,REJECT}`; missing last-good → 503 with code, not a fake full board.

Also GET any S8/S9 routes **only if** modules import. Else `NOT_CODED`.

Write a tiny probe if you want; keep it under `delete/gates_prod_audit_2026-08-25/`.

---

## 6. Debug rules (when anything fails)

Follow systematic-debugging **per failing node id**:

1. Read the full traceback. Reproduce with `pytest -k <id> -vv --tb=short`.  
2. Trace to the source value (fixture clock, fake transport, hash mismatch, stale uvicorn).  
3. One hypothesis. Smallest change.  
4. If PRODUCT_BUG: fix product + keep assertion.  
5. If STALE_FIXTURE: repair fixture to match **current honest contract** (e.g. 503 on empty DB is correct — update test to expect 503, do not make the API lie).  
6. If ENV_ONLY: `ABANDON: Gx <reason>` in GATES — still listed in the verdict.  
7. Re-run **that test**, then the **focused spine**, then **full suite**. Verification-before-completion: you may not say “fixed” until those three exist in this session.

Do not “fix” by deleting tests. Do not expand scope to S8/S9/R12.

---

## 7. Code review (after any edit)

Dispatch `superpowers:code-reviewer` with: what changed, File A research ceiling, “no CONFIRMED, no broker, no qty”.  
Fix Critical and Important. Re-run affected tests. Then full suite again.

---

## 8. Docs (only after GATES measured)

Append **observed** commands + numbers to:

- `docs/VALIDATION.md` (top)  
- `docs/BUILD_STATUS.md` (top) — verdict line: `PRODUCTION_RESEARCH_READY` or `NOT_READY` plus waiver list  

Do not rewrite File A. Throwaways only under `D:\TrendForge\delete\gates_prod_audit_2026-08-25\`.

---

## 9. GATES.md (create first; fill EVIDENCE last)

Create `D:\TrendForge\delete\gates_prod_audit_2026-08-25\GATES.md`:

```text
# Gates: production-research audit 2026-08-25

OWNS: backend/tests/** (fixture honesty only), backend/trendforge_api/** (bugfix only), frontend/tests/acceptance-check.js (if broken by truth), docs/VALIDATION.md, docs/BUILD_STATUS.md
Scope: Measure S0–S7 + R1–R6/R14 research ceiling; fix PRODUCT_BUG/STALE_FIXTURE that block it; never unlock CONFIRMED.

- [ ] G1 compile
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m compileall trendforge_api -q
  EXPECT: (empty or silent ok)
  CWD: D:\TrendForge\backend

- [ ] G2 focused spine pytest
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s2_market_weather.py tests/test_s3_cheap_discovery.py tests/test_s4_structure_pack.py tests/test_s5_shortlist_enrichment.py tests/test_s6_family_resolution.py tests/test_s6_claim_feed.py tests/test_s7_state_gates.py tests/test_r5_live_structure.py tests/test_r14_live_ca_join.py -q --tb=short
  EXPECT: passed
  CWD: D:\TrendForge\backend

- [ ] G3 full backend pytest
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests -q --tb=line
  EXPECT: failed=0
  CWD: D:\TrendForge\backend
  # If failed>0: either fix or ABANDON each node id with PRODUCT/STALE/ENV class. failed=0 is the research production bar. Waivers must be named in the verdict; a waiver is NOT a pass.

- [ ] G4 frontend acceptance
  CHECK: node tests/acceptance-check.js
  EXPECT: 0 failed checks
  CWD: D:\TrendForge\frontend

- [ ] G5 selection safety
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from pathlib import Path; root=Path(r'D:\\TrendForge\\backend\\trendforge_api\\selection'); needles=['sourceActivationReady=True','place_order','Combined_Score']; hits=[f'{p}:{n}' for p in root.rglob('*.py') for n in needles if n in p.read_text(encoding='utf-8', errors='replace')]; print('SELECTION_CLEAN' if not hits else '\n'.join(hits)); raise SystemExit(0 if not hits else 1)"
  EXPECT: SELECTION_CLEAN

- [ ] G6 live S7 confirmedCount=0
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/s7-state', timeout=60)); c=d.get('confirmedCount', d.get('confirmed_count')); print(c); assert c==0; states={(r.get('publicState') or r.get('public_state')) for r in (d.get('rows') or d.get('candidates') or [])}; assert 'CONFIRMED' not in states; print('S7_LOCKED', sorted(states))"
  EXPECT: S7_LOCKED

- [ ] G7 live S6 board honest
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/s6-resolution', timeout=120)); c=d.get('confirmedCount', d.get('confirmed_count')); print('s6', c, d.get('schemaVersion') or d.get('schema_version')); assert c==0; print('S6_LOCKED')"
  EXPECT: S6_LOCKED

- [ ] G8 POST 405
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import urllib.request,urllib.error
def p(url):
 req=urllib.request.Request(url, method='POST', data=b'{}', headers={'Content-Type':'application/json'})
 try:
  urllib.request.urlopen(req, timeout=30); return 200
 except urllib.error.HTTPError as e:
  return e.code
codes=[p('http://127.0.0.1:8000/api/v1/selection/s7-state'), p('http://127.0.0.1:8000/api/v1/selection/s6-resolution')]; print(codes); assert codes==[405,405]; print('POST_405')"
  EXPECT: POST_405

- [ ] G9 no CONFIRMED leak in live named-activation
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/named-activation', timeout=60)); print(d.get('sourceActivationReady') or d.get('source_activation_ready'), d.get('authorizedCount') or d.get('authorized_count')); assert (d.get('sourceActivationReady') is False) or (d.get('source_activation_ready') is False); print('ACTIVATION_FALSE')"
  EXPECT: ACTIVATION_FALSE
```

G3 `EXPECT: failed=0` is the honest bar. If you must ship with waivers, **do not check G3**. List `ABANDON: G3 <each node id + class + why research path still safe>`. Verdict cannot be `PRODUCTION_RESEARCH_READY` while G3 is abandoned unless every waiver is `ENV_ONLY` **and** live G6–G9 are green. Product bugs left failing ⇒ `NOT_READY`.

---

## 10. Final report (mandatory shape)

```text
## Verdict
PRODUCTION_RESEARCH_READY | NOT_READY | READY_WITH_NAMED_ENV_WAIVERS

## Evidence (this session)
- pytest full: passed / failed / errors  (paste counts)
- failing node ids: …
- frontend acceptance: …
- live S7 confirmedCount / states
- live S6 confirmedCount / rowCount vs S5 shortlist
- sourceActivationReady
- POST 405

## Built vs missing
- S2..S7: CODED / BROKEN / ABSENT
- S8/S9: CODED / NOT_CODED
- R8–R13/R16–R18: not claimed

## Six-or-N autopsy
| node id | class | root cause | action | retest |

## Fixes this ticket
- files + why

## Code review
- Critical/Important remaining: 0 or list

## Still not production trading
- no broker, no CONFIRMED, no qty, no PIT_APPROVED
```

Stop when GATES are measured and the verdict is honest. Do not start S8/S9 from this prompt.
