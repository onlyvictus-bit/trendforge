# OPENCODE BUILD PROMPT — File A R8 native core scanners (PK3)
## Registry: breakout / compression / volume / NR / trend · family caps · S3 may consume · PK shadow never votes

Copy **this entire file**. Load skills. Think. Build. Run **§9 GATES**.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. `;` not `&&`.  
**Date: 2026-08-25.** Tickets 1–4 of the S9/R12/R2-B pack are **coded**. This is the next File A vertical: **R8**.

Also read: `TRADE_GUIDANCE_LAW_2026-08-25.md` (guidance chips OK; live `placeorder` stays gated). D-053 already owns CONFIRMED.

Skills: `using-superpowers` → `unlazy` → `verification-before-completion` → `systematic-debugging` → `test-driven-development` → `requesting-code-review`.

Authority: File A §15 R8 / S3 SEL-004 “native core” / STO-016 / FUS-009 family caps / PK-007. Hybrid §16.8 formulas where File A points. Existing: `scanners/pk_compatibility.py` (shadow), `selection/structure.py` + R5 (closed-bar tags), S3 cheap discovery (no native registry yet).

---

## 0. What R8 is

| R8 IS | R8 is NOT |
|---|---|
| One **native** scanner registry: breakout, compression (NR), volume/RVOL, trend | Rebuilding R5 bar engine |
| Versioned definitions + `parameter_hash` (STO-016) | PK catalog as a vote (PK stays **shadow**) |
| Claims into existing families: STRUCTURE / PARTICIPATION, groups `CG_PRICE_STRUCTURE`, `CG_COMPRESSION`, `CG_ACTIVITY_SESSION` | A second fuse / Combined_Score |
| S3 **may** attach match chips as cheap facts | R10 pipe DSL (next after R8) |
| Trade **guidance** labels (“matched breakout — guidance”) | Live orders, win % as P(win) |
| Fixture parity documented | R13 remaining scanners |

Public state stays **S7**. Scanners never write `CONFIRMED`. They may set `guidanceMatch=true` on a row (user guidance law).

---

## 0.1 Outcome (observed)

1. `GET /api/v1/scanners/definitions` lists the five native cores with id, version, engine `trendforge.numpy-pandas`, family, group, `parameterHash`, `authority=NATIVE`, `pkShadow=false`.  
2. `GET /api/v1/scanners/run/latest` (or `/scanners/native-core`) returns last hash-matched run: per symbol match/fail, lookback, claim_ids, completeness. `confirmedCount=0`.  
3. Correlation: two breakout-like tags same CG_PRICE_STRUCTURE → **one** representative (FUS-009). Match **counts** labelled `correlated_possible`, never independent confirms.  
4. S3 cheap-discovery optionally shows `nativeCoreMatches[]` without re-ranking R2.  
5. PK compatibility worker still isolated; failure cannot change S7 state.  
6. POST `/scanners/run` → 405 this ticket (no dual-start collector). Compute on GET from last-good A4/R5 like S4.  
7. Frontend: inspector **Scanner Lab** tab (or `#nativeCorePanel` in Live Ops) lists matches. Copy: “Native core — trade guidance, not an order.”

---

## W. Folder map

```text
CREATE
  D:\TrendForge\backend\trendforge_api\scanners\native_core.py
  D:\TrendForge\backend\trendforge_api\scanners\registry.py
  D:\TrendForge\backend\tests\test_r8_native_core.py
  D:\TrendForge\frontend\native-core.js
  D:\TrendForge\delete\gates_r8_native_2026-08-25\GATES.md

EXTEND
  D:\TrendForge\backend\trendforge_api\main.py
      GET /api/v1/scanners/definitions
      GET /api/v1/scanners/native-core
      GET /api/v1/scanners/native-core/{symbol}
      POST /api/v1/scanners/run → 405
  D:\TrendForge\backend\trendforge_api\selection\s3_cheap_discovery.py
      optional nativeCoreMatches; do not change rank
  D:\TrendForge\backend\trendforge_api\selection\s6_family_resolution.py
      ingest native STRUCTURE/PARTICIPATION claims if minted (same groups as R5 — first-wins claim_id)
  frontend/index.html, selection-live-adapter.js, acceptance-check.js, styles.css
  docs/BUILD_STATUS.md, VALIDATION.md, DECISIONS.md (D-0xx R8_NATIVE_CORE)
```

Reuse `analyze_closed_bar_structure` / R5 tags. **Do not** fork a third structure engine. Native core **wraps** those formulas as versioned scanners.

PK: `scanners/pk_compatibility.py` remains shadow. R8 definitions must set `pkCompatible=true` only as **parity fixture**, `canVote=false`.

---

## 1. The five cores (minimum)

| Scanner ID | Family / group | Uses | Guidance copy |
|---|---|---|---|
| `native.breakout.v1` | STRUCTURE / CG_PRICE_STRUCTURE | R5 breakout/acceptance | “Breakout matched — guidance” |
| `native.nr_compression.v1` | STRUCTURE / CG_COMPRESSION | NR7/NR | “Compression — max WATCH unless S7” |
| `native.trend.v1` | STRUCTURE / CG_PRICE_STRUCTURE | closed trend | same CG as breakout → one rep |
| `native.rvol.v1` | PARTICIPATION / CG_ACTIVITY_SESSION | RVOL EOD | same CG as cash FTR-040 |
| `native.volume_thrust.v1` | PARTICIPATION / CG_ACTIVITY_SESSION | volume spike vs PIT baseline | not a second volume vote |

Each definition: `scannerId`, `version`, `engine`, `parameters` (sorted JSON), `parameterHash=SHA256`, `minBars`, `family`, `group`, `can_support_confirmed=false` (S7 still owns CONFIRMED via R2-B).

Run identity: `runId` includes definition hashes + R5/R14 hashes. Mismatch → 503.

Universe: S3/R2 eligible cash rows, or S5 shortlist if you must bound CPU — **document which**. Prefer full R2 like S3 if one A4 set-query stays fast.

---

## 2. Trade guidance (user law)

- Match chips and `guidanceWinRate` **from S9 homework joined by scannerId later** — this ticket may show `guidanceMatch` only. Do not invent a scanner win % without S9 labels.  
- Guidance OMS (ticket 4) may list `nativeCoreMatches` on the paper ticket as **why**.  
- No Combined_Score. No live `placeorder` from a scanner match.

---

## 3. Frontend

No new nav group. Mount `#nativeCorePanel` in inspector Scanner Lab / Live Ops.

`native-core.js?v=20260825-r8-1`  
`TrendForgeNativeCore.apply(batch)`  
Adapter +1 fetch `/api/v1/scanners/native-core` (count = names).

---

## 4. Tests `test_r8_native_core.py`

1. Definitions count ≥ 5; hashes stable.  
2. Breakout + trend same symbol → one STRUCTURE representative in S6 (or documented first-wins).  
3. RVOL + FTR-040 same CG → one PARTICIPATION rep.  
4. PK shadow failure does not change S7 publicState.  
5. `confirmedCount=0` on scanner DTO.  
6. POST `/scanners/run` 405.  
7. Hash mismatch 503.  
8. S3 rank unchanged when native matches attached.  
9. No `place_order` in `scanners/`.  
10. R5/S3/S7/R2-B tests still pass.

---

## 5. GATES

`D:\TrendForge\delete\gates_r8_native_2026-08-25\GATES.md`

```text
G1 module
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from trendforge_api.scanners.registry import NATIVE_CORE_IDS; print(len(NATIVE_CORE_IDS), ','.join(NATIVE_CORE_IDS))"
EXPECT: 5
CWD: D:\TrendForge\backend

G2 pytest
CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_r8_native_core.py tests/test_s3_cheap_discovery.py tests/test_s7_state_gates.py -q --tb=short
EXPECT: passed
CWD: D:\TrendForge\backend

G3 frontend
CHECK: node tests/acceptance-check.js
EXPECT: 0 failed checks
CWD: D:\TrendForge\frontend
```

If the registry export name differs, print the real names; EXPECT can be the token `NATIVE_CORE_OK` from a small print.

Stop. **Do not start R9/R10** in this ticket. After GATES: data ops still needed for R2-B live CONFIRMED (stale `nse_bhavcopy_eod` / CA / index). R8 does not wait on that.
