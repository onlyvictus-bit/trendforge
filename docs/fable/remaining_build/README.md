## 2026-09-04 - Build plan for the three blocked parts (price-band, R5, activation)

No code changed. Start here before building:
`THREE_BLOCKERS_BUILD_PLAN_2026-09-04.md` (what/why/order/gates for all three
parts, with the deep-plan council verdict), then
`PRICE_BAND_TECHNICAL_ZONES_BUILD_PLAN_2026-09-04.md` (16-section detail:
official NSE rule matrix, calculation contract, feature contracts, gate
pseudocode, house coding style, 50 adversarial tests, KEEP/REJECT table).
Key verified fact: the band/ESM/auction checkpoint is real in the normalized
store — the SQLite parse tables are archive-only for these keys (see D-068).
Next operational action still needs its own approval: collector rerun or first
geometry ticket per the sequence in §14 of the detail plan.
Audit 2026-09-04 (see D-069): plan hardened with the exact seven R5 match
fields, the five named R2-B sources, a first-designed grant-record prerequisite
(no grant path exists in code today), fixture-vs-live boundary, approval matrix
and effort CIs — all inside `THREE_BLOCKERS_BUILD_PLAN_2026-09-04.md` §§0–10.

## 2026-09-02 - R18 fixture build complete; promotion remains data-gated

R18-A-E code and fixture acceptance are complete. Do not rebuild them unless current regression evidence fails. Open selection/r18_governance.py for contracts/evaluation/review/drift, selection/r18_store.py for migration 0014 and append-only persistence, main.py for /api/research/ml/*, and frontend/r18-model-governance.js plus the Paper/ML section for presentation.

Current state remains MODEL_NOT_APPROVED because R16 is PIT_NOT_APPROVED and migration 0014 is not applied. Next operational actions require separate approvals: apply migration 0014 after backup/review, then accumulate sufficient R16 PIT dates and perform independent OOS approval. Neither action authorizes broker execution.

## 2026-09-01 - Verified build inventory and next handoff

Do not rebuild completed R1/R2/R3, R4-R8, R10-R16 or R17-B-F/H/I unless current regression evidence proves breakage. R3 and R14 are WAIT-only components, not future placeholders. R16 code/schema/replay exists, but one complete real S8 date leaves PIT_NOT_APPROVED.

R9 and R17-G are postponed. R18 has no dedicated implementation yet. Start at R18-A contracts and persistence, then offline challenger evaluation, human review/promotion, drift demotion/rollback and read-only Paper/ML projections. Preserve MODEL_NOT_APPROVED while R16 is not approved. Do not show probability, win rate or performance, and do not add automatic promotion or trading authority.

## 2026-09-01 - Current handoff: R17-G postponed, build R18-A next

Do not repeat R17-B-F or R17-H/I. They are fixture-verified. The bounded R17-G
live attempt fixed TrendForge's missing OpenAlgo `60m` interval support, then
stopped correctly because the stored Kite session was invalid. The user chose
to defer the fresh Kite login, so mark R17-G `POSTPONED_BY_USER`; do not claim
`SHADOW_LIVE` and do not use OpenAlgo as data authority.

R9 ORB/VWAP remains postponed because no verified intraday-bar source is active.
The next selected File A requirement is **R18**, beginning with **R18-A model
governance foundation**. Reuse R16's immutable PIT datasets and replay. Build
versioned model/challenger contracts, offline evaluation, human-only promotion,
drift demotion, deterministic rollback and read-only UI/API state. Because the
current real R16 dataset is `PIT_NOT_APPROVED`, runtime must show
`MODEL_NOT_APPROVED`; no probability, performance, automatic promotion, broker,
order or executable-quantity authority may unlock.
## 2026-08-31 - R17-D-F and R17-H/I fixture-verified

R17 now has exact NSE/NFO/MCX identity, existing-store replay, stream integrity
fixtures, one additive shadow DTO, cost-aware research quantity, seven visible
option-purpose calculations with shared-root concentration, proof-based
activation/rollback, read-only GET `/api/v1/integrations/openalgo/shadow`, and
the Live Ops shadow/inspector UI. Focused R17/lane/security: 110 passed; full
backend: 1,424 passed; frontend: 218/218 plus the R17 check.

Do not repeat R17-B-F or H/I unless regression evidence fails. Next R17 work is
R17-G only, and it requires separate approval for local credentials/network
observation. Configuration alone is `FIXTURE_VERIFIED`, not `SHADOW_LIVE`.

## 2026-08-31 - R17-C OpenAlgo REST client verified

The existing `openalgo_client.py` now implements all eight allowlisted POST
data routes. R17-C repaired timezone-aware IST history parsing, retained epoch
compatibility only for numeric JSON values, and added strict ping, intervals,
quote and multiquote methods. History and quotes fail closed on empty,
malformed, non-finite, impossible, duplicate/reversed, partial, stale or
identity-mismatched fixtures. Per-route pacing, bounded transient retry,
secret-free circuit state, response-size limits and API-key redaction are
active. Focused tests: 59 passed; full backend: 1,373 passed; frontend: 218/218.
This historical checkpoint is superseded by the R17-D-F/H/I record above.

## 2026-08-31 - R17 OpenAlgo shadow build authority

Read `R17_OPENALGO_SHADOW_BUILD_PLAN.md` before R17 work. It preserves
research quantity and defines separate purpose-specific option votes while
keeping OpenAlgo optional, read-only and non-executable.

## 2026-08-28 - Missing/WAIT pre-build decision contract tightened (plan only)

Before any remaining Missing/WAIT build, read File A
new_merge_PLAN_2026-07-18.md section 25.27. It owns per-side Top-10/15
semantics, profile eligibility, separate intraday/swing geometry, family-level
confluence, deterministic next-condition/invalidation fields, options/MCX
boundaries, replay/runtime gates and milestone prerequisite checks. R12 remains
partial, so Elliott and options-dependent approval remain blocked. This update
adds no runtime behavior or build authorization.

## 2026-08-26 - R13 remaining scanners CODED + verified (chips-only, PK4)

Six bounded-family scanners added to the R8 registry (11 total): VCP, TTM
squeeze, SMA20/50 trend overlay, RSI(14) momentum, failed-break reclaim
reversal, 10d/52w PIT extremes. **Chips-only** per audited amendment: zero
EvidenceClaims minted; family caps hold without claims (compression trio and
PRICE_STRUCTURE fold to one rep; twins marked by group count). Warmup gaps
seat INPUT_INCOMPLETE_WARMUP reasons. Reuses institutional_features._rsi.
No ORB/VWAP (R9 skipped). Lab lists new ids dynamically (no JS edits).
Verified: scope 78 passed; FULL backend 1306; acceptance 217/217; battery 29/29
with live defs_count=11. Prompt amended with 9 audited fixes pre-build.
Next: data ops (NSE last-goods for D-053 CONFIRMED) or R17 OpenAlgo RO shadow.

## 2026-08-25 - R15 Scanner Lab UI CODED + verified (PK7/UI-007)

Scanner Lab lives inside #q5Inspector as its own tab (scanner-lab.js
registers it; survives q5 tab re-renders). Views: Definitions (R8 cores +
R10 recipes with hashes), Pipe flow (stage in/out chips + drop reasons +
survivors), Symbol (per-name match/fail + correlated_possible + optional S9
win % footnote for that symbol only), PK shadow (descriptive parity chips).
Backend one-fetch BFF GET /api/v1/scanners/lab-bundle (one 200, named inner
codes, POST 405). #scannerRunButton relabelled "Refresh lab (GET)" and
rewired to bundle refresh - legacy scanner fire disconnected. All Stocks
columns frozen (acceptance pins the exact radar <th> template).
Verified: acceptance 217/217; s7 law 19 passed; FULL backend 1294; live
battery 28/28. GATES: delete/gates_r15_lab_2026-08-25/GATES.md.

## 2026-08-25 - R11 MCX master readiness CODED + verified (cash path green)

`selection/r11_mcx_live.py`: honest MCX board (trendforge.mcx-master.v1,
LIVE_MCX_WAIT_WITHOUT_NAMED_ACTIVATION). MCX leaves WAIT only with structured
official master + current local mcx_bhavcopy; missing lot/tick/expiry seat
WAIT (never invented); tender window hit vetoes READY; FBIL/CFTC/WGC are
context-only and can never confirm/unlock; PRF-005/006/007 stay EMPTY via
mcx_profile_blocker. Swing RS/delivery wired as gate-only helpers reusing
S3/S5 semantics (delivery EOD-only). Routes GET /api/v1/selection/mcx-master
{,/{symbol}}, POST 405. Frontend #mcxMasterPanel + mcx-master.js
(MCX segment loads live status, never fixture gold); adapter fetch #19.
Verified: G2 scope 41 passed; full backend 1291; acceptance 216/216; live
battery 27/27. GATES: delete/gates_r11_mcx_2026-08-25/GATES.md.

## 2026-08-26 - R10 pipe DSL (PK5/FUS-010) CODED + verified; R9 SKIPPED

Operator decision: **R9 (ORB/VWAP) skipped** - no verified intraday bars;
returns only when OPENALGO_RO lane or a free NRT source lands. CSV row stays
PARTIAL.

R10 built: `scanners/pipe_dsl.py` — named versioned recipes over R8 native-core
matches. Grammar v1: UNION / INTERSECTION / FILTER_STATE / ENRICH_S7; first
stage must be a scanner stage; invalid stage fails the run typed
(PIPE_INVALID_STAGE); ENRICH never filters; pipes emit ZERO claims (FUS-010);
stage counts are symbol counts so twins cannot inflate. Seeds:
pipe.breakout_watch.v1, pipe.thrust_participation.v1 (STO-016 hashes).
Routes GET /api/v1/pipes/{definitions,{pipe_id}/run}; POST /pipes/run 405.
Frontend #pipeLabPanel + pipes.js?v=20260826-r10-1; adapter fetch #18.
Verified: G2 scope 63 passed; full backend 1280; acceptance 215/215; live
battery 26/26 (live pipe run confirmedCount=0). GATES:
delete/gates_r10_pipes_2026-08-26/GATES.md.
Historical R10 checkpoint, superseded by the later R11/R13/R15 records below:
at this point those prompts were not yet written. R17 OpenAlgo RO shadow and
data ops were still pending. Data ops still owed for R2-B live
CONFIRMED (stale nse_bhavcopy_eod / CA / index last-goods).

## 2026-08-25 - R8 native core scanners CODED + verified (PK3)

Five versioned native cores wrap R5 claims (no third engine): breakout/trend
(FTR-006, CG_PRICE_STRUCTURE), NR compression (FTR-007, CG_COMPRESSION), RVOL +
volume thrust (FTR-017, CG_ACTIVITY_SESSION). parameterHash STO-016; twins fold
to one representative per group (correlated_possible, never two votes); PK
shadow isolated; confirmedCount pinned 0. Routes GET /api/v1/scanners/definitions
+ /native-core{,/{symbol}}, POST /scanners/run 405. S3 shows optional
nativeCoreMatches without re-rank; S6 merge_native_claims empty-group-only.
Frontend #nativeCorePanel + native-core.js + adapter fetch 17.
Verified: G1/G2/G3 gates pass; full backend 1263; acceptance 214/214; live
battery 24/24. GATES: delete/gates_r8_native_2026-08-25/GATES.md.
Next: R10 pipe DSL prompt (not written). Data ops still owed for R2-B live
CONFIRMED (stale nse_bhavcopy_eod / CA / index last-goods).

## 2026-08-25 - Guidance ticket set COMPLETE: all four coded + verified

Tickets 1-4 are all **on disk and verified**. Set is closed; do not re-run these prompts.

| # | Ticket | Coded as | Verified |
|---|---|---|---|
| 1 | S9 Validation tab UI | `frontend/s9-pit-homework.js` + adapter + Validation tab | acceptance-check |
| 2 | Later bars / PIT gate | `selection/pit_gate.py`, `GET /pit-gate` | pytest + live 200 |
| 3 | R12 options claims | `r12_options_claims.py` (options `guidanceConfirmed`) | pytest |
| 4 | R2-B amendment + guidance OMS | `r2b_live.py` v2 observed five-source flip; S7 CONFIRMED gates; `guidance_oms.py`; routes; `guidance-oms.js` | 36 suite tests; full backend 1246 passed; frontend 212/212; live battery 22/22 (`delete/gates_r2b_confirmed_2026-08-25/live_battery.py`) |

Live posture after ticket 4: `sourceActivationReady=false` until all five named
sources have current last-goods (blockers auto-listed by
`GET /api/v1/selection/named-activation`). Public CONFIRMED appears
automatically when they go current - no code change needed. Live orders stay
409 `LIVE_ORDERS_ARMED_OFF` unless env + OPENALGO_RO lane + `#armLiveOrders`.

**Next verticals (prompts NOT yet written):** R8 native scanners, R9 ORB/VWAP,
R10 pipe DSL, R11 MCX master, R15 Scanner Lab runtime UX, R17 OpenAlgo RO
read-only shadow. **Time-based:** keep collecting S8 days; PIT guidance
auto-approves at >=20 horizon-complete rows (needs calendar time, not code).

## 2026-08-25 - Next four OpenCode prompts (copy in order)

**User law:** former “must not” items are now **required trade guidance**.  
Read `TRADE_GUIDANCE_LAW_2026-08-25.md` first. Live `placeorder` stays **armed-off** unless env+switch.

| Order | File | What | **Needed (guidance)** |
|---|---|---|---|
| 1 | `S9_UI_VALIDATION_TAB_OPENCODE_PROMPT.md` | Validation tab + S8 join | Win %, small chart, APPROVED-for-guidance copy |
| 2 | `S8_DAYS_R16_R18_PIT_APPROVED_OPENCODE_PROMPT.md` | Later bars + auto-approve guidance | Yahoo/OpenAlgo as **proxy** PIT series; auto-approve when minima pass |
| 3 | `R12_OPTIONS_WALLS_GREEKS_CLAIMS_OPENCODE_PROMPT.md` | Walls/Greeks as claims | Dealer-GEX **scenario** guidance; options-only **guidanceConfirmed** |
| 4 | `R2B_CONFIRMED_AMENDMENT_OPENCODE_PROMPT.md` | Live File A CONFIRMED + guidance OMS | Paper OMS / order preview; intraday **guidance** CONFIRMED; live fire gated |

Tickets 2 and 3 after 1; **4 last**.

## 2026-08-27 - R13 guidance-grade native scanner closure

R9 remains skipped. R13 is implemented and reverified as closed-bar EOD
research guidance: six chips-only scanners use the hash-matched R5/R14 adjusted
PIT history, a single bulk history query and a separate claimless-family
representative selector. R13 emits zero claims and cannot change candidate
direction, rank or public state.

Observed gates: focused integration 60 passed; deterministic-regression set 61
passed; complete backend 1320 passed; frontend 217/217; read-only live battery
24/24. Current runtime returned 2623 native rows, 2379 matched rows and zero
confirmations. `/api/v1/selection/scans/latest` correctly remains
`WAIT_S8_LINEAGE` until a later authorized daily scan persists the new native
guidance hash.

Implementation and operating record:
`R13_REMAINING_SCANNERS_OPENCODE_PROMPT.md`. R9 is not implicitly completed,
and wider R8-R15 scope is not declared complete by this R13 closure.

## 2026-08-25 - R10 / R11 / R15 OpenCode prompts (R9 skipped)

User skipped R9 ORB/VWAP. Copy **in order**. R11 can overlap R10 if files disjoint; **R15 after R10**.

| Order | File | Expected |
|---|---|---|
| 1 | `R10_PIPE_DSL_OPENCODE_PROMPT.md` | Pipe recipes; 0 claims; stage counts; UI panel |
| 2 | `R11_MCX_MASTER_SWING_OPENCODE_PROMPT.md` | MCX WAIT without master; cash S7 unbroken |
| 3 | `R15_SCANNER_LAB_UI_OPENCODE_PROMPT.md` | Inspector Scanner Lab; no extra All Stocks columns |

Each: OWNS paths, adapter names=fetches, `delete/gates_*`, BUILD_STATUS/VALIDATION/DECISIONS after observed GATES. Trade guidance law still applies. Live `placeorder` gated.

## 2026-08-25 - Next after tickets 1–4: R8 native scanners

Ticket 4 (R2-B + guidance OMS) is on disk (D-053). Live CONFIRMED stays 0 until bhavcopy/CA/index last-goods refresh (data ops).

**Copy next:** `R8_NATIVE_SCANNERS_OPENCODE_PROMPT.md`  
Then R9 ORB/VWAP → R10 pipe → R11 MCX → R15 Scanner Lab → R17 OpenAlgo live RO shadow.

## 2026-08-25 - Dual-lane + research qty (backend landed; UI wired this follow-up)

**CODED:** `data_lane.py` / `research_quantity.py` / `test_dual_lane.py` / routes.
**UI wired:** `frontend/data-lane.js`, `research-quantity.js`, command-bar switch,
S7 qty panel, Live Ops funds/position, adapter 15 fetches. Prompt remains
`DUAL_LANE_FREE_VS_OPENALGO_QTY_OPENCODE_PROMPT.md`. Next: S9 PIT homework.

## 2026-08-25 - Dual-lane (free NSE vs OpenAlgo RO) + research quantity prompt

Copy into OpenCode: `DUAL_LANE_FREE_VS_OPENALGO_QTY_OPENCODE_PROMPT.md`

**Option B locked** (user 2026-08-25):
- Switch OFF: free official NSE; **try** free intraday; if none, `intradayMode=OFF`.
- Switch ON: **all OpenAlgo Data API** (read github.com/marketcalls/openalgo + docs.openalgo.in).
- Research qty + **calculated** funds/position card at `draftConfirmedEligible`. Never broker `/funds` or `place_order`.

## 2026-08-25 - Production-readiness audit prompt (all builds so far)

Copy **one file** into OpenCode (not GLM-only):  
`PRODUCTION_READINESS_AUDIT_OPENCODE_PROMPT.md`

It forces Superpowers + unlazy: GATES first, full pytest, live GET battery, systematic
debug of every fail (including the historical six), code-review after fixes, then an
honest verdict: `PRODUCTION_RESEARCH_READY` | `NOT_READY` | `READY_WITH_NAMED_ENV_WAIVERS`.
Research screener only. No broker. No S8/S9 implementation in that ticket.

## 2026-08-24 - S7 / S8 / S9 remaining File A prompts (copy in order)

Prompts only. Do **not** implement until the named file is pasted into GLM/OpenCode.
No broker account. Production-ready means **research screener**: honest WATCH/WAIT/REJECT,
reconstructable scan, PIT homework hidden until `PIT_APPROVED`. CONFIRMED stays unreachable
while `sourceActivationReady=false`.

| Order | File | Ticket | Copy when |
|---|---|---|---|
| 1 | `S7_STATE_GATES_GLM_PROMPT.md` | SEL-008 | Now. Session-0 pipe + PRF-003 WAIT gates. |
| 2 | `S8_PERSIST_RUN_GLM_PROMPT.md` | SEL-009 | After S7 GATES green. One reconstructable blob. |
| 3 | `S9_PIT_HOMEWORK_GLM_PROMPT.md` | SEL-010 | After S8 GATES green. Offline labels, no win-rate UI. |

Each file contains: outcome, forbidden, module/API/UI, tests, free-NSE data, **debug catalog**, **GATES**.
Builder must audit live GET + pytest after build and debug every fail before the next file.

## 2026-08-24 - S4 structure pack + S5 shortlist enrichment + S6 family resolution (coded WAIT)

- S4 (SEL-005): selection/s4_structure_pack.py over the hash-matched R5 batch;
  one CG_PRICE_STRUCTURE representative per row, pattern lane display-only,
  nextTrigger/invalidation on every WATCH/WAIT row. Route
  GET /api/v1/selection/s4-structure; POST 405.
- S5 (SEL-006): selection/s5_shortlist_enrichment.py bounded to the S4 claimed
  shortlist; delivery EOD-only (INTRADAY forbidden), one FO package,
  OPTIONS_PACKAGE=UNKNOWN_NEEDS_R12 score 0, market FII chip only.
  Route GET /api/v1/selection/s5-enrichment; POST 405.
- S6 (SEL-007): selection/s6_family_resolution.py resolving R5-minted claims via
  resolver.resolve_evidence with required families read from the active versioned
  profile object; conflict flag; strength labelled not-win-probability.
  Route GET /api/v1/selection/s6-resolution; POST 405.
- Frontend: s4-structure.js, s5-enrichment.js, s6-resolution.js wired through the
  extended selection-live-adapter fetch list (11 fetches = 11 names).
- Status rows: S4 coded at WAIT ceiling; S5 WAIT enrich observed with options
  UNKNOWN_NEEDS_R12 unless proven; S6 WAIT fuse over S4+S5 claims. NOT done:
  S7 profile gates, R2-B unlock, File A first CONFIRMED, R12 options tree.

## 2026-08-22 - Evidence radar + R6 shortlist + top-10 (built)

- R6 stickers + top-10: selection/r6_live.py, selection/top10_research.py.
- 3rd-eye radar package: selection/evidence_radar/ (catalog/slots/calculate/
  fuse/explain/boards/coverage). Coverage route proves nothing-skipped.
- Tests: radar 19 + r6/top10 18; combined regression 69 passed.
# Remaining Build Pack â€” AI / Human Guide

**Folder:** `D:\TrendForge\docs\fable\remaining_build`  
**Created:** 2026-07-20  
**Last audited:** 2026-08-01 (File A Â§9.3 S0â€“S9 crosswalk + state owner + no Combined_Score + property tests; FMR-002 story map)  
**Purpose:** Keep remaining-build planning, governance evidence, coverage matrix, the **mandatory Hybrid (File B) open-list**, and the mapped **Final Merge product/design addendum** in **one place** so agents do not implement from File A short contracts alone.

**Hard rule:** File A points at Hybrid. File A does **not** contain full Hybrid recipes (key lists, defect checklists, formulas, activation backlog, recovery SM, strategy source sets). **Â§9 of this README** is the operational map that forces every material Hybrid section to be opened and used. Do **not** full-merge Hybrid into File A or into this README.

---

## 0. Read this first (mandatory for AI agents)

### What this folder is

| This folder IS | This folder is NOT |
|---|---|
| Traceability (CSV), audits, dual-file governance evidence | The build authority |
| Checklist of what is left after Q5 | A third architecture plan |
| Seed data for â€œwhat nextâ€ | Permission to execute trades |

### Authority order (do **not** move these files)

| Order / role | Path |
|---|---|
| **1. Current explicit user instruction** | Current approved task; it cannot override safety, consent, or legal boundaries |
| **2. Engineering and safety rules** | `AGENTS.md` |
| **3. File A â€” future build order and requirement IDs** | `docs/fable/new_merge_PLAN_2026-07-18.md` |
| **3A. Final Merge â€” mandatory mapped product/design addendum** | `docs/fable/FINAL_MERGE_PLAN.md`; never a second build order |
| **4. Lasting technical decisions** | `docs/DECISIONS.md` |
| **5. Full system boundaries** | `TREND_FORGE_ARCHITECTURE.md` |
| **6. File B â€” domain formulas and detailed recipes** | `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` |
| **6A. Professional mathematics research detail** | `docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md`; open only through File A section 25.22 |
| **7. Source meaning and authority** | `TREND_FORGE_SOURCE_REGISTRY.md` |
| **8. Current executable module map** | `docs/ARCHITECTURE.md`, then current code |
| **9. Current implementation evidence** | `backend/`, `frontend/`, and tests |
| **10. What is built / proof history** | `docs/BUILD_STATUS.md`, `docs/VALIDATION.md` |
| **11. Current URL inventory** | `data/reports/SOURCE_LINK_INVENTORY_MASTER.xlsx` |
| **Navigation only** | `fileindex.md` (repo root) |

**Conflict rule:** Current explicit instruction and `AGENTS.md` govern conduct. File A wins on sequence, four states, research-only scope, and no quantity/execution. Architecture and Decisions govern their owned boundaries. File B supplies formulas/lists when File A Â§0.5 / Â§25 **or Â§9 of this README** points there. Official observed source evidence can reopen a plan assumption but cannot silently rewrite the plan. Stricter fail-closed / PIT / non-probability rules win.

**Hybrid under-use trap:** Reading only File A FTR/PRF short rows, or only the short Hybrid mentions in older Step B bullets, **hollows** inventory honesty, named source wiring, ops recovery, tradability fields, and fusion quality. Before coding any vertical, complete **Â§9** for that vertical.

---

## 1. Files in this folder

| File | Job | Open when |
|---|---|---|
| **`README.md`** (this file) | What to do next + **Â§9 Hybrid open-list** | Always first in this folder; re-read Â§9 every vertical |
| **`PLAN_REQUIREMENT_COVERAGE.csv`** | Status of Q5, R0â€“R18, CROSS, TDG-GAP, HYBRID-*, FMR-*, CONFLICT | Planning next task |
| **`../FINAL_MERGE_PLAN.md`** | Mandatory product/design addendum for mapped FMR aliases | All-stock, discovery, PK, options/Gamma/strike and trader-workflow verticals |
| **`build_coverage_csv.py`** | Rewrites the CSV from reviewed, hardcoded seed rows and validates required ID ranges | Only after updating its rows from current plan/status evidence |
| **`REMAINING_PROJECT_BUILD_FILES.md`** | Docs + code paths for remaining work | Before coding a vertical |
| **`INDEPENDENT_AUDIT_merge_plan_build_matrix_2026-07-20.md`** | Plan vs code matrix (Q5 done at ceiling) | â€œWhat is coded?â€ |
| **`INDEPENDENT_AUDIT_hybrid_vs_new_merge_2026-07-20.md`** | Hybrid gaps vs File A | â€œWhat Hybrid detail is still thin?â€ |
| **`TWO_DOCUMENT_GOVERNANCE_SYSTEM_2026-07-20.md`** | Full dual-file analysis | Deep dual-file audit |
| **`TRENDFORGE_GOVERNANCE_SYSTEM_ai.md`** | Preserved Kimi + GLM advisory guide; **not authority** | Review ideas already reconciled into File A |
| **`R6_TOP10_OPENCODE_PROMPT.md`** | OpenCode prompt for R6 stickers + simple top-10 | FII/MF/deals shortlist only |
| **`S2_MARKET_WEATHER_OPENCODE_PROMPT.md`** | OpenCode prompt: File A S2 index/VIX/breadth/sector/commodity context; fix Nifty 20.15-as-percent | When cash S1 is usable and market weather is not |
| **`S3_CHEAP_DISCOVERY_OPENCODE_PROMPT.md`** | Implemented File A S3 build/verification contract: full current R2 universe on A3+R2; no second ranker; no delivery | Debug/verify S3; do not rebuild it |
| **`S4_STRUCTURE_PACK_OPENCODE_PROMPT.md`** | OpenCode: File A S4/SEL-005 closed-bar pack on live R5 WAIT | After S3; not Hybrid S4 p̂ |
| **`S5_SHORTLIST_ENRICHMENT_OPENCODE_PROMPT.md`** | OpenCode: File A S5/SEL-006 shortlist enrichment; options package via Options Detail Plan | After S4; not all-universe |
| **`S6_FAMILY_RESOLUTION_OPENCODE_PROMPT.md`** | OpenCode: File A S6/SEL-007 FUS-009 on S4+S5 claims | After S5; not S7 CONFIRMED |
| **`THIRD_EYE_EVIDENCE_RADAR_OPENCODE_PROMPT.md`** | Historical OpenCode prompt; apply its typed-slot rule to the current 126-job registry, 4 horizons Ã— BUY/SELL, how/what/where/when | When every link must be represented and must **not** become a vote |
| **`M_FACTOR_LIVE_UI_OPENCODE_PROMPT.md`** | Paint existing M-Factor tool room; FUS-009 BFF; 4 horizons | **UI+BFF DONE 2026-08-22.** Do not rebuild empty BFF |
| **`M_FACTOR_USEFUL_FUS009_WIRING_GLM_PROMPT.md`** | Make M-Factor useful: wire R5 FTR-006/007/017 + event/A5 into FUS-009; two-sided BUY/SELL; fail-closed other horizons | **Give this file to GLM.** Screening; 0 CONFIRMED |
| **`OI_OPTIONS_ROOMS_GLM_PROMPT.md`** | OI Analysis, OI Tracker, Strike Explorer, Expiry Range: live BFFs, PRICE_UP_OI_UP, official MWPL BAN/RESUME/ALERT60, Q vs P, IV recorder, hard blocks, PAPER_CANDIDATE | **Give to GLM for derivatives rooms.** CONTEXT_ONLY; not File A CONFIRMED |
| **`S7_STATE_GATES_GLM_PROMPT.md`** | File A S7 (SEL-008): one public-state owner, PRF-003 live swing, CONFIRMED unreachable while activation=false, idea card | **Give to GLM/OpenCode next.** Run BEFORE S8. No broker, no qty. |
| **`S8_PERSIST_RUN_GLM_PROMPT.md`** | File A S8 (SEL-009): one reconstructable scan blob (S2–S7 hashes + claims + gates) | After S7 green. |
| **`S9_PIT_HOMEWORK_GLM_PROMPT.md`** | File A S9 (SEL-010): offline PIT labels, no win-rate UI, no auto-trade | After S8 green. R16 ceiling. |
| **`PRODUCTION_READINESS_AUDIT_OPENCODE_PROMPT.md`** | OpenCode master: audit+test+debug all coded builds; Superpowers skills; GATES; research-ceiling verdict | After S7 coded / anytime “is it production ready?” |
| **`DUAL_LANE_FREE_VS_OPENALGO_QTY_OPENCODE_PROMPT.md`** | Dual data lane FREE vs OpenAlgo RO + research qty at confirmation | After S8 coded; live without broker |
| **`S9_UI_VALIDATION_TAB_OPENCODE_PROMPT.md`** | S9 Validation tab UI; join S8 run; no win % | After S9 backend |
| **`S8_DAYS_R16_R18_PIT_APPROVED_OPENCODE_PROMPT.md`** | Later official bars + locked PIT gate | After S9 UI or GET |
| **`R12_OPTIONS_WALLS_GREEKS_CLAIMS_OPENCODE_PROMPT.md`** | R12 walls/greeks as claims; OI rooms ≠ owner | After S6 |
| **`R2B_CONFIRMED_AMENDMENT_OPENCODE_PROMPT.md`** | Execute R2-B; live CONFIRMED PRF-003 EOD only | **EXECUTED 2026-08-25** (with guidance OMS paper tickets; live fire triple-gated) |
| **`R8_NATIVE_SCANNERS_OPENCODE_PROMPT.md`** | PK3 native core registry; family caps; S3 may consume | After ticket 4 on disk |
| **`R10_PIPE_DSL_OPENCODE_PROMPT.md`** | FUS-010 pipe DSL; membership only | After R9 skip; R8 optional |
| **`R11_MCX_MASTER_SWING_OPENCODE_PROMPT.md`** | MCX master gates; swing RS/delivery | Parallel-ok vs R10 |
| **`R15_SCANNER_LAB_UI_OPENCODE_PROMPT.md`** | Scanner Lab inspector; no radar inflation | After R10 |
| **`R13_REMAINING_SCANNERS_OPENCODE_PROMPT.md`** | VCP/squeeze/oscillators/reversal/52w; family batches | After R8+R10+R15 |

Installed controls already live in File A (Â§0.5, Â§25, Â§25.16, Â§25.17). Do not re-install by pasting whole guides into File A.

The independent audits and AI governance guides contain historical proposals and pre-install action wording. Preserve them as evidence, but never let their self-declared status override the authority table above.

---

## 2. Current known position (do not re-do)

| Item | Status |
|---|---|
| Q5-R0 â€¦ Q5-R7 | **IMPLEMENTED** at research/fixture ceilings |
| Full R0â€“R18 product | **NOT complete** |
| Production CONFIRMED / live intraday | **Not authorized** yet |
| Quantity / sizing UI | **POSTPONED** for the current research plan |
| OMS / account access / order placement / autonomous execution | **REJECTED or outside the product boundary** |
| Dual-file governance docs | **Installed** (pointers + CSV) |
| DAT-010 feature registry | **IMPLEMENTED at R0 contract ceiling**: 39 FTR contracts, all 22 mandatory fields, read-only manifest/lint APIs |
| DAT-011 indicator engine pin | **IMPLEMENTED at R0 contract ceiling**: one internal NumPy/pandas engine identity per run, explicit warm-up/parity failure states |
| CROSS-002 / TDG-GAP-013 source map | **IMPLEMENTED at R0 governance ceiling and not rebuilt**: the 2026-07-23 review is the 129-key living map. Current compiler union is larger and reports baseline drift; do not treat the old 129/351 counts as today's live inventory |
| R0 residual split | **R0-A** closed (H1A0 6/6). **R0-B** field-reviewed with named waivers; `provenCount=0`, `canVote=false`; cohort API live. **R0-C** remaining inventory non-voting. File A Â§25.20.1 |
| R1 selection spine | **IMPLEMENTED at the live evidence-bundle ceiling**: 123 source contracts and 2,463 stock rows receive lineage, valid-empty/failure distinction, source-specific cadence and why-not-confirmed evidence. Multi-family activation and live CONFIRMED remain closed. |
| R2 cash attention (R2-A) | **IMPLEMENTED at the BASELINE attention ceiling**: immutable 2,463-row WATCH/WAIT order; stale/unknown rows do not rank; no trade geometry. |
| R2-B named activation ledger | **IMPLEMENTED, AMENDED 2026-08-25 (`LIVE_NAMED_ACTIVATION_AMENDED_EOD`)**: `selection/r2b_live.py` v2 + `GET /api/v1/selection/named-activation`. The five named confirm-path sources authorize ONLY from observed current last-goods (all-or-nothing; blockers named). `sourceActivationReady` may be true; S7 may then seat PRF-003 EOD CONFIRMED. MWPL never authorizes. `executable=false`, `canUnlockConfirmed=false` always. |
| R3 live family resolution | **IMPLEMENTED at the WAIT-only FUS-009 ceiling**: exact A1/A2 lineage, hash-scoped persistence/API and one FTR-040 NSE EOD PARTICIPATION claim per stock/correlation group. Intraday, MCX, options and events remain non-directional until separately contracted. |
| File A S3 cheap discovery | **IMPLEMENTED at `LIVE_S3_WATCH_WAIT_ONLY`**: consumes A3/R2, scans every current R2 row, preserves rank, adds cheap optional facts plus PIT RVOL/NR7/RS, reports exact completeness, and fails partial scans to WAIT. No delivery, second ranker, second volume vote, trade geometry or CONFIRMED. Routes `GET /api/v1/selection/cheap-discovery{,/watch}`. |
| R4 live ID pin + PK inventory | **IMPLEMENTED at `LIVE_ID_PIN_WAIT_ONLY`**: uses A2 IDs; refuses scripCode; PK digest zero-vote; PIT unproven unless fixtures supplied. Not A2/A4/R5. `r4_fixtures.py` is Q5 fixture only. |
| R5 live closed-bar structure | **IMPLEMENTED at `LIVE_WAIT_REJECT_ONLY`**: official cash history + official index-close companion; IST session phases; setup tags; `confirmedCount=0`. CA authority is the hash-matched R14 join. Not File A first CONFIRMED (still needs R2-B). |
| Hybrid S4/S5 paper A/B overlay | **RESEARCH_PROXY_NOT_CALIBRATED**: original compressed S4/S5 and the split family both stay. New files: `backend/trendforge_api/selection/s4s5_compare.py`, `backend/tests/test_s4s5_compare.py`, `frontend/s4s5-compare.js`. Route in `backend/trendforge_api/main.py`; panel in `frontend/index.html` (`#s4s5ComparePanel`). UI checkboxes WITH / WITHOUT / BOTH. Not File A rank, not size, not CONFIRMED. User picks after paper days. |
| R14 live CA join | **IMPLEMENTED at `LIVE_CA_JOIN_WAIT_ONLY`**: `backend/trendforge_api/selection/r14_live.py` + `backend/tests/test_r14_live_ca_join.py`; `GET /api/v1/selection/ca-join` (hash-scoped, POST 405). Joins official CA to A2/R4 instrument IDs, reuses `corporate_actions.reconcile_corporate_actions` (DAT-022), hides future CA (`available_at > decision_at`), maps conflict / identity-break / unresolved to `WAIT_CA_*`, never mutates RAW bars. Pipeline `R3 â†’ R4 â†’ R14 â†’ R5` (`...orchestrator-7`); R5 consumes the join as CA authority (`r14RunId`/`r14RunHash`) and drops `claim_ids` on WAIT_CA. Build prompt: `docs/fable/remaining_build/R14_LIVE_CA_JOIN_GLM_PROMPT.md`; record in locked plan Â§13.14. |
| Locked R0/R1/R2 plan | `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md` â€” current R1â€“R5 implementation and debugging handoff. It does not activate sources, permit CONFIRMED, or create a third pipeline. |
| Hybrid V2 remaining overlay | Paper package under `backend/trendforge_api/hybrid_v2/`. Prompt: `docs/fable/remaining_build/HYBRID_V2_OVERLAY_OPEN_MODEL_PROMPT.md`. Must not flip R2-B, paste S4â€“S9 into `r5_live.py`, or emit CONFIRMED. |
| R6 stickers + simple top-10 | **CODED at shortlist ceiling:** `selection/r6_live.py`, `selection/top10_research.py`, `GET /api/v1/selection/top10`. WATCH-40 + capped stickers. Not 3rd-eye. SHP FII delta null. Market FII is a chip. Prompt: `R6_TOP10_OPENCODE_PROMPT.md`. |
| 3rd-eye evidence radar | **CODED at WAIT radar ceiling:** `selection/evidence_radar/`, `GET /api/v1/selection/evidence-radar`. Prompt: `THIRD_EYE_EVIDENCE_RADAR_OPENCODE_PROMPT.md`. |
| File A S2 market weather | **PROMPT ONLY:** `docs/fable/remaining_build/S2_MARKET_WEATHER_OPENCODE_PROMPT.md`. A5 exists; Nifty % parse is wrong (points as percent). Sector/commodity weather not ready. Context only. |
| File A S7 state gates | **CODED 2026-08-24, amended 2026-08-25** (SEL-008): `selection/s7_state_gates.py`. CONFIRMED reachable only under the observed R2-B amendment; fail-closed overrides outrank it; guidance fields on cards. |
| File A S8 persist run | **CODED 2026-08-25** (SEL-009): one reconstructable S2-S7 blob; route + frontend owner live. |
| File A S9 PIT homework | **CODED 2026-08-25** (SEL-010): offline labels; `PIT_NOT_APPROVED` until >=20 horizon-complete rows; Validation tab UI wired. |

**Current selection checkpoint:** R1 qualifies saved data; R2 orders attention; R3 removes duplicate claims; S3 scans the full current R2 universe with cheap additive facts while preserving rank; R4 pins IDs/PK inventory; R14 joins official CA; R5 tags closed-bar structure from the R14 join; R6 adds WATCH-40 stickers and a simple 10+10 sort. All live stages are research-only and capped at WATCH/WAIT. Evidence radar uses every job as a typed slot without turning links into votes. Live CONFIRMED still requires R2-B unlock + a File A amendment. R7 PK worker stays isolated.
| Final Merge FMR | FMR-001/002 **partially evidenced** by cash path; not complete. See `FINAL_MERGE_PLAN.md` top section. |
Coverage snapshot after the Final Merge registration: **155 unique rows**,
including every `Q5-R0..R7`, `R0..R18`, `CROSS-001..024`,
`TDG-GAP-001..026`, and `FMR-001..011` ID. The snapshot has **41 active P0
build rows** in `PLANNED` or `PARTIAL`. Across all P0 statuses, **48 rows are
not `IMPLEMENTED`**, including active conflict and rejected rows that remain
intentionally unresolved/non-implemented. These are traceability counts, not
proof of independent features or signals.

### 2.1 DAT-010 / DAT-011 adversarial closure (2026-07-20)

The first happy-path implementation was **REFUTED** by two internal adversarial
reviews. Do not cite the earlier passing unit tests as sufficient evidence. The
reviewers reproduced unregistered evidence claims, caller-controlled warm-up,
duplicate/partial-bar warm-up, unenforced runtime pins, non-finite vectors marked
OK, false active API routes, forged scan counts/IDs, and invalid parity passes.

The corrected contract now enforces:

- every EvidenceClaim uses a registered FTR ID, exact feature version, evidence
  family and correlation group; its stable ID includes direction and authority;
- indicator bindings resolve version, engine and minimum warm-up from the
  registry, not from caller assertions;
- actual point-in-time and institutional calculations verify the pinned runtime;
- warm-up accepts only timezone-aware, ordered, distinct, coherent, explicitly
  COMPLETE bars;
- non-finite or missing institutional outputs return INPUT_INCOMPLETE;
- empty or non-finite parity comparisons cannot return PARITY_OK;
- RESEARCH_ACTIVE requires both a real backend module and a declared API route;
  only FTR-013 and FTR-018 currently meet that contract;
- scan counts reconcile exactly to the eligible universe, scan IDs include the
  completion outcome, and optional per-run indicator bindings reject mixed
  engines.

Observed verification after correction:

| Check | Result |
|---|---|
| Focused adversarial/backend suite | **126 passed** |
| Full backend suite | **514 passed** |
| Frontend acceptance suite | **135/135 passed** |
| Ruff on all touched files | **Passed** |
| Coverage generator/CSV check | **144 rows; zero added/removed/changed drift** |
| Registry manifest/lint GET | **HTTP 200; 39 contracts; lint ok=true** |
| Registry POST/PUT/DELETE | **HTTP 405** |
| Full static type baseline | **Not clean**; legacy/imported mypy errors remain, so no production-readiness claim |

This closes DAT-010/DAT-011 only at the **R0 contract ceiling**. It does not
activate missing sources, complete the inventory compiler, authorize live
intraday confirmation, or make the project production-ready.

---

## 3. What to do next (execution order for AI)

### Step A â€” Orient (every session)

```text
1. AGENTS.md
2. fileindex.md
3. docs/fable/new_merge_PLAN_2026-07-18.md preamble, Â§0.5, Â§15 that R*, Â§24.13 if Q5, Â§25 CROSS/TDG, Â§25.21 FMR crosswalk
4. docs/BUILD_STATUS.md + docs/VALIDATION.md (top dated sections)
5. docs/fable/remaining_build/README.md â€” this file, especially Â§9 Hybrid utilization
6. PLAN_REQUIREMENT_COVERAGE.csv: priority=P0 AND status in PLANNED|PARTIAL
   (include mapped FMR-* aliases; open FINAL_MERGE_PLAN.md for each selected FMR row)
   (include every CROSS / TDG-GAP / HYBRID-* row for the vertical, not only R*)
7. REMAINING_PROJECT_BUILD_FILES.md: code, tests, docs for the vertical
8. Open File B at every Hybrid section listed in Â§9 for that vertical
   (not only the short bullets in older notes)
9. TREND_FORGE_SOURCE_REGISTRY.md + workbook when any source/inventory row is touched
```

### Step B â€” Pick one vertical (do not parallelize unrelated P0)

**Recommended order after Q5** (each lineâ€™s Hybrid open-list is authoritative in **Â§9.3**; short form here):

1. **R0 inventory / source contracts** â€” split as File A **Â§25.20.1**: **R0-A** closed (H1A0 6/6), **R0-B** field-reviewed with named waivers (`GET /api/source-inventory/r0b-cohort`, still non-voting), **R0-C** remaining rows quarantined. CROSS-001/002/003/006/007/008 + TDG-GAP-001/011/012/013/024/025 + DAT-015. CROSS-019/020 belong to R1. DAT-010/DAT-011 are R0 contract ceiling only. Hybrid **must open:** Â§2, Â§4, Â§15.3, Â§16.1â€“16.6, Â§18.2â€“18.4, Â§18.8â€“18.9, Â§19.2â€“19.4, Â§19.9. Recompute workbook counts from the compiler.  
   **R0 residual checklist (still open until proven):** remaining R0-C contracts; mirror/resolver proof; living-map rebuild only as read-only research if chosen; **no** silent source activation; **no** CONFIRMED from inventory alone. R0-B shared retry/breaker fields stay named waivers until real per-source proof. Open File A **Â§9.3â€“9.6** before coding so S# and score law stay correct.  
   **Inventory workbench (freeze):** `D:\trendforge_inventory_app` is read-only glass. Adapter pieces are File A residuals only â€” hash-pin **R0**; PIT bundle/lineage **R1 / CROSS-019 / TDG-GAP-004**; discovery rank/shadow **R2 / CROSS-004 / TDG-GAP-014**. Do **not** redo CROSS-002. Do **not** treat catalog samples as evidence. Plan: `docs/fable/INVENTORY_WORKBENCH_INTEGRATION_HANDOFF.md`. The UI seam is implemented as a hash-pinned same-origin static snapshot at `/inventory-workbench/` (desktop `95vw x 96vh`, mobile full-screen), but it does not advance R0/R1/R2. Order **R0 â†’ R1 â†’ R2**.  
2. **R1 claims + legacy quarantine** â€” CROSS-014/019/020, FUS-008, TDG-GAP-004. Hybrid: Â§7, Â§16.10, Â§17.2 P0.2â€“P0.3, Â§17.2 P0.6, Â§19.11. **Already partial:** STO WAIT live + **cash A1â€“A4** (staging, identity, Â§25.25.4 discovery, PIT history/CA). **Still open:** multi-family live voting claims, live CONFIRMED.  
3. **R2 live S0â€“S3 + activation + PRF sources + tradability** â€” CROSS-004/005/009/015, TDG-GAP-014/021/022. Hybrid: Â§5 Stages 0â€“4, Â§6, Â§16.7, Â§16.16, Â§17.2 P0.1, Â§17.4, Â§19.5. **R2-A cash attention done:** A5â€“C1 (context, FO enrich, C0 matrix, C1 rank). **R2-B named activation not started.** Inventory ranks = attention only; WATCH/WAIT/REJECT.  
4. **Fusion + R8 scanners** â€” TDG-GAP-015/016, CROSS-011/018/021, family caps. Hybrid: Â§15.4, Â§16.8, Â§16.9, Â§17.2 P0.4, Â§17.5. Evidence strength â‰  win probability.  
5. **R9 lifecycle / ORB / VWAP** â€” Hybrid Â§5 Stage 6, Â§16.8 auction/price features; closed bars only.  
6. **R10 pipes â†’ R11/R12 MCX + options** â€” Hybrid Â§16.7 MCX blocks, Â§16.8 derivatives, Â§17.4 MCX, Â§18.5 four chains, Â§19.5 FX. Fail closed on lot/tick/expiry/freshness.  
7. **R13 scanners + R14 CA/sponsor/events** â€” TDG-GAP-003/026, CROSS-016/020. Hybrid: Â§5 Stage 5, Â§16.7 PEAD/accumulation, Â§17.2 P0.2, Â§19.8 match states.  
8. **R15 Scanner Lab / research UX** â€” CROSS-017/018. Hybrid: Â§9, Â§10, Â§16.15 (research fields only; no qty rail). Do **not** treat `docs/fable/FRONTEND_SHELL_ALIGNMENT_PLAN.md` as R15; that file is a pre-R15 chrome/governance seam only (WAIT rooms, qty=0, four public states).  
9. **Durable storage (after R0, explicit migration approval)** then **R16 PIT** â€” CROSS-023, TDG-GAP-009/017/023. Hybrid: Â§8, Â§16.11, Â§15.5, Â§17.3 P1.1â€“P1.2, Â§17.6â€“17.7.  
10. **R17 OpenAlgo RO** â€” CROSS-010/012/022, TDG-GAP-007/018/019. Hybrid: Â§15.2 lanes, Â§16.12 recovery SM, Â§16.13 RO methods only.  
11. **R18 model governance** â€” Hybrid Â§15.5, Â§16.11, Â§17.3 P1.2, Â§17.6; no P(win) UI without PIT_APPROVED.  

This sequence is a readable grouping, not a replacement for the CSV. Before
starting a vertical, include every active P0 row returned by the Step A filter
whose milestone or dependency belongs to that vertical, **and** complete the
matching **Â§9.3** Hybrid open-list.

### Step C â€” Implement with dual-file discipline

```text
File A requirement ID / R-step
  -> CSV row (status, hybrid_reference, modules, tests)
  -> File A Â§25 CROSS/TDG/GAP/POST-HYB and Â§25.21 FMR mapping for that work
  -> this README Â§9: open every listed File B section (full text, not summary)
  -> open every mapped FMR section in FINAL_MERGE_PLAN.md for product/design detail
  -> apply File A overrides (four states, no qty, no execution, strength â‰  P(win))
  -> if a useful Hybrid idea has no CROSS/GAP/POST/REJECT ID â†’ register orphan in File A first
  -> implement under backend/trendforge_api/ and frontend/
  -> focused tests + full backend suite + Python compile + frontend checks
  -> VALIDATION.md (commands + observed results)
  -> BUILD_STATUS.md (what changed, ceiling, **exact Hybrid Â§Â§ opened**)
  -> update coverage generator seed from evidence â†’ --check â†’ regenerate CSV
```

### Step D â€” Never do without explicit new authority

- Broker `place_order` / OMS / account access  
- INR quantity as product UI  
- Probability / win-rate as evidence strength  
- PK production sidecar or shadow voting  
- Mark production-ready from fixture runtime, code presence, or endpoint HTTP 200  
- Full-merge Hybrid into File A **or** paste Hybrid as a third master plan  
- Create another master plan; `FINAL_MERGE_PLAN.md` is the one accepted mapped addendum, not a competing authority  
- Skip Â§9 Hybrid open-list because â€œFile A already has FTR rowsâ€  

---

## 4. Regenerate coverage CSV

**Important:** this script is a validated static seed generator, not a code or
plan scanner. Running it without first updating its hardcoded rows will restore
old classifications. Update rows only from File A, current code/tests,
BUILD_STATUS, and VALIDATION evidence. `last_verified` means the row
classification was reviewed on that date; it does not mean live data was seen.

Use `--check` first. It validates generated rows and reports added, removed,
or changed IDs without writing. Normal regeneration refuses to remove IDs that
already exist and writes through a validated temporary file before replacement.

```text
cd D:\TrendForge
python docs\fable\remaining_build\build_coverage_csv.py --check
python docs\fable\remaining_build\build_coverage_csv.py --accept-reviewed-changes
```

Output: `docs/fable/remaining_build/PLAN_REQUIREMENT_COVERAGE.csv`

Example filter (PowerShell):

```powershell
Import-Csv D:\TrendForge\docs\fable\remaining_build\PLAN_REQUIREMENT_COVERAGE.csv |
  Where-Object { $_.priority -eq 'P0' -and $_.status -in 'PLANNED','PARTIAL' } |
  Select-Object requirement_id, merge_milestone, requirement, hybrid_reference, backend_module
```

---

## 5. Code touch map (remaining)

| Work | Code |
|---|---|
| Inventory / R0 | `source_contracts.py`, `source_registry_contracts.py`, `source_inventory_audit.py`, `feature_registry.py`, `indicator_engine.py`, `feature_engineering.py`, `institutional_features.py`, `selection/contracts.py` |
| Live S0â€“S3 | `source_resolver.py`, `institutional_sources.py`, `market_activity.py`, `selection/` |
| Legacy scorer quarantine | `intraday_stock_details.py` + FUS-008 tests |
| Structure / scanners | `selection/structure.py`, `scanners/` |
| MCX / options | `selection/mcx_contracts.py`, `options_domain.py`, parsers |
| OpenAlgo | `openalgo_client.py` |
| UI | `frontend/q5-contract.js`, `app.js`, `index.html` |
| Tests | `backend/tests/test_q5_*.py`, `test_source_*`, `test_feature_registry.py`, `frontend/tests/` |
| Durable history | `storage.py` migrations (**needs explicit approval**) |

---

## 6. Completion bar for â€œremaining research productâ€

Not complete until:

- [ ] Every active P0 CSV row has an accountable milestone, next action, and evidence-based status  
- [ ] Every vertical used the matching **Â§9.3 Hybrid open-list** (File B full text), not File A short rows alone  
- [ ] Live S0â€“S3 honest states + completeness  
- [x] Inventory compiler H1A0 and living source-key/endpoint map (CROSS-001/002) using Hybrid Â§16.4â€“16.6 acceptance
  Current pin `f1abcdceâ€¦` is H1A0 6/6 with 32 overlap groups. CROSS-002 129-key review is not rebuilt (live union 176). Source Health and Live Ops show the read-only ladder.
- [ ] Source-specific contract proof, maturity transition history and gate activation remain separate R0/R2 work
- [ ] Named PRF sources + activation backlog (CROSS-004/005 / Hybrid Â§16.7 / Â§16.16)  
- [ ] R8 core scanners under family caps with Hybrid Â§16.8 formulas where cited  
- [ ] Every IMPLEMENTED claim uses evidence appropriate to its type: DOCUMENTED for contracts, CODE_PRESENT for static exclusions, TESTED_OFFLINE for offline behavior, OBSERVED_RUNTIME for observed endpoints/fixtures, and LIVE_SOURCE_VERIFIED only for validated live-source behavior  
- [ ] Fixture/runtime-boundary evidence is never described as live-source verification  
- [ ] BUILD_STATUS cites Hybrid Â§Â§ opened; VALIDATION has observed tests  

Still **not** production-ready without separate live-source + PIT approval.

---

## 7. Where to write results (do not write into this folderâ€™s audits only)

| After work | Update |
|---|---|
| Feature done | `docs/BUILD_STATUS.md` |
| Tests / live checks | `docs/VALIDATION.md` |
| New stable requirement | File A with stable ID; update generator and regenerate CSV (**mandatory**) |
| Long domain recipe | File B + File A Â§25 pointer |
| Architecture boundary | `TREND_FORGE_ARCHITECTURE.md` and `docs/ARCHITECTURE.md` |
| Lasting technical decision | `docs/DECISIONS.md` |
| Dependency or license decision | `docs/DEPENDENCIES.md` |
| Source role, authority, freshness, or parser meaning | `TREND_FORGE_SOURCE_REGISTRY.md` plus inventory workbook when rows change |
| Navigation change | `fileindex.md` |

**Do not** treat edits to files in this folder alone as â€œfeature complete.â€

---

## 8. Quick path list

```text
D:\TrendForge\docs\fable\remaining_build\README.md
D:\TrendForge\docs\fable\remaining_build\PLAN_REQUIREMENT_COVERAGE.csv
D:\TrendForge\docs\fable\remaining_build\build_coverage_csv.py
D:\TrendForge\docs\fable\remaining_build\REMAINING_PROJECT_BUILD_FILES.md
D:\TrendForge\docs\fable\remaining_build\INDEPENDENT_AUDIT_merge_plan_build_matrix_2026-07-20.md
D:\TrendForge\docs\fable\remaining_build\INDEPENDENT_AUDIT_hybrid_vs_new_merge_2026-07-20.md
D:\TrendForge\docs\fable\remaining_build\TWO_DOCUMENT_GOVERNANCE_SYSTEM_2026-07-20.md
D:\TrendForge\docs\fable\remaining_build\TRENDFORGE_GOVERNANCE_SYSTEM_ai.md
```

Authority plans stay at:

```text
D:\TrendForge\docs\fable\new_merge_PLAN_2026-07-18.md
D:\TrendForge\docs\fable\TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md
```

---

## 9. Hybrid (File B) complete utilization index

**Purpose:** File A (`new_merge_PLAN_2026-07-18.md`) **indexes** Hybrid via Â§0.5 / Â§25 / CROSS / TDG-GAP / POST-HYB. It does **not** paste Hybridâ€™s long lists, exact keys, defect checklists, formulas, or recovery diagrams. This README previously under-listed those open-targets. **Â§9 is mandatory** so Hybrid is actually used without full-merging it into File A.

| Document | Role for Hybrid content |
|---|---|
| **File B** | Full text: lists, formulas, tables, failure narratives |
| **File A Â§0.5 / Â§25** | Stable IDs, sequence, short AMEND contracts, POSTPONE/REJECT |
| **This Â§9** | Operational open-list + â€œdetail only in Bâ€ catalog + per-milestone map |
| **CSV `hybrid_reference`** | Traceability; regenerate after status changes |

**Do not:** treat a short CROSS one-liner or AMEND field list as a substitute for opening File B.  
**Do not:** re-introduce READY, quantity, paper/live execution, or fetch-all-354 from Hybrid.

### 9.1 Hybrid Â§Â§1â€“20 disposition (every material block)

| Hybrid Â§ | Material (open File B for full text) | File A / pack IDs | Detail only in File B? | Build use |
|---|---|---|---|---|
| **1** Objective / 7 trader questions | Attention, why, missing, next trigger, invalidation; **qty question** | UI-001; qty â†’ POST-HYB-01 | Research Qs partial in A | KEEP research; POSTPONE qty Q |
| **2** Inventory baseline | Partition, linkedâ‰ authorized, recompute counts | CROSS-001; HYBRID-2-1 | **Yes** exact partitions/examples | R0 recompute; never freeze old totals |
| **3** Governing principles | Hard veto, delayed labels, fail-closed, no AI authority, hashes | GOV/FUS; HYBRID-3-01 | Narrative depth in B | KEEP; A states win |
| **4** Source Decision Contract | Full field template (jobs, veto, fallback, panel, testsâ€¦) | DAT-*; CROSS-002; TDG-GAP-001; HYBRID-4-1 | **Yes** full template | R0 activation contract |
| **5 Stage 0â€“4** Landing â†’ discovery | Immutable landing, universe/safety, quality, regime, cheap discovery | S0â€“S3; TDG-GAP-002 | Stage recipes in B | Live S0â€“S3 / R2 |
| **5 Stage 5** Enrichment | ESOP/inter-se/sponsor/ownership rules | FTR-026/027; TDG-GAP-003 | **Yes** event materiality rules | R6 / R14 |
| **5 Stage 6** Structure/deriv/traps | Structure, OI walls, traps; entry/stop **out** | FTR structure; no sizing | Structure yes; entry **POSTPONE** | R5/R9/R12 |
| **5 Stage 7** Gates G00â€“G14 | Multi WAIT_* in Hybrid â†’ **reasons** under 4 states | STA-*; gate codes | Gate narratives in B | All confirm paths |
| **5 Stage 8** Risk/guidance/persist | Qty tables, guidance rail | POST-HYB-01..03 | **Yes** full math | **POSTPONE** product; warnings only |
| **5 Stage 9** OpenAlgo | RO â†’ paper â†’ live ladder | OPN; CROSS-022; POST-HYB-04 | Method surface in B | RO only now |
| **6** Strategy profiles | Mandatory combos per profile | PRF-001..007; CROSS-004; TDG-GAP-014 | **Yes** named keys + veto lists | R2â€“R6 |
| **7** EvidenceClaim + Guidance | 19 base claim fields plus File A PIT fields; guidance with entry/qty | CROSS-019; TDG-GAP-004/005 | Claim list in B; guidance qty **POSTPONE** | R1 DTO |
| **8** Storage | Raw/adjusted, SQLite/Parquet; DuckDB later | Â§14 STO-*; POST-HYB-06 | Split narrative in B | R0 storage / R16 |
| **9** Trader UX | Radar, inspector, risk rail, command bar | UI-*; CROSS-017 | Risk rail **POSTPONE**; research fields in B | R15 / Q5-R6 |
| **10** Productivity (10 items) | Profiles, what-changed, **side-by-side**, FOMO/expiry, journal hash, **daily review**, search | CROSS-017; TDG-GAP-006 | **Yes** full 10-item list | Research-safe UI only |
| **11** API/tables | Scans, `risk/evaluate`, guidance tables | API-*; risk.evaluate **POSTPONE** | Risk endpoints **POSTPONE** | Selection APIs only |
| **12** Failure tests (18) | Baseline failure narratives | Â§25.12 / T-* | Narratives in B | Map to File A T-IDs |
| **13** H1â€“H9 milestones | Old order | **Not sprint board** | H* â†’ Â§9.4 detail map | Use R0â€“R18 only |
| **14** Completion definition | 9 completion points | GOV-006 + observed tests | â€” | File A completion wins |
| **15.1** Planâ†”impl mismatches | Historical | W-* in File A | â€” | Evidence only |
| **15.2** Two-speed lanes | Fast / NRT / EOD / Slow | CROSS-010; TDG-GAP-007; AMEND-A-006 | **Yes** lane table | R17 / ops |
| **15.3** Source contract fields | timezone, rate_budget, circuit_breaker, watermarkâ€¦ | TDG-GAP-001; AMEND-A-001 | **Yes** full field defs | R0 activate source |
| **15.4** Trust combinations | What combo proves / does not prove | CROSS-011; TDG-GAP-008 | **Yes** matrix | FUS / inspector |
| **15.5** Score split + P(win) rules | Data Confidence / Evidence Rank / P(win) / EV; ECE/Brier guards | CROSS-018/023; TDG-GAP-009; AMEND-A-010 | Thresholds in B | Labels now; P(win) UI R16+ |
| **15.6** Execution preflight | Lot/freeze/margin/bands (12 items) | FTR-035 research WAIT; TDG-GAP-010 | Order path **POSTPONE** | Research WAIT only |
| **15.7** Licensing / NSEâ€“SEBI | Compliance boundary | CONFLICT-001; AGENTS/DECISIONS | Pointers in B | Never claim licensed feed |
| **15.8â€“15.9** Alternatives / H1A | History | H1A0 â†’ R0 | â€” | Detail keys only |
| **16.1â€“16.2** Inventory audit scope | Honest boundary, dated SHA | CROSS-001 | Recompute; donâ€™t freeze SHA | R0 |
| **16.3** Source-state ladder | REGISTEREDâ†’â€¦â†’GATE/EXECUTION | CROSS-006; TDG-GAP-011; AMEND-A-011 | **Yes** stage counts | R0 health |
| **16.4** H1A0 defects 1â€“11 + acceptance 1â€“6 | Malformed keys, compound URLs, sentinels, MWPL mismatchâ€¦ | CROSS-001; TDG-GAP-012 | **Yes exact checklist** | **R0 mandatory** |
| **16.5** 354 role utilization table | Roleâ†’fetch disposition | CROSS-001/002 | **Yes** role counts/table | R0 compiler output |
| **16.6** 69 linked + 43 not-linked keys | Exact key lists | CROSS-002; TDG-GAP-013 | **Yes living lists** | Compiler artifact |
| **16.7** Strategy source combinations | Named mandatory/confirm/veto per strategy (incl. MCX blocks) | CROSS-004; TDG-GAP-014; AMEND-A-003 | **Yes full named sets** | R2â€“R6 / R11 |
| **16.8** Feature catalog + formulas | Auction, RVOL_TOD, OI walls, GEX_PROXY, eventsâ€¦ | FTR-*; TDG-GAP-015; AMEND-A-008 | **Yes formulas** | R5/R8/R12 |
| **16.9** Fusion `q_i` + families | Multiplicative quality; independence families | FUS; TDG-GAP-016; AMEND-A-004; CROSS-018 | Formula + family names in B | R3 fusion |
| **16.10** Legacy scorer quarantine | Line-level `intraday_stock_details.py` bugs | FUS-008; CROSS-014 | **Yes line cases** | R1 tests |
| **16.11** Prediction / DS plan | PIT store, labels, purged WF, Brier/ECE, libraries | CROSS-023; TDG-GAP-017 | Full DS plan in B | R16/R18; libs need approval |
| **16.12** Breakage/recovery SM | 14-state SM + fallback hierarchy | CROSS-012; TDG-GAP-018 | **Yes SM** | R17 / scheduler |
| **16.13** OpenAlgo interface | MarketDataProvider / ExecutionProvider methods | CROSS-022; TDG-GAP-019; OPN | Full method list in B | RO methods only |
| **16.14** INR 1L quantity math | Probe/Normal/Exceptional, caps | POST-HYB-01; TDG-GAP-020 | **Yes** | **POSTPONE** |
| **16.15** Product design fields | Surveillance badges, band distance, halt, prediction status | UI; FTR-035 partial | **Yes** badge list | Research badges only |
| **16.16** Activation backlog 1â€“20 | Ordered source activation by decision gap | CROSS-005; TDG-GAP-021; AMEND-A-009 | **Yes priority table** | R2 activation |
| **16.17** Build order + **4 E2E slices** | Stock intra, swing event, MCX gold, MCX crude | CROSS-013 | **Yes slice recipes** | Delivery pattern (not H-order) |
| **16.18** Completion / adversarial criteria | 25 completion criteria | GOV + T-* | Criteria text in B | Map to File A tests |
| **17.2 P0.1** TradabilityRestriction | Full schema; T2T/ESM/bands/halts keys | CROSS-015; FTR-035; TDG-GAP-022 | **Yes field list** | R6 tradability |
| **17.2 P0.2** Raw vs Adjusted | Immutable raw; new adjusted versions | CROSS-020; AMEND HYBRID-17-02 | â€” | CA / storage |
| **17.2 P0.3** Timestamp/revision | available_at, revision semantics | CROSS-019; DAT-019 | Detail in B | R1 claims |
| **17.2 P0.4** MARKET_FLOW parent | Hierarchical family cap | CROSS-021 | Parent rules in B | FUS |
| **17.2 P0.5** Realizable-exit stress | Gap/circuit/liquidity stress | POST-HYB-03 | Full model in B | Research **warning** only |
| **17.2 P0.6** Legacy quarantine | Reinforces FUS-008 | CROSS-014 | â€” | R1 |
| **17.3 P1.1â€“P1.5** Integrity | Outcomes early, demotion, broker tick, fees, release-time | STO/OPN/VAL; CROSS-022/023 | Detail in B | R16/R17 |
| **17.4** Strategy-specific | Stock intra/swing/event + MCX rules | CROSS-004/015; TDG-GAP-022 | **Yes** | R2/R6/R11 |
| **17.5** Feature corrections | Max pain PROTOTYPE_ONLY, etc. | REJ/PST; FTR | â€” | Feature flags |
| **17.6** DS corrections | Calibration/demotion | R16/R18 | â€” | Model gov |
| **17.7** Risk/cost corrections | STT/GST/fee list | TDG-GAP-023; VAL-001 | **Yes fee list** | R16 costs |
| **17.8** UI corrections | Inspector/radar corrections | CROSS-017; UI | **Yes** | R15 |
| **17.9â€“17.12** Milestones/tests/gates | Panel H-order + tests | Â§25.12; T-* | â€” | Do not use H-order as sprint |
| **18.1â€“18.3** Panel recon + claim ledger | ACCEPTED/REJECTED panel discipline | REJ/C-*; HYBRID-18-* | Ledger discipline in B | Docs + inventory |
| **18.4** Dataset-root 11-field identity plus File A business keys | transport_variant, mirror_group, resolverâ€¦ | CROSS-007; TDG-GAP-024; AMEND-A-005 | **Yes field defs** | R0 registry |
| **18.5** Four data-to-decision chains | NSE/MCX Ã— intra/swing flows | PRF; CROSS-013 | **Yes flow diagrams** | Isolation tests |
| **18.6â€“18.7** Code corrections + preserve | SHFE defaults, GSM dating, etc. | Code verify | Verify against code | R0/R11 |
| **18.8** Official-verification backlog | MCX pre-open, LME, â€¦ | POSTPONE/activation | **Yes backlog list** | Do not fake verified |
| **18.9** Not adopted | Universal pledge veto, fetch-all-354, etc. | POST-HYB-07..10; REJ | â€” | **REJECT** as written |
| **18.10â€“18.12** Integration + tests + gate | Panel acceptance | T-*; Â§25.12 | â€” | Map to File A tests |
| **19.1** Maturity / authority | Ladder reinforcement | CROSS-006 | â€” | R0 |
| **19.2** J01â€“J14 decision jobs | Full taxonomy table | CROSS-003; TDG-GAP-025; AMEND-A-012 | **Yes table text** | R0 every dataset_root |
| **19.3** Shared NSE transport | Seeded HTTP transport | DAT-020 | â€” | Keep/extend |
| **19.4** F&O ban vs MWPL % split | Separate contracts | CROSS-008; DAT-015 | **Yes split rules** | R0 safety |
| **19.5** FBIL vs live USD/INR | Daily FX â‰  intraday MCX unlock | CROSS-009 | **Yes role split** | R11 MCX |
| **19.6** State compatibility | READY/WAIT_* â†’ 4 states | STA; CONFLICT-002 | Mapping in B | Reasons only |
| **19.7** Unified PIT outcome worker | Automation worker | R16 STO | Worker detail in B | R16 |
| **19.8** Cross-exchange match states | MATCHED / POSSIBLE_MATCH / DISTINCT / MANUAL_REVIEW | CROSS-016; TDG-GAP-026; AMEND-A-007 | **Yes state rules** | R14 |
| **19.9** Dataset-root P0 priority | 5 true P0 roots | R0 | List in B | Activation |
| **19.10** Conflict/fusion rules 1â€“10 | Fusion narratives | FUS | â€” | Align File A families |
| **19.11** Legacy scorer | Quarantine again | FUS-008; CROSS-014 | â€” | R1 |
| **19.12** Risk policy | Versioned risk % config | POST-HYB / R16 | â€” | POSTPONE product risk % |
| **19.13â€“19.16** Milestone amends / tests / gate | H1A4/H3Aâ€¦ detail keys | R/Q5 map | â€” | Detail only |
| **20** Dual-file pointer | Points back to File A Â§25 | â€” | â€” | Do not treat as new plan |

### 9.2 Detail that is **not** fully written in File A body (must open File B)

File A may have a **one-line pointer** or a **short AMEND field list**. The following **full content** still lives only in Hybrid â€” implementers must open the cited File B section (recompute live data; do not copy stale counts as permanent truth):

1. **Â§16.4** â€” Exact defects **1â€“11** and acceptance **1â€“6** (malformed keys, `|` URLs, sentinels, purpose_jobs, legacy `nse_mwpl_ban` mismatch now resolved by the canonical split).  
2. **Â§16.5â€“16.6** â€” Role disposition table; **living** linked / not-linked `source_key` lists; compiler output requirements.  
3. **Â§19.2** â€” Full **J01â€“J14** decision-job taxonomy text.  
4. **Â§16.7** â€” Per-strategy **named** mandatory / confirm / veto `source_key` sets (intraday continuation/reversal, PEAD, accumulation, MCX gold/energy/base/agri).  
5. **Â§16.16** â€” Priority activation backlog **1â€“20** (the former combined key now maps to `nse_fno_ban` plus unavailable `nse_mwpl_percentages`).  
6. **Â§15.3 / Â§4** â€” Full source-contract field semantics (rate_budget, circuit_breaker, watermark, entitlementâ€¦).  
7. **Â§18.4** â€” Full dataset_root identity field definitions and dedupe model.  
8. **Â§15.2** â€” Fast / NRT / EOD / Slow **lane table** and implications for CONFIRMED ceilings.  
9. **Â§15.4** â€” Trust-producing combinations **matrix** (proves vs does not prove).  
10. **Â§16.3** â€” Maturity ladder **stage-count** requirements for inventory health.  
11. **Â§16.8** â€” Exact **feature formulas** (auction, RVOL_TOD, OI walls, GEX_PROXY labels, event materialityâ€¦).  
12. **Â§16.9** â€” Full `q_i` component semantics and independence-family naming.  
13. **Â§16.10 / Â§19.11** â€” **Line-level** legacy scorer failure cases â†’ regression tests.  
14. **Â§16.12** â€” Per-source **recovery SM** and fallback hierarchy (fallback never inherits official authority).  
15. **Â§17.2 P0.1 / Â§17.4** â€” Full **TradabilityRestriction** fields + strategy-specific tradability rules; proposed T2T/bands/halts contract keys.  
16. **Â§19.4 / Â§19.5** â€” Ban vs MWPL split rules; FBIL daily vs live USD/INR unlock rules.  
17. **Â§19.8** â€” Event match ambiguity **state machine** (not only the four enum names).  
18. **Â§16.17** â€” Four **E2E vertical slice** recipes (stock intra, swing event, MCX gold, MCX crude).  
19. **Â§9â€“10 / Â§16.15 / Â§17.8** â€” Research UX: FOMO/expiry, side-by-side compare, daily review, journal hash snapshot, surveillance badges (still **no** quantity rail).  
20. **Â§16.11 / Â§15.5 / Â§17.6** â€” PIT feature-store design, label defs, purged WF, Brier/ECE promotion guards, demotion ladder (product P(win) UI still gated).  
21. **Â§16.13** â€” OpenAlgo **method surface** (enable MarketData only; ExecutionProvider disabled).  
22. **Â§17.7** â€” STT/GST/fee / cost list for VAL-001 offline costs.  
23. **Â§18.3 / Â§18.8** â€” Panel ACCEPTED/REJECTED discipline; official-verification backlog (do not mark verified without evidence).  
24. **Â§12 / Â§17.10 / Â§18.11 / Â§19.14** â€” Extra failure narratives â†’ map into File A `T-*` / Â§25.12 (do not fork a second test authority).  
25. **Â§16.14 / Stage 8 / guidance qty fields** â€” Keep as **domain reference only** until File A amends research-only scope.

### 9.3 Per-milestone mandatory File B open-list

Open **every** section listed for the milestone. Cite them in `BUILD_STATUS.md`.

| Milestone / vertical | File A IDs (minimum) | Open File B sections (full text) |
|---|---|---|
| **R0 inventory / contracts** | R0, CROSS-001/002/003/006/007/008, TDG-GAP-001/011/012/013/024/025, DAT-010/011/015 | Â§2, Â§4, Â§15.3, Â§16.1â€“16.6, Â§18.2â€“18.4, Â§18.8â€“18.9, Â§19.2â€“19.4, Â§19.9 |
| **R1 claims / quarantine** | R1, CROSS-014/019/020, FUS-008, TDG-GAP-004 | Â§7, Â§16.10, Â§17.2 P0.2â€“P0.3, Â§17.2 P0.6, Â§19.11 |
| **R2 live S0â€“S3 / activation / PRF** | R2, CROSS-004/005/009/015, TDG-GAP-014/021/022 | Â§5 Stages 0â€“4, Â§6, Â§16.7, Â§16.16, Â§17.2 P0.1, Â§17.4, Â§19.5 |
| **R3â€“R5 structure / fusion residual** | FUS, TDG-GAP-015/016, CROSS-011/018/021 | Â§15.4, Â§16.8 (structure), Â§16.9, Â§17.2 P0.4 |
| **R6 enrichment / tradability / history lock** | R6, CROSS-015/019, TDG-GAP-003/005 | Â§5 Stage 5, Â§7 research fields, Â§17.2 P0.1, Â§16.15 badges |
| **R8 native scanners** | R8, TDG-GAP-015, FTR/PK | Â§16.8, Â§16.7 discovery sources, Â§17.5 |
| **R9 lifecycle / ORB / VWAP** | R9 | Â§5 Stage 6, Â§16.8 auction/price/liquidity |
| **R10 pipe DSL** | R10, PK | File A primary; Hybrid quarantine spirit Â§19.11 |
| **R11 MCX live** | R11, CROSS-009, MCX gates | Â§16.7 MCX blocks, Â§17.4 MCX, Â§18.5 MCX chains, Â§19.5 |
| **R12 options timeline** | R12, options FTR | Â§16.8 derivatives, Â§5 Stage 6 OI, GEX_PROXY rules |
| **R13 remaining scanners** | R13 | Â§16.8 + File A family caps |
| **R14 CA / sponsor / events** | R14, CROSS-016/020, TDG-GAP-026 | Â§5 Stage 5, Â§17.2 P0.2, Â§19.8, Â§16.7 PEAD/event |
| **R15 Scanner Lab / UX** | R15, CROSS-017/018 | Â§9, Â§10, Â§16.15, Â§17.8 (no risk rail qty) |
| **R16 PIT / costs / outcomes** | R16, CROSS-023, TDG-GAP-009/017/023 | File A section 25.28 is the mandatory dual-input build contract; Hybrid sections 8, 15.5, 16.11, 17.3 P1.1-P1.2 and 17.6-17.7 remain detail references. |
| **R17 OpenAlgo RO + ops** | R17, CROSS-010/012/022, TDG-GAP-007/018/019 | Â§15.2, Â§16.12, Â§16.13 (RO only), Â§17.3 P1.3 |
| **R18 model governance** | R18 | Â§15.5, Â§16.11, Â§17.3 P1.2, Â§17.6 |
| **Any qty / order / paper live** | â€” | Â§16.14, Â§5 Stage 8, Â§16.13 ExecutionProvider â†’ **POSTPONE/REJECT**; do not build without File A amendment |

### 9.4 Hybrid H* labels â†’ File A (detail keys only, not sprint board)

```text
H1     plan authority              -> File A + BUILD_STATUS
H1A0   inventory compiler          -> R0 / CROSS-001 / Â§16.4
H1A1   claim + raw/adjusted        -> R1 / CROSS-019..020
H1A2   tradability rules           -> FTR-035 / CROSS-015
H1A3   legacy quarantine           -> FUS-008 / CROSS-014
H1A4   scheduler + health          -> CROSS-012 / Â§16.12
H2/H2R/H2A source map / activation -> CROSS-002..005 / Â§16.6 / Â§16.16
H3/H3A pipeline + early outcomes   -> S0â€“S9 + STO outcomes
H4     strategy + fusion           -> PRF + FUS / CROSS-004,021
H5     risk/qty guidance           -> POSTPONE product; research warnings only
H6/H7  radar + inspector           -> UI / R15 / Q5-R6
H8/H8A calibration + drift         -> R16 / R18
H9/H9R OpenAlgo RO sign-off        -> Q5-R7 then R17
H9A    paper/reconcile             -> POSTPONE
H10    live execution              -> REJECT without new File A amendment
```

### 9.5 Explicit POSTPONE / REJECT from Hybrid (do not â€œutilizeâ€ as product)

| Hybrid topic | Disposition |
|---|---|
| INR 1L qty tables, Kelly, multi-tranche (Â§16.14, Stage 8) | POST-HYB-01 |
| entry/stop/targets/R:R/final_qty primary UI (Â§7, Â§9) | POST-HYB-02 |
| realizable_unit_risk â†’ order size (Â§17.2 P0.5) | POST-HYB-03 (research warning OK later) |
| OpenAlgo paper/live ExecutionProvider | POST-HYB-04 / REJ execution |
| Live P(win) / Half-Kelly product UI | POST-HYB-05 until PIT_APPROVED + UI-009 |
| DuckDB as default store | POST-HYB-06 |
| Browser CAPTCHA evade | POST-HYB-07 REJECT |
| Universal 50% pledge veto | POST-HYB-08 REJECT |
| Universal confidence integer score | POST-HYB-09 REJECT |
| Activate/fetch all 354 URLs every scan | POST-HYB-10 REJECT |
| Public multi WAIT_*/READY as API states | CONFLICT-002 â€” File A four states only |
| H1â€“H10 as primary sprint sequence | CONFLICT-003 â€” R0â€“R18 / Q5 only |

### 9.6 Agent checklist (before coding and before â€œdoneâ€)

**Before coding**

```text
[ ] File A requirement IDs for this vertical listed: R0-R18, CROSS-###, or TDG-GAP-###
[ ] CSV P0 PLANNED|PARTIAL rows for this vertical listed (incl. HYBRID-* aliases)
[ ] Every Hybrid Â§ in Â§9.3 for this vertical opened in File B (not skimmed from memory)
[ ] Â§9.2 items that apply are being implemented from File B full text
[ ] File A overrides applied (WATCH/WAIT/CONFIRMED/REJECT; no qty; no OMS; strength â‰  P(win))
[ ] No orphan Hybrid idea without CROSS/GAP/POST/REJECT ID
```

**Before claiming done**

```text
[ ] Tests observed; VALIDATION.md appended
[ ] BUILD_STATUS.md lists exact Hybrid Â§Â§ opened and File A overrides
[ ] CSV seed updated and regenerated with evidence
[ ] No production-ready / live-source claim without matching evidence_level
[ ] No Hybrid qty/execution surface added
```

### 9.7 What this README still does **not** do

- It does **not** replace File A sequence or mint new stable IDs (mint in File A).  
- It does **not** paste Hybridâ€™s multi-page tables (those stay in File B to avoid a third master plan).  
- It **does** make under-use of Hybrid a process failure: if Â§9.3 was not opened, the vertical is incomplete even if File A short contracts look â€œdone.â€

For narrative gap history, see `INDEPENDENT_AUDIT_hybrid_vs_new_merge_2026-07-20.md` (evidence only, not authority).
---

## 10A. Governance AI advisory correction register

### 10.1 Status and reading rule

TRENDFORGE_GOVERNANCE_SYSTEM_ai.md is preserved external advice, not a clean
master plan and not implementation authority. Its current header already labels
it PRESERVED_EXTERNAL_ADVISORY_REFERENCE and Authority: none. Keep the source
file unchanged as evidence. Builders do not read it by default.

Open it only when auditing the history of a reconciled idea. For implementation,
use File A section 0.5 / section 25 for IDs, sequence and scope, then open the
File B section that File A cites. If this advisory differs, File A controls.
No statement in the advisory can override AGENTS.md, DECISIONS.md, File A,
observed source evidence, code, tests, BUILD_STATUS.md or VALIDATION.md.

Verified 2026-07-20 snapshot:

| File | Current lines | Current SHA-256 |
|---|---:|---|
| TRENDFORGE_GOVERNANCE_SYSTEM_ai.md | 1,617 | a2af034c480a17c670d796c665046ff1dadd13c9792eff50b70feb697af6292e |
| File A: new_merge_PLAN_2026-07-18.md | 3,385 | b4a102184a864b7489dc3873b15e6f5527262f546ac7283e9239ac70e0cab2a2 |
| File B: TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md | 2,891 | 25339037b491de5bff5aa38ce91e33a9590922ead91a03f9dea300f3cba0ad1f |

These hashes are evidence for this audit only. They are not permanent CI
constants; any reviewed edit changes them.

### 10.2 Structural defects

The advisory is two analyses concatenated into one file:

- Part 1: lines 1-712.
- Join marker: line 715, glm5.2 guidance below.
- Part 2: starts at line 717 and continues through line 1,617.

The two parts use different CONFLICT and GAP meanings and incompatible coverage
estimates. They must not be treated as one stable registry. Part 1 claims roughly
18 percent present / 61 percent partial / 21 percent absent plus another
7 percent conflict. Part 2 ends near 60 percent fully represented / 35 percent
partial / 5 percent missing. Neither estimate is an active measured result.

Part 1 is also arithmetically inconsistent: its mapped table contains 44 rows
(27 IMPROVE_A, 11 ADD_TO_A, 5 CONFLICT and 1 MERGE), while its separate
8 + 27 + 9 + 3 count equals 47 and its percentages do not sum to 100.

### 10.3 Verified false, stale or imprecise claims

| Advisory claim | Verified current fact |
|---|---|
| File A is 2,199+ lines | File A is 3,385 lines at this audit snapshot |
| File B is 1,200+ lines | File B is 2,891 lines |
| 13 implementation milestones R0-R18 | R0 through R18 is 19 milestones |
| Feature contract has 20 fields | File A section 6 has 22 fields |
| EvidenceClaim has 17 fields | File B section 7 has 19 base fields; File A adds PIT requirements |
| Dataset-root model has 10 or 12 fields | File B section 18.4 has 11 fields; File A adds business keys |
| Cross-exchange model has 5 states | File B has 4: MATCHED, POSSIBLE_MATCH, DISTINCT, MANUAL_REVIEW |
| REJ-011 rejects quantity sizing | REJ-011 rejects broker execution, OMS, account, position and margin routes |
| J01-J14, maturity ladder, inventory pointers and dataset-root are absent from File A | Current File A section 25 already contains or points to them; implementation may still be incomplete |
| READY can map to CONFIRMED | False. READY is not a public state or a synonym for CONFIRMED |
| Fixed 200-outcome / ECE <= 0.05 rule is universal | False. File B rejects one universal fixed promotion count; validation must be profile and PIT specific |
| File B is above File A for exact build scope | False. File A owns scope, sequence, IDs, REJ/PST and acceptance ceilings; File B is detail library |
| Neither file may be read alone because this advisory is the controller | Wrong authority framing. File A already installs the dual-file rule in sections 0.5 and 25 |

### 10.4 ID and registry corrections

- Part 1 and Part 2 reuse CONFLICT-001 and later conflict IDs for different
  topics. They are not stable IDs.
- Part 1 and Part 2 likewise reuse GAP-001 and later GAP IDs for different
  topics.
- File A section 25.8 is the only active conflict registry:
  CONFLICT-001 public NSE routes vs live intraday authority;
  CONFLICT-002 WAIT/READY variants vs four public states;
  CONFLICT-003 H1-H10 vs R0-R18/Q5 order;
  CONFLICT-004 quantity/risk rail vs no-quantity scope;
  CONFLICT-005 online/automatic ML vs offline calibration;
  CONFLICT-006 long-domain-detail placement vs short File A contracts.
- Advisory CONFLICT-007 is retained in PLAN_REQUIREMENT_COVERAGE.csv only as a
  REJECTED legacy alias merged into File A CONFLICT-003. It is not a seventh
  active conflict.
- Quantity, risk-sizing and realizable-unit-risk proposals remain POST-HYB-01
  through POST-HYB-03. They do not use REJ-011 as their governing ID.

### 10.5 Hash, path and coverage-test defects

The executable examples inside the advisory are not safe verification tools:

- The File A hash is stale.
- The File B hash is a placeholder rather than evidence.
- One File B path has the wrong underscore placement.
- The section-orphan test searches generic patterns globally, not once per
  section, so it cannot prove zero orphan requirements.
- Its duplicate-ID and text.find context logic cannot establish stable,
  one-to-one requirement coverage.
- The workbook hashes happened to match at audit time, but workbook hashes must
  always be recomputed from the current files.

Use build_coverage_csv.py plus semantic checks instead. The current reviewed
coverage artifact has 144 unique IDs, six active File A conflicts, and one
explicit rejected legacy conflict alias. Passing --check proves generator/CSV
agreement only; it does not prove semantic correctness or production readiness.

### 10.6 Legacy scorer correction

The advisory Part 1 summary of intraday_stock_details.py lines 887-931 is
inaccurate. The observed implementation:

- uses relative gap_pct, but rewards absolute gap magnitude in either direction;
- counts overlapping options, futures, underlying and most-active activity;
- accepts block/bulk notional without reliable buyer/seller direction;
- uses static delivery, PCR and basis thresholds;
- mixes discovery and directional evidence into one 0-100 score.

File B section 16.10 is the better critique. FUS-008 and CROSS-014 keep this
legacy scorer quarantined until its output is separated from production voting.

### 10.7 Useful ideas retained

The advisory remains useful for these non-authoritative observations:

- File B contains material domain depth not repeated in File A.
- Public states remain WATCH, WAIT, CONFIRMED and REJECT; expanded labels are
  reason codes only.
- R0-R18/Q5 supersedes H-series build order.
- q_i can describe claim quality, while File A FUS-009 controls family fusion.
- No live execution or executable quantity is in current scope.
- PKScreener is a finite offline harness, never a permanent voting sidecar.
- Inventory partition 105 + 231 + 18 = 354 and MASTER row count 370 were
  consistent at the cited snapshot but must be recomputed before use.
- Missing, stale, malformed, metadata-only or conflicting evidence cannot
  produce CONFIRMED.

### 10.8 Corrections installed in active build files

The following corrections are already applied to active, existing files:

- build_coverage_csv.py now sources active conflicts from File A section 25.8,
  not from the advisory.
- PLAN_REQUIREMENT_COVERAGE.csv was regenerated and semantically checked.
- EvidenceClaim is labelled 19 base fields plus File A PIT fields.
- Dataset-root is labelled 11 fields plus File A business keys.
- Quantity rows no longer misuse REJ-011.
- The historical 60/35/5 figure is explicitly labelled external and unmeasured
  in BUILD_STATUS.md and FILEINDEX.md.
- TRENDFORGE_GOVERNANCE_SYSTEM_ai.md remains P3 evidence in
  REMAINING_PROJECT_BUILD_FILES.md and is not mandatory milestone reading.
- DAT-010 and DAT-011 are recorded as implemented at the R0 contract ceiling:
  the registry contains FTR-001..FTR-039 with the exact 22-field contract, every
  scan run carries registry/engine versions, and read-only manifest/lint routes
  expose the contract without activating evidence or unlocking CONFIRMED.
- The pinned indicator engine is `trendforge.numpy-pandas` version `1.0.0`, with
  observed runtime pins NumPy `2.4.3` and pandas `2.3.3`; insufficient warm-up,
  missing/mixed engines and parity divergence remain explicit fail-closed states.

### 10.9 Builder stop rule

Stop and correct the active plan or traceability ledger when any of these occur:

1. An advisory ID is used as active authority without a File A mapping.
2. A line count, hash, source count or coverage percentage is copied without
   current recomputation.
3. A rejected or postponed quantity/execution idea appears in a runtime API.
4. A valid-empty source is confused with fetch or parse failure.
5. A legacy READY or WAIT_* label appears as a fifth public state.
6. A passing test proves only internal consistency while contradicting File A,
   official source evidence or observed runtime behavior.
---

## 10. Final Merge mandatory product/design open-list

`docs/fable/FINAL_MERGE_PLAN.md` is an accepted mapped addendum, not a third build authority. File A section 25.21 owns the crosswalk.

**Naming lock:** **File B** = Hybrid only. Discovery Detail Plan and Options Detail Plan are **not** File B and are **not** build sequences.

Implementers must open the listed FMR section whenever the selected File A vertical includes its alias.

| Final Merge section | Open for | R owners | Linked requirements |
|---|---|---|---|
| `FMR-001` | Every source and every resolved stock in the research universe | R0, R2, R16 | None |
| `FMR-002` | Complete cheap-to-expensive all-stock workflow | R0, R2, R3, R8, R9, R15, R16 | None |
| `FMR-003` | Option-chain identity, quality and feature eligibility | R12 | None |
| `FMR-004` | Strike, OI, PCR, walls, max pain, skew and expiry | R12, R16 | None |
| `FMR-005` | Gamma concentration; signed GEX only as `SCENARIO_ONLY_NOT_OBSERVED_POSITION` | R12, R16 | None |
| `FMR-006` | IV, Greeks, expiry and research-contract inspection | R12, R16 | None |
| `FMR-007` | Derivatives combined with governed stock selection | R3, R12, R15 | None |
| `FMR-008` | PKScreener, open-source calculators and OpenAlgo read-only comparison | R4, R7, R12, R17 | None |
| `FMR-009` | All Stocks, radar and Strike/Expiry inspector | R15 | None |
| `FMR-010` | Acceptance tests, lineage, PIT and state ceilings | Applicable R0-R18 | None |
| `FMR-011` | Local deterministic Research Paper Lab + governed batch ML | R15, R16, R18 | FTR-034, STO-017, UI-009 |

Static fixture checkpoint (2026-08-14):

| Artifact | Present now | Still required in runtime |
|---|---|---|
| `docs/TRENDFORGE_FINAL_PRODUCT.html` | Operations header, All Stocks table/cards, side-by-side decision cards, Stock Evidence tabs, Elliott/harmonic Structure Lab, History & Replay, locked Model Lab and read-only Inventory Workbench drawer | R15 canonical DTO wiring and runtime UX; R16 immutable PIT/replay; R18 governed challenger lifecycle |

This checkpoint is design and interaction evidence only. Do not mark `R15`,
`R16`, `R18`, `FMR-009` or `FMR-011` complete from the static HTML. Do not copy
its inline fixture rows, geometry, timestamps or model values into runtime DTOs.

**Paper Lab vs broker paper trading**

- **FMR-011 allowed:** R15 presentation shell; R16 deterministic replay, path labels and PIT dataset; R18 challenger evaluation, human promotion, drift demotion and rollback.
- **Not allowed:** broker-connected paper/live trading, orders, quantity, Telegram side effects (File A REJECT/POSTPONE).

Checklist:

```text
[ ] Selected one unfinished File A requirement ID: R0-R18, CROSS-###, or TDG-GAP-###; never M/T/PK
[ ] Opened all mapped Hybrid (File B) sections from section 9
[ ] Opened every mapped FMR section from this table (001..011 as applicable)
[ ] Used File A IDs in code/tests; FMR stays a traceability alias
[ ] Preserved File A four states, source/gate permission, no execution and no quantity
[ ] Did not hardcode activation; used runtime + BUILD_STATUS/VALIDATION for ceiling
[ ] Updated coverage generator, VALIDATION and BUILD_STATUS from observed evidence
```

### 10.1 R-first derivation proof

This is a navigation proof, not another implementation order. Given selected
File A owner `R12`, the crosswalk deterministically opens:

```text
R owner: R12
FMR detail: FMR-003, FMR-004, FMR-005, FMR-006, FMR-007, FMR-008
Discovery detail tags: M10, M11, M22, T3
Options detail: OPTIONS_INTELLIGENCE_PLAN.md
```

The work item remains `R12`. `M10`, `M11`, `M22` and `T3` organize detail and
acceptance evidence only; none can be selected as a global "next M" milestone.

### 10.1.1 Mandatory R-first work-packet template

Create this packet before implementation. It is a derivation record for the
already selected File A requirement, not a new milestone or schedule.

```text
Selected File A requirement ID (R0-R18, CROSS-###, or TDG-GAP-###; never M/T/PK):
Objective and acceptance ceiling:
Mapped FMR_refs:
Mapped Hybrid sections:
Discovery/Options detail tags:
Local depends_on tags (inside this R packet only):
Observed sourceActivationReady and evidence timestamp:
Required fail-closed/public-state ceiling:
Focused and adversarial tests:
Full regression commands:
Allowed changed files:
Pre-edit runtime manifest hash:
Excluded/postponed behavior:
```

Validation rules:

1. The selected work item must be one File A requirement ID: `R0-R18`,
   `CROSS-###`, or `TDG-GAP-###`. It remains the only work selector; `M/T/PK`
   are subordinate detail tags and can never select work.
2. FMR aliases and detail tags provide requirements, prerequisites and tests;
   they cannot create a second order.
3. Every listed detail-tag R owner must be covered by its referenced FMR owner
   union. `FMR-010` may carry cross-cutting acceptance ownership where declared.
4. Activation wording and ceilings must use the current observed runtime state,
   never a permanent hardcoded claim.
5. The allowed-file list and runtime manifest hash must pass the executable
   validator before the packet can be reported complete.
### 10.2 Governance-cleanup changed-file boundary

Single-spine governance cleanup is limited to these existing files:

```text
docs/fable/new_merge_PLAN_2026-07-18.md
docs/fable/FINAL_MERGE_PLAN.md
docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md
docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md
fileindex.md
TREND_FORGE_ARCHITECTURE.md
docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md
docs/OPTIONS_INTELLIGENCE_PLAN.md
docs/DECISIONS.md
docs/fable/remaining_build/README.md
docs/fable/remaining_build/REMAINING_PROJECT_BUILD_FILES.md
docs/fable/remaining_build/build_coverage_csv.py
docs/fable/remaining_build/test_build_coverage_csv.py
docs/fable/remaining_build/PLAN_REQUIREMENT_COVERAGE.csv
docs/BUILD_STATUS.md
docs/VALIDATION.md
```

It must not change runtime backend/frontend code, activation state, databases,
the source workbook, broker boundaries or scanner behavior. The validator's
repeatable `--changed-file` option enforces this boundary for every explicitly
supplied repository-relative or absolute path. Governance-cleanup runs must pass
each changed path to the validator; a path outside this allowlist fails closed.
Runtime containment is machine-checked over exactly:

- `backend/trendforge_api/**/*.py`, excluding `__pycache__` and `*.pyc`;
- `frontend/app.js`;
- `frontend/index.html`;
- `frontend/q5-contract.js`;
- `frontend/styles.css`.

Use `--print-runtime-manifest-hash` before editing. Any validation call that
supplies `--changed-file` must also supply the unchanged baseline through
`--expected-runtime-manifest-hash HASH`; omission or mismatch fails closed.
### 10.3 Professional mathematics reconciliation

This documentation-only boundary follows File A section 25.22 and decision
D-030:

1. The mathematics document is a research detail reference, not an authority or second build spine.
2. Current CONFIRMED remains evidence-based; probability/EV is unavailable until mapped R16/R18 PIT validation and approval.
3. File A FUS-009, Hybrid q_i, Discovery M-Factor and Final Merge/Options formula owners remain separate and unchanged.
4. Architecture and UI store observable OI_* quadrant codes; intent terms are not facts.
5. Microprice/OFI/market impact remain postponed without verified timestamped order-event data and calibrated units.
6. The cleanup validator must verify these cross-file references, formulas, decision ID and runtime-file containment.
7. Full Theta uses the complete dividend/carry-aware model, declared clock and exercise/settlement compatibility; no mechanical 252/365 conversion is silently assumed.
8. Delta-hedged realized-versus-implied variance P&L is local, path- and cost-sensitive attribution; it cannot provide direction, observed flow or guaranteed gamma-scalping profit.
9. VRP context requires synchronized same-horizon implied-variance method and PIT expected-realized-variance forecast, costs and calibration. `ATM_IV^2 * T` is a labeled proxy, not model-free variance.
10. Missing or mismatched VRP evidence returns `VRP_UNKNOWN`. Positive/negative VRP, IV/RV, backwardation or contango cannot create automatic option buy/sell language.
11. R12 owns data/model contracts, R16 owns PIT replay/calibration, and R18 owns promotion/drift/demotion. The feature remains postponed research context until those gates pass.

## Source Operations UI note - 2026-08-15

The embedded Inventory Workbench Source Operations panel is a verification and
observability surface for the R0/R1/R2 build. It shows compiler-to-fact flow and
source failure reasons below the inventory KPI cards. It does not change the
File A milestone order, source activation, resolver rules, public states,
quantity scope, or execution boundary. Valid-empty remains distinct from failed;
activation and gate authorization remain separate. The panel is useful for
checking why a last-good fact is missing before implementing the next build step.


## Hash-pin caveat - 2026-08-15

The source and bundled runtime files contain aligned feature markers but are separate revisions and are not byte-identical for this
change, but the existing snapshot manifest still contains the pre-Source-
Operations byte sizes and hashes. The existing `inventory-workbench.test.js`
also still expects the old drawer URL without `embed=terminal`. Its current
observed result is **FAIL: Size mismatch: index.html**. This means the runtime
panel observation is valid, but the manifest/test pin must be refreshed before
claiming a clean snapshot-integrity verdict. No source data, catalog sample, or
TrendForge state authority is affected by this metadata/test discrepancy.

## Post-commit bridge correction - 2026-08-15

The A1-C1 stages are connected to Refresh and Scheduler through the existing saved-data boundary. The browser does not call the stages. A source must first produce a schema-valid parsed artifact committed as current last-good with hash/date identity. The bridge then runs only the affected cash path, deduplicates the same relevant fingerprint, preserves collector success when a downstream stage fails, and records FAILED_STAGE.

GET /api/source-operations/snapshot is the single read model for the embedded workbench. Its source-flow track and cash A1-C1 track are separate. It exposes health and lineage only; it does not change R0-R2 order, rebuild C0 for each download, invent MWPL, activate sources, produce CONFIRMED, calculate quantity or place orders.

Implementation files: backend/trendforge_api/selection/cash_post_commit.py, market_data_scheduler.py, source_operations.py, main.py, backend/run_server.py, scripts/start_api_md69.ps1, and frontend/inventory-workbench/index.html, app.js and styles.css. The API was restarted and a real current cash last-good artifact completed the path on 2026-08-16; this verifies operational research wiring, not source activation, CONFIRMED, quantity or execution.


## Cadence-aware source dates, family dispatch and scheduler closure - 2026-08-16

### Observed evidence

The manual registry run `2026-08-16-manual-20260816-123159-0047999505c9` attempted all **123** source contracts. The result was re-audited from normalized object contents, not HTTP status or manifest row count:

| Result class | Sources | Meaning |
|---|---:|---|
| Usable parsed records | 107 | Normalized market, event, holdings, contract or macro rows were present. This is data readiness evidence only, not activation or confirmation authority. |
| Valid empty | 3 | Empty was explicit and remains different from fetch/parse failure; it supplies no candidate rows. |
| Stale last-good fallback | 3 | Prior rows were retained after current transport/parser failure; they are visible but non-current. |
| Status/schema envelope only | 10 | Collector returned a normalized status envelope rather than usable trading records; HTTP/collector success must not count these as usable data. |

The cadence registry currently contains 32 intraday, 28 daily EOD, 15 daily/change-detect, 12 event-driven, 11 slow event-driven, 11 weekly, 5 quarterly, 3 intraday-event, 2 commodity EOD, 2 fortnightly and 2 session-window contracts. Its cadence evidence is still predominantly `PROVISIONAL_UNVERIFIED_NEEDS_OFFICIAL_WEB_CHECK`; the audit therefore records provisional disposition rather than activation truth.

The cadence-aware audit identifies **8** late or suspect contracts and **4** usable sources that still lack temporal proof. It does not call every old date stale. Examples:

- `nse_bhavcopy_eod` and `nse_fo_bhavcopy` dated 2026-08-14 are current for the latest NSE session when run on Sunday 2026-08-16.
- CFTC reports dated 2026-08-11 and EIA weekly petroleum data dated 2026-08-07 are plausible current weekly publications, pending official cadence proof.
- Event-driven disclosure dates describe the latest event, not collector freshness by themselves.
- `nsdl_fpi_daily_reportdetail` dated 2024-08-23 and `cdsl_fpi_fortnightly` dated 2024-08-26 are suspect parameter/publication selections and cannot be called current.
- At the 2026-08-16 12:31 full-registry snapshot, `mcx_bhavcopy`, `bse_financial_results_xbrl` and `bse_shareholding_pattern` were stale last-good fallbacks. Later source-specific runs repaired both BSE sources with populated 2026-08-15 data; `mcx_bhavcopy` remains the unresolved stale source. The historical 123-source counts above are not silently recalculated without another complete run.

The validated pending workbook `data/reports/SOURCE_LINK_INVENTORY_MASTER.updated.xlsx` contains `CADENCE_SUMMARY` and `CADENCE_AUDIT` sheets with URL, cadence, observed/derived data date, actual parsed-row count, usability class, dispatch rule and required next action for every registry source. Replacing the canonical workbook is awaiting separate explicit approval.

### Build pointer

The implementation plan is appended to `R0_R1_R2_LOCKED_PLAN_2026-08-15.md` under the same marker. Complete `CAD-001` through `CAD-006` sequentially. Do not run all 123 sources through cash A1-C1; use the cadence-aware family router. The validated pending workbook `SOURCE_LINK_INVENTORY_MASTER.updated.xlsx` sheets `CADENCE_SUMMARY` and `CADENCE_AUDIT` are the current per-source audit evidence until canonical replacement is approved.



## Refresh and A1-C1 implementation checkpoint - 2026-08-16

This operational repair supports the existing R0/R1/R2 work; it does **not** advance activation or create a new milestone. The shared scheduler now uses the official expected NSE EOD date for post-commit input selection, and FastAPI locally owns one guarded automatic worker when `MARKET_DATA_69_AUTOSTART=1`. A real 123-contract Refresh completed with 119 new, 1 last-good and 3 valid-empty results; no terminal failures. Its cash path completed A1/A2/A3/A4/A6/C1 for EOD 2026-08-14, while A5 and B remained explicit skips. The public ceiling remains WATCH/WAIT/REJECT and no source is activation-authorized.

Evidence: 38 focused tests passed; full backend was 861 passed with 21 unrelated baseline failures; frontend was 161/161; the bundled workbench verification reported 24 copied files verified. Continue the File A milestone order; do not treat the collector or inventory cards as independent votes.

## R3 implementation handoff - 2026-08-16

R3 is now live in TrendForge, not in the Inventory Workbench. Read `selection/r3_claim_adapter.py`, `selection/r3_live.py`, `selection/cash_post_commit.py`, `source_inventory_compiler.py` and `GET /api/v1/selection/resolution`. FTR-040 permits only exact current NSE EOD cash participation for SWING/NSE_EQ and remains WAIT-only. R1/R2 are immutable inputs; aliases/cards do not vote; stale permission or mixed hashes return 503. Runtime: 2,463 WAIT rows, 0 CONFIRMED and no trade geometry. Live R4 is the ID pin + PK inventory digest (`GET /api/v1/selection/identity-pin`); next before CONFIRMED is R14.

## Hybrid V2 overlay row (IMPLEMENTED at research ceiling) - 2026-08-22

`backend/trendforge_api/hybrid_v2/` is a sibling research package, not an
R-step: read-only spine adapter (R1/R2-A/R4/R14/R5, hash-matched or 503),
blocks B1-B5 (only B3/AS delivery real), stages S0-S9 paper chain,
triple-barrier label spec, cost-derived p_min / Kelly illustration. Both S4/S5
families kept; formulas reuse `selection/s4s5_compare` exactly. Ceiling:
RESEARCH_PROXY_NOT_CALIBRATED; never CONFIRMED, never qty. Routes:
`GET /api/v1/hybrid-v2/overlay`, `GET /api/v1/hybrid-v2/overlay/{symbol}`
(POST 405). Tests: `backend/tests/hybrid_v2/`. Frontend: same shell,
`#hybridV2Chain` in section#flow + `#hybridV2OverlayPanel`; File A strip and
`#s4s5ComparePanel` untouched.


### 2026-08-22 (later) - radar calculate layer filled

28 radar tests / 78 combined / 175 frontend. RS benchmark, R5 tags, delivery z
recipe, pre-open recipe, SHP context, MCX DTE wired; UNKNOWN slots are
file-missing (MTO, pre-open snapshot), not formula-missing.

### 2026-08-22 (latest) - S2 weather built

Nifty % honest at parse time; S2 DTO + routes + strip live. Tests 9/93/181.
## R16 pre-migration implementation handoff - 2026-08-28

Open File A section 25.28 before touching R16. Current code owners are:

- backend/trendforge_api/selection/s8_service.py
- backend/trendforge_api/selection/r16_pit.py
- backend/trendforge_api/selection/r16_metrics.py
- backend/trendforge_api/selection/r16_store.py
- backend/trendforge_api/selection/r16_service.py
- backend/trendforge_api/selection/cash_post_commit.py
- backend/trendforge_api/selection/cash_a4_history.py
- backend/trendforge_api/cli.py and main.py
- frontend/r16-pit-validation.js
- frontend/s9-pit-homework.js compatibility shim
- backend/tests/test_r16_pit.py

Verified pre-migration state: focused 51 passed; full backend 1,336 passed;
frontend 218/218; read-only CLI/API report BUILDING / PIT_NOT_APPROVED /
WAIT_R16_SCHEMA_NOT_APPLIED. Observations are absent from initial frontend load.

Do not rebuild R16 or restore the legacy 20-row/client-approval path. The next
R16 action is a separately approved backup plus live migration
0013_r16_pit_substrate, followed by r16-catch-up, populated deterministic replay,
query-plan/performance and API/UI observation. Keep R16 PARTIAL until those
checks pass. Insufficient real history remains BUILDING; never fabricate
PIT_APPROVED. No CONFIRMED, probability, broker, order or quantity authority is
part of this handoff.


## R16 post-migration handoff - 2026-08-29

Do not rerun the R16 migration or rebuild the legacy PIT gate. The live database
already has migration `0013_r16_pit_substrate`, one valid 2026-08-28 dataset,
2,034 hypotheses/observations, six exact-cell metrics and six ledger rows.
Replay is idempotent (`observationsAppended=0` on two repeats), named query
indexes are observed, API GETs are read-only and POSTs return 405.

Current truth is `BUILDING / PIT_NOT_APPROVED`, not a failure. Only one eligible
S8 date exists, so folds, holdout and the required sample floors cannot pass.
Keep collecting canonical complete S8 days and run incremental replay after new
closed EOD data. Do not backfill synthetic S8 history or reinterpret rejected
legacy artifacts. Next roadmap work may proceed, but probability/performance UI
and R18 promotion remain blocked until exact-cell PIT floors pass.

Verification checkpoint: focused R16 16 passed; full backend 1,343 passed;
frontend 218/218. Rendered browser inspection is the only tooling caveat; static
lazy-observation and no-client-approval checks pass. No broker, order, quantity
or CONFIRMED authority exists.


## 2026-09-03 - CROSS-015 / TDG-GAP-022 gate implemented

Do not rebuild the unified tradability gate unless regression evidence fails.
Open `selection/tradability.py` for typed source/component policy,
`selection/s7_state_gates.py` for state enforcement, `selection/s8_service.py`
and `selection/s8_persist_run.py` for one-batch lineage, and
`test_tradability_gate.py` for the acceptance matrix. The read-only endpoints
are `/api/v1/selection/tradability` and
`/api/v1/selection/tradability/{symbol}`.

The code requirement and the three named acquisition paths are complete at the
research fail-closed ceiling. `nse_esm`, `nse_price_bands` and
`nse_auction_securities` use the existing 126-job collector and canonical
last-good store. Current proof is 290 ESM rows, 3,517 price-band rows and an
explicit auction `NIL` valid-empty result. The gate consumes those saved
objects directly. Exact price-band boundaries are not present in the daily
classification file, so banded symbols remain WAIT until boundary values are
available. Current S7 runtime can still be upstream-blocked when R5 structure
is unavailable. PASS is never a vote. No source activation, probability,
broker, order or execution authority follows.
