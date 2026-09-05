# GLM / OPENCODE BUILD PROMPT — File A S8 persist one reconstructable scan (SEL-009)
## One immutable blob of S2–S7 · STO-006/007/008 · History inspector · no broker · no CONFIRMED

Copy **this entire file**. Think first. Build. Then run **§9 GATES** and debug every fail before claiming done.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. Chain with `;` not `&&`.  
**Date: 2026-08-24.** Run **after** `S7_STATE_GATES_GLM_PROMPT.md` GATES are green. Then `S9_PIT_HOMEWORK_GLM_PROMPT.md`.

Authority: File A `docs/fable/new_merge_PLAN_2026-07-18.md` §9 S8 / §9.1 completeness / §14.1 STO-006/007/008 / §14.2 scans GET / UI-011. Overlay gap #10: `docs/fable/S0_S9_RUN_OVERLAY_MAP_2026-08-24.md`. Store: `backend/trendforge_api/selection/store.py`.

If S7 is not live (`GET /api/v1/selection/s7-state` missing or GATES red): **stop**. Do not fake an S8 blob from R5 alone.

---

## 0. What “production ready” means here

TrendForge is a **localhost research screener**. Primary data is **already-fetched free official NSE/NCL** last-good (bhavcopy, UDiFF FO, fo_secban, combineoi, index close, deals, AMFI delayed).

**There is no broker, no OMS, no OpenAlgo orders, no quantity, no auto-trade.**  
Production-ready S8 = a researcher can reload yesterday’s scan and see the **same** public states, why/missing, hashes, and completeness. Reconstructable. Immutable. Fail-closed.

**Do not** set `sourceActivationReady=true`. **Do not** emit live File A `CONFIRMED`. Persisting a WAIT run does not make it CONFIRMED.

---

## 0.1 Outcome (done = observed on live 2026-08-21 lineage)

1. One GET returns the **latest** File A scan blob: lineage hashes S2–S7 + R1/R2/R14/R5, completeness counts, every shortlist symbol’s **S7 publicState**, why/missing/gates, family snapshot, what-changed vs prior comparable run (`NO_BASELINE` if none).
2. Reloading the same `runId` returns **byte-identical** `payload_json` (STO-006 immutability already in `persist_selection_payload`).
3. `confirmedCount=0`. States `WATCH|WAIT|REJECT` only. Completeness `< profile.min` ⇒ every row ceiling WAIT + `WAIT_PARTIAL_SCAN` (File A §9.1).
4. Overlay gap #10 closed: S2 weather snapshot + S3 cheap-discovery identity (run id / completeness) **are inside the blob**. Hybrid V2 overlay may be **hash-pinned**; it must **not** vote or write `publicState`.
5. History inspector shows this run (not a second score). POST on new routes = 405.
6. §9 GATES all pass.

---

## 0.2 Forbidden

- Broker, qty, Kelly, SPAN, order intent, OpenAlgo write, `place_order`.
- `Combined_Score`, win %, P(win), EV, “accuracy”.
- `sourceActivationReady=true` or live `CONFIRMED` in the blob.
- POST `/api/v1/selection/scans` that **starts the collector** or dual-starts Refresh. File A lists that POST for a later scan-trigger; **this ticket 405s it**. Persist is a **projection of last-good spine**, like S4–S7 GETs.
- DuckDB, new database file, destructive overwrite, silent last-good swap on hash mismatch.
- Rebuilding R5/S4/S5/S6/S7 engines. S8 **assembles and stores**.
- Persisting Hybrid `p̂` / Kelly / zone grade as File A law.
- Treating HTTP 200 as “usable” if `rows=[]` with no completeness reason.

---

## 1. What S8 is (File A §9 wins)

| Stage | ID | Work | Ceiling |
|---|---|---|---|
| **S8** | `SEL-009` | Persist run, facts, claims, gates, family resolution, explanation, transition, completeness | Reconstructable history |
| **S9** | `SEL-010` | Offline PIT labels | **Not this ticket** |

| This ticket IS | This ticket is NOT |
|---|---|
| One File A scan blob | A second public-state owner |
| STO-006 run + STO-007 candidate rows + STO-008 state events | Overwriting yesterday |
| UI-011 structured what-changed | Free-text “looks stronger” |
| S2/S3 DTO pins inside the blob | Re-running discovery |

**Already live (reuse, do not fork):**

- `selection/store.py` — `persist_selection_payload` (immutable on `run_id`), `latest_selection_payload`, `apply_comparable_diff` (R1 batch).
- SQLite tables `selection_scan_runs`, `selection_candidates`, `selection_state_events` in `storage.py` (migration `0007_selection_r1_runs`).
- Per-stage payloads already persisted for R1–R6/R14 under **other** `profile_id`s. S4/S5/S6 currently **do not** call `persist_selection_payload` (S5 test even asserts `PRF-S5-ENRICH-WAIT` is None). **S8 is the one-blob owner.** Optional: S8 may persist S7 first if S7 left persist to this ticket.

---

## 2. Module (keep these names)

`D:\TrendForge\backend\trendforge_api\selection\s8_persist_run.py`

| Piece | Contract |
|-------|----------|
| Schema | `trendforge.s8-scan.v1` |
| Profile | `PRF-S8-SCAN-RUN` version `1.0.0` |
| Ceiling | `LIVE_S8_RECONSTRUCTABLE_WAIT_ONLY` |
| `sourceActivationReady` | always `false` |
| `canUnlockConfirmed` | always `false` |
| `confirmedCount` | `0` |
| `dataMode` | `EOD_RESEARCH` |
| Frozen pydantic | `alias_generator=to_camel`, `populate_by_name=True`, `frozen=True` |

### 2.1 Blob (minimum fields)

```text
runId            stable_id of (profile, asOf date, lineage hash tuple) — same inputs => same runId
asOf             S7/R5 decision clock (timezone-aware IST/UTC consistent with spine)
lineage          r1RunHash, r2RunHash, r14RunHash, r5RunHash,
                 s2RunId, s3RunId, s4PackId, s5RunId, s6RunId, s7RunId
                 (null + WAIT_STAGE_ABSENT reason if a stage DTO is missing — do not invent)
weather          S2 regimeLabel + suspect flags (INDEX_CHANGE_SUSPECT etc). Context only.
s3Completeness   scanned / eligible / excluded / failed / unattempted from S3 if present
completeness     File A §9.1 against PIT eligible universe after S1 exclusions.
                 Timeouts and unattempted are NOT eligible exclusions.
hybridPin        optional overlay hash; canVote=false
rows[]           one per S7 row (shortlist, not 2,633-wide R5)
```

**Per row (STO-007 projection):**

```text
candidateId, symbol
publicState          FROM S7 ONLY
evidenceDirection, evidenceStrength, evidenceStrengthLabel
  label MUST contain "not win probability"
why[], missingEvidence[], gateCodes[]
nextTrigger, invalidationCondition     (S4 labels; entry/stop/qty null)
familySupport / familyOpposition / missingFamilies
foPackage / optionsPackage status strings (not votes)
changeKinds[]        STATE|GATE|FAMILY|FEATURE|SOURCE|FRESHNESS|COMPLETENESS|VERSION
comparableRunId      or NO_BASELINE
claimIds[]           frozen list from S6 (ids only, not a second fuse)
```

Reject the model if any row is `CONFIRMED`, if `entry`/`stop`/`quantity` are non-null, or if `sourceActivationReady` is true.

### 2.2 Persist rules

1. Build: hash-matched R5 → existing S4/S5/S6/S7 builders (same request). 503 on lineage miss — **never** persist a mixed-hash blob.
2. Call `persist_selection_payload(run_id=..., profile_id=PRF-S8-SCAN-RUN, as_of=..., payload=dump, candidates=tuples)`.
3. **STO-008:** also write `selection_state_events` for each candidate vs prior S8 run (prior_state → resulting_state, `accepted=0`, reason_code from gates). Extend `store.py` with a helper if needed; do **not** create a second SQLite. Re-persist of identical `run_id` must no-op (existing immutability). Different payload same `run_id` must raise.
4. Completeness ratio: if `< profile.min_completeness` (read from live profile object; if unset use a named constant documented in BUILD_STATUS, do not silently 1.0), set batch `stateCeiling=WAIT` and add `WAIT_PARTIAL_SCAN` on every row.
5. `apply_comparable_diff` exists for R1 batches — **clone the kind logic** onto S8 rows (do not require `LiveSelectionBatch`). Missing prior → `NO_BASELINE`, empty `changeKinds`.

### 2.3 Routes

```
GET  /api/v1/selection/scans/latest
GET  /api/v1/selection/scans/{run_id}
GET  /api/v1/selection/scans/{run_id}/candidates
GET  /api/v1/selection/scans/{run_id}/candidates/{symbol}
GET  /api/v1/selection/scans?limit=20          # newest first, reconstructable list
POST /api/v1/selection/scans                   → 405
POST /api/v1/selection/scans/{run_id}          → 405
```

Register in `backend/trendforge_api/main.py` next to S4–S7. Unknown `run_id` → 404. Hash-mismatch on **build** of latest → 503 `WAIT_S8_LINEAGE`. Do not return a stale other-day blob as “latest” when current lineage does not match — latest means latest **matching** current R1/R2/R14/R5 hashes, or 503.

FastAPI order: declare `/scans/latest` **before** `/scans/{run_id}`.

---

## 3. Frontend

- Do **not** invent a nav group. Paint File A inspector **History** tab (`#q5Inspector` History): run id, as-of, completeness counts, what-changed chips, publicState from the blob.
- Live Ops failures panel: excluded / failed / unattempted counts from completeness (File A §13.2 Failures).
- File: `frontend/s8-persist.js` + mount in `index.html` + `selection-live-adapter.js` fetch count **must equal** name count.
- Copy: “Reconstructable research run — not an order. Not a win rate.”
- Cache-bust `?v=20260824-s8-1`.
- Acceptance-check.js: script mounted, GET path present, no CONFIRMED product path, no qty.

---

## 4. Tests (mandatory)

`backend/tests/test_s8_persist_run.py`

1. Identical inputs → identical `runId`; second persist no-op; mutated payload same `runId` raises.
2. `confirmedCount=0`; no row `CONFIRMED`; `sourceActivationReady is False`.
3. Blob contains `lineage.s2RunId` or explicit `WAIT_STAGE_ABSENT` (gap #10). Same for S3 completeness fields.
4. Completeness below min → `WAIT_PARTIAL_SCAN` on rows; unattempted not counted as excluded.
5. Prior run exists → `changeKinds` includes `STATE` when publicState differs; none → `NO_BASELINE`.
6. Hash mismatch → builder/API 503, **nothing new** in `selection_scan_runs` for this profile.
7. POST `/api/v1/selection/scans` → 405.
8. GET latest then GET by that `runId` → equal publicStates (UI/API equality).
9. Hybrid pin if present has `canVote=false`; stripping Hybrid does not change `publicState`.
10. Idea-card geometry keys null. No `Combined_Score`.
11. Candidate count == S7 row count (shortlist), not 2,633.

Also no regression: `test_s7_state_gates.py`, `test_s6_family_resolution.py`, `test_s6_claim_feed.py`, `test_s4_structure_pack.py`, `test_s5_shortlist_enrichment.py`, `test_r5_live_structure.py`.

Fix collection errors under default `pytest tests` (the `tests.test_m_factor_claims` import trap).

---

## 5. Docs

- Append `docs/BUILD_STATUS.md` + `docs/VALIDATION.md` with observed GET 200, `runId`, row count, `confirmedCount=0`, completeness tuple.
- Overlay map: gap #10 **closed**; S8 row = CODED WAIT reconstructable.
- Throwaways: `D:\TrendForge\delete\s8_wip_2026-08-24\` only.
- GATES file: `D:\TrendForge\delete\gates_s8_2026-08-24\GATES.md`.

---

## 6. Free-data note (do not scrape paid APIs)

S8 does **not** fetch the web. It hashes and stores what S0–S7 already parsed from official last-good files:

- NSE cash / FO UDiFF zips, `fo_secban.csv`, `combineoi_*.zip`, index close, A4 bars, A6 futures, AMFI delayed.
- Do not add Yahoo, broker candles, or OpenAlgo.
- If a stage DTO is missing: `WAIT_STAGE_ABSENT` in lineage, still persist the rest with honest completeness — **or** 503 if S7 itself is missing (S7 is required).

---

## 7. Audit after build (you must run)

```text
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s8_persist_run.py tests/test_s7_state_gates.py tests/test_s6_family_resolution.py tests/test_s4_structure_pack.py tests/test_s5_shortlist_enrichment.py -q --tb=short
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests -q --tb=no
# Known: at most the same 6 pre-existing failures. Zero NEW fails.

cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Live (restart uvicorn after code so routes exist):

```text
GET  /api/v1/selection/s7-state           still 200, confirmedCount=0
GET  /api/v1/selection/scans/latest       200; lineage hashes present; confirmedCount=0
GET  /api/v1/selection/scans/{runId}      same publicStates
GET  /api/v1/selection/scans/{runId}/candidates
POST /api/v1/selection/scans              405
```

SQLite check (same DB the API uses):

```text
D:\TrendForge\.venv\Scripts\python.exe -c "from trendforge_api.selection.store import latest_selection_payload; p=latest_selection_payload('PRF-S8-SCAN-RUN'); print(p['runId'] if p else None, (p or {}).get('confirmedCount'))"
```

Grep: `s8_persist_run.py` has no `sourceActivationReady=True`, no broker client, no `Combined_Score`.

**Debug until GET observations hold.** Then stop. Do not start S9 until this ticket’s GATES are green.

---

## 8. Debug catalog (every class — fix, do not skip)

| Symptom | Likely cause | Fix |
|---|---|---|
| `/scans/latest` 404 or captured as `{run_id}=latest` | route order | declare `/scans/latest` first |
| Persist `ValueError: artifact is immutable` on every refresh | `runId` includes wall-clock | `runId` from lineage+date only |
| Latest returns yesterday’s other hash | missing hash-scope | 503 `WAIT_S8_LINEAGE` |
| 2,633 candidates | assembled from R5 not S7 | S7 rows only |
| S2/S3 missing in blob | gap #10 not closed | pin or `WAIT_STAGE_ABSENT` |
| Two public states vs S7 GET | S8 re-scored | copy S7 `publicState` |
| POST 200 starts collector | File A POST misread | 405 this ticket |
| Frontend History empty | adapter name≠fetch count; stale JS | match counts; `?v=20260824-s8-1`; restart |
| New pytest fails | collection import / CONFIRMED validator | fix import; do not touch the known 6 |
| SQLite locked | two APIs | one uvicorn on :8000 |
| DuckDB / new `.db` | out of scope | delete; use `storage.connect()` |

---

## 9. GATES (write + run before claiming done)

Create `D:\TrendForge\delete\gates_s8_2026-08-24\GATES.md`. Debug until green.

```text
G1 module
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from trendforge_api.selection.s8_persist_run import SCHEMA_VERSION, PROFILE_ID, ACCEPTANCE_CEILING; print(SCHEMA_VERSION, PROFILE_ID, ACCEPTANCE_CEILING)"
EXPECT: trendforge.s8-scan.v1

G2 focused pytest
CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s8_persist_run.py tests/test_s7_state_gates.py -q --tb=short
EXPECT: passed

G3 no CONFIRMED / no broker
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from pathlib import Path; t=Path(r'D:\\TrendForge\\backend\\trendforge_api\\selection\\s8_persist_run.py').read_text(encoding='utf-8'); assert 'sourceActivationReady=True' not in t; assert 'Combined_Score' not in t; assert 'place_order' not in t; print('S8_CLEAN')"
EXPECT: S8_CLEAN

G4 live latest confirmedCount=0 + lineage
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/scans/latest')); print(d.get('confirmedCount', d.get('confirmed_count'))); assert d.get('confirmedCount', d.get('confirmed_count'))==0; lin=d.get('lineage') or {}; print('LIN', sorted(lin.keys()) if isinstance(lin,dict) else lin); assert d.get('runId') or d.get('run_id')"
EXPECT: 0

G5 POST 405
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import urllib.request,urllib.error; req=urllib.request.Request('http://127.0.0.1:8000/api/v1/selection/scans', method='POST', data=b'{}', headers={'Content-Type':'application/json'});
try:
 urllib.request.urlopen(req); print('BAD_200')
except urllib.error.HTTPError as e:
 print(e.code)"
EXPECT: 405

G6 reconstruct by runId
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "import json,urllib.request; a=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/scans/latest')); rid=a.get('runId') or a.get('run_id'); b=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/selection/scans/'+rid)); assert (a.get('runId') or a.get('run_id'))==(b.get('runId') or b.get('run_id')); assert (a.get('confirmedCount') or 0)==0; print('RECONSTRUCT_OK', rid)"
EXPECT: RECONSTRUCT_OK

G7 frontend
CHECK: node tests/acceptance-check.js
EXPECT: ok
CWD: D:\TrendForge\frontend
```

Stop. Do **not** open S9 until G1–G7 are observed green.
