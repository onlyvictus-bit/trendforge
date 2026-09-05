# Gates: S4 structure pack + S5 shortlist enrichment + S6 family resolution

OWNS: backend/trendforge_api/selection/s4_structure_pack.py, backend/trendforge_api/selection/s5_shortlist_enrichment.py, backend/trendforge_api/selection/s6_family_resolution.py, backend/tests/test_s4_structure_pack.py, backend/tests/test_s5_shortlist_enrichment.py, backend/tests/test_s6_family_resolution.py, backend/trendforge_api/main.py (S4/S5/S6 route additions only), frontend/s4-structure.js, frontend/s5-enrichment.js, frontend/s6-resolution.js, frontend/index.html (mount additions), frontend/styles.css (additions), frontend/selection-live-adapter.js (fetch additions), frontend/product-fixture.js (tag paint additions), frontend/tests/acceptance-check.js (check additions)

Scope: File A SEL-005/006/007 at WAIT ceiling — closed-bar structure pack over the R5 WAIT shortlist, bounded shortlist enrichment, and family resolution over S4+S5 claims; 0 CONFIRMED everywhere.

## S4 — SEL-005 structure pack

- [x] G4.1: S4 pack tests pass (T1-T9: unclosed/WAIT_CA no claims, one CG_PRICE_STRUCTURE rep, NR never CONFIRMED, pattern lane can_support_confirmed=false, non-empty nextTrigger+invalidation, lineage required, confirmedCount=0, POST 405)
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s4_structure_pack.py -q
  EXPECT: passed
  CWD: D:\TrendForge\backend
  EVIDENCE: 2026-08-24 final rerun exit 0: "8 passed, 1 warning in 6.07s" (tests/test_s4_structure_pack.py)
- [x] G4.2: Upstream R5/R14/S2 regression suite still passes
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_r5_live_structure.py tests/test_r14_live_ca_join.py tests/test_s2_market_weather.py -q
  EXPECT: passed
  CWD: D:\TrendForge\backend
  EVIDENCE: 2026-08-24 final rerun exit 0: "39 passed, 1 warning in 11.26s" (r5+r14+s2 regression)
- [x] G4.3: GET /api/v1/selection/s4-structure returns a WAIT pack with r14RunHash lineage and zero CONFIRMED from persisted hash-matched R5; POST is 405
  CHECK: covered by test_s4_structure_pack.py API test (G4.1) asserting runId/r14RunId/confirmedCount/post-405
  EXPECT: s4 api assertions passed
  CWD: D:\TrendForge\backend
  EVIDENCE: both API tests passed inside G4.1 final rerun (8 passed); GET 200 with r14RunId/r14RunHash/confirmedCount=0, POST 405, empty-db GET 503
- [x] G4.4: Frontend mounts s4-structure.js via adapter without breaking existing acceptance checks; All Stocks shows tags + next trigger while entry/t1/t2 stay non-executable labels
  CHECK: node tests/acceptance-check.js
  EXPECT: Summary: with 0 failed checks
  CWD: D:\TrendForge\frontend
  EVIDENCE: 2026-08-24 node acceptance-check exit 0 "Summary: 189/189 checks passed."

## S5 — SEL-006 shortlist enrichment

- [x] G5.1: S5 enrichment tests pass (T1-T11)
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s5_shortlist_enrichment.py -q
  EXPECT: passed
  CWD: D:\TrendForge\backend
  EVIDENCE: 2026-08-24 final rerun exit 0: "11 passed, 1 warning in 7.83s"
- [x] G5.2: R6/top10/R5/S2 regression suite still passes after S5
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_r6_live.py tests/test_top10_research.py tests/test_r5_live_structure.py tests/test_s2_market_weather.py -q
  EXPECT: passed
  CWD: D:\TrendForge\backend
  EVIDENCE: 2026-08-24 declared combo exit 0 "46 passed"; components rerun: r6+top10 "18 passed", r5/r14/s2 within "39 passed"
- [x] G5.3: Frontend acceptance still green with S5 chips wired through the extended adapter fetch list
  CHECK: node tests/acceptance-check.js
  EXPECT: Summary: with 0 failed checks
  CWD: D:\TrendForge\frontend
  EVIDENCE: 2026-08-24 node acceptance-check exit 0 "Summary: 191/191 checks passed."

## S6 — SEL-007 family resolution

- [x] G6.1: S6 resolution tests pass (T1-T11)
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s6_family_resolution.py -q
  EXPECT: passed
  CWD: D:\TrendForge\backend
  EVIDENCE: 2026-08-24 final rerun exit 0: "11 passed, 1 warning in 8.25s"
- [x] G6.2: Existing resolver/radar fusion regression suite still passes after S6
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_q5_family_resolver.py tests/test_evidence_radar.py tests/test_r5_live_structure.py tests/test_r6_live.py -q
  EXPECT: passed
  CWD: D:\TrendForge\backend
  EVIDENCE: 2026-08-24 declared combo exit 0 "66 passed"; components rerun: q5 resolver + radar "38 passed", r5/r14/s2 within "39 passed"
- [x] G6.3: Frontend acceptance still green with S6 inspector wiring (public states unchanged, no CONFIRMED from S6)
  CHECK: node tests/acceptance-check.js
  EXPECT: Summary: with 0 failed checks
  CWD: D:\TrendForge\frontend
  EVIDENCE: 2026-08-24 final rerun exit 0 "Summary: 193/193 checks passed."

## Docs (after observed tests)

- [x] GD.1: Docs record observed results only — fileindex.md entries, BUILD_STATUS.md append, DECISIONS.md D-047/D-048/D-049, VALIDATION.md counts, remaining_build README status rows, ARCHITECTURE.md lines
  CHECK: node scripts/check-s456-docs.mjs
  EXPECT: docs verification passed
  CWD: D:\TrendForge
  EVIDENCE: 2026-08-24 node exit 0 "docs verification passed: S4/S5/S6 patches present, out-of-scope items still open."

## Final audit (2026-08-24)

Met: 12 (G4.1-G4.4, G5.1-G5.3, G6.1-G6.3, GD.1). Unmet: 0. Abandoned: 0.
Out-of-scope remains open by design: S7 profile gates, R2-B unlock, R12 options
tree, File A first CONFIRMED.


## Audit round (2026-08-24, after external review): one family-resolution board

- [x] GA.1: /s6-resolution ingests merged_feed - cash FTR-040 unioned with R5 structure claims; one participation representative per CG_ACTIVITY_SESSION (injected 0.95 beats RVOL 0.833); real pipeline assembly mints FTR-040 at priority 0.9 without warnings
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s6_family_resolution.py -q
  EXPECT: passed
  CWD: D:\TrendForge\backend
  EVIDENCE: 2026-08-24 exit 0 "14 passed" (incl. test_s6_merged_cash_feed_competes_in_one_participation_group, test_s6_assembles_cash_feed_from_pipeline_inputs)
- [x] GA.2: rows bounded to the S4/S5 claimed shortlist; claim-less rows excluded (0 vs wide 1 on same lineage); wide diagnostics opt-out kept
  CHECK: covered by test_s6_bounded_to_shortlist_excludes_claimless_rows in the GA.1 run
  EXPECT: bounding assertions passed
  CWD: D:\TrendForge\backend
  EVIDENCE: same "14 passed" run
- [x] GA.3: surrounding system healthy - combined regression 69 passed; full backend suite fail count unchanged at the same 6 pre-existing unrelated failures
  CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s6_family_resolution.py tests/test_q5_family_resolver.py tests/test_evidence_radar.py tests/test_r5_live_structure.py tests/test_r6_live.py -q
  EXPECT: passed
  CWD: D:\TrendForge\backend
  EVIDENCE: "69 passed"; full-suite rerun "1162 passed / 6 failed" with identical failure list to pre-change baseline
- [x] GA.4: frontend acceptance still green; adapter CONTRACT guard unaffected (schema_version unchanged)
  CHECK: node tests/acceptance-check.js
  EXPECT: Summary: with 0 failed checks
  CWD: D:\TrendForge\frontend
  EVIDENCE: "Summary: 193/193 checks passed."
- [x] GA.5: docs record D-050 + audit-round counts; thin R3 route byte-for-byte unchanged
  CHECK: node scripts/check-s456-docs.mjs
  EXPECT: docs verification passed
  CWD: D:\TrendForge
  EVIDENCE: checker exit 0 incl. D-050 + "1162 passed / 6 failed" markers; r3_evidence_resolution body re-read unchanged

## Final audit v2 (2026-08-24 audit round)

Met: 17 (G4.x, G5.x, G6.x, GD.1, GA.1-GA.5). Unmet: 0. Abandoned: 0.
Still open by design: S7 profile gates, R2-B unlock, R12 options tree, File A
first CONFIRMED, deprecating thin /resolution (kept until consumers move).
