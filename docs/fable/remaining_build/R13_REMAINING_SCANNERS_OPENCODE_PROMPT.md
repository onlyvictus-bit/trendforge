# R13 Guidance-Grade Native Scanner Closure (PK4)
## VCP / squeeze / trend overlay / momentum / reversal / extremes · family batches · chips-only · no extra votes

Status: implemented and reverified 2026-08-27. Run **section 6 GATES** before
changing the formula or guidance contracts.

Working tree: `D:\TrendForge`
Python: `D:\TrendForge\.venv\Scripts\python.exe`
OS: Windows. PowerShell. `;` not `&&`.
**Date: 2026-08-27.** R8/R10/R11/R12/R15 have bounded implementations;
R9 remains explicitly skipped. This R13 closure is guidance-only and does not
mean all R8-R15 work or production readiness is complete.

Also read: `TRADE_GUIDANCE_LAW_2026-08-25.md`. Public state = **S7**. FUS-009
first-wins for claim evidence remains in `representative_matches`. Claimless
R13 display deduplication is separately owned by
`native_core.representative_guidance_chips`. Pipe (R10) emits zero claims.

---

## 0. What R13 adds (bounded families)

| Scanner ID | FTR | Family / group | Rule |
|---|---|---|---|
| `native.vcp.v1` | FTR-008 | STRUCTURE / `CG_COMPRESSION` | >=61 adjusted closed bars; confirmed radius-2 pivots; three successively smaller contractions; recent/prior median volume <=0.70; compression only |
| `native.ttm_squeeze.v1` | FTR-009 | STRUCTURE / `CG_COMPRESSION` | BB(20,2) fully inside KC(20, EMA20 +/- 1.5*ATR10); shares COMPRESSION group with NR/VCP -> ONE representative |
| `native.trend_overlay.v1` | FTR-012 | STRUCTURE / `CG_TREND_OVERLAYS` | SMA20 vs SMA50 state chip (direction context); needs 51 bars else `INPUT_INCOMPLETE_WARMUP` |
| `native.momentum.v1` | FTR-013 | STRUCTURE / `CG_MOMENTUM_OSCILLATORS` | Pure-Python Wilder RSI14 over exactly 14 initial differences; >50 bullish, <50 bearish, 50 neutral |
| `native.reversal.v1` | FTR-014 | STRUCTURE / `CG_REVERSAL` | Symmetric bullish failed-breakdown reclaim and bearish failed-breakout rejection around the PIT R5 reference level |
| `native.extremes.v1` | FTR-015 | STRUCTURE / `CG_PRICE_STRUCTURE` | Explicit `10D_HIGH/LOW` and `52W_HIGH/LOW`; current bar excluded; valid 10-day result survives with 52-week component pending |

All: `can_support_confirmed=false`; chips-only (see §L); guidance copy
“R13 native — trade guidance, not an order.” **No ORB/VWAP** (R9 skipped).

## L. CHIPS-ONLY LAW (amendment #2 — locked)

R5 mints NO upstream claims for these six features. R13 therefore mints **zero
EvidenceClaims**: matches are guidance chips citing `(scanner_id, why,
lookback_used)` only. No `EvidenceClaim(` anywhere in new code; S6/S7 owners
untouched; FUS-010 purity preserved. Registry contracts already carry the
correct families/groups — introspected, not invented.

## M. MATH REUSE (amendment — audit correction)

R13 uses one shared pure-Python Wilder RSI14 implementation in
`native_extended.py`; it does not reuse `institutional_features._rsi`.
TTM uses BB SMA20/population standard deviation and KC EMA20 +/- 1.5 times
Wilder ATR10 true range. STO-016 parameters remain sorted JSON plus SHA-256.
SuperTrend is not built by this ticket; the trend overlay is close/SMA20/SMA50.

## 0.1 Expected output (observed)

1. `GET /api/v1/scanners/definitions` = R8 five **plus** these six (11 total).
2. `GET /api/v1/scanners/native-core`: new chips per symbol where honest;
   claimless chips expose relationship/metrics/formula/parameter/lineage fields;
   `representative_guidance_chips` selects one per family/group while all
   suppressed chips remain inspectable;
   `confirmedCount=0`.
3. Primary native-core radar shows representative guidance only. Scanner Lab
   receives the full native run from its existing bundle and shows formula,
   parameters, metrics, adjustment and lineage. No All Stocks column changes.
4. POST `/scanners/run` 405. Hash-match spine guard unchanged (503 typed).
5. Cash S7 / pipe / MCX / lab suites green.

## W. Folder map

```text
EXTEND
  scanners/registry.py                     (+6 specs)
  scanners/native_core.py                  (bulk adjusted-PIT adapter + guidance)
  selection/r5_live.py                     (public reuse alias for adjusted bars)
  selection/s8_persist_run.py              (native hash + representative ids)
  selection/scan_orchestrator.py           (normal S8 build attachment)
  main.py                                  (lab bundle + S8 attachment)
  frontend/{native-core.js,scanner-lab.js,index.html}
  tests/test_r8_native_core.py             (registry-grew law: contains-the-five)
  frontend/tests/acceptance-check.js       (representative/inspector contract)
CREATE
  tests/test_r13_remaining_scanners.py
  delete/gates_r13_scanners_2026-08-26/GATES.md
  delete/r13_wip_2026-08-26/
DOCS after GATES
  BUILD_STATUS.md, VALIDATION.md, DECISIONS.md D-058 R13_FAMILY_BATCHES_CHIPS_ONLY,
  remaining_build/{README.md, REMAINING_PROJECT_BUILD_FILES.md}, ARCHITECTURE.md row,
  fileindex.md, PLAN_REQUIREMENT_COVERAGE.csv (R13 seed refresh + regenerate)
```

## 1. Formula ceilings (honest)

- Warmup/history short -> no match + `INPUT_INCOMPLETE_*` reason (never zero-signal).
- VCP pivots ambiguous -> skip (documented reason).
- RSI period pinned 14; all params in sorted JSON + hash.
- 52w lookback = 252 completed sessions excluding current bar.
- EOD closed bars only; no intraday queries.

## 2. UI

Primary radar shows one representative chip per family with
SUPPORTS/CONFLICTS/NEUTRAL/UNKNOWN. Scanner Lab shows all matches, suppressed
siblings, formula version, parameters, metrics, as-of, adjustment and lineage.
No R13 probability or trade geometry is displayed. Do not add All Stocks
columns (existing `<th>` freeze assertions stay).

## 3. Tests `test_r13_remaining_scanners.py`

1. Registry grew: >=11 ids; the original five still present; hashes stable.
2. Chips-only: source scan — no `EvidenceClaim(` / `place_order` in
   scanners/*; matches carry no claim ids.
3. Compression twins: NR + squeeze (+VCP shape) same symbol -> exactly ONE
   CG_COMPRESSION representative; others marked correlated_possible.
4. PRICE_STRUCTURE: breakout + 10d-high -> ONE representative.
5. Momentum: RSI14 trusted fixture; >50 bullish, <50 bearish, =50 neutral;
   short history -> INPUT_INCOMPLETE_WARMUP.
6. Reversal: bullish and bearish symmetry plus no-reclaim fixture.
7. Extremes off-by-one: current bar excluded — series where including the
   current bar would falsely fire must NOT fire.
8. Trend overlay: 51-bar fixture gives direction chip; short -> incomplete.
9. `confirmedCount=0`; POST 405; no `orb|vwap` module created.
10. Adjusted bars, future-bar cutoff, lineage failure, one bulk query, S8
    attachment, API compatibility and hard-veto regressions.

## 4. Test-data note

`store_breakout_history(days=N)` accepts arbitrary N — use days=260 for
extremes/overlay; add ONE small shape-controlled generator in the R13 test
file for VCP (decreasing ranges + dry-up) and squeeze (tight BB/KC) shapes.

## 6. GATES

`delete/gates_r13_scanners_2026-08-26/GATES.md`

```text
G1 registry grew
CHECK: python -c "from trendforge_api.scanners.registry import NATIVE_CORE_IDS; print(len(NATIVE_CORE_IDS))"
EXPECT: 11
G2 pytest
CHECK: pytest tests/test_r13_remaining_scanners.py tests/test_r8_native_core.py tests/test_r10_pipes.py tests/test_s7_state_gates.py -q
EXPECT: passed
G3 frontend
CHECK: node tests/acceptance-check.js
EXPECT: 0 failed checks
G4 full backend: 1320 passed, 0 failed (2026-08-27)
G5 read-only live battery: PASS 24/24 with one denominator
G6 frontend acceptance: 217/217
```

Observed real-universe run: 2,623 rows, 2,379 with at least one native match,
`confirmedCount=0`; native-core took about 14-19 seconds and lab about 32-34
seconds. S8 remained `WAIT_S8_LINEAGE` until the next authorized daily scan
persists the new native-guidance hash. R9 remains skipped.
