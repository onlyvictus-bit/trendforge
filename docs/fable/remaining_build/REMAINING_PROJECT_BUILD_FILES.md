<!-- CURRENT_STATE_HISTORY_BOUNDARY: requirement-1 -->
> **Current code/readiness summary (reviewed 2026-09-07): [../../CURRENT_STATE.md](../../CURRENT_STATE.md).**
> This file retains dated technical notes and historical observations below.
> Older phrases such as "current", "not implemented", "next" or "passed" describe
> their recorded checkpoint, not today's code, database, freshness or permissions.
> File A remains plan authority. Historical counts never grant runtime activation.

<!-- HISTORICAL_CHECKPOINTS_START: original content preserved below -->

# Remaining Project Build — Required Files Map

**Date:** 2026-07-20 (code map refreshed 2026-08-16 for remaining R1 DTO / R2 attention)  
**Status:** Checklist only — not a third architecture plan  
**Authority:** Build order from File A; domain detail from File B via §25 / CSV; mapped product/design detail from `FINAL_MERGE_PLAN.md` via File A §25.21.

Q5-R0…Q5-R7 are complete at research/fixture ceilings. Below is what you need
open to finish the **remaining** research-only product (R0–R2 residuals, R4/R6,
live S0–S3, R8–R18, CROSS and TDG-GAP code).

---

### Current checkpoint - 2026-09-03

- Built: R0-C quarantine/API, live R1/R2, WAIT-only R3, R4-R8,
  R10-R16, R17-B-F/H/I and R18-A-E at their documented ceilings.
- Data-gated: R16 has one complete S8 date and remains PIT_NOT_APPROVED.
- Postponed: R9 and R17-G.
- Approval-gated: R18 migration 0014 is not applied; MODEL_NOT_APPROVED remains
  mandatory until R16 PIT/OOS approval.
- CROSS-015 / TDG-GAP-022: unified tradability gate is implemented through S7,
  S8, read-only API and inspector. ESM/band/auction acquisition is wired to the
  existing 126-job collector and canonical last-good store; sources remain
  non-voting and unactivated.

## 1. Document Priority Map

This table is a navigation checklist, not an instruction to read every file in
full during every milestone. Use the priorities as follows:

- **P0:** read before every milestone.
- **P1:** read when the selected milestone touches that document's ownership.
- **P2:** supporting policy or navigation reference; open when relevant.
- **P3:** preserved audit/history evidence only; never implementation authority.
- **History only:** do not use for current build decisions.

After choosing a milestone from File A and checking `BUILD_STATUS.md` and
`VALIDATION.md`, use Section 2 of this file to locate the smallest relevant code
and test surface. If this map conflicts with File A, current code evidence, or
an approved decision, stop and correct the map; never make implementation match
an obsolete map entry.

| Priority | Path | Role |
|---|---|---|
| P0 | `AGENTS.md` | Engineering and safety rules; read first |
| P0 | `docs/fable/new_merge_PLAN_2026-07-18.md` | File A — sequence, scope, IDs, ceilings, §0.5 and §25 |
| P0 | `docs/fable/remaining_build/README.md` | AI/human execution guide for remaining build |
| P0 | `docs/BUILD_STATUS.md` | Current implementation status |
| P0 | `docs/VALIDATION.md` | Observed proof and limitations |
| P1 | `docs/DECISIONS.md` | Lasting technical and scope decisions |
| P1 | `TREND_FORGE_ARCHITECTURE.md` | Full system boundaries |
| P1 | `TREND_FORGE_SOURCE_REGISTRY.md` | Source meaning, authority and freshness |
| P1 | `docs/ARCHITECTURE.md` | Current module ownership |
| P1 | `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` | File B detail library; open only through File A pointers |
| P1 | `docs/fable/FINAL_MERGE_PLAN.md` | Mandatory mapped product/design addendum; open through File A §25.21 FMR crosswalk |
| P1 | `data/reports/SOURCE_LINK_INVENTORY_MASTER.xlsx` | Current URL inventory counts/keys |
| P1 | `docs/fable/remaining_build/PLAN_REQUIREMENT_COVERAGE.csv` | Traceability only; never build authority |
| P2 | `docs/DEPENDENCIES.md` | License and dependency decisions |
| P2 | `fileindex.md` | Navigation only |
| P3 | `docs/fable/remaining_build/TRENDFORGE_GOVERNANCE_SYSTEM_ai.md` | Preserved external advisory; no authority |
| P3 | `docs/fable/remaining_build/TWO_DOCUMENT_GOVERNANCE_SYSTEM_2026-07-20.md` | Preserved analysis |
| P3 | `docs/fable/remaining_build/INDEPENDENT_AUDIT_merge_plan_build_matrix_2026-07-20.md` | Q5 code-matrix evidence |
| P3 | `docs/fable/remaining_build/INDEPENDENT_AUDIT_hybrid_vs_new_merge_2026-07-20.md` | Hybrid-gap evidence |
| — | `docs/fable/TRENDFORGE_STOCK_SCREENER_MERGE_PLAN_2026-07-18.md` | History only — not remaining build |

---

## 2. Code areas by remaining milestone

| Work | Primary code paths | Tests |
|---|---|---|
| **R0 residual / inventory compiler** | R0-A closed. R0-B: `source_cohort_r0b.py`, `source_extended_field_proofs.py`, r0b-cohort API. R0-C quarantine contract + `GET /api/source-inventory/r0c-cohort` are complete at zero-authority ceiling. C0: `selection/use_matrix_c0.py`, `GET /api/source-inventory/use-matrix`. R0 remains partial for source-specific proofs, maturity history, mirror/resolver values and activation review | `test_r0_*`, `test_r0c_source_cohort.py`, `test_cash_a5_c1.py` (C0 matrix) |
| **R1 live evidence DTO** | **Done.** `inventory_source_bundle.py`, `GET /api/v1/selection/evidence` | `test_inventory_source_bundle.py`. Do not rebuild. `/api/radar` is not R1 |
| **R2 live attention** | **Done.** `attention_order.py`, `shadow_screener.py`, `GET /api/v1/selection/attention`. File A **R2-B activation still closed** | `test_attention_order.py`. PRIMARY forbidden. Workbench is not this ranker |

| **R3 live evidence-family resolution** | **Done 2026-08-16 at WAIT-only ceiling.** selection/r3_live.py consumes hash-matched R1/R2 artifacts; its GET route fails closed on mismatched lineage | Recorded focused/full verification. No CONFIRMED, geometry, intraday, MCX, options or event activation |
| **R4/R6 residual PK/enrichment** | `scanners/pk_compatibility.py`, `selection/enrichment.py` | bounded enrichment and PK tests |
| **R9 lifecycle / ORB / VWAP** | history/lifecycle and verified-bar modules | closed-bar and lifecycle tests |
| **CROSS-003/025 jobs J01–J14** | contracts / registry schema | new unit tests |
| **CROSS-004 / TDG-GAP-014 PRF sources** | **Done 2026-09-02.** `selection/profile_source_contracts.py` + `GET /api/v1/selection/profile-source-contracts`; seven exact mandatory/confirmation/veto contracts; registration never means data-ready | `test_profile_source_contracts.py`; focused 5, backend 1,458, frontend 219/219 |
| **CROSS-008 ban/MWPL** | `parsers/nse_mwpl_parser.py`, safety | `test_safety_engine`, surveillance |
| **CROSS-014 / FUS-008 legacy scorer** | `intraday_stock_details.py` | call-graph + DTO tests |
| **CROSS-015 / TDG-GAP-022 tradability** | **Done 2026-09-03 at code/runtime fail-closed ceiling.** `selection/tradability.py`; S7 override; S8 hash/component lineage; GET batch/symbol routes; S7 inspector; ESM/band/auction acquisition via canonical collector/store | `test_tradability_gate.py`, `test_tradability_sources.py`, `test_s7_state_gates.py`, `test_s8_persist_run.py`. Current: ESM populated, band populated, auction valid-empty; missing/stale/malformed still WAIT; PASS non-voting; no activation or execution |
| **R8 native scanners** | **Done 2026-08-25.** `scanners/registry.py`, `scanners/native_core.py`, routes `GET /api/v1/scanners/{definitions,native-core,native-core/{symbol}}`, POST `/scanners/run` 405; S3 `nativeCoreMatches` attach (rank-safe); S6 `merge_native_claims` empty-group ingest; frontend `native-core.js` + `#nativeCorePanel` | `test_r8_native_core.py`. Wraps R5 FTR-006/007/017 claims; one representative per group; PK shadow isolated; confirmedCount pinned 0 |
| **R10 pipes** | **Done 2026-08-26.** `scanners/pipe_dsl.py` (FUS-010: UNION/INTERSECTION/FILTER_STATE/ENRICH_S7; zero emitted claims; invalid stage fails run), routes `GET /api/v1/pipes/{definitions,{pipe_id}/run}`, POST `/pipes/run` 405; frontend `pipes.js` + `#pipeLabPanel` | `test_r10_pipes.py`. Two seeded recipes, STO-016 hashes, twin non-inflation, deterministic counts |
| **R9 ORB/VWAP** | **SKIPPED by operator 2026-08-25** until verified intraday bars exist (OPENALGO_RO lane or free NRT source). CSV stays PARTIAL | revisit with R17 lane enablement |
| **R11 MCX master + swing gates** | **Done 2026-08-25 (readiness board).** `selection/r11_mcx_live.py` + routes `/api/v1/selection/mcx-master{,/{symbol}}` + POST 405; frontend `mcx-master.js` + `#mcxMasterPanel`. PRF-005/006/007 profiles remain EMPTY until named MCX activation | `test_r11_mcx_live.py`. WAIT without official master+local bars; tender veto; FBIL/CFTC context-only |
| **R12 options timeline/API and FMR-003..008** | **Done 2026-08-25.** `options_intelligence/` walls/Greeks/claims (`r12_options_claims.py`), guidance-only confirmation; OI rooms live BFFs | options identity, chain quality, strike/OI, Gamma/GEX scenario guidance |
| **R13 remaining scanners** | **Guidance-grade closure verified 2026-08-27.** Registry remains 11. Six chips-only scanners now use pinned VCP/TTM/trend/Wilder-RSI/reversal/extremes formulas over adjusted, closed, hash-matched PIT bars loaded once per batch. Claimless representatives are selected separately; all suppressed siblings remain inspectable. Native hash/representative IDs attach additively to the versioned S8 blob | `test_r13_remaining_scanners.py` plus native-core/S8/lab integration. Focused 60, deterministic regression 61, full backend 1320, frontend 217/217, read-only battery 24/24. Zero claims/confirmation/state/rank/direction mutations. Current stored S8 remains `WAIT_S8_LINEAGE` until the next authorized daily scan |
| **R14 CA/sponsor reconciliation** | **Done 2026-08-21 at WAIT-only ceiling.** selection/r14_live.py owns official CA and identity continuity; R5 requires the hash-matched join | test_r14_live_ca_join.py plus R5 integration; no vote, rank, geometry or confirmation authority |
| **R15 Scanner Lab UI + FMR-009/FMR-011 (UI shell)** | **Lab DONE 2026-08-25.** `frontend/scanner-lab.js` (inspector tab: Definitions / Pipe flow / Symbol / PK shadow) + backend one-fetch `GET /api/v1/scanners/lab-bundle`; radar columns frozen. Full FMR-009/011 workspace layout still open | `test_r15_lab.py` + acceptance-check. No Combined_Score; no second scoreboard on All Stocks |
| **R16 PIT dataset/replay substrate** | **Code and schema present; runtime data-gated.** r16 pit/store/service/metrics, migration 0013 and frontend validation provide immutable replay, labels, metrics and read-only projection. State: BUILDING / PIT_NOT_APPROVED | test_r16_pit.py and recorded regression. More PIT dates, OOS folds, costs and calibration are required |
| **R17 live OpenAlgo** | **R17-B-F and H/I fixture-verified. R17-G POSTPONED_BY_USER 2026-09-01.** The approved bounded attempt resolved 10/10 identities, observed populated intervals, fixed TrendForge `60m` compatibility, then failed closed on an invalid stored Kite session. OpenAlgo remains optional, read-only and non-authoritative | Focused R17/OpenAlgo 132; backend 1,435; frontend 218/218 plus shadow check. No quote/replay/stream proof and no `SHADOW_LIVE`. Resume only after a fresh Kite login and new approval |
| **R18 model governance + FMR-011** | **R18-A-E CODED + fixture-verified 2026-09-02.** r18_governance.py, r18_store.py, migration 0014, /api/research/ml/governance, review-only POST, and existing Paper/ML panel. Runtime remains MODEL_NOT_APPROVED | Focused 14; backend 1,449; frontend 219/219 plus R18 test. Live schema application and actual promotion remain blocked by separate migration approval and R16 PIT_NOT_APPROVED |
| **Durable selection storage** | **PARTIAL done 2026-08-15:** migration 0007 + `selection_scan_runs` / `selection_candidates` / `selection_state_events` (WAIT only). Further claim-stream tables still need approval | `test_r1_live_decision.py` + migration tests |

Existing Q5 code to **extend**, not replace:

```text
backend/trendforge_api/selection/
backend/trendforge_api/scanners/
backend/trendforge_api/openalgo_client.py
frontend/q5-contract.js
frontend/index.html
frontend/app.js
backend/tests/test_q5_*.py
frontend/tests/
```

---

## 3. Suggested build order (after Q5)

1. Read `AGENTS.md`, File A preamble/Section 0.5/Section 24.13, current BUILD_STATUS and VALIDATION, then use this file to locate the selected vertical's code and tests.
2. Run generator `--check`; select every `P0` row in `PLANNED` or `PARTIAL` for the chosen vertical.
3. R0 residual inventory/contracts and all linked CROSS/TDG/Hybrid rows.
4. Durable storage immediately after R0 only when migration is explicitly approved.
5. R1 + R2 are **live**. Do not rebuild. Do not treat the workbench as their page.
6. **R3 = locked plan §13 only** (adapter + FUS-009 WAIT diagnostics; R2 list unchanged). Then R4 IDs. R14 CA join **before** any live R5 CONFIRMED.
7. R6 shortlist enrich (extend A6). R8 native scanners — not workbench `screener.js`. R9 only on verified bars.
8. R10 pipe DSL (zero claims) before R11/R12 live MCX/options. R11 WAIT without MCX master. R12 from option last-good jobs, not catalog companions.
9. R13 remaining scanners. **R15 is TrendForge Scanner Lab / FINAL_PRODUCT IA**, not `/inventory-workbench`.
10. R16 production PIT before performance/probability UI.
11. R17-G is `POSTPONED_BY_USER`; resume its bounded live proof only after a fresh Kite login and new approval. R9 stays postponed with it.
12. **R18-A-E CODED + fixture-verified.** Next gates are separately approved migration 0014 and sufficient R16 PIT/OOS evidence; no model promotion is currently allowed.

**Never in current scope:** ExecutionProvider orders, INR quantity product UI, probability UI before PIT_APPROVED.

---

## 4. How to use the CSV

```text
# validate without writing
python docs/fable/remaining_build/build_coverage_csv.py --check

# after generator rows and diff are reviewed
python docs/fable/remaining_build/build_coverage_csv.py --accept-reviewed-changes

# remaining P0 planned work (example PowerShell)
Import-Csv docs\fable\remaining_build\PLAN_REQUIREMENT_COVERAGE.csv |
  Where-Object { $_.priority -eq 'P0' -and $_.status -in 'PLANNED','PARTIAL' } |
  Select-Object requirement_id, merge_milestone, requirement, hybrid_reference
```

---

## 5. Completion of remaining product (definition)

Remaining research product is **not** complete until:

- No P0 row stays PLANNED without an owner milestone  
- Live S0–S3 returns honest WATCH/WAIT/REJECT with completeness  
- Durable history/PIT if claimed  
- R8 core scanners under family caps  
- CSV `evidence_level` matches the claim type; fixture/runtime-boundary proof is not live-source proof  
- BUILD_STATUS + VALIDATION updated  

No production-ready claim without File A acceptance observation.



