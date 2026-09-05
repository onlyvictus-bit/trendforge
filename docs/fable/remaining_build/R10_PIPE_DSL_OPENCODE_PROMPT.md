# OPENCODE BUILD PROMPT — File A R10 pipe DSL + family caps (PK5)
## FUS-010 composition over R8 native cores · deterministic stage counts · zero emitted claims

Copy **this entire file**. Load skills. Think. Build. Run **§5 GATES**.

Working tree: `D:\TrendForge`
Python: `D:\TrendForge\.venv\Scripts\python.exe`
OS: Windows. PowerShell. `;` not `&&`.
**Date: 2026-08-26.** R8 native core registry is CODED. This is **R10**.
**R9 is SKIPPED by operator decision 2026-08-25** (no verified intraday bars;
revisit only when OPENALGO_RO lane or a free NRT source lands).

Also read: `TRADE_GUIDANCE_LAW_2026-08-25.md`. D-053 owns CONFIRMED (S7/R2-B).
Authority: File A §15 R10 row, §21.13 amendment row (**Apply FUS-010**),
FUS-010 full contract (§25 CROSS table): ops `INTERSECTION` / `UNION` /
`SEQUENCE` / `ENRICH` determine candidate membership only; the pipe emits
**zero evidence claims**; component claims keep their own family/group and
pass through FUS-009; **invalid stage fails the pipe run**; no majority- or
highest-family reassignment. Hybrid §16.8 formulas stay inside R5/R8 (pipes
never recompute features). STO-016 versioning applies.

---

## 0. What R10 is

| R10 IS | R10 is NOT |
|---|---|
| A versioned **pipe DSL**: ordered stages that FILTER the R8 native-core match set | New scanner math or a third engine |
| Deterministic per-stage in/out counts + capped reasons | Vote source: pipe contributes **zero claims** (FUS-010) |
| Guidance lens for the future Scanner Lab (R15) | Re-ranking R2/S3; touching S7 publicState |
| Seeded definitions in code (STO-016 hashes), compute-on-GET | User-editable runtime store; POST runner |
| Invalid stage ⇒ whole run fails typed | Silent skip / partial pipe |

## 0.1 Outcome (observed)

1. `GET /api/v1/pipes/definitions` lists ≥2 seeded pipes with id, version,
   engine `trendforge.numpy-pandas`, sorted-JSON stages, `parameterHash`,
   `emitsClaims=false`.
2. `GET /api/v1/pipes/{pipe_id}/run` returns the last-lineage run: ordered
   stage results (`op`, in/out counts, distinct exclusion reasons capped at 8),
   surviving symbols in native-core order, `confirmedCount=0`, `executable=false`.
3. Twin safety: `UNION`/`INTERSECTION` count **symbols**, so correlated twins
   (breakout+trend on one claim) can never inflate a stage count.
4. `ENRICH_S7` attaches publicState/guidanceMatch to survivors; it never filters.
5. Unknown pipe id → 404; spine not ready / lineage mismatch → 503 typed code;
   POST `/api/v1/pipes/run` → 405.
6. Frontend `#pipeLabPanel` (Live Ops): per-pipe stage survivor chips + copy
   “Pipes — guidance lens, zero claims.”
7. No new writes: pipes persist nothing this ticket.

## W. Folder map

```text
CREATE
  backend/trendforge_api/scanners/pipe_dsl.py      # FUS-010 engine + seeds
  backend/tests/test_r10_pipes.py
  frontend/pipes.js
  delete/gates_r10_pipes_2026-08-26/GATES.md

EXTEND
  backend/trendforge_api/main.py                   # 4 routes above
  frontend/index.html, selection-live-adapter.js (+1 fetch = 18),
  acceptance-check.js, styles.css
  docs/BUILD_STATUS.md, VALIDATION.md, DECISIONS.md (D-055 incl. R9 skip),
  docs/fable/remaining_build/{README.md, REMAINING_PROJECT_BUILD_FILES.md},
  fileindex.md, PLAN_REQUIREMENT_COVERAGE.csv (R10 -> IMPLEMENTED via seed)

NOTE
  File A names `pk_pipe_dsl.py`; that name stays reserved for the PK shadow
  harness. The LIVE module is `scanners/pipe_dsl.py` — PK may import it later.
  Record this mapping in DECISIONS.
```

## 1. Stage grammar (v1 — exactly these four + enrich)

| Stage | Params | Semantics |
|---|---|---|
| `UNION` | `scanners:[id…]` | survivors ∪= symbols matched by any listed native scanner (within stage: symbol counted once) |
| `INTERSECTION` | `scanners:[id…]` | survivors ∩= symbols matched by ALL listed scanners |
| `FILTER_STATE` | `states:[WATCH,WAIT,REJECT]` | keep survivors whose joined S7 `publicState` ∈ set |
| `ENRICH_S7` | `{}` | attach `publicState` + `guidanceMatch` to survivors; never filters |

Rules: first stage MUST be `UNION` or `INTERSECTION` (else run fails);
unknown scanner id or unknown op ⇒ run fails typed (`PIPE_INVALID_STAGE`);
stage reasons list first 8 distinct exclusion codes (e.g.
`SCANNER_NOT_MATCHED:native.breakout.v1`). Pipe identity hashes stage JSON +
native-core run hash (+ s7 run hash when FILTER_STATE/ENRICH used).

Seeds (minimum): `pipe.breakout_watch.v1`
(`UNION[breakout] → FILTER_STATE[WATCH] → ENRICH_S7`) and
`pipe.thrust_participation.v1` (`UNION[rvol,volume_thrust] → INTERSECTION?
no — keep UNION → FILTER_STATE[WATCH,WAIT] → ENRICH_S7`).

## 2. Law

- Pipes emit **zero claims** (FUS-010): output DTO carries symbols/counts/
  labels only — no claim ids, no EvidenceClaim construction anywhere in the
  new module. Component claims remain owned by R5/R8 and S6.
- Public state stays S7/R2-B. `confirmedCount` pinned 0. `executable=false`.
- Guidance copy only; no win % (that waits for S9 join by scannerId).

## 3. Frontend

No new nav group. `#pipeLabPanel` under Live Ops after `#nativeCorePanel`.
`pipes.js?v=20260826-r10-1`; `TrendForgePipeLab.apply(batch)`; adapter fetch #18
`GET /api/v1/pipes/definitions` + per-seed runs fetched by the panel itself.

## 4. Tests `test_r10_pipes.py`

1. ≥2 seeds; hashes stable across calls; `emitsClaims=False` pinned literal.
2. Deterministic: two builds on same spine → identical rows/stage counts/hash.
3. Stage math: out(last)==len(rows_out); every stage out ≤ in; reasons ≤8.
4. Twin non-inflation: UNION[breakout,trend] out-count == UNION[breakout] count
   on fixture where both fire on the same symbol.
5. Zero-claims: no `EvidenceClaim(` string in `scanners/pipe_dsl.py`;
   validator raises if confirmed_count ≠ 0.
6. Invalid stage (unknown op / unknown scanner / non-scanner first stage)
   fails run with typed error.
7. Routes: definitions 200 ≥2; unknown pipe 404; POST run 405; empty-spine 503.
8. ENRICH_S7 never removes a survivor (in==out for that stage).
9. `place_order` absent from `scanners/pipe_dsl.py`.
10. Regressions: r8/s3/s7 suites green.

## 5. GATES

`delete/gates_r10_pipes_2026-08-26/GATES.md`

```text
G1 module
CHECK: .venv python -c "from trendforge_api.scanners.pipe_dsl import PIPE_IDS; print(len(PIPE_IDS), ','.join(PIPE_IDS))"
EXPECT: starts with "2 "
G2 pytest
CHECK: pytest tests/test_r10_pipes.py tests/test_r8_native_core.py tests/test_s3_cheap_discovery.py tests/test_s7_state_gates.py -q
EXPECT: passed
G3 frontend
CHECK: node tests/acceptance-check.js   (CWD frontend)
EXPECT: 0 failed checks
```

Stop. Do not start R11/R13/R15. After GATES: update docs + CSV seed
(R10 → IMPLEMENTED) and record D-055 (R9 skip + FUS-010 module-name mapping).
