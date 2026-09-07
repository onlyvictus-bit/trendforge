<!-- CURRENT_STATE_HISTORY_BOUNDARY: requirement-1 -->
> **Current code/readiness summary (reviewed 2026-09-07): [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md).**
> This file retains dated technical notes and historical observations below.
> Older phrases such as "current", "not implemented", "next" or "passed" describe
> their recorded checkpoint, not today's code, database, freshness or permissions.
> File A remains plan authority. Historical counts never grant runtime activation.

<!-- HISTORICAL_CHECKPOINTS_START: original content preserved below -->

## Price-band + technical-zones build plan (2026-09-04, PLAN only)

- Plan: `docs/fable/remaining_build/PRICE_BAND_TECHNICAL_ZONES_BUILD_PLAN_2026-09-04.md`
  (16 sections: rule matrix, calculation contract, feature contracts, gates, 50 tests).
  Covers three blocked parts — price-band boundary geometry, R5 hash-matched rebuild,
  sourceActivationReady unlock — with deep-plan council verdict (calculated geometry,
  78% confidence) and triangulated grade A.
- Verified 2026-09-04: band/ESM/auction checkpoint is REAL in the normalized store
  (`nse_price_bands` 3,517 rows, `nse_esm` 290 rows, auction NIL valid-empty);
  R5 gap and activation lock are data-ops/governance consequences, not code bugs.

## R13 guidance-grade native scanners (2026-08-27)

- Backend: `backend/trendforge_api/scanners/native_extended.py` — six
  chips-only scanners over adjusted PIT closed EOD bars: confirmed-pivot VCP,
  canonical TTM squeeze, close/SMA20/SMA50 overlay, pure-Python Wilder RSI14,
  symmetric failed-break reversal and explicit 10d/52w extremes.
- Data/lineage: `scanners/native_core.py` bulk-loads once and reuses
  `selection/r5_live.py` R5/R14 adjustment; missing lineage fails closed.
- Guidance/S8: claimless family representatives remain separate from claim
  representatives; `selection/s8_persist_run.py` and `scan_orchestrator.py`
  attach only the native hash and representative ids.
- Frontend: `frontend/native-core.js` shows representative relationship chips;
  `frontend/scanner-lab.js` shows every match/suppression and formula lineage.
- Tests: `backend/tests/test_r13_remaining_scanners.py`; GATES
  `delete/gates_r13_scanners_2026-08-26/GATES.md`.

## R15 Scanner Lab UI (2026-08-25)

- Frontend: `frontend/scanner-lab.js?v=20260827-r13-guidance-1` — registers a Scanner
  Lab tab inside `#q5Inspector` (Definitions / Pipe flow / Symbol / PK shadow
  sub-tabs); mounts `#scannerLabPanel` `#scannerLabTabs` `#scannerLabBody`.
  All Stocks columns frozen (no `<th>` from lab owners).
- Backend: one-fetch BFF `GET /api/v1/scanners/lab-bundle` (native definitions,
  full native-core guidance or typed native-core failure code, both seeded pipe
  runs and PK parity state; named inner codes on unhealthy spine; POST 405).
- Symbol view: all matches and suppressed correlated siblings with relationship,
  input status, formula/parameter values, metrics, as-of, adjustment and lineage;
  no R13 win-rate, entry, target, stop or confirmation claim.
- Button: `#scannerRunButton` relabelled "Refresh lab (GET)" — GET refresh
  only, legacy scanner fire disconnected.
- Tests: `backend/tests/test_r15_lab.py`; GATES
  `delete/gates_r15_lab_2026-08-25/GATES.md`.

## R11 MCX master readiness (2026-08-25)

- Backend: `backend/trendforge_api/selection/r11_mcx_live.py` — honest
  readiness board (WAIT_MCX_MASTER / WAIT_MCX_LOCAL_BARS / WAIT_MCX_STALE /
  WAIT_MCX_CALENDAR / READY), per-row lot/tick/expiry/dte/tender with named
  why-codes; FBIL/CFTC/WGC context-only; PRF-005/006/007 stay empty via
  `mcx_profile_blocker`. Swing gates: `swing_delivery_gate`, `swing_rs_gate`.
- Routes: GET `/api/v1/selection/mcx-master{,/{symbol}}`; POST → 405.
- Frontend: `frontend/mcx-master.js`; mounts `#mcxMasterPanel` +
  `#mcxMasterMeta` (Live Ops); MCX segment re-loads live status; adapter
  fetch #19.
- Tests: `backend/tests/test_r11_mcx_live.py`; GATES
  `delete/gates_r11_mcx_2026-08-25/GATES.md`.

## R10 pipe DSL (2026-08-26)

- Backend: `backend/trendforge_api/scanners/pipe_dsl.py` — FUS-010 non-voting
  composition over R8 native-core matches. Ops: UNION / INTERSECTION /
  FILTER_STATE / ENRICH_S7; first stage must be a scanner stage; invalid stage
  fails the run (`PIPE_INVALID_STAGE`); pipes emit ZERO claims; stage counts
  are symbol counts (twins cannot inflate). Seeds:
  `pipe.breakout_watch.v1`, `pipe.thrust_participation.v1`.
- Routes: GET `/api/v1/pipes/definitions`, GET `/api/v1/pipes/{pipe_id}/run`;
  POST `/api/v1/pipes/run` → 405.
- Frontend: `frontend/pipes.js`; mounts `#pipeLabPanel` (Live Ops);
  adapter fetch #18 (definitions).
- Tests: `backend/tests/test_r10_pipes.py`; GATES
  `delete/gates_r10_pipes_2026-08-26/GATES.md`.

## R8 native core scanners (2026-08-25)

- Backend: `backend/trendforge_api/scanners/registry.py` (five versioned
  definitions, stable `parameterHash`) and
  `backend/trendforge_api/scanners/native_core.py` (run builder wrapping R5
  FTR-006/007/017 claims; one representative per correlation group;
  correlated twins labelled; PK shadow isolated; confirmedCount pinned 0).
- Routes: GET `/api/v1/scanners/definitions`,
  `/api/v1/scanners/native-core{,/{symbol}}`; POST `/api/v1/scanners/run` → 405.
- S3: optional batch-level `nativeCoreMatches` (rows byte-identical, rank safe);
  S6 helper `merge_native_claims` fills empty groups only.
- Frontend: `frontend/native-core.js`; mounts `#nativeCorePanel` (Live Ops);
  adapter fetch #17.
- Tests: `backend/tests/test_r8_native_core.py`; GATES
  `delete/gates_r8_native_2026-08-25/GATES.md`.

## R2-B CONFIRMED amendment + guidance OMS (2026-08-25)

- Backend: `backend/trendforge_api/selection/r2b_live.py` v2 (observed
  five-source flip), `s7_state_gates.py` amendment gates,
  `guidance_oms.py` (paper ticket + preview + triple-gated live path).
- Routes: GET/POST `/api/v1/selection/guidance-oms/{symbol,preview,place}`;
  GET/POST `/api/v1/settings/live-orders-arm`. Default boot = preview only;
  place returns 409 `LIVE_ORDERS_ARMED_OFF`.
- Frontend: `frontend/guidance-oms.js` (`#guidanceOmsPanel`, `#armLiveOrders`
  default off); header chip flips to `CONFIRMED EOD PRF-003 ONLY` when ready.
- Tests: `tests/test_guidance_oms.py`; GATES
  `delete/gates_r2b_confirmed_2026-08-25/GATES.md`.

## S4 / S5 / S6 remaining OpenCode prompts (2026-08-24)

File A §9 `SEL-005/006/007` only. Not Hybrid p̂. S7 CONFIRMED out of scope.

- S4: `docs/fable/remaining_build/S4_STRUCTURE_PACK_OPENCODE_PROMPT.md`
- S5: `docs/fable/remaining_build/S5_SHORTLIST_ENRICHMENT_OPENCODE_PROMPT.md`
- S6: `docs/fable/remaining_build/S6_FAMILY_RESOLUTION_OPENCODE_PROMPT.md`

## S4/S5/S6 implementation (coded WAIT, 2026-08-24)

- **S4 (SEL-005):** `backend/trendforge_api/selection/s4_structure_pack.py`;
  tests `backend/tests/test_s4_structure_pack.py`; routes
  `GET /api/v1/selection/s4-structure` (+POST 405) sharing the hash-matched
  R5 guard; frontend `frontend/s4-structure.js` mounted at `#s4StructurePanel`
  (Structure Lab) and `#s4StructureOps` (Live Ops); All Stocks paints tags +
  next trigger through the adapter while geometry stays "NONE — R5 research,
  not a trade". One CG_PRICE_STRUCTURE representative per row; pattern lane
  display-only; ceiling `LIVE_S4_WAIT_REJECT_ONLY`, confirmedCount=0.
- **S5 (SEL-006):** `backend/trendforge_api/selection/s5_shortlist_enrichment.py`;
  tests `backend/tests/test_s5_shortlist_enrichment.py`; route
  `GET /api/v1/selection/s5-enrichment` (+POST 405); bounded to the S4
  structure-claimed shortlist; delivery EOD-only with INTRADAY forbidden guard;
  OPTIONS_PACKAGE=UNKNOWN_NEEDS_R12 score 0; market FII chip only; frontend
  `frontend/s5-enrichment.js` at `#s5EnrichmentPanel` (All Stocks) and
  `#s5EnrichmentOps` (Live Ops). Ceiling `LIVE_S5_ENRICH_WAIT_ONLY`.
- **S6 (SEL-007):** `backend/trendforge_api/selection/s6_family_resolution.py`;
  tests `backend/tests/test_s6_family_resolution.py`; route
  `GET /api/v1/selection/s6-resolution` (+POST 405); resolves the merged_feed
  (cash FTR-040 ∪ R5 structure claims, one representative per correlation
  group) with required families read from the active versioned profile object;
  rows bounded to the S4/S5 claimed shortlist; family support/oppose map +
  conflict + "Evidence strength - not win probability"; frontend
  `frontend/s6-resolution.js` Decision view at `#s6InspectorMount` (Evidence
  Inspector) plus research records appended to `#liveDecisionList` and panel
  `#s6ResolutionPanel`. Ceiling `LIVE_S6_RESOLVE_WAIT_ONLY`. NOT S7, NOT
  CONFIRMED. Thin R3 `GET /api/v1/selection/resolution` stays diagnostic (D-049,
  D-050).

## S8 persist-one-reconstructable-scan (2026-08-25)

- `backend/trendforge_api/selection/s8_persist_run.py` — ONE immutable blob
  per scan run (lineage S2–S7, weather block, completeness tuple,
  changeKinds vs prior run, STO-008 state events).
- Store helpers: `get_selection_payload`, `list_latest_selection_payloads`.
- Routes: GET `/api/v1/selection/scans{,/latest,/{run_id},/{run_id}/candidates[,/{symbol}]}`;
  POST ×2 → 405.
- Frontend: `frontend/s8-persist.js`; mounts `#s8HistoryPanel`.
- Tests: `backend/tests/test_s8_persist_run.py`.

## S6 claim-feed widening (2026-08-24 evening)

- `backend/trendforge_api/selection/s6_claim_feed.py` — merges R5-published
  structure claims into the FUS-009 feed (dedupe by claim_id); S2 weather as
  display-only `market_context` on `R3ResolutionV1`.
- `r5_live.py` rows now publish minted `claims`/`facts` (schema v2, profile
  1.1.0; boundary validator rejects confirming claims).
- Tests: `backend/tests/test_s6_claim_feed.py`. Callers opt in; ceilings
  unchanged; not CONFIRMED.

## S9 PIT homework (2026-08-25)

- Backend: `backend/trendforge_api/selection/s9_pit_homework.py`.
- Routes: GET `/api/v1/selection/pit-homework{,/{symbol}}`; POST → 405.
- Frontend: `frontend/s9-pit-homework.js`; mounts `#s9PitHomeworkPanel`,
  replaces `#q5ValidationLock` copy.
- Tests: `backend/tests/test_s9_pit_homework.py`.

## S0-S9 run overlay map (navigation, 2026-08-24)

`docs/fable/S0_S9_RUN_OVERLAY_MAP_2026-08-24.md` — readability funnel drawn ON
File A §9 with verified R-tags and labelled overlays. Crosswalk only; not a
third S-map; no law change.

## S3 cheap discovery (implemented, 2026-08-24)

- Backend: `backend/trendforge_api/selection/s3_cheap_discovery.py`.
- Tests: `backend/tests/test_s3_cheap_discovery.py`.
- Frontend: `frontend/s3-cheap-discovery.js`; mounts `#s3WatchQueue` and
  `#s3WatchQueueOps` through `selection-live-adapter.js`.
- Routes: `GET /api/v1/selection/cheap-discovery` and
  `GET /api/v1/selection/cheap-discovery/watch?limit=50`; POST is 405.
- Contract: scans the full current R2 universe without rebuilding A3/R2,
  preserves R2 order, adds cheap discovery tags, and reports explicit
  completeness plus missing/unknown reasons. Delivery is excluded and the
  ceiling is `LIVE_S3_WATCH_WAIT_ONLY` with zero `CONFIRMED`.
- Performance: A4 history is loaded in one symbol-set query; benchmark history
  is cached once per run instead of queried per stock.
- Build contract retained at
  `docs/fable/remaining_build/S3_CHEAP_DISCOVERY_OPENCODE_PROMPT.md` for
  verification and debugging; do not rebuild it as a second ranker.

## S2 market weather (2026-08-22)

New: backend/trendforge_api/selection/s2_market_weather.py,
backend/tests/test_s2_market_weather.py, frontend/s2-market-weather.js.
Routes GET /api/v1/selection/market-weather{,/sectors}. Live Ops panel
#s2WeatherStrip. Prompt: docs/fable/remaining_build/S2_MARKET_WEATHER_OPENCODE_PROMPT.md.
## Evidence radar + R6 shortlist + top-10 (2026-08-22)

**New files:** ackend/trendforge_api/selection/evidence_radar/
(__init__.py, catalog.py, slots.py, calculate.py, use.py,
explain.py, oards.py, coverage.py),
ackend/trendforge_api/selection/r6_live.py,
ackend/trendforge_api/selection/top10_research.py,
ackend/tests/test_evidence_radar.py, ackend/tests/test_r6_live.py,
ackend/tests/test_top10_research.py,
rontend/evidence-radar.js, rontend/top10-research.js.

Routes: GET /api/v1/selection/evidence-radar{,/coverage,/boards},
GET /api/v1/selection/enrichment, GET /api/v1/selection/top10.
Panels: Live Ops #evidenceRadarPanel (horizon tabs, coverage strip) and
#top10ResearchPanel (labelled R6 shortlist stickers).
Prompt: docs/fable/remaining_build/THIRD_EYE_EVIDENCE_RADAR_OPENCODE_PROMPT.md.
# TrendForge â€” Document Index (navigation only)

## Current UI and compiler pin (2026-08-15)

- Live host: `http://127.0.0.1:8000/` â€” FINAL_PRODUCT chrome + Live Ops remounts.
- Source Health page: `#sources` + `#sourceHealthLadder` read-only compiler counts.
- Live Ops: `#maturityLadder` from `GET /api/source-inventory/compiler-report`.
- Live Ops decisions: `#liveDecisionPanel` â€” `GET /api/v1/selection/live` (latest
  stored run or ephemeral WAIT) and `POST /api/v1/selection/live/refresh` (persist).
- Inventory glass: `/inventory-workbench/` frozen snapshot, not evidence.
- Compiler pin: `f1abcdce2b451b4ded9d9e9c8eb6bd63fae82853803f60bef60a1651dd52eb0b`.
- Status: H1A0 6/6, 32 overlap dispositions, `sourceActivationReady=false`,
  `gateAuthorized=0`, frontend acceptance **163/163**.
- **R0-A** closed. **R0-B** field-reviewed (`provenCount=0`, `canVote=false`).
  **R0-C** quarantined. File A Â§25.20.1.
- **Cash research path A1â€“C1 (implemented):**
  - A1 `.../cash-staging/*` â€” SourceResult + staging rows
  - A2 `.../cash-identity/*` â€” NormalizedFact + S0/S1
  - A3 `.../cash-discovery/*` â€” Â§25.25.4 WATCH reasons
  - A4 `.../cash-history/*` â€” RAW bars + CA vintages
  - A5 `.../cash-context/*` â€” index context + CA integrity
  - A6 `.../fo-enrichment/*` â€” futures-only shortlist enrich
  - C0 `GET /api/source-inventory/use-matrix` â€” can_rank/can_veto
  - B `.../mwpl/assess` â€” MWPL_MISSING unless proven
  - C1 `.../cash-rank/*` â€” attention rank if can_rank (WATCH ceiling)
- **R1/R2 remaining:** live evidence DTO + attention order. Cash A1â€“C1 done. Workbench is **not** the R1/R2 stock page.
- **R3:** live WAIT-only FUS-009 (FTR-040). Locked how-to remains `R0_R1_R2_LOCKED_PLAN` **Â§13**.
- **R4:** live ID pin + PK0 inventory digest. `GET /api/v1/selection/identity-pin`.
  Uses A2 IDs; does **not** rebuild A2/A4. `r4_fixtures.py` is Q5-R4 fixture only.
  PK cannot vote. R4 cannot change R2/R3/R5 or emit CONFIRMED.
- **R5:** live WAIT-only closed-bar structure. `GET /api/v1/selection/structure`.
  Setup tags are not buys. `confirmedCount=0`. NSE clock is IST
  (`PRE_OPEN` / `OPEN` / `EOD_WINDOW` / `CLOSED_NON_TRADING`). Index close is
  an A5 companion, not a 124th job. R5 **requires a hash-matched R14 CA join**
  (`r14RunId`/`r14RunHash` on the batch; mismatch â†’ 503 `R5_R14_JOIN_NOT_READY`).
  R15 â‰  workbench. No live CONFIRMED, no named activation, no qty.
- **R14:** live official CA / identity-continuity join at `LIVE_CA_JOIN_WAIT_ONLY`.
  `GET /api/v1/selection/ca-join` (hash-scoped to current R1/R2 + R4 pin; POST 405).
  **New files:** `backend/trendforge_api/selection/r14_live.py`,
  `backend/tests/test_r14_live_ca_join.py`. Reuses
  `corporate_actions.reconcile_corporate_actions` (DAT-022); never rewrites it.
  Pipeline is R3 â†’ R4 â†’ R14 â†’ R5 (`a1-c1-r1-r2-r3-r4-r14-r5-orchestrator-7`).
  Future CA (`available_at > decision_at`) stays hidden; conflict / identity-break /
  unresolved CA â†’ `WAIT_CA_*` and R5 drops `claim_ids`; RAW bars never mutate
  (STO-020; adjusted series via `series_layers.open_adjusted_series`).
  Build prompt: `docs/fable/remaining_build/R14_LIVE_CA_JOIN_GLM_PROMPT.md`.
  **Hybrid V2 overlay (not File A, not R2-B):** remaining paper code prompt:
  `docs/fable/remaining_build/HYBRID_V2_OVERLAY_OPEN_MODEL_PROMPT.md`.
  **R6 shortlist (coded):** `GET /api/v1/selection/top10` â€” WATCH-40 sticker sort, not 3rd-eye.
  Prompt: `docs/fable/remaining_build/R6_TOP10_OPENCODE_PROMPT.md`.
  **File A S2 market weather (coded WAIT):** `GET /api/v1/selection/market-weather`.
  **File A S3 cheap discovery (coded):** full current R2 universe at
  `LIVE_S3_WATCH_WAIT_ONLY`; preserves R2 order, reports partial-scan accounting,
  no second ranker, no second volume vote, and no delivery.
  Routes: `GET /api/v1/selection/cheap-discovery{,/watch}`. Build contract:
  `docs/fable/remaining_build/S3_CHEAP_DISCOVERY_OPENCODE_PROMPT.md`.
  **3rd-eye evidence radar:** all 123 jobs as typed slots; four
  horizons Ã— BUY/SELL; how/what/where/when; nothing skipped = UNKNOWN slot, not
  165 votes. Prompt:
  `docs/fable/remaining_build/THIRD_EYE_EVIDENCE_RADAR_OPENCODE_PROMPT.md`.
  Live CONFIRMED still needs R2-B **unlock**, which is not the named-activation ledger.
- **R2-B named activation ledger (WAIT-only, not unlock):**
  `GET /api/v1/selection/named-activation`.
  New files: `backend/trendforge_api/selection/r2b_live.py`,
  `backend/tests/test_r2b_live_named_activation.py`,
  `frontend/r2b-activation.js`. `#r2bActivationPanel`.
  Names R0-B official sources. `sourceActivationReady` stays **false**.
  `authorizedCount=0`. `maySupportConfirmed=false`. Does **not** unlock CONFIRMED.
  R0-B: five confirm-path sources can be **proven**; MWPL stays unproven /
  confirm-ineligible (no official % file). Shared NSE domain breaker is proven.
  Draft activation note (not executed):
  `docs/fable/remaining_build/FILE_A_R2B_ACTIVATION_AMENDMENT_DRAFT.md`.
- **Hybrid S4/S5 paper A/B (overlay, not File A):** `GET /api/v1/selection/s4s5-compare`
  + `#s4s5ComparePanel` checkboxes WITH / WITHOUT / BOTH. Both original compressed
  and split formulas stay until you pick after paper days. `RESEARCH_PROXY_NOT_CALIBRATED`.
  Not rank. Not size. Not CONFIRMED.
  **New files:** `backend/trendforge_api/selection/s4s5_compare.py`,
  `backend/tests/test_s4s5_compare.py`, `frontend/s4s5-compare.js`.
  **Wired in:** `backend/trendforge_api/main.py`, `frontend/index.html`,
  `frontend/styles.css`, `frontend/tests/acceptance-check.js`.
- Plan: `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md`.
- Final Merge FMR status note: `docs/fable/FINAL_MERGE_PLAN.md` (top evidence section).
- Architecture: `docs/ARCHITECTURE.md`, `TREND_FORGE_ARCHITECTURE.md`.
- Evidence: top of `docs/BUILD_STATUS.md` and `docs/VALIDATION.md` (A1â€“C1 **19 passed**).

## Official BSE/RBI and calculated-output files (current, 2026-08-11)

- `backend/trendforge_api/parsers/official_replacement_parser.py` - pure,
  fail-closed BSE filing-index and RBI auction-result parsers.
- `backend/trendforge_api/derived_market_outputs.py` - exact-industry peer,
  assumptions-labelled Greeks, prospective PCR/Max-Pain and fail-closed ratio
  materialization with immutable zero-score fields.
- `backend/tests/test_official_replacement_sources.py` and
  `test_derived_market_outputs.py` - schema/date/empty/retry, lineage,
  missing-value and idempotent persistence coverage.
- `config/source_refresh_registry_69.csv` and
  `config/source_refresh_profiles.yaml` - current **123** source contracts.
- `docs/fable/MD69_REFRESH_OPERATION_REFERENCE.md` - acquisition and
  post-source calculated-output flow.
- Inventory projection: `D:\trendforge_inventory_app\links_105.json`, **165
  rows**. Calculated outputs are not catalog links.
- Third-party FII holding screens (INFO, collected + inventory strip): intake
  in `docs/fable/ADD_40_SCREENER_LINKS_PLAN.md`. Command-room UI still open
  (`TF-APP-FII-M1`). Helper `scripts/incoming_40pack/fii_sources.py` is audit-only.

## Pack 7 additions (historical, 2026-08-11)

- `docs/fable/evidence/FILE1_2_3_INTEGRATION_AUDIT_20260811.md` - current
  per-family production coverage and populated last-good proof for files 1-3.
- `docs/fable/evidence/pack7-20260811/PACK7_SOURCE_RECONCILIATION.json` - exact
  17-candidate terminal ledger and official access evidence.
- `backend/tests/test_pack7_source_reconciliation.py` - classification,
  registry reuse, no-broker-path and no-invented-Greeks assertions.
- Pack 7 adds no new source key; the existing Pack-6 option-chain acquisition,
  archive, parser and last-good flow remains authoritative.

## Pack 6 additions and changes (2026-08-11)

- `backend/trendforge_api/parsers/supplemental_market_parser.py` - NSE
  option-chain parser v1.1.0 identity fallback and fail-closed validation.
- `backend/tests/test_nse_option_chain_parser.py` - v3 identity and fail-closed
  regression fixtures.
- `backend/tests/test_pack6_source_reconciliation.py` - 10/10 candidate ledger,
  production-key reuse and no-second-ingestion tests.
- `docs/fable/evidence/pack6-20260811/PACK6_SOURCE_RECONCILIATION.json` - exact
  classifications and live attempt evidence.

## Pack 5 implementation pointers (2026-08-11)

- `backend/trendforge_api/parsers/pack5_public_sources_parser.py` - NSE market
  status and RupeeVest deterministic normalization.
- `backend/trendforge_api/parsers/supplemental_market_parser.py` - PIT v1.1
  direction/lineage normalization.
- `backend/trendforge_api/phase3_multi_step_fetch.py` and `source_resolver.py` -
  bounded public acquisition and fail-closed multi-step status.
- `backend/trendforge_api/market_data_service.py` - source-row lineage and
  successful-transport note handling.
- `backend/tests/test_pack5_public_sources.py` and
  `backend/tests/test_supplemental_market_sources.py` - golden/failure tests.

## 2026-08-05 manual collector additions

- `backend/trendforge_api/market_data_scheduler.py` - registry-driven manual
  all-source run, last-good manifest projection, single-flight coordinator.
- `backend/trendforge_api/main.py` - localhost refresh start/status API.
- `backend/trendforge_api/cli.py` - `market-data run-all` operations entry.
- `backend/trendforge_api/market_data_alignment.py` - committed current or
  last-good files projected into research panels.
- `backend/tests/test_market_data_scheduler.py`, `test_live_panels.py`, and
  `test_market_data_alignment.py` - deterministic refresh/fallback tests.

**Role:** Navigation and path finding only.  

## Current MD69 operations reference

| Path | Role |
|---|---|
| `docs/fable/MD69_REFRESH_OPERATION_REFERENCE.md` | Verified owner/code map, scheduled/manual refresh flow, last-good policy, panel mapping, controlled source add/remove procedure and tests |
| `docs/fable/MD69_PARAMETER_RESOLUTION_REVIEW_2026-08-06.md` | Five-source parameter repair, bounded dependency flow, live 69-source manifest evidence and caveats |
| `docs/fable/MD69_REMAINING_SOURCE_REPAIRS_2026-08-06.md` | Seven remaining-source transport/parser repairs, focused regression evidence and observed live canary counts |
| `docs/fable/MD69_SAVED_PANEL_OVERLAY_REPAIR_2026-08-06.md` | Saved-manifest display repair, dynamic supporting overlay, MISSED-audit fallback, forced post-Refresh reread and observed panel evidence |
| `config/source_refresh_registry_69.csv` | Hash-pinned current collection release source rows |
| `config/source_refresh_profiles.yaml` | Typed acquisition, parameter, normalizer, validator and reuse mapping |
**Not authority.** Build order, states, ceilings, and acceptance remain File A (`docs/fable/new_merge_PLAN_2026-07-18.md`) plus `AGENTS.md`.

**Updated:** 2026-08-01 â€” restored navigation index; File A Â§9.3 S0â€“S9 crosswalk pointer; no stale keep-token placeholders.

---

## Authority order (short)

1. Current user instruction + `AGENTS.md`
2. File A â€” `docs/fable/new_merge_PLAN_2026-07-18.md` (`R0â€“R18`, four states)
3. Final Merge addendum â€” `docs/fable/FINAL_MERGE_PLAN.md` (`FMR-001..011` via File A Â§25.21)
4. Decisions â€” `docs/DECISIONS.md`
5. Hybrid File B â€” `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` (formulas only when File A points)
6. Discovery / Options detail plans (never build order)
7. Evidence: runtime + `docs/BUILD_STATUS.md` + `docs/VALIDATION.md`
- Archived plans live under `delete\plans_archived_2026-08-19\` (provenance ledger: `delete\merge_his\PLAN_MERGE_HISTORY_2026-08-19.md`; not authority).

---

## Core governing docs

| Path | Role |
|---|---|
| `AGENTS.md` | Engineering and safety rules |
| `docs/fable/new_merge_PLAN_2026-07-18.md` | **File A** â€” only build sequence; Â§9 SEL S0â€“S9; Â§9.3 FMR story crosswalk; Â§10 states; Â§11 fusion |
| `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` | **File B (Hybrid only)** â€” inventory, formulas, ops detail |
| `docs/fable/FINAL_MERGE_PLAN.md` | Mandatory FMR product/design addendum (`FMR-001..011`) |
| `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` | Discovery Detail Plan â€” modes Aâ€“E, E1/E2, integrity G1â€“G8; not File B |
| `docs/OPTIONS_INTELLIGENCE_PLAN.md` | Options Detail Plan â€” one package; Â§18 hybrid truth-behind-maths playbook (stock/strike/expiry + claim classes); no Combined_Score; options never alone CONFIRMED |
| `docs/DECISIONS.md` | Lasting decisions (D-025 inventory, D-028 Final Merge, D-029 Single Build Spine, D-030 math detail, â€¦) |
| `TREND_FORGE_ARCHITECTURE.md` | System-boundary architecture reference |
| `TREND_FORGE_SOURCE_REGISTRY.md` | Source meaning and authority notes |
| `docs/ARCHITECTURE.md` | Executable module map (current code layout) |

### Pipeline ID rule

- **Build stages:** File A Â§9 `S0â€“S9` / `SEL-001..010` only.
- **FMR-002 `S0â€“S9`:** story labels only â€” map via File A **Â§9.3**.
- Do not invent a third S-map. Do not use Discovery `M/T/PK` as work selectors.

---

## Remaining build pack

| Path | Role |
|---|---|
| `docs/fable/remaining_build/README.md` | AI/human next-step guide; Hybrid open-list; R0 residual checklist |
| `docs/fable/remaining_build/PLAN_REQUIREMENT_COVERAGE.csv` | Traceability matrix (not authority) |
| `docs/fable/remaining_build/build_coverage_csv.py` | Coverage generator + governance validators |
| `docs/fable/remaining_build/test_build_coverage_csv.py` | Governance tests |
| `docs/fable/remaining_build/REMAINING_PROJECT_BUILD_FILES.md` | Code/doc location checklist |

---

## Status and validation

| Path | Role |
|---|---|
| `docs/BUILD_STATUS.md` | Implementation status history (append-only) |
| `docs/VALIDATION.md` | Observed proof and limitations (append-only) |

---

## Product preview and math

### `docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md`

Research mathematics detail reference (EV, barrier, OI codes, Theta, VRP context).  
**Not** a build authority. Open only through File A section 25.22.  
Cannot set public state, activate sources, authorize quantity/execution, or show win% before R16/R18 + `PIT_APPROVED`.

Want professional trading math? Start at that file, then return to File A gates and FUS-009.

| Path | Role |
|---|---|
| `docs/TRENDFORGE_FINAL_PRODUCT.html` | Canonical static product-vision fixture for operations header, All Stocks table/cards, side-by-side research decisions, Stock Evidence, Elliott/harmonic Structure Lab, replay/model shells and read-only Inventory Workbench drawer. Visual target only; runtime R15/R16/R18 remain open. |
| `frontend/inventory-workbench/` | Independent hash-pinned static copy of the Inventory Workbench runtime, catalog and linked reference docs, served at `/inventory-workbench/`; manifest proves the allow-list and source parity. Host drawer presents it at desktop `95vw x 96vh` and mobile `100vw x 100dvh`. Read-only discovery glass only. |
| `frontend/tests/inventory-workbench.test.js` | Verifies all copied hashes, required script order, excluded debris, same-origin drawer routing and final desktop/mobile drawer rules. |

---

## Options research references (detail, not build order)

| Path | Role |
|---|---|
| `docs/GITHUB_OI_CHAIN_REFERENCE_REPOS.md` | External OI/chain repo notes (fallback research) |
| `grok_plan/shadowflow_deep_dive.md` | Options package deep law (when Options plan points) |
| `grok_plan/convexity_intelligence_engine.md` | Surface studies detail (when Options plan points) |

---

## Code roots (implementation evidence)

| Path | Role |
|---|---|
| `backend/trendforge_api/` | Backend package |
| `backend/tests/` | Backend tests |
| `frontend/` | Frontend app and checks |
| `data/` | Runtime data / reports / raw archives |

### Pack-2 context-source implementation (2026-08-10)

| Path | Role |
|---|---|
| `backend/trendforge_api/phase3_multi_step_fetch.py` | Existing bounded fetchers for BDI, BDRY and Google RSS |
| `backend/trendforge_api/parsers/file2_context_parser.py` | Fail-closed normalization and proxy/context labels |
| `backend/trendforge_api/source_resolver.py` | Routes the three registry keys to the existing fetchers |
| `backend/trendforge_api/source_monitor.py` | Authority, cadence, limitation and raw archive descriptors |
| `backend/tests/test_file2_context_sources.py` | Empty/schema/proxy/date/resolver/last-good/scheduler tests |
| `config/source_refresh_registry_69.csv` | Legacy filename; current hash-pinned count is **104** |

---

## Naming lock (quick)

| Name | Means |
|---|---|
| File A | `new_merge_PLAN_2026-07-18.md` |
| File B | Hybrid only |
| Discovery / Options | Detail plans only |
| Public states | `WATCH` / `WAIT` / `CONFIRMED` / `REJECT` only |
| Work selectors | `R0â€“R18`, `CROSS-###`, `TDG-GAP-###` only â€” never `M/T/PK` |
| Combined_Score | Forbidden as product authority |
| qty / OMS | Out of research scope |


## Source Operations reference - 2026-08-15

The Inventory button opens the bundled workbench with `embed=terminal`. The
Source Operations panel below the five KPI cards reads compiler, monitor,
fetch-attempt, parser-output, and freshness APIs. It shows source flow health,
reasons, dates, and research effect from registered contracts to usable facts.

It uses typed states `HEALTHY`, `VALID_EMPTY`, `STALE_PARTIAL`, `BLOCKED`,
`FAILED`, and `NOT_ATTEMPTED`. Valid empty is not failure. The panel is
operational evidence only: it cannot rank, activate, authorize `CONFIRMED`,
calculate quantity, or execute orders. Standalone catalog behavior is unchanged.


## Hash-pin caveat - 2026-08-15

The source and bundled runtime files are directly byte-identical for this
change, but the existing snapshot manifest still contains the pre-Source-
Operations byte sizes and hashes. The existing `inventory-workbench.test.js`
also still expects the old drawer URL without `embed=terminal`. Its current
observed result is **FAIL: Size mismatch: index.html**. This means the runtime
panel observation is valid, but the manifest/test pin must be refreshed before
claiming a clean snapshot-integrity verdict. No source data, catalog sample, or
TrendForge state authority is affected by this metadata/test discrepancy.

## Hybrid V2 paper overlay - 2026-08-22

- Folder: `backend/trendforge_api/hybrid_v2/` (contracts, spine_adapter,
  pipeline, persist, blocks/, stages/, as_lab/, scorecard/, tests_support/)
- Tests: `backend/tests/hybrid_v2/`
- Routes: `GET /api/v1/hybrid-v2/overlay?limit=40`,
  `GET /api/v1/hybrid-v2/overlay/{symbol}`; POST -> 405; lineage mismatch ->
  503 WAIT_HYBRID_LINEAGE_MISMATCH (never last-good)
- Ceiling: RESEARCH_PROXY_NOT_CALIBRATED; not File A, not R2-B, not size
- Frontend: `frontend/hybrid-v2-overlay.js`, `#hybridV2Chain`, `#hybridV2OverlayPanel`



